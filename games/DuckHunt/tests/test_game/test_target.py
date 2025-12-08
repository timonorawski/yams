"""
Comprehensive tests for Target and TargetData.

Tests cover:
- TargetData validation and computed properties
- Target class movement and hit detection
- State transitions and immutability
- Edge cases and boundary conditions
"""

import pytest
from pydantic import ValidationError
from models import TargetData, Vector2D, TargetState, Rectangle
from games.DuckHunt.game.target import Target


# ============================================================================
# TargetData Tests
# ============================================================================


class TestTargetDataValidation:
    """Test TargetData Pydantic model validation."""

    def test_valid_target_data_creation(self):
        """Test creating valid TargetData."""
        data = TargetData(
            position=Vector2D(x=100.0, y=200.0),
            velocity=Vector2D(x=50.0, y=-25.0),
            size=40.0,
            state=TargetState.ALIVE
        )

        assert data.position.x == 100.0
        assert data.position.y == 200.0
        assert data.velocity.x == 50.0
        assert data.velocity.y == -25.0
        assert data.size == 40.0
        assert data.state == TargetState.ALIVE

    def test_positive_size_validation(self):
        """Test that size must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            TargetData(
                position=Vector2D(x=100.0, y=100.0),
                velocity=Vector2D(x=0.0, y=0.0),
                size=-10.0,
                state=TargetState.ALIVE
            )
        assert "Size must be positive" in str(exc_info.value)

    def test_zero_size_validation(self):
        """Test that size cannot be zero."""
        with pytest.raises(ValidationError) as exc_info:
            TargetData(
                position=Vector2D(x=100.0, y=100.0),
                velocity=Vector2D(x=0.0, y=0.0),
                size=0.0,
                state=TargetState.ALIVE
            )
        assert "Size must be positive" in str(exc_info.value)

    def test_tiny_size_allowed(self):
        """Test that very small positive sizes are allowed."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=0.1,
            state=TargetState.ALIVE
        )
        assert data.size == 0.1

    def test_large_size_allowed(self):
        """Test that very large sizes are allowed."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=1000.0,
            state=TargetState.ALIVE
        )
        assert data.size == 1000.0

    def test_all_target_states(self):
        """Test creating TargetData with each state."""
        for state in TargetState:
            data = TargetData(
                position=Vector2D(x=100.0, y=100.0),
                velocity=Vector2D(x=0.0, y=0.0),
                size=40.0,
                state=state
            )
            assert data.state == state


class TestTargetDataProperties:
    """Test TargetData computed properties."""

    def test_is_active_when_alive(self):
        """Test is_active returns True for ALIVE state."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        assert data.is_active is True

    def test_is_active_when_hit(self):
        """Test is_active returns False for HIT state."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.HIT
        )
        assert data.is_active is False

    def test_is_active_when_escaped(self):
        """Test is_active returns False for ESCAPED state."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ESCAPED
        )
        assert data.is_active is False

    def test_is_active_when_missed(self):
        """Test is_active returns False for MISSED state."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.MISSED
        )
        assert data.is_active is False

    def test_get_bounds_centered(self):
        """Test get_bounds returns correctly centered rectangle."""
        data = TargetData(
            position=Vector2D(x=100.0, y=200.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        bounds = data.get_bounds()

        # Rectangle should be centered on position
        assert bounds.width == 40.0
        assert bounds.height == 40.0
        assert bounds.x == 80.0  # 100 - 40/2
        assert bounds.y == 180.0  # 200 - 40/2
        assert bounds.center.x == 100.0
        assert bounds.center.y == 200.0

    def test_get_bounds_with_different_sizes(self):
        """Test get_bounds with various sizes."""
        sizes = [10.0, 50.0, 100.0]
        for size in sizes:
            data = TargetData(
                position=Vector2D(x=200.0, y=300.0),
                velocity=Vector2D(x=0.0, y=0.0),
                size=size,
                state=TargetState.ALIVE
            )
            bounds = data.get_bounds()
            assert bounds.width == size
            assert bounds.height == size
            assert bounds.center.x == 200.0
            assert bounds.center.y == 300.0


class TestTargetDataImmutability:
    """Test that TargetData is immutable (frozen)."""

    def test_cannot_modify_position(self):
        """Test that position cannot be modified after creation."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )

        with pytest.raises(ValidationError):
            data.position = Vector2D(x=200.0, y=200.0)

    def test_cannot_modify_velocity(self):
        """Test that velocity cannot be modified after creation."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=50.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )

        with pytest.raises(ValidationError):
            data.velocity = Vector2D(x=100.0, y=0.0)

    def test_cannot_modify_size(self):
        """Test that size cannot be modified after creation."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )

        with pytest.raises(ValidationError):
            data.size = 50.0

    def test_cannot_modify_state(self):
        """Test that state cannot be modified after creation."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )

        with pytest.raises(ValidationError):
            data.state = TargetState.HIT


# ============================================================================
# Target Class Tests
# ============================================================================


class TestTargetCreation:
    """Test Target class initialization."""

    def test_create_target_from_data(self):
        """Test creating Target from TargetData."""
        data = TargetData(
            position=Vector2D(x=100.0, y=200.0),
            velocity=Vector2D(x=50.0, y=-25.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        assert target.data == data
        assert target.is_active is True

    def test_target_data_property(self):
        """Test that data property returns the underlying TargetData."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        assert isinstance(target.data, TargetData)
        assert target.data.position.x == 100.0


