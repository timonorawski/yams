"""
Trajectory-based Target for Duck Hunt game.

This module provides the TrajectoryTarget class which follows a predefined
trajectory path rather than using simple velocity-based movement. It supports
3D depth simulation with perspective scaling for size and rendering.

Examples:
    >>> from game.trajectory import TrajectoryRegistry
    >>> algo = TrajectoryRegistry.get("bezier_3d")
    >>> trajectory = algo.generate(config, 800, 600)
    >>> target = TrajectoryTarget(trajectory, initial_size=50.0)
    >>> target.update(0.016)  # Update for one frame
"""

from typing import Optional
import pygame
from models import Vector2D, TargetState

from game.trajectory.base import Trajectory


class TrajectoryTarget:
    """Target that follows a predefined trajectory path.

    This class represents a target that moves along a trajectory curve
    rather than using simple velocity-based physics. It tracks progress
    along the trajectory (parameter t from 0.0 to 1.0) and supports
    3D depth simulation with perspective scaling.

    Attributes:
        trajectory: The Trajectory instance this target follows
        initial_size: Base size before depth scaling
        state: Current target state (ALIVE, HIT, ESCAPED)
        elapsed_time: Total time elapsed since spawn
        progress: Current position along trajectory (0.0 to 1.0)

    Examples:
        >>> trajectory = get_some_trajectory()
        >>> target = TrajectoryTarget(trajectory, initial_size=50.0)
        >>> target.is_active
        True
        >>> target.update(0.5)  # Update by 0.5 seconds
        >>> target.progress
        0.25  # If trajectory duration is 2.0 seconds
    """

    def __init__(
        self,
        trajectory: Trajectory,
        initial_size: float = 40.0,
        state: TargetState = TargetState.ALIVE,
    ):
        """Initialize trajectory-based target.

        Args:
            trajectory: The Trajectory instance to follow
            initial_size: Base target size before depth scaling
            state: Initial target state (default: ALIVE)
        """
        self._trajectory = trajectory
        self._initial_size = initial_size
        self._state = state
        self._elapsed_time = 0.0
        self._spawn_time = 0.0  # Track when target was spawned

    @property
    def trajectory(self) -> Trajectory:
        """Get the trajectory this target follows."""
        return self._trajectory

    @property
    def initial_size(self) -> float:
        """Get the base size before depth scaling."""
        return self._initial_size

    @property
    def state(self) -> TargetState:
        """Get the current target state."""
        return self._state

    @property
    def elapsed_time(self) -> float:
        """Get total elapsed time since spawn."""
        return self._elapsed_time

    @property
    def progress(self) -> float:
        """Get current progress along trajectory (0.0 to 1.0)."""
        if self._trajectory.data.duration <= 0:
            return 1.0  # Instant trajectory

        t = self._elapsed_time / self._trajectory.data.duration
        return min(max(t, 0.0), 1.0)  # Clamp to [0.0, 1.0]

    @property
    def position(self) -> Vector2D:
        """Get current position along trajectory."""
        return self._trajectory.get_position(self.progress)

    @property
    def current_size(self) -> float:
        """Get current size with depth scaling applied."""
        depth_factor = self._trajectory.get_depth_factor(self.progress)
        return self._initial_size / depth_factor

    @property
    def is_active(self) -> bool:
        """Check if target is active (can be hit)."""
        return self._state == TargetState.ALIVE

    @property
    def is_complete(self) -> bool:
        """Check if target has completed its trajectory."""
        return self.progress >= 1.0

    def update(self, dt: float) -> 'TrajectoryTarget':
        """Update target progress along trajectory.

        Creates a new TrajectoryTarget instance with advanced progress.
        Target movement is determined by the trajectory, not velocity.

        Args:
            dt: Time delta in seconds

        Returns:
            New TrajectoryTarget instance with updated progress

        Examples:
            >>> target = TrajectoryTarget(trajectory, initial_size=50.0)
            >>> target.progress
            0.0
            >>> new_target = target.update(1.0)  # 1 second
            >>> new_target.progress  # If duration=2.0s
            0.5
        """
        # Create new instance with advanced time
        new_target = TrajectoryTarget(
            trajectory=self._trajectory,
            initial_size=self._initial_size,
            state=self._state,
        )
        new_target._elapsed_time = self._elapsed_time + dt
        new_target._spawn_time = self._spawn_time

        return new_target

    def set_state(self, state: TargetState) -> 'TrajectoryTarget':
        """Create new target with updated state.

        Args:
            state: New state for the target

        Returns:
            New TrajectoryTarget instance with updated state

        Examples:
            >>> target = TrajectoryTarget(trajectory)
            >>> hit_target = target.set_state(TargetState.HIT)
            >>> hit_target.state
            <TargetState.HIT: 'hit'>
        """
        new_target = TrajectoryTarget(
            trajectory=self._trajectory,
            initial_size=self._initial_size,
            state=state,
        )
        new_target._elapsed_time = self._elapsed_time
        new_target._spawn_time = self._spawn_time

        return new_target

    def contains_point(self, position: Vector2D) -> bool:
        """Check if a point is inside the target's bounding circle.

        Uses circular hit detection based on current size (with depth scaling).

        Args:
            position: The position to check

        Returns:
            True if position is inside target bounds

        Examples:
            >>> target = TrajectoryTarget(trajectory, initial_size=50.0)
            >>> target_pos = target.position
            >>> target.contains_point(target_pos)
            True
        """
        current_pos = self.position
        radius = self.current_size / 2.0

        # Calculate distance from target center
        dx = position.x - current_pos.x
        dy = position.y - current_pos.y
        distance_squared = dx * dx + dy * dy

        # Check if within circular bounds
        return distance_squared <= (radius * radius)

    def is_off_screen(self, width: float, height: float) -> bool:
        """Check if target has moved completely off screen.

        A target is considered off-screen if its bounding circle does not
        intersect with the screen area at all.

        Args:
            width: Screen width in pixels
            height: Screen height in pixels

        Returns:
            True if target is completely off screen

        Examples:
            >>> target = TrajectoryTarget(trajectory)
            >>> target.is_off_screen(800.0, 600.0)
            False  # Depends on trajectory position
        """
        pos = self.position
        radius = self.current_size / 2.0

        # Check if completely outside screen bounds
        if pos.x + radius < 0:  # Off left edge
            return True
        if pos.x - radius > width:  # Off right edge
            return True
        if pos.y + radius < 0:  # Off top edge
            return True
        if pos.y - radius > height:  # Off bottom edge
            return True

        return False

    def render(self, screen: pygame.Surface, color: Optional[tuple] = None) -> None:
        """Render the target on screen with depth-scaled size.

        Draws a circle representing the target. The size is automatically
        scaled based on depth simulation (targets farther away appear smaller).

        Args:
            screen: Pygame surface to draw on
            color: Optional RGB tuple for target color. If None, uses
                   state-based coloring (red for alive, gray for hit, etc.)

        Examples:
            >>> import pygame
            >>> pygame.init()  # doctest: +SKIP
            >>> screen = pygame.display.set_mode((800, 600))  # doctest: +SKIP
            >>> target = TrajectoryTarget(trajectory)
            >>> target.render(screen)  # doctest: +SKIP
        """
        # Default colors based on state if not provided
        if color is None:
            if self._state == TargetState.ALIVE:
                color = (255, 0, 0)  # Red for alive
            elif self._state == TargetState.HIT:
                color = (100, 100, 100)  # Gray for hit
            elif self._state == TargetState.ESCAPED:
                color = (150, 150, 0)  # Yellow-ish for escaped
            else:
                color = (128, 128, 128)  # Default gray

        pos = self.position
        radius = int(self.current_size / 2)

        # Don't render if too small or off screen
        if radius < 1:
            return

        # Draw circle at target center
        pygame.draw.circle(
            screen,
            color,
            (int(pos.x), int(pos.y)),
            radius
        )

        # Draw outline for better visibility
        if radius >= 2:  # Only draw outline if big enough
            pygame.draw.circle(
                screen,
                (0, 0, 0),  # Black outline
                (int(pos.x), int(pos.y)),
                radius,
                2  # Line width
            )

    def __str__(self) -> str:
        """String representation for debugging."""
        return (
            f"TrajectoryTarget(progress={self.progress:.2f}, "
            f"pos={self.position}, size={self.current_size:.1f}, "
            f"state={self._state})"
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return self.__str__()
