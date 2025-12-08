"""
FruitSlice - Configuration loader with pacing presets.

Supports multiple input device speeds from archery (slow) to blaster (fast).
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any

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

# Physics
GRAVITY = _get_float('GRAVITY', 400.0)  # pixels/second²

# Pacing presets - all timing parameters bundled together
@dataclass
class PacingPreset:
    """Timing parameters for a specific input device speed."""
    name: str
    spawn_interval: float      # Seconds between spawns
    arc_duration: float        # How long targets stay on screen
    max_targets: int           # Maximum simultaneous targets
    target_size: int           # Base target radius in pixels
    bomb_ratio: float          # Fraction of spawns that are bombs
    combo_window: float        # Seconds before combo resets


PACING_PRESETS: Dict[str, PacingPreset] = {
    'archery': PacingPreset(
        name='archery',
        spawn_interval=5.0,
        arc_duration=6.0,
        max_targets=2,
        target_size=70,
        bomb_ratio=0.10,
        combo_window=8.0,
    ),
    'throwing': PacingPreset(
        name='throwing',
        spawn_interval=2.0,
        arc_duration=4.0,
        max_targets=4,
        target_size=50,
        bomb_ratio=0.15,
        combo_window=3.0,
    ),
    'blaster': PacingPreset(
        name='blaster',
        spawn_interval=0.75,
        arc_duration=2.5,
        max_targets=6,
        target_size=40,
        bomb_ratio=0.25,
        combo_window=1.5,
    ),
}

# Default pacing
DEFAULT_PACING = os.getenv('DEFAULT_PACING', 'throwing')

# Scoring
BASE_FRUIT_POINTS = _get_int('BASE_FRUIT_POINTS', 10)
GOLDEN_FRUIT_POINTS = _get_int('GOLDEN_FRUIT_POINTS', 100)
GOLDEN_FRUIT_CHANCE = _get_float('GOLDEN_FRUIT_CHANCE', 0.05)
MAX_COMBO_MULTIPLIER = _get_int('MAX_COMBO_MULTIPLIER', 5)

# Multi-hit bonus (hitting multiple targets with one shot)
MULTI_HIT_MULTIPLIER = _get_float('MULTI_HIT_MULTIPLIER', 2.0)  # Each additional target doubles bonus

# Game rules
DEFAULT_LIVES = _get_int('DEFAULT_LIVES', 3)
MISS_TOLERANCE = _get_int('MISS_TOLERANCE', 3)  # Fruits that can escape before losing life

# Quiver/ammo support
DEFAULT_QUIVER_SIZE = _get_int('DEFAULT_QUIVER_SIZE', 0)  # 0 = unlimited
DEFAULT_RETRIEVAL_PAUSE = _get_int('DEFAULT_RETRIEVAL_PAUSE', 30)

# Difficulty progression (multipliers over time)
DIFFICULTY_RAMP_INTERVAL = _get_float('DIFFICULTY_RAMP_INTERVAL', 30.0)  # seconds
SPAWN_RATE_RAMP = _get_float('SPAWN_RATE_RAMP', 0.9)  # multiply spawn interval
SPEED_RAMP = _get_float('SPEED_RAMP', 1.1)  # multiply target speed
BOMB_RATIO_RAMP = _get_float('BOMB_RATIO_RAMP', 0.05)  # add to bomb ratio

# Visual
BACKGROUND_COLOR = (20, 15, 30)

# Target colors by type
FRUIT_COLORS = [
    (255, 100, 100),   # Red (apple)
    (255, 200, 50),    # Orange
    (255, 255, 100),   # Yellow (lemon)
    (100, 255, 100),   # Green (lime)
    (150, 100, 255),   # Purple (grape)
    (255, 150, 200),   # Pink (peach)
]
GOLDEN_COLOR = (255, 215, 0)
BOMB_COLOR = (40, 40, 40)
BOMB_GLOW_COLOR = (255, 50, 50)

# Effects
HIT_FLASH_DURATION = _get_float('HIT_FLASH_DURATION', 0.15)
TRAIL_LENGTH = _get_int('TRAIL_LENGTH', 5)
