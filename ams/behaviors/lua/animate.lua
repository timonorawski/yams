--[[
animate behavior - cycle through animation frames

Sets a 'frame' property on the entity that cycles through a range of values.
Use with sprite templating: sprite: duck_{frame}

Config options (from YAML):
  frames: int - number of frames (1-indexed, default: 3)
  fps: float - frames per second (default: 8)
  property: string - property name to set (default: "frame")

Usage in YAML:
  behaviors: [animate]
  behavior_config:
    animate:
      frames: 3
      fps: 8
  render:
    - shape: sprite
      sprite: green_right_{frame}
]]

local animate = {}

function animate.on_spawn(entity_id)
    -- Initialize animation state
    ams.set_prop(entity_id, "_anim_timer", 0)
    ams.set_prop(entity_id, "frame", 1)
end

function animate.on_update(entity_id, dt)
    local frames = ams.get_config(entity_id, "animate", "frames", 3)
    local fps = ams.get_config(entity_id, "animate", "fps", 8)
    local prop_name = ams.get_config(entity_id, "animate", "property", "frame")

    -- Update timer
    local timer = ams.get_prop(entity_id, "_anim_timer") or 0
    timer = timer + dt

    -- Calculate frame duration
    local frame_duration = 1.0 / fps

    -- Advance frame if enough time passed
    while timer >= frame_duration do
        timer = timer - frame_duration
        local current_frame = ams.get_prop(entity_id, prop_name) or 1
        current_frame = current_frame + 1
        if current_frame > frames then
            current_frame = 1
        end
        ams.set_prop(entity_id, prop_name, current_frame)
    end

    ams.set_prop(entity_id, "_anim_timer", timer)
end

return animate
