# Game Engine Architecture

The YAML-driven game engine enables building complete games through declarative configuration rather than imperative code. Games are defined in `game.yaml` files with Lua behaviors for dynamic logic.

## Overview

### Design Philosophy

**Data-driven over code-driven**: Game logic lives in YAML and Lua, not Python. Python provides the runtime infrastructure.

**Composition over inheritance**: Entities are built from reusable behaviors, not class hierarchies.

**Declarative transforms**: Lifecycle events (destroy, hit, age) trigger declarative transforms defined in YAML.

**Zero boilerplate**: YAML-only games auto-discovered and playable without Python files.

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    YAML DEFINITION                          │
│  game.yaml: entities, behaviors, collisions, input, levels  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   GAME ENGINE (engine.py)                   │
│  • Loads YAML → GameDefinition                              │
│  • Spawns entities with type config                         │
│  • Collision detection (AABB)                               │
│  • Input mapping → transforms/actions                       │
│  • Win/lose condition checking                              │
│  • ContentFS integration (layered assets/behaviors)         │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ↓               ↓               ↓
┌────────────────┐  ┌─────────────┐  ┌──────────────┐
│  LUA ENGINE    │  │  RENDERER   │  │  LUA API     │
│  (ams/lua/)    │  │  (render)   │  │  (api.py)    │
│                │  │             │  │              │
│  • Run Lua     │  │  • Sprites  │  │  • Entity    │
│  • Behaviors   │  │  • Shapes   │  │    access    │
│  • Lifecycle   │  │  • Text     │  │  • Spawning  │
│  • Properties  │  │  • Layers   │  │  • Collision │
│  • Scheduling  │  │             │  │  • Hierarchy │
└────────────────┘  └─────────────┘  └──────────────┘
```

## Core Components

### GameEngine (`ams/games/game_engine/engine.py`)

The main orchestrator. Responsibilities:

- **YAML Loading**: Parse `game.yaml` into `GameDefinition` dataclass
- **Entity Lifecycle**: Spawn, update, destroy entities via LuaEngine
- **Collision System**: AABB detection + collision_behaviors dispatch
- **Input Mapping**: Route input events to entity transforms/actions
- **ContentFS Integration**: Layer game assets over engine defaults
- **Transform System**: Apply lifecycle transforms (destroy, type change, spawn children)
- **Win/Lose Logic**: Check conditions from game.yaml

#### Key Methods

```python
class GameEngine(BaseGame):
    def spawn_entity(self, entity_type: str, x: float, y: float, **overrides) -> GameEntity:
        """Spawn entity from type definition, with optional overrides."""

    def apply_transform(self, entity: Entity, transform: TransformConfig) -> Optional[Entity]:
        """Apply a transform: destroy or change type, spawn children."""

    def _check_collisions(self) -> None:
        """AABB check + dispatch collision_behaviors actions."""

    def _apply_input_mapping(self, event: InputEvent) -> None:
        """Route input to entities per input_mapping in game.yaml."""
```

### GameEntity (`ams/games/game_engine/entity.py`)

Concrete entity implementation extending `Entity` ABC:

```python
@dataclass
class GameEntity(Entity):
    # Transform
    x, y, width, height: float
    vx, vy: float  # Velocity

    # Visual
    sprite: str
    color: str
    visible: bool

    # State
    health: int
    spawn_time: float
    tags: list[str]

    # Behaviors
    behaviors: list[str]  # Behavior names
    behavior_config: dict[str, dict[str, Any]]  # Per-behavior config

    # Hierarchy
    parent_id: Optional[str]
    parent_offset: tuple[float, float]
    children: list[str]  # Child entity IDs
```

**Computed Properties**: Entities support computed properties via `get_property()`:
- `damage_ratio`: `1 - (hits_remaining / max_hits)`
- `health_ratio`: `health / max_health`
- `age`: Current time - spawn_time
- `heading`: Direction in degrees (0° = north, clockwise)
- `facing`: 'left' or 'right' based on vx

**Property Resolution**: `$property` references in YAML are resolved at runtime:
```yaml
render:
  - shape: text
    text: $score  # Resolves to entity.properties['score']
    color: red
