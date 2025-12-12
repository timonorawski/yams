# Lua Script YAML Format Specification

**Status**: Approved
**Created**: 2024-12-12

## Overview

This document proposes a YAML format for Lua scripts that includes machine-readable metadata alongside the code. The format replaces raw `.lua` files with `.yaml` files that can be validated against a JSON Schema.

## Goals

1. **Self-documenting**: Scripts carry their own documentation, config schema, and usage examples
2. **Validatable**: JSON Schema enables IDE autocompletion and CI validation
3. **Discoverable**: Metadata enables tooling (script browsers, dependency graphs, API docs)
4. **Backwards compatible**: The `code` field contains standard Lua that works unchanged

## File Structure

```yaml
# yaml-language-server: $schema=../lua_script.schema.json
type: behavior              # Required: behavior | collision_action | generator | input_action
name: animate               # Optional: defaults to filename
description: |              # Optional: human-readable description
  Cycle through animation frames...
version: "1.0"              # Optional: semantic version
author: "YAMS Team"         # Optional
tags: [visual, animation]   # Optional: categorization

config:                     # For behaviors: behavior_config schema
  frames:
    type: int
    description: Number of animation frames
    default: 3
    min: 1

args:                       # For generators/input_actions: argument schema
  index:
    type: int
    required: true

provides:                   # What this script provides/implements
  hooks:                    # Lifecycle hooks (auto-detected if omitted)
    - on_spawn
    - on_update
  properties:               # Properties managed by this script
    - frame

requires:                   # Dependencies
  behaviors: [brick]        # Other behaviors needed
  properties: [hits]        # Properties that must exist
  api: [get_prop, set_prop] # ams.* methods used

examples:                   # Usage examples
  - title: Basic usage
    yaml: |
      behaviors: [animate]
      behavior_config:
        animate:
          frames: 3

code: |                     # Required: the actual Lua code
  local animate = {}
  function animate.on_spawn(entity_id)
    ...
  end
  return animate
```

## Script Types

### behavior

Entity lifecycle scripts attached via `behaviors: [name]` in YAML.

**Valid hooks**: `on_spawn`, `on_update`, `on_destroy`, `on_hit`

**Config access**: `ams.get_config(entity_id, "behavior_name", "key", default)`

```yaml
type: behavior
provides:
  hooks: [on_spawn, on_update]
config:
  speed:
    type: float
    default: 100
```

### collision_action

Two-entity interaction handlers triggered by collision rules.

**Valid hooks**: `execute`

**Signature**: `execute(entity_a_id, entity_b_id, modifier)`

**Config source**: `modifier` table from collision_behaviors YAML

```yaml
type: collision_action
provides:
  hooks: [execute]
config:  # Documents the modifier fields
  amount:
    type: int
    default: 1
```

### generator

Property value generators called at entity spawn time.

**Valid hooks**: `generate`

**Signature**: `generate(args)` returns computed value

```yaml
type: generator
provides:
  hooks: [generate]
args:  # Documents the args table
  index:
    type: int
    required: true
  start:
    type: float
    default: 0
```

### input_action

User input event handlers.

**Valid hooks**: `execute`

**Signature**: `execute(x, y, args)`

```yaml
type: input_action
provides:
  hooks: [execute]
args:
  particle_type:
    type: string
    default: spark
```

## Config Parameter Schema

Each config/args parameter can have:

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Required. `int`, `float`, `string`, `bool`, `array`, `object` |
| `description` | string | Human-readable description |
| `default` | any | Default value if not specified |
| `required` | bool | Whether parameter must be provided (default: false) |
| `min` | number | Minimum value (for int/float) |
| `max` | number | Maximum value (for int/float) |
| `enum` | array | Allowed values (for string) |
| `items` | object | Item schema (for array type) |

## Inline Scripts in game.yaml

For simple, game-specific scripts that don't warrant separate files, a subset schema allows embedding directly in `game.yaml`.

### Use Cases

1. **One-off behaviors**: Game-specific logic that won't be reused
2. **Quick prototyping**: Test ideas without creating files
3. **Simple generators**: Inline property calculations
4. **Game-specific collision actions**: Custom interactions

### Schema Differences

| Field | File (.lua.yaml) | Inline (game.yaml) |
|-------|------------------|-------------------|
| `type` | Required | Inferred from context |
| `name` | Optional (from filename) | Required |
| `code` | Required | Required |
| `description` | Optional | Optional |
| `version` | Optional | Omitted |
| `author` | Optional | Omitted |
| `tags` | Optional | Omitted |
| `config` | Optional | Optional |
| `args` | Optional | Optional |
| `provides` | Optional | Optional |
| `requires` | Optional | Omitted |
| `examples` | Optional | Omitted |

