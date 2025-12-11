"""
Level loader for Sweet Physics.

Loads level definitions from YAML files using the common level system.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ams.games.levels import LevelLoader as BaseLevelLoader


@dataclass
class StarRequirements:
    """Requirements for each star rating."""
    one_star: Dict[str, Any] = field(default_factory=lambda: {'complete': True})
    two_star: Dict[str, Any] = field(default_factory=dict)
    three_star: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ElementData:
    """Data for a single level element."""
    type: str
    position: Optional[Tuple[float, float]] = None
    # Rope-specific
    anchor: Optional[Tuple[float, float]] = None
    attachment: Optional[str] = None
    segments: int = 8
    length: float = 150
    # Platform-specific
    start: Optional[Tuple[float, float]] = None
    end: Optional[Tuple[float, float]] = None
    thickness: float = 10
    # Goal/Star-specific
    radius: Optional[float] = None
    # Extra properties
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LevelData:
    """Complete level definition."""
    name: str
    author: str = "Unknown"
    difficulty: int = 1
    description: str = ""

    # Arrow budget (None = unlimited)
    arrow_budget: Optional[int] = None

    # Star requirements
    stars: StarRequirements = field(default_factory=StarRequirements)

    # Physics settings
    gravity: Tuple[float, float] = (0, 980)
    air_resistance: float = 0.995

    # Elements
    elements: List[ElementData] = field(default_factory=list)

    # Metadata
    file_path: Optional[Path] = None


class SweetPhysicsLevelLoader(BaseLevelLoader[LevelData]):
    """
    Level loader for Sweet Physics game.

    Extends the common LevelLoader with game-specific parsing.
    """

    def _parse_level_data(self, data: Dict[str, Any], file_path: Path) -> LevelData:
        """Parse raw YAML data into LevelData."""
        if not isinstance(data, dict):
            raise ValueError(f"Invalid level format: expected dict, got {type(data)}")

        # Parse star requirements
        stars_data = data.get('stars', {})
        stars = StarRequirements(
            one_star=stars_data.get('one_star', {'complete': True}),
            two_star=stars_data.get('two_star', {}),
            three_star=stars_data.get('three_star', {}),
        )

        # Parse physics settings
        physics = data.get('physics', {})
        gravity = tuple(physics.get('gravity', [0, 980]))
        air_resistance = physics.get('air_resistance', 0.995)

        # Parse elements
        elements = []
        for elem_data in data.get('elements', []):
            elements.append(self._parse_element(elem_data))

        return LevelData(
            name=data.get('name', 'Untitled'),
            author=data.get('author', 'Unknown'),
            difficulty=data.get('difficulty', 1),
            description=data.get('description', ''),
            arrow_budget=data.get('arrow_budget'),
            stars=stars,
            gravity=gravity,
            air_resistance=air_resistance,
            elements=elements,
            file_path=file_path,
        )

    def _parse_element(self, data: Dict[str, Any]) -> ElementData:
        """Parse element data from YAML."""
        elem_type = data.get('type', 'unknown')

        # Parse position (can be list or dict)
        position = None
        if 'position' in data:
            pos = data['position']
            if isinstance(pos, (list, tuple)):
                position = tuple(pos)
            elif isinstance(pos, dict):
                position = (pos.get('x', 0), pos.get('y', 0))

        # Parse anchor for ropes
        anchor = None
        if 'anchor' in data:
            anc = data['anchor']
            if isinstance(anc, (list, tuple)):
                anchor = tuple(anc)
            elif isinstance(anc, dict):
                anchor = (anc.get('x', 0), anc.get('y', 0))

        # Parse start/end for platforms
        start = None
        end = None
        if 'start' in data:
            s = data['start']
            start = tuple(s) if isinstance(s, (list, tuple)) else (s.get('x', 0), s.get('y', 0))
        if 'end' in data:
            e = data['end']
            end = tuple(e) if isinstance(e, (list, tuple)) else (e.get('x', 0), e.get('y', 0))

        return ElementData(
            type=elem_type,
            position=position,
            anchor=anchor,
            attachment=data.get('attachment'),
            segments=data.get('segments', 8),
            length=data.get('length', 150),
            start=start,
            end=end,
            thickness=data.get('thickness', 10),
            radius=data.get('radius'),
            properties=data.get('properties', {}),
        )


def create_default_level() -> LevelData:
    """Create a simple default level for testing."""
    return LevelData(
        name="Tutorial 1: Simple Drop",
        author="AMS Team",
        difficulty=1,
        description="Cut the rope to drop the candy into the goal",
        arrow_budget=3,
        elements=[
            ElementData(type='candy', position=(640, 150)),
            ElementData(type='rope', anchor=(640, 50), attachment='candy', length=100, segments=6),
            ElementData(type='goal', position=(640, 550), radius=60),
            ElementData(type='star', position=(640, 350)),
        ],
    )
