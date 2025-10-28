# Duck Hunt with AMS Integration

Play Duck Hunt with multiple input methods: mouse (for development), laser pointer (for projection setups), or object detection (for physical projectiles).

## Quick Start

### Mouse Mode (Development)
```bash
python ams_game.py --game duckhunt --backend mouse
```

### Laser Mode (Projection Setup)
```bash
# First run - calibrate
python ams_game.py --game duckhunt --backend laser --fullscreen --display 1

# Press 'C' to calibrate with ArUco markers
# Position camera to see all markers, press SPACE

# Subsequent runs - calibration auto-loads
python ams_game.py --game duckhunt --backend laser --fullscreen --display 1
```

### Object Detection Mode (Nerf Darts / Physical Projectiles)
```bash
# First run - calibrate
python ams_game.py --game duckhunt --backend object --fullscreen --display 1

# Press 'C' to calibrate, then shoot objects at targets
python ams_game.py --game duckhunt --backend object --fullscreen --display 1 --mode classic_archery
```

## Game Modes

Three classic Duck Hunt modes available:

### Classic Archery (Default)
```bash
python ams_game.py --game duckhunt --mode classic_archery
```
- Archery-style targets
- 3 rounds
- Limited projectiles per round

### Classic Ducks
```bash
python ams_game.py --game duckhunt --mode classic_ducks
```
- Traditional duck hunting
- Animated duck sprites
- Multiple rounds with increasing difficulty

### Classic Linear
```bash
python ams_game.py --game duckhunt --mode classic_linear
```
- Simple linear trajectory targets
- Good for testing and calibration

## Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--backend` | Input method (mouse/laser) | `--backend laser` |
| `--mode` | Game mode | `--mode classic_ducks` |
| `--fullscreen` | Fullscreen mode | `--fullscreen` |
| `--display N` | Display index | `--display 1` |
| `--camera-id N` | Camera device ID | `--camera-id 0` |
| `--brightness N` | Laser threshold | `--brightness 80` |

## Controls

### Mouse Mode
- **Click**: Shoot
- **ESC**: Quit

### Laser Mode
- **Point laser at targets**: Shoot
- **D**: Toggle debug view (shows camera + target overlay)
- **B**: Toggle B/W threshold view (for tuning)
- **+/-**: Adjust brightness threshold
- **C**: Recalibrate
- **ESC**: Quit

## Setup Workflow

### 1. Test with Mouse
```bash
python ams_game.py --game duckhunt --mode classic_archery
```
Verify game works with mouse input.

### 2. Calibrate for Laser
```bash
python ams_game.py --game duckhunt --backend laser --fullscreen --display 1
```
- ArUco pattern displays on projector
- Camera preview window shows marker detection
- Position camera until all markers detected
- Press SPACE to capture
- Calibration saves to `calibration.json`

### 3. Tune Laser Detection
Press **D** to see debug view:
- White circles = where targets are in camera view
- Should overlay blue targets on projection
- Green contours = detected laser

Press **B** for B/W threshold view:
- Adjust with **+/-** until only laser is white
- Typical values: 50-120 for projectors, 180-220 for green lasers

### 4. Play!
Once calibrated and tuned:
```bash
python ams_game.py --game duckhunt --backend laser --fullscreen --display 1 --mode classic_archery
```

## Troubleshooting

### "No calibration found. Press 'C' to calibrate"
- Normal on first run
- Press **C** during game to calibrate
- Or run `python calibrate.py` separately

### Targets don't align in debug view
- Recalibrate with **C**
- Make sure entire ArUco pattern visible during calibration
- Check for camera distortion

### Laser not detected
- Press **D** to show debug view
- Press **B** for B/W threshold view
- Lower threshold with **-** until laser appears white
- Check laser is bright enough

### Laser detected but no hits register
- Check debug view: white circles should overlay targets
- If misaligned: recalibrate
- Check coordinates in terminal for NaN/infinity errors

## Architecture

```
User Input (Mouse or Laser)
    ↓
Detection Backend
    ↓
AMS Session (calibration, event routing)
    ↓
Duck Hunt Game Mode
    ↓
Pygame Display
```

The AMS handles:
- Coordinate transformation (camera → game space)
- Calibration management
- Event standardization
- Session tracking

The game receives normalized hit coordinates [0,1] and handles:
- Target collision detection
- Scoring
- Game state
- Rendering

## Next Steps

- Try different game modes
- Adjust game difficulty in YAML config files
- Create custom game modes
- Experiment with different laser colors/brightness settings
