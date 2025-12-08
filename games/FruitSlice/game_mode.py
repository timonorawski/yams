"""
FruitSlice Game Mode

Fruit Ninja-style game with arcing targets, combo system,
bombs to avoid, and quiver/ammo support for physical devices.
"""
import time
from typing import List, Optional

import pygame

from models import Vector2D
from games.common import GameState
from games.common.input import InputEvent
from games.common.palette import GamePalette
from games.FruitSlice import config
from games.FruitSlice.target import ArcingTarget, TargetType
from games.FruitSlice.spawner import TargetSpawner


class ComboTracker:
    """Tracks combo multiplier based on rapid hits."""

    def __init__(self, combo_window: float):
        """Initialize combo tracker.

        Args:
            combo_window: Seconds before combo resets
        """
        self.combo_window = combo_window
        self.multiplier = 1
        self.hit_count = 0
        self.last_hit_time = 0.0

    def register_hit(self) -> int:
        """Register a hit and return current multiplier.

        Returns:
            Current combo multiplier
        """
        now = time.monotonic()

        # Check if combo is still active
        if now - self.last_hit_time <= self.combo_window:
            self.hit_count += 1
            self.multiplier = min(self.hit_count, config.MAX_COMBO_MULTIPLIER)
        else:
            # Combo expired, start fresh
            self.hit_count = 1
            self.multiplier = 1

        self.last_hit_time = now
        return self.multiplier

    def update(self) -> None:
        """Update combo state (check for expiration)."""
        now = time.monotonic()
        if self.multiplier > 1 and now - self.last_hit_time > self.combo_window:
            # Combo expired
            self.multiplier = 1
            self.hit_count = 0

    @property
    def is_active(self) -> bool:
        """Check if combo is currently active."""
        return self.multiplier > 1


