"""
AMS Calibration Session

Manages the calibration workflow described in AMS.md:
1. Measure display latency (button press → pattern detection)
2. Background characterization (cycle colors, capture statistics)
3. Object characterization (capture projectile under each color)
4. Compute available palette (which colors enable reliable detection)

For mouse/keyboard: All phases return immediately (no-op)
For CV: Full calibration process runs (3-6 seconds, between rounds)

This architecture ensures games work with mouse during development,
then seamlessly transition to CV detection without code changes.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from ams.events import CalibrationResult
from ams.detection_backend import DetectionBackend


class CalibrationSession:
    """
    Manages calibration for a detection backend.

    Calibration philosophy (from AMS.md):
    - Always recalibrate between rounds (not once at startup)
    - Fast enough to be invisible (3-6 seconds during round transition)
    - Adapts to changing conditions (lighting, surface, equipment drift)
    - Simpler than detecting when recalibration is needed

    Visual treatment:
    - Integrated into round transitions as "interstitial"
    - Color cycling looks like dramatic lighting effect
    - Show score summary, countdown, "Loading next round..."
    - User perceives game polish, not technical calibration
    """

    # Standard color palette for testing different projected backgrounds
    CANDIDATE_COLORS = [
        (255, 0, 0),     # Red
        (0, 255, 0),     # Green
        (0, 0, 255),     # Blue
        (255, 255, 0),   # Yellow
        (255, 0, 255),   # Magenta
        (0, 255, 255),   # Cyan
        (255, 128, 0),   # Orange
        (128, 0, 255),   # Purple
        (0, 0, 0),       # Black
        (255, 255, 255), # White
    ]

    def __init__(self, backend: DetectionBackend):
        """
        Initialize calibration session.

        Args:
            backend: Detection backend to calibrate
        """
        self.backend = backend
        self.last_calibration: Optional[CalibrationResult] = None

    def run_calibration(
        self,
        quick_mode: bool = False,
        visual_feedback_callback: Optional[callable] = None,
        display_surface=None,
        display_resolution=None
    ) -> CalibrationResult:
        """
        Run full calibration workflow.

        Args:
            quick_mode: If True, skip optional phases for faster calibration
            visual_feedback_callback: Optional function to call with progress updates
                Signature: callback(phase: str, progress: float, message: str)
            display_surface: Pygame surface for displaying calibration pattern
            display_resolution: (width, height) of display

        Returns:
            CalibrationResult with success status and available palette

        Workflow:
            Phase 1: Display latency measurement (~0.5s)
            Phase 2: Background characterization (~3s)
            Phase 3: Object characterization (~3s)
            Phase 4: Palette computation (~0.1s)

            For mouse/keyboard backends: All phases return immediately
            For laser backend: Runs ArUco geometric calibration
        """
        # Phase 0: Backend-specific calibration (e.g., geometric for CV/Laser)
        self._update_progress(visual_feedback_callback, "init", 0.0, "Starting calibration...")

        # Check if backend supports display-based calibration
        if hasattr(self.backend, 'calibrate') and callable(self.backend.calibrate):
            # Try to pass display parameters if backend supports them
            try:
                import inspect
                sig = inspect.signature(self.backend.calibrate)
                if 'display_surface' in sig.parameters:
                    backend_result = self.backend.calibrate(
                        display_surface=display_surface,
                        display_resolution=display_resolution
                    )
                else:
                    backend_result = self.backend.calibrate()
            except Exception as e:
                print(f"Backend calibration error: {e}")
                backend_result = self.backend.calibrate()
        else:
            backend_result = self.backend.calibrate()

        if not backend_result.success:
            return backend_result

        # Phase 1: Measure display latency
        self._update_progress(visual_feedback_callback, "latency", 0.25, "Measuring display latency...")
        latency_ms = self._measure_display_latency()

        # Phase 2: Background characterization
        if not quick_mode:
            self._update_progress(visual_feedback_callback, "background", 0.5, "Analyzing background...")
            background_stats = self._characterize_background()
        else:
            background_stats = {}

        # Phase 3: Object characterization
        if not quick_mode:
            self._update_progress(visual_feedback_callback, "object", 0.75, "Analyzing projectile...")
            object_stats = self._characterize_object()
        else:
            object_stats = {}

        # Phase 4: Compute available palette
        self._update_progress(visual_feedback_callback, "palette", 0.9, "Computing color palette...")
        available_colors = self._compute_palette(background_stats, object_stats)

        # Done
        self._update_progress(visual_feedback_callback, "complete", 1.0, "Calibration complete!")

        # Create result
        result = CalibrationResult(
            success=True,
            method=f"{backend_result.method}_with_color_calibration",
            available_colors=available_colors,
            display_latency_ms=latency_ms,
            detection_quality=self._estimate_quality(background_stats, object_stats),
            notes=f"Calibrated for {self.backend.__class__.__name__}",
            metadata={
                'backend_result': backend_result.model_dump(),
                'background_stats': background_stats,
                'object_stats': object_stats,
                'quick_mode': quick_mode
            }
        )

        self.last_calibration = result
        return result

    def _measure_display_latency(self) -> Optional[float]:
        """
        Phase 1: Measure display latency.

        Process:
        1. User presses "ready" button → note timestamp
        2. Display calibration pattern → camera detects it appearing
        3. Measure round-trip: display → projector → camera → capture

        For mouse/keyboard: Returns None (no display latency)
        For CV: Returns measured latency in milliseconds

        Returns:
            Latency in milliseconds, or None if not applicable
        """
        # Mouse/keyboard has no display latency
        # CV backends would override this to do actual measurement
        return None

    def _characterize_background(self) -> Dict[str, Any]:
        """
        Phase 2: Background characterization.

        Process:
        1. Point camera at empty projection surface
        2. Cycle through candidate color palette (8-10 colors)
        3. For each color: project it, capture 5-10 frames, compute statistics
        4. Build model: background_appearance[color] = (mean, variance, ...)

        This captures: ambient lighting, surface texture, projection brightness

        For mouse/keyboard: Returns empty dict (no background to characterize)
        For CV: Returns statistics for each color

        Returns:
            Dict mapping color name to statistics
        """
        # Mouse/keyboard doesn't need background characterization
        # CV backends would override this to capture actual statistics
        return {}

    def _characterize_object(self) -> Dict[str, Any]:
        """
        Phase 3: Object characterization.

        Process:
        1. "Hold up your projectile in the projection area"
        2. Cycle through same colors as background
        3. Capture object appearance under each projected color
        4. Build model: object_appearance[color] = (mean, variance, ...)

        For mouse/keyboard: Returns empty dict (no object to characterize)
        For CV: Returns statistics for each color

        Returns:
            Dict mapping color name to statistics
        """
        # Mouse/keyboard doesn't need object characterization
        # CV backends would override this
        return {}

    def _compute_palette(
        self,
        background_stats: Dict[str, Any],
        object_stats: Dict[str, Any]
    ) -> List[tuple]:
        """
        Phase 4: Compute available color palette.

        Process:
        1. For each color, compute detection_quality = contrast(object, background)
        2. Score colors by detection reliability
        3. Return colors that enable reliable object detection

        For mouse/keyboard: Returns full palette (all colors work)
        For CV: Returns only colors with sufficient contrast

        Args:
            background_stats: Statistics from phase 2
            object_stats: Statistics from phase 3

        Returns:
            List of RGB color tuples that are suitable for game use
        """
        # Mouse/keyboard can use any colors
        # CV backends would filter based on actual contrast measurements
        if not background_stats or not object_stats:
            # No restrictions - return full palette
            return self.CANDIDATE_COLORS.copy()

        # TODO: When implementing CV backend:
        # - Compute contrast for each color
        # - Filter to colors with contrast > threshold
        # - Return sorted by detection quality
        return self.CANDIDATE_COLORS.copy()

    def _estimate_quality(
        self,
        background_stats: Dict[str, Any],
        object_stats: Dict[str, Any]
    ) -> Optional[float]:
        """
        Estimate overall calibration quality.

        For mouse/keyboard: Returns 1.0 (perfect)
        For CV: Returns quality score based on measured statistics

        Args:
            background_stats: Statistics from phase 2
            object_stats: Statistics from phase 3

        Returns:
            Quality score [0, 1], or None if not applicable
        """
        if not background_stats or not object_stats:
            return 1.0  # Mouse/keyboard is always perfect

        # TODO: When implementing CV backend:
        # - Analyze variance in measurements
        # - Check if sufficient colors have good contrast
        # - Return quality score
        return 1.0

    def _update_progress(
        self,
        callback: Optional[callable],
        phase: str,
        progress: float,
        message: str
    ):
        """
        Send progress update to callback if provided.

        Args:
            callback: Optional progress callback function
            phase: Current calibration phase name
            progress: Progress value [0, 1]
            message: Human-readable progress message
        """
        if callback:
            callback(phase, progress, message)

    def get_available_colors(self) -> Optional[List[tuple]]:
        """
        Get available color palette from last calibration.

        Games should query this and design their graphics using only
        these colors for reliable detection.

        Returns:
            List of RGB color tuples, or None if no calibration run yet
        """
        if self.last_calibration:
            return self.last_calibration.available_colors
        return None

    def is_calibrated(self) -> bool:
        """
        Check if calibration has been run.

        Returns:
            True if calibration has been run successfully
        """
        return self.last_calibration is not None and self.last_calibration.success


if __name__ == "__main__":
    # Example: Calibrate with a mock backend
    from ams.detection_backend import DetectionBackend

    class MockBackend(DetectionBackend):
        def poll_events(self):
            return []

        def update(self, dt):
            pass

        def calibrate(self):
            return CalibrationResult(
                success=True,
                method="mock",
                notes="Mock backend for testing"
            )

    # Create calibration session
    backend = MockBackend(1920, 1080)
    session = CalibrationSession(backend)

    # Progress callback for visual feedback
    def progress_callback(phase, progress, message):
        bar = "=" * int(progress * 20)
        print(f"[{bar:<20}] {progress:3.0%} - {phase}: {message}")

    # Run calibration
    print("Running calibration...")
    result = session.run_calibration(visual_feedback_callback=progress_callback)

    print(f"\nCalibration result:")
    print(f"  Success: {result.success}")
    print(f"  Method: {result.method}")
    print(f"  Available colors: {len(result.available_colors or [])}")
    print(f"  Display latency: {result.display_latency_ms}ms")
    print(f"  Quality: {result.detection_quality}")

    # Get available colors
    colors = session.get_available_colors()
    if colors:
        print(f"\nGames can use these colors:")
        for i, color in enumerate(colors[:5]):  # Show first 5
            print(f"  Color {i}: RGB{color}")
