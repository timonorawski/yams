--[[
take_damage collision action

Reduces entity_a's hit points when hit by entity_b.
Destroys entity_a when hits reach zero.

Requires entity_a to have 'brick' behavior attached (for brick_hits_remaining property).

Modifier options:
  amount: int - damage amount per hit (default: 1)
  points: int - points awarded on destroy (default: from brick behavior config)
  hit_sound: string - sound on hit (default: "brick_hit")
  destroy_sound: string - sound on destroy (default: "brick_break")

Usage in game.yaml:
  collision_behaviors:
    brick:
      ball:
        action: take_damage
        modifier:
          amount: 1
]]

local take_damage = {}

function take_damage.execute(entity_a_id, entity_b_id, modifier)
    -- Check if entity is indestructible
    local indestructible = ams.get_config(entity_a_id, "brick", "indestructible", false)
    if indestructible then
        local hit_sound = "brick_hit"
        if modifier and modifier.hit_sound then
            hit_sound = modifier.hit_sound
        end
        ams.play_sound(hit_sound)
        return
    end

    -- Get current hits remaining
    local hits = ams.get_prop(entity_a_id, "brick_hits_remaining") or 1

    -- Get damage amount
    local damage = 1
    if modifier and modifier.amount then
        damage = modifier.amount
    end

    -- Apply damage
    hits = hits - damage
    ams.set_prop(entity_a_id, "brick_hits_remaining", hits)

    if hits <= 0 then
        -- Destroyed
        local points = ams.get_config(entity_a_id, "brick", "points", 100)
        if modifier and modifier.points then
            points = modifier.points
        end

        ams.add_score(points)
        ams.destroy(entity_a_id)

        local destroy_sound = "brick_break"
        if modifier and modifier.destroy_sound then
            destroy_sound = modifier.destroy_sound
        end
        ams.play_sound(destroy_sound)
    else
        -- Damaged but not destroyed
        local hit_sound = "brick_hit"
        if modifier and modifier.hit_sound then
            hit_sound = modifier.hit_sound
        end
        ams.play_sound(hit_sound)
    end
end

return take_damage
