"""
AMS Event Types

Defines the core event types that flow through the Arcade Management System:
- PlaneHitEvent: Standard format for all detection events
- HitResult: What games return when queried about hits
- EventMetadata: Additional detection information

These types are the contract between detection layers and games.
All detection backends must produce PlaneHitEvents.
All games must accept PlaneHitEvents and return HitResults.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class PlaneHitEvent(BaseModel):
    """
    Standard event format for coordinate-based detection.

    All detection backends (CV, mouse, AR, etc.) emit these events.
    Games receive only these normalized events, never raw detection data.

    Coordinates are normalized [0, 1] in game space:
    - (0, 0) = top-left corner
    - (1, 1) = bottom-right corner
    - Independent of display resolution
    """
    x: float = Field(..., ge=0, le=1, description="Normalized x coordinate [0, 1]")
    y: float = Field(..., ge=0, le=1, description="Normalized y coordinate [0, 1]")
    timestamp: float = Field(..., description="Event timestamp (seconds since epoch)")

    # Optional metadata from detection layer
    confidence: float = Field(default=1.0, ge=0, le=1, description="Detection confidence")
    detection_method: str = Field(default="unknown", description="Which backend produced this")
    latency_ms: float = Field(default=0.0, description="Detection latency in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Backend-specific data")

    class Config:
        frozen = True  # Events are immutable once created


class HitResult(BaseModel):
    """
    Result of querying a game about whether coordinates hit a target.

    Games maintain temporal state and respond to hit queries with these results.
    Includes both hit/miss status and contextual information.
    """
    hit: bool = Field(..., description="Whether the coordinates hit a target")
    target_id: Optional[str] = Field(default=None, description="Which target was hit")
    distance: Optional[float] = Field(default=None, description="Distance from target center")
    points: int = Field(default=0, description="Points awarded for this hit")

    # Game state information
    game_state: Optional[str] = Field(default=None, description="Game state at query time")
    frame: Optional[int] = Field(default=None, description="Frame number at query time")

    # Additional context
    message: Optional[str] = Field(default=None, description="Human-readable result message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Game-specific data")


class CalibrationResult(BaseModel):
    """
    Result of a calibration session.

    For mouse/keyboard: This is essentially a no-op.
    For CV: Contains color palette, background models, latency measurements.
    """
    success: bool = Field(..., description="Whether calibration succeeded")
    method: str = Field(..., description="Calibration method used")
    timestamp: datetime = Field(default_factory=datetime.now)

    # For CV backends
    available_colors: Optional[list] = Field(default=None, description="Colors games can use")
    display_latency_ms: Optional[float] = Field(default=None, description="Measured display latency")
    detection_quality: Optional[float] = Field(default=None, description="Overall quality score")

    # Metadata
    notes: Optional[str] = Field(default=None, description="Human-readable calibration info")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Backend-specific data")


if __name__ == "__main__":
    import time

    # Example: Create a PlaneHitEvent
    event = PlaneHitEvent(
        x=0.5,
        y=0.3,
        timestamp=time.time(),
        confidence=0.95,
        detection_method="mouse",
        metadata={"button": "left", "click_count": 1}
    )

    print("PlaneHitEvent:")
    print(f"  Position: ({event.x:.2f}, {event.y:.2f})")
    print(f"  Time: {event.timestamp:.3f}")
    print(f"  Method: {event.detection_method}")
    print(f"  Confidence: {event.confidence:.2%}")

    # Example: Create a HitResult
    result = HitResult(
        hit=True,
        target_id="target_1",
        distance=0.05,
        points=100,
        message="Direct hit!"
    )

    print("\nHitResult:")
    print(f"  Hit: {result.hit}")
    print(f"  Target: {result.target_id}")
    print(f"  Distance: {result.distance:.3f}")
    print(f"  Points: {result.points}")
    print(f"  Message: {result.message}")

    # Example: Serialize to JSON
    print("\nJSON serialization:")
    print(event.model_dump_json(indent=2))
