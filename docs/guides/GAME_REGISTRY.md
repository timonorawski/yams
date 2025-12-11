# Game Registry Guide

The Game Registry is AMS's automatic game discovery and management system. It scans the ContentFS for games and provides a unified interface for launching them with proper dependency injection.

## Overview

The registry discovers games from two sources:
1. **Python games** - Custom game classes inheriting from `BaseGame` (core repo only for security)
2. **YAML-only games** - Declarative games using `GameEngine` (all ContentFS layers)

All games are automatically discovered - no manual registration required.

## Quick Reference

```python
from games.registry import GameRegistry, get_registry
from ams.content_fs import ContentFS

# Initialize ContentFS and registry
content_fs = ContentFS(Path.cwd())
registry = get_registry(content_fs)

# List available games
games = registry.list_games()  # ['balloonpop', 'duckhunt', 'fruitsliceng', ...]

# Get game info
info = registry.get_game_info('balloonpop')
# GameInfo(name='Balloon Pop', slug='balloonpop', description='...', ...)

# Create game instance
game = registry.create_game(
    slug='balloonpop',
    width=1280,
    height=720,
    pacing='throwing',  # Game-specific arguments
    **kwargs
)
```

## Game Discovery

### Discovery Rules

The registry scans `games/` for directories containing:

1. **`game.yaml`** - YAML-only game (preferred, no Python required)
2. **`game_mode.py`** - Python game with `BaseGame` subclass
3. **`game_info.py`** - Legacy metadata (fallback for old games)

**Skipped directories:** `base`, `common`, `__pycache__`, names starting with `_` or `.`

### Security Model

**Python games (`game_mode.py`):**
- **Only discovered from core repository** (security boundary)
- Python code can execute arbitrary commands
- User-provided Python games are NOT loaded

**YAML games (`game.yaml`):**
- **Discovered from all ContentFS layers** (core, overlays, user)
- Lua scripting is sandboxed via lupa
- Safe for user-generated content

### Discovery Locations

```
Core Repo (Priority 0):
  /path/to/ArcheryGame/games/
    ├── BalloonPop/          # Python game (core only)
    │   └── game_mode.py
    └── FruitSliceNG/        # YAML game (core)
        └── game.yaml

Overlays (Priority 10+):
  /shared/team-content/games/
    └── CustomTargets/       # YAML game (overlay)
        └── game.yaml

User Dir (Priority 100):
  ~/.local/share/ams/games/
    └── MyGame/              # YAML game (user)
        └── game.yaml
```

## GameInfo Dataclass

Each discovered game has metadata stored in a `GameInfo` object:

```python
@dataclass
class GameInfo:
    name: str                      # Display name: "Balloon Pop"
    slug: str                      # Lowercase identifier: "balloonpop"
    description: str               # Short description
    version: str                   # Semantic version: "1.0.0"
    author: str                    # Author name
    module_path: str               # Import path: "games.BalloonPop"
    arguments: List[Dict[str, Any]]  # CLI argument definitions
    has_config: bool               # Has .env or config.py
    config_file: Optional[str]     # Config filename if present
```

### Accessing Game Info

```python
info = registry.get_game_info('balloonpop')
print(f"{info.name} v{info.version} by {info.author}")
print(f"Description: {info.description}")

# Get CLI arguments for argparse
args = registry.get_game_arguments('balloonpop')
for arg in args:
    parser.add_argument(arg['name'], **arg)
```

## Creating a Python Game

Python games live in the core repository and provide full control over game logic.

### 1. Directory Structure

```
games/MyGame/
├── __init__.py
├── game_mode.py          # Main game class (required)
├── game_info.py          # Factory function (required)
├── config.py             # Configuration
├── .env                  # Environment variables
├── input/                # Input abstraction (re-export from common)
│   ├── __init__.py
│   ├── input_event.py
│   ├── input_manager.py
│   └── sources/
│       ├── __init__.py
│       └── mouse.py
└── README.md
```

