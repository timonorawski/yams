"""
AMS Behavior System

Behaviors are Lua modules that attach logic to entities. The engine (Python)
handles rendering, input, and collision detection. Behaviors (Lua) handle
entity logic. Games (YAML) compose behaviors into playable experiences.

This architecture ensures:
- User-uploaded behaviors are sandboxed (no filesystem/network/OS access)
- Same Lua code runs on native Python and pygame-wasm
- Core behaviors serve as examples and test cases for the API
"""

from .engine import BehaviorEngine
from .entity import Entity
from .api import LuaAPI

__all__ = ['BehaviorEngine', 'Entity', 'LuaAPI']
