# AMS Logging Architecture

Unified logging system for the Arcade Management System that works consistently across native Python and browser (WebAssembly) environments.

## Overview

The AMS logging system provides:
- **Cross-runtime support**: Same API works in native Python and browser (Emscripten/WASM)
- **Per-module log levels**: Fine-grained control over what gets logged
- **Lua execution tracing**: Special support for debugging Lua scripts and ams.* API calls
- **Exception handling**: Integrated traceback logging
- **Zero dependencies**: Uses only Python stdlib

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Application Code                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ GameEngine   │  │  LuaBridge   │  │  ContentFS   │  ...         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                        │
│         └─────────────────┼─────────────────┘                        │
│                           │                                          │
│                           ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     ams.logging                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │ AMSLogger   │  │   Config    │  │  Output Adapters    │  │   │
│  │  │  .debug()   │  │  - levels   │  │  - print() native   │  │   │
│  │  │  .info()    │  │  - modules  │  │  - console.log()    │  │   │
│  │  │  .error()   │  │  - lua_*    │  │    browser          │  │   │
│  │  │  .lua_call()│  │             │  │                     │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
        ┌───────────────┐               ┌───────────────┐
        │    Native     │               │    Browser    │
        │   Terminal    │               │    Console    │
        │   stdout      │               │  DevTools     │
        └───────────────┘               └───────────────┘
```

## Usage

### Basic Usage

```python
from ams.logging import get_logger

log = get_logger('game_engine')

log.debug("Processing frame %d", frame_count)
log.info("Game started: %s", game_name)
log.warning("Low FPS detected: %d", fps)
log.error("Failed to load level: %s", level_name)
```

### Log Levels

| Level | Value | Use Case |
|-------|-------|----------|
| TRACE | 5 | Very verbose, per-frame data |
| DEBUG | 10 | Development debugging |
| INFO | 20 | Normal operational messages |
| WARNING | 30 | Potential issues |
| ERROR | 40 | Errors that don't crash |
| CRITICAL | 50 | Fatal errors |
| OFF | 100 | Disable logging |

### Exception Logging

```python
try:
    risky_operation()
except Exception as e:
    log.exception("Operation failed")  # Includes traceback
    # or
    log.error("Operation failed: %s", e)
    log.log_traceback(e)  # Explicit traceback
```

### Lua Execution Tracing

Special methods for debugging Lua script execution:

```python
# Log ams.* API calls from Lua
log.lua_call("ams.get_x", entity_id)  # Logs: [module] LUA→: ams.get_x("entity_123")
log.lua_result("ams.get_x", 150.5)    # Logs: [module] LUA←: ams.get_x = 150.5

# Log script execution
log.lua_script("behavior", "paddle", "on_update")  # Logs: [module] LUA: on_update behavior/paddle
```

These only log when `lua_calls` or `lua_scripts` tracing is enabled.

## Configuration

### Environment Variables

```bash
# Global default level
export AMS_LOG_LEVEL=DEBUG

# Per-module levels (module name after AMS_LOG_)
export AMS_LOG_GAME_ENGINE=DEBUG
export AMS_LOG_LUA_BRIDGE=INFO
export AMS_LOG_WASMOON=WARNING

# Lua tracing
export AMS_LOG_LUA_CALLS=1      # Trace ams.* API calls
export AMS_LOG_LUA_SCRIPTS=1    # Log script execution
```

### Programmatic Configuration

```python
from ams.logging import configure_logging

# Simple: set global level
configure_logging(level='DEBUG')

# Advanced: per-module levels + Lua tracing
configure_logging(
    level='INFO',
    modules={
        'game_engine': 'DEBUG',
        'lua_bridge': 'DEBUG',
        'content_fs': 'WARNING',
    },
    lua_calls=True,
    lua_scripts=True,
)
```

### Quick Helpers

```python
from ams.logging import enable_all_logging, disable_logging

# Enable everything for debugging
enable_all_logging()

