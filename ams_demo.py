#!/usr/bin/env python3
"""
AMS Integration Demo

Demonstrates the complete Arcade Management System architecture:

1. Detection Backend (Mouse input or Laser pointer CV detection)
2. AMS Session (calibration, event routing, session management)
3. Game with Temporal State (handles latency via historical queries)

This shows how all pieces work together and validates the architecture.

Usage:
    python ams_demo.py                    # Use mouse input (default)
    python ams_demo.py --backend mouse    # Use mouse input
    python ams_demo.py --backend laser    # Use laser pointer detection

Controls:
    - Click on targets to shoot them (mouse mode)
    - Point laser at targets (laser mode)
    - Press 'Q' or 'ESC' to quit
    - Press 'C' to recalibrate
    - Press 'R' to start new round
    - Press 'D' to toggle debug view (laser mode)
    - Press '+'/'-' to adjust brightness threshold (laser mode)
    - Press 'F' to toggle fullscreen (if supported)

Architecture:
    Mouse Mode:  Mouse → InputSource → InputSourceAdapter → AMS → Game
    Laser Mode:  Camera → LaserDetectionBackend → AMS → Game
"""

import pygame
import sys
import os
import time
import argparse

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Games', 'DuckHunt'))

from ams.session import AMSSession
from ams.detection_backend import InputSourceAdapter
from games.base.simple_targets import SimpleTargetGame

# Import existing DuckHunt mouse input
from input.sources.mouse import MouseInputSource


