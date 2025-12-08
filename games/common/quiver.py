"""
Common quiver/ammo management for AMS-integrated games.

Handles physical ammo constraints like arrow quivers, dart magazines, etc.
Supports retrieval pauses between rounds.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QuiverState:
    """
    Tracks ammo/shot count and retrieval pauses.

    For games with physical ammo constraints (archery quiver, dart magazine, etc.)
    """
    size: int = 0                    # Max shots per round (0 = unlimited)
    remaining: int = 0               # Shots left in current round
    retrieval_pause: float = 30.0    # Seconds for retrieval (0 = manual ready)
    retrieval_timer: float = 0.0     # Current retrieval countdown
    current_round: int = 1           # Current round number
    total_shots: int = 0             # Total shots fired this session

    def __post_init__(self):
        """Initialize remaining to size."""
        if self.size > 0 and self.remaining == 0:
            self.remaining = self.size

    @property
    def is_unlimited(self) -> bool:
        """Check if ammo is unlimited."""
        return self.size == 0

    @property
    def is_empty(self) -> bool:
        """Check if quiver is empty (needs retrieval)."""
        return not self.is_unlimited and self.remaining <= 0

    @property
    def is_manual_retrieval(self) -> bool:
        """Check if retrieval requires manual ready signal."""
        return self.retrieval_pause == 0

    def use_shot(self) -> bool:
        """
        Use a shot from the quiver.

        Returns:
            True if quiver is now empty (needs retrieval)
        """
        self.total_shots += 1
        if self.is_unlimited:
            return False
        self.remaining -= 1
        return self.remaining <= 0

    def start_retrieval(self):
        """Start retrieval countdown."""
        self.retrieval_timer = self.retrieval_pause

    def update_retrieval(self, dt: float) -> bool:
        """
        Update retrieval timer.

        Args:
            dt: Delta time in seconds

        Returns:
            True when retrieval is complete (ready to resume)
        """
        if self.is_manual_retrieval:
            return False  # Manual mode - never auto-completes
        self.retrieval_timer -= dt
        return self.retrieval_timer <= 0

    def end_retrieval(self):
        """Complete retrieval and refill quiver."""
        self.remaining = self.size
        self.current_round += 1
        self.retrieval_timer = 0.0

    def get_display_text(self) -> str:
        """Get text for UI display."""
        if self.is_unlimited:
            return ""
        return f"Arrows: {self.remaining}/{self.size}"

    def get_retrieval_text(self) -> str:
        """Get text for retrieval screen."""
        if self.is_manual_retrieval:
            return "Press SPACE when ready"
        return f"Retrieving arrows... {self.retrieval_timer:.0f}s"


def create_quiver(
    quiver_size: Optional[int] = None,
    retrieval_pause: Optional[float] = None
) -> Optional[QuiverState]:
    """
    Factory function to create quiver state.

    Args:
        quiver_size: Shots per round (None or 0 = unlimited, no quiver)
        retrieval_pause: Seconds for retrieval (0 = manual ready)

    Returns:
        QuiverState if quiver_size > 0, else None
    """
    if not quiver_size or quiver_size <= 0:
        return None

    return QuiverState(
        size=quiver_size,
        remaining=quiver_size,
        retrieval_pause=retrieval_pause if retrieval_pause is not None else 30.0
    )
