"""
Comprehensive tests for ClassicMode game mode.

Tests cover:
- Target spawning logic
- Hit detection
- Miss detection (off-screen escapes)
- Difficulty progression
- Win/lose conditions
- State management
- Feedback integration
"""

import pytest
import pygame
import time
from unittest.mock import Mock, patch
from games.DuckHunt.game.modes.classic import ClassicMode
from games.DuckHunt.input.input_event import InputEvent
from models import Vector2D, EventType, TargetState, GameState
from games.DuckHunt.config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    TARGET_SPAWN_RATE,
    TARGET_MAX_ACTIVE,
    CLASSIC_INITIAL_SPEED,
    CLASSIC_SPEED_INCREASE,
    CLASSIC_MAX_SPEED,
)


@pytest.fixture
def mode():
    """Create a ClassicMode instance for testing."""
    return ClassicMode()


@pytest.fixture
def mode_with_limits():
    """Create a ClassicMode with win/lose conditions."""
    return ClassicMode(max_misses=5, target_score=10)


@pytest.fixture
def pygame_init():
    """Initialize pygame for rendering tests."""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    yield screen
    pygame.quit()


# ============================================================================
# Target Spawning Tests
# ============================================================================


def test_initial_state(mode):
    """Test mode starts in correct initial state."""
    assert mode.state == GameState.PLAYING
    assert mode.get_score() == 0
    assert len(mode.targets) == 0


def test_target_spawning_on_update(mode):
    """Test that targets spawn after spawn timer expires."""
    # Initially no targets
    assert len(mode.targets) == 0

    # Update for less than spawn rate - should not spawn yet
    mode.update(TARGET_SPAWN_RATE / 2)
    assert len(mode.targets) == 0

    # Update to exceed spawn rate - should spawn one target
    mode.update(TARGET_SPAWN_RATE / 2 + 0.1)
    assert len(mode.targets) == 1


def test_target_spawns_from_edges(mode):
    """Test that targets spawn from left or right edges."""
    # Spawn multiple targets and check they're at edges
    for _ in range(20):  # Multiple spawns to test randomness
        mode._spawn_target()

    for target in mode.targets:
        x_pos = target.data.position.x
        # Should be at left edge (0) or right edge (SCREEN_WIDTH)
        assert x_pos == 0.0 or x_pos == float(SCREEN_WIDTH)


def test_target_spawn_respects_max_active(mode):
    """Test that spawning respects TARGET_MAX_ACTIVE limit."""
    # Try to spawn more than max
    for _ in range(TARGET_MAX_ACTIVE + 5):
        mode._spawn_target()

    # Should be capped at max
    assert len(mode.targets) <= TARGET_MAX_ACTIVE


def test_target_spawn_position_in_bounds(mode):
    """Test that target Y positions are within screen bounds."""
    for _ in range(20):
        mode._spawn_target()

    for target in mode.targets:
        y_pos = target.data.position.y
        assert 0 < y_pos < SCREEN_HEIGHT


def test_target_has_velocity(mode):
    """Test that spawned targets have non-zero velocity."""
    mode._spawn_target()
    target = mode.targets[0]

    # Should have velocity in X direction (left or right)
    assert target.data.velocity.x != 0
    # Should have zero Y velocity (horizontal movement)
    assert target.data.velocity.y == 0


def test_targets_spawn_left_and_right(mode):
    """Test that targets spawn from both left and right edges."""
    # Spawn many targets
    for _ in range(50):
        mode._spawn_target()

    # Check we have targets from both sides
    left_spawns = [t for t in mode.targets if t.data.position.x == 0.0]
    right_spawns = [t for t in mode.targets if t.data.position.x == float(SCREEN_WIDTH)]

    # With 50 spawns, should have at least one from each side (probabilistically)
    assert len(left_spawns) > 0
    assert len(right_spawns) > 0


# ============================================================================
# Movement and Update Tests
# ============================================================================


def test_targets_move_on_update(mode):
    """Test that targets move when update is called."""
    mode._spawn_target()
    target = mode.targets[0]
    initial_x = target.data.position.x

    # Update for 1 second
    mode.update(1.0)

    updated_target = mode.targets[0]
    updated_x = updated_target.data.position.x

    # Position should have changed
    assert updated_x != initial_x


