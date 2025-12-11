-- grid_position.lua
-- Property generator: Calculates pixel position from grid coordinates
--
-- Usage in YAML:
--   x: {call: "grid_position", args: {axis: "x", index: 5, start: 65, spacing: 75}}
--   y: {call: "grid_position", args: {axis: "y", index: 2, start: 60, spacing: 30}}

local grid_position = {}

function grid_position.generate(args)
    -- args.index: Grid index (0-based or 1-based depending on usage)
    -- args.start: Starting pixel position
    -- args.spacing: Pixels between grid cells
    -- args.axis: Optional, for documentation ("x" or "y")

    local index = args.index or 0
    local start = args.start or 0
    local spacing = args.spacing or 0

    return start + (index * spacing)
end

return grid_position
