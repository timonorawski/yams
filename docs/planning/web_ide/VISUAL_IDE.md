# YAMS Visual Web IDE
**Project codename:** CubedYams
**Status:** Foundation complete, features in progress
**Goal:** Browser-based game editor with live preview, schema-driven config, and debugging tools.

## 1. Current State Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Monaco Editor | ✅ Working | YAML/Lua syntax, themes |
| Split-pane layout | ✅ Working | Resizable editor/preview |
| File tree | 🚧 Partial | UI exists, API not wired |
| Preview iframe | ✅ Working | IDE bridge + postMessage |
| IDE ↔ Engine bridge | ✅ Working | `ide_bridge.js` + `ide_bridge.py` |
| Engine ready signal | ✅ Working | Hides loading overlay when game starts |
| JSON schemas | ✅ Complete | game, level, lua_script schemas |
| Schema validation | Not wired | Schemas exist but Monaco not configured |
| Config auto-generation | Not started | No UI generator from schemas |
| Log streaming | Not started | WebSocket exists but no log forwarding |
| Profiler UI | Not started | No flame graph components |
| Debugger UI | Not started | No breakpoints/stepping UI |
| Tailwind/DaisyUI | 🚧 In progress | Migration from vanilla CSS |

## 2. Tech Stack

| Layer | Technology | Status |
|-------|------------|--------|
| Framework | Svelte 4.2 + Vite 5.0 | Working |
| Editor | Monaco 0.52.0 | Working |
| Styling | Tailwind + daisyUI | To add |
| Runtime | pygbag + Fengari | Working |
| Communication | WebSocket (state sync) | Working |
| Schemas | JSON Schema | Files exist |

**Current dependencies** (`package.json`):
```json
{
  "dependencies": {
    "js-yaml": "^4.1.0",
    "monaco-editor": "^0.52.0"
  },
  "devDependencies": {
    "@sveltejs/vite-plugin-svelte": "^3.0.0",
    "svelte": "^4.2.0",
    "vite": "^5.0.0"
  }
}
```

> **Note:** `js-yaml` is required because PyYAML doesn't work in WASM. Monaco parses YAML and converts to JSON before sending to the engine.

**To add for styling:**
```bash
npm install -D tailwindcss postcss autoprefixer daisyui
```

### Tailwind + daisyUI Setup

daisyUI provides pre-built components that map to IDE needs:

| daisyUI Component | IDE Usage |
|-------------------|-----------|
| `tabs` | Bottom panel tabs (logs, profiler, debugger) |
| `dropdown` | Config panel enum selectors |
| `range` | Config panel numeric sliders |
| `toggle` | Config panel booleans |
| `collapse` | File tree folders |
| `modal` | Dialogs (save, errors, confirmations) |
| `btn` | Toolbar and panel buttons |
| `tooltip` | Schema descriptions on hover |
| `input` | Text fields in config panel |

```javascript
// tailwind.config.js
export default {
  content: ['./src/**/*.{svelte,js,ts}', './index.html', './*.html'],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: ['dark'],  // VS Code-like dark theme
  },
}
```

Existing vanilla CSS will coexist during migration. New components should use Tailwind/daisyUI.

## 3. Current Layout

```
+-------------------------------------------------------------+
|  AMS Editor  •  game.yaml                    [Run] [Save]   |
+-------------------------------------------------------------+
|  Files       |  Monaco Editor        |  Preview (iframe)    |
|  (sidebar)   |  (YAML/Lua)          |  (pygbag game)       |
|              |                       |                       |
|  game.yaml   |  name: My Game        |  ┌─────────────┐     |
|  levels/     |  screen_width: 800    |  │             │     |
|    level1    |  entity_types:        |  │   [game]    │     |
|  lua/        |    target:            |  │             │     |
|    behaviors/|      width: 50        |  └─────────────┘     |
|              |                       |                       |
+-------------------------------------------------------------+
|  Ready  •  YAML  •  UTF-8                                   |
+-------------------------------------------------------------+
```

## 4. Existing Components

### 4.1 MonacoEditor.svelte (Working)
**Location:** `src/lib/ide/MonacoEditor.svelte`

