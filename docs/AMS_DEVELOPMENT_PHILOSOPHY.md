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

# **Design Philosophy: Constraints as Engines of Flexibility**

One of the core architectural principles behind AMS is deceptively simple:

> **Constraints do not reduce flexibility.
> They *create* it.**

In software systems—especially ones intended to operate in unpredictable real-world environments—unbounded flexibility quickly turns into unbounded fragility. Every subsystem must compensate for every possible variation, leading to exponential complexity, inconsistent behavior, and brittle code.

AMS takes the opposite approach: it establishes *strong, explicit constraints* at every architectural boundary. These constraints reduce the state space each component must reason about, which in turn creates a system that is more predictable, more maintainable, and ultimately **far more flexible**.

## **1. ContentFS: The Power of Layer Boundaries**

ContentFS enforces a strict rule:

**All game content must exist within layered virtual filesystems.**

This constraint yields:

* deterministic asset resolution
* secure sandboxing
* natural modding support
* reliable user overrides
* shareable team overlays
* consistent paths across all platforms

By reducing where content *can* live, AMS dramatically increases what content can *do*: override, extend, mod, and customize without adding special cases or ad-hoc lookups.

## **2. YAML Game Definitions: Structure Enables Expression**

Games in AMS must conform to the `game.yaml` schema. This ensures:

* consistent entity definitions
* predictable metadata
* strict validation
* uniform loading processes
* compatibility with editors and tooling

What appears restrictive (“you must define games this way”) is actually liberating: new games can be dropped in without writing a single line of Python, and the engine can safely introspect, validate, and manipulate them.

## **3. Behavior Scripts: Separation of Declaration and Logic**

AMS enforces a clear division:

* YAML declares **what** exists
* Lua defines **how** it behaves
* Python provides **the runtime**

This constraint gives us:

* reusable behaviors
* composable entities
* hot-swappable logic
* minimal cross-language contamination
* game portability across devices and backends

Without this boundary, games would sprawl into arbitrary mixtures of Python/YAML/Lua, losing testability and composability.

## **4. Backend Isolation: Games Don’t Know CV Exists**

Games in AMS **never** interact with cameras, projectors, homographies, or CV pipelines directly. They receive plain logical events—just like a mouse-driven desktop game.

This constraint unlocks:

* seamless transition between dev mode and projector mode
* predictable behavior across real-world setups
* CV simulation without changing a line of game code
* portability to WebAssembly
* safety and determinism

Had games been coupled to the CV backend, none of this would be possible.

## **5. Normalized Coordinates: The Constraint That Shrinks the Universe**

AMS uses a strict normalization step that reduces all input—CV or otherwise—to a stable coordinate space before it reaches the game.

This deliberate constraint eliminates:

* projector angle dependencies
* surface warping
* device-specific calibration
* target distortion
* distance variation

…and replaces all of them with a unified measurement system.

The result is the surprising freedom to run the same game on:

* a wall
* an archery target
* a floor
* a foam dartboard
* a virtual canvas
* a browser window

All without modification.

## **6. Predictable Composition Over Arbitrary Possibility**

The general pattern behind all of these decisions:

**When components have strict, reliable boundaries, the system as a whole becomes vastly more flexible.**

Unbounded systems collapse under the weight of their own variability.
Bounded systems become **composable**, and composability is the true source of power and expressiveness.

AMS is built on boundaries—not to box developers in, but to eliminate ambiguity.
What remains is a platform where new games, tools, and features can be added with confidence that they will behave correctly.

This is the way