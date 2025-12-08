# Containment - Implementation Plan

## Overview

Adversarial containment game where a ball/entity tries to escape through gaps at screen edges. Player places deflectors by shooting to build walls and seal escape routes. Direct hits on the ball are penalized (it accelerates). The core mechanic is building geometry to contain, not targeting to destroy.

**Unique Value:** Inverts the standard "hit the target" loop into "hit everywhere except the target while it moves."

---

## Implementation Status (December 2024)

### Implemented

- [x] **Classic Mode**: Static walls with gaps, survive time limit
- [x] **Dynamic Mode**: Rotating spinner obstacles, no escape gaps
- [x] Ball physics with bounce and speed penalty on direct hit
- [x] Deflector placement (random angle at hit position)
- [x] Collision detection with penetration depth and push-out (fixes ball sticking)
- [x] Spinner obstacles (triangle, square, pentagon, hexagon) with rotation
- [x] Tempo presets (zen/mid/wild)
- [x] Pacing presets (archery/throwing/blaster)
- [x] Palette support
- [x] Quiver/retrieval support
- [x] HUD showing mode, time, bounces, deflector count
- [x] **YAML Level Loader** with full schema support
- [x] **All Hit Modes**: deflector, spinner, point, connect, morph, grow
- [x] **Hit Mode Selection**: random, sequential, weighted
- [x] **Level Chooser UI**: Tile-based level selection (`--choose-level`)

### CLI Flags

```bash
# Classic mode (default)
python dev_game.py containment --mode classic --tempo mid

# Dynamic mode with spinners
python dev_game.py containment --mode dynamic --spinner-count 3

# Tempo variants
python dev_game.py containment --tempo zen    # Slow, meditative
python dev_game.py containment --tempo wild   # Fast, chaotic

# Endless mode
python dev_game.py containment --time-limit 0

# Level chooser UI
python dev_game.py containment --choose-level

# Load a specific level file
python dev_game.py containment --level all_hit_modes
python dev_game.py containment --level connect_the_dots
python dev_game.py containment --level mixed_hits
```

### Not Yet Implemented

- [ ] Capture zone win condition
- [ ] Ball AI (reactive/strategic modes)
- [ ] Bouncing bomb hazards
- [ ] Multiplayer modes

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

Uses standard `GameState` enum from `games/common/game_state.py`:

```python
class GameState(Enum):
    PLAYING = "playing"          # Active gameplay
    PAUSED = "paused"            # Manual pause
    RETRIEVAL = "retrieval"      # Paused for arrow retrieval (archery mode)
    GAME_OVER = "game_over"      # Ball escaped - loss
    WON = "won"                  # Survived time limit - win
```

Internal game logic maps specific conditions to standard states:
- Ball escapes through gap → `GAME_OVER`
- Time limit reached → `WON`
- Quiver empty → `RETRIEVAL`

---

## Implementation Phases

### Phase 1: Core Loop (MVP) ✓ COMPLETE

**Goal:** Playable game with mouse input, basic physics

Files created:
- `games/Containment/game_info.py` - Game metadata, CLI args
- `games/Containment/game_mode.py` - Main game class (inherits BaseGame)
- `games/Containment/config.py` - Constants and presets
- `games/Containment/ball.py` - Ball entity with physics
- `games/Containment/deflector.py` - Deflector entity
- `games/Containment/gap.py` - Gap management
- `games/Containment/spinner.py` - Rotating polygon obstacles (dynamic mode)

MVP Features:
- [x] Ball spawns center, random initial direction
- [x] Ball bounces off screen edges (except gaps in classic mode)
- [x] Click places deflector at position (random angle)
- [x] Ball reflects off deflectors with proper push-out
- [x] Ball escaping through gap = game over (classic mode)
- [x] Basic HUD: time survived, deflector count, ball speed, bounce count

### Phase 2: Polish & Difficulty ✓ MOSTLY COMPLETE

**Goal:** Tunable difficulty, visual feedback

- [x] Tempo presets (zen/mid/wild)
- [x] Speed increase on direct ball hit
- [ ] Visual feedback: ball trail, deflector placement animation
- [ ] Gap visualization (pulsing edges, danger indicators)
- [ ] Sound effects: bounce, place, escape, hit-penalty
- [x] Score calculation and display (time survived)

