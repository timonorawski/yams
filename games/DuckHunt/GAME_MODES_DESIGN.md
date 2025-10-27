# Game Modes & Level Progression Design

## Project Context: Reference Implementation for ArcheryGame Platform

**This Duck Hunt game is a showcase application built on the ArcheryGame platform.**

### The Broader ArcheryGame Platform

The parent project provides universal infrastructure for **projected interactive targeting games**:

**Platform Components:**
1. **Calibration System**: Maps projector space ↔ camera space (use-case agnostic)
2. **Impact Detection**: Detects projectile impacts (balls, arrows, laser pointers, etc.)
3. **Input Abstraction**: Unified coordinate-based input (physical OR virtual)

**Use Cases the Platform Enables:**
- 🏫 **Physical Education**: Project onto gym wall, detect ball impacts
- 🎯 **Archery Instruction**: Project onto archery targets, detect arrow impacts
- 🏠 **Home Gaming**: Laser pointer at TV, webcam detects laser dot
- 🎪 **Event Entertainment**: Large-scale projected games at parties/events
- 🏥 **Physical Therapy**: Gamified movement exercises with impact tracking

### Duck Hunt as Reference Implementation

**This game demonstrates:**
- ✅ How to build on the ArcheryGame platform
- ✅ Clean input abstraction (works with mouse, laser pointer, OR impact detection)
- ✅ Data-driven game modes (YAML configuration)
- ✅ Theme/presentation separation (JSON themes)
- ✅ Pluggable trajectory algorithms
- ✅ Community modding architecture
- ✅ Professional game design patterns

**Goal:** Show developers how to create their own games on the platform, and show community members how to create modes/themes without coding.

**Vision:**
- Platform maintainers focus on calibration & detection
- Game developers create diverse applications (Duck Hunt, Fruit Ninja, Basketball, etc.)
- Community creates modes, themes, and variations
- Educational institutions customize for their specific needs
- Everyone benefits from improved detection/calibration

### Why This Architecture Matters

**For the Platform:**
- Duck Hunt proves the input abstraction works
- Demonstrates that one detection system serves many games
- Shows feasibility of community-driven content

**For Game Developers:**
- Reference implementation showing best practices
- Reusable patterns (trajectory systems, theming, modes)
- Example of data-driven design (YAML/JSON configs)

**For Community:**
- Create modes/themes without touching code
- Share content across installations
- Customize for local needs (PE teachers, archery clubs, etc.)

**For End Users:**
- Physical activity through gameplay
- Works with whatever equipment they have (balls, arrows, laser pointer)
- Community creates endless content variety

---

## Other Example Games (Future)

**The platform will provide multiple example games to demonstrate different interaction patterns:**

### 1. Duck Hunt (This Game) - Trajectory-Based Targeting
- Moving targets with 3D ballistic arcs
- Demonstrates: trajectory algorithms, depth simulation, timing challenges
- Best for: reflex training, prediction skills

### 2. Paint - Continuous Drawing
**Concept:** Interactive drawing application using impact points

**Gameplay:**
- Project a canvas on the screen
- Color palette displayed at bottom/sides
- Users hit points on screen to draw
- Each impact creates a colored mark
- Hit palette to change active color
- Drawing persists on screen

**Drawing Modes:**
- **Point Mode**: Each impact = single point
- **Line Mode**: Impacts connected by lines
- **Spray Mode**: Each impact = spray radius with color blur
- **Fill Mode**: Hit enclosed area to flood fill

**Features:**
- Brush size selector (small/medium/large circles on screen)
- Eraser (special palette color)
- Clear canvas (special button area)
- Save drawing (screenshot)
- Color gradient/blur effects

**Educational Use:**
- Art classes: collaborative drawing on wall
- PE: active art creation (moving to reach different areas)
- Special needs: large-scale, engaging drawing interface
- Team building: collaborative art projects

**Implementation Demonstrates:**
- Continuous state (drawing accumulation)
- UI interaction patterns (palette selection)
- Different input interpretation (drawing vs. targeting)
- Persistence of user actions

### 3. Fruit Ninja - Slicing Trajectories
- Fruit flies through screen
- User must "slice" through fruit path
- Demonstrates: gesture detection, trajectory intersection

### 4. Whack-a-Mole - Stationary Timing
- Targets appear/disappear at fixed positions
- Demonstrates: timing challenges, spatial memory

### 5. Simon Says - Sequence Memory
- Display sequence of highlighted targets
- User must repeat sequence
- Demonstrates: memory training, sequence input

### 6. Basketball - Physics Simulation
- Score by hitting moving/stationary hoops
- Different point values for different hoops
- Demonstrates: sports training, accuracy drills

### 7. Rhythm Game - Musical Timing
- Hit targets in sync with music beat
- Demonstrates: rhythm training, audio-visual sync

---

## Game Development Template (Future)

**For developers who want to create entirely new games:**

The platform will provide a **base game skeleton** that abstracts common patterns:

```python
# games/template/game_template.py

from archery_game import BaseGame, InputManager, Renderer

class MyCustomGame(BaseGame):
    """Template for creating new games on ArcheryGame platform."""

    def __init__(self, config_path: str):
        super().__init__()
        self.config = self.load_config(config_path)
        self.input_manager = InputManager()  # Platform provides this
        self.renderer = Renderer()            # Platform provides this

    def setup(self):
        """Initialize game-specific state."""
        pass

    def update(self, dt: float):
        """Update game logic each frame."""
        pass

    def handle_input(self, events: List[InputEvent]):
        """Process input events from platform."""
        pass

    def render(self, screen):
        """Render game visuals."""
        pass

    def on_game_start(self):
        """Called when game starts."""
        pass

    def on_game_end(self):
        """Called when game ends."""
        pass
```

**What the Platform Provides:**
- ✅ Input abstraction (mouse, laser, impact detection)
- ✅ Calibration system (projector ↔ camera mapping)
- ✅ Rendering utilities (pygame wrapper)
- ✅ Audio management
- ✅ Configuration loading (YAML/JSON)
- ✅ Menu system (start, pause, settings)
- ✅ Save/load functionality
- ✅ Logging and error handling

**What Developers Implement:**
- Game-specific logic (targets, rules, scoring)
- Visual presentation (sprites, backgrounds)
- Sound effects and music
- Game modes and levels
- Custom input interpretation (if needed)

**Example: Minimal Paint Game Implementation**

```python
# games/paint/paint_game.py

class PaintGame(BaseGame):
    """Simple paint application."""

    def __init__(self):
        super().__init__()
        self.canvas = pygame.Surface((800, 600))
        self.canvas.fill((255, 255, 255))  # White canvas
        self.current_color = (0, 0, 0)     # Black
        self.palette = self._create_palette()

    def _create_palette(self):
        """Create color palette at bottom of screen."""
        return [
            {"color": (255, 0, 0), "rect": pygame.Rect(50, 550, 50, 50)},
            {"color": (0, 255, 0), "rect": pygame.Rect(110, 550, 50, 50)},
            {"color": (0, 0, 255), "rect": pygame.Rect(170, 550, 50, 50)},
            # ... more colors
        ]

    def handle_input(self, events: List[InputEvent]):
        """Handle drawing and palette selection."""
        for event in events:
            pos = (int(event.position.x), int(event.position.y))

            # Check if palette was clicked
            for color_box in self.palette:
                if color_box["rect"].collidepoint(pos):
                    self.current_color = color_box["color"]
                    return

            # Otherwise, draw on canvas
            pygame.draw.circle(self.canvas, self.current_color, pos, 10)

    def render(self, screen):
        """Render canvas and palette."""
        screen.blit(self.canvas, (0, 0))

        # Draw palette
        for color_box in self.palette:
            pygame.draw.rect(screen, color_box["color"], color_box["rect"])
            pygame.draw.rect(screen, (0, 0, 0), color_box["rect"], 2)  # Border
```

**Educational Use Cases:**

**High School Computer Science:**
- Start with template skeleton
- Students implement game logic step-by-step
- Engaging project (interactive, visual, physical)
- Teaches: game loops, state management, event handling, geometry
- Progressive complexity (start simple, add features)

