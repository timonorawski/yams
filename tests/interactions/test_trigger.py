"""Tests for the trigger state manager."""

import pytest

from ams.interactions.trigger import (
    TriggerManager,
    TriggerEvent,
    LifecycleManager,
    LifecycleEvent,
)
from ams.interactions.parser import (
    Interaction,
    Filter,
    TriggerMode,
)


def make_interaction(
    target: str = "brick",
    action: str = "bounce",
    trigger: TriggerMode = TriggerMode.ENTER,
    source_entity_type: str = "ball"
) -> Interaction:
    """Create a test interaction."""
    return Interaction(
        target=target,
        filter=Filter(),
        trigger=trigger,
        edges=None,
        action=action,
        modifier={},
        source_entity_type=source_entity_type,
    )


class TestTriggerManager:
    """Tests for TriggerManager."""

    @pytest.fixture
    def manager(self):
        return TriggerManager()

    def test_enter_trigger_fires_once(self, manager):
        """Enter trigger fires once when filter becomes true."""
        interaction = make_interaction(trigger=TriggerMode.ENTER)

        # First frame: filter matches
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1
        assert events[0].trigger_type == TriggerMode.ENTER
        assert events[0].entity_a_id == "ball1"
        assert events[0].entity_b_id == "brick1"

        # Second frame: still matching, no event
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 0

    def test_enter_trigger_fires_again_after_reset(self, manager):
        """Enter trigger fires again after filter becomes false then true."""
        interaction = make_interaction(trigger=TriggerMode.ENTER)

        # First activation
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1

        # Filter becomes false
        events = manager.update(interaction, "ball1", "brick1", False)
        assert len(events) == 0

        # Filter becomes true again - fires again
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1

    def test_enter_trigger_no_fire_when_false(self, manager):
        """Enter trigger doesn't fire when filter is false."""
        interaction = make_interaction(trigger=TriggerMode.ENTER)

        events = manager.update(interaction, "ball1", "brick1", False)
        assert len(events) == 0

    def test_exit_trigger_fires_once(self, manager):
        """Exit trigger fires once when filter becomes false."""
        interaction = make_interaction(trigger=TriggerMode.EXIT)

        # First frame: filter matches
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 0

        # Second frame: filter no longer matches
        events = manager.update(interaction, "ball1", "brick1", False)
        assert len(events) == 1
        assert events[0].trigger_type == TriggerMode.EXIT

        # Third frame: still not matching, no event
        events = manager.update(interaction, "ball1", "brick1", False)
        assert len(events) == 0

    def test_exit_trigger_no_fire_initially(self, manager):
        """Exit trigger doesn't fire if filter was never true."""
        interaction = make_interaction(trigger=TriggerMode.EXIT)

        # Filter starts false
        events = manager.update(interaction, "ball1", "brick1", False)
        assert len(events) == 0

    def test_continuous_trigger_fires_every_frame(self, manager):
        """Continuous trigger fires every frame while filter is true."""
        interaction = make_interaction(trigger=TriggerMode.CONTINUOUS)

        # Frame 1
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1
        assert events[0].trigger_type == TriggerMode.CONTINUOUS

        # Frame 2
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1

        # Frame 3
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1

    def test_continuous_trigger_stops_when_false(self, manager):
        """Continuous trigger stops firing when filter becomes false."""
        interaction = make_interaction(trigger=TriggerMode.CONTINUOUS)

        # Matching
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1

        # No longer matching
        events = manager.update(interaction, "ball1", "brick1", False)
        assert len(events) == 0

    def test_multiple_entity_pairs(self, manager):
        """Different entity pairs tracked independently."""
        interaction = make_interaction(trigger=TriggerMode.ENTER)

        # Pair 1 enters
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1

        # Pair 2 enters (different pair)
        events = manager.update(interaction, "ball1", "brick2", True)
        assert len(events) == 1

        # Pair 1 stays matching, pair 2 also stays
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 0

    def test_context_passed_to_event(self, manager):
        """Context data passed through to event."""
        interaction = make_interaction(trigger=TriggerMode.ENTER)
        context = {"distance": 0, "angle": 90}

        events = manager.update(interaction, "ball1", "brick1", True, context)
        assert events[0].context == context

    def test_clear_entity(self, manager):
        """Clear all state for an entity."""
        interaction = make_interaction(trigger=TriggerMode.ENTER)

        # Ball interacts with multiple bricks
        manager.update(interaction, "ball1", "brick1", True)
        manager.update(interaction, "ball1", "brick2", True)
        manager.update(interaction, "ball2", "brick1", True)

        # Clear ball1's state
        manager.clear_entity("ball1")

        # Ball1 can re-enter brick1
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1

        # Ball2 still has state (doesn't re-fire)
        events = manager.update(interaction, "ball2", "brick1", True)
        assert len(events) == 0

    def test_clear_pair(self, manager):
        """Clear state for a specific pair."""
        interaction = make_interaction(trigger=TriggerMode.ENTER)

        manager.update(interaction, "ball1", "brick1", True)
        manager.clear_pair(interaction, "ball1", "brick1")

        # Can re-enter
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1

    def test_get_state(self, manager):
        """Get current state for a pair."""
        interaction = make_interaction(trigger=TriggerMode.ENTER)

        assert manager.get_state(interaction, "ball1", "brick1") is False

        manager.update(interaction, "ball1", "brick1", True)
        assert manager.get_state(interaction, "ball1", "brick1") is True

        manager.update(interaction, "ball1", "brick1", False)
        assert manager.get_state(interaction, "ball1", "brick1") is False

    def test_reset(self, manager):
        """Reset clears all state."""
        interaction = make_interaction(trigger=TriggerMode.ENTER)

        manager.update(interaction, "ball1", "brick1", True)
        manager.update(interaction, "ball1", "brick2", True)

        manager.reset()

        # Both pairs can re-enter
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1

        events = manager.update(interaction, "ball1", "brick2", True)
        assert len(events) == 1

    def test_get_active_pairs(self, manager):
        """Get all active pairs for an interaction."""
        interaction = make_interaction(trigger=TriggerMode.ENTER)

        manager.update(interaction, "ball1", "brick1", True)
        manager.update(interaction, "ball1", "brick2", True)
        manager.update(interaction, "ball1", "brick3", False)

        active = manager.get_active_pairs(interaction)
        assert ("ball1", "brick1") in active
        assert ("ball1", "brick2") in active
        assert ("ball1", "brick3") not in active


