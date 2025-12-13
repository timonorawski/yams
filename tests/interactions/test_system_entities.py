"""Tests for system entities."""

import pytest

from ams.interactions.system_entities import (
    SystemEntities,
    PointerEntity,
    ScreenEntity,
    LevelEntity,
    GameEntity,
    TimeEntity,
    InputType,
    GameState,
)


class TestPointerEntity:
    """Tests for PointerEntity."""

    def test_create_mouse_pointer(self):
        """Mouse pointer has 1x1 bounds."""
        pointer = PointerEntity.create(InputType.MOUSE)
        assert pointer.width == 1
        assert pointer.height == 1
        assert pointer.input_type == InputType.MOUSE

    def test_create_touch_pointer(self):
        """Touch pointer has larger bounds."""
        pointer = PointerEntity.create(InputType.TOUCH)
        assert pointer.width == 40
        assert pointer.height == 40
        assert pointer.input_type == InputType.TOUCH

    def test_create_laser_pointer(self):
        """Laser pointer has medium bounds."""
        pointer = PointerEntity.create(InputType.LASER)
        assert pointer.width == 10
        assert pointer.height == 10

    def test_update_position(self):
        """Update pointer position and active state."""
        pointer = PointerEntity()
        pointer.update(100, 200, active=True)

        assert pointer.x == 100
        assert pointer.y == 200
        assert pointer.active is True

    def test_update_without_active(self):
        """Update position without changing active state."""
        pointer = PointerEntity()
        pointer.active = True
        pointer.update(100, 200)

        assert pointer.x == 100
        assert pointer.y == 200
        assert pointer.active is False  # Default is False

    def test_set_custom_bounds(self):
        """Set custom bounds for object detection."""
        pointer = PointerEntity.create(InputType.OBJECT)
        pointer.set_bounds(50, 30)

        assert pointer.width == 50
        assert pointer.height == 30

    def test_to_dict(self):
        """Convert to dict for interaction context."""
        pointer = PointerEntity.create(InputType.TOUCH)
        pointer.update(100, 200, active=True)

        d = pointer.to_dict()
        assert d["x"] == 100
        assert d["y"] == 200
        assert d["width"] == 40
        assert d["height"] == 40
        assert d["active"] is True
        assert d["input_type"] == "touch"
        assert d["source"] == "system"


class TestScreenEntity:
    """Tests for ScreenEntity."""

    def test_create_default(self):
        """Create screen with default dimensions."""
        screen = ScreenEntity()
        assert screen.width == 800
        assert screen.height == 600

    def test_create_custom(self):
        """Create screen with custom dimensions."""
        screen = ScreenEntity.create(1920, 1080)
        assert screen.width == 1920
        assert screen.height == 1080
        assert screen.x == 0
        assert screen.y == 0

    def test_to_dict(self):
        """Convert to dict for interaction context."""
        screen = ScreenEntity.create(800, 600)
        d = screen.to_dict()

        assert d["x"] == 0
        assert d["y"] == 0
        assert d["width"] == 800
        assert d["height"] == 600
        assert d["source"] == "system"


class TestLevelEntity:
    """Tests for LevelEntity."""

    def test_default_state(self):
        """Default level state."""
        level = LevelEntity()
        assert level.name == ""
        assert level.time == 0.0

    def test_update_time(self):
        """Update level time."""
        level = LevelEntity()
        level.update(0.016)  # ~60fps
        level.update(0.016)

        assert level.time == pytest.approx(0.032)

    def test_reset(self):
        """Reset level state."""
        level = LevelEntity(name="level1", time=10.0)
        level.reset("level2")

        assert level.name == "level2"
        assert level.time == 0.0

    def test_to_dict(self):
        """Convert to dict for interaction context."""
        level = LevelEntity(name="test", time=5.0)
        d = level.to_dict()

        assert d["name"] == "test"
        assert d["time"] == 5.0
        assert d["source"] == "system"