### 2. Game Class (game_mode.py)

```python
"""MyGame - A simple target game."""
import pygame
from typing import List

from ams.games import GameState
from ams.games.base_game import BaseGame
from games.MyGame.input.input_event import InputEvent


class MyGameMode(BaseGame):
    """My awesome game."""

    # =========================================================================
    # Game Metadata (used by registry)
    # =========================================================================

    NAME = "My Game"
    DESCRIPTION = "Pop targets for points"
    VERSION = "1.0.0"
    AUTHOR = "Your Name"

    # CLI Arguments (merged with BaseGame._BASE_ARGUMENTS)
    ARGUMENTS = [
        {
            'name': '--difficulty',
            'type': str,
            'default': 'normal',
            'choices': ['easy', 'normal', 'hard'],
            'help': 'Game difficulty level'
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
        difficulty: str = 'normal',
        pacing: str = 'throwing',
        **kwargs,  # palette, quiver_size, retrieval_pause from BaseGame
    ):
        super().__init__(**kwargs)  # Initialize palette and quiver

        self._difficulty = difficulty
        self._pacing = pacing
        self._score = 0
        self._game_over = False

    # =========================================================================
    # Required Methods
    # =========================================================================

    def _get_internal_state(self) -> GameState:
        """Map internal state to standard GameState."""
        if self._game_over:
            return GameState.GAME_OVER
        return GameState.PLAYING

    def get_score(self) -> int:
        """Return current score."""
        return self._score

    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events."""
        for event in events:
            x, y = event.position.x, event.position.y
            # Handle click at (x, y)

    def update(self, dt: float) -> None:
        """Update game logic."""
        pass

    def render(self, screen: pygame.Surface) -> None:
        """Draw game."""
        bg_color = self._palette.get_background_color()
        screen.fill(bg_color)
        # Draw game elements
```

### 3. Factory Function (game_info.py)

```python
"""MyGame - Game Info"""


def get_game_mode(**kwargs):
    """Factory function to create game instance.

    Called by registry with CLI arguments.
    """
    from games.MyGame.game_mode import MyGameMode
    return MyGameMode(**kwargs)
```

### 4. Register Discovery

**That's it!** The registry automatically discovers games by:
1. Finding `game_mode.py` in `games/MyGame/`
2. Looking for classes inheriting from `BaseGame`
3. Reading metadata from class attributes (NAME, DESCRIPTION, etc.)
4. Caching the game class for fast instantiation

### 5. Launch Your Game

```bash
# Development mode (mouse input, no AMS)
python dev_game.py mygame --difficulty hard

# Production mode (with detection backend)
python ams_game.py --game mygame --backend mouse --difficulty hard

# List all games
python ams_game.py --list-games

# See game-specific options
python dev_game.py mygame --help
```

## Creating a YAML-Only Game

YAML games require no Python boilerplate - just declare entities, behaviors, and rules in YAML.

### 1. Minimal Structure

```
games/MyGameNG/
└── game.yaml
```

### 2. Game Definition (game.yaml)

```yaml
# yaml-language-server: $schema=../../schemas/game.schema.json

name: "My Game"
description: "A YAML-driven game"
version: "1.0.0"
author: "Your Name"

screen_width: 800
screen_height: 600
background_color: [20, 20, 40]

defaults:
  lives: 3

win_condition: reach_score
win_target: 1000

# =============================================================================
# Entity Types
# =============================================================================

entity_types:
  # Base type - floating target
  target:
    width: 50
    height: 50
    behaviors: [gravity, destroy_offscreen]
    behavior_config:
      gravity:
        acceleration: 600
      destroy_offscreen:
        edges: bottom
        margin: 50
    tags: [target]
    render:
      - shape: circle
        color: red
        radius: 0.5

  # Spawner - creates targets
  spawner:
    width: 1
    height: 1
    behaviors:
      - lua: |
          local spawner = {}

          function spawner.on_spawn(entity_id)
              ams.set_prop(entity_id, "timer", 0)
          end

          function spawner.on_update(entity_id, dt)
              local timer = ams.get_prop(entity_id, "timer") or 0
              timer = timer + dt

              if timer >= 2.0 then
                  ams.set_prop(entity_id, "timer", 0)

                  -- Spawn random target
                  local x = ams.random_range(100, 700)
                  ams.spawn("target", x, 650, 0, -200, 0, 0, "", "")
              else
                  ams.set_prop(entity_id, "timer", timer)
              end
          end

          return spawner
    render: []

# =============================================================================
# Input Mapping
# =============================================================================

input_mapping:
  target:
    on_hit:
      transform:
        type: destroy

# =============================================================================
# Player Configuration
# =============================================================================

player:
  type: spawner
  spawn: [0, 0]
```

