--[[
gravity behavior - apply gravitational acceleration and movement

Applies downward acceleration to velocity, then moves entity by velocity.
Handles both vertical and horizontal velocity for projectile motion.

Config options (from YAML):
  acceleration: float - gravity in pixels/sec^2 (default: 800)

Usage in YAML:
  behaviors: [gravity, destroy_offscreen]
  behavior_config:
    gravity:
      acceleration: 600
    destroy_offscreen:
      edges: all
]]

local gravity = {}

function gravity.on_update(entity_id, dt)
    local accel = ams.get_config(entity_id, "gravity", "acceleration", 800)

    -- Apply gravity to vertical velocity
    local vy = ams.get_vy(entity_id)
    vy = vy + accel * dt
    ams.set_vy(entity_id, vy)

    -- Move by velocity
    local x = ams.get_x(entity_id)
    local y = ams.get_y(entity_id)
    local vx = ams.get_vx(entity_id)

    x = x + vx * dt
    y = y + vy * dt

    ams.set_x(entity_id, x)
    ams.set_y(entity_id, y)
end

return gravity
