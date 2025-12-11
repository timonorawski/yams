"""
Lua Engine - Core Lua sandbox and runtime for game scripting.

The engine:
1. Initializes the Lua runtime with sandbox protections
2. Loads behavior scripts (single-entity) and collision actions (two-entity)
3. Loads generator scripts for dynamic property values
4. Attaches behaviors to entities
5. Calls behavior lifecycle hooks (on_update, on_hit, on_spawn, on_destroy)
6. Dispatches collision actions when entities collide
7. Manages entity spawning and destruction

Directory structure:
- ams/games/game_engine/lua/behaviors/         - Entity behaviors (single entity)
- ams/games/game_engine/lua/collision_actions/ - Collision actions (two entities)
- ams/games/game_engine/lua/generators/        - Property generators (return computed values)
- ams/input_actions/                           - Input actions (triggered by user input)
"""

from typing import Any, Callable, Optional, TYPE_CHECKING
import uuid

from lupa import LuaRuntime

from .entity import Entity
from .api import LuaAPIBase

if TYPE_CHECKING:
    from ams.content_fs import ContentFS


def _lua_attribute_filter(obj, attr_name, is_setting):
    """Attribute filter for Lua sandbox.

    Blocks access to:
    - Dunder attributes (__class__, __dict__, __module__, etc.)
    - Private attributes (_internal, _cache, etc.)
    - Callable attributes (methods) on Python objects

    This prevents Lua from accessing Python internals or calling methods
    on Python objects that might leak through. Note: This filter only applies
    to Python objects accessed from Lua, not to Lua tables like `ams.*`.
    """
    if attr_name.startswith('__'):
        raise AttributeError(f'Access to {attr_name} is blocked')
    if attr_name.startswith('_'):
        raise AttributeError(f'Access to private attribute {attr_name} is blocked')

    # Block callable attributes (methods) on Python objects
    # This prevents calling methods on objects that might leak through
    if not is_setting:
        try:
            attr = getattr(obj, attr_name, None)
            if attr is not None and callable(attr) and not isinstance(attr, type):
                raise AttributeError(f'Access to callable {attr_name} is blocked')
        except AttributeError:
            raise
        except Exception:
            pass  # If we can't check, allow the access

    return attr_name


class ScheduledCallback:
    """A callback scheduled to run after a delay."""
    def __init__(self, time_remaining: float, callback_name: str, entity_id: str):
        self.time_remaining = time_remaining
        self.callback_name = callback_name
        self.entity_id = entity_id


