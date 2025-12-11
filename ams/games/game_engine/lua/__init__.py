"""
Game-engine Lua assets.

Contains .lua behavior scripts, collision actions, and generators.
Entity ABC is in ams.lua (core Lua engine), GameEntity is here.
"""

# Re-export for convenience
from ams.lua import Entity, LuaAPI
from ams.games.game_engine.entity import GameEntity
from ams.games.game_engine.api import GameLuaAPI

__all__ = ['Entity', 'LuaAPI', 'GameEntity', 'GameLuaAPI']
