"""
Quick demonstration of the visual feedback system.

This script shows the FeedbackManager in action with sample effects.
Run this to see hit/miss effects and score popups in real-time.

Usage:
    ./venv/bin/python demo_feedback.py
"""

import pygame
from models import Vector2D
from game.feedback import FeedbackManager


def main():
    """Run a simple demo of the feedback system."""
    # Initialize pygame
    pygame.init()

    # Create screen
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Duck Hunt - Feedback System Demo")

    # Create feedback manager
    feedback = FeedbackManager()

    # Clock for frame timing
    clock = pygame.time.Clock()

    # Demo state
    running = True
    frame_count = 0

    print("=" * 60)
    print("Duck Hunt - Feedback System Demo")
    print("=" * 60)
    print()
    print("Click anywhere on the screen:")
    print("  - Left click: Hit effect (green ring + score popup)")
    print("  - Right click: Miss effect (red X)")
    print()
    print("Effects will fade out automatically.")
    print("Press ESC or close window to exit.")
    print("=" * 60)

    while running:
        # Get delta time
        dt = clock.tick(60) / 1000.0  # Convert to seconds

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Get mouse position
                pos = Vector2D(x=float(event.pos[0]), y=float(event.pos[1]))

                if event.button == 1:  # Left click
                    # Add hit effect
                    points = 100
                    feedback.add_hit_effect(pos, points)
                    print(f"Hit effect at ({pos.x:.0f}, {pos.y:.0f}) - Score: +{points}")
                elif event.button == 3:  # Right click
                    # Add miss effect
                    feedback.add_miss_effect(pos)
                    print(f"Miss effect at ({pos.x:.0f}, {pos.y:.0f})")

        # Update feedback
        feedback.update(dt)

        # Render
        screen.fill((20, 30, 40))  # Dark blue background

        # Draw some helper text
        font = pygame.font.Font(None, 24)
        text = font.render(
            "Left Click: Hit | Right Click: Miss | ESC: Quit",
            True,
            (200, 200, 200)
        )
        screen.blit(text, (20, 20))

        # Draw active effect count
        count_text = font.render(
            f"Active effects: {feedback.get_active_count()}",
            True,
            (200, 200, 200)
        )
        screen.blit(count_text, (20, 560))

        # Render feedback effects
        feedback.render(screen)

        # Update display
        pygame.display.flip()

        frame_count += 1

    # Clean up
    pygame.quit()
    print()
    print("Demo ended.")
    print(f"Total frames rendered: {frame_count}")


if __name__ == "__main__":
    main()
