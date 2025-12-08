"""
LoveOMeter game configuration.

Configuration constants and pacing presets for the Love-O-Meter game.
"""
from dataclasses import dataclass
from typing import Dict

# Screen dimensions
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

# Colors
BACKGROUND_COLOR = (20, 10, 30)  # Dark purple-ish
METER_EMPTY_COLOR = (60, 60, 80)
METER_FILL_COLOR = (255, 50, 100)  # Hot pink
METER_GLOW_COLOR = (255, 100, 150)
TARGET_COLOR = (255, 80, 120)
TARGET_OUTLINE_COLOR = (255, 255, 255)
HIT_FLASH_COLOR = (255, 255, 200)

# Meter settings
METER_X = 100  # Left edge of meter
METER_Y = 100  # Top of meter
METER_WIDTH = 60
METER_HEIGHT = 520
METER_BORDER = 4

# Target defaults
DEFAULT_TARGET_SIZE = 80
MIN_TARGET_SIZE = 25
TARGET_SHRINK_RATE = 2.0  # pixels per second

# Movement patterns
MOVEMENT_DRIFT = "drift"
MOVEMENT_ORBIT = "orbit"
MOVEMENT_RANDOM = "random"
MOVEMENT_BOUNCE = "bounce"

# Game modes
MODE_SPRINT = "sprint"      # Fill meter completely
MODE_ENDURANCE = "endurance"  # Keep above threshold
MODE_PRESSURE = "pressure"   # Drain increases until fail
MODE_ADAPTIVE = "adaptive"   # Difficulty responds to performance

# Audio
AUDIO_ENABLED = True


@dataclass
class PacingPreset:
    """Pacing preset for different input devices."""
    name: str
    # Meter settings
    initial_fill: float       # 0.0 to 1.0
    drain_rate: float         # per second
    fill_per_hit: float       # amount added per hit
    # Target settings
    target_size: int          # initial radius
    target_min_size: int      # minimum radius
    shrink_rate: float        # pixels per second
    # Movement
    movement_enabled: bool
    movement_speed: float     # pixels per second
    # Difficulty scaling
    drain_increase_rate: float   # per second
    shrink_increase_rate: float  # per second


# Pacing presets optimized for different input devices
PACING_PRESETS: Dict[str, PacingPreset] = {
    'archery': PacingPreset(
        name='archery',
        initial_fill=0.4,
        drain_rate=0.025,      # Slow drain - archery is slow
        fill_per_hit=0.12,     # Good reward per hit
        target_size=120,       # Larger target
        target_min_size=40,
        shrink_rate=1.0,       # Slow shrink
        movement_enabled=True,
        movement_speed=25,     # Slow movement
        drain_increase_rate=0.001,
        shrink_increase_rate=0.05,
    ),
    'throwing': PacingPreset(
        name='throwing',
        initial_fill=0.35,
        drain_rate=0.045,      # Medium drain
        fill_per_hit=0.10,
        target_size=90,
        target_min_size=35,
        shrink_rate=1.5,
        movement_enabled=True,
        movement_speed=40,
        drain_increase_rate=0.0015,
        shrink_increase_rate=0.08,
    ),
    'blaster': PacingPreset(
        name='blaster',
        initial_fill=0.3,
        drain_rate=0.10,       # Fast drain - blaster is fast
        fill_per_hit=0.06,     # Less per hit (more hits expected)
        target_size=70,
        target_min_size=30,
        shrink_rate=2.5,
        movement_enabled=True,
        movement_speed=70,
        drain_increase_rate=0.003,
        shrink_increase_rate=0.15,
    ),
}

DEFAULT_PACING = 'throwing'
