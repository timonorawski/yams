"""
Built-in trajectory algorithms for Duck Hunt game.

This package contains concrete implementations of trajectory algorithms:

- linear: Straight-line movement with optional depth scaling
- bezier_3d: Quadratic Bezier curves with 3D depth simulation

All algorithms in this package are automatically registered with the
TrajectoryRegistry when imported.

Examples:
    >>> from game.trajectory.algorithms.linear import LinearTrajectory
    >>> from game.trajectory.algorithms.bezier_3d import Bezier3DTrajectory
    >>>
    >>> # Or use via registry
    >>> from game.trajectory import TrajectoryRegistry
    >>> linear_algo = TrajectoryRegistry.get("linear")
    >>> bezier_algo = TrajectoryRegistry.get("bezier_3d")
"""

# Import algorithms to make them available
from game.trajectory.algorithms.linear import LinearTrajectory
from game.trajectory.algorithms.bezier_3d import Bezier3DTrajectory

# Public API
__all__ = [
    'LinearTrajectory',
    'Bezier3DTrajectory',
]
