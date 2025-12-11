"""
Game Registry - Auto-discovery and management of AMS games.

Games are automatically discovered by scanning the games/ directory for
subdirectories containing a game_mode.py with a class inheriting from BaseGame.

Game metadata and CLI arguments are retrieved from the game class itself
(via BaseGame class attributes). Falls back to game_info.py module-level
variables for backward compatibility with games not yet migrated.

Usage:
    from games.registry import GameRegistry

    registry = GameRegistry()
    available = registry.list_games()  # ['balloonpop', 'duckhunt', ...]

    # Get game info including CLI arguments
    info = registry.get_game_info('containment')
    args = registry.get_game_arguments('containment')

    # Create game instance
    game = registry.create_game('balloonpop', width=1920, height=1080)
"""

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from ams.session import AMSSession
    from ams.games.base_game import BaseGame
    from ams.content_fs import ContentFS


@dataclass
class GameInfo:
    """Information about a registered game."""
    name: str
    slug: str  # lowercase identifier (directory name)
    description: str
    version: str
    author: str
    module_path: str  # e.g., 'games.BalloonPop'

    # CLI arguments (from game class or module)
    arguments: List[Dict[str, Any]] = field(default_factory=list)

    # Optional features
    has_config: bool = False
    config_file: Optional[str] = None


