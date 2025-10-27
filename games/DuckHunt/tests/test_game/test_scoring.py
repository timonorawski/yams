"""
Comprehensive tests for scoring system.

Tests both the ScoreData Pydantic model and the ScoreTracker class,
including validation, computed fields, immutability, and all state transitions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pydantic import ValidationError
from models import ScoreData
from game.scoring import ScoreTracker


# ============================================================================
# ScoreData Model Tests
# ============================================================================


class TestScoreDataValidation:
    """Test ScoreData model validation."""

    def test_scoredata_creation_with_defaults(self):
        """Test creating ScoreData with default values (all zeros)."""
        score = ScoreData()
        assert score.hits == 0
        assert score.misses == 0
        assert score.current_combo == 0
        assert score.max_combo == 0

    def test_scoredata_creation_with_values(self):
        """Test creating ScoreData with specific values."""
        score = ScoreData(hits=10, misses=5, current_combo=3, max_combo=7)
        assert score.hits == 10
        assert score.misses == 5
        assert score.current_combo == 3
        assert score.max_combo == 7

    def test_scoredata_negative_hits_validation(self):
        """Test that negative hits raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScoreData(hits=-1)
        assert 'non-negative' in str(exc_info.value).lower()

    def test_scoredata_negative_misses_validation(self):
        """Test that negative misses raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScoreData(misses=-1)
        assert 'non-negative' in str(exc_info.value).lower()

    def test_scoredata_negative_current_combo_validation(self):
        """Test that negative current_combo raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScoreData(current_combo=-1)
        assert 'non-negative' in str(exc_info.value).lower()

    def test_scoredata_negative_max_combo_validation(self):
        """Test that negative max_combo raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ScoreData(max_combo=-1)
        assert 'non-negative' in str(exc_info.value).lower()

    def test_scoredata_all_zeros_valid(self):
        """Test that all zero values are valid."""
        score = ScoreData(hits=0, misses=0, current_combo=0, max_combo=0)
        assert score.hits == 0
        assert score.misses == 0

    def test_scoredata_large_values(self):
        """Test that large values are accepted."""
        score = ScoreData(hits=999999, misses=999999, current_combo=100, max_combo=500)
        assert score.hits == 999999
        assert score.misses == 999999
        assert score.current_combo == 100
        assert score.max_combo == 500


class TestScoreDataComputedFields:
    """Test ScoreData computed fields."""

    def test_total_shots_zero(self):
        """Test total_shots with no shots taken."""
        score = ScoreData()
        assert score.total_shots == 0

    def test_total_shots_only_hits(self):
        """Test total_shots with only hits."""
        score = ScoreData(hits=10)
        assert score.total_shots == 10

    def test_total_shots_only_misses(self):
        """Test total_shots with only misses."""
        score = ScoreData(misses=5)
        assert score.total_shots == 5

    def test_total_shots_mixed(self):
        """Test total_shots with both hits and misses."""
        score = ScoreData(hits=7, misses=3)
        assert score.total_shots == 10

    def test_accuracy_zero_shots(self):
        """Test accuracy returns 0.0 when no shots taken (avoid division by zero)."""
        score = ScoreData()
        assert score.accuracy == 0.0

    def test_accuracy_all_hits(self):
        """Test accuracy is 1.0 when all shots hit."""
        score = ScoreData(hits=10, misses=0)
        assert score.accuracy == 1.0

    def test_accuracy_all_misses(self):
        """Test accuracy is 0.0 when all shots miss."""
        score = ScoreData(hits=0, misses=10)
        assert score.accuracy == 0.0

    def test_accuracy_mixed_shots(self):
        """Test accuracy calculation with mixed hits/misses."""
        score = ScoreData(hits=7, misses=3)
        assert score.accuracy == 0.7

    def test_accuracy_50_percent(self):
        """Test accuracy at exactly 50%."""
        score = ScoreData(hits=5, misses=5)
        assert score.accuracy == 0.5

    def test_accuracy_precision(self):
        """Test accuracy calculation maintains precision."""
        score = ScoreData(hits=2, misses=1)
        assert abs(score.accuracy - 0.6666666666666666) < 1e-10


class TestScoreDataImmutability:
    """Test ScoreData immutability (frozen model)."""

    def test_scoredata_is_frozen(self):
        """Test that ScoreData cannot be modified after creation."""
        score = ScoreData(hits=10, misses=5)

        with pytest.raises(ValidationError):
            score.hits = 20  # Should raise error

    def test_scoredata_computed_fields_not_settable(self):
        """Test that computed fields cannot be set."""
        score = ScoreData(hits=10, misses=5)

        # Computed fields shouldn't be settable even if we try
        with pytest.raises((ValidationError, AttributeError)):
            score.total_shots = 100

    def test_scoredata_independence(self):
        """Test that creating new ScoreData doesn't affect existing instances."""
        score1 = ScoreData(hits=5)
        score2 = ScoreData(hits=10)

        assert score1.hits == 5
        assert score2.hits == 10
        # They should be independent
        assert score1 is not score2


