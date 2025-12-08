"""
Configuration for Balloon Pop game.

Loads settings from .env file in the game directory, with sensible defaults.
Create a .env.local file to override settings without modifying .env.
"""

import os
from pathlib import Path
from typing import Tuple

# Find the game directory (where this config.py lives)
GAME_DIR = Path(__file__).parent

def _load_env():
    """Load environment variables from .env files."""
    # Load .env first (defaults)
    env_file = GAME_DIR / ".env"
    if env_file.exists():
        _parse_env_file(env_file)

    # Load .env.local second (overrides)
    local_env = GAME_DIR / ".env.local"
    if local_env.exists():
        _parse_env_file(local_env)

def _parse_env_file(filepath: Path):
    """Parse a .env file and set environment variables."""
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Parse KEY=value
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Only set if not already set (allows real env vars to override)
                if key not in os.environ:
                    os.environ[key] = value

def _get_int(key: str, default: int) -> int:
    """Get integer from environment."""
    return int(os.environ.get(key, default))

def _get_float(key: str, default: float) -> float:
    """Get float from environment."""
    return float(os.environ.get(key, default))

def _get_bool(key: str, default: bool) -> bool:
    """Get boolean from environment."""
    val = os.environ.get(key, str(default)).lower()
    return val in ('true', '1', 'yes', 'on')

# Load environment on import
_load_env()

# Display settings
SCREEN_WIDTH: int = _get_int('SCREEN_WIDTH', 1280)
SCREEN_HEIGHT: int = _get_int('SCREEN_HEIGHT', 720)

# Balloon spawning
SPAWN_RATE: float = _get_float('SPAWN_RATE', 1.5)  # Seconds between spawns
BALLOON_MIN_SIZE: int = _get_int('BALLOON_MIN_SIZE', 40)
BALLOON_MAX_SIZE: int = _get_int('BALLOON_MAX_SIZE', 80)

# Movement
FLOAT_SPEED_MIN: float = _get_float('FLOAT_SPEED_MIN', 50)  # Pixels per second
FLOAT_SPEED_MAX: float = _get_float('FLOAT_SPEED_MAX', 150)
DRIFT_SPEED_MAX: float = _get_float('DRIFT_SPEED_MAX', 30)  # Horizontal drift

# Game rules
MAX_ESCAPED: int = _get_int('MAX_ESCAPED', 10)  # Game over after this many escape
TARGET_POPS: int = _get_int('TARGET_POPS', 0)  # Win condition (0 = endless)

# Audio
AUDIO_ENABLED: bool = _get_bool('AUDIO_ENABLED', True)

# Colors (not configurable via .env for simplicity)
BALLOON_COLORS: list[Tuple[int, int, int]] = [
    (255, 0, 0),      # Red
    (0, 255, 0),      # Green
    (0, 0, 255),      # Blue
    (255, 255, 0),    # Yellow
    (255, 0, 255),    # Magenta
    (0, 255, 255),    # Cyan
    (255, 128, 0),    # Orange
    (128, 0, 255),    # Purple
]

BACKGROUND_COLOR: Tuple[int, int, int] = (135, 206, 235)  # Sky blue
POP_EFFECT_COLOR: Tuple[int, int, int] = (255, 255, 255)  # White flash
