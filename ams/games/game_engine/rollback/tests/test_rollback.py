"""
Unit tests for rollback state management.

Tests snapshot capture, restoration, and re-simulation without
requiring the full game engine or Lua environment.
"""

import time
import pytest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from ams.games.game_engine.rollback import (
    RollbackStateManager,
    EntitySnapshot,
    GameSnapshot,
    ScheduledCallbackSnapshot,
)


# =============================================================================
# Mock Classes for Testing
# =============================================================================

class GameState(Enum):
    """Mock game state enum."""
    PLAYING = "playing"
    PAUSED = "paused"
    WON = "won"
    GAME_OVER = "game_over"


@dataclass
class MockScheduledCallback:
    """Mock scheduled callback."""
    time_remaining: float
    callback_name: str
    entity_id: str


@dataclass
class MockEntity:
    """Mock entity for testing (mirrors GameEntity structure)."""
    id: str
    entity_type: str = "test"
    alive: bool = True

    # Transform
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    width: float = 32.0
    height: float = 32.0

    # Visual
    color: str = "white"
    sprite: str = ""
    visible: bool = True

    # State
    health: int = 1
    spawn_time: float = 0.0

    # Tags and properties
    tags: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

    # Hierarchy
    parent_id: Optional[str] = None
    parent_offset: tuple = (0.0, 0.0)
    children: List[str] = field(default_factory=list)

    # Behaviors
    behaviors: List[str] = field(default_factory=list)
    behavior_config: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Lifecycle dispatch (ignored in mock)
    _lifecycle_dispatch: Any = None


class MockLuaEngine:
    """Mock Lua engine for testing."""

    def __init__(self):
        self.entities: Dict[str, MockEntity] = {}
        self.elapsed_time: float = 0.0
        self.score: int = 0
        self._scheduled: List[MockScheduledCallback] = []

    def add_entity(self, entity: MockEntity) -> None:
        """Add an entity."""
        self.entities[entity.id] = entity

    def remove_entity(self, entity_id: str) -> None:
        """Remove an entity."""
        if entity_id in self.entities:
            del self.entities[entity_id]


class MockGameEngine:
    """Mock game engine for testing rollback."""

    def __init__(self):
        self._behavior_engine = MockLuaEngine()
        self._internal_state = GameState.PLAYING
        self._lives = 3
        self._frame_updates = 0

    def _do_frame_update(self, dt: float) -> None:
        """Simulate one frame of game logic."""
        self._frame_updates += 1
        self._behavior_engine.elapsed_time += dt

        # Simple physics: update positions based on velocity
        for entity in self._behavior_engine.entities.values():
            if entity.alive:
                entity.x += entity.vx * dt
                entity.y += entity.vy * dt

        # Update scheduled callbacks
        for cb in self._behavior_engine._scheduled[:]:
            cb.time_remaining -= dt
            if cb.time_remaining <= 0:
                self._behavior_engine._scheduled.remove(cb)

    def _dispatch_lifecycle(self, entity, hook_name):
        """Mock lifecycle dispatch."""
        pass


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def manager():
    """Create a rollback manager with test settings."""
    return RollbackStateManager(
        history_duration=2.0,
        fps=60,
        snapshot_interval=1,
    )


@pytest.fixture
def game_engine():
    """Create a mock game engine."""
    return MockGameEngine()


@pytest.fixture
def game_with_entities(game_engine):
    """Create a game engine with some test entities."""
    lua = game_engine._behavior_engine

    # Add a few entities
    lua.add_entity(MockEntity(
        id="player",
        entity_type="player",
        x=100.0,
        y=200.0,
        vx=50.0,
        vy=0.0,
        health=3,
    ))

    lua.add_entity(MockEntity(
        id="enemy_1",
        entity_type="enemy",
        x=400.0,
        y=100.0,
        vx=-30.0,
        vy=10.0,
        properties={"damage": 10, "patrol_points": [1, 2, 3]},
    ))

    lua.add_entity(MockEntity(
        id="brick_1",
        entity_type="brick",
        x=300.0,
        y=50.0,
        tags=["brick", "destructible"],
        properties={"hits_remaining": 2},
    ))

    return game_engine


