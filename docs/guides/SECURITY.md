# AMS Security Model

This document describes the security architecture of the AMS game engine, covering sandboxing of user content, filesystem isolation, and safe APIs exposed to untrusted code.

## Overview

AMS is designed to run user-provided content (YAML games, Lua scripts) safely without compromising the host system. The security model is built on **defense in depth** with multiple independent layers of protection.

### Trust Boundaries

```
┌──────────────────────────────────────────────────────────┐
│                    TRUSTED                                │
│  - Core Python code (ams/*, games/registry.py)           │
│  - Python game modes (games/*/game_mode.py) from core    │
│  - Detection backends                                     │
└──────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│                    UNTRUSTED                              │
│  - YAML game definitions (game.yaml)                     │
│  - Lua behaviors and collision actions                   │
│  - User-provided assets (sprites, sounds)                │
│  - Content from overlays and user directories            │
└──────────────────────────────────────────────────────────┘
```

**Key principle**: User content can customize game logic and assets, but cannot access the filesystem, network, or execute arbitrary Python code.

---

## Lua Sandbox

All game behavior logic runs in a sandboxed Lua VM with strict isolation from the Python interpreter and host system.

### Sandbox Architecture

The Lua sandbox uses **6 independent security layers**:

1. **Lupa Constructor Options** - Disable Python bridge at initialization
2. **Attribute Filter** - Block access to Python object internals
3. **String Metatable Cleanup** - Remove dangerous string functions
4. **Nuclear Global Clearing** - Remove all Lua globals, reinstall safe subset
5. **Runtime Validation** - Verify sandbox integrity on every engine init
6. **Lua-Safe Return Values** - Convert Python objects to Lua-native types

Each layer is independently effective. A vulnerability in one layer is still blocked by the others.

### Layer 1: Lupa Constructor Options

```python
self._lua = LuaRuntime(
    register_eval=False,      # Don't expose python.eval()
    register_builtins=False,  # Don't expose python.builtins.*
    unpack_returned_tuples=True,
    attribute_filter=_lua_attribute_filter
)
```

This prevents Lupa from injecting the `python.*` bridge at creation time.

### Layer 2: Attribute Filter

Blocks access to Python object internals even if objects leak through:

```python
def _lua_attribute_filter(obj, attr_name, is_setting):
    if attr_name.startswith('__'):
        raise AttributeError(f'Access to {attr_name} is blocked')
    if attr_name.startswith('_'):
        raise AttributeError(f'Access to private attribute {attr_name} is blocked')

    # Block callable attributes (methods) on Python objects
    if not is_setting:
        attr = getattr(obj, attr_name, None)
        if attr is not None and callable(attr):
            raise AttributeError(f'Access to callable {attr_name} is blocked')

    return attr_name
```

This prevents:
- `obj.__class__` - No class introspection
- `obj.__dict__` - No attribute enumeration
- `obj._private` - No internal state access
- `obj.method()` - No calling methods on leaked Python objects

### Layer 3: String Metatable Cleanup

Remove dangerous functions from built-in string metatable:

```python
self._lua.execute("""
    local mt = getmetatable("")
    if mt and mt.__index then
        mt.__index.dump = nil  -- Bytecode serialization
        mt.__index.rep = nil   -- Memory DoS: ("x"):rep(2^30)
    end
""")
```

Blocks:
- `string.dump()` - Function serialization to bytecode
- `string.rep()` - Unbounded memory allocation

### Layer 4: Nuclear Global Clearing

Clear ALL Lua globals, reinstall only safe subset:

```python
# Save safe primitives
safe_globals = {
    'pairs', 'ipairs', 'type', 'tostring', 'tonumber',
    'select', 'unpack', 'pcall', 'error', 'next',
    'math',  # Full math library (pure functions, no side effects)
}

# Nuclear: clear ALL globals
for key in list(g.keys()):
    g[key] = None

# Reinstall only safe globals
for key, value in safe_globals.items():
    g[key] = value
```

**Not preserved**: `string.*`, `table.*`, `io`, `os`, `debug`, `require`, `package`, `loadfile`, `dofile`, `load`, `loadstring`, `getfenv`, `setfenv`, `getmetatable`, `setmetatable`, `rawget`, `rawset`, `coroutine`, `collectgarbage`, `_G`