### 3. Register Discovery

**Automatic!** The registry:
1. Finds `game.yaml` in `games/MyGameNG/`
2. Uses `GameEngine.from_yaml()` to create a dynamic game class
3. Extracts metadata from YAML (name, description, author)
4. Makes the game available via the slug `mygameng`

### 4. Launch Your Game

```bash
# With mouse input
python ams_game.py --game mygameng --backend mouse

# With laser pointer
python ams_game.py --game mygameng --backend laser --fullscreen

# List all games (YAML games appear alongside Python games)
python ams_game.py --list-games
```

### 5. Extended Structure (Optional)

```
games/MyGameNG/
├── game.yaml           # Game definition
├── levels/             # Level files
│   ├── 01_intro.yaml
│   ├── 02_harder.yaml
│   └── groups/
│       └── campaign.yaml
└── assets/             # Game assets
    ├── sprites.png
    └── sounds/
        └── hit.wav
```

Run with levels:
```bash
python ams_game.py --game mygameng --backend mouse --level 01_intro
```

## ContentFS Integration

The registry automatically injects `ContentFS` into games for layered content access.

### For Python Games

```python
class MyGameMode(BaseGame):
    def __init__(self, content_fs=None, **kwargs):
        super().__init__(**kwargs)
        self._content_fs = content_fs  # Injected by registry

    def _load_sprite(self, relative_path: str):
        """Load sprite via ContentFS (supports user overrides)."""
        if self._content_fs:
            # Resolve through layered filesystem
            real_path = self._content_fs.getsyspath(
                f'games/MyGame/assets/{relative_path}'
            )
        else:
            # Fallback for standalone mode
            real_path = Path(__file__).parent / 'assets' / relative_path

        return pygame.image.load(str(real_path))
```

### For YAML Games

ContentFS is automatically available - just reference assets:

```yaml
assets:
  sprites:
    _sheet:
      file: sprites.png  # Resolved via ContentFS
```

User can override by placing file in `~/.local/share/ams/games/MyGameNG/assets/sprites.png`.

## CLI Argument System

### Argument Format

```python
ARGUMENTS = [
    {
        'name': '--my-option',      # CLI flag (dashes, not underscores)
        'type': str,                # str, int, float
        'default': 'value',         # Default value
        'help': 'Description',      # Help text
        'choices': ['a', 'b'],      # Optional: valid values
    },
    {
        'name': '--enable-feature',
        'action': 'store_true',     # For boolean flags
        'default': False,
        'help': 'Enable cool feature',
    },
]
```

### BaseGame Automatic Arguments

All games inheriting from `BaseGame` automatically get these arguments:

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--palette` | str | 'default' | Test palette (for CV tuning) |
| `--quiver-size` | int | None | Shots before retrieval (None=unlimited) |
| `--retrieval-pause` | int | 10 | Seconds for arrow retrieval |

### Usage in ams_game.py

```python
# Registry provides game-specific arguments
registry = get_registry(content_fs)
game_args = registry.get_game_arguments(args.game)

# Add to argument parser
parser = argparse.ArgumentParser()
for arg_def in game_args:
    name = arg_def.pop('name')
    parser.add_argument(name, **arg_def)

