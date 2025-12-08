"""
Grouping - Game Info

Precision training game that measures shot grouping in real-time.
Required for auto-discovery by GameRegistry.
"""

# Game metadata
NAME = "Grouping"
DESCRIPTION = "Precision training - shrink the target by tightening your group."
VERSION = "1.0.0"
AUTHOR = "AMS Team"

# CLI argument definitions
ARGUMENTS = [
    {
        'name': '--method',
        'type': str,
        'default': 'centroid',
        'help': 'Grouping method: centroid, fixed (center+radius), or origin (fixed center, set radius)'
    },
    {
        'name': '--initial-radius',
        'type': int,
        'default': None,
        'help': 'Initial target radius in pixels'
    },
    {
        'name': '--min-radius',
        'type': int,
        'default': None,
        'help': 'Minimum target radius (smallest possible)'
    },
]


def get_game_mode(**kwargs):
    """
    Factory function to create a GroupingMode instance.

    Args:
        **kwargs: Game configuration options

    Returns:
        GroupingMode instance
    """
    from games.Grouping.game_mode import GroupingMode

    # Filter out None values
    game_kwargs = {k: v for k, v in kwargs.items() if v is not None}

    # Map CLI arg names to constructor params
    param_map = {
        'method': 'method',
        'initial_radius': 'initial_radius',
        'min_radius': 'min_radius',
    }

    constructor_kwargs = {}
    for cli_name, param_name in param_map.items():
        if cli_name in game_kwargs:
            constructor_kwargs[param_name] = game_kwargs[cli_name]

    return GroupingMode(**constructor_kwargs)
