"""Tests for the filter evaluator."""

import math
import pytest

from ams.interactions.filter import (
    EntityBounds,
    FilterEvaluator,
    InteractionContext,
    compute_distance,
    compute_distance_edge_to_edge,
    compute_distance_center_to_center,
    compute_distance_center_to_edge,
    compute_angle,
    evaluate_filter,
)
from ams.interactions.parser import (
    Filter,
    FilterValue,
    DistanceFrom,
    _parse_filter,
)


class TestEntityBounds:
    """Tests for EntityBounds."""

    def test_center_coordinates(self):
        """Center coordinates calculated correctly."""
        bounds = EntityBounds(x=100, y=50, width=40, height=20)
        assert bounds.center_x == 120
        assert bounds.center_y == 60

    def test_right_bottom(self):
        """Right and bottom edges calculated correctly."""
        bounds = EntityBounds(x=100, y=50, width=40, height=20)
        assert bounds.right == 140
        assert bounds.bottom == 70

    def test_from_dict(self):
        """Create from entity dict."""
        entity = {"x": 10, "y": 20, "width": 30, "height": 40}
        bounds = EntityBounds.from_dict(entity)

        assert bounds.x == 10
        assert bounds.y == 20
        assert bounds.width == 30
        assert bounds.height == 40

    def test_from_dict_defaults(self):
        """Missing keys default to 0."""
        bounds = EntityBounds.from_dict({})
        assert bounds.x == 0
        assert bounds.y == 0
        assert bounds.width == 0
        assert bounds.height == 0


class TestDistanceEdgeToEdge:
    """Tests for edge-to-edge distance calculation."""

    def test_overlapping_boxes(self):
        """Overlapping boxes have distance 0."""
        a = EntityBounds(x=0, y=0, width=50, height=50)
        b = EntityBounds(x=25, y=25, width=50, height=50)

        assert compute_distance_edge_to_edge(a, b) == 0

    def test_touching_boxes(self):
        """Touching boxes have distance 0."""
        a = EntityBounds(x=0, y=0, width=50, height=50)
        b = EntityBounds(x=50, y=0, width=50, height=50)

        assert compute_distance_edge_to_edge(a, b) == 0

    def test_horizontal_gap(self):
        """Boxes with horizontal gap only."""
        a = EntityBounds(x=0, y=0, width=50, height=50)
        b = EntityBounds(x=100, y=0, width=50, height=50)

        # Gap of 50 (from a.right=50 to b.x=100)
        assert compute_distance_edge_to_edge(a, b) == 50

    def test_vertical_gap(self):
        """Boxes with vertical gap only."""
        a = EntityBounds(x=0, y=0, width=50, height=50)
        b = EntityBounds(x=0, y=100, width=50, height=50)

        # Gap of 50 (from a.bottom=50 to b.y=100)
        assert compute_distance_edge_to_edge(a, b) == 50

    def test_diagonal_gap(self):
        """Boxes with diagonal gap."""
        a = EntityBounds(x=0, y=0, width=50, height=50)
        b = EntityBounds(x=80, y=80, width=50, height=50)

        # Horizontal gap: 80 - 50 = 30
        # Vertical gap: 80 - 50 = 30
        # Distance = sqrt(30^2 + 30^2) = sqrt(1800) ≈ 42.43
        expected = math.sqrt(30 * 30 + 30 * 30)
        assert compute_distance_edge_to_edge(a, b) == pytest.approx(expected)


class TestDistanceCenterToCenter:
    """Tests for center-to-center distance calculation."""

    def test_same_center(self):
        """Boxes with same center have distance 0."""
        a = EntityBounds(x=0, y=0, width=100, height=100)
        b = EntityBounds(x=25, y=25, width=50, height=50)

        assert compute_distance_center_to_center(a, b) == 0

    def test_horizontal_offset(self):
        """Boxes offset horizontally."""
        a = EntityBounds(x=0, y=0, width=50, height=50)  # center at 25, 25
        b = EntityBounds(x=50, y=0, width=50, height=50)  # center at 75, 25

        # Distance = 50 (horizontal only)
        assert compute_distance_center_to_center(a, b) == 50

    def test_diagonal_offset(self):
        """Boxes offset diagonally."""
        a = EntityBounds(x=0, y=0, width=50, height=50)  # center at 25, 25
        b = EntityBounds(x=100, y=100, width=50, height=50)  # center at 125, 125

        # Distance = sqrt(100^2 + 100^2) = sqrt(20000)
        expected = math.sqrt(100 * 100 + 100 * 100)
        assert compute_distance_center_to_center(a, b) == pytest.approx(expected)


