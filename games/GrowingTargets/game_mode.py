"""
GrowingTargets Game Mode

Speed/accuracy tradeoff game - targets grow over time.
Smaller = more points, but harder to hit.
"""
import time
from enum import Enum
from typing import List, Optional

import pygame

from models import Vector2D
from games.common.input import InputEvent
from games.GrowingTargets import config
from games.GrowingTargets.target import GrowingTarget, TargetSpawner


class GameState(Enum):
    """Game states for GrowingTargets."""
    PLAYING = "playing"
    GAME_OVER = "game_over"


class GrowingTargetsMode:
    """GrowingTargets game mode - hit targets while they're small.

    Core mechanic: Targets spawn small and grow over time.
    - Hit early (small) = high points but hard
    - Hit late (large) = low points but easy
    - Let it expire = penalty + lose life
    - Miss (click empty space) = penalty + lose life

    This creates a natural speed/accuracy tradeoff without
    artificial timers or pressure mechanics.
    """

    def __init__(
        self,
        spawn_rate: Optional[float] = None,
        max_targets: Optional[int] = None,
        growth_rate: Optional[float] = None,
        start_size: Optional[int] = None,
        max_size: Optional[int] = None,
        miss_penalty: Optional[int] = None,
        lives: Optional[int] = None,
        **kwargs,  # Accept any additional args
    ):
        """Initialize the GrowingTargets game.

        Args:
            spawn_rate: Seconds between target spawns
            max_targets: Maximum simultaneous targets
            growth_rate: Target growth rate (pixels/second)
            start_size: Initial target radius
            max_size: Maximum target radius (expires at this size)
            miss_penalty: Points lost per miss
            lives: Number of lives (0 = unlimited)
        """
        self._spawn_rate = spawn_rate or config.DEFAULT_SPAWN_RATE
        self._max_targets = max_targets or config.MAX_TARGETS
        self._growth_rate = growth_rate or config.GROWTH_RATE
        self._start_size = start_size or config.START_SIZE
        self._max_size = max_size or config.MAX_SIZE
        self._miss_penalty = miss_penalty or config.MISS_PENALTY
        self._max_lives = lives if lives is not None else config.DEFAULT_LIVES

        # Game state
        self._state = GameState.PLAYING
        self._score = 0
        self._lives = self._max_lives if self._max_lives > 0 else float('inf')
        self._targets: List[GrowingTarget] = []
        self._spawner: Optional[TargetSpawner] = None

        # Stats
        self._hits = 0
        self._misses = 0
        self._expired = 0
        self._total_hit_value = 0.0  # Sum of value multipliers
        self._best_hit_multiplier = 0.0

        # Screen dimensions (set on first render)
        self._screen_width = config.SCREEN_WIDTH
        self._screen_height = config.SCREEN_HEIGHT

        # Visual feedback
        self._hit_effects: List[dict] = []  # {position, time, points, color}
        self._miss_effects: List[dict] = []  # {position, time}
        self._expire_effects: List[dict] = []  # {position, time}

        # Session tracking
        self._session_best = 0
        self._games_played = 0
        self._start_time = time.monotonic()

    @property
    def state(self) -> GameState:
        """Current game state."""
        return self._state

    def get_score(self) -> int:
        """Get current score."""
        return self._score

    def _ensure_spawner(self) -> None:
        """Ensure spawner is initialized."""
        if self._spawner is None:
            self._spawner = TargetSpawner(
                screen_width=self._screen_width,
                screen_height=self._screen_height,
                spawn_rate=self._spawn_rate,
                max_targets=self._max_targets,
                start_size=self._start_size,
                max_size=self._max_size,
                growth_rate=self._growth_rate,
            )
            # Spawn first target immediately
            self._targets.append(self._spawner.force_spawn())

    def _restart(self) -> None:
        """Restart the game."""
        # Update session stats
        if self._score > self._session_best:
            self._session_best = self._score
        self._games_played += 1

        # Reset game state
        self._state = GameState.PLAYING
        self._score = 0
        self._lives = self._max_lives if self._max_lives > 0 else float('inf')
        self._targets = []
        self._spawner = None

        # Reset stats
        self._hits = 0
        self._misses = 0
        self._expired = 0
        self._total_hit_value = 0.0
        self._best_hit_multiplier = 0.0

        # Clear effects
        self._hit_effects = []
        self._miss_effects = []
        self._expire_effects = []

        self._start_time = time.monotonic()

    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events."""
        for event in events:
            self._handle_click(event.position)

    def _handle_click(self, position: Vector2D) -> None:
        """Handle a click/hit at position."""
        if self._state == GameState.GAME_OVER:
            # Click to restart
            self._restart()
            return

        # Check for target hits (newest first for visual feedback)
        hit_target = None
        for target in reversed(self._targets):
            if target.is_active and target.check_hit(position):
                hit_target = target
                break

        if hit_target:
            # Hit!
            points = hit_target.calculate_points()
            multiplier = hit_target.value_multiplier

            self._score += points
            self._hits += 1
            self._total_hit_value += multiplier
            if multiplier > self._best_hit_multiplier:
                self._best_hit_multiplier = multiplier

            # Hit effect color based on value
            if multiplier >= 8:
                color = config.TARGET_FILL_SMALL  # Amazing
            elif multiplier >= 4:
                color = (150, 255, 150)  # Good
            elif multiplier >= 2:
                color = config.TARGET_FILL_MEDIUM  # OK
            else:
                color = config.TARGET_FILL_LARGE  # Late

            self._hit_effects.append({
                'position': hit_target.position,
                'time': time.monotonic(),
                'points': points,
                'color': color,
                'multiplier': multiplier,
            })

        else:
            # Miss - clicked empty space
            self._score -= self._miss_penalty
            self._misses += 1

            self._miss_effects.append({
                'position': position,
                'time': time.monotonic(),
            })

            if config.LIVES_LOST_ON_MISS:
                self._lose_life()

    def _lose_life(self) -> None:
        """Lose a life and check for game over."""
        if self._max_lives > 0:  # Only if lives are limited
            self._lives -= 1
            if self._lives <= 0:
                self._state = GameState.GAME_OVER

    def update(self, dt: float) -> None:
        """Update game state."""
        if self._state == GameState.GAME_OVER:
            return

        self._ensure_spawner()

        # Update all targets
        for target in self._targets:
            target.update(dt)

        # Check for expired targets
        for target in self._targets:
            if target.expired and not hasattr(target, '_expire_counted'):
                target._expire_counted = True
                self._expired += 1
                self._score -= config.EXPIRE_PENALTY

                self._expire_effects.append({
                    'position': target.position,
                    'time': time.monotonic(),
                })

                if config.LIVES_LOST_ON_EXPIRE:
                    self._lose_life()

        # Remove inactive targets
        self._targets = [t for t in self._targets if t.is_active]

        # Spawn new targets
        if self._spawner and self._spawner.should_spawn(len(self._targets)):
            self._targets.append(self._spawner.spawn())

        # Clean up old effects
        now = time.monotonic()
        self._hit_effects = [e for e in self._hit_effects if now - e['time'] < 1.0]
        self._miss_effects = [e for e in self._miss_effects if now - e['time'] < 0.5]
        self._expire_effects = [e for e in self._expire_effects if now - e['time'] < 0.5]

    def render(self, screen: pygame.Surface) -> None:
        """Render the game."""
        # Update screen dimensions
        self._screen_width, self._screen_height = screen.get_size()
        if self._spawner:
            self._spawner.screen_width = self._screen_width
            self._spawner.screen_height = self._screen_height

        # Clear screen
        screen.fill(config.BACKGROUND_COLOR)

        # Draw targets
        self._render_targets(screen)

        # Draw effects
        self._render_effects(screen)

        # Draw HUD
        self._render_hud(screen)

        # Draw game over screen
        if self._state == GameState.GAME_OVER:
            self._render_game_over(screen)

    def _render_targets(self, screen: pygame.Surface) -> None:
        """Render all active targets."""
        for target in self._targets:
            if not target.is_active:
                continue

            center = (int(target.position.x), int(target.position.y))
            radius = int(target.current_radius)

            # Color based on size ratio (small=green, medium=yellow, large=red)
            ratio = target.size_ratio
            if ratio < 0.33:
                fill_color = config.TARGET_FILL_SMALL
            elif ratio < 0.66:
                # Interpolate green -> yellow
                t = (ratio - 0.33) / 0.33
                fill_color = (
                    int(config.TARGET_FILL_SMALL[0] + t * (config.TARGET_FILL_MEDIUM[0] - config.TARGET_FILL_SMALL[0])),
                    int(config.TARGET_FILL_SMALL[1] + t * (config.TARGET_FILL_MEDIUM[1] - config.TARGET_FILL_SMALL[1])),
                    int(config.TARGET_FILL_SMALL[2] + t * (config.TARGET_FILL_MEDIUM[2] - config.TARGET_FILL_SMALL[2])),
                )
            else:
                # Interpolate yellow -> red
                t = (ratio - 0.66) / 0.34
                fill_color = (
                    int(config.TARGET_FILL_MEDIUM[0] + t * (config.TARGET_FILL_LARGE[0] - config.TARGET_FILL_MEDIUM[0])),
                    int(config.TARGET_FILL_MEDIUM[1] + t * (config.TARGET_FILL_LARGE[1] - config.TARGET_FILL_MEDIUM[1])),
                    int(config.TARGET_FILL_MEDIUM[2] + t * (config.TARGET_FILL_LARGE[2] - config.TARGET_FILL_MEDIUM[2])),
                )

            # Fill
            pygame.draw.circle(screen, fill_color, center, radius)
            # Outline
            pygame.draw.circle(screen, config.TARGET_OUTLINE_COLOR, center, radius, 2)
            # Center dot
            pygame.draw.circle(screen, config.TARGET_OUTLINE_COLOR, center, 3)

            # Value indicator (small text showing multiplier)
            if radius > 20:
                font = pygame.font.Font(None, 20)
                mult_text = f"{target.value_multiplier:.1f}x"
                text = font.render(mult_text, True, (255, 255, 255))
                text_rect = text.get_rect(center=(center[0], center[1] - radius - 12))
                screen.blit(text, text_rect)

    def _render_effects(self, screen: pygame.Surface) -> None:
        """Render visual effects."""
        now = time.monotonic()

        # Hit effects - expanding ring with points
        for effect in self._hit_effects:
            age = now - effect['time']
            if age < 0.5:
                progress = age / 0.5
                radius = int(20 + 30 * progress)
                alpha = int(255 * (1 - progress))

                # Ring
                surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                color = (*effect['color'][:3], alpha)
                pygame.draw.circle(surf, color, (radius + 2, radius + 2), radius, 3)
                screen.blit(surf, (
                    int(effect['position'].x) - radius - 2,
                    int(effect['position'].y) - radius - 2
                ))

            # Floating points text
            if age < 1.0:
                progress = age / 1.0
                y_offset = int(-40 * progress)
                alpha = int(255 * (1 - progress * 0.5))

                font = pygame.font.Font(None, 32)
                points_text = f"+{effect['points']}"
                text = font.render(points_text, True, effect['color'])
                text.set_alpha(alpha)
                text_rect = text.get_rect(center=(
                    int(effect['position'].x),
                    int(effect['position'].y) + y_offset
                ))
                screen.blit(text, text_rect)

        # Miss effects - X mark
        for effect in self._miss_effects:
            age = now - effect['time']
            if age < 0.5:
                progress = age / 0.5
                alpha = int(255 * (1 - progress))
                size = 15

                x, y = int(effect['position'].x), int(effect['position'].y)
                surf = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
                color = (*config.MISS_COLOR[:3], alpha)
                pygame.draw.line(surf, color, (2, 2), (size * 2 + 2, size * 2 + 2), 4)
                pygame.draw.line(surf, color, (size * 2 + 2, 2), (2, size * 2 + 2), 4)
                screen.blit(surf, (x - size - 2, y - size - 2))

        # Expire effects - fading ring
        for effect in self._expire_effects:
            age = now - effect['time']
            if age < 0.5:
                progress = age / 0.5
                radius = int(self._max_size * (1 - progress * 0.3))
                alpha = int(150 * (1 - progress))

                surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                color = (*config.EXPIRE_COLOR[:3], alpha)
                pygame.draw.circle(surf, color, (radius + 2, radius + 2), radius, 2)
                screen.blit(surf, (
                    int(effect['position'].x) - radius - 2,
                    int(effect['position'].y) - radius - 2
                ))

    def _render_hud(self, screen: pygame.Surface) -> None:
        """Render heads-up display."""
        font_large = pygame.font.Font(None, 48)
        font_medium = pygame.font.Font(None, 32)
        font_small = pygame.font.Font(None, 24)

        y_offset = 20
        x_offset = 20

        # Score
        score_text = f"Score: {self._score}"
        text = font_large.render(score_text, True, (255, 255, 255))
        screen.blit(text, (x_offset, y_offset))
        y_offset += 50

        # Lives (if limited)
        if self._max_lives > 0:
            lives_text = f"Lives: {'❤' * int(self._lives)}"
            color = (255, 100, 100) if self._lives <= 1 else (255, 200, 200)
            text = font_medium.render(lives_text, True, color)
            screen.blit(text, (x_offset, y_offset))
            y_offset += 35

        # Stats
        stats_text = f"Hits: {self._hits}  Misses: {self._misses}  Expired: {self._expired}"
        text = font_small.render(stats_text, True, (180, 180, 180))
        screen.blit(text, (x_offset, y_offset))
        y_offset += 25

        # Average multiplier
        if self._hits > 0:
            avg_mult = self._total_hit_value / self._hits
            avg_text = f"Avg: {avg_mult:.1f}x  Best: {self._best_hit_multiplier:.1f}x"
            text = font_small.render(avg_text, True, (150, 200, 150))
            screen.blit(text, (x_offset, y_offset))

        # Session best (top right)
        if self._session_best > 0:
            best_text = f"Best: {self._session_best}"
            text = font_medium.render(best_text, True, (100, 200, 255))
            screen.blit(text, (self._screen_width - text.get_width() - 20, 20))

        # Instructions (bottom)
        hint_text = "Hit targets early for max points - Green=High, Red=Low"
        text = font_small.render(hint_text, True, (100, 100, 100))
        screen.blit(text, (self._screen_width // 2 - text.get_width() // 2, self._screen_height - 30))

    def _render_game_over(self, screen: pygame.Surface) -> None:
        """Render game over overlay."""
        # Semi-transparent overlay
        overlay = pygame.Surface((self._screen_width, self._screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Game over text
        font_large = pygame.font.Font(None, 72)
        font_medium = pygame.font.Font(None, 48)
        font_small = pygame.font.Font(None, 32)

        center_x = self._screen_width // 2
        y = self._screen_height // 2 - 100

        text = font_large.render("GAME OVER", True, (255, 100, 100))
        screen.blit(text, (center_x - text.get_width() // 2, y))
        y += 80

        # Final score
        text = font_medium.render(f"Final Score: {self._score}", True, (255, 255, 255))
        screen.blit(text, (center_x - text.get_width() // 2, y))
        y += 50

        # Stats
        if self._hits > 0:
            avg_mult = self._total_hit_value / self._hits
            text = font_small.render(f"Hits: {self._hits}  Avg Multiplier: {avg_mult:.1f}x", True, (200, 200, 200))
            screen.blit(text, (center_x - text.get_width() // 2, y))
            y += 35

        text = font_small.render(f"Misses: {self._misses}  Expired: {self._expired}", True, (200, 200, 200))
        screen.blit(text, (center_x - text.get_width() // 2, y))
        y += 50

        # Best score
        if self._score >= self._session_best and self._session_best > 0:
            text = font_medium.render("NEW HIGH SCORE!", True, (255, 255, 100))
            screen.blit(text, (center_x - text.get_width() // 2, y))
            y += 50

        # Restart prompt
        text = font_small.render("Click to play again", True, (150, 150, 150))
        screen.blit(text, (center_x - text.get_width() // 2, y + 30))
