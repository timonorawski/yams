# Multi-Device Compliance Plan

This document tracks the work needed to bring all games into compliance with the multi-device design guidance established in `docs/guides/NEW_GAME_QUICKSTART.md`.

## Reference Implementation

**FruitSlice** serves as the reference implementation for multi-device support:
- Pacing presets (archery/throwing/blaster) bundling all timing parameters
- Quiver mode with configurable shot limits
- Retrieval pauses (timed or manual ready)
- Combo window scaling with device speed

---

## AMS Color Palette Constraint

**Critical for CV detection:** Games must respect the AMS-provided color palette to ensure projectiles can be detected against projected backgrounds.

### The Problem

When using CV-based detection (object detection backend), the system needs to distinguish the projectile from the projected background. If a game uses colors that are too similar to the projectile color, detection fails.

### The Solution

The AMS calibration system (`ams/calibration.py`) determines which colors provide sufficient contrast:

1. **Calibration phases** cycle through candidate colors projecting each onto the surface
2. **Background characterization** captures how each color appears on the projection surface
3. **Object characterization** captures how the projectile appears under each projected color
4. **Palette computation** returns only colors where projectile contrasts sufficiently

### API

```python
# In game initialization (AMS-integrated games)
ams = AMSSession(backend)
result = ams.calibrate()

# Get available colors - games MUST use only these
available_colors = ams.get_available_colors()
# Returns: [(255, 0, 0), (0, 255, 0), ...] or full palette for mouse backend

# Pass to game
game = SomeGame(color_palette=available_colors)
```

### Compliance Matrix (Extended)

| Game | Pacing Presets | Quiver Support | Retrieval Pauses | Scaled Combos | **Palette Aware** | Status |
|------|----------------|----------------|------------------|---------------|-------------------|--------|
| FruitSlice | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ **Complete** |
| Grouping | ✅ N/A | ✅ N/A | ✅ N/A | ✅ N/A | ✅ | ✅ **Complete** |
| ManyTargets | ✅ N/A | ✅ | ✅ | ✅ N/A | ✅ | ✅ **Complete** |
| BalloonPop | ✅ | ✅ | ✅ | ✅ N/A | ✅ | ✅ **Complete** |
| GrowingTargets | ✅ | ✅ | ✅ | ✅ N/A | ✅ | ✅ **Complete** |
| DuckHunt | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ **Complete** |

### Implementation Pattern

Each game needs:

1. **Accept palette in constructor:**
```python
class SomeGameMode:
    def __init__(self, color_palette: List[Tuple[int,int,int]] = None, **kwargs):
        # Default to hardcoded colors if no palette provided (dev mode)
        self.colors = color_palette or DEFAULT_COLORS
```

2. **Use palette for all rendered elements:**
```python
# Target colors
target_color = random.choice(self.colors)

# Background - use darkest available or black
self.background = self._find_darkest(self.colors) or (0, 0, 0)

# UI elements - use brightest available or white
self.ui_color = self._find_brightest(self.colors) or (255, 255, 255)
```

3. **Handle reduced palettes gracefully:**
```python
# If calibration only found 3 usable colors, game still works
# May need to reduce visual variety but gameplay unaffected
```

### Special Cases

- **B/W Mode**: `--bw-palette` flag forces black/white only (maximum contrast)
- **Mouse Backend**: Returns full palette (no restrictions in dev mode)
- **Laser Backend**: Currently ignores palette (laser is bright point, not colored object)
- **Object Backend**: Requires palette compliance for reliable detection

### Standalone Mode: Test Palettes

When games run in standalone/dev mode (`dev_game.py`), they should support cycling through test palettes to verify palette compliance works. This helps catch hardcoded colors before AMS integration.

**Global test palettes** (defined in `games/common/palette.py`):

```python
TEST_PALETTES = {
    'full': [
        (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 0), (255, 0, 255), (0, 255, 255),
        (255, 128, 0), (128, 0, 255),
    ],
    'bw': [
        (0, 0, 0), (255, 255, 255),
    ],
    'warm': [
        (255, 0, 0), (255, 128, 0), (255, 255, 0), (255, 200, 150),
    ],
    'cool': [
        (0, 0, 255), (0, 255, 255), (128, 0, 255), (200, 200, 255),
    ],
    'mono_red': [
        (100, 0, 0), (180, 0, 0), (255, 0, 0), (255, 100, 100),
    ],
    'mono_green': [
        (0, 100, 0), (0, 180, 0), (0, 255, 0), (100, 255, 100),
    ],
    'limited': [
        (255, 255, 255), (255, 0, 0), (0, 0, 255),  # Only 3 colors
    ],
    'orange_dart': [
        # Simulates palette when orange nerf dart is the projectile
        # Orange excluded (too similar to dart)
        (0, 0, 255), (0, 255, 0), (255, 0, 255), (0, 255, 255),
    ],
}
```