# =============================================================================
# EntitySnapshot Tests
# =============================================================================

class TestEntitySnapshot:
    """Tests for EntitySnapshot."""

    def test_from_entity_basic(self):
        """Test creating snapshot from entity."""
        entity = MockEntity(
            id="test_1",
            entity_type="test",
            x=100.0,
            y=200.0,
            health=5,
        )

        snapshot = EntitySnapshot.from_entity(entity)

        assert snapshot.id == "test_1"
        assert snapshot.entity_type == "test"
        assert snapshot.x == 100.0
        assert snapshot.y == 200.0
        assert snapshot.health == 5
        assert snapshot.alive is True

    def test_from_entity_with_properties(self):
        """Test snapshot preserves properties."""
        entity = MockEntity(
            id="test_2",
            properties={"score": 100, "nested": {"a": 1, "b": 2}},
        )

        snapshot = EntitySnapshot.from_entity(entity)

        assert snapshot.properties["score"] == 100
        assert snapshot.properties["nested"]["a"] == 1

    def test_properties_are_deep_copied(self):
        """Test that properties are deep copied, not shared."""
        entity = MockEntity(
            id="test_3",
            properties={"list": [1, 2, 3], "dict": {"key": "value"}},
        )

        snapshot = EntitySnapshot.from_entity(entity)

        # Modify original
        entity.properties["list"].append(4)
        entity.properties["dict"]["key"] = "changed"

        # Snapshot should be unchanged
        assert snapshot.properties["list"] == [1, 2, 3]
        assert snapshot.properties["dict"]["key"] == "value"

    def test_apply_to_restores_state(self):
        """Test applying snapshot restores entity state."""
        original = MockEntity(
            id="test_4",
            x=100.0,
            y=200.0,
            vx=50.0,
            health=3,
            properties={"counter": 10},
        )

        snapshot = EntitySnapshot.from_entity(original)

        # Modify entity
        original.x = 500.0
        original.health = 1
        original.properties["counter"] = 99

        # Restore from snapshot
        snapshot.apply_to(original)

        assert original.x == 100.0
        assert original.health == 3
        assert original.properties["counter"] == 10

    def test_tags_converted_to_tuple(self):
        """Test tags are stored as immutable tuple."""
        entity = MockEntity(
            id="test_5",
            tags=["a", "b", "c"],
        )

        snapshot = EntitySnapshot.from_entity(entity)

        assert isinstance(snapshot.tags, tuple)
        assert snapshot.tags == ("a", "b", "c")


# =============================================================================
# GameSnapshot Tests
# =============================================================================

class TestGameSnapshot:
    """Tests for GameSnapshot."""

    def test_entity_count(self):
        """Test entity_count property."""
        snapshot = GameSnapshot(
            frame_number=0,
            elapsed_time=0.0,
            timestamp=time.monotonic(),
            entities={
                "a": EntitySnapshot.from_entity(MockEntity(id="a")),
                "b": EntitySnapshot.from_entity(MockEntity(id="b")),
            },
        )

        assert snapshot.entity_count == 2

    def test_alive_entity_count(self):
        """Test alive_entity_count with mixed alive/dead."""
        alive_entity = MockEntity(id="alive", alive=True)
        dead_entity = MockEntity(id="dead", alive=False)

        snapshot = GameSnapshot(
            frame_number=0,
            elapsed_time=0.0,
            timestamp=time.monotonic(),
            entities={
                "alive": EntitySnapshot.from_entity(alive_entity),
                "dead": EntitySnapshot.from_entity(dead_entity),
            },
        )

        assert snapshot.alive_entity_count == 1

    def test_get_entity(self):
        """Test get_entity retrieval."""
        entity = MockEntity(id="target", x=50.0)

        snapshot = GameSnapshot(
            frame_number=0,
            elapsed_time=0.0,
            timestamp=time.monotonic(),
            entities={"target": EntitySnapshot.from_entity(entity)},
        )

        retrieved = snapshot.get_entity("target")
        assert retrieved is not None
        assert retrieved.x == 50.0

        assert snapshot.get_entity("nonexistent") is None


# =============================================================================
# RollbackStateManager Tests
# =============================================================================

