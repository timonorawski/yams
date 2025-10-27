"""
Camera Interface for AMS

Provides abstract camera interface and OpenCV implementation for CV detection.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional
import numpy as np
import cv2


class CameraInterface(ABC):
    """Abstract camera interface for CV detection."""

    @abstractmethod
    def capture_frame(self) -> np.ndarray:
        """
        Capture a single frame from camera.

        Returns:
            BGR image (numpy array)
        """
        pass

    @abstractmethod
    def get_resolution(self) -> Tuple[int, int]:
        """
        Get camera resolution.

        Returns:
            (width, height) of camera
        """
        pass

    @abstractmethod
    def release(self):
        """Release camera resources."""
        pass


class OpenCVCamera(CameraInterface):
    """OpenCV-based camera implementation."""

    def __init__(
        self,
        camera_id: int = 0,
        resolution: Optional[Tuple[int, int]] = None,
        fps: int = 60
    ):
        """
        Initialize camera.

        Args:
            camera_id: OpenCV camera index (0 = default)
            resolution: Optional (width, height) to set
            fps: Target frame rate
        """
        self.camera_id = camera_id
        self.camera = cv2.VideoCapture(camera_id)

        if not self.camera.isOpened():
            raise RuntimeError(f"Could not open camera {camera_id}")

        # Set resolution if specified
        if resolution:
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        # Set high FPS for motion tracking
        self.camera.set(cv2.CAP_PROP_FPS, fps)

        # Warm up camera (first few frames can be dark)
        for _ in range(5):
            self.camera.read()

    def capture_frame(self) -> np.ndarray:
        """Capture frame from camera."""
        ret, frame = self.camera.read()
        if not ret:
            raise RuntimeError("Failed to capture frame")
        return frame

    def get_resolution(self) -> Tuple[int, int]:
        """Get actual camera resolution."""
        width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (width, height)

    def release(self):
        """Release camera."""
        if self.camera.isOpened():
            self.camera.release()

    def __del__(self):
        """Ensure camera is released on deletion."""
        self.release()


if __name__ == "__main__":
    # Test camera capture
    print("Testing OpenCV camera...")

    try:
        camera = OpenCVCamera(camera_id=0)
        print(f"Camera opened successfully")
        print(f"Resolution: {camera.get_resolution()}")

        # Capture and display a few frames
        print("\nCapturing frames (press 'q' to quit)...")
        for i in range(100):
            frame = camera.capture_frame()
            cv2.imshow("Camera Test", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        camera.release()
        cv2.destroyAllWindows()
        print("\nCamera test complete!")

    except Exception as e:
        print(f"Error: {e}")
