"""
Base Input Source - Abstract interface for input backends.

This is a shared module used by all games.
"""
from abc import ABC, abstractmethod
from typing import List

from games.common.input.input_event import InputEvent


class InputSource(ABC):
    """Abstract base class for input sources.

    All input backends (mouse, laser, impact detection) must implement this interface.
    """

    @abstractmethod
    def poll_events(self) -> List[InputEvent]:
        """Poll for new input events.

        Returns:
            List of InputEvent objects since last poll.
        """
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        """Update the input source, collecting events.

        Args:
            dt: Delta time in seconds since last update.
        """
        pass
