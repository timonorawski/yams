# CV Detection Backend Implementation Plan

**Status**: Planning
**Date**: October 27, 2025
**Prerequisites**: AMS architecture validated with mouse input, geometric calibration system working

---

## Executive Summary

This document plans the implementation of the CV Detection Backend for the Arcade Management System (AMS). This will enable real computer vision-based impact detection for transient projectiles (foam-tip arrows, balls, beanbags) using the interstitial calibration approach described in AMS.md.

### What We're Building

A `CVDetectionBackend` class that:
1. Implements the `DetectionBackend` interface (drop-in replacement for mouse input)
2. Performs color characterization calibration between rounds
3. Detects transient impacts using two-phase approach (lightweight motion tracking + pattern differencing)
4. Reports ~150ms detection latency for temporal query adjustment
5. Integrates with existing geometric calibration (ArUco homography)

### What We Already Have

✅ **AMS Framework** (fully working with mouse):
- `DetectionBackend` interface
- `TemporalGameState` with latency-adjusted temporal queries
- `PlaneHitEvent` with `latency_ms` field
- Session management and calibration workflow
- Demo game validating complete data flow

✅ **Geometric Calibration** (tested with hardware):
- ArUco marker detection
- Homography computation (camera ↔ projector)
- `CalibrationManager` API
- Tested: 0.25 pixel RMS error (excellent)

### What We Need to Build

🔨 **Color Characterization System**:
- Background characterization (empty surface under each color)
- Object characterization (projectile appearance under each color)
- Palette quality scoring (contrast computation)
- Integration into `CalibrationSession`

🔨 **CV Detection Backend**:
- Two-phase transient impact detection
- Integration with geometric calibration
- Camera interface and frame capture
- Event generation with correct latency reporting

🔨 **Interstitial Calibration UX**:
- Between-round calibration workflow
- Visual feedback (color cycling as "dramatic lighting")
- Progress callbacks and user prompts
- Subliminal ArUco flash (2-3 frames) for geometric recalibration

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    GEOMETRIC CALIBRATION                         │
│                 (One-time at setup, ~30 seconds)                 │
├─────────────────────────────────────────────────────────────────┤
│  1. Display ArUco marker grid (4x4)                             │
│  2. Detect markers in camera view                               │
│  3. Compute homography: Camera ↔ Projector                      │
│  4. Store in CalibrationData (already implemented ✅)           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   COLOR CALIBRATION PHASES                       │
│            (Between rounds, ~3-6 seconds per round)              │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1: Display Latency Measurement (~0.5s)                   │
│    - Button press → pattern appears → camera detects             │
│    - Measure projector→camera latency                            │
│                                                                   │
│  Phase 2: Background Characterization (~3s)                      │
│    - Cycle through 8-10 candidate colors                         │
│    - Project each color on empty surface                         │
│    - Capture 5-10 frames per color                              │
│    - Compute statistics: mean, variance, histogram               │
│    - Store: background_model[color] = statistics                 │
│                                                                   │
│  Phase 3: Object Characterization (~3s)                          │
│    - "Hold projectile in view"                                   │
│    - Cycle through same colors                                   │
│    - Capture projectile appearance under each color              │
│    - Store: object_model[color] = statistics                     │
│                                                                   │
│  Phase 4: Compute Available Palette (~0.1s)                      │
│    - For each color: quality = contrast(object, background)      │
│    - Filter to colors with quality > threshold                   │
│    - Return list to game                                         │
│                                                                   │
│  Optional: Geometric Recalibration (2-3 frames)                  │
│    - Flash ArUco grid subliminally                               │
│    - Update homography if equipment drifted                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    RUNTIME DETECTION                             │
│                    (During gameplay)                              │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1: Lightweight Motion Tracking (every frame, ~2ms)        │
│    - Background subtraction                                      │
│    - Blob detection and centroid                                 │
│    - Track position history (10 frames)                          │
│    - Calculate velocity                                          │
│    - Detect minimum velocity → IMPACT                            │
│                                                                   │
│  Phase 2: Precise Impact Location (once per impact, ~50ms)       │
│    - Use H_proj_to_cam to predict expected camera view          │
│    - Warp projector frame to camera perspective                  │
│    - Compute difference: actual - expected                       │
│    - Detect occlusion blob (where object blocks pattern)         │
│    - Extract precise impact coordinates                          │
│    - Apply homography: Camera → Game coordinates                 │
│    - Emit PlaneHitEvent(x, y, timestamp, latency_ms=150)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Color Characterization System

### 1.1 Color Statistics Model

```python
# ams/color_analysis.py

from pydantic import BaseModel, Field
from typing import Dict, List, Tuple, Optional
import numpy as np

class ColorStatistics(BaseModel):
    """Statistics for a single color (background or object)."""
    color: Tuple[int, int, int]  # RGB color that was projected
    mean_rgb: Tuple[float, float, float]  # Mean color in camera
    std_rgb: Tuple[float, float, float]   # Standard deviation
    histogram: Optional[List[int]] = None  # Optional: grayscale histogram
    sample_count: int = Field(..., gt=0)   # Number of frames captured

    class Config:
        frozen = True

class ColorPalette(BaseModel):
    """Evaluated color palette with quality scores."""
    available_colors: List[Tuple[int, int, int]]  # Colors suitable for game
    color_quality: Dict[str, float]  # color_rgb_string -> quality [0, 1]
    detection_threshold: float = Field(default=0.7, ge=0, le=1)

    def is_color_usable(self, color: Tuple[int, int, int]) -> bool:
        """Check if a color is suitable for detection."""
        color_key = f"{color[0]},{color[1]},{color[2]}"
        return self.color_quality.get(color_key, 0) >= self.detection_threshold

class ColorCalibrationData(BaseModel):
    """Complete color characterization data."""
    background_stats: Dict[str, ColorStatistics]  # color_rgb_string -> stats
    object_stats: Dict[str, ColorStatistics]
    palette: ColorPalette
    display_latency_ms: Optional[float] = None
    timestamp: datetime

    def save(self, filepath: str):
        """Save to JSON."""
        with open(filepath, 'w') as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, filepath: str) -> 'ColorCalibrationData':
        """Load from JSON."""
        with open(filepath, 'r') as f:
            return cls.model_validate_json(f.read())
```

