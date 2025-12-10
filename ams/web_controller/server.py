"""
FastAPI Web Controller Server for AMS.

Provides HTTP and WebSocket endpoints for mobile control interface.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
import threading
import uvicorn

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

logger = logging.getLogger("ams.web_controller")


@dataclass
class GameState:
    """Current game state for web controller display."""
    game_name: str = "No Game"
    level_name: str = ""
    state: str = "idle"  # idle, playing, paused, retrieval, ended
    score: int = 0
    time_elapsed: float = 0.0
    hits: int = 0
    misses: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SessionInfo:
    """AMS session information."""
    available_games: List[str] = field(default_factory=list)
    game_info: Dict[str, Any] = field(default_factory=dict)  # slug -> {name, description, arguments, levels, level_groups}
    available_backends: List[str] = field(default_factory=lambda: ["mouse", "laser", "object"])
    available_pacings: List[str] = field(default_factory=lambda: ["archery", "throwing", "blaster"])
    current_game: Optional[str] = None
    current_level: Optional[str] = None  # Current level slug
    current_level_group: Optional[str] = None  # Current level group slug
    detection_backend: str = "mouse"
    pacing: str = "throwing"
    calibrated: bool = False


class ConnectionManager:
    """Manages WebSocket connections for real-time state sync."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        if not self.active_connections:
            return

        message_json = json.dumps(message)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(connection)

        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


class WebController:
    """
    Web controller server for AMS mobile interface.

    Runs a FastAPI server in a background thread, providing:
    - Static file serving for Svelte frontend
    - WebSocket endpoint for real-time state sync
    - REST endpoints for commands (future)

    Usage:
        controller = WebController(host="0.0.0.0", port=8080)
        controller.start()

        # Update state (call from game loop)
        controller.update_game_state(GameState(...))

        # Cleanup
        controller.stop()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        static_dir: Optional[Path] = None,
        pygbag_dir: Optional[Path] = None,
    ):
        """
        Initialize web controller.

        Args:
            host: Host to bind to (0.0.0.0 for all interfaces)
            port: Port to serve on
            static_dir: Directory containing frontend static files
            pygbag_dir: Directory containing pygbag WASM build (build/web)
        """
        self.host = host
        self.port = port
        self.static_dir = static_dir or (Path(__file__).parent / "frontend" / "dist")
        # Default pygbag dir - pygbag outputs to build/web/build/web
        project_root = Path(__file__).parent.parent.parent
        self.pygbag_dir = pygbag_dir or (project_root / "build" / "web" / "build" / "web")

        self._app = FastAPI(title="AMS Web Controller")
        self._manager = ConnectionManager()
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # State
        self._game_state = GameState()
        self._session_info = SessionInfo()
        self._command_handlers: Dict[str, Callable] = {}

        self._setup_routes()

    def _setup_routes(self):
        """Configure FastAPI routes."""

        @self._app.get("/")
        async def root():
            """Serve main page (or redirect to static)."""
            # Check if we have a built frontend
            index_path = self.static_dir / "index.html"
            if index_path.exists():
                return HTMLResponse(content=index_path.read_text())

            # Fallback: simple status page
            return HTMLResponse(content=self._get_fallback_html())

        @self._app.get("/play")
        @self._app.get("/play.html")
        async def play_page():
            """Serve Play mode page."""
            play_path = self.static_dir / "play.html"
            if play_path.exists():
                return HTMLResponse(content=play_path.read_text())

            # Fallback for when frontend not built
            return HTMLResponse(content="""
