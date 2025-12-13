"""
AMS Web Controller Integration

Integrates the web controller with AMS for real game launching and control.
"""

import pygame
import os
import sys
import time
import socket
import threading
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum, auto

from .server import WebController, GameState, SessionInfo
from ams.logging import get_logger

log = get_logger('web_integration')


def get_local_ips() -> List[str]:
    """Get all local IP addresses for this machine."""
    ips = []
    try:
        # Get all network interfaces
        hostname = socket.gethostname()
        # Get all IPs associated with hostname
        try:
            host_ips = socket.gethostbyname_ex(hostname)[2]
            ips.extend(host_ips)
        except socket.gaierror:
            pass

        # Also try connecting to external address to find primary IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            s.close()
            if primary_ip not in ips:
                ips.insert(0, primary_ip)
        except Exception:
            pass

    except Exception:
        pass

    # Filter out localhost
    ips = [ip for ip in ips if not ip.startswith('127.')]
    return ips if ips else ['localhost']


def get_mdns_hostname() -> Optional[str]:
    """Get the mDNS hostname (.local) if available."""
    try:
        hostname = socket.gethostname()
        # On macOS/Linux, the .local suffix is typically available
        if not hostname.endswith('.local'):
            hostname = f"{hostname}.local"
        # Verify it resolves
        socket.gethostbyname(hostname)
        return hostname
    except Exception:
        return None


class ControllerState(Enum):
    """State of the AMS controller."""
    IDLE = auto()
    CALIBRATING = auto()
    GAME_RUNNING = auto()
    GAME_PAUSED = auto()
    RETRIEVAL = auto()


@dataclass
class BackendConfig:
    """Configuration for a detection backend."""
    backend_type: str  # 'mouse', 'laser', 'object'
    camera_id: int = 0
    brightness: int = 200
    # Additional backend-specific config can be added here


