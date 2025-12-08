"""
Input Event - Represents a single input action.

This is a shared module used by all games.
Uses Pydantic for validation and immutability.
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
    """
    position: Vector2D
    timestamp: float
    event_type: EventType = EventType.HIT

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: float) -> float:
        """Validate timestamp is non-negative."""
        if v < 0:
            raise ValueError(f'Timestamp must be non-negative, got {v}')
        return v

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """String representation for debugging."""
        return (f"InputEvent(pos=({self.position.x:.2f}, {self.position.y:.2f}), "
                f"t={self.timestamp:.3f}, type={self.event_type.value})")
