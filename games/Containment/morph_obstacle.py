"""Morph obstacle for Containment game.

Obstacles that change shape over time, morphing between different polygons.
"""
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from models import Vector2D


@dataclass
class MorphObstacle:
    """An obstacle that morphs between different shapes."""

    position: Vector2D
    shapes: List[int]  # List of side counts [3, 4, 5] for triangle, square, pentagon
    size: float
    rotation_speed: float
    morph_interval: float
    pulsate: bool = False
    pulsate_amount: float = 0.15
    color: Tuple[int, int, int] = (100, 180, 220)

    # Internal state
    current_shape_index: int = field(default=0, init=False)
    angle: float = field(default=0.0, init=False)
    morph_timer: float = field(default=0.0, init=False)
    pulsate_phase: float = field(default=0.0, init=False)

    @property
    def current_sides(self) -> int:
        """Get the number of sides for the current shape."""
        return self.shapes[self.current_shape_index % len(self.shapes)]

    @property
    def effective_size(self) -> float:
        """Get the effective size including pulsation."""
        if not self.pulsate:
            return self.size
        # Oscillate size using sine wave
        pulsate_factor = 1.0 + math.sin(self.pulsate_phase) * self.pulsate_amount
        return self.size * pulsate_factor

    def update(self, dt: float) -> None:
        """Update rotation, morph timer, and pulsation.

        Args:
            dt: Delta time in seconds
        """
        # Update rotation
        self.angle += math.radians(self.rotation_speed) * dt
        self.angle = self.angle % (2 * math.pi)

        # Update morph timer
        self.morph_timer += dt
        if self.morph_timer >= self.morph_interval:
            self.morph_timer = 0.0
            self.current_shape_index = (self.current_shape_index + 1) % len(self.shapes)

        # Update pulsate phase
        if self.pulsate:
            self.pulsate_phase += dt * 3.0  # ~3 rad/sec for nice oscillation

    def get_vertices(self) -> List[Vector2D]:
        """Get current vertex positions."""
        vertices = []
        sides = self.current_sides
        size = self.effective_size
        angle_step = 2 * math.pi / sides
        for i in range(sides):
            vertex_angle = self.angle + i * angle_step
            vertices.append(Vector2D(
                x=self.position.x + math.cos(vertex_angle) * size,
                y=self.position.y + math.sin(vertex_angle) * size
            ))
        return vertices

    def get_edges(self) -> List[Tuple[Vector2D, Vector2D]]:
        """Get current edge line segments."""
        vertices = self.get_vertices()
        edges = []
        for i in range(len(vertices)):
            edges.append((vertices[i], vertices[(i + 1) % len(vertices)]))
        return edges

    def get_render_points(self) -> List[Tuple[int, int]]:
        """Get vertices as integer tuples for pygame drawing."""
        return [(int(v.x), int(v.y)) for v in self.get_vertices()]

    def check_ball_collision(
        self,
        ball_pos: Vector2D,
        ball_radius: float
    ) -> Optional[Tuple[Vector2D, float]]:
        """Check if ball collides with any edge of the morph obstacle.

        Args:
            ball_pos: Position of the ball
            ball_radius: Radius of the ball

        Returns:
            (collision_normal, penetration_depth) if collision, None otherwise
        """
        # Check each edge
        for start, end in self.get_edges():
            result = self._check_edge_collision(start, end, ball_pos, ball_radius)
            if result:
                return result
        return None

    def _check_edge_collision(
        self,
        start: Vector2D,
        end: Vector2D,
        ball_pos: Vector2D,
        ball_radius: float
    ) -> Optional[Tuple[Vector2D, float]]:
        """Check collision between ball and a single edge (line segment).

        Args:
            start: Start point of the edge
            end: End point of the edge
            ball_pos: Position of the ball
            ball_radius: Radius of the ball

        Returns:
            (collision_normal, penetration_depth) if collision, None otherwise
        """
        # Vector from start to end
        dx = end.x - start.x
        dy = end.y - start.y
        line_len_sq = dx * dx + dy * dy

        if line_len_sq == 0:
            return None

        # Find closest point on line segment to ball center
        t = max(0, min(1, ((ball_pos.x - start.x) * dx + (ball_pos.y - start.y) * dy) / line_len_sq))
        closest = Vector2D(x=start.x + t * dx, y=start.y + t * dy)

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
                perp = Vector2D(x=-dy / edge_len, y=dx / edge_len)
                # Make sure normal points away from morph center
                to_center = Vector2D(x=self.position.x - ball_pos.x, y=self.position.y - ball_pos.y)
                if perp.x * to_center.x + perp.y * to_center.y > 0:
                    perp = Vector2D(x=-perp.x, y=-perp.y)
                return (perp, ball_radius)
        return None


def create_morph_obstacle(
    position: Vector2D,
    shapes: List[int],
    size: float = 50.0,
    rotation_speed: float = 30.0,
    morph_interval: float = 2.0,
    pulsate: bool = False,
    pulsate_amount: float = 0.15,
    color: Tuple[int, int, int] = (100, 180, 220),
) -> MorphObstacle:
    """Create a morph obstacle at the given position.

    Args:
        position: Center point of the obstacle
        shapes: List of side counts for shapes to morph between
        size: Radius from center to vertices
        rotation_speed: Degrees per second (negative = counter-clockwise)
        morph_interval: Seconds between shape changes
        pulsate: Enable size oscillation
        pulsate_amount: Pulsation amount as fraction (0.15 = ±15%)
        color: RGB color tuple

    Returns:
        MorphObstacle instance
    """
    return MorphObstacle(
        position=position,
        shapes=shapes,
        size=size,
        rotation_speed=rotation_speed,
        morph_interval=morph_interval,
        pulsate=pulsate,
        pulsate_amount=pulsate_amount,
        color=color,
    )
