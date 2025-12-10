#!/usr/bin/env python3
"""BrickBreaker - Standalone Entry Point.

Run this to play with mouse input (no AMS required).

Usage:
    python main.py
    python main.py --pacing archery
    python main.py --lives 5
"""

import argparse
import sys
import os
import time

# Add project root to path for imports
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pygame

from games.common import GameState
from games.common.input import InputEvent
from games.BrickBreaker.game_mode import BrickBreakerMode
from games.BrickBreaker.config import SCREEN_WIDTH, SCREEN_HEIGHT
from models import Vector2D


def main():
    """Run BrickBreaker standalone."""
    parser = argparse.ArgumentParser(description="BrickBreaker - Standalone")

    # Display options
    parser.add_argument('--width', type=int, default=SCREEN_WIDTH, help='Screen width')
    parser.add_argument('--height', type=int, default=SCREEN_HEIGHT, help='Screen height')
    parser.add_argument('--fullscreen', action='store_true', help='Run fullscreen')

    # Game options
    parser.add_argument('--pacing', type=str, default='throwing',
                        choices=['archery', 'throwing', 'blaster'],
                        help='Device speed preset')
    parser.add_argument('--lives', type=int, default=3, help='Starting lives')
    parser.add_argument('--skin', type=str, default='geometric',
                        choices=['geometric'],
                        help='Visual skin')

    args = parser.parse_args()

    # Initialize pygame
    pygame.init()
    pygame.font.init()

    # Create display
    if args.fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        width, height = screen.get_size()
    else:
        width, height = args.width, args.height
        screen = pygame.display.set_mode((width, height))

    pygame.display.set_caption("BrickBreaker")

    # Create game
    game = BrickBreakerMode(
        skin=args.skin,
        pacing=args.pacing,
        lives=args.lives,
        width=width,
        height=height,
    )

    # Game loop
    clock = pygame.time.Clock()
    running = True

    print("\n" + "=" * 50)
    print("BRICKBREAKER")
    print("=" * 50)
    print("Controls:")
    print("  - Click to move paddle to that position")
    print("  - First click also launches the ball")
    print("  - R to restart")
    print("  - ESC to quit")
    print("=" * 50 + "\n")

    while running:
        dt = clock.tick(60) / 1000.0  # 60 FPS

        # Collect input events
        input_events: list[InputEvent] = []

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    game.reset()
                    print("Game restarted!")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Create input event at mouse position
                    input_events.append(InputEvent(
                        position=Vector2D(x=float(event.pos[0]), y=float(event.pos[1])),
                        timestamp=time.monotonic(),
                    ))

        # Pass input to game
        game.handle_input(input_events)

        # Update game
        game.update(dt)

        # Render
        game.render(screen)
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
