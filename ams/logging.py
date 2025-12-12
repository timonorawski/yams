"""
AMS Unified Logging System

Provides consistent logging across native Python and browser (WASM) environments.
Supports per-module log levels and special tracing for Lua execution.

Usage:
    from ams.logging import get_logger

    log = get_logger('game_engine')
    log.debug("Processing entity")
    log.info("Game started")
    log.lua_call("ams.get_x", entity_id)  # Special Lua tracing

Configuration:
    Environment variables:
        AMS_LOG_LEVEL=DEBUG           # Global default level
        AMS_LOG_GAME_ENGINE=DEBUG     # Module-specific level
        AMS_LOG_LUA_BRIDGE=INFO
        AMS_LOG_LUA_CALLS=1           # Enable Lua API call tracing
        AMS_LOG_LUA_SCRIPTS=1         # Log script execution

    Or programmatically:
        from ams.logging import configure_logging
        configure_logging(level='DEBUG', modules={'lua_bridge': 'INFO'})
"""

import os
import sys
from enum import IntEnum
from typing import Any, Dict, Optional
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


# Global configuration
_config: Dict[str, Any] = {
    'default_level': LogLevel.INFO,
    'module_levels': {},
    'lua_calls': False,      # Trace ams.* API calls from Lua
    'lua_scripts': False,    # Log which scripts are executed
    'output': 'auto',        # 'auto', 'console', 'js'
}


def _is_browser() -> bool:
    """Check if running in browser (Emscripten/WASM)."""
    return sys.platform == 'emscripten'


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
    """Load configuration from environment variables."""
    # Global level
    if 'AMS_LOG_LEVEL' in os.environ:
        _config['default_level'] = _level_from_string(os.environ['AMS_LOG_LEVEL'])

    # Module-specific levels (AMS_LOG_GAME_ENGINE=DEBUG -> game_engine: DEBUG)
    for key, value in os.environ.items():
        if key.startswith('AMS_LOG_') and key not in ('AMS_LOG_LEVEL', 'AMS_LOG_LUA_CALLS', 'AMS_LOG_LUA_SCRIPTS'):
            module_name = key[8:].lower()  # Remove 'AMS_LOG_' prefix
            _config['module_levels'][module_name] = _level_from_string(value)

    # Lua tracing
    _config['lua_calls'] = os.environ.get('AMS_LOG_LUA_CALLS', '').lower() in ('1', 'true', 'yes')
    _config['lua_scripts'] = os.environ.get('AMS_LOG_LUA_SCRIPTS', '').lower() in ('1', 'true', 'yes')


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
