---
archived: 2024-12-07
original_date: 2025-10-27
status: partially_implemented
summary: >
  Planning document for CV detection backends. Phase 0 (Laser Backend) was fully
  implemented. Phases 1-4 (full CV with pattern differencing) remain unimplemented.
  The Object Detection backend was implemented using a different approach (velocity
  tracking + impact detection) rather than the pattern differencing described here.
implemented:
  - Phase 0: Laser pointer backend (/ams/laser_detection_backend.py)
  - Camera interface (/ams/camera.py)
  - Object detection backend (/ams/object_detection_backend.py) - different approach
not_implemented:
  - Color characterization system
  - Pattern differencing detection
  - Interstitial calibration UX
superseded_by:
  - /ams/laser_detection_backend.py
  - /ams/object_detection_backend.py
  - /ams/object_detection/ (pluggable detectors)
---

# CV Detection Backend Implementation Plan

> **Note**: This is a historical planning document. Phase 0 (laser backend) was
> implemented as planned. The object detection backend took a different approach
> using velocity-based impact detection rather than pattern differencing.

**Status**: Partially Implemented
**Date**: October 27, 2025
**Prerequisites**: AMS architecture validated with mouse input, geometric calibration system working

---

## Executive Summary

This document plans the implementation of the CV Detection Backend for the Arcade Management System (AMS). This will enable real computer vision-based impact detection for transient projectiles (foam-tip arrows, balls, beanbags) using the interstitial calibration approach described in AMS.md.

### Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Laser Pointer Backend | ✅ Implemented |
| Phase 1 | Color Characterization | ❌ Not implemented |
| Phase 2 | CV Detection Backend | ⚠️ Different approach taken |
| Phase 3 | Interstitial Calibration UX | ❌ Not implemented |
| Phase 4 | Integration and Testing | ✅ Done for actual implementation |

### What Was Actually Built

Instead of the pattern differencing approach described in this plan, the actual implementation uses:

1. **LaserDetectionBackend** (`/ams/laser_detection_backend.py`)
   - Brightness threshold detection
   - Works exactly as Phase 0 describes

2. **ObjectDetectionBackend** (`/ams/object_detection_backend.py`)
   - Color blob detection (HSV filtering)
   - Velocity tracking
   - Two impact modes:
     - TRAJECTORY_CHANGE: Detects bouncing objects via velocity/direction change
     - STATIONARY: Detects objects that stop moving

3. **Pluggable Detector System** (`/ams/object_detection/`)
   - `base.py` - ObjectDetector abstract class
   - `color_blob.py` - ColorBlobDetector implementation
   - `config.py` - Configuration dataclasses

The pattern differencing approach (using inverse homography to predict camera view) remains unimplemented but could be added as another pluggable detector.

---

The remainder of this document contains the original planning details for historical reference
and potential future implementation of the pattern differencing approach.
