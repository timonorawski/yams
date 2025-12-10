# BaseGame API Reference

The `BaseGame` class is the abstract base class for all AMS games. It provides a consistent interface for the game registry, dev_game.py, ams_game.py, and the web controller.

## Features

- **Metadata** - Game name, description, version, author
- **CLI Arguments** - Dynamic argument system for configuration
- **Palette System** - CV-compatible color management
- **Quiver System** - Ammo/shot tracking with retrieval pauses
- **Level Support** - Optional YAML-based levels with groups/campaigns

## Quick Start

```python
from games.common.base_game import BaseGame
from games.common.game_state import GameState

class MyGame(BaseGame):
    # Metadata (class attributes)
    NAME = "My Game"
    DESCRIPTION = "A fun projectile game"
    VERSION = "1.0.0"
    AUTHOR = "Your Name"

    # CLI arguments
    ARGUMENTS = [
        {'name': '--difficulty', 'type': str, 'default': 'normal',
         'choices': ['easy', 'normal', 'hard'], 'help': 'Game difficulty'},
        {'name': '--time-limit', 'type': int, 'default': 60,
         'help': 'Time limit in seconds (0=unlimited)'},
    ]

    def __init__(self, difficulty='normal', time_limit=60, **kwargs):
        super().__init__(**kwargs)  # Handles palette, quiver
        self._difficulty = difficulty
        self._time_limit = time_limit
        self._score = 0
        self._game_over = False

    def _get_internal_state(self) -> GameState:
        if self._game_over:
            return GameState.GAME_OVER
        return GameState.PLAYING

    def get_score(self) -> int:
        return self._score

    def handle_input(self, events):
        for event in events:
            # event.position.x, event.position.y are pixel coordinates
            if self._check_hit(event.position.x, event.position.y):
                self._score += 100

    def update(self, dt: float):
        # dt is delta time in seconds
        pass

    def render(self, screen):
        screen.fill((0, 0, 0))
        # Draw game elements...
```

## Class Attributes (Metadata)

These are read by the game registry for discovery and display:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `NAME` | `str` | Yes | Display name shown in UI |
| `DESCRIPTION` | `str` | Yes | Short description of gameplay |
| `VERSION` | `str` | No | Semantic version (default: "1.0.0") |
| `AUTHOR` | `str` | No | Author/team name (default: "Unknown") |
| `ARGUMENTS` | `List[Dict]` | No | CLI argument definitions |

## ARGUMENTS Format

Each argument is a dictionary compatible with `argparse.add_argument()`:

```python
ARGUMENTS = [
    {
        'name': '--difficulty',      # CLI flag (required)
        'type': str,                 # Python type: str, int, float, bool
        'default': 'normal',         # Default value
        'help': 'Game difficulty',   # Description for help text
        'choices': ['easy', 'normal', 'hard'],  # Optional: valid values
    },
    {
        'name': '--time-limit',
        'type': int,
        'default': 60,
        'help': 'Time limit in seconds (0=unlimited)',
    },
    {
        'name': '--endless',
        'type': bool,
        'default': False,
        'action': 'store_true',      # For boolean flags
        'help': 'Enable endless mode',
    },
]
```

### Argument Name Conversion

CLI argument names are converted to Python kwargs:
- `--difficulty` → `difficulty`
- `--time-limit` → `time_limit`
- `--max-escaped` → `max_escaped`

### Base Arguments (Auto-Included)

These arguments are automatically available to all games via `_BASE_ARGUMENTS`:

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--palette` | `str` | `None` | Test palette name (full, bw, warm, cool, etc.) |
| `--quiver-size` | `int` | `None` | Shots before retrieval pause (0=unlimited) |
| `--retrieval-pause` | `int` | `30` | Seconds for retrieval (0=manual) |

## Abstract Methods (Must Implement)

### `_get_internal_state() -> GameState`

Map your internal game state to the standard `GameState` enum.

```python
def _get_internal_state(self) -> GameState:
    if self._player_died:
        return GameState.GAME_OVER
    if self._level_complete:
        return GameState.WON
    return GameState.PLAYING
