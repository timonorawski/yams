"""
Entity - abstract base class for objects that Lua behaviors operate on.

The Entity ABC defines the minimal contract for Lua behavior attachment:
- Identity (id, entity_type)
- Custom properties for behavior state
- Behavior attachment and configuration

Concrete implementations (e.g., GameEntity) add domain-specific attributes
like position, velocity, health, visuals, etc.
"""

from abc import ABC
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Entity(ABC):
    """Abstract base for Lua-scriptable entities.

    Subclasses must implement domain-specific attributes and methods.
    This ABC provides only the behavior attachment mechanism.
    """

    # Identity
    id: str
    entity_type: str

    # Custom properties (behaviors can read/write arbitrary state)
    properties: dict[str, Any] = field(default_factory=dict)

    # Attached behavior names
    behaviors: list[str] = field(default_factory=list)

    # Behavior-specific config (from YAML)
    behavior_config: dict[str, dict[str, Any]] = field(default_factory=dict)