class TestDistanceCenterToEdge:
    """Tests for center-to-edge distance calculation."""

    def test_center_inside_box(self):
        """A's center inside B returns 0."""
        a = EntityBounds(x=50, y=50, width=10, height=10)  # center at 55, 55
        b = EntityBounds(x=0, y=0, width=100, height=100)

        assert compute_distance_center_to_edge(a, b) == 0

    def test_center_outside_box(self):
        """A's center outside B returns distance to nearest edge."""
        a = EntityBounds(x=0, y=45, width=10, height=10)  # center at 5, 50
        b = EntityBounds(x=100, y=0, width=100, height=100)

        # A's center at (5, 50), B's nearest edge at (100, 50)
        # Distance = 95
        assert compute_distance_center_to_edge(a, b) == 95


class TestComputeDistance:
    """Tests for the unified compute_distance function."""

    def test_default_edge_to_edge(self):
        """Default is edge-to-edge."""
        a = EntityBounds(x=0, y=0, width=50, height=50)
        b = EntityBounds(x=100, y=0, width=50, height=50)

        assert compute_distance(a, b) == 50

    def test_center_to_center(self):
        """Center-to-center mode."""
        a = EntityBounds(x=0, y=0, width=50, height=50)
        b = EntityBounds(x=50, y=0, width=50, height=50)

        dist = compute_distance(a, b, DistanceFrom.CENTER, DistanceFrom.CENTER)
        # Centers at (25, 25) and (75, 25) = 50
        assert dist == 50

    def test_center_to_edge(self):
        """Center-to-edge mode (radial effects)."""
        a = EntityBounds(x=0, y=0, width=50, height=50)  # center at 25, 25
        b = EntityBounds(x=100, y=0, width=50, height=50)

        dist = compute_distance(a, b, DistanceFrom.CENTER, DistanceFrom.EDGE)
        # A's center at (25, 25), B's nearest edge at (100, 25) = 75
        assert dist == 75


class TestComputeAngle:
    """Tests for angle calculation."""

    def test_angle_right(self):
        """B is directly right of A = 0 degrees."""
        a = EntityBounds(x=0, y=0, width=50, height=50)
        b = EntityBounds(x=100, y=0, width=50, height=50)

        # A center: (25, 25), B center: (125, 25)
        angle = compute_angle(a, b)
        assert angle == pytest.approx(0)

    def test_angle_left(self):
        """B is directly left of A = 180 degrees."""
        a = EntityBounds(x=100, y=0, width=50, height=50)
        b = EntityBounds(x=0, y=0, width=50, height=50)

        angle = compute_angle(a, b)
        assert angle == pytest.approx(180)

    def test_angle_up(self):
        """B is directly above A = 90 degrees (screen Y inverted)."""
        a = EntityBounds(x=0, y=100, width=50, height=50)
        b = EntityBounds(x=0, y=0, width=50, height=50)

        # A center: (25, 125), B center: (25, 25)
        # B is above A in screen coords (smaller Y)
        angle = compute_angle(a, b)
        assert angle == pytest.approx(90)

    def test_angle_down(self):
        """B is directly below A = 270 degrees."""
        a = EntityBounds(x=0, y=0, width=50, height=50)
        b = EntityBounds(x=0, y=100, width=50, height=50)

        # A center: (25, 25), B center: (25, 125)
        angle = compute_angle(a, b)
        assert angle == pytest.approx(270)

    def test_angle_diagonal(self):
        """B is diagonally up-right of A = 45 degrees."""
        a = EntityBounds(x=0, y=100, width=50, height=50)
        b = EntityBounds(x=100, y=0, width=50, height=50)

        angle = compute_angle(a, b)
        assert angle == pytest.approx(45)

    def test_angle_diagonal_down_left(self):
        """B is diagonally down-left of A = 225 degrees."""
        a = EntityBounds(x=100, y=0, width=50, height=50)
        b = EntityBounds(x=0, y=100, width=50, height=50)

        angle = compute_angle(a, b)
        assert angle == pytest.approx(225)


