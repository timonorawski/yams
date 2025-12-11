"""
GameEntity - concrete entity for the YAML-driven game engine.

Extends the Entity ABC with game-specific attributes:
- Transform (position, velocity, size)
- Lifecycle (alive, destroy)
- Visuals (sprite, color, visibility)
- Game state (health, spawn time, tags)
- Hierarchy (parent-child relationships)
"""

import math
import re
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

from ams.lua.entity import Entity

if TYPE_CHECKING:
    from ams.games.game_engine.config import RenderWhen


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

    def get_property(self, name: str, current_time: float = 0.0) -> Any:
        """Get property value, including computed properties.

        Args:
            name: Property name (can be entity attribute, computed, or custom property)
            current_time: Current game time for age calculations

        Computed properties:
            - damage_ratio: 1 - (hits_remaining / max_hits)
            - health_ratio: health / max_health
            - alive: entity.alive
            - age: current_time - spawn_time
            - vx, vy: velocity components
            - facing: 'left' or 'right' based on vx
            - moving_up, moving_down: vy direction
            - heading: direction in degrees (0=north, clockwise)
        """
        # Built-in computed properties
        if name == 'damage_ratio':
            max_hits = self.properties.get('brick_max_hits', 1)
            hits_remaining = self.properties.get('brick_hits_remaining', max_hits)
            return 0 if max_hits <= 0 else 1 - (hits_remaining / max_hits)
        elif name == 'health_ratio':
            max_health = self.properties.get('max_health', self.health)
            return 0 if max_health <= 0 else self.health / max_health
        elif name == 'alive':
            return self.alive
        elif name == 'age':
            return current_time - self.spawn_time
        elif name == 'vx':
            return self.vx
        elif name == 'vy':
            return self.vy
        elif name == 'facing':
            return 'left' if self.vx < 0 else 'right'
        elif name == 'moving_up':
            return self.vy < 0
        elif name == 'moving_down':
            return self.vy > 0
        elif name == 'heading':
            # Heading in degrees: 0° = north (up), clockwise
            if self.vx == 0 and self.vy == 0:
                return 0  # Stationary defaults to north
            angle_rad = math.atan2(self.vx, -self.vy)
            heading = math.degrees(angle_rad)
            return heading + 360 if heading < 0 else heading

        # Regular properties from dict
        return self.properties.get(name)

    def evaluate_when(self, when: 'RenderWhen', current_time: float = 0.0) -> bool:
        """Evaluate a when condition against this entity's properties.

        Args:
            when: RenderWhen condition to evaluate
            current_time: Current game time for age calculations

        Returns:
            True if condition is satisfied
        """
        prop_value = self.get_property(when.property, current_time)

        if when.compare == 'equals':
            return prop_value == when.value
        elif when.compare == 'not_equals':
            return prop_value != when.value
        elif when.compare == 'greater_than':
            return prop_value is not None and prop_value > when.value
        elif when.compare == 'less_than':
            return prop_value is not None and prop_value < when.value
        elif when.compare == 'between':
            # min <= value < max (value field is max, min field is min)
            if prop_value is None or when.min is None:
                return False
            return when.min <= prop_value < when.value
        return False

    def resolve_property_ref(self, value: Any, current_time: float = 0.0) -> Any:
        """Resolve a $property reference to its value.

        Args:
            value: Value that may be a $property reference string
            current_time: Current game time for age calculations

        Returns:
            Resolved value, or original value if not a reference
        """
        if isinstance(value, str) and value.startswith('$'):
            return self.get_property(value[1:], current_time)
        return value

    def resolve_sprite_template(self, sprite_name: str) -> str:
        """Resolve {property} placeholders in sprite name.

        Example: "duck_{color}_{frame}" with color='green', frame=2
                 -> "duck_green_2"

        Args:
            sprite_name: Sprite name with optional {property} placeholders

        Returns:
            Resolved sprite name
        """
        def replace_placeholder(match: re.Match) -> str:
            prop_name = match.group(1)
            value = self.properties.get(prop_name)
            if value is None:
                return match.group(0)  # Keep original if not found
            # Convert whole floats to int for cleaner names
            if isinstance(value, float) and value == int(value):
                return str(int(value))
            return str(value)

        return re.sub(r'\{(\w+)\}', replace_placeholder, sprite_name)
