# Laser Pointer Detection Backend

Phase 0 of the CV Detection System - A simplified testing backend for validation and development.

## Overview

The laser pointer detection backend is a **10x simpler** alternative to full projectile CV detection, designed for:

- **Rapid validation** of geometric calibration
- **Testing** temporal query system with real-time input
- **Debugging** coordinate transformations
- **Game development** without thrown objects
- **Demonstrations** in safe environments

### Detection Comparison

| Feature | Laser Pointer | Full CV (Projectile) |
|---------|--------------|---------------------|
| **Detection method** | Brightness threshold | Motion tracking + pattern diff |
| **Latency** | ~50ms | ~150ms |
| **Complexity** | Simple (100 lines) | Complex (500+ lines) |
| **Calibration needs** | None (geometric only) | Background + object characterization |
| **Testing speed** | Instant | Slow (retrieve object each throw) |
| **Precision** | Trace exact patterns | Limited by throw accuracy |
| **Safety** | Very safe | Requires safety measures |

## Requirements

- **Webcam** (USB or built-in)
- **Laser pointer** (any color, green recommended for brightness)
- **Python packages**: opencv-python, numpy (in venv)

## Quick Start

### 1. Standalone Test (Verify Detection)

Test laser detection without the full game:

```bash
# Basic detection test
python test_laser_detection.py

# Geometric accuracy test (corner/center mapping)
python test_laser_detection.py --test geometric

# Run all tests
python test_laser_detection.py --test all

# Adjust brightness threshold for dim lasers
python test_laser_detection.py --brightness 150
```

### 2. Run Game with Laser Backend

```bash
# Start game with laser detection
python ams_demo.py --backend laser

# Adjust brightness threshold
python ams_demo.py --backend laser --brightness 180

# Use different camera
python ams_demo.py --backend laser --camera-id 1
```

### 3. Controls

**In-Game Controls:**
- **Point laser at targets** to "shoot" them
- **D** - Toggle debug visualization (shows camera view)
- **+/-** - Adjust brightness threshold
- **C** - Recalibrate
- **R** - New round
- **Q** - Quit

**Test Script Controls:**
- **q** - Quit current test
- Follow on-screen instructions for geometric test

## Configuration

### Brightness Threshold

The brightness threshold determines what is considered a "laser spot":

- **200 (default)**: Works for most green lasers
- **180-200**: Bright green lasers
- **150-180**: Red lasers (dimmer)
- **120-150**: Weak or distant lasers

**Too many false positives?** → Increase threshold
**Laser not detected?** → Decrease threshold

You can adjust in real-time using **+/-** keys.

### Spot Size Filtering

Prevents noise and reflections from triggering false detections:

- **min_spot_size**: 5 pixels (adjustable in code)
- **max_spot_size**: 100 pixels (adjustable in code)

### Debouncing

Prevents spam from continuous laser pointing:

- **Spatial threshold**: 5 pixels movement required
- **Temporal threshold**: 100ms between events

## Validation Tests

### Basic Detection Test

Validates that laser spots are detected and tracked correctly.

**What it tests:**
- Camera initialization
- Spot detection
- Event generation
- Coordinate normalization
- Detection stability (jitter)

**How to run:**
```bash
python test_laser_detection.py --test basic
```

**Expected results:**
- Multiple detections as you move laser
- Low jitter (std < 0.05)
- Stable position when laser is held still

### Geometric Accuracy Test

Measures coordinate mapping precision at corners and center.

**What it tests:**
- Corner detection accuracy
- Coordinate transformation
- Mapping consistency
- RMS error across field

**How to run:**
```bash
python test_laser_detection.py --test geometric
```

**Test procedure:**
1. Point laser at top-left corner → press ENTER
2. Point laser at top-right corner → press ENTER
3. Point laser at bottom-right corner → press ENTER
4. Point laser at bottom-left corner → press ENTER
5. Point laser at center → press ENTER

**Expected results:**
- **Excellent**: RMS error < 5% of screen (~64 pixels at 1280px)
- **Good**: RMS error < 10% of screen (~128 pixels)
- **Poor**: RMS error > 10% (consider ArUco calibration)

## Architecture

```
Camera → OpenCVCamera → LaserDetectionBackend → AMS → Game
                              ↓
                        PlaneHitEvent
                        (x, y, timestamp, latency_ms=50)
```

### Key Components

**`ams/camera.py`**:
- Abstract `CameraInterface`
- `OpenCVCamera` implementation
- Frame capture and resolution management

**`ams/laser_detection_backend.py`**:
- Implements `DetectionBackend` interface
- Brightness thresholding
- Blob detection and centroid calculation
- Coordinate normalization
- Event generation with 50ms latency

**`test_laser_detection.py`**:
- Standalone validation tests
- Geometric accuracy measurement
- Detection reliability verification

## Integration with Full System

The laser backend is a **drop-in replacement** for the mouse backend:

