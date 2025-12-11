"""
Backward compatibility - re-exports from ams.games.input.

This module provides backward compatibility for code that imports from games.common.input.
All functionality has been moved to ams.games.input.
"""
from ams.games.input import InputEvent, InputManager

__all__ = ['InputEvent', 'InputManager']
