# Containment - Implementation Plan

## Overview

Adversarial containment game where a ball/entity tries to escape through gaps at screen edges. Player places deflectors by shooting to build walls and seal escape routes. Direct hits on the ball are penalized (it accelerates). The core mechanic is building geometry to contain, not targeting to destroy.

**Unique Value:** Inverts the standard "hit the target" loop into "hit everywhere except the target while it moves."

---

## Core Mechanics

### Ball Physics

```
State:
  position: Vector2D
  velocity: Vector2D
  radius: float
  speed_multiplier: float (increases on direct hits)

Behavior:
  - Moves continuously, bounces off walls and deflectors
  - Reflection angle based on surface normal
  - Seeks gaps (AI-controlled at higher difficulties)
  - Speed increases permanently when hit directly
```

### Deflectors

```
State:
  position: Vector2D      # Center point where shot landed
  angle: float            # Orientation (could be random, or based on shot direction)
  length: float           # How much wall this deflector provides

Behavior:
  - Placed permanently at shot location
  - Ball reflects off deflector surface
  - Cannot be moved after placement (archery constraint)
  - Optional: can be "retrieved" which removes them (creates vulnerability window)
```

### Gaps

```
State:
  edge: Enum(TOP, BOTTOM, LEFT, RIGHT)
  start: float            # Start position along edge (0-1 normalized)
  width: float            # Gap width
  active: bool            # Whether ball can escape through it

Behavior:
  - Ball escaping through active gap = game over
  - Static gaps at start
  - Dynamic gap spawning at higher difficulties
  - Gaps can be "sealed" by nearby deflectors
```

### Win/Lose Conditions

**Win:**
- Survival mode: Survive for X seconds
- Containment mode: Trap ball in small area (no escape path possible)
- Score mode: Maximize bounces / time / efficiency

**Lose:**
- Ball escapes through any gap

---

## Difficulty System

### Tempo Presets

| Preset | Ball Speed | Gap Count | Gap Width | Ball Count |
|--------|------------|-----------|-----------|------------|
| Zen    | 100 px/s   | 1-2       | 150px     | 1          |
| Mid    | 200 px/s   | 2-3       | 120px     | 1          |
| Wild   | 350 px/s   | 3-4       | 100px     | 1-3        |

### AI Sophistication Levels

**Dumb (Level 1):**
- Pure physics, no decision-making
- Ball bounces predictably
- Good for learning mechanics

**Reactive (Level 2):**
- Ball "notices" gaps and biases toward them
- Avoids dense deflector clusters
- Still exploitable with good placement

**Strategic (Level 3):**
- Tracks player shot patterns
- Baits wasted shots by feinting toward gaps
- Exploits retrieval windows (knows when deflectors removed)
- Avoids "trap" geometries player is building

---

## Game States

```python
class GameState(Enum):
    COUNTDOWN = "countdown"      # Pre-game countdown
    PLAYING = "playing"          # Active gameplay
    RETRIEVAL = "retrieval"      # Paused for arrow retrieval (archery mode)
    ESCAPED = "escaped"          # Ball escaped - loss
    CONTAINED = "contained"      # Ball trapped - win
    TIME_UP = "time_up"          # Survived time limit - win
```

---

## Implementation Phases

### Phase 1: Core Loop (MVP)

**Goal:** Playable game with mouse input, basic physics

Files to create:
- `games/Containment/game_info.py` - Game metadata, CLI args
- `games/Containment/game_mode.py` - Main game class
- `games/Containment/config.py` - Constants and presets
- `games/Containment/ball.py` - Ball entity with physics
- `games/Containment/deflector.py` - Deflector entity
- `games/Containment/gap.py` - Gap management
- `games/Containment/main.py` - Standalone entry point
- `games/Containment/input/` - Input system (copy from existing game)

MVP Features:
- [ ] Ball spawns center, random initial direction
- [ ] Ball bounces off screen edges (except gaps)
- [ ] Click places deflector at position
- [ ] Ball reflects off deflectors
- [ ] Ball escaping through gap = game over
- [ ] Basic HUD: time survived, deflector count, ball speed

