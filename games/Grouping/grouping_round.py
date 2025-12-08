"""
Grouping Round - Data structure for tracking a round of grouping.
"""
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from models import Vector2D


class GroupingMethod(Enum):
    """Methods for calculating group center and radius.

    CENTROID: Center moves to centroid of all hits, radius encompasses all hits.
              Good for measuring natural grouping tendency.

    FIXED_CENTER: First hit sets center, second hit sets radius.
                  Subsequent hits must stay within that fixed circle.
                  Good for training to hit a specific spot consistently.

    FIXED_ORIGIN: Center stays at original target position, first hit sets radius.
                  Subsequent hits must stay within that circle around the origin.
                  Good for training to hit a specific known target consistently.
    """
    CENTROID = "centroid"
    FIXED_CENTER = "fixed_center"
    FIXED_ORIGIN = "fixed_origin"


@dataclass
class GroupingRound:
    """Tracks a single round of the grouping game.

    A round starts when the player makes their first hit and ends when
    they miss (hit outside the current target boundary).

    Supports two grouping methods:
    - CENTROID: Center moves to centroid, radius encompasses all hits
    - FIXED_CENTER: First hit = center, second hit = radius, then fixed

    Attributes:
        target_center: Initial target center position (for display before first hit)
        initial_radius: Starting target radius
        method: Grouping calculation method
        hits: List of all hit positions in this round
        miss_position: Position of the miss that ended the round (if any)
        start_time: Timestamp when round started
        end_time: Timestamp when round ended (on miss)
        group_margin: Multiplier for group radius calculation (CENTROID mode only)
    """
    target_center: Vector2D
    initial_radius: float
    method: GroupingMethod = GroupingMethod.CENTROID
    group_margin: float = 1.15
    hits: List[Vector2D] = field(default_factory=list)
    miss_position: Optional[Vector2D] = None
    start_time: float = field(default_factory=time.monotonic)
    end_time: Optional[float] = None

    # Internal state for FIXED_CENTER mode
    _fixed_center: Optional[Vector2D] = field(default=None, repr=False)
    _fixed_radius: Optional[float] = field(default=None, repr=False)

    @property
    def is_active(self) -> bool:
        """Check if round is still in progress."""
        return self.end_time is None

    @property
    def shot_count(self) -> int:
        """Number of successful hits in this round."""
        return len(self.hits)

    @property
    def centroid(self) -> Vector2D:
        """Calculate centroid (center) of all hits.

        Returns target center if no hits yet.
        """
        if not self.hits:
            return self.target_center
        x = sum(h.x for h in self.hits) / len(self.hits)
        y = sum(h.y for h in self.hits) / len(self.hits)
        return Vector2D(x=x, y=y)

    @property
    def group_radius(self) -> float:
        """Calculate current group radius based on method."""
        if self.method == GroupingMethod.FIXED_CENTER:
            return self._group_radius_fixed()
        elif self.method == GroupingMethod.FIXED_ORIGIN:
            return self._group_radius_fixed_origin()
        else:
            return self._group_radius_centroid()

    def _group_radius_centroid(self) -> float:
        """Calculate radius for CENTROID method."""
        if len(self.hits) < 2:
            return self.initial_radius

        center = self.centroid
        max_dist = max(
            math.sqrt((h.x - center.x)**2 + (h.y - center.y)**2)
            for h in self.hits
        )
        return max(max_dist * self.group_margin, 10.0)

    def _group_radius_fixed(self) -> float:
        """Calculate radius for FIXED_CENTER method."""
        if self._fixed_radius is not None:
            return self._fixed_radius
        return self.initial_radius

    def _group_radius_fixed_origin(self) -> float:
        """Calculate radius for FIXED_ORIGIN method."""
        if self._fixed_radius is not None:
            return self._fixed_radius
        return self.initial_radius

    @property
    def group_diameter(self) -> float:
        """The score metric - diameter of the current group."""
        return self.group_radius * 2

    @property
    def current_center(self) -> Vector2D:
        """Current target center based on method."""
        if self.method == GroupingMethod.FIXED_CENTER:
            if self._fixed_center is not None:
                return self._fixed_center
            return self.target_center
        elif self.method == GroupingMethod.FIXED_ORIGIN:
            # Always use original target center
            return self.target_center
        else:
            # CENTROID mode
            if len(self.hits) >= 2:
                return self.centroid
            return self.target_center

    @property
    def current_radius(self) -> float:
        """Current target radius."""
        return self.group_radius

    @property
    def is_locked(self) -> bool:
        """Check if the target is locked (FIXED_CENTER after 2 hits, FIXED_ORIGIN after 1 hit)."""
        if self.method == GroupingMethod.FIXED_CENTER:
            return self._fixed_radius is not None
        elif self.method == GroupingMethod.FIXED_ORIGIN:
            return self._fixed_radius is not None
        return False

    def add_hit(self, position: Vector2D) -> None:
        """Record a successful hit."""
        self.hits.append(position)

        # Handle FIXED_CENTER mode setup
        if self.method == GroupingMethod.FIXED_CENTER:
            if len(self.hits) == 1:
                # First hit sets the center
                self._fixed_center = position
            elif len(self.hits) == 2:
                # Second hit sets the radius
                dist = math.sqrt(
                    (position.x - self._fixed_center.x)**2 +
                    (position.y - self._fixed_center.y)**2
                )
                # Radius is distance from center to second hit, with small margin
                self._fixed_radius = max(dist * 1.1, 15.0)

        # Handle FIXED_ORIGIN mode setup
        elif self.method == GroupingMethod.FIXED_ORIGIN:
            if len(self.hits) == 1:
                # First hit sets the radius (distance from origin to first hit)
                dist = math.sqrt(
                    (position.x - self.target_center.x)**2 +
                    (position.y - self.target_center.y)**2
                )
                # Radius is distance from origin to first hit, with small margin
                self._fixed_radius = max(dist * 1.1, 15.0)

    def end_round(self, miss_position: Vector2D) -> None:
        """End the round with a miss."""
        self.miss_position = miss_position
        self.end_time = time.monotonic()

    def is_inside_target(self, position: Vector2D) -> bool:
        """Check if a position is inside the current target boundary."""
        center = self.current_center
        radius = self.current_radius

        dist = math.sqrt(
            (position.x - center.x)**2 +
            (position.y - center.y)**2
        )
        # Small grace margin for edge hits (3 pixels)
        return dist <= radius + 3

    @property
    def duration(self) -> float:
        """Duration of the round in seconds."""
        end = self.end_time or time.monotonic()
        return end - self.start_time

    @property
    def phase_description(self) -> str:
        """Describe current phase for UI display."""
        if self.method == GroupingMethod.FIXED_CENTER:
            if len(self.hits) == 0:
                return "Set center point"
            elif len(self.hits) == 1:
                return "Set group radius"
            else:
                return "Stay in the circle"
        elif self.method == GroupingMethod.FIXED_ORIGIN:
            if len(self.hits) == 0:
                return "Set group radius"
            else:
                return "Stay in the circle"
        else:
            # CENTROID
            if len(self.hits) < 2:
                return "Establish group"
            else:
                return "Tighten group"
