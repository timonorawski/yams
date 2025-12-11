"""
YAML-driven Game Engine with Lua behaviors.

The GameEngine enables creating games primarily through YAML configuration
and Lua scripts, rather than Python code.
"""

from ams.games.game_engine.engine import GameEngine
from ams.games.game_engine.renderer import GameEngineRenderer
from ams.games.game_engine.assets import AssetProvider
from ams.games.game_engine.config import EntityPlacement, GameEngineLevelData
from ams.games.game_engine.entity import GameEntity
from ams.games.game_engine.api import GameLuaAPI

__all__ = [
    'GameEngine',
    'GameEngineRenderer',
    'AssetProvider',
    'EntityPlacement',
    'GameEngineLevelData',
    'GameEntity',
    'GameLuaAPI',
]
