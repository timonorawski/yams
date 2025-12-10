--[[
oscillate behavior - move entity side-to-side

Config options (from YAML):
  speed: float - pixels per second of oscillation (default: 40)
  range: float - total horizontal range in pixels (default: 50)

Usage in YAML:
  behaviors:
    - oscillate:
        speed: 60
        range: 100
]]

local oscillate = {}

function oscillate.on_spawn(entity_id)
    -- Store initial position and direction
    ams.set_prop(entity_id, "oscillate_start_x", ams.get_x(entity_id))
    ams.set_prop(entity_id, "oscillate_direction", 1)  -- 1 = right, -1 = left
end

function oscillate.on_update(entity_id, dt)
    local speed = ams.get_config(entity_id, "oscillate", "speed", 40)
    local range = ams.get_config(entity_id, "oscillate", "range", 50)
    local half_range = range / 2

    local start_x = ams.get_prop(entity_id, "oscillate_start_x") or ams.get_x(entity_id)
    local direction = ams.get_prop(entity_id, "oscillate_direction") or 1

    local x = ams.get_x(entity_id)
    local new_x = x + speed * direction * dt

    -- Check bounds and reverse direction
    if new_x > start_x + half_range then
        new_x = start_x + half_range
        direction = -1
    elseif new_x < start_x - half_range then
        new_x = start_x - half_range
        direction = 1
    end

    ams.set_x(entity_id, new_x)
    ams.set_prop(entity_id, "oscillate_direction", direction)
end

return oscillate
