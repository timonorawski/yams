"""
Common palette management for AMS-integrated games.

Provides test palettes for standalone mode and utilities for
working with AMS-constrained color palettes.
"""

from typing import List, Tuple, Optional
import random

# Type alias for RGB color
Color = Tuple[int, int, int]

# Default palette when no AMS constraints (dev mode)
DEFAULT_PALETTE: List[Color] = [
    (255, 0, 0),     # Red
    (0, 255, 0),     # Green
    (0, 0, 255),     # Blue
    (255, 255, 0),   # Yellow
    (255, 0, 255),   # Magenta
    (0, 255, 255),   # Cyan
    (255, 128, 0),   # Orange
    (128, 0, 255),   # Purple
]

# Test palettes for standalone mode - cycle with P key
TEST_PALETTES = {
    'full': [
        (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 0), (255, 0, 255), (0, 255, 255),
        (255, 128, 0), (128, 0, 255),
    ],
    'bw': [
        (0, 0, 0), (255, 255, 255),
    ],
    'warm': [
        (255, 0, 0), (255, 128, 0), (255, 255, 0), (255, 200, 150),
    ],
    'cool': [
        (0, 0, 255), (0, 255, 255), (128, 0, 255), (200, 200, 255),
    ],
    'mono_red': [
        (100, 0, 0), (180, 0, 0), (255, 0, 0), (255, 100, 100),
    ],
    'mono_green': [
        (0, 100, 0), (0, 180, 0), (0, 255, 0), (100, 255, 100),
    ],
    'limited': [
        (255, 255, 255), (255, 0, 0), (0, 0, 255),  # Only 3 colors
    ],
    'orange_dart': [
        # Simulates palette when orange nerf dart is the projectile
        # Orange excluded (too similar to dart)
        (0, 0, 255), (0, 255, 0), (255, 0, 255), (0, 255, 255),
    ],
}


class GamePalette:
    """Manages color palette with AMS constraint support."""

    def __init__(
        self,
        colors: List[Color] = None,
        palette_name: str = None,
        bw_mode: bool = False
    ):
        """
        Initialize palette.

        Args:
            colors: Explicit color list (from AMS calibration)
            palette_name: Name of test palette to use
            bw_mode: Force black/white only (maximum contrast)
        """
        if bw_mode:
            self.colors = TEST_PALETTES['bw'].copy()
            self.name = 'bw'
        elif palette_name and palette_name in TEST_PALETTES:
            self.colors = TEST_PALETTES[palette_name].copy()
            self.name = palette_name
        elif colors:
            self.colors = list(colors)
            self.name = 'custom'
        else:
            self.colors = DEFAULT_PALETTE.copy()
            self.name = 'full'

    def get_target_colors(self, count: int = None) -> List[Color]:
        """Get colors suitable for targets (excludes very dark colors)."""
        bright = [c for c in self.colors if sum(c) > 150]
        if not bright:
            bright = self.colors  # Fallback if all dark
        if count:
            return bright[:count]
        return bright

    def get_background_color(self) -> Color:
        """Get darkest color for background."""
        return min(self.colors, key=lambda c: sum(c))

    def get_ui_color(self) -> Color:
        """Get brightest color for UI text."""
        return max(self.colors, key=lambda c: sum(c))

    def random_target_color(self) -> Color:
        """Get random color for a new target."""
        return random.choice(self.get_target_colors())

    def set_palette(self, palette_name: str) -> bool:
        """
        Switch to a named test palette.

        Args:
            palette_name: Name from TEST_PALETTES

        Returns:
            True if palette found and switched, False otherwise
        """
        if palette_name in TEST_PALETTES:
            self.colors = TEST_PALETTES[palette_name].copy()
            self.name = palette_name
            return True
        return False

    def cycle_palette(self) -> str:
        """
        Cycle to next test palette.

        Returns:
            Name of new palette
        """
        palette_names = list(TEST_PALETTES.keys())
        try:
            current_idx = palette_names.index(self.name)
            next_idx = (current_idx + 1) % len(palette_names)
        except ValueError:
            next_idx = 0
        self.name = palette_names[next_idx]
        self.colors = TEST_PALETTES[self.name].copy()
        return self.name

    def __len__(self) -> int:
        return len(self.colors)

    def __iter__(self):
        return iter(self.colors)


def get_palette_names() -> List[str]:
    """Get list of available test palette names."""
    return list(TEST_PALETTES.keys())
