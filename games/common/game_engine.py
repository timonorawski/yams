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

        def _get_skin(self, skin_name: str) -> GameEngineSkin:
            return MyGameSkin()
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pygame
import yaml

from games.common import BaseGame, GameState
from games.common.input import InputEvent
from ams.behaviors import BehaviorEngine, Entity


@dataclass
class RenderCommand:
    """A single render primitive."""
    shape: str  # rectangle, circle, triangle, polygon, line, sprite
    color: str = "$color"  # Color or $property reference
    fill: bool = True
    line_width: int = 1
    # Shape-specific:
    points: List[Tuple[float, float]] = field(default_factory=list)  # For polygon/triangle (normalized 0-1)
    offset: Tuple[float, float] = (0, 0)  # Offset from entity position
    size: Optional[Tuple[float, float]] = None  # Override entity size
    sprite_name: str = ""  # For sprite shape
    radius: Optional[float] = None  # For circle (normalized to min(w,h)/2)


@dataclass
class EntityTypeConfig:
    """Configuration for an entity type from YAML."""

    name: str
    width: float = 32.0
    height: float = 32.0
    color: str = "white"
    sprite: str = ""
    behaviors: List[str] = field(default_factory=list)
    behavior_config: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    health: int = 1
    points: int = 0
    tags: List[str] = field(default_factory=list)
    extends: Optional[str] = None  # Base type this extends
    base_type: Optional[str] = None  # Resolved base type (for win conditions)
    render_as: List[str] = field(default_factory=list)  # Composite rendering
    render: List[RenderCommand] = field(default_factory=list)  # Render primitives


@dataclass
class SpawnConfig:
    """Configuration for spawning an entity during transform."""
    entity_type: str
    offset: Tuple[float, float] = (0, 0)  # Relative to parent position
    properties: Dict[str, Any] = field(default_factory=dict)  # Properties to set on spawned entity


@dataclass
class TransformConfig:
    """Configuration for entity transformation."""
    into: str  # Target entity type to transform into
    spawn: List[SpawnConfig] = field(default_factory=list)  # Additional entities to spawn


@dataclass
class WhenCondition:
    """Condition for triggering an action."""
    property: str  # Property name to check
    value: Any  # Expected value


@dataclass
class InputAction:
    """Action to take on input for an entity type."""
    transform: Optional[TransformConfig] = None  # Transform on input
    when: Optional[WhenCondition] = None  # Condition for triggering


@dataclass
class CollisionAction:
    """Defines what action to take when entities collide."""
    action: str  # Name of collision action Lua script
    modifier: Dict[str, Any] = field(default_factory=dict)  # Config passed to action


@dataclass
class CollisionRule:
    """Defines what types collide and how."""
    type_a: str  # Entity type or base type
    type_b: str  # Entity type or base type
    # Both entities get on_hit called when they collide


@dataclass
class LoseConditionConfig:
    """Configuration for a lose condition."""
    entity_type: str  # Type to watch
    event: str  # Event type: "exited_screen", "health_zero", etc.
    edge: Optional[str] = None  # For exited_screen: "top", "bottom", "left", "right", "any"
    action: str = "lose_life"  # Action to take
    then_destroy: Optional[str] = None  # Entity type to destroy
    then_transform: Optional[Dict[str, str]] = None  # {entity_type: X, into: Y}


@dataclass
class InputMappingConfig:
    """Configuration for input mapping to an entity type."""
    target_x: Optional[str] = None  # Property to set from input.position.x
    target_y: Optional[str] = None  # Property to set from input.position.y
    on_input: Optional[InputAction] = None  # Action to take on input


