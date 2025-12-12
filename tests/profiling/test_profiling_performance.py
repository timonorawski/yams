"""Performance tests to verify profiling overhead."""
import pytest
import time
from ams import profiling
from ams.profiling import (
    profile, begin_frame, end_frame,
    enable, disable, clear_frame_buffer
)


class TestProfilingOverhead:
    """Verify profiling overhead stays within acceptable limits."""

    def teardown_method(self):
        disable()
        clear_frame_buffer()

    def test_disabled_overhead_is_negligible(self):
        """When disabled, decorators should have negligible overhead."""
        disable()

        @profile("test", "Test")
        def fast_func():
            return sum(range(100))

        # Warm up
        for _ in range(1000):
            fast_func()

        # Measure
        start = time.perf_counter()
        for _ in range(10000):
            fast_func()
        elapsed = time.perf_counter() - start

        # Should be very fast (< 100ms for 10000 calls)
        # This is a very generous bound - mainly checking no major regression
        assert elapsed < 0.5, f"Disabled profiling overhead too high: {elapsed}s for 10000 calls"

    def test_enabled_overhead_acceptable(self):
        """When enabled, overhead should be reasonable per frame."""
        enable()

        @profile("test", "Test Work")
        def simulated_work():
            # Simulate some work (~0.5ms)
            total = 0
            for i in range(1000):
                total += i
            return total

        # Measure frame overhead
        frame_times = []
        work_times = []

        for i in range(100):
            begin_frame(i)

            work_start = time.perf_counter()
            simulated_work()
            work_time = time.perf_counter() - work_start
            work_times.append(work_time)

            frame = end_frame()
            frame_times.append(frame.duration_ms / 1000)

        avg_work = sum(work_times) / len(work_times)
        avg_frame = sum(frame_times) / len(frame_times)
        avg_overhead = avg_frame - avg_work

        # Overhead should be < 0.5ms per frame (generous for CI variability)
        assert avg_overhead < 0.0005, f"Profiling overhead too high: {avg_overhead*1000:.3f}ms per frame"

    def test_many_calls_per_frame(self):
        """Test overhead with many profiled calls per frame."""
        enable()

        @profile("test", "Quick Call")
        def quick_call():
            return 1

        begin_frame(1)
        start = time.perf_counter()

        # Make 1000 profiled calls in one frame
        for _ in range(1000):
            quick_call()

        elapsed = time.perf_counter() - start
        frame = end_frame()

        # 1000 calls should complete reasonably fast (< 100ms)
        assert elapsed < 0.1, f"Many calls too slow: {elapsed}s for 1000 calls"
        assert len(frame.calls) == 1000

    def test_frame_buffer_memory_bounded(self):
        """Verify frame buffer doesn't grow unbounded."""
        enable()

        # Create many frames
        for i in range(1000):
            begin_frame(i)
            end_frame()

        # Buffer should be capped at 60 frames
        buffer = profiling.get_frame_buffer()
        assert len(buffer) == 60


class TestThreadSafety:
    """Basic thread safety tests."""

    def setup_method(self):
        enable()

    def teardown_method(self):
        disable()
        clear_frame_buffer()

    def test_call_id_uniqueness(self):
        """Verify call IDs are unique across multiple frames."""
        @profile("test", "Call")
        def make_call():
            pass

        all_ids = set()
        for i in range(10):
            begin_frame(i)
            for _ in range(10):
                make_call()
            frame = end_frame()

            for call in frame.calls:
                assert call.id not in all_ids, f"Duplicate call ID: {call.id}"
                all_ids.add(call.id)

        assert len(all_ids) == 100  # 10 frames x 10 calls
