# New Game Quickstart Guide

This guide walks you through creating a new game for the AMS platform. Games are auto-discovered, so once you follow this structure, your game will automatically appear in `ams_game.py --list-games`.

## Quick Start (5 minutes)

### 1. Create Game Directory

```bash
mkdir -p games/MyGame/input/sources
```

### 2. Set Up Input Abstraction

The platform provides a common input module at `games/common/input/`. Create re-export files to use it:

**games/MyGame/input/__init__.py:**
```python
"""MyGame Input Module - Re-exports from common input module."""
from games.common.input import InputEvent, InputManager
from games.common.input.sources import InputSource, MouseInputSource

__all__ = ['InputEvent', 'InputManager', 'InputSource', 'MouseInputSource']
```

**games/MyGame/input/input_manager.py:**
```python
"""MyGame Input Manager - Re-export from common module."""
from games.common.input.input_manager import InputManager

__all__ = ['InputManager']
```

**games/MyGame/input/input_event.py:**
```python
"""MyGame Input Event - Re-export from common module."""
from games.common.input.input_event import InputEvent

__all__ = ['InputEvent']
```

**games/MyGame/input/sources/__init__.py:**
```python
"""MyGame Input Sources - Re-export from common module."""
from games.common.input.sources import InputSource, MouseInputSource

__all__ = ['InputSource', 'MouseInputSource']
```

**games/MyGame/input/sources/mouse.py:**
```python
"""MyGame Mouse Input Source - Re-export from common module."""
from games.common.input.sources.mouse import MouseInputSource

__all__ = ['MouseInputSource']
```

This approach:
- Uses the shared, validated input code from `games/common/input/`
- Maintains backward compatibility with game-specific imports
- Ensures consistent input handling across all games

### 3. Create Required Files

Your game needs these files:

```
games/MyGame/
├── __init__.py          # Empty or package docstring
├── game_info.py         # Game metadata + factory function (REQUIRED)
├── game_mode.py         # Game logic (REQUIRED)
├── config.py            # Configuration
├── .env                 # Default settings
├── main.py              # Standalone entry point
└── input/               # Copied from step 2
```

### 4. Create game_info.py

This is the key file for auto-discovery:

```python
"""MyGame - Game Info"""

NAME = "My Game"
DESCRIPTION = "A short description of my game."
VERSION = "1.0.0"
AUTHOR = "Your Name"

def get_game_mode(**kwargs):
    """Factory function to create game instance."""
    from games.MyGame.game_mode import MyGameMode
    return MyGameMode(**kwargs)
```

### 5. Create game_mode.py

Your game mode must implement these methods:

```python
from enum import Enum
from typing import List
import pygame

class GameState(Enum):
    PLAYING = "playing"
    GAME_OVER = "game_over"
    WON = "won"  # Optional

class MyGameMode:
    def __init__(self, **kwargs):
        self._state = GameState.PLAYING
        self._score = 0
        # Initialize your game state

    @property
    def state(self) -> GameState:
        return self._state

    def get_score(self) -> int:
        return self._score

    def handle_input(self, events: List) -> None:
        """Process input events (clicks/hits)."""
        for event in events:
            x, y = event.position.x, event.position.y
            # Handle the input at (x, y)

    def update(self, dt: float) -> None:
        """Update game logic. dt is seconds since last frame."""
        pass

    def render(self, screen: pygame.Surface) -> None:
        """Draw game to screen."""
        screen.fill((0, 0, 0))  # Clear screen
        # Draw your game elements
```

### 6. Create config.py

```python
"""Configuration for MyGame."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from game directory
_env_path = Path(__file__).parent / '.env'
load_dotenv(_env_path)


def _get_bool(key: str, default: bool) -> bool:
    """Get boolean from environment."""
    val = os.getenv(key, str(default)).lower()
    return val in ('true', '1', 'yes')


def _get_int(key: str, default: int) -> int:
    """Get integer from environment."""
    return int(os.getenv(key, str(default)))


def _get_float(key: str, default: float) -> float:
    """Get float from environment."""
    return float(os.getenv(key, str(default)))


# Display settings
SCREEN_WIDTH = _get_int('SCREEN_WIDTH', 1280)
SCREEN_HEIGHT = _get_int('SCREEN_HEIGHT', 720)

# Add your game-specific settings here
# Example:
# TARGET_SIZE = _get_int('TARGET_SIZE', 50)
# SPAWN_RATE = _get_float('SPAWN_RATE', 1.5)
# DEBUG_MODE = _get_bool('DEBUG_MODE', False)
```

