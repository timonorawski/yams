# Projectile Limiting System

## Overview

The projectile limiting system enables physical game constraints where players have a limited number of projectiles per round (e.g., 6 arrows for archery). When projectiles are depleted, the game signals the Arcade Management System (AMS) to handle reload interstitials.

## Architecture

### Game Responsibilities
- Track projectile usage per input event
- Transition to `WAITING_FOR_RELOAD` state when depleted
- Expose status via `get_projectiles_remaining()` method
- Provide `reload()` method for AMS to call

### AMS Responsibilities
- Monitor game state via `mode.state` property
- Display interstitial screens (e.g., "Collect your arrows")
- Handle system functions during interstitials (if needed)
- Call `mode.reload()` when ready to resume

### Design Rationale
The game **does not** control interstitials because:
1. AMS may need to run system functions between rounds
2. Interstitial UI is system-level, not game-specific
3. AMS has better context for timing (e.g., physical constraints)

## Configuration

### YAML Schema

Add `projectiles_per_round` to the `rules` section:

```yaml
rules:
  game_type: "endless"
  projectiles_per_round: 6  # Optional: null or omit for unlimited
```

### Example: Archery Mode

See `modes/classic_archery.yaml` for a complete example with:
- 6 arrows per round
- Progressive difficulty across 5 levels
- Curved trajectories with 3D depth simulation

## API Reference

### GameState Enum

New state: `WAITING_FOR_RELOAD`
- Game pauses all updates (targets freeze, no spawning)
- Input events are ignored
- Signals AMS to handle reload interstitial

### DynamicGameMode Methods

```python
def get_projectiles_remaining(self) -> Optional[int]:
    """
    Get number of projectiles remaining in current round.

    Returns:
        Number of projectiles left, or None if unlimited
    """
```

```python
def reload(self) -> None:
    """
    Reload projectiles and resume gameplay.

    Called by AMS after handling interstitial screens.
    Resets projectile count and transitions to PLAYING state.
    """
```

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. PLAYING: Game active, projectiles = 6                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Player shoots (input event)
                         │ projectiles -= 1
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. PLAYING: Game active, projectiles = 5, 4, 3, 2, 1       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Player shoots last arrow
                         │ projectiles = 0
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. WAITING_FOR_RELOAD: Game paused, projectiles = 0        │
│    - Targets freeze                                          │
│    - No new spawns                                           │
│    - Input ignored                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ AMS detects state change
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. AMS displays interstitial:                               │
│    "OUT OF ARROWS! Please collect your arrows."            │
│    - May run system functions (calibration, maintenance)    │
│    - Waits for timer or user confirmation                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ AMS calls mode.reload()
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. PLAYING: Game resumed, projectiles = 6                   │
│    Cycle repeats                                             │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Details

### Projectile Counter Decrement

Projectiles are decremented on **every input event**, not just hits:
- Each click/shot uses one projectile
- Misses count towards depletion
- This matches physical reality (you can't "unshoot" an arrow)

### State Transition Timing

Transition to `WAITING_FOR_RELOAD` happens **immediately** after the last projectile is used:
```python
# After processing input event
if self._projectiles_remaining <= 0:
    self._state = GameState.WAITING_FOR_RELOAD
    return  # Stop processing further events
```

### Unlimited Mode

If `projectiles_per_round` is `None` or omitted:
- `get_projectiles_remaining()` returns `None`
- No counter decrement occurs
- Game never transitions to `WAITING_FOR_RELOAD`

## Testing

Run the test suite:
```bash
./venv/bin/python test_projectile_limiting.py
```

Tests verify:
1. ✓ YAML validation and loading
2. ✓ Projectile counter initialization
3. ✓ Counter decrement on input
4. ✓ State transition when depleted
5. ✓ Input rejection in WAITING_FOR_RELOAD
6. ✓ reload() restores projectiles and state
7. ✓ Unlimited mode (None) works correctly

## Demo

Run the interactive demo:
```bash
./venv/bin/python demo_archery_reload.py
```

Features:
- Visual projectile counter in HUD
- Interstitial overlay when depleted
- Auto-reload after 5 seconds (simulates AMS behavior)
- Manual reload with 'R' key
- Progress bar showing reload timer

## Integration Example

```python
from game.mode_loader import GameModeLoader
from game.modes.dynamic import DynamicGameMode
from models import GameState

# Load archery mode
loader = GameModeLoader()
config = loader.load_mode("classic_archery")
mode = DynamicGameMode(config)

# Game loop
while True:
    # Update game
    mode.update(dt)

    # Check if reload needed
    if mode.state == GameState.WAITING_FOR_RELOAD:
        # AMS displays interstitial
        display_interstitial("Collect your arrows!")

        # Wait for timer or user confirmation
        wait_for_reload_ready()

        # Resume gameplay
        mode.reload()

    # Process input events
    if mode.state == GameState.PLAYING:
        events = get_input_events()
        mode.handle_input(events)

        # Optional: Show projectile count in UI
        remaining = mode.get_projectiles_remaining()
        if remaining is not None:
            display_hud(f"Arrows: {remaining}")
```

## Files Modified

### Core System
- `models.py`: Added `WAITING_FOR_RELOAD` state to `GameState` enum
- `models/game_mode_config.py`: Added `projectiles_per_round` field to `RulesConfig`
- `game/modes/dynamic.py`: Implemented projectile tracking and reload logic

### Configurations
- `modes/classic_archery.yaml`: Example archery mode with 6 arrows per round

### Testing & Demos
- `test_projectile_limiting.py`: Comprehensive test suite (7 tests, all passing)
- `demo_archery_reload.py`: Interactive demo showing AMS integration

## Future Enhancements

Possible extensions (not currently implemented):
- Per-level projectile limits (e.g., harder levels give fewer arrows)
- Projectile replenishment bonuses (hit X targets, get bonus arrow)
- Time-based reloads (auto-reload after N seconds in-game)
- Reload animations/feedback in the game rendering

## Notes

- Projectile limiting is **optional** - games work unchanged without it
- The system is **use-case agnostic** - works for any physical projectile game
- AMS integration is **non-invasive** - simple state checking and method call
- Backwards compatible - existing YAML configs without `projectiles_per_round` work unchanged
