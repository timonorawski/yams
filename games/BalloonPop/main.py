#!/usr/bin/env python3
"""
Balloon Pop - Standalone entry point.

Run this to play Balloon Pop with mouse input (no AMS required).

Usage:
    python main.py
    python main.py --fullscreen
    python main.py --width 1920 --height 1080
"""

import argparse
import pygame
import sys
import os

# Support running from any directory - add project root to path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from games.BalloonPop.game_mode import BalloonPopMode, GameState
from games.BalloonPop.input.input_manager import InputManager
from games.BalloonPop.input.sources.mouse import MouseInputSource
from games.BalloonPop.config import SCREEN_WIDTH, SCREEN_HEIGHT


def main():
    """Run Balloon Pop game."""
    parser = argparse.ArgumentParser(description="Balloon Pop Game")
    parser.add_argument('--width', type=int, default=SCREEN_WIDTH, help='Screen width')
    parser.add_argument('--height', type=int, default=SCREEN_HEIGHT, help='Screen height')
    parser.add_argument('--fullscreen', action='store_true', help='Run fullscreen')
    parser.add_argument('--pacing', type=str, default='throwing', choices=['archery', 'throwing', 'blaster'], help='Device speed preset')
    parser.add_argument('--quiver-size', type=int, default=None, help='Shots per round (0=unlimited)')
    parser.add_argument('--retrieval-pause', type=float, default=None, help='Retrieval pause in seconds (0=manual ready)')
    parser.add_argument('--palette', type=str, default=None, help='Test palette name')
    parser.add_argument('--spawn-rate', type=float, default=None, help='Seconds between spawns (overrides pacing)')
    parser.add_argument('--max-escaped', type=int, default=None, help='Max escaped before game over')
    parser.add_argument('--target-pops', type=int, default=None, help='Pops needed to win (0=endless)')
    args = parser.parse_args()

    # Initialize pygame
    pygame.init()

    # Create display
    if args.fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        width, height = screen.get_size()
    else:
        width, height = args.width, args.height
        screen = pygame.display.set_mode((width, height))

    pygame.display.set_caption("Balloon Pop")

    # Update config with actual screen size
    import games.BalloonPop.config as bp_config
    bp_config.SCREEN_WIDTH = width
    bp_config.SCREEN_HEIGHT = height

    # Create input manager with mouse input
    input_manager = InputManager(MouseInputSource())

    # Create game mode with optional overrides
    game_kwargs = {
        'pacing': args.pacing,
        'color_palette': args.palette,
    }
    if args.quiver_size is not None:
        game_kwargs['quiver_size'] = args.quiver_size
    if args.retrieval_pause is not None:
        game_kwargs['retrieval_pause'] = args.retrieval_pause
    if args.spawn_rate is not None:
        game_kwargs['spawn_rate'] = args.spawn_rate
    if args.max_escaped is not None:
        game_kwargs['max_escaped'] = args.max_escaped
    if args.target_pops is not None:
        game_kwargs['target_pops'] = args.target_pops

    game = BalloonPopMode(**game_kwargs)

    # Game loop
    clock = pygame.time.Clock()
    running = True

    print("="*50)
    print("BALLOON POP")
    print("="*50)
    print("\nPop the balloons before they escape!")
    print("\nControls:")
    print("  - Click to pop balloons")
    print("  - P to cycle palette")
    print("  - SPACE for manual retrieval ready")
    print("  - ESC to quit")
    print("  - R to restart")
    print("="*50)

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
                elif event.key == pygame.K_r:
                    # Restart game
                    game = BalloonPopMode(**game_kwargs)
                    print("\n--- RESTARTING ---\n")
                elif event.key == pygame.K_p:
                    # Cycle palette
                    new_palette = game._palette.cycle_palette()
                    print(f"Switched to palette: {new_palette}")
                elif event.key == pygame.K_SPACE:
                    # Manual retrieval ready
                    if game.state == GameState.RETRIEVAL:
                        game.ready_for_next_round()
                        print("Ready for next round!")

        # Get input events and pass to game
        events = input_manager.get_events()
        game.handle_input(events)

        # Update game
        game.update(dt)

        # Render
        game.render(screen)
        pygame.display.flip()

        # Check game over
        if game.state == GameState.GAME_OVER:
            print(f"\nGAME OVER! Score: {game.get_score()}")
            # Keep running to show game over screen
        elif game.state == GameState.WON:
            print(f"\nYOU WIN! Score: {game.get_score()}")

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
