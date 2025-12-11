--[[
rope_link - Bidirectional elastic constraint between parent and child

Creates spring-like connection using Hooke's Law.
Both parent and child are affected by the spring force.
Child typically has gravity, parent typically doesn't.

Config:
  rest_length: float - unstretched length (default: 30)
  stiffness: float - spring constant k (default: 800, higher = stiffer)
  damping: float - velocity damping (default: 0.98)

YAML example:
  rope_segment:
    behaviors: [rope_link]
    behavior_config:
      rope_link:
        rest_length: 30
        stiffness: 800
        damping: 0.98

  candy:
    behaviors: [gravity, rope_link]
    behavior_config:
      gravity:
        acceleration: 600
      rope_link:
        rest_length: 35
        stiffness: 600
]]

local rope_link = {}

function rope_link.on_update(entity_id, dt)
    -- Get parent using the proper API
    local parent_id = ams.get_parent_id(entity_id)
    if parent_id == "" or not ams.is_alive(parent_id) then
        return  -- No parent = behavior does nothing (gravity handles falling)
    end

    -- Get config
    local rest_length = ams.get_config(entity_id, "rope_link", "rest_length", 30)
    local stiffness = ams.get_config(entity_id, "rope_link", "stiffness", 800)
    local damping = ams.get_config(entity_id, "rope_link", "damping", 0.98)

    -- Get positions (top-left corners)
    local parent_x = ams.get_x(parent_id)
    local parent_y = ams.get_y(parent_id)
    local child_x = ams.get_x(entity_id)
    local child_y = ams.get_y(entity_id)

    -- Calculate centers
    local parent_w = ams.get_width(parent_id)
    local parent_h = ams.get_height(parent_id)
    local child_w = ams.get_width(entity_id)
    local child_h = ams.get_height(entity_id)

    local parent_cx = parent_x + parent_w / 2
    local parent_cy = parent_y + parent_h / 2
    local child_cx = child_x + child_w / 2
    local child_cy = child_y + child_h / 2

    -- Vector from parent center to child center
    local dx = child_cx - parent_cx
    local dy = child_cy - parent_cy
    local current_length = math.sqrt(dx * dx + dy * dy)

    -- Avoid division by zero
    if current_length < 0.001 then
        return
    end

    -- Unit vector pointing from parent to child
    local ux = dx / current_length
    local uy = dy / current_length

    -- Stretch amount (positive = too long, negative = compressed)
    local stretch = current_length - rest_length

    -- Spring force magnitude (Hooke's Law: F = k * x)
    -- Negative because force opposes stretch
    local force = stiffness * stretch

    -- Force components (pointing inward when stretched)
    local fx = -ux * force
    local fy = -uy * force

    -- Apply force to child (pulls toward parent when stretched)
    local child_vx = ams.get_vx(entity_id)
    local child_vy = ams.get_vy(entity_id)
    child_vx = (child_vx + fx * dt) * damping
    child_vy = (child_vy + fy * dt) * damping
    ams.set_vx(entity_id, child_vx)
    ams.set_vy(entity_id, child_vy)

    -- Apply opposite force to parent (Newton's 3rd law)
    -- Scale down parent response (rope segments are lighter)
    local parent_scale = 0.3
    local parent_vx = ams.get_vx(parent_id)
    local parent_vy = ams.get_vy(parent_id)
    parent_vx = (parent_vx - fx * dt * parent_scale) * damping
    parent_vy = (parent_vy - fy * dt * parent_scale) * damping
    ams.set_vx(parent_id, parent_vx)
    ams.set_vy(parent_id, parent_vy)

    -- Note: Position integration is handled by BehaviorEngine
    -- We only modify velocities here
end

return rope_link
