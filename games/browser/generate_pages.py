#!/usr/bin/env python3
"""
Static Page Generator for YAMS Browser Games

Generates:
- Game selector page at /play/index.html
- Per-game landing pages at /play/{slug}/index.html

Usage:
    python generate_pages.py --output _site/play/

Each game page iframes the shared WASM build with ?game={slug} parameter.
"""

import argparse
from pathlib import Path
from typing import Optional

from game_metadata import GAME_METADATA, CATEGORIES, get_all_games, get_games_by_category


# Path to WASM build relative to game pages
# From /play/balloonpop/ -> /play/wasm/
WASM_PATH = "../wasm"

# Path to site assets relative to play directory
# From /play/ -> /assets/
ASSETS_PATH = "../assets"


def generate_game_selector(games: list, output_path: Path) -> None:
    """Generate the main game selector page with cards for all games."""

    # Build game cards HTML
    game_cards = []
    for game in games:
        card = f'''
        <a href="{game['slug']}/" class="game-card">
            <h3>{game['name']}</h3>
            <p>{game['description']}</p>
            <span class="game-category">{CATEGORIES.get(game.get('category', 'other'), {}).get('name', 'Game')}</span>
        </a>'''
        game_cards.append(card)

    game_cards_html = "\n".join(game_cards)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Play Games - YAMS</title>
    <meta name="description" content="Play YAMS arcade games in your browser. Duck Hunt, Brick Breaker, Balloon Pop and more!">
    <link rel="stylesheet" href="{ASSETS_PATH}/style.css">
    <style>
        .games-container {{
            padding-top: 100px;
            padding-bottom: 4rem;
        }}

        .games-header {{
            text-align: center;
            margin-bottom: 3rem;
        }}

        .games-header h1 {{
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }}

        .games-header p {{
            color: var(--color-text-muted);
            font-size: 1.1rem;
        }}

        .game-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.5rem;
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
        }}

        .game-card {{
            background: var(--color-surface);
            padding: 1.5rem;
            border-radius: 12px;
            text-decoration: none;
            color: inherit;
            border: 2px solid transparent;
            transition: all 0.2s;
            display: flex;
            flex-direction: column;
        }}

        .game-card:hover {{
            border-color: var(--color-primary);
            transform: translateY(-2px);
        }}

        .game-card h3 {{
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
            color: var(--color-text);
        }}

        .game-card p {{
            color: var(--color-text-muted);
            flex-grow: 1;
            margin-bottom: 1rem;
        }}

        .game-category {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--color-primary);
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <header>
        <nav>
            <a href="/" class="logo">YAMS</a>
            <div class="nav-links">
                <a href="/#features">Features</a>
                <a href="/#games">Games</a>
                <a href="/play/" class="active">Play Online</a>
                <a href="https://github.com/timonorawski/yams">GitHub</a>
            </div>
        </nav>
    </header>

    <main class="games-container">
        <div class="games-header">
            <h1>Play Games</h1>
            <p>Select a game to play in your browser</p>
        </div>

        <div class="game-grid">
            {game_cards_html}
        </div>
    </main>

    <footer>
        <p>YAMS is open source software</p>
    </footer>
</body>
</html>
'''

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"  Generated: {output_path}")


def generate_game_page(slug: str, meta: dict, output_dir: Path) -> None:
    """Generate a landing page for a specific game."""

    game_dir = output_dir / slug
    game_dir.mkdir(parents=True, exist_ok=True)

    name = meta['name']
    description = meta['description']
    controls = meta.get('controls', 'Click to interact')
    category = CATEGORIES.get(meta.get('category', 'other'), {}).get('name', 'Game')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - YAMS</title>
    <meta name="description" content="{description}">
    <link rel="stylesheet" href="{ASSETS_PATH}/style.css">
    <style>
        .game-container {{
            padding-top: 80px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}

        .game-header {{
            padding: 1.5rem 2rem;
            background: var(--color-surface);
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}

        .game-header-inner {{
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}

        .game-info h1 {{
            font-size: 1.5rem;
            margin-bottom: 0.25rem;
        }}

        .game-info p {{
            color: var(--color-text-muted);
            font-size: 0.9rem;
        }}

        .game-controls {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .controls-hint {{
            color: var(--color-text-muted);
            font-size: 0.85rem;
        }}

        .controls-hint strong {{
            color: var(--color-text);
        }}

        .game-frame-container {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
            background: #000;
        }}

        .game-frame {{
            width: 100%;
            max-width: 800px;
            aspect-ratio: 4/3;
            border: none;
            border-radius: 8px;
            background: var(--color-surface);
        }}

        .back-link {{
            color: var(--color-primary);
            text-decoration: none;
            font-size: 0.9rem;
        }}

        .back-link:hover {{
            text-decoration: underline;
        }}

        .fullscreen-btn {{
            background: var(--color-primary);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
        }}

        .fullscreen-btn:hover {{
            background: var(--color-primary-dark);
        }}

        @media (max-width: 768px) {{
            .game-header-inner {{
                flex-direction: column;
                align-items: flex-start;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <nav>
            <a href="/" class="logo">YAMS</a>
            <div class="nav-links">
                <a href="/#features">Features</a>
                <a href="/#games">Games</a>
                <a href="/play/">Play Online</a>
                <a href="https://github.com/timonorawski/yams">GitHub</a>
            </div>
        </nav>
    </header>

    <main class="game-container">
        <div class="game-header">
            <div class="game-header-inner">
                <div class="game-info">
                    <a href="/play/" class="back-link">&larr; All Games</a>
                    <h1>{name}</h1>
                    <p>{description}</p>
                </div>
                <div class="game-controls">
                    <span class="controls-hint"><strong>Controls:</strong> {controls}</span>
                    <button class="fullscreen-btn" onclick="toggleFullscreen()">Fullscreen</button>
                </div>
            </div>
        </div>

        <div class="game-frame-container">
            <iframe
                id="game-frame"
                class="game-frame"
                src="{WASM_PATH}/index.html?game={slug}"
                allow="autoplay; fullscreen"
                loading="lazy"
            ></iframe>
        </div>
    </main>

    <script>
        function toggleFullscreen() {{
            const frame = document.getElementById('game-frame');
            if (frame.requestFullscreen) {{
                frame.requestFullscreen();
            }} else if (frame.webkitRequestFullscreen) {{
                frame.webkitRequestFullscreen();
            }}
        }}
    </script>
</body>
</html>
'''

    output_path = game_dir / "index.html"
    output_path.write_text(html)
    print(f"  Generated: {output_path}")


def generate_all_pages(output_dir: Path, wasm_path: Optional[str] = None) -> None:
    """Generate all static pages for the game site."""
    global WASM_PATH

    if wasm_path:
        WASM_PATH = wasm_path

    print("Generating static game pages...")

    # Get all games
    games = get_all_games()
    print(f"  Found {len(games)} games")

    # Generate game selector
    generate_game_selector(games, output_dir / "index.html")

    # Generate per-game pages
    for game in games:
        generate_game_page(game['slug'], game, output_dir)

    print(f"Done! Generated {len(games) + 1} pages")


def main():
    parser = argparse.ArgumentParser(description="Generate static game pages")
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("_site/play"),
        help="Output directory (default: _site/play)"
    )
    parser.add_argument(
        "--wasm-path",
        type=str,
        default=None,
        help="Relative path to WASM build from game pages (default: ../wasm)"
    )
    args = parser.parse_args()

    generate_all_pages(args.output, args.wasm_path)


if __name__ == "__main__":
    main()
