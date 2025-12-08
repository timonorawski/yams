#!/usr/bin/env python3
"""
AMS Game Launcher - Unified entry point for all AMS games

Games are auto-discovered from the games/ directory. Any game with a
game_info.py file will be automatically available.

Supports multiple detection backends:
- mouse: Development/testing (no hardware needed)
- laser: Laser pointer detection
- object: Object/projectile detection

Usage:
    # List available games
    python ams_game.py --list-games

    # Play a game with mouse
    python ams_game.py --game balloonpop --backend mouse

    # Play with laser pointer
    python ams_game.py --game duckhunt --backend laser --fullscreen --display 1
"""

import pygame
import sys
import os
import time
import argparse

# Add DuckHunt to path for imports (needed for some shared modules)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'games', 'DuckHunt'))

from ams.session import AMSSession
from ams.detection_backend import InputSourceAdapter
from games.registry import get_registry, GameRegistry
from input.sources.mouse import MouseInputSource


def create_detection_backend(args, DISPLAY_WIDTH, DISPLAY_HEIGHT):
    """Create detection backend based on command-line arguments.

    Args:
        args: Parsed command-line arguments
        DISPLAY_WIDTH: Display width in pixels
        DISPLAY_HEIGHT: Display height in pixels

    Returns:
        Configured detection backend instance
    """
    print("\n1. Creating detection backend...")

    if args.backend == 'mouse':
        # Mouse input backend
        print("   Using: MouseInputSource → InputSourceAdapter")

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

    elif args.backend == 'object':
        # Object detection backend (nerf darts, arrows, etc.)
        print("   Using: Camera → ObjectDetectionBackend → ColorBlobDetector")
        print(f"   Camera ID: {args.camera_id}")

        try:
            from ams.camera import OpenCVCamera
            from ams.object_detection_backend import ObjectDetectionBackend
            from ams.object_detection import ColorBlobDetector, ColorBlobConfig, ImpactMode
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

            # Create color blob detector for nerf darts
            blob_config = ColorBlobConfig(
                hue_min=0,
                hue_max=15,
                saturation_min=100,
                saturation_max=255,
                value_min=100,
                value_max=255,
                min_area=50,
                max_area=2000,
            )
            detector = ColorBlobDetector(blob_config)

            detection_backend = ObjectDetectionBackend(
                camera=camera,
                detector=detector,
                calibration_manager=calibration_manager,
                display_width=DISPLAY_WIDTH,
                display_height=DISPLAY_HEIGHT,
                impact_mode=ImpactMode.TRAJECTORY_CHANGE,  # Bouncing objects
                velocity_change_threshold=100.0,
                direction_change_threshold=90.0,
                min_impact_velocity=50.0,
            )
            detection_backend.set_debug_mode(True)

            print("\n   NOTE: Object detection mode for nerf darts/balls (bouncing objects)!")
            print("   Impact mode: TRAJECTORY_CHANGE (detects bounces)")
            print("   Controls:")
            print("     - Shoot colored object at targets")
            print("     - Press 'D' to toggle debug visualization")

        except Exception as e:
            print(f"\n   ERROR: Failed to initialize object detection backend: {e}")
            import traceback
            traceback.print_exc()
            print("   Falling back to mouse backend...")
            mouse_input = MouseInputSource()
            detection_backend = InputSourceAdapter(
                mouse_input,
                DISPLAY_WIDTH,
                DISPLAY_HEIGHT
            )

    print(f"   Backend: {detection_backend.get_backend_info()}")
    return detection_backend


