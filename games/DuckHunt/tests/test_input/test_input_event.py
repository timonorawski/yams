"""
Comprehensive tests for the InputEvent Pydantic model.

Tests cover:
- Valid construction
- Validation (timestamps, positions)
- Immutability
- Type coercion
- Edge cases
- String representation
"""

import pytest
from pydantic import ValidationError

from models import Vector2D, EventType
from games.DuckHunt.input.input_event import InputEvent


class TestInputEventConstruction:
    """Test InputEvent creation with valid data."""

    def test_valid_construction(self):
        """Test creating InputEvent with valid data."""
        position = Vector2D(x=100.0, y=200.0)
        event = InputEvent(
            position=position,
            timestamp=1.5,
            event_type=EventType.HIT
        )

        assert event.position == position
        assert event.timestamp == 1.5
        assert event.event_type == EventType.HIT

    def test_construction_with_zero_timestamp(self):
        """Test InputEvent with timestamp of 0 (valid - start of timing)."""
        event = InputEvent(
            position=Vector2D(x=0.0, y=0.0),
            timestamp=0.0,
            event_type=EventType.MISS
        )
        assert event.timestamp == 0.0

    def test_construction_with_miss_event_type(self):
        """Test InputEvent with MISS event type."""
        event = InputEvent(
            position=Vector2D(x=50.0, y=50.0),
            timestamp=2.5,
            event_type=EventType.MISS
        )
        assert event.event_type == EventType.MISS

    def test_construction_with_large_timestamp(self):
        """Test InputEvent with large timestamp (long-running game)."""
        event = InputEvent(
            position=Vector2D(x=300.0, y=400.0),
            timestamp=3600.5,  # Over an hour
            event_type=EventType.HIT
        )
        assert event.timestamp == 3600.5


class TestInputEventValidation:
    """Test InputEvent validation rules."""

    def test_negative_timestamp_raises_error(self):
        """Test that negative timestamp raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            InputEvent(
                position=Vector2D(x=100.0, y=100.0),
                timestamp=-1.0,
                event_type=EventType.HIT
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]['loc'] == ('timestamp',)
        assert 'non-negative' in errors[0]['msg'].lower()

    def test_invalid_event_type_raises_error(self):
        """Test that invalid event type raises ValidationError."""
        with pytest.raises(ValidationError):
            InputEvent(
                position=Vector2D(x=100.0, y=100.0),
                timestamp=1.0,
                event_type="invalid"  # type: ignore
            )

    def test_missing_position_raises_error(self):
        """Test that missing position raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            InputEvent(  # type: ignore
                timestamp=1.0,
                event_type=EventType.HIT
            )

        errors = exc_info.value.errors()
        assert any(err['loc'] == ('position',) for err in errors)

    def test_missing_timestamp_raises_error(self):
        """Test that missing timestamp raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            InputEvent(  # type: ignore
                position=Vector2D(x=100.0, y=100.0),
                event_type=EventType.HIT
            )

        errors = exc_info.value.errors()
        assert any(err['loc'] == ('timestamp',) for err in errors)

    def test_missing_event_type_raises_error(self):
        """Test that missing event_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            InputEvent(  # type: ignore
                position=Vector2D(x=100.0, y=100.0),
                timestamp=1.0
            )

        errors = exc_info.value.errors()
        assert any(err['loc'] == ('event_type',) for err in errors)


class TestInputEventTypeCoercion:
    """Test type coercion for InputEvent fields."""

    def test_timestamp_int_to_float_coercion(self):
        """Test that integer timestamp is coerced to float."""
        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=5,  # Integer
            event_type=EventType.HIT
        )
        assert isinstance(event.timestamp, float)
        assert event.timestamp == 5.0

    def test_string_event_type_coercion(self):
        """Test that string event type is coerced to EventType enum."""
        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=1.0,
            event_type="hit"  # String that matches enum value
        )
        assert event.event_type == EventType.HIT
        assert isinstance(event.event_type, EventType)


