"""
Lua Engine - Core Lua sandbox and runtime for game scripting.

The engine:
1. Initializes the Lua runtime with sandbox protections
2. Loads Lua subroutines of various types (behavior, collision_action, etc.)
3. Stores and manages entity lifecycle (creation delegated to game engine)
4. Delegates lifecycle events to a LifecycleProvider (e.g., GameEngine)
5. Executes collision actions, input actions, and generators

Subroutine types are not hardcoded - they're discovered dynamically from ContentFS
directory names. Common types include:
- behavior: Single-entity scripts with lifecycle hooks (on_update, on_spawn, etc.)
- collision_action: Two-entity interaction handlers with execute(a_id, b_id, modifier)
- generator: Property value generators with generate(args)
- input_action: User input handlers with execute(x, y, args)
"""

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Optional, Protocol, TYPE_CHECKING

from lupa import LuaRuntime

from .entity import Entity
from .api import LuaAPIBase
from ams import profiling

if TYPE_CHECKING:
    from ams.content_fs import ContentFS

# ScriptLoader for .lua.yaml support - loaded lazily to avoid circular import
HAS_SCRIPT_LOADER = False
ScriptLoader = None
ScriptMetadata = None

def _init_script_loader():
    """Lazy init ScriptLoader to avoid circular import at module load time."""
    global HAS_SCRIPT_LOADER, ScriptLoader, ScriptMetadata
    if HAS_SCRIPT_LOADER or ScriptLoader is not None:
        return  # Already initialized
    try:
        from ams.games.game_engine.lua.script_loader import ScriptLoader as SL, ScriptMetadata as SM
        ScriptLoader = SL
        ScriptMetadata = SM
        HAS_SCRIPT_LOADER = True
    except ImportError as e:
        print(f"[LuaEngine] ScriptLoader import failed: {e}")
        HAS_SCRIPT_LOADER = False


