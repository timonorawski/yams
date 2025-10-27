

# Arcade Management System (AMS)

**Status**: ✅ Initial Implementation Complete

The AMS is an abstraction layer between detection hardware and games, enabling games to work across different input methods and deployment platforms without modification.

## Overview

The AMS provides the foundation for building projection-based interactive games where physical actions (thrown objects, laser pointers, arrows, mouse clicks) create coordinate-based input events.

### Core Philosophy

> **"Code is not the asset, the developer is"** - Build clean abstractions that enable rapid iteration

- **Always recalibrate between rounds**: Optimize for robustness, not for skipping calibration
- **Games query the past**: Detection reports what happened when; games maintain state history
- **Platform-agnostic from day one**: Same games work with webcam, mobile AR, projectors, or mouse clicks

## Architecture

The system has three independent layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    DETECTION LAYER                           │
│  (Mouse, CV, AR, Laser Pointer, etc.)                       │
│                                                              │
│  Produces: PlaneHitEvent(x, y, timestamp, metadata)         │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   AMS (THIS LAYER)                           │
│                                                              │
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │  Calibration   │  │  Temporal State  │  │  Event      │ │
│  │  Management    │  │  Management      │  │  Routing    │ │
│  └────────────────┘  └──────────────────┘  └─────────────┘ │
│                                                              │
│  - Normalizes coordinates [0, 1]                            │
│  - Manages color palette (CV detection)                     │
│  - Provides temporal hit queries                            │
│  - Handles session state                                     │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                     GAME LAYER                               │
│  (DuckHunt, Target Practice, etc.)                          │
│                                                              │
│  Inherits: TemporalGameState                                │
│  Receives: PlaneHitEvents                                   │
│  Queries: was_target_hit(x, y, timestamp)                   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Running the Demo

```bash
python ams_demo.py
```

**Controls:**
- Click on targets to shoot
- Press 'C' to recalibrate
- Press 'R' to start new round
- Press 'Q' to quit

### Building a Game

```python
from ams.temporal_state import TemporalGameState
from ams.events import PlaneHitEvent, HitResult

class MyGame(TemporalGameState):
    def __init__(self):
        super().__init__(history_duration=5.0, fps=60)
        self.targets = []  # Your game state

    def update(self, dt):
        # Update game logic
        self.update_targets(dt)
        # Capture state snapshot (automatic)
        super().update(dt)

    def get_current_state_snapshot(self):
        # Return deep copy of current state
        return {
            'targets': [t.copy() for t in self.targets]
        }

    def check_hit_in_snapshot(self, snapshot, x, y):
        # Query a specific snapshot for hits
        for target in snapshot['targets']:
            if target.contains(x, y):
                return HitResult(hit=True, points=100)
        return HitResult(hit=False)

    def handle_hit_event(self, event: PlaneHitEvent):
        # Query historical state at event timestamp
        result = self.was_target_hit(event.x, event.y, event.timestamp)
        if result.hit:
            self.score += result.points
```

### Using with AMS

```python
from ams.session import AMSSession
from ams.detection_backend import InputSourceAdapter
from input.sources.mouse import MouseInputSource

# Setup detection backend
mouse = MouseInputSource()
backend = InputSourceAdapter(mouse, 1280, 720)

# Create AMS session
ams = AMSSession(backend, session_name="my_game")

# Calibrate
ams.calibrate()

# Game loop
while running:
    ams.update(dt)

    # Get events
    for event in ams.poll_events():
        result = game.handle_hit_event(event)

    game.update(dt)
    game.render()

# Session data saves automatically
```

## Components

### 1. Event Types (`ams/events.py`)

**PlaneHitEvent** - Standard format for all detection:
- Normalized coordinates [0, 1]
- Timestamp (for temporal queries)
- Confidence and metadata

**HitResult** - What games return from hit queries:
- Hit status (boolean)
- Target information
- Points awarded
- Frame/state context

**CalibrationResult** - Result of calibration:
- Success status
- Available color palette
- Detection quality metrics

### 2. Temporal State Management (`ams/temporal_state.py`)

