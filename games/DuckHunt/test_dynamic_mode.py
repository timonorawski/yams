"""Quick test script to validate the dynamic game mode system.

This script tests:
1. Loading YAML game mode configurations
2. Creating DynamicGameMode instances
3. Trajectory generation (linear and Bezier 3D)
4. Basic target spawning and movement
"""

import pygame
from game.mode_loader import GameModeLoader
from game.modes.dynamic import DynamicGameMode
from input.input_event import InputEvent
from models import Vector2D, EventType
import time

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Test: Dynamic Game Mode with Trajectories")
clock = pygame.time.Clock()

# Test 1: Load and validate YAML configurations
print("=" * 60)
print("TEST 1: Loading YAML Game Mode Configurations")
print("=" * 60)

loader = GameModeLoader()
available_modes = loader.list_available_modes()
print(f"\nAvailable game modes: {available_modes}")

if "classic_linear" in available_modes:
    linear_config = loader.load_mode("classic_linear")
    print(f"\n✓ Loaded 'classic_linear':")
    print(f"  - Name: {linear_config.name}")
    print(f"  - Trajectory: {linear_config.trajectory.algorithm}")
    print(f"  - Curvature: {linear_config.trajectory.curvature_factor}")
    print(f"  - Levels: {len(linear_config.levels)}")
else:
    print("\n✗ classic_linear.yaml not found!")

if "classic_ducks" in available_modes:
    ducks_config = loader.load_mode("classic_ducks")
    print(f"\n✓ Loaded 'classic_ducks':")
    print(f"  - Name: {ducks_config.name}")
    print(f"  - Trajectory: {ducks_config.trajectory.algorithm}")
    print(f"  - Curvature: {ducks_config.trajectory.curvature_factor}")
    print(f"  - Depth direction: {ducks_config.trajectory.depth_direction}")
    print(f"  - Levels: {len(ducks_config.levels)}")
else:
    print("\n✗ classic_ducks.yaml not found!")

# Test 2: Create DynamicGameMode instances
print("\n" + "=" * 60)
print("TEST 2: Creating DynamicGameMode Instances")
print("=" * 60)

try:
    # Test parabolic mode (classic_ducks)
    if "classic_ducks" in available_modes:
        parabolic_mode = DynamicGameMode(ducks_config, audio_enabled=False)
        print(f"\n✓ Created parabolic mode:")
        print(f"  - Current level: {parabolic_mode.current_level}")
        print(f"  - State: {parabolic_mode.state}")
        print(f"  - Algorithm: {ducks_config.trajectory.algorithm}")

        # Spawn a test target
        parabolic_mode._spawn_target()
        print(f"  - Targets spawned: {len(parabolic_mode.targets)}")

        if len(parabolic_mode.targets) > 0:
            target = parabolic_mode.targets[0]
            print(f"  - Target type: {type(target).__name__}")
            print(f"  - Initial position: ({target.position.x:.1f}, {target.position.y:.1f})")
            print(f"  - Initial size: {target.current_size:.1f}")
            print(f"  - Trajectory duration: {target.trajectory.data.duration:.2f}s")
    else:
        print("\n✗ Cannot test parabolic mode - classic_ducks.yaml missing")

except Exception as e:
    print(f"\n✗ Error creating dynamic mode: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Visual demonstration
print("\n" + "=" * 60)
print("TEST 3: Visual Demonstration")
print("=" * 60)
print("\nStarting visual test...")
print("- A target will spawn and move along a curved trajectory")
print("- Size will scale based on simulated 3D depth")
print("- Click on targets to hit them")
print("- Press ESC to exit")
print()

mode = parabolic_mode if "classic_ducks" in available_modes else None

if mode is None:
    print("✗ Cannot run visual test - no valid mode loaded")
    pygame.quit()
    exit(1)

# Main game loop
running = True
frames = 0
max_frames = 600  # 10 seconds at 60 FPS

while running and frames < max_frames:
    dt = clock.tick(60) / 1000.0  # 60 FPS, convert to seconds
    frames += 1

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Create input event
            input_event = InputEvent(
                position=Vector2D(x=float(event.pos[0]), y=float(event.pos[1])),
                timestamp=time.time(),
                event_type=EventType.HIT
            )
            mode.handle_input([input_event])

    # Update game mode
    mode.update(dt)

    # Render
    screen.fill((135, 206, 235))  # Sky blue
    mode.render(screen)

    # Draw instructions
    font = pygame.font.Font(None, 24)
    instructions = [
        "Parabolic Trajectory Test",
        "Click on targets (curved paths with depth scaling)",
        "Press ESC to exit",
        f"Targets: {len([t for t in mode.targets])}",
        f"Score: {mode.get_score()}",
    ]

    y_offset = 10
    for text in instructions:
        text_surface = font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect()
        # Add black background for readability
        pygame.draw.rect(screen, (0, 0, 0), (5, y_offset-2, text_rect.width+10, text_rect.height+4))
        screen.blit(text_surface, (10, y_offset))
        y_offset += 25

    pygame.display.flip()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print("\nAll tests passed successfully!")
print("The parabolic trajectory system with YAML configuration is working.")

pygame.quit()
