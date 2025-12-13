# Unified Interaction System
**Status:** RFC / Design Discussion
**Goal:** Unify all entity interactions (collisions, clicks, proximity) under a single conceptual model.

## Core Insight

All actions on an entity can be distilled to an **interaction between two entities** with a **declarative filter**.

| Current System | Entity A | Entity B | Filter |
|----------------|----------|----------|--------|
| Collision | `ball` | `brick` | distance = 0 |
| Click (on_hit) | `duck` | `system::pointer` | distance = 0, pointer.active |
| Proximity (new) | `player` | `enemy` | distance < 100 |

## Proposed Model

```
Interaction = (Entity A, Entity B, Filter, Handler)
```

All interaction handlers become **interaction actions** with uniform signature.

## Sketch: YAML Format

Interactions are a **property of the entity type**, not a separate section:

```yaml
entity_types:
  ball:
    width: 16
    height: 16
    properties:
      speed: 300

    interactions:
      # Collision with brick
      brick:
        when:
          distance: 0
        action: bounce_reflect

      # Multiple screen interactions
      screen:
        - edges: [bottom]
          action: ball_lost
        - edges: [left, right]
          action: bounce_horizontal

  duck:
    interactions:
      # Click/hit detection
      pointer:
        when:
          distance: 0
          b.active: true
        action: destroy_target
        modifier:
          points: 100

  player:
    interactions:
      # Proximity trigger
      enemy:
        when:
          distance: { lt: 100 }
        action: trigger_alert
        because: enter
```

Benefits:
- Co-located with entity definition
- Inheritance works naturally (subtypes inherit interactions)
- Multiple interactions per target use array syntax

## Open Questions

### 1. System Entities
What virtual entities exist for input/system events?

~~Options:~~
~~- `system::pointer` - current input position~~
~~- `system::hit` - confirmed hit event~~

**Simpler approach:** No special namespace syntax. A pointer is just an entity with attributes:

```yaml
# Implicit system entity
pointer:
  source: system     # Attribute distinguishes system vs game entities
  x: ...
  y: ...
  active: false      # True when click/hit occurs
```

Interactions reference it by name like any other entity:
```yaml
interactions:
  duck:
    pointer:
      when:
        distance: 0
        b.active: true    # Filter on pointer's active attribute
      action: destroy_target
```

**Decision:** No namespace syntax. System entities are regular entities with `source: system` attribute.

The `source` attribute is extensible:
- `source: system` - engine-provided (pointer, screen)
- `source: game` - defined in game.yaml
- `source: level` - defined in level file
- `source: spawned` - created at runtime via `ams.spawn()`

### Pointer Entity

The pointer is a **full entity with bounds**, not just a point. Size varies by input method:

| Input Method | Typical Size | Notes |
|--------------|--------------|-------|
| Mouse click | 1x1 | Point-like |
| Touch | ~40x40 | Finger-sized |
| Object detection | varies | Actual detected object size |
| Laser pointer | ~10x10 | Detected spot size |

```yaml
# Pointer as entity (managed by engine, updated each frame)
pointer:
  space: system
  x: 450
  y: 300
  width: 40        # Touch-sized
  height: 40
  active: false    # True on click/hit event
  input_type: touch  # mouse | touch | object | laser
```

This means pointer↔entity interaction uses the same AABB distance calculation as entity↔entity. No special case needed.

### Screen Entity

Single `screen` entity - just bounds, no special attributes. Edge detection uses the computed interaction `angle`.

```yaml
screen:
  source: system
  x: 0
  y: 0
  width: 800
  height: 600
```

Use `edges` shorthand to specify which edges trigger the interaction:

```yaml
interactions:
  # Ball hitting bottom = lose life
  ball:
    screen:
      edges: [bottom]
      action: lose_life

  # Ball hitting sides = bounce
  ball:
    screen:
      edges: [left, right]
      action: bounce_horizontal

  # Projectile hitting any edge = destroy
  projectile:
    screen:
      edges: [top, bottom, left, right]  # Or omit for "any"
      action: destroy
```

The `edges` list is sugar that expands to angle range filters:
- `top` → `angle: { between: [45, 135] }`
- `left` → `angle: { between: [135, 225] }`
- `bottom` → `angle: { between: [225, 315] }`
- `right` → `angle: { between: [315, 360] }` or `{ between: [0, 45] }`

**Decision:** `screen` is just a bounds entity. `edges` shorthand expands to computed `angle` filters.

