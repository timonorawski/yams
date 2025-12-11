# Game Engine Architecture

## Overview

The AMS Game Engine enables fully data-driven arcade games. Games are defined by YAML configuration and Lua behaviors—no Python code required for game logic.

```
┌─────────────────────────────────────────────────────────────┐
│                      YAML Game Definition                    │
│         Entity types, collisions, input mapping, etc.        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Game Engine (Python)                    │
│   Loads config, manages entities, runs game loop, renders    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Behavior Engine (Lua VM)                  │
│      Executes behaviors, collision actions, expressions      │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Games are data, not code.** A new game variant should require only YAML and assets.
2. **All behaviors run in Lua.** No privileged Python code path for game logic.
3. **Explicit over implicit.** Lua expressions use `{lua: "..."}` syntax.
4. **Engine is behavior-agnostic.** The engine doesn't know what "ball" or "paddle" means.

### The Minimal Game Mode

A fully data-driven game mode is just a YAML loader shim:

```python
class BrickBreakerNGSkin(GameEngineSkin):
    """All rendering is YAML-driven via game.yaml render commands."""
    pass  # All rendering handled by base class


class BrickBreakerNGMode(GameEngine):
    NAME = _GAME_META['name']           # From game.yaml
    DESCRIPTION = _GAME_META['description']
    VERSION = _GAME_META['version']
    AUTHOR = _GAME_META['author']

    GAME_DEF_FILE = Path(__file__).parent / 'game.yaml'
    LEVELS_DIR = Path(__file__).parent / 'levels'

    def _get_skin(self, _skin_name: str) -> GameEngineSkin:
        return BrickBreakerNGSkin()

    def _create_level_loader(self) -> NGLevelLoader:
        return NGLevelLoader(self.LEVELS_DIR)

    # ALL game logic is declarative in game.yaml:
    # - player spawn: player.type + player.spawn
    # - input mapping: input_mapping section
    # - collision behaviors: collision_behaviors section
    # - lose conditions: lose_conditions section
    # - win conditions: win_target_type
```

## YAML Game Definition

A game is defined by a `game.yaml` file with these sections.

**JSON Schema validation is available** at `schemas/game.schema.json` and `schemas/level.schema.json`. Add the schema reference to enable IDE validation:

```yaml
# yaml-language-server: $schema=../../schemas/game.schema.json
```

### Basic Structure

```yaml
# yaml-language-server: $schema=../../schemas/game.schema.json
name: "Brick Breaker NG"
description: "Lua behavior-driven brick breaker"
version: "1.0.0"
author: "AMS Team"

screen_width: 800
screen_height: 600
background_color: [20, 20, 30]

# Default settings (accessible via CLI)
defaults:
  lives: 3

# Win condition
win_condition: destroy_all
win_target_type: brick  # Entity base type to destroy
lose_on_player_death: true

# Entity type definitions
entity_types:
  # ...

# Collision rules (detection)
collisions:
  # ...

# Collision behavior handlers (what happens)
collision_behaviors:
  # ...

# Input handling
input_mapping:
  # ...

# Lose conditions
lose_conditions:
  # ...

# Player spawn config
player:
  type: paddle_ready
  spawn: [340, 550]

# Default layout (used when no level specified)
default_layout:
  brick_grid:
    start_x: 65
    start_y: 60
    cols: 10
    rows: 5
    row_types: [brick_blue, brick_green, brick_yellow, brick_orange, brick_red]

# Assets (sounds, sprites)
assets:
  sounds:
    paddle_hit: sounds/paddle_hit.wav
    wall_bounce: sounds/wall_bounce.wav
    brick_hit: sounds/brick_hit.wav
    brick_break: sounds/brick_break.wav
    shoot: sounds/shoot.wav
    player_hit: sounds/player_hit.wav
  sprites: {}
```

### Assets

The `assets` section maps sound and sprite names to file paths. All asset references in Lua behaviors resolve through this mapping—no hardcoded paths in the engine.

```yaml
assets:
  sounds:
    # Sound name -> path (relative to assets/ directory)
    paddle_hit: sounds/paddle_hit.wav
    brick_hit: sounds/brick_hit.wav

  sprites:
    # Simple image file
    paddle: sprites/paddle.png

    # With transparency color key
    ball:
      file: sprites/ball.png
      transparent: [255, 0, 255]  # Magenta = transparent

    # Sprite sheet region
    duck_flying:
      file: sprites/ducks.png
      x: 0
      y: 126
      width: 37
      height: 42
      transparent: [159, 227, 163]  # Light green
```

#### Sprite Formats

| Format | Fields | Description |
|--------|--------|-------------|
| Simple path | `name: path` | Load full image |
| With transparency | `file`, `transparent` | Image with color key |
| Sheet region | `file`, `x`, `y`, `width`, `height`, `transparent` | Extract region from sprite sheet |
| Data URI | `data: "data:image/png;base64,..."` | Embedded base64 image |
| File reference | `file: "@name"` | Reference to `assets.files.name` |

The `transparent` field is an RGB array `[r, g, b]` - that color becomes transparent.

#### Data URIs for Self-Contained Games

Assets can be embedded directly in game.yaml using data URIs:

```yaml
assets:
  sprites:
    # Embedded PNG (base64)
    ball:
      data: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAA..."
      transparent: [255, 0, 255]

  sounds:
    # Embedded WAV (base64)
    hit: "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEA..."