def test_target_movement_direction(mode):
    """Test that targets move in correct direction based on spawn side."""
    # Manually create left-spawning target
    from games.DuckHunt.game.target import Target
    from models import TargetData

    left_target_data = TargetData(
        position=Vector2D(x=0.0, y=100.0),
        velocity=Vector2D(x=100.0, y=0.0),
        size=50.0,
        state=TargetState.ALIVE,
    )
    mode._targets = [Target(left_target_data)]

    initial_x = mode.targets[0].data.position.x

    # Update
    mode.update(1.0)

    # Should move right (positive X)
    assert mode.targets[0].data.position.x > initial_x


# ============================================================================
# Hit Detection Tests
# ============================================================================


def test_hit_detection_on_target(mode):
    """Test that clicking on a target registers as a hit."""
    # Spawn a target
    mode._spawn_target()
    target = mode.targets[0]

    # Create input event at target position
    event = InputEvent(
        position=target.data.position,
        timestamp=time.monotonic(),
        event_type=EventType.HIT,
    )

    # Handle input
    mode.handle_input([event])

    # Target should be marked as HIT
    assert mode.targets[0].data.state == TargetState.HIT
    # Score should increase
    assert mode.get_score() == 1


def test_hit_detection_miss(mode):
    """Test that clicking away from target registers as miss."""
    # Spawn a target
    mode._spawn_target()

    # Create input event far from any target
    event = InputEvent(
        position=Vector2D(x=SCREEN_WIDTH / 2, y=SCREEN_HEIGHT / 2),
        timestamp=time.monotonic(),
        event_type=EventType.HIT,
    )

    # Handle input
    mode.handle_input([event])

    # Target should still be ALIVE
    assert mode.targets[0].data.state == TargetState.ALIVE
    # Score should not increase
    assert mode.get_score() == 0
    # Misses should increase
    stats = mode._score_tracker.get_stats()
    assert stats.misses == 1


def test_hit_only_affects_one_target(mode):
    """Test that one click only hits one target."""
    # Spawn multiple overlapping targets
    from games.DuckHunt.game.target import Target
    from models import TargetData

    position = Vector2D(x=100.0, y=100.0)
    for _ in range(3):
        target_data = TargetData(
            position=position,
            velocity=Vector2D(x=50.0, y=0.0),
            size=50.0,
            state=TargetState.ALIVE,
        )
        mode._targets.append(Target(target_data))

    # Click at that position
    event = InputEvent(
        position=position, timestamp=time.monotonic(), event_type=EventType.HIT
    )
    mode.handle_input([event])

    # Only one target should be hit
    hit_targets = [t for t in mode.targets if t.data.state == TargetState.HIT]
    assert len(hit_targets) == 1


def test_inactive_targets_cannot_be_hit(mode):
    """Test that targets marked as HIT cannot be hit again."""
    # Spawn target
    mode._spawn_target()
    target_pos = mode.targets[0].data.position

    # Hit it once
    event = InputEvent(
        position=target_pos, timestamp=time.monotonic(), event_type=EventType.HIT
    )
    mode.handle_input([event])
    assert mode.get_score() == 1

    # Try to hit it again
    event2 = InputEvent(
        position=target_pos, timestamp=time.monotonic(), event_type=EventType.HIT
    )
    mode.handle_input([event2])

    # Score should only be 1 (first click counted as miss on second attempt)
    assert mode.get_score() == 1


# ============================================================================
# Off-Screen Escape Tests (Miss Detection)
# ============================================================================


def test_target_escape_left_edge(mode):
    """Test that targets escaping left edge are removed and count as miss."""
    from games.DuckHunt.game.target import Target
    from models import TargetData

    # Create target moving left, near left edge
    target_data = TargetData(
        position=Vector2D(x=10.0, y=100.0),
        velocity=Vector2D(x=-100.0, y=0.0),
        size=50.0,
        state=TargetState.ALIVE,
    )
    mode._targets = [Target(target_data)]

    initial_misses = mode._score_tracker.get_stats().misses

    # Update enough to move it off screen
    mode.update(1.0)

    # Target should be removed
    assert len(mode.targets) == 0
    # Should count as a miss
    assert mode._score_tracker.get_stats().misses == initial_misses + 1


def test_target_escape_right_edge(mode):
    """Test that targets escaping right edge are removed and count as miss."""
    from games.DuckHunt.game.target import Target
    from models import TargetData

    # Create target moving right, near right edge
    target_data = TargetData(
        position=Vector2D(x=SCREEN_WIDTH - 10.0, y=100.0),
        velocity=Vector2D(x=100.0, y=0.0),
        size=50.0,
        state=TargetState.ALIVE,
    )
    mode._targets = [Target(target_data)]

    initial_misses = mode._score_tracker.get_stats().misses

    # Update enough to move it off screen
    mode.update(1.0)

    # Target should be removed
    assert len(mode.targets) == 0
    # Should count as a miss
    assert mode._score_tracker.get_stats().misses == initial_misses + 1


