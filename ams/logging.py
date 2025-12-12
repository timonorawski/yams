"""
AMS Unified Logging System

Provides consistent logging across native Python and browser (WASM) environments.
Supports per-module log levels and special tracing for Lua execution.

Structured Record Logging:
    The system supports structured log records that can be routed to different
    sinks depending on environment:
    - Native Python: FileSink writes JSONL to disk
    - Browser/WASM: WebSocketSink streams to dev server

Usage:
    from ams.logging import get_logger

    log = get_logger('game_engine')
    log.debug("Processing entity")
    log.info("Game started")
    log.lua_call("ams.get_x", entity_id)  # Special Lua tracing

    # Structured record logging (for rollback snapshots, etc.)
    from ams.logging import emit_record
    emit_record('rollback', {'type': 'snapshot', 'frame': 100, ...})

Configuration:
    Environment variables:
        AMS_LOG_LEVEL=DEBUG           # Global default level
        AMS_LOG_GAME_ENGINE=DEBUG     # Module-specific level
        AMS_LOG_LUA_BRIDGE=INFO
        AMS_LOG_LUA_CALLS=1           # Enable Lua API call tracing
        AMS_LOG_LUA_SCRIPTS=1         # Log script execution

        # Module-specific structured logging
        AMS_LOGGING_ROLLBACK_ENABLED=true
        AMS_LOGGING_ROLLBACK_INTERVAL=5

    Or programmatically:
        from ams.logging import configure_logging
        configure_logging(level='DEBUG', modules={'lua_bridge': 'INFO'})
"""

import json
import os
import sys
import time
from abc import ABC, abstractmethod
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, List, Optional
from functools import lru_cache


class LogLevel(IntEnum):
    """Log levels matching Python's logging module."""
    TRACE = 5      # Even more verbose than DEBUG
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    OFF = 100      # Disable logging


# =============================================================================
# Sink-Based Structured Logging
# =============================================================================

