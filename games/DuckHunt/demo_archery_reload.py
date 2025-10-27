#!/usr/bin/env python3
"""
Demo: Archery Practice with Projectile Limiting and Reload Interstitials

This demo showcases the integration between the game and AMS for handling
limited projectiles (arrows) and reload interstitials.

Flow:
1. Game starts with 6 arrows
2. Player shoots arrows (projectiles decrement)
3. When depleted, game transitions to WAITING_FOR_RELOAD
4. AMS displays interstitial screen ("Collect your arrows")
5. After delay (simulating collection time), AMS calls reload()
6. Game resumes with fresh arrows

Controls:
- Click to shoot (uses one arrow)
- Press R to manually trigger reload (when in WAITING_FOR_RELOAD)
- Press ESC to exit
"""

import pygame
import time
from game.mode_loader import GameModeLoader
from game.modes.dynamic import DynamicGameMode
from input.input_event import InputEvent
from models import Vector2D, EventType, GameState

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN)
pygame.display.set_caption("Archery Practice - Projectile Limiting Demo")
clock = pygame.time.Clock()

# Create fonts
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

print("=" * 70)
print("ARCHERY PRACTICE - PROJECTILE LIMITING DEMO")
print("=" * 70)
print()
print("Loading classic_archery game mode...")

# Load archery configuration
loader = GameModeLoader()
config = loader.load_mode("classic_archery")

print(f"✓ Loaded: {config.name}")
print(f"  - Arrows per round: {config.rules.projectiles_per_round}")
print()

# Create game mode
mode = DynamicGameMode(config, audio_enabled=False)
print("✓ Game mode initialized")
print()
print("INSTRUCTIONS:")
print("- Click to shoot arrows at targets")
print("- You have 6 arrows per round")
print("- When arrows are depleted, you'll see a reload screen")
print("- Press R to manually reload (simulates arrow collection)")
print("- Press ESC to exit")
print()
print("Starting in 3 seconds...")
pygame.time.wait(1000)
print("2...")
pygame.time.wait(1000)
print("1...")
pygame.time.wait(1000)
print("GO!")
print()

# Game state
running = True
show_help = True
help_timer = 5.0

# Interstitial state
reload_message_timer = 0.0
AUTO_RELOAD_DELAY = 5.0  # AMS would wait 5 seconds before auto-reload