### Phase 2: Polish & Difficulty

**Goal:** Tunable difficulty, visual feedback

- [ ] Tempo presets (zen/mid/wild)
- [ ] Speed increase on direct ball hit
- [ ] Visual feedback: ball trail, deflector placement animation
- [ ] Gap visualization (pulsing edges, danger indicators)
- [ ] Sound effects: bounce, place, escape, hit-penalty
- [ ] Score calculation and display

### Phase 3: AI Behavior

**Goal:** Ball becomes adversarial opponent

- [ ] Dumb mode: pure physics (default)
- [ ] Reactive mode: gap-seeking bias
- [ ] Strategic mode: pattern learning, baiting
- [ ] AI difficulty as separate axis from tempo

### Phase 4: Multi-Device Compliance

**Goal:** Full AMS integration

- [ ] Pacing presets for archery/throwing/blaster
- [ ] Quiver support (limited deflectors before retrieval)
- [ ] Retrieval pause state
- [ ] AMS color palette support
- [ ] Test palette cycling (P key)

### Phase 5: Advanced Features

**Goal:** Depth and replayability

- [ ] Multiple balls (Wild mode)
- [ ] Dynamic gap spawning mid-game
- [ ] Deflector types (angled, curved, temporary)
- [ ] Containment win condition (trap detection)
- [ ] Leaderboards / personal bests
- [ ] Theme variants (abstract, sci-fi, playful)

---

## Technical Design

### Ball-Deflector Collision

```python
def check_deflector_collision(ball: Ball, deflector: Deflector) -> Optional[Vector2D]:
    """
    Check if ball collides with deflector line segment.
    Returns reflection normal if collision, None otherwise.
    """
    # Line segment collision with circle
    # Return normal vector for reflection calculation
    pass

def reflect_velocity(velocity: Vector2D, normal: Vector2D) -> Vector2D:
    """Standard reflection: v' = v - 2(v·n)n"""
    dot = velocity.dot(normal)
    return Vector2D(
        velocity.x - 2 * dot * normal.x,
        velocity.y - 2 * dot * normal.y
    )
```

### Direct Hit Detection

```python
def is_direct_hit(ball: Ball, shot_position: Vector2D) -> bool:
    """Check if shot landed on the ball (penalty condition)."""
    distance = ball.position.distance_to(shot_position)
    return distance < ball.radius + HIT_TOLERANCE
```

### Gap Escape Detection

```python
def check_gap_escape(ball: Ball, gaps: List[Gap]) -> bool:
    """Check if ball center has passed through any gap."""
    for gap in gaps:
        if gap.contains_point(ball.position):
            return True
    return False
```

### AI Gap-Seeking (Reactive Mode)

```python
def calculate_gap_bias(ball: Ball, gaps: List[Gap]) -> Vector2D:
    """
    Return velocity adjustment that biases ball toward nearest gap.
    Applied as small force each frame, not teleportation.
    """
    nearest_gap = min(gaps, key=lambda g: g.distance_to(ball.position))
    direction = (nearest_gap.center - ball.position).normalized()
    return direction * GAP_SEEK_STRENGTH
```

---

## CLI Arguments

```python
ARGUMENTS = [
    # Pacing (standard AMS parameter)
    {'name': '--pacing', 'type': str, 'default': 'throwing',
     'help': 'Pacing preset: archery, throwing, blaster'},

    # Game-specific difficulty
    {'name': '--tempo', 'type': str, 'default': 'mid',
     'help': 'Tempo preset: zen, mid, wild (ball aggression)'},
    {'name': '--ai', 'type': str, 'default': 'dumb',
     'help': 'AI level: dumb, reactive, strategic'},

    # Game mode
    {'name': '--time-limit', 'type': int, 'default': 60,
     'help': 'Seconds to survive (0 = endless)'},
    {'name': '--gap-count', 'type': int, 'default': None,
     'help': 'Number of gaps (overrides preset)'},

    # Physical constraints (standard AMS parameters)
    {'name': '--max-deflectors', 'type': int, 'default': None,
     'help': 'Maximum deflectors allowed (None = unlimited)'},
    {'name': '--quiver-size', 'type': int, 'default': None,
     'help': 'Shots before retrieval pause'},
    {'name': '--retrieval-pause', 'type': int, 'default': 30,
     'help': 'Seconds for retrieval (0 = manual)'},

    # Palette (standard AMS parameter)
    {'name': '--palette', 'type': str, 'default': None,
     'help': 'Test palette: full, bw, warm, cool, etc.'},
]
```

