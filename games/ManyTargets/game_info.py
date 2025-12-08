"""
ManyTargets - Game Info

Field clearance game - clear all targets while avoiding misses.
Required for auto-discovery by GameRegistry.
"""

# Game metadata
NAME = "ManyTargets"
DESCRIPTION = "Clear the field of targets - misses cost points. Inspired by egg carton training."
VERSION = "1.0.0"
AUTHOR = "AMS Team"

# CLI argument definitions
ARGUMENTS = [
    {
        'name': '--count',
        'type': int,
        'default': None,
        'help': 'Number of targets to generate (default: 15)'
    },
    {
        'name': '--size',
        'type': str,
        'default': None,
        'help': 'Target size: small, medium, large (default: medium)'
    },
    {
        'name': '--timed',
        'type': int,
        'default': None,
        'help': 'Time limit in seconds (default: unlimited)'
    },
    {
        'name': '--miss-mode',
        'type': str,
        'default': None,
        'help': 'Miss behavior: penalty (default) or strict (game over on miss)'
    },
    {
        'name': '--allow-duplicates',
        'action': 'store_true',
        'default': False,
        'help': 'Allow hitting same target multiple times (penalized)'
    },
    {
        'name': '--progressive',
        'action': 'store_true',
        'default': False,
        'help': 'Targets shrink as you clear the field'
    },
    {
        'name': '--shrink-rate',
        'type': float,
        'default': None,
        'help': 'Size multiplier per hit in progressive mode (default: 0.9)'
    },
    {
        'name': '--min-size',
        'type': int,
        'default': None,
        'help': 'Minimum target radius in progressive mode (default: 15)'
    },
    {
        'name': '--spacing',
        'type': float,
        'default': None,
        'help': 'Minimum spacing between targets as radius multiplier (default: 1.5)'
    },
    {
        'name': '--quiver-size',
        'type': int,
        'default': None,
        'help': 'Arrows per round before retrieval (0 or omit = unlimited)'
    },
    {
        'name': '--retrieval-pause',
        'type': int,
        'default': None,
        'help': 'Seconds for retrieval pause between rounds (0 = manual with SPACE, default: 30)'
    },
    {
        'name': '--palette',
        'type': str,
        'default': None,
        'help': 'Color palette for testing (full, bw, warm, cool, mono_red, mono_green, limited, orange_dart)'
    },
]


def get_game_mode(**kwargs):
    """
    Factory function to create a ManyTargetsMode instance.

    Args:
        **kwargs: Game configuration options

    Returns:
        ManyTargetsMode instance
    """
    from games.ManyTargets.game_mode import ManyTargetsMode

    # Filter out None values (except for boolean flags)
    game_kwargs = {}
    for k, v in kwargs.items():
        if v is not None:
            game_kwargs[k] = v

    # Map CLI arg names to constructor params (handle hyphens)
    param_map = {
        'count': 'count',
        'size': 'size',
        'timed': 'timed',
        'miss_mode': 'miss_mode',
        'allow_duplicates': 'allow_duplicates',
        'progressive': 'progressive',
        'shrink_rate': 'shrink_rate',
        'min_size': 'min_size',
        'spacing': 'spacing',
        'quiver_size': 'quiver_size',
        'retrieval_pause': 'retrieval_pause',
        'palette': 'palette',
    }

    constructor_kwargs = {}
    for cli_name, param_name in param_map.items():
        if cli_name in game_kwargs:
            constructor_kwargs[param_name] = game_kwargs[cli_name]

    return ManyTargetsMode(**constructor_kwargs)
