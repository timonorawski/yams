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
        'name': '--spawn-rate',
        'type': float,
        'default': None,
        'help': 'Seconds between target spawns'
    },
    {
        'name': '--max-targets',
        'type': int,
        'default': None,
        'help': 'Maximum simultaneous targets'
    },
    {
        'name': '--growth-rate',
        'type': float,
        'default': None,
        'help': 'Growth rate (pixels per second)'
    },
    {
        'name': '--start-size',
        'type': int,
        'default': None,
        'help': 'Initial target radius'
    },
    {
        'name': '--max-size',
        'type': int,
        'default': None,
        'help': 'Maximum target radius (disappears at this size)'
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
