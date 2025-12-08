"""Grow obstacle for Containment game.

Circular obstacles that grow when hit by additional projectiles.
"""
import math
from dataclasses import dataclass, field
from typing import Tuple, Optional

from models import Vector2D


@dataclass
class GrowObstacle:
    """A circular obstacle that grows when hit again."""

    position: Vector2D
    initial_size: float
    growth_per_hit: float  # Multiplier (0.3 = +30%)
    max_size: float
    decay_rate: float  # Size loss per second (0 = permanent)
    color: Tuple[int, int, int] = (100, 180, 220)

    # Internal state
    current_size: float = field(default=0.0, init=False)
    hit_count: int = field(default=1, init=False)

    def __post_init__(self):
        self.current_size = self.initial_size

    @property
    def radius(self) -> float:
        return self.current_size

    def update(self, dt: float) -> bool:
        """Update obstacle. Returns False if obstacle should be removed."""
        if self.decay_rate > 0:
            self.current_size -= self.decay_rate * dt
            if self.current_size <= 0:
                return False
        return True

    def try_grow(self, hit_pos: Vector2D) -> bool:
        """Try to grow if hit position is inside. Returns True if grown."""
        dx = hit_pos.x - self.position.x
        dy = hit_pos.y - self.position.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance <= self.current_size:
            # Hit inside - grow!
            self.hit_count += 1
            new_size = self.current_size * (1.0 + self.growth_per_hit)
            self.current_size = min(new_size, self.max_size)
            return True
        return False

    def check_ball_collision(self, ball_pos: Vector2D, ball_radius: float) -> Optional[Tuple[Vector2D, float]]:
        """Check collision with ball. Returns (normal, penetration) or None."""
        dx = ball_pos.x - self.position.x
        dy = ball_pos.y - self.position.y
        distance = math.sqrt(dx * dx + dy * dy)

        min_dist = ball_radius + self.current_size
        if distance < min_dist:
            penetration = min_dist - distance
            if distance > 0:
                normal = Vector2D(x=dx / distance, y=dy / distance)
                return (normal, penetration)
            else:
                # Ball exactly at center - push in arbitrary direction
                return (Vector2D(x=1.0, y=0.0), min_dist)
        return None

    def get_render_pos(self) -> Tuple[int, int]:
        return (int(self.position.x), int(self.position.y))
