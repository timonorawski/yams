# YAMS Future Improvements

This document captures planned improvements and design ideas for the YAML Arcade Management System (YAMS).

## 1. Game Modality Declarations

### Problem

Games are designed to be adaptive to constraints (palette, pacing, quiver size). However, some games may not be able to support all input configurations:

- A game might require instantaneous feedback (laser only)
- A game might need object tracking for physics simulation
- A game might be mouse-only for development/testing
- A game might work with transient impacts (balls, foam arrows) but not persistent projectiles (arrows, darts that stay on screen)
- A game's visuals might be obscured by stuck projectiles

Currently, AMS presents all games regardless of whether they work with the active configuration.

### Solution: Modalities with Modifiers

Modality declarations need two dimensions:
1. **Detection backend**: How hits are detected (mouse, laser, object)
2. **Projectile persistence**: Whether projectiles remain on screen after impact

```python
class MyGame(BaseGame):
    NAME = "My Game"

    # Simple form: list of supported backends (assumes both transient and persistent OK)
    SUPPORTED_MODALITIES = ['mouse', 'laser', 'object']

    # Explicit form: dict with persistence modifiers
    SUPPORTED_MODALITIES = {
        'mouse': ['transient'],           # Mouse clicks are always transient
        'laser': ['transient'],            # Laser is always transient
        'object': ['transient', 'persistent'],  # Supports both
    }

    # Game that can't handle persistent projectiles obscuring targets
    SUPPORTED_MODALITIES = {
        'mouse': ['transient'],
        'laser': ['transient'],
        'object': ['transient'],  # Balls OK, arrows/darts NOT OK
    }
```

### Modality Definitions

**Detection Backends:**

| Backend | Class | Detection Type | Latency |
|---------|-------|----------------|---------|
| `mouse` | InputSourceAdapter | Immediate clicks | ~0ms |
| `laser` | LaserDetectionBackend | Instantaneous, untracked | ~50ms |
| `object` | ObjectDetectionBackend | Tracked to impact | ~100-500ms |

**Persistence Modifiers:**

| Modifier | Examples | Characteristics |
|----------|----------|-----------------|
| `transient` | Balls, foam arrows, beanbags, snowballs | Hit and bounce/fall away, screen stays clear |
| `persistent` | Real arrows, darts, throwing knives, axes | Stick to surface, accumulate on screen |

### Why Persistence Matters

Some games are incompatible with persistent projectiles:

- **Visual occlusion**: Targets get covered by accumulated arrows/darts
- **Detection interference**: Stuck projectiles confuse object detection
- **Gameplay design**: Game assumes clear screen between rounds

Examples:
- **FruitSlice**: Works with persistent (fruit positions avoid projectiles) ✓
- **ManyTargets**: Small targets get obscured by arrows ✗
- **BalloonPop**: Large targets, usually OK ✓
- **Containment**: Ball physics game, transient-only by design ✗

### AMS Integration

```python
@dataclass
class ActiveModality:
    """Current AMS input configuration."""
    backend: str  # 'mouse', 'laser', 'object'
    persistence: str  # 'transient', 'persistent'

def get_available_games(modality: ActiveModality) -> List[Type[BaseGame]]:
    """Return only games compatible with current modality."""
    compatible = []
    for game in all_games:
        supported = game.SUPPORTED_MODALITIES

        # Handle simple list form (legacy, assumes all persistence OK)
        if isinstance(supported, list):
            if modality.backend in supported:
                compatible.append(game)
            continue

        # Handle dict form with persistence modifiers
        if modality.backend in supported:
            if modality.persistence in supported[modality.backend]:
                compatible.append(game)

    return compatible
```

### Configuration Examples

```python
# Ball throwing setup
modality = ActiveModality(backend='object', persistence='transient')
# Shows: All games that support object detection with transient projectiles

# Archery setup
modality = ActiveModality(backend='object', persistence='persistent')
# Shows: Only games that can handle arrows staying on screen

# Laser pointer demo
modality = ActiveModality(backend='laser', persistence='transient')
# Shows: All games (laser is always transient)
```

### Default Behavior

- Games without `SUPPORTED_MODALITIES` default to all backends, all persistence modes
- Simple list form assumes both `transient` and `persistent` are OK
- Allows gradual adoption without breaking existing games

---

## 2. AMS Game Chooser Interface

### Problem

