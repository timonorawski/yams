--[[
descend behavior - move entity downward

Config options (from YAML):
  speed: float - pixels per second (default: 50)
  pattern: string - "fixed", "step", "wave" (default: "fixed")
  step_interval: float - seconds between steps for "step" pattern (default: 1.0)
  step_distance: float - pixels per step (default: 20)
  wave_amplitude: float - horizontal wave amplitude (default: 30)
  wave_frequency: float - oscillations per second (default: 1.0)

Usage in YAML:
  behaviors:
    - descend:
        speed: 30
        pattern: wave
        wave_amplitude: 50
]]

local descend = {}

function descend.on_spawn(entity_id)
    -- Initialize state
    ams.set_prop(entity_id, "descend_timer", 0)
    ams.set_prop(entity_id, "descend_start_x", ams.get_x(entity_id))
end

function descend.on_update(entity_id, dt)
    local speed = ams.get_config(entity_id, "descend", "speed", 50)
    local pattern = ams.get_config(entity_id, "descend", "pattern", "fixed")

    if pattern == "fixed" then
        -- Simple downward movement
        local y = ams.get_y(entity_id)
        ams.set_y(entity_id, y + speed * dt)

    elseif pattern == "step" then
        -- Move in discrete steps
        local interval = ams.get_config(entity_id, "descend", "step_interval", 1.0)
        local step_dist = ams.get_config(entity_id, "descend", "step_distance", 20)

        local timer = ams.get_prop(entity_id, "descend_timer") or 0
        timer = timer + dt

        if timer >= interval then
            local y = ams.get_y(entity_id)
            ams.set_y(entity_id, y + step_dist)
            timer = timer - interval
        end

        ams.set_prop(entity_id, "descend_timer", timer)

    elseif pattern == "wave" then
        -- Descend with horizontal wave motion
        local amplitude = ams.get_config(entity_id, "descend", "wave_amplitude", 30)
        local frequency = ams.get_config(entity_id, "descend", "wave_frequency", 1.0)
        local start_x = ams.get_prop(entity_id, "descend_start_x") or ams.get_x(entity_id)

        -- Move down
        local y = ams.get_y(entity_id)
        ams.set_y(entity_id, y + speed * dt)

        -- Oscillate horizontally
        local time = ams.get_time()
        local offset = amplitude * ams.sin(time * frequency * 2 * 3.14159)
        ams.set_x(entity_id, start_x + offset)
    end
end

return descend