> **Implementation note:** Under the hood, these become optimized intersection calculations (AABB tests, spatial partitioning, etc.). The declarative syntax hides that complexity.

### Level Entity

The `level` entity represents the game world itself. Lifecycle hooks become interactions:

```yaml
entity_types:
  ball:
    interactions:
      # on_spawn = enter level
      level:
        because: enter
        action: initialize_velocity

      # on_update = continuous with level
      level:
        because: continuous
        action: apply_physics

      # on_destroy = exit level
      level:
        because: exit
        action: spawn_particles
```

This unifies lifecycle hooks with the interaction model.

### System Entities Summary

| Entity | Attributes | Purpose |
|--------|------------|---------|
| `pointer` | x, y, width, height, active, input_type | Input/click/hit |
| `screen` | x, y, width, height | Play area bounds |
| `level` | (implicit) | Lifecycle: spawn/update/destroy |
| `game` | lives, score, state | Game state |

### Interaction Attributes (Computed)

Beyond entity attributes (`a.*`, `b.*`), interactions have **computed attributes** available for filtering:

| Attribute | Description |
|-----------|-------------|
| `distance` | Distance between A and B (AABB edge-to-edge) |
| `angle` | Angle from A to B (0=right, 90=up, 180=left, 270=down) |
| `relative_velocity` | Closing speed? |

This enables direction-sensitive interactions:

```yaml
interactions:
  # Ball bounces differently based on which side of brick it hits
  ball:
    brick:
      when:
        distance: 0
        angle: { between: [45, 135] }   # Hit from below
      action: bounce_vertical

  ball:
    brick:
      when:
        distance: 0
        angle: { between: [135, 225] }  # Hit from left
      action: bounce_horizontal

  # Enemy only triggers alert when approaching from behind
  enemy:
    player:
      when:
        distance: { lt: 100 }
        angle: { between: [135, 225] }  # Behind player
      action: ambush_alert

  # Screen edge just uses same mechanism
  ball:
    screen:
      when:
        distance: 0
        angle: 270                      # Ball moving downward into screen bottom
      action: lose_life
```

**Decision:** `angle` and `distance` are computed interaction attributes, not entity attributes. Available in all interaction filters.

### 2. Distance Semantics

Collision is just an interaction with `distance: 0`. Specify where to measure from/to:

```yaml
interactions:
  # AABB collision (edge-to-edge, current behavior)
  ball:
    brick:
      when:
        distance: 0
        from: edge          # Measure from A's edge
        to: edge            # To B's edge (default)
      action: bounce

  # Proximity by center distance
  player:
    powerup:
      when:
        distance: { lt: 50 }
        from: center
        to: center
      action: collect

  # Radial effect from center to edge
  explosion:
    enemy:
      when:
        distance: { lt: 100 }
        from: center        # Explosion center
        to: edge            # Enemy's nearest edge
      action: damage
```

| from | to | Distance = 0 means | Use case |
|------|-----|-------------------|----------|
| `edge` | `edge` | AABB overlap (default) | Collisions |
| `center` | `center` | Centers coincide | Proximity triggers |
| `center` | `edge` | A's center touches B's edge | Radial effects |

**Decision:** `from: edge, to: edge` is default (collision). Explicit `from`/`to` for other measurements.

> **Performance:** Spatial partitioning (quadtree, spatial hash) avoids O(n²). Only check pairs within relevant cells/regions.

### 3. Filter Attributes

Filters can test **any attribute**. The system is fully generic.

```yaml
interactions:
  player:
    enemy:
      when:
        distance: { lt: 100 }     # Computed interaction attribute
        b.health: { gt: 0 }       # Entity attribute
        b.state: "aggressive"     # Exact match
        a.has_shield: false       # Boolean
      action: take_damage
```

**Filter operators:**
- Exact: `attribute: value`
- Comparison: `{ lt: N }`, `{ gt: N }`, `{ lte: N }`, `{ gte: N }`
- Range: `{ between: [min, max] }`
- Set: `{ in: [a, b, c] }`

**Optimization:** Because filters are declarative, the compiler builds optimal data structures:
- `distance` filters → spatial partitioning (quadtree, spatial hash)
- Exact matches → hash lookups
- Common filters → precomputed indexes

Some attributes may be computed on-demand (generators) - less efficient, but allowed. The profiler makes costs visible.

**Decision:** Any attribute can be filtered. Compiler optimizes. Profiler exposes costs.

### 4. Trigger Modes

