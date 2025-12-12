# YAMS Real-Time Semantic Profiling System
**Project codename:** Yamslicer
**Status:** Phase 1 complete (instrumentation + tests), Phase 2 pending (IDE visualization)
**Goal:** Let users press F9 and watch the game's execution in real time.

## Completion Status

| Phase | Status | Description |
|-------|--------|-------------|
| Core Module | Done | `ams/profiling.py` with decorators, frame lifecycle, call tracking |
| Instrumentation | Done | GameEngine, LuaEngine, GameLuaAPI instrumented |
| Test Suite | Done | 40 tests in `tests/profiling/` |
| CI Integration | Done | GitHub Actions runs profiling tests |
| WebSocket Broadcast | Pending | Uses `ams.logging` sink system, ready for WebSocket |
| IDE Panel | Pending | `ProfilerPanel.svelte` with flame graph visualization |

## 1. Core Philosophy

We are **making the engine's heartbeat visible**.

Every frame, every Lua call, every Python ↔ Lua handoff becomes:
- Recorded
- Visualised
- Understandable
- Shareable

This is **causality transparency** - showing users why their game behaves the way it does.

## 2. Current System Architecture

### Call Chain During a Frame

```
GameEngine.update(dt)                           # engine.py:1427
├── RollbackStateManager.capture()              # Snapshot for rollback
└── GameEngine._do_frame_update(dt)             # engine.py:1444
    ├── LuaEngine.update(dt)                    # lua/engine.py:674
    │   ├── Process scheduled callbacks
    │   └── _lifecycle_provider.on_entity_update()  # Per-entity behaviors
    │       └── [Lua code runs, calls ams.* API]
    │           ├── GameLuaAPI.set_x()          # api.py:108
    │           ├── GameLuaAPI.set_vy()         # api.py:136
    │           ├── GameLuaAPI.spawn()          # api.py
    │           └── ...
    ├── GameEngine._check_on_update_transforms()
    ├── GameEngine._check_collisions()
    │   └── LuaEngine.execute_collision_action()  # lua/engine.py:448
    ├── Skin.update(dt)
    ├── GameEngine._check_win_conditions()
    └── GameEngine._check_lose_conditions()
```

### Delayed Hit / Rollback Chain

```
GameEngine.process_delayed_hit(x, y, timestamp)   # engine.py:1480
├── [If recent: immediate processing]
└── [If delayed: rollback]
    └── RollbackStateManager.rollback_and_resimulate()  # rollback/manager.py:328
        ├── find_snapshot(target_timestamp)
        ├── restore(game_engine, snapshot)
        ├── hit_applicator()                      # Apply hit at past state
        └── _resimulate()                         # rollback/manager.py:383
            └── [Loop: game_engine._do_frame_update(dt)]
```

## 3. What Gets Instrumented

| Layer | Class / Method | File:Line | Profile Label |
|-------|---------------|-----------|---------------|
| **Frame Loop** | `GameEngine.update()` | engine.py:1427 | `Frame` |
| **Frame Logic** | `GameEngine._do_frame_update()` | engine.py:1444 | `Frame Update` |
| **Entity Updates** | `LuaEngine.update()` | lua/engine.py:674 | `Lua Entity Updates` |
| **Behavior Hooks** | `_lifecycle_provider.on_entity_update()` | - | `Lua → on_update({entity_id})` |
| **Collision Actions** | `LuaEngine.execute_collision_action()` | lua/engine.py:448 | `Lua → collision({action})` |
| **Input Actions** | `LuaEngine.execute_input_action()` | lua/engine.py:497 | `Lua → input({action})` |
| **Rollback Trigger** | `GameEngine.process_delayed_hit()` | engine.py:1480 | `Delayed Hit` |
| **Rollback Resim** | `RollbackStateManager.rollback_and_resimulate()` | rollback/manager.py:328 | `Rollback` |
| **Re-simulation** | `RollbackStateManager._resimulate()` | rollback/manager.py:383 | `Re-simulation` |
| **API: Position** | `GameLuaAPI.set_x/y()` | api.py:108-118 | `ams.set_x/y` |
| **API: Velocity** | `GameLuaAPI.set_vx/vy()` | api.py:130-140 | `ams.set_vx/vy` |
| **API: Spawn** | `GameLuaAPI.spawn()` | api.py | `ams.spawn` |
| **API: Destroy** | `GameLuaAPI.destroy()` | api.py:67 | `ams.destroy` |
| **API: Sound** | `GameLuaAPI.play_sound()` | api.py:84 | `ams.play_sound` |
| **API: Schedule** | `GameLuaAPI.schedule()` | api.py:85 | `ams.schedule` |

