# Balloon Pop

Pop balloons as they float up from the bottom of the screen!

## Running

### Standalone (Mouse Input)
```bash
# From project root
python games/BalloonPop/main.py

# Or from game directory
cd games/BalloonPop && python main.py
```

### With AMS (Detection Backends)
```bash
# Mouse (testing)
python ams_game.py --game balloonpop --backend mouse

# Laser pointer
python ams_game.py --game balloonpop --backend laser --fullscreen

# Object detection (nerf darts)
python ams_game.py --game balloonpop --backend object --fullscreen
```

## Configuration

Settings are loaded from `.env` file. Create `.env.local` to override:

```env
# Balloon spawning
SPAWN_RATE=1.5           # Seconds between spawns
BALLOON_MIN_SIZE=40      # Minimum balloon size (pixels)
BALLOON_MAX_SIZE=80      # Maximum balloon size (pixels)

# Movement
FLOAT_SPEED_MIN=50       # Minimum float speed (pixels/sec)
FLOAT_SPEED_MAX=150      # Maximum float speed (pixels/sec)
DRIFT_SPEED_MAX=30       # Max horizontal drift (pixels/sec)

# Game rules
MAX_ESCAPED=10           # Game over after this many escape
TARGET_POPS=0            # Win condition (0 = endless)
```

## Command-Line Options

```bash
python main.py --spawn-rate 0.5    # Faster spawning
python main.py --max-escaped 5     # Harder game
python main.py --target-pops 50    # Win after 50 pops
python main.py --fullscreen        # Fullscreen mode
```

## Controls

- **Click/Shoot**: Pop balloons
- **R**: Restart game
- **ESC**: Quit

## Architecture

Uses the same input abstraction as DuckHunt:
- `input/` - InputManager, InputSource, InputEvent
- Works identically in standalone (mouse) and AMS (laser/object) modes