```

This makes game.yaml fully self-contained—no external asset files needed.
Files get large but enable single-file distribution.

#### Shared File References

When multiple sprites use the same sprite sheet, use the `files:` dict to avoid duplicating embedded data:

```yaml
assets:
  # Shared file references (name -> path or data URI)
  files:
    ducks_sheet: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
    # Or file path: ducks_sheet: sprites/ducks.png

  sprites:
    # Reference shared file with @ prefix
    duck_flying:
      file: "@ducks_sheet"      # Resolves to files.ducks_sheet
      x: 0
      y: 126
      width: 37
      height: 42
      transparent: [159, 227, 163]

    duck_hit:
      file: "@ducks_sheet"      # Same sheet, different region
      x: 216
      y: 126
      width: 35
      height: 42
      transparent: [159, 227, 163]

    duck_falling:
      file: "@ducks_sheet"
      x: 300
      y: 126
      width: 37
      height: 42
      transparent: [159, 227, 163]

  sounds:
    # Sounds can also use @references
    quack: "@quack_sound"
```

The `@` prefix tells the engine to look up the value in `assets.files`. This:
- Avoids embedding the same sprite sheet multiple times
- Allows switching between embedded and file-based assets easily
- Keeps the YAML readable when using large data URIs

When loading, sprites sharing the same source are efficiently cached—the image is only decoded once regardless of how many sprites reference it.

#### How It Works

1. **Lua calls `ams.play_sound("paddle_hit")`**
2. **Engine looks up `"paddle_hit"` in `assets.sounds`**
3. **Resolves path relative to `games/YourGame/assets/`**
4. **Plays `games/YourGame/assets/sounds/paddle_hit.wav`**

#### Standard Sound Names

These sound names are used by the built-in Lua behaviors:

| Sound Name | Used By | When |
|------------|---------|------|
| `paddle_hit` | `bounce_paddle.lua` | Ball bounces off paddle |
| `wall_bounce` | `ball.lua` | Ball bounces off wall |
| `brick_hit` | `take_damage.lua` | Brick takes damage but survives |
| `brick_break` | `take_damage.lua` | Brick is destroyed |
| `shoot` | `shoot.lua` | Entity fires projectile |
| `player_hit` | `hit_player.lua` | Player takes damage |

Games can add custom sounds for custom behaviors. The engine silently ignores sounds that aren't mapped (no crash if sound file missing).

#### Directory Structure

```
games/YourGame/
├── game.yaml
├── assets/
│   ├── sounds/
│   │   ├── paddle_hit.wav
│   │   ├── brick_break.wav
│   │   └── ...
│   └── sprites/
│       ├── paddle.png
│       └── ...
└── levels/
```

### Entity Types

Entity types define the building blocks of your game.

```yaml
entity_types:
  # Base paddle type
  paddle:
    width: 120
    height: 15
    color: blue
    behaviors: [paddle]
    behavior_config:
      paddle:
        speed: 500
        stop_threshold: 1.0
    tags: [player]
    render:
      - shape: rectangle
        color: blue
        fill: true
      - shape: rectangle
        color: white
        fill: false
        line_width: 2

  # Paddle with ball attached (extends paddle)
  paddle_ready:
    extends: paddle
    tags: [player]
    render:
      - shape: rectangle
        color: blue
        fill: true
      - shape: rectangle
        color: white
        fill: false
        line_width: 2
      - shape: circle
        color: white
        fill: true
        offset: [52, -20]
        size: [16, 16]

  # Ball entity
  ball:
    width: 16
    height: 16
    color: white
    behaviors: [ball]
    behavior_config:
      ball:
        speed: 300
        max_speed: 600
        speed_increase: 5
    tags: [ball]
    render:
      - shape: circle
        color: white
        fill: true

  # Base brick type
  brick:
    width: 70
    height: 25
    color: gray
    behaviors: [brick]
    behavior_config:
      brick:
        hits: 1
        points: 100
    tags: [enemy, brick]
    render:
      - shape: rectangle
        color: $color
        fill: true
      - shape: rectangle
        color: white
        fill: false
        line_width: 1
      # Damage overlay for multi-hit bricks
      - shape: rectangle
        color: black
        fill: true
        alpha: $damage_ratio
        when:
          property: brick_max_hits
          compare: greater_than
          value: 1
      # Hit count text
      - shape: text
        text: $brick_hits_remaining
        color: white
        font_size: 20
        align: center
        when:
          property: brick_max_hits
          compare: greater_than
          value: 1

  # Colored brick variants
  brick_red:
    extends: brick
    color: red
    behavior_config:
      brick:
        points: 500

  # Multi-hit brick
  brick_silver:
    extends: brick
    color: silver
    behavior_config:
      brick:
        hits: 3
        points: 400

  # Space Invaders style brick with multiple behaviors
  invader_shooter:
    extends: brick
    color: purple
    behaviors: [brick, descend, shoot]  # File-based behaviors
    behavior_config:
      brick:
        hits: 2
        points: 500
      descend:
        speed: 10
        pattern: fixed
      shoot:
        interval: 3.0
        projectile_speed: 200
        direction: down
    tags: [enemy, brick, shooter]
    render:
      - shape: rectangle
        color: $color
        fill: true
      - shape: rectangle
        color: white
        fill: false
        line_width: 1
      # Triangle indicator pointing down
      - shape: triangle
        color: yellow
        fill: true
        points: [[0.3, 0.8], [0.7, 0.8], [0.5, 1.3]]

  # Projectile
  projectile:
    width: 8
    height: 8
    color: red
    behaviors: [projectile]
    tags: [projectile, hazard]
    render:
      - shape: circle
        color: red
        fill: true

  # Indestructible brick
  brick_indestructible:
    width: 70
    height: 25
    color: white
    behaviors: [brick]
    behavior_config:
      brick:
        hits: 1
        indestructible: true
        points: 0
    tags: [brick]  # No 'enemy' tag - won't count for win
    render:
      - shape: rectangle
        color: $color
        fill: true
      - shape: line
        color: gray
        line_width: 2
        points: [[0.1, 0.1], [0.9, 0.9]]
      - shape: line
        color: gray
        line_width: 2
        points: [[0.9, 0.1], [0.1, 0.9]]
