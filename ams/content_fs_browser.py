"""
Browser-compatible ContentFS using Emscripten's virtual filesystem.

In browser, files are loaded into Emscripten's MEMFS during build.
This shim provides the same interface as ContentFS but reads from
the Emscripten virtual filesystem.

The layering is simplified for browser: all content is pre-bundled
at build time into a flat structure under /game/.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Iterator


class ContentFSBrowser:
    """Browser-compatible ContentFS shim over Emscripten FS.

    Provides the same interface as ContentFS but reads from
    Emscripten's virtual filesystem (MEMFS).
    """

    PRIORITY_ENGINE = 5
    PRIORITY_GAME = 50
    PRIORITY_USER = 100

    def __init__(self, base_path: str = '/game'):
        """Initialize with base path in Emscripten FS.

        Args:
            base_path: Root path where game content is mounted
        """
        self._base = base_path
        self._core_dir = Path(base_path)
        self._game_layer: Optional[str] = None

    @property
    def core_dir(self) -> Path:
        """Compatibility with native ContentFS."""
        return self._core_dir

    def add_game_layer(self, game_path) -> bool:
        """Set the game layer path.

        In browser, game content is already bundled, but we track
        the game path for relative lookups.
        """
        game_str = str(game_path)
        # Convert absolute path to relative if needed
        if game_str.startswith(str(self._base)):
            self._game_layer = game_str
        else:
            self._game_layer = f"{self._base}/{game_str}"
        return True

    def exists(self, path: str) -> bool:
        """Check if path exists in Emscripten FS."""
        full_path = self._resolve_path(path)
        return os.path.exists(full_path)

    def isdir(self, path: str) -> bool:
        """Check if path is a directory."""
        full_path = self._resolve_path(path)
        return os.path.isdir(full_path)

    def isfile(self, path: str) -> bool:
        """Check if path is a file."""
        full_path = self._resolve_path(path)
        return os.path.isfile(full_path)

    def readtext(self, path: str, encoding: str = 'utf-8') -> str:
        """Read text file from Emscripten FS."""
        full_path = self._resolve_path(path)
        with open(full_path, 'r', encoding=encoding) as f:
            return f.read()

    def readbytes(self, path: str) -> bytes:
        """Read binary file from Emscripten FS."""
        full_path = self._resolve_path(path)
        with open(full_path, 'rb') as f:
            return f.read()

    def listdir(self, path: str) -> list[str]:
        """List directory contents from Emscripten FS."""
        full_path = self._resolve_path(path)
        if os.path.isdir(full_path):
            return os.listdir(full_path)
        return []

    def getsyspath(self, path: str) -> str:
        """Return Emscripten virtual path (for pygame.image.load etc)."""
        return self._resolve_path(path)

    def open(self, path: str, mode: str = 'r'):
        """Open a file from Emscripten FS."""
        full_path = self._resolve_path(path)
        return open(full_path, mode)

    def walk_files(self, path: str = '/', filter_glob: list[str] | None = None) -> Iterator[str]:
        """Walk files in directory tree."""
        full_path = self._resolve_path(path)
        for root, dirs, files in os.walk(full_path):
            for fname in files:
                if filter_glob:
                    # Simple glob matching
                    import fnmatch
                    if not any(fnmatch.fnmatch(fname, pat) for pat in filter_glob):
                        continue
                # Return path relative to base
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, self._base)
                yield rel_path

    def get_layer_source(self, path: str) -> Optional[str]:
        """Get which layer a file comes from (for debugging)."""
        # In browser, everything is from 'bundle' layer
        if self.exists(path):
            return 'bundle'
        return None

    def get_layers_info(self) -> list[tuple[str, int, Path]]:
        """Get information about layers (for debugging)."""
        return [('bundle', 0, self._core_dir)]

    def describe_layers(self) -> str:
        """Get human-readable description of layers."""
        return f"Browser ContentFS (base: {self._base})"

    def _resolve_path(self, path: str) -> str:
        """Resolve a content path to full Emscripten FS path.

        Tries game layer first, then base path.
        """
        # If path is already absolute, use it directly
        if path.startswith('/'):
            return path

        # Try game layer first if set
        if self._game_layer:
            game_path = f"{self._game_layer}/{path}"
            if os.path.exists(game_path):
                return game_path

        # Fall back to base path
        return f"{self._base}/{path}"


def get_content_fs(core_dir=None):
    """Factory function to get appropriate ContentFS for current platform.

    In browser (Emscripten), returns ContentFSBrowser.
    In native Python, returns the full ContentFS.
    """
    if sys.platform == "emscripten":
        # In pygbag, working directory is where main.py lives
        return ContentFSBrowser(base_path=os.getcwd())
    else:
        from ams.content_fs import ContentFS
        from pathlib import Path
        return ContentFS(core_dir or Path.cwd())
