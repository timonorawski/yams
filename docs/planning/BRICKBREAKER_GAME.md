# BrickBreaker Game Implementation Plan

**Created**: 2025-12-10
**Status**: Planning

## Goal

Build a BrickBreaker game for AMS with:
- **Stopping paddle mode**: Player hits where they want paddle center to go
- **Data-driven brick behaviors**: ALL mechanics from YAML config, not code
- **Full level support**: YAML levels with ASCII layouts
- **Skins system**: Geometric (CV-friendly) and Classic (sprites)

## Key Design Principle

**All brick behaviors are data-driven.** The game engine reads behavior flags from level YAML and applies generic behaviors. No brick-type-specific code - new mechanics come from config combinations.

This approach was chosen because:
1. Level designers can create new brick types without code changes
2. Space Invaders mode is just bricks with `descends: true` flag
3. Shooter bricks are just bricks with `shoots: true` flag
4. Any combination of behaviors is possible via config

## File Structure

```
games/BrickBreaker/
├── __init__.py
├── main.py                        # Standalone entry point
├── config.py                      # Constants, pacing presets
├── game_info.py                   # Factory for registry
├── game_mode.py                   # BrickBreakerMode (inherits BaseGame)
├── game/
│   ├── __init__.py
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── paddle.py              # Stopping paddle movement
│   │   ├── ball.py                # Ball with physics
│   │   └── brick.py               # Brick with behavior flags
│   ├── physics/
│   │   ├── __init__.py
│   │   └── collision.py           # AABB collision, ball bouncing
│   ├── level_loader.py            # BrickBreakerLevelLoader
│   └── skins/
│       ├── __init__.py
│       ├── base.py                # BrickBreakerSkin ABC
│       ├── geometric.py           # Simple shapes
│       └── classic.py             # NES-style sprites
├── levels/
│   ├── tutorial_01.yaml
│   ├── tutorial_02.yaml
│   ├── space_invaders.yaml        # Descending bricks
│   └── campaign.yaml              # Level group
├── input/                         # Re-export from games.common
└── assets/                        # Sprites, sounds
```

## Core Entities

### Paddle (`game/entities/paddle.py`)

```python
class Paddle:
    """Paddle that slides to target position and stops."""

    def set_target(self, target_x: float) -> None:
        """Set target position (from player hit)."""
        self._target_x = clamp(target_x, half_width, screen_width - half_width)

    def update(self, dt: float) -> None:
        """Slide toward target, stop when reached."""
        if abs(self._x - self._target_x) < 1.0:
            self._x = self._target_x
            return
        direction = 1 if self._target_x > self._x else -1
        self._x += direction * self._speed * dt
```

### Ball (`game/entities/ball.py`)

```python
class Ball:
    """Ball with velocity-based physics."""

    def update(self, dt: float) -> 'Ball':
        return Ball(config, position + velocity * dt, velocity)

    def bounce_off_paddle(self, paddle) -> 'Ball':
        """Angle based on where ball hits paddle."""
        offset = (self.x - paddle.center_x) / (paddle.width / 2)
        # More offset = more horizontal angle
```

### Brick with Behavior Flags (`game/entities/brick.py`)

```python
@dataclass(frozen=True)
class BrickBehaviors:
    """ALL brick mechanics come from these flags - loaded from YAML."""

    # Core
    hits: int = 1                    # Hits to destroy
    points: int = 100
    color: str = "red"

    # Movement
    descends: bool = False           # Space Invaders mode
    descend_speed: float = 0.0
    oscillates: bool = False         # Side-to-side
    oscillate_speed: float = 0.0
    oscillate_range: float = 0.0

    # Combat
    shoots: bool = False             # Fires at paddle
    shoot_interval: float = 0.0

    # Hit restrictions
    hit_direction: str = "any"       # "top", "bottom", "left", "right", "any"

    # Destruction
    splits: bool = False             # Splits into smaller bricks
    split_into: int = 2
    explodes: bool = False           # Chain reaction
    explosion_radius: int = 1

    # Special
    indestructible: bool = False
    power_up: Optional[str] = None


class Brick:
    """Brick with behaviors driven entirely by config."""

    def can_be_hit_from(self, direction: str) -> bool:
        return self._behaviors.hit_direction == "any" or \
               self._behaviors.hit_direction == direction

    def update(self, dt: float) -> tuple['Brick', List['Projectile']]:
        """Apply all behavior flags generically."""
        projectiles = []

        if self._behaviors.descends:
            self._y += self._behaviors.descend_speed * dt

        if self._behaviors.oscillates:
            # Oscillate logic

        if self._behaviors.shoots:
            self._shoot_timer += dt
            if self._shoot_timer >= self._behaviors.shoot_interval:
                projectiles.append(self._create_projectile())
                self._shoot_timer = 0

        return self, projectiles
```

## Level YAML Format

### Basic Level (`levels/tutorial_01.yaml`)

```yaml
name: "Tutorial 1 - The Basics"
difficulty: 1

brick_types:
  red:
    color: red
    hits: 1
    points: 100
  blue:
    color: blue
    hits: 1
    points: 100

grid_cols: 10
grid_rows: 5
brick_width: 70
brick_height: 25

layout: |
  RRRRRRRRRR
  BBBBBBBBBB
  RRRRRRRRRR
  BBBBBBBBBB
  RRRRRRRRRR

layout_key:
  R: red
  B: blue
  .: empty

paddle:
  width: 120
  speed: 400

ball:
  speed: 250

lives: 3
```

### Space Invaders Level (`levels/space_invaders.yaml`)

