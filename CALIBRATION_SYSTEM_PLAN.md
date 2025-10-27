# Calibration System Planning Document

## Core Problem Statement

Build a reusable OpenCV-based calibration pipeline that establishes a one-time geometric transformation between:
- **Projector coordinate space** (what we display)
- **Camera coordinate space** (what we observe)
- **Game coordinate space** (logical gameplay coordinates)

Since the camera and target surface are **fixed after setup**, we perform calibration once and store the transformation matrices for runtime use. Real-time image analysis of projected content is unnecessary and wasteful.

**Use-Case Agnostic**: This calibration system works for any projectile-based targeting game (archery, darts, ball throwing, axe throwing, etc.). The detection methods may vary, but the coordinate transformation remains the same.

## Coordinate Systems

### 1. Game Space (Normalized)
- Logical coordinate system: `(0, 0)` to `(1, 1)`
- Origin at top-left, normalized to projection area dimensions
- Game engine thinks in these coordinates
- Resolution-independent, portable across different projector/camera setups

### 2. Projector Space (Pixels)
- Projector's native resolution (e.g., 1920x1080)
- What gets rendered to the display buffer
- Mapped from game space via simple scaling

### 3. Camera Space (Pixels)
- Camera's native resolution (e.g., 1280x720)
- What the camera observes
- Impact detection happens in this space
- Mapped to game space via homography transformation

### 4. Physical Space (Real World)
- Not directly used in software, but conceptually important
- The actual physical target surface (plywood, foam board, fabric, wall, etc.)
- Both projector and camera view this from different angles

## Formal Data Structures (Pydantic Models)

All data structures use Pydantic for type safety, validation, and serialization. This enables clean APIs and future inter-process communication if needed.

### Core Data Models

```python
from pydantic import BaseModel, Field, validator
from typing import Tuple, List, Optional, Literal
from datetime import datetime
import numpy as np

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
    matrix: List[List[float]] = Field(..., min_items=3, max_items=3)

    @validator('matrix')
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
    corners: List[Point2D] = Field(..., min_items=4, max_items=4)
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
```

### Inter-Process Communication Benefits

Using Pydantic models enables clean separation of concerns if you later split the system into multiple processes:

**Potential Multi-Process Architecture**:
```
Camera Process          Game Engine Process       Projector Process
     ↓                         ↓                         ↓
  ImpactDetection → JSON → HitResult → JSON → TargetDefinition
```

**Benefits**:
- Each process can run independently
- Type safety across process boundaries
- Easy debugging (inspect JSON messages)
- No pickle/serialization security issues
- Language-agnostic (could rewrite components in other languages)

**Example IPC Flow**:
```python
# Camera process: Detect impact, serialize
impact = ImpactDetection(
    camera_position=Point2D(x=640, y=360),
    game_position=Point2D(x=0.5, y=0.3),
    confidence=0.95,
    timestamp=datetime.now(),
    blob_area=1250  # Optional: size of detected object
)
message_queue.send(impact.model_dump_json())

# Game engine process: Receive, validate, process
json_msg = message_queue.receive()
impact = ImpactDetection.model_validate_json(json_msg)  # Automatic validation!
# Process hit detection...
hit_result = HitResult(...)
message_queue.send(hit_result.model_dump_json())

# Projector process: Receive, validate, display
json_msg = message_queue.receive()
hit_result = HitResult.model_validate_json(json_msg)
if hit_result.hit:
    display_hit_animation()
```

### Usage Examples

