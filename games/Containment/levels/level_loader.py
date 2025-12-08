"""Level loader for Containment game.

Parses YAML level definitions and provides level configuration to the game.
See schema.md for the full YAML format specification.
"""
import os
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml


# =============================================================================
# Data Classes for Level Configuration
# =============================================================================

@dataclass
class CaptureZone:
    """Capture zone configuration (for capture mode)."""
    position: Tuple[float, float]  # Normalized [0-1]
    radius: float  # Normalized


@dataclass
class Objectives:
    """Level objectives configuration."""
    type: str = "survive"  # survive | capture
    time_limit: Optional[int] = 60  # seconds, None = endless
    capture_zone: Optional[CaptureZone] = None


@dataclass
class BallConfig:
    """Ball configuration."""
    count: int = 1
    speed: float = 150.0  # pixels/second base
    radius: float = 20.0
    spawn: Union[str, Tuple[float, float]] = "center"  # center | random | [x, y]
    ai: str = "dumb"  # dumb | reactive | strategic


@dataclass
class GapConfig:
    """Single gap definition."""
    edge: str  # top | bottom | left | right
    range: Tuple[float, float]  # normalized start/end


@dataclass
class EdgeConfig:
    """Screen edge behavior configuration."""
    mode: str = "bounce"  # bounce | gaps
    gaps: List[GapConfig] = field(default_factory=list)


@dataclass
class SpinnerConfig:
    """Initial spinner configuration (environment spinners)."""
    position: Tuple[float, float]  # Normalized [0-1]
    shape: str = "triangle"  # triangle | square | pentagon | hexagon
    size: float = 60.0
    rotation_speed: float = 45.0  # degrees/sec


@dataclass
class Environment:
    """Environment configuration."""
    edges: EdgeConfig = field(default_factory=EdgeConfig)
    spinners: List[SpinnerConfig] = field(default_factory=list)


@dataclass
class HitModeConfig:
    """Configuration for a single hit mode."""
    type: str  # deflector | spinner | point | connect | morph | grow
    weight: int = 1
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HitModes:
    """Hit mode selection configuration."""
    selection: str = "random"  # random | sequential | weighted
    modes: List[HitModeConfig] = field(default_factory=list)

    # Internal state for sequential selection
    _sequence_index: int = field(default=0, init=False, repr=False)

    def get_next_mode(self) -> HitModeConfig:
        """Get the next hit mode based on selection type."""
        if not self.modes:
            # Default to deflector if no modes defined
            return HitModeConfig(type="deflector", config={"angle": "random", "length": 60})

        if self.selection == "sequential":
            mode = self.modes[self._sequence_index % len(self.modes)]
            self._sequence_index += 1
            return mode

        elif self.selection == "weighted":
            total_weight = sum(m.weight for m in self.modes)
            r = random.randint(1, total_weight)
            cumulative = 0
            for mode in self.modes:
                cumulative += mode.weight
                if r <= cumulative:
                    return mode
            return self.modes[-1]  # Fallback

        else:  # random
            return random.choice(self.modes)

    def reset_sequence(self) -> None:
        """Reset sequential selection to start."""
        self._sequence_index = 0


@dataclass
class LevelConfig:
    """Complete level configuration."""
    # Metadata
    name: str = "Untitled"
    description: str = ""
    difficulty: int = 1
    author: str = "unknown"
    version: int = 1

    # Game configuration
    objectives: Objectives = field(default_factory=Objectives)
    ball: BallConfig = field(default_factory=BallConfig)
    environment: Environment = field(default_factory=Environment)
    hit_modes: HitModes = field(default_factory=HitModes)

    # Pacing overrides (applied after loading)
    pacing_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)


# =============================================================================
# YAML Parsing Functions
# =============================================================================

def _parse_capture_zone(data: Dict) -> Optional[CaptureZone]:
    """Parse capture zone from YAML data."""
    if not data:
        return None
    return CaptureZone(
        position=tuple(data.get("position", [0.5, 0.5])),
        radius=data.get("radius", 0.08)
    )


