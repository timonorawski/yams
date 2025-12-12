# Build stage - compile frontend
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

# Copy package files first for better caching
COPY ams/web_controller/frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy source and build
COPY ams/web_controller/frontend/ ./
RUN npm run build

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic pyyaml

# Create projects directory
RUN mkdir -p /app/data/projects

# Copy built frontend from builder stage
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

# Copy server script
COPY docker/ide-server/server.py /app/server.py

# Create directories for volume mounts
RUN mkdir -p /app/schemas /app/builtins

# Copy schemas and filetypes registry (available even if volumes not mounted)
COPY ams/games/game_engine/lua/lua_script.schema.json /app/schemas/lua_script.schema.json
COPY ams/games/game_engine/schemas/filetypes.json /app/schemas/filetypes.json
COPY ams/games/game_engine/schemas/assets.schema.json /app/schemas/assets.schema.json
COPY ams/games/game_engine/schemas/game.schema.json /app/schemas/game.schema.json
COPY ams/games/game_engine/schemas/level.schema.json /app/schemas/level.schema.json

EXPOSE 8003

CMD ["python", "/app/server.py"]
