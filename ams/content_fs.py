"""Layered content filesystem using PyFilesystem2 MultiFS.

Provides unified file access across multiple content layers:
- Core content (built-in games, behaviors)
- Overlay directories (team/shared content)
- User directory (personal customizations)

Higher priority layers shadow lower priority files, enabling users to
override core assets, levels, and behaviors without modifying the
original files.

Environment variables:
- AMS_DATA_DIR: Override default user data directory
- AMS_OVERLAY_DIRS: Colon-separated list of overlay directories

WASM Compatibility Note:
    This implementation uses PyFilesystem2's MultiFS which is not compatible
    with Emscripten/WebAssembly builds. For browser deployment via pygbag,
    an alternative implementation will be needed that uses Emscripten's
    virtual filesystem (MEMFS/IDBFS) directly. The ContentFS interface
    should remain stable - only the backend implementation changes.
"""

from pathlib import Path
from typing import Optional, Iterator
import os
import sys

from fs.multifs import MultiFS
from fs.osfs import OSFS
from fs.errors import ResourceNotFound


def get_user_data_dir() -> Path:
    """Get XDG-compliant user data directory.

    Returns platform-appropriate default:
    - macOS: ~/Library/Application Support/AMS
    - Windows: %APPDATA%/AMS
    - Linux/BSD: ~/.local/share/ams (XDG_DATA_HOME)
    """
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'AMS'
    elif sys.platform == 'win32':
        return Path(os.environ.get('APPDATA', str(Path.home()))) / 'AMS'
    else:
        xdg_data = os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))
        return Path(xdg_data) / 'ams'


