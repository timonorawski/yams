"""Paddle entity with 'stopping' movement mode.

The paddle slides to the target position and stops. Players hit where
they want the paddle center to go.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class PaddleConfig:
    """Paddle configuration from level or defaults."""

    width: float = 120.0
    height: float = 20.0
    speed: float = 500.0
    y_position: float = 0.9  # Normalized (0-1), 0.9 = 90% down screen


class Paddle:
    """Paddle that slides to target position and stops.

    Movement mode: Player hits where they want paddle CENTER to be.
    Paddle smoothly slides to that position and stops.
    """

    def __init__(
        self,
        config: PaddleConfig,
        screen_width: float,
        screen_height: float,
    ):
        """Initialize paddle.

        Args:
            config: Paddle configuration
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
        """
        self._config = config
        self._screen_width = screen_width
        self._screen_height = screen_height

        # Position paddle at specified Y position
        self._y = screen_height * config.y_position
        # Start centered
        self._x = screen_width / 2
        self._target_x = self._x

    @property
    def x(self) -> float:
        """Get paddle center X position."""
        return self._x

    @property
    def y(self) -> float:
        """Get paddle center Y position."""
        return self._y

    @property
    def width(self) -> float:
        """Get paddle width."""
        return self._config.width

    @property
    def height(self) -> float:
        """Get paddle height."""
        return self._config.height

    @property
    def left(self) -> float:
        """Get paddle left edge X."""
        return self._x - self._config.width / 2

    @property
    def right(self) -> float:
        """Get paddle right edge X."""
        return self._x + self._config.width / 2

    @property
    def top(self) -> float:
        """Get paddle top Y."""
        return self._y - self._config.height / 2

    @property
    def bottom(self) -> float:
        """Get paddle bottom Y."""
        return self._y + self._config.height / 2

    @property
    def rect(self) -> Tuple[float, float, float, float]:
        """Get paddle bounding rectangle (x, y, width, height)."""
        return (
            self._x - self._config.width / 2,
            self._y - self._config.height / 2,
            self._config.width,
            self._config.height,
        )

    def set_target(self, target_x: float) -> None:
        """Set new target position for paddle center.

        The paddle will slide to this position.

        Args:
            target_x: Target X coordinate for paddle center
        """
        # Clamp to screen bounds
        half_width = self._config.width / 2
        self._target_x = max(
            half_width,
            min(self._screen_width - half_width, target_x)
        )

    def update(self, dt: float) -> None:
        """Move paddle toward target position.

        Args:
            dt: Delta time in seconds
        """
        # Check if we're close enough to snap
        if abs(self._x - self._target_x) < 1.0:
            self._x = self._target_x
            return

        # Move toward target
        direction = 1 if self._target_x > self._x else -1
        movement = direction * self._config.speed * dt

        # Don't overshoot
        if abs(movement) > abs(self._target_x - self._x):
            self._x = self._target_x
        else:
            self._x += movement

    def reset(self, screen_width: float) -> None:
        """Reset paddle to center position.

        Args:
            screen_width: Current screen width
        """
        self._screen_width = screen_width
        self._x = screen_width / 2
        self._target_x = self._x
