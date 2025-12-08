# FruitSlice Game Planning

## Overview

A Fruit Ninja-inspired game where targets arc across the screen in parabolic trajectories. Players must hit targets while they're in motion. Hitting bombs ends the game or costs lives.

**Training Focus:** Lead/timing, tracking, discrimination (shoot/no-shoot), reaction speed

## Input Device Considerations

The AMS platform supports varied projectile types with vastly different interaction speeds:

| Device | Cycle Time | Characteristics |
|--------|------------|-----------------|
| **Nerf Blaster** | ~0.3s | Rapid fire, low accuracy penalty |
| **Laser Pointer** | instant | Continuous, instant feedback |
| **Foam Balls** | ~1s | Throw, retrieve, throw again |
| **Darts** | ~2s | Aim, throw, retrieve |
| **Archery** | 3-8s | Nock, draw, aim, release, retrieve |

**Design Principle:** All timing parameters must be configurable to accommodate any input device. A game that works for Nerf should also work for archery with adjusted pacing.

### Physical Resource Constraints

Some input devices have limited ammunition requiring retrieval:

| Device | Typical Capacity | Retrieval Pattern |
|--------|------------------|-------------------|
| **Archery** | 3-12 arrows | Shoot all → retrieve all |
| **Darts** | 3-6 darts | Shoot all → retrieve all |
| **Foam Balls** | 1-5 balls | Often retrieve between throws |
| **Nerf Blaster** | 6-30 darts | Magazine reload or retrieve |

**Required Features:**

1. **Quiver/Ammo Mode**: Limit shots per round to match physical capacity
   - `--quiver-size 6` - Round ends after 6 shots, then retrieval pause
   - Score based on hits within quiver capacity
   - Natural break for arrow/dart retrieval

2. **Pause for Retrieval**: Manual or automatic pause between rounds
   - `--retrieval-pause 30` - 30 second pause between rounds
   - Or press key/button to signal "ready" after retrieval

3. **Round-Based Play**: Structure game as discrete rounds matching quiver size
   - Round 1: 6 targets, 6 arrows → retrieve → Round 2: 6 targets...
   - Cumulative scoring across rounds
   - Progressive difficulty between rounds (not within)

