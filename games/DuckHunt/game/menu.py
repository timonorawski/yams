"""
Menu system for Duck Hunt game.

This module provides menu screens for starting the game, selecting modes,
and handling game over states with restart/quit options.

Classes:
    MenuScreen: Base class for menu screens
    StartMenu: Main menu for game start and configuration
    GameOverMenu: Game over screen with stats and restart option
"""

from typing import List, Optional, Callable
from enum import Enum
import pygame
from models import Vector2D, GameState
from games.DuckHunt import config


class MenuAction(str, Enum):
    """Actions that can be triggered from menu selections."""
    START_GAME = "start_game"
    QUIT_GAME = "quit_game"
    RESTART = "restart"
    CHANGE_INPUT = "change_input"
    NONE = "none"


class MenuItem:
    """A selectable menu item.

    Attributes:
        text: Display text for the menu item
        action: Action to perform when selected
        position: Position of the menu item
        selected: Whether this item is currently selected
    """

    def __init__(self, text: str, action: MenuAction, position: Vector2D):
        """Initialize menu item.

        Args:
            text: Display text
            action: Action to perform when selected
            position: Screen position
        """
        self.text = text
        self.action = action
        self.position = position
        self.selected = False

    def render(self, screen: pygame.Surface) -> None:
        """Render the menu item.

        Args:
            screen: Pygame surface to draw on
        """
        # Choose color based on selection state
        color = config.Colors.UI_HIGHLIGHT if self.selected else config.Colors.UI_TEXT

        # Render text
        font = pygame.font.Font(None, config.Fonts.LARGE)
        text_surface = font.render(self.text, True, color)
        text_rect = text_surface.get_rect(center=(int(self.position.x), int(self.position.y)))
        screen.blit(text_surface, text_rect)


