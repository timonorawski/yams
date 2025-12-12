# Quick Start Guide - Creating Games for AMS

Welcome! This guide will help you create your first game for the AMS (Arcade Management System) platform. You'll learn how to build games that work with any projectile-based activity - archery, nerf blasters, laser pointers, and more.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Win: Run an Existing Game](#quick-win-run-an-existing-game)
3. [Choose Your Path](#choose-your-path)
4. [Path A: YAML Games (Recommended for Beginners)](#path-a-yaml-games-recommended-for-beginners)
5. [Path B: Python Games (For Complex Games)](#path-b-python-games-for-complex-games)
6. [Testing Your Game](#testing-your-game)
7. [Next Steps](#next-steps)

---

## Prerequisites

### Hardware (Optional)
For development, you only need a computer with a mouse. The full AMS setup (projector + camera) is only needed for production use.

### Software
- **Python 3.10 or higher** - Check with: `python3 --version`
- **pip** - Python package manager

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/yams.git
   cd yams
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   This installs:
   - `pygame` - Display and rendering
   - `opencv-contrib-python` - Computer vision for detection
   - `numpy` - Numerical operations
   - `pydantic` - Data validation
   - `pymunk` - 2D physics engine
   - `lupa` - Lua scripting support
   - `fastapi` + `uvicorn` - Web controller API

3. **Verify installation:**
   ```bash
   python3 -c "import pygame; print('Pygame version:', pygame.__version__)"
   python3 -c "import cv2; print('OpenCV version:', cv2.__version__)"
   ```

---

## Quick Win: Run an Existing Game

Before creating your own game, let's run one to see how everything works.

### Running with Mouse (No Hardware Setup Needed)

```bash
# Simple fruit slicing game
python3 ams_game.py --game fruitsliceng --backend mouse

# Grouping precision trainer
python3 ams_game.py --game groupingng --backend mouse

# Balloon popping game
python3 ams_game.py --game balloonpop --backend mouse
```

**Controls:**
- Click with your mouse to "shoot"
- ESC to quit

### List All Available Games

```bash
python3 ams_game.py --list-games
```

### Running with AMS (Projector + Camera Setup)

```bash
# With laser pointer
python3 ams_game.py --game fruitsliceng --backend laser --fullscreen --display 1

# With nerf darts (object detection)
python3 ams_game.py --game fruitsliceng --backend object --mode classic_archery
```

See [AMS_README.md](AMS_README.md) for full setup instructions.

---

## Choose Your Path

AMS supports two ways to create games:

| Approach | Best For | Complexity | Time to First Game |
|----------|----------|------------|--------------------|
| **YAML Games** | Simple games, quick prototypes, learning | Low | 10-15 minutes |
| **Python Games** | Complex logic, custom physics, advanced features | Medium-High | 30-60 minutes |

**Recommendation:** Start with YAML games to learn the system, then move to Python for more complex projects.

---

## Path A: YAML Games (Recommended for Beginners)

YAML games let you create fully functional games using only configuration files - no Python code required!

### Step 1: Create Game Directory

```bash
mkdir games/MyFirstGame
cd games/MyFirstGame
```

### Step 2: Create game.yaml

Create `games/MyFirstGame/game.yaml` with this complete working example:

```yaml
# yaml-language-server: $schema=../../schemas/game.schema.json

# =============================================================================
# Game Metadata
# =============================================================================

name: "My First Game"
description: "A simple target practice game"
version: "1.0.0"
author: "Your Name"

# =============================================================================
# Display Settings
# =============================================================================

screen_width: 800
screen_height: 600
background_color: [20, 20, 40]  # Dark blue-gray [R, G, B]

# =============================================================================
# Game Rules
# =============================================================================

defaults:
  lives: 3  # Player starts with 3 lives

win_condition: reach_score  # Win when reaching target score
win_target: 100             # Need 100 points to win

# =============================================================================
# Entity Types - Define Game Objects
# =============================================================================

entity_types:

  # Target - a simple clickable circle
  target:
    width: 60
    height: 60
    color: red
    points: 10                           # Points awarded when hit
    behaviors: [destroy_offscreen]       # Auto-destroy when leaving screen
    behavior_config:
      destroy_offscreen:
        edges: all                       # Destroy on any edge
        margin: 50                       # 50px past screen edge
    tags: [target]                       # Tag for easy identification
    render:
      - shape: circle                    # Draw as circle
        color: $color                    # Use entity's color
        radius: 0.5                      # 0.5 = half width (full circle)

  # Spawner - invisible entity that creates targets
  spawner:
    width: 1
    height: 1
    behaviors:
      - lua: |
          -- Spawner behavior in Lua
          local spawner = {}

          function spawner.on_spawn(entity_id)
              -- Initialize spawn timer
              ams.set_prop(entity_id, "timer", 0)
          end

          function spawner.on_update(entity_id, dt)
              -- Get current timer
              local timer = ams.get_prop(entity_id, "timer") or 0
              timer = timer + dt  -- dt = delta time in seconds

              -- Spawn a target every 2 seconds
              if timer >= 2.0 then
                  ams.set_prop(entity_id, "timer", 0)  -- Reset timer

                  -- Random position at top of screen
                  local screen_w = ams.get_screen_width()
                  local x = ams.random_range(50, screen_w - 50)
                  local y = -30  -- Start above screen

                  -- Spawn target moving downward
                  ams.spawn("target", x, y, 0, 100, 0, 0, "", "")
                  --        type      x  y  vx  vy  w  h  color sprite
              else
                  ams.set_prop(entity_id, "timer", timer)
              end
          end

          return spawner
    render: []  # Invisible - no rendering

# =============================================================================
# Input Mapping - What Happens When Things Are Clicked
# =============================================================================

input_mapping:
  target:
    on_hit:
      transform:
        type: destroy  # Destroy target when clicked

# =============================================================================
# Player Configuration
# =============================================================================

player:
  type: spawner     # Player entity is the spawner
  spawn: [0, 0]     # Position (doesn't matter for spawner)
```

### Step 3: Run Your Game!

```bash
cd ../..  # Back to yams root directory
python3 ams_game.py --game myfirstgame --backend mouse
```

That's it! You now have a working game where:
- Targets spawn every 2 seconds at random positions
- They fall downward at 100 pixels/second
- Click them to score 10 points
- Reach 100 points to win
- Miss targets (let them go off-screen) and you're fine - they just disappear

### Step 4: Customize Your Game

Let's make it more interesting! Edit your `game.yaml`:

#### Add More Target Types

```yaml
entity_types:
  # Keep existing target...

  # Add a fast target worth more points
  target_fast:
    extends: target        # Inherit from base target
    color: yellow
    points: 25
    behaviors: [destroy_offscreen]
    behavior_config:
      destroy_offscreen:
        edges: all
        margin: 50
    tags: [target]
    render:
      - shape: circle
        color: yellow
        radius: 0.5

  # Add a bomb - avoid clicking!
  bomb:
    width: 50
    height: 50
    color: [40, 40, 40]    # Dark gray
    behaviors: [destroy_offscreen]
    behavior_config:
      destroy_offscreen:
        edges: all
        margin: 50
    tags: [bomb, hazard]
    render:
      - shape: circle
        color: [40, 40, 40]
        radius: 0.5
      - shape: circle        # Inner red warning
        color: [200, 0, 0]
        radius: 0.3
```

#### Update Spawner to Use Multiple Types

Replace the spawner's Lua code with:

```lua
local spawner = {}

function spawner.on_spawn(entity_id)
    ams.set_prop(entity_id, "timer", 0)
end

function spawner.on_update(entity_id, dt)
    local timer = ams.get_prop(entity_id, "timer") or 0
    timer = timer + dt

    if timer >= 1.5 then  -- Spawn faster
        ams.set_prop(entity_id, "timer", 0)

        local screen_w = ams.get_screen_width()
        local x = ams.random_range(50, screen_w - 50)
        local y = -30

        -- Random entity type (70% regular, 20% fast, 10% bomb)
        local rand = ams.random()
        local entity_type
        local vy

        if rand < 0.7 then
            entity_type = "target"
            vy = 100
        elseif rand < 0.9 then
            entity_type = "target_fast"
            vy = 180  -- Fast target moves faster
        else
            entity_type = "bomb"
            vy = 80   -- Bombs move slower
        end

        ams.spawn(entity_type, x, y, 0, vy, 0, 0, "", "")
    else
        ams.set_prop(entity_id, "timer", timer)
    end
end

return spawner
```

#### Add Input Mapping for New Types

```yaml
input_mapping:
  target:
    on_hit:
      transform:
        type: destroy

  target_fast:
    on_hit:
      transform:
        type: destroy

  bomb:
    on_hit:
      transform:
        type: destroy

# Add lose condition - clicking bombs costs a life
lose_conditions:
  - entity_type: bomb
    event: destroyed
    action: lose_life
```

Run again to see your enhanced game!

### Understanding YAML Game Concepts

#### Entity Types
Define templates for game objects. Each can have:
- **Physical properties:** `width`, `height`, `color`
- **Game properties:** `points` (score when destroyed)
- **Behaviors:** Pre-built actions (see below)
- **Tags:** Categories for grouping (`target`, `hazard`, etc.)
- **Render:** How to draw it (shapes, sprites, text)

#### Built-in Behaviors

| Behavior | Description | Config Example |
|----------|-------------|----------------|
| `gravity` | Apply gravity + velocity | `acceleration: 600` |
| `destroy_offscreen` | Destroy when leaving screen | `edges: all`, `margin: 50` |
| `bounce` | Bounce off screen edges | `walls: all`, `min_y: 0` |
| `animate` | Cycle through sprite frames | `frames: 3`, `fps: 8` |
| `fade_out` | Fade and destroy | `duration: 0.5` |

#### Inline Lua Behaviors

For custom logic, write Lua code directly in the YAML:

```yaml
behaviors:
  - lua: |
      local behavior = {}
      function behavior.on_spawn(id)
          -- Initialize entity
      end
      function behavior.on_update(id, dt)
          -- Update each frame (dt = delta time)
      end
      return behavior
```

#### Essential Lua API Functions

**Entity Properties:**
```lua
ams.get_x(id), ams.set_x(id, value)
ams.get_y(id), ams.set_y(id, value)
ams.get_vx(id), ams.set_vx(id, value)  -- velocity x
ams.get_vy(id), ams.set_vy(id, value)  -- velocity y
ams.get_width(id), ams.get_height(id)
ams.get_type(id)  -- Returns entity type name
```

**Custom Properties:**
```lua
ams.get_prop(id, "key")
ams.set_prop(id, "key", value)
```

**Screen Info:**
```lua
ams.get_screen_width()
ams.get_screen_height()
```

**Entity Management:**
```lua
ams.spawn(type, x, y, vx, vy, width, height, color, sprite)
ams.destroy(id)
ams.get_entities_of_type("type_name")
ams.count_entities_by_tag("tag")
```

**Game State:**
```lua
ams.add_score(points)
ams.get_time()  -- Game time in seconds
```

**Utilities:**
```lua
ams.random()  -- Returns 0.0 to 1.0
ams.random_range(min, max)
ams.play_sound("sound_name")
```

#### Rendering

Multiple render commands create layered visuals:

```yaml
render:
  # Circle
  - shape: circle
    color: red
    radius: 0.5      # Relative to entity size (0.5 = half width)
    fill: true       # Optional, default true

  # Rectangle
  - shape: rect
    color: blue
    offset: [10, 10] # Optional offset from entity position
    size: [20, 30]   # Optional custom size

  # Text
  - shape: text
    text: "{score} pts"  # Can use properties with {}
    color: white
    font_size: 24
```

### More YAML Examples

For more advanced YAML game examples, check out:
- **`games/FruitSliceNG/game.yaml`** - Arcing projectiles, combos, bombs
- **`games/GroupingNG/game.yaml`** - Complex global input handler, state management
- **`games/SweetPhysicsNG/game.yaml`** - Physics-based rope constraints

Full reference: [YAML_GAME_QUICKSTART.md](YAML_GAME_QUICKSTART.md)

---

## Path B: Python Games (For Complex Games)

For games requiring custom physics, complex AI, or advanced features, create a Python game.

### When to Use Python

- Complex game logic (state machines, AI)
- Custom physics (beyond built-in pymunk)
- Advanced rendering (particle effects, shaders)
- Integration with external libraries
- Performance-critical code

### Step 1: Create Game Directory Structure

```bash
mkdir -p games/MyPythonGame/input/sources
```

### Step 2: Set Up Input Abstraction

Python games use a common input system that works standalone or with AMS.

**games/MyPythonGame/input/__init__.py:**
```python
"""MyPythonGame Input Module - Re-exports from common input module."""
from games.common.input import InputEvent, InputManager
from games.common.input.sources import InputSource, MouseInputSource

__all__ = ['InputEvent', 'InputManager', 'InputSource', 'MouseInputSource']
```

**games/MyPythonGame/input/input_manager.py:**
```python
"""MyPythonGame Input Manager - Re-export from common module."""
from games.common.input.input_manager import InputManager

__all__ = ['InputManager']
```

**games/MyPythonGame/input/input_event.py:**
```python
"""MyPythonGame Input Event - Re-export from common module."""
from games.common.input.input_event import InputEvent

__all__ = ['InputEvent']
```

**games/MyPythonGame/input/sources/__init__.py:**
```python
"""MyPythonGame Input Sources - Re-export from common module."""
from games.common.input.sources import InputSource, MouseInputSource

__all__ = ['InputSource', 'MouseInputSource']
```

**games/MyPythonGame/input/sources/mouse.py:**
```python
"""MyPythonGame Mouse Input Source - Re-export from common module."""
from games.common.input.sources.mouse import MouseInputSource

__all__ = ['MouseInputSource']
```

### Step 3: Create game_mode.py

This is your main game class:

```python
"""MyPythonGame - A Python-based game example."""
from typing import List
import pygame

from games.common import BaseGame, GameState


class MyPythonGameMode(BaseGame):
    """A simple Python game demonstrating the BaseGame interface.

    Inherits from BaseGame which provides:
    - Automatic state management (state property)
    - Palette support for CV-compatible colors
    - Quiver/ammo support for archery games
    - Base CLI arguments (--palette, --quiver-size, etc.)
    """

    # =========================================================================
    # Game Metadata (for registry auto-discovery)
    # =========================================================================

    NAME = "My Python Game"
    DESCRIPTION = "A simple target practice game in Python"
    VERSION = "1.0.0"
    AUTHOR = "Your Name"

    # Game-specific CLI arguments
    ARGUMENTS = [
        {
            'name': '--difficulty',
            'type': str,
            'default': 'normal',
            'choices': ['easy', 'normal', 'hard'],
            'help': 'Game difficulty level'
        },
        {
            'name': '--target-count',
            'type': int,
            'default': 3,
            'help': 'Number of targets on screen'
        },
    ]

    # =========================================================================
    # Initialization
    # =========================================================================

    def __init__(
        self,
        difficulty: str = 'normal',
        target_count: int = 3,
        **kwargs,  # Captures palette, quiver args for BaseGame
    ):
        # IMPORTANT: Call super().__init__ to set up palette and quiver
        super().__init__(**kwargs)

        # Game-specific initialization
        self._difficulty = difficulty
        self._target_count = target_count
        self._score = 0
        self._targets = []
        self._game_over = False

        # Create initial targets
        self._spawn_targets()

    # =========================================================================
    # Required: Internal State
    # =========================================================================

    def _get_internal_state(self) -> GameState:
        """Map internal state to standard GameState.

        BaseGame.state property calls this and handles RETRIEVAL automatically.
        """
        if self._game_over:
            return GameState.GAME_OVER
        if self._score >= 100:
            return GameState.WON
        return GameState.PLAYING

    # =========================================================================
    # Required: Game Interface
    # =========================================================================

    def get_score(self) -> int:
        """Return current score."""
        return self._score

    def handle_input(self, events: List) -> None:
        """Process input events (clicks/hits)."""
        for event in events:
            x, y = event.position.x, event.position.y

            # Check if clicked on any target
            for target in self._targets[:]:  # Copy list for safe removal
                if self._check_hit(target, x, y):
                    self._score += 10
                    self._targets.remove(target)
                    # Spawn new target to maintain count
                    self._spawn_targets()
                    break

    def update(self, dt: float) -> None:
        """Update game logic. dt is seconds since last frame."""
        # Move targets
        for target in self._targets:
            target['y'] += target['vy'] * dt

            # Wrap around screen
            if target['y'] > 600:
                target['y'] = -50

    def render(self, screen: pygame.Surface) -> None:
        """Draw game to screen."""
        # Use palette for CV-compatible colors
        bg_color = self._palette.get_background_color()
        screen.fill(bg_color)

        # Draw targets
        for i, target in enumerate(self._targets):
            color = self._palette.get_target_color(i % 4)  # Cycle through 4 colors
            pygame.draw.circle(
                screen,
                color,
                (int(target['x']), int(target['y'])),
                30
            )

        # Draw score (UI color)
        ui_color = self._palette.get_ui_color()
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Score: {self._score}", True, ui_color)
        screen.blit(score_text, (10, 10))

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _spawn_targets(self):
        """Ensure we have the right number of targets."""
        import random

        while len(self._targets) < self._target_count:
            self._targets.append({
                'x': random.randint(50, 750),
                'y': random.randint(50, 550),
                'vy': random.randint(30, 80)  # Downward speed
            })

    def _check_hit(self, target, x, y):
        """Check if click hit the target."""
        dx = x - target['x']
        dy = y - target['y']
        distance = (dx * dx + dy * dy) ** 0.5
        return distance <= 30  # Target radius
```

### Step 4: Create game_info.py

Factory function to create your game:

```python
"""MyPythonGame - Game Info"""


def get_game_mode(**kwargs):
    """Factory function to create game instance.

    The registry calls this with CLI arguments.
    """
    from games.MyPythonGame.game_mode import MyPythonGameMode
    return MyPythonGameMode(**kwargs)
```

### Step 5: Create Supporting Files

**games/MyPythonGame/__init__.py:**
```python
"""MyPythonGame package."""
```

**games/MyPythonGame/config.py:**
```python
"""Configuration for MyPythonGame."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from game directory
_env_path = Path(__file__).parent / '.env'
load_dotenv(_env_path)

def _get_int(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))

# Display settings
SCREEN_WIDTH = _get_int('SCREEN_WIDTH', 800)
SCREEN_HEIGHT = _get_int('SCREEN_HEIGHT', 600)
```

**games/MyPythonGame/.env:**
```env
# MyPythonGame Configuration
SCREEN_WIDTH=800
SCREEN_HEIGHT=600
```

### Step 6: Run Your Python Game

```bash
# Development mode (recommended)
python3 dev_game.py mypythongame

# With AMS
python3 ams_game.py --game mypythongame --backend mouse

# List available options
python3 dev_game.py mypythongame --help
```

### BaseGame Features

**Automatic Palette Support:**
```python
# In render():
bg = self._palette.get_background_color()       # Background
color = self._palette.get_target_color(index)   # Target colors (0-3)
ui = self._palette.get_ui_color()               # UI text

# Cycle palettes for testing:
self.cycle_palette()  # Returns new palette name
self.set_palette('bw')  # Set specific palette
```

**Quiver/Ammo Support:**
```python
# In handle_input():
if self._use_shot():  # Returns True when empty
    self._start_retrieval()

# In update():
if self._in_retrieval:
    if self._update_retrieval(dt):  # Returns True when done
        self._end_retrieval()

# Display:
remaining = self.shots_remaining  # None if unlimited
```

**Automatic CLI Arguments:**
- `--palette <name>` - Test palette (bw, high_contrast, etc.)
- `--quiver-size <n>` - Shots before retrieval
- `--retrieval-pause <s>` - Seconds for retrieval

### For More Complex Python Games

See these examples:
- **`games/BalloonPop/`** - Simple BaseGame example
- **`games/Containment/`** - Physics, geometry, level support
- **`games/DuckHunt/`** - Multiple modes, skins system, complex state

Full reference: [NEW_GAME_QUICKSTART.md](NEW_GAME_QUICKSTART.md)

---

## Testing Your Game

### Basic Testing

```bash
# Test with mouse
python3 ams_game.py --game yourgame --backend mouse

# Test fullscreen (press F to toggle)
python3 ams_game.py --game yourgame --backend mouse --fullscreen

# Test on specific display
python3 ams_game.py --game yourgame --backend mouse --display 1
```

### Test Different Input Speeds

Games should work with different projectile speeds:

```bash
# Slow (archery) - 3-8 second cycle time
python3 ams_game.py --game yourgame --backend mouse --pacing archery

# Medium (throwing) - 1-2 second cycle time
python3 ams_game.py --game yourgame --backend mouse --pacing throwing

# Fast (blaster) - 0.3 second cycle time
python3 ams_game.py --game yourgame --backend mouse --pacing blaster
```

### Test Palettes (CV Compatibility)

```bash
# Black & white (high contrast)
python3 ams_game.py --game yourgame --backend mouse --palette bw

# High contrast colors
python3 ams_game.py --game yourgame --backend mouse --palette high_contrast

# Projector-optimized
python3 ams_game.py --game yourgame --backend mouse --palette projector
```

### Verify Game Discovery

```bash
# List all games - yours should appear
python3 ams_game.py --list-games

# Check your game's options
python3 dev_game.py yourgame --help
```

### Common Issues

**Game not discovered:**
- For YAML: Ensure `game.yaml` exists in `games/YourGame/`
- For Python: Ensure `game_mode.py` has class inheriting from `BaseGame`
- Check for syntax errors: `python3 -c "from games.YourGame.game_mode import *"`

**Targets not appearing:**
- Check spawn positions are within screen bounds
- Verify entity types are defined correctly
- Add debug prints in Lua: `print("spawning at", x, y)`

**Input not working:**
- Ensure `input_mapping` matches entity type names
- Check collision detection logic (for Python games)
- Verify event handling in `handle_input()`

**Performance issues:**
- Limit entities on screen (use `count_entities_by_tag()`)
- Optimize rendering (avoid unnecessary draws)
- Profile with `cProfile` for Python games

---

## Next Steps

### Learn More

**YAML Games:**
- [YAML Game Quickstart](YAML_GAME_QUICKSTART.md) - Complete YAML reference
- [Lua Scripting Guide](lua_scripting.md) - Advanced Lua techniques

**Python Games:**
- [New Game Quickstart](NEW_GAME_QUICKSTART.md) - Complete Python reference
- [AMS Developer Guide](AMS_DEVELOPER_GUIDE.md) - Integration details

**AMS Setup:**
- [Getting Started](GETTING_STARTED.md) - Calibration system setup
- [AMS README](AMS_README.md) - Full AMS documentation
- [Laser Tuning Guide](LASER_TUNING_GUIDE.md) - Laser pointer detection
- [Object Detection Guide](OBJECT_DETECTION_GUIDE.md) - Nerf/dart detection

### Add Features to Your Game

**Levels and Progression:**
```yaml
# levels/tutorial.yaml
name: "Tutorial"
difficulty: 1
# ... level-specific config
```
See games with level support: `Containment`, `SweetPhysics`

**Sprites and Graphics:**
```yaml
assets:
  sprites:
    _sheet:
      file: sprites.png
      transparent: [159, 227, 163]
    my_sprite: { sprite: _sheet, x: 0, y: 0, width: 32, height: 32 }
```

**Sound Effects:**
```yaml
assets:
  sounds:
    hit: sounds/hit.wav
    miss: sounds/miss.wav
```

**Physics:**
- For YAML: Use `gravity`, `bounce` behaviors
- For Python: Use pymunk for complex physics (see `SweetPhysics`)

### Share Your Game

1. Test thoroughly with different backends
2. Add a README to your game directory
3. Document any special requirements
4. Share on the community forum!

### Get Help

- Check [CLAUDE.md](../../CLAUDE.md) for project architecture
- Look at similar games in `/games/` for examples
- Open an issue on GitHub with:
  - Game description
  - What you've tried
  - Error messages
  - Relevant code snippets

---

## Example: Complete YAML Game (Copy-Paste Ready)

Here's a complete working game you can copy, modify, and learn from:

**games/SimpleShooter/game.yaml:**

```yaml
# yaml-language-server: $schema=../../schemas/game.schema.json

name: "Simple Shooter"
description: "Click falling targets before they reach the bottom"
version: "1.0.0"
author: "AMS Team"

screen_width: 800
screen_height: 600
background_color: [15, 15, 30]

defaults:
  lives: 5

win_condition: reach_score
win_target: 50

entity_types:
  # Falling target
  target:
    width: 50
    height: 50
    color: [255, 100, 100]
    points: 5
    behaviors: [destroy_offscreen]
    behavior_config:
      destroy_offscreen:
        edges: bottom
        margin: 10
    tags: [target]
    render:
      - shape: circle
        color: [255, 100, 100]
        radius: 0.5

  # Spawner
  spawner:
    width: 1
    height: 1
    behaviors:
      - lua: |
          local s = {}
          function s.on_spawn(id)
              ams.set_prop(id, "timer", 0)
          end
          function s.on_update(id, dt)
              local t = ams.get_prop(id, "timer") + dt
              if t >= 1.0 then
                  ams.set_prop(id, "timer", 0)
                  local w = ams.get_screen_width()
                  local x = ams.random_range(50, w - 50)
                  ams.spawn("target", x, -25, 0, 80, 0, 0, "", "")
              else
                  ams.set_prop(id, "timer", t)
              end
          end
          return s
    render: []

input_mapping:
  target:
    on_hit:
      transform:
        type: destroy

lose_conditions:
  - entity_type: target
    event: offscreen
    action: lose_life

player:
  type: spawner
  spawn: [0, 0]
```

Run it:
```bash
python3 ams_game.py --game simpleshooter --backend mouse
```

**Congratulations! You're now ready to create amazing games for AMS!**
