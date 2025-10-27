"""
Simple Target Game - Example using AMS TemporalGameState

Demonstrates the complete AMS architecture:
1. Inherits from TemporalGameState for automatic history management
2. Uses PlaneHitEvents from AMS session
3. Queries past states for hit detection (handles latency)
4. Works with any detection backend (mouse, CV, AR, etc.)

This is a teaching example showing how to build games with AMS.
"""

import pygame
import time
import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from ams.temporal_state import TemporalGameState
from ams.events import PlaneHitEvent, HitResult


@dataclass
class Target:
    """A simple circular target."""
    x: float  # Normalized [0, 1]
    y: float  # Normalized [0, 1]
    radius: float  # Normalized size
    color: tuple  # RGB color
    points: int  # Points awarded for hitting
    alive: bool = True  # Whether target is active
    spawn_time: float = 0.0  # When target appeared
    target_id: int = 0  # Stable ID that persists across copies

    def contains(self, x: float, y: float) -> bool:
        """Check if point is inside target."""
        dx = x - self.x
        dy = y - self.y
        return (dx*dx + dy*dy) < (self.radius * self.radius)

    def copy(self):
        """Deep copy for state snapshots."""
        return Target(
            x=self.x,
            y=self.y,
            radius=self.radius,
            color=self.color,
            points=self.points,
            alive=self.alive,
            spawn_time=self.spawn_time,
            target_id=self.target_id  # Preserve ID across copies
        )


