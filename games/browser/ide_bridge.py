"""
IDE Bridge - Python side

Receives project files from the IDE via postMessage and writes them
to the Emscripten virtual filesystem. Triggers game reload after files
are updated.

This is the Python half of the IDE↔Engine communication bridge.
The JS half (ide_bridge.js) receives postMessage and calls these functions.
"""
import json
import logging
import sys
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from ams.content_fs_browser import ContentFSBrowser


class IDELogHandler(logging.Handler):
    """
    Forward Python logs to IDE via postMessage.

    Captures logs from ams.* and games.* loggers and sends them
    to the IDE's LogPanel for real-time display.
    """

    # Map Python log levels to IDE levels
    LEVEL_MAP = {
        logging.DEBUG: 'DEBUG',
        logging.INFO: 'INFO',
        logging.WARNING: 'WARN',
        logging.ERROR: 'ERROR',
        logging.CRITICAL: 'ERROR',
    }

    def __init__(self):
        super().__init__()
        self._enabled = True

    def emit(self, record: logging.LogRecord):
        """Forward log record to IDE."""
        if not self._enabled:
            return

        if sys.platform != "emscripten":
            return

        try:
            import platform as browser_platform

            level = self.LEVEL_MAP.get(record.levelno, 'INFO')
            message = record.getMessage()
            module = record.name

            # Call JavaScript notifyLog
            browser_platform.window.ideBridge.notifyLog(level, message, module)
        except Exception:
            # Silently ignore errors to avoid infinite loops
            pass

    def disable(self):
        """Temporarily disable log forwarding."""
        self._enabled = False

    def enable(self):
        """Re-enable log forwarding."""
        self._enabled = True


# Global log handler instance
_ide_log_handler: Optional[IDELogHandler] = None


def setup_ide_logging():
    """
    Set up log forwarding to IDE.

    Call this after the IDE bridge is initialized to start
    forwarding Python logs to the IDE's LogPanel.
    """
    global _ide_log_handler

    if sys.platform != "emscripten":
        return

    if _ide_log_handler is not None:
        return  # Already set up

    _ide_log_handler = IDELogHandler()
    _ide_log_handler.setLevel(logging.DEBUG)

    # Add handler to relevant loggers
    for logger_name in ['ams', 'games', 'browser']:
        logger = logging.getLogger(logger_name)
        logger.addHandler(_ide_log_handler)

    # Also add to root logger to catch everything
    root_logger = logging.getLogger()
    root_logger.addHandler(_ide_log_handler)

    print("[IDEBridge] Log forwarding to IDE enabled")


# Global reference to the bridge instance
_bridge_instance: Optional['IDEBridge'] = None


class IDEBridge:
    """
    Handles IDE → Engine communication.

    Receives files from Monaco editor, writes to ContentFS,
    and triggers game reload.
    """

    def __init__(self, content_fs: 'ContentFSBrowser', reload_callback: Optional[Callable] = None):
        """
        Initialize the IDE bridge.

        Args:
            content_fs: ContentFS instance for file operations
            reload_callback: Function to call after files are updated (triggers game reload)
        """
        self.content_fs = content_fs
        self.reload_callback = reload_callback

        # Generate unique project slug to avoid collisions
        import time
        import random
        timestamp = int(time.time() * 1000) % 100000
        rand_suffix = random.randint(100, 999)
        self._project_path = f'ide_project_{timestamp}_{rand_suffix}'

        # Ensure project directory exists
        import os
        project_dir = content_fs._resolve_path(self._project_path)
        os.makedirs(project_dir, exist_ok=True)

        self._log(f"IDEBridge initialized, project path: {project_dir}")

    def _log(self, msg: str):
        """Log to console."""
        print(f"[IDEBridge] {msg}")
        if sys.platform == "emscripten":
            try:
                import platform as browser_platform
                browser_platform.window.console.log(f"[IDEBridge] {msg}")
            except:
                pass

    def receive_files(self, files_json: str) -> dict:
        """
        Receive project files from IDE.

        Args:
            files_json: JSON string with file paths and contents
                        Format: {"path/to/file.json": {...}, "lua/behavior.lua": "..."}

        Returns:
            Status dict: {"success": bool, "files_written": int, "error": str|None}
        """
        try:
            files = json.loads(files_json) if isinstance(files_json, str) else files_json
            files_written = 0

            for path, content in files.items():
                # Prepend project path
                full_path = f"{self._project_path}/{path}"
                self._log(f"Writing file: {path} -> {full_path}")

                # Convert dict/list to JSON string for storage
                if isinstance(content, (dict, list)):
                    content = json.dumps(content, indent=2)
                    self._log(f"  Content type: dict/list, converted to JSON")
                else:
                    self._log(f"  Content type: {type(content).__name__}, length: {len(content) if content else 0}")

                self.content_fs.writetext(full_path, content)
                self._log(f"  Write complete")
                files_written += 1

            self._log(f"Received {files_written} files")
            return {"success": True, "files_written": files_written, "error": None}

        except Exception as e:
            self._log(f"Error receiving files: {e}")
            return {"success": False, "files_written": 0, "error": str(e)}

    def trigger_reload(self) -> dict:
        """
        Trigger game reload after files are updated.

        Returns:
            Status dict: {"success": bool, "error": str|None}
        """
        try:
            if self.reload_callback:
                self.reload_callback()
                self._log("Reload triggered")
                return {"success": True, "error": None}
            else:
                self._log("No reload callback registered")
                return {"success": False, "error": "No reload callback registered"}
        except Exception as e:
            self._log(f"Error during reload: {e}")
            return {"success": False, "error": str(e)}

    def get_project_path(self) -> str:
        """Get the path where IDE project files are stored."""
        return self.content_fs._resolve_path(self._project_path)


def init_bridge(content_fs: 'ContentFSBrowser', reload_callback: Optional[Callable] = None) -> IDEBridge:
    """
    Initialize the global IDE bridge instance.

    Called during game runtime startup to set up IDE communication.
    """
    global _bridge_instance
    _bridge_instance = IDEBridge(content_fs, reload_callback)
    return _bridge_instance


def get_bridge() -> Optional[IDEBridge]:
    """Get the global IDE bridge instance."""
    return _bridge_instance


# Functions exposed to JavaScript via ide_bridge.js

def js_receive_files(files_json: str) -> str:
    """
    Called from JavaScript to receive files.

    Args:
        files_json: JSON string of files

    Returns:
        JSON string with status
    """
    if _bridge_instance is None:
        return json.dumps({"success": False, "error": "Bridge not initialized"})

    result = _bridge_instance.receive_files(files_json)
    return json.dumps(result)


def js_trigger_reload() -> str:
    """
    Called from JavaScript to trigger reload.

    Returns:
        JSON string with status
    """
    if _bridge_instance is None:
        return json.dumps({"success": False, "error": "Bridge not initialized"})

    result = _bridge_instance.trigger_reload()
    return json.dumps(result)


def js_get_project_path() -> str:
    """
    Called from JavaScript to get project path.

    Returns:
        Project path string
    """
    if _bridge_instance is None:
        return ""
    return _bridge_instance.get_project_path()
