"""
Browser Lua Bridge - Routes Lua execution through JavaScript Fengari.

This module provides LuaEngineBrowser, a drop-in replacement for LuaEngine
that executes Lua code in JavaScript via Fengari (pure JS Lua 5.3). Game state
is serialized to JavaScript before Lua execution and changes are applied after.

Architecture:
    Python (GameEngine)     JavaScript (Fengari)
           │                        │
           │  serialize_state()     │
           │ ──────────────────────>│
           │                        │
           │  execute Lua behaviors │
           │                        │
           │  state_changes         │
           │ <──────────────────────│
           │                        │
           │  apply_changes()       │
           │                        │

This avoids async back-and-forth during Lua execution - all ams.* calls
operate on a local snapshot in JavaScript. Fengari is synchronous, unlike
WASMOON, which means cleaner execution flow and no memory corruption issues.
"""

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, TYPE_CHECKING

if sys.platform == "emscripten":
    import platform as browser_platform

if TYPE_CHECKING:
    from ams.content_fs_browser import ContentFSBrowser


def js_log(msg: str) -> None:
    """Log to browser console."""
    print(msg)
    if sys.platform == "emscripten":
        try:
            browser_platform.window.console.log(msg)
        except:
            pass


class LifecycleProvider(Protocol):
    """Protocol for lifecycle event dispatch (same as native LuaEngine)."""

    def on_entity_spawned(self, entity: 'EntityBrowser', lua_engine: 'LuaEngineBrowser') -> None:
        ...

    def on_entity_update(self, entity: 'EntityBrowser', lua_engine: 'LuaEngineBrowser', dt: float) -> None:
        ...

    def on_entity_destroyed(self, entity: 'EntityBrowser', lua_engine: 'LuaEngineBrowser') -> None:
        ...

    def dispatch_lifecycle(
        self, hook_name: str, entity: 'EntityBrowser', lua_engine: 'LuaEngineBrowser', *args
    ) -> None:
        ...

    def dispatch_scheduled(
        self, callback_name: str, entity: 'EntityBrowser', lua_engine: 'LuaEngineBrowser'
    ) -> None:
        ...