def main():
    """Run AMS demo."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='AMS Demo - Multiple Detection Backends')
    parser.add_argument(
        '--backend',
        choices=['mouse', 'laser'],
        default='mouse',
        help='Detection backend to use (default: mouse)'
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
    parser.add_argument(
        '--bw-palette',
        action='store_true',
        help='Use black and white palette only (better contrast on some displays)'
    )
    parser.add_argument(
        '--debug-only',
        action='store_true',
        help='Show targets only in debug window, not on game screen (blank projection for laser detection)'
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
        # Note: pygame needs SDL_VIDEO_WINDOW_POS to position on specific display
        import os
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{sum(d[0] for d in displays[:display_index])},0"

        screen = pygame.display.set_mode(
            (DISPLAY_WIDTH, DISPLAY_HEIGHT),
            pygame.FULLSCREEN
        )
        print("Fullscreen mode enabled")
    else:
        # Windowed mode
        if args.resolution:
            # Parse custom resolution
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

    pygame.display.set_caption(f"AMS Demo - Simple Targets ({args.backend.upper()} mode)")
    clock = pygame.time.Clock()

    print("="*60)
    print("AMS (Arcade Management System) Demo")
    print("="*60)
    print(f"\nBackend Mode: {args.backend.upper()}")
    print("\nInitializing...")

    # Step 1: Create detection backend based on argument
    print("\n1. Creating detection backend...")

    if args.backend == 'mouse':
        # Mouse input backend (existing)
        print("   Using: MouseInputSource (from DuckHunt) → InputSourceAdapter")

        mouse_input = MouseInputSource()
        detection_backend = InputSourceAdapter(
            mouse_input,
            DISPLAY_WIDTH,
            DISPLAY_HEIGHT
        )

    elif args.backend == 'laser':
        # Laser pointer CV detection backend
        print("   Using: Camera → LaserDetectionBackend")
        print(f"   Camera ID: {args.camera_id}")
        print(f"   Brightness threshold: {args.brightness}")

        try:
            from ams.camera import OpenCVCamera
            from ams.laser_detection_backend import LaserDetectionBackend
            from calibration.calibration_manager import CalibrationManager
            from models import CalibrationConfig
            import os

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
            detection_backend.set_debug_mode(True)  # Enable debug visualization

            print("\n   NOTE: Laser mode requires a camera and laser pointer!")
            print("   Controls:")
            print("     - Point laser pointer at targets")
            print("     - Press 'D' to toggle debug visualization")
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

    # Step 2: Create AMS session
    print("\n2. Creating AMS session...")
    ams = AMSSession(
        backend=detection_backend,
        session_name="demo_session"
    )

    # Step 3: Run calibration
    print("\n3. Running calibration...")

    def calibration_progress(phase, progress, message):
        """Callback for calibration progress."""
        bar = "█" * int(progress * 20)
        print(f"   [{bar:<20}] {progress:3.0%} - {message}")

    # Pass display surface for ArUco calibration (laser backend)
    calibration_result = ams.calibrate(
        progress_callback=calibration_progress,
        display_surface=screen,
        display_resolution=(DISPLAY_WIDTH, DISPLAY_HEIGHT)
    )

    print(f"\n   Calibration complete!")
    print(f"   Success: {calibration_result.success}")
    print(f"   Method: {calibration_result.method}")
    print(f"   Available colors: {len(calibration_result.available_colors or [])}")

    # Step 4: Create game
    print("\n4. Creating game...")
    print("   Game: SimpleTargetGame (uses TemporalGameState)")

    # Override colors if black/white palette requested
    if args.bw_palette:
        available_colors = [
            (255, 255, 255),  # White
            (200, 200, 200),  # Light gray
        ]
        print("   Using black/white palette for better contrast")
    else:
        available_colors = ams.get_available_colors()

    game = SimpleTargetGame(
        DISPLAY_WIDTH,
        DISPLAY_HEIGHT,
        available_colors=available_colors
    )

    print(f"   Game initialized with {len(game.targets)} targets")

    # Step 5: Game loop
    print("\n5. Starting game loop...")
    print("\nControls:")
    if args.backend == 'mouse':
        print("  - Click on targets to shoot")
    else:
        print("  - Point laser at targets to shoot")
        print("  - Press 'D' to toggle debug visualization")
        print("  - Press 'B' to toggle B/W threshold view (for tuning)")
        print("  - Press '+' or '-' to adjust brightness threshold")
    print("  - Press 'F' to toggle fullscreen")
    print("  - Press 'C' to recalibrate")
    print("  - Press 'R' to start new round")
    print("  - Press 'Q' or 'ESC' to quit")
    if args.bw_palette:
        print("\n  * Using BLACK/WHITE palette for targets")
    print("\n" + "="*60)

    running = True
    round_number = 1
    last_hit_message = ""
    message_time = 0

    while running:
        dt = clock.tick(60) / 1000.0  # 60 FPS

        # Update target overlay for laser backend debug view
        if args.backend == 'laser' and detection_backend.debug_mode:
            # Extract target positions from game
            target_info = []
            for target in game.targets:
                if target.alive:
                    target_info.append((target.x, target.y, target.radius, target.color))
            detection_backend.set_game_targets(target_info)

        # Update AMS first (polls detection backend and processes mouse events)
        ams.update(dt)

        # Handle pygame events (for quit and keyboard)
        # Note: MouseInputSource re-posts non-mouse events, so we can still handle them here
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_f:
                    # Toggle fullscreen
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_c:
                    # Recalibrate
                    print("\nRecalibrating...")
                    ams.calibrate_between_rounds(
                        display_surface=screen,
                        display_resolution=(DISPLAY_WIDTH, DISPLAY_HEIGHT)
                    )
                    print("Calibration complete!")
                elif event.key == pygame.K_d:
                    # Toggle debug mode (laser backend only)
                    if args.backend == 'laser':
                        detection_backend.set_debug_mode(not detection_backend.debug_mode)
                elif event.key == pygame.K_b:
                    # Toggle B/W threshold view (laser backend only)
                    if args.backend == 'laser':
                        detection_backend.toggle_bw_mode()
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    # Increase brightness threshold (laser backend only)
                    if args.backend == 'laser':
                        detection_backend.set_brightness_threshold(
                            detection_backend.brightness_threshold + 10
                        )
                elif event.key == pygame.K_MINUS:
                    # Decrease brightness threshold (laser backend only)
                    if args.backend == 'laser':
                        detection_backend.set_brightness_threshold(
                            detection_backend.brightness_threshold - 10
                        )
                elif event.key == pygame.K_r:
                    # New round
                    print(f"\n--- Round {round_number} Complete ---")
                    print(f"Score: {game.score}")
                    print(f"Hits: {game.hits}/{game.hits + game.misses}")

                    ams.record_score(game.score, "simple_targets", {
                        'round': round_number,
                        'hits': game.hits,
                        'misses': game.misses
                    })

                    # Recalibrate between rounds
                    print("Calibrating for next round...")
                    ams.calibrate_between_rounds(
                        display_surface=screen,
                        display_resolution=(DISPLAY_WIDTH, DISPLAY_HEIGHT)
                    )

                    # Reset game (preserve B/W palette if set)
                    if args.bw_palette:
                        new_colors = [
                            (255, 255, 255),  # White
                            (200, 200, 200),  # Light gray
                        ]
                    else:
                        new_colors = ams.get_available_colors()

                    game = SimpleTargetGame(
                        DISPLAY_WIDTH,
                        DISPLAY_HEIGHT,
                        available_colors=new_colors
                    )

                    round_number += 1
                    print(f"--- Round {round_number} Start ---\n")

        # Get detection events from AMS
        events = ams.poll_events()

        # Handle events in game
        for event in events:
            result = game.handle_hit_event(event)

            # Show feedback
            if result.hit:
                last_hit_message = f"HIT! +{result.points} points"
            else:
                last_hit_message = "MISS!"
            message_time = time.time()

        # Update game logic
        game.update(dt)

        # Render game
        game.render(screen)

        # Draw feedback message
        if time.time() - message_time < 1.0:  # Show for 1 second
            font = pygame.font.Font(None, 48)
            text = font.render(last_hit_message, True, (255, 255, 0))
            text_rect = text.get_rect(center=(DISPLAY_WIDTH // 2, 50))
            screen.blit(text, text_rect)

        # Draw round number
        font_small = pygame.font.Font(None, 24)
        round_text = font_small.render(f"Round {round_number}", True, (200, 200, 200))
        screen.blit(round_text, (DISPLAY_WIDTH - 120, 10))

        # Draw controls hint
        if args.backend == 'mouse':
            hint_text = font_small.render("F=Fullscreen C=Calibrate R=New Round ESC=Quit", True, (150, 150, 150))
        else:  # laser
            hint_text = font_small.render("D=Debug B=B/W +/-=Brightness ESC=Quit", True, (150, 150, 150))
        screen.blit(hint_text, (10, DISPLAY_HEIGHT - 30))

        pygame.display.flip()

        # Show laser debug visualization in separate window (if enabled)
        if args.backend == 'laser' and detection_backend.debug_mode:
            debug_frame = detection_backend.get_debug_frame()
            if debug_frame is not None:
                import cv2
                cv2.imshow("Laser Detection Debug", debug_frame)
                cv2.waitKey(1)

    # Cleanup and show session summary
    print("\n" + "="*60)
    print("Session Complete")
    print("="*60)

    summary = ams.get_session_summary()
    print(f"\nSession Summary:")
    print(f"  Name: {summary['session_name']}")
    print(f"  Backend: {summary['backend']}")
    print(f"  Total events: {summary['total_events']}")
    print(f"  Rounds completed: {summary['rounds_completed']}")

    if summary['scores']:
        print(f"\n  Scores:")
        for score_entry in summary['scores']:
            print(f"    Round {score_entry['round']}: {score_entry['score']} points")

    # Save session
    ams.save_session()
    print(f"\nSession saved to: ./ams_sessions/{ams.session_name}.json")

    # Show game state history stats
    history_stats = game.get_history_stats()
    print(f"\nTemporal State Statistics:")
    print(f"  State snapshots: {history_stats['snapshots']}")
    print(f"  Time span: {history_stats['time_span']:.2f}s")
    print(f"  Frames span: {history_stats['frames_span']}")

    print("\n" + "="*60)
    print("Thank you for trying the AMS demo!")
    print("="*60)

    # Cleanup
    if args.backend == 'laser':
        import cv2
        cv2.destroyAllWindows()
        detection_backend.camera.release()

    pygame.quit()


if __name__ == "__main__":
    main()