### Phase 3: Dynamic Mode ✓ COMPLETE (new phase)

**Goal:** Address "too easy/static" feedback

- [x] `--mode dynamic` flag
- [x] Spinner class: rotating polygon obstacles
- [x] Multiple spinner shapes (triangle, square, pentagon, hexagon)
- [x] Configurable rotation speed and direction
- [x] SpinnerManager with default layout generation
- [x] Ball bounces off all screen edges (no escape in dynamic mode)
- [x] `--spinner-count N` flag

### Phase 4: AI Behavior (NOT STARTED)

**Goal:** Ball becomes adversarial opponent

- [x] Dumb mode: pure physics (default) - implemented
- [ ] Reactive mode: gap-seeking bias
- [ ] Strategic mode: pattern learning, baiting
- [ ] AI difficulty as separate axis from tempo

### Phase 5: Multi-Device Compliance ✓ COMPLETE

**Goal:** Full AMS integration

- [x] Pacing presets for archery/throwing/blaster
- [x] Quiver support (limited deflectors before retrieval)
- [x] Retrieval pause state
- [x] AMS color palette support
- [x] Test palette cycling (P key)

### Phase 6: Level System & Hit Modes ✓ COMPLETE

**Goal:** Data-driven levels, flexible hit mechanics

- [x] YAML level loader (`games/Containment/levels/level_loader.py`)
- [x] Level schema documentation (`games/Containment/levels/schema.md`)
- [x] Example levels (classic_mode, dynamic_mode, mixed_hits, sequential_builder, all_hit_modes)
- [x] `--level` CLI flag
- [x] Hit mode: **deflector** - Basic wall segment
- [x] Hit mode: **spinner** - Player-spawned rotating polygon
- [x] Hit mode: **point** - Simple circular obstacle
- [x] Hit mode: **connect** - Connect-the-dots wall building
- [x] Hit mode: **morph** - Shape-changing obstacle with pulsation
- [x] Hit mode: **grow** - Circular obstacle that grows when hit again
- [x] Hit mode selection: random, sequential, weighted

### Phase 7: Advanced Features (NOT STARTED)

**Goal:** Depth and replayability

- [ ] Capture zone win condition (pinball mode)
- [ ] Multiple balls (Wild mode)
- [ ] Bouncing bomb hazards
- [ ] Ball AI (reactive/strategic modes)
- [ ] Containment win condition (trap detection)
- [ ] Leaderboards / personal bests

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

## CLI Arguments (Current Implementation)

```python
ARGUMENTS = [
    # Pacing (standard AMS parameter)
    {'name': '--pacing', 'type': str, 'default': 'throwing',
     'help': 'Pacing preset: archery, throwing, blaster'},

    # Game mode
    {'name': '--mode', 'type': str, 'default': 'classic',
     'help': 'Game mode: classic (static walls), dynamic (rotating spinners)'},

    # Game-specific difficulty
    {'name': '--tempo', 'type': str, 'default': 'mid',
     'help': 'Tempo preset: zen, mid, wild (ball aggression)'},
    {'name': '--ai', 'type': str, 'default': 'dumb',
     'help': 'AI level: dumb, reactive, strategic'},

    # Time/scoring
    {'name': '--time-limit', 'type': int, 'default': 60,
     'help': 'Seconds to survive (0 = endless)'},
    {'name': '--gap-count', 'type': int, 'default': None,
     'help': 'Number of gaps (overrides preset, classic mode only)'},
    {'name': '--spinner-count', 'type': int, 'default': 3,
     'help': 'Number of spinners (dynamic mode only)'},

    # Physical constraints (standard AMS parameters)
    {'name': '--max-deflectors', 'type': int, 'default': None,
     'help': 'Maximum deflectors allowed (None = unlimited)'},
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

## Playtest Feedback (December 2024)

**Problem:** Too easy/static. Close a few gaps and you've won. Needs more dynamism.

### Proposed Redesign Ideas

#### 1. Dynamic Environment Instead of Static Walls ✓ IMPLEMENTED

Use `--mode dynamic` or level YAML with `environment.spinners`. Rotating polygons create ever-changing geometry.

```bash
python dev_game.py containment --mode dynamic --spinner-count 5
```

```text
Before (static):          After (dynamic):
┌────────────────┐        ┌────────────────┐
│    ████        │        │    ◇ rotating  │
│  gap  gap      │        │  ▽     △       │
│        ████    │        │    ○ spinning  │
└────────────────┘        └────────────────┘
```

#### 2. Connect-the-Dots Wall Building ✓ IMPLEMENTED

Projectile placement creates geometry based on proximity. Use `--level connect_the_dots` or set `hit_modes.type: connect` in level YAML.

**Implemented behavior:**

- First hit drops a dot
- Hit within threshold of existing dot: creates wall from dot to hit position, consumes dot, leaves new dot at hit
- Chain hits to build multi-segment walls
- Hit outside threshold: drops independent dot

```yaml
# Example level config
hit_modes:
  selection: random
  modes:
    - type: connect
      config:
        threshold: 200
        fallback: point
        fallback_config:
          radius: 12
```

#### 3. Alternative Win Condition: Capture Zone

Instead of "contain indefinitely," engineer a bounce INTO a capture zone:

- Target zone appears on screen
- Ball bouncing into zone = win
- Player builds geometry to redirect ball trajectory
- More puzzle-like, less survival-like

```
┌────────────────────────┐
│                        │
│   ○ ball               │
│     \                  │
│      \→ deflector      │
│        \               │
│         ▼              │
│      [CAPTURE]         │
└────────────────────────┘
```

#### 4. Environmental Hazards

**Bouncing bombs** that player must avoid while shooting:

- Move around the play area
- Hit one = penalty (lose deflectors? speed up ball? game over?)
- Creates tension beyond just the ball
- Forces rushed/imperfect shots

#### 5. Projectile-Spawned Dynamic Geometry ✓ IMPLEMENTED

Projectiles spawn rotating/morphing obstacles. Use hit modes `spinner`, `morph`, or `grow`.

**Implemented obstacle types:**

- **Spinner** (`type: spinner`): Rotating polygon (triangle → hexagon)
- **Morph** (`type: morph`): Cycles through shapes, optional pulsation
- **Grow** (`type: grow`): Circular obstacle that expands when hit again

**Size dynamics (implemented):**

- **Pulsating:** Morph obstacles can pulse (sinusoidal size) via `pulsate: true`
- **Growth on hit:** Grow obstacles expand when hit within their bounds via `growth_per_hit`
- **Growth cap:** Configurable via `max_size`

```yaml
# Example: morphing obstacle config
- type: morph
  config:
    shapes: [triangle, square, pentagon, hexagon]
    morph_interval: 2.0
    size: 50
    rotation_speed: 30
    pulsate: true
    pulse_speed: 2.0
    pulse_amount: 0.15

# Example: growing obstacle config
- type: grow
  config:
    initial_size: 25
    growth_per_hit: 0.3
    max_size: 100
