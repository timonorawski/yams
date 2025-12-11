"""
Backward compatibility - re-exports from ams.games.input.sources.

This module provides backward compatibility for code that imports from games.common.input.sources.
All functionality has been moved to ams.games.input.sources.
"""
from ams.games.input.sources import InputSource, MouseInputSource

__all__ = ['InputSource', 'MouseInputSource']
