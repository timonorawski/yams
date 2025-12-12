"""
AMS Real-Time Semantic Profiling System (Yamslicer)

Provides frame-level profiling of the game engine with call hierarchy tracking.
Records every frame update, Lua call, and Python ↔ Lua handoff for visualization.

DISABLED BY DEFAULT - Enable via environment variable or programmatic config.

Environment variables (via ams.logging):
    AMS_LOGGING_PROFILE_ENABLED=true

Or programmatically:
    from ams.profiling import enable
    enable()

Usage:
    from ams import profiling

    # In GameEngine.update():
    profiling.begin_frame(frame_number)
    # ... frame logic ...
    profiling.end_frame()

    # Decorate functions to profile:
    @profiling.profile("game_engine", "Frame Update")
    def _do_frame_update(self, dt):
        ...
"""

import os
import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from collections import deque
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

# Module name for sink registry
PROFILE_MODULE = 'profile'

# Check if enabled via environment
_enabled = os.getenv("AMS_LOGGING_PROFILE_ENABLED", "").lower() in ("1", "true", "yes")

# Thread-local storage for call stack context
_context = threading.local()

# Global call ID counter
_call_id_counter = 0
_call_id_lock = threading.Lock()

# Frame buffer for historical queries (last 60 frames)
_frame_buffer: deque = deque(maxlen=60)


def _get_profile_config() -> Dict[str, Any]:
    """Get profile module config from central logging system."""
    from ams.logging import get_module_config
    return get_module_config(PROFILE_MODULE)


def _next_call_id() -> int:
    """Get next unique call ID (thread-safe)."""
    global _call_id_counter
    with _call_id_lock:
        _call_id_counter += 1
        return _call_id_counter


@dataclass
class CallNode:
    """
    A single profiled function call.

    Attributes:
        id: Unique call identifier
        parent_id: Parent call's ID (None if root)
        label: Human-readable label (e.g., "ams.set_vy")
        module: Module name (e.g., "lua_api", "game_engine")
        func: Function name
        start: Start time relative to frame start (ms)
        duration: Call duration (ms)
        args: Optional captured arguments
        entity_id: Optional entity being operated on
        lua_code: True if this is Lua code execution
        lua_callback: True if this is a callback from Lua to Python
    """
    id: int
    parent_id: Optional[int]
    label: str
    module: str
    func: str
    start: float  # Relative to frame start, in ms
    duration: float = 0.0
    args: Dict[str, Any] = field(default_factory=dict)
    entity_id: Optional[str] = None
    lua_code: bool = False
    lua_callback: bool = False


@dataclass
class FrameProfile:
    """
    Profile data for a single frame.

    Attributes:
        frame: Frame number
        timestamp: Wall clock time when frame started
        duration_ms: Total frame duration in milliseconds
        calls: List of CallNodes recorded during this frame
        rollback: Rollback event data if rollback occurred
    """
    frame: int
    timestamp: float
    duration_ms: float = 0.0
    calls: List[CallNode] = field(default_factory=list)
    rollback: Optional[Dict[str, Any]] = None


def is_enabled() -> bool:
    """Check if profiling is enabled."""
    return _enabled


def enable() -> None:
    """Enable profiling."""
    global _enabled
    _enabled = True


def disable() -> None:
    """Disable profiling."""
    global _enabled
    _enabled = False


def begin_frame(frame_number: int) -> None:
    """
    Begin profiling a new frame.

    Call at the start of GameEngine.update().

    Args:
        frame_number: Current frame number
    """
    if not _enabled:
        return

    _context.stack = []
    _context.frame_start = time.perf_counter()
    _context.current_frame = FrameProfile(
        frame=frame_number,
        timestamp=time.time(),
    )


def end_frame() -> Optional[FrameProfile]:
    """
    End profiling the current frame.

    Call at the end of GameEngine.update(). Emits the frame profile
    to the logging system.

    Returns:
        The completed FrameProfile, or None if profiling disabled
    """
    if not _enabled:
        return None

    frame = getattr(_context, 'current_frame', None)
    if frame is None:
        return None

    frame_start = getattr(_context, 'frame_start', None)
    if frame_start:
        frame.duration_ms = (time.perf_counter() - frame_start) * 1000

    # Store in buffer
    _frame_buffer.append(frame)

    # Emit to logging system
    _emit_frame(frame)

    # Clean up context
    _context.stack = []
    _context.current_frame = None
    _context.frame_start = None

    return frame


def _emit_frame(frame: FrameProfile) -> None:
    """Emit frame profile to the logging system."""
    from ams.logging import emit_record, get_sink, register_sink, create_sink_for_environment

    # Ensure sink is registered
    if get_sink(PROFILE_MODULE) is None:
        sink = create_sink_for_environment(PROFILE_MODULE)
        register_sink(PROFILE_MODULE, sink)

    # Convert to dict for serialization
    record = {
        "type": "frame",
        "frame": frame.frame,
        "timestamp": frame.timestamp,
        "duration_ms": frame.duration_ms,
        "calls": [asdict(c) for c in frame.calls],
        "rollback": frame.rollback,
    }
    emit_record(PROFILE_MODULE, record)