Currently, game selection happens via command line (`--game balloonpop`). For arcade/demo deployments, we need an in-game selection interface.

### Solution: Shoot-to-Select Interface

1. **Display**: Show game tiles arranged in a grid
2. **Selection**: Player shoots a tile to select that game
3. **Confirmation**: Brief pause to allow player to clear/ready
4. **Launch**: Selected game starts

### Design

```
┌─────────────────────────────────────────┐
│           SELECT A GAME                 │
│                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ Balloon │  │  Duck   │  │  Fruit  │  │
│  │   Pop   │  │  Hunt   │  │  Slice  │  │
│  └─────────┘  └─────────┘  └─────────┘  │
│                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ Growing │  │  Many   │  │Grouping │  │
│  │ Targets │  │ Targets │  │         │  │
│  └─────────┘  └─────────┘  └─────────┘  │
│                                         │
│         Shoot a tile to select          │
└─────────────────────────────────────────┘
```

### Implementation Considerations

- Tiles should be large enough for reliable detection
- Show only games compatible with current backend (see Modality Declarations)
- Visual feedback on hit (tile highlight, sound)
- Configurable delay before launch (default: 2-3 seconds)
- Option to show game preview/description on hover/near-miss

### Game Chooser as Special "Game"

The chooser could be implemented as a special BaseGame subclass:

```python
class GameChooser(BaseGame):
    """Meta-game that presents game selection interface."""
    NAME = "Game Chooser"
    SUPPORTED_MODALITIES = ['mouse', 'laser', 'object']

    def __init__(self, available_games: List[Type[BaseGame]], ...):
        self.games = available_games
        self.selected_game = None

    def handle_hit(self, event: PlaneHitEvent):
        # Check which tile was hit
        for tile in self.tiles:
            if tile.contains(event.x, event.y):
                self.selected_game = tile.game_class
                self.state = GameState.GAME_OVER  # Signal completion
```

---

## 3. Inter-Level AMS Callbacks

### Problem

Games currently run autonomously without opportunities for AMS to:
- Run calibration wipes between levels
- Verify hit accuracy
- Collect performance metrics
- Adjust detection parameters

### Solution: Level Transition Hooks

Games call back to AMS (or dev mode shim) at level boundaries:

```python
class BaseGame:
    def __init__(self, ams_session: Optional[AMSSession] = None):
        self.ams = ams_session

    def on_level_complete(self):
        """Called when player completes a level."""
        if self.ams:
            # Request AMS interstitial
            self.ams.on_level_transition(
                game=self,
                completed_level=self.current_level,
                next_level=self.current_level + 1,
                request_calibration=True,  # Optional
                request_accuracy_check=False,  # Optional
            )
        else:
            # Dev mode: show simple interstitial
            self._show_dev_interstitial()
```

### AMS Session Interface

```python
class AMSSession:
    def on_level_transition(
        self,
        game: BaseGame,
        completed_level: int,
        next_level: int,
        request_calibration: bool = False,
        request_accuracy_check: bool = False,
    ) -> LevelTransitionResult:
        """Handle level transition with optional calibration."""

        # Show level complete screen
        self._show_level_summary(game, completed_level)

        if request_calibration:
            # Run quick calibration wipe
            self.calibration_session.run_calibration(quick_mode=True)

        if request_accuracy_check:
            # Run accuracy verification (see section 4)
            self._run_accuracy_check()

        # Return result to game
        return LevelTransitionResult(
            continue_game=True,
            calibration_updated=request_calibration,
            accuracy_metrics=...,
        )
```

### Dev Mode Shim

For development without full AMS:

```python
class DevModeAMSShim:
    """Minimal AMS shim for development/testing."""

    def on_level_transition(self, game, completed_level, next_level, **kwargs):
        # Show simple "Level Complete" overlay
        # Wait for keypress or timeout
        # Return default result
        return LevelTransitionResult(continue_game=True)
```

---

## 4. Hit Accuracy Verification

### Problem

Detection accuracy can drift due to:
- Projector/camera thermal drift
- Surface changes (arrows accumulating, lighting changes)
- Calibration quality degradation

We need a way to verify and correct hit detection accuracy.

### Solution: Gradient Display Method

Display a 2D gradient pattern that encodes position in color:

