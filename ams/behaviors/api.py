"""
Lua API - the bridge between Lua behaviors and Python engine.

This module exposes safe functions to Lua that behaviors can call.
All game mutations go through this API - behaviors cannot directly
access Python objects.

The API is designed to be:
- Sufficient: Core behaviors can be fully implemented
- Safe: No filesystem, network, or OS access
- Symmetric: Same API on native and WASM (future)
- Lua-native returns: All return values are primitives or Lua tables (not Python objects)
"""

from functools import wraps
from typing import Callable, Any, TYPE_CHECKING
import math
import random

if TYPE_CHECKING:
    from .engine import BehaviorEngine


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
        # Reject (sets are unordered, might surprise Lua authors)
        raise TypeError("Cannot convert set to Lua - convert to list first")

    # For other objects, fail loudly - this is a bug in the API implementation
    # This prevents leaking arbitrary Python objects
    raise TypeError(
        f"Cannot convert {type(value).__name__} to Lua-safe value. "
        f"API methods must return only primitives, lists, or dicts."
    )


def lua_safe_return(method: Callable) -> Callable:
    """Decorator that converts return values to Lua-safe types.

    Wraps methods on LuaAPI to ensure they only return:
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


class LuaAPI:
    """
    API exposed to Lua behaviors.

    All methods here are callable from Lua. They operate on entities
    by ID, not direct reference, to maintain the sandbox boundary.

    Methods that return collections use @lua_safe_return to convert
    Python lists/dicts to Lua-native tables, ensuring proper 1-indexed
    iteration with ipairs/pairs and # operator support.
    """

    def __init__(self, engine: 'BehaviorEngine'):
        self._engine = engine
        self._lua = None  # Set by BehaviorEngine after init

    def set_lua_runtime(self, lua) -> None:
        """Set the Lua runtime reference for converting return values."""
        self._lua = lua

    # =========================================================================
    # Entity Access
    # =========================================================================

    def get_x(self, entity_id: str) -> float:
        """Get entity X position."""
        entity = self._engine.get_entity(entity_id)
        return entity.x if entity else 0.0

    def get_y(self, entity_id: str) -> float:
        """Get entity Y position."""
        entity = self._engine.get_entity(entity_id)
        return entity.y if entity else 0.0

    def set_x(self, entity_id: str, x: float) -> None:
        """Set entity X position."""
        entity = self._engine.get_entity(entity_id)
        if entity:
            entity.x = x

    def set_y(self, entity_id: str, y: float) -> None:
        """Set entity Y position."""
        entity = self._engine.get_entity(entity_id)
        if entity:
            entity.y = y

    def get_vx(self, entity_id: str) -> float:
        """Get entity X velocity."""
        entity = self._engine.get_entity(entity_id)
        return entity.vx if entity else 0.0

    def get_vy(self, entity_id: str) -> float:
        """Get entity Y velocity."""
        entity = self._engine.get_entity(entity_id)
        return entity.vy if entity else 0.0

    def set_vx(self, entity_id: str, vx: float) -> None:
        """Set entity X velocity."""
        entity = self._engine.get_entity(entity_id)
        if entity:
            entity.vx = vx

    def set_vy(self, entity_id: str, vy: float) -> None:
        """Set entity Y velocity."""
        entity = self._engine.get_entity(entity_id)
        if entity:
            entity.vy = vy

    def get_width(self, entity_id: str) -> float:
        """Get entity width."""
        entity = self._engine.get_entity(entity_id)
        return entity.width if entity else 0.0

    def get_height(self, entity_id: str) -> float:
        """Get entity height."""
        entity = self._engine.get_entity(entity_id)
        return entity.height if entity else 0.0

    def get_health(self, entity_id: str) -> int:
        """Get entity health."""
        entity = self._engine.get_entity(entity_id)
        return entity.health if entity else 0

    def set_health(self, entity_id: str, health: int) -> None:
        """Set entity health."""
        entity = self._engine.get_entity(entity_id)
        if entity:
            entity.health = health

    def get_sprite(self, entity_id: str) -> str:
        """Get entity sprite name."""
        entity = self._engine.get_entity(entity_id)
        return entity.sprite if entity else ""

    def set_sprite(self, entity_id: str, sprite: str) -> None:
        """Set entity sprite name."""
        entity = self._engine.get_entity(entity_id)
        if entity:
            entity.sprite = sprite

    def get_color(self, entity_id: str) -> str:
        """Get entity color."""
        entity = self._engine.get_entity(entity_id)
        return entity.color if entity else "white"

    def set_color(self, entity_id: str, color: str) -> None:
        """Set entity color."""
        entity = self._engine.get_entity(entity_id)
        if entity:
            entity.color = color

    def is_alive(self, entity_id: str) -> bool:
        """Check if entity is alive."""
        entity = self._engine.get_entity(entity_id)
        return entity.alive if entity else False

    def destroy(self, entity_id: str) -> None:
        """Mark entity for destruction."""
        entity = self._engine.get_entity(entity_id)
        if entity:
            entity.destroy()

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
    # Entity Spawning
    # =========================================================================

    def spawn(self, entity_type: str, x: float, y: float,
              vx: float = 0.0, vy: float = 0.0,
              width: float = 32.0, height: float = 32.0,
              color: str = "white", sprite: str = "") -> str:
        """
        Spawn a new entity.

        Returns the new entity's ID.
        """
        return self._engine.spawn_entity(
            entity_type=entity_type,
            x=x, y=y,
            vx=vx, vy=vy,
            width=width, height=height,
            color=color, sprite=sprite
        )

    # =========================================================================
    # Entity Queries
    # =========================================================================

    @lua_safe_return
    def get_entities_of_type(self, entity_type: str) -> list[str]:
        """Get IDs of all entities of a given type.

        Returns a 1-indexed Lua table, suitable for ipairs iteration.
        """
        return [e.id for e in self._engine.entities.values()
                if e.entity_type == entity_type and e.alive]

    @lua_safe_return
    def get_entities_by_tag(self, tag: str) -> list[str]:
        """Get IDs of all entities with a given tag.

        Returns a 1-indexed Lua table, suitable for ipairs iteration.
        """
        return [e.id for e in self._engine.entities.values()
                if tag in e.tags and e.alive]

    @lua_safe_return
    def get_all_entity_ids(self) -> list[str]:
        """Get IDs of all alive entities.

        Returns a 1-indexed Lua table, suitable for ipairs iteration.
        """
        return [e.id for e in self._engine.entities.values() if e.alive]

    def count_entities_by_tag(self, tag: str) -> int:
        """Count alive entities with a given tag."""
        return sum(1 for e in self._engine.entities.values()
                   if tag in e.tags and e.alive)

    # =========================================================================
    # Game State
    # =========================================================================

    def get_screen_width(self) -> float:
        """Get game screen width."""
        return self._engine.screen_width

    def get_screen_height(self) -> float:
        """Get game screen height."""
        return self._engine.screen_height

    def get_score(self) -> int:
        """Get current score."""
        return self._engine.score

    def add_score(self, points: int) -> None:
        """Add to score."""
        self._engine.score += points

    def get_time(self) -> float:
        """Get elapsed game time in seconds."""
        return self._engine.elapsed_time

    # =========================================================================
    # Events (deferred actions)
    # =========================================================================

    def play_sound(self, sound_name: str) -> None:
        """Request a sound to be played."""
        self._engine.queue_sound(sound_name)

    def schedule(self, delay: float, callback_name: str, entity_id: str) -> None:
        """Schedule a callback after delay seconds."""
        self._engine.schedule_callback(delay, callback_name, entity_id)

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
    # Parent-Child Relationships
    # =========================================================================

    def get_parent_id(self, entity_id: str) -> str:
        """Get parent entity ID, or empty string if no parent."""
        entity = self._engine.get_entity(entity_id)
        if entity and entity.parent_id:
            return entity.parent_id
        return ""

    def set_parent(self, entity_id: str, parent_id: str,
                   offset_x: float = 0.0, offset_y: float = 0.0) -> None:
        """
        Attach entity to a parent.

        Args:
            entity_id: Entity to attach
            parent_id: Parent entity ID (empty string to detach)
            offset_x: X offset from parent center
            offset_y: Y offset from parent center
        """
        entity = self._engine.get_entity(entity_id)
        if not entity:
            return

        # Remove from old parent's children list
        if entity.parent_id:
            old_parent = self._engine.get_entity(entity.parent_id)
            if old_parent and entity_id in old_parent.children:
                old_parent.children.remove(entity_id)

        if parent_id:
            parent = self._engine.get_entity(parent_id)
            if parent:
                entity.parent_id = parent_id
                entity.parent_offset = (offset_x, offset_y)
                if entity_id not in parent.children:
                    parent.children.append(entity_id)
                # Also set properties for Lua access
                entity.properties["_parent_id"] = parent_id
                entity.properties["_parent_offset_x"] = offset_x
                entity.properties["_parent_offset_y"] = offset_y
        else:
            # Detach
            entity.parent_id = None
            entity.parent_offset = (0.0, 0.0)
            entity.properties.pop("_parent_id", None)
            entity.properties.pop("_parent_offset_x", None)
            entity.properties.pop("_parent_offset_y", None)

    def detach_from_parent(self, entity_id: str) -> None:
        """Detach entity from its parent."""
        self.set_parent(entity_id, "")

    @lua_safe_return
    def get_children(self, entity_id: str) -> list[str]:
        """Get IDs of all child entities."""
        entity = self._engine.get_entity(entity_id)
        if entity:
            return list(entity.children)
        return []

    def has_parent(self, entity_id: str) -> bool:
        """Check if entity has a parent."""
        entity = self._engine.get_entity(entity_id)
        return bool(entity and entity.parent_id)

    # =========================================================================
    # Debug
    # =========================================================================

    def log(self, message: str) -> None:
        """Log a debug message."""
        print(f"[Lua] {message}")
