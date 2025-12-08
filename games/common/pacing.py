"""
Common pacing presets for AMS-integrated games.

Provides base classes and utilities for device-speed-aware timing.
"""

from dataclasses import dataclass
from typing import Dict, TypeVar, Optional

T = TypeVar('T')


@dataclass
class BasePacingPreset:
    """
    Base pacing preset with common timing parameters.

    Games should extend this with game-specific parameters.
    """
    name: str
    spawn_interval: float      # Seconds between spawns
    combo_window: float        # Seconds before combo resets


# Standard pacing tiers based on input device speed
PACING_TIERS = {
    'archery': {
        'description': 'Slow (3-8s cycle): Bows, crossbows',
        'spawn_interval_base': 5.0,
        'combo_window_base': 8.0,
    },
    'throwing': {
        'description': 'Medium (1-2s cycle): Darts, balls, axes',
        'spawn_interval_base': 2.0,
        'combo_window_base': 3.0,
    },
    'blaster': {
        'description': 'Fast (0.3-0.5s cycle): Nerf, laser pointer',
        'spawn_interval_base': 0.75,
        'combo_window_base': 1.5,
    },
}


def get_pacing_preset(
    presets: Dict[str, T],
    name: str,
    default: str = 'throwing'
) -> T:
    """
    Get a pacing preset by name with fallback.

    Args:
        presets: Dict mapping preset names to preset objects
        name: Requested preset name
        default: Fallback preset name if requested not found

    Returns:
        The preset object
    """
    if name in presets:
        return presets[name]
    if default in presets:
        return presets[default]
    # Return first available
    return next(iter(presets.values()))


def get_pacing_names() -> list:
    """Get list of standard pacing tier names."""
    return list(PACING_TIERS.keys())


def scale_for_pacing(
    base_value: float,
    pacing: str,
    archery_multiplier: float = 2.5,
    blaster_multiplier: float = 0.4
) -> float:
    """
    Scale a timing value based on pacing tier.

    Useful for games that want to derive all timing from a single base value.

    Args:
        base_value: The base timing value (for 'throwing' tier)
        pacing: Pacing tier name
        archery_multiplier: Multiplier for archery (slower)
        blaster_multiplier: Multiplier for blaster (faster)

    Returns:
        Scaled value appropriate for the pacing tier
    """
    multipliers = {
        'archery': archery_multiplier,
        'throwing': 1.0,
        'blaster': blaster_multiplier,
    }
    return base_value * multipliers.get(pacing, 1.0)
