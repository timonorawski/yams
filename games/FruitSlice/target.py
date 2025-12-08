"""
FruitSlice - Arcing target with projectile physics.

Targets follow parabolic arcs across the screen.
"""
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional

from models import Vector2D
from games.FruitSlice import config


class TargetType(Enum):
    """Types of targets."""
    FRUIT = "fruit"
    GOLDEN = "golden"
    BOMB = "bomb"


@dataclass
class ArcingTarget:
    """A target that follows a parabolic arc across the screen.

    Physics:
        x = x0 + vx * t
        y = y0 + vy * t + 0.5 * g * t²

    Where gravity (g) is positive (pulls downward in screen coords).
    """
    # Position and velocity
    x: float
    y: float
    vx: float                  # Horizontal velocity (constant)
    vy: float                  # Vertical velocity (affected by gravity)

    # Target properties
    radius: float
    color: Tuple[int, int, int]
    target_type: TargetType
    points: int

    # Timing
    spawn_time: float = field(default_factory=time.monotonic)

    # State
    hit: bool = False
    hit_time: Optional[float] = None

    # Trail for visual effect (recent positions)
    trail: List[Tuple[float, float]] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        """Target is active if not hit."""
        return not self.hit

    @property
    def age(self) -> float:
        """Time since spawn."""
        return time.monotonic() - self.spawn_time

    @property
    def is_bomb(self) -> bool:
        """Check if this is a bomb."""
        return self.target_type == TargetType.BOMB

    def update(self, dt: float, gravity: float) -> None:
        """Update position using projectile physics.

        Args:
            dt: Time delta in seconds
            gravity: Gravity constant (pixels/second²)
        """
        if self.hit:
            return

        # Store position in trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > config.TRAIL_LENGTH:
            self.trail.pop(0)

        # Update velocity (gravity affects vertical)
        self.vy += gravity * dt

        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt

    def is_off_screen(self, width: int, height: int, margin: float = 100) -> bool:
        """Check if target has left the screen.

        Args:
            width: Screen width
            height: Screen height
            margin: Extra margin before considering off-screen

        Returns:
            True if target is off-screen
        """
        # Off bottom
        if self.y > height + margin:
            return True
        # Off left
        if self.x < -margin:
            return True
        # Off right
        if self.x > width + margin:
            return True
        return False

    def contains_point(self, px: float, py: float) -> bool:
        """Check if a point is inside this target.

        Args:
            px: Point x coordinate
            py: Point y coordinate

        Returns:
            True if point is inside target
        """
        dx = px - self.x
        dy = py - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= self.radius

    def mark_hit(self) -> None:
        """Mark this target as hit."""
        self.hit = True
        self.hit_time = time.monotonic()


def create_arcing_target(
    screen_width: int,
    screen_height: int,
    target_type: TargetType,
    radius: float,
    arc_duration: float,
    from_left: Optional[bool] = None,
    fruit_colors: Optional[List[Tuple[int, int, int]]] = None,
) -> ArcingTarget:
    """Create a target with calculated arc parameters.

    The target will arc across the screen, reaching an apex somewhere
    in the upper portion of the screen.

    Args:
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels
        target_type: Type of target to create
        radius: Target radius
        arc_duration: Approximate time target should be on screen
        from_left: If True, spawn from left. If None, random.
        fruit_colors: Optional list of colors for fruit targets (from palette)

    Returns:
        Configured ArcingTarget
    """
    if from_left is None:
        from_left = random.choice([True, False])

    margin = 50 + radius

    # Spawn position (off-screen, below bottom)
    if from_left:
        x = -margin
    else:
        x = screen_width + margin

    y = screen_height + margin

    # Calculate horizontal velocity to cross screen in arc_duration
    # Account for starting and ending off-screen
    horizontal_distance = screen_width + 2 * margin
    vx = horizontal_distance / arc_duration
    if not from_left:
        vx = -vx

    # Calculate vertical velocity for a nice arc
    # We want the apex to be in the upper 30-70% of screen
    apex_y = random.uniform(screen_height * 0.2, screen_height * 0.5)

    # Using kinematics: at apex, vy = 0
    # vy_final² = vy_initial² + 2 * g * dy
    # 0 = vy² + 2 * g * (apex_y - start_y)
    # vy² = -2 * g * (apex_y - start_y)
    # Since start_y > apex_y (starting below, apex above), dy is negative
    # So: vy² = 2 * g * (start_y - apex_y)
    # vy = -sqrt(2 * g * (start_y - apex_y))  (negative = upward)

    dy = y - apex_y  # Distance to travel up (positive)
    vy = -math.sqrt(2 * config.GRAVITY * dy)

    # Determine color and points based on type
    if target_type == TargetType.GOLDEN:
        color = config.GOLDEN_COLOR
        points = config.GOLDEN_FRUIT_POINTS
    elif target_type == TargetType.BOMB:
        color = config.BOMB_COLOR
        points = 0
    else:  # FRUIT
        # Use provided palette colors if available, otherwise fall back to config
        available_colors = fruit_colors if fruit_colors else config.FRUIT_COLORS
        color = random.choice(available_colors)
        points = config.BASE_FRUIT_POINTS

    return ArcingTarget(
        x=x,
        y=y,
        vx=vx,
        vy=vy,
        radius=radius,
        color=color,
        target_type=target_type,
        points=points,
    )
