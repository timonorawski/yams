"""
System entities for the unified interaction system.

System entities are virtual entities provided by the engine that can
participate in interactions like any game entity.

System entities:
- pointer: Input position + bounds + active state
- screen: Play area bounds
- level: Implicit lifecycle entity (spawn/update/destroy)
- game: Game state (lives, score, state)
- time: Timing for timer-based interactions
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class InputType(Enum):
    """Input device type - affects pointer bounds."""
    MOUSE = "mouse"       # Point-like (1x1)
    TOUCH = "touch"       # Finger-sized (~40x40)
    OBJECT = "object"     # Detected object size (varies)
    LASER = "laser"       # Laser spot (~10x10)


class GameState(Enum):
    """Game state values."""
    PLAYING = "playing"
    PAUSED = "paused"
    WON = "won"
    LOST = "lost"


@dataclass
class PointerEntity:
    """
    The pointer entity represents the current input position.

    Unlike a simple point, pointer has bounds that vary by input type.
    This allows the same distance calculation as entity-entity interactions.

    Attributes:
        x: Center x position
        y: Center y position
        width: Pointer width (varies by input_type)
        height: Pointer height (varies by input_type)
        active: True during click/tap/hit event
        input_type: Type of input device
    """
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    active: bool = False
    input_type: InputType = InputType.MOUSE
    source: str = "system"

    # Default sizes by input type
    DEFAULT_SIZES = {
        InputType.MOUSE: (1, 1),
        InputType.TOUCH: (40, 40),
        InputType.OBJECT: (20, 20),
        InputType.LASER: (10, 10),
    }

    @classmethod
    def create(cls, input_type: InputType = InputType.MOUSE) -> "PointerEntity":
        """Create pointer with default size for input type."""
        width, height = cls.DEFAULT_SIZES.get(input_type, (1, 1))
        return cls(
            width=width,
            height=height,
            input_type=input_type
        )

    def update(self, x: float, y: float, active: bool = False) -> None:
        """Update pointer position and active state."""
        self.x = x
        self.y = y
        self.active = active

    def set_bounds(self, width: float, height: float) -> None:
        """Set custom pointer bounds (e.g., for object detection)."""
        self.width = width
        self.height = height

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for interaction context."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "active": self.active,
            "input_type": self.input_type.value,
            "source": self.source,
        }


@dataclass
class ScreenEntity:
    """
    The screen entity represents the play area bounds.

    Used for edge detection interactions (ball hitting walls, etc.).
    Edge detection uses the computed interaction angle.

    Attributes:
        x: Left edge (usually 0)
        y: Top edge (usually 0)
        width: Screen width
        height: Screen height
    """
    x: float = 0.0
    y: float = 0.0
    width: float = 800.0
    height: float = 600.0
    source: str = "system"

    @classmethod
    def create(cls, width: float, height: float) -> "ScreenEntity":
        """Create screen entity with given dimensions."""
        return cls(width=width, height=height)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for interaction context."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "source": self.source,
        }


@dataclass
class LevelEntity:
    """
    The level entity represents the game world for lifecycle interactions.

    This is an implicit entity - it doesn't have position/bounds.
    Interactions with level represent lifecycle events:
    - trigger: enter = on_spawn
    - trigger: continuous = on_update
    - trigger: exit = on_destroy

    Attributes:
        name: Level name/identifier
        time: Time since level start (seconds)
    """
    name: str = ""
    time: float = 0.0
    source: str = "system"

    def update(self, dt: float) -> None:
        """Update level time."""
        self.time += dt

    def reset(self, name: str = "") -> None:
        """Reset level state."""
        self.name = name
        self.time = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for interaction context."""
        return {
            "name": self.name,
            "time": self.time,
            "source": self.source,
        }


