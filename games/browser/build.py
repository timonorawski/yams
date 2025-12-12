#!/usr/bin/env python3
"""
Pygbag Build Script for AMS Games

Builds pygame games for browser deployment via WebAssembly.

Usage:
    python games/browser/build.py [--dev] [--output DIR]

Options:
    --dev       Start development server (auto-reload)
    --output    Output directory (default: build/web)
    --port      Dev server port (default: 8000)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import yaml  # Required for build process (converts YAML to JSON)


# Project structure
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
BROWSER_DIR = SCRIPT_DIR
GAMES_DIR = PROJECT_ROOT / "games"
BUILD_DIR = PROJECT_ROOT / "build" / "web"

# Browser-compatible games (BaseGame games + YAML games)
# SweetPhysics excluded - pymunk not available in WASM
BROWSER_GAMES = [
    # Python/BaseGame games
    "BalloonPop",
    "Containment",
    "DuckHunt",
    "FruitSlice",
    "Gradient",
    "Grouping",
    "GrowingTargets",
    "LoveOMeter",
    "ManyTargets",
]

# YAML-only games (use GameEngine, require WASMOON for Lua behaviors)
# These are the "NG" (Next Generation) versions using game.yaml
# SweetPhysicsNG excluded - pymunk not available in WASM
YAML_GAMES = [
    "BrickBreakerNG",
    "LoveOMeterNG",
    # "DuckHuntNG",      # Enable when tested
    # "FruitSliceNG",    # Enable when tested
    # "GroupingNG",      # Enable when tested
    # "RopeTestNG",      # Enable when tested
]

# Files/directories to include in the build
INCLUDE_PATTERNS = [
    # Browser runtime
    "games/browser/*.py",
    # Common game infrastructure
    "games/common/**/*.py",
    "games/registry.py",
    # Models
    "models/**/*.py",
]

# Files to exclude from build
EXCLUDE_PATTERNS = [
    "**/__pycache__/**",
    "**/*.pyc",
    "**/test_*.py",
    "**/tests/**",
    "**/.pytest_cache/**",
]


def find_pygbag() -> str:
    """Find pygbag executable."""
    # Try python -m pygbag
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pygbag", "--version"],
            capture_output=True,
            text=True,
        )
        # pygbag returns non-zero even for --version, so check if output contains version
        if "pygbag" in result.stdout or "pygbag" in result.stderr:
            return f"{sys.executable} -m pygbag"
    except Exception:
        pass

    # Try direct pygbag command
    if shutil.which("pygbag"):
        return "pygbag"

    raise RuntimeError(
        "pygbag not found. Install with: pip install pygbag"
    )


def prepare_build_dir(output_dir: Path):
    """
    Prepare build directory with necessary files.

    Pygbag expects a specific structure:
    - main.py at the root (entry point)
    - All dependencies in the same directory tree
    """
    print(f"Preparing build directory: {output_dir}")

    # Clean and create output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Copy main.py to root (pygbag requirement)
    main_src = BROWSER_DIR / "main.py"
    main_dst = output_dir / "main.py"
    shutil.copy2(main_src, main_dst)
    print(f"  Copied: main.py")

    # Copy browser runtime modules
    for py_file in BROWSER_DIR.glob("*.py"):
        if py_file.name != "main.py" and py_file.name != "build.py":
            dst = output_dir / py_file.name
            shutil.copy2(py_file, dst)
            print(f"  Copied: {py_file.name}")

    # Copy game modules maintaining directory structure
    _copy_game_files(output_dir)

    # Create __init__.py files where needed
    _ensure_init_files(output_dir)

    print(f"Build directory prepared at: {output_dir}")


def _convert_yaml_to_json(directory: Path):
    """Convert all YAML files in directory to JSON (for browser compatibility).

    PyYAML isn't available in WASM, so we pre-convert level files.
    """
    yaml_files = list(directory.rglob("*.yaml"))
    for yaml_path in yaml_files:
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)

            json_path = yaml_path.with_suffix('.json')
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)

            # Remove the original YAML file from the build
            yaml_path.unlink()
            print(f"    Converted: {yaml_path.name} -> {json_path.name}")
        except Exception as e:
            print(f"    Warning: Failed to convert {yaml_path}: {e}")


def _copy_game_files(output_dir: Path):
    """Copy game files maintaining directory structure."""
    # Copy games directory structure
    games_dst = output_dir / "games"
    games_dst.mkdir(exist_ok=True)

    # Copy common game infrastructure
    common_src = GAMES_DIR / "common"
    if common_src.exists():
        common_dst = games_dst / "common"
        shutil.copytree(
            common_src,
            common_dst,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "test_*"),
        )
        print(f"  Copied: games/common/")

    # Copy registry
    registry_src = GAMES_DIR / "registry.py"
    if registry_src.exists():
        shutil.copy2(registry_src, games_dst / "registry.py")
        print(f"  Copied: games/registry.py")

    # Copy Python/BaseGame games
    for game in BROWSER_GAMES:
        game_src = GAMES_DIR / game
        if game_src.exists():
            game_dst = games_dst / game
            shutil.copytree(
                game_src,
                game_dst,
                ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc", "test_*", "tests",
                    "venv", ".pytest_cache", ".claude", "*.md",
                    "coverage.xml", "pytest.ini", "requirements.txt"
                ),
            )
            print(f"  Copied: games/{game}/")

    # Copy YAML games
    for game in YAML_GAMES:
        game_src = GAMES_DIR / game
        if game_src.exists():
            game_dst = games_dst / game
            shutil.copytree(
                game_src,
                game_dst,
                ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc", "test_*", "tests",
                    "venv", ".pytest_cache", ".claude", "*.md",
                    "coverage.xml", "pytest.ini", "requirements.txt"
                ),
            )
            print(f"  Copied: games/{game}/ (YAML)")

    # Copy browser-compatible models (dataclass-based, no Pydantic)
    # Pydantic uses Rust extensions that don't work in WASM
    browser_models_src = BROWSER_DIR / "browser_models"
    if browser_models_src.exists():
        models_dst = output_dir / "models"
        shutil.copytree(
            browser_models_src,
            models_dst,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        print(f"  Copied: browser_models/ -> models/")

    # Copy AMS modules for YAML game support
    _copy_ams_modules(output_dir)

    # Convert YAML level files to JSON (PyYAML not available in WASM)
    print("  Converting YAML files to JSON...")
    _convert_yaml_to_json(games_dst)
    # Also convert YAML in ams dir
    ams_dst = output_dir / "ams"
    if ams_dst.exists():
        _convert_yaml_to_json(ams_dst)


def _copy_ams_modules(output_dir: Path):
    """Copy AMS modules needed for YAML game support."""
    ams_src = PROJECT_ROOT / "ams"
    ams_dst = output_dir / "ams"
    ams_dst.mkdir(exist_ok=True)

    # Create __init__.py for ams package
    (ams_dst / "__init__.py").touch()

    # Copy content_fs_browser (browser-compatible ContentFS)
    content_fs_browser = ams_src / "content_fs_browser.py"
    if content_fs_browser.exists():
        shutil.copy2(content_fs_browser, ams_dst / "content_fs_browser.py")
        print(f"  Copied: ams/content_fs_browser.py")

    # Copy logging module (unified logging for native/browser)
    logging_module = ams_src / "logging.py"
    if logging_module.exists():
        shutil.copy2(logging_module, ams_dst / "logging.py")
        print(f"  Copied: ams/logging.py")

    # Copy lua module (browser version - lua_bridge.py is at root level in build)
    lua_src = ams_src / "lua"
    lua_dst = ams_dst / "lua"
    lua_dst.mkdir(exist_ok=True)

    # Copy api.py (needed for LuaAPIBase, lua_safe_return)
    shutil.copy2(lua_src / "api.py", lua_dst / "api.py")
    print(f"  Copied: ams/lua/api.py")

    # Copy entity.py (Entity dataclass)
    shutil.copy2(lua_src / "entity.py", lua_dst / "entity.py")
    print(f"  Copied: ams/lua/entity.py")

    # Create __init__.py that redirects engine to browser version
    (lua_dst / "__init__.py").write_text(
        '"""Browser Lua module - uses WASMOON via JavaScript."""\n'
        'from lua_bridge import LuaEngineBrowser as LuaEngine\n'
        'from lua_bridge import EntityBrowser as Entity\n'
    )
    print(f"  Created: ams/lua/__init__.py (browser redirect)")

    # Copy entire ams/games subpackage (has many interdependencies)
    games_ams_src = ams_src / "games"
    games_ams_dst = ams_dst / "games"
    if games_ams_src.exists():
        shutil.copytree(
            games_ams_src, games_ams_dst,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "test_*", "tests"),
        )
        print(f"  Copied: ams/games/ (entire package)")

    # Copy WASMOON JavaScript bridge
    wasmoon_js = BROWSER_DIR / "wasmoon_bridge.js"
    if wasmoon_js.exists():
        shutil.copy2(wasmoon_js, output_dir / "wasmoon_bridge.js")
        print(f"  Copied: wasmoon_bridge.js")

    # Create root-level lua/ directory for subroutine loading
    # Engine looks for lua/{type}/ at ContentFS root, which maps to working directory
    lua_root_dst = output_dir / "lua"
    lua_engine_src = games_ams_dst / "game_engine" / "lua"
    if lua_engine_src.exists():
        # Copy behavior, collision_action, generator directories
        for subdir in ["behavior", "collision_action", "generator"]:
            src_dir = lua_engine_src / subdir
            if src_dir.exists():
                dst_dir = lua_root_dst / subdir
                shutil.copytree(
                    src_dir, dst_dir,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                    dirs_exist_ok=True,
                )
        print(f"  Created: lua/ (engine subroutines at root for ContentFS)")


def _ensure_init_files(output_dir: Path):
    """Ensure __init__.py exists in all package directories."""
    for dirpath in output_dir.rglob("*"):
        if dirpath.is_dir():
            # Check if directory has Python files
            has_py = any(dirpath.glob("*.py"))
            init_file = dirpath / "__init__.py"
            if has_py and not init_file.exists():
                init_file.touch()


def _copy_static_assets(output_dir: Path):
    """Copy static assets to pygbag's served directory."""
    served_dir = output_dir / "build" / "web"
    if not served_dir.exists():
        served_dir.mkdir(parents=True)

    # Copy wasmoon_bridge.js to served directory
    wasmoon_src = output_dir / "wasmoon_bridge.js"
    if wasmoon_src.exists():
        shutil.copy2(wasmoon_src, served_dir / "wasmoon_bridge.js")
        print(f"  Copied wasmoon_bridge.js to served directory")

    # Copy launcher.html to served directory
    launcher_src = output_dir / "launcher.html"
    if launcher_src.exists():
        shutil.copy2(launcher_src, served_dir / "launcher.html")
        print(f"  Copied launcher.html to served directory")


