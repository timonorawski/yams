# DuckHunt BaseGame Migration Plan

## Overview

DuckHunt is the oldest and most complex game in the AMS system. It predates the `BaseGame` architecture and has accumulated technical debt that makes it inconsistent with other games. This document outlines the migration to bring DuckHunt into compliance with the standard game architecture.

## Current State

### File Structure (Non-Compliant)

```
games/DuckHunt/
├── game_info.py          # Metadata + complex factory function
├── engine.py             # Standalone game loop (not used by dev_game.py)
├── main.py               # Standalone entry point
├── config.py             # Configuration
├── game/
│   ├── game_mode.py      # Local abstract base class (NOT BaseGame)
│   ├── modes/
│   │   ├── classic.py    # ClassicMode (main game logic)
│   │   └── dynamic.py    # DynamicMode variant
│   ├── target.py
│   ├── trajectory_target.py
│   ├── scoring.py
│   ├── feedback.py
│   ├── menu.py
│   ├── mode_loader.py
│   └── trajectory/       # Trajectory algorithms
├── input/                # Local input module (duplicates common)
│   ├── input_manager.py
│   ├── input_event.py
│   └── sources/
├── modes/                # YAML mode configurations
│   ├── classic_archery.yaml
│   └── ...
├── tests/
└── venv/                 # Local venv (should use project root)
```

### Architecture Issues

| Issue | Current State | Required State |
|-------|--------------|----------------|
| Base class | Local `GameMode` ABC | `games.common.BaseGame` |
| Metadata location | Module vars in `game_info.py` | Class attributes on game class |
| Game class location | `game/modes/classic.py` | `game_mode.py` at package root |
| Input module | Local duplicate | Re-export from `games.common.input` |
| State management | `DuckHuntInternalState` + manual mapping | `_get_internal_state()` override |
| Path manipulation | `sys.path` hacks everywhere | Clean imports via package structure |
| Palette/Quiver | Manual initialization | Inherited from `BaseGame.__init__` |

### Key Classes

**`game/game_mode.py:GameMode`** - Local ABC with:
- `_targets: List[Target]`
- `_state: DuckHuntInternalState`
- `state` property that calls `_state.to_game_state()`
- Abstract: `update()`, `handle_input()`, `render()`, `get_score()`

**`game/modes/classic.py:ClassicMode`** - Main game implementation:
- Inherits from local `GameMode`
- Manually initializes `GamePalette` and `create_quiver`
- Has `_score_tracker`, `feedback`, `_current_speed`, etc.
- Implements all game logic

**`game_info.py`** - Module-level metadata + factory:
- `NAME`, `DESCRIPTION`, `VERSION`, `AUTHOR` as module vars
- `ARGUMENTS` list
- `get_game_mode(**kwargs)` factory with complex mode loading

## Target State

### File Structure (Compliant)

```text
games/DuckHunt/
├── game_mode.py          # DuckHuntMode(BaseGame) - main entry point
├── game_info.py          # Minimal factory only
├── config.py             # Configuration (unchanged)
├── game/
│   ├── classic.py        # ClassicGameLogic (game mechanics, not BaseGame)
│   ├── dynamic.py        # DynamicGameLogic variant
│   ├── target.py         # (unchanged)
│   ├── trajectory_target.py
│   ├── scoring.py        # (unchanged)
│   ├── feedback.py       # (unchanged)
│   └── trajectory/       # (unchanged)
├── input/                # Re-exports from games.common.input
│   ├── __init__.py
│   ├── input_manager.py
│   ├── input_event.py
│   └── sources/
├── levels/               # NEW: Containment-style level system
│   ├── __init__.py
│   ├── level_loader.py   # YAML parsing, validation
│   ├── schema.md         # Level schema documentation
│   └── examples/
│       ├── classic_archery.yaml
│       ├── classic_blaster.yaml
│       ├── endless.yaml
│       └── speedrun.yaml
└── tests/
```

### New `game_mode.py`

