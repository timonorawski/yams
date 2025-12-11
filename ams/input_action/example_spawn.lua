--[[
Example input action - spawns particles at click location

Input actions are Lua scripts that execute on user input events.
They receive:
  - x, y: Input position in screen coordinates
  - args: Lua table of arguments from YAML config

Usage in game.yaml:
  global_on_input:
    action: example_spawn
    action_args:
      particle_type: "spark"
      count: 3

This example demonstrates how to create custom input actions.
]]

local action = {}

function action.execute(x, y, args)
    -- Get arguments with defaults
    local particle_type = args and args.particle_type or "particle"
    local count = args and args.count or 1

    -- Spawn particles at click location
    for i = 1, count do
        -- Random velocity spread
        local vx = ams.random_range(-50, 50)
        local vy = ams.random_range(-100, -50)

        ams.spawn(particle_type, x, y, vx, vy, 0, 0, "", "")
    end
end

return action
