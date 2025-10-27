"""
DuckHunt-specific data models.

These models define the game-specific structures for Duck Hunt,
including targets, scoring, visual effects, and score popups.
"""

from pydantic import BaseModel, field_validator, computed_field, ConfigDict

from ..primitives import Point2D, Color, Rectangle
from .enums import TargetState, EffectType


class TargetData(BaseModel):
    """Immutable target state data.

    Encapsulates all the information needed to represent a target in the game,
    including its position, velocity, size, and current state.

    Attributes:
        position: Current position of the target center
        velocity: Velocity vector (pixels per second)
        size: Size of the target (diameter/width in pixels, must be positive)
        state: Current state of the target lifecycle

    Examples:
        >>> target = TargetData(
        ...     position=Point2D(x=100.0, y=200.0),
        ...     velocity=Point2D(x=50.0, y=0.0),
        ...     size=40.0,
        ...     state=TargetState.ALIVE
        ... )
        >>> target.is_active
        True
        >>> bounds = target.get_bounds()
    """
    position: Point2D
    velocity: Point2D
    size: float
    state: TargetState

    @field_validator('size')
    @classmethod
    def validate_size(cls, v: float) -> float:
        """Validate size is positive.

        Args:
            v: Size value to validate

        Returns:
            Validated size value

        Raises:
            ValueError: If size is not positive
        """
        if v <= 0:
            raise ValueError(f'Size must be positive, got {v}')
        return v

    @computed_field
    @property
    def is_active(self) -> bool:
        """Check if target is currently active (can be hit).

        Returns:
            True if target state is ALIVE, False otherwise
        """
        return self.state == TargetState.ALIVE

    def get_bounds(self) -> Rectangle:
        """Get bounding box for collision detection.

        The bounding box is centered on the target's position.

        Returns:
            Rectangle representing the target's bounding box

        Examples:
            >>> target = TargetData(
            ...     position=Point2D(x=100.0, y=200.0),
            ...     velocity=Point2D(x=0.0, y=0.0),
            ...     size=40.0,
            ...     state=TargetState.ALIVE
            ... )
            >>> bounds = target.get_bounds()
            >>> bounds.width
            40.0
            >>> bounds.center.x
            100.0
        """
        return Rectangle(
            x=self.position.x - self.size / 2,
            y=self.position.y - self.size / 2,
            width=self.size,
            height=self.size
        )

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"TargetData(pos={self.position}, vel={self.velocity}, size={self.size:.1f}, state={self.state.value})"


class ScoreData(BaseModel):
    """Immutable score state data.

    Tracks all scoring information for a game session, including hits,
    misses, combo tracking, and computed statistics like accuracy.

    Attributes:
        hits: Number of successful target hits (non-negative)
        misses: Number of missed shots (non-negative)
        current_combo: Current consecutive hit streak (non-negative)
        max_combo: Highest combo achieved in this session (non-negative)

    Examples:
        >>> score = ScoreData(hits=10, misses=3, current_combo=5, max_combo=7)
        >>> score.total_shots
        13
        >>> score.accuracy
        0.7692307692307693
        >>> score2 = ScoreData()  # All zeros
        >>> score2.accuracy
        0.0
    """
    hits: int = 0
    misses: int = 0
    current_combo: int = 0
    max_combo: int = 0

    @field_validator('hits', 'misses', 'current_combo', 'max_combo')
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        """Validate score values are non-negative.

        Args:
            v: Value to validate

        Returns:
            Validated value

        Raises:
            ValueError: If value is negative
        """
        if v < 0:
            raise ValueError(f'Score values must be non-negative, got {v}')
        return v

    @computed_field
    @property
    def total_shots(self) -> int:
        """Calculate total number of shots taken.

        Returns:
            Sum of hits and misses
        """
        return self.hits + self.misses

    @computed_field
    @property
    def accuracy(self) -> float:
        """Calculate hit accuracy as a percentage (0.0 to 1.0).

        Returns:
            Ratio of hits to total shots, or 0.0 if no shots taken

        Examples:
            >>> score = ScoreData(hits=7, misses=3)
            >>> score.accuracy
            0.7
            >>> score_no_shots = ScoreData()
            >>> score_no_shots.accuracy
            0.0
        """
        if self.total_shots == 0:
            return 0.0
        return self.hits / self.total_shots

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"ScoreData(hits={self.hits}, misses={self.misses}, combo={self.current_combo}, max={self.max_combo}, acc={self.accuracy:.1%})"


