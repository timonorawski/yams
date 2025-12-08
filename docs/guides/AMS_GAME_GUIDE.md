# AMS Game Launcher - Quick Start Guide

The AMS Game Launcher (`ams_game.py`) is the unified entry point for all AMS-integrated games with multiple detection backends.

## Quick Start

### 🎯 Simple Targets (Mouse Mode)
Perfect for testing and development:
```bash
python ams_game.py --game simple_targets --backend mouse
```

### 🦆 Duck Hunt (Mouse Mode)
Classic duck hunt with mouse control:
```bash
python ams_game.py --game duckhunt --backend mouse --mode classic_archery
```

### 🔫 Duck Hunt with Laser Pointer
Full projection setup with laser detection:
```bash
# First run - calibrate
python ams_game.py --game duckhunt --backend laser --fullscreen --display 1

# Press 'C' to calibrate with ArUco markers
# Subsequent runs auto-load calibration
```

### 🎯 Duck Hunt with Object Detection (Nerf Darts)
Physical projectile detection:
```bash
python ams_game.py --game duckhunt --backend object --fullscreen --display 1 --mode classic_archery
```

## Available Games

### Simple Targets
A basic target shooting game for testing and demos.

**Features:**
- 3 circular targets
- Score tracking
- Round-based gameplay
- Temporal state management (compensates for latency)

**Commands:**
```bash
# Mouse mode
python ams_game.py --game simple_targets --backend mouse

# Laser mode
python ams_game.py --game simple_targets --backend laser --fullscreen --display 1

# Object detection mode
python ams_game.py --game simple_targets --backend object --fullscreen --display 1

# B/W palette (better for projectors)
python ams_game.py --game simple_targets --backend laser --bw-palette
```

### Duck Hunt
Classic Duck Hunt with multiple game modes.

**Game Modes:**
- `classic_archery` - Archery practice (6 arrows per round)
- `classic_ducks` - Traditional duck hunting (animated ducks)
- `classic_linear` - Linear trajectory targets (good for testing)

**Commands:**
```bash
# Archery mode with mouse
python ams_game.py --game duckhunt --backend mouse --mode classic_archery

# Duck mode with laser
python ams_game.py --game duckhunt --backend laser --mode classic_ducks --fullscreen --display 1

# Linear mode with object detection
python ams_game.py --game duckhunt --backend object --mode classic_linear
```

## Backend Options

### 1. Mouse Backend (`--backend mouse`)
**Best for:** Development, testing, desktop play

- Uses standard mouse input
- No calibration needed
- Works on any computer
- Perfect for development

### 2. Laser Backend (`--backend laser`)
**Best for:** Laser pointer projection setups

- Detects bright laser spot in camera view
- Requires ArUco calibration
- Adjustable brightness threshold
- Works with any bright laser pointer

**Additional Controls:**
- `D` - Toggle debug visualization
- `B` - Toggle B/W threshold view
- `+/-` - Adjust brightness threshold
- `C` - Recalibrate

### 3. Object Detection Backend (`--backend object`)
**Best for:** Physical projectiles (nerf darts, balls, foam arrows)

- Detects colored objects via HSV filtering
- Two impact modes: trajectory_change (bouncing) and stationary (sticking)
- Requires ArUco calibration
- Default: orange/red nerf darts

**Additional Controls:**
- `D` - Toggle debug visualization
- `C` - Recalibrate

**Impact Modes:**
- **TRAJECTORY_CHANGE** (default): Detects bouncing objects
  - Registers impact on sudden velocity or direction changes
  - Perfect for nerf darts, foam balls

- **STATIONARY**: Detects sticking objects
  - Registers impact when object stops and stays
  - Perfect for real darts, arrows that embed

## Command-Line Options

### Game Selection
```
--game {simple_targets,duckhunt}    Game to play (default: simple_targets)
--mode MODE                         Duck Hunt mode (default: classic_archery)
```

### Backend Selection
```
--backend {mouse,laser,object}      Input method (default: mouse)
--camera-id N                       Camera device ID (default: 0)
--brightness N                      Laser brightness threshold (default: 200)
```

### Display Options
```
--fullscreen                        Run in fullscreen
--display N                         Display index (0=primary, 1=secondary)
--resolution WIDTHxHEIGHT          Custom resolution
```

