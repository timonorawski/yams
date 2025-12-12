# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**YAMS (YAML Arcade Management System)** is an interactive projection targeting platform that uses computer vision to create engaging games for any projectile-based activity. A projector displays targets on a surface, a camera detects impacts, and the system provides real-time feedback.

**Website**: https://yamplay.cc

### Use Cases

**Projectile-Based (Point Detection)**
- Archery (foam-tip and real arrows)
- Nerf darts and blasters
- Ball/foam ball throwing
- Darts
- Axe/knife throwing (into soft targets)
- Laser pointer games
- Any activity where something hits a visible surface

**Full-Body Interaction (Occlusion Detection)**
- Laser maze games (jump over/duck under projected "beams")
- Physically interactive sidescrollers (body controls character)
- Dance/movement games
- Shadow-based interaction
- Any activity where body occludes projected patterns

The core tech - projector/camera coordinate mapping with occlusion detection - enables both point-based targeting AND full-body interaction through the same calibration system.

### Design Philosophy

**Variable practice over repetition**: Each attempt should be a fresh problem (different position, timing, decision) to build adaptable skill rather than context-dependent muscle memory.

**Use-case agnostic architecture**: The core system is completely agnostic to projectile type. Detection methods vary, but coordinate mapping and game engine remain the same.

**Code is not the asset, the developer is**: Build clean abstractions that enable rapid iteration.

**Games work standalone**: Games should be playable with mouse/keyboard without requiring YAMS or hardware. YAMS integration is additive.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DETECTION LAYER                           │
│  Mouse | Laser Pointer | Object Detection | Future: AR      │
│                                                              │
│  Produces: PlaneHitEvent(x, y, timestamp, metadata)         │
│            (normalized [0,1] coordinates)                    │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   AMS CORE (/ams/)                           │
│                                                              │
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │  Calibration   │  │  Temporal State  │  │  Session    │ │
│  │  Management    │  │  Management      │  │  & Events   │ │
│  └────────────────┘  └──────────────────┘  └─────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  AMSInputAdapter (ams/game_adapter.py)               │  │
│  │  Converts PlaneHitEvent → InputEvent (pixel coords)  │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                     GAME LAYER                               │
│  Simple Targets | Duck Hunt | Future games                  │
│                                                              │
│  Uses: InputManager + InputSource (unified interface)       │
│  Receives: InputEvent (pixel coordinates)                   │
│  Same code works standalone OR with YAMS                    │
└─────────────────────────────────────────────────────────────┘
```

### Input Abstraction

Games use a unified input system that works identically in standalone and YAMS modes:

```python
# Standalone mode (development)
from input.input_manager import InputManager
from input.sources.mouse import MouseInputSource
input_manager = InputManager(MouseInputSource())

# YAMS mode (production)
from ams.game_adapter import AMSInputAdapter
input_manager = InputManager(AMSInputAdapter(ams_session, width, height))

# Game code is identical either way:
events = input_manager.get_events()  # Returns List[InputEvent]
game_mode.handle_input(events)       # Same interface
```

Key files:
- `games/DuckHunt/input/sources/base.py` - `InputSource` interface
- `games/DuckHunt/input/input_event.py` - `InputEvent` (pixel coordinates)
- `ams/game_adapter.py` - `AMSInputAdapter` (bridges AMS → game input)

### Key Components

| Directory | Purpose |
|-----------|---------|
| `/ams/` | Core YAMS system - detection backends, calibration, events, temporal state |
| `/calibration/` | ArUco-based geometric calibration system |
| `/models/` | Unified Pydantic data models |
| `/games/` | Game implementations (Simple Targets, Duck Hunt) |
| `/docs/` | Documentation (guides, history) |

## Running the System

### Standalone Games (No YAMS)

Games can run independently with mouse/keyboard input for development and testing:

```bash
# Duck Hunt standalone (mouse input, no YAMS required)
cd games/DuckHunt && python main.py
```

This is useful for:
- Game development without hardware setup
- Testing game mechanics in isolation
- UI/UX iteration

### With YAMS (Detection Backends)

For projection setups with camera-based detection:

```bash
# Simple targets with mouse (testing YAMS integration)
python ams_game.py --game simple_targets --backend mouse

# Duck Hunt with laser pointer
python ams_game.py --game duckhunt --backend laser --fullscreen --display 1

# Duck Hunt with object detection (nerf darts)
python ams_game.py --game duckhunt --backend object --mode classic_archery
```

### Calibration
```bash
python calibrate.py --projector-width 1920 --projector-height 1080 --camera-id 0
```

## Detection Backends

### 1. Mouse (`--backend mouse`)
- Development and testing
- No calibration needed
- Perfect for rapid iteration

### 2. Laser Pointer (`--backend laser`)
- `/ams/laser_detection_backend.py`
- Brightness threshold detection
- ~50ms latency
- Great for demos and testing geometric calibration

### 3. Object Detection (`--backend object`)
- `/ams/object_detection_backend.py`
- Color blob detection (HSV filtering)
- Velocity tracking with two impact modes:
  - **TRAJECTORY_CHANGE**: Detects bouncing objects (nerf darts)
  - **STATIONARY**: Detects objects that stop (real darts, arrows in foam)
- ~100-150ms latency

## Data Models

All data structures use Pydantic for type safety and serialization. Models are in `/models/`:

- `primitives.py` - Point2D, Vector2D, Resolution, Color, Rectangle
- `calibration.py` - CalibrationData, HomographyMatrix, CalibrationQuality
- `game.py` - ImpactDetection, TargetDefinition, HitResult
- `duckhunt/` - Duck Hunt specific models and game mode configs

## Calibration System

Uses ArUco markers for geometric calibration:
1. Projects 4x4 marker grid onto target surface
2. Camera detects markers
3. Computes homography: Camera Space → Projector Space → Game Space
4. Achieves sub-pixel accuracy (0.25px RMS in testing)

Calibration data saved to `calibration.json` and auto-loaded on startup.

## Temporal State Management

Games inherit from `TemporalGameState` to handle detection latency:

```python
class MyGame(TemporalGameState):
    def was_target_hit(self, x, y, timestamp):
        # Query historical state at detection timestamp
        snapshot = self.get_state_at(timestamp)
        return check_hit(snapshot, x, y)
