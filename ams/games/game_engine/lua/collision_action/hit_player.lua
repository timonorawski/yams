--[[
hit_player collision action - projectile hits player, causing life loss

When a projectile (entity A) hits the player/paddle (entity B):
1. Destroys the projectile
2. Triggers a "player_hit" event (handled by game engine for life loss)

Modifier options:
  play_sound: string - sound to play (default: "player_hit")

Usage in YAML:
  collision_behaviors:
    projectile:
      paddle:
        action: hit_player
        modifier:
          play_sound: "hit"
]]

local hit_player = {}

function hit_player.execute(projectile_id, player_id, modifier)
    -- Destroy the projectile
    ams.destroy(projectile_id)

    -- Play hit sound
    local sound = modifier and modifier.play_sound or "player_hit"
    ams.play_sound(sound)

    -- Set a property on player that game engine can detect
    -- The game engine's lose_conditions will handle life loss
    ams.set_prop(player_id, "was_hit", true)
end

return hit_player