class TestRollbackStateManager:
    """Tests for RollbackStateManager."""

    def test_initial_state(self, manager):
        """Test manager starts empty."""
        assert manager.snapshot_count == 0
        assert manager.oldest_timestamp is None
        assert manager.newest_timestamp is None

    def test_capture_adds_snapshot(self, manager, game_engine):
        """Test capturing snapshots."""
        manager.capture(game_engine)

        assert manager.snapshot_count == 1
        assert manager.oldest_timestamp is not None

    def test_capture_respects_interval(self, game_engine):
        """Test snapshot interval is respected."""
        manager = RollbackStateManager(
            history_duration=1.0,
            fps=60,
            snapshot_interval=3,  # Every 3 frames
        )

        # Capture 10 frames
        for _ in range(10):
            manager.capture(game_engine)

        # Should have captured frames 3, 6, 9 = 3 snapshots
        # (frame 1, 2 skip; frame 3 capture; frame 4, 5 skip; frame 6 capture; etc.)
        assert manager.snapshot_count == 3

    def test_force_capture_ignores_interval(self, game_engine):
        """Test force=True captures regardless of interval."""
        manager = RollbackStateManager(
            history_duration=1.0,
            fps=60,
            snapshot_interval=10,
        )

        manager.capture(game_engine, force=True)
        manager.capture(game_engine, force=True)

        assert manager.snapshot_count == 2

    def test_max_snapshots_respected(self, game_engine):
        """Test old snapshots are evicted when buffer is full."""
        manager = RollbackStateManager(
            history_duration=0.1,  # Small window
            fps=10,  # = 1 snapshot max
            snapshot_interval=1,
        )

        manager.capture(game_engine, force=True)
        first_timestamp = manager.oldest_timestamp

        time.sleep(0.01)  # Ensure different timestamp
        manager.capture(game_engine, force=True)

        # Should still have only 1 snapshot (the newer one)
        assert manager.snapshot_count == 1
        assert manager.oldest_timestamp != first_timestamp

    def test_can_rollback_to(self, manager, game_engine):
        """Test can_rollback_to check."""
        assert not manager.can_rollback_to(time.monotonic())

        manager.capture(game_engine)
        capture_time = manager.newest_timestamp

        # Can rollback to capture time
        assert manager.can_rollback_to(capture_time)

        # Cannot rollback to before oldest snapshot
        assert not manager.can_rollback_to(capture_time - 1000)

    def test_find_snapshot_exact(self, manager, game_engine):
        """Test finding snapshot at exact timestamp."""
        manager.capture(game_engine)
        capture_time = manager.newest_timestamp

        found = manager.find_snapshot(capture_time)
        assert found is not None
        assert found.timestamp == capture_time

    def test_find_snapshot_before(self, manager, game_engine):
        """Test finding snapshot before requested time."""
        manager.capture(game_engine)
        capture_time = manager.newest_timestamp

        # Request time slightly after capture
        found = manager.find_snapshot(capture_time + 0.1)
        assert found is not None
        assert found.timestamp == capture_time

    def test_find_snapshot_none_before(self, manager, game_engine):
        """Test no snapshot found when request is before all snapshots."""
        manager.capture(game_engine)
        capture_time = manager.newest_timestamp

        # Request time before capture
        found = manager.find_snapshot(capture_time - 1.0)
        assert found is None


