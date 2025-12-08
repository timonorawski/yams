# Many Random Targets - Design Document

## Overview

A target clearance game that generates a field of randomly distributed, non-overlapping targets. The player must hit all targets while avoiding misses. Every miss costs points, encouraging deliberate, accurate shooting over rushed attempts.

This trains a critical real-world skill: **clearing a field with accuracy**, where every shot matters and mistakes are costly.

**Inspiration**: The "egg carton" training method - place an egg carton on your target and work through the cups one by one, never hitting the same cup twice. This game digitizes that progression.

## Core Mechanics

### Target Generation
- Targets spawn at random positions across the canvas
- Non-overlapping placement with minimum spacing
- Configurable target count (default: 10-20 targets)
- Configurable target sizes (uniform or varied)
- All targets visible from round start

### Scoring System
| Action | Points | Notes |
|--------|--------|-------|
| Hit target | +100 | Base points per target |
| Miss (hit empty space) | -50 | Penalty for inaccuracy (configurable) |
| Duplicate hit | -25 | Hitting same target twice (if duplicates allowed) |
| Remaining targets (time out) | -25 each | Incomplete clearance penalty |
| Perfect round bonus | +200 | All targets, zero misses, no duplicates |

**Final Score** = Hits - Misses - Duplicates - Remaining + Bonuses

Lower miss count matters more than speed (unless timed mode).

### Miss Behavior (Configurable)

| Mode | Behavior | Use Case |
|------|----------|----------|
| `penalty` (default) | Miss = -50 points, continue playing | Forgiving practice |
| `strict` | Miss = round ends immediately | High-stakes training |

### Duplicate Hit Behavior (Configurable)

| Mode | Behavior | Use Case |
|------|----------|----------|
| `no-duplicates` (default) | Target removed on first hit | Standard egg carton rules |
| `allow-duplicates` | Target stays, duplicate hits penalized | Tests target tracking awareness |

### Round Flow

```
┌─────────────────────────────────────────────────────────┐
│  READY                                                  │
│  ┌─────────────────┐                                    │
│  │  ○   ○      ○   │    Targets: 15                     │
│  │    ○    ○       │    Ready...                        │
│  │  ○      ○   ○   │                                    │
│  │     ○  ○    ○   │    Click to start                  │
│  │  ○       ○   ○  │                                    │
│  └─────────────────┘                                    │
└─────────────────────────────────────────────────────────┘
                         ↓ first click
┌─────────────────────────────────────────────────────────┐
│  PLAYING                                                │
│  ┌─────────────────┐                                    │
│  │  ●   ○      ○   │    Targets: 12 / 15                │
│  │    ○    ●       │    Hits: 3                         │
│  │  ○      ○   ✗   │    Misses: 1                       │
│  │     ●  ○    ○   │    Score: 250                      │
│  │  ○       ○   ○  │                                    │
│  └─────────────────┘    [■■■■■□□□□□] Time               │
└─────────────────────────────────────────────────────────┘
                         ↓ all targets hit OR time runs out
┌─────────────────────────────────────────────────────────┐
│  ROUND COMPLETE                                         │
│  ┌─────────────────┐                                    │
│  │                 │    Round Summary:                  │
│  │   ROUND OVER    │    ─────────────                   │
│  │                 │    Hits: 14 (+1400)                │
│  │    Score: 1150  │    Misses: 2 (-100)                │
│  │                 │    Remaining: 1 (-25)              │
│  │                 │    ─────────────                   │
│  └─────────────────┘    Total: 1275                     │
│  Click to play again                                    │
└─────────────────────────────────────────────────────────┘
```

## Game Modes

### 1. Standard Mode (Default)
- Fixed target count (configurable, default: 15)
- No time limit
- Round ends when all targets hit
- Misses penalized but don't end round

### 2. Timed Mode (`--timed`)
- Same target count
- Time limit (default: 60 seconds)
- Round ends when time expires OR all targets hit
- Remaining targets at timeout penalized

### 3. Endless Mode (`--endless`)
- Continuous play: new targets appear as old ones are hit
- Maintains constant target count on screen
- Track total hits vs misses over session
- No "win" condition - practice until you stop

### 4. Challenge Mode (`--challenge`)
- Increasing difficulty across rounds
- Round 1: 10 large targets, no timer
- Round 2: 12 medium targets, 90 seconds
- Round 3: 15 small targets, 75 seconds
- And so on...
- Session ends on failed round (score below threshold)