```

### GameLuaAPI (`ams/games/game_engine/api.py`)

Bridge between Lua behaviors and game engine. Exposed as `ams` namespace:

```lua
-- Transform
ams.get_x(id), ams.set_x(id, val)
ams.get_y(id), ams.set_y(id, val)
ams.get_vx(id), ams.set_vx(id, val)
ams.get_vy(id), ams.set_vy(id, val)

-- Visual
ams.get_sprite(id), ams.set_sprite(id, name)
ams.get_color(id), ams.set_color(id, color)

-- State
ams.get_health(id), ams.set_health(id, hp)
ams.destroy(id)

-- Properties (custom key-value storage)
ams.get_prop(id, "key"), ams.set_prop(id, "key", value)
ams.get_config(id, "behavior", "key", default)

-- Spawning & queries
ams.spawn(type, x, y, vx, vy, w, h, color, sprite) -> id
ams.get_entities_of_type(type) -> [id1, id2, ...]
ams.count_entities_by_tag(tag)

-- Game state
ams.get_screen_width(), ams.get_screen_height()
ams.add_score(points)
ams.get_time()

-- Events
ams.play_sound("hit")
ams.schedule(delay, "callback_name", entity_id)

-- Hierarchy
ams.set_parent(child_id, parent_id, offset_x, offset_y)
ams.detach_from_parent(id)
ams.get_children(id) -> [id1, id2, ...]
```

### GameDefinition (`ams/games/game_engine/config.py`)

Parsed YAML structure. Key dataclasses:

```python
@dataclass
class GameDefinition:
    entity_types: Dict[str, EntityTypeConfig]
    collision_behaviors: Dict[str, Dict[str, CollisionAction]]
    input_mapping: Dict[str, InputMappingConfig]
    lose_conditions: List[LoseConditionConfig]
    assets: AssetsConfig
    # ...

@dataclass
class EntityTypeConfig:
    name: str
    width, height: float
    behaviors: List[str]
    behavior_config: Dict[str, Dict[str, Any]]
    tags: List[str]
    render: List[RenderCommand]
    on_destroy: Optional[TransformConfig]
    on_parent_destroy: Optional[TransformConfig]
    on_update: List[OnUpdateTransform]
    extends: Optional[str]  # Inheritance
    # ...
```

## Entity System

### Lifecycle

1. **Spawn**: `GameEngine.spawn_entity()` creates GameEntity from type config
2. **on_spawn**: LuaEngine calls `behavior.on_spawn(entity_id)` for each behavior
3. **Update Loop**: Each frame:
   - `behavior.on_update(entity_id, dt)` for all behaviors
   - Apply physics (velocity → position)
   - Check collisions → `behavior.on_hit(entity_id, other_id, other_type)`
   - Check on_update transforms (age, property, interval conditions)
4. **Destroy**: `entity.destroy()` or `ams.destroy(id)`
   - `behavior.on_destroy(entity_id)` for all behaviors
   - Apply `on_destroy` transform (spawn children, effects)
   - Handle orphaned children (on_parent_destroy)
   - Remove from LuaEngine

### Behaviors

Behaviors are Lua scripts in `lua/behavior/` (via ContentFS):

```lua
-- lua/behavior/gravity.lua
local gravity = {}

function gravity.on_spawn(entity_id)
    -- Initialization
end

function gravity.on_update(entity_id, dt)
    local config = ams.get_config(entity_id, "gravity", "acceleration", 800)
    local vy = ams.get_vy(entity_id)
    ams.set_vy(entity_id, vy + config * dt)
end

return gravity
```

**Attaching to entities**:
```yaml
entity_types:
  fruit:
    behaviors: [gravity, destroy_offscreen]
    behavior_config:
      gravity:
        acceleration: 600
```

**Inline behaviors**:
```yaml
entity_types:
  spawner:
    behaviors:
      - lua: |
          local spawner = {}
          function spawner.on_update(id, dt)
              -- Inline Lua code here
          end
          return spawner
