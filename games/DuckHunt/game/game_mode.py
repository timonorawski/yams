"""
GameMode base class for Duck Hunt game.

This module defines the abstract base class for all game modes. Each game mode
implements specific gameplay rules, target spawning logic, and win/lose conditions.
"""

from abc import ABC, abstractmethod
from typing import List
import pygame
from models import GameState
from game.target import Target
from input.input_event import InputEvent


class GameMode(ABC):
    """Abstract base class for game modes.

    All game modes must inherit from this class and implement the abstract
    methods for game logic, input handling, and rendering. This ensures a
    consistent interface across different game modes.

    The GameMode manages:
    - A list of active targets
    - Current game state (playing/won/lost)
    - Game logic updates
    - Input event processing
    - Mode-specific rendering

    Attributes:
        targets: List of active Target instances
        state: Current game state (GameState enum)

    Examples:
        >>> # GameMode cannot be instantiated directly
        >>> # Instead, create a concrete subclass:
        >>> class SimpleMode(GameMode):
        ...     def update(self, dt: float) -> None:
        ...         pass
        ...     def handle_input(self, events: List[InputEvent]) -> None:
        ...         pass
        ...     def render(self, screen: pygame.Surface) -> None:
        ...         pass
    """

    def __init__(self):
        """Initialize the game mode.

        Sets up the initial game state and empty targets list.
        Subclasses should call super().__init__() and then initialize
        their specific state.
        """
        self._targets: List[Target] = []
        self._state: GameState = GameState.PLAYING

    @property
    def targets(self) -> List[Target]:
        """Get the list of active targets.

        Returns:
            List of Target instances currently in the game
        """
        return self._targets

    @property
    def state(self) -> GameState:
        """Get the current game state.

        Returns:
            GameState enum value (PLAYING, GAME_OVER, etc.)
        """
        return self._state

    @abstractmethod
    def update(self, dt: float) -> None:
        """Update game logic for this frame.

        This method is called once per frame and should handle:
        - Target movement and updates
        - Target spawning
        - Win/lose condition checking
        - Game state transitions
        - Any time-based game mechanics

        Args:
            dt: Time delta in seconds since last frame

        Examples:
            >>> class SimpleMode(GameMode):
            ...     def update(self, dt: float) -> None:
            ...         # Update all targets
            ...         self._targets = [t.update(dt) for t in self._targets]
            ...         # Remove off-screen targets
            ...         self._targets = [t for t in self._targets if not t.is_off_screen(800, 600)]
            ...     def handle_input(self, events: List[InputEvent]) -> None:
            ...         pass
            ...     def render(self, screen: pygame.Surface) -> None:
            ...         pass
        """
        pass

    @abstractmethod
    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events for this frame.

        This method receives a list of input events (clicks, impacts, etc.)
        and should handle:
        - Hit detection against targets
        - Scoring updates
        - Target state changes
        - Any input-triggered game mechanics

        Args:
            events: List of InputEvent instances to process

        Examples:
            >>> class SimpleMode(GameMode):
            ...     def update(self, dt: float) -> None:
            ...         pass
            ...     def handle_input(self, events: List[InputEvent]) -> None:
            ...         for event in events:
            ...             for i, target in enumerate(self._targets):
            ...                 if target.is_active and target.contains_point(event.position):
            ...                     # Target was hit
            ...                     self._targets[i] = target.set_state(TargetState.HIT)
            ...                     break
            ...     def render(self, screen: pygame.Surface) -> None:
            ...         pass
        """
        pass

    @abstractmethod
    def render(self, screen: pygame.Surface) -> None:
        """Render mode-specific UI and targets.

        This method is called once per frame to draw:
        - All active targets
        - Mode-specific UI elements (score, timer, instructions, etc.)
        - Visual feedback
        - Game over screens

        Args:
            screen: Pygame surface to draw on

        Examples:
            >>> class SimpleMode(GameMode):
            ...     def update(self, dt: float) -> None:
            ...         pass
            ...     def handle_input(self, events: List[InputEvent]) -> None:
            ...         pass
            ...     def render(self, screen: pygame.Surface) -> None:
            ...         # Render all targets
            ...         for target in self._targets:
            ...             target.render(screen)
            ...         # Render score, etc.
        """
        pass

    def get_score(self) -> int:
        """Get the current score for this game mode.

        Default implementation returns 0. Subclasses should override this
        to return their actual score tracking.

        Returns:
            Current score as an integer

        Examples:
            >>> class SimpleMode(GameMode):
            ...     def __init__(self):
            ...         super().__init__()
            ...         self._score = 0
            ...     def get_score(self) -> int:
            ...         return self._score
            ...     def update(self, dt: float) -> None:
            ...         pass
            ...     def handle_input(self, events: List[InputEvent]) -> None:
            ...         pass
            ...     def render(self, screen: pygame.Surface) -> None:
            ...         pass
        """
        return 0