<!DOCTYPE html>
<html><head><title>Play Mode</title></head>
<body style="background:#1a1a2e;color:#eee;font-family:sans-serif;padding:20px;text-align:center;">
<h1 style="color:#00d9ff;">Play Mode</h1>
<p>Frontend not built. Run: cd ams/web_controller/frontend && npm run build</p>
<a href="/" style="color:#00d9ff;">Back to Controller</a>
</body></html>
""")

        @self._app.get("/api/state")
        async def get_state():
            """Get current game state (REST fallback)."""
            return {
                "game": self._game_state.to_dict(),
                "session": asdict(self._session_info),
                "connections": self._manager.connection_count,
                "timestamp": datetime.now().isoformat(),
            }

        @self._app.get("/api/health")
        async def health():
            """Health check endpoint."""
            return {"status": "ok", "connections": self._manager.connection_count}

        @self._app.get("/api/levels/{game_slug}")
        async def get_levels(game_slug: str):
            """Get levels and level groups for a game (for Play mode)."""
            levels = []
            groups = []

            # Try to find levels from game_info in session
            if game_slug in self._session_info.game_info:
                info = self._session_info.game_info[game_slug]
                levels = info.get("levels", [])
                groups = info.get("level_groups", [])

            return {"levels": levels, "groups": groups}

        @self._app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time state sync."""
            await self._manager.connect(websocket)

            # Send initial state on connect
            await websocket.send_text(json.dumps({
                "type": "state",
                "game": self._game_state.to_dict(),
                "session": asdict(self._session_info),
            }))

            try:
                while True:
                    # Receive commands from client
                    data = await websocket.receive_text()
                    await self._handle_command(websocket, data)
            except WebSocketDisconnect:
                self._manager.disconnect(websocket)

        # Mount pygbag WASM files at /pygbag
        if self.pygbag_dir.exists():
            self._app.mount("/pygbag", StaticFiles(directory=self.pygbag_dir), name="pygbag")
            logger.info(f"Serving pygbag from {self.pygbag_dir}")

        # Mount static files if directory exists
        if self.static_dir.exists():
            self._app.mount("/", StaticFiles(directory=self.static_dir), name="static")

    async def _handle_command(self, websocket: WebSocket, data: str):
        """Handle incoming command from WebSocket client."""
        try:
            message = json.loads(data)
            command = message.get("command")
            payload = message.get("payload", {})

            logger.debug(f"Received command: {command} with payload: {payload}")

            # Check for registered handler
            if command in self._command_handlers:
                try:
                    result = self._command_handlers[command](payload)
                    await websocket.send_text(json.dumps({
                        "type": "command_response",
                        "command": command,
                        "success": True,
                        "result": result,
                    }))
                except Exception as e:
                    logger.error(f"Command handler error: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "command_response",
                        "command": command,
                        "success": False,
                        "error": str(e),
                    }))
            else:
                logger.warning(f"Unknown command: {command}")
                await websocket.send_text(json.dumps({
                    "type": "command_response",
                    "command": command,
                    "success": False,
                    "error": f"Unknown command: {command}",
                }))

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON received: {e}")

    def _get_fallback_html(self) -> str:
        """Generate fallback HTML when no frontend is built."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AMS Web Controller</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
        }
        h1 { color: #00d9ff; margin-bottom: 10px; }
        .subtitle { color: #888; margin-bottom: 30px; }
        .card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            width: 100%;
            max-width: 400px;
            margin-bottom: 20px;
        }
        .card h2 {
            color: #00d9ff;
            font-size: 14px;
            text-transform: uppercase;
            margin-bottom: 15px;
            letter-spacing: 1px;
        }
        .state-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #2a2a4a;
        }
        .state-item:last-child { border-bottom: none; }
        .state-label { color: #888; }
        .state-value { color: #fff; font-weight: 600; }
        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status.connected { background: #00c853; color: #000; }
        .status.disconnected { background: #ff5252; color: #fff; }
        .status.idle { background: #666; }
        .status.playing { background: #00d9ff; color: #000; }
        .status.paused { background: #ffab00; color: #000; }
        #connection-status { margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>AMS Web Controller</h1>
    <p class="subtitle">Mobile Control Interface</p>

    <div id="connection-status">
        <span class="status disconnected" id="ws-status">Connecting...</span>
    </div>

    <div class="card">
        <h2>Game State</h2>
        <div class="state-item">
            <span class="state-label">Game</span>
            <span class="state-value" id="game-name">-</span>
        </div>
        <div class="state-item">
            <span class="state-label">Level</span>
            <span class="state-value" id="level-name">-</span>
        </div>
        <div class="state-item">
            <span class="state-label">Status</span>
            <span class="state-value"><span class="status idle" id="game-state">-</span></span>
        </div>
        <div class="state-item">
            <span class="state-label">Score</span>
            <span class="state-value" id="score">0</span>
        </div>
        <div class="state-item">
            <span class="state-label">Hits / Misses</span>
            <span class="state-value"><span id="hits">0</span> / <span id="misses">0</span></span>
        </div>
        <div class="state-item">
            <span class="state-label">Time</span>
            <span class="state-value" id="time">0:00</span>
        </div>
    </div>

    <div class="card">
        <h2>Session Info</h2>
        <div class="state-item">
            <span class="state-label">Backend</span>
            <span class="state-value" id="backend">-</span>
        </div>
        <div class="state-item">
            <span class="state-label">Calibrated</span>
            <span class="state-value" id="calibrated">-</span>
        </div>
        <div class="state-item">
            <span class="state-label">Available Games</span>
            <span class="state-value" id="games-count">0</span>
        </div>
    </div>

    <script>
        let ws;
        let reconnectInterval;

        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onopen = () => {
                console.log('WebSocket connected');
                document.getElementById('ws-status').textContent = 'Connected';
                document.getElementById('ws-status').className = 'status connected';
                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                document.getElementById('ws-status').textContent = 'Disconnected';
                document.getElementById('ws-status').className = 'status disconnected';
                // Reconnect after 2 seconds
                if (!reconnectInterval) {
                    reconnectInterval = setInterval(connect, 2000);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'state') {
                    updateUI(data);
                }
            };
        }

        function updateUI(data) {
            const game = data.game || {};
            const session = data.session || {};

            // Game state
            document.getElementById('game-name').textContent = game.game_name || '-';
            document.getElementById('level-name').textContent = game.level_name || '-';
            document.getElementById('score').textContent = game.score || 0;
            document.getElementById('hits').textContent = game.hits || 0;
            document.getElementById('misses').textContent = game.misses || 0;

            // Format time
            const seconds = Math.floor(game.time_elapsed || 0);
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            document.getElementById('time').textContent = `${mins}:${secs.toString().padStart(2, '0')}`;

            // Game state badge
            const stateEl = document.getElementById('game-state');
            stateEl.textContent = game.state || 'idle';
            stateEl.className = `status ${game.state || 'idle'}`;

            // Session info
            document.getElementById('backend').textContent = session.detection_backend || '-';
            document.getElementById('calibrated').textContent = session.calibrated ? 'Yes' : 'No';
            document.getElementById('games-count').textContent =
                (session.available_games || []).length;
        }

        // Start connection
        connect();
    </script>
</body>
</html>
        """

    def start(self):
        """Start the web controller server in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Web controller already running")
            return

        def run_server():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            config = uvicorn.Config(
                self._app,
                host=self.host,
                port=self.port,
                log_level="warning",
                access_log=False,
            )
            self._server = uvicorn.Server(config)

            logger.info(f"Starting web controller at http://{self.host}:{self.port}")
            self._loop.run_until_complete(self._server.serve())

        self._thread = threading.Thread(target=run_server, daemon=True)
        self._thread.start()

        # Give server a moment to start
        import time
        time.sleep(0.5)

        logger.info(f"Web controller available at http://localhost:{self.port}")

    def stop(self):
        """Stop the web controller server."""
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Web controller stopped")

    def update_game_state(self, state: GameState):
        """
        Update game state and broadcast to connected clients.

        Call this from the game loop to sync state.
        """
        self._game_state = state

        if self._loop and self._manager.connection_count > 0:
            asyncio.run_coroutine_threadsafe(
                self._manager.broadcast({
                    "type": "state",
                    "game": state.to_dict(),
                    "session": asdict(self._session_info),
                }),
                self._loop
            )

    def update_session_info(self, info: SessionInfo):
        """Update session info (available games, backend, etc.)."""
        self._session_info = info

    def register_command(self, command: str, handler: Callable):
        """
        Register a command handler.

        Args:
            command: Command name (e.g., "pause", "resume", "select_game")
            handler: Callback function that takes payload dict and returns result
        """
        self._command_handlers[command] = handler
        logger.debug(f"Registered command handler: {command}")

    @property
    def url(self) -> str:
        """Get the URL to access the web controller."""
        return f"http://{self.host}:{self.port}"

    @property
    def connection_count(self) -> int:
        """Get number of connected WebSocket clients."""
        return self._manager.connection_count
