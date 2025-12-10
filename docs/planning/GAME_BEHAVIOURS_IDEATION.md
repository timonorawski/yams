**AMS Behavior System — Design Document**

## Overview

AMS games are defined by three layers:

1. **Engine (Python/pygame)** — Runs the game loop, renders sprites, handles input, manages the Lua VM
2. **Behaviors (Lua)** — Imperative logic that defines how entities act
3. **Game definitions (YAML)** — Declarative descriptions that compose behaviors into playable games

The engine is fixed. Behaviors are a library that grows. Games are data.

## Architectural Principle

All behaviors — including those shipped with AMS — run in a sandboxed Lua VM. There is no privileged code path for "core" behaviors. If a behavior cannot be implemented against the Lua API, the API must be extended.

This guarantees:
- User-uploaded behaviors are safe (no filesystem, network, or OS access)
- Identical execution on native Python and pygame-wasm
- Core behaviors serve as working examples and test cases for the API

## The Three Layers

### Engine (Python)

Responsibilities:
- Initialize pygame and the Lua VM (Wasmoon)
- Load game definitions (YAML)
- Load and register behaviors (Lua)
- Run the game loop: input → update → render
- Expose a safe API to Lua for entity manipulation, sound, scoring

Does not contain:
- Game-specific logic
- Behavior implementations
- Entity definitions

### Behaviors (Lua)

A behavior is a Lua module that attaches logic to an entity. Behaviors respond to lifecycle events:

- `on_update(entity, dt)` — called every frame
- `on_hit(entity, other)` — called on collision
- `on_destroy(entity)` — called when entity is removed
- `on_spawn(entity)` — called when entity is created

**Core Behaviors Shipping with AMS**

| Behavior | Purpose |
|----------|---------|
| `descend` | Move downward (fixed, step, or wave pattern) |
| `shoot` | Fire projectiles at intervals |
| `transform` | Change sprite/properties, entity persists |
| `split` | Spawn child entities on trigger |
| `thrust` | Player movement with momentum |
| `rhythm_gate` | Require input on beat |
| `transmute` | Spawn children + destroy self (composite) |

These are not special. They are the first entries in the behavior library.

**A note on transmute:**

Transmutation is the act of an entity becoming something fundamentally different — a yellow asteroid becomes an attacker ship while jettisoning debris.

Mechanically, this is:
1. Spawn new entity (the attacker ship) at current position
2. Spawn additional entities (asteroid fragments) with outward velocity
3. Destroy the original entity

This could be implemented as:
- **A distinct behavior** (`transmute.lua`) that encapsulates the pattern
- **A YAML composition** of `split` + `destroy`

Both approaches are valid. The argument for a dedicated `transmute` behavior:
- Common enough pattern to deserve a name
- Cleaner YAML for level designers
- Can encapsulate details like inheritance of velocity, spawn positioning, visual effects

The argument for composition:
- Fewer primitives to maintain
- Forces the API to be expressive enough for composition
- Level designers learn the building blocks

**Recommendation:** Implement `transmute` as a behavior, but build it on top of the same API that `split` and `transform` use. It's a convenience, not a primitive. If `transmute.lua` needs API methods that `split.lua` doesn't, that's a sign the API is incomplete.


### Game Definitions (YAML)

A YAML file defines a game or level: what entities exist, what behaviors they have, how they're configured.

```yaml
level:
  name: "Duck Invaders"
  
entities:
  - type: alien
    sprite: invader.png
    grid: [8, 3]
    spacing: [40, 30]
    behaviors:
      - descend:
          speed: 20
          pattern: step
      - shoot:
          interval: 3.0
          projectile: alien_laser

  - type: player
    sprite: ship.png
    position: [160, 220]
    behaviors:
      - thrust:
          max_speed: 120
      - shoot:
          key: space
          projectile: player_bullet

events:
  alien.on_hit:
    - transform:
        to: duck
        sprite: duck.png
    - play_sound: quack.wav
    - add_score: 100
```

The YAML schema will be discovered during implementation. The above is illustrative, not prescriptive.

## Lua API Surface

Behaviors need to read game state and request mutations. The API must be:
- **Sufficient** — Core behaviors can be fully implemented
- **Safe** — No access to filesystem, network, OS
- **Symmetric** — Same API on native and WASM

Anticipated API areas:

**Entity access:**
- Get position, velocity, sprite, health
- Set position, velocity, sprite
- Destroy entity
- Spawn new entity

**Game state:**
- Current score, time, level
- Player reference
- Entity queries (get all entities of type X)

**Events:**
- Schedule a callback after N seconds
- Play sound
- Trigger screen shake, flash, etc.

The exact API will be defined by implementing the core behaviors. Each behavior that can't be written reveals a missing API method.

## Execution Model

1. Engine starts, initializes Lua VM
2. Engine loads game YAML
3. For each behavior referenced, engine loads the .lua file into the VM
4. Engine creates entities, attaches behavior instances
5. Game loop runs:
   - Input is captured (Python), passed to Lua as needed
   - `on_update` called for all behaviors
   - Collisions detected (Python), `on_hit` called for relevant behaviors
   - Render (Python) using current entity state
6. On entity destruction, `on_destroy` called

All Lua calls are wrapped in error handling. A failing behavior is disabled, not fatal.

## Platform Parity

Native (pygame-ce):
- Wasmoon Python package embeds Lua VM
- Lua files loaded from disk

Browser (pygame-wasm via pygbag):
- Wasmoon JS runs in browser
- Lua files fetched or bundled
- Python ↔ JS bridge forwards API calls

Same Lua code runs in both environments. Platform differences are isolated to the engine layer.

## Open Questions

To be resolved during implementation:

- **State management:** Where do behaviors store persistent data between frames?
- **Behavior composition:** Can multiple behaviors of the same type attach to one entity?
- **Event ordering:** When multiple behaviors respond to `on_hit`, what order do they run?
- **Hot reloading:** Can behaviors be modified without restarting the game?
- **Error recovery:** Exact UX when a behavior fails — disable it? Show warning? Reset level?

## Implementation Sequence

1. Embed Wasmoon in Python, verify basic Lua execution
2. Design minimal API by implementing `descend` behavior
3. Expand API as needed for `shoot`, `transform`, `split`
4. Build YAML loader that instantiates entities with behaviors
5. Implement `thrust` and `rhythm_gate` (player-facing behaviors)
6. Port to pygame-wasm, verify parity
7. Document API, ship examples