```

#### Entity Type Fields

| Field | Type | Description |
|-------|------|-------------|
| `extends` | string | Parent type to inherit from |
| `width`, `height` | number | Entity dimensions |
| `color` | string | Render color (for geometric skin) |
| `sprite` | string | Sprite filename (for classic skin) |
| `behaviors` | list | Lua behaviors to attach |
| `behavior_config` | dict | Per-behavior configuration |
| `health` | number | Hit points (default: 1) |
| `points` | number | Score on destroy |
| `tags` | list | Tags for grouping/queries |
| `render` | list | Render commands (see Rendering) |

#### Inheritance

Types with `extends` inherit all fields from the parent. Child values override parent values. `behavior_config` is merged (child overrides parent keys). `render` is inherited only if child doesn't define its own.

The engine tracks `base_type` for collision matching and win conditions—`brick_red` has `base_type: brick`.

### Rendering

Entities are rendered using declarative render commands. Each entity type can define a list of render primitives.

#### Render Command Fields

| Field | Type | Description |
|-------|------|-------------|
| `shape` | string | Primitive: `rectangle`, `circle`, `triangle`, `polygon`, `line`, `sprite`, `text` |
| `color` | string | Color name or `$color` to use entity.color |
| `fill` | bool | Fill shape (true) or outline only (false) |
| `line_width` | int | Outline/stroke width in pixels |
| `alpha` | any | Opacity: 0-1 float, `$property`, or `{lua: expr}` |
| `points` | list | Normalized (0-1) coordinates for polygon/triangle/line |
| `offset` | [x, y] | Offset from entity position |
| `size` | [w, h] | Override entity dimensions |
| `radius` | float | For circle, normalized to entity size |
| `sprite` | string | Sprite filename (for sprite shape) |
| `text` | string | Text content or `$property` reference (for text shape) |
| `font_size` | int | Font size in pixels (default: 20) |
| `align` | string | Text alignment: `center`, `left`, `right` |
| `when` | object | Conditional rendering (see below) |

#### Conditional Rendering

The `when:` field enables conditional render layers:

```yaml
render:
  # Only show for multi-hit bricks
  - shape: text
    text: $brick_hits_remaining
    color: white
    when:
      property: brick_max_hits
      compare: greater_than
      value: 1
```

| Field | Description |
|-------|-------------|
| `property` | Property name to check |
| `value` | Value to compare against |
| `compare` | Comparison: `equals` (default), `not_equals`, `greater_than`, `less_than` |

#### Color and Property References

- `$color` - Use the entity's `color` field
- `$property_name` - Use value from entity.properties
- Any color name - Direct color (red, blue, white, gray, silver, cyan, purple, orange, yellow, green)

#### Computed Properties

Built-in computed properties available via `$name`:

| Property | Description |
|----------|-------------|
| `$damage_ratio` | `(max_hits - hits_remaining) / max_hits` (0-1, 0 when undamaged) |
| `$health_ratio` | `health / max_health` (0-1, 1 when full health) |
| `$alive` | Boolean, whether entity is alive |

#### Coordinate System

Points for `polygon`, `triangle`, and `line` use normalized coordinates (0-1):
- `[0, 0]` = top-left of entity bounds
- `[1, 1]` = bottom-right of entity bounds
- `[0.5, 0.5]` = center of entity

Points can extend beyond 0-1 for indicators that extend outside the entity bounds.

#### Layering

Render commands are drawn in order. Later commands appear on top.

### Collisions

Collisions are declared in two parts: which types collide (detection), and what happens (behavior).

```yaml
# Which entity types can collide (detection only)
collisions:
  - [ball, paddle]
  - [ball, brick]       # Also matches brick_red, invader, etc. via base_type
  - [projectile, paddle]

# What happens on collision (actions)
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
        max_speed: 600

  brick:
    ball:
      action: take_damage
      modifier:
        amount: 1

  projectile:
    paddle:
      action: hit_player
      modifier:
        play_sound: player_hit
```

The `collisions` list defines which type pairs the engine checks for overlap. The `collision_behaviors` section defines what action to execute when collision is detected.

Both sides of a collision can have separate actions. When ball hits brick: `ball->brick` triggers `bounce_reflect`, and `brick->ball` triggers `take_damage`.

Collision behaviors use `base_type` matching—a rule for `brick` matches `brick_red`, `invader_shooter`, etc.

### Input Mapping

Input mapping connects player input to entity behavior.

```yaml
input_mapping:
  # Simple: set property from input position
  paddle:
    target_x: paddle_target_x

  # Complex: transform entity on input
  paddle_ready:
    target_x: paddle_target_x
    on_input:
      transform:
        into: paddle
        spawn:
          - type: ball
            offset: [52, -20]
            speed: 300
            angle:
              lua: ams.random_range(-120, -60)
