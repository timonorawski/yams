--[[
bounce behavior - move with velocity and bounce off walls

Generic bouncing behavior that moves an entity by its velocity
and bounces off screen edges.

Config options (from YAML):
  walls: string - which walls to bounce off: "all", "sides", "top_sides" (default: "all")
  min_y: float - minimum y position (default: 0)
  max_y: float - maximum y position as fraction of screen (default: 1.0)

Usage in YAML:
  behaviors: [bounce]
  behavior_config:
    bounce:
      walls: top_sides  # bounce off top, left, right only
      max_y: 0.7        # stay in upper 70% of screen
]]

local bounce = {}

function bounce.on_update(entity_id, dt)
    local vx = ams.get_vx(entity_id)
    local vy = ams.get_vy(entity_id)

    -- No velocity = no movement
    if vx == 0 and vy == 0 then
        return
    end

    -- Move by velocity
    local x = ams.get_x(entity_id)
    local y = ams.get_y(entity_id)

    x = x + vx * dt
    y = y + vy * dt

    ams.set_x(entity_id, x)
    ams.set_y(entity_id, y)

    -- Get config
    local walls = ams.get_config(entity_id, "bounce", "walls", "all")
    local min_y = ams.get_config(entity_id, "bounce", "min_y", 0)
    local max_y_frac = ams.get_config(entity_id, "bounce", "max_y", 1.0)

    local width = ams.get_width(entity_id)
    local height = ams.get_height(entity_id)
    local screen_w = ams.get_screen_width()
    local screen_h = ams.get_screen_height()
    local max_y = screen_h * max_y_frac

    -- Left wall
    if x < 0 then
        ams.set_x(entity_id, 0)
        ams.set_vx(entity_id, math.abs(vx))
    end

    -- Right wall
    if x + width > screen_w then
        ams.set_x(entity_id, screen_w - width)
        ams.set_vx(entity_id, -math.abs(vx))
    end

    -- Top wall
    if walls == "all" or walls == "top_sides" then
        if y < min_y then
            ams.set_y(entity_id, min_y)
            ams.set_vy(entity_id, math.abs(vy))
        end
    end

    -- Bottom wall (or max_y limit)
    if walls == "all" then
        if y + height > screen_h then
            ams.set_y(entity_id, screen_h - height)
            ams.set_vy(entity_id, -math.abs(vy))
        end
    elseif walls == "top_sides" or walls == "sides" then
        -- For flying targets, bounce at max_y instead of screen bottom
        if y + height > max_y then
            ams.set_y(entity_id, max_y - height)
            ams.set_vy(entity_id, -math.abs(vy))
        end
    end
end

return bounce
