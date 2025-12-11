"""
Grouping Game Mode

Precision training game that measures shot grouping in real-time.
The target shrinks as you demonstrate consistency, ending when you miss.
"""
import math
import random
from enum import Enum
from typing import List, Optional

import pygame

from models import Vector2D
from ams.games import GameState
from ams.games.base_game import BaseGame
from games.Grouping.input.input_event import InputEvent
from games.Grouping import config
from games.Grouping.grouping_round import GroupingRound, GroupingMethod


class _InternalState(Enum):
    """Internal states for Grouping game flow."""
    WAITING = "waiting"        # Waiting for first shot to start round
    PLAYING = "playing"        # Active round in progress
    ROUND_OVER = "round_over"  # Round ended, showing results


class GroupingMode(BaseGame):
    """Grouping game mode - precision training through shot grouping.

    The game flow:
    1. Target appears at random position (WAITING state)
    2. First hit starts the round (PLAYING state)
    3. Each hit inside target: record position, recalculate group, shrink target
    4. Hit outside target: round ends (ROUND_OVER state)
    5. Press R or click to start new round

    Score is the smallest group diameter achieved.
    """

    # Game metadata
    NAME = "Grouping"
    DESCRIPTION = "Precision training - shrink the target by tightening your group."
    VERSION = "1.0.0"
    AUTHOR = "AMS Team"

    # CLI argument definitions
    ARGUMENTS = [
        {
            'name': '--method',
            'type': str,
            'default': 'centroid',
            'help': 'Grouping method: centroid, fixed (center+radius), or origin (fixed center, set radius)'
        },
        {
            'name': '--initial-radius',
            'type': int,
            'default': None,
            'help': 'Initial target radius in pixels'
        },
        {
            'name': '--min-radius',
            'type': int,
            'default': None,
            'help': 'Minimum target radius (smallest possible)'
        },
    ]

    def __init__(
        self,
        initial_radius: Optional[int] = None,
        min_radius: Optional[int] = None,
        group_margin: Optional[float] = None,
        method: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the grouping game.

        Args:
            initial_radius: Starting target radius (pixels)
            min_radius: Minimum target radius
            group_margin: Multiplier for group radius calculation
            method: Grouping method - 'centroid' or 'fixed_center'
        """
        # Initialize base class (handles palette and quiver)
        super().__init__(**kwargs)

        self._initial_radius = initial_radius or config.INITIAL_TARGET_RADIUS
        self._min_radius = min_radius or config.MIN_TARGET_RADIUS
        self._group_margin = group_margin or config.GROUP_MARGIN

        # Parse method
        if method is None:
            self._method = GroupingMethod.CENTROID
        elif method.lower() in ('fixed', 'fixed_center'):
            self._method = GroupingMethod.FIXED_CENTER
        elif method.lower() in ('origin', 'fixed_origin'):
            self._method = GroupingMethod.FIXED_ORIGIN
        else:
            self._method = GroupingMethod.CENTROID

        self._internal_state = _InternalState.WAITING
        self._current_round: Optional[GroupingRound] = None
        self._session_best: Optional[float] = None
        self._rounds_completed = 0
        self._total_hits = 0

        # Animation state
        self._display_radius = float(self._initial_radius)
        self._display_center: Optional[Vector2D] = None
        self._target_radius = float(self._initial_radius)
        self._target_center: Optional[Vector2D] = None

        # Screen dimensions (set on first render)
        self._screen_width = config.SCREEN_WIDTH
        self._screen_height = config.SCREEN_HEIGHT

        # Start first round
        self._start_new_round()

    def _get_internal_state(self) -> GameState:
        """Map internal state to standard GameState.

        Returns:
            GameState.PLAYING - Grouping is an endless game
        """
        # Map internal state to standard GameState
        # Grouping is endless, so it's always PLAYING unless explicitly ended
        return GameState.PLAYING

    def get_score(self) -> int:
        """Get current score (best group diameter in pixels, lower is better).

        Returns integer for compatibility with game protocol.
        """
        if self._session_best is None:
            return 0
        # Return as integer pixels, inverted so higher looks "better"
        # Actually, for grouping smaller is better, so we return diameter
        return int(self._session_best)

    def _start_new_round(self) -> None:
        """Initialize a new round with random target position."""
        # Random position with margin from edges
        margin = self._initial_radius + 50
        x = random.randint(margin, self._screen_width - margin)
        y = random.randint(margin, self._screen_height - margin)

        center = Vector2D(x=float(x), y=float(y))

        self._current_round = GroupingRound(
            target_center=center,
            initial_radius=float(self._initial_radius),
            method=self._method,
            group_margin=self._group_margin,
        )

        self._target_center = center
        self._target_radius = float(self._initial_radius)
        self._display_center = center
        self._display_radius = float(self._initial_radius)

        self._internal_state = _InternalState.WAITING

    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events.

        Args:
            events: List of input events from the input manager
        """
        for event in events:
            self._handle_hit(event.position)

    def _handle_hit(self, position: Vector2D) -> None:
        """Handle a hit at the given position."""
        if self._current_round is None:
            return

        if self._internal_state == _InternalState.WAITING:
            # First hit starts the round
            if self._current_round.is_inside_target(position):
                self._current_round.add_hit(position)
                self._internal_state = _InternalState.PLAYING
                self._update_target()

        elif self._internal_state == _InternalState.PLAYING:
            if self._current_round.is_inside_target(position):
                # Successful hit - record and recalculate
                self._current_round.add_hit(position)
                self._total_hits += 1
                self._update_target()
            else:
                # Miss - end round
                self._end_round(position)

        elif self._internal_state == _InternalState.ROUND_OVER:
            # Any click starts new round
            self._start_new_round()

    def _update_target(self) -> None:
        """Update target position and size based on current group."""
        if self._current_round is None:
            return

        # Get new target parameters from round
        new_center = self._current_round.current_center
        new_radius = self._current_round.current_radius

        # Enforce minimum radius
        new_radius = max(new_radius, float(self._min_radius))

        # Set target (animation will interpolate)
        self._target_center = new_center
        self._target_radius = new_radius

    def _end_round(self, miss_position: Vector2D) -> None:
        """End the current round with a miss."""
        if self._current_round is None:
            return

        self._current_round.end_round(miss_position)
        self._internal_state = _InternalState.ROUND_OVER
        self._rounds_completed += 1

        # Update session best (smaller is better)
        final_diameter = self._current_round.group_diameter
        if self._session_best is None or final_diameter < self._session_best:
            self._session_best = final_diameter

    def update(self, dt: float) -> None:
        """Update game state.

        Args:
            dt: Delta time in seconds since last update
        """
        # Animate target position and size
        if self._target_center and self._display_center:
            lerp_speed = 1.0 - math.pow(0.01, dt / config.ANIMATION_DURATION)

            # Interpolate center
            self._display_center = Vector2D(
                x=self._display_center.x + (self._target_center.x - self._display_center.x) * lerp_speed,
                y=self._display_center.y + (self._target_center.y - self._display_center.y) * lerp_speed,
            )

            # Interpolate radius
            self._display_radius += (self._target_radius - self._display_radius) * lerp_speed

    def render(self, screen: pygame.Surface) -> None:
        """Render the game.

        Args:
            screen: Pygame surface to render to
        """
        # Update screen dimensions
        self._screen_width, self._screen_height = screen.get_size()

        # Clear screen - use palette background if available
        bg_color = self._palette.get_background_color() if len(self._palette.colors) > 0 else config.BACKGROUND_COLOR
        screen.fill(bg_color)

        if self._current_round is None or self._display_center is None:
            return

        center_x = int(self._display_center.x)
        center_y = int(self._display_center.y)
        radius = int(self._display_radius)

        # Draw ghost ring (initial size)
        if config.SHOW_GHOST_RING and self._internal_state != _InternalState.WAITING:
            pygame.draw.circle(
                screen,
                config.GHOST_RING_COLOR,
                (int(self._current_round.target_center.x),
                 int(self._current_round.target_center.y)),
                int(self._current_round.initial_radius),
                2
            )

        # Draw target ring - use palette UI color
        target_color = self._palette.get_ui_color() if len(self._palette.colors) > 0 else config.TARGET_COLOR
        if self._internal_state == _InternalState.ROUND_OVER:
            target_color = config.MISS_MARKER_COLOR
        pygame.draw.circle(screen, target_color, (center_x, center_y), radius, 3)

        # Draw crosshair at center
        cross_size = 10
        pygame.draw.line(
            screen, target_color,
            (center_x - cross_size, center_y),
            (center_x + cross_size, center_y), 1
        )
        pygame.draw.line(
            screen, target_color,
            (center_x, center_y - cross_size),
            (center_x, center_y + cross_size), 1
        )

        # Draw hit markers
        if config.SHOW_HIT_MARKERS:
            for hit in self._current_round.hits:
                pygame.draw.circle(
                    screen,
                    config.HIT_MARKER_COLOR,
                    (int(hit.x), int(hit.y)),
                    5
                )

        # Draw miss marker
        if self._current_round.miss_position:
            miss = self._current_round.miss_position
            pygame.draw.line(
                screen, config.MISS_MARKER_COLOR,
                (int(miss.x) - 10, int(miss.y) - 10),
                (int(miss.x) + 10, int(miss.y) + 10), 3
            )
            pygame.draw.line(
                screen, config.MISS_MARKER_COLOR,
                (int(miss.x) + 10, int(miss.y) - 10),
                (int(miss.x) - 10, int(miss.y) + 10), 3
            )

        # Draw HUD
        self._render_hud(screen)

    def _render_hud(self, screen: pygame.Surface) -> None:
        """Render the heads-up display."""
        font_large = pygame.font.Font(None, 48)
        font_medium = pygame.font.Font(None, 32)
        font_small = pygame.font.Font(None, 24)

        y_offset = 20
        x_offset = 20

        # Mode indicator (top right)
        mode_names = {
            GroupingMethod.CENTROID: "CENTROID",
            GroupingMethod.FIXED_CENTER: "FIXED CENTER",
            GroupingMethod.FIXED_ORIGIN: "FIXED ORIGIN",
        }
        mode_name = mode_names.get(self._method, "UNKNOWN")
        mode_text = font_small.render(f"Mode: {mode_name}", True, (150, 150, 200))
        screen.blit(mode_text, (self._screen_width - mode_text.get_width() - 20, 20))

        # Phase description
        if self._current_round and self._internal_state != _InternalState.ROUND_OVER:
            phase_text = self._current_round.phase_description
            phase_color = (200, 200, 100) if self._internal_state == _InternalState.WAITING else (100, 255, 100)
            text = font_medium.render(phase_text, True, phase_color)
            screen.blit(text, (x_offset, y_offset))
            y_offset += 40
        elif self._internal_state == _InternalState.ROUND_OVER:
            text = font_medium.render("ROUND OVER - Click to continue", True, (255, 150, 150))
            screen.blit(text, (x_offset, y_offset))
            y_offset += 40

        # Current round stats
        if self._current_round:
            shots_text = f"Shots: {self._current_round.shot_count}"
            text = font_medium.render(shots_text, True, (200, 200, 200))
            screen.blit(text, (x_offset, y_offset))
            y_offset += 30

            # Show group size based on mode
            if self._method in (GroupingMethod.FIXED_CENTER, GroupingMethod.FIXED_ORIGIN):
                if self._current_round.is_locked:
                    group_text = f"Group: {self._current_round.group_diameter:.1f}px (locked)"
                    text = font_large.render(group_text, True, (255, 255, 255))
                    screen.blit(text, (x_offset, y_offset))
                    y_offset += 50
            else:
                if self._current_round.shot_count >= 2:
                    group_text = f"Group: {self._current_round.group_diameter:.1f}px"
                    text = font_large.render(group_text, True, (255, 255, 255))
                    screen.blit(text, (x_offset, y_offset))
                    y_offset += 50

        # Session best
        if self._session_best is not None:
            best_text = f"Best: {self._session_best:.1f}px"
            text = font_medium.render(best_text, True, (100, 200, 255))
            screen.blit(text, (x_offset, y_offset))
            y_offset += 30

        # Rounds completed
        rounds_text = f"Rounds: {self._rounds_completed}"
        text = font_small.render(rounds_text, True, (150, 150, 150))
        screen.blit(text, (x_offset, y_offset))

        # Instructions at bottom
        if self._internal_state == _InternalState.ROUND_OVER:
            inst_text = "Click anywhere or press R to start new round"
            text = font_small.render(inst_text, True, (150, 150, 150))
            text_rect = text.get_rect(center=(self._screen_width // 2, self._screen_height - 30))
            screen.blit(text, text_rect)
