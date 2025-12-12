# YAMS Architecture & Design Decisions

This document captures architectural decisions and serves as a guide for working on the YAML Arcade Management System (YAMS).

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     DETECTION BACKENDS                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │    Mouse     │  │  Laser Pointer   │  │ Object Detection │  │
│  │   Adapter    │  │    Backend       │  │    Backend       │  │
│  │  (testing)   │  │  (transient)     │  │  (persistent)    │  │
│  └──────┬───────┘  └────────┬─────────┘  └────────┬─────────┘  │
│         │                   │                     │             │
│         └───────────────────┼─────────────────────┘             │
│                             │                                   │
│                             ▼                                   │
│              PlaneHitEvent(x, y, timestamp)                     │
│                   normalized [0, 1]                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AMS SESSION                              │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Calibration │  │   Event     │  │   Temporal State        │ │
│  │  Manager    │  │  Routing    │  │   (latency handling)    │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          GAMES                                  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      BaseGame                            │   │
│  │  (BalloonPop, Containment, FruitSlice, Grouping,        │   │
│  │   GrowingTargets, ManyTargets)                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 DuckHunt (own GameMode)                  │   │
│  │            [tech debt - not yet migrated]                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Detection Backends

The system supports multiple detection backends for different physical input types.

### Backend Comparison

| Backend | Use Case | Detection Type | Tracking | Latency | Hardware |
|---------|----------|----------------|----------|---------|----------|
| `InputSourceAdapter` | Development/testing | Immediate | None | ~0ms | Mouse/keyboard |
| `LaserDetectionBackend` | Laser pointers | Instantaneous | None | ~50ms | Camera + laser |
| `ObjectDetectionBackend` | Arrows, darts, balls | Tracked | Motion → Impact | ~100-500ms | Camera |

### LaserDetectionBackend

**Purpose**: Detect laser pointer dots on projection surface.

**Key insight**: Laser detection is **instantaneous and untracked**.

**Characteristics**:
- **Instantaneous**: Laser dot appears at impact location immediately (speed of light)
- **Untracked**: No trajectory to follow - dot just appears where user points
- **Transient**: Dot only visible while user holds trigger/button
- **Brightness-based**: Looks for bright spots above threshold
- **Low latency**: Detection happens in same frame dot appears
- **Simple calibration**: Just needs brightness threshold tuning

**Detection approach**:
1. Scan frame for bright spots above threshold
2. Filter by size/shape (laser dots are small, round)
3. Report position immediately - no trajectory analysis needed

**When to use**: Laser pointer games, Nerf blasters with laser sights, instant feedback scenarios.

### ObjectDetectionBackend

**Purpose**: Detect physical projectiles (arrows, darts, thrown objects).

**Key insight**: Objects must be **detected, tracked, then traced to impact moment**.

**Characteristics**:
- **Tracked**: Object must be followed through flight path
- **Impact detection**: Must determine WHEN and WHERE object impacted
- **Higher latency**: Object flight time + detection processing
- **Complex calibration**: Background modeling, object recognition

**Detection pipeline**:
1. **Detect**: Identify object entering field of view
2. **Track**: Follow object across frames, compute velocity
3. **Impact**: Detect impact moment via:
   - **Stationary**: Object stops moving (arrow stuck in target)
   - **Velocity change**: Sudden deceleration (ball hitting surface)
   - **Direction change**: Trajectory reversal (ball bouncing)
4. **Report**: Emit PlaneHitEvent with impact coordinates and timestamp

**Object types**:
- **Persistent**: Arrows, darts, throwing knives - remain on target
- **Transient**: Balls, beanbags, foam darts - hit and fall/bounce away

**When to use**: Physical projectile games (archery, darts, ball throwing).

### Why This Matters for Temporal State

The tracking requirement explains why `TemporalGameState` exists:

| Backend | Needs Temporal Queries? | Why |
|---------|------------------------|-----|
| Mouse | No | Instant, click = impact |
| Laser | No | Instantaneous, dot appears at impact location |
| Object | **Yes** | Flight time + detection latency = 300-800ms delay |

For laser/mouse, the game can check "is there a target HERE right NOW?" because detection is instant.

For objects, by the time the impact is detected and reported, the game state has moved on. The game must ask "was there a target HERE at THAT TIME?" - hence temporal queries against state history.

### Adding a New Backend

```python
from ams.detection_backend import DetectionBackend
from ams.events import PlaneHitEvent, CalibrationResult

class MyBackend(DetectionBackend):
    def __init__(self, display_width: int, display_height: int):
        super().__init__(display_width, display_height)
        # Initialize your detection hardware/system

    def poll_events(self) -> List[PlaneHitEvent]:
        """Return new detection events since last poll."""
        events = []
        # Detect impacts, normalize coordinates to [0, 1]
        for detection in self._get_raw_detections():
            norm_x, norm_y = self.normalize_coordinates(
                detection.pixel_x, detection.pixel_y
            )
            events.append(PlaneHitEvent(
                x=norm_x,
                y=norm_y,
                timestamp=detection.timestamp,
                confidence=detection.confidence,
                detection_method=self.__class__.__name__,
            ))
        return events

    def update(self, dt: float):
        """Called each frame to update backend state."""
        pass

    def calibrate(self) -> CalibrationResult:
        """Run calibration for this detection method."""
        # Measure latency, characterize environment, etc.
        return CalibrationResult(success=True, method="my_method")
```