**Configuration options:**

```bash
# Via CLI argument
python dev_game.py fruitslice --palette warm

# Via .env file
DEFAULT_PALETTE=orange_dart

# Cycle at runtime (P key)
# Press P to cycle: full → bw → warm → cool → limited → ...
```

**Implementation in standalone main.py:**

```python
# In main loop, handle palette cycling
elif event.key == pygame.K_p:
    # Cycle to next test palette
    palette_names = list(TEST_PALETTES.keys())
    current_idx = palette_names.index(current_palette_name)
    next_idx = (current_idx + 1) % len(palette_names)
    current_palette_name = palette_names[next_idx]
    game.set_palette(TEST_PALETTES[current_palette_name])
    print(f"Switched to palette: {current_palette_name}")
```

This makes it easy to verify games degrade gracefully with restricted palettes before deploying with real CV detection.

---

## Implementation Status

**✅ All games upgraded as of December 2024.**

See the extended compliance matrix above for current status. All 6 games now support:
- AMS color palette integration
- Standalone test palette cycling (P key)
- Pacing presets (where applicable)
- Quiver/retrieval support

Shared infrastructure created in `games/common/`:
- `palette.py` - GamePalette class with TEST_PALETTES
- `quiver.py` - QuiverState class for ammo tracking
- `pacing.py` - Pacing utilities and standard tiers

---

## Game-Specific Plans

### 1. BalloonPop

**Current State:**
- `SPAWN_RATE` configurable (default 1.5s)
- No pacing presets
- No quiver/retrieval support
- No combo system

**Required Changes:**

#### 1.1 Add Pacing Presets to `config.py`

```python
@dataclass
class PacingPreset:
    name: str
    spawn_interval: float      # Seconds between spawns
    float_speed_min: float     # Min rise speed
    float_speed_max: float     # Max rise speed
    max_balloons: int          # Max simultaneous
    balloon_size_min: int      # Smaller = harder
    balloon_size_max: int

PACING_PRESETS = {
    'archery': PacingPreset(
        name='archery',
        spawn_interval=4.0,      # Slow spawning
        float_speed_min=30,      # Slow rise
        float_speed_max=60,
        max_balloons=3,
        balloon_size_min=50,     # Larger targets
        balloon_size_max=90,
    ),
    'throwing': PacingPreset(
        name='throwing',
        spawn_interval=1.5,
        float_speed_min=50,
        float_speed_max=150,
        max_balloons=6,
        balloon_size_min=40,
        balloon_size_max=80,
    ),
    'blaster': PacingPreset(
        name='blaster',
        spawn_interval=0.6,
        float_speed_min=80,
        float_speed_max=200,
        max_balloons=10,
        balloon_size_min=30,
        balloon_size_max=60,
    ),
}
```

#### 1.2 Add CLI Arguments to `game_info.py`

```python
ARGUMENTS = [
    # Existing...
    {'name': '--pacing', 'type': str, 'default': 'throwing',
     'help': 'Pacing preset: archery, throwing, blaster'},
    {'name': '--quiver-size', 'type': int, 'default': None,
     'help': 'Shots per round (None = unlimited)'},
    {'name': '--retrieval-pause', 'type': int, 'default': 30,
     'help': 'Seconds for retrieval (0 = manual ready)'},
]
```

#### 1.3 Add Quiver State to `game_mode.py`

- Track `shots_remaining` and `current_round`
- Add `RETRIEVAL` game state
- Pause spawning during retrieval
- Resume on timer or spacebar

**Estimated Scope:** Medium - ~100 lines config, ~50 lines game logic

---

### 2. GrowingTargets

**Current State:**
- `--spawn-rate` and `--growth-rate` configurable
- Defaults too fast for archery (1.5s spawn, 40px/s growth)
- No quiver/retrieval support

**Required Changes:**

#### 2.1 Add Pacing Presets to `config.py`