```

**GameState Values:**
- `GameState.PLAYING` - Active gameplay
- `GameState.PAUSED` - Manual pause
- `GameState.RETRIEVAL` - Ammo retrieval pause (handled by BaseGame)
- `GameState.GAME_OVER` - Loss/failure
- `GameState.WON` - Victory/success

### `get_score() -> int`

Return the current score as an integer.

```python
def get_score(self) -> int:
    return self._points
```

### `handle_input(events: List[InputEvent]) -> None`

Process input events. Each `InputEvent` has:
- `position.x` - X coordinate in pixels
- `position.y` - Y coordinate in pixels
- `timestamp` - When the event occurred

```python
def handle_input(self, events):
    for event in events:
        x, y = event.position.x, event.position.y

        # Check for hits on game objects
        for target in self._targets:
            if target.contains_point(x, y):
                self._score += target.points
                target.destroy()
                break

        # Track shot usage (for quiver system)
        if self._use_shot():
            self._start_retrieval()
```

### `update(dt: float) -> None`

Update game logic. Called every frame.

```python
def update(self, dt: float):
    # Handle retrieval state
    if self._in_retrieval:
        if self._update_retrieval(dt):
            self._end_retrieval()
        return

    # Normal game update
    for entity in self._entities:
        entity.update(dt)

    self._spawn_timer -= dt
    if self._spawn_timer <= 0:
        self._spawn_target()
        self._spawn_timer = self._spawn_interval
```

### `render(screen: pygame.Surface) -> None`

Draw the game to the screen.

```python
def render(self, screen):
    screen.fill(self._palette.get_background_color())

    for entity in self._entities:
        entity.render(screen)

    self._render_ui(screen)

    # Show retrieval overlay if needed
    if self.state == GameState.RETRIEVAL:
        self._render_retrieval_screen(screen)
```

## Built-in Systems

### Quiver System (Ammo Management)

For games with physical ammo constraints (arrows, darts, etc.):

```python
# In __init__, quiver is created from CLI args automatically via super().__init__()

# In handle_input:
def handle_input(self, events):
    for event in events:
        # Check if quiver is empty before allowing shot
        if self._quiver and self._quiver.is_empty:
            continue

        # Process the shot...
        self._process_hit(event)

        # Record shot usage, start retrieval if empty
        if self._use_shot():
            self._start_retrieval()

# In update:
def update(self, dt):
    if self._in_retrieval:
        # Auto-retrieval (timed)
        if self._update_retrieval(dt):
            self._end_retrieval()
        return

    # Normal update...
```

**Quiver Properties:**
- `self._quiver` - `QuiverState` or `None` if unlimited
- `self.shots_remaining` - Shots left, or `None` if unlimited
- `self.quiver_size` - Total capacity, or `None` if unlimited

**Quiver Methods:**
- `self._use_shot()` → `bool` - Record shot, returns `True` if now empty
- `self._start_retrieval()` - Enter retrieval state
- `self._end_retrieval()` - Exit retrieval, refill quiver
- `self._update_retrieval(dt)` → `bool` - Update timer, returns `True` when done

### Palette System (Color Management)

For CV compatibility, games should use colors from the palette:

```python
# Get colors for game elements
target_color = self._palette.random_target_color()
bg_color = self._palette.get_background_color()
ui_color = self._palette.get_ui_color()
colors = self._palette.get_target_colors(count=4)

# Palette info
palette_name = self._palette.name  # 'full', 'warm', 'bw', etc.

# Switch palettes (for testing)
self.set_palette('warm')
self.cycle_palette()  # Cycles through available palettes
```

**Available Test Palettes:**
- `full` - All primary/secondary colors
- `bw` - Black and white only
- `warm` - Red, orange, yellow tones
- `cool` - Blue, cyan, purple tones
- `mono_red` / `mono_green` - Single-hue variations
- `limited` - Only 3 colors
- `orange_dart` - Colors safe when orange dart is projectile

**Palette Callback:**
```python
def _on_palette_changed(self):
    """Called when palette changes. Override to update entity colors."""
    for entity in self._entities:
        entity.color = self._palette.random_target_color()
```

## State Property

The `state` property combines internal state with retrieval state:

```python
@property
def state(self) -> GameState:
    if self._in_retrieval:
        return GameState.RETRIEVAL
    return self._get_internal_state()