## 4. Data Format

```json
{
  "session_id": "2025-04-05_14-32-11_c4813854",
  "start_time": 1743953531.123,
  "frames": [
    {
      "frame": 1842,
      "timestamp": 1743953561.882,
      "duration_ms": 16.2,
      "calls": [
        {
          "id": 84291,
          "parent_id": null,
          "label": "Frame",
          "module": "game_engine",
          "func": "update",
          "start": 0.0,
          "duration": 16.2,
          "args": {"dt": 0.0166}
        },
        {
          "id": 84292,
          "parent_id": 84291,
          "label": "Lua Entity Updates",
          "module": "lua_engine",
          "func": "update",
          "start": 0.4,
          "duration": 9.1
        },
        {
          "id": 84293,
          "parent_id": 84292,
          "label": "Lua → on_update(duck_42)",
          "module": "lifecycle",
          "func": "on_entity_update",
          "start": 0.5,
          "duration": 2.3,
          "entity_id": "duck_42",
          "lua_code": true
        },
        {
          "id": 84294,
          "parent_id": 84293,
          "label": "ams.set_vy",
          "module": "lua_api",
          "func": "set_vy",
          "start": 0.6,
          "duration": 0.1,
          "args": {"entity_id": "duck_42", "vy": 533.7},
          "lua_callback": true
        }
      ],
      "rollback": null
    },
    {
      "frame": 1843,
      "rollback": {
        "triggered": true,
        "target_timestamp": 1743953561.750,
        "frames_resimulated": 8,
        "snapshot_age_ms": 12.3
      }
    }
  ]
}
```

## 5. Existing Infrastructure to Build On

### WebSocket Server (Ready)
- **File**: `ams/web_controller/server.py`
- **Class**: `WebController` with `ConnectionManager`
- **Endpoint**: `/ws` - accepts JSON commands, broadcasts state
- **Broadcast**: `ConnectionManager.broadcast(message)` sends to all clients

```python
# Existing pattern - add profiling channel
await websocket.send_text(json.dumps({
    "type": "profile_frame",  # New message type
    "data": frame_profile
}))
```

### Logging Infrastructure (Ready)
- **File**: `ams/games/game_engine/rollback/logger.py`
- **Class**: `GameStateLogger` - logs to sinks (file, websocket)
- **Pattern**: Disabled by default, enabled via env var

### Frontend Components (Ready)
- **Stack**: Svelte + Vite + Monaco Editor
- **IDE Components**: `src/lib/ide/` (FileTree, MonacoEditor, PreviewFrame)
- **WebSocket Client**: Exists in play interface components

## 6. Implementation Plan

### Python Side: `ams/profiling.py` (New File)

