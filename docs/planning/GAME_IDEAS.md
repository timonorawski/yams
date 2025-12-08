# Game Ideas Brainstorm

This document captures game ideas for the AMS platform. Games should leverage the core strength of the system: precision targeting with variable practice (different positions, timing, decisions each attempt).

## Design Principles

1. **Variable Practice**: Each attempt should be a fresh problem - avoid repetitive patterns
2. **Clear Feedback**: Immediate visual/audio response to hits and misses
3. **Skill Progression**: Games should reward improving accuracy and speed
4. **Projectile Agnostic**: Games work with any detection backend (mouse, laser, arrows, darts, etc.)

---

## Game Categories

### Target Practice / Accuracy

**1. Bullseye Rings**
- Concentric ring targets with point values (10-100)
- Targets appear at random positions
- Time pressure or limited shots
- Variants: Moving targets, shrinking targets, multiple simultaneous

**2. Sniper Challenge**
- Small, distant targets that require precision
- Wind/drift indicators (visual distraction, not physics)
- Limited time window before target disappears
- Scoring based on accuracy + speed

**3. Color Match**
- Targets of different colors appear
- Must hit targets in a specific color sequence
- Wrong color = penalty
- Tests both accuracy and pattern recognition

**4. Size Matters**
- Targets of varying sizes worth different points
- Smaller = more points but harder
- Risk/reward decision making

### Reflex / Speed

**5. Whack-a-Mole**
- Targets pop up briefly at random positions
- Must hit before they disappear
- Increasing speed over time
- Classic arcade feel

**6. Quick Draw**
- Single target appears - hit it as fast as possible
- Reaction time scoring
- False starts penalized
- Duel mode: two players, first accurate hit wins

**7. Meteor Shower**
- Objects fall from top of screen
- Must hit before they reach bottom
- Increasing frequency and speed
- Defense/survival theme

**8. Speed Circles**
- Expanding circles - hit when they reach optimal size
- Too early = miss, too late = miss
- Rhythm-game timing element

### Strategy / Decision Making

**9. Target Triage**
- Multiple targets with different point values and lifespans
- Must prioritize which to hit first
- Some targets subtract points if not hit
- Resource management under pressure

**10. Chain Reaction**
- Hit targets in correct order to build combos
- Adjacent/connected targets light up as valid next hits
- Encourages planning ahead while maintaining speed

**11. Bomb Defusal**
- Mix of targets and "bombs"
- Hitting bombs = game over or major penalty
- Tests discrimination under pressure
- Increasing bomb frequency

**12. Territory Control**
- Grid of zones, hit to claim
- Zones decay over time, need re-hitting
- Compete against AI or clock to control majority

### Rhythm / Pattern

**13. Beat Target**
- Targets appear synced to music/beat
- Hit on the beat for bonus points
- Miss timing = reduced score
- Different songs = different patterns

**14. Simon Says**
- Targets light up in sequence
- Player must hit in same sequence
- Increasing sequence length
- Memory + accuracy test

**15. Note Progression (Musical Memory)**
- Fixed target positions mapped to musical notes (like a piano/xylophone layout)
- System plays a melody by highlighting targets in sequence with corresponding tones
- Player reproduces the sequence by hitting targets in order
- Each hit plays the note - auditory feedback reinforces spatial-audio association
- Progression: start with 3-4 notes, add one each successful round
- Variants:
  - **Free Play**: Targets always active, make your own melodies
  - **Echo Mode**: Hear sequence, reproduce it
  - **Speed Round**: Same sequence, increasing tempo
  - **Harmony**: Multiple notes play simultaneously (chords) - hit all chord notes
- Training value: Working memory, pattern recognition, spatial-audio mapping
- Engagement: Musical feedback makes practice inherently rewarding
- Could use pentatonic scale (no wrong notes) for pleasant sounds regardless of skill

**16. Pattern Recognition**
- Targets form patterns (shapes, letters, numbers)
- Hit targets in order to "draw" the pattern
- Educational potential for kids

### Arcade Classics (Reimagined)

**17. Space Invaders**
- Rows of targets descending
- Hit to destroy before they reach bottom
- Boss targets that take multiple hits
- Power-ups appear occasionally

**18. Asteroids**
- Large targets split into smaller ones when hit
- Fragments move outward
- Clear all fragments to complete wave

