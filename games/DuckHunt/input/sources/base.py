"""
Abstract base class for input sources.

This module defines the InputSource interface that all input sources must implement.
This enables the game to work with any coordinate-based input (mouse, laser pointer, impact detection)
without changing game logic.
"""

from abc import ABC, abstractmethod
from typing import List
from input.input_event import InputEvent


class InputSource(ABC):
    """Abstract base class for input sources.

    All input sources must implement this interface to be compatible
    with the InputManager and game engine.

    Subclasses must implement:
        - poll_events(): Return new input events since last poll
        - update(dt): Update source state for time-based processing

    Examples:
        >>> class MyInputSource(InputSource):
        ...     def poll_events(self) -> List[InputEvent]:
        ...         return []  # Return collected events
        ...     def update(self, dt: float) -> None:
        ...         pass  # Update internal state
    """

    @abstractmethod
    def poll_events(self) -> List[InputEvent]:
        """Get new input events since last poll.

        This method should return all events that have occurred since
        the last call to poll_events(), then clear the internal event queue.

        Returns:
            List of InputEvent objects, empty list if no events

        Examples:
            >>> source = MyInputSource()
            >>> events = source.poll_events()
            >>> for event in events:
            ...     print(f"Event at {event.position}")
        """
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        """Update source state (for time-based processing).

        Called every frame to allow the input source to perform
        time-based updates, such as smoothing, filtering, or
        timeout handling.

        Args:
            dt: Delta time in seconds since last update

        Examples:
            >>> source = MyInputSource()
            >>> source.update(0.016)  # One frame at 60 FPS
        """
        pass
