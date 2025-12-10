"""Game info factory for BrickBreaker NextGen."""

from .game_mode import BrickBreakerNGMode


def get_game_mode():
    """Factory function for game registry."""
    return BrickBreakerNGMode