# Parse and pass to game
args = parser.parse_args()
game = registry.create_game(
    args.game,
    width=args.width,
    height=args.height,
    **vars(args)  # All CLI arguments passed to game
)
```

## Registry API Reference

### Initialization

```python
from games.registry import GameRegistry, get_registry
from ams.content_fs import ContentFS

# Create registry instance
content_fs = ContentFS(core_dir)
registry = GameRegistry(content_fs)

# Or use singleton
registry = get_registry(content_fs)  # First call initializes
registry = get_registry()             # Subsequent calls
```

### Listing Games

```python
# Get all game slugs
games = registry.list_games()
# ['balloonpop', 'containment', 'duckhunt', 'fruitsliceng', ...]

# Get all game info
all_games = registry.get_all_games()
# {'balloonpop': GameInfo(...), 'duckhunt': GameInfo(...), ...}

# Get specific game info
info = registry.get_game_info('balloonpop')
if info:
    print(f"{info.name} - {info.description}")
```

### Creating Games

```python
# Basic creation
game = registry.create_game(
    slug='balloonpop',
    width=1280,
    height=720,
)

# With game-specific arguments
game = registry.create_game(
    slug='balloonpop',
    width=1280,
    height=720,
    pacing='archery',      # Game-specific
    difficulty='hard',     # Game-specific
    palette='bw',          # BaseGame argument
    quiver_size=6,         # BaseGame argument
)

# ContentFS is automatically injected
# game._content_fs is available
```

### Getting Game Class

```python
# Get cached game class (for inspection)
game_class = registry.get_game_class('balloonpop')
if game_class:
    print(f"Game class: {game_class.__name__}")
    print(f"Version: {game_class.VERSION}")
    print(f"Arguments: {game_class.ARGUMENTS}")
```

### Creating Input Manager

```python
# AMS mode (with detection backend)
input_manager = registry.create_input_manager(
    slug='balloonpop',
    ams_session=ams_session,
    width=1280,
    height=720,
)

# Standalone mode (mouse input)
input_manager = registry.create_input_manager(
    slug='balloonpop',
    ams_session=None,
    width=1280,
    height=720,
)
```

## Examples

### Example 1: List All Games

```python
from pathlib import Path
from ams.content_fs import ContentFS
from games.registry import get_registry

# Initialize
content_fs = ContentFS(Path.cwd())
registry = get_registry(content_fs)

# List all games with details
for slug in registry.list_games():
    info = registry.get_game_info(slug)
    print(f"{info.name:<20} v{info.version:<8} by {info.author}")
    print(f"  Slug: {info.slug}")
    print(f"  {info.description}")
    if info.arguments:
        print(f"  Arguments: {len(info.arguments)} custom")
    print()
```

### Example 2: Launch Game with CLI Args

```python
import argparse
from pathlib import Path
from ams.content_fs import ContentFS
from games.registry import get_registry

# Initialize
content_fs = ContentFS(Path.cwd())
registry = get_registry(content_fs)

# Parse game selection
parser = argparse.ArgumentParser()
parser.add_argument('--game', required=True)
base_args, remaining = parser.parse_known_args()

# Add game-specific arguments
game_args = registry.get_game_arguments(base_args.game)
for arg_def in game_args:
    name = arg_def.pop('name')
    parser.add_argument(name, **arg_def)

# Parse all arguments
args = parser.parse_args()

# Create game with all arguments
game = registry.create_game(
    slug=args.game,
    width=1280,
    height=720,
    **{k: v for k, v in vars(args).items() if k != 'game'}
)

# Game loop
while running:
    game.update(dt)
    game.render(screen)
```

### Example 3: Inspect Game Metadata

```python
from pathlib import Path
from ams.content_fs import ContentFS
from games.registry import get_registry

content_fs = ContentFS(Path.cwd())
registry = get_registry(content_fs)