```python
# Creating calibration data
calibration = CalibrationData(
    timestamp=datetime.now(),
    projector_resolution=Resolution(width=1920, height=1080),
    camera_resolution=Resolution(width=1280, height=720),
    homography_camera_to_projector=HomographyMatrix.from_numpy(H_matrix),
    quality=CalibrationQuality(
        reprojection_error_rms=1.8,
        reprojection_error_max=4.2,
        num_inliers=18,
        num_total_points=20,
        inlier_ratio=0.9
    ),
    detection_method="aruco_4x4",
    num_calibration_points=20
)

# Save to disk (automatic JSON serialization)
calibration.save("./calibration_data/calibration_20251025_143000.json")

# Load from disk (automatic validation)
loaded = CalibrationData.load("./calibration_data/calibration_20251025_143000.json")

# Use in transformations
H = loaded.homography_camera_to_projector.to_numpy()
camera_point = np.array([[640, 360]], dtype=np.float32)
projector_point = cv2.perspectiveTransform(camera_point.reshape(-1, 1, 2), H)

# Type-safe impact detection (works for any projectile)
impact = ImpactDetection(
    camera_position=Point2D(x=640, y=360),
    game_position=Point2D(x=0.5, y=0.3),
    confidence=0.95,
    timestamp=datetime.now(),
    blob_area=1250,  # Optional: detected blob size
    color=(255, 128, 0)  # Optional: detected orange color (foam arrow tip)
)

# Check hit
target = TargetDefinition(
    game_position=Point2D(x=0.5, y=0.3),
    radius=0.05
)

distance = np.sqrt(
    (impact.game_position.x - target.game_position.x)**2 +
    (impact.game_position.y - target.game_position.y)**2
)

hit_result = HitResult(
    hit=(distance < target.radius),
    target=target,
    impact=impact,
    distance=distance,
    points=100 if distance < target.radius else 0
)

# Validation happens automatically
try:
    bad_impact = ImpactDetection(
        camera_position=Point2D(x=-100, y=360),  # Valid (no constraints)
        game_position=Point2D(x=1.5, y=0.3),     # Valid (no constraints)
        confidence=1.5,  # INVALID - must be <= 1.0
        timestamp=datetime.now()
    )
except ValidationError as e:
    print(f"Invalid data: {e}")
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CALIBRATION PHASE                         │
│  (One-time, at setup - takes ~30 seconds)                   │
└─────────────────────────────────────────────────────────────┘
    │
    ├─> Project calibration pattern (known coordinates)
    ├─> Camera captures pattern
    ├─> Detect pattern features in camera image
    ├─> Compute homography: Camera Space → Game Space
    ├─> Validate transformation accuracy
    └─> Save CalibrationData to disk (Pydantic model → JSON)

┌─────────────────────────────────────────────────────────────┐
│                     RUNTIME PHASE                            │
│  (During gameplay - uses stored calibration)                │
└─────────────────────────────────────────────────────────────┘
    │
    ├─> Load CalibrationData from disk (JSON → Pydantic model)
    ├─> Game generates TargetDefinition in game space
    ├─> Transform to projector space → display target
    ├─> Projectile hits surface (arrow/ball/dart/etc.)
    ├─> Camera detects impact → ImpactDetection (camera + game coords)
    ├─> Compute HitResult
    └─> Game engine processes hit
```

## Calibration Process Flow

### Phase 1: Pattern Projection
**Input**: Projector resolution, desired grid density
**Output**: Calibration pattern displayed on projector

**Pattern Design Options**:
1. **Checkerboard Grid** (OpenCV standard)
   - Easy to detect with `cv2.findChessboardCorners()`
   - Robust, well-tested
   - Requires precise corner detection

2. **Circle Grid**
   - Better for non-planar surfaces (less critical for us)
   - `cv2.findCirclesGrid()`

3. **ArUco Markers** (RECOMMENDED)
   - Individual IDs allow partial occlusion handling
   - Sub-pixel corner detection
   - `cv2.aruco.detectMarkers()`
   - Can detect even if some markers are out of camera view
   - More robust to lighting variations

**Recommendation**: Start with ArUco markers (4x4 or 5x5 grid) for robustness.

### Phase 2: Pattern Capture
**Input**: Live camera feed
**Output**: Captured frame with visible calibration pattern

**Requirements**:
- Wait for user confirmation (pattern fully visible, no motion blur)
- Good lighting on target surface
- Pattern must occupy significant portion of camera view
- Allow re-capture if detection fails

### Phase 3: Feature Detection
**Input**: Captured camera frame
**Output**: Detected feature points in camera coordinates

**For ArUco Markers**:
```python
import cv2.aruco as aruco

# Detect markers
corners, ids, rejected = aruco.detectMarkers(
    gray_image,
    aruco_dict,
    parameters=detection_params
)

# Extract corner positions in camera space
camera_points = []
projector_points = []  # Known from pattern generation

for i, marker_id in enumerate(ids):
    # marker_id tells us which marker this is
    # corners[i] gives us the 4 corners in camera space
    # We know where this marker SHOULD be in projector space
    camera_points.extend(corners[i])
    projector_points.extend(known_marker_positions[marker_id])
```

**Validation**:
- Minimum number of detected points (e.g., 16+ for robust homography)
- Points well-distributed across frame (not clustered)
- Expected marker IDs detected

### Phase 4: Homography Computation
**Input**: Corresponding point pairs (camera space ↔ projector space)
**Output**: 3x3 homography matrix H

**Method**: `cv2.findHomography()` with RANSAC
```python
H, mask = cv2.findHomography(
    camera_points,      # Source points (Nx2)
    projector_points,   # Destination points (Nx2)
    cv2.RANSAC,         # Robust to outliers
    ransacReprojThresh=5.0  # Pixel tolerance
)
```

**What This Gives Us**:
- Transform from camera space → projector space
- For runtime, we need camera space → game space
- Game space = normalized projector space (just scale)