```python
"""DuckHunt - Classic duck hunting game."""
from typing import List, Optional
import pygame

from games.common import BaseGame, GameState
from games.DuckHunt.game.classic import ClassicGameLogic
from games.DuckHunt.game.mode_loader import load_game_mode_config


class DuckHuntMode(BaseGame):
    """Duck Hunt game mode.

    Classic duck hunting with moving targets, combos, and difficulty progression.
    """

    # =========================================================================
    # Game Metadata
    # =========================================================================

    NAME = "Duck Hunt"
    DESCRIPTION = "Classic duck hunting game with moving targets and combos."
    VERSION = "2.0.0"  # Major version bump for architecture change
    AUTHOR = "AMS Team"

    ARGUMENTS = [
        {
            'name': '--mode',
            'type': str,
            'default': 'classic_archery',
            'help': 'Game mode config file (without .yaml extension)'
        },
        {
            'name': '--pacing',
            'type': str,
            'default': 'throwing',
            'choices': ['archery', 'throwing', 'blaster'],
            'help': 'Device speed preset'
        },
    ]

    # =========================================================================
    # Initialization
    # =========================================================================

    def __init__(
        self,
        mode: str = 'classic_archery',
        pacing: str = 'throwing',
        **kwargs,
    ):
        super().__init__(**kwargs)

        # Load mode configuration
        self._mode_name = mode
        self._pacing = pacing

        # Initialize game logic (delegates to ClassicGameLogic)
        self._game = ClassicGameLogic(
            mode_name=mode,
            pacing=pacing,
            palette=self._palette,
        )

    # =========================================================================
    # BaseGame Implementation
    # =========================================================================

    def _get_internal_state(self) -> GameState:
        return self._game.get_state()

    def get_score(self) -> int:
        return self._game.get_score()

    def handle_input(self, events: List) -> None:
        # Handle quiver
        for event in events:
            if self._use_shot():
                self._start_retrieval()
                return

        self._game.handle_input(events)

    def update(self, dt: float) -> None:
        if self._in_retrieval:
            if self._update_retrieval(dt):
                self._end_retrieval()
            return

        self._game.update(dt)

    def render(self, screen: pygame.Surface) -> None:
        self._game.render(screen, self._palette)

        # Render retrieval overlay if needed
        if self._in_retrieval:
            self._render_retrieval_overlay(screen)
```

### New `game_info.py` (Minimal)

```python
"""DuckHunt - Game Info (factory only)."""

def get_game_mode(**kwargs):
    """Factory function to create game instance."""
    from games.DuckHunt.game_mode import DuckHuntMode
    return DuckHuntMode(**kwargs)
```

### Input Module Re-exports

**`input/__init__.py`:**
```python
"""DuckHunt Input Module - Re-exports from common."""
from games.common.input import InputEvent, InputManager
from games.common.input.sources import InputSource, MouseInputSource

__all__ = ['InputEvent', 'InputManager', 'InputSource', 'MouseInputSource']
```

## Level System Migration

### Current YAML Mode Format

Located in `modes/classic_archery.yaml`:

```yaml
name: "Classic Archery"
description: "Traditional duck hunt with archery timing"

rules:
  max_misses: 10
  score_target: null  # Endless

levels:
  - level: 1
    target:
      speed: 150
      spawn_rate: 2.0
    # ... more level configs
```

### New Level Format (Containment-style)

Located in `levels/examples/classic_archery.yaml`:

```yaml
name: "Classic Archery"
description: "Traditional duck hunt with archery pacing"
difficulty: 2
author: "AMS Team"
version: 1

objectives:
  type: survive        # survive | score | endless
  max_misses: 10
  target_score: null   # null = endless

ball:  # Renamed from "target" for consistency? Or keep as "target"?
  count: 1
  speed: 150
  size: 40
  spawn_rate: 2.0

environment:
  spawn_edges: [left, right]  # Where targets spawn from
  trajectory: linear          # linear | arc | bezier

difficulty_scaling:
  speed_increase_per_hit: 5
  max_speed: 400
  spawn_rate_decrease: 0.05
  min_spawn_rate: 0.5

pacing:
  archery:
    target.speed: 100
    target.spawn_rate: 3.0
  throwing:
    target.speed: 150
    target.spawn_rate: 2.0
  blaster:
    target.speed: 250
    target.spawn_rate: 1.0
```