```

#### Input Mapping Fields

| Field | Type | Description |
|-------|------|-------------|
| `target_x` | string | Property to set from `input.position.x` |
| `target_y` | string | Property to set from `input.position.y` |
| `on_input.transform` | object | Transform entity on input |
| `on_input.when` | object | Condition for action |

### Transform System

Transform is the core primitive for entity metamorphosis—an entity becomes something fundamentally different, or is destroyed while spawning children.

```yaml
input_mapping:
  paddle_ready:
    on_input:
      transform:
        type: paddle             # Transform into this type
        children:                # Spawn children at same position
          - type: ball
            offset: [52, -20]    # Relative to parent
            speed: 300           # Spawn property (Lua reads on_spawn)
            angle:
              lua: ams.random_range(-120, -60)
```

#### Transform Types

| `type` Value | Behavior |
|--------------|----------|
| `"destroy"` | Spawn children only, destroy parent entity |
| `"<entity_type>"` | Transform into type, optionally spawn children |

#### Spawn Child Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | required | Entity type to spawn |
| `offset` | [x, y] | [0, 0] | Position relative to parent |
| `count` | int | 1 | Number to spawn (with `i` in Lua scope) |
| `inherit_velocity` | float | 0.0 | Fraction of parent velocity to add |
| `lifetime` | float | null | Auto-set on spawned entity |
| `$property` | any | - | Reference parent property (e.g., `$color`) |
| `{lua: ...}` | any | - | Dynamic value evaluated at spawn |
| `{call: ...}` | any | - | Generator script call (see below) |

### Dynamic Property Values

Property values throughout YAML can use three evaluation methods:

#### Literal Values

Simple values used as-is:

```yaml
speed: 300
color: red
offset: [10, 20]
```

#### Lua Expressions

Inline Lua for one-off calculations. Use `{lua: "expression"}`:

```yaml
angle: {lua: "ams.random_range(-120, -60)"}
vx: {lua: "ams.random_range(-100, 100)"}
```

The `ams.*` API is available in expressions.

#### Multiline Lua Blocks

For complex logic with local variables, use YAML multiline syntax:

```yaml
# Win condition: all bricks destroyed
win_condition:
  lua: |
    local count = ams.count_entities_by_tag("brick")
    return count == 0

# Score-based win
win_condition:
  lua: |
    local score = ams.get_score()
    local time = ams.get_time()
    return score >= 10000 or time >= 60

# Complex spawn velocity calculation
vx:
  lua: |
    local angle = ams.random_range(30, 150)
    local speed = 200
    return speed * ams.cos(angle * 3.14159 / 180)
```

Multiline blocks are wrapped in an anonymous function, so:

- Use `local` for variables
- Include `return` to provide the result
- Full Lua syntax is available (if/else, loops, etc.)

#### Generator Scripts

For complex/reusable computations. Use `{call: "script", args: {...}}`:

```yaml
# Calculate grid position from indices
x: {call: "grid_position", args: {index: 5, start: 65, spacing: 75}}

# Blend colors dynamically
color: {call: "color_blend", args: {from: "red", to: "yellow", factor: 0.5}}

# Args can contain nested Lua expressions
x: {call: "grid_position", args: {
  index: {lua: "ams.random(1, 10)"},
  start: 100,
  spacing: 50
}}
```

#### Generator Script Structure

Generators live in `ams/behaviors/generators/` and expose a `generate(args)` function:

```lua
-- grid_position.lua
local grid_position = {}

function grid_position.generate(args)
    local index = args.index or 0
    local start = args.start or 0
    local spacing = args.spacing or 0
    return start + (index * spacing)
end

return grid_position
```

Built-in generators:

- `grid_position` - Calculate pixel position from grid coordinates
- `color_blend` - Interpolate between two colors

### Lifecycle Transforms

Entity types can define transforms that trigger on spawn or destruction.

```yaml
entity_types:
  brick:
    # Spawn particles when destroyed
    on_destroy:
      type: destroy
      children:
        - type: particle
          count: 4
          offset: [35, 12]        # Center of brick
          vx: {lua: "ams.random_range(-100, 100)"}
          vy: {lua: "ams.random_range(-150, -50)"}
          color: $color           # Inherit parent's color

    # Conditional transforms during update
    on_update:
      - when:
          age: [0.4, null]        # After 0.4 seconds
        transform:
          type: destroy           # Auto-destroy