```svelte
<script>
  import * as monaco from 'monaco-editor';
  export let value = '';
  export let language = 'yaml';

  onMount(() => {
    editor = monaco.editor.create(container, {
      value,
      language,
      theme: 'vs-dark',
      automaticLayout: true,
      minimap: { enabled: false },
      lineNumbers: 'on',
      wordWrap: 'on',
    });

    editor.onDidChangeModelContent(() => {
      dispatch('change', { value: editor.getValue() });
    });
  });
</script>
```

Features:
- Dynamic language switching (yaml/lua)
- VS Code dark theme
- Change event dispatching
- Auto-layout on resize

### 4.2 FileTree.svelte (Basic)
**Location:** `src/lib/ide/FileTree.svelte`

```svelte
<script>
  export let files = [];
  function handleClick(file) {
    if (file.type === 'folder') {
      file.expanded = !file.expanded;
    } else {
      dispatch('select', { path: file.name });
    }
  }
</script>
```

Features:
- Folder expand/collapse
- File type icons (emojis)
- Selection events

Missing:
- Actual file loading from server
- Create/delete/rename operations
- Drag-and-drop

### 4.3 PreviewFrame.svelte (Working)
**Location:** `src/lib/ide/PreviewFrame.svelte`

```svelte
<script>
  export let gameYaml = '';

  function sendHotReload() {
    iframe?.contentWindow?.postMessage({
      type: 'hot_reload',
      data: { path: 'game.yaml', content: gameYaml }
    }, '*');
  }

  // Debounced reload on gameYaml change
  $: if (gameYaml && iframe) {
    clearTimeout(reloadTimeout);
    reloadTimeout = setTimeout(sendHotReload, 500);
  }

  // Listen for game messages
  window.addEventListener('message', (e) => {
    if (e.data.type === 'lua_crashed') {
      error = e.data.data.error;
    }
  });
</script>

<iframe src="/pygbag/" bind:this={iframe} />
```

Features:
- Embeds pygbag game in iframe
- Hot reload via postMessage
- Lua crash error display
- Loading spinner

### 4.4 Author.svelte (Layout Working)
**Location:** `src/Author.svelte`

Features:
- Split-pane with draggable divider
- Toolbar with Run/Save buttons (not wired)
- Status bar
- VS Code-like dark theme

TODOs in code:
- Line 49: `// TODO: Debounced hot reload` - partially done
- Line 54: `// TODO: Load file content` - not implemented

## 5. JSON Schemas (Complete)

**Locations:**
- `ams/games/game_engine/schemas/game.schema.json` (source)
- `ams/games/game_engine/schemas/level.schema.json` (source)
- `ams/games/game_engine/lua/lua_script.schema.json` (source)
- `frontend/public/schemas/` (copied for frontend)

### game.schema.json
Defines complete game structure:
- Screen dimensions, background
- Entity types with properties
- Collision behaviors
- Input mapping
- Win/lose conditions
- Render commands

### level.schema.json
Defines level layout:
- Entity instances with positions
- Spawn patterns
- Level-specific overrides

### lua_script.schema.json
Defines Lua behavior metadata:
```json
{
  "config": {
    "type": "object",
    "properties": {
      "acceleration": {
        "type": "number",
        "minimum": 0,
        "maximum": 2000,
        "default": 800,
        "description": "Downward acceleration in pixels/sec²"
      }
    }
  }
}
```

This schema could power auto-generated config UI (sliders, dropdowns) but no generator exists yet.

## 6. What Needs Building

### 6.1 Schema Validation in Monaco
Wire Monaco to validate against JSON schemas:

```javascript
// In MonacoEditor.svelte
monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
  validate: true,
  schemas: [{
    uri: '/schemas/game.schema.json',
    fileMatch: ['game.yaml', '*.game.yaml']
  }]
});

// For YAML: use monaco-yaml plugin
import { configureMonacoYaml } from 'monaco-yaml';
configureMonacoYaml(monaco, {
  schemas: [{
    uri: '/schemas/game.schema.json',
    fileMatch: ['game.yaml']
  }]
});
```

### 6.2 Auto-Generated Config Panel
Generate UI from lua_script.schema.json metadata using daisyUI components:

