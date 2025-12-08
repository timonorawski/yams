"""
Balloon entity for Balloon Pop game.

Balloons float upward from the bottom of the screen. Players must pop them
before they escape off the top.
"""

import random
import math
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional
import pygame

from games.BalloonPop.config import (
    BALLOON_MIN_SIZE,
    BALLOON_MAX_SIZE,
    FLOAT_SPEED_MIN,
    FLOAT_SPEED_MAX,
    DRIFT_SPEED_MAX,
    BALLOON_COLORS,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)


class BalloonState(Enum):
    """State of a balloon."""
    FLOATING = "floating"
    POPPED = "popped"
    ESCAPED = "escaped"


@dataclass
class BalloonData:
    """Immutable balloon state data."""
    x: float
    y: float
    size: float
    color: Tuple[int, int, int]
    float_speed: float  # Vertical speed (pixels/sec, negative = up)
    drift_speed: float  # Horizontal drift (pixels/sec)
    drift_phase: float  # Phase for sinusoidal drift
    state: BalloonState = BalloonState.FLOATING


class Balloon:
    """
    A floating balloon that can be popped.

    Balloons float upward with a gentle side-to-side drift.
    They can be popped by clicking/hitting them, or they escape
    off the top of the screen.
    """

    def __init__(
        self,
        data: Optional[BalloonData] = None,
        color: Optional[Tuple[int, int, int]] = None,
        size_range: Optional[Tuple[float, float]] = None,
        speed_range: Optional[Tuple[float, float]] = None
    ):
        """
        Create a balloon.

        Args:
            data: Initial balloon data, or None to create at random position
            color: Balloon color (overrides random if provided)
            size_range: (min, max) size range (overrides config if provided)
            speed_range: (min, max) float speed range (overrides config if provided)
        """
        if data is None:
            data = self._create_random(color, size_range, speed_range)
        self._data = data

    @property
    def data(self) -> BalloonData:
        """Get balloon data."""
        return self._data

    @property
    def x(self) -> float:
        return self._data.x

    @property
    def y(self) -> float:
        return self._data.y

    @property
    def size(self) -> float:
        return self._data.size

    @property
    def radius(self) -> float:
        return self._data.size / 2

    @property
    def color(self) -> Tuple[int, int, int]:
        return self._data.color

    @property
    def state(self) -> BalloonState:
        return self._data.state

    @property
    def is_active(self) -> bool:
        """Check if balloon is still in play."""
        return self._data.state == BalloonState.FLOATING

    def _create_random(
        self,
        color: Optional[Tuple[int, int, int]] = None,
        size_range: Optional[Tuple[float, float]] = None,
        speed_range: Optional[Tuple[float, float]] = None
    ) -> BalloonData:
        """
        Create random balloon data for spawning.

        Args:
            color: Balloon color (or None for random from config)
            size_range: (min, max) size range (or None for config values)
            speed_range: (min, max) float speed range (or None for config values)
        """
        # Use provided ranges or default to config
        size_min, size_max = size_range if size_range else (BALLOON_MIN_SIZE, BALLOON_MAX_SIZE)
        speed_min, speed_max = speed_range if speed_range else (FLOAT_SPEED_MIN, FLOAT_SPEED_MAX)

        size = random.uniform(size_min, size_max)
        x = random.uniform(size, SCREEN_WIDTH - size)
        y = SCREEN_HEIGHT + size  # Start below screen

        return BalloonData(
            x=x,
            y=y,
            size=size,
            color=color if color else random.choice(BALLOON_COLORS),
            float_speed=random.uniform(speed_min, speed_max),
            drift_speed=random.uniform(-DRIFT_SPEED_MAX, DRIFT_SPEED_MAX),
            drift_phase=random.uniform(0, 2 * math.pi),
            state=BalloonState.FLOATING,
        )

    def update(self, dt: float) -> 'Balloon':
        """
        Update balloon position.

        Args:
            dt: Delta time in seconds

        Returns:
            New Balloon instance with updated position
        """
        if self._data.state != BalloonState.FLOATING:
            return self

        # Move upward
        new_y = self._data.y - self._data.float_speed * dt

        # Sinusoidal horizontal drift
        new_phase = self._data.drift_phase + dt * 2  # Drift period ~3 seconds
        drift_offset = math.sin(new_phase) * self._data.drift_speed * dt
        new_x = self._data.x + drift_offset

        # Keep within horizontal bounds
        new_x = max(self.radius, min(SCREEN_WIDTH - self.radius, new_x))

        return Balloon(BalloonData(
            x=new_x,
            y=new_y,
            size=self._data.size,
            color=self._data.color,
            float_speed=self._data.float_speed,
            drift_speed=self._data.drift_speed,
            drift_phase=new_phase,
            state=self._data.state,
        ))

    def contains_point(self, x: float, y: float) -> bool:
        """
        Check if a point is inside the balloon.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if point is inside balloon
        """
        dx = x - self._data.x
        dy = y - self._data.y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= self.radius

    def pop(self) -> 'Balloon':
        """
        Pop this balloon.

        Returns:
            New Balloon instance with POPPED state
        """
        return Balloon(BalloonData(
            x=self._data.x,
            y=self._data.y,
            size=self._data.size,
            color=self._data.color,
            float_speed=0,
            drift_speed=0,
            drift_phase=self._data.drift_phase,
            state=BalloonState.POPPED,
        ))

    def is_escaped(self) -> bool:
        """Check if balloon has escaped off the top of screen."""
        return self._data.y < -self._data.size

    def mark_escaped(self) -> 'Balloon':
        """Mark balloon as escaped."""
        return Balloon(BalloonData(
            x=self._data.x,
            y=self._data.y,
            size=self._data.size,
            color=self._data.color,
            float_speed=0,
            drift_speed=0,
            drift_phase=self._data.drift_phase,
            state=BalloonState.ESCAPED,
        ))

    def render(self, screen: pygame.Surface) -> None:
        """
        Render the balloon.

        Args:
            screen: Pygame surface to draw on
        """
        if self._data.state == BalloonState.POPPED:
            # Draw pop effect (expanding ring)
            return

        if self._data.state == BalloonState.ESCAPED:
            return

        # Draw balloon body (ellipse - taller than wide)
        rect = pygame.Rect(
            int(self._data.x - self.radius),
            int(self._data.y - self.radius * 1.2),
            int(self._data.size),
            int(self._data.size * 1.2)
        )
        pygame.draw.ellipse(screen, self._data.color, rect)

        # Draw highlight (small white ellipse for 3D effect)
        highlight_size = self._data.size * 0.3
        highlight_rect = pygame.Rect(
            int(self._data.x - self.radius * 0.5),
            int(self._data.y - self.radius * 0.8),
            int(highlight_size),
            int(highlight_size * 0.6)
        )
        highlight_color = (
            min(255, self._data.color[0] + 100),
            min(255, self._data.color[1] + 100),
            min(255, self._data.color[2] + 100),
        )
        pygame.draw.ellipse(screen, highlight_color, highlight_rect)

        # Draw string (simple line)
        string_start = (int(self._data.x), int(self._data.y + self.radius * 0.2))
        string_end = (int(self._data.x), int(self._data.y + self.radius * 1.5))
        pygame.draw.line(screen, (100, 100, 100), string_start, string_end, 2)