**Note:** `--pacing` (device speed) and `--tempo` (game intensity) are independent axes:
- `--pacing archery --tempo zen` = Slow ball, slow shooting - meditative
- `--pacing archery --tempo wild` = Fast ball, slow shooting - intense challenge
- `--pacing blaster --tempo zen` = Slow ball, rapid fire - easy warmup
- `--pacing blaster --tempo wild` = Fast ball, rapid fire - chaos mode

---

## Visual Design

### Color Usage (Palette-Aware)

| Element | Role | Palette Selection |
|---------|------|-------------------|
| Background | Static | Darkest available |
| Ball | Primary target (avoid!) | Brightest / most saturated |
| Deflectors | Player-placed | Secondary bright |
| Gaps | Danger zones | Contrasting (red-ish if available) |
| Walls (sealed) | Safe edges | Muted / dim |
| HUD | Information | UI color from palette |

### Feedback Animations

- **Deflector placed:** Brief flash/pulse at placement point
- **Ball bounce:** Small particle burst at contact
- **Direct hit (penalty):** Screen shake, ball flashes, speed-up indicator
- **Gap approach:** Edge pulses faster as ball gets closer
- **Escape:** Dramatic outward burst, failure state

---

## Open Questions

1. **Deflector shape:** Line segments? Arrow shapes? Circles?
   - Line segments most intuitive for "wall building"
   - Arrow shapes thematic for archery
   - Could be configurable per theme

2. **Deflector orientation:** Random? Based on shot angle? Player-controlled?
   - Random adds chaos/adaptation requirement
   - Shot-angle-based rewards intentional placement
   - Start with random, add control as upgrade?

3. **Retrieval mechanic:** Remove deflectors during retrieval or keep them?
   - Removing creates vulnerability (more tension)
   - Keeping is simpler, less punishing
   - Could be difficulty option

4. **Containment win condition:** How to detect "trapped" state?
   - Ball hasn't moved significantly for X seconds?
   - No path to any gap exists? (computationally expensive)
   - Defer to Phase 5, survival mode sufficient for MVP

---

## Multi-Device Compliance (5 Key Design Questions)

Per `docs/guides/NEW_GAME_QUICKSTART.md`, all games must answer these questions:

### 1. Does timing scale?

**Yes.** Ball speed and gap width scale with pacing preset:

| Pacing | Ball Speed | Gap Width | Notes |
|--------|------------|-----------|-------|
| archery | 80 px/s | 180px | Slow ball, wide gaps - time to aim |
| throwing | 150 px/s | 140px | Medium pace |
| blaster | 280 px/s | 100px | Fast and frantic |

The core loop (observe ball → decide placement → shoot) scales naturally:
- Archery: 3-8 seconds to observe, decide, shoot - ball moves ~240-640px, plenty of time
- Blaster: Sub-second decisions needed - matches device speed

### 2. Is ammo considered?

**Yes.** Deflectors = arrows in archery mode.

- `--quiver-size N` limits deflectors before retrieval pause
- Default: unlimited for mouse/blaster, 6 for archery preset
- Deflector count shown in HUD

**Unique twist:** Unlike other games where ammo limits actions, here limited deflectors force strategic placement. You can't just spam walls everywhere.

### 3. Are pauses handled?

**Yes.** `GameState.RETRIEVAL` pauses ball movement during retrieval.

Options for retrieval behavior:
- **Keep deflectors** (default): Geometry persists, ball frozen, safe
- **Remove deflectors** (hardcore): Your walls disappear, ball resumes into vulnerable field