class ContentFS:
    """Layered content filesystem for AMS.

    Provides unified file access across:
    - Core content (built-in games, behaviors)
    - Overlay directories (team/shared content)
    - User directory (personal customizations)

    Higher priority layers shadow lower priority files.

    Example usage:
        content_fs = ContentFS(Path('/path/to/repo'))

        # Check if file exists in any layer
        if content_fs.exists('games/DuckHunt/game.yaml'):
            yaml_text = content_fs.readtext('games/DuckHunt/game.yaml')

        # Get real filesystem path (for pygame.image.load)
        sprite_path = content_fs.getsyspath('games/DuckHunt/assets/sprites.png')
        surface = pygame.image.load(sprite_path)

        # Debug: see which layer a file comes from
        source = content_fs.get_layer_source('games/DuckHunt/assets/sprites.png')
        # Returns 'user' if user has overridden it, 'core' otherwise
    """

    PRIORITY_CORE = 0
    PRIORITY_ENGINE = 5       # Engine lua scripts (ams/games/game_engine/)
    PRIORITY_OVERLAY_BASE = 10
    PRIORITY_GAME = 50        # Game-specific content (games/{slug}/)
    PRIORITY_USER = 100

    def __init__(self, core_dir: Path, add_user_layer: bool = True):
        """Initialize with core content directory.

        Args:
            core_dir: Path to core content (repo root containing /games/, /ams/behaviors/)
            add_user_layer: Whether to add user data directory layer (default True)
        """
        self._multi_fs = MultiFS()
        self._core_dir = core_dir
        self._layers: dict[str, tuple[Path, int]] = {}  # name -> (path, priority) for debugging

        # Add core layer (lowest priority)
        if core_dir.exists():
            self._multi_fs.add_fs('core', OSFS(str(core_dir)), priority=self.PRIORITY_CORE)
            self._layers['core'] = (core_dir, self.PRIORITY_CORE)

        # Add engine layer for lua scripts (lua/behavior/, lua/collision_action/, etc.)
        engine_dir = core_dir / 'ams' / 'games' / 'game_engine'
        if engine_dir.exists():
            self._multi_fs.add_fs('engine', OSFS(str(engine_dir)), priority=self.PRIORITY_ENGINE)
            self._layers['engine'] = (engine_dir, self.PRIORITY_ENGINE)

        # Add overlay layers from environment
        self._add_overlay_layers()

        # Add user layer (highest priority)
        if add_user_layer:
            self._add_user_layer()

    def _add_overlay_layers(self) -> None:
        """Add overlay directories from AMS_OVERLAY_DIRS environment variable.

        Format: colon-separated paths (e.g., /path/one:/path/two)
        Each overlay gets incrementing priority (10, 11, 12, ...)
        """
        overlay_dirs = os.environ.get('AMS_OVERLAY_DIRS', '')
        if not overlay_dirs:
            return

        for i, overlay_path in enumerate(overlay_dirs.split(':')):
            overlay_path = overlay_path.strip()
            if overlay_path:
                path = Path(overlay_path).expanduser()
                if path.exists():
                    priority = self.PRIORITY_OVERLAY_BASE + i
                    name = f'overlay_{i}'
                    self._multi_fs.add_fs(name, OSFS(str(path)), priority=priority)
                    self._layers[name] = (path, priority)

    def _add_user_layer(self) -> None:
        """Add user data directory layer (highest priority).

        Uses AMS_DATA_DIR if set, otherwise XDG-compliant default.
        Only added if the directory exists.
        """
        user_dir = os.environ.get('AMS_DATA_DIR')
        if user_dir:
            user_path = Path(user_dir).expanduser()
        else:
            user_path = get_user_data_dir()

        if user_path.exists():
            self._multi_fs.add_fs('user', OSFS(str(user_path)), priority=self.PRIORITY_USER)
            self._layers['user'] = (user_path, self.PRIORITY_USER)

    @property
    def fs(self) -> MultiFS:
        """Get the underlying MultiFS for direct operations."""
        return self._multi_fs

    @property
    def core_dir(self) -> Path:
        """Get the core content directory."""
        return self._core_dir

    def add_game_layer(self, game_path: Path) -> bool:
        """Add a game directory as a content layer.

        Game layers have higher priority than engine/core but lower than user.
        This allows games to override engine lua scripts (lua/behavior/, etc.)
        and provide game-specific assets.

        Args:
            game_path: Path to game directory (e.g., games/Breakout/)

        Returns:
            True if layer was added, False if path doesn't exist
        """
        if not game_path.exists():
            return False

        # Remove existing game layer if present
        if 'game' in self._layers:
            self._multi_fs.remove_fs('game')

        self._multi_fs.add_fs('game', OSFS(str(game_path)), priority=self.PRIORITY_GAME)
        self._layers['game'] = (game_path, self.PRIORITY_GAME)
        return True

    def exists(self, path: str) -> bool:
        """Check if a path exists in any layer.

        Args:
            path: Virtual path (e.g., 'games/DuckHunt/game.yaml')

        Returns:
            True if file/directory exists in any layer
        """
        return self._multi_fs.exists(path)

    def isdir(self, path: str) -> bool:
        """Check if path is a directory in any layer."""
        try:
            return self._multi_fs.isdir(path)
        except ResourceNotFound:
            return False

    def isfile(self, path: str) -> bool:
        """Check if path is a file in any layer."""
        try:
            return self._multi_fs.isfile(path)
        except ResourceNotFound:
            return False

    def open(self, path: str, mode: str = 'r'):
        """Open a file from the highest-priority layer.

        Args:
            path: Virtual path to file
            mode: File mode ('r', 'rb', etc.)

        Returns:
            File-like object

        Raises:
            fs.errors.ResourceNotFound: If file doesn't exist in any layer
        """
        return self._multi_fs.open(path, mode)

    def readbytes(self, path: str) -> bytes:
        """Read binary content from highest-priority layer.

        Args:
            path: Virtual path to file

        Returns:
            File contents as bytes

        Raises:
            fs.errors.ResourceNotFound: If file doesn't exist
        """
        return self._multi_fs.readbytes(path)

    def readtext(self, path: str, encoding: str = 'utf-8') -> str:
        """Read text content from highest-priority layer.

        Args:
            path: Virtual path to file
            encoding: Text encoding (default UTF-8)

        Returns:
            File contents as string

        Raises:
            fs.errors.ResourceNotFound: If file doesn't exist
        """
        return self._multi_fs.readtext(path, encoding=encoding)

    def listdir(self, path: str) -> list[str]:
        """List directory contents (merged from all layers).

        Args:
            path: Virtual path to directory

        Returns:
            List of file/directory names (deduplicated across layers)

        Raises:
            fs.errors.ResourceNotFound: If directory doesn't exist
        """
        return self._multi_fs.listdir(path)

    def getsyspath(self, path: str) -> str:
        """Get real filesystem path for a file.

        This is needed for libraries like pygame that require real
        filesystem paths (e.g., pygame.image.load needs a real path,
        not a virtual filesystem path).

        Args:
            path: Virtual path to file

        Returns:
            Absolute filesystem path to the file

        Raises:
            fs.errors.ResourceNotFound: If file doesn't exist
            fs.errors.NoSysPath: If file can't be represented as system path
        """
        return self._multi_fs.getsyspath(path)

    def walk_files(self, path: str = '/', filter_glob: list[str] | None = None) -> Iterator[str]:
        """Walk files across all layers.

        Args:
            path: Virtual path to start walking from
            filter_glob: Optional list of glob patterns (e.g., ['*.lua'])

        Yields:
            Virtual paths to files matching filter
        """
        return self._multi_fs.walk.files(path, filter=filter_glob)

    def get_layer_source(self, path: str) -> Optional[str]:
        """Get which layer a file comes from (for debugging).

        Checks layers in priority order (highest first) to find
        where the file would be loaded from.

        Args:
            path: Virtual path to file

        Returns:
            Layer name ('user', 'overlay_0', 'core', etc.) or None if not found
        """
        # iterate_fs returns in priority order (highest first)
        for name, fs in self._multi_fs.iterate_fs():
            if fs.exists(path):
                return name
        return None

    def get_layers_info(self) -> list[tuple[str, int, Path]]:
        """Get information about all layers for debugging.

        Returns:
            List of (name, priority, path) tuples, sorted by priority (highest first)
        """
        result = []
        for name, (path, priority) in self._layers.items():
            result.append((name, priority, path))
        return sorted(result, key=lambda x: x[1], reverse=True)

    def describe_layers(self) -> str:
        """Get human-readable description of content layers.

        Returns:
            Multi-line string describing all layers
        """
        lines = ["Content Layers (highest priority first):"]
        for name, priority, path in self.get_layers_info():
            lines.append(f"  [{priority:3d}] {name}: {path}")
        return '\n'.join(lines)
