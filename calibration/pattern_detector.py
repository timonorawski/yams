"""
ArUco calibration pattern detector.

Detects ArUco markers in camera frames and extracts their positions.
"""

import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
from models import MarkerDetection, Point2D


class ArucoPatternDetector:
    """Detect ArUco markers in camera images."""

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
        Initialize marker detector.

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
        self.parameters = cv2.aruco.DetectorParameters()

        # Tune parameters for better detection
        self.parameters.adaptiveThreshWinSizeMin = 3
        self.parameters.adaptiveThreshWinSizeMax = 23
        self.parameters.adaptiveThreshWinSizeStep = 10
        self.parameters.minMarkerPerimeterRate = 0.03
        self.parameters.maxMarkerPerimeterRate = 4.0
        self.parameters.polygonalApproxAccuracyRate = 0.05
        self.parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX

    def detect_markers(
        self,
        camera_frame: np.ndarray,
        expected_ids: Optional[List[int]] = None
    ) -> Tuple[List[MarkerDetection], bool]:
        """
        Detect ArUco markers in camera image.

        Args:
            camera_frame: numpy array from camera (BGR or grayscale)
            expected_ids: Optional list of marker IDs we expect to see

        Returns:
            Tuple of:
            - detections: list of MarkerDetection objects
            - success: bool indicating if minimum markers detected
        """
        # Convert to grayscale if needed
        if len(camera_frame.shape) == 3:
            gray = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = camera_frame

        # Detect markers
        corners, ids, rejected = cv2.aruco.detectMarkers(
            gray,
            self.aruco_dict,
            parameters=self.parameters
        )

        detections = []

        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                # Get corners for this marker (4 corners in clockwise order)
                marker_corners = corners[i][0]  # Shape: (4, 2)

                # Convert corners to Point2D
                corner_points = [
                    Point2D(x=float(corner[0]), y=float(corner[1]))
                    for corner in marker_corners
                ]

                # Calculate center
                center_x = np.mean([c.x for c in corner_points])
                center_y = np.mean([c.y for c in corner_points])
                center = Point2D(x=center_x, y=center_y)

                detection = MarkerDetection(
                    marker_id=int(marker_id),
                    corners=corner_points,
                    center=center
                )
                detections.append(detection)

        # Check success
        if expected_ids is not None:
            detected_ids = {d.marker_id for d in detections}
            success = len(detected_ids.intersection(expected_ids)) >= len(expected_ids) * 0.75
        else:
            success = len(detections) > 0

        return detections, success

    def draw_detected_markers(
        self,
        image: np.ndarray,
        detections: List[MarkerDetection]
    ) -> np.ndarray:
        """
        Draw detected markers on image for visualization.

        Args:
            image: Image to draw on
            detections: List of detected markers

        Returns:
            Image with markers drawn
        """
        result = image.copy()

        for detection in detections:
            # Draw marker outline
            corners_array = np.array([
                [c.x, c.y] for c in detection.corners
            ], dtype=np.int32)

            cv2.polylines(
                result,
                [corners_array],
                True,
                (0, 255, 0),  # Green
                2
            )

            # Draw center point
            center_int = (int(detection.center.x), int(detection.center.y))
            cv2.circle(result, center_int, 4, (0, 0, 255), -1)  # Red

            # Draw marker ID
            cv2.putText(
                result,
                str(detection.marker_id),
                (center_int[0] - 10, center_int[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 0, 0),  # Blue
                2
            )

        return result

    def create_point_correspondences(
        self,
        detections: List[MarkerDetection],
        known_positions: Dict[int, Point2D]
    ) -> Tuple[List[Point2D], List[Point2D]]:
        """
        Create point correspondences between detected markers and known positions.

        Args:
            detections: List of detected markers in camera space
            known_positions: Dict mapping marker_id -> position in projector space

        Returns:
            Tuple of (camera_points, projector_points) with matching pairs
        """
        camera_points = []
        projector_points = []

        for detection in detections:
            if detection.marker_id in known_positions:
                camera_points.append(detection.center)
                projector_points.append(known_positions[detection.marker_id])

        return camera_points, projector_points


if __name__ == "__main__":
    # Example usage
    detector = ArucoPatternDetector("DICT_4X4_50")

    # Try to open camera
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("No camera available. Please test with actual hardware.")
        exit()

    print("Press 'q' to quit, 's' to save frame with detections")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detect markers
        detections, success = detector.detect_markers(frame)

        # Draw detections
        result = detector.draw_detected_markers(frame, detections)

        # Display info
        info_text = f"Detected: {len(detections)} markers"
        cv2.putText(
            result,
            info_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.imshow("Marker Detection", result)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite("detected_markers.png", result)
            print(f"Saved frame with {len(detections)} markers")

    cap.release()
    cv2.destroyAllWindows()
