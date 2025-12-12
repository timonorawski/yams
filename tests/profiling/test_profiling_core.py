"""Unit tests for ams/profiling.py core functionality."""
import pytest
import time
from ams import profiling
from ams.profiling import (
    CallNode, FrameProfile, begin_frame, end_frame,
    is_enabled, enable, disable, record_rollback,
    get_frame_buffer, clear_frame_buffer
)


class TestCallNode:
    """Tests for CallNode dataclass."""

    def test_call_node_creation(self):
        node = CallNode(
            id=1,
            parent_id=None,
            label="Test",
            module="test_module",
            func="test_func",
            start=0.0,
        )
        assert node.id == 1
        assert node.parent_id is None
        assert node.duration == 0.0
        assert node.lua_code is False
        assert node.lua_callback is False

    def test_call_node_with_args(self):
        node = CallNode(
            id=2,
            parent_id=1,
            label="ams.set_x",
            module="lua_api",
            func="set_x",
            start=1.5,
            args={"entity_id": "duck_1", "x": 100.0},
            lua_callback=True,
        )
        assert node.args == {"entity_id": "duck_1", "x": 100.0}
        assert node.lua_callback is True

    def test_call_node_with_entity_id(self):
        node = CallNode(
            id=3,
            parent_id=2,
            label="on_update(duck_1)",
            module="lifecycle",
            func="on_entity_update",
            start=0.5,
            entity_id="duck_1",
            lua_code=True,
        )
        assert node.entity_id == "duck_1"
        assert node.lua_code is True


class TestFrameProfile:
    """Tests for FrameProfile dataclass."""

    def test_frame_profile_defaults(self):
        frame = FrameProfile(frame=1, timestamp=1000.0)
        assert frame.calls == []
        assert frame.rollback is None
        assert frame.duration_ms == 0.0

    def test_frame_profile_with_calls(self):
        frame = FrameProfile(
            frame=100,
            timestamp=1000.0,
            duration_ms=16.5,
            calls=[
                CallNode(id=1, parent_id=None, label="Frame", module="engine", func="update", start=0.0)
            ]
        )
        assert len(frame.calls) == 1
        assert frame.duration_ms == 16.5

    def test_frame_profile_with_rollback(self):
        frame = FrameProfile(
            frame=100,
            timestamp=1000.0,
            rollback={
                "triggered": True,
                "frames_resimulated": 5,
                "target_timestamp": 999.9,
                "snapshot_age_ms": 10.0,
            },
        )
        assert frame.rollback["triggered"] is True
        assert frame.rollback["frames_resimulated"] == 5


class TestEnableDisable:
    """Tests for enable/disable functionality."""

    def teardown_method(self):
        disable()
        clear_frame_buffer()

    def test_enable_sets_flag(self):
        disable()
        assert is_enabled() is False
        enable()
        assert is_enabled() is True

    def test_disable_sets_flag(self):
        enable()
        disable()
        assert is_enabled() is False


class TestFrameLifecycle:
    """Tests for begin_frame/end_frame lifecycle."""

    def setup_method(self):
        enable()

    def teardown_method(self):
        disable()
        clear_frame_buffer()

    def test_begin_end_frame_returns_profile(self):
        begin_frame(42)
        result = end_frame()

        assert result is not None
        assert result.frame == 42
        assert result.duration_ms >= 0

    def test_frame_timestamp_is_set(self):
        before = time.time()
        begin_frame(1)
        result = end_frame()
        after = time.time()

        assert before <= result.timestamp <= after

    def test_frame_not_recorded_when_disabled(self):
        disable()
        begin_frame(1)
        result = end_frame()
        assert result is None

    def test_multiple_frames_recorded(self):
        for i in range(5):
            begin_frame(i)
            end_frame()

        buffer = get_frame_buffer()
        assert len(buffer) == 5
        assert [f.frame for f in buffer] == [0, 1, 2, 3, 4]

    def test_frame_buffer_limits(self):
        """Verify frame buffer respects maxlen (60 frames)."""
        for i in range(100):
            begin_frame(i)
            end_frame()

        buffer = get_frame_buffer()
        # Buffer should only keep last 60 frames
        assert len(buffer) == 60
        assert buffer[0].frame == 40  # First kept frame
        assert buffer[-1].frame == 99  # Last frame


class TestRollbackRecording:
    """Tests for rollback event recording."""

    def setup_method(self):
        enable()

    def teardown_method(self):
        disable()
        clear_frame_buffer()

    def test_record_rollback_in_frame(self):
        begin_frame(100)
        record_rollback(
            frames_resimulated=10,
            target_timestamp=1000.0,
            snapshot_age_ms=50.0,
        )
        frame = end_frame()

        assert frame.rollback is not None
        assert frame.rollback["triggered"] is True
        assert frame.rollback["frames_resimulated"] == 10
        assert frame.rollback["target_timestamp"] == 1000.0
        assert frame.rollback["snapshot_age_ms"] == 50.0

    def test_record_rollback_when_disabled(self):
        disable()
        begin_frame(1)
        record_rollback(frames_resimulated=5, target_timestamp=100.0, snapshot_age_ms=10.0)
        # Should not raise, just no-op


class TestClearFrameBuffer:
    """Tests for clearing the frame buffer."""

    def setup_method(self):
        enable()

    def teardown_method(self):
        disable()
        clear_frame_buffer()

    def test_clear_frame_buffer(self):
        for i in range(10):
            begin_frame(i)
            end_frame()

        assert len(get_frame_buffer()) == 10

        clear_frame_buffer()
        assert len(get_frame_buffer()) == 0
