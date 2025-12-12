"""
Rollback State Management for Game Engine.

Provides temporal rollback capabilities to handle CV detection latency.
When a hit is detected at time T (in the past), the system:
1. Restores game state to time T
2. Applies the hit and all cascading effects
3. Re-simulates forward to the present

Usage:
    from ams.games.game_engine.rollback import RollbackStateManager

    manager = RollbackStateManager(history_duration=2.0, fps=60)

    # In game loop:
    manager.capture_snapshot(game_engine)

    # When delayed hit arrives:
    if manager.process_delayed_hit(game_engine, hit_event):
        # Hit was processed via rollback
        pass
"""

from .snapshot import EntitySnapshot, GameSnapshot, ScheduledCallbackSnapshot
from .manager import RollbackStateManager

__all__ = [
    'EntitySnapshot',
    'GameSnapshot',
    'ScheduledCallbackSnapshot',
    'RollbackStateManager',
]