## Architectural Decisions

### ADR-001: Games Don't Know Detection Method

**Decision**: Games receive normalized `PlaneHitEvent(x, y, timestamp)` and never interact directly with detection hardware.

**Rationale**:
- Same game works with mouse (testing), laser (demo), or CV (production)
- Detection improvements don't require game changes
- Enables rapid prototyping with mouse before hardware is ready

**Consequences**:
- All coordinates must be normalized to [0, 1]
- Detection-specific metadata goes in `event.metadata` dict
- Games can't optimize for specific detection characteristics

### ADR-002: Temporal State for Latency Compensation

**Decision**: Provide `TemporalGameState` base class that maintains state history for retroactive hit detection.

**Rationale**:
- Physical projectiles have flight time (200-500ms for arrows)
- Camera detection has latency (50-300ms)
- Display has latency (16-50ms)
- Total: detection event arrives 300-800ms after player action
- Game state has changed; need to query "was there a target HERE at THAT time?"

**Current Status**: `TemporalGameState` is implemented but games haven't been migrated to use it yet. Current games use immediate hit detection which works for mouse/laser but will need temporal queries for CV-based projectile detection.

**Migration path**:
1. Games currently work with immediate detection (mouse, laser)
2. When CV backend is integrated, games will need to:
   - Inherit from `TemporalGameState`
   - Implement `get_current_state_snapshot()`
   - Implement `check_hit_in_snapshot(snapshot, x, y)`
   - Use `was_target_hit(x, y, timestamp)` instead of immediate checks

### ADR-003: Always Recalibrate Between Rounds

**Decision**: Run calibration as interstitial between game rounds, every time.

**Rationale**:
- Lighting changes constantly (sun, clouds, indoor shadows)
- Surface evolves (holes from arrows, wear, moisture)
- Equipment drifts (projector warming, camera auto-adjust)
- Calibration takes 3-6 seconds, feels like "loading"
- Eliminates "detection degraded" failure mode

**Consequences**:
- No need for drift detection heuristics
- Simpler, more robust system
- Users see score screen during calibration (not waiting)

### ADR-004: DuckHunt Separate GameMode (Tech Debt)

**Status**: TECH DEBT - should be migrated

**History**: DuckHunt was developed before `BaseGame` was created. It has its own `GameMode` abstract base class in `games/DuckHunt/game/game_mode.py`.

**Current impact**:
- Registry has fallback logic for DuckHunt
- Inconsistent interface between games
- Harder to write game-agnostic tooling

**Resolution**: Migrate DuckHunt to inherit from `BaseGame`. This requires:
1. Mapping DuckHunt's internal states to `GameState` enum
2. Adding class attributes (NAME, DESCRIPTION, ARGUMENTS)
3. Implementing `_get_internal_state()` method
4. Testing with both `dev_game.py` and `ams_game.py`

### ADR-005: Normalized Coordinates [0, 1]

**Decision**: All coordinates in AMS use normalized [0, 1] range.

**Rationale**:
- Resolution-independent (works at 720p, 1080p, 4K)
- Simpler game logic (no pixel math)
- Portable across display devices
- Easy to reason about (0.5, 0.5 is always center)

**Mapping**:
- `(0, 0)` = top-left
- `(1, 1)` = bottom-right
- Games convert to pixels only for rendering

## File Structure

```
ams/
├── __init__.py
├── events.py                 # PlaneHitEvent, HitResult, CalibrationResult
├── session.py                # AMSSession - main coordinator
├── calibration.py            # Calibration workflow
├── temporal_state.py         # TemporalGameState base class
├── detection_backend.py      # DetectionBackend ABC, InputSourceAdapter
├── laser_detection_backend.py    # Laser pointer detection
├── object_detection_backend.py   # CV-based object detection
├── game_adapter.py           # AMSInputAdapter for game integration
└── camera.py                 # Camera management utilities
```

## Integration Points

### Running Games with AMS

```bash
# Mouse backend (development)
python ams_game.py --game balloonpop --backend mouse

# Laser backend
python ams_game.py --game balloonpop --backend laser --camera 0

# Object detection backend (when ready)
python ams_game.py --game balloonpop --backend object --camera 0
```

### Game Integration via Registry

Games don't need to know about AMS. The registry creates an `AMSInputAdapter` that converts `PlaneHitEvent` to game `InputEvent`:

```python
# In games/registry.py
def create_input_manager(self, slug, ams_session, width, height):
    if ams_session is not None:
        # AMS mode - wrap session in adapter
        from ams.game_adapter import AMSInputAdapter
        source = AMSInputAdapter(ams_session, width, height)
    else:
        # Standalone mode - use mouse directly
        source = MouseInputSource()
    return InputManager(source)
```

## Future Work

### Short Term
- [ ] Migrate DuckHunt to BaseGame
- [ ] Add logging to AMS modules (replace print statements)
- [ ] Write tests for detection backends

### Medium Term
- [ ] Integrate TemporalGameState into games for CV support
- [ ] Improve ObjectDetectionBackend for transient impacts
- [ ] Add calibration quality metrics UI

### Long Term
- [ ] Mobile AR detection backend
- [ ] Multi-player session support
- [ ] Replay/analysis features
