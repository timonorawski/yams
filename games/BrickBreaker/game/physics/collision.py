"""Collision detection and physics for BrickBreaker.

Handles ball-wall, ball-paddle, and ball-brick collisions.
"""

from typing import Optional, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities.ball import Ball
    from ..entities.paddle import Paddle
    from ..entities.brick import Brick


def check_wall_collision(
    ball: 'Ball',
    screen_width: float,
    screen_height: float,
) -> tuple['Ball', bool]:
    """Check and handle ball-wall collisions.

    Args:
        ball: Ball to check
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels

    Returns:
        Tuple of (updated ball, True if ball fell below screen)
    """
    new_ball = ball
    fell_below = False

    # Left wall
    if ball.x - ball.radius <= 0:
        new_ball = new_ball.bounce_horizontal()
        new_ball = new_ball.set_position(ball.radius, ball.y)

    # Right wall
    elif ball.x + ball.radius >= screen_width:
        new_ball = new_ball.bounce_horizontal()
        new_ball = new_ball.set_position(screen_width - ball.radius, ball.y)

    # Top wall (ceiling)
    if ball.y - ball.radius <= 0:
        new_ball = new_ball.bounce_vertical()
        new_ball = new_ball.set_position(ball.x, ball.radius)

    # Bottom (ball lost)
    elif ball.y + ball.radius >= screen_height:
        fell_below = True
        new_ball = new_ball.deactivate()

    return new_ball, fell_below


def check_paddle_collision(ball: 'Ball', paddle: 'Paddle') -> bool:
    """Check if ball collides with paddle.

    Only returns True if ball is moving downward (to prevent
    multiple bounces when ball is inside paddle).

    Args:
        ball: Ball to check
        paddle: Paddle to check against

    Returns:
        True if ball hits paddle
    """
    # Only collide if ball is moving down
    if ball.vy <= 0:
        return False

    # Get ball bounds
    ball_left, ball_top, ball_right, ball_bottom = ball.get_bounds()

    # Get paddle bounds
    paddle_rect = paddle.rect
    paddle_left = paddle_rect[0]
    paddle_top = paddle_rect[1]
    paddle_right = paddle_left + paddle_rect[2]
    paddle_bottom = paddle_top + paddle_rect[3]

    # Check AABB overlap
    if (ball_right < paddle_left or ball_left > paddle_right or
            ball_bottom < paddle_top or ball_top > paddle_bottom):
        return False

    return True


def check_brick_collision(ball: 'Ball', brick: 'Brick') -> bool:
    """Check if ball collides with brick.

    Args:
        ball: Ball to check
        brick: Brick to check against

    Returns:
        True if ball hits brick
    """
    if not brick.is_active:
        return False

    # Get ball bounds
    ball_left, ball_top, ball_right, ball_bottom = ball.get_bounds()

    # Get brick bounds
    brick_left, brick_top, brick_right, brick_bottom = brick.get_bounds()

    # Check AABB overlap
    if (ball_right < brick_left or ball_left > brick_right or
            ball_bottom < brick_top or ball_top > brick_bottom):
        return False

    return True


def get_collision_direction(
    ball: 'Ball',
    brick: 'Brick',
) -> Optional[Literal["top", "bottom", "left", "right"]]:
    """Determine collision direction between ball and brick.

    Uses the ball's velocity and position relative to brick
    to determine which side was hit.

    Args:
        ball: Ball that hit the brick
        brick: Brick that was hit

    Returns:
        Direction ball hit from: "top", "bottom", "left", "right",
        or None if no collision
    """
    if not check_brick_collision(ball, brick):
        return None

    # Get brick center
    brick_cx = brick.center_x
    brick_cy = brick.center_y

    # Calculate difference from brick center to ball center
    dx = ball.x - brick_cx
    dy = ball.y - brick_cy

    # Calculate overlap on each axis
    half_brick_w = brick.width / 2
    half_brick_h = brick.height / 2

    # Determine which side was hit based on position and velocity
    # Use the axis with smaller penetration depth

    overlap_x = half_brick_w + ball.radius - abs(dx)
    overlap_y = half_brick_h + ball.radius - abs(dy)

    if overlap_x < overlap_y:
        # Hit from left or right
        if dx > 0:
            return "right"  # Ball is to the right, hit right side
        else:
            return "left"   # Ball is to the left, hit left side
    else:
        # Hit from top or bottom
        if dy > 0:
            return "bottom"  # Ball is below, hit bottom
        else:
            return "top"     # Ball is above, hit top


def resolve_brick_collision(
    ball: 'Ball',
    brick: 'Brick',
    direction: Literal["top", "bottom", "left", "right"],
) -> 'Ball':
    """Resolve ball-brick collision by bouncing appropriately.

    Args:
        ball: Ball that hit the brick
        brick: Brick that was hit
        direction: Direction ball hit from

    Returns:
        Ball with updated velocity after bounce
    """
    if direction in ("top", "bottom"):
        return ball.bounce_vertical()
    else:
        return ball.bounce_horizontal()
