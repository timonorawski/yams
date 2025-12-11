-- fade_out.lua
-- Fade out and destroy entity after a duration

local behavior = {}

function behavior.on_spawn(entity_id)
    -- Set initial alpha if not already set
    local alpha = ams.get_prop(entity_id, "alpha")
    if not alpha then
        ams.set_prop(entity_id, "alpha", 255)
    end

    -- Get duration from config, default 0.5 seconds
    local duration = ams.get_config(entity_id, "fade_out", "duration", 0.5)
    ams.set_prop(entity_id, "fade_duration", duration)
    ams.set_prop(entity_id, "fade_timer", 0)
end

function behavior.on_update(entity_id, dt)
    local timer = ams.get_prop(entity_id, "fade_timer") or 0
    local duration = ams.get_prop(entity_id, "fade_duration") or 0.5

    timer = timer + dt
    ams.set_prop(entity_id, "fade_timer", timer)

    -- Calculate alpha based on progress
    local progress = timer / duration
    if progress >= 1.0 then
        -- Fully faded, destroy
        ams.destroy(entity_id)
    else
        -- Set alpha (255 to 0)
        local alpha = math.floor(255 * (1.0 - progress))
        ams.set_prop(entity_id, "alpha", alpha)
    end
end

return behavior
