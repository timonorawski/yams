"""YAML-driven game engine using Lua behaviors.

GameEngine extends BaseGame to provide a data-driven game framework where:
- Game definitions come from YAML (entities, behaviors, levels)
- Entity logic is implemented in Lua behaviors
- Python handles rendering, input, and collision detection

This enables creating new games primarily through configuration rather than code.

Usage:
    class MyGame(GameEngine):
        NAME = "My Game"
        GAME_DEF_FILE = Path(__file__).parent / 'game.yaml'

        def _get_skin(self, skin_name: str) -> GameEngineSkin:
            return MyGameSkin()
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pygame
import yaml

from games.common import BaseGame, GameState
from games.common.input import InputEvent
from ams.behaviors import BehaviorEngine, Entity


@dataclass
class EntityTypeConfig:
    """Configuration for an entity type from YAML."""

    name: str
    width: float = 32.0
    height: float = 32.0
    color: str = "white"
    sprite: str = ""
    behaviors: List[str] = field(default_factory=list)
    behavior_config: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    health: int = 1
    points: int = 0
    tags: List[str] = field(default_factory=list)


@dataclass
class GameDefinition:
    """Complete game definition loaded from YAML."""

    name: str = "Unnamed Game"
    screen_width: int = 800
    screen_height: int = 600
    background_color: Tuple[int, int, int] = (20, 20, 30)

    # Entity type definitions
    entity_types: Dict[str, EntityTypeConfig] = field(default_factory=dict)

    # Player config
    player_type: Optional[str] = None
    player_spawn: Tuple[float, float] = (400, 500)

    # Win/lose conditions
    win_condition: str = "destroy_all"  # destroy_all, survive_time, reach_score
    win_target: int = 0  # Score target or time in seconds
    lose_on_player_death: bool = True

    # Level spawning (for games without explicit levels)
    spawn_patterns: List[Dict[str, Any]] = field(default_factory=list)


class GameEngineSkin:
    """Abstract base for GameEngine rendering.

    Subclasses implement game-specific rendering for entities.
    """

    def render_entity(self, entity: Entity, screen: pygame.Surface) -> None:
        """Render an entity.

        Default implementation draws a colored rectangle.
        Override for custom rendering.
        """
        color = self._parse_color(entity.color)
        rect = pygame.Rect(int(entity.x), int(entity.y),
                           int(entity.width), int(entity.height))
        pygame.draw.rect(screen, color, rect)

    def render_hud(self, screen: pygame.Surface, score: int, lives: int,
                   level_name: str = "") -> None:
        """Render HUD elements."""
        font = pygame.font.Font(None, 36)

        # Score
        score_text = font.render(f"Score: {score}", True, (255, 255, 255))
        screen.blit(score_text, (10, 10))

        # Lives
        lives_text = font.render(f"Lives: {lives}", True, (255, 255, 255))
        screen.blit(lives_text, (screen.get_width() - 120, 10))

        # Level name
        if level_name:
            level_text = font.render(level_name, True, (200, 200, 200))
            level_rect = level_text.get_rect(centerx=screen.get_width() // 2, y=10)
            screen.blit(level_text, level_rect)

    def update(self, dt: float) -> None:
        """Update skin animations."""
        pass

    def play_sound(self, sound_name: str) -> None:
        """Play a sound effect."""
        pass

    def _parse_color(self, color_str: str) -> Tuple[int, int, int]:
        """Parse color string to RGB tuple."""
        colors = {
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'red': (220, 60, 60),
            'green': (60, 220, 60),
            'blue': (60, 60, 220),
            'yellow': (220, 220, 60),
            'orange': (220, 140, 60),
            'purple': (160, 60, 220),
            'cyan': (60, 220, 220),
            'gray': (128, 128, 128),
            'silver': (192, 192, 192),
        }
        return colors.get(color_str.lower(), (255, 255, 255))


class GameEngine(BaseGame):
    """YAML-driven game engine with Lua behaviors.

    This extends BaseGame to provide:
    - Automatic entity management via BehaviorEngine
    - YAML-based game definitions
    - Lua behavior scripting
    - Standard collision detection patterns

    Subclasses must implement:
    - _get_skin(): Return rendering skin instance
    - _handle_collision(): Game-specific collision logic

    Can optionally implement:
    - _on_entity_destroyed(): Handle entity death
    - _spawn_initial_entities(): Create starting entities
    """

    # Game definition file (override in subclass)
    GAME_DEF_FILE: Optional[Path] = None

    # Custom behaviors directory (override to add game-specific behaviors)
    BEHAVIORS_DIR: Optional[Path] = None

    def __init__(
        self,
        skin: str = 'default',
        lives: int = 3,
        width: int = 800,
        height: int = 600,
        **kwargs,
    ):
        """Initialize game engine.

        Args:
            skin: Skin name for rendering
            lives: Starting lives
            width: Screen width
            height: Screen height
            **kwargs: BaseGame arguments
        """
        # Initialize before super().__init__ (may call _apply_level_config)
        self._starting_lives = lives
        self._lives = lives
        self._screen_width = width
        self._screen_height = height
        self._score = 0
        self._internal_state = GameState.PLAYING
        self._game_def: Optional[GameDefinition] = None
        self._level_name = ""

        # Create behavior engine
        self._behavior_engine = BehaviorEngine(
            screen_width=width,
            screen_height=height,
        )

        # Load core behaviors
        self._behavior_engine.load_behaviors_from_dir()

        # Load game-specific behaviors
        if self.BEHAVIORS_DIR and self.BEHAVIORS_DIR.exists():
            self._behavior_engine.load_behaviors_from_dir(self.BEHAVIORS_DIR)

        # Load game definition
        if self.GAME_DEF_FILE and self.GAME_DEF_FILE.exists():
            self._game_def = self._load_game_definition(self.GAME_DEF_FILE)

        # Create skin
        self._skin = self._get_skin(skin)

        # Player entity reference
        self._player_id: Optional[str] = None

        # Call super init (may load levels)
        super().__init__(**kwargs)

        # Spawn initial entities if no level loaded
        if not self._behavior_engine.entities:
            self._spawn_initial_entities()

    def _load_game_definition(self, path: Path) -> GameDefinition:
        """Load game definition from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        game_def = GameDefinition(
            name=data.get('name', 'Unnamed Game'),
            screen_width=data.get('screen_width', 800),
            screen_height=data.get('screen_height', 600),
            background_color=tuple(data.get('background_color', [20, 20, 30])),
            win_condition=data.get('win_condition', 'destroy_all'),
            win_target=data.get('win_target', 0),
            lose_on_player_death=data.get('lose_on_player_death', True),
            spawn_patterns=data.get('spawn_patterns', []),
        )

        # Parse entity types
        for name, type_data in data.get('entity_types', {}).items():
            game_def.entity_types[name] = EntityTypeConfig(
                name=name,
                width=type_data.get('width', 32),
                height=type_data.get('height', 32),
                color=type_data.get('color', 'white'),
                sprite=type_data.get('sprite', ''),
                behaviors=type_data.get('behaviors', []),
                behavior_config=type_data.get('behavior_config', {}),
                health=type_data.get('health', 1),
                points=type_data.get('points', 0),
                tags=type_data.get('tags', []),
            )

        # Player config
        if 'player' in data:
            player_data = data['player']
            game_def.player_type = player_data.get('type')
            game_def.player_spawn = tuple(player_data.get('spawn', [400, 500]))

        return game_def

    @abstractmethod
    def _get_skin(self, skin_name: str) -> GameEngineSkin:
        """Get rendering skin instance.

        Override to return game-specific skin.

        Args:
            skin_name: Requested skin name

        Returns:
            GameEngineSkin instance
        """
        return GameEngineSkin()

    def _spawn_initial_entities(self) -> None:
        """Spawn initial entities for the game.

        Override to create starting game state.
        Default does nothing.
        """
        pass

    def spawn_entity(
        self,
        entity_type: str,
        x: float,
        y: float,
        **overrides,
    ) -> Optional[Entity]:
        """Spawn an entity of a defined type.

        Args:
            entity_type: Type name from game definition
            x, y: Position
            **overrides: Override default type properties

        Returns:
            Created Entity, or None if type not found
        """
        # Get type config
        type_config = None
        if self._game_def:
            type_config = self._game_def.entity_types.get(entity_type)

        # Use type config or defaults
        if type_config:
            behaviors = overrides.get('behaviors', type_config.behaviors)
            behavior_config = overrides.get('behavior_config', type_config.behavior_config)

            entity = self._behavior_engine.create_entity(
                entity_type=entity_type,
                x=x,
                y=y,
                width=overrides.get('width', type_config.width),
                height=overrides.get('height', type_config.height),
                color=overrides.get('color', type_config.color),
                sprite=overrides.get('sprite', type_config.sprite),
                health=overrides.get('health', type_config.health),
                behaviors=behaviors,
                behavior_config=behavior_config,
            )
        else:
            # Create with overrides only
            entity = self._behavior_engine.create_entity(
                entity_type=entity_type,
                x=x,
                y=y,
                **overrides,
            )

        return entity

    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get all alive entities of a type."""
        return [e for e in self._behavior_engine.get_alive_entities()
                if e.entity_type == entity_type]

    def get_entities_by_tag(self, tag: str) -> List[Entity]:
        """Get all alive entities with a tag."""
        result = []
        for entity in self._behavior_engine.get_alive_entities():
            if self._game_def:
                type_config = self._game_def.entity_types.get(entity.entity_type)
                if type_config and tag in type_config.tags:
                    result.append(entity)
        return result

    # =========================================================================
    # BaseGame Implementation
    # =========================================================================

    def _get_internal_state(self) -> GameState:
        return self._internal_state

    def get_score(self) -> int:
        return self._score

    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events.

        Default implementation passes to _handle_player_input.
        Override for custom input handling.
        """
        if self._internal_state != GameState.PLAYING:
            return

        for event in events:
            self._handle_player_input(event)

    def _handle_player_input(self, event: InputEvent) -> None:
        """Handle a single input event.

        Override in subclass for game-specific input handling.
        """
        pass

    def update(self, dt: float) -> None:
        """Update game state."""
        if self._internal_state != GameState.PLAYING:
            return

        # Update behavior engine (moves entities, fires callbacks)
        self._behavior_engine.update(dt)

        # Process queued sounds
        for sound in self._behavior_engine.pop_sounds():
            self._skin.play_sound(sound)

        # Check collisions
        self._check_collisions()

        # Handle destroyed entities
        self._handle_destroyed_entities()

        # Update skin
        self._skin.update(dt)

        # Check win/lose conditions
        self._check_win_conditions()
        self._check_lose_conditions()

    def _check_collisions(self) -> None:
        """Check and handle collisions.

        Override in subclass for game-specific collision logic.
        Default: no collision handling.
        """
        pass

    def _handle_collision(self, entity_a: Entity, entity_b: Entity) -> None:
        """Handle a collision between two entities.

        Override in subclass.
        """
        pass

    def _handle_destroyed_entities(self) -> None:
        """Process recently destroyed entities.

        Called after update to handle scoring, effects, etc.
        """
        # Check for entities that died this frame
        for entity in list(self._behavior_engine.entities.values()):
            if not entity.alive:
                self._on_entity_destroyed(entity)

    def _on_entity_destroyed(self, entity: Entity) -> None:
        """Handle entity destruction.

        Override to add scoring, effects, etc.
        """
        # Default: add points if entity type has them
        if self._game_def:
            type_config = self._game_def.entity_types.get(entity.entity_type)
            if type_config:
                self._score += type_config.points

    def _check_win_conditions(self) -> None:
        """Check if player has won.

        Override for custom win conditions.
        """
        if not self._game_def:
            return

        if self._game_def.win_condition == 'destroy_all':
            # Win when all enemies destroyed
            enemies = self.get_entities_by_tag('enemy')
            if not enemies:
                self._internal_state = GameState.WON

        elif self._game_def.win_condition == 'reach_score':
            if self._score >= self._game_def.win_target:
                self._internal_state = GameState.WON

    def _check_lose_conditions(self) -> None:
        """Check if player has lost."""
        if self._lives <= 0:
            self._internal_state = GameState.GAME_OVER

    def lose_life(self) -> None:
        """Lose a life."""
        self._lives -= 1
        if self._lives <= 0:
            self._internal_state = GameState.GAME_OVER

    def render(self, screen: pygame.Surface) -> None:
        """Render the game."""
        # Clear with background color
        bg = (20, 20, 30)
        if self._game_def:
            bg = self._game_def.background_color
        screen.fill(bg)

        # Render all entities
        for entity in self._behavior_engine.get_alive_entities():
            if entity.visible:
                self._skin.render_entity(entity, screen)

        # Render HUD
        self._skin.render_hud(screen, self._score, self._lives, self._level_name)

        # Render game over / win overlay
        if self._internal_state == GameState.GAME_OVER:
            self._render_overlay(screen, "GAME OVER", (255, 100, 100))
        elif self._internal_state == GameState.WON:
            self._render_overlay(screen, "YOU WIN!", (100, 255, 100))

    def _render_overlay(self, screen: pygame.Surface, text: str,
                        color: Tuple[int, int, int]) -> None:
        """Render a centered text overlay."""
        font = pygame.font.Font(None, 72)
        text_surf = font.render(text, True, color)
        rect = text_surf.get_rect(center=(self._screen_width // 2,
                                          self._screen_height // 2))
        screen.blit(text_surf, rect)

        font_small = pygame.font.Font(None, 36)
        score_text = font_small.render(f"Final Score: {self._score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self._screen_width // 2,
                                                 self._screen_height // 2 + 50))
        screen.blit(score_text, score_rect)

    def reset(self) -> None:
        """Reset game state."""
        super().reset()
        self._behavior_engine.clear()
        self._score = 0
        self._lives = self._starting_lives
        self._internal_state = GameState.PLAYING
        self._spawn_initial_entities()
