# Grouping Game - Design Document

## Overview

A precision training game that measures and visualizes shot grouping in real-time. The game challenges you to maintain consistency - hit inside the target or the round ends. Your final group size IS your score - smaller is better.

This directly trains the fundamental skill in archery/shooting: **consistency**.

## Grouping Methods

The game supports three distinct training methods, each targeting different skills:

### 1. Centroid Mode (`--method centroid`)

**How it works:**
- Target appears at random position
- Each hit is recorded; target center moves to the centroid of all hits
- Target radius shrinks to encompass all hits (with margin)
- Miss (outside current target) ends the round

**What it trains:**
- Natural grouping tendency - where do your shots naturally cluster?
- Identifies your natural point of aim vs. intended aim
- Good for discovering systematic errors in your form

**Best for:** Understanding your natural shot distribution, identifying consistency issues

### 2. Fixed Center Mode (`--method fixed`)

**How it works:**
- Target appears at random position (guide only)
- First hit establishes the center point (wherever you hit)
- Second hit establishes the radius (distance from center to second hit)
- All subsequent hits must stay within that fixed circle
- Miss (outside circle) ends the round

**What it trains:**
- Ability to repeat a shot exactly
- Pure consistency without a predetermined target
- Self-defined challenge - your first shot sets your own bar

**Best for:** Testing pure repeatability, training muscle memory for a self-chosen position

### 3. Fixed Origin Mode (`--method origin`)

**How it works:**
- Target appears at random position (the goal)
- First hit establishes the radius (distance from target center to your shot)
- All subsequent hits must stay within that circle around the original target
- Miss (outside circle) ends the round

**What it trains:**
- Hitting a specific known target consistently
- Accuracy + consistency combined
- Traditional "hit the bullseye repeatedly" training

**Best for:** Traditional target practice, training to hit a specific mark consistently

## Method Comparison

| Aspect | Centroid | Fixed Center | Fixed Origin |
|--------|----------|--------------|--------------|
| Target Center | Moves to centroid | Set by 1st shot | Fixed at origin |
| Radius | Shrinks to group | Set by 2nd shot | Set by 1st shot |
| Tests | Natural grouping | Pure repeatability | Accuracy + consistency |
| Challenge | Keep tightening | Maintain your standard | Hit the mark repeatedly |

## Game Flow

```
┌─────────────────────────────────────────────────────────┐
│  WAITING                                                │
│  ┌─────────────────┐                                    │
│  │                 │    Mode: FIXED ORIGIN              │
│  │    ◎            │    Phase: Set group radius         │
│  │  (target)       │    Shots: 0                        │
│  │                 │                                    │
│  └─────────────────┘                                    │
│  First hit starts the round                             │
└─────────────────────────────────────────────────────────┘
                          ↓ first hit
┌─────────────────────────────────────────────────────────┐
│  PLAYING                                                │
│  ┌─────────────────┐                                    │
│  │      ┌───┐      │    Mode: FIXED ORIGIN              │
│  │      │ ◎ │      │    Phase: Stay in the circle       │
│  │      │ • │      │    Shots: 3                        │
│  │      └───┘      │    Group: 45.2px (locked)          │
│  └─────────────────┘    Best: 32.1px                    │
│  Stay inside the circle                                 │
└─────────────────────────────────────────────────────────┘
                          ↓ miss (outside target)
┌─────────────────────────────────────────────────────────┐
│  ROUND OVER                                             │
│  ┌─────────────────┐                                    │
│  │      ┌───┐      │    Round Complete!                 │
│  │      │•••│ ✗    │    Shots: 7                        │
│  │      │ • │      │    Final Group: 45.2px             │
│  │      └───┘      │    Best: 32.1px                    │
│  └─────────────────┘                                    │
│  Click or press R to start new round                    │
└─────────────────────────────────────────────────────────┘
```

## Usage

### Command Line

```bash
# Development mode (mouse input, no hardware needed)
python dev_game.py grouping                      # Default: centroid mode
python dev_game.py grouping --method centroid    # Shrinking group
python dev_game.py grouping --method fixed       # Set your own center + radius
python dev_game.py grouping --method origin      # Fixed target, set radius

# With AMS (laser/object detection)
python ams_game.py --game grouping --backend laser --method origin
```

### VS Code Launch Configs

- `Dev: Grouping (Centroid)` - Shrinking centroid mode
- `Dev: Grouping (Fixed Center)` - Player sets center and radius
- `Dev: Grouping (Fixed Origin)` - Fixed target, player sets radius