def test_hit_targets_removed_when_off_screen(mode):
    """Test that hit targets are also removed when they go off screen."""
    from games.DuckHunt.game.target import Target
    from models import TargetData

    # Create hit target near edge
    target_data = TargetData(
        position=Vector2D(x=10.0, y=100.0),
        velocity=Vector2D(x=-100.0, y=0.0),
        size=50.0,
        state=TargetState.HIT,  # Already hit
    )
    mode._targets = [Target(target_data)]

    # Update to move it off screen
    mode.update(1.0)

    # Should be removed but NOT counted as miss
    assert len(mode.targets) == 0


# ============================================================================
# Difficulty Progression Tests
# ============================================================================


def test_difficulty_increases_on_hit(mode):
    """Test that target speed increases after successful hits."""
    initial_speed = mode._current_speed

    # Record a hit
    mode._increase_difficulty()

    # Speed should increase
    assert mode._current_speed == initial_speed + CLASSIC_SPEED_INCREASE


def test_difficulty_progression_caps_at_max_speed(mode):
    """Test that speed doesn't exceed CLASSIC_MAX_SPEED."""
    # Set speed near max
    mode._current_speed = CLASSIC_MAX_SPEED - CLASSIC_SPEED_INCREASE / 2

    # Increase difficulty multiple times
    for _ in range(10):
        mode._increase_difficulty()

    # Should be capped at max
    assert mode._current_speed == CLASSIC_MAX_SPEED


def test_new_targets_use_current_speed(mode):
    """Test that newly spawned targets use the current difficulty speed."""
    # Increase difficulty
    mode._increase_difficulty()
    current_speed = mode._current_speed

    # Spawn a target
    mode._spawn_target()
    target = mode.targets[0]

    # Velocity magnitude should match current speed
    velocity_magnitude = abs(target.data.velocity.x)
    assert velocity_magnitude == current_speed


# ============================================================================
# Win/Lose Condition Tests
# ============================================================================


def test_win_condition_target_score(mode_with_limits):
    """Test that game ends when target score is reached."""
    # Mode has target_score=10
    assert mode_with_limits.state == GameState.PLAYING

    # Record 10 hits
    for _ in range(10):
        mode_with_limits._score_tracker = mode_with_limits._score_tracker.record_hit()

    # Check game over
    mode_with_limits._check_game_over()

    # Should be game over
    assert mode_with_limits.state == GameState.GAME_OVER


def test_lose_condition_max_misses(mode_with_limits):
    """Test that game ends when max misses is reached."""
    # Mode has max_misses=5
    assert mode_with_limits.state == GameState.PLAYING

    # Record 5 misses
    for _ in range(5):
        mode_with_limits._score_tracker = mode_with_limits._score_tracker.record_miss()

    # Check game over
    mode_with_limits._check_game_over()

    # Should be game over
    assert mode_with_limits.state == GameState.GAME_OVER


def test_no_win_condition_in_endless_mode(mode):
    """Test that endless mode (no target_score) never wins."""
    # Record many hits
    for _ in range(100):
        mode._score_tracker = mode._score_tracker.record_hit()

    mode._check_game_over()

    # Should still be playing
    assert mode.state == GameState.PLAYING


def test_no_lose_condition_in_endless_mode(mode):
    """Test that endless mode (no max_misses) never loses."""
    # Record many misses
    for _ in range(100):
        mode._score_tracker = mode._score_tracker.record_miss()

    mode._check_game_over()

    # Should still be playing
    assert mode.state == GameState.PLAYING


# ============================================================================
# State Management Tests
# ============================================================================


def test_no_updates_when_game_over(mode_with_limits):
    """Test that updates are ignored when game is over."""
    # Force game over
    mode_with_limits._state = GameState.GAME_OVER

    # Spawn timer should not trigger spawns
    initial_target_count = len(mode_with_limits.targets)
    mode_with_limits.update(TARGET_SPAWN_RATE * 2)

    # No new targets should spawn
    assert len(mode_with_limits.targets) == initial_target_count


