# AMS Logging Architecture

The AMS logging system provides unified logging across native Python and browser (WebAssembly) environments. It consists of two complementary subsystems designed for different use cases.

## Design Goals

1. **Cross-runtime transparency**: Same API works identically in native Python and browser/WASM
2. **Zero runtime cost when disabled**: No string formatting or I/O when logging is off
3. **Environment-aware output routing**: Automatic selection of appropriate output (terminal, browser console, file, WebSocket)
4. **Structured data support**: High-volume structured logging (snapshots, telemetry) alongside text messages
5. **Minimal dependencies**: Core system uses only Python stdlib

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Application Code                                │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────────┐│
│  │  GameEngine    │  │   LuaBridge    │  │  RollbackStateManager          ││
│  │  log.info()    │  │  log.lua_call()│  │  logger.log_snapshot()         ││
│  └───────┬────────┘  └───────┬────────┘  └───────────────┬────────────────┘│
│          │                   │                           │                  │
│          │ Text Logging      │                           │ Structured       │
│          │                   │                           │ Records          │
│          ▼                   ▼                           ▼                  │
│  ┌─────────────────────────────────────┐  ┌────────────────────────────────┐│
│  │         AMSLogger (Text)            │  │     Sink System (Structured)   ││
│  │  • Per-module log levels            │  │  • emit_record() dispatch      ││
│  │  • Lazy message formatting          │  │  • Per-module sink registry    ││
│  │  • Lua execution tracing            │  │  • Environment-aware routing   ││
│  │  • Exception/traceback support      │  │  • JSONL serialization         ││
│  └───────────────┬─────────────────────┘  └───────────────┬────────────────┘│
│                  │                                        │                  │
└──────────────────┼────────────────────────────────────────┼──────────────────┘
                   │                                        │
       ┌───────────┴───────────┐            ┌───────────────┼───────────────┐
       ▼                       ▼            ▼               ▼               ▼
┌─────────────┐        ┌─────────────┐ ┌─────────┐  ┌─────────────┐ ┌───────────┐
│   Native    │        │   Browser   │ │ FileSink│  │WebSocketSink│ │ NullSink  │
│   stdout    │        │console.log()│ │  JSONL  │  │  Streaming  │ │  No-op    │
└─────────────┘        └─────────────┘ └─────────┘  └─────────────┘ └───────────┘
```

## Two Logging Subsystems

### 1. Text Logging (AMSLogger)

**Purpose**: Human-readable debug messages, warnings, errors, and Lua execution tracing.

**Use when**:
- Debugging application flow
- Logging errors and exceptions
- Tracing Lua script execution
- Operational status messages

**Output**: Formatted text to stdout (native) or browser console (WASM)

```python
from ams.logging import get_logger

log = get_logger('game_engine')
log.debug("Processing frame %d", frame)
log.error("Entity %s not found", entity_id)
log.lua_call("ams.get_x", entity_id)
```

### 2. Structured Record Logging (Sink System)

**Purpose**: High-volume structured data for analysis, replay, and debugging.

**Use when**:
- Logging game state snapshots
- Recording rollback events
- Capturing telemetry data
- Any data that will be programmatically analyzed

**Output**: JSONL to files (native) or WebSocket stream (browser)

```python
from ams.logging import emit_record

emit_record('rollback', {
    'type': 'snapshot',
    'frame_number': 100,
    'entities': {...},
})
```

## Text Logging Architecture

### AMSLogger

Each module gets a cached logger instance via `get_logger()`:

```
┌─────────────────────────────────────────────────────────────────┐
│                         AMSLogger                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Module    │  │  Effective  │  │    Output Adapter       │ │
│  │   Name      │  │   Level     │  │  (auto-detected)        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                  │
│  Methods:                                                        │
│  • trace/debug/info/warning/error/critical - Standard levels    │
│  • exception() - Error + traceback                              │
│  • lua_call/lua_result/lua_script - Lua tracing                 │
└─────────────────────────────────────────────────────────────────┘
```

### Log Levels

| Level | Value | Purpose |
|-------|-------|---------|
| TRACE | 5 | Per-frame data, very verbose |
| DEBUG | 10 | Development debugging |
| INFO | 20 | Normal operations |
| WARNING | 30 | Potential issues |
| ERROR | 40 | Recoverable errors |
| CRITICAL | 50 | Fatal errors |
| OFF | 100 | Disable logging |

### Output Format

```
[module_name] LEVEL: message
[game_engine] INFO: Game started
[lua_bridge] LUA→: ams.get_x("entity_123")
[lua_bridge] LUA←: ams.get_x = 150.5
```

### Configuration Hierarchy

```
Environment Variables          Programmatic Config
       │                              │
       ▼                              ▼
