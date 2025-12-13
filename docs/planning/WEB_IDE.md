# AMS Web IDE

**Epic: Browser-based game creation environment with live preview**

Enable non-developers to create, edit, and share YAML-defined games directly in the browser. No local setup required.

## Current Status

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 0: Browser Engine** | ✅ Complete | Fengari Lua + pygbag - games running in browser |
| **Phase 1: MVP Editor** | ✅ Complete | Monaco editor + Docker backend + hot reload working |
| Phase 1.1: Log Streaming | 🚧 Next | Live tail panel for engine logs (testing aid) |
| Phase 1.5: Asset & Content-Type | Not Started | Asset browser, content-type aware field editors |
| Phase 2: Visual Editors | Not Started | Sprite sheet + level layout editors |
| Phase 3: Debugger | Not Started | Breakpoints, stepping, inspection |
| Phase 4: Sharing | Not Started | Export, shareable links, gallery |

**Prerequisite:** BROWSER_DEPLOYMENT.md Phase 1-3 (Complete) ✅

> **Phase 1 Complete!** Full IDE-to-engine workflow operational:
> - Monaco editor with YAML syntax and project file tree
> - Docker backend with file API and host volume persistence
> - IDE bridge (postMessage) for file transfer to engine
> - **Hot reload**: Edit files → engine auto-reloads game in real-time
> - WASM compatibility fixes (threading, JS/Python boundary)
> - **Profile Viewer**: `/profiler` endpoint for analyzing game performance

---

## The Problem

Creating YAML games currently requires:
1. Local Python environment with dependencies
2. Text editor knowledge (YAML syntax)
3. Command-line familiarity
4. Understanding of asset paths and structure

This excludes:
- Kids who want to make their own targets
- Non-technical users at events/workshops
- Quick experimentation without setup
- Sharing creations easily

## The Solution

A browser-based IDE that:
- Edits YAML + Lua with intelligent autocomplete
- Shows live game preview (< 100ms reload)
- Provides visual editors for sprites and levels
- Enables debugging Lua behaviors
- Exports shareable games

---

## Architecture

```
+------------------------------------------------------------------+
|                     AMS WEB IDE (Browser)                         |
+------------------------------------------------------------------+
|  +------------------------+     +----------------------------+   |
|  |     EDITOR PANEL       |     |     PREVIEW PANEL          |   |
|  | +--------------------+ |     | +------------------------+ |   |
|  | | Monaco Editor      | | MSG | | pygbag iframe          | |   |
|  | | - YAML + Lua       | |<--->| | - pygame (WASM)        | |   |
|  | +--------------------+ |     | | - Fengari Lua (JS)     | |   |
|  | +--------------------+ |     | | - fengari_bridge.js    | |   |
|  | | Visual Editors     | |     | +------------------------+ |   |
|  | | - Sprite Sheet     | |     | +------------------------+ |   |
|  | | - Level Layout     | |     | | Debug Panel            | |   |
|  | +--------------------+ |     | | - Entity inspector     | |   |
|  | +--------------------+ |     | | - Lua console          | |   |
|  | | Lua Debugger UI    | |     | +------------------------+ |   |
|  +------------------------+     +----------------------------+   |
|  +--------------------------------------------------------------+|
|  |          Emscripten MEMFS (pygbag virtual filesystem)         ||
|  +--------------------------------------------------------------+|
+------------------------------------------------------------------+
```

### Communication Flow

```
Editor saves game.yaml
       │
       ▼
postMessage('file_update', {path, content})
       │
       ▼
Emscripten MEMFS write (virtual filesystem)
       │
       ▼
BrowserGameRuntime receives 'hot_reload' message
       │
       ▼
GameEngine reloads game definition
       │
       ▼
Preview shows changes (target: < 500ms)
```

### Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Editor | Monaco Editor | VS Code-quality, native JSON Schema |
| UI Framework | **Svelte** | Already used in `ams/web_controller/frontend/` |
| Build Tool | **Vite** | Already configured for Svelte frontend |
| Preview Runtime | pygbag | Existing infrastructure, games already work |
| Lua Runtime | **Fengari** | Pure JS Lua 5.3, stable (WASMOON had memory issues) |
| Backend API | **FastAPI** | File persistence, schema serving |
| Storage (browser) | **Emscripten MEMFS** | pygbag's virtual filesystem |
| Storage (Docker) | **Host volume** | `./data/projects/` persists to host |

> **Reuse:** Extend existing `ams/web_controller/frontend/` rather than creating new project.

---

## Phase 0: Browser Engine ✅ COMPLETE

**Goal:** Get the refactored YAML game engine running in browser with full Lua support.

### What Was Done

Games now run in the browser using **Fengari** (pure JavaScript Lua 5.3) instead of the originally planned WASMOON.

