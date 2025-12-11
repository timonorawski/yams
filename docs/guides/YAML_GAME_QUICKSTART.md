# YAML Game Quickstart Guide

Create games using only YAML and Lua - no Python boilerplate required.

## Quick Start

### 1. Create Game Directory

```bash
mkdir games/MyGameNG
```

### 2. Create game.yaml

This single file defines your entire game:

```yaml
# yaml-language-server: $schema=../../schemas/game.schema.json

name: "My Game"
description: "A YAML-driven game"
version: "1.0.0"
author: "Your Name"

screen_width: 800
screen_height: 600
background_color: [20, 20, 40]

defaults:
  lives: 3

win_condition: reach_score
win_target: 1000

# =============================================================================
# Entity Types
# =============================================================================

entity_types:
  target:
    width: 50
    height: 50
    color: red
    behaviors: [destroy_offscreen]
    tags: [target]
    render:
      - shape: circle
        color: $color
        radius: 0.5

# =============================================================================
# Input Mapping
# =============================================================================

input_mapping:
  target:
    on_hit:
      transform:
        type: destroy

# =============================================================================
# Player Configuration
# =============================================================================

player:
  type: spawner
  spawn: [0, 0]
```

### 3. Run Your Game

```bash
python ams_game.py --game mygameng --backend mouse
```

That's it! The registry auto-discovers YAML-only games.

## Core Concepts

### Entity Types

Define reusable entity templates:

```yaml
entity_types:
  # Base type
  fruit:
    width: 50
    height: 50
    behaviors: [gravity, destroy_offscreen]
    behavior_config:
      gravity:
        acceleration: 600
      destroy_offscreen:
        edges: all
        margin: 50
    tags: [fruit, target]
    render:
      - shape: circle
        color: $color
        radius: 0.5

  # Inherit and override
  fruit_red:
    extends: fruit
    color: red
    points: 10

  fruit_golden:
    extends: fruit
    color: [255, 215, 0]
    points: 100
    width: 60
    height: 60
```

### Behaviors

Built-in Lua behaviors (in `ams/behaviors/lua/`):

| Behavior | Description | Config |
|----------|-------------|--------|
| `gravity` | Apply gravity + velocity movement | `acceleration: 800` |
| `destroy_offscreen` | Destroy when leaving screen | `edges: all/bottom/sides`, `margin: 50` |
| `bounce` | Bounce off screen edges | `walls: all/top_sides`, `min_y`, `max_y` |
| `animate` | Cycle through sprite frames | `frames: 3`, `fps: 8` |
| `fade_out` | Fade and destroy | `duration: 0.5` |

Combine behaviors declaratively:

```yaml
duck_falling:
  behaviors: [gravity, destroy_offscreen, animate]
  behavior_config:
    gravity:
      acceleration: 800
    destroy_offscreen:
      edges: bottom
      margin: 50
    animate:
      frames: 2
      fps: 5
```

### Inline Lua Behaviors

For game-specific logic, write inline Lua:

```yaml
spawner:
  behaviors:
    - lua: |
        local spawner = {}

        function spawner.on_spawn(entity_id)
            ams.set_prop(entity_id, "timer", 0)
        end

        function spawner.on_update(entity_id, dt)
            local timer = ams.get_prop(entity_id, "timer") or 0
            timer = timer + dt

            if timer >= 2.0 then
                ams.set_prop(entity_id, "timer", 0)
                local x = ams.random_range(100, 700)
                ams.spawn("target", x, -50, 0, 100, 0, 0, "", "")
            else
                ams.set_prop(entity_id, "timer", timer)
            end
        end

        return spawner
```

### Rendering

Each entity type has a `render` list of draw commands:

```yaml
render:
  # Circle
  - shape: circle
    color: red
    radius: 0.5  # Relative to entity size

  # Rectangle
  - shape: rect
    color: blue

  # Sprite
  - shape: sprite
    sprite: my_sprite

  # Text
  - shape: text
    text: "{score} pts"
    color: white
    font_size: 24

  # Conditional rendering
  - shape: sprite
    sprite: duck_right_{frame}
    when:
      property: heading
      compare: between
      min: 90
      value: 180
```

