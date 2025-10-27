"""
Unit tests for menu system.

Tests menu screens, navigation, and action handling.
"""

import pytest
import pygame
from game.menu import (
    MenuScreen,
    StartMenu,
    GameOverMenu,
    PauseMenu,
    MenuAction,
    MenuItem,
)
from models import Vector2D


@pytest.fixture
def pygame_init():
    """Initialize pygame for testing."""
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def test_screen(pygame_init):
    """Create a test pygame surface."""
    return pygame.display.set_mode((800, 600))


class TestMenuItem:
    """Test cases for MenuItem class."""

    def test_menu_item_creation(self):
        """Test creating a menu item."""
        item = MenuItem(
            text="Test Item",
            action=MenuAction.START_GAME,
            position=Vector2D(x=100.0, y=200.0)
        )

        assert item.text == "Test Item"
        assert item.action == MenuAction.START_GAME
        assert item.position.x == 100.0
        assert item.position.y == 200.0
        assert item.selected is False

    def test_menu_item_render(self, test_screen):
        """Test rendering a menu item doesn't crash."""
        item = MenuItem(
            text="Test Item",
            action=MenuAction.START_GAME,
            position=Vector2D(x=400.0, y=300.0)
        )

        # Should not raise an exception
        item.render(test_screen)

    def test_menu_item_selected_state(self, test_screen):
        """Test menu item selection changes color."""
        item = MenuItem(
            text="Test Item",
            action=MenuAction.START_GAME,
            position=Vector2D(x=400.0, y=300.0)
        )

        # Not selected initially
        assert item.selected is False

        # Select it
        item.selected = True
        assert item.selected is True

        # Rendering should still work
        item.render(test_screen)


class TestMenuScreen:
    """Test cases for MenuScreen base class."""

    def test_menu_screen_creation(self):
        """Test creating a menu screen."""
        menu = MenuScreen(title="Test Menu")

        assert menu.title == "Test Menu"
        assert len(menu.items) == 0
        assert menu.selected_index == 0

    def test_add_menu_item(self):
        """Test adding menu items."""
        menu = MenuScreen(title="Test Menu")

        menu.add_item("Item 1", MenuAction.START_GAME, Vector2D(x=100.0, y=100.0))
        assert len(menu.items) == 1
        assert menu.items[0].text == "Item 1"
        assert menu.items[0].selected is True  # First item auto-selected

        menu.add_item("Item 2", MenuAction.QUIT_GAME, Vector2D(x=100.0, y=150.0))
        assert len(menu.items) == 2
        assert menu.items[1].selected is False  # Second item not selected

    def test_keyboard_navigation_down(self):
        """Test navigating menu with DOWN arrow."""
        menu = MenuScreen(title="Test Menu")
        menu.add_item("Item 1", MenuAction.START_GAME, Vector2D(x=100.0, y=100.0))
        menu.add_item("Item 2", MenuAction.QUIT_GAME, Vector2D(x=100.0, y=150.0))

        # Initially item 0 is selected
        assert menu.selected_index == 0
        assert menu.items[0].selected is True

        # Press DOWN key
        key_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN})
        result = menu.handle_input([key_event])

        # Should move to item 1
        assert menu.selected_index == 1
        assert menu.items[0].selected is False
        assert menu.items[1].selected is True
        assert result is None  # No action on navigation

    def test_keyboard_navigation_up(self):
        """Test navigating menu with UP arrow."""
        menu = MenuScreen(title="Test Menu")
        menu.add_item("Item 1", MenuAction.START_GAME, Vector2D(x=100.0, y=100.0))
        menu.add_item("Item 2", MenuAction.QUIT_GAME, Vector2D(x=100.0, y=150.0))

        # Press UP key (should wrap to last item)
        key_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_UP})
        result = menu.handle_input([key_event])

        assert menu.selected_index == 1  # Wrapped around
        assert menu.items[1].selected is True

    def test_keyboard_navigation_wasd(self):
        """Test navigating menu with WASD keys."""
        menu = MenuScreen(title="Test Menu")
        menu.add_item("Item 1", MenuAction.START_GAME, Vector2D(x=100.0, y=100.0))
        menu.add_item("Item 2", MenuAction.QUIT_GAME, Vector2D(x=100.0, y=150.0))

        # Press S key (down)
        key_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_s})
        menu.handle_input([key_event])
        assert menu.selected_index == 1

        # Press W key (up)
        key_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_w})
        menu.handle_input([key_event])
        assert menu.selected_index == 0

    def test_keyboard_activation_enter(self):
        """Test activating menu item with ENTER."""
        menu = MenuScreen(title="Test Menu")
        menu.add_item("Item 1", MenuAction.START_GAME, Vector2D(x=100.0, y=100.0))

        # Press ENTER
        key_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN})
        result = menu.handle_input([key_event])

        assert result == MenuAction.START_GAME

    def test_keyboard_activation_space(self):
        """Test activating menu item with SPACE."""
        menu = MenuScreen(title="Test Menu")
        menu.add_item("Item 1", MenuAction.QUIT_GAME, Vector2D(x=100.0, y=100.0))

        # Press SPACE
        key_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_SPACE})
        result = menu.handle_input([key_event])

        assert result == MenuAction.QUIT_GAME

    def test_mouse_click_activation(self):
        """Test activating menu item with mouse click."""
        menu = MenuScreen(title="Test Menu")
        menu.add_item("Item 1", MenuAction.START_GAME, Vector2D(x=400.0, y=300.0))

        # Click near the menu item position
        click_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'pos': (400, 300), 'button': 1}
        )
        result = menu.handle_input([click_event])

        assert result == MenuAction.START_GAME

    def test_mouse_hover_selection(self):
        """Test menu item selection with mouse hover."""
        menu = MenuScreen(title="Test Menu")
        menu.add_item("Item 1", MenuAction.START_GAME, Vector2D(x=400.0, y=300.0))
        menu.add_item("Item 2", MenuAction.QUIT_GAME, Vector2D(x=400.0, y=380.0))

        # Initially item 0 is selected
        assert menu.selected_index == 0

        # Move mouse over item 1
        motion_event = pygame.event.Event(
            pygame.MOUSEMOTION,
            {'pos': (400, 380)}
        )
        menu.handle_input([motion_event])

        # Item 1 should be selected
        assert menu.selected_index == 1
        assert menu.items[1].selected is True

    def test_render_menu(self, test_screen):
        """Test rendering menu doesn't crash."""
        menu = MenuScreen(title="Test Menu")
        menu.add_item("Item 1", MenuAction.START_GAME, Vector2D(x=400.0, y=300.0))
        menu.add_item("Item 2", MenuAction.QUIT_GAME, Vector2D(x=400.0, y=380.0))

        # Should not raise an exception
        menu.render(test_screen)