**Why Fengari instead of WASMOON?**
- WASMOON (Lua 5.4 in WebAssembly) suffered memory corruption after ~100 frames
- Processing 52 entities/frame with JSON serialization exceeded WASM heap limits
- Fengari is slower but stable and has no memory constraints

### Implemented Architecture

```
Python (pygbag WASM)              JavaScript
┌─────────────────────┐           ┌─────────────────────┐
│ GameEngine          │           │ fengari_bridge.js   │
│ LuaEngineBrowser    │──────────►│ Fengari Lua 5.3     │
│ (lua_bridge.py)     │ postMsg   │ ams.* API (JS)      │
└─────────────────────┘           └─────────────────────┘
```

- **LuaEngineBrowser** serializes entity state to JSON, sends via postMessage
- **fengari_bridge.js** executes Lua behaviors, tracks state changes
- Changes returned to Python and applied to real entities

### Key Files

| File | Purpose |
|------|---------|
| `games/browser/fengari_bridge.js` | JS Lua runtime + ams.* API |
| `games/browser/lua_bridge.py` | Python LuaEngineBrowser |
| `games/browser/game_runtime.py` | Browser game loop |
| `games/browser/build.py` | pygbag build script |

### Success Criteria ✅

- [x] `python games/browser/build.py --dev` succeeds
- [x] Browser opens, game selector shows YAML games
- [x] Games load with working Lua behaviors
- [x] `gravity.lua` behavior executes (entities fall)
- [x] Collision actions trigger (entities respond to hits)
- [x] No Python import errors in browser console

> **Full details:** See `docs/architecture/BROWSER_LUA_BRIDGE.md`

---

## Phase 1: MVP Editor ✅ COMPLETE

**Goal:** Edit game.yaml in Monaco, see changes in pygbag preview.

### What's Been Implemented

#### Frontend (Svelte + Vite)

| Component | Status | File |
|-----------|--------|------|
| IDE entry point | ✅ | `author.html`, `src/author.js` |
| Split-pane layout | ✅ | `src/Author.svelte` |
| Monaco editor wrapper | ✅ | `src/lib/ide/MonacoEditor.svelte` |
| File tree sidebar | ✅ | `src/lib/ide/FileTree.svelte` |
| Preview iframe | ✅ | `src/lib/ide/PreviewFrame.svelte` |
| Schema files | ✅ | `public/schemas/*.json` |

#### Docker Backend

| Component | Status | File |
|-----------|--------|------|
| IDE server (FastAPI) | ✅ | `docker/ide-server/server.py` |
| IDE Dockerfile | ✅ | `docker/ide-server/Dockerfile` |
| Web server (pygbag) | ✅ | `docker/web-server/server.py` |
| Web server Dockerfile | ✅ | `docker/web-server/Dockerfile` |
| Pygbag auto-build | ✅ | `docker/web-server/entrypoint.sh` |
| docker-compose services | ✅ | `docker-compose.yml` |
| nginx routing | ✅ | `docker/nginx/dev.conf` |

#### APIs Working

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/author` | GET | IDE frontend |
| `/api/schemas` | GET | List available schemas |
| `/api/schemas/{name}` | GET | Fetch individual schema |
| `/api/projects` | GET | List user projects |
| `/api/projects` | POST | Create new project |
| `/api/projects/{name}` | DELETE | Delete project |
| `/api/projects/{name}/files` | GET | List files in project |
| `/api/projects/{name}/files/{path}` | GET/PUT/DELETE | Read/write/delete files |

#### File Persistence

Projects persist to `./data/projects/` on the host machine via Docker volume mount:

```yaml
ide-server:
  volumes:
    - ${PROJECTS_DIR:-./data/projects}:/app/data/projects
```

### Static Engine Architecture

The preview uses a **static pre-built pygbag engine** rather than rebuilding on each Docker start. This separation of engine vs. content enables instant hot reload.

```
┌─────────────────────────────────────────────────────────────────┐
│  Monaco Editor (YAML)                                           │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  game.yaml  →  js-yaml parse  →  JSON Schema validation   │ │
│  │                      │                                     │ │
│  │                      ▼                                     │ │
│  │              JSON serialization                            │ │
│  └───────────────────────┬───────────────────────────────────┘ │
│                          │ postMessage({type: 'project_files'}) │
│                          ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Preview iframe (static engine from CDN/yamplay.cc)       │ │
│  │  ┌─────────────────┐    ┌─────────────────────────────┐  │ │
│  │  │ ide_bridge.js   │───▶│ ide_bridge.py               │  │ │
│  │  │ receives msg    │    │ writes to ContentFS         │  │ │
│  │  │ calls Python    │    │ triggers GameEngine reload  │  │ │
│  │  └─────────────────┘    └─────────────────────────────┘  │ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │ pygbag WASM (pre-built, static, never changes)      │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Why static engine?**
- PyYAML doesn't work in WASM → Monaco converts YAML→JSON before sending
- Engine build takes ~2 minutes → pre-build once, cache forever
- Hot reload becomes instant postMessage (no rebuild)
- Works offline once cached

