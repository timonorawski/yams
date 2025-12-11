"""DuckHunt - Classic duck hunting game.

This module provides the main game class that inherits from BaseGame,
making DuckHunt compliant with the AMS game architecture.

The game supports YAML-based level configuration loaded from games/DuckHunt/modes/
or can use the built-in classic mode for simple gameplay.
"""
from pathlib import Path
from typing import List, Optional
import pygame

from ams.games import BaseGame, GameState
from ams.games.palette import GamePalette


class DuckHuntMode(BaseGame):
    """Duck Hunt game mode.

    Classic duck hunting with moving targets, combos, and difficulty progression.
    Targets spawn from screen edges and fly across - hit them before they escape!

    Supports two modes of operation:
    1. YAML-based: Load full configuration from modes/*.yaml files
    2. Classic: Simple built-in mode with CLI overrides

    Inherits from BaseGame which provides:
    - Automatic state management (state property)
    - Palette support (_palette, cycle_palette, set_palette)
    - Quiver/ammo support (_quiver, _use_shot, _start_retrieval, etc.)
    - Base CLI arguments (--palette, --quiver-size, --retrieval-pause)
    """

    # =========================================================================
    # Game Metadata
    # =========================================================================

    NAME = "Duck Hunt"
    DESCRIPTION = "Classic duck hunting game with moving targets and combos."
    VERSION = "2.0.0"
    AUTHOR = "AMS Team"

    # Game-specific CLI arguments (base args added automatically)
    ARGUMENTS = [
        {
            'name': '--level',
            'type': str,
            'default': 'classic',
            'help': 'Level name (from modes/ dir) or "classic" for built-in mode'
        },
        {
            'name': '--skin',
            'type': str,
            'default': 'classic',
            'choices': ['geometric', 'classic'],
            'help': 'Visual skin (geometric=circles, classic=sprites)'
        },
        {
            'name': '--pacing',
            'type': str,
            'default': 'throwing',
            'choices': ['archery', 'throwing', 'blaster'],
            'help': 'Device speed preset (archery=slow, throwing=medium, blaster=fast)'
        },
        {
            'name': '--max-misses',
            'type': int,
            'default': None,
            'help': 'Maximum misses before game over (None=unlimited)'
        },
        {
            'name': '--target-score',
            'type': int,
            'default': None,
            'help': 'Score needed to win (None=endless)'
        },
        {
            'name': '--list-levels',
            'action': 'store_true',
            'default': False,
            'help': 'List available levels and exit'
        },
    ]

    # =========================================================================
    # Initialization
    # =========================================================================

    # Skin registry - maps skin names to skin classes
    SKINS = {}  # Populated in __init__ to avoid circular imports

    def __init__(
        self,
        level: str = 'classic',
        skin: str = 'classic',
        pacing: str = 'throwing',
        max_misses: Optional[int] = None,
        target_score: Optional[int] = None,
        list_levels: bool = False,
        **kwargs,
    ):
        """Initialize Duck Hunt game.

        Args:
            level: Level name or 'classic' for built-in mode
            skin: Visual skin ('geometric' or 'classic')
            pacing: Device speed preset (archery/throwing/blaster)
            max_misses: Maximum misses before game over (None=unlimited)
            target_score: Score needed to win (None=endless)
            list_levels: If True, list available levels and exit
            **kwargs: Base game args (quiver_size, retrieval_pause, palette, etc.)
        """
        # Call parent constructor (handles palette and quiver)
        super().__init__(**kwargs)

        # Handle list-levels request
        if list_levels:
            self._print_available_levels()
            import sys
            sys.exit(0)

        # Store configuration
        self._level_name = level
        self._skin_name = skin
        self._pacing = pacing
        self._max_misses = max_misses
        self._target_score = target_score

        # Import game components (delayed import to avoid circular deps)
        from games.DuckHunt.game.duck_target import DuckTarget, DuckPhase
        from games.DuckHunt.game.skins import GeometricSkin, ClassicSkin
        from games.DuckHunt.game.scoring import ScoreTracker
        from games.DuckHunt.game.feedback import FeedbackManager
        from games.DuckHunt.config import (
            SCREEN_WIDTH, SCREEN_HEIGHT,
            TARGET_DEFAULT_SIZE,
            CLASSIC_INITIAL_SPEED,
            CLASSIC_SPEED_INCREASE,
            CLASSIC_MAX_SPEED,
            TARGET_SPAWN_RATE,
            TARGET_MAX_ACTIVE,
        )
        from models import Vector2D, TargetData, TargetState

        # Initialize skin system
        self.SKINS = {
            'geometric': GeometricSkin,
            'classic': ClassicSkin,
        }
        skin_class = self.SKINS.get(skin, ClassicSkin)
        self._skin = skin_class()

        # Store imports for use in methods
        self._DuckTarget = DuckTarget
        self._DuckPhase = DuckPhase
        self._Target = DuckTarget  # Alias for compatibility
        self._TargetData = TargetData
        self._TargetState = TargetState
        self._Vector2D = Vector2D
        self._SCREEN_WIDTH = SCREEN_WIDTH
        self._SCREEN_HEIGHT = SCREEN_HEIGHT
        self._TARGET_DEFAULT_SIZE = TARGET_DEFAULT_SIZE
        self._TARGET_MAX_ACTIVE = TARGET_MAX_ACTIVE

        # Initialize game state
        self._targets: List = []
        self._score_tracker = ScoreTracker()
        self._feedback = FeedbackManager(audio_enabled=True)
        self._game_over = False
        self._won = False

        # Level configuration (loaded from YAML or defaults)
        self._level_config = None
        self._current_level = 1
        self._level_hits = 0

        # Try to load YAML level configuration
        if level != 'classic':
            self._load_level_config(level)

        # Set up speed and spawning based on config or defaults
        if self._level_config:
            self._init_from_config()
        else:
            # Classic mode - use defaults
            self._current_speed = CLASSIC_INITIAL_SPEED
            self._speed_increase = CLASSIC_SPEED_INCREASE
            self._max_speed = CLASSIC_MAX_SPEED
            self._spawn_rate = TARGET_SPAWN_RATE
            self._spawn_timer = self._spawn_rate
            self._spawn_sides = ['left', 'right']

            # Apply pacing adjustments for classic mode
            self._apply_pacing(pacing)

    def _print_available_levels(self) -> None:
        """Print available levels to stdout."""
        from games.DuckHunt.game.mode_loader import GameModeLoader

        levels_dir = Path(__file__).parent / 'levels'
        loader = GameModeLoader(levels_dir)
        levels = loader.list_available_modes()

        print("\nAvailable DuckHunt levels:")
        print("-" * 40)
        print("  classic          Built-in classic mode")

        for level_id in levels:
            try:
                info = loader.get_mode_info(level_id)
                print(f"  {level_id:16} {info.get('description', '')[:40]}")
            except Exception:
                print(f"  {level_id:16} (error loading info)")

        print("-" * 40)
        print("Use --level <name> to select a level\n")

    def _load_level_config(self, level_name: str) -> None:
        """Load level configuration from YAML file.

        Args:
            level_name: Name of level file (without .yaml extension)
        """
        from games.DuckHunt.game.mode_loader import GameModeLoader

        levels_dir = Path(__file__).parent / 'levels'
        loader = GameModeLoader(levels_dir)

        if not loader.mode_exists(level_name):
            print(f"Warning: Level '{level_name}' not found, using classic mode")
            return

        try:
            self._level_config = loader.load_mode(level_name)
            print(f"Loaded level: {self._level_config.name}")
        except Exception as e:
            print(f"Warning: Failed to load level '{level_name}': {e}")
            print("Using classic mode instead")

    def _init_from_config(self) -> None:
        """Initialize game parameters from loaded level config."""
        if not self._level_config:
            return

        # Get first level's settings
        level_cfg = self._level_config.levels[0]

        # Target settings
        self._TARGET_DEFAULT_SIZE = level_cfg.target.size
        self._current_speed = level_cfg.target.speed

        # Spawning settings
        self._spawn_rate = level_cfg.spawning.spawn_rate_base
        self._spawn_timer = self._spawn_rate
        self._TARGET_MAX_ACTIVE = level_cfg.spawning.max_active
        self._spawn_sides = level_cfg.spawning.spawn_sides

        # Rules
        rules = self._level_config.rules
        if rules.max_misses is not None and self._max_misses is None:
            self._max_misses = rules.max_misses
        if rules.score_target is not None and self._target_score is None:
            self._target_score = rules.score_target

        # Speed increase per level (estimate)
        self._speed_increase = 20.0
        self._max_speed = 400.0

    def _apply_pacing(self, pacing: str) -> None:
        """Apply pacing preset adjustments.

        Args:
            pacing: Pacing preset name
        """
        from ams.games.pacing import scale_for_pacing
        from games.DuckHunt.config import TARGET_SPAWN_RATE

        # Scale spawn rate based on pacing
        self._spawn_rate = scale_for_pacing(TARGET_SPAWN_RATE, pacing)
        self._spawn_timer = self._spawn_rate

    # =========================================================================
    # BaseGame Implementation
    # =========================================================================

    def _get_internal_state(self) -> GameState:
        """Map internal state to standard GameState."""
        if self._game_over:
            if self._won:
                return GameState.WON
            return GameState.GAME_OVER
        return GameState.PLAYING

    def get_score(self) -> int:
        """Get current score."""
        return self._score_tracker.get_stats().hits

    def handle_input(self, events: List) -> None:
        """Process input events (shots)."""
        if self.state != GameState.PLAYING:
            return

        for event in events:
            # Check quiver before allowing shot
            if self._use_shot():
                self._start_retrieval()
                return

            hit_detected = False

            # Check all targets for hit
            for i, target in enumerate(self._targets):
                if target.is_active and target.contains_point(event.position):
                    # Target was hit - use DuckTarget.hit() for phase transition
                    self._targets[i] = target.hit()

                    # Update score
                    self._score_tracker = self._score_tracker.record_hit()

                    # Add visual and audio feedback
                    self._feedback.add_hit_effect(event.position, points=100)

                    # Play hit sound via skin
                    self._skin.play_hit_sound()

                    # Check for combo milestone
                    new_combo = self._score_tracker.get_stats().current_combo
                    if new_combo % 5 == 0 and new_combo > 0:
                        self._feedback.play_combo_sound()

                    # Increase difficulty
                    self._increase_difficulty()
                    hit_detected = True
                    break

            # If no target was hit, count as miss
            if not hit_detected:
                self._score_tracker = self._score_tracker.record_miss()
                self._feedback.add_miss_effect(event.position)
                self._skin.play_miss_sound()

    def update(self, dt: float) -> None:
        """Update game logic."""
        # Handle retrieval state
        if self._in_retrieval:
            if self._update_retrieval(dt):
                self._end_retrieval()
            return

        if self.state != GameState.PLAYING:
            return

        # Update skin (for animations)
        self._skin.update(dt)

        # Update all targets using DuckTarget's phase-based logic
        updated_targets = []

        for target in self._targets:
            # DuckTarget.update() handles:
            # - FLYING: normal movement
            # - HIT_PAUSE: stay in place
            # - FALLING: gravity-based fall
            updated_target = target.update(dt)

            # Check if target went off screen
            if updated_target.is_off_screen(self._SCREEN_WIDTH, self._SCREEN_HEIGHT):
                # Only count as miss if it was an alive target that escaped
                if target.phase == self._DuckPhase.FLYING:
                    self._score_tracker = self._score_tracker.record_miss()
                    self._skin.play_escape_sound()
                # Don't add to updated list - target is gone
            else:
                updated_targets.append(updated_target)

        self._targets = updated_targets

        # Spawn new targets
        self._spawn_timer -= dt
        if self._spawn_timer <= 0:
            self._spawn_target()
            self._spawn_timer = self._spawn_rate

        # Update feedback effects
        self._feedback.update(dt)

        # Check win/lose conditions
        self._check_game_over()

    def render(self, screen: pygame.Surface) -> None:
        """Render the game."""
        from games.DuckHunt.config import Colors, Fonts, SCREEN_WIDTH, SCREEN_HEIGHT

        # Clear screen with background color
        bg_color = self._palette.get_background_color()
        screen.fill(bg_color)

        # Render all targets via skin
        for target in self._targets:
            self._skin.render_target(target, screen)

        # Render feedback effects
        self._feedback.render(screen)

        # Render score
        self._score_tracker.render(screen)

        # Render quiver status if active
        if self._quiver and not self._quiver.is_unlimited:
            self._render_quiver_status(screen)

        # Render retrieval message if in retrieval state
        if self._in_retrieval:
            self._render_retrieval_overlay(screen)

        # Render game over if applicable
        if self._game_over:
            self._render_game_over(screen)

    # =========================================================================
    # Game-specific methods
    # =========================================================================

    def _spawn_target(self) -> None:
        """Spawn a new target if under the active limit."""
        import random

        if len(self._targets) >= self._TARGET_MAX_ACTIVE:
            return

        # Choose spawn side from configured list
        spawn_side = random.choice(self._spawn_sides)
        margin = self._TARGET_DEFAULT_SIZE

        # Determine position and velocity based on spawn side
        if spawn_side == 'left':
            x_pos = 0.0
            y_pos = random.uniform(margin, self._SCREEN_HEIGHT - margin)
            velocity = self._Vector2D(x=self._current_speed, y=0.0)
        elif spawn_side == 'right':
            x_pos = float(self._SCREEN_WIDTH)
            y_pos = random.uniform(margin, self._SCREEN_HEIGHT - margin)
            velocity = self._Vector2D(x=-self._current_speed, y=0.0)
        elif spawn_side == 'top':
            x_pos = random.uniform(margin, self._SCREEN_WIDTH - margin)
            y_pos = 0.0
            velocity = self._Vector2D(x=0.0, y=self._current_speed)
        elif spawn_side == 'bottom':
            x_pos = random.uniform(margin, self._SCREEN_WIDTH - margin)
            y_pos = float(self._SCREEN_HEIGHT)
            velocity = self._Vector2D(x=0.0, y=-self._current_speed)
        else:
            # Default fallback
            x_pos = 0.0
            y_pos = random.uniform(margin, self._SCREEN_HEIGHT - margin)
            velocity = self._Vector2D(x=self._current_speed, y=0.0)

        target_data = self._TargetData(
            position=self._Vector2D(x=x_pos, y=y_pos),
            velocity=velocity,
            size=self._TARGET_DEFAULT_SIZE,
            state=self._TargetState.ALIVE,
        )

        # Create DuckTarget
        self._targets.append(self._DuckTarget(target_data))

        # Play spawn sound via skin
        self._skin.play_spawn_sound()

    def _increase_difficulty(self) -> None:
        """Increase game difficulty by speeding up targets."""
        self._current_speed = min(
            self._current_speed + self._speed_increase,
            self._max_speed
        )

    def _check_game_over(self) -> None:
        """Check win/lose conditions."""
        stats = self._score_tracker.get_stats()

        # Check win condition
        if self._target_score is not None and stats.hits >= self._target_score:
            self._game_over = True
            self._won = True
            return

        # Check lose condition
        if self._max_misses is not None and stats.misses >= self._max_misses:
            self._game_over = True
            self._won = False

    def _render_quiver_status(self, screen: pygame.Surface) -> None:
        """Render quiver/ammo status."""
        from games.DuckHunt.config import Colors, Fonts, SCREEN_WIDTH

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

    def _render_retrieval_overlay(self, screen: pygame.Surface) -> None:
        """Render retrieval/reload message overlay."""
        from games.DuckHunt.config import Colors, Fonts, SCREEN_WIDTH, SCREEN_HEIGHT

        if not self._quiver:
            return

        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(Colors.BLACK[:3])
        screen.blit(overlay, (0, 0))

        try:
            font = pygame.font.Font(None, Fonts.LARGE)
        except Exception:
            font = pygame.font.SysFont("monospace", Fonts.LARGE)

        text = self._quiver.get_retrieval_text()
        text_surface = font.render(text, True, Colors.YELLOW)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(text_surface, text_rect)

    def _render_game_over(self, screen: pygame.Surface) -> None:
        """Render game over overlay."""
        from games.DuckHunt.config import Colors, Fonts, SCREEN_WIDTH, SCREEN_HEIGHT

        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(Colors.BLACK[:3])
        screen.blit(overlay, (0, 0))

        try:
            font = pygame.font.Font(None, Fonts.HUGE)
        except Exception:
            font = pygame.font.SysFont("monospace", Fonts.HUGE)

        text = "YOU WIN!" if self._won else "GAME OVER"
        text_surface = font.render(text, True, Colors.WHITE)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(text_surface, text_rect)

        # Final score
        stats = self._score_tracker.get_stats()
        try:
            score_font = pygame.font.Font(None, Fonts.LARGE)
        except Exception:
            score_font = pygame.font.SysFont("monospace", Fonts.LARGE)

        score_text = f"Final Score: {stats.hits}"
        score_surface = score_font.render(score_text, True, Colors.YELLOW)
        score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        screen.blit(score_surface, score_rect)

        # Accuracy
        accuracy_text = f"Accuracy: {stats.accuracy:.1%}"
        accuracy_surface = score_font.render(accuracy_text, True, Colors.WHITE)
        accuracy_rect = accuracy_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70))
        screen.blit(accuracy_surface, accuracy_rect)
