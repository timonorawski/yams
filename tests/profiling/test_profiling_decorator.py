"""Tests for @profile decorator and context managers."""
import pytest
import time
from ams import profiling
from ams.profiling import (
    profile, profile_section, profile_lua_callback,
    begin_frame, end_frame, enable, disable, clear_frame_buffer
)


class TestProfileDecorator:
    """Tests for the @profile decorator."""

    def setup_method(self):
        enable()

    def teardown_method(self):
        disable()
        clear_frame_buffer()

    def test_decorator_records_call(self):
        @profile("test_module", "Test Function")
        def my_function():
            time.sleep(0.001)
            return 42

        begin_frame(1)
        result = my_function()
        frame = end_frame()

        assert result == 42
        assert len(frame.calls) == 1
        assert frame.calls[0].label == "Test Function"
        assert frame.calls[0].module == "test_module"
        assert frame.calls[0].func == "my_function"
        assert frame.calls[0].duration > 0

    def test_decorator_uses_default_label(self):
        @profile("test_module")
        def another_function():
            return 1

        begin_frame(1)
        another_function()
        frame = end_frame()

        assert frame.calls[0].label == "test_module.another_function"

    def test_nested_calls_have_parent_ids(self):
        @profile("outer", "Outer")
        def outer():
            inner()

        @profile("inner", "Inner")
        def inner():
            pass

        begin_frame(1)
        outer()
        frame = end_frame()

        assert len(frame.calls) == 2
        outer_call = next(c for c in frame.calls if c.label == "Outer")
        inner_call = next(c for c in frame.calls if c.label == "Inner")
        assert inner_call.parent_id == outer_call.id

    def test_deeply_nested_calls(self):
        @profile("level1", "Level 1")
        def level1():
            level2()

        @profile("level2", "Level 2")
        def level2():
            level3()

        @profile("level3", "Level 3")
        def level3():
            pass

        begin_frame(1)
        level1()
        frame = end_frame()

        assert len(frame.calls) == 3
        l1 = next(c for c in frame.calls if c.label == "Level 1")
        l2 = next(c for c in frame.calls if c.label == "Level 2")
        l3 = next(c for c in frame.calls if c.label == "Level 3")

        assert l1.parent_id is None
        assert l2.parent_id == l1.id
        assert l3.parent_id == l2.id

    def test_decorator_preserves_exceptions(self):
        @profile("test", "Failing")
        def failing_func():
            raise ValueError("test error")

        begin_frame(1)
        with pytest.raises(ValueError, match="test error"):
            failing_func()
        frame = end_frame()

        # Call should still be recorded even on exception
        assert len(frame.calls) == 1
        assert frame.calls[0].label == "Failing"
        assert frame.calls[0].duration > 0

    def test_no_recording_outside_frame(self):
        """Calls outside begin_frame/end_frame are not recorded."""
        @profile("test", "Outside")
        def outside_func():
            return 1

        # Call without frame context
        result = outside_func()
        assert result == 1  # Function still works

    def test_decorator_is_noop_when_disabled(self):
        disable()

        call_count = 0

        @profile("test", "Disabled")
        def tracked_func():
            nonlocal call_count
            call_count += 1
            return 99

        result = tracked_func()
        assert result == 99
        assert call_count == 1  # Function runs but no profiling

    def test_decorator_preserves_return_value(self):
        @profile("test", "Returns Value")
        def returns_dict():
            return {"key": "value", "count": 42}

        begin_frame(1)
        result = returns_dict()
        end_frame()

        assert result == {"key": "value", "count": 42}

    def test_decorator_preserves_kwargs(self):
        @profile("test", "With Kwargs")
        def with_kwargs(a, b=10, c=20):
            return a + b + c

        begin_frame(1)
        result = with_kwargs(1, c=100)
        end_frame()

        assert result == 111


class TestProfileSection:
    """Tests for profile_section context manager."""

    def setup_method(self):
        enable()

    def teardown_method(self):
        disable()
        clear_frame_buffer()

    def test_profile_section_records_call(self):
        begin_frame(1)
        with profile_section("test", "Test Section"):
            time.sleep(0.001)
        frame = end_frame()

        assert len(frame.calls) == 1
        assert frame.calls[0].label == "Test Section"
        assert frame.calls[0].module == "test"
        assert frame.calls[0].duration > 0

    def test_profile_section_with_entity_id(self):
        begin_frame(1)
        with profile_section("lua", "on_update(duck_1)", entity_id="duck_1"):
            pass
        frame = end_frame()

        assert frame.calls[0].entity_id == "duck_1"

    def test_profile_section_with_lua_code_flag(self):
        begin_frame(1)
        with profile_section("lua", "Execute Behavior", lua_code=True):
            pass
        frame = end_frame()

        assert frame.calls[0].lua_code is True

    def test_profile_section_nesting(self):
        begin_frame(1)
        with profile_section("outer", "Outer Section"):
            with profile_section("inner", "Inner Section"):
                pass
        frame = end_frame()

        outer = next(c for c in frame.calls if c.label == "Outer Section")
        inner = next(c for c in frame.calls if c.label == "Inner Section")
        assert inner.parent_id == outer.id

    def test_profile_section_disabled(self):
        disable()
        begin_frame(1)
        with profile_section("test", "Should Not Record"):
            pass
        # No error should occur


class TestProfileLuaCallback:
    """Tests for profile_lua_callback context manager."""

    def setup_method(self):
        enable()

    def teardown_method(self):
        disable()
        clear_frame_buffer()

    def test_profile_lua_callback_records_call(self):
        begin_frame(1)
        with profile_lua_callback("lua_api", "ams.set_x"):
            pass
        frame = end_frame()

        assert len(frame.calls) == 1
        assert frame.calls[0].label == "ams.set_x"
        assert frame.calls[0].lua_callback is True

    def test_profile_lua_callback_with_entity_id(self):
        begin_frame(1)
        with profile_lua_callback("lua_api", "ams.set_vy", entity_id="enemy_1"):
            pass
        frame = end_frame()

        assert frame.calls[0].entity_id == "enemy_1"

    def test_profile_lua_callback_disabled(self):
        disable()
        begin_frame(1)
        with profile_lua_callback("lua_api", "ams.destroy"):
            pass
        # No error should occur


class TestCallTimings:
    """Tests for timing accuracy."""

    def setup_method(self):
        enable()

    def teardown_method(self):
        disable()
        clear_frame_buffer()

    def test_call_start_time_relative_to_frame(self):
        @profile("test", "Delayed Start")
        def delayed():
            pass

        begin_frame(1)
        time.sleep(0.005)  # 5ms delay before call
        delayed()
        frame = end_frame()

        # Start time should be ~5ms (relative to frame start)
        assert frame.calls[0].start >= 4.0  # At least 4ms
        assert frame.calls[0].start < 20.0  # But not too much

    def test_frame_duration_includes_all_calls(self):
        @profile("test", "Work")
        def do_work():
            time.sleep(0.005)

        begin_frame(1)
        do_work()
        do_work()
        frame = end_frame()

        # Frame should be at least 10ms (2 x 5ms)
        assert frame.duration_ms >= 8.0  # Allow some tolerance
