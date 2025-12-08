"""
Comprehensive tests for input sources.

Tests cover:
- InputSource ABC interface
- MockInputSource for testing
- MouseInputSource with pygame events
- Event collection and clearing
- Time-based processing
"""

import pytest
import pygame
from typing import List
from unittest.mock import MagicMock, patch

from models import Vector2D, EventType
from games.DuckHunt.input.input_event import InputEvent
from games.DuckHunt.input.sources.base import InputSource
from games.DuckHunt.input.sources.mouse import MouseInputSource


class MockInputSource(InputSource):
    """Mock implementation of InputSource for testing."""

    def __init__(self):
        """Initialize mock source with empty event list."""
        self.events: List[InputEvent] = []
        self.update_calls = 0
        self.last_dt = 0.0

    def poll_events(self) -> List[InputEvent]:
        """Return and clear the events list."""
        events = self.events.copy()
        self.events.clear()
        return events

    def update(self, dt: float) -> None:
        """Track update calls."""
        self.update_calls += 1
        self.last_dt = dt

    def add_event(self, event: InputEvent) -> None:
        """Helper to add events for testing."""
        self.events.append(event)


class TestInputSourceABC:
    """Test InputSource abstract base class."""

    def test_cannot_instantiate_input_source_directly(self):
        """Test that InputSource ABC cannot be instantiated."""
        with pytest.raises(TypeError):
            InputSource()  # type: ignore

    def test_mock_source_implements_interface(self):
        """Test that MockInputSource properly implements InputSource."""
        source = MockInputSource()
        assert isinstance(source, InputSource)

    def test_mock_source_poll_events(self):
        """Test MockInputSource poll_events method."""
        source = MockInputSource()
        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=1.0,
            event_type=EventType.HIT
        )
        source.add_event(event)

        events = source.poll_events()
        assert len(events) == 1
        assert events[0] == event

    def test_mock_source_poll_clears_events(self):
        """Test that poll_events clears the event queue."""
        source = MockInputSource()
        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=1.0,
            event_type=EventType.HIT
        )
        source.add_event(event)

        first_poll = source.poll_events()
        assert len(first_poll) == 1

        second_poll = source.poll_events()
        assert len(second_poll) == 0

    def test_mock_source_update(self):
        """Test MockInputSource update method."""
        source = MockInputSource()
        source.update(0.016)

        assert source.update_calls == 1
        assert source.last_dt == 0.016


class TestMouseInputSourceConstruction:
    """Test MouseInputSource construction."""

    def test_mouse_source_construction(self):
        """Test creating a MouseInputSource."""
        source = MouseInputSource()
        assert isinstance(source, InputSource)
        assert isinstance(source, MouseInputSource)

    def test_mouse_source_starts_empty(self):
        """Test that MouseInputSource starts with no events."""
        source = MouseInputSource()
        events = source.poll_events()
        assert len(events) == 0