┌──────────────────────────────────────────────┐
│              Global _config Dict              │
│  ┌────────────────┐  ┌────────────────────┐ │
│  │ default_level  │  │  module_levels{}   │ │
│  │    (INFO)      │  │  game_engine: DEBUG│ │
│  └────────────────┘  └────────────────────┘ │
│  ┌────────────────┐  ┌────────────────────┐ │
│  │  lua_calls     │  │  lua_scripts       │ │
│  │   (False)      │  │    (False)         │ │
│  └────────────────┘  └────────────────────┘ │
└──────────────────────────────────────────────┘
                    │
                    ▼
            AMSLogger.level property
            (checks module_levels first,
             falls back to default_level)
```

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `AMS_LOG_LEVEL` | Global default level | `DEBUG` |
| `AMS_LOG_<MODULE>` | Per-module level | `AMS_LOG_GAME_ENGINE=DEBUG` |
| `AMS_LOG_LUA_CALLS` | Enable Lua API tracing | `1` or `true` |
| `AMS_LOG_LUA_SCRIPTS` | Enable script execution logging | `1` or `true` |
| `AMS_LOG_DIR` | Override log directory | `./debug_logs` |

## Structured Logging Architecture

### Sink System

The sink system routes structured records to environment-appropriate destinations:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Sink Registry                             │
│                                                                  │
│  _sinks: Dict[str, LogSink]     _default_sink: Optional[LogSink]│
│  ┌─────────────────────────┐    ┌─────────────────────────────┐ │
│  │ 'rollback' → FileSink   │    │     (fallback for unknown   │ │
│  │ 'telemetry' → FileSink  │    │      modules)               │ │
│  └─────────────────────────┘    └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      emit_record(module, record)                 │
│  1. Look up sink in _sinks[module]                              │
│  2. Fall back to _default_sink                                  │
│  3. Call sink.emit(module, record)                              │
│  4. Return True if emitted, False if no sink                    │
└─────────────────────────────────────────────────────────────────┘
```

### LogSink Abstract Base Class

```python
class LogSink(ABC):
    @abstractmethod
    def emit(self, module: str, record: Dict[str, Any]) -> None:
        """Write a structured record."""

    @abstractmethod
    def flush(self) -> None:
        """Flush buffered records."""

    @abstractmethod
    def close(self) -> None:
        """Close and release resources."""
```

### Sink Implementations

| Sink | Environment | Behavior |
|------|-------------|----------|
| **FileSink** | Native Python | Writes JSONL files, one per module. Lazy directory/file creation. Adds header/footer records. |
| **WebSocketSink** | Browser/WASM | Streams to WebSocket server. Buffers if disconnected. Auto-reconnect. |
| **NullSink** | Any | No-op. Used when module logging is disabled. |

### FileSink Architecture

```
FileSink
  │
  ├── _log_dir: Path (lazy-initialized)
  ├── _session_name: str
  ├── _files: Dict[module, file_handle]
  │
  └── emit(module, record)
        │
        ├── Ensure directory exists
        ├── Get/create file for module
        ├── Add wall_time if missing
        └── Write JSON + newline
```

**File naming**: `{session_name}_{module}.jsonl`

**Record format (JSONL)**:
```jsonl
{"type": "header", "module": "rollback", "session_name": "debug", "start_time": 1702368000.0}
{"type": "snapshot", "wall_time": 1702368001.0, "frame_number": 0, "score": 0}
{"type": "snapshot", "wall_time": 1702368002.0, "frame_number": 60, "score": 100}
{"type": "footer", "module": "rollback", "end_time": 1702368120.0}
```

### Module Configuration

Modules can have hierarchical settings via environment variables:

```bash
AMS_LOGGING_ROLLBACK_ENABLED=true
AMS_LOGGING_ROLLBACK_INTERVAL=5
```

