"""Generic Level Chooser UI for AMS games.

A tile-based level selection screen that can be used by any game
with level support. Can be navigated with mouse clicks or projectile
hits in AMS mode.

Usage:
    from ams.games.level_chooser import LevelChooserUI

    # In your game's render method, when show_level_chooser is True:
    if self._level_chooser_ui is None:
        self._level_chooser_ui = LevelChooserUI(
            level_loader=self._level_loader,
            screen_width=screen.get_width(),
            screen_height=screen.get_height(),
            game_name=self.NAME,
            on_level_selected=self._on_level_selected,
            on_back=self._on_level_chooser_back,
        )
    self._level_chooser_ui.render(screen)
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from ams.games.levels import LevelLoader, LevelInfo


@dataclass
class LevelTile:
    """A selectable level tile."""
    slug: str
    name: str
    description: str
    difficulty: int
    author: str
    is_group: bool
    level_count: int  # For groups
    rect: pygame.Rect
    hover: bool = False


class LevelChooserUI:
    """Generic tile-based level selection UI.

    Features:
    - Grid of level tiles with name, description, difficulty
    - Mouse/click selection
    - Visual feedback on hover/selection
    - Difficulty indicators (colored dots)
    - Separate sections for levels and level groups
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
    TILE_GROUP_COLOR = (45, 50, 70)  # Slightly different for groups
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
    GROUP_ACCENT_COLOR = (180, 140, 255)  # Purple for groups

    def __init__(
        self,
        level_loader: 'LevelLoader',
        screen_width: int = 1280,
        screen_height: int = 720,
        game_name: str = "Game",
        on_level_selected: Optional[Callable[[str], None]] = None,
        on_group_selected: Optional[Callable[[str], None]] = None,
        on_back: Optional[Callable[[], None]] = None,
    ):
        """Initialize the level chooser.

        Args:
            level_loader: LevelLoader instance for this game
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            game_name: Name to display in header
            on_level_selected: Callback when a level is selected (receives slug)
            on_group_selected: Callback when a group is selected (receives slug)
            on_back: Callback when back/default is selected
        """
        self._loader = level_loader
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._game_name = game_name
        self._on_level_selected = on_level_selected
        self._on_group_selected = on_group_selected
        self._on_back = on_back

        # State
        self._level_tiles: List[LevelTile] = []
        self._group_tiles: List[LevelTile] = []
        self._back_rect: Optional[pygame.Rect] = None
        self._scroll_offset = 0
        self._max_scroll = 0

        # Fonts (initialized lazily)
        self._font_large: Optional[pygame.font.Font] = None
        self._font_medium: Optional[pygame.font.Font] = None
        self._font_small: Optional[pygame.font.Font] = None
        self._font_tiny: Optional[pygame.font.Font] = None

        # Load levels and layout
        self._load_items()
        self._layout_tiles()

    def _get_fonts(self) -> Tuple[pygame.font.Font, ...]:
        """Get or create fonts."""
        if self._font_large is None:
            self._font_large = pygame.font.Font(None, 56)
            self._font_medium = pygame.font.Font(None, 32)
            self._font_small = pygame.font.Font(None, 22)
            self._font_tiny = pygame.font.Font(None, 20)
        return self._font_large, self._font_medium, self._font_small, self._font_tiny

    def _load_items(self) -> None:
        """Load available levels and groups."""
        self._level_tiles = []
        self._group_tiles = []

        # Load individual levels
        for slug in self._loader.list_levels():
            info = self._loader.get_level_info(slug)
            if info:
                tile = LevelTile(
                    slug=slug,
                    name=info.name,
                    description=info.description,
                    difficulty=info.difficulty,
                    author=info.author,
                    is_group=False,
                    level_count=0,
                    rect=pygame.Rect(0, 0, self.TILE_WIDTH, self.TILE_HEIGHT),
                )
                self._level_tiles.append(tile)

        # Load level groups
        for slug in self._loader.list_groups():
            info = self._loader.get_level_info(slug)
            if info:
                tile = LevelTile(
                    slug=slug,
                    name=info.name,
                    description=info.description,
                    difficulty=info.difficulty,
                    author=info.author,
                    is_group=True,
                    level_count=len(info.levels),
                    rect=pygame.Rect(0, 0, self.TILE_WIDTH, self.TILE_HEIGHT),
                )
                self._group_tiles.append(tile)

        # Sort by difficulty, then name
        self._level_tiles.sort(key=lambda t: (t.difficulty, t.name))
        self._group_tiles.sort(key=lambda t: t.name)

    def _layout_tiles(self) -> None:
        """Calculate tile positions based on screen size."""
        total_tile_width = self.TILE_WIDTH + self.TILE_MARGIN
        total_tile_height = self.TILE_HEIGHT + self.TILE_MARGIN

        # Center the grid
        grid_width = self.TILES_PER_ROW * total_tile_width - self.TILE_MARGIN
        start_x = (self._screen_width - grid_width) // 2
        y = 120  # Leave room for title

        # Layout level groups first (if any)
        if self._group_tiles:
            for i, tile in enumerate(self._group_tiles):
                row = i // self.TILES_PER_ROW
                col = i % self.TILES_PER_ROW
                x = start_x + col * total_tile_width
                tile.rect = pygame.Rect(x, y + row * total_tile_height, self.TILE_WIDTH, self.TILE_HEIGHT)

            # Add spacing after groups
            rows_for_groups = (len(self._group_tiles) + self.TILES_PER_ROW - 1) // self.TILES_PER_ROW
            y += rows_for_groups * total_tile_height + 40  # Extra spacing

        # Layout individual levels
        for i, tile in enumerate(self._level_tiles):
            row = i // self.TILES_PER_ROW
            col = i % self.TILES_PER_ROW
            x = start_x + col * total_tile_width
            tile.rect = pygame.Rect(x, y + row * total_tile_height, self.TILE_WIDTH, self.TILE_HEIGHT)

        # Calculate max scroll
        all_tiles = self._group_tiles + self._level_tiles
        if all_tiles:
            last_tile = max(all_tiles, key=lambda t: t.rect.bottom)
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
            Selected level/group slug if chosen, "__back__" if back selected, None otherwise
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

    def handle_hit(self, x: float, y: float) -> Optional[str]:
        """Handle a hit/click at the given position (for AMS integration).

        Args:
            x: X position in screen coordinates
            y: Y position in screen coordinates

        Returns:
            Selected level/group slug if chosen, None otherwise
        """
        return self._handle_click((int(x), int(y)))

    def _handle_mouse_move(self, pos: Tuple[int, int]) -> None:
        """Update hover states based on mouse position."""
        adjusted_pos = (pos[0], pos[1] + self._scroll_offset)

        for tile in self._group_tiles + self._level_tiles:
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

        # Check groups first
        for tile in self._group_tiles:
            if tile.rect.collidepoint(adjusted_pos):
                if self._on_group_selected:
                    self._on_group_selected(tile.slug)
                return tile.slug

        # Then individual levels
        for tile in self._level_tiles:
            if tile.rect.collidepoint(adjusted_pos):
                if self._on_level_selected:
                    self._on_level_selected(tile.slug)
                return tile.slug

        return None

    def update(self, dt: float) -> None:
        """Update the chooser state.

        Args:
            dt: Delta time in seconds
        """
        # Could add animations here
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

        # Draw group tiles (if any)
        if self._group_tiles:
            self._render_section_header(screen, "Campaigns & Groups", 95)
            self._render_tiles(screen, self._group_tiles, is_group=True)

        # Draw level tiles
        if self._level_tiles:
            if self._group_tiles:
                # Find where groups end
                last_group = max(self._group_tiles, key=lambda t: t.rect.bottom)
                header_y = last_group.rect.bottom - self._scroll_offset + 15
                self._render_section_header(screen, "Individual Levels", header_y)
            self._render_tiles(screen, self._level_tiles, is_group=False)

        # Draw back button
        self._render_back_button(screen)

        # Draw scroll indicator if needed
        if self._max_scroll > 0:
            self._render_scroll_indicator(screen)

    def _render_title(self, screen: pygame.Surface) -> None:
        """Render the title header."""
        font_large, font_medium, font_small, _ = self._get_fonts()

        # Main title
        title = font_large.render(f"{self._game_name} - Select Level", True, self.TEXT_COLOR)
        title_rect = title.get_rect(centerx=self._screen_width // 2, y=25)
        screen.blit(title, title_rect)

        # Subtitle
        total = len(self._level_tiles) + len(self._group_tiles)
        subtitle = font_small.render(
            f"{len(self._level_tiles)} levels, {len(self._group_tiles)} groups",
            True,
            self.TEXT_DIM_COLOR
        )
        subtitle_rect = subtitle.get_rect(centerx=self._screen_width // 2, y=70)
        screen.blit(subtitle, subtitle_rect)

    def _render_section_header(self, screen: pygame.Surface, text: str, y: int) -> None:
        """Render a section header."""
        _, font_medium, _, _ = self._get_fonts()
        header = font_medium.render(text, True, self.TEXT_DIM_COLOR)
        screen.blit(header, (40, y))

    def _render_tiles(self, screen: pygame.Surface, tiles: List[LevelTile], is_group: bool) -> None:
        """Render tiles."""
        _, font_medium, font_small, font_tiny = self._get_fonts()

        for tile in tiles:
            # Adjust position for scroll
            render_rect = tile.rect.copy()
            render_rect.y -= self._scroll_offset

            # Skip if off-screen
            if render_rect.bottom < 100 or render_rect.top > self._screen_height - 70:
                continue

            # Determine tile color
            if tile.hover:
                color = self.TILE_HOVER_COLOR
            elif is_group:
                color = self.TILE_GROUP_COLOR
            else:
                color = self.TILE_COLOR

            # Draw tile background
            pygame.draw.rect(screen, color, render_rect, border_radius=8)

            # Draw border
            accent = self.GROUP_ACCENT_COLOR if is_group else self.ACCENT_COLOR
            border_color = accent if tile.hover else (60, 65, 85)
            pygame.draw.rect(screen, border_color, render_rect, width=2, border_radius=8)

            # Draw difficulty indicator (for non-groups)
            if not is_group:
                self._render_difficulty(screen, render_rect, tile.difficulty)
            else:
                # Draw level count badge for groups
                self._render_level_count(screen, render_rect, tile.level_count)

            # Draw name
            name_surface = font_medium.render(tile.name, True, self.TEXT_COLOR)
            max_name_width = self.TILE_WIDTH - 80
            if name_surface.get_width() > max_name_width:
                truncated = tile.name
                while font_medium.size(truncated + "...")[0] > max_name_width and len(truncated) > 0:
                    truncated = truncated[:-1]
                name_surface = font_medium.render(truncated + "...", True, self.TEXT_COLOR)
            screen.blit(name_surface, (render_rect.x + 15, render_rect.y + 15))

            # Draw description
            if tile.description:
                desc_text = tile.description
                max_desc_width = self.TILE_WIDTH - 30
                if font_small.size(desc_text)[0] > max_desc_width:
                    while font_small.size(desc_text + "...")[0] > max_desc_width and len(desc_text) > 0:
                        desc_text = desc_text[:-1]
                    desc_text += "..."
                desc_surface = font_small.render(desc_text, True, self.TEXT_DIM_COLOR)
                screen.blit(desc_surface, (render_rect.x + 15, render_rect.y + 50))

            # Draw author
            author_surface = font_tiny.render(f"by {tile.author}", True, self.TEXT_DIM_COLOR)
            screen.blit(author_surface, (render_rect.x + 15, render_rect.y + self.TILE_HEIGHT - 30))

    def _render_difficulty(self, screen: pygame.Surface, rect: pygame.Rect, difficulty: int) -> None:
        """Render difficulty indicator (colored dots)."""
        difficulty = max(1, min(5, difficulty))
        color = self.DIFFICULTY_COLORS[difficulty - 1]

        dot_radius = 5
        dot_spacing = 14
        start_x = rect.right - 15 - (difficulty - 1) * dot_spacing
        y = rect.y + 20

        for i in range(difficulty):
            x = start_x + i * dot_spacing
            pygame.draw.circle(screen, color, (x, y), dot_radius)

    def _render_level_count(self, screen: pygame.Surface, rect: pygame.Rect, count: int) -> None:
        """Render level count badge for groups."""
        _, _, font_small, _ = self._get_fonts()

        badge_text = f"{count} lvls"
        text_surf = font_small.render(badge_text, True, self.GROUP_ACCENT_COLOR)
        text_rect = text_surf.get_rect(right=rect.right - 15, y=rect.y + 15)
        screen.blit(text_surf, text_rect)

    def _render_back_button(self, screen: pygame.Surface) -> None:
        """Render the back/default button."""
        if not self._back_rect:
            return

        _, font_medium, _, _ = self._get_fonts()

        mouse_pos = pygame.mouse.get_pos()
        hover = self._back_rect.collidepoint(mouse_pos)

        color = self.TILE_HOVER_COLOR if hover else self.TILE_COLOR
        pygame.draw.rect(screen, color, self._back_rect, border_radius=6)

        border_color = self.ACCENT_COLOR if hover else (60, 65, 85)
        pygame.draw.rect(screen, border_color, self._back_rect, width=2, border_radius=6)

        text = font_medium.render("Back", True, self.TEXT_COLOR)
        text_rect = text.get_rect(center=self._back_rect.center)
        screen.blit(text, text_rect)

    def _render_scroll_indicator(self, screen: pygame.Surface) -> None:
        """Render scroll position indicator."""
        if self._max_scroll <= 0:
            return

        track_height = self._screen_height - 200
        track_x = self._screen_width - 20
        track_y = 120

        pygame.draw.rect(
            screen,
            (40, 45, 60),
            (track_x, track_y, 8, track_height),
            border_radius=4
        )

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
