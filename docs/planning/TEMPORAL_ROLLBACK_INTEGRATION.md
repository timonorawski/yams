---
created: 2024-12-12
status: partially_implemented
summary: >
  Planning document for temporal rollback integration to handle CV detection
  latency. The core rollback subsystem (Phase 1-2) has been implemented as
  standalone classes with unit tests. Integration with GameEngine (Phase 3+)
  is pending.
implemented:
  - Phase 1: EntitySnapshot, GameSnapshot dataclasses (ams/games/game_engine/rollback/snapshot.py)
  - Phase 1: RollbackStateManager with capture/restore/resimulate (ams/games/game_engine/rollback/manager.py)
  - Phase 2: find_snapshot() timestamp search
  - Phase 2: rollback_and_resimulate() main entry point
  - 32 unit tests (ams/games/game_engine/rollback/tests/test_rollback.py)
not_implemented:
  - GameEngine integration (modified update loop, input handling)
  - Phase 3: Cascading effects verification with real Lua behaviors
  - Phase 4: Visual reconciliation (visual_x/visual_y, smoothing)
  - Phase 5: Optimization (delta compression, profiling)
  - Phase 6: Debug visualization and metrics
related_files:
  - ams/games/game_engine/rollback/__init__.py
  - ams/games/game_engine/rollback/snapshot.py
  - ams/games/game_engine/rollback/manager.py
  - ams/games/game_engine/rollback/tests/test_rollback.py
  - docs/architecture/TEMPORAL_STATE.md
---

# Temporal Rollback Integration for Game Engine

## Executive Summary

This document plans the integration of temporal state management into the YAML game engine to handle computer vision (CV) detection latency. The core challenge: **when a hit is detected at time T (which is in the past), we must roll back game state to T, apply the hit, and re-simulate forward to the present**.

This is not a simple query system - it's **rollback netcode** similar to GGPO in fighting games or lag compensation in FPS games.

## The Problem

### Detection Latency Chain

```
Player releases arrow
        │
        ▼  (200-500ms projectile flight)
Arrow hits target surface
        │
        ▼  (16-50ms camera capture)
Frame captured
        │
        ▼  (50-150ms CV processing)
Impact detected, PlaneHitEvent emitted
        │
        ▼
Game receives event with timestamp T
        │
        ▼
Game state is now at T + 300-700ms
```

**Problem**: By the time the game receives the hit event, the game has advanced 300-700ms (18-42 frames at 60fps). The target the player hit may have:
- Moved to a different position
- Been destroyed by another hit
- Spawned children or triggered effects
- Changed type (transformed)

### Why Simple Temporal Queries Fail

The existing `TemporalGameState` class handles the simple case: "Was there a target at position (x,y) at time T?"

But this is insufficient because:

1. **Cascading Effects**: Hitting a brick at T should:
   - Destroy the brick at T (not now)
   - Award points at T
   - Spawn particles at T
   - Those particles should have been moving for 300ms
   - Ball should have bounced at T, affecting its current position

