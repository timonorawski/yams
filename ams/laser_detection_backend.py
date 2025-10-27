"""
Laser Pointer Detection Backend for AMS

A simplified CV detection backend for testing and development.
Detects bright laser spots - much simpler than full projectile tracking.

Advantages over full CV detection:
- 10x simpler implementation (brightness threshold vs motion tracking)
- Instant feedback (no object retrieval needed)
- Precise validation of coordinate mapping
- Lower latency (~50ms vs ~150ms)
- Safer for indoor development

Use this backend to:
- Validate geometric calibration accuracy
- Test temporal query system with real input
- Rapid game development iteration
- Debug coordinate transformations
- Demos without thrown objects
"""

from typing import List, Optional, Tuple
import time
import numpy as np
import cv2

from ams.detection_backend import DetectionBackend
from ams.events import PlaneHitEvent, CalibrationResult
from ams.camera import CameraInterface

# Try to import calibration manager - may not be available in all setups
try:
    from calibration.calibration_manager import CalibrationManager
    from models import Point2D
    CALIBRATION_AVAILABLE = True
except ImportError:
    CALIBRATION_AVAILABLE = False
    # Fallback for basic testing without full calibration system
    class Point2D:
        def __init__(self, x: float, y: float):
            self.x = x
            self.y = y


