"""
Balloon Pop game mode.

Players pop balloons as they float up from the bottom of the screen.
Game ends when too many balloons escape off the top.
"""

import time
from typing import List, Optional
import pygame

from games.common import GameState
from games.BalloonPop.balloon import Balloon, BalloonState
from games.BalloonPop.input.input_event import InputEvent
from games.BalloonPop.config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    SPAWN_RATE,
    MAX_ESCAPED,
    TARGET_POPS,
    BACKGROUND_COLOR,
    AUDIO_ENABLED,
    PACING_PRESETS,
    PacingPreset,
)
from games.common.palette import GamePalette
from games.common.quiver import QuiverState, create_quiver


class PopEffect:
    """Visual effect when a balloon is popped."""

    def __init__(self, x: float, y: float, color: tuple, size: float):
        self.x = x
        self.y = y
        self.color = color
        self.max_radius = size
        self.lifetime = 0.3  # seconds
        self.elapsed = 0.0

    def update(self, dt: float) -> bool:
        """Update effect. Returns False when effect is done."""
        self.elapsed += dt
        return self.elapsed < self.lifetime

    def render(self, screen: pygame.Surface) -> None:
        """Render the pop effect."""
        progress = self.elapsed / self.lifetime
        radius = int(self.max_radius * (0.5 + progress * 0.5))
        alpha = int(255 * (1 - progress))

        # Create surface with alpha
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        color_with_alpha = (*self.color, alpha)
        pygame.draw.circle(surf, color_with_alpha, (radius, radius), radius, 3)
        screen.blit(surf, (int(self.x - radius), int(self.y - radius)))


