# GameEngine Refactor Plan: Fully Data-Driven Games

## Vision

Games should be **configuration + Lua behaviors**, not Python code. A new game should require:
1. A `game.yaml` defining entities, collisions, win/lose conditions
2. Level YAML files with layouts
3. A minimal Python class that just points to the YAML and provides a skin

BrickBreakerNG currently has ~150 lines of game logic in Python that should be eliminated.

## Current State: BrickBreakerNGMode

```
BrickBreakerNGMode (347 lines)
├── BrickBreakerNGSkin (83 lines) - KEEP (rendering is Python's job)
├── __init__ (20 lines) - KEEP (minimal setup)
├── _get_skin, _create_level_loader (6 lines) - KEEP (factory methods)
├── _apply_level_config (47 lines) - PARTIALLY KEEP (level loading)
├── _spawn_initial_entities (30 lines) - REMOVE (use default_layout)
├── _spawn_default_bricks (30 lines) - REMOVE (use default_layout)
├── _handle_player_input (14 lines) - REMOVE (make declarative)
├── _handle_ball_lost (18 lines) - REMOVE (move to Lua)
├── _check_collisions override (14 lines) - REMOVE (make declarative)
└── _on_level_transition (3 lines) - KEEP (hook)
```

**Target:** ~100 lines (skin + minimal boilerplate)

---

## Phase 1: Input Mapping (Declarative)

### Problem
Python hardcodes input handling:
```python
def _handle_player_input(self, event: InputEvent):
    paddle.properties['paddle_target_x'] = event.position.x
    if not ball.properties.get('ball_launched'):
        ball_behavior.launch(ball.id, -75)
```

### Solution
Add `input_mapping` to game.yaml:

```yaml
input_mapping:
  # Map input position to entity property
  paddle:
  on_input:
    action: set_property
    x: input.position.x

  # Trigger Lua function on input (when condition met)
  ball:
    on_input:
      action: ball.launch
      when:
        property: ball_launched
        value: false
      modifier:
        angle: -75
```

The `when` block is extensible for future needs:
```yaml
when:
  property: some_prop
  value: expected_value
  # Future optional keys:
  # compare: equals | greater_than | less_than | contains
  # target: self | other | nearest
  # any_of: [value1, value2]
```

### Engine Changes
- `GameEngine._handle_player_input()` reads `input_mapping` from game_def
- For property mappings: set property directly
- For action triggers: call Lua function via behavior engine

### Lua Changes
- Add `ball.launch_from_paddle(entity_id, modifier)` or use existing `ball.launch`

---

## Phase 2: Lose Conditions (Declarative)

### Problem
Python checks `ball_fell` and handles life loss:
```python
def _check_collisions(self):
    if ball.properties.get('ball_fell'):
        self._handle_ball_lost()
```

### Solution
Add `lose_conditions` to game.yaml using events instead of properties:

```yaml
lose_conditions:
  - entity_type: ball
    event: exited_screen
    edge: bottom           # optional: top, bottom, left, right, any
    action: lose_life
    reset_action: ball.reset
```

This is better than property-based because:
- Engine detects screen exit directly (no `ball_fell` property needed in Lua)
- Reusable pattern for other games (enemies escaping, projectiles leaving)
- Configurable which edge matters

Future events could include:
```yaml
event: exited_screen     # left screen bounds
event: health_zero       # health reached 0
event: timer_expired     # entity-specific timer
```

### Engine Changes
- `GameEngine.update()` checks entity positions against screen bounds
- When `exited_screen` event detected:
  1. Call `lose_life()`
  2. Execute `then` block: destroy ball, transform paddle→paddle_ready
- Remove `ball_fell` property check from ball.lua (engine handles it)

### Lua Changes
- Remove `ball_fell` property handling from ball.lua (engine detects screen exit)
- No `ball.reset()` needed - transform handles the state change

---

## Phase 4: Default Layout from YAML

### Problem
Python hardcodes default brick layout:
```python
def _spawn_default_bricks(self):
    colors = ['red', 'orange', 'yellow', 'green', 'blue']
    # ... 30 lines of grid generation
```

### Solution
Use `default_layout` already in game.yaml:

```yaml
default_layout:
  ball_spawn: [392, 525]
  paddle_spawn: [340, 550]
  brick_grid:
    start_x: 65
    start_y: 60
    cols: 10
    rows: 5
    row_types:
      - brick_blue
      - brick_green
      - brick_yellow
      - brick_orange
      - brick_red
```

### Engine Changes
- `GameEngine._spawn_initial_entities()` reads `default_layout` from game_def
- If present, spawn entities from it instead of requiring override
- `_spawn_initial_entities()` becomes generic, not game-specific

---

## Phase 5: Transform System (replaces Attachment)

### Problem
Ball-paddle relationship is ad-hoc property manipulation. But "ball attached to paddle"
is really "paddle_ready entity that transforms into paddle + ball on input".

### Solution
Use the **transform** primitive from TRANSFORM_BEHAVIOUR.md:

```yaml
entity_types:
  paddle_ready:
    # A paddle with ball sitting on top - single entity
    behaviors: [paddle]
    render_as: [paddle, ball]  # skin draws both
    on_input:
      transform:
        into: paddle
        spawn:
          - type: ball
            offset: [0, -20]
            velocity_y: -300  # from ball.speed config

  paddle:
    behaviors: [paddle]

  ball:
    behaviors: [ball]
```