```

### Inheritance

Entity types support `extends` for DRY definitions:

```yaml
entity_types:
  fruit:
    width: 50
    height: 50
    behaviors: [gravity]
    render:
      - shape: circle
        color: $color

  fruit_red:
    extends: fruit
    color: red
    points: 10

  fruit_golden:
    extends: fruit
    color: [255, 215, 0]
    points: 100
```

Child types inherit width, height, behaviors, render, etc., and can override.

## ContentFS Integration

The engine uses ContentFS for **layered content resolution**:

```
Priority (high to low):
1. Game layer (games/mygame/lua/behavior/)
2. Engine layer (ams/games/game_engine/lua/behavior/)
3. Core layer (ams/lua/behavior/) - base defaults
```

Games can **override engine behaviors** by placing identically-named files in their `lua/` directory.

```python
# Engine setup
if self.GAME_SLUG:
    game_path = self._content_fs.core_dir / 'games' / self.GAME_SLUG
    self._content_fs.add_game_layer(game_path)

# Behavior loading
for sub_type in ['behavior', 'collision_action', 'generator']:
    lua_path = f'lua/{sub_type}'
    if self._content_fs.exists(lua_path):
        self._behavior_engine.load_subroutines_from_dir(sub_type, lua_path)
```

## Collision System

### Detection

AABB (Axis-Aligned Bounding Box) collision detection:

```python
def _check_aabb_collision(self, a: Entity, b: Entity) -> bool:
    return (a.x < b.x + b.width and
            a.x + a.width > b.x and
            a.y < b.y + b.height and
            a.y + a.height > b.y)
```

### Collision Behaviors

Defined in nested dict format:

```yaml
collision_behaviors:
  ball:
    paddle:
      action: bounce_paddle
      modifier:
        max_angle: 60
    brick:
      action: take_damage
      modifier:
        damage: 1
```

**Action dispatch**:
1. Find collision between entity_a and entity_b
2. Look up `collision_behaviors[type_a][type_b]`
3. Execute Lua collision action: `action.execute(a_id, b_id, modifier)`

**Collision action example** (`lua/collision_action/bounce_paddle.lua`):
```lua
local bounce = {}

function bounce.execute(ball_id, paddle_id, modifier)
    -- Calculate bounce angle based on hit position
    local max_angle = modifier.max_angle or 60
    local ball_x = ams.get_x(ball_id) + ams.get_width(ball_id) / 2
    local paddle_x = ams.get_x(paddle_id)
    local paddle_w = ams.get_width(paddle_id)

    local hit_pos = (ball_x - paddle_x) / paddle_w - 0.5  -- -0.5 to 0.5
    local angle = hit_pos * max_angle

    -- Reflect velocity
    local speed = math.sqrt(ams.get_vx(ball_id)^2 + ams.get_vy(ball_id)^2)
    local angle_rad = math.rad(-90 - angle)
    ams.set_vx(ball_id, speed * math.cos(angle_rad))
    ams.set_vy(ball_id, speed * math.sin(angle_rad))
end

return bounce
```

**Inline collision actions**:
```yaml
collision_behaviors:
  ball:
    powerup:
      action:
        lua: |
          local action = {}
          function action.execute(a_id, b_id, mod)
              ams.destroy(b_id)
              ams.set_prop(a_id, "powered_up", true)
          end
          return action
```

### Type Matching

Supports both **exact type** and **base type** matching:

```yaml
entity_types:
  brick:
    # ...

  brick_red:
    extends: brick  # base_type = "brick"

  brick_blue:
    extends: brick  # base_type = "brick"

collision_behaviors:
  ball:
    brick:  # Matches brick, brick_red, brick_blue
      action: take_damage
```

## Input Mapping System

Declarative input routing defined in game.yaml:

```yaml
input_mapping:
  paddle:
    target_x: paddle_target_x  # Set property from input.x

  paddle_ready:
    on_input:  # Any input triggers
      transform:
        type: paddle
        children:
          - type: ball
            offset: [0, -20]
            vy: -300
      when:
        property: ball_launched
        value: false

  duck:
    on_hit:  # Only if input inside entity bounds
      transform:
        type: duck_falling