@dataclass
class EntityBrowser:
    """Browser-compatible entity with same interface as native Entity/GameEntity."""

    id: str
    entity_type: str
    alive: bool = True
    properties: Dict[str, Any] = field(default_factory=dict)

    # GameEntity fields
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    width: float = 32.0
    height: float = 32.0
    color: str = "white"
    sprite: str = ""
    health: int = 1
    visible: bool = True
    behaviors: List[str] = field(default_factory=list)
    behavior_config: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    spawn_time: float = 0.0

    # Parent-child relationships
    parent_id: Optional[str] = None
    parent_offset: tuple = (0.0, 0.0)
    children: List[str] = field(default_factory=list)

    def destroy(self) -> None:
        """Mark entity for destruction."""
        self.alive = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entity for JavaScript."""
        return {
            'id': self.id,
            'entity_type': self.entity_type,
            'alive': self.alive,
            'x': self.x,
            'y': self.y,
            'vx': self.vx,
            'vy': self.vy,
            'width': self.width,
            'height': self.height,
            'color': self.color,
            'sprite': self.sprite,
            'health': self.health,
            'visible': self.visible,
            'behaviors': self.behaviors,
            'behavior_config': self.behavior_config,
            'tags': self.tags,
            'properties': self.properties,
            'spawn_time': self.spawn_time,
            'parent_id': self.parent_id,
            'parent_offset': list(self.parent_offset),
            'children': self.children,
        }

    def apply_changes(self, changes: Dict[str, Any]) -> None:
        """Apply changes from JavaScript execution."""
        for key, value in changes.items():
            if key == 'properties':
                self.properties.update(value)
            elif key == 'parent_offset':
                self.parent_offset = tuple(value)
            elif key == 'children':
                self.children = list(value)
            elif hasattr(self, key):
                setattr(self, key, value)


@dataclass
class ScheduledCallback:
    """A callback scheduled to run after a delay."""
    time_remaining: float
    callback_name: str
    entity_id: str


class LuaEngineBrowser:
    """
    Browser-compatible Lua engine using Fengari via JavaScript.

    Provides the same interface as native LuaEngine but executes Lua
    in JavaScript. State is serialized before execution and changes
    are applied after.
    """

    def __init__(
        self,
        content_fs: 'ContentFSBrowser',
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
        self.entities: Dict[str, EntityBrowser] = {}

        # Loaded subroutines (just track names - actual code is in JS)
        self._subroutines: defaultdict[str, set] = defaultdict(set)

        # Lifecycle provider
        self._lifecycle_provider: Optional[LifecycleProvider] = None
        self._destroy_callback: Optional[Callable] = None

        # Scheduled callbacks
        self._scheduled: List[ScheduledCallback] = []

        # Sound queue
        self._sound_queue: List[str] = []

        # Pending spawns from Lua (collected during JS execution)
        self._pending_spawns: List[Dict[str, Any]] = []

        # API instance (for compatibility - not actually used in browser)
        self._api = None
        if api_class:
            # Create API but it won't be used - JS has its own implementation
            pass

        # Initialize Fengari in JavaScript
        self._init_fengari()

    @property
    def api(self):
        """Get API instance (for compatibility)."""
        return self._api

    def _init_fengari(self) -> None:
        """Initialize Fengari in JavaScript."""
        if sys.platform != "emscripten":
            return

        js_log("[LuaEngineBrowser] Initializing Fengari...")

        # Send init message to JavaScript
        self._send_to_js('lua_init', {
            'screen_width': self.screen_width,
            'screen_height': self.screen_height,
        })

    def _send_to_js(self, msg_type: str, data: Dict[str, Any]) -> None:
        """Send message to JavaScript."""
        if sys.platform != "emscripten":
            return

        try:
            message = json.dumps({
                'source': 'lua_engine',
                'type': msg_type,
                'data': data,
            })
            browser_platform.window.postMessage(message, '*')
        except Exception as e:
            js_log(f"[LuaEngineBrowser] Error sending to JS: {e}")

    def _get_js_response(self, response_type: str) -> Optional[Dict[str, Any]]:
        """Get response from JavaScript (polling)."""
        if sys.platform != "emscripten":
            return None

        try:
            # Check for response in global lua_responses array
            if hasattr(browser_platform.window, 'luaResponses'):
                responses = browser_platform.window.luaResponses
                for i in range(len(responses)):
                    resp_str = responses[i]
                    try:
                        resp = json.loads(resp_str)
                        if resp.get('type') == response_type:
                            responses.splice(i, 1)  # Remove from array
                            return resp.get('data')
                    except:
                        pass
        except Exception as e:
            js_log(f"[LuaEngineBrowser] Error getting JS response: {e}")

        return None

    def set_lifecycle_provider(self, provider: LifecycleProvider) -> None:
        """Set lifecycle provider for event dispatch."""
        self._lifecycle_provider = provider

    def set_destroy_callback(self, callback: Callable) -> None:
        """Set callback for entity destruction."""
        self._destroy_callback = callback

    # =========================================================================
    # Subroutine Loading (sends code to JavaScript)
    # =========================================================================

    def load_subroutine(self, sub_type: str, name: str, content_path: str) -> bool:
        """Load a Lua subroutine from ContentFS."""
        if name in self._subroutines[sub_type]:
            return True

        if not self._content_fs.exists(content_path):
            js_log(f"[LuaEngineBrowser] Subroutine not found: {content_path}")
            return False

        try:
            code = self._content_fs.readtext(content_path)
            return self._send_subroutine_to_js(sub_type, name, code)
        except Exception as e:
            js_log(f"[LuaEngineBrowser] Error loading {sub_type}/{name}: {e}")
            return False

    def load_inline_subroutine(self, sub_type: str, name: str, lua_code: str) -> bool:
        """Load an inline Lua subroutine."""
        if name in self._subroutines[sub_type]:
            return True

        return self._send_subroutine_to_js(sub_type, name, lua_code)

    def _send_subroutine_to_js(self, sub_type: str, name: str, code: str) -> bool:
        """Send subroutine code to JavaScript for loading."""
        js_log(f"[LuaEngineBrowser] Sending {sub_type}/{name}")
        self._send_to_js('lua_load_subroutine', {
            'sub_type': sub_type,
            'name': name,
            'code': code,
        })
        self._subroutines[sub_type].add(name)
        return True

    def load_subroutines_from_dir(self, sub_type: str, content_dir: str) -> int:
        """Load all Lua subroutines from a directory.

        Supports multiple formats (in order of preference):
        1. .lua.json - JSON wrapper with code field (browser build from .lua.yaml)
        2. .lua - Raw Lua files (legacy format)
        """
        count = 0
        seen_names: set = set()

        if not self._content_fs.exists(content_dir):
            return 0

        items = self._content_fs.listdir(content_dir)

        # First pass: .lua.json files (preferred - have metadata from .lua.yaml)
        for item in items:
            if item.endswith('.lua.json'):
                name = item[:-9]  # Remove .lua.json
                if name in seen_names:
                    continue
                content_path = f'{content_dir}/{item}'
                if self._load_json_subroutine(sub_type, name, content_path):
                    seen_names.add(name)
                    count += 1

        # Second pass: .lua files (only if no .lua.json version exists)
        for item in items:
            if item.endswith('.lua') and not item.endswith('.lua.json'):
                name = item[:-4]  # Remove .lua
                if name in seen_names:
                    continue
                content_path = f'{content_dir}/{item}'
                if self.load_subroutine(sub_type, name, content_path):
                    seen_names.add(name)
                    count += 1

        return count

    def _load_json_subroutine(self, sub_type: str, name: str, content_path: str) -> bool:
        """Load a Lua subroutine from a .lua.json file (converted from .lua.yaml)."""
        if name in self._subroutines[sub_type]:
            return True

        try:
            json_text = self._content_fs.readtext(content_path)
            data = json.loads(json_text)

            # Extract the lua field from the JSON wrapper
            code = data.get('lua')
            if not code:
                js_log(f"[LuaEngineBrowser] No lua field in {content_path}")
                return False

            return self._send_subroutine_to_js(sub_type, name, code)
        except Exception as e:
            js_log(f"[LuaEngineBrowser] Error loading JSON subroutine {sub_type}/{name}: {e}")
            return False

    def get_subroutine(self, sub_type: str, name: str) -> Optional[Any]:
        """Check if subroutine is loaded (returns truthy for compat)."""
        if name in self._subroutines[sub_type]:
            return True  # Actual subroutine is in JavaScript
        return None

    def has_subroutine(self, sub_type: str, name: str) -> bool:
        """Check if a subroutine is loaded."""
        return name in self._subroutines[sub_type]

    # =========================================================================
    # Entity Management
    # =========================================================================

    def register_entity(self, entity: EntityBrowser) -> None:
        """Register an entity."""
        self.entities[entity.id] = entity

        if self._lifecycle_provider:
            self._lifecycle_provider.on_entity_spawned(entity, self)

    def get_entity(self, entity_id: str) -> Optional[EntityBrowser]:
        """Get entity by ID."""
        return self.entities.get(entity_id)

    def get_alive_entities(self) -> List[EntityBrowser]:
        """Get all alive entities."""
        return [e for e in self.entities.values() if e.alive]

    # =========================================================================
    # Frame Update (batch execution)
    # =========================================================================

    def update(self, dt: float) -> None:
        """Update all entities - executes Lua behaviors in JavaScript."""
        self.elapsed_time += dt

        # Update scheduled callbacks
        for scheduled in self._scheduled[:]:
            scheduled.time_remaining -= dt
            if scheduled.time_remaining <= 0:
                self._call_scheduled_callback(scheduled)
                self._scheduled.remove(scheduled)

        # Execute behavior updates via JavaScript
        self._execute_behavior_updates(dt)

        # Remove dead entities
        dead_ids = [eid for eid, e in self.entities.items() if not e.alive]
        for eid in dead_ids:
            entity = self.entities.get(eid)
            if entity:
                if self._destroy_callback:
                    self._destroy_callback(entity)
                self.entities.pop(eid)
                if self._lifecycle_provider:
                    self._lifecycle_provider.on_entity_destroyed(entity, self)

    def _execute_behavior_updates(self, dt: float) -> None:
        """Execute behavior on_update for all entities via JavaScript."""
        if sys.platform != "emscripten":
            # Native mode - use lifecycle provider directly
            if self._lifecycle_provider:
                for entity in list(self.entities.values()):
                    if entity.alive:
                        self._lifecycle_provider.on_entity_update(entity, self, dt)
            return

        # Browser mode - batch execute in JavaScript
        # Serialize entity state
        entities_data = {}
        for eid, entity in self.entities.items():
            if entity.alive:
                entities_data[eid] = entity.to_dict()

        # Send to JavaScript for execution
        self._send_to_js('lua_update', {
            'dt': dt,
            'elapsed_time': self.elapsed_time,
            'score': self.score,
            'entities': entities_data,
        })

        # Results are processed asynchronously via message queue
        # The game_runtime will poll for lua_update_result and call apply_lua_results

    def apply_lua_results(self, results: Dict[str, Any]) -> None:
        """Apply results from JavaScript Lua execution."""
        # Apply entity changes
        entity_changes = results.get('entities', {})
        for eid, changes in entity_changes.items():
            entity = self.entities.get(eid)
            if entity:
                entity.apply_changes(changes)

        # Update score
        if 'score' in results:
            self.score = results['score']

        # Process spawns
        for spawn_data in results.get('spawns', []):
            self._pending_spawns.append(spawn_data)

        # Process sounds
        for sound in results.get('sounds', []):
            self._sound_queue.append(sound)

        # Process scheduled callbacks
        for sched in results.get('scheduled', []):
            self._scheduled.append(ScheduledCallback(
                time_remaining=sched['delay'],
                callback_name=sched['callback'],
                entity_id=sched['entity_id'],
            ))

    # =========================================================================
    # Collision Actions
    # =========================================================================

    def execute_collision_action(
        self,
        action_name: str,
        entity_a: EntityBrowser,
        entity_b: EntityBrowser,
        modifier: Optional[Dict[str, Any]] = None,
        default_path: str = 'lua/collision_action'
    ) -> bool:
        """Execute a collision action."""
        # Load if needed
        if not self.has_subroutine('collision_action', action_name):
            content_path = f'{default_path}/{action_name}.lua'
            if not self.load_subroutine('collision_action', action_name, content_path):
                return False

        # Send to JavaScript
        self._send_to_js('lua_collision', {
            'action': action_name,
            'entity_a': entity_a.to_dict(),
            'entity_b': entity_b.to_dict(),
            'modifier': modifier or {},
        })

        return True

    def execute_input_action(
        self,
        action_name: str,
        x: float,
        y: float,
        args: Optional[Dict[str, Any]] = None,
        default_path: str = 'ams/input_action'
    ) -> bool:
        """Execute an input action."""
        # Load if needed
        if not self.has_subroutine('input_action', action_name):
            content_path = f'{default_path}/{action_name}.lua'
            if not self.load_subroutine('input_action', action_name, content_path):
                return False

        self._send_to_js('lua_input_action', {
            'action': action_name,
            'x': x,
            'y': y,
            'args': args or {},
        })

        return True

    def call_generator(
        self,
        name: str,
        args: Optional[Dict[str, Any]] = None,
        default_path: str = 'lua/generator'
    ) -> Any:
        """Call a generator (synchronous in browser is tricky - may return None)."""
        # For browser, generators need special handling
        # For now, return None and handle in game logic
        js_log(f"[LuaEngineBrowser] Generator {name} called - async not supported yet")
        return None

    def evaluate_expression(self, expression: str) -> Any:
        """Evaluate a Lua expression (synchronous - limited support).

        Supports common ams.* math functions used in entity definitions:
        - ams.random() - random float 0-1
        - ams.random_range(min, max) - random float in range
        - ams.sin(x), ams.cos(x), ams.sqrt(x), ams.abs(x)
        - ams.floor(x), ams.ceil(x)
        - ams.min(a, b), ams.max(a, b)
        - ams.clamp(value, min, max)
        - ams.atan2(y, x)
        - ams.get_screen_width(), ams.get_screen_height()
        """
        import math
        import random as rand

        # Create ams namespace object with math functions
        class AmsNamespace:
            def __init__(self, screen_width, screen_height):
                self._screen_width = screen_width
                self._screen_height = screen_height

            def random(self):
                return rand.random()

            def random_range(self, min_val, max_val):
                return min_val + rand.random() * (max_val - min_val)

            def sin(self, x):
                return math.sin(x)

            def cos(self, x):
                return math.cos(x)

            def sqrt(self, x):
                return math.sqrt(x)

            def abs(self, x):
                return abs(x)

            def floor(self, x):
                return math.floor(x)

            def ceil(self, x):
                return math.ceil(x)

            def min(self, a, b):
                return min(a, b)

            def max(self, a, b):
                return max(a, b)

            def clamp(self, value, min_val, max_val):
                return max(min_val, min(max_val, value))

            def atan2(self, y, x):
                return math.atan2(y, x)

            def get_screen_width(self):
                return self._screen_width

            def get_screen_height(self):
                return self._screen_height

        ams = AmsNamespace(self.screen_width, self.screen_height)

        try:
            # Safe evaluation with ams namespace
            result = eval(expression, {
                'ams': ams,
                'math': math,
                '__builtins__': {},
            })
            return result
        except Exception as e:
            js_log(f"[LuaEngineBrowser] Expression evaluation failed: {expression} - {e}")
            return None

    def set_global(self, name: str, value: Any) -> None:
        """Set a global variable (for iteration context)."""
        # Send to JavaScript
        self._send_to_js('lua_set_global', {'name': name, 'value': value})

    # =========================================================================
    # Lifecycle Hooks
    # =========================================================================

    def notify_hit(self, entity: EntityBrowser, other: Optional[EntityBrowser] = None,
                   hit_x: float = 0.0, hit_y: float = 0.0) -> None:
        """Notify entity of hit."""
        if entity.alive and self._lifecycle_provider:
            other_id = other.id if other else ""
            self._lifecycle_provider.dispatch_lifecycle(
                'on_hit', entity, self, other_id, hit_x, hit_y
            )

    def notify_collision(self, entity: EntityBrowser, other: EntityBrowser,
                         other_type: str, other_base_type: str) -> None:
        """Notify entity of collision."""
        if entity.alive and self._lifecycle_provider:
            self._lifecycle_provider.dispatch_lifecycle(
                'on_hit', entity, self, other.id, other_type, other_base_type
            )

    def _call_scheduled_callback(self, scheduled: ScheduledCallback) -> None:
        """Execute a scheduled callback."""
        entity = self.entities.get(scheduled.entity_id)
        if entity is None or not entity.alive:
            return

        if self._lifecycle_provider:
            self._lifecycle_provider.dispatch_scheduled(
                scheduled.callback_name, entity, self
            )

    def schedule_callback(self, delay: float, callback_name: str, entity_id: str) -> None:
        """Schedule a callback."""
        self._scheduled.append(ScheduledCallback(delay, callback_name, entity_id))

    def queue_sound(self, sound_name: str) -> None:
        """Queue a sound."""
        self._sound_queue.append(sound_name)

    def pop_sounds(self) -> List[str]:
        """Get and clear queued sounds."""
        sounds = self._sound_queue[:]
        self._sound_queue.clear()
        return sounds

    def get_pending_spawns(self) -> List[Dict[str, Any]]:
        """Get and clear pending spawns from Lua."""
        spawns = self._pending_spawns[:]
        self._pending_spawns.clear()
        return spawns

    def clear(self) -> None:
        """Clear all entities and reset state."""
        if self._lifecycle_provider:
            for entity in self.entities.values():
                self._lifecycle_provider.on_entity_destroyed(entity, self)

        self.entities.clear()
        self._scheduled.clear()
        self._sound_queue.clear()
        self._pending_spawns.clear()
        self.score = 0
        self.elapsed_time = 0.0


# Alias for compatibility
Entity = EntityBrowser
