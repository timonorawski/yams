--[[
projectile behavior - move in a direction and destroy when off-screen

A projectile moves according to its velocity and destroys itself
when it leaves the screen bounds.

No config needed - uses entity's vx/vy set at spawn time.
]]

local projectile = {}

function projectile.on_update(entity_id, dt)
    -- Move according to velocity
    local x = ams.get_x(entity_id)
    local y = ams.get_y(entity_id)
    local vx = ams.get_vx(entity_id)
    local vy = ams.get_vy(entity_id)

    x = x + vx * dt
    y = y + vy * dt

    ams.set_x(entity_id, x)
    ams.set_y(entity_id, y)

    -- Destroy if off-screen
    local width = ams.get_width(entity_id)
    local height = ams.get_height(entity_id)
    local screen_w = ams.get_screen_width()
    local screen_h = ams.get_screen_height()

    if x + width < 0 or x > screen_w or y + height < 0 or y > screen_h then
        ams.destroy(entity_id)
    end
end

return projectile
