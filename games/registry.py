"""
Game Registry - Auto-discovery and management of AMS games.

Games are automatically discovered by scanning the games/ directory for
subdirectories containing a game_info.py file that defines the game's
metadata and entry points.

Each game must provide:
- game_info.py with NAME, DESCRIPTION, and get_game_mode() function
- A game mode class that implements handle_input(), update(), render()
- input/ directory with InputManager abstraction (can be copied from template)

Usage:
    from games.registry import GameRegistry

    registry = GameRegistry()
    available = registry.list_games()  # ['balloonpop', 'duckhunt', ...]

    game_mode = registry.create_game('balloonpop', width=1920, height=1080)
    input_manager = registry.create_input_manager('balloonpop', ams_session, width, height)
"""

import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ams.session import AMSSession


@dataclass
class GameInfo:
    """Information about a registered game."""
    name: str
    slug: str  # lowercase identifier (directory name)
    description: str
    version: str
    author: str
    module_path: str  # e.g., 'games.BalloonPop'

    # Optional features
    has_config: bool = False
    config_file: Optional[str] = None


class GameRegistry:
    """
    Registry for auto-discovering and managing AMS games.

    Scans the games/ directory for valid game packages and provides
    a unified interface for creating game instances.
    """

    def __init__(self, games_dir: Optional[Path] = None):
        """
        Initialize the game registry.

        Args:
            games_dir: Path to games directory. Defaults to ./games/
        """
        if games_dir is None:
            games_dir = Path(__file__).parent
        self.games_dir = Path(games_dir)
        self._games: Dict[str, GameInfo] = {}
        self._discover_games()

    def _discover_games(self) -> None:
        """Scan games directory and register valid games."""
        if not self.games_dir.exists():
            return

        for item in self.games_dir.iterdir():
            if not item.is_dir():
                continue
            if item.name.startswith('_') or item.name.startswith('.'):
                continue
            if item.name in ('base', '__pycache__'):
                continue

            # Check for game_info.py
            game_info_path = item / 'game_info.py'
            if game_info_path.exists():
                self._register_game(item)

    def _register_game(self, game_dir: Path) -> None:
        """
        Register a game from its directory.

        Args:
            game_dir: Path to game directory
        """
        slug = game_dir.name.lower()
        module_path = f"games.{game_dir.name}"

        try:
            # Import game_info module
            spec = importlib.util.spec_from_file_location(
                f"{module_path}.game_info",
                game_dir / "game_info.py"
            )
            if spec is None or spec.loader is None:
                return

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{module_path}.game_info"] = module
            spec.loader.exec_module(module)

            # Extract game info
            name = getattr(module, 'NAME', game_dir.name)
            description = getattr(module, 'DESCRIPTION', '')
            version = getattr(module, 'VERSION', '1.0.0')
            author = getattr(module, 'AUTHOR', 'Unknown')

            # Check for config
            has_config = (game_dir / '.env').exists() or (game_dir / 'config.py').exists()
            config_file = '.env' if (game_dir / '.env').exists() else None

            self._games[slug] = GameInfo(
                name=name,
                slug=slug,
                description=description,
                version=version,
                author=author,
                module_path=module_path,
                has_config=has_config,
                config_file=config_file,
            )

        except Exception as e:
            # Skip games that fail to load
            print(f"Warning: Failed to load game from {game_dir}: {e}")

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

        # Import the game's game_info module
        game_info_module = importlib.import_module(f"{info.module_path}.game_info")

        # Update screen size in config if available
        try:
            config_module = importlib.import_module(f"{info.module_path}.config")
            config_module.SCREEN_WIDTH = width
            config_module.SCREEN_HEIGHT = height
        except (ImportError, AttributeError):
            pass

        # Get the game mode factory
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

        # Import game's input module
        input_manager_module = importlib.import_module(f"{info.module_path}.input.input_manager")
        InputManager = input_manager_module.InputManager

        if ams_session is not None:
            # AMS mode - use adapter
            from ams.game_adapter import AMSInputAdapter
            source = AMSInputAdapter(ams_session, width, height)
        else:
            # Standalone mode - use mouse
            mouse_module = importlib.import_module(f"{info.module_path}.input.sources.mouse")
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
        from games.common import GameState
        return GameState


# Singleton instance for convenience
_registry: Optional[GameRegistry] = None

def get_registry() -> GameRegistry:
    """Get the global game registry instance."""
    global _registry
    if _registry is None:
        _registry = GameRegistry()
    return _registry
