"""
ManyTargets Game Mode

Field clearance game - hit all targets while avoiding misses.
Inspired by the "egg carton" training method.
"""
import time
from enum import Enum
from typing import List, Optional

import pygame

from models import Vector2D
from games.common.input import InputEvent
from games.ManyTargets import config
from games.ManyTargets.target_field import TargetField, MissMode, HitResult


class GameState(Enum):
    """Game states for ManyTargets."""
    READY = "ready"          # Showing targets, waiting for first shot
    PLAYING = "playing"      # Active round in progress
    COMPLETE = "complete"    # All targets hit
    FAILED = "failed"        # Strict mode miss
    TIMEOUT = "timeout"      # Time ran out
    GAME_OVER = "game_over"  # Session complete (for compatibility)


class ManyTargetsMode:
    """ManyTargets game mode - clear the field of targets.

    Game flow:
    1. Targets appear randomly distributed (READY state)
    2. First shot starts the round (PLAYING state)
    3. Hit targets to clear them, misses penalized
    4. Round ends when: all hit (COMPLETE), miss in strict mode (FAILED), or timeout
    5. Click to start new round
    """

    def __init__(
        self,
        count: Optional[int] = None,
        size: Optional[str] = None,
        timed: Optional[int] = None,
        miss_mode: Optional[str] = None,
        allow_duplicates: bool = False,
        progressive: bool = False,
        shrink_rate: Optional[float] = None,
        min_size: Optional[int] = None,
        spacing: Optional[float] = None,
    ):
        """Initialize the ManyTargets game.

        Args:
            count: Number of targets to generate
            size: Target size (small, medium, large, mixed)
            timed: Time limit in seconds (None = unlimited)
            miss_mode: 'penalty' or 'strict'
            allow_duplicates: If True, targets stay after hit
            progressive: If True, targets shrink as you clear
            shrink_rate: Size multiplier per hit in progressive mode
            min_size: Minimum target radius in progressive mode
            spacing: Minimum spacing between targets
        """
        self._target_count = count or config.DEFAULT_TARGET_COUNT
        self._target_radius = self._parse_size(size)
        self._time_limit = timed
        self._miss_mode = MissMode.STRICT if miss_mode == 'strict' else MissMode.PENALTY
        self._allow_duplicates = allow_duplicates
        self._progressive = progressive
        self._shrink_rate = shrink_rate or config.DEFAULT_SHRINK_RATE
        self._min_size = min_size or config.MIN_TARGET_SIZE
        self._spacing = spacing or config.MIN_TARGET_SPACING

        self._state = GameState.READY
        self._field: Optional[TargetField] = None
        self._session_best: Optional[int] = None
        self._rounds_completed = 0

        # Screen dimensions (set on first render)
        self._screen_width = config.SCREEN_WIDTH
        self._screen_height = config.SCREEN_HEIGHT

        # Animation state
        self._hit_animations: List[dict] = []  # {position, time, radius}
        self._miss_animations: List[dict] = []  # {position, time}

        # Start first round
        self._start_new_round()

    def _parse_size(self, size: Optional[str]) -> float:
        """Parse size string to radius."""
        if size is None or size == 'medium':
            return config.TARGET_RADIUS_MEDIUM
        elif size == 'small':
            return config.TARGET_RADIUS_SMALL
        elif size == 'large':
            return config.TARGET_RADIUS_LARGE
        elif size == 'mixed':
            # Will be handled per-target in future
            return config.TARGET_RADIUS_MEDIUM
        else:
            return config.TARGET_RADIUS_MEDIUM

    @property
    def state(self) -> GameState:
        """Current game state."""
        return self._state

    def get_score(self) -> int:
        """Get current score."""
        if self._field is None:
            return 0
        return self._field.calculate_score()

    def _start_new_round(self) -> None:
        """Initialize a new round."""
        self._field = TargetField(
            screen_width=self._screen_width,
            screen_height=self._screen_height,
            target_count=self._target_count,
            target_radius=self._target_radius,
            min_spacing=self._spacing,
            miss_mode=self._miss_mode,
            allow_duplicates=self._allow_duplicates,
            progressive=self._progressive,
            shrink_rate=self._shrink_rate,
            min_size=self._min_size,
        )
        self._state = GameState.READY
        self._hit_animations = []
        self._miss_animations = []

    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events."""
        for event in events:
            self._handle_shot(event.position)

    def _handle_shot(self, position: Vector2D) -> None:
        """Handle a shot at the given position."""
        if self._field is None:
            return

        if self._state == GameState.READY:
            # First shot starts the round
            self._state = GameState.PLAYING
            self._process_shot(position)

        elif self._state == GameState.PLAYING:
            self._process_shot(position)

        elif self._state in (GameState.COMPLETE, GameState.FAILED, GameState.TIMEOUT):
            # Any click starts new round
            self._start_new_round()

    def _process_shot(self, position: Vector2D) -> None:
        """Process a shot during active play."""
        if self._field is None:
            return

        result = self._field.process_shot(position)

        if result == HitResult.HIT:
            # Add hit animation
            self._hit_animations.append({
                'position': position,
                'time': time.monotonic(),
                'radius': self._target_radius,
            })

            # Check if complete
            if self._field.is_complete:
                self._end_round(GameState.COMPLETE)

        elif result == HitResult.DUPLICATE:
            # Could add duplicate animation
            pass

        elif result == HitResult.MISS:
            # Add miss animation
            self._miss_animations.append({
                'position': position,
                'time': time.monotonic(),
            })

            # Check if failed (strict mode)
            if self._field.is_failed:
                self._end_round(GameState.FAILED)

    def _end_round(self, end_state: GameState) -> None:
        """End the current round."""
        if self._field is None:
            return

        self._field.end_round()
        self._state = end_state
        self._rounds_completed += 1

        # Update session best
        final_score = self._field.calculate_final_score()
        if self._session_best is None or final_score > self._session_best:
            self._session_best = final_score

    def update(self, dt: float) -> None:
        """Update game state."""
        if self._field is None:
            return

        # Check timeout
        if self._state == GameState.PLAYING and self._time_limit is not None:
            if self._field.duration >= self._time_limit:
                self._end_round(GameState.TIMEOUT)

        # Clean up old animations
        now = time.monotonic()
        self._hit_animations = [
            a for a in self._hit_animations
            if now - a['time'] < 0.5
        ]
        self._miss_animations = [
            a for a in self._miss_animations
            if now - a['time'] < 1.0
        ]

    def render(self, screen: pygame.Surface) -> None:
        """Render the game."""
        # Update screen dimensions
        self._screen_width, self._screen_height = screen.get_size()

        # Clear screen
        screen.fill(config.BACKGROUND_COLOR)

        if self._field is None:
            return

        # Draw targets
        self._render_targets(screen)

        # Draw hit animations
        self._render_hit_animations(screen)

        # Draw miss markers
        self._render_miss_markers(screen)

        # Draw HUD
        self._render_hud(screen)

    def _render_targets(self, screen: pygame.Surface) -> None:
        """Render all targets."""
        if self._field is None:
            return

        for target in self._field.targets:
            if target.hit and not self._allow_duplicates:
                # Draw faded hit marker
                if config.SHOW_HIT_MARKERS:
                    pygame.draw.circle(
                        screen,
                        config.HIT_MARKER_COLOR,
                        (int(target.position.x), int(target.position.y)),
                        int(target.radius),
                        2
                    )
            else:
                # Draw active target
                center = (int(target.position.x), int(target.position.y))
                radius = int(target.radius)

                # Fill
                pygame.draw.circle(screen, config.TARGET_FILL_COLOR, center, radius)
                # Outline
                pygame.draw.circle(screen, config.TARGET_COLOR, center, radius, 3)

                # Center dot
                pygame.draw.circle(screen, config.TARGET_COLOR, center, 3)

    def _render_hit_animations(self, screen: pygame.Surface) -> None:
        """Render hit feedback animations."""
        now = time.monotonic()

        for anim in self._hit_animations:
            age = now - anim['time']
            if age < 0.3:
                # Expanding ring
                progress = age / 0.3
                radius = int(anim['radius'] * (1 + progress * 0.5))
                alpha = int(255 * (1 - progress))

                # Create surface with alpha
                surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                color = (*config.HIT_COLOR[:3], alpha)
                pygame.draw.circle(surf, color, (radius + 2, radius + 2), radius, 3)
                screen.blit(surf, (
                    int(anim['position'].x) - radius - 2,
                    int(anim['position'].y) - radius - 2
                ))

    def _render_miss_markers(self, screen: pygame.Surface) -> None:
        """Render miss markers."""
        now = time.monotonic()

        # Draw persistent miss markers from field
        if self._field:
            for pos in self._field.miss_positions:
                self._draw_x_marker(screen, pos, config.MISS_COLOR, 1.0)

        # Draw animated miss markers
        for anim in self._miss_animations:
            age = now - anim['time']
            if age < 0.5:
                progress = age / 0.5
                alpha = 1.0 - progress * 0.5  # Fade slightly
                self._draw_x_marker(screen, anim['position'], config.MISS_COLOR, alpha)

    def _draw_x_marker(self, screen: pygame.Surface, pos: Vector2D, color: tuple, alpha: float) -> None:
        """Draw an X marker at position."""
        size = 12
        x, y = int(pos.x), int(pos.y)

        if alpha < 1.0:
            # Draw with alpha
            surf = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
            c = (*color[:3], int(255 * alpha))
            pygame.draw.line(surf, c, (2, 2), (size * 2 + 2, size * 2 + 2), 3)
            pygame.draw.line(surf, c, (size * 2 + 2, 2), (2, size * 2 + 2), 3)
            screen.blit(surf, (x - size - 2, y - size - 2))
        else:
            pygame.draw.line(screen, color, (x - size, y - size), (x + size, y + size), 3)
            pygame.draw.line(screen, color, (x + size, y - size), (x - size, y + size), 3)

    def _render_hud(self, screen: pygame.Surface) -> None:
        """Render the heads-up display."""
        if self._field is None:
            return

        font_large = pygame.font.Font(None, 48)
        font_medium = pygame.font.Font(None, 32)
        font_small = pygame.font.Font(None, 24)

        y_offset = 20
        x_offset = 20

        # Mode indicators (top right)
        mode_parts = []
        if self._miss_mode == MissMode.STRICT:
            mode_parts.append("STRICT")
        if self._progressive:
            mode_parts.append("PROGRESSIVE")
        if self._allow_duplicates:
            mode_parts.append("DUPLICATES")
        if self._time_limit:
            mode_parts.append(f"{self._time_limit}s")

        if mode_parts:
            mode_text = " | ".join(mode_parts)
            text = font_small.render(mode_text, True, (150, 150, 200))
            screen.blit(text, (self._screen_width - text.get_width() - 20, 20))

        # State message
        if self._state == GameState.READY:
            text = font_medium.render("Click to start", True, (200, 200, 100))
            screen.blit(text, (x_offset, y_offset))
            y_offset += 40
        elif self._state == GameState.PLAYING:
            text = font_medium.render("Clear the field!", True, (100, 255, 100))
            screen.blit(text, (x_offset, y_offset))
            y_offset += 40
        elif self._state == GameState.COMPLETE:
            text = font_medium.render("COMPLETE! Click to continue", True, (100, 255, 100))
            screen.blit(text, (x_offset, y_offset))
            y_offset += 40
        elif self._state == GameState.FAILED:
            text = font_medium.render("MISS! Round over - Click to retry", True, (255, 100, 100))
            screen.blit(text, (x_offset, y_offset))
            y_offset += 40
        elif self._state == GameState.TIMEOUT:
            text = font_medium.render("TIME'S UP! Click to continue", True, (255, 200, 100))
            screen.blit(text, (x_offset, y_offset))
            y_offset += 40

        # Target count
        remaining = self._field.remaining_count
        total = self._field.total_targets
        count_text = f"Targets: {total - remaining} / {total}"
        text = font_medium.render(count_text, True, (200, 200, 200))
        screen.blit(text, (x_offset, y_offset))
        y_offset += 30

        # Hits and misses
        stats_text = f"Hits: {self._field.hits}  Misses: {self._field.misses}"
        if self._allow_duplicates and self._field.duplicates > 0:
            stats_text += f"  Dupes: {self._field.duplicates}"
        text = font_small.render(stats_text, True, (180, 180, 180))
        screen.blit(text, (x_offset, y_offset))
        y_offset += 25

        # Score
        score = self._field.calculate_score()
        score_text = f"Score: {score}"
        text = font_large.render(score_text, True, (255, 255, 255))
        screen.blit(text, (x_offset, y_offset))
        y_offset += 50

        # Session best
        if self._session_best is not None:
            best_text = f"Best: {self._session_best}"
            text = font_medium.render(best_text, True, (100, 200, 255))
            screen.blit(text, (x_offset, y_offset))
            y_offset += 30

        # Rounds completed
        rounds_text = f"Rounds: {self._rounds_completed}"
        text = font_small.render(rounds_text, True, (150, 150, 150))
        screen.blit(text, (x_offset, y_offset))

        # Timer (if timed mode)
        if self._time_limit and self._state == GameState.PLAYING:
            self._render_timer(screen)

        # Final score breakdown (on round end)
        if self._state in (GameState.COMPLETE, GameState.FAILED, GameState.TIMEOUT):
            self._render_score_breakdown(screen)

    def _render_timer(self, screen: pygame.Surface) -> None:
        """Render the countdown timer."""
        if self._field is None or self._time_limit is None:
            return

        elapsed = self._field.duration
        remaining = max(0, self._time_limit - elapsed)
        progress = remaining / self._time_limit

        # Timer bar
        bar_width = 200
        bar_height = 20
        bar_x = self._screen_width - bar_width - 20
        bar_y = 50

        # Color based on time remaining
        if progress > 0.5:
            color = config.TIMER_COLOR_SAFE
        elif progress > 0.25:
            color = config.TIMER_COLOR_WARNING
        else:
            color = config.TIMER_COLOR_DANGER

        # Background
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
        # Fill
        fill_width = int(bar_width * progress)
        pygame.draw.rect(screen, color, (bar_x, bar_y, fill_width, bar_height))
        # Border
        pygame.draw.rect(screen, (150, 150, 150), (bar_x, bar_y, bar_width, bar_height), 2)

        # Time text
        font = pygame.font.Font(None, 24)
        time_text = f"{remaining:.1f}s"
        text = font.render(time_text, True, (200, 200, 200))
        screen.blit(text, (bar_x + bar_width + 10, bar_y + 2))

    def _render_score_breakdown(self, screen: pygame.Surface) -> None:
        """Render score breakdown on round end."""
        if self._field is None:
            return

        font = pygame.font.Font(None, 24)
        x = self._screen_width // 2 - 100
        y = self._screen_height // 2 + 50

        lines = [
            f"Hits: {self._field.hits} × {config.HIT_POINTS} = +{self._field.hits * config.HIT_POINTS}",
        ]

        if self._field.misses > 0:
            lines.append(f"Misses: {self._field.misses} × {config.MISS_PENALTY} = -{self._field.misses * config.MISS_PENALTY}")

        if self._field.duplicates > 0:
            lines.append(f"Duplicates: {self._field.duplicates} × {config.DUPLICATE_PENALTY} = -{self._field.duplicates * config.DUPLICATE_PENALTY}")

        if self._field.remaining_count > 0:
            lines.append(f"Remaining: {self._field.remaining_count} × {config.REMAINING_PENALTY} = -{self._field.remaining_count * config.REMAINING_PENALTY}")

        if self._field.is_complete and self._field.misses == 0 and self._field.duplicates == 0:
            lines.append(f"Perfect Bonus: +{config.PERFECT_BONUS}")

        lines.append("─" * 25)
        lines.append(f"Final Score: {self._field.calculate_final_score()}")

        for i, line in enumerate(lines):
            color = (200, 200, 200) if i < len(lines) - 1 else (255, 255, 100)
            text = font.render(line, True, color)
            screen.blit(text, (x, y + i * 25))
