"""
Pydantic data models for the interactive projection targeting system.

These models provide type safety, validation, and serialization for:
- Calibration data and configuration
- Impact detection results
- Target definitions
- Game state

All models use Pydantic for automatic JSON serialization and validation,
enabling clean APIs and future inter-process communication.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Tuple, List, Optional, Literal
from datetime import datetime
import numpy as np
from pathlib import Path


class Point2D(BaseModel):
    """2D point in any coordinate system."""
    x: float
    y: float

    class Config:
        frozen = True  # Immutable


class Resolution(BaseModel):
    """Display or camera resolution."""
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

    class Config:
        frozen = True


class HomographyMatrix(BaseModel):
    """
    3x3 homography transformation matrix.
    Stored as flat list for JSON serialization.
    """
    matrix: List[List[float]] = Field(..., min_length=3, max_length=3)

    @field_validator('matrix')
    @classmethod
    def validate_matrix_shape(cls, v):
        if len(v) != 3 or any(len(row) != 3 for row in v):
            raise ValueError("Matrix must be 3x3")
        return v

    def to_numpy(self) -> np.ndarray:
        """Convert to numpy array for OpenCV operations."""
        return np.array(self.matrix, dtype=np.float64)

    @classmethod
    def from_numpy(cls, arr: np.ndarray) -> 'HomographyMatrix':
        """Create from numpy array."""
        if arr.shape != (3, 3):
            raise ValueError(f"Expected 3x3 array, got {arr.shape}")
        return cls(matrix=arr.tolist())


class MarkerDetection(BaseModel):
    """Single ArUco marker detection result."""
    marker_id: int
    corners: List[Point2D] = Field(..., min_length=4, max_length=4)
    center: Point2D


class CalibrationQuality(BaseModel):
    """Metrics describing calibration quality."""
    reprojection_error_rms: float = Field(..., ge=0)
    reprojection_error_max: float = Field(..., ge=0)
    num_inliers: int = Field(..., ge=0)
    num_total_points: int = Field(..., ge=0)
    inlier_ratio: float = Field(..., ge=0, le=1)

    @property
    def is_acceptable(self) -> bool:
        """Check if calibration meets quality thresholds."""
        return (
            self.reprojection_error_rms < 3.0 and
            self.inlier_ratio > 0.8
        )


class CalibrationData(BaseModel):
    """
    Complete calibration data for persistence.
    This is the main data structure saved/loaded from disk.
    """
    version: str = "1.0"
    timestamp: datetime
    projector_resolution: Resolution
    camera_resolution: Resolution
    homography_camera_to_projector: HomographyMatrix
    quality: CalibrationQuality
    detection_method: Literal["aruco_4x4", "aruco_5x5", "checkerboard"]
    num_calibration_points: int

    # Optional metadata
    notes: Optional[str] = None
    hardware_config: Optional[dict] = None

    def save(self, filepath: str):
        """Save calibration to JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, filepath: str) -> 'CalibrationData':
        """Load calibration from JSON file."""
        with open(filepath, 'r') as f:
            return cls.model_validate_json(f.read())


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


class CalibrationConfig(BaseModel):
    """Configuration parameters for calibration process."""
    pattern_type: Literal["aruco"] = "aruco"
    aruco_dict: str = "DICT_4X4_50"
    grid_size: Tuple[int, int] = (4, 4)
    margin_percent: float = Field(default=0.1, ge=0, le=0.5)
    min_markers_required: int = Field(default=12, ge=4)

    # Homography parameters
    ransac_threshold: float = Field(default=5.0, gt=0)
    max_reprojection_error: float = Field(default=3.0, gt=0)

    # Validation
    corner_test_enabled: bool = True
    interactive_verification: bool = False

    # Persistence
    auto_save: bool = True
    calibration_dir: str = "./calibration_data"
    keep_history: int = Field(default=5, ge=1)

    def save(self, filepath: str):
        """Save configuration to JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, filepath: str) -> 'CalibrationConfig':
        """Load configuration from JSON file."""
        with open(filepath, 'r') as f:
            return cls.model_validate_json(f.read())
