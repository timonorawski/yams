"""
Classic skin for DuckHunt - sprites and authentic sounds.

This skin renders targets using Duck Hunt sprites and plays
classic game sounds for the full experience.
"""

from pathlib import Path
from typing import Optional

import pygame

from ..duck_target import DuckTarget, DuckPhase
from ..sprites import DuckSprites, DuckDirection, get_duck_sprites
from .base import GameSkin


class ClassicSkin(GameSkin):
    """Renders targets using Duck Hunt sprites with authentic sounds."""

    NAME = "classic"
    DESCRIPTION = "Original Duck Hunt style with sprites and sounds"

    def __init__(self):
        """Initialize classic skin with sprites and sounds."""
        self._sprites: Optional[DuckSprites] = None
        self._hit_sound: Optional[pygame.mixer.Sound] = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization of sprites and sounds."""
        if self._initialized:
            return

        # Load sprites
        self._sprites = get_duck_sprites()

        # Load sounds
        self._load_sounds()
        self._initialized = True

    def _load_sounds(self) -> None:
        """Load sound effects."""
        assets_dir = Path(__file__).parent.parent.parent / "assets"

        # Hit/shot sound
        shot_path = assets_dir / "shot.ogg"
        if shot_path.exists():
            try:
                self._hit_sound = pygame.mixer.Sound(str(shot_path))
            except pygame.error:
                pass  # Sound loading failed, continue without

    def update(self, dt: float) -> None:
        """Update sprite animations.

        Args:
            dt: Delta time in seconds
        """
        self._ensure_initialized()
        if self._sprites:
            self._sprites.update(dt)

    def render_target(self, target: DuckTarget, screen: pygame.Surface) -> None:
        """Render target using sprites.

        Args:
            target: The DuckTarget to render
            screen: Pygame surface to draw on
        """
        self._ensure_initialized()

        if not self._sprites or not self._sprites.is_loaded:
            # Fallback to simple circle if sprites not available
            self._render_fallback(target, screen)
            return

        # Determine which direction sprite to use based on phase
        if target.phase == DuckPhase.HIT_PAUSE:
            direction = DuckDirection.HIT
        elif target.phase == DuckPhase.FALLING:
            direction = DuckDirection.FALLING
        else:
            # Flying - determine direction from velocity
            vx = target.data.velocity.x
            vy = target.data.velocity.y
            direction = self._sprites.get_direction_from_velocity(vx, vy)

        # Calculate scale based on target size vs sprite size
        sprite_width, sprite_height = self._sprites.sprite_size
        target_size = target.data.size
        scale = target_size / max(sprite_width, sprite_height)

        # Get the current animation frame
        frame = self._sprites.get_frame(target.color, direction, scale)

        if frame is None:
            self._render_fallback(target, screen)
            return

        # Position sprite centered on target position
        pos_x = int(target.data.position.x - frame.get_width() / 2)
        pos_y = int(target.data.position.y - frame.get_height() / 2)

        screen.blit(frame, (pos_x, pos_y))

    def _render_fallback(self, target: DuckTarget, screen: pygame.Surface) -> None:
        """Render simple circle as fallback.

        Args:
            target: The DuckTarget to render
            screen: Pygame surface to draw on
        """
        pos = (int(target.data.position.x), int(target.data.position.y))
        radius = int(target.data.size / 2)
        color = (255, 100, 100)  # Red
        pygame.draw.circle(screen, color, pos, radius)
        pygame.draw.circle(screen, (255, 255, 255), pos, radius, 2)

    def play_hit_sound(self) -> None:
        """Play shot sound effect."""
        self._ensure_initialized()
        if self._hit_sound:
            self._hit_sound.play()
