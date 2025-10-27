"""
Temporal Game State Management

Provides automatic state history maintenance for games that need to handle
detection latency and projectile flight time.

Key Concept: "Games query the past"
- Detection happens AFTER game state has advanced (latency + flight time)
- Games maintain a rolling window of state history
- When hit event arrives, game queries its own history to determine if it was a hit
- Decouples detection timing from game timing

Usage:
    class MyGame(TemporalGameState):
        def __init__(self):
            super().__init__(history_duration=5.0, fps=60)
            self.targets = []

        def update(self, dt):
            # Game logic updates current state
            self.move_targets(dt)

            # Capture state snapshot automatically
            super().update(dt)

        def get_current_state_snapshot(self):
            # Return deep copy of current state
            return {
                'targets': [t.copy() for t in self.targets],
                # ... other game state
            }

        def check_hit_in_snapshot(self, snapshot, x, y):
            # Query specific snapshot for hit
            for target in snapshot['targets']:
                if target.contains(x, y):
                    return HitResult(hit=True, target_id=target.id, ...)
            return HitResult(hit=False)
"""

from collections import deque
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import time
import copy

from ams.events import HitResult


class StateSnapshot:
    """
    Single snapshot of game state at a moment in time.

    Stores both the timestamp and frame number for flexible querying.
    """

    def __init__(
        self,
        frame: int,
        timestamp: float,
        state_data: Dict[str, Any]
    ):
        """
        Create a state snapshot.

        Args:
            frame: Frame number
            timestamp: Timestamp when this state was active
            state_data: Deep copy of game state
        """
        self.frame = frame
        self.timestamp = timestamp
        self.state_data = state_data


