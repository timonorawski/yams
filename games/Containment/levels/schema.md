# Containment Level YAML Schema

This document defines the YAML format for Containment levels.

## Overview

Levels separate **mechanics** (code) from **level design** (data), allowing:
- Rapid iteration without code changes
- Community/designer level creation
- A/B testing configurations
- Campaign/progression systems

## Example Level

```yaml
# levels/dynamic_chaos.yaml
name: "Spinning Chaos"
description: "Dodge rotating obstacles while building walls"
difficulty: 3
author: "core"
version: 1

# === OBJECTIVES ===
objectives:
  type: survive        # survive | capture
  time_limit: 60       # seconds (null = endless)
  # For capture mode:
  # capture_zone:
  #   position: [0.5, 0.9]  # normalized [0-1]
  #   radius: 0.08

# === BALL ===
ball:
  count: 1
  speed: 150           # pixels/second (base, modified by tempo)
  radius: 20
  spawn: center        # center | random | [x, y] position
  ai: dumb             # dumb | reactive | strategic

# === ENVIRONMENT ===
environment:
  # Screen edge behavior
  edges:
    mode: bounce       # bounce (dynamic) | gaps (classic)
    # For gaps mode:
    # gaps:
    #   - edge: top
    #     range: [0.3, 0.5]  # normalized start/end

  # Rotating obstacles
  spinners:
    - position: [0.25, 0.4]
      shape: triangle
      size: 70
      rotation_speed: 45    # degrees/sec, negative = CCW

    - position: [0.75, 0.4]
      shape: square
      size: 80
      rotation_speed: -35

    - position: [0.5, 0.7]
      shape: pentagon
      size: 60
      rotation_speed: 50

# === HIT MODES ===
# Defines what happens when player shoots
hit_modes:
  selection: random    # random | sequential | weighted
  modes:
    - type: deflector
      weight: 3        # Used if selection: weighted
      config:
        angle: random  # random | fixed | toward_ball | away_from_ball
        length: 60

    - type: spinner
      weight: 1
      config:
        shape: random  # random | triangle | square | pentagon | hexagon
        size: 50
        rotation_speed: [30, 60]  # random range

    - type: point
      weight: 2
      config:
        radius: 15

# === PACING OVERRIDES ===
# Optional per-pacing adjustments (merged with base config)
pacing:
  archery:
    ball.speed: 80
    hit_modes.modes[0].config.length: 80  # Longer deflectors
  blaster:
    ball.speed: 220
    hit_modes.modes[0].config.length: 40  # Shorter deflectors
```

## Schema Reference

### Top Level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Display name |
| `description` | string | no | Short description |
| `difficulty` | int (1-5) | no | Difficulty rating |
| `author` | string | no | Level creator |
| `version` | int | no | Schema version |

### objectives

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | survive | `survive` or `capture` |
| `time_limit` | int/null | 60 | Seconds to survive, null=endless |
| `capture_zone.position` | [x, y] | - | Normalized position for capture mode |
| `capture_zone.radius` | float | - | Capture zone size (normalized) |

### ball

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `count` | int | 1 | Number of balls |
| `speed` | float | 150 | Base speed in px/sec |
| `radius` | float | 20 | Ball radius in pixels |
| `spawn` | string/[x,y] | center | `center`, `random`, or [x, y] |
| `ai` | string | dumb | `dumb`, `reactive`, `strategic` |

### environment.edges

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | string | bounce | `bounce` (all edges solid) or `gaps` |
| `gaps` | array | [] | Gap definitions for gaps mode |
| `gaps[].edge` | string | - | `top`, `bottom`, `left`, `right` |
| `gaps[].range` | [start, end] | - | Normalized position range |

### environment.spinners[]

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `position` | [x, y] | - | Normalized center position |
| `shape` | string | triangle | `triangle`, `square`, `pentagon`, `hexagon` |
| `size` | float | 60 | Radius from center to vertices |
| `rotation_speed` | float | 45 | Degrees/sec (negative = CCW) |

### hit_modes

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `selection` | string | random | How to pick mode: `random`, `sequential`, `weighted` |
| `modes` | array | - | Available hit mode definitions |

### hit_modes.modes[] - Common Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Hit mode type (see below) |
| `weight` | int | Weight for weighted selection (default: 1) |
| `config` | object | Type-specific configuration |

### Hit Mode Types

#### `deflector` - Line segment wall
```yaml
type: deflector
config:
  angle: random        # random | fixed | toward_ball | away_from_ball
  fixed_angle: 45      # degrees, used if angle: fixed
  length: 60           # line segment length
  color: null          # null = use palette
```

#### `spinner` - Rotating polygon (spawned by player)
```yaml
type: spinner
config:
  shape: random        # random | triangle | square | pentagon | hexagon
  size: 50             # or [min, max] for random range
  rotation_speed: 45   # or [min, max] for random range
  color: null
```

#### `point` - Simple circular obstacle
```yaml
type: point
config:
  radius: 15           # or [min, max]
  color: null
```

#### `connect` - Connect-the-dots (creates wall to nearby hits)
```yaml
type: connect
config:
  threshold: 100       # max distance to connect
  fallback: point      # what to create if no nearby hits
  fallback_config:
    radius: 15
```

#### `morph` - Shape that changes over time
```yaml
type: morph
config:
  shapes: [triangle, square, pentagon]
  morph_interval: 2.0  # seconds between changes
  size: 50
  rotation_speed: 30
  pulsate: true        # size oscillation
  pulsate_amount: 0.15 # ±15% size
```

#### `grow` - Grows when hit again
```yaml
type: grow
config:
  initial_size: 30
  growth_per_hit: 0.3  # +30% per additional hit inside
  max_size: 150
  shape: circle        # circle | current spinner shape
  decay_rate: 0        # size loss per second (0 = permanent)
```

### pacing (optional overrides)

Dot-notation paths to override values per pacing preset:

```yaml
pacing:
  archery:
    ball.speed: 80
    ball.radius: 25
    hit_modes.modes[0].config.length: 80
  throwing:
    ball.speed: 150
  blaster:
    ball.speed: 220
    hit_modes.modes[0].config.length: 40
```

## Selection Modes

### `random`
Each hit randomly picks from available modes (equal probability unless weighted).

### `sequential`
Cycles through modes in order. First hit = first mode, second hit = second mode, etc.
Wraps around when exhausted.

### `weighted`
Random selection weighted by `weight` field. Higher weight = more likely.

```yaml
hit_modes:
  selection: weighted
  modes:
    - type: deflector
      weight: 5        # 5/8 = 62.5% chance
    - type: spinner
      weight: 2        # 2/8 = 25% chance
    - type: point
      weight: 1        # 1/8 = 12.5% chance
```

## File Organization

```
games/Containment/levels/
├── schema.md              # This file
├── tutorial/
│   ├── 01_basics.yaml
│   ├── 02_spinners.yaml
│   └── 03_connect.yaml
├── campaign/
│   ├── 01_warmup.yaml
│   ├── 02_spinning_gates.yaml
│   └── ...
├── challenge/
│   ├── chaos.yaml
│   ├── architect.yaml
│   └── minefield.yaml
└── examples/
    ├── classic_mode.yaml
    ├── dynamic_mode.yaml
    └── mixed_hits.yaml
```

## Backwards Compatibility

Levels without `hit_modes` default to:
```yaml
hit_modes:
  selection: random
  modes:
    - type: deflector
      config:
        angle: random
        length: 60
```

This matches current behavior (random-angle deflectors).
