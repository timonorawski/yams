--[[
bounce_paddle collision action

Bounces entity_a off a paddle (entity_b), adjusting angle based on hit position.
Used for ball-paddle collisions in brick breaker games.

Only bounces if entity_a is moving downward (toward paddle).
Angle varies based on where ball hits paddle:
- Center hit = straight up (-90 degrees)
- Edge hit = angled up to max_angle degrees from vertical

Modifier options:
  max_angle: float - maximum angle from vertical for edge hits (default: 60)

Usage in game.yaml:
  collision_behaviors:
    ball:
      paddle:
        action: bounce_paddle
        modifier:
          max_angle: 60
]]

local bounce_paddle = {}

function bounce_paddle.execute(entity_a_id, entity_b_id, modifier)
    -- entity_a is the ball, entity_b is the paddle

    -- Only bounce if ball is moving downward
    local vy = ams.get_vy(entity_a_id)
    if vy <= 0 then
        return
    end

    -- Get paddle info
    local paddle_x = ams.get_x(entity_b_id)
    local paddle_width = ams.get_width(entity_b_id)
    local paddle_center = paddle_x + paddle_width / 2

    -- Get ball info
    local ball_x = ams.get_x(entity_a_id)
    local ball_width = ams.get_width(entity_a_id)
    local ball_center_x = ball_x + ball_width / 2

    -- Calculate offset from paddle center (-1 to 1)
    local offset = (ball_center_x - paddle_center) / (paddle_width / 2)
    offset = ams.clamp(offset, -1, 1)

    -- Get max angle from modifier or use default
    local max_angle = 60
    if modifier and modifier.max_angle then
        max_angle = modifier.max_angle
    end

    -- Calculate new angle based on offset
    -- Center hit = straight up (-90), edge hit = max_angle degrees from vertical
    local angle = -90 + offset * max_angle
    local angle_rad = angle * 3.14159 / 180

    -- Get current speed
    local vx = ams.get_vx(entity_a_id)
    local speed = ams.sqrt(vx * vx + vy * vy)

    -- Set new velocity
    ams.set_vx(entity_a_id, speed * ams.cos(angle_rad))
    ams.set_vy(entity_a_id, speed * ams.sin(angle_rad))

    ams.play_sound("paddle_hit")
end

return bounce_paddle
