# Unified Interactions Guide

All entity interactions in AMS use a single declarative model. Collisions, input handling, screen bounds, timers, and lifecycle hooks are all just interactions between entities.

## Quick Start

```yaml
entity_types:
  ball:
    width: 16
    height: 16

    interactions:
      # Collision with brick
      brick:
        when:
          distance: 0
        action: bounce_reflect

      # Ball exits bottom of screen
      screen:
        edges: [bottom]
        action: ball_lost
```

## Core Concept

Every interaction is between two entities with a filter:

```
Interaction = (Entity A, Entity B, Filter, Action)
```

| What you want | Entity A | Entity B | Filter |
|---------------|----------|----------|--------|
| Collision | `ball` | `brick` | `distance: 0` |
| Click detection | `duck` | `pointer` | `distance: 0`, `b.active: true` |
| Proximity trigger | `player` | `enemy` | `distance: {lt: 100}` |
| Screen edge | `ball` | `screen` | `edges: [bottom]` |
| Spawn hook | `ball` | `level` | `because: enter` |
| Timer | `spawner` | `time` | `elapsed: {gte: 5.0}` |

## Syntax Reference

### Basic Interaction

```yaml
interactions:
  target_entity:
    when:
      # filter conditions
    because: enter    # when to fire (default: enter)
    action: action_name
    modifier:
      # config passed to action
```

### Filter Conditions (`when:`)

**Distance** - measures between entity bounds (0 = collision):
```yaml
when:
  distance: 0              # Exact collision
  distance: {lt: 100}      # Within 100 pixels
  distance: {between: [50, 150]}
```

**Distance modes** - where to measure from/to:
```yaml
when:
  distance: 0
  from: center    # Measure from A's center (default: edge)
  to: edge        # Measure to B's edge (default: edge)
```

**Angle** - direction from A to B (0=right, 90=up, 180=left, 270=down):
```yaml
when:
  angle: {between: [45, 135]}   # B is above A
```

**Entity attributes** - filter on A's or B's properties:
```yaml
when:
  a.ball_attached: true    # Entity A has ball_attached = true
  b.active: true           # Entity B has active = true
  b.health: {gt: 0}        # Entity B health > 0
```

**Filter operators:**
| Operator | Example | Meaning |
|----------|---------|---------|
| exact | `distance: 0` | Equals 0 |
| `lt` | `{lt: 100}` | Less than 100 |
| `gt` | `{gt: 0}` | Greater than 0 |
| `lte` | `{lte: 100}` | Less than or equal |
| `gte` | `{gte: 50}` | Greater than or equal |
| `between` | `{between: [45, 135]}` | In range [45, 135] |
| `in` | `{in: [a, b, c]}` | In set |

### Trigger Modes (`because:`)

Controls when the action fires:

| Mode | Fires | Use case |
|------|-------|----------|
| `enter` | Once when filter becomes true | Collisions, click events |
| `exit` | Once when filter becomes false | Leave proximity, release |
| `continuous` | Every frame while true | Position tracking, physics |

```yaml
# Default - fires once on collision
brick:
  when:
    distance: 0
  action: bounce          # because: enter is default

# Fires every frame while touching
danger_zone:
  when:
    distance: 0
  because: continuous
  action: take_damage

# Fires when leaving proximity
safe_zone:
  when:
    distance: {lt: 100}
  because: exit
  action: trigger_alarm
```

### Multiple Interactions (Array Syntax)

When an entity has multiple interactions with the same target:

```yaml
interactions:
  screen:
    - edges: [bottom]
      action: ball_lost

    - edges: [left, right]
      action: bounce_horizontal

    - edges: [top]
      action: bounce_vertical
```

### Screen Edge Shorthand

The `edges:` key is sugar for angle-based collision with screen:

```yaml
screen:
  edges: [bottom]      # Ball moving downward hits bottom
  action: ball_lost
```

Edges expand to angle filters:
| Edge | Angle range | Ball moving... |
|------|-------------|----------------|
| `top` | 225-315 | downward |
| `bottom` | 45-135 | upward |
| `left` | 315-360, 0-45 | rightward |
| `right` | 135-225 | leftward |

## System Entities

Five system entities are always available:

### `pointer` - Input position

```yaml
interactions:
  pointer:
    when:
      distance: 0
      b.active: true      # Click/tap occurred
    action: hit_target
```

Pointer attributes:
- `x`, `y` - position
- `width`, `height` - bounds (varies by input type)
- `active` - true during click/tap
- `input_type` - mouse, touch, object, laser

### `screen` - Play area bounds

```yaml
interactions:
  screen:
    edges: [bottom]
    action: lose_life
```

### `level` - Lifecycle hooks

```yaml
interactions:
  level:
    because: enter        # on_spawn
    action: initialize

  level:
    because: continuous   # on_update
    action: apply_physics

  level:
    because: exit         # on_destroy
    action: spawn_particles
```

### `game` - Game state

```yaml
interactions:
  game:
    when:
      b.lives: 0
    action: game_over
```

Game attributes: `lives`, `score`, `state` (playing/paused/won/lost)

