"""Lua Action Handler - Bridge between InteractionEngine and LuaEngine.

This module provides an ActionHandler implementation that delegates
interaction actions to the Lua scripting engine.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ams.lua import LuaEngine


class LuaActionHandler:
    """Action handler that executes Lua scripts for interactions.

    This bridges the InteractionEngine's unified interaction model to the
    existing Lua behavior system. All collision/input/screen/time actions
    are dispatched to Lua scripts.

    Usage:
        handler = LuaActionHandler(lua_engine)
        interaction_engine.set_default_handler(handler)
    """

    def __init__(self, lua_engine: "LuaEngine"):
        """Initialize with LuaEngine reference.

        Args:
            lua_engine: The LuaEngine instance that executes Lua scripts
        """
        self._lua = lua_engine

    def execute(
        self,
        entity_a_id: str,
        entity_b_id: str,
        interaction: Dict[str, Any]
    ) -> None:
        """Execute an interaction action via Lua.

        Args:
            entity_a_id: Source entity ID
            entity_b_id: Target entity ID (or system entity name)
            interaction: Interaction context dict containing:
                - action: Action name (maps to Lua script)
                - modifier: Config dict passed to action
                - trigger: Trigger mode that fired (enter/exit/continuous)
                - distance: Computed distance (if applicable)
                - angle: Computed angle (if applicable)
                - a: Entity A attributes dict
                - b: Entity B attributes dict
                - target: Target entity type (e.g., "pointer", "screen", "time")
        """
        action_name = interaction.get("action")
        if not action_name:
            return

        modifier = interaction.get("modifier") or {}
        target = interaction.get("target", "")

        # Build interaction context as separate dict (passed as 4th arg)
        context = {
            "trigger": interaction.get("trigger", "enter"),
            "target": target,
            "dt": interaction.get("dt", 0.016),
        }

        # Add computed values if present
        if "distance" in interaction:
            context["distance"] = interaction["distance"]
        if "angle" in interaction:
            context["angle"] = interaction["angle"]

        # Add entity B attributes (e.g., pointer x/y) for Lua access
        entity_b_attrs = interaction.get("b", {})
        if entity_b_attrs:
            context["target_x"] = entity_b_attrs.get("x", 0)
            context["target_y"] = entity_b_attrs.get("y", 0)
            context["target_active"] = entity_b_attrs.get("active", False)

        # Execute via LuaEngine - pass context as 4th arg
        self._lua.execute_interaction_action(
            action_name,
            self._lua.get_entity(entity_a_id),
            self._get_target_entity(entity_b_id),
            modifier,
            context,
        )

    def _get_target_entity(self, entity_id: str) -> Any:
        """Get target entity, handling system entities.

        For system entities (pointer, screen, level, game, time), returns
        a stub object with just an id attribute for compatibility.

        Args:
            entity_id: Entity ID or system entity name

        Returns:
            Entity object or stub with id
        """
        # Try to get real entity first
        entity = self._lua.get_entity(entity_id)
        if entity:
            return entity

        # System entities get a stub object
        # LuaEngine.execute_collision_action only needs entity.id
        class SystemEntityStub:
            def __init__(self, entity_id: str):
                self.id = entity_id

        return SystemEntityStub(entity_id)
