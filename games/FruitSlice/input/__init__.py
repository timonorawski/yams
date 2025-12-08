"""FruitSlice Input Module - Re-exports from common input module."""
from games.common.input import InputEvent, InputManager
from games.common.input.sources import InputSource, MouseInputSource

__all__ = ['InputEvent', 'InputManager', 'InputSource', 'MouseInputSource']