def launch_simple_targets(args, screen, detection_backend, ams):
    """Launch Simple Targets game.

    Args:
        args: Command-line arguments
        screen: Pygame display surface
        detection_backend: Configured detection backend
        ams: AMS session instance

    Returns:
        Exit code (0 for success)
    """
    from games.base.simple_targets import SimpleTargetGame

    DISPLAY_WIDTH, DISPLAY_HEIGHT = screen.get_size()

    print("\n4. Creating Simple Targets game...")

    # Override colors if black/white palette requested
    if hasattr(args, 'bw_palette') and args.bw_palette:
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

    # Game loop
    print("\n5. Starting game loop...")
    print("\nControls:")
    if args.backend == 'mouse':
        print("  - Click on targets to shoot")
    elif args.backend == 'laser':
        print("  - Point laser at targets to shoot")
        print("  - Press 'D' to toggle debug visualization")
        print("  - Press 'B' to toggle B/W threshold view")
        print("  - Press '+' or '-' to adjust brightness threshold")
    else:  # object
        print("  - Shoot object at targets")
        print("  - Press 'D' to toggle debug visualization")
    print("  - Press 'C' to recalibrate")
    print("  - Press 'F' to toggle fullscreen")
    print("  - Press 'R' to start new round")
    print("  - Press 'Q' or 'ESC' to quit")
    print("\n" + "="*60)

    clock = pygame.time.Clock()
    running = True
    round_number = 1
    last_hit_message = ""
    message_time = 0

    while running:
        dt = clock.tick(60) / 1000.0  # 60 FPS

        # Update target overlay for laser/object backend debug view
        if args.backend in ['laser', 'object'] and hasattr(detection_backend, 'debug_mode') and detection_backend.debug_mode:
            target_info = []
            for target in game.targets:
                if target.alive:
                    target_info.append((target.x, target.y, target.radius, target.color))
            if hasattr(detection_backend, 'set_game_targets'):
                detection_backend.set_game_targets(target_info)

        # Update AMS
        ams.update(dt)

        # Handle pygame events
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
                    print("\nRecalibrating...")
                    ams.calibrate_between_rounds(
                        display_surface=screen,
                        display_resolution=(DISPLAY_WIDTH, DISPLAY_HEIGHT)
                    )
                    print("Calibration complete!")
                elif event.key == pygame.K_d and args.backend in ['laser', 'object']:
                    if hasattr(detection_backend, 'set_debug_mode') and hasattr(detection_backend, 'debug_mode'):
                        detection_backend.set_debug_mode(not detection_backend.debug_mode)
                elif event.key == pygame.K_b and args.backend == 'laser':
                    if hasattr(detection_backend, 'toggle_bw_mode'):
                        detection_backend.toggle_bw_mode()
                elif event.key in [pygame.K_EQUALS, pygame.K_PLUS] and args.backend in ['laser', 'object']:
                    if hasattr(detection_backend, 'set_brightness_threshold'):
                        detection_backend.set_brightness_threshold(
                            detection_backend.brightness_threshold + 10
                        )
                elif event.key == pygame.K_MINUS and args.backend in ['laser', 'object']:
                    if hasattr(detection_backend, 'set_brightness_threshold'):
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

                    # Reset game
                    if hasattr(args, 'bw_palette') and args.bw_palette:
                        new_colors = [(255, 255, 255), (200, 200, 200)]
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

        pygame.display.flip()

        # Show debug visualization if enabled
        if args.backend in ['laser', 'object'] and hasattr(detection_backend, 'debug_mode') and detection_backend.debug_mode:
            debug_frame = detection_backend.get_debug_frame()
            if debug_frame is not None:
                import cv2
                cv2.imshow(f"{args.backend.capitalize()} Detection Debug", debug_frame)
                cv2.waitKey(1)

    return 0


