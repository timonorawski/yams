"""Gap entity for Containment game.

Gaps are openings at screen edges where the ball can escape.
The player must seal these gaps with deflectors to contain the ball.
"""
import random
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional

from models import Vector2D


class Edge(Enum):
    """Screen edge where a gap can appear."""
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


@dataclass
class Gap:
    """An opening in the screen edge where the ball can escape."""

    edge: Edge
    start: float      # Start position along edge (0-1 normalized)
    width: float      # Width of gap in pixels
    screen_width: int
    screen_height: int

    @property
    def center(self) -> Vector2D:
        """Center point of the gap."""
        if self.edge == Edge.TOP:
            return Vector2D(
                x=self.start * self.screen_width + self.width / 2,
                y=0
            )
        elif self.edge == Edge.BOTTOM:
            return Vector2D(
                x=self.start * self.screen_width + self.width / 2,
                y=self.screen_height
            )
        elif self.edge == Edge.LEFT:
            return Vector2D(
                x=0,
                y=self.start * self.screen_height + self.width / 2
            )
        else:  # RIGHT
            return Vector2D(
                x=self.screen_width,
                y=self.start * self.screen_height + self.width / 2
            )

    def get_pixel_range(self) -> Tuple[float, float]:
        """Get the pixel range of the gap along its edge."""
        if self.edge in (Edge.TOP, Edge.BOTTOM):
            start_px = self.start * self.screen_width
            end_px = start_px + self.width
        else:
            start_px = self.start * self.screen_height
            end_px = start_px + self.width
        return (start_px, end_px)

    def contains_point(self, point: Vector2D, ball_radius: float = 0) -> bool:
        """Check if a point (ball center) has escaped through this gap."""
        start_px, end_px = self.get_pixel_range()

        if self.edge == Edge.TOP:
            # Ball escapes if center goes above screen and within gap x-range
            return (
                point.y - ball_radius < 0 and
                start_px < point.x < end_px
            )
        elif self.edge == Edge.BOTTOM:
            return (
                point.y + ball_radius > self.screen_height and
                start_px < point.x < end_px
            )
        elif self.edge == Edge.LEFT:
            return (
                point.x - ball_radius < 0 and
                start_px < point.y < end_px
            )
        else:  # RIGHT
            return (
                point.x + ball_radius > self.screen_width and
                start_px < point.y < end_px
            )

    def distance_to(self, point: Vector2D) -> float:
        """Distance from a point to the center of this gap."""
        center = self.center
        dx = point.x - center.x
        dy = point.y - center.y
        return (dx * dx + dy * dy) ** 0.5

    def get_render_line(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Get line coordinates for rendering the gap."""
        start_px, end_px = self.get_pixel_range()

        if self.edge == Edge.TOP:
            return ((int(start_px), 0), (int(end_px), 0))
        elif self.edge == Edge.BOTTOM:
            return ((int(start_px), self.screen_height), (int(end_px), self.screen_height))
        elif self.edge == Edge.LEFT:
            return ((0, int(start_px)), (0, int(end_px)))
        else:  # RIGHT
            return ((self.screen_width, int(start_px)), (self.screen_width, int(end_px)))


class GapManager:
    """Manages gaps and wall collision detection."""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        gap_width: float = 140.0
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.gap_width = gap_width
        self.gaps: List[Gap] = []

    def create_gaps(self, count: int = 2) -> None:
        """Create random gaps at screen edges."""
        self.gaps.clear()

        # Available edges
        edges = list(Edge)
        random.shuffle(edges)

        for i in range(min(count, len(edges))):
            edge = edges[i]

            # Calculate normalized position range for gap
            if edge in (Edge.TOP, Edge.BOTTOM):
                edge_length = self.screen_width
            else:
                edge_length = self.screen_height

            # Gap width as fraction of edge
            gap_fraction = self.gap_width / edge_length

            # Random start position (ensure gap fits)
            max_start = 1.0 - gap_fraction
            start = random.uniform(0.1, max(0.1, max_start - 0.1))

            gap = Gap(
                edge=edge,
                start=start,
                width=self.gap_width,
                screen_width=self.screen_width,
                screen_height=self.screen_height,
            )
            self.gaps.append(gap)

    def check_escape(self, ball_pos: Vector2D, ball_radius: float) -> bool:
        """Check if ball has escaped through any gap."""
        for gap in self.gaps:
            if gap.contains_point(ball_pos, ball_radius):
                return True
        return False

    def check_wall_collision(
        self,
        ball_pos: Vector2D,
        ball_radius: float,
        ball_velocity: Vector2D
    ) -> Optional[str]:
        """Check if ball hits a wall (not a gap).

        Returns 'horizontal', 'vertical', or None.
        """
        # Check each edge
        # TOP
        if ball_pos.y - ball_radius <= 0 and ball_velocity.y < 0:
            if not self._is_in_gap(ball_pos.x, Edge.TOP):
                return 'horizontal'

        # BOTTOM
        if ball_pos.y + ball_radius >= self.screen_height and ball_velocity.y > 0:
            if not self._is_in_gap(ball_pos.x, Edge.BOTTOM):
                return 'horizontal'

        # LEFT
        if ball_pos.x - ball_radius <= 0 and ball_velocity.x < 0:
            if not self._is_in_gap(ball_pos.y, Edge.LEFT):
                return 'vertical'

        # RIGHT
        if ball_pos.x + ball_radius >= self.screen_width and ball_velocity.x > 0:
            if not self._is_in_gap(ball_pos.y, Edge.RIGHT):
                return 'vertical'

        return None

    def _is_in_gap(self, position: float, edge: Edge) -> bool:
        """Check if a position along an edge is within a gap."""
        for gap in self.gaps:
            if gap.edge != edge:
                continue
            start_px, end_px = gap.get_pixel_range()
            if start_px < position < end_px:
                return True
        return False

    def get_nearest_gap(self, point: Vector2D) -> Optional[Gap]:
        """Get the gap nearest to a point."""
        if not self.gaps:
            return None
        return min(self.gaps, key=lambda g: g.distance_to(point))

    @property
    def count(self) -> int:
        """Number of gaps."""
        return len(self.gaps)