def _parse_objectives(data: Dict) -> Objectives:
    """Parse objectives from YAML data."""
    if not data:
        return Objectives()

    return Objectives(
        type=data.get("type", "survive"),
        time_limit=data.get("time_limit", 60),
        capture_zone=_parse_capture_zone(data.get("capture_zone"))
    )


def _parse_ball(data: Dict) -> BallConfig:
    """Parse ball configuration from YAML data."""
    if not data:
        return BallConfig()

    spawn = data.get("spawn", "center")
    if isinstance(spawn, list):
        spawn = tuple(spawn)

    return BallConfig(
        count=data.get("count", 1),
        speed=data.get("speed", 150.0),
        radius=data.get("radius", 20.0),
        spawn=spawn,
        ai=data.get("ai", "dumb")
    )


def _parse_gap(data: Dict) -> GapConfig:
    """Parse single gap from YAML data."""
    return GapConfig(
        edge=data.get("edge", "top"),
        range=tuple(data.get("range", [0.3, 0.5]))
    )


def _parse_edges(data: Dict) -> EdgeConfig:
    """Parse edge configuration from YAML data."""
    if not data:
        return EdgeConfig()

    gaps = [_parse_gap(g) for g in data.get("gaps", [])]

    return EdgeConfig(
        mode=data.get("mode", "bounce"),
        gaps=gaps
    )


def _parse_spinner_config(data: Dict) -> SpinnerConfig:
    """Parse single spinner from YAML data (environment spinner)."""
    shape = data.get("shape", "triangle")
    if shape == "random":
        shape = random.choice(["triangle", "square", "pentagon", "hexagon"])

    return SpinnerConfig(
        position=tuple(data.get("position", [0.5, 0.5])),
        shape=shape,
        size=data.get("size", 60.0),
        rotation_speed=data.get("rotation_speed", 45.0)
    )


def _parse_environment(data: Dict) -> Environment:
    """Parse environment configuration from YAML data."""
    if not data:
        return Environment()

    spinners = [_parse_spinner_config(s) for s in data.get("spinners", [])]

    return Environment(
        edges=_parse_edges(data.get("edges", {})),
        spinners=spinners
    )


def _parse_hit_mode(data: Dict) -> HitModeConfig:
    """Parse single hit mode from YAML data."""
    return HitModeConfig(
        type=data.get("type", "deflector"),
        weight=data.get("weight", 1),
        config=data.get("config", {})
    )


def _parse_hit_modes(data: Dict) -> HitModes:
    """Parse hit modes configuration from YAML data."""
    if not data:
        # Default: random deflectors (backward compatible)
        return HitModes(
            selection="random",
            modes=[HitModeConfig(
                type="deflector",
                config={"angle": "random", "length": 60}
            )]
        )

    modes = [_parse_hit_mode(m) for m in data.get("modes", [])]

    return HitModes(
        selection=data.get("selection", "random"),
        modes=modes if modes else [HitModeConfig(
            type="deflector",
            config={"angle": "random", "length": 60}
        )]
    )


def load_level(path: Union[str, Path]) -> LevelConfig:
    """Load a level from a YAML file.

    Args:
        path: Path to the YAML file

    Returns:
        LevelConfig with all level settings

    Raises:
        FileNotFoundError: If the file doesn't exist
        yaml.YAMLError: If the YAML is invalid
    """
    path = Path(path)

    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    if not data:
        return LevelConfig()

    return LevelConfig(
        name=data.get("name", path.stem),
        description=data.get("description", ""),
        difficulty=data.get("difficulty", 1),
        author=data.get("author", "unknown"),
        version=data.get("version", 1),
        objectives=_parse_objectives(data.get("objectives", {})),
        ball=_parse_ball(data.get("ball", {})),
        environment=_parse_environment(data.get("environment", {})),
        hit_modes=_parse_hit_modes(data.get("hit_modes")),
        pacing_overrides=data.get("pacing", {})
    )


def apply_pacing_overrides(config: LevelConfig, pacing: str) -> LevelConfig:
    """Apply pacing-specific overrides to level config.

    Args:
        config: The base level configuration
        pacing: Pacing preset name (archery, throwing, blaster)

    Returns:
        Modified LevelConfig with overrides applied
    """
    if pacing not in config.pacing_overrides:
        return config

    overrides = config.pacing_overrides[pacing]

    # Apply dot-notation overrides
    for path, value in overrides.items():
        _apply_override(config, path, value)

    return config


