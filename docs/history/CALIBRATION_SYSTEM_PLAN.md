---
archived: 2024-12-07
original_date: 2025-10-25
status: implemented
summary: >
  Original planning document for the ArUco-based geometric calibration system.
  This system has been fully implemented in /calibration/ with excellent results
  (0.25px RMS error achieved in hardware testing).
superseded_by:
  - /calibration/ (implementation)
  - /docs/guides/GETTING_STARTED.md (user guide)
---

# Calibration System Planning Document

> **Note**: This is a historical planning document. The calibration system described here
> has been fully implemented. See `/calibration/` for the actual implementation and
> `/docs/guides/GETTING_STARTED.md` for current usage instructions.

## Core Problem Statement

Build a reusable OpenCV-based calibration pipeline that establishes a one-time geometric transformation between:
- **Projector coordinate space** (what we display)
- **Camera coordinate space** (what we observe)
- **Game coordinate space** (logical gameplay coordinates)

Since the camera and target surface are **fixed after setup**, we perform calibration once and store the transformation matrices for runtime use. Real-time image analysis of projected content is unnecessary and wasteful.

**Use-Case Agnostic**: This calibration system works for any projectile-based targeting game (archery, darts, ball throwing, axe throwing, etc.). The detection methods may vary, but the coordinate transformation remains the same.

## Coordinate Systems

### 1. Game Space (Normalized)
- Logical coordinate system: `(0, 0)` to `(1, 1)`
- Origin at top-left, normalized to projection area dimensions
- Game engine thinks in these coordinates
- Resolution-independent, portable across different projector/camera setups

### 2. Projector Space (Pixels)
- Projector's native resolution (e.g., 1920x1080)
- What gets rendered to the display buffer
- Mapped from game space via simple scaling

### 3. Camera Space (Pixels)
- Camera's native resolution (e.g., 1280x720)
- What the camera observes
- Impact detection happens in this space
- Mapped to game space via homography transformation

### 4. Physical Space (Real World)
- Not directly used in software, but conceptually important
- The actual physical target surface (plywood, foam board, fabric, wall, etc.)
- Both projector and camera view this from different angles

## Implementation Status

**IMPLEMENTED** - See `/calibration/` directory:
- `pattern_generator.py` - ArUco grid generation
- `pattern_detector.py` - Marker detection with sub-pixel accuracy
- `homography.py` - RANSAC-based homography computation
- `calibration_manager.py` - High-level API

**Hardware Test Results** (October 25, 2025):
- 16/16 markers detected
- RMS error: 0.25 pixels (target was <3.0)
- Max error: 0.42 pixels
- 100% inlier ratio

The remainder of this document contains the original planning details for historical reference.
