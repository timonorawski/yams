"""Geometric skin - simple shapes for testing and CV calibration."""

from typing import TYPE_CHECKING, Tuple

import pygame

from .base import BrickBreakerSkin
from ...config import BRICK_COLORS

if TYPE_CHECKING:
    from ..entities.paddle import Paddle
    from ..entities.ball import Ball
    from ..entities.brick import Brick


class GeometricSkin(BrickBreakerSkin):
    """Renders game using simple geometric shapes.

    - Paddle: Blue rectangle with white outline
    - Ball: White circle
    - Bricks: Colored rectangles based on brick.behaviors.color
    - Multi-hit bricks: Darken color based on damage
    - Special indicators: Triangle for shooters, X for indestructible
    """

    NAME = "geometric"
    DESCRIPTION = "Simple shapes for testing and CV calibration"

    # Paddle colors
    PADDLE_COLOR = (100, 150, 255)
    PADDLE_OUTLINE = (255, 255, 255)

    # Ball color
    BALL_COLOR = (255, 255, 255)

    # HUD colors
    HUD_COLOR = (255, 255, 255)
    HUD_BG_COLOR = (40, 40, 50)

    def __init__(self):
        """Initialize geometric skin."""
        self._font: pygame.font.Font | None = None

    def _ensure_font(self) -> None:
        """Ensure font is initialized."""
        if self._font is None:
            pygame.font.init()
            self._font = pygame.font.Font(None, 36)

    def _get_brick_color(self, brick: 'Brick') -> Tuple[int, int, int]:
        """Get color for brick, darkened based on damage.

        Args:
            brick: Brick to get color for

        Returns:
            RGB color tuple
        """
        base_color = BRICK_COLORS.get(
            brick.behaviors.color,
            (255, 255, 255)
        )

        # Darken based on damage
        if brick.behaviors.hits > 1:
            damage_pct = 1 - (brick.hits_remaining / brick.behaviors.hits)
            # Darken by up to 50% based on damage
            darkening = 1 - (damage_pct * 0.5)
            color = tuple(int(c * darkening) for c in base_color)
            return color  # type: ignore

        return base_color

    def render_paddle(self, paddle: 'Paddle', screen: pygame.Surface) -> None:
        """Render paddle as a colored rectangle."""
        rect = paddle.rect
        pygame.draw.rect(
            screen,
            self.PADDLE_COLOR,
            (rect[0], rect[1], rect[2], rect[3])
        )
        pygame.draw.rect(
            screen,
            self.PADDLE_OUTLINE,
            (rect[0], rect[1], rect[2], rect[3]),
            2
        )

    def render_ball(self, ball: 'Ball', screen: pygame.Surface) -> None:
        """Render ball as a white circle."""
        if not ball.is_active:
            return

        pos = (int(ball.x), int(ball.y))
        pygame.draw.circle(screen, self.BALL_COLOR, pos, int(ball.radius))

    def render_brick(self, brick: 'Brick', screen: pygame.Surface) -> None:
        """Render brick as a colored rectangle with indicators."""
        if not brick.is_active:
            return

        color = self._get_brick_color(brick)
        rect = brick.rect

        # Draw filled rectangle
        pygame.draw.rect(
            screen,
            color,
            (rect[0], rect[1], rect[2], rect[3])
        )

        # Draw outline
        pygame.draw.rect(
            screen,
            (255, 255, 255),
            (rect[0], rect[1], rect[2], rect[3]),
            1
        )

        # Draw special indicators
        center_x = int(brick.center_x)
        center_y = int(brick.center_y)

        # Shooter indicator: small triangle pointing down
        if brick.behaviors.shoots:
            triangle_size = min(brick.width, brick.height) / 4
            pygame.draw.polygon(
                screen,
                (255, 0, 0),
                [
                    (center_x, center_y + triangle_size),
                    (center_x - triangle_size * 0.7, center_y - triangle_size * 0.5),
                    (center_x + triangle_size * 0.7, center_y - triangle_size * 0.5),
                ]
            )

        # Indestructible indicator: X
        if brick.behaviors.indestructible:
            margin = 5
            pygame.draw.line(
                screen,
                (0, 0, 0),
                (rect[0] + margin, rect[1] + margin),
                (rect[0] + rect[2] - margin, rect[1] + rect[3] - margin),
                2
            )
            pygame.draw.line(
                screen,
                (0, 0, 0),
                (rect[0] + rect[2] - margin, rect[1] + margin),
                (rect[0] + margin, rect[1] + rect[3] - margin),
                2
            )

        # Multi-hit indicator: show remaining hits
        if brick.behaviors.hits > 1 and brick.hits_remaining > 0:
            self._ensure_font()
            if self._font:
                text = self._font.render(
                    str(brick.hits_remaining),
                    True,
                    (0, 0, 0)
                )
                text_rect = text.get_rect(center=(center_x, center_y))
                screen.blit(text, text_rect)

    def render_projectile(
        self,
        projectile: dict,
        screen: pygame.Surface,
    ) -> None:
        """Render enemy projectile as a small red circle."""
        x = int(projectile.get('x', 0))
        y = int(projectile.get('y', 0))
        pygame.draw.circle(screen, (255, 50, 50), (x, y), 5)

    def render_hud(
        self,
        screen: pygame.Surface,
        score: int,
        lives: int,
        level_name: str = "",
    ) -> None:
        """Render HUD with score and lives."""
        self._ensure_font()
        if not self._font:
            return

        # Score (top left)
        score_text = self._font.render(f"Score: {score}", True, self.HUD_COLOR)
        screen.blit(score_text, (10, 10))

        # Lives (top right)
        lives_text = self._font.render(f"Lives: {lives}", True, self.HUD_COLOR)
        lives_rect = lives_text.get_rect()
        lives_rect.topright = (screen.get_width() - 10, 10)
        screen.blit(lives_text, lives_rect)

        # Level name (top center)
        if level_name:
            level_text = self._font.render(level_name, True, self.HUD_COLOR)
            level_rect = level_text.get_rect()
            level_rect.midtop = (screen.get_width() // 2, 10)
            screen.blit(level_text, level_rect)
