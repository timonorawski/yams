"""
Interaction Engine - Main orchestrator for the unified interaction system.

The InteractionEngine:
1. Parses and stores interactions from entity type definitions
2. Manages system entities (pointer, screen, level, game, time)
3. Evaluates interactions each frame
4. Tracks trigger states for enter/exit/continuous modes
5. Dispatches actions to handlers
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Set
import yaml

from .parser import Interaction, parse_interactions, TriggerMode, Filter
from .filter import FilterEvaluator, InteractionContext, evaluate_filter
from .trigger import TriggerManager, TriggerEvent, LifecycleManager, LifecycleEvent
from .system_entities import SystemEntities, InputType


@dataclass
class MonotonicConfig:
    """Configuration for monotonic (fire-and-forget) interactions."""
    all_monotonic: bool = False  # All attributes are monotonic
    monotonic_attrs: Set[str] = field(default_factory=set)  # Specific monotonic attrs

    def is_monotonic(self, filter_obj: Filter) -> bool:
        """Check if a filter only uses monotonic conditions."""
        if self.all_monotonic:
            return True
        # Would need to check which b.* attrs are used
        # For now, if we have specific attrs listed, assume filter uses them
        return len(self.monotonic_attrs) > 0


class MonotonicRegistry:
    """
    Registry of system entities with monotonic conditions.

    Monotonic conditions only increase/trigger once, so interactions
    using only these conditions can be unbound after firing.
    """

    def __init__(self):
        self._configs: Dict[str, MonotonicConfig] = {}

    @classmethod
    def load_from_yaml(cls, path: Optional[Path] = None) -> "MonotonicRegistry":
        """Load registry from system_entities.yaml."""
        registry = cls()

        if path is None:
            path = Path(__file__).parent / "system_entities.yaml"

        if not path.exists():
            return registry

        with open(path) as f:
            data = yaml.safe_load(f)

        for entity_name, config in data.items():
            if not isinstance(config, dict):
                continue

            monotonic = config.get("monotonic")
            if monotonic is True:
                registry._configs[entity_name] = MonotonicConfig(all_monotonic=True)
            elif isinstance(monotonic, list):
                registry._configs[entity_name] = MonotonicConfig(
                    monotonic_attrs=set(monotonic)
                )

        return registry

    def can_unbind_after_fire(self, interaction: Interaction) -> bool:
        """
        Check if interaction can be unbound after firing.

        Returns True if:
        - Target is monotonic (time, game.score, etc.)
        - Trigger is 'enter' (fires once)
        - No entity A attribute filters (those can change)
        """
        if interaction.trigger != TriggerMode.ENTER:
            return False

        # Entity A attributes can change, can't unbind
        if interaction.filter.entity_a_attrs:
            return False

        config = self._configs.get(interaction.target)
        if not config:
            return False

        return config.is_monotonic(interaction.filter)


class ActionHandler(Protocol):
    """Protocol for action handlers."""

    def execute(
        self,
        entity_a_id: str,
        entity_b_id: str,
        interaction: Dict[str, Any]
    ) -> None:
        """
        Execute an action.

        Args:
            entity_a_id: Source entity ID
            entity_b_id: Target entity ID
            interaction: Interaction context dict containing:
                - distance: Computed distance
                - angle: Computed angle
                - trigger: Trigger mode that fired
                - modifier: Action configuration
                - a: Entity A attributes
                - b: Entity B attributes
        """
        ...


@dataclass
class Entity:
    """
    Representation of a game entity for the interaction system.

    The engine stores a minimal view of entities needed for interaction
    evaluation (bounds and attributes).
    """
    id: str
    entity_type: str
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for filter evaluation."""
        return {
            "id": self.id,
            "type": self.entity_type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            **self.attributes,
        }


