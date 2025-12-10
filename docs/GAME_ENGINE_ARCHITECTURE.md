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

## YAML Game Definition

A game is defined by a `game.yaml` file with these sections:

### Basic Structure

```yaml
name: "My Game"
screen_width: 800
screen_height: 600
background_color: black

# Win condition
win_condition: destroy_all
win_target_type: brick  # Entity base type to destroy

# Entity type definitions
entity_types:
  # ...

# Collision rules
collisions:
  # ...

# Collision behavior handlers
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
  type: paddle
  spawn: [400, 550]
```

### Entity Types

Entity types define the building blocks of your game.

```yaml
entity_types:
  # Basic entity
  paddle:
    width: 120
    height: 20
    color: blue
    behaviors: [paddle]
    behavior_config:
      paddle:
        speed: 400

  # Entity with inheritance
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

  # Variant inherits from base
  brick_red:
    extends: brick
    color: red
    behavior_config:
      brick:
        points: 500

  # Complex entity with multiple behaviors
  invader_shooter:
    extends: brick
    color: purple
    behaviors: [brick, descend, shoot]
    behavior_config:
      brick:
        hits: 2
        points: 500
      descend:
        speed: 10
        pattern: fixed
      shoot:
        interval: 3.0
        projectile_type: projectile
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

Types with `extends` inherit all fields from the parent. Child values override parent values. `behavior_config` and `render` are inherited if not specified by child.

The engine tracks `base_type` for win conditions—`brick_red` has `base_type: brick`.

### Rendering

Entities are rendered using declarative render commands. Each entity type can define a list of render primitives.

```yaml
entity_types:
  paddle:
    width: 120
    height: 15
    render:
      # Blue filled rectangle
      - shape: rectangle
        color: blue
        fill: true
      # White outline
      - shape: rectangle
        color: white
        fill: false
        line_width: 2

  ball:
    width: 16
    height: 16
    render:
      - shape: circle
        color: white
        fill: true

  brick:
    width: 70
    height: 25
    render:
      - shape: rectangle
        color: $color  # Reference entity.color
        fill: true
      - shape: rectangle
        color: white
        fill: false
        line_width: 1

  invader_shooter:
    extends: brick
    render:
      # Inherit brick render, add indicator
      - shape: rectangle
        color: $color
        fill: true
      - shape: rectangle
        color: white
        fill: false
        line_width: 1
      # Triangle indicator for "shoots"
      - shape: triangle
        color: yellow
        fill: true
        points: [[0.5, 0.3], [0.3, 0.7], [0.7, 0.7]]

  brick_indestructible:
    render:
      - shape: rectangle
        color: $color
        fill: true
      # X pattern
      - shape: line
        color: gray
        line_width: 2
        points: [[0.1, 0.1], [0.9, 0.9]]
      - shape: line
        color: gray
        line_width: 2
        points: [[0.9, 0.1], [0.1, 0.9]]
```

#### Render Command Fields

| Field | Type | Description |
|-------|------|-------------|
| `shape` | string | Primitive type: `rectangle`, `circle`, `triangle`, `polygon`, `line`, `sprite` |
| `color` | string | Color name or `$color` to use entity.color |
| `fill` | bool | Fill shape (true) or outline only (false) |
| `line_width` | int | Outline/stroke width in pixels |
| `points` | list | Normalized (0-1) coordinates for polygon/triangle/line |
| `offset` | [x, y] | Offset from entity position |
| `size` | [w, h] | Override entity dimensions |
| `radius` | float | For circle, normalized to entity size |
| `sprite` | string | Sprite filename (for sprite shape) |

#### Color References

- `$color` - Use the entity's `color` field
- `$property_name` - Use value from entity.properties
- Any color name - Direct color (red, blue, white, etc.)

#### Coordinate System

Points for `polygon`, `triangle`, and `line` use normalized coordinates (0-1):
- `[0, 0]` = top-left of entity bounds
- `[1, 1]` = bottom-right of entity bounds
- `[0.5, 0.5]` = center of entity

#### Layering

Render commands are drawn in order. Later commands appear on top.

```yaml
render:
  - shape: rectangle  # Background
    color: blue
    fill: true
  - shape: circle     # Drawn on top
    color: white
    fill: true
    offset: [10, 10]
    size: [8, 8]
```

### Collisions

Collisions are declared in two parts: which types collide, and what happens.

```yaml
# Which entity types can collide
collisions:
  - [ball, paddle]
  - [ball, brick]    # Also matches brick_red, invader, etc. (inheritance)
  - [projectile, paddle]

# What happens on collision
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
        max_speed: 500
  brick:
    ball:
      action: take_damage
      modifier:
        amount: 1
        points: 100