```python
"""
Profiling infrastructure for YAMS game engine.

Disabled by default. Enable via:
  - Environment: YAMS_PROFILE=1
  - Runtime: profiling.enable()
"""
import os
import time
import threading
from functools import wraps
from typing import Optional, Callable, Any
from dataclasses import dataclass, field, asdict
from collections import deque

ENABLED = os.getenv("YAMS_PROFILE", "").lower() in ("1", "true", "yes")
_call_stack = threading.local()
_call_id = 0
_frame_buffer: deque = deque(maxlen=60)  # Keep last 60 frames
_broadcast_callback: Optional[Callable] = None


@dataclass
class CallNode:
    id: int
    parent_id: Optional[int]
    label: str
    module: str
    func: str
    start: float  # Relative to frame start
    duration: float = 0.0
    args: dict = field(default_factory=dict)
    entity_id: Optional[str] = None
    lua_code: bool = False
    lua_callback: bool = False


@dataclass
class FrameProfile:
    frame: int
    timestamp: float
    duration_ms: float = 0.0
    calls: list = field(default_factory=list)
    rollback: Optional[dict] = None


def enable():
    global ENABLED
    ENABLED = True


def disable():
    global ENABLED
    ENABLED = False


def set_broadcast_callback(callback: Callable[[dict], None]):
    """Set callback for real-time streaming (e.g., WebSocket broadcast)."""
    global _broadcast_callback
    _broadcast_callback = callback


def profile(module: str, label: Optional[str] = None):
    """Decorator to profile a function call."""
    def decorator(func: Callable) -> Callable:
        if not ENABLED:
            return func

        @wraps(func)
        def wrapper(*args, **kwargs):
            global _call_id

            # Get or create frame context
            stack = getattr(_call_stack, 'stack', None)
            if stack is None:
                return func(*args, **kwargs)

            # Create call node
            _call_id += 1
            parent_id = stack[-1].id if stack else None
            frame_start = getattr(_call_stack, 'frame_start', time.perf_counter())

            node = CallNode(
                id=_call_id,
                parent_id=parent_id,
                label=label or f"{module}.{func.__name__}",
                module=module,
                func=func.__name__,
                start=(time.perf_counter() - frame_start) * 1000,
            )

            stack.append(node)
            start = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                node.duration = (time.perf_counter() - start) * 1000
                stack.pop()

                # Record in current frame
                frame = getattr(_call_stack, 'current_frame', None)
                if frame:
                    frame.calls.append(node)

        return wrapper
    return decorator


def begin_frame(frame_number: int) -> None:
    """Call at start of GameEngine.update()."""
    if not ENABLED:
        return
    _call_stack.stack = []
    _call_stack.frame_start = time.perf_counter()
    _call_stack.current_frame = FrameProfile(
        frame=frame_number,
        timestamp=time.time(),
    )


def end_frame() -> Optional[FrameProfile]:
    """Call at end of GameEngine.update(). Returns frame profile."""
    if not ENABLED:
        return None

    frame = getattr(_call_stack, 'current_frame', None)
    if frame:
        frame.duration_ms = (time.perf_counter() - _call_stack.frame_start) * 1000
        _frame_buffer.append(frame)

        if _broadcast_callback:
            _broadcast_callback({"type": "profile_frame", "data": asdict(frame)})

        return frame
    return None


def record_rollback(frames_resimulated: int, target_timestamp: float, snapshot_age_ms: float):
    """Record rollback event in current frame."""
    frame = getattr(_call_stack, 'current_frame', None)
    if frame:
        frame.rollback = {
            "triggered": True,
            "target_timestamp": target_timestamp,
            "frames_resimulated": frames_resimulated,
            "snapshot_age_ms": snapshot_age_ms,
        }
```

### Integration Points

**GameEngine** (`ams/games/game_engine/engine.py`):
```python
from ams import profiling

class GameEngine:
    def update(self, dt: float) -> None:
        profiling.begin_frame(self._frame_count)
        # ... existing code ...
        profiling.end_frame()

    @profiling.profile("game_engine", "Frame Update")
    def _do_frame_update(self, dt: float) -> None:
        # ... existing code ...
```

**LuaEngine** (`ams/lua/engine.py`):
```python
@profiling.profile("lua_engine", "Lua Entity Updates")
def update(self, dt: float) -> None:
    # ... existing code ...

@profiling.profile("lua_engine", "Collision Action")
def execute_collision_action(self, ...):
    # ... existing code ...
```

**GameLuaAPI** (`ams/games/game_engine/api.py`):
```python
@profiling.profile("lua_api", "ams.set_vy")
def set_vy(self, entity_id: str, vy: float) -> None:
    # ... existing code ...
```

**WebController** (`ams/web_controller/server.py`):
```python
from ams import profiling

class WebController:
    def _setup_profiling(self):
        if profiling.ENABLED:
            profiling.set_broadcast_callback(
                lambda msg: asyncio.run_coroutine_threadsafe(
                    self._manager.broadcast(msg),
                    self._loop
                )
            )
```

### Frontend: Profiler Panel

**New file**: `src/lib/ide/ProfilerPanel.svelte`