class LogSink(ABC):
    """
    Abstract base class for log record sinks.

    Sinks receive structured log records and write them to their destination.
    Different sinks handle different environments (file, websocket, etc.).
    """

    @abstractmethod
    def emit(self, module: str, record: Dict[str, Any]) -> None:
        """
        Emit a structured log record.

        Args:
            module: Module name (e.g., 'rollback', 'game_engine')
            record: Structured data to log (must be JSON-serializable)
        """
        pass

    @abstractmethod
    def flush(self) -> None:
        """Flush any buffered records."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the sink and release resources."""
        pass

    def __enter__(self) -> 'LogSink':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class FileSink(LogSink):
    """
    Writes structured log records to JSONL files.

    Each module gets its own file in the log directory. Records are written
    as JSON Lines (one JSON object per line) for easy streaming and parsing.

    Args:
        log_dir: Directory for log files (default: from get_log_dir())
        session_name: Session identifier for file naming (default: timestamp)
    """

    def __init__(
        self,
        log_dir: Optional[str] = None,
        session_name: Optional[str] = None,
    ):
        self._log_dir = Path(log_dir) if log_dir else None
        self._session_name = session_name or time.strftime("%Y%m%d_%H%M%S")
        self._files: Dict[str, Any] = {}  # module -> file handle
        self._initialized = False

    def _ensure_dir(self) -> Path:
        """Lazily initialize log directory."""
        if self._log_dir is None:
            self._log_dir = Path(get_log_dir())
        self._log_dir.mkdir(parents=True, exist_ok=True)
        return self._log_dir

    def _get_file(self, module: str):
        """Get or create file handle for module."""
        if module not in self._files:
            log_dir = self._ensure_dir()
            path = log_dir / f"{self._session_name}_{module}.jsonl"
            self._files[module] = open(path, 'a')

            # Write header on new file
            header = {
                "type": "header",
                "module": module,
                "session_name": self._session_name,
                "start_time": time.time(),
                "start_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            self._files[module].write(json.dumps(header) + "\n")

        return self._files[module]

    def emit(self, module: str, record: Dict[str, Any]) -> None:
        """Write record to module's JSONL file."""
        f = self._get_file(module)
        # Add timestamp if not present
        if 'wall_time' not in record:
            record = {'wall_time': time.time(), **record}
        f.write(json.dumps(record) + "\n")

    def flush(self) -> None:
        """Flush all open files."""
        for f in self._files.values():
            f.flush()

    def close(self) -> None:
        """Close all open files."""
        for module, f in self._files.items():
            # Write footer
            footer = {
                "type": "footer",
                "module": module,
                "end_time": time.time(),
                "end_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            f.write(json.dumps(footer) + "\n")
            f.close()
        self._files.clear()

    @property
    def log_paths(self) -> Dict[str, Path]:
        """Get paths to all log files."""
        log_dir = self._ensure_dir()
        return {
            module: log_dir / f"{self._session_name}_{module}.jsonl"
            for module in self._files
        }


class WebSocketSink(LogSink):
    """
    Streams structured log records to a WebSocket server.

    Used in browser/WASM environments to send logs to a development server
    for real-time debugging.

    Args:
        url: WebSocket server URL (default: ws://localhost:8765)
        buffer_size: Max records to buffer if disconnected (default: 100)
    """

    def __init__(
        self,
        url: str = "ws://localhost:8765",
        buffer_size: int = 100,
    ):
        self._url = url
        self._buffer_size = buffer_size
        self._buffer: List[Dict[str, Any]] = []
        self._connected = False
        self._ws = None

    def _ensure_connected(self) -> bool:
        """Attempt to establish WebSocket connection."""
        if self._connected:
            return True

        if _is_browser():
            try:
                # Browser WebSocket via Pyodide/Emscripten
                import platform
                self._ws = platform.window.WebSocket.new(self._url)
                self._connected = True
                # Flush buffered records
                self._flush_buffer()
                return True
            except Exception:
                return False
        else:
            # Native Python - try websockets library
            try:
                import asyncio
                import websockets
                # For native, we'd need async handling
                # For now, just buffer and skip
                return False
            except ImportError:
                return False

    def _flush_buffer(self) -> None:
        """Send buffered records."""
        if not self._connected or not self._ws:
            return

        for record in self._buffer:
            try:
                self._ws.send(json.dumps(record))
            except Exception:
                break
        self._buffer.clear()

    def emit(self, module: str, record: Dict[str, Any]) -> None:
        """Send record to WebSocket or buffer if disconnected."""
        record = {'module': module, 'wall_time': time.time(), **record}

        if self._ensure_connected() and self._ws:
            try:
                self._ws.send(json.dumps(record))
                return
            except Exception:
                self._connected = False

        # Buffer if not connected
        self._buffer.append(record)
        if len(self._buffer) > self._buffer_size:
            self._buffer.pop(0)  # Drop oldest

    def flush(self) -> None:
        """Attempt to flush buffer to WebSocket."""
        self._flush_buffer()

    def close(self) -> None:
        """Close WebSocket connection."""
        if self._ws and self._connected:
            try:
                self._ws.close()
            except Exception:
                pass
        self._ws = None
        self._connected = False
        self._buffer.clear()


class NullSink(LogSink):
    """No-op sink when logging is disabled."""

    def emit(self, module: str, record: Dict[str, Any]) -> None:
        pass

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


# Sink registry - active sinks by module
_sinks: Dict[str, LogSink] = {}
_default_sink: Optional[LogSink] = None


def register_sink(module: str, sink: LogSink) -> None:
    """
    Register a sink for a specific module.

    Args:
        module: Module name (e.g., 'rollback')
        sink: Sink instance to receive records
    """
    _sinks[module] = sink


def set_default_sink(sink: LogSink) -> None:
    """Set the default sink for modules without specific sinks."""
    global _default_sink
    _default_sink = sink


def get_sink(module: str) -> Optional[LogSink]:
    """Get the sink for a module, or default sink."""
    return _sinks.get(module, _default_sink)


def emit_record(module: str, record: Dict[str, Any]) -> bool:
    """
    Emit a structured log record to the appropriate sink.

    Args:
        module: Module name (e.g., 'rollback', 'game_engine')
        record: Structured data to log (must be JSON-serializable)

    Returns:
        True if record was emitted, False if no sink available
    """
    sink = get_sink(module)
    if sink:
        sink.emit(module, record)
        return True
    return False


def close_all_sinks() -> None:
    """Close all registered sinks."""
    global _default_sink
    for sink in _sinks.values():
        sink.close()
    _sinks.clear()
    if _default_sink:
        _default_sink.close()
        _default_sink = None


def create_sink_for_environment(
    module: str,
    session_name: Optional[str] = None,
) -> LogSink:
    """
    Create appropriate sink for current environment.

    In browser/WASM: WebSocketSink
    In native Python: FileSink

    Args:
        module: Module name for configuration lookup
        session_name: Optional session identifier

    Returns:
        Appropriate LogSink for the environment
    """
    config = get_module_config(module)
    if not config.get('enabled', False):
        return NullSink()

    if _is_browser():
        ws_url = config.get('websocket_url', 'ws://localhost:8765')
        return WebSocketSink(url=ws_url)
    else:
        return FileSink(session_name=session_name)


# =============================================================================
# Global configuration
# =============================================================================

# Global configuration
_config: Dict[str, Any] = {
    'default_level': LogLevel.INFO,
    'module_levels': {},
    'lua_calls': False,      # Trace ams.* API calls from Lua
    'lua_scripts': False,    # Log which scripts are executed
    'output': 'auto',        # 'auto', 'console', 'js'
    'log_dir': None,         # Override log directory (None = platform default)
    'modules': {},           # Per-module settings (hierarchical)
}


def _is_browser() -> bool:
    """Check if running in browser (Emscripten/WASM)."""
    return sys.platform == 'emscripten'


def get_log_dir() -> str:
    """Get the log directory, respecting AMS_LOG_DIR env var.

    Priority:
    1. AMS_LOG_DIR environment variable
    2. Configured log_dir in _config
    3. Platform-specific user data directory:
       - macOS: ~/Library/Application Support/AMS/logs
       - Windows: %APPDATA%/AMS/logs
       - Linux: ~/.local/share/ams/logs

    Returns:
        Path to log directory (as string)
    """
    from pathlib import Path

    # Check explicit config first
    if _config.get('log_dir'):
        return str(Path(_config['log_dir']).expanduser())

    # Check env var
    env_dir = os.environ.get('AMS_LOG_DIR')
    if env_dir:
        return str(Path(env_dir).expanduser())

    # Fall back to platform default
    if sys.platform == 'darwin':
        user_data = Path.home() / 'Library' / 'Application Support' / 'AMS'
    elif sys.platform == 'win32':
        user_data = Path(os.environ.get('APPDATA', str(Path.home()))) / 'AMS'
    else:
        xdg_data = os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))
        user_data = Path(xdg_data) / 'ams'

    return str(user_data / 'logs')


