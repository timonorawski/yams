# YAML Game Engine Physics Support

## Problem Statement

The YAML game engine needs physics support for games like Sweet Physics (Cut the Rope style). Current limitations:

1. **No physics simulation** - YAML engine has gravity behavior but no real physics
2. **No constraint system** - Can't connect entities with joints/ropes
3. **Pymunk dependency** - Current SweetPhysics uses pymunk which has C bindings and **doesn't work in WASM**

## Requirements

### Must Have
- Work in WASM/browser (no C extensions)
- Integrate with YAML game engine and Lua behaviors
- Support rope physics with tension and swinging
- Support basic rigid body dynamics (gravity, collision, momentum)
- Support constraints (pivot joints, distance joints)
- Performant enough for 60fps with ~50 physics bodies

### Nice to Have
- Soft body physics
- Particle systems
- Fluid simulation
- Configurable via YAML

## Architecture Options

### Option 1: Pure Lua Physics Engine

Implement physics directly in Lua, integrated with the behavior engine.

**Pros:**
- Runs everywhere Lua runs (native Python + WASM)
- Full control over implementation
- Tight integration with existing Lua behaviors
- Single codebase for all platforms

**Cons:**
- Lua is slower than native code
- Significant implementation effort
- Risk of physics edge cases and stability issues

**Implementation Approach:**
```lua
-- ams/physics/lua/world.lua
local physics = {}

function physics.create_world(gravity_x, gravity_y)
    return {
        gravity = {x = gravity_x, y = gravity_y},
        bodies = {},
        constraints = {},
        dt_accumulator = 0
    }
end

function physics.add_body(world, body_type, x, y, mass)
    local body = {
        type = body_type,  -- "dynamic", "static", "kinematic"
        position = {x = x, y = y},
        velocity = {x = 0, y = 0},
        mass = mass,
        inv_mass = mass > 0 and 1/mass or 0,
        shapes = {}
    }
    table.insert(world.bodies, body)
    return body
end

function physics.add_pivot_joint(world, body_a, body_b, anchor)
    local joint = {
        type = "pivot",
        body_a = body_a,
        body_b = body_b,
        anchor = anchor
    }
    table.insert(world.constraints, joint)
    return joint
end

function physics.step(world, dt)
    -- Fixed timestep with accumulator
    world.dt_accumulator = world.dt_accumulator + dt
    local fixed_dt = 1/60

    while world.dt_accumulator >= fixed_dt do
        -- Apply gravity
        for _, body in ipairs(world.bodies) do
            if body.type == "dynamic" then
                body.velocity.x = body.velocity.x + world.gravity.x * fixed_dt
                body.velocity.y = body.velocity.y + world.gravity.y * fixed_dt
            end
        end

        -- Solve constraints (iterative)
        for iter = 1, 10 do
            for _, constraint in ipairs(world.constraints) do
                physics.solve_constraint(constraint)
            end
        end

        -- Integrate positions
        for _, body in ipairs(world.bodies) do
            if body.type == "dynamic" then
                body.position.x = body.position.x + body.velocity.x * fixed_dt
                body.position.y = body.position.y + body.velocity.y * fixed_dt
            end
        end

        world.dt_accumulator = world.dt_accumulator - fixed_dt
    end
end

return physics
```

**Estimated Effort:** 2-3 weeks for basic rope physics

---

### Option 2: Pure Python Physics Module

Custom lightweight physics in Python, designed to work with pygame-web/pygbag.

**Pros:**
- Python is more performant than Lua
- Can use numpy for WASM (numpy works in pyodide)
- Cleaner integration with existing game engine
- Better debugging and testing

**Cons:**
- Need to ensure all dependencies work in WASM
- Two implementations to maintain if we want Lua physics too
- Python's dynamic typing can mask physics bugs