**PostMessage Protocol:**

```javascript
// IDE → Engine
{type: 'project_files', files: {
  'game.json': {...},              // YAML converted to JSON
  'levels/level1.json': {...},
  'lua/behavior/bounce.lua': '...' // Lua stays as string
}}
{type: 'reload'}                   // trigger hot reload

// Engine → IDE
{type: 'ready'}                    // engine initialized
{type: 'error', file: '...', line: 42, message: '...'}
{type: 'log', level: 'info', message: '...'}
```

**Key files:**
| File | Purpose |
|------|---------|
| `games/browser/ide_bridge.js` | JS message receiver, queues for Python |
| `games/browser/ide_bridge.py` | Writes files to ContentFS, triggers reload |
| `ams/content_fs_browser.py` | Added writetext/writebytes/remove methods |
| `games/browser/game_runtime.py` | IDE bridge integration in game loop |
| `src/lib/ide/PreviewFrame.svelte` | Sends files via postMessage |

### Completed Work

1. **IDE ↔ Engine Bridge** ✅
   - [x] `ide_bridge.js` - receive postMessage, queue for Python
   - [x] `ide_bridge.py` - write to ContentFS, trigger reload
   - [x] `ContentFSBrowser` - added write support
   - [x] `BrowserGameRuntime` - IDE message processing
   - [x] Update `PreviewFrame.svelte` to send files
   - [x] Add `js-yaml` to package.json for YAML→JSON conversion

2. **Frontend ↔ Backend Integration** ✅
   - [x] Connect FileTree to `/api/projects` endpoints
   - [x] Connect MonacoEditor save to `/api/projects/{name}/files/{path}`
   - [x] Load/save project state
   - [x] Auto-save with 2-second debounce

3. **Preview Integration** ✅
   - [x] Embed pygbag build in iframe
   - [x] IDE mode startup (wait for files before loading game)
   - [x] Hot reload on file changes (reactive file watching)
   - [x] Engine signals ready → IDE sends files → engine reloads

4. **WASM Compatibility Fixes** ✅
   - [x] Make `ams/profiling.py` WASM-safe (conditional threading)
   - [x] Fix JS/Python boundary (JSON serialization at boundary)
   - [x] Add `_frame_count` initialization for profiling

5. **UI** ✅
   - [x] Tailwind CSS + DaisyUI components
   - [x] Dark theme

### Future Enhancements (Phase 1.5+)

1. **Monaco Schema Validation**
   - [ ] Wire up JSON schemas to Monaco YAML validation
   - [ ] Handle `$ref` resolution between schemas

2. **Error Display**
   - [ ] Display runtime Lua errors in IDE
   - [ ] Show validation errors inline in editor

### File Structure (Implemented)

```text
ams/web_controller/frontend/
├── author.html                    # ✅ IDE entry point
├── vite.config.js                 # ✅ Updated with author entry
├── package.json                   # ✅ Added monaco-editor
├── public/schemas/                # ✅ Copied from game_engine
│   ├── game.schema.json
│   ├── level.schema.json
│   └── lua_script.schema.json
└── src/
    ├── author.js                  # ✅ IDE entry point
    ├── Author.svelte              # ✅ Main IDE layout
    └── lib/ide/
        ├── MonacoEditor.svelte    # ✅ Monaco wrapper
        ├── FileTree.svelte        # ✅ File browser
        └── PreviewFrame.svelte    # ✅ Preview iframe

games/browser/
├── ide_bridge.js                  # ✅ JS postMessage receiver
├── ide_bridge.py                  # ✅ Python ContentFS writer
├── game_runtime.py                # ✅ Updated with IDE message loop
└── build.py                       # ✅ Updated to include bridge files

ams/
└── content_fs_browser.py          # ✅ Added write support

docker/
├── ide-server/
│   ├── Dockerfile                 # ✅ Multi-stage: Node build + Python runtime
│   └── server.py                  # ✅ File API server
├── web-server/
│   ├── Dockerfile                 # ✅ Python + pygbag + pygame-ce
│   ├── entrypoint.sh              # ✅ Auto-build pygbag on startup
│   └── server.py                  # ✅ Serves build output
└── nginx/
    └── dev.conf                   # ✅ Routes for /author, /api/*, /pygbag/

data/
└── projects/                      # ✅ User projects (persists to host)
    └── .gitkeep

.vscode/
├── launch.json                    # ✅ IDE dev configurations
└── tasks.json                     # ✅ Build tasks
```

### Usage

