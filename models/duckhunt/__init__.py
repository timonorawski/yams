"""
DuckHunt-specific models package.

This package contains all data models specific to the Duck Hunt game,
including enums, game-specific data structures, and configuration models.
"""

# Import and re-export enums
from .enums import (
    EventType,
    TargetState,
    GameState,  # Re-exported from ams.games.game_state for backward compatibility
    DuckHuntInternalState,
    EffectType,
)

# Import and re-export game models
from .models import (
    TargetData,
    ScoreData,
    VisualEffect,
    ScorePopup,
)

# Import and re-export configuration models
from .game_mode_config import (
    GameModeConfig,
    LevelConfig,
    RulesConfig,
    ScoringConfig,
    SpawningConfig,
    TargetConfig,
    TrajectoryConfig,
    PacingConfig,
)

__all__ = [
    # Enums
    "EventType",
    "TargetState",
    "GameState",  # Common GameState from ams.games
    "DuckHuntInternalState",  # DuckHunt-specific internal states
    "EffectType",
    # Game models
    "TargetData",
    "ScoreData",
    "VisualEffect",
    "ScorePopup",
    # Configuration models
    "GameModeConfig",
    "LevelConfig",
    "RulesConfig",
    "ScoringConfig",
    "SpawningConfig",
    "TargetConfig",
    "TrajectoryConfig",
    "PacingConfig",
]