class InteractionEngine:
    """
    Main engine for evaluating entity interactions.

    Usage:
        engine = InteractionEngine()

        # Register entity types with their interactions
        engine.register_entity_type("ball", ball_interactions)
        engine.register_entity_type("paddle", paddle_interactions)

        # Register action handlers
        engine.register_action("bounce_reflect", bounce_handler)
        engine.register_action("take_damage", damage_handler)

        # Each frame:
        engine.update_pointer(x, y, active)
        events = engine.evaluate(entities, dt)
        # Events are automatically dispatched to handlers
    """

    def __init__(
        self,
        screen_width: float = 800,
        screen_height: float = 600,
        lives: int = 3,
        input_type: InputType = InputType.MOUSE
    ):
        # System entities
        self.system = SystemEntities.create(
            screen_width=screen_width,
            screen_height=screen_height,
            lives=lives,
            input_type=input_type,
        )

        # Interactions by entity type
        self._interactions: Dict[str, List[Interaction]] = {}

        # Fired monotonic interactions per entity (unbound, zero cost)
        # Key: (entity_id, interaction_key), restored on transform
        self._fired_monotonic: Set[tuple] = set()

        # Monotonic condition registry
        self._monotonic = MonotonicRegistry.load_from_yaml()

        # Action handlers
        self._handlers: Dict[str, ActionHandler] = {}

        # Fallback handler for unregistered actions
        self._default_handler: Optional[ActionHandler] = None

        # Filter evaluator
        self._filter = FilterEvaluator()

        # Trigger state manager
        self._triggers = TriggerManager()

        # Lifecycle manager
        self._lifecycle = LifecycleManager()

        # Currently tracked entities
        self._entities: Dict[str, Entity] = {}

    def register_entity_type(
        self,
        entity_type: str,
        interactions_data: Dict[str, Any]
    ) -> List[Interaction]:
        """
        Register an entity type with its interactions.

        Args:
            entity_type: Name of the entity type (e.g., "ball")
            interactions_data: The 'interactions' dict from entity type definition

        Returns:
            List of parsed Interaction objects
        """
        interactions = parse_interactions(interactions_data, entity_type)
        self._interactions[entity_type] = interactions
        return interactions

    def get_interactions(self, entity_type: str) -> List[Interaction]:
        """Get interactions for an entity type."""
        return self._interactions.get(entity_type, [])

    def register_action(
        self,
        action_name: str,
        handler: ActionHandler
    ) -> None:
        """Register a handler for an action."""
        self._handlers[action_name] = handler

    def register_actions(
        self,
        handlers: Dict[str, ActionHandler]
    ) -> None:
        """Register multiple action handlers."""
        self._handlers.update(handlers)

    def set_default_handler(self, handler: ActionHandler) -> None:
        """Set fallback handler for unregistered actions."""
        self._default_handler = handler

    def update_pointer(
        self,
        x: float,
        y: float,
        active: bool = False,
        width: Optional[float] = None,
        height: Optional[float] = None
    ) -> None:
        """Update pointer position and state."""
        self.system.pointer.update(x, y, active)
        if width is not None and height is not None:
            self.system.pointer.set_bounds(width, height)

    def add_entity(self, entity: Entity) -> List[LifecycleEvent]:
        """
        Add an entity to tracking.

        Returns spawn lifecycle events.
        """
        self._entities[entity.id] = entity
        return self._lifecycle.on_spawn(entity.id)

    def remove_entity(self, entity_id: str) -> List[LifecycleEvent]:
        """
        Remove an entity from tracking.

        Returns destroy lifecycle events.
        """
        self._triggers.clear_entity(entity_id)
        self._clear_fired_monotonic(entity_id)
        if entity_id in self._entities:
            del self._entities[entity_id]
        return self._lifecycle.on_destroy(entity_id)

    def _clear_fired_monotonic(self, entity_id: str) -> None:
        """Clear fired monotonic interactions for an entity (on destroy/transform)."""
        to_remove = [key for key in self._fired_monotonic if key[0] == entity_id]
        for key in to_remove:
            self._fired_monotonic.discard(key)

    def transform_entity(self, entity_id: str, new_type: str) -> None:
        """
        Transform entity to new type.

        Clears all interaction state, re-registering interactions from new type.
        Transform to same type = reset all timers/interactions.
        """
        if entity_id in self._entities:
            self._entities[entity_id].entity_type = new_type
            self._triggers.clear_entity(entity_id)
            self._clear_fired_monotonic(entity_id)

    def update_entity(
        self,
        entity_id: str,
        x: float,
        y: float,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update entity position and attributes."""
        if entity_id in self._entities:
            entity = self._entities[entity_id]
            entity.x = x
            entity.y = y
            if attributes:
                entity.attributes.update(attributes)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self._entities.get(entity_id)

    def evaluate(self, dt: float = 0.016) -> List[TriggerEvent]:
        """
        Evaluate all interactions for the current frame.

        Args:
            dt: Delta time since last frame

        Returns:
            List of trigger events that fired
        """
        # Update time-based system entities
        self.system.update(dt)

        all_events: List[TriggerEvent] = []

        # Get entities by type for efficient lookup
        entities_by_type: Dict[str, List[Entity]] = {}
        for entity in self._entities.values():
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity)

        # Evaluate each entity's interactions
        for entity in self._entities.values():
            interactions = self._interactions.get(entity.entity_type, [])

            for interaction in interactions:
                events = self._evaluate_interaction(
                    entity,
                    interaction,
                    entities_by_type,
                )
                all_events.extend(events)

        # Dispatch events to handlers
        for event in all_events:
            self._dispatch(event)

        return all_events

    def _get_interaction_key(self, interaction: Interaction) -> str:
        """Get stable key for an interaction."""
        return f"{interaction.source_entity_type}:{interaction.target}:{interaction.action}"

    def _evaluate_interaction(
        self,
        entity_a: Entity,
        interaction: Interaction,
        entities_by_type: Dict[str, List[Entity]]
    ) -> List[TriggerEvent]:
        """Evaluate a single interaction for an entity."""
        # Skip if this monotonic interaction already fired for this entity
        int_key = self._get_interaction_key(interaction)
        if (entity_a.id, int_key) in self._fired_monotonic:
            return []

        events: List[TriggerEvent] = []
        target = interaction.target

        # Get target entities
        if self.system.is_system_entity(target):
            # System entity target
            target_dict = self.system.get_entity_dict(target)
            if target_dict:
                events.extend(self._check_pair(
                    entity_a,
                    target,
                    target_dict,
                    interaction,
                ))
        else:
            # Game entity targets
            targets = entities_by_type.get(target, [])
            for entity_b in targets:
                if entity_b.id != entity_a.id:  # Don't interact with self
                    events.extend(self._check_pair(
                        entity_a,
                        entity_b.id,
                        entity_b.to_dict(),
                        interaction,
                    ))

        # If events fired and interaction is monotonic, unbind it
        if events and self._monotonic.can_unbind_after_fire(interaction):
            self._fired_monotonic.add((entity_a.id, int_key))

        return events

    def _check_pair(
        self,
        entity_a: Entity,
        entity_b_id: str,
        entity_b_dict: Dict[str, Any],
        interaction: Interaction
    ) -> List[TriggerEvent]:
        """Check a single entity pair against an interaction filter."""
        entity_a_dict = entity_a.to_dict()

        # Evaluate filter
        matches, context = evaluate_filter(
            interaction.filter,
            entity_a_dict,
            entity_b_dict,
        )

        # Build context dict for trigger manager
        context_dict = {}
        if context:
            context_dict = {
                "distance": context.distance,
                "angle": context.angle,
                "a": entity_a_dict,
                "b": entity_b_dict,
            }

        # Update trigger state and get events
        return self._triggers.update(
            interaction,
            entity_a.id,
            entity_b_id,
            matches,
            context_dict,
        )

    def _dispatch(self, event: TriggerEvent) -> None:
        """Dispatch a trigger event to its action handler."""
        action = event.interaction.action
        handler = self._handlers.get(action, self._default_handler)

        if handler:
            # Build interaction dict for handler
            interaction_dict = {
                **event.context,
                "trigger": event.trigger_type.value,
                "modifier": event.interaction.modifier,
                "action": action,
                "target": event.interaction.target,
            }

            handler.execute(
                event.entity_a_id,
                event.entity_b_id,
                interaction_dict,
            )

    def handle_lifecycle(
        self,
        entity_id: str,
        entity_type: str,
        event_type: str,
        cause: Optional[str] = None
    ) -> List[TriggerEvent]:
        """
        Handle lifecycle events as level interactions.

        Args:
            entity_id: The entity
            entity_type: Entity type for looking up interactions
            event_type: "spawn", "update", or "destroy"
            cause: Optional cause ("transform", etc.)

        Returns:
            List of trigger events for lifecycle interactions
        """
        events: List[TriggerEvent] = []

        # Get level interactions for this entity type
        interactions = self._interactions.get(entity_type, [])
        level_interactions = [i for i in interactions if i.target == "level"]

        for interaction in level_interactions:
            # Check if trigger mode matches event type
            if event_type == "spawn" and interaction.trigger == TriggerMode.ENTER:
                # Check because filter if present
                if interaction.filter.because and cause != interaction.filter.because:
                    continue

                events.append(TriggerEvent(
                    interaction=interaction,
                    entity_a_id=entity_id,
                    entity_b_id="level",
                    trigger_type=TriggerMode.ENTER,
                    context={"cause": cause or "spawn"},
                ))

            elif event_type == "update" and interaction.trigger == TriggerMode.CONTINUOUS:
                events.append(TriggerEvent(
                    interaction=interaction,
                    entity_a_id=entity_id,
                    entity_b_id="level",
                    trigger_type=TriggerMode.CONTINUOUS,
                    context={},
                ))

            elif event_type == "destroy" and interaction.trigger == TriggerMode.EXIT:
                # Check because filter if present
                if interaction.filter.because and cause != interaction.filter.because:
                    continue

                events.append(TriggerEvent(
                    interaction=interaction,
                    entity_a_id=entity_id,
                    entity_b_id="level",
                    trigger_type=TriggerMode.EXIT,
                    context={"cause": cause or "destroy"},
                ))

        # Dispatch lifecycle events
        for event in events:
            self._dispatch(event)

        return events

    def reset(self) -> None:
        """Reset engine state (e.g., for new level)."""
        self._triggers.reset()
        self._lifecycle.clear()
        self._entities.clear()
        self._fired_monotonic.clear()
        self.system.game.reset()
        self.system.time.reset_absolute()
        self.system.level.reset()