**Implementation Approach:**
```python
# ams/physics/engine.py
from dataclasses import dataclass
from typing import List, Tuple, Optional
import math

@dataclass
class Vec2:
    x: float
    y: float

    def __add__(self, other): return Vec2(self.x + other.x, self.y + other.y)
    def __sub__(self, other): return Vec2(self.x - other.x, self.y - other.y)
    def __mul__(self, s): return Vec2(self.x * s, self.y * s)
    def dot(self, other): return self.x * other.x + self.y * other.y
    def length(self): return math.sqrt(self.x**2 + self.y**2)
    def normalized(self):
        l = self.length()
        return Vec2(self.x/l, self.y/l) if l > 0 else Vec2(0, 0)

@dataclass
class Body:
    position: Vec2
    velocity: Vec2
    mass: float
    is_static: bool = False

    @property
    def inv_mass(self):
        return 0 if self.is_static or self.mass == 0 else 1 / self.mass

class DistanceConstraint:
    """Keeps two bodies at fixed distance (rope segment)."""
    def __init__(self, body_a: Body, body_b: Body, distance: float):
        self.body_a = body_a
        self.body_b = body_b
        self.distance = distance

    def solve(self):
        delta = self.body_b.position - self.body_a.position
        current_dist = delta.length()
        if current_dist == 0:
            return

        diff = (current_dist - self.distance) / current_dist
        correction = delta * diff * 0.5

        total_inv_mass = self.body_a.inv_mass + self.body_b.inv_mass
        if total_inv_mass == 0:
            return

        self.body_a.position = self.body_a.position + correction * (self.body_a.inv_mass / total_inv_mass)
        self.body_b.position = self.body_b.position - correction * (self.body_b.inv_mass / total_inv_mass)

class PhysicsWorld:
    def __init__(self, gravity: Vec2 = Vec2(0, 980)):
        self.gravity = gravity
        self.bodies: List[Body] = []
        self.constraints: List[DistanceConstraint] = []
        self.damping = 0.99

    def step(self, dt: float, iterations: int = 8):
        # Apply forces
        for body in self.bodies:
            if not body.is_static:
                body.velocity = body.velocity + self.gravity * dt
                body.velocity = body.velocity * self.damping

        # Integrate velocity
        for body in self.bodies:
            if not body.is_static:
                body.position = body.position + body.velocity * dt

        # Solve constraints
        for _ in range(iterations):
            for constraint in self.constraints:
                constraint.solve()
```

**Estimated Effort:** 2 weeks for basic implementation

---

### Option 3: Hybrid - JavaScript Physics for WASM

Use matter.js or planck.js when running in browser, pymunk/custom for native.

**Pros:**
- Leverage battle-tested JS physics engines
- Great WASM performance (JS engines are highly optimized)
- Less code to write/maintain

**Cons:**
- Two different physics implementations = potential behavior differences
- Complex bridging between Python game code and JS physics
- Harder to debug cross-platform issues

**Implementation Approach:**
```python
# ams/physics/__init__.py
import sys

if sys.platform == "emscripten":
    from ams.physics.js_bridge import JSPhysicsWorld as PhysicsWorld
else:
    from ams.physics.native import NativePhysicsWorld as PhysicsWorld
```

```javascript
// web/physics_bridge.js
class PhysicsBridge {
    constructor() {
        this.engine = Matter.Engine.create();
        this.world = this.engine.world;
    }

    createBody(x, y, width, height, options) {
        const body = Matter.Bodies.rectangle(x, y, width, height, options);
        Matter.World.add(this.world, body);
        return body.id;
    }

    createConstraint(bodyA, bodyB, options) {
        const constraint = Matter.Constraint.create({
            bodyA: this.getBody(bodyA),
            bodyB: this.getBody(bodyB),
            ...options
        });
        Matter.World.add(this.world, constraint);
        return constraint.id;
    }

    step(dt) {
        Matter.Engine.update(this.engine, dt * 1000);
    }
}
```

**Estimated Effort:** 3 weeks (bridging complexity)

