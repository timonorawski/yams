"""DuckHunt NextGen - YAML-driven duck hunting game.

This reimplements DuckHunt using the GameEngine framework with:
- Declarative entity transforms (flying -> hit -> falling)
- on_hit input mapping (click detection on entities)
- Reusable behaviors (bounce, gravity)
- Inline Lua for spawner logic

All game mechanics are defined in game.yaml.
"""

from pathlib import Path

from games.common import GameEngine, GameEngineSkin


class DuckHuntNGSkin(GameEngineSkin):
    """Rendering skin for DuckHunt NG.

    All rendering is YAML-driven via game.yaml render commands.
    """
    pass


class DuckHuntNGMode(GameEngine):
    """DuckHunt NextGen - YAML-driven duck hunting."""

    NAME = "Duck Hunt NG"
    DESCRIPTION = "YAML-driven duck hunting game"

    GAME_DEF_FILE = Path(__file__).parent / 'game.yaml'
    LEVELS_DIR = Path(__file__).parent / 'levels'

    def __init__(self, **kwargs):
        """Initialize DuckHunt NG."""
        kwargs.pop('skin', None)
        super().__init__(skin='default', **kwargs)

    def _get_skin(self, _skin_name: str) -> GameEngineSkin:
        """Get rendering skin."""
        return DuckHuntNGSkin()
