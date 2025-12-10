"""Level loader for BrickBreaker NG.

Parses YAML level files with ASCII brick layouts.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from games.common.levels import LevelLoader


@dataclass
class BrickPlacement:
    """A brick to spawn at a specific position."""
    entity_type: str
    x: float
    y: float
    row: int
    col: int


@dataclass
class NGLevelData:
    """Parsed level data for BrickBreaker NG.

    Conforms to GameEngineLevelData protocol for generic level application.
    """

    name: str = "Unnamed Level"
    difficulty: int = 1
    lives: int = 3

    # Player spawn position (GameEngineLevelData protocol)
    player_x: float = 340
    player_y: float = 550

    # Grid configuration (BrickBreaker-specific)
    grid_cols: int = 10
    grid_rows: int = 5
    brick_width: float = 70
    brick_height: float = 25
    start_x: float = 65
    start_y: float = 60

    # Entity placements (GameEngineLevelData protocol uses 'entities')
    # For backwards compatibility, we store as 'bricks' but expose as 'entities'
    bricks: List[BrickPlacement] = field(default_factory=list)

    @property
    def entities(self) -> List[BrickPlacement]:
        """Alias for bricks - conforms to GameEngineLevelData protocol."""
        return self.bricks


class NGLevelLoader(LevelLoader[NGLevelData]):
    """Level loader for BrickBreaker NG levels."""

    def __init__(self, levels_dir: Path, game_def: Optional[Dict] = None):
        """Initialize loader.

        Args:
            levels_dir: Directory containing level YAML files
            game_def: Game definition with entity types (optional)
        """
        super().__init__(levels_dir)
        self._game_def = game_def

    def _parse_level_data(self, data: Dict[str, Any], file_path: Path) -> NGLevelData:
        """Parse level YAML into NGLevelData."""
        level = NGLevelData(
            name=data.get('name', 'Unnamed Level'),
            difficulty=data.get('difficulty', 1),
            lives=data.get('lives', 3),
        )

        # Parse grid config
        grid = data.get('grid', {})
        level.grid_cols = grid.get('cols', 10)
        level.grid_rows = grid.get('rows', 5)
        level.brick_width = grid.get('brick_width', 70)
        level.brick_height = grid.get('brick_height', 25)
        level.start_x = grid.get('start_x', 65)
        level.start_y = grid.get('start_y', 60)

        # Parse player/paddle config (uses player_x/player_y for protocol)
        paddle = data.get('paddle', {})
        level.player_x = paddle.get('x', 340)
        level.player_y = paddle.get('y', 550)

        # Parse ASCII layout
        layout_str = data.get('layout', '')
        layout_key = data.get('layout_key', {})

        if layout_str:
            level.bricks = self._parse_ascii_layout(
                layout_str,
                layout_key,
                level.start_x,
                level.start_y,
                level.brick_width,
                level.brick_height,
            )

        return level

    def _parse_ascii_layout(
        self,
        layout_str: str,
        layout_key: Dict[str, str],
        start_x: float,
        start_y: float,
        brick_width: float,
        brick_height: float,
    ) -> List[BrickPlacement]:
        """Parse ASCII art layout into brick placements.

        Args:
            layout_str: Multi-line string with brick layout
            layout_key: Mapping of characters to entity types
            start_x, start_y: Top-left position of grid
            brick_width, brick_height: Brick dimensions

        Returns:
            List of BrickPlacement objects
        """
        bricks = []
        lines = layout_str.strip().split('\n')

        for row, line in enumerate(lines):
            for col, char in enumerate(line):
                if char in layout_key:
                    entity_type = layout_key[char]
                    if entity_type == 'empty' or entity_type == '':
                        continue

                    x = start_x + col * brick_width
                    y = start_y + row * brick_height

                    bricks.append(BrickPlacement(
                        entity_type=entity_type,
                        x=x,
                        y=y,
                        row=row,
                        col=col,
                    ))

        return bricks
