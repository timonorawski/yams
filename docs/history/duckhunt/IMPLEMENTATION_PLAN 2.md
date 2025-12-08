# Duck Hunt Game - Implementation Plan

## Project Overview
Building a Duck Hunt style game with abstracted input layer to validate projection-based interactive system. The game must work with ANY coordinate-based input source (mouse, laser pointer, impact detection).

## Core Architecture Principles

1. **Input Abstraction**: Game logic never directly accesses mouse/keyboard - all input through InputManager
2. **Modularity**: Easy to add new game modes and input sources
3. **Testability**: Mouse input allows rapid development without specialized hardware; comprehensive unit tests for all components
4. **Performance**: Target 60 FPS with multiple targets
5. **Type Safety**: All internal data structures use Pydantic models for runtime validation and bug prevention
6. **Test-Driven Development**: Every testable component must have unit tests; aim for >80% coverage

## File Structure
```
DuckHunt/
├── main.py                    # Entry point
├── config.py                  # Game constants/settings
├── models.py                  # Pydantic models for all data structures
├── engine.py                  # Main game engine/loop
├── input/
│   ├── __init__.py
│   ├── input_event.py        # InputEvent Pydantic model
│   ├── input_manager.py      # InputManager
│   └── sources/
│       ├── __init__.py
│       ├── base.py           # InputSource ABC
│       ├── mouse.py          # MouseInputSource
│       └── laser.py          # LaserPointerInputSource (stub)
├── game/
│   ├── __init__.py
│   ├── target.py             # Target class with Pydantic state
│   ├── game_mode.py          # GameMode base class
│   ├── modes/
│   │   ├── __init__.py
│   │   ├── classic.py        # Classic Duck Hunt mode
│   │   ├── flash.py          # Stationary Flash mode
│   │   └── sequence.py       # Sequence mode
│   ├── scoring.py            # Score tracking with Pydantic models
│   └── feedback.py           # Visual/audio feedback
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Pytest fixtures and configuration
│   ├── test_models.py        # Test all Pydantic models
│   ├── test_input/
│   │   ├── __init__.py
│   │   ├── test_input_event.py
│   │   ├── test_input_manager.py
│   │   └── test_sources.py
│   └── test_game/
│       ├── __init__.py
│       ├── test_target.py
│       ├── test_scoring.py
│       ├── test_feedback.py
│       └── test_modes/
│           ├── __init__.py
│           ├── test_classic.py
│           ├── test_flash.py
│           └── test_sequence.py
└── assets/                   # Sprites, sounds (optional)
```

---

## Implementation Deliverables

### Phase 1: Foundation (MVP)

#### Deliverable 1.1: Project Setup
- [x] Create directory structure (including tests/)
- [x] Create all `__init__.py` files
- [x] Create `config.py` with screen dimensions, colors, game constants
- [x] Create `requirements.txt` (pygame, pydantic, numpy, pytest, pytest-cov)
- [x] Create `pytest.ini` or `pyproject.toml` with pytest configuration
- [x] Set up test coverage requirements (minimum 80%)

#### Deliverable 1.2: Core Data Models (Pydantic Schemas)
- [x] Create `models.py` with all Pydantic base models
  - `Vector2D` - position/velocity with x, y coordinates (validated floats)
  - `Color` - RGBA color with validation (0-255 range)
  - `Rectangle` - bounding box with position and size
  - `EventType` - enum for input event types
  - `TargetState` - enum for target states (alive, hit, missed, escaped)
  - `GameState` - enum for game states (menu, playing, paused, game_over)
