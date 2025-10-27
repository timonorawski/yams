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
from game.game_mode import GameMode
from game.target import Target
from game.scoring import ScoreTracker
from game.feedback import FeedbackManager
from input.input_event import InputEvent
from models import Vector2D, TargetData, TargetState, GameState
from config import (
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
        <GameState.PLAYING: 'playing'>
        >>> mode.get_score()
        0
    """

    def __init__(
        self,
        max_misses: int = None,
        target_score: int = None,
        initial_speed: float = CLASSIC_INITIAL_SPEED,
        audio_enabled: bool = True,
    ):
        """Initialize Classic Mode.

        Args:
            max_misses: Maximum misses before game over (None = unlimited)
            target_score: Score needed to win (None = endless mode)
            initial_speed: Starting speed for targets
            audio_enabled: Whether to enable audio feedback (default: True)
        """
        super().__init__()
        self._score_tracker = ScoreTracker()
        self.feedback = FeedbackManager(audio_enabled=audio_enabled)
        self._current_speed = initial_speed
        self._spawn_timer = TARGET_SPAWN_RATE  # Initialize to full timer
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
        if self._state != GameState.PLAYING:
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

        # Update spawn timer
        self._spawn_timer -= dt
        if self._spawn_timer <= 0:
            self._spawn_target()
            self._spawn_timer = TARGET_SPAWN_RATE

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
        if self._state != GameState.PLAYING:
            return

        for event in events:
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
        # Render all targets
        for target in self._targets:
            target.render(screen)

        # Render feedback effects (after targets, before score)
        self.feedback.render(screen)

        # Render score
        self._score_tracker.render(screen)

        # Render game over message if applicable
        if self._state == GameState.GAME_OVER:
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
            self._state = GameState.GAME_OVER
            return

        # Check lose condition
        if self._max_misses is not None and stats.misses >= self._max_misses:
            self._state = GameState.GAME_OVER
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
