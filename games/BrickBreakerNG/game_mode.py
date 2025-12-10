"""BrickBreaker NextGen - Lua behavior-driven brick breaker.

This is a reimplementation of BrickBreaker using the GameEngine framework
with Lua behaviors. It serves as:
1. A proof-of-concept for the behavior system
2. A comparison platform against the original Python implementation
3. A template for creating new behavior-driven games

All game logic is in Lua behaviors:
- paddle: Stopping paddle that slides to target
- ball: Bouncing ball with velocity
- brick: Destructible with multi-hit support
- descend, oscillate, shoot: Brick modifiers
"""

from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import pygame

from games.common import GameEngine, GameEngineSkin, GameState
from games.common.input import InputEvent
from ams.behaviors import Entity


# Screen constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BACKGROUND_COLOR = (20, 20, 30)


class BrickBreakerNGSkin(GameEngineSkin):
    """Geometric rendering skin for BrickBreaker NG."""

    # Color map for bricks
    COLORS = {
        'red': (220, 60, 60),
        'orange': (220, 140, 60),
        'yellow': (220, 220, 60),
        'green': (60, 220, 60),
        'blue': (60, 60, 220),
        'purple': (160, 60, 220),
        'cyan': (60, 220, 220),
        'gray': (128, 128, 128),
        'silver': (192, 192, 192),
        'white': (255, 255, 255),
    }

    def render_entity(self, entity: Entity, screen: pygame.Surface) -> None:
        """Render entity based on type."""
        if entity.entity_type == 'paddle':
            self._render_paddle(entity, screen)
        elif entity.entity_type == 'ball':
            self._render_ball(entity, screen)
        elif entity.entity_type == 'brick':
            self._render_brick(entity, screen)
        elif entity.entity_type == 'projectile':
            self._render_projectile(entity, screen)
        else:
            super().render_entity(entity, screen)

    def _render_paddle(self, entity: Entity, screen: pygame.Surface) -> None:
        """Render the paddle."""
        rect = pygame.Rect(int(entity.x), int(entity.y),
                           int(entity.width), int(entity.height))
        # Fill
        pygame.draw.rect(screen, (60, 60, 220), rect)
        # Outline
        pygame.draw.rect(screen, (255, 255, 255), rect, 2)

    def _render_ball(self, entity: Entity, screen: pygame.Surface) -> None:
        """Render the ball."""
        center = (int(entity.x + entity.width / 2),
                  int(entity.y + entity.height / 2))
        radius = int(entity.width / 2)
        pygame.draw.circle(screen, (255, 255, 255), center, radius)

    def _render_brick(self, entity: Entity, screen: pygame.Surface) -> None:
        """Render a brick with damage indication."""
        rect = pygame.Rect(int(entity.x), int(entity.y),
                           int(entity.width), int(entity.height))

        # Get base color
        base_color = self.COLORS.get(entity.color, (200, 200, 200))

        # Darken based on damage
        hits_remaining = entity.properties.get('brick_hits_remaining', 1)
        max_hits = entity.properties.get('brick_max_hits', 1)
        damage_ratio = 1 - (hits_remaining / max_hits) if max_hits > 1 else 0

        # Darken color based on damage
        darken = 1 - (damage_ratio * 0.5)
        color = (int(base_color[0] * darken),
                 int(base_color[1] * darken),
                 int(base_color[2] * darken))

        # Fill
        pygame.draw.rect(screen, color, rect)
        # Outline
        pygame.draw.rect(screen, (255, 255, 255), rect, 1)

        # Show remaining hits for multi-hit bricks
        if max_hits > 1 and hits_remaining > 0:
            font = pygame.font.Font(None, 20)
            text = font.render(str(hits_remaining), True, (255, 255, 255))
            text_rect = text.get_rect(center=rect.center)
            screen.blit(text, text_rect)

    def _render_projectile(self, entity: Entity, screen: pygame.Surface) -> None:
        """Render an enemy projectile."""
        rect = pygame.Rect(int(entity.x), int(entity.y),
                           int(entity.width), int(entity.height))
        pygame.draw.rect(screen, (255, 100, 100), rect)


