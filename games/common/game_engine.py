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
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

import pygame
import yaml

from games.common import BaseGame, GameState
from games.common.input import InputEvent
from ams.behaviors import BehaviorEngine, Entity


# =============================================================================
# Schema Validation
# =============================================================================

import os

_game_schema: Optional[Dict[str, Any]] = None
_SCHEMAS_DIR = Path(__file__).parent.parent.parent / 'schemas'

# Set AMS_SKIP_SCHEMA_VALIDATION=1 to disable strict validation
_SKIP_VALIDATION = os.environ.get('AMS_SKIP_SCHEMA_VALIDATION', '').lower() in ('1', 'true', 'yes')


class SchemaValidationError(Exception):
    """Raised when YAML data fails schema validation."""
    pass


def _get_game_schema() -> Optional[Dict[str, Any]]:
    """Lazy-load game schema."""
    global _game_schema
    if _game_schema is None:
        schema_path = _SCHEMAS_DIR / 'game.schema.json'
        if schema_path.exists():
            with open(schema_path) as f:
                _game_schema = json.load(f)
    return _game_schema


def validate_game_yaml(data: Dict[str, Any], source_path: Optional[Path] = None) -> None:
    """Validate game YAML data against schema.

    Args:
        data: Parsed YAML data
        source_path: Optional path for error messages

    Raises:
        SchemaValidationError: If validation fails (unless AMS_SKIP_SCHEMA_VALIDATION=1)
        ImportError: If jsonschema is not installed (unless AMS_SKIP_SCHEMA_VALIDATION=1)
    """
    schema = _get_game_schema()
    if schema is None:
        error_msg = f"Schema file not found: {_SCHEMAS_DIR / 'game.schema.json'}"
        if _SKIP_VALIDATION:
            print(f"[GameEngine] Warning: {error_msg}")
            return
        raise SchemaValidationError(error_msg)

    try:
        import jsonschema
        from jsonschema import RefResolver
    except ImportError as e:
        error_msg = "jsonschema package not installed - required for YAML validation"
        if _SKIP_VALIDATION:
            print(f"[GameEngine] Warning: {error_msg}")
            return
        raise ImportError(error_msg) from e

    try:
        # Create resolver with local schema store for external $ref
        schema_store = {}
        for schema_file in _SCHEMAS_DIR.glob('*.json'):
            with open(schema_file) as f:
                schema_store[schema_file.name] = json.load(f)

        resolver = RefResolver.from_schema(schema, store=schema_store)
        jsonschema.validate(data, schema, resolver=resolver)
    except jsonschema.ValidationError as e:
        path_str = f" in {source_path}" if source_path else ""
        error_msg = f"Schema validation error{path_str}: {e.message} at {'/'.join(str(p) for p in e.absolute_path)}"
        if _SKIP_VALIDATION:
            print(f"[GameEngine] Warning: {error_msg}")
        else:
            raise SchemaValidationError(error_msg) from e
    except jsonschema.SchemaError as e:
        error_msg = f"Invalid schema: {e.message}"
        if _SKIP_VALIDATION:
            print(f"[GameEngine] Warning: {error_msg}")
        else:
            raise SchemaValidationError(error_msg) from e


# Protocol for entity placements in levels
@dataclass
class EntityPlacement:
    """An entity to spawn at a specific position."""
    entity_type: str
    x: float
    y: float


@runtime_checkable
class GameEngineLevelData(Protocol):
    """Protocol for level data that GameEngine can apply.

    Level loaders should return data conforming to this protocol.
    """
    name: str
    lives: int

    # Player spawn position (uses game.yaml player.type)
    player_x: float
    player_y: float

    # Entity placements to spawn
    entities: List[EntityPlacement]


@dataclass
class RenderWhen:
    """Condition for conditional rendering."""
    property: str
    value: Any = None
    compare: str = "equals"  # equals, not_equals, greater_than, less_than


