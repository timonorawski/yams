--[[
paddle behavior - stopping paddle that slides to target position

The paddle receives a target X position (set via properties) and
slides toward it, stopping when reached.

Properties used:
  paddle_target_x: Target X position (set by game on input)

Config options (from YAML):
  speed: float - pixels per second (default: 500)
  stop_threshold: float - distance to consider "reached" (default: 1.0)

Usage in YAML:
  behaviors:
    - paddle:
        speed: 500
]]

local paddle = {}

function paddle.on_spawn(entity_id)
    -- Initialize target to current position
    local x = ams.get_x(entity_id)
    local width = ams.get_width(entity_id)
    ams.set_prop(entity_id, "paddle_target_x", x + width / 2)
end

function paddle.on_update(entity_id, dt)
    local speed = ams.get_config(entity_id, "paddle", "speed", 500)
    local threshold = ams.get_config(entity_id, "paddle", "stop_threshold", 1.0)

    local x = ams.get_x(entity_id)
    local width = ams.get_width(entity_id)
    local center_x = x + width / 2

    local target_x = ams.get_prop(entity_id, "paddle_target_x") or center_x

    -- Calculate distance to target
    local distance = target_x - center_x

    if math.abs(distance) <= threshold then
        -- Close enough, stop
        return
    end

    -- Move toward target
    local direction = 1
    if distance < 0 then
        direction = -1
    end

    local move_amount = speed * dt
    if math.abs(distance) < move_amount then
        -- Would overshoot, just move to target
        ams.set_x(entity_id, target_x - width / 2)
    else
        ams.set_x(entity_id, x + direction * move_amount)
    end

    -- Clamp to screen bounds
    local screen_w = ams.get_screen_width()
    local new_x = ams.get_x(entity_id)
    if new_x < 0 then
        ams.set_x(entity_id, 0)
    elseif new_x + width > screen_w then
        ams.set_x(entity_id, screen_w - width)
    end
end

return paddle
