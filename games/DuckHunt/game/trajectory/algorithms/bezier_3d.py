"""
Bezier curve trajectory with 3D depth simulation.

This module implements quadratic Bezier curve trajectories with perspective
scaling to simulate 3D depth. Targets follow a curved path (like a duck flying
in an arc) while appearing to move closer or further away from the viewer.

The quadratic Bezier curve uses three control points:
- P0: Start position
- P1: Control point (apex of the arc)
- P2: End position

Formula: P(t) = (1-t)^2 * P0 + 2*(1-t)*t * P1 + t^2 * P2

Examples:
    >>> from game.trajectory.algorithms.bezier_3d import Bezier3DTrajectory
    >>> config = {
    ...     'duration': 3.0,
    ...     'start_x': 100.0,
    ...     'start_y': 400.0,
    ...     'end_x': 700.0,
    ...     'end_y': 400.0,
    ...     'control_x': 400.0,
    ...     'control_y': 100.0,
    ...     'depth_range': (1.0, 3.0),  # Flying away
    ...     'curvature_factor': 1.5
    ... }
    >>> trajectory = Bezier3DTrajectory.generate(config, 800, 600)
    >>> pos = trajectory.get_position(0.5)  # Apex position
"""

from typing import Dict
from models import Vector2D
from games.DuckHunt.game.trajectory.base import Trajectory, TrajectoryData, TrajectoryAlgorithm


class Bezier3DTrajectoryImpl(Trajectory):
    """Bezier curve trajectory with 3D depth simulation.

    Implements quadratic Bezier curve interpolation for smooth curved motion
    with perspective scaling based on depth. The curve creates natural-looking
    arcing flight paths similar to how a duck might fly.

    The trajectory uses three control points:
    - P0 (start): Where the target spawns
    - P1 (control): Apex/peak of the arc (controls curve shape)
    - P2 (end): Where the target exits

    Mathematical formula:
        P(t) = (1-t)^2 * P0 + 2*(1-t)*t * P1 + t^2 * P2

    Where t is normalized time [0.0, 1.0]:
    - t=0.0: Target at start position
    - t=0.5: Target at apex (closest to control point)
    - t=1.0: Target at end position

    The curvature_factor scales the control point's influence, allowing
    for more or less pronounced curves with the same control point position.

    Attributes:
        data: Immutable trajectory configuration with control_point required
    """

    def get_position(self, t: float) -> Vector2D:
        """Get position at normalized time t using quadratic Bezier interpolation.

        Formula with curvature factor:
            P(t) = (1-t)^2 * P0 + 2*(1-t)*t*k * P1 + t^2 * P2

        Where:
            - P0 = start position
            - P1 = control point (apex)
            - P2 = end position
            - k = curvature_factor (default 1.0)
            - t = normalized time [0.0, 1.0]

        The curvature_factor allows tuning the curve intensity:
        - k = 0.0: Straight line (degenerate curve)
        - k = 1.0: Standard Bezier curve
        - k > 1.0: More pronounced curve (control point has stronger influence)
        - k < 1.0: Flatter curve (control point has weaker influence)

        Args:
            t: Normalized time in range [0.0, 1.0]
               - 0.0 = start position
               - ~0.5 = near apex (closest to control point)
               - 1.0 = end position

        Returns:
            Position vector at time t along the Bezier curve

        Raises:
            ValueError: If control_point is None (required for Bezier curves)

        Examples:
            >>> data = TrajectoryData(
            ...     start=Vector2D(x=100.0, y=400.0),
            ...     end=Vector2D(x=700.0, y=400.0),
            ...     control_point=Vector2D(x=400.0, y=100.0),
            ...     depth_range=(1.0, 3.0),
            ...     duration=3.0,
            ...     curvature_factor=1.0
            ... )
            >>> traj = Bezier3DTrajectoryImpl(data)
            >>> traj.get_position(0.0)  # Start
            Vector2D(x=100.00, y=400.00)
            >>> traj.get_position(0.5)  # Near apex
            Vector2D(x=400.00, y=250.00)
            >>> traj.get_position(1.0)  # End
            Vector2D(x=700.00, y=400.00)
        """
        if self.data.control_point is None:
            raise ValueError("Bezier trajectory requires a control_point")

        # Extract control points
        p0 = self.data.start
        p1 = self.data.control_point
        p2 = self.data.end
        k = self.data.curvature_factor

        # Quadratic Bezier formula with curvature factor:
        # P(t) = (1-t)^2 * P0 + 2*(1-t)*t*k * P1 + t^2 * P2
        #
        # Standard Bezier formula (k=1.0):
        # P(t) = (1-t)^2 * P0 + 2*(1-t)*t * P1 + t^2 * P2
        #
        # Breaking down the formula:
        # - (1-t)^2: Weight for start point (max at t=0, min at t=1)
        # - 2*(1-t)*t*k: Weight for control point (max at t=0.5, zero at t=0 and t=1)
        # - t^2: Weight for end point (min at t=0, max at t=1)

        one_minus_t = 1.0 - t
        t_squared = t * t
        one_minus_t_squared = one_minus_t * one_minus_t

        # Calculate X coordinate
        x = (one_minus_t_squared * p0.x +
             2.0 * one_minus_t * t * k * p1.x +
             t_squared * p2.x)

        # Calculate Y coordinate
        y = (one_minus_t_squared * p0.y +
             2.0 * one_minus_t * t * k * p1.y +
             t_squared * p2.y)

        return Vector2D(x=x, y=y)


