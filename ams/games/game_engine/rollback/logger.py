"""
Game State Logger - Log snapshots for debugging via central sink system.

Serializes GameSnapshots for post-mortem analysis, replay debugging, and
understanding rollback behavior. Output is routed through ams.logging sinks:
- Native Python: FileSink writes JSONL to disk
- Browser/WASM: WebSocketSink streams to dev server

DISABLED BY DEFAULT - Enable via environment variable or programmatic config.

Environment variables (via ams.logging):
    AMS_LOGGING_ROLLBACK_ENABLED=true
    AMS_LOGGING_ROLLBACK_INTERVAL=5
    AMS_LOG_DIR=./debug_logs

Example .env:
    AMS_LOGGING_ROLLBACK_ENABLED=true
    AMS_LOGGING_ROLLBACK_INTERVAL=1
"""

import time
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING, Union

from .snapshot import GameSnapshot, EntitySnapshot

if TYPE_CHECKING:
    from .manager import RollbackStateManager

# Module name for sink registry
ROLLBACK_MODULE = 'rollback'


def _get_rollback_config() -> Dict[str, Any]:
    """Get rollback module config from central logging system."""
    from ams.logging import get_module_config
    return get_module_config(ROLLBACK_MODULE)


class GameStateLogger:
    """
    Logs game state snapshots via the central ams.logging sink system.

    Records are emitted through emit_record() which routes to the appropriate
    sink for the environment (FileSink for native, WebSocketSink for browser).

    DISABLED BY DEFAULT. Use create_logger() factory which respects
    AMS_LOGGING_ROLLBACK_ENABLED environment variable.

    Args:
        session_name: Optional name for this session (default: timestamp)
        log_interval: Only log every N snapshots (default: 1 = every snapshot)
        include_entities: Whether to include full entity data (default: True)

    Example:
        # Preferred: Use factory (respects config)
        logger = create_logger(session_name="debug_run")
        snapshot = rollback_manager.capture(game_engine)
        logger.log_snapshot(snapshot)
        logger.close()

        # Or with context manager:
        with create_logger() as logger:
            logger.log_snapshot(snapshot)
    """

    def __init__(
        self,
        session_name: Optional[str] = None,
        log_interval: int = 1,
        include_entities: bool = True,
    ):
        # Generate session name from timestamp if not provided
        if session_name is None:
            session_name = time.strftime("%Y%m%d_%H%M%S")
        self.session_name = session_name

        self.log_interval = log_interval
        self.include_entities = include_entities

        self._snapshot_count = 0
        self._logged_count = 0
        self._closed = False

        # Emit header record
        self._emit({
            "type": "header",
            "session_name": self.session_name,
            "start_time": time.time(),
            "start_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "log_interval": self.log_interval,
            "include_entities": self.include_entities,
        })

    def _emit(self, record: Dict[str, Any]) -> bool:
        """Emit a record through the central logging system."""
        from ams.logging import emit_record
        return emit_record(ROLLBACK_MODULE, record)

    def log_snapshot(self, snapshot: GameSnapshot) -> bool:
        """Log a snapshot.

        Args:
            snapshot: The game snapshot to log

        Returns:
            True if snapshot was logged, False if skipped due to interval
        """
        self._snapshot_count += 1

        # Check interval
        if self._snapshot_count % self.log_interval != 0:
            return False

        record = self._snapshot_to_dict(snapshot)
        record["type"] = "snapshot"
        record["log_index"] = self._logged_count

        self._emit(record)
        self._logged_count += 1

        return True

    def log_rollback(
        self,
        target_timestamp: float,
        restored_frame: int,
        frames_resimulated: int,
        hit_position: Optional[tuple] = None,
    ) -> None:
        """Log a rollback event.

        Args:
            target_timestamp: Timestamp we rolled back to
            restored_frame: Frame number we restored to
            frames_resimulated: Number of frames re-simulated
            hit_position: Optional (x, y) of the hit that triggered rollback
        """
        self._emit({
            "type": "rollback",
            "wall_time": time.time(),
            "target_timestamp": target_timestamp,
            "restored_frame": restored_frame,
            "frames_resimulated": frames_resimulated,
            "hit_position": hit_position,
            "log_index": self._logged_count,
        })
        self._logged_count += 1

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log a custom event.

        Args:
            event_type: Type identifier for the event
            data: Event data to log
        """
        self._emit({
            "type": event_type,
            "wall_time": time.time(),
            "log_index": self._logged_count,
            **data,
        })
        self._logged_count += 1

    def _snapshot_to_dict(self, snapshot: GameSnapshot) -> Dict[str, Any]:
        """Convert snapshot to JSON-serializable dict."""
        result = {
            "frame_number": snapshot.frame_number,
            "elapsed_time": snapshot.elapsed_time,
            "timestamp": snapshot.timestamp,
            "score": snapshot.score,
            "lives": snapshot.lives,
            "internal_state": snapshot.internal_state,
            "entity_count": snapshot.entity_count,
            "alive_entity_count": snapshot.alive_entity_count,
        }

        if self.include_entities:
            result["entities"] = {
                eid: self._entity_to_dict(e)
                for eid, e in snapshot.entities.items()
            }

        # Scheduled callbacks
        result["scheduled_callbacks"] = [
            {
                "time_remaining": cb.time_remaining,
                "callback_name": cb.callback_name,
                "entity_id": cb.entity_id,
            }
            for cb in snapshot.scheduled_callbacks
        ]

        return result

    def _entity_to_dict(self, entity: EntitySnapshot) -> Dict[str, Any]:
        """Convert entity snapshot to JSON-serializable dict."""
        return {
            "id": entity.id,
            "entity_type": entity.entity_type,
            "alive": entity.alive,
            "x": entity.x,
            "y": entity.y,
            "vx": entity.vx,
            "vy": entity.vy,
            "width": entity.width,
            "height": entity.height,
            "health": entity.health,
            "visible": entity.visible,
            "color": entity.color,
            "sprite": entity.sprite,
            "tags": list(entity.tags),
            "properties": entity.properties,
            "behaviors": list(entity.behaviors),
            "parent_id": entity.parent_id,
            "children": list(entity.children),
        }

    def flush(self) -> None:
        """Flush buffered data."""
        from ams.logging import get_sink
        sink = get_sink(ROLLBACK_MODULE)
        if sink:
            sink.flush()

    def close(self) -> None:
        """Close the logger and write footer."""
        if self._closed:
            return

        self._emit({
            "type": "footer",
            "end_time": time.time(),
            "end_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_snapshots": self._snapshot_count,
            "logged_snapshots": self._logged_count,
        })

        # Flush the sink but don't close it (other loggers may share it)
        self.flush()
        self._closed = True

    @property
    def log_path(self) -> Optional[Path]:
        """Path to the current log file (if using FileSink)."""
        from ams.logging import get_sink, FileSink
        sink = get_sink(ROLLBACK_MODULE)
        if isinstance(sink, FileSink):
            paths = sink.log_paths
            return paths.get(ROLLBACK_MODULE)
        return None

    @property
    def stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        return {
            "session_name": self.session_name,
            "total_snapshots": self._snapshot_count,
            "logged_snapshots": self._logged_count,
            "log_interval": self.log_interval,
            "log_path": str(self.log_path) if self.log_path else None,
        }

    def __enter__(self) -> 'GameStateLogger':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class NullLogger:
    """No-op logger when logging is disabled.

    Provides the same interface as GameStateLogger but does nothing.
    Allows code to call logger methods without checking if logger is None.
    """

    def log_snapshot(self, snapshot: GameSnapshot) -> bool:
        return False

    def log_rollback(self, *args, **kwargs) -> None:
        pass

    def log_event(self, *args, **kwargs) -> None:
        pass

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass

    @property
    def log_path(self) -> Optional[Path]:
        return None

    @property
    def stats(self) -> Dict[str, Any]:
        return {"enabled": False}

    def __enter__(self) -> 'NullLogger':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


def create_logger(
    session_name: Optional[str] = None,
    log_interval: Optional[int] = None,
    include_entities: bool = True,
    force: bool = False,
) -> Union['GameStateLogger', 'NullLogger']:
    """Factory to create a logger, respecting central logging config.

    Returns a real GameStateLogger if logging is enabled, otherwise
    returns a NullLogger that does nothing. Automatically sets up the
    appropriate sink for the environment.

    Configuration via env vars:
        AMS_LOGGING_ROLLBACK_ENABLED=true
        AMS_LOGGING_ROLLBACK_INTERVAL=5

    Args:
        session_name: Optional name for this session
        log_interval: Log every N snapshots (default from config, or 1)
        include_entities: Include full entity data
        force: Create real logger even if not enabled in config

    Returns:
        GameStateLogger if enabled, NullLogger if disabled

    Example:
        # In .env:
        # AMS_LOGGING_ROLLBACK_ENABLED=true

        logger = create_logger(session_name="debug")
        logger.log_snapshot(snapshot)  # Works whether enabled or not
        logger.close()
    """
    config = _get_rollback_config()
    enabled = config.get('enabled', False)

    if force or enabled:
        # Ensure sink is registered for rollback module
        from ams.logging import (
            get_sink, register_sink, create_sink_for_environment
        )
        if get_sink(ROLLBACK_MODULE) is None:
            sink = create_sink_for_environment(ROLLBACK_MODULE, session_name)
            register_sink(ROLLBACK_MODULE, sink)

        # Get interval from config if not explicitly provided
        if log_interval is None:
            log_interval = config.get('interval', 1)

        return GameStateLogger(
            session_name=session_name,
            log_interval=log_interval,
            include_entities=include_entities,
        )
    else:
        return NullLogger()


def load_log(log_path: str) -> list:
    """Load a log file and return list of records.

    Args:
        log_path: Path to .jsonl log file

    Returns:
        List of parsed JSON records
    """
    import json
    records = []
    with open(log_path, 'r') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def summarize_log(log_path: str) -> Dict[str, Any]:
    """Generate summary statistics from a log file.

    Args:
        log_path: Path to .jsonl log file

    Returns:
        Dict with summary statistics
    """
    records = load_log(log_path)

    header = next((r for r in records if r.get("type") == "header"), {})
    footer = next((r for r in records if r.get("type") == "footer"), {})
    snapshots = [r for r in records if r.get("type") == "snapshot"]
    rollbacks = [r for r in records if r.get("type") == "rollback"]

    summary = {
        "session_name": header.get("session_name"),
        "start_time": header.get("start_time_iso"),
        "end_time": footer.get("end_time_iso"),
        "total_snapshots": footer.get("total_snapshots", len(snapshots)),
        "logged_snapshots": len(snapshots),
        "rollback_count": len(rollbacks),
    }

    if snapshots:
        summary["frame_range"] = (
            snapshots[0].get("frame_number"),
            snapshots[-1].get("frame_number"),
        )
        summary["time_range"] = (
            snapshots[0].get("elapsed_time"),
            snapshots[-1].get("elapsed_time"),
        )
        summary["final_score"] = snapshots[-1].get("score")

    if rollbacks:
        summary["total_frames_resimulated"] = sum(
            r.get("frames_resimulated", 0) for r in rollbacks
        )

    return summary
