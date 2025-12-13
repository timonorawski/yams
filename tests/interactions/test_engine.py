"""Tests for the InteractionEngine."""

import pytest
from typing import Any, Dict, List
from unittest.mock import Mock, MagicMock

from ams.interactions.engine import InteractionEngine, Entity
from ams.interactions.parser import TriggerMode
from ams.interactions.system_entities import InputType


class MockHandler:
    """Mock action handler that records calls."""

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []

    def execute(
        self,
        entity_a_id: str,
        entity_b_id: str,
        interaction: Dict[str, Any]
    ) -> None:
        self.calls.append({
            "entity_a_id": entity_a_id,
            "entity_b_id": entity_b_id,
            "interaction": interaction,
        })


class TestInteractionEngine:
    """Tests for InteractionEngine."""

    @pytest.fixture
    def engine(self):
        return InteractionEngine(
            screen_width=800,
            screen_height=600,
            lives=3,
            input_type=InputType.MOUSE
        )

    def test_create_engine(self, engine):
        """Create engine with default settings."""
        assert engine.system.screen.width == 800
        assert engine.system.screen.height == 600
        assert engine.system.game.lives == 3

    def test_register_entity_type(self, engine):
        """Register entity type with interactions."""
        interactions_data = {
            "brick": {
                "when": {"distance": 0},
                "action": "bounce_reflect"
            }
        }

        interactions = engine.register_entity_type("ball", interactions_data)

        assert len(interactions) == 1
        assert interactions[0].target == "brick"
        assert engine.get_interactions("ball") == interactions

    def test_register_action_handler(self, engine):
        """Register action handler."""
        handler = MockHandler()
        engine.register_action("bounce", handler)

        assert "bounce" in engine._handlers

    def test_register_multiple_handlers(self, engine):
        """Register multiple handlers at once."""
        handlers = {
            "bounce": MockHandler(),
            "damage": MockHandler(),
        }
        engine.register_actions(handlers)

        assert "bounce" in engine._handlers
        assert "damage" in engine._handlers

    def test_update_pointer(self, engine):
        """Update pointer position and state."""
        engine.update_pointer(100, 200, active=True)

        assert engine.system.pointer.x == 100
        assert engine.system.pointer.y == 200
        assert engine.system.pointer.active is True

    def test_add_entity(self, engine):
        """Add entity to tracking."""
        entity = Entity(id="ball1", entity_type="ball", x=100, y=100, width=16, height=16)
        events = engine.add_entity(entity)

        assert engine.get_entity("ball1") is entity
        assert len(events) == 1  # Spawn event
        assert events[0].event_type == "spawn"

    def test_remove_entity(self, engine):
        """Remove entity from tracking."""
        entity = Entity(id="ball1", entity_type="ball")
        engine.add_entity(entity)

        events = engine.remove_entity("ball1")

        assert engine.get_entity("ball1") is None
        assert len(events) == 1  # Destroy event
        assert events[0].event_type == "destroy"

    def test_update_entity(self, engine):
        """Update entity position and attributes."""
        entity = Entity(id="ball1", entity_type="ball", x=0, y=0)
        engine.add_entity(entity)

        engine.update_entity("ball1", x=100, y=200, attributes={"speed": 300})

        updated = engine.get_entity("ball1")
        assert updated.x == 100
        assert updated.y == 200
        assert updated.attributes["speed"] == 300


