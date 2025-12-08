"""
Comprehensive tests for all Pydantic models in models.py.

Tests cover:
- Validation (valid and invalid data)
- Type coercion
- Computed fields
- Immutability (frozen models)
- Edge cases
- Boundary conditions
"""

import pytest
from pydantic import ValidationError

from models import (
    Vector2D,
    Color,
    Rectangle,
    EventType,
    TargetState,
    GameState,
)


# ============================================================================
# Enum Tests
# ============================================================================


class TestEventType:
    """Test EventType enum."""

    def test_event_type_values(self):
        """Test EventType has expected values."""
        assert EventType.HIT == "hit"
        assert EventType.MISS == "miss"

    def test_event_type_membership(self):
        """Test EventType membership checks."""
        assert EventType.HIT in EventType
        assert EventType.MISS in EventType
        assert "hit" in [e.value for e in EventType]

    def test_event_type_count(self):
        """Test EventType has exactly 2 values."""
        assert len(EventType) == 2


class TestTargetState:
    """Test TargetState enum."""

    def test_target_state_values(self):
        """Test TargetState has expected values."""
        assert TargetState.ALIVE == "alive"
        assert TargetState.HIT == "hit"
        assert TargetState.MISSED == "missed"
        assert TargetState.ESCAPED == "escaped"

    def test_target_state_membership(self):
        """Test TargetState membership checks."""
        assert TargetState.ALIVE in TargetState
        assert TargetState.HIT in TargetState
        assert TargetState.MISSED in TargetState
        assert TargetState.ESCAPED in TargetState

    def test_target_state_count(self):
        """Test TargetState has exactly 4 values."""
        assert len(TargetState) == 4


class TestGameState:
    """Test GameState enum."""

    def test_game_state_values(self):
        """Test GameState has expected values."""
        assert GameState.PLAYING.value == "playing"
        assert GameState.PAUSED.value == "paused"
        assert GameState.RETRIEVAL.value == "retrieval"
        assert GameState.GAME_OVER.value == "game_over"
        assert GameState.WON.value == "won"

    def test_game_state_membership(self):
        """Test GameState membership checks."""
        assert GameState.PLAYING in GameState
        assert GameState.PAUSED in GameState
        assert GameState.RETRIEVAL in GameState
        assert GameState.GAME_OVER in GameState
        assert GameState.WON in GameState

    def test_game_state_count(self):
        """Test GameState has exactly 5 values."""
        assert len(GameState) == 5


# ============================================================================
# Vector2D Tests
# ============================================================================


class TestVector2D:
    """Test Vector2D model."""

    def test_vector2d_valid_construction(self):
        """Test creating valid Vector2D instances."""
        v = Vector2D(x=10.0, y=20.0)
        assert v.x == 10.0
        assert v.y == 20.0

    def test_vector2d_type_coercion_int_to_float(self):
        """Test integers are coerced to floats."""
        v = Vector2D(x=10, y=20)
        assert isinstance(v.x, float)
        assert isinstance(v.y, float)
        assert v.x == 10.0
        assert v.y == 20.0

    def test_vector2d_positive_coordinates(self):
        """Test positive coordinates work correctly."""
        v = Vector2D(x=100.5, y=200.7)
        assert v.x == 100.5
        assert v.y == 200.7

    def test_vector2d_negative_coordinates(self):
        """Test negative coordinates are allowed (for velocities)."""
        v = Vector2D(x=-50.0, y=-100.0)
        assert v.x == -50.0
        assert v.y == -100.0

    def test_vector2d_zero_coordinates(self):
        """Test zero coordinates work correctly."""
        v = Vector2D(x=0.0, y=0.0)
        assert v.x == 0.0
        assert v.y == 0.0

    def test_vector2d_large_values(self):
        """Test very large coordinate values."""
        v = Vector2D(x=999999.99, y=888888.88)
        assert v.x == 999999.99
        assert v.y == 888888.88

    def test_vector2d_mixed_positive_negative(self):
        """Test mixed positive and negative coordinates."""
        v1 = Vector2D(x=100.0, y=-50.0)
        assert v1.x == 100.0
        assert v1.y == -50.0

        v2 = Vector2D(x=-75.0, y=125.0)
        assert v2.x == -75.0
        assert v2.y == 125.0

    def test_vector2d_immutability(self):
        """Test Vector2D is frozen (immutable)."""
        v = Vector2D(x=10.0, y=20.0)
        with pytest.raises(ValidationError):
            v.x = 30.0

    def test_vector2d_string_representation(self):
        """Test __str__ method."""
        v = Vector2D(x=10.5, y=20.7)
        s = str(v)
        # May be called Point2D or Vector2D depending on alias
        assert "10.5" in s or "10.50" in s
        assert "20.7" in s or "20.70" in s

    def test_vector2d_invalid_type(self):
        """Test invalid types raise ValidationError."""
        with pytest.raises(ValidationError):
            Vector2D(x="not a number", y=20.0)

        with pytest.raises(ValidationError):
            Vector2D(x=10.0, y="not a number")