# Disable all logging (production)
disable_logging()
```

## Cross-Runtime Support

### Native Python

In native Python, logs go to `stdout` via `print()`:

```
[game_engine] INFO: Game started: BrickBreaker
[lua_bridge] DEBUG: Loading behavior/paddle
[game_engine] LUA→: ams.get_x("paddle_001")
```

### Browser (Emscripten/WASM)

In the browser, logs go to both Python's stdout (visible in terminal if running pygbag locally) AND the browser's `console.log()`:

```javascript
// Browser DevTools Console:
[game_engine] INFO: Game started: BrickBreaker
[lua_bridge] DEBUG: Loading behavior/paddle
```

The runtime detection is automatic:

```python
def _is_browser() -> bool:
    return sys.platform == 'emscripten'
```

## Module Naming Conventions

| Module | Logger Name | Description |
|--------|-------------|-------------|
| GameEngine | `game_engine` | Core game loop, entity management |
| LuaEngine (native) | `lua_engine` | Native lupa-based Lua execution |
| LuaBridge (browser) | `lua_bridge` | Browser WASMOON bridge |
| WASMOON JS | `wasmoon` | JavaScript-side Lua execution |
| ContentFS | `content_fs` | Virtual filesystem |
| InputAdapter | `input_adapter` | Input event handling |
| GameRuntime | `game_runtime` | Browser game loop wrapper |

## Integration Examples

### Game Engine Integration

```python
# ams/games/game_engine/engine.py
from ams.logging import get_logger

log = get_logger('game_engine')

class GameEngine:
    def update(self, dt: float) -> None:
        log.trace("update(dt=%f)", dt)

        for entity in self.entities:
            try:
                self._update_entity(entity, dt)
            except Exception as e:
                log.exception("Failed to update entity %s", entity.id)
```

### Lua Bridge Integration

```python
# games/browser/lua_bridge.py
from ams.logging import get_logger

log = get_logger('lua_bridge')

class LuaEngineBrowser:
    def load_subroutine(self, sub_type: str, name: str, path: str) -> bool:
        log.lua_script(sub_type, name, "load")

        try:
            code = self._content_fs.readtext(path)
            self._send_to_js('lua_load_subroutine', {...})
            log.debug("Loaded %s/%s", sub_type, name)
            return True
        except Exception as e:
            log.exception("Failed to load %s/%s", sub_type, name)
            return False
```

### JavaScript (WASMOON) Integration

For JavaScript-side logging, use a similar pattern:

```javascript
// wasmoon_bridge.js
const LOG_LEVEL = {
    TRACE: 5, DEBUG: 10, INFO: 20, WARNING: 30, ERROR: 40
};

let currentLogLevel = LOG_LEVEL.INFO;

function log(level, module, msg, ...args) {
    if (level < currentLogLevel) return;
    const levelName = Object.keys(LOG_LEVEL).find(k => LOG_LEVEL[k] === level);
    console.log(`[${module}] ${levelName}: ${msg}`, ...args);
}

// Usage
log(LOG_LEVEL.DEBUG, 'wasmoon', 'Executing behavior/%s.on_update', behaviorName);
```

## Output Format

All log messages follow a consistent format:

```
[module_name] LEVEL: message
```

For Lua tracing:
```
[module_name] LUA→: function_name(args)     # Call into Lua
[module_name] LUA←: function_name = result  # Return from Lua
[module_name] LUA: action type/name         # Script execution
```

For tracebacks:
```
[module_name] ERROR: Operation failed
[module_name] TRACE: Traceback (most recent call last):
[module_name] TRACE:   File "engine.py", line 123, in update
[module_name] TRACE:     entity.process()
[module_name] TRACE: ValueError: Invalid state
```

## Performance Considerations

1. **Level checking is fast**: `if level >= self.level` is O(1)
2. **Message formatting is lazy**: String formatting only happens if the message will be logged
3. **Logger instances are cached**: `get_logger()` uses `@lru_cache`
4. **No I/O overhead when disabled**: Setting level to OFF skips all processing

## Files

| File | Description |
|------|-------------|
| `ams/logging.py` | Core logging module |
| `docs/architecture/LOGGING.md` | This documentation |

## Future Enhancements

- [ ] Log to file in addition to console
- [ ] Structured JSON logging for log aggregation
- [ ] Log sampling for high-frequency messages
- [ ] Remote logging endpoint for browser builds
- [ ] Log viewer UI in web controller