### 5. Progressive Mode (`--progressive`)
- **Targets shrink as you clear them**
- All targets start at the same size
- Each hit causes remaining targets to shrink slightly
- Creates increasing difficulty within a single round
- Final targets are much smaller than starting targets
- Tests sustained focus and adaptation to shrinking targets
- Configurable shrink rate (`--shrink-rate`, default: 0.9 = 10% smaller per hit)

## Configuration Options

### Command Line Arguments

```bash
# Development mode
python dev_game.py manytargets                    # Default: 15 targets, no timer
python dev_game.py manytargets --count 20         # 20 targets
python dev_game.py manytargets --timed 60         # 60 second timer
python dev_game.py manytargets --size small       # Smaller targets
python dev_game.py manytargets --endless          # Endless practice mode
python dev_game.py manytargets --miss-mode strict # Miss = game over
python dev_game.py manytargets --allow-duplicates # Targets stay after hit
python dev_game.py manytargets --progressive      # Targets shrink as you clear

# Egg carton simulation (strict, no duplicates, 12 targets)
python dev_game.py manytargets --count 12 --miss-mode strict

# Progressive challenge
python dev_game.py manytargets --progressive --shrink-rate 0.85 --count 20

# With AMS
python ams_game.py --game manytargets --backend laser --count 12
```

### Game Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--count` | 15 | Number of targets to generate |
| `--size` | medium | Target size: small, medium, large, mixed |
| `--timed` | None | Time limit in seconds (None = unlimited) |
| `--spacing` | 1.5 | Minimum spacing between targets (multiplier of radius) |
| `--endless` | false | Enable endless mode |
| `--miss-penalty` | 50 | Points deducted per miss |
| `--hit-bonus` | 100 | Points per target hit |
| `--miss-mode` | penalty | Miss behavior: `penalty` (lose points) or `strict` (game over) |
| `--allow-duplicates` | false | If true, targets stay after hit (duplicate hits penalized) |
| `--progressive` | false | Enable progressive mode (targets shrink as you clear) |
| `--shrink-rate` | 0.9 | Size multiplier per hit in progressive mode (0.9 = 10% smaller) |
| `--min-size` | 15 | Minimum target radius in progressive mode (pixels) |

### Environment Variables (.env)

```bash
# Display
SCREEN_WIDTH=1280
SCREEN_HEIGHT=720

# Target settings
DEFAULT_TARGET_COUNT=15
TARGET_RADIUS_SMALL=25
TARGET_RADIUS_MEDIUM=40
TARGET_RADIUS_LARGE=60
MIN_TARGET_SPACING=1.5      # Multiplier of radius

# Scoring
HIT_POINTS=100
MISS_PENALTY=50
REMAINING_PENALTY=25
PERFECT_BONUS=200

# Timing
DEFAULT_TIME_LIMIT=60       # Seconds (for timed mode)
```

## Visual Design

### Target Appearance

```
Standard Target:          Hit Target:              Miss Marker:
     ╭───╮                    (fades out)              ✗
    │  ○  │               ╭───╮                   (red, fades)
    │     │              │ ✓  │
     ╰───╯                ╰───╯
  (white ring)          (green flash)
```

### Color Scheme

| Element | Color | Notes |
|---------|-------|-------|
| Background | Dark gray | `(30, 30, 35)` |
| Target ring | White | `(255, 255, 255)` |
| Target fill | Dark blue | `(40, 60, 100)` optional |
| Hit flash | Green | `(100, 255, 100)` brief |
| Hit marker (remaining) | Dim green | `(60, 120, 60)` |
| Miss marker | Red X | `(255, 80, 80)` |
| Timer bar | Yellow → Red | Changes as time runs low |

### HUD Layout

```
┌────────────────────────────────────────────────────────────┐
│ Targets: 8/15        Score: 750         Time: 0:45        │
│ Hits: 7  Misses: 1                      [■■■■■■□□□□]      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│                    (game area)                             │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Target Placement Algorithm

Non-overlapping random placement:

```python
def generate_targets(count: int, radius: float, screen_size: tuple) -> List[Vector2D]:
    targets = []
    margin = radius * 2
    max_attempts = 1000

    for _ in range(count):
        for attempt in range(max_attempts):
            x = random.uniform(margin, screen_size[0] - margin)
            y = random.uniform(margin, screen_size[1] - margin)
            candidate = Vector2D(x, y)

            # Check spacing against all existing targets
            min_dist = radius * 2 * MIN_TARGET_SPACING
            if all(distance(candidate, t) >= min_dist for t in targets):
                targets.append(candidate)
                break
        else:
            # Could not place target - reduce count or use smaller spacing
            break

    return targets