```

Collision behaviors are Lua scripts in `ams/behaviors/collision_actions/`. The `modifier` dict is passed to the action's `execute(a_id, b_id, modifier)` function.

### Input Mapping

Input mapping connects player input to entity behavior.

```yaml
input_mapping:
  # Simple: set property from input position
  paddle:
    target_x: paddle_target_x  # Property name to set

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

  # Conditional action
  ball:
    on_input:
      action: ball.launch
      when:
        property: ball_launched
        value: false
      modifier:
        angle: -90
```

#### Input Mapping Fields

| Field | Type | Description |
|-------|------|-------------|
| `target_x` | string | Property to set from `input.position.x` |
| `target_y` | string | Property to set from `input.position.y` |
| `on_input.transform` | object | Transform entity on input |
| `on_input.action` | string | Lua function to call |
| `on_input.when` | object | Condition for action |
| `on_input.modifier` | object | Config passed to action |

### Transform System

Transform is the core primitive for entity metamorphosis—an entity becomes something fundamentally different.

```yaml
# Composite entity (renders as multiple things)
paddle_ready:
  behaviors: [paddle]
  render_as: [paddle, ball]  # Skin renders both

# Transform on input
input_mapping:
  paddle_ready:
    on_input:
      transform:
        into: paddle           # Entity becomes this type
        spawn:                 # Spawn children at same position
          - type: ball
            offset: [52, -20]  # Relative to parent
            speed: 300         # Spawn properties (behavior interprets)
            angle:
              lua: ams.random_range(-120, -60)
```

Transform:
1. Changes the entity's type (updates behaviors, config, rendering)
2. Optionally spawns child entities with offset and properties
3. Child properties support `{lua: "..."}` for dynamic values

### Lose Conditions

Lose conditions define what causes life loss and how to recover.

```yaml
lose_conditions:
  - entity_type: ball
    event: exited_screen
    edge: bottom              # bottom, top, left, right, any
    action: lose_life
    then:
      destroy: ball           # Remove the ball
      transform:
        entity_type: paddle   # Transform this entity
        into: paddle_ready    # Back to waiting state
```

The engine detects screen exit events and triggers the configured response.

### Spawn Properties and Lua Evaluation

Any property in a spawn config can use `{lua: "..."}` for dynamic evaluation:

```yaml
spawn:
  - type: ball
    offset: [0, -20]
    speed: 300
    angle:
      lua: ams.random_range(-120, -60)
    some_flag: true           # Literal value
    custom_value:
      lua: ams.random() * 100  # Any Lua expression
```

The engine evaluates `{lua: "..."}` at spawn time, passing the result to the entity's properties. The behavior's `on_spawn` can then use these values.

## Lua Behaviors

Behaviors are Lua scripts that define entity logic. They live in `ams/behaviors/lua/`.

### Lifecycle Events

```lua
local my_behavior = {}

function my_behavior.on_spawn(entity_id)
    -- Called when entity is created
    -- Initialize properties, set up state
end

function my_behavior.on_update(entity_id, dt)
    -- Called every frame
    -- dt is delta time in seconds
end

function my_behavior.on_hit(entity_id, other_id, hit_x, hit_y)
    -- Called on collision (before collision_action)
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

-- Size
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
ams.get_config(id, "behavior_name", "key", default_value)
```

#### Spawning

```lua
-- Spawn new entity, returns entity ID
local new_id = ams.spawn(type, x, y, vx, vy, width, height, color, sprite, behaviors, behavior_config)
```

#### Queries

```lua
-- Get entity IDs by type
local ids = ams.get_entities_of_type("brick")

-- Get all entity IDs
local all_ids = ams.get_all_entity_ids()
```

#### Game State

```lua
ams.get_screen_width()
ams.get_screen_height()
ams.get_score()
ams.add_score(points)
ams.get_time()  -- Elapsed game time
```

#### Events

```lua
ams.play_sound("hit.wav")
ams.schedule(delay_seconds, function_name, entity_id)
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

### Example: Ball Behavior