class TestTargetMovement:
    """Test Target update and movement logic."""

    def test_update_moves_target(self):
        """Test that update moves target based on velocity."""
        data = TargetData(
            position=Vector2D(x=100.0, y=200.0),
            velocity=Vector2D(x=50.0, y=-25.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Update for 1 second
        new_target = target.update(dt=1.0)

        # Position should have changed
        assert new_target.data.position.x == 150.0  # 100 + 50*1
        assert new_target.data.position.y == 175.0  # 200 + (-25)*1

        # Velocity and other properties unchanged
        assert new_target.data.velocity == data.velocity
        assert new_target.data.size == data.size
        assert new_target.data.state == data.state

    def test_update_with_small_dt(self):
        """Test update with small time delta (frame time)."""
        data = TargetData(
            position=Vector2D(x=100.0, y=200.0),
            velocity=Vector2D(x=60.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Update for typical frame time (1/60 second)
        new_target = target.update(dt=1.0/60.0)

        # Should move 1 pixel (60 pixels/sec * 1/60 sec)
        assert new_target.data.position.x == pytest.approx(101.0)
        assert new_target.data.position.y == 200.0

    def test_update_with_zero_velocity(self):
        """Test update with zero velocity (stationary target)."""
        data = TargetData(
            position=Vector2D(x=100.0, y=200.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        new_target = target.update(dt=1.0)

        # Position should not change
        assert new_target.data.position.x == 100.0
        assert new_target.data.position.y == 200.0

    def test_update_with_negative_velocity(self):
        """Test update with negative velocity."""
        data = TargetData(
            position=Vector2D(x=100.0, y=200.0),
            velocity=Vector2D(x=-50.0, y=-30.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        new_target = target.update(dt=2.0)

        assert new_target.data.position.x == 0.0  # 100 + (-50)*2
        assert new_target.data.position.y == 140.0  # 200 + (-30)*2

    def test_update_multiple_times(self):
        """Test chaining multiple updates."""
        data = TargetData(
            position=Vector2D(x=0.0, y=0.0),
            velocity=Vector2D(x=10.0, y=20.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Chain updates
        target = target.update(dt=1.0)
        target = target.update(dt=1.0)
        target = target.update(dt=1.0)

        assert target.data.position.x == 30.0
        assert target.data.position.y == 60.0


class TestTargetHitDetection:
    """Test Target hit detection logic."""

    def test_contains_point_at_center(self):
        """Test hit detection at target center."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        assert target.contains_point(Vector2D(x=100.0, y=100.0)) is True

    def test_contains_point_inside_bounds(self):
        """Test hit detection for point inside bounds."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Point slightly offset from center but still inside
        assert target.contains_point(Vector2D(x=110.0, y=110.0)) is True
        assert target.contains_point(Vector2D(x=90.0, y=90.0)) is True

    def test_contains_point_on_edge(self):
        """Test hit detection for point on edge."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Points on edge should be inside
        # Bounds are from 80 to 120 (100 +/- 20)
        assert target.contains_point(Vector2D(x=80.0, y=100.0)) is True
        assert target.contains_point(Vector2D(x=120.0, y=100.0)) is True
        assert target.contains_point(Vector2D(x=100.0, y=80.0)) is True
        assert target.contains_point(Vector2D(x=100.0, y=120.0)) is True

    def test_contains_point_outside_bounds(self):
        """Test hit detection for point outside bounds."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        assert target.contains_point(Vector2D(x=200.0, y=100.0)) is False
        assert target.contains_point(Vector2D(x=100.0, y=200.0)) is False
        assert target.contains_point(Vector2D(x=50.0, y=50.0)) is False

    def test_contains_point_just_outside(self):
        """Test hit detection for point just barely outside."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Just outside bounds (120.1 is outside 80-120 range)
        assert target.contains_point(Vector2D(x=120.1, y=100.0)) is False
        assert target.contains_point(Vector2D(x=79.9, y=100.0)) is False


class TestTargetBoundaryDetection:
    """Test Target off-screen detection logic."""

    def test_on_screen_target(self):
        """Test that target in middle of screen is not off-screen."""
        data = TargetData(
            position=Vector2D(x=400.0, y=300.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        assert target.is_off_screen(800.0, 600.0) is False

    def test_target_off_left_edge(self):
        """Test target completely off left edge of screen."""
        data = TargetData(
            position=Vector2D(x=-50.0, y=300.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Target centered at -50, size 40, so right edge at -30
        assert target.is_off_screen(800.0, 600.0) is True

    def test_target_off_right_edge(self):
        """Test target completely off right edge of screen."""
        data = TargetData(
            position=Vector2D(x=850.0, y=300.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Target centered at 850, size 40, so left edge at 830
        assert target.is_off_screen(800.0, 600.0) is True

    def test_target_off_top_edge(self):
        """Test target completely off top edge of screen."""
        data = TargetData(
            position=Vector2D(x=400.0, y=-50.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        assert target.is_off_screen(800.0, 600.0) is True

    def test_target_off_bottom_edge(self):
        """Test target completely off bottom edge of screen."""
        data = TargetData(
            position=Vector2D(x=400.0, y=650.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        assert target.is_off_screen(800.0, 600.0) is True

    def test_target_partially_on_screen_left(self):
        """Test target partially on screen (left edge)."""
        data = TargetData(
            position=Vector2D(x=15.0, y=300.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Target extends from -5 to 35, so partially on screen
        assert target.is_off_screen(800.0, 600.0) is False

    def test_target_partially_on_screen_right(self):
        """Test target partially on screen (right edge)."""
        data = TargetData(
            position=Vector2D(x=785.0, y=300.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Target extends from 765 to 805, so partially on screen
        assert target.is_off_screen(800.0, 600.0) is False

    def test_target_at_exact_edge(self):
        """Test target with edge exactly at screen boundary."""
        data = TargetData(
            position=Vector2D(x=20.0, y=300.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Left edge at exactly 0
        assert target.is_off_screen(800.0, 600.0) is False


class TestTargetStateTransitions:
    """Test Target state changes."""

    def test_set_state_to_hit(self):
        """Test changing state to HIT."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=50.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        hit_target = target.set_state(TargetState.HIT)

        assert hit_target.data.state == TargetState.HIT
        assert hit_target.is_active is False

        # Original unchanged
        assert target.data.state == TargetState.ALIVE
        assert target.is_active is True

    def test_set_state_to_escaped(self):
        """Test changing state to ESCAPED."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=50.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        escaped_target = target.set_state(TargetState.ESCAPED)

        assert escaped_target.data.state == TargetState.ESCAPED
        assert escaped_target.is_active is False

    def test_set_state_preserves_other_properties(self):
        """Test that set_state only changes state, nothing else."""
        data = TargetData(
            position=Vector2D(x=100.0, y=200.0),
            velocity=Vector2D(x=50.0, y=-25.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        new_target = target.set_state(TargetState.HIT)

        # Position, velocity, and size unchanged
        assert new_target.data.position == data.position
        assert new_target.data.velocity == data.velocity
        assert new_target.data.size == data.size


class TestTargetImmutability:
    """Test that Target updates return new instances."""

    def test_update_returns_new_instance(self):
        """Test that update returns a new Target instance."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=50.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        new_target = target.update(dt=1.0)

        assert new_target is not target
        assert new_target.data is not target.data

    def test_set_state_returns_new_instance(self):
        """Test that set_state returns a new Target instance."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=50.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        new_target = target.set_state(TargetState.HIT)

        assert new_target is not target
        assert new_target.data is not target.data

    def test_original_unchanged_after_update(self):
        """Test that original target is unchanged after update."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=50.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)
        original_position = target.data.position

        _ = target.update(dt=1.0)

        # Original should be unchanged
        assert target.data.position == original_position


class TestTargetEdgeCases:
    """Test edge cases and special scenarios."""

    def test_zero_velocity_target(self):
        """Test target with zero velocity (stationary)."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Should not move
        new_target = target.update(dt=5.0)
        assert new_target.data.position == data.position

    def test_very_small_target(self):
        """Test target with very small size."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=1.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Should still work for hit detection
        assert target.contains_point(Vector2D(x=100.0, y=100.0)) is True
        assert target.contains_point(Vector2D(x=102.0, y=100.0)) is False

    def test_very_large_target(self):
        """Test target with very large size."""
        data = TargetData(
            position=Vector2D(x=400.0, y=300.0),
            velocity=Vector2D(x=0.0, y=0.0),
            size=200.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        # Should have large hit area
        assert target.contains_point(Vector2D(x=350.0, y=300.0)) is True
        assert target.contains_point(Vector2D(x=450.0, y=300.0)) is True

    def test_target_with_high_velocity(self):
        """Test target with very high velocity."""
        data = TargetData(
            position=Vector2D(x=100.0, y=100.0),
            velocity=Vector2D(x=1000.0, y=500.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        new_target = target.update(dt=1.0)

        assert new_target.data.position.x == 1100.0
        assert new_target.data.position.y == 600.0

    def test_target_starting_off_screen(self):
        """Test target that starts off screen."""
        data = TargetData(
            position=Vector2D(x=-100.0, y=300.0),
            velocity=Vector2D(x=100.0, y=0.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        assert target.is_off_screen(800.0, 600.0) is True

        # After moving, should come on screen
        target = target.update(dt=1.5)
        assert target.is_off_screen(800.0, 600.0) is False


class TestTargetStringRepresentation:
    """Test Target and TargetData string representations."""

    def test_target_str(self):
        """Test Target __str__ method."""
        data = TargetData(
            position=Vector2D(x=100.0, y=200.0),
            velocity=Vector2D(x=50.0, y=-25.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        result = str(target)
        assert "Target" in result
        assert "TargetData" in result

    def test_target_repr(self):
        """Test Target __repr__ method."""
        data = TargetData(
            position=Vector2D(x=100.0, y=200.0),
            velocity=Vector2D(x=50.0, y=-25.0),
            size=40.0,
            state=TargetState.ALIVE
        )
        target = Target(data)

        result = repr(target)
        assert "Target" in result

    def test_target_data_str(self):
        """Test TargetData __str__ method."""
        data = TargetData(
            position=Vector2D(x=100.0, y=200.0),
            velocity=Vector2D(x=50.0, y=-25.0),
            size=40.0,
            state=TargetState.ALIVE
        )

        result = str(data)
        assert "TargetData" in result
        assert "40.0" in result or "40" in result
        assert "alive" in result