### Inline Schema Location

`ams/games/game_engine/lua/lua_script_inline.schema.json`

Referenced from the main game.yaml schema via `$ref`.

### Example: Inline Behavior

```yaml
# game.yaml
entity_types:
  special_enemy:
    behaviors: [gravity, my_custom_behavior]

inline_behaviors:
  my_custom_behavior:
    description: Wobble side to side
    provides:
      hooks: [on_update]
    code: |
      local my_custom_behavior = {}
      function my_custom_behavior.on_update(entity_id, dt)
        local x = ams.get_x(entity_id)
        local wobble = math.sin(ams.get_time() * 5) * 10
        ams.set_x(entity_id, x + wobble * dt)
      end
      return my_custom_behavior
```

### Example: Inline Generator

```yaml
# game.yaml
inline_generators:
  random_color:
    description: Generate a random RGB color
    args:
      saturation:
        type: float
        default: 1.0
    provides:
      hooks: [generate]
    code: |
      local random_color = {}
      function random_color.generate(args)
        local s = args.saturation or 1.0
        return string.format("#%02x%02x%02x",
          math.floor(ams.random() * 255 * s),
          math.floor(ams.random() * 255 * s),
          math.floor(ams.random() * 255 * s))
      end
      return random_color

entity_types:
  particle:
    color: {call: random_color, args: {saturation: 0.8}}
```

### Example: Inline Collision Action

```yaml
# game.yaml
inline_collision_actions:
  explode_on_contact:
    description: Destroy both entities and spawn particles
    provides:
      hooks: [execute]
    code: |
      local explode_on_contact = {}
      function explode_on_contact.execute(a_id, b_id, modifier)
        local x = ams.get_x(a_id)
        local y = ams.get_y(a_id)
        for i = 1, 5 do
          ams.spawn("particle", x, y)
        end
        ams.destroy(a_id)
        ams.destroy(b_id)
      end
      return explode_on_contact

collision_behaviors:
  bomb:
    enemy:
      action: explode_on_contact
```

### game.yaml Integration Points

New top-level keys in game.yaml:
- `inline_behaviors: {name: script_def, ...}`
- `inline_collision_actions: {name: script_def, ...}`
- `inline_generators: {name: script_def, ...}`
- `inline_input_actions: {name: script_def, ...}`

These are loaded after file-based scripts, allowing overrides.

### Validation

1. Inline scripts validated against `lua_script_inline.schema.json`
2. `name` is the key in the dict (required, must be valid identifier)
3. `type` is inferred from which `inline_*` section contains it
4. All other fields follow the subset rules above

## Migration Path

1. **Phase 1**: Add YAML loader that can read both `.lua` and `.lua.yaml` files
2. **Phase 2**: Convert engine scripts to `.lua.yaml` format
3. **Phase 3**: Update documentation and examples

## Decisions

| Question | Decision |
|----------|----------|
| File extension | `.lua.yaml` |
| Schema location | `ams/games/game_engine/lua/lua_script.schema.json` |
| Migration tooling | Not needed (few scripts) |
| Code block style | Literal block `|` for readability |

## Files

| File | Purpose |
|------|---------|
| `ams/games/game_engine/lua/lua_script.schema.json` | JSON Schema for validation |
| `ams/games/game_engine/lua/behavior/animate.lua.yaml` | Example behavior |
| `ams/games/game_engine/lua/collision_action/take_damage.lua.yaml` | Example collision_action |

## Example: Full Behavior

```yaml
# yaml-language-server: $schema=../lua_script.schema.json
type: behavior
name: gravity
description: Apply gravitational acceleration to entity velocity
version: "1.0"
tags: [physics, motion]

config:
  acceleration:
    type: float
    description: Downward acceleration in pixels/second^2
    default: 400
    min: 0
  terminal_velocity:
    type: float
    description: Maximum fall speed
    default: 800
    min: 0

provides:
  hooks:
    - on_update

requires:
  api: [get_vy, set_vy, get_config]

examples:
  - title: Standard gravity
    yaml: |
      behaviors: [gravity]
      behavior_config:
        gravity:
          acceleration: 400

  - title: Low gravity (moon)
    yaml: |
      behaviors: [gravity]
      behavior_config:
        gravity:
          acceleration: 60
          terminal_velocity: 200

code: |
  local gravity = {}

  function gravity.on_update(entity_id, dt)
      local accel = ams.get_config(entity_id, "gravity", "acceleration", 400)
      local terminal = ams.get_config(entity_id, "gravity", "terminal_velocity", 800)

      local vy = ams.get_vy(entity_id)
      vy = vy + accel * dt

      if vy > terminal then
          vy = terminal
      end

      ams.set_vy(entity_id, vy)
  end

  return gravity
```
