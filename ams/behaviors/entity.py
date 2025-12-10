"""
Entity - the core object that behaviors operate on.

An Entity is a game object with:
- Position and velocity
- Visual representation (sprite name, color, size)
- Attached behaviors
- Custom properties

Entities are mutable - behaviors modify them via the Lua API.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Entity:
    """A game entity that behaviors can manipulate."""

    # Identity
    id: str
    entity_type: str

    # Transform
    x: float = 0.0
    y: float = 0.0
    width: float = 32.0
    height: float = 32.0

    # Physics
    vx: float = 0.0
    vy: float = 0.0

    # Visual
    sprite: str = ""
    color: str = "white"
    visible: bool = True

    # State
    health: int = 1
    alive: bool = True

    # Custom properties (behaviors can read/write)
    properties: dict[str, Any] = field(default_factory=dict)

    # Attached behavior names
    behaviors: list[str] = field(default_factory=list)

    # Behavior-specific config (from YAML)
    behavior_config: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_rect(self) -> tuple[float, float, float, float]:
        """Return (x, y, width, height) for collision detection."""
        return (self.x, self.y, self.width, self.height)

    def get_center(self) -> tuple[float, float]:
        """Return center position."""
        return (self.x + self.width / 2, self.y + self.height / 2)

    def set_center(self, cx: float, cy: float) -> None:
        """Set position by center."""
        self.x = cx - self.width / 2
        self.y = cy - self.height / 2

    def destroy(self) -> None:
        """Mark entity for removal."""
        self.alive = False
