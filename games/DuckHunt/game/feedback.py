"""
Visual and audio feedback system for Duck Hunt game.

This module manages visual effects, score popups, and audio feedback that
provide immediate feedback to the player when they hit or miss targets.

Classes:
    FeedbackManager: Manages all active visual effects, score popups, and audio
"""

from typing import List, Optional, Dict
import pygame
import numpy as np

from models import (
    Vector2D,
    Color,
    VisualEffect,
    ScorePopup,
    EffectType,
)
import config


class FeedbackManager:
    """Manages visual and audio feedback effects for player actions.

    The FeedbackManager tracks all active visual effects (hits, misses,
    explosions) and score popups, updating their state each frame and
    rendering them to the screen. It also plays audio feedback for hits,
    misses, and combo milestones. Effects automatically fade out and
    are removed when they expire.

    Attributes:
        effects: List of active VisualEffect instances
        popups: List of active ScorePopup instances
        sounds: Dictionary of sound effects (hit, miss, combo)
        audio_enabled: Whether audio is enabled

    Examples:
        >>> manager = FeedbackManager()
        >>> manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)
        >>> manager.update(0.016)  # One frame at 60 FPS
        >>> len(manager.effects) > 0
        True
    """

    def __init__(self, audio_enabled: bool = True):
        """Initialize the FeedbackManager with empty effect lists and audio.

        Args:
            audio_enabled: Whether to enable audio feedback (default: True)
        """
        self.effects: List[VisualEffect] = []
        self.popups: List[ScorePopup] = []
        self.audio_enabled = audio_enabled and config.AUDIO_ENABLED
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}

        # Initialize audio
        if self.audio_enabled:
            self._init_audio()

    def _init_audio(self) -> None:
        """Initialize pygame mixer and generate placeholder sounds.

        Creates simple procedurally generated sounds for hit, miss,
        and combo effects using pygame.sndarray.
        """
        try:
            # Initialize mixer with specific settings for sound generation
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

            # Generate placeholder sounds
            self.sounds['hit'] = self._generate_hit_sound()
            self.sounds['miss'] = self._generate_miss_sound()
            self.sounds['combo'] = self._generate_combo_sound()

            # Set volumes based on config
            for sound in self.sounds.values():
                if sound is not None:
                    sound.set_volume(config.SFX_VOLUME * config.MASTER_VOLUME)

        except Exception as e:
            # If audio initialization fails, disable audio
            print(f"Warning: Audio initialization failed: {e}")
            self.audio_enabled = False
            self.sounds = {}

    def _generate_hit_sound(self) -> Optional[pygame.mixer.Sound]:
        """Generate a pleasant 'hit' sound effect.

        Creates a short, upward-sweeping tone that sounds satisfying.

        Returns:
            pygame.mixer.Sound or None if generation fails
        """
        try:
            sample_rate = 22050
            duration = 0.15  # 150ms
            num_samples = int(sample_rate * duration)

            # Generate a pleasant rising tone (C to E notes)
            frequency_start = 523.25  # C5
            frequency_end = 659.25    # E5

            # Create frequency sweep
            t = np.linspace(0, duration, num_samples, False)
            frequencies = np.linspace(frequency_start, frequency_end, num_samples)

            # Generate sine wave with frequency sweep
            phase = np.cumsum(2.0 * np.pi * frequencies / sample_rate)
            wave = np.sin(phase)

            # Apply envelope (fade in/out) for smoother sound
            envelope = np.ones(num_samples)
            fade_samples = int(num_samples * 0.1)
            envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
            envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
            wave *= envelope

            # Scale to 16-bit integer range
            wave = (wave * 32767 * 0.3).astype(np.int16)

            # Convert to stereo
            stereo_wave = np.column_stack((wave, wave))

            return pygame.sndarray.make_sound(stereo_wave)
        except Exception as e:
            print(f"Warning: Could not generate hit sound: {e}")
            return None

    def _generate_miss_sound(self) -> Optional[pygame.mixer.Sound]:
        """Generate a gentle 'miss' sound effect.

        Creates a short, descending tone that's not too harsh.

        Returns:
            pygame.mixer.Sound or None if generation fails
        """
        try:
            sample_rate = 22050
            duration = 0.1  # 100ms
            num_samples = int(sample_rate * duration)

            # Generate a gentle descending tone
            frequency_start = 392.00  # G4
            frequency_end = 293.66    # D4

            # Create frequency sweep
            t = np.linspace(0, duration, num_samples, False)
            frequencies = np.linspace(frequency_start, frequency_end, num_samples)

            # Generate sine wave with frequency sweep
            phase = np.cumsum(2.0 * np.pi * frequencies / sample_rate)
            wave = np.sin(phase)

            # Apply envelope for smoother sound
            envelope = np.ones(num_samples)
            fade_samples = int(num_samples * 0.2)
            envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
            wave *= envelope

            # Scale to 16-bit integer range (quieter than hit)
            wave = (wave * 32767 * 0.2).astype(np.int16)

            # Convert to stereo
            stereo_wave = np.column_stack((wave, wave))

            return pygame.sndarray.make_sound(stereo_wave)
        except Exception as e:
            print(f"Warning: Could not generate miss sound: {e}")
            return None

    def _generate_combo_sound(self) -> Optional[pygame.mixer.Sound]:
        """Generate an exciting 'combo milestone' sound effect.

        Creates a bright, celebratory tone sequence.

        Returns:
            pygame.mixer.Sound or None if generation fails
        """
        try:
            sample_rate = 22050
            duration = 0.3  # 300ms
            num_samples = int(sample_rate * duration)

            # Generate a bright arpeggio (C-E-G major chord)
            frequencies = [523.25, 659.25, 783.99]  # C5, E5, G5
            wave = np.zeros(num_samples)

            samples_per_note = num_samples // len(frequencies)
            for i, freq in enumerate(frequencies):
                start_idx = i * samples_per_note
                end_idx = start_idx + samples_per_note
                t = np.linspace(0, samples_per_note / sample_rate, samples_per_note, False)

                # Generate sine wave for this note
                note_wave = np.sin(2.0 * np.pi * freq * t)

                # Apply envelope
                envelope = np.ones(samples_per_note)
                fade_samples = int(samples_per_note * 0.1)
                envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
                envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
                note_wave *= envelope

                wave[start_idx:end_idx] = note_wave

            # Scale to 16-bit integer range
            wave = (wave * 32767 * 0.35).astype(np.int16)

            # Convert to stereo
            stereo_wave = np.column_stack((wave, wave))

            return pygame.sndarray.make_sound(stereo_wave)
        except Exception as e:
            print(f"Warning: Could not generate combo sound: {e}")
            return None

    def play_hit_sound(self) -> None:
        """Play the hit sound effect.

        Safe to call even if audio is disabled or sound generation failed.
        """
        if self.audio_enabled and self.sounds.get('hit') is not None:
            try:
                self.sounds['hit'].play()
            except Exception as e:
                print(f"Warning: Could not play hit sound: {e}")

    def play_miss_sound(self) -> None:
        """Play the miss sound effect.

        Safe to call even if audio is disabled or sound generation failed.
        """
        if self.audio_enabled and self.sounds.get('miss') is not None:
            try:
                self.sounds['miss'].play()
            except Exception as e:
                print(f"Warning: Could not play miss sound: {e}")

    def play_combo_sound(self) -> None:
        """Play the combo milestone sound effect.

        Safe to call even if audio is disabled or sound generation failed.
        Call this when the player reaches combo milestones (3x, 5x, 10x, etc.).
        """
        if self.audio_enabled and self.sounds.get('combo') is not None:
            try:
                self.sounds['combo'].play()
            except Exception as e:
                print(f"Warning: Could not play combo sound: {e}")

    def play_spawn_sound(self) -> None:
        """Play the target spawn sound effect.

        Safe to call even if audio is disabled or sound generation failed.
        Call this when a new target spawns to alert the player.
        """
        # For now, reuse the hit sound at lower volume as spawn indicator
        # TODO: Generate dedicated spawn sound (e.g., "quack" for ducks)
        if self.audio_enabled and self.sounds.get('hit') is not None:
            try:
                # Play hit sound at reduced volume as spawn cue
                self.sounds['hit'].set_volume(0.3)
                self.sounds['hit'].play()
                self.sounds['hit'].set_volume(1.0)  # Reset volume
            except Exception as e:
                print(f"Warning: Could not play spawn sound: {e}")

    def add_hit_effect(self, position: Vector2D, points: int) -> None:
        """Add a visual effect and score popup for a successful hit.

        Creates a green explosion effect and a floating score popup
        at the hit location, and plays the hit sound effect.

        Args:
            position: Position where the hit occurred
            points: Score value to display in the popup

        Examples:
            >>> manager = FeedbackManager()
            >>> manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)
            >>> len(manager.effects)
            1
            >>> len(manager.popups)
            1
        """
        # Play hit sound
        self.play_hit_sound()

        # Create green explosion effect
        hit_effect = VisualEffect(
            position=position,
            lifetime=0.0,
            max_lifetime=0.5,  # Half second explosion
            effect_type=EffectType.HIT,
            color=Color(r=0, g=255, b=0, a=255),  # Bright green
            size=40.0,
            velocity=Vector2D(x=0.0, y=0.0)
        )
        self.effects.append(hit_effect)

        # Create floating score popup
        popup = ScorePopup(
            position=position,
            value=points,
            lifetime=0.0,
            color=Color(r=255, g=215, b=0, a=255),  # Gold
            max_lifetime=1.0,  # One second float
            velocity=Vector2D(x=0.0, y=-50.0)  # Float upward
        )
        self.popups.append(popup)

    def add_miss_effect(self, position: Vector2D) -> None:
        """Add a visual effect for a missed shot.

        Creates a small red X or cross effect at the miss location
        and plays the miss sound effect.

        Args:
            position: Position where the miss occurred

        Examples:
            >>> manager = FeedbackManager()
            >>> manager.add_miss_effect(Vector2D(x=100.0, y=200.0))
            >>> len(manager.effects)
            1
            >>> manager.effects[0].effect_type == EffectType.MISS
            True
        """
        # Play miss sound
        self.play_miss_sound()

        # Create red miss effect
        miss_effect = VisualEffect(
            position=position,
            lifetime=0.0,
            max_lifetime=0.3,  # Quick fade
            effect_type=EffectType.MISS,
            color=Color(r=255, g=0, b=0, a=255),  # Bright red
            size=20.0,
            velocity=Vector2D(x=0.0, y=0.0)
        )
        self.effects.append(miss_effect)

    def update(self, dt: float) -> None:
        """Update all active effects, aging them and removing expired ones.

        Args:
            dt: Delta time in seconds since last update

        Examples:
            >>> manager = FeedbackManager()
            >>> manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)
            >>> manager.update(0.016)
            >>> manager.effects[0].lifetime > 0
            True
        """
        # Update effects and filter out dead ones
        updated_effects = []
        for effect in self.effects:
            # Create new effect with updated lifetime and position
            new_effect = VisualEffect(
                position=Vector2D(
                    x=effect.position.x + effect.velocity.x * dt,
                    y=effect.position.y + effect.velocity.y * dt
                ),
                lifetime=effect.lifetime + dt,
                max_lifetime=effect.max_lifetime,
                effect_type=effect.effect_type,
                color=effect.color,
                size=effect.size,
                velocity=effect.velocity
            )
            if new_effect.is_alive:
                updated_effects.append(new_effect)

        self.effects = updated_effects

        # Update popups and filter out dead ones
        updated_popups = []
        for popup in self.popups:
            # Create new popup with updated lifetime and position
            new_popup = ScorePopup(
                position=Vector2D(
                    x=popup.position.x + popup.velocity.x * dt,
                    y=popup.position.y + popup.velocity.y * dt
                ),
                value=popup.value,
                lifetime=popup.lifetime + dt,
                color=popup.color,
                max_lifetime=popup.max_lifetime,
                velocity=popup.velocity
            )
            if new_popup.is_alive:
                updated_popups.append(new_popup)

        self.popups = updated_popups

    def render(self, screen: pygame.Surface) -> None:
        """Render all active effects to the screen.

        Draws visual effects as circles and score popups as text,
        with appropriate alpha blending for fade effects.

        Args:
            screen: Pygame surface to render to

        Examples:
            >>> import pygame
            >>> pygame.init()
            >>> screen = pygame.display.set_mode((800, 600))
            >>> manager = FeedbackManager()
            >>> manager.add_hit_effect(Vector2D(x=400.0, y=300.0), points=100)
            >>> manager.render(screen)  # Draws effects to screen
        """
        # Render visual effects
        for effect in self.effects:
            # Create surface with per-pixel alpha for fade effect
            effect_surface = pygame.Surface(
                (int(effect.size * 2), int(effect.size * 2)),
                pygame.SRCALPHA
            )

            # Apply alpha to color
            effect_color = Color(
                r=effect.color.r,
                g=effect.color.g,
                b=effect.color.b,
                a=effect.alpha
            )

            if effect.effect_type == EffectType.HIT:
                # Draw expanding circle for hits
                radius = int(effect.size * (1.0 + effect.lifetime / effect.max_lifetime))
                pygame.draw.circle(
                    effect_surface,
                    effect_color.as_tuple,
                    (int(effect.size), int(effect.size)),
                    radius,
                    width=3  # Ring, not filled
                )
            elif effect.effect_type == EffectType.MISS:
                # Draw X for misses
                center = int(effect.size)
                offset = int(effect.size * 0.7)
                pygame.draw.line(
                    effect_surface,
                    effect_color.as_tuple,
                    (center - offset, center - offset),
                    (center + offset, center + offset),
                    width=3
                )
                pygame.draw.line(
                    effect_surface,
                    effect_color.as_tuple,
                    (center - offset, center + offset),
                    (center + offset, center - offset),
                    width=3
                )
            else:  # EXPLOSION or other
                # Draw filled circle for explosions
                pygame.draw.circle(
                    effect_surface,
                    effect_color.as_tuple,
                    (int(effect.size), int(effect.size)),
                    int(effect.size)
                )

            # Blit effect centered on position
            screen.blit(
                effect_surface,
                (effect.position.x - effect.size, effect.position.y - effect.size)
            )

        # Render score popups
        font = pygame.font.Font(None, 36)  # Default font, size 36
        for popup in self.popups:
            # Create text surface
            text_str = f"+{popup.value}" if popup.value >= 0 else str(popup.value)
            text_surface = font.render(text_str, True, popup.color.as_rgb_tuple)

            # Apply alpha by creating a copy with alpha
            text_with_alpha = text_surface.copy()
            text_with_alpha.set_alpha(popup.alpha)

            # Center text on position
            text_rect = text_with_alpha.get_rect()
            text_rect.center = (int(popup.position.x), int(popup.position.y))

            screen.blit(text_with_alpha, text_rect)

    def clear(self) -> None:
        """Remove all active effects and popups.

        Examples:
            >>> manager = FeedbackManager()
            >>> manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)
            >>> manager.clear()
            >>> len(manager.effects)
            0
            >>> len(manager.popups)
            0
        """
        self.effects = []
        self.popups = []

    def get_active_count(self) -> int:
        """Get total count of active effects and popups.

        Returns:
            Sum of active effects and popups

        Examples:
            >>> manager = FeedbackManager()
            >>> manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)
            >>> manager.get_active_count()
            2
        """
        return len(self.effects) + len(self.popups)