def run_dev_server(output_dir: Path, port: int = 8000):
    """Run pygbag development server."""
    pygbag = find_pygbag()
    print(f"\nStarting development server on port {port}...")
    print(f"Open: http://localhost:{port}\n")

    # Copy static assets to served directory before starting
    _copy_static_assets(output_dir)

    cmd = f"{pygbag} --port {port} {output_dir}"
    subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT)


def build_production(output_dir: Path):
    """Build production WASM bundle."""
    pygbag = find_pygbag()
    print("\nBuilding production bundle...")

    cmd = f"{pygbag} --build --app_name ams_games {output_dir}"
    result = subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT)

    # Copy static assets after pygbag creates the build directory
    _copy_static_assets(output_dir)

    if result.returncode == 0:
        print(f"\nBuild complete!")
        print(f"Output: {output_dir}/build/web/")
        print("\nTo deploy:")
        print(f"  1. Copy {output_dir}/build/web/ to your web server")
        print("  2. Or upload to GitHub Pages, Netlify, etc.")
    else:
        print(f"\nBuild failed with code {result.returncode}")
        sys.exit(1)


# Game metadata for launcher (slug -> display info)
GAME_INFO = {
    # Python/BaseGame games
    "BalloonPop": {"name": "Balloon Pop", "desc": "Pop the balloons before they escape"},
    "Containment": {"name": "Containment", "desc": "Keep the ball inside the boundary"},
    "DuckHunt": {"name": "Duck Hunt", "desc": "Classic arcade shooting game"},
    "FruitSlice": {"name": "Fruit Slice", "desc": "Slice the fruit, avoid the bombs"},
    "Gradient": {"name": "Gradient", "desc": "Color gradient test game"},
    "Grouping": {"name": "Grouping", "desc": "Group matching targets together"},
    "GrowingTargets": {"name": "Growing Targets", "desc": "Hit targets as they grow"},
    "LoveOMeter": {"name": "Love-O-Meter", "desc": "Carnival love meter challenge"},
    "ManyTargets": {"name": "Many Targets", "desc": "Hit as many targets as you can"},
    # YAML games (use WASMOON for Lua behaviors)
    "BrickBreakerNG": {"name": "Brick Breaker NG", "desc": "YAML-driven brick breaking"},
    "LoveOMeterNG": {"name": "Love-O-Meter NG", "desc": "YAML-driven love meter"},
}