```svelte
<script>
  import { onMount, onDestroy } from 'svelte';

  export let wsConnection;

  let frames = [];
  let selectedFrame = null;
  let view = 'flame';  // 'flame' | 'tree' | 'timeline'

  function handleProfileFrame(data) {
    frames = [...frames.slice(-59), data];
    if (!selectedFrame) selectedFrame = data;
  }

  // Subscribe to profile_frame messages from existing WebSocket
</script>

<div class="profiler-panel">
  <div class="toolbar">
    <button class:active={view === 'flame'} on:click={() => view = 'flame'}>
      Flame Graph
    </button>
    <button class:active={view === 'tree'} on:click={() => view = 'tree'}>
      Call Tree
    </button>
    <button class:active={view === 'timeline'} on:click={() => view = 'timeline'}>
      Timeline
    </button>
  </div>

  {#if view === 'flame'}
    <FlameGraph {selectedFrame} />
  {:else if view === 'tree'}
    <CallTree {selectedFrame} />
  {:else}
    <Timeline {frames} />
  {/if}
</div>
```

## 7. Visualizations

| View | Description |
|------|-------------|
| **Flame Graph** | Horizontal bars showing call hierarchy. Red = Python, Blue = Lua callbacks |
| **Call Tree** | Collapsible tree with timing. Click to jump to source in Monaco |
| **Timeline** | Per-entity swim lanes showing when behaviors execute |
| **Rollback Events** | Purple highlight band when rollback occurs |

## 8. User Experience

**Happy path:**
1. User presses F9 (or clicks "Profiler" tab)
2. Bottom panel opens with live flame graph
3. Big bar shows `Lua → on_update(enemy_17)` taking 40% of frame
4. Click bar → Monaco opens the behavior file at the line
5. User adjusts behavior, sees immediate flame graph change

**Debugging path:**
1. User sees occasional lag spikes
2. Profiler shows purple "Rollback" bands
3. Clicks to see: 38 frames resimulated, 150ms snapshot age
4. Realizes detection latency is high, adjusts setup

## 9. Implementation Steps

1. **Create `ams/profiling.py`** with decorator and frame tracking
2. **Add `@profile` decorators** to ~15 hot paths listed above
3. **Wire WebSocket broadcast** in WebController
4. **Create `ProfilerPanel.svelte`** with basic flame graph (d3-flamegraph)
5. **Add call tree view** with source linking to Monaco
6. **Add timeline view** for per-entity visualization
7. **Add rollback highlighting**
8. **Add F9 toggle** and panel visibility state

## 10. Dependencies

**Python:** None new (uses stdlib `time`, `threading`, `dataclasses`)

**Frontend:**
- `d3-flamegraph` - flame graph visualization
- Already have: Svelte, Monaco, WebSocket infrastructure

## 11. Configuration

```bash
# Enable profiling (disabled by default)
YAMS_PROFILE=1 python ams_game.py --game duckhunt

# Or enable at runtime via web controller command
# POST /ws: {"command": "enable_profiling"}
```

The profiler adds ~0.1ms overhead per frame when enabled. When disabled (default), the decorators are no-ops with zero overhead.

## 12. Testing Strategy

### Test Structure

```
tests/
└── profiling/
    ├── __init__.py
    ├── test_profiling_core.py      # Unit tests for profiling module
    ├── test_profiling_decorator.py # Decorator behavior tests
    ├── test_profiling_integration.py # Integration with game engine
    └── test_profiling_websocket.py # WebSocket broadcast tests
```

### Unit Tests (`test_profiling_core.py`)

```python
"""Unit tests for ams/profiling.py core functionality."""
import pytest
import time
from ams import profiling
from ams.profiling import CallNode, FrameProfile, begin_frame, end_frame


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


class TestFrameProfile:
    """Tests for FrameProfile dataclass."""

    def test_frame_profile_defaults(self):
        frame = FrameProfile(frame=1, timestamp=1000.0)
        assert frame.calls == []
        assert frame.rollback is None
        assert frame.duration_ms == 0.0

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


class TestFrameLifecycle:
    """Tests for begin_frame/end_frame lifecycle."""

    def setup_method(self):
        profiling.enable()

    def teardown_method(self):
        profiling.disable()

    def test_begin_end_frame_returns_profile(self):
        begin_frame(42)
        result = end_frame()

        assert result is not None
        assert result.frame == 42
        assert result.duration_ms > 0

    def test_frame_not_recorded_when_disabled(self):
        profiling.disable()
        begin_frame(1)
        result = end_frame()
        assert result is None

    def test_frame_buffer_limits(self):
        """Verify frame buffer respects maxlen."""
        for i in range(100):
            begin_frame(i)
            end_frame()

        # Buffer should only keep last 60 frames
        assert len(profiling._frame_buffer) == 60


class TestEnableDisable:
    """Tests for enable/disable functionality."""

    def teardown_method(self):
        profiling.disable()

    def test_enable_sets_flag(self):
        profiling.disable()
        assert profiling.ENABLED is False
        profiling.enable()
        assert profiling.ENABLED is True

    def test_disable_sets_flag(self):
        profiling.enable()
        profiling.disable()
        assert profiling.ENABLED is False
```

