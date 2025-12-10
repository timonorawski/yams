# AMS - Arcade Management System

An interactive projection targeting platform that uses computer vision to create engaging games for projectile-based activities.

## What It Does

A projector displays targets on any flat surface. A camera detects when something hits the target area. The system provides real-time visual and audio feedback. Works with laser pointers, nerf darts, foam arrows, balls, or any projectile.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Play Duck Hunt with mouse (for testing)
python ams_game.py --game duckhunt --backend mouse

# Play with laser pointer (requires calibration)
python ams_game.py --game duckhunt --backend laser --fullscreen --display 1

# Play with nerf dart detection
python ams_game.py --game duckhunt --backend object --fullscreen --display 1
```

## Features

- **3 Detection Backends**: Mouse (testing), laser pointer, object detection
- **Geometric Calibration**: ArUco marker-based camera-projector alignment
- **Temporal Hit Detection**: Handles detection latency automatically
- **Duck Hunt Game**: Full implementation with multiple modes
- **Extensible Architecture**: Easy to add new games and detection methods

## Hardware Setup

- Projector (any resolution)
- Webcam or USB camera
- Flat projection surface
- Optional: Laser pointer or colorful projectiles

## Documentation

- See `CLAUDE.md` for architecture overview
- See `docs/guides/` for setup guides
- See `docs/history/` for design rationale

## Project Structure

```
├── ams/              # Core detection and calibration
├── calibration/      # ArUco-based geometric calibration
├── models/           # Pydantic data models
├── games/            # Game implementations
│   ├── base/         # Simple targets example
│   └── DuckHunt/     # Full Duck Hunt game
├── docs/             # Documentation
└── ams_game.py       # Main entry point
```

## License

CC-BY-NC-SA 4.0 with a heart:

You can use, modify, and share this freely for non-commercial purposes
(personal use, schools, non-profits, publicly subsidized daycares, makerspaces, art projects, ...).

If you're a business making money with it (installations, arcades, events, etc.),
don't be a jerk—just reach out and we'll figure out a fair contribution
or a simple commercial license. No gotchas, no NDAs, no 50-page contracts.

In short: be cool, share alike, and if you're getting paid, help keep it alive and make it better for everyone.

https://creativecommons.org/licenses/by-nc-sa/4.0/
