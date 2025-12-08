# Laser Detection Tuning Guide

Quick reference for tuning laser detection on difficult displays (TVs, projectors).

## Quick Start for TV/Projector Setup

```bash
# Black/white targets + laser backend + fullscreen on TV
python ams_demo.py --backend laser --fullscreen --display 1 --bw-palette --brightness 50
```

## New Features

### 1. Lower Brightness Threshold (Down to 10!)

**Problem**: Laser barely visible on TV, can't detect at threshold 100

**Solution**: Threshold now goes down to 10 (was minimum 100)

```bash
# Start with very low threshold
python ams_demo.py --backend laser --brightness 50
```

**In-game adjustment:**
- Press **+** to increase threshold (reduce sensitivity)
- Press **-** to decrease threshold (increase sensitivity)
- Shows current threshold on screen

### 2. Black/White Palette for Targets

**Problem**: Colored targets hard to see on TV, or colors look washed out

**Solution**: Use `--bw-palette` for maximum contrast

```bash
# White targets on black background
python ams_demo.py --backend laser --bw-palette
```

**What it does:**
- Targets are bright white (255, 255, 255)
- Some targets are light gray (200, 200, 200)
- Maximum contrast on any display
- Works on projectors with poor color reproduction

### 3. B/W Threshold View (Camera Debug)

**Problem**: Hard to know what the camera is detecting

**Solution**: Press **B** to see exactly what's above brightness threshold

**Usage:**
1. Start with debug enabled: `--backend laser` (debug auto-enabled)
2. Press **B** to toggle B/W view
3. See white pixels = detected bright spots
4. Adjust threshold with **+/-** until only laser shows white

**View modes:**
- **Color mode** (default): Camera view with green contours + **TARGET OVERLAY**
- **B/W mode** (press B): Pure black/white showing threshold

### 4. Target Overlay on Debug View

**NEW**: Debug window now shows where game targets are!

**What you see:**
- **Colored circles** on camera view = game target positions
- **Crosshairs** at target centers
- Shows exactly where to aim laser
- Updates in real-time as targets move

**Why this helps:**
- See camera field of view vs. game field
- Understand coordinate mapping
- Aim laser precisely at targets
- Debug calibration issues

## Tuning Process

### Step 1: Start Low

```bash
python ams_demo.py --backend laser --fullscreen --display 1 --bw-palette --brightness 30
```

### Step 2: Enable B/W View

1. Game starts, press **D** to show camera window
2. Press **B** to switch to B/W threshold view
3. Point laser at camera

### Step 3: Adjust Threshold

**In B/W view:**
- **All white**: Threshold too low → Press **+** to increase
- **All black** (laser not visible): Threshold too high → Press **-** to decrease
- **Only laser white**: Perfect! You're done.

### Step 4: Test in Game

1. Press **B** again to return to color view
2. **See target circles overlaid on camera view** (shows where to aim!)
3. Point laser at the target circles you see on screen
4. Should register hits immediately

**If targets appear in wrong position:**
- Camera field of view ≠ game field
- Normal without geometric calibration
- Targets show approximate location
- Still useful for general aiming

## Command-Line Options

### For TV/Projector

| Option | Purpose | Example |
|--------|---------|---------|
| `--fullscreen` | Fill entire display | `--fullscreen` |
| `--display 1` | Use secondary display (TV) | `--display 1` |
| `--bw-palette` | White targets (max contrast) | `--bw-palette` |
| `--brightness 50` | Low threshold for dim lasers | `--brightness 50` |

**Recommended combo:**
```bash
python ams_demo.py --backend laser --fullscreen --display 1 --bw-palette --brightness 50
```

## Keyboard Controls

### During Game

| Key | Action | When to Use |
|-----|--------|-------------|
| **D** | Toggle camera debug window | Show/hide camera view |
| **B** | Toggle B/W threshold view | Tune brightness threshold |
| **+** | Increase brightness threshold | Too many false positives |
| **-** | Decrease brightness threshold | Laser not detected |
| **F** | Toggle fullscreen | Switch display mode |
| **ESC** | Quit | Exit game |

## Troubleshooting

### Laser Not Detected at All

**Symptoms:**
- B/W view is all black
- No white spots even when pointing laser

**Solutions:**
1. Lower threshold: Press **-** repeatedly (or start with `--brightness 20`)
2. Check laser is on and bright enough
3. Try different laser color (green is brightest)
4. Reduce ambient lighting (close curtains)