class TestGameEntity:
    """Tests for GameEntity."""

    def test_create_default(self):
        """Create game with default lives."""
        game = GameEntity.create()
        assert game.lives == 3
        assert game.score == 0
        assert game.state == GameState.PLAYING

    def test_create_custom_lives(self):
        """Create game with custom lives."""
        game = GameEntity.create(lives=5)
        assert game.lives == 5

    def test_lose_life(self):
        """Lose a life."""
        game = GameEntity.create(lives=3)
        remaining = game.lose_life()

        assert remaining == 2
        assert game.lives == 2
        assert game.state == GameState.PLAYING

    def test_lose_last_life(self):
        """Losing last life triggers game over."""
        game = GameEntity.create(lives=1)
        remaining = game.lose_life()

        assert remaining == 0
        assert game.lives == 0
        assert game.state == GameState.LOST

    def test_lose_life_doesnt_go_negative(self):
        """Lives can't go below 0."""
        game = GameEntity.create(lives=0)
        game.lose_life()

        assert game.lives == 0

    def test_add_score(self):
        """Add score points."""
        game = GameEntity.create()
        new_score = game.add_score(100)

        assert new_score == 100
        assert game.score == 100

        game.add_score(50)
        assert game.score == 150

    def test_win(self):
        """Set game to won state."""
        game = GameEntity.create()
        game.win()

        assert game.state == GameState.WON

    def test_lose(self):
        """Set game to lost state."""
        game = GameEntity.create()
        game.lose()

        assert game.state == GameState.LOST

    def test_pause_resume(self):
        """Pause and resume game."""
        game = GameEntity.create()
        game.pause()
        assert game.state == GameState.PAUSED

        game.resume()
        assert game.state == GameState.PLAYING

    def test_pause_only_from_playing(self):
        """Can only pause from playing state."""
        game = GameEntity.create()
        game.lose()
        game.pause()

        assert game.state == GameState.LOST  # Unchanged

    def test_resume_only_from_paused(self):
        """Can only resume from paused state."""
        game = GameEntity.create()
        game.lose()
        game.resume()

        assert game.state == GameState.LOST  # Unchanged

    def test_reset(self):
        """Reset game to initial state."""
        game = GameEntity.create(lives=5)
        game.lose_life()
        game.add_score(1000)
        game.reset()

        assert game.lives == 5  # Back to initial
        assert game.score == 0
        assert game.state == GameState.PLAYING

    def test_to_dict(self):
        """Convert to dict for interaction context."""
        game = GameEntity.create(lives=3)
        game.add_score(500)
        d = game.to_dict()

        assert d["lives"] == 3
        assert d["score"] == 500
        assert d["state"] == "playing"
        assert d["source"] == "system"


class TestTimeEntity:
    """Tests for TimeEntity."""

    def test_default_state(self):
        """Default time is 0."""
        time = TimeEntity()
        assert time.elapsed == 0.0
        assert time.absolute == 0.0

    def test_update(self):
        """Update time values."""
        time = TimeEntity()
        time.update(0.5)
        time.update(0.5)

        assert time.elapsed == 1.0
        assert time.absolute == 1.0

    def test_reset_elapsed(self):
        """Reset elapsed time (for new entity)."""
        time = TimeEntity(elapsed=5.0, absolute=10.0)
        time.reset_elapsed()

        assert time.elapsed == 0.0
        assert time.absolute == 10.0

    def test_reset_absolute(self):
        """Reset absolute time (for new level)."""
        time = TimeEntity(elapsed=5.0, absolute=10.0)
        time.reset_absolute()

        assert time.elapsed == 5.0
        assert time.absolute == 0.0

    def test_to_dict(self):
        """Convert to dict for interaction context."""
        time = TimeEntity(elapsed=2.5, absolute=10.0)
        d = time.to_dict()

        assert d["elapsed"] == 2.5
        assert d["absolute"] == 10.0
        assert d["source"] == "system"


class TestSystemEntities:
    """Tests for SystemEntities container."""

    def test_create_default(self):
        """Create with default values."""
        entities = SystemEntities.create()

        assert entities.screen.width == 800
        assert entities.screen.height == 600
        assert entities.game.lives == 3
        assert entities.pointer.input_type == InputType.MOUSE

    def test_create_custom(self):
        """Create with custom configuration."""
        entities = SystemEntities.create(
            screen_width=1920,
            screen_height=1080,
            lives=5,
            input_type=InputType.TOUCH
        )

        assert entities.screen.width == 1920
        assert entities.screen.height == 1080
        assert entities.game.lives == 5
        assert entities.pointer.input_type == InputType.TOUCH

    def test_update_updates_time(self):
        """Update advances time-based entities."""
        entities = SystemEntities.create()
        entities.update(1.0)

        assert entities.level.time == 1.0
        assert entities.time.elapsed == 1.0
        assert entities.time.absolute == 1.0

    def test_get_entity_by_name(self):
        """Get system entity by name."""
        entities = SystemEntities.create()

        assert entities.get_entity("pointer") is entities.pointer
        assert entities.get_entity("screen") is entities.screen
        assert entities.get_entity("level") is entities.level
        assert entities.get_entity("game") is entities.game
        assert entities.get_entity("time") is entities.time

    def test_get_unknown_entity(self):
        """Unknown entity returns None."""
        entities = SystemEntities.create()
        assert entities.get_entity("unknown") is None

    def test_get_entity_dict(self):
        """Get entity as dict for interaction context."""
        entities = SystemEntities.create()
        entities.pointer.update(100, 200, active=True)

        d = entities.get_entity_dict("pointer")
        assert d["x"] == 100
        assert d["y"] == 200
        assert d["active"] is True

    def test_is_system_entity(self):
        """Check if name is a system entity."""
        entities = SystemEntities.create()

        assert entities.is_system_entity("pointer")
        assert entities.is_system_entity("screen")
        assert entities.is_system_entity("level")
        assert entities.is_system_entity("game")
        assert entities.is_system_entity("time")
        assert not entities.is_system_entity("ball")
        assert not entities.is_system_entity("brick")
