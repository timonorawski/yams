"""DuckHunt - Game Info (factory only).

Metadata and arguments are now defined as class attributes on DuckHuntMode.
This file only provides the factory function for backward compatibility.
"""


def get_game_mode(**kwargs):
    """Factory function to create game instance.

    The registry calls this with CLI arguments.
    """
    from games.DuckHunt.game_mode import DuckHuntMode
    return DuckHuntMode(**kwargs)