### 7. Create .env

```env
# MyGame Configuration
SCREEN_WIDTH=1280
SCREEN_HEIGHT=720
# Add your game-specific defaults
```

### 8. Create main.py (Standalone Entry)

```python
#!/usr/bin/env python3
"""MyGame - Standalone entry point."""

import pygame
import sys
import os

# Add project root to path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _root not in sys.path:
    sys.path.insert(0, _root)

from games.MyGame.game_mode import MyGameMode, GameState
from games.MyGame.input.input_manager import InputManager
from games.MyGame.input.sources.mouse import MouseInputSource
from games.MyGame.config import SCREEN_WIDTH, SCREEN_HEIGHT

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("My Game")

    input_manager = InputManager(MouseInputSource())
    game = MyGameMode()
    clock = pygame.time.Clock()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        input_manager.update(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        events = input_manager.get_events()
        game.handle_input(events)
        game.update(dt)
        game.render(screen)
        pygame.display.flip()

        if game.state == GameState.GAME_OVER:
            print(f"Game Over! Score: {game.get_score()}")
            running = False

    pygame.quit()
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 9. Create __init__.py

```python
"""MyGame package."""
```

## Running Your Game

### Standalone (Development)
```bash
python games/MyGame/main.py
```

### With AMS
```bash
# Verify it appears
python ams_game.py --list-games

# Play with mouse
python ams_game.py --game mygame --backend mouse

# Play with laser pointer
python ams_game.py --game mygame --backend laser --fullscreen
```

## Game Protocol Reference

### Required Interface

Your game mode class MUST have:

| Method/Property | Signature | Description |
|-----------------|-----------|-------------|
| `state` | `@property -> GameState` | Current game state |
| `get_score()` | `() -> int` | Current score |
| `handle_input(events)` | `(List[InputEvent]) -> None` | Process input |
| `update(dt)` | `(float) -> None` | Update logic |
| `render(screen)` | `(pygame.Surface) -> None` | Draw game |

### InputEvent Structure

```python
class InputEvent:
    position: Vector2D  # .x and .y in pixels
    timestamp: float    # Time of event
    event_type: EventType  # HIT or MISS
```

### GameState Enum

Your game needs at minimum:
```python
class GameState(Enum):
    PLAYING = "playing"
    GAME_OVER = "game_over"
```

Optionally add `WON = "won"` for win conditions.

## Adding CLI Arguments

To add game-specific command-line arguments, define them in `game_info.py`:

```python
ARGUMENTS = [
    {
        'name': '--difficulty',
        'type': str,
        'default': 'normal',
        'help': 'Game difficulty (easy, normal, hard)'
    },
    {
        'name': '--time-limit',
        'type': int,
        'default': None,
        'help': 'Time limit in seconds'
    },
]

def get_game_mode(**kwargs):
    difficulty = kwargs.get('difficulty', 'normal')
    time_limit = kwargs.get('time_limit')
    return MyGameMode(difficulty=difficulty, time_limit=time_limit)
