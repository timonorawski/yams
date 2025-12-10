"""
DuckTarget class for Duck Hunt game.

Wraps the base Target with duck-specific behavior:
- Duck color assignment
- Hit pause phase before falling
- Gravity-based falling animation

Note: Rendering is handled by skins (see game/skins/), not by DuckTarget.
"""

import random
from typing import Optional
from enum import Enum

from models import TargetData, Vector2D, TargetState
from .target import Target
from .sprites import DuckColor  # Just the enum, not the sprite manager


class DuckPhase(Enum):
    """Phase of a duck's lifecycle after being hit."""
    FLYING = "flying"       # Normal flight
    HIT_PAUSE = "hit_pause" # Just hit, showing hit sprite (2 seconds)
    FALLING = "falling"     # Falling down with gravity


class DuckTarget:
    """A duck target with hit/fall behavior.

    Wraps a Target and adds:
    - Duck color assignment (for skin rendering)
    - Hit pause phase before falling
    - Gravity-based falling animation

    Note: Rendering is handled externally by skins.
    """

    # Physics constants
    GRAVITY = 800.0  # pixels per second squared
    HIT_PAUSE_DURATION = 0.5  # seconds to show hit sprite before falling

    def __init__(
        self,
        data: TargetData,
        color: Optional[DuckColor] = None,
    ):
        """Initialize duck target.

        Args:
            data: Target data model
            color: Duck color (random if None)
        """
        self._target = Target(data)
        self._color = color or random.choice(list(DuckColor))
        self._phase = DuckPhase.FLYING
        self._hit_timer = 0.0
        self._fall_velocity = 0.0  # Separate y velocity for falling

    @property
    def data(self) -> TargetData:
        """Get the underlying TargetData model."""
        return self._target.data

    @property
    def is_active(self) -> bool:
        """Check if target can be hit (still flying)."""
        return self._target.is_active and self._phase == DuckPhase.FLYING

    @property
    def phase(self) -> DuckPhase:
        """Get current duck phase."""
        return self._phase

    @property
    def color(self) -> DuckColor:
        """Get duck color."""
        return self._color

    def contains_point(self, position: Vector2D) -> bool:
        """Check if a point is inside the target's bounding box."""
        return self._target.contains_point(position)

    def is_off_screen(self, width: float, height: float) -> bool:
        """Check if target has moved completely off screen."""
        # For falling ducks, only check if off bottom
        if self._phase == DuckPhase.FALLING:
            bounds = self._target.data.get_bounds()
            return bounds.top > height
        return self._target.is_off_screen(width, height)

    def hit(self) -> 'DuckTarget':
        """Mark duck as hit, starting the hit pause phase.

        Returns:
            New DuckTarget instance in HIT_PAUSE phase
        """
        # Create new target with HIT state and zero velocity
        hit_data = TargetData(
            position=self._target.data.position,
            velocity=Vector2D(x=0.0, y=0.0),
            size=self._target.data.size,
            state=TargetState.HIT
        )
        new_duck = DuckTarget(hit_data, self._color)
        new_duck._phase = DuckPhase.HIT_PAUSE
        new_duck._hit_timer = 0.0
        return new_duck

    def update(self, dt: float) -> 'DuckTarget':
        """Update duck position and phase state.

        Args:
            dt: Time delta in seconds

        Returns:
            New DuckTarget instance with updated state
        """
        if self._phase == DuckPhase.FLYING:
            # Normal flight - delegate to base Target
            new_target = self._target.update(dt)
            new_duck = DuckTarget(new_target.data, self._color)
            new_duck._phase = DuckPhase.FLYING
            return new_duck

        elif self._phase == DuckPhase.HIT_PAUSE:
            # Increment hit timer
            new_hit_timer = self._hit_timer + dt

            if new_hit_timer >= self.HIT_PAUSE_DURATION:
                # Transition to falling
                new_duck = DuckTarget(self._target.data, self._color)
                new_duck._phase = DuckPhase.FALLING
                new_duck._fall_velocity = 0.0
                return new_duck
            else:
                # Stay in hit pause
                new_duck = DuckTarget(self._target.data, self._color)
                new_duck._phase = DuckPhase.HIT_PAUSE
                new_duck._hit_timer = new_hit_timer
                return new_duck

        elif self._phase == DuckPhase.FALLING:
            # Apply gravity and update position
            new_fall_velocity = self._fall_velocity + self.GRAVITY * dt
            new_y = self._target.data.position.y + new_fall_velocity * dt

            new_data = TargetData(
                position=Vector2D(
                    x=self._target.data.position.x,
                    y=new_y
                ),
                velocity=Vector2D(x=0.0, y=new_fall_velocity),
                size=self._target.data.size,
                state=TargetState.HIT
            )

            new_duck = DuckTarget(new_data, self._color)
            new_duck._phase = DuckPhase.FALLING
            new_duck._fall_velocity = new_fall_velocity
            return new_duck

        return self

    def set_state(self, state: TargetState) -> 'DuckTarget':
        """Create new duck with updated state.

        Args:
            state: New state for the target

        Returns:
            New DuckTarget instance with updated state
        """
        new_target = self._target.set_state(state)
        new_duck = DuckTarget(new_target.data, self._color)
        new_duck._phase = self._phase
        new_duck._hit_timer = self._hit_timer
        new_duck._fall_velocity = self._fall_velocity
        return new_duck

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"DuckTarget({self._color.name}, {self._phase.name}, {self._target.data})"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return self.__str__()
