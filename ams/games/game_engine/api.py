"""
Game Lua API - game-specific bridge between Lua behaviors and game engine.

Extends LuaAPIBase with game entity operations:
- Position, velocity, size access
- Visual properties (sprite, color)
- Health and lifecycle
- Entity spawning and queries
- Game state (score, time, screen)
- Parent-child relationships
- Events (sounds, scheduling)
"""

from typing import Any, TYPE_CHECKING

from ams.lua.api import LuaAPIBase, lua_safe_return

if TYPE_CHECKING:
    from ams.lua.engine import LuaEngine


class GameLuaAPI(LuaAPIBase):
    """
    Game-specific API exposed to Lua behaviors.

    Extends LuaAPIBase with GameEntity operations. All methods operate
    on entities by ID to maintain the sandbox boundary.
    """

    def register_api(self, ams_namespace) -> None:
        """Register game API methods on the ams.* namespace."""
        # Register base methods first
        super().register_api(ams_namespace)

        # Entity access - transform
        ams_namespace.get_x = self.get_x
        ams_namespace.get_y = self.get_y
        ams_namespace.set_x = self.set_x
        ams_namespace.set_y = self.set_y
        ams_namespace.get_vx = self.get_vx
        ams_namespace.get_vy = self.get_vy
        ams_namespace.set_vx = self.set_vx
        ams_namespace.set_vy = self.set_vy
        ams_namespace.get_width = self.get_width
        ams_namespace.get_height = self.get_height

        # Entity access - visual
        ams_namespace.get_sprite = self.get_sprite
        ams_namespace.set_sprite = self.set_sprite
        ams_namespace.get_color = self.get_color
        ams_namespace.set_color = self.set_color

        # Entity access - state
        ams_namespace.get_health = self.get_health
        ams_namespace.set_health = self.set_health
        ams_namespace.is_alive = self.is_alive
        ams_namespace.destroy = self.destroy

        # Spawning and queries
        ams_namespace.spawn = self.spawn
        ams_namespace.get_entities_of_type = self.get_entities_of_type
        ams_namespace.get_entities_by_tag = self.get_entities_by_tag
        ams_namespace.count_entities_by_tag = self.count_entities_by_tag
        ams_namespace.get_all_entity_ids = self.get_all_entity_ids

        # Game state
        ams_namespace.get_screen_width = self.get_screen_width
        ams_namespace.get_screen_height = self.get_screen_height
        ams_namespace.get_score = self.get_score
        ams_namespace.add_score = self.add_score
        ams_namespace.get_time = self.get_time

        # Events
        ams_namespace.play_sound = self.play_sound
        ams_namespace.schedule = self.schedule

        # Parent-child relationships
        ams_namespace.get_parent_id = self.get_parent_id
        ams_namespace.set_parent = self.set_parent
        ams_namespace.detach_from_parent = self.detach_from_parent
        ams_namespace.get_children = self.get_children
        ams_namespace.has_parent = self.has_parent

    # =========================================================================
    # Entity Access - Transform
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

    # =========================================================================
    # Entity Access - Visual
    # =========================================================================

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

    # =========================================================================
    # Entity Access - State
    # =========================================================================

    def get_health(self, entity_id: str) -> int:
        """Get entity health."""
        entity = self._engine.get_entity(entity_id)
        return entity.health if entity else 0

    def set_health(self, entity_id: str, health: int) -> None:
        """Set entity health."""
        entity = self._engine.get_entity(entity_id)
        if entity:
            entity.health = health

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
    # Entity Spawning
    # =========================================================================

    def spawn(self, entity_type: str, x: float, y: float,
              vx: float = 0.0, vy: float = 0.0,
              width: float = 32.0, height: float = 32.0,
              color: str = "white", sprite: str = "") -> str:
        """Spawn a new entity. Returns the new entity's ID."""
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