def get_module_config(module: str) -> Dict[str, Any]:
    """Get configuration for a specific module.

    Modules can have hierarchical settings configured via env vars:
        AMS_LOGGING_ROLLBACK_ENABLED=true
        AMS_LOGGING_ROLLBACK_SNAPSHOT_INTERVAL=5

    Maps to:
        {'enabled': True, 'snapshot': {'interval': 5}}

    Args:
        module: Module name (e.g., 'rollback', 'game_engine')

    Returns:
        Dict of module settings, empty dict if none configured
    """
    return _config.get('modules', {}).get(module.lower(), {})


def _set_nested(d: Dict, keys: list, value: Any) -> None:
    """Set a value in a nested dict, creating intermediate dicts as needed."""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def _parse_env_value(value: str) -> Any:
    """Parse environment variable value to appropriate type."""
    lower = value.lower()
    if lower in ('true', '1', 'yes', 'on'):
        return True
    if lower in ('false', '0', 'no', 'off'):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _js_log(msg: str) -> None:
    """Log to browser console."""
    print(msg)
    if _is_browser():
        try:
            import platform
            platform.window.console.log(msg)
        except:
            pass


def _format_message(module: str, level: str, msg: str) -> str:
    """Format a log message."""
    return f"[{module}] {level}: {msg}"


def _level_from_string(level_str: str) -> LogLevel:
    """Convert string to LogLevel."""
    mapping = {
        'TRACE': LogLevel.TRACE,
        'DEBUG': LogLevel.DEBUG,
        'INFO': LogLevel.INFO,
        'WARNING': LogLevel.WARNING,
        'WARN': LogLevel.WARNING,
        'ERROR': LogLevel.ERROR,
        'CRITICAL': LogLevel.CRITICAL,
        'OFF': LogLevel.OFF,
    }
    return mapping.get(level_str.upper(), LogLevel.INFO)


