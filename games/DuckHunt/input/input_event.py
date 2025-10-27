"""
Input event model for the Duck Hunt game.

This module defines the InputEvent Pydantic model that represents
any coordinate-based input from any source (mouse, laser pointer, impact detection).
"""

from pydantic import BaseModel, field_validator, ConfigDict
from models import Vector2D, EventType


class InputEvent(BaseModel):
    """Immutable input event from any source.

    Represents a single input action (hit or miss) at a specific position and time.
    All input sources must convert their events to this common format.

    Attributes:
        position: The 2D position where the input occurred (screen coordinates)
        timestamp: Time when the event occurred (seconds, from monotonic clock)
        event_type: Type of event (HIT or MISS)

    Examples:
        >>> from models import Vector2D, EventType
        >>> import time
        >>> event = InputEvent(
        ...     position=Vector2D(x=100.0, y=200.0),
        ...     timestamp=time.monotonic(),
        ...     event_type=EventType.HIT
        ... )
        >>> print(event)
        InputEvent(pos=(100.00, 200.00), t=..., type=hit)
    """
    position: Vector2D
    timestamp: float
    event_type: EventType

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: float) -> float:
        """Validate timestamp is non-negative.

        Args:
            v: Timestamp value to validate

        Returns:
            The validated timestamp

        Raises:
            ValueError: If timestamp is negative
        """
        if v < 0:
            raise ValueError(f'Timestamp must be non-negative, got {v}')
        return v

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """String representation for debugging.

        Returns:
            Human-readable string showing position, timestamp, and event type
        """
        return (f"InputEvent(pos=({self.position.x:.2f}, {self.position.y:.2f}), "
                f"t={self.timestamp:.3f}, type={self.event_type.value})")
