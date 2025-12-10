"""Base class for BrickBreaker game skins.

Skins handle ALL rendering - the game only manages state.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Any

import pygame

if TYPE_CHECKING:
    from ..entities.paddle import Paddle
    from ..entities.ball import Ball
    from ..entities.brick import Brick


class BrickBreakerSkin(ABC):
    """Base class for game skins (visuals + audio).

    Skins handle all rendering and audio. The game logic only
    manages state - skins decide how to present it.
    """

    NAME: str = "base"
    DESCRIPTION: str = "Base skin"

    @abstractmethod
    def render_paddle(self, paddle: 'Paddle', screen: pygame.Surface) -> None:
        """Render the paddle.

        Args:
            paddle: Paddle to render
            screen: Pygame surface to draw on
        """
        pass

    @abstractmethod
    def render_ball(self, ball: 'Ball', screen: pygame.Surface) -> None:
        """Render a ball.

        Args:
            ball: Ball to render
            screen: Pygame surface to draw on
        """
        pass

    @abstractmethod
    def render_brick(self, brick: 'Brick', screen: pygame.Surface) -> None:
        """Render a brick based on its behaviors and state.

        Args:
            brick: Brick to render (access brick.behaviors for config)
            screen: Pygame surface to draw on
        """
        pass

    def render_projectile(
        self,
        projectile: dict,
        screen: pygame.Surface,
    ) -> None:
        """Render an enemy projectile.

        Args:
            projectile: Projectile data dict with x, y, speed
            screen: Pygame surface to draw on
        """
        pass

    def render_hud(
        self,
        screen: pygame.Surface,
        score: int,
        lives: int,
        level_name: str = "",
    ) -> None:
        """Render the heads-up display (score, lives, etc.).

        Args:
            screen: Pygame surface to draw on
            score: Current score
            lives: Remaining lives
            level_name: Current level name
        """
        pass

    def update(self, dt: float) -> None:
        """Update skin state (animations, timers, etc.).

        Args:
            dt: Delta time in seconds
        """
        pass

    def play_paddle_hit_sound(self) -> None:
        """Play sound when ball hits paddle."""
        pass

    def play_brick_hit_sound(self) -> None:
        """Play sound when brick is damaged but not destroyed."""
        pass

    def play_brick_break_sound(self) -> None:
        """Play sound when brick is destroyed."""
        pass

    def play_wall_hit_sound(self) -> None:
        """Play sound when ball hits wall."""
        pass

    def play_life_lost_sound(self) -> None:
        """Play sound when ball falls below paddle."""
        pass

    def play_level_complete_sound(self) -> None:
        """Play sound when level is completed."""
        pass

    def play_game_over_sound(self) -> None:
        """Play sound when game is over."""
        pass
