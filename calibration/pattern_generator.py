"""
ArUco calibration pattern generator.

Generates grid patterns of ArUco markers for projection-based calibration.
Returns both the pattern image and ground truth marker positions.
"""

import cv2
import numpy as np
from typing import Dict, Tuple
from models import Point2D, Resolution


class ArucoPatternGenerator:
    """Generate ArUco marker grid patterns for calibration."""

    # Available ArUco dictionaries
    ARUCO_DICTS = {
        "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
        "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
        "DICT_4X4_250": cv2.aruco.DICT_4X4_250,
        "DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
        "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
        "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
        "DICT_5X5_250": cv2.aruco.DICT_5X5_250,
        "DICT_5X5_1000": cv2.aruco.DICT_5X5_1000,
        "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
        "DICT_6X6_100": cv2.aruco.DICT_6X6_100,
        "DICT_6X6_250": cv2.aruco.DICT_6X6_250,
        "DICT_6X6_1000": cv2.aruco.DICT_6X6_1000,
    }

    def __init__(self, aruco_dict_name: str = "DICT_4X4_50"):
        """
        Initialize pattern generator.

        Args:
            aruco_dict_name: Name of ArUco dictionary to use
        """
        if aruco_dict_name not in self.ARUCO_DICTS:
            raise ValueError(
                f"Unknown ArUco dictionary: {aruco_dict_name}. "
                f"Available: {list(self.ARUCO_DICTS.keys())}"
            )

        self.aruco_dict = cv2.aruco.getPredefinedDictionary(
            self.ARUCO_DICTS[aruco_dict_name]
        )

    def generate_grid(
        self,
        resolution: Resolution,
        grid_size: Tuple[int, int] = (4, 4),
        margin_percent: float = 0.1,
        marker_size_px: int = 150
    ) -> Tuple[np.ndarray, Dict[int, Point2D]]:
        """
        Generate ArUco marker grid pattern.

        Args:
            resolution: Target resolution (projector resolution)
            grid_size: (cols, rows) number of markers
            margin_percent: Border margin as fraction of frame (0.0 to 0.5)
            marker_size_px: Size of each marker in pixels

        Returns:
            Tuple of:
            - image: numpy array ready to display (white background, black markers)
            - marker_positions: dict mapping marker_id -> center position in projector coords
        """
        cols, rows = grid_size

        # Validate grid size
        max_markers = self.aruco_dict.bytesList.shape[0]
        if cols * rows > max_markers:
            raise ValueError(
                f"Grid size {cols}x{rows} requires {cols*rows} markers, "
                f"but dictionary only has {max_markers}"
            )

        # Create white background
        image = np.ones((resolution.height, resolution.width), dtype=np.uint8) * 255

        # Calculate usable area (excluding margins)
        margin_h = int(resolution.height * margin_percent)
        margin_w = int(resolution.width * margin_percent)

        usable_height = resolution.height - 2 * margin_h
        usable_width = resolution.width - 2 * margin_w

        # Calculate spacing between markers
        spacing_h = usable_height / rows
        spacing_w = usable_width / cols

        # Ensure marker fits within spacing
        max_marker_size = min(spacing_h, spacing_w) * 0.8  # 80% of cell size
        actual_marker_size = min(marker_size_px, int(max_marker_size))

        marker_positions = {}
        marker_id = 0

        # Generate grid of markers
        for row in range(rows):
            for col in range(cols):
                # Calculate center position for this marker
                center_x = margin_w + (col + 0.5) * spacing_w
                center_y = margin_h + (row + 0.5) * spacing_h

                # Store marker position (center in projector coords)
                marker_positions[marker_id] = Point2D(x=center_x, y=center_y)

                # Generate marker image
                marker_img = cv2.aruco.generateImageMarker(
                    self.aruco_dict,
                    marker_id,
                    actual_marker_size
                )

                # Calculate top-left corner for placement
                top_left_x = int(center_x - actual_marker_size / 2)
                top_left_y = int(center_y - actual_marker_size / 2)

                # Place marker on pattern
                try:
                    image[
                        top_left_y:top_left_y + actual_marker_size,
                        top_left_x:top_left_x + actual_marker_size
                    ] = marker_img
                except ValueError:
                    # Marker doesn't fit, skip it
                    print(f"Warning: Marker {marker_id} doesn't fit, skipping")
                    continue

                marker_id += 1

        # Convert to BGR for display (OpenCV uses BGR)
        image_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        return image_bgr, marker_positions

    def generate_test_pattern(
        self,
        resolution: Resolution,
        marker_size_px: int = 200
    ) -> Tuple[np.ndarray, Dict[int, Point2D]]:
        """
        Generate simple test pattern with markers at corners and center.

        Useful for quick calibration validation.

        Args:
            resolution: Target resolution
            marker_size_px: Size of each marker in pixels

        Returns:
            Tuple of (image, marker_positions)
        """
        # Create white background
        image = np.ones((resolution.height, resolution.width), dtype=np.uint8) * 255

        # Define positions: corners + center
        positions = [
            (0.15, 0.15),  # Top-left
            (0.85, 0.15),  # Top-right
            (0.85, 0.85),  # Bottom-right
            (0.15, 0.85),  # Bottom-left
            (0.5, 0.5),    # Center
        ]

        marker_positions = {}

        for marker_id, (x_frac, y_frac) in enumerate(positions):
            center_x = int(resolution.width * x_frac)
            center_y = int(resolution.height * y_frac)

            marker_positions[marker_id] = Point2D(x=center_x, y=center_y)

            # Generate marker
            marker_img = cv2.aruco.generateImageMarker(
                self.aruco_dict,
                marker_id,
                marker_size_px
            )

            # Place marker
            top_left_x = center_x - marker_size_px // 2
            top_left_y = center_y - marker_size_px // 2

            # Ensure marker fits within bounds
            if (0 <= top_left_x < resolution.width - marker_size_px and
                0 <= top_left_y < resolution.height - marker_size_px):
                image[
                    top_left_y:top_left_y + marker_size_px,
                    top_left_x:top_left_x + marker_size_px
                ] = marker_img

        # Convert to BGR
        image_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        return image_bgr, marker_positions


if __name__ == "__main__":
    # Example usage
    generator = ArucoPatternGenerator("DICT_4X4_50")
    resolution = Resolution(width=1920, height=1080)

    # Generate 4x4 grid
    pattern, positions = generator.generate_grid(
        resolution,
        grid_size=(4, 4),
        margin_percent=0.1
    )

    print(f"Generated pattern: {pattern.shape}")
    print(f"Marker positions: {len(positions)} markers")
    for marker_id, pos in positions.items():
        print(f"  Marker {marker_id}: ({pos.x:.1f}, {pos.y:.1f})")

    # Save pattern for testing
    cv2.imwrite("calibration_pattern.png", pattern)
    print("Saved pattern to calibration_pattern.png")

    # Display pattern (if display available)
    try:
        cv2.imshow("Calibration Pattern", pattern)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except:
        print("No display available, pattern saved to file")