### Layer 5: Runtime Validation

Every `BehaviorEngine` initialization validates sandbox integrity:

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

    if failures:
        raise RuntimeError('Sandbox validation failed')
```

If validation fails, the engine **refuses to start**. This catches regressions in sandbox setup.

### Layer 6: Lua-Safe Return Values

API methods that return collections use `@lua_safe_function` decorator to convert Python objects to Lua-native types:

```python
@lua_safe_function
def get_entities_of_type(self, entity_type: str) -> list[str]:
    # Returns Python list
    return [e.id for e in entities if e.entity_type == entity_type]
```

Conversion rules:
- Python `list` → 1-indexed Lua table (works with `ipairs`, `#` operator)
- Python `dict` → Lua table (works with `pairs`)
- Primitives (int, float, str, bool, None) → Pass through
- **bytes** → Rejected (TypeError)
- **sets** → Rejected (TypeError)
- Unknown types → Rejected (TypeError)

This prevents Lua from receiving raw Python objects with different semantics (0-indexed lists, no `ipairs` support, etc.).

### What Lua CAN Access

#### Safe Lua Primitives

| Function | Purpose |
|----------|---------|
| `pairs`, `ipairs` | Iterate tables |
| `type`, `tostring`, `tonumber` | Type operations |
| `select`, `unpack` | Vararg handling |
| `pcall`, `error` | Error handling |
| `next` | Raw table iteration |
| `math.*` | Full math library (sin, cos, random, sqrt, etc.) |

**Note**: Basic string methods like `:upper()`, `:gsub()` work via string metatable (safe operations).

#### The `ams.*` API

Lua behaviors interact with the game engine through a whitelist of safe functions:

**Entity Properties**:
```lua
-- Position and velocity
ams.get_x(id), ams.set_x(id, value)
ams.get_vx(id), ams.set_vx(id, value)

-- Visual properties
ams.get_sprite(id), ams.set_sprite(id, name)
ams.get_color(id), ams.set_color(id, color)

-- State
ams.is_alive(id), ams.destroy(id)
```

**Custom Properties** (key-value storage):
```lua
ams.get_prop(id, "key"), ams.set_prop(id, "key", value)
ams.get_config(id, "behavior_name", "key", default)
```

**Entity Queries**:
```lua
ams.get_entities_of_type("brick")
ams.get_entities_by_tag("enemy")
ams.count_entities_by_tag("brick")
```

**Game State**:
```lua
ams.get_screen_width(), ams.get_screen_height()
ams.get_score(), ams.add_score(points)
ams.get_time()  -- Elapsed game time
```

**Effects** (queued for game layer):
```lua
ams.play_sound("explosion")
ams.schedule(2.0, "on_timer", entity_id)
```

**Math Utilities**:
```lua
ams.sin(rad), ams.cos(rad), ams.sqrt(x)
ams.random(), ams.random_range(min, max)
ams.clamp(value, min, max)
```

**Debug**:
```lua
ams.log("message")  -- Prints to console
```

### What Lua CANNOT Access

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

### ID-Based Access Pattern

Lua never holds direct Python object references:

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

This ensures:
- Lua cannot hold stale references to destroyed entities
- API can validate every access
- Python objects never exposed to Lua's garbage collector
- Entity storage can change without breaking Lua code

### Deferred Effects

Side effects don't execute immediately - they're queued for the game layer:

```python
# In LuaAPI
def play_sound(self, sound_name: str) -> None:
    self._engine.queue_sound(sound_name)  # Queued, not played

# In game layer (each frame)
for sound in behavior_engine.pop_sounds():
    audio_system.play(sound)
```

This prevents:
- Infinite loops blocking the game
- Unbounded resource allocation
- Race conditions from immediate execution

### Error Handling

Lua errors are caught and logged without crashing the game:

```python
try:
    behavior_method(entity_id, *args)
except Exception as e:
    print(f"[BehaviorEngine] Error in {behavior_name}: {e}")
    # Continue - one bad behavior doesn't crash the game
```

### Testing