class TestFilterEvaluator:
    """Tests for FilterEvaluator."""

    @pytest.fixture
    def evaluator(self):
        return FilterEvaluator()

    def test_compute_context(self, evaluator):
        """Compute context from entity pair."""
        entity_a = {"x": 0, "y": 0, "width": 50, "height": 50}
        entity_b = {"x": 100, "y": 0, "width": 50, "height": 50}
        filter_obj = Filter()

        ctx = evaluator.compute_context(entity_a, entity_b, filter_obj)

        assert ctx.distance == 50  # Edge-to-edge
        assert ctx.angle == pytest.approx(0)  # B is right of A
        assert ctx.entity_a is entity_a
        assert ctx.entity_b is entity_b

    def test_evaluate_collision_match(self, evaluator):
        """Collision filter matches when distance is 0."""
        filter_obj = _parse_filter({"distance": 0})
        ctx = InteractionContext(
            distance=0,
            angle=0,
            entity_a={},
            entity_b={},
            bounds_a=EntityBounds(0, 0, 0, 0),
            bounds_b=EntityBounds(0, 0, 0, 0),
        )

        assert evaluator.evaluate(filter_obj, ctx) is True

    def test_evaluate_collision_no_match(self, evaluator):
        """Collision filter doesn't match when distance > 0."""
        filter_obj = _parse_filter({"distance": 0})
        ctx = InteractionContext(
            distance=10,
            angle=0,
            entity_a={},
            entity_b={},
            bounds_a=EntityBounds(0, 0, 0, 0),
            bounds_b=EntityBounds(0, 0, 0, 0),
        )

        assert evaluator.evaluate(filter_obj, ctx) is False

    def test_evaluate_proximity_match(self, evaluator):
        """Proximity filter matches when distance < threshold."""
        filter_obj = _parse_filter({"distance": {"lt": 100}})
        ctx = InteractionContext(
            distance=50,
            angle=0,
            entity_a={},
            entity_b={},
            bounds_a=EntityBounds(0, 0, 0, 0),
            bounds_b=EntityBounds(0, 0, 0, 0),
        )

        assert evaluator.evaluate(filter_obj, ctx) is True

    def test_evaluate_angle_match(self, evaluator):
        """Angle filter matches when angle in range."""
        filter_obj = _parse_filter({"angle": {"between": [45, 135]}})
        ctx = InteractionContext(
            distance=0,
            angle=90,  # Up
            entity_a={},
            entity_b={},
            bounds_a=EntityBounds(0, 0, 0, 0),
            bounds_b=EntityBounds(0, 0, 0, 0),
        )

        assert evaluator.evaluate(filter_obj, ctx) is True

    def test_evaluate_angle_no_match(self, evaluator):
        """Angle filter doesn't match when angle outside range."""
        filter_obj = _parse_filter({"angle": {"between": [45, 135]}})
        ctx = InteractionContext(
            distance=0,
            angle=270,  # Down
            entity_a={},
            entity_b={},
            bounds_a=EntityBounds(0, 0, 0, 0),
            bounds_b=EntityBounds(0, 0, 0, 0),
        )

        assert evaluator.evaluate(filter_obj, ctx) is False

    def test_evaluate_entity_a_attr_match(self, evaluator):
        """Entity A attribute filter matches."""
        filter_obj = _parse_filter({"a.ball_attached": True})
        ctx = InteractionContext(
            distance=0,
            angle=0,
            entity_a={"ball_attached": True},
            entity_b={},
            bounds_a=EntityBounds(0, 0, 0, 0),
            bounds_b=EntityBounds(0, 0, 0, 0),
        )

        assert evaluator.evaluate(filter_obj, ctx) is True

    def test_evaluate_entity_a_attr_no_match(self, evaluator):
        """Entity A attribute filter doesn't match."""
        filter_obj = _parse_filter({"a.ball_attached": True})
        ctx = InteractionContext(
            distance=0,
            angle=0,
            entity_a={"ball_attached": False},
            entity_b={},
            bounds_a=EntityBounds(0, 0, 0, 0),
            bounds_b=EntityBounds(0, 0, 0, 0),
        )

        assert evaluator.evaluate(filter_obj, ctx) is False

    def test_evaluate_entity_b_attr_match(self, evaluator):
        """Entity B attribute filter matches."""
        filter_obj = _parse_filter({"b.active": True})
        ctx = InteractionContext(
            distance=0,
            angle=0,
            entity_a={},
            entity_b={"active": True},
            bounds_a=EntityBounds(0, 0, 0, 0),
            bounds_b=EntityBounds(0, 0, 0, 0),
        )

        assert evaluator.evaluate(filter_obj, ctx) is True

    def test_evaluate_combined_filters(self, evaluator):
        """Multiple filter conditions must all match."""
        filter_obj = _parse_filter({
            "distance": 0,
            "b.active": True,
            "a.ball_attached": True
        })
        ctx = InteractionContext(
            distance=0,
            angle=0,
            entity_a={"ball_attached": True},
            entity_b={"active": True},
            bounds_a=EntityBounds(0, 0, 0, 0),
            bounds_b=EntityBounds(0, 0, 0, 0),
        )

        assert evaluator.evaluate(filter_obj, ctx) is True

    def test_evaluate_combined_filters_partial_fail(self, evaluator):
        """If any filter condition fails, whole filter fails."""
        filter_obj = _parse_filter({
            "distance": 0,
            "b.active": True,
            "a.ball_attached": True
        })
        ctx = InteractionContext(
            distance=0,
            angle=0,
            entity_a={"ball_attached": False},  # This fails
            entity_b={"active": True},
            bounds_a=EntityBounds(0, 0, 0, 0),
            bounds_b=EntityBounds(0, 0, 0, 0),
        )

        assert evaluator.evaluate(filter_obj, ctx) is False