```svelte
<!-- ConfigPanel.svelte -->
<script>
  export let schema;  // From lua_script.schema.json
  export let values;  // Current config values
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  function getWidget(meta) {
    if (meta.enum) return 'dropdown';
    if (meta.type === 'boolean') return 'toggle';
    if (meta.type === 'number' && meta.minimum !== undefined) return 'slider';
    return 'text';
  }

  function handleChange(name, value) {
    values[name] = value;
    dispatch('change', { name, value, values });
  }
</script>

<div class="flex flex-col gap-4 p-4">
  {#each Object.entries(schema.properties) as [name, meta]}
    <div class="form-control">
      <label class="label">
        <span class="label-text">{meta.title || name}</span>
        {#if meta.description}
          <span class="tooltip tooltip-left" data-tip={meta.description}>
            <span class="text-info">ⓘ</span>
          </span>
        {/if}
      </label>

      {#if getWidget(meta) === 'slider'}
        <div class="flex items-center gap-2">
          <input type="range" class="range range-sm range-primary flex-1"
            min={meta.minimum}
            max={meta.maximum}
            step={meta.multipleOf || 1}
            value={values[name]}
            on:input={(e) => handleChange(name, +e.target.value)}
          />
          <span class="badge badge-neutral w-16">{values[name]}</span>
        </div>

      {:else if getWidget(meta) === 'dropdown'}
        <select class="select select-bordered select-sm"
          value={values[name]}
          on:change={(e) => handleChange(name, e.target.value)}>
          {#each meta.enum as option}
            <option value={option}>{option}</option>
          {/each}
        </select>

      {:else if getWidget(meta) === 'toggle'}
        <input type="checkbox" class="toggle toggle-primary"
          checked={values[name]}
          on:change={(e) => handleChange(name, e.target.checked)}
        />

      {:else}
        <input type="text" class="input input-bordered input-sm"
          value={values[name]}
          on:input={(e) => handleChange(name, e.target.value)}
        />
      {/if}
    </div>
  {/each}
</div>
```

### 6.3 File Persistence
Options:
1. **IndexedDB** - Browser-only, no server needed
2. **File System Access API** - Direct local file access (Chrome only)
3. **Server API** - POST/GET to backend

```javascript
// IndexedDB approach
const db = await openDB('yams-ide', 1, {
  upgrade(db) {
    db.createObjectStore('files');
  }
});

async function saveFile(path, content) {
  await db.put('files', content, path);
}

async function loadFile(path) {
  return await db.get('files', path);
}
```

### 6.4 Log Streaming
Add WebSocket channel for logs:

```python
# In server.py
async def stream_logs(websocket):
    while True:
        log = await log_queue.get()
        await websocket.send_json({
            "type": "log",
            "level": log.level,
            "module": log.module,
            "message": log.message,
            "timestamp": log.timestamp
        })
```

```svelte
<!-- LogPanel.svelte -->
<script>
  export let ws;
  let logs = [];
  let filter = { level: 'all', module: 'all' };
  let modules = ['all'];

  ws.addEventListener('message', (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'log') {
      logs = [...logs.slice(-999), msg];
      if (!modules.includes(msg.module)) modules = [...modules, msg.module];
    }
  });

  $: filteredLogs = logs.filter(l =>
    (filter.level === 'all' || l.level === filter.level) &&
    (filter.module === 'all' || l.module === filter.module)
  );

  const levelColors = {
    DEBUG: 'badge-ghost',
    INFO: 'badge-info',
    WARN: 'badge-warning',
    ERROR: 'badge-error'
  };
</script>

<div class="flex flex-col h-full">
  <div class="flex gap-2 p-2 border-b border-base-300">
    <select class="select select-xs" bind:value={filter.level}>
      <option value="all">All Levels</option>
      <option value="DEBUG">DEBUG</option>
      <option value="INFO">INFO</option>
      <option value="WARN">WARN</option>
      <option value="ERROR">ERROR</option>
    </select>
    <select class="select select-xs" bind:value={filter.module}>
      {#each modules as mod}
        <option value={mod}>{mod}</option>
      {/each}
    </select>
    <button class="btn btn-xs btn-ghost ml-auto" on:click={() => logs = []}>
      Clear
    </button>
  </div>

  <div class="flex-1 overflow-y-auto font-mono text-xs">
    {#each filteredLogs as log}
      <div class="flex gap-2 px-2 py-0.5 hover:bg-base-200">
        <span class="badge {levelColors[log.level]} badge-xs">{log.level}</span>
        <span class="opacity-50">{log.module}</span>
        <span>{log.message}</span>
      </div>
    {/each}
  </div>
</div>
```