```lua
--[[
ball behavior - bouncing ball with velocity

A ball with zero velocity is stationary (not yet launched).
On spawn, if speed+angle properties are set, computes velocity.
]]

local ball = {}

function ball.on_spawn(entity_id)
    -- Initialize ball_speed from config default
    ams.set_prop(entity_id, "ball_speed",
        ams.get_config(entity_id, "ball", "speed", 300))

    -- If spawned with speed+angle properties, compute velocity
    local speed = ams.get_prop(entity_id, "speed")
    local angle = ams.get_prop(entity_id, "angle")

    if speed and angle then
        local angle_rad = angle * 3.14159 / 180
        ams.set_vx(entity_id, speed * ams.cos(angle_rad))
        ams.set_vy(entity_id, speed * ams.sin(angle_rad))
        ams.set_prop(entity_id, "ball_speed", speed)
        -- Clear spawn properties
        ams.set_prop(entity_id, "speed", nil)
        ams.set_prop(entity_id, "angle", nil)
    end
end

function ball.on_update(entity_id, dt)
    local vx = ams.get_vx(entity_id)
    local vy = ams.get_vy(entity_id)

    -- Ball with no velocity doesn't move
    if vx == 0 and vy == 0 then
        return
    end

    -- Move ball
    local x = ams.get_x(entity_id)
    local y = ams.get_y(entity_id)

    x = x + vx * dt
    y = y + vy * dt

    -- Bounce off walls
    local w = ams.get_width(entity_id)
    local screen_w = ams.get_screen_width()

    if x < 0 then
        x = 0
        vx = -vx
    elseif x + w > screen_w then
        x = screen_w - w
        vx = -vx
    end

    if y < 0 then
        y = 0
        vy = -vy
    end

    ams.set_x(entity_id, x)
    ams.set_y(entity_id, y)
    ams.set_vx(entity_id, vx)
    ams.set_vy(entity_id, vy)
end

return ball
```

## Collision Actions

Collision actions are Lua scripts that handle what happens when two entities collide. They live in `ams/behaviors/collision_actions/`.

```lua
--[[
bounce_paddle - ball bounces off paddle with angle based on hit position
]]

local bounce_paddle = {}

function bounce_paddle.execute(ball_id, paddle_id, modifier)
    local max_angle = modifier and modifier.max_angle or 60

    -- Get positions
    local ball_x = ams.get_x(ball_id)
    local ball_w = ams.get_width(ball_id)
    local ball_center = ball_x + ball_w / 2

    local paddle_x = ams.get_x(paddle_id)
    local paddle_w = ams.get_width(paddle_id)
    local paddle_center = paddle_x + paddle_w / 2

    -- Calculate hit offset (-1 to 1)
    local offset = (ball_center - paddle_center) / (paddle_w / 2)
    offset = ams.clamp(offset, -1, 1)

    -- Calculate bounce angle
    local angle = offset * max_angle
    local angle_rad = (angle - 90) * 3.14159 / 180

    -- Apply new velocity
    local speed = ams.get_prop(ball_id, "ball_speed") or 300
    ams.set_vx(ball_id, speed * ams.cos(angle_rad))
    ams.set_vy(ball_id, speed * ams.sin(angle_rad))

    ams.play_sound("paddle_hit.wav")
end

return bounce_paddle
```

## Skins

Skins provide visual representation. They're Python classes that know how to render entities.

```python
class GameEngineSkin(ABC):
    @abstractmethod
    def render_entity(self, entity: Entity, screen) -> None:
        """Render an entity."""
        pass

    def render_hud(self, game, screen) -> None:
        """Render HUD (score, lives, etc.)."""
        pass

    def update(self, dt: float) -> None:
        """Update animations."""
        pass

    def play_sound(self, sound_name: str) -> None:
        """Play a sound effect."""
        pass
```

Skins handle:
- Entity rendering based on `entity_type`, `color`, `sprite`
- Composite rendering via `render_as` (e.g., `paddle_ready` renders as paddle + ball)
- HUD (score, lives, level name)
- Sound effects

## Creating a New Game

1. Create `games/MyGame/game.yaml` with entity types, collisions, input mapping
2. Create any custom Lua behaviors in `ams/behaviors/lua/`
3. Create any custom collision actions in `ams/behaviors/collision_actions/`
4. Create `games/MyGame/game_mode.py`:

```python
from games.common.game_engine import GameEngine, GameEngineSkin
from pathlib import Path

class MyGameSkin(GameEngineSkin):
    def render_entity(self, entity, screen):
        # Render based on entity.entity_type, entity.color, etc.
        pass

class MyGameMode(GameEngine):
    NAME = "My Game"
    GAME_DEF_FILE = Path(__file__).parent / 'game.yaml'

    def _get_skin(self) -> GameEngineSkin:
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
├── __init__.py           # Lazy import to avoid circular deps
├── game_info.py          # Factory function
├── game_mode.py          # GameEngine subclass + skin
├── game.yaml             # Game definition
└── levels/               # Optional level files
    ├── level_01.yaml
    └── campaign.yaml

ams/behaviors/
├── lua/                  # Entity behaviors
│   ├── ball.lua
│   ├── paddle.lua
│   ├── brick.lua
│   └── ...
└── collision_actions/    # Collision handlers
    ├── bounce_paddle.lua
    ├── bounce_reflect.lua
    └── take_damage.lua
```

## Architecture Test

> "The architecture is working if a new Breakout variant requires only YAML and sprites."
>
> "The architecture is failing if 'simple' game variants require Python changes."

To add a new brick type with unique behavior:
1. Add entry to `entity_types:` in game.yaml ✓
2. Create Lua behavior if needed ✓
3. No Python changes required ✓