The sandbox has 105 comprehensive regression tests in `tests/test_lua_sandbox.py`:

```bash
pytest tests/test_lua_sandbox.py -v
```

Test categories:
- **TestBlockedGlobals** - Dangerous globals are nil
- **TestBlockedOperations** - Dangerous operations fail
- **TestMetatableAccess** - Metatable functions blocked
- **TestAttributeFilter** - Python internals inaccessible
- **TestAllowedGlobals** - Safe primitives work
- **TestAmsApiAvailable** - ams.* API functions work
- **TestLuaSafeReturns** - API returns Lua-native tables
- **TestRuntimeValidation** - Validation catches issues

### Threat Model

#### Protected Against

- Arbitrary code execution
- File system access
- Network access
- Python interpreter access
- Environment variable access
- System command execution
- Memory corruption
- Bytecode injection
- Memory exhaustion via string operations
- Metatable manipulation
- Attribute enumeration on Python objects
- Method calls on leaked objects

#### Not Protected Against

| Threat | Status |
|--------|--------|
| Malicious YAML files | Trust boundary at YAML loading; schema-validated |
| CPU exhaustion | No execution time limits yet |
| Entity spawn flooding | No hard limits on `ams.spawn()` |
| Logic bugs in behaviors | Expected - that's what debugging is for |

### References

- Full Lua security documentation: `/docs/game_engine/LUA_SECURITY.md`
- Lua sandbox implementation: `/ams/lua/engine.py`
- Lua API implementation: `/ams/lua/api.py`
- Test suite: `/tests/test_lua_sandbox.py`

---

## ContentFS Layer Security

ContentFS provides a layered virtual filesystem for game assets with built-in sandbox protection.

### Layer Architecture

```
Priority 100: User Layer       ~/.local/share/ams/
Priority 10+: Overlay Layers   $AMS_OVERLAY_DIRS (team/shared content)
Priority 5:   Engine Layer     ams/games/game_engine/
```

**Key security property**: Repository root is NOT included as a filesystem layer. Only specific subdirectories (`ams/games/game_engine/`) are exposed.

### Sandbox Enforcement

ContentFS uses PyFilesystem2's `OSFS` which enforces sandbox boundaries:

```python
content_fs.exists('../../../etc/passwd')
# Raises: IllegalBackReference

content_fs.exists('games/../../../etc/passwd')
# Raises: IllegalBackReference

content_fs.exists('/etc/passwd')
# Returns: False (absolute paths don't exist within sandbox)
```

Each layer is independently sandboxed:
- **User layer**: Sandboxed to `~/.local/share/ams/`
- **Overlay layers**: Each sandboxed to its own directory
- **Engine layer**: Sandboxed to `ams/games/game_engine/`

A malicious path in user content **cannot escape** to access:
- Core repository files (Python source code)
- Other user's directories
- System files (`/etc/passwd`, etc.)

### Path Traversal Protection

PyFilesystem2 normalizes and validates all paths:

```python
# All of these are rejected:
content_fs.readtext('../../../ams/session.py')          # Back-reference
content_fs.readtext('games/../../ams/session.py')      # Back-reference
content_fs.readtext('/etc/passwd')                      # Absolute path
content_fs.getsyspath('../../calibration.py')          # Back-reference
```

### Layer Priority and Shadowing

Higher priority layers shadow lower priority layers:

```
User:    ~/.local/share/ams/games/DuckHunt/assets/sprites.png  (Priority 100)
  ↓ shadows
Core:    <repo>/games/DuckHunt/assets/sprites.png              (Priority 5)
```

When a user creates a custom sprite, it shadows the core sprite without modifying the repository.

### Repository Root Protection

**Critical security boundary**: The repository root (containing Python source code) is **not** included as a ContentFS layer.

```python
# In ContentFS.__init__():
# We intentionally do NOT add the repo root as a layer.
# Only specific subdirectories are exposed:

engine_dir = core_dir / 'ams' / 'games' / 'game_engine'
self._multi_fs.add_fs('engine', OSFS(str(engine_dir)), priority=5)
```