```bash
# Development (standalone)
cd ams/web_controller/frontend
npm install
npm run dev
# Open http://localhost:5173/author.html

# Docker (full stack with persistence)
docker compose up --build
# Open http://localhost:8000/author
# Projects save to ./data/projects/

# Port 8000 is required for pygbag CDN compatibility
# nginx proxies /archives/* to pygame-web.github.io
```

### Success Criteria ✅ ALL MET

- [x] IDE entry point at `/author`
- [x] Split-pane layout with resizable divider
- [x] Monaco editor with YAML syntax highlighting
- [x] File tree sidebar with API integration
- [x] Schema API endpoint serving all schemas
- [x] Projects API with CRUD operations
- [x] Files persist to host via Docker volume
- [x] Preview iframe loads pygbag games (Docker auto-builds on startup)
- [x] Edit `game.yaml` → see changes in preview (hot reload)
- [x] **Auto-reload on file change** (no manual Run button needed)
- [x] Engine ready signal hides loading overlay
- [x] WASM compatibility (threading, JS/Python boundary)

---

## Phase 1.1: Log Streaming (Testing Aid)

**Goal:** Live tail panel showing engine logs for debugging hot reload and game behavior.

### Architecture

```
Engine (Python)                              IDE (Svelte)
┌─────────────────────┐                      ┌─────────────────────┐
│ IDELogHandler       │    postMessage       │ LogPanel.svelte     │
│ (logging.Handler)   │───────────────────►  │ - auto-truncate     │
│                     │    {type: 'log',     │ - level filtering   │
│ Captures ams.*      │     level, message}  │ - pause/resume      │
│ logger output       │                      │ - search            │
└─────────────────────┘                      └─────────────────────┘
```

### Features

| Feature | Description |
|---------|-------------|
| **Auto-Truncation** | Keep only last N lines (default: 200) to prevent memory bloat |
| Level Filtering | Show/hide DEBUG, INFO, WARNING, ERROR |
| Pause/Resume | Stop scrolling to inspect, resume to catch up |
| Search | Filter logs by regex or text |
| Clear | Manual clear button |
| Timestamps | Optional timestamp prefix |

### Auto-Truncation

Engine logs are noisy - the panel auto-truncates by default:

```javascript
// LogPanel.svelte
const MAX_LINES = 200;  // Configurable

function addLog(entry) {
  logs = [...logs, entry];
  if (logs.length > MAX_LINES) {
    logs = logs.slice(-MAX_LINES);  // Keep most recent
  }
}
```

User can:
- Adjust max lines (50, 100, 200, 500, unlimited)
- See "X lines truncated" indicator
- Scroll lock pauses truncation temporarily

### postMessage Protocol

```javascript
// Engine → IDE
{type: 'log', level: 'info', message: 'Loading entity_types...', timestamp: 1234567890}
{type: 'log', level: 'error', message: 'Failed to load sprite: player', timestamp: 1234567891}
{type: 'log', level: 'debug', message: 'Entity spawned: duck_123', timestamp: 1234567892}
```

### Files to Create/Modify

| File | Change |
|------|--------|
| `src/lib/ide/LogPanel.svelte` | **NEW** - Log viewer with auto-truncation |
| `src/Author.svelte` | Add LogPanel below preview or as collapsible panel |
| `games/browser/ide_bridge.py` | Add `IDELogHandler` to forward logs |
| `games/browser/ide_bridge.js` | Forward log messages to parent window |

### Success Criteria

- [ ] Engine logs appear in IDE within 100ms
- [ ] Panel auto-truncates at 200 lines by default
- [ ] Can filter by log level (hide DEBUG)
- [ ] Can pause to inspect, resume to catch up
- [ ] "X lines truncated" indicator shows when trimmed

> **Full implementation details:** See `docs/planning/web_ide/VISUAL_IDE.md` Section 12

---

## Phase 1.5: Asset Registry & Content-Type Editors

**Goal:** Leverage discovered asset definitions for intelligent editing.

### Asset Registry Integration

The `AssetRegistry` class discovers asset definitions from `assets/*.json` files (converted from YAML at build time). This enables rich IDE features:

```
┌─────────────────────────────────────────────────────────────────┐
│  Engine loads                                                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ AssetRegistry.discover('assets/')                           ││
│  │   → finds sprites.json, shot.json, etc.                     ││
│  │   → registers sprites/sounds by name                        ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ IDE receives asset manifest via postMessage                 ││
│  │   → populates asset browser panel                           ││
│  │   → enables autocomplete for sprite:/sound: fields          ││
│  │   → shows previews and provenance                           ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Features:**

| Feature | Description |
|---------|-------------|
| Asset Browser Panel | Sidebar showing all discovered sprites/sounds with thumbnails |
| Autocomplete | Type `sprite: p` → suggests `player`, `projectile`, etc. |
| Inline Preview | Hover over `sprite: duck_flying` → see sprite thumbnail |
| Provenance Display | Show author, license, source for assets with metadata |
| Asset Search | Filter assets by name, tags, type |
| Drag-and-Drop | Drag asset from browser into YAML → inserts reference |

**postMessage Protocol (new):**

```javascript
// Engine → IDE (on load)
{type: 'asset_manifest', sprites: {...}, sounds: {...}}