2. **State Consistency**: If we just "retroactively" award points without rollback:
   - The player sees the brick still there (it wasn't destroyed at T)
   - The ball didn't bounce (it passed through where the brick was)
   - The score jumps unexpectedly

3. **Multiple Delayed Hits**: With CV detection, multiple hits might arrive out of order:
   - Hit A at T=1.0s arrives at T=1.5s
   - Hit B at T=1.2s arrives at T=1.4s
   - Must process in temporal order, not arrival order

## Rollback Architecture Overview

### Core Concept

```
Timeline with CV detection:

Real Time:     0.0s ─────────────────────────────────────────────► 1.0s
                │                                                    │
Game State:    [Frame 0]────[Frame 30]────[Frame 60]────────────[Frame 60]
                │                │              │                    │
                │                │              │                    │
                │           Hit occurs      Detection          Game receives
                │            (T=0.5s)       processes           PlaneHitEvent
                │                │           (latent)           (T=0.5s, now=1.0s)
                │                │              │                    │
                │                ▼              │                    │
                │         [No hit recorded -   │              ROLLBACK TO T=0.5s
                │          game doesn't know]  │                    │
                │                              │                    ▼
                │                              │              Apply hit at T=0.5s
                │                              │                    │
                │                              │                    ▼
                │                              │              Re-simulate 0.5s→1.0s
                │                              │              (30 frames at 60fps)
                │                              │                    │
                │                              │                    ▼
                │                              │              Reconciled state at 1.0s
```

### The Rollback Loop

When a delayed hit event arrives:

```
1. RECEIVE: PlaneHitEvent with timestamp T (in the past)
   │
   ▼
2. VALIDATE: Is T within rollback window? (e.g., last 2 seconds)
   │
   ├─ No: Log warning, apply to current state (best effort)
   │
   └─ Yes: Continue to rollback
         │
         ▼
3. SNAPSHOT: Save current "speculative" state (what we showed the player)
   │
   ▼
4. RESTORE: Load state snapshot from time T (or closest earlier snapshot)
   │
   ▼
5. APPLY: Process the hit at time T
   │        - Check collision at T
   │        - Trigger on_hit behaviors
   │        - Apply transforms (destroy, spawn children)
   │        - Award points
   │
   ▼
6. RE-SIMULATE: Step forward from T to current time
   │             - Run update(dt) for each frame
   │             - Process any other pending hits in [T, now]
   │             - All game logic runs normally
   │
   ▼
7. RECONCILE: New "authoritative" state replaces speculative state
   │           - Entity positions updated
   │           - Score updated
   │           - Visual state reconciled
   │
   ▼
8. CONTINUE: Resume normal game loop
```

## State Capture Requirements

### What Must Be Captured

For rollback to work, snapshots must capture **everything** needed to restore game state exactly:

#### Entity State (per entity)

```python
@dataclass
class EntitySnapshot:
    # Identity
    id: str
    entity_type: str
    alive: bool

    # Transform
    x: float
    y: float
    vx: float
    vy: float
    width: float
    height: float

    # Visual (needed for reconciliation)
    color: str
    sprite: str
    visible: bool

    # Game state
    health: int
    spawn_time: float

    # Custom properties (behaviors store state here)
    properties: Dict[str, Any]  # DEEP COPY

    # Hierarchy
    parent_id: Optional[str]
    parent_offset: Tuple[float, float]
    children: List[str]

    # Behavior state
    behaviors: List[str]
    behavior_config: Dict[str, Dict[str, Any]]
```

#### Global Game State

```python
@dataclass
class GameSnapshot:
    # Timing
    frame_number: int
    elapsed_time: float
    timestamp: float  # time.monotonic() for correlation with input events

    # All entities
    entities: Dict[str, EntitySnapshot]

    # Game progress
    score: int
    lives: int
    internal_state: GameState  # PLAYING, WON, GAME_OVER

    # Scheduled callbacks
    scheduled_callbacks: List[ScheduledCallbackSnapshot]

    # Random state (for deterministic replay)
    random_seed: int  # If using seeded random
```

#### What NOT to Capture

- Rendered frames (too large, not needed)
- Sound queue (sounds already played)
- Skin/renderer state (derived from entity state)
- Loaded Lua scripts (immutable during game)

### Snapshot Storage

```python
class RollbackStateManager:
    """Manages state snapshots for rollback."""

    def __init__(
        self,
        history_duration: float = 2.0,  # How far back we can rollback
        fps: int = 60,
        snapshot_interval: int = 1,  # Snapshot every N frames (1 = every frame)
    ):
        self.max_snapshots = int(history_duration * fps / snapshot_interval)
        self.snapshots: deque[GameSnapshot] = deque(maxlen=self.max_snapshots)
        self.snapshot_interval = snapshot_interval

    def capture(self, game_engine: GameEngine) -> GameSnapshot:
        """Capture current game state."""
        # Deep copy all entity state
        entity_snapshots = {}
        for entity in game_engine._behavior_engine.entities.values():
            entity_snapshots[entity.id] = self._snapshot_entity(entity)

        return GameSnapshot(
            frame_number=game_engine._behavior_engine.frame_counter,
            elapsed_time=game_engine._behavior_engine.elapsed_time,
            timestamp=time.monotonic(),
            entities=entity_snapshots,
            score=game_engine._behavior_engine.score,
            lives=game_engine._lives,
            internal_state=game_engine._internal_state,
            scheduled_callbacks=self._snapshot_scheduled(game_engine),
        )

    def find_snapshot(self, timestamp: float) -> Optional[GameSnapshot]:
        """Find snapshot closest to (but not after) timestamp."""
        best = None
        for snapshot in self.snapshots:
            if snapshot.timestamp <= timestamp:
                if best is None or snapshot.timestamp > best.timestamp:
                    best = snapshot
        return best
```

## State Restoration

### Restoring Entity State

```python
def restore_entity(self, entity: GameEntity, snapshot: EntitySnapshot) -> None:
    """Restore entity to snapshot state."""
    entity.x = snapshot.x
    entity.y = snapshot.y
    entity.vx = snapshot.vx
    entity.vy = snapshot.vy
    entity.width = snapshot.width
    entity.height = snapshot.height
    entity.color = snapshot.color
    entity.sprite = snapshot.sprite
    entity.visible = snapshot.visible
    entity.health = snapshot.health
    entity.alive = snapshot.alive
    entity.spawn_time = snapshot.spawn_time
    entity.parent_id = snapshot.parent_id
    entity.parent_offset = snapshot.parent_offset
    entity.children = list(snapshot.children)
    entity.behaviors = list(snapshot.behaviors)
    entity.behavior_config = deep_copy(snapshot.behavior_config)

    # Properties need deep copy to avoid shared state
    entity.properties = deep_copy(snapshot.properties)
```

### Restoring Game State

```python
def restore(self, game_engine: GameEngine, snapshot: GameSnapshot) -> None:
    """Restore full game state from snapshot."""
    engine = game_engine._behavior_engine

    # Restore global state
    engine.elapsed_time = snapshot.elapsed_time
    engine.frame_counter = snapshot.frame_number
    engine.score = snapshot.score
    game_engine._lives = snapshot.lives
    game_engine._internal_state = snapshot.internal_state

    # Restore scheduled callbacks
    engine._scheduled = self._restore_scheduled(snapshot.scheduled_callbacks)

    # Restore entities
    # First: identify entities to remove (exist now but not in snapshot)
    current_ids = set(engine.entities.keys())
    snapshot_ids = set(snapshot.entities.keys())

    for entity_id in current_ids - snapshot_ids:
        # Entity didn't exist at snapshot time - remove it
        del engine.entities[entity_id]

    # Second: restore or create entities from snapshot
    for entity_id, entity_snap in snapshot.entities.items():
        if entity_id in engine.entities:
            # Entity exists - restore its state
            self.restore_entity(engine.entities[entity_id], entity_snap)
        else:
            # Entity doesn't exist - recreate it
            entity = self._recreate_entity(entity_snap, game_engine)
            engine.entities[entity_id] = entity
```

## Re-simulation

### Deterministic Updates

For rollback to produce consistent results, game updates must be **deterministic**:

```python
def re_simulate(
    self,
    game_engine: GameEngine,
    from_time: float,
    to_time: float,
    pending_hits: List[PlaneHitEvent],
) -> None:
    """Re-simulate game from from_time to to_time, applying pending hits."""

    # Sort pending hits by timestamp
    pending_hits = sorted(pending_hits, key=lambda h: h.timestamp)
    hit_index = 0

    # Calculate frames to simulate
    dt = 1.0 / 60.0  # Fixed timestep for determinism
    current_time = from_time

    while current_time < to_time:
        # Apply any hits that occurred before this frame
        while hit_index < len(pending_hits):
            hit = pending_hits[hit_index]
            if hit.timestamp <= current_time:
                self._apply_hit(game_engine, hit)
                hit_index += 1
            else:
                break

        # Run one frame of game logic
        game_engine.update(dt)
        current_time += dt
```

### Determinism Requirements

For re-simulation to match original simulation:

1. **Fixed Timestep**: Always use same dt (1/60s), not variable frame time
2. **Seeded Random**: Lua's `ams.random()` must use seeded PRNG, restorable from snapshot
3. **No External State**: Behaviors can't depend on wall-clock time, only `ams.get_time()`
4. **Order Independence**: Entity update order must be deterministic (sort by ID)

```python
# In LuaEngine.update():
def update(self, dt: float) -> None:
    # IMPORTANT: Update entities in deterministic order
    for entity in sorted(self.entities.values(), key=lambda e: e.id):
        if entity.alive:
            self._lifecycle_provider.on_entity_update(entity, self, dt)
```

## Handling Hit Application

### During Rollback

```python
def _apply_hit(self, game_engine: GameEngine, hit: PlaneHitEvent) -> None:
    """Apply a hit event during rollback re-simulation."""

    # Convert normalized coords to pixel coords
    pixel_x = hit.x * game_engine._screen_width
    pixel_y = hit.y * game_engine._screen_height

    # Create InputEvent as if it arrived now
    input_event = InputEvent(
        position=Vector2D(x=pixel_x, y=pixel_y),
        timestamp=hit.timestamp,
        event_type=EventType.HIT,
    )

    # Process through normal input handling
    # This triggers input_mapping, on_hit transforms, etc.
    game_engine._apply_input_mapping(input_event)
```

### Cascading Effects

When a hit destroys an entity during rollback:

```
Hit at T=0.5s destroys brick
    │
    ├─► on_destroy transform fires
    │       └─► Spawns 4 particle entities at T=0.5s
    │
    ├─► Ball collision detected at T=0.5s
    │       └─► bounce_paddle action fires
    │       └─► Ball velocity changes
    │
    └─► Score updated (+100 points)

Re-simulation continues from T=0.5s to T=1.0s:
    │
    ├─► Particles move for 0.5s (applying gravity, etc.)
    │
    ├─► Ball moves with new velocity
    │       └─► May hit another brick during re-sim
    │       └─► That brick destruction is also simulated
    │
    └─► Final state at T=1.0s reflects ALL cascading effects
```

## Visual Reconciliation

### The Problem

During the 300-700ms latency window, the player saw a **speculative** game state:
- The brick was still visible (it shouldn't have been after T=0.5s)
- The ball passed through where the brick was (it should have bounced)
- Particles weren't visible (they should have been spawned and moving)

After rollback, the **authoritative** state is different.

### Reconciliation Strategies

#### Option A: Instant Snap (Simplest)

Just replace speculative state with authoritative state. The player sees:
- Brick suddenly disappears
- Ball suddenly at different position
- Particles suddenly appear (already mid-animation)

**Pros**: Simple to implement, always correct
**Cons**: Visually jarring, can feel unfair

#### Option B: Visual Smoothing (Recommended)

Interpolate visual positions toward authoritative positions over a short period:

```python
class ReconciliationState:
    def __init__(self, entity_id: str, target_pos: Tuple[float, float]):
        self.entity_id = entity_id
        self.target_x, self.target_y = target_pos
        self.blend_time = 0.1  # 100ms blend
        self.elapsed = 0.0

def reconcile_visuals(self, dt: float) -> None:
    """Smoothly blend visual positions toward authoritative state."""
    for recon in self._pending_reconciliations[:]:
        entity = self._behavior_engine.get_entity(recon.entity_id)
        if not entity:
            self._pending_reconciliations.remove(recon)
            continue

        recon.elapsed += dt
        t = min(1.0, recon.elapsed / recon.blend_time)

        # Entity's authoritative position is already set
        # We're just smoothing the VISUAL position
        entity.visual_x = lerp(entity.visual_x, entity.x, t)
        entity.visual_y = lerp(entity.visual_y, entity.y, t)

        if t >= 1.0:
            self._pending_reconciliations.remove(recon)
```

#### Option C: Prediction Correction (Advanced)

For entities with continuous motion (like balls), predict where they "should" be and only correct the error:

```python
# If ball was at (100, 200) with velocity (300, 0)
# After 0.5s rollback, it "should" be at (250, 200)
# But authoritative state says (250, 180) due to bounce
# Error = (0, -20)
# Correct error over time, not position

error_x = authoritative_x - predicted_x
error_y = authoritative_y - predicted_y
```

### Handling Destroyed Entities

If an entity was destroyed during rollback but the player was still seeing it:

```python
def reconcile_destruction(self, entity_id: str) -> None:
    """Handle entity that should have been destroyed earlier."""
    # Option 1: Instant removal (simple)
    # Option 2: Play death animation from current point
    # Option 3: Flash/fade effect to indicate retroactive destruction

    # For now, simple removal with effect
    self._spawn_reconciliation_effect(entity_id, "poof")
```

## Integration with GameEngine

### Modified Update Loop

```python
class GameEngine(BaseGame):
    def __init__(self, ...):
        # ... existing init ...

        # Rollback state manager
        self._rollback_manager = RollbackStateManager(
            history_duration=2.0,  # 2 seconds of rollback window
            fps=60,
        )

        # Pending hits from CV (may be delayed)
        self._pending_hits: List[PlaneHitEvent] = []

        # Frame counter for deterministic updates
        self._frame_counter = 0

    def update(self, dt: float) -> None:
        """Main update loop with rollback support."""
        if self._internal_state != GameState.PLAYING:
            return

        # Capture snapshot BEFORE processing this frame
        # (so we can rollback TO this point if needed)
        if self._frame_counter % self._rollback_manager.snapshot_interval == 0:
            snapshot = self._rollback_manager.capture(self)
            self._rollback_manager.snapshots.append(snapshot)

        # Check for delayed hits that need rollback
        current_time = time.monotonic()
        delayed_hits = [h for h in self._pending_hits if h.timestamp < current_time - 0.016]

        if delayed_hits:
            self._process_delayed_hits(delayed_hits)
            for hit in delayed_hits:
                self._pending_hits.remove(hit)

        # Normal update (fixed timestep for determinism)
        self._do_update(1.0 / 60.0)
        self._frame_counter += 1

    def _process_delayed_hits(self, hits: List[PlaneHitEvent]) -> None:
        """Process hits that arrived late via rollback."""
        if not hits:
            return

        # Find earliest hit
        earliest = min(hits, key=lambda h: h.timestamp)

        # Find snapshot at or before earliest hit
        snapshot = self._rollback_manager.find_snapshot(earliest.timestamp)
        if not snapshot:
            # Hit too old - can't rollback, apply to current state
            for hit in hits:
                self._apply_hit_immediate(hit)
            return

        # Restore to snapshot
        self._rollback_manager.restore(self, snapshot)

        # Re-simulate from snapshot to now, applying hits
        current_time = time.monotonic()
        self._rollback_manager.re_simulate(
            self,
            from_time=snapshot.timestamp,
            to_time=current_time,
            pending_hits=hits,
        )
```

### Input Handling Changes

```python
def handle_input(self, events: List[InputEvent]) -> None:
    """Process input events, queueing delayed ones for rollback."""
    if self._internal_state != GameState.PLAYING:
        return

    current_time = time.monotonic()

    for event in events:
        # Check if event is delayed (CV detection)
        event_age = current_time - event.timestamp

        if event_age < 0.016:  # Less than 1 frame old - process immediately
            self._apply_input_mapping(event)
        else:
            # Delayed event - queue for rollback processing
            self._pending_hits.append(PlaneHitEvent(
                x=event.position.x / self._screen_width,
                y=event.position.y / self._screen_height,
                timestamp=event.timestamp,
                latency_ms=event_age * 1000,
            ))
```

## Impact on Lua Behaviors

### Required Changes

Lua behaviors must be rollback-safe:

1. **No Side Effects Outside Entity State**
   ```lua
   -- BAD: External state
   local global_counter = 0
   function behavior.on_update(id, dt)
       global_counter = global_counter + 1  -- Lost on rollback!
   end

   -- GOOD: State in entity properties
   function behavior.on_update(id, dt)
       local counter = ams.get_prop(id, "counter") or 0
       ams.set_prop(id, "counter", counter + 1)  -- Survives rollback
   end
   ```

2. **Deterministic Random**
   ```lua
   -- BAD: Non-deterministic
   local angle = math.random() * 360

   -- GOOD: Use seeded random through API
   local angle = ams.random_range(0, 360)  -- Seeded, deterministic
   ```

3. **No Wall-Clock Time**
   ```lua
   -- BAD: Real time
   local now = os.time()

   -- GOOD: Game time
   local now = ams.get_time()  -- Game's elapsed time, consistent across rollback
   ```

### Existing Behaviors Audit

Review all behaviors in `lua/behavior/`:

| Behavior | Rollback Safe? | Issues |
|----------|----------------|--------|
| `ball.lua` | Yes | Uses entity properties |
| `paddle.lua` | Yes | Uses entity properties |
| `brick.lua` | Yes | Uses entity properties |
| `gravity.lua` | Yes | Stateless |
| `destroy_offscreen.lua` | Yes | Stateless |
| `shoot.lua` | **Check** | Timer in properties - OK |

## Performance Considerations

### Snapshot Memory

```
Per entity: ~500 bytes (estimate)
100 entities × 120 snapshots (2s @ 60fps) = 6 MB

Mitigation:
- Snapshot every 2-3 frames instead of every frame
- Delta compression (store only changed properties)
- Pool/reuse snapshot objects
```

### Re-simulation Cost

```
Worst case: 700ms delay = 42 frames to re-simulate
At 60fps target: 16.6ms per frame budget

If re-simulation takes 0.5ms per frame:
42 frames × 0.5ms = 21ms total
+ snapshot restore overhead: ~5ms
= ~26ms spike

Mitigation:
- Limit rollback window (reject hits >1s old)
- Spread re-simulation across multiple frames if needed
- Profile and optimize hot paths
```

### Snapshot Frequency Trade-off

| Interval | Memory | Restore Accuracy | Re-sim Overhead |
|----------|--------|------------------|-----------------|
| Every frame | High | Exact | Minimal |
| Every 2 frames | Medium | ±8ms | Small |
| Every 4 frames | Low | ±33ms | Medium |

Recommendation: Start with every frame, optimize if memory is an issue.

## Implementation Phases

### Phase 1: Foundation (Core Infrastructure) - COMPLETE

1. ~~Create `RollbackStateManager` class~~ ✓
2. ~~Implement `EntitySnapshot` and `GameSnapshot` dataclasses~~ ✓
3. Add snapshot capture to GameEngine.update() - **pending integration**
4. ~~Add snapshot restoration methods~~ ✓
5. ~~Unit tests for snapshot/restore round-trip~~ ✓ (32 tests)

**Files created:**
- `ams/games/game_engine/rollback/__init__.py`
- `ams/games/game_engine/rollback/snapshot.py`
- `ams/games/game_engine/rollback/manager.py`
- `ams/games/game_engine/rollback/tests/test_rollback.py`

### Phase 2: Basic Rollback - COMPLETE (standalone)

1. ~~Implement `find_snapshot()` with timestamp search~~ ✓
2. ~~Implement `re_simulate()` with fixed timestep~~ ✓
3. Add delayed hit detection in input handling - **pending integration**
4. ~~Basic integration test with mock delayed hits~~ ✓

**Note:** The rollback system works with mock game engines in tests.
GameEngine integration requires adding `_do_frame_update()` method.

### Phase 3: Cascading Effects - NOT STARTED

1. Ensure entity destruction during rollback triggers transforms
2. Verify child spawning works during re-simulation
3. Test collision detection during re-simulation
4. Verify score/lives update correctly

### Phase 4: Visual Reconciliation - NOT STARTED

1. Add `visual_x`, `visual_y` to entities (separate from authoritative position)
2. Implement visual smoothing in render loop
3. Add reconciliation effects (poof for destroyed entities)
4. Test with actual CV backend

### Phase 5: Optimization - NOT STARTED

1. Profile memory usage, add delta compression if needed
2. Profile re-simulation performance, optimize hot paths
3. Add snapshot interval configuration
4. Consider spreading re-simulation across frames

### Phase 6: Polish - NOT STARTED

1. Add debug visualization (show rollback occurring)
2. Add metrics/logging for rollback events
3. Document behavior requirements for rollback safety
4. Update YAML game engine documentation

## Testing Strategy

### Unit Tests

```python
def test_snapshot_restore_round_trip():
    """Snapshot and restore should produce identical state."""
    game = create_test_game()

    # Run for a bit
    for _ in range(60):
        game.update(1/60)

    # Snapshot
    snapshot = manager.capture(game)

    # Modify state
    game.update(1/60)
    game.update(1/60)

    # Restore
    manager.restore(game, snapshot)

    # Verify identical
    assert game._behavior_engine.elapsed_time == snapshot.elapsed_time
    assert game._behavior_engine.score == snapshot.score
    # ... verify all entity states
```

### Integration Tests

```python
def test_delayed_hit_rollback():
    """Delayed hit should be processed via rollback."""
    game = create_test_game_with_brick_at(100, 100)

    # Run to T=0.5s
    for _ in range(30):
        game.update(1/60)

    # Simulate delayed hit arriving at T=1.0s for impact at T=0.5s
    delayed_hit = PlaneHitEvent(
        x=0.125,  # 100/800
        y=0.167,  # 100/600
        timestamp=game._rollback_manager.snapshots[30].timestamp,
    )

    # Run to T=1.0s
    for _ in range(30):
        game.update(1/60)

    # Inject delayed hit
    game._pending_hits.append(delayed_hit)
    game.update(1/60)

    # Brick should be destroyed (rollback applied hit at T=0.5s)
    assert len(game.get_entities_by_type('brick')) == 0
```

## Open Questions

1. **Should rollback be opt-in per game?**
   - Some games (simple targets) may not need it
   - Could add `rollback_enabled: true` to game.yaml

2. **How to handle sounds during rollback?**
   - Option A: Don't play sounds during re-simulation (weird if hit just happened)
   - Option B: Play sounds but time-shift (play "older" sounds quieter?)
   - Option C: Queue sounds and play with timestamp (complex)

3. **Network multiplayer implications?**
   - Future feature, but rollback architecture helps
   - Each client does local prediction + rollback on server authoritative updates

4. **Maximum rollback window?**
   - 2 seconds seems reasonable (limits memory, handles typical CV latency)
   - Configurable per detection backend?

## References

- [GGPO Rollback Netcode](https://www.ggpo.net/) - Fighting game rollback
- [Overwatch Netcode](https://www.youtube.com/watch?v=W3aieHjyNvw) - Lag compensation
- [Rocket League Physics](https://www.youtube.com/watch?v=ueEmiDM94IE) - Rollback in physics games
- [Source Engine Lag Compensation](https://developer.valvesoftware.com/wiki/Lag_compensation)

## Appendix: State Diagram

```
                    ┌─────────────────────────────────────────────────────┐
                    │                  NORMAL OPERATION                    │
                    │                                                     │
     Input ────────►│  capture_snapshot() ───► update() ───► render()    │
     (immediate)    │         │                    │              │       │
                    │         ▼                    ▼              ▼       │
                    │   [Snapshot N]         [Frame N]      [Display N]   │
                    │                                                     │
                    └───────────────────────────┬─────────────────────────┘
                                                │
                                                │ Delayed hit arrives
                                                │ (timestamp in past)
                                                ▼
                    ┌─────────────────────────────────────────────────────┐
                    │                    ROLLBACK MODE                     │
                    │                                                     │
                    │  1. find_snapshot(hit.timestamp)                    │
                    │         │                                           │
                    │         ▼                                           │
                    │  2. restore(snapshot)  ──► [State at T_hit]         │
                    │         │                                           │
                    │         ▼                                           │
                    │  3. apply_hit(hit)     ──► [Hit processed at T_hit] │
                    │         │                                           │
                    │         ▼                                           │
                    │  4. re_simulate(T_hit → T_now)                      │
                    │         │                                           │
                    │         │  For each frame:                          │
                    │         │    - Apply any other pending hits         │
                    │         │    - update(dt)                           │
                    │         │    - capture_snapshot()                   │
                    │         │                                           │
                    │         ▼                                           │
                    │  5. [Authoritative state at T_now]                  │
                    │         │                                           │
                    │         ▼                                           │
                    │  6. reconcile_visuals()                             │
                    │                                                     │
                    └───────────────────────────┬─────────────────────────┘
                                                │
                                                │ Resume
                                                ▼
                    ┌─────────────────────────────────────────────────────┐
                    │                  NORMAL OPERATION                    │
                    │                        ...                          │
                    └─────────────────────────────────────────────────────┘
```
