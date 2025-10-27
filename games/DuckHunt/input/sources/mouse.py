"""
Mouse input source for the Duck Hunt game.

This module provides a concrete implementation of InputSource that
converts pygame mouse events into InputEvent models.
"""

import time
from typing import List
import pygame
from models import Vector2D, EventType
from input.input_event import InputEvent
from input.sources.base import InputSource


class MouseInputSource(InputSource):
    """Mouse-based input source using pygame events.

    Converts pygame mouse button clicks into InputEvent models.
    This is the primary input source for development and testing
    without specialized hardware.

    The event_type is determined later by the game logic (whether
    the click hit a target or not), so all mouse clicks start as
    EventType.HIT by default.

    Attributes:
        _event_queue: Internal queue of events collected since last poll

    Examples:
        >>> import pygame
        >>> pygame.init()
        >>> source = MouseInputSource()
        >>> source.update(0.016)  # Process pygame events
        >>> events = source.poll_events()  # Get collected events
    """

    def __init__(self):
        """Initialize the mouse input source."""
        self._event_queue: List[InputEvent] = []

    def poll_events(self) -> List[InputEvent]:
        """Get new input events since last poll.

        Returns all collected mouse click events and clears the queue.

        Returns:
            List of InputEvent objects from mouse clicks, empty if no clicks

        Examples:
            >>> source = MouseInputSource()
            >>> events = source.poll_events()
            >>> len(events)
            0
        """
        events = self._event_queue.copy()
        self._event_queue.clear()
        return events

    def update(self, dt: float) -> None:
        """Process pygame events and collect mouse clicks.

        Processes all pygame events and converts MOUSEBUTTONDOWN events
        (left button only) into InputEvent models with validated coordinates.

        Args:
            dt: Delta time in seconds since last update (unused for mouse input)

        Examples:
            >>> source = MouseInputSource()
            >>> source.update(0.016)  # Processes pygame events
        """
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button only
                    # Get mouse position and create validated InputEvent
                    pos_x, pos_y = event.pos

                    # Create Vector2D with type coercion (pygame gives ints)
                    position = Vector2D(x=float(pos_x), y=float(pos_y))

                    # Create InputEvent with current timestamp
                    input_event = InputEvent(
                        position=position,
                        timestamp=time.monotonic(),
                        event_type=EventType.HIT  # Game logic will determine if actually hit
                    )

                    self._event_queue.append(input_event)

            # Important: Re-post non-mouse events so other systems can handle them
            # (like QUIT events for the game loop)
            elif event.type != pygame.MOUSEMOTION:  # Skip mouse motion to avoid spam
                pygame.event.post(event)

    def clear(self) -> None:
        """Clear the event queue.

        Useful for resetting input state when starting a new game
        or changing game modes.

        Examples:
            >>> source = MouseInputSource()
            >>> source.clear()
            >>> len(source.poll_events())
            0
        """
        self._event_queue.clear()
