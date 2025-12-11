"""Configuration dataclasses for game engine YAML definitions."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


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
    compare: str = "equals"  # equals, not_equals, greater_than, less_than, between
    min: Optional[float] = None  # For 'between': min <= value < max (value is max)


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
    stop: bool = False  # If true, stop processing further render commands after this one


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
    on_destroy: Optional[TransformConfig] = None  # Transform on destroy (explosions, death effects)
    on_parent_destroy: Optional[TransformConfig] = None  # Transform when parent entity is destroyed
    on_update: List[OnUpdateTransform] = field(default_factory=list)  # Conditional transforms


@dataclass
class InputAction:
    """Action to take on input for an entity type."""
    transform: Optional[TransformConfig] = None  # Transform on input
    when: Optional[WhenCondition] = None  # Condition for triggering
    action: Optional[str] = None  # Action name (e.g., "play_sound")
    action_args: Dict[str, Any] = field(default_factory=dict)  # Action arguments


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
    """Configuration for input mapping to an entity type.

    Modes:
    - target_x/target_y: Set properties from input position (e.g., paddle)
    - on_input: Action when any input occurs for this entity type
    - on_hit: Action when input position is INSIDE the entity (click-on-entity)
    """
    target_x: Optional[str] = None  # Property to set from input.position.x
    target_y: Optional[str] = None  # Property to set from input.position.y
    on_input: Optional[InputAction] = None  # Action to take on any input
    on_hit: Optional[InputAction] = None  # Action when input is inside entity bounds


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
    - Flip horizontally/vertically (flip_x, flip_y)
    """
    file: str = ""  # Path to image file (mutually exclusive with data)
    data: Optional[str] = None  # Data URI (data:image/png;base64,...)
    transparent: Optional[Tuple[int, int, int]] = None  # RGB color key
    # For sprite sheets:
    x: Optional[int] = None  # Region x offset
    y: Optional[int] = None  # Region y offset
    width: Optional[int] = None  # Region width (None = full image)
    height: Optional[int] = None  # Region height (None = full image)
    # Flip options:
    flip_x: bool = False  # Flip horizontally
    flip_y: bool = False  # Flip vertically


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

    # Global input action - fires on any input regardless of entity
    global_on_input: Optional[InputAction] = None

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
