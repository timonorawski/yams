--[[
destroy_offscreen behavior - destroy entity when it leaves screen bounds

Checks if entity has fully exited the screen and destroys it.
Can be configured to only check certain edges.

Config options (from YAML):
  edges: string - which edges to check: "all", "bottom", "sides", "top_bottom" (default: "all")
  margin: float - extra pixels beyond screen edge before destroying (default: 50)

Usage in YAML:
  behaviors: [gravity, destroy_offscreen]
  behavior_config:
    destroy_offscreen:
      edges: bottom
      margin: 100
]]

local destroy_offscreen = {}

function destroy_offscreen.on_update(entity_id, dt)
    local edges = ams.get_config(entity_id, "destroy_offscreen", "edges", "all")
    local margin = ams.get_config(entity_id, "destroy_offscreen", "margin", 50)

    local x = ams.get_x(entity_id)
    local y = ams.get_y(entity_id)
    local width = ams.get_width(entity_id)
    local height = ams.get_height(entity_id)
    local screen_w = ams.get_screen_width()
    local screen_h = ams.get_screen_height()

    local should_destroy = false

    -- Check bottom edge
    if edges == "all" or edges == "bottom" or edges == "top_bottom" then
        if y > screen_h + margin then
            should_destroy = true
        end
    end

    -- Check top edge
    if edges == "all" or edges == "top" or edges == "top_bottom" then
        if y + height < -margin then
            should_destroy = true
        end
    end

    -- Check left edge
    if edges == "all" or edges == "sides" or edges == "left" then
        if x + width < -margin then
            should_destroy = true
        end
    end

    -- Check right edge
    if edges == "all" or edges == "sides" or edges == "right" then
        if x > screen_w + margin then
            should_destroy = true
        end
    end

    if should_destroy then
        ams.destroy(entity_id)
    end
end

return destroy_offscreen
