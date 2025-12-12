"""
Snapshot dataclasses for rollback state management.

These immutable snapshots capture the complete game state at a point in time,
enabling restoration and re-simulation for handling delayed hit detection.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import copy


@dataclass(frozen=True)
class ScheduledCallbackSnapshot:
    """Snapshot of a scheduled callback."""
    time_remaining: float
    callback_name: str
    entity_id: str


@dataclass
class EntitySnapshot:
    """
    Complete snapshot of a single entity's state.

    All fields needed to restore an entity to this exact state.
    Properties dict is deep-copied to avoid shared mutable state.
    """
    # Identity
    id: str
    entity_type: str
    alive: bool

    # Transform
    x: float
    y: float
    vx: float
    vy: float
    width: float
    height: float

    # Visual
    color: str
    sprite: str
    visible: bool

    # Game state
    health: int
    spawn_time: float

    # Tags
    tags: Tuple[str, ...]  # Immutable tuple

    # Custom properties (deep copy of dict)
    properties: Dict[str, Any] = field(default_factory=dict)

    # Hierarchy
    parent_id: Optional[str] = None
    parent_offset: Tuple[float, float] = (0.0, 0.0)
    children: Tuple[str, ...] = ()  # Immutable tuple

    # Behavior state
    behaviors: Tuple[str, ...] = ()  # Immutable tuple
    behavior_config: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_entity(cls, entity: 'GameEntity') -> 'EntitySnapshot':
        """Create snapshot from a GameEntity.

        Args:
            entity: The entity to snapshot

        Returns:
            Immutable snapshot of entity state
        """
        return cls(
            id=entity.id,
            entity_type=entity.entity_type,
            alive=entity.alive,
            x=entity.x,
            y=entity.y,
            vx=entity.vx,
            vy=entity.vy,
            width=entity.width,
            height=entity.height,
            color=entity.color,
            sprite=entity.sprite,
            visible=entity.visible,
            health=entity.health,
            spawn_time=entity.spawn_time,
            tags=tuple(entity.tags),
            properties=copy.deepcopy(entity.properties),
            parent_id=entity.parent_id,
            parent_offset=tuple(entity.parent_offset),
            children=tuple(entity.children),
            behaviors=tuple(entity.behaviors),
            behavior_config=copy.deepcopy(entity.behavior_config),
        )

    def apply_to(self, entity: 'GameEntity') -> None:
        """Apply this snapshot's state to an entity.

        Args:
            entity: The entity to restore
        """
        entity.entity_type = self.entity_type
        entity.alive = self.alive
        entity.x = self.x
        entity.y = self.y
        entity.vx = self.vx
        entity.vy = self.vy
        entity.width = self.width
        entity.height = self.height
        entity.color = self.color
        entity.sprite = self.sprite
        entity.visible = self.visible
        entity.health = self.health
        entity.spawn_time = self.spawn_time
        entity.tags = list(self.tags)
        entity.properties = copy.deepcopy(self.properties)
        entity.parent_id = self.parent_id
        entity.parent_offset = tuple(self.parent_offset)
        entity.children = list(self.children)
        entity.behaviors = list(self.behaviors)
        entity.behavior_config = copy.deepcopy(self.behavior_config)


@dataclass
class GameSnapshot:
    """
    Complete snapshot of game state at a point in time.

    Includes all entities, global state, and timing information
    needed for complete state restoration.
    """
    # Timing
    frame_number: int
    elapsed_time: float
    timestamp: float  # time.monotonic() for correlation with input events

    # All entities (keyed by entity ID)
    entities: Dict[str, EntitySnapshot] = field(default_factory=dict)

    # Game progress
    score: int = 0
    lives: int = 3

    # Internal state (as string for serialization)
    internal_state: str = "PLAYING"

    # Scheduled callbacks
    scheduled_callbacks: Tuple[ScheduledCallbackSnapshot, ...] = ()

    @property
    def entity_count(self) -> int:
        """Number of entities in snapshot."""
        return len(self.entities)

    @property
    def alive_entity_count(self) -> int:
        """Number of alive entities in snapshot."""
        return sum(1 for e in self.entities.values() if e.alive)

    def get_entity(self, entity_id: str) -> Optional[EntitySnapshot]:
        """Get entity snapshot by ID."""
        return self.entities.get(entity_id)

    def __repr__(self) -> str:
        return (
            f"GameSnapshot(frame={self.frame_number}, "
            f"time={self.elapsed_time:.3f}, "
            f"entities={self.entity_count}, "
            f"score={self.score})"
        )


# Type hint for GameEntity (avoid circular import)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ams.games.game_engine.entity import GameEntity
