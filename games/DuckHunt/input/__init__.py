"""DuckHunt Input Module - Re-exports from common input module."""
from ams.games.input import InputEvent, InputManager
from ams.games.input.sources import InputSource, MouseInputSource

__all__ = [
    'InputEvent',
    'InputManager',
    'InputSource',
    'MouseInputSource',
]