# ============================================================================
# Color Tests
# ============================================================================


class TestColor:
    """Test Color model."""

    def test_color_valid_construction(self):
        """Test creating valid Color instances."""
        c = Color(r=255, g=128, b=64, a=200)
        assert c.r == 255
        assert c.g == 128
        assert c.b == 64
        assert c.a == 200

    def test_color_default_alpha(self):
        """Test alpha defaults to 255 (fully opaque)."""
        c = Color(r=100, g=100, b=100)
        assert c.a == 255

    def test_color_boundary_values(self):
        """Test color components at boundary values (0 and 255)."""
        c1 = Color(r=0, g=0, b=0, a=0)
        assert c1.r == 0 and c1.g == 0 and c1.b == 0 and c1.a == 0

        c2 = Color(r=255, g=255, b=255, a=255)
        assert c2.r == 255 and c2.g == 255 and c2.b == 255 and c2.a == 255

    def test_color_out_of_range_negative(self):
        """Test negative color values raise ValidationError."""
        with pytest.raises(ValidationError):
            Color(r=-1, g=100, b=100, a=255)

        with pytest.raises(ValidationError):
            Color(r=100, g=-50, b=100, a=255)

        with pytest.raises(ValidationError):
            Color(r=100, g=100, b=-10, a=255)

        with pytest.raises(ValidationError):
            Color(r=100, g=100, b=100, a=-1)

    def test_color_out_of_range_too_large(self):
        """Test color values > 255 raise ValidationError."""
        with pytest.raises(ValidationError):
            Color(r=256, g=100, b=100, a=255)

        with pytest.raises(ValidationError):
            Color(r=100, g=300, b=100, a=255)

        with pytest.raises(ValidationError):
            Color(r=100, g=100, b=1000, a=255)

        with pytest.raises(ValidationError):
            Color(r=100, g=100, b=100, a=500)

    def test_color_as_tuple(self):
        """Test as_tuple computed field."""
        c = Color(r=255, g=128, b=64, a=200)
        t = c.as_tuple
        assert t == (255, 128, 64, 200)
        assert isinstance(t, tuple)

    def test_color_as_rgb_tuple(self):
        """Test as_rgb_tuple computed field."""
        c = Color(r=255, g=128, b=64, a=200)
        t = c.as_rgb_tuple
        assert t == (255, 128, 64)
        assert isinstance(t, tuple)
        assert len(t) == 3

    def test_color_immutability(self):
        """Test Color is frozen (immutable)."""
        c = Color(r=100, g=100, b=100, a=255)
        with pytest.raises(ValidationError):
            c.r = 200

    def test_color_string_representation(self):
        """Test __str__ method."""
        c = Color(r=255, g=128, b=64, a=200)
        s = str(c)
        assert "Color" in s
        assert "255" in s
        assert "128" in s
        assert "64" in s
        assert "200" in s

    def test_color_common_colors(self):
        """Test common color definitions."""
        red = Color(r=255, g=0, b=0, a=255)
        assert red.r == 255 and red.g == 0 and red.b == 0

        green = Color(r=0, g=255, b=0, a=255)
        assert green.r == 0 and green.g == 255 and green.b == 0

        blue = Color(r=0, g=0, b=255, a=255)
        assert blue.r == 0 and blue.g == 0 and blue.b == 255

        white = Color(r=255, g=255, b=255, a=255)
        assert white.r == 255 and white.g == 255 and white.b == 255

        black = Color(r=0, g=0, b=0, a=255)
        assert black.r == 0 and black.g == 0 and black.b == 0

    def test_color_type_coercion(self):
        """Test that Pydantic validates int types strictly (no fractional floats)."""
        # Pydantic v2 is strict: floats with fractional parts are rejected
        with pytest.raises(ValidationError):
            Color(r=255.9, g=128.1, b=64.5, a=200.7)

        # But whole number floats should be accepted
        c = Color(r=255.0, g=128.0, b=64.0, a=200.0)
        assert isinstance(c.r, int)
        assert isinstance(c.g, int)
        assert isinstance(c.b, int)
        assert isinstance(c.a, int)


