--[[
shoot behavior - entity fires projectiles at intervals

Config options (from YAML):
  interval: float - seconds between shots (default: 2.0)
  projectile_type: string - entity type to spawn (default: "projectile")
  projectile_speed: float - projectile velocity (default: 200)
  projectile_color: string - projectile color (default: "red")
  direction: string - "down", "up", "player" (default: "down")
  offset_x: float - spawn offset from center (default: 0)
  offset_y: float - spawn offset from center (default: 0)

Usage in YAML:
  behaviors:
    - shoot:
        interval: 3.0
        projectile_speed: 150
        direction: down
]]

local shoot = {}

function shoot.on_spawn(entity_id)
    -- Start with random offset so not all shoot at once
    local interval = ams.get_config(entity_id, "shoot", "interval", 2.0)
    local initial_timer = ams.random() * interval
    ams.set_prop(entity_id, "shoot_timer", initial_timer)
end

function shoot.on_update(entity_id, dt)
    local interval = ams.get_config(entity_id, "shoot", "interval", 2.0)

    local timer = ams.get_prop(entity_id, "shoot_timer") or 0
    timer = timer + dt

    if timer >= interval then
        shoot.fire(entity_id)
        timer = timer - interval
    end

    ams.set_prop(entity_id, "shoot_timer", timer)
end

function shoot.fire(entity_id)
    local projectile_type = ams.get_config(entity_id, "shoot", "projectile_type", "projectile")
    local speed = ams.get_config(entity_id, "shoot", "projectile_speed", 200)
    local color = ams.get_config(entity_id, "shoot", "projectile_color", "red")
    local direction = ams.get_config(entity_id, "shoot", "direction", "down")
    local offset_x = ams.get_config(entity_id, "shoot", "offset_x", 0)
    local offset_y = ams.get_config(entity_id, "shoot", "offset_y", 0)

    -- Get entity center
    local x = ams.get_x(entity_id) + ams.get_width(entity_id) / 2
    local y = ams.get_y(entity_id) + ams.get_height(entity_id) / 2

    -- Apply offset
    x = x + offset_x
    y = y + offset_y

    -- Calculate velocity based on direction
    local vx, vy = 0, 0

    if direction == "down" then
        vy = speed
    elseif direction == "up" then
        vy = -speed
    elseif direction == "left" then
        vx = -speed
    elseif direction == "right" then
        vx = speed
    elseif direction == "player" then
        -- TODO: Find player entity and aim at it
        -- For now, just shoot down
        vy = speed
    end

    -- Spawn projectile
    local proj_id = ams.spawn(
        projectile_type,
        x - 4,  -- Center the 8x8 projectile
        y,
        vx, vy,
        8, 8,   -- width, height
        color,
        ""      -- sprite
    )

    ams.play_sound("shoot")
end

return shoot
