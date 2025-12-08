"""
Input Manager - Collects input from various sources.

This is a shared module used by all games.
"""
from typing import List, Optional

from games.common.input.input_event import InputEvent
from games.common.input.sources.base import InputSource


class InputManager:
    """Manages input sources and collects events.

    The InputManager allows games to switch between different input sources
    (mouse, laser pointer, impact detection) at runtime without changing game logic.
    """

    def __init__(self, source: Optional[InputSource] = None):
        """Initialize with an optional input source."""
        self._source = source

    def set_source(self, source: InputSource) -> None:
        """Set the input source."""
        self._source = source

    def get_source(self) -> Optional[InputSource]:
        """Get the currently active input source."""
        return self._source

    def has_source(self) -> bool:
        """Check if an input source is currently active."""
        return self._source is not None

    def update(self, dt: float) -> None:
        """Update the active input source.

        Args:
            dt: Delta time in seconds since last update.
        """
        if self._source is not None:
            self._source.update(dt)

    def get_events(self) -> List[InputEvent]:
        """Get collected events since last update."""
        if self._source is None:
            return []
        return self._source.poll_events()

    def clear_events(self) -> None:
        """Clear any pending events from the active source."""
        if self._source is not None:
            self._source.poll_events()
