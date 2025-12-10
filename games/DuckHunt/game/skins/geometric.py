"""
Geometric skin for DuckHunt - simple colored circles.

This skin renders targets as colored circles, useful for:
- CV calibration and testing
- Accessibility (high contrast)
- Development without asset dependencies
"""

import pygame

from models import TargetState
from ..duck_target import DuckTarget, DuckPhase
from .base import GameSkin


class GeometricSkin(GameSkin):
    """Renders targets as colored circles with no audio."""

    NAME = "geometric"
    DESCRIPTION = "Simple shapes for testing and CV calibration"

    # Colors for different target states
    STATE_COLORS = {
        TargetState.ALIVE: (255, 100, 100),   # Red - active target
        TargetState.HIT: (150, 150, 150),     # Gray - hit
        TargetState.ESCAPED: (255, 200, 50),  # Yellow - escaped
    }

    # Colors for duck phases (override state colors)
    PHASE_COLORS = {
        DuckPhase.FLYING: (255, 100, 100),    # Red
        DuckPhase.HIT_PAUSE: (255, 255, 100), # Yellow flash
        DuckPhase.FALLING: (150, 150, 150),   # Gray
    }

    def render_target(self, target: DuckTarget, screen: pygame.Surface) -> None:
        """Render target as a colored circle.

        Args:
            target: The DuckTarget to render
            screen: Pygame surface to draw on
        """
        pos = (int(target.data.position.x), int(target.data.position.y))
        radius = int(target.data.size / 2)

        # Use phase color if available, fall back to state color
        color = self.PHASE_COLORS.get(
            target.phase,
            self.STATE_COLORS.get(target.data.state, (255, 255, 255))
        )

        # Draw filled circle
        pygame.draw.circle(screen, color, pos, radius)

        # Draw white outline for visibility
        pygame.draw.circle(screen, (255, 255, 255), pos, radius, 2)
