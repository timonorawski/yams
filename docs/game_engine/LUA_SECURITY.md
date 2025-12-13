# Lua Security Model

This document describes the security model for Lua scripting in the AMS game engine. Lua behaviors provide game logic flexibility while maintaining strict isolation from the host system.

## Overview

The AMS game engine uses [Lupa](https://github.com/scoder/lupa) (LuaJIT via Python) to execute Lua scripts for entity behaviors, collision actions, and property generators. The security model is based on:

1. **Defense in depth**: Multiple layers of protection, each independently effective
2. **Capability-based sandbox**: Lua code can only call functions explicitly exposed via the `ams.*` API
3. **ID-based access**: Entities are referenced by string IDs, not direct Python object references
4. **No dangerous primitives**: No filesystem, network, OS, or raw memory access
5. **Deferred effects**: Side effects (sounds, spawns) go through queues processed by the Python layer
6. **Runtime validation**: Sandbox integrity verified on every engine initialization

## Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                    Lua Scripts                           │
│  behaviors/*.lua | collision_actions/*.lua | inline     │
│                                                          │
│  Can only call: ams.get_x(), ams.spawn(), ams.log()...  │
└──────────────────────────┬───────────────────────────────┘
                           │ Function calls (ID-based)
                           ↓
┌─────────────────────────────────────────────────────────┐
│                    LuaAPI (api.py)                       │
│                                                          │
│  - Validates entity IDs before operations                │
│  - Returns safe defaults for missing entities            │
│  - Queues effects for deferred execution                 │
└──────────────────────────┬───────────────────────────────┘
                           │ Internal calls
                           ↓
┌─────────────────────────────────────────────────────────┐
│               BehaviorEngine (engine.py)                 │
│                                                          │
│  - Entity storage and lifecycle                          │
│  - Sound queue (processed by game layer)                 │
│  - Scheduled callbacks                                   │
└─────────────────────────────────────────────────────────┘
```

## Defense in Depth

The sandbox implements multiple independent security layers:

### Layer 1: Lupa Constructor Options

```python
self._lua = LuaRuntime(
    register_eval=False,      # Don't expose python.eval()
    register_builtins=False,  # Don't expose python.builtins.*
    unpack_returned_tuples=True,
    attribute_filter=_lua_attribute_filter
)
```

### Layer 2: Attribute Filter

Blocks access to Python internals even on exposed objects:

```python
def _lua_attribute_filter(obj, attr_name, is_setting):
    if attr_name.startswith('__'):
        raise AttributeError(f'Access to {attr_name} is blocked')
    if attr_name.startswith('_'):
        raise AttributeError(f'Access to private attribute {attr_name} is blocked')

    # Block callable attributes (methods) on Python objects
    if not is_setting:
        try:
            attr = getattr(obj, attr_name, None)
            if attr is not None and callable(attr) and not isinstance(attr, type):
                raise AttributeError(f'Access to callable {attr_name} is blocked')
        except AttributeError:
            raise
        except Exception:
            pass  # If we can't check, allow the access

    return attr_name
```

This prevents:

- `obj.__class__` - No class/type introspection
- `obj.__dict__` - No attribute enumeration
- `obj._private` - No internal state access
- `method.__self__` - No access to bound method's instance
- `obj.method()` - No calling methods on leaked Python objects

Note: This filter only applies to Python objects accessed from Lua, not to Lua tables like `ams.*`. The `ams.*` API functions work because they're stored in a Lua table, not accessed as Python object attributes.

### Layer 3: String Metatable Cleanup

Remove dangerous functions from built-in metatables:

```python
# Remove dangerous string functions before clearing globals
self._lua.execute("""
    local mt = getmetatable("")
    if mt and mt.__index then
        mt.__index.dump = nil  -- Bytecode serialization
        mt.__index.rep = nil   -- Memory DoS risk: ("x"):rep(2^30)
    end
""")
```

### Layer 4: Nuclear Global Clearing

Clear ALL Lua globals, reinstall only safe subset:

```python
# Save safe primitives
safe_globals = {
    'pairs': g.pairs,
    'ipairs': g.ipairs,
    'type': g.type,
    'tostring': g.tostring,
    'tonumber': g.tonumber,
    'select': g.select,
    'unpack': g.table.unpack,
    'pcall': g.pcall,
    'error': g.error,
    'next': g.next,
    'math': g.math,  # Full math library (safe, no side effects)
}

# Nuclear: clear ALL globals
for key in list(g.keys()):
    g[key] = None

# Reinstall only safe globals
for key, value in safe_globals.items():
    g[key] = value
```

### Layer 5: Runtime Validation

Every `BehaviorEngine` initialization validates the sandbox:

```python
def _validate_sandbox(self) -> None:
    critical_escapes = [
        ('python', 'python bridge gives full interpreter access'),
        ('io', 'filesystem access'),
        ('os', 'OS interface'),
        ('debug', 'full introspection'),
        ('loadfile', 'load from filesystem'),
        # ... 30+ checks
    ]

    failures = []
    for name, risk in critical_escapes:
        if self._lua.eval(f'{name} ~= nil'):
            failures.append(f'EXPOSED: {name} - {risk}')

    # Also check string.dump via method syntax
    if self._lua.eval('("").dump') is not None:
        failures.append('EXPOSED: string.dump')

    if failures:
        raise RuntimeError('Sandbox validation failed')
```

If validation fails, the engine refuses to start.

## What Lua CAN Access

### Safe Lua Primitives

These standard Lua functions are preserved:

| Function | Purpose |
|----------|---------|
| `pairs` | Iterate table key-value pairs |
| `ipairs` | Iterate array indices |
| `type` | Check value types |
| `tostring` | Convert to string |
| `tonumber` | Convert to number |
| `select` | Vararg handling |
| `unpack` | Unpack table to args |
| `pcall` | Protected function calls |
| `error` | Raise errors |
| `next` | Raw table iteration |
| `math` | Full math library (`math.sin`, `math.random`, etc.) |

**Not preserved**: `string.*`, `table.*` libraries.

**Note**: Basic string methods like `:upper()`, `:gsub()` still work via the string metatable - these are safe string manipulation functions.

### The `ams.*` API

The `ams.*` namespace provides a whitelist of safe game operations:

#### Entity Properties

```lua
-- Read/write position and velocity
local x = ams.get_x(entity_id)
ams.set_x(entity_id, x + 10)
ams.set_vx(entity_id, 100)

-- Read/write size, health, sprite, color
local w = ams.get_width(entity_id)
ams.set_health(entity_id, ams.get_health(entity_id) - 1)
ams.set_sprite(entity_id, "damaged")
ams.set_color(entity_id, "red")

-- Custom properties (behavior state)
ams.set_prop(entity_id, "oscillate_phase", 0)
local phase = ams.get_prop(entity_id, "oscillate_phase")

-- Read-only behavior config from YAML
local speed = ams.get_config(entity_id, "descend", "speed", 50)
```

#### Entity Lifecycle

```lua
ams.destroy(entity_id)  -- Mark for destruction
local alive = ams.is_alive(entity_id)

-- Spawn new entities (inherits config from game.yaml entity_types)
local new_id = ams.spawn("projectile", x, y, vx, vy, width, height, color, sprite)
```

#### Entity Queries

```lua
local brick_ids = ams.get_entities_of_type("brick")
local enemies = ams.get_entities_by_tag("enemy")
local count = ams.count_entities_by_tag("destructible")
local all = ams.get_all_entity_ids()
```

#### Game State

```lua
local w = ams.get_screen_width()
local h = ams.get_screen_height()
local score = ams.get_score()
ams.add_score(100)
local elapsed = ams.get_time()
```

#### Events and Scheduling

```lua
ams.play_sound("explosion")  -- Queued, played by game layer
ams.schedule(2.0, "on_timer", entity_id)  -- Call behavior.on_timer after 2s
```

#### Math

The full Lua `math` library is available, plus convenience wrappers via `ams.*`:

```lua
-- Standard Lua math library (all functions available)
local angle = math.atan2(dy, dx)
local dist = math.sqrt(dx*dx + dy*dy)
local osc = math.sin(ams.get_time() * 2)
local r = math.random()  -- [0, 1)

-- ams.* convenience wrappers
local r2 = ams.random_range(10, 50)  -- [10, 50]
local clamped = ams.clamp(value, 0, 100)
```

#### Debug

```lua
ams.log("Debug message")  -- Prints to console
```

## What Lua CANNOT Access

The sandbox blocks all of these (validated on every init):

| Category | Blocked | Risk |
|----------|---------|------|
| **Python Bridge** | `python`, `_python` | Full interpreter access |
| **FFI** | `ffi`, `jit` | Raw memory access |
| **Code Loading** | `load`, `loadstring`, `loadfile`, `dofile` | Arbitrary code execution |
| **Modules** | `require`, `package`, `module` | Load external code |
| **Introspection** | `debug`, `getfenv`, `setfenv` | Sandbox escape |
| **Metatables** | `getmetatable`, `setmetatable` | Metatable manipulation |
| **Raw Access** | `rawget`, `rawset`, `rawequal`, `rawlen` | Bypass metamethods |
| **Globals** | `_G`, `_VERSION` | Global table access |
| **Misc** | `collectgarbage`, `newproxy` | GC/userdata manipulation |
| **Libraries** | `io`, `os`, `coroutine` | System access |
| **Bytecode** | `string.dump` | Function serialization |
| **Memory DoS** | `string.rep` | Unbounded memory allocation |

## ID-Based Access Pattern

A critical security property is that Lua never holds direct Python object references:

```python
# In LuaAPI (Python side)
def get_x(self, entity_id: str) -> float:
    entity = self._engine.get_entity(entity_id)  # Lookup by ID
    return entity.x if entity else 0.0  # Safe default
```

```lua
-- In behavior (Lua side)
function behavior.on_update(entity_id, dt)
    -- entity_id is a string like "brick_a1b2c3d4"
    -- Cannot access entity.x directly, must use API
    local x = ams.get_x(entity_id)
end
```

This pattern ensures:

- Lua cannot hold stale references to destroyed entities
- API can validate every access
- Python objects are never exposed to Lua's garbage collector
- Entity storage can change without breaking Lua code

## Lua-Safe Return Values

### Layer 6: Return Value Conversion

API methods that return collections use the `@lua_safe_function` decorator to convert Python objects to Lua-native types:

```python
def _to_lua_value(value: Any, lua_runtime) -> Any:
    """Convert Python value to Lua-safe value."""
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value  # Primitives pass through
    if isinstance(value, (list, tuple)):
        # Convert to 1-indexed Lua table
        lua_table = lua_runtime.table()
        for i, item in enumerate(value, start=1):
            lua_table[i] = _to_lua_value(item, lua_runtime)
        return lua_table
    if isinstance(value, dict):
        lua_table = lua_runtime.table()
        for k, v in value.items():
            if not isinstance(k, (str, int, float, bool)):
                raise TypeError(f"Dict key must be str/int/float, got {type(k).__name__}")
            lua_table[k] = _to_lua_value(v, lua_runtime)
        return lua_table
    if isinstance(value, bytes):
        raise TypeError("Cannot pass bytes to Lua - decode to str first")
    if isinstance(value, set):
        raise TypeError("Cannot convert set to Lua - convert to list first")
    # Fail loudly for unknown types - this is a bug in the API
    raise TypeError(f"Cannot convert {type(value).__name__} to Lua-safe value")
```

This ensures:

- **1-indexed tables**: Lists become proper Lua tables with 1-based indexing
- **`ipairs`/`pairs` support**: Returned tables work with standard Lua iteration
- **`#` operator support**: Can get length of returned tables
- **No silent failures**: Unknown types raise TypeError instead of silently converting
- **Key validation**: Dict keys must be primitives (no tuple keys, etc.)

### Decorated Methods

The following API methods use `@lua_safe_function`:

| Method | Returns | Conversion |
|--------|---------|------------|
| `get_entities_of_type()` | `list[str]` | 1-indexed Lua table |
| `get_entities_by_tag()` | `list[str]` | 1-indexed Lua table |
| `get_all_entity_ids()` | `list[str]` | 1-indexed Lua table |
| `get_prop()` | `Any` | Recursive conversion |
| `get_config()` | `Any` | Recursive conversion |

### Usage in Lua

```lua
-- Entity queries return proper Lua tables
local bricks = ams.get_entities_of_type("brick")
print(#bricks)  -- Works! (e.g., 5)

for i, id in ipairs(bricks) do
    -- Works! 1-indexed iteration
    ams.destroy(id)
end

-- Nested config is also converted
local waypoints = ams.get_config(entity_id, "patrol", "waypoints")
local first = waypoints[1]  -- 1-indexed access
print(first.x, first.y)     -- Nested dicts become tables
```

## Deferred Effects

Side effects don't execute immediately - they're queued for the game layer:

### Sound Queue

```python
# In LuaAPI
def play_sound(self, sound_name: str) -> None:
    self._engine.queue_sound(sound_name)  # Queued, not played

# In game layer (each frame)
for sound in behavior_engine.pop_sounds():
    audio_system.play(sound)
```

### Scheduled Callbacks

```python
# In LuaAPI
def schedule(self, delay: float, callback_name: str, entity_id: str) -> None:
    self._engine.schedule_callback(delay, callback_name, entity_id)

# In BehaviorEngine.update()
for scheduled in self._scheduled[:]:
    scheduled.time_remaining -= dt
    if scheduled.time_remaining <= 0:
        self._call_scheduled_callback(scheduled)  # Safe dispatch
```

This prevents:

- Infinite loops blocking the game
- Unbounded resource allocation
- Race conditions from immediate execution

## Inline Lua Security

YAML files can embed inline Lua for behaviors and expressions:

```yaml
# Inline behavior
behaviors:
  - lua: |
      local behavior = {}
      function behavior.on_update(entity_id, dt)
          local x = ams.get_x(entity_id) + 10 * dt
          ams.set_x(entity_id, x)
      end
      return behavior

# Inline expression (property value)
angle: {lua: "ams.random_range(-60, -120)"}

# Win condition expression
win_condition:
  lua: |
    local bricks = ams.count_entities_by_tag("brick")
    return bricks == 0
```

Inline Lua runs in the same sandbox - it has no additional privileges. The `ams.*` API is the only way to interact with the game.

## Error Handling

Lua errors are caught and logged without crashing the game:

```python
# In BehaviorEngine._call_lifecycle()
try:
    method(entity.id, *args)
except Exception as e:
    print(f"[BehaviorEngine] Error in {behavior_name}.{method_name}: {e}")
    # Continue execution - one bad behavior doesn't crash the game
```

This provides:

- Graceful degradation when scripts fail
- Debug visibility into errors
- No crash amplification from malformed Lua

## Testing

The sandbox has comprehensive regression tests in `tests/test_lua_sandbox.py`:

```bash
pytest tests/test_lua_sandbox.py -v
```

Test categories (105 tests):

- **TestBlockedGlobals** - Verifies dangerous globals are nil (io, os, python, ffi, etc.)
- **TestBlockedOperations** - Verifies dangerous operations fail
- **TestMetatableAccess** - Verifies metatable functions blocked
- **TestAttributeFilter** - Verifies Python internals and methods inaccessible
- **TestAllowedGlobals** - Verifies safe primitives work (pairs, ipairs, math, etc.)
- **TestAmsApiAvailable** - Verifies ams.* API works
- **TestBehaviorExecution** - Verifies behaviors run correctly
- **TestEdgeCases** - string.dump, string.rep, coroutines, etc.
- **TestLegitimateUseCases** - Verifies Python/Lua interop works correctly
- **TestRuntimeValidation** - Verifies validation catches issues
- **TestLuaSafeReturns** - Verifies API returns Lua-native tables
- **TestLuaSafeReturnBoundary** - Verifies type conversion rejects invalid types
- **TestAttributeFilterEdgeCases** - Edge cases in attribute filtering

## Threat Model

### In Scope (Protected Against)

| Threat | Mitigation |
|--------|------------|
| Arbitrary code execution | No `load`, `loadstring`, `dofile` |
| File system access | No `io.*` exposed |
| Network access | No socket primitives |
| Python interpreter access | `python` bridge removed + `register_eval=False` |
| Environment variable access | No `os.getenv` |
| System command execution | No `os.execute`, `io.popen` |
| Memory corruption | Lupa handles type marshaling safely |
| Bytecode injection | `string.dump` removed from metatable |
| Memory exhaustion via string | `string.rep` removed from metatable |
| Metatable manipulation | `getmetatable`/`setmetatable` removed |
| Attribute enumeration | Attribute filter blocks `__dict__` etc. |
| Method calls on leaked objects | Attribute filter blocks callables |

### Out of Scope (Not Protected Against)

| Threat | Status |
|--------|--------|
| Malicious YAML files | Trust boundary is at YAML loading, YAML Files are schema-validated by the game engine at load |
| CPU exhaustion (slow scripts) | No execution time limits yet |
| Entity spawn flooding | No hard limits on `ams.spawn()` |
| Logic bugs in behaviors | Expected - that's what debugging is for |

## Future Enhancements

Planned security improvements:

1. **Execution time limits**: Kill scripts that run too long
2. **Entity count limits**: Cap total entities to prevent spawn floods
3. **Memory limits**: Restrict Lua heap size via `max_memory` parameter
4. **Script signing**: Verify authorship of behavior scripts
5. **Permission levels**: Different API access for different script sources

## Implementation Files

| File | Purpose |
|------|---------|
| `ams/behaviors/engine.py` | BehaviorEngine - Lua VM setup, sandbox, validation |
| `ams/behaviors/api.py` | LuaAPI - All `ams.*` functions |
| `ams/behaviors/entity.py` | Entity class (Python-side storage) |
| `ams/behaviors/lua/*.lua` | Built-in behavior scripts |
| `ams/behaviors/collision_actions/*.lua` | Built-in collision actions |
| `tests/test_lua_sandbox.py` | Security regression tests (105 tests) |

## Summary

The Lua security model follows the principle of defense in depth:

1. **Lupa options**: `register_eval=False`, `register_builtins=False`
2. **Attribute filter**: Blocks `__dunder__`, `_private`, and callable access
3. **Metatable cleanup**: Removes `string.dump` and `string.rep`
4. **Nuclear clearing**: All globals removed, only safe subset reinstalled
5. **Runtime validation**: 30+ checks on every engine init, fails if compromised
6. **Lua-safe returns**: API methods convert Python objects to Lua-native tables
7. **ID indirection**: No direct object references cross the boundary
8. **Deferred effects**: Side effects are queued and controlled
9. **Comprehensive tests**: 105 regression tests

This allows game designers to write flexible behaviors in Lua while maintaining strict isolation from the host system.
