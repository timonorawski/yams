-- follow_parent.lua
-- Makes entity follow its parent entity with an offset
--
-- Config:
--   offset_x: X offset from parent center (default: from entity.parent_offset)
--   offset_y: Y offset from parent center (default: from entity.parent_offset)
--
-- When parent is destroyed, this entity triggers its on_parent_destroy transform

local behavior = {}

function behavior.on_spawn(entity_id)
    -- Get parent_id from entity properties
    local parent_id = ams.get_prop(entity_id, "_parent_id")
    if parent_id then
        -- Initial sync to parent position
        behavior._sync_to_parent(entity_id, parent_id)
    end
end

function behavior.on_update(entity_id, dt)
    local parent_id = ams.get_prop(entity_id, "_parent_id")
    if not parent_id then
        return
    end

    -- Check if parent still exists
    local parent_x = ams.get_x(parent_id)
    if parent_x == nil then
        -- Parent was destroyed - trigger orphan behavior
        -- The game engine handles on_parent_destroy transform
        -- For now, just clear the parent reference
        ams.set_prop(entity_id, "_parent_id", nil)
        return
    end

    behavior._sync_to_parent(entity_id, parent_id)
end

function behavior._sync_to_parent(entity_id, parent_id)
    local parent_x = ams.get_x(parent_id)
    local parent_y = ams.get_y(parent_id)
    local parent_w = ams.get_width(parent_id)
    local parent_h = ams.get_height(parent_id)

    if parent_x == nil then
        return
    end

    -- Get offset from config or properties
    local offset_x = ams.get_config(entity_id, "follow_parent", "offset_x", nil)
    local offset_y = ams.get_config(entity_id, "follow_parent", "offset_y", nil)

    -- Fall back to stored parent_offset property
    if offset_x == nil then
        offset_x = ams.get_prop(entity_id, "_parent_offset_x") or 0
    end
    if offset_y == nil then
        offset_y = ams.get_prop(entity_id, "_parent_offset_y") or 0
    end

    -- Calculate parent center
    local parent_cx = parent_x + parent_w / 2
    local parent_cy = parent_y + parent_h / 2

    -- Position this entity relative to parent center
    local my_w = ams.get_width(entity_id)
    local my_h = ams.get_height(entity_id)

    ams.set_x(entity_id, parent_cx + offset_x - my_w / 2)
    ams.set_y(entity_id, parent_cy + offset_y - my_h / 2)

    -- Inherit parent velocity (for momentum when detached)
    local parent_vx = ams.get_vx(parent_id) or 0
    local parent_vy = ams.get_vy(parent_id) or 0
    ams.set_vx(entity_id, parent_vx)
    ams.set_vy(entity_id, parent_vy)
end

return behavior