```

### Global Input

Fire actions on any input regardless of entities:

```yaml
global_on_input:
  action: play_sound
  action_args:
    sound: shot
```

### Input Actions

Named actions or inline Lua:

```yaml
input_mapping:
  spawner:
    on_input:
      action:
        lua: |
          local action = {}
          function action.execute(x, y, args)
              ams.spawn("target", x, y, 0, 100, 0, 0, "", "")
          end
          return action
```

## Transform System

Transforms are the core abstraction for entity state changes. Triggered by:
- Input events (`on_hit`, `on_input`)
- Lifecycle events (`on_destroy`, `on_parent_destroy`)
- Time/property conditions (`on_update`)
- Lose conditions (`then_transform`)

### Transform Types

**Destroy** - Remove entity, spawn children:
```yaml
on_destroy:
  transform:
    type: destroy
    children:
      - type: explosion
        count: 5
        offset: {lua: "[ams.random_range(-10, 10), ams.random_range(-10, 10)]"}
```

**Type change** - Morph into another entity type:
```yaml
on_hit:
  transform:
    type: duck_falling  # Transform from duck_flying → duck_falling
    children:
      - type: feather
        count: 3
```

### Child Spawning

Children support:
- **Offset**: Relative to parent position (supports `{lua: ...}`)
- **Count**: Spawn multiple (e.g., radial explosions)
- **Velocity inheritance**: `inherit_velocity: 0.5` adds 50% of parent velocity
- **Lifetime**: `lifetime: 0.5` auto-destroys after 0.5s
- **Properties**: Pass initial properties (supports `$property` refs)

```yaml
children:
  - type: debris
    count: 8
    offset: {lua: "[math.cos(i*45)*20, math.sin(i*45)*20]"}  # 'i' = spawn index
    inherit_velocity: 0.3
    lifetime: 1.0
    properties:
      rotation: {lua: "ams.random_range(0, 360)"}
```

### On Update Transforms

Conditional transforms checked each frame:

```yaml
entity_types:
  projectile:
    on_update:
      - when:
          age_min: 2.0
          age_max: 2.1
        transform:
          type: destroy

      - when:
          property: hit_wall
          value: true
        transform:
          type: explosion

      - when:
          interval: 0.1  # Every 0.1 seconds
        transform:
          children:
            - type: smoke_trail
```

**Condition types**:
- `age_min` / `age_max`: Age range (seconds since spawn)
- `property` / `value`: Property equals check
- `interval`: Repeat every N seconds (auto-tracked per entity)

## Rendering System

### Render Commands

Entities rendered via declarative `render` list:

```yaml
entity_types:
  target:
    render:
      # Background circle
      - shape: circle
        color: red
        radius: 0.5

      # Border
      - shape: circle
        color: white
        fill: false
        line_width: 2

      # Sprite layer
      - shape: sprite
        sprite: target_{frame}

      # Text overlay
      - shape: text
        text: $points
        color: white
        font_size: 24
```

**Supported shapes**:
- `rectangle`, `circle`, `triangle`, `polygon`, `line`
- `sprite` - Load from assets
- `text` - Dynamic text with property refs

**Features**:
- `offset`, `size`: Position/scale relative to entity
- `alpha`: Transparency (0-255 or `$property` ref)
- `when`: Conditional rendering based on properties
- `stop`: Halt further render commands (render layering)

### Conditional Rendering

```yaml
render:
  - shape: sprite
    sprite: duck_right_{frame}
    when:
      property: heading
      compare: between
      min: 90
      value: 180  # 90° ≤ heading < 180°

  - shape: sprite
    sprite: duck_left_{frame}
    when:
      property: heading
      compare: between
      min: 180
      value: 270
```

### Sprite System

**Sprite sheets** with regions:
```yaml
assets:
  sprites:
    _sheet:
      file: sprites.png
      transparent: [159, 227, 163]

    duck_right_1: {sprite: _sheet, x: 7, y: 126, width: 37, height: 41}
    duck_right_2: {sprite: _sheet, x: 48, y: 126, width: 37, height: 41}
```

**Sprite inheritance** with transforms:
```yaml
sprites:
  duck_left_1:
    sprite: duck_right_1
    flip_x: true