```python
@dataclass
class PacingPreset:
    name: str
    spawn_interval: float
    growth_rate: float         # Slower = more time to aim
    max_targets: int
    start_size: int
    max_size: int              # Larger max = longer window

PACING_PRESETS = {
    'archery': PacingPreset(
        name='archery',
        spawn_interval=5.0,
        growth_rate=15.0,       # Very slow growth
        max_targets=2,
        start_size=15,
        max_size=150,          # Long growth window
    ),
    'throwing': PacingPreset(
        name='throwing',
        spawn_interval=1.5,
        growth_rate=40.0,
        max_targets=5,
        start_size=10,
        max_size=120,
    ),
    'blaster': PacingPreset(
        name='blaster',
        spawn_interval=0.5,
        growth_rate=80.0,       # Fast growth
        max_targets=8,
        start_size=8,
        max_size=100,
    ),
}
```

#### 2.2 Add CLI Arguments

```python
ARGUMENTS = [
    # Existing...
    {'name': '--pacing', 'type': str, 'default': 'throwing',
     'help': 'Pacing preset: archery, throwing, blaster'},
    {'name': '--quiver-size', 'type': int, 'default': None,
     'help': 'Shots per round (None = unlimited)'},
    {'name': '--retrieval-pause', 'type': int, 'default': 30,
     'help': 'Seconds for retrieval (0 = manual ready)'},
]
```

#### 2.3 Add Quiver/Retrieval State

Same pattern as FruitSlice - track shots, pause spawning/growth during retrieval.

**Estimated Scope:** Medium - ~80 lines config, ~50 lines game logic

---

### 3. DuckHunt

**Current State:**
- YAML-based mode configs with some timing parameters
- `classic_archery.yaml` exists but timing not fully scaled
- Combo multiplier hardcoded at 1.5x, threshold at 3 hits
- No quiver support

**Required Changes:**

#### 3.1 Extend Mode YAML Schema

Add pacing section to mode configs:

```yaml
# modes/classic_archery.yaml
pacing:
  spawn_interval: 4.0
  target_lifetime: 8.0
  max_active: 2
  combo_window: 8.0
  combo_threshold: 2    # Fewer hits needed for slow devices

# modes/classic_blaster.yaml
pacing:
  spawn_interval: 0.8
  target_lifetime: 3.0
  max_active: 8
  combo_window: 1.5
  combo_threshold: 5
```

#### 3.2 Add CLI Pacing Override

```python
ARGUMENTS = [
    {'name': '--mode', ...},  # Existing
    {'name': '--pacing', 'type': str, 'default': None,
     'help': 'Override mode timing: archery, throwing, blaster'},
    {'name': '--quiver-size', 'type': int, 'default': None,
     'help': 'Shots per round (None = unlimited)'},
    {'name': '--retrieval-pause', 'type': int, 'default': 30,
     'help': 'Seconds for retrieval (0 = manual ready)'},
]
```

#### 3.3 Update Mode Loader

- Parse pacing section from YAML
- Apply combo window/threshold from pacing
- Support CLI override of mode pacing

#### 3.4 Add Quiver/Retrieval State

- Track shots in ClassicMode
- Add retrieval state between rounds
- Pause duck spawning during retrieval

**Estimated Scope:** Large - YAML schema changes, loader updates, ~100 lines game logic

---

### 4. ManyTargets

**Current State:**
- Static targets (no spawning) - inherently works for slow devices
- Optional `--timed` mode doesn't pause for retrieval
- No quiver needed (field-clearing, not continuous)

**Required Changes:**

#### 4.1 Add Pause Support for Timed Mode

When quiver empties in timed mode:
- Pause the timer
- Show retrieval screen
- Resume timer when ready

```python
# In game_mode.py
class GameState(Enum):
    PLAYING = auto()
    RETRIEVAL = auto()  # New
    GAME_OVER = auto()
    VICTORY = auto()

# Pause timer during RETRIEVAL state
def update(self, dt):
    if self.state == GameState.PLAYING:
        if self.time_limit:
            self.time_remaining -= dt
```

#### 4.2 Add Optional Quiver Arguments

```python
ARGUMENTS = [
    # Existing...
    {'name': '--quiver-size', 'type': int, 'default': None,
     'help': 'Shots before retrieval pause (None = unlimited)'},
    {'name': '--retrieval-pause', 'type': int, 'default': 30,
     'help': 'Seconds for retrieval (0 = manual ready)'},
]
```

**Estimated Scope:** Small - ~40 lines for pause/resume logic

---

## Implementation Order

Recommended order based on complexity and user value:

