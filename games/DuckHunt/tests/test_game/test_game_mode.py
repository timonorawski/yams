"""
Tests for GameMode base class.

Tests the abstract base class interface and verifies that concrete
implementations properly implement required methods.
"""

import pytest
import pygame
from typing import List
from abc import ABC

from game.game_mode import GameMode
from game.target import Target
from input.input_event import InputEvent
from models import (
    GameState, TargetState, TargetData, Vector2D, EventType
)


class TestGameModeABC:
    """Test that GameMode is properly abstract."""

    def test_cannot_instantiate_abstract_class(self):
        """GameMode is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            GameMode()

    def test_is_abc_subclass(self):
        """GameMode should be a subclass of ABC."""
        assert issubclass(GameMode, ABC)

    def test_has_abstract_methods(self):
        """GameMode should have required abstract methods."""
        # Get abstract methods
        abstract_methods = GameMode.__abstractmethods__

        # Check all required abstract methods are present
        assert 'update' in abstract_methods
        assert 'handle_input' in abstract_methods
        assert 'render' in abstract_methods


class MockGameMode(GameMode):
    """Concrete implementation of GameMode for testing.

    This mock implementation provides minimal but valid implementations
    of all abstract methods for testing the base class functionality.
    """

    def __init__(self):
        """Initialize mock game mode."""
        super().__init__()
        self._score = 0
        self.update_called = False
        self.handle_input_called = False
        self.render_called = False
        self.last_dt = None
        self.last_events = None

    def update(self, dt: float) -> None:
        """Mock update implementation."""
        self.update_called = True
        self.last_dt = dt
        # Update all targets
        self._targets = [t.update(dt) for t in self._targets]

    def handle_input(self, events: List[InputEvent]) -> None:
        """Mock input handler implementation."""
        self.handle_input_called = True
        self.last_events = events
        # Simple hit detection
        for event in events:
            for i, target in enumerate(self._targets):
                if target.is_active and target.contains_point(event.position):
                    self._targets[i] = target.set_state(TargetState.HIT)
                    self._score += 10
                    break

    def render(self, screen: pygame.Surface) -> None:
        """Mock render implementation."""
        self.render_called = True
        # Render all targets
        for target in self._targets:
            target.render(screen)

    def get_score(self) -> int:
        """Return mock score."""
        return self._score


class TestGameModeBase:
    """Test GameMode base class functionality."""

    def test_initialization(self):
        """GameMode initializes with empty targets and PLAYING state."""
        mode = MockGameMode()

        assert mode.targets == []
        assert mode.state == GameState.PLAYING

    def test_targets_property(self):
        """targets property returns the list of targets."""
        mode = MockGameMode()

        # Initially empty
        assert mode.targets == []

        # Add a target
        target_data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=50.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(target_data)
        mode._targets.append(target)

        # Should be accessible via property
        assert len(mode.targets) == 1
        assert mode.targets[0] is target

    def test_state_property(self):
        """state property returns current game state."""
        mode = MockGameMode()

        # Initial state
        assert mode.state == GameState.PLAYING

        # Change state
        mode._state = GameState.GAME_OVER
        assert mode.state == GameState.GAME_OVER

    def test_update_method_called(self):
        """update() method is called with correct parameters."""
        mode = MockGameMode()

        dt = 0.016  # ~60 FPS
        mode.update(dt)

        assert mode.update_called is True
        assert mode.last_dt == dt

    def test_update_modifies_targets(self):
        """update() can modify target positions."""
        mode = MockGameMode()

        # Add a moving target
        target_data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=50.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        mode._targets.append(Target(target_data))

        # Update for 1 second
        mode.update(1.0)

        # Position should have changed
        assert mode.targets[0].data.position.x == 150.0
        assert mode.targets[0].data.position.y == 100.0

    def test_handle_input_method_called(self):
        """handle_input() is called with correct parameters."""
        mode = MockGameMode()

        events = [
            InputEvent(
                position=Vector2D(x=100.0, y=100.0),
                timestamp=1.0,
                event_type=EventType.HIT
            )
        ]

        mode.handle_input(events)

        assert mode.handle_input_called is True
        assert mode.last_events == events

    def test_handle_input_empty_events(self):
        """handle_input() works with empty event list."""
        mode = MockGameMode()

        mode.handle_input([])

        assert mode.handle_input_called is True
        assert mode.last_events == []

    def test_handle_input_hit_detection(self):
        """handle_input() can detect hits on targets."""
        mode = MockGameMode()

        # Add a target
        target_data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        mode._targets.append(Target(target_data))

        # Create a hit event at target center
        events = [
            InputEvent(
                position=Vector2D(x=100.0, y=100.0),
                timestamp=1.0,
                event_type=EventType.HIT
            )
        ]

        mode.handle_input(events)

        # Target should be hit
        assert mode.targets[0].data.state == TargetState.HIT
        assert mode.get_score() == 10

    def test_handle_input_miss(self):
        """handle_input() doesn't affect targets when missing."""
        mode = MockGameMode()

        # Add a target
        target_data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        mode._targets.append(Target(target_data))

        # Create a miss event far from target
        events = [
            InputEvent(
                position=Vector2D(x=500.0, y=500.0),
                timestamp=1.0,
                event_type=EventType.MISS
            )
        ]

        mode.handle_input(events)

        # Target should still be alive
        assert mode.targets[0].data.state == TargetState.ALIVE
        assert mode.get_score() == 0

    def test_render_method_called(self):
        """render() is called with pygame surface."""
        mode = MockGameMode()

        # Initialize pygame for surface creation
        pygame.init()
        screen = pygame.Surface((800, 600))

        mode.render(screen)

        assert mode.render_called is True

        pygame.quit()

    def test_get_score_default(self):
        """get_score() returns 0 by default."""
        mode = MockGameMode()
        assert mode.get_score() == 0

    def test_get_score_tracks_hits(self):
        """get_score() reflects score changes from hits."""
        mode = MockGameMode()

        # Add target
        target_data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        mode._targets.append(Target(target_data))

        # Hit the target
        events = [
            InputEvent(
                position=Vector2D(x=100.0, y=100.0),
                timestamp=1.0,
                event_type=EventType.HIT
            )
        ]
        mode.handle_input(events)

        assert mode.get_score() == 10