**Example Lesson Plan:**
1. Week 1: Understand template, implement stationary target
2. Week 2: Add scoring system
3. Week 3: Add multiple targets
4. Week 4: Add visual/audio feedback
5. Week 5: Implement levels and progression
6. Week 6: Polish and present to class

**Student Projects Could Include:**
- Math Practice: Hit targets with correct answers
- Spelling Game: Hit letters to spell words
- Geography: Hit countries/capitals on map
- Science Quiz: Hit correct answers to displayed questions
- Custom Sports Training: Specific drills for their sport

---

## Architectural Extraction Strategy

**Critical Development Principle: Build to Extract**

Duck Hunt is being developed as **both a working game AND a prototype for platform abstractions**. As we implement features, we continuously identify patterns that should be extracted into the shared game development library.

### Development Process

**Phase 1: Build Duck Hunt (Current)**
- Implement all features directly in Duck Hunt codebase
- Focus on making it work and play well
- Document patterns as they emerge
- Identify reusable vs. game-specific code

**Phase 2: Extract Shared Library (Future)**
- Refactor common patterns into `archery_game_lib/`
- Duck Hunt becomes a reference implementation using the library
- Other games use the same abstractions
- Library evolves based on multiple game needs

### Extraction Candidates (Identified During Development)

As we build Duck Hunt, these patterns are emerging as library candidates:

#### 1. **Trajectory System** (High Priority)
```python
# archery_game_lib/trajectory/
├── base.py              # TrajectoryAlgorithm protocol
├── registry.py          # Algorithm registry and discovery
├── algorithms/
│   ├── linear.py
│   ├── bezier_2d.py
│   ├── bezier_3d.py
│   └── physics.py
└── depth_simulation.py  # 3D projection utilities
```

**Why Extract:**
- Multiple games need moving objects (Fruit Ninja, Basketball, etc.)
- Trajectory algorithms are game-agnostic
- 3D depth simulation is reusable
- Algorithm swapping is universally useful

**Duck Hunt Usage:**
```python
from archery_game_lib.trajectory import TrajectoryRegistry, DepthSimulator

# Duck Hunt uses library abstractions
trajectory_algo = TrajectoryRegistry.get("bezier_3d")
trajectory = trajectory_algo.generate(config)
```

#### 2. **Data-Driven Configuration System** (High Priority)
```python
# archery_game_lib/config/
├── loader.py            # YAML/JSON loading with validation
├── models.py            # Base Pydantic models for configs
└── validators.py        # Common validation utilities
```

**Why Extract:**
- Every game benefits from YAML configuration
- Pydantic validation should be standardized
- Mode/theme loading is universal pattern

**Duck Hunt Usage:**
```python
from archery_game_lib.config import ConfigLoader, GameModeConfig

loader = ConfigLoader()
mode_config = loader.load_mode("classic_ducks")  # Validates with Pydantic
```

#### 3. **Theme/Presentation System** (High Priority)
```python
# archery_game_lib/theming/
├── theme_manager.py     # Theme loading and discovery
├── renderer.py          # Rendering utilities (sprites, backgrounds)
├── audio.py             # Sound effect and music management
└── particles.py         # Particle effect system
```

**Why Extract:**
- All games need themes/visual customization
- Sprite/audio management is boilerplate
- Community modding requires standard theme format

**Duck Hunt Usage:**
```python
from archery_game_lib.theming import ThemeManager, ParticleSystem

theme = ThemeManager.load("classic_ducks")
particles = ParticleSystem()
particles.emit("feathers", position=(100, 200))
```

#### 4. **UI Components** (Medium Priority)
```python
# archery_game_lib/ui/
├── menu.py              # Menu systems (start, pause, settings)
├── hud.py               # HUD elements (score, timer, etc.)
├── dialogs.py           # Modal dialogs and popups
└── widgets.py           # Buttons, sliders, selectors
```

**Why Extract:**
- Standard UI patterns across games
- Consistency improves user experience
- Reduces boilerplate for game developers

#### 5. **Game State Machine** (Medium Priority)
```python
# archery_game_lib/state/
├── game_state.py        # Base state machine
├── transitions.py       # State transition utilities
└── save_load.py         # Save/load functionality
```

**Why Extract:**
- All games have states (menu, playing, paused, game over)
- State transitions are consistent pattern
- Save/load is universal need

#### 6. **Scoring and Feedback** (Medium Priority)
```python
# archery_game_lib/feedback/
├── scoring.py           # Base scoring systems
├── visual_effects.py    # Hit effects, explosions, etc.
├── audio_feedback.py    # Procedural sound generation
└── combo.py             # Combo/streak tracking
```

**Why Extract:**
- Most games need scoring
- Visual/audio feedback patterns are similar
- Combo systems are common mechanic

### Extraction Criteria

**Extract when:**
- ✅ Used by 2+ games (or obviously will be)
- ✅ Game-agnostic (no Duck Hunt-specific logic)
- ✅ Well-tested and stable
- ✅ Clear interface/protocol defined
- ✅ Benefits from centralized maintenance

**Don't Extract when:**
- ❌ Only used by Duck Hunt
- ❌ Still experimental/changing rapidly
- ❌ Tightly coupled to Duck Hunt specifics
- ❌ Simple enough to reimplement per-game

### Refactoring Strategy

**Step 1: Identify Pattern**
- Notice repeated code or reusable abstraction
- Document the pattern and its use cases
- Consider how other games would use it

**Step 2: Stabilize in Duck Hunt**
- Implement fully in Duck Hunt first
- Test thoroughly
- Iterate until API feels right

**Step 3: Extract to Library**
- Move code to `archery_game_lib/`
- Create clean public interface
- Write comprehensive tests
- Document for other developers

**Step 4: Refactor Duck Hunt**
- Update Duck Hunt to use library version
- Ensure Duck Hunt still works identically
- Becomes reference example of library usage

**Step 5: Validate with Second Game**
- Implement another game (Paint, Fruit Ninja)
- Test if library abstractions work well
- Refine library based on multi-game needs

### Benefits of This Approach

**For Duck Hunt Development:**
- ✅ Focus on game logic, not infrastructure
- ✅ Faster iteration (no premature abstraction)
- ✅ Real-world testing before extraction

**For Platform:**
- ✅ Abstractions based on actual usage
- ✅ Avoids over-engineering
- ✅ Library shaped by real game needs

**For Future Games:**
- ✅ Proven patterns from Duck Hunt
- ✅ Less boilerplate to write
- ✅ Consistent APIs across games
- ✅ Reference implementation to learn from

**For Community:**
- ✅ Lower barrier to entry (use library)
- ✅ Focus on creative aspects, not plumbing
- ✅ Consistent modding interfaces

### Duck Hunt's Dual Role

**As a Game:**
- Engaging gameplay
- Multiple modes and themes
- Polished user experience
- Fun to play

**As a Reference Implementation:**
- Demonstrates library patterns
- Shows best practices
- Proves platform capabilities
- Template for other games

**Both roles inform each other:**
- Good game design reveals good abstractions
- Good abstractions enable better games
- Duck Hunt validates library design
- Library amplifies Duck Hunt's impact

---

### Future External Integrations (Arcade Management Layer)

Beyond the platform and game library, there's an outer **arcade management system** that handles deployment concerns:

**Four-Layer Architecture:**

```
┌─────────────────────────────────────────────────┐
│  Arcade Management System (Outer Layer)         │
│  - User identification (NFC/RFID)               │
│  - Game selection menu                          │
│  - Hardware management (buttons, coin slots)    │
│  - Admin interface (stats, settings)            │
│  - Payment processing                           │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  ArcheryGame Platform (Core Infrastructure)     │
│  - Calibration system                           │
│  - Impact detection                             │
│  - Input abstraction                            │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  Game Library (Shared Abstractions)             │
│  - Trajectory systems                           │
│  - Config loading                               │
│  - Theme management                             │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  Games (Duck Hunt, Paint, Fruit Ninja, etc.)    │
│  - Game-specific logic and content              │
└─────────────────────────────────────────────────┘
```