class TestLifecycleManager:
    """Tests for LifecycleManager."""

    @pytest.fixture
    def manager(self):
        return LifecycleManager()

    def test_spawn_fires_once(self, manager):
        """Spawn event fires once."""
        events = manager.on_spawn("entity1")
        assert len(events) == 1
        assert events[0].event_type == "spawn"
        assert events[0].entity_id == "entity1"
        assert events[0].cause == "spawn"

        # Spawning again doesn't fire
        events = manager.on_spawn("entity1")
        assert len(events) == 0

    def test_update_fires_while_exists(self, manager):
        """Update event fires every frame while entity exists."""
        manager.on_spawn("entity1")

        events = manager.on_update("entity1")
        assert len(events) == 1
        assert events[0].event_type == "update"

        events = manager.on_update("entity1")
        assert len(events) == 1

    def test_update_no_fire_for_unknown(self, manager):
        """Update doesn't fire for unknown entities."""
        events = manager.on_update("unknown")
        assert len(events) == 0

    def test_destroy_fires_once(self, manager):
        """Destroy event fires once."""
        manager.on_spawn("entity1")

        events = manager.on_destroy("entity1")
        assert len(events) == 1
        assert events[0].event_type == "destroy"
        assert events[0].cause == "destroy"

        # Can't destroy again
        events = manager.on_destroy("entity1")
        assert len(events) == 0

    def test_destroy_no_fire_for_unknown(self, manager):
        """Destroy doesn't fire for unknown entities."""
        events = manager.on_destroy("unknown")
        assert len(events) == 0

    def test_spawn_after_destroy(self, manager):
        """Entity can spawn again after destruction."""
        manager.on_spawn("entity1")
        manager.on_destroy("entity1")

        events = manager.on_spawn("entity1")
        assert len(events) == 1
        assert events[0].event_type == "spawn"

    def test_transform_no_lifecycle_by_default(self, manager):
        """Transform doesn't fire lifecycle by default."""
        manager.on_spawn("entity1")

        events = manager.on_transform("entity1")
        assert len(events) == 0

    def test_transform_with_lifecycle(self, manager):
        """Transform fires exit/enter when requested."""
        manager.on_spawn("entity1")

        events = manager.on_transform("entity1", fire_lifecycle=True)
        assert len(events) == 2
        assert events[0].event_type == "destroy"
        assert events[0].cause == "transform"
        assert events[1].event_type == "spawn"
        assert events[1].cause == "transform"

    def test_clear(self, manager):
        """Clear removes all state."""
        manager.on_spawn("entity1")
        manager.on_spawn("entity2")

        manager.clear()

        # Both can spawn again
        events = manager.on_spawn("entity1")
        assert len(events) == 1

        events = manager.on_spawn("entity2")
        assert len(events) == 1

    def test_entity_exists(self, manager):
        """Check if entity is tracked."""
        assert manager.entity_exists("entity1") is False

        manager.on_spawn("entity1")
        assert manager.entity_exists("entity1") is True

        manager.on_destroy("entity1")
        assert manager.entity_exists("entity1") is False