### In-Game Controls

- **Click** - Shoot at target
- **R** - Restart round
- **F** - Toggle fullscreen
- **ESC** - Quit

## Scoring System

**Primary Score: Group Diameter (pixels)**
- Smaller = better
- Tracks: Current round, Session best
- In fixed modes, this is the diameter of the circle you must stay within
- In centroid mode, this shrinks as your group tightens

**Secondary Metrics:**
- Shot count (how many successful hits before miss)
- Rounds completed

## Visual Design

### Target Display

```
     ╭─────────────────╮
     │    ┌───────┐    │   Ghost ring: Initial target size (faded)
     │    │ ┌───┐ │    │   Current target: Active boundary (white)
     │    │ │ + │ │    │   Crosshair: Target center
     │    │ │• •│ │    │   Hit markers: Green dots
     │    │ └───┘ │    │
     │    └───────┘    │
     ╰─────────────────╯
```

### Color Scheme

| Element | Color | Notes |
|---------|-------|-------|
| Background | Dark blue-gray | `(20, 20, 30)` |
| Target ring | White | `(255, 255, 255)` |
| Hit markers | Green | `(100, 255, 100)` |
| Miss marker | Red X | `(255, 80, 80)` |
| Ghost ring | Dim gray | `(60, 60, 80)` |

### HUD Elements

- **Top-left:** Phase description, shot count, group size, session best
- **Top-right:** Current mode name
- **Bottom:** Instructions (on round over)

## Configuration

### Environment Variables (.env)

```bash
# Display
SCREEN_WIDTH=1280
SCREEN_HEIGHT=720

# Target settings
INITIAL_TARGET_RADIUS=150    # Starting size in pixels
MIN_TARGET_RADIUS=15         # Smallest allowed (centroid mode)
GROUP_MARGIN=1.15            # Buffer around group (centroid mode)

# Visual settings
SHOW_HIT_MARKERS=true        # Show green dots for hits
SHOW_GHOST_RING=true         # Show initial target size
ANIMATION_DURATION=0.2       # Target resize animation speed
```

## Training Recommendations

### For Beginners

Start with **Fixed Origin** mode:
1. You have a clear target to aim at (the crosshair)
2. Your first shot sets a reasonable challenge
3. Focus on repeating the same shot

### For Intermediate

Use **Centroid** mode to:
1. Discover your natural grouping tendency
2. See how tight you can get with extended focus
3. Identify if you're consistently off-center

### For Advanced

Challenge yourself with **Fixed Center** mode:
1. No predetermined target - pure consistency test
2. Your first shot matters - it sets your center
3. Second shot matters - it sets your challenge level
4. Tests true repeatability without visual aid

## File Structure

```
games/Grouping/
├── __init__.py
├── game_info.py          # Registry metadata, CLI args
├── game_mode.py          # GroupingMode class
├── grouping_round.py     # GroupingRound + GroupingMethod enum
├── config.py             # Load .env settings
├── .env                  # Default configuration
├── main.py               # Standalone entry
└── input/                # Input abstraction layer
    ├── __init__.py
    ├── input_event.py
    ├── input_manager.py
    └── sources/
        ├── __init__.py
        ├── base.py
        └── mouse.py
```

## Technical Details

### GroupingMethod Enum

```python
class GroupingMethod(Enum):
    CENTROID = "centroid"      # Center moves to centroid, radius shrinks
    FIXED_CENTER = "fixed_center"  # 1st hit = center, 2nd hit = radius
    FIXED_ORIGIN = "fixed_origin"  # Center = target origin, 1st hit = radius
```

### State Machine

```
WAITING (show target, wait for first hit)
    ↓ hit inside initial target
PLAYING (record hits, check bounds)
    ↓ hit inside → record, update display
    ↓ hit outside → end round
ROUND_OVER (show results, wait for restart)
    ↓ click or R
WAITING (new random target position)
```

### Grace Margin

Hits exactly on the boundary get a 3-pixel grace margin to feel fair.

## Future Enhancements

Potential additions (not yet implemented):

1. **Multi-Position Mode** - Complete groups at multiple screen positions
2. **Timed Mode** - Best group in fixed time limit
3. **Sound Effects** - Audio feedback for hits/misses
4. **Real-World Units** - Display in inches/cm if calibrated
5. **Historical Tracking** - Save best scores across sessions
6. **Difficulty Presets** - Easy/Medium/Hard starting sizes
