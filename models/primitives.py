"""
Shared primitive data types for the game engine.

This module provides basic geometric and color types used throughout
the codebase, including calibration, games, and the AMS system.
"""

from pydantic import BaseModel, Field, field_validator, computed_field, ConfigDict
from typing import Tuple


class Point2D(BaseModel):
    """Immutable 2D point/vector for positions, velocities, and coordinates.

    This is the unified type used throughout the system for any 2D coordinate,
    whether it's a position, velocity, offset, or dimension.

    Coordinates can be positive, negative, or zero, allowing for:
    - Screen positions
    - Camera coordinates
    - Velocity vectors
    - Normalized coordinates [0, 1]

    Attributes:
        x: X coordinate (horizontal)
        y: Y coordinate (vertical)

    Examples:
        >>> pos = Point2D(x=100.0, y=200.0)
        >>> vel = Point2D(x=-50.0, y=25.0)  # Moving left and down
        >>> normalized = Point2D(x=0.5, y=0.5)  # Center of screen
    """
    x: float
    y: float

    model_config = ConfigDict(frozen=True)  # Immutable

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"Point2D(x={self.x:.2f}, y={self.y:.2f})"


# Alias for backward compatibility with DuckHunt code
Vector2D = Point2D


class Resolution(BaseModel):
    """Display, camera, or projector resolution.

    Represents pixel dimensions for any display device.

    Attributes:
        width: Width in pixels (must be positive)
        height: Height in pixels (must be positive)

    Examples:
        >>> fullhd = Resolution(width=1920, height=1080)
        >>> fullhd.aspect_ratio
        1.7777777777777777
    """
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)

    @computed_field
    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio (width / height)."""
        return self.width / self.height

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"Resolution({self.width}x{self.height})"


class Color(BaseModel):
    """Immutable RGBA color with validation.

    All color components must be in the range [0, 255] inclusive.

    Attributes:
        r: Red component (0-255)
        g: Green component (0-255)
        b: Blue component (0-255)
        a: Alpha/opacity component (0-255), where 255 is fully opaque

    Examples:
        >>> red = Color(r=255, g=0, b=0, a=255)
        >>> semi_transparent_blue = Color(r=0, g=0, b=255, a=128)
        >>> white = Color(r=255, g=255, b=255, a=255)
    """
    r: int
    g: int
    b: int
    a: int = 255  # Default to fully opaque

    @field_validator('r', 'g', 'b', 'a')
    @classmethod
    def validate_color_range(cls, v: int) -> int:
        """Validate color components are in valid range [0, 255]."""
        if not 0 <= v <= 255:
            raise ValueError(f'Color component must be in range [0, 255], got {v}')
        return v

    @computed_field
    @property
    def as_tuple(self) -> Tuple[int, int, int, int]:
        """Return color as RGBA tuple for pygame compatibility.

        Returns:
            Tuple of (r, g, b, a) values
        """
        return (self.r, self.g, self.b, self.a)

    @computed_field
    @property
    def as_rgb_tuple(self) -> Tuple[int, int, int]:
        """Return color as RGB tuple (without alpha).

        Returns:
            Tuple of (r, g, b) values
        """
        return (self.r, self.g, self.b)

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"Color(r={self.r}, g={self.g}, b={self.b}, a={self.a})"


class Rectangle(BaseModel):
    """Immutable rectangle defined by position and dimensions.

    Used for bounding boxes, collision detection, and UI elements.
    Position is at top-left corner (pygame convention).

    Attributes:
        x: X coordinate of top-left corner
        y: Y coordinate of top-left corner
        width: Width of rectangle (must be positive)
        height: Height of rectangle (must be positive)

    Examples:
        >>> rect = Rectangle(x=100.0, y=100.0, width=50.0, height=50.0)
        >>> rect.area
        2500.0
        >>> rect.contains_point(Point2D(x=125.0, y=125.0))
        True
    """
    x: float
    y: float
    width: float
    height: float

    @field_validator('width', 'height')
    @classmethod
    def validate_positive_dimensions(cls, v: float) -> float:
        """Validate dimensions are positive."""
        if v <= 0:
            raise ValueError(f'Rectangle dimensions must be positive, got {v}')
        return v

    @computed_field
    @property
    def area(self) -> float:
        """Calculate the area of the rectangle.

        Returns:
            Area in square pixels
        """
        return self.width * self.height

    @computed_field
    @property
    def center(self) -> Point2D:
        """Calculate the center point of the rectangle.

        Returns:
            Point2D at the center of the rectangle
        """
        return Point2D(
            x=self.x + self.width / 2,
            y=self.y + self.height / 2
        )

    @computed_field
    @property
    def left(self) -> float:
        """Get left edge x coordinate."""
        return self.x

    @computed_field
    @property
    def right(self) -> float:
        """Get right edge x coordinate."""
        return self.x + self.width

    @computed_field
    @property
    def top(self) -> float:
        """Get top edge y coordinate."""
        return self.y

    @computed_field
    @property
    def bottom(self) -> float:
        """Get bottom edge y coordinate."""
        return self.y + self.height

    def contains_point(self, point: Point2D) -> bool:
        """Check if a point is inside the rectangle.

        Args:
            point: The point to check

        Returns:
            True if point is inside or on the boundary of the rectangle

        Examples:
            >>> rect = Rectangle(x=0.0, y=0.0, width=100.0, height=100.0)
            >>> rect.contains_point(Point2D(x=50.0, y=50.0))
            True
            >>> rect.contains_point(Point2D(x=150.0, y=50.0))
            False
        """
        return (self.left <= point.x <= self.right and
                self.top <= point.y <= self.bottom)

    def intersects(self, other: 'Rectangle') -> bool:
        """Check if this rectangle intersects with another rectangle.

        Args:
            other: Another rectangle to check intersection with

        Returns:
            True if rectangles overlap

        Examples:
            >>> rect1 = Rectangle(x=0.0, y=0.0, width=100.0, height=100.0)
            >>> rect2 = Rectangle(x=50.0, y=50.0, width=100.0, height=100.0)
            >>> rect1.intersects(rect2)
            True
        """
        return not (self.right < other.left or
                   self.left > other.right or
                   self.bottom < other.top or
                   self.top > other.bottom)

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"Rectangle(x={self.x:.2f}, y={self.y:.2f}, w={self.width:.2f}, h={self.height:.2f})"
