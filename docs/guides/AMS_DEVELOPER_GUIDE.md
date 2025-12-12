# YAMS Developer Guide

A practical guide for developers working on the YAML Arcade Management System (YAMS).

## Getting Started

### Running with Different Backends

```bash
# Development: Mouse input (no hardware needed)
python ams_game.py --game balloonpop --backend mouse

# Testing: Laser pointer detection
python ams_game.py --game balloonpop --backend laser --camera 0

# Production: Object detection (arrows, darts)
python ams_game.py --game balloonpop --backend object --camera 0
```

### Enabling Debug Logging

AMS uses Python's standard `logging` module. Configure it in your entry point:

```python
import logging

# Show all AMS logs
logging.basicConfig(level=logging.DEBUG)

# Or just AMS logs at INFO level
logging.getLogger('ams').setLevel(logging.INFO)

# Or specific module
logging.getLogger('ams.laser').setLevel(logging.DEBUG)
```

**Log levels used in AMS:**

| Level | Use Case |
|-------|----------|
| `DEBUG` | Frame-by-frame detection details, coordinate transforms |
| `INFO` | Session start/stop, calibration results, significant events |
| `WARNING` | Recoverable errors, fallback behavior triggered |
| `ERROR` | Failures that affect functionality |

## Code Conventions

### Logging in AMS Modules

Each module should create its own logger:

```python
# At top of file, after imports
import logging
logger = logging.getLogger('ams.modulename')

# In code
logger.debug(f"Processing frame {frame_num}")
logger.info(f"Calibration complete: {quality}")
logger.warning(f"Using fallback: {reason}")
logger.error(f"Detection failed: {error}")
```

**When to use print() vs logging:**

- `print()`: Interactive user prompts during calibration (user must see these)
- `logger.info()`: Status updates that could be silenced in production
- `logger.debug()`: Verbose debugging info

### Coordinate Systems

All AMS coordinates are **normalized [0, 1]**:

```python
# Converting from pixels to normalized
norm_x = pixel_x / display_width
norm_y = pixel_y / display_height

# Use the helper method
norm_x, norm_y = backend.normalize_coordinates(pixel_x, pixel_y)
```

**Coordinate origin**: (0, 0) = top-left, (1, 1) = bottom-right

### Event Creation

Always include timestamp and detection method:

```python
from ams.events import PlaneHitEvent
import time

event = PlaneHitEvent(
    x=norm_x,
    y=norm_y,
    timestamp=time.time(),
    confidence=0.95,
    detection_method="laser",
    metadata={
        'brightness': 245,
        'camera_position': {'x': pixel_x, 'y': pixel_y},
    }
)
```

## Detection Backend Development

### Backend Interface

All backends must implement:

```python
from ams.detection_backend import DetectionBackend
from ams.events import PlaneHitEvent, CalibrationResult

class MyBackend(DetectionBackend):
    def __init__(self, display_width: int, display_height: int):
        super().__init__(display_width, display_height)
        # Initialize your detection system

    def poll_events(self) -> List[PlaneHitEvent]:
        """Return new detections since last poll."""
        # Called every frame - must be fast
        pass

    def update(self, dt: float):
        """Update internal state."""
        # Called every frame with delta time
        pass

    def calibrate(self) -> CalibrationResult:
        """Run calibration procedure."""
        pass
```

### Calibration Guidelines

**For instant backends (mouse, laser):**

```python
def calibrate(self) -> CalibrationResult:
    return CalibrationResult(
        success=True,
        method="instant",
        notes="No calibration required"
    )
```

**For CV backends (object detection):**

```python
def calibrate(self, display_surface=None, display_resolution=None):
    # 1. Display calibration pattern (if display_surface provided)
    # 2. Detect pattern in camera view
    # 3. Compute homography transform
    # 4. Store for coordinate mapping
    # 5. Return result with quality metrics
    pass
```

### Testing Without Hardware

Use `InputSourceAdapter` to wrap mouse input:

```python
from ams.detection_backend import InputSourceAdapter
from games.common.input.sources.mouse import MouseInputSource

mouse = MouseInputSource()
backend = InputSourceAdapter(mouse, 1920, 1080)

# Backend now produces PlaneHitEvents from mouse clicks
```

## Common Tasks

### Adding a New Detection Method

1. Create `ams/my_detection_backend.py`
2. Inherit from `DetectionBackend`
3. Implement `poll_events()`, `update()`, `calibrate()`
4. Add to `ams_game.py` backend selection
5. Document in `docs/architecture/AMS_ARCHITECTURE.md`

### Debugging Coordinate Transforms

Enable debug mode on laser backend:

```python
backend.set_debug_mode(True)
backend.set_debug_bw_mode(True)  # Show threshold visualization
```

Or check transforms manually:

```python
# Camera coords -> normalized
camera_x, camera_y = 320, 240
norm_x, norm_y = backend.normalize_coordinates(camera_x, camera_y)
logger.debug(f"Camera ({camera_x}, {camera_y}) -> Normalized ({norm_x:.3f}, {norm_y:.3f})")
```

### Handling Detection Latency

For backends with significant latency (object detection), games should use temporal queries:

```python
# In game, when handling PlaneHitEvent
def handle_hit_event(self, event: PlaneHitEvent):
    # DON'T check current state
    # DO query state at event timestamp
    result = self.was_target_hit(event.x, event.y, event.timestamp)
```

See `ams/temporal_state.py` for `TemporalGameState` base class.

## Architecture Reference

```
ams/
├── __init__.py              # Package init, logger setup
├── events.py                # PlaneHitEvent, CalibrationResult, HitResult
├── detection_backend.py     # DetectionBackend ABC, InputSourceAdapter
├── laser_detection_backend.py   # Laser pointer detection
├── object_detection_backend.py  # CV object tracking
├── calibration.py           # CalibrationSession workflow
├── temporal_state.py        # TemporalGameState for latency handling
├── session.py               # AMSSession coordinator
├── game_adapter.py          # AMSInputAdapter for game integration
└── camera.py                # Camera utilities
```

**Key flows:**

1. **Detection**: Backend.poll_events() → PlaneHitEvent → Game
2. **Calibration**: AMSSession.calibrate() → CalibrationSession → Backend.calibrate()
3. **Game integration**: Registry creates AMSInputAdapter wrapping AMSSession

## Troubleshooting

### "No events detected"

1. Check camera is working: `python -m ams.camera`
2. Check brightness threshold (laser): lower it with `-` key
3. Check calibration completed successfully
4. Enable debug logging: `logging.getLogger('ams').setLevel(logging.DEBUG)`

### "Coordinates are wrong"

1. Re-run calibration
2. Check homography quality metrics (should be < 3.0 RMS error)
3. Verify camera can see entire projection area
4. Check coordinate normalization is happening

### "High latency"

1. Check camera FPS (should be 30+)
2. Reduce image processing (lower resolution)
3. For object detection, this is expected (use temporal queries)

## See Also

- [AMS Architecture](../architecture/AMS_ARCHITECTURE.md) - Design decisions and backend comparison
- [AMS README](AMS_README.md) - High-level overview
- [Laser Tuning Guide](LASER_TUNING_GUIDE.md) - Laser backend setup
- [Object Detection Guide](OBJECT_DETECTION_GUIDE.md) - CV backend details
