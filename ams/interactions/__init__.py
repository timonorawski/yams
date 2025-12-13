"""
AMS Unified Interaction System

All entity interactions (collisions, input, screen bounds, lifecycle)
are handled through a single declarative model.

System entities:
- pointer: input position + bounds + active state
- screen: play area bounds
- level: implicit, lifecycle (spawn/update/destroy)
- game: lives, score, state
- time: timer-based interactions
"""

from .parser import InteractionParser, parse_interactions
from .system_entities import (
    SystemEntities,
    PointerEntity,
    ScreenEntity,
    LevelEntity,
    GameEntity,
    TimeEntity,
    InputType,
    GameState,
)
from .filter import (
    FilterEvaluator,
    EntityBounds,
    InteractionContext,
    evaluate_filter,
    compute_distance,
    compute_angle,
)
from .trigger import (
    TriggerManager,
    TriggerEvent,
    LifecycleManager,
    LifecycleEvent,
)
from .engine import (
    InteractionEngine,
    Entity,
    ActionHandler,
)

__all__ = [
    'InteractionParser',
    'parse_interactions',
    'SystemEntities',
    'PointerEntity',
    'ScreenEntity',
    'LevelEntity',
    'GameEntity',
    'TimeEntity',
    'InputType',
    'GameState',
    'FilterEvaluator',
    'EntityBounds',
    'InteractionContext',
    'evaluate_filter',
    'compute_distance',
    'compute_angle',
    'TriggerManager',
    'TriggerEvent',
    'LifecycleManager',
    'LifecycleEvent',
    'InteractionEngine',
    'Entity',
    'ActionHandler',
]