```

**Do not override `state`** - override `_get_internal_state()` instead.

## Optional Methods

### `reset() -> None`

Reset game to initial state (for replay without recreating instance):

```python
def reset(self):
    super().reset()  # Clears retrieval state, refills quiver
    self._score = 0
    self._entities.clear()
    self._game_over = False
```

## Game Actions (Web Controller UI)

Games can expose contextual actions to the web controller UI by implementing two methods.

### `get_available_actions() -> List[Dict]`

Returns actions currently available based on game state. Each action has:

- `id` - Unique identifier (e.g., 'retry', 'skip', 'next_level')
- `label` - Display text for the button
- `style` - Visual style: 'primary' (cyan), 'secondary' (gray), 'danger' (red)

```python
def get_available_actions(self) -> list:
    actions = []

    # Always allow restart when a level is loaded
    if self._current_level is not None:
        if self._level_state == LevelState.LOST:
            actions.append({'id': 'retry', 'label': 'Retry Level', 'style': 'primary'})
        else:
            actions.append({'id': 'retry', 'label': 'Restart Level', 'style': 'secondary'})

    # Additional actions based on state
    if self._level_state == LevelState.LOST and self._current_group:
        actions.append({'id': 'skip', 'label': 'Skip Level', 'style': 'secondary'})

    return actions
```

### `execute_action(action_id: str) -> bool`

Handle an action triggered from the web UI. Return `True` if handled.

```python
def execute_action(self, action_id: str) -> bool:
    if action_id == 'retry':
        self._initialize_level()
        return True
    elif action_id == 'skip':
        if self._level_complete():
            return True
    return False
```

### Common Actions

| Action ID | Use Case |
|-----------|----------|
| `retry` | Restart current level (always available during level play) |
| `skip` | Skip to next level in group (when stuck/lost) |
| `next` | Manually advance to next level (during win delay) |

## Class Methods

### `get_arguments() -> List[Dict]`

Returns all CLI arguments (game-specific + base arguments). Called by registry.

### `get_info() -> Dict`

Returns game metadata dictionary:
```python
{
    'name': 'My Game',
    'description': 'A fun game',
    'version': '1.0.0',
    'author': 'Your Name',
    'arguments': [...]
}
```

## Game Discovery

Games are auto-discovered by the registry when:
1. Located in `games/<GameName>/` directory
2. Contains `game_mode.py` with a `BaseGame` subclass
3. The class is defined in that module (not imported)

Directory structure:
```
games/
└── MyGame/
    ├── __init__.py
    ├── game_mode.py      # Contains BaseGame subclass
    ├── config.py         # Optional: SCREEN_WIDTH, SCREEN_HEIGHT constants
    └── input/            # Optional: Custom input handling
        ├── __init__.py
        ├── input_event.py
        ├── input_manager.py
        └── sources/
            └── mouse.py
```

## Complete Example

```python
"""
Simple Target Practice Game
"""
import random
import pygame
from typing import List, Optional

from games.common.base_game import BaseGame
from games.common.game_state import GameState


class Target:
    def __init__(self, x, y, radius, color, points=100):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.points = points
        self.alive = True

    def contains_point(self, px, py):
        dx = px - self.x
        dy = py - self.y
        return (dx*dx + dy*dy) <= self.radius * self.radius

    def render(self, screen):
        if self.alive:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)


