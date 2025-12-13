"""
Rollback State Manager - Core rollback implementation.

Manages state snapshots and provides rollback/re-simulation capabilities
for handling delayed hit detection from CV backends.
"""

import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple, TYPE_CHECKING

from .snapshot import EntitySnapshot, GameSnapshot, ScheduledCallbackSnapshot

if TYPE_CHECKING:
    from ams.games.game_engine.engine import GameEngine
    from ams.games.game_engine.entity import GameEntity
    from ams.events import PlaneHitEvent


@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    success: bool
    frames_resimulated: int = 0
    snapshot_age_ms: float = 0.0
    error: Optional[str] = None


class RollbackStateManager:
    """
    Manages game state snapshots for rollback and re-simulation.

    Captures periodic snapshots of game state, enabling restoration
    to a past point and re-simulation with corrected inputs.

    Args:
        history_duration: How far back in time we can rollback (seconds)
        fps: Expected frame rate (for calculating snapshot buffer size)
        snapshot_interval: Capture every N frames (1 = every frame)

    Example:
        manager = RollbackStateManager(history_duration=2.0, fps=60)

        # In game loop:
        manager.capture(game_engine)

        # When delayed hit arrives:
        result = manager.rollback_and_resimulate(
            game_engine,
            target_timestamp=hit.timestamp,
            hit_applicator=lambda: apply_hit(hit),
        )
    """

    def __init__(
        self,
        history_duration: float = 2.0,
        fps: int = 60,
        snapshot_interval: int = 1,
    ):
        self.history_duration = history_duration
        self.fps = fps
        self.snapshot_interval = snapshot_interval

        # Calculate buffer size
        max_snapshots = int(history_duration * fps / snapshot_interval)
        self._snapshots: Deque[GameSnapshot] = deque(maxlen=max_snapshots)

        # Frame counter for interval-based capture
        self._frame_counter = 0

        # Statistics
        self._total_captures = 0
        self._total_rollbacks = 0

    @property
    def snapshot_count(self) -> int:
        """Number of snapshots currently stored."""
        return len(self._snapshots)

    @property
    def max_snapshots(self) -> int:
        """Maximum number of snapshots that can be stored."""
        return self._snapshots.maxlen or 0

    @property
    def oldest_timestamp(self) -> Optional[float]:
        """Timestamp of oldest available snapshot, or None if empty."""
        if self._snapshots:
            return self._snapshots[0].timestamp
        return None

    @property
    def newest_timestamp(self) -> Optional[float]:
        """Timestamp of newest available snapshot, or None if empty."""
        if self._snapshots:
            return self._snapshots[-1].timestamp
        return None

    def can_rollback_to(self, timestamp: float) -> bool:
        """Check if we can rollback to the given timestamp.

        Args:
            timestamp: Target timestamp (time.monotonic())

        Returns:
            True if timestamp is within rollback window
        """
        if not self._snapshots:
            return False
        return self._snapshots[0].timestamp <= timestamp

    def capture(self, game_engine: 'GameEngine', force: bool = False) -> Optional[GameSnapshot]:
        """Capture current game state as a snapshot.

        Args:
            game_engine: The game engine to capture state from
            force: If True, capture even if not at snapshot interval

        Returns:
            The captured snapshot, or None if skipped due to interval
        """
        self._frame_counter += 1

        # Check interval (unless forced)
        if not force and (self._frame_counter % self.snapshot_interval != 0):
            return None

        snapshot = self._capture_snapshot(game_engine)
        self._snapshots.append(snapshot)
        self._total_captures += 1

        return snapshot

    def _capture_snapshot(self, game_engine: 'GameEngine') -> GameSnapshot:
        """Internal: Create snapshot from current game state."""
        lua_engine = game_engine._behavior_engine

        # Capture all entity states (skip system entities like pointer)
        entity_snapshots: Dict[str, EntitySnapshot] = {}
        for entity_id, entity in lua_engine.entities.items():
            if entity_id != 'pointer':
                entity_snapshots[entity_id] = EntitySnapshot.from_entity(entity)

        # Capture scheduled callbacks
        scheduled = tuple(
            ScheduledCallbackSnapshot(
                time_remaining=cb.time_remaining,
                callback_name=cb.callback_name,
                entity_id=cb.entity_id,
            )
            for cb in lua_engine._scheduled
        )

        # Get internal state as string
        internal_state = game_engine._internal_state.name if hasattr(
            game_engine._internal_state, 'name'
        ) else str(game_engine._internal_state)

        return GameSnapshot(
            frame_number=self._frame_counter,
            elapsed_time=lua_engine.elapsed_time,
            timestamp=time.monotonic(),
            entities=entity_snapshots,
            score=lua_engine.score,
            lives=getattr(game_engine, '_lives', 3),
            internal_state=internal_state,
            scheduled_callbacks=scheduled,
        )

    def find_snapshot(self, timestamp: float) -> Optional[GameSnapshot]:
        """Find the snapshot closest to (but not after) the given timestamp.

        Args:
            timestamp: Target timestamp to find

        Returns:
            Snapshot at or before timestamp, or None if not found
        """
        if not self._snapshots:
            return None

        # Binary search would be faster, but linear is fine for typical sizes
        best: Optional[GameSnapshot] = None
        for snapshot in self._snapshots:
            if snapshot.timestamp <= timestamp:
                best = snapshot
            else:
                # Snapshots are ordered, so we can stop
                break

        return best

    def find_snapshot_index(self, timestamp: float) -> int:
        """Find index of snapshot closest to (but not after) timestamp.

        Args:
            timestamp: Target timestamp

        Returns:
            Index into snapshots deque, or -1 if not found
        """
        best_idx = -1
        for idx, snapshot in enumerate(self._snapshots):
            if snapshot.timestamp <= timestamp:
                best_idx = idx
            else:
                break
        return best_idx

    def restore(self, game_engine: 'GameEngine', snapshot: GameSnapshot) -> None:
        """Restore game state from a snapshot.

        Args:
            game_engine: The game engine to restore
            snapshot: The snapshot to restore from
        """
        lua_engine = game_engine._behavior_engine

        # Restore global state
        lua_engine.elapsed_time = snapshot.elapsed_time
        lua_engine.score = snapshot.score
        if hasattr(game_engine, '_lives'):
            game_engine._lives = snapshot.lives

        # Restore internal state (convert string back to enum if needed)
        self._restore_internal_state(game_engine, snapshot.internal_state)

        # Restore scheduled callbacks
        self._restore_scheduled_callbacks(lua_engine, snapshot.scheduled_callbacks)

        # Restore entities
        self._restore_entities(game_engine, lua_engine, snapshot)

    def _restore_internal_state(
        self, game_engine: 'GameEngine', state_str: str
    ) -> None:
        """Restore internal game state from string representation."""
        # Try to convert string to enum
        if hasattr(game_engine, '_internal_state'):
            state_type = type(game_engine._internal_state)
            if hasattr(state_type, state_str):
                game_engine._internal_state = getattr(state_type, state_str)
            elif hasattr(state_type, '__members__'):
                # Enum type - try to find matching member
                for member in state_type.__members__.values():
                    if member.name == state_str:
                        game_engine._internal_state = member
                        break

    def _restore_scheduled_callbacks(
        self,
        lua_engine: Any,
        callbacks: Tuple[ScheduledCallbackSnapshot, ...],
    ) -> None:
        """Restore scheduled callbacks from snapshot."""
        from ams.lua.engine import ScheduledCallback

        lua_engine._scheduled = [
            ScheduledCallback(
                time_remaining=cb.time_remaining,
                callback_name=cb.callback_name,
                entity_id=cb.entity_id,
            )
            for cb in callbacks
        ]

    def _restore_entities(
        self,
        game_engine: 'GameEngine',
        lua_engine: Any,
        snapshot: GameSnapshot,
    ) -> None:
        """Restore entity state from snapshot."""
        current_ids = set(lua_engine.entities.keys())
        snapshot_ids = set(snapshot.entities.keys())

        # Remove entities that didn't exist at snapshot time
        for entity_id in current_ids - snapshot_ids:
            del lua_engine.entities[entity_id]

        # Restore or recreate entities from snapshot
        for entity_id, entity_snap in snapshot.entities.items():
            if entity_id in lua_engine.entities:
                # Entity exists - restore its state
                entity_snap.apply_to(lua_engine.entities[entity_id])
            else:
                # Entity doesn't exist - recreate it
                entity = self._recreate_entity(game_engine, entity_snap)
                lua_engine.entities[entity_id] = entity

    def _recreate_entity(
        self, game_engine: 'GameEngine', snapshot: EntitySnapshot
    ) -> 'GameEntity':
        """Recreate an entity from snapshot (for entities that were removed)."""
        from ams.games.game_engine.entity import GameEntity

        entity = GameEntity(
            id=snapshot.id,
            entity_type=snapshot.entity_type,
            alive=snapshot.alive,
            x=snapshot.x,
            y=snapshot.y,
            vx=snapshot.vx,
            vy=snapshot.vy,
            width=snapshot.width,
            height=snapshot.height,
            color=snapshot.color,
            sprite=snapshot.sprite,
            visible=snapshot.visible,
            health=snapshot.health,
            spawn_time=snapshot.spawn_time,
            tags=list(snapshot.tags),
            behaviors=list(snapshot.behaviors),
            behavior_config=dict(snapshot.behavior_config),
            parent_id=snapshot.parent_id,
            parent_offset=tuple(snapshot.parent_offset),
            children=list(snapshot.children),
        )
        entity.properties = dict(snapshot.properties)

        # Set lifecycle dispatch if available
        if hasattr(game_engine, '_dispatch_lifecycle'):
            entity._lifecycle_dispatch = game_engine._dispatch_lifecycle

        return entity

    def rollback_and_resimulate(
        self,
        game_engine: 'GameEngine',
        target_timestamp: float,
        hit_applicator: Callable[[], None],
        current_timestamp: Optional[float] = None,
    ) -> RollbackResult:
        """Rollback to target time, apply hit, and re-simulate to present.

        This is the main entry point for processing delayed hits.

        Args:
            game_engine: The game engine to rollback
            target_timestamp: When the hit actually occurred
            hit_applicator: Callable that applies the hit to current state
            current_timestamp: Current time (defaults to time.monotonic())

        Returns:
            RollbackResult with success status and statistics
        """
        if current_timestamp is None:
            current_timestamp = time.monotonic()

        # Find snapshot to restore from
        snapshot = self.find_snapshot(target_timestamp)
        if snapshot is None:
            return RollbackResult(
                success=False,
                error=f"No snapshot available for timestamp {target_timestamp}",
            )

        # Calculate how old the snapshot is
        snapshot_age_ms = (target_timestamp - snapshot.timestamp) * 1000

        # Restore to snapshot
        self.restore(game_engine, snapshot)

        # Apply the hit at the restored state
        hit_applicator()

        # Re-simulate from snapshot time to current time
        frames = self._resimulate(
            game_engine,
            from_time=snapshot.elapsed_time,
            to_elapsed=(current_timestamp - snapshot.timestamp) + snapshot.elapsed_time,
        )

        self._total_rollbacks += 1

        return RollbackResult(
            success=True,
            frames_resimulated=frames,
            snapshot_age_ms=snapshot_age_ms,
        )

    def _resimulate(
        self,
        game_engine: 'GameEngine',
        from_time: float,
        to_elapsed: float,
    ) -> int:
        """Re-simulate game state from one time to another.

        Uses fixed timestep for determinism.

        Args:
            game_engine: The game engine to simulate
            from_time: Starting elapsed time
            to_elapsed: Target elapsed time

        Returns:
            Number of frames simulated
        """
        dt = 1.0 / self.fps
        frames = 0

        lua_engine = game_engine._behavior_engine
        current_elapsed = from_time

        while current_elapsed < to_elapsed:
            # Run one frame of game logic
            # Use the engine's internal update that doesn't capture snapshots
            game_engine._do_frame_update(dt)
            current_elapsed += dt
            frames += 1

            # Safety limit to prevent infinite loops
            if frames > self.fps * self.history_duration * 2:
                break

        return frames

    def clear(self) -> None:
        """Clear all stored snapshots."""
        self._snapshots.clear()
        self._frame_counter = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about rollback manager state.

        Returns:
            Dict with snapshot count, time span, capture/rollback counts
        """
        time_span = 0.0
        if self._snapshots and len(self._snapshots) >= 2:
            time_span = self._snapshots[-1].timestamp - self._snapshots[0].timestamp

        return {
            'snapshot_count': len(self._snapshots),
            'max_snapshots': self.max_snapshots,
            'time_span_seconds': time_span,
            'oldest_frame': self._snapshots[0].frame_number if self._snapshots else None,
            'newest_frame': self._snapshots[-1].frame_number if self._snapshots else None,
            'total_captures': self._total_captures,
            'total_rollbacks': self._total_rollbacks,
            'frame_counter': self._frame_counter,
        }
