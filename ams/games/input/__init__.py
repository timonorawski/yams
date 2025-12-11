"""
Input abstraction layer for AMS games.

Provides unified input handling that works identically with mouse,
laser pointer, or detection backends.
"""

from ams.games.input.input_event import InputEvent
from ams.games.input.input_manager import InputManager

__all__ = ['InputEvent', 'InputManager']
