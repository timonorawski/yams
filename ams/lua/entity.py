"""
Entity - abstract base class for objects that Lua scripts operate on.

The Entity ABC defines the minimal contract for LuaEngine:
- Identity (id, entity_type)
- Lifecycle state (alive)
- Custom properties for script state

Concrete implementations (e.g., GameEntity) add domain-specific attributes
like position, velocity, visuals, subroutine attachments, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Entity(ABC):
    """Abstract base for Lua-scriptable entities.

    Subclasses must implement domain-specific attributes and methods.
    This ABC provides only the minimal contract for LuaEngine.
    """

    # Identity
    id: str
    entity_type: str

    # Lifecycle (needed by LuaEngine for scheduled callbacks)
    alive: bool = True

    # Custom properties (scripts can read/write arbitrary state)
    properties: dict[str, Any] = field(default_factory=dict)

    @property
    @abstractmethod
    def renderable(self) -> bool:
        """Whether this entity should be rendered."""
        ...