# ============================================================================
# ScoreTracker Class Tests
# ============================================================================


class TestScoreTrackerInitialization:
    """Test ScoreTracker initialization."""

    def test_scoretracker_default_initialization(self):
        """Test creating ScoreTracker with default values."""
        tracker = ScoreTracker()
        stats = tracker.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.current_combo == 0
        assert stats.max_combo == 0

    def test_scoretracker_initialization_with_score(self):
        """Test creating ScoreTracker with existing ScoreData."""
        initial_score = ScoreData(hits=5, misses=2, current_combo=3, max_combo=5)
        tracker = ScoreTracker(score=initial_score)
        stats = tracker.get_stats()
        assert stats.hits == 5
        assert stats.misses == 2
        assert stats.current_combo == 3
        assert stats.max_combo == 5


class TestScoreTrackerRecordHit:
    """Test ScoreTracker.record_hit() method."""

    def test_record_first_hit(self):
        """Test recording the first hit."""
        tracker = ScoreTracker()
        tracker2 = tracker.record_hit()

        stats = tracker2.get_stats()
        assert stats.hits == 1
        assert stats.misses == 0
        assert stats.current_combo == 1
        assert stats.max_combo == 1

    def test_record_multiple_hits(self):
        """Test recording multiple consecutive hits."""
        tracker = ScoreTracker()
        tracker2 = tracker.record_hit()
        tracker3 = tracker2.record_hit()
        tracker4 = tracker3.record_hit()

        stats = tracker4.get_stats()
        assert stats.hits == 3
        assert stats.misses == 0
        assert stats.current_combo == 3
        assert stats.max_combo == 3

    def test_record_hit_updates_max_combo(self):
        """Test that max_combo is updated when current_combo exceeds it."""
        tracker = ScoreTracker()
        tracker2 = tracker.record_hit().record_hit().record_hit()

        stats = tracker2.get_stats()
        assert stats.current_combo == 3
        assert stats.max_combo == 3

    def test_record_hit_does_not_decrease_max_combo(self):
        """Test that max_combo doesn't decrease when combo is broken and rebuilt."""
        tracker = ScoreTracker()
        # Build up a combo
        tracker2 = tracker.record_hit().record_hit().record_hit()
        assert tracker2.get_stats().max_combo == 3

        # Break combo
        tracker3 = tracker2.record_miss()
        assert tracker3.get_stats().current_combo == 0
        assert tracker3.get_stats().max_combo == 3  # Still 3

        # Build new combo
        tracker4 = tracker3.record_hit().record_hit()
        assert tracker4.get_stats().current_combo == 2
        assert tracker4.get_stats().max_combo == 3  # Still 3, not decreased


