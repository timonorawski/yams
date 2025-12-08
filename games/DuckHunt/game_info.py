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
    {
        'name': '--pacing',
        'type': str,
        'default': None,
        'choices': ['archery', 'throwing', 'blaster'],
        'help': 'Pacing preset for device speed (archery/throwing/blaster)'
    },
    {
        'name': '--quiver-size',
        'type': int,
        'default': None,
        'help': 'Shots per round (0 = unlimited)'
    },
    {
        'name': '--retrieval-pause',
        'type': float,
        'default': None,
        'help': 'Seconds for ammo retrieval (0 = manual ready with SPACE)'
    },
    {
        'name': '--palette',
        'type': str,
        'default': None,
        'help': 'Test palette name (full/bw/warm/cool/etc) for standalone mode'
    },
]


def get_game_mode(**kwargs):
    """
    Factory function to create a ClassicMode instance.

    Args:
        **kwargs: Game configuration options
            - mode: Game mode config name (e.g., 'classic_archery')
            - pacing: Pacing preset ('archery', 'throwing', 'blaster')
            - quiver_size: Shots per round (None/0 = unlimited)
            - retrieval_pause: Seconds for retrieval (0 = manual)
            - palette: Test palette name for standalone mode

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
    pacing = kwargs.get('pacing')
    quiver_size = kwargs.get('quiver_size')
    retrieval_pause = kwargs.get('retrieval_pause')
    palette = kwargs.get('palette')

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
            audio_enabled=True,
            pacing=pacing,
            quiver_size=quiver_size,
            retrieval_pause=retrieval_pause,
            palette_name=palette,
        )
    else:
        return ClassicMode(
            max_misses=max_misses,
            target_score=target_score,
            audio_enabled=True,
            pacing=pacing,
            quiver_size=quiver_size,
            retrieval_pause=retrieval_pause,
            palette_name=palette,
        )
