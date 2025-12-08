"""Containment Game Mode.

Adversarial containment game where a ball tries to escape through gaps.
Player places deflectors to build walls and contain the ball.
Direct hits on the ball are penalized (it speeds up).
"""
import math
import random
from pathlib import Path
from typing import List, Optional, Tuple

import pygame

from models import Vector2D
from games.common import GameState
from games.common.base_game import BaseGame
from games.Containment.ball import Ball, create_ball
from games.Containment.deflector import Deflector, DeflectorManager, create_deflector
from games.Containment.gap import GapManager
from games.Containment.spinner import SpinnerManager, create_spinner
from games.Containment.grow_obstacle import GrowObstacle
from games.Containment.morph_obstacle import MorphObstacle, create_morph_obstacle
from games.Containment import config
from games.Containment.levels import (
    LevelConfig,
    load_level,
    apply_pacing_overrides,
    list_levels,
    get_levels_dir,
    resolve_hit_mode_angle,
    resolve_random_value,
    shape_name_to_sides,
)
from games.Containment.level_chooser import LevelChooser


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
        # Level file
        {
            'name': '--level',
            'type': str,
            'default': None,
            'help': 'Path to level YAML file (overrides other settings)'
        },
        {
            'name': '--choose-level',
            'action': 'store_true',
            'default': False,
            'help': 'Show level chooser UI before starting'
        },

        # Pacing (standard AMS parameter)
        {
            'name': '--pacing',
            'type': str,
            'default': 'throwing',
            'help': 'Pacing preset: archery, throwing, blaster'
        },

        # Game mode
        {
            'name': '--mode',
            'type': str,
            'default': 'classic',
            'help': 'Game mode: classic (static walls), dynamic (rotating spinners)'
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

        # Time/scoring
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
            'help': 'Number of gaps (overrides preset, classic mode only)'
        },
        {
            'name': '--spinner-count',
            'type': int,
            'default': 3,
            'help': 'Number of spinners (dynamic mode only)'
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
        # Level file (overrides other settings)
        level: Optional[str] = None,
        choose_level: bool = False,
        # Pacing (device speed)
        pacing: str = 'throwing',
        # Game mode
        mode: str = 'classic',
        # Tempo (game intensity)
        tempo: str = 'mid',
        # AI behavior
        ai: str = 'dumb',
        # Time/scoring
        time_limit: int = 60,
        gap_count: Optional[int] = None,
        spinner_count: int = 3,
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
            level: Path to level YAML file (overrides other settings)
            choose_level: Show level chooser UI before starting
            pacing: Device pacing preset (archery, throwing, blaster)
            mode: Game mode - 'classic' (static walls) or 'dynamic' (rotating spinners)
            tempo: Game intensity preset (zen, mid, wild)
            ai: AI behavior level (dumb, reactive, strategic)
            time_limit: Seconds to survive (0 = endless)
            gap_count: Number of gaps (None = use preset, classic mode only)
            spinner_count: Number of spinners (dynamic mode only)
            max_deflectors: Maximum deflectors allowed (None = unlimited)
            quiver_size: Shots before retrieval (None = use preset)
            retrieval_pause: Seconds for retrieval (0 = manual)
            color_palette: AMS-provided color palette
            palette_name: Test palette name for standalone mode
        """
        # Level chooser state
        self._show_level_chooser = choose_level and level is None
        self._level_chooser: Optional[LevelChooser] = None

        # Store level path and load if specified
        self._level_path = level
        self._level_config: Optional[LevelConfig] = None

        if level:
            # Load level from YAML
            level_path = Path(level)
            if not level_path.is_absolute():
                # Check if it's a built-in level name
                levels_dir = get_levels_dir()
                possible_paths = [
                    levels_dir / f"{level}.yaml",
                    levels_dir / "examples" / f"{level}.yaml",
                    levels_dir / "tutorial" / f"{level}.yaml",
                    levels_dir / "campaign" / f"{level}.yaml",
                    levels_dir / "challenge" / f"{level}.yaml",
                    level_path,
                ]
                for p in possible_paths:
                    if p.exists():
                        level_path = p
                        break

            self._level_config = load_level(level_path)
            self._level_config = apply_pacing_overrides(self._level_config, pacing)

            # Override parameters from level
            mode = "dynamic" if self._level_config.environment.spinners else "classic"
            if self._level_config.environment.edges.mode == "gaps":
                mode = "classic"
            time_limit = self._level_config.objectives.time_limit or 0
            ai = self._level_config.ball.ai

        # Load presets
        self._pacing = config.get_pacing_preset(pacing)
        self._tempo = config.get_tempo_preset(tempo)
        self._ai_level = ai
        self._game_mode = mode  # 'classic' or 'dynamic'

        # Calculate effective parameters (level overrides if present)
        if self._level_config:
            self._ball_speed = self._level_config.ball.speed
            self._ball_radius = self._level_config.ball.radius
        else:
            self._ball_speed = self._pacing.ball_speed * self._tempo.ball_speed_multiplier
            self._ball_radius = self._pacing.ball_radius

        self._gap_count = gap_count if gap_count is not None else max(
            1, self._pacing.gap_count + self._tempo.gap_count_modifier
        )
        self._spinner_count = spinner_count
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
        self._spinners: Optional[SpinnerManager] = None

        # Point obstacles (for point hit mode)
        self._points: List[Tuple[Vector2D, float, Tuple[int, int, int]]] = []

        # Grow obstacles (for grow hit mode)
        self._grows: List[GrowObstacle] = []

        # Morph obstacles (for morph hit mode)
        self._morphs: List[MorphObstacle] = []

        # Hit positions tracking (for connect hit mode)
        self._hit_positions: List[Vector2D] = []

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
        # Clear point obstacles
        self._points = []

        # Clear grow obstacles
        self._grows = []

        # Clear morph obstacles
        self._morphs = []

        # Clear hit positions
        self._hit_positions = []

        # Get ball radius (from level or pacing)
        ball_radius = self._ball_radius if hasattr(self, '_ball_radius') else self._pacing.ball_radius

        # Create ball
        ball_color = self._palette.random_target_color()
        self._ball = create_ball(
            screen_width=self._screen_width,
            screen_height=self._screen_height,
            base_speed=self._ball_speed,
            radius=ball_radius,
            color=ball_color,
        )

        # Create deflector manager
        self._deflectors = DeflectorManager(
            default_length=self._pacing.deflector_length
        )
        deflector_color = self._palette.get_ui_color()
        self._deflectors.default_color = deflector_color

        # Initialize spinners manager (may be used in classic mode too if level defines them)
        self._spinners = SpinnerManager()
        spinner_color = self._palette.get_ui_color()

        if self._level_config:
            # Load from level configuration
            self._init_from_level(spinner_color)
        elif self._game_mode == 'classic':
            # Classic mode: static walls with gaps
            self._gaps = GapManager(
                screen_width=self._screen_width,
                screen_height=self._screen_height,
                gap_width=self._pacing.gap_width,
            )
            self._gaps.create_gaps(self._gap_count)
        else:
            # Dynamic mode: rotating spinners, no static gaps
            self._gaps = None
            self._spinners.create_default_layout(
                screen_width=self._screen_width,
                screen_height=self._screen_height,
                count=self._spinner_count,
                color=spinner_color,
            )

        # Reset state
        self._state = GameState.PLAYING
        self._time_elapsed = 0.0

        # Reset hit mode sequence if using level
        if self._level_config:
            self._level_config.hit_modes.reset_sequence()

    def _init_from_level(self, spinner_color: Tuple[int, int, int]) -> None:
        """Initialize game entities from level configuration."""
        level = self._level_config
        if not level:
            return

        # Setup gaps (classic mode)
        if level.environment.edges.mode == "gaps" and level.environment.edges.gaps:
            self._gaps = GapManager(
                screen_width=self._screen_width,
                screen_height=self._screen_height,
                gap_width=self._pacing.gap_width,
            )
            # Create gaps from level definition
            for gap_config in level.environment.edges.gaps:
                self._gaps.add_gap_from_config(
                    edge=gap_config.edge,
                    start_ratio=gap_config.range[0],
                    end_ratio=gap_config.range[1]
                )
        else:
            self._gaps = None

        # Setup spinners from level
        if level.environment.spinners:
            for spinner_config in level.environment.spinners:
                # Convert normalized position to screen coordinates
                x = spinner_config.position[0] * self._screen_width
                y = spinner_config.position[1] * self._screen_height

                sides = shape_name_to_sides(spinner_config.shape)

                self._spinners.add_spinner(
                    position=Vector2D(x=x, y=y),
                    size=spinner_config.size,
                    sides=sides,
                    rotation_speed=spinner_config.rotation_speed,
                    color=spinner_color,
                )

    def get_score(self) -> int:
        """Get current score (time survived in seconds)."""
        return int(self._time_elapsed)

    def _on_level_selected(self, level_path: str) -> None:
        """Callback when a level is selected in the level chooser.

        Args:
            level_path: Path to the selected level YAML file
        """
        self._show_level_chooser = False
        self._level_chooser = None

        # Load and apply the selected level
        self._level_path = level_path
        level_path_obj = Path(level_path)
        self._level_config = load_level(level_path_obj)
        self._level_config = apply_pacing_overrides(self._level_config, 'throwing')

        # Override parameters from level
        self._game_mode = "dynamic" if self._level_config.environment.spinners else "classic"
        if self._level_config.environment.edges.mode == "gaps":
            self._game_mode = "classic"
        self._time_limit = self._level_config.objectives.time_limit or 0
        self._ai_level = self._level_config.ball.ai
        self._ball_speed = self._level_config.ball.speed
        self._ball_radius = self._level_config.ball.radius

        # Reinitialize game with new level
        self._init_game()

    def _on_level_chooser_back(self) -> None:
        """Callback when back/default is selected in the level chooser."""
        self._show_level_chooser = False
        self._level_chooser = None
        # Continue with default game (already initialized)

    def handle_pygame_event(self, event: pygame.event.Event) -> bool:
        """Handle raw pygame events (for level chooser mouse support).

        Args:
            event: Pygame event to handle

        Returns:
            True if the event was consumed, False otherwise
        """
        if self._show_level_chooser and self._level_chooser:
            result = self._level_chooser.handle_event(event)
            if result:
                if result == "__back__":
                    self._on_level_chooser_back()
                else:
                    self._on_level_selected(result)
                return True
            # Even if no result, level chooser may have consumed the event (hover, scroll)
            if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                return True
        return False

    def handle_input(self, events: List) -> None:
        """Process input events (shots).

        Args:
            events: List of InputEvent objects
        """
        # Handle level chooser input
        if self._show_level_chooser:
            # Level chooser handles its own mouse events via pygame events
            # For AMS hits, convert to level chooser hits
            for event in events:
                if self._level_chooser:
                    result = self._level_chooser.handle_hit(event.position)
                    if result:
                        if result == "__back__":
                            self._on_level_chooser_back()
                        else:
                            self._on_level_selected(result)
            return

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

            # Handle hit based on level config or default behavior
            if self._level_config:
                self._handle_level_hit(position)
            else:
                # Default: place deflector
                if self._deflectors is not None:
                    # Check max deflectors limit
                    if self._max_deflectors and self._deflectors.count >= self._max_deflectors:
                        continue

                    self._deflectors.add_deflector(position)

            # Check quiver
            if self._use_shot():
                self._start_retrieval()

    def _handle_level_hit(self, position: Vector2D) -> None:
        """Handle a hit using level-defined hit modes.

        Args:
            position: Where the hit occurred
        """
        if not self._level_config:
            return

        # FIRST: Check if hit is inside an existing grow obstacle
        # If so, grow it instead of spawning a new obstacle
        for grow in self._grows:
            if grow.try_grow(position):
                return  # Grew existing obstacle, don't spawn new one

        # Get next hit mode
        hit_mode = self._level_config.hit_modes.get_next_mode()
        mode_type = hit_mode.type
        mode_config = hit_mode.config

        # Get ball position for directional calculations
        ball_pos = None
        if self._ball:
            ball_pos = (self._ball.position.x, self._ball.position.y)

        hit_pos = (position.x, position.y)
        ui_color = self._palette.get_ui_color()

        if mode_type == "deflector":
            self._spawn_deflector(position, mode_config, ball_pos, hit_pos, ui_color)

        elif mode_type == "spinner":
            self._spawn_spinner(position, mode_config, ui_color)

        elif mode_type == "point":
            self._spawn_point(position, mode_config, ui_color)

        elif mode_type == "connect":
            self._spawn_connect(position, mode_config, ui_color)

        elif mode_type == "morph":
            self._spawn_morph(position, mode_config, ui_color)

        elif mode_type == "grow":
            self._spawn_grow(position, mode_config, ui_color)

    def _spawn_deflector(
        self,
        position: Vector2D,
        config_dict: dict,
        ball_pos: Optional[Tuple[float, float]],
        hit_pos: Tuple[float, float],
        color: Tuple[int, int, int]
    ) -> None:
        """Spawn a deflector from hit mode config."""
        if self._deflectors is None:
            return

        # Check max deflectors limit
        if self._max_deflectors and self._deflectors.count >= self._max_deflectors:
            return

        # Resolve angle
        angle = resolve_hit_mode_angle(config_dict, ball_pos, hit_pos)

        # Get length (may be a range)
        length = resolve_random_value(config_dict.get("length", 60))

        # Use custom color or default
        custom_color = config_dict.get("color")
        deflector_color = tuple(custom_color) if custom_color else color

        deflector = create_deflector(
            position=position,
            length=length,
            angle=angle,
            color=deflector_color,
        )
        self._deflectors.deflectors.append(deflector)

    def _spawn_spinner(
        self,
        position: Vector2D,
        config_dict: dict,
        color: Tuple[int, int, int]
    ) -> None:
        """Spawn a spinner from hit mode config."""
        if self._spinners is None:
            return

        # Resolve shape
        shape = config_dict.get("shape", "random")
        sides = shape_name_to_sides(shape)

        # Resolve size (may be a range)
        size = resolve_random_value(config_dict.get("size", 50))

        # Resolve rotation speed (may be a range)
        rotation_speed = resolve_random_value(config_dict.get("rotation_speed", 45))

        # Randomly flip rotation direction
        if random.random() < 0.5:
            rotation_speed = -rotation_speed

        # Use custom color or default
        custom_color = config_dict.get("color")
        spinner_color = tuple(custom_color) if custom_color else color

        self._spinners.add_spinner(
            position=position,
            size=size,
            sides=sides,
            rotation_speed=rotation_speed,
            color=spinner_color,
        )

    def _spawn_point(
        self,
        position: Vector2D,
        config_dict: dict,
        color: Tuple[int, int, int]
    ) -> None:
        """Spawn a point obstacle from hit mode config."""
        # Resolve radius (may be a range)
        radius = resolve_random_value(config_dict.get("radius", 15))

        # Use custom color or default
        custom_color = config_dict.get("color")
        point_color = tuple(custom_color) if custom_color else color

        self._points.append((position, radius, point_color))

    def _spawn_connect(
        self,
        position: Vector2D,
        config_dict: dict,
        color: Tuple[int, int, int]
    ) -> None:
        """Spawn a connect-the-dots deflector from hit mode config.

        Behavior:
        - If there's a dot within threshold: create wall FROM the dot TO the hit,
          consume the dot (becomes a vertex), and leave a new dot at hit position
        - Multiple consecutive hits within threshold chain into multi-segment walls
        - If no dots within threshold: drop a new dot at hit position

        This creates a "connect the dots" mechanic where each hit extends the wall
        from the previous dot to the current position.
        """
        # Get threshold distance
        threshold = config_dict.get("threshold", 100)
        fallback_config = config_dict.get("fallback_config", {})

        # Find nearest previous dot within threshold
        nearest_dot = None
        nearest_dot_idx = -1
        nearest_distance = float('inf')

        for idx, prev_pos in enumerate(self._hit_positions):
            dx = position.x - prev_pos.x
            dy = position.y - prev_pos.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < nearest_distance and distance <= threshold:
                nearest_distance = distance
                nearest_dot = prev_pos
                nearest_dot_idx = idx

        if nearest_dot is not None:
            # Found a dot to connect from - create wall from dot to hit position
            if self._deflectors is not None:
                # Check max deflectors limit
                if not (self._max_deflectors and self._deflectors.count >= self._max_deflectors):
                    # Calculate angle from dot to current hit position
                    dx = position.x - nearest_dot.x
                    dy = position.y - nearest_dot.y
                    angle_rad = math.atan2(dy, dx)

                    # Deflectors are centered, so position at midpoint between dot and hit
                    midpoint = Vector2D(
                        x=(nearest_dot.x + position.x) / 2,
                        y=(nearest_dot.y + position.y) / 2
                    )

                    # Length is the distance between the dot and hit
                    length = nearest_distance

                    # Use custom color or default
                    custom_color = config_dict.get("color")
                    deflector_color = tuple(custom_color) if custom_color else color

                    # Create deflector centered at midpoint, spanning from dot to hit
                    deflector = Deflector(
                        position=midpoint,
                        angle=angle_rad,  # Deflector uses radians internally
                        length=length,
                        color=deflector_color,
                    )
                    self._deflectors.deflectors.append(deflector)

            # Consume the connected dot - remove from hit positions list
            del self._hit_positions[nearest_dot_idx]

            # Remove the visual point for the consumed dot
            self._points = [
                p for p in self._points
                if not (abs(p[0].x - nearest_dot.x) < 1 and abs(p[0].y - nearest_dot.y) < 1)
            ]

            # The hit position becomes a new dot (vertex for potential next segment)
            self._hit_positions.append(position)
            self._spawn_point(position, fallback_config, color)
        else:
            # No nearby dots - drop a new dot at this position
            self._hit_positions.append(position)
            self._spawn_point(position, fallback_config, color)

    def _spawn_morph(
        self,
        position: Vector2D,
        config_dict: dict,
        color: Tuple[int, int, int]
    ) -> None:
        """Spawn a morph obstacle from hit mode config.

        Args:
            position: Where to spawn the morph obstacle
            config_dict: Configuration dictionary from level
            color: Default color to use
        """
        # Get shapes list (convert from names to side counts)
        shape_names = config_dict.get("shapes", ["triangle", "square", "pentagon"])
        shapes = [shape_name_to_sides(name) for name in shape_names]

        # Resolve size (may be a range)
        size = resolve_random_value(config_dict.get("size", 50))

        # Resolve rotation speed (may be a range)
        rotation_speed = resolve_random_value(config_dict.get("rotation_speed", 30))

        # Randomly flip rotation direction
        if random.random() < 0.5:
            rotation_speed = -rotation_speed

        # Get morph interval
        morph_interval = config_dict.get("morph_interval", 2.0)

        # Get pulsate settings
        pulsate = config_dict.get("pulsate", False)
        pulsate_amount = config_dict.get("pulsate_amount", 0.15)

        # Use custom color or default
        custom_color = config_dict.get("color")
        morph_color = tuple(custom_color) if custom_color else color

        morph = create_morph_obstacle(
            position=position,
            shapes=shapes,
            size=size,
            rotation_speed=rotation_speed,
            morph_interval=morph_interval,
            pulsate=pulsate,
            pulsate_amount=pulsate_amount,
            color=morph_color,
        )
        self._morphs.append(morph)

    def _spawn_grow(
        self,
        position: Vector2D,
        config_dict: dict,
        color: Tuple[int, int, int]
    ) -> None:
        """Spawn a grow obstacle from hit mode config.

        Args:
            position: Where to spawn the grow obstacle
            config_dict: Configuration dictionary from level
            color: Default color to use
        """
        # Resolve initial size (may be a range)
        initial_size = resolve_random_value(config_dict.get("initial_size", 30))

        # Get growth parameters
        growth_per_hit = config_dict.get("growth_per_hit", 0.3)
        max_size = config_dict.get("max_size", 150)
        decay_rate = config_dict.get("decay_rate", 0)

        # Use custom color or default
        custom_color = config_dict.get("color")
        grow_color = tuple(custom_color) if custom_color else color

        grow = GrowObstacle(
            position=position,
            initial_size=initial_size,
            growth_per_hit=growth_per_hit,
            max_size=max_size,
            decay_rate=decay_rate,
            color=grow_color,
        )
        self._grows.append(grow)

    def update(self, dt: float) -> None:
        """Update game state.

        Args:
            dt: Delta time in seconds since last update
        """
        # Handle level chooser UI
        if self._show_level_chooser:
            if self._level_chooser:
                self._level_chooser.update(dt)
            return

        # Handle retrieval state (BaseGame manages _in_retrieval flag)
        if self.state == GameState.RETRIEVAL:
            # Update retrieval timer
            if self._update_retrieval(dt):
                self._end_retrieval()
            return

        if self._state != GameState.PLAYING:
            return

        if self._ball is None:
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

        # Update spinners (dynamic mode)
        if self._spinners:
            self._spinners.update(dt)

        # Update morph obstacles
        for morph in self._morphs:
            morph.update(dt)

        # Update grow obstacles (remove any that decay away)
        self._grows = [grow for grow in self._grows if grow.update(dt)]

        # Mode-specific collision handling
        if self._game_mode == 'classic' and self._gaps:
            # Classic mode: check wall/gap collisions
            wall_hit = self._gaps.check_wall_collision(
                self._ball.position,
                self._ball.radius,
                self._ball.velocity
            )
            if wall_hit == 'horizontal':
                self._ball.bounce_off_horizontal()
                self._clamp_ball_position()
            elif wall_hit == 'vertical':
                self._ball.bounce_off_vertical()
                self._clamp_ball_position()
        else:
            # Dynamic mode: bounce off all screen edges
            self._check_screen_edge_collision()

        # Check spinner collisions (dynamic mode)
        if self._spinners:
            collision = self._spinners.check_ball_collision(
                self._ball.position,
                self._ball.radius
            )
            if collision:
                normal, penetration = collision
                self._ball.bounce_off_surface(normal, push_out=penetration)

        # Check deflector collisions (both modes)
        if self._deflectors:
            collision = self._deflectors.check_ball_collision(
                self._ball.position,
                self._ball.radius
            )
            if collision:
                normal, penetration = collision
                self._ball.bounce_off_surface(normal, push_out=penetration)

        # Check point obstacle collisions
        self._check_point_collisions()

        # Check morph obstacle collisions
        self._check_morph_collisions()

        # Check grow obstacle collisions
        self._check_grow_collisions()

        # Check escape (classic mode only)
        if self._gaps and self._gaps.check_escape(self._ball.position, self._ball.radius):
            self._state = GameState.GAME_OVER
            self._score = int(self._time_elapsed)

    def _check_point_collisions(self) -> None:
        """Check for collisions with point obstacles."""
        if not self._ball or not self._points:
            return

        ball_pos = self._ball.position
        ball_radius = self._ball.radius

        for point_pos, point_radius, _ in self._points:
            # Distance between centers
            dx = ball_pos.x - point_pos.x
            dy = ball_pos.y - point_pos.y
            distance = math.sqrt(dx * dx + dy * dy)

            # Check for collision
            min_dist = ball_radius + point_radius
            if distance < min_dist:
                # Collision! Calculate normal and penetration
                if distance > 0:
                    normal = Vector2D(x=dx / distance, y=dy / distance)
                    penetration = min_dist - distance
                    self._ball.bounce_off_surface(normal, push_out=penetration)
                break  # Handle one collision per frame

    def _check_morph_collisions(self) -> None:
        """Check for collisions with morph obstacles."""
        if not self._ball or not self._morphs:
            return

        ball_pos = self._ball.position
        ball_radius = self._ball.radius

        for morph in self._morphs:
            collision = morph.check_ball_collision(ball_pos, ball_radius)
            if collision:
                normal, penetration = collision
                self._ball.bounce_off_surface(normal, push_out=penetration)
                break  # Handle one collision per frame

    def _check_grow_collisions(self) -> None:
        """Check for collisions with grow obstacles."""
        if not self._ball or not self._grows:
            return

        ball_pos = self._ball.position
        ball_radius = self._ball.radius

        for grow in self._grows:
            collision = grow.check_ball_collision(ball_pos, ball_radius)
            if collision:
                normal, penetration = collision
                self._ball.bounce_off_surface(normal, push_out=penetration)
                break  # Handle one collision per frame

    def _check_screen_edge_collision(self) -> None:
        """Check and handle collisions with screen edges (dynamic mode)."""
        if self._ball is None:
            return

        bounced = False
        pos = self._ball.position
        radius = self._ball.radius

        # Left edge
        if pos.x - radius <= 0:
            self._ball.bounce_off_vertical()
            self._ball.position = Vector2D(x=radius + 1, y=pos.y)
            bounced = True
        # Right edge
        elif pos.x + radius >= self._screen_width:
            self._ball.bounce_off_vertical()
            self._ball.position = Vector2D(x=self._screen_width - radius - 1, y=pos.y)
            bounced = True

        pos = self._ball.position  # Get updated position

        # Top edge
        if pos.y - radius <= 0:
            self._ball.bounce_off_horizontal()
            self._ball.position = Vector2D(x=pos.x, y=radius + 1)
            bounced = True
        # Bottom edge
        elif pos.y + radius >= self._screen_height:
            self._ball.bounce_off_horizontal()
            self._ball.position = Vector2D(x=pos.x, y=self._screen_height - radius - 1)
            bounced = True

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

        # Handle level chooser UI
        if self._show_level_chooser:
            # Initialize level chooser if needed
            if self._level_chooser is None:
                self._level_chooser = LevelChooser(
                    screen_width=self._screen_width,
                    screen_height=self._screen_height,
                    on_level_selected=self._on_level_selected,
                    on_back=self._on_level_chooser_back,
                )
            self._level_chooser.render(screen)
            return

        # Clear screen
        bg_color = self._palette.get_background_color()
        screen.fill(bg_color)

        # Draw walls (screen edges that aren't gaps)
        self._render_walls(screen)

        # Draw gaps (highlighted danger zones) - classic mode
        self._render_gaps(screen)

        # Draw spinners - dynamic mode
        self._render_spinners(screen)

        # Draw deflectors
        self._render_deflectors(screen)

        # Draw point obstacles
        self._render_points(screen)

        # Draw morph obstacles
        self._render_morphs(screen)

        # Draw grow obstacles
        self._render_grows(screen)

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

    def _render_spinners(self, screen: pygame.Surface) -> None:
        """Render rotating spinner obstacles."""
        if self._spinners is None:
            return

        for spinner in self._spinners.spinners:
            # Draw filled polygon
            points = spinner.get_render_points()
            if len(points) >= 3:
                pygame.draw.polygon(screen, spinner.color, points, 0)  # Filled
                # Draw outline for better visibility
                outline_color = tuple(min(255, c + 50) for c in spinner.color)
                pygame.draw.polygon(screen, outline_color, points, 2)  # Outline

            # Draw center point
            center = (int(spinner.position.x), int(spinner.position.y))
            pygame.draw.circle(screen, spinner.color, center, 4)

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

    def _render_points(self, screen: pygame.Surface) -> None:
        """Render point obstacles."""
        for point_pos, radius, color in self._points:
            pos = (int(point_pos.x), int(point_pos.y))
            pygame.draw.circle(screen, color, pos, int(radius))
            # Draw outline for better visibility
            outline_color = tuple(min(255, c + 50) for c in color)
            pygame.draw.circle(screen, outline_color, pos, int(radius), 2)

    def _render_grows(self, screen: pygame.Surface) -> None:
        """Render grow obstacles."""
        font_small = pygame.font.Font(None, 20)

        for grow in self._grows:
            pos = grow.get_render_pos()
            radius = int(grow.radius)

            # Draw filled circle
            pygame.draw.circle(screen, grow.color, pos, radius)

            # Draw outline for better visibility
            outline_color = tuple(min(255, c + 50) for c in grow.color)
            pygame.draw.circle(screen, outline_color, pos, radius, 2)

            # Draw hit count at center
            if grow.hit_count > 1:
                hit_text = f"{grow.hit_count}"
                text = font_small.render(hit_text, True, (255, 255, 255))
                text_rect = text.get_rect(center=pos)
                screen.blit(text, text_rect)

    def _render_morphs(self, screen: pygame.Surface) -> None:
        """Render morph obstacles."""
        for morph in self._morphs:
            # Draw filled polygon
            points = morph.get_render_points()
            if len(points) >= 3:
                pygame.draw.polygon(screen, morph.color, points, 0)  # Filled
                # Draw outline for better visibility
                outline_color = tuple(min(255, c + 50) for c in morph.color)
                pygame.draw.polygon(screen, outline_color, points, 2)  # Outline

            # Draw center point
            center = (int(morph.position.x), int(morph.position.y))
            pygame.draw.circle(screen, morph.color, center, 4)

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

        # Mode/pacing/tempo indicator (top right)
        if self._level_config:
            mode_text = f"{self._level_config.name} | {self._pacing.name}"
        else:
            mode_text = f"{self._game_mode.upper()} | {self._pacing.name} / {self._tempo.name}"
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

        if self._state == GameState.GAME_OVER:
            title = "ESCAPED!"
            subtitle = f"Survived: {self._score}s"
            title_color = config.GAP_COLOR
            hint = "Press R to restart"

        elif self._state == GameState.WON:
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