class TestInputEventImmutability:
    """Test that InputEvent is immutable (frozen model)."""

    def test_cannot_modify_position(self):
        """Test that position cannot be modified after creation."""
        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=1.0,
            event_type=EventType.HIT
        )

        with pytest.raises(ValidationError):
            event.position = Vector2D(x=200.0, y=200.0)  # type: ignore

    def test_cannot_modify_timestamp(self):
        """Test that timestamp cannot be modified after creation."""
        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=1.0,
            event_type=EventType.HIT
        )

        with pytest.raises(ValidationError):
            event.timestamp = 2.0  # type: ignore

    def test_cannot_modify_event_type(self):
        """Test that event_type cannot be modified after creation."""
        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=1.0,
            event_type=EventType.HIT
        )

        with pytest.raises(ValidationError):
            event.event_type = EventType.MISS  # type: ignore


class TestInputEventStringRepresentation:
    """Test string representation of InputEvent."""

    def test_string_representation_format(self):
        """Test that string representation is formatted correctly."""
        event = InputEvent(
            position=Vector2D(x=123.456, y=789.012),
            timestamp=1.234,
            event_type=EventType.HIT
        )

        str_repr = str(event)
        assert "InputEvent" in str_repr
        assert "123.46" in str_repr  # Position x rounded to 2 decimals
        assert "789.01" in str_repr  # Position y rounded to 2 decimals
        assert "1.234" in str_repr  # Timestamp with 3 decimals
        assert "hit" in str_repr  # Event type value

    def test_string_representation_miss_event(self):
        """Test string representation for MISS event type."""
        event = InputEvent(
            position=Vector2D(x=50.0, y=60.0),
            timestamp=2.5,
            event_type=EventType.MISS
        )

        str_repr = str(event)
        assert "miss" in str_repr


class TestInputEventEdgeCases:
    """Test edge cases for InputEvent."""

    def test_very_large_coordinates(self):
        """Test InputEvent with very large coordinate values."""
        event = InputEvent(
            position=Vector2D(x=10000.0, y=10000.0),
            timestamp=1.0,
            event_type=EventType.HIT
        )
        assert event.position.x == 10000.0
        assert event.position.y == 10000.0

    def test_very_small_positive_timestamp(self):
        """Test InputEvent with very small positive timestamp."""
        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=0.0001,
            event_type=EventType.HIT
        )
        assert event.timestamp == 0.0001

    def test_fractional_coordinates(self):
        """Test InputEvent with fractional pixel coordinates."""
        event = InputEvent(
            position=Vector2D(x=123.456789, y=987.654321),
            timestamp=1.0,
            event_type=EventType.HIT
        )
        assert event.position.x == 123.456789
        assert event.position.y == 987.654321

    def test_zero_coordinates(self):
        """Test InputEvent at origin (0, 0)."""
        event = InputEvent(
            position=Vector2D(x=0.0, y=0.0),
            timestamp=0.0,
            event_type=EventType.HIT
        )
        assert event.position.x == 0.0
        assert event.position.y == 0.0


class TestInputEventEquality:
    """Test equality comparison for InputEvent."""

    def test_events_with_same_data_are_equal(self):
        """Test that two InputEvents with identical data are equal."""
        position = Vector2D(x=100.0, y=200.0)
        event1 = InputEvent(
            position=position,
            timestamp=1.5,
            event_type=EventType.HIT
        )
        event2 = InputEvent(
            position=position,
            timestamp=1.5,
            event_type=EventType.HIT
        )
        assert event1 == event2

    def test_events_with_different_positions_not_equal(self):
        """Test that events with different positions are not equal."""
        event1 = InputEvent(
            position=Vector2D(x=100.0, y=200.0),
            timestamp=1.5,
            event_type=EventType.HIT
        )
        event2 = InputEvent(
            position=Vector2D(x=101.0, y=200.0),
            timestamp=1.5,
            event_type=EventType.HIT
        )
        assert event1 != event2

    def test_events_with_different_timestamps_not_equal(self):
        """Test that events with different timestamps are not equal."""
        position = Vector2D(x=100.0, y=200.0)
        event1 = InputEvent(
            position=position,
            timestamp=1.5,
            event_type=EventType.HIT
        )
        event2 = InputEvent(
            position=position,
            timestamp=1.6,
            event_type=EventType.HIT
        )
        assert event1 != event2

    def test_events_with_different_types_not_equal(self):
        """Test that events with different event types are not equal."""
        position = Vector2D(x=100.0, y=200.0)
        event1 = InputEvent(
            position=position,
            timestamp=1.5,
            event_type=EventType.HIT
        )
        event2 = InputEvent(
            position=position,
            timestamp=1.5,
            event_type=EventType.MISS
        )
        assert event1 != event2