**19. Fruit Ninja Style**
- Targets arc across screen
- Must hit while in motion
- Avoid "bomb" targets
- Combo multipliers for rapid hits

**20. Pong Defense**
- Ball bounces around screen
- Hit targets to score, but ball destroys targets too
- Defensive positioning element

### Skill Building / Training

**21. Accuracy Trainer**
- Structured drills with specific patterns
- Track improvement over sessions
- Adjustable difficulty presets
- Performance analytics

**22. Speed Ladder**
- Progressive difficulty levels
- Must complete level to unlock next
- Leaderboard for each level
- Replay to improve times

**23. Weakness Finder**
- Targets in all screen regions
- Identifies areas where player struggles
- Generates custom practice sessions
- Data-driven improvement

**24. Grouping**
- Target appears at random position on screen
- First hit establishes the group center
- Each subsequent hit shrinks the target circle toward your group centroid
- Target size represents your current spread/grouping
- Miss (hit outside current target) = round ends
- Final score based on smallest achieved group size
- Measures real precision - tighter group = better archer/shooter
- Variants: Timed rounds, multiple group locations, moving group center

**25. Many Random Targets (Field of Targets)**
- Generates a random distribution of non-overlapping targets across the canvas
- All targets visible simultaneously - player clears the field
- Missing any target = negative points (penalty)
- Scoring: hit = +points, miss = -points, remaining targets at end = -points each
- Tests: coverage accuracy, decision-making on target order, avoiding rushed misses
- Variants: Timed rounds, different target sizes, priority targets worth more
- Training value: Encourages deliberate shooting - quality over speed
- Real-world parallel: Clearing a course, archery field rounds

**26. Growing Targets (Speed/Accuracy Tradeoff)**
- Target appears small and grows over time
- Score = inverse of size when hit (smaller = more points)
- Natural speed/accuracy tradeoff - no artificial timer needed
- You CAN wait for easy shot, but rewarded for taking harder one early
- Miss penalty to prevent spray-and-pray
- Tests: confidence in your accuracy, risk assessment, quick acquisition
- Training value: Develops "send it" mentality - trust your skill, don't overthink
- Variants: Multiple growing targets, targets that shrink after peak, random growth rates
- Inspired by: Asteroids - same core mechanic (approaching threat = easier but losing points/time)
  but "growing" fits projected targets better than simulating depth/approach

### 3D / Immersive (Requires 3D Rendering)

**27. Dinosaur Chase (Jurassic Tranquilizer)**
- First-person view from moving vehicle (jeep, train car, boat)
- Procedurally generated terrain scrolling past
- Dinosaurs appear from sides, behind rocks, trees - charge toward you
- Hit them with "tranquilizer darts" before they reach you
- Different dino types: small/fast (raptors), large/slow (T-Rex), flying (pterodactyls)
- Vehicle on rails - player only aims, no driving
- Themes: Jungle, desert canyon, volcanic island
- Power-ups: slow motion, multi-shot, shield

**28. Rail Shooter Classic**
- On-rails movement through environments
- Enemies pop out from cover, windows, doorways
- Boss battles with weak points
- Themes: Haunted house, alien invasion, zombie outbreak, wild west

**29. Turret Defense**
- Stationary turret position (like beach defense)
- Waves of incoming threats (planes, boats, vehicles)
- 3D depth - targets at different distances
- Lead your shots for moving targets
- Ammo management between waves

**30. Safari Photo Hunt**
- Non-violent variant - "shoot" photos instead
- Animals appear briefly in scenic environments
- Rare animals worth more points
- Composition bonus for centered shots
- Educational: animal facts on successful captures

**31. Tunnel Run**
- Flying/driving through tunnel or canyon
- Targets on walls, ceiling, obstacles ahead
- Increasing speed creates urgency
- Dodge obstacles by hitting them first
- Star Fox / Panzer Dragoon inspired

### Side-Scroller / Runner Defense