### Everything Detected (False Positives)

**Symptoms:**
- B/W view is all white
- Random hits without pointing laser
- TV screen or lights showing white

**Solutions:**
1. Increase threshold: Press **+** repeatedly
2. Reduce room lighting
3. Angle camera away from bright sources
4. Use darker background (black screen helps)

### Laser Detected But Hits Don't Register

**Symptoms:**
- Camera sees laser (green contour or white in B/W view)
- Debug shows "Laser detected" messages
- But game targets don't respond

**Possible causes:**
1. **Threshold too low**: Other bright spots confusing detection
   - **Fix**: Press **+** to increase threshold
2. **Coordinate mapping wrong**: Camera not aligned with game
   - **Fix**: Need geometric calibration (ArUco markers)
3. **Target palette wrong**: Using colors on black background
   - **Fix**: Add `--bw-palette` flag

### Laser Jittery/Unstable

**Symptoms:**
- Detection position jumps around
- Multiple spots detected
- Inconsistent hits

**Solutions:**
1. Hold laser more steadily
2. Increase threshold to filter noise
3. Check for reflections (shiny surfaces)
4. Increase blur (edit code: `self.blur_size = 7`)

## Example Sessions

### Initial Setup (Finding Right Threshold)

```bash
# Start low with B/W view
python ams_demo.py --backend laser --brightness 30 --bw-palette

# In game:
# 1. Press D (show camera)
# 2. Press B (B/W threshold view)
# 3. Point laser at camera
# 4. Adjust with +/- until only laser is white
# 5. Press B again (back to color view)
# 6. Point laser at targets
```

### Production Setup (After Tuning)

```bash
# Use discovered threshold (example: 80)
python ams_demo.py --backend laser --fullscreen --display 1 --bw-palette --brightness 80

# No need to show camera debug in production
# Targets are bright white on black - easy to see
```

## Technical Details

### Brightness Threshold Range

- **Minimum**: 10 (was 100)
- **Maximum**: 255
- **Default**: 200 (good for bright green lasers)
- **Recommended ranges**:
  - Green lasers: 180-220
  - Red lasers: 120-180
  - Weak/distant lasers: 50-120
  - TV/projector setups: 30-80

### Detection Pipeline

1. Capture camera frame
2. Convert to grayscale
3. Apply Gaussian blur (reduce noise)
4. Threshold: `pixel > brightness_threshold`
5. Morphological operations (clean up)
6. Find contours (bright blobs)
7. Filter by size (5-100 pixels)
8. Extract centroid (laser position)

### B/W View

Shows the result of step 4 (threshold):
- **White pixels**: Above threshold (detected as "bright")
- **Black pixels**: Below threshold (ignored)

This is exactly what the algorithm sees before finding the laser spot.

## Performance Notes

### Threshold Effect on Performance

Lower threshold = more processing:
- Threshold 200: ~2ms per frame
- Threshold 100: ~3ms per frame
- Threshold 30: ~5ms per frame

Still well within 16ms budget for 60 FPS.

### B/W Palette Effect

No performance impact - just changes target colors in game logic.

## Next Steps

1. **Test with current settings**: Start at brightness 50
2. **Tune threshold**: Use B/W view to find optimal value
3. **Save your settings**: Note what works (e.g., brightness 80)
4. **Add to script**: Create launcher script with your values

### Example Launcher Script

```bash
#!/bin/bash
# launch_laser_game.sh

# Optimized settings for my TV setup
python ams_demo.py \
  --backend laser \
  --fullscreen \
  --display 1 \
  --bw-palette \
  --brightness 75 \
  --camera-id 0
```

Make executable: `chmod +x launch_laser_game.sh`

Run: `./launch_laser_game.sh`

---

## Quick Reference Card

```
FOR TV/PROJECTOR:
  python ams_demo.py --backend laser --fullscreen --display 1 --bw-palette --brightness 50

TUNING THRESHOLD:
  Press D (show camera with TARGET OVERLAY)
  Press B (B/W view for tuning)
  Press +/- (adjust threshold)
  Only laser should be white

DEBUG VIEW SHOWS:
  - Camera feed
  - Target circles (where to aim!)
  - Laser detection (green contour)
  - Brightness threshold info

CONTROLS:
  D = Camera debug (with target overlay)
  B = B/W threshold view
  +/- = Adjust brightness
  ESC = Quit
```
