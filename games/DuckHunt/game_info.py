"""
Duck Hunt - Game Info

This file defines the game's metadata and provides the factory function
for creating game instances. Required for auto-discovery by GameRegistry.
"""

import os

# Game metadata
NAME = "Duck Hunt"
DESCRIPTION = "Classic duck hunting game with moving targets and combos."
VERSION = "1.0.0"
AUTHOR = "AMS Team"

# CLI argument definitions (optional, for ams_game.py)
ARGUMENTS = [
    {
        'name': '--mode',
        'type': str,
        'default': 'classic_archery',
        'help': 'Game mode config file (without .yaml extension)'
    },
]


def get_game_mode(**kwargs):
    """
    Factory function to create a ClassicMode instance.

    Args:
        **kwargs: Game configuration options
            - mode: Game mode config name (e.g., 'classic_archery')

    Returns:
        ClassicMode instance
    """
    import sys
    # Ensure DuckHunt is on path for its imports
    duckhunt_path = os.path.dirname(__file__)
    if duckhunt_path not in sys.path:
        sys.path.insert(0, duckhunt_path)

    from game.modes.classic import ClassicMode
    from game.mode_loader import load_game_mode_config

    mode_name = kwargs.get('mode', 'classic_archery')

    # Find mode file
    mode_path = os.path.join(os.path.dirname(__file__), 'modes', f'{mode_name}.yaml')
    if not os.path.exists(mode_path):
        # Try from project root
        mode_path = os.path.join('games', 'DuckHunt', 'modes', f'{mode_name}.yaml')

    if os.path.exists(mode_path):
        mode_config = load_game_mode_config(mode_path)
        max_misses = mode_config.rules.max_misses
        target_score = mode_config.rules.score_target
        initial_speed = None
        if mode_config.levels and len(mode_config.levels) > 0:
            initial_speed = mode_config.levels[0].target.speed
    else:
        # Defaults if mode file not found
        max_misses = 10
        target_score = None
        initial_speed = None

    if initial_speed:
        return ClassicMode(
            max_misses=max_misses,
            target_score=target_score,
            initial_speed=initial_speed,
            audio_enabled=True
        )
    else:
        return ClassicMode(
            max_misses=max_misses,
            target_score=target_score,
            audio_enabled=True
        )
