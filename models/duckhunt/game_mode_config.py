"""
Pydantic v2 models for game mode YAML configuration.

These models validate and parse game mode configuration files that define
target behavior, spawning rules, scoring, and progression for Duck Hunt game modes.
"""

from typing import List, Literal, Optional, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator


class TrajectoryConfig(BaseModel):
    """
    Configuration for trajectory generation algorithms.

    Defines how targets move across the screen, including path type,
    depth behavior, and curvature characteristics.
    """
    model_config = {"frozen": True}

    algorithm: str = Field(
        description="Trajectory algorithm: 'linear', 'bezier_2d', 'bezier_3d', etc."
    )
    depth_direction: Literal["away", "toward"] = Field(
        description="Direction of depth change: 'away' (receding) or 'toward' (approaching)"
    )
    curvature_factor: float = Field(
        default=1.0,
        description="Multiplier for trajectory curvature (1.0 = standard, >1.0 = more curved)",
        ge=0.0
    )


class SpawningConfig(BaseModel):
    """
    Configuration for target spawning behavior.

    Controls where targets appear, how frequently they spawn,
    and the maximum number of simultaneous active targets.
    """
    model_config = {"frozen": True}

    spawn_sides: List[Literal["left", "right", "top", "bottom"]] = Field(
        description="List of screen sides where targets can spawn",
        min_length=1
    )
    spawn_rate_base: float = Field(
        description="Base spawn rate in targets per second",
        gt=0.0
    )
    max_active: int = Field(
        description="Maximum number of targets active simultaneously",
        ge=1
    )


class RulesConfig(BaseModel):
    """
    Game rules configuration defining win/loss conditions.

    Specifies the game type and associated victory/failure criteria
    such as target scores, miss limits, or time constraints.
    """
    model_config = {"frozen": True}

    game_type: Literal["endless", "score_target", "survival", "timed"] = Field(
        description="Type of game mode determining victory conditions"
    )
    score_target: Optional[int] = Field(
        default=None,
        description="Target score to win (for 'score_target' mode)",
        ge=1
    )
    max_misses: Optional[int] = Field(
        default=None,
        description="Maximum allowed misses before game over (for 'survival' mode)",
        ge=1
    )
    time_limit: Optional[float] = Field(
        default=None,
        description="Time limit in seconds (for 'timed' mode)",
        gt=0.0
    )
    projectiles_per_round: Optional[int] = Field(
        default=None,
        description="Number of projectiles available per round (e.g., 6 arrows). None = unlimited",
        ge=1
    )

    @model_validator(mode='after')
    def validate_game_type_requirements(self) -> 'RulesConfig':
        """Ensure required fields are provided based on game_type."""
        if self.game_type == "score_target" and self.score_target is None:
            raise ValueError("score_target is required for game_type='score_target'")
        if self.game_type == "survival" and self.max_misses is None:
            raise ValueError("max_misses is required for game_type='survival'")
        if self.game_type == "timed" and self.time_limit is None:
            raise ValueError("time_limit is required for game_type='timed'")
        return self


class TargetConfig(BaseModel):
    """
    Target properties for a specific level.

    Defines physical characteristics of targets including size,
    movement speed, and perceived depth range.
    """
    model_config = {"frozen": True}

    size: float = Field(
        description="Target size multiplier (1.0 = standard size)",
        gt=0.0
    )
    speed: float = Field(
        description="Target movement speed multiplier (1.0 = standard speed)",
        gt=0.0
    )
    depth_range: Tuple[float, float] = Field(
        description="Depth range as (min_distance, max_distance) for scale simulation"
    )

    @field_validator("depth_range")
    @classmethod
    def validate_depth_range(cls, v: Tuple[float, float]) -> Tuple[float, float]:
        """Ensure min_distance < max_distance and both are positive."""
        min_dist, max_dist = v
        if min_dist <= 0.0 or max_dist <= 0.0:
            raise ValueError("Depth range values must be positive")
        if min_dist >= max_dist:
            raise ValueError("min_distance must be less than max_distance")
        return v


class LevelConfig(BaseModel):
    """
    Configuration for a specific difficulty level.

    Combines target properties, trajectory behavior, and spawning rules
    to create progressive difficulty across game levels.
    """
    model_config = {"frozen": True}

    level: int = Field(
        description="Level number (1-based)",
        ge=1
    )
    target: TargetConfig = Field(
        description="Target properties for this level"
    )
    trajectory: TrajectoryConfig = Field(
        description="Trajectory configuration for this level"
    )
    spawning: SpawningConfig = Field(
        description="Spawning behavior for this level"
    )


class ScoringConfig(BaseModel):
    """
    Scoring configuration for the game mode.

    Defines base point values and bonus modifiers for
    various hit conditions and player performance.
    """
    model_config = {"frozen": True}

    base_hit_points: int = Field(
        description="Base points awarded for a successful hit",
        ge=1
    )
    combo_multiplier: bool = Field(
        description="Whether to apply multipliers for consecutive hits"
    )
    apex_bonus: int = Field(
        default=0,
        description="Bonus points for hitting at trajectory apex",
        ge=0
    )
    speed_bonus: bool = Field(
        default=False,
        description="Whether to award bonus points for faster targets"
    )


class GameModeConfig(BaseModel):
    """
    Complete game mode configuration from YAML.

    Top-level model that encompasses all game mode settings including
    metadata, default behavior, level progression, and scoring rules.
    """
    model_config = {"frozen": True}

    name: str = Field(
        description="Human-readable name of the game mode"
    )
    id: str = Field(
        description="Unique identifier for the game mode"
    )
    version: str = Field(
        description="Version string (e.g., '1.0.0')"
    )
    description: str = Field(
        description="Detailed description of the game mode"
    )
    author: str = Field(
        default="Community",
        description="Author or creator of the game mode"
    )
    unlock_requirement: int = Field(
        default=0,
        description="Score or level required to unlock this mode (0 = unlocked)",
        ge=0
    )
    theme: str = Field(
        description="Visual theme identifier (e.g., 'classic', 'modern')"
    )
    trajectory: TrajectoryConfig = Field(
        description="Default trajectory configuration"
    )
    spawning: SpawningConfig = Field(
        description="Default spawning configuration"
    )
    rules: RulesConfig = Field(
        description="Game rules and victory conditions"
    )
    levels: List[LevelConfig] = Field(
        description="List of level configurations for progression",
        min_length=1
    )
    scoring: ScoringConfig = Field(
        description="Scoring rules and bonus configuration"
    )

    @field_validator("levels")
    @classmethod
    def validate_levels(cls, v: List[LevelConfig]) -> List[LevelConfig]:
        """Ensure levels are sequential and start from 1."""
        if not v:
            raise ValueError("At least one level must be defined")

        level_numbers = sorted([level.level for level in v])
        expected = list(range(1, len(v) + 1))

        if level_numbers != expected:
            raise ValueError(
                f"Levels must be sequential starting from 1. "
                f"Expected {expected}, got {level_numbers}"
            )

        return v
