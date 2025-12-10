# AMS Browser Deployment

Deploy AMS pygame games to the browser via pygbag/pygame-wasm, enabling play, observation, and level authoring directly in the web interface.

## Current Status

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1: Browser Runtime** | **Done** | Pygbag-compatible game runtime with async loop |
| **Phase 2: Build System** | **Done** | Build script, YAML→JSON conversion, 9 browser-compatible games |
| **Phase 3: Play Mode UI** | **Done** | Svelte frontend integration with game selector |
| Phase 4: Observer Mode | Not Started | Frame streaming from AMS sessions |
| Phase 5: Level Authoring | Not Started | Monaco YAML editor with live preview |
| Phase 6: Polish | Not Started | Mobile optimization, performance tuning |

---

## Implementation Details

### Phase 1: Browser Runtime (Complete)

**Created Files:**
```
games/browser/
├── main.py                 # Pygbag entry point (async main)
├── game_runtime.py         # BrowserGameRuntime - async game loop
├── input_adapter.py        # BrowserInputAdapter - mouse/touch → InputEvent
├── platform_compat.py      # is_browser(), get_url_param()
├── level_bridge.py         # JS ↔ Python postMessage communication
├── build.py                # Build script with YAML→JSON conversion
└── browser_models/         # Dataclass replacements for Pydantic models
    ├── __init__.py
    ├── primitives.py       # Point2D, Vector2D, Color, etc.
    └── game.py             # GameState, InputEvent, etc.
```

**Key Features:**
- Async game loop with `await asyncio.sleep(0)` to yield to browser
- URL parameter parsing for game/level selection
- postMessage bridge for JS ↔ Python communication
- Dataclass-based models (Pydantic uses Rust, doesn't work in WASM)
- Build-time YAML→JSON conversion (PyYAML uses C, doesn't work in WASM)

### Phase 2: Build System (Complete)

**Usage:**
```bash
# Development server (auto-reload)
python games/browser/build.py --dev --port 8000

# Production build
python games/browser/build.py
```

**Browser-Compatible Games (9):**
- BalloonPop, Containment, DuckHunt, FruitSlice, Gradient
- Grouping, GrowingTargets, LoveOMeter, ManyTargets

**Excluded:**
- SweetPhysics (pymunk uses CFFI, doesn't work in WASM)

**Build Output:**
```
build/web/
├── main.py, game_runtime.py, ...  # Source files
├── games/                          # Game modules + levels (JSON)
├── models/                         # Browser-compatible models
└── build/web/                      # Pygbag output
    ├── index.html                  # Self-contained loader
    ├── web.apk                     # WASM bundle (~500KB)
    └── favicon.png
```

### Phase 3: Svelte Frontend (Complete)

**Created Files:**
```
ams/web_controller/frontend/
├── play.html                       # Play mode entry point
├── src/
│   ├── play.js                     # Play mode JS entry
│   ├── Play.svelte                 # Play mode page component
│   └── lib/
│       ├── GameCanvas.svelte       # Pygbag iframe wrapper
│       └── GameSelector.svelte     # Game selection UI
└── vite.config.js                  # Multi-page config + /pygbag proxy
```

**Server Updates (`ams/web_controller/server.py`):**
- Added `/play` and `/play.html` routes
- Added `/api/levels/{game_slug}` endpoint
- Added `/pygbag` static mount for WASM files

**Architecture:**
- Plain Svelte (not SvelteKit) with Vite multi-page app
- GameCanvas wraps pygbag in iframe, handles postMessage
- GameSelector shows 9 games with hardcoded list matching build.py
- /pygbag proxy (dev) or static mount (prod) serves WASM files

**Running Play Mode:**

*Development (Vite + pygbag dev server):*
```bash
# Terminal 1: pygbag dev server
python games/browser/build.py --dev --port 8000

# Terminal 2: Vite dev server
cd ams/web_controller/frontend && npm run dev

# Visit http://localhost:5173/play.html
```

*Production (FastAPI serves everything):*
```bash
# Build frontend
cd ams/web_controller/frontend && npm run build

# Start AMS server
python ams_game.py --game containment

# Visit http://localhost:8080/play
```

---

## Known WASM-Incompatible Libraries

| Library | Reason | Alternative |
|---------|--------|-------------|
| **Pydantic** | Rust extensions | `games/browser/browser_models/` (dataclasses) |
| **PyYAML** | C libyaml | Build-time YAML→JSON conversion |
| **python-dotenv** | N/A in browser | Conditional import |
| **pymunk** | CFFI + Chipmunk2D | Pure Python physics (not implemented) |

---

## Phase 4: Observer Mode (Planned)

Stream live frames from AMS sessions to browser observers.

**Components:**
- `ObserverStream` - capture pygame surface → JPEG → WebSocket
- `/ws/observer` endpoint for frame streaming
- `ObserverCanvas.svelte` - render frames on canvas
- Observer page at `/observe`

**Implementation:**
```python
# ams/web_controller/observer.py
class ObserverStream:
    def capture_frame(self, screen: pygame.Surface) -> bytes:
        """Capture pygame surface as JPEG bytes."""
        data = pygame.surfarray.array3d(screen)
        data = data.swapaxes(0, 1)
        img = Image.fromarray(data)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=70)
        return buffer.getvalue()
```

---

## Phase 5: Level Authoring (Planned)

Monaco YAML editor with live pygbag preview for creating levels.

**Components:**
- `LevelEditor.svelte` - Monaco editor wrapper
- `LevelPreview.svelte` - live game preview
- `/api/levels/validate` endpoint
- `/api/levels/schema/{game}` endpoint
- Author page at `/author`

---

## Phase 6: Polish (Planned)

- Mobile touch optimization (iOS Safari, Android Chrome)
- Performance tuning (bundle size, lazy loading)
- Error handling (WebSocket reconnection, WASM fallback)
- Documentation updates

---

## Technical Notes

### Pygbag Async Pattern
```python
async def main():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()

    while True:
        dt = clock.tick(60) / 1000.0
        # ... game loop ...
        pygame.display.flip()
        await asyncio.sleep(0)  # CRITICAL: yield to browser
```

### JS ↔ Python Communication
```javascript
// Send to Python
iframe.contentWindow.postMessage(JSON.stringify({
    type: 'load_game',
    game: 'containment',
    level: null
}), '*');

// Receive from Python
window.addEventListener('message', (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'game_state') {
        // Update UI with data.data
    }
});
```

### Vite Proxy for Development
```javascript
// vite.config.js
server: {
    proxy: {
        '/pygbag': {
            target: 'http://localhost:8000',
            rewrite: (path) => path.replace(/^\/pygbag/, ''),
        },
    },
},
```

---

## Resources

- [Pygbag Documentation](https://pygame-web.github.io/wiki/pygbag/)
- [Pygbag Code FAQ](https://pygame-web.github.io/wiki/pygbag-code/)
- [Monaco Editor](https://microsoft.github.io/monaco-editor/)
