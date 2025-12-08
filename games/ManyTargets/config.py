"""
ManyTargets - Configuration loader.

Loads settings from .env file with sensible defaults.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from game directory
_env_path = Path(__file__).parent / '.env'
load_dotenv(_env_path)


def _get_bool(key: str, default: bool) -> bool:
    """Get boolean from environment."""
    val = os.getenv(key, str(default)).lower()
    return val in ('true', '1', 'yes')


def _get_int(key: str, default: int) -> int:
    """Get integer from environment."""
    return int(os.getenv(key, str(default)))


def _get_float(key: str, default: float) -> float:
    """Get float from environment."""
    return float(os.getenv(key, str(default)))


# Display
SCREEN_WIDTH = _get_int('SCREEN_WIDTH', 1280)
SCREEN_HEIGHT = _get_int('SCREEN_HEIGHT', 720)

# Target settings
DEFAULT_TARGET_COUNT = _get_int('DEFAULT_TARGET_COUNT', 15)
TARGET_RADIUS_SMALL = _get_int('TARGET_RADIUS_SMALL', 25)
TARGET_RADIUS_MEDIUM = _get_int('TARGET_RADIUS_MEDIUM', 40)
TARGET_RADIUS_LARGE = _get_int('TARGET_RADIUS_LARGE', 60)
MIN_TARGET_SPACING = _get_float('MIN_TARGET_SPACING', 1.5)

# Scoring
HIT_POINTS = _get_int('HIT_POINTS', 100)
MISS_PENALTY = _get_int('MISS_PENALTY', 50)
DUPLICATE_PENALTY = _get_int('DUPLICATE_PENALTY', 25)
REMAINING_PENALTY = _get_int('REMAINING_PENALTY', 25)
PERFECT_BONUS = _get_int('PERFECT_BONUS', 200)

# Progressive mode
DEFAULT_SHRINK_RATE = _get_float('DEFAULT_SHRINK_RATE', 0.9)
MIN_TARGET_SIZE = _get_int('MIN_TARGET_SIZE', 15)

# Timing
DEFAULT_TIME_LIMIT = _get_int('DEFAULT_TIME_LIMIT', 60)

# Visual
ANIMATION_DURATION = _get_float('ANIMATION_DURATION', 0.15)
SHOW_HIT_MARKERS = _get_bool('SHOW_HIT_MARKERS', True)

# Colors
BACKGROUND_COLOR = (30, 30, 35)
TARGET_COLOR = (255, 255, 255)
TARGET_FILL_COLOR = (40, 60, 100)
HIT_COLOR = (100, 255, 100)
HIT_MARKER_COLOR = (60, 120, 60)
MISS_COLOR = (255, 80, 80)
TIMER_COLOR_SAFE = (100, 200, 100)
TIMER_COLOR_WARNING = (255, 200, 50)
TIMER_COLOR_DANGER = (255, 80, 80)
