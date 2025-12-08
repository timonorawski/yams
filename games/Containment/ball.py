"""Ball entity for Containment game.

The ball bounces around the play area, seeking to escape through gaps.
Direct hits from the player cause it to speed up (penalty).
"""
import math
import random
from dataclasses import dataclass, field
from typing import Optional, Tuple

from models import Vector2D


@dataclass
class Ball:
    """A ball that bounces and tries to escape."""

    position: Vector2D
    velocity: Vector2D
    radius: float = 20.0
    speed_multiplier: float = 1.0
    base_speed: float = 150.0
    color: Tuple[int, int, int] = (255, 255, 255)

    # Tracking
    bounce_count: int = field(default=0, init=False)

    @property
    def speed(self) -> float:
        """Current speed accounting for multiplier."""
        return self.base_speed * self.speed_multiplier

    def update(self, dt: float) -> None:
        """Update ball position."""
        # Normalize velocity and apply current speed
        vel_magnitude = math.sqrt(self.velocity.x ** 2 + self.velocity.y ** 2)
        if vel_magnitude > 0:
            normalized = Vector2D(
                x=self.velocity.x / vel_magnitude,
                y=self.velocity.y / vel_magnitude
            )
            self.position = Vector2D(
                x=self.position.x + normalized.x * self.speed * dt,
                y=self.position.y + normalized.y * self.speed * dt
            )

    def bounce_off_horizontal(self) -> None:
        """Bounce off a horizontal surface (top/bottom)."""
        self.velocity = Vector2D(x=self.velocity.x, y=-self.velocity.y)
        self.bounce_count += 1

    def bounce_off_vertical(self) -> None:
        """Bounce off a vertical surface (left/right)."""
        self.velocity = Vector2D(x=-self.velocity.x, y=self.velocity.y)
        self.bounce_count += 1

    def bounce_off_surface(self, normal: Vector2D, push_out: float = 0.0) -> None:
        """Bounce off an arbitrary surface given its normal vector.

        Uses reflection formula: v' = v - 2(v·n)n

        Args:
            normal: Surface normal (pointing toward ball)
            push_out: Distance to push ball along normal to prevent sticking
        """
        # Normalize the normal vector
        n_mag = math.sqrt(normal.x ** 2 + normal.y ** 2)
        if n_mag == 0:
            return
        n = Vector2D(x=normal.x / n_mag, y=normal.y / n_mag)

        # Check if ball is moving toward the surface (dot product < 0)
        # If not, skip the bounce to prevent double-bouncing
        dot = self.velocity.x * n.x + self.velocity.y * n.y
        if dot >= 0:
            # Ball is already moving away from surface, don't bounce again
            # But still push out if needed
            if push_out > 0:
                self.position = Vector2D(
                    x=self.position.x + n.x * push_out,
                    y=self.position.y + n.y * push_out
                )
            return

        # Calculate reflection
        self.velocity = Vector2D(
            x=self.velocity.x - 2 * dot * n.x,
            y=self.velocity.y - 2 * dot * n.y
        )
        self.bounce_count += 1

        # Push ball out of collision zone to prevent sticking
        if push_out > 0:
            # Add a small buffer (1 pixel) to ensure we're fully clear
            push_distance = push_out + 1.0
            self.position = Vector2D(
                x=self.position.x + n.x * push_distance,
                y=self.position.y + n.y * push_distance
            )

    def apply_speed_penalty(self, multiplier: float = 1.2) -> None:
        """Increase speed when hit directly (penalty)."""
        self.speed_multiplier *= multiplier

    def is_point_inside(self, point: Vector2D, tolerance: float = 0.0) -> bool:
        """Check if a point is inside the ball (for direct hit detection)."""
        dx = point.x - self.position.x
        dy = point.y - self.position.y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance < self.radius + tolerance


def create_ball(
    screen_width: int,
    screen_height: int,
    base_speed: float = 150.0,
    radius: float = 20.0,
    color: Tuple[int, int, int] = (255, 255, 255),
) -> Ball:
    """Create a ball at screen center with random direction."""
    # Start at center
    position = Vector2D(x=screen_width / 2, y=screen_height / 2)

    # Random direction
    angle = random.uniform(0, 2 * math.pi)
    # Avoid purely horizontal/vertical for more interesting bounces
    while abs(math.cos(angle)) > 0.95 or abs(math.sin(angle)) > 0.95:
        angle = random.uniform(0, 2 * math.pi)

    velocity = Vector2D(
        x=math.cos(angle) * base_speed,
        y=math.sin(angle) * base_speed
    )

    return Ball(
        position=position,
        velocity=velocity,
        radius=radius,
        base_speed=base_speed,
        color=color,
    )