**Arcade Management System (Outer Layer):**

This is a separate component that sits above everything else and handles:

**1. User Identification & Profiles:**
- **NFC/RFID readers**: Tap card to load player profile
- **QR codes**: Scan phone to identify user
- **Biometrics**: Fingerprint/face recognition (privacy considerations)
- Profile storage across all games

**2. Game Selection Interface:**
- Visual menu showing available games
- Thumbnails and descriptions
- "Coming attractions" for new games
- Recently played games
- Favorites/bookmarks

**3. Hardware Management:**
- **Custom arcade cabinets**: Buttons, joysticks, coin slots
- **COTS hardware**: Off-the-shelf controllers, payment systems
- Input mapping to platform abstraction
- Hardware diagnostics and monitoring

**4. Admin Management Software:**
- **Operator interface**: Configure games, view stats, manage users
- **Analytics dashboard**: Usage patterns, popular games, revenue
- **Content management**: Install/remove games, update themes
- **Maintenance tools**: Calibration wizards, hardware testing

**5. Payment Processing:**
- **Coin acceptors**: Traditional arcade tokens/quarters
- **Card readers**: Credit/debit payments
- **Mobile payments**: QR codes, NFC payments
- **Subscription models**: Monthly memberships
- **Free play modes**: For schools, therapy centers

**Example Deployment Scenarios:**

**School Gymnasium:**
```
Arcade Management System (No payment, student IDs)
    ↓
ArcheryGame Platform (Ball impact detection)
    ↓
Games: Basketball drills, dodgeball target practice
```

**Commercial Arcade:**
```
Arcade Management System (Coin slots, player cards with NFC)
    ↓
ArcheryGame Platform (Multiple setups: balls, laser pointers)
    ↓
Games: Duck Hunt, Paint, Basketball, various competitive games
```

**Home Setup:**
```
Simple launcher (No management system needed)
    ↓
ArcheryGame Platform (Laser pointer at TV)
    ↓
Games: Personal favorites
```

**Physical Therapy Center:**
```
Arcade Management System (Patient identification, progress tracking)
    ↓
ArcheryGame Platform (Adaptive input devices)
    ↓
Games: Therapeutic exercises disguised as games
```

**Separation of Concerns:**

- **Arcade Management** → User/hardware/payment/admin (outer deployment layer)
- **Platform** → Calibration/detection/input (core infrastructure)
- **Game Library** → Shared patterns (reusable abstractions)
- **Games** → Gameplay and content (what players interact with)

**Why This Matters:**

**Games remain simple and isolated:**
```python
# Duck Hunt receives minimal player info, returns scores/saves
def main(player_display: PlayerDisplay, save_data: dict):
    """
    Args:
        player_display: Name and avatar for UI display only
        save_data: Previous save state to restore (if any)

    Returns:
        GameResult: Final score, achievements, updated save data
    """
    config = load_config("classic_ducks.yaml")
    game = DuckHunt(config, player_name=player_display.name, avatar=player_display.avatar)

    if save_data:
        game.load_state(save_data)

    result = game.run()  # Play the game

    # Return results to Arcade Management Layer
    return GameResult(
        score=result.score,
        achievements=result.achievements,
        save_data=game.get_save_state(),
        play_duration=result.duration
    )
```

**Clean API Boundary:**

