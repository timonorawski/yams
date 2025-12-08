"""
Unified models library for the Archery Game project.

This package provides all Pydantic data models used across the system:
- Primitives: Basic geometric and color types (Point2D, Vector2D, Color, Rectangle, Resolution)
- Calibration: ArUco marker detection and geometric calibration models
- Game: Generic game models for the AMS and game engines
- DuckHunt: Game-specific models for Duck Hunt

Usage:
    >>> from models import Point2D, Resolution, CalibrationData
    >>> from models.duckhunt import TargetData, GameState
    >>> from models.primitives import Color, Rectangle
"""

# ============================================================================
# Primitives (basic types used everywhere)
# ============================================================================
from .primitives import (
    Point2D,
    Vector2D,  # Alias for Point2D
    Resolution,
    Color,
    Rectangle,
)

# ============================================================================
# Calibration models
# ============================================================================
from .calibration import (
    HomographyMatrix,
    MarkerDetection,
    CalibrationQuality,
    CalibrationData,
    CalibrationConfig,
)

# ============================================================================
# Generic game models
# ============================================================================
from .game import (
    ImpactDetection,
    TargetDefinition,
    HitResult,
)

# ============================================================================
# DuckHunt models (re-exported for backward compatibility)
# ============================================================================
from .duckhunt import (
    EventType,
    TargetState,
    GameState,
    DuckHuntInternalState,
    EffectType,
    TargetData,
    ScoreData,
    VisualEffect,
    ScorePopup,
    GameModeConfig,
    LevelConfig,
    RulesConfig,
    ScoringConfig,
    SpawningConfig,
    TargetConfig,
    TrajectoryConfig,
    PacingConfig,
)

# Top-level exports - most commonly used models
__all__ = [
    # Primitives
    "Point2D",
    "Vector2D",
    "Resolution",
    "Color",
    "Rectangle",
    # Calibration
    "HomographyMatrix",
    "MarkerDetection",
    "CalibrationQuality",
    "CalibrationData",
    "CalibrationConfig",
    # Game
    "ImpactDetection",
    "TargetDefinition",
    "HitResult",
    # DuckHunt (for backward compatibility)
    "EventType",
    "TargetState",
    "GameState",
    "DuckHuntInternalState",
    "EffectType",
    "TargetData",
    "ScoreData",
    "VisualEffect",
    "ScorePopup",
    "GameModeConfig",
    "LevelConfig",
    "RulesConfig",
    "ScoringConfig",
    "SpawningConfig",
    "TargetConfig",
    "TrajectoryConfig",
    "PacingConfig",
]
