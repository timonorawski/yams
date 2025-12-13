"""Test Detection Backend for automated game testing.

Provides a scriptable detection backend that can:
- Emit events at specific times and positions
- Run headlessly for fast testing
- Capture game state for assertions
- Generate test reports

Usage:
    from ams.test_backend import TestDetectionBackend, GameTestHarness

    # Create backend with scripted events
    backend = TestDetectionBackend(800, 600)
    backend.schedule_click(0.5, 400, 300)  # Click center at t=0.5s
    backend.schedule_click(1.0, 100, 100)  # Click top-left at t=1.0s

    # Run game with harness
    harness = GameTestHarness(game_class, backend)
    result = harness.run(duration=2.0)

    # Check results
    assert result.final_score > 0
    assert "ball" in result.entities_at_end
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import time

from ams.detection_backend import DetectionBackend
from ams.events import PlaneHitEvent, CalibrationResult


@dataclass
class ScheduledEvent:
    """An event scheduled to fire at a specific time."""
    time: float  # Seconds from start
    x: float     # Normalized [0, 1]
    y: float     # Normalized [0, 1]
    active: bool = True  # Whether this is a click (True) or just movement (False)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateSnapshot:
    """Captured game state at a point in time."""
    time: float
    frame: int
    score: int
    lives: int
    entities: Dict[str, Dict[str, Any]]  # entity_id -> {type, x, y, ...}
    game_state: str  # "playing", "won", "lost", etc.


@dataclass
class TestResult:
    """Result of running a game test."""
    duration: float
    frames: int
    final_score: int
    final_lives: int
    final_state: str
    entities_at_end: List[str]  # Entity types present at end
    snapshots: List[StateSnapshot]
    events_fired: int
    errors: List[str]

    @property
    def success(self) -> bool:
        """Test succeeded if no errors and game didn't crash."""
        return len(self.errors) == 0

    def get_entity_history(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get all snapshots of entities of a given type."""
        history = []
        for snap in self.snapshots:
            for eid, edata in snap.entities.items():
                if edata.get("type") == entity_type:
                    history.append({"time": snap.time, "frame": snap.frame, **edata})
        return history


class TestDetectionBackend(DetectionBackend):
    """Detection backend for automated testing.

    Emits pre-scheduled events at specific times, enabling deterministic
    testing of game behavior.

    Features:
    - Schedule clicks/movements at specific times and positions
    - Track pointer position continuously (for pointer-following entities)
    - Query elapsed time for synchronization
    """

    def __init__(self, display_width: int = 800, display_height: int = 600):
        super().__init__(display_width, display_height)
        self._scheduled: List[ScheduledEvent] = []
        self._elapsed: float = 0.0
        self._last_event_index: int = 0
        self._pointer_x: float = 0.5  # Normalized
        self._pointer_y: float = 0.5
        self._pointer_active: bool = False

    def reset(self) -> None:
        """Reset timing state (keeps scheduled events)."""
        self._elapsed = 0.0
        self._last_event_index = 0

    def clear_events(self) -> None:
        """Clear all scheduled events."""
        self._scheduled.clear()
        self._last_event_index = 0

    def schedule_click(
        self,
        time: float,
        x: float,
        y: float,
        normalized: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Schedule a click event.

        Args:
            time: Seconds from test start
            x: X coordinate (pixels if not normalized, [0,1] if normalized)
            y: Y coordinate (pixels if not normalized, [0,1] if normalized)
            normalized: If True, x/y are already in [0,1] range
            metadata: Optional metadata to attach to event
        """
        if normalized:
            norm_x, norm_y = x, y
        else:
            norm_x, norm_y = self.normalize_coordinates(x, y)

        event = ScheduledEvent(
            time=time,
            x=norm_x,
            y=norm_y,
            active=True,
            metadata=metadata or {}
        )
        self._scheduled.append(event)
        self._scheduled.sort(key=lambda e: e.time)

    def schedule_move(
        self,
        time: float,
        x: float,
        y: float,
        normalized: bool = False
    ) -> None:
        """Schedule a pointer movement (no click).

        Args:
            time: Seconds from test start
            x: X coordinate (pixels if not normalized)
            y: Y coordinate (pixels if not normalized)
            normalized: If True, x/y are already in [0,1] range
        """
        if normalized:
            norm_x, norm_y = x, y
        else:
            norm_x, norm_y = self.normalize_coordinates(x, y)

        event = ScheduledEvent(
            time=time,
            x=norm_x,
            y=norm_y,
            active=False
        )
        self._scheduled.append(event)
        self._scheduled.sort(key=lambda e: e.time)

    def set_pointer(self, x: float, y: float, active: bool = False) -> None:
        """Set current pointer position (for continuous tracking)."""
        self._pointer_x, self._pointer_y = self.normalize_coordinates(x, y)
        self._pointer_active = active

    def get_pointer(self) -> Tuple[float, float, bool]:
        """Get current pointer state (x, y, active)."""
        return (
            self._pointer_x * self.display_width,
            self._pointer_y * self.display_height,
            self._pointer_active
        )

    @property
    def elapsed(self) -> float:
        """Get elapsed time since test start."""
        return self._elapsed

    def poll_events(self) -> List[PlaneHitEvent]:
        """Get events that should fire at current time."""
        events = []

        # Reset active state each frame (clicks are momentary)
        # Pointer position persists, but active only lasts one frame
        was_active = self._pointer_active
        self._pointer_active = False

        while self._last_event_index < len(self._scheduled):
            scheduled = self._scheduled[self._last_event_index]
            if scheduled.time <= self._elapsed:
                # Update pointer position
                self._pointer_x = scheduled.x
                self._pointer_y = scheduled.y
                self._pointer_active = scheduled.active

                # Only emit PlaneHitEvent for clicks
                if scheduled.active:
                    event = PlaneHitEvent(
                        x=scheduled.x,
                        y=scheduled.y,
                        timestamp=time.time(),
                        confidence=1.0,
                        detection_method="test_backend",
                        latency_ms=0.0,
                        metadata=scheduled.metadata
                    )
                    events.append(event)

                self._last_event_index += 1
            else:
                break

        return events

    def update(self, dt: float) -> None:
        """Advance time."""
        self._elapsed += dt

    def calibrate(self) -> CalibrationResult:
        """No-op calibration."""
        return CalibrationResult(
            success=True,
            method="test_backend_no_op",
            notes="Test backend doesn't require calibration"
        )

    def get_backend_info(self) -> dict:
        info = super().get_backend_info()
        info['scheduled_events'] = len(self._scheduled)
        info['elapsed_time'] = self._elapsed
        return info


class GameTestHarness:
    """Harness for running automated game tests.

    Runs a game headlessly with a TestDetectionBackend, capturing
    state snapshots for analysis.

    Usage:
        harness = GameTestHarness("BrickBreakerUltimate")
        harness.backend.schedule_click(0.5, 400, 550)  # Click paddle area
        result = harness.run(duration=5.0, snapshot_interval=0.1)

        # Analyze results
        print(f"Final score: {result.final_score}")
        ball_history = result.get_entity_history("ball")
    """

    def __init__(
        self,
        game_name: str,
        width: int = 800,
        height: int = 600,
        headless: bool = True
    ):
        """Initialize test harness.

        Args:
            game_name: Name of game to test (from registry)
            width: Display width
            height: Display height
            headless: If True, skip rendering (faster)
        """
        self.game_name = game_name
        self.width = width
        self.height = height
        self.headless = headless
        self.backend = TestDetectionBackend(width, height)

        self._game = None
        self._snapshots: List[StateSnapshot] = []
        self._errors: List[str] = []

    def _create_game(self):
        """Create game instance from registry."""
        from pathlib import Path
        from ams.content_fs import ContentFS
        from games.registry import get_registry

        # Create ContentFS with project root as core directory
        core_dir = Path(__file__).parent.parent  # ams/ -> project root
        content_fs = ContentFS(core_dir)

        registry = get_registry(content_fs)

        # Use registry's create_game method
        return registry.create_game(
            slug=self.game_name,
            width=self.width,
            height=self.height,
        )

    def _capture_snapshot(self, frame: int) -> StateSnapshot:
        """Capture current game state."""
        entities = {}

        # Get entities from game's behavior engine (GameEngine)
        if hasattr(self._game, '_behavior_engine'):
            for entity in self._game._behavior_engine.get_alive_entities():
                entities[entity.id] = {
                    "type": entity.entity_type,
                    "x": entity.x,
                    "y": entity.y,
                    "vx": getattr(entity, 'vx', 0),
                    "vy": getattr(entity, 'vy', 0),
                }
        # Fallback: try lua engine directly
        elif hasattr(self._game, '_lua') and self._game._lua:
            for entity in self._game._lua.get_all_entities():
                entities[entity.id] = {
                    "type": entity.entity_type,
                    "x": entity.x,
                    "y": entity.y,
                    "vx": getattr(entity, 'vx', 0),
                    "vy": getattr(entity, 'vy', 0),
                }

        # Get game state
        game_state = "playing"
        if hasattr(self._game, 'state'):
            game_state = str(self._game.state)
        elif hasattr(self._game, '_get_internal_state'):
            game_state = str(self._game._get_internal_state())

        # Get score and lives
        score = self._game.get_score() if hasattr(self._game, 'get_score') else 0
        lives = 3
        if hasattr(self._game, '_lives'):
            lives = self._game._lives
        elif hasattr(self._game, 'lives'):
            lives = self._game.lives

        return StateSnapshot(
            time=self.backend.elapsed,
            frame=frame,
            score=score,
            lives=lives,
            entities=entities,
            game_state=game_state
        )

    def run(
        self,
        duration: float = 5.0,
        dt: float = 1/60,
        snapshot_interval: float = 0.1,
        stop_on_game_over: bool = True
    ) -> TestResult:
        """Run the game test.

        Args:
            duration: Maximum test duration in seconds
            dt: Time step per frame (default 60fps)
            snapshot_interval: How often to capture state (seconds)
            stop_on_game_over: Stop early if game ends

        Returns:
            TestResult with captured data
        """
        import pygame

        # Initialize pygame minimally
        if not pygame.get_init():
            pygame.init()

        # Create a small hidden surface for headless mode
        if self.headless:
            screen = pygame.Surface((self.width, self.height))
        else:
            screen = pygame.display.set_mode((self.width, self.height))

        # Create game
        try:
            self._game = self._create_game()
        except Exception as e:
            self._errors.append(f"Failed to create game: {e}")
            return TestResult(
                duration=0,
                frames=0,
                final_score=0,
                final_lives=0,
                final_state="error",
                entities_at_end=[],
                snapshots=[],
                events_fired=0,
                errors=self._errors
            )

        # Reset backend timing
        self.backend.reset()
        self._snapshots = []

        frame = 0
        events_fired = 0
        last_snapshot = -snapshot_interval

        # Run game loop
        while self.backend.elapsed < duration:
            # Update backend (advances time)
            self.backend.update(dt)

            # Poll events from backend
            events = self.backend.poll_events()
            events_fired += len(events)

            # Update pointer in game's interaction engine
            if hasattr(self._game, '_interaction_engine'):
                px, py, active = self.backend.get_pointer()
                self._game._interaction_engine.update_pointer(px, py, active)

            # Convert to InputEvents and pass to game
            if events and hasattr(self._game, 'handle_input'):
                from ams.games.input.input_event import InputEvent
                from models import Vector2D, EventType
                input_events = []
                for e in events:
                    ie = InputEvent(
                        position=Vector2D(x=e.x * self.width, y=e.y * self.height),
                        timestamp=e.timestamp,
                        event_type=EventType.HIT
                    )
                    input_events.append(ie)
                try:
                    self._game.handle_input(input_events)
                except Exception as ex:
                    self._errors.append(f"Frame {frame}: handle_input error: {ex}")

            # Update game
            try:
                self._game.update(dt)
            except Exception as e:
                self._errors.append(f"Frame {frame}: update error: {e}")

            # Capture snapshot periodically
            if self.backend.elapsed - last_snapshot >= snapshot_interval:
                try:
                    snapshot = self._capture_snapshot(frame)
                    self._snapshots.append(snapshot)
                    last_snapshot = self.backend.elapsed
                except Exception as e:
                    self._errors.append(f"Frame {frame}: snapshot error: {e}")

            # Render (even headless, to ensure render code runs)
            if not self.headless:
                try:
                    self._game.render(screen)
                    pygame.display.flip()
                except Exception as e:
                    self._errors.append(f"Frame {frame}: render error: {e}")

            # Check for game over
            if stop_on_game_over:
                state = self._snapshots[-1].game_state if self._snapshots else "playing"
                if state in ("won", "lost", "game_over", "GameState.WON", "GameState.LOST"):
                    break

            frame += 1

        # Final snapshot
        try:
            final_snap = self._capture_snapshot(frame)
            self._snapshots.append(final_snap)
        except:
            final_snap = self._snapshots[-1] if self._snapshots else StateSnapshot(
                time=0, frame=0, score=0, lives=0, entities={}, game_state="error"
            )

        # Build result
        entities_at_end = list(set(
            e["type"] for e in final_snap.entities.values()
        )) if final_snap.entities else []

        return TestResult(
            duration=self.backend.elapsed,
            frames=frame,
            final_score=final_snap.score,
            final_lives=final_snap.lives,
            final_state=final_snap.game_state,
            entities_at_end=entities_at_end,
            snapshots=self._snapshots,
            events_fired=events_fired,
            errors=self._errors
        )


def run_quick_test(game_name: str, duration: float = 3.0) -> TestResult:
    """Quick helper to run a basic test on a game.

    Args:
        game_name: Name of game to test
        duration: How long to run (seconds)

    Returns:
        TestResult
    """
    harness = GameTestHarness(game_name, headless=True)
    # Schedule a click in the center at 0.5s
    harness.backend.schedule_click(0.5, 400, 300)
    return harness.run(duration=duration)


if __name__ == "__main__":
    # Test the backend itself
    print("Testing TestDetectionBackend...")

    backend = TestDetectionBackend(800, 600)
    backend.schedule_click(0.1, 100, 100)
    backend.schedule_click(0.2, 200, 200)
    backend.schedule_move(0.15, 150, 150)

    print(f"Scheduled {len(backend._scheduled)} events")

    # Simulate time
    for i in range(30):  # 30 frames at 60fps = 0.5s
        backend.update(1/60)
        events = backend.poll_events()
        if events:
            for e in events:
                print(f"  t={backend.elapsed:.3f}s: Click at ({e.x:.2f}, {e.y:.2f})")

    print(f"\nFinal elapsed: {backend.elapsed:.3f}s")
    print("TestDetectionBackend works!")