@dataclass
class GameEntity:
    """
    The game entity represents overall game state.

    System-level actions (lose life, add score) modify this entity.

    Attributes:
        lives: Remaining lives
        score: Current score
        state: Game state (playing, paused, won, lost)
    """
    lives: int = 3
    score: int = 0
    state: GameState = GameState.PLAYING
    source: str = "system"

    # For tracking changes
    _initial_lives: int = field(default=3, repr=False)

    @classmethod
    def create(cls, lives: int = 3) -> "GameEntity":
        """Create game entity with starting lives."""
        return cls(lives=lives, _initial_lives=lives)

    def lose_life(self) -> int:
        """Decrement lives, return remaining."""
        self.lives = max(0, self.lives - 1)
        if self.lives == 0:
            self.state = GameState.LOST
        return self.lives

    def add_score(self, points: int) -> int:
        """Add to score, return new total."""
        self.score += points
        return self.score

    def win(self) -> None:
        """Set game to won state."""
        self.state = GameState.WON

    def lose(self) -> None:
        """Set game to lost state."""
        self.state = GameState.LOST

    def pause(self) -> None:
        """Pause the game."""
        if self.state == GameState.PLAYING:
            self.state = GameState.PAUSED

    def resume(self) -> None:
        """Resume the game."""
        if self.state == GameState.PAUSED:
            self.state = GameState.PLAYING

    def reset(self) -> None:
        """Reset game to initial state."""
        self.lives = self._initial_lives
        self.score = 0
        self.state = GameState.PLAYING

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for interaction context."""
        return {
            "lives": self.lives,
            "score": self.score,
            "state": self.state.value,
            "source": self.source,
        }


@dataclass
class TimeEntity:
    """
    The time entity for timer-based interactions.

    Timers become interactions with time:
    - elapsed: time since entity spawn
    - absolute: game time since level start

    Used for delayed actions, scheduled spawns, etc.

    Attributes:
        elapsed: Seconds since entity spawn (per-entity)
        absolute: Seconds since level start (global)
    """
    elapsed: float = 0.0
    absolute: float = 0.0
    source: str = "system"

    def update(self, dt: float) -> None:
        """Update time values."""
        self.elapsed += dt
        self.absolute += dt

    def reset_elapsed(self) -> None:
        """Reset elapsed time (for new entity)."""
        self.elapsed = 0.0

    def reset_absolute(self) -> None:
        """Reset absolute time (for new level)."""
        self.absolute = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for interaction context."""
        return {
            "elapsed": self.elapsed,
            "absolute": self.absolute,
            "source": self.source,
        }


@dataclass
class SystemEntities:
    """
    Container for all system entities.

    This is the interface between the game engine and the interaction system.
    """
    pointer: PointerEntity = field(default_factory=PointerEntity)
    screen: ScreenEntity = field(default_factory=ScreenEntity)
    level: LevelEntity = field(default_factory=LevelEntity)
    game: GameEntity = field(default_factory=GameEntity)
    time: TimeEntity = field(default_factory=TimeEntity)

    @classmethod
    def create(
        cls,
        screen_width: float = 800,
        screen_height: float = 600,
        lives: int = 3,
        input_type: InputType = InputType.MOUSE
    ) -> "SystemEntities":
        """Create system entities with initial configuration."""
        return cls(
            pointer=PointerEntity.create(input_type),
            screen=ScreenEntity.create(screen_width, screen_height),
            level=LevelEntity(),
            game=GameEntity.create(lives),
            time=TimeEntity(),
        )

    def update(self, dt: float) -> None:
        """Update time-based system entities."""
        self.level.update(dt)
        self.time.update(dt)

    def get_entity(self, name: str) -> Optional[Any]:
        """Get system entity by name."""
        return getattr(self, name, None)

    def get_entity_dict(self, name: str) -> Optional[Dict[str, Any]]:
        """Get system entity as dict for interaction context."""
        entity = self.get_entity(name)
        if entity and hasattr(entity, "to_dict"):
            return entity.to_dict()
        return None

    def is_system_entity(self, name: str) -> bool:
        """Check if name is a system entity."""
        return name in ("pointer", "screen", "level", "game", "time")