### Input Mapping

Define what happens when entities are clicked:

```yaml
input_mapping:
  target:
    on_hit:
      transform:
        type: destroy  # Destroy the entity

  duck_flying:
    on_hit:
      transform:
        type: duck_hit  # Transform to different entity type

  bomb:
    on_hit:
      transform:
        type: destroy
```

### Global Input

Handle clicks anywhere on screen:

```yaml
global_on_input:
  action: play_sound
  action_args:
    sound: shot
```

### Lose Conditions

Define when players lose lives:

```yaml
lose_conditions:
  - entity_type: bomb
    event: destroyed
    action: lose_life
```

## ASCII Art Levels

Design levels visually using ASCII layouts:

### In game.yaml (default layout)

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
    MMMMMMMMMM
    ..WWWWWW..
  layout_key:
    I: invader
    M: invader_moving
    S: shooter
    W: wall
    ".": empty
```

### In Level Files (levels/*.yaml)

```yaml
# levels/space_invaders.yaml
name: "Space Invaders"
difficulty: 4
lives: 5

grid:
  cols: 10
  rows: 6
  brick_width: 70
  brick_height: 25
  start_x: 65
  start_y: 60

layout: |
  ..SSSSSS..
  MMMMMMMMMM
  IIIIIIIIII
  MMMMMMMMMM
  IIIIIIIIII
  ..WWWWWW..

layout_key:
  I: invader
  M: invader_moving
  S: shooter
  W: wall
  ".": empty

paddle:
  x: 340
  y: 550
```

## Sprites

### Sprite Sheet Definition

```yaml
assets:
  sprites:
    # Base sheet config
    _sheet:
      file: sprites.png
      transparent: [159, 227, 163]  # Transparent color

    # Individual sprites from sheet
    duck_right_1: { sprite: _sheet, x: 7, y: 126, width: 37, height: 41 }
    duck_right_2: { sprite: _sheet, x: 48, y: 126, width: 37, height: 41 }
    duck_right_3: { sprite: _sheet, x: 88, y: 126, width: 37, height: 41 }

    # Sprite inheritance with flip
    duck_left_1: { sprite: duck_right_1, flip_x: true }
    duck_left_2: { sprite: duck_right_2, flip_x: true }
```

### Using Sprites in Render

```yaml
render:
  - shape: sprite
    sprite: duck_right_{frame}  # {frame} replaced by animate behavior
```

## Sounds

```yaml
assets:
  sounds:
    shot: shot.wav
    hit: sounds/hit.wav

# Play via global_on_input or Lua
global_on_input:
  action: play_sound
  action_args:
    sound: shot
```

In Lua:

```lua
ams.play_sound("hit")
```

## Win/Lose Conditions

```yaml
# Win when score reaches target
win_condition: reach_score
win_target: 1000

# Or win when all of a type are destroyed
win_condition: destroy_all
win_target_type: brick

# Lose conditions
lose_on_player_death: true

lose_conditions:
  - entity_type: bomb
    event: destroyed
    action: lose_life
```

## Lua API Reference

Available in all Lua scripts:

### Entity Properties

```lua
ams.get_x(id), ams.set_x(id, val)
ams.get_y(id), ams.set_y(id, val)
ams.get_vx(id), ams.set_vx(id, val)
ams.get_vy(id), ams.set_vy(id, val)
ams.get_width(id), ams.get_height(id)
ams.get_type(id)
ams.get_age(id)
```

### Custom Properties

```lua
ams.get_prop(id, "key")
ams.set_prop(id, "key", value)
```

### Behavior Config

```lua
ams.get_config(id, "behavior_name", "key", default)
```

### Screen Info

```lua
ams.get_screen_width()
ams.get_screen_height()
```

### Entity Management

```lua
ams.destroy(id)
ams.spawn(type, x, y, vx, vy, width, height, color, sprite)
ams.count_entities_by_tag("tag")
ams.get_entities_of_type("type")
```

### Game State

```lua
ams.add_score(points)
ams.get_time()  -- Game time in seconds
```

### Utilities

```lua
ams.random()  -- 0 to 1
ams.random_range(min, max)
ams.play_sound("sound_name")
```

## Complete Example: Fruit Slice

```yaml
# yaml-language-server: $schema=../../schemas/game.schema.json

