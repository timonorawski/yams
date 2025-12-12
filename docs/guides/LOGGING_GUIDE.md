# AMS Logging Developer Guide

Practical guide for using the AMS logging system. For architecture details, see [LOGGING.md](../architecture/LOGGING.md).

## Quick Start

### Text Logging (Debug Messages)

```python
from ams.logging import get_logger

log = get_logger('my_module')

log.debug("Processing entity %s", entity_id)
log.info("Game started")
log.warning("Low framerate: %d fps", fps)
log.error("Failed to load: %s", filename)
```

### Structured Logging (Data Records)

```python
from ams.logging import emit_record, FileSink, register_sink

# Set up sink (once at startup)
sink = FileSink(session_name='debug_session')
register_sink('my_module', sink)

# Emit records
emit_record('my_module', {
    'type': 'event',
    'frame': 100,
    'data': {...}
})

# Clean up
sink.close()
```

## Configuration

### Via Environment Variables (.env)

```bash
# Text logging levels
AMS_LOG_LEVEL=INFO                    # Global default
AMS_LOG_GAME_ENGINE=DEBUG             # Per-module override
AMS_LOG_LUA_BRIDGE=WARNING

# Lua tracing (for debugging Lua scripts)
AMS_LOG_LUA_CALLS=true                # Log ams.* API calls
AMS_LOG_LUA_SCRIPTS=true              # Log script execution

# Structured logging
AMS_LOGGING_ROLLBACK_ENABLED=true     # Enable rollback snapshot logging
AMS_LOGGING_ROLLBACK_INTERVAL=5       # Log every 5th snapshot

# Output location
AMS_LOG_DIR=./debug_logs              # Override log directory
```

### Via Code

```python
from ams.logging import configure_logging, enable_all_logging

# Simple: set global level
configure_logging(level='DEBUG')

# Advanced: per-module + Lua tracing
configure_logging(
    level='INFO',
    modules={
        'game_engine': 'DEBUG',
        'lua_bridge': 'TRACE',
    },
    lua_calls=True,
    lua_scripts=True,
)

# Quick: enable everything for debugging
enable_all_logging()
```

## Text Logging Patterns

### Basic Logging

```python
from ams.logging import get_logger

log = get_logger('game_engine')

# Standard levels
log.trace("Per-frame: pos=(%f, %f)", x, y)  # Very verbose
log.debug("Entity created: %s", entity_id)
log.info("Level loaded: %s", level_name)
log.warning("Health low: %d", health)
log.error("Collision failed: %s", reason)
log.critical("Fatal: %s", error)
```

### Exception Handling

```python
try:
    risky_operation()
except Exception as e:
    # Log error with full traceback
    log.exception("Operation failed")

    # Or manually
    log.error("Operation failed: %s", e)
    log.log_traceback(e)
```

### Lua Execution Tracing

```python
# In your Lua bridge code
log.lua_call("ams.get_x", entity_id)       # → [module] LUA→: ams.get_x("e123")
result = lua.get_x(entity_id)
log.lua_result("ams.get_x", result)        # → [module] LUA←: ams.get_x = 150.5

log.lua_script("behavior", "paddle", "on_update")  # → [module] LUA: on_update behavior/paddle
```

Only logs when `lua_calls` or `lua_scripts` is enabled.

## Structured Logging Patterns

### Manual Sink Setup

```python
from ams.logging import FileSink, register_sink, emit_record, close_all_sinks

# Create and register sink
sink = FileSink(
    log_dir='./logs',
    session_name='game_session_001'
)
register_sink('my_module', sink)

# Emit records anywhere in your code
emit_record('my_module', {'type': 'start', 'level': 'level_1'})
emit_record('my_module', {'type': 'score', 'points': 100})
emit_record('my_module', {'type': 'end', 'final_score': 500})

# Clean up at shutdown
close_all_sinks()
```

### Using GameStateLogger (Rollback System)

```python
from ams.games.game_engine.rollback import create_logger, RollbackStateManager

# Create logger (respects AMS_LOGGING_ROLLBACK_ENABLED)
logger = create_logger(session_name='debug_run')
manager = RollbackStateManager()

# In game loop
snapshot = manager.capture(game_engine)
logger.log_snapshot(snapshot)

# On rollback
logger.log_rollback(
    target_timestamp=hit_time,
    restored_frame=50,
    frames_resimulated=30,
    hit_position=(0.5, 0.3),
)

# Custom events
logger.log_event('hit_detected', {
    'entity_id': 'brick_42',
    'position': (100, 200),
})

# Clean up
logger.close()
```

### Force Enable (Bypass Config)