class TestStartMenu:
    """Test cases for StartMenu."""

    def test_start_menu_creation(self):
        """Test creating start menu."""
        menu = StartMenu()

        assert menu.title == "DUCK HUNT"
        assert len(menu.items) == 3  # Start, Input, Quit
        assert menu.selected_mode == "classic"
        assert menu.selected_input == "mouse"

    def test_start_menu_has_start_action(self):
        """Test start menu has start game action."""
        menu = StartMenu()

        # First item should be "Start Game"
        assert menu.items[0].action == MenuAction.START_GAME

    def test_start_menu_has_quit_action(self):
        """Test start menu has quit action."""
        menu = StartMenu()

        # Last item should be "Quit"
        assert menu.items[-1].action == MenuAction.QUIT_GAME

    def test_start_menu_render(self, test_screen):
        """Test rendering start menu."""
        menu = StartMenu()

        # Should not raise an exception
        menu.render(test_screen)


class TestGameOverMenu:
    """Test cases for GameOverMenu."""

    def test_game_over_menu_creation_loss(self):
        """Test creating game over menu for a loss."""
        menu = GameOverMenu(
            score=150,
            accuracy=0.75,
            max_combo=8,
            won=False
        )

        assert menu.title == "GAME OVER"
        assert menu.score == 150
        assert menu.accuracy == 0.75
        assert menu.max_combo == 8
        assert menu.won is False
        assert len(menu.items) == 2  # Restart, Quit

    def test_game_over_menu_creation_win(self):
        """Test creating game over menu for a win."""
        menu = GameOverMenu(
            score=500,
            accuracy=0.95,
            max_combo=20,
            won=True
        )

        assert menu.title == "YOU WIN!"
        assert menu.score == 500
        assert menu.accuracy == 0.95
        assert menu.max_combo == 20
        assert menu.won is True

    def test_game_over_menu_has_restart_action(self):
        """Test game over menu has restart action."""
        menu = GameOverMenu(100, 0.5, 5, False)

        # First item should be "Restart"
        assert menu.items[0].action == MenuAction.RESTART

    def test_game_over_menu_has_quit_action(self):
        """Test game over menu has quit action."""
        menu = GameOverMenu(100, 0.5, 5, False)

        # Last item should be "Quit"
        assert menu.items[-1].action == MenuAction.QUIT_GAME

    def test_game_over_menu_render(self, test_screen):
        """Test rendering game over menu."""
        menu = GameOverMenu(150, 0.75, 8, False)

        # Should not raise an exception
        menu.render(test_screen)


class TestPauseMenu:
    """Test cases for PauseMenu."""

    def test_pause_menu_creation(self):
        """Test creating pause menu."""
        menu = PauseMenu()

        assert menu.title == "PAUSED"
        assert len(menu.items) == 2  # Resume, Quit to Menu

    def test_pause_menu_render(self, test_screen):
        """Test rendering pause menu with overlay."""
        menu = PauseMenu()

        # Should not raise an exception
        menu.render(test_screen)

    def test_pause_menu_has_quit_action(self):
        """Test pause menu has quit to menu action."""
        menu = PauseMenu()

        # Last item should quit to menu
        assert menu.items[-1].action == MenuAction.QUIT_GAME
