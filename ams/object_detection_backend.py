"""
Object Detection Backend for AMS.

Detects physical objects (nerf darts, arrows, balls) and registers impacts.
Uses pluggable object detectors and ArUco calibration.
"""

import cv2
import numpy as np
import math
import time
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from ams.detection_backend import DetectionBackend
from ams.camera import CameraInterface
from ams.events import PlaneHitEvent, CalibrationResult
from calibration.calibration_manager import CalibrationManager
from models import Point2D
from .object_detection import (
    ObjectDetector,
    DetectedObject,
    ImpactEvent,
    ColorBlobDetector,
    ColorBlobConfig,
    ImpactMode,
)


@dataclass
class TrackedObject:
    """Tracked object with history for impact detection."""
    object_id: int
    last_detection: DetectedObject
    stationary_since: Optional[float] = None  # When it became stationary
    velocity_history: List[Tuple[float, Point2D]] = None  # (timestamp, velocity)

    def __post_init__(self):
        if self.velocity_history is None:
            self.velocity_history = []


class ObjectDetectionBackend(DetectionBackend):
    """Detection backend using object detection and impact detection.

    Detects colored objects (nerf darts) and registers hits when they impact
    and come to rest at a location. Uses ArUco calibration for coordinate mapping.
    """

    def __init__(
        self,
        camera: CameraInterface,
        detector: Optional[ObjectDetector] = None,
        calibration_manager: Optional[CalibrationManager] = None,
        display_width: int = 1920,
        display_height: int = 1080,
        impact_mode: ImpactMode = ImpactMode.TRAJECTORY_CHANGE,
        impact_velocity_threshold: float = 10.0,
        impact_duration: float = 0.15,
        velocity_change_threshold: float = 100.0,
        direction_change_threshold: float = 90.0,
        min_impact_velocity: float = 50.0,
    ):
        """Initialize object detection backend.

        Args:
            camera: Camera instance for capturing frames
            detector: Object detector (defaults to ColorBlobDetector)
            calibration_manager: ArUco calibration manager (optional)
            display_width: Display width in pixels
            display_height: Display height in pixels
            impact_mode: Detection mode (TRAJECTORY_CHANGE for bouncing, STATIONARY for sticking)
            impact_velocity_threshold: Speed threshold (px/s) for stationary mode
            impact_duration: Duration (s) object must be stationary for stationary mode
            velocity_change_threshold: Velocity change magnitude (px/s) for trajectory_change mode
            direction_change_threshold: Direction change (degrees) for trajectory_change mode
            min_impact_velocity: Minimum speed before impact (px/s) for trajectory_change mode
        """
        self.camera = camera
        self.detector = detector or ColorBlobDetector()
        self.calibration_manager = calibration_manager
        self.display_width = display_width
        self.display_height = display_height

        # Impact detection mode and parameters
        self.impact_mode = impact_mode

        # Stationary mode parameters
        self.impact_velocity_threshold = impact_velocity_threshold
        self.impact_duration = impact_duration

        # Trajectory change mode parameters
        self.velocity_change_threshold = velocity_change_threshold
        self.direction_change_threshold = direction_change_threshold
        self.min_impact_velocity = min_impact_velocity

        # Tracking state
        self.tracked_objects: Dict[int, TrackedObject] = {}
        self.next_object_id = 0
        self.max_tracking_gap = 0.5  # seconds

        # Debug visualization
        self.debug_mode = False
        self.debug_frame: Optional[np.ndarray] = None
        self.game_targets: List[Tuple[float, float, float, Tuple[int, int, int]]] = []

    def poll_events(self) -> List[PlaneHitEvent]:
        """Get new detection events since last poll.

        Returns:
            List of hit events from detected impacts
        """
        return self.poll()

    def update(self, dt: float):
        """Update backend state (called each frame).

        For object detection, all processing happens in poll_events(),
        so this is a no-op.

        Args:
            dt: Delta time since last update
        """
        pass

    def poll(self) -> List[PlaneHitEvent]:
        """Poll for object impacts and return hit events.

        Returns:
            List of hit events from detected impacts
        """
        # Capture camera frame
        frame = self.camera.capture_frame()
        if frame is None:
            return []

        timestamp = time.time()

        # Detect objects in frame
        detections = self.detector.detect(frame, timestamp)

        # Update tracking and detect impacts
        impacts = self._update_tracking(detections, timestamp)

        # Convert impacts to hit events
        events = []
        for impact in impacts:
            # Transform coordinates to game space
            game_pos = self._camera_to_game(impact.position)

            if game_pos is not None:
                # Validate coordinates
                if self._is_valid_coordinate(game_pos):
                    event = PlaneHitEvent(
                        x=game_pos.x,
                        y=game_pos.y,
                        timestamp=impact.timestamp
                    )
                    events.append(event)

        # Create debug visualization if enabled
        if self.debug_mode:
            self._create_debug_visualization(frame, detections, impacts)

        return events

    def _update_tracking(
        self,
        detections: List[DetectedObject],
        timestamp: float
    ) -> List[ImpactEvent]:
        """Update object tracking and detect impacts.

        Args:
            detections: Current frame detections
            timestamp: Current timestamp

        Returns:
            List of detected impact events
        """
        impacts = []

        # Match detections to tracked objects
        matched_detections = set()
        current_tracks: Dict[int, TrackedObject] = {}

        for track_id, tracked in self.tracked_objects.items():
            # Find closest matching detection
            closest_det = None
            min_dist = float('inf')

            for i, det in enumerate(detections):
                if i in matched_detections:
                    continue

                dx = det.position.x - tracked.last_detection.position.x
                dy = det.position.y - tracked.last_detection.position.y
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < min_dist and dist < 100:  # 100px max matching distance
                    min_dist = dist
                    closest_det = (i, det)

            if closest_det is not None:
                det_idx, det = closest_det
                matched_detections.add(det_idx)

                # Calculate current speed
                speed = math.sqrt(det.velocity.x ** 2 + det.velocity.y ** 2)

                # Get previous velocity for trajectory change detection
                prev_velocity = tracked.last_detection.velocity
                prev_speed = math.sqrt(prev_velocity.x ** 2 + prev_velocity.y ** 2)

                # Impact detection based on mode
                impact_detected = False

                if self.impact_mode == ImpactMode.TRAJECTORY_CHANGE:
                    # Trajectory change mode - detect bounces
                    # Calculate velocity change magnitude
                    velocity_change_mag = math.sqrt(
                        (det.velocity.x - prev_velocity.x) ** 2 +
                        (det.velocity.y - prev_velocity.y) ** 2
                    )

                    # Calculate direction change
                    direction_change = self._calculate_direction_change(prev_velocity, det.velocity)

                    # Check if this looks like an impact (bounce)
                    # Requirements:
                    # 1. Object was moving fast enough before impact
                    # 2. Significant velocity change OR direction change
                    if prev_speed >= self.min_impact_velocity:
                        if (velocity_change_mag >= self.velocity_change_threshold or
                            direction_change >= self.direction_change_threshold):
                            # Detected bounce/impact!
                            impact_detected = True
                            impact = ImpactEvent(
                                position=tracked.last_detection.position,  # Use position before bounce
                                velocity_before=prev_velocity,
                                timestamp=timestamp,
                                stationary_duration=0.0  # N/A for trajectory change mode
                            )
                            impacts.append(impact)

                            # Continue tracking (object bounces off, doesn't stop)

                elif self.impact_mode == ImpactMode.STATIONARY:
                    # Stationary mode - detect when object stops and stays
                    is_stationary = speed < self.impact_velocity_threshold

                    if is_stationary:
                        # Object is stationary
                        if tracked.stationary_since is None:
                            # Just became stationary
                            tracked.stationary_since = timestamp
                        else:
                            # Check if stationary long enough for impact
                            stationary_duration = timestamp - tracked.stationary_since

                            if stationary_duration >= self.impact_duration:
                                # Register impact!
                                impact_detected = True
                                impact = ImpactEvent(
                                    position=det.position,
                                    velocity_before=tracked.last_detection.velocity,
                                    timestamp=timestamp,
                                    stationary_duration=stationary_duration
                                )
                                impacts.append(impact)

                                # Stop tracking this object (impact registered)
                                continue
                    else:
                        # Object is moving, reset stationary timer
                        tracked.stationary_since = None

                # Update tracked object
                tracked.last_detection = det
                tracked.velocity_history.append((timestamp, det.velocity))

                # Keep only recent velocity history
                tracked.velocity_history = [
                    (t, v) for t, v in tracked.velocity_history
                    if timestamp - t < 1.0
                ]

                current_tracks[track_id] = tracked

        # Add new tracks for unmatched detections
        for i, det in enumerate(detections):
            if i not in matched_detections:
                new_track = TrackedObject(
                    object_id=self.next_object_id,
                    last_detection=det,
                    velocity_history=[(timestamp, det.velocity)]
                )
                current_tracks[self.next_object_id] = new_track
                self.next_object_id += 1

        # Update tracking state
        self.tracked_objects = current_tracks

        return impacts

    def _calculate_direction_change(self, v1: Point2D, v2: Point2D) -> float:
        """Calculate angle change between two velocity vectors.

        Args:
            v1: Previous velocity vector
            v2: Current velocity vector

        Returns:
            Angle change in degrees (0-180)
        """
        # Calculate magnitudes
        mag1 = math.sqrt(v1.x ** 2 + v1.y ** 2)
        mag2 = math.sqrt(v2.x ** 2 + v2.y ** 2)

        # Avoid division by zero
        if mag1 < 1.0 or mag2 < 1.0:
            return 0.0

        # Calculate dot product
        dot = v1.x * v2.x + v1.y * v2.y

        # Calculate cosine of angle
        cos_angle = dot / (mag1 * mag2)

        # Clamp to valid range for acos
        cos_angle = max(-1.0, min(1.0, cos_angle))

        # Calculate angle in radians, then convert to degrees
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)

        return angle_deg

    def _camera_to_game(self, camera_pos: Point2D) -> Optional[Point2D]:
        """Transform camera coordinates to normalized game coordinates.

        Args:
            camera_pos: Position in camera pixel coordinates

        Returns:
            Position in normalized [0,1] game coordinates, or None if invalid
        """
        if self.calibration_manager is None:
            # No calibration - use simple scaling
            game_x = camera_pos.x / self.camera.get_resolution()[0]
            game_y = camera_pos.y / self.camera.get_resolution()[1]
            return Point2D(x=game_x, y=game_y)

        try:
            # Use calibration manager for accurate transformation
            return self.calibration_manager.camera_to_game(camera_pos)
        except Exception:
            return None

    def _is_valid_coordinate(self, pos: Point2D) -> bool:
        """Check if coordinate is valid (no NaN, infinity, within game bounds).

        Args:
            pos: Position to validate

        Returns:
            True if valid (within [0, 1] range), False otherwise
        """
        if not (math.isfinite(pos.x) and math.isfinite(pos.y)):
            return False

        # Strictly enforce [0, 1] bounds for game coordinates
        if not (0.0 <= pos.x <= 1.0 and 0.0 <= pos.y <= 1.0):
            return False

        return True

    def _create_debug_visualization(
        self,
        frame: np.ndarray,
        detections: List[DetectedObject],
        impacts: List[ImpactEvent]
    ) -> None:
        """Create debug visualization overlay.

        Args:
            frame: Camera frame
            detections: Detected objects
            impacts: Detected impacts
        """
        # Get detector's debug frame
        detector_frame = self.detector.get_debug_frame()

        if detector_frame is not None:
            debug = detector_frame.copy()
        else:
            debug = frame.copy()

        # Draw tracked objects
        for tracked in self.tracked_objects.values():
            det = tracked.last_detection
            x, y = int(det.position.x), int(det.position.y)

            # Color based on state
            if tracked.stationary_since is not None:
                color = (0, 165, 255)  # Orange - stationary
            else:
                color = (255, 255, 0)  # Cyan - moving

            cv2.circle(debug, (x, y), 8, color, 2)
            cv2.putText(debug, f"ID:{tracked.object_id}", (x + 10, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Draw impacts
        for impact in impacts:
            x, y = int(impact.position.x), int(impact.position.y)
            cv2.circle(debug, (x, y), 15, (0, 0, 255), 3)  # Red circle
            cv2.putText(debug, "IMPACT!", (x - 30, y - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Draw game targets overlay (if calibrated)
        if self.calibration_manager is not None and self.game_targets:
            cam_height, cam_width = frame.shape[:2]

            for target_x, target_y, radius, color in self.game_targets:
                try:
                    # Transform game coords to camera coords
                    game_point = Point2D(x=target_x, y=target_y)
                    proj_point = self.calibration_manager.game_to_projector(game_point)
                    cam_point = self.calibration_manager.projector_to_camera(proj_point)

                    cam_x = int(cam_point.x)
                    cam_y = int(cam_point.y)

                    # Draw target overlay
                    cv2.circle(debug, (cam_x, cam_y), int(radius * 50), (255, 255, 255), 2)
                except Exception:
                    pass  # Skip if transformation fails

        self.debug_frame = debug

    def calibrate(self, display_surface=None, display_resolution=None, **kwargs) -> CalibrationResult:
        """Run ArUco calibration for geometric mapping.

        Args:
            display_surface: Pygame surface to display calibration pattern
            display_resolution: (width, height) of display
            **kwargs: Additional calibration parameters

        Returns:
            Calibration result
        """
        # Import calibration dependencies
        try:
            import pygame
            from datetime import datetime
            from models import (
                CalibrationConfig,
                Resolution,
                CalibrationData,
                HomographyMatrix,
            )
            from calibration.pattern_generator import ArucoPatternGenerator
            from calibration.pattern_detector import ArucoPatternDetector
            from calibration.homography import compute_homography
        except ImportError as e:
            print(f"Calibration dependencies not available: {e}")
            import traceback
            traceback.print_exc()
            return self._return_no_calibration()

        if display_surface is None or display_resolution is None:
            print("No display surface provided, skipping geometric calibration")
            return self._return_no_calibration()

        print("\n" + "="*60)
        print("ArUco Geometric Calibration")
        print("="*60)
        print("\nInstructions:")
        print("1. ArUco marker pattern will be displayed")
        print("2. Position camera to see entire pattern")
        print("3. Press SPACE to capture and calibrate")
        print("4. Press ESC to skip calibration")
        print("\nStarting in 3 seconds...")

        import time
        time.sleep(3)

        # Initialize
        config = CalibrationConfig()
        pattern_generator = ArucoPatternGenerator(config.aruco_dict)

        # Generate pattern
        proj_resolution = Resolution(width=display_resolution[0], height=display_resolution[1])
        calibration_pattern, marker_positions = pattern_generator.generate_grid(
            proj_resolution,
            grid_size=config.grid_size,
            margin_percent=config.margin_percent
        )

        # Convert to pygame surface
        pattern_rgb = cv2.cvtColor(calibration_pattern, cv2.COLOR_BGR2RGB)
        pattern_surface = pygame.surfarray.make_surface(pattern_rgb.swapaxes(0, 1))

        # Display pattern and wait for capture
        captured = False
        camera_frame = None

        print("\nLIVE CAMERA PREVIEW:")
        print("  - Position camera to see entire pattern")
        print("  - Wait for marker count to reach 12+ (shown in preview window)")
        print("  - Press SPACE when markers are detected")
        print("  - Press ESC to skip calibration")

        # Import detector for live preview
        detector = ArucoPatternDetector(config.aruco_dict)

        clock = pygame.time.Clock()
        while not captured:
            # Display pattern on projector/display
            display_surface.blit(pattern_surface, (0, 0))

            # Add instruction text on projector
            font = pygame.font.Font(None, 36)
            text = font.render("SPACE=Capture  ESC=Skip", True, (0, 255, 0))
            display_surface.blit(text, (20, 20))

            pygame.display.flip()

            # Show live camera preview with marker detection
            frame = self.camera.capture_frame()
            detected_markers, _ = detector.detect_markers(frame)

            # Draw detected markers on preview
            preview = frame.copy()
            for marker in detected_markers:
                # Draw marker corners
                corners = [(int(c.x), int(c.y)) for c in marker.corners]
                cv2.polylines(preview, [np.array(corners)], True, (0, 255, 0), 2)
                # Draw marker ID
                center = (int(marker.center.x), int(marker.center.y))
                cv2.putText(preview, str(marker.marker_id), center,
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Add marker count with color coding
            count = len(detected_markers)
            total = len(marker_positions)
            color = (0, 255, 0) if count >= config.min_markers_required else (0, 0, 255)
            cv2.putText(preview, f"Detected: {count}/{total} markers", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            # Add instructions
            status = "READY" if count >= config.min_markers_required else "ADJUST CAMERA"
            cv2.putText(preview, f"Status: {status}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(preview, "SPACE=Capture  ESC=Skip", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            cv2.imshow("ArUco Calibration - Camera Preview", preview)

            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        # Capture current frame (already in 'frame' variable)
                        camera_frame = frame
                        captured = True
                        print(f"Frame captured! Detected {count} markers")
                    elif event.key == pygame.K_ESCAPE:
                        print("Calibration skipped")
                        cv2.destroyAllWindows()
                        return self._return_no_calibration()

            # Also handle CV window events
            key = cv2.waitKey(1) & 0xFF
            if key == 32:  # SPACE
                camera_frame = frame
                captured = True
                print(f"Frame captured! Detected {count} markers")
            elif key == 27:  # ESC
                print("Calibration skipped")
                cv2.destroyAllWindows()
                return self._return_no_calibration()

            clock.tick(30)

        cv2.destroyAllWindows()

        # Safety check
        if camera_frame is None:
            print("ERROR: No frame captured")
            return self._return_no_calibration()

        # Detect markers in captured frame (detector already created above)
        detected_markers, _ = detector.detect_markers(camera_frame)

        if len(detected_markers) < 4:
            print(f"ERROR: Only {len(detected_markers)} markers detected, need at least 4")
            return self._return_no_calibration()

        print(f"Detected {len(detected_markers)} markers")

        # Create point correspondences (match detected markers with known positions)
        camera_points, projector_points = detector.create_point_correspondences(
            detected_markers,
            marker_positions
        )

        print(f"Matched {len(camera_points)} point pairs for homography computation")

        if len(camera_points) < 4:
            print(f"ERROR: Need at least 4 matched pairs, got {len(camera_points)}")
            return self._return_no_calibration()

        # Compute homography
        try:
            homography, inlier_mask, quality = compute_homography(camera_points, projector_points)

            print(f"Homography computed successfully!")
            print(f"  RMS error: {quality.reprojection_error_rms:.2f}px")
            print(f"  Max error: {quality.reprojection_error_max:.2f}px")
            print(f"  Inliers: {quality.num_inliers}/{quality.num_total_points}")
            print(f"  Quality: {'GOOD' if quality.is_acceptable else 'POOR'}")

            # Create calibration data
            cam_width, cam_height = self.camera.get_resolution()
            calibration_data = CalibrationData(
                camera_resolution=Resolution(width=cam_width, height=cam_height),
                projector_resolution=proj_resolution,
                homography_camera_to_projector=homography,
                quality=quality,
                calibration_time=datetime.now(),
                marker_count=len(detected_markers)
            )

            # Save calibration
            calib_path = "calibration.json"
            calibration_data.save(calib_path)
            print(f"Calibration saved to {calib_path}")

            # Update calibration manager if available
            if self.calibration_manager:
                self.calibration_manager.load_calibration(calib_path)
                print("Calibration manager updated")

            return CalibrationResult(
                success=True,
                method="aruco_geometric_calibration",
                available_colors=self._get_default_colors(),
                display_latency_ms=0.0,
                detection_quality=quality.quality_score if quality.quality_score is not None else 1.0,
                notes=f"ArUco calibration: {len(detected_markers)} markers, {quality.reprojection_error_rms:.2f}px RMS error"
            )

        except Exception as e:
            print(f"ERROR during calibration: {e}")
            import traceback
            traceback.print_exc()
            return self._return_no_calibration()

    def _return_no_calibration(self):
        """Return calibration result without geometric calibration."""
        return CalibrationResult(
            success=True,
            method="object_detection_no_geometric_calibration",
            available_colors=self._get_default_colors(),
            display_latency_ms=0.0,
            detection_quality=0.5,  # Reduced quality without calibration
            notes="No geometric calibration performed - using simple coordinate normalization"
        )

    def _get_default_colors(self):
        """Get default color palette."""
        return [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (255, 128, 0),  # Orange
            (128, 0, 255),  # Purple
            (0, 255, 128),  # Spring Green
            (255, 255, 255) # White
        ]

    def get_backend_info(self) -> dict:
        """Get backend information.

        Returns:
            Dictionary with backend details
        """
        return {
            'backend_type': 'ObjectDetectionBackend',
            'detector': type(self.detector).__name__,
            'calibrated': self.calibration_manager is not None,
            'display_resolution': f'{self.display_width}x{self.display_height}',
            'impact_threshold': f'{self.impact_velocity_threshold}px/s',
            'impact_duration': f'{self.impact_duration}s',
        }

    def set_debug_mode(self, enabled: bool) -> None:
        """Enable/disable debug visualization.

        Args:
            enabled: Whether to show debug overlay
        """
        self.debug_mode = enabled
        self.detector.set_debug_mode(enabled)

    def get_debug_frame(self) -> Optional[np.ndarray]:
        """Get debug visualization frame.

        Returns:
            Debug frame with overlays, or None
        """
        return self.debug_frame

    def set_game_targets(
        self,
        targets: List[Tuple[float, float, float, Tuple[int, int, int]]]
    ) -> None:
        """Set game targets for debug overlay.

        Args:
            targets: List of (x, y, radius, color) tuples in normalized coords
        """
        self.game_targets = targets

    def configure_detector(self, **kwargs) -> None:
        """Update detector configuration dynamically.

        Args:
            **kwargs: Detector-specific parameters
        """
        self.detector.configure(**kwargs)
