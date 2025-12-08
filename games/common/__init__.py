"""
Common game utilities shared across all games.

Provides:
- base_game: BaseGame class that all games should inherit from
- game_state: Standard GameState enum for platform compatibility
- palette: AMS color palette management and test palettes
- quiver: Physical ammo constraints (arrows, darts, etc.)
- pacing: Device-speed pacing presets
- input: Common input event handling
"""

from games.common.game_state import GameState
from games.common.base_game import BaseGame
from games.common.palette import GamePalette, TEST_PALETTES, get_palette_names
from games.common.quiver import QuiverState, create_quiver
from games.common.pacing import get_pacing_preset, get_pacing_names, scale_for_pacing

__all__ = [
    'GameState',
    'BaseGame',
    'GamePalette',
    'TEST_PALETTES',
    'get_palette_names',
    'QuiverState',
    'create_quiver',
    'get_pacing_preset',
    'get_pacing_names',
    'scale_for_pacing',
]