```

This allows accurate hit detection even with 100-200ms detection latency.

## Development Guidelines

### Adding a New Detection Backend

1. Create class implementing `DetectionBackend` interface (`/ams/detection_backend.py`)
2. Implement `update(dt)` and `poll_events()` methods
3. Return `PlaneHitEvent` with normalized [0,1] coordinates
4. Add to `ams_game.py` backend selection

### Adding a New Game

1. Create game in `/games/your_game/`
2. **Make it work standalone first** with mouse/keyboard input:
   - Copy DuckHunt's `input/` directory for the input abstraction
   - Use `InputManager` + `MouseInputSource` for mouse input
   - Game receives `InputEvent` with pixel coordinates
   - Create a `main.py` entry point for standalone testing
3. Add YAMS integration (automatic if using InputManager):
   - In `ams_game.py`, create `AMSInputAdapter` wrapping the YAMS session
   - Pass adapter to `InputManager` instead of `MouseInputSource`
   - Game code remains unchanged - same `InputEvent` interface
4. Optionally add temporal state management for latency compensation:
   - Inherit from `TemporalGameState`
   - Implement `was_target_hit(x, y, timestamp)` for historical queries

### Code Style

- Python 3.10+, type hints throughout
- Pydantic models for all data structures
- Well-commented code explaining *why*, not just *what*
- Prefer editing existing files over creating new ones

## Directory Structure

```
ArcheryGame/
├── ams/                      # Core YAMS system
│   ├── session.py           # Main YAMS interface
│   ├── detection_backend.py # Backend interface
│   ├── game_adapter.py      # AMSInputAdapter (YAMS → game input bridge)
│   ├── laser_detection_backend.py
│   ├── object_detection_backend.py
│   ├── temporal_state.py    # TemporalGameState base class
│   ├── events.py            # PlaneHitEvent, HitResult
│   ├── calibration.py       # CalibrationSession
│   ├── camera.py            # Camera interface
│   └── object_detection/    # Pluggable detectors
├── calibration/             # Geometric calibration
│   ├── calibration_manager.py
│   ├── pattern_generator.py # ArUco grid generation
│   ├── pattern_detector.py  # Marker detection
│   └── homography.py        # Transform computation
├── models/                  # Pydantic data models
│   ├── primitives.py
│   ├── calibration.py
│   ├── game.py
│   └── duckhunt/
├── games/
│   ├── base/
│   │   └── simple_targets.py
│   └── DuckHunt/            # Full game with modes, trajectories
├── docs/
│   ├── guides/              # User and developer guides
│   └── history/             # Historical planning docs
├── pasture/                 # Archived WIP/experimental code
├── ams_game.py              # Main entry point
├── calibrate.py             # Calibration CLI
└── CLAUDE.md                # This file
```

## Future Vision

### Detection Methods (Not Yet Implemented)
- **Pattern Differencing**: Use inverse homography to predict camera view, detect occlusions where projectile blocks projected pattern. Enables precise impact detection for any projectile without color requirements.
- **AR Detection**: Mobile AR tracking for phone-based games
- **Depth Sensors**: True 3D tracking for complex scenarios

### Games and Features
- Multiple game modes beyond Duck Hunt
- Multiplayer support
- Performance tracking and progression
- On-projection menu system (select games without command line)
- Raspberry Pi portable packaging

### Calibration Enhancements
- Color characterization (determine which colors enable reliable detection)
- Interstitial calibration between rounds (invisible to user)
- Auto-recalibration when equipment drifts

## Key Files

| File | Purpose |
|------|---------|
| `ams_game.py` | **Start here** - unified launcher |
| `ams/session.py` | Main YAMS class, ties everything together |
| `ams/game_adapter.py` | **AMSInputAdapter** - bridges YAMS to game input |
| `ams/temporal_state.py` | Temporal queries for latency handling |
| `calibration/calibration_manager.py` | Calibration API |
| `games/DuckHunt/input/` | Input abstraction (InputManager, InputSource, InputEvent) |
| `models/__init__.py` | All model exports |

## Testing

```bash
# Run DuckHunt tests
cd games/DuckHunt && pytest tests/

# Test laser detection
python test_laser_detection.py --test all
```

## Documentation

- `/docs/guides/` - User guides for setup and operation
- `/docs/history/` - Historical planning docs with YAML frontmatter
- DuckHunt has its own README at `/games/DuckHunt/README.md`
