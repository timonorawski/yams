"""
Classic Mode for Duck Hunt game.

This module implements the classic Duck Hunt gameplay mode where targets
spawn from the edges of the screen and move horizontally across. Players
must hit them before they escape, with difficulty increasing over time.

Examples:
    >>> mode = ClassicMode()
    >>> mode.update(0.016)  # Update for one frame
    >>> events = [...]  # Input events from InputManager
    >>> mode.handle_input(events)
"""

import random
import time
from typing import List
import pygame
from games.DuckHunt.game.game_mode import GameMode
from games.DuckHunt.game.target import Target
from games.DuckHunt.game.scoring import ScoreTracker
from games.DuckHunt.game.feedback import FeedbackManager
from games.DuckHunt.input.input_event import InputEvent
from models import Vector2D, TargetData, TargetState, GameState, DuckHuntInternalState
from games.DuckHunt.config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    TARGET_DEFAULT_SIZE,
    CLASSIC_INITIAL_SPEED,
    CLASSIC_SPEED_INCREASE,
    CLASSIC_MAX_SPEED,
    TARGET_SPAWN_RATE,
    TARGET_MAX_ACTIVE,
    Colors,
    Fonts,
)


class ClassicMode(GameMode):
    """Classic Duck Hunt game mode.

    Targets spawn from the left or right edges of the screen and move
    horizontally across. The player must hit them before they escape off
    the opposite edge. Speed increases with each successful hit, making
    the game progressively more challenging.

    Gameplay Rules:
    - Targets spawn at random Y positions on left or right edge
    - Targets move horizontally across screen
    - Hit targets increase score and combo
    - Escaped targets count as misses and break combo
    - Speed increases slightly with each hit
    - Win condition: reach target score (optional)
    - Lose condition: too many misses (optional)

    Attributes:
        score_tracker: ScoreTracker instance for managing score
        feedback: FeedbackManager instance for visual/audio feedback
        current_speed: Current target speed (increases over time)
        spawn_timer: Time until next target spawn
        max_misses: Maximum allowed misses before game over (None = unlimited)
        target_score: Score needed to win (None = endless mode)

    Examples:
        >>> mode = ClassicMode()
        >>> mode.update(0.016)
        >>> mode.state
        <DuckHuntInternalState.PLAYING: 'playing'>
        >>> mode.get_score()
        0
    """

    def __init__(
        self,
        max_misses: int = None,
        target_score: int = None,
        initial_speed: float = CLASSIC_INITIAL_SPEED,
        audio_enabled: bool = True,
        pacing: str = None,
        quiver_size: int = None,
        retrieval_pause: float = None,
        palette_name: str = None,
        color_palette: list = None,
    ):
        """Initialize Classic Mode.

        Args:
            max_misses: Maximum misses before game over (None = unlimited)
            target_score: Score needed to win (None = endless mode)
            initial_speed: Starting speed for targets
            audio_enabled: Whether to enable audio feedback (default: True)
            pacing: Pacing preset ('archery', 'throwing', 'blaster')
            quiver_size: Shots per round (None/0 = unlimited)
            retrieval_pause: Seconds for retrieval (0 = manual)
            palette_name: Test palette name for standalone mode
            color_palette: Explicit color list (from AMS)
        """
        super().__init__()

        # Import common modules
        import sys
        import os
        parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        from games.common.palette import GamePalette
        from games.common.quiver import create_quiver
        from games.common.pacing import scale_for_pacing

        # Initialize palette
        if color_palette:
            self._palette = GamePalette(colors=color_palette, palette_name='custom')
        elif palette_name:
            self._palette = GamePalette(palette_name=palette_name)
        else:
            self._palette = GamePalette()  # Default palette

        # Initialize quiver state
        self._quiver = create_quiver(quiver_size, retrieval_pause)

        # Apply pacing adjustments if provided
        self._pacing = pacing
        if pacing:
            # Scale spawn rate based on pacing
            spawn_rate = scale_for_pacing(TARGET_SPAWN_RATE, pacing)
        else:
            spawn_rate = TARGET_SPAWN_RATE

        self._score_tracker = ScoreTracker()
        self.feedback = FeedbackManager(audio_enabled=audio_enabled)
        self._current_speed = initial_speed
        self._spawn_timer = spawn_rate  # Initialize to full timer
        self._spawn_rate = spawn_rate  # Store base spawn rate
        self._max_misses = max_misses
        self._target_score = target_score
        self._hit_target_timers = {}  # Track how long hit targets have been on screen

    def update(self, dt: float) -> None:
        """Update game logic for this frame.

        Updates all targets, spawns new targets based on timer, removes
        off-screen targets (counting them as misses), and checks win/lose
        conditions.

        Args:
            dt: Time delta in seconds since last frame
        """
        # Handle retrieval state
        if self._state == DuckHuntInternalState.WAITING_FOR_RELOAD:
            if self._quiver and self._quiver.update_retrieval(dt):
                # Retrieval complete
                self._quiver.end_retrieval()
                self._state = DuckHuntInternalState.PLAYING
            return

        if self._state != DuckHuntInternalState.PLAYING:
            return

        # Update all targets
        updated_targets = []
        hit_timers_to_keep = {}

        for target in self._targets:
            target_id = id(target)

            if target.data.state == TargetState.HIT:
                # Update hit timer
                if target_id not in self._hit_target_timers:
                    self._hit_target_timers[target_id] = 0.0
                self._hit_target_timers[target_id] += dt

                # Keep hit target for 0.5 seconds then remove
                if self._hit_target_timers[target_id] < 0.5:
                    updated_targets.append(target)  # Don't update position (velocity is 0)
                    hit_timers_to_keep[target_id] = self._hit_target_timers[target_id]
                # else: remove target (don't add to updated_targets)

            elif target.is_active:
                # Update position for active targets
                updated_target = target.update(dt)

                # Check if target escaped off screen
                if updated_target.is_off_screen(SCREEN_WIDTH, SCREEN_HEIGHT):
                    # Target escaped - count as miss
                    self._score_tracker = self._score_tracker.record_miss()
                    # Don't add to updated list
                else:
                    updated_targets.append(updated_target)

        self._targets = updated_targets
        self._hit_target_timers = hit_timers_to_keep

        # Update spawn timer (only if not in retrieval)
        if self._state == DuckHuntInternalState.PLAYING:
            self._spawn_timer -= dt
            if self._spawn_timer <= 0:
                self._spawn_target()
                self._spawn_timer = self._spawn_rate

        # Update feedback effects
        self.feedback.update(dt)

        # Check win/lose conditions
        self._check_game_over()

    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events for this frame.

        Checks each input event against all active targets. If a hit is
        detected, marks the target as hit, updates score, and increases
        difficulty. If no hit is detected, counts as a miss.

        Args:
            events: List of InputEvent instances to process
        """
        if self._state != DuckHuntInternalState.PLAYING:
            return

        for event in events:
            # Check quiver before allowing shot
            if self._quiver:
                if self._quiver.use_shot():
                    # Quiver empty - enter retrieval state
                    self._quiver.start_retrieval()
                    self._state = DuckHuntInternalState.WAITING_FOR_RELOAD
                    return
            hit_detected = False

            # Check all targets for hit
            for i, target in enumerate(self._targets):
                if target.is_active and target.contains_point(event.position):
                    # Target was hit! Stop it at current position
                    hit_data = TargetData(
                        position=target.data.position,
                        velocity=Vector2D(x=0.0, y=0.0),  # Stop moving
                        size=target.data.size,
                        state=TargetState.HIT
                    )
                    self._targets[i] = Target(hit_data)

                    # Get old combo before updating
                    old_combo = self._score_tracker.get_stats().current_combo

                    # Update score
                    self._score_tracker = self._score_tracker.record_hit()

                    # Add visual and audio feedback
                    # Award 100 points for base hit
                    self.feedback.add_hit_effect(event.position, points=100)

                    # Check for combo milestone (every 5 hits)
                    new_combo = self._score_tracker.get_stats().current_combo
                    if new_combo % 5 == 0 and new_combo > 0:
                        self.feedback.play_combo_sound()

                    self._increase_difficulty()
                    hit_detected = True
                    break  # Only hit one target per click

            # If no target was hit, count as miss
            if not hit_detected:
                self._score_tracker = self._score_tracker.record_miss()
                # Add miss feedback
                self.feedback.add_miss_effect(event.position)

    def render(self, screen: pygame.Surface) -> None:
        """Render mode-specific UI and targets.

        Draws all active targets, feedback effects, and the score display.

        Args:
            screen: Pygame surface to draw on
        """
        # Render all targets with palette colors
        target_color = self._palette.random_target_color()
        for target in self._targets:
            if target.data.state == TargetState.ALIVE:
                target.render(screen, color=target_color)
            else:
                target.render(screen)  # Use default color for hit targets

        # Render feedback effects (after targets, before score)
        self.feedback.render(screen)

        # Render score
        self._score_tracker.render(screen)

        # Render quiver status if active
        if self._quiver and not self._quiver.is_unlimited:
            self._render_quiver_status(screen)

        # Render retrieval message if in retrieval state
        if self._state == DuckHuntInternalState.WAITING_FOR_RELOAD:
            self._render_retrieval_message(screen)

        # Render game over message if applicable
        if self._state == DuckHuntInternalState.GAME_OVER:
            self._render_game_over(screen)

    def get_score(self) -> int:
        """Get the current score.

        Returns:
            Current number of hits
        """
        return self._score_tracker.get_stats().hits

    def _spawn_target(self) -> None:
        """Spawn a new target if under the active limit.

        Targets spawn from left or right edge at random Y position,
        moving horizontally across the screen.
        """
        # Don't spawn if at max capacity
        if len(self._targets) >= TARGET_MAX_ACTIVE:
            return

        # Randomly choose left or right edge
        from_left = random.choice([True, False])

        # Random Y position (keep within screen bounds with margin)
        margin = TARGET_DEFAULT_SIZE
        y_pos = random.uniform(margin, SCREEN_HEIGHT - margin)

        # Set position and velocity based on spawn side
        if from_left:
            x_pos = 0.0  # Start at left edge
            velocity = Vector2D(x=self._current_speed, y=0.0)  # Move right
        else:
            x_pos = float(SCREEN_WIDTH)  # Start at right edge
            velocity = Vector2D(x=-self._current_speed, y=0.0)  # Move left

        # Create target data
        target_data = TargetData(
            position=Vector2D(x=x_pos, y=y_pos),
            velocity=velocity,
            size=TARGET_DEFAULT_SIZE,
            state=TargetState.ALIVE,
        )

        # Add target to list
        self._targets.append(Target(target_data))

    def _increase_difficulty(self) -> None:
        """Increase game difficulty by speeding up targets.

        Called after each successful hit. Speed increases by a fixed
        amount up to a maximum speed limit.
        """
        self._current_speed = min(
            self._current_speed + CLASSIC_SPEED_INCREASE, CLASSIC_MAX_SPEED
        )

    def _check_game_over(self) -> None:
        """Check win/lose conditions and update game state.

        Checks:
        - Win condition: target score reached (if set)
        - Lose condition: too many misses (if set)
        """
        stats = self._score_tracker.get_stats()

        # Check win condition
        if self._target_score is not None and stats.hits >= self._target_score:
            self._state = DuckHuntInternalState.GAME_OVER
            return

        # Check lose condition
        if self._max_misses is not None and stats.misses >= self._max_misses:
            self._state = DuckHuntInternalState.GAME_OVER
            return

    def _render_game_over(self, screen: pygame.Surface) -> None:
        """Render game over message.

        Args:
            screen: Pygame surface to draw on
        """
        # Create semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(Colors.BLACK[:3])  # Use RGB only
        screen.blit(overlay, (0, 0))

        # Render "GAME OVER" text
        try:
            font = pygame.font.Font(None, Fonts.HUGE)
        except Exception:
            font = pygame.font.SysFont("monospace", Fonts.HUGE)

        text = "GAME OVER"
        text_surface = font.render(text, True, Colors.WHITE)
        text_rect = text_surface.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)
        )
        screen.blit(text_surface, text_rect)

        # Render final score
        stats = self._score_tracker.get_stats()
        score_text = f"Final Score: {stats.hits}"
        try:
            score_font = pygame.font.Font(None, Fonts.LARGE)
        except Exception:
            score_font = pygame.font.SysFont("monospace", Fonts.LARGE)

        score_surface = score_font.render(score_text, True, Colors.YELLOW)
        score_rect = score_surface.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)
        )
        screen.blit(score_surface, score_rect)

        # Render accuracy
        accuracy_text = f"Accuracy: {stats.accuracy:.1%}"
        accuracy_surface = score_font.render(accuracy_text, True, Colors.WHITE)
        accuracy_rect = accuracy_surface.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70)
        )
        screen.blit(accuracy_surface, accuracy_rect)

    def _render_quiver_status(self, screen: pygame.Surface) -> None:
        """Render quiver/ammo status display.

        Args:
            screen: Pygame surface to draw on
        """
        if not self._quiver:
            return

        try:
            font = pygame.font.Font(None, Fonts.MEDIUM)
        except Exception:
            font = pygame.font.SysFont("monospace", Fonts.MEDIUM)

        text = self._quiver.get_display_text()
        text_surface = font.render(text, True, Colors.WHITE)
        text_rect = text_surface.get_rect(topright=(SCREEN_WIDTH - 20, 70))
        screen.blit(text_surface, text_rect)

    def _render_retrieval_message(self, screen: pygame.Surface) -> None:
        """Render retrieval/reload message overlay.

        Args:
            screen: Pygame surface to draw on
        """
        if not self._quiver:
            return

        # Create semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(Colors.BLACK[:3])
        screen.blit(overlay, (0, 0))

        # Render retrieval message
        try:
            font = pygame.font.Font(None, Fonts.LARGE)
        except Exception:
            font = pygame.font.SysFont("monospace", Fonts.LARGE)

        text = self._quiver.get_retrieval_text()
        text_surface = font.render(text, True, Colors.YELLOW)
        text_rect = text_surface.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        )
        screen.blit(text_surface, text_rect)

    def set_palette(self, palette_name: str) -> bool:
        """
        Switch to a named test palette.

        Args:
            palette_name: Name from TEST_PALETTES

        Returns:
            True if palette found and switched
        """
        return self._palette.set_palette(palette_name)

    def cycle_palette(self) -> str:
        """
        Cycle to next test palette (for standalone testing).

        Returns:
            Name of new palette
        """
        return self._palette.cycle_palette()

    def manual_retrieval_ready(self) -> None:
        """
        Signal that manual retrieval is complete (SPACE key in standalone mode).
        """
        if self._quiver and self._state == DuckHuntInternalState.WAITING_FOR_RELOAD:
            self._quiver.end_retrieval()
            self._state = DuckHuntInternalState.PLAYING