class TestScoreTrackerRecordMiss:
    """Test ScoreTracker.record_miss() method."""

    def test_record_first_miss(self):
        """Test recording the first miss."""
        tracker = ScoreTracker()
        tracker2 = tracker.record_miss()

        stats = tracker2.get_stats()
        assert stats.hits == 0
        assert stats.misses == 1
        assert stats.current_combo == 0
        assert stats.max_combo == 0

    def test_record_miss_resets_combo(self):
        """Test that recording a miss resets the current combo."""
        tracker = ScoreTracker()
        # Build up a combo
        tracker2 = tracker.record_hit().record_hit().record_hit()
        assert tracker2.get_stats().current_combo == 3

        # Record a miss
        tracker3 = tracker2.record_miss()
        stats = tracker3.get_stats()
        assert stats.current_combo == 0
        assert stats.max_combo == 3  # Max combo preserved
        assert stats.misses == 1

    def test_record_multiple_misses(self):
        """Test recording multiple misses."""
        tracker = ScoreTracker()
        tracker2 = tracker.record_miss().record_miss().record_miss()

        stats = tracker2.get_stats()
        assert stats.hits == 0
        assert stats.misses == 3
        assert stats.current_combo == 0

    def test_record_miss_preserves_max_combo(self):
        """Test that max_combo is preserved when combo is broken."""
        tracker = ScoreTracker()
        tracker2 = tracker.record_hit().record_hit().record_hit().record_hit().record_hit()
        assert tracker2.get_stats().max_combo == 5

        tracker3 = tracker2.record_miss()
        assert tracker3.get_stats().max_combo == 5


class TestScoreTrackerComboTracking:
    """Test combo tracking logic."""

    def test_combo_increments_on_consecutive_hits(self):
        """Test combo increments on each consecutive hit."""
        tracker = ScoreTracker()

        tracker1 = tracker.record_hit()
        assert tracker1.get_stats().current_combo == 1

        tracker2 = tracker1.record_hit()
        assert tracker2.get_stats().current_combo == 2

        tracker3 = tracker2.record_hit()
        assert tracker3.get_stats().current_combo == 3

    def test_max_combo_tracks_highest(self):
        """Test max_combo tracks the highest combo achieved."""
        tracker = ScoreTracker()

        # First combo of 3
        tracker2 = tracker.record_hit().record_hit().record_hit()
        assert tracker2.get_stats().max_combo == 3

        # Break combo
        tracker3 = tracker2.record_miss()
        assert tracker3.get_stats().max_combo == 3

        # New combo of 2 (doesn't exceed max)
        tracker4 = tracker3.record_hit().record_hit()
        assert tracker4.get_stats().max_combo == 3

        # New combo of 5 (exceeds previous max)
        tracker5 = tracker4.record_hit().record_hit().record_hit()
        assert tracker5.get_stats().current_combo == 5
        assert tracker5.get_stats().max_combo == 5

    def test_combo_resets_to_zero_on_miss(self):
        """Test combo resets to exactly zero on miss."""
        tracker = ScoreTracker()
        tracker2 = tracker.record_hit().record_hit().record_hit()
        assert tracker2.get_stats().current_combo == 3

        tracker3 = tracker2.record_miss()
        assert tracker3.get_stats().current_combo == 0


class TestScoreTrackerImmutability:
    """Test ScoreTracker immutability pattern."""

    def test_record_hit_returns_new_instance(self):
        """Test that record_hit returns a new instance."""
        tracker1 = ScoreTracker()
        tracker2 = tracker1.record_hit()

        assert tracker1 is not tracker2
        assert tracker1.get_stats().hits == 0
        assert tracker2.get_stats().hits == 1

    def test_record_miss_returns_new_instance(self):
        """Test that record_miss returns a new instance."""
        tracker1 = ScoreTracker()
        tracker2 = tracker1.record_miss()

        assert tracker1 is not tracker2
        assert tracker1.get_stats().misses == 0
        assert tracker2.get_stats().misses == 1

    def test_original_tracker_unchanged_after_hit(self):
        """Test that original tracker is unchanged after recording hit."""
        tracker1 = ScoreTracker()
        tracker2 = tracker1.record_hit()
        tracker3 = tracker2.record_hit()

        # Original trackers should remain unchanged
        assert tracker1.get_stats().hits == 0
        assert tracker2.get_stats().hits == 1
        assert tracker3.get_stats().hits == 2

    def test_original_tracker_unchanged_after_miss(self):
        """Test that original tracker is unchanged after recording miss."""
        tracker1 = ScoreTracker()
        tracker2 = tracker1.record_hit().record_hit()
        tracker3 = tracker2.record_miss()

        # Tracker2 should still have its combo
        assert tracker2.get_stats().current_combo == 2
        # Tracker3 should have reset combo
        assert tracker3.get_stats().current_combo == 0


class TestScoreTrackerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_large_number_of_hits(self):
        """Test handling very large numbers of hits."""
        tracker = ScoreTracker()

        # Record 1000 hits
        for _ in range(1000):
            tracker = tracker.record_hit()

        stats = tracker.get_stats()
        assert stats.hits == 1000
        assert stats.current_combo == 1000
        assert stats.max_combo == 1000

    def test_very_large_number_of_misses(self):
        """Test handling very large numbers of misses."""
        tracker = ScoreTracker()

        # Record 1000 misses
        for _ in range(1000):
            tracker = tracker.record_miss()

        stats = tracker.get_stats()
        assert stats.misses == 1000
        assert stats.current_combo == 0

    def test_alternating_hits_and_misses(self):
        """Test alternating pattern of hits and misses."""
        tracker = ScoreTracker()

        # Alternate 10 times
        for i in range(10):
            tracker = tracker.record_hit()
            assert tracker.get_stats().current_combo == 1
            tracker = tracker.record_miss()
            assert tracker.get_stats().current_combo == 0

        stats = tracker.get_stats()
        assert stats.hits == 10
        assert stats.misses == 10
        assert stats.current_combo == 0
        assert stats.max_combo == 1  # Never got past 1

    def test_combo_exactly_one(self):
        """Test combo of exactly one."""
        tracker = ScoreTracker()
        tracker2 = tracker.record_hit()

        assert tracker2.get_stats().current_combo == 1
        assert tracker2.get_stats().max_combo == 1

    def test_accuracy_after_many_operations(self):
        """Test accuracy calculation remains correct after many operations."""
        tracker = ScoreTracker()

        # 70 hits, 30 misses
        for _ in range(70):
            tracker = tracker.record_hit()
        for _ in range(30):
            tracker = tracker.record_miss()

        stats = tracker.get_stats()
        assert stats.hits == 70
        assert stats.misses == 30
        assert stats.total_shots == 100
        assert stats.accuracy == 0.7


class TestScoreTrackerGetStats:
    """Test ScoreTracker.get_stats() method."""

    def test_get_stats_returns_scoredata(self):
        """Test that get_stats returns a ScoreData instance."""
        tracker = ScoreTracker()
        stats = tracker.get_stats()
        assert isinstance(stats, ScoreData)

    def test_get_stats_returns_immutable_data(self):
        """Test that get_stats returns immutable data."""
        tracker = ScoreTracker()
        stats = tracker.get_stats()

        # Should not be able to modify the returned stats
        with pytest.raises(ValidationError):
            stats.hits = 999

    def test_get_stats_reflects_current_state(self):
        """Test that get_stats reflects the current state."""
        tracker = ScoreTracker()

        tracker2 = tracker.record_hit()
        assert tracker2.get_stats().hits == 1

        tracker3 = tracker2.record_hit()
        assert tracker3.get_stats().hits == 2

        tracker4 = tracker3.record_miss()
        assert tracker4.get_stats().misses == 1


class TestScoreTrackerStringRepresentation:
    """Test ScoreTracker string representations."""

    def test_str_representation(self):
        """Test __str__ method."""
        tracker = ScoreTracker()
        tracker2 = tracker.record_hit().record_hit()

        str_repr = str(tracker2)
        assert isinstance(str_repr, str)
        # Should contain score information
        assert 'hits=2' in str_repr.lower() or '2' in str_repr

    def test_repr_representation(self):
        """Test __repr__ method."""
        tracker = ScoreTracker()
        repr_str = repr(tracker)
        assert isinstance(repr_str, str)
        assert 'ScoreTracker' in repr_str