class TestRollbackRestore:
    """Tests for state restoration."""

    def test_restore_entity_positions(self, manager, game_with_entities):
        """Test restoring entity positions."""
        lua = game_with_entities._behavior_engine
        player = lua.entities["player"]

        # Capture initial state
        manager.capture(game_with_entities)
        snapshot = manager.find_snapshot(time.monotonic())

        initial_x = player.x

        # Move player
        player.x = 999.0
        player.y = 888.0

        # Restore
        manager.restore(game_with_entities, snapshot)

        assert player.x == initial_x

    def test_restore_score(self, manager, game_with_entities):
        """Test restoring score."""
        lua = game_with_entities._behavior_engine

        lua.score = 100
        manager.capture(game_with_entities)
        snapshot = manager.find_snapshot(time.monotonic())

        lua.score = 9999

        manager.restore(game_with_entities, snapshot)

        assert lua.score == 100

    def test_restore_lives(self, manager, game_with_entities):
        """Test restoring lives."""
        game_with_entities._lives = 5
        manager.capture(game_with_entities)
        snapshot = manager.find_snapshot(time.monotonic())

        game_with_entities._lives = 0

        manager.restore(game_with_entities, snapshot)

        assert game_with_entities._lives == 5

    def test_restore_removes_new_entities(self, manager, game_with_entities):
        """Test entities created after snapshot are removed on restore."""
        lua = game_with_entities._behavior_engine

        manager.capture(game_with_entities)
        snapshot = manager.find_snapshot(time.monotonic())

        # Add new entity after snapshot
        lua.add_entity(MockEntity(id="new_entity"))
        assert "new_entity" in lua.entities

        # Restore
        manager.restore(game_with_entities, snapshot)

        assert "new_entity" not in lua.entities

    def test_restore_recreates_removed_entities(self, manager, game_with_entities):
        """Test entities removed after snapshot are recreated on restore."""
        lua = game_with_entities._behavior_engine

        manager.capture(game_with_entities)
        snapshot = manager.find_snapshot(time.monotonic())

        # Remove entity after snapshot
        lua.remove_entity("brick_1")
        assert "brick_1" not in lua.entities

        # Restore
        manager.restore(game_with_entities, snapshot)

        assert "brick_1" in lua.entities

    def test_restore_entity_properties(self, manager, game_with_entities):
        """Test entity properties are restored."""
        lua = game_with_entities._behavior_engine
        enemy = lua.entities["enemy_1"]

        manager.capture(game_with_entities)
        snapshot = manager.find_snapshot(time.monotonic())

        # Modify properties
        enemy.properties["damage"] = 999

        manager.restore(game_with_entities, snapshot)

        assert enemy.properties["damage"] == 10


class TestResimulation:
    """Tests for re-simulation after rollback."""

    def test_resimulate_advances_time(self, manager, game_with_entities):
        """Test re-simulation advances elapsed time."""
        lua = game_with_entities._behavior_engine

        manager.capture(game_with_entities, force=True)
        snapshot_time = manager.newest_timestamp
        initial_elapsed = lua.elapsed_time

        # Simulate 0.5 seconds passing
        time.sleep(0.01)  # Small real delay
        current_time = snapshot_time + 0.5  # Pretend 0.5s passed

        hit_applied = [False]

        def apply_hit():
            hit_applied[0] = True

        result = manager.rollback_and_resimulate(
            game_with_entities,
            target_timestamp=snapshot_time,
            hit_applicator=apply_hit,
            current_timestamp=current_time,
        )

        assert result.success
        assert hit_applied[0]
        assert result.frames_resimulated > 0
        # Elapsed time should have advanced
        assert lua.elapsed_time > initial_elapsed

    def test_resimulate_moves_entities(self, manager, game_with_entities):
        """Test re-simulation applies physics."""
        lua = game_with_entities._behavior_engine
        player = lua.entities["player"]

        # Player has vx=50, so should move right during resim
        initial_x = player.x

        manager.capture(game_with_entities, force=True)
        snapshot_time = manager.newest_timestamp

        # Pretend 1 second passed
        current_time = snapshot_time + 1.0

        result = manager.rollback_and_resimulate(
            game_with_entities,
            target_timestamp=snapshot_time,
            hit_applicator=lambda: None,
            current_timestamp=current_time,
        )

        # Player should have moved (vx=50 for ~1 second)
        assert player.x > initial_x
        # Should be approximately initial_x + 50 * 1.0 = initial_x + 50
        assert abs(player.x - (initial_x + 50)) < 5  # Allow small variance

    def test_rollback_fails_without_snapshot(self, manager, game_engine):
        """Test rollback fails gracefully when no snapshot available."""
        result = manager.rollback_and_resimulate(
            game_engine,
            target_timestamp=time.monotonic() - 100,  # Way in the past
            hit_applicator=lambda: None,
        )

        assert not result.success
        assert result.error is not None


