"""
AMS Session Manager

The main interface between detection hardware and games.
Coordinates calibration, event routing, and session state.

From AMS.md:
"The AMS sits between Detection and Game layers, providing:
- Calibration Management (run between rounds, invisible to users)
- Temporal Hit Detection Support (games query the past)
- Session Management (scores, progress, player data)
- Event Translation (raw detection → standardized PlaneHitEvents)"

Usage:
    # Initialize AMS with a detection backend
    backend = InputSourceAdapter(mouse_source, 1920, 1080)
    ams = AMSSession(backend)

    # Calibrate (instant for mouse, 3-6s for CV)
    ams.calibrate()

    # Game loop
    while running:
        # Update detection
        ams.update(dt)

        # Get events
        events = ams.poll_events()
        for event in events:
            # Events are PlaneHitEvents with normalized coords
            game.handle_hit(event.x, event.y, event.timestamp)

        # Render
        game.render()

    # Between rounds: recalibrate
    ams.calibrate_between_rounds()  # Fast, invisible
"""

from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
import json
from pathlib import Path

from ams.detection_backend import DetectionBackend
from ams.calibration import CalibrationSession
from ams.events import PlaneHitEvent, CalibrationResult


class AMSSession:
    """
    Main AMS session manager.

    Responsibilities:
    1. Manage detection backend lifecycle
    2. Coordinate calibration workflow
    3. Route events to active game
    4. Maintain session state (scores, progress)
    5. Handle save/load of session data
    """

    def __init__(
        self,
        backend: DetectionBackend,
        session_name: str = "default",
        session_dir: str = "./ams_sessions"
    ):
        """
        Initialize AMS session.

        Args:
            backend: Detection backend to use
            session_name: Name for this session (for save/load)
            session_dir: Directory to store session data
        """
        self.backend = backend
        self.session_name = session_name
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Calibration management
        self.calibration = CalibrationSession(backend)

        # Session state
        self.session_start_time = datetime.now()
        self.total_events = 0
        self.rounds_completed = 0

        # Session data (scores, progress, etc.)
        self.session_data: Dict[str, Any] = {
            'session_name': session_name,
            'start_time': self.session_start_time.isoformat(),
            'backend_type': backend.__class__.__name__,
            'scores': [],
            'metadata': {}
        }

        # Load existing session if available
        self._load_session()

    def update(self, dt: float):
        """
        Update detection backend.

        Call this every frame.

        Args:
            dt: Delta time in seconds since last update
        """
        self.backend.update(dt)

    def poll_events(self) -> List[PlaneHitEvent]:
        """
        Get new detection events since last poll.

        Returns:
            List of PlaneHitEvents in normalized coordinates

        Note:
            Events have already been processed by AMS:
            - Coordinates normalized to [0, 1]
            - Latency corrected (if backend provides latency info)
            - Ready for games to consume
        """
        events = self.backend.poll_events()
        self.total_events += len(events)
        return events

    def calibrate(
        self,
        quick_mode: bool = False,
        progress_callback: Optional[Callable] = None,
        display_surface=None,
        display_resolution=None
    ) -> CalibrationResult:
        """
        Run initial calibration.

        For mouse/keyboard: Returns immediately (no-op)
        For CV/Laser: Full calibration process (ArUco geometric calibration)

        Args:
            quick_mode: Skip optional phases for faster calibration
            progress_callback: Optional callback for progress updates
                Signature: callback(phase: str, progress: float, message: str)
            display_surface: Pygame surface for displaying calibration pattern
            display_resolution: (width, height) of display

        Returns:
            CalibrationResult with available colors and quality metrics
        """
        result = self.calibration.run_calibration(
            quick_mode=quick_mode,
            display_surface=display_surface,
            display_resolution=display_resolution,
            visual_feedback_callback=progress_callback
        )

        # Store calibration result in session data
        self.session_data['last_calibration'] = {
            'timestamp': datetime.now().isoformat(),
            'success': result.success,
            'method': result.method,
            'available_colors': result.available_colors,
            'quality': result.detection_quality
        }

        return result

    def calibrate_between_rounds(
        self,
        progress_callback: Optional[Callable] = None,
        display_surface=None,
        display_resolution=None
    ) -> CalibrationResult:
        """
        Run calibration between game rounds.

        From AMS.md:
        "Always recalibrate between rounds. Lighting changes constantly,
        surface evolves, equipment drifts. Cost is negligible (few seconds,
        integrated as interstitial). Eliminates 'detection degraded over time' failures."

        Visual treatment:
        - Integrated into round transition
        - Color cycling looks like dramatic lighting effect
        - Show score summary, countdown, "Loading next round..."
        - User perceives game polish, not technical calibration

        For mouse/keyboard: Instant (no-op)
        For laser: ArUco geometric recalibration
        For CV: 3-6 seconds, invisible integration

        Args:
            progress_callback: Optional callback for progress updates
            display_surface: Pygame surface for displaying calibration pattern
            display_resolution: (width, height) of display

        Returns:
            CalibrationResult
        """
        self.rounds_completed += 1
        return self.calibrate(
            quick_mode=False,
            progress_callback=progress_callback,
            display_surface=display_surface,
            display_resolution=display_resolution
        )

    def get_available_colors(self) -> Optional[List[tuple]]:
        """
        Get color palette that games should use.

        From AMS.md:
        "Game designs within these constraints (only uses detectable colors).
        Games query AMS for available colors and design graphics accordingly."

        For mouse/keyboard: Returns full palette (no restrictions)
        For CV: Returns only colors with sufficient detection contrast

        Returns:
            List of RGB color tuples, or None if not calibrated
        """
        return self.calibration.get_available_colors()

    def is_calibrated(self) -> bool:
        """
        Check if session is calibrated and ready for use.

        Returns:
            True if calibration has been run successfully
        """
        return self.calibration.is_calibrated()

    def record_score(self, score: int, game_mode: str, metadata: Optional[Dict] = None):
        """
        Record a score for the session.

        Args:
            score: Score value
            game_mode: Name of game mode
            metadata: Optional additional data (round number, difficulty, etc.)
        """
        score_entry = {
            'score': score,
            'game_mode': game_mode,
            'timestamp': datetime.now().isoformat(),
            'round': self.rounds_completed,
            'metadata': metadata or {}
        }

        self.session_data['scores'].append(score_entry)

    def save_session(self):
        """
        Save session data to disk.

        Saves scores, progress, calibration info, etc.
        Called automatically at end of session or can be called manually.
        """
        session_file = self.session_dir / f"{self.session_name}.json"

        # Update summary stats
        self.session_data['total_events'] = self.total_events
        self.session_data['rounds_completed'] = self.rounds_completed
        self.session_data['last_saved'] = datetime.now().isoformat()

        with open(session_file, 'w') as f:
            json.dump(self.session_data, f, indent=2)

    def _load_session(self):
        """Load existing session data if available."""
        session_file = self.session_dir / f"{self.session_name}.json"

        if session_file.exists():
            with open(session_file, 'r') as f:
                loaded_data = json.load(f)

            # Restore session data
            self.session_data = loaded_data
            print(f"Loaded existing session: {self.session_name}")
            print(f"  Previous rounds: {loaded_data.get('rounds_completed', 0)}")
            print(f"  Previous scores: {len(loaded_data.get('scores', []))}")

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of current session.

        Returns:
            Dict with session stats, scores, calibration info
        """
        return {
            'session_name': self.session_name,
            'start_time': self.session_start_time.isoformat(),
            'backend': self.backend.__class__.__name__,
            'calibrated': self.is_calibrated(),
            'total_events': self.total_events,
            'rounds_completed': self.rounds_completed,
            'scores': self.session_data.get('scores', []),
            'available_colors': self.get_available_colors(),
        }

    def __enter__(self):
        """Context manager entry - returns self."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - saves session data."""
        self.save_session()
        return False


