# Arcade Management System (AMS) - Initial Implementation

## Project Context
Building a projection-based interactive gaming system where physical actions (thrown objects, laser pointers, arrows) create coordinate-based input events that drive games. The AMS is the abstraction layer between detection hardware and game logic, enabling games to work across different input methods and deployment platforms without modification.

## Core Philosophy
- **Code is not the asset, the developer is**: Build clean abstractions that enable rapid iteration
- **Always recalibrate between rounds**: Optimize for robustness and speed, not for skipping calibration
- **Games query the past**: Detection reports what happened when; games maintain state history to determine if it was a hit
- **Platform-agnostic from day one**: Same games work with webcam detection, mobile AR, projector setups, or even mouse clicks for testing

## Architecture Overview

The system has three independent layers that communicate through well-defined interfaces:

### 1. Detection Layer
Converts physical events into coordinate-based game events. Examples:
- Webcam CV detecting thrown objects
- Mobile AR tracking + CV
- Laser pointer detection
- Mouse clicks (testing)
- Future: arrow detection, depth sensors, etc.

**Output**: `PlaneHitEvent(x, y, timestamp, metadata)`

### 2. Game Layer (What we're building AMS for)
Receives coordinate events, maintains game state, implements rules and scoring. Games must:
- Maintain 5 seconds of state history for temporal hit queries
- Respond to `was_target_hit(x, y, timestamp)` queries
- Work with available color palette (provided by calibration)
- Render using only colors that detection can reliably distinguish objects against

**Input**: PlaneHitEvents from AMS
**Output**: Game rendering, score updates, session data

### 3. Physical Setup Layer
Platform-specific deployment (Pi + projector, laptop + webcam, mobile app). Handles calibration, power management, hardware specifics.

## AMS Responsibilities

The AMS sits between Detection and Game layers, providing:

### Calibration Management
Run automatically between rounds (invisible to users, ~3-6 seconds):

**Phase 1: Measure Display Latency**
- User presses "ready" button → note timestamp
- Display calibration pattern → camera detects it appearing
- Measure round-trip latency: display → projector → camera → capture
- Store latency for this session

**Phase 2: Background Characterization** (~3 seconds)
- Point camera at empty projection surface
- Cycle through candidate color palette (8-10 colors)
- For each color: project it, capture 5-10 frames, compute statistics (mean, variance)
- Build model: `background_appearance[color] = statistics`
- This captures: ambient lighting, surface texture, projection brightness

**Phase 3: Object Characterization** (~3 seconds)
- "Hold up your projectile in the projection area"
- Cycle through same colors
- Capture object appearance under each projected color
- Build model: `object_appearance[color] = statistics`
- Compute detection matrix: `detection_quality[color] = contrast(object, background)`

**Phase 4: Compute Available Palette**
- Score each color by detection reliability
- Return to game: colors that enable reliable object detection
- Game designs within these constraints (only uses detectable colors)

**Visual Treatment**:
- Calibration integrated into round transitions as "interstitial"
- Color cycling looks like dramatic lighting effect
- Show score summary, countdown timer, "Loading next round..."
- User perceives game transition, not technical calibration
- Calibration grid can flash for 2-3 frames (subliminal) to update coordinate mapping

**Why Always Recalibrate**:
- Lighting changes constantly (sun angle, clouds, indoor shadows)
- Surface evolves (arrow holes, wear, moisture)
- Equipment drifts (projector warming, camera auto-adjust)
- Cost is negligible (few seconds, invisible integration)
- Eliminates entire class of "detection degraded over time" failures
- Simpler than heuristics for detecting when recalibration needed

### Temporal Hit Detection Support
AMS provides the infrastructure for games to handle detection latency:

**For Games (via base framework classes)**:
```python
class TemporalGameState:
    """
    Automatic state history maintenance for hit queries.
    Games inherit this and get temporal queries for free.
    """
    def __init__(self, history_duration=5.0, fps=30):
        self.history = deque(maxlen=int(history_duration * fps))
        self.frame_counter = 0
    
    def update(self):
        """Call each frame - captures state automatically"""
        self.history.append({
            'frame': self.frame_counter,
            'timestamp': time.time(),
            'targets': [t.copy() for t in self.targets],
            # ... other game state
        })
        self.frame_counter += 1
    
    def was_target_hit(self, x, y, frame_or_timestamp):
        """Query: was (x,y) a hit at this point in time?"""
        state = self._get_state_at(frame_or_timestamp)
        for target in state['targets']:
            if target.contains(x, y):
                return HitResult(hit=True, target=target)
        return HitResult(hit=False)
```