---

### Option 4: Verlet Integration in Lua (Recommended for Sweet Physics)

Verlet integration is perfect for rope/cloth simulation and very simple to implement.

**Pros:**
- Extremely simple algorithm (positions only, no velocities)
- Naturally handles constraints (rope segments, cloth)
- Very stable for chains/ropes
- Easy to implement in Lua
- Used by many games for rope physics

**Cons:**
- Less suitable for rigid body collisions
- Damping handled implicitly
- Harder to apply forces at specific points

**Implementation Approach:**
```lua
-- ams/physics/lua/verlet.lua
-- Verlet integration for rope/chain physics

local verlet = {}

-- Point in verlet simulation
function verlet.create_point(x, y, pinned)
    return {
        x = x,
        y = y,
        old_x = x,
        old_y = y,
        pinned = pinned or false
    }
end

-- Constraint between two points
function verlet.create_stick(point_a, point_b, length)
    return {
        point_a = point_a,
        point_b = point_b,
        length = length or verlet.distance(point_a, point_b)
    }
end

function verlet.distance(a, b)
    local dx = b.x - a.x
    local dy = b.y - a.y
    return math.sqrt(dx * dx + dy * dy)
end

-- Update all points (gravity + verlet integration)
function verlet.update_points(points, gravity_y, dt, damping)
    damping = damping or 0.99
    for _, p in ipairs(points) do
        if not p.pinned then
            local vx = (p.x - p.old_x) * damping
            local vy = (p.y - p.old_y) * damping

            p.old_x = p.x
            p.old_y = p.y

            p.x = p.x + vx
            p.y = p.y + vy + gravity_y * dt * dt
        end
    end
end

-- Solve stick constraints
function verlet.solve_sticks(sticks, iterations)
    iterations = iterations or 3
    for _ = 1, iterations do
        for _, stick in ipairs(sticks) do
            local a = stick.point_a
            local b = stick.point_b

            local dx = b.x - a.x
            local dy = b.y - a.y
            local dist = math.sqrt(dx * dx + dy * dy)

            if dist > 0 then
                local diff = (stick.length - dist) / dist
                local offset_x = dx * diff * 0.5
                local offset_y = dy * diff * 0.5

                if not a.pinned then
                    a.x = a.x - offset_x
                    a.y = a.y - offset_y
                end
                if not b.pinned then
                    b.x = b.x + offset_x
                    b.y = b.y + offset_y
                end
            end
        end
    end
end

-- Create a rope from anchor to attachment point
function verlet.create_rope(anchor_x, anchor_y, end_x, end_y, segments)
    local points = {}
    local sticks = {}

    for i = 0, segments do
        local t = i / segments
        local x = anchor_x + (end_x - anchor_x) * t
        local y = anchor_y + (end_y - anchor_y) * t
        local pinned = (i == 0)  -- First point is anchor

        table.insert(points, verlet.create_point(x, y, pinned))
    end

    for i = 1, #points - 1 do
        table.insert(sticks, verlet.create_stick(points[i], points[i + 1]))
    end

    return {
        points = points,
        sticks = sticks,
        cut_index = nil
    }
end

-- Cut rope at segment index
function verlet.cut_rope(rope, index)
    rope.cut_index = index
    -- Remove sticks from cut point onwards
    local new_sticks = {}
    for i, stick in ipairs(rope.sticks) do
        if i < index then
            table.insert(new_sticks, stick)
        end
    end
    rope.sticks = new_sticks
end

-- Check if point hits rope segment
function verlet.check_rope_hit(rope, x, y, radius)
    for i, stick in ipairs(rope.sticks) do
        local dist = verlet.point_to_segment_dist(
            x, y,
            stick.point_a.x, stick.point_a.y,
            stick.point_b.x, stick.point_b.y
        )
        if dist < radius then
            return i
        end
    end
    return nil
end

function verlet.point_to_segment_dist(px, py, x1, y1, x2, y2)
    local dx = x2 - x1
    local dy = y2 - y1
    local len_sq = dx * dx + dy * dy

    if len_sq == 0 then
        return math.sqrt((px - x1)^2 + (py - y1)^2)
    end

    local t = math.max(0, math.min(1, ((px - x1) * dx + (py - y1) * dy) / len_sq))
    local proj_x = x1 + t * dx
    local proj_y = y1 + t * dy

    return math.sqrt((px - proj_x)^2 + (py - proj_y)^2)
end

return verlet
```

