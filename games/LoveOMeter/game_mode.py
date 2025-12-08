"""
LoveOMeter - Carnival Rate Challenge Game Mode.

Hit the target repeatedly to fill a thermometer that's constantly draining.
Pure speed vs. accuracy under escalating pressure.
"""
import time
from typing import List, Optional

import pygame

from games.common import GameState
from games.common.base_game import BaseGame
from games.common.input import InputEvent
from games.LoveOMeter import config
from games.LoveOMeter.target import Target
from games.LoveOMeter.meter import Meter


class LoveOMeterMode(BaseGame):
    """
    Love-O-Meter game mode.

    Core mechanic: Hit the target to fill the meter, which constantly drains.
    The difficulty escalates: drain increases, target shrinks and moves faster.

    The game engineers a state where conscious aiming can't keep up -
    the body must learn to solve the problem instinctively.

    Game modes:
    - sprint: Fill meter completely to win
    - endurance: Keep meter above threshold as long as possible
    - pressure: Drain increases until inevitable failure
    - adaptive: Difficulty responds to performance
    """

    # Game metadata
    NAME = "Love-O-Meter"
    DESCRIPTION = "Fill the meter by hitting the target - but it's constantly draining!"
    VERSION = "1.0.0"
    AUTHOR = "AMS Team"

    # CLI arguments
    ARGUMENTS = [
        {
            'name': '--mode',
            'type': str,
            'default': 'adaptive',
            'choices': ['sprint', 'endurance', 'pressure', 'adaptive'],
            'help': 'Game mode (sprint=fill to win, endurance=survive, pressure=escalating, adaptive=responsive)'
        },
        {
            'name': '--pacing',
            'type': str,
            'default': 'throwing',
            'choices': ['archery', 'throwing', 'blaster'],
            'help': 'Device speed preset (archery=slow, throwing=medium, blaster=fast)'
        },
        {
            'name': '--movement',
            'type': str,
            'default': 'drift',
            'choices': ['drift', 'orbit', 'random', 'bounce', 'static'],
            'help': 'Target movement pattern'
        },
        {
            'name': '--drain-rate',
            'type': float,
            'default': None,
            'help': 'Override drain rate (per second)'
        },
        {
            'name': '--target-size',
            'type': int,
            'default': None,
            'help': 'Override initial target size'
        },
        {
            'name': '--no-shrink',
            'action': 'store_true',
            'default': False,
            'help': 'Disable target shrinking'
        },
    ]

    def __init__(
        self,
        mode: str = 'adaptive',
        pacing: str = 'throwing',
        movement: str = 'drift',
        drain_rate: Optional[float] = None,
        target_size: Optional[int] = None,
        no_shrink: bool = False,
        **kwargs,
    ):
        """
        Initialize Love-O-Meter game.

        Args:
            mode: Game mode (sprint/endurance/pressure/adaptive)
            pacing: Pacing preset for input device
            movement: Target movement pattern
            drain_rate: Override for drain rate
            target_size: Override for target size
            no_shrink: Disable target shrinking
            **kwargs: Base game args (palette, quiver_size, etc.)
        """
        super().__init__(**kwargs)

        # Get pacing preset
        preset = config.PACING_PRESETS.get(pacing, config.PACING_PRESETS['throwing'])

        # Store config
        self._game_mode = mode
        self._pacing = pacing
        self._movement = movement if movement != 'static' else None

        # Initialize meter
        self._meter = Meter(
            initial_fill=preset.initial_fill,
            drain_rate=drain_rate if drain_rate is not None else preset.drain_rate,
            fill_per_hit=preset.fill_per_hit,
        )

        # Initialize target
        self._target = Target(
            screen_width=config.SCREEN_WIDTH,
            screen_height=config.SCREEN_HEIGHT,
            initial_size=target_size if target_size is not None else preset.target_size,
            min_size=preset.target_min_size,
            shrink_rate=0 if no_shrink else preset.shrink_rate,
            movement_pattern=movement if movement != 'static' else config.MOVEMENT_DRIFT,
            movement_speed=preset.movement_speed if movement != 'static' else 0,
        )

        # Difficulty scaling
        self._base_drain_rate = drain_rate if drain_rate is not None else preset.drain_rate
        self._drain_increase_rate = preset.drain_increase_rate
        self._shrink_increase_rate = preset.shrink_increase_rate
        self._current_drain_rate = self._base_drain_rate
        self._current_shrink_rate = 0 if no_shrink else preset.shrink_rate

        # Game state
        self._internal_state = GameState.PLAYING
        self._time_survived = 0.0
        self._hits = 0
        self._misses = 0
        self._best_streak = 0
        self._current_streak = 0

        # Adaptive difficulty tracking
        self._recent_hit_times: List[float] = []
        self._adaptive_window = 5.0  # seconds to consider for adaptation

        # Fonts
        self._font: Optional[pygame.font.Font] = None
        self._font_large: Optional[pygame.font.Font] = None

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

    def _get_internal_state(self) -> GameState:
        """Return current internal game state."""
        return self._internal_state

    def get_score(self) -> int:
        """Return current score (hits)."""
        return self._hits

    def ready_for_next_round(self) -> None:
        """Signal ready for next round (manual retrieval)."""
        if self.state == GameState.RETRIEVAL:
            self._end_retrieval()

    def update(self, dt: float) -> None:
        """
        Update game logic.

        Args:
            dt: Delta time in seconds
        """
        # Handle retrieval state
        if self._in_retrieval:
            if self._quiver and not self._quiver.is_manual_retrieval:
                if self._update_retrieval(dt):
                    self._end_retrieval()
            return

        if self._internal_state != GameState.PLAYING:
            return

        # Track time
        self._time_survived += dt

        # Update difficulty based on mode
        self._update_difficulty(dt)

        # Update meter
        self._meter.update(dt)

        # Update target
        self._target.update(dt)

        # Clean up old hit times for adaptive mode
        current_time = time.time()
        self._recent_hit_times = [
            t for t in self._recent_hit_times
            if current_time - t < self._adaptive_window
        ]

        # Check win/lose conditions
        self._check_game_state()

    def _update_difficulty(self, dt: float) -> None:
        """Update difficulty based on game mode."""
        if self._game_mode == 'sprint':
            # Sprint: Fixed difficulty
            pass

        elif self._game_mode == 'endurance':
            # Endurance: Very slow escalation
            self._current_drain_rate += self._drain_increase_rate * 0.3 * dt
            self._meter.set_drain_rate(self._current_drain_rate)

        elif self._game_mode == 'pressure':
            # Pressure: Constant escalation
            self._current_drain_rate += self._drain_increase_rate * dt
            self._current_shrink_rate += self._shrink_increase_rate * dt
            self._meter.set_drain_rate(self._current_drain_rate)
            self._target.set_shrink_rate(self._current_shrink_rate)

            # Also increase movement speed
            base_speed = config.PACING_PRESETS[self._pacing].movement_speed
            speed_multiplier = 1.0 + self._time_survived * 0.02
            self._target.set_movement_speed(base_speed * speed_multiplier)

        elif self._game_mode == 'adaptive':
            # Adaptive: Adjust based on performance
            hit_rate = len(self._recent_hit_times) / self._adaptive_window

            # Target hit rate for flow state (varies by pacing)
            target_rates = {'archery': 0.5, 'throwing': 1.0, 'blaster': 2.5}
            target_rate = target_rates.get(self._pacing, 1.0)

            # Adjust difficulty based on performance
            if hit_rate > target_rate * 1.2:
                # Doing too well - increase difficulty
                self._current_drain_rate = min(
                    self._base_drain_rate * 2.5,
                    self._current_drain_rate + self._drain_increase_rate * dt * 2
                )
            elif hit_rate < target_rate * 0.8:
                # Struggling - ease off slightly
                self._current_drain_rate = max(
                    self._base_drain_rate * 0.7,
                    self._current_drain_rate - self._drain_increase_rate * dt
                )

            self._meter.set_drain_rate(self._current_drain_rate)

    def _check_game_state(self) -> None:
        """Check win/lose conditions."""
        # Lose: Meter empty
        if self._meter.is_empty:
            self._internal_state = GameState.GAME_OVER
            return

        # Win: Meter full (sprint mode only)
        if self._game_mode == 'sprint' and self._meter.is_full:
            self._internal_state = GameState.WON
            return

    def handle_input(self, events: List[InputEvent]) -> None:
        """
        Process input events.

        Args:
            events: List of input events
        """
        if self._internal_state != GameState.PLAYING:
            return

        for event in events:
            # Check quiver
            if self._quiver and self._quiver.is_empty:
                continue

            # Check if hit target
            if self._target.contains_point(event.position.x, event.position.y):
                # Hit!
                self._hits += 1
                self._current_streak += 1
                self._best_streak = max(self._best_streak, self._current_streak)

                # Fill meter
                self._meter.add_hit()

                # Visual feedback
                self._target.register_hit()

                # Track for adaptive difficulty
                self._recent_hit_times.append(time.time())
            else:
                # Miss
                self._misses += 1
                self._current_streak = 0

            # Use shot from quiver
            if self._use_shot():
                self._start_retrieval()

    def render(self, screen: pygame.Surface) -> None:
        """
        Render the game.

        Args:
            screen: Pygame surface to draw on
        """
        # Background
        screen.fill(config.BACKGROUND_COLOR)

        # Render meter
        self._meter.render(screen)
        self._meter.render_percentage(screen)

        # Render target
        self._target.render(screen)

        # Render UI
        self._render_ui(screen)

        # Render retrieval overlay
        if self.state == GameState.RETRIEVAL:
            self._render_retrieval(screen)
        elif self._internal_state == GameState.GAME_OVER:
            self._render_game_over(screen)
        elif self._internal_state == GameState.WON:
            self._render_win(screen)

    def _render_ui(self, screen: pygame.Surface) -> None:
        """Render UI elements."""
        font = self._get_font()

        # Right side stats
        x_right = config.SCREEN_WIDTH - 200

        # Time survived
        time_text = font.render(f"Time: {self._time_survived:.1f}s", True, (255, 255, 255))
        screen.blit(time_text, (x_right, 20))

        # Hits
        hits_text = font.render(f"Hits: {self._hits}", True, (100, 255, 100))
        screen.blit(hits_text, (x_right, 60))

        # Current streak
        if self._current_streak > 1:
            streak_text = font.render(f"Streak: {self._current_streak}", True, (255, 255, 100))
            screen.blit(streak_text, (x_right, 100))

        # Accuracy
        total_shots = self._hits + self._misses
        if total_shots > 0:
            accuracy = self._hits / total_shots * 100
            acc_color = (100, 255, 100) if accuracy >= 70 else (255, 255, 100) if accuracy >= 50 else (255, 100, 100)
            acc_text = font.render(f"Accuracy: {accuracy:.0f}%", True, acc_color)
            screen.blit(acc_text, (x_right, 140))

        # Game mode indicator
        mode_text = font.render(f"Mode: {self._game_mode.upper()}", True, (150, 150, 150))
        screen.blit(mode_text, (x_right, config.SCREEN_HEIGHT - 80))

        # Quiver status
        if self._quiver:
            quiver_text = font.render(
                self._quiver.get_display_text(),
                True,
                (255, 100, 100) if self._quiver.remaining <= 2 else (255, 255, 255)
            )
            screen.blit(quiver_text, (x_right, config.SCREEN_HEIGHT - 40))

        # Drain rate indicator (bottom center, subtle)
        drain_percent = (self._current_drain_rate / self._base_drain_rate - 1) * 100
        if drain_percent > 5:
            drain_text = font.render(f"Pressure: +{drain_percent:.0f}%", True, (255, 150, 100))
            drain_rect = drain_text.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - 30))
            screen.blit(drain_text, drain_rect)

    def _render_retrieval(self, screen: pygame.Surface) -> None:
        """Render retrieval overlay."""
        if not self._quiver:
            return

        font_large = self._get_font_large()
        font_small = self._get_font()

        # Semi-transparent overlay
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        # Title
        title = font_large.render("RETRIEVAL", True, (255, 200, 100))
        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 - 60))
        screen.blit(title, title_rect)

        # Instructions
        instr = font_small.render(self._quiver.get_retrieval_text(), True, (255, 255, 255))
        instr_rect = instr.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2))
        screen.blit(instr, instr_rect)

        # Note about meter draining
        note = font_small.render("(Meter is paused during retrieval)", True, (150, 150, 150))
        note_rect = note.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 + 40))
        screen.blit(note, note_rect)

    def _render_game_over(self, screen: pygame.Surface) -> None:
        """Render game over screen."""
        font_large = self._get_font_large()
        font_small = self._get_font()

        # Overlay
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Game over text
        title = font_large.render("GAME OVER", True, (255, 80, 80))
        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 - 80))
        screen.blit(title, title_rect)

        # Stats
        stats = [
            f"Time Survived: {self._time_survived:.1f}s",
            f"Total Hits: {self._hits}",
            f"Best Streak: {self._best_streak}",
        ]

        if self._hits + self._misses > 0:
            accuracy = self._hits / (self._hits + self._misses) * 100
            stats.append(f"Accuracy: {accuracy:.1f}%")

        y_offset = config.SCREEN_HEIGHT // 2 - 20
        for stat in stats:
            text = font_small.render(stat, True, (255, 255, 255))
            text_rect = text.get_rect(center=(config.SCREEN_WIDTH // 2, y_offset))
            screen.blit(text, text_rect)
            y_offset += 40

        # Restart hint
        hint = font_small.render("Press R to restart", True, (150, 150, 150))
        hint_rect = hint.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - 60))
        screen.blit(hint, hint_rect)

    def _render_win(self, screen: pygame.Surface) -> None:
        """Render win screen."""
        font_large = self._get_font_large()
        font_small = self._get_font()

        # Overlay
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Win text
        title = font_large.render("METER FULL!", True, (100, 255, 100))
        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 - 80))
        screen.blit(title, title_rect)

        # Stats
        stats = [
            f"Time: {self._time_survived:.1f}s",
            f"Hits: {self._hits}",
            f"Best Streak: {self._best_streak}",
        ]

        if self._hits + self._misses > 0:
            accuracy = self._hits / (self._hits + self._misses) * 100
            stats.append(f"Accuracy: {accuracy:.1f}%")

        y_offset = config.SCREEN_HEIGHT // 2 - 20
        for stat in stats:
            text = font_small.render(stat, True, (255, 255, 255))
            text_rect = text.get_rect(center=(config.SCREEN_WIDTH // 2, y_offset))
            screen.blit(text, text_rect)
            y_offset += 40

        # Restart hint
        hint = font_small.render("Press R to play again", True, (150, 150, 150))
        hint_rect = hint.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - 60))
        screen.blit(hint, hint_rect)
