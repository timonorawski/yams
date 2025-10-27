"""
Models package for Duck Hunt - imports from root models package.

DEPRECATED: This package is kept for backward compatibility.
All models have been moved to the root /models/ package.

New import style:
    from models import Point2D, Vector2D, TargetData
    from models.duckhunt import EventType, GameState

Old import style (still works):
    from models import Vector2D, EventType, TargetData
"""

# Import from root models package using importlib to avoid path issues
import sys
import os
import importlib.util

# Get path to root models package
# Current file: .../ArcheryGame/Games/DuckHunt/models/__init__.py
# Need to go up 3 levels to get to ArcheryGame root
_this_file = os.path.abspath(__file__)
_duckhunt_models_dir = os.path.dirname(_this_file)  # Games/DuckHunt/models
_duckhunt_dir = os.path.dirname(_duckhunt_models_dir)  # Games/DuckHunt
_games_dir = os.path.dirname(_duckhunt_dir)  # Games
_root_dir = os.path.dirname(_games_dir)  # ArcheryGame root

# Add root to sys.path so relative imports in models/ work
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

# Now import the real models module
import models as _root_models

# Re-export everything from root models
Point2D = _root_models.Point2D
Vector2D = _root_models.Vector2D
Resolution = _root_models.Resolution
Color = _root_models.Color
Rectangle = _root_models.Rectangle
HomographyMatrix = _root_models.HomographyMatrix
MarkerDetection = _root_models.MarkerDetection
CalibrationQuality = _root_models.CalibrationQuality
CalibrationData = _root_models.CalibrationData
CalibrationConfig = _root_models.CalibrationConfig
ImpactDetection = _root_models.ImpactDetection
TargetDefinition = _root_models.TargetDefinition
HitResult = _root_models.HitResult
EventType = _root_models.EventType
TargetState = _root_models.TargetState
GameState = _root_models.GameState
EffectType = _root_models.EffectType
TargetData = _root_models.TargetData
ScoreData = _root_models.ScoreData
VisualEffect = _root_models.VisualEffect
ScorePopup = _root_models.ScorePopup
GameModeConfig = _root_models.GameModeConfig
LevelConfig = _root_models.LevelConfig
RulesConfig = _root_models.RulesConfig
ScoringConfig = _root_models.ScoringConfig
SpawningConfig = _root_models.SpawningConfig
TargetConfig = _root_models.TargetConfig
TrajectoryConfig = _root_models.TrajectoryConfig

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
    # DuckHunt enums
    "EventType",
    "TargetState",
    "GameState",
    "EffectType",
    # DuckHunt models
    "TargetData",
    "ScoreData",
    "VisualEffect",
    "ScorePopup",
    # Configuration
    "GameModeConfig",
    "LevelConfig",
    "RulesConfig",
    "ScoringConfig",
    "SpawningConfig",
    "TargetConfig",
    "TrajectoryConfig",
]
