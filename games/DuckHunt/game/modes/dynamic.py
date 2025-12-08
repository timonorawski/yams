"""
Dynamic Game Mode - YAML-configured gameplay.

This module implements a data-driven game mode that executes based on
YAML configuration files. It supports trajectory-based targets, level
progression, and configurable scoring rules without requiring code changes.

Examples:
    >>> from game.mode_loader import GameModeLoader
    >>> loader = GameModeLoader()
    >>> config = loader.load_mode("classic_ducks")
    >>> mode = DynamicGameMode(config)
    >>> mode.update(0.016)
"""

import random
import time
from typing import List, Optional
import pygame

from game.game_mode import GameMode
from game.trajectory_target import TrajectoryTarget
from game.scoring import ScoreTracker
from game.feedback import FeedbackManager
from game.trajectory import TrajectoryRegistry
from input.input_event import InputEvent
from models import Vector2D, GameState, TargetState, DuckHuntInternalState
from models.game_mode_config import GameModeConfig, LevelConfig
from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    Colors,
    Fonts,
)


class DynamicGameMode(GameMode):
    """Dynamic game mode driven by YAML configuration.

    This mode executes gameplay based on a loaded GameModeConfig, supporting:
    - Pluggable trajectory algorithms (linear, bezier_3d, etc.)
    - Level-based progression with config-defined parameters
    - Configurable scoring rules and bonuses
    - Multiple spawn patterns and game types

    The mode is completely data-driven - no code changes needed for
    new game modes, only YAML configuration files.

    Attributes:
        config: Loaded and validated GameModeConfig
        score_tracker: ScoreTracker instance for scoring
        feedback: FeedbackManager for visual/audio feedback
        current_level: Current level number (1-indexed)
        spawn_timer: Time until next target spawn

    Examples:
        >>> from game.mode_loader import GameModeLoader
        >>> loader = GameModeLoader()
        >>> config = loader.load_mode("classic_ducks")
        >>> mode = DynamicGameMode(config)
        >>> mode.state
        <DuckHuntInternalState.PLAYING: 'playing'>
    """

    def __init__(self, config: GameModeConfig, audio_enabled: bool = True):
        """Initialize dynamic game mode from configuration.

        Args:
            config: Validated GameModeConfig from YAML
            audio_enabled: Whether to enable audio feedback
        """
        super().__init__()

        self.config = config
        self._score_tracker = ScoreTracker()
        self.feedback = FeedbackManager(audio_enabled=audio_enabled)

        # Level progression
        self._current_level = 1
        self._level_hits = 0  # Hits in current level

        # Spawning state
        self._spawn_timer = self._get_current_level_config().spawning.spawn_rate_base
        self._hit_target_timers = {}  # Track how long hit targets visible

        # Trajectory algorithm
        self._trajectory_algo = TrajectoryRegistry.get(
            config.trajectory.algorithm
        )

        # Projectile limiting (for physical games like archery)
        if config.rules.projectiles_per_round is not None:
            self._projectiles_remaining = config.rules.projectiles_per_round
        else:
            self._projectiles_remaining = None  # Unlimited

    @property
    def current_level(self) -> int:
        """Get current level number (1-indexed)."""
        return self._current_level

    def get_projectiles_remaining(self) -> Optional[int]:
        """Get number of projectiles remaining in current round.

        Returns:
            Number of projectiles left, or None if unlimited
        """
        return self._projectiles_remaining

    def reload(self) -> None:
        """Reload projectiles and resume gameplay.

        This method is called by the AMS after handling interstitial screens
        or system functions between rounds. Resets projectile count and
        transitions back to PLAYING state.
        """
        if self.config.rules.projectiles_per_round is not None:
            self._projectiles_remaining = self.config.rules.projectiles_per_round
            self._state = DuckHuntInternalState.PLAYING

    def _get_current_level_config(self) -> LevelConfig:
        """Get configuration for current level.

        If current level exceeds configured levels, returns the last level config.

        Returns:
            LevelConfig for current level
        """
        # Find config for current level
        for level_config in self.config.levels:
            if level_config.level == self._current_level:
                return level_config

        # If beyond configured levels, use last level
        return self.config.levels[-1]

    def _should_advance_level(self) -> bool:
        """Check if player should advance to next level.

        Returns:
            True if conditions met to advance level
        """
        # Check if we have more levels defined
        if self._current_level >= len(self.config.levels):
            return False  # At max level

        # Advance after 10 hits per level (could be configurable)
        return self._level_hits >= 10

    def _advance_level(self) -> None:
        """Advance to the next level."""
        if self._current_level < len(self.config.levels):
            self._current_level += 1
            self._level_hits = 0
            # Play level-up sound/effect
            # TODO: Add level-up feedback

    def _spawn_target(self) -> None:
        """Spawn a new target based on current level configuration."""
        level_config = self._get_current_level_config()

        # Don't spawn if at max capacity
        active_targets = [
            t for t in self._targets
            if isinstance(t, TrajectoryTarget) and t.is_active
        ]
        if len(active_targets) >= level_config.spawning.max_active:
            return

        # Generate random start and end positions based on spawn_sides
        spawn_side = random.choice(level_config.spawning.spawn_sides)

        # Determine start and end positions
        margin = 50  # Margin from screen edges
        if spawn_side == "left":
            start_x = 0.0
            start_y = random.uniform(margin, SCREEN_HEIGHT - margin)
            end_x = float(SCREEN_WIDTH)
            end_y = random.uniform(margin, SCREEN_HEIGHT - margin)
        elif spawn_side == "right":
            start_x = float(SCREEN_WIDTH)
            start_y = random.uniform(margin, SCREEN_HEIGHT - margin)
            end_x = 0.0
            end_y = random.uniform(margin, SCREEN_HEIGHT - margin)
        elif spawn_side == "top":
            start_x = random.uniform(margin, SCREEN_WIDTH - margin)
            start_y = 0.0
            end_x = random.uniform(margin, SCREEN_WIDTH - margin)
            end_y = float(SCREEN_HEIGHT)
        elif spawn_side == "bottom":
            start_x = random.uniform(margin, SCREEN_WIDTH - margin)
            start_y = float(SCREEN_HEIGHT)
            end_x = random.uniform(margin, SCREEN_WIDTH - margin)
            end_y = 0.0
        else:
            # Default to left side
            start_x, start_y = 0.0, SCREEN_HEIGHT / 2
            end_x, end_y = float(SCREEN_WIDTH), SCREEN_HEIGHT / 2

        # Generate control point for curve (apex of trajectory)
        control_x = (start_x + end_x) / 2
        control_y = (start_y + end_y) / 2

        # Add curvature variation
        curvature = level_config.trajectory.curvature_factor
        if curvature > 0:
            # Randomize control point for varied curves
            control_x += random.uniform(-200, 200) * curvature
            control_y += random.uniform(-200, 200) * curvature

        # Clamp control point to screen bounds
        control_x = max(0, min(SCREEN_WIDTH, control_x))
        control_y = max(0, min(SCREEN_HEIGHT, control_y))

        # Calculate trajectory duration based on speed
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        duration = distance / level_config.target.speed

        # Generate trajectory using configured algorithm
        trajectory_config = {
            'duration': duration,
            'start_x': start_x,
            'start_y': start_y,
            'end_x': end_x,
            'end_y': end_y,
            'control_x': control_x,
            'control_y': control_y,
            'depth_range': level_config.target.depth_range,
            'depth_direction': self.config.trajectory.depth_direction,
            'curvature_factor': level_config.trajectory.curvature_factor,
        }

        trajectory = self._trajectory_algo.generate(
            trajectory_config,
            screen_width=SCREEN_WIDTH,
            screen_height=SCREEN_HEIGHT,
        )

        # Create trajectory target
        target = TrajectoryTarget(
            trajectory=trajectory,
            initial_size=level_config.target.size,
            state=TargetState.ALIVE,
        )

        self._targets.append(target)

        # Play spawn sound
        self.feedback.play_spawn_sound()

    def update(self, dt: float) -> None:
        """Update game logic for this frame.

        Updates all targets, spawns new targets based on timer, removes
        off-screen or completed targets, and checks win/lose conditions.
        Does not update if in WAITING_FOR_RELOAD state (AMS will call reload()).

        Args:
            dt: Time delta in seconds since last frame
        """
        if self._state != DuckHuntInternalState.PLAYING:
            return

        # Update all targets
        updated_targets = []
        hit_timers_to_keep = {}

        for target in self._targets:
            if not isinstance(target, TrajectoryTarget):
                continue  # Skip non-trajectory targets

            target_id = id(target)

            if target.state == TargetState.HIT:
                # Update hit timer
                if target_id not in self._hit_target_timers:
                    self._hit_target_timers[target_id] = 0.0
                self._hit_target_timers[target_id] += dt

                # Keep hit target for 0.5 seconds then remove
                if self._hit_target_timers[target_id] < 0.5:
                    updated_targets.append(target)  # Don't update position
                    hit_timers_to_keep[target_id] = self._hit_target_timers[target_id]
                # else: remove target (don't add to updated_targets)

            elif target.is_active:
                # Update position for active targets
                updated_target = target.update(dt)

                # Check if target completed trajectory or escaped off screen
                if updated_target.is_complete or updated_target.is_off_screen(
                    SCREEN_WIDTH, SCREEN_HEIGHT
                ):
                    # Target escaped - count as miss
                    self._score_tracker = self._score_tracker.record_miss()
                    self.feedback.play_miss_sound()
                    # Don't add to updated list
                else:
                    updated_targets.append(updated_target)

        self._targets = updated_targets
        self._hit_target_timers = hit_timers_to_keep

        # Update spawn timer
        level_config = self._get_current_level_config()
        self._spawn_timer -= dt
        if self._spawn_timer <= 0:
            self._spawn_target()
            self._spawn_timer = level_config.spawning.spawn_rate_base

        # Update feedback effects
        self.feedback.update(dt)

        # Check level progression
        if self._should_advance_level():
            self._advance_level()

        # Check win/lose conditions
        self._check_game_over()

    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events for this frame.

        Checks each input event against all active targets. If a hit is
        detected, marks the target as hit, updates score with config-based
        bonuses, and provides feedback.

        If projectile limiting is enabled, decrements projectile counter
        and transitions to WAITING_FOR_RELOAD when depleted.

        Args:
            events: List of InputEvent instances to process
        """
        if self._state != DuckHuntInternalState.PLAYING:
            return

        for event in events:
            # Decrement projectile counter if limited
            if self._projectiles_remaining is not None:
                if self._projectiles_remaining <= 0:
                    # Already depleted, transition to reload state
                    self._state = DuckHuntInternalState.WAITING_FOR_RELOAD
                    return
                self._projectiles_remaining -= 1
            hit_detected = False

            # Check all targets for hit
            for i, target in enumerate(self._targets):
                if not isinstance(target, TrajectoryTarget):
                    continue

                if target.is_active and target.contains_point(event.position):
                    # Target was hit! Stop it at current position
                    hit_target = target.set_state(TargetState.HIT)
                    self._targets[i] = hit_target

                    # Update score
                    self._score_tracker = self._score_tracker.record_hit()
                    self._level_hits += 1

                    # Calculate points with bonuses
                    points = self.config.scoring.base_hit_points

                    # Apex bonus (if hit near trajectory peak)
                    if self.config.scoring.apex_bonus > 0:
                        progress = target.progress
                        # Check if near apex (around 0.5 progress)
                        if 0.4 <= progress <= 0.6:
                            points += self.config.scoring.apex_bonus

                    # Speed bonus (config-based)
                    if self.config.scoring.speed_bonus:
                        # Award bonus for faster targets
                        level_config = self._get_current_level_config()
                        if level_config.target.speed > 150:
                            speed_bonus = int((level_config.target.speed - 150) / 10)
                            points += speed_bonus

                    # Add visual and audio feedback
                    self.feedback.add_hit_effect(event.position, points=points)

                    # Check for combo milestone (every 5 hits)
                    if self.config.scoring.combo_multiplier:
                        combo = self._score_tracker.get_stats().current_combo
                        if combo % 5 == 0 and combo > 0:
                            self.feedback.play_combo_sound()

                    hit_detected = True
                    break  # Only hit one target per click

            # If no target was hit, count as miss
            if not hit_detected:
                self._score_tracker = self._score_tracker.record_miss()
                # Add miss feedback
                self.feedback.add_miss_effect(event.position)

            # Check if we just used the last projectile
            if self._projectiles_remaining is not None and self._projectiles_remaining <= 0:
                self._state = DuckHuntInternalState.WAITING_FOR_RELOAD
                return

    def render(self, screen: pygame.Surface) -> None:
        """Render mode-specific UI and targets.

        Draws all active targets (with depth-scaled size), feedback effects,
        score display, and level information.

        Args:
            screen: Pygame surface to draw on
        """
        # Render all targets
        for target in self._targets:
            if isinstance(target, TrajectoryTarget):
                target.render(screen)

        # Render feedback effects (after targets, before UI)
        self.feedback.render(screen)

        # Render score
        self._score_tracker.render(screen)

        # Render level info
        self._render_level_info(screen)

        # Render game over message if applicable
        if self._state == DuckHuntInternalState.GAME_OVER:
            self._render_game_over(screen)

    def get_score(self) -> int:
        """Get the current score.

        Returns:
            Current number of hits
        """
        return self._score_tracker.get_stats().hits

    def _render_level_info(self, screen: pygame.Surface) -> None:
        """Render current level information.

        Args:
            screen: Pygame surface to draw on
        """
        try:
            font = pygame.font.Font(None, Fonts.SMALL)
        except Exception:
            font = pygame.font.SysFont("monospace", Fonts.SMALL)

        level_text = f"Level {self._current_level}"
        text_surface = font.render(level_text, True, Colors.WHITE)
        screen.blit(text_surface, (10, 40))

    def _check_game_over(self) -> None:
        """Check win/lose conditions and update game state.

        Checks conditions based on config.rules.game_type:
        - score_target: Win when score reaches target
        - survival: Lose when misses exceed max_misses
        - timed: Lose when time expires
        - endless: Never ends
        """
        stats = self._score_tracker.get_stats()

        # Check win condition (score_target mode)
        if self.config.rules.game_type == "score_target":
            if (self.config.rules.score_target is not None and
                    stats.hits >= self.config.rules.score_target):
                self._state = DuckHuntInternalState.GAME_OVER
                return

        # Check lose condition (survival mode)
        if self.config.rules.game_type == "survival":
            if (self.config.rules.max_misses is not None and
                    stats.misses >= self.config.rules.max_misses):
                self._state = DuckHuntInternalState.GAME_OVER
                return

        # TODO: Implement timed mode with timer tracking

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

        # Render level reached
        level_text = f"Level Reached: {self._current_level}"
        level_surface = score_font.render(level_text, True, Colors.CYAN)
        level_rect = level_surface.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 120)
        )
        screen.blit(level_surface, level_rect)
