"""
Core Lua sandbox and runtime abstraction.

Provides a reusable, sandboxed Lua execution environment with:
- Secure sandbox (no io, os, debug, require, etc.)
- Entity management and lifecycle hooks
- Behavior loading and execution

Entity is an ABC; use GameEntity from ams.games.game_engine for games.
"""

from ams.lua.engine import LuaEngine
from ams.lua.entity import Entity
from ams.lua.api import LuaAPIBase, LuaAPI, lua_safe_return, _to_lua_value

__all__ = ['LuaEngine', 'Entity', 'LuaAPIBase', 'LuaAPI', 'lua_safe_return', '_to_lua_value']