class BalloonPopMode:
    """
    Balloon Pop game mode.

    Balloons spawn at the bottom and float upward. Pop them before they escape!
    """

    def __init__(
        self,
        max_escaped: int = MAX_ESCAPED,
        target_pops: int = TARGET_POPS,
        spawn_rate: float = None,
        audio_enabled: bool = AUDIO_ENABLED,
        pacing: str = 'throwing',
        quiver_size: int = None,
        retrieval_pause: float = None,
        color_palette: str = None,
    ):
        """
        Initialize game mode.

        Args:
            max_escaped: Number of escaped balloons before game over (0 = unlimited)
            target_pops: Number of pops to win (0 = endless)
            spawn_rate: Seconds between balloon spawns (overrides pacing preset)
            audio_enabled: Whether to play sounds
            pacing: Pacing preset name (archery/throwing/blaster)
            quiver_size: Shots per round (None = unlimited)
            retrieval_pause: Seconds for retrieval (0 = manual ready)
            color_palette: Test palette name (or None for default)
        """
        # Apply pacing preset
        preset = PACING_PRESETS.get(pacing, PACING_PRESETS['throwing'])
        self._preset = preset

        self._balloons: List[Balloon] = []
        self._effects: List[PopEffect] = []
        self._state = GameState.PLAYING
        self._max_escaped = max_escaped
        self._target_pops = target_pops

        # Use spawn_rate if provided, otherwise use preset
        self._spawn_rate = spawn_rate if spawn_rate is not None else preset.spawn_interval
        self._spawn_timer = 0.0
        self._audio_enabled = audio_enabled

        # Pacing-driven parameters
        self._balloon_size_min = preset.balloon_size_min
        self._balloon_size_max = preset.balloon_size_max
        self._float_speed_min = preset.float_speed_min
        self._float_speed_max = preset.float_speed_max
        self._max_balloons = preset.max_balloons

        # Color palette
        self._palette = GamePalette(palette_name=color_palette)

        # Quiver state
        self._quiver: Optional[QuiverState] = create_quiver(quiver_size, retrieval_pause)

        # Stats
        self._pops = 0
        self._escaped = 0
        self._combo = 0
        self._max_combo = 0

        # Fonts (initialized lazily)
        self._font: Optional[pygame.font.Font] = None
        self._font_large: Optional[pygame.font.Font] = None

        # Sounds
        self._pop_sound: Optional[pygame.mixer.Sound] = None
        self._init_audio()

    def _init_audio(self) -> None:
        """Initialize audio (create simple pop sound)."""
        if not self._audio_enabled:
            return

        try:
            pygame.mixer.init()
            # Create a simple pop sound programmatically
            # (In production, load from file)
        except Exception:
            self._audio_enabled = False

    def _get_font(self) -> pygame.font.Font:
        """Get or create font."""
        if self._font is None:
            self._font = pygame.font.Font(None, 36)
        return self._font

    def _get_font_large(self) -> pygame.font.Font:
        """Get or create large font."""
        if self._font_large is None:
            self._font_large = pygame.font.Font(None, 72)
        return self._font_large

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def balloons(self) -> List[Balloon]:
        return self._balloons

    def get_score(self) -> int:
        return self._pops

    def set_palette(self, palette_name: str) -> bool:
        """
        Change the color palette.

        Args:
            palette_name: Name of test palette

        Returns:
            True if palette found and changed
        """
        return self._palette.set_palette(palette_name)

    def ready_for_next_round(self) -> None:
        """Signal ready for next round (manual retrieval mode)."""
        if self._state == GameState.RETRIEVAL and self._quiver:
            self._quiver.end_retrieval()
            self._state = GameState.PLAYING

    def update(self, dt: float) -> None:
        """
        Update game logic.

        Args:
            dt: Delta time in seconds
        """
        # Handle retrieval state
        if self._state == GameState.RETRIEVAL:
            if self._quiver and not self._quiver.is_manual_retrieval:
                if self._quiver.update_retrieval(dt):
                    self._quiver.end_retrieval()
                    self._state = GameState.PLAYING
            return

        if self._state != GameState.PLAYING:
            return

        # Update spawn timer (only spawn if under max limit)
        self._spawn_timer -= dt
        if self._spawn_timer <= 0 and len(self._balloons) < self._max_balloons:
            self._spawn_balloon()
            self._spawn_timer = self._spawn_rate

        # Update balloons
        updated_balloons = []
        for balloon in self._balloons:
            if balloon.state == BalloonState.POPPED:
                # Remove popped balloons after brief delay
                continue
            elif balloon.is_escaped():
                self._escaped += 1
                self._combo = 0  # Break combo
                continue
            else:
                updated_balloons.append(balloon.update(dt))

        self._balloons = updated_balloons

        # Update effects
        self._effects = [e for e in self._effects if e.update(dt)]

        # Check win/lose conditions
        self._check_game_over()

    def handle_input(self, events: List[InputEvent]) -> None:
        """
        Process input events.

        Args:
            events: List of input events
        """
        if self._state != GameState.PLAYING:
            return

        for event in events:
            # Check quiver before allowing shot
            if self._quiver and self._quiver.is_empty:
                continue

            hit = False

            # Check all balloons for hit (check from front to back)
            for i, balloon in enumerate(self._balloons):
                if balloon.is_active and balloon.contains_point(
                    event.position.x, event.position.y
                ):
                    # Pop this balloon
                    self._balloons[i] = balloon.pop()
                    self._pops += 1
                    self._combo += 1
                    self._max_combo = max(self._max_combo, self._combo)

                    # Add pop effect
                    self._effects.append(PopEffect(
                        balloon.x, balloon.y, balloon.color, balloon.size
                    ))

                    hit = True
                    break  # Only pop one balloon per click

            if not hit:
                # Missed - break combo
                self._combo = 0

            # Use shot from quiver
            if self._quiver:
                is_empty = self._quiver.use_shot()
                if is_empty:
                    self._quiver.start_retrieval()
                    self._state = GameState.RETRIEVAL

    def render(self, screen: pygame.Surface) -> None:
        """
        Render the game.

        Args:
            screen: Pygame surface to draw on
        """
        # Background
        screen.fill(BACKGROUND_COLOR)

        # Draw balloons
        for balloon in self._balloons:
            balloon.render(screen)

        # Draw effects
        for effect in self._effects:
            effect.render(screen)

        # Draw UI
        self._render_ui(screen)

        # Draw retrieval screen
        if self._state == GameState.RETRIEVAL:
            self._render_retrieval(screen)
        # Draw game over
        elif self._state == GameState.GAME_OVER:
            self._render_game_over(screen)
        elif self._state == GameState.WON:
            self._render_win(screen)

    def _render_ui(self, screen: pygame.Surface) -> None:
        """Render UI elements."""
        font = self._get_font()

        # Score
        score_text = font.render(f"Pops: {self._pops}", True, (255, 255, 255))
        screen.blit(score_text, (10, 10))

        # Combo
        if self._combo > 1:
            combo_text = font.render(f"Combo: {self._combo}x", True, (255, 255, 0))
            screen.blit(combo_text, (10, 50))

        # Quiver count
        if self._quiver:
            quiver_text = font.render(
                self._quiver.get_display_text(),
                True,
                (255, 100, 100) if self._quiver.remaining <= 2 else (255, 255, 255)
            )
            screen.blit(quiver_text, (10, 90))

        # Escaped counter
        if self._max_escaped > 0:
            escaped_text = font.render(
                f"Escaped: {self._escaped}/{self._max_escaped}",
                True,
                (255, 100, 100) if self._escaped > self._max_escaped * 0.7 else (255, 255, 255)
            )
            screen.blit(escaped_text, (SCREEN_WIDTH - 200, 10))

        # Target progress
        if self._target_pops > 0:
            progress_text = font.render(
                f"Goal: {self._pops}/{self._target_pops}",
                True,
                (100, 255, 100)
            )
            screen.blit(progress_text, (SCREEN_WIDTH - 200, 50))

        # Palette indicator (bottom left)
        palette_text = font.render(
            f"Palette: {self._palette.name}",
            True,
            (200, 200, 200)
        )
        screen.blit(palette_text, (10, SCREEN_HEIGHT - 40))

    def _render_retrieval(self, screen: pygame.Surface) -> None:
        """Render retrieval screen."""
        if not self._quiver:
            return

        font_large = self._get_font_large()
        font_small = self._get_font()

        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        screen.blit(overlay, (0, 0))

        # Retrieval text
        title_text = font_large.render("RETRIEVAL", True, (255, 200, 0))
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80))
        screen.blit(title_text, title_rect)

        # Instructions
        instruction_text = font_small.render(
            self._quiver.get_retrieval_text(),
            True,
            (255, 255, 255)
        )
        instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(instruction_text, instruction_rect)

        # Round info
        round_text = font_small.render(
            f"Round {self._quiver.current_round} | Total shots: {self._quiver.total_shots}",
            True,
            (200, 200, 200)
        )
        round_rect = round_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40))
        screen.blit(round_text, round_rect)

    def _render_game_over(self, screen: pygame.Surface) -> None:
        """Render game over screen."""
        font = self._get_font_large()

        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        screen.blit(overlay, (0, 0))

        # Game over text
        text = font.render("GAME OVER", True, (255, 0, 0))
        text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(text, text_rect)

        # Final score
        font_small = self._get_font()
        score_text = font_small.render(f"Final Score: {self._pops}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        screen.blit(score_text, score_rect)

        # Max combo
        combo_text = font_small.render(f"Max Combo: {self._max_combo}", True, (255, 255, 0))
        combo_rect = combo_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
        screen.blit(combo_text, combo_rect)

    def _render_win(self, screen: pygame.Surface) -> None:
        """Render win screen."""
        font = self._get_font_large()

        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        screen.blit(overlay, (0, 0))

        # Win text
        text = font.render("YOU WIN!", True, (0, 255, 0))
        text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(text, text_rect)

        # Final stats
        font_small = self._get_font()
        stats_text = font_small.render(
            f"Popped {self._pops} balloons | Max Combo: {self._max_combo}",
            True,
            (255, 255, 255)
        )
        stats_rect = stats_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        screen.blit(stats_text, stats_rect)

    def _spawn_balloon(self) -> None:
        """Spawn a new balloon at the bottom of the screen."""
        color = self._palette.random_target_color()
        balloon = Balloon(
            color=color,
            size_range=(self._balloon_size_min, self._balloon_size_max),
            speed_range=(self._float_speed_min, self._float_speed_max)
        )
        self._balloons.append(balloon)

    def _check_game_over(self) -> None:
        """Check win/lose conditions."""
        # Lose: too many escaped
        if self._max_escaped > 0 and self._escaped >= self._max_escaped:
            self._state = GameState.GAME_OVER
            return

        # Win: reached target pops
        if self._target_pops > 0 and self._pops >= self._target_pops:
            self._state = GameState.WON
            return