class TestScoreTrackerComplexScenarios:
    """Test complex realistic gameplay scenarios."""

    def test_perfect_game(self):
        """Test a perfect game (all hits, no misses)."""
        tracker = ScoreTracker()

        # 20 perfect hits
        for _ in range(20):
            tracker = tracker.record_hit()

        stats = tracker.get_stats()
        assert stats.hits == 20
        assert stats.misses == 0
        assert stats.accuracy == 1.0
        assert stats.current_combo == 20
        assert stats.max_combo == 20

    def test_terrible_game(self):
        """Test a terrible game (all misses, no hits)."""
        tracker = ScoreTracker()

        # 20 misses
        for _ in range(20):
            tracker = tracker.record_miss()

        stats = tracker.get_stats()
        assert stats.hits == 0
        assert stats.misses == 20
        assert stats.accuracy == 0.0
        assert stats.current_combo == 0
        assert stats.max_combo == 0

    def test_recovery_after_bad_start(self):
        """Test recovery after a bad start."""
        tracker = ScoreTracker()

        # Start with 5 misses
        for _ in range(5):
            tracker = tracker.record_miss()

        # Then hit 15 in a row
        for _ in range(15):
            tracker = tracker.record_hit()

        stats = tracker.get_stats()
        assert stats.hits == 15
        assert stats.misses == 5
        assert stats.total_shots == 20
        assert stats.accuracy == 0.75
        assert stats.current_combo == 15
        assert stats.max_combo == 15

    def test_multiple_combo_streaks(self):
        """Test tracking across multiple combo streaks."""
        tracker = ScoreTracker()

        # First streak: 5 hits
        for _ in range(5):
            tracker = tracker.record_hit()
        assert tracker.get_stats().max_combo == 5

        # Break it
        tracker = tracker.record_miss()

        # Second streak: 3 hits (doesn't beat max)
        for _ in range(3):
            tracker = tracker.record_hit()
        assert tracker.get_stats().max_combo == 5
        assert tracker.get_stats().current_combo == 3

        # Break it
        tracker = tracker.record_miss()

        # Third streak: 10 hits (new max)
        for _ in range(10):
            tracker = tracker.record_hit()
        assert tracker.get_stats().max_combo == 10
        assert tracker.get_stats().current_combo == 10

        stats = tracker.get_stats()
        assert stats.hits == 18
        assert stats.misses == 2
        assert stats.max_combo == 10


# ============================================================================
# Integration Tests
# ============================================================================


class TestScoreDataAndTrackerIntegration:
    """Test integration between ScoreData and ScoreTracker."""

    def test_tracker_uses_validated_scoredata(self):
        """Test that tracker properly uses validated ScoreData."""
        # Create valid ScoreData
        score = ScoreData(hits=5, misses=3, current_combo=2, max_combo=5)
        tracker = ScoreTracker(score=score)

        # Verify tracker has correct state
        stats = tracker.get_stats()
        assert stats.hits == 5
        assert stats.misses == 3
        assert stats.current_combo == 2
        assert stats.max_combo == 5

    def test_tracker_operations_maintain_scoredata_invariants(self):
        """Test that all tracker operations maintain ScoreData invariants."""
        tracker = ScoreTracker()

        # Perform various operations
        tracker = tracker.record_hit().record_hit().record_miss()
        tracker = tracker.record_hit().record_hit().record_hit()

        stats = tracker.get_stats()

        # Verify invariants
        assert stats.hits >= 0
        assert stats.misses >= 0
        assert stats.current_combo >= 0
        assert stats.max_combo >= 0
        assert stats.max_combo >= stats.current_combo
        assert stats.total_shots == stats.hits + stats.misses
        assert 0.0 <= stats.accuracy <= 1.0


# ============================================================================
# Render Tests (with mocking)
# ============================================================================