```

#### on_destroy

Triggers when entity is destroyed. Only spawns children (parent is already being destroyed).

#### on_update

List of conditional transforms checked each frame. Each entry has:

| Field | Type | Description |
|-------|------|-------------|
| `when.age` | [min, max] | Age range in seconds (`null` = unbounded) |
| `when.property` | string | Property name to check |
| `when.value` | any | Expected property value |
| `when.interval` | float | Repeat every N seconds |
| `transform` | object | Transform to apply when condition met |

#### Computed Properties for Conditions

| Property | Description |
|----------|-------------|
| `$age` | Seconds since entity spawned |
| `$damage_ratio` | 0 to 1, based on hits taken |
| `$health_ratio` | 0 to 1, based on remaining health |
| `$alive` | Boolean, whether entity is alive |

Lifecycle transforms are inherited via `extends`

### Lose Conditions

Lose conditions define what causes life loss and how to recover.

```yaml
lose_conditions:
  # Ball exits screen
  - entity_type: ball
    event: exited_screen
    edge: bottom
    action: lose_life
    then:
      destroy: ball
      transform:
        entity_type: paddle
        type: paddle_ready      # Transform paddle back to ready state

  # Projectile hits paddle (via property set by collision action)
  - entity_type: paddle
    event: property_true
    property: was_hit
    action: lose_life
    then:
      clear_property: was_hit
      destroy: ball
      transform:
        entity_type: paddle
        type: paddle_ready
```

#### Lose Condition Fields

| Field | Type | Description |
|-------|------|-------------|
| `entity_type` | string | Entity type to watch |
| `event` | string | `exited_screen` or `property_true` |
| `edge` | string | For exited_screen: `bottom`, `top`, `left`, `right`, `any` |
| `property` | string | For property_true: property name to check |
| `action` | string | `lose_life` |
| `then.destroy` | string | Entity type to destroy |
| `then.transform.entity_type` | string | Which entity type to transform |
| `then.transform.type` | string | Transform into this type |
| `then.transform.children` | array | Entities to spawn during transform |
| `then.clear_property` | string | Property to set to false after action |

### Win Conditions

Win conditions are defined at the top level:

```yaml
win_condition: destroy_all    # or: reach_score, survive_time
win_target_type: brick        # For destroy_all: base type to destroy
win_target: 10000             # For reach_score: target score
lose_on_player_death: true    # Game over when lives reach 0
```

For `destroy_all`, the engine counts entities whose `base_type` matches `win_target_type`. Entities without the `enemy` tag (like `brick_indestructible`) don't count.

## Lua Behaviors

Behaviors are Lua scripts that define entity logic. They can be:

1. **File-based**: Scripts in `ams/behaviors/lua/` (for reusable behaviors)
2. **Inline**: Lua code embedded directly in game.yaml (for rapid prototyping)

### Inline Behaviors

For quick prototyping, define behaviors directly in YAML:

```yaml
entity_types:
  wobbling_brick:
    extends: brick
    behaviors:
      - brick                    # File-based (brick.lua)
      - lua: |                   # Inline Lua
          local wobble = {}
          function wobble.on_update(entity_id, dt)
              local t = ams.get_time()
              local base_x = ams.get_prop(entity_id, "start_x") or ams.get_x(entity_id)
              if not ams.get_prop(entity_id, "start_x") then
                  ams.set_prop(entity_id, "start_x", base_x)
              end
              ams.set_x(entity_id, base_x + math.sin(t * 3) * 5)
          end
          return wobble
```

Inline behaviors have full access to the `ams.*` API, identical to file-based behaviors.
When a behavior is reused across multiple entity types, promote it to a file.

### Available Behaviors

| Behavior | Description |
|----------|-------------|
| `paddle` | Stopping paddle that slides to target_x position |
| `ball` | Movement, wall bouncing, speed management |
| `brick` | Hit tracking, multi-hit support, destruction |
| `projectile` | Move according to velocity, destroy when off-screen |
| `shoot` | Fire projectiles at intervals |
| `descend` | Move downward (patterns: fixed, step, wave) |
| `oscillate` | Move side-to-side within a range |

### Lifecycle Events

```lua
local my_behavior = {}

function my_behavior.on_spawn(entity_id)
    -- Called when entity is created
    -- Initialize properties, read spawn properties
end

function my_behavior.on_update(entity_id, dt)
    -- Called every frame
    -- dt is delta time in seconds
end

function my_behavior.on_hit(entity_id, other_id, other_type, other_base_type)
    -- Called on collision (legacy - prefer collision_actions)
end

function my_behavior.on_destroy(entity_id)
    -- Called when entity is destroyed
end

return my_behavior
```

### The `ams` API

Behaviors interact with the game through the `ams` namespace:

#### Entity Properties

```lua
-- Position
ams.get_x(id), ams.set_x(id, value)
ams.get_y(id), ams.set_y(id, value)

-- Velocity
ams.get_vx(id), ams.set_vx(id, value)
ams.get_vy(id), ams.set_vy(id, value)

-- Size (read-only)
ams.get_width(id), ams.get_height(id)

-- Health
ams.get_health(id), ams.set_health(id, value)

-- Visual
ams.get_sprite(id), ams.set_sprite(id, value)
ams.get_color(id), ams.set_color(id, value)

-- State
ams.is_alive(id)
ams.destroy(id)
```

#### Custom Properties

```lua
-- Get/set arbitrary properties
ams.get_prop(id, "my_property")
ams.set_prop(id, "my_property", value)

-- Get behavior config from YAML
-- Returns config[behavior_name][key] or default_value
ams.get_config(id, "behavior_name", "key", default_value)
```

#### Spawning

```lua
-- Spawn new entity, returns entity ID
-- If GameEngine has spawn callback, applies entity type config from game.yaml
local new_id = ams.spawn(type, x, y, vx, vy, width, height, color, sprite)
```

#### Queries

```lua
-- Get entity IDs by type
local ids = ams.get_entities_of_type("brick")

