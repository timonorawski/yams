#!/usr/bin/env python3
"""
Duck Hunt with AMS Integration

Run Duck Hunt game with the Arcade Management System, supporting:
- Mouse input (for development)
- Laser pointer detection (for projection setup)

Usage:
    python duckhunt_ams.py                    # Mouse mode (default)
    python duckhunt_ams.py --backend mouse    # Mouse mode
    python duckhunt_ams.py --backend laser    # Laser pointer mode
    python duckhunt_ams.py --backend laser --fullscreen --display 1 --mode classic_archery

Controls:
    Mouse Mode:
        - Click to shoot
        - ESC to quit

    Laser Mode:
        - Point laser at targets
        - Press 'D' to toggle debug view
        - Press 'B' to toggle B/W threshold view
        - Press '+/-' to adjust brightness threshold
        - Press 'C' to recalibrate
        - Press 'ESC' to quit
"""

import pygame
import sys
import os
import argparse

# Add DuckHunt to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Games', 'DuckHunt'))

from ams.session import AMSSession
from ams.detection_backend import InputSourceAdapter
from input.sources.mouse import MouseInputSource


def main():
    """Run Duck Hunt with AMS integration."""

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Duck Hunt with AMS - Multiple Detection Backends')
    parser.add_argument(
        '--backend',
        choices=['mouse', 'laser'],
        default='mouse',
        help='Detection backend to use (default: mouse)'
    )
    parser.add_argument(
        '--mode',
        type=str,
        default='classic_archery',
        help='Game mode YAML file (without .yaml extension)'
    )
    parser.add_argument(
        '--camera-id',
        type=int,
        default=0,
        help='Camera ID for laser backend (default: 0)'
    )
    parser.add_argument(
        '--brightness',
        type=int,
        default=200,
        help='Brightness threshold for laser detection (default: 200)'
    )
    parser.add_argument(
        '--fullscreen',
        action='store_true',
        help='Run in fullscreen mode'
    )
    parser.add_argument(
        '--display',
        type=int,
        default=0,
        help='Display index for fullscreen (0=primary, 1=secondary, etc.)'
    )
    parser.add_argument(
        '--resolution',
        type=str,
        default=None,
        help='Resolution as WIDTHxHEIGHT (e.g., 1920x1080). Auto-detected in fullscreen.'
    )
    args = parser.parse_args()

    # Initialize pygame
    pygame.init()

    # Display settings
    if args.fullscreen:
        # Get available displays
        displays = pygame.display.get_desktop_sizes()
        print(f"\nAvailable displays: {len(displays)}")
        for i, size in enumerate(displays):
            print(f"  Display {i}: {size[0]}x{size[1]}")

        # Select display
        if args.display >= len(displays):
            print(f"\nWARNING: Display {args.display} not found, using display 0")
            display_index = 0
        else:
            display_index = args.display

        DISPLAY_WIDTH, DISPLAY_HEIGHT = displays[display_index]
        print(f"\nUsing display {display_index}: {DISPLAY_WIDTH}x{DISPLAY_HEIGHT}")

        # Create fullscreen on selected display
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{sum(d[0] for d in displays[:display_index])},0"
        screen = pygame.display.set_mode(
            (DISPLAY_WIDTH, DISPLAY_HEIGHT),
            pygame.FULLSCREEN
        )
        print("Fullscreen mode enabled")
    else:
        # Windowed mode
        if args.resolution:
            try:
                width, height = args.resolution.split('x')
                DISPLAY_WIDTH = int(width)
                DISPLAY_HEIGHT = int(height)
            except:
                print(f"Invalid resolution format: {args.resolution}, using default")
                DISPLAY_WIDTH = 1280
                DISPLAY_HEIGHT = 720
        else:
            DISPLAY_WIDTH = 1280
            DISPLAY_HEIGHT = 720

        screen = pygame.display.set_mode((DISPLAY_WIDTH, DISPLAY_HEIGHT))
        print(f"Windowed mode: {DISPLAY_WIDTH}x{DISPLAY_HEIGHT}")

    pygame.display.set_caption(f"Duck Hunt - AMS ({args.backend.upper()} mode)")
    clock = pygame.time.Clock()

    print("="*60)
    print("Duck Hunt with AMS (Arcade Management System)")
    print("="*60)
    print(f"\nBackend Mode: {args.backend.upper()}")
    print(f"Game Mode: {args.mode}")
    print("\nInitializing...")

    # Create detection backend
    print("\n1. Creating detection backend...")

    if args.backend == 'mouse':
        print("   Using: MouseInputSource → InputSourceAdapter")
        mouse_input = MouseInputSource()
        detection_backend = InputSourceAdapter(
            mouse_input,
            DISPLAY_WIDTH,
            DISPLAY_HEIGHT
        )
    elif args.backend == 'laser':
        print("   Using: Camera → LaserDetectionBackend")
        print(f"   Camera ID: {args.camera_id}")
        print(f"   Brightness threshold: {args.brightness}")

        try:
            from ams.camera import OpenCVCamera
            from ams.laser_detection_backend import LaserDetectionBackend
            from calibration.calibration_manager import CalibrationManager
            from models import CalibrationConfig

            camera = OpenCVCamera(camera_id=args.camera_id)

            # Try to load existing calibration
            calibration_manager = None
            calib_path = "calibration.json"
            if os.path.exists(calib_path):
                try:
                    calibration_manager = CalibrationManager(CalibrationConfig())
                    calibration_manager.load_calibration(calib_path)
                    print(f"   ✓ Loaded calibration from {calib_path}")
                    quality = calibration_manager.get_calibration_quality()
                    print(f"   Calibration quality: RMS error {quality.reprojection_error_rms:.2f}px")
                except Exception as e:
                    print(f"   Warning: Could not load calibration: {e}")
                    calibration_manager = None
            else:
                print(f"   No calibration found. Press 'C' to calibrate.")

            detection_backend = LaserDetectionBackend(
                camera=camera,
                calibration_manager=calibration_manager,
                display_width=DISPLAY_WIDTH,
                display_height=DISPLAY_HEIGHT,
                brightness_threshold=args.brightness
            )
            detection_backend.set_debug_mode(True)

            print("\n   NOTE: Laser mode requires a camera and laser pointer!")
            print("   Controls:")
            print("     - Point laser pointer at targets")
            print("     - Press 'D' to toggle debug visualization")
            print("     - Press 'B' to toggle B/W threshold view")
            print("     - Press '+' or '-' to adjust brightness threshold")

        except Exception as e:
            print(f"\n   ERROR: Failed to initialize laser backend: {e}")
            print("   Falling back to mouse backend...")
            mouse_input = MouseInputSource()
            detection_backend = InputSourceAdapter(
                mouse_input,
                DISPLAY_WIDTH,
                DISPLAY_HEIGHT
            )

    print(f"   Backend: {detection_backend.get_backend_info()}")

    # Create AMS session
    print("\n2. Creating AMS session...")
    ams = AMSSession(
        backend=detection_backend,
        session_name="duckhunt_session"
    )

    # Run calibration
    print("\n3. Running calibration...")

    def calibration_progress(phase, progress, message):
        """Callback for calibration progress."""
        bar = "█" * int(progress * 20)
        print(f"   [{bar:<20}] {progress:3.0%} - {message}")

    calibration_result = ams.calibrate(
        progress_callback=calibration_progress,
        display_surface=screen,
        display_resolution=(DISPLAY_WIDTH, DISPLAY_HEIGHT)
    )

    print(f"\n   Calibration complete!")
    print(f"   Success: {calibration_result.success}")
    print(f"   Method: {calibration_result.method}")

    # Initialize Duck Hunt game
    print("\n4. Initializing Duck Hunt...")
    from game.modes.classic import ClassicMode
    from game.mode_loader import load_game_mode_config

    # Load game mode configuration
    mode_path = os.path.join('Games', 'DuckHunt', 'modes', f'{args.mode}.yaml')
    if not os.path.exists(mode_path):
        print(f"   ERROR: Mode file not found: {mode_path}")
        print(f"   Available modes: classic_archery, classic_ducks, classic_linear")
        return 1

    mode_config = load_game_mode_config(mode_path)
    print(f"   Mode: {mode_config.metadata.name}")
    print(f"   Description: {mode_config.metadata.description}")

    # Create game instance
    game_mode = ClassicMode(DISPLAY_WIDTH, DISPLAY_HEIGHT, mode_config)
    print(f"   Game initialized")

    # Game loop
    print("\n5. Starting game loop...")
    print("\nControls:")
    if args.backend == 'mouse':
        print("  - Click to shoot")
    else:
        print("  - Point laser at targets to shoot")
        print("  - Press 'D' to toggle debug visualization")
        print("  - Press 'B' to toggle B/W threshold view")
        print("  - Press '+' or '-' to adjust brightness threshold")
        print("  - Press 'C' to recalibrate")
    print("  - Press 'ESC' to quit")
    print("\n" + "="*60)

    running = True

    while running:
        dt = clock.tick(60) / 1000.0  # 60 FPS

        # Update AMS (polls detection backend)
        ams.update(dt)

        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_c and args.backend == 'laser':
                    # Recalibrate
                    print("\nRecalibrating...")
                    ams.calibrate(
                        display_surface=screen,
                        display_resolution=(DISPLAY_WIDTH, DISPLAY_HEIGHT)
                    )
                    print("Calibration complete!")
                elif event.key == pygame.K_d and args.backend == 'laser':
                    detection_backend.set_debug_mode(not detection_backend.debug_mode)
                elif event.key == pygame.K_b and args.backend == 'laser':
                    detection_backend.toggle_bw_mode()
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    if args.backend == 'laser':
                        detection_backend.set_brightness_threshold(
                            detection_backend.brightness_threshold + 10
                        )
                elif event.key == pygame.K_MINUS:
                    if args.backend == 'laser':
                        detection_backend.set_brightness_threshold(
                            detection_backend.brightness_threshold - 10
                        )

        # Get detection events from AMS
        events = ams.poll_events()

        # Convert AMS events to game input events
        from models import EventType
        for ams_event in events:
            # Create game input event from AMS event
            # Note: Game expects pixel coordinates, not normalized
            pixel_x = int(ams_event.x * DISPLAY_WIDTH)
            pixel_y = int(ams_event.y * DISPLAY_HEIGHT)

            # Duck Hunt's input system will handle hit detection
            # For now, just inject the click event
            pygame.event.post(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {'pos': (pixel_x, pixel_y), 'button': 1}
            ))

        # Update game
        game_mode.update(dt)

        # Render game
        screen.fill((135, 206, 235))  # Sky blue background
        game_mode.render(screen)

        pygame.display.flip()

        # Show laser debug visualization if enabled
        if args.backend == 'laser' and detection_backend.debug_mode:
            debug_frame = detection_backend.get_debug_frame()
            if debug_frame is not None:
                import cv2
                cv2.imshow("Laser Detection Debug", debug_frame)
                cv2.waitKey(1)

        # Check if game is over
        from models import GameState
        if game_mode.state == GameState.GAME_OVER:
            print("\n" + "="*60)
            print("GAME OVER!")
            print("="*60)
            # Could show final score, restart, etc.
            running = False

    # Cleanup
    print("\n" + "="*60)
    print("Session Complete")
    print("="*60)

    summary = ams.get_session_summary()
    print(f"\nSession Summary:")
    print(f"  Name: {summary['session_name']}")
    print(f"  Backend: {summary['backend']}")
    print(f"  Total events: {summary['total_events']}")

    # Save session
    ams.save_session()
    print(f"\nSession saved to: ./ams_sessions/{ams.session_name}.json")

    # Cleanup
    if args.backend == 'laser':
        import cv2
        cv2.destroyAllWindows()
        detection_backend.camera.release()

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
