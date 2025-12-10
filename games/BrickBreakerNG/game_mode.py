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
from typing import List, Optional

import pygame
import yaml

from games.common import GameEngine, GameEngineSkin, GameState
from ams.behaviors import Entity

from .level_loader import NGLevelLoader, NGLevelData


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

    Uses YAML render commands for basic shapes, adds:
    - Damage darkening for multi-hit bricks
    - Hit count text overlay for multi-hit bricks
    """

    def render_entity(self, entity: Entity, screen: pygame.Surface) -> None:
        """Render entity using YAML commands + brick damage overlay."""
        # Use base class YAML-driven rendering
        super().render_entity(entity, screen)

        # Add damage overlay for bricks
        if entity.entity_type.startswith('brick') or entity.entity_type.startswith('invader'):
            self._render_brick_overlay(entity, screen)

    def _render_brick_overlay(self, entity: Entity, screen: pygame.Surface) -> None:
        """Add damage indication and hit count for multi-hit bricks."""
        hits_remaining = entity.properties.get('brick_hits_remaining', 1)
        max_hits = entity.properties.get('brick_max_hits', 1)

        # Only show for multi-hit bricks
        if max_hits > 1 and hits_remaining > 0:
            # Damage overlay (darken)
            damage_ratio = 1 - (hits_remaining / max_hits)
            if damage_ratio > 0:
                rect = pygame.Rect(int(entity.x), int(entity.y),
                                   int(entity.width), int(entity.height))
                overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, int(damage_ratio * 100)))
                screen.blit(overlay, rect.topleft)

            # Hit count text
            font = pygame.font.Font(None, 20)
            text = font.render(str(hits_remaining), True, (255, 255, 255))
            rect = pygame.Rect(int(entity.x), int(entity.y),
                               int(entity.width), int(entity.height))
            text_rect = text.get_rect(center=rect.center)
            screen.blit(text, text_rect)


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

    def _apply_level_config(self, level_data: NGLevelData) -> None:
        """Apply level configuration - spawn entities from level YAML.

        Args:
            level_data: Parsed level data from NGLevelLoader
        """
        # Clear existing entities
        self._behavior_engine.clear()

        # Set level name for HUD
        self._level_name = level_data.name

        # Apply lives from level
        self._lives = level_data.lives
        self._starting_lives = level_data.lives

        # Spawn paddle_ready (composite entity: paddle with ball attached)
        # Transform system will handle splitting into paddle + ball on first input
        paddle_ready = self.spawn_entity(
            'paddle_ready',
            x=level_data.paddle_x,
            y=level_data.paddle_y,
            **level_data.paddle_overrides,
        )
        if paddle_ready:
            self._paddle_id = paddle_ready.id

        # Spawn bricks from ASCII layout
        for brick_placement in level_data.bricks:
            self.spawn_entity(
                brick_placement.entity_type,
                x=brick_placement.x,
                y=brick_placement.y,
            )

        # Reset game state
        self._internal_state = GameState.PLAYING

    def _on_level_transition(self) -> None:
        """Reset state when transitioning to next level in a group."""
        # Ball will be reset by _apply_level_config
        pass

    # All game logic is now handled declaratively by GameEngine:
    # - player spawn: player.type + player.spawn in game.yaml
    # - default layout: default_layout.brick_grid in game.yaml
    # - input mapping: input_mapping in game.yaml
    # - collision behaviors: collision_behaviors in game.yaml
    # - lose conditions: lose_conditions in game.yaml
    # - win conditions: win_target_type in game.yaml