Just another attribute on the interaction:

```yaml
interactions:
  ball:
    brick:
      when:
        distance: 0
      because: enter        # Fire once when filter becomes true
      action: bounce

  player:
    danger_zone:
      when:
        distance: 0
      because: continuous   # Fire every frame while true
      action: take_damage

  ball:
    screen:
      edges: [bottom]
      because: enter        # Don't re-fire while still touching
      action: lose_life
```

| Trigger | Behavior |
|---------|----------|
| `enter` | Once when filter becomes true (default) |
| `exit` | Once when filter becomes false |
| `continuous` | Every frame while filter is true |

"Fire once ever" is handled by the action transforming the entity (destroy it, change a property so filter no longer matches, etc.) - not a trigger mode.

**Decision:** Three trigger modes: `enter` (default), `exit`, `continuous`.

### 5. Handler Signature

Uniform signature for all interaction handlers:

```lua
function handler.execute(entity_id, other_id, interaction)
    -- interaction contains all computed properties:
    -- interaction.distance    -- actual distance
    -- interaction.angle       -- angle from entity to other
    -- interaction.trigger     -- "enter" | "exit" | "continuous"
    -- interaction.modifier    -- config from yaml
    -- interaction.a           -- entity A's attributes
    -- interaction.b           -- entity B's attributes
end
```

Example:
```lua
local bounce = {}

function bounce.execute(entity_id, other_id, interaction)
    local angle = interaction.angle
    local speed_boost = interaction.modifier.speed_increase or 0

    -- Bounce logic using angle
    if angle > 45 and angle < 135 then
        -- Hit from below, reverse vy
        ams.set_vy(entity_id, -ams.get_vy(entity_id))
    else
        -- Hit from side, reverse vx
        ams.set_vx(entity_id, -ams.get_vx(entity_id))
    end
end

return bounce
```

**Decision:** `execute(entity_id, other_id, interaction)` - uniform for all handlers.

### 6. Backwards Compatibility

No users yet. Just rewrite existing games when implementing the new system.

**Decision:** No backwards compatibility needed. Migrate existing games.

### 7. Performance

Already addressed above:
- Spatial partitioning (quadtree, spatial hash) for distance checks
- Compiler optimizes declarative filters into efficient data structures
- Profiler exposes costs of expensive filters

**Decision:** Covered. Implementation will use spatial partitioning.

## Validation

The test of this design: **can we cleanly represent existing games in the new format?**

See `games/BrickBreakerUltimate/game.yaml` - full brick breaker in unified interactions format.

### What it replaces

| Old System | New Unified |
|------------|-------------|
| `collision_behaviors.ball.paddle` | `interactions.ball.paddle` |
| `collision_behaviors.ball.brick` | `interactions.ball.brick` |
| `collision_behaviors.brick.ball` | `interactions.brick.ball` |
| `collision_behaviors.projectile.paddle` | `interactions.projectile.paddle` |
| `lose_conditions[ball exited bottom]` | `interactions.ball.screen` with `edges: [bottom]` |
| `input_mapping.paddle.target_x` | `interactions.paddle.pointer` with `because: continuous` |
| `input_mapping.paddle_ready.on_input` | `interactions.paddle.pointer` with `b.active: true` filter |

### Observations

1. **Screen interactions are clean** - `edges: [bottom]` reads naturally
2. **Input is unified** - pointer is just another entity, `because: continuous` for tracking
3. **Click detection** - `b.active: true` filter on pointer
4. **Multiple interactions per pair** - paddle has both continuous tracking AND click-to-launch
5. **Wall bounces** - now explicit interactions, not hidden in behavior code

### Resolved issues

1. **Multiple interactions for same pair** - Array syntax:
   ```yaml
   screen:
     - edges: [bottom]
       action: ball_lost
     - edges: [left, right]
       action: bounce_horizontal
   ```

2. **Interactions as entity property** - cleaner than separate section, inheritance works

### Game Entity

Game state is an entity too:

```yaml
game:
  source: system
  lives: 3
  score: 0
  state: playing    # playing | paused | won | lost
```

System-level actions are just interactions with `game`:

```yaml
ball:
  interactions:
    screen:
      edges: [bottom]
      action: decrement_lives   # Modifies game.lives
```

The action can read/write `game.*` properties like any entity.

### Transform = Property Change

Changing entity type (paddle → paddle_ready) doesn't trigger exit/enter by default - the entity stays in the world, just changes its properties and interactions.