// IDE → Engine (query)
{type: 'get_asset_preview', name: 'duck_flying', type: 'sprite'}

// Engine → IDE (response)
{type: 'asset_preview', name: 'duck_flying', dataUrl: 'data:image/png;base64,...'}
```

### Content-Type Aware Editors

When the cursor is on a typed field in YAML, offer specialized editors based on the field's JSON Schema `x-content-type`:

```yaml
# game.yaml with content-type annotations (from schema)
entity_types:
  duck:
    sprite: duck_flying      # x-content-type: "sprite" → sprite picker
    sound: quack             # x-content-type: "sound" → sound picker
    color: [255, 200, 0]     # x-content-type: "color" → color picker
    transparent: [159, 227, 163]  # x-content-type: "color"

background:
  color: "#1a1a2e"           # x-content-type: "color" → color picker
  image: backgrounds/sky.png # x-content-type: "file" → file browser

levels:
  - level: level1            # x-content-type: "level" → level editor
```

**Content-Type Editor Mapping:**

| x-content-type | Editor Widget | Behavior |
|----------------|---------------|----------|
| `sprite` | SpritePicker | Grid of available sprites with preview |
| `sound` | SoundPicker | List with play button for each sound |
| `color` | ColorPicker | RGB/hex picker with transparency support |
| `file` | FileBrowser | Asset file browser with upload support |
| `level` | LevelLink | Click to jump to level editor view |
| `lua` | LuaEditor | Monaco with Lua syntax, `ams.*` completions, error markers |
| `yaml` | YamlEditor | Monaco with YAML syntax, schema validation, $ref support |
| `behavior` | BehaviorPicker | List behaviors with config schema preview |
| `entity_type` | EntityPicker | List entity types with sprite preview |

### Code Field Editors (Lua & YAML)

For `x-content-type: lua` and `x-content-type: yaml` fields, the IDE opens a dedicated code editor panel rather than inline editing. This provides:

**Lua Editor (`x-content-type: lua`):**
```yaml
# In game.yaml - inline Lua behavior
behaviors:
  custom_bounce:
    lua: |                    # ← x-content-type: lua
      function on_update(entity, dt)
        if ams.get_y(entity) > 500 then
          ams.set_vy(entity, -ams.get_vy(entity) * 0.8)
        end
      end
```

Features:
- Full Monaco editor with Lua syntax highlighting
- `ams.*` API autocomplete (get_x, set_vy, spawn, destroy, etc.)
- Function signature hints from Lua API documentation
- Syntax error highlighting
- Expand to full-screen editor mode
- **Sandbox violation warnings** - flags use of blocked globals

**Sandbox-Aware Linting:**

The Lua sandbox removes dangerous functions for security. The IDE warns immediately:

```lua
function on_update(entity, dt)
  local f = io.open("secrets.txt")  -- ⚠️ Warning: 'io' is not available (sandboxed)
  os.execute("rm -rf /")            -- ⚠️ Warning: 'os' is not available (sandboxed)
  require("socket")                 -- ⚠️ Warning: 'require' is not available (sandboxed)
  debug.getinfo(1)                  -- ⚠️ Warning: 'debug' is not available (sandboxed)
end
```

Blocked globals (from `LUA_SECURITY.md`):
- `io`, `os`, `debug`, `package` - removed entirely
- `require`, `loadfile`, `dofile`, `load` - no dynamic code loading
- `rawget`, `rawset`, `getmetatable`, `setmetatable` - no metatable access
- `string.dump` - no bytecode access
- `string.rep` - limited to prevent memory bombs

**YAML Editor (`x-content-type: yaml`):**
```yaml
# In game.yaml - embedded level definition
levels:
  - level: level1
    inline: |                 # ← x-content-type: yaml
      entities:
        - type: brick
          grid: { cols: 10, rows: 3 }
