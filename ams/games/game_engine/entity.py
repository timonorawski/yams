"""
GameEntity - concrete entity for the YAML-driven game engine.

Extends the Entity ABC with game-specific attributes:
- Transform (position, velocity, size)
- Lifecycle (alive, destroy)
- Visuals (sprite, color, visibility)
- Game state (health, spawn time, tags)
- Hierarchy (parent-child relationships)
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from ams.lua.entity import Entity


@dataclass
class GameEntity(Entity):
    """A game entity with physics, visuals, and lifecycle."""

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
    spawn_time: float = 0.0  # Game time when entity was spawned

    # Tags for categorization (e.g., ["enemy", "brick"])
    tags: list[str] = field(default_factory=list)

    # Parent-child relationships (for rope chains, attached objects)
    parent_id: Optional[str] = None  # Entity ID this is attached to
    parent_offset: tuple[float, float] = (0.0, 0.0)  # Offset from parent position
    children: list[str] = field(default_factory=list)  # Child entity IDs

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
