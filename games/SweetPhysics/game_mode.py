"""
Sweet Physics - Cut the Rope style physics puzzle game.

Hit targets to manipulate physics elements and guide candy to the goal.
"""
import sys
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def _browser_log(msg):
    print(msg)
    if sys.platform == "emscripten":
        try:
            import platform
            platform.window.console.log(msg)
        except:
            pass

_browser_log("[SweetPhysics game_mode.py] Starting imports...")

import pygame
_browser_log("[SweetPhysics game_mode.py] pygame OK")

try:
    import pymunk
    _browser_log("[SweetPhysics game_mode.py] pymunk OK")
except Exception as e:
    _browser_log(f"[SweetPhysics game_mode.py] pymunk FAILED: {e}")
    raise

from ams.games import GameState
from ams.games.base_game import BaseGame
from ams.games.input import InputEvent
from ams.games.levels import LevelLoader
from games.SweetPhysics import config
from games.SweetPhysics.physics import PhysicsWorld
from games.SweetPhysics.elements import Candy, Rope, Goal, Star, Platform
from games.SweetPhysics.levels import SweetPhysicsLevelLoader, LevelData
from games.SweetPhysics.levels.loader import create_default_level


class LevelState(Enum):
    """State of current level."""
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


class SweetPhysicsMode(BaseGame):
    """
    Sweet Physics game mode.

    Physics puzzle game where you cut ropes and trigger mechanisms
    to guide candy to the goal.
    """

    NAME = "Sweet Physics"
    DESCRIPTION = "Cut ropes to guide candy to the goal - physics puzzle fun!"
    VERSION = "1.0.0"
    AUTHOR = "AMS Team"

    # Enable level support via BaseGame
    LEVELS_DIR = Path(__file__).parent / "levels"

    # Game-specific arguments (level args added automatically by BaseGame)
    ARGUMENTS = []

    def __init__(
        self,
        level: Optional[str] = None,
        list_levels: bool = False,
        level_group: Optional[str] = None,
        choose_level: bool = False,
        **kwargs,
    ):
        """
        Initialize Sweet Physics game.

        Args:
            level: Level name to load
            list_levels: If True, list levels and exit
            level_group: Level group to play through
            choose_level: Show level chooser UI
            **kwargs: Base game arguments
        """
        super().__init__(
            level=level,
            list_levels=list_levels,
            level_group=level_group,
            choose_level=choose_level,
            **kwargs,
        )

        # Current level data (loaded by BaseGame's _apply_level_config)
        self._current_level: Optional[LevelData] = None

        # Physics
        self._world: Optional[PhysicsWorld] = None

        # Elements
        self._candy: Optional[Candy] = None
        self._ropes: List[Rope] = []
        self._goal: Optional[Goal] = None
        self._stars: List[Star] = []
        self._platforms: List[Platform] = []

        # Game state
        self._internal_state = GameState.PLAYING
        self._level_state = LevelState.PLAYING
        self._shots_fired = 0
        self._stars_collected = 0
        self._time_elapsed = 0.0
        self._win_timer = 0.0
        self._lose_timer = 0.0

        # Screen dimensions (set on first render)
        self._screen_width = config.SCREEN_WIDTH
        self._screen_height = config.SCREEN_HEIGHT
        self._initialized = False

        # Fonts
        self._font: Optional[pygame.font.Font] = None
        self._font_large: Optional[pygame.font.Font] = None

    def _create_level_loader(self) -> LevelLoader:
        """Create the level loader for Sweet Physics."""
        return SweetPhysicsLevelLoader(self.LEVELS_DIR)

    def _apply_level_config(self, level_data: LevelData) -> None:
        """Apply loaded level configuration."""
        self._current_level = level_data

    def _on_level_transition(self) -> None:
        """Reinitialize game state for the new level."""
        self._initialize_level()

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 32)
        return self._font

    def _get_font_large(self) -> pygame.font.Font:
        if self._font_large is None:
            self._font_large = pygame.font.Font(None, 64)
        return self._font_large

    def _get_internal_state(self) -> GameState:
        return self._internal_state

    def get_score(self) -> int:
        """Return stars collected as score."""
        return self._stars_collected

    def get_available_actions(self) -> list:
        """Get actions available based on current game state."""
        actions = []

        # Always allow restart when a level is loaded
        if self._current_level is not None:
            if self._level_state == LevelState.LOST:
                # Emphasize retry when lost
                actions.append({'id': 'retry', 'label': 'Retry Level', 'style': 'primary'})
            else:
                # Secondary option during normal play
                actions.append({'id': 'retry', 'label': 'Restart Level', 'style': 'secondary'})

        if self._level_state == LevelState.LOST:
            if self._current_group:
                actions.append({'id': 'skip', 'label': 'Skip Level', 'style': 'secondary'})

        elif self._level_state == LevelState.WON:
            # During win delay, show what's coming
            if self._current_group and not self._current_group.is_complete:
                actions.append({'id': 'next', 'label': 'Next Level', 'style': 'primary'})

        return actions

    def execute_action(self, action_id: str) -> bool:
        """Execute a game action."""
        if action_id == 'retry':
            # Retry current level
            self._initialize_level()
            return True

        elif action_id == 'skip':
            # Skip to next level in group
            if self._level_complete():
                return True
            return False

        elif action_id == 'next':
            # Manually advance (if win delay hasn't auto-advanced yet)
            if self._level_state == LevelState.WON:
                if not self._level_complete():
                    self._internal_state = GameState.WON
                return True

        return False

    def _initialize_level(self) -> None:
        """Initialize or reinitialize the current level."""
        # Clear existing elements
        self._clear_elements()

        # Create physics world
        level = self._current_level
        self._world = PhysicsWorld(
            gravity=level.gravity,
            damping=level.air_resistance,
        )

        # Create bounds
        self._world.create_bounds(self._screen_width, self._screen_height)

        # Create elements from level data
        candy_pos = None
        rope_attachments: Dict[str, pymunk.Body] = {}

        # First pass: create candy and goal
        for elem in level.elements:
            if elem.type == 'candy':
                pos = elem.position or (self._screen_width // 2, 150)
                self._candy = Candy(self._world, pos)
                rope_attachments['candy'] = self._candy.body

            elif elem.type == 'goal':
                pos = elem.position or (self._screen_width // 2, self._screen_height - 100)
                radius = elem.radius or config.GOAL_RADIUS
                self._goal = Goal(self._world, pos, radius)

            elif elem.type == 'star':
                pos = elem.position or (self._screen_width // 2, self._screen_height // 2)
                self._stars.append(Star(self._world, pos))

            elif elem.type == 'platform':
                if elem.start and elem.end:
                    self._platforms.append(Platform(
                        self._world,
                        elem.start,
                        elem.end,
                        thickness=elem.thickness,
                    ))

        # Second pass: create ropes (need candy body)
        for elem in level.elements:
            if elem.type == 'rope':
                anchor = elem.anchor or (self._screen_width // 2, 50)
                attach_body = None

                if elem.attachment and elem.attachment in rope_attachments:
                    attach_body = rope_attachments[elem.attachment]

                rope = Rope(
                    self._world,
                    anchor,
                    attach_body=attach_body,
                    length=elem.length,
                    segments=elem.segments,
                )
                self._ropes.append(rope)

        # Set up collision handlers
        self._setup_collisions()

        # Reset state
        self._level_state = LevelState.PLAYING
        self._shots_fired = 0
        self._stars_collected = 0
        self._time_elapsed = 0.0
        self._win_timer = 0.0
        self._lose_timer = 0.0

    def _clear_elements(self) -> None:
        """Clear all game elements."""
        if self._candy:
            self._candy.remove()
            self._candy = None

        for rope in self._ropes:
            rope.remove()
        self._ropes.clear()

        if self._goal:
            self._goal.remove()
            self._goal = None

        for star in self._stars:
            star.remove()
        self._stars.clear()

        for platform in self._platforms:
            platform.remove()
        self._platforms.clear()

        if self._world:
            self._world.clear()
            self._world = None

    def _setup_collisions(self) -> None:
        """Set up collision handlers."""
        if self._world is None:
            return

        # Candy-Star collision (collect star)
        def candy_star_begin(arbiter, space, data):
            shapes = arbiter.shapes
            for shape in shapes:
                if hasattr(shape, 'star') and not shape.star.collected:
                    shape.star.collect()
                    self._stars_collected += 1
            return True

        self._world.add_collision_handler(
            config.COLLISION_CANDY,
            config.COLLISION_STAR,
            begin=candy_star_begin,
        )

    def _ensure_level_loaded(self) -> None:
        """Ensure a level is loaded (use default if none specified)."""
        if self._current_level is None:
            # No level was loaded via BaseGame, use default
            self._current_level = create_default_level()

    def update(self, dt: float) -> None:
        """Update game state."""
        # Handle retrieval
        if self._in_retrieval:
            if self._quiver and not self._quiver.is_manual_retrieval:
                if self._update_retrieval(dt):
                    self._end_retrieval()
            return

        if self._internal_state != GameState.PLAYING:
            return

        # Initialize on first update
        if not self._initialized:
            self._ensure_level_loaded()
            self._initialize_level()
            self._initialized = True

        if self._world is None or self._candy is None:
            return

        # Update based on level state
        if self._level_state == LevelState.PLAYING:
            self._time_elapsed += dt

            # Update physics
            self._world.update(dt)

            # Update elements
            self._candy.update(dt)
            if self._goal:
                self._goal.update(dt)
            for star in self._stars:
                star.update(dt)

            # Check win/lose conditions
            self._check_level_state()

        elif self._level_state == LevelState.WON:
            self._win_timer += dt
            if self._win_timer > config.WIN_DELAY:
                # Try to advance to next level in group
                if not self._level_complete():
                    # No more levels (or not in a group), game complete
                    self._internal_state = GameState.WON

        elif self._level_state == LevelState.LOST:
            self._lose_timer += dt
            if self._lose_timer > config.FAIL_DELAY:
                # Stay in playing state but show retry UI
                pass

    def _check_level_state(self) -> None:
        """Check win/lose conditions."""
        if self._candy is None or self._goal is None:
            return

        # Check if candy reached goal
        if self._goal.contains_candy(self._candy.position, self._candy.radius):
            self._candy.reached_goal = True
            self._level_state = LevelState.WON
            return

        # Check if candy out of bounds
        if self._candy.is_out_of_bounds(self._screen_width, self._screen_height):
            self._candy.lost = True
            self._level_state = LevelState.LOST
            return

    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events."""
        if self._internal_state != GameState.PLAYING:
            return

        if self._level_state != LevelState.PLAYING:
            return

        for event in events:
            # Check quiver
            if self._quiver and self._quiver.is_empty:
                continue

            x, y = event.position.x, event.position.y
            hit_something = False

            # Check ropes for cuts
            for rope in self._ropes:
                if rope.active and rope.check_hit(x, y, config.HIT_RADIUS):
                    if rope.on_hit(x, y):
                        hit_something = True
                        break

            # Count shot
            self._shots_fired += 1

            # Use shot from quiver
            if self._use_shot():
                self._start_retrieval()

    def handle_pygame_event(self, event: pygame.event.Event) -> bool:
        """Handle pygame events."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r and self._level_state == LevelState.LOST:
                # Restart level
                self._initialize_level()
                return True
        return False

    def render(self, screen: pygame.Surface) -> None:
        """Render the game."""
        # Update screen dimensions
        self._screen_width = screen.get_width()
        self._screen_height = screen.get_height()

        # Background
        screen.fill(config.BACKGROUND_COLOR)

        if not self._initialized:
            self._render_loading(screen)
            return

        # Render elements (order matters for layering)
        # Platforms first (background)
        for platform in self._platforms:
            platform.render(screen)

        # Goal
        if self._goal:
            self._goal.render(screen)

        # Stars
        for star in self._stars:
            star.render(screen)

        # Ropes
        for rope in self._ropes:
            rope.render(screen)

        # Candy on top
        if self._candy:
            self._candy.render(screen)

        # UI
        self._render_ui(screen)

        # State overlays
        if self._level_state == LevelState.WON:
            self._render_win(screen)
        elif self._level_state == LevelState.LOST:
            self._render_lost(screen)

        # Retrieval overlay
        if self.state == GameState.RETRIEVAL:
            self._render_retrieval(screen)

    def _render_loading(self, screen: pygame.Surface) -> None:
        """Render loading screen."""
        font = self._get_font_large()
        text = font.render("Loading...", True, config.TEXT_COLOR)
        rect = text.get_rect(center=(self._screen_width // 2, self._screen_height // 2))
        screen.blit(text, rect)

    def _render_ui(self, screen: pygame.Surface) -> None:
        """Render UI elements."""
        font = self._get_font()

        # Level name
        if self._current_level:
            name_text = font.render(self._current_level.name, True, config.TEXT_COLOR)
            screen.blit(name_text, (config.MARGIN, config.MARGIN))

        # Stars collected
        star_text = f"Stars: {self._stars_collected}/{len(self._stars)}"
        stars_render = font.render(star_text, True, config.STAR_COLOR)
        screen.blit(stars_render, (config.MARGIN, config.MARGIN + 35))

        # Shots fired
        if self._current_level and self._current_level.arrow_budget:
            remaining = self._current_level.arrow_budget - self._shots_fired
            shots_color = (255, 100, 100) if remaining <= 1 else config.TEXT_COLOR
            shots_text = font.render(f"Shots: {remaining}", True, shots_color)
        else:
            shots_text = font.render(f"Shots: {self._shots_fired}", True, config.TEXT_COLOR)
        screen.blit(shots_text, (self._screen_width - 150, config.MARGIN))

        # Time
        time_text = font.render(f"Time: {self._time_elapsed:.1f}s", True, config.HEADER_COLOR)
        screen.blit(time_text, (self._screen_width - 150, config.MARGIN + 35))

        # Quiver status
        if self._quiver:
            quiver_text = font.render(
                self._quiver.get_display_text(),
                True,
                (255, 100, 100) if self._quiver.remaining <= 2 else config.TEXT_COLOR
            )
            screen.blit(quiver_text, (self._screen_width - 150, config.MARGIN + 70))

    def _render_win(self, screen: pygame.Surface) -> None:
        """Render win overlay."""
        font_large = self._get_font_large()
        font = self._get_font()

        # Overlay
        overlay = pygame.Surface((self._screen_width, self._screen_height), pygame.SRCALPHA)
        overlay.fill((0, 50, 0, 150))
        screen.blit(overlay, (0, 0))

        # Win text
        text = font_large.render("LEVEL COMPLETE!", True, (100, 255, 100))
        rect = text.get_rect(center=(self._screen_width // 2, self._screen_height // 2 - 50))
        screen.blit(text, rect)

        # Stats
        stats = [
            f"Stars: {self._stars_collected}/{len(self._stars)}",
            f"Shots: {self._shots_fired}",
            f"Time: {self._time_elapsed:.1f}s",
        ]
        y = self._screen_height // 2 + 20
        for stat in stats:
            stat_text = font.render(stat, True, config.TEXT_COLOR)
            stat_rect = stat_text.get_rect(center=(self._screen_width // 2, y))
            screen.blit(stat_text, stat_rect)
            y += 35

    def _render_lost(self, screen: pygame.Surface) -> None:
        """Render lose overlay."""
        font_large = self._get_font_large()
        font = self._get_font()

        # Overlay
        overlay = pygame.Surface((self._screen_width, self._screen_height), pygame.SRCALPHA)
        overlay.fill((50, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Lose text
        text = font_large.render("CANDY LOST!", True, (255, 100, 100))
        rect = text.get_rect(center=(self._screen_width // 2, self._screen_height // 2 - 30))
        screen.blit(text, rect)

        # Retry hint
        hint = font.render("Press R to retry", True, config.TEXT_COLOR)
        hint_rect = hint.get_rect(center=(self._screen_width // 2, self._screen_height // 2 + 30))
        screen.blit(hint, hint_rect)

    def _render_retrieval(self, screen: pygame.Surface) -> None:
        """Render retrieval overlay."""
        if not self._quiver:
            return

        font_large = self._get_font_large()
        font = self._get_font()

        # Overlay
        overlay = pygame.Surface((self._screen_width, self._screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        # Title
        title = font_large.render("RETRIEVAL", True, (255, 200, 100))
        title_rect = title.get_rect(center=(self._screen_width // 2, self._screen_height // 2 - 30))
        screen.blit(title, title_rect)

        # Instructions
        instr = font.render(self._quiver.get_retrieval_text(), True, config.TEXT_COLOR)
        instr_rect = instr.get_rect(center=(self._screen_width // 2, self._screen_height // 2 + 20))
        screen.blit(instr, instr_rect)