-- Get entity IDs by tag
local enemies = ams.get_entities_by_tag("enemy")

-- Count entities by tag (useful for win conditions)
local brick_count = ams.count_entities_by_tag("brick")

-- Get all entity IDs
local all_ids = ams.get_all_entity_ids()
```

#### Game State

```lua
ams.get_screen_width()
ams.get_screen_height()
ams.get_score()
ams.add_score(points)
ams.get_time()  -- Elapsed game time in seconds
```

#### Events

```lua
ams.play_sound("hit")  -- Queued for game layer to play
ams.schedule(delay_seconds, "callback_name", entity_id)
```

#### Math Utilities

```lua
ams.sin(radians), ams.cos(radians)
ams.sqrt(value)
ams.atan2(y, x)
ams.random()              -- 0.0 to 1.0
ams.random_range(min, max)
ams.clamp(value, min, max)
```

#### Debug

```lua
ams.log("message")
```

### Behavior Examples

#### paddle.lua

```lua
--[[
paddle behavior - stopping paddle that slides to target position

Properties used:
  paddle_target_x: Target X position (set by game on input)

Config options:
  speed: float - pixels per second (default: 500)
  stop_threshold: float - distance to consider "reached" (default: 1.0)
]]

local paddle = {}

function paddle.on_spawn(entity_id)
    local x = ams.get_x(entity_id)
    local width = ams.get_width(entity_id)
    ams.set_prop(entity_id, "paddle_target_x", x + width / 2)
end

function paddle.on_update(entity_id, dt)
    local speed = ams.get_config(entity_id, "paddle", "speed", 500)
    local threshold = ams.get_config(entity_id, "paddle", "stop_threshold", 1.0)

    local x = ams.get_x(entity_id)
    local width = ams.get_width(entity_id)
    local center_x = x + width / 2
    local target_x = ams.get_prop(entity_id, "paddle_target_x") or center_x

    local distance = target_x - center_x
    if math.abs(distance) <= threshold then return end

    local direction = distance > 0 and 1 or -1
    local move_amount = speed * dt

    if math.abs(distance) < move_amount then
        ams.set_x(entity_id, target_x - width / 2)
    else
        ams.set_x(entity_id, x + direction * move_amount)
    end

    -- Clamp to screen
    local screen_w = ams.get_screen_width()
    local new_x = ams.get_x(entity_id)
    if new_x < 0 then ams.set_x(entity_id, 0)
    elseif new_x + width > screen_w then ams.set_x(entity_id, screen_w - width) end
end

return paddle
```

#### ball.lua

```lua
--[[
ball behavior - bouncing ball with velocity

Properties used:
  ball_speed: float - current speed magnitude
  speed, angle: spawn properties for initial velocity

Config options:
  speed: float - initial speed (default: 300)
  max_speed: float - maximum speed (default: 600)
  speed_increase: float - speed added per brick hit (default: 5)
]]

local ball = {}

function ball.on_spawn(entity_id)
    ams.set_prop(entity_id, "ball_speed", ams.get_config(entity_id, "ball", "speed", 300))

    -- If spawned with speed+angle properties, compute velocity
    local speed = ams.get_prop(entity_id, "speed")
    local angle = ams.get_prop(entity_id, "angle")

    if speed and angle then
        local angle_rad = angle * 3.14159 / 180
        ams.set_vx(entity_id, speed * ams.cos(angle_rad))
        ams.set_vy(entity_id, speed * ams.sin(angle_rad))
        ams.set_prop(entity_id, "ball_speed", speed)
        ams.set_prop(entity_id, "speed", nil)
        ams.set_prop(entity_id, "angle", nil)
    end
end

function ball.on_update(entity_id, dt)
    local vx = ams.get_vx(entity_id)
    local vy = ams.get_vy(entity_id)
    if vx == 0 and vy == 0 then return end

    -- Move
    local x = ams.get_x(entity_id) + vx * dt
    local y = ams.get_y(entity_id) + vy * dt
    ams.set_x(entity_id, x)
    ams.set_y(entity_id, y)

    -- Wall bouncing
    local w = ams.get_width(entity_id)
    local h = ams.get_height(entity_id)
    local screen_w = ams.get_screen_width()

    if x < 0 then
        ams.set_x(entity_id, 0)
        ams.set_vx(entity_id, -vx)
        ams.play_sound("wall_bounce")
    elseif x + w > screen_w then
        ams.set_x(entity_id, screen_w - w)
        ams.set_vx(entity_id, -vx)
        ams.play_sound("wall_bounce")
    end

    if y < 0 then
        ams.set_y(entity_id, 0)
        ams.set_vy(entity_id, -vy)
        ams.play_sound("wall_bounce")
    end
end

return ball
```

#### brick.lua

```lua
--[[
brick behavior - destructible brick with hit tracking

Properties used:
  brick_hits_remaining: int - hits left to destroy
  brick_max_hits: int - original hit count (for damage ratio)

Config options:
  hits: int - hits required to destroy (default: 1)
  points: int - points when destroyed (default: 100)
  indestructible: bool - cannot be destroyed (default: false)
]]

local brick = {}

function brick.on_spawn(entity_id)
    local hits = ams.get_config(entity_id, "brick", "hits", 1)
    ams.set_prop(entity_id, "brick_hits_remaining", hits)
    ams.set_prop(entity_id, "brick_max_hits", hits)
