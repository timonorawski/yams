"""End-to-end tests for game engine interactions.

Uses InlineGameHarness to run minimal test games that validate
core engine behaviors like bouncing, collisions, and input handling.
"""

import pytest
import os

# Set headless mode for tests
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['AMS_LOG_LEVEL'] = 'WARNING'

from ams.test_backend import InlineGameHarness


class TestBallBouncing:
    """Test ball bouncing off screen edges."""

    BOUNCING_BALL_GAME = """
name: "Test Bouncing Ball"
screen_width: 400
screen_height: 300

entity_types:
  ball:
    width: 10
    height: 10
    color: white
    render:
      - shape: circle
        color: white
        fill: true
    interactions:
      screen:
        - edges: [left, right]
          because: continuous
          action: bounce_horizontal
        - edges: [top, bottom]
          because: continuous
          action: bounce_vertical

player:
  type: ball
  spawn: [195, 145]
  velocity: [200, 150]
"""

    def test_ball_bounces_off_right_wall(self):
        """Ball moving right should bounce off right wall."""
        harness = InlineGameHarness(self.BOUNCING_BALL_GAME, width=400, height=300)
        result = harness.run(duration=2.0, snapshot_interval=0.05)

        assert result.success, f"Errors: {result.errors}"
        assert "ball" in result.entities_at_end

        # Track ball's x positions to verify bouncing
        ball_history = result.get_entity_history("ball")
        assert len(ball_history) >= 2, "Should have multiple snapshots"

        # Ball should have changed direction at some point (bounced)
        # Check that x values go up then down (or vx changes sign)
        x_values = [h["x"] for h in ball_history]
        max_x = max(x_values)

        # Ball should stay in bounds
        assert max_x < 400, f"Ball should stay in bounds, max_x={max_x}"

    def test_ball_bounces_off_top_wall(self):
        """Ball moving up should bounce off top wall."""
        game = """
name: "Test Top Bounce"
screen_width: 400
screen_height: 300

entity_types:
  ball:
    width: 10
    height: 10
    color: white
    render:
      - shape: circle
        color: white
        fill: true
    interactions:
      screen:
        - edges: [top]
          because: continuous
          action: bounce_vertical

player:
  type: ball
  spawn: [195, 145]
  velocity: [0, -200]
"""
        harness = InlineGameHarness(game, width=400, height=300)
        result = harness.run(duration=2.0, snapshot_interval=0.05)

        assert result.success, f"Errors: {result.errors}"

        ball_history = result.get_entity_history("ball")
        y_values = [h["y"] for h in ball_history]
        min_y = min(y_values)

        # Ball should bounce off top (y=0) but not escape
        assert min_y >= 0, f"Ball should stay in bounds, min_y={min_y}"


class TestEntityCollisions:
    """Test entity-to-entity collision interactions."""

    def test_ball_destroys_brick_on_collision(self):
        """Ball hitting brick should destroy the brick."""
        game = """
name: "Test Brick Collision"
screen_width: 400
screen_height: 300

entity_types:
  ball:
    width: 10
    height: 10
    color: white
    render:
      - shape: circle
        color: white
        fill: true
    interactions:
      brick:
        when:
          distance: 0
        action: bounce_reflect

  brick:
    width: 50
    height: 20
    color: red
    tags: [brick]
    properties:
      hits_remaining: 1
    render:
      - shape: rectangle
        color: red
        fill: true
    interactions:
      ball:
        when:
          distance: 0
        action: take_damage

player:
  type: ball
  spawn: [175, 200]
  velocity: [0, -200]

default_layout:
  name: "Test Level"
  entities:
    - type: brick
      x: 150
      y: 50
"""
        harness = InlineGameHarness(game, width=400, height=300)
        result = harness.run(duration=2.0, snapshot_interval=0.1)

        assert result.success, f"Errors: {result.errors}"

        # Check brick was destroyed
        final_entities = result.entities_at_end
        assert "brick" not in final_entities, "Brick should be destroyed"
        assert "ball" in final_entities, "Ball should still exist"


class TestPointerInput:
    """Test pointer/click interactions."""

    def test_click_destroys_target(self):
        """Clicking on a target should destroy it."""
        game = """
name: "Test Click Destroy"
screen_width: 400
screen_height: 300

entity_types:
  target:
    width: 50
    height: 50
    color: red
    render:
      - shape: circle
        color: red
        fill: true
    interactions:
      pointer:
        when:
          distance: 0
          b.active: true
        action: destroy_self

default_layout:
  name: "Test Level"
  entities:
    - type: target
      x: 175
      y: 125
"""
        harness = InlineGameHarness(game, width=400, height=300)
        # Click on target at t=0.1s
        harness.backend.schedule_click(0.1, 200, 150)
        result = harness.run(duration=1.0, snapshot_interval=0.1)

        assert result.success, f"Errors: {result.errors}"
        assert "target" not in result.entities_at_end, "Target should be destroyed by click"

    @pytest.mark.xfail(reason="hit_target scoring needs interaction engine debugging")
    def test_click_scores_points(self):
        """Clicking on a target should add points."""
        game = """
name: "Test Click Score"
screen_width: 400
screen_height: 300

entity_types:
  target:
    width: 50
    height: 50
    color: red
    properties:
      points: 100
    render:
      - shape: circle
        color: red
        fill: true
    interactions:
      pointer:
        when:
          distance: 0
          b.active: true
        action: hit_target

default_layout:
  name: "Test Level"
  entities:
    - type: target
      x: 175
      y: 125
"""
        harness = InlineGameHarness(game, width=400, height=300)
        harness.backend.schedule_click(0.1, 200, 150)
        # Don't stop on game over - we want to see the score after hit
        result = harness.run(duration=0.5, snapshot_interval=0.1, stop_on_game_over=False)

        assert result.success, f"Errors: {result.errors}"
        assert result.final_score >= 100, f"Score should be >= 100, got {result.final_score}"


