"""
GrowingTargets - Configuration loader.

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

# Target spawning
DEFAULT_SPAWN_RATE = _get_float('DEFAULT_SPAWN_RATE', 1.5)  # seconds between spawns
MAX_TARGETS = _get_int('MAX_TARGETS', 5)  # max simultaneous targets
SPAWN_MARGIN = _get_int('SPAWN_MARGIN', 100)  # keep targets away from edges

# Target sizing
START_SIZE = _get_int('START_SIZE', 10)  # initial radius
MAX_SIZE = _get_int('MAX_SIZE', 120)  # target expires at this radius
GROWTH_RATE = _get_float('GROWTH_RATE', 40.0)  # pixels per second

# Scoring
# Score = BASE_POINTS * (MAX_SIZE / current_size)
# So hitting at start_size gives BASE_POINTS * 12 = 1200
# Hitting at max_size gives BASE_POINTS * 1 = 100
BASE_POINTS = _get_int('BASE_POINTS', 100)
MISS_PENALTY = _get_int('MISS_PENALTY', 200)  # penalty for clicking empty space
EXPIRE_PENALTY = _get_int('EXPIRE_PENALTY', 100)  # penalty when target expires

# Game rules
DEFAULT_LIVES = _get_int('DEFAULT_LIVES', 3)  # 0 = unlimited
LIVES_LOST_ON_MISS = _get_bool('LIVES_LOST_ON_MISS', True)
LIVES_LOST_ON_EXPIRE = _get_bool('LIVES_LOST_ON_EXPIRE', True)

# Visual
BACKGROUND_COLOR = (20, 20, 25)
TARGET_OUTLINE_COLOR = (255, 255, 255)
TARGET_FILL_SMALL = (100, 255, 100)  # Green when small (high value)
TARGET_FILL_MEDIUM = (255, 255, 100)  # Yellow when medium
TARGET_FILL_LARGE = (255, 100, 100)  # Red when large (low value)
HIT_FLASH_COLOR = (255, 255, 255)
MISS_COLOR = (255, 60, 60)
EXPIRE_COLOR = (100, 100, 100)