**TemporalGameState** - Base class for games:
- Automatic state history maintenance (5 seconds default)
- `was_target_hit(x, y, timestamp)` - query past states
- Handles detection latency automatically

**Why Temporal Queries?**
- Display latency varies (50-300ms depending on platform)
- Projectile flight time is significant (200-500ms)
- Detection happens AFTER game state has advanced
- Games query their own history to determine if detection corresponds to a hit

### 3. Detection Backends (`ams/detection_backend.py`)

**DetectionBackend** - Abstract interface:
- `poll_events()` → List[PlaneHitEvent]
- `update(dt)` → Update backend state
- `calibrate()` → Run calibration

**InputSourceAdapter** - Wraps existing DuckHunt InputSource:
- Converts InputEvents → PlaneHitEvents
- Normalizes pixel coords → [0, 1]
- Compatible with existing mouse input

**Future Backends** (ready to implement):
- `CVDetectionBackend` - Computer vision impact detection
- `ARDetectionBackend` - Mobile AR tracking
- `LaserDetectionBackend` - Laser pointer detection

### 4. Calibration System (`ams/calibration.py`)

**CalibrationSession** - Manages calibration workflow:

**For Mouse/Keyboard** (current):
- Instant no-op calibration
- Full color palette available
- Perfect detection quality (1.0)

**For CV** (architecture ready):
1. Measure display latency (button press → pattern detection)
2. Background characterization (cycle colors, capture statistics)
3. Object characterization (capture projectile under each color)
4. Compute available palette (which colors enable reliable detection)

**Philosophy: Always Recalibrate Between Rounds**
- Lighting changes constantly
- Surface evolves (wear, moisture)
- Equipment drifts (projector warming)
- Cost is negligible (3-6 seconds, integrated as interstitial)

### 5. Session Management (`ams/session.py`)

**AMSSession** - Main AMS interface:
- Manages detection backend
- Coordinates calibration
- Routes events to game
- Handles session state (scores, progress)
- Automatic save/load

## File Structure

```
ArcheryGame/
├── ams/
│   ├── __init__.py
│   ├── events.py                 # PlaneHitEvent, HitResult, CalibrationResult
│   ├── temporal_state.py         # TemporalGameState base class
│   ├── detection_backend.py      # DetectionBackend interface, InputSourceAdapter
│   ├── calibration.py            # CalibrationSession (color characterization)
│   └── session.py                # AMSSession (main interface)
│
├── games/
│   └── base/
│       ├── __init__.py
│       └── simple_targets.py     # Example game using TemporalGameState
│
├── ams_demo.py                   # Complete integration demo
├── AMS_README.md                 # This file
└── Games/DuckHunt/               # Existing game (uses AMS input abstraction)
    └── input/
        └── sources/
            └── mouse.py          # MouseInputSource (wrapped by AMS)
```

## How It Works

### Data Flow Example

```
1. User clicks mouse at (640, 360) pixels
   ↓
2. MouseInputSource produces InputEvent(position=(640, 360), timestamp=123.456)
   ↓
3. InputSourceAdapter normalizes coords → PlaneHitEvent(x=0.5, y=0.333, timestamp=123.456)
   ↓
4. AMSSession routes to game
   ↓
5. Game queries: was_target_hit(0.5, 0.333, 123.456)
   ↓
6. TemporalGameState finds snapshot at timestamp 123.456
   ↓
7. Game's check_hit_in_snapshot() examines that historical state
   ↓
8. Returns HitResult(hit=True, points=100) if target was there THEN
   ↓
9. Game updates current score, spawns new target
```

### Temporal Query Example