### 1.2 Color Analysis Functions

```python
# ams/color_analysis.py (continued)

def characterize_color(
    camera_frames: List[np.ndarray],
    projected_color: Tuple[int, int, int],
    mask: Optional[np.ndarray] = None
) -> ColorStatistics:
    """
    Analyze how a projected color appears in camera frames.

    Args:
        camera_frames: List of frames captured while projecting this color
        projected_color: RGB color that was projected
        mask: Optional mask of region to analyze (for object characterization)

    Returns:
        ColorStatistics with mean, std, histogram
    """
    all_pixels = []

    for frame in camera_frames:
        if mask is not None:
            # Extract only masked region (object characterization)
            pixels = frame[mask > 0]
        else:
            # Use entire frame (background characterization)
            pixels = frame.reshape(-1, 3)

        all_pixels.append(pixels)

    all_pixels = np.vstack(all_pixels)

    mean_rgb = tuple(np.mean(all_pixels, axis=0))
    std_rgb = tuple(np.std(all_pixels, axis=0))

    # Optional: grayscale histogram
    gray = np.mean(all_pixels, axis=1)
    histogram, _ = np.histogram(gray, bins=64, range=(0, 255))

    return ColorStatistics(
        color=projected_color,
        mean_rgb=mean_rgb,
        std_rgb=std_rgb,
        histogram=histogram.tolist(),
        sample_count=len(camera_frames)
    )

def compute_contrast(
    background_stats: ColorStatistics,
    object_stats: ColorStatistics
) -> float:
    """
    Compute detection quality for a color.

    Higher values = better separation between object and background.

    Returns:
        Quality score [0, 1]
    """
    # Euclidean distance in RGB space
    bg_mean = np.array(background_stats.mean_rgb)
    obj_mean = np.array(object_stats.mean_rgb)

    color_distance = np.linalg.norm(obj_mean - bg_mean)

    # Normalize by maximum possible distance
    max_distance = np.sqrt(3 * 255**2)
    normalized_distance = color_distance / max_distance

    # Penalize high variance (unstable appearance)
    bg_variance = np.mean(background_stats.std_rgb)
    obj_variance = np.mean(object_stats.std_rgb)
    variance_penalty = (bg_variance + obj_variance) / (2 * 255)

    quality = normalized_distance * (1 - 0.5 * variance_penalty)

    return float(np.clip(quality, 0, 1))

def compute_color_palette(
    background_stats: Dict[str, ColorStatistics],
    object_stats: Dict[str, ColorStatistics],
    threshold: float = 0.7
) -> ColorPalette:
    """
    Determine which colors are suitable for detection.

    Args:
        background_stats: Background appearance for each color
        object_stats: Object appearance for each color
        threshold: Minimum quality score to be usable

    Returns:
        ColorPalette with available colors and quality scores
    """
    color_quality = {}
    available_colors = []

    for color_key in background_stats.keys():
        if color_key not in object_stats:
            continue

        bg_stat = background_stats[color_key]
        obj_stat = object_stats[color_key]

        quality = compute_contrast(bg_stat, obj_stat)
        color_quality[color_key] = quality

        if quality >= threshold:
            available_colors.append(bg_stat.color)

    return ColorPalette(
        available_colors=available_colors,
        color_quality=color_quality,
        detection_threshold=threshold
    )
```

### 1.3 Integration into CalibrationSession

Update `ams/calibration.py` to actually perform color characterization:

```python
# ams/calibration.py (updates to existing file)

def _characterize_background(self) -> Dict[str, Any]:
    """
    Phase 2: Background characterization.

    Cycle through candidate colors, capture empty surface appearance.
    """
    if not hasattr(self.backend, 'camera'):
        # Non-CV backend (mouse, etc.) - return empty
        return {}

    camera = self.backend.camera
    background_stats = {}

    for i, color in enumerate(self.CANDIDATE_COLORS):
        # Visual feedback
        progress = (i + 1) / len(self.CANDIDATE_COLORS)
        self._update_progress(
            self._progress_callback,
            "background",
            0.5 + progress * 0.15,  # Maps to 50-65% overall progress
            f"Analyzing background color {i+1}/{len(self.CANDIDATE_COLORS)}"
        )

        # Project this color on entire surface
        self.backend.project_solid_color(color)
        time.sleep(0.1)  # Allow projector/camera to stabilize

        # Capture multiple frames
        frames = []
        for _ in range(5):
            frame = camera.capture_frame()
            frames.append(frame)
            time.sleep(0.05)  # 20 fps

        # Analyze
        stats = color_analysis.characterize_color(
            frames,
            projected_color=color,
            mask=None  # Full frame for background
        )

        color_key = f"{color[0]},{color[1]},{color[2]}"
        background_stats[color_key] = stats

    return background_stats

def _characterize_object(self) -> Dict[str, Any]:
    """
    Phase 3: Object characterization.

    User holds projectile in view, we capture appearance under each color.
    """
    if not hasattr(self.backend, 'camera'):
        return {}

    camera = self.backend.camera
    object_stats = {}

    # Prompt user
    self._update_progress(
        self._progress_callback,
        "object",
        0.65,
        "Hold projectile in view (center of projection area)"
    )
    time.sleep(2)  # Give user time to position object

    for i, color in enumerate(self.CANDIDATE_COLORS):
        progress = (i + 1) / len(self.CANDIDATE_COLORS)
        self._update_progress(
            self._progress_callback,
            "object",
            0.65 + progress * 0.20,  # Maps to 65-85% overall progress
            f"Analyzing object color {i+1}/{len(self.CANDIDATE_COLORS)}"
        )

        # Project this color
        self.backend.project_solid_color(color)
        time.sleep(0.1)

        # Capture frames
        frames = []
        for _ in range(5):
            frame = camera.capture_frame()
            frames.append(frame)
            time.sleep(0.05)

        # Detect object blob in center of frame (user is holding it there)
        # Simple approach: center region is object, everything else is background
        h, w = frames[0].shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        center_y, center_x = h // 2, w // 2
        radius = min(h, w) // 6
        cv2.circle(mask, (center_x, center_y), radius, 255, -1)

        # Analyze
        stats = color_analysis.characterize_color(
            frames,
            projected_color=color,
            mask=mask
        )

        color_key = f"{color[0]},{color[1]},{color[2]}"
        object_stats[color_key] = stats

    return object_stats

def _compute_palette(
    self,
    background_stats: Dict[str, Any],
    object_stats: Dict[str, Any]
) -> List[tuple]:
    """
    Phase 4: Compute available color palette.
    """
    if not background_stats or not object_stats:
        # Fallback for non-CV backends
        return self.CANDIDATE_COLORS.copy()

    # Use color analysis module
    palette = color_analysis.compute_color_palette(
        background_stats,
        object_stats,
        threshold=0.7
    )

    return palette.available_colors
```