**Transform Chain**:
```
Camera Space → Projector Space (via H) → Game Space (via scaling)
```

### Phase 5: Validation
**Input**: Homography matrix H, test point pairs
**Output**: Reprojection error metric, pass/fail decision

**Validation Tests**:
1. **Reprojection Error**:
   - Project camera points through H
   - Compare to known projector points
   - RMS error should be < 2-3 pixels

2. **Corner Test**:
   - Project known test points at game space corners and center
   - Display markers at those positions
   - Verify they appear where expected in camera view

3. **Interactive Verification** (optional but recommended):
   - "Point at the displayed markers" (finger, stick, or actual projectile)
   - Show moving target, user indicates if camera detection aligns
   - Quick sanity check before starting game

### Phase 6: Persistence
**Input**: CalibrationData Pydantic model
**Output**: JSON file saved to disk

**Implementation**:
```python
from datetime import datetime
from pathlib import Path

def save_calibration(
    calibration: CalibrationData,
    config: CalibrationConfig
) -> Path:
    """
    Save calibration data to timestamped JSON file.

    Returns: Path to saved file
    """
    # Create calibration directory if it doesn't exist
    calib_dir = Path(config.calibration_dir)
    calib_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamped filename
    timestamp_str = calibration.timestamp.strftime("%Y%m%d_%H%M%S")
    filename = f"calibration_{timestamp_str}.json"
    filepath = calib_dir / filename

    # Save using Pydantic's built-in serialization
    calibration.save(str(filepath))

    # Manage history (keep only N most recent)
    if config.keep_history > 0:
        cleanup_old_calibrations(calib_dir, keep=config.keep_history)

    return filepath
```

**Example JSON Output**:
```json
{
  "version": "1.0",
  "timestamp": "2025-10-25T14:30:00Z",
  "projector_resolution": {
    "width": 1920,
    "height": 1080
  },
  "camera_resolution": {
    "width": 1280,
    "height": 720
  },
  "homography_camera_to_projector": {
    "matrix": [
      [1.2, 0.1, -50.0],
      [0.05, 1.3, -30.0],
      [0.0001, 0.0002, 1.0]
    ]
  },
  "quality": {
    "reprojection_error_rms": 1.8,
    "reprojection_error_max": 4.2,
    "num_inliers": 18,
    "num_total_points": 20,
    "inlier_ratio": 0.9
  },
  "detection_method": "aruco_4x4",
  "num_calibration_points": 20,
  "notes": null,
  "hardware_config": null
}
```

**File Location**: `./calibration_data/calibration_YYYYMMDD_HHMMSS.json`

## Runtime Usage API

The calibration system should provide a clean API for the game engine:

### CalibrationManager Class

```python
from typing import Optional
import numpy as np
import cv2

class CalibrationManager:
    """
    Manages calibration data and coordinate transformations.
    Thread-safe for multi-process use.
    """

    def __init__(
        self,
        config: CalibrationConfig,
        calibration_file: Optional[str] = None
    ):
        """
        Initialize calibration manager.

        Args:
            config: Configuration parameters
            calibration_file: Optional path to existing calibration JSON
        """
        self.config = config
        self._calibration: Optional[CalibrationData] = None
        self._H_cam_to_proj: Optional[np.ndarray] = None  # Cached numpy matrix

        if calibration_file:
            self.load_calibration(calibration_file)

    def calibrate(
        self,
        projector_resolution: Resolution,
        camera_resolution: Resolution
    ) -> CalibrationData:
        """
        Run full calibration sequence.

        Returns: CalibrationData object with transformation and quality metrics

        Raises:
            CalibrationError: If calibration fails
        """
        # Implementation calls pattern projection, detection, homography computation
        # Returns typed CalibrationData object
        pass

    def load_calibration(self, filepath: str) -> None:
        """
        Load calibration from file.

        Raises:
            FileNotFoundError: If file doesn't exist
            ValidationError: If JSON is invalid
        """
        self._calibration = CalibrationData.load(filepath)
        self._H_cam_to_proj = self._calibration.homography_camera_to_projector.to_numpy()

    def is_calibrated(self) -> bool:
        """Check if valid calibration exists."""
        return self._calibration is not None

    def camera_to_game(self, camera_point: Point2D) -> Point2D:
        """
        Transform point from camera space to game space (normalized).

        Args:
            camera_point: Point in camera pixel coordinates

        Returns:
            Point in normalized game coordinates [0, 1]

        Raises:
            RuntimeError: If not calibrated
        """
        if not self.is_calibrated():
            raise RuntimeError("No calibration loaded. Run calibrate() first.")

        # Transform camera → projector
        cam_pt = np.array([[camera_point.x, camera_point.y]], dtype=np.float32)
        proj_pt = cv2.perspectiveTransform(
            cam_pt.reshape(-1, 1, 2),
            self._H_cam_to_proj
        )[0][0]

        # Normalize to game space [0, 1]
        game_x = proj_pt[0] / self._calibration.projector_resolution.width
        game_y = proj_pt[1] / self._calibration.projector_resolution.height

        return Point2D(x=game_x, y=game_y)

    def game_to_projector(self, game_point: Point2D) -> Point2D:
        """
        Transform point from game space to projector space.

        Args:
            game_point: Point in normalized coordinates [0, 1]

        Returns:
            Point in projector pixel coordinates

        Raises:
            RuntimeError: If not calibrated
        """
        if not self.is_calibrated():
            raise RuntimeError("No calibration loaded. Run calibrate() first.")

        # Simple scaling from normalized to projector pixels
        proj_x = game_point.x * self._calibration.projector_resolution.width
        proj_y = game_point.y * self._calibration.projector_resolution.height

        return Point2D(x=proj_x, y=proj_y)

    def get_calibration_quality(self) -> CalibrationQuality:
        """
        Get quality metrics for current calibration.

        Returns: CalibrationQuality object

        Raises:
            RuntimeError: If not calibrated
        """
        if not self.is_calibrated():
            raise RuntimeError("No calibration loaded.")
        return self._calibration.quality

    def get_calibration_data(self) -> CalibrationData:
        """
        Get complete calibration data.

        Returns: CalibrationData object

        Raises:
            RuntimeError: If not calibrated
        """
        if not self.is_calibrated():
            raise RuntimeError("No calibration loaded.")
        return self._calibration
```