```
┌─────────────────────────────────────────┐
│ Accuracy Check: Hit anywhere on screen  │
│                                         │
│  ░░░▒▒▒▓▓▓███████▓▓▓▒▒▒░░░              │
│  ░░░▒▒▒▓▓▓███████▓▓▓▒▒▒░░░              │
│  ▒▒▒▓▓▓███████████▓▓▓▒▒▒              │
│  ▓▓▓███████████████████▓▓▓              │
│  ███████████████████████████            │
│  ▓▓▓███████████████████▓▓▓              │
│  ▒▒▒▓▓▓███████████▓▓▓▒▒▒              │
│  ░░░▒▒▒▓▓▓███████▓▓▓▒▒▒░░░              │
│                                         │
└─────────────────────────────────────────┘
```

### Gradient Encoding

```python
def encode_position_as_color(x: float, y: float) -> Tuple[int, int, int]:
    """Encode normalized [0,1] position as RGB color."""
    # X position → Red channel
    # Y position → Green channel
    # Blue channel for additional precision or checksum
    r = int(x * 255)
    g = int(y * 255)
    b = (r + g) % 256  # Simple checksum
    return (r, g, b)

def decode_color_to_position(r: int, g: int, b: int) -> Tuple[float, float]:
    """Decode RGB color back to normalized position."""
    x = r / 255.0
    y = g / 255.0
    return (x, y)
```

### Verification Flow

1. **Display gradient**: Project position-encoded gradient
2. **Request hit**: Player hits anywhere on the gradient
3. **Detect hit**: Backend reports detected position `(det_x, det_y)`
4. **Sample color**: Camera captures color at detected position
5. **Decode true position**: Convert sampled RGB to `(true_x, true_y)`
6. **Compute error**: `error = distance(detected, true)`
7. **Calibration decision**: If error > threshold, trigger recalibration

### Multiple Hit Verification

For higher confidence, request multiple hits across the surface:

```python
def run_accuracy_check(self, num_samples: int = 5) -> AccuracyResult:
    """Verify hit accuracy with multiple samples."""
    errors = []

    for i in range(num_samples):
        # Show gradient with target zone
        self._display_gradient_with_target(zone=i)

        # Wait for hit
        hit = self._wait_for_hit()

        # Compare detected vs true position
        true_pos = self._sample_gradient_at(hit.x, hit.y)
        error = self._compute_error(hit, true_pos)
        errors.append(error)

    return AccuracyResult(
        mean_error=np.mean(errors),
        max_error=np.max(errors),
        samples=errors,
        needs_recalibration=np.max(errors) > self.RECAL_THRESHOLD,
    )
```

### Applications

- **Per-session calibration check**: Quick sanity check at session start
- **Between-level verification**: Catch drift during play
- **Diagnostic mode**: Detailed accuracy mapping for troubleshooting
- **Automatic recalibration trigger**: System detects when accuracy degrades

### Gradient Test Game

The gradient display naturally extends into a diagnostic "game" for validating the entire CV pipeline:

```python
class GradientTestGame(BaseGame):
    """
    Diagnostic game for validating AMS detection accuracy.

    Projects a persistent position-encoded gradient. Each hit:
    1. Draws a marker at the detected position
    2. Samples the gradient color at that position
    3. Computes and displays the error
    4. Accumulates statistics over the session
    """
    NAME = "Gradient Test"
    DESCRIPTION = "CV pipeline validation - hit anywhere, see accuracy"
    SUPPORTED_MODALITIES = {
        'mouse': ['transient'],
        'laser': ['transient'],
        'object': ['transient', 'persistent'],
    }
```

**Display:**

```
┌─────────────────────────────────────────┐
│  GRADIENT TEST        Hits: 12          │
│                       Mean error: 1.2%  │
│                       Max error: 3.1%   │
│                                         │
│  ░░░▒▒▒▓▓▓███████▓▓▓▒▒▒░░░              │
│  ░░░▒▒▒▓▓▓████X██▓▓▓▒▒▒░░░   ← marker  │
│  ▒▒▒▓▓▓█████X█████▓▓▓▒▒▒              │
│  ▓▓▓██████X███████████▓▓▓              │
│  ███████████████████████████            │
│                                         │
│  Last hit: detected (0.52, 0.31)        │
│            actual   (0.51, 0.30)        │
│            error    1.4%                │
└─────────────────────────────────────────┘
```

**Use cases:**

