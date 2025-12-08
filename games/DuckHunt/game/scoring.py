"""
Score tracking system for Duck Hunt game.

This module implements the ScoreTracker class which manages game scoring
using an immutable state pattern. All score operations return new instances
rather than modifying existing state.

Examples:
    >>> tracker = ScoreTracker()
    >>> tracker2 = tracker.record_hit()
    >>> tracker2.get_stats().hits
    1
    >>> tracker3 = tracker2.record_hit().record_hit()
    >>> tracker3.get_stats().current_combo
    3
"""

from typing import Optional
import pygame
from models import ScoreData
from games.DuckHunt.config import Colors, Fonts


class ScoreTracker:
    """Tracks scoring with immutable state pattern.

    Uses the ScoreData Pydantic model for validated, immutable score state.
    All operations return new ScoreTracker instances rather than modifying
    the existing tracker in place.

    This functional approach makes the code easier to test, debug, and reason
    about, as there are no side effects or hidden state mutations.

    Attributes:
        _score: Internal ScoreData model (private, immutable)

    Examples:
        >>> tracker = ScoreTracker()
        >>> tracker2 = tracker.record_hit()
        >>> tracker2.get_stats().hits
        1
        >>> tracker.get_stats().hits  # Original unchanged
        0
        >>> tracker3 = tracker2.record_miss()
        >>> tracker3.get_stats().current_combo  # Combo reset
        0
    """

    def __init__(self, score: Optional[ScoreData] = None):
        """Initialize score tracker.

        Args:
            score: Initial score data. If None, starts with zeros.
        """
        self._score = score if score is not None else ScoreData()

    def record_hit(self) -> 'ScoreTracker':
        """Record a successful hit.

        Returns a new ScoreTracker instance with:
        - hits incremented by 1
        - current_combo incremented by 1
        - max_combo updated if current_combo exceeds it

        Returns:
            New ScoreTracker instance with updated state

        Examples:
            >>> tracker = ScoreTracker()
            >>> tracker2 = tracker.record_hit()
            >>> tracker2.get_stats().hits
            1
            >>> tracker2.get_stats().current_combo
            1
        """
        new_combo = self._score.current_combo + 1
        new_max_combo = max(new_combo, self._score.max_combo)

        new_score = ScoreData(
            hits=self._score.hits + 1,
            misses=self._score.misses,
            current_combo=new_combo,
            max_combo=new_max_combo
        )
        return ScoreTracker(new_score)

    def record_miss(self) -> 'ScoreTracker':
        """Record a missed shot.

        Returns a new ScoreTracker instance with:
        - misses incremented by 1
        - current_combo reset to 0
        - max_combo unchanged

        Returns:
            New ScoreTracker instance with updated state

        Examples:
            >>> tracker = ScoreTracker()
            >>> tracker2 = tracker.record_hit().record_hit()
            >>> tracker2.get_stats().current_combo
            2
            >>> tracker3 = tracker2.record_miss()
            >>> tracker3.get_stats().current_combo
            0
            >>> tracker3.get_stats().misses
            1
        """
        new_score = ScoreData(
            hits=self._score.hits,
            misses=self._score.misses + 1,
            current_combo=0,  # Reset combo on miss
            max_combo=self._score.max_combo
        )
        return ScoreTracker(new_score)

    def get_stats(self) -> ScoreData:
        """Get current score data.

        Returns:
            Immutable ScoreData instance with current statistics

        Examples:
            >>> tracker = ScoreTracker()
            >>> stats = tracker.get_stats()
            >>> stats.hits
            0
            >>> stats.total_shots
            0
        """
        return self._score

    def render(self, screen: pygame.Surface, x: int = 10, y: int = 10) -> None:
        """Render score display on screen.

        Displays current score statistics including hits, misses, accuracy,
        and current combo streak.

        Args:
            screen: Pygame surface to render on
            x: X coordinate for score display (default: 10)
            y: Y coordinate for score display (default: 10)

        Examples:
            >>> screen = pygame.display.set_mode((800, 600))
            >>> tracker = ScoreTracker()
            >>> tracker.render(screen)  # Draws score at (10, 10)
            >>> tracker.render(screen, x=100, y=50)  # Custom position
        """
        # Create font if not already available
        try:
            font = pygame.font.Font(None, Fonts.SCORE_SIZE)
        except Exception:
            # Fallback if custom font fails
            font = pygame.font.SysFont('monospace', Fonts.SCORE_SIZE)

        # Prepare score text
        stats = self._score
        lines = [
            f"Hits: {stats.hits}",
            f"Misses: {stats.misses}",
            f"Accuracy: {stats.accuracy:.1%}",
            f"Combo: {stats.current_combo}"
        ]

        # Add max combo if it's greater than 0
        if stats.max_combo > 0:
            lines.append(f"Best Combo: {stats.max_combo}")

        # Render each line
        line_height = Fonts.SCORE_SIZE + 5  # Add some spacing
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, Colors.SCORE_TEXT)
            screen.blit(text_surface, (x, y + i * line_height))

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"ScoreTracker({self._score!r})"

    def __str__(self) -> str:
        """User-friendly string representation."""
        return str(self._score)