### Example Usage in Game Loop

```python
# Initialization
config = CalibrationConfig(
    aruco_dict="DICT_4X4_50",
    grid_size=(4, 4),
    calibration_dir="./calibration_data"
)

calibration = CalibrationManager(config)

if not calibration.is_calibrated():
    print("Running calibration...")
    calibration_data = calibration.calibrate(
        projector_resolution=Resolution(width=1920, height=1080),
        camera_resolution=Resolution(width=1280, height=720)
    )

    if calibration_data.quality.is_acceptable:
        print(f"✓ Calibration successful! RMS error: {calibration_data.quality.reprojection_error_rms:.2f}px")
    else:
        print("⚠ Calibration quality low, consider re-running")

# Runtime - display target
target = TargetDefinition(
    game_position=Point2D(x=0.5, y=0.3),
    radius=0.05,
    color=(255, 0, 0),
    duration=5.0
)

target_proj_pos = calibration.game_to_projector(target.game_position)
display_target(target_proj_pos, target.radius, target.color)

# Runtime - detect impact (generic - works for any projectile)
camera_pos = detect_impact_in_camera()  # Returns Point2D(x=640, y=360)
game_pos = calibration.camera_to_game(camera_pos)

impact = ImpactDetection(
    camera_position=camera_pos,
    game_position=game_pos,
    confidence=0.95,
    timestamp=datetime.now(),
    blob_area=1200  # Optional metadata from detection
)

# Check hit (using Pydantic models)
distance = np.sqrt(
    (impact.game_position.x - target.game_position.x)**2 +
    (impact.game_position.y - target.game_position.y)**2
)

hit_result = HitResult(
    hit=(distance < target.radius),
    target=target,
    impact=impact,
    distance=distance,
    points=100 if distance < target.radius else 0
)

if hit_result.hit:
    print(f"HIT! Distance: {hit_result.distance:.3f}, Points: {hit_result.points}")

# Serialization for IPC (if needed)
# Send to another process
hit_result_json = hit_result.model_dump_json()
send_to_game_engine(hit_result_json)

# Receive in game engine process
received_hit = HitResult.model_validate_json(hit_result_json)
```

## Impact Detection Strategies

The calibration system enables multiple detection strategies. Each strategy uses the homography differently.

### Strategy 1: Persistence Tracking (Simplest)

**Use Case**: Projectiles that stick to surface (real arrows, darts, axes in soft target)

**Approach**:
1. Maintain background model of empty target surface
2. Frame differencing to detect new objects
3. Color segmentation for high-visibility projectiles
4. Blob detection to find object centroid
5. Apply homography: camera coords → game coords

**Calibration Usage**: Single direction (Camera → Game)

**Pros**: Simple, robust, works with basic cameras
**Cons**: Only works for projectiles that persist on surface

### Strategy 2: Projected Pattern Differencing (Advanced)

**Use Case**: Transient impacts (balls, beanbags, foam-tip arrows that bounce)