class BrickBreakerNGMode(GameEngine):
    """BrickBreaker NextGen - behavior-driven brick breaker."""

    NAME = "Brick Breaker NG"
    DESCRIPTION = "Lua behavior-driven brick breaker"
    VERSION = "1.0.0"
    AUTHOR = "AMS Team"

    LEVELS_DIR = Path(__file__).parent / 'levels'

    ARGUMENTS = [
        {
            'name': '--lives',
            'type': int,
            'default': 3,
            'help': 'Starting lives'
        },
    ]

    def __init__(
        self,
        lives: int = 3,
        width: int = SCREEN_WIDTH,
        height: int = SCREEN_HEIGHT,
        **kwargs,
    ):
        """Initialize BrickBreaker NG."""
        self._paddle_id: Optional[str] = None
        self._ball_id: Optional[str] = None

        # Remove skin from kwargs if present (we handle it internally)
        kwargs.pop('skin', None)

        super().__init__(
            skin='default',
            lives=lives,
            width=width,
            height=height,
            **kwargs,
        )

    def _get_skin(self, skin_name: str) -> GameEngineSkin:
        """Get rendering skin."""
        return BrickBreakerNGSkin()

    def _spawn_initial_entities(self) -> None:
        """Spawn paddle, ball, and bricks."""
        # Spawn paddle
        paddle = self._behavior_engine.create_entity(
            entity_type='paddle',
            x=(self._screen_width - 120) / 2,
            y=self._screen_height - 50,
            width=120,
            height=15,
            color='blue',
            behaviors=['paddle'],
            behavior_config={'paddle': {'speed': 500}},
        )
        self._paddle_id = paddle.id

        # Spawn ball (attached to paddle)
        ball = self._behavior_engine.create_entity(
            entity_type='ball',
            x=self._screen_width / 2 - 8,
            y=self._screen_height - 75,
            width=16,
            height=16,
            color='white',
            behaviors=['ball'],
            behavior_config={'ball': {'speed': 300, 'max_speed': 600}},
        )
        self._ball_id = ball.id
        ball.properties['ball_attached_to'] = paddle.id

        # Spawn bricks (5 rows x 10 cols)
        self._spawn_default_bricks()

    def _spawn_default_bricks(self) -> None:
        """Spawn default brick layout."""
        colors = ['red', 'orange', 'yellow', 'green', 'blue']
        rows = 5
        cols = 10
        brick_width = 70
        brick_height = 25
        start_y = 60

        total_width = cols * brick_width
        start_x = (self._screen_width - total_width) / 2

        for row in range(rows):
            color = colors[row % len(colors)]
            points = 100 * (rows - row)

            for col in range(cols):
                x = start_x + col * brick_width
                y = start_y + row * brick_height

                self._behavior_engine.create_entity(
                    entity_type='brick',
                    x=x,
                    y=y,
                    width=brick_width,
                    height=brick_height,
                    color=color,
                    behaviors=['brick'],
                    behavior_config={'brick': {'hits': 1, 'points': points}},
                )

    def _handle_player_input(self, event: InputEvent) -> None:
        """Handle player input - set paddle target and launch ball."""
        # Set paddle target
        paddle = self._behavior_engine.get_entity(self._paddle_id) if self._paddle_id else None
        if paddle:
            paddle.properties['paddle_target_x'] = event.position.x

        # Launch ball on first input
        ball = self._behavior_engine.get_entity(self._ball_id) if self._ball_id else None
        if ball and not ball.properties.get('ball_launched'):
            # Get ball behavior and call launch
            ball_behavior = self._behavior_engine._behaviors.get('ball')
            if ball_behavior and hasattr(ball_behavior, 'launch'):
                ball_behavior.launch(ball.id, -75)  # Launch at -75 degrees

    def _check_collisions(self) -> None:
        """Check ball-paddle and ball-brick collisions."""
        ball = self._behavior_engine.get_entity(self._ball_id) if self._ball_id else None
        if not ball or not ball.properties.get('ball_launched'):
            return

        # Check if ball fell
        if ball.properties.get('ball_fell'):
            self._handle_ball_lost()
            return

        # Check paddle collision
        paddle = self._behavior_engine.get_entity(self._paddle_id) if self._paddle_id else None
        if paddle and self._check_rect_collision(ball, paddle):
            # Only bounce if ball is moving down
            if ball.vy > 0:
                paddle_center = paddle.x + paddle.width / 2
                ball_behavior = self._behavior_engine._behaviors.get('ball')
                if ball_behavior and hasattr(ball_behavior, 'bounce_off_paddle'):
                    ball_behavior.bounce_off_paddle(ball.id, paddle_center, paddle.width)

        # Check brick collisions
        for entity in self._behavior_engine.get_alive_entities():
            if entity.entity_type == 'brick' and self._check_rect_collision(ball, entity):
                self._handle_brick_collision(ball, entity)
                break  # One collision per frame

    def _check_rect_collision(self, a: Entity, b: Entity) -> bool:
        """Check if two entities overlap."""
        return (a.x < b.x + b.width and
                a.x + a.width > b.x and
                a.y < b.y + b.height and
                a.y + a.height > b.y)

    def _handle_brick_collision(self, ball: Entity, brick: Entity) -> None:
        """Handle ball hitting a brick."""
        # Determine collision direction for bounce
        ball_center_x = ball.x + ball.width / 2
        ball_center_y = ball.y + ball.height / 2
        brick_center_x = brick.x + brick.width / 2
        brick_center_y = brick.y + brick.height / 2

        dx = ball_center_x - brick_center_x
        dy = ball_center_y - brick_center_y

        # Determine primary collision axis
        overlap_x = (ball.width + brick.width) / 2 - abs(dx)
        overlap_y = (ball.height + brick.height) / 2 - abs(dy)

        if overlap_x < overlap_y:
            # Horizontal collision
            ball.vx = -ball.vx
        else:
            # Vertical collision
            ball.vy = -ball.vy

        # Hit the brick
        brick_behavior = self._behavior_engine._behaviors.get('brick')
        if brick_behavior and hasattr(brick_behavior, 'hit'):
            destroyed = brick_behavior.hit(brick.id)
            if destroyed:
                # Increase ball speed
                ball_behavior = self._behavior_engine._behaviors.get('ball')
                if ball_behavior and hasattr(ball_behavior, 'increase_speed'):
                    ball_behavior.increase_speed(ball.id)

    def _handle_ball_lost(self) -> None:
        """Handle ball falling off screen."""
        self.lose_life()

        if self._lives > 0:
            # Reset ball to paddle
            ball = self._behavior_engine.get_entity(self._ball_id) if self._ball_id else None
            paddle = self._behavior_engine.get_entity(self._paddle_id) if self._paddle_id else None

            if ball and paddle:
                ball.properties['ball_launched'] = False
                ball.properties['ball_fell'] = False
                ball.properties['ball_attached_to'] = paddle.id
                ball.vx = 0
                ball.vy = 0
                # Reset speed
                ball.properties['ball_speed'] = 300

    def _check_win_conditions(self) -> None:
        """Check if all bricks destroyed."""
        bricks = [e for e in self._behavior_engine.get_alive_entities()
                  if e.entity_type == 'brick']
        if not bricks:
            self._internal_state = GameState.WON
