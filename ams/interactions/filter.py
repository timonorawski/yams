"""
Filter evaluation for the unified interaction system.

Evaluates interaction filters against entity pairs, computing
distance, angle, and checking entity attribute conditions.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from .parser import Filter, FilterValue, DistanceFrom


@dataclass
class EntityBounds:
    """
    Entity bounds for distance/angle calculations.

    Attributes:
        x: Left edge x position
        y: Top edge y position
        width: Width
        height: Height
    """
    x: float
    y: float
    width: float
    height: float

    @property
    def center_x(self) -> float:
        """Center x coordinate."""
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        """Center y coordinate."""
        return self.y + self.height / 2

    @property
    def right(self) -> float:
        """Right edge x coordinate."""
        return self.x + self.width

    @property
    def bottom(self) -> float:
        """Bottom edge y coordinate."""
        return self.y + self.height

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityBounds":
        """Create from entity dict."""
        return cls(
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 0),
            height=data.get("height", 0),
        )


def compute_distance_edge_to_edge(a: EntityBounds, b: EntityBounds) -> float:
    """
    Compute minimum distance between two axis-aligned bounding boxes.

    Returns 0 if boxes overlap, otherwise the minimum edge-to-edge distance.
    """
    # Horizontal gap
    if a.right < b.x:
        dx = b.x - a.right
    elif b.right < a.x:
        dx = a.x - b.right
    else:
        dx = 0  # Overlapping horizontally

    # Vertical gap
    if a.bottom < b.y:
        dy = b.y - a.bottom
    elif b.bottom < a.y:
        dy = a.y - b.bottom
    else:
        dy = 0  # Overlapping vertically

    if dx == 0 and dy == 0:
        return 0  # Boxes overlap

    return math.sqrt(dx * dx + dy * dy)


def compute_distance_center_to_center(a: EntityBounds, b: EntityBounds) -> float:
    """Compute distance between entity centers."""
    dx = b.center_x - a.center_x
    dy = b.center_y - a.center_y
    return math.sqrt(dx * dx + dy * dy)


def compute_distance_center_to_edge(a: EntityBounds, b: EntityBounds) -> float:
    """
    Compute distance from A's center to B's nearest edge.

    Used for radial effects (explosion center to enemy edge).
    """
    # Find nearest point on B's edge to A's center
    nearest_x = max(b.x, min(a.center_x, b.right))
    nearest_y = max(b.y, min(a.center_y, b.bottom))

    dx = nearest_x - a.center_x
    dy = nearest_y - a.center_y
    return math.sqrt(dx * dx + dy * dy)


def compute_distance(
    a: EntityBounds,
    b: EntityBounds,
    from_mode: DistanceFrom = DistanceFrom.EDGE,
    to_mode: DistanceFrom = DistanceFrom.EDGE
) -> float:
    """
    Compute distance between entities based on mode.

    Args:
        a: Entity A bounds
        b: Entity B bounds
        from_mode: Measure from A's edge or center
        to_mode: Measure to B's edge or center

    Returns:
        Distance value (0 = collision for edge-to-edge)
    """
    if from_mode == DistanceFrom.EDGE and to_mode == DistanceFrom.EDGE:
        return compute_distance_edge_to_edge(a, b)
    elif from_mode == DistanceFrom.CENTER and to_mode == DistanceFrom.CENTER:
        return compute_distance_center_to_center(a, b)
    elif from_mode == DistanceFrom.CENTER and to_mode == DistanceFrom.EDGE:
        return compute_distance_center_to_edge(a, b)
    elif from_mode == DistanceFrom.EDGE and to_mode == DistanceFrom.CENTER:
        # Reverse: distance from B's center to A's edge
        return compute_distance_center_to_edge(b, a)

    # Default to edge-to-edge
    return compute_distance_edge_to_edge(a, b)


def compute_angle(a: EntityBounds, b: EntityBounds) -> float:
    """
    Compute angle from A to B in degrees.

    Convention:
    - 0 = right
    - 90 = up
    - 180 = left
    - 270 = down

    Uses standard math convention (counterclockwise from positive x-axis),
    but with Y inverted for screen coordinates.
    """
    dx = b.center_x - a.center_x
    # Negate dy because screen Y increases downward
    dy = -(b.center_y - a.center_y)

    angle = math.degrees(math.atan2(dy, dx))

    # Normalize to [0, 360)
    if angle < 0:
        angle += 360

    return angle


@dataclass
class InteractionContext:
    """
    Context for a single interaction evaluation.

    Contains computed values and entity attributes needed for filtering.
    """
    distance: float
    angle: float
    entity_a: Dict[str, Any]
    entity_b: Dict[str, Any]

    # Bounds for reference
    bounds_a: EntityBounds
    bounds_b: EntityBounds


class FilterEvaluator:
    """
    Evaluates interaction filters against entity pairs.

    Usage:
        evaluator = FilterEvaluator()
        context = evaluator.compute_context(entity_a, entity_b, filter_obj)
        if evaluator.evaluate(filter_obj, context):
            # Fire interaction
    """

    def compute_context(
        self,
        entity_a: Dict[str, Any],
        entity_b: Dict[str, Any],
        filter_obj: Filter
    ) -> InteractionContext:
        """
        Compute interaction context for an entity pair.

        Args:
            entity_a: Entity A attributes (must include x, y, width, height)
            entity_b: Entity B attributes
            filter_obj: Filter with distance mode settings

        Returns:
            InteractionContext with computed distance and angle
        """
        bounds_a = EntityBounds.from_dict(entity_a)
        bounds_b = EntityBounds.from_dict(entity_b)

        distance = compute_distance(
            bounds_a,
            bounds_b,
            filter_obj.distance_from,
            filter_obj.distance_to
        )

        angle = compute_angle(bounds_a, bounds_b)

        return InteractionContext(
            distance=distance,
            angle=angle,
            entity_a=entity_a,
            entity_b=entity_b,
            bounds_a=bounds_a,
            bounds_b=bounds_b,
        )

    def evaluate(self, filter_obj: Filter, context: InteractionContext) -> bool:
        """
        Evaluate filter against context.

        Returns True if all filter conditions match.
        """
        # Distance filter
        if filter_obj.distance is not None:
            if not filter_obj.distance.matches(context.distance):
                return False

        # Angle filter
        if filter_obj.angle is not None:
            if not filter_obj.angle.matches(context.angle):
                return False

        # Entity A attributes (a.*)
        for attr_name, filter_value in filter_obj.entity_a_attrs.items():
            value = context.entity_a.get(attr_name)
            if not filter_value.matches(value):
                return False

        # Entity B attributes (b.*)
        for attr_name, filter_value in filter_obj.entity_b_attrs.items():
            value = context.entity_b.get(attr_name)
            if not filter_value.matches(value):
                return False

        # Lifecycle cause (handled at trigger level, skip here)
        # filter_obj.because is checked by TriggerManager

        return True

    def evaluate_pair(
        self,
        entity_a: Dict[str, Any],
        entity_b: Dict[str, Any],
        filter_obj: Filter
    ) -> Tuple[bool, Optional[InteractionContext]]:
        """
        Convenience method to compute context and evaluate in one call.

        Returns (matches, context) tuple.
        Context is None if filter doesn't match.
        """
        context = self.compute_context(entity_a, entity_b, filter_obj)
        matches = self.evaluate(filter_obj, context)
        return matches, context if matches else None


# Module-level instance for convenience
_default_evaluator = FilterEvaluator()


def evaluate_filter(
    filter_obj: Filter,
    entity_a: Dict[str, Any],
    entity_b: Dict[str, Any]
) -> Tuple[bool, Optional[InteractionContext]]:
    """
    Evaluate filter against entity pair.

    Convenience function using default evaluator.

    Returns:
        (matches, context) tuple. Context is None if filter doesn't match.
    """
    return _default_evaluator.evaluate_pair(entity_a, entity_b, filter_obj)
