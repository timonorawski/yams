"""GrowingTargets - Game Info

Speed/accuracy tradeoff game where targets grow over time.
Hit them small for maximum points, or wait for an easier shot.
"""

NAME = "Growing Targets"
DESCRIPTION = "Targets grow over time - hit small for max points, or wait for easier shot"
VERSION = "1.0.0"
AUTHOR = "AMS Team"

ARGUMENTS = [
    {
        'name': '--pacing',
        'type': str,
        'default': 'throwing',
        'help': 'Pacing preset: archery (slow), throwing (medium), blaster (fast)'
    },
    {
        'name': '--quiver-size',
        'type': int,
        'default': None,
        'help': 'Arrows per round (0 or None = unlimited)'
    },
    {
        'name': '--retrieval-pause',
        'type': float,
        'default': 30.0,
        'help': 'Seconds to retrieve arrows (0 = manual with SPACE)'
    },
    {
        'name': '--palette',
        'type': str,
        'default': None,
        'help': 'Color palette name (full, bw, warm, cool, etc.)'
    },
    {
        'name': '--spawn-rate',
        'type': float,
        'default': None,
        'help': 'Seconds between target spawns (overrides pacing preset)'
    },
    {
        'name': '--max-targets',
        'type': int,
        'default': None,
        'help': 'Maximum simultaneous targets (overrides pacing preset)'
    },
    {
        'name': '--growth-rate',
        'type': float,
        'default': None,
        'help': 'Growth rate (pixels per second) (overrides pacing preset)'
    },
    {
        'name': '--start-size',
        'type': int,
        'default': None,
        'help': 'Initial target radius (overrides pacing preset)'
    },
    {
        'name': '--max-size',
        'type': int,
        'default': None,
        'help': 'Maximum target radius (overrides pacing preset)'
    },
    {
        'name': '--miss-penalty',
        'type': int,
        'default': None,
        'help': 'Points lost per miss'
    },
    {
        'name': '--lives',
        'type': int,
        'default': None,
        'help': 'Number of lives (0 = unlimited)'
    },
]


def get_game_mode(**kwargs):
    """Factory function to create game instance."""
    from games.GrowingTargets.game_mode import GrowingTargetsMode
    return GrowingTargetsMode(**kwargs)