---

## Phase 0: Laser Pointer Testing Backend (Recommended First Step)

### Rationale

Before implementing the full CV detection system with motion tracking and pattern differencing, implementing a simpler **laser pointer detection backend** provides:

1. **Rapid validation** of geometric calibration accuracy
2. **Testing platform** for temporal query system with real-time input
3. **Debugging tool** to isolate coordinate transformation vs detection algorithm issues
4. **Faster iteration** during game development (no object retrieval delays)
5. **Safer development** environment (no thrown objects indoors)

**Implementation time**: ~1 day vs ~4 weeks for full CV backend

**Validation coverage**: ~90% of system with ~10% of complexity

### Detection Type Comparison

| Aspect | Laser Pointer | Thrown Object (CV) |
|--------|--------------|-------------------|
| **Appearance in camera** | Bright spot (adds light) | Dark occlusion (blocks light) |
| **Motion pattern** | Continuous smooth motion | Parabolic trajectory with impact |
| **Detection method** | Brightness threshold + blob | Motion tracking + pattern diff |
| **Latency** | ~50ms (very simple) | ~150ms (complex processing) |
| **Calibration needs** | Background only | Background + object |
| **Testing speed** | Instant feedback | Retrieve object each throw |
| **Precision** | Trace exact patterns | Limited by throw accuracy |

### 0.1 Laser Detection Backend Implementation

```python
# ams/laser_detection_backend.py

from typing import List, Optional
import time
import numpy as np
import cv2
from ams.detection_backend import DetectionBackend
from ams.events import PlaneHitEvent, CalibrationResult
from ams.camera import CameraInterface
from calibration.calibration_manager import CalibrationManager
from models import Point2D

class LaserDetectionBackend(DetectionBackend):
    """
    Laser pointer detection backend for testing and development.

    Advantages over full CV detection:
    - 10x simpler implementation
    - Instant feedback (no object retrieval)
    - Precise validation of coordinate mapping
    - Can trace exact patterns for accuracy testing
    - Safer for indoor development

    Use for:
    - Validating geometric calibration
    - Testing temporal query system
    - Rapid game development iteration
    - Debugging coordinate transformations
    - Demos without thrown objects
    """

    def __init__(
        self,
        camera: CameraInterface,
        calibration_manager: CalibrationManager,
        display_width: int,
        display_height: int
    ):
        """
        Initialize laser detection backend.

        Args:
            camera: Camera interface for frame capture
            calibration_manager: Geometric calibration manager
            display_width: Display width in pixels
            display_height: Display height in pixels
        """
        super().__init__(display_width, display_height)

        self.camera = camera
        self.calibration_manager = calibration_manager
        self.detection_latency_ms = 50.0  # Much lower than CV (~150ms)

        # Detection parameters
        self.brightness_threshold = 200  # Laser spot is very bright (0-255)
        self.min_spot_size = 5           # Minimum pixels
        self.max_spot_size = 100         # Maximum pixels

        # Event queue
        self._event_queue: List[PlaneHitEvent] = []

        # Optional: Track last position for debouncing
        self._last_position: Optional[Point2D] = None
        self._last_detection_time: float = 0
        self._min_detection_interval: float = 0.1  # 100ms minimum between events

    def update(self, dt: float):
        """
        Update detection (called every frame).

        Detects bright laser spot in camera frame.
        Much simpler than projectile detection - no motion tracking needed.
        """
        # Capture camera frame
        frame = self.camera.capture_frame()
        timestamp = time.monotonic()

        # Convert to grayscale for brightness analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Threshold for very bright spots (laser pointer)
        # Laser pointers are typically 200-255 brightness
        _, bright_spots = cv2.threshold(
            gray,
            self.brightness_threshold,
            255,
            cv2.THRESH_BINARY
        )

        # Morphological operations to clean noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        bright_spots = cv2.morphologyEx(bright_spots, cv2.MORPH_OPEN, kernel)

        # Find contours (bright blobs)
        contours, _ = cv2.findContours(
            bright_spots,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            self._last_position = None
            return  # No laser detected

        # Find largest bright spot (assume it's the laser)
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)

        # Validate spot size (filter out noise and reflections)
        if not (self.min_spot_size < area < self.max_spot_size):
            return

        # Get centroid
        M = cv2.moments(largest)
        if M["m00"] == 0:
            return

        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        camera_pos = Point2D(x=cx, y=cy)

        # Optional: Debounce rapid detections (prevent spam)
        if self._last_position is not None:
            # Check if moved significantly
            dx = abs(camera_pos.x - self._last_position.x)
            dy = abs(camera_pos.y - self._last_position.y)

            # Also check time interval
            time_since_last = timestamp - self._last_detection_time

            # Skip if too close to last detection (both spatially and temporally)
            if dx < 5 and dy < 5 and time_since_last < self._min_detection_interval:
                return

        # Transform to game coordinates
        game_pos = self.calibration_manager.camera_to_game(camera_pos)

        # Create event
        event = PlaneHitEvent(
            x=game_pos.x,
            y=game_pos.y,
            timestamp=timestamp,
            confidence=0.99,  # Very high confidence for laser (unambiguous)
            detection_method="laser_pointer",
            latency_ms=self.detection_latency_ms,
            metadata={
                'camera_position': {'x': camera_pos.x, 'y': camera_pos.y},
                'spot_area': int(area),
                'brightness': int(gray[int(cy), int(cx)])  # Sample brightness
            }
        )

        self._event_queue.append(event)
        self._last_position = camera_pos
        self._last_detection_time = timestamp

    def poll_events(self) -> List[PlaneHitEvent]:
        """Get all pending detection events."""
        events = self._event_queue.copy()
        self._event_queue.clear()
        return events

    def calibrate(self) -> CalibrationResult:
        """
        Laser pointer backend doesn't need color characterization.

        Laser is self-illuminated, so background color doesn't affect detection.
        Only geometric calibration is needed (already done).
        """
        return CalibrationResult(
            success=True,
            method="laser_pointer_no_op",
            available_colors=None,  # N/A for laser
            display_latency_ms=self.detection_latency_ms,
            notes="Laser pointer backend requires no color calibration"
        )

    def set_brightness_threshold(self, threshold: int):
        """
        Adjust brightness threshold for different laser colors/powers.

        Args:
            threshold: Brightness threshold (0-255)
                - Green lasers: 180-200 (very bright)
                - Red lasers: 150-180 (dimmer)
                - Weak lasers: 120-150
        """
        self.brightness_threshold = max(100, min(240, threshold))
```

