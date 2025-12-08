"""
LoveOMeter target with movement patterns.

The target that players must hit repeatedly to fill the meter.
Supports various movement patterns and shrinking over time.
"""
import math
import random
from dataclasses import dataclass
from typing import Tuple

import pygame

from games.LoveOMeter import config


@dataclass
class TargetState:
    """Current state of the target."""
    x: float
    y: float
    radius: float
    # Movement
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    # For orbit pattern
    orbit_angle: float = 0.0
    orbit_center_x: float = 0.0
    orbit_center_y: float = 0.0
    orbit_radius: float = 0.0
    # Visual
    hit_flash: float = 0.0  # Countdown for hit flash effect


class Target:
    """
    The target that players hit to fill the meter.

    Supports movement patterns:
    - drift: Smooth random wandering
    - orbit: Circular path around a point
    - random: Teleports to new position periodically
    - bounce: Bounces off screen edges
    """

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        initial_size: int = config.DEFAULT_TARGET_SIZE,
        min_size: int = config.MIN_TARGET_SIZE,
        shrink_rate: float = config.TARGET_SHRINK_RATE,
        movement_pattern: str = config.MOVEMENT_DRIFT,
        movement_speed: float = 40.0,
        play_area_margin: int = 200,  # Keep away from meter on left
    ):
        """
        Initialize the target.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            initial_size: Starting radius
            min_size: Minimum radius (won't shrink below this)
            shrink_rate: Pixels per second to shrink
            movement_pattern: One of drift, orbit, random, bounce
            movement_speed: Base movement speed in pixels/second
            play_area_margin: Left margin to avoid meter
        """
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._initial_size = initial_size
        self._min_size = min_size
        self._shrink_rate = shrink_rate
        self._movement_pattern = movement_pattern
        self._movement_speed = movement_speed
        self._play_area_margin = play_area_margin

        # Calculate play area (right side of screen, away from meter)
        self._play_left = play_area_margin
        self._play_right = screen_width - 50
        self._play_top = 50
        self._play_bottom = screen_height - 50
        self._play_center_x = (self._play_left + self._play_right) / 2
        self._play_center_y = (self._play_top + self._play_bottom) / 2

        # Initialize state
        self._state = self._init_state()

        # For random pattern
        self._random_timer = 0.0
        self._random_interval = 2.0  # seconds between teleports

        # For drift pattern
        self._drift_change_timer = 0.0
        self._drift_change_interval = 1.5

    def _init_state(self) -> TargetState:
        """Create initial target state."""
        # Start in center of play area
        x = self._play_center_x
        y = self._play_center_y

        state = TargetState(
            x=x,
            y=y,
            radius=float(self._initial_size),
        )

        # Initialize pattern-specific state
        if self._movement_pattern == config.MOVEMENT_ORBIT:
            state.orbit_center_x = self._play_center_x
            state.orbit_center_y = self._play_center_y
            state.orbit_radius = min(
                (self._play_right - self._play_left) / 3,
                (self._play_bottom - self._play_top) / 3
            )
            state.orbit_angle = random.uniform(0, 2 * math.pi)

        elif self._movement_pattern == config.MOVEMENT_BOUNCE:
            angle = random.uniform(0, 2 * math.pi)
            state.velocity_x = math.cos(angle) * self._movement_speed
            state.velocity_y = math.sin(angle) * self._movement_speed

        elif self._movement_pattern == config.MOVEMENT_DRIFT:
            self._update_drift_velocity(state)

        return state

    def _update_drift_velocity(self, state: TargetState) -> None:
        """Update drift velocity with smooth random direction."""
        # Bias toward center if near edges
        bias_x = 0.0
        bias_y = 0.0

        margin = 100
        if state.x < self._play_left + margin:
            bias_x = 0.5
        elif state.x > self._play_right - margin:
            bias_x = -0.5

        if state.y < self._play_top + margin:
            bias_y = 0.5
        elif state.y > self._play_bottom - margin:
            bias_y = -0.5

        # Random direction with bias
        angle = random.uniform(0, 2 * math.pi)
        state.velocity_x = (math.cos(angle) + bias_x) * self._movement_speed * 0.7
        state.velocity_y = (math.sin(angle) + bias_y) * self._movement_speed * 0.7

    @property
    def x(self) -> float:
        return self._state.x

    @property
    def y(self) -> float:
        return self._state.y

    @property
    def radius(self) -> float:
        return self._state.radius

    @property
    def hit_flash(self) -> float:
        return self._state.hit_flash

    def contains_point(self, px: float, py: float) -> bool:
        """Check if point is inside the target."""
        dx = px - self._state.x
        dy = py - self._state.y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= self._state.radius

    def register_hit(self) -> None:
        """Called when target is hit - triggers visual feedback."""
        self._state.hit_flash = 0.15  # Flash duration in seconds

    def update(self, dt: float) -> None:
        """
        Update target state.

        Args:
            dt: Delta time in seconds
        """
        state = self._state

        # Update hit flash
        if state.hit_flash > 0:
            state.hit_flash = max(0, state.hit_flash - dt)

        # Shrink target (but not below minimum)
        if state.radius > self._min_size:
            state.radius = max(self._min_size, state.radius - self._shrink_rate * dt)

        # Update movement based on pattern
        if self._movement_pattern == config.MOVEMENT_DRIFT:
            self._update_drift(dt)
        elif self._movement_pattern == config.MOVEMENT_ORBIT:
            self._update_orbit(dt)
        elif self._movement_pattern == config.MOVEMENT_RANDOM:
            self._update_random(dt)
        elif self._movement_pattern == config.MOVEMENT_BOUNCE:
            self._update_bounce(dt)

    def _update_drift(self, dt: float) -> None:
        """Update drift movement."""
        state = self._state

        # Periodically change direction
        self._drift_change_timer += dt
        if self._drift_change_timer >= self._drift_change_interval:
            self._drift_change_timer = 0
            self._update_drift_velocity(state)

        # Move
        state.x += state.velocity_x * dt
        state.y += state.velocity_y * dt

        # Clamp to play area
        state.x = max(self._play_left + state.radius,
                      min(self._play_right - state.radius, state.x))
        state.y = max(self._play_top + state.radius,
                      min(self._play_bottom - state.radius, state.y))

    def _update_orbit(self, dt: float) -> None:
        """Update orbital movement."""
        state = self._state

        # Angular velocity based on movement speed
        angular_speed = self._movement_speed / state.orbit_radius
        state.orbit_angle += angular_speed * dt

        # Calculate position on orbit
        state.x = state.orbit_center_x + math.cos(state.orbit_angle) * state.orbit_radius
        state.y = state.orbit_center_y + math.sin(state.orbit_angle) * state.orbit_radius

    def _update_random(self, dt: float) -> None:
        """Update random teleport movement."""
        self._random_timer += dt

        if self._random_timer >= self._random_interval:
            self._random_timer = 0
            state = self._state

            # Teleport to new random position
            margin = state.radius + 20
            state.x = random.uniform(self._play_left + margin, self._play_right - margin)
            state.y = random.uniform(self._play_top + margin, self._play_bottom - margin)

    def _update_bounce(self, dt: float) -> None:
        """Update bouncing movement."""
        state = self._state

        # Move
        state.x += state.velocity_x * dt
        state.y += state.velocity_y * dt

        # Bounce off edges
        if state.x - state.radius < self._play_left:
            state.x = self._play_left + state.radius
            state.velocity_x = abs(state.velocity_x)
        elif state.x + state.radius > self._play_right:
            state.x = self._play_right - state.radius
            state.velocity_x = -abs(state.velocity_x)

        if state.y - state.radius < self._play_top:
            state.y = self._play_top + state.radius
            state.velocity_y = abs(state.velocity_y)
        elif state.y + state.radius > self._play_bottom:
            state.y = self._play_bottom - state.radius
            state.velocity_y = -abs(state.velocity_y)

    def set_movement_speed(self, speed: float) -> None:
        """Update movement speed (for difficulty scaling)."""
        self._movement_speed = speed

        # Update velocity magnitude for bounce/drift patterns
        if self._movement_pattern == config.MOVEMENT_BOUNCE:
            state = self._state
            current_speed = math.sqrt(state.velocity_x**2 + state.velocity_y**2)
            if current_speed > 0:
                scale = speed / current_speed
                state.velocity_x *= scale
                state.velocity_y *= scale

    def set_shrink_rate(self, rate: float) -> None:
        """Update shrink rate (for difficulty scaling)."""
        self._shrink_rate = rate

    def render(self, screen: pygame.Surface) -> None:
        """
        Render the target.

        Args:
            screen: Pygame surface to draw on
        """
        state = self._state
        x = int(state.x)
        y = int(state.y)
        radius = int(state.radius)

        # Hit flash effect
        if state.hit_flash > 0:
            flash_radius = int(radius * 1.3)
            flash_alpha = int(200 * (state.hit_flash / 0.15))
            flash_surf = pygame.Surface((flash_radius * 2, flash_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                flash_surf,
                (*config.HIT_FLASH_COLOR, flash_alpha),
                (flash_radius, flash_radius),
                flash_radius
            )
            screen.blit(flash_surf, (x - flash_radius, y - flash_radius))

        # Main target circle
        pygame.draw.circle(screen, config.TARGET_COLOR, (x, y), radius)

        # Outline
        pygame.draw.circle(screen, config.TARGET_OUTLINE_COLOR, (x, y), radius, 3)

        # Inner rings for visual depth
        if radius > 30:
            pygame.draw.circle(screen, config.TARGET_OUTLINE_COLOR, (x, y), radius - 15, 2)
        if radius > 50:
            pygame.draw.circle(screen, config.TARGET_OUTLINE_COLOR, (x, y), radius - 30, 1)

        # Center dot
        pygame.draw.circle(screen, config.TARGET_OUTLINE_COLOR, (x, y), 4)
