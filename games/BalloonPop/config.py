"""
Configuration for Balloon Pop game.

Loads settings from .env file in the game directory, with sensible defaults.
Create a .env.local file to override settings without modifying .env.
"""

import os
from pathlib import Path
from typing import Tuple
from dataclasses import dataclass

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

# Pacing presets for different device types
@dataclass
class PacingPreset:
    """Pacing configuration for different input device speeds."""
    name: str
    spawn_interval: float      # Seconds between spawns
    float_speed_min: float     # Min rise speed (pixels/sec)
    float_speed_max: float     # Max rise speed (pixels/sec)
    max_balloons: int          # Max simultaneous balloons
    balloon_size_min: int      # Smaller = harder
    balloon_size_max: int

PACING_PRESETS = {
    'archery': PacingPreset(
        name='archery',
        spawn_interval=4.0,      # Slow spawning
        float_speed_min=30,      # Slow rise
        float_speed_max=60,
        max_balloons=3,
        balloon_size_min=50,     # Larger targets
        balloon_size_max=90,
    ),
    'throwing': PacingPreset(
        name='throwing',
        spawn_interval=1.5,
        float_speed_min=50,
        float_speed_max=150,
        max_balloons=6,
        balloon_size_min=40,
        balloon_size_max=80,
    ),
    'blaster': PacingPreset(
        name='blaster',
        spawn_interval=0.6,
        float_speed_min=80,
        float_speed_max=200,
        max_balloons=10,
        balloon_size_min=30,
        balloon_size_max=60,
    ),
}
