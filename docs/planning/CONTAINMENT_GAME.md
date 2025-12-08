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

## Playtest Feedback (December 2024)

**Problem:** Too easy/static. Close a few gaps and you've won. Needs more dynamism.

### Proposed Redesign Ideas

#### 1. Dynamic Environment Instead of Static Walls

Replace static walls/gaps with **rotating geometric structures**:

- Generatively placed polygons that rotate continuously
- Create ever-changing gaps and openings
- Ball must navigate through shifting geometry
- Player can never "solve" the level permanently

```
Before (static):          After (dynamic):
┌────────────────┐        ┌────────────────┐
│    ████        │        │    ◇ rotating  │
│  gap  gap      │        │  ▽     △       │
│        ████    │        │    ○ spinning  │
└────────────────┘        └────────────────┘
```

#### 2. Connect-the-Dots Wall Building

Projectile placement creates geometry based on proximity:

- **Close together (< threshold):** Forms a wall segment between them
- **Far apart:** Just a point obstacle (circle or random small shape)
- **Three close:** Could form a triangle enclosure

This rewards intentional, strategic placement over spam.

```python
def on_hit(position):
    nearby = find_hits_within_radius(position, CONNECT_THRESHOLD)
    if nearby:
        # Create wall segment(s) connecting to nearby hits
        for hit in nearby:
            create_wall_segment(hit.position, position)
    else:
        # Isolated hit - just a small obstacle
        create_point_obstacle(position)
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

#### 5. Projectile-Spawned Dynamic Geometry

Projectiles themselves spawn rotating/morphing obstacles:

- Each hit creates a shape that rotates and changes
- Could cycle through polygon types (triangle → square → pentagon)
- Or continuously morph vertices
- Adds chaos and unpredictability to your own placements

**Size dynamics:**

- **Pulsating:** Geometry breathes in/out over time (sinusoidal size)
- **Growth on grouping:** Hit within existing geometry = that geometry grows larger
  - Creates risk/reward: intentional grouping builds bigger walls, but requires precision
  - Accidental grouping might block areas you didn't intend
- **Decay:** Geometry slowly shrinks over time, needs "feeding" with more hits to maintain

```python
class SpawnedGeometry:
    def __init__(self, position, base_size=50):
        self.position = position
        self.base_size = base_size
        self.growth_level = 1.0  # Multiplier from grouping
        self.pulse_phase = 0.0

    def add_grouped_hit(self):
        """Another projectile landed within this geometry."""
        self.growth_level += 0.3  # Grow by 30%

    def get_current_size(self, time):
        pulse = 1.0 + 0.15 * math.sin(self.pulse_phase + time * 2)  # ±15% pulsation
        return self.base_size * self.growth_level * pulse

    def contains(self, point) -> bool:
        """Check if point is within current geometry bounds."""
        # Used to detect grouping hits
        pass
```

**Variants to test:**

- Random shape on spawn
- Shape cycles through variants over time
- Shape determined by hit timing (hit during certain phase = certain shape)
- Side count increases/decreases rhythmically
- **Pulsation speed** varies by shape type
- **Growth cap** or unlimited scaling?
- **Decay rate** balanced against growth rate

---

## Game Mode Variants (to prototype)

| Mode | Core Mechanic | Win Condition |
|------|---------------|---------------|
| **Classic** (current) | Static walls, close gaps | Survive time |
| **Dynamic** | Rotating geometry, no permanent solutions | Survive time |
| **Architect** | Connect-the-dots walls | Build enclosure / capture zone |
| **Pinball** | Engineer bounces | Guide ball to capture zone |
| **Chaos** | Projectiles spawn morphing geometry | Survive the madness |
| **Minefield** | Bouncing bombs + ball | Survive without hitting bombs |

**Testing priority:** Start with Dynamic (rotating obstacles) and Architect (connect-the-dots) as they address the core "too easy" problem most directly.

---

## Level Builder Toolkit

### Philosophy

Separate **mechanics** (code) from **level design** (data). A YAML-based level definition allows:

- Rapid iteration on challenges without code changes
- Community/designer level creation
- Difficulty progression via level sequences
- A/B testing different configurations

### Level Definition Schema

```yaml
# levels/containment/dynamic_intro.yaml
name: "Spinning Gates"
description: "Learn to navigate rotating obstacles"
difficulty: 1
author: "core"

# Win/lose conditions
objectives:
  type: survive  # survive | capture | escape
  time_limit: 60  # seconds (null = endless)
  capture_zone:   # only for type: capture
    position: [0.5, 0.9]
    radius: 0.08

