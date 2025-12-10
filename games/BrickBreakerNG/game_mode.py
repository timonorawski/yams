"""BrickBreaker NextGen - Lua behavior-driven brick breaker.

This is a reimplementation of BrickBreaker using the GameEngine framework
with Lua behaviors. It serves as:
1. A proof-of-concept for the behavior system
2. A comparison platform against the original Python implementation
3. A template for creating new behavior-driven games

Game logic is split between:

Entity behaviors (ams/behaviors/lua/):
- paddle: Stopping paddle that slides to target position
- ball: Movement, velocity, wall bouncing, launch
- brick: Hit tracking, damage state

Collision actions (ams/behaviors/collision_actions/):
- bounce_paddle: Ball bounces off paddle at angle based on hit position
- bounce_reflect: Ball bounces off solid surface
- take_damage: Entity takes damage, can be destroyed

Game definition in game.yaml defines:
- Entity types with inheritance (extends)
- Collision behaviors mapping type pairs to actions
- Win conditions based on base_type

Level YAML files define brick layouts using ASCII art.
"""

from pathlib import Path
from typing import Optional

import yaml

from games.common import GameEngine, GameEngineSkin

from .level_loader import NGLevelLoader


# Load game metadata from YAML at import time
def _load_game_metadata():
    """Load name/description/version/author/defaults from game.yaml."""
    game_yaml = Path(__file__).parent / 'game.yaml'
    if game_yaml.exists():
        with open(game_yaml) as f:
            data = yaml.safe_load(f)
            return {
                'name': data.get('name', 'Unnamed Game'),
                'description': data.get('description', ''),
                'version': data.get('version', '1.0.0'),
                'author': data.get('author', ''),
                'defaults': data.get('defaults', {}),
            }
    return {'name': 'Unnamed Game', 'description': '', 'version': '1.0.0',
            'author': '', 'defaults': {}}

_GAME_META = _load_game_metadata()


# Screen constants (fallback if not in game.yaml)
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600


class BrickBreakerNGSkin(GameEngineSkin):
    """Geometric rendering skin for BrickBreaker NG.

    All rendering is now YAML-driven via game.yaml render commands:
    - Base brick fill and outline
    - Damage darkening via alpha: $damage_ratio with when: condition
    - Hit count text via shape: text with when: condition
    """
    pass  # All rendering handled by base class


class BrickBreakerNGMode(GameEngine):
    """BrickBreaker NextGen - behavior-driven brick breaker."""

    # Metadata from game.yaml
    NAME = _GAME_META['name']
    DESCRIPTION = _GAME_META['description']
    VERSION = _GAME_META['version']
    AUTHOR = _GAME_META['author']

    # Enable YAML-based game definition and levels
    GAME_DEF_FILE = Path(__file__).parent / 'game.yaml'
    LEVELS_DIR = Path(__file__).parent / 'levels'

    # CLI arguments with defaults from game.yaml
    ARGUMENTS = [
        {
            'name': '--lives',
            'type': int,
            'default': _GAME_META['defaults'].get('lives', 3),
            'help': 'Starting lives'
        },
    ]

    def __init__(
        self,
        lives: int = _GAME_META['defaults'].get('lives', 3),
        width: int = SCREEN_WIDTH,
        height: int = SCREEN_HEIGHT,
        **kwargs,
    ):
        """Initialize BrickBreaker NG."""
        self._paddle_id: Optional[str] = None

        # Remove skin from kwargs if present (we handle it internally)
        kwargs.pop('skin', None)

        super().__init__(
            skin='default',
            lives=lives,
            width=width,
            height=height,
            **kwargs,
        )

    def _get_skin(self, _skin_name: str) -> GameEngineSkin:
        """Get rendering skin."""
        return BrickBreakerNGSkin()

    def _create_level_loader(self) -> NGLevelLoader:
        """Create BrickBreaker NG level loader."""
        return NGLevelLoader(self.LEVELS_DIR)

    # All game logic is now handled declaratively by GameEngine:
    # - player spawn: player.type + player.spawn in game.yaml
    # - level application: GameEngine._apply_level_config() using protocol
    # - default layout: default_layout.brick_grid in game.yaml
    # - input mapping: input_mapping in game.yaml
    # - collision behaviors: collision_behaviors in game.yaml
    # - lose conditions: lose_conditions in game.yaml
    # - win conditions: win_target_type in game.yaml