def launch_duckhunt(args, screen, detection_backend, ams):
    """Launch Duck Hunt game.

    Uses the unified AMSInputAdapter to bridge AMS detection events to
    the game's InputManager, allowing identical game code for standalone
    and AMS modes.

    Args:
        args: Command-line arguments
        screen: Pygame display surface
        detection_backend: Configured detection backend
        ams: AMS session instance

    Returns:
        Exit code (0 for success)
    """
    from game.modes.classic import ClassicMode
    from game.mode_loader import load_game_mode_config
    from input.input_manager import InputManager
    from ams.game_adapter import AMSInputAdapter
    from models import GameState

    DISPLAY_WIDTH, DISPLAY_HEIGHT = screen.get_size()

    print("\n4. Initializing Duck Hunt...")

    # Load game mode configuration
    mode_path = os.path.join('games', 'DuckHunt', 'modes', f'{args.mode}.yaml')
    if not os.path.exists(mode_path):
        print(f"   ERROR: Mode file not found: {mode_path}")
        print(f"   Available modes: classic_archery, classic_ducks, classic_linear")
        return 1

    mode_config = load_game_mode_config(mode_path)
    print(f"   Mode: {mode_config.name}")
    print(f"   Description: {mode_config.description}")

    # Create game instance - extract parameters from config
    max_misses = mode_config.rules.max_misses
    target_score = mode_config.rules.score_target

    # Use first level's speed as initial speed
    initial_speed = None
    if mode_config.levels and len(mode_config.levels) > 0:
        initial_speed = mode_config.levels[0].target.speed  # Speed in pixels/sec

    # Create game mode with config parameters
    if initial_speed:
        game_mode = ClassicMode(
            max_misses=max_misses,
            target_score=target_score,
            initial_speed=initial_speed,
            audio_enabled=True
        )
    else:
        game_mode = ClassicMode(
            max_misses=max_misses,
            target_score=target_score,
            audio_enabled=True
        )

    # Create input manager with AMS adapter
    # This bridges AMS PlaneHitEvents -> game InputEvents
    ams_adapter = AMSInputAdapter(ams, DISPLAY_WIDTH, DISPLAY_HEIGHT)
    input_manager = InputManager(ams_adapter)
    print(f"   Game initialized with AMS input adapter")

    # Game loop
    print("\n5. Starting game loop...")
    print("\nControls:")
    if args.backend == 'mouse':
        print("  - Click to shoot")
    elif args.backend == 'laser':
        print("  - Point laser at targets")
        print("  - Press 'D' to toggle debug visualization")
        print("  - Press 'B' to toggle B/W threshold view")
        print("  - Press '+' or '-' to adjust brightness threshold")
        print("  - Press 'C' to recalibrate")
    else:  # object
        print("  - Shoot object at targets")
        print("  - Press 'D' to toggle debug visualization")
        print("  - Press 'C' to recalibrate")
    print("  - Press 'F' to toggle fullscreen")
    print("  - Press 'ESC' to quit")
    print("\n" + "="*60)

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(60) / 1000.0  # 60 FPS

        # Update input manager (this updates AMS internally)
        input_manager.update(dt)

        # Handle pygame events (keyboard controls, quit, etc.)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_f:
                    # Toggle fullscreen
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_c and args.backend in ['laser', 'object']:
                    print("\nRecalibrating...")
                    ams.calibrate(
                        display_surface=screen,
                        display_resolution=(DISPLAY_WIDTH, DISPLAY_HEIGHT)
                    )
                    print("Calibration complete!")
                elif event.key == pygame.K_d and args.backend in ['laser', 'object']:
                    if hasattr(detection_backend, 'set_debug_mode') and hasattr(detection_backend, 'debug_mode'):
                        detection_backend.set_debug_mode(not detection_backend.debug_mode)
                elif event.key == pygame.K_b and args.backend == 'laser':
                    if hasattr(detection_backend, 'toggle_bw_mode'):
                        detection_backend.toggle_bw_mode()
                elif event.key in [pygame.K_EQUALS, pygame.K_PLUS] and args.backend in ['laser', 'object']:
                    if hasattr(detection_backend, 'set_brightness_threshold'):
                        detection_backend.set_brightness_threshold(
                            detection_backend.brightness_threshold + 10
                        )
                elif event.key == pygame.K_MINUS and args.backend in ['laser', 'object']:
                    if hasattr(detection_backend, 'set_brightness_threshold'):
                        detection_backend.set_brightness_threshold(
                            detection_backend.brightness_threshold - 10
                        )

        # Get input events through unified interface
        # These are InputEvents with pixel coordinates - same format as standalone mode
        input_events = input_manager.get_events()

        # Pass events to game mode - same code works for standalone and AMS
        game_mode.handle_input(input_events)

        # Update game
        game_mode.update(dt)

        # Render game
        screen.fill((135, 206, 235))  # Sky blue background
        game_mode.render(screen)

        pygame.display.flip()

        # Show debug visualization if enabled
        if args.backend in ['laser', 'object'] and hasattr(detection_backend, 'debug_mode') and detection_backend.debug_mode:
            debug_frame = detection_backend.get_debug_frame()
            if debug_frame is not None:
                import cv2
                cv2.imshow(f"{args.backend.capitalize()} Detection Debug", debug_frame)
                cv2.waitKey(1)

        # Check if game is over
        if game_mode.state == GameState.GAME_OVER:
            print("\n" + "="*60)
            print("GAME OVER!")
            print(f"Final Score: {game_mode.get_score()}")
            print("="*60)
            running = False

    return 0


