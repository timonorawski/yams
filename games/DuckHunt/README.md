# Duck Hunt Style Game with Abstracted Input Layer

## Project Context
Building a projection-based interactive game system where physical actions (thrown objects, laser pointers, arrows) generate coordinate-based input events. Need a working game to validate the full pipeline and test user engagement.

## Immediate Goal
Create a Duck Hunt inspired game in pygame with clean input abstraction so we can swap input sources (laser pointer detection, impact detection, mouse clicks) without changing game logic.

## Technical Requirements

### Input Abstraction Layer
Create an `InputEvent` class/system that represents:
- x, y coordinates (in screen/projection space)
- timestamp
- event type (hit, miss, etc.)

The game should accept events from ANY source that can generate (x, y, timestamp) tuples:
- Mouse clicks (for development/testing)
- Webcam detecting laser pointer
- Future: impact detection from thrown objects
- Future: arrow position detection

**Critical**: Game logic should NEVER directly call mouse/keyboard handlers. All input comes through the abstraction layer.

### Game Mechanics (Duck Hunt Style)
- Targets appear at random positions on screen
- Targets move across screen (optional: vary speed/pattern)
- Player "shoots" by generating input event at target location
- Hit detection: was the input coordinate within target bounds?
- Score tracking: hits/misses, maybe accuracy percentage
- Visual feedback: target reacts to hit (disappear, explosion, etc.)
- Audio feedback: hit sound, miss sound (optional but nice)
- Progressive difficulty: targets get faster, smaller, or more numerous

### Game Modes to Support
Start with simple mode, but architecture should allow:
1. **Classic**: Targets appear and move, player shoots
2. **Stationary Flash**: Targets appear briefly then disappear (tests reaction + memory)
3. **Sequence**: Hit targets in specific order (tests decision making)
4. Future: Whatever else we want to add

### Code Structure