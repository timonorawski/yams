# Fullscreen and Multi-Display Support

The AMS demo now supports fullscreen mode with multi-display selection, perfect for projector setups.

## Quick Start

### Fullscreen on Primary Display
```bash
python ams_demo.py --fullscreen
```

### Fullscreen on Secondary Display (Projector)
```bash
# Display 0 = Primary monitor
# Display 1 = Secondary monitor (projector)
python ams_demo.py --fullscreen --display 1
```

### Fullscreen on Secondary Display with Laser Backend
```bash
python ams_demo.py --backend laser --fullscreen --display 1
```

## Command-Line Options

### Display Options

| Option | Description | Example |
|--------|-------------|---------|
| `--fullscreen` | Enable fullscreen mode | `--fullscreen` |
| `--display N` | Select display (0=primary, 1=secondary, etc.) | `--display 1` |
| `--resolution WxH` | Set custom resolution (windowed mode only) | `--resolution 1920x1080` |

### Backend Options

| Option | Description | Example |
|--------|-------------|---------|
| `--backend mouse` | Use mouse input (default) | `--backend mouse` |
| `--backend laser` | Use laser pointer detection | `--backend laser` |
| `--camera-id N` | Camera to use for laser backend | `--camera-id 0` |
| `--brightness N` | Brightness threshold for laser (0-255) | `--brightness 200` |

## Runtime Controls

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **ESC** or **Q** | Quit game |
| **F** | Toggle fullscreen on/off |
| **C** | Recalibrate |
| **R** | Start new round |
| **D** | Toggle debug view (laser mode only) |
| **+** | Increase brightness threshold (laser mode only) |
| **-** | Decrease brightness threshold (laser mode only) |

## Common Usage Patterns

### Development Setup (Single Monitor)

Windowed mode for easy switching:
```bash
python ams_demo.py --backend mouse
```

### Projector Demo (Dual Monitor)

Game fullscreen on projector, debug on laptop:
```bash
# Mouse input
python ams_demo.py --fullscreen --display 1

# Laser input (camera debug window shows on primary display)
python ams_demo.py --backend laser --fullscreen --display 1
```

### Testing Different Resolutions

Test in windowed mode with specific resolution:
```bash
python ams_demo.py --resolution 1920x1080
python ams_demo.py --resolution 1280x720
```

## Display Detection

When you run with `--fullscreen`, the program will print available displays:

```
Available displays: 2
  Display 0: 1920x1080
  Display 1: 1920x1200

Using display 1: 1920x1200
Fullscreen mode enabled
```

This helps you identify which display index to use.

## Troubleshooting

### Game Opens on Wrong Display

**Problem**: Game opens on primary display instead of projector

**Solution**:
```bash
# Check which displays are detected
python ams_demo.py --fullscreen --display 1

# Try different display index if needed
python ams_demo.py --fullscreen --display 0  # Primary
python ams_demo.py --fullscreen --display 1  # Secondary
```

### Display Index Not Found

**Problem**: "Display X not found, using display 0"

**Cause**: You specified `--display 2` but only have 2 displays (0 and 1)

**Solution**: Use `--display 0` or `--display 1`

### Fullscreen Wrong Resolution

**Problem**: Fullscreen uses wrong resolution

**Cause**: Pygame auto-detects display resolution

**Solution**:
- Resolution is automatically detected per-display
- Use `toggle_fullscreen()` (press **F**) to switch modes
- Check display detection output at startup

### Can't Exit Fullscreen

**Problem**: Stuck in fullscreen mode

**Solution**: Press **ESC** or **F** to exit

## Laser Backend with Projector Setup

### Recommended Setup

1. **Projector**: Display 1 (game fullscreen)
2. **Laptop/Monitor**: Display 0 (camera debug window)

```bash
python ams_demo.py --backend laser --fullscreen --display 1
```

This shows:
- Game fullscreen on projector (targets, score)
- Debug window on laptop (camera view, detection)

### Debug Window Controls

Press **D** in-game to toggle the camera debug window:
- **Enabled**: See laser detection in real-time
- **Disabled**: Game only (cleaner presentation)

## Examples

### Basic Testing
```bash
# Mouse, windowed
python ams_demo.py

# Laser, windowed
python ams_demo.py --backend laser
```

### Projector Demo
```bash
# Mouse, fullscreen on projector
python ams_demo.py --fullscreen --display 1

# Laser, fullscreen on projector
python ams_demo.py --backend laser --fullscreen --display 1
```

### Custom Configurations
```bash
# Windowed 1080p with laser
python ams_demo.py --backend laser --resolution 1920x1080

# Fullscreen on projector with dim red laser
python ams_demo.py --backend laser --fullscreen --display 1 --brightness 150

# Fullscreen on projector with external camera
python ams_demo.py --backend laser --fullscreen --display 1 --camera-id 1
```

## Architecture Notes

### Coordinate Systems

The game uses **normalized coordinates** [0, 1] internally:
- (0, 0) = top-left
- (1, 1) = bottom-right

This ensures the game works at any resolution:
- 1280x720 windowed
- 1920x1080 fullscreen
- 1920x1200 projector

Targets scale automatically based on `min(width, height)`.

### Multi-Display Positioning

Pygame positions the fullscreen window using `SDL_VIDEO_WINDOW_POS`:
```python
# Display 0: x=0
# Display 1: x=1920 (if display 0 is 1920px wide)
# Display 2: x=3840 (if displays 0+1 are 1920px wide each)
```

The program calculates this automatically.

## Performance

### Frame Rate

Target: 60 FPS

Fullscreen mode typically has **better** performance than windowed:
- No compositor overhead
- Direct rendering to display
- No window decorations

### Latency

| Backend | Latency | Notes |
|---------|---------|-------|
| Mouse | ~0ms | Instant |
| Laser | ~50ms | CV processing time |

Resolution doesn't significantly affect latency (game logic is lightweight).

## Next Steps

1. **Test with mouse first**: Verify fullscreen works
   ```bash
   python ams_demo.py --fullscreen --display 1
   ```

2. **Test with laser**: Ensure camera works in fullscreen
   ```bash
   python ams_demo.py --backend laser --fullscreen --display 1
   ```

3. **Adjust settings**: Use **+/-** and **F** keys to tune

4. **Add calibration**: Run ArUco calibration for accuracy (optional)

---

**Quick Reference Card**

```
Fullscreen on Projector:
  python ams_demo.py --fullscreen --display 1

Laser + Fullscreen:
  python ams_demo.py --backend laser --fullscreen --display 1

Exit Fullscreen:
  Press ESC or F
```
