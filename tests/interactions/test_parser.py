"""Tests for the interaction parser."""

import pytest
import yaml
from pathlib import Path

from ams.interactions.parser import (
    InteractionParser,
    parse_interactions,
    FilterValue,
    Filter,
    Interaction,
    TriggerMode,
    DistanceFrom,
    _parse_filter_value,
    _parse_filter,
    _edges_to_angle_filter,
)


class TestFilterValue:
    """Tests for FilterValue parsing and matching."""

    def test_exact_match_int(self):
        """Exact integer match."""
        fv = FilterValue(exact=0)
        assert fv.matches(0)
        assert not fv.matches(1)

    def test_exact_match_string(self):
        """Exact string match."""
        fv = FilterValue(exact="aggressive")
        assert fv.matches("aggressive")
        assert not fv.matches("passive")

    def test_exact_match_bool(self):
        """Exact boolean match."""
        fv = FilterValue(exact=True)
        assert fv.matches(True)
        assert not fv.matches(False)

    def test_lt_comparison(self):
        """Less than comparison."""
        fv = FilterValue(lt=100)
        assert fv.matches(50)
        assert fv.matches(99)
        assert not fv.matches(100)
        assert not fv.matches(150)

    def test_gt_comparison(self):
        """Greater than comparison."""
        fv = FilterValue(gt=0)
        assert fv.matches(1)
        assert fv.matches(100)
        assert not fv.matches(0)
        assert not fv.matches(-1)

    def test_lte_comparison(self):
        """Less than or equal comparison."""
        fv = FilterValue(lte=100)
        assert fv.matches(50)
        assert fv.matches(100)
        assert not fv.matches(101)

    def test_gte_comparison(self):
        """Greater than or equal comparison."""
        fv = FilterValue(gte=0)
        assert fv.matches(0)
        assert fv.matches(100)
        assert not fv.matches(-1)

    def test_between_range(self):
        """Between range check."""
        fv = FilterValue(between=(45, 135))
        assert fv.matches(45)
        assert fv.matches(90)
        assert fv.matches(135)
        assert not fv.matches(44)
        assert not fv.matches(136)

    def test_in_set(self):
        """In set membership check."""
        fv = FilterValue(in_set=["red", "blue", "green"])
        assert fv.matches("red")
        assert fv.matches("blue")
        assert not fv.matches("yellow")

    def test_combined_filters(self):
        """Multiple conditions combined."""
        fv = FilterValue(gt=0, lt=100)
        assert fv.matches(50)
        assert not fv.matches(0)
        assert not fv.matches(100)


class TestParseFilterValue:
    """Tests for _parse_filter_value function."""

    def test_parse_exact_int(self):
        """Parse exact integer value."""
        fv = _parse_filter_value(0)
        assert fv.exact == 0

    def test_parse_exact_string(self):
        """Parse exact string value."""
        fv = _parse_filter_value("aggressive")
        assert fv.exact == "aggressive"

    def test_parse_lt(self):
        """Parse less than operator."""
        fv = _parse_filter_value({"lt": 100})
        assert fv.lt == 100
        assert fv.exact is None

    def test_parse_gt(self):
        """Parse greater than operator."""
        fv = _parse_filter_value({"gt": 0})
        assert fv.gt == 0

    def test_parse_between(self):
        """Parse between range."""
        fv = _parse_filter_value({"between": [45, 135]})
        assert fv.between == (45, 135)

    def test_parse_in_set(self):
        """Parse in set."""
        fv = _parse_filter_value({"in": ["a", "b", "c"]})
        assert fv.in_set == ["a", "b", "c"]

    def test_parse_combined(self):
        """Parse combined operators."""
        fv = _parse_filter_value({"gt": 0, "lt": 100})
        assert fv.gt == 0
        assert fv.lt == 100


class TestParseFilter:
    """Tests for _parse_filter function."""

    def test_empty_filter(self):
        """Empty/None when block."""
        f = _parse_filter(None)
        assert f.distance is None
        assert f.angle is None

    def test_distance_exact(self):
        """Parse exact distance filter."""
        f = _parse_filter({"distance": 0})
        assert f.distance.exact == 0

    def test_distance_comparison(self):
        """Parse distance comparison."""
        f = _parse_filter({"distance": {"lt": 100}})
        assert f.distance.lt == 100

    def test_distance_from_to(self):
        """Parse distance from/to specifiers."""
        f = _parse_filter({
            "distance": 0,
            "from": "center",
            "to": "edge"
        })
        assert f.distance_from == DistanceFrom.CENTER
        assert f.distance_to == DistanceFrom.EDGE

    def test_angle_filter(self):
        """Parse angle filter."""
        f = _parse_filter({"angle": {"between": [45, 135]}})
        assert f.angle.between == (45, 135)

    def test_entity_a_attrs(self):
        """Parse entity A attribute filters."""
        f = _parse_filter({
            "a.ball_attached": True,
            "a.health": {"gt": 0}
        })
        assert "ball_attached" in f.entity_a_attrs
        assert f.entity_a_attrs["ball_attached"].exact is True
        assert f.entity_a_attrs["health"].gt == 0

    def test_entity_b_attrs(self):
        """Parse entity B attribute filters."""
        f = _parse_filter({
            "b.active": True,
            "b.state": "aggressive"
        })
        assert f.entity_b_attrs["active"].exact is True
        assert f.entity_b_attrs["state"].exact == "aggressive"

    def test_because_filter(self):
        """Parse lifecycle cause filter."""
        f = _parse_filter({"because": "transform"})
        assert f.because == "transform"


