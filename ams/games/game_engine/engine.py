"""YAML-driven game engine using Lua behaviors.

GameEngine extends BaseGame to provide a data-driven game framework where:
- Game definitions come from YAML (entities, behaviors, levels)
- Entity logic is implemented in Lua behaviors
- Python handles rendering, input, and collision detection

This enables creating new games primarily through configuration rather than code.

Usage:
    class MyGame(GameEngine):
        NAME = "My Game"
        GAME_DEF_FILE = Path(__file__).parent / 'game.yaml'

        def _get_skin(self, skin_name: str) -> GameEngineRenderer:
            return MyGameSkin()
"""

from abc import abstractmethod
import json
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TYPE_CHECKING
import uuid

import pygame

# Unified YAML/JSON loader (handles browser/WASM fallback)
from ams.yaml import load as yaml_load, HAS_YAML
from ams.logging import get_logger

log = get_logger('game_engine')

from ams.games.base_game import BaseGame
from ams.games.game_state import GameState
from ams.games.input.input_event import InputEvent
from ams.lua import LuaEngine, Entity
from ams.games.game_engine.api import GameLuaAPI
from ams.games.game_engine.entity import GameEntity
from ams.games.game_engine.schema import SchemaValidationError, validate_game_yaml
from ams.games.game_engine.lua.behavior_loader import BehaviorLoader
from ams.games.game_engine.config import (
    AssetsConfig,
    CollisionAction,
    CollisionRule,
    EntityPlacement,
    EntityTypeConfig,
    GameDefinition,
    GameEngineLevelData,
    InputAction,
    InputMappingConfig,
    LoseConditionConfig,
    OnUpdateTransform,
    RenderCommand,
    RenderWhen,
    SoundConfig,
    SpawnConfig,
    SpriteConfig,
    TargetedTransform,
    TransformConfig,
    WhenCondition,
)
from ams.games.game_engine.renderer import GameEngineRenderer
from ams.games.game_engine.rollback import RollbackStateManager, create_logger
from ams import profiling
from ams.interactions import InteractionEngine, Entity as InteractionEntity, LuaActionHandler
from ams.games.game_engine.lua.script_loader import VALID_SUBROUTINE_TYPES

if TYPE_CHECKING:
    from ams.content_fs import ContentFS


