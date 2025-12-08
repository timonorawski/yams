"""
Main game engine for Duck Hunt.

This module provides the core game loop, pygame initialization,
and frame timing for the Duck Hunt game.
"""

import pygame
from typing import Optional
from models import GameState, DuckHuntInternalState
import config
from input.input_manager import InputManager
from input.sources.mouse import MouseInputSource
from game.modes.classic import ClassicMode
from game.game_mode import GameMode
from game.menu import StartMenu, GameOverMenu, PauseMenu, MenuAction


class GameEngine:
    """Main game engine managing the game loop and pygame state.

    Manages the game loop, input processing, active game mode, and menu system.
    Integrates InputManager for abstracted input and delegates gameplay
    to the active game mode. Handles menu navigation and pause functionality.

    Attributes:
        screen: Pygame display surface
        clock: Pygame clock for frame timing
        running: Whether the game loop should continue
        state: Current game state (MENU, PLAYING, PAUSED, GAME_OVER)
        input_manager: Input manager for handling all input sources
        current_mode: Active game mode (ClassicMode, FlashMode, etc.)
        start_menu: Start menu screen
        pause_menu: Pause menu screen
        game_over_menu: Game over menu screen

    Examples:
        >>> engine = GameEngine()
        >>> engine.run()
    """

    def __init__(self):
        """Initialize the game engine and pygame.

        Sets up the display, clock, initial game state, input manager,
        menus, and starts in the main menu.
        """
        # Initialize pygame
        pygame.init()

        # Create display surface
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        pygame.display.set_caption("Duck Hunt")

        # Create clock for frame timing
        self.clock = pygame.time.Clock()

        # Game state
        self.running = True
        self.state = DuckHuntInternalState.MENU  # Start in menu

        # Initialize input manager with mouse input
        self.input_manager = InputManager(MouseInputSource())

        # Initialize menus
        self.start_menu = StartMenu()
        self.pause_menu: Optional[PauseMenu] = None
        self.game_over_menu: Optional[GameOverMenu] = None

        # Game mode (initialized when game starts)
        self.current_mode: Optional[GameMode] = None

    def start_game(self) -> None:
        """Start a new game by initializing the game mode."""
        self.current_mode = ClassicMode(
            max_misses=10,  # Game over after 10 misses
            target_score=None,  # Endless mode
        )
        self.state = DuckHuntInternalState.PLAYING

    def handle_events(self) -> None:
        """Process pygame events based on current game state.

        Handles quit events, pause/resume, and menu navigation.
        Delegates input to the appropriate handler based on game state.
        """
        events = pygame.event.get()

        # Global quit handling
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return

        # State-specific event handling
        if self.state == DuckHuntInternalState.MENU:
            self._handle_menu_events(events)

        elif self.state == DuckHuntInternalState.PLAYING:
            self._handle_playing_events(events)

        elif self.state == DuckHuntInternalState.WAITING_FOR_RELOAD:
            self._handle_retrieval_events(events)

        elif self.state == DuckHuntInternalState.PAUSED:
            self._handle_pause_events(events)

        elif self.state == DuckHuntInternalState.GAME_OVER:
            self._handle_game_over_events(events)

    def _handle_menu_events(self, events: list) -> None:
        """Handle events in menu state.

        Args:
            events: List of pygame events
        """
        action = self.start_menu.handle_input(events)

        if action == MenuAction.START_GAME:
            self.start_game()
        elif action == MenuAction.QUIT_GAME:
            self.running = False

    def _handle_playing_events(self, events: list) -> None:
        """Handle events in playing state.

        Args:
            events: List of pygame events
        """
        # Check for special keys
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Pause game
                    self.state = DuckHuntInternalState.PAUSED
                    self.pause_menu = PauseMenu()
                    return
                elif event.key == pygame.K_p:
                    # Cycle palette (for standalone testing)
                    if self.current_mode is not None and hasattr(self.current_mode, 'cycle_palette'):
                        palette_name = self.current_mode.cycle_palette()
                        print(f"Switched to palette: {palette_name}")
                    return
                elif event.key == pygame.K_SPACE:
                    # Manual retrieval ready (for manual retrieval mode)
                    if self.current_mode is not None and hasattr(self.current_mode, 'manual_retrieval_ready'):
                        self.current_mode.manual_retrieval_ready()
                    return

        # Post events back for InputManager
        for event in events:
            pygame.event.post(event)

        # Update input manager
        self.input_manager.update(0.0)

        # Get input events and pass to active mode
        if self.current_mode is not None:
            input_events = self.input_manager.get_events()
            self.current_mode.handle_input(input_events)

    def _handle_retrieval_events(self, events: list) -> None:
        """Handle events in retrieval/reload state.

        Args:
            events: List of pygame events
        """
        # Check for manual retrieval ready (SPACE)
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if self.current_mode is not None and hasattr(self.current_mode, 'manual_retrieval_ready'):
                    self.current_mode.manual_retrieval_ready()
                return

    def _handle_pause_events(self, events: list) -> None:
        """Handle events in paused state.

        Args:
            events: List of pygame events
        """
        # Check for resume key (ESC)
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = DuckHuntInternalState.PLAYING
                self.pause_menu = None
                return

        # Handle menu navigation
        if self.pause_menu is not None:
            action = self.pause_menu.handle_input(events)

            if action == MenuAction.QUIT_GAME:
                # Return to main menu
                self.state = DuckHuntInternalState.MENU
                self.current_mode = None
                self.pause_menu = None

    def _handle_game_over_events(self, events: list) -> None:
        """Handle events in game over state.

        Args:
            events: List of pygame events
        """
        if self.game_over_menu is not None:
            action = self.game_over_menu.handle_input(events)

            if action == MenuAction.RESTART:
                self.start_game()
                self.game_over_menu = None
            elif action == MenuAction.QUIT_GAME:
                # Return to main menu
                self.state = DuckHuntInternalState.MENU
                self.current_mode = None
                self.game_over_menu = None

    def update(self, dt: float) -> None:
        """Update game state based on current state.

        Updates the active game mode when playing, and checks for
        state transitions (e.g., PLAYING -> GAME_OVER, PLAYING -> WAITING_FOR_RELOAD).

        Args:
            dt: Delta time since last frame in seconds
        """
        # Update game mode when actively playing or in retrieval
        if self.state == DuckHuntInternalState.PLAYING or self.state == DuckHuntInternalState.WAITING_FOR_RELOAD:
            if self.current_mode is not None:
                self.current_mode.update(dt)

                # Sync engine state with mode state
                if self.current_mode.state != self.state:
                    if self.current_mode.state == DuckHuntInternalState.GAME_OVER:
                        self._transition_to_game_over()
                    else:
                        self.state = self.current_mode.state

        # Menu and pause states don't need updates (static screens)

    def _transition_to_game_over(self) -> None:
        """Transition to game over state and create game over menu."""
        if self.current_mode is not None:
            stats = self.current_mode.get_score().get_stats()
            # Determine if player won based on whether they reached target score
            won = False
            if hasattr(self.current_mode, '_target_score') and self.current_mode._target_score is not None:
                won = stats.hits >= self.current_mode._target_score

            self.game_over_menu = GameOverMenu(
                score=stats.hits,
                accuracy=stats.accuracy,
                max_combo=stats.max_combo,
                won=won
            )
            self.state = DuckHuntInternalState.GAME_OVER

    def render(self) -> None:
        """Render the current frame based on game state.

        Renders the appropriate screen (menu, game, pause overlay, or
        game over) based on current game state.
        """
        # Clear screen to background color
        self.screen.fill(config.BACKGROUND_COLOR)

        # Render based on state
        if self.state == DuckHuntInternalState.MENU:
            self.start_menu.render(self.screen)

        elif self.state == DuckHuntInternalState.PLAYING:
            # Render active game mode
            if self.current_mode is not None:
                self.current_mode.render(self.screen)

        elif self.state == DuckHuntInternalState.WAITING_FOR_RELOAD:
            # Render game mode with retrieval overlay
            if self.current_mode is not None:
                self.current_mode.render(self.screen)

        elif self.state == DuckHuntInternalState.PAUSED:
            # Render game mode behind pause overlay
            if self.current_mode is not None:
                self.current_mode.render(self.screen)
            # Render pause menu on top
            if self.pause_menu is not None:
                self.pause_menu.render(self.screen)

        elif self.state == DuckHuntInternalState.GAME_OVER:
            # Render game over menu
            if self.game_over_menu is not None:
                self.game_over_menu.render(self.screen)

        # Flip display to show the new frame
        pygame.display.flip()

    def run(self) -> None:
        """Run the main game loop.

        This implements the standard game loop pattern:
        1. Handle events
        2. Update game state
        3. Render frame
        4. Maintain target FPS

        The loop continues until self.running is set to False.
        """
        while self.running:
            # Calculate delta time in seconds
            dt = self.clock.tick(config.FPS) / 1000.0

            # Handle events (quit, input, etc.)
            self.handle_events()

            # Update game state
            self.update(dt)

            # Render the current frame
            self.render()

    def quit(self) -> None:
        """Clean up and quit pygame.

        Should be called when the game exits to properly
        shut down pygame subsystems.
        """
        pygame.quit()
