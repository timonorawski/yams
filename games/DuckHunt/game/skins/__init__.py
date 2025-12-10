"""
DuckHunt game skins - visual and audio presentation layers.

Skins provide different visual representations and audio for the game
without changing game logic. Available skins:
- geometric: Simple colored circles (CV-friendly, testing)
- classic: Duck Hunt sprites with authentic sounds
"""

from .base import GameSkin
from .geometric import GeometricSkin
from .classic import ClassicSkin

__all__ = ['GameSkin', 'GeometricSkin', 'ClassicSkin']
