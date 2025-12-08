"""
Game Adapter - Bridges AMS detection backends to game input systems.

This module provides adapters that allow games to work identically whether
running standalone (with mouse/keyboard) or through AMS (with CV detection).

The key abstraction is that games always receive InputEvents in pixel coordinates,
regardless of the input source. AMS backends produce PlaneHitEvents in normalized
[0,1] coordinates, which are converted to pixel coordinates before being passed
to games.

Design Principles:
- Games should be developed and tested with mouse input (no hardware required)
- The same game code works with any AMS detection backend
- Games don't need to know whether they're running standalone or through AMS

Usage:
    # Standalone mode (game handles its own input)
    from input.input_manager import InputManager
    from input.sources.mouse import MouseInputSource
    input_manager = InputManager(MouseInputSource())

    # AMS mode (adapter converts PlaneHitEvents to InputEvents)
    from ams.game_adapter import AMSInputAdapter
    adapter = AMSInputAdapter(ams_session, display_width, display_height)
    input_manager = InputManager(adapter)

    # Game code is identical in both cases:
    events = input_manager.get_events()
    game_mode.handle_input(events)
"""

import time
from typing import List, Optional, TYPE_CHECKING

# Import from the games directory for InputEvent compatibility
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'games', 'DuckHunt'))

from input.input_event import InputEvent
from input.sources.base import InputSource
from models import Vector2D, EventType

if TYPE_CHECKING:
    from ams.session import AMSSession


class AMSInputAdapter(InputSource):
    """
    Adapter that makes an AMS session look like a game InputSource.

    This allows games to use their existing InputManager and InputEvent
    system while receiving events from any AMS detection backend (laser,
    object detection, etc.).

    The adapter:
    1. Polls PlaneHitEvents from the AMS session
    2. Converts normalized [0,1] coordinates to pixel coordinates
    3. Wraps them in InputEvent objects that games already understand

    Attributes:
        ams_session: The AMS session providing detection events
        display_width: Display width in pixels
        display_height: Display height in pixels

    Example:
        >>> from ams.session import AMSSession
        >>> from ams.game_adapter import AMSInputAdapter
        >>> from input.input_manager import InputManager
        >>>
        >>> # Create AMS session with laser backend
        >>> ams = AMSSession(laser_backend)
        >>>
        >>> # Create adapter that converts to game input
        >>> adapter = AMSInputAdapter(ams, 1920, 1080)
        >>>
        >>> # Use with game's existing input manager
        >>> input_manager = InputManager(adapter)
        >>> events = input_manager.get_events()  # Returns List[InputEvent]
    """

    def __init__(
        self,
        ams_session: 'AMSSession',
        display_width: int,
        display_height: int
    ):
        """
        Initialize the AMS input adapter.

        Args:
            ams_session: AMS session to poll events from
            display_width: Display width in pixels (for coordinate conversion)
            display_height: Display height in pixels (for coordinate conversion)
        """
        self.ams_session = ams_session
        self.display_width = display_width
        self.display_height = display_height
        self._event_queue: List[InputEvent] = []

    def poll_events(self) -> List[InputEvent]:
        """
        Get new input events since last poll.

        Polls PlaneHitEvents from AMS and converts them to InputEvents
        with pixel coordinates.

        Returns:
            List of InputEvent objects with pixel coordinates
        """
        # Get events from our queue (populated by update())
        events = self._event_queue.copy()
        self._event_queue.clear()
        return events

    def update(self, dt: float) -> None:
        """
        Update the adapter (called each frame).

        Polls the AMS session for new PlaneHitEvents and converts
        them to InputEvents.

        Args:
            dt: Delta time in seconds since last update
        """
        # Update the AMS session
        self.ams_session.update(dt)

        # Get events from AMS
        plane_events = self.ams_session.poll_events()

        # Convert to InputEvents
        for plane_event in plane_events:
            # Convert normalized [0,1] to pixel coordinates
            pixel_x = plane_event.x * self.display_width
            pixel_y = plane_event.y * self.display_height

            # Create InputEvent with pixel position
            input_event = InputEvent(
                position=Vector2D(x=pixel_x, y=pixel_y),
                timestamp=plane_event.timestamp,
                event_type=EventType.HIT  # All detections are potential hits
            )

            self._event_queue.append(input_event)

    def clear(self) -> None:
        """Clear the event queue."""
        self._event_queue.clear()


class StandaloneInputAdapter(InputSource):
    """
    Passthrough adapter for standalone mode.

    This adapter wraps an existing InputSource (like MouseInputSource)
    and passes through events unchanged. It exists to provide a consistent
    interface whether running in standalone or AMS mode.

    In most cases you can just use MouseInputSource directly, but this
    adapter is useful when you want to add logging, filtering, or other
    processing to standalone input.

    Example:
        >>> from input.sources.mouse import MouseInputSource
        >>> from ams.game_adapter import StandaloneInputAdapter
        >>>
        >>> mouse = MouseInputSource()
        >>> adapter = StandaloneInputAdapter(mouse)
        >>>
        >>> # Use identically to AMSInputAdapter
        >>> input_manager = InputManager(adapter)
    """

    def __init__(self, source: InputSource):
        """
        Initialize the standalone adapter.

        Args:
            source: The underlying input source to wrap
        """
        self.source = source

    def poll_events(self) -> List[InputEvent]:
        """Get events from the underlying source."""
        return self.source.poll_events()

    def update(self, dt: float) -> None:
        """Update the underlying source."""
        self.source.update(dt)

    def clear(self) -> None:
        """Clear events from the underlying source."""
        if hasattr(self.source, 'clear'):
            self.source.clear()


def create_input_source(
    mode: str,
    ams_session: Optional['AMSSession'] = None,
    display_width: int = 800,
    display_height: int = 600
) -> InputSource:
    """
    Factory function to create the appropriate input source.

    This is a convenience function for games that want to support
    both standalone and AMS modes without complex setup code.

    Args:
        mode: Either 'standalone' or 'ams'
        ams_session: Required if mode is 'ams'
        display_width: Display width in pixels
        display_height: Display height in pixels

    Returns:
        An InputSource that can be used with InputManager

    Raises:
        ValueError: If mode is 'ams' but no ams_session provided

    Example:
        >>> # For standalone development
        >>> source = create_input_source('standalone', display_width=1920, display_height=1080)
        >>>
        >>> # For AMS mode
        >>> source = create_input_source('ams', ams_session=ams, display_width=1920, display_height=1080)
        >>>
        >>> # Either way, use with InputManager
        >>> input_manager = InputManager(source)
    """
    if mode == 'standalone':
        from input.sources.mouse import MouseInputSource
        return MouseInputSource()

    elif mode == 'ams':
        if ams_session is None:
            raise ValueError("ams_session required for AMS mode")
        return AMSInputAdapter(ams_session, display_width, display_height)

    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'standalone' or 'ams'")
