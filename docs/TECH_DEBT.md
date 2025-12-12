# Technical Debt Summary

Last updated: December 2024

This document tracks known technical debt and improvement opportunities in the YAMS codebase. Items are prioritized by impact and effort.

## High Priority (Fix Soon)

### ~~1. Duplicate Models Location~~ ✓ FIXED
**Issue**: `models.py` (root) duplicates definitions in `models/` package.
**Fix**: Deleted root `models.py`. All imports now use `models/` package.

### ~~2. DuckHunt Not Using BaseGame~~ ✓ FIXED
**Issue**: DuckHunt had its own `GameMode` ABC instead of inheriting from `BaseGame`.
**Fix**: All 11 game_mode.py files now inherit from BaseGame or GameEngine.

### ~~3. Hardcoded Path in detection_backend.py~~ ✓ FIXED
**Issue**: Line 20 referenced `'Games'` instead of `'games'`.
**Fix**: Changed to lowercase `'games'`.

### 4. Missing Test Coverage
**Issue**: Test coverage is improving but still gaps in:
- AMS core (`ams/session.py`, detection backends)
- Calibration (`calibration/`)
- GameEngine/LuaEngine integration

**Impact**: Regressions can slip through unnoticed.
**Fix**: Add test suite for critical paths.

### ~~5. Migration Artifact Files~~ ✓ FIXED
**Issue**: Leftover test files from BaseGame migration.
**Fix**: Deleted migration test artifacts.

---

## Medium Priority (Plan Next)

### 6. Print Statements Instead of Logging
**Files affected**: 12+ files in `ams/` and `calibration/`
**Impact**: No log level control, hard to debug in production.
**Fix**: Replace `print()` with `logging` module.
**Status**: Partially done - loggers added to key modules (session, calibration, laser, object).
  - Remaining: Interactive calibration prompts still use print (intentional for user feedback)
  - See `docs/guides/AMS_DEVELOPER_GUIDE.md` for logging conventions

### 7. Bare Exception Handlers
**Files**: `ams/object_detection_backend.py` (lines 357, 437)
**Issue**: `except Exception:` hides specific errors.
**Fix**: Catch specific exceptions, add error logging.

### 8. Configuration Sprawl (Legacy Python Games) — Will Self-Resolve
**Issue**: Each legacy Python game has its own `config.py` with duplicated boilerplate and inconsistent patterns.

**Affected**: Containment, Grouping, DuckHunt, Gradient, SweetPhysics, BrickBreaker

**Resolution**: Legacy Python games will be deleted once reimplemented as NG (YAML+Lua) games.
NG games use standardized `game.yaml` schema — no per-game config.py needed.

**No action required** — debt resolves naturally as NG ports are completed.

### 9. TODO Comments
| File | Line | Issue |
|------|------|-------|
| `ams/calibration.py` | 252 | CV backend contrast computation placeholder |
| `ams/calibration.py` | 279 | CV backend quality estimation placeholder |
| `games/DuckHunt/game/feedback.py` | 261 | Missing dedicated spawn sound |
| `games/DuckHunt/game/modes/dynamic.py` | 156 | Missing level-up feedback |
| `games/DuckHunt/game/modes/dynamic.py` | 477 | Unimplemented timed mode |

### 10. Documentation Gaps
- ~~No AMS event flow diagram~~ ✓ See `docs/architecture/AMS_ARCHITECTURE.md`
- ~~Architectural decisions not documented~~ ✓ See `docs/architecture/AMS_ARCHITECTURE.md`
- ~~No GameEngine/LuaEngine architecture~~ ✓ See `docs/architecture/LUA_ENGINE_ARCHITECTURE.md`
- ~~No Lua scripting guide~~ ✓ See `docs/guides/lua_scripting.md`
- ~~No YAML game quickstart~~ ✓ See `docs/guides/YAML_GAME_QUICKSTART.md`
- No calibration workflow documentation (step-by-step user guide)

---

## Low Priority (Nice to Have)

