"""Asset registry for discovering and loading asset definitions from YAML files.

Scans the assets/ directory tree for YAML registration files that match the
assets.schema.json format and converts them to engine config objects.

This enables games to:
- Define sprites/sounds in separate files with metadata and provenance
- Reference assets by name without inline definitions in game.yaml
- Share assets across multiple entity types cleanly

Usage:
    registry = AssetRegistry(content_fs, game_dir / 'assets')
    registry.discover('assets/')

    # Merge with inline definitions (inline takes precedence)
    merged_sprites = registry.merge_sprites(inline_sprites)
    merged_sounds = registry.merge_sounds(inline_sounds)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, TYPE_CHECKING, Tuple

import yaml

from ams.games.game_engine.config import SpriteConfig, SoundConfig

if TYPE_CHECKING:
    from ams.content_fs import ContentFS


@dataclass
class ImageAsset:
    """Raw image asset metadata (not a sprite - used for backgrounds, etc.)."""
    name: str
    file: str = ""
    data: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    provenance: Optional[Dict[str, Any]] = None


@dataclass
class RegisteredAssets:
    """Collection of assets discovered from registry files."""
    sprites: Dict[str, SpriteConfig] = field(default_factory=dict)
    sounds: Dict[str, SoundConfig] = field(default_factory=dict)
    images: Dict[str, ImageAsset] = field(default_factory=dict)


class AssetRegistry:
    """Discovers and loads asset definitions from YAML registration files.

    Scans the assets/ directory tree for *.yaml files that define sprites,
    sounds, or images and converts them to engine config objects.

    Supports multiple registration patterns:
    - Individual files: assets/sprites/player.yaml → sprite named "player"
    - Flat files: assets/shot.yaml → sound named "shot"
    - Sprite sheets: assets/sprites.yaml with sprites: map → multiple sprites
    """

    def __init__(
        self,
        content_fs: Optional['ContentFS'] = None,
        assets_base_dir: Optional[Path] = None
    ):
        """Initialize registry.

        Args:
            content_fs: ContentFS for layered file access (optional)
            assets_base_dir: Base directory for resolving relative paths
        """
        self._content_fs = content_fs
        self._assets_base_dir = assets_base_dir or Path('.')
        self._registered = RegisteredAssets()
        self._extends_map: Dict[str, str] = {}  # sprite_name -> extends_name

    def discover(self, assets_path: str = 'assets/') -> None:
        """Discover asset registration files in assets/ directory tree.

        Scans for *.yaml files and parses those that match the asset schema.
        Files can be at any depth:
        - assets/sprites.yaml (single file with name field, or sprite sheet)
        - assets/sprites/player.yaml (individual sprite)
        - assets/sounds/explosion.yaml

        Args:
            assets_path: Virtual path to assets directory
        """
        if self._content_fs:
            self._discover_via_content_fs(assets_path)
        elif self._assets_base_dir.exists():
            self._discover_via_filesystem(self._assets_base_dir)

        # Resolve sprite inheritance after all sprites are registered
        self._resolve_sprite_inheritance()

    def _discover_via_content_fs(self, assets_path: str) -> None:
        """Discover using ContentFS (supports layered filesystems)."""
        if not self._content_fs.exists(assets_path):
            return

        # Walk all YAML files in assets/
        try:
            for yaml_path in self._content_fs.walk_files(assets_path, filter_glob=['*.yaml']):
                self._process_registration_file_content_fs(yaml_path)
        except Exception as e:
            print(f"[AssetRegistry] Error walking {assets_path}: {e}")

    def _discover_via_filesystem(self, assets_dir: Path) -> None:
        """Discover using direct filesystem access."""
        if not assets_dir.exists():
            return

        for yaml_path in assets_dir.rglob('*.yaml'):
            self._process_registration_file_filesystem(yaml_path, assets_dir)

    def _process_registration_file_content_fs(self, yaml_path: str) -> None:
        """Process a single registration YAML file via ContentFS."""
        try:
            content = self._content_fs.readtext(yaml_path)
            data = yaml.safe_load(content)

            if not data or not isinstance(data, dict):
                return

            # Determine asset type and register
            asset_type = self._detect_asset_type(data, yaml_path)
            if asset_type == 'sprite':
                self._register_sprite(data, yaml_path)
            elif asset_type == 'sound':
                self._register_sound(data, yaml_path)
            elif asset_type == 'image':
                self._register_image(data, yaml_path)

        except Exception as e:
            print(f"[AssetRegistry] Failed to process {yaml_path}: {e}")

    def _process_registration_file_filesystem(self, yaml_path: Path, assets_dir: Path) -> None:
        """Process a single registration YAML file via filesystem."""
        try:
            content = yaml_path.read_text()
            data = yaml.safe_load(content)

            if not data or not isinstance(data, dict):
                return

            # Convert to virtual path for detection
            rel_path = str(yaml_path.relative_to(assets_dir.parent))

            # Determine asset type and register
            asset_type = self._detect_asset_type(data, rel_path)
            if asset_type == 'sprite':
                self._register_sprite(data, rel_path)
            elif asset_type == 'sound':
                self._register_sound(data, rel_path)
            elif asset_type == 'image':
                self._register_image(data, rel_path)

        except Exception as e:
            print(f"[AssetRegistry] Failed to process {yaml_path}: {e}")

    def _detect_asset_type(self, data: Dict[str, Any], yaml_path: str) -> Optional[str]:
        """Detect asset type from file content or path.

        Priority:
        1. Path-based detection (sprites/, sounds/, images/)
        2. Content-based detection (x/y/frames → sprite, volume/loop → sound)
        3. File extension heuristic
        """
        path_lower = yaml_path.lower()

        # Path-based detection
        if '/sprites/' in path_lower or path_lower.endswith('/sprites.yaml'):
            return 'sprite'
        if '/sounds/' in path_lower:
            return 'sound'
        if '/images/' in path_lower:
            return 'image'

        # Content-based detection
        sprite_keys = {'x', 'y', 'width', 'height', 'frames', 'flip_x', 'flip_y', 'transparent', 'extends', 'sprites'}
        sound_keys = {'volume', 'loop', 'pitch', 'variants', 'spatial'}

        data_keys = set(data.keys())

        if data_keys & sprite_keys:
            return 'sprite'
        if data_keys & sound_keys:
            return 'sound'

        # File extension heuristic
        file_ref = data.get('file', '')
        if file_ref:
            ext = Path(file_ref).suffix.lower()
            if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
                # Could be sprite or image - check for sprite-specific fields
                if data_keys & {'x', 'y', 'width', 'height', 'transparent'}:
                    return 'sprite'
                return 'image'
            if ext in ['.wav', '.mp3', '.ogg', '.flac']:
                return 'sound'

        return None

    def _register_sprite(self, data: Dict[str, Any], yaml_path: str) -> None:
        """Register sprite(s) from YAML data.

        Handles both individual sprites and sprite sheets with multiple regions.
        """
        # Check if this is a sprite sheet with multiple sprites defined
        if 'sprites' in data and isinstance(data['sprites'], dict):
            # Sprite sheet with embedded sprite definitions
            base_file = data.get('file', '')
            base_data = data.get('data')
            base_transparent = self._parse_transparent(data.get('transparent'))

            for sprite_name, sprite_data in data['sprites'].items():
                if not isinstance(sprite_data, dict):
                    continue

                config = SpriteConfig(
                    file=sprite_data.get('file', base_file),
                    data=sprite_data.get('data', base_data),
                    transparent=self._parse_transparent(sprite_data.get('transparent')) or base_transparent,
                    x=sprite_data.get('x'),
                    y=sprite_data.get('y'),
                    width=sprite_data.get('width'),
                    height=sprite_data.get('height'),
                    flip_x=sprite_data.get('flip_x', False),
                    flip_y=sprite_data.get('flip_y', False),
                )
                self._registered.sprites[sprite_name] = config

                # Track extends for later resolution
                if 'extends' in sprite_data:
                    self._extends_map[sprite_name] = sprite_data['extends']
        else:
            # Single sprite definition
            name = data.get('name') or Path(yaml_path).stem

            config = SpriteConfig(
                file=data.get('file', ''),
                data=data.get('data'),
                transparent=self._parse_transparent(data.get('transparent')),
                x=data.get('x'),
                y=data.get('y'),
                width=data.get('width'),
                height=data.get('height'),
                flip_x=data.get('flip_x', False),
                flip_y=data.get('flip_y', False),
            )
            self._registered.sprites[name] = config

            # Track extends for later resolution
            if 'extends' in data:
                self._extends_map[name] = data['extends']

    def _register_sound(self, data: Dict[str, Any], yaml_path: str) -> None:
        """Register a sound from YAML data."""
        name = data.get('name') or Path(yaml_path).stem

        config = SoundConfig(
            file=data.get('file', ''),
            data=data.get('data'),
        )

        self._registered.sounds[name] = config

    def _register_image(self, data: Dict[str, Any], yaml_path: str) -> None:
        """Register a raw image asset."""
        name = data.get('name') or Path(yaml_path).stem

        asset = ImageAsset(
            name=name,
            file=data.get('file', ''),
            data=data.get('data'),
            width=data.get('width'),
            height=data.get('height'),
            tags=data.get('tags', []),
            provenance=data.get('provenance'),
        )

        self._registered.images[name] = asset

    def _parse_transparent(self, value: Any) -> Optional[Tuple[int, int, int]]:
        """Parse transparent color value to RGB tuple."""
        if value is None:
            return None
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            return (int(value[0]), int(value[1]), int(value[2]))
        return None

    def _resolve_sprite_inheritance(self) -> None:
        """Resolve 'extends' inheritance within registered sprites.

        Sprites can extend other sprites to inherit file, transparent, etc.
        """
        resolved: set = set()

        def resolve(name: str, visited: set) -> None:
            if name in resolved:
                return
            if name not in self._registered.sprites:
                return
            if name in visited:
                print(f"[AssetRegistry] Circular sprite inheritance: {name}")
                return

            visited = visited | {name}
            sprite = self._registered.sprites[name]

            extends = self._extends_map.get(name)
            if extends:
                # Resolve base first
                resolve(extends, visited)

                if extends in self._registered.sprites:
                    base = self._registered.sprites[extends]

                    # Inherit unset fields from base
                    if not sprite.file and not sprite.data:
                        sprite.file = base.file
                        sprite.data = base.data
                    if sprite.transparent is None:
                        sprite.transparent = base.transparent
                    # x/y/width/height are typically overridden, not inherited
                    # unless they're explicitly None
                    if sprite.x is None and base.x is not None:
                        sprite.x = base.x
                    if sprite.y is None and base.y is not None:
                        sprite.y = base.y
                    if sprite.width is None and base.width is not None:
                        sprite.width = base.width
                    if sprite.height is None and base.height is not None:
                        sprite.height = base.height

            resolved.add(name)

        for name in list(self._registered.sprites.keys()):
            resolve(name, set())

    def get_registered_assets(self) -> RegisteredAssets:
        """Get all discovered and resolved assets."""
        return self._registered

    def get_sprites(self) -> Dict[str, SpriteConfig]:
        """Get all registered sprites."""
        return self._registered.sprites

    def get_sounds(self) -> Dict[str, SoundConfig]:
        """Get all registered sounds."""
        return self._registered.sounds

    def get_images(self) -> Dict[str, ImageAsset]:
        """Get all registered images."""
        return self._registered.images

    def merge_sprites(self, inline_sprites: Dict[str, SpriteConfig]) -> Dict[str, SpriteConfig]:
        """Merge registered sprites with inline definitions.

        Inline definitions take precedence over registered.

        Args:
            inline_sprites: Sprites from game.yaml assets.sprites

        Returns:
            Merged sprite configs (registered + inline, inline wins conflicts)
        """
        merged = dict(self._registered.sprites)
        merged.update(inline_sprites)  # Inline takes precedence
        return merged

    def merge_sounds(self, inline_sounds: Dict[str, SoundConfig]) -> Dict[str, SoundConfig]:
        """Merge registered sounds with inline definitions.

        Inline definitions take precedence over registered.

        Args:
            inline_sounds: Sounds from game.yaml assets.sounds

        Returns:
            Merged sound configs (registered + inline, inline wins conflicts)
        """
        merged = dict(self._registered.sounds)
        merged.update(inline_sounds)
        return merged
