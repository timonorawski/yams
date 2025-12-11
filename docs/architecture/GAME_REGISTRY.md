# Game Registry & Content Loading Architecture

This document describes how AMS discovers, loads, and launches games through its layered content system.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Application Startup                              │
│  ams_game.py / dev_game.py                                              │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           ContentFS                                      │
│  Layered virtual filesystem (PyFilesystem2 MultiFS)                     │
│                                                                          │
│  Priority 0:   Core      (/path/to/repo)                                │
│  Priority 10+: Overlays  (AMS_OVERLAY_DIRS)                             │
│  Priority 100: User      (~/.local/share/ams or AMS_DATA_DIR)           │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          GameRegistry                                    │
│  - Scans ContentFS for games (games/*/game.yaml or game_mode.py)        │
│  - Builds GameInfo catalog with metadata                                │
│  - Creates game class instances on demand                               │
│  - Injects ContentFS into games for asset resolution                    │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          GameEngine                                      │
│  - Receives ContentFS from registry                                     │
│  - Loads game.yaml definition                                           │
│  - Loads Lua behaviors from ContentFS                                   │
│  - Resolves assets (sprites, sounds) via ContentFS                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## ContentFS: Layered Content System

### Purpose

ContentFS provides a unified interface for accessing files across multiple directories with priority-based shadowing. This enables:

- **User customization**: Override any core asset without modifying source files
- **Team overlays**: Share custom content across a team via network paths
- **Modding support**: Layer third-party content on top of core games

### Layer Priority

Higher priority layers shadow (override) lower priority layers:

| Priority | Layer | Source | Example Path |
|----------|-------|--------|--------------|
| 100 | User | `AMS_DATA_DIR` or XDG default | `~/.local/share/ams/` |
| 10-90 | Overlays | `AMS_OVERLAY_DIRS` (colon-separated) | `/shared/ams-content/` |
| 0 | Core | Repository root | `/path/to/ArcheryGame/` |

### XDG Default Paths

When `AMS_DATA_DIR` is not set, ContentFS uses platform-appropriate defaults:

```python
# macOS
~/Library/Application Support/AMS/

# Windows
%APPDATA%/AMS/

# Linux/BSD (XDG compliant)
~/.local/share/ams/   # or $XDG_DATA_HOME/ams/
```

### Directory Structure

All layers follow the same structure:

```
<layer_root>/
├── games/                      # Game definitions
│   └── MyGame/
│       ├── game.yaml           # Game definition
│       ├── levels/             # Level files
│       │   ├── 01_intro.yaml
│       │   └── groups/
│       │       └── campaign.yaml
│       └── assets/             # Game assets
│           ├── sprites.png
│           └── sounds/
│               └── shot.ogg
└── behaviors/                  # Shared Lua behaviors
    └── lua/
        └── my_behavior.lua
```

### Key Methods

```python
content_fs = ContentFS(core_dir)

# Check existence (any layer)
content_fs.exists('games/DuckHunt/game.yaml')  # True/False

# Read text (highest priority layer wins)
yaml_text = content_fs.readtext('games/DuckHunt/game.yaml')

# Get real filesystem path (for pygame.image.load)
sprite_path = content_fs.getsyspath('games/DuckHunt/assets/sprites.png')

# List directory (merged across all layers)
games = content_fs.listdir('games')  # ['DuckHunt', 'BalloonPop', ...]

# Debug: which layer provides a file?
source = content_fs.get_layer_source('games/DuckHunt/assets/sprites.png')
# Returns 'user', 'overlay_0', or 'core'
```

### Sandbox Security

PyFilesystem2's OSFS enforces sandbox boundaries. Path traversal attempts are rejected:

```python
content_fs.exists('../../../etc/passwd')
# Raises: IllegalBackReference: path contains back-references outside of filesystem

content_fs.exists('games/../../../etc/passwd')
# Raises: IllegalBackReference

content_fs.exists('/etc/passwd')
# Returns: False (absolute paths don't exist within sandbox)
```

Each layer (core, overlays, user) is independently sandboxed. A malicious path in user content cannot escape to access core files or system files.

### WASM Compatibility

The current implementation uses PyFilesystem2's MultiFS, which is not compatible with Emscripten/WebAssembly builds. For browser deployment via pygbag, an alternative implementation using Emscripten's virtual filesystem (MEMFS/IDBFS) will be needed. The ContentFS interface remains stable. Any WASM implementation must maintain equivalent sandbox enforcement.

---

## GameRegistry: Game Discovery & Creation

### Purpose

GameRegistry scans ContentFS for available games and provides a unified interface for:

- Listing available games
- Retrieving game metadata and CLI arguments
- Creating game instances with proper dependency injection

### Game Discovery

On initialization, GameRegistry scans `games/` in ContentFS for valid games:

```python
registry = GameRegistry(content_fs)
games = registry.list_games()  # ['balloonpop', 'duckhunt', 'sweetphysicsng', ...]
```

#### Discovery Rules

A directory is recognized as a game if it contains:

1. **`game.yaml`** - YAML-only game (preferred, uses GameEngine)
2. **`game_mode.py`** - Python game with BaseGame subclass
3. **`game_info.py`** - Legacy metadata module (fallback)

Skipped directories: `base`, `common`, `__pycache__`, names starting with `_` or `.`

### Game Types

#### YAML-Only Games (GameEngine)

Most games are defined entirely in YAML with Lua behaviors:

```
games/SweetPhysicsNG/
├── game.yaml           # Entity types, behaviors, collisions
├── levels/
│   ├── 01_simple.yaml
│   └── groups/
│       └── tutorial.yaml
└── assets/
    └── sprites.png
```

The registry uses `GameEngine.from_yaml()` to create a dynamic game class:

```python
# Registry internally does:
game_class = GameEngine.from_yaml(yaml_path)
# game_class is now a configured GameEngine subclass

# Later, when launching:
game = game_class(content_fs=content_fs, **kwargs)
```

#### Python Games (BaseGame subclass)

Games with custom Python logic define a class in `game_mode.py`:

```python
# games/MyGame/game_mode.py
class MyGameMode(BaseGame):
    NAME = "My Game"
    DESCRIPTION = "A custom game"

    def update(self, dt): ...
    def render(self, screen): ...
```

### GameInfo Structure

Each discovered game has a `GameInfo` record:

```python
@dataclass
class GameInfo:
    name: str           # Display name ("Sweet Physics")
    slug: str           # Identifier ("sweetphysicsng")
    description: str    # Short description
    version: str        # Semantic version
    author: str         # Author name
    module_path: str    # Import path ("games.SweetPhysicsNG")
    arguments: List[Dict]  # CLI argument definitions
    has_config: bool    # Has .env or config.py
    config_file: str    # Config filename if present
```

### Creating Games

```python
# Get registry (initialized once at startup)
registry = get_registry(content_fs)

# Create game instance
game = registry.create_game(
    slug='sweetphysicsng',
    width=1280,
    height=720,
    level='01_simple',
    # ... other game-specific kwargs
)
```

The registry:
1. Looks up the game class
2. Injects `content_fs` into kwargs
3. Instantiates the game class

---

## GameEngine: YAML-Driven Game Framework

### Purpose

GameEngine is the runtime for YAML-defined games. It:

- Parses `game.yaml` into a `GameDefinition`
- Manages entities via `BehaviorEngine`
- Loads and executes Lua behaviors
- Handles rendering, input, and collisions

### Initialization Flow

```python
def __init__(self, content_fs, skin='default', lives=3, **kwargs):
    self._content_fs = content_fs

    # 1. Create behavior engine
    self._behavior_engine = BehaviorEngine(...)

    # 2. Load core Lua behaviors (ams/behaviors/lua/*.lua)
    self._behavior_engine.load_behaviors_from_dir()

    # 3. Load game-specific behaviors (games/MyGame/behaviors/*.lua)
    if self.BEHAVIORS_DIR:
        self._behavior_engine.load_behaviors_from_dir(self.BEHAVIORS_DIR)

    # 4. Load game definition from YAML
    self._game_def = self._load_game_definition(self.GAME_DEF_FILE)

    # 5. Create rendering skin
    self._skin = self._get_skin(skin)
    self._skin.set_game_definition(self._game_def, assets_dir)

    # 6. Initialize base game (may load levels)
    super().__init__(**kwargs)
```

### from_yaml Factory

For YAML-only games, `GameEngine.from_yaml()` creates a configured subclass:

```python
@classmethod
def from_yaml(cls, yaml_path: Path) -> Type['GameEngine']:
    # Load metadata from YAML
    with open(yaml_path) as f:
        game_data = yaml.safe_load(f)

    name = game_data.get('name', yaml_path.parent.name)
    game_slug = yaml_path.parent.name.lower()

    # Create dynamic subclass
    class YAMLGameMode(cls):
        NAME = name
        GAME_DEF_FILE = yaml_path
        LEVELS_DIR = yaml_path.parent / 'levels'
        GAME_SLUG = game_slug

        def __init__(self, content_fs, **kwargs):
            super().__init__(content_fs, skin='default', **kwargs)

        def _get_skin(self, skin_name):
            return GameEngineSkin()

    return YAMLGameMode
```

### Asset Resolution

Assets are resolved through ContentFS, enabling user overrides:

```python
# In GameEngineSkin._load_sprite():
if self._content_fs:
    # Resolve through layered filesystem
    real_path = self._content_fs.getsyspath(
        f'games/{self._game_slug}/assets/{config.file}'
    )
else:
    # Fallback to direct path
    real_path = str(self._assets_dir / config.file)

surface = pygame.image.load(real_path)
```

### Level Loading

Levels are loaded from `games/<slug>/levels/`:

```yaml
# games/SweetPhysicsNG/levels/01_simple.yaml
name: "Simple Drop"
lives: 3
player_x: 400
player_y: 50
layout:
  level_name: simple_drop
entities:
  - type: goal
    x: 350
    y: 520
```

Level groups define campaigns:

```yaml
# games/SweetPhysicsNG/levels/groups/tutorial.yaml
name: "Tutorial"
levels:
  - 01_simple_drop
  - 02_swing_timing
  - 03_two_ropes
```

---

## Startup Sequence

### ams_game.py

```python
def main():
    # 1. Initialize layered content filesystem
    core_dir = Path(__file__).parent
    content_fs = ContentFS(core_dir)

    # 2. Initialize game registry (discovers all games)
    registry = get_registry(content_fs)
    available_games = registry.list_games()

    # 3. Parse CLI arguments
    args = parse_args(available_games)

    # 4. Initialize pygame display
    screen = pygame.display.set_mode((width, height))

    # 5. Create detection backend (mouse, laser, object)
    backend = create_detection_backend(args, width, height)

    # 6. Create AMS session
    ams = AMSSession(backend, width, height)

    # 7. Create game instance
    game = registry.create_game(args.game, width, height, **game_kwargs)

    # 8. Run game loop
    while running:
        events = ams.poll_events()
        game.handle_input(events)
        game.update(dt)
        game.render(screen)
```

---

## Extension Points

### Adding a New Game

1. Create `games/MyGame/game.yaml`:
   ```yaml
   name: "My Game"
   description: "A new game"
   entity_types:
     target:
       width: 50
       height: 50
       behaviors: [gravity]
   ```

2. Optionally add levels: `games/MyGame/levels/01_intro.yaml`

3. Optionally add custom behaviors: `games/MyGame/behaviors/my_behavior.lua`

4. The game is automatically discovered on next startup.

### User Content Override

To override a core asset:

```bash
# Create user content directory
mkdir -p ~/.local/share/ams/games/DuckHunt/assets/

# Copy modified sprite
cp my_custom_sprites.png ~/.local/share/ams/games/DuckHunt/assets/sprites.png

# Run game - user sprite shadows core sprite
python ams_game.py --game duckhunt --backend mouse
```

### Adding an Overlay

```bash
# Set overlay directory
export AMS_OVERLAY_DIRS=/shared/team-content:/mods/expansion-pack

# Games and assets from overlays are now available
python ams_game.py --list-games
```

---

## Class Reference

| Class | File | Purpose |
|-------|------|---------|
| `ContentFS` | `ams/content_fs.py` | Layered virtual filesystem |
| `GameRegistry` | `games/registry.py` | Game discovery and creation |
| `GameInfo` | `games/registry.py` | Game metadata container |
| `GameEngine` | `games/common/game_engine.py` | YAML-driven game runtime |
| `GameEngineSkin` | `games/common/game_engine.py` | Rendering abstraction |
| `BehaviorEngine` | `ams/behaviors/engine.py` | Lua behavior execution |
| `BaseGame` | `games/common/base_game.py` | Abstract game base class |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AMS_DATA_DIR` | XDG default | User content directory |
| `AMS_OVERLAY_DIRS` | (none) | Colon-separated overlay paths |
| `AMS_SKIP_SCHEMA_VALIDATION` | `0` | Skip YAML schema validation |
