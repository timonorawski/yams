"""
Interactive Demo: Classic Duck Hunt with Parabolic Trajectories

This demo showcases the enhanced Duck Hunt mode with:
- Curved Bezier trajectories (parabolic arcs)
- 3D depth simulation (targets shrink as they fly away)
- 7 progressive difficulty levels
- Dynamic spawning from edges
- Score tracking and combo system

Controls:
- Click on moving targets to hit them
- Targets follow curved paths and scale with depth
- Reach 10 hits to advance to next level
- Press ESC to exit
"""

import pygame
import time
from game.mode_loader import GameModeLoader
from game.modes.dynamic import DynamicGameMode
from input.input_event import InputEvent
from models import Vector2D, EventType

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN)
pygame.display.set_caption("Classic Duck Hunt - Parabolic Trajectories Demo")
clock = pygame.time.Clock()

# Hide mouse cursor for authentic duck hunt feel
pygame.mouse.set_visible(True)  # Keep visible for now

print("=" * 70)
print("CLASSIC DUCK HUNT - PARABOLIC TRAJECTORY DEMO")
print("=" * 70)
print()
print("Loading classic_ducks game mode...")

# Load the classic ducks configuration
loader = GameModeLoader()
config = loader.load_mode("classic_ducks")

print(f"✓ Loaded: {config.name}")
print(f"  - Trajectory: {config.trajectory.algorithm} (curvature: {config.trajectory.curvature_factor})")
print(f"  - Depth: {config.trajectory.depth_direction} (3D simulation)")
print(f"  - Levels: {len(config.levels)}")
print()

# Create the game mode
mode = DynamicGameMode(config, audio_enabled=False)
print("✓ Game mode initialized")
print()
print("INSTRUCTIONS:")
print("- Ducks fly in curved parabolic arcs")
print("- They shrink as they fly away (3D depth simulation)")
print("- Click on ducks to shoot them")
print("- Score 10 hits to advance to next level")
print("- Miss too many and combo breaks")
print("- Press ESC to exit")
print()
print("Starting game in 3 seconds...")
pygame.time.wait(1000)
print("2...")
pygame.time.wait(1000)
print("1...")
pygame.time.wait(1000)
print("GO!")
print()

# Game state
running = True
paused = False
show_help = True
help_timer = 5.0  # Show help for 5 seconds

# Create custom font sizes
try:
    title_font = pygame.font.Font(None, 72)
    large_font = pygame.font.Font(None, 48)
    medium_font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)
except:
    title_font = pygame.font.SysFont("monospace", 72)
    large_font = pygame.font.SysFont("monospace", 48)
    medium_font = pygame.font.SysFont("monospace", 36)
    small_font = pygame.font.SysFont("monospace", 24)