class SimpleTargetGame(TemporalGameState):
    """
    Simple target shooting game using AMS TemporalGameState.

    Demonstrates:
    - Automatic state history (handled by TemporalGameState)
    - Temporal hit queries (handle detection latency)
    - Using available color palette from calibration
    - Rendering with normalized coordinates
    """

    def __init__(
        self,
        display_width: int,
        display_height: int,
        available_colors: Optional[List[tuple]] = None
    ):
        """
        Initialize game.

        Args:
            display_width: Display width in pixels
            display_height: Display height in pixels
            available_colors: Colors from calibration (None = use defaults)
        """
        # Initialize temporal state management
        super().__init__(
            history_duration=5.0,  # 5 seconds of history
            fps=60,
            auto_snapshot=True
        )

        self.display_width = display_width
        self.display_height = display_height

        # Use calibrated colors if provided
        self.available_colors = available_colors or [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
        ]

        # Game state
        self.targets: List[Target] = []
        self.score = 0
        self.hits = 0
        self.misses = 0
        self._next_target_id = 0  # Counter for stable target IDs

        # Spawn initial targets
        self._spawn_targets(3)

    def update(self, dt: float):
        """
        Update game logic.

        Called every frame.

        Args:
            dt: Delta time in seconds
        """
        # Update target animations (example: pulse effect)
        current_time = time.time()
        for target in self.targets:
            if target.alive:
                # Pulse effect based on age
                age = current_time - target.spawn_time
                pulse = 1.0 + 0.1 * math.sin(age * 3)
                # Could animate target.radius here

        # Capture state snapshot (automatic via TemporalGameState)
        super().update(dt)

    def handle_hit_event(self, event: PlaneHitEvent) -> HitResult:
        """
        Handle a hit event from AMS.

        This demonstrates the key temporal query:
        - Event arrives with timestamp
        - We query our state history at that timestamp
        - Determine if it was a hit THEN (not now)

        Args:
            event: PlaneHitEvent from detection backend

        Returns:
            HitResult indicating whether this was a hit
        """
        # Query game state at the event's timestamp, adjusted for detection latency
        result = self.was_target_hit(event.x, event.y, event.timestamp, latency_ms=event.latency_ms)

        # Update game state based on result
        if result.hit:
            self.hits += 1
            self.score += result.points

            # Mark target as hit (find it in current state by stable ID)
            if result.target_id:
                target_id = int(result.target_id)
                for target in self.targets:
                    if target.target_id == target_id:
                        target.alive = False
                        break

            # Spawn new target to replace it
            self._spawn_targets(1)

            # Capture snapshot immediately after state change
            self.capture_snapshot()

        else:
            self.misses += 1

        return result

    def get_current_state_snapshot(self) -> Dict[str, Any]:
        """
        Return deep copy of current game state.

        Required by TemporalGameState.
        Called automatically each frame to build state history.

        Returns:
            Dictionary with all state needed for hit detection
        """
        return {
            'targets': [t.copy() for t in self.targets],
            'score': self.score,
            'frame': self.frame_counter
        }

    def check_hit_in_snapshot(
        self,
        snapshot: Dict[str, Any],
        x: float,
        y: float
    ) -> HitResult:
        """
        Check if coordinates hit a target in a specific state snapshot.

        Required by TemporalGameState.
        Called when game queries historical state for hit detection.

        Args:
            snapshot: State snapshot from get_current_state_snapshot()
            x: Normalized x coordinate [0, 1]
            y: Normalized y coordinate [0, 1]

        Returns:
            HitResult with hit status and details
        """
        # Convert normalized coords to pixel coords for accurate circular hit detection
        # (normalized space has aspect ratio distortion)
        click_px_x = x * self.display_width
        click_px_y = y * self.display_height

        # Check each target in the snapshot
        for target in snapshot['targets']:
            if target.alive:
                # Convert target position to pixels
                target_px_x = target.x * self.display_width
                target_px_y = target.y * self.display_height

                # Target radius in pixels (same as rendering)
                radius_px = target.radius * min(self.display_width, self.display_height)

                # Distance check in pixel space (true circular distance)
                dx = click_px_x - target_px_x
                dy = click_px_y - target_px_y
                distance_px = math.sqrt(dx*dx + dy*dy)

                if distance_px < radius_px:
                    # Hit!
                    return HitResult(
                        hit=True,
                        target_id=str(target.target_id),  # Use stable ID
                        distance=distance_px / min(self.display_width, self.display_height),
                        points=target.points,
                        message=f"Hit! +{target.points} points",
                        metadata={
                            'target_position': (target.x, target.y),
                            'target_color': target.color
                        }
                    )

        # Miss
        return HitResult(
            hit=False,
            message="Miss!"
        )

    def render(self, screen: pygame.Surface):
        """
        Render game to screen.

        Args:
            screen: Pygame surface to render to
        """
        # Clear screen
        screen.fill((0, 0, 0))

        # Draw targets
        for target in self.targets:
            if target.alive:
                # Convert normalized coords to screen coords
                screen_x = int(target.x * self.display_width)
                screen_y = int(target.y * self.display_height)
                screen_radius = int(target.radius * min(self.display_width, self.display_height))

                # Draw target
                pygame.draw.circle(
                    screen,
                    target.color,
                    (screen_x, screen_y),
                    screen_radius
                )

                # Draw center dot
                pygame.draw.circle(
                    screen,
                    (255, 255, 255),
                    (screen_x, screen_y),
                    3
                )

        # Draw HUD
        self._draw_hud(screen)

    def _draw_hud(self, screen: pygame.Surface):
        """Draw score and stats."""
        font = pygame.font.Font(None, 36)

        # Score
        score_text = font.render(f"Score: {self.score}", True, (255, 255, 255))
        screen.blit(score_text, (10, 10))

        # Hit/Miss stats
        stats_text = font.render(
            f"Hits: {self.hits}  Misses: {self.misses}",
            True,
            (255, 255, 255)
        )
        screen.blit(stats_text, (10, 50))

        # Accuracy
        total_shots = self.hits + self.misses
        if total_shots > 0:
            accuracy = (self.hits / total_shots) * 100
            acc_text = font.render(
                f"Accuracy: {accuracy:.1f}%",
                True,
                (255, 255, 255)
            )
            screen.blit(acc_text, (10, 90))

    def _spawn_targets(self, count: int):
        """Spawn new targets at random positions."""
        import random

        for _ in range(count):
            # Random position (avoid edges)
            x = random.uniform(0.2, 0.8)
            y = random.uniform(0.2, 0.8)

            # Random color from available palette
            color = random.choice(self.available_colors)

            target = Target(
                x=x,
                y=y,
                radius=0.05,  # 5% of screen size
                color=color,
                points=100,
                spawn_time=time.time(),
                target_id=self._next_target_id  # Assign stable ID
            )

            self._next_target_id += 1
            self.targets.append(target)

    def _calculate_distance(self, x: float, y: float, target: Target) -> float:
        """Calculate normalized distance from point to target center."""
        dx = x - target.x
        dy = y - target.y
        return math.sqrt(dx*dx + dy*dy)


if __name__ == "__main__":
    # Standalone test
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Simple Target Game - AMS Example")
    clock = pygame.time.Clock()

    # Create game
    game = SimpleTargetGame(800, 600)

    print("Simple Target Game - AMS Example")
    print("Click on targets to shoot them!")
    print("Demonstrates temporal hit detection")

    running = True
    while running:
        dt = clock.tick(60) / 1000.0  # 60 FPS

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Simulate PlaneHitEvent from mouse click
                mouse_x, mouse_y = event.pos
                norm_x = mouse_x / 800
                norm_y = mouse_y / 600

                hit_event = PlaneHitEvent(
                    x=norm_x,
                    y=norm_y,
                    timestamp=time.time(),
                    detection_method="mouse"
                )

                # Handle hit
                result = game.handle_hit_event(hit_event)
                print(f"  {result.message}")

        # Update game
        game.update(dt)

        # Render
        game.render(screen)
        pygame.display.flip()

    # Print final stats
    stats = game.get_history_stats()
    print(f"\nFinal Stats:")
    print(f"  Score: {game.score}")
    print(f"  Hits: {game.hits}")
    print(f"  Misses: {game.misses}")
    print(f"  History: {stats['snapshots']} snapshots, {stats['time_span']:.1f}s")

    pygame.quit()