# Ball configuration
ball:
  count: 1
  speed: 120
  radius: 20
  spawn: center  # center | random | position
  ai: dumb       # dumb | reactive | strategic

# Environment geometry
environment:
  # Static walls (screen edges with gaps)
  walls:
    - edge: top
      gaps: [[0.3, 0.4], [0.7, 0.8]]  # [start, end] normalized
    - edge: bottom
      gaps: []  # solid wall

  # Dynamic rotating obstacles
  spinners:
    - position: [0.3, 0.5]
      shape: triangle
      size: 80
      rotation_speed: 45  # degrees/second

    - position: [0.7, 0.5]
      shape: rectangle
      size: 100
      rotation_speed: -30  # negative = counter-clockwise

  # Morphing obstacles (change shape over time)
  morphers:
    - position: [0.5, 0.3]
      shapes: [triangle, square, pentagon, hexagon]
      morph_interval: 2.0  # seconds between shape changes
      size: 60

  # Bouncing hazards
  bombs:
    - speed: 100
      radius: 25
      spawn: random
      behavior: bounce  # bounce | seek_player | patrol

# Player mechanics
player:
  mode: connect_dots  # point | line | connect_dots | morph_spawn

  # For connect_dots mode
  connect_threshold: 100  # pixels - closer creates walls

  # For morph_spawn mode
  spawn_shapes: [triangle, square]
  spawn_rotation: true

  # Constraints
  max_obstacles: null  # null = unlimited
  obstacle_lifetime: null  # null = permanent, or seconds

# Pacing overrides (optional - defaults from --pacing flag)
pacing:
  archery:
    ball_speed: 80
    connect_threshold: 120  # larger threshold = easier to connect
  blaster:
    ball_speed: 200
    connect_threshold: 60
```

### Toolkit Components

```
games/Containment/
├── toolkit/
│   ├── __init__.py
│   ├── level_loader.py      # Parse YAML, validate, instantiate
│   ├── geometry.py          # Spinner, Morpher, Wall classes
│   ├── objectives.py        # Win/lose condition checkers
│   └── spawners.py          # Ball, bomb, obstacle spawning
├── levels/
│   ├── tutorial/
│   │   ├── 01_static.yaml
│   │   ├── 02_first_spinner.yaml
│   │   └── 03_connect_dots.yaml
│   ├── campaign/
│   │   ├── 01_easy.yaml
│   │   └── ...
│   └── challenge/
│       ├── chaos_mode.yaml
│       └── minefield.yaml
└── game_mode.py             # Uses toolkit to run levels
```

### Level Loader API

```python
from toolkit.level_loader import load_level, LevelConfig

class ContainmentMode(BaseGame):
    def __init__(self, level: str = None, **kwargs):
        if level:
            self.config = load_level(f"levels/{level}.yaml")
        else:
            self.config = LevelConfig.default()

        self._setup_from_config(self.config)

    def _setup_from_config(self, config: LevelConfig):
        # Ball
        self.ball = Ball(
            speed=config.ball.speed,
            radius=config.ball.radius,
            ai=config.ball.ai,
        )

        # Environment
        for spinner_def in config.environment.spinners:
            self.spinners.append(Spinner(**spinner_def))

        for morpher_def in config.environment.morphers:
            self.morphers.append(Morpher(**morpher_def))

        # Objectives
        self.objective = create_objective(config.objectives)
```

### CLI Integration

```bash
# Play specific level
python dev_game.py containment --level tutorial/01_static

# List available levels
python dev_game.py containment --list-levels

# Play campaign (sequential levels)
python dev_game.py containment --campaign

# Random challenge
python dev_game.py containment --random-level difficulty=3
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

1. ~~**Deflector shape:** Line segments? Arrow shapes? Circles?~~ → Now depends on mode (connect-the-dots vs point obstacles)

2. **Rotation speed:** How fast should dynamic geometry rotate? Needs to be readable but challenging.

3. **Connect threshold:** What distance triggers wall creation vs point obstacle?

4. **Morphing rate:** If shapes change over time, how fast? Synchronized or independent?

5. **Bomb behavior:** Bouncing pattern for hazards? Predictable vs chaotic?

6. **Capture zone placement:** Random? Strategic (hardest corner)? Player-placed?

7. **Retrieval mechanic:** Does dynamic geometry pause during retrieval? (Probably yes for archery mode)

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