**Approach**:
1. **Project known pattern** onto target surface (could be game graphics or dedicated detection pattern)
2. **Predict camera view**: Use inverse homography to compute what camera SHOULD see
   ```python
   # H_cam_to_proj is our calibration homography
   # We want H_proj_to_cam (inverse)
   H_proj_to_cam = np.linalg.inv(H_cam_to_proj)

   # For each pixel in projector image, predict where it appears in camera
   expected_camera_frame = warp_projector_to_camera(
       projector_frame,
       H_proj_to_cam,
       camera_resolution
   )
   ```
3. **Capture actual camera view**
4. **Compute difference**: `diff = actual_camera - expected_camera`
5. **Detect occlusions**: Where object blocks/distorts projected pattern
6. **Track object position** across frames (optical flow or blob tracking)
7. **Find minimum velocity**: Frame where object is closest to surface (impact moment)
8. **Extract impact location**: Centroid of occlusion blob at min velocity frame
9. **Apply homography**: camera coords → game coords

**Calibration Usage**:
- Forward: Projector → Camera (predict expected view)
- Inverse: Camera → Game (map detected impact)

**Pros**:
- Works for any projectile (no special colors needed)
- Accurate impact timing (min velocity detection)
- Can work in various lighting conditions

**Cons**:
- Computationally intensive for pattern warping (but see optimization below)
- Requires higher frame rate (60fps+)
- More complex algorithm
- Requires good lighting control (projected pattern must be visible in camera)

**Optimization**: Pattern differencing only needs to run at the impact moment
- Use lightweight motion detection to track object and detect minimum velocity
- Only run full pattern differencing when impact is detected
- This reduces computational load significantly (expensive operation runs once per impact, not every frame)

**Implementation Notes** (Two-Phase Approach):

**Phase 1: Lightweight Motion Tracking** (runs every frame)
- Simple frame differencing or optical flow
- Track blob position and velocity
- Detect minimum velocity moment

**Phase 2: Precise Impact Location** (runs only at impact moment)
- Project known pattern, predict camera view, find occlusion
- Extract precise impact coordinates

```python
class ProjectedPatternDetector:
    """
    Detect transient impacts using two-phase approach:
    1. Lightweight motion tracking (continuous)
    2. Pattern differencing (only at impact moment)
    """

    def __init__(self, calibration: CalibrationData):
        self.H_cam_to_proj = calibration.homography_camera_to_projector.to_numpy()
        self.H_proj_to_cam = np.linalg.inv(self.H_cam_to_proj)
        self.proj_res = calibration.projector_resolution
        self.cam_res = calibration.camera_resolution

        # Background model for motion detection
        self.background_model = None

        # Track object positions for velocity calculation
        self.position_history: List[Tuple[Point2D, float]] = []  # (position, timestamp)
        self.velocity_history: List[float] = []

    def process_frame(
        self,
        camera_frame: np.ndarray,
        projector_frame: np.ndarray,
        timestamp: float
    ) -> Optional[ImpactDetection]:
        """
        Main processing loop - runs every frame.
        Uses lightweight tracking, only runs expensive pattern diff at impact.
        """
        # Phase 1: Lightweight motion detection (FAST - runs every frame)
        motion_position = self._detect_motion(camera_frame, timestamp)

        if motion_position is None:
            # No object detected, reset tracking
            self.position_history.clear()
            self.velocity_history.clear()
            return None

        # Track position history
        self.position_history.append((motion_position, timestamp))
        if len(self.position_history) > 10:
            self.position_history.pop(0)

        # Calculate current velocity
        velocity = self._calculate_velocity()
        self.velocity_history.append(velocity)
        if len(self.velocity_history) > 10:
            self.velocity_history.pop(0)

        # Check if this is impact moment (minimum velocity)
        if self.is_impact_moment():
            # Phase 2: Precise impact location (EXPENSIVE - runs once per impact)
            return self._extract_precise_impact(
                camera_frame,
                projector_frame,
                timestamp
            )

        return None  # Still tracking, no impact yet

    def _detect_motion(
        self,
        camera_frame: np.ndarray,
        timestamp: float
    ) -> Optional[Point2D]:
        """
        Phase 1: Lightweight motion detection.
        Uses simple background subtraction - very fast.
        """
        gray = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2GRAY)

        # Initialize background model if needed
        if self.background_model is None:
            self.background_model = gray.copy().astype(float)
            return None

        # Update background model (running average)
        cv2.accumulateWeighted(gray, self.background_model, 0.01)

        # Compute difference
        diff = cv2.absdiff(gray, self.background_model.astype(np.uint8))
        _, mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

        # Find largest blob
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)

        # Filter small noise
        if cv2.contourArea(largest) < 100:
            return None

        # Compute centroid
        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None

        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]

        return Point2D(x=cx, y=cy)

    def _extract_precise_impact(
        self,
        camera_frame: np.ndarray,
        projector_frame: np.ndarray,
        timestamp: float
    ) -> ImpactDetection:
        """
        Phase 2: Expensive pattern differencing for precise impact location.
        Only called when impact moment is detected.
        """
        # Predict what camera should see
        expected = cv2.warpPerspective(
            projector_frame,
            self.H_proj_to_cam,
            (self.cam_res.width, self.cam_res.height)
        )

        # Compute difference
        diff = cv2.absdiff(camera_frame, expected)

        # Threshold to find occlusions
        _, mask = cv2.threshold(
            cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY),
            30,
            255,
            cv2.THRESH_BINARY
        )

        # Find projectile blob
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            # Fallback to lightweight detection position
            if self.position_history:
                camera_pos, _ = self.position_history[-1]
            else:
                # Should not happen, but handle gracefully
                camera_pos = Point2D(x=self.cam_res.width/2, y=self.cam_res.height/2)
        else:
            largest = max(contours, key=cv2.contourArea)
            M = cv2.moments(largest)
            if M["m00"] > 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
                camera_pos = Point2D(x=cx, y=cy)
            else:
                camera_pos, _ = self.position_history[-1]

        # Convert to game coordinates using homography
        cam_pt = np.array([[camera_pos.x, camera_pos.y]], dtype=np.float32)
        proj_pt = cv2.perspectiveTransform(
            cam_pt.reshape(-1, 1, 2),
            self.H_cam_to_proj
        )[0][0]

        game_x = proj_pt[0] / self.proj_res.width
        game_y = proj_pt[1] / self.proj_res.height

        return ImpactDetection(
            camera_position=camera_pos,
            game_position=Point2D(x=game_x, y=game_y),
            confidence=0.9,
            timestamp=datetime.fromtimestamp(timestamp),
            velocity=self.velocity_history[-1] if self.velocity_history else 0.0
        )

    def _calculate_velocity(self) -> float:
        """Calculate current velocity from position history."""
        if len(self.position_history) < 2:
            return 0.0

        # Velocity: distance / time between last two positions
        (p1, t1), (p2, t2) = self.position_history[-2:]
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        distance = np.sqrt(dx**2 + dy**2)
        dt = t2 - t1

        return distance / dt if dt > 0 else 0.0

    def is_impact_moment(self, velocity_threshold: float = 20.0) -> bool:
        """
        Detect if current moment is likely an impact.
        Impact = local minimum velocity (object stops briefly at surface).
        """
        if len(self.velocity_history) < 3:
            return False

        # Check if current velocity is local minimum
        current = self.velocity_history[-1]
        prev = self.velocity_history[-2]
        prev_prev = self.velocity_history[-3]

        # Impact conditions:
        # 1. Current velocity is low (below threshold)
        # 2. Velocity was decreasing (prev > current)
        # 3. Previous velocity was higher (indicates deceleration to stop)
        is_low = current < velocity_threshold
        is_decreasing = prev > current
        was_higher = prev_prev > current

        return is_low and is_decreasing and was_higher
```

**Performance Comparison**:
- **Without optimization**: Warp full projector frame every frame (60fps × expensive warp = ~100ms/frame = unusable)
- **With optimization**: Lightweight motion tracking every frame (~2ms/frame) + pattern differencing once per impact (~50ms once) = **usable at 60fps**

### Strategy 3: Dual Camera Stereoscopic (Hardware Intensive)

**Use Case**: Transient impacts with precise 3D tracking

**Approach**:
1. Two cameras viewing target from different angles
2. Stereo calibration to compute 3D positions
3. Track projectile in 3D space
4. Detect minimum Z-velocity (approaching/leaving surface)
5. Project 3D impact point onto 2D target surface
6. Apply homography: camera coords → game coords

**Calibration Usage**: Each camera needs separate homography calibration

**Pros**: Most accurate 3D tracking, works for any projectile
**Cons**: Requires two cameras, complex stereo calibration, higher cost

### Recommended Approach for Initial Implementation

**Phase 1**: Implement calibration system (works for all strategies)
**Phase 2**: Implement persistence tracking (simplest, validate calibration works)
**Phase 3**: Implement projected pattern differencing (enables transient impacts)

The beauty of this architecture is that the **calibration system remains identical** across all strategies. Only the detection module changes.

## Calibration Pattern Generator

### Module: `calibration_pattern.py`

**Responsibility**: Generate calibration patterns for projection

```python
def generate_aruco_grid(
    projector_resolution,
    grid_size=(4, 4),
    marker_dict=cv2.aruco.DICT_4X4_50,
    margin_percent=0.1
):
    """
    Generate ArUco marker grid pattern.

    Args:
        projector_resolution: (width, height) in pixels
        grid_size: (cols, rows) number of markers
        marker_dict: ArUco dictionary to use
        margin_percent: Border margin as fraction of frame

    Returns:
        image: numpy array ready to display
        marker_positions: dict mapping marker_id -> (x, y) center in projector coords
    """
```

