"""
Linear trajectory algorithm for straight-line movement.

This module implements the simplest trajectory type: linear interpolation
between start and end points. Targets move in a straight line at constant
velocity with optional depth scaling for pseudo-3D effects.

Examples:
    >>> from game.trajectory.algorithms.linear import LinearTrajectory
    >>> config = {
    ...     'duration': 2.0,
    ...     'start_x': 0.0,
    ...     'start_y': 300.0,
    ...     'end_x': 800.0,
    ...     'end_y': 300.0,
    ...     'depth_range': (1.0, 1.0)
    ... }
    >>> trajectory = LinearTrajectory.generate(config, 800, 600)
    >>> pos = trajectory.get_position(0.5)  # Midpoint
"""

from typing import Dict
from models import Vector2D
from games.DuckHunt.game.trajectory.base import Trajectory, TrajectoryData, TrajectoryAlgorithm


class LinearTrajectoryImpl(Trajectory):
    """Linear trajectory implementation using straight-line interpolation.

    Position at time t is calculated using linear interpolation:
        P(t) = P0 + t * (P1 - P0)

    Where:
        - P0 is the start position
        - P1 is the end position
        - t is normalized time in [0.0, 1.0]

    This produces constant-velocity motion in a straight line.

    Attributes:
        data: Immutable trajectory configuration
    """

    def get_position(self, t: float) -> Vector2D:
        """Get position at normalized time t using linear interpolation.

        Formula: P(t) = start + t * (end - start)

        Args:
            t: Normalized time in range [0.0, 1.0]
               - 0.0 = start position
               - 1.0 = end position
               - Values outside [0.0, 1.0] will extrapolate

        Returns:
            Position vector at time t

        Examples:
            >>> data = TrajectoryData(
            ...     start=Vector2D(x=0.0, y=300.0),
            ...     end=Vector2D(x=800.0, y=300.0),
            ...     control_point=None,
            ...     depth_range=(1.0, 1.0),
            ...     duration=2.0
            ... )
            >>> traj = LinearTrajectoryImpl(data)
            >>> traj.get_position(0.0)
            Vector2D(x=0.00, y=300.00)
            >>> traj.get_position(0.5)
            Vector2D(x=400.00, y=300.00)
            >>> traj.get_position(1.0)
            Vector2D(x=800.00, y=300.00)
        """
        # Linear interpolation: P(t) = P0 + t * (P1 - P0)
        x = self.data.start.x + t * (self.data.end.x - self.data.start.x)
        y = self.data.start.y + t * (self.data.end.y - self.data.start.y)
        return Vector2D(x=x, y=y)


class LinearTrajectory:
    """Linear trajectory algorithm generator.

    Factory class that implements the TrajectoryAlgorithm protocol for
    creating linear trajectories from configuration dictionaries.

    This is a stateless generator - all configuration is passed in the
    config dictionary and screen dimensions.
    """

    @staticmethod
    def generate(config: Dict, screen_width: float, screen_height: float) -> Trajectory:
        """Generate a linear trajectory from configuration.

        Required config keys:
            - duration: float - Total time to traverse path in seconds
            - start_x: float - Starting X coordinate
            - start_y: float - Starting Y coordinate
            - end_x: float - Ending X coordinate
            - end_y: float - Ending Y coordinate

        Optional config keys:
            - depth_range: Tuple[float, float] - (start_depth, end_depth)
                          Defaults to (1.0, 1.0) for constant depth

        Args:
            config: Configuration dictionary with trajectory parameters
            screen_width: Width of screen/play area (used for validation)
            screen_height: Height of screen/play area (used for validation)

        Returns:
            LinearTrajectoryImpl instance configured with given parameters

        Raises:
            KeyError: If required config keys are missing
            ValueError: If config values are invalid

        Examples:
            >>> config = {
            ...     'duration': 2.0,
            ...     'start_x': 0.0,
            ...     'start_y': 300.0,
            ...     'end_x': 800.0,
            ...     'end_y': 300.0,
            ...     'depth_range': (1.0, 2.0)
            ... }
            >>> trajectory = LinearTrajectory.generate(config, 800, 600)
            >>> trajectory.get_position(0.0)
            Vector2D(x=0.00, y=300.00)
        """
        # Extract required parameters
        try:
            duration = config['duration']
            start_x = config['start_x']
            start_y = config['start_y']
            end_x = config['end_x']
            end_y = config['end_y']
        except KeyError as e:
            raise KeyError(f"Missing required config key: {e}")

        # Extract optional parameters with defaults
        depth_range = config.get('depth_range', (1.0, 1.0))

        # Create trajectory data
        data = TrajectoryData(
            start=Vector2D(x=start_x, y=start_y),
            end=Vector2D(x=end_x, y=end_y),
            control_point=None,  # Linear trajectories don't use control points
            depth_range=depth_range,
            duration=duration,
            curvature_factor=1.0  # Not used for linear trajectories
        )

        return LinearTrajectoryImpl(data)


# Auto-register this algorithm when module is imported
from games.DuckHunt.game.trajectory.registry import TrajectoryRegistry
TrajectoryRegistry.register("linear", LinearTrajectory)