name: "Fruit Slice"
description: "Slice fruits as they arc across the screen"
version: "1.0.0"
author: "AMS Team"

screen_width: 800
screen_height: 600
background_color: [20, 20, 40]

defaults:
  lives: 3

win_condition: reach_score
win_target: 1000

entity_types:
  # Base fruit - arcs across screen
  fruit:
    width: 50
    height: 50
    behaviors: [gravity, destroy_offscreen]
    behavior_config:
      gravity:
        acceleration: 600
      destroy_offscreen:
        edges: all
        margin: 50
    tags: [fruit, target]
    render:
      - shape: circle
        color: $color
        radius: 0.5

  # Colored variants
  fruit_red:
    extends: fruit
    color: red
    points: 10

  fruit_golden:
    extends: fruit
    color: [255, 215, 0]
    points: 100

  # Bomb - avoid!
  bomb:
    width: 45
    height: 45
    color: [40, 40, 40]
    behaviors: [gravity, destroy_offscreen]
    behavior_config:
      gravity:
        acceleration: 600
      destroy_offscreen:
        edges: all
        margin: 50
    tags: [bomb, hazard]
    render:
      - shape: circle
        color: [40, 40, 40]
        radius: 0.5
      - shape: circle
        color: [200, 0, 0]
        radius: 0.35

  # Spawner - launches fruits
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
                  local screen_w = ams.get_screen_width()
                  local screen_h = ams.get_screen_height()

                  -- Random side
                  local from_left = ams.random() > 0.5
                  local x = from_left and -30 or screen_w + 30
                  local vx = from_left and ams.random_range(150, 300) or ams.random_range(-300, -150)

                  -- Launch upward
                  local y = screen_h + 30
                  local vy = -math.sqrt(2 * 600 * ams.random_range(200, 400))

                  -- Random type
                  local types = {"fruit_red", "fruit_red", "fruit_golden", "bomb"}
                  local t = types[math.floor(ams.random() * #types) + 1]
                  ams.spawn(t, x, y, vx, vy, 0, 0, "", "")
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
  fruit_golden:
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

## File Structure

Minimal YAML game:
```
games/MyGameNG/
└── game.yaml
```

With levels:
```
games/MyGameNG/
├── game.yaml
└── levels/
    ├── tutorial_01.yaml
    ├── tutorial_02.yaml
    └── campaign.yaml
```

With assets:
```
games/MyGameNG/
├── game.yaml
├── assets/
│   ├── sprites.png
│   └── sounds/
│       └── hit.wav
└── levels/
    └── ...
```

## Running

```bash
# Basic
python ams_game.py --game mygameng --backend mouse

# With level
python ams_game.py --game mygameng --backend mouse --level tutorial_01

# List available games
python ams_game.py --list-games
```

## Troubleshooting

### Game not discovered
- Ensure `game.yaml` exists in `games/YourGame/`
- Check for YAML syntax errors
- Try: `python -c "import yaml; yaml.safe_load(open('games/YourGame/game.yaml'))"`

### Schema validation errors
- Add `# yaml-language-server: $schema=../../schemas/game.schema.json` to get IDE validation
- Set `AMS_SKIP_SCHEMA_VALIDATION=1` to debug without strict validation

### Behaviors not working
- Check behavior names match files in `ams/behaviors/lua/`
- Verify `behavior_config` keys match what the behavior expects
- Add print statements in Lua: `print("debug:", value)`

### Sprites not loading
- Paths are relative to game directory
- Check `transparent` color matches sprite background exactly
- Verify coordinates with a sprite tuner tool