4. **Endless with Pauses**: Continuous play with retrieval breaks
   - Play until quiver empty → forced pause → continue
   - No penalty for pause time (it's physical necessity)

## Core Mechanics

### Target Physics

Targets follow parabolic arcs (projectile motion):
- Spawn from left or right edge, below screen
- Launch upward at an angle with initial velocity
- Gravity pulls them back down in a smooth arc
- Exit screen on opposite side or bottom

```
     ___apex___
    /          \
   /            \
  /              \
spawn           exit
```

**Physics equations:**
```python
x = x0 + vx * t
y = y0 + vy * t - 0.5 * g * t²
```

Where:
- `vx` = horizontal velocity (constant)
- `vy` = initial vertical velocity (decreases due to gravity)
- `g` = gravity constant

### Target Types

| Type | Color | Points | Behavior |
|------|-------|--------|----------|
| **Fruit** | Various bright colors | +10-50 | Standard target, hit for points |
| **Golden Fruit** | Gold/Yellow glow | +100 | Rare, bonus points |
| **Bomb** | Black/Red | -life or game over | Avoid! Hitting ends round or costs life |
| **Freeze** | Blue/Cyan | Slow-mo | Optional power-up, slows time briefly |

### Combo System

- **Rapid hits** within time window build combo multiplier
- Combo resets after ~1.5 seconds without a hit
- Multiplier: 1x → 2x → 3x → 4x → 5x (max)
- Visual feedback: combo counter, screen effects

### Scoring

```
base_points = target.value
combo_bonus = base_points * (combo_multiplier - 1)
total = base_points + combo_bonus
```

Example: Hit a 30-point fruit at 4x combo = 30 + 90 = 120 points

### Lives System

- Start with 3 lives
- Lose life when:
  - Hit a bomb
  - Let 3 fruits pass without hitting (configurable)
- Game over when lives = 0

## Game Modes

### Classic

- Continuous fruit spawning
- Bombs mixed in (~15% of spawns)
- Score attack until game over
- Increasing difficulty over time (more fruits, faster, more bombs)

### Zen (No Bombs)

- No bombs - pure accuracy practice
- Relaxed, no penalty for misses
- Good for learning timing and trajectories

### Arcade

- Timed rounds (60/90/120 seconds)
- High score challenge
- Bomb ratio increases over time

### Quiver Mode (Physical Ammo)

- `--quiver-size N` enables this mode
- Round structure: N targets spawn → player shoots N times → retrieval pause
- Game pauses automatically after N shots detected
- Display: "Retrieval Time - Press SPACE when ready" (or auto-resume after timer)
- Combo persists across retrieval pause (reward consistency across rounds)
- Progressive difficulty between rounds, not within
- Perfect for archery, darts, limited ammo scenarios

### Challenge

- Specific goals: "Hit 50 fruits", "Reach 5x combo", "Score 1000 points"
- Unlock progression

## Pacing Presets

Games must adapt to input device speed. Rather than "difficulty", we use **pacing presets**:

### Archery Preset (Slow)

Designed for 3-8 second shot cycles:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Spawn interval | 4-6s | One target in flight per shot cycle |
| Max simultaneous | 2 | Rarely overlap, clear shot selection |
| Arc duration | 5-8s | Long hang time, plan your shot |
| Target size | Large (60-80px) | Forgiving hit detection |
| Bomb ratio | 10% | Rare, clear identification time |
| Miss tolerance | High | Retrieval time between shots |

### Throwing Preset (Medium)

Designed for 1-2 second throw cycles:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Spawn interval | 1.5-2.5s | Steady stream, manageable pace |
| Max simultaneous | 3-4 | Some overlap, prioritization needed |
| Arc duration | 3-5s | Time to track and throw |
| Target size | Medium (40-60px) | Standard hit detection |
| Bomb ratio | 15% | Moderate discrimination challenge |
| Miss tolerance | Medium | Some penalty for misses |

### Blaster Preset (Fast)

Designed for rapid-fire (0.3-0.5s cycles):

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Spawn interval | 0.5-1.0s | Rapid targets, action-packed |
| Max simultaneous | 5-8 | Many targets, fast decisions |
| Arc duration | 2-3s | Quick crossing, reactive shots |
| Target size | Small-Medium (30-50px) | Accuracy challenge |
| Bomb ratio | 20-30% | Frequent discrimination |
| Miss tolerance | Low | Spray-and-pray penalty |

### Custom Preset

All parameters individually configurable via CLI for any use case.

## Difficulty Progression (Within Preset)

Difficulty increases *within* a pacing preset over time:

| Parameter | Start | +30s | +60s | +90s |
|-----------|-------|------|------|------|
| Spawn rate | base | 0.9x | 0.8x | 0.7x |
| Target speed | base | 1.1x | 1.2x | 1.3x |
| Bomb ratio | base | +5% | +10% | +15% |
| Max simultaneous | base | +1 | +2 | +3 |

This keeps the game challenging regardless of starting preset.

## Visual Design

### Targets
- Circular targets with distinct colors
- Size varies (larger = easier, fewer points)
- Trail effect showing trajectory
- Slice effect on hit (particles, flash)

### Bombs
- Clearly distinct from fruits (black with red warning glow)
- Pulsing animation
- Explosion effect if hit

### Background
- Dark background for contrast
- Subtle grid or pattern (not distracting)

### HUD
- Score (top left)
- Combo multiplier (center, fades when inactive)
- Lives (top right)
- Time remaining (arcade mode)

## Implementation Structure

```
games/FruitSlice/
├── __init__.py
├── game_info.py          # Metadata, CLI args, factory
├── game_mode.py          # Main game logic
├── config.py             # Configuration from .env
├── .env                  # Default settings
├── main.py               # Standalone entry
├── fruit.py              # Fruit/target entity with physics
├── bomb.py               # Bomb entity (or unified with fruit)
├── spawner.py            # Spawn logic, difficulty progression
└── input/                # Re-exports from common
    ├── __init__.py
    ├── input_manager.py
    ├── input_event.py
    └── sources/
        ├── __init__.py
        └── mouse.py
```

### Key Classes

#### `ArcingTarget` (dataclass)
```python
@dataclass
class ArcingTarget:
    x: float
    y: float
    vx: float              # Horizontal velocity
    vy: float              # Vertical velocity (affected by gravity)
    radius: float
    color: tuple
    target_type: TargetType  # FRUIT, GOLDEN, BOMB, FREEZE
    points: int
    spawn_time: float
    hit: bool = False

    def update(self, dt: float, gravity: float) -> None:
        self.x += self.vx * dt
        self.vy += gravity * dt  # Gravity pulls down
        self.y += self.vy * dt

    def is_off_screen(self, width: int, height: int) -> bool:
        # Check if target has left the screen
        ...
```

#### `FruitSpawner`
```python
class FruitSpawner:
    def __init__(self, screen_width, screen_height, difficulty):
        ...

    def update(self, dt: float, elapsed_time: float) -> List[ArcingTarget]:
        # Adjust difficulty based on elapsed_time
        # Return new targets to spawn
        ...

    def _create_fruit(self, from_left: bool) -> ArcingTarget:
        # Calculate launch angle and velocity for nice arc
        ...
```

#### `ComboTracker`
```python
class ComboTracker:
    def __init__(self, combo_window: float = 1.5):
        self.multiplier = 1
        self.last_hit_time = 0
        self.combo_window = combo_window

    def register_hit(self, timestamp: float) -> int:
        # Update combo, return current multiplier
        ...

    def update(self, current_time: float) -> None:
        # Reset combo if window expired
        ...
```

## CLI Arguments

```python
ARGUMENTS = [
    # Game mode
    {
        'name': '--mode',
        'type': str,
        'default': 'classic',
        'help': 'Game mode: classic, zen, arcade'
    },

    # Pacing preset (core timing parameter)
    {
        'name': '--pacing',
        'type': str,
        'default': 'medium',
        'help': 'Pacing preset: archery (slow), throwing (medium), blaster (fast), custom'
    },

    # Individual timing overrides (for --pacing custom or fine-tuning)
    {
        'name': '--spawn-interval',
        'type': float,
        'default': None,
        'help': 'Seconds between spawns (overrides preset)'
    },
    {
        'name': '--arc-duration',
        'type': float,
        'default': None,
        'help': 'How long targets stay on screen (overrides preset)'
    },
    {
        'name': '--max-targets',
        'type': int,
        'default': None,
        'help': 'Maximum simultaneous targets (overrides preset)'
    },
    {
        'name': '--target-size',
        'type': int,
        'default': None,
        'help': 'Base target radius in pixels (overrides preset)'
    },

    # Game rules
    {
        'name': '--time-limit',
        'type': int,
        'default': None,
        'help': 'Time limit in seconds (arcade mode)'
    },
    {
        'name': '--lives',
        'type': int,
        'default': 3,
        'help': 'Starting lives'
    },
    {
        'name': '--no-bombs',
        'action': 'store_true',
        'default': False,
        'help': 'Disable bombs (zen mode)'
    },
    {
        'name': '--bomb-ratio',
        'type': float,
        'default': None,
        'help': 'Fraction of spawns that are bombs (0.0-1.0)'
    },

    # Combo system
    {
        'name': '--combo-window',
        'type': float,
        'default': None,
        'help': 'Seconds before combo resets (longer for slow devices)'
    },

    # Physical resource constraints (quiver/ammo)
    {
        'name': '--quiver-size',
        'type': int,
        'default': None,
        'help': 'Shots per round before retrieval pause (None = unlimited)'
    },
    {
        'name': '--retrieval-pause',
        'type': int,
        'default': 30,
        'help': 'Seconds for retrieval between rounds (0 = manual ready)'
    },
    {
        'name': '--rounds',
        'type': int,
        'default': None,
        'help': 'Number of rounds (None = endless until game over)'
    },
]
```

### Pacing Preset Defaults

| Parameter | archery | throwing | blaster |
|-----------|---------|----------|---------|
| spawn_interval | 5.0s | 2.0s | 0.75s |
| arc_duration | 6.0s | 4.0s | 2.5s |
| max_targets | 2 | 4 | 6 |
| target_size | 70px | 50px | 40px |
| bomb_ratio | 0.10 | 0.15 | 0.25 |
| combo_window | 8.0s | 3.0s | 1.5s |

The combo window is critical - archery needs 8+ seconds to maintain combo between shots, while blaster can use tight 1.5s windows.

## Training Value

### Skills Trained

| Skill | Coverage | Notes |
|-------|----------|-------|
| **Lead/Timing** | ★★★★★ | Core mechanic - predict where target will be |
| **Tracking** | ★★★★☆ | Follow arc trajectory |
| **Discrimination** | ★★★★☆ | Identify bomb vs fruit quickly |
| **Reaction Speed** | ★★★★☆ | Fast recognition and response |
| **Divided Attention** | ★★★☆☆ | Multiple targets simultaneously |
| **Pressure Management** | ★★★☆☆ | Increasing difficulty, combo maintenance |

### Why It Works for Training

1. **Variable Practice**: Every arc is different - angle, speed, spawn side
2. **Natural Timing**: Parabolic motion matches real-world projectile intuition
3. **Risk/Reward**: Combo system rewards sustained accuracy
4. **Discrimination Under Pressure**: Bombs force shoot/no-shoot decisions
5. **Progressive Difficulty**: Adapts to skill level
6. **Device Agnostic**: Pacing presets ensure meaningful challenge regardless of input speed

### Device-Specific Training Notes

**Archery (slow pacing):**
- Emphasizes shot selection and timing over volume
- Long arc duration allows full draw-aim-release cycle
- Combo window accommodates arrow retrieval
- Training: deliberate aiming, patience, shot commitment

**Throwing (medium pacing):**
- Balanced between speed and deliberation
- Multiple targets require prioritization
- Training: quick acquisition, target switching, rhythm

**Blaster (fast pacing):**
- High volume, rapid target discrimination
- Many simultaneous targets
- Training: rapid target ID, divided attention, trigger discipline (don't hit bombs)

## Development Phases

### Phase 1: Core Mechanics
- [ ] Basic arcing target physics
- [ ] Spawn from edges
- [ ] Hit detection
- [ ] Simple scoring

### Phase 2: Game Feel
- [ ] Combo system
- [ ] Visual effects (hit flash, trails)
- [ ] Sound placeholders
- [ ] Lives system

### Phase 3: Bombs & Modes
- [ ] Bomb targets
- [ ] Game over logic
- [ ] Zen mode (no bombs)
- [ ] Arcade mode (timed)

### Phase 4: Polish
- [ ] Difficulty progression
- [ ] Visual polish
- [ ] HUD improvements
- [ ] VSCode launch configs

## Physics Notes

### Calculating Launch Parameters

For a target to arc nicely across screen:

```python
def calculate_launch(from_left: bool, screen_width: int, screen_height: int):
    # Spawn position
    if from_left:
        x = -50  # Off-screen left
        vx = random.uniform(200, 400)  # Moving right
    else:
        x = screen_width + 50
        vx = random.uniform(-400, -200)  # Moving left

    y = screen_height + 50  # Below screen

    # Calculate vy to reach desired apex height
    apex_height = random.uniform(100, screen_height * 0.7)
    # Using v² = u² + 2as, where v=0 at apex
    # 0 = vy² - 2 * g * apex_height
    # vy = sqrt(2 * g * apex_height)
    vy = -math.sqrt(2 * GRAVITY * apex_height)  # Negative = upward

    return x, y, vx, vy
```

### Gravity Constant

A good starting value: `GRAVITY = 800` pixels/second²

This gives satisfying arcs that aren't too floaty or too fast.

## References

- BalloonPop (`games/BalloonPop/balloon.py`) - Entity pattern, state management
- GrowingTargets (`games/GrowingTargets/target.py`) - Target lifecycle
- DuckHunt - Moving targets, difficulty progression
