"""Deflector entity for Containment game.

Deflectors are line segments placed by the player to redirect the ball.
Each shot places one deflector that persists until retrieval.
"""
import math
from dataclasses import dataclass
from typing import Optional, Tuple, List

from models import Vector2D


@dataclass
class Deflector:
    """A line segment that deflects the ball."""

    position: Vector2D  # Center point where shot landed
    angle: float        # Orientation in radians
    length: float       # Total length of the deflector
    color: Tuple[int, int, int] = (100, 200, 255)

    @property
    def start(self) -> Vector2D:
        """Start point of the line segment."""
        half_len = self.length / 2
        return Vector2D(
            x=self.position.x - math.cos(self.angle) * half_len,
            y=self.position.y - math.sin(self.angle) * half_len
        )

    @property
    def end(self) -> Vector2D:
        """End point of the line segment."""
        half_len = self.length / 2
        return Vector2D(
            x=self.position.x + math.cos(self.angle) * half_len,
            y=self.position.y + math.sin(self.angle) * half_len
        )

    @property
    def normal(self) -> Vector2D:
        """Surface normal (perpendicular to the line)."""
        # Rotate angle by 90 degrees
        return Vector2D(
            x=-math.sin(self.angle),
            y=math.cos(self.angle)
        )

    def get_line_points(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Get start and end as integer tuples for pygame drawing."""
        return (
            (int(self.start.x), int(self.start.y)),
            (int(self.end.x), int(self.end.y))
        )

    def check_ball_collision(
        self,
        ball_pos: Vector2D,
        ball_radius: float
    ) -> Optional[Tuple[Vector2D, float]]:
        """Check if ball collides with this deflector.

        Returns (collision_normal, penetration_depth) if collision occurs, None otherwise.
        Uses line segment to circle collision detection.

        The penetration depth is how far the ball has penetrated into the deflector,
        which is needed to push the ball out and prevent it from getting stuck.
        """
        # Vector from start to end
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        line_len_sq = dx * dx + dy * dy

        if line_len_sq == 0:
            # Degenerate case: point deflector
            dist = math.sqrt(
                (ball_pos.x - self.start.x) ** 2 +
                (ball_pos.y - self.start.y) ** 2
            )
            if dist < ball_radius:
                # Return normal pointing from deflector to ball
                if dist > 0:
                    normal = Vector2D(
                        x=(ball_pos.x - self.start.x) / dist,
                        y=(ball_pos.y - self.start.y) / dist
                    )
                    penetration = ball_radius - dist
                    return (normal, penetration)
            return None

        # Find closest point on line segment to ball center
        # t is the parameter along the line (0 = start, 1 = end)
        t = max(0, min(1, (
            (ball_pos.x - self.start.x) * dx +
            (ball_pos.y - self.start.y) * dy
        ) / line_len_sq))

        closest = Vector2D(
            x=self.start.x + t * dx,
            y=self.start.y + t * dy
        )

        # Distance from ball center to closest point
        dist_x = ball_pos.x - closest.x
        dist_y = ball_pos.y - closest.y
        distance = math.sqrt(dist_x * dist_x + dist_y * dist_y)

        if distance < ball_radius:
            # Collision! Return normal pointing from deflector toward ball
            penetration = ball_radius - distance
            if distance > 0:
                normal = Vector2D(x=dist_x / distance, y=dist_y / distance)
                return (normal, penetration)
            else:
                # Ball center exactly on line, use perpendicular
                # Penetration is full radius in this edge case
                return (self.normal, ball_radius)

        return None


def create_deflector(
    position: Vector2D,
    length: float = 60.0,
    angle: Optional[float] = None,
    color: Tuple[int, int, int] = (100, 200, 255),
) -> Deflector:
    """Create a deflector at the given position.

    Args:
        position: Center point of the deflector
        length: Length of the deflector line segment
        angle: Orientation in radians (None = random)
        color: RGB color tuple
    """
    import random
    if angle is None:
        angle = random.uniform(0, math.pi)  # Random orientation

    return Deflector(
        position=position,
        angle=angle,
        length=length,
        color=color,
    )


class DeflectorManager:
    """Manages all deflectors in the game."""

    def __init__(self, default_length: float = 60.0):
        self.deflectors: List[Deflector] = []
        self.default_length = default_length
        self.default_color = (100, 200, 255)

    def add_deflector(
        self,
        position: Vector2D,
        angle: Optional[float] = None
    ) -> Deflector:
        """Add a new deflector at the given position."""
        deflector = create_deflector(
            position=position,
            length=self.default_length,
            angle=angle,
            color=self.default_color,
        )
        self.deflectors.append(deflector)
        return deflector

    def clear(self) -> None:
        """Remove all deflectors (for retrieval)."""
        self.deflectors.clear()

    def check_ball_collision(
        self,
        ball_pos: Vector2D,
        ball_radius: float
    ) -> Optional[Tuple[Vector2D, float]]:
        """Check if ball collides with any deflector.

        Returns (collision_normal, penetration_depth) if collision, None otherwise.
        """
        for deflector in self.deflectors:
            result = deflector.check_ball_collision(ball_pos, ball_radius)
            if result is not None:
                return result
        return None

    @property
    def count(self) -> int:
        """Number of placed deflectors."""
        return len(self.deflectors)
