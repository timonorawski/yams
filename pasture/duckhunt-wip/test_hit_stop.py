"""Quick test to verify hit targets stop at their position."""

import pygame
from game.modes.classic import ClassicMode
from input.input_event import InputEvent
from models import Vector2D, EventType
import time

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Test: Hit Targets Stop")
clock = pygame.time.Clock()

# Create classic mode
mode = ClassicMode()

# Spawn a target manually
mode._spawn_target()

print("Test: Hit Targets Stop at Their Position")
print("=" * 50)
print("A target will spawn and move across the screen.")
print("Click on it to hit it.")
print("The target should STOP at the hit position and remain")
print("visible for 0.5 seconds before disappearing.")
print()
print("Press any key to start...")

# Wait for key press
waiting = True
while waiting:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            waiting = False
            pygame.quit()
            exit()
        if event.type == pygame.KEYDOWN:
            waiting = False

running = True
frames = 0
max_frames = 300  # 5 seconds at 60 FPS

while running and frames < max_frames:
    dt = clock.tick(60) / 1000.0  # 60 FPS, convert to seconds
    frames += 1

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Create input event
            input_event = InputEvent(
                position=Vector2D(x=float(event.pos[0]), y=float(event.pos[1])),
                timestamp=time.time(),
                event_type=EventType.HIT
            )
            mode.handle_input([input_event])
            print(f"Click at ({event.pos[0]}, {event.pos[1]})")

    # Update
    mode.update(dt)

    # Render
    screen.fill((135, 206, 235))  # Sky blue
    mode.render(screen)

    # Draw instructions
    font = pygame.font.Font(None, 24)
    text = "Click on the moving target. It should STOP when hit."
    text_surface = font.render(text, True, (255, 255, 255))
    screen.blit(text_surface, (10, 10))

    pygame.display.flip()

print("\nTest complete!")
pygame.quit()