class TestRollbackRoundTrip:
    """Integration tests for full rollback scenarios."""

    def test_full_rollback_scenario(self, manager, game_with_entities):
        """Test complete rollback scenario with delayed hit."""
        lua = game_with_entities._behavior_engine
        brick = lua.entities["brick_1"]

        # === Frame 0: Initial state ===
        manager.capture(game_with_entities, force=True)
        t0 = manager.newest_timestamp
        brick_initial_x = brick.x

        # === Frames 1-30: Game advances (0.5 seconds) ===
        for _ in range(30):
            game_with_entities._do_frame_update(1/60)
            manager.capture(game_with_entities)

        # Brick is still there
        assert brick.alive

        # === Delayed hit arrives ===
        # Hit actually occurred at t0, but we're just now receiving it

        def apply_delayed_hit():
            # This simulates what would happen when processing the hit
            # In real code, this would call input handling
            brick.alive = False
            brick.health = 0
            lua.score += 100

        result = manager.rollback_and_resimulate(
            game_with_entities,
            target_timestamp=t0,
            hit_applicator=apply_delayed_hit,
            current_timestamp=time.monotonic(),
        )

        # === Verify result ===
        assert result.success
        assert result.frames_resimulated > 0

        # Brick should be destroyed (hit was applied)
        assert not brick.alive

        # Score should be updated
        assert lua.score == 100

    def test_multiple_snapshots_find_correct_one(self, manager, game_engine):
        """Test finding correct snapshot among many."""
        timestamps = []

        # Capture 10 snapshots with delays
        for i in range(10):
            manager.capture(game_engine, force=True)
            timestamps.append(manager.newest_timestamp)
            time.sleep(0.001)  # Small delay to ensure different timestamps

        # Find snapshot for middle timestamp
        middle_idx = 5
        found = manager.find_snapshot(timestamps[middle_idx])

        assert found is not None
        assert found.timestamp == timestamps[middle_idx]

    def test_snapshot_between_captures(self, manager, game_engine):
        """Test finding snapshot when target is between capture times."""
        manager.capture(game_engine, force=True)
        t1 = manager.newest_timestamp

        time.sleep(0.01)

        manager.capture(game_engine, force=True)
        t2 = manager.newest_timestamp

        # Request time between t1 and t2
        between = (t1 + t2) / 2
        found = manager.find_snapshot(between)

        # Should find t1 (the one before requested time)
        assert found is not None
        assert found.timestamp == t1


class TestStatistics:
    """Tests for manager statistics."""

    def test_get_stats(self, manager, game_engine):
        """Test statistics reporting."""
        for _ in range(5):
            manager.capture(game_engine, force=True)

        stats = manager.get_stats()

        assert stats['snapshot_count'] == 5
        assert stats['total_captures'] == 5
        assert stats['total_rollbacks'] == 0
        assert stats['frame_counter'] == 5

    def test_rollback_increments_counter(self, manager, game_engine):
        """Test rollback counter is incremented."""
        manager.capture(game_engine, force=True)
        t = manager.newest_timestamp

        manager.rollback_and_resimulate(
            game_engine,
            target_timestamp=t,
            hit_applicator=lambda: None,
        )

        stats = manager.get_stats()
        assert stats['total_rollbacks'] == 1

    def test_clear_resets_state(self, manager, game_engine):
        """Test clear removes all snapshots."""
        for _ in range(5):
            manager.capture(game_engine, force=True)

        manager.clear()

        assert manager.snapshot_count == 0
        assert manager.oldest_timestamp is None


# =============================================================================
# Logger Tests
# =============================================================================

from ams.games.game_engine.rollback import (
    GameStateLogger,
    NullLogger,
    create_logger,
    load_log,
    summarize_log,
)
import ams.logging as ams_logging


@pytest.fixture
def clean_sinks():
    """Clean up sinks before and after tests."""
    ams_logging.close_all_sinks()
    ams_logging._config['modules'] = {}
    yield
    ams_logging.close_all_sinks()
    ams_logging._config['modules'] = {}


@pytest.fixture
def file_sink_for_test(tmp_path, clean_sinks):
    """Set up a FileSink for testing."""
    sink = ams_logging.FileSink(
        log_dir=str(tmp_path),
        session_name="test_session",
    )
    ams_logging.register_sink('rollback', sink)
    yield sink
    sink.close()


