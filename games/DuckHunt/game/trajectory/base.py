"""
Base classes and protocols for trajectory algorithms.

This module defines the core interfaces and data structures for trajectory
generation in the Duck Hunt game. Trajectories define how targets move across
the screen, supporting both simple linear motion and complex curved paths with
simulated 3D depth.

Examples:
    >>> from game.trajectory.base import TrajectoryData, Trajectory
    >>> from models import Vector2D
    >>> data = TrajectoryData(
    ...     start=Vector2D(x=0.0, y=300.0),
    ...     end=Vector2D(x=800.0, y=300.0),
    ...     control_point=None,
    ...     depth_range=(1.0, 1.0),
    ...     duration=2.0
    ... )
    >>> trajectory = Trajectory(data)
    >>> pos = trajectory.get_position(0.5)  # Position at 50% progress
"""

from typing import Protocol, Optional, Tuple
from pydantic import BaseModel, field_validator, ConfigDict
from models import Vector2D


class TrajectoryData(BaseModel):
    """Immutable data describing a trajectory path.

    Encapsulates all parameters needed to define how a target moves through
    space, including start/end positions, optional control points for curves,
    depth simulation for pseudo-3D effects, and timing information.

    Attributes:
        start: Starting position in screen coordinates
        end: Ending position in screen coordinates
        control_point: Optional control point for Bezier curves (None for linear)
        depth_range: Tuple of (start_distance, end_distance) for perspective scaling
                    - Values > 1.0 represent objects further away (smaller)
                    - Values < 1.0 represent objects closer (larger)
                    - (1.0, 1.0) means constant depth (no scaling)
                    - (1.0, 3.0) means moving away from viewer
                    - (3.0, 1.0) means approaching viewer
        duration: Total time to traverse the path in seconds (positive)
        curvature_factor: Controls the intensity of curve (1.0 = standard, >1.0 = more curved)

    Examples:
        >>> # Linear trajectory at constant depth
        >>> linear = TrajectoryData(
        ...     start=Vector2D(x=0.0, y=300.0),
        ...     end=Vector2D(x=800.0, y=300.0),
        ...     control_point=None,
        ...     depth_range=(1.0, 1.0),
        ...     duration=2.0
        ... )
        >>>
        >>> # Curved trajectory moving away from viewer
        >>> curved = TrajectoryData(
        ...     start=Vector2D(x=100.0, y=400.0),
        ...     end=Vector2D(x=700.0, y=400.0),
        ...     control_point=Vector2D(x=400.0, y=100.0),  # Apex of arc
        ...     depth_range=(1.0, 3.0),  # Flying away
        ...     duration=3.0,
        ...     curvature_factor=1.5
        ... )
    """
    start: Vector2D
    end: Vector2D
    control_point: Optional[Vector2D] = None
    depth_range: Tuple[float, float]
    duration: float
    curvature_factor: float = 1.0

    @field_validator('duration')
    @classmethod
    def validate_positive_duration(cls, v: float) -> float:
        """Validate duration is positive.

        Args:
            v: Duration value to validate

        Returns:
            Validated duration value

        Raises:
            ValueError: If duration is not positive
        """
        if v <= 0:
            raise ValueError(f'Duration must be positive, got {v}')
        return v

    @field_validator('depth_range')
    @classmethod
    def validate_depth_range(cls, v: Tuple[float, float]) -> Tuple[float, float]:
        """Validate depth range values are positive.

        Args:
            v: Depth range tuple to validate

        Returns:
            Validated depth range

        Raises:
            ValueError: If any depth value is not positive
        """
        start_depth, end_depth = v
        if start_depth <= 0 or end_depth <= 0:
            raise ValueError(f'Depth values must be positive, got {v}')
        return v

    @field_validator('curvature_factor')
    @classmethod
    def validate_positive_curvature(cls, v: float) -> float:
        """Validate curvature factor is positive.

        Args:
            v: Curvature factor to validate

        Returns:
            Validated curvature factor

        Raises:
            ValueError: If curvature factor is not positive
        """
        if v <= 0:
            raise ValueError(f'Curvature factor must be positive, got {v}')
        return v

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """String representation for debugging."""
        return (f"TrajectoryData(start={self.start}, end={self.end}, "
                f"depth={self.depth_range}, duration={self.duration:.2f}s)")