1. **ManyTargets** (Small) - Just add pause support for timed mode
2. **GrowingTargets** (Medium) - Add pacing presets, quiver mode
3. **BalloonPop** (Medium) - Add pacing presets, quiver mode
4. **DuckHunt** (Large) - YAML schema extension, loader changes, quiver mode

## Shared Code Opportunities

Consider extracting common patterns to `games/common/`:

### `games/common/palette.py`
```python
from typing import List, Tuple, Optional

# Default palette when no AMS constraints (dev mode)
DEFAULT_PALETTE = [
    (255, 0, 0),     # Red
    (0, 255, 0),     # Green
    (0, 0, 255),     # Blue
    (255, 255, 0),   # Yellow
    (255, 0, 255),   # Magenta
    (0, 255, 255),   # Cyan
    (255, 128, 0),   # Orange
    (128, 0, 255),   # Purple
]

BW_PALETTE = [(0, 0, 0), (255, 255, 255)]


class GamePalette:
    """Manages color palette with AMS constraint support."""

    def __init__(self, colors: List[Tuple[int,int,int]] = None, bw_mode: bool = False):
        if bw_mode:
            self.colors = BW_PALETTE.copy()
        else:
            self.colors = colors or DEFAULT_PALETTE.copy()

    def get_target_colors(self, count: int = None) -> List[Tuple[int,int,int]]:
        """Get colors suitable for targets."""
        # Exclude very dark colors (hard to see)
        bright = [c for c in self.colors if sum(c) > 200]
        if count:
            return bright[:count]
        return bright

    def get_background_color(self) -> Tuple[int,int,int]:
        """Get darkest color for background."""
        return min(self.colors, key=lambda c: sum(c))

    def get_ui_color(self) -> Tuple[int,int,int]:
        """Get brightest color for UI text."""
        return max(self.colors, key=lambda c: sum(c))

    def random_target_color(self) -> Tuple[int,int,int]:
        """Get random color for a new target."""
        import random
        return random.choice(self.get_target_colors())
```

### `games/common/pacing.py`
```python
@dataclass
class BasePacingPreset:
    name: str
    spawn_interval: float
    combo_window: float

def get_pacing_preset(presets: dict, name: str, default: str = 'throwing'):
    """Get preset by name with fallback."""
    return presets.get(name, presets[default])
```

### `games/common/quiver.py`
```python
@dataclass
class QuiverState:
    size: int              # 0 = unlimited
    remaining: int
    retrieval_pause: int   # seconds, 0 = manual
    retrieval_timer: float

    def use_shot(self) -> bool:
        """Use a shot. Returns True if quiver now empty."""
        if self.size == 0:
            return False
        self.remaining -= 1
        return self.remaining <= 0

    def start_retrieval(self):
        self.retrieval_timer = float(self.retrieval_pause)

    def update_retrieval(self, dt) -> bool:
        """Update retrieval timer. Returns True when complete."""
        if self.retrieval_pause == 0:
            return False  # Manual mode
        self.retrieval_timer -= dt
        return self.retrieval_timer <= 0

    def refill(self):
        self.remaining = self.size
```

This could reduce per-game quiver implementation to ~10 lines.

## Testing Checklist

For each updated game, verify:

**Pacing:**
- [ ] `--pacing archery` gives 5+ seconds between required actions
- [ ] `--pacing blaster` maintains fast-paced gameplay
- [ ] Combo/streak mechanics work at archery speed (8s+ windows)

**Quiver/Retrieval:**
- [ ] `--quiver-size 6` triggers retrieval after 6 shots
- [ ] `--retrieval-pause 0` waits for spacebar
- [ ] `--retrieval-pause 30` auto-resumes after 30s
- [ ] Game doesn't end during retrieval pause
- [ ] Score/state preserved across retrieval

**Palette Compliance:**
- [ ] Game accepts `color_palette` parameter in constructor
- [ ] All targets/elements use only palette colors
- [ ] Game works with reduced palette (3 colors)
- [ ] Game works with B/W palette (2 colors)
- [ ] No hardcoded colors bypass palette constraint

## Success Criteria

All games pass the **5 Key Design Questions**:

1. ✅ **Does timing scale?** Pacing presets for all timed games
2. ✅ **Is ammo considered?** Quiver support where applicable
3. ✅ **Are pauses handled?** Retrieval state doesn't end game
4. ✅ **Does combo/streak scale?** Windows adjust with pacing
5. ✅ **Is palette constrained?** Games accept AMS color palette and render only those colors