class TemporalGameState(ABC):
    """
    Base class for games that need temporal hit detection.

    Automatically maintains a rolling window of game state history.
    Subclasses implement:
    - get_current_state_snapshot(): Return current state
    - check_hit_in_snapshot(): Query a snapshot for hits

    The base class handles:
    - History management (automatic snapshots each frame)
    - Temporal queries (find state at a specific time)
    - Memory management (rolling window, old states discarded)
    """

    def __init__(
        self,
        history_duration: float = 5.0,
        fps: int = 60,
        auto_snapshot: bool = True
    ):
        """
        Initialize temporal state management.

        Args:
            history_duration: How many seconds of history to maintain
            fps: Expected frame rate (for calculating buffer size)
            auto_snapshot: Whether to automatically capture state in update()
        """
        self.history_duration = history_duration
        self.fps = fps
        self.auto_snapshot = auto_snapshot

        # Calculate buffer size
        max_snapshots = int(history_duration * fps)
        self.history: deque[StateSnapshot] = deque(maxlen=max_snapshots)

        # Frame tracking
        self.frame_counter = 0
        self.game_start_time = time.time()

    def update(self, dt: float):
        """
        Called each frame to update game state.

        If auto_snapshot is enabled, captures current state automatically.
        Subclasses should call super().update(dt) after updating their state.

        Args:
            dt: Delta time since last frame (seconds)
        """
        if self.auto_snapshot:
            self.capture_snapshot()

        self.frame_counter += 1

    def capture_snapshot(self):
        """
        Capture current game state into history.

        Called automatically by update() if auto_snapshot is True.
        Can be called manually for finer control over snapshot timing.
        """
        state_data = self.get_current_state_snapshot()

        snapshot = StateSnapshot(
            frame=self.frame_counter,
            timestamp=time.monotonic(),  # Use monotonic time to match input events
            state_data=state_data
        )

        self.history.append(snapshot)

    @abstractmethod
    def get_current_state_snapshot(self) -> Dict[str, Any]:
        """
        Return a deep copy of current game state.

        MUST be implemented by subclasses.

        Returns:
            Dictionary containing all state needed to check hits.
            Must be a DEEP COPY - modifying returned dict should not affect game state.

        Example:
            return {
                'targets': [t.copy() for t in self.targets],
                'obstacles': [o.copy() for o in self.obstacles],
                'active_powerups': self.powerups.copy()
            }
        """
        pass

    @abstractmethod
    def check_hit_in_snapshot(
        self,
        snapshot: Dict[str, Any],
        x: float,
        y: float
    ) -> HitResult:
        """
        Check if coordinates hit anything in a specific state snapshot.

        MUST be implemented by subclasses.

        Args:
            snapshot: State snapshot (from get_current_state_snapshot())
            x: Normalized x coordinate [0, 1]
            y: Normalized y coordinate [0, 1]

        Returns:
            HitResult with hit status, target info, points, etc.

        Example:
            for target in snapshot['targets']:
                if target.contains(x, y):
                    return HitResult(
                        hit=True,
                        target_id=target.id,
                        points=target.points
                    )
            return HitResult(hit=False)
        """
        pass

    def was_target_hit(
        self,
        x: float,
        y: float,
        query_time: Optional[Union[float, int]] = None,
        latency_ms: float = 0.0
    ) -> HitResult:
        """
        Query: Was (x, y) a hit at the specified time or frame?

        This is the main temporal query interface. Games call this when
        they receive a PlaneHitEvent to determine if it was a hit.

        Args:
            x: Normalized x coordinate [0, 1]
            y: Normalized y coordinate [0, 1]
            query_time: Either:
                - float: timestamp (seconds since epoch)
                - int: frame number
                - None: use current state
            latency_ms: Detection latency in milliseconds (0 for mouse, ~150 for CV)

        Returns:
            HitResult indicating whether this was a hit in that state

        Example:
            # Detection event arrives
            event = PlaneHitEvent(x=0.5, y=0.3, timestamp=123.456)

            # Query game state at that timestamp, adjusted for detection latency
            result = self.was_target_hit(event.x, event.y, event.timestamp, latency_ms=150)

            if result.hit:
                self.award_points(result.points)
        """
        # Adjust query time for detection latency
        adjusted_time = query_time
        if isinstance(query_time, float) and latency_ms > 0:
            adjusted_time = query_time - (latency_ms / 1000.0)

        # Use current state if no query time specified
        if adjusted_time is None:
            snapshot_state = self.get_current_state_snapshot()
            return self.check_hit_in_snapshot(snapshot_state, x, y)

        # Check if query is for current/future time (after latest snapshot)
        if self.history:
            latest_snapshot = self.history[-1]
            if adjusted_time >= latest_snapshot.timestamp:
                # Query is for current or future state - use current state
                snapshot_state = self.get_current_state_snapshot()
                return self.check_hit_in_snapshot(snapshot_state, x, y)

        # Find the closest snapshot to query time
        snapshot = self._get_closest_snapshot(adjusted_time)

        if snapshot is None:
            # No history available - use current state
            snapshot_state = self.get_current_state_snapshot()
            return self.check_hit_in_snapshot(snapshot_state, x, y)

        # Check hit in that snapshot
        result = self.check_hit_in_snapshot(snapshot.state_data, x, y)

        # Add frame/state info to result
        result.frame = snapshot.frame
        result.game_state = f"frame_{snapshot.frame}"

        return result

    def _get_closest_snapshot(
        self,
        query_time: Union[float, int]
    ) -> Optional[StateSnapshot]:
        """
        Find snapshot closest to specified time or frame.

        Args:
            query_time: Either timestamp (float) or frame (int)

        Returns:
            Closest StateSnapshot, or None if no history available
        """
        if not self.history:
            return None

        # Integer = frame number
        if isinstance(query_time, int):
            return self._find_snapshot_by_frame(query_time)

        # Float = timestamp - find closest in absolute time
        best_snapshot = None
        best_distance = float('inf')

        for snapshot in self.history:
            distance = abs(snapshot.timestamp - query_time)
            if distance < best_distance:
                best_distance = distance
                best_snapshot = snapshot

        return best_snapshot

    def _is_query_current(self, query_time: Union[float, int]) -> bool:
        """
        Check if query time is recent enough to use current state.

        For zero-latency input (mouse, keyboard), queries are always "current"
        since the event arrives at the same time as the visible game state.

        For CV detection with latency, queries look back in history.

        Args:
            query_time: Either timestamp (float) or frame (int)

        Returns:
            True if query should use current state instead of history
        """
        if not self.history:
            return True  # No history, must use current

        latest_snapshot = self.history[-1]

        if isinstance(query_time, int):
            # Frame number - current if at or after latest snapshot
            return query_time >= latest_snapshot.frame

        # Timestamp - current if at or after latest snapshot
        # (Zero-latency input like mouse will always be current or future)
        return query_time >= latest_snapshot.timestamp

    def _get_snapshot_at(
        self,
        query_time: Optional[Union[float, int]]
    ) -> Optional[StateSnapshot]:
        """
        Find the snapshot closest to the specified time or frame.

        Args:
            query_time: Either timestamp (float), frame (int), or None (latest)

        Returns:
            Closest StateSnapshot, or None if no history available
        """
        if not self.history:
            return None

        # No query time specified - use latest
        if query_time is None:
            return self.history[-1]

        # Integer = frame number
        if isinstance(query_time, int):
            return self._find_snapshot_by_frame(query_time)

        # Float = timestamp
        return self._find_snapshot_by_timestamp(query_time)

    def _find_snapshot_by_frame(self, frame: int) -> Optional[StateSnapshot]:
        """Find snapshot for specific frame number."""
        # Binary search would be faster, but history is small enough
        # that linear search is fine and simpler
        best_snapshot = None
        best_distance = float('inf')

        for snapshot in self.history:
            distance = abs(snapshot.frame - frame)
            if distance < best_distance:
                best_distance = distance
                best_snapshot = snapshot

        return best_snapshot

    def _find_snapshot_by_timestamp(self, timestamp: float) -> Optional[StateSnapshot]:
        """
        Find snapshot closest to specific timestamp.

        If query timestamp is very recent (within last frame), returns most
        recent snapshot to avoid temporal mismatch with newly spawned objects.
        """
        if not self.history:
            return None

        latest_snapshot = self.history[-1]

        # If querying very recent time (within one frame), use latest snapshot
        # This prevents misses on objects that just spawned
        time_since_latest = timestamp - latest_snapshot.timestamp
        frame_time = 1.0 / self.fps

        if 0 <= time_since_latest < frame_time * 2:
            # Query is for current or very recent state - use latest snapshot
            return latest_snapshot

        # Otherwise, find closest historical snapshot
        best_snapshot = None
        best_distance = float('inf')

        for snapshot in self.history:
            distance = abs(snapshot.timestamp - timestamp)
            if distance < best_distance:
                best_distance = distance
                best_snapshot = snapshot

        return best_snapshot

    def get_history_stats(self) -> Dict[str, Any]:
        """
        Get statistics about state history for debugging.

        Returns:
            Dict with history size, time span, etc.
        """
        if not self.history:
            return {
                'snapshots': 0,
                'time_span': 0.0,
                'frames_span': 0
            }

        oldest = self.history[0]
        newest = self.history[-1]

        return {
            'snapshots': len(self.history),
            'time_span': newest.timestamp - oldest.timestamp,
            'frames_span': newest.frame - oldest.frame,
            'oldest_frame': oldest.frame,
            'newest_frame': newest.frame,
            'buffer_size': self.history.maxlen
        }