class TestTriggerScenarios:
    """Real-world trigger scenarios."""

    def test_ball_brick_collision_enter(self):
        """Ball-brick collision using enter trigger."""
        manager = TriggerManager()
        interaction = make_interaction(
            target="brick",
            action="bounce_reflect",
            trigger=TriggerMode.ENTER
        )

        # Frame 1: Ball enters brick
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1
        assert events[0].interaction.action == "bounce_reflect"

        # Frame 2: Still colliding (no double-bounce)
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 0

        # Frame 3: Ball exits brick
        events = manager.update(interaction, "ball1", "brick1", False)
        assert len(events) == 0

        # Frame 4: Ball re-enters same brick (shouldn't happen in practice)
        events = manager.update(interaction, "ball1", "brick1", True)
        assert len(events) == 1

    def test_paddle_pointer_continuous(self):
        """Paddle tracking pointer continuously."""
        manager = TriggerManager()
        interaction = make_interaction(
            target="pointer",
            action="track_pointer_x",
            trigger=TriggerMode.CONTINUOUS
        )

        # Every frame while pointer exists
        for _ in range(5):
            events = manager.update(interaction, "paddle1", "pointer", True)
            assert len(events) == 1
            assert events[0].interaction.action == "track_pointer_x"

    def test_proximity_alert_enter_exit(self):
        """Enemy proximity alert using enter/exit.

        In practice, both enter and exit interactions would be evaluated
        each frame. This test verifies both work correctly.
        """
        manager = TriggerManager()
        enter_interaction = make_interaction(
            target="enemy",
            action="trigger_alert",
            trigger=TriggerMode.ENTER
        )
        exit_interaction = make_interaction(
            target="enemy",
            action="clear_alert",
            trigger=TriggerMode.EXIT
        )

        # Frame 1: Player enters proximity
        # Both interactions evaluated with same filter result
        enter_events = manager.update(enter_interaction, "player", "enemy1", True)
        exit_events = manager.update(exit_interaction, "player", "enemy1", True)

        assert len(enter_events) == 1
        assert enter_events[0].interaction.action == "trigger_alert"
        assert len(exit_events) == 0  # Exit doesn't fire on entering

        # Frame 2: Player still in proximity (no events)
        enter_events = manager.update(enter_interaction, "player", "enemy1", True)
        exit_events = manager.update(exit_interaction, "player", "enemy1", True)
        assert len(enter_events) == 0
        assert len(exit_events) == 0

        # Frame 3: Player exits proximity
        enter_events = manager.update(enter_interaction, "player", "enemy1", False)
        exit_events = manager.update(exit_interaction, "player", "enemy1", False)

        assert len(enter_events) == 0  # Enter doesn't fire on exiting
        assert len(exit_events) == 1
        assert exit_events[0].interaction.action == "clear_alert"

    def test_lifecycle_spawn_update_destroy(self):
        """Entity lifecycle using level interactions."""
        lifecycle = LifecycleManager()

        # Spawn
        events = lifecycle.on_spawn("ball1")
        assert events[0].event_type == "spawn"

        # Update each frame
        for _ in range(3):
            events = lifecycle.on_update("ball1")
            assert len(events) == 1
            assert events[0].event_type == "update"

        # Destroy
        events = lifecycle.on_destroy("ball1")
        assert events[0].event_type == "destroy"

        # No more updates
        events = lifecycle.on_update("ball1")
        assert len(events) == 0

    @pytest.fixture
    def trigger_event(self):
        """Create a sample trigger event for testing."""
        interaction = make_interaction()
        return TriggerEvent(
            interaction=interaction,
            entity_a_id="ball1",
            entity_b_id="brick1",
            trigger_type=TriggerMode.ENTER,
            context={"distance": 0, "angle": 90}
        )

    def test_trigger_event_has_interaction(self, trigger_event):
        """TriggerEvent contains the interaction definition."""
        assert trigger_event.interaction.action == "bounce"
        assert trigger_event.interaction.target == "brick"

    def test_trigger_event_has_entities(self, trigger_event):
        """TriggerEvent contains entity IDs."""
        assert trigger_event.entity_a_id == "ball1"
        assert trigger_event.entity_b_id == "brick1"

    def test_trigger_event_has_context(self, trigger_event):
        """TriggerEvent contains interaction context."""
        assert trigger_event.context["distance"] == 0
        assert trigger_event.context["angle"] == 90