@dataclass
class GameDefinition:
    """Complete game definition loaded from YAML."""

    name: str = "Unnamed Game"
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    screen_width: int = 800
    screen_height: int = 600
    background_color: Tuple[int, int, int] = (20, 20, 30)
    defaults: Dict[str, Any] = field(default_factory=dict)  # Default settings (lives, etc.)

    # Entity type definitions
    entity_types: Dict[str, EntityTypeConfig] = field(default_factory=dict)

    # Collision rules - which entity types collide (legacy)
    collisions: List[CollisionRule] = field(default_factory=list)

    # Collision behaviors - nested dict defining actions when types collide
    # Format: collision_behaviors[type_a][type_b] = CollisionAction
    # Example: collision_behaviors['ball']['paddle'] = CollisionAction('bounce_paddle', {...})
    collision_behaviors: Dict[str, Dict[str, CollisionAction]] = field(default_factory=dict)

    # Input mapping - how input affects entity types
    # Format: input_mapping[entity_type] = InputMappingConfig
    input_mapping: Dict[str, InputMappingConfig] = field(default_factory=dict)

    # Lose conditions - events that cause life loss
    lose_conditions: List[LoseConditionConfig] = field(default_factory=list)

    # Player config
    player_type: Optional[str] = None
    player_spawn: Tuple[float, float] = (400, 500)

    # Win/lose conditions
    win_condition: str = "destroy_all"  # destroy_all, survive_time, reach_score
    win_target: int = 0  # Score target or time in seconds
    win_target_type: Optional[str] = None  # For destroy_all: base type to destroy
    lose_on_player_death: bool = True

    # Default layout (used when no level specified)
    default_layout: Optional[Dict[str, Any]] = None


