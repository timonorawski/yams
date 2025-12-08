"""
Registry system for trajectory algorithms.

This module provides a central registry for trajectory algorithms, allowing
game modes to dynamically select and instantiate different movement patterns
without tight coupling to specific implementations.

Examples:
    >>> from game.trajectory.registry import TrajectoryRegistry
    >>> from game.trajectory.algorithms.linear import LinearTrajectory
    >>>
    >>> # Register an algorithm
    >>> TrajectoryRegistry.register("linear", LinearTrajectory)
    >>>
    >>> # List available algorithms
    >>> TrajectoryRegistry.list_algorithms()
    ['linear', 'bezier_3d']
    >>>
    >>> # Get and use an algorithm
    >>> algorithm = TrajectoryRegistry.get("linear")
    >>> config = {'duration': 2.0, 'start_x': 0.0, 'start_y': 300.0, ...}
    >>> trajectory = algorithm.generate(config, screen_width=800, screen_height=600)
"""

from typing import Dict, Type, List
from games.DuckHunt.game.trajectory.base import TrajectoryAlgorithm


class TrajectoryRegistry:
    """Central registry of trajectory generation algorithms.

    Provides a singleton registry pattern for managing trajectory algorithms.
    Algorithms can be registered at module import time or dynamically at runtime,
    and retrieved by name for instantiation.

    This enables:
    - Decoupling game modes from specific trajectory implementations
    - Easy addition of new trajectory algorithms without modifying existing code
    - Configuration-driven trajectory selection in game modes

    Class Attributes:
        _algorithms: Dictionary mapping algorithm names to algorithm classes

    Examples:
        >>> # Register a custom algorithm
        >>> class MyTrajectory:
        ...     @staticmethod
        ...     def generate(config, screen_width, screen_height):
        ...         # Implementation
        ...         pass
        >>>
        >>> TrajectoryRegistry.register("my_custom", MyTrajectory)
        >>>
        >>> # Retrieve and use
        >>> algo = TrajectoryRegistry.get("my_custom")
        >>> traj = algo.generate({...}, 800, 600)
    """

    _algorithms: Dict[str, Type[TrajectoryAlgorithm]] = {}

    @classmethod
    def register(cls, name: str, algorithm: Type[TrajectoryAlgorithm]) -> None:
        """Register a trajectory algorithm with a given name.

        Adds an algorithm to the registry, making it available for retrieval
        by name. If an algorithm with the same name already exists, it will
        be overwritten (allowing for algorithm replacement/mocking in tests).

        Args:
            name: Unique identifier for the algorithm (e.g., "linear", "bezier_3d")
            algorithm: Algorithm class implementing TrajectoryAlgorithm protocol

        Examples:
            >>> from game.trajectory.algorithms.linear import LinearTrajectory
            >>> TrajectoryRegistry.register("linear", LinearTrajectory)
            >>> TrajectoryRegistry.register("straight_line", LinearTrajectory)  # Alias
        """
        cls._algorithms[name] = algorithm

    @classmethod
    def get(cls, name: str) -> Type[TrajectoryAlgorithm]:
        """Retrieve a trajectory algorithm by name.

        Args:
            name: Name of the algorithm to retrieve

        Returns:
            Algorithm class implementing TrajectoryAlgorithm protocol

        Raises:
            ValueError: If no algorithm with the given name is registered

        Examples:
            >>> algorithm = TrajectoryRegistry.get("linear")
            >>> trajectory = algorithm.generate(config, 800, 600)
        """
        if name not in cls._algorithms:
            available = ", ".join(cls.list_algorithms())
            raise ValueError(
                f"Unknown trajectory algorithm: '{name}'. "
                f"Available algorithms: {available if available else 'none'}"
            )
        return cls._algorithms[name]

    @classmethod
    def list_algorithms(cls) -> List[str]:
        """List all registered algorithm names.

        Returns:
            Sorted list of registered algorithm names

        Examples:
            >>> TrajectoryRegistry.list_algorithms()
            ['bezier_3d', 'linear']
        """
        return sorted(cls._algorithms.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if an algorithm is registered.

        Args:
            name: Algorithm name to check

        Returns:
            True if algorithm is registered, False otherwise

        Examples:
            >>> TrajectoryRegistry.is_registered("linear")
            True
            >>> TrajectoryRegistry.is_registered("nonexistent")
            False
        """
        return name in cls._algorithms

    @classmethod
    def clear(cls) -> None:
        """Clear all registered algorithms.

        Primarily useful for testing to ensure clean state between tests.
        Should not be used in production code.

        Examples:
            >>> # In test teardown
            >>> TrajectoryRegistry.clear()
        """
        cls._algorithms.clear()