class TestEngineEvaluation:
    """Tests for engine evaluation loop."""

    @pytest.fixture
    def engine(self):
        return InteractionEngine()

    def test_evaluate_collision(self, engine):
        """Evaluate collision between two entities."""
        # Register entity type with collision
        engine.register_entity_type("ball", {
            "brick": {
                "when": {"distance": 0},
                "action": "bounce_reflect"
            }
        })

        handler = MockHandler()
        engine.register_action("bounce_reflect", handler)

        # Add overlapping entities
        ball = Entity(id="ball1", entity_type="ball", x=0, y=0, width=16, height=16)
        brick = Entity(id="brick1", entity_type="brick", x=10, y=10, width=70, height=25)
        engine.add_entity(ball)
        engine.add_entity(brick)

        # Evaluate
        events = engine.evaluate()

        assert len(events) == 1
        assert events[0].entity_a_id == "ball1"
        assert events[0].entity_b_id == "brick1"

        # Handler should have been called
        assert len(handler.calls) == 1
        assert handler.calls[0]["entity_a_id"] == "ball1"
        assert handler.calls[0]["entity_b_id"] == "brick1"

    def test_evaluate_no_collision(self, engine):
        """No events when entities don't collide."""
        engine.register_entity_type("ball", {
            "brick": {
                "when": {"distance": 0},
                "action": "bounce_reflect"
            }
        })

        # Add non-overlapping entities
        ball = Entity(id="ball1", entity_type="ball", x=0, y=0, width=16, height=16)
        brick = Entity(id="brick1", entity_type="brick", x=100, y=100, width=70, height=25)
        engine.add_entity(ball)
        engine.add_entity(brick)

        events = engine.evaluate()
        assert len(events) == 0

    def test_evaluate_pointer_interaction(self, engine):
        """Evaluate interaction with pointer system entity."""
        engine.register_entity_type("duck", {
            "pointer": {
                "when": {
                    "distance": 0,
                    "b.active": True
                },
                "action": "hit_duck"
            }
        })

        handler = MockHandler()
        engine.register_action("hit_duck", handler)

        # Add duck entity
        duck = Entity(id="duck1", entity_type="duck", x=100, y=100, width=50, height=50)
        engine.add_entity(duck)

        # Click on duck
        engine.update_pointer(125, 125, active=True)

        events = engine.evaluate()

        assert len(events) == 1
        assert events[0].entity_a_id == "duck1"
        assert events[0].entity_b_id == "pointer"
        assert len(handler.calls) == 1

    def test_evaluate_continuous_trigger(self, engine):
        """Continuous trigger fires every frame."""
        engine.register_entity_type("paddle", {
            "pointer": {
                "because": "continuous",
                "action": "track_pointer"
            }
        })

        handler = MockHandler()
        engine.register_action("track_pointer", handler)

        paddle = Entity(id="paddle1", entity_type="paddle", x=0, y=0, width=120, height=15)
        engine.add_entity(paddle)
        engine.update_pointer(60, 7)

        # Frame 1
        engine.evaluate()
        # Frame 2
        engine.evaluate()
        # Frame 3
        engine.evaluate()

        # Handler called every frame (3 times)
        assert len(handler.calls) == 3

    def test_evaluate_enter_trigger_once(self, engine):
        """Enter trigger fires only once."""
        engine.register_entity_type("ball", {
            "brick": {
                "when": {"distance": 0},
                "because": "enter",
                "action": "bounce"
            }
        })

        handler = MockHandler()
        engine.register_action("bounce", handler)

        ball = Entity(id="ball1", entity_type="ball", x=0, y=0, width=16, height=16)
        brick = Entity(id="brick1", entity_type="brick", x=10, y=10, width=70, height=25)
        engine.add_entity(ball)
        engine.add_entity(brick)

        # Frame 1: Collision starts
        engine.evaluate()
        # Frame 2: Still colliding
        engine.evaluate()
        # Frame 3: Still colliding
        engine.evaluate()

        # Handler called only once (on enter)
        assert len(handler.calls) == 1

    def test_entity_doesnt_interact_with_self(self, engine):
        """Entities don't interact with themselves."""
        engine.register_entity_type("ball", {
            "ball": {  # Ball-ball interaction
                "when": {"distance": 0},
                "action": "bounce_balls"
            }
        })

        handler = MockHandler()
        engine.register_action("bounce_balls", handler)

        # Single ball
        ball = Entity(id="ball1", entity_type="ball", x=0, y=0, width=16, height=16)
        engine.add_entity(ball)

        events = engine.evaluate()

        # No self-interaction
        assert len(events) == 0

    def test_evaluate_updates_time(self, engine):
        """Evaluate updates system time."""
        initial_time = engine.system.time.absolute
        engine.evaluate(dt=1.0)

        assert engine.system.time.absolute == initial_time + 1.0