class FruitSliceMode:
    """FruitSlice game mode - hit arcing targets, avoid bombs.

    Features:
    - Parabolic arc physics for targets
    - Combo multiplier for rapid hits
    - Bombs that end game or cost lives
    - Quiver mode for physical ammo constraints
    - Pacing presets for different input devices
    """

    def __init__(
        self,
        mode: str = 'classic',
        pacing: str = 'throwing',
        spawn_interval: Optional[float] = None,
        arc_duration: Optional[float] = None,
        max_targets: Optional[int] = None,
        target_size: Optional[int] = None,
        bomb_ratio: Optional[float] = None,
        no_bombs: bool = False,
        lives: int = 3,
        time_limit: Optional[int] = None,
        quiver_size: Optional[int] = None,
        retrieval_pause: int = 30,
        combo_window: Optional[float] = None,
        color_palette: Optional[List[tuple]] = None,
        palette_name: Optional[str] = None,
        **kwargs,
    ):
        """Initialize FruitSlice game.

        Args:
            mode: Game mode (classic, zen, arcade)
            pacing: Pacing preset (archery, throwing, blaster)
            spawn_interval: Override spawn interval
            arc_duration: Override arc duration
            max_targets: Override max simultaneous targets
            target_size: Override target radius
            bomb_ratio: Override bomb spawn ratio
            no_bombs: Disable bombs (zen mode)
            lives: Starting lives
            time_limit: Time limit in seconds (arcade mode)
            quiver_size: Shots per round before retrieval (None = unlimited)
            retrieval_pause: Seconds for retrieval between rounds
            combo_window: Override combo window duration
            color_palette: Optional list of RGB colors from AMS calibration
            palette_name: Optional test palette name (for standalone mode)
        """
        # Mode settings
        self._mode = mode
        self._no_bombs = no_bombs or mode == 'zen'
        self._time_limit = time_limit
        self._max_lives = lives

        # Quiver settings
        self._quiver_size = quiver_size
        self._retrieval_pause = retrieval_pause
        self._shots_this_round = 0
        self._current_round = 1

        # Palette settings
        self._palette = GamePalette(colors=color_palette, palette_name=palette_name)

        # Get combo window from preset if not specified
        if combo_window is None:
            from games.FruitSlice.config import PACING_PRESETS
            preset = PACING_PRESETS.get(pacing, PACING_PRESETS['throwing'])
            combo_window = preset.combo_window

        # Screen dimensions (set on first render)
        self._screen_width = config.SCREEN_WIDTH
        self._screen_height = config.SCREEN_HEIGHT

        # Game state
        self._state = GameState.PLAYING
        self._score = 0
        self._lives = lives
        self._targets: List[ArcingTarget] = []
        self._combo = ComboTracker(combo_window)
        self._escaped_count = 0  # Fruits that escaped

        # Spawner
        self._spawner: Optional[TargetSpawner] = None
        self._pacing = pacing
        self._spawn_interval = spawn_interval
        self._arc_duration = arc_duration
        self._max_targets = max_targets
        self._target_size = target_size
        self._bomb_ratio = bomb_ratio

        # Stats
        self._hits = 0
        self._misses = 0
        self._bombs_hit = 0
        self._max_combo = 1
        self._multi_hits = 0  # Times hit multiple targets with one shot
        self._best_multi_hit = 0  # Most targets hit with one shot

        # Timing
        self._start_time = time.monotonic()
        self._retrieval_start_time: Optional[float] = None

        # Visual effects
        self._hit_effects: List[dict] = []
        self._bomb_effects: List[dict] = []

        # Session tracking
        self._session_best = 0
        self._games_played = 0

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
                pacing=self._pacing,
                spawn_interval=self._spawn_interval,
                arc_duration=self._arc_duration,
                max_targets=self._max_targets,
                target_size=self._target_size,
                bomb_ratio=self._bomb_ratio,
                no_bombs=self._no_bombs,
                fruit_colors=self._palette.get_target_colors(),
            )

    def _restart(self) -> None:
        """Restart the game."""
        if self._score > self._session_best:
            self._session_best = self._score
        self._games_played += 1

        self._state = GameState.PLAYING
        self._score = 0
        self._lives = self._max_lives
        self._targets = []
        self._escaped_count = 0
        self._shots_this_round = 0
        self._current_round = 1

        self._hits = 0
        self._misses = 0
        self._bombs_hit = 0
        self._max_combo = 1
        self._multi_hits = 0
        self._best_multi_hit = 0

        self._combo = ComboTracker(self._combo.combo_window)

        if self._spawner:
            self._spawner.reset()

        self._start_time = time.monotonic()
        self._hit_effects = []
        self._bomb_effects = []

    def _start_retrieval(self) -> None:
        """Enter retrieval pause state."""
        self._state = GameState.RETRIEVAL
        self._retrieval_start_time = time.monotonic()
        self._targets = []  # Clear remaining targets

    def _end_retrieval(self) -> None:
        """End retrieval pause, start new round."""
        self._state = GameState.PLAYING
        self._shots_this_round = 0
        self._current_round += 1
        self._retrieval_start_time = None

        # Increase difficulty for new round
        if self._spawner:
            self._spawner.update_difficulty()

    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events."""
        for event in events:
            self._handle_shot(event.position)

    def _handle_shot(self, position: Vector2D) -> None:
        """Handle a shot at position.

        Checks ALL targets that overlap with the hit position.
        Hitting multiple targets with one shot gives a multi-hit bonus!
        """
        if self._state == GameState.GAME_OVER:
            self._restart()
            return

        if self._state == GameState.RETRIEVAL:
            # Any click ends retrieval (manual ready)
            if self._retrieval_pause == 0:
                self._end_retrieval()
            return

        # Check ALL targets that overlap with hit position
        hit_targets = []
        hit_bomb = None
        for target in self._targets:
            if target.is_active and target.contains_point(position.x, position.y):
                if target.is_bomb:
                    hit_bomb = target
                else:
                    hit_targets.append(target)

        # Process bomb hit (takes priority - ends combo, costs life)
        if hit_bomb:
            hit_bomb.mark_hit()
            self._bombs_hit += 1
            self._lives -= 1

            self._bomb_effects.append({
                'position': Vector2D(x=hit_bomb.x, y=hit_bomb.y),
                'time': time.monotonic(),
            })

            if self._lives <= 0:
                self._state = GameState.GAME_OVER

        # Process fruit hits (can hit multiple!)
        elif hit_targets:
            num_hits = len(hit_targets)
            self._hits += num_hits

            # Track multi-hit stats
            if num_hits > 1:
                self._multi_hits += 1
                if num_hits > self._best_multi_hit:
                    self._best_multi_hit = num_hits

            # Calculate multi-hit bonus multiplier
            # 1 target = 1x, 2 targets = 2x, 3 targets = 4x, 4 targets = 8x
            multi_hit_bonus = 1.0
            if num_hits > 1:
                multi_hit_bonus = config.MULTI_HIT_MULTIPLIER ** (num_hits - 1)

            # Get combo multiplier (one combo increment per shot, not per target)
            combo_multiplier = self._combo.register_hit()
            if combo_multiplier > self._max_combo:
                self._max_combo = combo_multiplier

            # Score all hit targets
            total_points = 0
            for target in hit_targets:
                target.mark_hit()
                base_points = target.points
                points = int(base_points * combo_multiplier * multi_hit_bonus)
                total_points += points

                self._hit_effects.append({
                    'position': Vector2D(x=target.x, y=target.y),
                    'time': time.monotonic(),
                    'points': points,
                    'multiplier': combo_multiplier,
                    'multi_hit': num_hits if num_hits > 1 else 0,
                    'color': target.color,
                })

            self._score += total_points

            # Show multi-hit celebration effect
            if num_hits > 1:
                # Add a centered multi-hit effect
                avg_x = sum(t.x for t in hit_targets) / num_hits
                avg_y = sum(t.y for t in hit_targets) / num_hits
                self._hit_effects.append({
                    'position': Vector2D(x=avg_x, y=avg_y),
                    'time': time.monotonic(),
                    'points': total_points,
                    'multiplier': combo_multiplier,
                    'multi_hit': num_hits,
                    'color': (255, 255, 100),  # Gold for multi-hit
                    'is_multi_hit_banner': True,
                })
        else:
            # Miss - clicked empty space
            self._misses += 1

        # Track shots for quiver mode
        self._shots_this_round += 1
        if self._quiver_size and self._shots_this_round >= self._quiver_size:
            self._start_retrieval()

    def update(self, dt: float) -> None:
        """Update game state."""
        if self._state == GameState.GAME_OVER:
            return

        if self._state == GameState.RETRIEVAL:
            # Check if auto-resume timer expired
            if self._retrieval_pause > 0 and self._retrieval_start_time:
                elapsed = time.monotonic() - self._retrieval_start_time
                if elapsed >= self._retrieval_pause:
                    self._end_retrieval()
            return

        self._ensure_spawner()

        # Update difficulty
        if self._spawner:
            self._spawner.update_difficulty()

        # Update combo tracker
        self._combo.update()

        # Update all targets
        for target in self._targets:
            target.update(dt, config.GRAVITY)

        # Check for escaped targets (off-screen)
        for target in self._targets:
            if not target.hit and target.is_off_screen(self._screen_width, self._screen_height):
                if not target.is_bomb:
                    # Fruit escaped
                    self._escaped_count += 1
                    if self._escaped_count >= config.MISS_TOLERANCE:
                        self._lives -= 1
                        self._escaped_count = 0
                        if self._lives <= 0:
                            self._state = GameState.GAME_OVER
                target.hit = True  # Mark as done

        # Remove inactive targets
        self._targets = [t for t in self._targets if t.is_active and not t.is_off_screen(self._screen_width, self._screen_height)]

        # Spawn new targets
        if self._spawner and self._spawner.should_spawn(len(self._targets)):
            self._targets.append(self._spawner.spawn())

        # Check time limit (arcade mode)
        if self._time_limit:
            elapsed = time.monotonic() - self._start_time
            if elapsed >= self._time_limit:
                self._state = GameState.GAME_OVER

        # Clean up old effects
        now = time.monotonic()
        self._hit_effects = [e for e in self._hit_effects if now - e['time'] < 1.0]
        self._bomb_effects = [e for e in self._bomb_effects if now - e['time'] < 0.5]

    def render(self, screen: pygame.Surface) -> None:
        """Render the game."""
        self._screen_width, self._screen_height = screen.get_size()
        if self._spawner:
            self._spawner.screen_width = self._screen_width
            self._spawner.screen_height = self._screen_height

        screen.fill(config.BACKGROUND_COLOR)

        # Draw targets
        self._render_targets(screen)

        # Draw effects
        self._render_effects(screen)

        # Draw HUD
        self._render_hud(screen)

        # Draw retrieval screen
        if self._state == GameState.RETRIEVAL:
            self._render_retrieval(screen)

        # Draw game over
        if self._state == GameState.GAME_OVER:
            self._render_game_over(screen)

    def _render_targets(self, screen: pygame.Surface) -> None:
        """Render all targets."""
        for target in self._targets:
            if not target.is_active:
                continue

            center = (int(target.x), int(target.y))
            radius = int(target.radius)

            # Draw trail
            if len(target.trail) > 1:
                for i, (tx, ty) in enumerate(target.trail):
                    alpha = int(100 * (i / len(target.trail)))
                    trail_radius = int(radius * 0.3 * (i / len(target.trail)))
                    if trail_radius > 0:
                        surf = pygame.Surface((trail_radius * 2 + 2, trail_radius * 2 + 2), pygame.SRCALPHA)
                        color = (*target.color[:3], alpha)
                        pygame.draw.circle(surf, color, (trail_radius + 1, trail_radius + 1), trail_radius)
                        screen.blit(surf, (int(tx) - trail_radius - 1, int(ty) - trail_radius - 1))

            # Draw target
            if target.is_bomb:
                # Bomb: dark circle with red glow
                pygame.draw.circle(screen, config.BOMB_GLOW_COLOR, center, radius + 4)
                pygame.draw.circle(screen, config.BOMB_COLOR, center, radius)
                # Fuse/warning symbol
                pygame.draw.line(screen, config.BOMB_GLOW_COLOR,
                                 (center[0], center[1] - radius + 5),
                                 (center[0], center[1] - radius - 10), 3)
            else:
                # Fruit: colored circle with highlight
                pygame.draw.circle(screen, target.color, center, radius)

                # Highlight
                highlight_offset = int(radius * 0.3)
                highlight_radius = int(radius * 0.25)
                highlight_color = (
                    min(255, target.color[0] + 80),
                    min(255, target.color[1] + 80),
                    min(255, target.color[2] + 80),
                )
                pygame.draw.circle(screen, highlight_color,
                                   (center[0] - highlight_offset, center[1] - highlight_offset),
                                   highlight_radius)

                # Golden glow for golden fruit
                if target.target_type == TargetType.GOLDEN:
                    glow_surf = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, (255, 215, 0, 50), (radius * 1.5, radius * 1.5), radius * 1.4)
                    screen.blit(glow_surf, (center[0] - radius * 1.5, center[1] - radius * 1.5))

    def _render_effects(self, screen: pygame.Surface) -> None:
        """Render visual effects."""
        now = time.monotonic()

        # Hit effects
        for effect in self._hit_effects:
            age = now - effect['time']

            # Expanding ring
            if age < 0.3:
                progress = age / 0.3
                radius = int(30 + 40 * progress)
                alpha = int(200 * (1 - progress))

                surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                color = (*effect['color'][:3], alpha)
                pygame.draw.circle(surf, color, (radius + 2, radius + 2), radius, 4)
                screen.blit(surf, (
                    int(effect['position'].x) - radius - 2,
                    int(effect['position'].y) - radius - 2
                ))

            # Floating points
            if age < 1.0:
                progress = age / 1.0
                y_offset = int(-60 * progress)
                alpha = int(255 * (1 - progress * 0.7))

                # Multi-hit banner (special treatment)
                if effect.get('is_multi_hit_banner'):
                    font = pygame.font.Font(None, 48)
                    text_str = f"MULTI-HIT x{effect['multi_hit']}! +{effect['points']}"
                    text = font.render(text_str, True, (255, 255, 100))
                    text.set_alpha(alpha)
                    screen.blit(text, (
                        int(effect['position'].x) - text.get_width() // 2,
                        int(effect['position'].y) + y_offset - 40
                    ))
                else:
                    font = pygame.font.Font(None, 36)
                    if effect.get('multi_hit', 0) > 1:
                        text_str = f"+{effect['points']}"
                    elif effect['multiplier'] > 1:
                        text_str = f"+{effect['points']} ({effect['multiplier']}x)"
                    else:
                        text_str = f"+{effect['points']}"
                    text = font.render(text_str, True, effect['color'])
                    text.set_alpha(alpha)
                    screen.blit(text, (
                        int(effect['position'].x) - text.get_width() // 2,
                        int(effect['position'].y) + y_offset
                    ))

        # Bomb effects
        for effect in self._bomb_effects:
            age = now - effect['time']
            if age < 0.5:
                progress = age / 0.5
                radius = int(50 + 100 * progress)
                alpha = int(200 * (1 - progress))

                surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 100, 50, alpha), (radius + 2, radius + 2), radius)
                pygame.draw.circle(surf, (255, 200, 100, alpha // 2), (radius + 2, radius + 2), radius // 2)
                screen.blit(surf, (
                    int(effect['position'].x) - radius - 2,
                    int(effect['position'].y) - radius - 2
                ))

    def _render_hud(self, screen: pygame.Surface) -> None:
        """Render heads-up display."""
        font_large = pygame.font.Font(None, 48)
        font_medium = pygame.font.Font(None, 32)
        font_small = pygame.font.Font(None, 24)

        y = 20
        x = 20

        # Score
        text = font_large.render(f"Score: {self._score}", True, (255, 255, 255))
        screen.blit(text, (x, y))
        y += 50

        # Lives
        lives_text = "Lives: " + "O " * self._lives + "X " * (self._max_lives - self._lives)
        color = (255, 100, 100) if self._lives <= 1 else (200, 200, 200)
        text = font_medium.render(lives_text.strip(), True, color)
        screen.blit(text, (x, y))
        y += 35

        # Combo (center of screen, large when active)
        if self._combo.is_active:
            combo_font = pygame.font.Font(None, 72)
            combo_text = f"{self._combo.multiplier}x COMBO"
            text = combo_font.render(combo_text, True, (255, 200, 50))
            text_rect = text.get_rect(center=(self._screen_width // 2, 80))
            screen.blit(text, text_rect)

        # Quiver info (if in quiver mode)
        if self._quiver_size:
            remaining = self._quiver_size - self._shots_this_round
            quiver_text = f"Arrows: {remaining}/{self._quiver_size}  Round: {self._current_round}"
            text = font_medium.render(quiver_text, True, (150, 200, 255))
            screen.blit(text, (self._screen_width - text.get_width() - 20, 20))

        # Time remaining (arcade mode)
        if self._time_limit:
            elapsed = time.monotonic() - self._start_time
            remaining = max(0, self._time_limit - elapsed)
            time_text = f"Time: {remaining:.1f}s"
            color = (255, 100, 100) if remaining < 10 else (200, 200, 200)
            text = font_medium.render(time_text, True, color)
            screen.blit(text, (self._screen_width - text.get_width() - 20, 55))

        # Session best (top right)
        if self._session_best > 0:
            text = font_small.render(f"Best: {self._session_best}", True, (100, 200, 255))
            screen.blit(text, (self._screen_width - text.get_width() - 20, self._screen_height - 30))

        # Mode indicator
        mode_text = f"{self._pacing.upper()} pacing"
        if self._no_bombs:
            mode_text += " | ZEN"
        text = font_small.render(mode_text, True, (100, 100, 100))
        screen.blit(text, (x, self._screen_height - 30))

    def _render_retrieval(self, screen: pygame.Surface) -> None:
        """Render retrieval pause overlay."""
        # Semi-transparent overlay
        overlay = pygame.Surface((self._screen_width, self._screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        font_large = pygame.font.Font(None, 64)
        font_medium = pygame.font.Font(None, 36)

        center_x = self._screen_width // 2
        y = self._screen_height // 2 - 60

        # Title
        text = font_large.render("RETRIEVAL TIME", True, (255, 255, 100))
        screen.blit(text, (center_x - text.get_width() // 2, y))
        y += 70

        # Round info
        text = font_medium.render(f"Round {self._current_round} complete!", True, (200, 200, 200))
        screen.blit(text, (center_x - text.get_width() // 2, y))
        y += 50

        # Countdown or manual prompt
        if self._retrieval_pause > 0 and self._retrieval_start_time:
            elapsed = time.monotonic() - self._retrieval_start_time
            remaining = max(0, self._retrieval_pause - elapsed)
            text = font_medium.render(f"Next round in {remaining:.0f}s...", True, (150, 150, 150))
        else:
            text = font_medium.render("Click when ready to continue", True, (150, 255, 150))
        screen.blit(text, (center_x - text.get_width() // 2, y))

    def _render_game_over(self, screen: pygame.Surface) -> None:
        """Render game over overlay."""
        overlay = pygame.Surface((self._screen_width, self._screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        font_large = pygame.font.Font(None, 72)
        font_medium = pygame.font.Font(None, 48)
        font_small = pygame.font.Font(None, 32)

        center_x = self._screen_width // 2
        y = self._screen_height // 2 - 120

        # Game over
        text = font_large.render("GAME OVER", True, (255, 100, 100))
        screen.blit(text, (center_x - text.get_width() // 2, y))
        y += 80

        # Final score
        text = font_medium.render(f"Final Score: {self._score}", True, (255, 255, 255))
        screen.blit(text, (center_x - text.get_width() // 2, y))
        y += 50

        # Stats
        stats_line1 = f"Hits: {self._hits}  Max Combo: {self._max_combo}x"
        if self._multi_hits > 0:
            stats_line1 += f"  Multi-hits: {self._multi_hits}"
        text = font_small.render(stats_line1, True, (200, 200, 200))
        screen.blit(text, (center_x - text.get_width() // 2, y))
        y += 35

        stats_line2 = f"Bombs Hit: {self._bombs_hit}  Misses: {self._misses}"
        if self._best_multi_hit > 1:
            stats_line2 += f"  Best Multi: {self._best_multi_hit}x"
        text = font_small.render(stats_line2, True, (200, 200, 200))
        screen.blit(text, (center_x - text.get_width() // 2, y))
        y += 50

        # High score
        if self._score >= self._session_best and self._session_best > 0:
            text = font_medium.render("NEW HIGH SCORE!", True, (255, 255, 100))
            screen.blit(text, (center_x - text.get_width() // 2, y))
            y += 50

        # Restart prompt
        text = font_small.render("Click to play again", True, (150, 150, 150))
        screen.blit(text, (center_x - text.get_width() // 2, y + 30))

    def set_palette(self, palette_name: str) -> str:
        """Switch to a named test palette.

        Args:
            palette_name: Name from TEST_PALETTES

        Returns:
            New palette name
        """
        if self._palette.set_palette(palette_name):
            # Update spawner if it exists
            if self._spawner:
                self._spawner.set_fruit_colors(self._palette.get_target_colors())
            return palette_name
        return self._palette.name

    def cycle_palette(self) -> str:
        """Cycle to next test palette.

        Returns:
            Name of new palette
        """
        new_name = self._palette.cycle_palette()
        # Update spawner if it exists
        if self._spawner:
            self._spawner.set_fruit_colors(self._palette.get_target_colors())
        return new_name

    @property
    def palette_name(self) -> str:
        """Current palette name."""
        return self._palette.name