class TestGameStateLogger:
    """Tests for GameStateLogger."""

    def test_logs_to_sink(self, file_sink_for_test, game_engine, manager):
        """Test logger emits records to sink."""
        logger = GameStateLogger(session_name="test_session")
        snapshot = manager.capture(game_engine, force=True)
        logger.log_snapshot(snapshot)
        logger.close()

        # Check sink received records
        file_sink_for_test.flush()
        log_paths = file_sink_for_test.log_paths
        assert 'rollback' in log_paths

    def test_writes_header(self, file_sink_for_test):
        """Test logger writes header as first record."""
        logger = GameStateLogger(session_name="test")
        logger.close()
        file_sink_for_test.close()

        # Find the log file
        log_dir = file_sink_for_test._log_dir
        log_file = log_dir / "test_session_rollback.jsonl"

        records = load_log(str(log_file))
        # First record is sink header, second is logger header
        headers = [r for r in records if r.get("type") == "header"]
        assert len(headers) >= 1
        logger_header = [h for h in headers if h.get("session_name") == "test"]
        assert len(logger_header) == 1

    def test_writes_footer(self, file_sink_for_test):
        """Test logger writes footer on close."""
        logger = GameStateLogger(session_name="test")
        logger.close()
        file_sink_for_test.close()

        log_dir = file_sink_for_test._log_dir
        log_file = log_dir / "test_session_rollback.jsonl"

        records = load_log(str(log_file))
        footers = [r for r in records if r.get("type") == "footer"]
        assert len(footers) >= 1

    def test_log_snapshot(self, file_sink_for_test, game_engine, manager):
        """Test logging a snapshot."""
        logger = GameStateLogger()
        snapshot = manager.capture(game_engine, force=True)
        logger.log_snapshot(snapshot)
        logger.close()
        file_sink_for_test.close()

        log_dir = file_sink_for_test._log_dir
        log_file = log_dir / "test_session_rollback.jsonl"

        records = load_log(str(log_file))
        snapshots = [r for r in records if r.get("type") == "snapshot"]

        assert len(snapshots) == 1
        assert "frame_number" in snapshots[0]
        assert "elapsed_time" in snapshots[0]
        assert "score" in snapshots[0]

    def test_log_interval(self, file_sink_for_test, game_engine, manager):
        """Test log_interval skips snapshots."""
        logger = GameStateLogger(log_interval=3)  # Log every 3rd snapshot
        for _ in range(9):
            snapshot = manager.capture(game_engine, force=True)
            logger.log_snapshot(snapshot)
        logger.close()
        file_sink_for_test.close()

        log_dir = file_sink_for_test._log_dir
        log_file = log_dir / "test_session_rollback.jsonl"

        records = load_log(str(log_file))
        snapshots = [r for r in records if r.get("type") == "snapshot"]

        # Should have logged snapshots 3, 6, 9 = 3 total
        assert len(snapshots) == 3

    def test_log_entities(self, file_sink_for_test, game_with_entities, manager):
        """Test entities are included in snapshot."""
        logger = GameStateLogger(include_entities=True)
        snapshot = manager.capture(game_with_entities, force=True)
        logger.log_snapshot(snapshot)
        logger.close()
        file_sink_for_test.close()

        log_dir = file_sink_for_test._log_dir
        log_file = log_dir / "test_session_rollback.jsonl"

        records = load_log(str(log_file))
        snapshots = [r for r in records if r.get("type") == "snapshot"]

        assert "entities" in snapshots[0]
        assert "player" in snapshots[0]["entities"]
        assert snapshots[0]["entities"]["player"]["x"] == 100.0

    def test_log_without_entities(self, file_sink_for_test, game_with_entities, manager):
        """Test entities can be excluded."""
        logger = GameStateLogger(include_entities=False)
        snapshot = manager.capture(game_with_entities, force=True)
        logger.log_snapshot(snapshot)
        logger.close()
        file_sink_for_test.close()

        log_dir = file_sink_for_test._log_dir
        log_file = log_dir / "test_session_rollback.jsonl"

        records = load_log(str(log_file))
        snapshots = [r for r in records if r.get("type") == "snapshot"]

        assert "entities" not in snapshots[0]
        assert "entity_count" in snapshots[0]  # Summary still present

    def test_log_rollback_event(self, file_sink_for_test):
        """Test logging rollback events."""
        logger = GameStateLogger()
        logger.log_rollback(
            target_timestamp=1000.0,
            restored_frame=50,
            frames_resimulated=30,
            hit_position=(0.5, 0.5),
        )
        logger.close()
        file_sink_for_test.close()

        log_dir = file_sink_for_test._log_dir
        log_file = log_dir / "test_session_rollback.jsonl"

        records = load_log(str(log_file))
        rollbacks = [r for r in records if r.get("type") == "rollback"]

        assert len(rollbacks) == 1
        assert rollbacks[0]["restored_frame"] == 50
        assert rollbacks[0]["frames_resimulated"] == 30
        assert rollbacks[0]["hit_position"] == [0.5, 0.5]

    def test_log_custom_event(self, file_sink_for_test):
        """Test logging custom events."""
        logger = GameStateLogger()
        logger.log_event("hit_detected", {"x": 100, "y": 200, "entity": "brick_1"})
        logger.close()
        file_sink_for_test.close()

        log_dir = file_sink_for_test._log_dir
        log_file = log_dir / "test_session_rollback.jsonl"

        records = load_log(str(log_file))
        custom = [r for r in records if r.get("type") == "hit_detected"]

        assert len(custom) == 1
        assert custom[0]["x"] == 100
        assert custom[0]["entity"] == "brick_1"

    def test_stats(self, file_sink_for_test, game_engine, manager):
        """Test stats property."""
        logger = GameStateLogger()
        for _ in range(5):
            snapshot = manager.capture(game_engine, force=True)
            logger.log_snapshot(snapshot)

        stats = logger.stats
        assert stats["total_snapshots"] == 5
        assert stats["logged_snapshots"] == 5
        logger.close()


