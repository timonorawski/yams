#!/usr/bin/env python3
"""
Simple development web server for YAMS browser builds.

Serves static files from /app with:
- Proper MIME types (especially for .mjs, .wasm)
- CORS headers for development
- Directory listing
"""

import mimetypes
from pathlib import Path

from aiohttp import web

# Ensure proper MIME types
mimetypes.add_type('application/javascript', '.mjs')
mimetypes.add_type('application/wasm', '.wasm')
mimetypes.add_type('application/json', '.json')
mimetypes.add_type('text/yaml', '.yaml')
mimetypes.add_type('text/yaml', '.yml')

ROOT = Path('/app')


async def cors_middleware(app, handler):
    """Add CORS headers to all responses."""
    async def middleware(request):
        if request.method == 'OPTIONS':
            return web.Response(headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': '*',
            })
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    return middleware


async def serve_file(request):
    """Serve a file or directory listing."""
    path = request.match_info.get('path', '')
    file_path = ROOT / path

    # Security: prevent path traversal
    try:
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(ROOT.resolve())):
            return web.Response(status=403, text='Forbidden')
    except (ValueError, RuntimeError):
        return web.Response(status=400, text='Invalid path')

    if not file_path.exists():
        return web.Response(status=404, text='Not found')

    if file_path.is_dir():
        # Serve directory listing
        index = file_path / 'index.html'
        if index.exists():
            return web.FileResponse(index)

        # Generate directory listing
        items = sorted(file_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        html = f'<html><head><title>Index of /{path}</title></head><body>'
        html += f'<h1>Index of /{path}</h1><ul>'
        if path:
            html += f'<li><a href="/{"/".join(path.split("/")[:-1])}">..</a></li>'
        for item in items:
            name = item.name + ('/' if item.is_dir() else '')
            rel_path = f'{path}/{item.name}' if path else item.name
            html += f'<li><a href="/{rel_path}">{name}</a></li>'
        html += '</ul></body></html>'
        return web.Response(text=html, content_type='text/html')

    # Serve file
    return web.FileResponse(file_path)


def create_app():
    """Create the web application."""
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get('/', serve_file)
    app.router.add_get('/{path:.*}', serve_file)
    return app


if __name__ == '__main__':
    print('YAMS Dev Server starting on http://0.0.0.0:8000')
    print(f'Serving files from: {ROOT}')
    web.run_app(create_app(), host='0.0.0.0', port=8000, print=None)