@dataclass
class RenderCommand:
    """A single render primitive."""
    shape: str  # rectangle, circle, triangle, polygon, line, sprite, text
    color: str = "$color"  # Color or $property reference
    fill: bool = True
    line_width: int = 1
    alpha: Any = None  # 0-255 or $property or {lua: expr} (None = fully opaque)
    # Shape-specific:
    points: List[Tuple[float, float]] = field(default_factory=list)  # For polygon/triangle (normalized 0-1)
    offset: Tuple[float, float] = (0, 0)  # Offset from entity position
    size: Optional[Tuple[float, float]] = None  # Override entity size
    sprite_name: str = ""  # For sprite shape
    radius: Optional[float] = None  # For circle (normalized to min(w,h)/2)
    # Text shape:
    text: str = ""  # Text content or $property reference
    font_size: int = 20
    align: str = "center"  # center, left, right
    # Conditional rendering:
    when: Optional[RenderWhen] = None  # Only render if condition is true


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

    # Lifecycle transforms
    on_destroy: Optional['TransformConfig'] = None  # Transform on destroy (explosions, death effects)
    on_update: List['OnUpdateTransform'] = field(default_factory=list)  # Conditional transforms


@dataclass
class SpawnConfig:
    """Configuration for spawning an entity during transform."""
    entity_type: str
    offset: Tuple[float, float] = (0, 0)  # Relative to parent position
    count: int = 1  # Number to spawn (for radial explosions, etc.)
    inherit_velocity: float = 0.0  # Fraction of parent velocity to add (0-1)
    lifetime: Optional[float] = None  # Auto-destroy after N seconds
    properties: Dict[str, Any] = field(default_factory=dict)  # Properties ({lua: ...} expressions supported)


@dataclass
class TransformConfig:
    """Configuration for entity transformation.

    Types:
    - "destroy" - Destroy entity, spawn children only (death effects)
    - "<entity_type>" - Transform into another type, optionally spawn children
    """
    type: str = "destroy"  # "destroy" or entity type name
    children: List[SpawnConfig] = field(default_factory=list)  # Entities to spawn


@dataclass
class WhenCondition:
    """Extensible condition for triggering actions.

    Supports multiple condition types:
    - property/value: Check entity property equals value
    - age: Check entity age in range [min, max)
    - interval: Repeat every N seconds (uses last_trigger tracking)
    """
    # Property check
    property: Optional[str] = None  # Property name to check
    value: Any = None  # Expected value

    # Age check (seconds since spawn)
    age_min: Optional[float] = None  # Min age (inclusive)
    age_max: Optional[float] = None  # Max age (exclusive)

    # Repeating
    interval: Optional[float] = None  # Repeat every N seconds


@dataclass
class OnUpdateTransform:
    """Transform triggered during update based on conditions."""
    when: Optional[WhenCondition] = None  # Condition (age, property, interval)
    transform: Optional[TransformConfig] = None


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
class TargetedTransform:
    """Transform targeting a specific entity type (for lose conditions)."""
    entity_type: str  # Which entity type to transform
    transform: TransformConfig  # The transform to apply


@dataclass
class LoseConditionConfig:
    """Configuration for a lose condition."""
    entity_type: str  # Type to watch
    event: str  # Event type: "exited_screen", "property_true", etc.
    edge: Optional[str] = None  # For exited_screen: "top", "bottom", "left", "right", "any"
    property_name: Optional[str] = None  # For property_true: property to check
    action: str = "lose_life"  # Action to take
    then_destroy: Optional[str] = None  # Entity type to destroy
    then_transform: Optional[TargetedTransform] = None  # Transform another entity
    then_clear_property: Optional[str] = None  # Property to clear after action


@dataclass
class InputMappingConfig:
    """Configuration for input mapping to an entity type."""
    target_x: Optional[str] = None  # Property to set from input.position.x
    target_y: Optional[str] = None  # Property to set from input.position.y
    on_input: Optional[InputAction] = None  # Action to take on input


@dataclass
class SpriteRegion:
    """A rectangular region within a sprite sheet."""
    x: int
    y: int
    width: int
    height: int