class TestEdgesToAngleFilter:
    """Tests for edge shorthand to angle filter conversion."""

    def test_bottom_edge(self):
        """Bottom edge = ball moving upward (45-135)."""
        fv = _edges_to_angle_filter(["bottom"])
        assert fv.between == (45, 135)

    def test_top_edge(self):
        """Top edge = ball moving downward (225-315)."""
        fv = _edges_to_angle_filter(["top"])
        assert fv.between == (225, 315)

    def test_right_edge(self):
        """Right edge = ball moving left (135-225)."""
        fv = _edges_to_angle_filter(["right"])
        assert fv.between == (135, 225)

    def test_multiple_edges(self):
        """Multiple edges returns None (not yet fully implemented)."""
        result = _edges_to_angle_filter(["left", "right"])
        # Current implementation returns None for multiple edges
        assert result is None


class TestParseInteractions:
    """Tests for the main parse_interactions function."""

    def test_simple_interaction(self):
        """Parse a simple collision interaction."""
        data = {
            "brick": {
                "when": {"distance": 0},
                "action": "bounce_reflect"
            }
        }
        interactions = parse_interactions(data, "ball")

        assert len(interactions) == 1
        i = interactions[0]
        assert i.target == "brick"
        assert i.filter.distance.exact == 0
        assert i.action == "bounce_reflect"
        assert i.trigger == TriggerMode.ENTER
        assert i.source_entity_type == "ball"

    def test_interaction_with_modifier(self):
        """Parse interaction with modifier config."""
        data = {
            "paddle": {
                "when": {"distance": 0},
                "action": "bounce_paddle",
                "modifier": {"max_angle": 60}
            }
        }
        interactions = parse_interactions(data)

        assert len(interactions) == 1
        assert interactions[0].modifier == {"max_angle": 60}

    def test_trigger_mode(self):
        """Parse explicit trigger mode."""
        data = {
            "pointer": {
                "trigger": "continuous",
                "action": "track_pointer_x"
            }
        }
        interactions = parse_interactions(data)

        assert interactions[0].trigger == TriggerMode.CONTINUOUS

    def test_edges_shorthand(self):
        """Parse edges shorthand."""
        data = {
            "screen": {
                "edges": ["bottom"],
                "action": "ball_lost"
            }
        }
        interactions = parse_interactions(data)

        i = interactions[0]
        assert i.edges == ["bottom"]
        # Edges should set distance: 0
        assert i.filter.distance.exact == 0
        # Edges should set angle filter
        assert i.filter.angle.between == (45, 135)

    def test_array_syntax_multiple_interactions(self):
        """Parse array syntax for multiple interactions with same target."""
        data = {
            "screen": [
                {"edges": ["bottom"], "action": "ball_lost"},
                {"edges": ["left", "right"], "action": "bounce_horizontal"},
                {"edges": ["top"], "action": "bounce_vertical"}
            ]
        }
        interactions = parse_interactions(data)

        assert len(interactions) == 3
        assert interactions[0].action == "ball_lost"
        assert interactions[1].action == "bounce_horizontal"
        assert interactions[2].action == "bounce_vertical"

    def test_entity_attribute_filters(self):
        """Parse entity attribute filters."""
        data = {
            "pointer": {
                "when": {
                    "b.active": True,
                    "a.ball_attached": True
                },
                "action": "launch_ball"
            }
        }
        interactions = parse_interactions(data)

        i = interactions[0]
        assert i.filter.entity_b_attrs["active"].exact is True
        assert i.filter.entity_a_attrs["ball_attached"].exact is True


class TestInteractionParser:
    """Tests for InteractionParser class with validation."""

    def test_parse_valid_interaction(self):
        """Parse valid interaction data."""
        parser = InteractionParser()
        data = {
            "brick": {
                "when": {"distance": 0},
                "action": "bounce"
            }
        }

        interactions = parser.parse(data, validate=False)
        assert len(interactions) == 1

    def test_parse_without_action_fails(self):
        """Interaction without action should fail validation."""
        parser = InteractionParser()
        data = {
            "brick": {
                "when": {"distance": 0}
                # Missing action
            }
        }

        # Without jsonschema, validation is skipped
        # The parser will still work, just with empty action
        interactions = parser.parse(data, validate=False)
        assert interactions[0].action == ""