class TestLogAnalysis:
    """Tests for log analysis utilities."""

    def test_summarize_log(self, file_sink_for_test, game_with_entities, manager):
        """Test log summary generation."""
        logger = GameStateLogger()

        # Log some snapshots
        for i in range(10):
            game_with_entities._behavior_engine.score = i * 10
            snapshot = manager.capture(game_with_entities, force=True)
            logger.log_snapshot(snapshot)

        # Log a rollback
        logger.log_rollback(
            target_timestamp=1000.0,
            restored_frame=5,
            frames_resimulated=20,
        )

        logger.close()
        file_sink_for_test.close()

        log_dir = file_sink_for_test._log_dir
        log_file = log_dir / "test_session_rollback.jsonl"

        summary = summarize_log(str(log_file))

        assert summary["logged_snapshots"] == 10
        assert summary["rollback_count"] == 1
        assert summary["total_frames_resimulated"] == 20
        assert summary["final_score"] == 90


class TestNullLogger:
    """Tests for NullLogger (disabled logging)."""

    def test_null_logger_methods_are_noop(self):
        """Test NullLogger methods don't raise errors."""
        logger = NullLogger()

        # These should all be no-ops
        assert logger.log_snapshot(None) is False
        logger.log_rollback(1.0, 10, 5)
        logger.log_event("test", {"foo": "bar"})
        logger.flush()
        logger.close()

    def test_null_logger_properties(self):
        """Test NullLogger property values."""
        logger = NullLogger()

        assert logger.log_path is None
        assert logger.stats == {"enabled": False}

    def test_null_logger_context_manager(self):
        """Test NullLogger works as context manager."""
        with NullLogger() as logger:
            logger.log_event("test", {})
        # Should not raise


