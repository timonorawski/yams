"""BrickBreaker physics and collision detection."""

from .collision import (
    check_wall_collision,
    check_paddle_collision,
    check_brick_collision,
    get_collision_direction,
)

__all__ = [
    'check_wall_collision',
    'check_paddle_collision',
    'check_brick_collision',
    'get_collision_direction',
]