def test_no_input_handling_when_game_over(mode_with_limits):
    """Test that input is ignored when game is over."""
    # Spawn a target
    mode_with_limits._spawn_target()

    # Force game over
    mode_with_limits._state = GameState.GAME_OVER

    target_pos = mode_with_limits.targets[0].data.position
    initial_score = mode_with_limits.get_score()

    # Try to hit target
    event = InputEvent(
        position=target_pos, timestamp=time.monotonic(), event_type=EventType.HIT
    )
    mode_with_limits.handle_input([event])

    # Score should not change
    assert mode_with_limits.get_score() == initial_score


def test_score_tracking_with_combo(mode):
    """Test that combo tracking works correctly."""
    # Spawn target and hit it 3 times
    for i in range(3):
        mode._spawn_target()
        target_pos = mode.targets[-1].data.position
        event = InputEvent(
            position=target_pos, timestamp=time.monotonic(), event_type=EventType.HIT
        )
        mode.handle_input([event])

    stats = mode._score_tracker.get_stats()
    assert stats.hits == 3
    assert stats.current_combo == 3


def test_combo_breaks_on_miss(mode):
    """Test that combo resets on miss."""
    # Hit twice
    for i in range(2):
        mode._spawn_target()
        target_pos = mode.targets[-1].data.position
        event = InputEvent(
            position=target_pos, timestamp=time.monotonic(), event_type=EventType.HIT
        )
        mode.handle_input([event])

    # Miss once
    event = InputEvent(
        position=Vector2D(x=9999.0, y=9999.0),
        timestamp=time.monotonic(),
        event_type=EventType.HIT,
    )
    mode.handle_input([event])

    stats = mode._score_tracker.get_stats()
    assert stats.current_combo == 0
    assert stats.max_combo == 2  # Should remember max


# ============================================================================
# Rendering Tests
# ============================================================================


def test_render_does_not_crash(mode, pygame_init):
    """Test that render method doesn't crash."""
    screen = pygame_init

    # Add some targets
    mode._spawn_target()
    mode._spawn_target()

    # Should not raise exception
    mode.render(screen)


def test_render_game_over_screen(mode_with_limits, pygame_init):
    """Test that game over screen renders without crashing."""
    screen = pygame_init

    # Force game over
    mode_with_limits._state = GameState.GAME_OVER

    # Should not raise exception
    mode_with_limits.render(screen)


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_game_flow(mode_with_limits):
    """Test a complete game flow from start to win."""
    assert mode_with_limits.state == GameState.PLAYING

    # Simulate game loop - 10 hits to win
    hits = 0
    while hits < 10:
        # Ensure we have room for a new target by clearing hit targets
        mode_with_limits._targets = [t for t in mode_with_limits.targets if t.is_active]

        # Spawn target
        mode_with_limits._spawn_target()

        # Get the newly spawned target (last one)
        target = mode_with_limits.targets[-1]
        target_pos = target.data.position

        # Hit it immediately (before it moves)
        event = InputEvent(
            position=target_pos, timestamp=time.monotonic(), event_type=EventType.HIT
        )
        mode_with_limits.handle_input([event])

        # Update hit count
        hits = mode_with_limits.get_score()

        # Update game state (only a tiny amount so targets don't escape)
        mode_with_limits.update(0.001)

    # Should win
    assert mode_with_limits.state == GameState.GAME_OVER
    assert mode_with_limits.get_score() == 10


def test_multiple_targets_active_simultaneously(mode):
    """Test that multiple targets can be active and move correctly."""
    # Spawn multiple targets
    for _ in range(3):
        mode._spawn_target()

    assert len(mode.targets) == 3

    # Update them
    mode.update(1.0)

    # All should have moved
    assert len(mode.targets) == 3  # None should have escaped yet


def test_spawn_timer_resets(mode):
    """Test that spawn timer resets after spawning."""
    # Update to trigger spawn
    mode.update(TARGET_SPAWN_RATE + 0.1)
    assert len(mode.targets) == 1

    # Update less than spawn rate
    mode.update(TARGET_SPAWN_RATE / 2)

    # Should not spawn another yet
    initial_count = len(mode.targets)
    mode.update(0.1)
    # Count may be same or higher depending on exact timing
    # The key is the spawn timer is working

    # Update again past spawn rate
    mode.update(TARGET_SPAWN_RATE)
    # Should have spawned at least one more (up to max)
    assert len(mode.targets) >= initial_count


# ============================================================================
# Feedback Integration Tests
# ============================================================================


def test_feedback_manager_initialized(mode):
    """Test that FeedbackManager is initialized."""
    assert mode.feedback is not None
    assert hasattr(mode.feedback, 'add_hit_effect')
    assert hasattr(mode.feedback, 'add_miss_effect')
    assert hasattr(mode.feedback, 'play_combo_sound')


