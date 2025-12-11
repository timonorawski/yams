"""
AMS Game Framework.

Provides:
- base_game: BaseGame class that all games should inherit from
- game_engine: YAML-driven GameEngine with Lua behaviors
- game_state: Standard GameState enum for platform compatibility
- palette: AMS color palette management and test palettes
- quiver: Physical ammo constraints (arrows, darts, etc.)
- pacing: Device-speed pacing presets
- levels: YAML-based level loading and level groups
- input: Common input event handling
"""

from ams.games.game_state import GameState
from ams.games.base_game import BaseGame
from ams.games.palette import GamePalette, TEST_PALETTES, get_palette_names
from ams.games.quiver import QuiverState, create_quiver
from ams.games.pacing import get_pacing_preset, get_pacing_names, scale_for_pacing
from ams.games.levels import (
    LevelInfo,
    LevelGroup,
    LevelLoader,
    SimpleLevelLoader,
)

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
    'LevelInfo',
    'LevelGroup',
    'LevelLoader',
    'SimpleLevelLoader',
]
