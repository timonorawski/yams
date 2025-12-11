"""
BalloonPop Input Module

Re-exports from common input module for convenience.
"""
from ams.games.input import InputEvent, InputManager
from ams.games.input.sources import InputSource, MouseInputSource

__all__ = [
    'InputEvent',
    'InputManager',
    'InputSource',
    'MouseInputSource',
]
