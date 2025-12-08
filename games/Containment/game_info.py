"""Containment - Game Info

Adversarial geometry-building game where you place deflectors to contain
a ball trying to escape through gaps.
"""

NAME = "Containment"
DESCRIPTION = "Build walls to contain the ball. Direct hits make it faster!"
VERSION = "1.0.0"
AUTHOR = "AMS Team"

ARGUMENTS = [
    # Pacing (standard AMS parameter)
    {
        'name': '--pacing',
        'type': str,
        'default': 'throwing',
        'help': 'Pacing preset: archery, throwing, blaster'
    },

    # Game-specific difficulty
    {
        'name': '--tempo',
        'type': str,
        'default': 'mid',
        'help': 'Tempo preset: zen, mid, wild (ball aggression)'
    },
    {
        'name': '--ai',
        'type': str,
        'default': 'dumb',
        'help': 'AI level: dumb, reactive, strategic'
    },

    # Game mode
    {
        'name': '--time-limit',
        'type': int,
        'default': 60,
        'help': 'Seconds to survive (0 = endless)'
    },
    {
        'name': '--gap-count',
        'type': int,
        'default': None,
        'help': 'Number of gaps (overrides preset)'
    },

    # Physical constraints (standard AMS parameters)
    {
        'name': '--max-deflectors',
        'type': int,
        'default': None,
        'help': 'Maximum deflectors allowed (None = unlimited)'
    },
    {
        'name': '--quiver-size',
        'type': int,
        'default': None,
        'help': 'Shots before retrieval pause'
    },
    {
        'name': '--retrieval-pause',
        'type': int,
        'default': 30,
        'help': 'Seconds for retrieval (0 = manual)'
    },

    # Palette (standard AMS parameter)
    {
        'name': '--palette',
        'type': str,
        'default': None,
        'help': 'Test palette: full, bw, warm, cool, etc.'
    },
]


def get_game_mode(**kwargs):
    """Factory function to create game instance."""
    from games.Containment.game_mode import ContainmentMode

    # Map CLI arg names to constructor params
    param_map = {
        'pacing': 'pacing',
        'tempo': 'tempo',
        'ai': 'ai',
        'time_limit': 'time_limit',
        'gap_count': 'gap_count',
        'max_deflectors': 'max_deflectors',
        'quiver_size': 'quiver_size',
        'retrieval_pause': 'retrieval_pause',
        'palette': 'palette_name',
    }

    constructor_kwargs = {}
    for cli_name, param_name in param_map.items():
        if cli_name in kwargs and kwargs[cli_name] is not None:
            constructor_kwargs[param_name] = kwargs[cli_name]

    return ContainmentMode(**constructor_kwargs)
