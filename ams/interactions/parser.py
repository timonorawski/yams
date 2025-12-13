"""
Interaction parser - validates and parses interaction definitions.

Converts YAML interaction definitions into structured Interaction objects
that can be evaluated by the InteractionEngine.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json


class TriggerMode(Enum):
    """When the interaction handler fires."""
    ENTER = "enter"       # Once when filter becomes true
    EXIT = "exit"         # Once when filter becomes false
    CONTINUOUS = "continuous"  # Every frame while true


class DistanceFrom(Enum):
    """Where to measure distance from."""
    EDGE = "edge"
    CENTER = "center"


@dataclass
class FilterValue:
    """
    A filter value - either exact match or comparison.

    Examples:
        FilterValue(exact=0)           # distance: 0
        FilterValue(lt=100)            # distance: {lt: 100}
        FilterValue(between=[45, 135]) # angle: {between: [45, 135]}
    """
    exact: Optional[Any] = None
    lt: Optional[float] = None
    gt: Optional[float] = None
    lte: Optional[float] = None
    gte: Optional[float] = None
    between: Optional[tuple] = None
    in_set: Optional[list] = None

    def matches(self, value: Any) -> bool:
        """Check if a value matches this filter."""
        if self.exact is not None:
            return value == self.exact
        if self.lt is not None and not (value < self.lt):
            return False
        if self.gt is not None and not (value > self.gt):
            return False
        if self.lte is not None and not (value <= self.lte):
            return False
        if self.gte is not None and not (value >= self.gte):
            return False
        if self.between is not None:
            if not (self.between[0] <= value <= self.between[1]):
                return False
        if self.in_set is not None:
            if value not in self.in_set:
                return False
        return True


@dataclass
class Filter:
    """
    Filter conditions for an interaction.

    Attributes:
        distance: Distance filter (0 = collision)
        distance_from: Measure from edge or center of A
        distance_to: Measure to edge or center of B
        angle: Angle filter (direction from A to B)
        entity_a_attrs: Filters on entity A attributes (a.*)
        entity_b_attrs: Filters on entity B attributes (b.*)
        because: Lifecycle trigger cause filter
    """
    distance: Optional[FilterValue] = None
    distance_from: DistanceFrom = DistanceFrom.EDGE
    distance_to: DistanceFrom = DistanceFrom.EDGE
    angle: Optional[FilterValue] = None
    entity_a_attrs: Dict[str, FilterValue] = field(default_factory=dict)
    entity_b_attrs: Dict[str, FilterValue] = field(default_factory=dict)
    because: Optional[str] = None


@dataclass
class Interaction:
    """
    A parsed interaction definition.

    Attributes:
        target: Target entity type (e.g., "brick", "pointer", "screen")
        filter: Conditions for when this interaction fires
        trigger: When to fire (enter, exit, continuous)
        edges: Screen edge shorthand (expands to angle filter)
        action: Action name to execute
        modifier: Configuration passed to the action
    """
    target: str
    filter: Filter
    trigger: TriggerMode
    edges: Optional[List[str]]
    action: str
    modifier: Dict[str, Any]

    # Source info for error messages
    source_entity_type: str = ""


def _parse_filter_value(value: Any) -> FilterValue:
    """Parse a filter value from YAML."""
    if isinstance(value, dict):
        return FilterValue(
            lt=value.get('lt'),
            gt=value.get('gt'),
            lte=value.get('lte'),
            gte=value.get('gte'),
            between=tuple(value['between']) if 'between' in value else None,
            in_set=value.get('in'),
        )
    else:
        return FilterValue(exact=value)


def _parse_filter(when: Optional[Dict[str, Any]]) -> Filter:
    """Parse a filter from YAML 'when' block."""
    if when is None:
        return Filter()

    f = Filter()

    # Distance
    if 'distance' in when:
        f.distance = _parse_filter_value(when['distance'])

    # Distance measurement
    if 'from' in when:
        f.distance_from = DistanceFrom(when['from'])
    if 'to' in when:
        f.distance_to = DistanceFrom(when['to'])

    # Angle
    if 'angle' in when:
        f.angle = _parse_filter_value(when['angle'])

    # Lifecycle cause
    if 'because' in when:
        f.because = when['because']

    # Entity attributes (a.* and b.*)
    for key, value in when.items():
        if key.startswith('a.'):
            attr_name = key[2:]
            f.entity_a_attrs[attr_name] = _parse_filter_value(value)
        elif key.startswith('b.'):
            attr_name = key[2:]
            f.entity_b_attrs[attr_name] = _parse_filter_value(value)

    return f


def _edges_to_angle_filter(edges: List[str]) -> FilterValue:
    """
    Convert edge names to angle filter.

    Angle convention: 0=right, 90=up, 180=left, 270=down
    Edge angles (incoming direction):
    - top: ball coming from above, angle ~270 (down)
    - bottom: ball coming from below, angle ~90 (up)
    - left: ball coming from left, angle ~0 (right)
    - right: ball coming from right, angle ~180 (left)
    """
    # Build list of angle ranges
    ranges = []
    for edge in edges:
        if edge == 'top':
            ranges.append((225, 315))  # Coming from above
        elif edge == 'bottom':
            ranges.append((45, 135))   # Coming from below
        elif edge == 'left':
            ranges.append((315, 360))  # Coming from left (wraps)
            ranges.append((0, 45))
        elif edge == 'right':
            ranges.append((135, 225))  # Coming from right

    # For now, return the first range (TODO: handle multiple ranges)
    if len(ranges) == 1:
        return FilterValue(between=ranges[0])
    elif len(ranges) > 1:
        # Multiple edges - can't easily express as single filter
        # For now, return None and handle specially
        return None

    return None


def _parse_interaction(target: str, data: Dict[str, Any], source_entity: str) -> Interaction:
    """Parse a single interaction from YAML."""
    # Parse filter
    filter_obj = _parse_filter(data.get('when'))

    # Parse trigger mode (YAML key is 'because' for readability)
    trigger_str = data.get('because', 'enter')
    trigger = TriggerMode(trigger_str)

    # Parse edges shorthand
    edges = data.get('edges')
    if edges:
        # Expand edges to angle filter if not already set
        if filter_obj.angle is None:
            filter_obj.angle = _edges_to_angle_filter(edges)
        # Also set distance: 0 for edge interactions
        if filter_obj.distance is None:
            filter_obj.distance = FilterValue(exact=0)

    # Action and modifier
    action = data.get('action', '')
    modifier = data.get('modifier', {})

    return Interaction(
        target=target,
        filter=filter_obj,
        trigger=trigger,
        edges=edges,
        action=action,
        modifier=modifier,
        source_entity_type=source_entity,
    )


def parse_interactions(
    interactions_data: Dict[str, Any],
    source_entity_type: str = ""
) -> List[Interaction]:
    """
    Parse interactions from YAML data.

    Args:
        interactions_data: The 'interactions' dict from an entity type
        source_entity_type: Name of the entity type (for error messages)

    Returns:
        List of Interaction objects
    """
    result = []

    for target, data in interactions_data.items():
        # Handle array syntax (multiple interactions with same target)
        if isinstance(data, list):
            for item in data:
                result.append(_parse_interaction(target, item, source_entity_type))
        else:
            result.append(_parse_interaction(target, data, source_entity_type))

    return result


class InteractionParser:
    """
    Parser for interaction definitions with schema validation.
    """

    def __init__(self):
        self._schema = None
        self._validator = None

    def _load_schema(self):
        """Load the JSON schema for validation."""
        if self._schema is not None:
            return

        schema_path = Path(__file__).parent / 'schemas' / 'interaction.schema.json'
        if schema_path.exists():
            with open(schema_path) as f:
                self._schema = json.load(f)

            # Try to create validator if jsonschema is available
            try:
                import jsonschema
                self._validator = jsonschema.Draft7Validator(self._schema)
            except ImportError:
                pass

    def validate(self, interactions_data: Dict[str, Any]) -> List[str]:
        """
        Validate interactions data against schema.

        Returns list of error messages (empty if valid).
        """
        self._load_schema()

        if self._validator is None:
            return []  # Can't validate without jsonschema

        errors = []
        for error in self._validator.iter_errors(interactions_data):
            path = '.'.join(str(p) for p in error.absolute_path)
            errors.append(f"{path}: {error.message}")

        return errors

    def parse(
        self,
        interactions_data: Dict[str, Any],
        source_entity_type: str = "",
        validate: bool = True
    ) -> List[Interaction]:
        """
        Parse and optionally validate interactions data.

        Args:
            interactions_data: The 'interactions' dict
            source_entity_type: Entity type name for error messages
            validate: Whether to validate against schema first

        Returns:
            List of Interaction objects

        Raises:
            ValueError: If validation fails
        """
        if validate:
            errors = self.validate(interactions_data)
            if errors:
                raise ValueError(f"Invalid interactions: {'; '.join(errors)}")

        return parse_interactions(interactions_data, source_entity_type)
