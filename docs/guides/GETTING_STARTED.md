# Getting Started - Calibration System Prototype

This guide will help you set up and run the calibration system.

## Prerequisites

### Hardware
- Projector (any resolution, tested with 1920x1080)
- Webcam or camera with USB connection
- Flat projection surface (plywood, foam board, wall, etc.)
- Computer with 2 video outputs (one for projector, one for monitor)

### Software
- Python 3.8 or higher
- pip package manager

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- opencv-contrib-python (computer vision + ArUco markers)
- numpy (numerical operations)
- pygame (projection display)
- pydantic (data validation)

### 2. Verify Installation

```bash
python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"
python -c "import pygame; print(f'Pygame version: {pygame.__version__}')"
```

## Running Calibration

### Quick Start

1. **Set up hardware**:
   - Connect projector as second display
   - Point projector at target surface
   - Position camera to see the projection surface
   - Ensure camera and projector can both see the same area

2. **Run calibration script**:
   ```bash
   python calibrate.py --projector-width 1920 --projector-height 1080
   ```

3. **Follow on-screen instructions**:
   - Calibration pattern will display on projector (fullscreen)
   - Camera preview shows detected markers
   - Adjust camera/projector until you see most markers (green count)
   - Press SPACE to capture
   - Calibration will compute automatically

4. **Check results**:
   - Look for "CALIBRATION SUCCESSFUL!" message
   - Check quality metrics (RMS error should be < 3 pixels)
   - Calibration saved to `./calibration_data/calibration_YYYYMMDD_HHMMSS.json`

### Command Line Options

```bash
python calibrate.py --help
```

Options:
- `--projector-width WIDTH`: Projector resolution width (default: 1920)
- `--projector-height HEIGHT`: Projector resolution height (default: 1080)
- `--camera-id ID`: Camera device ID (default: 0)
- `--projector-display N`: Which display for projector (0=primary, 1=secondary, default: 1)
- `--grid-size 4x4`: Calibration grid size (default: 4x4)

### Examples

**HD projector on second display:**
```bash
python calibrate.py --projector-width 1920 --projector-height 1080 --projector-display 1
```

**4K projector:**
```bash
python calibrate.py --projector-width 3840 --projector-height 2160
```

**External USB camera (usually device 1):**
```bash
python calibrate.py --camera-id 1
```

**Larger calibration grid for better accuracy:**
```bash
python calibrate.py --grid-size 6x6
```

## Testing the Calibration

### 1. Generate a Test Pattern

```bash
python -m calibration.pattern_generator
```

This creates `calibration_pattern.png` you can inspect.

### 2. Test Marker Detection

```bash
python -m calibration.pattern_detector
```

This opens a live camera feed showing detected markers. Use this to:
- Check if camera can see projected pattern
- Verify marker detection is working
- Test different lighting conditions

### 3. Test Homography Computation

```bash
python -m calibration.homography
```

Runs synthetic tests to verify homography math is correct.

## Troubleshooting

### Problem: No camera found

**Error**: `Failed to open camera 0`

**Solution**:
- Check camera is connected
- Try different camera IDs: `--camera-id 1` or `--camera-id 2`
- On macOS, grant camera permissions in System Preferences

### Problem: Pattern not visible on projector

**Error**: Pattern appears on wrong display

**Solution**:
- Try different display IDs: `--projector-display 0` or `--projector-display 1`
- Manually move the pygame window to projector display
- Check display settings in OS (display arrangement)

### Problem: Few markers detected

**Symptoms**: Camera preview shows "Detected: 5/16 markers" (red text)

**Solution**:
- Adjust camera angle to see entire projection
- Improve lighting on target surface
- Reduce ambient light (projector pattern must be visible)
- Move camera closer or adjust projector focus
- Clean camera lens

### Problem: High calibration error

**Symptoms**: "RMS error: 8.5 pixels" (>3 pixels)

**Causes**:
- Camera/projector moved during calibration
- Poor focus on camera or projector
- Markers at extreme angles
- Non-planar target surface

**Solution**:
- Ensure camera and projector are stable
- Adjust focus on both devices
- Use flatter target surface
- Try larger markers: `--grid-size 3x3`

### Problem: Calibration fails completely

**Error**: `Insufficient markers detected` or `Failed to compute homography`

**Solution**:
- Check camera can see projector output
- Reduce grid size: `--grid-size 3x3`
- Increase room lighting slightly (but keep pattern visible)
- Verify ArUco markers are being generated (check saved pattern image)

## Understanding the Output

After successful calibration, you'll see:

```
CALIBRATION SUCCESSFUL!
Quality Metrics:
  RMS Error: 1.8 pixels
  Max Error: 4.2 pixels
  Inlier Ratio: 90.0%
  Acceptable: True
```

**What this means**:
- **RMS Error < 3 pixels**: Good calibration (impacts will be accurate within ~5cm on surface)
- **Inlier Ratio > 80%**: Most markers were used (high confidence)
- **Acceptable = True**: System considers this good enough for use

## Next Steps

Once calibrated, you can:

1. **Use calibration in your code**:
   ```python
   from models import CalibrationConfig
   from calibration.calibration_manager import CalibrationManager

   config = CalibrationConfig()
   manager = CalibrationManager(config)
   manager.load_calibration("./calibration_data/calibration_20251025_143000.json")

   # Transform camera detection to game coordinates
   game_pos = manager.camera_to_game(camera_point)
   ```

2. **Build impact detection** (next phase)
3. **Create game modes** (after detection works)

## File Structure

After calibration, you'll have:

```
ArcheryGame/
├── calibration_data/
│   ├── calibration_20251025_143000.json  # Calibration data
│   ├── calibration_frame_20251025_143000.png  # Reference image
│   └── ...                                 # Up to 5 most recent
├── calibration/
│   ├── pattern_generator.py
│   ├── pattern_detector.py
│   ├── homography.py
│   └── calibration_manager.py
├── models.py                               # Pydantic data models
├── calibrate.py                            # Main calibration script
└── requirements.txt
```

## Tips for Best Results

1. **Lighting**: Moderate room lighting works best. Too dark = camera can't see; too bright = pattern washes out
2. **Distance**: Camera should see entire projection area but be close enough for good resolution
3. **Stability**: Mount camera and projector if possible. Hand-holding works but is less accurate
4. **Surface**: Flatter is better. Fabric screens work well. Avoid glossy surfaces (reflection)
5. **Timing**: Let projector warm up for a few minutes (brightness/color can shift)
6. **Focus**: Both camera and projector should be in focus on the target surface

## Known Limitations

- Calibration assumes planar (flat) target surface
- Works best with camera viewing target at < 45° angle
- Requires stable camera/projector positions (recalibrate if moved)
- ArUco marker detection requires good contrast
- Pattern must be fully visible in camera view

## Getting Help

If you encounter issues:

1. Check this troubleshooting guide
2. Review `CALIBRATION_SYSTEM_PLAN.md` for technical details
3. Open an issue with:
   - Error message
   - Hardware setup description
   - Sample image from camera showing what it sees