# ============================================================================
# Rectangle Tests
# ============================================================================


class TestRectangle:
    """Test Rectangle model."""

    def test_rectangle_valid_construction(self):
        """Test creating valid Rectangle instances."""
        r = Rectangle(x=100.0, y=200.0, width=50.0, height=75.0)
        assert r.x == 100.0
        assert r.y == 200.0
        assert r.width == 50.0
        assert r.height == 75.0

    def test_rectangle_type_coercion(self):
        """Test integers are coerced to floats."""
        r = Rectangle(x=100, y=200, width=50, height=75)
        assert isinstance(r.x, float)
        assert isinstance(r.y, float)
        assert isinstance(r.width, float)
        assert isinstance(r.height, float)

    def test_rectangle_zero_position(self):
        """Test rectangle at origin (0, 0)."""
        r = Rectangle(x=0.0, y=0.0, width=100.0, height=100.0)
        assert r.x == 0.0
        assert r.y == 0.0

    def test_rectangle_negative_position(self):
        """Test rectangle with negative position (off-screen)."""
        r = Rectangle(x=-50.0, y=-100.0, width=100.0, height=100.0)
        assert r.x == -50.0
        assert r.y == -100.0

    def test_rectangle_zero_width_invalid(self):
        """Test width of 0 raises ValidationError."""
        with pytest.raises(ValidationError):
            Rectangle(x=0.0, y=0.0, width=0.0, height=100.0)

    def test_rectangle_zero_height_invalid(self):
        """Test height of 0 raises ValidationError."""
        with pytest.raises(ValidationError):
            Rectangle(x=0.0, y=0.0, width=100.0, height=0.0)

    def test_rectangle_negative_width_invalid(self):
        """Test negative width raises ValidationError."""
        with pytest.raises(ValidationError):
            Rectangle(x=0.0, y=0.0, width=-50.0, height=100.0)

    def test_rectangle_negative_height_invalid(self):
        """Test negative height raises ValidationError."""
        with pytest.raises(ValidationError):
            Rectangle(x=0.0, y=0.0, width=100.0, height=-75.0)

    def test_rectangle_area_computation(self):
        """Test area computed field."""
        r = Rectangle(x=0.0, y=0.0, width=10.0, height=20.0)
        assert r.area == 200.0

        r2 = Rectangle(x=50.0, y=50.0, width=5.5, height=4.0)
        assert r2.area == 22.0

    def test_rectangle_center_computation(self):
        """Test center computed field."""
        r = Rectangle(x=0.0, y=0.0, width=100.0, height=100.0)
        center = r.center
        assert center.x == 50.0
        assert center.y == 50.0
        assert isinstance(center, Vector2D)

        r2 = Rectangle(x=100.0, y=200.0, width=50.0, height=80.0)
        center2 = r2.center
        assert center2.x == 125.0
        assert center2.y == 240.0

    def test_rectangle_edge_properties(self):
        """Test left, right, top, bottom computed fields."""
        r = Rectangle(x=100.0, y=200.0, width=50.0, height=75.0)
        assert r.left == 100.0
        assert r.right == 150.0
        assert r.top == 200.0
        assert r.bottom == 275.0

    def test_rectangle_contains_point_inside(self):
        """Test contains_point returns True for points inside."""
        r = Rectangle(x=0.0, y=0.0, width=100.0, height=100.0)
        assert r.contains_point(Vector2D(x=50.0, y=50.0)) is True
        assert r.contains_point(Vector2D(x=10.0, y=10.0)) is True
        assert r.contains_point(Vector2D(x=90.0, y=90.0)) is True

    def test_rectangle_contains_point_on_boundary(self):
        """Test contains_point returns True for points on boundary."""
        r = Rectangle(x=0.0, y=0.0, width=100.0, height=100.0)
        assert r.contains_point(Vector2D(x=0.0, y=0.0)) is True
        assert r.contains_point(Vector2D(x=100.0, y=100.0)) is True
        assert r.contains_point(Vector2D(x=0.0, y=50.0)) is True
        assert r.contains_point(Vector2D(x=100.0, y=50.0)) is True

    def test_rectangle_contains_point_outside(self):
        """Test contains_point returns False for points outside."""
        r = Rectangle(x=0.0, y=0.0, width=100.0, height=100.0)
        assert r.contains_point(Vector2D(x=-10.0, y=50.0)) is False
        assert r.contains_point(Vector2D(x=110.0, y=50.0)) is False
        assert r.contains_point(Vector2D(x=50.0, y=-10.0)) is False
        assert r.contains_point(Vector2D(x=50.0, y=110.0)) is False
        assert r.contains_point(Vector2D(x=200.0, y=200.0)) is False

    def test_rectangle_intersects_overlapping(self):
        """Test intersects returns True for overlapping rectangles."""
        r1 = Rectangle(x=0.0, y=0.0, width=100.0, height=100.0)
        r2 = Rectangle(x=50.0, y=50.0, width=100.0, height=100.0)
        assert r1.intersects(r2) is True
        assert r2.intersects(r1) is True

    def test_rectangle_intersects_touching(self):
        """Test intersects for rectangles touching at edges."""
        r1 = Rectangle(x=0.0, y=0.0, width=100.0, height=100.0)
        r2 = Rectangle(x=100.0, y=0.0, width=100.0, height=100.0)
        # Touching at edge should be considered intersecting
        assert r1.intersects(r2) is True

    def test_rectangle_intersects_non_overlapping(self):
        """Test intersects returns False for non-overlapping rectangles."""
        r1 = Rectangle(x=0.0, y=0.0, width=50.0, height=50.0)
        r2 = Rectangle(x=100.0, y=100.0, width=50.0, height=50.0)
        assert r1.intersects(r2) is False
        assert r2.intersects(r1) is False

    def test_rectangle_intersects_contained(self):
        """Test intersects when one rectangle is inside another."""
        r1 = Rectangle(x=0.0, y=0.0, width=200.0, height=200.0)
        r2 = Rectangle(x=50.0, y=50.0, width=50.0, height=50.0)
        assert r1.intersects(r2) is True
        assert r2.intersects(r1) is True

    def test_rectangle_immutability(self):
        """Test Rectangle is frozen (immutable)."""
        r = Rectangle(x=100.0, y=100.0, width=50.0, height=50.0)
        with pytest.raises(ValidationError):
            r.x = 200.0
        with pytest.raises(ValidationError):
            r.width = 100.0

    def test_rectangle_string_representation(self):
        """Test __str__ method."""
        r = Rectangle(x=100.5, y=200.7, width=50.3, height=75.9)
        s = str(r)
        assert "Rectangle" in s
        assert "100.50" in s
        assert "200.70" in s
        assert "50.30" in s
        assert "75.90" in s

    def test_rectangle_large_values(self):
        """Test rectangle with large dimensions."""
        r = Rectangle(x=10000.0, y=20000.0, width=5000.0, height=3000.0)
        assert r.area == 15000000.0
        assert r.right == 15000.0
        assert r.bottom == 23000.0

    def test_rectangle_small_values(self):
        """Test rectangle with very small dimensions."""
        r = Rectangle(x=0.0, y=0.0, width=0.1, height=0.1)
        # Use pytest.approx for floating point comparisons
        assert r.area == pytest.approx(0.01)
        assert r.center.x == pytest.approx(0.05)
        assert r.center.y == pytest.approx(0.05)