def launch_balloonpop(args, screen, detection_backend, ams):
    """Launch Balloon Pop game.

    Uses the unified AMSInputAdapter to bridge AMS detection events to
    the game's InputManager.

    Args:
        args: Command-line arguments
        screen: Pygame display surface
        detection_backend: Configured detection backend
        ams: AMS session instance

    Returns:
        Exit code (0 for success)
    """
    from games.BalloonPop.game_mode import BalloonPopMode, GameState
    from games.BalloonPop.input.input_manager import InputManager
    from ams.game_adapter import AMSInputAdapter

    DISPLAY_WIDTH, DISPLAY_HEIGHT = screen.get_size()

    print("\n4. Initializing Balloon Pop...")

    # Update BalloonPop config with actual screen size
    import games.BalloonPop.config as bp_config
    bp_config.SCREEN_WIDTH = DISPLAY_WIDTH
    bp_config.SCREEN_HEIGHT = DISPLAY_HEIGHT

    # Create game mode with optional overrides from args
    game_kwargs = {}
    if hasattr(args, 'spawn_rate') and args.spawn_rate is not None:
        game_kwargs['spawn_rate'] = args.spawn_rate
    if hasattr(args, 'max_escaped') and args.max_escaped is not None:
        game_kwargs['max_escaped'] = args.max_escaped
    if hasattr(args, 'target_pops') and args.target_pops is not None:
        game_kwargs['target_pops'] = args.target_pops

    game = BalloonPopMode(**game_kwargs)

    # Create input manager with AMS adapter
    ams_adapter = AMSInputAdapter(ams, DISPLAY_WIDTH, DISPLAY_HEIGHT)
    input_manager = InputManager(ams_adapter)
    print(f"   Game initialized with AMS input adapter")

    # Game loop
    print("\n5. Starting game loop...")
    print("\nControls:")
    if args.backend == 'mouse':
        print("  - Click to pop balloons")
    elif args.backend == 'laser':
        print("  - Point laser at balloons to pop them")
        print("  - Press 'D' to toggle debug visualization")
        print("  - Press 'C' to recalibrate")
    else:  # object
        print("  - Shoot object at balloons to pop them")
        print("  - Press 'D' to toggle debug visualization")
        print("  - Press 'C' to recalibrate")
    print("  - Press 'F' to toggle fullscreen")
    print("  - Press 'R' to restart")
    print("  - Press 'ESC' to quit")
    print("\n" + "="*60)

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(60) / 1000.0

        # Update input manager (this updates AMS internally)
        input_manager.update(dt)

        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_r:
                    # Restart game
                    game = BalloonPopMode(**game_kwargs)
                    print("\n--- RESTARTING ---\n")
                elif event.key == pygame.K_c and args.backend in ['laser', 'object']:
                    print("\nRecalibrating...")
                    ams.calibrate(
                        display_surface=screen,
                        display_resolution=(DISPLAY_WIDTH, DISPLAY_HEIGHT)
                    )
                    print("Calibration complete!")
                elif event.key == pygame.K_d and args.backend in ['laser', 'object']:
                    if hasattr(detection_backend, 'set_debug_mode') and hasattr(detection_backend, 'debug_mode'):
                        detection_backend.set_debug_mode(not detection_backend.debug_mode)

        # Get input events and pass to game
        input_events = input_manager.get_events()
        game.handle_input(input_events)

        # Update game
        game.update(dt)

        # Render
        game.render(screen)
        pygame.display.flip()

        # Show debug visualization if enabled
        if args.backend in ['laser', 'object'] and hasattr(detection_backend, 'debug_mode') and detection_backend.debug_mode:
            debug_frame = detection_backend.get_debug_frame()
            if debug_frame is not None:
                import cv2
                cv2.imshow(f"{args.backend.capitalize()} Detection Debug", debug_frame)
                cv2.waitKey(1)

        # Check game over
        if game.state == GameState.GAME_OVER:
            print("\n" + "="*60)
            print("GAME OVER!")
            print(f"Final Score: {game.get_score()}")
            print("="*60)
            running = False
        elif game.state == GameState.WON:
            print("\n" + "="*60)
            print("YOU WIN!")
            print(f"Final Score: {game.get_score()}")
            print("="*60)
            running = False

    return 0