class TargetPractice(BaseGame):
    NAME = "Target Practice"
    DESCRIPTION = "Hit targets as they appear!"
    VERSION = "1.0.0"
    AUTHOR = "AMS Team"

    ARGUMENTS = [
        {'name': '--pacing', 'type': str, 'default': 'throwing',
         'choices': ['archery', 'throwing', 'blaster'],
         'help': 'Game speed preset'},
        {'name': '--target-count', 'type': int, 'default': 10,
         'help': 'Targets to hit to win'},
        {'name': '--miss-limit', 'type': int, 'default': 5,
         'help': 'Misses allowed before game over'},
    ]

    PACING_INTERVALS = {
        'archery': 4.0,
        'throwing': 2.0,
        'blaster': 0.5,
    }

    def __init__(
        self,
        pacing='throwing',
        target_count=10,
        miss_limit=5,
        **kwargs
    ):
        super().__init__(**kwargs)

        self._spawn_interval = self.PACING_INTERVALS.get(pacing, 2.0)
        self._target_count = target_count
        self._miss_limit = miss_limit

        self._targets: List[Target] = []
        self._score = 0
        self._hits = 0
        self._misses = 0
        self._spawn_timer = 0.0
        self._game_over = False
        self._won = False

        # Screen size (set by registry before instantiation)
        from games.TargetPractice.config import SCREEN_WIDTH, SCREEN_HEIGHT
        self._width = SCREEN_WIDTH
        self._height = SCREEN_HEIGHT

    def _get_internal_state(self) -> GameState:
        if self._won:
            return GameState.WON
        if self._game_over:
            return GameState.GAME_OVER
        return GameState.PLAYING

    def get_score(self) -> int:
        return self._score

    def handle_input(self, events):
        if self._get_internal_state() != GameState.PLAYING:
            return

        for event in events:
            if self._quiver and self._quiver.is_empty:
                continue

            hit = False
            for target in self._targets:
                if target.alive and target.contains_point(event.position.x, event.position.y):
                    target.alive = False
                    self._score += target.points
                    self._hits += 1
                    hit = True
                    break

            if not hit:
                self._misses += 1

            if self._use_shot():
                self._start_retrieval()

        # Check win/lose
        if self._hits >= self._target_count:
            self._won = True
        elif self._misses >= self._miss_limit:
            self._game_over = True

    def update(self, dt: float):
        if self._in_retrieval:
            if self._update_retrieval(dt):
                self._end_retrieval()
            return

        if self._get_internal_state() != GameState.PLAYING:
            return

        # Remove dead targets
        self._targets = [t for t in self._targets if t.alive]

        # Spawn new targets
        self._spawn_timer -= dt
        if self._spawn_timer <= 0 and len(self._targets) < 3:
            self._spawn_target()
            self._spawn_timer = self._spawn_interval

    def _spawn_target(self):
        margin = 100
        x = random.randint(margin, self._width - margin)
        y = random.randint(margin, self._height - margin)
        radius = random.randint(30, 60)
        color = self._palette.random_target_color()
        self._targets.append(Target(x, y, radius, color))

    def render(self, screen):
        screen.fill(self._palette.get_background_color())

        for target in self._targets:
            target.render(screen)

        # UI
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Score: {self._score}", True, self._palette.get_ui_color())
        screen.blit(score_text, (10, 10))

        progress = font.render(f"Hits: {self._hits}/{self._target_count}", True, (100, 255, 100))
        screen.blit(progress, (10, 50))

        misses = font.render(f"Misses: {self._misses}/{self._miss_limit}", True, (255, 100, 100))
        screen.blit(misses, (10, 90))

        if self._quiver:
            quiver_text = font.render(self._quiver.get_display_text(), True, (255, 255, 255))
            screen.blit(quiver_text, (10, 130))

        # Overlays
        if self.state == GameState.RETRIEVAL:
            self._render_overlay(screen, "RETRIEVAL", (255, 200, 0))
        elif self._won:
            self._render_overlay(screen, "YOU WIN!", (0, 255, 0))
        elif self._game_over:
            self._render_overlay(screen, "GAME OVER", (255, 0, 0))

    def _render_overlay(self, screen, text, color):
        overlay = pygame.Surface((self._width, self._height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        screen.blit(overlay, (0, 0))

        font = pygame.font.Font(None, 72)
        text_surf = font.render(text, True, color)
        rect = text_surf.get_rect(center=(self._width // 2, self._height // 2))
        screen.blit(text_surf, rect)
```

## Skins System (Visual Themes)

Games can implement multiple visual representations through a skins system. This is useful for:
- **CV-friendly modes**: Simple geometric shapes for reliable detection
- **Classic visuals**: Sprite-based rendering with animations
- **Accessibility**: High-contrast or simplified visuals
- **Theming**: Holiday themes, custom branding, etc.

### Implementing Skins

**1. Create Skin Base Class:**

```python
# games/MyGame/game/skins/base.py
from abc import ABC, abstractmethod
import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..target import Target

class GameSkin(ABC):
    """Base class for game skins (visuals + audio)."""

    NAME: str = "base"
    DESCRIPTION: str = "Base skin"

    @abstractmethod
    def render_target(self, target: 'Target', screen: pygame.Surface) -> None:
        """Render a target to the screen."""
        pass

    def update(self, dt: float) -> None:
        """Update skin state (animations, etc.)."""
        pass

    def play_hit_sound(self) -> None:
        """Play sound when target is hit."""
        pass

    def play_miss_sound(self) -> None:
        """Play sound when shot misses."""
        pass
```

**2. Create Concrete Skins:**

```python
# games/MyGame/game/skins/geometric.py
class GeometricSkin(GameSkin):
    """Simple circles for CV testing."""

    NAME = "geometric"
    DESCRIPTION = "Simple shapes for testing and CV calibration"

    def render_target(self, target, screen):
        pos = (int(target.x), int(target.y))
        pygame.draw.circle(screen, (255, 100, 100), pos, target.radius)
        pygame.draw.circle(screen, (255, 255, 255), pos, target.radius, 2)

# games/MyGame/game/skins/classic.py
class ClassicSkin(GameSkin):
    """Sprite-based rendering with sounds."""

    NAME = "classic"
    DESCRIPTION = "Original style with sprites and sounds"

    def __init__(self):
        self._sprites = None
        self._hit_sound = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy loading of assets."""
        if self._initialized:
            return
        self._sprites = load_sprites()
        self._hit_sound = pygame.mixer.Sound("assets/hit.ogg")
        self._initialized = True

    def render_target(self, target, screen):
        self._ensure_initialized()
        frame = self._sprites.get_frame(target.state)
        screen.blit(frame, (target.x, target.y))

    def play_hit_sound(self):
        self._ensure_initialized()
        if self._hit_sound:
            self._hit_sound.play()
```

**3. Wire Up in Game Mode:**

```python
class MyGameMode(BaseGame):
    ARGUMENTS = [
        {'name': '--skin', 'type': str, 'default': 'classic',
         'choices': ['geometric', 'classic'], 'help': 'Visual skin'},
        # ... other arguments
    ]

    SKINS = {}  # Populated in __init__

    def __init__(self, skin: str = 'classic', **kwargs):
        super().__init__(**kwargs)

        from .game.skins import GeometricSkin, ClassicSkin
        self.SKINS = {
            'geometric': GeometricSkin,
            'classic': ClassicSkin,
        }
        self._skin = self.SKINS.get(skin, ClassicSkin)()

    def handle_input(self, events):
        for event in events:
            if self._check_hit(event.position):
                self._skin.play_hit_sound()
            else:
                self._skin.play_miss_sound()

    def update(self, dt):
        self._skin.update(dt)  # Update animations
        # ... rest of update

    def render(self, screen):
        screen.fill(self._palette.get_background_color())
        for target in self._targets:
            self._skin.render_target(target, screen)
```

### Skin Design Principles

1. **Presentation only**: Skins should not change game logic, only visuals and audio
2. **Lazy initialization**: Load assets only when needed (first render/sound)
3. **Fallback support**: Provide fallback rendering if assets fail to load
4. **Registry-based**: Games declare available skins in SKINS dict

### Example: DuckHunt Skins

DuckHunt implements two skins:

```bash
# CV-friendly geometric circles
python ams_game.py --game duckhunt --backend mouse --skin geometric

# Classic sprite-based ducks with sounds
python ams_game.py --game duckhunt --backend mouse --skin classic
```

## Level System

Games can opt-in to YAML-based level support by setting `LEVELS_DIR` and implementing level-specific methods.

### Enabling Level Support

```python
from pathlib import Path
from games.common.base_game import BaseGame
from games.common.levels import LevelLoader

class MyGame(BaseGame):
    NAME = "My Game"
    LEVELS_DIR = Path(__file__).parent / 'levels'  # Enable level support

    def _create_level_loader(self) -> LevelLoader:
        """Return a game-specific level loader."""
        return MyLevelLoader(self.LEVELS_DIR)

    def _apply_level_config(self, level_data) -> None:
        """Apply level configuration to game state."""
        self._enemies = level_data.enemies
        self._spawn_rate = level_data.spawn_rate
        # ... game-specific setup
```

When `LEVELS_DIR` is set, these CLI arguments are automatically added:

- `--level <slug>` - Load a specific level
- `--list-levels` - Print available levels and exit
- `--level-group <slug>` - Play through a level group (campaign)
- `--choose-level` - Show level chooser UI before starting

### Level File Format (YAML)

```yaml
# levels/tutorial_01.yaml
name: "Tutorial 1"
description: "Learn the basics"
difficulty: 1
author: "AMS Team"
version: 1

# Game-specific configuration below
enemies:
  - type: basic
    count: 3
spawn_rate: 2.0
```

### Level Groups (Campaigns)

Level groups define sequences of levels for campaigns, tutorials, or challenges:

```yaml
# levels/campaign.yaml
group: true  # Marks this as a group, not a level
name: "Main Campaign"
description: "The story mode"
author: "AMS Team"

levels:
  - tutorial_01
  - tutorial_02
  - level_01
  - level_02
  - boss_01
```

### Creating a Custom Level Loader

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
from games.common.levels import LevelLoader

@dataclass
class MyLevelData:
    """Game-specific level configuration."""
    name: str
    enemies: list
    spawn_rate: float
    time_limit: int

class MyLevelLoader(LevelLoader[MyLevelData]):
    """Level loader for MyGame."""

    def _parse_level_data(self, data: Dict[str, Any], file_path: Path) -> MyLevelData:
        return MyLevelData(
            name=data.get('name', 'Untitled'),
            enemies=data.get('enemies', []),
            spawn_rate=data.get('spawn_rate', 1.0),
            time_limit=data.get('time_limit', 60),
        )
```

### Level Progression (Groups)

When a player completes a level, call `_level_complete()` to handle progression:

```python
def update(self, dt: float):
    # Check if level is complete
    if self._player_won_level:
        # Let BaseGame handle progression
        if not self._level_complete():
            # No more levels - game complete
            self._game_won = True
```

**`_level_complete() -> bool`**

Called when player beats a level. This method:

1. Checks if there's a next level in the group
2. If yes, loads it and calls `_on_level_transition()`
3. Returns `False` if no more levels (game should show victory)

Future: Will also handle pause for target clearance and quick recalibration.

**`_on_level_transition() -> None`**

Override this to reinitialize your game state when transitioning to a new level:

```python
def _on_level_transition(self) -> None:
    """Reinitialize game state for new level."""
    self._clear_entities()
    self._setup_level()  # Uses self._current_level_data
    self._reset_timers()
```

The new level data is already loaded via `_apply_level_config()` before this is called.

### Level Properties

```python
# Current level info
self.current_level_slug   # e.g., "tutorial_01"
self.current_level_name   # e.g., "Tutorial 1"
self._current_level_data  # The loaded level data object

# Group info (if playing a group)
self.current_group              # LevelGroup object or None
self.current_group.progress     # 0.0 to 1.0
self.current_group.current_level
self.current_group.is_complete

# Check if game has levels
self.has_levels           # True if LEVELS_DIR is set and valid
self.show_level_chooser   # True if --choose-level was passed
```

### Level Chooser UI

A generic level chooser UI is provided for games with level support:

```python
from games.common.level_chooser import LevelChooserUI

# In your game:
if self.show_level_chooser:
    if self._chooser_ui is None:
        self._chooser_ui = LevelChooserUI(
            level_loader=self._level_loader,
            screen_width=screen.get_width(),
            screen_height=screen.get_height(),
            game_name=self.NAME,
            on_level_selected=self._on_level_selected,
            on_group_selected=self._on_group_selected,
            on_back=lambda: setattr(self, 'show_level_chooser', False),
        )
    self._chooser_ui.render(screen)
    return  # Skip normal rendering
```

## Integration Points

### With Game Registry

```python
from games.registry import get_registry

registry = get_registry()
games = registry.list_games()  # ['balloonpop', 'targetpractice', ...]
info = registry.get_game_info('targetpractice')
args = registry.get_game_arguments('targetpractice')

# Create instance
game = registry.create_game('targetpractice', width=1920, height=1080, pacing='archery')
```

### With Web Controller

The web controller uses `get_arguments()` to dynamically generate configuration forms. Arguments are serialized to JSON with type names converted to strings.

### With dev_game.py / ams_game.py

These launchers use argparse with the game's `ARGUMENTS` to create CLI interfaces:

```bash
python ams_game.py --game targetpractice --pacing archery --target-count 20
```
