# Static GitHub Pages Deployment

This document describes the architecture for deploying YAMS games as static pages on GitHub Pages, with one URL per game.

## Overview

The static deployment system creates:
- Individual landing pages for each game at `/play/{slug}/`
- A game selector at `/play/` showing all available games
- A shared WebAssembly build at `/play/wasm/` used by all games

This approach is efficient (single WASM build ~50-60MB shared across all games) and SEO-friendly (each game has its own URL and metadata).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          GitHub Pages Site                               │
│                                                                         │
│  yamplay.cc/                  yamplay.cc/play/                          │
│  ┌─────────────────┐          ┌─────────────────┐                       │
│  │  Landing Page   │          │  Game Selector  │                       │
│  │  (site/index)   │   ────►  │  (generated)    │                       │
│  └─────────────────┘          └────────┬────────┘                       │
│                                        │                                │
│                    ┌───────────────────┼───────────────────┐            │
│                    ▼                   ▼                   ▼            │
│     yamplay.cc/play/balloonpop/   /duckhunt/        /brickbreaker/      │
│     ┌─────────────────┐     ┌─────────────────┐  ┌─────────────────┐   │
│     │  Game Page      │     │  Game Page      │  │  Game Page      │   │
│     │  - Description  │     │  - Description  │  │  - Description  │   │
│     │  - Controls     │     │  - Controls     │  │  - Controls     │   │
│     │  - iframe ──────┼─────┼──────────────────┼──┼──────┐          │   │
│     └─────────────────┘     └─────────────────┘  └──────┼──────────┘   │
│                                                          │              │
│                              ┌───────────────────────────┘              │
│                              ▼                                          │
│                    yamplay.cc/play/wasm/                                │
│                    ┌─────────────────────────────────────────────────┐  │
│                    │  Shared WASM Build (pygbag output)              │  │
│                    │                                                 │  │
│                    │  index.html?game={slug}                         │  │
│                    │  ├── Python runtime (pyodide WASM)              │  │
│                    │  ├── All game code (Python + YAML/JSON)         │  │
│                    │  ├── fengari_bridge.js (Lua runtime)            │  │
│                    │  └── Assets (sprites, sounds)                   │  │
│                    └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## URL Structure

| URL | Content |
|-----|---------|
| `/` | Landing page with features, about |
| `/play/` | Game selector showing all games |
| `/play/{slug}/` | Individual game page with iframe |
| `/play/wasm/` | Shared pygbag build (not user-facing) |

Example game URLs:
- `/play/balloonpop/` - Balloon Pop
- `/play/duckhunt/` - Duck Hunt
- `/play/brickbreaker/` - Brick Breaker NG

## Game Selection Mechanism

Games are selected via URL parameter passed to the WASM build:

```
/play/wasm/index.html?game=balloonpop
```

The `main.py` browser entry point reads this parameter:
```python
game_slug = get_url_param('game', 'containment')  # Default to containment
await runtime.load_game(game_slug)
```

Each game landing page simply iframes the WASM with the appropriate parameter:
```html
<iframe src="/play/wasm/index.html?game=balloonpop"></iframe>
```

## Build Process

The build process (`games/browser/build.py --static`) produces:

```
output/
├── index.html              # Game selector (generated)
├── balloonpop/
│   └── index.html          # Game page (generated)
├── duckhunt/
│   └── index.html          # Game page (generated)
├── brickbreaker/
│   └── index.html          # Game page (generated)
├── ... (other games)
└── wasm/
    ├── index.html          # pygbag output
    ├── *.wasm              # WebAssembly runtime
    ├── fengari_bridge.js   # Lua runtime
    └── ... (game assets)
```

### Build Steps

1. **pygbag build** - Compile Python to WASM, output to `{output}/wasm/`
2. **Generate game selector** - Create `{output}/index.html` with game cards
3. **Generate game pages** - Create `{output}/{slug}/index.html` for each game

## Components

### game_metadata.py

Defines metadata for each game:
```python
GAME_METADATA = {
    "balloonpop": {
        "name": "Balloon Pop",
        "description": "Pop colorful balloons before they float away!",
        "controls": "Click or tap balloons to pop them",
        "category": "arcade",
        "registry_name": "BalloonPop",
    },
    ...
}
```

### generate_pages.py

Generates static HTML pages:
- Uses Python f-strings (no template engine dependency)
- Reads metadata from `game_metadata.py`
- Creates consistent styling matching main site (`site/assets/style.css`)

### GitHub Actions Workflow

The `pages.yml` workflow:
1. Checks out code
2. Installs pygbag and dependencies
3. Runs `build.py --static --output _site/play/`
4. Copies `site/` to `_site/`
5. Deploys to GitHub Pages

## Design Decisions

### Why Shared WASM?

Building pygbag per-game would:
- Take 5-15 minutes per game (11+ games = 1-2+ hours build time)
- Produce ~50-60MB per game (600MB+ total)
- Duplicate the entire Python runtime

Single build with URL parameter selection:
- ~5-15 minute build time total
- ~50-60MB total (shared across all games)
- Simpler cache management

### Why Per-Game Landing Pages?

- **SEO**: Each game has unique URL, title, description
- **Shareability**: Users can share direct links to specific games
- **Discoverability**: Search engines index each game separately
- **Flexibility**: Can add game-specific content (screenshots, tutorials)

### Why Iframe Isolation?

- **Security**: Game runs in isolated context
- **Reliability**: Page chrome survives game crashes
- **UX**: Can show loading states, error handling in parent page
- **Navigation**: Back button works correctly (returns to game page, not previous game state)

## Future Enhancements

1. **Screenshots**: Add game screenshots to metadata, display on landing pages
2. **Game-specific parameters**: Support level selection via URL (`?game=duckhunt&level=classic`)
3. **Analytics**: Track which games are played most
4. **PWA Support**: Make games installable as standalone apps
5. **Offline Mode**: Service worker for offline play after initial load