def create_index_html(output_dir: Path):
    """Create a custom index.html with game selector."""
    # Generate game cards from all games (BaseGame + YAML)
    all_games = BROWSER_GAMES + YAML_GAMES
    game_cards = []
    for game in all_games:
        info = GAME_INFO.get(game, {"name": game, "desc": ""})
        slug = game.lower()
        is_yaml = game in YAML_GAMES
        badge = ' <span class="badge">YAML</span>' if is_yaml else ''
        card = f'''            <div class="game-card" onclick="loadGame('{slug}')">
                <h2>{info["name"]}{badge}</h2>
                <p>{info["desc"]}</p>
            </div>'''
        game_cards.append(card)

    game_cards_html = "\n".join(game_cards)

    index_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>AMS Games</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #1a1a2e;
            color: #eee;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
        }}
        .container {{
            text-align: center;
            max-width: 1200px;
        }}
        h1 {{
            color: #00d9ff;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        .subtitle {{
            color: #888;
            margin-bottom: 30px;
        }}
        .game-select {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .game-card {{
            background: #16213e;
            border: 2px solid #0f3460;
            border-radius: 12px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.2s;
            text-align: left;
        }}
        .game-card:hover {{
            border-color: #00d9ff;
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0, 217, 255, 0.2);
        }}
        .game-card h2 {{
            color: #00d9ff;
            margin-bottom: 8px;
            font-size: 1.2em;
        }}
        .game-card p {{
            color: #888;
            font-size: 13px;
            line-height: 1.4;
        }}
        .badge {{
            background: #e94560;
            color: white;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            vertical-align: middle;
            margin-left: 8px;
        }}
        #game-frame {{
            width: 100%;
            max-width: 1280px;
            height: 720px;
            border: none;
            display: none;
        }}
        .back-btn {{
            background: #0f3460;
            color: #00d9ff;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            margin-top: 20px;
            display: none;
            font-size: 14px;
        }}
        .back-btn:hover {{
            background: #16213e;
        }}
    </style>
