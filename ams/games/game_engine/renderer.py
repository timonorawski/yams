"""Renderer for the YAML-driven game engine."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pygame

from ams.games.game_engine.entity import GameEntity
from ams.games.game_engine.config import (
    GameDefinition,
    RenderCommand,
    SoundConfig,
    SpriteConfig,
)


class GameEngineRenderer:
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

    def render_entity(self, entity: GameEntity, screen: pygame.Surface) -> None:
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

    def _render_commands(self, entity: GameEntity, commands: List[RenderCommand],
                         screen: pygame.Surface) -> None:
        """Render entity using a list of render commands."""
        for cmd in commands:
            # Check when condition (delegate to entity)
            if cmd.when and not entity.evaluate_when(cmd.when, self._elapsed_time):
                continue
            self._render_command(entity, cmd, screen)
            # Stop processing further commands if stop flag is set
            if cmd.stop:
                break

    def _render_command(self, entity: GameEntity, cmd: RenderCommand,
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
                                  w: int, h: int, entity: GameEntity) -> None:
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

    def _resolve_alpha(self, entity: GameEntity, alpha_value: Any) -> Optional[int]:
        """Resolve alpha value (int, $property, or {lua: expr}) to 0-255 range."""
        if alpha_value is None:
            return None

        if isinstance(alpha_value, (int, float)):
            return int(alpha_value * 255) if alpha_value <= 1 else int(alpha_value)

        if isinstance(alpha_value, str) and alpha_value.startswith('$'):
            # Delegate property resolution to entity
            prop_val = entity.resolve_property_ref(alpha_value, self._elapsed_time)
            if prop_val is not None:
                # Assume 0-1 range, convert to 0-255
                return int(float(prop_val) * 255)
            return None

        if isinstance(alpha_value, dict) and 'lua' in alpha_value:
            # Lua expression evaluation - needs behavior engine
            # For now, return None (not implemented without engine reference)
            return None

        return None

    def _resolve_text(self, entity: GameEntity, text_value: str) -> str:
        """Resolve text content ($property references)."""
        if not text_value:
            return ""
        # Delegate property resolution to entity
        val = entity.resolve_property_ref(text_value, self._elapsed_time)
        return str(val) if val is not None else ""

    def _render_sprite(self, entity: GameEntity, sprite_name: str,
                       screen: pygame.Surface, x: int, y: int, w: int, h: int) -> None:
        """Render a sprite from loaded assets."""
        if not sprite_name:
            # No sprite specified, fallback to colored rectangle
            color = self._parse_color(entity.color)
            pygame.draw.rect(screen, color, pygame.Rect(x, y, w, h))
            return

        # Resolve template placeholders like {frame} (delegate to entity)
        resolved_name = entity.resolve_sprite_template(sprite_name)

        # Check if sprite is loaded
        sprite = self._sprites.get(resolved_name)
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

    def _resolve_color(self, entity: GameEntity, color_ref) -> Tuple[int, int, int]:
        """Resolve color reference (e.g., $color) or direct color to RGB.

        Args:
            entity: Entity for property lookups
            color_ref: Color name string, RGB tuple/list, or $property reference
        """
        # Direct RGB tuple/list - parse immediately
        if isinstance(color_ref, (list, tuple)):
            return self._parse_color(color_ref)

        # Property reference (e.g., $color)
        if isinstance(color_ref, str) and color_ref.startswith('$'):
            prop_name = color_ref[1:]
            if prop_name == 'color':
                return self._parse_color(entity.color)
            # Could also look up entity.properties[prop_name]
            prop_val = entity.properties.get(prop_name, entity.color)
            return self._parse_color(prop_val)

        # Color name string
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
            print(f"[GameEngineRenderer] Failed to load sound '{name}': {e}")

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
            print(f"[GameEngineRenderer] Failed to load sound from data URI: {e}")
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
                    print(f"[GameEngineRenderer] Sprite file not found: {sprite_path}")
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

            # Apply flip transformations
            if config.flip_x or config.flip_y:
                sprite = pygame.transform.flip(sprite, config.flip_x, config.flip_y)
                # Re-apply colorkey after flip (transform may lose it)
                if config.transparent:
                    sprite.set_colorkey(config.transparent)

            self._sprites[name] = sprite

        except Exception as e:
            print(f"[GameEngineRenderer] Failed to load sprite '{name}': {e}")

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
            print(f"[GameEngineRenderer] Failed to load image from data URI: {e}")
            return None

    def _parse_color(self, color_value) -> Tuple[int, int, int]:
        """Parse color value to RGB tuple.

        Accepts:
        - RGB tuple/list: [255, 215, 0] or (255, 215, 0)
        - Color name string: 'red', 'blue', etc.
        """
        # Already a tuple or list of RGB values
        if isinstance(color_value, (list, tuple)):
            if len(color_value) >= 3:
                return (int(color_value[0]), int(color_value[1]), int(color_value[2]))
            return (255, 255, 255)

        # Color name string
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
        if isinstance(color_value, str):
            return colors.get(color_value.lower(), (255, 255, 255))
        return (255, 255, 255)
