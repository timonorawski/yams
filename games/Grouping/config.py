"""Configuration for Grouping game."""
import os
from pathlib import Path

GAME_DIR = Path(__file__).parent


def _load_env():
    """Load environment variables from .env file."""
    env_file = GAME_DIR / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip()


_load_env()


def _parse_color(value: str) -> tuple:
    """Parse RGB color from string like '255,255,255'."""
    try:
        parts = value.split(',')
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return (255, 255, 255)


def _parse_bool(value: str) -> bool:
    """Parse boolean from string."""
    return value.lower() in ('true', '1', 'yes')


# Display settings
SCREEN_WIDTH = int(os.environ.get('SCREEN_WIDTH', 1280))
SCREEN_HEIGHT = int(os.environ.get('SCREEN_HEIGHT', 720))

# Target settings
INITIAL_TARGET_RADIUS = int(os.environ.get('INITIAL_TARGET_RADIUS', 150))
MIN_TARGET_RADIUS = int(os.environ.get('MIN_TARGET_RADIUS', 15))
GROUP_MARGIN = float(os.environ.get('GROUP_MARGIN', 1.15))

# Visual settings
SHOW_HIT_MARKERS = _parse_bool(os.environ.get('SHOW_HIT_MARKERS', 'true'))
SHOW_GHOST_RING = _parse_bool(os.environ.get('SHOW_GHOST_RING', 'true'))
ANIMATION_DURATION = float(os.environ.get('ANIMATION_DURATION', 0.2))

# Colors
BACKGROUND_COLOR = _parse_color(os.environ.get('BACKGROUND_COLOR', '20,20,30'))
TARGET_COLOR = _parse_color(os.environ.get('TARGET_COLOR', '255,255,255'))
HIT_MARKER_COLOR = _parse_color(os.environ.get('HIT_MARKER_COLOR', '100,255,100'))
MISS_MARKER_COLOR = _parse_color(os.environ.get('MISS_MARKER_COLOR', '255,80,80'))
GHOST_RING_COLOR = _parse_color(os.environ.get('GHOST_RING_COLOR', '60,60,80'))