**Design Considerations**:
- Markers should be large enough to detect reliably (min ~100x100px projected)
- Spacing between markers for clear separation
- White background, black markers for contrast
- Return both the image AND the ground truth positions

## Detection Module

### Module: `pattern_detector.py`

**Responsibility**: Detect calibration pattern in camera frames

```python
def detect_aruco_markers(
    camera_frame,
    marker_dict=cv2.aruco.DICT_4X4_50,
    expected_ids=None
):
    """
    Detect ArUco markers in camera image.

    Args:
        camera_frame: numpy array from camera
        marker_dict: Which ArUco dictionary was used
        expected_ids: Optional list of marker IDs we expect to see

    Returns:
        detections: list of (marker_id, corners_2d) tuples
        success: bool indicating if minimum markers detected
    """
```

**Error Handling**:
- Return partial results even if not all markers detected
- Provide feedback on what's missing ("Only detected 12/16 markers")
- Suggest fixes ("Move camera to see top-right corner")

## Homography Computation Module

### Module: `homography.py`

**Responsibility**: Compute and validate geometric transformations

```python
def compute_homography(source_points, dest_points):
    """
    Compute homography matrix from point correspondences.

    Returns:
        H: 3x3 homography matrix (numpy array)
        inlier_mask: which points were inliers in RANSAC
        reprojection_error: RMS error in pixels
    """

def apply_homography(H, points):
    """
    Apply homography transformation to points.

    Args:
        H: 3x3 homography matrix
        points: Nx2 array of points or single (x,y) tuple

    Returns:
        transformed_points: same shape as input
    """

def validate_homography(H, test_point_pairs, threshold=3.0):
    """
    Validate homography quality.

    Returns:
        is_valid: bool
        metrics: dict with error statistics
    """
```

## Testing Strategy

### Unit Tests
1. **Pattern Generation**:
   - Verify marker positions are correctly computed
   - Check image dimensions match projector resolution
   - Validate marker spacing (no overlaps)

2. **Detection**:
   - Test with synthetic images (known marker positions)
   - Test with partial occlusion
   - Test with various lighting conditions (synthetic noise)

3. **Homography Computation**:
   - Test with identity transformation (points map to themselves)
   - Test with known transformations (rotation, translation, scale)
   - Test robustness to outliers

### Integration Tests
1. **Simulated Calibration**:
   - Generate synthetic "camera view" of calibration pattern
   - Run full calibration pipeline
   - Verify recovered transformation matches ground truth

2. **Round-trip Accuracy**:
   - Project test points: Game → Projector → Camera → Game
   - Verify final coordinates match original

### Physical Tests (Hardware Required)
1. **Calibration Repeatability**:
   - Run calibration 5 times without moving camera
   - Verify homography matrices are nearly identical
   - Error should be < 1 pixel between runs

2. **Detection Accuracy**:
   - Place physical markers at known positions on target
   - Project marker indicators at those game coordinates
   - Verify alignment in camera view
   - Test at corners, center, edges

3. **Impact Detection Validation**:
   - Point projectile (finger, stick, laser pointer) at projected target
   - Verify detected position matches target position
   - Test at 10+ different positions across target surface
   - Acceptable error: < 5cm on target surface (maps to ~20-30 pixels depending on resolution)
   - Test with actual projectile once detection method is implemented

## Error Handling and Edge Cases

### Calibration Failures
1. **Insufficient Markers Detected**:
   - Cause: Camera can't see full pattern, poor lighting, motion blur
   - Response: Display live detection overlay, guide user to adjust camera

2. **Poor Homography Quality**:
   - Cause: Markers detected but high reprojection error
   - Response: Flag specific problematic areas, suggest recalibration

3. **Camera/Projector Moved After Calibration**:
   - Detection: Runtime validation check (periodic or on-demand)
   - Response: Alert user, request recalibration

### Runtime Issues
1. **Coordinates Outside Valid Range**:
   - Impact detected outside expected projection area
   - Possible causes: False detection, projectile missed target entirely
   - Response: Clamp to [0, 1] or reject as invalid hit

2. **Homography Singularity**:
   - Rare but possible with degenerate point configurations
   - Response: Catch during calibration, force recalibration

## Configuration and Tuning Parameters

Configuration is managed via the `CalibrationConfig` Pydantic model (defined earlier). This provides:
- Type safety and validation
- Easy serialization to/from JSON
- Default values with constraints
- IDE autocomplete support

**Usage**:

