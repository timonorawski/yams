"""
Input manager for the Duck Hunt game.

This module provides the InputManager class that manages the active input source
and provides a unified interface for the game engine to receive input events.
"""

from typing import List, Optional
from input.input_event import InputEvent
from input.sources.base import InputSource


class InputManager:
    """Manages the active input source and provides unified event access.

    The InputManager allows the game to switch between different input sources
    (mouse, laser pointer, impact detection) at runtime without changing game logic.
    Only one input source can be active at a time.

    Attributes:
        _source: The currently active input source

    Examples:
        >>> from input.sources.mouse import MouseInputSource
        >>> manager = InputManager(MouseInputSource())
        >>> manager.update(0.016)
        >>> events = manager.get_events()
    """

    def __init__(self, source: Optional[InputSource] = None):
        """Initialize the input manager with an optional input source.

        Args:
            source: The initial input source, or None to start with no source

        Examples:
            >>> from input.sources.mouse import MouseInputSource
            >>> manager = InputManager(MouseInputSource())
            >>> # Or start with no source
            >>> manager = InputManager()
        """
        self._source: Optional[InputSource] = source

    def set_source(self, source: InputSource) -> None:
        """Set or change the active input source.

        This allows runtime switching between different input types
        (e.g., mouse for testing, laser pointer for gameplay).

        Args:
            source: The new input source to use

        Raises:
            TypeError: If source is not an instance of InputSource

        Examples:
            >>> from input.sources.mouse import MouseInputSource
            >>> manager = InputManager()
            >>> manager.set_source(MouseInputSource())
        """
        if not isinstance(source, InputSource):
            raise TypeError(
                f"source must be an instance of InputSource, got {type(source).__name__}"
            )
        self._source = source

    def get_source(self) -> Optional[InputSource]:
        """Get the currently active input source.

        Returns:
            The active InputSource, or None if no source is set

        Examples:
            >>> manager = InputManager()
            >>> manager.get_source() is None
            True
        """
        return self._source

    def has_source(self) -> bool:
        """Check if an input source is currently active.

        Returns:
            True if a source is set, False otherwise

        Examples:
            >>> manager = InputManager()
            >>> manager.has_source()
            False
            >>> from input.sources.mouse import MouseInputSource
            >>> manager.set_source(MouseInputSource())
            >>> manager.has_source()
            True
        """
        return self._source is not None

    def update(self, dt: float) -> None:
        """Update the active input source.

        Calls the update method of the active source, if one is set.
        Safe to call even if no source is active.

        Args:
            dt: Delta time in seconds since last update

        Examples:
            >>> manager = InputManager()
            >>> manager.update(0.016)  # Safe even with no source
        """
        if self._source is not None:
            self._source.update(dt)

    def get_events(self) -> List[InputEvent]:
        """Get new input events from the active source.

        Returns events from the active source's poll_events() method.
        Returns an empty list if no source is active.

        Returns:
            List of InputEvent objects, empty if no source or no events

        Examples:
            >>> from input.sources.mouse import MouseInputSource
            >>> manager = InputManager(MouseInputSource())
            >>> events = manager.get_events()
            >>> for event in events:
            ...     print(f"Input at {event.position}")
        """
        if self._source is None:
            return []
        return self._source.poll_events()

    def clear_events(self) -> None:
        """Clear any pending events from the active source.

        Useful when transitioning between game states (e.g., menu to gameplay)
        to avoid processing stale input events.

        Examples:
            >>> manager = InputManager(MouseInputSource())
            >>> manager.clear_events()  # Clear any buffered events
        """
        if self._source is not None:
            # Poll and discard events to clear the queue
            self._source.poll_events()