# ============================================================================
# Integration Tests
# ============================================================================


class TestModelIntegration:
    """Test models working together."""

    def test_rectangle_with_vector2d_position(self):
        """Test using Vector2D to check rectangle containment."""
        rect = Rectangle(x=100.0, y=100.0, width=200.0, height=150.0)
        point1 = Vector2D(x=150.0, y=150.0)
        point2 = Vector2D(x=50.0, y=50.0)

        assert rect.contains_point(point1) is True
        assert rect.contains_point(point2) is False

    def test_color_and_rectangle_for_ui_element(self):
        """Test creating a colored UI element."""
        bounds = Rectangle(x=10.0, y=10.0, width=100.0, height=50.0)
        color = Color(r=255, g=0, b=0, a=200)

        assert bounds.area == 5000.0
        assert color.as_tuple == (255, 0, 0, 200)
        # These could be used together in rendering

    def test_multiple_vectors_and_rectangles(self):
        """Test managing multiple geometric objects."""
        positions = [
            Vector2D(x=0.0, y=0.0),
            Vector2D(x=100.0, y=100.0),
            Vector2D(x=200.0, y=200.0),
        ]
        bounds = Rectangle(x=50.0, y=50.0, width=100.0, height=100.0)

        # Check which positions are in bounds
        inside = [pos for pos in positions if bounds.contains_point(pos)]
        assert len(inside) == 1
        assert inside[0].x == 100.0
        assert inside[0].y == 100.0
