--[[
gravity behavior - apply gravitational acceleration

Simple behavior that applies downward acceleration to an entity.
Destroys entity when it falls off screen bottom.

Config options (from YAML):
  acceleration: float - gravity in pixels/sec^2 (default: 800)
  destroy_offscreen: bool - destroy when off bottom (default: true)

Usage in YAML:
  behaviors: [gravity]
  behavior_config:
    gravity:
      acceleration: 800
]]

local gravity = {}

function gravity.on_update(entity_id, dt)
    local accel = ams.get_config(entity_id, "gravity", "acceleration", 800)

    -- Apply gravity to velocity
    local vy = ams.get_vy(entity_id)
    vy = vy + accel * dt
    ams.set_vy(entity_id, vy)

    -- Move by velocity
    local y = ams.get_y(entity_id)
    y = y + vy * dt
    ams.set_y(entity_id, y)

    -- Also apply horizontal velocity if any
    local vx = ams.get_vx(entity_id)
    if vx ~= 0 then
        local x = ams.get_x(entity_id)
        x = x + vx * dt
        ams.set_x(entity_id, x)
    end

    -- Destroy if off screen bottom
    local destroy_offscreen = ams.get_config(entity_id, "gravity", "destroy_offscreen", true)
    if destroy_offscreen then
        local height = ams.get_height(entity_id)
        local screen_h = ams.get_screen_height()
        if y > screen_h + height then
            ams.destroy(entity_id)
        end
    end
end

return gravity