@dataclass
class SpriteSheet:
    """A sprite sheet with named regions."""
    file: str  # Path to image file
    transparent: Optional[Tuple[int, int, int]] = None  # RGB color key for transparency
    regions: Dict[str, SpriteRegion] = field(default_factory=dict)  # Named regions


@dataclass
class SpriteConfig:
    """Configuration for a sprite - file path, data URI, or sheet region.

    Supports:
    - File path: file: sprites/paddle.png
    - Data URI: data: "data:image/png;base64,iVBORw0KGgo..."
    - Either can have region extraction (x, y, width, height)
    """
    file: str = ""  # Path to image file (mutually exclusive with data)
    data: Optional[str] = None  # Data URI (data:image/png;base64,...)
    transparent: Optional[Tuple[int, int, int]] = None  # RGB color key
    # For sprite sheets:
    x: Optional[int] = None  # Region x offset
    y: Optional[int] = None  # Region y offset
    width: Optional[int] = None  # Region width (None = full image)
    height: Optional[int] = None  # Region height (None = full image)


@dataclass
class SoundConfig:
    """Configuration for a sound - file path or data URI."""
    file: str = ""  # Path to sound file
    data: Optional[str] = None  # Data URI (data:audio/wav;base64,...)


@dataclass
class AssetsConfig:
    """Configuration for game assets (sounds, sprites).

    Assets can be file paths, embedded data URIs, or references to shared files.

    Shared files (for sprite sheets used by multiple sprites):
        files:
          ducks_sheet: "data:image/png;base64,..."

    Sprites:
    - Simple path: "paddle: sprites/paddle.png"
    - With options: {file: sprites/paddle.png, transparent: [255, 0, 255]}
    - Data URI: {data: "data:image/png;base64,..."}
    - File reference: {file: "@ducks_sheet", x: 0, y: 0, width: 37, height: 42}

    Sounds:
    - Simple path: "hit: sounds/hit.wav"
    - Data URI: {data: "data:audio/wav;base64,..."}
    - File reference: {file: "@sounds_sheet"}
    """
    # Shared file references (name -> path or data URI)
    files: Dict[str, str] = field(default_factory=dict)
    # Sound name -> SoundConfig mapping
    sounds: Dict[str, SoundConfig] = field(default_factory=dict)
    # Sprite name -> SpriteConfig mapping
    sprites: Dict[str, SpriteConfig] = field(default_factory=dict)


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

    # Assets (sounds, sprites)
    assets: AssetsConfig = field(default_factory=AssetsConfig)


