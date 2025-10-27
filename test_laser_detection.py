#!/usr/bin/env python3
"""
Laser Pointer Detection Validation Test

Standalone test for validating laser pointer detection backend.
Tests geometric accuracy, detection reliability, and coordinate mapping.

Usage:
    python test_laser_detection.py                  # Basic detection test
    python test_laser_detection.py --geometric      # Geometric accuracy test
    python test_laser_detection.py --brightness 180 # Adjust threshold
"""

import argparse
import time
import numpy as np
import cv2
from typing import List, Tuple

from ams.camera import OpenCVCamera
from ams.laser_detection_backend import LaserDetectionBackend


def basic_detection_test(brightness_threshold: int = 200):
    """
    Basic detection test - verify laser spots are detected.

    Tests:
    - Camera initialization
    - Spot detection
    - Event generation
    - Coordinate normalization
    """
    print("=" * 70)
    print("Basic Laser Detection Test")
    print("=" * 70)
    print("\nThis test validates basic laser spot detection.")
    print("\nInstructions:")
    print("  1. Point your laser pointer at the camera")
    print("  2. Move it around to test tracking")
    print("  3. Press 'q' to finish test")
    print("\nPress any key to start...")
    input()

    # Initialize
    camera = OpenCVCamera(camera_id=0)
    backend = LaserDetectionBackend(
        camera=camera,
        calibration_manager=None,
        display_width=1280,
        display_height=720,
        brightness_threshold=brightness_threshold
    )
    backend.set_debug_mode(True)

    print("\nDetection running... (press 'q' to quit)")

    detection_count = 0
    positions: List[Tuple[float, float]] = []

    try:
        while True:
            # Update detection
            backend.update(0.016)

            # Check for events
            events = backend.poll_events()
            for event in events:
                detection_count += 1
                positions.append((event.x, event.y))

                print(f"\n✓ Detection #{detection_count}:")
                print(f"  Position: ({event.x:.4f}, {event.y:.4f})")
                print(f"  Camera: ({event.metadata['camera_position']['x']:.1f}, "
                      f"{event.metadata['camera_position']['y']:.1f})")
                print(f"  Brightness: {event.metadata['brightness']}/255")
                print(f"  Spot area: {event.metadata['spot_area']} pixels")

            # Show debug visualization
            debug_frame = backend.get_debug_frame()
            if debug_frame is not None:
                cv2.imshow("Laser Detection Test", debug_frame)

            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()

    # Results
    print("\n" + "=" * 70)
    print("Test Results")
    print("=" * 70)
    print(f"Total detections: {detection_count}")

    if detection_count > 0:
        print("\n✓ PASS: Laser detection working!")

        # Compute statistics
        positions_array = np.array(positions)
        mean_x = np.mean(positions_array[:, 0])
        mean_y = np.mean(positions_array[:, 1])
        std_x = np.std(positions_array[:, 0])
        std_y = np.std(positions_array[:, 1])

        print(f"\nDetection Statistics:")
        print(f"  Mean position: ({mean_x:.4f}, {mean_y:.4f})")
        print(f"  Std deviation: ({std_x:.4f}, {std_y:.4f})")

        if std_x < 0.05 and std_y < 0.05:
            print("  ✓ Low jitter - stable detection")
        else:
            print("  ⚠ High jitter - consider adjusting brightness threshold")

        return True
    else:
        print("\n✗ FAIL: No detections recorded!")
        print("\nTroubleshooting:")
        print("  - Ensure laser pointer is bright enough")
        print("  - Try adjusting --brightness threshold (default: 200)")
        print("  - Check camera is working (see debug window)")
        print("  - Ensure room is not too bright (laser must stand out)")
        return False


