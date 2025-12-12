"""
AMS IDE Server - File API and static file serving for the game editor.

Provides:
- Static file serving for the built frontend
- File API for reading/writing user projects
- Schema serving for Monaco validation

Environment variables:
- IDE_PROJECTS_DIR: Directory for user projects (default: /app/data/projects)
- IDE_PORT: Server port (default: 8003)
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AMS IDE Server")

# Configuration
PROJECTS_DIR = Path(os.environ.get("IDE_PROJECTS_DIR", "/app/data/projects"))
FRONTEND_DIR = Path("/app/frontend/dist")
SCHEMAS_DIR = Path("/app/schemas")
BUILTINS_DIR = Path("/app/builtins")

# Ensure projects directory exists
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


class FileContent(BaseModel):
    content: str


class ProjectCreate(BaseModel):
    name: str
    template: Optional[str] = "blank"


# ============================================================================
# Schema API
# ============================================================================

@app.get("/api/schemas/{schema_name:path}")
async def get_schema(schema_name: str):
    """Serve JSON schemas for Monaco validation.

    Supports fragment references like 'assets.schema.json#sprite' which returns
    the subschema at $defs/sprite wrapped as a standalone schema.
    """
    # Handle fragment references (e.g., assets.schema.json#sprite)
    fragment = None
    if '#' in schema_name:
        schema_name, fragment = schema_name.split('#', 1)

    schema_path = SCHEMAS_DIR / schema_name

    if not schema_path.exists():
        raise HTTPException(status_code=404, detail=f"Schema not found: {schema_name}")

    schema = json.loads(schema_path.read_text())

    # If fragment specified, extract the subschema
    if fragment:
        defs = schema.get('$defs', schema.get('definitions', {}))
        if fragment not in defs:
            raise HTTPException(status_code=404, detail=f"Schema fragment not found: #{fragment}")

        # Return subschema with $defs included for internal references
        subschema = defs[fragment].copy()
        subschema['$schema'] = schema.get('$schema', 'http://json-schema.org/draft-07/schema#')
        subschema['$id'] = f"{schema.get('$id', '')}#{fragment}"
        if '$defs' not in subschema and defs:
            subschema['$defs'] = defs
        schema = subschema

    return JSONResponse(
        content=schema,
        media_type="application/schema+json"
    )


@app.get("/api/schemas")
async def list_schemas():
    """List available schemas."""
    schemas = []
    if SCHEMAS_DIR.exists():
        schemas.extend([f.name for f in SCHEMAS_DIR.glob("*.json") if f.name != "filetypes.json"])
    return {"schemas": schemas}


@app.get("/api/filetypes")
async def get_filetypes():
    """Get file type registry for the IDE (schemas, templates, file matching patterns)."""
    filetypes_path = SCHEMAS_DIR / "filetypes.json"

    if not filetypes_path.exists():
        return {"filetypes": []}

    data = json.loads(filetypes_path.read_text())
    return {"filetypes": data.get("filetypes", [])}


# ============================================================================
# Built-in Scripts API (read-only)
# ============================================================================

@app.get("/api/builtins")
async def list_builtins():
    """List all built-in Lua scripts by category."""
    categories = {}

    if not BUILTINS_DIR.exists():
        return {"categories": categories}

    for category_dir in BUILTINS_DIR.iterdir():
        if category_dir.is_dir():
            scripts = []
            for script_file in sorted(category_dir.glob("*.lua.yaml")):
                scripts.append({
                    "name": script_file.stem.replace(".lua", ""),
                    "filename": script_file.name,
                    "path": f"{category_dir.name}/{script_file.name}"
                })
            if scripts:
                categories[category_dir.name] = scripts

    return {"categories": categories}


@app.get("/api/builtins/{category}/{filename}")
async def read_builtin(category: str, filename: str):
    """Read a built-in script (read-only)."""
    script_path = BUILTINS_DIR / category / filename

    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Script not found")

    # Security: ensure file is within builtins directory
    try:
        script_path.resolve().relative_to(BUILTINS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "category": category,
        "filename": filename,
        "content": script_path.read_text(),
        "readonly": True
    }


# ============================================================================
# Projects API
# ============================================================================

@app.get("/api/projects")
async def list_projects():
    """List all user projects."""
    projects = []
    if PROJECTS_DIR.exists():
        for p in PROJECTS_DIR.iterdir():
            if p.is_dir() and (p / "game.yaml").exists():
                projects.append({
                    "name": p.name,
                    "path": str(p.relative_to(PROJECTS_DIR)),
                    "modified": (p / "game.yaml").stat().st_mtime
                })
    return {"projects": sorted(projects, key=lambda x: x["modified"], reverse=True)}


@app.post("/api/projects")
async def create_project(project: ProjectCreate):
    """Create a new project."""
    project_dir = PROJECTS_DIR / project.name

    if project_dir.exists():
        raise HTTPException(status_code=409, detail="Project already exists")

    project_dir.mkdir(parents=True)
    (project_dir / "levels").mkdir()
    (project_dir / "lua" / "behaviors").mkdir(parents=True)

    # Create default game.yaml
    game_yaml = f"""name: {project.name}