class TestEngineLifecycle:
    """Tests for lifecycle handling."""

    @pytest.fixture
    def engine(self):
        return InteractionEngine()

    def test_lifecycle_spawn(self, engine):
        """Lifecycle spawn triggers level enter interaction."""
        engine.register_entity_type("ball", {
            "level": {
                "because": "enter",
                "action": "initialize_ball"
            }
        })

        handler = MockHandler()
        engine.register_action("initialize_ball", handler)

        events = engine.handle_lifecycle("ball1", "ball", "spawn")

        assert len(events) == 1
        assert events[0].trigger_type == TriggerMode.ENTER
        assert len(handler.calls) == 1

    def test_lifecycle_update(self, engine):
        """Lifecycle update triggers level continuous interaction."""
        engine.register_entity_type("ball", {
            "level": {
                "because": "continuous",
                "action": "apply_physics"
            }
        })

        handler = MockHandler()
        engine.register_action("apply_physics", handler)

        engine.handle_lifecycle("ball1", "ball", "update")
        engine.handle_lifecycle("ball1", "ball", "update")

        assert len(handler.calls) == 2

    def test_lifecycle_destroy(self, engine):
        """Lifecycle destroy triggers level exit interaction."""
        engine.register_entity_type("ball", {
            "level": {
                "because": "exit",
                "action": "spawn_particles"
            }
        })

        handler = MockHandler()
        engine.register_action("spawn_particles", handler)

        events = engine.handle_lifecycle("ball1", "ball", "destroy")

        assert len(events) == 1
        assert events[0].trigger_type == TriggerMode.EXIT
        assert len(handler.calls) == 1

    def test_lifecycle_with_because_filter(self, engine):
        """Because filter limits lifecycle triggers."""
        engine.register_entity_type("paddle", {
            "level": {
                "because": "exit",
                "when": {"because": "transform"},
                "action": "transform_cleanup"
            }
        })

        handler = MockHandler()
        engine.register_action("transform_cleanup", handler)

        # Regular destroy - doesn't match
        events = engine.handle_lifecycle("paddle1", "paddle", "destroy", cause="destroy")
        assert len(events) == 0

        # Transform destroy - matches
        events = engine.handle_lifecycle("paddle2", "paddle", "destroy", cause="transform")
        assert len(events) == 1


class TestEngineReset:
    """Tests for engine reset."""

    def test_reset_clears_state(self):
        """Reset clears all state."""
        engine = InteractionEngine()

        # Add some state
        engine.register_entity_type("ball", {"brick": {"action": "bounce"}})
        ball = Entity(id="ball1", entity_type="ball")
        engine.add_entity(ball)
        engine.system.game.add_score(1000)
        engine.system.game.lose_life()

        # Reset
        engine.reset()

        # State cleared
        assert engine.get_entity("ball1") is None
        assert engine.system.game.score == 0
        assert engine.system.game.lives == 3  # Back to initial


class TestBrickBreakerScenario:
    """Integration test with BrickBreaker-like game."""

    def test_brickbreaker_interactions(self):
        """Test full BrickBreaker interaction flow."""
        engine = InteractionEngine(screen_width=800, screen_height=600, lives=3)

        # Register entity types
        engine.register_entity_type("ball", {
            "paddle": {
                "when": {"distance": 0},
                "action": "bounce_paddle"
            },
            "brick": {
                "when": {"distance": 0},
                "action": "bounce_reflect"
            }
        })

        engine.register_entity_type("brick", {
            "ball": {
                "when": {"distance": 0},
                "action": "take_damage"
            }
        })

        engine.register_entity_type("paddle", {
            "pointer": {
                "because": "continuous",
                "action": "track_pointer_x"
            }
        })

        # Create handlers
        bounce_handler = MockHandler()
        damage_handler = MockHandler()
        track_handler = MockHandler()

        engine.register_action("bounce_paddle", bounce_handler)
        engine.register_action("bounce_reflect", bounce_handler)
        engine.register_action("take_damage", damage_handler)
        engine.register_action("track_pointer_x", track_handler)

        # Add entities
        paddle = Entity(id="paddle1", entity_type="paddle", x=340, y=550, width=120, height=15)
        ball = Entity(id="ball1", entity_type="ball", x=395, y=540, width=16, height=16)  # Overlapping paddle
        brick = Entity(id="brick1", entity_type="brick", x=65, y=60, width=70, height=25)

        engine.add_entity(paddle)
        engine.add_entity(ball)
        engine.add_entity(brick)

        # Update pointer (inside paddle bounds for continuous trigger)
        engine.update_pointer(400, 555)

        # Evaluate
        events = engine.evaluate()

        # Paddle should track pointer (continuous)
        assert len(track_handler.calls) == 1

        # Ball overlapping paddle - collision
        assert len(bounce_handler.calls) == 1

        # Move ball to hit brick
        engine.update_entity("ball1", x=65, y=70)
        events = engine.evaluate()

        # Ball-brick collision triggers both bounce and damage
        assert len(bounce_handler.calls) == 2
        assert len(damage_handler.calls) == 1
