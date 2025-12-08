"""
Comprehensive tests for the visual feedback system.

Tests cover:
- VisualEffect model validation and computed properties
- ScorePopup model validation and computed properties
- FeedbackManager effect creation and lifecycle management
- Effect aging and removal
- Multiple simultaneous effects
"""

import pytest
from pydantic import ValidationError
import pygame

from models import (
    Vector2D,
    Color,
    VisualEffect,
    ScorePopup,
    EffectType,
)
from games.DuckHunt.game.feedback import FeedbackManager


# ============================================================================
# VisualEffect Model Tests
# ============================================================================


class TestVisualEffectModel:
    """Test suite for VisualEffect Pydantic model."""

    def test_visual_effect_creation_minimal(self):
        """Test creating VisualEffect with minimal required fields."""
        effect = VisualEffect(
            position=Vector2D(x=100.0, y=200.0),
            lifetime=0.0,
            max_lifetime=1.0,
            effect_type=EffectType.HIT
        )

        assert effect.position.x == 100.0
        assert effect.position.y == 200.0
        assert effect.lifetime == 0.0
        assert effect.max_lifetime == 1.0
        assert effect.effect_type == EffectType.HIT
        # Check defaults
        assert effect.color == Color(r=255, g=255, b=255, a=255)
        assert effect.size == 20.0
        assert effect.velocity == Vector2D(x=0.0, y=0.0)

    def test_visual_effect_creation_full(self):
        """Test creating VisualEffect with all fields specified."""
        effect = VisualEffect(
            position=Vector2D(x=100.0, y=200.0),
            lifetime=0.5,
            max_lifetime=2.0,
            effect_type=EffectType.EXPLOSION,
            color=Color(r=255, g=0, b=0, a=200),
            size=40.0,
            velocity=Vector2D(x=10.0, y=-20.0)
        )

        assert effect.position.x == 100.0
        assert effect.color.r == 255
        assert effect.size == 40.0
        assert effect.velocity.x == 10.0

    def test_visual_effect_negative_lifetime_validation(self):
        """Test that negative lifetime is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VisualEffect(
                position=Vector2D(x=100.0, y=200.0),
                lifetime=-0.5,
                max_lifetime=1.0,
                effect_type=EffectType.HIT
            )
        assert "Lifetime must be non-negative" in str(exc_info.value)

    def test_visual_effect_negative_max_lifetime_validation(self):
        """Test that negative max_lifetime is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VisualEffect(
                position=Vector2D(x=100.0, y=200.0),
                lifetime=0.0,
                max_lifetime=-1.0,
                effect_type=EffectType.HIT
            )
        assert "Lifetime must be non-negative" in str(exc_info.value)

    def test_visual_effect_zero_size_validation(self):
        """Test that zero size is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VisualEffect(
                position=Vector2D(x=100.0, y=200.0),
                lifetime=0.0,
                max_lifetime=1.0,
                effect_type=EffectType.HIT,
                size=0.0
            )
        assert "Size must be positive" in str(exc_info.value)

    def test_visual_effect_negative_size_validation(self):
        """Test that negative size is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VisualEffect(
                position=Vector2D(x=100.0, y=200.0),
                lifetime=0.0,
                max_lifetime=1.0,
                effect_type=EffectType.HIT,
                size=-10.0
            )
        assert "Size must be positive" in str(exc_info.value)

    def test_visual_effect_alpha_at_start(self):
        """Test alpha is 255 (fully opaque) at start of lifetime."""
        effect = VisualEffect(
            position=Vector2D(x=100.0, y=200.0),
            lifetime=0.0,
            max_lifetime=1.0,
            effect_type=EffectType.HIT
        )
        assert effect.alpha == 255

    def test_visual_effect_alpha_at_half_life(self):
        """Test alpha is approximately 128 at half lifetime."""
        effect = VisualEffect(
            position=Vector2D(x=100.0, y=200.0),
            lifetime=0.5,
            max_lifetime=1.0,
            effect_type=EffectType.HIT
        )
        # Should be 127 or 128 due to integer rounding
        assert 127 <= effect.alpha <= 128

    def test_visual_effect_alpha_at_end(self):
        """Test alpha is 0 (fully transparent) at end of lifetime."""
        effect = VisualEffect(
            position=Vector2D(x=100.0, y=200.0),
            lifetime=1.0,
            max_lifetime=1.0,
            effect_type=EffectType.HIT
        )
        assert effect.alpha == 0

    def test_visual_effect_alpha_beyond_lifetime(self):
        """Test alpha is 0 when lifetime exceeds max_lifetime."""
        effect = VisualEffect(
            position=Vector2D(x=100.0, y=200.0),
            lifetime=1.5,
            max_lifetime=1.0,
            effect_type=EffectType.HIT
        )
        assert effect.alpha == 0

    def test_visual_effect_alpha_linear_fade(self):
        """Test alpha fades linearly over lifetime."""
        max_lifetime = 1.0
        lifetimes = [0.0, 0.25, 0.5, 0.75, 1.0]
        expected_alphas = [255, 191, 127, 63, 0]

        for lifetime, expected_alpha in zip(lifetimes, expected_alphas):
            effect = VisualEffect(
                position=Vector2D(x=100.0, y=200.0),
                lifetime=lifetime,
                max_lifetime=max_lifetime,
                effect_type=EffectType.HIT
            )
            # Allow ±1 for rounding
            assert abs(effect.alpha - expected_alpha) <= 1

    def test_visual_effect_is_alive_true(self):
        """Test is_alive returns True when lifetime < max_lifetime."""
        effect = VisualEffect(
            position=Vector2D(x=100.0, y=200.0),
            lifetime=0.5,
            max_lifetime=1.0,
            effect_type=EffectType.HIT
        )
        assert effect.is_alive is True

    def test_visual_effect_is_alive_false_at_end(self):
        """Test is_alive returns False when lifetime == max_lifetime."""
        effect = VisualEffect(
            position=Vector2D(x=100.0, y=200.0),
            lifetime=1.0,
            max_lifetime=1.0,
            effect_type=EffectType.HIT
        )
        assert effect.is_alive is False

    def test_visual_effect_is_alive_false_beyond_end(self):
        """Test is_alive returns False when lifetime > max_lifetime."""
        effect = VisualEffect(
            position=Vector2D(x=100.0, y=200.0),
            lifetime=1.5,
            max_lifetime=1.0,
            effect_type=EffectType.HIT
        )
        assert effect.is_alive is False

    def test_visual_effect_immutability(self):
        """Test that VisualEffect is immutable (frozen model)."""
        effect = VisualEffect(
            position=Vector2D(x=100.0, y=200.0),
            lifetime=0.0,
            max_lifetime=1.0,
            effect_type=EffectType.HIT
        )

        with pytest.raises(ValidationError):
            effect.lifetime = 0.5

    def test_visual_effect_all_effect_types(self):
        """Test VisualEffect with all EffectType values."""
        for effect_type in [EffectType.HIT, EffectType.MISS, EffectType.EXPLOSION, EffectType.SCORE_POPUP]:
            effect = VisualEffect(
                position=Vector2D(x=100.0, y=200.0),
                lifetime=0.0,
                max_lifetime=1.0,
                effect_type=effect_type
            )
            assert effect.effect_type == effect_type

    def test_visual_effect_string_representation(self):
        """Test __str__ method provides useful debug output."""
        effect = VisualEffect(
            position=Vector2D(x=100.0, y=200.0),
            lifetime=0.5,
            max_lifetime=1.0,
            effect_type=EffectType.HIT
        )
        str_repr = str(effect)
        assert "VisualEffect" in str_repr
        assert "hit" in str_repr
        assert "0.50" in str_repr or "0.5" in str_repr


