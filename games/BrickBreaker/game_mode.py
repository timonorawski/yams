"""BrickBreaker - Classic brick-breaking game for AMS.

Features:
- Stopping paddle mode: Hit where you want paddle center to go
- Data-driven brick behaviors from YAML config
- Full level and skin support
"""

from pathlib import Path
from typing import List, Optional, Dict, Any

import pygame

from ams.games import BaseGame, GameState
from ams.games.input import InputEvent

from .config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, BACKGROUND_COLOR,
    BALL_DEFAULT_SPEED, BALL_RADIUS,
    PADDLE_DEFAULT_WIDTH, PADDLE_HEIGHT, PADDLE_DEFAULT_SPEED, PADDLE_Y_POSITION,
    BRICK_DEFAULT_WIDTH, BRICK_DEFAULT_HEIGHT, GRID_OFFSET_X, GRID_OFFSET_Y,
    get_pacing_preset,
)
from .game.entities.paddle import Paddle, PaddleConfig
from .game.entities.ball import Ball, BallConfig
from .game.entities.brick import Brick, BrickBehaviors, BrickState
from .game.physics.collision import (
    check_wall_collision,
    check_paddle_collision,
    check_brick_collision,
    get_collision_direction,
    resolve_brick_collision,
)
from .game.skins import BrickBreakerSkin, GeometricSkin
from .game.level_loader import BrickBreakerLevelLoader, LevelData


