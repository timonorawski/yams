"""
DuckHunt-specific enumerations.

These enums define the various states and types specific to Duck Hunt gameplay.
"""

from enum import Enum

# Import common GameState for backward compatibility
from games.common.game_state import GameState


class EventType(str, Enum):
    """Types of input events.

    Attributes:
        HIT: A click/impact that hit a target
        MISS: A click/impact that missed all targets
    """
    HIT = "hit"
    MISS = "miss"


class TargetState(str, Enum):
    """States a target can be in during its lifecycle.

    Attributes:
        ALIVE: Target is active and can be hit
        HIT: Target was successfully hit by player
        MISSED: Target was shot at but missed
        ESCAPED: Target left the screen without being hit
    """
    ALIVE = "alive"
    HIT = "hit"
    MISSED = "missed"
    ESCAPED = "escaped"


class DuckHuntInternalState(str, Enum):
    """Internal states specific to DuckHunt gameplay.

    These map to the common GameState for platform compatibility:
    - MENU -> GameState.PLAYING (shown as menu within game)
    - PLAYING -> GameState.PLAYING
    - PAUSED -> GameState.PAUSED
    - WAITING_FOR_RELOAD -> GameState.RETRIEVAL
    - GAME_OVER -> GameState.GAME_OVER

    Attributes:
        MENU: Main menu/start screen
        PLAYING: Active gameplay
        PAUSED: Game paused
        WAITING_FOR_RELOAD: Projectiles depleted, waiting for AMS to handle reload/interstitial
        GAME_OVER: Game ended (win or loss)
    """
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    WAITING_FOR_RELOAD = "waiting_for_reload"
    GAME_OVER = "game_over"

    def to_game_state(self) -> GameState:
        """Convert internal state to common GameState."""
        mapping = {
            DuckHuntInternalState.MENU: GameState.PLAYING,
            DuckHuntInternalState.PLAYING: GameState.PLAYING,
            DuckHuntInternalState.PAUSED: GameState.PAUSED,
            DuckHuntInternalState.WAITING_FOR_RELOAD: GameState.RETRIEVAL,
            DuckHuntInternalState.GAME_OVER: GameState.GAME_OVER,
        }
        return mapping[self]


class EffectType(str, Enum):
    """Types of visual effects.

    Attributes:
        HIT: Visual effect for successful target hit
        MISS: Visual effect for missed shot
        EXPLOSION: Explosion effect when target is destroyed
        SCORE_POPUP: Score value popup text
    """
    HIT = "hit"
    MISS = "miss"
    EXPLOSION = "explosion"
    SCORE_POPUP = "score_popup"