**This is my recommendation for Sweet Physics specifically** because:
1. Verlet is perfect for rope simulation
2. Very simple to implement in Lua (~100 lines)
3. Works everywhere (native + WASM)
4. Proven technique used in many games

**Estimated Effort:** 1 week

---

## Recommended Approach: Layered Physics

Build physics support in layers, starting simple:

### Layer 1: Verlet Rope Physics (Lua)
- Implement `ams/physics/lua/verlet.lua`
- Integrate with behavior engine
- Enables Sweet Physics and rope-based games
- **Effort: 1 week**

### Layer 2: Basic Rigid Body (Lua)
- Circle and box colliders
- Simple collision detection (AABB, circle-circle)
- Collision response (bounce, friction)
- **Effort: 1-2 weeks**

### Layer 3: Constraints (Lua)
- Pivot joints (connect bodies at point)
- Distance joints (fixed distance)
- Hinge joints (rotation limits)
- **Effort: 1 week**

### Layer 4: Advanced Features (Future)
- Broad phase collision detection
- Continuous collision detection
- More shape types (polygon, compound)
- **Effort: 2+ weeks**

## YAML Integration

### Constraints as First-Class Concept

Constraints are relationships between entities that the physics system enforces. This is a new YAML concept alongside `entity_types`, `collisions`, etc.

```yaml
# game.yaml - New top-level "constraints" section

# =============================================================================
# Constraint Types (templates, like entity_types)
# =============================================================================

constraint_types:
  # Distance constraint - keeps two points at fixed distance
  rope_segment:
    type: distance
    length: 20              # Fixed distance in pixels
    stiffness: 1.0          # 1.0 = rigid, <1.0 = springy
    damping: 0.0            # Velocity damping at joint

  # Pivot constraint - bodies rotate around shared point
  hinge:
    type: pivot
    anchor: local           # "local" = relative to body, "world" = absolute

  # Spring constraint - elastic connection
  spring:
    type: spring
    rest_length: 50
    stiffness: 100          # Spring constant
    damping: 5              # Damping coefficient

  # Rope constraint - chain of distance constraints
  rope:
    type: rope_chain
    segments: 8
    segment_length: 20
    stiffness: 1.0

# =============================================================================
# Constraint Instances (like entity placements in levels)
# =============================================================================

constraints:
  # Simple distance constraint between two entities
  - type: rope_segment
    entity_a: candy
    entity_b: anchor_1
    anchor_a: [0, 0]        # Offset from entity_a center
    anchor_b: [0, 0]        # Offset from entity_b center

  # Rope chain from static point to entity
  - type: rope
    name: main_rope         # For referencing in Lua
    anchor: [400, 50]       # Static world position
    attach_to: candy        # Entity to attach end to
    segments: 8
    length: 150

  # Pivot joint
  - type: hinge
    entity_a: door
    entity_b: wall
    anchor: [100, 200]      # World position of pivot

# =============================================================================
# Constraint Actions (what can happen to constraints)
# =============================================================================

# Constraints can be:
# - Created at level start (above)
# - Created dynamically via Lua
# - Destroyed (broken/cut)
# - Modified (change length, stiffness)

input_mapping:
  rope:                     # Entity type (rope visual)
    on_hit:
      action:
        lua: |
          local action = {}
          function action.execute(x, y, args)
            -- Find which rope was hit and cut it
            local hit_constraint = ams.constraints.find_at(x, y, 15)
            if hit_constraint then
              ams.constraints.break(hit_constraint)
            end
          end
          return action
```

