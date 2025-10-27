# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **interactive projection targeting system** that uses computer vision to create engaging games for any projectile-based activity. A projector displays targets on a surface, a camera detects impacts, and the system provides real-time feedback.

**Use Cases**: Archery, darts, ball throwing, axe throwing, knife throwing, snowballs, beanbag toss, and any other activity where a projectile hits a visible surface.

**Key Design Philosophy**: Variable practice over repetition—each attempt should be a fresh problem (different position, timing, decision) to build adaptable skill rather than context-dependent muscle memory.

**Architecture Principle**: The core calibration and detection system is completely agnostic to the specific projectile type. Detection methods may vary (color blob detection, motion tracking, impact flash, etc.), but the coordinate mapping and game engine remain the same.

## Architecture

The system has three main components with a specific data flow:

### 1. Calibration System (`/calibration`)
- Projects calibration grid onto target surface
- Detects grid intersections in camera view
- Computes homography transformation between projector space and camera space
- This transformation is critical—all impact detection depends on accurate coordinate mapping
- **Use-case agnostic**: works for any flat surface regardless of projectile type

### 2. Impact Detection (`/impact_detection`)
- Monitors camera feed for projectile impacts on the target surface
- Detection methods are configurable based on projectile characteristics:

  - **Persistence tracking** (easiest): Projectiles that stick to surface (real arrows with points, darts, axes, throwing knives stuck in soft target)
    - Longer dwell time allows for robust blob detection
    - Can use color segmentation for high-vis projectiles

  - **Transient impact** (harder): Projectiles that hit and fall/bounce away (balls, beanbags, snowballs, foam-tip arrows)
    - Object appears, approaches target, impacts (min velocity), then moves away
    - **Two potential approaches**:
      1. **Dual camera setup**: Stereoscopic tracking to measure 3D position/velocity, detect minimum velocity point
      2. **Projected pattern differencing** (recommended, more feasible):
         - **Phase 1** (continuous): Lightweight motion tracking to detect object and calculate velocity
         - **Phase 2** (at impact moment only): Use pattern differencing for precise location
           - Know what's projected (we control it)
           - Use inverse calibration homography to predict what camera should see
           - Detect distortion/occlusion in camera view vs. expected view
           - Extract precise impact coordinates from occlusion
         - **Key optimization**: Expensive pattern warping only runs once per impact, not every frame
         - Similar to structured light scanning techniques
    - Requires higher frame rate camera (60fps+)
    - Computationally feasible with two-phase approach

  - **Motion tracking**: Track projectile flight path and detect intersection with target plane (complex, requires good depth perception)

- Maps detected position to game coordinates using calibration homography
- **Pluggable architecture**: Different detection strategies can be swapped without affecting calibration or game engine
- **Initial implementation**: Start with persistence tracking OR projected pattern differencing (both use calibration differently)

### 3. Game Engine (`/game_engine`)
- Projects targets at random positions
- Receives impact coordinates from detection system
- Provides visual/audio feedback
- Tracks scoring and performance
- **Game-mode agnostic**: doesn't care what created the impact

### Data Flow
```
Calibration → Homography Matrix (one-time setup)
Camera Feed → Impact Detection → Impact Coordinates
Impact Coordinates + Homography → Game Coordinates → Game Engine → Visual Feedback → Projector
```

**Key Insight**: The calibration homography is the foundation. Once established, any detection method can plug in as long as it outputs camera coordinates. The game engine only sees normalized game coordinates and doesn't need to know whether it was an arrow, ball, or snowball.

## Technology Stack

- **Computer Vision**: OpenCV for image processing, blob detection, homography computation
- **Rendering**: pygame or similar for projection display
- **Camera**: 30-60fps webcam or Raspberry Pi camera
- **Python**: Primary language for the entire pipeline

## Development Environment

### Hardware Setup (Current Phase - Backyard Prototype)
- Flat projection surface (~4x4 feet): plywood, foam board, fabric screen, etc.
- Projector positioned to cover target area
- Camera positioned with clear view of target surface
- **Initial testing**: High-visibility foam-tip arrows (easiest detection case)
- **Future testing**: Other projectiles as detection methods expand

### Testing Priorities
1. Calibration accuracy with known reference points
2. Impact visibility and dwell time in camera view (varies by projectile type)
3. Detection reliability at different frame rates and lighting
4. Quick calibration (<30 seconds for practical use)

## Critical Implementation Notes

### Calibration (Use-Case Agnostic)
- The homography transformation is the foundation—everything depends on accurate coordinate mapping
- Test with physical markers (tape on surface) at known positions before impact detection
- Must work in various lighting conditions (indoor, outdoor/daylight)
- Calibration is completely independent of projectile type
- **Dual purpose**:
  1. Map camera detections → game coordinates (all detection methods)
  2. Predict camera view of projected content (for pattern differencing method)

### Impact Detection (Projectile-Specific)
- Detection strategy should be configurable/pluggable based on use case
- **For persistence tracking** (stuck projectiles):
  - Color blob detection for high-vis projectiles
  - 30fps camera sufficient
  - Simple frame differencing
- **For transient impacts** (bouncing projectiles):
  - **Recommended**: Projected pattern differencing
    - Project known pattern, use calibration to predict camera view
    - Detect occlusion/distortion where object blocks pattern
    - Track object position over frames to find minimum velocity (impact moment)
    - Computationally intensive but doesn't require special projectile colors
  - **Alternative**: Dual camera stereoscopic tracking (hardware complexity)
  - Requires 60fps+ camera
  - Higher computational cost
- Lighting conditions affect all detection methods—may need adaptive thresholding

### Coordinate Systems
Three coordinate systems must be precisely mapped:
1. **Projector space**: Where we want to display targets
2. **Camera space**: What the camera observes
3. **Game space**: Logical coordinate system for gameplay

The calibration homography maps between these spaces.

## Current Status

This is an initial prototype phase. The repository will be built from scratch with the calibration system as the first priority. No code exists yet—start with calibration grid projection and detection before implementing impact detection or game logic.

**Initial Use Case**: Archery practice (easiest detection case) - but architecture must remain generic.

## Future Extensions (Not Current Priority)

- Additional detection methods for transient impacts (balls, beanbags)
- Detection for stuck projectiles in soft surfaces (arrows in foam, axes in wood)
- Multiple game modes (timed targets, sequences, cooperative play, multiplayer)
- Performance tracking and progression metrics
- Raspberry Pi portable packaging
- Support for multiple simultaneous projectiles
- Different surface materials and lighting conditions