def record_rollback(
    frames_resimulated: int,
    target_timestamp: float,
    snapshot_age_ms: float,
) -> None:
    """
    Record a rollback event in the current frame.

    Call from RollbackStateManager when rollback occurs.

    Args:
        frames_resimulated: Number of frames re-simulated
        target_timestamp: Timestamp we rolled back to
        snapshot_age_ms: Age of the snapshot used for rollback
    """
    if not _enabled:
        return

    frame = getattr(_context, 'current_frame', None)
    if frame:
        frame.rollback = {
            "triggered": True,
            "target_timestamp": target_timestamp,
            "frames_resimulated": frames_resimulated,
            "snapshot_age_ms": snapshot_age_ms,
        }


def get_frame_buffer() -> List[FrameProfile]:
    """Get the frame buffer (last 60 frames)."""
    return list(_frame_buffer)


def clear_frame_buffer() -> None:
    """Clear the frame buffer."""
    _frame_buffer.clear()


# Type variable for decorated functions
F = TypeVar('F', bound=Callable[..., Any])


def profile(module: str, label: Optional[str] = None, capture_args: bool = False) -> Callable[[F], F]:
    """
    Decorator to profile a function.

    Args:
        module: Module name (e.g., "game_engine", "lua_api")
        label: Human-readable label. If None, uses "{module}.{func_name}"
        capture_args: If True, capture function arguments in profile

    Example:
        @profile("game_engine", "Frame Update")
        def _do_frame_update(self, dt):
            ...
    """
    def decorator(func: F) -> F:
        func_name = func.__name__
        effective_label = label or f"{module}.{func_name}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not _enabled:
                return func(*args, **kwargs)

            # Check if we're in a frame context
            stack = getattr(_context, 'stack', None)
            if stack is None:
                # No frame context, just run the function
                return func(*args, **kwargs)

            frame_start = getattr(_context, 'frame_start', None)
            if frame_start is None:
                return func(*args, **kwargs)

            # Create call node
            call_id = _next_call_id()
            parent_id = stack[-1].id if stack else None

            node = CallNode(
                id=call_id,
                parent_id=parent_id,
                label=effective_label,
                module=module,
                func=func_name,
                start=(time.perf_counter() - frame_start) * 1000,
            )

            # Capture args if requested
            if capture_args and args:
                # Skip 'self' for methods
                arg_start = 1 if args and hasattr(args[0], '__class__') else 0
                node.args = {f"arg{i}": repr(a) for i, a in enumerate(args[arg_start:])}
                node.args.update({k: repr(v) for k, v in kwargs.items()})

            # Push onto stack
            stack.append(node)
            start = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Calculate duration
                node.duration = (time.perf_counter() - start) * 1000

                # Pop from stack
                if stack and stack[-1] is node:
                    stack.pop()

                # Record in current frame
                frame = getattr(_context, 'current_frame', None)
                if frame:
                    frame.calls.append(node)

        return cast(F, wrapper)
    return decorator


@contextmanager
def profile_section(module: str, label: str, entity_id: Optional[str] = None, lua_code: bool = False):
    """
    Context manager for profiling a section of code.

    Useful for profiling blocks that aren't easily decorated.

    Args:
        module: Module name
        label: Human-readable label
        entity_id: Optional entity being operated on
        lua_code: True if this section executes Lua code

    Example:
        with profiling.profile_section("lua_engine", f"on_update({entity_id})", entity_id=entity_id):
            lua_runtime.execute(...)
    """
    if not _enabled:
        yield
        return

    stack = getattr(_context, 'stack', None)
    if stack is None:
        yield
        return

    frame_start = getattr(_context, 'frame_start', None)
    if frame_start is None:
        yield
        return

    # Create call node
    call_id = _next_call_id()
    parent_id = stack[-1].id if stack else None

    node = CallNode(
        id=call_id,
        parent_id=parent_id,
        label=label,
        module=module,
        func="section",
        start=(time.perf_counter() - frame_start) * 1000,
        entity_id=entity_id,
        lua_code=lua_code,
    )

    stack.append(node)
    start = time.perf_counter()

    try:
        yield
    finally:
        node.duration = (time.perf_counter() - start) * 1000

        if stack and stack[-1] is node:
            stack.pop()

        frame = getattr(_context, 'current_frame', None)
        if frame:
            frame.calls.append(node)


def profile_lua_callback(module: str, label: str, entity_id: Optional[str] = None):
    """
    Context manager for profiling a Lua→Python callback.

    Args:
        module: Module name (typically "lua_api")
        label: Human-readable label (e.g., "ams.set_vy")
        entity_id: Optional entity being operated on

    Example:
        with profiling.profile_lua_callback("lua_api", "ams.set_vy", entity_id):
            entity.vy = vy
    """
    @contextmanager
    def _inner():
        if not _enabled:
            yield
            return

        stack = getattr(_context, 'stack', None)
        if stack is None:
            yield
            return

        frame_start = getattr(_context, 'frame_start', None)
        if frame_start is None:
            yield
            return

        call_id = _next_call_id()
        parent_id = stack[-1].id if stack else None

        node = CallNode(
            id=call_id,
            parent_id=parent_id,
            label=label,
            module=module,
            func=label.split('.')[-1] if '.' in label else label,
            start=(time.perf_counter() - frame_start) * 1000,
            entity_id=entity_id,
            lua_callback=True,
        )

        stack.append(node)
        start = time.perf_counter()

        try:
            yield
        finally:
            node.duration = (time.perf_counter() - start) * 1000

            if stack and stack[-1] is node:
                stack.pop()

            frame = getattr(_context, 'current_frame', None)
            if frame:
                frame.calls.append(node)

    return _inner()