### 0.2 Testing Strategy with Laser Pointer

**Week 0: Laser Backend Development** (~1 day)
```python
# Implement LaserDetectionBackend
# Test basic spot detection with camera
# Validate coordinate transformation accuracy
```

**Week 1: Geometric Validation**
```python
# Test 1: Corner Testing
# - Point laser at all 4 corners of projection
# - Verify game coordinates = (0,0), (1,0), (1,1), (0,1)
# - Measure error (should be < 2cm with good calibration)

# Test 2: Perimeter Trace
# - Trace laser around entire projection perimeter
# - Plot normalized coordinates
# - Verify uniform mapping, detect distortions

# Test 3: Grid Pattern
# - Point laser at 5x5 grid points
# - Compare detected positions to expected positions
# - Compute RMS error across entire field
```

**Week 2: Temporal Query Validation**
```python
# Test 1: Moving Targets
# - Game displays target at precise time
# - User aims laser at target
# - Verify temporal query finds target at correct historical state

# Test 2: Latency Stress Test
# - Targets appear/disappear with 100ms timing
# - Test if 50ms laser latency is correctly adjusted
# - Should have higher hit rate than 150ms CV latency

# Test 3: Rapid Fire
# - Click laser rapidly at multiple targets
# - Verify all events processed correctly
# - Check for event queue overflow issues
```

**Week 3: Game Integration**
```python
# Test 1: Play SimpleTargetGame with laser
# - Compare hit accuracy to mouse input (baseline)
# - Track false positives/negatives
# - Measure coordinate precision

# Test 2: Continuous Game Session
# - Play for 5 minutes without issues
# - Monitor performance (frame rate, latency)
# - Check for memory leaks or degradation

# Test 3: Between-Round Calibration
# - Verify laser backend skips color characterization
# - Confirm geometric recalibration works (if enabled)
# - Test that games receive updated color palette (should be full)
```

### 0.3 Validation Tests

**Geometric Accuracy Test**
```python
# test_laser_geometric_accuracy.py

def test_corner_accuracy():
    """Verify laser detection at projection corners."""
    laser_backend = LaserDetectionBackend(camera, calib_manager, 1280, 720)

    # Define expected corners in projector space
    corners_proj = [
        (0, 0),      # Top-left
        (1280, 0),   # Top-right
        (1280, 720), # Bottom-right
        (0, 720)     # Bottom-left
    ]

    # Point laser at each corner, capture position
    detected_corners = []
    for corner in corners_proj:
        # User points laser at corner
        input("Point laser at corner {}, press Enter".format(corner))

        # Capture detection
        laser_backend.update(0.016)
        events = laser_backend.poll_events()

        if events:
            detected_corners.append((events[0].x, events[0].y))

    # Compute error
    expected_game = [(0, 0), (1, 0), (1, 1), (0, 1)]
    errors = []
    for detected, expected in zip(detected_corners, expected_game):
        dx = detected[0] - expected[0]
        dy = detected[1] - expected[1]
        error = np.sqrt(dx*dx + dy*dy)
        errors.append(error)

    rms_error = np.sqrt(np.mean(np.array(errors)**2))

    print(f"Corner detection RMS error: {rms_error:.4f} (normalized)")
    print(f"Corner detection RMS error: {rms_error * 1280:.1f} pixels")

    assert rms_error < 0.01, "Corner error too high (> 1% of screen)"
```

**Temporal Query Test**
```python
# test_laser_temporal.py

def test_temporal_query_accuracy():
    """Verify temporal queries work correctly with laser latency."""
    game = SimpleTargetGame(1280, 720)
    laser_backend = LaserDetectionBackend(camera, calib_manager, 1280, 720)

    # Spawn target at known position
    target_pos = (0.5, 0.5)
    game.spawn_target_at(target_pos)

    # Wait for state to be captured
    game.update(0.016)
    time.sleep(0.1)

    # Point laser at target
    input("Point laser at center target, press Enter")

    # Capture detection
    laser_backend.update(0.016)
    events = laser_backend.poll_events()

    assert len(events) > 0, "No laser detection"

    # Query game with latency adjustment
    result = game.handle_hit_event(events[0])

    assert result.hit, "Should hit target at center"
    print(f"Hit detected! Distance: {result.distance:.4f}")
```

### 0.4 Advantages for Development

**Rapid Iteration**
- Test detection changes in seconds, not minutes
- No need to retrieve thrown objects
- Can run hundreds of tests in an hour
- Instant validation of code changes

**Precision Validation**
- Trace exact patterns (circles, lines, grids)
- Measure coordinate accuracy at every point
- Identify systematic errors/distortions
- Validate homography quality empirically

**Safer Development**
- No risk of damaging equipment with thrown objects
- Can develop indoors without safety concerns
- Easier to demonstrate to stakeholders
- Children can safely test games

**Debugging Tool**
- When CV detection fails, laser pointer can isolate root cause:
  - If laser fails → geometric calibration issue
  - If laser works but CV fails → detection algorithm issue
- Provides ground truth for comparison

### 0.5 Limitations (When to Transition to CV)