class Bezier3DTrajectory:
    """Bezier curve trajectory algorithm generator with 3D depth simulation.

    Factory class that implements the TrajectoryAlgorithm protocol for
    creating curved trajectories with perspective scaling. Combines smooth
    Bezier curves with depth interpolation to create visually interesting
    3D-like movement patterns.

    Use cases:
    - Targets flying in arcing paths
    - Targets moving diagonally while appearing to fly away or approach
    - Any curved motion that needs to feel three-dimensional

    Depth simulation:
    - depth_range = (1.0, 3.0): Target flies away (shrinks)
    - depth_range = (3.0, 1.0): Target approaches (grows)
    - depth_range = (1.0, 1.0): Constant size along curve

    This is a stateless generator - all configuration is passed in the
    config dictionary and screen dimensions.
    """

    @staticmethod
    def generate(config: Dict, screen_width: float, screen_height: float) -> Trajectory:
        """Generate a Bezier curve trajectory with 3D depth from configuration.

        Required config keys:
            - duration: float - Total time to traverse path in seconds
            - start_x: float - Starting X coordinate
            - start_y: float - Starting Y coordinate
            - end_x: float - Ending X coordinate
            - end_y: float - Ending Y coordinate
            - control_x: float - Control point X coordinate (apex)
            - control_y: float - Control point Y coordinate (apex)

        Optional config keys:
            - depth_range: Tuple[float, float] - (start_depth, end_depth)
                          Defaults to (1.0, 1.0) for constant depth
                          Use (1.0, 3.0) for flying away, (3.0, 1.0) for approaching
            - curvature_factor: float - Controls curve intensity (default 1.0)
                               >1.0 for more curved, <1.0 for flatter

        Args:
            config: Configuration dictionary with trajectory parameters
            screen_width: Width of screen/play area (used for validation)
            screen_height: Height of screen/play area (used for validation)

        Returns:
            Bezier3DTrajectoryImpl instance configured with given parameters

        Raises:
            KeyError: If required config keys are missing
            ValueError: If config values are invalid

        Examples:
            >>> # Duck flying in high arc while moving away
            >>> config = {
            ...     'duration': 3.0,
            ...     'start_x': 100.0,
            ...     'start_y': 400.0,
            ...     'end_x': 700.0,
            ...     'end_y': 400.0,
            ...     'control_x': 400.0,
            ...     'control_y': 100.0,
            ...     'depth_range': (1.0, 3.0),
            ...     'curvature_factor': 1.5
            ... }
            >>> trajectory = Bezier3DTrajectory.generate(config, 800, 600)
            >>>
            >>> # Duck flying low while approaching
            >>> config2 = {
            ...     'duration': 2.5,
            ...     'start_x': 700.0,
            ...     'start_y': 450.0,
            ...     'end_x': 100.0,
            ...     'end_y': 450.0,
            ...     'control_x': 400.0,
            ...     'control_y': 350.0,
            ...     'depth_range': (3.0, 1.0),
            ...     'curvature_factor': 0.8
            ... }
            >>> trajectory2 = Bezier3DTrajectory.generate(config2, 800, 600)
        """
        # Extract required parameters
        try:
            duration = config['duration']
            start_x = config['start_x']
            start_y = config['start_y']
            end_x = config['end_x']
            end_y = config['end_y']
            control_x = config['control_x']
            control_y = config['control_y']
        except KeyError as e:
            raise KeyError(f"Missing required config key: {e}")

        # Extract optional parameters with defaults
        depth_range = config.get('depth_range', (1.0, 1.0))
        curvature_factor = config.get('curvature_factor', 1.0)

        # Create trajectory data
        data = TrajectoryData(
            start=Vector2D(x=start_x, y=start_y),
            end=Vector2D(x=end_x, y=end_y),
            control_point=Vector2D(x=control_x, y=control_y),
            depth_range=depth_range,
            duration=duration,
            curvature_factor=curvature_factor
        )

        return Bezier3DTrajectoryImpl(data)


# Auto-register this algorithm when module is imported
from games.DuckHunt.game.trajectory.registry import TrajectoryRegistry
TrajectoryRegistry.register("bezier_3d", Bezier3DTrajectory)
