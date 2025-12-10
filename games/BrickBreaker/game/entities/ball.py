"""Ball entity with velocity-based physics.

The ball bounces off walls, paddle, and bricks. Ball angle depends
on where it hits the paddle.
"""

from dataclasses import dataclass
import math
from typing import Tuple, Optional


@dataclass
class BallConfig:
    """Ball configuration from level or defaults."""

    radius: float = 10.0
    speed: float = 300.0          # Initial speed in pixels/second
    max_speed: float = 600.0
    speed_increase: float = 5.0   # Speed increase per brick hit


class Ball:
    """Ball with velocity-based movement and bouncing physics."""

    def __init__(
        self,
        config: BallConfig,
        x: float,
        y: float,
        vx: float = 0.0,
        vy: float = 0.0,
        active: bool = True,
    ):
        """Initialize ball.

        Args:
            config: Ball configuration
            x: Center X position
            y: Center Y position
            vx: X velocity (pixels/second)
            vy: Y velocity (pixels/second)
            active: Whether ball is active (in play)
        """
        self._config = config
        self._x = x
        self._y = y
        self._vx = vx
        self._vy = vy
        self._active = active

    @property
    def x(self) -> float:
        """Get ball center X."""
        return self._x

    @property
    def y(self) -> float:
        """Get ball center Y."""
        return self._y

    @property
    def vx(self) -> float:
        """Get X velocity."""
        return self._vx

    @property
    def vy(self) -> float:
        """Get Y velocity."""
        return self._vy

    @property
    def radius(self) -> float:
        """Get ball radius."""
        return self._config.radius

    @property
    def speed(self) -> float:
        """Get current ball speed."""
        return math.sqrt(self._vx**2 + self._vy**2)

    @property
    def is_active(self) -> bool:
        """Check if ball is active (in play)."""
        return self._active

    def launch(self, angle_degrees: float = -60.0) -> 'Ball':
        """Launch ball at specified angle.

        Args:
            angle_degrees: Launch angle (0 = right, -90 = up)

        Returns:
            New Ball with velocity set
        """
        angle_rad = math.radians(angle_degrees)
        vx = self._config.speed * math.cos(angle_rad)
        vy = self._config.speed * math.sin(angle_rad)
        return Ball(self._config, self._x, self._y, vx, vy, self._active)

    def update(self, dt: float) -> 'Ball':
        """Update ball position based on velocity.

        Args:
            dt: Delta time in seconds

        Returns:
            New Ball with updated position
        """
        if not self._active:
            return self

        new_x = self._x + self._vx * dt
        new_y = self._y + self._vy * dt

        return Ball(self._config, new_x, new_y, self._vx, self._vy, self._active)

    def set_position(self, x: float, y: float) -> 'Ball':
        """Set ball position.

        Args:
            x: New X position
            y: New Y position

        Returns:
            New Ball at new position
        """
        return Ball(self._config, x, y, self._vx, self._vy, self._active)

    def bounce_horizontal(self) -> 'Ball':
        """Bounce off vertical surface (reverse X velocity).

        Returns:
            New Ball with reversed X velocity
        """
        return Ball(self._config, self._x, self._y, -self._vx, self._vy, self._active)

    def bounce_vertical(self) -> 'Ball':
        """Bounce off horizontal surface (reverse Y velocity).

        Returns:
            New Ball with reversed Y velocity
        """
        return Ball(self._config, self._x, self._y, self._vx, -self._vy, self._active)

    def bounce_off_paddle(self, paddle_x: float, paddle_width: float) -> 'Ball':
        """Bounce off paddle with angle based on hit position.

        Ball bounces at different angles depending on where it hits
        the paddle. Hitting the center bounces straight up, edges
        bounce at steeper angles.

        Args:
            paddle_x: Paddle center X position
            paddle_width: Paddle width

        Returns:
            New Ball with new velocity based on paddle hit position
        """
        # Calculate offset from paddle center (-1 to 1)
        offset = (self._x - paddle_x) / (paddle_width / 2)
        offset = max(-1.0, min(1.0, offset))  # Clamp

        # Calculate bounce angle
        # offset=0 (center) -> -90 degrees (straight up)
        # offset=-1 (left edge) -> -135 degrees (up-left)
        # offset=+1 (right edge) -> -45 degrees (up-right)
        max_angle = 60.0  # Max deviation from vertical (degrees)
        angle_degrees = -90.0 + (offset * max_angle)
        angle_rad = math.radians(angle_degrees)

        # Maintain current speed
        current_speed = self.speed
        vx = current_speed * math.cos(angle_rad)
        vy = current_speed * math.sin(angle_rad)

        # Ensure ball is moving up
        if vy > 0:
            vy = -vy

        return Ball(self._config, self._x, self._y, vx, vy, self._active)

    def increase_speed(self) -> 'Ball':
        """Increase ball speed after hitting a brick.

        Returns:
            New Ball with increased speed
        """
        current_speed = self.speed
        if current_speed >= self._config.max_speed:
            return self

        # Calculate new speed
        new_speed = min(
            current_speed + self._config.speed_increase,
            self._config.max_speed
        )

        # Scale velocity to new speed
        if current_speed > 0:
            scale = new_speed / current_speed
            new_vx = self._vx * scale
            new_vy = self._vy * scale
        else:
            new_vx = self._vx
            new_vy = self._vy

        return Ball(self._config, self._x, self._y, new_vx, new_vy, self._active)

    def deactivate(self) -> 'Ball':
        """Mark ball as inactive (lost).

        Returns:
            New inactive Ball
        """
        return Ball(self._config, self._x, self._y, self._vx, self._vy, False)

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Get ball bounding box (left, top, right, bottom).

        Returns:
            Tuple of (left, top, right, bottom)
        """
        return (
            self._x - self._config.radius,
            self._y - self._config.radius,
            self._x + self._config.radius,
            self._y + self._config.radius,
        )