def configure_logging(
    level: str = 'INFO',
    modules: Optional[Dict[str, str]] = None,
    lua_calls: bool = False,
    lua_scripts: bool = False,
) -> None:
    """
    Configure the logging system.

    Args:
        level: Default log level for all modules
        modules: Dict of module_name -> level for per-module configuration
        lua_calls: Enable tracing of ams.* API calls from Lua
        lua_scripts: Log which Lua scripts are being executed
    """
    _config['default_level'] = _level_from_string(level)

    if modules:
        for mod, mod_level in modules.items():
            _config['module_levels'][mod] = _level_from_string(mod_level)

    _config['lua_calls'] = lua_calls
    _config['lua_scripts'] = lua_scripts


def _load_env_config() -> None:
    """Load configuration from environment variables.

    Supports two prefixes:
    - AMS_LOG_*: Log levels (AMS_LOG_GAME_ENGINE=DEBUG)
    - AMS_LOGGING_*: Module settings (AMS_LOGGING_ROLLBACK_ENABLED=true)

    Hierarchical module settings use underscore as separator:
        AMS_LOGGING_ROLLBACK_ENABLED=true
        AMS_LOGGING_ROLLBACK_SNAPSHOT_INTERVAL=5

    Maps to:
        modules['rollback'] = {'enabled': True, 'snapshot': {'interval': 5}}
    """
    # Global level
    if 'AMS_LOG_LEVEL' in os.environ:
        _config['default_level'] = _level_from_string(os.environ['AMS_LOG_LEVEL'])

    # Log directory override
    if 'AMS_LOG_DIR' in os.environ:
        _config['log_dir'] = os.environ['AMS_LOG_DIR']

    # Module-specific levels (AMS_LOG_GAME_ENGINE=DEBUG -> game_engine: DEBUG)
    reserved = ('AMS_LOG_LEVEL', 'AMS_LOG_LUA_CALLS', 'AMS_LOG_LUA_SCRIPTS', 'AMS_LOG_DIR')
    for key, value in os.environ.items():
        if key.startswith('AMS_LOG_') and key not in reserved:
            module_name = key[8:].lower()  # Remove 'AMS_LOG_' prefix
            _config['module_levels'][module_name] = _level_from_string(value)

    # Lua tracing
    _config['lua_calls'] = os.environ.get('AMS_LOG_LUA_CALLS', '').lower() in ('1', 'true', 'yes')
    _config['lua_scripts'] = os.environ.get('AMS_LOG_LUA_SCRIPTS', '').lower() in ('1', 'true', 'yes')

    # Hierarchical module settings (AMS_LOGGING_MODULE_KEY_SUBKEY=value)
    for key, value in os.environ.items():
        if key.startswith('AMS_LOGGING_'):
            parts = key[12:].lower().split('_')  # Remove 'AMS_LOGGING_' prefix
            if len(parts) >= 2:
                module = parts[0]
                setting_path = parts[1:]

                if module not in _config['modules']:
                    _config['modules'][module] = {}

                _set_nested(_config['modules'][module], setting_path, _parse_env_value(value))


# Load env config on import
_load_env_config()


class AMSLogger:
    """
    Logger for a specific module.

    Provides standard log levels plus special methods for Lua tracing.
    """

    def __init__(self, module: str):
        self.module = module
        self._module_key = module.lower().replace('.', '_').replace('/', '_')

    @property
    def level(self) -> LogLevel:
        """Get effective log level for this module."""
        if self._module_key in _config['module_levels']:
            return _config['module_levels'][self._module_key]
        return _config['default_level']

    def _should_log(self, level: LogLevel) -> bool:
        """Check if message at given level should be logged."""
        return level >= self.level

    def _log(self, level: LogLevel, level_name: str, msg: str, *args) -> None:
        """Internal log method."""
        if not self._should_log(level):
            return

        # Format message with args if provided
        if args:
            try:
                msg = msg % args
            except:
                msg = f"{msg} {args}"

        formatted = _format_message(self.module, level_name, msg)

        if _is_browser():
            _js_log(formatted)
        else:
            print(formatted)

    def trace(self, msg: str, *args) -> None:
        """Log at TRACE level (very verbose)."""
        self._log(LogLevel.TRACE, 'TRACE', msg, *args)

    def debug(self, msg: str, *args) -> None:
        """Log at DEBUG level."""
        self._log(LogLevel.DEBUG, 'DEBUG', msg, *args)

    def info(self, msg: str, *args) -> None:
        """Log at INFO level."""
        self._log(LogLevel.INFO, 'INFO', msg, *args)

    def warning(self, msg: str, *args) -> None:
        """Log at WARNING level."""
        self._log(LogLevel.WARNING, 'WARN', msg, *args)

    def warn(self, msg: str, *args) -> None:
        """Alias for warning()."""
        self.warning(msg, *args)

    def error(self, msg: str, *args) -> None:
        """Log at ERROR level."""
        self._log(LogLevel.ERROR, 'ERROR', msg, *args)

    def critical(self, msg: str, *args) -> None:
        """Log at CRITICAL level."""
        self._log(LogLevel.CRITICAL, 'CRIT', msg, *args)

    def exception(self, msg: str, *args, exc_info: bool = True) -> None:
        """
        Log an exception with traceback.

        Args:
            msg: Message describing what failed
            exc_info: If True, include current exception traceback
        """
        import traceback

        self._log(LogLevel.ERROR, 'ERROR', msg, *args)

        if exc_info:
            tb = traceback.format_exc()
            if tb and tb.strip() != 'NoneType: None':
                for line in tb.strip().split('\n'):
                    self._log(LogLevel.ERROR, 'TRACE', line)

    def log_traceback(self, exc: Optional[BaseException] = None) -> None:
        """
        Log a traceback for an exception.

        Args:
            exc: Exception to log (uses current exception if None)
        """
        import traceback

        if exc:
            tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        else:
            tb_lines = traceback.format_exc().split('\n')

        for line in tb_lines:
            if line.strip():
                self._log(LogLevel.ERROR, 'TRACE', line)

    # Special Lua tracing methods

    def lua_call(self, fn_name: str, *args) -> None:
        """
        Log an ams.* API call from Lua.

        Only logs if lua_calls tracing is enabled.
        """
        if not _config['lua_calls']:
            return

        args_str = ', '.join(repr(a) for a in args)
        self._log(LogLevel.DEBUG, 'LUA→', f"{fn_name}({args_str})")

    def lua_result(self, fn_name: str, result: Any) -> None:
        """
        Log the result of an ams.* API call.

        Only logs if lua_calls tracing is enabled.
        """
        if not _config['lua_calls']:
            return

        self._log(LogLevel.DEBUG, 'LUA←', f"{fn_name} = {result!r}")

    def lua_script(self, script_type: str, name: str, action: str = 'execute') -> None:
        """
        Log Lua script execution.

        Only logs if lua_scripts tracing is enabled.

        Args:
            script_type: Type of script (behavior, collision_action, generator, etc.)
            name: Name of the script
            action: What's happening (load, execute, on_update, etc.)
        """
        if not _config['lua_scripts']:
            return

        self._log(LogLevel.DEBUG, 'LUA', f"{action} {script_type}/{name}")


@lru_cache(maxsize=64)
def get_logger(module: str) -> AMSLogger:
    """
    Get a logger for the specified module.

    Loggers are cached, so calling get_logger('foo') multiple times
    returns the same logger instance.

    Args:
        module: Module name (e.g., 'game_engine', 'lua_bridge', 'wasmoon')

    Returns:
        AMSLogger instance for the module
    """
    return AMSLogger(module)


# Convenience function for quick debug logging
def log_debug(msg: str, module: str = 'ams') -> None:
    """Quick debug log without getting a logger first."""
    get_logger(module).debug(msg)


# Enable all logging for debugging
def enable_all_logging() -> None:
    """Enable DEBUG level for all modules and all Lua tracing."""
    configure_logging(
        level='DEBUG',
        lua_calls=True,
        lua_scripts=True,
    )


# Disable all logging
def disable_logging() -> None:
    """Disable all logging."""
    _config['default_level'] = LogLevel.OFF
    _config['lua_calls'] = False
    _config['lua_scripts'] = False