Retrieval triggered by:
- Quiver empty
- Manual pause (SPACE key)

Retrieval ends by:
- Timer (`--retrieval-pause N` seconds)
- Manual ready (SPACE key if `--retrieval-pause 0`)

### 4. Does combo/streak logic scale?

**N/A for core mechanic.** No combo system - this is a survival/building game, not a hit-streak game.

However, scoring could include:
- **Efficiency bonus:** Fewer deflectors used = higher score multiplier
- **Bounce chains:** Long bounce sequences without escape attempts

These don't require time windows, so no scaling needed.

### 5. Is palette constrained?

**Yes.** Uses `games/common/palette.py` infrastructure.

```python
from games.common.palette import GamePalette

class ContainmentMode:
    def __init__(self, color_palette=None, palette_name=None, **kwargs):
        self._palette = GamePalette(colors=color_palette, palette_name=palette_name)
```

Color assignments:
- Background: `_palette.get_background_color()`
- Ball: `_palette.random_target_color()` (brightest to track visually)
- Deflectors: `_palette.get_ui_color()`
- Gaps: Rendered as absence (background shows through) or pulsing edge indicator

**P key** cycles test palettes in standalone mode.

---

## Pacing Presets (Archery-Compatible)

Using `games/common/pacing.py` infrastructure:

```python
from dataclasses import dataclass

@dataclass
class ContainmentPacing:
    ball_speed: float          # Pixels per second
    gap_width: float           # Gap size in pixels
    gap_count: int             # Number of gaps
    ball_radius: float         # Ball size
    deflector_length: float    # How much wall each deflector provides

PACING_PRESETS = {
    'archery': ContainmentPacing(
        ball_speed=80,
        gap_width=180,
        gap_count=2,
        ball_radius=25,
        deflector_length=80,    # Large deflectors for fewer, strategic placements
    ),
    'throwing': ContainmentPacing(
        ball_speed=150,
        gap_width=140,
        gap_count=3,
        ball_radius=20,
        deflector_length=60,
    ),
    'blaster': ContainmentPacing(
        ball_speed=280,
        gap_width=100,
        gap_count=4,
        ball_radius=15,
        deflector_length=40,    # Smaller deflectors, need more rapid placement
    ),
}
```

**Key insight:** For archery, larger deflectors mean each arrow placement has more impact - you're building significant walls, not spamming small obstacles.

---

## Quiver Integration

Using `games/common/quiver.py` infrastructure:

```python
from games.common.quiver import QuiverState, create_quiver

class ContainmentMode:
    def __init__(self, quiver_size=None, retrieval_pause=30, **kwargs):
        self._quiver = create_quiver(quiver_size, retrieval_pause)

    def handle_input(self, events):
        for event in events:
            if self._quiver and self._quiver.use_shot():
                # Quiver empty - trigger retrieval
                self._start_retrieval()
            self._place_deflector(event.position)

    def _start_retrieval(self):
        self._state = GameState.RETRIEVAL
        self._quiver.start_retrieval()
        # Ball pauses (or continues based on difficulty setting)

    def update(self, dt):
        if self._state == GameState.RETRIEVAL:
            if self._quiver.update_retrieval(dt):
                self._end_retrieval()
            return  # Skip ball update during retrieval
        # Normal update...
```

Default quiver sizes by pacing:
- archery: 6 (matches typical quiver)
- throwing: 12 (larger capacity)
- blaster: None (unlimited)

---

## Success Metrics

- [ ] Core loop feels different from other AMS games (building vs destroying)
- [ ] Zen mode is genuinely meditative
- [ ] Wild mode induces productive panic
- [ ] Direct-hit penalty creates interesting risk/reward tension
- [ ] Emergent geometry creates "happy accident" moments
- [ ] Works well with archery pacing (retrieval windows feel natural)
- [ ] **Passes all 5 Key Design Questions**
- [ ] **Uses shared infrastructure** (palette.py, quiver.py, pacing.py)
