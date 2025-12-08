"""
Balloon Pop - Game Info

This file defines the game's metadata and provides the factory function
for creating game instances. Required for auto-discovery by GameRegistry.
"""

# Game metadata
NAME = "Balloon Pop"
DESCRIPTION = "Pop balloons as they float up! Don't let them escape."
VERSION = "1.0.0"
AUTHOR = "AMS Team"

# CLI argument definitions (optional, for ams_game.py)
ARGUMENTS = [
    {
        'name': '--spawn-rate',
        'type': float,
        'default': None,
        'help': 'Balloon spawn rate in seconds'
    },
    {
        'name': '--max-escaped',
        'type': int,
        'default': None,
        'help': 'Max escaped balloons before game over'
    },
    {
        'name': '--target-pops',
        'type': int,
        'default': None,
        'help': 'Pops needed to win (0=endless)'
    },
]


def get_game_mode(**kwargs):
    """
    Factory function to create a BalloonPopMode instance.

    Args:
        **kwargs: Game configuration options
            - spawn_rate: Seconds between spawns
            - max_escaped: Max escaped before game over
            - target_pops: Pops to win (0=endless)

    Returns:
        BalloonPopMode instance
    """
    from games.BalloonPop.game_mode import BalloonPopMode

    # Filter out None values
    game_kwargs = {k: v for k, v in kwargs.items() if v is not None}

    # Map CLI arg names to constructor params
    param_map = {
        'spawn_rate': 'spawn_rate',
        'max_escaped': 'max_escaped',
        'target_pops': 'target_pops',
    }

    constructor_kwargs = {}
    for cli_name, param_name in param_map.items():
        if cli_name in game_kwargs:
            constructor_kwargs[param_name] = game_kwargs[cli_name]

    return BalloonPopMode(**constructor_kwargs)
