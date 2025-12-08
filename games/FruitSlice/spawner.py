"""
FruitSlice - Target spawner with difficulty progression.

Handles spawning targets at appropriate intervals and manages
difficulty ramping over time.
"""
import random
import time
from dataclasses import dataclass
from typing import List, Optional

from games.FruitSlice import config
from games.FruitSlice.config import PacingPreset, PACING_PRESETS
from games.FruitSlice.target import ArcingTarget, TargetType, create_arcing_target


@dataclass
class SpawnerState:
    """Current state of the spawner for difficulty tracking."""
    spawn_interval: float
    arc_duration: float
    max_targets: int
    target_size: float
    bomb_ratio: float
    speed_multiplier: float = 1.0
    difficulty_level: int = 0


class TargetSpawner:
    """Spawns arcing targets with configurable pacing and difficulty progression."""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        pacing: str = 'throwing',
        spawn_interval: Optional[float] = None,
        arc_duration: Optional[float] = None,
        max_targets: Optional[int] = None,
        target_size: Optional[int] = None,
        bomb_ratio: Optional[float] = None,
        no_bombs: bool = False,
    ):
        """Initialize the spawner.

        Args:
            screen_width: Screen width
            screen_height: Screen height
            pacing: Pacing preset name (archery, throwing, blaster)
            spawn_interval: Override spawn interval (seconds)
            arc_duration: Override arc duration (seconds)
            max_targets: Override max simultaneous targets
            target_size: Override target radius
            bomb_ratio: Override bomb spawn ratio
            no_bombs: If True, disable bombs entirely
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.no_bombs = no_bombs

        # Get base preset
        preset = PACING_PRESETS.get(pacing, PACING_PRESETS['throwing'])

        # Apply overrides
        self._base_spawn_interval = spawn_interval or preset.spawn_interval
        self._base_arc_duration = arc_duration or preset.arc_duration
        self._base_max_targets = max_targets or preset.max_targets
        self._base_target_size = target_size or preset.target_size
        self._base_bomb_ratio = 0.0 if no_bombs else (bomb_ratio or preset.bomb_ratio)

        # Current state (modified by difficulty)
        self.state = SpawnerState(
            spawn_interval=self._base_spawn_interval,
            arc_duration=self._base_arc_duration,
            max_targets=self._base_max_targets,
            target_size=self._base_target_size,
            bomb_ratio=self._base_bomb_ratio,
        )

        # Timing
        self._last_spawn_time = 0.0
        self._game_start_time = time.monotonic()
        self._last_difficulty_check = 0.0

    @property
    def elapsed_time(self) -> float:
        """Time since game started."""
        return time.monotonic() - self._game_start_time

    def reset(self) -> None:
        """Reset spawner for new game/round."""
        self._last_spawn_time = 0.0
        self._game_start_time = time.monotonic()
        self._last_difficulty_check = 0.0
        self.state = SpawnerState(
            spawn_interval=self._base_spawn_interval,
            arc_duration=self._base_arc_duration,
            max_targets=self._base_max_targets,
            target_size=self._base_target_size,
            bomb_ratio=self._base_bomb_ratio,
        )

    def update_difficulty(self) -> None:
        """Update difficulty based on elapsed time."""
        elapsed = self.elapsed_time
        expected_level = int(elapsed / config.DIFFICULTY_RAMP_INTERVAL)

        if expected_level > self.state.difficulty_level:
            # Ramp up difficulty
            ramps = expected_level - self.state.difficulty_level
            for _ in range(ramps):
                self.state.difficulty_level += 1
                self.state.spawn_interval *= config.SPAWN_RATE_RAMP
                self.state.speed_multiplier *= config.SPEED_RAMP
                if not self.no_bombs:
                    self.state.bomb_ratio = min(0.5, self.state.bomb_ratio + config.BOMB_RATIO_RAMP)
                self.state.max_targets += 1

    def should_spawn(self, current_target_count: int) -> bool:
        """Check if a new target should spawn.

        Args:
            current_target_count: Number of active targets

        Returns:
            True if should spawn
        """
        now = time.monotonic()

        # Don't exceed max targets
        if current_target_count >= self.state.max_targets:
            return False

        # Check spawn timing
        if now - self._last_spawn_time >= self.state.spawn_interval:
            return True

        return False

    def spawn(self) -> ArcingTarget:
        """Create and return a new target.

        Returns:
            New ArcingTarget
        """
        self._last_spawn_time = time.monotonic()

        # Determine target type
        target_type = self._choose_target_type()

        # Calculate arc duration adjusted for speed multiplier
        arc_duration = self.state.arc_duration / self.state.speed_multiplier

        # Create target
        target = create_arcing_target(
            screen_width=self.screen_width,
            screen_height=self.screen_height,
            target_type=target_type,
            radius=self.state.target_size,
            arc_duration=arc_duration,
        )

        return target

    def _choose_target_type(self) -> TargetType:
        """Choose target type based on probabilities."""
        roll = random.random()

        # Check for bomb
        if roll < self.state.bomb_ratio:
            return TargetType.BOMB

        # Check for golden fruit
        if roll < self.state.bomb_ratio + config.GOLDEN_FRUIT_CHANCE:
            return TargetType.GOLDEN

        # Regular fruit
        return TargetType.FRUIT

    def spawn_batch(self, count: int) -> List[ArcingTarget]:
        """Spawn multiple targets at once (for quiver mode).

        Staggers spawn times slightly so they don't all appear at once.

        Args:
            count: Number of targets to spawn

        Returns:
            List of new targets
        """
        targets = []
        for i in range(count):
            target = self.spawn()
            # Stagger the spawns slightly
            if i > 0:
                # Delay subsequent spawns
                target.spawn_time += i * 0.5
            targets.append(target)
        return targets