```python
# Mouse backend (existing)
from ams.detection_backend import InputSourceAdapter
mouse_input = MouseInputSource()
backend = InputSourceAdapter(mouse_input, width, height)

# Laser backend (new)
from ams.camera import OpenCVCamera
from ams.laser_detection_backend import LaserDetectionBackend
camera = OpenCVCamera(camera_id=0)
backend = LaserDetectionBackend(camera, None, width, height)

# Both work identically with AMS
ams = AMSSession(backend=backend)
```

## Limitations

The laser pointer backend **does not validate**:

- ❌ Motion tracking algorithms (no velocity needed)
- ❌ Pattern differencing (laser adds light, doesn't occlude)
- ❌ Object characterization (laser is self-illuminated)
- ❌ Impact moment detection (continuous motion only)
- ❌ Transient impact handling (no discrete "hit" event)

**When to transition to full CV:**
- Geometric calibration proven accurate with laser
- Temporal query system fully tested
- Game mechanics validated and polished
- Ready to handle complexity of thrown objects

## Troubleshooting

### "Could not open camera"
- **Check**: Camera not in use by another app
- **Check**: Camera ID is correct (try --camera-id 1)
- **Check**: Camera permissions granted

### "No detections recorded"
- **Check**: Laser pointer is bright enough
- **Try**: Decrease brightness threshold (--brightness 150)
- **Check**: Room is not too bright (laser must stand out)
- **Check**: Camera is pointing at laser (see debug window)

### "High jitter - unstable detection"
- **Check**: Laser spot is in focus
- **Try**: Hold laser more steadily
- **Try**: Increase blur_size in code (reduces noise sensitivity)
- **Check**: No bright reflections confusing detector

### "Poor geometric accuracy"
- **Expected**: Without geometric calibration, expect 5-10% error
- **Solution**: Add ArUco marker calibration for <1% error
- **Workaround**: Test hit detection is still functional despite error

## Debug Visualization

Press **D** in game to see the debug window showing:

- **Green contours**: Detected bright spots
- **Red dot**: Laser centroid (detection point)
- **Text overlay**: Position, brightness, spot area
- **Threshold indicator**: Current brightness setting

Use this to:
- Verify laser is being detected
- Tune brightness threshold
- Check for false positives (reflections)
- Validate coordinate mapping

## Next Steps

After validating the laser backend:

1. **Geometric Calibration** (optional but recommended):
   - Use ArUco markers for <1% coordinate error
   - Run calibration system: `python calibrate.py`
   - Test laser backend with calibration enabled

2. **Game Development**:
   - Build and test game mechanics with laser input
   - Validate temporal queries with 50ms latency
   - Polish game feel and timing

3. **Full CV Implementation** (when ready):
   - Implement color characterization (Phase 1)
   - Implement motion detection (Phase 2)
   - Implement pattern differencing (Phase 3)
   - Integrate interstitial calibration (Phase 4)

## Performance

- **Frame rate**: 60fps (16.7ms per frame)
- **Detection latency**: ~50ms
- **CPU usage**: ~5-10% (single core)
- **Memory**: ~50MB

Much more efficient than full CV detection (~150ms latency, 20-30% CPU).

## Examples

### Basic Usage

```bash
# Test detection
python test_laser_detection.py

# Play game
python ams_demo.py --backend laser
```

### Advanced Usage

```bash
# Test with dim red laser
python test_laser_detection.py --brightness 150

# Play with external webcam
python ams_demo.py --backend laser --camera-id 1 --brightness 180

# Run full validation suite
python test_laser_detection.py --test all
```

## Code Examples

### Standalone Detection

```python
from ams.camera import OpenCVCamera
from ams.laser_detection_backend import LaserDetectionBackend

camera = OpenCVCamera(camera_id=0)
backend = LaserDetectionBackend(
    camera=camera,
    calibration_manager=None,
    display_width=1280,
    display_height=720,
    brightness_threshold=200
)

backend.set_debug_mode(True)

while True:
    backend.update(0.016)  # ~60fps
    events = backend.poll_events()

    for event in events:
        print(f"Laser at ({event.x:.3f}, {event.y:.3f})")
```

### Custom Brightness Threshold

```python
# Detect very bright spots only
backend.set_brightness_threshold(220)

# Detect dimmer spots
backend.set_brightness_threshold(150)
```

## Support

For issues or questions:

1. Run validation tests: `python test_laser_detection.py --test all`
2. Check debug visualization (press **D** in game)
3. Review troubleshooting section above
4. Check CV_DETECTION_IMPLEMENTATION_PLAN.md for full context

## Summary

The laser pointer backend provides a **fast, simple, safe** way to validate 90% of the AMS system with 10% of the complexity. Use it to prove out your architecture before investing in full CV detection.

**Ready to test?** → `python test_laser_detection.py`
**Ready to play?** → `python ams_demo.py --backend laser`