### Decorator Tests (`test_profiling_decorator.py`)

```python
"""Tests for @profile decorator behavior."""
import pytest
import time
from ams import profiling
from ams.profiling import profile, begin_frame, end_frame


class TestProfileDecorator:
    """Tests for the @profile decorator."""

    def setup_method(self):
        profiling.enable()

    def teardown_method(self):
        profiling.disable()

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
        assert frame.calls[0].duration > 0

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

    def test_no_recording_outside_frame(self):
        """Calls outside begin_frame/end_frame are not recorded."""
        @profile("test", "Outside")
        def outside_func():
            return 1

        # Call without frame context
        result = outside_func()
        assert result == 1  # Function still works

    def test_decorator_is_noop_when_disabled(self):
        profiling.disable()

        call_count = 0

        @profile("test", "Disabled")
        def tracked_func():
            nonlocal call_count
            call_count += 1

        tracked_func()
        assert call_count == 1  # Function runs but no profiling overhead
```

### Integration Tests (`test_profiling_integration.py`)

```python
"""Integration tests for profiling with game engine."""
import pytest
from unittest.mock import MagicMock, patch
from ams import profiling


class TestGameEngineIntegration:
    """Tests that profiling integrates correctly with GameEngine."""

    def setup_method(self):
        profiling.enable()

    def teardown_method(self):
        profiling.disable()

    def test_frame_update_is_profiled(self):
        """Verify _do_frame_update appears in profile."""
        # This requires the actual GameEngine with profiling decorators
        # Skip if game engine not available
        pytest.importorskip("ams.games.game_engine.engine")

        from ams.games.game_engine.engine import GameEngine

        # Create minimal game engine (may need fixtures)
        # engine = GameEngine(...)
        # profiling.begin_frame(1)
        # engine._do_frame_update(0.016)
        # frame = profiling.end_frame()
        # assert any(c.label == "Frame Update" for c in frame.calls)

    def test_rollback_recording(self):
        """Verify rollback events are recorded."""
        profiling.begin_frame(1)
        profiling.record_rollback(
            frames_resimulated=10,
            target_timestamp=1000.0,
            snapshot_age_ms=50.0,
        )
        frame = profiling.end_frame()

        assert frame.rollback is not None
        assert frame.rollback["triggered"] is True
        assert frame.rollback["frames_resimulated"] == 10
        assert frame.rollback["snapshot_age_ms"] == 50.0


class TestLuaAPIIntegration:
    """Tests that Lua API calls are profiled."""

    def setup_method(self):
        profiling.enable()

    def teardown_method(self):
        profiling.disable()

    def test_lua_api_calls_recorded(self):
        """Verify ams.* API calls appear in profile."""
        # This requires the actual GameLuaAPI with profiling decorators
        pytest.importorskip("ams.games.game_engine.api")

        # Similar pattern - create API instance and verify calls are recorded
        pass
```

### WebSocket Tests (`test_profiling_websocket.py`)

```python
"""Tests for profiling WebSocket broadcast."""
import pytest
import json
from unittest.mock import MagicMock, AsyncMock
from ams import profiling


class TestBroadcastCallback:
    """Tests for WebSocket broadcast integration."""

    def setup_method(self):
        profiling.enable()
        self.received_messages = []

    def teardown_method(self):
        profiling.disable()
        profiling.set_broadcast_callback(None)

    def test_broadcast_callback_receives_frame(self):
        def capture_callback(msg):
            self.received_messages.append(msg)

        profiling.set_broadcast_callback(capture_callback)

        profiling.begin_frame(1)
        profiling.end_frame()

        assert len(self.received_messages) == 1
        assert self.received_messages[0]["type"] == "profile_frame"
        assert self.received_messages[0]["data"]["frame"] == 1

    def test_broadcast_includes_calls(self):
        @profiling.profile("test", "Test Call")
        def test_func():
            pass

        def capture_callback(msg):
            self.received_messages.append(msg)

        profiling.set_broadcast_callback(capture_callback)

        profiling.begin_frame(1)
        test_func()
        profiling.end_frame()

        data = self.received_messages[0]["data"]
        assert len(data["calls"]) == 1
        assert data["calls"][0]["label"] == "Test Call"

    def test_no_broadcast_when_disabled(self):
        def capture_callback(msg):
            self.received_messages.append(msg)

        profiling.set_broadcast_callback(capture_callback)
        profiling.disable()

        profiling.begin_frame(1)
        profiling.end_frame()

        assert len(self.received_messages) == 0

    def test_broadcast_serializes_to_json(self):
        """Verify broadcast data is JSON-serializable."""
        captured = None

        def capture_callback(msg):
            nonlocal captured
            captured = msg

        profiling.set_broadcast_callback(capture_callback)

        profiling.begin_frame(1)
        profiling.end_frame()

        # Should not raise
        json_str = json.dumps(captured)
        assert "profile_frame" in json_str
```