- **Setup validation**: Verify AMS is working before running real games
- **Troubleshooting**: Visualize where detection errors occur (edges? center? specific regions?)
- **Calibration tuning**: See real-time impact of calibration parameter changes
- **Hardware comparison**: Quantify accuracy differences between cameras, lighting setups
- **Regression testing**: Verify CV code changes don't degrade accuracy

**Implementation notes:**

- Markers persist on screen (don't clear between hits)
- Color-code markers by error magnitude (green=good, yellow=warning, red=bad)
- Optional heatmap mode showing error distribution across screen
- Export session data for analysis

---

## 5. Implementation Priority

### Phase 1: Foundation (Next)
1. Add `SUPPORTED_MODALITIES` to BaseGame
2. Update registry to filter by modality
3. Add dev mode shim for level transitions

### Phase 2: Game Chooser
1. Implement GameChooser as special game
2. Wire into ams_game.py as default when no `--game` specified
3. Add visual polish (animations, sounds)

### Phase 3: Calibration Integration
1. Implement `on_level_transition` in AMSSession
2. Add quick calibration mode
3. Integrate gradient-based accuracy check

### Phase 4: Production Polish
1. Accuracy check automation
2. Drift detection and alerts
3. Session metrics and logging

---

## 6. Open Questions

1. **Additional modifiers?**: Beyond `transient`/`persistent`, are there other relevant modifiers?
   - `single` vs `multi`: Single projectile at a time vs multiple simultaneous?
   - `precision` vs `area`: Point impacts vs area effects (shotgun spread)?
   - `timed` vs `unlimited`: Games that need retrieval pauses vs continuous play?

2. **Game chooser return**: How does player return to chooser after game ends? Timeout? Special hit zone?

3. **Calibration timing**: How long is acceptable for between-level calibration? Current: 3-6 seconds.

4. **Accuracy threshold**: What error (in normalized coords) triggers recalibration? Initial guess: 0.02 (2% of screen).

5. **Gradient visibility**: Will gradient pattern work for all detection methods? Laser may struggle with subtle color differences.

6. **Persistence detection**: How does AMS know if current setup uses persistent or transient projectiles? Manual config? Auto-detect from camera?

---

## 7. Future: Touch/Mobile Platform

### Concept

The game architecture is input-agnostic - games receive normalized `(x, y)` hit events regardless of source. This means games could run on touch devices (iOS, Android) with minimal changes.

### Touch as a Backend

```python
class TouchInputBackend(DetectionBackend):
    """Touch events as hit detection - for mobile platforms."""

    def poll_events(self) -> List[PlaneHitEvent]:
        # Kivy/mobile touch events are already normalized [0,1]
        # Convert touch down/up to PlaneHitEvents
        pass
```

### Technology: Kivy

[Kivy](https://kivy.org/) is a natural fit:

- **Cross-platform**: Same Python codebase on iOS, Android, desktop
- **Touch-native**: Designed for multi-touch from the start
- **Python**: Existing game logic ports directly
- **Graphics**: OpenGL ES backend for 2D rendering

### Modality Characteristics

| Property | Touch |
|----------|-------|
| Persistence | `transient` (always) |
| Latency | ~0ms (immediate) |
| Multi-input | Yes (multi-touch possible) |
| Precision | High (finger size ~7mm) |
| Retrieval | None needed |

### Games Well-Suited for Touch

- **BalloonPop**: Tap to pop
- **GrowingTargets**: Tap timing challenge
- **ManyTargets**: Rapid tapping
- **Grouping**: Tap sequences
- **FruitSlice**: Could support swipe gestures (extended input model)

### Considerations

- **Pacing**: Touch needs fastest preset (near-instant reaction possible)
- **Multi-touch**: Opens new gameplay - simultaneous taps, two-finger gestures
- **Screen size**: Games need to scale to phone/tablet dimensions
- **No calibration**: Touch coordinates are inherently accurate
- **Gesture extension**: Swipes, holds, pinches could extend beyond point hits

### Not a Current Priority

This is documented for future reference. The projection-based AMS is the primary focus. Touch/mobile would be a separate product using the same game library.

---

## Related Documents

- [AMS Architecture](../architecture/AMS_ARCHITECTURE.md) - Current system design
- [Tech Debt](../TECH_DEBT.md) - Known issues to address
- [AMS Developer Guide](../guides/AMS_DEVELOPER_GUIDE.md) - Development patterns
- [Multi-Device Compliance](MULTI_DEVICE_COMPLIANCE.md) - Input device considerations
