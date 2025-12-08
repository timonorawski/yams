#!/usr/bin/env python3
"""Containment - Standalone entry point.

Adversarial geometry-building game where you place deflectors to contain
a ball trying to escape through gaps.
"""

import pygame
import sys
import os

# Add project root to path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _root not in sys.path:
    sys.path.insert(0, _root)

from games.common import GameState
from games.Containment.game_mode import ContainmentMode
from games.Containment.input.input_manager import InputManager
from games.Containment.input.sources.mouse import MouseInputSource
from games.Containment.config import SCREEN_WIDTH, SCREEN_HEIGHT


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Containment")

    input_manager = InputManager(MouseInputSource())
    game = ContainmentMode()
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
                    # Reset game
                    game.reset()
                elif event.key == pygame.K_SPACE:
                    # Manual retrieval ready
                    if game.state == GameState.RETRIEVAL:
                        game._end_retrieval()
                elif event.key == pygame.K_p:
                    # Cycle palette
                    new_palette = game.cycle_palette()
                    print(f"Switched to palette: {new_palette}")

        events = input_manager.get_events()
        game.handle_input(events)
        game.update(dt)
        game.render(screen)
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
