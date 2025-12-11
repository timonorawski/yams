"""
Lua API helpers and base class.

This module provides:
- Value conversion utilities for Lua-safe returns
- @lua_safe_return decorator
- LuaAPIBase with property access, math, and logging

Domain-specific API classes (like GameLuaAPI) extend this base.
"""

from functools import wraps
from typing import Callable, Any, TYPE_CHECKING
import math
import random

if TYPE_CHECKING:
    from .engine import LuaEngine


def _to_lua_value(value: Any, lua_runtime) -> Any:
    """Convert a Python value to a Lua-safe value.

    Safe values:
    - Primitives: None, bool, int, float, str
    - Lua tables: Created via lua.table() for lists/dicts

    This ensures Lua code never receives raw Python objects (lists, dicts, etc.)
    which have different semantics (0-indexed, no ipairs/pairs support, no # operator).
    """
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, (list, tuple)):
        # Convert to 1-indexed Lua table
        lua_table = lua_runtime.table()
        for i, item in enumerate(value, start=1):
            lua_table[i] = _to_lua_value(item, lua_runtime)
        return lua_table

    if isinstance(value, dict):
        # Convert to Lua table with string keys
        lua_table = lua_runtime.table()
        for k, v in value.items():
            if not isinstance(k, (str, int, float, bool)):
                raise TypeError(
                    f"Dict key must be str/int/float, got {type(k).__name__}"
                )
            lua_table[k] = _to_lua_value(v, lua_runtime)
        return lua_table

    # bytes - reject, we don't want "b'...'" strings to sneak through
    if isinstance(value, bytes):
        raise TypeError("Cannot pass bytes to Lua - decode to str first")

    # sets - reject, not predictable order
    if isinstance(value, set):
        raise TypeError("Cannot convert set to Lua - convert to list first")

    # For other objects, fail loudly - this is a bug in the API implementation
    raise TypeError(
        f"Cannot convert {type(value).__name__} to Lua-safe value. "
        f"API methods must return only primitives, lists, or dicts."
    )


def lua_safe_return(method: Callable) -> Callable:
    """Decorator that converts return values to Lua-safe types.

    Wraps methods on LuaAPI classes to ensure they only return:
    - Primitives (None, bool, int, float, str)
    - Lua-native tables (for lists/dicts)

    This prevents Lua from receiving raw Python objects which have
    different semantics (0-indexed lists, no ipairs support, etc.).
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        result = method(self, *args, **kwargs)
        return _to_lua_value(result, self._lua)
    return wrapper


class LuaAPIBase:
    """
    Base API for Lua behaviors.

    Provides core functionality that any Lua-scriptable system needs:
    - Property get/set (custom key-value storage)
    - Behavior config access
    - Math helpers
    - Debug logging

    Domain-specific APIs extend this with entity access, spawning, etc.
    """

    def __init__(self, engine: 'LuaEngine'):
        self._engine = engine
        self._lua = None  # Set by LuaEngine after init

    def set_lua_runtime(self, lua) -> None:
        """Set the Lua runtime reference for converting return values."""
        self._lua = lua

    def register_api(self, ams_namespace) -> None:
        """Register this API's methods on the ams.* namespace.

        Subclasses should override and call super().register_api() first.
        """
        # Property access
        ams_namespace.get_prop = self.get_prop
        ams_namespace.set_prop = self.set_prop
        ams_namespace.get_config = self.get_config

        # Math helpers
        ams_namespace.sin = self.math_sin
        ams_namespace.cos = self.math_cos
        ams_namespace.sqrt = self.math_sqrt
        ams_namespace.atan2 = self.math_atan2
        ams_namespace.random = self.math_random
        ams_namespace.random_range = self.math_random_range
        ams_namespace.clamp = self.math_clamp

        # Debug
        ams_namespace.log = self.log

    # =========================================================================
    # Properties (custom key-value storage for behaviors)
    # =========================================================================

    @lua_safe_return
    def get_prop(self, entity_id: str, key: str) -> Any:
        """Get custom property from entity.

        Returns Lua-safe values (primitives or Lua tables).
        """
        entity = self._engine.get_entity(entity_id)
        if entity:
            return entity.properties.get(key)
        return None

    def set_prop(self, entity_id: str, key: str, value: Any) -> None:
        """Set custom property on entity."""
        entity = self._engine.get_entity(entity_id)
        if entity:
            entity.properties[key] = value

    # =========================================================================
    # Behavior Config (read-only, from YAML)
    # =========================================================================

    @lua_safe_return
    def get_config(self, entity_id: str, behavior_name: str, key: str, default: Any = None) -> Any:
        """Get behavior config value from YAML definition.

        Returns Lua-safe values (primitives or Lua tables).
        Nested dicts/lists from YAML are converted to Lua tables.
        """
        entity = self._engine.get_entity(entity_id)
        if entity and behavior_name in entity.behavior_config:
            return entity.behavior_config[behavior_name].get(key, default)
        return default

    # =========================================================================
    # Math helpers (safe, no side effects)
    # =========================================================================

    def math_sin(self, x: float) -> float:
        return math.sin(x)

    def math_cos(self, x: float) -> float:
        return math.cos(x)

    def math_sqrt(self, x: float) -> float:
        return math.sqrt(max(0, x))

    def math_atan2(self, y: float, x: float) -> float:
        return math.atan2(y, x)

    def math_random(self) -> float:
        """Return random float in [0, 1)."""
        return random.random()

    def math_random_range(self, min_val: float, max_val: float) -> float:
        """Return random float in [min, max]."""
        return random.uniform(min_val, max_val)

    def math_clamp(self, value: float, min_val: float, max_val: float) -> float:
        """Clamp value to range."""
        return max(min_val, min(max_val, value))

    # =========================================================================
    # Debug
    # =========================================================================

    def log(self, message: str) -> None:
        """Log a debug message."""
        print(f"[Lua] {message}")


# Backward compatibility alias
LuaAPI = LuaAPIBase
