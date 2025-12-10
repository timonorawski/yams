"""
Base class for DuckHunt game skins.

A skin provides the visual representation and audio for game elements
without affecting game logic. Skins are responsible for:
- Rendering targets (sprites, shapes, etc.)
- Playing sound effects (hit, miss, spawn)
- Managing animations

Games select a skin via the --skin CLI argument.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from ..duck_target import DuckTarget


class GameSkin(ABC):
    """Base class for game skins (visuals + audio).

    Subclasses implement render_target() and optionally override
    sound methods and update() for animations.
    """

    NAME: str = "base"
    DESCRIPTION: str = "Base skin"

    @abstractmethod
    def render_target(self, target: 'DuckTarget', screen: pygame.Surface) -> None:
        """Render a target to the screen.

        Args:
            target: The DuckTarget to render
            screen: Pygame surface to draw on
        """
        pass

    def update(self, dt: float) -> None:
        """Update skin state (animations, timers, etc.).

        Args:
            dt: Delta time in seconds
        """
        pass

    def play_hit_sound(self) -> None:
        """Play sound when a target is hit."""
        pass

    def play_miss_sound(self) -> None:
        """Play sound when a shot misses."""
        pass

    def play_spawn_sound(self) -> None:
        """Play sound when a target spawns."""
        pass

    def play_escape_sound(self) -> None:
        """Play sound when a target escapes."""
        pass