class BrickBreakerMode(BaseGame):
    """Brick Breaker game mode.

    Features:
    - Stopping paddle mode: Hit where you want paddle center to go
    - Data-driven brick behaviors from YAML
    - Multiple skins (geometric, classic)
    - Level progression with groups/campaigns
    """

    # Game metadata
    NAME = "Brick Breaker"
    DESCRIPTION = "Classic brick-breaking with data-driven behaviors."
    VERSION = "1.0.0"
    AUTHOR = "AMS Team"

    # Enable level support
    LEVELS_DIR = Path(__file__).parent / 'levels'

    # CLI arguments
    ARGUMENTS = [
        {
            'name': '--skin',
            'type': str,
            'default': 'geometric',
            'choices': ['geometric'],  # Will add 'classic' later
            'help': 'Visual skin (geometric=shapes)'
        },
        {
            'name': '--pacing',
            'type': str,
            'default': 'throwing',
            'choices': ['archery', 'throwing', 'blaster'],
            'help': 'Device speed preset'
        },
        {
            'name': '--lives',
            'type': int,
            'default': 3,
            'help': 'Starting lives'
        },
    ]

    # Skin registry
    SKINS: Dict[str, type] = {}

    def __init__(
        self,
        skin: str = 'geometric',
        pacing: str = 'throwing',
        lives: int = 3,
        width: int = SCREEN_WIDTH,
        height: int = SCREEN_HEIGHT,
        **kwargs,
    ):
        """Initialize BrickBreaker game.

        Args:
            skin: Visual skin to use
            pacing: Device speed preset
            lives: Starting lives
            width: Screen width
            height: Screen height
            **kwargs: Base game args (palette, quiver_size, etc.)
        """
        # Initialize attributes BEFORE super().__init__() because it may call _apply_level_config
        self._pacing = pacing
        self._pacing_preset = get_pacing_preset(pacing)
        self._starting_lives = lives
        self._lives = lives
        self._screen_width = width
        self._screen_height = height

        # Game state
        self._internal_state = GameState.PLAYING
        self._score = 0
        self._ball_launched = False
        self._level_name = ""

        # Game entities (initialized in _init_level)
        self._paddle: Optional[Paddle] = None
        self._ball: Optional[Ball] = None
        self._bricks: List[Brick] = []
        self._projectiles: List[Dict[str, Any]] = []

        # Current level data (set by _apply_level_config or _init_default_level)
        self._current_level: Optional[LevelData] = None

        # Initialize skin registry
        self.SKINS = {
            'geometric': GeometricSkin,
            # 'classic': ClassicSkin,  # Add later
        }

        # Create skin instance
        skin_class = self.SKINS.get(skin, GeometricSkin)
        self._skin: BrickBreakerSkin = skin_class()

        # Now call super().__init__() which may load levels
        super().__init__(**kwargs)

        # Initialize with default level if no level was loaded by BaseGame
        if self._paddle is None:
            self._init_default_level()

    def _create_level_loader(self) -> BrickBreakerLevelLoader:
        """Create BrickBreaker-specific level loader.

        Returns:
            BrickBreakerLevelLoader instance
        """
        return BrickBreakerLevelLoader(self.LEVELS_DIR)

    def _apply_level_config(self, level_data: LevelData) -> None:
        """Apply loaded level configuration to game state.

        Args:
            level_data: Parsed level data from YAML
        """
        self._current_level = level_data
        self._level_name = level_data.name

        # Apply lives from level (if not overridden by CLI)
        if self._starting_lives == 3:  # Default, use level's value
            self._lives = level_data.lives
            self._starting_lives = level_data.lives

        # Create paddle from level config
        paddle_config = PaddleConfig(
            width=level_data.paddle.width,
            height=level_data.paddle.height,
            speed=level_data.paddle.speed,
            y_position=level_data.paddle.y_position,
        )
        self._paddle = Paddle(
            paddle_config,
            self._screen_width,
            self._screen_height,
        )

        # Create ball from level config
        ball_config = BallConfig(
            radius=level_data.ball.radius,
            speed=level_data.ball.speed,
            max_speed=level_data.ball.max_speed,
            speed_increase=level_data.ball.speed_increase,
        )
        self._ball = Ball(
            ball_config,
            self._paddle.x,
            self._paddle.top - level_data.ball.radius - 5,
        )
        self._ball_launched = False

        # Create bricks from level layout
        self._bricks = []
        for placement in level_data.bricks:
            behaviors = level_data.brick_types.get(placement.brick_type)
            if behaviors is None:
                continue

            brick = Brick(
                placement.x,
                placement.y,
                placement.width,
                placement.height,
                behaviors,
                (placement.row, placement.col),
            )
            self._bricks.append(brick)

        # Reset projectiles
        self._projectiles = []

        # Reset game state
        self._internal_state = GameState.PLAYING
        self._ball_launched = False

    def _on_level_transition(self) -> None:
        """Reinitialize game state for the next level in a group."""
        # Reset score is optional - keep accumulating for campaign
        self._ball_launched = False
        self._projectiles = []
        # Level data will be applied by BaseGame calling _apply_level_config

    def _init_default_level(self) -> None:
        """Initialize game with a hardcoded default level."""
        self._level_name = "Default Level"

        # Create paddle with pacing-adjusted width
        paddle_config = PaddleConfig(
            width=self._pacing_preset.paddle_width,
            height=PADDLE_HEIGHT,
            speed=self._pacing_preset.paddle_speed,
            y_position=PADDLE_Y_POSITION,
        )
        self._paddle = Paddle(
            paddle_config,
            self._screen_width,
            self._screen_height,
        )

        # Create ball (positioned on paddle, not launched)
        ball_config = BallConfig(
            radius=BALL_RADIUS,
            speed=self._pacing_preset.ball_speed,
        )
        self._ball = Ball(
            ball_config,
            self._paddle.x,
            self._paddle.top - BALL_RADIUS - 5,
        )
        self._ball_launched = False

        # Create default brick layout (5 rows x 10 cols)
        self._bricks = []
        colors = ['red', 'orange', 'yellow', 'green', 'blue']

        rows = 5
        cols = 10
        brick_width = BRICK_DEFAULT_WIDTH
        brick_height = BRICK_DEFAULT_HEIGHT

        # Center the grid
        total_width = cols * brick_width
        start_x = (self._screen_width - total_width) / 2

        for row in range(rows):
            color = colors[row % len(colors)]
            behaviors = BrickBehaviors(
                hits=1,
                points=100 * (rows - row),  # More points for higher rows
                color=color,
            )

            for col in range(cols):
                x = start_x + col * brick_width
                y = GRID_OFFSET_Y + row * brick_height

                brick = Brick(
                    x, y, brick_width, brick_height,
                    behaviors, (row, col)
                )
                self._bricks.append(brick)

        # Reset projectiles
        self._projectiles = []

    def _get_internal_state(self) -> GameState:
        """Get current game state."""
        return self._internal_state

    def get_score(self) -> int:
        """Get current score."""
        return self._score

    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events - set paddle target and launch ball.

        Args:
            events: List of input events
        """
        if self._internal_state != GameState.PLAYING:
            return

        if self._paddle is None:
            return

        for event in events:
            # Set paddle target to hit x position
            self._paddle.set_target(event.position.x)

            # Launch ball on first input if not launched
            if not self._ball_launched and self._ball is not None:
                self._ball_launched = True
                self._ball = self._ball.launch(angle_degrees=-75)

    def update(self, dt: float) -> None:
        """Update game physics and state.

        Args:
            dt: Delta time in seconds
        """
        if self._internal_state != GameState.PLAYING:
            return

        if self._paddle is None or self._ball is None:
            return

        # Update paddle
        self._paddle.update(dt)

        # If ball not launched, keep it on paddle
        if not self._ball_launched:
            self._ball = self._ball.set_position(
                self._paddle.x,
                self._paddle.top - self._ball.radius - 5,
            )
            return

        # Update ball position
        self._ball = self._ball.update(dt)

        # Check wall collisions
        self._ball, fell_below = check_wall_collision(
            self._ball,
            self._screen_width,
            self._screen_height,
        )

        if fell_below:
            self._lose_life()
            return

        # Check paddle collision
        if check_paddle_collision(self._ball, self._paddle):
            self._ball = self._ball.bounce_off_paddle(
                self._paddle.x,
                self._paddle.width,
            )
            self._skin.play_paddle_hit_sound()

        # Check brick collisions
        self._handle_brick_collisions()

        # Update bricks (for behaviors like descending, shooting)
        self._update_bricks(dt)

        # Update projectiles
        self._update_projectiles(dt)

        # Update skin animations
        self._skin.update(dt)

        # Check win condition
        if self._all_bricks_destroyed():
            self._internal_state = GameState.WON
            self._skin.play_level_complete_sound()

    def _handle_brick_collisions(self) -> None:
        """Check and handle ball-brick collisions."""
        if self._ball is None:
            return

        for i, brick in enumerate(self._bricks):
            if not brick.is_active:
                continue

            direction = get_collision_direction(self._ball, brick)
            if direction is None:
                continue

            # Check if brick can be hit from this direction
            if not brick.can_be_hit_from(direction):
                # Ball bounces but brick not damaged
                self._ball = resolve_brick_collision(self._ball, brick, direction)
                continue

            # Hit the brick
            self._bricks[i] = brick.hit()

            # Bounce ball
            self._ball = resolve_brick_collision(self._ball, brick, direction)

            # Check if destroyed
            if self._bricks[i].is_destroyed:
                self._score += brick.behaviors.points
                self._skin.play_brick_break_sound()

                # Handle split behavior
                if brick.behaviors.splits:
                    split_bricks = brick.get_split_bricks()
                    self._bricks.extend(split_bricks)

                # Speed up ball
                self._ball = self._ball.increase_speed()
            else:
                self._skin.play_brick_hit_sound()

            # Only handle one brick collision per frame
            break

    def _update_bricks(self, dt: float) -> None:
        """Update all bricks (movement, shooting, etc.)."""
        updated_bricks = []
        for brick in self._bricks:
            if brick.is_active:
                updated_brick, projectiles = brick.update(dt)
                updated_bricks.append(updated_brick)
                self._projectiles.extend(projectiles)

                # Check if descending brick reached paddle
                if updated_brick.behaviors.descends:
                    if updated_brick.y + updated_brick.height >= self._paddle.top:
                        # Game over - brick reached paddle
                        self._internal_state = GameState.GAME_OVER
                        self._skin.play_game_over_sound()
                        return
            elif brick.is_destroyed:
                # Remove destroyed bricks
                pass
            else:
                updated_bricks.append(brick)

        self._bricks = updated_bricks

    def _update_projectiles(self, dt: float) -> None:
        """Update enemy projectiles."""
        if not self._projectiles:
            return

        updated = []
        for proj in self._projectiles:
            # Move projectile down
            proj['y'] += proj.get('speed', 200) * dt

            # Check if off screen
            if proj['y'] > self._screen_height:
                continue

            # Check if hit paddle
            if self._paddle is not None:
                paddle_rect = self._paddle.rect
                if (paddle_rect[0] <= proj['x'] <= paddle_rect[0] + paddle_rect[2] and
                        paddle_rect[1] <= proj['y'] <= paddle_rect[1] + paddle_rect[3]):
                    # Hit paddle - lose a life
                    self._lose_life()
                    continue

            updated.append(proj)

        self._projectiles = updated

    def _lose_life(self) -> None:
        """Handle losing a life."""
        self._lives -= 1
        self._skin.play_life_lost_sound()

        if self._lives <= 0:
            self._internal_state = GameState.GAME_OVER
            self._skin.play_game_over_sound()
        else:
            # Reset ball to paddle
            if self._paddle is not None:
                ball_config = BallConfig(
                    radius=BALL_RADIUS,
                    speed=self._pacing_preset.ball_speed,
                )
                self._ball = Ball(
                    ball_config,
                    self._paddle.x,
                    self._paddle.top - BALL_RADIUS - 5,
                )
                self._ball_launched = False

    def _all_bricks_destroyed(self) -> bool:
        """Check if all destructible bricks are destroyed."""
        for brick in self._bricks:
            if brick.is_active and not brick.behaviors.indestructible:
                return False
        return True

    def render(self, screen: pygame.Surface) -> None:
        """Render the game.

        Args:
            screen: Pygame surface to draw on
        """
        # Clear screen
        screen.fill(BACKGROUND_COLOR)

        # Render bricks
        for brick in self._bricks:
            self._skin.render_brick(brick, screen)

        # Render paddle
        if self._paddle is not None:
            self._skin.render_paddle(self._paddle, screen)

        # Render ball
        if self._ball is not None:
            self._skin.render_ball(self._ball, screen)

        # Render projectiles
        for proj in self._projectiles:
            self._skin.render_projectile(proj, screen)

        # Render HUD
        self._skin.render_hud(
            screen,
            self._score,
            self._lives,
            self._level_name,
        )

        # Render game over / win overlay
        if self._internal_state == GameState.GAME_OVER:
            self._render_game_over(screen)
        elif self._internal_state == GameState.WON:
            self._render_win(screen)

    def _render_game_over(self, screen: pygame.Surface) -> None:
        """Render game over overlay."""
        font = pygame.font.Font(None, 72)
        text = font.render("GAME OVER", True, (255, 100, 100))
        rect = text.get_rect(center=(self._screen_width // 2, self._screen_height // 2))
        screen.blit(text, rect)

        font_small = pygame.font.Font(None, 36)
        score_text = font_small.render(f"Final Score: {self._score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self._screen_width // 2, self._screen_height // 2 + 50))
        screen.blit(score_text, score_rect)

    def _render_win(self, screen: pygame.Surface) -> None:
        """Render win overlay."""
        font = pygame.font.Font(None, 72)
        text = font.render("LEVEL COMPLETE!", True, (100, 255, 100))
        rect = text.get_rect(center=(self._screen_width // 2, self._screen_height // 2))
        screen.blit(text, rect)

        font_small = pygame.font.Font(None, 36)
        score_text = font_small.render(f"Score: {self._score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self._screen_width // 2, self._screen_height // 2 + 50))
        screen.blit(score_text, score_rect)

    def reset(self) -> None:
        """Reset game to initial state."""
        super().reset()
        self._score = 0
        self._lives = self._starting_lives
        self._internal_state = GameState.PLAYING
        self._init_default_level()
