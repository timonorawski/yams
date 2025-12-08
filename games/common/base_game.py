"""Base class for all AMS games.

All games should inherit from BaseGame to ensure consistent interface
with dev_game.py, ams_game.py, and the game registry.

Game metadata (NAME, DESCRIPTION, etc.) and CLI arguments (ARGUMENTS)
are declared as class attributes, making them part of the plugin architecture.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import pygame

from games.common.game_state import GameState
from games.common.palette import GamePalette
from games.common.quiver import QuiverState, create_quiver


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

    @classmethod
    def get_arguments(cls) -> List[Dict[str, Any]]:
        """Get all CLI arguments for this game (game-specific + base).

        Returns list of argument definitions suitable for argparse.
        Game-specific arguments come first, then base arguments.
        Duplicates by name are removed (game-specific takes precedence).
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
        **kwargs,
    ):
        """Initialize base game.

        Args:
            color_palette: AMS-provided colors for CV compatibility
            palette_name: Test palette name for standalone mode
            palette: Alias for palette_name (CLI arg name)
            quiver_size: Shots before retrieval (None = unlimited)
            retrieval_pause: Seconds for retrieval (0 = manual)
        """
        # Palette management (accept either palette_name or palette)
        effective_palette = palette_name or palette
        self._palette = GamePalette(colors=color_palette, palette_name=effective_palette)

        # Quiver management (None if unlimited)
        self._quiver = create_quiver(quiver_size, retrieval_pause)

        # Track if in retrieval state
        self._in_retrieval = False

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
