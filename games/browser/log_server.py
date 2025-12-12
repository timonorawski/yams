#!/usr/bin/env python3
"""
WebSocket Log Server for AMS Browser Development

Collects logs from the browser via WebSocket and makes them available
via HTTP for debugging.

Usage:
    python games/browser/log_server.py [--port 8001]

The browser connects via WebSocket and sends log entries.
Claude can fetch logs via HTTP GET /logs/<build_id>

Endpoints:
    WS  /           - WebSocket for receiving logs
    GET /logs       - List all build IDs with log counts
    GET /logs/<id>  - Get logs for a specific build ID
    DELETE /logs    - Clear all logs
"""

import argparse
import asyncio
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    import websockets
    from aiohttp import web
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


# In-memory log storage: build_id -> list of log entries
logs: Dict[str, List[dict]] = defaultdict(list)

# Keep only last N entries per build to prevent memory issues
MAX_LOGS_PER_BUILD = 5000

# File persistence
LOG_DIR: Optional[Path] = None
log_files: Dict[str, Path] = {}


def init_log_dir(log_dir: Path) -> None:
    """Initialize log directory for file persistence."""
    global LOG_DIR
    LOG_DIR = log_dir
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Log files: {LOG_DIR.absolute()}")


def write_log_to_file(build_id: str, entry: dict) -> None:
    """Append a log entry to the build's log file."""
    if LOG_DIR is None:
        return

    if build_id not in log_files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_files[build_id] = LOG_DIR / f"{build_id}_{timestamp}.jsonl"

    with open(log_files[build_id], "a") as f:
        f.write(json.dumps(entry) + "\n")


async def websocket_handler(websocket):
    """Handle WebSocket connections from browser."""
    build_id = "unknown"
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                build_id = data.get("build_id", "unknown")
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "level": data.get("level", "INFO"),
                    "source": data.get("source", "unknown"),
                    "message": data.get("message", ""),
                }

                # Store log entry (memory + file)
                logs[build_id].append(entry)
                write_log_to_file(build_id, entry)

                # Trim old entries from memory (file keeps all)
                if len(logs[build_id]) > MAX_LOGS_PER_BUILD:
                    logs[build_id] = logs[build_id][-MAX_LOGS_PER_BUILD:]

            except json.JSONDecodeError:
                # Plain text message
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "source": "raw",
                    "message": message,
                }
                logs[build_id].append(entry)
                write_log_to_file(build_id, entry)
    except websockets.exceptions.ConnectionClosed:
        pass


async def http_list_logs(request):
    """List all build IDs with log counts."""
    result = {
        build_id: {
            "count": len(entries),
            "first": entries[0]["timestamp"] if entries else None,
            "last": entries[-1]["timestamp"] if entries else None,
        }
        for build_id, entries in logs.items()
    }
    return web.json_response(result)


async def http_get_logs(request):
    """Get logs for a specific build ID."""
    build_id = request.match_info["build_id"]

    # Query params
    limit = int(request.query.get("limit", 500))
    offset = int(request.query.get("offset", 0))
    level = request.query.get("level", None)  # Filter by level
    source = request.query.get("source", None)  # Filter by source
    search = request.query.get("search", None)  # Search in message

    if build_id not in logs:
        return web.json_response({"error": "Build ID not found"}, status=404)

    entries = logs[build_id]

    # Apply filters
    if level:
        entries = [e for e in entries if e["level"].upper() == level.upper()]
    if source:
        entries = [e for e in entries if source.lower() in e["source"].lower()]
    if search:
        entries = [e for e in entries if search.lower() in e["message"].lower()]

    # Apply pagination
    total = len(entries)
    entries = entries[offset:offset + limit]

    return web.json_response({
        "build_id": build_id,
        "total": total,
        "offset": offset,
        "limit": limit,
        "entries": entries,
    })


async def http_clear_logs(request):
    """Clear all logs."""
    logs.clear()
    return web.json_response({"status": "cleared"})


async def http_clear_build_logs(request):
    """Clear logs for a specific build."""
    build_id = request.match_info["build_id"]
    if build_id in logs:
        del logs[build_id]
    return web.json_response({"status": "cleared", "build_id": build_id})


async def start_servers(host: str, ws_port: int, http_port: int):
    """Start both WebSocket and HTTP servers."""

    # HTTP server for log retrieval
    app = web.Application()
    app.router.add_get("/logs", http_list_logs)
    app.router.add_get("/logs/{build_id}", http_get_logs)
    app.router.add_delete("/logs", http_clear_logs)
    app.router.add_delete("/logs/{build_id}", http_clear_build_logs)

    # Add CORS headers
    async def cors_middleware(app, handler):
        async def middleware(request):
            if request.method == "OPTIONS":
                return web.Response(headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                })
            response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
        return middleware

    app.middlewares.append(cors_middleware)

    runner = web.AppRunner(app)
    await runner.setup()
    http_site = web.TCPSite(runner, host, http_port)

    # WebSocket server
    ws_server = await websockets.serve(websocket_handler, host, ws_port)

    print(f"Log Server Started")
    print(f"  WebSocket: ws://{host}:{ws_port}")
    print(f"  HTTP API:  http://{host}:{http_port}/logs")
    print(f"")
    print(f"Browser should connect to WebSocket and POST logs.")
    print(f"Fetch logs: GET http://localhost:{http_port}/logs/<build_id>")
    print(f"")

    await http_site.start()
    await asyncio.Future()  # Run forever


def main():
    if not HAS_DEPS:
        print("Missing dependencies. Install with:")
        print("  pip install websockets aiohttp")
        return 1

    parser = argparse.ArgumentParser(description="AMS Log Server")
    parser.add_argument("--host", type=str, default="localhost", help="Host to bind to (use 0.0.0.0 for Docker)")
    parser.add_argument("--ws-port", type=int, default=8001, help="WebSocket port")
    parser.add_argument("--http-port", type=int, default=8002, help="HTTP API port")
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("data/logs/browser"),
        help="Directory to store log files (default: data/logs/browser)"
    )
    parser.add_argument(
        "--no-file",
        action="store_true",
        help="Disable file logging (memory only)"
    )
    args = parser.parse_args()

    # Initialize file logging unless disabled
    if not args.no_file:
        init_log_dir(args.log_dir)

    try:
        asyncio.run(start_servers(args.host, args.ws_port, args.http_port))
    except KeyboardInterrupt:
        print("\nShutting down...")

    return 0


if __name__ == "__main__":
    exit(main())