Ball returning after lost:
```yaml
lose_conditions:
  - entity_type: ball
    event: exited_screen
    edge: bottom
    action: lose_life
    then:
      destroy: ball
      transform:
        entity_type: paddle
        into: paddle_ready
```

### Why Transform > Attachment
- **One primitive** handles: paddle+ball, asteroid→alien, enemy→fragments, power-up→shield
- **No hidden state** - entities are what they are, not "attached" or "detached"
- **Clear lifecycle** - spawn, transform, destroy
- **Already designed** - see docs/planning/TRANSFORM_BEHAVIOUR.md

### Engine Changes
- Implement `transform` as core action (like collision actions)
- Transform can: change entity type, spawn children, set velocities
- Works from: on_hit, on_input, lose_conditions, win_conditions

### Benefit
- Ball attachment logic removed entirely
- Same system enables asteroid games, power-ups, multi-phase bosses
- "Ontological metamorphosis" as the doc says

---

## Phase 6: Clean Up BrickBreakerNGMode

After phases 1-5, the game mode becomes:

```python
class BrickBreakerNGMode(GameEngine):
    """BrickBreaker NG - fully data-driven brick breaker."""

    NAME = "Brick Breaker NG"
    DESCRIPTION = "Lua behavior-driven brick breaker"

    GAME_DEF_FILE = Path(__file__).parent / 'game.yaml'
    LEVELS_DIR = Path(__file__).parent / 'levels'

    ARGUMENTS = [
        {'name': '--lives', 'type': int, 'default': 3, 'help': 'Starting lives'},
    ]

    def _get_skin(self, skin_name: str) -> GameEngineSkin:
        return BrickBreakerNGSkin()

    def _create_level_loader(self) -> NGLevelLoader:
        return NGLevelLoader(self.LEVELS_DIR)
```

**That's it.** ~20 lines of game-specific code + skin.

---

## Implementation Order

Transform is the foundational primitive - implement it first and completely.

| Phase | Effort | Impact | Dependencies |
|-------|--------|--------|--------------|
| 1. Transform System | High | Very High | None |
| 2. Input Mapping | Medium | High | Transform |
| 3. Lose Conditions | Medium | High | Transform |
| 4. Default Layout | Low | Medium | None |
| 5. Cleanup | Low | High | Phases 1-4 |

**Order:** 1 → 2 → 3 → 4 → 5

Notes:
- **Transform first** - enables cleaner input_mapping and lose_conditions
- **Default layout is degenerate case** - just a level definition embedded in game.yaml
- **Ball Reset (Lua) removed** - transform handles paddle→paddle_ready, no reset needed

---

## Updated game.yaml (Target)

```yaml
name: "Brick Breaker NG"
screen_width: 800
screen_height: 600

win_condition: destroy_all
win_target_type: brick

lose_conditions:
  - entity_type: ball
    event: exited_screen
    edge: bottom
    action: lose_life
    then:
      destroy: ball
      transform:
        entity_type: paddle
        into: paddle_ready

input_mapping:
  paddle_ready:
    target_x: input.position.x
    on_input:
      transform:
        into: paddle
        spawn:
          - type: ball
            offset: [0, -20]
            velocity_y: -300
  paddle:
    target_x: input.position.x

collision_behaviors:
  ball:
    paddle:
      action: bounce_paddle
      modifier:
        max_angle: 60
    brick:
      action: bounce_reflect
      modifier:
        speed_increase: 5
  brick:
    ball:
      action: take_damage

entity_types:
  paddle_ready:
    # Paddle with ball on top - transforms on first input
    width: 120
    height: 35
    behaviors: [paddle]
    render_as: [paddle, ball]

  paddle:
    width: 120
    height: 15
    behaviors: [paddle]

  ball:
    width: 16
    height: 16
    behaviors: [ball]

  brick:
    width: 70
    height: 25
    behaviors: [brick]
    # ... color variants with extends

default_layout:
  entities:
    - type: paddle_ready
      x: 340
      y: 550
  brick_grid:
    start_x: 65
    start_y: 60
    cols: 10
    rows: 5
    row_types: [brick_blue, brick_green, brick_yellow, brick_orange, brick_red]

collisions:
  - [ball, paddle]
  - [ball, brick]
```

---

## Success Criteria

1. **BrickBreakerNGMode** has no game logic, only factory methods
2. **New brick breaker variant** requires only YAML changes
3. **New game type** requires only:
   - game.yaml
   - Optional: new Lua behaviors (if mechanics don't exist)
   - Optional: custom skin (if rendering differs)
   - Minimal Python (just the class definition pointing to YAML)

---

## Resolved Decisions

1. ~~**Input mapping syntax**~~ - Use `when: {property, value}` for conditions
2. ~~**Lose condition actions**~~ - Use events (`exited_screen`) + transform system
3. ~~**Default layout vs levels**~~ - Default layout is a degenerate case (level embedded in game.yaml)
4. ~~**Attachment system**~~ - Replaced with transform system
5. ~~**Scope**~~ - Transform first, implement completely
6. ~~**Transform complexity**~~ - Full implementation