class GameEngineSkin:
    """Abstract base for GameEngine rendering.

    Subclasses implement game-specific rendering for entities.
    Uses render commands from game.yaml when available.
    """

    def __init__(self):
        self._game_def: Optional[GameDefinition] = None
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._sprites: Dict[str, pygame.Surface] = {}  # Loaded sprite surfaces
        self._sprite_sheets: Dict[str, pygame.Surface] = {}  # Cached full sheets
        self._assets_dir: Optional[Path] = None
        self._elapsed_time: float = 0.0  # Set by engine each frame

    def set_game_definition(self, game_def: GameDefinition,
                            assets_dir: Optional[Path] = None) -> None:
        """Set game definition for render command lookup and load assets."""
        self._game_def = game_def
        self._assets_dir = assets_dir
        self._load_sounds()
        self._load_sprites()

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
            # Check when condition
            if cmd.when and not self._evaluate_when(entity, cmd.when):
                continue
            self._render_command(entity, cmd, screen)

    def _evaluate_when(self, entity: Entity, when: RenderWhen) -> bool:
        """Evaluate a when condition against entity properties."""
        # Get property value (handle computed properties)
        prop_value = self._get_entity_property(entity, when.property)

        # Compare
        if when.compare == 'equals':
            return prop_value == when.value
        elif when.compare == 'not_equals':
            return prop_value != when.value
        elif when.compare == 'greater_than':
            return prop_value is not None and prop_value > when.value
        elif when.compare == 'less_than':
            return prop_value is not None and prop_value < when.value
        return False

    def _get_entity_property(self, entity: Entity, prop_name: str) -> Any:
        """Get entity property, including computed properties."""
        # Built-in computed properties
        if prop_name == 'damage_ratio':
            max_hits = entity.properties.get('brick_max_hits', 1)
            hits_remaining = entity.properties.get('brick_hits_remaining', max_hits)
            if max_hits > 0:
                return 1 - (hits_remaining / max_hits)
            return 0
        elif prop_name == 'health_ratio':
            max_health = entity.properties.get('max_health', entity.health)
            if max_health > 0:
                return entity.health / max_health
            return 0
        elif prop_name == 'alive':
            return entity.alive
        elif prop_name == 'age':
            # Seconds since spawn
            return self._elapsed_time - entity.spawn_time

        # Regular properties
        return entity.properties.get(prop_name)

    def _render_command(self, entity: Entity, cmd: RenderCommand,
                        screen: pygame.Surface) -> None:
        """Render a single command."""
        # Resolve color (handle $property references)
        color = self._resolve_color(entity, cmd.color)

        # Resolve alpha if specified
        alpha = self._resolve_alpha(entity, cmd.alpha)

        # Calculate position and size
        x = int(entity.x + cmd.offset[0])
        y = int(entity.y + cmd.offset[1])
        w = int(cmd.size[0] if cmd.size else entity.width)
        h = int(cmd.size[1] if cmd.size else entity.height)

        # If alpha specified, render to temp surface then blit
        if alpha is not None and alpha < 255:
            temp_surface = pygame.Surface((w, h), pygame.SRCALPHA)
            self._render_shape_to_surface(temp_surface, cmd, color, 0, 0, w, h, entity)
            temp_surface.set_alpha(alpha)
            screen.blit(temp_surface, (x, y))
        else:
            self._render_shape_to_surface(screen, cmd, color, x, y, w, h, entity)

    def _render_shape_to_surface(self, surface: pygame.Surface, cmd: RenderCommand,
                                  color: Tuple[int, int, int], x: int, y: int,
                                  w: int, h: int, entity: Entity) -> None:
        """Render shape to a surface at given position."""
        if cmd.shape == 'rectangle':
            rect = pygame.Rect(x, y, w, h)
            if cmd.fill:
                pygame.draw.rect(surface, color, rect)
            else:
                pygame.draw.rect(surface, color, rect, cmd.line_width)

        elif cmd.shape == 'circle':
            # Radius: use explicit, or derive from entity size
            if cmd.radius is not None:
                radius = int(cmd.radius * min(w, h) / 2)
            else:
                radius = min(w, h) // 2
            center = (x + w // 2, y + h // 2)
            if cmd.fill:
                pygame.draw.circle(surface, color, center, radius)
            else:
                pygame.draw.circle(surface, color, center, radius, cmd.line_width)

        elif cmd.shape == 'triangle':
            # Points are normalized (0-1) relative to entity bounds
            if cmd.points and len(cmd.points) >= 3:
                points = [(x + int(p[0] * w), y + int(p[1] * h))
                          for p in cmd.points[:3]]
            else:
                # Default: pointing up
                points = [(x + w // 2, y), (x, y + h), (x + w, y + h)]
            if cmd.fill:
                pygame.draw.polygon(surface, color, points)
            else:
                pygame.draw.polygon(surface, color, points, cmd.line_width)

        elif cmd.shape == 'polygon':
            if cmd.points:
                points = [(x + int(p[0] * w), y + int(p[1] * h))
                          for p in cmd.points]
                if cmd.fill:
                    pygame.draw.polygon(surface, color, points)
                else:
                    pygame.draw.polygon(surface, color, points, cmd.line_width)

        elif cmd.shape == 'line':
            if cmd.points and len(cmd.points) >= 2:
                start = (x + int(cmd.points[0][0] * w), y + int(cmd.points[0][1] * h))
                end = (x + int(cmd.points[1][0] * w), y + int(cmd.points[1][1] * h))
                pygame.draw.line(surface, color, start, end, cmd.line_width)

        elif cmd.shape == 'sprite':
            # Sprite rendering - subclasses can override for asset loading
            self._render_sprite(entity, cmd.sprite_name or entity.sprite, surface, x, y, w, h)

        elif cmd.shape == 'text':
            # Text rendering
            text_content = self._resolve_text(entity, cmd.text)
            if text_content:
                font = pygame.font.Font(None, cmd.font_size)
                text_surface = font.render(str(text_content), True, color)
                rect = pygame.Rect(x, y, w, h)
                if cmd.align == 'center':
                    text_rect = text_surface.get_rect(center=rect.center)
                elif cmd.align == 'left':
                    text_rect = text_surface.get_rect(midleft=rect.midleft)
                else:  # right
                    text_rect = text_surface.get_rect(midright=rect.midright)
                surface.blit(text_surface, text_rect)

    def _resolve_alpha(self, entity: Entity, alpha_value: Any) -> Optional[int]:
        """Resolve alpha value (int, $property, or {lua: expr})."""
        if alpha_value is None:
            return None

        if isinstance(alpha_value, (int, float)):
            return int(alpha_value * 255) if alpha_value <= 1 else int(alpha_value)

        if isinstance(alpha_value, str) and alpha_value.startswith('$'):
            prop_name = alpha_value[1:]
            prop_val = self._get_entity_property(entity, prop_name)
            if prop_val is not None:
                # Assume 0-1 range, convert to 0-255
                return int(float(prop_val) * 255)
            return None

        if isinstance(alpha_value, dict) and 'lua' in alpha_value:
            # Lua expression evaluation - needs behavior engine
            # For now, return None (not implemented without engine reference)
            return None

        return None

    def _resolve_text(self, entity: Entity, text_value: str) -> str:
        """Resolve text content ($property references)."""
        if not text_value:
            return ""
        if text_value.startswith('$'):
            prop_name = text_value[1:]
            val = self._get_entity_property(entity, prop_name)
            return str(val) if val is not None else ""
        return text_value

    def _render_sprite(self, entity: Entity, sprite_name: str,
                       screen: pygame.Surface, x: int, y: int, w: int, h: int) -> None:
        """Render a sprite from loaded assets."""
        if not sprite_name:
            # No sprite specified, fallback to colored rectangle
            color = self._parse_color(entity.color)
            pygame.draw.rect(screen, color, pygame.Rect(x, y, w, h))
            return

        # Check if sprite is loaded
        sprite = self._sprites.get(sprite_name)
        if sprite is None:
            # Fallback to colored rectangle
            color = self._parse_color(entity.color)
            pygame.draw.rect(screen, color, pygame.Rect(x, y, w, h))
            return

        # Scale sprite to entity size
        sprite_w, sprite_h = sprite.get_size()
        if sprite_w != w or sprite_h != h:
            scaled = pygame.transform.scale(sprite, (int(w), int(h)))
            # Preserve transparency after scaling
            colorkey = sprite.get_colorkey()
            if colorkey:
                scaled.set_colorkey(colorkey)
            screen.blit(scaled, (x, y))
        else:
            screen.blit(sprite, (x, y))

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
        """Play a sound effect by name (from assets.sounds in game.yaml)."""
        if sound_name in self._sounds:
            self._sounds[sound_name].play()

    def _load_sounds(self) -> None:
        """Load sounds defined in game definition assets."""
        self._sounds.clear()
        if not self._game_def:
            return

        for sound_name, sound_config in self._game_def.assets.sounds.items():
            self._load_sound(sound_name, sound_config)

    def _load_sound(self, name: str, config: SoundConfig) -> None:
        """Load a single sound from config (file path or data URI)."""
        try:
            if config.data:
                # Data URI: decode and load from bytes
                sound = self._load_sound_from_data_uri(config.data)
                if sound:
                    self._sounds[name] = sound
            elif config.file:
                # File path: load from disk
                sound_path = Path(config.file)
                if not sound_path.is_absolute() and self._assets_dir:
                    sound_path = self._assets_dir / config.file

                if sound_path.exists():
                    self._sounds[name] = pygame.mixer.Sound(str(sound_path))
        except Exception as e:
            print(f"[GameEngineSkin] Failed to load sound '{name}': {e}")

    def _load_sound_from_data_uri(self, data_uri: str) -> Optional[pygame.mixer.Sound]:
        """Load a sound from a data URI (data:audio/wav;base64,...)."""
        import base64
        import io

        try:
            # Parse data URI: data:[<mediatype>][;base64],<data>
            if not data_uri.startswith('data:'):
                return None

            # Split header and data
            header, encoded = data_uri.split(',', 1)
            # Decode base64
            audio_bytes = base64.b64decode(encoded)
            # Load from bytes
            return pygame.mixer.Sound(io.BytesIO(audio_bytes))
        except Exception as e:
            print(f"[GameEngineSkin] Failed to load sound from data URI: {e}")
            return None

    def _load_sprites(self) -> None:
        """Load sprites defined in game definition assets."""
        self._sprites.clear()
        self._sprite_sheets.clear()
        if not self._game_def:
            return

        for sprite_name, sprite_config in self._game_def.assets.sprites.items():
            self._load_sprite(sprite_name, sprite_config)

    def _load_sprite(self, name: str, config: SpriteConfig) -> None:
        """Load a single sprite from config (file path or data URI).

        Supports:
        - File paths or data URIs
        - Regions within sprite sheets (x, y, width, height specified)
        - Transparency via color key
        - Shared sheets via @references (cached by data URI hash)
        """
        try:
            sheet: Optional[pygame.Surface] = None

            if config.data:
                # Data URI: decode and load from bytes
                # Use hash of data URI as cache key for deduplication
                # This allows multiple sprites to share the same embedded sheet
                import hashlib
                sheet_key = f"data:{hashlib.md5(config.data.encode()).hexdigest()[:16]}"
                if sheet_key in self._sprite_sheets:
                    sheet = self._sprite_sheets[sheet_key]
                else:
                    sheet = self._load_image_from_data_uri(config.data)
                    if sheet:
                        self._sprite_sheets[sheet_key] = sheet
            elif config.file:
                # File path: load from disk
                sprite_path = Path(config.file)
                if not sprite_path.is_absolute() and self._assets_dir:
                    sprite_path = self._assets_dir / config.file

                if not sprite_path.exists():
                    print(f"[GameEngineSkin] Sprite file not found: {sprite_path}")
                    return

                # Load or get cached sheet
                sheet_key = str(sprite_path)
                if sheet_key not in self._sprite_sheets:
                    sheet = pygame.image.load(str(sprite_path)).convert()
                    self._sprite_sheets[sheet_key] = sheet
                else:
                    sheet = self._sprite_sheets[sheet_key]

            if sheet is None:
                return

            # Extract region or use full image
            if config.x is not None and config.y is not None:
                # Extract region from sprite sheet
                w = config.width or (sheet.get_width() - config.x)
                h = config.height or (sheet.get_height() - config.y)
                sprite = sheet.subsurface(pygame.Rect(config.x, config.y, w, h)).copy()
            else:
                # Use full image
                sprite = sheet.copy()

            # Apply transparency color key
            if config.transparent:
                sprite.set_colorkey(config.transparent)

            self._sprites[name] = sprite

        except Exception as e:
            print(f"[GameEngineSkin] Failed to load sprite '{name}': {e}")

    def _load_image_from_data_uri(self, data_uri: str) -> Optional[pygame.Surface]:
        """Load an image from a data URI (data:image/png;base64,...)."""
        import base64
        import io

        try:
            # Parse data URI: data:[<mediatype>][;base64],<data>
            if not data_uri.startswith('data:'):
                return None

            # Split header and data
            _, encoded = data_uri.split(',', 1)
            # Decode base64
            image_bytes = base64.b64decode(encoded)
            # Load from bytes
            return pygame.image.load(io.BytesIO(image_bytes)).convert()
        except Exception as e:
            print(f"[GameEngineSkin] Failed to load image from data URI: {e}")
            return None

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

        # Counters for generating unique inline names
        self._inline_behavior_counter = 0
        self._inline_collision_action_counter = 0

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

        # Register spawn callback so Lua spawns use entity type config
        self._behavior_engine.set_spawn_callback(self._lua_spawn_callback)

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

        # Spawn initial entities if no level loaded
        if not self._behavior_engine.entities:
            self._spawn_initial_entities()

    def _load_game_definition(self, path: Path) -> GameDefinition:
        """Load game definition from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        # Validate against schema (raises SchemaValidationError unless AMS_SKIP_SCHEMA_VALIDATION=1)
        validate_game_yaml(data, path)

        # Parse assets section
        assets_data = data.get('assets', {})
        files_config = assets_data.get('files', {})
        sounds_config = self._parse_sounds_config(assets_data.get('sounds', {}), files_config)
        sprites_config = self._parse_sprites_config(assets_data.get('sprites', {}), files_config)
        assets_config = AssetsConfig(
            files=files_config,
            sounds=sounds_config,
            sprites=sprites_config,
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
                    sprite_name=render_data.get('sprite', ''),
                    radius=render_data.get('radius'),
                    text=render_data.get('text', ''),
                    font_size=render_data.get('font_size', 20),
                    align=render_data.get('align', 'center'),
                    when=when_cond,
                ))

            # Parse lifecycle transforms
            on_destroy = None
            on_update = []
            if 'on_destroy' in type_data:
                on_destroy = self._parse_transform_config(type_data['on_destroy'])
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
                on_update=on_update,
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
        raw_input_mapping = data.get('input_mapping', {})
        for entity_type, mapping_data in raw_input_mapping.items():
            on_input = None
            if 'on_input' in mapping_data:
                on_input_data = mapping_data['on_input']
                transform_config = None
                when_condition = None

                # Parse transform
                if 'transform' in on_input_data:
                    transform_config = self._parse_transform_config(on_input_data['transform'])

                # Parse when condition
                if 'when' in on_input_data:
                    when_condition = self._parse_when_condition(on_input_data['when'])

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

    def _parse_behaviors(self, entity_type: str, behaviors_data: List[Any]) -> List[str]:
        """Parse behaviors list, handling both file references and inline Lua.

        Behaviors can be:
        - String: Reference to file in behaviors directory (e.g., "paddle")
        - Dict with 'lua' key: Inline Lua code

        Example YAML:
            behaviors:
              - paddle              # loads paddle.lua
              - lua: |
                  local b = {}
                  function b.on_update(id, dt)
                      ams.log("Custom behavior!")
                  end
                  return b

        Returns list of behavior names (inline behaviors get generated names).
        """
        behavior_names: List[str] = []

        for item in behaviors_data:
            if isinstance(item, str):
                # File-based behavior
                behavior_names.append(item)
            elif isinstance(item, dict) and 'lua' in item:
                # Inline Lua behavior
                lua_code = item['lua']
                name = f"_inline_{entity_type}_{self._inline_behavior_counter}"
                self._inline_behavior_counter += 1

                # Register inline behavior with engine
                if self._behavior_engine.load_inline_behavior(name, lua_code):
                    behavior_names.append(name)
                else:
                    print(f"[GameEngine] Failed to load inline behavior for {entity_type}")

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
                - dict with 'action.lua' key: Inline Lua

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

            # Inline Lua
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

                if self._behavior_engine.load_inline_collision_action(name, lua_code):
                    return name
                else:
                    print(f"[GameEngine] Failed to load inline collision action for {type_a}->{type_b}")
                    return ''

        return ''

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
        """
        result: Dict[str, SpriteConfig] = {}

        for name, sprite_data in sprites_data.items():
            if isinstance(sprite_data, str):
                # Simple path string, data URI, or @reference
                file_path, data_uri = self._resolve_file_reference(sprite_data, files)
                result[name] = SpriteConfig(file=file_path, data=data_uri)
            elif isinstance(sprite_data, dict):
                # Dict format with optional fields
                transparent = None
                if 'transparent' in sprite_data:
                    t = sprite_data['transparent']
                    if isinstance(t, (list, tuple)) and len(t) >= 3:
                        transparent = (int(t[0]), int(t[1]), int(t[2]))

                # Resolve file reference if present
                file_value = sprite_data.get('file', '')
                data_value = sprite_data.get('data')

                if file_value and file_value.startswith('@'):
                    file_path, data_uri = self._resolve_file_reference(file_value, files)
                else:
                    file_path = file_value
                    data_uri = data_value

                result[name] = SpriteConfig(
                    file=file_path,
                    data=data_uri,
                    transparent=transparent,
                    x=sprite_data.get('x'),
                    y=sprite_data.get('y'),
                    width=sprite_data.get('width'),
                    height=sprite_data.get('height'),
                )

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
                    if not config.on_update and base.on_update:
                        config.on_update = base.on_update.copy()

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

    def _apply_level_config(self, level_data: Any) -> None:
        """Apply level configuration - spawn entities from level data.

        Works with any level data conforming to GameEngineLevelData protocol:
        - name: str
        - lives: int
        - player_x, player_y: float
        - entities: List[EntityPlacement]

        Args:
            level_data: Parsed level data (should conform to GameEngineLevelData)
        """
        # Clear existing entities
        self._behavior_engine.clear()

        # Set level name for HUD
        self._level_name = getattr(level_data, 'name', 'Level')

        # Apply lives from level
        lives = getattr(level_data, 'lives', self._starting_lives)
        self._lives = lives
        self._starting_lives = lives

        # Spawn player entity at level-specified position
        if self._game_def and self._game_def.player_type:
            player_x = getattr(level_data, 'player_x', self._game_def.player_spawn[0])
            player_y = getattr(level_data, 'player_y', self._game_def.player_spawn[1])
            player = self.spawn_entity(
                self._game_def.player_type,
                x=player_x,
                y=player_y,
            )
            if player:
                self._player_id = player.id

        # Spawn entities from level
        entities = getattr(level_data, 'entities', [])
        for placement in entities:
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

    def _lua_spawn_callback(
        self, entity_type: str, x: float, y: float,
        vx: float, vy: float, width: float, height: float,
        color: str, sprite: str
    ) -> Optional[Entity]:
        """Callback for BehaviorEngine.spawn_entity to apply entity type config.

        Called when Lua code spawns entities (e.g., shoot behavior spawning projectiles).
        Applies entity type config from game.yaml so spawned entities have behaviors.
        """
        return self.spawn_entity(
            entity_type, x, y,
            vx=vx, vy=vy, width=width, height=height,
            color=color, sprite=sprite
        )

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
        if action.when and action.when.property:
            prop_value = entity.properties.get(action.when.property)
            if prop_value != action.when.value:
                # Condition not met, skip action
                return

        # Execute transform if configured
        if action.transform:
            self.apply_transform(entity, action.transform)

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

        # Check on_update transforms (age-based, property-based, interval)
        self._check_on_update_transforms()

        # Check collisions
        self._check_collisions()

        # Handle destroyed entities
        self._handle_destroyed_entities()

        # Update skin
        self._skin.update(dt)

        # Check win/lose conditions
        self._check_win_conditions()
        self._check_lose_conditions()

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

        Applies on_destroy transforms and scoring.
        """
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

        # Re-register with behavior engine for new behaviors
        self._behavior_engine.update_entity_behaviors(entity)

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

        Generator scripts live in ams/behaviors/generators/ and expose a
        generate(args) function that returns the computed value.
        """
        if isinstance(value, dict):
            if 'lua' in value:
                return self._behavior_engine.evaluate_expression(value['lua'])
            elif 'call' in value:
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