if __name__ == "__main__":
    # Example usage with a simple target game
    from dataclasses import dataclass

    @dataclass
    class SimpleTarget:
        x: float
        y: float
        radius: float
        points: int

        def contains(self, x: float, y: float) -> bool:
            dx = x - self.x
            dy = y - self.y
            return (dx*dx + dy*dy) < (self.radius * self.radius)

        def copy(self):
            return SimpleTarget(self.x, self.y, self.radius, self.points)

    class ExampleGame(TemporalGameState):
        def __init__(self):
            super().__init__(history_duration=5.0, fps=60)
            self.targets = [
                SimpleTarget(x=0.5, y=0.5, radius=0.1, points=100)
            ]

        def update(self, dt):
            # Move targets (example game logic)
            for target in self.targets:
                target.x += 0.01 * dt  # Drift right slowly

            # Capture state
            super().update(dt)

        def get_current_state_snapshot(self):
            return {
                'targets': [t.copy() for t in self.targets]
            }

        def check_hit_in_snapshot(self, snapshot, x, y):
            for target in snapshot['targets']:
                if target.contains(x, y):
                    return HitResult(
                        hit=True,
                        target_id=f"target_{id(target)}",
                        points=target.points,
                        message="Direct hit!"
                    )
            return HitResult(hit=False, message="Miss")

    # Test
    game = ExampleGame()

    # Simulate some frames
    for i in range(100):
        game.update(0.016)  # ~60fps

    # Query current state
    result = game.was_target_hit(0.5, 0.5)
    print(f"Hit test at (0.5, 0.5): {result.hit} - {result.message}")

    # Query past state (50 frames ago)
    result_past = game.was_target_hit(0.5, 0.5, query_time=game.frame_counter - 50)
    print(f"Hit test 50 frames ago: {result_past.hit}")

    # Stats
    stats = game.get_history_stats()
    print(f"\nHistory stats:")
    print(f"  Snapshots: {stats['snapshots']}")
    print(f"  Time span: {stats['time_span']:.2f}s")
    print(f"  Frames: {stats['frames_span']}")