class LifecycleProvider(Protocol):
    """Protocol for dispatching lifecycle events to entity subroutines.

    GameEngine implements this to handle behavior-specific lifecycle dispatch.
    LuaEngine remains generic and delegates lifecycle calls to the provider.
    """

    def on_entity_spawned(self, entity: Entity, lua_engine: 'LuaEngine') -> None:
        """Called when an entity is created and registered."""
        ...

    def on_entity_update(self, entity: Entity, lua_engine: 'LuaEngine', dt: float) -> None:
        """Called each frame for alive entities."""
        ...

    def on_entity_destroyed(self, entity: Entity, lua_engine: 'LuaEngine') -> None:
        """Called when an entity is destroyed and about to be removed."""
        ...

    def dispatch_lifecycle(
        self, hook_name: str, entity: Entity, lua_engine: 'LuaEngine', *args
    ) -> None:
        """Dispatch a generic lifecycle hook (on_hit, etc.) to entity subroutines."""
        ...

    def dispatch_scheduled(
        self, callback_name: str, entity: Entity, lua_engine: 'LuaEngine'
    ) -> None:
        """Dispatch a scheduled callback to entity's attached subroutines."""
        ...


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

    Manages Lua subroutines and entity lifecycle with sandboxed Lua runtime.
    Entity creation is delegated to the game engine via register_entity().

    Usage:
        from ams.content_fs import ContentFS

        content_fs = ContentFS(Path('/path/to/repo'))
        engine = LuaEngine(content_fs, screen_width=800, screen_height=600)

        # Set lifecycle provider (GameEngine implements this)
        engine.set_lifecycle_provider(game_engine)

        # Load subroutines by type and directory
        engine.load_subroutines_from_dir('behavior', 'ams/games/game_engine/lua/behavior')
        engine.load_subroutines_from_dir('collision_action', 'ams/games/game_engine/lua/collision_action')

        # Entity creation is done by GameEngine, then registered here
        entity = GameEntity(id='brick_001', entity_type='brick', ...)
        engine.register_entity(entity)  # Triggers on_entity_spawned

        # In game loop:
        engine.update(dt)  # Calls on_entity_update/on_entity_destroyed via provider
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

        # Loaded Lua subroutines by type (type -> name -> lua function table)
        # Types are discovered dynamically from ContentFS folder names
        # e.g., 'behavior', 'collision_action', 'generator', 'input_action'
        self._subroutines: defaultdict[str, dict[str, Any]] = defaultdict(dict)

        # Pending entity spawns/destroys (processed end of frame)
        self._pending_spawns: list[Entity] = []
        self._pending_destroys: list[str] = []

        # Scheduled callbacks
        self._scheduled: list[ScheduledCallback] = []

        # Sound queue (processed by game layer)
        self._sound_queue: list[str] = []

        # Destroy callback - notifies GameEngine when entity is destroyed
        # Signature: (entity) -> None
        # Called BEFORE entity is removed from dict, allowing orphan handling
        self._destroy_callback: Optional[Callable] = None

        # Lifecycle provider - dispatches lifecycle events to entity subroutines
        # GameEngine implements this to handle behavior-specific dispatch
        self._lifecycle_provider: Optional[LifecycleProvider] = None

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

    @property
    def api(self) -> LuaAPIBase:
        """Get the Lua API instance for configuration."""
        return self._api

    def set_destroy_callback(self, callback: Callable) -> None:
        """Set callback for entity destruction (used by GameEngine for orphan handling).

        The callback is called BEFORE the entity is removed from the dict,
        allowing orphan handling and other cleanup.
        """
        self._destroy_callback = callback

    def set_lifecycle_provider(self, provider: LifecycleProvider) -> None:
        """Set the lifecycle provider for dispatching lifecycle events.

        The provider handles dispatching lifecycle methods (on_update, on_spawn, etc.)
        to entity-attached subroutines. GameEngine implements this protocol.
        """
        self._lifecycle_provider = provider

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

    # =========================================================================
    # Generic Subroutine Loading
    # =========================================================================

    def load_inline_subroutine(self, sub_type: str, name: str, lua_code: str) -> bool:
        """Load an inline Lua subroutine from a code string.

        Args:
            sub_type: Subroutine type (e.g., 'behavior', 'collision_action')
            name: Unique name for this subroutine
            lua_code: Lua source code (should return a table)

        Returns:
            True if loaded successfully
        """
        if name in self._subroutines[sub_type]:
            return True  # Already loaded

        try:
            result = self._lua.execute(lua_code)

            if result is None:
                print(f"[LuaEngine] Inline {sub_type}/{name} did not return a table")
                return False

            self._subroutines[sub_type][name] = result
            return True

        except Exception as e:
            print(f"[LuaEngine] Error loading inline {sub_type}/{name}: {e}")
            return False

    def load_subroutines_from_dir(self, sub_type: str, content_dir: str) -> int:
        """Load all .lua.yaml files from a ContentFS directory.

        Args:
            sub_type: Subroutine type (e.g., 'behavior', 'collision_action')
            content_dir: ContentFS path to directory

        Returns:
            Count of subroutines loaded
        """
        count = 0
        if not self._content_fs.exists(content_dir):
            return count

        for item in self._content_fs.listdir(content_dir):
            if item.endswith('.lua.yaml'):
                name = item[:-9]  # Remove .lua.yaml extension
                content_path = f'{content_dir}/{item}'
                if self._load_yaml_subroutine(sub_type, name, content_path):
                    count += 1

        return count

    def _load_yaml_subroutine(self, sub_type: str, name: str, content_path: str) -> bool:
        """Load a .lua.yaml subroutine using ScriptLoader.

        Args:
            sub_type: Subroutine type
            name: Subroutine name
            content_path: ContentFS path to .lua.yaml file

        Returns:
            True if loaded successfully
        """
        if name in self._subroutines[sub_type]:
            return True  # Already loaded

        # Lazy init ScriptLoader (avoids circular import at module load time)
        _init_script_loader()

        if not HAS_SCRIPT_LOADER:
            # Fall back to treating as raw Lua (just extract code)
            print(f"[LuaEngine._load_yaml_subroutine] ScriptLoader not available, skipping {content_path}")
            return False

        if not self._content_fs.exists(content_path):
            print(f"[LuaEngine._load_yaml_subroutine] Subroutine not found: {content_path}")
            return False

        try:
            # Read YAML content
            yaml_content = self._content_fs.readtext(content_path)

            # Parse YAML using ams.yaml (handles both YAML and JSON formats)
            from ams.yaml import loads as yaml_loads
            data = yaml_loads(yaml_content, format='yaml')

            # Create ScriptMetadata via ScriptLoader
            loader = ScriptLoader(validate=False)  # Schema validation optional
            script = loader.load_inline(name, sub_type, data)

            # Execute the Lua code
            result = self._lua.execute(script.code)

            if result is None:
                g = self._lua.globals()
                result = getattr(g, name, None)

            if result is None:
                print(f"[LuaEngine._load_yaml_subroutine] Subroutine {name} did not return a table")
                return False

            self._subroutines[sub_type][name] = result
            print(f"[LuaEngine._load_yaml_subroutine] Subroutine loaded: [{sub_type}][{name}] from {content_path}")

            return True

        except Exception as e:
            print(f"[LuaEngine._load_yaml_subroutine] Error loading {sub_type}/{name}.lua.yaml: {e}")
            return False

    def get_subroutine(self, sub_type: str, name: str) -> Optional[Any]:
        """Get a loaded subroutine by type and name."""
        return self._subroutines[sub_type].get(name)

    def has_subroutine(self, sub_type: str, name: str) -> bool:
        """Check if a subroutine is loaded."""
        return name in self._subroutines[sub_type]

    # =========================================================================
    # Subroutine Execution (collision actions, input actions, generators)
    # =========================================================================

    @profiling.profile("lua_engine", "Collision Action")
    def execute_collision_action(
        self,
        action_name: str,
        entity_a: Entity,
        entity_b: Entity,
        modifier: Optional[dict[str, Any]] = None,
        default_path: str = 'lua/collision_action',
        sub_type: str = 'collision_action'
    ) -> bool:
        """
        Execute a collision action between two entities.

        Args:
            action_name: Name of the collision action to execute
            entity_a: First entity in collision (the one whose collision rule triggered)
            entity_b: Second entity in collision
            modifier: Optional config dict passed to the action
            default_path: Default ContentFS directory to look for actions
            sub_type: Subroutine type (e.g., 'collision_action', 'interaction_action')

        Returns:
            True if action executed successfully
        """
        # Load action if not already loaded (.lua.yaml format only)
        if not self.has_subroutine(sub_type, action_name):
            yaml_path = f'{default_path}/{action_name}.lua.yaml'
            if not self._load_yaml_subroutine(sub_type, action_name, yaml_path):
                return False

        action = self.get_subroutine(sub_type, action_name)
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
            print(f"  entity_a: {entity_a.id} (type={entity_a.entity_type})")
            print(f"  entity_b: {entity_b.id} (type={entity_b.entity_type})")
            if modifier:
                print(f"  modifier: {modifier}")
            return False

    @profiling.profile("lua_engine", "Interaction Action")
    def execute_interaction_action(
        self,
        action_name: str,
        entity_a: Entity,
        entity_b: Entity,
        modifier: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Execute an interaction action between two entities.

        This is the unified interactions system entry point. Actions receive:
        - entity_a_id, entity_b_id: The interacting entities
        - modifier: User-defined config from YAML
        - context: Runtime context (trigger, distance, angle, target position)

        Args:
            action_name: Name of the interaction action to execute
            entity_a: Source entity
            entity_b: Target entity (or system entity stub)
            modifier: Optional config dict from YAML
            context: Runtime context (trigger, distance, angle, target_x/y, etc.)

        Returns:
            True if action executed successfully
        """
        # Load action if not already loaded
        if not self.has_subroutine('interaction_action', action_name):
            yaml_path = f'lua/interaction_action/{action_name}.lua.yaml'
            if not self._load_yaml_subroutine('interaction_action', action_name, yaml_path):
                return False

        action = self.get_subroutine('interaction_action', action_name)
        if not action:
            return False

        execute_fn = getattr(action, 'execute', None)
        if not execute_fn:
            print(f"[LuaEngine] Interaction action {action_name} has no execute function")
            return False

        try:
            # Convert dicts to Lua tables
            lua_modifier = self._lua.table_from(modifier) if modifier else self._lua.table()
            lua_context = self._lua.table_from(context) if context else self._lua.table()

            execute_fn(entity_a.id, entity_b.id, lua_modifier, lua_context)
            return True

        except Exception as e:
            print(f"[LuaEngine] Error executing interaction action {action_name}: {e}")
            print(f"  entity_a: {entity_a.id} (type={entity_a.entity_type})")
            print(f"  entity_b: {entity_b.id} (type={entity_b.entity_type})")
            if modifier:
                print(f"  modifier: {modifier}")
            if context:
                print(f"  context: {context}")
            import traceback
            exc = e
            if exc:
                tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
            else:
                tb_lines = traceback.format_exc().split('\n')

            for line in tb_lines:
                if line.strip():
                    print(line)
            return False

    @profiling.profile("lua_engine", "Input Action")
    def execute_input_action(
        self,
        action_name: str,
        x: float,
        y: float,
        args: Optional[dict[str, Any]] = None,
        default_path: str = 'ams/input_action'
    ) -> bool:
        """
        Execute an input action.

        Args:
            action_name: Name of the input action to execute
            x: Input x position in screen coordinates
            y: Input y position in screen coordinates
            args: Optional arguments dict passed to the action
            default_path: Default ContentFS directory to look for actions

        Returns:
            True if action executed successfully
        """
        # Load action if not already loaded (.lua.yaml format only)
        if not self.has_subroutine('input_action', action_name):
            yaml_path = f'{default_path}/{action_name}.lua.yaml'
            if not self._load_yaml_subroutine('input_action', action_name, yaml_path):
                return False

        action = self.get_subroutine('input_action', action_name)
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

    def call_generator(
        self,
        name: str,
        args: Optional[dict[str, Any]] = None,
        default_path: str = 'lua/generator'
    ) -> Any:
        """
        Call a property generator to compute a value.

        Args:
            name: Name of the generator (must be loaded or loadable)
            args: Arguments to pass to the generator (converted to Lua table)
            default_path: Default ContentFS directory to look for generators

        Returns:
            The computed value from the generator

        Usage in YAML:
            property: {call: "grid_position", args: {row: 1, col: 5}}
        """
        # Load generator if not already loaded (.lua.yaml format only)
        if not self.has_subroutine('generator', name):
            yaml_path = f'{default_path}/{name}.lua.yaml'
            if not self._load_yaml_subroutine('generator', name, yaml_path):
                return None

        generator = self.get_subroutine('generator', name)
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

    def register_entity(self, entity: Entity) -> None:
        """Register an entity created by the game engine.

        The game engine is responsible for creating entities with the appropriate
        concrete type. LuaEngine only stores and manages lifecycle.

        Args:
            entity: Entity to register (must have unique id)
        """
        self.entities[entity.id] = entity

        # Notify lifecycle provider of spawn
        if self._lifecycle_provider:
            self._lifecycle_provider.on_entity_spawned(entity, self)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self.entities.get(entity_id)

    def get_alive_entities(self) -> list[Entity]:
        """Get all alive entities."""
        return [e for e in self.entities.values() if e.alive]

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

    @profiling.profile("lua_engine", "Lua Entity Updates")
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
        if self._lifecycle_provider:
            for entity in list(self.entities.values()):
                if entity.alive:
                    self._lifecycle_provider.on_entity_update(entity, self, dt)

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
                if self._lifecycle_provider:
                    self._lifecycle_provider.on_entity_destroyed(entity, self)

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
        """Call a lifecycle method via the lifecycle provider."""
        if self._lifecycle_provider:
            self._lifecycle_provider.dispatch_lifecycle(method_name, entity, self, *args)

    def _call_scheduled_callback(self, scheduled: ScheduledCallback) -> None:
        """Execute a scheduled callback via the lifecycle provider."""
        entity = self.entities.get(scheduled.entity_id)
        if entity is None or not entity.alive:
            return

        if self._lifecycle_provider:
            self._lifecycle_provider.dispatch_scheduled(scheduled.callback_name, entity, self)

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
        if self._lifecycle_provider:
            for entity in self.entities.values():
                self._lifecycle_provider.on_entity_destroyed(entity, self)

        self.entities.clear()
        self._scheduled.clear()
        self._sound_queue.clear()
        self.score = 0
        self.elapsed_time = 0.0