end

return brick
```

#### shoot.lua

```lua
--[[
shoot behavior - entity fires projectiles at intervals

Config options:
  interval: float - seconds between shots (default: 2.0)
  projectile_type: string - entity type to spawn (default: "projectile")
  projectile_speed: float - projectile velocity (default: 200)
  projectile_color: string - projectile color (default: "red")
  direction: string - "down", "up", "left", "right", "player" (default: "down")
  offset_x, offset_y: float - spawn offset from center (default: 0)
]]

local shoot = {}

function shoot.on_spawn(entity_id)
    local interval = ams.get_config(entity_id, "shoot", "interval", 2.0)
    ams.set_prop(entity_id, "shoot_timer", ams.random() * interval)
end

function shoot.on_update(entity_id, dt)
    local interval = ams.get_config(entity_id, "shoot", "interval", 2.0)
    local timer = (ams.get_prop(entity_id, "shoot_timer") or 0) + dt

    if timer >= interval then
        shoot.fire(entity_id)
        timer = timer - interval
    end

    ams.set_prop(entity_id, "shoot_timer", timer)
end

function shoot.fire(entity_id)
    local projectile_type = ams.get_config(entity_id, "shoot", "projectile_type", "projectile")
    local speed = ams.get_config(entity_id, "shoot", "projectile_speed", 200)
    local color = ams.get_config(entity_id, "shoot", "projectile_color", "red")
    local direction = ams.get_config(entity_id, "shoot", "direction", "down")

    local x = ams.get_x(entity_id) + ams.get_width(entity_id) / 2
    local y = ams.get_y(entity_id) + ams.get_height(entity_id) / 2

    local vx, vy = 0, 0
    if direction == "down" then vy = speed
    elseif direction == "up" then vy = -speed
    elseif direction == "left" then vx = -speed
    elseif direction == "right" then vx = speed
    end

    ams.spawn(projectile_type, x - 4, y, vx, vy, 8, 8, color, "")
    ams.play_sound("shoot")
end

return shoot
```

## Collision Actions

Collision actions are Lua scripts that handle what happens when two entities collide. They can be:

1. **File-based**: Scripts in `ams/behaviors/collision_actions/` (for reusable actions)
2. **Inline**: Lua code embedded directly in game.yaml (for rapid prototyping)

### Inline Collision Actions

For quick prototyping, define collision actions directly in YAML:

```yaml
collision_behaviors:
  ball:
    # File-based action
    paddle:
      action: bounce_paddle
      modifier:
        max_angle: 60

    # Inline Lua action
    powerup:
      action:
        lua: |
          local a = {}
          function a.execute(ball_id, powerup_id, mod)
              ams.destroy(powerup_id)
              ams.set_prop(ball_id, "powered_up", true)
              ams.play_sound("powerup")
          end
          return a
```

Inline collision actions have full access to the `ams.*` API.

### Available Collision Actions

| Action | Description |
|--------|-------------|
| `bounce_paddle` | Ball bounces off paddle with angle based on hit position |
| `bounce_reflect` | Ball bounces off surface using AABB overlap detection |
| `take_damage` | Entity takes damage, destroyed when hits reach 0 |
| `hit_player` | Projectile hits player, sets `was_hit` property |

### Collision Action Interface

```lua
local my_action = {}

function my_action.execute(entity_a_id, entity_b_id, modifier)
    -- entity_a: The entity whose collision rule triggered
    -- entity_b: The other entity
    -- modifier: Config dict from YAML (or nil)
end

return my_action
```

### Collision Action Examples

#### bounce_paddle.lua

```lua
--[[
Bounces entity_a off paddle (entity_b) with angle based on hit position.

Modifier options:
  max_angle: float - maximum angle from vertical for edge hits (default: 60)
]]

local bounce_paddle = {}

function bounce_paddle.execute(entity_a_id, entity_b_id, modifier)
    local vy = ams.get_vy(entity_a_id)
    if vy <= 0 then return end  -- Only bounce if moving toward paddle

    local paddle_x = ams.get_x(entity_b_id)
    local paddle_w = ams.get_width(entity_b_id)
    local paddle_center = paddle_x + paddle_w / 2

    local ball_x = ams.get_x(entity_a_id)
    local ball_w = ams.get_width(entity_a_id)
    local ball_center = ball_x + ball_w / 2

    local offset = ams.clamp((ball_center - paddle_center) / (paddle_w / 2), -1, 1)
    local max_angle = modifier and modifier.max_angle or 60

    local angle = -90 + offset * max_angle
    local angle_rad = angle * 3.14159 / 180

    local vx = ams.get_vx(entity_a_id)
    local speed = ams.sqrt(vx * vx + vy * vy)

    ams.set_vx(entity_a_id, speed * ams.cos(angle_rad))
    ams.set_vy(entity_a_id, speed * ams.sin(angle_rad))
    ams.play_sound("paddle_hit")
end

return bounce_paddle
```

#### take_damage.lua

```lua
--[[
Reduces entity_a's hit points when hit by entity_b.

Modifier options:
  amount: int - damage per hit (default: 1)
  hit_sound: string - sound on hit (default: "brick_hit")
  destroy_sound: string - sound on destroy (default: "brick_break")
]]

local take_damage = {}

