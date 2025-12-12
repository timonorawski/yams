# YAMS Web Dev Server
FROM python:3.11-slim

WORKDIR /app

# Install a simple dev server with better defaults
RUN pip install --no-cache-dir aiohttp aiohttp-cors

# Copy the dev server script
COPY docker/web-server/server.py /server.py

EXPOSE 8000

CMD ["python", "/server.py"]