### Physics section in game.yaml:

```yaml
# game.yaml
physics:
  enabled: true
  gravity: [0, 980]
  damping: 0.99
  iterations: 8             # Constraint solver iterations
  step_rate: 60             # Physics steps per second
  engine: verlet            # "verlet" (Lua) or "rigid" (future)

entity_types:
  candy:
    width: 50
    height: 50
    physics:
      type: dynamic        # dynamic, static, kinematic
      shape: circle        # circle, rectangle
      mass: 1.0
      restitution: 0.3     # bounciness
      friction: 0.5

  rope_segment:
    width: 4
    height: 20
    physics:
      type: verlet_point   # Special type for verlet chains

  platform:
    width: 200
    height: 20
    physics:
      type: static
      shape: rectangle
```

### Constraint Solver Architecture

Constraints can be solved in either Lua or Python:

```
┌─────────────────────────────────────────────────────────────┐
│                    YAML Definition                          │
│  constraints:                                               │
│    - type: rope                                             │
│      anchor: [400, 50]                                      │
│      attach_to: candy                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Constraint Manager (Python)                    │
│  - Parses YAML constraint definitions                       │
│  - Creates constraint objects                               │
│  - Routes to appropriate solver                             │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
┌──────────────────────┐    ┌──────────────────────┐
│   Lua Solver         │    │   Python Solver      │
│   (WASM compatible)  │    │   (Native only)      │
│                      │    │                      │
│  verlet.lua          │    │  Optional: numpy     │
│  - Distance          │    │  - Performance       │
│  - Rope chain        │    │  - Complex physics   │
│  - Simple & portable │    │                      │
└──────────────────────┘    └──────────────────────┘
```

### Constraint Types Reference

| Type | Description | Parameters |
|------|-------------|------------|
| `distance` | Fixed distance between two points | `length`, `stiffness` |
| `pivot` | Rotation around shared point | `anchor` |
| `spring` | Elastic connection | `rest_length`, `stiffness`, `damping` |
| `rope_chain` | Chain of distance constraints | `segments`, `length`, `stiffness` |
| `slider` | Movement along an axis | `axis`, `min`, `max` |
| `weld` | Rigid connection (no movement) | - |

### New Lua API for Physics and Constraints:

```lua
-- =============================================================================
-- Physics Body API
-- =============================================================================
ams.physics.create_body(entity_id, body_type, shape)
ams.physics.remove_body(entity_id)
ams.physics.apply_force(entity_id, fx, fy)
ams.physics.apply_impulse(entity_id, ix, iy)
ams.physics.set_velocity(entity_id, vx, vy)
ams.physics.get_velocity(entity_id)
ams.physics.get_position(entity_id)  -- Physics position (may differ from render)

-- =============================================================================
-- Constraint API (works with both Lua and Python solvers)
-- =============================================================================

-- Query constraints
ams.constraints.get_all()                    -- Returns list of constraint IDs
ams.constraints.get_by_name(name)            -- Get constraint by name
ams.constraints.get_attached_to(entity_id)   -- All constraints on an entity
ams.constraints.find_at(x, y, radius)        -- Find constraint near point (for hit detection)

-- Create constraints dynamically
ams.constraints.create_distance(entity_a, entity_b, length, stiffness)
ams.constraints.create_pivot(entity_a, entity_b, anchor_x, anchor_y)
ams.constraints.create_spring(entity_a, entity_b, rest_length, stiffness, damping)
ams.constraints.create_rope(anchor_x, anchor_y, entity_id, length, segments)

-- Modify constraints
ams.constraints.set_length(constraint_id, new_length)
ams.constraints.set_stiffness(constraint_id, new_stiffness)
ams.constraints.set_enabled(constraint_id, enabled)

-- Break/remove constraints
ams.constraints.break(constraint_id)         -- Remove constraint (for cutting ropes)
ams.constraints.break_at(constraint_id, index)  -- Break rope at segment index

-- Get constraint state
ams.constraints.get_type(constraint_id)      -- "distance", "pivot", "rope_chain", etc.
ams.constraints.get_points(constraint_id)    -- For ropes: list of {x, y} positions
ams.constraints.get_tension(constraint_id)   -- Current tension/stress on constraint
ams.constraints.is_broken(constraint_id)     -- Has constraint been broken?

-- =============================================================================
-- Rope-specific API (convenience wrappers)
-- =============================================================================
ams.rope.create(anchor_x, anchor_y, entity_id, length, segments)
ams.rope.cut(rope_id, segment_index)
ams.rope.cut_at_point(rope_id, x, y)         -- Cut at closest segment to point
ams.rope.get_points(rope_id)                 -- List of {x, y} for rendering
ams.rope.get_end_position(rope_id)           -- Position of rope end
ams.rope.get_segment_count(rope_id)
ams.rope.is_cut(rope_id)

-- =============================================================================
-- Example: Sweet Physics rope cutting behavior
-- =============================================================================
-- In input_mapping or global_on_input:
local action = {}
function action.execute(x, y, args)
    -- Check all ropes for hit
    local ropes = ams.constraints.get_all()
    for _, rope_id in ipairs(ropes) do
        if ams.constraints.get_type(rope_id) == "rope_chain" then
            -- Check if click is near any rope segment
            local points = ams.rope.get_points(rope_id)
            for i = 1, #points - 1 do
                local dist = point_to_segment_dist(x, y, points[i], points[i+1])
                if dist < 15 then  -- Hit radius
                    ams.rope.cut(rope_id, i)
                    ams.play_sound("rope_cut")
                    return
                end
            end
        end
    end
end
return action
```

## Migration Path for SweetPhysics

1. **Phase 1**: Implement verlet.lua with rope physics
2. **Phase 2**: Create `ams/behaviors/lua/verlet_rope.lua` behavior
3. **Phase 3**: Create SweetPhysicsNG using YAML + Lua verlet
4. **Phase 4**: Test and tune physics feel to match original
5. **Phase 5**: Migrate original levels to new format

## Files to Create

```
ams/
├── physics/
│   ├── __init__.py          # Physics engine selector
│   ├── lua/
│   │   ├── verlet.lua       # Verlet integration (ropes)
│   │   ├── collision.lua    # Collision detection
│   │   └── rigid_body.lua   # Basic rigid body physics
│   └── world.py             # Python physics coordinator
├── behaviors/
│   └── lua/
│       ├── verlet_rope.lua  # Verlet rope behavior
│       └── physics_body.lua # Rigid body behavior
```

## Success Criteria

1. **Sweet Physics works in WASM** - Rope swinging feels natural
2. **60fps performance** - Physics doesn't cause frame drops
3. **YAML-configurable** - New physics games via YAML only
4. **Consistent behavior** - Same physics on all platforms

## Open Questions

1. Should physics be opt-in per game or always available?
2. How to handle physics debug rendering?
3. Should we support multiple physics "worlds" per game?
4. How fine-grained should YAML physics config be?

## References

- [Verlet Integration Tutorial](https://www.youtube.com/watch?v=3HjO_RGIjCU) - Coding Math
- [Building a Physics Engine](https://www.toptal.com/game/video-game-physics-part-i-an-introduction-to-rigid-body-dynamics)
- [Matter.js](https://brm.io/matter-js/) - JS physics engine (reference)
- [Chipmunk2D](http://chipmunk-physics.net/) - What Pymunk wraps

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| TBD | Start with Verlet Lua | Simplest path to working rope physics |
| TBD | Pure Lua over hybrid | Single codebase, WASM compatibility |