```python
# Use defaults
config = CalibrationConfig()

# Override specific parameters
config = CalibrationConfig(
    grid_size=(5, 5),
    min_markers_required=20,
    ransac_threshold=3.0,
    interactive_verification=True
)

# Load from JSON file (optional)
with open("calibration_config.json") as f:
    config = CalibrationConfig.model_validate_json(f.read())

# Save to JSON file
with open("calibration_config.json", "w") as f:
    f.write(config.model_dump_json(indent=2))
```

**Default Configuration** (see `CalibrationConfig` model definition):
- `pattern_type`: "aruco"
- `aruco_dict`: "DICT_4X4_50"
- `grid_size`: (4, 4)
- `margin_percent`: 0.1
- `min_markers_required`: 12 (out of 16 for 4x4 grid)
- `ransac_threshold`: 5.0 pixels
- `max_reprojection_error`: 3.0 pixels
- `corner_test_enabled`: True
- `interactive_verification`: False
- `auto_save`: True
- `calibration_dir`: "./calibration_data"
- `keep_history`: 5

**Tuning Guidelines**:
- Increase `grid_size` to (5, 5) or (6, 6) for higher accuracy (requires more detection time)
- Decrease `ransac_threshold` for stricter outlier rejection (may reject valid points)
- Enable `interactive_verification` for initial testing/debugging
- Adjust `min_markers_required` based on camera field of view

## Performance Considerations

### Calibration Phase (One-time)
- **Target Time**: < 30 seconds total
  - Pattern projection: instant
  - User positioning: ~10-20 seconds
  - Detection + computation: < 5 seconds
- **Optimization**: Not critical, clarity and robustness more important

### Runtime Phase (Per Frame)
- **Target Latency**: < 16ms (for 60fps camera)
  - Impact detection: < 10ms (varies by detection method)
  - Homography transform: < 1ms (matrix multiplication)
  - Game logic: < 5ms
- **Optimization**:
  - Homography application is just matrix multiply - very fast
  - Cache numpy arrays, avoid allocations
  - The stored calibration means NO pattern detection at runtime

## Dependencies

### Required

```txt
opencv-contrib-python>=4.8.0  # Computer vision + ArUco markers
numpy>=1.24.0                  # Numerical operations
pygame>=2.5.0                  # Display/rendering for projector output
pydantic>=2.0.0                # Data validation and serialization
```

**Note**: `opencv-contrib-python` includes ArUco marker support, which is essential for the recommended calibration pattern approach. If you already have `opencv-python` installed, uninstall it first to avoid conflicts.

### Optional

```txt
pytest>=7.4.0          # Testing framework
pillow>=10.0.0         # Image loading/manipulation helpers
```

## Implementation Order

### Phase 1: Core Infrastructure (Week 1)
1. Set up project structure (`/calibration` module)
2. **Define Pydantic data models** (`models.py`) - Do this FIRST
3. Implement pattern generation (ArUco grid)
4. Implement pattern detection
5. Basic homography computation

### Phase 2: Calibration Pipeline (Week 1-2)
1. Implement CalibrationManager class
2. Add validation and quality metrics
3. Implement persistence (save/load)
4. Build calibration UI (simple pygame display + camera view)

### Phase 3: Testing and Validation (Week 2)
1. Unit tests for all modules
2. Simulated calibration tests
3. Physical hardware tests with actual projector/camera
4. Tune parameters based on real-world performance

### Phase 4: Integration with Game Engine (Week 3)
1. API integration with game loop
2. Error handling for edge cases
3. Runtime validation checks
4. Performance profiling

## Success Criteria

The calibration system is complete when:

1. ✅ Calibration completes in < 30 seconds with clear user feedback
2. ✅ Reprojection error consistently < 3 pixels RMS
3. ✅ Impact detection accuracy within 5cm on physical target surface
4. ✅ Calibration persists across sessions (save/load works)
5. ✅ Clean API that game engine can use with < 10 lines of code
6. ✅ Robust error handling with helpful user guidance
7. ✅ Works with camera at arbitrary angle (within reason - must see target)
8. ✅ Works in various lighting conditions (indoor, outdoor/daylight)
9. ✅ **Use-case agnostic**: No hardcoded assumptions about projectile type

## Future Enhancements (Post-MVP)

1. **Multi-target Calibration**: Support non-planar surfaces or multiple surfaces
2. **Auto-Calibration Validation**: Periodic checks that calibration is still valid
3. **Camera Distortion Correction**: Account for lens distortion (currently assuming minimal)
4. **Adaptive Lighting**: Adjust detection parameters based on ambient light
5. **Mobile Calibration UI**: Tablet/phone app for easier calibration control

## References and Resources

- OpenCV Homography Tutorial: https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html
- ArUco Marker Detection: https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html
- Projector-Camera Calibration (academic): Research "structured light" and "projector-camera systems"