class TestMouseInputSourceEventProcessing:
    """Test MouseInputSource pygame event processing."""

    @pytest.fixture
    def pygame_init(self):
        """Initialize pygame for testing."""
        pygame.init()
        # Create a small display for testing
        pygame.display.set_mode((100, 100))
        yield
        pygame.quit()

    def test_mouse_click_creates_event(self, pygame_init):
        """Test that mouse click creates an InputEvent."""
        source = MouseInputSource()

        # Create a fake mouse button down event
        fake_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 1, 'pos': (150, 250)}
        )

        # Post the event to pygame's queue
        pygame.event.post(fake_event)

        # Process events
        source.update(0.016)

        # Check that event was captured
        events = source.poll_events()
        assert len(events) == 1

        event = events[0]
        assert event.position.x == 150.0
        assert event.position.y == 250.0
        assert event.event_type == EventType.HIT
        assert event.timestamp > 0

    def test_right_mouse_button_ignored(self, pygame_init):
        """Test that right mouse button clicks are ignored."""
        source = MouseInputSource()

        # Create a right-button click event
        fake_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 3, 'pos': (100, 100)}  # button 3 is right click
        )
        pygame.event.post(fake_event)

        source.update(0.016)

        # No events should be created
        events = source.poll_events()
        assert len(events) == 0

    def test_middle_mouse_button_ignored(self, pygame_init):
        """Test that middle mouse button clicks are ignored."""
        source = MouseInputSource()

        # Create a middle-button click event
        fake_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 2, 'pos': (100, 100)}  # button 2 is middle click
        )
        pygame.event.post(fake_event)

        source.update(0.016)

        # No events should be created
        events = source.poll_events()
        assert len(events) == 0

    def test_multiple_clicks_captured(self, pygame_init):
        """Test that multiple mouse clicks are all captured."""
        source = MouseInputSource()

        # Post multiple click events
        positions = [(10, 20), (30, 40), (50, 60)]
        for pos in positions:
            fake_event = pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {'button': 1, 'pos': pos}
            )
            pygame.event.post(fake_event)

        source.update(0.016)

        # All events should be captured
        events = source.poll_events()
        assert len(events) == 3

        for i, event in enumerate(events):
            assert event.position.x == float(positions[i][0])
            assert event.position.y == float(positions[i][1])

    def test_events_cleared_after_poll(self, pygame_init):
        """Test that events are cleared after polling."""
        source = MouseInputSource()

        # Create and process a click
        fake_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 1, 'pos': (100, 100)}
        )
        pygame.event.post(fake_event)
        source.update(0.016)

        # First poll gets the event
        first_poll = source.poll_events()
        assert len(first_poll) == 1

        # Second poll should be empty
        second_poll = source.poll_events()
        assert len(second_poll) == 0

    def test_position_type_coercion(self, pygame_init):
        """Test that integer positions from pygame are converted to floats."""
        source = MouseInputSource()

        fake_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 1, 'pos': (100, 200)}  # Integers
        )
        pygame.event.post(fake_event)
        source.update(0.016)

        events = source.poll_events()
        event = events[0]

        # Should be converted to floats
        assert isinstance(event.position.x, float)
        assert isinstance(event.position.y, float)
        assert event.position.x == 100.0
        assert event.position.y == 200.0

    def test_timestamp_increases(self, pygame_init):
        """Test that timestamps increase for sequential events."""
        source = MouseInputSource()

        # First click
        fake_event1 = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 1, 'pos': (100, 100)}
        )
        pygame.event.post(fake_event1)
        source.update(0.016)
        events1 = source.poll_events()

        # Small delay
        import time
        time.sleep(0.01)

        # Second click
        fake_event2 = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 1, 'pos': (200, 200)}
        )
        pygame.event.post(fake_event2)
        source.update(0.016)
        events2 = source.poll_events()

        # Second timestamp should be greater
        assert events2[0].timestamp > events1[0].timestamp


class TestMouseInputSourceClear:
    """Test MouseInputSource clear functionality."""

    @pytest.fixture
    def pygame_init(self):
        """Initialize pygame for testing."""
        pygame.init()
        pygame.display.set_mode((100, 100))
        yield
        pygame.quit()

    def test_clear_removes_events(self, pygame_init):
        """Test that clear removes pending events."""
        source = MouseInputSource()

        # Add some events
        fake_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 1, 'pos': (100, 100)}
        )
        pygame.event.post(fake_event)
        source.update(0.016)

        # Clear before polling
        source.clear()

        # No events should be returned
        events = source.poll_events()
        assert len(events) == 0


class TestMouseInputSourceEdgeCases:
    """Test edge cases for MouseInputSource."""

    @pytest.fixture
    def pygame_init(self):
        """Initialize pygame for testing."""
        pygame.init()
        pygame.display.set_mode((800, 600))
        yield
        pygame.quit()

    def test_click_at_origin(self, pygame_init):
        """Test mouse click at (0, 0)."""
        source = MouseInputSource()

        fake_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 1, 'pos': (0, 0)}
        )
        pygame.event.post(fake_event)
        source.update(0.016)

        events = source.poll_events()
        assert len(events) == 1
        assert events[0].position.x == 0.0
        assert events[0].position.y == 0.0

    def test_click_at_screen_edge(self, pygame_init):
        """Test mouse click at screen edge."""
        source = MouseInputSource()

        fake_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 1, 'pos': (799, 599)}
        )
        pygame.event.post(fake_event)
        source.update(0.016)

        events = source.poll_events()
        assert len(events) == 1
        assert events[0].position.x == 799.0
        assert events[0].position.y == 599.0

    def test_update_with_no_events(self, pygame_init):
        """Test update when there are no pygame events."""
        source = MouseInputSource()

        # Clear any existing events
        pygame.event.clear()

        # Update with no events
        source.update(0.016)

        # Should return empty list
        events = source.poll_events()
        assert len(events) == 0

    def test_multiple_updates_before_poll(self, pygame_init):
        """Test calling update multiple times before polling."""
        source = MouseInputSource()

        # First update with event
        fake_event1 = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 1, 'pos': (100, 100)}
        )
        pygame.event.post(fake_event1)
        source.update(0.016)

        # Second update with event
        fake_event2 = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 1, 'pos': (200, 200)}
        )
        pygame.event.post(fake_event2)
        source.update(0.016)

        # Both events should be collected
        events = source.poll_events()
        assert len(events) == 2
