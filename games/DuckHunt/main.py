"""
Entry point for Duck Hunt game.

Run this script to start the game:
    ./venv/bin/python main.py
"""

from engine import GameEngine


def main():
    """Initialize and run the Duck Hunt game."""
    # Create game engine
    engine = GameEngine()

    try:
        # Run the game loop
        engine.run()
    finally:
        # Ensure pygame quits cleanly
        engine.quit()


if __name__ == "__main__":
    main()
