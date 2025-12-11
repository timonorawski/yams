"""
Gradient Test Game - CV Pipeline Validation Tool.

Projects a position-encoded gradient where color encodes (x, y) position.
Each hit shows:
- Detected position (where the system thinks you hit)
- Actual position (decoded from gradient color at detected location)
- Error between them

Used for tuning and validating detection accuracy.
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pygame

from ams.games import GameState
from ams.games.base_game import BaseGame
from ams.games.input import InputEvent
from games.Gradient import config


@dataclass
class HitMarker:
    """Record of a single hit with error data."""
    detected_x: float  # Normalized [0,1] detected position
    detected_y: float
    actual_x: float    # Normalized [0,1] actual position (from gradient)
    actual_y: float
    error: float       # Distance as fraction of screen diagonal
    timestamp: float   # When hit occurred


@dataclass
class HitStats:
    """Accumulated statistics across all hits."""
    hits: List[HitMarker] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.hits)

    @property
    def mean_error(self) -> float:
        if not self.hits:
            return 0.0
        return sum(h.error for h in self.hits) / len(self.hits)

    @property
    def max_error(self) -> float:
        if not self.hits:
            return 0.0
        return max(h.error for h in self.hits)

    @property
    def min_error(self) -> float:
        if not self.hits:
            return 0.0
        return min(h.error for h in self.hits)

    @property
    def std_error(self) -> float:
        if len(self.hits) < 2:
            return 0.0
        mean = self.mean_error
        variance = sum((h.error - mean) ** 2 for h in self.hits) / len(self.hits)
        return math.sqrt(variance)


class GradientMode(BaseGame):
    """
    Gradient Test Game for CV pipeline validation.

    Projects a persistent position-encoded gradient. Each hit:
    1. Draws a marker at the detected position
    2. Computes error vs actual position (from gradient encoding)
    3. Displays running statistics
    """

    NAME = "Gradient Test"
    DESCRIPTION = "CV pipeline validation - hit anywhere, see detection accuracy"
    VERSION = "1.0.0"
    AUTHOR = "AMS Team"

    ARGUMENTS = [
        {
            'name': '--encoding',
            'type': str,
            'default': 'checkerboard',
            'choices': ['rgb', 'hsv', 'checkerboard'],
            'help': 'Gradient encoding method (rgb=position as color, hsv=hue wheel, checkerboard=grid pattern)'
        },
        {
            'name': '--show-grid',
            'action': 'store_true',
            'default': True,
            'help': 'Show grid overlay for visual reference'
        },
        {
            'name': '--clear-on-r',
            'action': 'store_true',
            'default': True,
            'help': 'Clear markers when R is pressed (default: true)'
        },
    ]

    def __init__(
        self,
        encoding: str = 'checkerboard',
        show_grid: bool = False,
        clear_on_r: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self._encoding = encoding
        self._show_grid = show_grid
        self._clear_on_r = clear_on_r

        # Hit tracking
        self._stats = HitStats()
        self._last_hit: Optional[HitMarker] = None

        # Gradient surface (pre-rendered for performance)
        self._gradient_surface: Optional[pygame.Surface] = None
        self._gradient_rect: Optional[pygame.Rect] = None

        # Fonts
        self._font: Optional[pygame.font.Font] = None
        self._font_large: Optional[pygame.font.Font] = None
        self._font_small: Optional[pygame.font.Font] = None

        # Game state
        self._internal_state = GameState.PLAYING
        self._time = 0.0

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 32)
        return self._font

    def _get_font_large(self) -> pygame.font.Font:
        if self._font_large is None:
            self._font_large = pygame.font.Font(None, 48)
        return self._font_large

    def _get_font_small(self) -> pygame.font.Font:
        if self._font_small is None:
            self._font_small = pygame.font.Font(None, 24)
        return self._font_small

    def _get_internal_state(self) -> GameState:
        return self._internal_state

    def get_score(self) -> int:
        """Return hit count as score."""
        return self._stats.count

    def _encode_position_rgb(self, x: float, y: float) -> Tuple[int, int, int]:
        """Encode normalized [0,1] position as RGB color."""
        # X → Red, Y → Green, checksum → Blue
        r = int(x * 255)
        g = int(y * 255)
        b = (r + g) % 256
        return (r, g, b)

    def _decode_color_rgb(self, r: int, g: int, b: int) -> Tuple[float, float]:
        """Decode RGB color to normalized position."""
        x = r / 255.0
        y = g / 255.0
        return (x, y)

    def _encode_position_hsv(self, x: float, y: float) -> Tuple[int, int, int]:
        """Encode position using HSV (hue wheel, saturation/value for position)."""
        # Angle from center → Hue
        # Distance from center → Saturation
        cx, cy = 0.5, 0.5
        dx, dy = x - cx, y - cy
        angle = math.atan2(dy, dx)
        hue = (angle + math.pi) / (2 * math.pi)  # 0-1
        dist = min(1.0, math.sqrt(dx*dx + dy*dy) * 2)

        # Convert HSV to RGB
        h = hue * 6
        c = dist
        x_c = c * (1 - abs(h % 2 - 1))

        if h < 1:
            r, g, b = c, x_c, 0
        elif h < 2:
            r, g, b = x_c, c, 0
        elif h < 3:
            r, g, b = 0, c, x_c
        elif h < 4:
            r, g, b = 0, x_c, c
        elif h < 5:
            r, g, b = x_c, 0, c
        else:
            r, g, b = c, 0, x_c

        # Add minimum brightness
        m = 0.2
        return (int((r + m) * 200), int((g + m) * 200), int((b + m) * 200))

    def _encode_position_checkerboard(self, x: float, y: float) -> Tuple[int, int, int]:
        """Encode position as checkerboard with color gradient."""
        # Grid cell determines base pattern
        grid_size = 8
        gx = int(x * grid_size)
        gy = int(y * grid_size)

        # Alternate pattern
        is_light = (gx + gy) % 2 == 0

        # Color gradient within cell
        base_r = int(x * 200) + 55
        base_g = int(y * 200) + 55

        if is_light:
            return (base_r, base_g, 200)
        else:
            return (base_r // 2, base_g // 2, 100)

    def _encode_position(self, x: float, y: float) -> Tuple[int, int, int]:
        """Encode position using current encoding method."""
        if self._encoding == 'hsv':
            return self._encode_position_hsv(x, y)
        elif self._encoding == 'checkerboard':
            return self._encode_position_checkerboard(x, y)
        else:  # rgb
            return self._encode_position_rgb(x, y)

    def _create_gradient_surface(self, width: int, height: int) -> pygame.Surface:
        """Create pre-rendered gradient surface."""
        surface = pygame.Surface((width, height))

        for py in range(height):
            for px in range(width):
                # Normalize to [0, 1]
                nx = px / (width - 1) if width > 1 else 0.5
                ny = py / (height - 1) if height > 1 else 0.5

                color = self._encode_position(nx, ny)
                surface.set_at((px, py), color)

        return surface

    def _get_gradient_rect(self, screen_width: int, screen_height: int) -> pygame.Rect:
        """Calculate gradient display area."""
        # Leave room for header and stats
        x = config.MARGIN
        y = config.HEADER_HEIGHT
        w = screen_width - config.STATS_WIDTH - config.MARGIN * 2
        h = screen_height - config.HEADER_HEIGHT - config.MARGIN

        return pygame.Rect(x, y, w, h)

    def _screen_to_gradient(self, screen_x: float, screen_y: float,
                           screen_w: int, screen_h: int) -> Tuple[float, float]:
        """Convert screen coordinates to gradient-normalized coordinates."""
        if self._gradient_rect is None:
            return (0.5, 0.5)

        rect = self._gradient_rect

        # Clamp to gradient area
        gx = max(0, min(screen_x - rect.x, rect.width - 1))
        gy = max(0, min(screen_y - rect.y, rect.height - 1))

        # Normalize
        nx = gx / (rect.width - 1) if rect.width > 1 else 0.5
        ny = gy / (rect.height - 1) if rect.height > 1 else 0.5

        return (nx, ny)

    def _gradient_to_screen(self, gx: float, gy: float) -> Tuple[int, int]:
        """Convert gradient-normalized coordinates to screen coordinates."""
        if self._gradient_rect is None:
            return (0, 0)

        rect = self._gradient_rect
        sx = int(rect.x + gx * (rect.width - 1))
        sy = int(rect.y + gy * (rect.height - 1))

        return (sx, sy)

    def _sample_gradient(self, nx: float, ny: float) -> Tuple[float, float]:
        """Sample the actual position from gradient color at normalized coords."""
        if self._gradient_surface is None:
            return (nx, ny)

        # Get pixel coordinates in gradient
        px = int(nx * (self._gradient_surface.get_width() - 1))
        py = int(ny * (self._gradient_surface.get_height() - 1))

        # Clamp
        px = max(0, min(px, self._gradient_surface.get_width() - 1))
        py = max(0, min(py, self._gradient_surface.get_height() - 1))

        # Sample color
        color = self._gradient_surface.get_at((px, py))

        # Decode based on encoding method
        if self._encoding == 'rgb':
            return self._decode_color_rgb(color.r, color.g, color.b)
        else:
            # For HSV and checkerboard, actual position IS the input position
            # (these encodings aren't invertible, so we use input as "actual")
            return (nx, ny)

    def _compute_error(self, detected: Tuple[float, float],
                      actual: Tuple[float, float]) -> float:
        """Compute error as fraction of screen diagonal."""
        dx = detected[0] - actual[0]
        dy = detected[1] - actual[1]
        # Diagonal of normalized [0,1] square is sqrt(2)
        return math.sqrt(dx*dx + dy*dy) / math.sqrt(2)

    def _get_error_color(self, error: float) -> Tuple[int, int, int]:
        """Get marker color based on error magnitude."""
        if error < config.ERROR_EXCELLENT:
            return config.MARKER_EXCELLENT
        elif error < config.ERROR_GOOD:
            return config.MARKER_GOOD
        elif error < config.ERROR_WARNING:
            return config.MARKER_WARNING
        elif error < config.ERROR_BAD:
            return config.MARKER_BAD
        else:
            return config.MARKER_TERRIBLE

    def update(self, dt: float) -> None:
        """Update game state."""
        self._time += dt

        # Handle retrieval (not really needed for this game but keeps interface consistent)
        if self._in_retrieval:
            if self._quiver and not self._quiver.is_manual_retrieval:
                if self._update_retrieval(dt):
                    self._end_retrieval()
            return

    def handle_input(self, events: List[InputEvent]) -> None:
        """Process input events."""
        if self._internal_state != GameState.PLAYING:
            return

        for event in events:
            # Get screen dimensions
            screen = pygame.display.get_surface()
            if screen is None:
                continue

            screen_w, screen_h = screen.get_width(), screen.get_height()

            # Ensure gradient is created
            if self._gradient_rect is None:
                self._gradient_rect = self._get_gradient_rect(screen_w, screen_h)
                self._gradient_surface = self._create_gradient_surface(
                    self._gradient_rect.width,
                    self._gradient_rect.height
                )

            # Convert screen position to gradient position
            detected = self._screen_to_gradient(
                event.position.x, event.position.y,
                screen_w, screen_h
            )

            # Sample actual position from gradient
            actual = self._sample_gradient(detected[0], detected[1])

            # Compute error
            error = self._compute_error(detected, actual)

            # Create marker
            marker = HitMarker(
                detected_x=detected[0],
                detected_y=detected[1],
                actual_x=actual[0],
                actual_y=actual[1],
                error=error,
                timestamp=self._time,
            )

            self._stats.hits.append(marker)
            self._last_hit = marker

            # Use shot from quiver if applicable
            if self._use_shot():
                self._start_retrieval()

    def handle_pygame_event(self, event: pygame.event.Event) -> bool:
        """Handle pygame events (for R to clear)."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_c:
                # Clear markers
                self._stats = HitStats()
                self._last_hit = None
                return True
        return False

    def render(self, screen: pygame.Surface) -> None:
        """Render the game."""
        screen_w, screen_h = screen.get_width(), screen.get_height()

        # Background
        screen.fill(config.BACKGROUND_COLOR)

        # Ensure gradient is created
        if self._gradient_rect is None:
            self._gradient_rect = self._get_gradient_rect(screen_w, screen_h)
            self._gradient_surface = self._create_gradient_surface(
                self._gradient_rect.width,
                self._gradient_rect.height
            )

        # Draw gradient
        if self._gradient_surface is not None:
            screen.blit(self._gradient_surface, self._gradient_rect.topleft)

        # Draw grid overlay if enabled
        if self._show_grid:
            self._render_grid(screen)

        # Draw gradient border
        pygame.draw.rect(screen, (100, 100, 100), self._gradient_rect, 2)

        # Draw all hit markers
        self._render_markers(screen)

        # Draw header
        self._render_header(screen)

        # Draw stats panel
        self._render_stats(screen)

        # Draw last hit details
        if self._last_hit:
            self._render_last_hit(screen)

        # Draw retrieval overlay if needed
        if self.state == GameState.RETRIEVAL:
            self._render_retrieval(screen)

    def _render_grid(self, screen: pygame.Surface) -> None:
        """Render grid overlay."""
        if self._gradient_rect is None:
            return

        rect = self._gradient_rect
        grid_color = (80, 80, 80)
        grid_size = 8

        # Vertical lines
        for i in range(1, grid_size):
            x = rect.x + int(rect.width * i / grid_size)
            pygame.draw.line(screen, grid_color, (x, rect.y), (x, rect.y + rect.height))

        # Horizontal lines
        for i in range(1, grid_size):
            y = rect.y + int(rect.height * i / grid_size)
            pygame.draw.line(screen, grid_color, (rect.x, y), (rect.x + rect.width, y))

    def _render_markers(self, screen: pygame.Surface) -> None:
        """Render all hit markers."""
        for marker in self._stats.hits:
            # Get screen position
            sx, sy = self._gradient_to_screen(marker.detected_x, marker.detected_y)

            # Get color based on error
            color = self._get_error_color(marker.error)

            # Draw outer ring
            pygame.draw.circle(screen, color, (sx, sy), config.MARKER_RADIUS, 2)

            # Draw inner dot
            pygame.draw.circle(screen, color, (sx, sy), config.MARKER_INNER_RADIUS)

            # Draw error line to actual position (if RGB encoding)
            if self._encoding == 'rgb' and marker.error > 0.001:
                ax, ay = self._gradient_to_screen(marker.actual_x, marker.actual_y)
                pygame.draw.line(screen, color, (sx, sy), (ax, ay), config.ERROR_LINE_WIDTH)

    def _render_header(self, screen: pygame.Surface) -> None:
        """Render header with title."""
        font_large = self._get_font_large()
        font = self._get_font()

        # Title
        title = font_large.render("GRADIENT TEST", True, config.TEXT_COLOR)
        screen.blit(title, (config.MARGIN, config.MARGIN))

        # Encoding mode
        mode_text = font.render(f"Encoding: {self._encoding.upper()}", True, config.HEADER_COLOR)
        screen.blit(mode_text, (config.MARGIN, config.MARGIN + 40))

        # Instructions
        font_small = self._get_font_small()
        instr = font_small.render("Hit anywhere on gradient | C to clear markers", True, (150, 150, 150))
        screen.blit(instr, (config.MARGIN + 250, config.MARGIN + 45))

    def _render_stats(self, screen: pygame.Surface) -> None:
        """Render statistics panel."""
        font = self._get_font()
        font_small = self._get_font_small()

        # Panel position (right side)
        screen_w = screen.get_width()
        x = screen_w - config.STATS_WIDTH + config.MARGIN
        y = config.HEADER_HEIGHT

        # Panel background
        panel_rect = pygame.Rect(
            screen_w - config.STATS_WIDTH,
            config.HEADER_HEIGHT - 10,
            config.STATS_WIDTH,
            300
        )
        pygame.draw.rect(screen, (30, 30, 40), panel_rect)
        pygame.draw.rect(screen, (60, 60, 70), panel_rect, 1)

        # Stats header
        header = font.render("STATISTICS", True, config.TEXT_COLOR)
        screen.blit(header, (x, y))
        y += 35

        # Hit count
        hits_text = font.render(f"Hits: {self._stats.count}", True, config.TEXT_COLOR)
        screen.blit(hits_text, (x, y))
        y += 30

        if self._stats.count > 0:
            # Mean error
            mean_pct = self._stats.mean_error * 100
            mean_color = self._get_error_color(self._stats.mean_error)
            mean_text = font.render(f"Mean error: {mean_pct:.2f}%", True, mean_color)
            screen.blit(mean_text, (x, y))
            y += 30

            # Max error
            max_pct = self._stats.max_error * 100
            max_color = self._get_error_color(self._stats.max_error)
            max_text = font.render(f"Max error: {max_pct:.2f}%", True, max_color)
            screen.blit(max_text, (x, y))
            y += 30

            # Min error
            min_pct = self._stats.min_error * 100
            min_color = self._get_error_color(self._stats.min_error)
            min_text = font.render(f"Min error: {min_pct:.2f}%", True, min_color)
            screen.blit(min_text, (x, y))
            y += 30

            # Std dev
            std_pct = self._stats.std_error * 100
            std_text = font_small.render(f"Std dev: {std_pct:.2f}%", True, config.HEADER_COLOR)
            screen.blit(std_text, (x, y))
            y += 25

        # Legend
        y += 20
        legend_header = font_small.render("Error thresholds:", True, config.HEADER_COLOR)
        screen.blit(legend_header, (x, y))
        y += 20

        thresholds = [
            (config.MARKER_EXCELLENT, "< 1%", "Excellent"),
            (config.MARKER_GOOD, "1-2%", "Good"),
            (config.MARKER_WARNING, "2-3%", "Warning"),
            (config.MARKER_BAD, "3-5%", "Bad"),
            (config.MARKER_TERRIBLE, "> 5%", "Terrible"),
        ]

        for color, range_text, label in thresholds:
            pygame.draw.circle(screen, color, (x + 8, y + 8), 6)
            text = font_small.render(f"{range_text} - {label}", True, color)
            screen.blit(text, (x + 22, y))
            y += 18

    def _render_last_hit(self, screen: pygame.Surface) -> None:
        """Render details of last hit."""
        if self._last_hit is None:
            return

        font = self._get_font()
        font_small = self._get_font_small()

        # Position below stats panel
        screen_w = screen.get_width()
        x = screen_w - config.STATS_WIDTH + config.MARGIN
        y = config.HEADER_HEIGHT + 320

        # Panel background
        panel_rect = pygame.Rect(
            screen_w - config.STATS_WIDTH,
            y - 10,
            config.STATS_WIDTH,
            150
        )
        pygame.draw.rect(screen, (30, 30, 40), panel_rect)
        pygame.draw.rect(screen, (60, 60, 70), panel_rect, 1)

        # Header
        header = font.render("LAST HIT", True, config.TEXT_COLOR)
        screen.blit(header, (x, y))
        y += 30

        hit = self._last_hit
        error_color = self._get_error_color(hit.error)

        # Detected position
        det_text = font_small.render(
            f"Detected: ({hit.detected_x:.3f}, {hit.detected_y:.3f})",
            True, config.TEXT_COLOR
        )
        screen.blit(det_text, (x, y))
        y += 22

        # Actual position (only meaningful for RGB encoding)
        if self._encoding == 'rgb':
            act_text = font_small.render(
                f"Actual:   ({hit.actual_x:.3f}, {hit.actual_y:.3f})",
                True, config.HEADER_COLOR
            )
            screen.blit(act_text, (x, y))
            y += 22

        # Error
        error_pct = hit.error * 100
        error_text = font.render(f"Error: {error_pct:.2f}%", True, error_color)
        screen.blit(error_text, (x, y))

    def _render_retrieval(self, screen: pygame.Surface) -> None:
        """Render retrieval overlay."""
        if not self._quiver:
            return

        font_large = self._get_font_large()
        font = self._get_font()

        screen_w, screen_h = screen.get_width(), screen.get_height()

        # Semi-transparent overlay
        overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        # Title
        title = font_large.render("RETRIEVAL", True, (255, 200, 100))
        title_rect = title.get_rect(center=(screen_w // 2, screen_h // 2 - 30))
        screen.blit(title, title_rect)

        # Instructions
        instr = font.render(self._quiver.get_retrieval_text(), True, config.TEXT_COLOR)
        instr_rect = instr.get_rect(center=(screen_w // 2, screen_h // 2 + 20))
        screen.blit(instr, instr_rect)
