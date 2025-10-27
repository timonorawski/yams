#!/usr/bin/env python3
"""
Interactive calibration workflow.

Run this script to calibrate your projection system:
1. Displays calibration pattern via pygame (fullscreen on projector)
2. Captures camera frame
3. Detects markers and computes homography
4. Saves calibration data

Usage:
    python calibrate.py --projector-width 1920 --projector-height 1080
    python calibrate.py --camera-id 0 --projector-display 1
"""

import argparse
import cv2
import pygame
import numpy as np
import sys
from pathlib import Path

from models import Resolution, CalibrationConfig
from calibration.pattern_generator import ArucoPatternGenerator
from calibration.pattern_detector import ArucoPatternDetector
from calibration.calibration_manager import CalibrationManager


class CalibrationWorkflow:
    """Interactive calibration workflow."""

    def __init__(
        self,
        projector_resolution: Resolution,
        camera_id: int = 0,
        projector_display: int = 1,
        config: CalibrationConfig = None
    ):
        """
        Initialize calibration workflow.

        Args:
            projector_resolution: Projector resolution
            camera_id: Camera device ID
            projector_display: Which display to use for projector (0=primary, 1=secondary)
            config: Calibration configuration
        """
        self.projector_resolution = projector_resolution
        self.camera_id = camera_id
        self.projector_display = projector_display
        self.config = config or CalibrationConfig()

        self.camera = None
        self.pattern_generator = None
        self.manager = None
        self.calibration_pattern = None
        self.marker_positions = None

    def initialize(self):
        """Initialize camera and pattern generator."""
        print("Initializing calibration system...")

        # Initialize camera
        self.camera = cv2.VideoCapture(self.camera_id)
        if not self.camera.isOpened():
            raise RuntimeError(f"Failed to open camera {self.camera_id}")

        # Get camera resolution
        cam_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        cam_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.camera_resolution = Resolution(width=cam_width, height=cam_height)

        print(f"Camera resolution: {cam_width}x{cam_height}")
        print(f"Projector resolution: {self.projector_resolution.width}x{self.projector_resolution.height}")

        # Initialize pattern generator
        self.pattern_generator = ArucoPatternGenerator(self.config.aruco_dict)

        # Generate calibration pattern
        self.calibration_pattern, self.marker_positions = self.pattern_generator.generate_grid(
            self.projector_resolution,
            grid_size=self.config.grid_size,
            margin_percent=self.config.margin_percent
        )

        print(f"Generated {len(self.marker_positions)} markers in {self.config.grid_size[0]}x{self.config.grid_size[1]} grid")

        # Initialize calibration manager
        self.manager = CalibrationManager(self.config)

    def display_pattern(self):
        """Display calibration pattern using pygame (fullscreen on projector)."""
        print("\nDisplaying calibration pattern...")
        print("Position camera to see the entire pattern")
        print("Press SPACE when ready to capture, ESC to cancel")

        # Initialize pygame
        pygame.init()

        # Get display info
        displays = pygame.display.get_num_displays()
        print(f"Found {displays} display(s)")

        if self.projector_display >= displays:
            print(f"Warning: Display {self.projector_display} not found, using display 0")
            self.projector_display = 0

        # Create fullscreen window on specified display
        # Note: pygame display selection can be tricky on some systems
        # You may need to manually move the window to the correct display
        screen = pygame.display.set_mode(
            (self.projector_resolution.width, self.projector_resolution.height),
            pygame.FULLSCREEN,
            display=self.projector_display
        )
        pygame.display.set_caption("Calibration Pattern")

        # Convert pattern from OpenCV (BGR) to pygame (RGB)
        pattern_rgb = cv2.cvtColor(self.calibration_pattern, cv2.COLOR_BGR2RGB)
        pattern_surface = pygame.surfarray.make_surface(
            np.transpose(pattern_rgb, (1, 0, 2))
        )

        # Display pattern
        screen.blit(pattern_surface, (0, 0))
        pygame.display.flip()

        # Wait for user input
        camera_frame = None
        running = True

        while running:
            # Show camera preview in separate window
            ret, frame = self.camera.read()
            if ret:
                # Show detector preview
                detector = ArucoPatternDetector(self.config.aruco_dict)
                detections, _ = detector.detect_markers(frame)
                preview = detector.draw_detected_markers(frame, detections)

                # Add instructions
                cv2.putText(
                    preview,
                    f"Detected: {len(detections)}/{len(self.marker_positions)} markers",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0) if len(detections) >= self.config.min_markers_required else (0, 0, 255),
                    2
                )
                cv2.putText(
                    preview,
                    "SPACE=Capture  ESC=Cancel",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    1
                )

                cv2.imshow("Camera Preview", preview)

            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        # Capture frame
                        ret, camera_frame = self.camera.read()
                        if ret:
                            print("Frame captured!")
                            running = False

            # Also check OpenCV window
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                running = False
            elif key == 32:  # SPACE
                ret, camera_frame = self.camera.read()
                if ret:
                    print("Frame captured!")
                    running = False

        # Cleanup
        pygame.quit()
        cv2.destroyAllWindows()

        return camera_frame

    def run_calibration(self, camera_frame: np.ndarray):
        """
        Run calibration from captured frame.

        Args:
            camera_frame: Captured camera frame with visible markers

        Returns:
            CalibrationData if successful
        """
        print("\nRunning calibration...")

        try:
            calibration_data = self.manager.calibrate_from_detections(
                camera_frame,
                self.projector_resolution,
                self.camera_resolution,
                self.marker_positions
            )

            print("\n" + "="*60)
            print("CALIBRATION SUCCESSFUL!")
            print("="*60)
            print(f"Quality Metrics:")
            print(f"  RMS Error: {calibration_data.quality.reprojection_error_rms:.2f} pixels")
            print(f"  Max Error: {calibration_data.quality.reprojection_error_max:.2f} pixels")
            print(f"  Inlier Ratio: {calibration_data.quality.inlier_ratio:.1%}")
            print(f"  Acceptable: {calibration_data.quality.is_acceptable}")
            print("="*60)

            return calibration_data

        except RuntimeError as e:
            print(f"\nCALIBRATION FAILED: {e}")
            return None

    def cleanup(self):
        """Release resources."""
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()

    def run(self):
        """Run complete calibration workflow."""
        try:
            # Initialize
            self.initialize()

            # Display pattern and capture frame
            camera_frame = self.display_pattern()

            if camera_frame is None:
                print("Calibration cancelled")
                return False

            # Run calibration
            calibration_data = self.run_calibration(camera_frame)

            if calibration_data is None:
                return False

            # Save captured frame for reference
            calib_dir = Path(self.config.calibration_dir)
            calib_dir.mkdir(parents=True, exist_ok=True)
            timestamp_str = calibration_data.timestamp.strftime("%Y%m%d_%H%M%S")
            frame_path = calib_dir / f"calibration_frame_{timestamp_str}.png"
            cv2.imwrite(str(frame_path), camera_frame)
            print(f"Saved calibration frame to {frame_path}")

            return True

        finally:
            self.cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive calibration for projection targeting system"
    )
    parser.add_argument(
        "--projector-width",
        type=int,
        default=1920,
        help="Projector width in pixels (default: 1920)"
    )
    parser.add_argument(
        "--projector-height",
        type=int,
        default=1080,
        help="Projector height in pixels (default: 1080)"
    )
    parser.add_argument(
        "--camera-id",
        type=int,
        default=0,
        help="Camera device ID (default: 0)"
    )
    parser.add_argument(
        "--projector-display",
        type=int,
        default=1,
        help="Display index for projector (0=primary, 1=secondary, default: 1)"
    )
    parser.add_argument(
        "--grid-size",
        type=str,
        default="4x4",
        help="Calibration grid size, e.g., '4x4' (default: 4x4)"
    )

    args = parser.parse_args()

    # Parse grid size
    try:
        grid_cols, grid_rows = map(int, args.grid_size.split('x'))
        grid_size = (grid_cols, grid_rows)
    except ValueError:
        print(f"Invalid grid size: {args.grid_size}. Use format 'COLSxROWS', e.g., '4x4'")
        return 1

    # Create configuration
    config = CalibrationConfig(
        grid_size=grid_size,
        calibration_dir="./calibration_data"
    )

    # Create workflow
    projector_resolution = Resolution(
        width=args.projector_width,
        height=args.projector_height
    )

    workflow = CalibrationWorkflow(
        projector_resolution=projector_resolution,
        camera_id=args.camera_id,
        projector_display=args.projector_display,
        config=config
    )

    # Run calibration
    success = workflow.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