**32. Trail Blazer (Runner Escort)**
- Side-scrolling runner you're protecting by clearing obstacles
- Runner advances when path is clear, hesitates when blocked - speed reflects your recent hit rate
- Creates natural flow state: clearing consistently = runner speeds up = intensity increases = genuine difficulty curve
- Obstacles spawn at sustainable shooting rhythm (2-3 sec intervals baseline, adjustable)
- Physical archery constraint: limited arrows + retrieval time creates natural burst-clear-retrieve rhythm
- Clear zones (bridges, tunnels) provide retrieval windows and pacing breaks
- Miss consequence options: runner stumbles (time/momentum loss) vs takes damage (health) vs dies (high stakes)
- Obstacle variety: static barriers, approaching threats, priority targets (some more lethal than others)
- Runner has minimal autonomy - can navigate small gaps if cleared, but dependent on you for real obstacles
- Procedural terrain generation with density ramping based on current run performance
- Protective motivation > accumulative motivation: stakes feel visceral, not abstract
- Training value: Decision-making under pressure, triage/prioritization, sustainable rhythm, consequence weight
- Dopamine profile: Flow state when clicking, protective stakes, visible momentum feedback, natural intensity ramping
- **Theme variants** (core mechanic is genre-agnostic):
  - *Military/Action*: Chopper escort protecting convoy, sniper covering squad advance, naval escort through minefield
  - *Classic Arcade*: Donkey Kong barrels (break before they hit Mario), Frogger defense (clear traffic for the frog), Pitfall jungle hazards
  - *Fantasy/Adventure*: Knight escorting princess through monster forest, dragon rider clearing sky, shepherd protecting flock from wolves
  - *Casual/Cute*: Mama duck leading ducklings (clear lily pads of frogs), ice cream truck (clear road so it doesn't melt), school bus route
  - *Abstract*: Pure geometric shapes - no theme, just satisfying flow
- Key insight: Protective stakes create fundamentally different motivation than score accumulation - something bad happens to something you care about if you fail
- Retrieval windows (safe zones/tunnels) become narrative rhythm, not game pauses

**33. Sweet Physics (Cut the Rope Style)
Core Concept:
Physics puzzle game where you cut ropes, pop bubbles, and trigger mechanisms by shooting targets to guide an object (candy/ball/creature) to a goal. Precision + timing + strategy layered together.
Novel Mechanic:
Projectile-based interaction with physics puzzles. Unlike touchscreen swipe (instant, costless), each shot is a commitment with physical constraints. The economy of limited arrows transforms casual puzzling into deliberate decision-making.
Gameplay Loop:

Level presents: suspended object, goal location, obstacles, collectibles (stars)
Player studies physics setup - ropes, bubbles, air cushions, mechanisms
Player shoots targets to trigger physics changes
Object moves according to physics
Success = object reaches goal; bonus = collect stars along the way

Skill Layers (Progressive Depth):

Basic: Get object to goal (completion)
Precision: Collect stars en route (optimization)
Economy: Fewer shots = better score (efficiency, especially meaningful with quiver limits)
Timing: Speed bonus / time pressure variants (flow state)

Physics Elements (Targets You Can Hit):

Ropes: Cut to drop/swing object
Bubbles: Pop to release floating object
Air cushions: Trigger to boost object trajectory
Triggers/buttons: Activate mechanisms (platforms, doors, conveyors)
Bumpers: Change object direction on contact
Portals: Teleport object across level

Archery-Specific Value:

Timing accuracy: Waiting for right moment in swing arc, holding draw
Physical accuracy: Hitting small targets (rope attachment points)
Deliberate shooting: Opposite of reactive - patience rewarded
Economy pressure: 6 arrows, 8 cuts needed = which cuts can wait for retrieval?
Retrieval as puzzle phase: Natural pause to study next sequence

Quiver Constraint as Feature:
Unlike touchscreen where cuts are free, limited arrows mean:

Can't brute force solutions
Each shot is commitment
Star collection has real cost (arrow you can't use elsewhere)
Some levels may require retrieval mid-puzzle (built into design)

Difficulty Axes:

Puzzle complexity: Number of elements, physics interactions
Target size: Larger rope targets (easy) vs small precise trigger points (hard)
Timing windows: Generous swing cycles vs tight timing requirements
Star placement: Easy path vs requiring detour/extra shots
Arrow budget: Generous vs exactly-enough vs requires retrieval planning

Level Design Principles:

Clear visual language for each element type
Multiple solutions possible (emergent, not scripted)
Stars as optional mastery challenges, not completion requirements
Progressive introduction of elements
"Aha moment" potential - realizing a clever sequence

Theme Variants:

Classic: Candy + cute creature (Om Nom style)
Abstract: Geometric shapes, pure physics aesthetic
Nature: Acorn to squirrel, fish through water currents
Spooky: Ghost to haunted house, chains instead of ropes
Rube Goldberg: Elaborate chain reaction emphasis
Holiday: Seasonal theming (present to tree, egg to basket)

Training Value:

Patience and timing (holding draw for right moment)
Strategic thinking (planning sequence before shooting)
Precision under low pressure (deliberate, not reactive)
Economy of action (making each shot count)
Physics intuition (predicting swing arcs, momentum)

Dopamine Profile:

Satisfaction of clean, well-timed cut
Chain reaction joy (one shot triggers cascade)
Puzzle solution "aha" moment
Star collection completionism
Improvement visible through fewer shots / better times

Level Format (YAML-driven like Containment):
yamlname: "Swing and Drop"
difficulty: 2
stars: 3
arrow_budget: 4  # null = unlimited

elements:
  - type: candy
    position: [0.5, 0.2]
    attached_to: [rope_1, rope_2]

  - type: rope
    id: rope_1
    anchor: [0.3, 0.0]
    length: 0.25
    cuttable: true

  - type: rope
    id: rope_2
    anchor: [0.7, 0.0]
    length: 0.2
    cuttable: true

  - type: bubble
    position: [0.5, 0.5]

  - type: star
    position: [0.3, 0.4]

  - type: star
    position: [0.7, 0.4]

  - type: star
    position: [0.5, 0.7]

  - type: goal
    position: [0.5, 0.9]
    radius: 0.08

physics:
  gravity: 9.8
  rope_elasticity: 0.1
  bubble_float_speed: 0.5
Implementation Notes:

Physics engine needed (pymunk or similar)
Rope as segmented physics body with cuttable joints
Clear visual feedback for "what's targetable"
Trajectory preview for object after cut (optional, for easier modes)
Replay system to watch successful solutions

Community Potential:

Level editor (visual or YAML)
Level sharing / curated packs
Community challenges (fewest shots, fastest time)
Theme/asset packs

Comparison to Containment:
AspectContainmentSweet PhysicsPressureReactive, real-timeDeliberate, self-pacedSkill typeTracking + chaos managementTiming + precisionFailure modeBall escapes (sudden)Candy lost (recoverable via retry)Cognitive loadHigh (constant adaptation)Medium (plan then execute)Archery trainingSnap shooting, instinctHeld draw, patience
Both valuable, different modes of engagement.

**34. Love-O-Meter (Carnival Rate Challenge)
Core Concept:
Classic carnival high-striker reimagined. Hit the target repeatedly to fill a thermometer that's constantly draining. Pure speed vs. accuracy under escalating pressure.
The Hook:
Can you shoot fast enough to outpace the drain? The answer is always "barely" - difficulty adapts to keep you at your edge.
Core Loop:

Thermometer starts partially filled (or empty)
Each hit adds to the meter
Meter constantly drains
Fill it completely to win / survive as long as possible
Difficulty escalates: drain increases, target shrinks, target moves

Difficulty Axes (Compound Pressure):
AxisEasyHardTraining EffectDrain rateSlowFastTempo, urgencyTarget sizeLargeSmallPrecision under pressureTarget movementStaticDriftingInstinctive shooting
The axes combine: shrinking target makes you want to slow down, increasing drain punishes slowing down. The tension between impulses is where skill lives.
Movement Speed as Teaching Dial:

Static: Mechanical aiming works, conscious alignment
Slow drift: Can track consciously, but harder
Medium movement: Conscious aiming fails, instinct must emerge
Fast movement: Pure instinct or pure miss

Moving target removes the "aim, hold, verify" crutch - the body must learn to solve the problem without conscious involvement.
Modality Split:
NERF:

Pure chaos energy
Volume compensates for accuracy (until target shrinks)
Dump magazine, reload, dump again
Friends feeding you blasters
Party game, everyone participates
Builds: speed, aggression, comfort with chaos

Archery:

Meditative brutality
No spray option - every arrow must land
Draw cycle is your rate limiter
Drain rate tuned to just exceed comfortable pace
Miss once = feel it immediately
Miss twice = recovery mode
Builds: form under pressure, tempo control, mental resilience

Training Value (Archery):

Economy of motion (wasted movement = lost time)
Consistent anchor (no time to find it, must be automatic)
Smooth draw cycle (jerky = slow)
Recovery after release (next arrow NOW)
Performance under stress (competition simulation)
Instinctive shooting (when target moves)

The Psychological Screw:
The game engineers a state where the analytical mind can't keep up. Target moving + drain pressure = conscious aiming overwhelmed. The body has to take over. That's when instinctive shooting emerges - not as choice but as only viable option.
Biofeedback Loop:
The meter tells you when you're in flow. It climbs when you let go, drops when you tense up and try to control. Visible feedback for an internal state.
Game Modes:
ModeDescriptionSprintFill meter completely, fastest time winsEnduranceKeep meter above threshold, how long can you last?PressureDrain rate increases until inevitable failureAdaptiveDifficulty responds to performance, keeps you at edgeVersusTwo meters, first to fill winsTug-of-WarYour hits drain opponent's meter
Carnival Framing:
The silly theme matters. "Love-O-Meter" is inherently unserious. You can fail and laugh. Lower stakes framing for high-pressure skill development. The training is real, the vibe is play.
Physical Exercise (Hidden Workout):

Repeated draws at real weight (25-50 lb)
Sustained shooting rate = cardio
Core engagement for stability
Shoulder/back/arm fatigue accumulating
Walking retrieval = active rest intervals
30 minutes of love-o-meter = real workout

Range Etiquette:

Sound via earbuds (private feedback, no noise pollution)
Visual spectacle draws curiosity without imposing
Normal retrieval rhythm (designed around it)
Standard safety protocols unchanged

Visual Design:

Thermometer/meter as central UI element
Target clearly visible with current size indicated
Movement path subtle or invisible (don't aid prediction)
Hit feedback: satisfying pulse on meter rise
Miss feedback: meter drop emphasized
Near-fail state: visual urgency (pulsing, color shift)

YAML Configuration:
yamlname: "Love-O-Meter"
mode: adaptive  # sprint | endurance | pressure | adaptive

meter:
  initial_fill: 0.3
  drain_rate: 0.05  # per second, base rate
  fill_per_hit: 0.08
  win_threshold: 1.0  # fill completely to win

target:
  initial_size: 120  # pixels radius
  minimum_size: 30
  shrink_rate: 0.5  # pixels per second
  movement:
    enabled: true
    speed: 50  # pixels per second
    pattern: drift  # drift | orbit | random | bounce

difficulty:
  adaptive: true
  drain_increase_rate: 0.002  # per second
  shrink_increase_rate: 0.1  # per second
  
pacing:
  archery:
    meter.drain_rate: 0.03
    target.initial_size: 150
    target.movement.speed: 30
  nerf:
    meter.drain_rate: 0.12
    target.initial_size: 100
    target.movement.speed: 80
Success Metrics:

 "One more try" compulsion
 Visible improvement across sessions
 Flow state achievable (meter climbing steadily)
 Failure feels fair ("I missed" not "game cheated")
 Physical tiredness after extended play
 NERF version causes party chaos
 Archery version builds competition readiness

Comparison to Other Games:
AspectContainmentSweet PhysicsLove-O-MeterPressure typeSpatialStrategicTemporalPacingReactiveDeliberateRelentlessThinkingAdaptivePlanningNone (flow)Physical demandModerateLowHighParty energyHighLowVery highArchery trainingSnap shootingPatienceTempo/form

---

### Multiplayer / Social

**35. Hot Potato**
- Target bounces between players
- Must hit within time limit
- Last player standing wins
- Works with turn-taking for single input

**36. Score Attack**
- Same targets for all players
- Highest score in time limit wins
- Can be async (take turns, compare scores)

**37. Cooperative Survival**
- Targets require multiple hits
- Players work together
- Shared health/lives
- Communication required

---

### Adversarial / Containment

**38. Containment (Working Title)**

Adversarial containment game. A ball/entity tries to escape the play area through gaps at edges. Player places deflectors (arrows/touches/clicks) to build walls and seal escape routes. Direct hits on the ball are penalized - it accelerates. You're building geometry to contain, not targeting to destroy.

**Novel Mechanic:**
- Precision placement while avoiding a moving exclusion zone
- Tracking to *not* hit while placing accurate shots nearby
- Real-time level editing under adversarial pressure

**Input Agnostic:**
- Same game across touch, mouse, laser, archery
- Input method determines precision variance and physical cost, but core loop is identical
- Imprecision from any source becomes part of the challenge - adapting to your own errors

**Difficulty Axes (Independent):**

*Tempo:*
- Zen: Slow ball, few gaps, meditative geometry-building
- Mid: Pressure demands attention, mistakes recoverable
- Wild: Fast ball, multiple balls, dynamic gap spawning, panic management

*AI Sophistication:*
- Dumb: Pure physics, predictable bounces
- Reactive: Seeks gaps, avoids dense geometry, opportunistic
- Strategic: Learns placement patterns, baits wasted shots, exploits retrieval windows, reads player

**Core Loop:**
1. Ball spawns, begins bouncing
2. Gaps exist or open at edges
3. Player places deflectors to seal gaps and shape bounce paths
4. Ball probes geometry, seeks escape
5. Direct ball hits = speed increase (punishment for sloppy/rushed shots)
6. Win: Containment achieved (ball trapped or survived X time)
7. Lose: Ball escapes through gap

**Emergent Properties:**
- Early playfield is sparse, simple paths
- Accumulated deflectors create complex bounce mazes
- Unintended combos from geometry you placed earlier
- "Didn't plan that but it worked" moments
- Panic spiral: rushing → accidental hits → faster ball → more panic → earned loss

**Deflector Mechanics:**
- Placed permanently where shot lands
- Limited count (physical arrows) or unlimited (touch/mouse) - tunable
- Retrieval/removal creates temporary vulnerability
- Placement accuracy matters for future bounce behavior
- Imperfect placement = adapting to your own geometry errors

**Skill Stack:**
1. Immediate accuracy (hit where you aimed)
2. Exclusion zone tracking (avoid the ball while shooting near it)
3. Placement strategy (where creates future value)
4. Emergent physics reading (predict ball through your geometry)
5. AI theory of mind (what does it think I'll do) - higher difficulty only

**Theming Options:**
- Abstract: Ball and lines, pure geometry
- Containment: Alien spacecraft, escaped entity, quarantine breach
- Playful: Catch the critter, keep the pet contained
- Physics toy: Zen mode as screensaver/fidget experience

**Win/Scoring:**
- Time survived
- Bounce count while contained
- Deflector efficiency (fewer = better)
- Escape margin (how close ball got to gaps)
- Style points for interesting bounce chains (optional)

**Cognitive Profile:**
Strong flavor - appeals to architectures comfortable with emergent chaos, improvisation, adapting to evolving systems. May frustrate those needing predictable cause-effect and time to plan. Zen mode offers accessible on-ramp.

**Training Value:**
- Precision under pressure
- Predictive tracking
- Strategic vs reactive thinking
- Handling panic / arousal management
- Adapting to own errors

**Implementation Notes:**
- Standard game protocol (handle_input, update, render, state, get_score)
- Ball physics: basic reflection with optional spin/curve at higher difficulties
- Gap system: static positions initially, dynamic spawning for higher difficulty
- AI behavior: state machine or simple utility-based decision making
- Deflector rendering: line segments or arrow shapes at impact points
- Collision detection: ball-deflector, ball-edge, ball-gap
- Developer mode: mouse/touch input for rapid iteration before archery integration

---

## Evaluation Criteria

When selecting games to implement:

| Criterion | Weight | Notes |
|-----------|--------|-------|
| Fun Factor | High | Is it engaging? Would you play it repeatedly? |
| Skill Expression | High | Does improving skill show in scores? |
| Implementation Complexity | Medium | Can we build it quickly? |
| Replayability | High | Does it stay fresh? |
| Hardware Agnostic | Must Have | Works with all detection backends |
| Variable Practice | Must Have | Avoids repetitive patterns |

---

## Top Candidates for Next Implementation

*To be filled in after discussion*

1.
2.
3.

---

## Notes

- All games should support the standard game protocol (handle_input, update, render, state, get_score)
- Consider adding difficulty settings to make games accessible
- Sound effects and visual feedback are crucial for game feel
- Keep scope small for initial versions - can always add features later