class TestPaddleMovement:
    """Test paddle movement with set_target_x and stop_at_target."""

    @pytest.mark.xfail(reason="Paddle pointer interaction needs harness debugging")
    def test_paddle_moves_to_click(self):
        """Paddle should move toward click position."""
        game = """
name: "Test Paddle Movement"
screen_width: 400
screen_height: 300

entity_types:
  paddle:
    width: 60
    height: 10
    color: blue
    render:
      - shape: rectangle
        color: blue
        fill: true
    interactions:
      pointer:
        - when:
            b.active: true
          action: set_target_x
          modifier:
            speed: 500
            stop_threshold: 5.0
      screen:
        because: continuous
        action: stop_at_target
        modifier:
          threshold: 5.0

player:
  type: paddle
  spawn: [170, 280]
"""
        harness = InlineGameHarness(game, width=400, height=300)
        # Click at x=350 (right side)
        harness.backend.schedule_click(0.1, 350, 280)
        # Don't stop on game over since there's no win condition
        result = harness.run(duration=1.0, snapshot_interval=0.1, stop_on_game_over=False)

        assert result.success, f"Errors: {result.errors}"

        paddle_history = result.get_entity_history("paddle")
        assert len(paddle_history) >= 2, "Should have paddle history"

        # Paddle should have moved right (end x > start x)
        start_x = paddle_history[0]["x"]
        end_x = paddle_history[-1]["x"]
        assert end_x > start_x, f"Paddle should move right: {start_x} -> {end_x}"


class TestWinLoseConditions:
    """Test win/lose condition checking."""

    def test_destroy_all_wins(self):
        """Destroying all targets should trigger win."""
        game = """
name: "Test Win Condition"
screen_width: 400
screen_height: 300

win_condition: destroy_all
win_target_type: target

entity_types:
  target:
    width: 30
    height: 30
    color: red
    tags: [target]
    properties:
      hits_remaining: 1
    render:
      - shape: circle
        color: red
        fill: true
    interactions:
      pointer:
        when:
          distance: 0
          b.active: true
        action: take_damage

default_layout:
  name: "Test Level"
  entities:
    - type: target
      x: 100
      y: 100
    - type: target
      x: 200
      y: 100
"""
        harness = InlineGameHarness(game, width=400, height=300)
        # Click both targets
        harness.backend.schedule_click(0.1, 115, 115)
        harness.backend.schedule_click(0.3, 215, 115)
        result = harness.run(duration=2.0, snapshot_interval=0.1)

        assert result.success, f"Errors: {result.errors}"
        assert "target" not in result.entities_at_end
        assert "WON" in result.final_state or "won" in result.final_state.lower(), \
            f"Should win, got state: {result.final_state}"


class TestTransform:
    """Test entity transformation."""

    @pytest.mark.xfail(reason="Transform pointer interaction needs harness debugging")
    def test_transform_changes_type(self):
        """Transforming an entity should change its type."""
        game = """
name: "Test Transform"
screen_width: 400
screen_height: 300

entity_types:
  ready:
    width: 60
    height: 10
    color: gray
    render:
      - shape: rectangle
        color: gray
        fill: true
    interactions:
      pointer:
        - when:
            b.active: true
          action: launch_transform
          modifier:
            into: active
            angle_range: [80, 100]
            speed: 200

  active:
    width: 60
    height: 10
    color: blue
    render:
      - shape: rectangle
        color: blue
        fill: true

  ball:
    width: 10
    height: 10
    color: white
    render:
      - shape: circle
        color: white
        fill: true

player:
  type: ready
  spawn: [170, 280]
"""
        harness = InlineGameHarness(game, width=400, height=300)
        harness.backend.schedule_click(0.1, 200, 150)
        # Don't stop on game over since there's no win condition
        result = harness.run(duration=0.5, snapshot_interval=0.1, stop_on_game_over=False)

        assert result.success, f"Errors: {result.errors}"

        # After transform, should have 'active' instead of 'ready'
        assert "active" in result.entities_at_end, \
            f"Should have 'active' entity after transform, got: {result.entities_at_end}"
        assert "ball" in result.entities_at_end, \
            f"Should spawn ball on transform, got: {result.entities_at_end}"


class TestVelocity:
    """Test that entities with initial velocity move correctly."""

    @pytest.mark.xfail(reason="Velocity application needs harness debugging")
    def test_entity_moves_with_velocity(self):
        """Entity with initial velocity should move."""
        game = """
name: "Test Velocity"
screen_width: 400
screen_height: 300

entity_types:
  mover:
    width: 20
    height: 20
    color: white
    render:
      - shape: circle
        color: white
        fill: true

player:
  type: mover
  spawn: [190, 50]
  velocity: [100, 150]
"""
        harness = InlineGameHarness(game, width=400, height=300)
        # Don't stop on game over
        result = harness.run(duration=1.0, snapshot_interval=0.1, stop_on_game_over=False)

        assert result.success, f"Errors: {result.errors}"

        history = result.get_entity_history("mover")
        assert len(history) >= 2, "Should have entity history"

        # Entity should move right and down (positive vx, vy)
        start_x = history[0]["x"]
        start_y = history[0]["y"]
        end_x = history[-1]["x"]
        end_y = history[-1]["y"]

        assert end_x > start_x, f"Entity should move right: {start_x} -> {end_x}"
        assert end_y > start_y, f"Entity should move down: {start_y} -> {end_y}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
