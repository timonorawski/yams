"""Configuration for Containment game."""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

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


# Display settings
SCREEN_WIDTH = _get_int('SCREEN_WIDTH', 1280)
SCREEN_HEIGHT = _get_int('SCREEN_HEIGHT', 720)

# Colors (defaults, will be overridden by palette)
BACKGROUND_COLOR = (20, 20, 30)
BALL_COLOR = (255, 220, 100)
DEFLECTOR_COLOR = (100, 200, 255)
GAP_COLOR = (255, 80, 80)
WALL_COLOR = (60, 60, 80)
HUD_COLOR = (200, 200, 200)

# Direct hit penalty
HIT_SPEED_MULTIPLIER = 1.25  # Ball speeds up by 25% on direct hit
HIT_TOLERANCE = 5.0  # Extra pixels for hit detection


# Pacing presets (device speed)
@dataclass
class PacingPreset:
    """Pacing configuration for different input devices."""
    name: str
    ball_speed: float         # Base ball speed in pixels/second
    gap_width: float          # Gap width in pixels
    gap_count: int            # Number of gaps
    ball_radius: float        # Ball size
    deflector_length: float   # Length of each deflector
    quiver_size: int          # Default shots before retrieval (0 = unlimited)


PACING_PRESETS: Dict[str, PacingPreset] = {
    'archery': PacingPreset(
        name='archery',
        ball_speed=80,
        gap_width=180,
        gap_count=2,
        ball_radius=25,
        deflector_length=80,
        quiver_size=6,
    ),
    'throwing': PacingPreset(
        name='throwing',
        ball_speed=150,
        gap_width=140,
        gap_count=3,
        ball_radius=20,
        deflector_length=60,
        quiver_size=12,
    ),
    'blaster': PacingPreset(
        name='blaster',
        ball_speed=280,
        gap_width=100,
        gap_count=4,
        ball_radius=15,
        deflector_length=40,
        quiver_size=0,  # Unlimited
    ),
}


# Tempo presets (game intensity - independent of pacing)
@dataclass
class TempoPreset:
    """Tempo configuration for game intensity."""
    name: str
    ball_speed_multiplier: float  # Applied on top of pacing speed
    gap_count_modifier: int       # Added to pacing gap count
    ai_level: str                 # Default AI behavior


TEMPO_PRESETS: Dict[str, TempoPreset] = {
    'zen': TempoPreset(
        name='zen',
        ball_speed_multiplier=0.6,
        gap_count_modifier=-1,
        ai_level='dumb',
    ),
    'mid': TempoPreset(
        name='mid',
        ball_speed_multiplier=1.0,
        gap_count_modifier=0,
        ai_level='dumb',
    ),
    'wild': TempoPreset(
        name='wild',
        ball_speed_multiplier=1.5,
        gap_count_modifier=1,
        ai_level='reactive',
    ),
}


def get_pacing_preset(name: str) -> PacingPreset:
    """Get pacing preset by name."""
    return PACING_PRESETS.get(name, PACING_PRESETS['throwing'])


def get_tempo_preset(name: str) -> TempoPreset:
    """Get tempo preset by name."""
    return TEMPO_PRESETS.get(name, TEMPO_PRESETS['mid'])
