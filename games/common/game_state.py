"""Common GameState enum for all AMS games.

All games must use this standard GameState enum for compatibility with
dev_game.py, ams_game.py, and the game registry.

Games can have additional internal states, but must map them to these
standard states via the `state` property.
"""
from enum import Enum


class GameState(Enum):
    """Standard game states used by the AMS platform.

    All games must report one of these states via their `state` property.
    Games may have additional internal states, but the external interface
    must use these values.

    States:
        PLAYING: Active gameplay in progress
        PAUSED: Game temporarily paused (manual pause)
        RETRIEVAL: Paused for physical ammo retrieval (quiver empty)
        GAME_OVER: Game ended in loss/failure
        WON: Game ended in success/victory

    Usage in game_mode.py:
        from games.common.game_state import GameState

        class MyGameMode:
            def __init__(self):
                self._state = GameState.PLAYING

            @property
            def state(self) -> GameState:
                return self._state

    For games with internal states:
        class MyGameMode:
            def __init__(self):
                self._internal_state = "level_complete"  # internal detail

            @property
            def state(self) -> GameState:
                # Map internal state to standard state
                if self._internal_state in ("escaped", "died", "failed"):
                    return GameState.GAME_OVER
                elif self._internal_state in ("won", "completed", "time_up"):
                    return GameState.WON
                elif self._internal_state == "retrieving":
                    return GameState.RETRIEVAL
                else:
                    return GameState.PLAYING
    """
    PLAYING = "playing"
    PAUSED = "paused"
    RETRIEVAL = "retrieval"
    GAME_OVER = "game_over"
    WON = "won"
