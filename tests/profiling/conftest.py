"""Pytest fixtures for profiling tests."""
import pytest
from ams import profiling


@pytest.fixture
def profiling_enabled():
    """Enable profiling for a test, disable after."""
    profiling.enable()
    yield
    profiling.disable()
    profiling.clear_frame_buffer()


@pytest.fixture
def profiling_disabled():
    """Ensure profiling is disabled for a test."""
    profiling.disable()
    yield


@pytest.fixture
def capture_broadcasts():
    """Capture broadcast messages for verification.

    Note: This requires the logging system to be configured with a
    sink that calls a callback. For unit tests, we test the frame
    data directly via end_frame() return value.
    """
    messages = []
    yield messages
