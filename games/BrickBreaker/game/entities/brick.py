"""Brick entity with data-driven behaviors.

ALL brick mechanics come from the BrickBehaviors dataclass, loaded
from YAML. The game engine applies generic behaviors based on flags.
No brick-type-specific code - new mechanics come from config.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Optional, List, Any


class BrickState(Enum):
    """Brick lifecycle states."""

    ACTIVE = "active"       # Normal, can be hit
    HIT = "hit"            # Just hit, showing hit effect
    DESTROYED = "destroyed"  # Fully destroyed


@dataclass(frozen=True)
class BrickBehaviors:
    """Data-driven brick behaviors loaded from level YAML.

    ALL brick mechanics come from these flags - NO brick-type-specific code.
    Level designers add new behaviors by combining flags.

    Example YAML:
        brick_types:
          standard:
            color: red
            hits: 1
            points: 100

          tough:
            color: gray
            hits: 3
            points: 300

          invader:
            color: green
            hits: 1
            points: 150
            descends: true
            descend_speed: 20

          shooter:
            color: purple
            hits: 2
            points: 200
            shoots: true
            shoot_interval: 3.0

          armored_top:
            color: silver
            hits: 2
            points: 250
            hit_direction: bottom

          splitter:
            color: orange
            hits: 1
            points: 100
            splits: true
            split_into: 2
    """

    # Core properties
    hits: int = 1                    # Hits required to destroy
    points: int = 100                # Points when destroyed
    color: str = "red"               # Color identifier for skin

    # Movement behaviors
    descends: bool = False           # Moves down over time (Space Invaders)
    descend_speed: float = 0.0       # Pixels per second downward
    oscillates: bool = False         # Moves side to side
    oscillate_speed: float = 0.0     # Pixels per second
    oscillate_range: float = 0.0     # Pixels left/right from start

    # Combat behaviors
    shoots: bool = False             # Fires projectiles at paddle
    shoot_interval: float = 3.0      # Seconds between shots
    shoot_speed: float = 200.0       # Projectile speed

    # Hit restrictions
    hit_direction: str = "any"       # "top", "bottom", "left", "right", "any"

    # Destruction behaviors
    splits: bool = False             # Splits into smaller bricks when destroyed
    split_into: int = 2              # Number of smaller bricks
    explodes: bool = False           # Destroys adjacent bricks when destroyed
    explosion_radius: int = 1        # How many tiles away explosion reaches

    # Special properties
    indestructible: bool = False     # Cannot be destroyed (must avoid)
    power_up: Optional[str] = None   # Drops power-up when destroyed


class Brick:
    """A brick with behavior driven entirely by BrickBehaviors config."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        behaviors: BrickBehaviors,
        grid_position: Tuple[int, int] = (0, 0),
    ):
        """Initialize brick.

        Args:
            x: Left edge X position
            y: Top edge Y position
            width: Brick width
            height: Brick height
            behaviors: Behavior configuration from YAML
            grid_position: (row, col) position in grid
        """
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        self._behaviors = behaviors
        self._grid_position = grid_position
        self._hits_remaining = behaviors.hits
        self._state = BrickState.ACTIVE

        # Runtime state for behaviors
        self._start_x = x  # For oscillation
        self._oscillate_offset = 0.0
        self._oscillate_direction = 1
        self._shoot_timer = 0.0

    @property
    def x(self) -> float:
        """Get left edge X position."""
        return self._x

    @property
    def y(self) -> float:
        """Get top edge Y position."""
        return self._y

    @property
    def center_x(self) -> float:
        """Get center X position."""
        return self._x + self._width / 2

    @property
    def center_y(self) -> float:
        """Get center Y position."""
        return self._y + self._height / 2

    @property
    def width(self) -> float:
        """Get brick width."""
        return self._width

    @property
    def height(self) -> float:
        """Get brick height."""
        return self._height

    @property
    def behaviors(self) -> BrickBehaviors:
        """Get behavior configuration."""
        return self._behaviors

    @property
    def state(self) -> BrickState:
        """Get current state."""
        return self._state

    @property
    def hits_remaining(self) -> int:
        """Get remaining hits to destroy."""
        return self._hits_remaining

    @property
    def is_active(self) -> bool:
        """Check if brick is active (can be hit)."""
        return self._state == BrickState.ACTIVE

    @property
    def is_destroyed(self) -> bool:
        """Check if brick is destroyed."""
        return self._state == BrickState.DESTROYED

    @property
    def grid_position(self) -> Tuple[int, int]:
        """Get grid position (row, col)."""
        return self._grid_position

    @property
    def rect(self) -> Tuple[float, float, float, float]:
        """Get bounding rectangle (x, y, width, height)."""
        return (self._x, self._y, self._width, self._height)

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Get bounds (left, top, right, bottom)."""
        return (
            self._x,
            self._y,
            self._x + self._width,
            self._y + self._height,
        )

    def can_be_hit_from(self, direction: str) -> bool:
        """Check if brick can be hit from given direction.

        Args:
            direction: "top", "bottom", "left", or "right"

        Returns:
            True if brick can be hit from that direction
        """
        if self._behaviors.hit_direction == "any":
            return True
        return self._behaviors.hit_direction == direction

    def hit(self) -> 'Brick':
        """Apply a hit to the brick.

        Returns:
            New Brick with updated state
        """
        if self._behaviors.indestructible:
            return self  # No effect

        new_brick = Brick(
            self._x, self._y, self._width, self._height,
            self._behaviors, self._grid_position
        )
        new_brick._start_x = self._start_x
        new_brick._oscillate_offset = self._oscillate_offset
        new_brick._oscillate_direction = self._oscillate_direction
        new_brick._shoot_timer = self._shoot_timer

        new_brick._hits_remaining = self._hits_remaining - 1

        if new_brick._hits_remaining <= 0:
            new_brick._state = BrickState.DESTROYED
        else:
            new_brick._state = BrickState.ACTIVE

        return new_brick

    def update(self, dt: float) -> Tuple['Brick', List[Any]]:
        """Update brick state based on behaviors.

        Applies all behavior flags generically:
        - descends: Move down
        - oscillates: Move side to side
        - shoots: Fire projectiles

        Args:
            dt: Delta time in seconds

        Returns:
            Tuple of (updated brick, list of projectiles fired)
        """
        if self._state != BrickState.ACTIVE:
            return self, []

        projectiles: List[Any] = []
        new_x = self._x
        new_y = self._y
        new_offset = self._oscillate_offset
        new_direction = self._oscillate_direction
        new_shoot_timer = self._shoot_timer

        # Handle descending
        if self._behaviors.descends:
            new_y = self._y + self._behaviors.descend_speed * dt

        # Handle oscillation
        if self._behaviors.oscillates:
            new_offset += self._behaviors.oscillate_speed * dt * new_direction
            if abs(new_offset) >= self._behaviors.oscillate_range:
                new_direction *= -1
                # Clamp to range
                new_offset = max(
                    -self._behaviors.oscillate_range,
                    min(self._behaviors.oscillate_range, new_offset)
                )
            new_x = self._start_x + new_offset

        # Handle shooting (projectiles handled by game mode)
        if self._behaviors.shoots:
            new_shoot_timer += dt
            if new_shoot_timer >= self._behaviors.shoot_interval:
                new_shoot_timer = 0.0
                # Signal that a projectile should be created
                # (actual projectile creation handled by game mode)
                projectiles.append({
                    'x': self.center_x,
                    'y': self._y + self._height,
                    'speed': self._behaviors.shoot_speed,
                })

        # Create new brick with updated state
        new_brick = Brick(
            new_x, new_y, self._width, self._height,
            self._behaviors, self._grid_position
        )
        new_brick._start_x = self._start_x
        new_brick._oscillate_offset = new_offset
        new_brick._oscillate_direction = new_direction
        new_brick._shoot_timer = new_shoot_timer
        new_brick._hits_remaining = self._hits_remaining
        new_brick._state = self._state

        return new_brick, projectiles

    def get_split_bricks(self) -> List['Brick']:
        """Get smaller bricks when this brick is destroyed (if splits: true).

        Returns:
            List of smaller bricks, empty if not a splitting brick
        """
        if not self._behaviors.splits:
            return []

        # Create smaller bricks
        smaller_width = self._width / 2
        smaller_height = self._height / 2
        split_count = self._behaviors.split_into

        # Create behaviors for smaller bricks (same but no split)
        smaller_behaviors = BrickBehaviors(
            hits=1,
            points=self._behaviors.points // 2,
            color=self._behaviors.color,
            descends=self._behaviors.descends,
            descend_speed=self._behaviors.descend_speed,
            # Don't inherit splits to prevent infinite recursion
            splits=False,
        )

        bricks = []
        for i in range(split_count):
            # Position smaller bricks side by side
            offset_x = (i - (split_count - 1) / 2) * smaller_width
            brick = Brick(
                self.center_x + offset_x - smaller_width / 2,
                self._y,
                smaller_width,
                smaller_height,
                smaller_behaviors,
                self._grid_position,
            )
            bricks.append(brick)

        return bricks
