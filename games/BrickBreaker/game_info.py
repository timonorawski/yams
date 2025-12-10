"""BrickBreaker - Game Info for Registry.

Required for auto-discovery by GameRegistry.
"""


def get_game_mode(**kwargs):
    """Factory function to create BrickBreaker game instance.

    Args:
        **kwargs: Game configuration options (from CLI or AMS)

    Returns:
        BrickBreakerMode instance
    """
    from games.BrickBreaker.game_mode import BrickBreakerMode
    return BrickBreakerMode(**kwargs)
