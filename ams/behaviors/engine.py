"""
Behavior Engine - manages Lua VM and entity behaviors.

The engine:
1. Initializes the Lua runtime
2. Loads behavior scripts (single-entity) and collision actions (two-entity)
3. Attaches behaviors to entities
4. Calls behavior lifecycle hooks (on_update, on_hit, on_spawn, on_destroy)
5. Dispatches collision actions when entities collide
6. Manages entity spawning and destruction

Directory structure:
- ams/behaviors/lua/           - Entity behaviors (single entity)
- ams/behaviors/collision_actions/ - Collision actions (two entities)
"""

from pathlib import Path
from typing import Any, Optional
import uuid

from lupa import LuaRuntime

from .entity import Entity
from .api import LuaAPI


class ScheduledCallback:
    """A callback scheduled to run after a delay."""
    def __init__(self, time_remaining: float, callback_name: str, entity_id: str):
        self.time_remaining = time_remaining
        self.callback_name = callback_name
        self.entity_id = entity_id


class BehaviorEngine:
    """
    Manages Lua behaviors and entity lifecycle.

    Usage:
        engine = BehaviorEngine(screen_width=800, screen_height=600)
        engine.load_behavior('descend', 'path/to/descend.lua')

        entity = engine.create_entity('brick', behaviors=['descend'],
                                       behavior_config={'descend': {'speed': 50}})

        # In game loop:
        engine.update(dt)
        for entity in engine.get_alive_entities():
            render(entity)
    """

    # Default paths for Lua scripts
    BEHAVIORS_DIR = Path(__file__).parent / 'lua'
    COLLISION_ACTIONS_DIR = Path(__file__).parent / 'collision_actions'

    def __init__(self, screen_width: float = 800, screen_height: float = 600):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.score = 0
        self.elapsed_time = 0.0

        # Entity storage
        self.entities: dict[str, Entity] = {}

        # Loaded behavior scripts (name -> lua function table)
        self._behaviors: dict[str, Any] = {}

        # Loaded collision actions (name -> lua function table)
        self._collision_actions: dict[str, Any] = {}

        # Pending entity spawns/destroys (processed end of frame)
        self._pending_spawns: list[Entity] = []
        self._pending_destroys: list[str] = []

        # Scheduled callbacks
        self._scheduled: list[ScheduledCallback] = []

        # Sound queue (processed by game layer)
        self._sound_queue: list[str] = []

        # Initialize Lua
        self._lua = LuaRuntime(unpack_returned_tuples=True)
        self._api = LuaAPI(self)
        self._setup_lua_environment()

    def _setup_lua_environment(self) -> None:
        """Set up the Lua environment with API functions."""
        g = self._lua.globals()

        # Create 'ams' namespace for API
        self._lua.execute("ams = {}")
        ams = g.ams

        # Expose all API methods
        api = self._api
        ams.get_x = api.get_x
        ams.get_y = api.get_y
        ams.set_x = api.set_x
        ams.set_y = api.set_y
        ams.get_vx = api.get_vx
        ams.get_vy = api.get_vy
        ams.set_vx = api.set_vx
        ams.set_vy = api.set_vy
        ams.get_width = api.get_width
        ams.get_height = api.get_height
        ams.get_health = api.get_health
        ams.set_health = api.set_health
        ams.get_sprite = api.get_sprite
        ams.set_sprite = api.set_sprite
        ams.get_color = api.get_color
        ams.set_color = api.set_color
        ams.is_alive = api.is_alive
        ams.destroy = api.destroy

        ams.get_prop = api.get_prop
        ams.set_prop = api.set_prop
        ams.get_config = api.get_config

        ams.spawn = api.spawn
        ams.get_entities_of_type = api.get_entities_of_type
        ams.get_all_entity_ids = api.get_all_entity_ids

        ams.get_screen_width = api.get_screen_width
        ams.get_screen_height = api.get_screen_height
        ams.get_score = api.get_score
        ams.add_score = api.add_score
        ams.get_time = api.get_time

        ams.play_sound = api.play_sound
        ams.schedule = api.schedule

        ams.sin = api.math_sin
        ams.cos = api.math_cos
        ams.sqrt = api.math_sqrt
        ams.atan2 = api.math_atan2
        ams.random = api.math_random
        ams.random_range = api.math_random_range
        ams.clamp = api.math_clamp

        ams.log = api.log

    def load_behavior(self, name: str, path: Optional[Path] = None) -> bool:
        """
        Load a behavior script.

        If path is None, looks in BEHAVIORS_DIR for {name}.lua.

        Returns True if loaded successfully.
        """
        if name in self._behaviors:
            return True  # Already loaded

        if path is None:
            path = self.BEHAVIORS_DIR / f"{name}.lua"

        if not path.exists():
            print(f"[BehaviorEngine] Behavior not found: {path}")
            return False

        try:
            code = path.read_text()
            # Execute the Lua file - it should return a table with on_update, etc.
            result = self._lua.execute(code)

            # The behavior script should define a table with lifecycle methods
            # Convention: the script returns the behavior table
            if result is None:
                # Alternative: script defines global with behavior name
                g = self._lua.globals()
                result = getattr(g, name, None)

            if result is None:
                print(f"[BehaviorEngine] Behavior {name} did not return a table")
                return False

            self._behaviors[name] = result
            return True

        except Exception as e:
            print(f"[BehaviorEngine] Error loading {name}: {e}")
            return False

    def load_behaviors_from_dir(self, directory: Optional[Path] = None) -> int:
        """Load all .lua files from directory. Returns count loaded."""
        if directory is None:
            directory = self.BEHAVIORS_DIR

        count = 0
        if directory.exists():
            for lua_file in directory.glob("*.lua"):
                name = lua_file.stem
                if self.load_behavior(name, lua_file):
                    count += 1
        return count

    def load_collision_action(self, name: str, path: Optional[Path] = None) -> bool:
        """
        Load a collision action script.

        Collision actions handle two-entity interactions (collisions).
        They expose an `execute(entity_a_id, entity_b_id, modifier)` function.

        If path is None, looks in COLLISION_ACTIONS_DIR for {name}.lua.

        Returns True if loaded successfully.
        """
        if name in self._collision_actions:
            return True  # Already loaded

        if path is None:
            path = self.COLLISION_ACTIONS_DIR / f"{name}.lua"

        if not path.exists():
            print(f"[BehaviorEngine] Collision action not found: {path}")
            return False

        try:
            code = path.read_text()
            result = self._lua.execute(code)

            if result is None:
                g = self._lua.globals()
                result = getattr(g, name, None)

            if result is None:
                print(f"[BehaviorEngine] Collision action {name} did not return a table")
                return False

            self._collision_actions[name] = result
            return True

        except Exception as e:
            print(f"[BehaviorEngine] Error loading collision action {name}: {e}")
            return False

    def load_collision_actions_from_dir(self, directory: Optional[Path] = None) -> int:
        """Load all collision action .lua files from directory. Returns count loaded."""
        if directory is None:
            directory = self.COLLISION_ACTIONS_DIR

        count = 0
        if directory.exists():
            for lua_file in directory.glob("*.lua"):
                name = lua_file.stem
                if self.load_collision_action(name, lua_file):
                    count += 1
        return count

    def execute_collision_action(
        self,
        action_name: str,
        entity_a: Entity,
        entity_b: Entity,
        modifier: Optional[dict[str, Any]] = None
    ) -> bool:
        """
        Execute a collision action between two entities.

        Args:
            action_name: Name of the collision action to execute
            entity_a: First entity in collision (the one whose collision rule triggered)
            entity_b: Second entity in collision
            modifier: Optional config dict passed to the action

        Returns:
            True if action executed successfully
        """
        # Load action if not already loaded
        if action_name not in self._collision_actions:
            if not self.load_collision_action(action_name):
                return False

        action = self._collision_actions.get(action_name)
        if not action:
            return False

        execute_fn = getattr(action, 'execute', None)
        if not execute_fn:
            print(f"[BehaviorEngine] Collision action {action_name} has no execute function")
            return False

        try:
            # Convert modifier dict to Lua table if provided
            lua_modifier = None
            if modifier:
                lua_modifier = self._lua.table_from(modifier)

            execute_fn(entity_a.id, entity_b.id, lua_modifier)
            return True

        except Exception as e:
            print(f"[BehaviorEngine] Error executing collision action {action_name}: {e}")
            return False

    def create_entity(
        self,
        entity_type: str,
        x: float = 0.0,
        y: float = 0.0,
        width: float = 32.0,
        height: float = 32.0,
        behaviors: Optional[list[str]] = None,
        behavior_config: Optional[dict[str, dict[str, Any]]] = None,
        **kwargs
    ) -> Entity:
        """
        Create a new entity with behaviors attached.

        Args:
            entity_type: Type identifier (e.g., 'brick', 'ball', 'projectile')
            x, y: Initial position
            width, height: Size
            behaviors: List of behavior names to attach
            behavior_config: Per-behavior config from YAML
            **kwargs: Additional Entity fields (vx, vy, color, sprite, health, etc.)

        Returns:
            The created Entity (already registered)
        """
        entity_id = f"{entity_type}_{uuid.uuid4().hex[:8]}"

        entity = Entity(
            id=entity_id,
            entity_type=entity_type,
            x=x,
            y=y,
            width=width,
            height=height,
            behaviors=behaviors or [],
            behavior_config=behavior_config or {},
            **kwargs
        )

        # Ensure behaviors are loaded
        for behavior_name in entity.behaviors:
            self.load_behavior(behavior_name)

        self.entities[entity_id] = entity

        # Call on_spawn for each behavior
        self._call_lifecycle('on_spawn', entity)

        return entity

    def spawn_entity(self, entity_type: str, x: float, y: float,
                     vx: float = 0.0, vy: float = 0.0,
                     width: float = 32.0, height: float = 32.0,
                     color: str = "white", sprite: str = "",
                     behaviors: Optional[list[str]] = None,
                     behavior_config: Optional[dict[str, dict[str, Any]]] = None) -> str:
        """
        Spawn entity (called from Lua API).

        Returns entity ID.
        """
        entity = self.create_entity(
            entity_type=entity_type,
            x=x, y=y,
            vx=vx, vy=vy,
            width=width, height=height,
            color=color, sprite=sprite,
            behaviors=behaviors,
            behavior_config=behavior_config
        )
        return entity.id

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self.entities.get(entity_id)

    def get_alive_entities(self) -> list[Entity]:
        """Get all alive entities."""
        return [e for e in self.entities.values() if e.alive]

    def update_entity_behaviors(self, entity: Entity) -> None:
        """Re-register an entity's behaviors after transform.

        Called when an entity's type changes to ensure new behaviors
        are properly loaded and on_spawn is called.

        Args:
            entity: The entity whose behaviors have changed
        """
        # Ensure all new behaviors are loaded
        for behavior_name in entity.behaviors:
            self.load_behavior(behavior_name)

        # Clear any old behavior state from properties
        # (behaviors should init fresh via on_spawn)

        # Call on_spawn for new behaviors
        self._call_lifecycle('on_spawn', entity)

    def evaluate_expression(self, expression: str) -> float:
        """Evaluate a Lua expression and return the result.

        Used for dynamic values in spawn configs like:
            angle: {lua: "ams.random_range(-60, -120)"}

        The expression must be complete Lua code - use ams.* explicitly.

        Args:
            expression: Lua expression string (e.g., "ams.random_range(-60, -120)")

        Returns:
            Evaluated result as float
        """
        try:
            result = self._lua.eval(expression)
            return float(result)
        except Exception:
            return 0.0

    def update(self, dt: float) -> None:
        """
        Update all entities and their behaviors.

        Args:
            dt: Delta time in seconds
        """
        self.elapsed_time += dt

        # Update scheduled callbacks
        for scheduled in self._scheduled[:]:
            scheduled.time_remaining -= dt
            if scheduled.time_remaining <= 0:
                self._call_scheduled_callback(scheduled)
                self._scheduled.remove(scheduled)

        # Call on_update for each entity's behaviors
        for entity in list(self.entities.values()):
            if entity.alive:
                self._call_lifecycle('on_update', entity, dt)

        # Remove dead entities
        dead_ids = [eid for eid, e in self.entities.items() if not e.alive]
        for eid in dead_ids:
            entity = self.entities.pop(eid)
            self._call_lifecycle('on_destroy', entity)

    def notify_hit(self, entity: Entity, other: Optional[Entity] = None,
                   hit_x: float = 0.0, hit_y: float = 0.0) -> None:
        """
        Notify entity of a hit/collision (legacy API).

        Args:
            entity: The entity that was hit
            other: The other entity involved (if any)
            hit_x, hit_y: Position of hit
        """
        if entity.alive:
            other_id = other.id if other else ""
            self._call_lifecycle('on_hit', entity, other_id, hit_x, hit_y)

    def notify_collision(self, entity: Entity, other: Entity,
                         other_type: str, other_base_type: str) -> None:
        """
        Notify entity of collision with another entity.

        Called by GameEngine when collision rules match.

        Args:
            entity: The entity being notified
            other: The other entity it collided with
            other_type: Type of the other entity (e.g., 'brick_red')
            other_base_type: Base type of other entity (e.g., 'brick')
        """
        if entity.alive:
            self._call_lifecycle('on_hit', entity,
                                 other.id, other_type, other_base_type)

    def _call_lifecycle(self, method_name: str, entity: Entity, *args) -> None:
        """Call a lifecycle method on all of an entity's behaviors."""
        for behavior_name in entity.behaviors:
            behavior = self._behaviors.get(behavior_name)
            if behavior is None:
                continue

            method = getattr(behavior, method_name, None)
            if method is None:
                continue

            try:
                method(entity.id, *args)
            except Exception as e:
                print(f"[BehaviorEngine] Error in {behavior_name}.{method_name}: {e}")

    def _call_scheduled_callback(self, scheduled: ScheduledCallback) -> None:
        """Execute a scheduled callback."""
        entity = self.entities.get(scheduled.entity_id)
        if entity is None or not entity.alive:
            return

        for behavior_name in entity.behaviors:
            behavior = self._behaviors.get(behavior_name)
            if behavior is None:
                continue

            callback = getattr(behavior, scheduled.callback_name, None)
            if callback:
                try:
                    callback(entity.id)
                except Exception as e:
                    print(f"[BehaviorEngine] Error in scheduled {scheduled.callback_name}: {e}")

    def schedule_callback(self, delay: float, callback_name: str, entity_id: str) -> None:
        """Schedule a callback to run after delay seconds."""
        self._scheduled.append(ScheduledCallback(delay, callback_name, entity_id))

    def queue_sound(self, sound_name: str) -> None:
        """Queue a sound to be played by the game layer."""
        self._sound_queue.append(sound_name)

    def pop_sounds(self) -> list[str]:
        """Get and clear queued sounds."""
        sounds = self._sound_queue[:]
        self._sound_queue.clear()
        return sounds

    def clear(self) -> None:
        """Remove all entities and reset state."""
        # Call on_destroy for all
        for entity in self.entities.values():
            self._call_lifecycle('on_destroy', entity)

        self.entities.clear()
        self._scheduled.clear()
        self._sound_queue.clear()
        self.score = 0
        self.elapsed_time = 0.0
