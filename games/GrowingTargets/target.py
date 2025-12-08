"""
GrowingTargets - Target class

A target that starts small and grows over time.
Score is inversely proportional to size when hit.
"""
import random
import time
from dataclasses import dataclass, field
from typing import Optional

from models import Vector2D
from games.GrowingTargets import config


@dataclass
class GrowingTarget:
    """A target that grows over time.

    The target appears small and grows at a constant rate.
    Hitting it when small yields more points.
    If it grows too large, it expires (missed opportunity).
    """
    position: Vector2D
    start_size: float = config.START_SIZE
    max_size: float = config.MAX_SIZE
    growth_rate: float = config.GROWTH_RATE
    created_at: float = field(default_factory=time.monotonic)

    # State
    current_radius: float = field(init=False)
    hit: bool = False
    expired: bool = False
    hit_at: Optional[float] = None
    hit_radius: Optional[float] = None

    def __post_init__(self):
        self.current_radius = self.start_size

    @property
    def is_active(self) -> bool:
        """Target is active if not hit and not expired."""
        return not self.hit and not self.expired

    @property
    def age(self) -> float:
        """Time since target appeared."""
        return time.monotonic() - self.created_at

    @property
    def size_ratio(self) -> float:
        """Current size as ratio of max size (0-1)."""
        return min(1.0, self.current_radius / self.max_size)

    @property
    def value_multiplier(self) -> float:
        """Point multiplier based on current size.

        Smaller = higher multiplier.
        At start_size: max_size / start_size (e.g., 120/10 = 12x)
        At max_size: 1x
        """
        if self.current_radius <= 0:
            return 1.0
        return self.max_size / self.current_radius

    def update(self, dt: float) -> None:
        """Update target size.

        Args:
            dt: Time delta in seconds
        """
        if not self.is_active:
            return

        # Grow the target
        self.current_radius += self.growth_rate * dt

        # Check for expiration
        if self.current_radius >= self.max_size:
            self.current_radius = self.max_size
            self.expired = True

    def check_hit(self, position: Vector2D) -> bool:
        """Check if position hits this target.

        Args:
            position: Click/hit position

        Returns:
            True if hit, False otherwise
        """
        if not self.is_active:
            return False

        dx = position.x - self.position.x
        dy = position.y - self.position.y
        distance = (dx * dx + dy * dy) ** 0.5

        if distance <= self.current_radius:
            self.hit = True
            self.hit_at = time.monotonic()
            self.hit_radius = self.current_radius
            return True
        return False

    def calculate_points(self) -> int:
        """Calculate points earned for this hit.

        Returns:
            Points (only valid if target was hit)
        """
        if not self.hit or self.hit_radius is None:
            return 0

        # Score = base * (max_size / hit_size)
        multiplier = self.max_size / self.hit_radius
        return int(config.BASE_POINTS * multiplier)


class TargetSpawner:
    """Manages spawning of growing targets."""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        spawn_rate: float = config.DEFAULT_SPAWN_RATE,
        max_targets: int = config.MAX_TARGETS,
        start_size: float = config.START_SIZE,
        max_size: float = config.MAX_SIZE,
        growth_rate: float = config.GROWTH_RATE,
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.spawn_rate = spawn_rate
        self.max_targets = max_targets
        self.start_size = start_size
        self.max_size = max_size
        self.growth_rate = growth_rate

        self._last_spawn = 0.0
        self._spawn_margin = config.SPAWN_MARGIN

    def should_spawn(self, current_target_count: int) -> bool:
        """Check if a new target should spawn."""
        now = time.monotonic()

        # Don't exceed max targets
        if current_target_count >= self.max_targets:
            return False

        # Check spawn timing
        if now - self._last_spawn >= self.spawn_rate:
            return True

        return False

    def spawn(self) -> GrowingTarget:
        """Create a new target at random position."""
        self._last_spawn = time.monotonic()

        # Random position within margins
        x = random.uniform(
            self._spawn_margin + self.max_size,
            self.screen_width - self._spawn_margin - self.max_size
        )
        y = random.uniform(
            self._spawn_margin + self.max_size,
            self.screen_height - self._spawn_margin - self.max_size
        )

        return GrowingTarget(
            position=Vector2D(x=x, y=y),
            start_size=self.start_size,
            max_size=self.max_size,
            growth_rate=self.growth_rate,
        )

    def force_spawn(self) -> GrowingTarget:
        """Force spawn a target immediately (for game start)."""
        self._last_spawn = time.monotonic()
        return self.spawn()