```

**Template sprites**:
```yaml
sprite: duck_{color}_{frame}  # Resolves entity.properties['color'], ['frame']
```

## Parent-Child Hierarchy

Entities can attach to parents for **rope physics, compound objects, attachments**:

```lua
-- Attach candy to rope anchor
ams.set_parent(candy_id, rope_segment_id, 0, 20)  -- 20px below parent

-- Check hierarchy
if ams.has_parent(entity_id) then
    local parent_id = ams.get_parent_id(entity_id)
end

-- Detach
ams.detach_from_parent(entity_id)
```

**Orphan handling**: When parent destroyed, children trigger `on_parent_destroy` transform:

```yaml
entity_types:
  rope_segment:
    on_parent_destroy:
      transform:
        type: destroy  # Cascade destroy down chain

  candy:
    on_parent_destroy:
      transform:
        type: candy_falling  # Start falling when rope cut
```

Children are recursively orphaned (breadth-first) when parent dies.

## Win/Lose Conditions

### Win Conditions

```yaml
# Destroy all of a type
win_condition: destroy_all
win_target_type: brick  # Destroy all entities with base_type = "brick"

# Reach score
win_condition: reach_score
win_target: 1000
```

### Lose Conditions

Declarative triggers with then-blocks:

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
      clear_property: ball_launched
```

**Events**:
- `exited_screen`: Entity left screen (edge: top/bottom/left/right/any)
- `property_true`: Entity property became truthy

**Then actions**:
- `destroy: <type>`: Destroy entities of type
- `transform`: Apply transform to target entities
- `clear_property`: Reset entity property

## Level System

### ASCII Layout

Design levels visually:

```yaml
default_layout:
  grid:
    cell_width: 70
    cell_height: 25
    start_x: 65
    start_y: 60
  layout: |
    ..SSSSSS..
    MMMMMMMMMM
    IIIIIIIIII
  layout_key:
    I: invader
    M: invader_moving
    S: shooter
    ".": empty
```

### Level Files

`levels/<name>.yaml`:
```yaml
name: "Tutorial 1"
difficulty: 1
lives: 5

grid:
  # ...

layout: |
  BBBBBBBBBB
  RRRRRRRRRR

layout_key:
  B: brick_blue
  R: brick_red

paddle:
  x: 340
  y: 550
```

Load via `--level` flag:
```bash
python ams_game.py --game mygame --level tutorial_01
```

## Factory Pattern (YAML-Only Games)

Games require **zero Python boilerplate**:

```python
# GameEngine.from_yaml() creates dynamic subclass
MyGame = GameEngine.from_yaml(Path('games/MyGame/game.yaml'))

# Auto-discovered by game registry
# Just create game.yaml and run:
python ams_game.py --game mygame --backend mouse
```

Factory method reads metadata from YAML:
```yaml
name: "My Game"
description: "A YAML-driven game"
version: "1.0.0"
author: "Your Name"
```

## Example: Complete Game

**Fruit Slice** - minimal YAML-only game:

```yaml
# yaml-language-server: $schema=../../schemas/game.schema.json

name: "Fruit Slice"
description: "Slice fruits as they arc across the screen"
version: "1.0.0"

screen_width: 800
screen_height: 600
background_color: [20, 20, 40]

win_condition: reach_score
win_target: 1000

defaults:
  lives: 3

entity_types:
  fruit:
    width: 50
    height: 50
    behaviors: [gravity, destroy_offscreen]
    behavior_config:
      gravity:
        acceleration: 600
    tags: [fruit, target]
    render:
      - shape: circle
        color: $color
        radius: 0.5

  fruit_red:
    extends: fruit
    color: red
    points: 10

  bomb:
    width: 45
    height: 45
    color: [40, 40, 40]
    behaviors: [gravity, destroy_offscreen]
    behavior_config:
      gravity:
        acceleration: 600
    tags: [bomb, hazard]
    render:
      - shape: circle
        color: [40, 40, 40]
        radius: 0.5
      - shape: circle
        color: [200, 0, 0]
        radius: 0.35

  spawner:
    width: 1
    height: 1
    behaviors:
      - lua: |
          local spawner = {}
          function spawner.on_spawn(id)
              ams.set_prop(id, "timer", 0)
          end
          function spawner.on_update(id, dt)
              local timer = ams.get_prop(id, "timer") + dt
              if timer >= 1.5 then
                  ams.set_prop(id, "timer", 0)
                  local types = {"fruit_red", "fruit_red", "bomb"}
                  local t = types[math.floor(ams.random() * #types) + 1]
                  local x = ams.random_range(-30, 830)
                  local vy = -math.sqrt(2 * 600 * ams.random_range(200, 400))
                  ams.spawn(t, x, 630, 0, vy, 0, 0, "", "")
              else
                  ams.set_prop(id, "timer", timer)
              end
          end
          return spawner
    render: []

input_mapping:
  fruit_red:
    on_hit:
      transform:
        type: destroy
  bomb:
    on_hit:
      transform:
        type: destroy

lose_conditions:
  - entity_type: bomb
    event: destroyed
    action: lose_life

player:
  type: spawner
  spawn: [0, 0]
```

Run with:
```bash
python ams_game.py --game fruitslice --backend mouse
```

## Best Practices

### Entity Design

1. **Use inheritance** for variants (brick_red, brick_blue from brick base)
2. **Prefer behaviors** over inline Lua when reusable
3. **Tag entities** for bulk queries (`ams.count_entities_by_tag("enemy")`)
4. **Use properties** for entity-specific state (timers, counters)

### Behavior Design

1. **Single responsibility** - one behavior does one thing
2. **Use behavior_config** for tunable parameters
3. **Check config bounds** - behaviors run on any entity type
4. **Fail gracefully** - missing properties should not crash

### Performance

1. **Limit entities** - 100-200 alive entities max for 60fps
2. **Use destroy_offscreen** - cleanup entities that left screen
3. **Batch spawns** - spawn children in bursts, not per-frame
4. **Avoid O(n²) queries** - use tags/types, not iterate all entities

### YAML Organization

1. **Break up large files** - use levels/*.yaml for level data
2. **Comment entity relationships** - explain collision pairs
3. **Group related types** - base types first, variants below
4. **Use YAML anchors** for repeated config (not yet supported, future)

## Extension Points

### Custom Renderer

Override `_get_skin()` for game-specific rendering:

```python
class MyGame(GameEngine):
    GAME_DEF_FILE = Path(__file__).parent / 'game.yaml'

    def _get_skin(self, skin_name: str) -> GameEngineRenderer:
        return MyCustomRenderer()
```

### Custom Win/Lose Logic

Override `_check_win_conditions()` for complex logic:

```python
def _check_win_conditions(self) -> None:
    # Custom condition checking
    if self._custom_condition_met():
        self._internal_state = GameState.WON
```

### Custom Collision Handling

Override `_handle_collision()` for physics:

```python
def _handle_collision(self, entity_a: Entity, entity_b: Entity) -> None:
    # Custom physics before action dispatch
    self._apply_physics_response(entity_a, entity_b)
    super()._handle_collision(entity_a, entity_b)
```

## Troubleshooting

### Behaviors not firing

- Check behavior file exists in `lua/behavior/`
- Verify ContentFS layer order (game > engine > core)
- Add `print()` in Lua for debugging

### Entities not spawning

- Check `entity_types` key matches spawn call
- Verify `player.type` exists in entity_types
- Check console for YAML schema validation errors

### Collisions not detected

- Ensure both types listed in `collision_behaviors`
- Verify entity bounds overlap (visual debug: render rectangles)
- Check if entities are alive (destroyed entities don't collide)

### Input not working

- Check `input_mapping` keys match entity types
- For `on_hit`, verify input position inside entity bounds
- Add `global_on_input` to test input is reaching engine

## See Also

- [YAML Game Quickstart](YAML_GAME_QUICKSTART.md) - Building games with game.yaml
- [Lua Scripting Guide](lua_scripting.md) - Writing Lua behaviors
- [YAML Physics Engine](../planning/YAML_PHYSICS_ENGINE.md) - Future physics system design