```

**Not yet implemented:**

- Decay (geometry shrinks over time)
- Shape determined by hit timing

---

## Game Mode Variants

| Mode | Core Mechanic | Win Condition | Status |
|------|---------------|---------------|--------|
| **Classic** | Static walls, close gaps | Survive time | ✓ Implemented |
| **Dynamic** | Rotating spinners, no permanent solutions | Survive time | ✓ Implemented |
| **Architect** | Connect-the-dots walls | Survive time / Build enclosure | ✓ `--level connect_the_dots` |
| **Chaos** | Projectiles spawn morphing/growing geometry | Survive the madness | ✓ `--level all_hit_modes` |
| **Mixed** | Weighted random hit modes | Survive time | ✓ `--level mixed_hits` |
| **Pinball** | Engineer bounces | Guide ball to capture zone | Planned (needs capture zone) |
| **Minefield** | Bouncing bombs + ball | Survive without hitting bombs | Planned |

**Implemented via Level System:** The YAML level loader enables all variant modes through hit mode configuration. Use `--choose-level` to browse available levels or `--level <name>` to load directly.

---

## Level Builder Toolkit ✓ IMPLEMENTED

### Philosophy

Separate **mechanics** (code) from **level design** (data). A YAML-based level definition allows:

- Rapid iteration on challenges without code changes
- Community/designer level creation
- Difficulty progression via level sequences
- A/B testing different configurations

### Current Implementation

```text
games/Containment/
├── levels/
│   ├── __init__.py              # Module exports
│   ├── level_loader.py          # Parse YAML, validate, instantiate
│   ├── schema.md                # Full YAML schema documentation
│   └── examples/
│       ├── classic_mode.yaml    # Classic gaps mode
│       ├── dynamic_mode.yaml    # Rotating spinners
│       ├── mixed_hits.yaml      # Weighted hit mode selection
│       ├── sequential_builder.yaml  # Sequential hit modes
│       ├── all_hit_modes.yaml   # Showcases all 6 hit modes
│       ├── connect_the_dots.yaml    # Pure connect mode
│       └── morph_demo.yaml      # Morphing obstacles demo
├── morph_obstacle.py            # Shape-morphing obstacles
├── grow_obstacle.py             # Growing obstacles
├── level_chooser.py             # Tile-based level selection UI
└── game_mode.py                 # Uses level loader
```

### Level Definition Schema (Implemented)

See `games/Containment/levels/schema.md` for full documentation. Example:

```yaml
name: "Mixed Obstacles"
description: "Each shot spawns different obstacle types"
difficulty: 3
author: "core"
version: 1

objectives:
  type: survive
  time_limit: 90

ball:
  count: 1
  speed: 140
  radius: 22
  spawn: center
  ai: dumb

environment:
  edges:
    mode: bounce  # bounce | gaps

  spinners:
    - position: [0.5, 0.5]
      shape: triangle
      size: 50
      rotation_speed: 30

hit_modes:
  selection: weighted  # random | sequential | weighted
  modes:
    - type: deflector
      weight: 5
      config:
        angle: random
        length: 60

    - type: spinner
      weight: 2
      config:
        shape: random
        size: [40, 60]
        rotation_speed: [25, 55]

    - type: point
      weight: 1
      config:
        radius: [12, 20]

    - type: connect
      config:
        threshold: 100
        fallback: point

    - type: morph
      config:
        shapes: [triangle, square, pentagon]
        morph_interval: 2.0
        pulsate: true

    - type: grow
      config:
        initial_size: 25
        growth_per_hit: 0.3
        max_size: 100

pacing:
  archery:
    ball.speed: 90
  blaster:
    ball.speed: 200
```

### Hit Mode Types

| Type | Description | Key Config |
|------|-------------|------------|
| `deflector` | Line segment wall | `angle`, `length` |
| `spinner` | Player-spawned rotating polygon | `shape`, `size`, `rotation_speed` |
| `point` | Circular obstacle | `radius` |
| `connect` | Connect-the-dots wall building (see below) | `threshold`, `fallback` |
| `morph` | Shape-changing polygon | `shapes`, `morph_interval`, `pulsate` |
| `grow` | Circle that grows when hit again | `initial_size`, `growth_per_hit`, `max_size` |

**Connect Mode Behavior:**
- First hit: Drops a visible dot at hit position
- Hit within threshold of existing dot: Creates wall FROM dot TO hit, consumes dot, places new dot at hit
- Chain hits within threshold to build multi-segment walls
- Hit outside threshold: Drops a new independent dot

### CLI Integration

```bash
# Play specific level
python dev_game.py containment --level mixed_hits

# Play from examples directory
python dev_game.py containment --level all_hit_modes

