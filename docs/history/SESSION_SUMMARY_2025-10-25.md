---
archived: 2024-12-07
original_date: 2025-10-25
status: historical
summary: >
  Development session summary documenting the initial creation of the calibration
  system and establishment of core architectural principles. This was the founding
  session that established use-case agnostic design and Pydantic data models.
key_decisions:
  - Use-case agnostic architecture (not just archery)
  - Pydantic for all data models
  - ArUco markers for calibration
  - Two-phase detection approach for transient impacts
---

# Development Session Summary - October 25, 2025

> **Note**: This is a historical document capturing the founding development session.
> The decisions made here shaped the entire project architecture.

## Session Overview

**Objective**: Initialize repository documentation and build a working calibration system prototype for an interactive projection targeting system.

**Duration**: Initial planning through successful hardware calibration test

**Status**: ✅ Complete - Calibration system functional and tested with hardware

---

## Phase 1: Repository Initialization and Architecture Definition

### Initial Request
User requested `/init` to analyze the codebase and create CLAUDE.md documentation for future Claude Code sessions.

### Key Discovery: Use-Case Generalization Needed

**Initial Context**: README.md described project as "Archery Training Projection System"

**Critical Pivot**: User identified that archery is just ONE potential use case:
- Ball hits target on wall
- Darts
- Axe throwing
- Throwing knives
- Snowballs
- Bean bags in living room
- Any projectile hitting a visible surface

**Decision**: Architecture must be completely use-case agnostic. No hardcoded assumptions about projectile type.

### Architectural Principle Established

> "The core calibration and detection system is completely agnostic to the specific projectile type. Detection methods may vary (color blob detection, motion tracking, impact flash, etc.), but the coordinate mapping and game engine remain the same."

This became the foundational design constraint for all subsequent decisions.

---

## Phase 2: Calibration System Planning

### Problem Statement

Build a reusable OpenCV-based calibration pipeline that establishes a one-time geometric transformation between:
- **Projector coordinate space** (what we display)
- **Camera coordinate space** (what we observe)
- **Game coordinate space** (logical gameplay coordinates)

**Key Insight**: Since camera and target surface are **fixed after setup**, we perform calibration once and store the transformation. No real-time pattern analysis needed during gameplay.

### Critical Decision: Pydantic for Data Structures

**User Requirement**: "When internal datastructures are required, we should have formal datastructure definitions -- since we may have need for serialization for inter-process communication in the future, pydantic seems like a reasonable choice"

**Rationale**:
- Type safety and validation at runtime
- Built-in JSON serialization (no pickle security issues)
- Clean APIs with IDE autocomplete
- Enables future multi-process architecture
- Language-agnostic (JSON messages)

**Impact**: All data models implemented as Pydantic classes from the start, not as afterthought.

---

## Phase 3: Impact Detection Strategy Evolution

### Initial Understanding: Simple Blob Detection

Early assumption was transient impacts (foam-tip arrows, balls) could be detected with simple frame-by-frame differencing.

### Breakthrough: Projected Pattern Differencing

**User Insight**: "For transient impacts, it's object appears, gets closer to target, then moves away -- the location of least velocity is the impact location."

**Follow-up Insight**: "I'm not sure that one's possible to be accurate without two cameras - or capturing the frame that is supposed to be on screen at that moment, mapping it to the coordinate transformation based on viewpoint, and identifying where the object distorts the picture"

**This changed everything.**

### Decision: Two-Phase Detection Approach

**Problem**: Full pattern differencing (warping projector frame to predict camera view) is computationally expensive (~100ms/frame at 60fps = unusable).

**Solution**: User clarified: "That detection method is computationally intensive, but only needs to be run when the moment of least velocity is detected to extract the impact location"

**Final Architecture**:

**Phase 1** (runs every frame, ~2ms):
- Lightweight motion detection (background subtraction)
- Track object position history
- Calculate velocity
- Detect minimum velocity moment (impact)

**Phase 2** (runs once per impact, ~50ms):
- Use inverse homography to predict what camera should see: `H_proj_to_cam = inv(H_cam_to_proj)`
- Warp projector frame to camera view
- Detect occlusion (where object blocks projected pattern)
- Extract precise impact coordinates

**Performance**: 60fps × 2ms + 50ms once per impact = **usable at 60fps**

---

## Phase 6: Hardware Testing

### Test Setup
- Projector: 1920x1080 resolution
- Camera: 1920x1080 resolution
- Target: Projection surface visible to both
- Grid: 4x4 ArUco markers (16 total)

### Results

**Detection**: ✅ Perfect
- 16/16 markers detected
- 16/16 markers matched
- 100% inlier ratio

**Calibration Quality**: ✅ Excellent
- RMS error: **0.25 pixels** (target was <3.0)
- Max error: **0.42 pixels**
- Sub-pixel accuracy achieved

---

## Key Documents Created

1. CLAUDE.md - Claude Code context file
2. CALIBRATION_SYSTEM_PLAN.md - Technical architecture
3. GETTING_STARTED.md - User guide
4. requirements.txt - Dependencies

---

## Architecture Decisions Summary

### ✅ Decisions That Proved Correct

1. **Use-case agnostic design**: Enables any projectile type without refactoring
2. **Pydantic from the start**: Saved time, provided safety, clean APIs
3. **Modular architecture**: Each component testable independently
4. **Two-phase detection**: Makes transient impact detection computationally feasible
5. **Dual-purpose homography**: Camera→Game AND Projector→Camera transforms
6. **ArUco markers**: Robust, sub-pixel accurate, well-supported by OpenCV
7. **Automatic persistence**: Calibration history management prevents data loss

---

**Session Date**: October 25, 2025
**Status**: Complete
**Next Session**: Impact Detection Implementation