class TestScoreTrackerRender:
    """Test ScoreTracker.render() method with mocked pygame."""

    @patch('game.scoring.pygame')
    def test_render_basic(self, mock_pygame):
        """Test basic render functionality."""
        # Setup mocks
        mock_font = MagicMock()
        mock_pygame.font.Font.return_value = mock_font
        mock_text_surface = MagicMock()
        mock_font.render.return_value = mock_text_surface
        mock_screen = MagicMock()

        # Create tracker with some data
        tracker = ScoreTracker()
        tracker = tracker.record_hit().record_hit().record_miss()

        # Render
        tracker.render(mock_screen)

        # Verify font was created
        mock_pygame.font.Font.assert_called_once()

        # Verify text was rendered (should render multiple lines)
        assert mock_font.render.call_count >= 4  # At least hits, misses, accuracy, combo

        # Verify text was blitted to screen
        assert mock_screen.blit.call_count >= 4

    @patch('game.scoring.pygame')
    def test_render_custom_position(self, mock_pygame):
        """Test render with custom position."""
        # Setup mocks
        mock_font = MagicMock()
        mock_pygame.font.Font.return_value = mock_font
        mock_text_surface = MagicMock()
        mock_font.render.return_value = mock_text_surface
        mock_screen = MagicMock()

        tracker = ScoreTracker()

        # Render at custom position
        tracker.render(mock_screen, x=100, y=50)

        # Verify screen.blit was called
        assert mock_screen.blit.called

    @patch('game.scoring.pygame')
    def test_render_with_max_combo(self, mock_pygame):
        """Test render includes max combo when it exists."""
        # Setup mocks
        mock_font = MagicMock()
        mock_pygame.font.Font.return_value = mock_font
        mock_text_surface = MagicMock()
        mock_font.render.return_value = mock_text_surface
        mock_screen = MagicMock()

        # Create tracker with max combo
        tracker = ScoreTracker()
        tracker = tracker.record_hit().record_hit().record_hit()
        tracker = tracker.record_miss()  # Break combo but preserve max_combo

        # Render
        tracker.render(mock_screen)

        # Should render 5 lines (hits, misses, accuracy, combo, best combo)
        assert mock_font.render.call_count == 5
        assert mock_screen.blit.call_count == 5

    @patch('game.scoring.pygame')
    def test_render_without_max_combo(self, mock_pygame):
        """Test render excludes max combo when it's zero."""
        # Setup mocks
        mock_font = MagicMock()
        mock_pygame.font.Font.return_value = mock_font
        mock_text_surface = MagicMock()
        mock_font.render.return_value = mock_text_surface
        mock_screen = MagicMock()

        # Create tracker with no combo
        tracker = ScoreTracker()

        # Render
        tracker.render(mock_screen)

        # Should render 4 lines (hits, misses, accuracy, combo) - no best combo
        assert mock_font.render.call_count == 4
        assert mock_screen.blit.call_count == 4

    @patch('game.scoring.pygame')
    def test_render_fallback_font(self, mock_pygame):
        """Test render falls back to system font if Font fails."""
        # Make Font raise exception, but SysFont succeeds
        mock_pygame.font.Font.side_effect = Exception("Font not found")
        mock_sysfont = MagicMock()
        mock_pygame.font.SysFont.return_value = mock_sysfont
        mock_text_surface = MagicMock()
        mock_sysfont.render.return_value = mock_text_surface
        mock_screen = MagicMock()

        tracker = ScoreTracker()

        # Should not raise exception, should use fallback
        tracker.render(mock_screen)

        # Verify fallback was used
        mock_pygame.font.SysFont.assert_called_once()
        assert mock_sysfont.render.called

    @patch('game.scoring.pygame')
    def test_render_displays_correct_stats(self, mock_pygame):
        """Test that render displays correct statistics."""
        # Setup mocks
        mock_font = MagicMock()
        mock_pygame.font.Font.return_value = mock_font
        mock_text_surface = MagicMock()
        mock_font.render.return_value = mock_text_surface
        mock_screen = MagicMock()

        # Create tracker with specific data
        tracker = ScoreTracker()
        tracker = tracker.record_hit().record_hit().record_hit()
        tracker = tracker.record_miss()

        # Render
        tracker.render(mock_screen)

        # Check that render was called with correct text
        render_calls = [call[0][0] for call in mock_font.render.call_args_list]

        # Should contain stats (exact format may vary)
        text_all = ' '.join(render_calls).lower()
        assert 'hits' in text_all or '3' in text_all
        assert 'misses' in text_all or '1' in text_all
        assert 'accuracy' in text_all
        assert 'combo' in text_all
