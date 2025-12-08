"""Level Chooser UI for Containment game.

A tile-based level selection screen that can be navigated with mouse clicks
or projectile hits in AMS mode.
"""
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Callable

import pygame

from models import Vector2D
from games.Containment.levels import (
    list_levels,
    get_level_info,
    get_levels_dir,
)


@dataclass
class LevelTile:
    """A selectable level tile."""
    path: Path
    name: str
    description: str
    difficulty: int
    author: str
    rect: pygame.Rect
    selected: bool = False
    hover: bool = False


class LevelChooser:
    """Tile-based level selection UI.

    Features:
    - Grid of level tiles with name, description, difficulty
    - Mouse/click selection
    - Visual feedback on hover/selection
    - Difficulty indicators (stars or color coding)
    - Back option to return to default mode
    """

    # Layout constants
    TILE_WIDTH = 280
    TILE_HEIGHT = 120
    TILE_MARGIN = 20
    TILES_PER_ROW = 3

    # Colors
    BG_COLOR = (20, 20, 30)
    TILE_COLOR = (40, 45, 60)
    TILE_HOVER_COLOR = (55, 60, 80)
    TILE_SELECTED_COLOR = (70, 100, 140)
    TEXT_COLOR = (220, 220, 230)
    TEXT_DIM_COLOR = (140, 140, 160)
    DIFFICULTY_COLORS = [
        (100, 200, 100),  # 1 - Easy (green)
        (180, 200, 100),  # 2 - Medium-easy
        (220, 180, 80),   # 3 - Medium (yellow)
        (220, 130, 80),   # 4 - Hard (orange)
        (200, 80, 80),    # 5 - Very hard (red)
    ]
    ACCENT_COLOR = (100, 180, 255)

    def __init__(
        self,
        screen_width: int = 1280,
        screen_height: int = 720,
        on_level_selected: Optional[Callable[[str], None]] = None,
        on_back: Optional[Callable[[], None]] = None,
    ):
        """Initialize the level chooser.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            on_level_selected: Callback when a level is selected (receives level path)
            on_back: Callback when back/default is selected
        """
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._on_level_selected = on_level_selected
        self._on_back = on_back

        # State
        self._tiles: List[LevelTile] = []
        self._back_rect: Optional[pygame.Rect] = None
        self._scroll_offset = 0
        self._max_scroll = 0
        self._selected_level: Optional[str] = None

        # Load levels
        self._load_levels()
        self._layout_tiles()

    def _load_levels(self) -> None:
        """Load available levels from the levels directory."""
        self._tiles = []

        # Get all level files
        level_paths = list_levels()

        for path in level_paths:
            info = get_level_info(path)
            tile = LevelTile(
                path=path,
                name=info.get("name", path.stem),
                description=info.get("description", ""),
                difficulty=info.get("difficulty", 1),
                author=info.get("author", "unknown"),
                rect=pygame.Rect(0, 0, self.TILE_WIDTH, self.TILE_HEIGHT),
            )
            self._tiles.append(tile)

        # Sort by difficulty, then name
        self._tiles.sort(key=lambda t: (t.difficulty, t.name))

    def _layout_tiles(self) -> None:
        """Calculate tile positions based on screen size."""
        # Calculate grid dimensions
        total_tile_width = self.TILE_WIDTH + self.TILE_MARGIN
        total_tile_height = self.TILE_HEIGHT + self.TILE_MARGIN

        # Center the grid
        grid_width = self.TILES_PER_ROW * total_tile_width - self.TILE_MARGIN
        start_x = (self._screen_width - grid_width) // 2
        start_y = 120  # Leave room for title

        # Position tiles
        for i, tile in enumerate(self._tiles):
            row = i // self.TILES_PER_ROW
            col = i % self.TILES_PER_ROW

            x = start_x + col * total_tile_width
            y = start_y + row * total_tile_height

            tile.rect = pygame.Rect(x, y, self.TILE_WIDTH, self.TILE_HEIGHT)

        # Calculate max scroll
        if self._tiles:
            last_tile = self._tiles[-1]
            content_height = last_tile.rect.bottom + self.TILE_MARGIN
            self._max_scroll = max(0, content_height - self._screen_height + 80)

        # Back button at bottom
        self._back_rect = pygame.Rect(
            (self._screen_width - 200) // 2,
            self._screen_height - 60,
            200,
            40
        )

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Handle pygame events.

        Args:
            event: Pygame event

        Returns:
            Selected level path if a level was chosen, None otherwise
        """
        if event.type == pygame.MOUSEMOTION:
            self._handle_mouse_move(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                return self._handle_click(event.pos)
            elif event.button == 4:  # Scroll up
                self._scroll_offset = max(0, self._scroll_offset - 30)
            elif event.button == 5:  # Scroll down
                self._scroll_offset = min(self._max_scroll, self._scroll_offset + 30)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self._on_back:
                    self._on_back()
                return "__back__"

        return None

    def handle_hit(self, position: Vector2D) -> Optional[str]:
        """Handle a hit/click at the given position (for AMS integration).

        Args:
            position: Hit position in screen coordinates

        Returns:
            Selected level path if a level was chosen, None otherwise
        """
        return self._handle_click((int(position.x), int(position.y)))

    def _handle_mouse_move(self, pos: Tuple[int, int]) -> None:
        """Update hover states based on mouse position."""
        adjusted_pos = (pos[0], pos[1] + self._scroll_offset)

        for tile in self._tiles:
            tile.hover = tile.rect.collidepoint(adjusted_pos)

    def _handle_click(self, pos: Tuple[int, int]) -> Optional[str]:
        """Handle a click at the given position."""
        # Check back button (not affected by scroll)
        if self._back_rect and self._back_rect.collidepoint(pos):
            if self._on_back:
                self._on_back()
            return "__back__"

        # Check tiles (affected by scroll)
        adjusted_pos = (pos[0], pos[1] + self._scroll_offset)

        for tile in self._tiles:
            if tile.rect.collidepoint(adjusted_pos):
                self._selected_level = str(tile.path)
                if self._on_level_selected:
                    self._on_level_selected(self._selected_level)
                return self._selected_level

        return None

    def update(self, dt: float) -> None:
        """Update the chooser state.

        Args:
            dt: Delta time in seconds
        """
        # Could add animations here (tile pulse, transitions, etc.)
        pass

    def render(self, screen: pygame.Surface) -> None:
        """Render the level chooser.

        Args:
            screen: Pygame surface to render to
        """
        # Update screen dimensions
        self._screen_width, self._screen_height = screen.get_size()

        # Clear screen
        screen.fill(self.BG_COLOR)

        # Draw title
        self._render_title(screen)

        # Draw tiles (with scroll offset)
        self._render_tiles(screen)

        # Draw back button
        self._render_back_button(screen)

        # Draw scroll indicator if needed
        if self._max_scroll > 0:
            self._render_scroll_indicator(screen)

    def _render_title(self, screen: pygame.Surface) -> None:
        """Render the title header."""
        font_large = pygame.font.Font(None, 56)
        font_small = pygame.font.Font(None, 28)

        # Main title
        title = font_large.render("SELECT LEVEL", True, self.TEXT_COLOR)
        title_rect = title.get_rect(centerx=self._screen_width // 2, y=30)
        screen.blit(title, title_rect)

        # Subtitle
        subtitle = font_small.render(
            f"{len(self._tiles)} levels available",
            True,
            self.TEXT_DIM_COLOR
        )
        subtitle_rect = subtitle.get_rect(centerx=self._screen_width // 2, y=75)
        screen.blit(subtitle, subtitle_rect)

    def _render_tiles(self, screen: pygame.Surface) -> None:
        """Render all level tiles."""
        font_name = pygame.font.Font(None, 32)
        font_desc = pygame.font.Font(None, 22)
        font_meta = pygame.font.Font(None, 20)

        for tile in self._tiles:
            # Adjust position for scroll
            render_rect = tile.rect.copy()
            render_rect.y -= self._scroll_offset

            # Skip if off-screen
            if render_rect.bottom < 100 or render_rect.top > self._screen_height - 70:
                continue

            # Determine tile color
            if tile.selected:
                color = self.TILE_SELECTED_COLOR
            elif tile.hover:
                color = self.TILE_HOVER_COLOR
            else:
                color = self.TILE_COLOR

            # Draw tile background
            pygame.draw.rect(screen, color, render_rect, border_radius=8)

            # Draw border
            border_color = self.ACCENT_COLOR if tile.hover else (60, 65, 85)
            pygame.draw.rect(screen, border_color, render_rect, width=2, border_radius=8)

            # Draw difficulty indicator (stars or dots)
            self._render_difficulty(screen, render_rect, tile.difficulty)

            # Draw level name
            name_surface = font_name.render(tile.name, True, self.TEXT_COLOR)
            # Truncate if too long
            max_name_width = self.TILE_WIDTH - 80
            if name_surface.get_width() > max_name_width:
                # Truncate with ellipsis
                truncated = tile.name
                while font_name.size(truncated + "...")[0] > max_name_width and len(truncated) > 0:
                    truncated = truncated[:-1]
                name_surface = font_name.render(truncated + "...", True, self.TEXT_COLOR)
            screen.blit(name_surface, (render_rect.x + 15, render_rect.y + 15))

            # Draw description (truncated)
            if tile.description:
                desc_text = tile.description
                max_desc_width = self.TILE_WIDTH - 30
                if font_desc.size(desc_text)[0] > max_desc_width:
                    while font_desc.size(desc_text + "...")[0] > max_desc_width and len(desc_text) > 0:
                        desc_text = desc_text[:-1]
                    desc_text += "..."
                desc_surface = font_desc.render(desc_text, True, self.TEXT_DIM_COLOR)
                screen.blit(desc_surface, (render_rect.x + 15, render_rect.y + 50))

            # Draw author
            author_surface = font_meta.render(f"by {tile.author}", True, self.TEXT_DIM_COLOR)
            screen.blit(author_surface, (render_rect.x + 15, render_rect.y + self.TILE_HEIGHT - 30))

    def _render_difficulty(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        difficulty: int
    ) -> None:
        """Render difficulty indicator (colored dots)."""
        difficulty = max(1, min(5, difficulty))  # Clamp to 1-5
        color = self.DIFFICULTY_COLORS[difficulty - 1]

        # Draw dots in top-right corner
        dot_radius = 5
        dot_spacing = 14
        start_x = rect.right - 15 - (difficulty - 1) * dot_spacing
        y = rect.y + 20

        for i in range(difficulty):
            x = start_x + i * dot_spacing
            pygame.draw.circle(screen, color, (x, y), dot_radius)

    def _render_back_button(self, screen: pygame.Surface) -> None:
        """Render the back/default button."""
        if not self._back_rect:
            return

        font = pygame.font.Font(None, 28)

        # Check hover
        mouse_pos = pygame.mouse.get_pos()
        hover = self._back_rect.collidepoint(mouse_pos)

        # Draw button
        color = self.TILE_HOVER_COLOR if hover else self.TILE_COLOR
        pygame.draw.rect(screen, color, self._back_rect, border_radius=6)

        border_color = self.ACCENT_COLOR if hover else (60, 65, 85)
        pygame.draw.rect(screen, border_color, self._back_rect, width=2, border_radius=6)

        # Draw text
        text = font.render("← Default Mode", True, self.TEXT_COLOR)
        text_rect = text.get_rect(center=self._back_rect.center)
        screen.blit(text, text_rect)

    def _render_scroll_indicator(self, screen: pygame.Surface) -> None:
        """Render scroll position indicator."""
        if self._max_scroll <= 0:
            return

        # Draw scrollbar track
        track_height = self._screen_height - 200
        track_x = self._screen_width - 20
        track_y = 120

        pygame.draw.rect(
            screen,
            (40, 45, 60),
            (track_x, track_y, 8, track_height),
            border_radius=4
        )

        # Draw scrollbar thumb
        visible_ratio = (self._screen_height - 200) / (self._max_scroll + self._screen_height - 200)
        thumb_height = max(30, int(track_height * visible_ratio))
        scroll_ratio = self._scroll_offset / self._max_scroll if self._max_scroll > 0 else 0
        thumb_y = track_y + int((track_height - thumb_height) * scroll_ratio)

        pygame.draw.rect(
            screen,
            self.ACCENT_COLOR,
            (track_x, thumb_y, 8, thumb_height),
            border_radius=4
        )

    @property
    def selected_level(self) -> Optional[str]:
        """Get the currently selected level path."""
        return self._selected_level


def run_level_chooser() -> Optional[str]:
    """Run the level chooser as a standalone screen.

    Returns:
        Selected level path, "__back__" for default mode, or None if cancelled
    """
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Containment - Level Select")
    clock = pygame.time.Clock()

    selected = None

    def on_selected(path: str):
        nonlocal selected
        selected = path

    def on_back():
        nonlocal selected
        selected = "__back__"

    chooser = LevelChooser(
        screen_width=1280,
        screen_height=720,
        on_level_selected=on_selected,
        on_back=on_back,
    )

    running = True
    while running and selected is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                result = chooser.handle_event(event)
                if result:
                    selected = result

        chooser.update(1/60)
        chooser.render(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return selected


if __name__ == "__main__":
    # Test the level chooser standalone
    result = run_level_chooser()
    if result:
        print(f"Selected: {result}")
    else:
        print("Cancelled")