### 11. Hardcoded Detection Thresholds
**File**: `ams/object_detection_backend.py`
**Issue**: Impact velocity (10.0 px/s), direction change (90.0°) hardcoded.
**Fix**: Make configurable via constructor or config.

### 12. Common Effect Patterns
**Issue**: Similar effect classes duplicated across games (PopEffect, etc.).
**Fix**: Extract to `games/common/effects/` if patterns mature.

### 13. Pasture WIP Directory
**Path**: `pasture/duckhunt-wip/`
**Issue**: Old WIP code that may confuse developers.
**Fix**: Archive or remove.

---

## Good Patterns to Spread

These patterns exist in parts of the codebase and should be adopted more widely.

### 1. YAML + Lua Game Engine ✓ FULLY REALIZED

**Location**: `ams/games/game_engine/` + `games/*NG/`

**Pattern**: Games defined entirely in YAML + Lua, no Python game logic:

```yaml
# games/BrickBreakerNG/game.yaml
name: "Brick Breaker NG"
entity_types:
  ball:
    behaviors: [ball, bounce]
    behavior_config:
      ball: {speed: 300}
  paddle:
    behaviors: [paddle]
collision_behaviors:
  ball:
    paddle: {action: bounce_paddle}
    brick: {action: take_damage}
```

**Status**: 7 "NG" games now use this pattern:
- BrickBreakerNG, DuckHuntNG, FruitSliceNG, GroupingNG
- LoveOMeterNG, RopeTestNG, SweetPhysicsNG

**Architecture documented in**:
- `docs/architecture/LUA_ENGINE_ARCHITECTURE.md`
- `docs/GAME_ENGINE_ARCHITECTURE.md`
- `docs/guides/lua_scripting.md`
- `docs/guides/YAML_GAME_QUICKSTART.md`

**Benefits**:
- Zero Python code for game logic
- Lua behaviors are composable and reusable
- ContentFS layering allows game-specific overrides
- Sandboxed Lua safe for web deployment

### 2. Pacing Presets (Common Infrastructure)

**Location**: `games/common/pacing.py`

**Pattern**: Named presets for device-speed tuning.

**Current** (Python dicts):
```python
PACING_PRESETS = {
    'archery': PacingPreset(spawn_interval=4.0, ...),
    'throwing': PacingPreset(spawn_interval=2.0, ...),
    'blaster': PacingPreset(spawn_interval=0.5, ...),
}
```

**Could be** (YAML):
```yaml
# games/common/pacing_presets.yaml
archery:
  description: "Slow cycle for bows, crossbows"
  spawn_interval: 4.0
  target_lifetime: 8.0
  combo_window: 10.0

throwing:
  description: "Medium cycle for darts, balls"
  spawn_interval: 2.0
  target_lifetime: 5.0
  combo_window: 5.0

blaster:
  description: "Fast cycle for Nerf, laser"
  spawn_interval: 0.5
  target_lifetime: 3.0
  combo_window: 2.0
```

**Benefits**:
- Games work across all input devices
- Single `--pacing` flag instead of many params
- Consistent experience terminology
- **YAML would allow**: custom presets without code changes, per-venue tuning

**Status**: Adopted by most games, but still Python dicts (candidate for YAML)

### 3. Internal State Pattern (ManyTargets, Grouping)

**Location**: `games/ManyTargets/game_mode.py`

**Pattern**: Private enum for complex state machines:

```python
class _InternalState(Enum):
    WAITING = auto()
    PLAYING = auto()
    ROUND_COMPLETE = auto()

class MyGame(BaseGame):
    def _get_internal_state(self) -> GameState:
        # Map complex internal states to simple external states
        return {
            _InternalState.WAITING: GameState.PLAYING,
            _InternalState.PLAYING: GameState.PLAYING,
            _InternalState.ROUND_COMPLETE: GameState.WON,
        }[self._internal_state]
```

**Benefits**:
- Clean separation of game-specific vs platform states
- External interface stays simple
- Internal complexity doesn't leak

**Status**: Documented in NEW_GAME_QUICKSTART.md ✓

---

## Completed Items

### ✓ Dynamic CLI Arguments (December 2024)
- **Issue**: `dev_game.py` had hardcoded game arguments.
- **Fix**: Two-phase argparse with dynamic loading from game classes.