```

Features:
- Monaco with YAML syntax + schema validation
- Autocomplete from referenced schema (level.schema.json)
- Inline error markers for schema violations
- Expand to full-screen editor mode

**UI Interaction:**

```
+------------------------------------------------------------------+
|  Monaco Editor                                                     |
|------------------------------------------------------------------|
|  entity_types:                                                    |
|    duck:                                                          |
|      sprite: duck_flying  ← cursor here                           |
|              └─────────────────────────────────────────────┐      |
|                                                            │      |
|  +--------------------------------------------------+      │      |
|  │ SPRITE PICKER                           [×]      │◄─────┘      |
|  │ ┌────────┐ ┌────────┐ ┌────────┐               │              |
|  │ │[sprite]│ │[sprite]│ │[sprite]│               │              |
|  │ │  duck  │ │ duck_l │ │ duck_r │ ← click to    │              |
|  │ │ flying │ │ flying │ │ flying │   select      │              |
|  │ └────────┘ └────────┘ └────────┘               │              |
|  │ Search: [________________]                      │              |
|  +--------------------------------------------------+             |
+------------------------------------------------------------------+
```

**Implementation:**

```svelte
<!-- ContentTypeEditor.svelte -->
<script>
  export let fieldType;  // from x-content-type in schema
  export let currentValue;
  export let onSelect;
  export let assets;  // from asset manifest

  const editors = {
    sprite: SpritePicker,
    sound: SoundPicker,
    color: ColorPicker,
    // ...
  };
</script>

<svelte:component this={editors[fieldType]}
  value={currentValue}
  {assets}
  on:select={onSelect}
/>
```

### Files to Create

```
src/lib/ide/
├── AssetBrowser.svelte       # Sidebar asset browser panel
├── AssetManifest.js          # Parse/cache asset manifest from engine
├── content-editors/
│   ├── SpritePicker.svelte   # Grid picker for sprites
│   ├── SoundPicker.svelte    # List with play buttons
│   ├── ColorPicker.svelte    # RGB/hex color picker
│   ├── FileBrowser.svelte    # File/asset browser
│   ├── BehaviorPicker.svelte # Behavior selection with config preview
│   └── EntityPicker.svelte   # Entity type selection
└── ContentTypeEditor.svelte  # Router component for type-aware editing
```

### Success Criteria

- [ ] Asset browser shows all sprites/sounds from registry
- [ ] Typing `sprite:` triggers autocomplete with registered sprites
- [ ] Clicking a sprite field opens sprite picker overlay
- [ ] Color fields show color picker with live preview
- [ ] Asset provenance (author, license) visible in browser

---

## Phase 2: Visual Editors (3-4 weeks)

**Goal:** Non-coders can create sprites and levels visually.

### Sprite Sheet Editor

```
+------------------------------------------------------------------+
|  SPRITE SHEET EDITOR                                              |
+------------------------------------------------------------------+
| +------------------------+  +----------------------------------+ |
| | [Sprite Sheet Image]   |  | Sprite Definition                | |
| | [Selection Rectangle]  |  |                                  | |
| |                        |  | Name: duck_flying_right          | |
| | Zoom: [+][-] 100%      |  | X: 0    Y: 126   W: 37   H: 42   | |
| +------------------------+  | Flip X: [ ] Flip Y: [ ]          | |
|                             | Transparent: [159,227,163]       | |
| +------------------------+  |                                  | |
| | Extracted Sprites      |  | Inherits: _ducks_base            | |
| | > duck_flying_right    |  +----------------------------------+ |
| | > duck_flying_left     |                                       |
| +------------------------+  [ Generate YAML ]                    |
+------------------------------------------------------------------+
```

**Features:**
- Upload sprite sheets (PNG, JPG)
- Drag to select regions
- Auto-detect boundaries (optional)
- Generate `assets.sprites` YAML
- Support sprite inheritance

### Level Layout Editor

```
+------------------------------------------------------------------+
|  LEVEL EDITOR                                    Mode: [Visual]   |
+------------------------------------------------------------------+
| +----------------+  +----------------------------------------+   |
| | Entity Palette |  | Level Grid                             |   |
| |                |  |                                        |   |
| | [brick_blue]   |  |  B B B B B B B B B B                   |   |
| | [brick_red]    |  |  R R R R R R R R R R                   |   |
| | [brick_yellow] |  |  Y Y Y Y Y Y Y Y Y Y                   |   |
| | [invader]      |  |  . . . . . . . . . .                   |   |
| | [...]          |  |                                        |   |
| +----------------+  +----------------------------------------+   |
|                                                                   |
| Grid: 10x5   Brick: 70x25   Start: (65, 60)   Spacing: 0x0       |
+------------------------------------------------------------------+
```

**Features:**
- Visual grid with entity icons
- Click to place, drag to fill
- ASCII mode for power users
- Configure grid parameters
- Preview entity types from palette

### Project Persistence

- Save to Emscripten IDBFS (survives refresh, syncs to IndexedDB)
- Export as ZIP (game.yaml + levels + assets)
- Import from ZIP

### Files to Create

```
ams/web_controller/frontend/src/lib/
├── visual/
│   ├── SpriteSheetEditor.svelte
│   ├── SpriteRegionSelector.svelte
│   ├── LevelEditor.svelte
│   ├── LevelGrid.svelte
│   ├── EntityPalette.svelte
│   └── AsciiEditor.svelte
├── project/
│   ├── ProjectManager.js         # Save/load with IDBFS
│   └── ExportManager.js          # ZIP export
```

### Success Criteria

- [ ] Upload sprite sheet, extract 10+ sprites
- [ ] Create level layout visually
- [ ] Save project, close browser, reopen → project restored
- [ ] Export ZIP, import elsewhere → works

---

## Phase 3: Lua Debugger (2-3 weeks)

**Goal:** Debug behaviors interactively.

### Debugger UI

```
+------------------------------------------------------------------+
|  LUA DEBUGGER                                                     |
+------------------------------------------------------------------+
| [▶ Play] [⏸ Pause] [→ Step] [↓ Step Into]    Frame: 1234         |
+------------------------------------------------------------------+
| +----------------------+  +------------------------------------+ |
| | BREAKPOINTS          |  | WATCH EXPRESSIONS                  | |
| | ● rope_link.lua:34   |  | entity.x         → 400.5           | |
| | ○ gravity.lua:12     |  | entity.vy        → 125.3           | |
| +----------------------+  +------------------------------------+ |
| +----------------------+  +------------------------------------+ |
| | CALL STACK           |  | LOCAL VARIABLES                    | |
| | → rope_link:on_update|  | entity_id: "candy_abc123"          | |
| |   gravity:on_update  |  | dt: 0.016                          | |
| +----------------------+  | rest_length: 30                    | |
+------------------------------------------------------------------+
| CONSOLE                                                           |
| > ams.get_x("candy_abc123")                                       |
| 400.5                                                             |
| > ams.set_prop("candy_abc123", "debug", true)                     |
| nil                                                               |
+------------------------------------------------------------------+
```

### Features

1. **Breakpoint Management**
   - Set breakpoints by clicking line numbers
   - Conditional breakpoints (optional)
   - Persist across sessions

2. **Execution Control**
   - Play/Pause game loop
   - Step Over (next line)
   - Step Into (enter function)
   - Continue to next breakpoint

3. **State Inspection**
   - View local variables at breakpoint
   - Watch expressions (custom)
   - Entity property viewer

4. **Lua Console (REPL)**
   - Execute arbitrary Lua
   - Auto-complete for `ams.*`
   - History (up/down arrows)

### Implementation

WASMOON supports debug hooks:

```typescript
lua.global.set('__ams_debug_hook', (event, line) => {
    if (event === 'line' && breakpoints.has(currentFile, line)) {
        pauseExecution();
        sendToIDE({ type: 'breakpoint_hit', file: currentFile, line });
    }
});

