# YAML Behavior Bundles

**Status**: In Progress
**Goal**: Unify behaviors and interactions - behaviors become pure YAML collections of interactions

## Cleanup Completed

Pastured legacy code to eliminate confusion:

**Lua folders pastured** (`pasture/lua_legacy/`):
- `behavior/` - Lua behaviors with lifecycle hooks
- `collision_action/` - Legacy collision handlers
- `test_script_loader.py` - Tests for legacy system

**Games pastured** (`pasture/games_legacy_format/`):
- BrickBreakerNG, DuckHuntNG, FruitSliceNG, GroupingNG, LoveOMeterNG, RopeTestNG, SweetPhysicsNG
- These used legacy `collision_behaviors`, `input_mapping` instead of `interactions`
- Kept as reference for reimplementation

**New simplified structure**:
```
ams/games/game_engine/lua/
├── actions/          # Renamed from interaction_action
├── behaviors/        # NEW: Pure YAML bundles (empty, ready for implementation)
├── generator/        # Kept: Still needed for spawn-time value generation
└── script_loader.py
```

**Games remaining**: BrickBreakerUltimate (uses interactions system)

## Previous State

Behaviors were Lua scripts with lifecycle hooks:

```lua
-- behavior/gravity.lua.yaml
local gravity = {}

function gravity.on_spawn(entity_id)
    -- init
end

function gravity.on_update(entity_id, dt)
    local accel = ams.get_config(entity_id, "gravity", "acceleration", 600)
    local vy = ams.get_vy(entity_id) + accel * dt
    ams.set_vy(entity_id, vy)
    ams.set_y(entity_id, ams.get_y(entity_id) + vy * dt)
end

function gravity.on_destroy(entity_id)
    -- cleanup
end

return gravity
```

**Problems:**
- Two mental models: behaviors (Lua with hooks) vs interactions (YAML declarative)
- Behaviors have implicit lifecycle coupling (`on_spawn`, `on_update`, `on_destroy`)
- Hard to see what a behavior actually does without reading Lua
- Behaviors can't easily compose with interactions

## Target State

Behaviors become pure YAML - bundled collections of interactions:

```yaml
# behavior/gravity.yaml
name: gravity
description: Apply gravity acceleration and velocity-based movement

config:
  acceleration:
    type: number
    default: 600

interactions:
  level:
    because: continuous
    action: apply_gravity
    modifier:
      acceleration: $config.acceleration
```

**Benefits:**
- One unified model: everything is interactions
- Behaviors are declarative and inspectable
- Clear what triggers fire and what actions run
- Composable - behaviors just merge their interactions
- Lua only exists in interaction actions (tightly scoped)

## Behavior Format Specification

### File Structure

```
ams/games/game_engine/behaviors/
├── gravity.yaml
├── bounce.yaml
├── animate.yaml
├── destroy_offscreen.yaml
├── paddle.yaml
└── ...
```

### Schema

```yaml
# Required
name: string           # Behavior identifier

# Optional
description: string    # Human-readable description

config:                # Configurable parameters
  param_name:
    type: number|string|boolean|array
    default: any       # Default value
    description: string

interactions:          # Interaction definitions (same syntax as entity_types.X.interactions)
  target_entity:
    when: ...
    because: enter|exit|continuous
    action: string | {lua: string}
    modifier: ...
```

### Config Substitution

Use `$config.X` in modifier values to reference config parameters:

```yaml
config:
  speed: 300

interactions:
  level:
    because: continuous
    action: move_forward
    modifier:
      speed: $config.speed
```

### Multiple Interactions

Behaviors can define multiple interactions:

```yaml
name: bounce

config:
  walls: all
  speed: 300

interactions:
  level:
    because: continuous
    action: apply_velocity
    modifier:
      speed: $config.speed

  screen:
    - edges: [left, right]
      action: bounce_horizontal
    - edges: [top, bottom]
      action: bounce_vertical
```

## Migration: Existing Behaviors

### gravity.lua.yaml → gravity.yaml

```yaml
name: gravity

config:
  acceleration:
    default: 600

interactions:
  level:
    because: continuous
    action: apply_gravity
    modifier:
      acceleration: $config.acceleration
```

**Requires action:** `apply_gravity` - applies acceleration to vy, then velocity to position.

### destroy_offscreen.lua.yaml → destroy_offscreen.yaml

```yaml
name: destroy_offscreen

config:
  margin:
    default: 50

interactions:
  screen:
    when:
      distance: 0
    because: exit
    action: destroy_self
```

No new action needed - uses existing `destroy_self`.

### animate.lua.yaml → animate.yaml