```yaml
name: "Space Invaders Mode"
difficulty: 3

brick_types:
  invader:
    color: green
    hits: 1
    points: 100
    descends: true
    descend_speed: 15

  invader_moving:
    color: cyan
    hits: 1
    points: 150
    descends: true
    descend_speed: 15
    oscillates: true
    oscillate_speed: 30
    oscillate_range: 20

  boss:
    color: red
    hits: 3
    points: 500
    descends: true
    descend_speed: 10
    shoots: true
    shoot_interval: 2.0

layout: |
  .MMMMMMMM.
  IIIIIIIIII
  IIIIIIIIII
  MMMMMMMMMM
  ...BB.....

layout_key:
  I: invader
  M: invader_moving
  B: boss
  .: empty
```

## Skins

### Base Skin (`game/skins/base.py`)

```python
class BrickBreakerSkin(ABC):
    NAME: str = "base"

    @abstractmethod
    def render_paddle(self, paddle, screen) -> None: pass

    @abstractmethod
    def render_ball(self, ball, screen) -> None: pass

    @abstractmethod
    def render_brick(self, brick, screen) -> None: pass

    def render_projectile(self, proj, screen) -> None: pass
    def update(self, dt: float) -> None: pass
    def play_brick_break_sound(self) -> None: pass
    def play_paddle_hit_sound(self) -> None: pass
```

### Geometric Skin

- Paddle: Blue rectangle with white outline
- Ball: White circle
- Bricks: Colored rectangles based on `brick.behaviors.color`
- Multi-hit bricks: Darken color based on damage
- Special indicators: Triangle for shooters, X for indestructible

### Classic Skin

- NES-style pixel sprites
- Sound effects for hits, breaks, bounces
- Animations for destruction

## Game Mode Integration

```python
class BrickBreakerMode(BaseGame):
    NAME = "Brick Breaker"
    LEVELS_DIR = Path(__file__).parent / 'levels'

    ARGUMENTS = [
        {'name': '--skin', 'type': str, 'default': 'geometric',
         'choices': ['geometric', 'classic']},
        {'name': '--pacing', 'type': str, 'default': 'throwing',
         'choices': ['archery', 'throwing', 'blaster']},
        {'name': '--lives', 'type': int, 'default': 3},
    ]

    def handle_input(self, events):
        for event in events:
            self._paddle.set_target(event.position.x)
            if not self._ball_launched:
                self._launch_ball()

    def update(self, dt):
        self._paddle.update(dt)
        self._ball = self._handle_collisions(self._ball.update(dt))

        for brick in self._bricks:
            brick, projectiles = brick.update(dt)
            self._projectiles.extend(projectiles)

    def render(self, screen):
        for brick in self._bricks:
            self._skin.render_brick(brick, screen)
        self._skin.render_paddle(self._paddle, screen)
        self._skin.render_ball(self._ball, screen)
```

## Implementation Phases

### Phase 1: Core Foundation
1. Create directory structure
2. `config.py` with constants
3. `Paddle` class (stopping mode)
4. `Ball` class with physics
5. `Brick` class (single-hit only)
6. Basic collision detection
7. `BrickBreakerMode` with hardcoded level
8. `main.py` standalone launcher

**Deliverable**: Playable with mouse, simple grid

### Phase 2: Skins
1. `BrickBreakerSkin` ABC
2. `GeometricSkin` implementation
3. `--skin` CLI argument

**Deliverable**: Selectable geometric skin

### Phase 3: Level System
1. Level config Pydantic models
2. `BrickBreakerLevelLoader`
3. ASCII layout parsing
4. Tutorial levels
5. `--level` CLI argument

**Deliverable**: YAML-based levels

### Phase 4: Data-Driven Behaviors
1. Full `BrickBehaviors` dataclass
2. `hits` behavior (multi-hit)
3. `descends` behavior
4. `oscillates` behavior
5. `shoots` behavior + projectiles
6. `hit_direction` behavior
7. `splits` behavior
8. `explodes` behavior
9. Demo levels for each

**Deliverable**: Full behavior system

### Phase 5: Classic Skin
1. Sprite assets
2. `ClassicSkin` with sprites
3. Sound effects

**Deliverable**: NES-style visuals

### Phase 6: Campaigns
1. Level group YAML
2. Tutorial campaign
3. Challenge campaign

**Deliverable**: Full progression

### Phase 7: Polish
1. Visual feedback effects
2. Scoring with combos
3. Game over/win screens
4. Unit tests
5. Documentation

## Critical Reference Files

| File | Purpose |
|------|---------|
| `games/common/base_game.py` | BaseGame to inherit |
| `games/common/levels.py` | LevelLoader[T] to subclass |
| `games/DuckHunt/game_mode.py` | Reference for skins pattern |
| `games/DuckHunt/game/skins/base.py` | GameSkin ABC pattern |
| `games/Containment/levels/level_loader.py` | Complex level loader example |

## Usage

```bash
# Basic play
python ams_game.py --game brickbreaker --backend mouse

# With skin and level
python ams_game.py --game brickbreaker --skin geometric --level tutorial_01

# Space Invaders mode
python ams_game.py --game brickbreaker --level space_invaders

# Campaign
python ams_game.py --game brickbreaker --level-group campaign
```

## Design Decisions

### Why "Stopping Paddle" Mode?
- Simpler to understand for new players
- Works well with AMS's click-to-target input model
- Feels natural with laser pointer, blasters, and arrows

### Why Data-Driven Behaviors?
- User explicitly requested: "all behavioural modifiers should be done via config, not code"
- Allows level designers to create new brick types without code changes
- Space Invaders mode is just `descends: true` flag
- Shooter bricks are just `shoots: true` flag
- Any combination is possible

### Why ASCII Layouts?
- Much easier to visualize level design than coordinate lists
- Quick iteration on layouts
- Human-readable in version control diffs