def _apply_override(obj: Any, path: str, value: Any) -> None:
    """Apply a dot-notation override to an object.

    Supports paths like:
    - ball.speed
    - hit_modes.modes[0].config.length
    """
    parts = path.replace("]", "").replace("[", ".").split(".")

    current = obj
    for i, part in enumerate(parts[:-1]):
        if part.isdigit():
            current = current[int(part)]
        elif hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict):
            current = current[part]
        else:
            return  # Invalid path, skip

    final_part = parts[-1]
    if final_part.isdigit():
        current[int(final_part)] = value
    elif hasattr(current, final_part):
        setattr(current, final_part, value)
    elif isinstance(current, dict):
        current[final_part] = value


# =============================================================================
# Level Discovery
# =============================================================================

def get_levels_dir() -> Path:
    """Get the levels directory path."""
    return Path(__file__).parent


def list_levels(category: Optional[str] = None) -> List[Path]:
    """List available level files.

    Args:
        category: Optional subdirectory (tutorial, campaign, challenge, examples)

    Returns:
        List of paths to level YAML files
    """
    levels_dir = get_levels_dir()

    if category:
        search_dir = levels_dir / category
    else:
        search_dir = levels_dir

    if not search_dir.exists():
        return []

    levels = []
    for path in search_dir.rglob("*.yaml"):
        # Skip schema.md and other non-level files
        if path.name.startswith("_"):
            continue
        levels.append(path)

    return sorted(levels)


def get_level_info(path: Union[str, Path]) -> Dict[str, Any]:
    """Get level metadata without loading full config.

    Args:
        path: Path to level YAML file

    Returns:
        Dict with name, description, difficulty, author
    """
    path = Path(path)

    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    if not data:
        return {
            "name": path.stem,
            "description": "",
            "difficulty": 1,
            "author": "unknown"
        }

    return {
        "name": data.get("name", path.stem),
        "description": data.get("description", ""),
        "difficulty": data.get("difficulty", 1),
        "author": data.get("author", "unknown")
    }


# =============================================================================
# Hit Mode Resolution
# =============================================================================

def resolve_hit_mode_angle(config: Dict, ball_pos: Optional[Tuple[float, float]] = None,
                           hit_pos: Tuple[float, float] = (0, 0)) -> float:
    """Resolve the angle for a deflector hit mode.

    Args:
        config: Hit mode config dict
        ball_pos: Current ball position (for directional modes)
        hit_pos: Where the hit occurred

    Returns:
        Angle in radians
    """
    angle_type = config.get("angle", "random")

    if angle_type == "random":
        return random.uniform(0, math.pi)

    elif angle_type == "fixed":
        return math.radians(config.get("fixed_angle", 45))

    elif angle_type == "toward_ball" and ball_pos:
        dx = ball_pos[0] - hit_pos[0]
        dy = ball_pos[1] - hit_pos[1]
        # Perpendicular to direction toward ball
        return math.atan2(dy, dx) + math.pi / 2

    elif angle_type == "away_from_ball" and ball_pos:
        dx = ball_pos[0] - hit_pos[0]
        dy = ball_pos[1] - hit_pos[1]
        # Parallel to direction toward ball
        return math.atan2(dy, dx)

    return random.uniform(0, math.pi)


def resolve_random_value(value: Any) -> float:
    """Resolve a value that might be a range [min, max] or a single value.

    Args:
        value: Either a number or a [min, max] list

    Returns:
        Resolved float value
    """
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return random.uniform(value[0], value[1])
    return float(value) if value is not None else 0.0


def shape_name_to_sides(shape: str) -> int:
    """Convert shape name to number of sides.

    Args:
        shape: Shape name (triangle, square, pentagon, hexagon, random)

    Returns:
        Number of sides
    """
    shapes = {
        "triangle": 3,
        "square": 4,
        "pentagon": 5,
        "hexagon": 6,
    }

    if shape == "random":
        return random.choice(list(shapes.values()))

    return shapes.get(shape, 3)
