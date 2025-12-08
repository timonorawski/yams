"""Spinner entity for Containment game - Dynamic mode.

Spinners are rotating geometric obstacles that create ever-changing
gaps and openings. Unlike static walls, the ball can never permanently
"solve" a spinner - it requires continuous adaptation.
"""
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from models import Vector2D


@dataclass
class Spinner:
    """A rotating polygon obstacle."""

    position: Vector2D          # Center of rotation
    size: float                 # Radius from center to vertices
    sides: int                  # Number of sides (3=triangle, 4=square, etc.)
    rotation_speed: float       # Degrees per second (negative = counter-clockwise)
    color: Tuple[int, int, int] = (100, 180, 220)

    # Internal state
    angle: float = field(default=0.0, init=False)  # Current rotation in radians

    def update(self, dt: float) -> None:
        """Update rotation angle."""
        # Convert degrees/sec to radians and apply
        self.angle += math.radians(self.rotation_speed) * dt
        # Keep angle in [0, 2π) range
        self.angle = self.angle % (2 * math.pi)

    def get_vertices(self) -> List[Vector2D]:
        """Get current vertex positions."""
        vertices = []
        angle_step = 2 * math.pi / self.sides
        for i in range(self.sides):
            vertex_angle = self.angle + i * angle_step
            vertices.append(Vector2D(
                x=self.position.x + math.cos(vertex_angle) * self.size,
                y=self.position.y + math.sin(vertex_angle) * self.size
            ))
        return vertices

    def get_edges(self) -> List[Tuple[Vector2D, Vector2D]]:
        """Get current edge line segments."""
        vertices = self.get_vertices()
        edges = []
        for i in range(len(vertices)):
            start = vertices[i]
            end = vertices[(i + 1) % len(vertices)]
            edges.append((start, end))
        return edges

    def get_render_points(self) -> List[Tuple[int, int]]:
        """Get vertices as integer tuples for pygame drawing."""
        return [(int(v.x), int(v.y)) for v in self.get_vertices()]

    def check_ball_collision(
        self,
        ball_pos: Vector2D,
        ball_radius: float
    ) -> Optional[Tuple[Vector2D, float]]:
        """Check if ball collides with any edge of the spinner.

        Returns (collision_normal, penetration_depth) if collision, None otherwise.
        """
        edges = self.get_edges()

        for start, end in edges:
            result = self._check_edge_collision(start, end, ball_pos, ball_radius)
            if result is not None:
                return result

        return None

    def _check_edge_collision(
        self,
        start: Vector2D,
        end: Vector2D,
        ball_pos: Vector2D,
        ball_radius: float
    ) -> Optional[Tuple[Vector2D, float]]:
        """Check collision between ball and a single edge (line segment)."""
        # Vector from start to end
        dx = end.x - start.x
        dy = end.y - start.y
        line_len_sq = dx * dx + dy * dy

        if line_len_sq == 0:
            # Degenerate edge
            return None

        # Find closest point on line segment to ball center
        t = max(0, min(1, (
            (ball_pos.x - start.x) * dx +
            (ball_pos.y - start.y) * dy
        ) / line_len_sq))

        closest = Vector2D(
            x=start.x + t * dx,
            y=start.y + t * dy
        )

        # Distance from ball center to closest point
        dist_x = ball_pos.x - closest.x
        dist_y = ball_pos.y - closest.y
        distance = math.sqrt(dist_x * dist_x + dist_y * dist_y)

        if distance < ball_radius:
            # Collision!
            penetration = ball_radius - distance
            if distance > 0:
                normal = Vector2D(x=dist_x / distance, y=dist_y / distance)
                return (normal, penetration)
            else:
                # Ball center exactly on edge - compute perpendicular normal
                edge_len = math.sqrt(line_len_sq)
                # Normal perpendicular to edge, pointing outward from spinner center
                perp = Vector2D(x=-dy / edge_len, y=dx / edge_len)
                # Make sure normal points away from spinner center
                to_center = Vector2D(
                    x=self.position.x - ball_pos.x,
                    y=self.position.y - ball_pos.y
                )
                dot = perp.x * to_center.x + perp.y * to_center.y
                if dot > 0:
                    perp = Vector2D(x=-perp.x, y=-perp.y)
                return (perp, ball_radius)

        return None