### `time` - Timer-based interactions

```yaml
interactions:
  time:
    when:
      elapsed: {gte: 5.0}    # 5 seconds since spawn
    action: spawn_enemy
```

Time attributes:
- `elapsed` - seconds since entity spawned
- `absolute` - seconds since level started

## Examples

### Brick Breaker Ball

```yaml
ball:
  width: 16
  height: 16

  interactions:
    # Bounce off paddle
    paddle:
      when:
        distance: 0
      action: bounce_paddle
      modifier:
        max_angle: 60

    # Bounce off and damage brick
    brick:
      when:
        distance: 0
      action: bounce_reflect
      modifier:
        speed_increase: 5

    # Screen edges
    screen:
      - edges: [bottom]
        action: ball_lost

      - edges: [left, right, top]
        action: bounce_reflect
```

### Clickable Target (Duck Hunt)

```yaml
duck:
  width: 50
  height: 50
  properties:
    points: 100

  interactions:
    pointer:
      when:
        distance: 0
        b.active: true
      action: hit_target
      modifier:
        sound: quack
```

### Paddle with Ball Attachment

```yaml
paddle:
  width: 120
  height: 15
  properties:
    ball_attached: false

  interactions:
    # Track pointer position
    pointer:
      because: continuous
      action: track_pointer_x

    # Launch ball on click (only if attached)
    pointer:
      when:
        b.active: true
        a.ball_attached: true
      action: launch_ball
      modifier:
        angle_range: [-120, -60]
        speed: 300
```

### Proximity Alert

```yaml
player:
  interactions:
    enemy:
      when:
        distance: {lt: 100}
      because: enter
      action: trigger_alert

    enemy:
      when:
        distance: {lt: 100}
      because: exit
      action: clear_alert
```

### One-Shot Timer

```yaml
powerup:
  interactions:
    time:
      when:
        elapsed: {gte: 10.0}    # 10 seconds after spawn
      action: expire_powerup    # Fires once, then never again
```

### Repeating Timer (Interval)

Transform to same type resets all state, including elapsed time:

```yaml
enemy_spawner:
  interactions:
    time:
      when:
        elapsed: {gte: 3.0}
      action: spawn_and_restart

# Action does:
#   ams.spawn("enemy", x, y)
#   ams.transform(entity_id, "enemy_spawner")  -- resets elapsed to 0
```

## Action Handlers

Actions are Lua scripts in `lua/interaction_action/` that receive the interacting entities, user config, and runtime context as separate arguments:

```lua
-- lua/interaction_action/bounce_reflect.lua.yaml
description: Ball bounces off brick with reflection
lua: |
  local action = {}

  function action.execute(entity_id, other_id, modifier, context)
    -- context contains: trigger, target, target_x, target_y, target_active, distance, angle
    local speed_increase = modifier.speed_increase or 0

    -- Reflect based on collision angle
    local angle = context.angle or 0
    if angle > 45 and angle < 135 then
        ams.set_vy(entity_id, -ams.get_vy(entity_id))
    else
        ams.set_vx(entity_id, -ams.get_vx(entity_id))
    end

    -- Apply speed boost
    local vx = ams.get_vx(entity_id)
    local vy = ams.get_vy(entity_id)
    local speed = math.sqrt(vx * vx + vy * vy)
    local new_speed = speed + speed_increase
    local scale = new_speed / speed
    ams.set_vx(entity_id, vx * scale)
    ams.set_vy(entity_id, vy * scale)
  end

  return action
```

### Function Signature

```lua
function action.execute(entity_id, other_id, modifier, context)
```

| Argument | Description |
|----------|-------------|
| `entity_id` | ID of entity A (the one with the interaction defined) |
| `other_id` | ID of entity B (the target entity) |
| `modifier` | User-defined config from YAML `modifier:` block |
| `context` | Runtime context computed by the interaction engine |

### Modifier (User Config)

The `modifier` table contains values from the YAML definition:

```yaml
action: bounce_reflect
modifier:
  speed_increase: 5
  max_speed: 600
```

### Context (Runtime Data)

The `context` table contains computed interaction data:

| Field | Description |
|-------|-------------|
| `trigger` | Trigger mode: "enter", "exit", or "continuous" |
| `target` | Target entity type name |
| `target_x` | Entity B's x position |
| `target_y` | Entity B's y position |
| `target_active` | Entity B's active state (for pointer) |
| `distance` | Computed distance between entities |
| `angle` | Angle from A to B (degrees) |

## Migration from Legacy Systems

| Old System | New Unified |
|------------|-------------|
| `collision_behaviors.ball.brick` | `interactions.ball.brick` |
| `on_hit` behavior | `pointer` interaction with `b.active: true` |
| `lose_conditions[ball exited bottom]` | `screen` interaction with `edges: [bottom]` |
| `input_mapping.target_x` | `pointer` interaction with `because: continuous` |
| `behaviors.on_spawn` | `level` interaction with `because: enter` |
| `behaviors.on_update` | `level` interaction with `because: continuous` |