class GameRegistry:
    """
    Registry for auto-discovering and managing AMS games.

    Scans the games/ directory for valid game packages and provides
    a unified interface for creating game instances.

    Discovery works by:
    1. Looking for game_mode.py in each game directory
    2. Finding classes that inherit from BaseGame
    3. Reading metadata from class attributes (NAME, DESCRIPTION, etc.)
    4. Falling back to game_info.py module variables if no BaseGame found
    """

    def __init__(self, content_fs: 'ContentFS'):
        """
        Initialize the game registry.

        Args:
            content_fs: ContentFS for layered content access.
                       - Python games: core_dir only (security)
                       - YAML games: all layers (Lua is sandboxed)
        """
        self._content_fs = content_fs
        self._games: Dict[str, GameInfo] = {}
        self._game_classes: Dict[str, Type['BaseGame']] = {}
        self._discover_games()

    def _discover_games(self) -> None:
        """Discover games from appropriate sources.

        Python games (game_mode.py): Only from core repo (security - arbitrary code)
        YAML games (game.yaml): From all ContentFS layers (Lua is sandboxed)
        """
        skip_dirs = {'base', 'common', '__pycache__'}

        # Track discovered slugs to avoid duplicates
        discovered_slugs: set[str] = set()

        # 1. SECURITY: Python games only from core repo
        games_dir = self._content_fs.core_dir / 'games'
        if games_dir.exists():
            for game_dir in games_dir.iterdir():
                if not game_dir.is_dir():
                    continue
                if game_dir.name.startswith('_') or game_dir.name.startswith('.'):
                    continue
                if game_dir.name.lower() in skip_dirs:
                    continue

                slug = game_dir.name.lower()
                has_game_mode = (game_dir / 'game_mode.py').exists()
                has_game_info = (game_dir / 'game_info.py').exists()

                if has_game_mode or has_game_info:
                    self._register_game(game_dir)
                    discovered_slugs.add(slug)
                elif (game_dir / 'game.yaml').exists():
                    # YAML game in core repo
                    self._register_yaml_game(game_dir)
                    discovered_slugs.add(slug)

        # 2. YAML games from all ContentFS layers (Lua is sandboxed, safe)
        if self._content_fs.exists('games'):
            for item_name in self._content_fs.listdir('games'):
                if item_name.startswith('_') or item_name.startswith('.'):
                    continue
                if item_name.lower() in skip_dirs:
                    continue
                if item_name.lower() in discovered_slugs:
                    continue  # Already registered from core

                game_path = f'games/{item_name}'
                if not self._content_fs.isdir(game_path):
                    continue

                # Only YAML games from non-core layers (Python would be security risk)
                if self._content_fs.exists(f'{game_path}/game.yaml'):
                    try:
                        real_game_dir = Path(self._content_fs.getsyspath(game_path))
                        self._register_yaml_game(real_game_dir)
                    except Exception:
                        continue

    def _register_game(self, game_dir: Path) -> None:
        """
        Register a game from its directory.

        Attempts to find a BaseGame subclass in game_mode.py first,
        falling back to game_info.py module variables.

        Args:
            game_dir: Path to game directory
        """
        slug = game_dir.name.lower()
        module_path = f"games.{game_dir.name}"

        try:
            # Try to find BaseGame subclass in game_mode.py
            game_class = self._find_game_class(game_dir, module_path)

            if game_class is not None:
                # Use class attributes (preferred method)
                name = getattr(game_class, 'NAME', game_dir.name)
                description = getattr(game_class, 'DESCRIPTION', '')
                version = getattr(game_class, 'VERSION', '1.0.0')
                author = getattr(game_class, 'AUTHOR', 'Unknown')

                # Get arguments via class method if available
                if hasattr(game_class, 'get_arguments'):
                    arguments = game_class.get_arguments()
                else:
                    arguments = getattr(game_class, 'ARGUMENTS', [])

                self._game_classes[slug] = game_class

            else:
                # Fall back to game_info.py module variables
                game_info_module = self._load_game_info(game_dir, module_path)
                if game_info_module is None:
                    return

                name = getattr(game_info_module, 'NAME', game_dir.name)
                description = getattr(game_info_module, 'DESCRIPTION', '')
                version = getattr(game_info_module, 'VERSION', '1.0.0')
                author = getattr(game_info_module, 'AUTHOR', 'Unknown')
                arguments = getattr(game_info_module, 'ARGUMENTS', [])

            # Check for config files
            has_config = (game_dir / '.env').exists() or (game_dir / 'config.py').exists()
            config_file = '.env' if (game_dir / '.env').exists() else None

            self._games[slug] = GameInfo(
                name=name,
                slug=slug,
                description=description,
                version=version,
                author=author,
                module_path=module_path,
                arguments=arguments,
                has_config=has_config,
                config_file=config_file,
            )

        except Exception as e:
            # Skip games that fail to load
            print(f"Warning: Failed to load game from {game_dir}: {e}")

    def _register_yaml_game(self, game_dir: Path) -> None:
        """
        Register a YAML-only game (no Python boilerplate required).

        Uses GameEngine.from_yaml() factory to create a dynamic game class
        from the game.yaml definition.

        Args:
            game_dir: Path to game directory containing game.yaml
        """
        slug = game_dir.name.lower()
        yaml_path = game_dir / 'game.yaml'

        try:
            # Use GameEngine factory to create class from YAML
            from ams.games.game_engine import GameEngine
            game_class = GameEngine.from_yaml(yaml_path)

            # Extract metadata from class (set by factory)
            name = getattr(game_class, 'NAME', game_dir.name)
            description = getattr(game_class, 'DESCRIPTION', '')
            version = getattr(game_class, 'VERSION', '1.0.0')
            author = getattr(game_class, 'AUTHOR', 'Unknown')
            arguments = getattr(game_class, 'ARGUMENTS', [])

            self._game_classes[slug] = game_class

            # Check for config files
            has_config = (game_dir / '.env').exists() or (game_dir / 'config.py').exists()
            config_file = '.env' if (game_dir / '.env').exists() else None

            self._games[slug] = GameInfo(
                name=name,
                slug=slug,
                description=description,
                version=version,
                author=author,
                module_path=f"games.{game_dir.name}",  # Virtual module path
                arguments=arguments,
                has_config=has_config,
                config_file=config_file,
            )

        except Exception as e:
            print(f"Warning: Failed to load YAML game from {game_dir}: {e}")

    def _find_game_class(self, game_dir: Path, module_path: str) -> Optional[Type['BaseGame']]:
        """
        Find a BaseGame subclass in the game's game_mode.py.

        Args:
            game_dir: Path to game directory
            module_path: Module path (e.g., 'games.BalloonPop')

        Returns:
            The game class, or None if not found
        """
        game_mode_path = game_dir / 'game_mode.py'
        if not game_mode_path.exists():
            return None

        try:
            # Import BaseGame for isinstance checking
            from ams.games.base_game import BaseGame

            # Import the game_mode module
            spec = importlib.util.spec_from_file_location(
                f"{module_path}.game_mode",
                game_mode_path
            )
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{module_path}.game_mode"] = module
            spec.loader.exec_module(module)

            # Find classes that inherit from BaseGame
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Skip imported classes (only want classes defined in this module)
                if obj.__module__ != module.__name__:
                    continue

                # Check if it inherits from BaseGame (but isn't BaseGame itself)
                if issubclass(obj, BaseGame) and obj is not BaseGame:
                    return obj

        except Exception:
            # Silently fail - will fall back to game_info.py
            pass

        return None

    def _load_game_info(self, game_dir: Path, module_path: str):
        """
        Load the game_info.py module for a game.

        Args:
            game_dir: Path to game directory
            module_path: Module path

        Returns:
            The module, or None if not found
        """
        game_info_path = game_dir / 'game_info.py'
        if not game_info_path.exists():
            return None

        try:
            spec = importlib.util.spec_from_file_location(
                f"{module_path}.game_info",
                game_info_path
            )
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{module_path}.game_info"] = module
            spec.loader.exec_module(module)
            return module

        except Exception:
            return None

    def list_games(self) -> List[str]:
        """
        Get list of available game slugs.

        Returns:
            List of game slug identifiers
        """
        return sorted(self._games.keys())

    def get_game_info(self, slug: str) -> Optional[GameInfo]:
        """
        Get information about a specific game.

        Args:
            slug: Game identifier

        Returns:
            GameInfo or None if not found
        """
        return self._games.get(slug.lower())

    def get_game_arguments(self, slug: str) -> List[Dict[str, Any]]:
        """
        Get CLI arguments for a specific game.

        Args:
            slug: Game identifier

        Returns:
            List of argument definitions for argparse
        """
        info = self._games.get(slug.lower())
        if info is None:
            return []
        return info.arguments

    def get_game_class(self, slug: str) -> Optional[Type['BaseGame']]:
        """
        Get the game class for a specific game.

        Args:
            slug: Game identifier

        Returns:
            Game class or None if not found/cached
        """
        return self._game_classes.get(slug.lower())

    def get_all_games(self) -> Dict[str, GameInfo]:
        """
        Get all registered games.

        Returns:
            Dict mapping slug to GameInfo
        """
        return self._games.copy()

    def create_game(
        self,
        slug: str,
        width: int,
        height: int,
        **kwargs
    ) -> Any:
        """
        Create a game mode instance.

        Uses the cached game class if available, otherwise falls back
        to game_info.py's get_game_mode() function.

        Args:
            slug: Game identifier
            width: Display width
            height: Display height
            **kwargs: Additional game-specific arguments

        Returns:
            Game mode instance

        Raises:
            ValueError: If game not found
        """
        info = self._games.get(slug.lower())
        if info is None:
            available = ', '.join(self.list_games())
            raise ValueError(f"Unknown game: {slug}. Available: {available}")

        # Update screen size in config if available
        try:
            config_module = importlib.import_module(f"{info.module_path}.config")
            config_module.SCREEN_WIDTH = width
            config_module.SCREEN_HEIGHT = height
        except (ImportError, AttributeError):
            pass

        # Inject ContentFS for layered content access
        if 'content_fs' not in kwargs:
            kwargs['content_fs'] = self._content_fs

        # Prefer using cached game class directly
        game_class = self._game_classes.get(slug.lower())
        if game_class is not None:
            return game_class(**kwargs)

        # Fall back to game_info.py's get_game_mode()
        game_info_module = importlib.import_module(f"{info.module_path}.game_info")
        get_game_mode = getattr(game_info_module, 'get_game_mode', None)
        if get_game_mode is None:
            raise ValueError(f"Game {slug} does not define get_game_mode()")

        return get_game_mode(**kwargs)

    def create_input_manager(
        self,
        slug: str,
        ams_session: Optional['AMSSession'],
        width: int,
        height: int
    ) -> Any:
        """
        Create an InputManager for a game.

        If ams_session is provided, creates AMSInputAdapter.
        Otherwise creates MouseInputSource for standalone mode.

        Args:
            slug: Game identifier
            ams_session: AMS session (None for standalone)
            width: Display width
            height: Display height

        Returns:
            InputManager instance
        """
        info = self._games.get(slug.lower())
        if info is None:
            raise ValueError(f"Unknown game: {slug}")

        # Try game-specific input module, fall back to common input
        try:
            input_manager_module = importlib.import_module(f"{info.module_path}.input.input_manager")
        except ModuleNotFoundError:
            # Use common input module (for GameEngine-based games)
            input_manager_module = importlib.import_module("ams.games.input.input_manager")
        InputManager = input_manager_module.InputManager

        if ams_session is not None:
            # AMS mode - use adapter
            from ams.game_adapter import AMSInputAdapter
            source = AMSInputAdapter(ams_session, width, height)
        else:
            # Standalone mode - use mouse
            try:
                mouse_module = importlib.import_module(f"{info.module_path}.input.sources.mouse")
            except ModuleNotFoundError:
                # Use common mouse input source
                mouse_module = importlib.import_module("ams.games.input.sources.mouse")
            source = mouse_module.MouseInputSource()

        return InputManager(source)

    def get_game_state_enum(self, slug: str) -> Any:
        """
        Get the GameState enum for a game.

        Args:
            slug: Game identifier

        Returns:
            GameState enum class
        """
        info = self._games.get(slug.lower())
        if info is None:
            raise ValueError(f"Unknown game: {slug}")

        # All games should use the common GameState
        from ams.games import GameState
        return GameState


# Singleton instance for convenience
_registry: Optional[GameRegistry] = None


def get_registry(content_fs: Optional['ContentFS'] = None) -> GameRegistry:
    """Get the global game registry instance.

    Args:
        content_fs: ContentFS instance. Required on first call to initialize
                   the registry. Subsequent calls can omit it.

    Returns:
        The global GameRegistry instance.

    Raises:
        ValueError: If called without content_fs when registry not initialized.
    """
    global _registry
    if _registry is None:
        if content_fs is None:
            raise ValueError("ContentFS required to initialize registry")
        _registry = GameRegistry(content_fs)
    return _registry