class VisualEffect(BaseModel):
    """Immutable visual effect data for on-screen feedback animations.

    Represents a temporary visual effect that lives for a specific duration,
    with optional color, size, and velocity properties. The effect fades out
    over its lifetime.

    Attributes:
        position: Current position of the effect center
        lifetime: Current age of the effect in seconds (non-negative)
        max_lifetime: Maximum duration before effect dies (positive)
        effect_type: Type of visual effect (hit, miss, explosion, etc.)
        color: Optional color for the effect (defaults to white)
        size: Optional size in pixels (defaults to 20.0)
        velocity: Optional velocity vector for moving effects (defaults to zero)

    Examples:
        >>> effect = VisualEffect(
        ...     position=Point2D(x=100.0, y=200.0),
        ...     lifetime=0.5,
        ...     max_lifetime=1.0,
        ...     effect_type=EffectType.HIT,
        ...     color=Color(r=0, g=255, b=0, a=255),
        ...     size=30.0
        ... )
        >>> effect.alpha  # Opacity at 50% of lifetime
        128
        >>> effect.is_alive
        True
    """
    position: Point2D
    lifetime: float
    max_lifetime: float
    effect_type: EffectType
    color: Color = Color(r=255, g=255, b=255, a=255)  # Default to white
    size: float = 20.0
    velocity: Point2D = Point2D(x=0.0, y=0.0)

    @field_validator('lifetime', 'max_lifetime')
    @classmethod
    def validate_positive_lifetime(cls, v: float) -> float:
        """Validate lifetime values are non-negative/positive.

        Args:
            v: Lifetime value to validate

        Returns:
            Validated lifetime value

        Raises:
            ValueError: If lifetime is negative or max_lifetime is not positive
        """
        if v < 0:
            raise ValueError(f'Lifetime must be non-negative, got {v}')
        return v

    @field_validator('size')
    @classmethod
    def validate_positive_size(cls, v: float) -> float:
        """Validate size is positive.

        Args:
            v: Size value to validate

        Returns:
            Validated size value

        Raises:
            ValueError: If size is not positive
        """
        if v <= 0:
            raise ValueError(f'Size must be positive, got {v}')
        return v

    @computed_field
    @property
    def alpha(self) -> int:
        """Calculate opacity based on effect lifetime (fade out effect).

        The effect fades linearly from full opacity (255) at lifetime=0
        to fully transparent (0) at lifetime=max_lifetime.

        Returns:
            Alpha value in range [0, 255], clamped to valid range

        Examples:
            >>> effect = VisualEffect(
            ...     position=Point2D(x=0.0, y=0.0),
            ...     lifetime=0.0,
            ...     max_lifetime=1.0,
            ...     effect_type=EffectType.HIT
            ... )
            >>> effect.alpha
            255
            >>> effect2 = VisualEffect(
            ...     position=Point2D(x=0.0, y=0.0),
            ...     lifetime=0.5,
            ...     max_lifetime=1.0,
            ...     effect_type=EffectType.HIT
            ... )
            >>> effect2.alpha
            128
        """
        if self.max_lifetime <= 0:
            return 0

        # Linear fade: 1.0 at start (lifetime=0), 0.0 at end (lifetime=max_lifetime)
        fade_ratio = 1.0 - (self.lifetime / self.max_lifetime)
        fade_ratio = max(0.0, min(1.0, fade_ratio))  # Clamp to [0, 1]

        return int(fade_ratio * 255)

    @computed_field
    @property
    def is_alive(self) -> bool:
        """Check if effect is still alive.

        Returns:
            True if lifetime has not exceeded max_lifetime

        Examples:
            >>> effect = VisualEffect(
            ...     position=Point2D(x=0.0, y=0.0),
            ...     lifetime=0.5,
            ...     max_lifetime=1.0,
            ...     effect_type=EffectType.HIT
            ... )
            >>> effect.is_alive
            True
            >>> dead_effect = VisualEffect(
            ...     position=Point2D(x=0.0, y=0.0),
            ...     lifetime=1.5,
            ...     max_lifetime=1.0,
            ...     effect_type=EffectType.HIT
            ... )
            >>> dead_effect.is_alive
            False
        """
        return self.lifetime < self.max_lifetime

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"VisualEffect(type={self.effect_type.value}, pos={self.position}, life={self.lifetime:.2f}/{self.max_lifetime:.2f}, alpha={self.alpha})"


class ScorePopup(BaseModel):
    """Immutable score popup text effect data.

    Represents a floating score value that appears when a target is hit,
    showing the points earned. This is a specialized visual effect for
    displaying score feedback.

    Attributes:
        position: Current position of the popup center
        value: Score value to display (can be positive or negative)
        lifetime: Current age of the popup in seconds (non-negative)
        color: Color of the popup text
        max_lifetime: Maximum duration before popup fades (positive, defaults to 1.0)
        velocity: Velocity vector for floating animation (defaults to upward)

    Examples:
        >>> popup = ScorePopup(
        ...     position=Point2D(x=100.0, y=200.0),
        ...     value=100,
        ...     lifetime=0.0,
        ...     color=Color(r=255, g=215, b=0, a=255)
        ... )
        >>> popup.alpha
        255
        >>> popup.is_alive
        True
    """
    position: Point2D
    value: int
    lifetime: float
    color: Color
    max_lifetime: float = 1.0
    velocity: Point2D = Point2D(x=0.0, y=-50.0)  # Float upward by default

    @field_validator('lifetime', 'max_lifetime')
    @classmethod
    def validate_positive_lifetime(cls, v: float) -> float:
        """Validate lifetime values are non-negative/positive.

        Args:
            v: Lifetime value to validate

        Returns:
            Validated lifetime value

        Raises:
            ValueError: If lifetime is negative or max_lifetime is not positive
        """
        if v < 0:
            raise ValueError(f'Lifetime must be non-negative, got {v}')
        return v

    @computed_field
    @property
    def alpha(self) -> int:
        """Calculate opacity based on popup lifetime (fade out effect).

        The popup fades linearly from full opacity (255) at lifetime=0
        to fully transparent (0) at lifetime=max_lifetime.

        Returns:
            Alpha value in range [0, 255], clamped to valid range
        """
        if self.max_lifetime <= 0:
            return 0

        # Linear fade: 1.0 at start (lifetime=0), 0.0 at end (lifetime=max_lifetime)
        fade_ratio = 1.0 - (self.lifetime / self.max_lifetime)
        fade_ratio = max(0.0, min(1.0, fade_ratio))  # Clamp to [0, 1]

        return int(fade_ratio * 255)

    @computed_field
    @property
    def is_alive(self) -> bool:
        """Check if popup is still alive.

        Returns:
            True if lifetime has not exceeded max_lifetime
        """
        return self.lifetime < self.max_lifetime

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"ScorePopup(value={self.value:+d}, pos={self.position}, life={self.lifetime:.2f}/{self.max_lifetime:.2f}, alpha={self.alpha})"
