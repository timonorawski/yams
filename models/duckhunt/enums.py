"""
DuckHunt-specific enumerations.

These enums define the various states and types specific to Duck Hunt gameplay.
"""

from enum import Enum


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


class GameState(str, Enum):
    """States of the overall game.

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
