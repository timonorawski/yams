# YAMS Docker Development Environment

Local development setup with nginx, web server, and log server.

## Quick Start

```bash
# Start all services
docker compose up

# Start in background
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Services

| Service | Internal Port | Description |
|---------|---------------|-------------|
| nginx | 80 → 8080 | Reverse proxy, single entry point |
| web-server | 8000 | Static file server for browser builds |
| log-server | 8001 (WS), 8002 (HTTP) | WebSocket log collector |

## Access Points

All access through nginx on `http://localhost:8080`:

| URL | Target |
|-----|--------|
| `http://localhost:8080/` | Web server (static files) |
| `ws://localhost:8080/ws` | Log WebSocket |
| `http://localhost:8080/api/logs` | Log HTTP API |

## Configuration

Copy `.env.example` to `.env` to customize:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `NGINX_PORT` | 8080 | External port for nginx |
| `LOG_DIR` | ./data/logs | Directory for log file output |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                    Browser                       │
└──────────────────────┬──────────────────────────┘
                       │ :8080
┌──────────────────────▼──────────────────────────┐
│                    nginx                         │
│  /        → web-server:8000                     │
│  /ws      → log-server:8001 (WebSocket)         │
│  /api/logs → log-server:8002 (HTTP)             │
└──────┬─────────────────────────────┬────────────┘
       │                             │
┌──────▼──────┐             ┌───────▼───────┐
│ web-server  │             │  log-server   │
│ :8000       │             │ :8001 (WS)    │
│ Static files│             │ :8002 (HTTP)  │
└─────────────┘             └───────────────┘
       │                             │
       └──────────┬──────────────────┘
                  │
         ┌───────▼────────┐
         │   /app (volume)│
         │   Shared code  │
         └────────────────┘
```

## Development Workflow

1. Edit code locally (volume mounted)
2. Browser connects to `localhost:8080`
3. Logs stream via WebSocket to log-server
4. Query logs: `curl localhost:8080/api/logs`