**Why Temporal Queries**:
- Display latency varies (50-300ms depending on platform)
- Arrow/projectile flight time is significant (200-500ms)
- Detection happens AFTER game state has advanced
- Game queries its own history to determine if detection corresponds to a hit
- Decouples detection timing from game timing

**Timestamp Embedding (for webview games with high latency)**:
- Game can embed frame counter in projection (border pattern, subtle encoding)
- Camera captures and decodes timestamp
- Ensures detection correlates with correct game frame regardless of variable latency
- Not required for initial implementation, but architecture should allow it

### Session Management
- Initialize calibration data structure
- Store measured latency, background models, object models, palette quality
- Provide session state to games (available colors, detection confidence levels)
- Handle save/load of game progress, scores, player data
- Graceful cleanup on session end

### Event Translation
- Receive raw detection events: (x, y, camera_timestamp, detection_metadata)
- Apply latency correction: actual_time = camera_timestamp - measured_latency  
- Apply coordinate transformation (from calibration homography)
- Emit standardized PlaneHitEvent to game
- Games never see raw detection data, only processed events in game coordinates

## Initial Implementation Scope

### Must Have (Phase 1)
1. **Calibration System**
   - Background characterization (color cycling, statistics capture)
   - Object characterization  
   - Palette quality scoring
   - Fast execution (target: under 10 seconds total)
   - Visual feedback during calibration

2. **TemporalGameState Base Class**
   - Automatic state history maintenance
   - `was_target_hit()` query interface
   - 5-second rolling window
   - Deep copy of game state each frame

3. **Event Pipeline**
   - Accept PlaneHitEvents from detection layer
   - Route to active game
   - Handle game queries about past states

4. **Session Management**
   - Store calibration data
   - Provide palette to games
   - Basic save/load for scores

### Nice to Have (Phase 2)
- Latency measurement using button press + pattern detection
- Timestamp embedding in projection for webview games
- Calibration quality metrics and warnings
- Drift detection and automatic recalibration triggers
- Multi-player session support

### Explicitly Deferred
- Actual detection implementations (CV, AR, etc.) - separate modules
- Specific game implementations - games use the AMS framework
- Mobile app integration - comes later
- Advanced features like replay, slow-motion analysis

## Code Organization
```
/ams
  - calibration.py (background/object characterization, palette scoring)
  - temporal_state.py (TemporalGameState base class)
  - events.py (PlaneHitEvent, HitResult, event routing)
  - session.py (session management, save/load)
  - config.py (calibration parameters, timing constants)
  
/ams/utils
  - color_analysis.py (color statistics, contrast computation)
  - timing.py (latency measurement, timestamp handling)
  - storage.py (persistence for scores, progress)

/games/base
  - game_template.py (base class showing how to use TemporalGameState)
  - primitives.py (Target, Score, basic game components)
```

## Key Design Principles

1. **Clean Abstractions**: Detection, AMS, and Games are independent. Changes to one don't require changes to others.

2. **Fail Visibly**: If calibration can't achieve good detection quality, tell user why and what to fix. Don't silently degrade.

3. **Educational Documentation**: Code should teach systems design principles. Comment why, not just what. Reference design decisions.

4. **Test Without Hardware**: Mock detection events for testing game logic. Games should work with mouse clicks before requiring camera setup.

5. **Platform Portability**: Design works equally well for Python CLI, WASM/browser, or mobile native. Only the detection and display layers change.

## Success Criteria

After this implementation:
- Developer can build a simple game by inheriting TemporalGameState and defining targets
- Game automatically gets temporal hit detection
- Calibration runs quickly and produces reliable palette
- System handles detection events and routes them to games correctly
- Clear documentation shows how to extend with new detection methods
- Code demonstrates professional software architecture patterns

## Technical Notes

- Python 3.10+, use type hints throughout
- Pygame for rendering/display (for initial CLI version)
- OpenCV for calibration pattern detection and color analysis
- Well-commented code explaining design decisions
- Unit tests for core functionality (calibration, temporal queries)
- README with architecture overview and getting started guide

## What We're NOT Building Yet

- Actual CV detection (separate module, different prompt)
- Specific games beyond template (educational projects)
- Mobile app (future work)
- Advanced optimizations (measure first, optimize later)
- Complex UI beyond functional (games provide their own UI)

## Implementation Priority

1. Build TemporalGameState first - this is the core abstraction games depend on
2. Then calibration system - needed for real deployment
3. Then event routing and session management
4. Finally integration testing with mock detection events

Focus on clean abstractions and clear documentation. This becomes the foundation everything else builds on.