```

Note: You'll need to add these arguments to `ams_game.py` parser as well for them to work via CLI.

## Design Considerations for Multi-Device Support

The AMS platform supports many input devices with vastly different characteristics. **All games must be designed with this in mind.**

### Input Device Speed Variance

| Device | Cycle Time | Notes |
|--------|------------|-------|
| Laser Pointer | instant | Continuous pointing |
| Nerf Blaster | ~0.3s | Rapid fire |
| Foam Balls | ~1s | Throw and retrieve |
| Darts | ~2s | Aim, throw, retrieve |
| Archery | 3-8s | Nock, draw, aim, release |

**Required:** All timing parameters (spawn rates, target duration, combo windows) must be configurable to accommodate any device speed.

### Physical Resource Constraints (Quiver/Ammo)

Some devices have limited ammunition requiring retrieval:

| Device | Typical Capacity |
|--------|------------------|
| Archery | 3-12 arrows |
| Darts | 3-6 darts |
| Nerf (magazine) | 6-30 darts |

**Consider implementing:**

- `--quiver-size N` - Limit shots per round, then pause for retrieval
- `--retrieval-pause N` - Seconds between rounds (or manual "ready" signal)
- Round-based play structure matching physical ammo capacity

### Pacing Presets

Rather than "difficulty levels", consider **pacing presets** that adjust all timing parameters together:

```python
PACING_PRESETS = {
    'archery': {
        'spawn_interval': 5.0,
        'target_duration': 6.0,
        'combo_window': 8.0,  # Long enough for draw-aim-release-retrieve
        'max_simultaneous': 2,
    },
    'throwing': {
        'spawn_interval': 2.0,
        'target_duration': 4.0,
        'combo_window': 3.0,
        'max_simultaneous': 4,
    },
    'blaster': {
        'spawn_interval': 0.75,
        'target_duration': 2.5,
        'combo_window': 1.5,
        'max_simultaneous': 6,
    },
}
```

### Key Design Questions

When designing a new game, ask:

1. **Does timing scale?** Can an archer complete the core loop in time?
2. **Is ammo considered?** What happens when arrows run out?
3. **Are pauses handled?** Retrieval time shouldn't end the game
4. **Does combo/streak logic account for slow devices?** 8+ second windows for archery

## Tips

### Development Workflow
1. Start with standalone mode (`python games/MyGame/main.py`)
2. Get game mechanics working with mouse
3. Test with AMS mouse backend (`ams_game.py --game mygame --backend mouse`)
4. Test with laser/object backends when ready

### Configuration Best Practices
- Put all tunable values in `.env`
- Use `config.py` to load and validate
- Support command-line overrides for testing

### Input Handling
- `event.position.x` and `event.position.y` are pixel coordinates
- Check collision using distance or bounds
- Events are already filtered to valid screen positions

## Common Input Module

The shared input module at `games/common/input/` provides:

### InputEvent (Pydantic Model)

```python
from games.common.input import InputEvent

class InputEvent(BaseModel):
    position: Vector2D    # .x and .y in screen pixels
    timestamp: float      # time.monotonic() when event occurred
    event_type: EventType # HIT or MISS (default: HIT)
```

- **Immutable** (frozen Pydantic model)
- **Validated** (timestamp must be non-negative)
- Works with all input backends (mouse, laser, object detection)

### InputManager

```python
from games.common.input import InputManager
from games.common.input.sources import MouseInputSource

manager = InputManager(MouseInputSource())

# In game loop:
manager.update(dt)           # Collect events from source
events = manager.get_events() # Get collected events
```

### InputSource (Abstract Base)

All input backends implement this interface:

```python
class InputSource(ABC):
    def update(self, dt: float) -> None:
        """Update source, collecting events."""
        pass

    def poll_events(self) -> List[InputEvent]:
        """Return collected events since last poll."""
        pass
```

Built-in sources:
- `MouseInputSource` - Development/testing with mouse clicks

## Example Games

Study these existing games for reference:

- **BalloonPop** (`games/BalloonPop/`) - Simple, clean example
- **Grouping** (`games/Grouping/`) - Multiple game modes, precision training
- **ManyTargets** (`games/ManyTargets/`) - Target field clearance, configurable modes
- **DuckHunt** (`games/DuckHunt/`) - More complex with modes and trajectories

## Troubleshooting

### Game doesn't appear in --list-games
- Ensure `game_info.py` exists
- Check for import errors: `python -c "from games.MyGame.game_info import *"`

### Import errors when running
- Check path setup in `main.py`
- Use full package paths: `from games.MyGame.module import ...`

### Input not working
- Verify `input/` re-export files import from `games.common.input`
- Check `input_manager.update(dt)` is called each frame
- Verify `input_manager.get_events()` returns events
- Test imports: `python -c "from games.MyGame.input import InputManager"`
