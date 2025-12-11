"""
Backward compatibility - re-exports from ams.games.

This module provides backward compatibility for code that imports from games.common.
All functionality has been moved to ams.games.
"""

# Re-export everything from ams.games for backward compatibility
from ams.games import *
from ams.games.game_engine import *

__all__ = [
    'GameState',
    'BaseGame',
    'GameEngine',
    'GameEngineSkin',
    'EntityPlacement',
    'GameEngineLevelData',
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
