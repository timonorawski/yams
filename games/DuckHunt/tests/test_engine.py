"""
Unit tests for the GameEngine class.

Tests cover:
- Initialization without errors
- Config values are correctly loaded
- Game loop can run for a few iterations
- Mode integration (ClassicMode, InputManager)
- Input event processing
- State transitions
"""

import pytest
import pygame
from engine import GameEngine
from models import GameState, Vector2D, EventType
from input.input_event import InputEvent
import config
from game.modes.classic import ClassicMode
from input.input_manager import InputManager


class TestGameEngine:
    """Tests for GameEngine initialization and basic functionality."""

    def test_engine_initialization(self):
        """Test that engine initializes without errors."""
        engine = GameEngine()

        # Verify pygame was initialized
        assert pygame.get_init()

        # Verify display was created with correct dimensions
        assert engine.screen is not None
        assert engine.screen.get_width() == config.SCREEN_WIDTH
        assert engine.screen.get_height() == config.SCREEN_HEIGHT

        # Verify clock was created
        assert engine.clock is not None

        # Verify initial state
        assert engine.running is True
        assert engine.state == GameState.PLAYING  # Now starts in PLAYING mode

        # Verify InputManager was initialized
        assert engine.input_manager is not None
        assert isinstance(engine.input_manager, InputManager)

        # Verify ClassicMode was initialized
        assert engine.current_mode is not None
        assert isinstance(engine.current_mode, ClassicMode)

        # Clean up
        engine.quit()

    def test_config_values_loaded(self):
        """Test that engine correctly uses config values."""
        engine = GameEngine()

        # Check that screen dimensions match config
        assert engine.screen.get_width() == config.SCREEN_WIDTH
        assert engine.screen.get_height() == config.SCREEN_HEIGHT

        # Clean up
        engine.quit()

    def test_engine_quit(self):
        """Test that engine can quit cleanly."""
        engine = GameEngine()
        engine.quit()

        # After quit, pygame should be uninitialized
        assert not pygame.get_init()

    def test_game_loop_iteration(self):
        """Test that game loop can run for a few iterations."""
        engine = GameEngine()

        # Run for 10 frames
        for _ in range(10):
            dt = engine.clock.tick(config.FPS) / 1000.0

            # These should not raise errors
            engine.handle_events()
            engine.update(dt)
            engine.render()

        # Engine should still be running
        assert engine.running is True

        # Clean up
        engine.quit()

    def test_handle_events_quit(self):
        """Test that QUIT event sets running to False."""
        engine = GameEngine()

        # Simulate a QUIT event
        quit_event = pygame.event.Event(pygame.QUIT)
        pygame.event.post(quit_event)

        # Handle events
        engine.handle_events()

        # Engine should now be marked as not running
        assert engine.running is False

        # Clean up
        engine.quit()

    def test_update_with_delta_time(self):
        """Test that update accepts delta time parameter."""
        engine = GameEngine()

        # Should not raise errors with various dt values
        engine.update(0.016)  # ~60 FPS
        engine.update(0.033)  # ~30 FPS
        engine.update(0.0)    # Zero dt

        # Clean up
        engine.quit()

    def test_render_clears_screen(self):
        """Test that render clears the screen to background color."""
        engine = GameEngine()

        # Render a frame
        engine.render()

        # Check that screen surface exists (can't easily verify color)
        assert engine.screen is not None

        # Clean up
        engine.quit()

    def test_engine_initializes_with_classic_mode(self):
        """Test that engine initializes with ClassicMode."""
        engine = GameEngine()

        # Verify ClassicMode is initialized
        assert engine.current_mode is not None
        assert isinstance(engine.current_mode, ClassicMode)
        assert engine.current_mode.state == GameState.PLAYING

        # Clean up
        engine.quit()

    def test_engine_passes_events_to_mode(self):
        """Test that input events are passed to the active mode."""
        engine = GameEngine()

        # Simulate a mouse click event
        mouse_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"pos": (100, 100), "button": 1}
        )
        pygame.event.post(mouse_event)

        # Handle events (should process through InputManager to mode)
        engine.handle_events()

        # Verify mode received input (score should have changed)
        # Since there are no targets, this should count as a miss
        stats = engine.current_mode._score_tracker.get_stats()
        assert stats.misses == 1

        # Clean up
        engine.quit()

    def test_mode_update_is_called(self):
        """Test that mode.update() is called during engine update."""
        engine = GameEngine()

        # Get initial spawn timer
        initial_timer = engine.current_mode._spawn_timer

        # Update for one frame
        engine.update(0.5)

        # Spawn timer should have decreased
        assert engine.current_mode._spawn_timer < initial_timer

        # Clean up
        engine.quit()

    def test_mode_render_is_called(self):
        """Test that mode.render() is called during engine render."""
        engine = GameEngine()

        # Force spawn a target so there's something to render
        engine.current_mode._spawn_target()
        assert len(engine.current_mode._targets) > 0

        # Should not raise errors
        engine.render()

        # Clean up
        engine.quit()

    def test_game_state_transition_to_game_over(self):
        """Test that engine state transitions when mode reaches GAME_OVER."""
        engine = GameEngine()

        # Force mode into GAME_OVER state by exceeding max misses
        for _ in range(10):
            engine.current_mode._score_tracker = (
                engine.current_mode._score_tracker.record_miss()
            )

        # Check game over condition
        engine.current_mode._check_game_over()
        assert engine.current_mode.state == GameState.GAME_OVER

        # Update engine - should detect mode state change
        engine.update(0.016)

        # Engine state should now be GAME_OVER
        assert engine.state == GameState.GAME_OVER

        # Clean up
        engine.quit()

    def test_engine_handles_input_when_mode_is_active(self):
        """Test that engine only processes input when mode is active."""
        engine = GameEngine()

        # Initially mode should be active
        assert engine.current_mode.state == GameState.PLAYING

        # Post a mouse click
        mouse_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"pos": (200, 200), "button": 1}
        )
        pygame.event.post(mouse_event)

        initial_misses = engine.current_mode._score_tracker.get_stats().misses

        # Handle events
        engine.handle_events()

        # Miss count should increase (no target at that position)
        final_misses = engine.current_mode._score_tracker.get_stats().misses
        assert final_misses == initial_misses + 1

        # Clean up
        engine.quit()

    def test_engine_integration_full_frame(self):
        """Test full integration: handle events, update, render."""
        engine = GameEngine()

        # Run a full frame cycle
        dt = 0.016  # ~60 FPS

        # Should not raise errors
        engine.handle_events()
        engine.update(dt)
        engine.render()

        # Engine should still be running
        assert engine.running is True

        # Clean up
        engine.quit()