class LuaEngine:
    """
    Core Lua sandbox engine for game scripting.

    Manages Lua behaviors and entity lifecycle with sandboxed Lua runtime.

    Usage:
        from ams.content_fs import ContentFS

        content_fs = ContentFS(Path('/path/to/repo'))
        engine = LuaEngine(content_fs, screen_width=800, screen_height=600)
        engine.load_behaviors_from_dir()  # Loads from ams/games/game_engine/lua/behaviors/

        entity = engine.create_entity('brick', behaviors=['descend'],
                                       behavior_config={'descend': {'speed': 50}})

        # In game loop:
        engine.update(dt)
        for entity in engine.get_alive_entities():
            render(entity)
    """

    def __init__(
        self,
        content_fs: 'ContentFS',
        screen_width: float = 800,
        screen_height: float = 600,
        api_class: Optional[type] = None,
    ):
        self._content_fs = content_fs
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.score = 0
        self.elapsed_time = 0.0

        # Entity storage
        self.entities: dict[str, Entity] = {}

        # Loaded Lua routines by type (type -> name -> lua function table)
        # Types: 'behavior', 'collision', 'generator', 'input'
        self._routines: dict[str, dict[str, Any]] = {
            'behavior': {},    # Entity lifecycle routines
            'collision': {},   # Collision handler routines
            'generator': {},   # Value generator routines
            'input': {},       # Input action routines
        }

        # Pending entity spawns/destroys (processed end of frame)
        self._pending_spawns: list[Entity] = []
        self._pending_destroys: list[str] = []

        # Scheduled callbacks
        self._scheduled: list[ScheduledCallback] = []

        # Sound queue (processed by game layer)
        self._sound_queue: list[str] = []

        # Spawn callback - allows GameEngine to inject entity type config
        # Signature: (entity_type, x, y, vx, vy, width, height, color, sprite) -> Entity
        self._spawn_callback: Optional[Callable] = None

        # Destroy callback - notifies GameEngine when entity is destroyed
        # Signature: (entity) -> None
        # Called BEFORE entity is removed from dict, allowing orphan handling
        self._destroy_callback: Optional[Callable] = None

        # Initialize Lua with sandbox protections:
        # - register_eval=False: don't expose python.eval()
        # - register_builtins=False: don't expose python.builtins.*
        # - attribute_filter: blocks access to __dunder__ and _private attrs
        # - unpack_returned_tuples: convenience for multi-return values
        # Note: We also clear all globals including 'python' in _setup_lua_environment,
        # but these options provide defense in depth.
        self._lua = LuaRuntime(
            register_eval=False,
            register_builtins=False,
            unpack_returned_tuples=True,
            attribute_filter=_lua_attribute_filter
        )

        # Use provided API class or default to base
        api_cls = api_class or LuaAPIBase
        self._api = api_cls(self)
        self._api.set_lua_runtime(self._lua)  # Enable Lua-safe return value conversion
        self._setup_lua_environment()

    def set_spawn_callback(self, callback: Callable) -> None:
        """Set callback for entity spawning (used by GameEngine to apply type config)."""
        self._spawn_callback = callback

    def set_destroy_callback(self, callback: Callable) -> None:
        """Set callback for entity destruction (used by GameEngine for orphan handling).

        The callback is called BEFORE the entity is removed from the dict,
        allowing orphan handling and other cleanup.
        """
        self._destroy_callback = callback

    def _validate_sandbox(self) -> None:
        """Validate that the Lua sandbox is properly locked down.

        This runs after sandbox setup to catch any regressions. If validation
        fails, it raises RuntimeError to prevent running with a compromised sandbox.
        """
        critical_escapes = [
            # Lupa-injected (most dangerous)
            ('python', 'python bridge gives full interpreter access'),
            ('_python', 'alternate python accessor'),
            # LuaJIT specific
            ('ffi', 'FFI gives raw memory access'),
            ('jit', 'JIT library'),
            # Code loading
            ('load', 'can compile arbitrary bytecode'),
            ('loadstring', 'same as load'),
            ('loadfile', 'load from filesystem'),
            ('dofile', 'execute from filesystem'),
            # Module system
            ('require', 'module loader'),
            ('package', 'package system'),
            ('module', 'legacy module creation'),
            # Debug/introspection
            ('debug', 'full introspection'),
            ('getfenv', 'environment access'),
            ('setfenv', 'environment manipulation'),
            ('getmetatable', 'metatable access'),
            ('setmetatable', 'metatable manipulation'),
            # Raw table access (metatable bypass)
            ('rawget', 'bypass __index'),
            ('rawset', 'bypass __newindex'),
            ('rawequal', 'bypass __eq'),
            ('rawlen', 'bypass __len'),
            # Misc dangerous
            ('_G', 'global table reference'),
            ('collectgarbage', 'GC manipulation'),
            ('newproxy', 'userdata creation'),
            # Libraries
            ('io', 'filesystem access'),
            ('os', 'OS interface'),
            ('coroutine', 'coroutines'),
        ]

        failures = []
        for name, risk in critical_escapes:
            try:
                result = self._lua.eval(f'{name} ~= nil')
                if result:
                    failures.append(f'EXPOSED: {name} - {risk}')
            except Exception:
                pass  # eval failed = not accessible = good

        # Check string.dump via method syntax
        try:
            result = self._lua.eval('("").dump')
            if result is not None:
                failures.append('EXPOSED: string.dump accessible via method syntax')
        except Exception:
            pass

        # Verify ams namespace exists (sanity check)
        try:
            result = self._lua.eval('ams ~= nil')
            if not result:
                failures.append('ERROR: ams namespace missing - sandbox broken')
        except Exception as e:
            failures.append(f'ERROR: cannot verify ams namespace: {e}')

        if failures:
            for f in failures:
                print(f'[LuaEngine] SANDBOX FAILURE: {f}')
            raise RuntimeError(
                f'Lua sandbox validation failed with {len(failures)} issue(s). '
                'This is a security risk - refusing to continue.'
            )

    def _setup_lua_environment(self) -> None:
        """Set up the Lua environment with sandboxed API functions.

        Security model: Opt-in globals only. We clear all default Lua globals
        and expose only the safe subset needed for game behaviors. This prevents
        access to io, os, debug, loadfile, require, package, and the python bridge.
        """
        g = self._lua.globals()

        # Save safe primitives before nuking globals
        # These are needed for basic Lua operations in behavior scripts
        safe_globals = {
            'pairs': g.pairs,        # Iterate tables
            'ipairs': g.ipairs,      # Iterate arrays
            'type': g.type,          # Type checking
            'tostring': g.tostring,  # String conversion
            'tonumber': g.tonumber,  # Number conversion
            'select': g.select,      # Vararg handling
            'unpack': g.table.unpack if hasattr(g.table, 'unpack') else g.unpack,  # Table unpacking
            'pcall': g.pcall,        # Protected calls (error handling)
            'error': g.error,        # Raise errors
            'next': g.next,          # Table iteration primitive
            'math': g.math,          # Math library (we'll override specific functions)
            # Note: string library omitted - behaviors don't need string manipulation
            # Note: table library omitted - basic table ops work without it
        }

        # Remove dangerous functions from string metatable BEFORE clearing globals
        # string.dump can serialize functions to bytecode - security risk
        # We need getmetatable which will be cleared shortly
        self._lua.execute("""
            local mt = getmetatable("")
            if mt and mt.__index then
                mt.__index.dump = nil  -- Remove string.dump
                mt.__index.rep = nil   -- Remove string.rep (Memory DoS risk)
            end
        """)

        # Nuclear option: clear ALL globals
        for key in list(g.keys()):
            g[key] = None

        # Reinstall only safe globals
        for key, value in safe_globals.items():
            g[key] = value

        # Create 'ams' namespace for our API
        self._lua.execute("ams = {}")
        ams = g.ams

        # Let the API register its methods
        self._api.register_api(ams)

        # Validate sandbox is properly locked down
        self._validate_sandbox()

    def load_behavior(self, name: str, content_path: Optional[str] = None) -> bool:
        """
        Load a behavior script from ContentFS.

        Args:
            name: Behavior name (used as key and for default path lookup)
            content_path: ContentFS path to .lua file. If None, looks in
                         'ams/games/game_engine/lua/behaviors/{name}.lua'

        Returns True if loaded successfully.
        """
        if name in self._routines['behavior']:
            return True  # Already loaded

        if content_path is None:
            content_path = f'ams/games/game_engine/lua/behaviors/{name}.lua'

        if not self._content_fs.exists(content_path):
            print(f"[LuaEngine] Behavior not found: {content_path}")
            return False

        try:
            code = self._content_fs.readtext(content_path)
            # Execute the Lua file - it should return a table with on_update, etc.
            result = self._lua.execute(code)

            # The behavior script should define a table with lifecycle methods
            # Convention: the script returns the behavior table
            if result is None:
                # Alternative: script defines global with behavior name
                g = self._lua.globals()
                result = getattr(g, name, None)

            if result is None:
                print(f"[LuaEngine] Behavior {name} did not return a table")
                return False

            self._routines['behavior'][name] = result
            return True

        except Exception as e:
            print(f"[LuaEngine] Error loading {name}: {e}")
            return False

    def load_inline_behavior(self, name: str, lua_code: str) -> bool:
        """
        Load an inline Lua behavior from a code string.

        The code should define a behavior table with lifecycle methods
        (on_spawn, on_update, on_hit, on_destroy) and return it.

        Example inline behavior in YAML:
            behaviors:
              - lua: |
                  local behavior = {}
                  function behavior.on_update(entity_id, dt)
                      local x = ams.get_x(entity_id) + 10 * dt
                      ams.set_x(entity_id, x)
                  end
                  return behavior

        Args:
            name: Unique name for this inline behavior
            lua_code: Lua source code defining the behavior table

        Returns:
            True if loaded successfully
        """
        if name in self._routines['behavior']:
            return True  # Already loaded

        try:
            # Execute the Lua code - it should return a table
            result = self._lua.execute(lua_code)

            if result is None:
                print(f"[LuaEngine] Inline behavior {name} did not return a table")
                return False

            self._routines['behavior'][name] = result
            return True

        except Exception as e:
            print(f"[LuaEngine] Error loading inline behavior {name}: {e}")
            return False

    def load_behaviors_from_dir(self, content_dir: Optional[str] = None) -> int:
        """Load all .lua files from ContentFS directory.

        Args:
            content_dir: ContentFS path to directory (e.g., 'ams/games/game_engine/lua/behaviors').
                        If None, uses default 'ams/games/game_engine/lua/behaviors'.

        Returns count loaded.
        """
        if content_dir is None:
            content_dir = 'ams/games/game_engine/lua/behaviors'

        count = 0
        if self._content_fs.exists(content_dir):
            for item in self._content_fs.listdir(content_dir):
                if item.endswith('.lua'):
                    name = item[:-4]  # Remove .lua extension
                    content_path = f'{content_dir}/{item}'
                    if self.load_behavior(name, content_path):
                        count += 1
        return count

    def load_collision_action(self, name: str, content_path: Optional[str] = None) -> bool:
        """
        Load a collision action script from ContentFS.

        Collision actions handle two-entity interactions (collisions).
        They expose an `execute(entity_a_id, entity_b_id, modifier)` function.

        Args:
            name: Action name
            content_path: ContentFS path. If None, looks in
                         'ams/games/game_engine/lua/collision_actions/{name}.lua'

        Returns True if loaded successfully.
        """
        if name in self._routines['collision']:
            return True  # Already loaded

        if content_path is None:
            content_path = f'ams/games/game_engine/lua/collision_actions/{name}.lua'

        if not self._content_fs.exists(content_path):
            print(f"[LuaEngine] Collision action not found: {content_path}")
            return False

        try:
            code = self._content_fs.readtext(content_path)
            result = self._lua.execute(code)

            if result is None:
                g = self._lua.globals()
                result = getattr(g, name, None)

            if result is None:
                print(f"[LuaEngine] Collision action {name} did not return a table")
                return False

            self._routines['collision'][name] = result
            return True

        except Exception as e:
            print(f"[LuaEngine] Error loading collision action {name}: {e}")
            return False

    def load_collision_actions_from_dir(self, content_dir: Optional[str] = None) -> int:
        """Load all collision action .lua files from ContentFS directory."""
        if content_dir is None:
            content_dir = 'ams/games/game_engine/lua/collision_actions'

        count = 0
        if self._content_fs.exists(content_dir):
            for item in self._content_fs.listdir(content_dir):
                if item.endswith('.lua'):
                    name = item[:-4]
                    content_path = f'{content_dir}/{item}'
                    if self.load_collision_action(name, content_path):
                        count += 1
        return count

    def load_inline_collision_action(self, name: str, lua_code: str) -> bool:
        """
        Load an inline collision action from a Lua code string.

        The code should define a table with an `execute(entity_a_id, entity_b_id, modifier)`
        function and return it.

        Example inline collision action in YAML:
            collision_behaviors:
              ball:
                brick:
                  action:
                    lua: |
                      local action = {}
                      function action.execute(a_id, b_id, modifier)
                          ams.destroy(b_id)
                          ams.add_score(100)
                      end
                      return action

        Args:
            name: Unique name for this inline collision action
            lua_code: Lua source code defining the action table

        Returns:
            True if loaded successfully
        """
        if name in self._routines['collision']:
            return True  # Already loaded

        try:
            result = self._lua.execute(lua_code)

            if result is None:
                print(f"[LuaEngine] Inline collision action {name} did not return a table")
                return False

            self._routines['collision'][name] = result
            return True

        except Exception as e:
            print(f"[LuaEngine] Error loading inline collision action {name}: {e}")
            return False

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
        if action_name not in self._routines['collision']:
            if not self.load_collision_action(action_name):
                return False

        action = self._routines['collision'].get(action_name)
        if not action:
            return False

        execute_fn = getattr(action, 'execute', None)
        if not execute_fn:
            print(f"[LuaEngine] Collision action {action_name} has no execute function")
            return False

        try:
            # Convert modifier dict to Lua table if provided
            lua_modifier = None
            if modifier:
                lua_modifier = self._lua.table_from(modifier)

            execute_fn(entity_a.id, entity_b.id, lua_modifier)
            return True

        except Exception as e:
            print(f"[LuaEngine] Error executing collision action {action_name}: {e}")
            return False

    # =========================================================================
    # Input Actions
    # =========================================================================

    def load_input_action(self, name: str, content_path: Optional[str] = None) -> bool:
        """
        Load an input action script from ContentFS.

        Input actions are triggered by user input (clicks, touches, etc.).
        They expose an `execute(x, y, args)` function that receives:
        - x, y: Input position in screen coordinates
        - args: Lua table of action arguments from YAML config

        Args:
            name: Action name
            content_path: ContentFS path. If None, looks in
                         'ams/input_actions/{name}.lua'

        Returns True if loaded successfully.
        """
        if name in self._routines['input']:
            return True  # Already loaded

        if content_path is None:
            content_path = f'ams/input_actions/{name}.lua'

        if not self._content_fs.exists(content_path):
            print(f"[LuaEngine] Input action file not found: {content_path}")
            return False

        try:
            lua_code = self._content_fs.readtext(content_path)
            result = self._lua.execute(lua_code)

            if result is None or not hasattr(result, 'execute'):
                print(f"[LuaEngine] Input action {name} did not return a table with execute function")
                return False

            self._routines['input'][name] = result
            return True

        except Exception as e:
            print(f"[LuaEngine] Error loading input action {name}: {e}")
            return False

    def load_inline_input_action(self, name: str, lua_code: str) -> bool:
        """
        Load an inline input action from a Lua code string.

        The code should define a table with an `execute(x, y, args)` function
        and return it.

        Example inline input action in YAML:
            global_on_input:
              action:
                lua: |
                  local action = {}
                  function action.execute(x, y, args)
                      ams.play_sound("shot")
                      -- Custom logic here
                  end
                  return action

        Args:
            name: Unique name for this inline input action
            lua_code: Lua source code defining the action table

        Returns:
            True if loaded successfully
        """
        if name in self._routines['input']:
            return True  # Already loaded

        try:
            result = self._lua.execute(lua_code)

            if result is None or not hasattr(result, 'execute'):
                print(f"[LuaEngine] Inline input action {name} did not return a table with execute function")
                return False

            self._routines['input'][name] = result
            return True

        except Exception as e:
            print(f"[LuaEngine] Error loading inline input action {name}: {e}")
            return False

    def execute_input_action(
        self,
        action_name: str,
        x: float,
        y: float,
        args: Optional[dict[str, Any]] = None
    ) -> bool:
        """
        Execute an input action.

        Args:
            action_name: Name of the input action to execute
            x: Input x position in screen coordinates
            y: Input y position in screen coordinates
            args: Optional arguments dict passed to the action

        Returns:
            True if action executed successfully
        """
        # Load action if not already loaded
        if action_name not in self._routines['input']:
            if not self.load_input_action(action_name):
                return False

        action = self._routines['input'].get(action_name)
        if not action:
            return False

        execute_fn = getattr(action, 'execute', None)
        if not execute_fn:
            print(f"[LuaEngine] Input action {action_name} has no execute function")
            return False

        try:
            # Convert args dict to Lua table if provided
            lua_args = None
            if args:
                lua_args = self._lua.table_from(args)

            execute_fn(x, y, lua_args)
            return True

        except Exception as e:
            print(f"[LuaEngine] Error executing input action {action_name}: {e}")
            return False

    def load_generator(self, name: str, content_path: Optional[str] = None) -> bool:
        """
        Load a property generator script from ContentFS.

        Property generators compute dynamic property values. They expose a
        `generate(args)` function that takes a Lua table of arguments and
        returns a computed value.

        Use case: Complex property calculations like grid positions, color
        interpolation, pattern generation, etc.

        Args:
            name: Generator name
            content_path: ContentFS path. If None, looks in
                         'ams/games/game_engine/lua/generators/{name}.lua'

        Returns True if loaded successfully.
        """
        if name in self._routines['generator']:
            return True  # Already loaded

        if content_path is None:
            content_path = f'ams/games/game_engine/lua/generators/{name}.lua'

        if not self._content_fs.exists(content_path):
            print(f"[LuaEngine] Generator not found: {content_path}")
            return False

        try:
            code = self._content_fs.readtext(content_path)
            result = self._lua.execute(code)

            if result is None:
                g = self._lua.globals()
                result = getattr(g, name, None)

            if result is None:
                print(f"[LuaEngine] Generator {name} did not return a table")
                return False

            self._routines['generator'][name] = result
            return True

        except Exception as e:
            print(f"[LuaEngine] Error loading generator {name}: {e}")
            return False

    def load_generators_from_dir(self, content_dir: Optional[str] = None) -> int:
        """Load all generator .lua files from ContentFS directory.

        Args:
            content_dir: ContentFS path to directory (e.g., 'ams/games/game_engine/lua/generators').
                        If None, uses default 'ams/games/game_engine/lua/generators'.

        Returns count loaded.
        """
        if content_dir is None:
            content_dir = 'ams/games/game_engine/lua/generators'

        count = 0
        if self._content_fs.exists(content_dir):
            for item in self._content_fs.listdir(content_dir):
                if item.endswith('.lua'):
                    name = item[:-4]  # Remove .lua extension
                    content_path = f'{content_dir}/{item}'
                    if self.load_generator(name, content_path):
                        count += 1
        return count

    def call_generator(self, name: str, args: Optional[dict[str, Any]] = None) -> Any:
        """
        Call a property generator to compute a value.

        Args:
            name: Name of the generator (must be loaded or loadable)
            args: Arguments to pass to the generator (converted to Lua table)

        Returns:
            The computed value from the generator

        Usage in YAML:
            property: {call: "grid_position", args: {row: 1, col: 5}}
        """
        # Load generator if not already loaded
        if name not in self._routines['generator']:
            if not self.load_generator(name):
                return None

        generator = self._routines['generator'].get(name)
        if not generator:
            return None

        generate_fn = getattr(generator, 'generate', None)
        if not generate_fn:
            print(f"[LuaEngine] Generator {name} has no generate function")
            return None

        try:
            # Convert args dict to Lua table if provided
            lua_args = None
            if args:
                lua_args = self._lua.table_from(args)

            result = generate_fn(lua_args)
            return result

        except Exception as e:
            print(f"[LuaEngine] Error calling generator {name}: {e}")
            return None

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
        # Lazy import to avoid circular dependency
        from ams.games.game_engine.entity import GameEntity

        entity_id = f"{entity_type}_{uuid.uuid4().hex[:8]}"

        entity = GameEntity(
            id=entity_id,
            entity_type=entity_type,
            x=x,
            y=y,
            width=width,
            height=height,
            behaviors=behaviors or [],
            behavior_config=behavior_config or {},
            spawn_time=self.elapsed_time,
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

        If a spawn callback is registered (by GameEngine), uses that to apply
        entity type config from game.yaml. Otherwise creates directly.

        Returns entity ID.
        """
        # Use spawn callback if available (applies entity type config)
        if self._spawn_callback:
            entity = self._spawn_callback(entity_type, x, y, vx, vy, width, height, color, sprite)
            if entity:
                return entity.id
            # Fallback to direct create if callback returns None

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

    def evaluate_expression(self, expression: str) -> Any:
        """Evaluate a Lua expression or block and return the result.

        Supports two modes:
        1. Single-line expression: Evaluated directly
           angle: {lua: "ams.random_range(-60, -120)"}

        2. Multiline block: Executed as function body, returns last expression
           win_condition:
             lua: |
               local bricks = ams.count_entities_by_tag("brick")
               return bricks == 0

        The ams.* API is available in both modes.

        Args:
            expression: Lua expression or block string

        Returns:
            Evaluated result (any type - number, boolean, table, etc.)
        """
        try:
            # Check if multiline (contains newlines or 'return')
            is_multiline = '\n' in expression or expression.strip().startswith('return') \
                          or 'local ' in expression

            if is_multiline:
                # Wrap in function and execute to get return value
                # Strip leading/trailing whitespace but preserve internal structure
                code = expression.strip()

                # Ensure there's a return statement if not present
                if not code.startswith('return') and 'return ' not in code:
                    # Wrap entire block as return value
                    code = f"return {code}"

                # Create anonymous function and call it immediately
                wrapped = f"return (function()\n{code}\nend)()"
                result = self._lua.execute(wrapped)
                return result
            else:
                # Simple expression - use eval
                result = self._lua.eval(expression)
                return result

        except Exception as e:
            print(f"[LuaEngine] Lua error in expression: {e}")
            print(f"  Expression: {expression[:100]}...")
            return None

    def set_global(self, name: str, value: Any) -> None:
        """Set a global variable in the Lua environment.

        Used to pass iteration context (like 'i' in count loops) to Lua expressions.
        """
        self._lua.globals()[name] = value

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
            entity = self.entities.get(eid)
            if entity:
                # Notify GameEngine BEFORE removing (for orphan handling)
                if self._destroy_callback:
                    self._destroy_callback(entity)
                # Now remove from dict and call on_destroy
                self.entities.pop(eid)
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
            behavior = self._routines['behavior'].get(behavior_name)
            if behavior is None:
                continue

            method = getattr(behavior, method_name, None)
            if method is None:
                continue

            try:
                method(entity.id, *args)
            except Exception as e:
                print(f"[LuaEngine] Error in {behavior_name}.{method_name}: {e}")

    def _call_scheduled_callback(self, scheduled: ScheduledCallback) -> None:
        """Execute a scheduled callback."""
        entity = self.entities.get(scheduled.entity_id)
        if entity is None or not entity.alive:
            return

        for behavior_name in entity.behaviors:
            behavior = self._routines['behavior'].get(behavior_name)
            if behavior is None:
                continue

            callback = getattr(behavior, scheduled.callback_name, None)
            if callback:
                try:
                    callback(entity.id)
                except Exception as e:
                    print(f"[LuaEngine] Error in scheduled {scheduled.callback_name}: {e}")

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
