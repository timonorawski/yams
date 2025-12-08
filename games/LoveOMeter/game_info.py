"""Game info factory for LoveOMeter."""


def get_game_mode(**kwargs):
    """Factory function to create game mode instance."""
    from games.LoveOMeter.game_mode import LoveOMeterMode
    return LoveOMeterMode(**kwargs)