class TestGameModeMultipleTargets:
    """Test GameMode with multiple targets."""

    def test_multiple_targets_update(self):
        """All targets are updated correctly."""
        mode = MockGameMode()

        # Add multiple targets with different velocities
        for i in range(3):
            target_data = TargetData(
                position=Vector2D(x=100.0 * i, y=100.0),
                velocity=Vector2D(x=50.0 * (i + 1), y=0.0),
                size=40.0,
                state=TargetState.ALIVE
            )
            mode._targets.append(Target(target_data))

        # Update for 1 second
        mode.update(1.0)

        # Each target should have moved by its velocity
        assert mode.targets[0].data.position.x == 50.0   # 0 + 50
        assert mode.targets[1].data.position.x == 200.0  # 100 + 100
        assert mode.targets[2].data.position.x == 350.0  # 200 + 150

    def test_hit_only_one_target(self):
        """Input event hits only one target even if multiple overlap."""
        mode = MockGameMode()

        # Add two overlapping targets
        for _ in range(2):
            target_data = TargetData(
                position=Vector2D(x=100.0, y=100.0),
                velocity=Vector2D(x=0.0, y=0.0),
                size=40.0,
                state=TargetState.ALIVE
            )
            mode._targets.append(Target(target_data))

        # Hit at the overlapping position
        events = [
            InputEvent(
                position=Vector2D(x=100.0, y=100.0),
                timestamp=1.0,
                event_type=EventType.HIT
            )
        ]
        mode.handle_input(events)

        # Only one target should be hit (first one due to break)
        hit_count = sum(1 for t in mode.targets if t.data.state == TargetState.HIT)
        assert hit_count == 1
        assert mode.get_score() == 10

    def test_multiple_events_multiple_targets(self):
        """Multiple events can hit multiple targets."""
        mode = MockGameMode()

        # Add targets at different positions
        positions = [
            Vector2D(x=100.0, y=100.0),
            Vector2D(x=200.0, y=200.0),
            Vector2D(x=300.0, y=300.0)
        ]

        for pos in positions:
            target_data = TargetData(
                position=pos,
                velocity=Vector2D(x=0.0, y=0.0),
                size=40.0,
                state=TargetState.ALIVE
            )
            mode._targets.append(Target(target_data))

        # Hit each target
        events = [
            InputEvent(position=pos, timestamp=float(i), event_type=EventType.HIT)
            for i, pos in enumerate(positions)
        ]
        mode.handle_input(events)

        # All targets should be hit
        hit_count = sum(1 for t in mode.targets if t.data.state == TargetState.HIT)
        assert hit_count == 3
        assert mode.get_score() == 30


class TestGameModeStateManagement:
    """Test game state management."""

    def test_initial_state_playing(self):
        """Initial state should be PLAYING."""
        mode = MockGameMode()
        assert mode.state == GameState.PLAYING

    def test_can_change_state(self):
        """Game mode can transition between states."""
        mode = MockGameMode()

        # Test all state transitions
        mode._state = GameState.PAUSED
        assert mode.state == GameState.PAUSED

        mode._state = GameState.GAME_OVER
        assert mode.state == GameState.GAME_OVER

        mode._state = GameState.MENU
        assert mode.state == GameState.MENU


class TestGameModeIncomplete:
    """Test that incomplete implementations fail."""

    def test_missing_update_method(self):
        """Class missing update() cannot be instantiated."""

        class IncompleteMode(GameMode):
            def handle_input(self, events: List[InputEvent]) -> None:
                pass

            def render(self, screen: pygame.Surface) -> None:
                pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteMode()

    def test_missing_handle_input_method(self):
        """Class missing handle_input() cannot be instantiated."""

        class IncompleteMode(GameMode):
            def update(self, dt: float) -> None:
                pass

            def render(self, screen: pygame.Surface) -> None:
                pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteMode()

    def test_missing_render_method(self):
        """Class missing render() cannot be instantiated."""

        class IncompleteMode(GameMode):
            def update(self, dt: float) -> None:
                pass

            def handle_input(self, events: List[InputEvent]) -> None:
                pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteMode()