- [x] Add validation decorators and computed fields where needed
- [x] Add `model_config` for immutability where appropriate (frozen=True)
- [x] Include docstrings and examples for each model
- [x] **TESTS**: Create `tests/test_models.py`
  - Test Vector2D validation (negative coords, type coercion)
  - Test Color validation (out of range values, invalid types)
  - Test Rectangle computed properties (area, contains_point)
  - Test all enums have expected values
  - Test immutability (frozen models can't be modified)
  - Test edge cases (zero values, large values, floats vs ints)

#### Deliverable 1.3: Input Abstraction Layer
- [ ] Define `InputEvent` Pydantic model (input/input_event.py)
  - Fields: position (Vector2D), timestamp (float), event_type (EventType)
  - Validator: ensure timestamp is positive
  - Validator: ensure position coordinates are non-negative
  - Frozen model (immutable after creation)
  - String representation for debugging
- [ ] Implement `InputSource` ABC (input/sources/base.py)
  - Abstract method: `poll_events() -> List[InputEvent]`
  - Abstract method: `update(dt: float)` for time-based processing
- [ ] Implement `MouseInputSource` (input/sources/mouse.py)
  - Converts pygame mouse clicks to InputEvent models
  - Creates Vector2D from click position
  - Validates all data through Pydantic
  - Generates timestamp
- [ ] Implement `InputManager` (input/input_manager.py)
  - Manages active input source
  - Provides `get_events() -> List[InputEvent]` method
  - Validates input source switching
  - Type-safe input source management
- [ ] **TESTS**: Create `tests/test_input/`
  - `test_input_event.py`: Test InputEvent creation, validation, immutability
  - `test_input_manager.py`: Test source switching, event polling, error handling
  - `test_sources.py`: Mock InputSource implementations, test MouseInputSource with fake pygame events
  - Test invalid data handling (negative timestamps, invalid coordinates)
  - Test event batching and ordering

#### Deliverable 1.4: Basic Target System
- [ ] Define `TargetData` Pydantic model (in models.py)
  - Fields: position (Vector2D), velocity (Vector2D), size (float), state (TargetState)
  - Validator: ensure size is positive
  - Method: `get_bounds() -> Rectangle` for collision detection
  - Computed field: `is_active` (state == TargetState.ALIVE)
- [ ] Implement `Target` class (game/target.py)
  - Encapsulates TargetData model
  - Method: `update(dt)` - creates new TargetData with updated position
  - Method: `contains_point(position: Vector2D) -> bool` - hit detection
  - Method: `render(screen)` - draw target (simple rectangle/circle)
  - Method: `is_off_screen(width, height)` - check if escaped
  - Immutable state updates (returns new Target instances)
- [ ] **TESTS**: Create `tests/test_game/test_target.py`
  - Test TargetData validation (positive size, valid states)
  - Test target movement (position updates correctly with velocity)
  - Test hit detection (point inside/outside bounds)
  - Test boundary detection (on/off screen)
  - Test state transitions (alive → hit, alive → escaped)
  - Test immutability (update returns new instance)
  - Test edge cases (zero velocity, edge of screen, tiny targets)

#### Deliverable 1.5: Minimal Game Engine
- [ ] Implement basic `GameEngine` class (engine.py)
  - Initialize pygame, display, clock
  - Main game loop structure
  - Frame timing (60 FPS)
  - Event handling (quit events)
  - Clear screen and flip display
- [ ] Create `main.py` entry point
  - Initialize engine
  - Run game loop

### Phase 2: Core Gameplay

#### Deliverable 2.1: Game Mode System
- [ ] Implement `GameMode` base class (game/game_mode.py)
  - Abstract method: `update(dt)` - game logic
  - Abstract method: `handle_input(events)` - process InputEvents
  - Abstract method: `render(screen)` - draw mode UI
  - Method: `get_score()` - return current score
  - Properties: targets list, game state (playing/won/lost)

#### Deliverable 2.2: Classic Mode Implementation
- [ ] Implement `ClassicMode` class (game/modes/classic.py)
  - Target spawning logic (random positions, edges)
  - Movement patterns (left-to-right, various angles)
  - Difficulty progression (speed increases over time)
  - Handle input events - check hits against all targets
  - Remove off-screen targets (count as misses)
  - Win/lose conditions

#### Deliverable 2.3: Scoring System
- [ ] Define `ScoreData` Pydantic model (in models.py)
  - Fields: hits (int), misses (int), current_combo (int), max_combo (int)
  - Validators: ensure all values are non-negative
  - Computed field: `total_shots` (hits + misses)
  - Computed field: `accuracy` (hits / total_shots if total_shots > 0)
  - Frozen model for immutability
- [ ] Implement `ScoreTracker` class (game/scoring.py)
  - Encapsulates ScoreData model
  - Method: `record_hit() -> ScoreTracker` - returns new instance with updated score
  - Method: `record_miss() -> ScoreTracker` - returns new instance, resets combo
  - Method: `get_stats() -> ScoreData` - return current score data
  - Method: `render(screen)` - display score UI
  - Immutable state pattern (functional approach)
- [ ] **TESTS**: Create `tests/test_game/test_scoring.py`
  - Test ScoreData validation (non-negative values)
  - Test computed fields (total_shots, accuracy)
  - Test accuracy calculation edge cases (zero shots, divide by zero)
  - Test ScoreTracker.record_hit() (increments hits, updates combo, max_combo)
  - Test ScoreTracker.record_miss() (increments misses, resets combo)
  - Test combo tracking (consecutive hits increment, miss resets)
  - Test max_combo tracking (stores highest combo achieved)
  - Test immutability (each operation returns new instance)
  - Test large numbers (many hits/misses)

#### Deliverable 2.4: Integrate Mode with Engine
- [ ] Update `GameEngine` to manage game modes
  - Initialize with ClassicMode
  - Pass InputManager events to active mode
  - Call mode's update and render
  - Handle game state transitions (menu → playing → game over)

### Phase 3: Feedback & Polish

#### Deliverable 3.1: Visual Feedback System
- [ ] Define `VisualEffect` Pydantic model (in models.py)
  - Fields: position (Vector2D), lifetime (float), max_lifetime (float), effect_type (EffectType enum)
  - Optional fields: color (Color), size (float), velocity (Vector2D)
  - Validators: ensure lifetime values are positive
  - Computed field: `alpha` (opacity based on lifetime for fade effects)
  - Computed field: `is_alive` (lifetime < max_lifetime)
- [ ] Define `ScorePopup` Pydantic model (in models.py)
  - Fields: position (Vector2D), value (int), lifetime (float), color (Color)
  - Extends/composes with VisualEffect
- [ ] Implement `FeedbackManager` class (game/feedback.py)
  - Manages list of VisualEffect models
  - Method: `add_hit_effect(position: Vector2D, points: int)` - creates effect models
  - Method: `add_miss_effect(position: Vector2D)` - creates effect models
  - Method: `update(dt)` - updates all effects, filters out dead ones
  - Method: `render(screen)` - draw all active effects
  - Type-safe effect management with validated models
- [ ] **TESTS**: Create `tests/test_game/test_feedback.py`
  - Test VisualEffect validation (positive lifetimes)
  - Test alpha computation (fades correctly over time)
  - Test is_alive logic (dies when lifetime exceeded)
  - Test FeedbackManager.add_hit_effect() (creates valid effect)
  - Test FeedbackManager.add_miss_effect() (creates valid effect)
  - Test FeedbackManager.update() (ages effects, removes dead ones)
  - Test effect lifecycle (create → update → die)
  - Test multiple simultaneous effects
  - Test ScorePopup value display

#### Deliverable 3.2: Audio Feedback (Optional but Recommended)
- [ ] Add audio to `FeedbackManager`
  - Hit sound effect (satisfying)
  - Miss sound effect (gentle)
  - Combo milestone sounds
  - Background music (optional)
  - Method: `play_hit_sound()`, `play_miss_sound()`

#### Deliverable 3.3: UI Polish
- [ ] Create start menu
  - Mode selection
  - Input source selection
  - Start/quit options
- [ ] Create game over screen
  - Final score display
  - Statistics (accuracy, best combo)
  - Restart/quit options
- [ ] Add pause functionality
  - Pause/resume key
  - Pause overlay

### Phase 4: Additional Game Modes

#### Deliverable 4.1: Stationary Flash Mode
- [ ] Implement `FlashMode` class (game/modes/flash.py)
  - Targets appear briefly then disappear
  - Player must remember positions
  - Limited time to shoot after disappearance
  - Score based on memory + reaction time

#### Deliverable 4.2: Sequence Mode
- [ ] Implement `SequenceMode` class (game/modes/sequence.py)
  - Multiple targets spawn with numbers/colors
  - Must hit in specific order
  - Wrong target = penalty
  - Track sequence progress
  - Visual indicators for correct order

### Phase 5: Extended Input Sources

#### Deliverable 5.1: Laser Pointer Input (Stub)
- [ ] Implement `LaserPointerInputSource` (input/sources/laser.py)
  - Stub implementation for testing architecture
  - Comment placeholders for CV integration
  - Same interface as MouseInputSource
  - Future: webcam color blob detection

#### Deliverable 5.2: Input Source Switching UI
- [ ] Add input source selection to menu
  - Display available sources
  - Allow runtime switching
  - Show active source indicator

### Phase 6: Configuration & Testing

#### Deliverable 6.1: Configuration System
- [ ] Expand `config.py` with all settings
  - Screen resolution (for projector)
  - Target sizes, speeds, spawn rates
  - Difficulty progression parameters
  - Color schemes
  - Input sensitivity/deadzone settings

#### Deliverable 6.2: Debug/Testing Features
- [ ] Add debug mode toggle
  - Show FPS counter
  - Show target bounding boxes
  - Show input event positions
  - Log input events to console
- [ ] Add target spawn testing
  - Manual spawn with key press
  - Freeze target movement
  - Adjust difficulty in real-time

---

## Technical Specifications

### Core Pydantic Models

#### Vector2D (Position/Velocity)
```python
from pydantic import BaseModel, field_validator

class Vector2D(BaseModel):
    """2D vector for positions and velocities"""
    x: float
    y: float

    @field_validator('x', 'y')
    @classmethod
    def validate_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Coordinates must be non-negative')
        return v

    model_config = {"frozen": True}  # Immutable
```

#### InputEvent
```python
from pydantic import BaseModel, field_validator
from enum import Enum

class EventType(str, Enum):
    HIT = "hit"
    MISS = "miss"

class InputEvent(BaseModel):
    """Immutable input event from any source"""
    position: Vector2D
    timestamp: float
    event_type: EventType

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Timestamp must be non-negative')
        return v

    model_config = {"frozen": True}
```

#### TargetData
```python
from enum import Enum

class TargetState(str, Enum):
    ALIVE = "alive"
    HIT = "hit"
    MISSED = "missed"
    ESCAPED = "escaped"

class TargetData(BaseModel):
    """Immutable target state"""
    position: Vector2D
    velocity: Vector2D
    size: float
    state: TargetState

    @field_validator('size')
    @classmethod
    def validate_size(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Size must be positive')
        return v

    @property
    def is_active(self) -> bool:
        return self.state == TargetState.ALIVE

    def get_bounds(self) -> Rectangle:
        """Get bounding box for collision detection"""
        return Rectangle(
            position=self.position,
            width=self.size,
            height=self.size
        )

    model_config = {"frozen": True}
```

#### ScoreData
```python
from pydantic import computed_field

class ScoreData(BaseModel):
    """Immutable score state"""
    hits: int = 0
    misses: int = 0
    current_combo: int = 0
    max_combo: int = 0

    @field_validator('hits', 'misses', 'current_combo', 'max_combo')
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Score values must be non-negative')
        return v

    @computed_field
    @property
    def total_shots(self) -> int:
        return self.hits + self.misses

    @computed_field
    @property
    def accuracy(self) -> float:
        if self.total_shots == 0:
            return 0.0
        return self.hits / self.total_shots

    model_config = {"frozen": True}
```

### InputSource Interface
```python
from abc import ABC, abstractmethod
from typing import List

class InputSource(ABC):
    """Abstract base class for input sources"""

    @abstractmethod
    def poll_events(self) -> List[InputEvent]:
        """Get new input events since last poll"""
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        """Update source state (for time-based processing)"""
        pass
```

### Target Movement Patterns
1. Linear: constant velocity in one direction
2. Sine wave: oscillating vertical movement
3. Bezier: smooth curved paths
4. Random walk: unpredictable movement

### Coordinate System
- All coordinates in screen space (pixels)
- Origin at top-left (pygame convention)
- Input sources responsible for mapping to screen coordinates
- Game logic works with pixel positions directly

### Performance Targets
- 60 FPS minimum
- Support 10+ simultaneous targets without slowdown
- Input latency < 16ms (one frame)

---

## Testing Strategy

### Unit Testing Requirements

**Coverage Target**: Minimum 80% code coverage for all non-rendering code

**What to Test**:
1. **Pydantic Models** (models.py)
   - All validators work correctly
   - Computed fields calculate correctly
   - Immutability enforcement (frozen models)
   - Edge cases and boundary conditions
   - Type coercion and validation errors

2. **Business Logic** (scoring, target state management, input processing)
   - State transitions
   - Calculations (accuracy, combos, positions)
   - Edge cases (division by zero, empty lists, boundary values)
   - Immutability (functional state updates)

3. **Input System**
   - InputEvent creation and validation
   - InputManager source switching
   - Mock input sources for testing
   - Event ordering and batching

4. **Game Modes** (as much as possible without rendering)
   - Target spawning logic
   - Hit detection algorithms
   - Win/lose condition checking
   - Difficulty progression

**What NOT to Test** (or test minimally):
- Pygame rendering code (visual, hard to unit test)
- Audio playback
- Main game loop (integration test territory)
- User interface interactions (requires pygame display)

### Testing Tools

- **pytest**: Test framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking pygame components
- **hypothesis** (optional): Property-based testing for models

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures (mock screens, sample data)
├── test_models.py           # All Pydantic model tests
├── test_input/              # Input system tests
├── test_game/               # Game logic tests
└── fixtures/                # Test data (sample scores, positions, etc.)
```

### Fixtures and Helpers

Create reusable fixtures in `conftest.py`:
- Sample Vector2D instances (origin, typical positions, edge cases)
- Sample TargetData instances
- Mock pygame surfaces for render tests
- Sample InputEvent batches
- Score progressions for testing

### Testing Pydantic Models

Example test structure:
```python
def test_vector2d_validation():
    # Valid construction
    v = Vector2D(x=10.0, y=20.0)
    assert v.x == 10.0
    assert v.y == 20.0

    # Invalid: negative coordinates
    with pytest.raises(ValidationError):
        Vector2D(x=-10.0, y=20.0)

    # Type coercion
    v = Vector2D(x=10, y=20)  # ints should coerce to floats
    assert isinstance(v.x, float)
```

### Testing Immutability

```python
def test_target_data_immutability():
    target = TargetData(
        position=Vector2D(x=100, y=100),
        velocity=Vector2D(x=50, y=0),
        size=30.0,
        state=TargetState.ALIVE
    )

    # Should not be able to modify
    with pytest.raises(ValidationError):
        target.position = Vector2D(x=200, y=200)
```

### Testing State Updates

```python
def test_score_tracker_immutability():
    tracker = ScoreTracker()

    # record_hit should return NEW instance
    tracker2 = tracker.record_hit()
    assert tracker2 is not tracker
    assert tracker.get_stats().hits == 0  # Original unchanged
    assert tracker2.get_stats().hits == 1  # New instance updated
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run tests matching pattern
pytest -k "test_vector"

# Verbose output
pytest -v
```

### Continuous Testing

- Run tests before every commit
- Use pytest-watch for continuous testing during development
- Set up pre-commit hooks to run tests
- Fail commits if coverage drops below 80%

---

## Development Strategy

### Testing Approach
1. Use mouse input for all initial development
2. Create mock input sources for automated testing
3. Record/replay input sequences for consistency
4. Test each game mode independently

### Implementation Order Priority
1. **Critical Path**: Input abstraction → Target → Classic mode
2. **High Value**: Scoring, visual feedback
3. **Nice to Have**: Additional modes, audio
4. **Future**: Laser pointer integration

### Success Criteria
- [ ] Mouse input works flawlessly
- [ ] Can play full game of Classic mode
- [ ] Hit detection is accurate and responsive
- [ ] Score tracking is correct
- [ ] Can swap input sources without code changes
- [ ] 60 FPS with 10+ targets
- [ ] **All Pydantic models have comprehensive unit tests**
- [ ] **Test coverage >= 80% for non-rendering code**
- [ ] **No runtime ValidationErrors in normal gameplay** (all validation happens at boundaries)
- [ ] Game is fun and engaging (subjective but important!)

---

## Future Integration Points

### Laser Pointer Detection
- OpenCV color blob detection
- HSV color space thresholding
- Calibration for different lighting
- Noise filtering

### Impact Detection
- Integration with parent project's impact detection system
- Homography transformation from camera space to screen space
- Event generation from detected impacts

### Projection System
- Fullscreen projector mode
- Coordinate mapping for different projector resolutions
- Edge blending for large projection surfaces

---

## Notes & Decisions Log

### Design Decisions
1. **Why pygame?** Simple, fast, good for 2D games, easy rendering
2. **Why not game engine?** Want full control, simple requirements, educational value
3. **Input abstraction first?** Yes - core requirement, affects all other code
4. **Start with mouse?** Yes - fastest development cycle, no hardware dependencies
5. **Why Pydantic?** Runtime type validation prevents bugs in Python's loosely-typed environment; clear data contracts; automatic validation; immutability support
6. **Immutable state pattern?** Functional approach with frozen models prevents accidental mutations, easier to test, clearer data flow
7. **Why unit tests?** Catch bugs early, document expected behavior, enable refactoring with confidence, especially important given Python's dynamic typing

### Open Questions
- [ ] Audio library choice? (pygame.mixer vs. alternative)
- [ ] Sprite assets: create custom or use placeholder shapes?
- [ ] Difficulty curve: linear increase or stepped levels?
- [ ] Multi-player support? (Future consideration)

---

## Progress Tracking

**Current Phase**: Phase 1 - Foundation (MVP)
**Completed Deliverables**: 0 / 29 (27 implementation + integrated testing)
**Next Up**: Deliverable 1.1 - Project Setup

### Phase Breakdown
- **Phase 1**: Foundation (MVP) - 5 deliverables
- **Phase 2**: Core Gameplay - 4 deliverables
- **Phase 3**: Feedback & Polish - 3 deliverables
- **Phase 4**: Additional Game Modes - 2 deliverables
- **Phase 5**: Extended Input Sources - 2 deliverables
- **Phase 6**: Configuration & Testing - 2 deliverables

### Testing Deliverables Integrated
Each major component includes test specifications:
- Models testing (in Deliverable 1.2)
- Input system testing (in Deliverable 1.3)
- Target system testing (in Deliverable 1.4)
- Scoring system testing (in Deliverable 2.3)
- Feedback system testing (in Deliverable 3.1)

---

*Last Updated: 2025-10-25*