# ============================================================================
# ScorePopup Model Tests
# ============================================================================


class TestScorePopupModel:
    """Test suite for ScorePopup Pydantic model."""

    def test_score_popup_creation_minimal(self):
        """Test creating ScorePopup with minimal fields (using defaults)."""
        popup = ScorePopup(
            position=Vector2D(x=100.0, y=200.0),
            value=100,
            lifetime=0.0,
            color=Color(r=255, g=215, b=0, a=255)
        )

        assert popup.position.x == 100.0
        assert popup.value == 100
        assert popup.lifetime == 0.0
        assert popup.color.r == 255
        # Check defaults
        assert popup.max_lifetime == 1.0
        assert popup.velocity == Vector2D(x=0.0, y=-50.0)

    def test_score_popup_creation_full(self):
        """Test creating ScorePopup with all fields specified."""
        popup = ScorePopup(
            position=Vector2D(x=100.0, y=200.0),
            value=250,
            lifetime=0.3,
            color=Color(r=0, g=255, b=0, a=255),
            max_lifetime=2.0,
            velocity=Vector2D(x=5.0, y=-30.0)
        )

        assert popup.position.x == 100.0
        assert popup.value == 250
        assert popup.lifetime == 0.3
        assert popup.max_lifetime == 2.0
        assert popup.velocity.x == 5.0

    def test_score_popup_negative_value(self):
        """Test ScorePopup with negative value (penalty)."""
        popup = ScorePopup(
            position=Vector2D(x=100.0, y=200.0),
            value=-50,
            lifetime=0.0,
            color=Color(r=255, g=0, b=0, a=255)
        )
        assert popup.value == -50

    def test_score_popup_zero_value(self):
        """Test ScorePopup with zero value."""
        popup = ScorePopup(
            position=Vector2D(x=100.0, y=200.0),
            value=0,
            lifetime=0.0,
            color=Color(r=128, g=128, b=128, a=255)
        )
        assert popup.value == 0

    def test_score_popup_negative_lifetime_validation(self):
        """Test that negative lifetime is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ScorePopup(
                position=Vector2D(x=100.0, y=200.0),
                value=100,
                lifetime=-0.5,
                color=Color(r=255, g=215, b=0, a=255)
            )
        assert "Lifetime must be non-negative" in str(exc_info.value)

    def test_score_popup_alpha_at_start(self):
        """Test alpha is 255 (fully opaque) at start of lifetime."""
        popup = ScorePopup(
            position=Vector2D(x=100.0, y=200.0),
            value=100,
            lifetime=0.0,
            color=Color(r=255, g=215, b=0, a=255)
        )
        assert popup.alpha == 255

    def test_score_popup_alpha_at_half_life(self):
        """Test alpha is approximately 128 at half lifetime."""
        popup = ScorePopup(
            position=Vector2D(x=100.0, y=200.0),
            value=100,
            lifetime=0.5,
            color=Color(r=255, g=215, b=0, a=255),
            max_lifetime=1.0
        )
        assert 127 <= popup.alpha <= 128

    def test_score_popup_alpha_at_end(self):
        """Test alpha is 0 (fully transparent) at end of lifetime."""
        popup = ScorePopup(
            position=Vector2D(x=100.0, y=200.0),
            value=100,
            lifetime=1.0,
            color=Color(r=255, g=215, b=0, a=255),
            max_lifetime=1.0
        )
        assert popup.alpha == 0

    def test_score_popup_is_alive_true(self):
        """Test is_alive returns True when lifetime < max_lifetime."""
        popup = ScorePopup(
            position=Vector2D(x=100.0, y=200.0),
            value=100,
            lifetime=0.5,
            color=Color(r=255, g=215, b=0, a=255),
            max_lifetime=1.0
        )
        assert popup.is_alive is True

    def test_score_popup_is_alive_false(self):
        """Test is_alive returns False when lifetime >= max_lifetime."""
        popup = ScorePopup(
            position=Vector2D(x=100.0, y=200.0),
            value=100,
            lifetime=1.0,
            color=Color(r=255, g=215, b=0, a=255),
            max_lifetime=1.0
        )
        assert popup.is_alive is False

    def test_score_popup_immutability(self):
        """Test that ScorePopup is immutable (frozen model)."""
        popup = ScorePopup(
            position=Vector2D(x=100.0, y=200.0),
            value=100,
            lifetime=0.0,
            color=Color(r=255, g=215, b=0, a=255)
        )

        with pytest.raises(ValidationError):
            popup.lifetime = 0.5

    def test_score_popup_string_representation(self):
        """Test __str__ method provides useful debug output."""
        popup = ScorePopup(
            position=Vector2D(x=100.0, y=200.0),
            value=100,
            lifetime=0.5,
            color=Color(r=255, g=215, b=0, a=255),
            max_lifetime=1.0
        )
        str_repr = str(popup)
        assert "ScorePopup" in str_repr
        assert "+100" in str_repr
        assert "0.50" in str_repr or "0.5" in str_repr

    def test_score_popup_string_representation_negative(self):
        """Test __str__ formats negative values correctly."""
        popup = ScorePopup(
            position=Vector2D(x=100.0, y=200.0),
            value=-50,
            lifetime=0.0,
            color=Color(r=255, g=0, b=0, a=255)
        )
        str_repr = str(popup)
        assert "-50" in str_repr


# ============================================================================
# FeedbackManager Tests
# ============================================================================


class TestFeedbackManager:
    """Test suite for FeedbackManager class."""

    def test_feedback_manager_initialization(self):
        """Test FeedbackManager initializes with empty lists."""
        manager = FeedbackManager()
        assert len(manager.effects) == 0
        assert len(manager.popups) == 0
        assert manager.get_active_count() == 0

    def test_add_hit_effect_creates_effect(self):
        """Test add_hit_effect creates a visual effect."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)

        assert len(manager.effects) == 1
        assert manager.effects[0].effect_type == EffectType.HIT
        assert manager.effects[0].position.x == 100.0
        assert manager.effects[0].position.y == 200.0

    def test_add_hit_effect_creates_popup(self):
        """Test add_hit_effect creates a score popup."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)

        assert len(manager.popups) == 1
        assert manager.popups[0].value == 100
        assert manager.popups[0].position.x == 100.0

    def test_add_hit_effect_count(self):
        """Test add_hit_effect increases active count by 2."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)

        assert manager.get_active_count() == 2  # 1 effect + 1 popup

    def test_add_miss_effect_creates_effect(self):
        """Test add_miss_effect creates a visual effect."""
        manager = FeedbackManager()
        manager.add_miss_effect(Vector2D(x=150.0, y=250.0))

        assert len(manager.effects) == 1
        assert manager.effects[0].effect_type == EffectType.MISS
        assert manager.effects[0].position.x == 150.0

    def test_add_miss_effect_no_popup(self):
        """Test add_miss_effect does not create a score popup."""
        manager = FeedbackManager()
        manager.add_miss_effect(Vector2D(x=150.0, y=250.0))

        assert len(manager.popups) == 0

    def test_update_ages_effects(self):
        """Test update increases effect lifetime."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)

        initial_lifetime = manager.effects[0].lifetime
        manager.update(0.1)

        assert manager.effects[0].lifetime > initial_lifetime
        assert manager.effects[0].lifetime == pytest.approx(0.1)

    def test_update_ages_popups(self):
        """Test update increases popup lifetime."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)

        initial_lifetime = manager.popups[0].lifetime
        manager.update(0.1)

        assert manager.popups[0].lifetime > initial_lifetime
        assert manager.popups[0].lifetime == pytest.approx(0.1)

    def test_update_moves_effects_with_velocity(self):
        """Test update moves effects according to velocity."""
        manager = FeedbackManager()
        # Create effect with custom velocity (need to add manually)
        effect = VisualEffect(
            position=Vector2D(x=100.0, y=200.0),
            lifetime=0.0,
            max_lifetime=1.0,
            effect_type=EffectType.HIT,
            velocity=Vector2D(x=50.0, y=-50.0)
        )
        manager.effects.append(effect)

        manager.update(0.1)

        # Position should change: x += 50 * 0.1 = 5, y += -50 * 0.1 = -5
        assert manager.effects[0].position.x == pytest.approx(105.0)
        assert manager.effects[0].position.y == pytest.approx(195.0)

    def test_update_moves_popups_with_velocity(self):
        """Test update moves popups according to velocity (default upward)."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)

        initial_y = manager.popups[0].position.y
        manager.update(0.1)

        # Default velocity is (0, -50), so y should decrease
        assert manager.popups[0].position.y < initial_y

    def test_update_removes_dead_effects(self):
        """Test update removes effects that exceed max_lifetime."""
        manager = FeedbackManager()
        manager.add_miss_effect(Vector2D(x=100.0, y=200.0))

        # Miss effect has max_lifetime of 0.3 seconds
        manager.update(0.4)  # Age beyond max_lifetime

        assert len(manager.effects) == 0

    def test_update_removes_dead_popups(self):
        """Test update removes popups that exceed max_lifetime."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)

        # Popup has max_lifetime of 1.0 second
        manager.update(1.1)  # Age beyond max_lifetime

        assert len(manager.popups) == 0

    def test_update_keeps_alive_effects(self):
        """Test update keeps effects that haven't expired."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)

        # Hit effect has max_lifetime of 0.5 seconds
        manager.update(0.3)  # Age but not beyond max_lifetime

        assert len(manager.effects) == 1

    def test_multiple_effects_update(self):
        """Test updating multiple effects simultaneously."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)
        manager.add_miss_effect(Vector2D(x=200.0, y=300.0))

        manager.update(0.1)

        # Should have 1 hit effect, 1 miss effect, 1 popup
        assert len(manager.effects) == 2
        assert len(manager.popups) == 1

    def test_multiple_effects_partial_expiration(self):
        """Test that only expired effects are removed."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)  # 0.5s lifetime
        manager.add_miss_effect(Vector2D(x=200.0, y=300.0))  # 0.3s lifetime

        manager.update(0.35)  # Miss expires, hit doesn't

        assert len(manager.effects) == 1
        assert manager.effects[0].effect_type == EffectType.HIT

    def test_clear_removes_all_effects(self):
        """Test clear removes all effects and popups."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)
        manager.add_miss_effect(Vector2D(x=200.0, y=300.0))

        manager.clear()

        assert len(manager.effects) == 0
        assert len(manager.popups) == 0
        assert manager.get_active_count() == 0

    def test_get_active_count_multiple(self):
        """Test get_active_count with multiple effects."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)
        manager.add_hit_effect(Vector2D(x=150.0, y=250.0), points=200)
        manager.add_miss_effect(Vector2D(x=200.0, y=300.0))

        # 3 effects (2 hits + 1 miss) + 2 popups
        assert manager.get_active_count() == 5

    def test_render_does_not_crash_with_effects(self):
        """Test render doesn't crash with active effects (basic smoke test)."""
        pygame.init()
        screen = pygame.display.set_mode((800, 600))

        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=400.0, y=300.0), points=100)
        manager.add_miss_effect(Vector2D(x=200.0, y=150.0))

        # Should not raise exception
        manager.render(screen)

        pygame.quit()

    def test_render_does_not_crash_empty(self):
        """Test render doesn't crash with no effects."""
        pygame.init()
        screen = pygame.display.set_mode((800, 600))

        manager = FeedbackManager()

        # Should not raise exception
        manager.render(screen)

        pygame.quit()

    def test_effect_lifecycle_complete(self):
        """Test complete lifecycle: create → update → expire → remove."""
        manager = FeedbackManager()
        manager.add_miss_effect(Vector2D(x=100.0, y=200.0))

        # Just created
        assert len(manager.effects) == 1
        assert manager.effects[0].is_alive is True

        # Age partially
        manager.update(0.15)
        assert len(manager.effects) == 1
        assert manager.effects[0].lifetime == pytest.approx(0.15)

        # Age to expiration (miss has 0.3s max_lifetime)
        manager.update(0.20)
        assert len(manager.effects) == 0  # Should be removed

    def test_popup_lifecycle_complete(self):
        """Test complete popup lifecycle: create → update → expire → remove."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)

        # Just created
        assert len(manager.popups) == 1
        assert manager.popups[0].is_alive is True

        # Age partially
        manager.update(0.5)
        assert len(manager.popups) == 1

        # Age to expiration (popup has 1.0s max_lifetime)
        manager.update(0.6)
        assert len(manager.popups) == 0  # Should be removed

    def test_multiple_simultaneous_effects_different_positions(self):
        """Test managing many simultaneous effects at different positions."""
        manager = FeedbackManager()

        # Add multiple effects
        positions = [
            Vector2D(x=100.0, y=100.0),
            Vector2D(x=200.0, y=200.0),
            Vector2D(x=300.0, y=300.0),
            Vector2D(x=400.0, y=400.0),
        ]

        for pos in positions:
            manager.add_hit_effect(pos, points=100)

        assert len(manager.effects) == 4
        assert len(manager.popups) == 4

        # Verify positions are preserved
        effect_positions = [e.position for e in manager.effects]
        for pos in positions:
            assert pos in effect_positions

    def test_hit_effect_properties(self):
        """Test that hit effects have correct properties."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=100)

        effect = manager.effects[0]
        assert effect.effect_type == EffectType.HIT
        assert effect.color.g == 255  # Green for hits
        assert effect.max_lifetime == 0.5
        assert effect.size == 40.0

    def test_miss_effect_properties(self):
        """Test that miss effects have correct properties."""
        manager = FeedbackManager()
        manager.add_miss_effect(Vector2D(x=100.0, y=200.0))

        effect = manager.effects[0]
        assert effect.effect_type == EffectType.MISS
        assert effect.color.r == 255  # Red for misses
        assert effect.max_lifetime == 0.3
        assert effect.size == 20.0

    def test_score_popup_properties(self):
        """Test that score popups have correct properties."""
        manager = FeedbackManager()
        manager.add_hit_effect(Vector2D(x=100.0, y=200.0), points=250)

        popup = manager.popups[0]
        assert popup.value == 250
        assert popup.color.r == 255  # Gold color
        assert popup.color.g == 215
        assert popup.max_lifetime == 1.0
        assert popup.velocity.y == -50.0  # Float upward

    def test_render_explosion_effect(self):
        """Test rendering explosion effect type (for full coverage)."""
        pygame.init()
        screen = pygame.display.set_mode((800, 600))

        manager = FeedbackManager()
        # Manually add an explosion effect
        explosion = VisualEffect(
            position=Vector2D(x=400.0, y=300.0),
            lifetime=0.0,
            max_lifetime=1.0,
            effect_type=EffectType.EXPLOSION,
            color=Color(r=255, g=128, b=0, a=255),
            size=30.0
        )
        manager.effects.append(explosion)

        # Should not raise exception
        manager.render(screen)

        pygame.quit()