await lua.doString(`
    debug.sethook(__ams_debug_hook, "l")
`);
```

### Files to Create

```
ams/web_controller/frontend/src/lib/debug/
├── Debugger.svelte
├── BreakpointGutter.svelte
├── CallStack.svelte
├── VariableInspector.svelte
├── WatchExpressions.svelte
├── Console.svelte
├── DebugSession.js
├── BreakpointManager.js
└── LuaEvaluator.js
```

### Success Criteria

- [ ] Set breakpoint, execution pauses at line
- [ ] Inspect entity properties at breakpoint
- [ ] Step through `on_update` function
- [ ] Console evaluates `ams.get_x(id)`

---

## Phase 4: Sharing and Polish (2-3 weeks)

**Goal:** Share games with the world.

### Export Options

1. **ZIP Archive**
   - game.yaml + levels/ + lua/ + assets/
   - Importable by other IDE users
   - Works with local Python setup

2. **Standalone HTML**
   - Single file, playable anywhere
   - Embeds all assets as data URIs
   - Includes minimal pygbag runtime

3. **Shareable Link**
   - Small games: URL-encoded data
   - Large games: Server-stored with ID
   - Example: `https://ams.games/play?id=abc123`

### Gallery/Showcase

```
+------------------------------------------------------------------+
|  AMS GAME GALLERY                                                 |
+------------------------------------------------------------------+
| +----------------+ +----------------+ +----------------+          |
| | [Screenshot]   | | [Screenshot]   | | [Screenshot]   |          |
| | Space Bricks   | | Duck Hunt Rem  | | Fruit Ninja    |          |
| | by @creator    | | by @hunter     | | by @slicer     |          |
| | ★★★★☆ (42)     | | ★★★★★ (128)    | | ★★★★☆ (67)     |          |
| | [Play] [Fork]  | | [Play] [Fork]  | | [Play] [Fork]  |          |
| +----------------+ +----------------+ +----------------+          |
|                                                                   |
| [Upload Your Game]                    Sort: [Popular] [Recent]    |
+------------------------------------------------------------------+
```

### Hosting Options

**Option A: Static (Vercel/Netlify/GitHub Pages)**
- IDE + pygbag bundle
- Games in localStorage only
- Sharing via URL-encoded data (size limited)

