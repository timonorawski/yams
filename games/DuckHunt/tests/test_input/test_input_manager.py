"""
Comprehensive tests for the InputManager class.

Tests cover:
- Construction with and without sources
- Source switching
- Event polling
- Update delegation
- Error handling
- Edge cases
"""

import pytest
from typing import List

from models import Vector2D, EventType
from games.DuckHunt.input.input_event import InputEvent
from games.DuckHunt.input.input_manager import InputManager
from games.DuckHunt.input.sources.base import InputSource


class MockInputSource(InputSource):
    """Mock implementation of InputSource for testing."""

    def __init__(self):
        """Initialize mock source."""
        self.events: List[InputEvent] = []
        self.update_count = 0
        self.last_dt = None

    def poll_events(self) -> List[InputEvent]:
        """Return and clear events."""
        events = self.events.copy()
        self.events.clear()
        return events

    def update(self, dt: float) -> None:
        """Track update calls."""
        self.update_count += 1
        self.last_dt = dt

    def add_event(self, event: InputEvent) -> None:
        """Helper to add test events."""
        self.events.append(event)


class NotAnInputSource:
    """Class that does not inherit from InputSource."""
    pass


class TestInputManagerConstruction:
    """Test InputManager construction."""

    def test_construction_without_source(self):
        """Test creating InputManager with no source."""
        manager = InputManager()
        assert manager.get_source() is None
        assert not manager.has_source()

    def test_construction_with_source(self):
        """Test creating InputManager with an initial source."""
        source = MockInputSource()
        manager = InputManager(source)
        assert manager.get_source() is source
        assert manager.has_source()

    def test_construction_with_none_source(self):
        """Test creating InputManager with None as source."""
        manager = InputManager(None)
        assert manager.get_source() is None
        assert not manager.has_source()


class TestInputManagerSourceManagement:
    """Test InputManager source setting and retrieval."""

    def test_set_source(self):
        """Test setting a source."""
        manager = InputManager()
        source = MockInputSource()

        manager.set_source(source)

        assert manager.get_source() is source
        assert manager.has_source()

    def test_set_source_replaces_existing(self):
        """Test that setting a source replaces the existing one."""
        source1 = MockInputSource()
        source2 = MockInputSource()
        manager = InputManager(source1)

        manager.set_source(source2)

        assert manager.get_source() is source2
        assert manager.get_source() is not source1

    def test_set_source_with_invalid_type_raises_error(self):
        """Test that setting an invalid source type raises TypeError."""
        manager = InputManager()
        invalid_source = NotAnInputSource()

        with pytest.raises(TypeError) as exc_info:
            manager.set_source(invalid_source)  # type: ignore

        assert "InputSource" in str(exc_info.value)

    def test_get_source_returns_none_when_not_set(self):
        """Test get_source returns None when no source is set."""
        manager = InputManager()
        assert manager.get_source() is None

    def test_has_source_false_when_not_set(self):
        """Test has_source returns False when no source is set."""
        manager = InputManager()
        assert not manager.has_source()

    def test_has_source_true_when_set(self):
        """Test has_source returns True when source is set."""
        manager = InputManager()
        manager.set_source(MockInputSource())
        assert manager.has_source()


class TestInputManagerUpdate:
    """Test InputManager update method."""

    def test_update_calls_source_update(self):
        """Test that update delegates to the source."""
        source = MockInputSource()
        manager = InputManager(source)

        manager.update(0.016)

        assert source.update_count == 1
        assert source.last_dt == 0.016

    def test_update_multiple_times(self):
        """Test multiple update calls."""
        source = MockInputSource()
        manager = InputManager(source)

        manager.update(0.016)
        manager.update(0.020)
        manager.update(0.014)

        assert source.update_count == 3
        assert source.last_dt == 0.014  # Last value

    def test_update_without_source_does_not_crash(self):
        """Test that update is safe to call without a source."""
        manager = InputManager()

        # Should not raise an exception
        manager.update(0.016)

    def test_update_with_zero_dt(self):
        """Test update with zero delta time."""
        source = MockInputSource()
        manager = InputManager(source)

        manager.update(0.0)

        assert source.last_dt == 0.0

    def test_update_with_large_dt(self):
        """Test update with large delta time."""
        source = MockInputSource()
        manager = InputManager(source)

        manager.update(1.0)  # 1 second frame (very slow)

        assert source.last_dt == 1.0


