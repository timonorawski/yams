"""
Trajectory system for Duck Hunt game.

This package provides a pluggable trajectory system for defining how targets
move across the screen. It includes:

- Base classes and protocols for trajectory algorithms
- A registry system for managing available algorithms
- Built-in implementations (linear, bezier with 3D depth)

Quick Start:
    >>> from game.trajectory import TrajectoryRegistry
    >>>
    >>> # List available algorithms
    >>> TrajectoryRegistry.list_algorithms()
    ['bezier_3d', 'linear']
    >>>
    >>> # Generate a linear trajectory
    >>> algorithm = TrajectoryRegistry.get("linear")
    >>> config = {
    ...     'duration': 2.0,
    ...     'start_x': 0.0,
    ...     'start_y': 300.0,
    ...     'end_x': 800.0,
    ...     'end_y': 300.0
    ... }
    >>> trajectory = algorithm.generate(config, 800, 600)
    >>>
    >>> # Use the trajectory
    >>> pos_at_start = trajectory.get_position(0.0)
    >>> pos_at_midpoint = trajectory.get_position(0.5)
    >>> pos_at_end = trajectory.get_position(1.0)
    >>> depth_factor = trajectory.get_depth_factor(0.5)

Algorithm Registration:
    Algorithms are automatically registered when their modules are imported.
    To ensure all built-in algorithms are available, import this package:

    >>> import game.trajectory  # Auto-registers linear and bezier_3d

Creating Custom Algorithms:
    1. Implement the TrajectoryAlgorithm protocol
    2. Create a Trajectory subclass with get_position()
    3. Register with TrajectoryRegistry

    >>> from game.trajectory.base import Trajectory, TrajectoryData, TrajectoryAlgorithm
    >>> from game.trajectory.registry import TrajectoryRegistry
    >>>
    >>> class MyTrajectory(Trajectory):
    ...     def get_position(self, t):
    ...         # Custom implementation
    ...         pass
    >>>
    >>> class MyAlgorithm:
    ...     @staticmethod
    ...     def generate(config, screen_width, screen_height):
    ...         # Create TrajectoryData and return MyTrajectory instance
    ...         pass
    >>>
    >>> TrajectoryRegistry.register("my_algorithm", MyAlgorithm)
"""

# Import base classes and registry
from games.DuckHunt.game.trajectory.base import (
    Trajectory,
    TrajectoryData,
    TrajectoryAlgorithm,
)
from games.DuckHunt.game.trajectory.registry import TrajectoryRegistry

# Import algorithms to auto-register them
# This ensures they're available when the package is imported
import games.DuckHunt.game.trajectory.algorithms.linear
import games.DuckHunt.game.trajectory.algorithms.bezier_3d

# Public API
__all__ = [
    # Base classes
    'Trajectory',
    'TrajectoryData',
    'TrajectoryAlgorithm',
    # Registry
    'TrajectoryRegistry',
]
