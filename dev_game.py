#!/usr/bin/env python3
"""
Development Mode Game Launcher

Simple launcher for testing games with mouse input only.
No AMS session, no calibration, no detection backends - just pure game testing.

Uses the game registry for auto-discovery.

Usage:
    # List available games
    python dev_game.py --list

    # Play a game
    python dev_game.py balloonpop
    python dev_game.py duckhunt
    python dev_game.py duckhunt --mode classic_ducks

    # With custom resolution
    python dev_game.py balloonpop --resolution 1920x1080
"""

import pygame
import sys
import os
import argparse

# Ensure project root is on path
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from games.registry import get_registry


def main():
    """Main entry point for development game launcher."""

    # Get game registry
    registry = get_registry()
    available_games = registry.list_games()

    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Development Mode Game Launcher - Test games with mouse input',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dev_game.py --list              # List available games
  python dev_game.py balloonpop          # Play Balloon Pop
  python dev_game.py duckhunt            # Play Duck Hunt
  python dev_game.py duckhunt --mode classic_ducks
        """
    )

    parser.add_argument(
        'game',
        nargs='?',
        choices=available_games,
        help=f'Game to play (available: {", ".join(available_games)})'
    )

    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available games and exit'
    )

    parser.add_argument(
        '--resolution', '-r',
        type=str,
        default='1280x720',
        help='Window resolution as WIDTHxHEIGHT (default: 1280x720)'
    )

    parser.add_argument(
        '--fullscreen', '-f',
        action='store_true',
        help='Run in fullscreen mode'
    )

    # Game-specific arguments
    parser.add_argument(
        '--mode',
        type=str,
        default='classic_archery',
        help='Game mode for Duck Hunt (default: classic_archery)'
    )

    parser.add_argument(
        '--spawn-rate',
        type=float,
        default=None,
        help='Balloon spawn rate in seconds (Balloon Pop)'
    )

    parser.add_argument(
        '--max-escaped',
        type=int,
        default=None,
        help='Max escaped balloons before game over (Balloon Pop)'
    )

    parser.add_argument(
        '--target-pops',
        type=int,
        default=None,
        help='Pops needed to win (Balloon Pop, 0=endless)'
    )

    # Grouping specific
    parser.add_argument(
        '--method',
        type=str,
        default=None,
        help='Grouping method: centroid or fixed (Grouping)'
    )

    # ManyTargets specific
    parser.add_argument(
        '--count',
        type=int,
        default=None,
        help='Number of targets (ManyTargets)'
    )
    parser.add_argument(
        '--size',
        type=str,
        default=None,
        help='Target size: small, medium, large (ManyTargets)'
    )
    parser.add_argument(
        '--timed',
        type=int,
        default=None,
        help='Time limit in seconds (ManyTargets)'
    )
    parser.add_argument(
        '--miss-mode',
        type=str,
        default=None,
        help='Miss behavior: penalty or strict (ManyTargets)'
    )
    parser.add_argument(
        '--allow-duplicates',
        action='store_true',
        default=False,
        help='Allow hitting same target multiple times (ManyTargets)'
    )
    parser.add_argument(
        '--progressive',
        action='store_true',
        default=False,
        help='Targets shrink as you clear (ManyTargets)'
    )
    parser.add_argument(
        '--shrink-rate',
        type=float,
        default=None,
        help='Size multiplier per hit in progressive mode (ManyTargets)'
    )
    parser.add_argument(
        '--min-size',
        type=int,
        default=None,
        help='Minimum target radius in progressive mode (ManyTargets)'
    )
    parser.add_argument(
        '--spacing',
        type=float,
        default=None,
        help='Minimum spacing between targets (ManyTargets)'
    )

    args = parser.parse_args()

    # Handle --list
    if args.list:
        print("\nAvailable Games (Development Mode)")
        print("=" * 50)
        for slug in available_games:
            info = registry.get_game_info(slug)
            print(f"\n  {slug}")
            print(f"    Name: {info.name}")
            print(f"    Description: {info.description}")
            print(f"    Version: {info.version}")
        print()
        return 0

    # Require a game
    if args.game is None:
        parser.print_help()
        print(f"\nAvailable games: {', '.join(available_games)}")
        return 1

    # Parse resolution
    try:
        width, height = args.resolution.split('x')
        DISPLAY_WIDTH = int(width)
        DISPLAY_HEIGHT = int(height)
    except ValueError:
        print(f"Invalid resolution format: {args.resolution}")
        print("Expected format: WIDTHxHEIGHT (e.g., 1920x1080)")
        return 1

    # Initialize pygame
    pygame.init()

    # Create display
    game_info = registry.get_game_info(args.game)

    if args.fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        DISPLAY_WIDTH, DISPLAY_HEIGHT = screen.get_size()
    else:
        screen = pygame.display.set_mode((DISPLAY_WIDTH, DISPLAY_HEIGHT))

    pygame.display.set_caption(f"{game_info.name} - Development Mode")

    print("=" * 60)
    print(f"Development Mode: {game_info.name}")
    print("=" * 60)
    print(f"Resolution: {DISPLAY_WIDTH}x{DISPLAY_HEIGHT}")
    print(f"Input: Mouse")
    print()

    # Collect game kwargs
    game_kwargs = {}
    if args.mode and args.game == 'duckhunt':
        game_kwargs['mode'] = args.mode
    if args.spawn_rate is not None:
        game_kwargs['spawn_rate'] = args.spawn_rate
    if args.max_escaped is not None:
        game_kwargs['max_escaped'] = args.max_escaped
    if args.target_pops is not None:
        game_kwargs['target_pops'] = args.target_pops
    if args.method is not None and args.game == 'grouping':
        game_kwargs['method'] = args.method

    # Create game
    try:
        game = registry.create_game(args.game, DISPLAY_WIDTH, DISPLAY_HEIGHT, **game_kwargs)
    except Exception as e:
        print(f"ERROR: Failed to create game: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Create input manager with mouse source (standalone mode)
    input_manager = registry.create_input_manager(args.game, None, DISPLAY_WIDTH, DISPLAY_HEIGHT)

    # Get GameState enum
    GameState = registry.get_game_state_enum(args.game)

    print("Controls:")
    print("  - Click to interact")
    print("  - R to restart")
    print("  - F to toggle fullscreen")
    print("  - ESC to quit")
    print()
    print("=" * 60)

    # Game loop
    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(60) / 1000.0

        # Update input
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
                    # Restart
                    game = registry.create_game(args.game, DISPLAY_WIDTH, DISPLAY_HEIGHT, **game_kwargs)
                    print("\n--- RESTARTED ---\n")

        # Get input events and pass to game
        input_events = input_manager.get_events()
        game.handle_input(input_events)

        # Update game
        game.update(dt)

        # Render
        game.render(screen)
        pygame.display.flip()

        # Check game over
        if game.state == GameState.GAME_OVER:
            print("\n" + "=" * 60)
            print("GAME OVER!")
            print(f"Final Score: {game.get_score()}")
            print("=" * 60)
            print("\nPress R to restart or ESC to quit")

            # Wait for restart or quit
            waiting = True
            while waiting and running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        waiting = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                            waiting = False
                        elif event.key == pygame.K_r:
                            game = registry.create_game(args.game, DISPLAY_WIDTH, DISPLAY_HEIGHT, **game_kwargs)
                            print("\n--- RESTARTED ---\n")
                            waiting = False
                clock.tick(30)

        elif hasattr(GameState, 'WON') and game.state == GameState.WON:
            print("\n" + "=" * 60)
            print("YOU WIN!")
            print(f"Final Score: {game.get_score()}")
            print("=" * 60)
            print("\nPress R to restart or ESC to quit")

            # Wait for restart or quit
            waiting = True
            while waiting and running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        waiting = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                            waiting = False
                        elif event.key == pygame.K_r:
                            game = registry.create_game(args.game, DISPLAY_WIDTH, DISPLAY_HEIGHT, **game_kwargs)
                            print("\n--- RESTARTED ---\n")
                            waiting = False
                clock.tick(30)

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