class TestInputManagerGetEvents:
    """Test InputManager get_events method."""

    def test_get_events_returns_source_events(self):
        """Test that get_events returns events from the source."""
        source = MockInputSource()
        manager = InputManager(source)

        # Add some test events
        event1 = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=1.0,
            event_type=EventType.HIT
        )
        event2 = InputEvent(
            position=Vector2D(x=200.0, y=200.0),
            timestamp=2.0,
            event_type=EventType.MISS
        )
        source.add_event(event1)
        source.add_event(event2)

        events = manager.get_events()

        assert len(events) == 2
        assert events[0] == event1
        assert events[1] == event2

    def test_get_events_without_source_returns_empty_list(self):
        """Test that get_events returns empty list when no source is set."""
        manager = InputManager()

        events = manager.get_events()

        assert isinstance(events, list)
        assert len(events) == 0

    def test_get_events_clears_source_queue(self):
        """Test that get_events clears the source's event queue."""
        source = MockInputSource()
        manager = InputManager(source)

        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=1.0,
            event_type=EventType.HIT
        )
        source.add_event(event)

        # First call gets the event
        first_events = manager.get_events()
        assert len(first_events) == 1

        # Second call should be empty
        second_events = manager.get_events()
        assert len(second_events) == 0

    def test_get_events_when_source_empty(self):
        """Test get_events when source has no events."""
        source = MockInputSource()
        manager = InputManager(source)

        events = manager.get_events()

        assert isinstance(events, list)
        assert len(events) == 0


class TestInputManagerClearEvents:
    """Test InputManager clear_events method."""

    def test_clear_events_removes_pending_events(self):
        """Test that clear_events removes pending events from source."""
        source = MockInputSource()
        manager = InputManager(source)

        # Add events
        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=1.0,
            event_type=EventType.HIT
        )
        source.add_event(event)

        # Clear events
        manager.clear_events()

        # Events should be gone
        events = manager.get_events()
        assert len(events) == 0

    def test_clear_events_without_source_does_not_crash(self):
        """Test that clear_events is safe to call without a source."""
        manager = InputManager()

        # Should not raise an exception
        manager.clear_events()


class TestInputManagerIntegration:
    """Integration tests for InputManager with multiple sources."""

    def test_switching_sources_mid_game(self):
        """Test switching between different sources during runtime."""
        source1 = MockInputSource()
        source2 = MockInputSource()

        manager = InputManager(source1)

        # Add events to first source
        event1 = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=1.0,
            event_type=EventType.HIT
        )
        source1.add_event(event1)

        # Switch to second source
        manager.set_source(source2)

        # Add events to second source
        event2 = InputEvent(
            position=Vector2D(x=200.0, y=200.0),
            timestamp=2.0,
            event_type=EventType.MISS
        )
        source2.add_event(event2)

        # Should get events from second source only
        events = manager.get_events()
        assert len(events) == 1
        assert events[0] == event2

    def test_update_and_get_events_workflow(self):
        """Test typical workflow of update followed by get_events."""
        source = MockInputSource()
        manager = InputManager(source)

        # Add event before update
        event = InputEvent(
            position=Vector2D(x=150.0, y=150.0),
            timestamp=1.5,
            event_type=EventType.HIT
        )
        source.add_event(event)

        # Update source
        manager.update(0.016)

        # Get events
        events = manager.get_events()

        assert len(events) == 1
        assert events[0] == event
        assert source.update_count == 1

    def test_multiple_managers_with_same_source(self):
        """Test that multiple managers can theoretically share a source."""
        source = MockInputSource()
        manager1 = InputManager(source)
        manager2 = InputManager(source)

        assert manager1.get_source() is manager2.get_source()

        # Note: In practice, sharing sources isn't recommended,
        # but the architecture doesn't prevent it

    def test_manager_lifecycle(self):
        """Test full lifecycle of InputManager usage."""
        # Start with no source
        manager = InputManager()
        assert not manager.has_source()

        # Set source
        source = MockInputSource()
        manager.set_source(source)
        assert manager.has_source()

        # Use source
        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=1.0,
            event_type=EventType.HIT
        )
        source.add_event(event)
        manager.update(0.016)
        events = manager.get_events()
        assert len(events) == 1

        # Clear events
        source.add_event(event)
        manager.clear_events()
        events = manager.get_events()
        assert len(events) == 0


class TestInputManagerEdgeCases:
    """Test edge cases for InputManager."""

    def test_rapid_source_switching(self):
        """Test rapidly switching between sources."""
        manager = InputManager()

        for _ in range(10):
            source = MockInputSource()
            manager.set_source(source)
            assert manager.get_source() is source

    def test_get_events_many_times_without_update(self):
        """Test calling get_events repeatedly without update."""
        source = MockInputSource()
        manager = InputManager(source)

        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=1.0,
            event_type=EventType.HIT
        )
        source.add_event(event)

        # First call gets event
        events1 = manager.get_events()
        assert len(events1) == 1

        # Subsequent calls should be empty
        for _ in range(5):
            events = manager.get_events()
            assert len(events) == 0

    def test_update_many_times_without_get_events(self):
        """Test calling update repeatedly without getting events."""
        source = MockInputSource()
        manager = InputManager(source)

        # Multiple updates
        for i in range(10):
            manager.update(0.016)

        assert source.update_count == 10

    def test_set_source_to_same_source(self):
        """Test setting the source to the same source again."""
        source = MockInputSource()
        manager = InputManager(source)

        # Set to same source again
        manager.set_source(source)

        assert manager.get_source() is source
        assert manager.has_source()