### Level Loader Implementation

Create `levels/level_loader.py` following Containment's pattern:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import yaml

@dataclass
class Objectives:
    type: str  # survive, score, endless
    max_misses: Optional[int]
    target_score: Optional[int]

@dataclass
class TargetConfig:
    count: int
    speed: float
    size: float
    spawn_rate: float

@dataclass
class DifficultyScaling:
    speed_increase_per_hit: float
    max_speed: float
    spawn_rate_decrease: float
    min_spawn_rate: float

@dataclass
class LevelConfig:
    name: str
    description: str
    difficulty: int
    author: str
    version: int
    objectives: Objectives
    target: TargetConfig
    scaling: DifficultyScaling
    # ... etc

def load_level(path: Path) -> LevelConfig:
    """Load and validate a level YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return _parse_level_config(data)

def list_levels() -> List[str]:
    """List available level names."""
    levels_dir = Path(__file__).parent / "examples"
    return [p.stem for p in levels_dir.glob("*.yaml")]
```

### CLI Integration

```python
ARGUMENTS = [
    {
        'name': '--level',
        'type': str,
        'default': 'classic_archery',
        'help': 'Level name or path to YAML file'
    },
    {
        'name': '--choose-level',
        'action': 'store_true',
        'default': False,
        'help': 'Show level chooser UI'
    },
    # ... other args
]
```

## Migration Strategy

### Phase 1: Input Module Standardization

1. **Update `input/` to re-export from common** - Replace local implementations with re-exports
2. **Update all internal imports** - Change `from input.X` to use common module
3. **Verify input still works** - Quick test that mouse input functions

### Phase 2: BaseGame Migration

1. **Create `game_mode.py`** with `DuckHuntMode(BaseGame)`
2. **Refactor `ClassicMode`** to `ClassicGameLogic` (remove palette/quiver responsibilities)
3. **Update `game_info.py`** to minimal factory
4. **Remove local `GameMode` base class**
5. **Update imports throughout** - Use `games.common` imports

### Phase 3: Level System Migration

1. **Create `levels/` directory structure**
2. **Create `levels/level_loader.py`** following Containment pattern
3. **Create `levels/schema.md`** documenting the format
4. **Convert existing YAML modes** to new level format
5. **Add `--level` and `--choose-level` CLI args**
6. **Optionally add level chooser UI** (can reuse Containment's)

### Phase 4: Cleanup

1. **Remove `engine.py`** (standalone loop no longer needed)
2. **Remove `main.py`** (use `dev_game.py duckhunt` instead)
3. **Remove `modes/`** (replaced by `levels/`)
4. **Remove `game/mode_loader.py`** (replaced by `levels/level_loader.py`)
5. **Update tests** to use new imports and structure
6. **Remove local venv** (use project root venv)
7. **Update README.md**

## Detailed Changes

### Files to Create

| File | Purpose |
|------|---------|
| `game_mode.py` | New main game class inheriting BaseGame |
| `levels/__init__.py` | Level system module exports |
| `levels/level_loader.py` | YAML parsing and validation |
| `levels/schema.md` | Level format documentation |
| `levels/examples/classic_archery.yaml` | Converted from modes/ |
| `levels/examples/classic_blaster.yaml` | Converted from modes/ |
| `levels/examples/endless.yaml` | New endless mode level |

### Files to Modify

| File | Changes |
|------|---------|
| `game_info.py` | Remove metadata, simplify to factory only |
| `input/__init__.py` | Re-export from common instead of local |
| `input/input_manager.py` | Re-export from common |
| `input/input_event.py` | Re-export from common |
| `input/sources/__init__.py` | Re-export from common |
| `input/sources/mouse.py` | Re-export from common |
| `input/sources/base.py` | Re-export from common |
| `game/modes/classic.py` | Remove palette/quiver init, accept as params |
| `game/modes/dynamic.py` | Same as classic.py |
| `game/game_mode.py` | Keep as internal ABC or remove |

### Files to Delete (Phase 4)

| File | Reason |
|------|--------|
| `engine.py` | Replaced by dev_game.py integration |
| `main.py` | Replaced by dev_game.py integration |
| `venv/` | Use project root venv |
| `modes/` | Replaced by `levels/` directory |
| `game/mode_loader.py` | Replaced by `levels/level_loader.py` |
| `game/game_mode.py` | Local ABC no longer needed |

### Import Changes

All files currently importing from local modules need updates:

```python
# Before
from input.input_event import InputEvent
from game.game_mode import GameMode
from models import DuckHuntInternalState

# After
from games.DuckHunt.input import InputEvent  # Re-exports from common
from games.common import BaseGame, GameState
# DuckHuntInternalState stays in models/duckhunt/ for internal use
```

## Risk Assessment

### High Risk

- **Test breakage** - Many tests import directly from internal modules
- **Standalone mode** - `main.py` / `engine.py` users need migration path

### Medium Risk

- **Mode loading** - YAML mode configs need to work with new structure
- **Trajectory system** - Complex trajectory code shouldn't be affected but needs testing

### Low Risk

- **Palette/Quiver** - Already using common modules, just moving initialization
- **Scoring/Feedback** - Internal modules, no interface changes

## Testing Strategy

### Before Migration

1. Run existing test suite: `cd games/DuckHunt && pytest`
2. Manual play test via `dev_game.py duckhunt`
3. Document current behavior for comparison

### During Migration

1. Keep old files until new ones verified
2. Add parallel tests for new structure
3. Compare game behavior frame-by-frame if needed

### After Migration

1. Full test suite passes
2. `dev_game.py duckhunt` works identically
3. All CLI arguments work
4. Palette cycling works (P key)
5. Quiver/retrieval works
6. All game modes load correctly

## Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1: Input Standardization | 30 min | None |
| Phase 2: BaseGame Migration | 2-3 hours | Phase 1 |
| Phase 3: Level System | 2-3 hours | Phase 2 |
| Phase 4: Cleanup | 1 hour | Phase 3 |
| Testing & Polish | 1-2 hours | All phases |

**Total: 7-10 hours**

## Design Decisions

1. **Standalone mode** - Remove `engine.py`/`main.py`. Use `dev_game.py duckhunt` exclusively.

2. **Internal organization** - Keep `game/` subdirectory with modes. DuckHunt is complex enough to warrant directory structure.

3. **Test migration** - Update tests directly to new imports. No compatibility shims (they're just tech debt).

4. **Level system** - Migrate YAML mode configs to Containment-style level system. This is now the standard pattern for data-driven game configuration.

## Success Criteria

### BaseGame Compliance

- [ ] `dev_game.py --list` shows DuckHunt with correct metadata
- [ ] `dev_game.py duckhunt --help` shows all arguments
- [ ] `dev_game.py duckhunt` plays identically to before
- [ ] Quiver/retrieval works correctly
- [ ] Palette cycling (P key) works
- [ ] No `sys.path` manipulation in any file

### Level System

- [ ] `dev_game.py duckhunt --level classic_archery` works
- [ ] `dev_game.py duckhunt --level endless` works
- [ ] `dev_game.py duckhunt --choose-level` shows level chooser UI
- [ ] `dev_game.py duckhunt --pacing archery` applies pacing overrides
- [ ] Level schema is documented in `levels/schema.md`

### Testing

- [ ] All existing tests pass (with updated imports)
- [ ] New level loader has unit tests
- [ ] Manual playtest confirms identical gameplay feel