This means:
- Lua scripts can access `lua/behavior/bounce.lua` (via engine layer)
- Lua scripts **cannot** access `../../session.py` (not in any layer)
- YAML games can reference `assets/sprites.png` (via game layer)
- YAML games **cannot** reference `../../ams_game.py` (not in any layer)

### Direct Filesystem Access

The `core_dir` property provides direct filesystem access for trusted code:

```python
# Game registry uses this for Python game discovery
games_dir = content_fs.core_dir / 'games'
for game_dir in games_dir.iterdir():
    if (game_dir / 'game_mode.py').exists():
        # Load Python game (trusted code only)
```

This is **only used by trusted Python code** for:
- Game discovery (GameRegistry)
- Python game loading (from core repo only)
- YAML schema loading

Lua scripts and YAML games **never** have access to `core_dir`.

### Asset Resolution

Assets resolve through ContentFS layers:

```python
# In GameEngineRenderer._load_sprite():
if self._content_fs:
    # Resolve through layered filesystem
    real_path = self._content_fs.getsyspath(
        f'games/{game_slug}/assets/{sprite_file}'
    )
else:
    # Fallback to direct path (legacy)
    real_path = str(self._assets_dir / sprite_file)
```

The `getsyspath()` method:
1. Checks layers in priority order (user → overlay → engine)
2. Returns real filesystem path to the file
3. Rejects path traversal attempts
4. Raises `ResourceNotFound` if file doesn't exist in any layer

### References

- ContentFS implementation: `/ams/content_fs.py`
- Game registry architecture: `/docs/architecture/GAME_REGISTRY.md`

---

## Game Registry Security

The game registry discovers and loads games from ContentFS with different trust levels for Python vs YAML games.

### Python Games: Core Repository Only

**Python games can execute arbitrary code**, so they're only loaded from the core repository:

```python
# In GameRegistry._discover_games():

# 1. SECURITY: Python games only from core repo
games_dir = self._content_fs.core_dir / 'games'
if games_dir.exists():
    for game_dir in games_dir.iterdir():
        has_game_mode = (game_dir / 'game_mode.py').exists()
        if has_game_mode:
            self._register_game(game_dir)  # OK - from core repo
```

Python games from overlays or user directories are **ignored**. This prevents:
- User uploading `game_mode.py` that executes malicious Python
- Network shares containing trojan Python game modes
- Untrusted Python code execution

### YAML Games: All Layers

**YAML games run in sandboxed Lua**, so they're loaded from all ContentFS layers:

```python
# 2. YAML games from all ContentFS layers (Lua is sandboxed, safe)
if self._content_fs.exists('games'):
    for item_name in self._content_fs.listdir('games'):
        game_path = f'games/{item_name}'

        # Only YAML games from non-core layers
        if self._content_fs.exists(f'{game_path}/game.yaml'):
            real_game_dir = Path(self._content_fs.getsyspath(game_path))
            self._register_yaml_game(real_game_dir)  # OK - Lua sandboxed
```

This allows:
- Users creating custom games in `~/.local/share/ams/games/MyGame/`
- Team sharing games via `AMS_OVERLAY_DIRS`
- Modding and customization

Since YAML games only execute Lua (which is sandboxed), they cannot compromise the host system.

### Game Class Caching

Game classes are cached to prevent repeated imports:

```python
self._game_classes: Dict[str, Type['BaseGame']] = {}

# On first access:
game_class = self._find_game_class(game_dir, module_path)
self._game_classes[slug] = game_class

# On subsequent access:
game_class = self._game_classes.get(slug)
if game_class is not None:
    return game_class(**kwargs)
```

This prevents:
- Import side effects executing multiple times
- Module reload vulnerabilities
- Race conditions in game loading

### Discovery Rules

Directories are skipped if:
- Name starts with `_` or `.` (private/hidden)
- Name in `['base', 'common', '__pycache__']` (internal)
- Not a directory
- Missing both `game.yaml` and `game_mode.py`

### Summary: Trust Model

| Game Type | Source | Reason |
|-----------|--------|--------|
| Python (`game_mode.py`) | Core repo only | Arbitrary code execution risk |
| YAML (`game.yaml`) | All layers | Lua sandbox prevents escalation |
| Lua behaviors | All layers | Sandboxed - cannot access system |
| Assets (sprites/sounds) | All layers | No code execution |

