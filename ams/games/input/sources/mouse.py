"""
Mouse Input Source - Mouse click input for development/testing.

This is a shared module used by all games.
"""
import time
from typing import List

import pygame

from models import Vector2D, EventType
from ams.games.input.input_event import InputEvent
from ams.games.input.sources.base import InputSource


class MouseInputSource(InputSource):
    """Mouse click input source for development testing.

    Converts pygame mouse button clicks into InputEvent models.
    Non-mouse events are re-posted to the pygame event queue for the main loop.
    """

    def __init__(self):
        """Initialize the mouse input source."""
        self._event_queue: List[InputEvent] = []

    def poll_events(self) -> List[InputEvent]:
        """Get new input events since last poll."""
        events = self._event_queue.copy()
        self._event_queue.clear()
        return events

    def update(self, dt: float) -> None:
        """Process pygame events and collect mouse clicks."""
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button only
                    pos_x, pos_y = event.pos
                    position = Vector2D(x=float(pos_x), y=float(pos_y))
                    input_event = InputEvent(
                        position=position,
                        timestamp=time.monotonic(),
                        event_type=EventType.HIT
                    )
                    self._event_queue.append(input_event)
            elif event.type != pygame.MOUSEMOTION:
                # Re-post non-mouse events for the main loop to handle
                pygame.event.post(event)

    def clear(self) -> None:
        """Clear the event queue."""
        self._event_queue.clear()
