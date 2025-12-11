"""Game info factory for DuckHunt NG."""

from games.common import GameInfo
from .game_mode import DuckHuntNGMode


def get_game_info() -> GameInfo:
    """Return game info for registry."""
    return GameInfo(
        name="duckhuntng",
        display_name="Duck Hunt NG",
        description="YAML-driven duck hunting game",
        game_class=DuckHuntNGMode,
        arguments=DuckHuntNGMode.ARGUMENTS if hasattr(DuckHuntNGMode, 'ARGUMENTS') else [],
    )