class LaserDetectionBackend(DetectionBackend):
    """
    Laser pointer detection backend for testing and development.

    Detects bright spots in camera frame and transforms to game coordinates.
    Much simpler than full CV detection - validates the pipeline without complexity.
    """

    def __init__(
        self,
        camera: CameraInterface,
        calibration_manager: Optional['CalibrationManager'],
        display_width: int,
        display_height: int,
        brightness_threshold: int = 200
    ):
        """
        Initialize laser detection backend.

        Args:
            camera: Camera interface for frame capture
            calibration_manager: Geometric calibration manager (optional)
            display_width: Display width in pixels
            display_height: Display height in pixels
            brightness_threshold: Minimum brightness for laser detection (0-255)
        """
        super().__init__(display_width, display_height)

        self.camera = camera
        self.calibration_manager = calibration_manager
        self.detection_latency_ms = 50.0  # Much lower than CV (~150ms)

        # Detection parameters
        self.brightness_threshold = brightness_threshold
        self.min_spot_size = 5           # Minimum pixels
        self.max_spot_size = 100         # Maximum pixels
        self.blur_size = 5               # Gaussian blur for noise reduction

        # Event queue
        self._event_queue: List[PlaneHitEvent] = []

        # Debouncing: Track last position to prevent spam
        self._last_position: Optional[Point2D] = None
        self._last_detection_time: float = 0
        self._min_detection_interval: float = 0.1  # 100ms minimum between events

        # Debug mode
        self.debug_mode = False
        self.debug_bw_mode = False  # Black/white threshold view
        self.debug_frame: Optional[np.ndarray] = None
        self.debug_targets: List[Tuple[float, float, float, tuple]] = []  # (x, y, radius, color) in normalized coords

        print(f"LaserDetectionBackend initialized")
        print(f"  Camera resolution: {camera.get_resolution()}")
        print(f"  Brightness threshold: {brightness_threshold}")
        print(f"  Latency: {self.detection_latency_ms}ms")

    def update(self, dt: float):
        """
        Update detection (called every frame).

        Detects bright laser spot in camera frame.
        Much simpler than projectile detection - no motion tracking needed.
        """
        # Capture camera frame
        frame = self.camera.capture_frame()
        timestamp = time.monotonic()

        # Convert to grayscale for brightness analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        gray = cv2.GaussianBlur(gray, (self.blur_size, self.blur_size), 0)

        # Threshold for very bright spots (laser pointer)
        # Laser pointers are typically 200-255 brightness
        _, bright_spots = cv2.threshold(
            gray,
            self.brightness_threshold,
            255,
            cv2.THRESH_BINARY
        )

        # Morphological operations to clean noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        bright_spots = cv2.morphologyEx(bright_spots, cv2.MORPH_OPEN, kernel)

        # Find contours (bright blobs)
        contours, _ = cv2.findContours(
            bright_spots,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Debug visualization - create frame FIRST
        if self.debug_mode:
            if self.debug_bw_mode:
                # Show black/white threshold view (easier to tune)
                debug_frame = cv2.cvtColor(bright_spots, cv2.COLOR_GRAY2BGR)
            else:
                # Show normal camera view with contours
                debug_frame = frame.copy()
                cv2.drawContours(debug_frame, contours, -1, (0, 255, 0), 2)

            # ALWAYS draw target overlay when debug is enabled
            self._draw_target_overlay(debug_frame)

        if not contours:
            self._last_position = None
            if self.debug_mode:
                self.debug_frame = debug_frame
            return  # No laser detected

        # Find largest bright spot (assume it's the laser)
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)

        # Validate spot size (filter out noise and reflections)
        if not (self.min_spot_size < area < self.max_spot_size):
            if self.debug_mode:
                # Add text showing why detection failed
                cv2.putText(
                    debug_frame,
                    f"Spot too {'large' if area >= self.max_spot_size else 'small'}: {int(area)} pixels",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 255),
                    2
                )
                self.debug_frame = debug_frame
            return

        # Get centroid
        M = cv2.moments(largest)
        if M["m00"] == 0:
            if self.debug_mode:
                cv2.putText(
                    debug_frame,
                    f"Invalid moment (M00 = 0)",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 255),
                    2
                )
                self.debug_frame = debug_frame
            return

        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        camera_pos = Point2D(x=cx, y=cy)

        # Debug: Draw detected spot
        if self.debug_mode:
            if not self.debug_bw_mode:
                # Only draw on color view, not BW view
                cv2.circle(debug_frame, (int(cx), int(cy)), 5, (0, 0, 255), -1)

            # Add text overlay
            cv2.putText(
                debug_frame,
                f"Laser ({int(cx)}, {int(cy)}) Area: {int(area)} Bright: {int(gray[int(cy), int(cx)])}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
            cv2.putText(
                debug_frame,
                f"Threshold: {self.brightness_threshold} | Mode: {'B/W' if self.debug_bw_mode else 'COLOR'}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 0),
                2
            )

            # Target overlay already drawn earlier
            self.debug_frame = debug_frame

        # Debounce rapid detections (prevent spam)
        if self._last_position is not None:
            # Check if moved significantly
            dx = abs(camera_pos.x - self._last_position.x)
            dy = abs(camera_pos.y - self._last_position.y)

            # Also check time interval
            time_since_last = timestamp - self._last_detection_time

            # Skip if too close to last detection (both spatially and temporally)
            if dx < 5 and dy < 5 and time_since_last < self._min_detection_interval:
                return

        # Transform to game coordinates
        if self.calibration_manager and CALIBRATION_AVAILABLE:
            # Use calibration for accurate transformation
            try:
                game_pos = self.calibration_manager.camera_to_game(camera_pos)

                # Validate transformed coordinates (check for NaN, infinity, or out of bounds)
                import math
                if not (math.isfinite(game_pos.x) and math.isfinite(game_pos.y)):
                    # Invalid transformation result, skip this detection
                    return

                # Optionally clamp to valid game space [0, 1] to handle edge cases
                # (Allow slightly outside bounds for edge hits)
                if game_pos.x < -0.1 or game_pos.x > 1.1 or game_pos.y < -0.1 or game_pos.y > 1.1:
                    # Way outside game bounds, likely bad detection
                    return

            except Exception as e:
                # Transformation failed, skip this detection
                # print(f"Warning: Coordinate transformation failed: {e}")
                return
        else:
            # Fallback: Simple normalization (no calibration)
            cam_width, cam_height = self.camera.get_resolution()
            game_pos = Point2D(
                x=camera_pos.x / cam_width,
                y=camera_pos.y / cam_height
            )

        # Sample brightness at detection point
        brightness = int(gray[int(cy), int(cx)])

        # Create event
        event = PlaneHitEvent(
            x=game_pos.x,
            y=game_pos.y,
            timestamp=timestamp,
            confidence=0.99,  # Very high confidence for laser (unambiguous)
            detection_method="laser_pointer",
            latency_ms=self.detection_latency_ms,
            metadata={
                'camera_position': {'x': camera_pos.x, 'y': camera_pos.y},
                'spot_area': int(area),
                'brightness': brightness
            }
        )

        self._event_queue.append(event)
        self._last_position = camera_pos
        self._last_detection_time = timestamp

    def poll_events(self) -> List[PlaneHitEvent]:
        """Get all pending detection events."""
        events = self._event_queue.copy()
        self._event_queue.clear()
        return events

    def calibrate(self, display_surface=None, display_resolution=None) -> CalibrationResult:
        """
        Run geometric calibration using ArUco markers.

        Laser is self-illuminated (no color calibration needed), but does need
        geometric calibration to map camera coordinates to game coordinates.

        Args:
            display_surface: Pygame surface to display calibration pattern
            display_resolution: (width, height) of display

        Returns:
            CalibrationResult with success status
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
            if self.calibration_manager and CALIBRATION_AVAILABLE:
                self.calibration_manager.load_calibration(calib_path)
                print("Calibration manager updated")

            return CalibrationResult(
                success=True,
                method="aruco_geometric_calibration",
                available_colors=self._get_default_colors(),
                display_latency_ms=self.detection_latency_ms,
                quality=quality.quality_score if quality.quality_score is not None else 1.0,
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
            method="laser_pointer_no_geometric_calibration",
            available_colors=self._get_default_colors(),
            display_latency_ms=self.detection_latency_ms,
            quality=0.5,  # Reduced quality without calibration
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
            (0, 0, 0),      # Black
            (255, 255, 255) # White
        ]

    def set_brightness_threshold(self, threshold: int):
        """
        Adjust brightness threshold for different laser colors/powers.

        Args:
            threshold: Brightness threshold (0-255)
                - Green lasers: 180-200 (very bright)
                - Red lasers: 150-180 (dimmer)
                - Weak lasers: 120-150
                - Very weak/distant: 50-120
                - Extreme low light: 10-50
        """
        self.brightness_threshold = max(10, min(255, threshold))
        print(f"Brightness threshold updated to: {self.brightness_threshold}")

    def set_debug_mode(self, enabled: bool):
        """Enable/disable debug visualization."""
        self.debug_mode = enabled
        print(f"Debug mode: {'enabled' if enabled else 'disabled'}")

    def toggle_bw_mode(self):
        """Toggle black/white threshold view (helps with tuning)."""
        self.debug_bw_mode = not self.debug_bw_mode
        print(f"B/W threshold view: {'enabled' if self.debug_bw_mode else 'disabled'}")
        print(f"  (Shows exactly what's above brightness threshold)")

    def get_debug_frame(self) -> Optional[np.ndarray]:
        """Get the latest debug visualization frame."""
        return self.debug_frame

    def set_game_targets(self, targets: List[Tuple[float, float, float, tuple]]):
        """
        Update game target positions for debug overlay.

        Args:
            targets: List of (x, y, radius, color) tuples in normalized coordinates [0, 1]
        """
        self.debug_targets = targets

    def _draw_target_overlay(self, debug_frame: np.ndarray):
        """
        Draw game target positions on camera debug view.

        Shows where targets are in camera space, helping user aim laser.
        """
        if not self.debug_targets:
            return

        cam_width, cam_height = self.camera.get_resolution()

        for target_x, target_y, target_radius, target_color in self.debug_targets:
            # Convert normalized game coords to camera pixel coords
            if self.calibration_manager and CALIBRATION_AVAILABLE:
                try:
                    # Use calibration to transform game → camera
                    # Step 1: Game (normalized [0,1]) → Projector (pixels)
                    # Step 2: Projector → Camera (using inverse homography)
                    game_point = Point2D(x=target_x, y=target_y)

                    # Transform: game → projector → camera
                    proj_point = self.calibration_manager.game_to_projector(game_point)
                    cam_point = self.calibration_manager.projector_to_camera(proj_point)

                    cam_x = int(cam_point.x)
                    cam_y = int(cam_point.y)
                except Exception as e:
                    # Fallback to simple scaling if transformation fails
                    # print(f"Warning: Calibration transform failed: {e}, using simple scaling")
                    cam_x = int(target_x * cam_width)
                    cam_y = int(target_y * cam_height)
            else:
                # Simple scaling (no calibration)
                cam_x = int(target_x * cam_width)
                cam_y = int(target_y * cam_height)

            # Convert target radius (normalized relative to screen) to camera pixels
            # target_radius is relative to min(display_width, display_height)
            # Scale to camera space
            cam_radius = int(target_radius * min(cam_width, cam_height))

            # Draw target circle (semi-transparent overlay)
            overlay = debug_frame.copy()
            cv2.circle(overlay, (cam_x, cam_y), cam_radius, target_color, 2)
            # Draw center crosshair
            cv2.line(overlay, (cam_x - 5, cam_y), (cam_x + 5, cam_y), target_color, 2)
            cv2.line(overlay, (cam_x, cam_y - 5), (cam_x, cam_y + 5), target_color, 2)
            # Blend with original
            cv2.addWeighted(overlay, 0.7, debug_frame, 0.3, 0, debug_frame)

        # Add instruction text
        cv2.putText(
            debug_frame,
            f"Targets: {len(self.debug_targets)} (circles = game targets, aim laser here)",
            (10, cam_height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )


if __name__ == "__main__":
    # Standalone test for laser detection
    print("=" * 60)
    print("Laser Pointer Detection Test")
    print("=" * 60)
    print("\nThis will open your camera and detect bright laser spots.")
    print("\nControls:")
    print("  - Point a laser pointer at the camera")
    print("  - Press '+' to increase brightness threshold")
    print("  - Press '-' to decrease brightness threshold")
    print("  - Press 'd' to toggle debug visualization")
    print("  - Press 'q' to quit")
    print("=" * 60)

    try:
        from ams.camera import OpenCVCamera

        # Initialize camera
        camera = OpenCVCamera(camera_id=0)

        # Initialize laser backend (no calibration for standalone test)
        laser_backend = LaserDetectionBackend(
            camera=camera,
            calibration_manager=None,
            display_width=1280,
            display_height=720,
            brightness_threshold=200
        )

        laser_backend.set_debug_mode(True)

        print("\nStarting detection loop...")

        frame_count = 0
        event_count = 0

        while True:
            # Update detection
            laser_backend.update(0.016)  # ~60fps

            # Check for events
            events = laser_backend.poll_events()
            if events:
                for event in events:
                    event_count += 1
                    print(f"\nEvent #{event_count}:")
                    print(f"  Position: ({event.x:.3f}, {event.y:.3f}) [normalized]")
                    print(f"  Brightness: {event.metadata['brightness']}")
                    print(f"  Area: {event.metadata['spot_area']} pixels")
                    print(f"  Camera: ({event.metadata['camera_position']['x']:.1f}, "
                          f"{event.metadata['camera_position']['y']:.1f})")

            # Display debug frame
            debug_frame = laser_backend.get_debug_frame()
            if debug_frame is not None:
                # Add text overlay
                cv2.putText(
                    debug_frame,
                    f"Threshold: {laser_backend.brightness_threshold}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2
                )
                cv2.putText(
                    debug_frame,
                    f"Events: {event_count}",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2
                )

                cv2.imshow("Laser Detection", debug_frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('+') or key == ord('='):
                laser_backend.set_brightness_threshold(
                    laser_backend.brightness_threshold + 10
                )
            elif key == ord('-') or key == ord('_'):
                laser_backend.set_brightness_threshold(
                    laser_backend.brightness_threshold - 10
                )
            elif key == ord('d'):
                laser_backend.set_debug_mode(not laser_backend.debug_mode)

            frame_count += 1

        camera.release()
        cv2.destroyAllWindows()

        print("\n" + "=" * 60)
        print("Test Complete")
        print(f"  Frames processed: {frame_count}")
        print(f"  Laser events detected: {event_count}")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
