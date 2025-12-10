--[[
brick behavior - destructible brick with hit tracking

Handles multi-hit bricks and destruction logic.
Movement behaviors (descend, oscillate) are separate.

Properties used:
  brick_hits_remaining: int - hits left to destroy

Config options (from YAML):
  hits: int - hits required to destroy (default: 1)
  points: int - points when destroyed (default: 100)
  indestructible: bool - cannot be destroyed (default: false)

Usage in YAML:
  behaviors:
    - brick:
        hits: 3
        points: 300
]]

local brick = {}

function brick.on_spawn(entity_id)
    local hits = ams.get_config(entity_id, "brick", "hits", 1)
    ams.set_prop(entity_id, "brick_hits_remaining", hits)
    ams.set_prop(entity_id, "brick_max_hits", hits)
end

-- Called by game when ball hits brick
-- Returns true if brick was destroyed
function brick.hit(entity_id)
    local indestructible = ams.get_config(entity_id, "brick", "indestructible", false)
    if indestructible then
        ams.play_sound("brick_hit")
        return false
    end

    local hits = ams.get_prop(entity_id, "brick_hits_remaining") or 1
    hits = hits - 1
    ams.set_prop(entity_id, "brick_hits_remaining", hits)

    if hits <= 0 then
        -- Destroyed
        local points = ams.get_config(entity_id, "brick", "points", 100)
        ams.add_score(points)
        ams.destroy(entity_id)
        ams.play_sound("brick_break")
        return true
    else
        -- Damaged but not destroyed
        ams.play_sound("brick_hit")
        return false
    end
end

-- Get damage ratio for rendering (0 = full health, 1 = nearly destroyed)
function brick.get_damage_ratio(entity_id)
    local hits = ams.get_prop(entity_id, "brick_hits_remaining") or 1
    local max_hits = ams.get_prop(entity_id, "brick_max_hits") or 1
    return 1 - (hits / max_hits)
end

-- NOTE: Collision handling has been moved to collision_actions/
-- The on_hit hook below is kept for legacy/fallback support only.
-- New games should use collision_behaviors in game.yaml instead.

-- Legacy on_hit handler (only called if no collision_behaviors defined)
function brick.on_hit(entity_id, other_id, other_type, other_base_type)
    -- This is now handled by collision_actions/take_damage.lua
    -- Keeping stub for backwards compatibility with games not using collision_behaviors
end

return brick