# Inspect game
slug = 'balloonpop'
info = registry.get_game_info(slug)

print(f"Game: {info.name}")
print(f"Description: {info.description}")
print(f"Version: {info.version}")
print(f"Author: {info.author}")
print()

print("CLI Arguments:")
for arg in info.arguments:
    name = arg.get('name', '?')
    arg_type = arg.get('type', arg.get('action', '?'))
    default = arg.get('default', 'None')
    help_text = arg.get('help', '')
    print(f"  {name:<25} {arg_type.__name__:<10} (default: {default})")
    print(f"    {help_text}")
```

## Troubleshooting

### Game Not Discovered

**Symptoms:**
- Game doesn't appear in `--list-games`
- Error: "Unknown game: mygame"

**Solutions:**

1. **Check directory structure:**
   ```bash
   # Must be in games/ directory
   ls games/MyGame/
   # Should contain: game.yaml OR game_mode.py
   ```

2. **Check for import errors:**
   ```bash
   python -c "from games.MyGame.game_mode import *"
   ```

3. **Verify BaseGame inheritance:**
   ```python
   # game_mode.py must have:
   class MyGameMode(BaseGame):  # Must inherit from BaseGame
       NAME = "My Game"         # Must have NAME
   ```

4. **Check YAML syntax:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('games/MyGame/game.yaml'))"
   ```

### Python Game in User Directory Ignored

**This is intentional for security.** Python games can execute arbitrary code.

**Solutions:**
- Move Python games to core repository: `<repo>/games/MyGame/`
- Convert to YAML-only game (safe for user directories)

### Arguments Not Available

**Symptoms:**
- CLI arguments don't appear in `--help`
- Game doesn't receive argument values

**Solutions:**

1. **Check ARGUMENTS is a class attribute:**
   ```python
   class MyGameMode(BaseGame):
       ARGUMENTS = [...]  # Class attribute (correct)

   # Not this:
   def __init__(self):
       self.ARGUMENTS = [...]  # Instance attribute (wrong)
   ```

2. **Verify argument format:**
   ```python
   ARGUMENTS = [
       {
           'name': '--my-arg',  # Must have 'name'
           'type': str,         # Must have 'type' or 'action'
           'default': 'value',  # Must have 'default'
           'help': 'text',      # Must have 'help'
       }
   ]
   ```

3. **Check for naming conflicts:**
   ```python
   # Don't use reserved names:
   '--game', '--backend', '--width', '--height'
   ```

### ContentFS Not Available in Game

**Symptoms:**
- `self._content_fs` is None
- Assets from user directory not loaded

**Solutions:**

1. **Accept content_fs in __init__:**
   ```python
   def __init__(self, content_fs=None, **kwargs):
       super().__init__(**kwargs)
       self._content_fs = content_fs  # Save it
   ```

2. **Use registry.create_game():**
   ```python
   # Correct (injects content_fs):
   game = registry.create_game('mygame', width=800, height=600)

   # Wrong (no content_fs):
   from games.MyGame.game_mode import MyGameMode
   game = MyGameMode(width=800, height=600)
   ```

### YAML Game Not Loading Assets

**Check asset paths:**
```yaml
# Relative to game directory:
assets:
  sprites:
    _sheet:
      file: sprites.png  # games/MyGame/assets/sprites.png
```

**Verify file exists:**
```bash
ls games/MyGame/assets/sprites.png
# OR in user directory:
ls ~/.local/share/ams/games/MyGame/assets/sprites.png
```

## See Also

- [YAML Game Quickstart](YAML_GAME_QUICKSTART.md) - Creating YAML-only games
- [New Game Quickstart](NEW_GAME_QUICKSTART.md) - Creating Python games
- [Game Registry Architecture](../architecture/GAME_REGISTRY.md) - Technical details
- [Base Game API](../architecture/BASE_GAME_API.md) - BaseGame reference
- [Lua Scripting Guide](lua_scripting.md) - Writing Lua behaviors