class TestEvaluateFilter:
    """Tests for the convenience evaluate_filter function."""

    def test_collision_detection(self):
        """Detect collision between overlapping entities."""
        filter_obj = _parse_filter({"distance": 0})

        entity_a = {"x": 0, "y": 0, "width": 50, "height": 50}
        entity_b = {"x": 25, "y": 25, "width": 50, "height": 50}

        matches, ctx = evaluate_filter(filter_obj, entity_a, entity_b)

        assert matches is True
        assert ctx is not None
        assert ctx.distance == 0

    def test_no_collision(self):
        """No collision between separate entities."""
        filter_obj = _parse_filter({"distance": 0})

        entity_a = {"x": 0, "y": 0, "width": 50, "height": 50}
        entity_b = {"x": 100, "y": 100, "width": 50, "height": 50}

        matches, ctx = evaluate_filter(filter_obj, entity_a, entity_b)

        assert matches is False
        assert ctx is None

    def test_pointer_click_detection(self):
        """Detect click on entity (pointer interaction)."""
        filter_obj = _parse_filter({
            "distance": 0,
            "b.active": True
        })

        # Entity (target)
        entity = {"x": 100, "y": 100, "width": 50, "height": 50}
        # Pointer (clicking on entity)
        pointer = {
            "x": 120,
            "y": 120,
            "width": 1,
            "height": 1,
            "active": True
        }

        matches, ctx = evaluate_filter(filter_obj, entity, pointer)

        assert matches is True

    def test_screen_edge_bottom(self):
        """Detect ball hitting bottom screen edge.

        Note: In the full system, screen interactions use the edges shorthand
        which expands to angle ranges based on ball velocity, not position.
        This test validates the angle filter evaluation works correctly.
        """
        # Angle filter for "coming from above" (ball moving down)
        filter_obj = _parse_filter({
            "distance": 0,
            "angle": {"between": [225, 315]}  # Bottom edge angle range
        })

        # Ball overlapping with target (collision), ball is above target's center
        ball = {"x": 100, "y": 80, "width": 16, "height": 16}  # Center at (108, 88)
        # Target below ball (overlapping)
        target = {"x": 100, "y": 90, "width": 16, "height": 16}  # Center at (108, 98)

        matches, ctx = evaluate_filter(filter_obj, ball, target)

        # Angle from ball to target is ~270 (down)
        assert matches is True
        assert ctx.angle == pytest.approx(270, abs=5)


class TestBrickBreakerScenarios:
    """Real-world scenarios from BrickBreakerUltimate."""

    def test_ball_paddle_collision(self):
        """Ball colliding with paddle."""
        filter_obj = _parse_filter({"distance": 0})

        ball = {"x": 395, "y": 540, "width": 16, "height": 16}
        paddle = {"x": 340, "y": 550, "width": 120, "height": 15}

        matches, ctx = evaluate_filter(filter_obj, ball, paddle)

        assert matches is True
        assert ctx.distance == 0

    def test_ball_brick_collision(self):
        """Ball colliding with brick."""
        filter_obj = _parse_filter({"distance": 0})

        ball = {"x": 100, "y": 85, "width": 16, "height": 16}
        brick = {"x": 65, "y": 60, "width": 70, "height": 25}

        matches, ctx = evaluate_filter(filter_obj, ball, brick)

        assert matches is True

    def test_paddle_click_to_launch(self):
        """Paddle click interaction to launch ball."""
        filter_obj = _parse_filter({
            "b.active": True,
            "a.ball_attached": True
        })

        paddle = {"x": 340, "y": 550, "width": 120, "height": 15, "ball_attached": True}
        pointer = {"x": 400, "y": 560, "width": 1, "height": 1, "active": True}

        matches, ctx = evaluate_filter(filter_obj, paddle, pointer)

        assert matches is True

    def test_paddle_click_ball_not_attached(self):
        """Click doesn't launch if ball not attached."""
        filter_obj = _parse_filter({
            "b.active": True,
            "a.ball_attached": True
        })

        paddle = {"x": 340, "y": 550, "width": 120, "height": 15, "ball_attached": False}
        pointer = {"x": 400, "y": 560, "width": 1, "height": 1, "active": True}

        matches, ctx = evaluate_filter(filter_obj, paddle, pointer)

        assert matches is False

    def test_proximity_trigger(self):
        """Proximity-based interaction (enemy alert)."""
        filter_obj = _parse_filter({"distance": {"lt": 100}})

        player = {"x": 100, "y": 100, "width": 32, "height": 32}
        enemy = {"x": 150, "y": 100, "width": 32, "height": 32}

        matches, ctx = evaluate_filter(filter_obj, player, enemy)

        # Distance should be ~18 (edge-to-edge)
        assert matches is True
        assert ctx.distance < 100
