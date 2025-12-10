# AMS Game Architecture — Design Rationale

## Core Observation

Most arcade games are variations on a small number of mechanical patterns. The differences between games are primarily:

- Visual presentation (sprites, colors, theme)
- Tuning parameters (speed, spawn rates, scoring)
- Composition of behaviors (does it shoot? does it descend?)

The underlying mechanics are surprisingly few.

## The Six Primal Patterns

| Pattern | Core Mechanic | Classic Examples |
|---------|---------------|------------------|
| **Paddle/Bounce** | Deflect object with player-controlled surface | Breakout, Pong, Arkanoid |
| **Swarm Defense** | Shoot at descending/approaching enemies | Space Invaders, Galaga, Centipede |
| **Maze Navigation** | Move through constrained paths, state-based predator/prey | Pac-Man, Rally-X |
| **Thrust/Inertia** | Player movement with momentum in open space | Asteroids, Lunar Lander |
| **Arena Survival** | Omnidirectional movement, enemies spawn from edges | Robotron, Smash TV, Geometry Wars |
| **Rhythm/Timing** | Input must align with temporal pattern | Track & Field, Dance Dance Revolution, Guitar Hero |

These patterns can combine. Galaga is Swarm Defense + Rhythm (firing cadence). Asteroids is Thrust + Split (fragments). Most "new" arcade games are recombinations with fresh visuals.

## Architectural Implication

If six patterns cover most arcade games, then:

1. **Behaviors that implement these patterns are the core library**
2. **Games are primarily data** — which behaviors to use, how to configure them
3. **New games shouldn't require new code** — just new YAML and assets

This is the design goal, not a claim that we've achieved it. Some games will need new behaviors. But those new behaviors join the library for future games.

## What Lives in Code vs. Data

**Engine (Python) — stable, rarely changes:**
- Game loop (input → update → render)
- Collision detection
- Lua VM hosting
- YAML parsing
- Input handling (physical plane, keyboard, etc.)
- Rendering and audio playback

**Behaviors (Lua) — grows over time:**
- `descend` — entity moves toward player/bottom
- `shoot` — entity fires projectiles
- `bounce` — entity reflects off surfaces
- `thrust` — momentum-based player movement
- `patrol` — entity follows a path
- `rhythm_gate` — input validated against beat
- `split` — entity spawns children
- `transform` — entity changes properties
- `transmute` — entity replaced by new entities

**Game Definitions (YAML) — changes constantly:**
- Entity types and their sprites
- Which behaviors attach to which entities
- Behavior parameters (speed, interval, pattern)
- Level layout and progression
- Win/lose conditions
- Scoring rules

## AMS-Specific Considerations

AMS has constraints beyond typical game engines:

- **Physical input** — Arrows/darts hitting a plane, not button presses
- **Retrieval rhythm** — Mandatory pauses while player retrieves projectiles
- **Projection context** — Games displayed on walls, foam targets, various surfaces
- **Accessibility range** — From competitive archers to rehabilitation patients

These constraints shape the behaviors:

- `rhythm_gate` aligns naturally with retrieval cadence
- Descend speeds must account for physical aiming time
- Difficulty tuning has a wider range than typical games

## The Test

The architecture is working if:

- A new Breakout variant requires only YAML and sprites
- A new Galaga variant requires only YAML and sprites
- A genuinely new mechanic requires one new Lua behavior, which then becomes reusable
- Someone unfamiliar with the codebase can create a game by reading examples

The architecture is failing if:

- "Simple" game variants require Python changes
- Behaviors have special cases for specific games
- The YAML schema keeps expanding to handle edge cases
- Core behaviors need API methods that user behaviors can't access