```python
# Create logger even if not enabled in config
logger = create_logger(session_name='debug', force=True)
```

## Analyzing Log Files

### Load and Inspect

```python
from ams.games.game_engine.rollback import load_log, summarize_log

# Load all records
records = load_log('debug_session_rollback.jsonl')
for r in records:
    if r.get('type') == 'snapshot':
        print(f"Frame {r['frame_number']}: score={r['score']}")

# Quick summary
summary = summarize_log('debug_session_rollback.jsonl')
print(f"Session: {summary['session_name']}")
print(f"Snapshots: {summary['logged_snapshots']}")
print(f"Rollbacks: {summary['rollback_count']}")
print(f"Final score: {summary['final_score']}")
```

### Command Line (jq)

```bash
# Count snapshots
cat debug_session_rollback.jsonl | jq -s '[.[] | select(.type=="snapshot")] | length'

# Get all scores
cat debug_session_rollback.jsonl | jq 'select(.type=="snapshot") | .score'

# Find rollback events
cat debug_session_rollback.jsonl | jq 'select(.type=="rollback")'

# Filter by frame range
cat debug_session_rollback.jsonl | jq 'select(.type=="snapshot" and .frame_number >= 100 and .frame_number <= 200)'
```

## Browser Development

### Remote Log Streaming

For browser builds, logs can stream to a local server:

```bash
# Start log server
python games/browser/log_server.py

# Open game with streaming enabled
# http://localhost:8000/?logstream=true
```

### Fetch Logs via API

```bash
# List sessions
curl http://localhost:8002/logs

# Get logs for a build
curl http://localhost:8002/logs/c4813854

# Filter
curl "http://localhost:8002/logs/c4813854?level=ERROR"
curl "http://localhost:8002/logs/c4813854?search=entity"
curl "http://localhost:8002/logs/c4813854?limit=100"
```

## Common Recipes

### Debug a Specific Module

```bash
# In .env or shell
export AMS_LOG_LEVEL=WARNING          # Quiet by default
export AMS_LOG_GAME_ENGINE=TRACE      # Verbose for game_engine only
```

### Capture Rollback Debug Session

```bash
# Enable snapshot logging
export AMS_LOGGING_ROLLBACK_ENABLED=true
export AMS_LOGGING_ROLLBACK_INTERVAL=1   # Every frame
export AMS_LOG_DIR=./debug_session

# Run game, reproduce issue, then analyze
python -c "
from ams.games.game_engine.rollback import summarize_log
import glob
for f in glob.glob('./debug_session/*.jsonl'):
    print(f, summarize_log(f))
"
```

### Disable All Logging (Production)

```python
from ams.logging import disable_logging
disable_logging()
```

Or via environment:
```bash
export AMS_LOG_LEVEL=OFF
```

### Custom Sink for Testing

```python
class CapturingSink(LogSink):
    def __init__(self):
        self.records = []

    def emit(self, module, record):
        self.records.append((module, record))

    def flush(self):
        pass

    def close(self):
        pass

# In tests
sink = CapturingSink()
register_sink('my_module', sink)

# Run code that emits records...

# Assert on captured records
assert len(sink.records) == 3
assert sink.records[0][1]['type'] == 'start'
```

## Troubleshooting

### Logs Not Appearing

1. Check log level: `print(log.level)` - is it higher than your message?
2. Check module name matches: `AMS_LOG_GAME_ENGINE` for `get_logger('game_engine')`
3. Verify environment variables are loaded (use python-dotenv or export)

### Structured Logs Not Written

1. Check sink is registered: `get_sink('my_module')` should not be None
2. Check module config: `get_module_config('my_module').get('enabled')`
3. Verify log directory exists and is writable

### Performance Issues

1. Set `AMS_LOG_LEVEL=WARNING` or higher in production
2. Use `log_interval > 1` for high-frequency snapshots
3. Use NullSink when logging not needed

## Module Naming Convention

| Component | Logger Name |
|-----------|-------------|
| GameEngine | `game_engine` |
| LuaEngine | `lua_engine` |
| LuaBridge (browser) | `lua_bridge` |
| ContentFS | `content_fs` |
| InputAdapter | `input_adapter` |
| Your module | `your_module` (lowercase, underscores) |

Environment variable format: `AMS_LOG_YOUR_MODULE=DEBUG`

## File Locations

| What | Where |
|------|-------|
| Log directory (macOS) | `~/Library/Application Support/AMS/logs` |
| Log directory (Linux) | `~/.local/share/ams/logs` |
| Log directory (Windows) | `%APPDATA%/AMS/logs` |
| Override | `AMS_LOG_DIR` environment variable |