```python
# Time: t=0.0 - Target spawns at (0.5, 0.5)
game.targets = [Target(x=0.5, y=0.5)]

# Time: t=0.3 - User fires projectile
# (projectile is in flight, takes 200ms to hit)

# Time: t=0.4 - Target moves to (0.6, 0.5)
game.targets[0].x = 0.6

# Time: t=0.5 - Projectile hits wall at (0.5, 0.5)
# Camera detects impact (50ms latency)

# Time: t=0.55 - Detection event arrives
event = PlaneHitEvent(x=0.5, y=0.5, timestamp=0.5)

# Question: Is this a hit?
# WITHOUT temporal queries: Check current state at t=0.55
#   → Target is at (0.6, 0.5) → MISS (wrong!)

# WITH temporal queries: Check state at event.timestamp (t=0.5)
result = game.was_target_hit(0.5, 0.5, timestamp=0.5)
#   → TemporalGameState finds snapshot at t=0.5
#   → Target WAS at (0.5, 0.5) at that time
#   → HIT! (correct!)
```

## Integration with Existing Code

The AMS is designed to **complement, not replace** existing systems:

### DuckHunt Integration

The existing DuckHunt game already has:
- `InputEvent` - similar to `PlaneHitEvent`
- `InputSource` - abstract input interface
- `MouseInputSource` - mouse input implementation

**AMS adds on top**:
- `InputSourceAdapter` - wraps InputSource for AMS compatibility
- Temporal state management (optional, games can choose)
- Calibration interface (ready for CV detection)
- Normalized coordinates [0, 1]

**Migration Path**:
1. **Keep using bare InputSource** - works as before
2. **Add AMS wrapper** - get normalized coords
3. **Add TemporalGameState** - get temporal queries
4. **Add CV backend** - games work unchanged!

## Next Steps

### Immediate (Working Now)

- ✅ Mouse/keyboard input
- ✅ Temporal state management
- ✅ Session management
- ✅ Demo game
- ✅ Architecture validated

### Phase 2 (Ready to Implement)

- [ ] CV Detection Backend
  - Integrate with existing calibration system
  - Implement color characterization
  - Add display latency measurement
- [ ] More game examples
- [ ] Performance profiling
- [ ] Documentation expansion

### Phase 3 (Future)

- [ ] AR detection backend (mobile)
- [ ] Laser pointer detection
- [ ] Multi-player session support
- [ ] Replay/analysis features
- [ ] Advanced game modes

## Design Principles

### 1. Clean Abstractions
Detection, AMS, and Games are independent. Changes to one don't require changes to others.

### 2. Test Without Hardware
Mock detection events for testing. Games work with mouse before requiring camera setup.

### 3. Platform Portability
Design works for Python CLI, WASM/browser, or mobile native. Only detection/display layers change.

### 4. Fail Visibly
If calibration can't achieve good detection quality, tell user why and what to fix. Don't silently degrade.

### 5. Educational Code
Code teaches systems design principles. Comment *why*, not just *what*.

## Key Insights

### From Implementation

1. **Temporal queries solve latency elegantly** - Games don't need to know about latency, they just query their own history
2. **Normalization simplifies everything** - [0, 1] coords work everywhere, resolution-independent
3. **Calibration as no-op works** - Mouse backend proves architecture without CV complexity
4. **Adapter pattern enables reuse** - Existing DuckHunt input works with AMS unchanged
5. **Pydantic for events is powerful** - Type safety, validation, serialization for free

### Architecture Validation

✅ **Mouse input works** - Proves detection abstraction
✅ **Temporal queries work** - Can test with simulated latency
✅ **Calibration interface works** - No-op for mouse, ready for CV
✅ **Games are generic** - Don't know about detection method
✅ **Session management works** - Scores save/load correctly

The architecture is **validated and ready** for CV detection backend implementation.

## Technical Notes

- Python 3.10+, type hints throughout
- Pygame for rendering/display
- Pydantic for data models
- Well-commented code explaining design decisions
- Unit tests for core functionality (see individual modules)

## References

- [AMS.md](Games/DuckHunt/AMS.md) - Original architecture document
- [CALIBRATION_SYSTEM_PLAN.md](CALIBRATION_SYSTEM_PLAN.md) - CV calibration details
- [SESSION_SUMMARY_2025-10-25.md](SESSION_SUMMARY_2025-10-25.md) - Development history

---

**Status**: Ready for CV detection backend implementation
**Last Updated**: October 25, 2025
**Version**: 1.0 (Initial Implementation)