Transform is just:
1. Change `type` property
2. Swap in new type's interactions
3. Apply new type's default properties

Same entity identity, different "shape".

If needed, lifecycle triggers on transform can be explicit:

```yaml
paddle:
  interactions:
    level:
      because: exit
      when:
        because: transform    # Only fires on transform, not destroy
      action: cleanup_old_type
```

Default: no lifecycle triggers on transform. Opt-in if needed.

### Resolved: Behaviors vs Interactions

Behaviors are **replaced by interactions**:

| Behavior Hook | Interaction Equivalent |
|---------------|----------------------|
| `on_spawn` | `level` + `because: enter` |
| `on_update` | `level` + `because: continuous` |
| `on_destroy` | `level` + `because: exit` |
| `on_hit` | entity + `distance: 0` |

No more `behaviors: [ball, gravity]`. Just interactions.

## Summary

All questions resolved. The unified model:

| Concept | Implementation |
|---------|----------------|
| Collision | Entity interaction, `distance: 0` |
| Input/click | `pointer` interaction |
| Screen bounds | `screen` interaction with `edges` |
| Lifecycle (spawn/update/destroy) | `level` interaction with trigger |
| Game state (lives/score) | `game` entity |
| Transform | Property change, no lifecycle trigger |

Four system entities: `pointer`, `screen`, `level`, `game`

## Implementation Plan

### Phase 1: Core Interaction Engine

```
ams/interactions/
├── __init__.py
├── engine.py          # InteractionEngine - main loop
├── filter.py          # Filter evaluation
├── trigger.py         # Trigger state (enter/exit tracking)
├── system_entities.py # pointer, screen, level, game
└── spatial.py         # Spatial partitioning (later optimization)
```

**InteractionEngine responsibilities:**
1. Parse `interactions` from entity types
2. Each frame: evaluate all interaction filters
3. Track trigger states (was filter true last frame?)
4. Fire actions on trigger conditions
5. Manage system entities

### Phase 2: System Entities

| Entity | Implementation |
|--------|----------------|
| `pointer` | Updated by input system each frame |
| `screen` | Static bounds, edge detection via angle |
| `level` | Implicit, tracks entity membership |
| `game` | Properties: lives, score, state |

### Phase 3: Filter Evaluation

```python
class Filter:
    def evaluate(self, entity_a, entity_b, context) -> bool:
        # Check distance
        # Check angle
        # Check entity attributes (a.*, b.*)
        # Check edges shorthand
        pass
```

### Phase 4: Actions

Unified action signature:
```python
def execute(entity_id: str, other_id: str, interaction: dict):
    # interaction.distance, interaction.angle, interaction.modifier, etc.
    pass
```

### Decisions

1. **InteractionEngine as module** - attaches to GameEngine
   - GameEngine becomes game state + entity arbitrator
   - InteractionEngine handles all interaction logic

2. **Big bang approach** - build engine with tests, then attach
   - Games are small, migrate all at once

3. **Parser first** - validate syntax before engine exists

### Build Order

1. ✅ YAML schema for `interactions` format
2. ✅ Parser + tests (validate BrickBreakerUltimate)
3. ✅ System entities (pointer, screen, level, game, time)
4. ✅ Filter evaluator + tests
5. ✅ Trigger state manager + tests
6. ✅ Action dispatch + InteractionEngine
7. ⬜ Attach to GameEngine
8. ⬜ Migrate all games
9. ⬜ Remove old systems
10. ⬜ Spatial optimization (later)

## Implementation Status

**Completed (179 tests):**

| Module | File | Tests | Purpose |
|--------|------|-------|---------|
| Parser | `ams/interactions/parser.py` | 45 | Parse YAML interactions to dataclasses |
| Schema | `ams/interactions/schemas/interaction.schema.json` | - | JSON schema validation |
| System Entities | `ams/interactions/system_entities.py` | 39 | pointer, screen, level, game, time |
| Filter | `ams/interactions/filter.py` | 43 | Distance/angle calculation, filter evaluation |
| Trigger | `ams/interactions/trigger.py` | 31 | Enter/exit/continuous state tracking |
| Engine | `ams/interactions/engine.py` | 21 | Main orchestrator + action dispatch |

**Next Steps:**

1. Integrate with existing `GameEngine` in `ams/games/game_engine/`
2. Create action handlers for existing behaviors (bounce, destroy, etc.)
3. Migrate games to unified format
4. Remove legacy collision/behavior systems
