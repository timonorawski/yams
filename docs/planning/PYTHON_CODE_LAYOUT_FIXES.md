# Game Engine Extraction Refactor

## Goal

Restructure the codebase to:
1. Move game engine from `games/common/` to `ams/games/`
2. Extract generalizable Lua engine from `ams/behaviors/` to `ams/lua/`
3. Keep Lua assets (behaviors, collision_actions, generators) as game_engine core assets

## Target Structure

```
ams/
├── games/                          # NEW - from games/common/
│   ├── __init__.py
│   ├── base_game.py                # Base class for all games
│   ├── game_state.py               # GameState enum
│   ├── levels.py                   # Level loading system
│   ├── level_chooser.py            # Level selection UI
│   ├── pacing.py                   # Device pacing presets
│   ├── palette.py                  # Color palette management
│   ├── quiver.py                   # Ammo management
│   ├── input/                      # Input abstraction layer
│   │   ├── __init__.py
│   │   ├── input_event.py
│   │   ├── input_manager.py
│   │   └── sources/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       └── mouse.py
│   └── game_engine/                # YAML-driven game framework
│       ├── __init__.py
│       ├── engine.py               # Main GameEngine class (from game_engine.py)
│       └── lua/                    # Lua behavior system (game-engine specific)
│           ├── __init__.py
│           ├── entity.py           # Entity class
│           ├── api.py              # LuaAPI (ams.* namespace)
│           ├── behaviors/          # .lua entity behaviors
│           ├── collision_actions/  # .lua collision handlers
│           └── generators/         # .lua property generators
│
├── lua/                            # Core Lua sandbox abstraction (reusable)
│   ├── __init__.py
│   └── engine.py                   # LuaEngine (renamed from BehaviorEngine)
│                                   # Sandboxed Lua runtime with entity/behavior mgmt
│
├── input_actions/                  # Keep here (game engine uses via ContentFS)
│   └── *.lua
│
├── content_fs.py                   # Keep (already in place)
└── ...
```

## Current → New Path Mapping

| Current Path | New Path |
|--------------|----------|
| `games/common/game_engine.py` | `ams/games/game_engine/engine.py` |
| `games/common/base_game.py` | `ams/games/base_game.py` |
| `games/common/game_state.py` | `ams/games/game_state.py` |
| `games/common/levels.py` | `ams/games/levels.py` |
| `games/common/level_chooser.py` | `ams/games/level_chooser.py` |
| `games/common/pacing.py` | `ams/games/pacing.py` |
| `games/common/palette.py` | `ams/games/palette.py` |
| `games/common/quiver.py` | `ams/games/quiver.py` |
| `games/common/input/` | `ams/games/input/` |
| `ams/behaviors/engine.py` | `ams/lua/engine.py` (rename to LuaEngine) |
| `ams/behaviors/entity.py` | `ams/games/game_engine/lua/entity.py` |
| `ams/behaviors/api.py` | `ams/games/game_engine/lua/api.py` |
| `ams/behaviors/lua/` | `ams/games/game_engine/lua/behaviors/` |
| `ams/behaviors/collision_actions/` | `ams/games/game_engine/lua/collision_actions/` |
| `ams/behaviors/generators/` | `ams/games/game_engine/lua/generators/` |

## Import Updates Required

### Old → New Import Mapping

| Old Import | New Import |
|------------|------------|
| `from games.common import GameState` | `from ams.games import GameState` |
| `from games.common import BaseGame` | `from ams.games import BaseGame` |
| `from games.common import GameEngine` | `from ams.games.game_engine import GameEngine` |
| `from games.common.base_game import BaseGame` | `from ams.games.base_game import BaseGame` |
| `from games.common.game_state import GameState` | `from ams.games.game_state import GameState` |
| `from games.common.game_engine import GameEngine` | `from ams.games.game_engine import GameEngine` |
| `from games.common.palette import GamePalette` | `from ams.games.palette import GamePalette` |
| `from games.common.pacing import scale_for_pacing` | `from ams.games.pacing import scale_for_pacing` |
| `from games.common.levels import SimpleLevelLoader` | `from ams.games.levels import SimpleLevelLoader` |
| `from games.common.input import InputEvent, InputManager` | `from ams.games.input import InputEvent, InputManager` |
| `from games.common.input.sources import InputSource, MouseInputSource` | `from ams.games.input.sources import InputSource, MouseInputSource` |
| `from ams.behaviors import BehaviorEngine, Entity` | `from ams.lua import LuaEngine` + `from ams.games.game_engine.lua import Entity` |
| `from ams.behaviors.engine import BehaviorEngine` | `from ams.lua.engine import LuaEngine` |
| `from ams.behaviors.api import _to_lua_value` | `from ams.games.game_engine.lua.api import _to_lua_value` |

### Files Requiring Import Updates (~25 files)

**Game mode files (13):**
- `games/BalloonPop/game_mode.py`
- `games/BrickBreaker/game_mode.py`
- `games/Containment/game_mode.py`
- `games/DuckHunt/game_mode.py`
- `games/FruitSlice/game_mode.py`
- `games/Gradient/game_mode.py`
- `games/Grouping/game_mode.py`
- `games/GrowingTargets/game_mode.py`
- `games/LoveOMeter/game_mode.py`
- `games/ManyTargets/game_mode.py`
- `games/SweetPhysics/game_mode.py`
- `games/BrickBreaker/main.py`
- `games/Containment/main.py`

**Registry and integration:**
- `games/registry.py`
- `ams/web_controller/ams_integration.py`

**Models:**
- `models/duckhunt/__init__.py`
- `models/duckhunt/enums.py`

**Tests:**
- `tests/test_lua_sandbox.py`

