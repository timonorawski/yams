#!/usr/bin/env python3
"""
Test script for projectile limiting feature.

Verifies that:
1. classic_archery.yaml loads correctly
2. DynamicGameMode initializes with projectile counter
3. Projectile counter decrements on input
4. Game transitions to WAITING_FOR_RELOAD when depleted
5. reload() method restores projectiles and resumes play
"""

import sys
from game.mode_loader import GameModeLoader
from game.modes.dynamic import DynamicGameMode
from input.input_event import InputEvent
from models import Vector2D, EventType, GameState
import time

print("=" * 70)
print("PROJECTILE LIMITING SYSTEM TEST")
print("=" * 70)
print()

# Test 1: Load classic_archery.yaml
print("Test 1: Loading classic_archery.yaml...")
try:
    loader = GameModeLoader()
    config = loader.load_mode("classic_archery")
    print(f"✓ Loaded: {config.name}")
    print(f"  - Projectiles per round: {config.rules.projectiles_per_round}")
    print(f"  - Game type: {config.rules.game_type}")
    print()
except Exception as e:
    print(f"✗ Failed to load: {e}")
    sys.exit(1)

# Test 2: Initialize DynamicGameMode
print("Test 2: Initializing DynamicGameMode...")
try:
    mode = DynamicGameMode(config, audio_enabled=False)
    projectiles = mode.get_projectiles_remaining()
    print(f"✓ Mode initialized")
    print(f"  - Initial projectiles: {projectiles}")
    print(f"  - Game state: {mode.state}")
    print()

    if projectiles != 6:
        print(f"✗ Expected 6 projectiles, got {projectiles}")
        sys.exit(1)
    if mode.state != GameState.PLAYING:
        print(f"✗ Expected PLAYING state, got {mode.state}")
        sys.exit(1)
except Exception as e:
    print(f"✗ Failed to initialize: {e}")
    sys.exit(1)

# Test 3: Simulate projectile usage
print("Test 3: Simulating projectile usage...")
try:
    # Fire 5 shots
    for i in range(5):
        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=time.time(),
            event_type=EventType.MISS
        )
        mode.handle_input([event])
        remaining = mode.get_projectiles_remaining()
        print(f"  - Shot {i+1}: {remaining} projectiles remaining")

        if remaining != 5 - i:
            print(f"✗ Expected {5-i} projectiles, got {remaining}")
            sys.exit(1)

    # Check state is still PLAYING
    if mode.state != GameState.PLAYING:
        print(f"✗ Expected PLAYING state after 5 shots, got {mode.state}")
        sys.exit(1)

    print("✓ First 5 shots processed correctly")
    print()
except Exception as e:
    print(f"✗ Failed during projectile usage: {e}")
    sys.exit(1)

# Test 4: Deplete last projectile
print("Test 4: Depleting last projectile...")
try:
    event = InputEvent(
        position=Vector2D(x=100.0, y=100.0),
        timestamp=time.time(),
        event_type=EventType.MISS
    )
    mode.handle_input([event])
    remaining = mode.get_projectiles_remaining()
    state = mode.state

    print(f"  - Shot 6: {remaining} projectiles remaining")
    print(f"  - Game state: {state}")

    if remaining != 0:
        print(f"✗ Expected 0 projectiles, got {remaining}")
        sys.exit(1)

    if state != GameState.WAITING_FOR_RELOAD:
        print(f"✗ Expected WAITING_FOR_RELOAD state, got {state}")
        sys.exit(1)

    print("✓ Game correctly transitioned to WAITING_FOR_RELOAD")
    print()
except Exception as e:
    print(f"✗ Failed during depletion: {e}")
    sys.exit(1)

# Test 5: Verify no more input accepted
print("Test 5: Verifying no input accepted in WAITING_FOR_RELOAD...")
try:
    event = InputEvent(
        position=Vector2D(x=100.0, y=100.0),
        timestamp=time.time(),
        event_type=EventType.MISS
    )
    mode.handle_input([event])
    remaining = mode.get_projectiles_remaining()

    if remaining != 0:
        print(f"✗ Projectile count changed during WAITING_FOR_RELOAD: {remaining}")
        sys.exit(1)

    print("✓ Input correctly ignored in WAITING_FOR_RELOAD state")
    print()
except Exception as e:
    print(f"✗ Failed during input verification: {e}")
    sys.exit(1)

# Test 6: Test reload() method
print("Test 6: Testing reload() method...")
try:
    mode.reload()
    remaining = mode.get_projectiles_remaining()
    state = mode.state

    print(f"  - Projectiles after reload: {remaining}")
    print(f"  - Game state: {state}")

    if remaining != 6:
        print(f"✗ Expected 6 projectiles after reload, got {remaining}")
        sys.exit(1)

    if state != GameState.PLAYING:
        print(f"✗ Expected PLAYING state after reload, got {state}")
        sys.exit(1)

    print("✓ Reload correctly restored projectiles and resumed play")
    print()
except Exception as e:
    print(f"✗ Failed during reload: {e}")
    sys.exit(1)

# Test 7: Verify unlimited projectiles mode
print("Test 7: Testing unlimited projectiles (classic_ducks)...")
try:
    config_unlimited = loader.load_mode("classic_ducks")
    mode_unlimited = DynamicGameMode(config_unlimited, audio_enabled=False)

    projectiles = mode_unlimited.get_projectiles_remaining()
    print(f"  - Projectiles: {projectiles}")

    if projectiles is not None:
        print(f"✗ Expected None for unlimited mode, got {projectiles}")
        sys.exit(1)

    # Fire 10 shots - should never transition to WAITING_FOR_RELOAD
    for i in range(10):
        event = InputEvent(
            position=Vector2D(x=100.0, y=100.0),
            timestamp=time.time(),
            event_type=EventType.MISS
        )
        mode_unlimited.handle_input([event])

    if mode_unlimited.state != GameState.PLAYING:
        print(f"✗ Unlimited mode should stay in PLAYING, got {mode_unlimited.state}")
        sys.exit(1)

    print("✓ Unlimited projectiles mode works correctly")
    print()
except Exception as e:
    print(f"✗ Failed during unlimited mode test: {e}")
    sys.exit(1)

print("=" * 70)
print("ALL TESTS PASSED ✓")
print("=" * 70)
print()
print("Summary:")
print("  - classic_archery.yaml validates correctly")
print("  - Projectile counter tracks usage accurately")
print("  - Game transitions to WAITING_FOR_RELOAD when depleted")
print("  - reload() restores projectiles and resumes gameplay")
print("  - Unlimited mode (None) works as expected")
print()
print("Integration with AMS:")
print("  - Game exposes get_projectiles_remaining() for status queries")
print("  - Game transitions to WAITING_FOR_RELOAD when depleted")
print("  - AMS can display interstitial (e.g., 'Collect your arrows')")
print("  - AMS calls reload() when ready to resume")