def launch_game_generic(args, screen, detection_backend, ams, registry: GameRegistry):
    """
    Generic game launcher using the game registry.

    This function works with any game that follows the game_info.py protocol.

    Args:
        args: Command-line arguments
        screen: Pygame display surface
        detection_backend: Configured detection backend
        ams: AMS session instance
        registry: GameRegistry instance

    Returns:
        Exit code (0 for success)
    """
    from ams.game_adapter import AMSInputAdapter

    DISPLAY_WIDTH, DISPLAY_HEIGHT = screen.get_size()
    game_slug = args.game.lower()

    print(f"\n4. Initializing {args.game}...")

    # Get game info
    game_info = registry.get_game_info(game_slug)
    if game_info is None:
        print(f"   ERROR: Unknown game: {game_slug}")
        return 1

    print(f"   Game: {game_info.name}")
    print(f"   Description: {game_info.description}")

    # Collect game-specific kwargs from args
    game_kwargs = {}
    for key in ['mode', 'spawn_rate', 'max_escaped', 'target_pops']:
        if hasattr(args, key):
            value = getattr(args, key)
            if value is not None:
                game_kwargs[key] = value

    # Create game mode
    try:
        game = registry.create_game(game_slug, DISPLAY_WIDTH, DISPLAY_HEIGHT, **game_kwargs)
    except Exception as e:
        print(f"   ERROR: Failed to create game: {e}")
        return 1

    # Create input manager with AMS adapter
    input_manager = registry.create_input_manager(game_slug, ams, DISPLAY_WIDTH, DISPLAY_HEIGHT)
    print(f"   Game initialized with AMS input adapter")

    # Get GameState enum for this game
    GameState = registry.get_game_state_enum(game_slug)

    # Game loop
    print("\n5. Starting game loop...")
    print("\nControls:")
    if args.backend == 'mouse':
        print("  - Click to shoot/interact")
    elif args.backend == 'laser':
        print("  - Point laser at targets")
        print("  - Press 'D' to toggle debug visualization")
        print("  - Press 'C' to recalibrate")
    else:  # object
        print("  - Shoot object at targets")
        print("  - Press 'D' to toggle debug visualization")
        print("  - Press 'C' to recalibrate")
    print("  - Press 'F' to toggle fullscreen")
    print("  - Press 'R' to restart")
    print("  - Press 'ESC' to quit")
    print("\n" + "="*60)

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(60) / 1000.0

        # Update input manager (this updates AMS internally)
        input_manager.update(dt)

        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_r:
                    # Restart game
                    game = registry.create_game(game_slug, DISPLAY_WIDTH, DISPLAY_HEIGHT, **game_kwargs)
                    print("\n--- RESTARTING ---\n")
                elif event.key == pygame.K_c and args.backend in ['laser', 'object']:
                    print("\nRecalibrating...")
                    ams.calibrate(
                        display_surface=screen,
                        display_resolution=(DISPLAY_WIDTH, DISPLAY_HEIGHT)
                    )
                    print("Calibration complete!")
                elif event.key == pygame.K_d and args.backend in ['laser', 'object']:
                    if hasattr(detection_backend, 'set_debug_mode') and hasattr(detection_backend, 'debug_mode'):
                        detection_backend.set_debug_mode(not detection_backend.debug_mode)

        # Get input events and pass to game
        input_events = input_manager.get_events()
        game.handle_input(input_events)

        # Update game
        game.update(dt)

        # Render
        game.render(screen)
        pygame.display.flip()

        # Show debug visualization if enabled
        if args.backend in ['laser', 'object'] and hasattr(detection_backend, 'debug_mode') and detection_backend.debug_mode:
            debug_frame = detection_backend.get_debug_frame()
            if debug_frame is not None:
                import cv2
                cv2.imshow(f"{args.backend.capitalize()} Detection Debug", debug_frame)
                cv2.waitKey(1)

        # Check game over
        if game.state == GameState.GAME_OVER:
            print("\n" + "="*60)
            print("GAME OVER!")
            print(f"Final Score: {game.get_score()}")
            print("="*60)
            running = False
        elif hasattr(GameState, 'WON') and game.state == GameState.WON:
            print("\n" + "="*60)
            print("YOU WIN!")
            print(f"Final Score: {game.get_score()}")
            print("="*60)
            running = False

    return 0