**Game-local input wrappers (can be removed or updated):**
- `games/ManyTargets/input/` (5 files)
- `games/Grouping/input/` (5 files)
- `games/GrowingTargets/input/` (5 files)

## ContentFS Path Updates

The behavior engine loads Lua files via ContentFS. Update paths:

| Old ContentFS Path | New ContentFS Path |
|--------------------|-------------------|
| `ams/behaviors/lua/` | `ams/games/game_engine/lua/behaviors/` |
| `ams/behaviors/collision_actions/` | `ams/games/game_engine/lua/collision_actions/` |
| `ams/behaviors/generators/` | `ams/games/game_engine/lua/generators/` |
| `ams/input_actions/` | `ams/input_actions/` (no change) |

## Implementation Steps

### Phase 1: Create New Directory Structure
```bash
mkdir -p ams/games/input/sources
mkdir -p ams/games/game_engine/lua/behaviors
mkdir -p ams/games/game_engine/lua/collision_actions
mkdir -p ams/games/game_engine/lua/generators
mkdir -p ams/lua
```

### Phase 2: Move Supporting Files (games/common → ams/games)
```bash
# Core game abstractions
mv games/common/base_game.py ams/games/
mv games/common/game_state.py ams/games/
mv games/common/levels.py ams/games/
mv games/common/level_chooser.py ams/games/
mv games/common/pacing.py ams/games/
mv games/common/palette.py ams/games/
mv games/common/quiver.py ams/games/

# Input system
mv games/common/input/input_event.py ams/games/input/
mv games/common/input/input_manager.py ams/games/input/
mv games/common/input/sources/base.py ams/games/input/sources/
mv games/common/input/sources/mouse.py ams/games/input/sources/
```

### Phase 3: Move Game Engine
```bash
# Main GameEngine class
mv games/common/game_engine.py ams/games/game_engine/engine.py
```

### Phase 4: Move Lua Engine (ams/behaviors/engine.py → ams/lua/)
```bash
# Core Lua engine (rename BehaviorEngine → LuaEngine)
mv ams/behaviors/engine.py ams/lua/engine.py
# Then rename class BehaviorEngine to LuaEngine in the file
```

### Phase 5: Move Game-Engine Lua Components
```bash
# Entity and API (game-engine specific)
mv ams/behaviors/entity.py ams/games/game_engine/lua/entity.py
mv ams/behaviors/api.py ams/games/game_engine/lua/api.py

# Lua assets (game-engine core behaviors)
mv ams/behaviors/lua/* ams/games/game_engine/lua/behaviors/
mv ams/behaviors/collision_actions/* ams/games/game_engine/lua/collision_actions/
mv ams/behaviors/generators/* ams/games/game_engine/lua/generators/
```

Note: After this split, `ams.lua.LuaEngine` is the reusable sandboxed Lua runtime.
The game engine's `GameEngine` class uses `LuaEngine` and adds Entity/API/behavior management.

### Phase 6: Create __init__.py Files
1. `ams/lua/__init__.py` - export LuaEngine
2. `ams/games/__init__.py` - export GameState, BaseGame, etc.
3. `ams/games/input/__init__.py` - export InputEvent, InputManager
4. `ams/games/input/sources/__init__.py` - export InputSource, MouseInputSource
5. `ams/games/game_engine/__init__.py` - export GameEngine, GameEngineSkin
6. `ams/games/game_engine/lua/__init__.py` - export Entity, LuaAPI

### Phase 7: Update Internal Imports
1. Fix relative imports within `ams/games/` (base_game, levels, etc.)
2. Fix imports within `ams/games/game_engine/lua/` (engine, entity, api)
3. Update `ams/games/game_engine/engine.py` to import from `..lua`

### Phase 8: Update External Imports
1. Update all game_mode.py files (13 files)
2. Update games/registry.py
3. Update ams/web_controller/ams_integration.py
4. Update models/duckhunt/
5. Update tests/test_lua_sandbox.py

### Phase 9: Update ContentFS Paths
Update default paths in `ams/lua/engine.py` (LuaEngine):
- `ams/behaviors/lua/` → `ams/games/game_engine/lua/behaviors/`
- `ams/behaviors/collision_actions/` → `ams/games/game_engine/lua/collision_actions/`
- `ams/behaviors/generators/` → `ams/games/game_engine/lua/generators/`

### Phase 10: Cleanup
1. Remove empty `ams/behaviors/` directory
2. Remove empty `games/common/` directory
3. Optionally remove game-local input wrappers (now redundant)
4. Update documentation (CLAUDE.md, architecture docs)

### Phase 11: Testing
```bash
pytest tests/test_lua_sandbox.py -v          # All 105 tests pass
python dev_game.py --list                    # List all games
python dev_game.py sweetphysicsng            # YAML-driven game
python dev_game.py duckhunt                  # Python game
```

## Files to Create

| File | Purpose |
|------|---------|
| `ams/lua/__init__.py` | Export LuaEngine |
| `ams/games/__init__.py` | Export GameState, BaseGame, pacing, palette, quiver, levels |
| `ams/games/input/__init__.py` | Export InputEvent, InputManager |
| `ams/games/input/sources/__init__.py` | Export InputSource, MouseInputSource |
| `ams/games/game_engine/__init__.py` | Export GameEngine, GameEngineSkin, etc. |
| `ams/games/game_engine/lua/__init__.py` | Export Entity, LuaAPI |

## Verification

After refactor, these commands should work:
```bash
python dev_game.py --list                    # List all games
python dev_game.py sweetphysicsng            # YAML-driven game
python dev_game.py duckhunt                  # Python game
pytest tests/test_lua_sandbox.py -v          # All 105 tests pass
```