class AMSWebIntegration:
    """
    Integrates WebController with AMS for real game control.

    This class manages:
    - Web controller server lifecycle
    - Backend creation and switching
    - Game launching and state management
    - Real-time state broadcasting

    Usage:
        integration = AMSWebIntegration(screen, display_resolution)
        integration.start()

        # Main loop
        while integration.running:
            integration.update(dt)
            # ... render current game or idle screen

        integration.stop()
    """

    def __init__(
        self,
        screen: pygame.Surface,
        display_resolution: tuple,
        host: str = "0.0.0.0",
        port: int = 8080,
    ):
        """
        Initialize AMS web integration.

        Args:
            screen: Pygame display surface
            display_resolution: (width, height) tuple
            host: Web server host
            port: Web server port
        """
        self.screen = screen
        self.display_width, self.display_height = display_resolution

        # Web controller
        self.web_controller = WebController(host=host, port=port)

        # State
        self.state = ControllerState.IDLE
        self.running = True
        self._stop_requested = False

        # Backend configuration
        self.backend_config = BackendConfig(backend_type='mouse')
        self.detection_backend = None
        self.ams_session = None
        self.calibrated = False

        # Pacing configuration
        self.pacing = 'throwing'  # archery, throwing, blaster

        # Current game
        self.current_game = None
        self.current_game_name: Optional[str] = None
        self.input_manager = None
        self.game_start_time: Optional[float] = None

        # Game registry
        self._registry = None

        # Cache network info (already enumerated before fullscreen)
        self._cached_ips: Optional[List[str]] = None
        self._cached_mdns: Optional[str] = None

        # Register command handlers
        self._register_commands()

    def _register_commands(self):
        """Register web controller command handlers."""
        self.web_controller.register_command('set_backend', self._handle_set_backend)
        self.web_controller.register_command('set_pacing', self._handle_set_pacing)
        self.web_controller.register_command('calibrate', self._handle_calibrate)
        self.web_controller.register_command('launch_game', self._handle_launch_game)
        self.web_controller.register_command('stop_game', self._handle_stop_game)
        self.web_controller.register_command('pause', self._handle_pause)
        self.web_controller.register_command('resume', self._handle_resume)
        self.web_controller.register_command('retrieval', self._handle_retrieval)
        self.web_controller.register_command('game_action', self._handle_game_action)

    @property
    def registry(self):
        """Lazy-load game registry."""
        if self._registry is None:
            from games.registry import get_registry
            self._registry = get_registry()
        return self._registry

    def start(self):
        """Start the web controller server."""
        self.web_controller.start()
        log.info(f"Web controller available at: {self.web_controller.url}")

        # Initialize with mouse backend (no calibration needed)
        self._create_backend('mouse')

        # Update initial session info
        self._update_session_info()

    def stop(self):
        """Stop the web controller and cleanup."""
        self._stop_requested = True
        self.running = False

        if self.current_game:
            self._cleanup_game()

        if self.detection_backend:
            self._cleanup_backend()

        self.web_controller.stop()

    def update(self, dt: float) -> bool:
        """
        Update the integration.

        Args:
            dt: Delta time in seconds

        Returns:
            True if should continue running, False to exit
        """
        if self._stop_requested:
            return False

        # Update AMS if active
        if self.ams_session:
            self.ams_session.update(dt)

        # Update current game if running
        if self.current_game and self.state in (ControllerState.GAME_RUNNING, ControllerState.GAME_PAUSED, ControllerState.RETRIEVAL):
            self._update_game(dt)

        # Broadcast current state
        self._broadcast_state()

        return self.running

    def handle_pygame_events(self, events: list) -> bool:
        """
        Handle pygame events.

        Only handles system events (QUIT) and specific keyboard shortcuts.
        All other events (especially mouse events) are re-posted to the queue
        so the game's input system can consume them.

        Args:
            events: List of pygame events

        Returns:
            True if should continue, False to quit
        """
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.current_game:
                        self._handle_stop_game({})
                    else:
                        self.running = False
                        return False

                elif event.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()

                elif event.key == pygame.K_d:
                    # Toggle debug mode on backend
                    if self.detection_backend and hasattr(self.detection_backend, 'set_debug_mode'):
                        debug = getattr(self.detection_backend, 'debug_mode', False)
                        self.detection_backend.set_debug_mode(not debug)
                else:
                    # Re-post other key events for the game
                    pygame.event.post(event)

            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                # Re-post mouse events for the game's input system
                pygame.event.post(event)

        return True

    def render(self):
        """Render current state to screen."""
        if self.current_game and self.state != ControllerState.IDLE:
            # Game is rendering itself
            self.current_game.render(self.screen)
        else:
            # Show idle screen
            self._render_idle_screen()

        pygame.display.flip()

        # Show debug visualization if enabled
        if self.detection_backend and hasattr(self.detection_backend, 'debug_mode') and self.detection_backend.debug_mode:
            debug_frame = self.detection_backend.get_debug_frame()
            if debug_frame is not None:
                import cv2
                cv2.imshow("Detection Debug", debug_frame)
                cv2.waitKey(1)

    def _render_idle_screen(self):
        """Render the idle/waiting screen."""
        self.screen.fill((26, 26, 46))  # Dark blue background

        font_large = pygame.font.Font(None, 72)
        font_medium = pygame.font.Font(None, 36)
        font_small = pygame.font.Font(None, 24)
        font_url = pygame.font.Font(None, 32)

        # Title
        title = font_large.render("AMS Controller", True, (0, 217, 255))
        title_rect = title.get_rect(center=(self.display_width // 2, 80))
        self.screen.blit(title, title_rect)

        # Connection URLs - show actual IPs when bound to 0.0.0.0
        port = self.web_controller.port
        y_offset = 140

        # Use cached network info (enumerated before fullscreen to avoid hidden prompts)
        if self._cached_mdns is None:
            self._cached_mdns = get_mdns_hostname() or ""
        if self._cached_ips is None:
            self._cached_ips = get_local_ips()

        # Try mDNS hostname first (most user-friendly)
        if self._cached_mdns:
            url_text = font_url.render(f"http://{self._cached_mdns}:{port}", True, (0, 217, 255))
            url_rect = url_text.get_rect(center=(self.display_width // 2, y_offset))
            self.screen.blit(url_text, url_rect)
            y_offset += 35

        # Show IP addresses
        for ip in self._cached_ips[:3]:  # Limit to 3 IPs to avoid clutter
            url_text = font_small.render(f"http://{ip}:{port}", True, (180, 180, 180))
            url_rect = url_text.get_rect(center=(self.display_width // 2, y_offset))
            self.screen.blit(url_text, url_rect)
            y_offset += 25

        y_offset += 10

        # Status
        status_text = f"Backend: {self.backend_config.backend_type.upper()}"
        if self.calibrated:
            status_text += " (Calibrated)"
        else:
            status_text += " (Not Calibrated)"

        status = font_small.render(status_text, True, (150, 150, 150))
        status_rect = status.get_rect(center=(self.display_width // 2, y_offset))
        self.screen.blit(status, status_rect)
        y_offset += 25

        # Connection count
        conn_text = f"Connected devices: {self.web_controller.connection_count}"
        conn = font_small.render(conn_text, True, (150, 150, 150))
        conn_rect = conn.get_rect(center=(self.display_width // 2, y_offset))
        self.screen.blit(conn, conn_rect)
        y_offset += 50

        # Available games
        games_title = font_medium.render("Available Games:", True, (0, 217, 255))
        games_rect = games_title.get_rect(center=(self.display_width // 2, y_offset))
        self.screen.blit(games_title, games_rect)
        y_offset += 45

        for game_slug in self.registry.list_games():
            info = self.registry.get_game_info(game_slug)
            if info:
                game_text = font_small.render(f"• {info.name}", True, (200, 200, 200))
                game_rect = game_text.get_rect(center=(self.display_width // 2, y_offset))
                self.screen.blit(game_text, game_rect)
                y_offset += 28

        # Instructions
        instructions = font_small.render("Open URL on your phone to control", True, (100, 100, 100))
        inst_rect = instructions.get_rect(center=(self.display_width // 2, self.display_height - 50))
        self.screen.blit(instructions, inst_rect)

    def _update_game(self, dt: float):
        """Update the current game."""
        if not self.current_game or not self.input_manager:
            return

        # Skip updates if paused or retrieval
        if self.state == ControllerState.GAME_PAUSED:
            return

        if self.state == ControllerState.RETRIEVAL:
            # In retrieval mode, just render but don't update game logic
            return

        # Update input manager (this updates AMS internally)
        self.input_manager.update(dt)

        # Get input events and pass to game
        input_events = self.input_manager.get_events()
        self.current_game.handle_input(input_events)

        # Update game
        self.current_game.update(dt)

        # Check game over
        from ams.games import GameState as GS
        if self.current_game.state == GS.GAME_OVER:
            log.info(f"GAME OVER! Final Score: {self.current_game.get_score()}")
            self._handle_stop_game({})
        elif hasattr(GS, 'WON') and self.current_game.state == GS.WON:
            log.info(f"YOU WIN! Final Score: {self.current_game.get_score()}")
            self._handle_stop_game({})

    def _broadcast_state(self):
        """Broadcast current state to web clients."""
        # Map controller state to web state
        state_map = {
            ControllerState.IDLE: 'idle',
            ControllerState.CALIBRATING: 'calibrating',
            ControllerState.GAME_RUNNING: 'playing',
            ControllerState.GAME_PAUSED: 'paused',
            ControllerState.RETRIEVAL: 'retrieval',
        }

        # Get game stats
        score = 0
        hits = 0
        misses = 0
        elapsed = 0.0
        level_name = ""
        available_actions = []

        if self.current_game:
            score = self.current_game.get_score() if hasattr(self.current_game, 'get_score') else 0
            hits = getattr(self.current_game, 'hits', 0)
            misses = getattr(self.current_game, 'misses', 0)
            if self.game_start_time:
                elapsed = time.time() - self.game_start_time

            # Get current level name if available
            if hasattr(self.current_game, 'current_level_name'):
                level_name = self.current_game.current_level_name or ""

            # Get available actions
            if hasattr(self.current_game, 'get_available_actions'):
                available_actions = self.current_game.get_available_actions()

        game_state = GameState(
            game_name=self.current_game_name or "No Game",
            level_name=level_name,
            state=state_map.get(self.state, 'idle'),
            score=score,
            time_elapsed=elapsed,
            hits=hits,
            misses=misses,
            extra={'actions': available_actions},
        )

        self.web_controller.update_game_state(game_state)

    def _update_session_info(self):
        """Update session info for web clients."""
        available_games = self.registry.list_games()

        # Build game info dict with arguments for config UI
        game_info = {}
        for slug in available_games:
            info = self.registry.get_game_info(slug)
            game_class = self.registry.get_game_class(slug)
            if info:
                # Get arguments and convert Python types to strings for JSON
                raw_args = game_class.get_arguments() if game_class else []
                json_args = []
                for arg in raw_args:
                    json_arg = dict(arg)
                    # Convert Python type to string name
                    if 'type' in json_arg and not isinstance(json_arg['type'], str):
                        type_obj = json_arg['type']
                        json_arg['type'] = type_obj.__name__ if hasattr(type_obj, '__name__') else str(type_obj)
                    json_args.append(json_arg)

                # Get level info if game has levels
                levels = []
                level_groups = []
                if game_class and hasattr(game_class, 'LEVELS_DIR') and game_class.LEVELS_DIR:
                    levels, level_groups = self._get_game_level_info(game_class)

                game_info[slug] = {
                    'name': info.name,
                    'description': info.description,
                    'arguments': json_args,
                    'has_levels': bool(levels or level_groups),
                    'levels': levels,
                    'level_groups': level_groups,
                }

        # Get current level info from running game
        current_level = None
        current_level_group = None
        if self.current_game:
            if hasattr(self.current_game, 'current_level_slug'):
                current_level = self.current_game.current_level_slug
            if hasattr(self.current_game, 'current_group') and self.current_game.current_group:
                current_level_group = self.current_game.current_group.slug

        session_info = SessionInfo(
            available_games=available_games,
            game_info=game_info,
            current_game=self.current_game_name,
            current_level=current_level,
            current_level_group=current_level_group,
            detection_backend=self.backend_config.backend_type,
            pacing=self.pacing,
            calibrated=self.calibrated,
        )

        self.web_controller.update_session_info(session_info)

    def _get_game_level_info(self, game_class) -> tuple:
        """Get level and level group info for a game class.

        Returns:
            Tuple of (levels_list, level_groups_list)
        """
        levels = []
        level_groups = []

        try:
            # Create a temporary loader to enumerate levels
            from ams.games.levels import SimpleLevelLoader

            levels_dir = game_class.LEVELS_DIR
            if not levels_dir or not levels_dir.exists():
                return levels, level_groups

            loader = SimpleLevelLoader(levels_dir)

            # Get individual levels
            for slug in loader.list_levels():
                info = loader.get_level_info(slug)
                if info:
                    levels.append({
                        'slug': slug,
                        'name': info.name,
                        'description': info.description,
                        'difficulty': info.difficulty,
                        'author': info.author,
                    })

            # Get level groups
            for slug in loader.list_groups():
                info = loader.get_level_info(slug)
                if info:
                    level_groups.append({
                        'slug': slug,
                        'name': info.name,
                        'description': info.description,
                        'levels': info.levels,  # List of level slugs in this group
                        'level_count': len(info.levels),
                    })

        except Exception as e:
            log.warning(f"Failed to enumerate levels for {game_class.NAME}: {e}")

        return levels, level_groups

    # Command handlers

    def _handle_set_backend(self, payload: dict) -> dict:
        """Handle set_backend command."""
        backend_type = payload.get('backend', 'mouse')

        if backend_type not in ('mouse', 'laser', 'object'):
            return {'error': f'Unknown backend: {backend_type}'}

        if self.current_game:
            return {'error': 'Cannot change backend while game is running'}

        log.info(f"Switching backend to: {backend_type}")

        # Cleanup old backend
        if self.detection_backend:
            self._cleanup_backend()

        # Create new backend
        self._create_backend(backend_type)
        self._update_session_info()

        return {'backend': backend_type, 'calibrated': self.calibrated}

    def _handle_set_pacing(self, payload: dict) -> dict:
        """Handle set_pacing command."""
        pacing = payload.get('pacing', 'throwing')

        if pacing not in ('archery', 'throwing', 'blaster'):
            return {'error': f'Unknown pacing: {pacing}'}

        if self.current_game:
            return {'error': 'Cannot change pacing while game is running'}

        log.info(f"Setting pacing to: {pacing}")
        self.pacing = pacing
        self._update_session_info()

        return {'pacing': pacing}

    def _handle_calibrate(self, payload: dict) -> dict:
        """Handle calibrate command."""
        if self.current_game:
            return {'error': 'Cannot calibrate while game is running'}

        if self.backend_config.backend_type == 'mouse':
            # Mouse doesn't need calibration
            self.calibrated = True
            self._update_session_info()
            return {'calibrated': True, 'message': 'Mouse backend needs no calibration'}

        log.info("Running calibration...")
        self.state = ControllerState.CALIBRATING

        try:
            result = self.ams_session.calibrate(
                display_surface=self.screen,
                display_resolution=(self.display_width, self.display_height)
            )

            self.calibrated = result.success
            log.info(f"Calibration complete! Success: {result.success}")

        except Exception as e:
            log.error(f"Calibration error: {e}")
            self.calibrated = False

        self.state = ControllerState.IDLE
        self._update_session_info()

        return {'calibrated': self.calibrated}

    def _handle_launch_game(self, payload: dict) -> dict:
        """Handle launch_game command.

        Payload can include:
        - game: Game slug (required)
        - config: Dict of game-specific config options
        - level: Level slug to load (can also be in config)
        - level_group: Level group slug to play through (can also be in config)
        """
        game_slug = payload.get('game', '').lower()
        config = payload.get('config', {})

        # level and level_group can be at top level or inside config
        level = payload.get('level') or config.get('level')
        level_group = payload.get('level_group') or config.get('level_group')

        if not game_slug:
            return {'error': 'No game specified'}

        if game_slug not in self.registry.list_games():
            return {'error': f'Unknown game: {game_slug}'}

        if self.current_game:
            self._cleanup_game()

        # Merge pacing into config (config can override if user changed it)
        game_kwargs = {'pacing': self.pacing}
        game_kwargs.update(config)

        # Add level/level_group to kwargs if specified
        if level:
            game_kwargs['level'] = level
        if level_group:
            game_kwargs['level_group'] = level_group

        log.info(f"Launching game: {game_slug} with config: {game_kwargs}")

        try:
            # Create game instance with config
            self.current_game = self.registry.create_game(
                game_slug,
                self.display_width,
                self.display_height,
                **game_kwargs
            )

            # Create input manager
            self.input_manager = self.registry.create_input_manager(
                game_slug,
                self.ams_session,
                self.display_width,
                self.display_height
            )

            self.current_game_name = game_slug
            self.game_start_time = time.time()
            self.state = ControllerState.GAME_RUNNING

            self._update_session_info()

            # Include level info in response
            result = {'game': game_slug, 'status': 'launched'}
            if hasattr(self.current_game, 'current_level_slug') and self.current_game.current_level_slug:
                result['level'] = self.current_game.current_level_slug
            if hasattr(self.current_game, 'current_group') and self.current_game.current_group:
                result['level_group'] = self.current_game.current_group.slug

            return result

        except Exception as e:
            log.exception(f"Failed to launch game: {e}")
            self.current_game = None
            self.current_game_name = None
            return {'error': str(e)}

    def _handle_stop_game(self, payload: dict) -> dict:
        """Handle stop_game command."""
        if not self.current_game:
            return {'status': 'no_game_running'}

        game_name = self.current_game_name
        self._cleanup_game()
        self._update_session_info()

        return {'status': 'stopped', 'game': game_name}

    def _handle_pause(self, payload: dict) -> dict:
        """Handle pause command."""
        if self.state == ControllerState.GAME_RUNNING:
            self.state = ControllerState.GAME_PAUSED
            return {'state': 'paused'}
        return {'state': self._state_name()}

    def _handle_resume(self, payload: dict) -> dict:
        """Handle resume command."""
        if self.state in (ControllerState.GAME_PAUSED, ControllerState.RETRIEVAL):
            self.state = ControllerState.GAME_RUNNING
            return {'state': 'playing'}
        return {'state': self._state_name()}

    def _handle_retrieval(self, payload: dict) -> dict:
        """Handle retrieval command."""
        if self.state in (ControllerState.GAME_RUNNING, ControllerState.GAME_PAUSED):
            self.state = ControllerState.RETRIEVAL
            return {'state': 'retrieval'}
        return {'state': self._state_name()}

    def _handle_game_action(self, payload: dict) -> dict:
        """Handle game_action command."""
        action_id = payload.get('action')
        if not action_id:
            return {'error': 'No action specified'}

        if not self.current_game:
            return {'error': 'No game running'}

        if hasattr(self.current_game, 'execute_action'):
            success = self.current_game.execute_action(action_id)
            return {'action': action_id, 'success': success}

        return {'error': 'Game does not support actions'}

    def _state_name(self) -> str:
        """Get current state name for responses."""
        state_map = {
            ControllerState.IDLE: 'idle',
            ControllerState.CALIBRATING: 'calibrating',
            ControllerState.GAME_RUNNING: 'playing',
            ControllerState.GAME_PAUSED: 'paused',
            ControllerState.RETRIEVAL: 'retrieval',
        }
        return state_map.get(self.state, 'unknown')

    # Backend management

    def _create_backend(self, backend_type: str):
        """Create a detection backend."""
        from ams.session import AMSSession
        from ams.detection_backend import InputSourceAdapter
        from input.sources.mouse import MouseInputSource

        self.backend_config.backend_type = backend_type

        if backend_type == 'mouse':
            mouse_input = MouseInputSource()
            self.detection_backend = InputSourceAdapter(
                mouse_input,
                self.display_width,
                self.display_height
            )
            self.calibrated = True  # Mouse is always "calibrated"

        elif backend_type == 'laser':
            try:
                from ams.camera import OpenCVCamera
                from ams.laser_detection_backend import LaserDetectionBackend
                from calibration.calibration_manager import CalibrationManager
                from models import CalibrationConfig

                camera = OpenCVCamera(camera_id=self.backend_config.camera_id)

                # Try to load existing calibration
                calibration_manager = None
                calib_path = "calibration.json"
                if os.path.exists(calib_path):
                    try:
                        calibration_manager = CalibrationManager(CalibrationConfig())
                        calibration_manager.load_calibration(calib_path)
                        self.calibrated = True
                        log.info(f"Loaded existing calibration from {calib_path}")
                    except Exception as e:
                        log.warning(f"Could not load calibration: {e}")
                        self.calibrated = False
                else:
                    self.calibrated = False

                self.detection_backend = LaserDetectionBackend(
                    camera=camera,
                    calibration_manager=calibration_manager,
                    display_width=self.display_width,
                    display_height=self.display_height,
                    brightness_threshold=self.backend_config.brightness
                )

            except Exception as e:
                log.error(f"Failed to create laser backend: {e}, falling back to mouse")
                self._create_backend('mouse')
                return

        elif backend_type == 'object':
            try:
                from ams.camera import OpenCVCamera
                from ams.object_detection_backend import ObjectDetectionBackend
                from ams.object_detection import ColorBlobDetector, ColorBlobConfig, ImpactMode
                from calibration.calibration_manager import CalibrationManager
                from models import CalibrationConfig

                camera = OpenCVCamera(camera_id=self.backend_config.camera_id)

                # Try to load existing calibration
                calibration_manager = None
                calib_path = "calibration.json"
                if os.path.exists(calib_path):
                    try:
                        calibration_manager = CalibrationManager(CalibrationConfig())
                        calibration_manager.load_calibration(calib_path)
                        self.calibrated = True
                        log.info(f"Loaded existing calibration from {calib_path}")
                    except Exception as e:
                        log.warning(f"Could not load calibration: {e}")
                        self.calibrated = False
                else:
                    self.calibrated = False

                # Default color blob config
                blob_config = ColorBlobConfig(
                    hue_min=0,
                    hue_max=15,
                    saturation_min=100,
                    saturation_max=255,
                    value_min=100,
                    value_max=255,
                    min_area=50,
                    max_area=2000,
                )
                detector = ColorBlobDetector(blob_config)

                self.detection_backend = ObjectDetectionBackend(
                    camera=camera,
                    detector=detector,
                    calibration_manager=calibration_manager,
                    display_width=self.display_width,
                    display_height=self.display_height,
                    impact_mode=ImpactMode.TRAJECTORY_CHANGE,
                    velocity_change_threshold=100.0,
                    direction_change_threshold=90.0,
                    min_impact_velocity=50.0,
                )

            except Exception as e:
                log.error(f"Failed to create object backend: {e}, falling back to mouse")
                self._create_backend('mouse')
                return

        # Create AMS session
        self.ams_session = AMSSession(
            backend=self.detection_backend,
            session_name="web_controlled_session"
        )

        log.info(f"Backend created: {backend_type}")

    def _cleanup_backend(self):
        """Clean up current backend."""
        if self.detection_backend:
            if hasattr(self.detection_backend, 'camera'):
                self.detection_backend.camera.release()

            # Close debug windows
            if self.backend_config.backend_type in ('laser', 'object'):
                try:
                    import cv2
                    cv2.destroyAllWindows()
                except:
                    pass

        self.detection_backend = None
        self.ams_session = None
        self.calibrated = False

    def _cleanup_game(self):
        """Clean up current game."""
        if self.current_game:
            # Record final score if AMS session exists
            if self.ams_session and hasattr(self.current_game, 'get_score'):
                self.ams_session.record_score(
                    self.current_game.get_score(),
                    self.current_game_name or "unknown",
                    {}
                )

        self.current_game = None
        self.current_game_name = None
        self.input_manager = None
        self.game_start_time = None
        self.state = ControllerState.IDLE
