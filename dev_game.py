#!/usr/bin/env python3
"""
Development Mode Game Launcher

Simple launcher for testing games with mouse input only.
No AMS session, no calibration, no detection backends - just pure game testing.

Uses the game registry for auto-discovery. Game-specific arguments are
dynamically loaded from each game's game_info.py ARGUMENTS list.

Usage:
    # List available games
    python dev_game.py --list

    # Play a game
    python dev_game.py balloonpop
    python dev_game.py duckhunt
    python dev_game.py duckhunt --mode classic_ducks

    # See game-specific options
    python dev_game.py containment --help

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

    # Phase 1: Parse just enough to identify the game
    # Use parse_known_args to allow unknown game-specific args through
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('game', nargs='?', choices=available_games)
    pre_parser.add_argument('--list', '-l', action='store_true')
    pre_parser.add_argument('--help', '-h', action='store_true')

    pre_args, remaining = pre_parser.parse_known_args()

    # Phase 2: Build full parser with game-specific arguments
    parser = argparse.ArgumentParser(
        description='Development Mode Game Launcher - Test games with mouse input',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available games: {', '.join(available_games)}

Examples:
  python dev_game.py --list              # List available games
  python dev_game.py balloonpop          # Play Balloon Pop
  python dev_game.py containment --tempo wild
  python dev_game.py duckhunt --mode classic_ducks
  python dev_game.py <game> --help       # See game-specific options
        """
    )

    parser.add_argument(
        'game',
        nargs='?',
        choices=available_games,
        help=f'Game to play'
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

    # Add game-specific arguments if a game was specified
    game_args_added = set()
    if pre_args.game:
        game_arguments = registry.get_game_arguments(pre_args.game)
        for arg_def in game_arguments:
            arg_name = arg_def['name']
            # Avoid duplicates
            if arg_name in game_args_added:
                continue
            game_args_added.add(arg_name)

            # Build kwargs for add_argument
            kwargs = {}
            if 'type' in arg_def:
                type_val = arg_def['type']
                # Handle type as string or actual type
                if isinstance(type_val, str):
                    kwargs['type'] = {'str': str, 'int': int, 'float': float}.get(type_val, str)
                else:
                    kwargs['type'] = type_val
            if 'default' in arg_def:
                kwargs['default'] = arg_def['default']
            if 'help' in arg_def:
                kwargs['help'] = arg_def['help']
            if 'action' in arg_def:
                kwargs['action'] = arg_def['action']
                kwargs.pop('type', None)  # action and type are mutually exclusive
            if 'choices' in arg_def:
                kwargs['choices'] = arg_def['choices']

            parser.add_argument(arg_name, **kwargs)

    # Now parse everything
    args = parser.parse_args()

    # Handle --list
    if args.list:
        print("\nAvailable Games (Development Mode)")
        print("=" * 50)
        for slug in available_games:
            info = registry.get_game_info(slug)
            if info:
                print(f"\n  {slug}")
                print(f"    Name: {info.name}")
                print(f"    Description: {info.description}")
                print(f"    Version: {info.version}")

                # Show available arguments
                game_args = registry.get_game_arguments(slug)
                if game_args:
                    arg_names = [a['name'] for a in game_args]
                    print(f"    Options: {', '.join(arg_names)}")
        print()
        return 0

    # Require a game
    if args.game is None:
        parser.print_help()
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

    if game_info:
        pygame.display.set_caption(f"{game_info.name} - Development Mode")
        print("=" * 60)
        print(f"Development Mode: {game_info.name}")
        print("=" * 60)
    else:
        pygame.display.set_caption(f"{args.game} - Development Mode")
        print("=" * 60)
        print(f"Development Mode: {args.game}")
        print("=" * 60)

    print(f"Resolution: {DISPLAY_WIDTH}x{DISPLAY_HEIGHT}")
    print(f"Input: Mouse")
    print()

    # Collect game kwargs from all parsed arguments
    # Skip the common launcher arguments
    skip_args = {'game', 'list', 'resolution', 'fullscreen'}
    game_kwargs = {
        k: v for k, v in vars(args).items()
        if k not in skip_args and v is not None
    }

    if game_kwargs:
        print("Game options:")
        for k, v in game_kwargs.items():
            print(f"  --{k.replace('_', '-')}: {v}")
        print()

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
    print("  - P to cycle palette (if supported)")
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
                elif event.key == pygame.K_p:
                    # Cycle palette if supported
                    if hasattr(game, 'cycle_palette'):
                        new_palette = game.cycle_palette()
                        print(f"Palette: {new_palette}")
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

        elif game.state == GameState.WON:
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
