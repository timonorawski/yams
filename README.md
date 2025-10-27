# Archery Training Projection System - Initial Prototype

## Project Context
Building a portable system that projects interactive archery games onto target surfaces. The goal is to create engaging, variable practice scenarios that train first-shot accuracy and adaptive shooting rather than static target grouping. This approach emphasizes motor learning through novel problems rather than repetitive execution.

### Long-term Vision
- Portable range setup: Raspberry Pi, camera, projector, car battery
- Detects arrows in foam buttress during calibration rounds
- Projects randomized/moving targets for varied practice
- Open-source system others can build and extend
- Scales from backyard use (kids learning) to advanced training

### Design Philosophy
Variable practice over repetition. Each shot should be a fresh problem—different position, timing, or decision requirement. This builds adaptable skill rather than context-dependent muscle memory. Static targets and grouping practice come later; first-shot accuracy under varied conditions is the foundation.

## Current Goal: Backyard Prototype
Build and test core calibration and detection system in controlled environment before dealing with range logistics.

### Hardware Setup (Testing Phase)
- Plywood board as projection surface (~4x4 feet, mounted vertically)
- Projector positioned on ground, projecting upward onto plywood
- Camera (webcam or Pi camera) positioned near projector
- High-visibility foam-tip arrows (bright orange/pink for easy detection)

### Technical Requirements - Phase 1

**Calibration System:**
1. Project a calibration grid onto plywood surface
2. Detect grid intersections in camera view
3. Compute homography transformation between:
   - Projector coordinate space (what we want to display)
   - Camera coordinate space (what we observe)
4. Store transformation for real-time use

**Impact Detection:**
1. Monitor camera feed for high-vis arrow impacts
2. Detect either:
   - Sudden appearance of colored blob (if arrow dwells on surface)
   - Arrow crossing into projection plane (flight tracking)
   - Whichever proves more reliable in testing
3. Map detected position to game coordinate space using calibration
4. Register hit and provide visual feedback

**Simple Game Mode (POC):**
- Project colored circle target at random position
- Detect arrow impact
- Provide immediate visual/audio feedback on hit
- Display next target after brief delay
- Track basic scoring (hits/attempts)

### Code Organization Suggestions
```
/calibration
  - grid_projection.py (generate and display calibration pattern)
  - detection.py (find grid intersections in camera view)
  - homography.py (compute and store coordinate transformation)

/arrow_detection  
  - impact_detector.py (watch for arrow hits)
  - color_segmentation.py (isolate high-vis arrows)
  
/game_engine
  - target_generator.py (random positioning, timing)
  - renderer.py (draw game elements in projector space)
  - scoring.py (track performance)
  
/main.py (orchestrate calibration -> game loop)
```

### Testing Priorities
1. **Calibration accuracy**: Can we reliably map coordinates? Test with known reference points on plywood
2. **Arrow visibility**: Do foam tips dwell long enough for detection? Review camera footage
3. **Detection reliability**: What frame rate and color thresholds work in backyard lighting?
4. **Game engagement**: Is the feedback loop actually fun/motivating?

### Technical Notes
- OpenCV for computer vision pipeline
- Simple pygame or similar for projection rendering
- Assume 30-60fps camera, adjust if needed
- Start with daylight/outdoor lighting conditions
- Calibration should be quick (under 30 seconds) to encourage actual use

### Future Extensions (Not Now)
- Arrow detection for range use with arrows stuck in foam buttress
- Multiple game modes (timed targets, sequences, cooperative play)
- Performance tracking and progression metrics
- Raspberry Pi packaging for portable range setup

## Immediate Next Step
Build calibration system that can accurately map between camera and projector coordinates. Test with physical markers (tape on plywood at known positions) before worrying about arrow detection.

Focus on getting the coordinate transformation right—everything else depends on this working reliably.