# Main game loop
while running:
    dt = clock.tick(60) / 1000.0  # 60 FPS

    # Update help timer
    if show_help:
        help_timer -= dt
        if help_timer <= 0:
            show_help = False

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                paused = not paused
            elif event.key == pygame.K_h:
                show_help = not show_help
                help_timer = 5.0
        elif event.type == pygame.MOUSEBUTTONDOWN and not paused:
            # Create input event for hit detection
            input_event = InputEvent(
                position=Vector2D(x=float(event.pos[0]), y=float(event.pos[1])),
                timestamp=time.time(),
                event_type=EventType.HIT
            )
            mode.handle_input([input_event])

    # Update game logic
    if not paused:
        mode.update(dt)

    # Render
    # Sky blue background
    screen.fill((135, 206, 235))

    # Render game mode (targets, effects, score)
    mode.render(screen)

    # Draw crosshair at mouse position
    mouse_pos = pygame.mouse.get_pos()
    crosshair_size = 20
    crosshair_color = (255, 0, 0)
    # Horizontal line
    pygame.draw.line(screen, crosshair_color,
                     (mouse_pos[0] - crosshair_size, mouse_pos[1]),
                     (mouse_pos[0] + crosshair_size, mouse_pos[1]), 2)
    # Vertical line
    pygame.draw.line(screen, crosshair_color,
                     (mouse_pos[0], mouse_pos[1] - crosshair_size),
                     (mouse_pos[0], mouse_pos[1] + crosshair_size), 2)
    # Center dot
    pygame.draw.circle(screen, crosshair_color, mouse_pos, 3)

    # Draw HUD overlay
    hud_y = screen.get_height() - 100

    # Semi-transparent background for HUD
    hud_surface = pygame.Surface((screen.get_width(), 100))
    hud_surface.set_alpha(128)
    hud_surface.fill((0, 0, 0))
    screen.blit(hud_surface, (0, hud_y))

    # Level info
    level_text = f"LEVEL {mode.current_level}"
    level_surface = large_font.render(level_text, True, (255, 255, 0))
    screen.blit(level_surface, (20, hud_y + 10))

    # Active targets count
    active_targets = len([t for t in mode.targets])
    targets_text = f"Targets: {active_targets}"
    targets_surface = medium_font.render(targets_text, True, (255, 255, 255))
    screen.blit(targets_surface, (20, hud_y + 60))

    # Stats
    stats = mode._score_tracker.get_stats()
    stats_text = f"Hits: {stats.hits}  Misses: {stats.misses}  Combo: {stats.current_combo}x  Accuracy: {stats.accuracy:.1%}"
    stats_surface = medium_font.render(stats_text, True, (255, 255, 255))
    stats_rect = stats_surface.get_rect(center=(screen.get_width() // 2, hud_y + 35))
    screen.blit(stats_surface, stats_rect)

    # Help text
    if show_help:
        help_texts = [
            "CLASSIC DUCK HUNT - PARABOLIC TRAJECTORIES",
            "",
            "• Ducks fly in curved arcs (Bezier curves)",
            "• They shrink as they fly away (3D depth simulation)",
            "• Click to shoot",
            "• Hit 10 ducks to advance level",
            "",
            "Press H to toggle help | SPACE to pause | ESC to exit"
        ]

        # Semi-transparent help background
        help_height = len(help_texts) * 35 + 40
        help_surface = pygame.Surface((700, help_height))
        help_surface.set_alpha(200)
        help_surface.fill((0, 0, 0))
        help_x = (screen.get_width() - 700) // 2
        help_y = 50
        screen.blit(help_surface, (help_x, help_y))

        # Help text
        y_offset = help_y + 20
        for text in help_texts:
            if text:
                if text.startswith("•"):
                    text_surface = small_font.render(text, True, (255, 255, 255))
                elif text == help_texts[0]:
                    text_surface = medium_font.render(text, True, (255, 255, 0))
                else:
                    text_surface = small_font.render(text, True, (200, 200, 200))
                text_rect = text_surface.get_rect(center=(screen.get_width() // 2, y_offset))
                screen.blit(text_surface, text_rect)
            y_offset += 35

    # Pause indicator
    if paused:
        pause_text = "PAUSED"
        pause_surface = title_font.render(pause_text, True, (255, 255, 0))
        pause_rect = pause_surface.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))

        # Black background for pause text
        pause_bg = pygame.Surface((pause_rect.width + 40, pause_rect.height + 20))
        pause_bg.set_alpha(180)
        pause_bg.fill((0, 0, 0))
        screen.blit(pause_bg, (pause_rect.x - 20, pause_rect.y - 10))

        screen.blit(pause_surface, pause_rect)

        # Pause instructions
        pause_help = "Press SPACE to resume"
        pause_help_surface = medium_font.render(pause_help, True, (255, 255, 255))
        pause_help_rect = pause_help_surface.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 + 60))
        screen.blit(pause_help_surface, pause_help_rect)

    # FPS counter (top right)
    fps_text = f"FPS: {int(clock.get_fps())}"
    fps_surface = small_font.render(fps_text, True, (255, 255, 255))
    screen.blit(fps_surface, (screen.get_width() - 100, 10))

    pygame.display.flip()

# Game over
print()
print("=" * 70)
print("GAME OVER")
print("=" * 70)
stats = mode._score_tracker.get_stats()
print(f"Final Stats:")
print(f"  - Hits: {stats.hits}")
print(f"  - Misses: {stats.misses}")
print(f"  - Accuracy: {stats.accuracy:.1%}")
print(f"  - Final Combo: {stats.current_combo}x")
print(f"  - Final Level: {mode.current_level}")
print()
print("Thanks for playing!")

pygame.quit()