# Main game loop
while running:
    dt = clock.tick(60) / 1000.0

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
            elif event.key == pygame.K_h:
                show_help = not show_help
                help_timer = 5.0
            elif event.key == pygame.K_r:
                # Manual reload (simulates AMS calling reload after interstitial)
                if mode.state == GameState.WAITING_FOR_RELOAD:
                    print("Manual reload triggered (simulating AMS reload call)")
                    mode.reload()
                    reload_message_timer = 0.0
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if mode.state == GameState.PLAYING:
                # Create input event for shooting
                input_event = InputEvent(
                    position=Vector2D(x=float(event.pos[0]), y=float(event.pos[1])),
                    timestamp=time.time(),
                    event_type=EventType.HIT
                )
                mode.handle_input([input_event])

                # Log projectile usage
                remaining = mode.get_projectiles_remaining()
                print(f"Arrow fired! {remaining} arrows remaining")

                # Check if just transitioned to WAITING_FOR_RELOAD
                if mode.state == GameState.WAITING_FOR_RELOAD:
                    print("Out of arrows! Waiting for reload...")
                    reload_message_timer = 0.0

    # Update game logic
    if mode.state == GameState.PLAYING:
        mode.update(dt)

    # Handle auto-reload (simulates AMS behavior)
    if mode.state == GameState.WAITING_FOR_RELOAD:
        reload_message_timer += dt
        if reload_message_timer >= AUTO_RELOAD_DELAY:
            print(f"Auto-reload after {AUTO_RELOAD_DELAY} seconds (simulating AMS)")
            mode.reload()
            reload_message_timer = 0.0

    # Render
    screen.fill((135, 206, 235))  # Sky blue

    # Render game (targets, effects, score)
    mode.render(screen)

    # Draw crosshair
    mouse_pos = pygame.mouse.get_pos()
    crosshair_size = 20
    crosshair_color = (255, 0, 0)
    pygame.draw.line(screen, crosshair_color,
                     (mouse_pos[0] - crosshair_size, mouse_pos[1]),
                     (mouse_pos[0] + crosshair_size, mouse_pos[1]), 2)
    pygame.draw.line(screen, crosshair_color,
                     (mouse_pos[0], mouse_pos[1] - crosshair_size),
                     (mouse_pos[0], mouse_pos[1] + crosshair_size), 2)
    pygame.draw.circle(screen, crosshair_color, mouse_pos, 3)

    # Draw HUD
    hud_y = screen.get_height() - 100
    hud_surface = pygame.Surface((screen.get_width(), 100))
    hud_surface.set_alpha(128)
    hud_surface.fill((0, 0, 0))
    screen.blit(hud_surface, (0, hud_y))

    # Level info
    level_text = f"LEVEL {mode.current_level}"
    level_surface = large_font.render(level_text, True, (255, 255, 0))
    screen.blit(level_surface, (20, hud_y + 10))

    # Projectile count (prominent display)
    projectiles = mode.get_projectiles_remaining()
    if projectiles is not None:
        arrows_text = f"ARROWS: {projectiles}/6"
        arrows_color = (0, 255, 0) if projectiles > 2 else (255, 165, 0) if projectiles > 0 else (255, 0, 0)
        arrows_surface = large_font.render(arrows_text, True, arrows_color)
        arrows_rect = arrows_surface.get_rect(center=(screen.get_width() // 2, hud_y + 35))
        screen.blit(arrows_surface, arrows_rect)

    # Stats
    stats = mode._score_tracker.get_stats()
    stats_text = f"Hits: {stats.hits}  Misses: {stats.misses}  Accuracy: {stats.accuracy:.1%}"
    stats_surface = medium_font.render(stats_text, True, (255, 255, 255))
    screen.blit(stats_surface, (screen.get_width() - 600, hud_y + 60))

    # Interstitial overlay (simulates AMS interstitial screen)
    if mode.state == GameState.WAITING_FOR_RELOAD:
        # Semi-transparent overlay
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # "Collect your arrows" message
        messages = [
            "OUT OF ARROWS!",
            "",
            "Please collect your arrows from the target.",
            "",
            f"Auto-reload in {max(0, AUTO_RELOAD_DELAY - reload_message_timer):.1f} seconds",
            "or press R to reload now"
        ]

        y_offset = screen.get_height() // 2 - 150
        for msg in messages:
            if msg:
                if msg == messages[0]:
                    text_surface = title_font.render(msg, True, (255, 0, 0))
                elif "Auto-reload" in msg or "press R" in msg:
                    text_surface = small_font.render(msg, True, (200, 200, 200))
                else:
                    text_surface = large_font.render(msg, True, (255, 255, 255))
                text_rect = text_surface.get_rect(center=(screen.get_width() // 2, y_offset))
                screen.blit(text_surface, text_rect)
            y_offset += 60

        # Progress bar for auto-reload
        bar_width = 400
        bar_height = 20
        bar_x = (screen.get_width() - bar_width) // 2
        bar_y = screen.get_height() // 2 + 150

        # Background bar
        pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height))

        # Progress bar
        progress = min(1.0, reload_message_timer / AUTO_RELOAD_DELAY)
        progress_width = int(bar_width * progress)
        pygame.draw.rect(screen, (0, 255, 0), (bar_x, bar_y, progress_width, bar_height))

        # Border
        pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 2)

    # Help text
    if show_help:
        help_texts = [
            "ARCHERY PRACTICE - PROJECTILE LIMITING",
            "",
            "• Click to shoot arrows at targets",
            "• You have 6 arrows per round",
            "• When depleted, collect arrows to reload",
            "• System auto-reloads after 5 seconds",
            "",
            "Press H to toggle help | ESC to exit"
        ]

        help_height = len(help_texts) * 35 + 40
        help_surface = pygame.Surface((700, help_height))
        help_surface.set_alpha(200)
        help_surface.fill((0, 0, 0))
        help_x = (screen.get_width() - 700) // 2
        help_y = 50
        screen.blit(help_surface, (help_x, help_y))

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

    # FPS counter
    fps_text = f"FPS: {int(clock.get_fps())}"
    fps_surface = small_font.render(fps_text, True, (255, 255, 255))
    screen.blit(fps_surface, (screen.get_width() - 100, 10))

    pygame.display.flip()

# Game over
print()
print("=" * 70)
print("DEMO COMPLETE")
print("=" * 70)
stats = mode._score_tracker.get_stats()
print(f"Final Stats:")
print(f"  - Hits: {stats.hits}")
print(f"  - Misses: {stats.misses}")
print(f"  - Accuracy: {stats.accuracy:.1%}")
print()
print("This demo showed how the game integrates with AMS for projectile limiting:")
print("  1. Game tracks projectile usage transparently")
print("  2. Transitions to WAITING_FOR_RELOAD when depleted")
print("  3. AMS displays interstitial screen with instructions")
print("  4. AMS calls reload() when ready (after timer or user action)")
print("  5. Game seamlessly resumes with fresh projectiles")

pygame.quit()