### ✓ BaseGame Plugin Architecture (December 2024)
- **Issue**: Game metadata scattered in game_info.py modules.
- **Fix**: Moved to class attributes (NAME, DESCRIPTION, ARGUMENTS).

### ✓ Registry Discovery via Introspection (December 2024)
- **Issue**: Registry did source code introspection.
- **Fix**: Now uses `inspect.getmembers()` + `issubclass()` for proper discovery.

### ✓ Game Migrations to BaseGame (December 2024)

All games except DuckHunt now use BaseGame:
- BalloonPop
- Containment
- FruitSlice
- Grouping
- GrowingTargets
- ManyTargets

### ✓ Quick Fixes (December 2024)

- Deleted migration test artifacts (4 files)
- Fixed `'Games'` → `'games'` path in `ams/detection_backend.py`
- Deleted redundant root `models.py` (consolidated to `models/` package)

### ✓ AMS Architecture Documentation (December 2024)

- Created `docs/architecture/AMS_ARCHITECTURE.md`
- Documented detection backend comparison (mouse, laser, object)
- Added ADRs for key decisions (normalized coords, temporal state, etc.)
- Documented DuckHunt tech debt (ADR-004)
- Added "how to add a new backend" guide

### ✓ AMS Logging Infrastructure (December 2024)

- Added `logging` module to AMS package
- Created `docs/guides/AMS_DEVELOPER_GUIDE.md` with logging conventions
- Updated key modules: session.py, calibration.py, laser_detection_backend.py, object_detection_backend.py
- Established pattern: `logger = logging.getLogger('ams.modulename')`

### ✓ GameEngine + LuaEngine Architecture (December 2024)

- Created YAML-driven game engine (`ams/games/game_engine/`)
- Sandboxed Lua scripting via lupa (`ams/lua/`)
- 7 "NG" games created using pure YAML + Lua (no Python game logic)
- ContentFS layered filesystem for game overrides
- Comprehensive documentation:
  - `docs/architecture/LUA_ENGINE_ARCHITECTURE.md`
  - `docs/GAME_ENGINE_ARCHITECTURE.md`
  - `docs/guides/lua_scripting.md`
  - `docs/guides/YAML_GAME_QUICKSTART.md`

### ✓ All Games Using BaseGame/GameEngine (December 2024)

- All 18 games now inherit from BaseGame or GameEngine
- DuckHunt migrated to BaseGame
- Legacy games: 11 using BaseGame with Python logic
- NG games: 7 using GameEngine with YAML + Lua

---

## Statistics

| Metric | Count |
|--------|-------|
| Python files | ~200 (core), ~5000 (with tests/deps) |
| Games (legacy Python) | 11 |
| Games (YAML+Lua NG) | 7 |
| Test files | 649 |
| TODO comments | 5 |
| Games using BaseGame/GameEngine | 18/18 |

---

## Suggested Order of Work

1. **Quick wins** (< 1 hour each):
   - ~~Delete migration test files~~ ✓ Done
   - ~~Fix `Games` → `games` path~~ ✓ Done
   - ~~Consolidate models imports~~ ✓ Done (removed root `models.py`)

2. **Next sprint**:
   - ~~Add logging infrastructure to AMS/calibration~~ ✓ Done
   - Write tests for game registry
   - Write tests for GameEngine/LuaEngine integration
   - ~~Document DuckHunt architecture decision~~ ✓ Done (ADR-004 in AMS_ARCHITECTURE.md)

3. **Pattern spreading** (largely complete via GameEngine):
   - ~~YAML config support for games~~ ✓ Done (GameEngine + NG games)
   - Migrate remaining legacy games to GameEngine when appropriate
   - Convert pacing presets to YAML (`games/common/pacing_presets.yaml`)

4. **Future**:
   - ~~Migrate games to BaseGame~~ ✓ Done (all 18 games)
   - Add comprehensive test coverage for GameEngine
   - Browser/WASM deployment of YAML+Lua games
   - Calibration workflow documentation