def geometric_accuracy_test():
    """
    Geometric accuracy test - test coordinate mapping precision.

    Tests:
    - Corner detection accuracy
    - Edge linearity
    - Coordinate mapping consistency
    """
    print("=" * 70)
    print("Geometric Accuracy Test")
    print("=" * 70)
    print("\nThis test measures coordinate mapping accuracy.")
    print("\nInstructions:")
    print("  1. We'll ask you to point the laser at 5 positions:")
    print("     - Top-left corner")
    print("     - Top-right corner")
    print("     - Bottom-right corner")
    print("     - Bottom-left corner")
    print("     - Center")
    print("  2. Point laser at each position and press ENTER")
    print("  3. Keep laser steady for each measurement")
    print("\nPress any key to start...")
    input()

    # Initialize
    camera = OpenCVCamera(camera_id=0)
    backend = LaserDetectionBackend(
        camera=camera,
        calibration_manager=None,
        display_width=1280,
        display_height=720
    )
    backend.set_debug_mode(True)

    # Expected positions (normalized)
    test_points = [
        ("Top-Left Corner", (0.0, 0.0)),
        ("Top-Right Corner", (1.0, 0.0)),
        ("Bottom-Right Corner", (1.0, 1.0)),
        ("Bottom-Left Corner", (0.0, 1.0)),
        ("Center", (0.5, 0.5))
    ]

    detected_positions = []

    for label, expected in test_points:
        print(f"\n{'='*70}")
        print(f"Point laser at: {label}")
        print(f"Expected position: ({expected[0]:.1f}, {expected[1]:.1f})")
        input("Press ENTER when ready...")

        # Collect samples
        samples = []
        start_time = time.time()

        while len(samples) < 10 and time.time() - start_time < 5.0:
            backend.update(0.016)
            events = backend.poll_events()

            for event in events:
                samples.append((event.x, event.y))
                print(f"  Sample {len(samples)}: ({event.x:.4f}, {event.y:.4f})")

            # Show debug
            debug_frame = backend.get_debug_frame()
            if debug_frame is not None:
                cv2.imshow("Geometric Test", debug_frame)
            cv2.waitKey(1)

        if not samples:
            print("  ✗ No detection! Skipping this point.")
            detected_positions.append(None)
            continue

        # Compute mean position
        samples_array = np.array(samples)
        mean_pos = (np.mean(samples_array[:, 0]), np.mean(samples_array[:, 1]))
        detected_positions.append(mean_pos)

        print(f"  Detected: ({mean_pos[0]:.4f}, {mean_pos[1]:.4f})")

    camera.release()
    cv2.destroyAllWindows()

    # Analyze results
    print("\n" + "=" * 70)
    print("Geometric Accuracy Results")
    print("=" * 70)

    errors = []
    for i, (label, expected) in enumerate(test_points):
        detected = detected_positions[i]

        if detected is None:
            print(f"\n{label}: SKIPPED (no detection)")
            continue

        # Compute error
        dx = detected[0] - expected[0]
        dy = detected[1] - expected[1]
        error = np.sqrt(dx*dx + dy*dy)
        errors.append(error)

        print(f"\n{label}:")
        print(f"  Expected:  ({expected[0]:.4f}, {expected[1]:.4f})")
        print(f"  Detected:  ({detected[0]:.4f}, {detected[1]:.4f})")
        print(f"  Error:     {error:.4f} (normalized)")
        print(f"  Error:     {error * 1280:.1f} pixels (at 1280px width)")

    if errors:
        rms_error = np.sqrt(np.mean(np.array(errors)**2))
        print(f"\n{'='*70}")
        print(f"RMS Error: {rms_error:.4f} (normalized)")
        print(f"RMS Error: {rms_error * 1280:.1f} pixels")

        if rms_error < 0.05:
            print("\n✓ EXCELLENT: Error < 5% of screen")
        elif rms_error < 0.10:
            print("\n✓ GOOD: Error < 10% of screen")
        else:
            print("\n⚠ POOR: Error > 10% of screen")
            print("  Consider adding geometric calibration (ArUco markers)")

        return rms_error < 0.10
    else:
        print("\n✗ FAIL: No valid measurements")
        return False


def main():
    parser = argparse.ArgumentParser(description='Laser Detection Validation Tests')
    parser.add_argument(
        '--test',
        choices=['basic', 'geometric', 'all'],
        default='basic',
        help='Which test to run (default: basic)'
    )
    parser.add_argument(
        '--brightness',
        type=int,
        default=200,
        help='Brightness threshold (default: 200)'
    )
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("LASER POINTER DETECTION VALIDATION")
    print("=" * 70)
    print("\nPrerequisites:")
    print("  ✓ Camera connected and working")
    print("  ✓ Laser pointer available")
    print("  ✓ Room lighting controlled (not too bright)")
    print("=" * 70)

    results = {}

    try:
        if args.test in ['basic', 'all']:
            results['basic'] = basic_detection_test(args.brightness)

        if args.test in ['geometric', 'all']:
            print("\n\n")
            results['geometric'] = geometric_accuracy_test()

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return

    except Exception as e:
        print(f"\n\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return

    # Final summary
    print("\n\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name.upper()}: {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\n✓ All tests passed! Laser backend is ready for use.")
        print("\nNext steps:")
        print("  1. Test with the full game: python ams_demo.py --backend laser")
        print("  2. Adjust brightness threshold if needed: --brightness <value>")
        print("  3. Consider adding geometric calibration for better accuracy")
    else:
        print("\n⚠ Some tests failed. Review output above for details.")

    print("=" * 70)


if __name__ == "__main__":
    main()
