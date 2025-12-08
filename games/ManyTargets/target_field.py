"""
ManyTargets - Target Field management.

Handles target generation, hit detection, and field state.
"""
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from models import Vector2D
from games.ManyTargets import config


class MissMode(Enum):
    """How to handle misses."""
    PENALTY = "penalty"  # Lose points, continue playing
    STRICT = "strict"    # Game over on miss


class HitResult(Enum):
    """Result of a shot."""
    HIT = "hit"              # Hit a target
    DUPLICATE = "duplicate"  # Hit already-hit target (if duplicates allowed)
    MISS = "miss"            # Hit empty space


@dataclass
class Target:
    """A single target in the field."""
    position: Vector2D
    radius: float
    hit: bool = False
    hit_time: Optional[float] = None

    def contains(self, point: Vector2D) -> bool:
        """Check if point is inside this target."""
        dist = math.sqrt(
            (point.x - self.position.x) ** 2 +
            (point.y - self.position.y) ** 2
        )
        return dist <= self.radius


@dataclass
class TargetField:
    """Manages a field of targets.

    Handles generation, hit detection, and scoring.
    """
    screen_width: int
    screen_height: int
    target_count: int = config.DEFAULT_TARGET_COUNT
    target_radius: float = config.TARGET_RADIUS_MEDIUM
    min_spacing: float = config.MIN_TARGET_SPACING
    miss_mode: MissMode = MissMode.PENALTY
    allow_duplicates: bool = False
    progressive: bool = False
    shrink_rate: float = config.DEFAULT_SHRINK_RATE
    min_size: float = config.MIN_TARGET_SIZE

    # Internal state
    targets: List[Target] = field(default_factory=list)
    hits: int = 0
    misses: int = 0
    duplicates: int = 0
    miss_positions: List[Vector2D] = field(default_factory=list)
    failed: bool = False  # True if strict mode and missed
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def __post_init__(self):
        """Generate targets after initialization."""
        self.generate_targets()

    def generate_targets(self) -> None:
        """Generate non-overlapping random targets."""
        self.targets = []
        self.hits = 0
        self.misses = 0
        self.duplicates = 0
        self.miss_positions = []
        self.failed = False
        self.start_time = None
        self.end_time = None

        margin = self.target_radius * 2
        max_attempts = 1000
        min_dist = self.target_radius * 2 * self.min_spacing

        for _ in range(self.target_count):
            placed = False
            for _ in range(max_attempts):
                x = random.uniform(margin, self.screen_width - margin)
                y = random.uniform(margin, self.screen_height - margin)
                candidate = Vector2D(x=x, y=y)

                # Check spacing against all existing targets
                if all(self._distance(candidate, t.position) >= min_dist for t in self.targets):
                    self.targets.append(Target(
                        position=candidate,
                        radius=self.target_radius
                    ))
                    placed = True
                    break

            if not placed:
                # Could not place all targets - stop here
                break

    def _distance(self, a: Vector2D, b: Vector2D) -> float:
        """Calculate distance between two points."""
        return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

    def process_shot(self, position: Vector2D) -> HitResult:
        """Process a shot at the given position.

        Returns the result of the shot.
        """
        # Start timer on first shot
        if self.start_time is None:
            self.start_time = time.monotonic()

        # Check each target
        for target in self.targets:
            if target.contains(position):
                if target.hit:
                    # Duplicate hit
                    if self.allow_duplicates:
                        self.duplicates += 1
                        return HitResult.DUPLICATE
                    else:
                        # Target already removed, treat as miss
                        pass
                else:
                    # New hit
                    target.hit = True
                    target.hit_time = time.monotonic()
                    self.hits += 1

                    # Progressive mode: shrink remaining targets
                    if self.progressive:
                        self._shrink_remaining_targets()

                    return HitResult.HIT

        # Miss
        self.misses += 1
        self.miss_positions.append(position)

        if self.miss_mode == MissMode.STRICT:
            self.failed = True
            self.end_time = time.monotonic()

        return HitResult.MISS

    def _shrink_remaining_targets(self) -> None:
        """Shrink all remaining (unhit) targets."""
        for target in self.targets:
            if not target.hit:
                new_radius = target.radius * self.shrink_rate
                target.radius = max(new_radius, self.min_size)

    @property
    def remaining_count(self) -> int:
        """Number of targets not yet hit."""
        return sum(1 for t in self.targets if not t.hit)

    @property
    def is_complete(self) -> bool:
        """Check if all targets have been hit."""
        return self.remaining_count == 0

    @property
    def is_failed(self) -> bool:
        """Check if the round failed (strict mode miss)."""
        return self.failed

    @property
    def total_targets(self) -> int:
        """Total number of targets in the field."""
        return len(self.targets)

    def calculate_score(self) -> int:
        """Calculate the current score."""
        score = 0

        # Points for hits
        score += self.hits * config.HIT_POINTS

        # Penalty for misses
        score -= self.misses * config.MISS_PENALTY

        # Penalty for duplicates
        score -= self.duplicates * config.DUPLICATE_PENALTY

        # Perfect bonus (all hit, no misses, no duplicates)
        if self.is_complete and self.misses == 0 and self.duplicates == 0:
            score += config.PERFECT_BONUS

        return score

    def calculate_final_score(self) -> int:
        """Calculate final score including remaining target penalty."""
        score = self.calculate_score()

        # Penalty for remaining targets
        score -= self.remaining_count * config.REMAINING_PENALTY

        return score

    def end_round(self) -> None:
        """End the current round."""
        if self.end_time is None:
            self.end_time = time.monotonic()

    @property
    def duration(self) -> float:
        """Duration of the round in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.monotonic()
        return end - self.start_time

    def get_active_targets(self) -> List[Target]:
        """Get list of targets that haven't been hit."""
        return [t for t in self.targets if not t.hit]

    def get_hit_targets(self) -> List[Target]:
        """Get list of targets that have been hit."""
        return [t for t in self.targets if t.hit]
