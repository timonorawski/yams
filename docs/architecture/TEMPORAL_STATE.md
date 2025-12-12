# Temporal Game State Architecture

This document describes the `TemporalGameState` system for handling detection latency in CV-based projectile detection.

## The Problem

When using computer vision to detect projectile impacts, there is significant latency between when a projectile actually hits the target and when the system reports the hit:

```
Player releases arrow
        │
        ▼  (200-500ms projectile flight)
Arrow hits target
        │
        ▼  (50-200ms camera capture + CV processing)
Detection system reports PlaneHitEvent
        │
        ▼
Game receives event... but game state has MOVED ON
```

**Total latency**: 300-800ms from player action to detection event.

During this time, the game continues running at 60fps. Targets move, spawn, despawn. By the time the hit event arrives, the target the player was aiming at may no longer be where it was when they released.

**Naive approach fails**: Checking "is there a target at (x, y) RIGHT NOW?" produces incorrect results because the game state no longer matches what the player saw.

## The Solution: "Games Query the Past"

Instead of checking current state, games maintain a rolling history of state snapshots. When a hit event arrives with timestamp T, the game queries its own history to find what the state was at time T.

```
┌─────────────────────────────────────────────────────────────────┐
│                     STATE HISTORY                                │
│                                                                  │
│  Frame 100      Frame 101      Frame 102      Frame 103         │
│  t=1.666s       t=1.683s       t=1.700s       t=1.716s          │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       │
│  │ Target  │    │ Target  │    │ Target  │    │ Target  │       │
│  │ at 0.3  │    │ at 0.35 │    │ at 0.4  │    │ at 0.45 │       │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘       │
│       ▲                                                          │
│       │                                                          │
│       └─── PlaneHitEvent arrives: x=0.32, timestamp=1.670s       │
│            Query: "Was there a hit at (0.32, y) at t=1.670?"     │
│            Answer: Check Frame 100 snapshot → YES, target hit!   │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture

### Core Classes

```
┌─────────────────────────────────────────────────────────────────┐
│                     StateSnapshot                                │
│                                                                  │
│  • frame: int           Frame number                             │
│  • timestamp: float     time.monotonic() when captured           │
│  • state_data: Dict     Deep copy of game state                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ stored in
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TemporalGameState (ABC)                          │
│                                                                  │
│  history: deque[StateSnapshot]    Rolling window of snapshots    │
│  history_duration: float          How long to keep (default 5s)  │
│  fps: int                         Expected frame rate            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Abstract Methods (implement in your game)                  │ │
│  │                                                            │ │
│  │  get_current_state_snapshot() → Dict                       │ │
│  │  check_hit_in_snapshot(snapshot, x, y) → HitResult         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Provided Methods                                           │ │
│  │                                                            │ │
│  │  update(dt)              Capture snapshot each frame       │ │
│  │  was_target_hit(x, y, timestamp, latency_ms) → HitResult   │ │
│  │  get_history_stats() → Dict                                │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Memory Management

The history is stored in a `deque` with a fixed maximum length:

```python
max_snapshots = history_duration * fps  # e.g., 5.0 * 60 = 300 snapshots
history = deque(maxlen=max_snapshots)
```

When a new snapshot is added and the deque is full, the oldest snapshot is automatically discarded. This provides:

- **Bounded memory**: Never grows beyond `max_snapshots` entries
- **Automatic cleanup**: No manual pruning required
- **O(1) append**: Adding new snapshots is constant time

### Snapshot Query Algorithm

When `was_target_hit(x, y, timestamp, latency_ms)` is called:

1. **Adjust for detection latency**: `adjusted_time = timestamp - (latency_ms / 1000.0)`
2. **Check if query is current**: If adjusted_time >= latest snapshot, use current state
3. **Find closest snapshot**: Linear scan through history for smallest time delta
4. **Query snapshot**: Call `check_hit_in_snapshot(snapshot.state_data, x, y)`
5. **Return result**: `HitResult` with hit status, target info, points, etc.

```python
# Pseudocode for temporal query
def was_target_hit(x, y, timestamp, latency_ms=0):
    adjusted_time = timestamp - (latency_ms / 1000.0)

    # Find closest snapshot
    best_snapshot = None
    best_distance = infinity
    for snapshot in history:
        distance = abs(snapshot.timestamp - adjusted_time)
        if distance < best_distance:
            best_distance = distance
            best_snapshot = snapshot

    # Query that snapshot
    return check_hit_in_snapshot(best_snapshot.state_data, x, y)
```

## Implementation Guide

### Step 1: Inherit from TemporalGameState

