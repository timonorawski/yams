"""Containment Game Mode.

Adversarial containment game where a ball tries to escape through gaps.
Player places deflectors to build walls and contain the ball.
Direct hits on the ball are penalized (it speeds up).
"""
from typing import List, Optional, Tuple

import pygame

from models import Vector2D
from games.common import GameState
from games.common.base_game import BaseGame
from games.Containment.ball import Ball, create_ball
from games.Containment.deflector import DeflectorManager
from games.Containment.gap import GapManager
from games.Containment import config


class ContainmentMode(BaseGame):
    """Containment game mode - adversarial geometry building.

    Core loop:
    1. Ball bounces around, seeking escape through gaps
    2. Player places deflectors by shooting
    3. Ball reflects off deflectors
    4. Direct hits on ball = speed penalty
    5. Ball escaping through gap = game over
    6. Survive time limit = win
    """

    # Game metadata
    NAME = "Containment"
    DESCRIPTION = "Build walls to contain the ball. Direct hits make it faster!"
    VERSION = "1.0.0"
    AUTHOR = "AMS Team"

    # CLI argument definitions
    ARGUMENTS = [
        # Pacing (standard AMS parameter)
        {
            'name': '--pacing',
            'type': str,
            'default': 'throwing',
            'help': 'Pacing preset: archery, throwing, blaster'
        },

        # Game-specific difficulty
        {
            'name': '--tempo',
            'type': str,
            'default': 'mid',
            'help': 'Tempo preset: zen, mid, wild (ball aggression)'
        },
        {
            'name': '--ai',
            'type': str,
            'default': 'dumb',
            'help': 'AI level: dumb, reactive, strategic'
        },

        # Game mode
        {
            'name': '--time-limit',
            'type': int,
            'default': 60,
            'help': 'Seconds to survive (0 = endless)'
        },
        {
            'name': '--gap-count',
            'type': int,
            'default': None,
            'help': 'Number of gaps (overrides preset)'
        },

        # Physical constraints (standard AMS parameters)
        {
            'name': '--max-deflectors',
            'type': int,
            'default': None,
            'help': 'Maximum deflectors allowed (None = unlimited)'
        },
    ]

    def __init__(
        self,
        # Pacing (device speed)
        pacing: str = 'throwing',
        # Tempo (game intensity)
        tempo: str = 'mid',
        # AI behavior
        ai: str = 'dumb',
        # Game mode
        time_limit: int = 60,
        gap_count: Optional[int] = None,
        # Physical constraints
        max_deflectors: Optional[int] = None,
        quiver_size: Optional[int] = None,
        retrieval_pause: int = 30,
        # Palette
        color_palette: Optional[List[Tuple[int, int, int]]] = None,
        palette_name: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the containment game.

        Args:
            pacing: Device pacing preset (archery, throwing, blaster)
            tempo: Game intensity preset (zen, mid, wild)
            ai: AI behavior level (dumb, reactive, strategic)
            time_limit: Seconds to survive (0 = endless)
            gap_count: Number of gaps (None = use preset)
            max_deflectors: Maximum deflectors allowed (None = unlimited)
            quiver_size: Shots before retrieval (None = use preset)
            retrieval_pause: Seconds for retrieval (0 = manual)
            color_palette: AMS-provided color palette
            palette_name: Test palette name for standalone mode
        """
        # Load presets
        self._pacing = config.get_pacing_preset(pacing)
        self._tempo = config.get_tempo_preset(tempo)
        self._ai_level = ai

        # Calculate effective parameters
        self._ball_speed = self._pacing.ball_speed * self._tempo.ball_speed_multiplier
        self._gap_count = gap_count if gap_count is not None else max(
            1, self._pacing.gap_count + self._tempo.gap_count_modifier
        )
        self._time_limit = time_limit
        self._max_deflectors = max_deflectors

        # Quiver (use preset default if not specified)
        effective_quiver = quiver_size if quiver_size is not None else self._pacing.quiver_size

        # Initialize base game (handles palette and quiver)
        super().__init__(
            color_palette=color_palette,
            palette_name=palette_name,
            quiver_size=effective_quiver if effective_quiver > 0 else None,
            retrieval_pause=retrieval_pause,
            **kwargs,
        )

        # Screen dimensions (updated on first render)
        self._screen_width = config.SCREEN_WIDTH
        self._screen_height = config.SCREEN_HEIGHT

        # Game state
        self._state = GameState.PLAYING
        self._time_elapsed = 0.0
        self._score = 0

        # Entities
        self._ball: Optional[Ball] = None
        self._deflectors: Optional[DeflectorManager] = None
        self._gaps: Optional[GapManager] = None

        # Initialize game
        self._init_game()

    def _get_internal_state(self) -> GameState:
        """Map internal state to standard GameState (required by BaseGame).

        Returns:
            GameState.PLAYING, GameState.GAME_OVER, or GameState.WON
        """
        return self._state

    def _init_game(self) -> None:
        """Initialize or reset game entities."""
        # Create ball
        ball_color = self._palette.random_target_color()
        self._ball = create_ball(
            screen_width=self._screen_width,
            screen_height=self._screen_height,
            base_speed=self._ball_speed,
            radius=self._pacing.ball_radius,
            color=ball_color,
        )

        # Create deflector manager
        self._deflectors = DeflectorManager(
            default_length=self._pacing.deflector_length
        )
        deflector_color = self._palette.get_ui_color()
        self._deflectors.default_color = deflector_color

        # Create gap manager
        self._gaps = GapManager(
            screen_width=self._screen_width,
            screen_height=self._screen_height,
            gap_width=self._pacing.gap_width,
        )
        self._gaps.create_gaps(self._gap_count)

        # Reset state
        self._state = GameState.PLAYING
        self._time_elapsed = 0.0

    def get_score(self) -> int:
        """Get current score (time survived in seconds)."""
        return int(self._time_elapsed)

    def handle_input(self, events: List) -> None:
        """Process input events (shots).

        Args:
            events: List of InputEvent objects
        """
        if self._state not in (GameState.PLAYING,) and self.state != GameState.RETRIEVAL:
            return

        for event in events:
            if self.state == GameState.RETRIEVAL:
                # Any input during retrieval ends it (manual ready)
                self._end_retrieval()
                continue

            position = event.position

            # Check for direct hit on ball (penalty)
            if self._ball and self._ball.is_point_inside(position, config.HIT_TOLERANCE):
                self._ball.apply_speed_penalty(config.HIT_SPEED_MULTIPLIER)
                # Still place deflector, but ball is faster now
                # Could optionally skip placement as additional penalty

            # Place deflector
            if self._deflectors is not None:
                # Check max deflectors limit
                if self._max_deflectors and self._deflectors.count >= self._max_deflectors:
                    continue

                self._deflectors.add_deflector(position)

            # Check quiver
            if self._use_shot():
                self._start_retrieval()

    def update(self, dt: float) -> None:
        """Update game state.

        Args:
            dt: Delta time in seconds since last update
        """
        # Handle retrieval state (BaseGame manages _in_retrieval flag)
        if self.state == GameState.RETRIEVAL:
            # Update retrieval timer
            if self._update_retrieval(dt):
                self._end_retrieval()
            return

        if self._state != GameState.PLAYING:
            return

        if self._ball is None or self._gaps is None:
            return

        # Update time
        self._time_elapsed += dt

        # Check time limit
        if self._time_limit > 0 and self._time_elapsed >= self._time_limit:
            self._state = GameState.WON
            self._score = int(self._time_elapsed)
            return

        # Update ball position
        self._ball.update(dt)

        # Check wall collisions
        wall_hit = self._gaps.check_wall_collision(
            self._ball.position,
            self._ball.radius,
            self._ball.velocity
        )
        if wall_hit == 'horizontal':
            self._ball.bounce_off_horizontal()
            # Clamp position to screen
            self._clamp_ball_position()
        elif wall_hit == 'vertical':
            self._ball.bounce_off_vertical()
            self._clamp_ball_position()

        # Check deflector collisions
        if self._deflectors:
            collision = self._deflectors.check_ball_collision(
                self._ball.position,
                self._ball.radius
            )
            if collision:
                normal, penetration = collision
                self._ball.bounce_off_surface(normal, push_out=penetration)

        # Check escape
        if self._gaps.check_escape(self._ball.position, self._ball.radius):
            self._state = GameState.GAME_OVER
            self._score = int(self._time_elapsed)

    def _clamp_ball_position(self) -> None:
        """Keep ball within screen bounds (except gaps)."""
        if self._ball is None:
            return

        x = max(self._ball.radius, min(
            self._screen_width - self._ball.radius,
            self._ball.position.x
        ))
        y = max(self._ball.radius, min(
            self._screen_height - self._ball.radius,
            self._ball.position.y
        ))
        self._ball.position = Vector2D(x=x, y=y)

    def render(self, screen: pygame.Surface) -> None:
        """Render the game.

        Args:
            screen: Pygame surface to render to
        """
        # Update screen dimensions
        self._screen_width, self._screen_height = screen.get_size()

        # Clear screen
        bg_color = self._palette.get_background_color()
        screen.fill(bg_color)

        # Draw walls (screen edges that aren't gaps)
        self._render_walls(screen)

        # Draw gaps (highlighted danger zones)
        self._render_gaps(screen)

        # Draw deflectors
        self._render_deflectors(screen)

        # Draw ball
        self._render_ball(screen)

        # Draw HUD
        self._render_hud(screen)

        # Draw state overlay
        if self._state in (GameState.GAME_OVER, GameState.WON, GameState.RETRIEVAL):
            self._render_overlay(screen)

    def _render_walls(self, screen: pygame.Surface) -> None:
        """Render screen edge walls."""
        wall_color = config.WALL_COLOR
        thickness = 3

        # Draw all four edges
        # Gaps will be drawn over these
        pygame.draw.rect(
            screen, wall_color,
            (0, 0, self._screen_width, thickness)
        )
        pygame.draw.rect(
            screen, wall_color,
            (0, self._screen_height - thickness, self._screen_width, thickness)
        )
        pygame.draw.rect(
            screen, wall_color,
            (0, 0, thickness, self._screen_height)
        )
        pygame.draw.rect(
            screen, wall_color,
            (self._screen_width - thickness, 0, thickness, self._screen_height)
        )

    def _render_gaps(self, screen: pygame.Surface) -> None:
        """Render gaps as highlighted openings."""
        if self._gaps is None:
            return

        gap_color = config.GAP_COLOR
        thickness = 6

        for gap in self._gaps.gaps:
            start, end = gap.get_render_line()
            pygame.draw.line(screen, gap_color, start, end, thickness)

    def _render_deflectors(self, screen: pygame.Surface) -> None:
        """Render all placed deflectors."""
        if self._deflectors is None:
            return

        for deflector in self._deflectors.deflectors:
            start, end = deflector.get_line_points()
            pygame.draw.line(screen, deflector.color, start, end, 4)
            # Draw small circles at endpoints
            pygame.draw.circle(screen, deflector.color, start, 4)
            pygame.draw.circle(screen, deflector.color, end, 4)

    def _render_ball(self, screen: pygame.Surface) -> None:
        """Render the ball."""
        if self._ball is None:
            return

        pos = (int(self._ball.position.x), int(self._ball.position.y))
        pygame.draw.circle(screen, self._ball.color, pos, int(self._ball.radius))

        # Draw direction indicator
        import math
        vel_mag = math.sqrt(
            self._ball.velocity.x ** 2 + self._ball.velocity.y ** 2
        )
        if vel_mag > 0:
            indicator_len = self._ball.radius * 0.6
            end_x = pos[0] + int(self._ball.velocity.x / vel_mag * indicator_len)
            end_y = pos[1] + int(self._ball.velocity.y / vel_mag * indicator_len)
            pygame.draw.line(
                screen, config.BACKGROUND_COLOR,
                pos, (end_x, end_y), 2
            )

    def _render_hud(self, screen: pygame.Surface) -> None:
        """Render the heads-up display."""
        font = pygame.font.Font(None, 36)
        font_small = pygame.font.Font(None, 24)
        hud_color = self._palette.get_ui_color()

        y_offset = 20
        x_offset = 20

        # Time survived / remaining
        if self._time_limit > 0:
            remaining = max(0, self._time_limit - self._time_elapsed)
            time_text = f"Time: {remaining:.1f}s"
        else:
            time_text = f"Time: {self._time_elapsed:.1f}s"
        text = font.render(time_text, True, hud_color)
        screen.blit(text, (x_offset, y_offset))
        y_offset += 35

        # Ball speed multiplier (if penalized)
        if self._ball and self._ball.speed_multiplier > 1.0:
            speed_text = f"Ball Speed: {self._ball.speed_multiplier:.1f}x"
            speed_color = (255, 150, 100)  # Warning color
            text = font_small.render(speed_text, True, speed_color)
            screen.blit(text, (x_offset, y_offset))
            y_offset += 25

        # Deflector count
        if self._deflectors:
            defl_text = f"Deflectors: {self._deflectors.count}"
            if self._max_deflectors:
                defl_text += f" / {self._max_deflectors}"
            text = font_small.render(defl_text, True, hud_color)
            screen.blit(text, (x_offset, y_offset))
            y_offset += 25

        # Quiver status
        if self._quiver:
            quiver_text = f"Shots: {self._quiver.remaining} / {self._quiver.size}"
            text = font_small.render(quiver_text, True, hud_color)
            screen.blit(text, (x_offset, y_offset))
            y_offset += 25

        # Bounce count
        if self._ball:
            bounce_text = f"Bounces: {self._ball.bounce_count}"
            text = font_small.render(bounce_text, True, hud_color)
            screen.blit(text, (x_offset, y_offset))

        # Pacing/tempo indicator (top right)
        mode_text = f"{self._pacing.name} / {self._tempo.name}"
        text = font_small.render(mode_text, True, (150, 150, 150))
        screen.blit(text, (self._screen_width - text.get_width() - 20, 20))

    def _render_overlay(self, screen: pygame.Surface) -> None:
        """Render state overlay (game over, retrieval, etc)."""
        font_large = pygame.font.Font(None, 72)
        font_medium = pygame.font.Font(None, 36)

        # Semi-transparent overlay
        overlay = pygame.Surface((self._screen_width, self._screen_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        if self._state == GameState.ESCAPED:
            title = "ESCAPED!"
            subtitle = f"Survived: {self._score}s"
            title_color = config.GAP_COLOR
            hint = "Press R to restart"

        elif self._state == GameState.TIME_UP:
            title = "CONTAINED!"
            subtitle = f"Time: {self._score}s"
            title_color = (100, 255, 100)
            hint = "Press R to play again"

        elif self._state == GameState.RETRIEVAL:
            title = "RETRIEVAL"
            if self._quiver and self._quiver.retrieval_pause > 0:
                remaining = self._quiver.retrieval_timer
                subtitle = f"Resuming in {remaining:.1f}s"
            else:
                subtitle = "Press SPACE when ready"
            title_color = (200, 200, 100)
            hint = ""

        else:
            return

        # Draw title
        text = font_large.render(title, True, title_color)
        rect = text.get_rect(center=(self._screen_width // 2, self._screen_height // 2 - 40))
        screen.blit(text, rect)

        # Draw subtitle
        text = font_medium.render(subtitle, True, (200, 200, 200))
        rect = text.get_rect(center=(self._screen_width // 2, self._screen_height // 2 + 20))
        screen.blit(text, rect)

        # Draw hint
        if hint:
            text = font_medium.render(hint, True, (150, 150, 150))
            rect = text.get_rect(center=(self._screen_width // 2, self._screen_height // 2 + 70))
            screen.blit(text, rect)

    def reset(self) -> None:
        """Reset the game."""
        super().reset()  # Reset BaseGame state (quiver, retrieval)
        self._init_game()

    def _on_palette_changed(self) -> None:
        """Called when palette changes. Update entity colors."""
        # Update entity colors when palette changes
        if self._ball:
            self._ball.color = self._palette.random_target_color()
        if self._deflectors:
            self._deflectors.default_color = self._palette.get_ui_color()