if __name__ == "__main__":
    # Example usage
    from ams.detection_backend import DetectionBackend
    from ams.events import CalibrationResult
    import time

    class MockBackend(DetectionBackend):
        def __init__(self):
            super().__init__(1920, 1080)
            self.events = []

        def poll_events(self):
            events = self.events.copy()
            self.events.clear()
            return events

        def update(self, dt):
            pass

        def calibrate(self):
            return CalibrationResult(success=True, method="mock")

    # Create AMS session with context manager (auto-saves)
    print("Creating AMS session...")
    with AMSSession(MockBackend(), session_name="test_session") as ams:

        # Calibrate
        print("\nRunning calibration...")
        result = ams.calibrate()
        print(f"  Success: {result.success}")
        print(f"  Available colors: {len(result.available_colors or [])}")

        # Simulate some game rounds
        for round_num in range(3):
            print(f"\nRound {round_num + 1}")

            # Simulate gameplay
            for frame in range(60):
                ams.update(0.016)  # 60fps

            # Record score
            ams.record_score(
                score=100 * (round_num + 1),
                game_mode="test_mode",
                metadata={'round': round_num + 1}
            )

            # Calibrate between rounds
            if round_num < 2:  # Not after last round
                print("  Calibrating between rounds...")
                ams.calibrate_between_rounds()

        # Get summary
        summary = ams.get_session_summary()
        print(f"\nSession summary:")
        print(f"  Total events: {summary['total_events']}")
        print(f"  Rounds completed: {summary['rounds_completed']}")
        print(f"  Scores: {[s['score'] for s in summary['scores']]}")

    print("\nSession saved automatically on exit")
