"""
Input Sources - Various input backends.
"""
from games.common.input.sources.base import InputSource
from games.common.input.sources.mouse import MouseInputSource

__all__ = ['InputSource', 'MouseInputSource']