class TestCreateLogger:
    """Tests for create_logger factory."""

    def test_create_logger_disabled_by_default(self, clean_sinks):
        """Test create_logger returns NullLogger when not enabled."""
        logger = create_logger()
        assert isinstance(logger, NullLogger)

    def test_create_logger_force_bypasses_config(self, tmp_path, clean_sinks):
        """Test force=True creates logger even when disabled."""
        # Set up a sink for the module
        sink = ams_logging.FileSink(log_dir=str(tmp_path), session_name="test")
        ams_logging.register_sink('rollback', sink)

        logger = create_logger(force=True)
        try:
            assert isinstance(logger, GameStateLogger)
        finally:
            logger.close()
            sink.close()

    def test_create_logger_respects_interval_config(self, tmp_path, clean_sinks):
        """Test create_logger uses interval from config."""
        ams_logging._config['modules']['rollback'] = {'enabled': True, 'interval': 5}

        # Note: create_logger will create its own sink when enabled
        logger = create_logger(session_name="test")
        try:
            assert isinstance(logger, GameStateLogger)
            assert logger.log_interval == 5
        finally:
            logger.close()
            ams_logging.close_all_sinks()


# =============================================================================
# Sink Tests
# =============================================================================

class TestFileSink:
    """Tests for FileSink."""

    def test_creates_log_directory(self, tmp_path):
        """Test FileSink creates log directory."""
        log_dir = tmp_path / "logs"
        sink = ams_logging.FileSink(log_dir=str(log_dir))

        sink.emit("test_module", {"type": "test", "data": 123})
        sink.close()

        assert log_dir.exists()

    def test_writes_jsonl(self, tmp_path):
        """Test FileSink writes valid JSONL."""
        sink = ams_logging.FileSink(log_dir=str(tmp_path), session_name="test")

        sink.emit("mymodule", {"type": "event", "value": 42})
        sink.emit("mymodule", {"type": "event", "value": 43})
        sink.close()

        log_file = tmp_path / "test_mymodule.jsonl"
        assert log_file.exists()

        records = load_log(str(log_file))
        # Should have header, 2 events, footer
        assert len(records) == 4
        events = [r for r in records if r.get("type") == "event"]
        assert len(events) == 2
        assert events[0]["value"] == 42
        assert events[1]["value"] == 43

    def test_separate_files_per_module(self, tmp_path):
        """Test different modules get separate files."""
        sink = ams_logging.FileSink(log_dir=str(tmp_path), session_name="test")

        sink.emit("module_a", {"type": "test"})
        sink.emit("module_b", {"type": "test"})
        sink.close()

        assert (tmp_path / "test_module_a.jsonl").exists()
        assert (tmp_path / "test_module_b.jsonl").exists()


class TestNullSink:
    """Tests for NullSink."""

    def test_null_sink_is_noop(self):
        """Test NullSink does nothing."""
        sink = ams_logging.NullSink()

        # These should all be no-ops
        sink.emit("test", {"data": 123})
        sink.flush()
        sink.close()
        # No assertions needed - just shouldn't raise


class TestSinkRegistry:
    """Tests for sink registry functions."""

    def test_register_and_get_sink(self, tmp_path, clean_sinks):
        """Test registering and retrieving sinks."""
        sink = ams_logging.FileSink(log_dir=str(tmp_path))
        ams_logging.register_sink("test_module", sink)

        retrieved = ams_logging.get_sink("test_module")
        assert retrieved is sink

        sink.close()

    def test_default_sink(self, tmp_path, clean_sinks):
        """Test default sink fallback."""
        default_sink = ams_logging.FileSink(log_dir=str(tmp_path))
        ams_logging.set_default_sink(default_sink)

        # Should get default for unknown module
        retrieved = ams_logging.get_sink("unknown_module")
        assert retrieved is default_sink

        default_sink.close()

    def test_emit_record(self, tmp_path, clean_sinks):
        """Test emit_record dispatches to correct sink."""
        sink = ams_logging.FileSink(log_dir=str(tmp_path), session_name="test")
        ams_logging.register_sink("test_module", sink)

        result = ams_logging.emit_record("test_module", {"type": "test", "value": 99})
        assert result is True

        sink.close()

        log_file = tmp_path / "test_test_module.jsonl"
        records = load_log(str(log_file))
        test_records = [r for r in records if r.get("type") == "test"]
        assert len(test_records) == 1
        assert test_records[0]["value"] == 99

    def test_emit_record_no_sink(self, clean_sinks):
        """Test emit_record returns False when no sink available."""
        result = ams_logging.emit_record("no_sink_module", {"data": 123})
        assert result is False


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
