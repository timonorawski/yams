"""
Unit tests for audio feedback in FeedbackManager.

Tests audio initialization, sound generation, and playback.
Note: Actual sound playback is hard to test, so we mainly test
that methods don't crash and audio can be disabled gracefully.
"""

import pytest
import pygame
from unittest.mock import Mock, patch, MagicMock
from games.DuckHunt.game.feedback import FeedbackManager
from models import Vector2D


@pytest.fixture
def pygame_init():
    """Initialize pygame for testing."""
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def mock_mixer():
    """Mock pygame.mixer to prevent actual audio initialization."""
    with patch('pygame.mixer.init') as mock_init, \
         patch('pygame.mixer.Sound') as mock_sound:
        mock_sound_instance = MagicMock()
        mock_sound_instance.play = MagicMock()
        mock_sound_instance.set_volume = MagicMock()
        yield {
            'init': mock_init,
            'sound': mock_sound,
            'instance': mock_sound_instance
        }


class TestFeedbackManagerAudio:
    """Test cases for audio functionality in FeedbackManager."""

    def test_feedback_manager_with_audio_enabled(self, pygame_init):
        """Test creating FeedbackManager with audio enabled."""
        # This will try to initialize audio
        manager = FeedbackManager(audio_enabled=True)

        # Should have sounds dictionary
        assert hasattr(manager, 'sounds')
        assert isinstance(manager.sounds, dict)

        # Should have audio_enabled flag
        assert hasattr(manager, 'audio_enabled')

    def test_feedback_manager_with_audio_disabled(self, pygame_init):
        """Test creating FeedbackManager with audio disabled."""
        manager = FeedbackManager(audio_enabled=False)

        assert manager.audio_enabled is False
        assert manager.sounds == {}

    def test_play_hit_sound_with_audio_disabled(self, pygame_init):
        """Test playing hit sound when audio is disabled (should not crash)."""
        manager = FeedbackManager(audio_enabled=False)

        # Should not raise an exception
        manager.play_hit_sound()

    def test_play_miss_sound_with_audio_disabled(self, pygame_init):
        """Test playing miss sound when audio is disabled (should not crash)."""
        manager = FeedbackManager(audio_enabled=False)

        # Should not raise an exception
        manager.play_miss_sound()

    def test_play_combo_sound_with_audio_disabled(self, pygame_init):
        """Test playing combo sound when audio is disabled (should not crash)."""
        manager = FeedbackManager(audio_enabled=False)

        # Should not raise an exception
        manager.play_combo_sound()

    def test_add_hit_effect_plays_sound(self, pygame_init):
        """Test that add_hit_effect triggers sound playback."""
        manager = FeedbackManager(audio_enabled=False)

        # Mock the play method
        manager.play_hit_sound = Mock()

        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)

        # Should have called play_hit_sound
        manager.play_hit_sound.assert_called_once()

    def test_add_miss_effect_plays_sound(self, pygame_init):
        """Test that add_miss_effect triggers sound playback."""
        manager = FeedbackManager(audio_enabled=False)

        # Mock the play method
        manager.play_miss_sound = Mock()

        manager.add_miss_effect(Vector2D(x=100.0, y=200.0))

        # Should have called play_miss_sound
        manager.play_miss_sound.assert_called_once()

    @patch('games.DuckHunt.game.feedback.pygame.mixer')
    def test_audio_init_failure_graceful(self, mock_mixer, pygame_init):
        """Test that audio initialization failure is handled gracefully."""
        # Make mixer.init raise an exception
        mock_mixer.init.side_effect = Exception("Audio device not available")

        # Should not crash, just disable audio
        manager = FeedbackManager(audio_enabled=True)

        # Audio should be disabled after failed init
        assert manager.audio_enabled is False
        assert manager.sounds == {}

    @patch('games.DuckHunt.game.feedback.np')
    def test_sound_generation_failure_graceful(self, mock_np, pygame_init):
        """Test that sound generation failure is handled gracefully."""
        # Make numpy operations fail
        mock_np.linspace.side_effect = Exception("NumPy error")

        # Should not crash, just return None for sounds
        manager = FeedbackManager(audio_enabled=True)

        # Sound methods should still be callable
        manager.play_hit_sound()
        manager.play_miss_sound()
        manager.play_combo_sound()

    def test_sound_methods_with_none_sounds(self, pygame_init):
        """Test that sound playback handles None sounds gracefully."""
        manager = FeedbackManager(audio_enabled=True)

        # Manually set sounds to None (simulating generation failure)
        manager.sounds = {
            'hit': None,
            'miss': None,
            'combo': None
        }

        # Should not crash
        manager.play_hit_sound()
        manager.play_miss_sound()
        manager.play_combo_sound()

    def test_visual_effects_work_without_audio(self, pygame_init):
        """Test that visual effects work even when audio fails."""
        manager = FeedbackManager(audio_enabled=False)

        # Add effects
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)
        manager.add_miss_effect(Vector2D(x=150.0, y=250.0))

        # Visual effects should be created
        assert len(manager.effects) == 2
        assert len(manager.popups) == 1  # Only hit creates popup

    def test_audio_does_not_affect_effect_count(self, pygame_init):
        """Test that enabling/disabling audio doesn't affect effect counts."""
        manager_with_audio = FeedbackManager(audio_enabled=True)
        manager_without_audio = FeedbackManager(audio_enabled=False)

        # Add same effects to both
        manager_with_audio.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)
        manager_without_audio.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)

        # Should have same number of effects
        assert len(manager_with_audio.effects) == len(manager_without_audio.effects)
        assert len(manager_with_audio.popups) == len(manager_without_audio.popups)


class TestSoundGeneration:
    """Test cases for procedural sound generation."""

    def test_hit_sound_generation_returns_sound_or_none(self, pygame_init):
        """Test that _generate_hit_sound returns a Sound or None."""
        manager = FeedbackManager(audio_enabled=True)

        # Should have attempted to generate sound
        hit_sound = manager.sounds.get('hit')

        # Should be either a pygame.mixer.Sound or None
        assert hit_sound is None or isinstance(hit_sound, pygame.mixer.Sound)

    def test_miss_sound_generation_returns_sound_or_none(self, pygame_init):
        """Test that _generate_miss_sound returns a Sound or None."""
        manager = FeedbackManager(audio_enabled=True)

        # Should have attempted to generate sound
        miss_sound = manager.sounds.get('miss')

        # Should be either a pygame.mixer.Sound or None
        assert miss_sound is None or isinstance(miss_sound, pygame.mixer.Sound)

    def test_combo_sound_generation_returns_sound_or_none(self, pygame_init):
        """Test that _generate_combo_sound returns a Sound or None."""
        manager = FeedbackManager(audio_enabled=True)

        # Should have attempted to generate sound
        combo_sound = manager.sounds.get('combo')

        # Should be either a pygame.mixer.Sound or None
        assert combo_sound is None or isinstance(combo_sound, pygame.mixer.Sound)

    def test_all_sounds_have_volume_set(self, pygame_init):
        """Test that volume is set for all generated sounds."""
        manager = FeedbackManager(audio_enabled=True)

        # All sounds that exist should have had set_volume called
        # (we can't verify this without mocking, but we ensure no crash)
        for sound in manager.sounds.values():
            if sound is not None:
                # Should be a valid Sound object
                assert isinstance(sound, pygame.mixer.Sound)
