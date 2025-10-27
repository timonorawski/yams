"""
Target class for Duck Hunt game.

This module provides the Target class which wraps TargetData in an immutable,
functional style. All state updates create new Target instances rather than
mutating existing ones.
"""

from typing import Optional
import pygame
from models import TargetData, Vector2D, TargetState


class Target:
    """Immutable target wrapper with game logic.

    This class encapsulates a TargetData model and provides methods for
    target behavior like movement, hit detection, and rendering. Following
    functional programming principles, all state-modifying operations return
    new Target instances rather than mutating the current one.

    Attributes:
        data: The underlying TargetData model (immutable)

    Examples:
        >>> from models import Vector2D, TargetState
        >>> target_data = TargetData(
        ...     position=Vector2D(x=100.0, y=200.0),
        ...     velocity=Vector2D(x=50.0, y=0.0),
        ...     size=40.0,
        ...     state=TargetState.ALIVE
        ... )
        >>> target = Target(target_data)
        >>> target.is_active
        True
        >>> new_target = target.update(dt=0.1)  # Returns new instance
        >>> new_target.data.position.x
        105.0
    """

    def __init__(self, data: TargetData):
        """Initialize target with data model.

        Args:
            data: TargetData model containing target state
        """
        self._data = data

    @property
    def data(self) -> TargetData:
        """Get the underlying TargetData model.

        Returns:
            The immutable TargetData model
        """
        return self._data

    @property
    def is_active(self) -> bool:
        """Check if target is active (can be hit).

        Returns:
            True if target state is ALIVE
        """
        return self._data.is_active

    def update(self, dt: float) -> 'Target':
        """Update target position based on velocity.

        Creates a new Target instance with updated position based on
        velocity and elapsed time.

        Args:
            dt: Time delta in seconds

        Returns:
            New Target instance with updated position

        Examples:
            >>> from models import Vector2D, TargetState, TargetData
            >>> data = TargetData(
            ...     position=Vector2D(x=100.0, y=200.0),
            ...     velocity=Vector2D(x=50.0, y=-25.0),
            ...     size=40.0,
            ...     state=TargetState.ALIVE
            ... )
            >>> target = Target(data)
            >>> new_target = target.update(dt=1.0)
            >>> new_target.data.position.x
            150.0
            >>> new_target.data.position.y
            175.0
        """
        new_position = Vector2D(
            x=self._data.position.x + self._data.velocity.x * dt,
            y=self._data.position.y + self._data.velocity.y * dt
        )

        new_data = TargetData(
            position=new_position,
            velocity=self._data.velocity,
            size=self._data.size,
            state=self._data.state
        )

        return Target(new_data)

    def contains_point(self, position: Vector2D) -> bool:
        """Check if a point is inside the target's bounding box.

        Args:
            position: The position to check

        Returns:
            True if position is inside target bounds

        Examples:
            >>> from models import Vector2D, TargetState, TargetData
            >>> data = TargetData(
            ...     position=Vector2D(x=100.0, y=100.0),
            ...     velocity=Vector2D(x=0.0, y=0.0),
            ...     size=40.0,
            ...     state=TargetState.ALIVE
            ... )
            >>> target = Target(data)
            >>> target.contains_point(Vector2D(x=100.0, y=100.0))
            True
            >>> target.contains_point(Vector2D(x=200.0, y=200.0))
            False
        """
        bounds = self._data.get_bounds()
        return bounds.contains_point(position)

    def is_off_screen(self, width: float, height: float) -> bool:
        """Check if target has moved completely off screen.

        A target is considered off-screen if its bounding box does not
        intersect with the screen area at all.

        Args:
            width: Screen width in pixels
            height: Screen height in pixels

        Returns:
            True if target is completely off screen

        Examples:
            >>> from models import Vector2D, TargetState, TargetData
            >>> data = TargetData(
            ...     position=Vector2D(x=-50.0, y=100.0),
            ...     velocity=Vector2D(x=0.0, y=0.0),
            ...     size=40.0,
            ...     state=TargetState.ALIVE
            ... )
            >>> target = Target(data)
            >>> target.is_off_screen(800.0, 600.0)
            True
            >>> data2 = TargetData(
            ...     position=Vector2D(x=100.0, y=100.0),
            ...     velocity=Vector2D(x=0.0, y=0.0),
            ...     size=40.0,
            ...     state=TargetState.ALIVE
            ... )
            >>> target2 = Target(data2)
            >>> target2.is_off_screen(800.0, 600.0)
            False
        """
        bounds = self._data.get_bounds()

        # Check if completely outside screen bounds
        if bounds.right < 0:  # Off left edge
            return True
        if bounds.left > width:  # Off right edge
            return True
        if bounds.bottom < 0:  # Off top edge
            return True
        if bounds.top > height:  # Off bottom edge
            return True

        return False

    def set_state(self, state: TargetState) -> 'Target':
        """Create new target with updated state.

        Args:
            state: New state for the target

        Returns:
            New Target instance with updated state

        Examples:
            >>> from models import Vector2D, TargetState, TargetData
            >>> data = TargetData(
            ...     position=Vector2D(x=100.0, y=100.0),
            ...     velocity=Vector2D(x=0.0, y=0.0),
            ...     size=40.0,
            ...     state=TargetState.ALIVE
            ... )
            >>> target = Target(data)
            >>> hit_target = target.set_state(TargetState.HIT)
            >>> hit_target.data.state
            <TargetState.HIT: 'hit'>
            >>> target.data.state  # Original unchanged
            <TargetState.ALIVE: 'alive'>
        """
        new_data = TargetData(
            position=self._data.position,
            velocity=self._data.velocity,
            size=self._data.size,
            state=state
        )
        return Target(new_data)

    def render(self, screen: pygame.Surface, color: Optional[tuple] = None) -> None:
        """Render the target on screen.

        Draws a simple circle representing the target. The color can be
        customized or will default based on target state.

        Args:
            screen: Pygame surface to draw on
            color: Optional RGB tuple for target color. If None, uses
                   state-based coloring (red for alive, gray for hit, etc.)

        Examples:
            >>> import pygame
            >>> pygame.init()  # doctest: +SKIP
            >>> screen = pygame.display.set_mode((800, 600))  # doctest: +SKIP
            >>> from models import Vector2D, TargetState, TargetData
            >>> data = TargetData(
            ...     position=Vector2D(x=100.0, y=100.0),
            ...     velocity=Vector2D(x=0.0, y=0.0),
            ...     size=40.0,
            ...     state=TargetState.ALIVE
            ... )
            >>> target = Target(data)
            >>> target.render(screen)  # doctest: +SKIP
        """
        # Default colors based on state if not provided
        if color is None:
            if self._data.state == TargetState.ALIVE:
                color = (255, 0, 0)  # Red for alive
            elif self._data.state == TargetState.HIT:
                color = (100, 100, 100)  # Gray for hit
            elif self._data.state == TargetState.ESCAPED:
                color = (150, 150, 0)  # Yellow-ish for escaped
            else:
                color = (128, 128, 128)  # Default gray

        # Draw circle at target center
        pygame.draw.circle(
            screen,
            color,
            (int(self._data.position.x), int(self._data.position.y)),
            int(self._data.size / 2)
        )

        # Draw outline for better visibility
        pygame.draw.circle(
            screen,
            (0, 0, 0),  # Black outline
            (int(self._data.position.x), int(self._data.position.y)),
            int(self._data.size / 2),
            2  # Line width
        )

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"Target({self._data})"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return self.__str__()