**Input from AML → Game:**
- `PlayerDisplay`: Name and avatar URL (for rendering "Player: John" in UI)
- `save_data`: Opaque dict to restore game state (game's format, AML just stores it)

**Output from Game → AML:**
- `score`: Final score for leaderboards
- `achievements`: List of achievements earned this session
- `save_data`: Updated save state (opaque to AML, just store it)
- `play_duration`: How long the session lasted (for analytics)

**What Games DON'T know about:**
- ❌ User authentication (NFC cards, passwords, etc.)
- ❌ Where save data is stored (database, files, cloud)
- ❌ Payment processing or credits
- ❌ Cross-game profiles or global achievements
- ❌ Hardware management (coin slots, buttons)

**What AML handles:**
- ✅ User identification (NFC, QR, biometrics)
- ✅ Save data persistence (per user, per game)
- ✅ Leaderboards and cross-game statistics
- ✅ Payment/credit tracking
- ✅ Game launching and switching

**Platform remains focused:**
- Calibration and detection
- Input abstraction
- No business logic, no user management

**Management system handles complexity:**
- Multiple games, multiple users
- Hardware variations (buttons, coin slots, NFC)
- Business concerns (payments, analytics)
- Profile storage and retrieval
- Can be custom-built or COTS solution

**Implementation Options:**

**Option 1: Custom Management System**
- Build tailored to specific deployment
- Full control over features
- Can integrate with existing systems (school IDs, etc.)

**Option 2: COTS Arcade Management Software**
- Off-the-shelf solution (like existing arcade management platforms)
- Plug in ArcheryGame platform as game backend
- Faster deployment, less development

**Option 3: Minimal Launcher (Home Use)**
- Simple game selection menu
- No user management or payments
- Direct to platform and games

This keeps Duck Hunt focused on being a great game while enabling powerful arcade-style deployments at the management layer.

---

## Design Philosophy

**Core Principle**: Variable practice over repetition
- Each attempt should be a fresh problem (different position, timing, decision)
- Build adaptable skill rather than context-dependent muscle memory
- Progressive difficulty that challenges multiple skill dimensions

**From Parent Project Philosophy**:
> Variable practice over repetition—each attempt should be a fresh problem (different position, timing, decision) to build adaptable skill rather than context-dependent muscle memory.

---

## Current Implementation

### Classic Mode (✅ Implemented - LINEAR VERSION)

**Current Status: SIMPLIFIED IMPLEMENTATION**

The current Classic Mode uses **straight horizontal movement**, which is simpler but less engaging than the original Duck Hunt.

**Current Behavior:**
- Targets spawn from screen edges (left or right) at random Y positions
- **LINEAR horizontal movement across screen** (not curved like original Duck Hunt!)
- Speed increases with each successful hit
- Escaped targets count as misses
- Combo system rewards consecutive hits

**Difficulty Progression:**
- Linear speed increase: +10 px/s per hit
- Speed cap: 300 px/s maximum
- No target size changes
- Spawn rate: 2.0 seconds between spawns
- Max active targets: 5 simultaneous

**⚠️ NEEDS ENHANCEMENT:**
The original Duck Hunt's engagement came from **non-linear, curving flight paths**. Birds would arc, swoop, and fly in parabolic trajectories - not straight lines. This made them harder to track and more satisfying to hit.

**Recommended Update:**
Classic Mode should be upgraded to use curved trajectories by default:
- Parabolic arcs (like original Duck Hunt birds)
- Variable apex heights
- Swooping and rising patterns
- Unpredictable curves

This makes straight-line movement the "tutorial" difficulty, with curves being the standard gameplay.

---

## Proposed Enhancements

### 1. Classic Mode Enhancement: Curved Flight Paths (🎯 HIGH PRIORITY)

**Purpose**: Restore the engagement factor of the original Duck Hunt with non-linear trajectories

**Problem:**
Current Classic Mode uses straight horizontal lines, which is:
- Less engaging than the original Duck Hunt
- Easier to track and predict
- Doesn't train spatial prediction skills
- Monotonous - every target behaves the same way

**Solution - Add Curved Trajectories:**
Like the original SNES Duck Hunt, targets should fly in **parabolic arcs** that vary each time:

**Trajectory Generation:**
- Each target gets:
  - **Random starting position** (random side of FOV, random height)
  - **Random ending position** (opposite side, random height)
  - **Random apex position** (anywhere in FOV - creates unique arc shape)
  - **Speed multiplier** (variable speeds: 0.5x - 3.0x)
- Parabolic path calculated using **quadratic Bezier curves**:
  - Three control points: start → apex → end
  - Parameter t (0 to 1) controls position along arc
  - Velocity calculated as derivative of curve
  - Each trajectory is unique

**Difficulty Progression:**
```
Level 1: Slow, shallow arcs (easy to track) - 2s flight time
Level 2: Medium speed, more variance in arc shape - 1.5s
Level 3: Faster arcs, apex can be ±20% off predicted
Level 4: Variable speeds (0.7x-1.3x), apex ±30% variance
Level 5: Fast arcs, ±40% variance, smaller targets
Level 6: Very fast, steep arcs, 2 simultaneous
Level 7+: Multiple speeds, 3-4 simultaneous, extreme variance
```

**Benefits:**
- ✅ Matches original Duck Hunt engagement
- ✅ Variable practice - each target unique
- ✅ Trains prediction skills
- ✅ More visually interesting
- ✅ Prepares for real ballistic projectiles
- ✅ Maintains same code architecture (just changes movement calculation)

**🧠 Evolutionary Psychology - Why Arcs Are Engaging:**
- **Humans are evolutionarily programmed to track ballistic arcs**
- Our ancestors survived by:
  - Throwing spears and rocks (understanding projectile motion)
  - Tracking birds and flying prey
  - Predicting where objects will land
  - Intercepting moving targets
- Games that leverage this instinct are inherently satisfying:
  - **Duck Hunt** - tracking arcing birds
  - **Fruit Ninja** - predicting fruit trajectories
  - **Angry Birds** - calculating ballistic paths
  - **Basketball/Baseball** - intercepting arcing balls
- Straight-line motion doesn't engage this primal tracking system
- Curved trajectories tap into deep-seated spatial prediction abilities
- This is why ballistic arcs feel "right" - they align with millions of years of evolution

**This is not just a game mechanic - it's leveraging fundamental human neurology.**

**Audio Cues (Like Original Duck Hunt):**
The original game had an important mechanic: **audio indicators for target spawning**
- Play "quack" or "flutter" sound when target spawns
- Alerts player that a new target appeared
- Helps locate target without constant visual scanning
- Adds urgency and atmosphere
- Gameplay loop: Hear spawn → Locate target → Track → Shoot

This is already supported by our FeedbackManager's audio system!

**Visual Enhancements (Authenticity & Engagement):**

The original Duck Hunt wasn't just moving circles on a blank screen - it had visual depth and atmosphere:

**1. Background Scenes**
- Outdoor environment (forest, field, pond)
- Creates context and immersion
- Makes tracking feel like actual hunting
- Static background - doesn't distract from targets
- Examples: trees in distance, sky gradient, grass field

**2. Foreground Obstacles**
- **Trees, bushes, grass in front of targets** (key feature!)
- Targets disappear BEHIND obstacles (occlusion)
- Adds visual complexity to tracking
- Forces player to predict trajectory through occlusion
- Increases engagement - can't just stare at one spot
- Implementation: Render targets, THEN render foreground layer with alpha/transparency

**3. 3D Depth Simulation (2D Projection of 3D Arc)** 🎯
**This is a critical realism mechanism!**

The original Duck Hunt simulated **3D ballistic motion projected onto a 2D screen**:

- **Not just size scaling** - it's simulating actual depth (Z-axis distance)
- Targets fly in 3D space, but we only see the 2D projection
- As targets get farther away:
  - **Size decreases** (perspective scaling)
  - **Horizontal speed decreases** (angular velocity decreases with distance)
  - **Both scale together** to simulate real 3D depth

**This is why it felt so natural** - it matched real-world physics of watching flying objects!

**3D Projection Formula:**
```python
# t = progress through trajectory (0.0 at spawn → 1.0 at end)
# Simulate increasing distance from player (Z-axis)
distance_factor = 1.0 + (t * depth_multiplier)  # e.g., 1.0 → 3.0 (3x farther)

# Perspective scaling - size decreases with distance
current_size = initial_size / distance_factor

# Angular velocity - horizontal speed decreases with distance
# Object at same 3D speed appears slower when farther away
horizontal_speed = base_horizontal_speed / distance_factor

# Example: depth_multiplier = 2.0 means target ends 3x farther than it started
# - Size: 60px → 20px (1/3 size)
# - Speed: 300px/s → 100px/s (1/3 speed)
# This simulates flying from close to far
```

**What This Simulates:**
- Bird/duck flying in a 3D parabolic arc **away from the player**
- Starts close (large, moves fast across field of view)
- Ends far (small, moves slowly across field of view)
- Matches real physics: distant objects have lower angular velocity
- **Adaptive difficulty is a side effect of realistic physics!**

**Psychological Impact:**
- **Urgency**: "Shoot before it gets too far away!"
- **Risk/Reward**: Shoot now (large, fast) vs. wait (small, slow)
- **Natural realism**: Matches lifetime experience watching birds, thrown objects
- **Depth perception training**: Useful for real projectile sports
- **Evolutionary cues**: Prey escaping into distance = decreasing chance of success

**Why These Visual Elements Matter:**
- Creates **context** for the prediction task (not abstract circles)
- Adds **spatial reasoning** with occlusion (predict where target reappears)
- Provides **adaptive challenge** without artificial speed increases
- Leverages **depth perception** instincts
- Makes the game feel like **actual hunting**, not just a clicking exercise

**Implementation:**
- Add `calculate_bezier_position(t, start, apex, end)` helper function
- Replace linear velocity with curve-following logic
- Update `Target.update()` to advance along curve (parameter t)
- **Add `current_size` property based on trajectory progress (t)**
- Add `play_spawn_sound()` when target spawns in ClassicMode
- Add apex bonus scoring for hitting at peak of arc
- Store curve parameters in TargetData (or new BezierTarget class)
- **Render pipeline: Background → Targets → Foreground (with occlusion)**
- Add configurable `shrink_factor` per difficulty level

**Priority:** This should be implemented BEFORE adding new game modes, as it makes the core game much more engaging.

---

## Additional Game Modes

### 2. Incoming Mode (Asteroids-Style) (💡 New Concept)

**Purpose**: Threat response and urgency training

**Core Mechanic**: Inverse of Classic Mode - targets fly **TOWARD the player** instead of away

**3D Depth Simulation (Reversed):**
```python
# t = progress through trajectory (0.0 at spawn → 1.0 at impact)
# Simulate DECREASING distance from player (approaching)
distance_factor = 3.0 - (t * 2.0)  # e.g., 3.0 → 1.0 (gets 3x closer)

# Perspective scaling - size INCREASES as it approaches
current_size = initial_size / distance_factor

# Angular velocity - horizontal speed INCREASES as it approaches
horizontal_speed = base_horizontal_speed / distance_factor

# Example: Starts at distance_factor=3.0, ends at distance_factor=1.0
# - Size: 20px → 60px (3x larger)
# - Speed: 100px/s → 300px/s (3x faster)
# This simulates flying from far to close
```

**Gameplay:**
- Targets spawn at edge of screen (far away, small, slow)
- Targets grow larger and move faster as they approach
- Must be hit before reaching threshold (too close = miss/damage)
- Different psychological pressure: **threat approaching** vs. prey escaping
- Useful training for reactive defense scenarios

**Trajectory Options:**
- **Linear (Classic Asteroids)**: Straight-line approach
  - Set trajectory curvature parameter to 0
  - Objects fly directly toward player position
  - Simpler prediction, focus on speed and timing
- **Curved (Evasive)**: Arcing trajectories while approaching
  - Objects spiral or arc inward
  - Combines lateral movement with approach
  - Harder to track and predict

**Psychological Difference from Classic Mode:**
- Classic Mode: "Catch it before it escapes!" (opportunity loss)
- Incoming Mode: "Stop it before impact!" (threat mitigation)
- Different evolutionary circuits: prey escape vs. predator defense
- Both use same 3D projection math, just inverted

**Difficulty Progression:**
- Level 1: Slow, large starting size, linear trajectories
- Level 2-3: Faster approach, smaller starting size
- Level 4-5: Multiple simultaneous threats
- Level 6+: Curved evasive trajectories, very fast approach

**Implementation Note:**
Trajectory curvature should be **parameterized**, not hardcoded:
- `curvature_factor = 0.0`: Linear/straight trajectories (Asteroids style)
- `curvature_factor = 0.5`: Moderate arcs
- `curvature_factor = 1.0`: Strong parabolic curves (Classic Duck Hunt)

This allows any game mode to use linear or curved trajectories as needed.

---

### 3. Stationary Flash Mode (📋 Planned - Deliverable 4.1)

**Purpose**: Memory + reaction time training

**Gameplay:**
- Targets appear briefly at random positions (1-2 seconds)
- Targets disappear but remain "active" for shooting window (2-3 seconds)
- Player must remember position and shoot where target was
- Visual cue: faint outline or question mark at position after disappearing

**Progression Dimensions:**
1. **Display time**: Longer → Shorter (2s → 0.5s)
2. **Memory window**: Longer → Shorter (5s → 2s)
3. **Number of targets**: Single → Multiple sequential positions to remember
4. **Distractor targets**: False targets that shouldn't be shot

**Scoring:**
- Base points for hitting remembered position
- Bonus for speed (faster memory recall)
- Penalty for shooting wrong remembered positions
- Combo multiplier for consecutive correct memories

**Skill Focus:**
- Spatial memory
- Pattern recognition
- Quick decision making
- Position estimation

**Levels:**
```
Level 1: Single target, 2s display, 5s window
Level 2: Single target, 1.5s display, 4s window
Level 3: Single target, 1s display, 3s window
Level 4: Two sequential targets, 1.5s each, 4s window
Level 5: Two sequential targets, 1s each, 3s window
Level 6: Three sequential targets, 1s each, 3s window
Level 7+: Distractor targets added
```

---

### 3. Sequence Mode (📋 Planned - Deliverable 4.2)

**Purpose**: Decision making + prioritization training

**Gameplay:**
- Multiple targets spawn simultaneously with numbers or colors
- Must hit targets in specific order (1→2→3 or red→green→blue)
- Hitting wrong target = penalty (combo break, time penalty, or miss)
- Targets may move while player makes decisions
- Time pressure: sequence expires after X seconds

**Progression Dimensions:**
1. **Sequence length**: 2 → 6 targets in order
2. **Target movement**: Stationary → Slow → Fast
3. **Time pressure**: Generous → Tight time limits
4. **Complexity**: Numbers → Colors → Symbols → Mixed
5. **Distractor targets**: Extra targets not in sequence

**Scoring:**
- Base points for correct sequence completion
- Bonus for speed (complete sequence quickly)
- Multiplier for perfect sequences (no mistakes)
- Penalty for wrong order

**Skill Focus:**
- Pattern recognition
- Planning and sequencing
- Multi-target tracking
- Decision speed under pressure

**Levels:**
```
Level 1: 2 stationary targets, 10s time limit
Level 2: 3 stationary targets, 10s time limit
Level 3: 3 slow-moving targets, 12s time limit
Level 4: 4 slow-moving targets, 12s time limit
Level 5: 4 fast-moving targets, 15s time limit
Level 6: 5 fast-moving targets, 15s time limit
Level 7+: Distractor targets added
```

---

### 4. Precision Mode (💡 New Concept)

**Purpose**: Accuracy over speed training

**Gameplay:**
- Small, slow-moving (or stationary) targets
- High penalty for misses
- Target size decreases with progression
- Optional: Shrinking hit zones (center worth more points)
- Very limited number of shots per round

**Progression Dimensions:**
1. **Target size**: Large → Tiny (50px → 10px radius)
2. **Shot economy**: Unlimited → Limited shots (10 → 5 → 3)
3. **Hit zones**: Full target → Bullseye scoring (center = bonus)
4. **Target arrangement**: Random → Challenging positions (edges, clusters)

**Scoring:**
- High points for hits (accuracy valued)
- Severe penalty for misses (100 points = 1 hit, -50 points = 1 miss)
- Bonus for hitting target center (bullseye)
- Perfect round bonus (100% accuracy)

**Skill Focus:**
- Fine motor control
- Patience and timing
- Accuracy over speed
- Shot selection

**Levels:**
```
Level 1: 40px targets, 15 shots, 10 targets
Level 2: 35px targets, 12 shots, 10 targets
Level 3: 30px targets, 10 shots, 10 targets
Level 4: 25px targets, 10 shots, 12 targets (bullseye scoring introduced)
Level 5: 20px targets, 8 shots, 12 targets
Level 6: 15px targets, 6 shots, 10 targets
Level 7+: 10px targets, limited shots, challenging positions
```

---

### 5. Reflex Mode (💡 New Concept)

**Purpose**: Pure reaction time training

**Gameplay:**
- Targets appear suddenly and briefly (0.3-0.5s)
- No predictable pattern or warning
- Must shoot before target disappears
- No penalty for missed opportunities (only for wrong shots)
- Focus on twitch reflexes

**Progression Dimensions:**
1. **Display duration**: 1s → 0.3s → 0.15s
2. **Spawn frequency**: Slow → Fast → Rapid
3. **Spawn predictability**: Random positions → Including peripheral vision areas
4. **Distractor frequency**: Occasional false targets that shouldn't be shot

**Scoring:**
- Points only for hitting before target disappears
- Bonus for very fast reactions (<200ms)
- Penalty for shooting non-targets (if distractors enabled)
- Streak bonus for consecutive quick hits

**Skill Focus:**
- Reaction time
- Peripheral vision awareness
- Snap targeting
- Impulse control (not shooting distractors)

**Levels:**
```
Level 1: 1s display, 2s between spawns, center screen area
Level 2: 0.8s display, 1.5s between spawns, half screen area
Level 3: 0.6s display, 1.2s between spawns, full screen area
Level 4: 0.5s display, 1s between spawns, full screen + distractors
Level 5: 0.4s display, 0.8s between spawns, full screen + distractors
Level 6: 0.3s display, 0.6s between spawns, full screen + frequent distractors
Level 7+: 0.2s display, rapid spawning, high distractor frequency
```

---

### 6. Rhythm Mode (💡 New Concept)

**Purpose**: Timing and cadence training

**Gameplay:**
- Targets appear in rhythmic patterns
- Must shoot on the beat (or at specific timing intervals)
- Visual/audio cues indicate rhythm
- Shooting off-rhythm = miss or reduced points
- Like a timing-based rhythm game

**Progression Dimensions:**
1. **Rhythm complexity**: Simple steady beat → Complex syncopation
2. **Tempo**: Slow (60 BPM) → Fast (180 BPM)
3. **Pattern variability**: Repeating → Changing patterns
4. **Feedback latency**: Forgiving timing window → Strict timing

**Scoring:**
- Perfect timing = full points
- Close timing = reduced points
- Off-beat = miss
- Streak bonus for sustained rhythm
- Multiplier for complex patterns

**Skill Focus:**
- Timing consistency
- Pattern anticipation
- Muscle memory for cadence
- Coordination under tempo pressure

---

### 7. Adaptive Training Mode (💡 Advanced Concept)

**Purpose**: Personalized skill development

**Gameplay:**
- AI-driven difficulty adjustment
- Analyzes player weaknesses:
  - Slow targets vs fast targets accuracy
  - Left side vs right side performance
  - Small targets vs large targets
  - Reaction time distribution
- Focuses training on weak areas
- Mixes elements from other modes

**Progression:**
- Automatic difficulty adjustment
- Identifies skill gaps and creates targeted drills
- Provides performance analytics and recommendations

**Skill Focus:**
- Comprehensive skill assessment
- Targeted weakness training
- Balanced skill development

---

## Level Progression System Design

### Global Progression Framework

**Experience Points (XP):**
- Earn XP for all activities (hits, completions, challenges)
- XP unlocks new modes, customization options, and harder difficulties
- Persistent across modes

**Player Level:**
- Level 1-100 progression
- Unlock new modes at milestones:
  - Level 1: Classic Mode unlocked
  - Level 5: Stationary Flash Mode unlocked
  - Level 10: Sequence Mode unlocked
  - Level 15: Precision Mode unlocked
  - Level 20: Reflex Mode unlocked
  - Level 25: Rhythm Mode unlocked
  - Level 30: Adaptive Training unlocked

**Difficulty Tiers per Mode:**
```
Beginner    (Levels 1-3)   - Learning mechanics
Intermediate (Levels 4-6)   - Building competency
Advanced    (Levels 7-9)   - Challenging mastery
Expert      (Levels 10+)   - Extreme difficulty
```

---

### Difficulty Variables (Configurable per Mode)

**Target Properties:**
- `size`: Radius in pixels (50px → 10px)
- `speed`: Pixels per second (50 → 500)
- `spawn_rate`: Seconds between spawns (3s → 0.5s)
- `max_active`: Simultaneous targets (1 → 10)
- `lifetime`: Seconds before despawn (10s → 1s)

**Game Constraints:**
- `time_limit`: Seconds per round/level (unlimited → 30s)
- `shot_limit`: Max shots allowed (unlimited → 5)
- `target_count`: Targets to spawn (5 → 50)
- `miss_tolerance`: Max misses before fail (unlimited → 3)

**Environmental Factors:**
- `spawn_area`: Screen region for spawning (full → edges only)
- `movement_pattern`: How targets move (linear → random walk → bezier)
- `distractor_frequency`: False target spawn rate (0% → 30%)

---

### Per-Mode Progression Examples

#### Classic Mode Progression Curve

```python
levels = {
    1: {"speed": 50,  "spawn_rate": 3.0, "max_active": 1, "size": 40},
    2: {"speed": 75,  "spawn_rate": 2.5, "max_active": 2, "size": 38},
    3: {"speed": 100, "spawn_rate": 2.0, "max_active": 2, "size": 36},
    4: {"speed": 125, "spawn_rate": 2.0, "max_active": 3, "size": 34},
    5: {"speed": 150, "spawn_rate": 1.8, "max_active": 3, "size": 32},
    6: {"speed": 175, "spawn_rate": 1.5, "max_active": 4, "size": 30},
    7: {"speed": 200, "spawn_rate": 1.5, "max_active": 4, "size": 28},
    8: {"speed": 250, "spawn_rate": 1.2, "max_active": 5, "size": 26},
    9: {"speed": 300, "spawn_rate": 1.0, "max_active": 5, "size": 24},
    10:{"speed": 350, "spawn_rate": 1.0, "max_active": 6, "size": 22},
}
```

#### Flash Mode Progression Curve

```python
levels = {
    1: {"display_time": 2.0, "memory_window": 5.0, "count": 1, "size": 40},
    2: {"display_time": 1.5, "memory_window": 4.5, "count": 1, "size": 38},
    3: {"display_time": 1.0, "memory_window": 4.0, "count": 1, "size": 36},
    4: {"display_time": 1.5, "memory_window": 4.0, "count": 2, "size": 35},
    5: {"display_time": 1.0, "memory_window": 3.5, "count": 2, "size": 33},
    6: {"display_time": 1.0, "memory_window": 3.0, "count": 3, "size": 32},
    7: {"display_time": 0.8, "memory_window": 3.0, "count": 3, "size": 30},
    8: {"display_time": 0.8, "memory_window": 2.5, "count": 4, "size": 28},
    9: {"display_time": 0.6, "memory_window": 2.5, "count": 4, "size": 26},
    10:{"display_time": 0.5, "memory_window": 2.0, "count": 5, "size": 25},
}
```

---

## Scoring & Rewards System

### Points System

**Base Points:**
- Hit: 100 points
- Perfect accuracy round: +500 bonus
- Speed bonus: +10 per 100ms faster than target deadline
- Size bonus: Smaller targets worth more (10px = 3x multiplier)

**Combo System:**
- Consecutive hits multiply score: 2x, 3x, 4x, 5x (caps at 5x)
- Combo breaks on miss or escaped target
- Audio/visual feedback at combo milestones (5, 10, 25, 50)

**Mode-Specific Bonuses:**
- Flash Mode: Memory accuracy bonus (+50 per remembered position)
- Sequence Mode: Perfect sequence bonus (+200)
- Precision Mode: Bullseye bonus (+150 for center hits)
- Reflex Mode: Fast reflex bonus (<200ms = +100)

### Unlockables

**Cosmetic:**
- Target skins (different shapes, colors, themes)
- Hit effect styles (explosions, sparks, cartoon effects)
- Sound packs (8-bit, realistic, musical)
- Background themes

**Gameplay:**
- Custom difficulty sliders
- Practice mode with specific parameters
- Challenge mode with special constraints
- Multiplayer/competitive modes (future)

---

## Implementation Considerations

### Architecture Alignment

All modes should:
- Extend the `GameMode` base class (game/game_mode.py)
- Use Pydantic models for configuration and state
- Support the existing InputManager abstraction
- Use Target class for all target entities
- Use ScoreTracker for scoring
- Use FeedbackManager for visual/audio feedback

### Critical Architecture Separation: Trajectory System vs. Presentation Layer

**The trajectory/physics system is completely independent from visual presentation.**

**Trajectory System (Universal Logic):**
- 3D position calculation (X, Y, Z coordinates)
- Velocity and acceleration
- Parametric curve following (Bezier, linear, etc.)
- Depth simulation (distance_factor)
- Curvature parameters
- Hit detection (bounding boxes based on size)
- **Agnostic to what is being displayed**

**Presentation Layer (Themeable):**
- What sprite/shape to render (ducks, basketballs, asteroids, zombies, etc.)
- Background scenes (forest, basketball court, space, graveyard)
- Foreground obstacles (trees, hoops, debris)
- Sound effects (quacks, bounces, explosions, groans)
- Visual effects (feathers, sparks, blood splatter)
- Color schemes and art style

**Implementation Benefit:**
```python
# Same trajectory system, different themes
classic_mode = ClassicMode(theme="ducks")      # Forest scene, quacking sounds
basketball_mode = ClassicMode(theme="basketball")  # Court scene, bounce sounds
space_mode = ClassicMode(theme="asteroids")    # Space scene, explosion sounds
zombie_mode = ClassicMode(theme="zombie_geese")  # Graveyard, groans

# All use identical 3D trajectory physics
# Only visual/audio presentation differs
```

**Theme Configuration (Pydantic Model):**
```python
class Theme(BaseModel):
    name: str
    target_sprite: str  # Path to sprite or shape type
    background_image: Optional[str]
    foreground_image: Optional[str]
    hit_sound: str
    spawn_sound: str
    miss_sound: str
    hit_particle_effect: str  # "feathers", "sparks", "explosion", etc.

# Themes can be swapped without touching game logic
```

**Benefits:**
- ✅ Single trajectory codebase serves infinite themes
- ✅ Easy to add new themes without duplicating logic
- ✅ Modding support - users can create custom themes
- ✅ Seasonal variants (Halloween zombies, Christmas snowballs, etc.)
- ✅ Clear separation of concerns
- ✅ Testable physics independent of rendering

---

### Open Source & Modding Support

**This is designed as an open source game with first-class modding support.**

**Core Design Principle:**
> The engine is open, the content is replaceable. Anyone should be able to create and share custom themes without touching game logic.

**Modding Architecture:**

**1. Theme Packages (Mods)**
```
themes/
├── classic_ducks/
│   ├── theme.json          # Theme configuration (Pydantic-validated)
│   ├── target.png          # Target sprite
│   ├── background.png      # Background image
│   ├── foreground.png      # Foreground obstacles (with transparency)
│   ├── sounds/
│   │   ├── spawn.wav
│   │   ├── hit.wav
│   │   └── miss.wav
│   └── particles/
│       └── hit_effect.png  # Feathers, sparks, etc.
│
├── basketball/
│   └── ...
│
└── zombie_geese/
    └── ...
```

**2. Theme Configuration (theme.json)**
```json
{
  "name": "Classic Ducks",
  "version": "1.0.0",
  "author": "Community",
  "description": "Original Duck Hunt style with forest background",
  "target": {
    "sprite": "target.png",
    "sprite_type": "animated",  // "static", "animated", "sprite_sheet"
    "animation_frames": 4,
    "animation_speed": 0.1
  },
  "background": {
    "image": "background.png",
    "parallax_layers": []  // Optional depth layers
  },
  "foreground": {
    "image": "foreground.png",
    "occlusion_enabled": true
  },
  "sounds": {
    "spawn": "sounds/spawn.wav",
    "hit": "sounds/hit.wav",
    "miss": "sounds/miss.wav"
  },
  "particles": {
    "hit_effect": "particles/hit_effect.png",
    "hit_effect_type": "burst",  // "burst", "trail", "explosion"
    "hit_effect_count": 20,
    "hit_effect_lifetime": 0.5
  },
  "colors": {
    "ui_primary": "#8B4513",
    "ui_secondary": "#D2691E"
  }
}
```

**3. Theme Loading System**
```python
class ThemeManager:
    """Loads and manages user-created themes."""

    def load_theme(self, theme_name: str) -> Theme:
        """Load theme from themes/ directory."""
        theme_path = Path("themes") / theme_name
        config = self._load_json(theme_path / "theme.json")
        return Theme.model_validate(config)  # Pydantic validation

    def list_available_themes(self) -> List[str]:
        """Discover all installed themes."""
        return [d.name for d in Path("themes").iterdir() if d.is_dir()]
```

**4. Modding Documentation**

Create `MODDING.md` with:
- Theme structure specification
- Asset format requirements (PNG, WAV, etc.)
- JSON schema for theme.json
- Example theme walkthrough
- Animation guidelines
- Sound effect guidelines
- How to test themes locally
- How to share themes (GitHub, mod sites)

**5. Community Features**

**Theme Browser (Future):**
- In-game theme selector
- Preview before applying
- Download from community repository
- Rate/review themes
- Automatic updates

**Theme Creation Tool (Future):**
- GUI for theme.json editing
- Asset validation
- Preview mode
- Export as shareable package

**6. Example Community Themes**

Starter theme ideas to inspire modders:
- **Classic Ducks**: Original NES style
- **Basketball Free Throws**: Court, basketballs, bounce sounds
- **Space Asteroids**: Black background, rocks, explosions
- **Zombie Apocalypse**: Graveyard, zombie ducks, gore effects
- **Fruit Ninja**: Kitchen, sliced fruit, juice splatter
- **Clay Pigeons**: Outdoor range, realistic skeet
- **Cyberpunk Drones**: Neon city, flying drones, electric effects
- **Medieval Archery**: Castle, targets, arrow sounds
- **Snowball Fight**: Winter scene, snowballs, kids laughing
- **Paintball**: Arena, paintballs, splat effects

**7. Licensing Considerations**

**Code:** MIT or GPL (permissive open source)
**Themes:** Each theme can have its own license
- Built-in themes: Same as code license
- Community themes: Creator chooses license
- Asset attribution in theme.json

**Benefits for Open Source:**
- ✅ Lowers barrier to contribution (art vs. code)
- ✅ Allows non-programmers to contribute
- ✅ Community can create educational themes
- ✅ Seasonal/holiday themes from community
- ✅ Localized themes (different cultures)
- ✅ Accessible themes (colorblind, high contrast)
- ✅ Viral potential (people share cool themes)
- ✅ Long-term content generation without core team effort

**Testing Themes:**
```bash
# Run with specific theme
./venv/bin/python main.py --theme basketball

# Validate theme package
./venv/bin/python tools/validate_theme.py themes/my_theme

# Preview theme without playing
./venv/bin/python tools/theme_preview.py themes/my_theme
```

---

### Data-Driven Game Modes (YAML Configuration)

**Critical Architecture Decision: Game modes should be declarative, not imperative.**

Instead of hardcoding game mode logic in Python classes, define them in **YAML configuration files**. This allows:
- Community creation of new game modes without writing code
- Easy parameter tuning and balancing
- A/B testing different difficulty curves
- Swapping trajectory algorithms per mode/level
- Educational use (teaching different physics models)
- Rapid prototyping of game mode ideas

**Game Mode Configuration File Structure:**

```yaml
# modes/classic_ducks.yaml

# Metadata
name: "Classic Duck Hunt"
id: "classic_ducks"
version: "1.0.0"
description: "Original Duck Hunt gameplay with curved trajectories"
author: "Core Team"
unlock_requirement: 0  # Available from start

# Link to presentation theme
theme: "classic_ducks"  # References themes/classic_ducks/

# Trajectory algorithm selection
trajectory:
  algorithm: "bezier_3d"  # Options: "linear", "bezier_2d", "bezier_3d", "physics_ballistic"
  depth_direction: "away"  # "away" (receding) or "toward" (approaching)
  curvature_factor: 1.0   # 0.0 = straight line, 1.0 = full curve

# Spawn configuration
spawning:
  spawn_sides: ["left", "right"]  # Where targets can spawn
  spawn_rate_base: 2.0            # Seconds between spawns
  max_active: 3                    # Max simultaneous targets

# Win/Loss conditions
rules:
  game_type: "endless"  # "endless", "score_target", "survival", "timed"
  # Optional: score_target: 50
  # Optional: max_misses: 10
  # Optional: time_limit: 120

# Per-level difficulty progression
levels:
  - level: 1
    target:
      size: 50.0
      speed: 100.0
      depth_range: [1.0, 2.0]  # Z-axis distance multiplier
    trajectory:
      curvature_factor: 0.8    # Slight curves
    spawning:
      spawn_rate: 2.5
      max_active: 1

  - level: 2
    target:
      size: 45.0
      speed: 120.0
      depth_range: [1.0, 2.5]
    trajectory:
      curvature_factor: 1.0    # Full curves
    spawning:
      spawn_rate: 2.2
      max_active: 2

  - level: 3
    target:
      size: 40.0
      speed: 150.0
      depth_range: [1.0, 3.0]
    trajectory:
      curvature_factor: 1.2    # Exaggerated curves
    spawning:
      spawn_rate: 2.0
      max_active: 2

  # ... more levels

# Scoring configuration
scoring:
  base_hit_points: 100
  combo_multiplier: true
  apex_bonus: 50  # Bonus for hitting at trajectory apex
  speed_bonus: true
```

**Example: Asteroids-Style Incoming Mode**

```yaml
# modes/incoming_asteroids.yaml

name: "Incoming Threats"
id: "incoming_asteroids"
description: "Stop asteroids before they reach you"
theme: "space_asteroids"

trajectory:
  algorithm: "bezier_3d"
  depth_direction: "toward"  # ← Key difference!
  curvature_factor: 0.0      # Linear trajectories (classic asteroids)

spawning:
  spawn_sides: ["top", "bottom", "left", "right"]  # Can come from anywhere
  spawn_rate_base: 1.5
  max_active: 5

rules:
  game_type: "survival"
  max_misses: 3  # 3 impacts = game over

levels:
  - level: 1
    target:
      size: 20.0  # Start small (far away)
      speed: 80.0
      depth_range: [3.0, 1.0]  # Far to close
    trajectory:
      curvature_factor: 0.0  # Straight lines
    spawning:
      spawn_rate: 2.0
      max_active: 2

  - level: 2
    target:
      size: 20.0
      speed: 100.0
      depth_range: [3.0, 1.0]
    trajectory:
      curvature_factor: 0.3  # Slight curves (evasive)
    spawning:
      spawn_rate: 1.8
      max_active: 3

  # ... more levels
```

**Trajectory Algorithm Registry:**

```python
# game/trajectory/registry.py

class TrajectoryAlgorithm(Protocol):
    """Interface for trajectory generation algorithms."""
    def generate(self, config: dict) -> Trajectory:
        """Generate trajectory from configuration."""
        ...

class TrajectoryRegistry:
    """Registry of available trajectory algorithms."""

    _algorithms: Dict[str, Type[TrajectoryAlgorithm]] = {
        "linear": LinearTrajectory,
        "bezier_2d": Bezier2DTrajectory,
        "bezier_3d": Bezier3DTrajectory,
        "physics_ballistic": PhysicsBallisticTrajectory,
        "sine_wave": SineWaveTrajectory,
        "spiral": SpiralTrajectory,
        # Easy to add custom algorithms
    }

    @classmethod
    def get(cls, name: str) -> Type[TrajectoryAlgorithm]:
        """Get trajectory algorithm by name."""
        return cls._algorithms[name]

    @classmethod
    def register(cls, name: str, algorithm: Type[TrajectoryAlgorithm]):
        """Register custom trajectory algorithm."""
        cls._algorithms[name] = algorithm
```

**Game Mode Loader:**

```python
# game/mode_loader.py

class GameModeLoader:
    """Loads game modes from YAML configuration files."""

    def load_mode(self, mode_id: str) -> GameModeConfig:
        """Load mode configuration from YAML."""
        yaml_path = Path("modes") / f"{mode_id}.yaml"
        with open(yaml_path) as f:
            config_dict = yaml.safe_load(f)

        # Validate with Pydantic
        return GameModeConfig.model_validate(config_dict)

    def list_available_modes(self) -> List[str]:
        """Discover all available game modes."""
        return [
            p.stem for p in Path("modes").glob("*.yaml")
        ]

class DynamicGameMode(GameMode):
    """Game mode that executes based on YAML configuration."""

    def __init__(self, config: GameModeConfig):
        super().__init__()
        self.config = config
        self.theme = ThemeManager.load_theme(config.theme)
        self.trajectory_algo = TrajectoryRegistry.get(config.trajectory.algorithm)
        # ... initialize based on config

    def _spawn_target(self):
        """Spawn target using configured algorithm."""
        level_config = self._get_current_level_config()

        # Generate trajectory using selected algorithm
        trajectory = self.trajectory_algo.generate({
            "depth_direction": self.config.trajectory.depth_direction,
            "curvature_factor": level_config.trajectory.curvature_factor,
            "depth_range": level_config.target.depth_range,
            "speed": level_config.target.speed,
            # ... other params
        })

        # Create target
        target = Target(
            trajectory=trajectory,
            size=level_config.target.size,
            # ...
        )
        self._targets.append(target)
```

**Configuration Data Models (Pydantic):**

```python
# models/game_mode_config.py

class TrajectoryConfig(BaseModel):
    algorithm: str
    depth_direction: Literal["away", "toward"]
    curvature_factor: float = 1.0

class SpawningConfig(BaseModel):
    spawn_sides: List[Literal["left", "right", "top", "bottom"]]
    spawn_rate_base: float
    max_active: int

class RulesConfig(BaseModel):
    game_type: Literal["endless", "score_target", "survival", "timed"]
    score_target: Optional[int] = None
    max_misses: Optional[int] = None
    time_limit: Optional[float] = None

class TargetConfig(BaseModel):
    size: float
    speed: float
    depth_range: Tuple[float, float]

class LevelConfig(BaseModel):
    level: int
    target: TargetConfig
    trajectory: TrajectoryConfig
    spawning: SpawningConfig

class ScoringConfig(BaseModel):
    base_hit_points: int
    combo_multiplier: bool
    apex_bonus: int = 0
    speed_bonus: bool = False

class GameModeConfig(BaseModel):
    name: str
    id: str
    version: str
    description: str
    author: str = "Community"
    unlock_requirement: int = 0
    theme: str
    trajectory: TrajectoryConfig
    spawning: SpawningConfig
    rules: RulesConfig
    levels: List[LevelConfig]
    scoring: ScoringConfig
```

**Benefits of Data-Driven Modes:**

- ✅ **Community Mode Creation**: Non-programmers can create modes with YAML
- ✅ **Rapid Prototyping**: Test new ideas without code changes
- ✅ **Easy Balancing**: Tweak numbers in YAML, reload instantly
- ✅ **A/B Testing**: Create variants of modes to test difficulty curves
- ✅ **Educational**: Teach different physics models (linear, parabolic, etc.)
- ✅ **Algorithm Swapping**: Try different trajectory algorithms per level
- ✅ **Modding**: Share custom modes as simple YAML files
- ✅ **Version Control**: Easy to track balance changes in git
- ✅ **Validation**: Pydantic ensures correctness before runtime

**Usage:**

```bash
# Play specific mode
./venv/bin/python main.py --mode classic_ducks

# Validate mode configuration
./venv/bin/python tools/validate_mode.py modes/my_mode.yaml

# List available modes
./venv/bin/python main.py --list-modes
```

**Creating New Modes:**

Community members can create new modes by:
1. Copy an existing YAML file from `modes/`
2. Modify parameters, trajectory algorithm, rules
3. Reference an existing theme or create a new one
4. Test locally
5. Share YAML file with community

No Python knowledge required!

### Testing Strategy

Each mode needs:
- Unit tests for core logic (spawning, hit detection, scoring)
- Level progression validation tests
- Edge case tests (level transitions, score boundaries)
- Mock input for automated gameplay simulation

---

## Skill Development Matrix

| Mode | Accuracy | Speed | Memory | Decision | Reaction | Timing | Prediction |
|------|----------|-------|--------|----------|----------|--------|------------|
| Classic | ●●○ | ●●● | ○○○ | ●○○ | ●●○ | ●●○ | ●○○ |
| Ballistic Arc | ●●● | ●●○ | ○○○ | ●●○ | ●●○ | ●●● | ●●● |
| Flash | ●●○ | ●○○ | ●●● | ●●○ | ●●○ | ○○○ | ●○○ |
| Sequence | ●●○ | ●●○ | ●●○ | ●●● | ●○○ | ●●○ | ●●○ |
| Precision | ●●● | ○○○ | ○○○ | ●○○ | ○○○ | ●●○ | ○○○ |
| Reflex | ●●○ | ●●● | ○○○ | ●○○ | ●●● | ●○○ | ○○○ |
| Rhythm | ●●○ | ●●○ | ●○○ | ○○○ | ●●○ | ●●● | ○○○ |

**Legend**: ●●● = Primary focus, ●●○ = Secondary focus, ●○○ = Minimal focus, ○○○ = Not relevant

**Ballistic Arc Mode** is the most comprehensive training mode - it develops accuracy, timing, and prediction skills simultaneously, mimicking real projectile motion.

---

## Future Extensions

### Multi-player Modes
- Cooperative: Two players share screen, team scoring
- Competitive: Split-screen racing to target score
- Hot-seat: Turn-based high score competition

### Integration with Physical Systems
- When integrated with laser pointer/arrow detection:
  - Adjust difficulty based on physical accuracy constraints
  - Larger targets for physical projectiles
  - Slower movement speeds
  - Account for reload/reset time
- Calibration mode to test input accuracy and latency

### Analytics & Progress Tracking
- Store performance history (SQLite/JSON)
- Track skill development over time
- Generate progress reports
- Identify improvement areas
- Compare performance across modes

### Accessibility Options
- Colorblind modes
- Adjustable contrast
- Audio cues for target positions
- Adjustable game speed (0.5x - 2.0x)
- Input assist options

---

## Implementation Priorities

### 🎯 IMMEDIATE PRIORITY: Classic Mode Enhancement
1. **Add Curved Flight Paths to Classic Mode** - This is not a new mode, but an enhancement to the existing mode!
   - Implements the original Duck Hunt's engaging non-linear trajectories
   - Replaces boring straight-line movement
   - Uses Bezier curves for parabolic arcs
   - Each target gets unique trajectory (start, apex, end points)
   - Makes the game FUN like the original!

### Phase 4: Additional Game Modes (After Classic is Enhanced)
2. **Flash Mode** (Deliverable 4.1) - Memory training
3. **Sequence Mode** (Deliverable 4.2) - Decision training

### Phase 5+: Advanced Features (Future)
4. **Precision Mode** - Accuracy training
5. **Reflex Mode** - Reaction training
6. **Level Progression System** - XP, unlocks, difficulty curves
7. **Rhythm Mode** - Timing training
8. **Adaptive Training Mode** - AI-driven personalization

**Why Curved Trajectories First?**
- ✅ **Restores the fun factor** of original Duck Hunt
- ✅ **Variable practice principle** - each target is unique
- ✅ Trains prediction skills (critical for real projectile systems)
- ✅ Simple enhancement to existing code (not a whole new mode)
- ✅ Straightforward math (Bezier curves)
- ✅ Makes current game worth playing before adding more modes

---

*Last Updated: 2025-10-26*
*Status: Design Document - Ready for Implementation*
