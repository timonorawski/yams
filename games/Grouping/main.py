#!/usr/bin/env python3
"""Grouping - Standalone entry point."""

import pygame
import sys
import os

# Add project root to path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _root not in sys.path:
    sys.path.insert(0, _root)

from games.Grouping.game_mode import GroupingMode, GameState
from games.Grouping.input.input_manager import InputManager
from games.Grouping.input.sources.mouse import MouseInputSource
from games.Grouping.config import SCREEN_WIDTH, SCREEN_HEIGHT


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Grouping - Precision Training")

    input_manager = InputManager(MouseInputSource())
    game = GroupingMode()
    clock = pygame.time.Clock()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        input_manager.update(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    game = GroupingMode()

        events = input_manager.get_events()
        game.handle_input(events)
        game.update(dt)
        game.render(screen)
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