```

If placement fails (too many targets for screen), the game should:
1. Reduce target count to fit
2. Log warning
3. Continue with fewer targets

## State Machine

```
READY (show all targets, wait for first shot)
    ↓ first hit/miss
PLAYING (track hits, misses, time)
    ↓ all targets hit
COMPLETE (show results, perfect bonus if no misses)
    ↓ click
READY (new round)

--- OR (timed mode) ---

PLAYING
    ↓ time expires
TIMEOUT (show results with remaining penalty)
    ↓ click
READY

--- OR (strict miss mode) ---

PLAYING
    ↓ miss (hit empty space)
FAILED (show results, highlight miss location)
    ↓ click
READY (new round)
```

## Training Value

### Skills Developed

1. **Deliberate Accuracy**: Miss penalty discourages "spray and pray"
2. **Target Prioritization**: Player decides order (closest? largest? pattern?)
3. **Coverage Planning**: Efficient path through target field
4. **Composure Under Pressure**: Timer adds urgency without rewarding panic

### Real-World Parallels

- **Egg carton method**: The original inspiration - work through an egg carton without repeating cups
- **Field archery**: Navigating a course with varied target positions
- **Practical shooting**: Clearing a stage with multiple targets
- **Hunting**: Taking clean shots vs. wounding misses

## File Structure

```
games/ManyTargets/
├── __init__.py
├── game_info.py          # Registry metadata, CLI args
├── game_mode.py          # ManyTargetsMode class
├── target_field.py       # TargetField class (generation, tracking)
├── config.py             # Load .env settings
├── .env                  # Default configuration
└── input/                # Input abstraction layer
    ├── __init__.py
    ├── input_event.py
    ├── input_manager.py
    └── sources/
        ├── __init__.py
        ├── base.py
        └── mouse.py
```

## VS Code Launch Configs

```json
{
    "name": "Dev: Many Targets",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/dev_game.py",
    "args": ["manytargets"],
    "console": "integratedTerminal",
    "cwd": "${workspaceFolder}",
    "python": "${workspaceFolder}/venv/bin/python"
},
{
    "name": "Dev: Many Targets (Egg Carton/Strict)",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/dev_game.py",
    "args": ["manytargets", "--count", "12", "--miss-mode", "strict"],
    "console": "integratedTerminal",
    "cwd": "${workspaceFolder}",
    "python": "${workspaceFolder}/venv/bin/python"
},
{
    "name": "Dev: Many Targets (Progressive)",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/dev_game.py",
    "args": ["manytargets", "--progressive", "--count", "20"],
    "console": "integratedTerminal",
    "cwd": "${workspaceFolder}",
    "python": "${workspaceFolder}/venv/bin/python"
},
{
    "name": "Dev: Many Targets (Timed)",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/dev_game.py",
    "args": ["manytargets", "--timed", "60"],
    "console": "integratedTerminal",
    "cwd": "${workspaceFolder}",
    "python": "${workspaceFolder}/venv/bin/python"
},
{
    "name": "Dev: Many Targets (Allow Duplicates)",
    "type": "debugpy",
    "request": "launch",
    "program": "${workspaceFolder}/dev_game.py",
    "args": ["manytargets", "--allow-duplicates"],
    "console": "integratedTerminal",
    "cwd": "${workspaceFolder}",
    "python": "${workspaceFolder}/venv/bin/python"
}
```

## Implementation Priority

### Phase 1: Core Game
- [ ] Target generation with non-overlap
- [ ] Basic hit/miss detection
- [ ] Score tracking
- [ ] Round complete detection
- [ ] Basic HUD

### Phase 2: Core Options
- [ ] Miss mode: penalty vs strict (game over)
- [ ] Duplicate hits: allow/disallow
- [ ] Timer mode

### Phase 3: Progressive Mode
- [ ] Targets shrink on each hit
- [ ] Configurable shrink rate
- [ ] Minimum size threshold
- [ ] Visual feedback for shrinking

### Phase 4: Polish
- [ ] Hit/miss animations
- [ ] Sound effects
- [ ] Session statistics
- [ ] Endless mode
- [ ] Challenge mode
- [ ] Variable target sizes

## Future Enhancements

Potential additions (not initial scope):

1. **Target Types**: Some targets worth more, some are "bombs" (don't hit)
2. **Patterns**: Targets form recognizable shapes
3. **Moving Targets**: Some targets drift slowly
4. **Zones**: Different screen regions worth different multipliers
5. **Replay**: Show shot sequence after round
6. **Analytics**: Track accuracy by screen region over sessions