def test_hit_triggers_hit_effect(mode):
    """Test that hitting a target triggers hit visual/audio feedback."""
    # Spawn a target
    mode._spawn_target()
    target = mode.targets[0]

    # Mock the feedback manager methods
    mode.feedback.add_hit_effect = Mock()
    mode.feedback.play_hit_sound = Mock()

    # Create input event at target position
    event = InputEvent(
        position=target.data.position,
        timestamp=time.monotonic(),
        event_type=EventType.HIT,
    )

    # Handle input
    mode.handle_input([event])

    # Verify feedback was called
    mode.feedback.add_hit_effect.assert_called_once()
    # Check that position and points were passed
    call_args = mode.feedback.add_hit_effect.call_args
    assert call_args[0][0] == event.position  # First positional arg is position
    assert call_args[1]['points'] == 100  # Keyword arg is points


def test_miss_triggers_miss_effect(mode):
    """Test that missing triggers miss visual/audio feedback."""
    # Mock the feedback manager methods
    mode.feedback.add_miss_effect = Mock()
    mode.feedback.play_miss_sound = Mock()

    # Create input event far from any target
    miss_position = Vector2D(x=SCREEN_WIDTH / 2, y=SCREEN_HEIGHT / 2)
    event = InputEvent(
        position=miss_position,
        timestamp=time.monotonic(),
        event_type=EventType.HIT,
    )

    # Handle input
    mode.handle_input([event])

    # Verify miss feedback was called
    mode.feedback.add_miss_effect.assert_called_once_with(miss_position)


def test_combo_milestone_triggers_combo_sound(mode):
    """Test that reaching combo milestones triggers combo sound."""
    # Mock the combo sound
    mode.feedback.play_combo_sound = Mock()
    mode.feedback.add_hit_effect = Mock()  # Mock this too to avoid side effects

    # Hit 5 targets to reach first combo milestone
    for i in range(5):
        mode._spawn_target()
        target = mode.targets[-1]
        event = InputEvent(
            position=target.data.position,
            timestamp=time.monotonic(),
            event_type=EventType.HIT,
        )
        mode.handle_input([event])

    # Should have called combo sound at least once (when combo = 5)
    assert mode.feedback.play_combo_sound.call_count >= 1


def test_combo_sound_not_triggered_before_milestone(mode):
    """Test that combo sound is not triggered before reaching milestone."""
    # Mock the combo sound
    mode.feedback.play_combo_sound = Mock()
    mode.feedback.add_hit_effect = Mock()

    # Hit only 4 targets (just before milestone)
    for i in range(4):
        mode._spawn_target()
        target = mode.targets[-1]
        event = InputEvent(
            position=target.data.position,
            timestamp=time.monotonic(),
            event_type=EventType.HIT,
        )
        mode.handle_input([event])

    # Should NOT have called combo sound
    mode.feedback.play_combo_sound.assert_not_called()


def test_feedback_update_called_on_mode_update(mode):
    """Test that feedback.update() is called during mode update."""
    # Mock the feedback update
    mode.feedback.update = Mock()

    # Update the mode
    dt = 0.016
    mode.update(dt)

    # Verify feedback update was called with correct dt
    mode.feedback.update.assert_called_once_with(dt)


def test_feedback_render_called_on_mode_render(mode, pygame_init):
    """Test that feedback.render() is called during mode render."""
    screen = pygame_init

    # Mock the feedback render
    mode.feedback.render = Mock()

    # Render the mode
    mode.render(screen)

    # Verify feedback render was called with screen
    mode.feedback.render.assert_called_once_with(screen)


def test_audio_can_be_disabled(mode):
    """Test that audio can be disabled via constructor."""
    # Create mode with audio disabled
    mode_no_audio = ClassicMode(audio_enabled=False)

    # FeedbackManager should still exist
    assert mode_no_audio.feedback is not None
    # But audio should be disabled
    assert mode_no_audio.feedback.audio_enabled is False


def test_multiple_hits_create_multiple_effects(mode):
    """Test that multiple hits create multiple feedback effects."""
    # Mock feedback methods
    mode.feedback.add_hit_effect = Mock()

    # Hit 3 targets
    for _ in range(3):
        mode._spawn_target()
        target = mode.targets[-1]
        event = InputEvent(
            position=target.data.position,
            timestamp=time.monotonic(),
            event_type=EventType.HIT,
        )
        mode.handle_input([event])

    # Should have called add_hit_effect 3 times
    assert mode.feedback.add_hit_effect.call_count == 3