class GameEngine(BaseGame):
    """YAML-driven game engine with Lua behaviors.

    This extends BaseGame to provide:
    - Automatic entity management via LuaEngine
    - YAML-based game definitions
    - Lua behavior scripting
    - Standard collision detection patterns
    - Rollback/replay for CV latency compensation

    Rollback System:
        The engine captures state snapshots each frame, enabling rollback when
        hits arrive with detection latency. Use process_delayed_hit() to handle
        CV-detected hits that occurred in the past.

        Hits within ROLLBACK_THRESHOLD (default 100ms) are processed immediately.
        Older hits trigger rollback → apply hit → re-simulate to present.

        Configure via __init__ kwargs:
        - rollback_enabled: Enable/disable rollback (default: True)
        - rollback_history: Seconds of history to keep (default: 2.0)
        - rollback_threshold: Skip rollback for hits newer than this (default: 0.1)

    Subclasses must implement:
    - _get_skin(): Return rendering skin instance

    Can optionally override:
    - _on_entity_destroyed(): Handle entity death
    - _spawn_initial_entities(): Create starting entities
    - ROLLBACK_THRESHOLD: Latency threshold for immediate processing (default: 0.1s)
    """

    # Game definition file (override in subclass)
    GAME_DEF_FILE: Optional[Path] = None

    # Game slug (for ContentFS path resolution, used for behaviors, levels, assets)
    GAME_SLUG: Optional[str] = None

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> Type['GameEngine']:
        """Create a GameEngine subclass from a YAML or JSON game definition.

        This factory method eliminates the need for boilerplate Python files
        for YAML-only games. It reads metadata from the YAML/JSON and dynamically
        creates a properly configured GameEngine subclass.

        Args:
            yaml_path: Path to the game.yaml or game.json file

        Returns:
            A new GameEngine subclass configured for this game

        Example:
            # Instead of creating game_mode.py with boilerplate:
            MyGame = GameEngine.from_yaml(Path('games/MyGame/game.yaml'))
            game = MyGame()
        """
        # Load YAML or JSON to extract metadata (JSON for browser builds)
        game_data = yaml_load(yaml_path)

        # Extract metadata with defaults
        name = game_data.get('name', yaml_path.parent.name)
        description = game_data.get('description', f'YAML-driven game: {name}')
        version = game_data.get('version', '1.0.0')
        author = game_data.get('author', 'Unknown')

        # Create class name from game name (e.g., "Duck Hunt NG" -> "DuckHuntNGMode")
        class_name = ''.join(word.capitalize() for word in name.split()) + 'Mode'
        class_name = ''.join(c for c in class_name if c.isalnum())

        # Define the dynamic subclass
        game_def_file = yaml_path
        levels_dir = yaml_path.parent / 'levels'

        # Extract game slug from path
        game_slug = yaml_path.parent.name.lower()

        class YAMLGameMode(cls):
            NAME = name
            DESCRIPTION = description
            VERSION = version
            AUTHOR = author
            GAME_DEF_FILE = game_def_file
            LEVELS_DIR = levels_dir
            GAME_SLUG = game_slug

            def __init__(self, content_fs: 'ContentFS', **kwargs):
                kwargs.pop('skin', None)
                super().__init__(content_fs, skin='default', **kwargs)

            def _get_skin(self, skin_name: str) -> 'GameEngineRenderer':
                return GameEngineRenderer()

        # Set the class name for better debugging/repr
        YAMLGameMode.__name__ = class_name
        YAMLGameMode.__qualname__ = class_name

        return YAMLGameMode

    def __init__(
        self,
        content_fs: 'ContentFS',
        skin: str = 'default',
        lives: int = 3,
        width: int = 800,
        height: int = 600,
        **kwargs,
    ):
        """Initialize game engine.

        Args:
            content_fs: ContentFS for layered content access
            skin: Skin name for rendering
            lives: Starting lives
            width: Screen width
            height: Screen height
            **kwargs: BaseGame arguments
        """
        self._content_fs = content_fs
        # Initialize before super().__init__ (may call _apply_level_config)
        self._starting_lives = lives
        self._lives = lives
        self._screen_width = width
        self._screen_height = height
        self._score = 0
        self._internal_state = GameState.PLAYING
        self._game_def: Optional[GameDefinition] = None
        self._level_name = ""

        # Counters for generating unique inline names
        self._inline_behavior_counter = 0
        self._inline_collision_action_counter = 0
        self._inline_input_action_counter = 0
        self._inline_generator_counter = 0

        # Frame counter for profiling
        self._frame_count = 0

        # Add game directory as ContentFS layer (higher priority than engine)
        # This allows games to override engine lua scripts at lua/{type}/
        if self.GAME_SLUG:
            game_path = self._content_fs.core_dir / 'games' / self.GAME_SLUG
            self._content_fs.add_game_layer(game_path)

        # Create behavior engine with ContentFS and game-specific API
        self._behavior_engine = LuaEngine(
            content_fs=self._content_fs,
            screen_width=width,
            screen_height=height,
            api_class=GameLuaAPI,
        )

        # Create interaction engine for unified interactions
        self._interaction_engine = InteractionEngine(
            screen_width=width,
            screen_height=height,
            lives=lives,
        )

        # Wire action handler to Lua engine
        self._lua_action_handler = LuaActionHandler(self._behavior_engine)
        self._interaction_engine.set_default_handler(self._lua_action_handler)

        # Create behavior loader for YAML behavior bundles
        self._behavior_loader = BehaviorLoader(content_fs=self._content_fs)

        # Create system entities for Lua access (pointer, screen, etc.)
        from ams.games.game_engine.entity import SystemEntity
        self._pointer_entity = SystemEntity(id="pointer", entity_type="pointer")
        self._behavior_engine.register_entity(self._pointer_entity)

        # Load subroutines from lua/{type}/ - ContentFS resolves game overrides automatically
        # Priority: game > engine > core (via ContentFS layering)
        self._load_subroutines()

        # Load game definition
        self._raw_game_data: Optional[dict] = None  # Store raw data for inline scripts
        if self.GAME_DEF_FILE and self.GAME_DEF_FILE.exists():
            self._game_def = self._load_game_definition(self.GAME_DEF_FILE)
            # Load inline scripts after game definition (they can override file-based scripts)
            self._load_inline_scripts()
            # Register entity types with InteractionEngine
            self._register_entity_interactions()

        # Register spawn handler on API so Lua spawns use entity type config
        api = self._behavior_engine.api
        if hasattr(api, 'set_spawn_handler'):
            api.set_spawn_handler(self._lua_spawn_handler)

        # Register transform handler on API so Lua can transform entities
        if hasattr(api, 'set_transform_handler'):
            api.set_transform_handler(self._transform_into_type)

        # Register lose_life handler on API so Lua can trigger life loss
        if hasattr(api, 'set_lose_life_handler'):
            api.set_lose_life_handler(self.lose_life)

        # Register destroy callback for orphan handling
        self._behavior_engine.set_destroy_callback(self._on_entity_destroyed)

        # Register self as lifecycle provider for behavior dispatch
        self._behavior_engine.set_lifecycle_provider(self)

        # Create skin and give it access to game definition
        self._skin = self._get_skin(skin)
        if self._game_def:
            # Assets dir is relative to the game.yaml file
            assets_dir = self.GAME_DEF_FILE.parent / 'assets' if self.GAME_DEF_FILE else None
            self._skin.set_game_definition(self._game_def, assets_dir)

        # Player entity reference
        self._player_id: Optional[str] = None

        # Call super init (may load levels)
        super().__init__(**kwargs)

        # Initialize rollback system for CV latency compensation
        # Can be disabled by passing rollback_enabled=False
        self._rollback_enabled = kwargs.get('rollback_enabled', True)
        if self._rollback_enabled:
            self._rollback_manager = RollbackStateManager(
                history_duration=kwargs.get('rollback_history', 2.0),
                fps=kwargs.get('fps', 60),
                snapshot_interval=kwargs.get('snapshot_interval', 1),
            )
            self._rollback_logger = create_logger(
                session_name=kwargs.get('session_name', 'game'),
                force=False,  # Respects AMS_LOGGING_ROLLBACK_ENABLED env var
            )
            # Allow overriding threshold via kwarg
            if 'rollback_threshold' in kwargs:
                self.ROLLBACK_THRESHOLD = kwargs['rollback_threshold']
        else:
            self._rollback_manager = None
            self._rollback_logger = None

        # Spawn initial entities if no game entities loaded (ignore system entities like pointer)
        game_entities = [e for e in self._behavior_engine.entities.values()
                         if e.renderable]
        if not game_entities:
            self._spawn_initial_entities()

    def _load_game_definition(self, path: Path) -> GameDefinition:
        """Load game definition from YAML or JSON file."""
        data = yaml_load(path)

        # Validate against schema (raises SchemaValidationError unless AMS_SKIP_SCHEMA_VALIDATION=1)
        validate_game_yaml(data, path)

        # Store raw data for inline script loading
        self._raw_game_data = data

        # Discover registered assets from YAML files in assets/ directory
        from ams.games.game_engine.asset_registry import AssetRegistry
        assets_dir = path.parent / 'assets'
        registry = AssetRegistry(
            content_fs=self._content_fs,
            assets_base_dir=assets_dir
        )
        registry.discover('assets/')

        # Parse inline assets section
        assets_data = data.get('assets', {})
        files_config = assets_data.get('files', {})
        inline_sounds = self._parse_sounds_config(assets_data.get('sounds', {}), files_config)
        inline_sprites = self._parse_sprites_config(assets_data.get('sprites', {}), files_config)

        # Merge registered with inline (inline takes precedence)
        merged_sounds = registry.merge_sounds(inline_sounds)
        merged_sprites = registry.merge_sprites(inline_sprites)

        assets_config = AssetsConfig(
            files=files_config,
            sounds=merged_sounds,
            sprites=merged_sprites,
        )

        game_def = GameDefinition(
            name=data.get('name', 'Unnamed Game'),
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            author=data.get('author', ''),
            screen_width=data.get('screen_width', 800),
            screen_height=data.get('screen_height', 600),
            background_color=tuple(data.get('background_color', [20, 20, 30])),
            defaults=data.get('defaults', {}),
            win_condition=data.get('win_condition', 'destroy_all'),
            win_target=data.get('win_target', 0),
            win_target_type=data.get('win_target_type'),
            lose_on_player_death=data.get('lose_on_player_death', True),
            default_layout=data.get('default_layout'),
            assets=assets_config,
        )

        # First pass: parse all entity types
        raw_types = data.get('entity_types', {})
        for name, type_data in raw_types.items():
            # Parse render commands
            render_commands = []
            for render_data in type_data.get('render', []):
                # Parse when condition if present
                when_data = render_data.get('when')
                when_cond = None
                if when_data:
                    when_cond = RenderWhen(
                        property=when_data.get('property', ''),
                        value=when_data.get('value'),
                        compare=when_data.get('compare', 'equals'),
                        min=when_data.get('min'),
                    )

                render_commands.append(RenderCommand(
                    shape=render_data.get('shape', 'rectangle'),
                    color=render_data.get('color', '$color'),
                    fill=render_data.get('fill', True),
                    line_width=render_data.get('line_width', 1),
                    alpha=render_data.get('alpha'),  # Can be int, $prop, or {lua: expr}
                    points=[tuple(p) for p in render_data.get('points', [])],
                    offset=tuple(render_data.get('offset', [0, 0])),
                    size=tuple(render_data['size']) if render_data.get('size') else None,
                    sprite_name=render_data.get('sprite_name', render_data.get('sprite', '')),
                    radius=render_data.get('radius'),
                    text=render_data.get('text', ''),
                    font_size=render_data.get('font_size', 20),
                    align=render_data.get('align', 'center'),
                    when=when_cond,
                    stop=render_data.get('stop', False),
                ))

            # Parse lifecycle transforms
            on_destroy = None
            on_parent_destroy = None
            on_update = []
            if 'on_destroy' in type_data:
                on_destroy = self._parse_transform_config(type_data['on_destroy'])
            if 'on_parent_destroy' in type_data:
                on_parent_destroy = self._parse_transform_config(type_data['on_parent_destroy'])
            if 'on_update' in type_data:
                for update_data in type_data['on_update']:
                    on_update.append(self._parse_on_update_transform(update_data))

            # Parse behaviors (strings for files, dicts with lua: for inline)
            behaviors = self._parse_behaviors(name, type_data.get('behaviors', []))

            game_def.entity_types[name] = EntityTypeConfig(
                name=name,
                width=type_data.get('width', 32),
                height=type_data.get('height', 32),
                color=type_data.get('color', 'white'),
                sprite=type_data.get('sprite', ''),
                behaviors=behaviors,
                behavior_config=type_data.get('behavior_config', {}),
                health=type_data.get('health', 1),
                points=type_data.get('points', 0),
                tags=type_data.get('tags', []),
                extends=type_data.get('extends'),
                render_as=type_data.get('render_as', []),
                render=render_commands,
                on_destroy=on_destroy,
                on_parent_destroy=on_parent_destroy,
                on_update=on_update,
                interactions=type_data.get('interactions', {}),
            )

        # Second pass: resolve inheritance
        self._resolve_entity_inheritance(game_def)

        # Third pass: expand behaviors into interactions
        self._expand_behavior_interactions(game_def)

        # Parse collision rules (legacy format)
        for collision in data.get('collisions', []):
            if isinstance(collision, list) and len(collision) >= 2:
                game_def.collisions.append(CollisionRule(
                    type_a=collision[0],
                    type_b=collision[1],
                ))

        # Parse collision_behaviors (new nested dict format)
        # Format in YAML:
        # collision_behaviors:
        #   ball:
        #     paddle:
        #       action: bounce_paddle           # File-based
        #       modifier:
        #         max_angle: 60
        #   OR inline:
        #     brick:
        #       action:
        #         lua: |
        #           local a = {}
        #           function a.execute(a_id, b_id, mod)
        #               ams.destroy(b_id)
        #           end
        #           return a
        raw_collision_behaviors = data.get('collision_behaviors', {})
        for type_a, targets in raw_collision_behaviors.items():
            if type_a not in game_def.collision_behaviors:
                game_def.collision_behaviors[type_a] = {}
            for type_b, action_data in targets.items():
                action_name = self._parse_collision_action(
                    type_a, type_b, action_data
                )
                modifier = {}
                if isinstance(action_data, dict):
                    modifier = action_data.get('modifier', {})
                game_def.collision_behaviors[type_a][type_b] = CollisionAction(
                    action=action_name,
                    modifier=modifier
                )

        # Parse input_mapping
        # Format in YAML:
        # input_mapping:
        #   paddle_ready:
        #     target_x: paddle_target_x
        #     on_input:
        #       transform:
        #         into: paddle
        #         spawn:
        #           - type: ball
        #             offset: [0, -20]
        #             velocity_y: -300
        #       when:
        #         property: ball_launched
        #         value: false
        # Parse global on_input (fires on any input regardless of entity)
        global_on_input_data = data.get('global_on_input')
        if global_on_input_data:
            game_def.global_on_input = self._parse_input_action(global_on_input_data)

        raw_input_mapping = data.get('input_mapping', {})
        for entity_type, mapping_data in raw_input_mapping.items():
            on_input = None
            on_hit = None

            if 'on_input' in mapping_data:
                on_input = self._parse_input_action(mapping_data['on_input'])

            # Parse on_hit (input must be inside entity bounds)
            if 'on_hit' in mapping_data:
                on_hit = self._parse_input_action(mapping_data['on_hit'])

            game_def.input_mapping[entity_type] = InputMappingConfig(
                target_x=mapping_data.get('target_x'),
                target_y=mapping_data.get('target_y'),
                on_input=on_input,
                on_hit=on_hit,
            )

        # Parse lose_conditions
        # Format in YAML:
        # lose_conditions:
        #   - entity_type: ball
        #     event: exited_screen
        #     edge: bottom
        #     action: lose_life
        #     then:
        #       destroy: ball
        #       transform:
        #         entity_type: paddle
        #         into: paddle_ready
        raw_lose_conditions = data.get('lose_conditions', [])
        for condition_data in raw_lose_conditions:
            then_transform = None
            if 'then' in condition_data:
                then_data = condition_data['then']
                if 'transform' in then_data:
                    transform_data = then_data['transform']
                    # Parse the targeted transform
                    target_type = transform_data.get('entity_type', '')
                    # The transform config itself (type, children)
                    transform_config = self._parse_transform_config(transform_data)
                    then_transform = TargetedTransform(
                        entity_type=target_type,
                        transform=transform_config,
                    )

            game_def.lose_conditions.append(LoseConditionConfig(
                entity_type=condition_data.get('entity_type', ''),
                event=condition_data.get('event', ''),
                edge=condition_data.get('edge'),
                property_name=condition_data.get('property'),
                action=condition_data.get('action', 'lose_life'),
                then_destroy=condition_data.get('then', {}).get('destroy'),
                then_transform=then_transform,
                then_clear_property=condition_data.get('then', {}).get('clear_property'),
            ))

        # Player config
        if 'player' in data:
            player_data = data['player']
            game_def.player_type = player_data.get('type')
            game_def.player_spawn = tuple(player_data.get('spawn', [400, 500]))

        return game_def

    def _parse_spawn_config(self, data: Dict[str, Any]) -> SpawnConfig:
        """Parse a spawn config from YAML."""
        # Reserved keys that are NOT properties
        reserved = ('type', 'offset', 'count', 'inherit_velocity', 'lifetime')
        props = {k: v for k, v in data.items() if k not in reserved}

        return SpawnConfig(
            entity_type=data.get('type', ''),
            offset=tuple(data.get('offset', [0, 0])),
            count=data.get('count', 1),
            inherit_velocity=data.get('inherit_velocity', 0.0),
            lifetime=data.get('lifetime'),
            properties=props,
        )

    def _load_subroutines(self) -> None:
        """Load Lua subroutines from ContentFS.

        Loads from lua/{type}/ paths. ContentFS layering handles priority:
        - Game layer (games/{GAME_SLUG}/lua/{type}/) - highest, can override
        - Engine layer (ams/games/game_engine/lua/{type}/) - base defaults

        Subroutine types loaded:
        - behavior: Entity lifecycle scripts
        - collision_action: Collision handlers (legacy)
        - interaction_action: Unified interaction handlers
        - generator: Property generators
        """

        for sub_type in VALID_SUBROUTINE_TYPES:
            lua_path = f'lua/{sub_type}'
            if self._content_fs.exists(lua_path):
                self._behavior_engine.load_subroutines_from_dir(sub_type, lua_path)

    def _load_inline_scripts(self) -> None:
        """Load inline scripts from game.yaml.

        Looks for top-level keys:
        - inline_behaviors: {name: {lua: ..., description: ...}, ...}
        - inline_collision_actions: {name: {lua: ..., ...}, ...}
        - inline_generators: {name: {lua: ..., ...}, ...}
        - inline_input_actions: {name: {lua: ..., ...}, ...}

        These are loaded AFTER file-based scripts, allowing game-specific
        overrides or one-off scripts without creating separate files.
        """
        if not self._raw_game_data:
            return

        # Map section names to subroutine types
        inline_sections = {
            'inline_behaviors': 'behavior',
            'inline_collision_actions': 'collision_action',
            'inline_generators': 'generator',
            'inline_input_actions': 'input_action',
        }

        for section_name, sub_type in inline_sections.items():
            section_data = self._raw_game_data.get(section_name, {})
            if not section_data:
                continue

            for name, script_def in section_data.items():
                if not isinstance(script_def, dict):
                    log.error(f"Invalid inline script '{name}': expected dict")
                    continue

                lua_code = script_def.get('lua')
                if not lua_code:
                    log.error(f"Inline script '{name}' missing 'lua' field")
                    continue

                # Load via LuaEngine's inline loader
                if self._behavior_engine.load_inline_subroutine(sub_type, name, lua_code):
                    desc = script_def.get('description', '')
                    if desc:
                        log.debug(f"Loaded inline {sub_type}: {name} - {desc[:50]}")
                else:
                    log.error(f"Failed to load inline {sub_type}: {name}")

    def _register_entity_interactions(self) -> None:
        """Register entity type interactions with the InteractionEngine.

        For each entity type that has an 'interactions' field, parses and
        registers those interactions with the unified InteractionEngine.
        """
        if not self._game_def:
            return

        for entity_type, type_config in self._game_def.entity_types.items():
            if type_config.interactions:
                # Register with InteractionEngine - it handles parsing
                self._interaction_engine.register_entity_type(
                    entity_type,
                    type_config.interactions
                )

    def _parse_behaviors(self, entity_type: str, behaviors_data: List[Any]) -> List[str]:
        """Parse behaviors list, handling both file references and inline Lua.

        Behaviors can be:
        - String: Reference to file in behaviors directory (e.g., "paddle")
        - Dict with 'lua' key: Inline Lua script (lua_script_inline format)

        Example YAML:
            behaviors:
              - paddle              # loads paddle.lua.yaml
              - lua: |              # inline script
                  local wobble = {}
                  function wobble.on_update(entity_id, dt)
                      local x = ams.get_x(entity_id)
                      ams.set_x(entity_id, x + math.sin(ams.get_time() * 5) * dt * 10)
                  end
                  return wobble
                description: Wobble side to side

        Returns list of behavior names (inline behaviors get generated names).
        """
        behavior_names: List[str] = []

        for item in behaviors_data:
            if isinstance(item, str):
                # File-based behavior
                behavior_names.append(item)
            elif isinstance(item, dict) and 'lua' in item:
                # Inline behavior with lua_script_inline format
                lua_code = item['lua']
                name = f"_inline_{entity_type}_{self._inline_behavior_counter}"
                self._inline_behavior_counter += 1

                # Register inline behavior with engine
                if self._behavior_engine.load_inline_subroutine('behavior', name, lua_code):
                    behavior_names.append(name)
                    if 'description' in item:
                        log.debug(f"Loaded inline behavior: {item['description'][:50]}")
                else:
                    log.error(f"Failed to load inline behavior for {entity_type}")

        return behavior_names

    def _parse_collision_action(
        self, type_a: str, type_b: str, action_data: Any
    ) -> str:
        """Parse a collision action, handling both file references and inline Lua.

        Args:
            type_a: First entity type in collision
            type_b: Second entity type in collision
            action_data: Can be:
                - str: Action name (file reference)
                - dict with 'action' key: File reference with modifier
                - dict with 'action.lua' key: Inline Lua script

        Returns:
            Action name (inline actions get generated names).

        Example YAML formats:
            # Simple file reference
            ball:
              paddle: bounce_paddle

            # File with modifier
            ball:
              brick:
                action: take_damage
                modifier:
                  damage: 1

            # Inline Lua script
            ball:
              powerup:
                action:
                  lua: |
                    local a = {}
                    function a.execute(a_id, b_id, mod)
                        ams.destroy(b_id)
                        ams.set_prop(a_id, "powered_up", true)
                    end
                    return a
                  description: Collect powerup and activate
        """
        if isinstance(action_data, str):
            # Simple format: just action name string
            return action_data

        if isinstance(action_data, dict):
            action_field = action_data.get('action', '')

            if isinstance(action_field, str):
                # File-based action
                return action_field

            if isinstance(action_field, dict) and 'lua' in action_field:
                # Inline Lua action
                lua_code = action_field['lua']
                name = f"_inline_collision_{type_a}_{type_b}_{self._inline_collision_action_counter}"
                self._inline_collision_action_counter += 1

                if self._behavior_engine.load_inline_subroutine('collision_action', name, lua_code):
                    return name
                else:
                    log.error(f"Failed to load inline collision action for {type_a}->{type_b}")
                    return ''

        return ''

    def _parse_input_action(self, data: Dict[str, Any]) -> InputAction:
        """Parse an input action from YAML.

        Action can be:
        - String: Built-in action name (e.g., 'play_sound') or Lua script name
        - Dict with 'lua' key: Inline Lua script
        """
        transform_config = None
        when_condition = None
        action_name = None

        if 'transform' in data:
            transform_config = self._parse_transform_config(data['transform'])

        if 'when' in data:
            when_condition = self._parse_when_condition(data['when'])

        # Handle action - can be string or inline Lua
        action_data = data.get('action')
        if action_data:
            if isinstance(action_data, str):
                # File reference or built-in action
                action_name = action_data
            elif isinstance(action_data, dict) and 'lua' in action_data:
                # Inline Lua script
                lua_code = action_data['lua']
                self._inline_input_action_counter += 1
                name = f'_inline_input_action_{self._inline_input_action_counter}'

                if self._behavior_engine.load_inline_subroutine('input_action', name, lua_code):
                    action_name = name
                else:
                    log.error(f"Failed to load inline input action")

        return InputAction(
            transform=transform_config,
            when=when_condition,
            action=action_name,
            action_args=data.get('action_args', {}),
        )

    def _parse_transform_config(self, data: Dict[str, Any]) -> TransformConfig:
        """Parse a transform config from YAML."""
        children = []
        for child_data in data.get('children', []):
            children.append(self._parse_spawn_config(child_data))

        return TransformConfig(
            type=data.get('type', 'destroy'),
            children=children,
        )

    def _parse_when_condition(self, data: Dict[str, Any]) -> WhenCondition:
        """Parse a when condition from YAML."""
        # Parse age range: [min, max] | [min, ] | [, max]
        age_min = None
        age_max = None
        if 'age' in data:
            age = data['age']
            if isinstance(age, list) and len(age) >= 2:
                age_min = age[0] if age[0] is not None else None
                age_max = age[1] if age[1] is not None else None

        return WhenCondition(
            property=data.get('property'),
            value=data.get('value'),
            age_min=age_min,
            age_max=age_max,
            interval=data.get('interval'),
        )

    def _parse_on_update_transform(self, data: Dict[str, Any]) -> OnUpdateTransform:
        """Parse an on_update transform from YAML."""
        when = None
        transform = None

        if 'when' in data:
            when = self._parse_when_condition(data['when'])
        if 'transform' in data:
            transform = self._parse_transform_config(data['transform'])

        return OnUpdateTransform(when=when, transform=transform)

    def _resolve_file_reference(
        self, value: str, files: Dict[str, str]
    ) -> Tuple[str, Optional[str]]:
        """Resolve a file value that may be a @reference.

        Args:
            value: File path, data URI, or @reference
            files: Shared files dict from assets.files

        Returns:
            Tuple of (file_path, data_uri) - one will be set, other None
        """
        if value.startswith('@'):
            # Reference to shared file
            ref_name = value[1:]
            ref_value = files.get(ref_name, '')
            if ref_value.startswith('data:'):
                return ('', ref_value)
            else:
                return (ref_value, None)
        elif value.startswith('data:'):
            return ('', value)
        else:
            return (value, None)

    def _parse_sprites_config(
        self, sprites_data: Dict[str, Any], files: Dict[str, str]
    ) -> Dict[str, SpriteConfig]:
        """Parse sprites configuration from YAML.

        Supports:
        1. Simple path string: "paddle: sprites/paddle.png"
        2. Dict with file: {file: sprites/paddle.png, transparent: [r, g, b]}
        3. Dict with data URI: {data: "data:image/png;base64,..."}
        4. File reference: {file: "@sheet_name", x: 0, y: 0, ...}
        5. Either can have region: {x: 0, y: 0, width: 32, height: 32}
        6. Inheritance: {sprite: base_sprite, x: 10, y: 20} - inherits and overrides
        """
        result: Dict[str, SpriteConfig] = {}

        # First pass: parse all sprites without resolving inheritance
        raw_sprites: Dict[str, Dict[str, Any]] = {}

        for name, sprite_data in sprites_data.items():
            if isinstance(sprite_data, str):
                # Simple path string, data URI, or @reference
                file_path, data_uri = self._resolve_file_reference(sprite_data, files)
                result[name] = SpriteConfig(file=file_path, data=data_uri)
            elif isinstance(sprite_data, dict):
                raw_sprites[name] = sprite_data

        # Second pass: resolve inheritance and build final configs
        # Process in order, resolving dependencies
        def resolve_sprite(name: str, visited: set) -> SpriteConfig:
            if name in result:
                return result[name]

            if name not in raw_sprites:
                # Unknown sprite reference
                return SpriteConfig(file='', data=None)

            if name in visited:
                log.error(f"Circular sprite inheritance detected: {name}")
                return SpriteConfig(file='', data=None)

            visited.add(name)
            sprite_data = raw_sprites[name]

            # Check for inheritance via 'sprite' field
            base_sprite_name = sprite_data.get('sprite')
            if base_sprite_name:
                # Resolve base sprite first
                base = resolve_sprite(base_sprite_name, visited)
                # Start with base values
                file_path = base.file
                data_uri = base.data
                transparent = base.transparent
                x = base.x
                y = base.y
                width = base.width
                height = base.height
                flip_x = base.flip_x
                flip_y = base.flip_y
            else:
                # No inheritance, start fresh
                file_path = ''
                data_uri = None
                transparent = None
                x = None
                y = None
                width = None
                height = None
                flip_x = False
                flip_y = False

            # Override with values from this sprite's definition
            if 'transparent' in sprite_data:
                t = sprite_data['transparent']
                if isinstance(t, (list, tuple)) and len(t) >= 3:
                    transparent = (int(t[0]), int(t[1]), int(t[2]))

            # Resolve file reference if present
            file_value = sprite_data.get('file', '')
            data_value = sprite_data.get('data')

            if file_value:
                if file_value.startswith('@'):
                    file_path, data_uri = self._resolve_file_reference(file_value, files)
                else:
                    file_path = file_value
                    data_uri = None

            if data_value:
                data_uri = data_value

            # Override region/flip if specified
            if 'x' in sprite_data:
                x = sprite_data['x']
            if 'y' in sprite_data:
                y = sprite_data['y']
            if 'width' in sprite_data:
                width = sprite_data['width']
            if 'height' in sprite_data:
                height = sprite_data['height']
            if 'flip_x' in sprite_data:
                flip_x = sprite_data['flip_x']
            if 'flip_y' in sprite_data:
                flip_y = sprite_data['flip_y']

            config = SpriteConfig(
                file=file_path,
                data=data_uri,
                transparent=transparent,
                x=x,
                y=y,
                width=width,
                height=height,
                flip_x=flip_x,
                flip_y=flip_y,
            )
            result[name] = config
            return config

        # Resolve all raw sprites
        for name in raw_sprites:
            resolve_sprite(name, set())

        return result

    def _parse_sounds_config(
        self, sounds_data: Dict[str, Any], files: Dict[str, str]
    ) -> Dict[str, SoundConfig]:
        """Parse sounds configuration from YAML.

        Supports:
        1. Simple path string: "hit: sounds/hit.wav"
        2. Data URI string: "hit: data:audio/wav;base64,..."
        3. Dict with file: {file: sounds/hit.wav}
        4. Dict with data URI: {data: "data:audio/wav;base64,..."}
        5. File reference: "@sound_name" or {file: "@sound_name"}
        """
        result: Dict[str, SoundConfig] = {}

        for name, sound_data in sounds_data.items():
            if isinstance(sound_data, str):
                # Simple path string, data URI, or @reference
                file_path, data_uri = self._resolve_file_reference(sound_data, files)
                result[name] = SoundConfig(file=file_path, data=data_uri)
            elif isinstance(sound_data, dict):
                # Resolve file reference if present
                file_value = sound_data.get('file', '')
                data_value = sound_data.get('data')

                if file_value and file_value.startswith('@'):
                    file_path, data_uri = self._resolve_file_reference(file_value, files)
                else:
                    file_path = file_value
                    data_uri = data_value

                result[name] = SoundConfig(file=file_path, data=data_uri)

        return result

    def _resolve_entity_inheritance(self, game_def: GameDefinition) -> None:
        """Resolve 'extends' inheritance for entity types."""
        for name, config in game_def.entity_types.items():
            if config.extends:
                # Find the base type
                base = game_def.entity_types.get(config.extends)
                if base:
                    # Inherit properties that weren't overridden
                    if config.width == 32:
                        config.width = base.width
                    if config.height == 32:
                        config.height = base.height
                    if config.color == 'white':
                        config.color = base.color
                    if not config.sprite:
                        config.sprite = base.sprite
                    if not config.behaviors:
                        config.behaviors = base.behaviors.copy()
                    if config.health == 1:
                        config.health = base.health
                    if config.points == 0:
                        config.points = base.points
                    if not config.tags:
                        config.tags = base.tags.copy()

                    # Merge behavior configs (child overrides parent)
                    merged_config = dict(base.behavior_config)
                    for behavior, bconfig in config.behavior_config.items():
                        if behavior in merged_config:
                            merged_config[behavior] = {**merged_config[behavior], **bconfig}
                        else:
                            merged_config[behavior] = bconfig
                    config.behavior_config = merged_config

                    # Inherit render commands if not overridden
                    if not config.render and base.render:
                        config.render = base.render.copy()

                    # Inherit lifecycle transforms if not overridden
                    if not config.on_destroy and base.on_destroy:
                        config.on_destroy = base.on_destroy
                    if not config.on_parent_destroy and base.on_parent_destroy:
                        config.on_parent_destroy = base.on_parent_destroy
                    if not config.on_update and base.on_update:
                        config.on_update = base.on_update.copy()

                    # Set base_type (walk up the chain)
                    config.base_type = base.base_type or config.extends
            else:
                # No extends - this type is its own base
                config.base_type = name

    def _expand_behavior_interactions(self, game_def: GameDefinition) -> None:
        """Expand behaviors into interactions for all entity types.

        Behaviors are YAML bundles that define collections of interactions.
        This method expands them and merges with entity's own interactions.
        """
        for name, config in game_def.entity_types.items():
            if not config.behaviors:
                continue

            # Filter to named behaviors (skip inline Lua which will be legacy)
            behavior_names = [b for b in config.behaviors if isinstance(b, str)]
            if not behavior_names:
                continue

            # Expand behaviors into interactions
            behavior_interactions = self._behavior_loader.expand_behaviors(
                behaviors=behavior_names,
                behavior_config=config.behavior_config
            )

            # Merge with entity's own interactions (entity's take precedence)
            merged = dict(behavior_interactions)
            for target, interactions in config.interactions.items():
                if target not in merged:
                    merged[target] = interactions
                else:
                    # Entity has interactions for same target - merge
                    existing = merged[target]
                    if not isinstance(existing, list):
                        existing = [existing]
                    if not isinstance(interactions, list):
                        interactions = [interactions]
                    merged[target] = existing + interactions

            config.interactions = merged

    @abstractmethod
    def _get_skin(self, skin_name: str) -> GameEngineRenderer:
        """Get rendering skin instance.

        Override to return game-specific skin.

        Args:
            skin_name: Requested skin name

        Returns:
            GameEngineRenderer instance
        """
        return GameEngineRenderer()

    def _spawn_initial_entities(self) -> None:
        """Spawn initial entities from game.yaml config.

        Uses player.type + player.spawn and default_layout if present.
        Override for custom spawning logic.
        """
        if not self._game_def:
            return

        # Spawn player entity
        if self._game_def.player_type:
            player = self.spawn_entity(
                self._game_def.player_type,
                x=self._game_def.player_spawn[0],
                y=self._game_def.player_spawn[1],
            )
            if player:
                self._player_id = player.id

        # Spawn default layout if present
        self._spawn_default_layout()

    def _apply_level_config(self, level_data: Any) -> None:
        """Apply level configuration - spawn entities from level data.

        Supports multiple level formats:
        1. GameEngineLevelData protocol (entities list)
        2. Raw dict with ASCII layout (layout + layout_key)
        3. Raw dict with entities list

        Args:
            level_data: Parsed level data (protocol, dict, or dataclass)
        """
        # Clear existing entities
        self._behavior_engine.clear()

        # Handle both dict and protocol-style access
        def get_attr(obj: Any, key: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # Set level name for HUD
        self._level_name = get_attr(level_data, 'name', 'Level')

        # Apply lives from level
        lives = get_attr(level_data, 'lives', self._starting_lives)
        self._lives = lives
        self._starting_lives = lives

        # Spawn player entity at level-specified position
        if self._game_def and self._game_def.player_type:
            # Check for paddle config (BrickBreaker style) or player_x/y
            paddle = get_attr(level_data, 'paddle', {})
            if paddle:
                player_x = paddle.get('x', self._game_def.player_spawn[0])
                player_y = paddle.get('y', self._game_def.player_spawn[1])
            else:
                player_x = get_attr(level_data, 'player_x', self._game_def.player_spawn[0])
                player_y = get_attr(level_data, 'player_y', self._game_def.player_spawn[1])

            # Get layout properties to pass during spawn (for level_setup behaviors)
            layout_props = get_attr(level_data, 'layout', {})
            initial_props = layout_props if isinstance(layout_props, dict) else {}

            player = self.spawn_entity(
                self._game_def.player_type,
                x=player_x,
                y=player_y,
                properties=initial_props,
            )
            if player:
                self._player_id = player.id

        # Try ASCII layout first (layout + layout_key)
        layout_str = get_attr(level_data, 'layout')
        layout_key = get_attr(level_data, 'layout_key', {})
        if layout_str and layout_key:
            # Get grid config from level data
            grid = get_attr(level_data, 'grid', {})
            layout_config = {
                'grid': grid,
                'layout': layout_str,
                'layout_key': layout_key,
            }
            self._spawn_ascii_layout(layout_config, layout_str, layout_key)
        else:
            # Fall back to entities list
            entities = get_attr(level_data, 'entities', [])
            for placement in entities:
                if isinstance(placement, dict):
                    self.spawn_entity(
                        placement.get('entity_type', placement.get('type', '')),
                        x=placement.get('x', 0),
                        y=placement.get('y', 0),
                    )
                else:
                    self.spawn_entity(
                        placement.entity_type,
                        x=placement.x,
                        y=placement.y,
                    )

        # Reset game state
        self._internal_state = GameState.PLAYING

    def _spawn_default_layout(self) -> None:
        """Spawn entities from default_layout in game.yaml."""
        if not self._game_def or not self._game_def.default_layout:
            return

        layout = self._game_def.default_layout

        # ASCII layout support - parse layout string with layout_key mapping
        layout_str = layout.get('layout')
        layout_key = layout.get('layout_key', {})
        if layout_str and layout_key:
            self._spawn_ascii_layout(layout, layout_str, layout_key)
            return

        # Legacy brick_grid support (simple row-based grid)
        brick_grid = layout.get('brick_grid')
        if brick_grid:
            self._spawn_brick_grid(brick_grid)

    def _spawn_ascii_layout(
        self,
        layout_config: Dict[str, Any],
        layout_str: str,
        layout_key: Dict[str, str],
    ) -> None:
        """Spawn entities from ASCII art layout.

        Enables rapid level design using visual character layouts:

        default_layout:
          grid:
            cell_width: 70
            cell_height: 25
            start_x: 65
            start_y: 60
          layout: |
            ..SSSSSS..
            MMMMMMMMMM
            IIIIIIIIII
          layout_key:
            I: invader
            M: invader_moving
            S: shooter
            ".": empty

        Args:
            layout_config: Full layout config (contains grid settings)
            layout_str: Multi-line ASCII string
            layout_key: Mapping of characters to entity types
        """
        # Get grid configuration
        grid = layout_config.get('grid', {})
        start_x = grid.get('start_x', 65)
        start_y = grid.get('start_y', 60)
        cell_width = grid.get('cell_width', grid.get('brick_width', 70))
        cell_height = grid.get('cell_height', grid.get('brick_height', 25))

        # Parse ASCII lines
        lines = layout_str.strip().split('\n')

        for row, line in enumerate(lines):
            for col, char in enumerate(line):
                # Look up entity type for this character
                entity_type = layout_key.get(char)

                # Skip empty/unmapped characters
                if not entity_type or entity_type == 'empty' or entity_type == '':
                    continue

                # Calculate position
                x = start_x + col * cell_width
                y = start_y + row * cell_height

                self.spawn_entity(entity_type, x, y)

    def _spawn_brick_grid(self, brick_grid: Dict[str, Any]) -> None:
        """Spawn a simple row-based brick grid (legacy support).

        Args:
            brick_grid: Grid configuration with row_types
        """
        start_x = brick_grid.get('start_x', 65)
        start_y = brick_grid.get('start_y', 60)
        cols = brick_grid.get('cols', 10)
        rows = brick_grid.get('rows', 5)
        row_types = brick_grid.get('row_types', ['brick'])

        # Get brick dimensions from first row type
        first_type = row_types[0] if row_types else 'brick'
        type_config = self._game_def.entity_types.get(first_type) if self._game_def else None
        brick_width = type_config.width if type_config else 70
        brick_height = type_config.height if type_config else 25

        # Spawn grid
        for row in range(rows):
            # Get entity type for this row (cycle through row_types)
            entity_type = row_types[row % len(row_types)] if row_types else 'brick'
            for col in range(cols):
                x = start_x + col * brick_width
                y = start_y + row * brick_height
                self.spawn_entity(entity_type, x, y)

    def _lua_spawn_handler(
        self, entity_type: str, x: float, y: float,
        vx: float, vy: float, width: float, height: float,
        color: str, sprite: str
    ) -> Optional[GameEntity]:
        """Handler for Lua API spawn calls.

        Called when Lua code spawns entities (e.g., shoot behavior spawning projectiles).
        Applies entity type config from game.yaml so spawned entities have behaviors.

        Width/height of 0 means "use entity type defaults".
        """
        overrides: Dict[str, Any] = {'vx': vx, 'vy': vy}
        if width > 0:
            overrides['width'] = width
        if height > 0:
            overrides['height'] = height
        if color:
            overrides['color'] = color
        if sprite:
            overrides['sprite'] = sprite
        return self.spawn_entity(entity_type, x, y, **overrides)
    
    @profiling.profile("game_engine", "Spawn Entity")
    def spawn_entity(
        self,
        entity_type: str,
        x: float,
        y: float,
        properties: Optional[Dict[str, Any]] = None,
        **overrides,
    ) -> Optional[GameEntity]:
        """Spawn an entity of a defined type.

        Args:
            entity_type: Type name from game definition
            x, y: Position
            properties: Initial properties (available to on_spawn)
            **overrides: Override default type properties

        Returns:
            Created GameEntity, or None if type not found
        """
        # Get type config
        type_config = None
        if self._game_def:
            type_config = self._game_def.entity_types.get(entity_type)

        # Generate unique ID
        entity_id = f"{entity_type}_{uuid.uuid4().hex[:8]}"

        # Use type config or defaults
        if type_config:
            behaviors = overrides.get('behaviors', type_config.behaviors)
            behavior_config = overrides.get('behavior_config', type_config.behavior_config)

            entity = GameEntity(
                id=entity_id,
                entity_type=entity_type,
                x=x,
                y=y,
                vx=overrides.get('vx', 0.0),
                vy=overrides.get('vy', 0.0),
                width=overrides.get('width', type_config.width),
                height=overrides.get('height', type_config.height),
                color=overrides.get('color', type_config.color),
                sprite=overrides.get('sprite', type_config.sprite),
                health=overrides.get('health', type_config.health),
                behaviors=behaviors,
                behavior_config=behavior_config,
                properties=properties or {},
                tags=overrides.get('tags', type_config.tags.copy()),
                spawn_time=self._behavior_engine.elapsed_time,
            )
        else:
            # Create with overrides only
            entity = GameEntity(
                id=entity_id,
                entity_type=entity_type,
                x=x,
                y=y,
                properties=properties or {},
                spawn_time=self._behavior_engine.elapsed_time,
                **overrides,
            )

        # Register with LuaEngine (triggers on_entity_spawned via provider)
        self._behavior_engine.register_entity(entity)

        # Register with InteractionEngine for unified interactions
        interaction_entity = InteractionEntity(
            id=entity.id,
            entity_type=entity.entity_type,
            x=entity.x,
            y=entity.y,
            width=entity.width,
            height=entity.height,
            attributes=entity.properties.copy(),
        )
        self._interaction_engine.add_entity(interaction_entity)

        return entity

    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get all alive entities of a type."""
        return [e for e in self._behavior_engine.get_alive_entities()
                if e.entity_type == entity_type]

    def get_entities_by_tag(self, tag: str) -> List[Entity]:
        """Get all alive entities with a tag."""
        result = []
        for entity in self._behavior_engine.get_alive_entities():
            if self._game_def:
                type_config = self._game_def.entity_types.get(entity.entity_type)
                if type_config and tag in type_config.tags:
                    result.append(entity)
        return result

    # =========================================================================
    # BaseGame Implementation
    # =========================================================================

    def _get_internal_state(self) -> GameState:
        return self._internal_state

    def get_score(self) -> int:
        # Return behavior engine's score (set by Lua via ams.add_score)
        return self._behavior_engine.score

    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events.

        Applies input_mapping from game.yaml, then passes to _handle_player_input.
        """
        if self._internal_state != GameState.PLAYING:
            return

        for event in events:
            # Update InteractionEngine pointer for unified interactions
            # 'hit' events are active clicks, 'move' events are passive positioning
            is_active = event.event_type == 'hit'
            self._interaction_engine.update_pointer(
                event.position.x,
                event.position.y,
                active=is_active
            )

            # Update pointer system entity for Lua access via ams.get_x("pointer")
            self._pointer_entity.update(event.position.x, event.position.y, is_active)

            # Apply declarative input_mapping (legacy)
            self._apply_input_mapping(event)
            # Call subclass handler for any additional logic
            self._handle_player_input(event)

    def _apply_input_mapping(self, event: InputEvent) -> None:
        """Apply input mapping from game.yaml to entities."""
        if not self._game_def:
            return

        input_x, input_y = event.position.x, event.position.y

        # Handle global on_input action (e.g., play shot sound)
        if self._game_def.global_on_input:
            self._handle_input_action(None, self._game_def.global_on_input, input_x, input_y)

        if not self._game_def.input_mapping:
            return

        for entity_type, mapping in self._game_def.input_mapping.items():
            # Find all entities matching this type
            entities = self._get_entities_matching_type(
                entity_type,
                self._behavior_engine.get_alive_entities()
            )


            for entity in entities:
                # Apply target_x/target_y if configured
                if mapping.target_x:
                    entity.properties[mapping.target_x] = input_x
                if mapping.target_y:
                    entity.properties[mapping.target_y] = input_y

                # Check for on_input action (fires for any input)
                if mapping.on_input:
                    self._handle_input_action(entity, mapping.on_input, input_x, input_y)

                # Check for on_hit action (only fires if input is inside entity)
                if mapping.on_hit:
                    if self._point_in_entity(input_x, input_y, entity):
                        self._handle_input_action(entity, mapping.on_hit, input_x, input_y)

    def _point_in_entity(self, x: float, y: float, entity: Entity) -> bool:
        """Check if a point is inside an entity's bounding box."""
        return (entity.x <= x <= entity.x + entity.width and
                entity.y <= y <= entity.y + entity.height)

    def _handle_input_action(
        self,
        entity: Optional[Entity],
        action: InputAction,
        input_x: float,
        input_y: float
    ) -> None:
        """Handle an input action for an entity (or globally if entity is None)."""
        # Check when condition if present
        if action.when and action.when.property and entity:
            prop_value = entity.properties.get(action.when.property)
            if prop_value != action.when.value:
                # Condition not met, skip action
                return

        # Execute named action if configured
        if action.action:
            self._execute_action(action.action, action.action_args, input_x, input_y)

        # Execute transform if configured (requires entity)
        if action.transform and entity:
            self.apply_transform(entity, action.transform)

    def _execute_action(
        self,
        action_name: str,
        args: Dict[str, Any],
        input_x: float,
        input_y: float
    ) -> None:
        """Execute a named action with arguments.

        Built-in actions:
        - play_sound: Plays a sound (args: {sound: "name"})

        For any other action name, tries to execute a Lua input action script
        from ams/input_action/{action_name}.lua
        """
        # Built-in actions
        if action_name == 'play_sound':
            sound_name = args.get('sound', '')
            if sound_name:
                self._skin.play_sound(sound_name)
            return

        # Try Lua input action
        self._behavior_engine.execute_input_action(action_name, input_x, input_y, args)

    def _handle_player_input(self, event: InputEvent) -> None:
        """Handle a single input event.

        Override in subclass for game-specific input handling.
        """
        pass

    def update(self, dt: float) -> None:
        """Update game state.

        Captures state snapshot for rollback before running frame update.
        """
        if self._internal_state != GameState.PLAYING:
            return

        # Begin profiling frame
        profiling.begin_frame(self._frame_count)

        # Capture snapshot before update for rollback capability
        if self._rollback_manager:
            snapshot = self._rollback_manager.capture(self)
            if snapshot and self._rollback_logger:
                self._rollback_logger.log_snapshot(snapshot)

        # Run the actual frame update
        self._do_frame_update(dt)

        # End profiling frame
        profiling.end_frame()
        self._frame_count += 1

        # Increment frame counter
        self._frame_count += 1

    @profiling.profile("game_engine", "Frame Update")
    def _do_frame_update(self, dt: float) -> None:
        """Internal frame update logic.

        This method contains the core game loop logic and is called:
        - By update() during normal gameplay
        - By RollbackStateManager during re-simulation

        Args:
            dt: Delta time since last frame
        """
        # Apply velocity to position for all entities (core physics)
        self._apply_physics(dt)

        # Update behavior engine (moves entities, fires callbacks)
        self._behavior_engine.update(dt)

        # Process queued sounds
        for sound in self._behavior_engine.pop_sounds():
            self._skin.play_sound(sound)

        # Check on_update transforms (age-based, property-based, interval)
        self._check_on_update_transforms()

        # Sync entity positions to InteractionEngine
        self._sync_entities_to_interaction_engine()

        # Evaluate unified interactions (collisions, input, screen, timer)
        # This replaces: _check_collisions, _apply_input_mapping (hit detection),
        # and _check_lose_conditions (screen exit)
        self._interaction_engine.evaluate(dt)

        # Legacy collision check - fallback for games not yet migrated
        self._check_collisions()

        # Note: destroyed entities are handled via callback from LuaEngine
        # (see _on_entity_destroyed, registered via set_destroy_callback)

        # Update skin
        self._skin.update(dt)

        # Check win/lose conditions
        self._check_win_conditions()
        self._check_lose_conditions()

    # Threshold below which we skip rollback and process hits immediately
    ROLLBACK_THRESHOLD: float = 0.1  # 100ms default, configurable via subclass

    def process_delayed_hit(
        self,
        x: float,
        y: float,
        hit_timestamp: float,
        hit_applicator: Optional[Callable[[], None]] = None,
    ) -> bool:
        """Process a hit that may have arrived with latency.

        If the hit is recent (within ROLLBACK_THRESHOLD), process immediately.
        If older but within rollback window, rollback and re-simulate.
        If too old, process at current time as fallback.

        Args:
            x: Hit x coordinate (screen pixels)
            y: Hit y coordinate (screen pixels)
            hit_timestamp: When the hit actually occurred (time.monotonic())
            hit_applicator: Optional custom hit application function.
                           If None, uses standard input mapping.

        Returns:
            True if hit was processed (via rollback or immediate),
            False if rollback failed.
        """
        current_time = time.monotonic()
        latency = current_time - hit_timestamp

        # Recent hit - process immediately, no rollback needed
        if latency <= self.ROLLBACK_THRESHOLD:
            self._apply_input_mapping(InputEvent(
                position=(x, y),
                event_type='hit',
                timestamp=hit_timestamp,
            ))
            return True

        # No rollback manager - process immediately
        if not self._rollback_manager:
            self._apply_input_mapping(InputEvent(
                position=(x, y),
                event_type='hit',
                timestamp=hit_timestamp,
            ))
            return True

        # Check if we can rollback to the hit time
        if not self._rollback_manager.can_rollback_to(hit_timestamp):
            # Hit is too old - process at current time as fallback
            self._apply_input_mapping(InputEvent(
                position=(x, y),
                event_type='hit',
                timestamp=current_time,
            ))
            return True

        # Create hit applicator if not provided
        if hit_applicator is None:
            def hit_applicator():
                self._apply_input_mapping(InputEvent(
                    position=(x, y),
                    event_type='hit',
                    timestamp=hit_timestamp,
                ))

        # Rollback and resimulate
        result = self._rollback_manager.rollback_and_resimulate(
            game_engine=self,
            target_timestamp=hit_timestamp,
            hit_applicator=hit_applicator,
            current_timestamp=current_time,
        )

        # Log the rollback if enabled
        if result.success and self._rollback_logger:
            self._rollback_logger.log_rollback(
                target_timestamp=hit_timestamp,
                restored_frame=result.restored_frame,
                frames_resimulated=result.frames_resimulated,
                hit_position=(x, y),
            )

        return result.success

    def _check_on_update_transforms(self) -> None:
        """Check and apply on_update transforms based on conditions.

        Evaluates age-based, property-based, and interval conditions
        for each entity and applies matching transforms.
        """
        if not self._game_def:
            return

        current_time = self._behavior_engine.elapsed_time

        for entity in self._behavior_engine.get_alive_entities():
            type_config = self._game_def.entity_types.get(entity.entity_type)
            if not type_config or not type_config.on_update:
                continue

            entity_age = current_time - entity.spawn_time

            for update_transform in type_config.on_update:
                if not update_transform.when or not update_transform.transform:
                    continue

                when = update_transform.when

                # Check age condition
                if when.age_min is not None or when.age_max is not None:
                    if when.age_min is not None and entity_age < when.age_min:
                        continue
                    if when.age_max is not None and entity_age >= when.age_max:
                        continue

                # Check property condition
                if when.property is not None:
                    prop_value = entity.properties.get(when.property)
                    if prop_value != when.value:
                        continue

                # Check interval (uses entity property to track last trigger)
                if when.interval is not None:
                    last_trigger_key = f'_last_trigger_{id(update_transform)}'
                    last_trigger = entity.properties.get(last_trigger_key, 0)
                    if current_time - last_trigger < when.interval:
                        continue
                    entity.properties[last_trigger_key] = current_time

                # Condition met - apply transform
                self.apply_transform(entity, update_transform.transform)

                # If entity was destroyed, stop processing its transforms
                if not entity.alive:
                    break

    @profiling.profile("game_engine", "Check Collisions")
    def _check_collisions(self) -> None:
        """Check collisions based on rules defined in game.yaml.

        Supports both collision formats:
        - collisions: [[type_a, type_b], ...] - explicit pairs (legacy)
        - collision_behaviors: {type_a: {type_b: action}} - nested dict (new)

        For each collision rule, finds all entity pairs that match and
        dispatches to collision actions or on_hit behaviors.
        """
        if not self._game_def:
            return

        # Need either collisions or collision_behaviors defined
        has_collisions = bool(self._game_def.collisions)
        has_collision_behaviors = bool(self._game_def.collision_behaviors)
        if not has_collisions and not has_collision_behaviors:
            return

        alive_entities = self._behavior_engine.get_alive_entities()

        # Track collisions already processed this frame to avoid duplicates
        processed: set[str] = set()

        # Collect all type pairs to check from both systems
        type_pairs: set[tuple[str, str]] = set()

        # From legacy collisions
        for rule in self._game_def.collisions:
            type_pairs.add((rule.type_a, rule.type_b))

        # From collision_behaviors
        for type_a, targets in self._game_def.collision_behaviors.items():
            for type_b in targets.keys():
                type_pairs.add((type_a, type_b))

        # Check all type pairs
        for type_a, type_b in type_pairs:
            # Find entities matching each side of the rule
            entities_a = self._get_entities_matching_type(type_a, alive_entities)
            entities_b = self._get_entities_matching_type(type_b, alive_entities)

            # Check all pairs for collision
            for entity_a in entities_a:
                for entity_b in entities_b:
                    # Skip self-collision
                    if entity_a.id == entity_b.id:
                        continue

                    # Skip if already processed (order-independent)
                    pair_key = "|".join(sorted([entity_a.id, entity_b.id]))
                    if pair_key in processed:
                        continue

                    # Check AABB overlap
                    if self._check_aabb_collision(entity_a, entity_b):
                        processed.add(pair_key)
                        self._handle_collision(entity_a, entity_b)

    def _get_entities_matching_type(self, type_pattern: str,
                                     entities: List[Entity]) -> List[Entity]:
        """Get entities that match a type pattern (exact type or base type)."""
        result = []
        for entity in entities:
            # Exact type match
            if entity.entity_type == type_pattern:
                result.append(entity)
                continue

            # Base type match (e.g., 'brick' matches 'brick_red')
            if self._game_def:
                type_config = self._game_def.entity_types.get(entity.entity_type)
                if type_config and type_config.base_type == type_pattern:
                    result.append(entity)

        return result

    def _check_aabb_collision(self, a: Entity, b: Entity) -> bool:
        """Check if two entities' bounding boxes overlap."""
        return (a.x < b.x + b.width and
                a.x + a.width > b.x and
                a.y < b.y + b.height and
                a.y + a.height > b.y)

    def _handle_collision(self, entity_a: Entity, entity_b: Entity) -> None:
        """Handle a collision between two entities.

        Dispatches collision actions based on collision_behaviors config.
        Falls back to on_hit behavior calls if no collision_behaviors defined.
        """
        # Get type info for context
        type_a = entity_a.entity_type
        type_b = entity_b.entity_type
        base_a = self._get_base_type(type_a)
        base_b = self._get_base_type(type_b)

        # Try collision_behaviors first (new system)
        if self._game_def and self._game_def.collision_behaviors:
            # Look up action for A hitting B
            action_a = self._find_collision_action(type_a, base_a, type_b, base_b)
            if action_a:
                self._behavior_engine.execute_collision_action(
                    action_a.action, entity_a, entity_b, action_a.modifier
                )

            # Look up action for B hitting A
            action_b = self._find_collision_action(type_b, base_b, type_a, base_a)
            if action_b:
                self._behavior_engine.execute_collision_action(
                    action_b.action, entity_b, entity_a, action_b.modifier
                )

            # If we found any collision_behaviors, don't fall through to on_hit
            if action_a or action_b:
                return

        # Fallback: notify both entities via legacy on_hit behavior hook
        self._behavior_engine.notify_collision(
            entity_a, entity_b, type_b, base_b
        )
        self._behavior_engine.notify_collision(
            entity_b, entity_a, type_a, base_a
        )

    def _find_collision_action(
        self, type_a: str, base_a: str, type_b: str, base_b: str
    ) -> Optional[CollisionAction]:
        """Find collision action for type_a colliding with type_b.

        Checks in order of specificity:
        1. Exact type match: collision_behaviors[type_a][type_b]
        2. A exact, B base: collision_behaviors[type_a][base_b]
        3. A base, B exact: collision_behaviors[base_a][type_b]
        4. Base type match: collision_behaviors[base_a][base_b]

        Returns None if no action defined.
        """
        if not self._game_def:
            return None

        cb = self._game_def.collision_behaviors

        # Try most specific to least specific
        for a_key in [type_a, base_a]:
            if a_key not in cb:
                continue
            for b_key in [type_b, base_b]:
                if b_key in cb[a_key]:
                    return cb[a_key][b_key]

        return None

    def _get_base_type(self, entity_type: str) -> str:
        """Get the base type for an entity type."""
        if self._game_def:
            type_config = self._game_def.entity_types.get(entity_type)
            if type_config and type_config.base_type:
                return type_config.base_type
        return entity_type

    def _handle_destroyed_entities(self) -> None:
        """Process recently destroyed entities.

        Called after update to handle scoring, effects, etc.
        """
        # Check for entities that died this frame
        for entity in list(self._behavior_engine.entities.values()):
            if not entity.alive:
                self._on_entity_destroyed(entity)

    def _on_entity_destroyed(self, entity: Entity) -> None:
        """Handle entity destruction.

        Applies on_destroy transforms, scoring, and orphan handling.
        """
        # Remove from InteractionEngine
        self._interaction_engine.remove_entity(entity.id)

        if not self._game_def:
            return

        type_config = self._game_def.entity_types.get(entity.entity_type)
        if not type_config:
            return

        # Add points
        self._score += type_config.points

        # Apply on_destroy transform (spawn death effects, etc.)
        if type_config.on_destroy:
            # Spawn children at entity's position
            self._spawn_children(entity, type_config.on_destroy.children)

        # Handle orphaned children (parent-child relationship)
        self._handle_orphaned_children(entity)

    def _handle_orphaned_children(self, parent: Entity) -> None:
        """Handle children of a destroyed parent entity.

        When a parent is destroyed, triggers on_parent_destroy transform
        for each child AND recursively for all descendants.
        (e.g., cutting a rope segment orphans everything below it).
        """
        if not parent.children:
            return

        # Collect all descendants first (breadth-first)
        descendants_to_orphan: list[Entity] = []
        queue = list(parent.children)

        while queue:
            child_id = queue.pop(0)
            child = self._behavior_engine.get_entity(child_id)
            if not child or not child.alive:
                continue
            descendants_to_orphan.append(child)
            # Add this child's children to the queue (recursive)
            queue.extend(child.children)

        # Now orphan all descendants
        for child in descendants_to_orphan:
            # Clear parent reference
            child.parent_id = None
            child.parent_offset = (0.0, 0.0)
            child.properties.pop("_parent_id", None)
            child.properties.pop("_parent_offset_x", None)
            child.properties.pop("_parent_offset_y", None)
            child.children.clear()  # Clear children list too

            # Apply on_parent_destroy transform if defined
            if self._game_def:
                child_config = self._game_def.entity_types.get(child.entity_type)
                if child_config and child_config.on_parent_destroy:
                    self.apply_transform(child, child_config.on_parent_destroy)

    def _sync_entities_to_interaction_engine(self) -> None:
        """Sync entity positions and attributes to InteractionEngine.

        Called each frame after behavior engine update to ensure
        InteractionEngine has current entity state for filter evaluation.
        """
        for entity in self._behavior_engine.get_alive_entities():
            self._interaction_engine.update_entity(
                entity.id,
                x=entity.x,
                y=entity.y,
                attributes=entity.properties,
            )

    @profiling.profile("game_engine", "Apply Physics")
    def _apply_physics(self, dt: float) -> None:
        """Apply velocity to position for all entities.

        Core physics step that runs before behaviors/interactions.
        Entities with non-zero velocity will move automatically.
        """
        for entity in self._behavior_engine.get_alive_entities():
            if entity.vx != 0 or entity.vy != 0:
                entity.x += entity.vx * dt
                entity.y += entity.vy * dt

    def _check_win_conditions(self) -> None:
        """Check if player has won based on game definition.

        Uses win_condition and win_target_type from game.yaml.
        Override in subclass only for truly custom conditions.
        """
        if not self._game_def:
            return

        if self._game_def.win_condition == 'destroy_all':
            # Win when all entities of target type are destroyed
            target_type = self._game_def.win_target_type
            if target_type:
                # Check for entities with matching base_type
                targets = self.get_entities_by_base_type(target_type)
                if not targets:
                    self._internal_state = GameState.WON
            else:
                # Fallback: check for 'enemy' tagged entities
                enemies = self.get_entities_by_tag('enemy')
                if not enemies:
                    self._internal_state = GameState.WON

        elif self._game_def.win_condition == 'reach_score':
            if self.get_score() >= self._game_def.win_target:
                self._internal_state = GameState.WON

    def get_entities_by_base_type(self, base_type: str) -> List[Entity]:
        """Get all alive entities that extend from a base type."""
        result = []
        for entity in self._behavior_engine.get_alive_entities():
            if self._game_def:
                type_config = self._game_def.entity_types.get(entity.entity_type)
                if type_config and type_config.base_type == base_type:
                    result.append(entity)
        return result

    def _check_lose_conditions(self) -> None:
        """Check lose conditions from game.yaml and check if player has lost."""
        if self._lives <= 0:
            self._internal_state = GameState.GAME_OVER
            return

        # Check declarative lose conditions
        if not self._game_def or not self._game_def.lose_conditions:
            return

        for condition in self._game_def.lose_conditions:
            if condition.event == 'exited_screen':
                self._check_exited_screen_condition(condition)
            elif condition.event == 'property_true':
                self._check_property_true_condition(condition)

    def _check_exited_screen_condition(self, condition: LoseConditionConfig) -> None:
        """Check if any entity of type has exited the screen."""
        entities = self._get_entities_matching_type(
            condition.entity_type,
            self._behavior_engine.get_alive_entities()
        )

        for entity in entities:
            exited = False
            edge = condition.edge or 'any'

            # Check if entity has exited screen
            if edge == 'bottom' or edge == 'any':
                if entity.y > self._screen_height:
                    exited = True
            if edge == 'top' or edge == 'any':
                if entity.y + entity.height < 0:
                    exited = True
            if edge == 'left' or edge == 'any':
                if entity.x + entity.width < 0:
                    exited = True
            if edge == 'right' or edge == 'any':
                if entity.x > self._screen_width:
                    exited = True

            if exited:
                self._handle_lose_condition_triggered(entity, condition)

    def _check_property_true_condition(self, condition: LoseConditionConfig) -> None:
        """Check if any entity of type has a property set to true."""
        if not condition.property_name:
            return

        entities = self._get_entities_matching_type(
            condition.entity_type,
            self._behavior_engine.get_alive_entities()
        )

        for entity in entities:
            prop_value = entity.properties.get(condition.property_name)
            if prop_value:  # Truthy check
                self._handle_lose_condition_triggered(entity, condition)

    def _handle_lose_condition_triggered(self, entity: Entity,
                                          condition: LoseConditionConfig) -> None:
        """Handle a triggered lose condition - execute action and then block."""
        # Execute action
        if condition.action == 'lose_life':
            self.lose_life()

        # Execute 'then' block
        if condition.then_destroy:
            # Destroy entities matching the type
            to_destroy = self._get_entities_matching_type(
                condition.then_destroy,
                self._behavior_engine.get_alive_entities()
            )
            # For ball exiting, destroy just this entity
            if condition.then_destroy == condition.entity_type:
                entity.alive = False
            else:
                for e in to_destroy:
                    e.alive = False

        if condition.then_transform:
            # Transform another entity type
            targets = self._get_entities_matching_type(
                condition.then_transform.entity_type,
                self._behavior_engine.get_alive_entities()
            )
            if targets:
                # Transform first matching entity
                self.apply_transform(targets[0], condition.then_transform.transform)

        if condition.then_clear_property:
            # Clear the property that triggered the condition
            entity.properties[condition.then_clear_property] = False

    def apply_transform(self, entity: Entity, transform: TransformConfig) -> Optional[Entity]:
        """Apply a transform to an entity.

        This is the core transform primitive. Two modes:
        - type="destroy": Spawn children, destroy entity
        - type="<entity_type>": Transform into another type, spawn children

        Args:
            entity: The entity to transform
            transform: Transform configuration

        Returns:
            The transformed entity (or None if destroyed)
        """
        # Spawn children first (before entity is potentially destroyed)
        self._spawn_children(entity, transform.children)

        # Handle destroy vs transform
        if transform.type == "destroy":
            entity.destroy()
            return None
        else:
            # Transform into another type
            return self._transform_into_type(entity, transform.type)

    def _transform_into_type(self, entity: Entity, into_type: str) -> Optional[Entity]:
        """Transform entity into another type, keeping position and ID."""
        if not self._game_def or into_type not in self._game_def.entity_types:
            return None

        new_config = self._game_def.entity_types[into_type]

        # Transform - keep position and ID, change type
        entity.entity_type = into_type
        entity.width = new_config.width
        entity.height = new_config.height
        entity.color = new_config.color
        entity.sprite = new_config.sprite

        # Update behaviors
        entity.behaviors = new_config.behaviors.copy()
        entity.behavior_config = dict(new_config.behavior_config)

        # Sync entity type to interaction engine (clears trigger state for fresh interactions)
        self._interaction_engine.transform_entity(entity.id, into_type)

        # Trigger on_spawn for new behaviors
        self.on_entity_spawned(entity, self._behavior_engine)

        return entity

    def _spawn_children(self, parent: Entity, children: List[SpawnConfig]) -> List[Entity]:
        """Spawn child entities relative to parent.

        Handles count, inherit_velocity, lifetime, and {lua:...} expressions.
        """
        spawned = []

        for spawn in children:
            count = spawn.count

            for i in range(count):
                # Make 'i' available for Lua expressions
                self._behavior_engine.set_global('i', i)

                # Evaluate offset (may be {lua: ...})
                if isinstance(spawn.offset, dict) and 'lua' in spawn.offset:
                    offset = self._evaluate_property_value(spawn.offset)
                    if isinstance(offset, (list, tuple)) and len(offset) >= 2:
                        offset_x, offset_y = offset[0], offset[1]
                    else:
                        offset_x, offset_y = 0, 0
                else:
                    offset_x, offset_y = spawn.offset

                spawn_x = parent.x + offset_x
                spawn_y = parent.y + offset_y

                # Evaluate all properties (handle {lua: ...} and $property refs)
                spawn_props = {}
                for key, value in spawn.properties.items():
                    if isinstance(value, str) and value.startswith('$'):
                        # Resolve from parent entity
                        prop_name = value[1:]
                        if prop_name == 'color':
                            spawn_props[key] = parent.color
                        else:
                            spawn_props[key] = parent.properties.get(prop_name)
                    else:
                        spawn_props[key] = self._evaluate_property_value(value)

                # Add lifetime as property if specified
                if spawn.lifetime is not None:
                    spawn_props['lifetime'] = spawn.lifetime

                # Calculate inherited velocity
                inherited_vx = parent.vx * spawn.inherit_velocity
                inherited_vy = parent.vy * spawn.inherit_velocity

                # If spawn has explicit velocity, add inherited
                if 'vx' in spawn_props:
                    spawn_props['vx'] = spawn_props['vx'] + inherited_vx
                elif spawn.inherit_velocity > 0:
                    spawn_props['vx'] = inherited_vx

                if 'vy' in spawn_props:
                    spawn_props['vy'] = spawn_props['vy'] + inherited_vy
                elif spawn.inherit_velocity > 0:
                    spawn_props['vy'] = inherited_vy

                # Convert speed+angle to vx/vy in Python
                # This is needed for browser mode where Lua on_spawn may not run synchronously
                # The ball behavior also handles this, but it's harmless to do it here too
                if 'speed' in spawn_props and 'angle' in spawn_props:
                    import math
                    speed = spawn_props.pop('speed')
                    angle = spawn_props.pop('angle')
                    if speed is not None and angle is not None:
                        angle_rad = math.radians(angle)
                        # cos gives x component, sin gives y component
                        spawn_props['vx'] = spawn_props.get('vx', 0) + speed * math.cos(angle_rad)
                        spawn_props['vy'] = spawn_props.get('vy', 0) + speed * math.sin(angle_rad)

                # Extract color/vx/vy from properties into overrides
                overrides = {}
                if 'color' in spawn_props:
                    overrides['color'] = spawn_props.pop('color')
                if 'vx' in spawn_props:
                    overrides['vx'] = spawn_props.pop('vx')
                if 'vy' in spawn_props:
                    overrides['vy'] = spawn_props.pop('vy')

                # Spawn the child
                child = self.spawn_entity(
                    spawn.entity_type, spawn_x, spawn_y,
                    properties=spawn_props,
                    **overrides
                )
                if child:
                    spawned.append(child)

        return spawned

    def _evaluate_property_value(self, value: Any) -> Any:
        """Evaluate a property value.

        Supported value formats:
        - Literal: 100, "red", [1, 2, 3]
        - Lua expression: {lua: "ams.random_range(-60, -120)"}
        - Generator call: {call: "grid_position", args: {row: 1, col: 5}}
        - Inline generator: {lua: "full generator code", args: {x: 10}}

        Generator scripts live in ams/behaviors/generators/ and expose a
        generate(args) function that returns the computed value.
        """
        if isinstance(value, dict):
            if 'lua' in value and 'args' in value:
                # Inline generator: register then call
                lua_code = value['lua']
                name = f'_inline_generator_{self._inline_generator_counter}'
                self._inline_generator_counter += 1

                if self._behavior_engine.load_inline_subroutine('generator', name, lua_code):
                    args = value.get('args', {})
                    evaluated_args = {}
                    for k, v in args.items():
                        evaluated_args[k] = self._evaluate_property_value(v)
                    return self._behavior_engine.call_generator(name, evaluated_args)
                else:
                    log.error(f"Failed to load inline generator")
                    return None
            elif 'lua' in value:
                # Simple Lua expression
                return self._behavior_engine.evaluate_expression(value['lua'])
            elif 'call' in value:
                # Named generator call
                script_name = value['call']
                args = value.get('args', {})
                # Recursively evaluate args (they may also contain {lua:...})
                evaluated_args = {}
                for k, v in args.items():
                    evaluated_args[k] = self._evaluate_property_value(v)
                return self._behavior_engine.call_generator(script_name, evaluated_args)
        return value

    def lose_life(self) -> None:
        """Lose a life."""
        self._lives -= 1
        if self._lives <= 0:
            self._internal_state = GameState.GAME_OVER

    def render(self, screen: pygame.Surface) -> None:
        """Render the game."""
        # Clear with background color
        bg = (20, 20, 30)
        if self._game_def:
            bg = self._game_def.background_color
        screen.fill(bg)

        # Update skin's elapsed time for $age property
        self._skin._elapsed_time = self._behavior_engine.elapsed_time

        # Render all renderable entities
        for entity in self._behavior_engine.get_alive_entities():
            if entity.renderable:
                self._skin.render_entity(entity, screen)

        # Render HUD
        self._skin.render_hud(screen, self.get_score(), self._lives, self._level_name)

        # Render game over / win overlay
        if self._internal_state == GameState.GAME_OVER:
            self._render_overlay(screen, "GAME OVER", (255, 100, 100))
        elif self._internal_state == GameState.WON:
            self._render_overlay(screen, "YOU WIN!", (100, 255, 100))

    def _render_overlay(self, screen: pygame.Surface, text: str,
                        color: Tuple[int, int, int]) -> None:
        """Render a centered text overlay."""
        font = pygame.font.Font(None, 72)
        text_surf = font.render(text, True, color)
        rect = text_surf.get_rect(center=(self._screen_width // 2,
                                          self._screen_height // 2))
        screen.blit(text_surf, rect)

        font_small = pygame.font.Font(None, 36)
        score_text = font_small.render(f"Final Score: {self.get_score()}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self._screen_width // 2,
                                                 self._screen_height // 2 + 50))
        screen.blit(score_text, score_rect)

    def reset(self) -> None:
        """Reset game state."""
        super().reset()
        self._behavior_engine.clear()
        self._score = 0
        self._lives = self._starting_lives
        self._internal_state = GameState.PLAYING
        self._spawn_initial_entities()

    # =========================================================================
    # LifecycleProvider Protocol Implementation
    # =========================================================================

    def on_entity_spawned(self, entity: 'Entity', lua_engine: 'LuaEngine') -> None:
        """Called when an entity is created and registered."""
        self._dispatch_to_behaviors('on_spawn', entity, lua_engine)

    def on_entity_update(self, entity: 'Entity', lua_engine: 'LuaEngine', dt: float) -> None:
        """Called each frame for alive entities."""
        self._dispatch_to_behaviors('on_update', entity, lua_engine, dt)

    def on_entity_destroyed(self, entity: 'Entity', lua_engine: 'LuaEngine') -> None:
        """Called when an entity is destroyed and about to be removed."""
        self._dispatch_to_behaviors('on_destroy', entity, lua_engine)

    def dispatch_lifecycle(
        self, hook_name: str, entity: 'Entity', lua_engine: 'LuaEngine', *args
    ) -> None:
        """Dispatch a generic lifecycle hook to entity's attached behaviors.

        Used for hooks like on_hit that aren't part of the core lifecycle.

        Args:
            hook_name: Lifecycle hook (e.g., 'on_hit')
            entity: The entity receiving the event
            lua_engine: LuaEngine for subroutine lookup
            *args: Additional arguments passed to the hook
        """
        self._dispatch_to_behaviors(hook_name, entity, lua_engine, *args)

    def _dispatch_to_behaviors(
        self, method_name: str, entity: 'Entity', lua_engine: 'LuaEngine', *args
    ) -> None:
        """Internal helper to dispatch a method to entity's behaviors.

        Args:
            method_name: Method name to call on behaviors
            entity: The entity receiving the event
            lua_engine: LuaEngine for subroutine lookup
            *args: Additional arguments
        """
        # GameEntity has behaviors, Entity ABC does not
        if not hasattr(entity, 'behaviors'):
            return

        for behavior_name in entity.behaviors:
            behavior = lua_engine.get_subroutine('behavior', behavior_name)
            if behavior is None:
                continue

            method = getattr(behavior, method_name, None)
            if method is None:
                continue

            try:
                method(entity.id, *args)
            except Exception as e:
                log.error(f"Error in {behavior_name}.{method_name}: {e}")

    def dispatch_scheduled(
        self, callback_name: str, entity: 'Entity', lua_engine: 'LuaEngine'
    ) -> None:
        """Dispatch a scheduled callback to entity's attached behaviors.

        Called by LuaEngine when a scheduled callback timer fires.

        Args:
            callback_name: Name of the callback method to invoke
            entity: The entity that scheduled the callback
            lua_engine: LuaEngine for subroutine lookup
        """
        # GameEntity has behaviors, Entity ABC does not
        if not hasattr(entity, 'behaviors'):
            return

        for behavior_name in entity.behaviors:
            behavior = lua_engine.get_subroutine('behavior', behavior_name)
            if behavior is None:
                continue

            callback = getattr(behavior, callback_name, None)
            if callback:
                try:
                    callback(entity.id)
                except Exception as e:
                    log.error(f"Error in scheduled {callback_name}: {e}")
