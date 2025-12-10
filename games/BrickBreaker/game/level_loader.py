"""Level loader for BrickBreaker game.

Loads YAML levels with ASCII art brick layouts and data-driven brick behaviors.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from games.common.levels import LevelLoader as BaseLevelLoader

from .entities.brick import BrickBehaviors


@dataclass
class PaddleConfig:
    """Paddle configuration from level YAML."""
    width: float = 120.0
    height: float = 20.0
    speed: float = 500.0
    y_position: float = 0.9


@dataclass
class BallConfig:
    """Ball configuration from level YAML."""
    radius: float = 10.0
    speed: float = 300.0
    max_speed: float = 600.0
    speed_increase: float = 5.0


@dataclass
class BrickPlacement:
    """A brick placement in the level."""
    brick_type: str
    x: float
    y: float
    width: float
    height: float
    row: int
    col: int


@dataclass
class LevelData:
    """Parsed level data ready for game use."""
    name: str
    description: str = ""
    difficulty: int = 1
    author: str = "unknown"

    # Brick type definitions (name -> BrickBehaviors)
    brick_types: Dict[str, BrickBehaviors] = field(default_factory=dict)

    # Brick placements
    bricks: List[BrickPlacement] = field(default_factory=list)

    # Entity configs
    paddle: PaddleConfig = field(default_factory=PaddleConfig)
    ball: BallConfig = field(default_factory=BallConfig)

    # Game rules
    lives: int = 3
    time_limit: Optional[float] = None

    # Source file
    file_path: Optional[Path] = None


class BrickBreakerLevelLoader(BaseLevelLoader[LevelData]):
    """Loads and parses BrickBreaker levels from YAML."""

    def _parse_level_data(self, data: Dict[str, Any], file_path: Path) -> LevelData:
        """Parse YAML data into LevelData.

        Args:
            data: Raw YAML data dict
            file_path: Path to the level file

        Returns:
            Parsed LevelData object
        """
        # Parse brick types
        brick_types = self._parse_brick_types(data.get('brick_types', {}))

        # Parse brick layout
        bricks = self._parse_layout(data, brick_types)

        # Parse paddle config
        paddle_data = data.get('paddle', {})
        paddle = PaddleConfig(
            width=paddle_data.get('width', 120.0),
            height=paddle_data.get('height', 20.0),
            speed=paddle_data.get('speed', 500.0),
            y_position=paddle_data.get('y_position', 0.9),
        )

        # Parse ball config
        ball_data = data.get('ball', {})
        ball = BallConfig(
            radius=ball_data.get('radius', 10.0),
            speed=ball_data.get('speed', 300.0),
            max_speed=ball_data.get('max_speed', 600.0),
            speed_increase=ball_data.get('speed_increase', 5.0),
        )

        return LevelData(
            name=data.get('name', 'Untitled'),
            description=data.get('description', ''),
            difficulty=data.get('difficulty', 1),
            author=data.get('author', 'unknown'),
            brick_types=brick_types,
            bricks=bricks,
            paddle=paddle,
            ball=ball,
            lives=data.get('lives', 3),
            time_limit=data.get('time_limit'),
            file_path=file_path,
        )

    def _parse_brick_types(
        self,
        types_data: Dict[str, Any],
    ) -> Dict[str, BrickBehaviors]:
        """Parse brick type definitions into BrickBehaviors.

        Args:
            types_data: Dict of brick type name -> config

        Returns:
            Dict of brick type name -> BrickBehaviors
        """
        brick_types = {}

        for name, config in types_data.items():
            behaviors = BrickBehaviors(
                hits=config.get('hits', 1),
                points=config.get('points', 100),
                color=config.get('color', 'red'),
                descends=config.get('descends', False),
                descend_speed=config.get('descend_speed', 0.0),
                oscillates=config.get('oscillates', False),
                oscillate_speed=config.get('oscillate_speed', 0.0),
                oscillate_range=config.get('oscillate_range', 0.0),
                shoots=config.get('shoots', False),
                shoot_interval=config.get('shoot_interval', 3.0),
                shoot_speed=config.get('shoot_speed', 200.0),
                hit_direction=config.get('hit_direction', 'any'),
                splits=config.get('splits', False),
                split_into=config.get('split_into', 2),
                explodes=config.get('explodes', False),
                explosion_radius=config.get('explosion_radius', 1),
                indestructible=config.get('indestructible', False),
                power_up=config.get('power_up'),
            )
            brick_types[name] = behaviors

        return brick_types

    def _parse_layout(
        self,
        data: Dict[str, Any],
        brick_types: Dict[str, BrickBehaviors],
    ) -> List[BrickPlacement]:
        """Parse brick layout from ASCII art or brick list.

        Args:
            data: Level YAML data
            brick_types: Parsed brick type definitions

        Returns:
            List of BrickPlacement objects
        """
        # Grid configuration
        brick_width = data.get('brick_width', 70.0)
        brick_height = data.get('brick_height', 25.0)
        grid_offset_x = data.get('grid_offset_x', 65.0)
        grid_offset_y = data.get('grid_offset_y', 80.0)

        bricks = []

        # Check for ASCII layout
        layout = data.get('layout')
        if layout:
            layout_key = data.get('layout_key', {})
            bricks = self._parse_ascii_layout(
                layout, layout_key, brick_types,
                brick_width, brick_height,
                grid_offset_x, grid_offset_y,
            )
        else:
            # Fall back to explicit brick list
            brick_list = data.get('bricks', [])
            for i, brick_def in enumerate(brick_list):
                brick_type = brick_def.get('type', 'default')
                if brick_type not in brick_types:
                    continue

                row = brick_def.get('row', 0)
                col = brick_def.get('col', 0)

                # Use explicit position if provided, otherwise grid position
                x = brick_def.get('x', grid_offset_x + col * brick_width)
                y = brick_def.get('y', grid_offset_y + row * brick_height)

                bricks.append(BrickPlacement(
                    brick_type=brick_type,
                    x=x,
                    y=y,
                    width=brick_def.get('width', brick_width),
                    height=brick_def.get('height', brick_height),
                    row=row,
                    col=col,
                ))

        return bricks

    def _parse_ascii_layout(
        self,
        layout: str,
        layout_key: Dict[str, str],
        brick_types: Dict[str, BrickBehaviors],
        brick_width: float,
        brick_height: float,
        grid_offset_x: float,
        grid_offset_y: float,
    ) -> List[BrickPlacement]:
        """Parse ASCII art layout into brick placements.

        Args:
            layout: Multi-line ASCII art string
            layout_key: Maps characters to brick type names
            brick_types: Available brick types
            brick_width: Width of each brick
            brick_height: Height of each brick
            grid_offset_x: X offset for grid start
            grid_offset_y: Y offset for grid start

        Returns:
            List of BrickPlacement objects
        """
        bricks = []
        lines = layout.strip().split('\n')

        for row, line in enumerate(lines):
            for col, char in enumerate(line):
                # Skip whitespace and empty markers
                if char in (' ', '.', '-', '_'):
                    continue

                # Look up brick type from layout key
                brick_type = layout_key.get(char)
                if not brick_type or brick_type == 'empty':
                    continue

                # Verify brick type exists
                if brick_type not in brick_types:
                    continue

                x = grid_offset_x + col * brick_width
                y = grid_offset_y + row * brick_height

                bricks.append(BrickPlacement(
                    brick_type=brick_type,
                    x=x,
                    y=y,
                    width=brick_width,
                    height=brick_height,
                    row=row,
                    col=col,
                ))

        return bricks