def main():
    """Main entry point for AMS game launcher."""

    # Get game registry for auto-discovery
    registry = get_registry()
    available_games = registry.list_games()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='AMS Game Launcher - Play games with multiple detection backends',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available games
  python ams_game.py --list-games

  # Play with mouse (development)
  python ams_game.py --game balloonpop --backend mouse

  # Play with laser pointer
  python ams_game.py --game duckhunt --backend laser --fullscreen --display 1

  # Custom game settings
  python ams_game.py --game balloonpop --spawn-rate 0.5 --max-escaped 5
        """
    )

    # List games option
    parser.add_argument(
        '--list-games',
        action='store_true',
        help='List all available games and exit'
    )

    # Game selection - use auto-discovered games + simple_targets
    game_choices = ['simple_targets'] + available_games
    parser.add_argument(
        '--game',
        choices=game_choices,
        default='balloonpop' if 'balloonpop' in available_games else 'simple_targets',
        help=f'Game to play (available: {", ".join(game_choices)})'
    )

    # Backend selection
    parser.add_argument(
        '--backend',
        choices=['mouse', 'laser', 'object'],
        default='mouse',
        help='Detection backend to use (default: mouse)'
    )

    # Duck Hunt specific
    parser.add_argument(
        '--mode',
        type=str,
        default='classic_archery',
        help='Duck Hunt game mode (default: classic_archery)'
    )

    # Camera/detection settings
    parser.add_argument(
        '--camera-id',
        type=int,
        default=0,
        help='Camera ID for laser/object backend (default: 0)'
    )
    parser.add_argument(
        '--brightness',
        type=int,
        default=200,
        help='Brightness threshold for laser detection (default: 200)'
    )

    # Display settings
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

    # Simple targets specific
    parser.add_argument(
        '--bw-palette',
        action='store_true',
        help='Use black and white palette (simple_targets only)'
    )

    # Balloon Pop specific
    parser.add_argument(
        '--spawn-rate',
        type=float,
        default=None,
        help='Balloon spawn rate in seconds (balloonpop only)'
    )
    parser.add_argument(
        '--max-escaped',
        type=int,
        default=None,
        help='Max escaped balloons before game over (balloonpop only)'
    )
    parser.add_argument(
        '--target-pops',
        type=int,
        default=None,
        help='Pops needed to win, 0=endless (balloonpop only)'
    )

    args = parser.parse_args()

    # Handle --list-games
    if args.list_games:
        print("\nAvailable Games:")
        print("="*50)
        for slug in registry.list_games():
            info = registry.get_game_info(slug)
            print(f"\n  {slug}")
            print(f"    Name: {info.name}")
            print(f"    Description: {info.description}")
            if info.has_config:
                print(f"    Config: {info.config_file or 'config.py'}")
        print("\n  simple_targets")
        print("    Name: Simple Targets")
        print("    Description: Basic target shooting game (built-in)")
        print()
        return 0

    # Initialize pygame
    pygame.init()

    # Display settings
    if args.fullscreen:
        displays = pygame.display.get_desktop_sizes()
        print(f"\nAvailable displays: {len(displays)}")
        for i, size in enumerate(displays):
            print(f"  Display {i}: {size[0]}x{size[1]}")

        if args.display >= len(displays):
            print(f"\nWARNING: Display {args.display} not found, using display 0")
            display_index = 0
        else:
            display_index = args.display

        DISPLAY_WIDTH, DISPLAY_HEIGHT = displays[display_index]
        print(f"\nUsing display {display_index}: {DISPLAY_WIDTH}x{DISPLAY_HEIGHT}")

        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{sum(d[0] for d in displays[:display_index])},0"
        screen = pygame.display.set_mode(
            (DISPLAY_WIDTH, DISPLAY_HEIGHT),
            pygame.FULLSCREEN
        )
        print("Fullscreen mode enabled")
    else:
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

    pygame.display.set_caption(f"AMS - {args.game.title()} ({args.backend.upper()} mode)")

    print("="*60)
    print(f"AMS Game Launcher - {args.game.title()}")
    print("="*60)
    print(f"\nGame: {args.game}")
    print(f"Backend: {args.backend.upper()}")
    if args.game == 'duckhunt':
        print(f"Mode: {args.mode}")
    print("\nInitializing...")

    # Create detection backend
    detection_backend = create_detection_backend(args, DISPLAY_WIDTH, DISPLAY_HEIGHT)

    # Create AMS session
    print("\n2. Creating AMS session...")
    ams = AMSSession(
        backend=detection_backend,
        session_name=f"{args.game}_session"
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

    # Launch selected game
    if args.game == 'simple_targets':
        # Simple targets uses the old launcher (not yet migrated to registry)
        exit_code = launch_simple_targets(args, screen, detection_backend, ams)
    elif args.game in registry.list_games():
        # Use generic launcher for registry games
        exit_code = launch_game_generic(args, screen, detection_backend, ams, registry)
    else:
        print(f"Unknown game: {args.game}")
        exit_code = 1

    # Cleanup and summary
    print("\n" + "="*60)
    print("Session Complete")
    print("="*60)

    summary = ams.get_session_summary()
    print(f"\nSession Summary:")
    print(f"  Name: {summary['session_name']}")
    print(f"  Game: {args.game}")
    print(f"  Backend: {summary['backend']}")
    print(f"  Total events: {summary['total_events']}")

    # Save session
    ams.save_session()
    print(f"\nSession saved to: ./ams_sessions/{ams.session_name}.json")

    # Cleanup
    if args.backend in ['laser', 'object']:
        import cv2
        cv2.destroyAllWindows()
        if hasattr(detection_backend, 'camera'):
            detection_backend.camera.release()

    pygame.quit()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