### References

- Game registry implementation: `/games/registry.py`
- Game registry architecture: `/docs/architecture/GAME_REGISTRY.md`

---

## YAML Schema Validation

All YAML game definitions are validated against JSON schemas before loading.

### Schema Files

| Schema | Location | Validates |
|--------|----------|-----------|
| `game.schema.json` | `/schemas/game.schema.json` | Game definitions (`game.yaml`) |
| `level.schema.json` | `/schemas/level.schema.json` | Level files (`levels/*.yaml`) |

### Validation Process

```python
# In GameEngine._load_game_definition():
if not os.environ.get('AMS_SKIP_SCHEMA_VALIDATION'):
    # Validate against schema
    validator = get_game_schema_validator()
    validator.validate(game_data)
```

This catches:
- Invalid field names (typos in YAML)
- Type mismatches (string instead of number)
- Missing required fields
- Invalid enum values
- Structural errors

Schema validation is a **data integrity check**, not a security boundary. Malicious YAML can still be schema-valid but malicious in intent (e.g., spawning 10,000 entities). The Lua sandbox prevents escalation.

### Bypassing Validation

Schema validation can be skipped for debugging:

```bash
export AMS_SKIP_SCHEMA_VALIDATION=1
python ams_game.py --game mygame
```

This is useful when:
- Developing new schema features
- Debugging schema validation issues
- Working with prototype YAML before schema update

**Warning**: Skipping validation may cause runtime errors if YAML is malformed.

---

## Environment Variables

Environment variables control security-related behavior:

| Variable | Default | Security Impact |
|----------|---------|-----------------|
| `AMS_DATA_DIR` | XDG default | User content directory (sandboxed) |
| `AMS_OVERLAY_DIRS` | (none) | Colon-separated overlay paths (each sandboxed) |
| `AMS_SKIP_SCHEMA_VALIDATION` | `0` | Disables YAML schema validation |

### XDG Compliance

Default user directories follow XDG Base Directory Specification:

```python
# macOS
~/Library/Application Support/AMS/

# Windows
%APPDATA%/AMS/

# Linux/BSD
~/.local/share/ams/   # or $XDG_DATA_HOME/ams/
```

These locations:
- Are user-writable
- Don't require elevated privileges
- Follow platform conventions
- Are automatically sandboxed by ContentFS

---

## Security Checklist

Before running untrusted content:

- [ ] Lua sandbox validation passes (automatic)
- [ ] ContentFS layers properly sandboxed (automatic)
- [ ] Python games only from core repo (automatic)
- [ ] YAML schema validation enabled (default)
- [ ] No suspicious environment variables set
- [ ] Asset files scanned for malware (manual)

---

## Future Enhancements

Planned security improvements:

1. **Execution Time Limits**: Kill Lua scripts that run too long (DoS prevention)
2. **Entity Count Limits**: Cap total entities to prevent spawn floods
3. **Memory Limits**: Restrict Lua heap size via `lua_max_memory` parameter
4. **Script Signing**: Verify authorship of behavior scripts (trust chain)
5. **Permission Levels**: Different API access for different script sources
6. **WASM Sandbox**: Alternative ContentFS backend for browser deployment

---

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT create a public GitHub issue**
2. Contact the maintainers privately
3. Provide:
   - Exploit description
   - Proof-of-concept (if possible)
   - Affected versions
   - Suggested fix (optional)

---

## References

### Documentation

- Lua Sandbox: `/docs/game_engine/LUA_SECURITY.md`
- Game Engine Architecture: `/docs/GAME_ENGINE_ARCHITECTURE.md`
- Game Registry: `/docs/architecture/GAME_REGISTRY.md`

### Implementation

- Lua Engine: `/ams/lua/engine.py`
- Lua API: `/ams/lua/api.py`
- ContentFS: `/ams/content_fs.py`
- Game Registry: `/games/registry.py`

### Testing

- Lua Sandbox Tests: `/tests/test_lua_sandbox.py` (105 tests)
- Run tests: `pytest tests/test_lua_sandbox.py -v`
