"""
Browser Input Adapter

Converts browser/pygame events into InputEvent objects that games expect.
Works with both mouse events (desktop) and touch events (mobile).

NOTE: We use late/lazy imports to avoid Pydantic import issues in WASM.
"""
import time
from typing import List, Any

import pygame


class BrowserInputAdapter:
    """
    Adapts browser input events to the InputEvent format games expect.

    Handles:
    - Mouse clicks (MOUSEBUTTONDOWN)
    - Touch events (FINGERDOWN)
    - Touch position normalization

    This implements the same interface as other InputSource classes,
    so games receive input identically regardless of source.
    """

    def __init__(self, screen_width: int, screen_height: int):
        """
        Initialize the input adapter.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._events: List[Any] = []  # Will hold InputEvent objects

        # Lazy-load InputEvent and related classes to avoid Pydantic at import time
        self._InputEvent = None
        self._Vector2D = None
        self._EventType = None

    def handle_pygame_event(self, event: pygame.event.Event):
        """
        Process a pygame event and convert to InputEvent if applicable.

        Args:
            event: Pygame event to process
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Mouse click - position is already in pixels
            if event.button == 1:  # Left click only
                self._add_hit_event(event.pos)

        # NOTE: MOUSEMOTION should NOT create HIT events!
        # The paddle follows via input_mapping.target_x which only triggers on HIT.
        # Mouse tracking for paddle would need a different mechanism (not implemented).

        elif event.type == pygame.FINGERDOWN:
            # Touch event - position is normalized (0.0 to 1.0)
            x = int(event.x * self.screen_width)
            y = int(event.y * self.screen_height)
            self._add_hit_event((x, y))

        # NOTE: FINGERMOTION should NOT create HIT events - same as MOUSEMOTION

    def _ensure_imports(self):
        """Lazily import Pydantic-based classes when first needed."""
        if self._InputEvent is None:
            from models import Vector2D, EventType
            from ams.games.input import InputEvent
            self._InputEvent = InputEvent
            self._Vector2D = Vector2D
            self._EventType = EventType

    def _add_hit_event(self, pos: tuple):
        """
        Create and queue a hit event.

        Args:
            pos: (x, y) position in pixels
        """
        self._ensure_imports()
        event = self._InputEvent(
            position=self._Vector2D(x=float(pos[0]), y=float(pos[1])),
            timestamp=time.monotonic(),
            event_type=self._EventType.HIT,
        )
        self._events.append(event)
        # Debug: log every 60th event or all clicks
        if len(self._events) == 1 or len(self._events) % 60 == 0:
            print(f"[InputAdapter] Event queued: pos={pos}, queue_size={len(self._events)}")

    def get_events(self) -> List[Any]:
        """
        Get all pending input events and clear the queue.

        Returns:
            List of InputEvent objects
        """
        events = self._events[:]
        self._events.clear()
        return events

    def update(self, dt: float):
        """
        Update method for InputSource compatibility.

        Args:
            dt: Delta time (unused)
        """
        # No periodic updates needed for browser input
        pass

    def resize(self, width: int, height: int):
        """
        Update screen dimensions (for responsive layouts).

        Args:
            width: New screen width
            height: New screen height
        """
        self.screen_width = width
        self.screen_height = height
