"""
Generic game data models for the targeting system.

These models are used by the AMS and game engines for handling
impacts, targets, and hit detection across all games.
"""

from pydantic import BaseModel, Field
from typing import Tuple, Optional
from datetime import datetime

from .primitives import Point2D


class ImpactDetection(BaseModel):
    """Projectile impact detection result (generic for any projectile type)."""
    camera_position: Point2D
    game_position: Point2D
    confidence: float = Field(..., ge=0, le=1)
    timestamp: datetime

    # Optional metadata - varies by detection method
    blob_area: Optional[int] = None  # Size of detected blob in pixels
    color: Optional[Tuple[int, int, int]] = None  # Detected color (for color-based detection)
    velocity: Optional[float] = None  # Impact velocity (for motion tracking)


class TargetDefinition(BaseModel):
    """Target specification for game engine."""
    game_position: Point2D
    radius: float = Field(..., gt=0)  # In normalized game coordinates
    color: Tuple[int, int, int] = (255, 0, 0)  # RGB
    duration: Optional[float] = None  # Seconds, None = infinite


class HitResult(BaseModel):
    """Result of checking if projectile hit target."""
    hit: bool
    target: TargetDefinition
    impact: ImpactDetection
    distance: float  # Normalized distance in game space
    points: int = 0