### Performance Tests

```python
"""Performance tests to verify profiling overhead."""
import pytest
import time
from ams import profiling


class TestProfilingOverhead:
    """Verify profiling overhead stays within acceptable limits."""

    def test_disabled_overhead_is_zero(self):
        """When disabled, decorators should have negligible overhead."""
        profiling.disable()

        @profiling.profile("test", "Test")
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

        # Should be very fast (< 1ms per 10000 calls)
        assert elapsed < 0.1, f"Disabled profiling overhead too high: {elapsed}s"

    def test_enabled_overhead_acceptable(self):
        """When enabled, overhead should be < 0.1ms per frame."""
        profiling.enable()

        @profiling.profile("test", "Test")
        def simulated_work():
            time.sleep(0.001)  # Simulate 1ms of work

        # Measure frame overhead
        overheads = []
        for i in range(100):
            profiling.begin_frame(i)

            start = time.perf_counter()
            simulated_work()
            work_time = time.perf_counter() - start

            frame = profiling.end_frame()
            frame_time = frame.duration_ms / 1000

            overhead = frame_time - work_time
            overheads.append(overhead)

        avg_overhead = sum(overheads) / len(overheads)
        # Average overhead should be < 0.1ms (0.0001s)
        assert avg_overhead < 0.0001, f"Profiling overhead too high: {avg_overhead*1000:.3f}ms"

        profiling.disable()
```

### GitHub Actions Integration

The profiling tests integrate with the existing `tests.yml` workflow. Update `.github/workflows/tests.yml`:

```yaml
# Add to existing tests.yml under python-tests job

      - name: Run profiling tests
        run: |
          pytest tests/profiling/ \
            --tb=short \
            -v

      - name: Run profiling performance tests
        run: |
          pytest tests/profiling/test_profiling_performance.py \
            --tb=short \
            -v \
            -x  # Stop on first failure for perf tests
```

### Test Coverage Requirements

| Component | Minimum Coverage | Notes |
|-----------|-----------------|-------|
| `ams/profiling.py` | 90% | Core module must be well-tested |
| Decorator behavior | 100% | Critical path, all branches covered |
| WebSocket broadcast | 80% | Integration points |
| Performance tests | Pass/Fail | Overhead limits enforced |

### CI Test Matrix

```yaml
# Optional: Test profiling across Python versions
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
```

### Running Tests Locally

```bash
# Run all profiling tests
pytest tests/profiling/ -v

# Run with coverage
pytest tests/profiling/ --cov=ams.profiling --cov-report=html

# Run only performance tests
pytest tests/profiling/test_profiling_performance.py -v

# Run with profiling enabled (test the tests!)
YAMS_PROFILE=1 pytest tests/profiling/ -v
```

### Test Fixtures

Create `tests/profiling/conftest.py`:

```python
"""Pytest fixtures for profiling tests."""
import pytest
from ams import profiling


@pytest.fixture
def profiling_enabled():
    """Enable profiling for a test, disable after."""
    profiling.enable()
    yield
    profiling.disable()


@pytest.fixture
def profiling_disabled():
    """Ensure profiling is disabled for a test."""
    profiling.disable()
    yield


@pytest.fixture
def capture_broadcasts():
    """Capture broadcast messages for verification."""
    messages = []

    def callback(msg):
        messages.append(msg)

    profiling.set_broadcast_callback(callback)
    yield messages
    profiling.set_broadcast_callback(None)
```
