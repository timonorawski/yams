"""
LoveOMeter meter visualization.

The thermometer-style meter that fills with hits and drains over time.
"""
import math
from dataclasses import dataclass
from typing import Tuple

import pygame

from games.LoveOMeter import config


@dataclass
class MeterState:
    """Current state of the meter."""
    fill: float  # 0.0 to 1.0
    drain_rate: float  # per second
    fill_per_hit: float
    # Visual effects
    pulse: float = 0.0  # Pulse animation for urgency
    recent_gain: float = 0.0  # For gain animation


class Meter:
    """
    The Love-O-Meter thermometer display.

    Visual feedback for player progress. Fills when target is hit,
    drains constantly. Fill it completely to win (sprint mode) or
    keep it above threshold (endurance mode).
    """

    def __init__(
        self,
        x: int = config.METER_X,
        y: int = config.METER_Y,
        width: int = config.METER_WIDTH,
        height: int = config.METER_HEIGHT,
        initial_fill: float = 0.3,
        drain_rate: float = 0.05,
        fill_per_hit: float = 0.08,
    ):
        """
        Initialize the meter.

        Args:
            x: Left edge X position
            y: Top Y position
            width: Meter width
            height: Meter height
            initial_fill: Starting fill level (0.0 to 1.0)
            drain_rate: Fill lost per second
            fill_per_hit: Fill gained per hit
        """
        self._x = x
        self._y = y
        self._width = width
        self._height = height

        self._state = MeterState(
            fill=initial_fill,
            drain_rate=drain_rate,
            fill_per_hit=fill_per_hit,
        )

        # Threshold markers
        self._win_threshold = 1.0
        self._danger_threshold = 0.2

        # Animation
        self._glow_phase = 0.0

    @property
    def fill(self) -> float:
        """Current fill level (0.0 to 1.0)."""
        return self._state.fill

    @property
    def is_empty(self) -> bool:
        """Check if meter is completely empty."""
        return self._state.fill <= 0

    @property
    def is_full(self) -> bool:
        """Check if meter is completely full."""
        return self._state.fill >= self._win_threshold

    @property
    def is_danger(self) -> bool:
        """Check if meter is in danger zone."""
        return self._state.fill < self._danger_threshold

    def add_hit(self) -> None:
        """Register a hit - add to the meter."""
        self._state.fill = min(1.0, self._state.fill + self._state.fill_per_hit)
        self._state.recent_gain = self._state.fill_per_hit

    def set_drain_rate(self, rate: float) -> None:
        """Update drain rate (for difficulty scaling)."""
        self._state.drain_rate = rate

    def set_fill_per_hit(self, amount: float) -> None:
        """Update fill amount per hit."""
        self._state.fill_per_hit = amount

    def update(self, dt: float) -> None:
        """
        Update meter state.

        Args:
            dt: Delta time in seconds
        """
        state = self._state

        # Drain the meter
        state.fill = max(0.0, state.fill - state.drain_rate * dt)

        # Update recent gain animation
        if state.recent_gain > 0:
            state.recent_gain = max(0, state.recent_gain - dt * 0.3)

        # Update pulse for danger state
        if self.is_danger:
            state.pulse = (math.sin(pygame.time.get_ticks() / 100) + 1) / 2
        else:
            state.pulse = 0

        # Update glow animation
        self._glow_phase += dt * 2

    def render(self, screen: pygame.Surface) -> None:
        """
        Render the meter.

        Args:
            screen: Pygame surface to draw on
        """
        x, y = self._x, self._y
        w, h = self._width, self._height
        border = config.METER_BORDER
        state = self._state

        # Background (empty meter)
        bg_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, config.METER_EMPTY_COLOR, bg_rect)

        # Fill level
        fill_height = int(h * state.fill)
        if fill_height > 0:
            fill_rect = pygame.Rect(
                x + border,
                y + h - fill_height - border,
                w - border * 2,
                fill_height
            )

            # Color gradient based on fill level
            if state.fill > 0.7:
                fill_color = (255, 50, 150)  # Hot pink when high
            elif state.fill > 0.4:
                fill_color = config.METER_FILL_COLOR
            else:
                # Lerp toward red when low
                t = state.fill / 0.4
                fill_color = (
                    int(255),
                    int(50 * t),
                    int(100 * t)
                )

            pygame.draw.rect(screen, fill_color, fill_rect)

            # Glow effect at top of fill
            glow_intensity = 0.3 + 0.2 * math.sin(self._glow_phase)
            glow_height = 10
            if fill_height > glow_height:
                glow_surf = pygame.Surface((w - border * 2, glow_height), pygame.SRCALPHA)
                glow_alpha = int(150 * glow_intensity)
                glow_surf.fill((*config.METER_GLOW_COLOR, glow_alpha))
                screen.blit(glow_surf, (x + border, y + h - fill_height - border))

        # Recent gain highlight
        if state.recent_gain > 0:
            gain_height = int(h * state.recent_gain)
            gain_alpha = int(200 * (state.recent_gain / self._state.fill_per_hit))
            gain_surf = pygame.Surface((w - border * 2, gain_height), pygame.SRCALPHA)
            gain_surf.fill((255, 255, 200, gain_alpha))
            screen.blit(gain_surf, (x + border, y + h - fill_height - border))

        # Danger pulse overlay
        if state.pulse > 0:
            pulse_alpha = int(80 * state.pulse)
            pulse_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pulse_surf.fill((255, 0, 0, pulse_alpha))
            screen.blit(pulse_surf, (x, y))

        # Border
        pygame.draw.rect(screen, (200, 200, 200), bg_rect, 3)

        # Threshold markers
        self._render_threshold_marker(screen, 1.0, "WIN", (100, 255, 100))
        if self._danger_threshold > 0:
            self._render_threshold_marker(screen, self._danger_threshold, "", (255, 100, 100))

        # Bulb at bottom (thermometer style)
        bulb_radius = w // 2 + 5
        bulb_x = x + w // 2
        bulb_y = y + h + bulb_radius - 5

        # Bulb fill color matches meter
        if state.fill > 0:
            pygame.draw.circle(screen, config.METER_FILL_COLOR, (bulb_x, bulb_y), bulb_radius)
        else:
            pygame.draw.circle(screen, config.METER_EMPTY_COLOR, (bulb_x, bulb_y), bulb_radius)
        pygame.draw.circle(screen, (200, 200, 200), (bulb_x, bulb_y), bulb_radius, 3)

    def _render_threshold_marker(
        self,
        screen: pygame.Surface,
        threshold: float,
        label: str,
        color: Tuple[int, int, int]
    ) -> None:
        """Render a threshold marker line."""
        x, y = self._x, self._y
        w, h = self._width, self._height

        marker_y = y + h - int(h * threshold)

        # Line
        pygame.draw.line(
            screen,
            color,
            (x - 10, marker_y),
            (x + w + 10, marker_y),
            2
        )

        # Label
        if label:
            try:
                font = pygame.font.Font(None, 24)
                text = font.render(label, True, color)
                screen.blit(text, (x + w + 15, marker_y - 10))
            except Exception:
                pass

    def render_percentage(self, screen: pygame.Surface) -> None:
        """Render the fill percentage as text."""
        try:
            font = pygame.font.Font(None, 48)
            percent = int(self._state.fill * 100)

            # Color based on level
            if percent >= 70:
                color = (100, 255, 100)
            elif percent >= 30:
                color = (255, 255, 100)
            else:
                color = (255, 100, 100)

            text = font.render(f"{percent}%", True, color)
            text_rect = text.get_rect(center=(self._x + self._width // 2, self._y - 30))
            screen.blit(text, text_rect)
        except Exception:
            pass
