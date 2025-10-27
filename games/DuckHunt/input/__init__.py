"""Input abstraction layer for Duck Hunt game."""

from input.input_event import InputEvent
from input.input_manager import InputManager
from input.sources.base import InputSource
from input.sources.mouse import MouseInputSource

__all__ = [
    'InputEvent',
    'InputManager',
    'InputSource',
    'MouseInputSource',
]