class Trajectory:
    """Represents a trajectory path that targets follow.

    Provides methods to query position and depth at any point along the
    trajectory. The trajectory is parameterized by time t in range [0.0, 1.0]
    where 0.0 is the start and 1.0 is the end.

    This is an abstract base class that should be subclassed by specific
    trajectory algorithm implementations.

    Attributes:
        data: Immutable trajectory configuration data

    Examples:
        >>> data = TrajectoryData(
        ...     start=Vector2D(x=0.0, y=300.0),
        ...     end=Vector2D(x=800.0, y=300.0),
        ...     control_point=None,
        ...     depth_range=(1.0, 1.0),
        ...     duration=2.0
        ... )
        >>> trajectory = Trajectory(data)
        >>> pos_start = trajectory.get_position(0.0)  # Start position
        >>> pos_mid = trajectory.get_position(0.5)    # Midpoint
        >>> pos_end = trajectory.get_position(1.0)    # End position
        >>> depth = trajectory.get_depth_factor(0.5)  # Depth at midpoint
    """

    def __init__(self, data: TrajectoryData):
        """Initialize trajectory with configuration data.

        Args:
            data: Immutable trajectory configuration
        """
        self.data = data

    def get_position(self, t: float) -> Vector2D:
        """Get position at normalized time t.

        Must be implemented by subclasses to define specific trajectory behavior.

        Args:
            t: Normalized time in range [0.0, 1.0]
               - 0.0 = start of trajectory
               - 1.0 = end of trajectory
               - Values outside [0.0, 1.0] may extrapolate

        Returns:
            Position vector at time t

        Raises:
            NotImplementedError: If called on base class
        """
        raise NotImplementedError("Subclasses must implement get_position()")

    def get_depth_factor(self, t: float) -> float:
        """Get distance factor at time t for perspective scaling.

        Linear interpolation between start and end depth values.
        This value is used to scale target size for pseudo-3D effect:
        - Factor = 1.0: normal size (no scaling)
        - Factor > 1.0: target appears further away (scaled down)
        - Factor < 1.0: target appears closer (scaled up)

        Args:
            t: Normalized time in range [0.0, 1.0]

        Returns:
            Depth factor for perspective scaling

        Examples:
            >>> # Target moving away from viewer
            >>> data = TrajectoryData(
            ...     start=Vector2D(x=0.0, y=0.0),
            ...     end=Vector2D(x=100.0, y=0.0),
            ...     control_point=None,
            ...     depth_range=(1.0, 3.0),
            ...     duration=2.0
            ... )
            >>> traj = Trajectory(data)
            >>> traj.get_depth_factor(0.0)  # At start
            1.0
            >>> traj.get_depth_factor(0.5)  # Halfway
            2.0
            >>> traj.get_depth_factor(1.0)  # At end
            3.0
        """
        start_depth, end_depth = self.data.depth_range
        # Linear interpolation: depth(t) = start + t * (end - start)
        return start_depth + t * (end_depth - start_depth)


class TrajectoryAlgorithm(Protocol):
    """Protocol defining the interface for trajectory generation algorithms.

    Any trajectory algorithm must implement this protocol to be usable
    by the trajectory registry system. Algorithms are stateless and should
    be pure functions of their configuration.

    Examples:
        >>> class MyAlgorithm:
        ...     @staticmethod
        ...     def generate(config: dict, screen_width: float, screen_height: float) -> Trajectory:
        ...         # Implementation here
        ...         pass
        >>>
        >>> from game.trajectory.registry import TrajectoryRegistry
        >>> TrajectoryRegistry.register("my_algorithm", MyAlgorithm)
    """

    @staticmethod
    def generate(config: dict, screen_width: float, screen_height: float) -> Trajectory:
        """Generate a trajectory from configuration parameters.

        Takes a configuration dictionary with algorithm-specific parameters
        and screen dimensions, and returns a configured Trajectory instance.

        Args:
            config: Dictionary of algorithm-specific configuration parameters.
                   Common keys might include:
                   - 'duration': trajectory duration in seconds
                   - 'depth_range': tuple of (start_depth, end_depth)
                   - 'start_x', 'start_y': starting position
                   - 'end_x', 'end_y': ending position
                   Additional keys depend on the specific algorithm.
            screen_width: Width of the screen/play area in pixels
            screen_height: Height of the screen/play area in pixels

        Returns:
            Configured Trajectory instance ready for use

        Raises:
            ValueError: If configuration is invalid or missing required keys
        """
        ...