class GameEngineSkin:
    """Abstract base for GameEngine rendering.

    Subclasses implement game-specific rendering for entities.
    Uses render commands from game.yaml when available.
    """

    def __init__(self):
        self._game_def: Optional[GameDefinition] = None

    def set_game_definition(self, game_def: GameDefinition) -> None:
        """Set game definition for render command lookup."""
        self._game_def = game_def

    def render_entity(self, entity: Entity, screen: pygame.Surface) -> None:
        """Render an entity using YAML render commands or fallback."""
        # Look up render commands from game definition
        if self._game_def:
            type_config = self._game_def.entity_types.get(entity.entity_type)
            if type_config and type_config.render:
                self._render_commands(entity, type_config.render, screen)
                return

        # Fallback: simple colored rectangle
        color = self._parse_color(entity.color)
        rect = pygame.Rect(int(entity.x), int(entity.y),
                           int(entity.width), int(entity.height))
        pygame.draw.rect(screen, color, rect)

    def _render_commands(self, entity: Entity, commands: List[RenderCommand],
                         screen: pygame.Surface) -> None:
        """Render entity using a list of render commands."""
        for cmd in commands:
            self._render_command(entity, cmd, screen)

    def _render_command(self, entity: Entity, cmd: RenderCommand,
                        screen: pygame.Surface) -> None:
        """Render a single command."""
        # Resolve color (handle $property references)
        color = self._resolve_color(entity, cmd.color)

        # Calculate position and size
        x = int(entity.x + cmd.offset[0])
        y = int(entity.y + cmd.offset[1])
        w = int(cmd.size[0] if cmd.size else entity.width)
        h = int(cmd.size[1] if cmd.size else entity.height)

        if cmd.shape == 'rectangle':
            rect = pygame.Rect(x, y, w, h)
            if cmd.fill:
                pygame.draw.rect(screen, color, rect)
            else:
                pygame.draw.rect(screen, color, rect, cmd.line_width)

        elif cmd.shape == 'circle':
            # Radius: use explicit, or derive from entity size
            if cmd.radius is not None:
                radius = int(cmd.radius * min(w, h) / 2)
            else:
                radius = min(w, h) // 2
            center = (x + w // 2, y + h // 2)
            if cmd.fill:
                pygame.draw.circle(screen, color, center, radius)
            else:
                pygame.draw.circle(screen, color, center, radius, cmd.line_width)

        elif cmd.shape == 'triangle':
            # Points are normalized (0-1) relative to entity bounds
            if cmd.points and len(cmd.points) >= 3:
                points = [(x + int(p[0] * w), y + int(p[1] * h))
                          for p in cmd.points[:3]]
            else:
                # Default: pointing up
                points = [(x + w // 2, y), (x, y + h), (x + w, y + h)]
            if cmd.fill:
                pygame.draw.polygon(screen, color, points)
            else:
                pygame.draw.polygon(screen, color, points, cmd.line_width)

        elif cmd.shape == 'polygon':
            if cmd.points:
                points = [(x + int(p[0] * w), y + int(p[1] * h))
                          for p in cmd.points]
                if cmd.fill:
                    pygame.draw.polygon(screen, color, points)
                else:
                    pygame.draw.polygon(screen, color, points, cmd.line_width)

        elif cmd.shape == 'line':
            if cmd.points and len(cmd.points) >= 2:
                start = (x + int(cmd.points[0][0] * w), y + int(cmd.points[0][1] * h))
                end = (x + int(cmd.points[1][0] * w), y + int(cmd.points[1][1] * h))
                pygame.draw.line(screen, color, start, end, cmd.line_width)

        elif cmd.shape == 'sprite':
            # Sprite rendering - subclasses can override for asset loading
            self._render_sprite(entity, cmd.sprite_name or entity.sprite, screen, x, y, w, h)

    def _render_sprite(self, entity: Entity, sprite_name: str,
                       screen: pygame.Surface, x: int, y: int, w: int, h: int) -> None:
        """Render a sprite. Override in subclasses for actual sprite loading."""
        # Default: fallback to colored rectangle
        color = self._parse_color(entity.color)
        pygame.draw.rect(screen, color, pygame.Rect(x, y, w, h))

    def _resolve_color(self, entity: Entity, color_ref: str) -> Tuple[int, int, int]:
        """Resolve color reference (e.g., $color) to RGB."""
        if color_ref.startswith('$'):
            prop_name = color_ref[1:]
            if prop_name == 'color':
                return self._parse_color(entity.color)
            # Could also look up entity.properties[prop_name]
            prop_val = entity.properties.get(prop_name, entity.color)
            return self._parse_color(str(prop_val))
        return self._parse_color(color_ref)

    def render_hud(self, screen: pygame.Surface, score: int, lives: int,
                   level_name: str = "") -> None:
        """Render HUD elements."""
        font = pygame.font.Font(None, 36)

        # Score
        score_text = font.render(f"Score: {score}", True, (255, 255, 255))
        screen.blit(score_text, (10, 10))

        # Lives
        lives_text = font.render(f"Lives: {lives}", True, (255, 255, 255))
        screen.blit(lives_text, (screen.get_width() - 120, 10))

        # Level name
        if level_name:
            level_text = font.render(level_name, True, (200, 200, 200))
            level_rect = level_text.get_rect(centerx=screen.get_width() // 2, y=10)
            screen.blit(level_text, level_rect)

    def update(self, dt: float) -> None:
        """Update skin animations."""
        pass

    def play_sound(self, sound_name: str) -> None:
        """Play a sound effect."""
        pass

    def _parse_color(self, color_str: str) -> Tuple[int, int, int]:
        """Parse color string to RGB tuple."""
        colors = {
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'red': (220, 60, 60),
            'green': (60, 220, 60),
            'blue': (60, 60, 220),
            'yellow': (220, 220, 60),
            'orange': (220, 140, 60),
            'purple': (160, 60, 220),
            'cyan': (60, 220, 220),
            'gray': (128, 128, 128),
            'silver': (192, 192, 192),
        }
        return colors.get(color_str.lower(), (255, 255, 255))


class GameEngine(BaseGame):
    """YAML-driven game engine with Lua behaviors.

    This extends BaseGame to provide:
    - Automatic entity management via BehaviorEngine
    - YAML-based game definitions
    - Lua behavior scripting
    - Standard collision detection patterns

    Subclasses must implement:
    - _get_skin(): Return rendering skin instance
    - _handle_collision(): Game-specific collision logic

    Can optionally implement:
    - _on_entity_destroyed(): Handle entity death
    - _spawn_initial_entities(): Create starting entities
    """

    # Game definition file (override in subclass)
    GAME_DEF_FILE: Optional[Path] = None

    # Custom behaviors directory (override to add game-specific behaviors)
    BEHAVIORS_DIR: Optional[Path] = None

    def __init__(
        self,
        skin: str = 'default',
        lives: int = 3,
        width: int = 800,
        height: int = 600,
        **kwargs,
    ):
        """Initialize game engine.

        Args:
            skin: Skin name for rendering
            lives: Starting lives
            width: Screen width
            height: Screen height
            **kwargs: BaseGame arguments
        """
        # Initialize before super().__init__ (may call _apply_level_config)
        self._starting_lives = lives
        self._lives = lives
        self._screen_width = width
        self._screen_height = height
        self._score = 0
        self._internal_state = GameState.PLAYING
        self._game_def: Optional[GameDefinition] = None
        self._level_name = ""

        # Create behavior engine
        self._behavior_engine = BehaviorEngine(
            screen_width=width,
            screen_height=height,
        )

        # Load core behaviors
        self._behavior_engine.load_behaviors_from_dir()

        # Load game-specific behaviors
        if self.BEHAVIORS_DIR and self.BEHAVIORS_DIR.exists():
            self._behavior_engine.load_behaviors_from_dir(self.BEHAVIORS_DIR)

        # Load game definition
        if self.GAME_DEF_FILE and self.GAME_DEF_FILE.exists():
            self._game_def = self._load_game_definition(self.GAME_DEF_FILE)

        # Create skin and give it access to game definition
        self._skin = self._get_skin(skin)
        if self._game_def:
            self._skin.set_game_definition(self._game_def)

        # Player entity reference
        self._player_id: Optional[str] = None

        # Call super init (may load levels)
        super().__init__(**kwargs)

        # Spawn initial entities if no level loaded
        if not self._behavior_engine.entities:
            self._spawn_initial_entities()

    def _load_game_definition(self, path: Path) -> GameDefinition:
        """Load game definition from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

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
        )

        # First pass: parse all entity types
        raw_types = data.get('entity_types', {})
        for name, type_data in raw_types.items():
            # Parse render commands
            render_commands = []
            for render_data in type_data.get('render', []):
                render_commands.append(RenderCommand(
                    shape=render_data.get('shape', 'rectangle'),
                    color=render_data.get('color', '$color'),
                    fill=render_data.get('fill', True),
                    line_width=render_data.get('line_width', 1),
                    points=[tuple(p) for p in render_data.get('points', [])],
                    offset=tuple(render_data.get('offset', [0, 0])),
                    size=tuple(render_data['size']) if render_data.get('size') else None,
                    sprite_name=render_data.get('sprite', ''),
                    radius=render_data.get('radius'),
                ))

            game_def.entity_types[name] = EntityTypeConfig(
                name=name,
                width=type_data.get('width', 32),
                height=type_data.get('height', 32),
                color=type_data.get('color', 'white'),
                sprite=type_data.get('sprite', ''),
                behaviors=type_data.get('behaviors', []),
                behavior_config=type_data.get('behavior_config', {}),
                health=type_data.get('health', 1),
                points=type_data.get('points', 0),
                tags=type_data.get('tags', []),
                extends=type_data.get('extends'),
                render_as=type_data.get('render_as', []),
                render=render_commands,
            )

        # Second pass: resolve inheritance
        self._resolve_entity_inheritance(game_def)

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
        #       action: bounce_paddle
        #       modifier:
        #         max_angle: 60
        raw_collision_behaviors = data.get('collision_behaviors', {})
        for type_a, targets in raw_collision_behaviors.items():
            if type_a not in game_def.collision_behaviors:
                game_def.collision_behaviors[type_a] = {}
            for type_b, action_data in targets.items():
                if isinstance(action_data, str):
                    # Simple format: just action name
                    game_def.collision_behaviors[type_a][type_b] = CollisionAction(
                        action=action_data
                    )
                elif isinstance(action_data, dict):
                    # Full format with modifier
                    game_def.collision_behaviors[type_a][type_b] = CollisionAction(
                        action=action_data.get('action', ''),
                        modifier=action_data.get('modifier', {})
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
        raw_input_mapping = data.get('input_mapping', {})
        for entity_type, mapping_data in raw_input_mapping.items():
            on_input = None
            if 'on_input' in mapping_data:
                on_input_data = mapping_data['on_input']
                transform_config = None
                when_condition = None

                # Parse transform
                if 'transform' in on_input_data:
                    transform_data = on_input_data['transform']
                    spawn_configs = []
                    for spawn_data in transform_data.get('spawn', []):
                        # All keys except 'type' and 'offset' become properties
                        props = {k: v for k, v in spawn_data.items()
                                 if k not in ('type', 'offset')}
                        spawn_configs.append(SpawnConfig(
                            entity_type=spawn_data.get('type', ''),
                            offset=tuple(spawn_data.get('offset', [0, 0])),
                            properties=props,
                        ))
                    transform_config = TransformConfig(
                        into=transform_data.get('into', ''),
                        spawn=spawn_configs,
                    )

                # Parse when condition
                if 'when' in on_input_data:
                    when_data = on_input_data['when']
                    when_condition = WhenCondition(
                        property=when_data.get('property', ''),
                        value=when_data.get('value'),
                    )

                on_input = InputAction(
                    transform=transform_config,
                    when=when_condition,
                )

            game_def.input_mapping[entity_type] = InputMappingConfig(
                target_x=mapping_data.get('target_x'),
                target_y=mapping_data.get('target_y'),
                on_input=on_input,
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
                    then_transform = then_data['transform']

            game_def.lose_conditions.append(LoseConditionConfig(
                entity_type=condition_data.get('entity_type', ''),
                event=condition_data.get('event', ''),
                edge=condition_data.get('edge'),
                action=condition_data.get('action', 'lose_life'),
                then_destroy=condition_data.get('then', {}).get('destroy'),
                then_transform=then_transform,
            ))

        # Player config
        if 'player' in data:
            player_data = data['player']
            game_def.player_type = player_data.get('type')
            game_def.player_spawn = tuple(player_data.get('spawn', [400, 500]))

        return game_def

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

                    # Set base_type (walk up the chain)
                    config.base_type = base.base_type or config.extends
            else:
                # No extends - this type is its own base
                config.base_type = name

    @abstractmethod
    def _get_skin(self, skin_name: str) -> GameEngineSkin:
        """Get rendering skin instance.

        Override to return game-specific skin.

        Args:
            skin_name: Requested skin name

        Returns:
            GameEngineSkin instance
        """
        return GameEngineSkin()

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

    def _spawn_default_layout(self) -> None:
        """Spawn entities from default_layout in game.yaml."""
        if not self._game_def or not self._game_def.default_layout:
            return

        layout = self._game_def.default_layout

        # Parse brick_grid if present
        brick_grid = layout.get('brick_grid')
        if brick_grid:
            start_x = brick_grid.get('start_x', 65)
            start_y = brick_grid.get('start_y', 60)
            cols = brick_grid.get('cols', 10)
            rows = brick_grid.get('rows', 5)
            row_types = brick_grid.get('row_types', ['brick'])

            # Get brick dimensions from first row type
            first_type = row_types[0] if row_types else 'brick'
            type_config = self._game_def.entity_types.get(first_type)
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

    def spawn_entity(
        self,
        entity_type: str,
        x: float,
        y: float,
        properties: Optional[Dict[str, Any]] = None,
        **overrides,
    ) -> Optional[Entity]:
        """Spawn an entity of a defined type.

        Args:
            entity_type: Type name from game definition
            x, y: Position
            properties: Initial properties (available to on_spawn)
            **overrides: Override default type properties

        Returns:
            Created Entity, or None if type not found
        """
        # Get type config
        type_config = None
        if self._game_def:
            type_config = self._game_def.entity_types.get(entity_type)

        # Use type config or defaults
        if type_config:
            behaviors = overrides.get('behaviors', type_config.behaviors)
            behavior_config = overrides.get('behavior_config', type_config.behavior_config)

            entity = self._behavior_engine.create_entity(
                entity_type=entity_type,
                x=x,
                y=y,
                width=overrides.get('width', type_config.width),
                height=overrides.get('height', type_config.height),
                color=overrides.get('color', type_config.color),
                sprite=overrides.get('sprite', type_config.sprite),
                health=overrides.get('health', type_config.health),
                behaviors=behaviors,
                behavior_config=behavior_config,
                properties=properties or {},
            )
        else:
            # Create with overrides only
            entity = self._behavior_engine.create_entity(
                entity_type=entity_type,
                x=x,
                y=y,
                properties=properties or {},
                **overrides,
            )

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
            # Apply declarative input_mapping
            self._apply_input_mapping(event)
            # Call subclass handler for any additional logic
            self._handle_player_input(event)

    def _apply_input_mapping(self, event: InputEvent) -> None:
        """Apply input mapping from game.yaml to entities."""
        if not self._game_def or not self._game_def.input_mapping:
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
                    entity.properties[mapping.target_x] = event.position.x
                if mapping.target_y:
                    entity.properties[mapping.target_y] = event.position.y

                # Check for on_input action
                if mapping.on_input:
                    self._handle_input_action(entity, mapping.on_input)

    def _handle_input_action(self, entity: Entity, action: InputAction) -> None:
        """Handle an input action for an entity."""
        # Check when condition if present
        if action.when:
            prop_value = entity.properties.get(action.when.property)
            if prop_value != action.when.value:
                # Condition not met, skip action
                return

        # Execute transform if configured
        if action.transform:
            self.transform_entity(
                entity,
                action.transform.into,
                action.transform.spawn
            )

    def _handle_player_input(self, event: InputEvent) -> None:
        """Handle a single input event.

        Override in subclass for game-specific input handling.
        """
        pass

    def update(self, dt: float) -> None:
        """Update game state."""
        if self._internal_state != GameState.PLAYING:
            return

        # Update behavior engine (moves entities, fires callbacks)
        self._behavior_engine.update(dt)

        # Process queued sounds
        for sound in self._behavior_engine.pop_sounds():
            self._skin.play_sound(sound)

        # Check collisions
        self._check_collisions()

        # Handle destroyed entities
        self._handle_destroyed_entities()

        # Update skin
        self._skin.update(dt)

        # Check win/lose conditions
        self._check_win_conditions()
        self._check_lose_conditions()

    def _check_collisions(self) -> None:
        """Check collisions based on rules defined in game.yaml.

        For each collision rule, finds all entity pairs that match and
        calls on_hit on both entities' behaviors.
        """
        if not self._game_def or not self._game_def.collisions:
            return

        alive_entities = self._behavior_engine.get_alive_entities()

        # Track collisions already processed this frame to avoid duplicates
        processed: set[str] = set()

        for rule in self._game_def.collisions:
            # Find entities matching each side of the rule
            entities_a = self._get_entities_matching_type(rule.type_a, alive_entities)
            entities_b = self._get_entities_matching_type(rule.type_b, alive_entities)

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

        Override to add scoring, effects, etc.
        """
        # Default: add points if entity type has them
        if self._game_def:
            type_config = self._game_def.entity_types.get(entity.entity_type)
            if type_config:
                self._score += type_config.points

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
            target_type = condition.then_transform.get('entity_type')
            into_type = condition.then_transform.get('into')
            if target_type and into_type:
                targets = self._get_entities_matching_type(
                    target_type,
                    self._behavior_engine.get_alive_entities()
                )
                if targets:
                    # Transform first matching entity
                    self.transform_entity(targets[0], into_type)

    def transform_entity(self, entity: Entity, into_type: str,
                         spawn_configs: Optional[List[SpawnConfig]] = None) -> Optional[Entity]:
        """Transform an entity into another type, optionally spawning children.

        This is the core transform primitive - entity becomes fundamentally different.

        Args:
            entity: The entity to transform
            into_type: Entity type to transform into
            spawn_configs: Optional list of entities to spawn alongside

        Returns:
            The transformed entity (same ID, different type)
        """
        if not self._game_def or into_type not in self._game_def.entity_types:
            return None

        # Get the new type config
        new_config = self._game_def.entity_types[into_type]

        # Transform the entity - keep position and ID, change type
        entity.entity_type = into_type
        entity.width = new_config.width
        entity.height = new_config.height
        entity.color = new_config.color
        entity.sprite = new_config.sprite

        # Update behaviors
        entity.behaviors = new_config.behaviors.copy()
        entity.behavior_config = dict(new_config.behavior_config)

        # Re-register with behavior engine for new behaviors
        self._behavior_engine.update_entity_behaviors(entity)

        # Spawn child entities if configured
        if spawn_configs:
            for spawn in spawn_configs:
                # Calculate spawn position
                spawn_x = entity.x + spawn.offset[0]
                spawn_y = entity.y + spawn.offset[1]

                # Evaluate spawn properties (handle {lua: ...} expressions)
                spawn_props = {
                    key: self._evaluate_property_value(value)
                    for key, value in spawn.properties.items()
                }

                # Spawn the child entity with properties already set
                # (so on_spawn can access them)
                child = self.spawn_entity(
                    spawn.entity_type, spawn_x, spawn_y,
                    properties=spawn_props
                )

        return entity

    def _evaluate_property_value(self, value: Any) -> Any:
        """Evaluate a property value - either literal or {lua: "expression"}."""
        if isinstance(value, dict) and 'lua' in value:
            return self._behavior_engine.evaluate_expression(value['lua'])
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

        # Render all entities
        for entity in self._behavior_engine.get_alive_entities():
            if entity.visible:
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