```yaml
name: animate

config:
  frames:
    default: 3
  fps:
    default: 8

interactions:
  level:
    because: continuous
    action: cycle_frame
    modifier:
      frames: $config.frames
      fps: $config.fps
```

**Requires action:** `cycle_frame` - increments frame property based on fps.

### bounce.lua.yaml → bounce.yaml

```yaml
name: bounce

config:
  walls:
    default: all
  min_y:
    default: null
  max_y:
    default: null

interactions:
  level:
    because: continuous
    action: apply_velocity

  screen:
    - edges: [left, right]
      when:
        a.bounce_walls: {in: [all, sides, top_sides]}
      action: bounce_horizontal

    - edges: [top]
      when:
        a.bounce_walls: {in: [all, top_sides]}
      action: bounce_vertical

    - edges: [bottom]
      when:
        a.bounce_walls: all
      action: bounce_vertical
```

Note: This may need refinement - the `walls` config needs to be accessible as entity property or the filter needs adjustment.

### paddle.lua.yaml → paddle.yaml

```yaml
name: paddle

config:
  speed:
    default: 500

interactions:
  pointer:
    because: continuous
    action: track_pointer_x

  level:
    because: continuous
    action: move_toward_target
    modifier:
      speed: $config.speed
```

Uses existing actions.

## New Interaction Actions Needed

To support the behavior migrations, we need these atomic actions:

| Action | Purpose | Modifier |
|--------|---------|----------|
| `apply_velocity` | Add vx/vy to x/y | - |
| `apply_gravity` | Add acceleration to vy, then apply velocity | `acceleration` |
| `cycle_frame` | Increment frame property for animation | `frames`, `fps` |
| `oscillate` | Side-to-side movement | `speed`, `range` |
| `descend` | Move downward | `speed` |

Most existing behaviors map to 1-2 simple actions.

## Implementation Plan

### Phase 1: Infrastructure

1. Create `BehaviorLoader` class to load YAML behavior definitions
2. Add config substitution logic (`$config.X` → actual values)
3. Modify `GameEngine` to merge behavior interactions into entity types
4. Update `InteractionEngine` to handle merged interactions

### Phase 2: Action Library

1. Create missing interaction actions:
   - `apply_velocity`
   - `apply_gravity`
   - `cycle_frame`
   - `oscillate`
   - `descend`

2. Ensure all actions follow the standard signature:
   ```lua
   function action.execute(entity_id, other_id, modifier, context)
   ```

### Phase 3: Migrate Behaviors

Convert existing Lua behaviors to YAML:

1. `gravity` - straightforward
2. `destroy_offscreen` - already works with screen exit
3. `animate` - needs cycle_frame action
4. `bounce` - needs thought about walls config
5. `paddle` - uses existing actions
6. `oscillate` - needs oscillate action
7. `descend` - needs descend action
8. `projectile` - velocity + destroy_offscreen
9. `shoot` - timer + spawn
10. `fade_out` - continuous opacity reduction

### Phase 4: Cleanup

1. Remove Lua behavior loading code
2. Remove `behavior/*.lua.yaml` files
3. Update documentation
4. Update game-author agent prompt

## Backward Compatibility

### Transition Period

Support both formats during migration:
- If `behavior/X.yaml` exists, use YAML bundle
- If `behavior/X.lua.yaml` exists, use legacy Lua
- YAML takes precedence

### Inline Lua in Games

Game authors can still write inline Lua actions:

```yaml
entity_types:
  custom_enemy:
    interactions:
      time:
        when:
          elapsed: {gte: 3.0}
        action:
          lua: |
            -- Custom spawn logic
            local x = ams.random_range(100, 700)
            ams.spawn("minion", x, 0, 0, 100)
            ams.transform(entity_id, "custom_enemy")
```

This is encouraged for game-specific logic. The change only affects reusable behavior definitions.

## Open Questions

1. **Config as entity properties**: Should `$config.X` values be copied to entity properties at spawn time? This would allow filters like `a.bounce_walls: all` to work.

2. **Behavior composition order**: When entity has `behaviors: [A, B]` and both define interactions with same target, how to merge? Options:
   - Append (both fire)
   - Last wins
   - Explicit override syntax

3. **Behavior inheritance**: Should behaviors be able to extend other behaviors?
   ```yaml
   name: gravity_strong
   extends: gravity
   config:
     acceleration: 1200
   ```

## Success Criteria

- [ ] All 15 existing behaviors converted to YAML
- [ ] No Lua behavior loading code remains
- [ ] Games using behaviors continue to work
- [ ] game-author agent prompt updated
- [ ] Developer documentation updated
- [ ] Tests pass