**Laser pointer testing does NOT validate**:
- Motion tracking algorithms (no velocity detection needed)
- Pattern differencing (laser adds light, doesn't occlude)
- Object characterization (laser is self-illuminated)
- Impact moment detection (no discrete "hit" event)
- Transient impact handling (continuous motion only)

**Transition to CV when**:
- Geometric calibration proven accurate with laser
- Temporal query system fully tested
- Game mechanics validated and polished
- Ready to handle complexity of thrown objects

### 0.6 Integration with Demo

Update `ams_demo.py` to support laser backend:

```python
# ams_demo.py (additions)

parser = argparse.ArgumentParser()
parser.add_argument('--backend', choices=['mouse', 'laser', 'cv'], default='mouse',
                   help='Detection backend to use')
args = parser.parse_args()

if args.backend == 'mouse':
    # Existing mouse backend
    mouse_input = MouseInputSource()
    detection_backend = InputSourceAdapter(mouse_input, DISPLAY_WIDTH, DISPLAY_HEIGHT)

elif args.backend == 'laser':
    # Laser pointer backend
    from ams.camera import OpenCVCamera
    from ams.laser_detection_backend import LaserDetectionBackend
    from calibration.calibration_manager import CalibrationManager

    # Load geometric calibration
    calib_manager = CalibrationManager(config)
    if not calib_manager.is_calibrated():
        print("ERROR: Run geometric calibration first (calibrate.py)")
        sys.exit(1)

    camera = OpenCVCamera(camera_id=0)
    detection_backend = LaserDetectionBackend(
        camera=camera,
        calibration_manager=calib_manager,
        display_width=DISPLAY_WIDTH,
        display_height=DISPLAY_HEIGHT
    )

elif args.backend == 'cv':
    # Full CV backend (implemented in later phases)
    from ams.cv_detection_backend import CVDetectionBackend
    # ... implementation details
```

---

## Phase 2: CV Detection Backend

### 2.1 Camera Interface

```python
# ams/camera.py

from abc import ABC, abstractmethod
import numpy as np
import cv2
from typing import Optional

class CameraInterface(ABC):
    """Abstract camera interface for CV detection."""

    @abstractmethod
    def capture_frame(self) -> np.ndarray:
        """
        Capture a single frame from camera.

        Returns:
            BGR image (numpy array)
        """
        pass

    @abstractmethod
    def get_resolution(self) -> Tuple[int, int]:
        """Returns (width, height) of camera."""
        pass

    @abstractmethod
    def release(self):
        """Release camera resources."""
        pass

class OpenCVCamera(CameraInterface):
    """OpenCV-based camera implementation."""

    def __init__(self, camera_id: int = 0, resolution: Optional[Tuple[int, int]] = None):
        """
        Initialize camera.

        Args:
            camera_id: OpenCV camera index (0 = default)
            resolution: Optional (width, height) to set
        """
        self.camera = cv2.VideoCapture(camera_id)

        if not self.camera.isOpened():
            raise RuntimeError(f"Could not open camera {camera_id}")

        if resolution:
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        # Set high FPS for motion tracking
        self.camera.set(cv2.CAP_PROP_FPS, 60)

    def capture_frame(self) -> np.ndarray:
        """Capture frame from camera."""
        ret, frame = self.camera.read()
        if not ret:
            raise RuntimeError("Failed to capture frame")
        return frame

    def get_resolution(self) -> Tuple[int, int]:
        """Get actual camera resolution."""
        width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (width, height)

    def release(self):
        """Release camera."""
        self.camera.release()
```

### 2.2 Motion Detector (Phase 1)

```python
# ams/motion_detector.py

from typing import Optional, List, Tuple
from collections import deque
import numpy as np
import cv2
from models import Point2D
import time

class MotionDetector:
    """
    Lightweight motion detection for tracking projectile.

    Uses background subtraction to detect moving objects and track velocity.
    Runs every frame (~2ms) to detect impact moment (minimum velocity).
    """

    def __init__(self, history_size: int = 10):
        """
        Initialize motion detector.

        Args:
            history_size: Number of frames to track for velocity calculation
        """
        self.background_model: Optional[np.ndarray] = None
        self.position_history: deque[Tuple[Point2D, float]] = deque(maxlen=history_size)
        self.velocity_history: deque[float] = deque(maxlen=history_size)

        # Detection parameters
        self.bg_learning_rate = 0.01
        self.motion_threshold = 25  # Pixel intensity difference
        self.min_blob_area = 100    # Minimum object size in pixels

    def process_frame(
        self,
        frame: np.ndarray,
        timestamp: float
    ) -> Optional[Tuple[Point2D, bool]]:
        """
        Process frame for motion detection.

        Args:
            frame: BGR camera frame
            timestamp: Frame timestamp (monotonic)

        Returns:
            Tuple of (position, is_impact) or None if no motion detected
            - position: Blob centroid in camera coordinates
            - is_impact: True if this frame is impact moment (min velocity)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Initialize background model
        if self.background_model is None:
            self.background_model = gray.astype(float)
            return None

        # Background subtraction
        diff = cv2.absdiff(gray, self.background_model.astype(np.uint8))
        _, thresh = cv2.threshold(diff, self.motion_threshold, 255, cv2.THRESH_BINARY)

        # Morphological operations to clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Find contours (blobs)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            # No motion detected - update background and reset tracking
            cv2.accumulateWeighted(gray, self.background_model, self.bg_learning_rate)
            self._reset_tracking()
            return None

        # Find largest blob (assume it's our projectile)
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)

        if area < self.min_blob_area:
            # Too small, likely noise
            cv2.accumulateWeighted(gray, self.background_model, self.bg_learning_rate)
            self._reset_tracking()
            return None

        # Get centroid
        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None

        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        position = Point2D(x=cx, y=cy)

        # Track position and velocity
        self.position_history.append((position, timestamp))

        if len(self.position_history) < 2:
            return (position, False)  # Not enough history for velocity

        # Calculate velocity (pixels/second)
        velocity = self._calculate_velocity()
        self.velocity_history.append(velocity)

        # Check if this is impact moment (local minimum velocity)
        is_impact = self._is_impact_moment()

        return (position, is_impact)

    def _calculate_velocity(self) -> float:
        """Calculate current velocity from position history."""
        if len(self.position_history) < 2:
            return 0.0

        pos1, t1 = self.position_history[-2]
        pos2, t2 = self.position_history[-1]

        dt = t2 - t1
        if dt == 0:
            return 0.0

        dx = pos2.x - pos1.x
        dy = pos2.y - pos1.y
        distance = np.sqrt(dx*dx + dy*dy)

        return distance / dt

    def _is_impact_moment(self) -> bool:
        """
        Detect if current frame is impact moment.

        Impact = local minimum velocity (object closest to surface).
        """
        if len(self.velocity_history) < 5:
            return False

        # Check if last velocity is local minimum
        recent_velocities = list(self.velocity_history)[-5:]
        current_velocity = recent_velocities[-1]

        # Must be slower than previous frames and starting to speed up again
        is_local_min = (
            current_velocity < recent_velocities[-2] and  # Slower than previous
            current_velocity < np.mean(recent_velocities[:-1])  # Slower than average
        )

        # Also check absolute threshold (object must be moving somewhat)
        has_moved = current_velocity < 100 and len(self.position_history) > 3

        return is_local_min and has_moved

    def _reset_tracking(self):
        """Reset position and velocity history."""
        self.position_history.clear()
        self.velocity_history.clear()
```

### 2.3 Pattern Differencing (Phase 2)

```python
# ams/pattern_detector.py

from typing import Optional, Tuple
import numpy as np
import cv2
from models import Point2D, HomographyMatrix

class PatternDifferencingDetector:
    """
    Precise impact location via projected pattern differencing.

    Only runs at impact moment (detected by MotionDetector).
    Uses inverse homography to predict expected camera view.
    """

    def __init__(
        self,
        homography_cam_to_proj: HomographyMatrix,
        camera_resolution: Tuple[int, int],
        projector_resolution: Tuple[int, int]
    ):
        """
        Initialize pattern differencing detector.

        Args:
            homography_cam_to_proj: Camera to projector transformation
            camera_resolution: (width, height) of camera
            projector_resolution: (width, height) of projector
        """
        self.H_cam_to_proj = homography_cam_to_proj.to_numpy()
        self.H_proj_to_cam = np.linalg.inv(self.H_cam_to_proj)
        self.camera_resolution = camera_resolution
        self.projector_resolution = projector_resolution

    def extract_precise_impact(
        self,
        camera_frame: np.ndarray,
        projector_frame: np.ndarray
    ) -> Optional[Point2D]:
        """
        Extract precise impact location using pattern differencing.

        Args:
            camera_frame: Actual camera frame at impact moment
            projector_frame: What is being projected (known)

        Returns:
            Impact position in camera coordinates, or None if detection fails
        """
        # Step 1: Predict what camera SHOULD see (no object)
        expected_camera = self._warp_projector_to_camera(projector_frame)

        # Step 2: Compute difference
        diff = cv2.absdiff(camera_frame, expected_camera)

        # Convert to grayscale and threshold
        if len(diff.shape) == 3:
            diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        else:
            diff_gray = diff

        _, thresh = cv2.threshold(diff_gray, 30, 255, cv2.THRESH_BINARY)

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Find contours (occlusion regions)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Find largest occlusion (should be our projectile)
        largest = max(contours, key=cv2.contourArea)

        # Get centroid
        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None

        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]

        return Point2D(x=cx, y=cy)

    def _warp_projector_to_camera(self, projector_frame: np.ndarray) -> np.ndarray:
        """
        Warp projector image to predict camera view.

        Uses inverse homography: Projector → Camera
        """
        h, w = self.camera_resolution[1], self.camera_resolution[0]

        warped = cv2.warpPerspective(
            projector_frame,
            self.H_proj_to_cam,
            (w, h),
            flags=cv2.INTER_LINEAR
        )

        return warped
```

### 2.4 CV Detection Backend

```python
# ams/cv_detection_backend.py

from typing import List, Optional
import time
import numpy as np
from ams.detection_backend import DetectionBackend
from ams.events import PlaneHitEvent, CalibrationResult
from ams.camera import CameraInterface
from ams.motion_detector import MotionDetector
from ams.pattern_detector import PatternDifferencingDetector
from calibration.calibration_manager import CalibrationManager

class CVDetectionBackend(DetectionBackend):
    """
    Computer Vision detection backend for transient projectile impacts.

    Implements two-phase detection:
    - Phase 1: Lightweight motion tracking (every frame)
    - Phase 2: Pattern differencing (only at impact)

    Reports ~150ms detection latency for temporal queries.
    """

    def __init__(
        self,
        camera: CameraInterface,
        calibration_manager: CalibrationManager,
        display_width: int,
        display_height: int
    ):
        """
        Initialize CV detection backend.

        Args:
            camera: Camera interface for frame capture
            calibration_manager: Geometric calibration manager
            display_width: Display width in pixels
            display_height: Display height in pixels
        """
        super().__init__(display_width, display_height)

        self.camera = camera
        self.calibration_manager = calibration_manager
        self.detection_latency_ms = 150.0  # Typical CV detection latency

        # Get calibration data
        calib_data = calibration_manager.get_calibration_data()

        # Initialize detectors
        self.motion_detector = MotionDetector(history_size=10)
        self.pattern_detector = PatternDifferencingDetector(
            homography_cam_to_proj=calib_data.homography_camera_to_projector,
            camera_resolution=(camera.get_resolution()[0], camera.get_resolution()[1]),
            projector_resolution=(calib_data.projector_resolution.width,
                                 calib_data.projector_resolution.height)
        )

        # Event queue
        self._event_queue: List[PlaneHitEvent] = []

        # Current projector frame (needed for pattern differencing)
        self._current_projector_frame: Optional[np.ndarray] = None

    def update(self, dt: float):
        """
        Update detection (called every frame).

        Runs Phase 1 motion tracking. If impact detected, runs Phase 2.
        """
        # Capture camera frame
        camera_frame = self.camera.capture_frame()
        timestamp = time.monotonic()

        # Phase 1: Lightweight motion detection
        result = self.motion_detector.process_frame(camera_frame, timestamp)

        if result is None:
            return  # No motion detected

        position, is_impact = result

        if not is_impact:
            return  # Still tracking, not impact yet

        # Phase 2: Precise impact location (expensive, only at impact)
        if self._current_projector_frame is not None:
            precise_position = self.pattern_detector.extract_precise_impact(
                camera_frame,
                self._current_projector_frame
            )

            if precise_position:
                position = precise_position  # Use precise location

        # Transform to game coordinates
        game_position = self.calibration_manager.camera_to_game(position)

        # Create event
        event = PlaneHitEvent(
            x=game_position.x,
            y=game_position.y,
            timestamp=timestamp,
            confidence=0.95,  # High confidence for CV detection
            detection_method="cv_pattern_differencing",
            latency_ms=self.detection_latency_ms,
            metadata={
                'camera_position': {'x': position.x, 'y': position.y},
                'detection_phase': 'pattern_differencing' if self._current_projector_frame else 'motion_only'
            }
        )

        self._event_queue.append(event)

    def poll_events(self) -> List[PlaneHitEvent]:
        """Get all pending detection events."""
        events = self._event_queue.copy()
        self._event_queue.clear()
        return events

    def set_projector_frame(self, frame: np.ndarray):
        """
        Update current projector frame for pattern differencing.

        Call this whenever the projected image changes (from game rendering).
        """
        self._current_projector_frame = frame.copy()

    def calibrate(self) -> CalibrationResult:
        """
        Run CV calibration (color characterization).

        Called by AMS between rounds.
        """
        # This is handled by CalibrationSession in ams/calibration.py
        # which already has framework for color calibration
        # For now, return success (geometric calibration already done)
        return CalibrationResult(
            success=True,
            method="cv_detection",
            available_colors=None,  # Will be populated by CalibrationSession
            display_latency_ms=self.detection_latency_ms
        )
```

---

## Phase 3: Interstitial Calibration UX

### 3.1 Visual Treatment

The calibration happens between rounds and should feel like part of the game experience, not a technical interruption.

**Calibration as Interstitial**:
```
┌──────────────────────────────────────┐
│         ROUND 2 COMPLETE!            │
│                                      │
│         Score: 850 points            │
│         Accuracy: 78%                │
│                                      │
│    [Color cycling animation]         │
│    "Preparing next challenge..."     │
│                                      │
│    Progress: [████████░░] 80%        │
│                                      │
│    ⏱ Next round in 2 seconds...      │
└──────────────────────────────────────┘
```

### 3.2 Calibration Workflow

```python
# ams/interstitial.py

from typing import Callable, Optional
import pygame
import time
from ams.session import AMSSession

class InterstitialCalibration:
    """
    Manage between-round calibration as game interstitial.

    Makes calibration feel like dramatic lighting/loading effect.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        ams_session: AMSSession
    ):
        """
        Initialize interstitial manager.

        Args:
            screen: Pygame screen for rendering
            ams_session: AMS session to calibrate
        """
        self.screen = screen
        self.ams = ams_session
        self.width = screen.get_width()
        self.height = screen.get_height()

    def run_between_rounds(
        self,
        score: int,
        round_number: int,
        accuracy: float
    ):
        """
        Run calibration between rounds with visual feedback.

        Args:
            score: Player's score from completed round
            round_number: Round that just completed
            accuracy: Player's accuracy percentage
        """
        # Phase 1: Show round summary
        self._show_round_summary(score, round_number, accuracy)
        time.sleep(1.5)

        # Phase 2: Calibration with visual feedback
        def progress_callback(phase: str, progress: float, message: str):
            self._render_calibration_progress(phase, progress, message)

        # Run calibration (3-6 seconds)
        calibration_result = self.ams.calibrate_between_rounds(
            progress_callback=progress_callback
        )

        # Phase 3: Countdown to next round
        self._countdown_to_next_round(3)

    def _show_round_summary(
        self,
        score: int,
        round_number: int,
        accuracy: float
    ):
        """Display round completion summary."""
        self.screen.fill((20, 20, 40))  # Dark blue background

        font_large = pygame.font.Font(None, 72)
        font_medium = pygame.font.Font(None, 48)

        # Title
        title = font_large.render(f"ROUND {round_number} COMPLETE!", True, (255, 255, 100))
        title_rect = title.get_rect(center=(self.width // 2, self.height // 3))
        self.screen.blit(title, title_rect)

        # Score
        score_text = font_medium.render(f"Score: {score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(score_text, score_rect)

        # Accuracy
        acc_text = font_medium.render(f"Accuracy: {accuracy:.1f}%", True, (255, 255, 255))
        acc_rect = acc_text.get_rect(center=(self.width // 2, self.height // 2 + 60))
        self.screen.blit(acc_text, acc_rect)

        pygame.display.flip()

    def _render_calibration_progress(
        self,
        phase: str,
        progress: float,
        message: str
    ):
        """
        Render calibration progress as dramatic lighting effect.

        Color cycling appears as game atmosphere, not technical calibration.
        """
        # Map phase to color for dramatic effect
        phase_colors = {
            "init": (50, 50, 100),
            "latency": (100, 50, 150),
            "background": (150, 100, 50),  # Warm colors during background phase
            "object": (50, 150, 100),      # Cool colors during object phase
            "palette": (100, 100, 150),
            "complete": (50, 200, 50)      # Green = success
        }

        bg_color = phase_colors.get(phase, (50, 50, 50))

        # Fade between colors smoothly
        self.screen.fill(bg_color)

        # Progress bar
        bar_width = int(self.width * 0.6)
        bar_height = 40
        bar_x = (self.width - bar_width) // 2
        bar_y = self.height // 2

        # Background
        pygame.draw.rect(self.screen, (60, 60, 60),
                        (bar_x, bar_y, bar_width, bar_height), border_radius=10)

        # Progress
        fill_width = int(bar_width * progress)
        pygame.draw.rect(self.screen, (100, 200, 100),
                        (bar_x, bar_y, fill_width, bar_height), border_radius=10)

        # Text
        font = pygame.font.Font(None, 36)
        text = font.render(message, True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.width // 2, bar_y + 80))
        self.screen.blit(text, text_rect)

        pygame.display.flip()

    def _countdown_to_next_round(self, seconds: int):
        """Countdown timer before next round starts."""
        font = pygame.font.Font(None, 96)

        for i in range(seconds, 0, -1):
            self.screen.fill((20, 20, 40))

            text = font.render(f"Next round in {i}...", True, (255, 255, 100))
            text_rect = text.get_rect(center=(self.width // 2, self.height // 2))
            self.screen.blit(text, text_rect)

            pygame.display.flip()
            time.sleep(1)
```

---

## Phase 4: Integration and Testing

### 4.1 Update Demo to Support CV Backend

```python
# ams_demo.py (modifications)

# Add command-line flag to choose backend
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--backend', choices=['mouse', 'cv'], default='mouse',
                   help='Detection backend to use')
args = parser.parse_args()

if args.backend == 'mouse':
    # Existing mouse backend
    mouse_input = MouseInputSource()
    detection_backend = InputSourceAdapter(mouse_input, DISPLAY_WIDTH, DISPLAY_HEIGHT)
else:
    # CV backend
    from ams.camera import OpenCVCamera
    from ams.cv_detection_backend import CVDetectionBackend
    from calibration.calibration_manager import CalibrationManager

    camera = OpenCVCamera(camera_id=0)
    calib_manager = CalibrationManager(...)  # Load existing geometric calibration

    detection_backend = CVDetectionBackend(
        camera=camera,
        calibration_manager=calib_manager,
        display_width=DISPLAY_WIDTH,
        display_height=DISPLAY_HEIGHT
    )
```

### 4.2 Testing Plan

**Unit Tests**:
```python
# tests/test_color_analysis.py
def test_color_statistics_creation():
    """Test ColorStatistics creation and validation."""

def test_contrast_computation():
    """Test contrast between background and object."""

def test_palette_filtering():
    """Test that low-quality colors are filtered out."""

# tests/test_motion_detector.py
def test_motion_detection():
    """Test lightweight motion detector with synthetic data."""

def test_velocity_calculation():
    """Test velocity from position history."""

def test_impact_detection():
    """Test impact moment detection (min velocity)."""

# tests/test_pattern_detector.py
def test_homography_warping():
    """Test projector→camera warping."""

def test_pattern_differencing():
    """Test occlusion detection."""
```

**Integration Tests**:
```python
# tests/test_cv_backend.py
def test_cv_backend_interface():
    """Test CVDetectionBackend implements DetectionBackend correctly."""

def test_latency_reporting():
    """Test that events include correct latency_ms."""

def test_temporal_query_with_cv():
    """Test temporal queries work with CV latency."""
```

**Hardware Tests**:
1. Geometric calibration (already tested ✅ - 0.25px RMS)
2. Color characterization with real projectile
3. Motion detection with thrown object
4. Full integration test: throw → detect → temporal query → hit result

---

## Implementation Order

### Week 1: Color Characterization
1. Implement `color_analysis.py` (models + functions)
2. Update `ams/calibration.py` to perform real color characterization
3. Test color characterization with camera and projector
4. Validate palette computation (which colors are usable)

### Week 2: Motion Detection
1. Implement `camera.py` (OpenCVCamera)
2. Implement `motion_detector.py` (Phase 1 detection)
3. Test motion tracking with thrown object
4. Validate impact moment detection

### Week 3: Pattern Differencing
1. Implement `pattern_detector.py` (Phase 2 detection)
2. Integrate with motion detector
3. Test precise impact location extraction
4. Benchmark performance (should be ~50ms per impact)

### Week 4: CV Backend Integration
1. Implement `cv_detection_backend.py`
2. Integrate with existing AMS architecture
3. Update demo to support CV backend
4. Test complete data flow with real projectile

### Week 5: Interstitial UX
1. Implement `interstitial.py` (visual calibration feedback)
2. Integrate into demo game
3. Polish visual effects
4. User testing with non-technical users

### Week 6: Polish and Documentation
1. Add comprehensive error handling
2. Write integration guide
3. Create troubleshooting documentation
4. Record demo video

---

## Success Criteria

✅ **Color characterization produces usable palette**:
- At least 4-6 colors with quality > 0.7
- Background/object contrast clearly separates projectile
- Calibration completes in < 10 seconds

✅ **Motion detection tracks projectile accurately**:
- Detects object within 50ms of entering frame
- Velocity calculation tracks flight path
- Impact moment detected reliably (< 10% false positives)

✅ **Pattern differencing extracts precise location**:
- Impact location within 2cm of actual position
- Works under varying lighting conditions
- Completes in < 100ms

✅ **CV backend integrates seamlessly**:
- Drop-in replacement for mouse backend
- Temporal queries work correctly with 150ms latency
- Game hits/misses match visual gameplay

✅ **Interstitial calibration feels polished**:
- Users don't perceive it as "technical" calibration
- Color cycling adds to game atmosphere
- Completes within round transition time budget

---

## Performance Targets

| Component | Target | Rationale |
|-----------|--------|-----------|
| Motion detection (Phase 1) | < 2ms/frame | Must run at 60fps without lag |
| Pattern differencing (Phase 2) | < 100ms | Only once per impact, acceptable |
| Color characterization | < 10 seconds | Between rounds, invisible to user |
| Display latency measurement | < 1 second | Quick validation step |
| Total between-round calibration | < 10 seconds | Fits in round transition |

---

## Risk Mitigation

**Risk**: Color characterization produces no usable colors (poor lighting)
- **Mitigation**: Provide clear feedback with suggestions ("Increase ambient lighting", "Adjust projector brightness")
- **Fallback**: Allow manual color selection, warn about reduced accuracy

**Risk**: Motion detection has high false positive rate (shadows, lighting changes)
- **Mitigation**: Adaptive background model, stricter velocity thresholds
- **Fallback**: Require user confirmation for ambiguous detections

**Risk**: Pattern differencing performance too slow
- **Mitigation**: Optimize warping with GPU acceleration (OpenCV CUDA)
- **Fallback**: Skip Phase 2, use only Phase 1 motion detection (lower accuracy but functional)

**Risk**: Camera/projector sync issues cause temporal misalignment
- **Mitigation**: Display latency measurement validates timing
- **Fallback**: Manual latency adjustment in config

---

## Future Enhancements

**Post-MVP improvements**:
1. **GPU Acceleration**: Use OpenCV CUDA for warping (10x speedup)
2. **Multi-camera support**: Stereo vision for 3D impact location
3. **Adaptive thresholds**: Machine learning for optimal detection parameters
4. **Replay system**: Record and analyze missed detections
5. **Remote camera**: Network camera support for flexible setup

---

## References

- **AMS.md**: Core architecture and calibration philosophy
- **CALIBRATION_SYSTEM_PLAN.md**: Geometric calibration details and detection strategies
- **SESSION_SUMMARY_2025-10-25.md**: Historical context and decision rationale
- **AMS_README.md**: Current implementation status

---

**Next Action**: Review this plan with stakeholder, prioritize features, begin Week 1 implementation.