### Game-Specific Options
```
--bw-palette                        Use B/W palette (simple_targets only)
```

## Examples

### Development Testing
```bash
# Quick test with mouse
python ams_game.py --game simple_targets --backend mouse

# Test different Duck Hunt modes
python ams_game.py --game duckhunt --backend mouse --mode classic_ducks
python ams_game.py --game duckhunt --backend mouse --mode classic_linear
```

### Projection Setup
```bash
# First time setup - calibrate
python ams_game.py --game duckhunt --backend laser --fullscreen --display 1

# After calibration (auto-loads)
python ams_game.py --game duckhunt --backend laser --fullscreen --display 1 --mode classic_archery
```

### Physical Archery Setup
```bash
# Nerf dart detection with archery mode
python ams_game.py --game duckhunt --backend object --fullscreen --display 1 --mode classic_archery

# Simple targets for practice
python ams_game.py --game simple_targets --backend object --fullscreen --display 1
```

## In-Game Controls

### Common Controls (All Games)
- `ESC` - Quit game
- `C` - Recalibrate (laser/object backends only)

### Simple Targets Specific
- `R` - Start new round
- `Q` - Quit

### Laser Backend Specific
- `D` - Toggle debug visualization
- `B` - Toggle B/W threshold view
- `+/-` - Adjust brightness threshold

### Object Detection Specific
- `D` - Toggle debug visualization (shows detection mask and velocity vectors)

## Calibration Workflow

### For Laser Backend

1. **Run game** with laser backend
   ```bash
   python ams_game.py --game duckhunt --backend laser --fullscreen --display 1
   ```

2. **Press 'C'** during game to start calibration
   - ArUco pattern displays on projector
   - Camera preview shows marker detection
   - Position camera to see all 16 markers

3. **Press SPACE** when all markers visible
   - Calibration saves to `calibration.json`
   - Auto-loads on subsequent runs

4. **Tune brightness** if needed
   - Press `D` for debug view
   - Press `+/-` to adjust threshold
   - Laser should appear as bright spot

### For Object Detection Backend

1. **Run game** with object backend
   ```bash
   python ams_game.py --game duckhunt --backend object --fullscreen --display 1
   ```

2. **Calibrate** same as laser (press 'C', position camera, press SPACE)

3. **Tune color detection**
   - Press `D` for debug view
   - Throw/shoot your object through camera view
   - Object should appear white in mask (right panel)
   - Adjust HSV ranges in code if needed

4. **Test impact detection**
   - Shoot object at targets
   - Green box shows tracking
   - Blue arrow shows velocity
   - Red circle appears on impact

## Troubleshooting

### Game won't start
- Check that you're in the project root directory
- Verify virtual environment is activated: `source venv/bin/activate`
- Check that pygame is installed: `pip install pygame`

### Calibration fails
- Ensure entire ArUco pattern is visible in camera
- Try better lighting
- Check camera is working: `ls /dev/video*` (Linux) or check System Settings (Mac)

### Laser not detected
- Press `D` to show debug view
- Laser should appear as bright spot
- Lower brightness threshold with `-` key
- Ensure laser is bright enough

### Object not detected
- Press `D` to show debug view
- Object should appear white in mask (right panel)
- Adjust HSV ranges in code for your object color
- Ensure good lighting and contrasting background

## Next Steps

- Try different game modes
- Experiment with different detection backends
- Adjust detection parameters for your setup
- Check individual guides:
  - `DUCKHUNT_AMS_GUIDE.md` - Duck Hunt details
  - `LASER_TUNING_GUIDE.md` - Laser detection tuning
  - `OBJECT_DETECTION_GUIDE.md` - Object detection setup

## Future: On-Projection Menu

Coming soon: An on-projection menu system to select games without command-line arguments!

```
┌─────────────────────────────────┐
│      AMS GAME LAUNCHER          │
├─────────────────────────────────┤
│  1. Simple Targets              │
│  2. Duck Hunt - Archery         │
│  3. Duck Hunt - Ducks           │
│  4. Duck Hunt - Linear          │
└─────────────────────────────────┘
   Point laser to select...
```