```python
from ams.temporal_state import TemporalGameState
from ams.events import HitResult

class MyGame(TemporalGameState):
    def __init__(self):
        # 5 seconds of history at 60fps = 300 snapshots
        super().__init__(history_duration=5.0, fps=60)

        self.targets = []
        self.score = 0
```

### Step 2: Implement get_current_state_snapshot()

Return a **deep copy** of all state needed to check hits. Modifying the returned dict must not affect game state.

```python
def get_current_state_snapshot(self) -> Dict[str, Any]:
    return {
        'targets': [
            {
                'id': t.id,
                'x': t.x,
                'y': t.y,
                'radius': t.radius,
                'points': t.points,
                'active': t.active
            }
            for t in self.targets
        ]
    }
```

**Important**: Only include state that affects hit detection. Don't include:
- Rendering state (sprites, animations)
- UI state (menus, scores)
- Audio state

### Step 3: Implement check_hit_in_snapshot()

Check if coordinates hit anything in a specific state snapshot.

```python
def check_hit_in_snapshot(
    self,
    snapshot: Dict[str, Any],
    x: float,
    y: float
) -> HitResult:
    for target in snapshot['targets']:
        if not target['active']:
            continue

        # Distance check (normalized coordinates)
        dx = x - target['x']
        dy = y - target['y']
        distance = (dx*dx + dy*dy) ** 0.5

        if distance < target['radius']:
            return HitResult(
                hit=True,
                target_id=target['id'],
                points=target['points'],
                message="Hit!"
            )

    return HitResult(hit=False, message="Miss")
```

### Step 4: Call super().update() Each Frame

The base class captures snapshots automatically when `auto_snapshot=True` (default).

```python
def update(self, dt: float):
    # Update game logic FIRST
    self.move_targets(dt)
    self.spawn_new_targets()
    self.check_despawns()

    # Then capture snapshot
    super().update(dt)
```

### Step 5: Use was_target_hit() for Detection Events

When processing `PlaneHitEvent` from detection backend:

```python
def handle_detection_event(self, event: PlaneHitEvent):
    # Query historical state at event timestamp
    # Adjust for detection latency (e.g., 150ms for CV)
    result = self.was_target_hit(
        x=event.x,
        y=event.y,
        query_time=event.timestamp,
        latency_ms=150.0
    )

    if result.hit:
        self.score += result.points
        self.deactivate_target(result.target_id)
```

## When to Use Temporal State

| Detection Method | Latency | Use Temporal State? |
|-----------------|---------|---------------------|
| Mouse/keyboard | ~0ms | No - instant, use current state |
| Laser pointer | ~50ms | No - instantaneous detection |
| Object detection | 100-500ms | **Yes** - significant delay |
| Network/remote | Variable | **Yes** - unpredictable delay |

## Configuration

### History Duration

Default is 5 seconds. Adjust based on:

- **Maximum expected latency**: Must be > worst-case detection delay
- **Memory constraints**: Each snapshot uses memory proportional to game state size
- **Game dynamics**: Fast-paced games with many objects need more history

```python
# For a game with heavy CV latency (800ms worst case)
super().__init__(history_duration=2.0, fps=60)  # 120 snapshots

# For network play with potential lag spikes
super().__init__(history_duration=10.0, fps=60)  # 600 snapshots
```

### Manual Snapshot Control

For games that need finer control over when snapshots are captured:

```python
class MyGame(TemporalGameState):
    def __init__(self):
        super().__init__(auto_snapshot=False)  # Disable auto-capture

    def update(self, dt):
        self.update_game_logic(dt)

        # Only capture snapshot when targets have moved
        if self.targets_changed:
            self.capture_snapshot()

        self.frame_counter += 1
```

## Debugging

### History Stats

```python
stats = game.get_history_stats()
print(f"Snapshots: {stats['snapshots']}")
print(f"Time span: {stats['time_span']:.2f}s")
print(f"Frames: {stats['frames_span']}")
print(f"Buffer size: {stats['buffer_size']}")
```

### Verify Snapshot Content

```python
# Check what's being captured
snapshot = game.get_current_state_snapshot()
print(f"Snapshot keys: {snapshot.keys()}")
print(f"Target count: {len(snapshot.get('targets', []))}")
```

### Query Timing Analysis

```python
import time

# Measure query performance
start = time.monotonic()
result = game.was_target_hit(0.5, 0.5, query_time=start - 0.2)
query_time = time.monotonic() - start
print(f"Query took {query_time*1000:.2f}ms")
```

## File Location

```
ams/temporal_state.py
```

## Related Documentation

- [AMS Architecture](AMS_ARCHITECTURE.md) - Overall system architecture
- [Detection Backends](AMS_ARCHITECTURE.md#detection-backends) - Backend comparison and latency characteristics
