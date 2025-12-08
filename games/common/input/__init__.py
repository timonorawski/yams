"""
Common Input Module

Provides input abstraction shared by all games.
"""
from games.common.input.input_event import InputEvent
from games.common.input.input_manager import InputManager

__all__ = ['InputEvent', 'InputManager']