class MenuScreen:
    """Base class for menu screens.

    Provides common functionality for rendering menus and handling
    keyboard/mouse selection.

    Attributes:
        items: List of menu items
        selected_index: Index of currently selected item
        title: Menu title text
    """

    def __init__(self, title: str):
        """Initialize menu screen.

        Args:
            title: Title text for the menu
        """
        self.title = title
        self.items: List[MenuItem] = []
        self.selected_index = 0

    def add_item(self, text: str, action: MenuAction, position: Vector2D) -> None:
        """Add a menu item.

        Args:
            text: Display text
            action: Action to perform when selected
            position: Screen position
        """
        item = MenuItem(text, action, position)
        self.items.append(item)

        # Select first item by default
        if len(self.items) == 1:
            item.selected = True

    def handle_input(self, events: List[pygame.event.Event]) -> Optional[MenuAction]:
        """Handle input events for menu navigation.

        Args:
            events: List of pygame events

        Returns:
            MenuAction if an item was activated, None otherwise
        """
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    self._select_previous()
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    self._select_next()
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    return self._activate_selected()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if mouse clicked on any item
                if hasattr(event, 'pos'):
                    mouse_pos = event.pos
                else:
                    mouse_pos = pygame.mouse.get_pos()

                for i, item in enumerate(self.items):
                    # Simple hit test (within 200px width, 40px height of text center)
                    if (abs(mouse_pos[0] - item.position.x) < 200 and
                        abs(mouse_pos[1] - item.position.y) < 40):
                        self._select_item(i)
                        return self._activate_selected()

            elif event.type == pygame.MOUSEMOTION:
                # Highlight item under mouse
                if hasattr(event, 'pos'):
                    mouse_pos = event.pos
                else:
                    mouse_pos = pygame.mouse.get_pos()

                for i, item in enumerate(self.items):
                    if (abs(mouse_pos[0] - item.position.x) < 200 and
                        abs(mouse_pos[1] - item.position.y) < 40):
                        self._select_item(i)
                        break

        return None

    def _select_item(self, index: int) -> None:
        """Select a menu item by index.

        Args:
            index: Index of item to select
        """
        if 0 <= index < len(self.items):
            # Deselect current
            if 0 <= self.selected_index < len(self.items):
                self.items[self.selected_index].selected = False

            # Select new
            self.selected_index = index
            self.items[self.selected_index].selected = True

    def _select_next(self) -> None:
        """Select the next menu item (wrap around)."""
        next_index = (self.selected_index + 1) % len(self.items)
        self._select_item(next_index)

    def _select_previous(self) -> None:
        """Select the previous menu item (wrap around)."""
        prev_index = (self.selected_index - 1) % len(self.items)
        self._select_item(prev_index)

    def _activate_selected(self) -> MenuAction:
        """Activate the currently selected item.

        Returns:
            MenuAction for the selected item
        """
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index].action
        return MenuAction.NONE

    def render(self, screen: pygame.Surface) -> None:
        """Render the menu screen.

        Args:
            screen: Pygame surface to draw on
        """
        # Clear background
        screen.fill(config.Colors.BACKGROUND[:3])

        # Render title
        title_font = pygame.font.Font(None, config.Fonts.HUGE)
        title_surface = title_font.render(self.title, True, config.Colors.UI_TEXT)
        title_rect = title_surface.get_rect(center=(config.SCREEN_WIDTH // 2, 150))
        screen.blit(title_surface, title_rect)

        # Render all menu items
        for item in self.items:
            item.render(screen)


class StartMenu(MenuScreen):
    """Main menu for starting the game.

    Allows selecting game mode and input source, then starting or quitting.

    Attributes:
        selected_mode: Currently selected game mode
        selected_input: Currently selected input source
    """

    def __init__(self):
        """Initialize start menu with default options."""
        super().__init__("DUCK HUNT")

        # Center of screen
        center_x = config.SCREEN_WIDTH // 2
        base_y = 300

        # Add menu items
        self.add_item(
            "Start Game",
            MenuAction.START_GAME,
            Vector2D(x=float(center_x), y=float(base_y))
        )

        self.add_item(
            "Input: Mouse",
            MenuAction.CHANGE_INPUT,
            Vector2D(x=float(center_x), y=float(base_y + 80))
        )

        self.add_item(
            "Quit",
            MenuAction.QUIT_GAME,
            Vector2D(x=float(center_x), y=float(base_y + 160))
        )

        self.selected_mode = "classic"
        self.selected_input = "mouse"

    def render(self, screen: pygame.Surface) -> None:
        """Render the start menu with instructions.

        Args:
            screen: Pygame surface to draw on
        """
        # Render base menu
        super().render(screen)

        # Add instructions at bottom
        instructions = [
            "Use UP/DOWN arrows or W/S to navigate",
            "Press ENTER or SPACE to select",
            "Or click with mouse"
        ]

        inst_font = pygame.font.Font(None, config.Fonts.SMALL)
        y_offset = config.SCREEN_HEIGHT - 150

        for instruction in instructions:
            inst_surface = inst_font.render(instruction, True, config.Colors.LIGHT_GRAY)
            inst_rect = inst_surface.get_rect(center=(config.SCREEN_WIDTH // 2, y_offset))
            screen.blit(inst_surface, inst_rect)
            y_offset += 30


class GameOverMenu(MenuScreen):
    """Game over screen with final stats and restart option.

    Displays final score, accuracy, and best combo, with options to
    restart or quit.

    Attributes:
        score: Final score
        accuracy: Final accuracy percentage
        max_combo: Best combo achieved
        won: Whether the player won or lost
    """

    def __init__(self, score: int, accuracy: float, max_combo: int, won: bool = False):
        """Initialize game over menu.

        Args:
            score: Final score
            accuracy: Final accuracy (0.0 to 1.0)
            max_combo: Maximum combo achieved
            won: Whether player won (True) or lost (False)
        """
        title = "YOU WIN!" if won else "GAME OVER"
        super().__init__(title)

        self.score = score
        self.accuracy = accuracy
        self.max_combo = max_combo
        self.won = won

        # Center of screen
        center_x = config.SCREEN_WIDTH // 2
        base_y = 500

        # Add menu items
        self.add_item(
            "Restart",
            MenuAction.RESTART,
            Vector2D(x=float(center_x), y=float(base_y))
        )

        self.add_item(
            "Quit",
            MenuAction.QUIT_GAME,
            Vector2D(x=float(center_x), y=float(base_y + 80))
        )

    def render(self, screen: pygame.Surface) -> None:
        """Render the game over screen with stats.

        Args:
            screen: Pygame surface to draw on
        """
        # Render base menu
        super().render(screen)

        # Render stats in the middle
        stats_font = pygame.font.Font(None, config.Fonts.LARGE)
        center_x = config.SCREEN_WIDTH // 2

        # Final Score
        score_text = f"Final Score: {self.score}"
        score_surface = stats_font.render(score_text, True, config.Colors.YELLOW)
        score_rect = score_surface.get_rect(center=(center_x, 280))
        screen.blit(score_surface, score_rect)

        # Accuracy
        accuracy_text = f"Accuracy: {self.accuracy:.1%}"
        accuracy_surface = stats_font.render(accuracy_text, True, config.Colors.WHITE)
        accuracy_rect = accuracy_surface.get_rect(center=(center_x, 340))
        screen.blit(accuracy_surface, accuracy_rect)

        # Max Combo
        combo_text = f"Best Combo: {self.max_combo}x"
        combo_surface = stats_font.render(combo_text, True, config.Colors.CYAN)
        combo_rect = combo_surface.get_rect(center=(center_x, 400))
        screen.blit(combo_surface, combo_rect)


class PauseMenu(MenuScreen):
    """Pause screen overlay.

    Simple pause menu that can resume or quit to main menu.
    """

    def __init__(self):
        """Initialize pause menu."""
        super().__init__("PAUSED")

        # Center of screen
        center_x = config.SCREEN_WIDTH // 2
        base_y = 400

        # Add menu items
        self.add_item(
            "Resume (ESC)",
            MenuAction.NONE,  # Resume handled by ESC key
            Vector2D(x=float(center_x), y=float(base_y))
        )

        self.add_item(
            "Quit to Menu",
            MenuAction.QUIT_GAME,
            Vector2D(x=float(center_x), y=float(base_y + 80))
        )

    def render(self, screen: pygame.Surface) -> None:
        """Render the pause menu with semi-transparent overlay.

        Args:
            screen: Pygame surface to draw on
        """
        # Create semi-transparent overlay
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(config.Colors.BLACK[:3])
        screen.blit(overlay, (0, 0))

        # Render title
        title_font = pygame.font.Font(None, config.Fonts.HUGE)
        title_surface = title_font.render(self.title, True, config.Colors.UI_TEXT)
        title_rect = title_surface.get_rect(center=(config.SCREEN_WIDTH // 2, 250))
        screen.blit(title_surface, title_rect)

        # Render menu items
        for item in self.items:
            item.render(screen)
