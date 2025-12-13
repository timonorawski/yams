"""Base class for all AMS games.

All games should inherit from BaseGame to ensure consistent interface
with dev_game.py, ams_game.py, and the game registry.

Game metadata (NAME, DESCRIPTION, etc.) and CLI arguments (ARGUMENTS)
are declared as class attributes, making them part of the plugin architecture.

Level Support:
Games can opt-in to YAML-based level support by:
1. Setting LEVELS_DIR class attribute to their levels directory
2. Implementing _create_level_loader() to return a game-specific loader
3. Implementing _apply_level_config() to apply level data to game state

Level groups (campaigns, tutorials) are also supported - see games/common/levels.py.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import pygame

from ams.games.game_state import GameState
from ams.games.palette import GamePalette
from ams.games.quiver import QuiverState, create_quiver
from ams.logging import get_logger

log = get_logger('base_game')

if TYPE_CHECKING:
    from ams.games.levels import LevelLoader, LevelGroup


class BaseGame(ABC):
    """Abstract base class for all AMS games.

    Class Attributes (metadata):
        NAME: Display name for the game
        DESCRIPTION: Short description of gameplay
        VERSION: Semantic version string
        AUTHOR: Author/team name
        ARGUMENTS: List of CLI argument definitions for argparse

    Subclasses must implement:
        - _get_internal_state() -> GameState: Map internal state to standard state
        - get_score() -> int: Return current score
        - handle_input(events): Process input events
        - update(dt): Update game logic
        - render(screen): Draw the game

    Optional overrides:
        - reset(): Reset game to initial state
        - set_palette(name) -> str: Switch color palette
        - cycle_palette() -> str: Cycle to next palette

    Usage:
        class MyGame(BaseGame):
            NAME = "My Game"
            DESCRIPTION = "A fun game"
            VERSION = "1.0.0"
            AUTHOR = "Me"

            ARGUMENTS = [
                {'name': '--difficulty', 'type': str, 'default': 'normal',
                 'help': 'Game difficulty'},
            ]

            def __init__(self, difficulty='normal', **kwargs):
                super().__init__(**kwargs)
                self._difficulty = difficulty

            def _get_internal_state(self) -> GameState:
                return GameState.PLAYING

            # ... implement other abstract methods
    """

    # =========================================================================
    # Game Metadata (override in subclasses)
    # =========================================================================

    NAME: str = "Unnamed Game"
    DESCRIPTION: str = "No description"
    VERSION: str = "1.0.0"
    AUTHOR: str = "Unknown"

    # CLI argument definitions for argparse
    # Each entry is a dict with keys: name, type, default, help, choices (optional), action (optional)
    # Example:
    #   ARGUMENTS = [
    #       {'name': '--difficulty', 'type': str, 'default': 'normal',
    #        'choices': ['easy', 'normal', 'hard'], 'help': 'Game difficulty'},
    #       {'name': '--time-limit', 'type': int, 'default': 60,
    #        'help': 'Time limit in seconds (0=unlimited)'},
    #   ]
    ARGUMENTS: List[Dict[str, Any]] = []

    # Level support - set LEVELS_DIR to enable level loading
    # Should be Path(__file__).parent / 'levels' in subclasses
    LEVELS_DIR: Optional[Path] = None

    # =========================================================================
    # Standard Arguments (automatically available to all games)
    # Subclasses can extend ARGUMENTS but these are always included
    # =========================================================================

    _BASE_ARGUMENTS: List[Dict[str, Any]] = [
        {
            'name': '--palette',
            'type': str,
            'default': None,
            'help': 'Test palette: full, bw, warm, cool, mono_red, etc.'
        },
        {
            'name': '--quiver-size',
            'type': int,
            'default': None,
            'help': 'Shots before retrieval pause (0=unlimited)'
        },
        {
            'name': '--retrieval-pause',
            'type': int,
            'default': 30,
            'help': 'Seconds for retrieval (0=manual)'
        },
    ]

    # Level-related arguments (only included if LEVELS_DIR is set)
    _LEVEL_ARGUMENTS: List[Dict[str, Any]] = [
        {
            'name': '--level',
            'type': str,
            'default': None,
            'help': 'Level to play (slug or path to YAML)'
        },
        {
            'name': '--list-levels',
            'action': 'store_true',
            'default': False,
            'help': 'List available levels and exit'
        },
        {
            'name': '--level-group',
            'type': str,
            'default': None,
            'help': 'Play through a level group (campaign, tutorial, etc.)'
        },
        {
            'name': '--choose-level',
            'action': 'store_true',
            'default': False,
            'help': 'Show level chooser UI before starting'
        },
    ]

    @classmethod
    def get_arguments(cls) -> List[Dict[str, Any]]:
        """Get all CLI arguments for this game (game-specific + base + level).

        Returns list of argument definitions suitable for argparse.
        Game-specific arguments come first, then level args (if LEVELS_DIR set),
        then base arguments. Duplicates by name are removed (game-specific takes precedence).
        """
        # Collect argument names from game-specific args
        seen_names = set()
        result = []

        # Game-specific arguments first
        for arg in cls.ARGUMENTS:
            name = arg.get('name', '')
            if name and name not in seen_names:
                seen_names.add(name)
                result.append(arg)

        # Level arguments if LEVELS_DIR is set
        if cls.LEVELS_DIR is not None:
            for arg in cls._LEVEL_ARGUMENTS:
                name = arg.get('name', '')
                if name and name not in seen_names:
                    seen_names.add(name)
                    result.append(arg)

        # Then base arguments (skip if already defined)
        for arg in cls._BASE_ARGUMENTS:
            name = arg.get('name', '')
            if name and name not in seen_names:
                seen_names.add(name)
                result.append(arg)

        return result

    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """Get game metadata as a dictionary.

        Returns:
            Dict with keys: name, description, version, author, arguments
        """
        return {
            'name': cls.NAME,
            'description': cls.DESCRIPTION,
            'version': cls.VERSION,
            'author': cls.AUTHOR,
            'arguments': cls.get_arguments(),
        }

    # =========================================================================
    # Instance Initialization
    # =========================================================================

    def __init__(
        self,
        # Palette support
        color_palette: Optional[List[Tuple[int, int, int]]] = None,
        palette_name: Optional[str] = None,
        palette: Optional[str] = None,  # CLI arg name
        # Quiver support
        quiver_size: Optional[int] = None,
        retrieval_pause: int = 30,
        # Level support
        level: Optional[str] = None,
        level_group: Optional[str] = None,
        list_levels: bool = False,
        choose_level: bool = False,
        **kwargs,
    ):
        """Initialize base game.

        Args:
            color_palette: AMS-provided colors for CV compatibility
            palette_name: Test palette name for standalone mode
            palette: Alias for palette_name (CLI arg name)
            quiver_size: Shots before retrieval (None = unlimited)
            retrieval_pause: Seconds for retrieval (0 = manual)
            level: Level slug to load (if game has levels)
            level_group: Level group/campaign to play through
            list_levels: Print available levels and exit
            choose_level: Show level chooser UI before starting
        """
        # Palette management (accept either palette_name or palette)
        effective_palette = palette_name or palette
        self._palette = GamePalette(colors=color_palette, palette_name=effective_palette)

        # Quiver management (None if unlimited)
        self._quiver = create_quiver(quiver_size, retrieval_pause)

        # Track if in retrieval state
        self._in_retrieval = False

        # Level support
        self._level_loader: Optional['LevelLoader'] = None
        self._current_level_slug: Optional[str] = None
        self._current_level_data: Any = None
        self._current_group: Optional['LevelGroup'] = None
        self._show_level_chooser = False

        # Initialize level support if LEVELS_DIR is set
        if self.LEVELS_DIR is not None:
            self._init_level_support(
                level=level,
                level_group=level_group,
                list_levels=list_levels,
                choose_level=choose_level,
            )

    @property
    def state(self) -> GameState:
        """Current game state (standard interface).

        Returns the appropriate GameState based on internal state.
        Games should not override this - override _get_internal_state instead.
        """
        if self._in_retrieval:
            return GameState.RETRIEVAL
        return self._get_internal_state()

    @abstractmethod
    def _get_internal_state(self) -> GameState:
        """Map internal game state to standard GameState.

        Subclasses must implement this to return the appropriate
        GameState based on their internal state tracking.

        Returns:
            GameState.PLAYING, GameState.GAME_OVER, GameState.WON, etc.
        """
        pass

    @abstractmethod
    def get_score(self) -> int:
        """Get current score.

        Returns:
            Integer score value
        """
        pass

    @abstractmethod
    def handle_input(self, events: List) -> None:
        """Process input events.

        Args:
            events: List of InputEvent objects
        """
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        """Update game logic.

        Args:
            dt: Delta time in seconds since last frame
        """
        pass

    @abstractmethod
    def render(self, screen: pygame.Surface) -> None:
        """Render the game.

        Args:
            screen: Pygame surface to draw on
        """
        pass

    # =========================================================================
    # Quiver/Retrieval Support
    # =========================================================================

    def _use_shot(self) -> bool:
        """Record a shot used. Returns True if quiver now empty.

        Call this in handle_input when player takes a shot.
        """
        if self._quiver is None:
            return False
        return self._quiver.use_shot()

    def _start_retrieval(self) -> None:
        """Start retrieval pause."""
        self._in_retrieval = True
        if self._quiver:
            self._quiver.start_retrieval()

    def _end_retrieval(self) -> None:
        """End retrieval and resume game."""
        self._in_retrieval = False
        if self._quiver:
            self._quiver.end_retrieval()

    def _update_retrieval(self, dt: float) -> bool:
        """Update retrieval timer. Returns True when complete.

        Call this in update() when state is RETRIEVAL.
        """
        if self._quiver is None:
            return True
        return self._quiver.update_retrieval(dt)

    @property
    def shots_remaining(self) -> Optional[int]:
        """Shots remaining in quiver, or None if unlimited."""
        if self._quiver is None:
            return None
        return self._quiver.remaining

    @property
    def quiver_size(self) -> Optional[int]:
        """Total quiver capacity, or None if unlimited."""
        if self._quiver is None:
            return None
        return self._quiver.size

    # =========================================================================
    # Palette Support
    # =========================================================================

    def set_palette(self, palette_name: str) -> str:
        """Switch to a named test palette.

        Args:
            palette_name: Name from TEST_PALETTES

        Returns:
            Actual palette name (may differ if invalid name provided)
        """
        self._palette.set_palette(palette_name)
        self._on_palette_changed()
        return self._palette.name

    def cycle_palette(self) -> str:
        """Cycle to next test palette.

        Returns:
            Name of new palette
        """
        name = self._palette.cycle_palette()
        self._on_palette_changed()
        return name

    @property
    def palette_name(self) -> str:
        """Current palette name."""
        return self._palette.name

    def _on_palette_changed(self) -> None:
        """Called when palette changes. Override to update entity colors."""
        pass

    # =========================================================================
    # Optional Methods
    # =========================================================================

    def reset(self) -> None:
        """Reset game to initial state.

        Override this to implement game-specific reset logic.
        """
        self._in_retrieval = False
        if self._quiver:
            self._quiver.end_retrieval()

    # =========================================================================
    # Game Actions (for web controller UI)
    # =========================================================================

    def get_available_actions(self) -> List[Dict[str, Any]]:
        """Get list of actions currently available to the player.

        Returns a list of action definitions that the web controller can
        display as buttons. Each action has:
        - id: Unique identifier (e.g., 'retry', 'skip', 'next_level')
        - label: Display text (e.g., 'Retry Level')
        - style: Optional style hint ('primary', 'secondary', 'danger')

        Override this in subclasses to provide game-specific actions.
        Base implementation returns empty list.

        Example:
            def get_available_actions(self):
                actions = []
                if self._level_state == LevelState.LOST:
                    actions.append({'id': 'retry', 'label': 'Retry', 'style': 'primary'})
                    actions.append({'id': 'skip', 'label': 'Skip Level', 'style': 'secondary'})
                return actions
        """
        return []

    def execute_action(self, action_id: str) -> bool:
        """Execute a game action by ID.

        Called when player triggers an action from the web UI.
        Override this in subclasses to handle game-specific actions.

        Args:
            action_id: The action identifier (e.g., 'retry', 'skip')

        Returns:
            True if action was handled, False otherwise
        """
        return False

    # =========================================================================
    # Level Support
    # =========================================================================

    def _init_level_support(
        self,
        level: Optional[str] = None,
        level_group: Optional[str] = None,
        list_levels: bool = False,
        choose_level: bool = False,
    ) -> None:
        """Initialize level support.

        Called automatically if LEVELS_DIR is set.

        Args:
            level: Level slug to load
            level_group: Level group slug to load
            list_levels: Print level list and exit
            choose_level: Show level chooser UI
        """
        # Create loader
        self._level_loader = self._create_level_loader()
        self._show_level_chooser = choose_level and level is None and level_group is None

        # Handle list-levels request
        if list_levels:
            self._print_levels()
            import sys
            sys.exit(0)

        # Load level group if specified
        if level_group and self._level_loader:
            try:
                self._current_group = self._level_loader.load_group(level_group)
                level = self._current_group.current_level
            except (FileNotFoundError, ValueError) as e:
                log.error(f"Failed to load level group '{level_group}': {e}")

        # Load specific level if specified
        if level and self._level_loader:
            self._load_level(level)

    def _create_level_loader(self) -> Optional['LevelLoader']:
        """Create the level loader instance.

        Override in subclass to return a game-specific loader.
        Default returns SimpleLevelLoader.

        Returns:
            LevelLoader instance, or None if LEVELS_DIR not set
        """
        if self.LEVELS_DIR is None or not self.LEVELS_DIR.exists():
            return None

        from ams.games.levels import SimpleLevelLoader
        return SimpleLevelLoader(self.LEVELS_DIR)

    def _load_level(self, slug: str) -> bool:
        """Load a level by slug.

        Args:
            slug: Level identifier

        Returns:
            True if loaded successfully
        """
        if not self._level_loader:
            return False

        try:
            self._current_level_data = self._level_loader.load_level(slug)
            self._current_level_slug = slug
            self._apply_level_config(self._current_level_data)
            return True
        except (FileNotFoundError, ValueError) as e:
            log.error(f"Failed to load level '{slug}': {e}")
            return False

    def _apply_level_config(self, level_data: Any) -> None:
        """Apply loaded level configuration to game state.

        Override in subclass to handle game-specific level setup.

        Args:
            level_data: The loaded level data object
        """
        pass  # Default: no-op, subclass implements

    def _advance_to_next_level(self) -> bool:
        """Advance to next level in group (if playing a group).

        Internal method - games should call _level_complete() instead.

        Returns:
            True if advanced to next level, False if group complete or no group
        """
        if not self._current_group:
            return False

        next_level = self._current_group.advance()
        if next_level:
            return self._load_level(next_level)

        return False

    def _level_complete(self) -> bool:
        """Called when a level is completed successfully.

        Games should call this when the player beats a level. This method:
        1. Checks if there's a next level in the group
        2. If yes, loads it and calls _on_level_transition()
        3. If no, returns False (game should transition to WON state)

        Future: This will also handle:
        - Pause for target clearance
        - Quick recalibration between levels
        - Level transition animations

        Returns:
            True if transitioned to next level, False if no more levels
        """
        if self._advance_to_next_level():
            self._on_level_transition()
            return True
        return False

    def _on_level_transition(self) -> None:
        """Called when transitioning to a new level.

        Override this to reinitialize game state for the new level.
        The new level data is already loaded via _apply_level_config().

        Default implementation does nothing - subclasses should override
        to reset physics, clear entities, etc.
        """
        pass

    def _print_levels(self) -> None:
        """Print available levels to stdout."""
        if not self._level_loader:
            print("No levels directory configured")
            return

        print(f"\nAvailable levels for {self.NAME}:")
        print("-" * 50)

        levels = self._level_loader.list_levels()
        for slug in levels:
            info = self._level_loader.get_level_info(slug)
            if info:
                diff_str = "*" * info.difficulty
                print(f"  {slug:24} [{diff_str:5}] {info.name}")
            else:
                print(f"  {slug}")

        groups = self._level_loader.list_groups()
        if groups:
            print("\nLevel groups:")
            print("-" * 50)
            for slug in groups:
                info = self._level_loader.get_level_info(slug)
                if info:
                    count = len(info.levels)
                    print(f"  {slug:24} ({count} levels) {info.name}")
                else:
                    print(f"  {slug}")

        if not levels and not groups:
            print("  (no levels found)")

        print()

    @property
    def current_level_name(self) -> str:
        """Get current level display name."""
        if self._level_loader and self._current_level_slug:
            info = self._level_loader.get_level_info(self._current_level_slug)
            if info:
                return info.name
        return ""

    @property
    def current_level_slug(self) -> Optional[str]:
        """Get current level slug."""
        return self._current_level_slug

    @property
    def current_group(self) -> Optional['LevelGroup']:
        """Get current level group (if playing a group)."""
        return self._current_group

    @property
    def has_levels(self) -> bool:
        """Check if this game has level support configured."""
        return self._level_loader is not None

    @property
    def show_level_chooser(self) -> bool:
        """Check if level chooser UI should be shown."""
        return self._show_level_chooser

    @show_level_chooser.setter
    def show_level_chooser(self, value: bool) -> None:
        """Set whether level chooser UI should be shown."""
        self._show_level_chooser = value