## 7. Bottom Panel Tabs (To Build)

```svelte
<!-- BottomPanel.svelte -->
<script>
  export let ws;
  let activeTab = 'logs';
</script>

<div class="flex flex-col h-64 border-t border-base-300 bg-base-200">
  <div role="tablist" class="tabs tabs-bordered bg-base-300">
    <button role="tab" class="tab" class:tab-active={activeTab === 'logs'}
      on:click={() => activeTab = 'logs'}>
      Logs
    </button>
    <button role="tab" class="tab" class:tab-active={activeTab === 'profiler'}
      on:click={() => activeTab = 'profiler'}>
      Profiler
    </button>
    <button role="tab" class="tab" class:tab-active={activeTab === 'timemachine'}
      on:click={() => activeTab = 'timemachine'}>
      Time Machine
    </button>
    <button role="tab" class="tab" class:tab-active={activeTab === 'debugger'}
      on:click={() => activeTab = 'debugger'}>
      Debugger
    </button>
  </div>

  <div class="flex-1 overflow-hidden">
    {#if activeTab === 'logs'}
      <LogPanel {ws} />
    {:else if activeTab === 'profiler'}
      <ProfilerPanel {ws} />
    {:else if activeTab === 'timemachine'}
      <TimeMachinePanel {ws} />
    {:else if activeTab === 'debugger'}
      <DebuggerPanel {ws} />
    {/if}
  </div>
</div>
```

### Tab 1: Logs
- Real-time log streaming (WebSocket)
- Filter by level (DEBUG, INFO, WARN, ERROR)
- Filter by module
- Click log → jump to source

### Tab 2: Profiler
- Flame graph (d3-flamegraph)
- Frame timing breakdown
- Entity update costs
- Requires: `ams/profiling.py` integration

### Tab 3: Time Machine
- Frame slider (0 → current)
- Step backward/forward buttons
- Visual diff of frame changes
- Requires: Rollback snapshot integration

### Tab 4: Debugger
- Breakpoint gutter in Monaco
- Step controls (F5, F10, F11)
- Locals panel
- Call stack viewer
- Requires: Fengari debug hooks

## 8. Entry Points

| Entry | File | Purpose |
|-------|------|---------|
| Play mode | `index.html` → `App.svelte` | Game launcher + controls |
| IDE | `author.html` → `Author.svelte` | Editor + preview |
| Standalone play | `play.html` → `Play.svelte` | Direct game embed |

Vite config handles multi-entry build:
```javascript
build: {
  rollupOptions: {
    input: {
      main: 'index.html',
      play: 'play.html',
      author: 'author.html'
    }
  }
}
```

## 9. Implementation Priorities

### Phase 1: Complete MVP Editor
1. Wire file loading from FileTree selection
2. Add monaco-yaml for schema validation
3. Implement IndexedDB file persistence
4. Wire Save button to persist

### Phase 2: Config Panel
1. Create ConfigPanel.svelte
2. Parse lua_script schemas for config metadata
3. Generate sliders/dropdowns from schema
4. Wire config changes to hot reload

### Phase 3: Bottom Panels
1. Log streaming (WebSocket + UI)
2. Profiler integration (after `ams/profiling.py`)
3. Time machine (after rollback exposure)
4. Debugger (after Fengari debug hooks)

### Phase 4: Polish
1. Keyboard shortcuts (Cmd+S, F5, etc.)
2. Multiple file tabs
3. Error markers in editor gutter
4. Mobile-responsive layout

## 10. Development

```bash
# Option 1: Docker (recommended - full stack)
docker compose up --build
open http://localhost:8000/author

# Option 2: Standalone frontend dev
cd ams/web_controller/frontend
npm run dev
open http://localhost:5173/author.html
# Note: Preview won't work without Docker backend
```

Docker serves on port 8000 (required for pygbag CDN compatibility).

Vite dev proxies (for standalone mode):
- `/api` → `http://localhost:8000`
- `/ws` → `ws://localhost:8000`
- `/pygbag` → `http://localhost:8000`
