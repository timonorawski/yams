"""
Quick test script to validate the game_mode_config models.
"""

import yaml
from models.game_mode_config import GameModeConfig

# Example YAML from GAME_MODES_DESIGN.md (Incoming Asteroids mode)
example_yaml = """
name: "Incoming Threats"
id: "incoming_asteroids"
version: "1.0.0"
description: "Stop asteroids before they reach you"
author: "DuckHunt Dev"
theme: "space_asteroids"

trajectory:
  algorithm: "bezier_3d"
  depth_direction: "toward"
  curvature_factor: 0.0

spawning:
  spawn_sides: ["top", "bottom", "left", "right"]
  spawn_rate_base: 1.5
  max_active: 5

rules:
  game_type: "survival"
  max_misses: 3

levels:
  - level: 1
    target:
      size: 20.0
      speed: 80.0
      depth_range: [3.0, 1.0]
    trajectory:
      algorithm: "bezier_3d"
      depth_direction: "toward"
      curvature_factor: 0.0
    spawning:
      spawn_sides: ["top", "bottom", "left", "right"]
      spawn_rate_base: 2.0
      max_active: 2

  - level: 2
    target:
      size: 20.0
      speed: 100.0
      depth_range: [3.0, 1.0]
    trajectory:
      algorithm: "bezier_3d"
      depth_direction: "toward"
      curvature_factor: 0.3
    spawning:
      spawn_sides: ["top", "bottom", "left", "right"]
      spawn_rate_base: 1.8
      max_active: 3

scoring:
  base_hit_points: 10
  combo_multiplier: true
  apex_bonus: 50
  speed_bonus: true
"""

def test_basic_validation():
    """Test that the model can parse and validate example YAML."""
    config_dict = yaml.safe_load(example_yaml)
    config = GameModeConfig.model_validate(config_dict)

    print("✓ Basic validation passed")
    print(f"  Game Mode: {config.name}")
    print(f"  ID: {config.id}")
    print(f"  Version: {config.version}")
    print(f"  Levels: {len(config.levels)}")
    print(f"  Game Type: {config.rules.game_type}")
    print(f"  Max Misses: {config.rules.max_misses}")
    print()

    # Test immutability
    try:
        config.name = "Modified Name"
        print("✗ Immutability test FAILED - model should be frozen")
    except Exception:
        print("✓ Immutability test passed - model is frozen")

    return config

def test_validation_errors():
    """Test that invalid configurations are caught."""
    print("\nTesting validation errors:")

    # Test 1: Missing required field for game_type
    invalid_yaml_1 = """
name: "Test Mode"
id: "test"
version: "1.0.0"
description: "Test"
theme: "test"
trajectory:
  algorithm: "linear"
  depth_direction: "away"
spawning:
  spawn_sides: ["left", "right"]
  spawn_rate_base: 1.0
  max_active: 3
rules:
  game_type: "survival"
levels:
  - level: 1
    target:
      size: 10.0
      speed: 50.0
      depth_range: [1.0, 3.0]
    trajectory:
      algorithm: "linear"
      depth_direction: "away"
    spawning:
      spawn_sides: ["left"]
      spawn_rate_base: 1.0
      max_active: 1
scoring:
  base_hit_points: 10
  combo_multiplier: false
"""

    try:
        config_dict = yaml.safe_load(invalid_yaml_1)
        GameModeConfig.model_validate(config_dict)
        print("✗ Should have failed - survival mode requires max_misses")
    except ValueError as e:
        print(f"✓ Correctly caught missing max_misses: {e}")

    # Test 2: Invalid depth_range (min >= max)
    invalid_yaml_2 = """
name: "Test Mode"
id: "test"
version: "1.0.0"
description: "Test"
theme: "test"
trajectory:
  algorithm: "linear"
  depth_direction: "away"
spawning:
  spawn_sides: ["left", "right"]
  spawn_rate_base: 1.0
  max_active: 3
rules:
  game_type: "endless"
levels:
  - level: 1
    target:
      size: 10.0
      speed: 50.0
      depth_range: [3.0, 1.0]
    trajectory:
      algorithm: "linear"
      depth_direction: "away"
    spawning:
      spawn_sides: ["left"]
      spawn_rate_base: 1.0
      max_active: 1
scoring:
  base_hit_points: 10
  combo_multiplier: false
"""

    try:
        config_dict = yaml.safe_load(invalid_yaml_2)
        GameModeConfig.model_validate(config_dict)
        print("✓ Valid configuration - depth_range [3.0, 1.0] is allowed (approaching motion)")
    except ValueError as e:
        print(f"Info: {e}")

    # Test 3: Non-sequential level numbers
    invalid_yaml_3 = """
name: "Test Mode"
id: "test"
version: "1.0.0"
description: "Test"
theme: "test"
trajectory:
  algorithm: "linear"
  depth_direction: "away"
spawning:
  spawn_sides: ["left", "right"]
  spawn_rate_base: 1.0
  max_active: 3
rules:
  game_type: "endless"
levels:
  - level: 1
    target:
      size: 10.0
      speed: 50.0
      depth_range: [1.0, 3.0]
    trajectory:
      algorithm: "linear"
      depth_direction: "away"
    spawning:
      spawn_sides: ["left"]
      spawn_rate_base: 1.0
      max_active: 1
  - level: 3
    target:
      size: 8.0
      speed: 60.0
      depth_range: [1.0, 3.0]
    trajectory:
      algorithm: "linear"
      depth_direction: "away"
    spawning:
      spawn_sides: ["left"]
      spawn_rate_base: 1.2
      max_active: 2
scoring:
  base_hit_points: 10
  combo_multiplier: false
"""

    try:
        config_dict = yaml.safe_load(invalid_yaml_3)
        GameModeConfig.model_validate(config_dict)
        print("✗ Should have failed - levels must be sequential")
    except ValueError as e:
        print(f"✓ Correctly caught non-sequential levels: {e}")

if __name__ == "__main__":
    print("Testing Pydantic v2 Game Mode Configuration Models")
    print("=" * 60)
    print()

    config = test_basic_validation()
    test_validation_errors()

    print("\n" + "=" * 60)
    print("All tests completed!")