</head>
<body>
    <div class="container" id="selector">
        <h1>AMS Games</h1>
        <p class="subtitle">Select a game to play</p>
        <div class="game-select">
{game_cards_html}
        </div>
    </div>
    <iframe id="game-frame"></iframe>
    <button class="back-btn" id="back-btn" onclick="showSelector()">Back to Games</button>

    <script>
        function loadGame(slug) {{
            document.getElementById('selector').style.display = 'none';
            const frame = document.getElementById('game-frame');
            frame.style.display = 'block';
            frame.src = 'index.html?game=' + slug;
            document.getElementById('back-btn').style.display = 'block';
        }}

        function showSelector() {{
            document.getElementById('selector').style.display = 'block';
            document.getElementById('game-frame').style.display = 'none';
            document.getElementById('back-btn').style.display = 'none';
        }}

        // Listen for messages from game
        window.addEventListener('message', function(e) {{
            if (e.data && e.data.source === 'ams_game') {{
                console.log('Game message:', e.data);
            }}
        }});
    </script>
</body>
</html>'''

    # Write to launcher.html (index.html is generated by pygbag)
    launcher_path = output_dir / "launcher.html"
    launcher_path.write_text(index_content)
    print(f"  Created: launcher.html")


def main():
    parser = argparse.ArgumentParser(description="Build AMS games for browser")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Start development server",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BUILD_DIR,
        help="Output directory",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Development server port",
    )
    args = parser.parse_args()

    # Generate build ID for cache validation
    build_id = uuid.uuid4().hex[:8]
    print(f"\n{'='*60}")
    print(f"  BUILD ID: {build_id}")
    print(f"{'='*60}\n")

    # Prepare build directory
    prepare_build_dir(args.output)

    # Write build ID to file for runtime verification
    (args.output / "build_id.txt").write_text(build_id)
    print(f"  Written: build_id.txt ({build_id})")

    create_index_html(args.output)

    if args.dev:
        run_dev_server(args.output, args.port)
    else:
        build_production(args.output)


if __name__ == "__main__":
    main()
