"""FruitSlice - Game Info

Fruit Ninja-style game with arcing targets and combo system.
Supports multiple pacing presets for different input devices.
"""

NAME = "Fruit Slice"
DESCRIPTION = "Hit arcing targets for points, avoid bombs. Pacing adapts to your input device."
VERSION = "1.0.0"
AUTHOR = "AMS Team"

ARGUMENTS = [
    # Game mode
    {
        'name': '--mode',
        'type': str,
        'default': 'classic',
        'help': 'Game mode: classic, zen (no bombs), arcade (timed)'
    },

    # Pacing preset
    {
        'name': '--pacing',
        'type': str,
        'default': 'throwing',
        'help': 'Pacing preset: archery (slow), throwing (medium), blaster (fast)'
    },

    # Timing overrides
    {
        'name': '--spawn-interval',
        'type': float,
        'default': None,
        'help': 'Seconds between spawns (overrides preset)'
    },
    {
        'name': '--arc-duration',
        'type': float,
        'default': None,
        'help': 'How long targets stay on screen (overrides preset)'
    },
    {
        'name': '--max-targets',
        'type': int,
        'default': None,
        'help': 'Maximum simultaneous targets (overrides preset)'
    },
    {
        'name': '--target-size',
        'type': int,
        'default': None,
        'help': 'Base target radius in pixels (overrides preset)'
    },

    # Game rules
    {
        'name': '--lives',
        'type': int,
        'default': 3,
        'help': 'Starting lives'
    },
    {
        'name': '--time-limit',
        'type': int,
        'default': None,
        'help': 'Time limit in seconds (arcade mode)'
    },
    {
        'name': '--no-bombs',
        'action': 'store_true',
        'default': False,
        'help': 'Disable bombs (zen mode)'
    },
    {
        'name': '--bomb-ratio',
        'type': float,
        'default': None,
        'help': 'Fraction of spawns that are bombs (0.0-1.0)'
    },

    # Combo
    {
        'name': '--combo-window',
        'type': float,
        'default': None,
        'help': 'Seconds before combo resets (longer for slow devices)'
    },

    # Physical ammo constraints
    {
        'name': '--quiver-size',
        'type': int,
        'default': None,
        'help': 'Shots per round before retrieval pause (None = unlimited)'
    },
    {
        'name': '--retrieval-pause',
        'type': int,
        'default': 30,
        'help': 'Seconds for retrieval between rounds (0 = manual ready)'
    },

    # Palette (for testing CV compatibility)
    {
        'name': '--palette',
        'type': str,
        'default': None,
        'help': 'Test palette: full, bw, warm, cool, limited, orange_dart'
    },
]


def get_game_mode(**kwargs):
    """Factory function to create game instance."""
    from games.FruitSlice.game_mode import FruitSliceMode

    # Handle mode shortcuts
    mode = kwargs.get('mode', 'classic')
    if mode == 'zen':
        kwargs['no_bombs'] = True

    # Map palette arg to palette_name
    if 'palette' in kwargs and kwargs['palette']:
        kwargs['palette_name'] = kwargs.pop('palette')

    return FruitSliceMode(**kwargs)
