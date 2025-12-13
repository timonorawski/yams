"""
Game-engine Lua assets.

Contains:
- actions/: Lua interaction action scripts
- behaviors/: YAML behavior bundles (interaction collections)
- generator/: Lua generators for spawn-time values

Entity ABC is in ams.lua (core Lua engine), GameEntity is here.
"""

# Re-export for convenience
from ams.lua import Entity, LuaAPIBase
from ams.games.game_engine.entity import GameEntity
from ams.games.game_engine.api import GameLuaAPI
from ams.games.game_engine.lua.behavior_loader import BehaviorLoader

__all__ = ['Entity', 'LuaAPIBase', 'GameEntity', 'GameLuaAPI', 'BehaviorLoader']