function take_damage.execute(entity_a_id, entity_b_id, modifier)
    if ams.get_config(entity_a_id, "brick", "indestructible", false) then
        ams.play_sound(modifier and modifier.hit_sound or "brick_hit")
        return
    end

    local hits = (ams.get_prop(entity_a_id, "brick_hits_remaining") or 1)
    local damage = modifier and modifier.amount or 1
    hits = hits - damage
    ams.set_prop(entity_a_id, "brick_hits_remaining", hits)

    if hits <= 0 then
        local points = ams.get_config(entity_a_id, "brick", "points", 100)
        ams.add_score(points)
        ams.destroy(entity_a_id)
        ams.play_sound(modifier and modifier.destroy_sound or "brick_break")
    else
        ams.play_sound(modifier and modifier.hit_sound or "brick_hit")
    end
end

return take_damage
```

#### hit_player.lua

```lua
--[[
Projectile hits player - destroys projectile and sets was_hit property.

Modifier options:
  play_sound: string - sound to play (default: "player_hit")
]]

local hit_player = {}

function hit_player.execute(projectile_id, player_id, modifier)
    ams.destroy(projectile_id)
    ams.play_sound(modifier and modifier.play_sound or "player_hit")
    ams.set_prop(player_id, "was_hit", true)
end

return hit_player
```

## Skins

Skins provide visual representation. The base `GameEngineSkin` handles all rendering via YAML render commands.

```python
class GameEngineSkin:
    def render_entity(self, entity: Entity, screen) -> None:
        """Render entity using YAML render commands."""
        # Looks up render commands from game definition
        # Falls back to simple colored rectangle

    def render_hud(self, screen, score, lives, level_name) -> None:
        """Render HUD (score, lives, level name)."""

    def update(self, dt: float) -> None:
        """Update animations."""

    def play_sound(self, sound_name: str) -> None:
        """Play a sound effect."""
```

For fully data-driven games, the skin can be an empty subclass:

```python
class BrickBreakerNGSkin(GameEngineSkin):
    pass  # All rendering handled by base class via game.yaml
```

## Creating a New Game

1. Create `games/MyGame/game.yaml` with entity types, collisions, input mapping
2. Create any custom Lua behaviors in `ams/behaviors/lua/`
3. Create any custom collision actions in `ams/behaviors/collision_actions/`
4. Create `games/MyGame/game_mode.py`:

```python
from games.common.game_engine import GameEngine, GameEngineSkin
from pathlib import Path
import yaml

def _load_game_metadata():
    game_yaml = Path(__file__).parent / 'game.yaml'
    with open(game_yaml) as f:
        data = yaml.safe_load(f)
        return {
            'name': data.get('name', 'Unnamed'),
            'description': data.get('description', ''),
            'version': data.get('version', '1.0.0'),
            'author': data.get('author', ''),
            'defaults': data.get('defaults', {}),
        }

_GAME_META = _load_game_metadata()


class MyGameSkin(GameEngineSkin):
    pass  # YAML-driven rendering


class MyGameMode(GameEngine):
    NAME = _GAME_META['name']
    DESCRIPTION = _GAME_META['description']
    VERSION = _GAME_META['version']
    AUTHOR = _GAME_META['author']

    GAME_DEF_FILE = Path(__file__).parent / 'game.yaml'
    LEVELS_DIR = Path(__file__).parent / 'levels'

    def _get_skin(self, skin_name: str) -> GameEngineSkin:
        return MyGameSkin()
```

5. Create `games/MyGame/game_info.py`:

```python
def get_game_mode():
    from .game_mode import MyGameMode
    return MyGameMode
```

6. Run: `python ams_game.py --game mygame --backend mouse`

## File Structure

```
games/MyGame/
├── __init__.py           # Lazy import
├── game_info.py          # Factory function
├── game_mode.py          # GameEngine subclass + skin
├── game.yaml             # Game definition
├── level_loader.py       # Optional: custom level loader
└── levels/               # Optional level files
    ├── level_01.yaml
    └── campaign.yaml

ams/behaviors/
├── engine.py             # BehaviorEngine
├── entity.py             # Entity class
├── api.py                # LuaAPI class
├── lua/                  # Entity behaviors
│   ├── ball.lua
│   ├── paddle.lua
│   ├── brick.lua
│   ├── projectile.lua
│   ├── shoot.lua
│   ├── descend.lua
│   └── oscillate.lua
└── collision_actions/    # Collision handlers
    ├── bounce_paddle.lua
    ├── bounce_reflect.lua
    ├── take_damage.lua
    └── hit_player.lua
```

## Architecture Validation

> "The architecture is working if a new game variant requires only YAML and assets."
>
> "The architecture is failing if 'simple' game variants require Python changes."

Checklist for adding a new brick type with unique behavior:
1. Add entry to `entity_types:` in game.yaml ✓
2. Create Lua behavior if needed ✓
3. Add collision behavior if needed ✓
4. No Python changes required ✓

Checklist for adding Space Invaders mode to BrickBreaker:
1. Add `invader`, `invader_shooter` entity types (extend brick) ✓
2. Add `descend`, `shoot`, `oscillate` behaviors ✓
3. Add `projectile` entity type ✓
4. Add `projectile->paddle: hit_player` collision ✓
5. Add `property_true` lose condition for `was_hit` ✓
6. Create level YAML with invader layout ✓
7. No Python changes required ✓
