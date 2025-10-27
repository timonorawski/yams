"""
Detection Backend Interface for AMS

Defines the interface between detection systems and AMS.
Detection backends can wrap existing InputSource implementations or implement
new detection methods (CV, AR, etc.).

Key responsibilities:
- Produce PlaneHitEvents in normalized coordinates [0, 1]
- Support calibration (even if no-op for some backends)
- Provide poll-based event retrieval
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import sys
import os

# Add Games/DuckHunt to path to import existing input system
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Games', 'DuckHunt'))

from ams.events import PlaneHitEvent, CalibrationResult


class DetectionBackend(ABC):
    """
    Abstract base class for detection backends.

    All detection methods must implement this interface to work with AMS.
    This includes:
    - Mouse/keyboard input (testing/development)
    - Computer vision detection
    - AR tracking
    - Any other coordinate-based input

    The backend is responsible for:
    1. Converting raw detection to normalized [0, 1] coordinates
    2. Supporting calibration (even if it's a no-op)
    3. Producing PlaneHitEvents that games can consume
    """

    def __init__(self, display_width: int, display_height: int):
        """
        Initialize detection backend.

        Args:
            display_width: Display width in pixels
            display_height: Display height in pixels
        """
        self.display_width = display_width
        self.display_height = display_height
        self.detection_latency_ms = 0.0  # Detection latency in milliseconds

    @abstractmethod
    def poll_events(self) -> List[PlaneHitEvent]:
        """
        Get new detection events since last poll.

        Returns:
            List of PlaneHitEvents in normalized coordinates [0, 1]

        Note:
            Coordinates must be normalized:
            - (0, 0) = top-left
            - (1, 1) = bottom-right
            Independent of display resolution
        """
        pass

    @abstractmethod
    def update(self, dt: float):
        """
        Update backend state (called each frame).

        Args:
            dt: Delta time in seconds since last update
        """
        pass

    @abstractmethod
    def calibrate(self) -> CalibrationResult:
        """
        Run calibration for this detection method.

        For mouse/keyboard: Returns immediate success (no-op)
        For CV: Measures colors, latency, builds detection models
        For AR: Initializes tracking, measures environment

        Returns:
            CalibrationResult with success status and metadata
        """
        pass

    def normalize_coordinates(self, pixel_x: float, pixel_y: float) -> tuple[float, float]:
        """
        Helper to normalize pixel coordinates to [0, 1] range.

        Args:
            pixel_x: X coordinate in pixels
            pixel_y: Y coordinate in pixels

        Returns:
            Tuple of (normalized_x, normalized_y) in [0, 1]
        """
        norm_x = pixel_x / self.display_width
        norm_y = pixel_y / self.display_height

        # Clamp to [0, 1]
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        return norm_x, norm_y

    def get_backend_info(self) -> dict:
        """
        Get information about this backend for debugging.

        Returns:
            Dict with backend name, capabilities, etc.
        """
        return {
            'backend_type': self.__class__.__name__,
            'display_resolution': f"{self.display_width}x{self.display_height}",
            'supports_calibration': True,  # All backends must support calibration interface
        }


class InputSourceAdapter(DetectionBackend):
    """
    Adapter to use existing DuckHunt InputSource with AMS.

    Wraps an InputSource and converts InputEvents to PlaneHitEvents
    with normalized coordinates.

    This enables using the existing mouse input (and future input sources)
    with AMS temporal state management.
    """

    def __init__(
        self,
        input_source,  # InputSource from Games/DuckHunt
        display_width: int,
        display_height: int
    ):
        """
        Create adapter for an existing InputSource.

        Args:
            input_source: An instance of InputSource (e.g., MouseInputSource)
            display_width: Display width in pixels
            display_height: Display height in pixels
        """
        super().__init__(display_width, display_height)
        self.input_source = input_source

    def poll_events(self) -> List[PlaneHitEvent]:
        """
        Poll InputSource and convert to PlaneHitEvents.

        Returns:
            List of PlaneHitEvents with normalized coordinates
        """
        # Get events from wrapped input source
        input_events = self.input_source.poll_events()

        # Convert to PlaneHitEvents
        plane_events = []
        for event in input_events:
            # Normalize coordinates
            norm_x, norm_y = self.normalize_coordinates(
                event.position.x,
                event.position.y
            )

            # Create PlaneHitEvent
            plane_event = PlaneHitEvent(
                x=norm_x,
                y=norm_y,
                timestamp=event.timestamp,
                confidence=1.0,  # Mouse input is always confident
                detection_method=f"input_source_{self.input_source.__class__.__name__}",
                latency_ms=self.detection_latency_ms,  # Include backend latency
                metadata={
                    'event_type': event.event_type.value,
                    'original_position': {
                        'x': event.position.x,
                        'y': event.position.y
                    }
                }
            )

            plane_events.append(plane_event)

        return plane_events

    def update(self, dt: float):
        """Update wrapped input source."""
        self.input_source.update(dt)

    def calibrate(self) -> CalibrationResult:
        """
        No-op calibration for input sources.

        Mouse/keyboard don't need calibration - they already produce
        accurate pixel coordinates.

        Returns:
            Immediate success result
        """
        return CalibrationResult(
            success=True,
            method="input_source_no_op",
            notes="Input sources don't require calibration"
        )


if __name__ == "__main__":
    # Example: Create a simple mock input source
    from dataclasses import dataclass
    import time

    # Mock the minimal parts we need from DuckHunt
    @dataclass(frozen=True)
    class Vector2D:
        x: float
        y: float

    class EventType:
        HIT = "hit"

    class InputEvent:
        def __init__(self, position, timestamp, event_type):
            self.position = position
            self.timestamp = timestamp
            self.event_type = type('obj', (object,), {'value': event_type})()

    class MockInputSource:
        def __init__(self):
            self.events = []

        def poll_events(self):
            events = self.events.copy()
            self.events.clear()
            return events

        def update(self, dt):
            pass

        def add_event(self, x, y):
            event = InputEvent(
                Vector2D(x, y),
                time.time(),
                EventType.HIT
            )
            self.events.append(event)

    # Test the adapter
    mock_source = MockInputSource()
    adapter = InputSourceAdapter(mock_source, 1920, 1080)

    # Simulate a click at (960, 540) - center of screen
    mock_source.add_event(960, 540)

    # Poll through adapter
    events = adapter.poll_events()

    print(f"Adapter test:")
    print(f"  Backend info: {adapter.get_backend_info()}")
    print(f"  Events: {len(events)}")

    if events:
        event = events[0]
        print(f"  Position: ({event.x:.3f}, {event.y:.3f}) [normalized]")
        print(f"  Expected: (0.500, 0.500) [screen center]")
        print(f"  Method: {event.detection_method}")
        print(f"  Metadata: {event.metadata}")

    # Test calibration
    result = adapter.calibrate()
    print(f"\nCalibration:")
    print(f"  Success: {result.success}")
    print(f"  Method: {result.method}")
    print(f"  Notes: {result.notes}")
