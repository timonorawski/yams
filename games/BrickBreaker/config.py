"""Configuration for BrickBreaker game.

Contains screen dimensions, physics constants, pacing presets,
and color definitions.
"""

from dataclasses import dataclass
from typing import Dict, Tuple

# Screen dimensions (default, can be overridden)
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720

# Physics constants
BALL_DEFAULT_SPEED: float = 300.0  # pixels/second
BALL_MAX_SPEED: float = 600.0
BALL_SPEED_INCREASE_PER_HIT: float = 5.0
BALL_RADIUS: float = 10.0

PADDLE_DEFAULT_WIDTH: float = 120.0
PADDLE_HEIGHT: float = 20.0
PADDLE_DEFAULT_SPEED: float = 500.0
PADDLE_Y_POSITION: float = 0.9  # 90% down the screen (normalized)

# Brick grid defaults
BRICK_DEFAULT_WIDTH: float = 70.0
BRICK_DEFAULT_HEIGHT: float = 25.0
GRID_OFFSET_X: float = 65.0
GRID_OFFSET_Y: float = 80.0

# Visual
BACKGROUND_COLOR: Tuple[int, int, int] = (20, 20, 30)

# Brick colors mapping
BRICK_COLORS: Dict[str, Tuple[int, int, int]] = {
    'red': (255, 100, 100),
    'blue': (100, 100, 255),
    'green': (100, 255, 100),
    'yellow': (255, 255, 100),
    'orange': (255, 180, 100),
    'purple': (200, 100, 255),
    'cyan': (100, 255, 255),
    'gray': (150, 150, 150),
    'silver': (200, 200, 200),
    'gold': (255, 215, 0),
    'white': (255, 255, 255),
}


@dataclass
class PacingPreset:
    """Pacing configuration for different input device speeds.

    Adjusts timings based on how fast players can shoot:
    - archery: 3-8s cycle (slow, deliberate)
    - throwing: 1-2s cycle (medium, natural throwing speed)
    - blaster: 0.3-0.5s cycle (fast, rapid-fire)
    """

    name: str
    ball_speed: float       # Base ball speed in pixels/second
    paddle_speed: float     # Paddle movement speed
    paddle_width: float     # Paddle width (wider = easier)


PACING_PRESETS: Dict[str, PacingPreset] = {
    'archery': PacingPreset(
        name='archery',
        ball_speed=200.0,       # Slow ball
        paddle_speed=400.0,
        paddle_width=150.0,     # Wide paddle
    ),
    'throwing': PacingPreset(
        name='throwing',
        ball_speed=300.0,       # Medium ball
        paddle_speed=500.0,
        paddle_width=120.0,     # Medium paddle
    ),
    'blaster': PacingPreset(
        name='blaster',
        ball_speed=400.0,       # Fast ball
        paddle_speed=600.0,
        paddle_width=100.0,     # Narrow paddle
    ),
}


def get_pacing_preset(name: str) -> PacingPreset:
    """Get pacing preset by name, with fallback to throwing."""
    return PACING_PRESETS.get(name, PACING_PRESETS['throwing'])
