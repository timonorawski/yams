--[[
ball behavior - bouncing ball with velocity

The ball moves according to its velocity and bounces off walls.
A ball with zero velocity is stationary (not yet launched).
Collision handling is done via collision_actions when GameEngine detects overlaps.

Properties used:
  ball_speed: float - current speed magnitude (initialized from config)
  ball_fell: bool - set true when ball goes off bottom of screen

Config options (from YAML):
  speed: float - initial speed magnitude (default: 300)
  max_speed: float - maximum speed (default: 600)
  speed_increase: float - speed added per brick hit (default: 5)

Collision handling via collision_actions:
  - bounce_paddle.lua: ball vs paddle (angle based on hit position)
  - bounce_reflect.lua: ball vs brick (AABB reflection)

Usage in YAML:
  behaviors:
    - ball:
        speed: 300
        max_speed: 600
]]

local ball = {}

function ball.on_spawn(entity_id)
    -- Initialize ball_speed from config default
    ams.set_prop(entity_id, "ball_speed", ams.get_config(entity_id, "ball", "speed", 300))

    -- If spawned with speed+angle properties, compute velocity
    local speed = ams.get_prop(entity_id, "speed")
    local angle = ams.get_prop(entity_id, "angle")

    if speed and angle then
        local angle_rad = angle * 3.14159 / 180
        ams.set_vx(entity_id, speed * ams.cos(angle_rad))
        ams.set_vy(entity_id, speed * ams.sin(angle_rad))
        ams.set_prop(entity_id, "ball_speed", speed)
        -- Clear spawn properties
        ams.set_prop(entity_id, "speed", nil)
        ams.set_prop(entity_id, "angle", nil)
    end
end

function ball.on_update(entity_id, dt)
    local vx = ams.get_vx(entity_id)
    local vy = ams.get_vy(entity_id)

    -- Ball with no velocity doesn't move (waiting to be launched)
    if vx == 0 and vy == 0 then
        return
    end

    -- Move ball
    local x = ams.get_x(entity_id)
    local y = ams.get_y(entity_id)

    x = x + vx * dt
    y = y + vy * dt

    ams.set_x(entity_id, x)
    ams.set_y(entity_id, y)

    -- Bounce off walls
    local width = ams.get_width(entity_id)
    local height = ams.get_height(entity_id)
    local screen_w = ams.get_screen_width()
    local screen_h = ams.get_screen_height()

    -- Left wall
    if x < 0 then
        ams.set_x(entity_id, 0)
        ams.set_vx(entity_id, -vx)
        ams.play_sound("wall_bounce")
    end

    -- Right wall
    if x + width > screen_w then
        ams.set_x(entity_id, screen_w - width)
        ams.set_vx(entity_id, -vx)
        ams.play_sound("wall_bounce")
    end

    -- Top wall
    if y < 0 then
        ams.set_y(entity_id, 0)
        ams.set_vy(entity_id, -vy)
        ams.play_sound("wall_bounce")
    end

    -- Bottom (ball lost) - handled by game layer, just mark property
    if y + height > screen_h then
        ams.set_prop(entity_id, "ball_fell", true)
    end
end

-- Called by game to launch the ball at an angle
function ball.launch(entity_id, angle_degrees)
    local speed = ams.get_prop(entity_id, "ball_speed") or 300
    local angle_degrees = angle_degrees or -75  -- Default: mostly up, slightly right

    local angle_rad = angle_degrees * 3.14159 / 180
    local vx = speed * ams.cos(angle_rad)
    local vy = speed * ams.sin(angle_rad)

    ams.set_vx(entity_id, vx)
    ams.set_vy(entity_id, vy)
end

-- Called by game after paddle hit to adjust angle
function ball.bounce_off_paddle(entity_id, paddle_center_x, paddle_width)
    local ball_x = ams.get_x(entity_id)
    local ball_width = ams.get_width(entity_id)
    local ball_center_x = ball_x + ball_width / 2

    -- Calculate offset from paddle center (-1 to 1)
    local offset = (ball_center_x - paddle_center_x) / (paddle_width / 2)
    offset = ams.clamp(offset, -1, 1)

    -- Calculate new angle based on offset
    -- Center hit = straight up (-90), edge hit = 60 degrees from vertical
    local max_angle = 60
    local angle = -90 + offset * max_angle
    local angle_rad = angle * 3.14159 / 180

    -- Get current speed
    local vx = ams.get_vx(entity_id)
    local vy = ams.get_vy(entity_id)
    local speed = ams.sqrt(vx * vx + vy * vy)

    -- Set new velocity
    ams.set_vx(entity_id, speed * ams.cos(angle_rad))
    ams.set_vy(entity_id, speed * ams.sin(angle_rad))

    ams.play_sound("paddle_hit")
end

-- Called by game to increase speed after brick hit
function ball.increase_speed(entity_id)
    local speed_increase = ams.get_config(entity_id, "ball", "speed_increase", 5)
    local max_speed = ams.get_config(entity_id, "ball", "max_speed", 600)

    local vx = ams.get_vx(entity_id)
    local vy = ams.get_vy(entity_id)
    local current_speed = ams.sqrt(vx * vx + vy * vy)

    if current_speed >= max_speed then
        return
    end

    local new_speed = math.min(current_speed + speed_increase, max_speed)
    local ratio = new_speed / current_speed

    ams.set_vx(entity_id, vx * ratio)
    ams.set_vy(entity_id, vy * ratio)

    ams.set_prop(entity_id, "ball_speed", new_speed)
end

-- NOTE: Collision handling has been moved to collision_actions/
-- The on_hit hook below is kept for legacy/fallback support only.
-- New games should use collision_behaviors in game.yaml instead.

-- Legacy on_hit handler (only called if no collision_behaviors defined)
function ball.on_hit(entity_id, other_id, other_type, other_base_type)
    -- This is now handled by collision_actions:
    -- - bounce_paddle.lua (ball vs paddle)
    -- - bounce_reflect.lua (ball vs brick)
    -- Keeping stub for backwards compatibility with games not using collision_behaviors
end

return ball
