"""
Input Event - Represents a single input action.

This is a shared module used by all games.
Uses dataclass for immutability (Pydantic not available in WASM).
"""
from dataclasses import dataclass
from models import Vector2D, EventType


@dataclass(frozen=True)
class InputEvent:
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

    def __post_init__(self):
        """Validate timestamp is non-negative."""
        if self.timestamp < 0:
            raise ValueError(f'Timestamp must be non-negative, got {self.timestamp}')

    def __str__(self) -> str:
        """String representation for debugging."""
        return (f"InputEvent(pos=({self.position.x:.2f}, {self.position.y:.2f}), "
                f"t={self.timestamp:.3f}, type={self.event_type.value})")