**Option B: With Backend (Recommended for sharing)**
- Simple API: POST game → ID, GET game by ID
- CDN for WASM bundles
- Optional user accounts
- Gallery with ratings

### Files to Create

```
ams/web_controller/frontend/src/lib/
├── sharing/
│   ├── ExportZip.js
│   ├── ExportHtml.js
│   └── ShareLink.js
├── Gallery.svelte
├── ExportDialog.svelte
└── ShareDialog.svelte
```

### Success Criteria

- [ ] Export ZIP, import on another machine
- [ ] Generate shareable link
- [ ] Open link → game plays immediately
- [ ] Browse gallery, fork game to edit

---

## Security Considerations

### Lua Sandbox (WASMOON)

Apply identical restrictions as Python `LuaEngine`:

```lua
-- BLOCKED
io = nil
os = nil
debug = nil
package = nil
require = nil
loadfile = nil
dofile = nil
load = nil
rawget = nil
rawset = nil
getmetatable = nil
setmetatable = nil

-- ALLOWED
math.*
string.* (except string.dump, string.rep limited)
pairs, ipairs, type, tonumber, tostring
pcall, error, next
```

### User Content

- Sanitize uploaded files (images only)
- No server-side code execution
- CSP headers prevent XSS
- Same-origin iframe policy

### Storage Limits

- Warn at 50MB project size
- IndexedDB quota varies by browser
- Offer export for large projects

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Fengari performance | Medium | Profile if needed; Fengari is stable but slower than native |
| Lua 5.3 vs 5.4 differences | Low | Minor syntax differences; test behaviors in both |
| IndexedDB quota | Medium | Warn user; support external storage; compress assets |
| pygbag version drift | Medium | Pin version; integration tests |
| Large sprite sheets | Medium | Chunked loading; OPFS for big files |
| Mobile browser quirks | Low | Test matrix; graceful degradation |

---

## Open Questions

1. **Hosting model:** Static-only or with backend for sharing?
2. **Collaboration:** Real-time multi-user editing (future scope)?
3. **Mobile:** Touch-friendly editing on tablets (future scope)?
4. **Offline:** Service worker for offline editing?

---

## Resources

- [Monaco Editor](https://microsoft.github.io/monaco-editor/)
- [Fengari](https://fengari.io/) - Lua 5.3 in JavaScript
- [Pygbag](https://pygame-web.github.io/)
- [Vite](https://vitejs.dev/)
- [Svelte](https://svelte.dev/)

---

## Docker Quick Reference

```bash
# Start full stack (IDE + game server + logging)
# NOTE: First start takes ~2 minutes (frontend + pygbag builds)
docker compose up --build

# ide-server Dockerfile runs: npm install && npm run build
# web-server entrypoint runs: python games/browser/build.py

# Force rebuild pygbag (after game code changes)
docker compose down -v              # Clear build cache
docker compose up                   # Triggers fresh build

# Or set environment variable
FORCE_REBUILD=1 docker compose up

# Access points (port 8000 for pygbag CDN compatibility)
# http://localhost:8000/author    - IDE
# http://localhost:8000/          - Game launcher
# http://localhost:8000/pygbag/   - Game runtime (preview iframe target)
# http://localhost:8000/api/projects - Projects API
# http://localhost:8000/archives/ - Pygame CDN proxy (wheel downloads)

# Persistence locations
# ./data/projects/      - User projects (host volume)
# pygbag-build volume   - WebAssembly build cache (Docker volume)
```

Services:
- **nginx** (port 8000) - Reverse proxy, routes to all services, proxies /archives to pygame CDN
- **ide-server** (port 8003) - FastAPI file API, serves IDE frontend
- **web-server** (port 8000 internal) - pygbag game server (auto-builds on first start)
- **log-server** (ports 8001-8002) - WebSocket log streaming

### Auto-build Flow

On first `docker compose up`, the web-server:
1. Runs `games/browser/build.py` to compile Python games to WebAssembly
2. Copies YAML→JSON converted game definitions
3. Patches index.html with error handlers
4. Caches build in Docker volume (persists across restarts)
5. Serves from `/build/web/output/build/web/`

Key files:
- `docker/web-server/entrypoint.sh` - Build orchestration
- `docker/web-server/Dockerfile` - Includes pygbag, pygame-ce, pyyaml
- `games/browser/build.py` - Pygbag build script

---

## Related Documents

- `docs/architecture/BROWSER_LUA_BRIDGE.md` - **Browser Lua implementation details**
- `docs/planning/BROWSER_DEPLOYMENT.md` - Foundation (Phases 1-3 complete)
- `docs/planning/WEB_CONTROLLER.md` - Mobile control interface
- `docs/guides/lua_scripting.md` - Lua API reference
- `docs/guides/GAME_ENGINE_ARCHITECTURE.md` - Engine internals