Parsed into:
```python
_config['modules']['rollback'] = {
    'enabled': True,
    'interval': 5
}
```

Retrieved via:
```python
from ams.logging import get_module_config
config = get_module_config('rollback')
# {'enabled': True, 'interval': 5}
```

### Environment Detection

```python
def _is_browser() -> bool:
    return sys.platform == 'emscripten'

def create_sink_for_environment(module, session_name=None) -> LogSink:
    config = get_module_config(module)
    if not config.get('enabled', False):
        return NullSink()

    if _is_browser():
        return WebSocketSink(url=config.get('websocket_url', 'ws://localhost:8765'))
    else:
        return FileSink(session_name=session_name)
```

## Cross-Runtime Behavior

### Native Python

| Subsystem | Output |
|-----------|--------|
| Text logging | `print()` to stdout |
| Structured logging | JSONL files in log directory |

### Browser (Emscripten/WASM)

| Subsystem | Output |
|-----------|--------|
| Text logging | `print()` + `console.log()` |
| Structured logging | WebSocket stream to dev server |

### Log Directory Resolution

Priority order:
1. `AMS_LOG_DIR` environment variable
2. Programmatic `_config['log_dir']`
3. Platform default:
   - macOS: `~/Library/Application Support/AMS/logs`
   - Windows: `%APPDATA%/AMS/logs`
   - Linux: `~/.local/share/ams/logs`

## Performance Characteristics

### Text Logging

| Operation | Cost |
|-----------|------|
| Level check | O(1) dict lookup |
| Disabled message | Zero cost (no formatting) |
| Logger lookup | O(1) with LRU cache |
| Message formatting | Lazy (only if will be logged) |

### Structured Logging

| Operation | Cost |
|-----------|------|
| No sink registered | O(1) dict lookup, returns False |
| NullSink | O(1) no-op |
| FileSink emit | O(n) JSON serialization + file write |
| WebSocketSink emit | O(n) JSON serialization + network I/O (or buffer) |

## Extension Points

### Adding a New Sink Type

1. Subclass `LogSink`
2. Implement `emit()`, `flush()`, `close()`
3. Register via `register_sink(module, sink)`

```python
class CloudSink(LogSink):
    def __init__(self, endpoint: str):
        self._endpoint = endpoint
        self._batch = []

    def emit(self, module: str, record: Dict[str, Any]) -> None:
        self._batch.append({'module': module, **record})
        if len(self._batch) >= 100:
            self._flush_batch()

    def flush(self) -> None:
        self._flush_batch()

    def close(self) -> None:
        self._flush_batch()
```

### Adding Module-Specific Configuration

1. Set via environment variable: `AMS_LOGGING_<MODULE>_<KEY>=value`
2. Retrieve via `get_module_config(module)`

## File Reference

| File | Purpose |
|------|---------|
| `ams/logging.py` | Core logging module (AMSLogger + Sink system) |
| `ams/games/game_engine/rollback/logger.py` | GameStateLogger using sink system |
| `games/browser/log_server.py` | WebSocket server for browser log streaming |
| `docs/architecture/LOGGING.md` | This document |
| `docs/guides/LOGGING_GUIDE.md` | Developer guide with usage examples |

## Design Decisions

### Why Two Subsystems?

Text logging and structured logging have different requirements:

| Aspect | Text Logging | Structured Logging |
|--------|--------------|-------------------|
| Volume | Low-medium | Potentially very high |
| Format | Human-readable | Machine-parseable |
| Filtering | By log level | By module enablement |
| Output | Console/terminal | Files/streams |
| Analysis | Read by humans | Processed by tools |

Combining them would compromise both.

### Why Sink Registry Instead of Direct File Handles?

1. **Environment transparency**: Code doesn't know if it's writing to file or WebSocket
2. **Testability**: Can inject NullSink or mock sink in tests
3. **Flexibility**: Can add new sink types without changing application code
4. **Resource management**: Centralized cleanup via `close_all_sinks()`

### Why JSONL Instead of JSON Arrays?

1. **Streaming**: Can append records without loading entire file
2. **Crash resilience**: Partial files are still parseable
3. **Memory efficiency**: Process one record at a time
4. **Tool compatibility**: Works with `jq`, `grep`, streaming parsers
