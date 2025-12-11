--[[
bounce_reflect collision action

Reflects entity_a off entity_b based on collision direction.
Uses AABB overlap to determine bounce axis.

Modifier options:
  speed_increase: float - speed added after bounce (default: 0)
  max_speed: float - maximum speed cap (default: 600)
  sound: string - sound to play on bounce (default: none)

Usage in game.yaml:
  collision_behaviors:
    ball:
      brick:
        action: bounce_reflect
        modifier:
          speed_increase: 5
          max_speed: 600
]]

local bounce_reflect = {}

function bounce_reflect.execute(entity_a_id, entity_b_id, modifier)
    -- Get entity_a (ball) position and size
    local a_x = ams.get_x(entity_a_id)
    local a_y = ams.get_y(entity_a_id)
    local a_w = ams.get_width(entity_a_id)
    local a_h = ams.get_height(entity_a_id)
    local a_cx = a_x + a_w / 2
    local a_cy = a_y + a_h / 2

    -- Get entity_b (brick) position and size
    local b_x = ams.get_x(entity_b_id)
    local b_y = ams.get_y(entity_b_id)
    local b_w = ams.get_width(entity_b_id)
    local b_h = ams.get_height(entity_b_id)
    local b_cx = b_x + b_w / 2
    local b_cy = b_y + b_h / 2

    -- Calculate overlap on each axis
    local dx = a_cx - b_cx
    local dy = a_cy - b_cy

    local overlap_x = (a_w + b_w) / 2 - math.abs(dx)
    local overlap_y = (a_h + b_h) / 2 - math.abs(dy)

    -- Bounce on axis with less overlap (collision came from that direction)
    if overlap_x < overlap_y then
        -- Horizontal collision - reverse X velocity
        ams.set_vx(entity_a_id, -ams.get_vx(entity_a_id))
    else
        -- Vertical collision - reverse Y velocity
        ams.set_vy(entity_a_id, -ams.get_vy(entity_a_id))
    end

    -- Apply speed increase if configured
    if modifier then
        local speed_increase = modifier.speed_increase or 0
        local max_speed = modifier.max_speed or 600

        if speed_increase > 0 then
            local vx = ams.get_vx(entity_a_id)
            local vy = ams.get_vy(entity_a_id)
            local current_speed = ams.sqrt(vx * vx + vy * vy)

            if current_speed < max_speed then
                local new_speed = math.min(current_speed + speed_increase, max_speed)
                local ratio = new_speed / current_speed
                ams.set_vx(entity_a_id, vx * ratio)
                ams.set_vy(entity_a_id, vy * ratio)
            end
        end

        -- Play sound if configured
        if modifier.sound then
            ams.play_sound(modifier.sound)
        end
    end
end

return bounce_reflect