# Full path also works
python dev_game.py containment --level games/Containment/levels/examples/sequential_builder.yaml
```

### Level Editor (Future)

Eventually, a visual level editor:

```
┌─────────────────────────────────────────────────┐
│  CONTAINMENT LEVEL EDITOR                       │
├─────────────────────────────────────────────────┤
│                                                 │
│  [Toolbox]     │  [Preview]                     │
│  ○ Ball        │                                │
│  △ Spinner     │      △                         │
│  ◇ Morpher     │           ○                    │
│  ● Bomb        │                 □              │
│  ─ Wall        │                                │
│  □ Capture     │                                │
│                │                                │
├─────────────────────────────────────────────────┤
│  [Properties]  rotation: 45°/s  size: 80px     │
│  [Test] [Save] [Export YAML]                    │
└─────────────────────────────────────────────────┘
```

But YAML-first approach means levels are creatable without the editor.

---

## Open Questions (Updated)

### Resolved

1. ~~**Deflector shape:** Line segments? Arrow shapes? Circles?~~ → **Resolved:** Hit modes now support deflector (line), point (circle), spinner (polygon), morph (changing polygon), grow (expanding circle), connect (line to nearest).

2. ~~**Rotation speed:** How fast should dynamic geometry rotate?~~ → **Resolved:** Configurable per-obstacle, typically 30-60 degrees/sec. Supports random ranges.

3. ~~**Connect threshold:** What distance triggers wall creation vs point obstacle?~~ → **Resolved:** Configurable via `threshold` parameter (default 100px). Falls back to configurable type (point/deflector).

4. ~~**Morphing rate:** If shapes change over time, how fast?~~ → **Resolved:** `morph_interval` parameter (default 2.0 seconds). Independent per obstacle.

5. ~~**Retrieval mechanic:** Does dynamic geometry pause during retrieval?~~ → **Resolved:** Yes, all gameplay pauses during retrieval.

### Still Open

6. **Bomb behavior:** Bouncing pattern for hazards? Predictable vs chaotic? (Not yet implemented)

7. **Capture zone placement:** Random? Strategic (hardest corner)? Player-placed? (Not yet implemented)

8. **Ball AI:** How aggressive should reactive/strategic modes be? (Not yet implemented)

---

## Future: Multiplayer Modes

### Concept

Containment's mechanics naturally extend to multiplayer - both cooperative and competitive.

### Local Multiplayer (Same Screen)

**Cooperative:**
- Multiple players defend against the same ball(s)
- Different colored projectiles/deflectors per player
- Shared win/lose condition
- "You take left side, I'll take right"

**Competitive (Pong-like):**
- Each player has a capture zone on their side
- Ball entering YOUR zone = opponent scores
- Build deflectors to redirect ball toward opponent's zone
- First to N points wins

```
┌────────────────────────────────────────┐
│  [P1 ZONE]          ○           [P2 ZONE]│
│     ▲               ball           ▼     │
│   blue                           red     │
│  deflectors                   deflectors │
└────────────────────────────────────────┘
```

### Networked Multiplayer (Adjacent Targets)

Two archers on adjacent target butts, each with their own projector/camera:

**Architecture:**
```
┌─────────────┐    network    ┌─────────────┐
│  Butt A     │◄────────────►│  Butt B     │
│  Projector  │   game state  │  Projector  │
│  Camera     │   sync        │  Camera     │
│  Player 1   │               │  Player 2   │
└─────────────┘               └─────────────┘
```

**Sync requirements:**
- Ball position/velocity (authoritative server or peer-to-peer)
- Deflector placements from each player
- Score state
- Low latency critical for real-time physics

**Game modes:**
- **Mirror:** Same ball physics, each sees their own perspective
- **Portal:** Ball can cross between screens (hits right edge of A → appears left edge of B)
- **Volley:** Like tennis - redirect ball to opponent's screen

### Level Schema Extension

```yaml
# levels/multiplayer/versus_basic.yaml
multiplayer:
  mode: competitive  # cooperative | competitive
  players: 2

  player_zones:
    - player: 1
      color: [0, 100, 255]  # blue
      capture_zone:
        edge: left
        position: [0.0, 0.5]
        size: 0.2
    - player: 2
      color: [255, 100, 0]  # orange
      capture_zone:
        edge: right
        position: [1.0, 0.5]
        size: 0.2

  scoring:
    type: first_to  # first_to | timed
    target: 5       # points to win
```

### Implementation Considerations

- **Input disambiguation:** How to know which player made a shot?
  - Local: Different input devices, or screen regions
  - Networked: Each client reports own hits
- **Fairness:** Ball physics must be deterministic for network sync
- **Latency compensation:** Deflector placement needs to feel instant even with network delay

### Priority

This is a future feature - single-player needs to be solid first. But the YAML level system should be designed with multiplayer extensibility in mind.

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
