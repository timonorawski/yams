"""Asset loading and management for the game engine."""

import base64
import hashlib
import io
from pathlib import Path
from typing import Dict, Optional

import pygame

from ams.games.game_engine.config import GameDefinition, SoundConfig, SpriteConfig


class AssetProvider:
    """Loads and provides access to game assets (sprites, sounds).

    Handles:
    - File paths and data URIs
    - Sprite sheet extraction and caching
    - Transparency color keys
    - Flip transformations
    """

    def __init__(self):
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._sprites: Dict[str, pygame.Surface] = {}
        self._sprite_sheets: Dict[str, pygame.Surface] = {}  # Cached full sheets
        self._assets_dir: Optional[Path] = None

    def load_from_definition(self, game_def: GameDefinition,
                             assets_dir: Optional[Path] = None) -> None:
        """Load all assets defined in a game definition.

        Args:
            game_def: Game definition containing asset configs
            assets_dir: Base directory for relative file paths
        """
        self._assets_dir = assets_dir
        self._load_sounds(game_def)
        self._load_sprites(game_def)

    def get_sprite(self, name: str) -> Optional[pygame.Surface]:
        """Get a loaded sprite by name."""
        return self._sprites.get(name)

    def play_sound(self, name: str) -> None:
        """Play a sound effect by name."""
        sound = self._sounds.get(name)
        if sound:
            sound.play()

    def has_sprite(self, name: str) -> bool:
        """Check if a sprite is loaded."""
        return name in self._sprites

    def has_sound(self, name: str) -> bool:
        """Check if a sound is loaded."""
        return name in self._sounds

    # --- Sound Loading ---

    def _load_sounds(self, game_def: GameDefinition) -> None:
        """Load all sounds from game definition."""
        self._sounds.clear()
        for name, config in game_def.assets.sounds.items():
            self._load_sound(name, config)

    def _load_sound(self, name: str, config: SoundConfig) -> None:
        """Load a single sound from config."""
        try:
            if config.data:
                sound = self._load_sound_from_data_uri(config.data)
                if sound:
                    self._sounds[name] = sound
            elif config.file:
                sound_path = Path(config.file)
                if not sound_path.is_absolute() and self._assets_dir:
                    sound_path = self._assets_dir / config.file

                if sound_path.exists():
                    self._sounds[name] = pygame.mixer.Sound(str(sound_path))
        except Exception as e:
            print(f"[AssetProvider] Failed to load sound '{name}': {e}")

    def _load_sound_from_data_uri(self, data_uri: str) -> Optional[pygame.mixer.Sound]:
        """Load a sound from a data URI (data:audio/wav;base64,...)."""
        try:
            if not data_uri.startswith('data:'):
                return None
            _, encoded = data_uri.split(',', 1)
            audio_bytes = base64.b64decode(encoded)
            return pygame.mixer.Sound(io.BytesIO(audio_bytes))
        except Exception as e:
            print(f"[AssetProvider] Failed to load sound from data URI: {e}")
            return None

    # --- Sprite Loading ---

    def _load_sprites(self, game_def: GameDefinition) -> None:
        """Load all sprites from game definition."""
        self._sprites.clear()
        self._sprite_sheets.clear()
        for name, config in game_def.assets.sprites.items():
            self._load_sprite(name, config)

    def _load_sprite(self, name: str, config: SpriteConfig) -> None:
        """Load a single sprite from config.

        Supports:
        - File paths or data URIs
        - Regions within sprite sheets (x, y, width, height)
        - Transparency via color key
        - Flip transformations
        """
        try:
            sheet: Optional[pygame.Surface] = None

            if config.data:
                # Data URI: use hash as cache key for deduplication
                sheet_key = f"data:{hashlib.md5(config.data.encode()).hexdigest()[:16]}"
                if sheet_key in self._sprite_sheets:
                    sheet = self._sprite_sheets[sheet_key]
                else:
                    sheet = self._load_image_from_data_uri(config.data)
                    if sheet:
                        self._sprite_sheets[sheet_key] = sheet
            elif config.file:
                sprite_path = Path(config.file)
                if not sprite_path.is_absolute() and self._assets_dir:
                    sprite_path = self._assets_dir / config.file

                if not sprite_path.exists():
                    print(f"[AssetProvider] Sprite file not found: {sprite_path}")
                    return

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
                w = config.width or (sheet.get_width() - config.x)
                h = config.height or (sheet.get_height() - config.y)
                sprite = sheet.subsurface(pygame.Rect(config.x, config.y, w, h)).copy()
            else:
                sprite = sheet.copy()

            # Apply transparency color key
            if config.transparent:
                sprite.set_colorkey(config.transparent)

            # Apply flip transformations
            if config.flip_x or config.flip_y:
                sprite = pygame.transform.flip(sprite, config.flip_x, config.flip_y)
                if config.transparent:
                    sprite.set_colorkey(config.transparent)

            self._sprites[name] = sprite

        except Exception as e:
            print(f"[AssetProvider] Failed to load sprite '{name}': {e}")

    def _load_image_from_data_uri(self, data_uri: str) -> Optional[pygame.Surface]:
        """Load an image from a data URI (data:image/png;base64,...)."""
        try:
            if not data_uri.startswith('data:'):
                return None
            _, encoded = data_uri.split(',', 1)
            image_bytes = base64.b64decode(encoded)
            return pygame.image.load(io.BytesIO(image_bytes)).convert()
        except Exception as e:
            print(f"[AssetProvider] Failed to load image from data URI: {e}")
            return None
