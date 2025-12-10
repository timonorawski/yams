# AMS Game Development Philosophy  
The Core Primal Arcade Games & The Canvas That Never Dies  
2025–∞

## The Truth Everyone Forgot

There are only roughly six real arcade games.

Everything else is skin, juice, and minor rule tweaks.

1. Breakout / Pong  
   → Bounce the thing off the paddle  
2. Space Invaders / Galaga  
   → Shoot the descending swarm  
3. Pac-Man  
   → Navigate the maze, flip predator/prey  
4. Asteroids  
   → Thrust + shoot in open space  
5. Robotron / Gauntlet  
   → Twin-stick murder room  
6. Track & Field / Rhythm games  
   → Hit the button on the beat

From these six primitives, constrained by 256×224 pixels, 16 colors, and a 25-cent coin slot, came the entire golden age of arcade.

The magic was never the graphics.  
The magic was the **perfectly brutal constraint**.

## AMS Is the Modern Evolution of That Constraint when we remove the hardware constraints of microcontroller architecture.

We kept the brutality.  
We removed the coin slot.

AMS gives you the same primal canvases — but now:

- The paddle is moved by real arrows or Nerf darts  
- The swarm descends across your living-room wall or 50-yard range  
- The maze is built from arrows stuck in foam  
- The thrust is controlled by the rhythm of your breath  
- The murder room is your entire body in real space  
- The beat is the heartbeat of a stroke patient re-learning to aim

Same six games.  
Infinite reality.

## The Current Six Core Engines (2025 Edition)

| Primal Game        | AMS Core Engine       | Example Titles (already shipped or trivial) |
|--------------------|-----------------------|---------------------------------------------|
| Breakout / Pong    | BrickBreaker          | Brick Breaker, Invader Breaker, Death Star Trench Run |
| Space Invaders     | SwarmDefense          | Galaga, Missile Command, Asteroids (descending variant) |
| Pac-Man            | MazeNavigator         | Maze Masochist, Trail Blazer (escort mode) |
| Asteroids          | OpenSpaceThrust       | Asteroids, Free-Fly Trench Run |
| Robotron           | Containment           | Containment (the genre you invented) |
| Rhythm / Track     | RhythmFlapper         | Rhythm Flapper, Note Progression, Duck Hunt (beat-based) |

Every other game you or the community will ever make is likely just one of these six, with different YAML and sprites - but we're leaving the door open for people to invent new game concepts.

## The Philosophy in One Sentence

**Code the primal constraints once.  
Let data do the rest forever.**

### What belongs in code (never changes)
- The core physics loops
- Temporal state retro-queries
- Quiver + retrieval rhythm
- Palette auto-contrast
- PlaneHitEvent → InputEvent pipeline
- YAML → behavior interpreter
- Plugin system for the last 1 %

### What belongs in data (changes every day)
- Does the brick descend? → `descends: true`
- Does it shoot back? → `shoots: true`
- Does it transform into a duck when hit? → `transform: platform_assets.duck`
- Does it split into four angry pieces? → `split: 4`
- Does it laugh like the Duck Hunt dog? → `on_hit: dog_laugh`

## The Canvas Is Sacred

The canvas is still primitive:
- 0.0–1.0 normalized coordinates
- One projectile stream at a time
- Retrieval pauses are mandatory
- Latency is a feature, not a bug

These are not limitations.  
These are the **new 25-cent coin slot**.

They force the same genius the original arcade designers were forced into.

Except now anyone can paint on the canvas — with a text file.

## The Result

- A 10-year-old makes “My Little Pony Galaga” in 10 minutes  
- A stroke therapist makes “slow descending bricks for hand rehab” in 5 minutes  
- A retro purist makes pixel-perfect Galaga in a weekend  
- You never write another game loop again

We have built an **arcade platform anyone can build games for**.

Six games.  
Infinite everything else.

This is the AMS philosophy.

**Code the constraints.  
Free the creativity.  
Let the world play.**

— The Arcade Management System Manifesto, 2025