description: A new AMS game

screen_width: 800
screen_height: 600
background_color: [30, 30, 46]

entity_types:
  target:
    width: 50
    height: 50
    color: red
    health: 1
    points: 10
    tags: [target]

default_layout:
  entities:
    - type: target
      x: 400
      y: 300
"""
    (project_dir / "game.yaml").write_text(game_yaml)

    return {"name": project.name, "path": str(project_dir.relative_to(PROJECTS_DIR))}


@app.delete("/api/projects/{project_name}")
async def delete_project(project_name: str):
    """Delete a project."""
    project_dir = PROJECTS_DIR / project_name

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    import shutil
    shutil.rmtree(project_dir)

    return {"deleted": project_name}


# ============================================================================
# File API
# ============================================================================

@app.get("/api/projects/{project_name}/files")
async def list_files(project_name: str, path: str = ""):
    """List files in a project directory."""
    project_dir = PROJECTS_DIR / project_name
    target_dir = project_dir / path if path else project_dir

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    if not target_dir.exists():
        raise HTTPException(status_code=404, detail="Directory not found")

    files = []
    for item in sorted(target_dir.iterdir()):
        rel_path = str(item.relative_to(project_dir))
        files.append({
            "name": item.name,
            "path": rel_path,
            "type": "folder" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None
        })

    return {"files": files, "path": path}


@app.get("/api/projects/{project_name}/files/{file_path:path}")
async def read_file(project_name: str, file_path: str):
    """Read a file from a project."""
    project_dir = PROJECTS_DIR / project_name
    target_file = project_dir / file_path

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    if not target_file.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not target_file.is_file():
        raise HTTPException(status_code=400, detail="Path is a directory")

    # Security: ensure file is within project directory
    try:
        target_file.resolve().relative_to(project_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return {"path": file_path, "content": target_file.read_text()}


@app.put("/api/projects/{project_name}/files/{file_path:path}")
async def write_file(project_name: str, file_path: str, body: FileContent):
    """Write/create a file in a project."""
    project_dir = PROJECTS_DIR / project_name
    target_file = project_dir / file_path

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    # Security: ensure file is within project directory
    try:
        target_file.resolve().relative_to(project_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    # Create parent directories if needed
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(body.content)

    logger.info(f"Saved file: {project_name}/{file_path}")

    return {"path": file_path, "saved": True}


@app.delete("/api/projects/{project_name}/files/{file_path:path}")
async def delete_file(project_name: str, file_path: str):
    """Delete a file from a project."""
    project_dir = PROJECTS_DIR / project_name
    target_file = project_dir / file_path

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    if not target_file.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Security: ensure file is within project directory
    try:
        target_file.resolve().relative_to(project_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if target_file.is_dir():
        import shutil
        shutil.rmtree(target_file)
    else:
        target_file.unlink()

    return {"path": file_path, "deleted": True}


# ============================================================================
# Static files (frontend)
# ============================================================================

# Serve author.html at /author
@app.get("/author")
@app.get("/author.html")
async def serve_author():
    """Serve the IDE frontend."""
    author_html = FRONTEND_DIR / "author.html"
    if not author_html.exists():
        raise HTTPException(status_code=404, detail="Frontend not built. Run: npm run build")
    return FileResponse(author_html)


# Mount static assets
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "projects_dir": str(PROJECTS_DIR)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("IDE_PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)