def create_spinner(
    position: Vector2D,
    size: float = 60.0,
    sides: int = 3,
    rotation_speed: float = 45.0,
    color: Tuple[int, int, int] = (100, 180, 220),
) -> Spinner:
    """Create a spinner at the given position.

    Args:
        position: Center point of the spinner
        size: Radius from center to vertices
        sides: Number of sides (3=triangle, 4=square, 5=pentagon, etc.)
        rotation_speed: Degrees per second (negative = counter-clockwise)
        color: RGB color tuple
    """
    return Spinner(
        position=position,
        size=size,
        sides=sides,
        rotation_speed=rotation_speed,
        color=color,
    )


class SpinnerManager:
    """Manages all spinners in the game."""

    def __init__(self):
        self.spinners: List[Spinner] = []

    def add_spinner(
        self,
        position: Vector2D,
        size: float = 60.0,
        sides: int = 3,
        rotation_speed: float = 45.0,
        color: Tuple[int, int, int] = (100, 180, 220),
    ) -> Spinner:
        """Add a new spinner."""
        spinner = create_spinner(
            position=position,
            size=size,
            sides=sides,
            rotation_speed=rotation_speed,
            color=color,
        )
        self.spinners.append(spinner)
        return spinner

    def update(self, dt: float) -> None:
        """Update all spinners."""
        for spinner in self.spinners:
            spinner.update(dt)

    def check_ball_collision(
        self,
        ball_pos: Vector2D,
        ball_radius: float
    ) -> Optional[Tuple[Vector2D, float]]:
        """Check if ball collides with any spinner.

        Returns (collision_normal, penetration_depth) if collision, None otherwise.
        """
        for spinner in self.spinners:
            result = spinner.check_ball_collision(ball_pos, ball_radius)
            if result is not None:
                return result
        return None

    def clear(self) -> None:
        """Remove all spinners."""
        self.spinners.clear()

    @property
    def count(self) -> int:
        """Number of spinners."""
        return len(self.spinners)

    def create_default_layout(
        self,
        screen_width: int,
        screen_height: int,
        count: int = 3,
        color: Tuple[int, int, int] = (100, 180, 220),
    ) -> None:
        """Create a default layout of spinners spread across the screen.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            count: Number of spinners to create
            color: Color for all spinners
        """
        self.clear()

        # Calculate positions to spread spinners evenly
        margin = 150  # Keep away from edges
        usable_width = screen_width - 2 * margin
        usable_height = screen_height - 2 * margin

        if count == 1:
            # Single spinner in center
            positions = [(screen_width / 2, screen_height / 2)]
        elif count == 2:
            # Two spinners horizontally spread
            positions = [
                (margin + usable_width * 0.25, screen_height / 2),
                (margin + usable_width * 0.75, screen_height / 2),
            ]
        elif count == 3:
            # Triangle arrangement
            positions = [
                (screen_width / 2, margin + usable_height * 0.2),
                (margin + usable_width * 0.25, margin + usable_height * 0.7),
                (margin + usable_width * 0.75, margin + usable_height * 0.7),
            ]
        elif count == 4:
            # Grid arrangement
            positions = [
                (margin + usable_width * 0.25, margin + usable_height * 0.25),
                (margin + usable_width * 0.75, margin + usable_height * 0.25),
                (margin + usable_width * 0.25, margin + usable_height * 0.75),
                (margin + usable_width * 0.75, margin + usable_height * 0.75),
            ]
        else:
            # Spread evenly in a rough grid
            import random
            positions = []
            for i in range(count):
                x = margin + random.uniform(0, usable_width)
                y = margin + random.uniform(0, usable_height)
                positions.append((x, y))

        # Create spinners with varying properties
        shapes = [3, 4, 5, 6]  # Triangle, square, pentagon, hexagon
        base_speeds = [30, 45, 60, -40, -55]  # Mix of directions

        for i, (x, y) in enumerate(positions):
            sides = shapes[i % len(shapes)]
            speed = base_speeds[i % len(base_speeds)]
            # Vary size slightly based on shape
            size = 50 + (sides - 3) * 10

            self.add_spinner(
                position=Vector2D(x=x, y=y),
                size=size,
                sides=sides,
                rotation_speed=speed,
                color=color,
            )
