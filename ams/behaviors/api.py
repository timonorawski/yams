"""
Lua API - the bridge between Lua behaviors and Python engine.

This module exposes safe functions to Lua that behaviors can call.
All game mutations go through this API - behaviors cannot directly
access Python objects.

The API is designed to be:
- Sufficient: Core behaviors can be fully implemented
- Safe: No filesystem, network, or OS access
- Symmetric: Same API on native and WASM (future)
"""

from typing import Callable, Any, TYPE_CHECKING
import math
import random

if TYPE_CHECKING:
    from .engine import BehaviorEngine


class LuaAPI:
    """
    API exposed to Lua behaviors.

    All methods here are callable from Lua. They operate on entities
    by ID, not direct reference, to maintain the sandbox boundary.
    """

    def __init__(self, engine: 'BehaviorEngine'):
        self._engine = engine

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

    def get_prop(self, entity_id: str, key: str) -> Any:
        """Get custom property from entity."""
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

    def get_config(self, entity_id: str, behavior_name: str, key: str, default: Any = None) -> Any:
        """Get behavior config value from YAML definition."""
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

    def get_entities_of_type(self, entity_type: str) -> list[str]:
        """Get IDs of all entities of a given type."""
        return [e.id for e in self._engine.entities.values()
                if e.entity_type == entity_type and e.alive]

    def get_all_entity_ids(self) -> list[str]:
        """Get IDs of all alive entities."""
        return [e.id for e in self._engine.entities.values() if e.alive]

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
    # Debug
    # =========================================================================

    def log(self, message: str) -> None:
        """Log a debug message."""
        print(f"[Lua] {message}")