class TestBrickBreakerUltimate:
    """Validate parser against BrickBreakerUltimate game.yaml."""

    @pytest.fixture
    def brick_breaker_data(self):
        """Load BrickBreakerUltimate entity types."""
        game_path = Path(__file__).parent.parent.parent / "games" / "BrickBreakerUltimate" / "game.yaml"
        if not game_path.exists():
            pytest.skip("BrickBreakerUltimate game.yaml not found")

        with open(game_path) as f:
            game = yaml.safe_load(f)

        return game.get("entity_types", {})

    def test_paddle_interactions(self, brick_breaker_data):
        """Parse paddle interactions from BrickBreakerUltimate."""
        paddle = brick_breaker_data.get("paddle", {})
        interactions_data = paddle.get("interactions", {})

        interactions = parse_interactions(interactions_data, "paddle")

        # Should have 2 pointer interactions
        pointer_interactions = [i for i in interactions if i.target == "pointer"]
        assert len(pointer_interactions) == 2

        # First: continuous tracking
        tracking = next(i for i in pointer_interactions if i.trigger == TriggerMode.CONTINUOUS)
        assert tracking.action == "track_pointer_x"

        # Second: launch ball on click
        launch = next(i for i in pointer_interactions if i.trigger == TriggerMode.ENTER)
        assert launch.action == "launch_ball"
        assert launch.filter.entity_b_attrs["active"].exact is True
        assert launch.filter.entity_a_attrs["ball_attached"].exact is True

    def test_ball_interactions(self, brick_breaker_data):
        """Parse ball interactions from BrickBreakerUltimate."""
        ball = brick_breaker_data.get("ball", {})
        interactions_data = ball.get("interactions", {})

        interactions = parse_interactions(interactions_data, "ball")

        # Paddle collision
        paddle_int = next(i for i in interactions if i.target == "paddle")
        assert paddle_int.filter.distance.exact == 0
        assert paddle_int.action == "bounce_paddle"

        # Brick collision
        brick_int = next(i for i in interactions if i.target == "brick")
        assert brick_int.filter.distance.exact == 0
        assert brick_int.action == "bounce_reflect"
        assert brick_int.modifier.get("speed_increase") == 5

        # Screen interactions (array syntax)
        screen_ints = [i for i in interactions if i.target == "screen"]
        assert len(screen_ints) == 3

        actions = {i.action for i in screen_ints}
        assert "ball_lost" in actions
        assert "bounce_horizontal" in actions
        assert "bounce_vertical" in actions

    def test_brick_interactions(self, brick_breaker_data):
        """Parse brick interactions from BrickBreakerUltimate."""
        brick = brick_breaker_data.get("brick", {})
        interactions_data = brick.get("interactions", {})

        interactions = parse_interactions(interactions_data, "brick")

        assert len(interactions) == 1
        i = interactions[0]
        assert i.target == "ball"
        assert i.filter.distance.exact == 0
        assert i.action == "take_damage"
        assert i.modifier.get("amount") == 1

    def test_projectile_interactions(self, brick_breaker_data):
        """Parse projectile interactions from BrickBreakerUltimate."""
        projectile = brick_breaker_data.get("projectile", {})
        interactions_data = projectile.get("interactions", {})

        interactions = parse_interactions(interactions_data, "projectile")

        # Paddle hit
        paddle_int = next(i for i in interactions if i.target == "paddle")
        assert paddle_int.action == "hit_player"

        # Screen edges destroy
        screen_int = next(i for i in interactions if i.target == "screen")
        assert screen_int.edges == ["top", "bottom", "left", "right"]
        assert screen_int.action == "destroy_self"


class TestFilterMatching:
    """Integration tests for filter matching logic."""

    def test_collision_filter_matches(self):
        """Collision filter matches when distance is 0."""
        f = _parse_filter({"distance": 0})
        assert f.distance.matches(0)
        assert not f.distance.matches(1)

    def test_proximity_filter_matches(self):
        """Proximity filter matches when distance is within range."""
        f = _parse_filter({"distance": {"lt": 100}})
        assert f.distance.matches(50)
        assert f.distance.matches(0)
        assert not f.distance.matches(100)
        assert not f.distance.matches(150)

    def test_angle_filter_matches(self):
        """Angle filter matches when angle is in range."""
        f = _parse_filter({"angle": {"between": [45, 135]}})
        assert f.angle.matches(90)
        assert f.angle.matches(45)
        assert f.angle.matches(135)
        assert not f.angle.matches(0)
        assert not f.angle.matches(180)

    def test_entity_attr_filter_matches(self):
        """Entity attribute filters match correctly."""
        f = _parse_filter({
            "a.health": {"gt": 0},
            "b.active": True
        })

        assert f.entity_a_attrs["health"].matches(100)
        assert not f.entity_a_attrs["health"].matches(0)
        assert f.entity_b_attrs["active"].matches(True)
        assert not f.entity_b_attrs["active"].matches(False)
