# YAMS Log Server
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir websockets aiohttp

# Expose WebSocket and HTTP ports
EXPOSE 8001 8002

# Run log server (bind to 0.0.0.0 for Docker networking)
CMD ["python", "games/browser/log_server.py", \
     "--host", "0.0.0.0", \
     "--ws-port", "8001", \
     "--http-port", "8002", \
     "--log-dir", "/app/data/logs/browser"]
