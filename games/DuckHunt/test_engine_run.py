"""
Quick test script to verify engine runs without errors.

This script runs the game engine for a few frames then exits.
Used for testing during development.
"""

import pygame
from engine import GameEngine


def test_engine_run():
    """Test that the engine can run for a few frames."""
    engine = GameEngine()

    # Run for a few frames
    frame_count = 0
    max_frames = 60  # Run for 1 second at 60 FPS

    while engine.running and frame_count < max_frames:
        dt = engine.clock.tick(60) / 1000.0

        # Handle events (including quit)
        engine.handle_events()

        # Update
        engine.update(dt)

        # Render
        engine.render()

        frame_count += 1

    engine.quit()
    print(f"✓ Engine ran successfully for {frame_count} frames")
    return True


if __name__ == "__main__":
    try:
        test_engine_run()
        print("✓ All tests passed!")
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise
