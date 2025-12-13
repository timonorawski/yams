# YAMS Visual Web IDE
**Project codename:** CubedYams
**Status:** Foundation complete, features in progress
**Goal:** Browser-based game editor with live preview, schema-driven config, and debugging tools.

## 1. Current State Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Monaco Editor | ✅ Working | YAML/Lua syntax, themes |
| Split-pane layout | ✅ Working | Resizable editor/preview |
| File tree | ✅ Working | API wired, file CRUD working |
| Preview iframe | ✅ Working | IDE bridge + postMessage |
| IDE ↔ Engine bridge | ✅ Working | `ide_bridge.js` + `ide_bridge.py` |
| Hot reload | ✅ Working | **Auto-reload on file change** (reactive) |
| Engine ready signal | ✅ Working | Hides loading overlay when game starts |
| JSON schemas | ✅ Complete | game, level, lua_script, assets schemas |
| Project persistence | ✅ Working | Server API with recursive file listing |
| WASM compatibility | ✅ Working | Threading, JS/Python boundary fixes |
| Schema validation | Not wired | Schemas exist but Monaco not configured |
| **Log streaming** | 🚧 Next | Engine logs to IDE panel via postMessage |
| Config auto-generation | Not started | No UI generator from schemas |
| Asset browser | Not started | Asset registry integration planned |
| **Profiler UI** | ✅ Working | `/profiler` - file viewer with call tree + detail panel |
| Debugger UI | Not started | No breakpoints/stepping UI |
| Tailwind/DaisyUI | ✅ Working | daisyUI components in use |

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
  export let projectFiles = {};
  export let engineUrl = '/pygbag/?mode=ide';

  let initialFilesSent = false;
  let lastFilesHash = '';

  // Convert YAML to JSON before sending (PyYAML doesn't work in WASM)
  function prepareFiles() {
    const jsonFiles = {};
    for (const [path, content] of Object.entries(projectFiles)) {
      if (path.endsWith('.yaml') || path.endsWith('.yml')) {
        const jsonPath = path.replace(/\.ya?ml$/, '.json');
        jsonFiles[jsonPath] = yaml.load(content);
      } else {
        jsonFiles[path] = content;
      }
    }
    return jsonFiles;
  }

  // Watch for file changes after initial load (reactive hot reload)
  $: if (initialFilesSent && engineReady && Object.keys(projectFiles).length > 0) {
    const newHash = computeFilesHash(projectFiles);
    if (newHash !== lastFilesHash) {
      sendFileUpdate();  // Auto-reload on change
    }
  }

  // Handle 'ready' message from engine
  function handleMessage(event) {
    if (event.data.type === 'ready') {
      engineReady = true;
      sendFilesAndReload();  // Initial file send
    }
  }
</script>

<iframe src={engineUrl} bind:this={iframe} />
```

Features:
- Embeds pygbag game in iframe with IDE mode
- YAML → JSON conversion (PyYAML not available in WASM)
- Initial file send on engine ready
- **Reactive hot reload**: auto-sends files when `projectFiles` changes
- Hash-based change detection to avoid redundant sends
- Engine ready signal handling

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

### Phase 1: Complete MVP Editor ✅ COMPLETE
1. ~~Wire file loading from FileTree selection~~ ✅
2. ~~Implement server API file persistence~~ ✅
3. ~~Wire Save button to persist~~ ✅
4. ~~Wire Run button to hot reload~~ ✅
5. ~~Reactive hot reload on file change~~ ✅
6. ~~WASM compatibility fixes~~ ✅
   - Threading-safe profiling (`ams/profiling.py`)
   - JS/Python boundary handling (JSON serialization)
   - `_frame_count` initialization in GameEngine

### Phase 1.1: Log Streaming 🚧 NEXT
**Goal:** Real-time engine logs in IDE for debugging hot reload and game behavior.

1. Add log forwarding from Python to JS via postMessage
2. Create LogPanel.svelte component with filtering
3. Wire to bottom panel in Author.svelte
4. Add log level filtering (DEBUG, INFO, WARN, ERROR)

See **Section 12: Log Streaming Implementation** below for details.

### Phase 1.5: Asset Registry & Content-Type Editors
1. Receive asset manifest from engine via postMessage
2. Build AssetBrowser sidebar component
3. Implement content-type aware field editors
4. Wire autocomplete for sprite/sound fields

### Phase 2: Config Panel
1. Create ConfigPanel.svelte
2. Parse lua_script schemas for config metadata
3. Generate sliders/dropdowns from schema
4. Wire config changes to hot reload

### Phase 3: Bottom Panels
1. ~~Log streaming~~ (Phase 1.1)
2. Profiler integration (after `ams/profiling.py`)
3. Time machine (after rollback exposure)
4. Debugger (after Fengari debug hooks)

### Phase 4: Polish
1. Keyboard shortcuts (Cmd+S, F5, etc.)
2. Add monaco-yaml for schema validation
3. Multiple file tabs
4. Error markers in editor gutter
5. Mobile-responsive layout

---

## 10. Asset Registry Integration

The engine's `AssetRegistry` discovers asset definitions from `assets/*.json` files. The IDE can leverage this for intelligent editing features.

### Asset Manifest Protocol

```javascript
// Engine → IDE (on game load)
{
  type: 'asset_manifest',
  sprites: {
    'duck_flying': { file: 'sprites.png', x: 0, y: 126, width: 37, height: 42 },
    'duck_left': { file: 'sprites.png', x: 37, y: 126, width: 37, height: 42 },
    // ...
  },
  sounds: {
    'shot': { file: 'shot.wav', volume: 0.8 },
    // ...
  },
  provenance: {
    'sprites': { source: 'Nintendo Duck Hunt (NES, 1984)', license: 'proprietary' }
  }
}
```

### Asset Browser Component

```svelte
<!-- AssetBrowser.svelte -->
<script>
  export let manifest = { sprites: {}, sounds: {} };
  let filter = '';
  let activeTab = 'sprites';

  $: filteredSprites = Object.entries(manifest.sprites)
    .filter(([name]) => name.includes(filter));

  $: filteredSounds = Object.entries(manifest.sounds)
    .filter(([name]) => name.includes(filter));
</script>

<div class="flex flex-col h-full bg-base-200">
  <div class="p-2 border-b border-base-300">
    <input type="text" class="input input-xs w-full"
      placeholder="Search assets..."
      bind:value={filter} />
  </div>

  <div role="tablist" class="tabs tabs-xs tabs-bordered">
    <button class="tab" class:tab-active={activeTab === 'sprites'}
      on:click={() => activeTab = 'sprites'}>
      Sprites ({Object.keys(manifest.sprites).length})
    </button>
    <button class="tab" class:tab-active={activeTab === 'sounds'}
      on:click={() => activeTab = 'sounds'}>
      Sounds ({Object.keys(manifest.sounds).length})
    </button>
  </div>

  <div class="flex-1 overflow-y-auto p-2">
    {#if activeTab === 'sprites'}
      <div class="grid grid-cols-3 gap-2">
        {#each filteredSprites as [name, sprite]}
          <div class="card card-compact bg-base-100 cursor-pointer hover:ring-2 ring-primary"
            draggable="true"
            on:dragstart={(e) => e.dataTransfer.setData('text/plain', `sprite: ${name}`)}>
            <figure class="h-16 bg-base-300">
              <!-- Sprite preview rendered by engine -->
              <img src={sprite.previewUrl} alt={name} class="object-contain h-full" />
            </figure>
            <div class="card-body p-1">
              <p class="text-xs truncate">{name}</p>
            </div>
          </div>
        {/each}
      </div>
    {:else}
      {#each filteredSounds as [name, sound]}
        <div class="flex items-center gap-2 p-1 hover:bg-base-300 rounded cursor-pointer"
          draggable="true"
          on:dragstart={(e) => e.dataTransfer.setData('text/plain', `sound: ${name}`)}>
          <button class="btn btn-xs btn-circle" on:click={() => playSound(name)}>▶</button>
          <span class="text-sm flex-1">{name}</span>
        </div>
      {/each}
    {/if}
  </div>
</div>
```

---

## 11. Content-Type Aware Field Editors

When editing YAML fields with `x-content-type` annotations in the JSON Schema, the IDE opens specialized editors instead of plain text input.

### Schema Annotations

The game schema uses `x-content-type` to indicate field types:

```json
{
  "properties": {
    "sprite": {
      "type": "string",
      "x-content-type": "sprite",
      "description": "Reference to a registered sprite name"
    },
    "color": {
      "oneOf": [
        {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
        {"type": "array", "items": {"type": "integer"}, "minItems": 3, "maxItems": 4}
      ],
      "x-content-type": "color"
    },
    "transparent": {
      "type": "array",
      "x-content-type": "color",
      "description": "RGB color to treat as transparent"
    }
  }
}
```

### Content-Type Editor Components

| x-content-type | Component | Features |
|----------------|-----------|----------|
| `sprite` | SpritePicker | Grid view, search, drag-drop, preview |
| `sound` | SoundPicker | List view, play button, search |
| `color` | ColorPicker | RGB/HSL sliders, hex input, opacity |
| `file` | FileBrowser | Tree view, upload, preview |
| `level` | LevelPicker | List levels, click to open editor |
| `lua` | LuaEditor | Monaco with Lua syntax, `ams.*` completions, error markers |
| `yaml` | YamlEditor | Monaco with YAML syntax, schema validation, `$ref` support |
| `behavior` | BehaviorPicker | List behaviors with config schema |
| `entity_type` | EntityPicker | Entity types with sprite preview |

### Code Field Editors (Lua & YAML)

For fields containing embedded code, the IDE provides dedicated editor panels with full language support.

**Lua Editor (`x-content-type: lua`):**

When the cursor enters a `lua:` field (inline behavior/script), opens a dedicated Lua editor:

```yaml
behaviors:
  custom_bounce:
    lua: |                    # ← click to open Lua editor panel
      function on_update(entity, dt)
        if ams.get_y(entity) > 500 then
          ams.set_vy(entity, -ams.get_vy(entity) * 0.8)
        end
      end
```

**Lua Editor Features:**
- Monaco with Lua syntax highlighting
- `ams.*` API autocomplete with signatures:
  ```
  ams.get_x(entity_id) → number
  ams.set_vy(entity_id, vy: number) → nil
  ams.spawn(type: string, x: number, y: number) → string
  ```
- Hover documentation from `lua_api.schema.json`
- Real-time syntax error highlighting
- Expand to full-screen mode for complex scripts
- **Sandbox violation warnings** - immediate feedback on blocked globals

**Sandbox-Aware Linting:**

The Lua runtime sandboxes scripts for security. The IDE warns when users reference blocked globals:

```lua
function on_update(entity, dt)
  local f = io.open("file.txt")  -- ⚠️ 'io' is not available (sandboxed)
  os.execute("cmd")              -- ⚠️ 'os' is not available (sandboxed)
  require("module")              -- ⚠️ 'require' is not available (sandboxed)
end
```

**Blocked Globals** (flagged with warnings):
| Global | Reason |
|--------|--------|
| `io`, `os` | Filesystem/system access |
| `debug` | Introspection/breakout |
| `package`, `require` | Dynamic code loading |
| `loadfile`, `dofile`, `load` | Arbitrary code execution |
| `rawget`, `rawset` | Metatable bypass |
| `getmetatable`, `setmetatable` | Sandbox escape vectors |
| `string.dump` | Bytecode access |

Implementation uses Monaco's `setModelMarkers` to show inline warnings:

```javascript
// sandbox-lint.js
const BLOCKED_GLOBALS = [
  'io', 'os', 'debug', 'package', 'require',
  'loadfile', 'dofile', 'load',
  'rawget', 'rawset', 'getmetatable', 'setmetatable'
];

function lintLuaSandbox(model) {
  const markers = [];
  const text = model.getValue();

  for (const global of BLOCKED_GLOBALS) {
    const regex = new RegExp(`\\b${global}\\b`, 'g');
    let match;
    while ((match = regex.exec(text)) !== null) {
      const pos = model.getPositionAt(match.index);
      markers.push({
        severity: monaco.MarkerSeverity.Warning,
        message: `'${global}' is not available in sandboxed Lua`,
        startLineNumber: pos.lineNumber,
        startColumn: pos.column,
        endLineNumber: pos.lineNumber,
        endColumn: pos.column + global.length,
      });
    }
  }

  monaco.editor.setModelMarkers(model, 'sandbox-lint', markers);
}
```

**YAML Editor (`x-content-type: yaml`):**

For embedded YAML content (inline levels, config blocks):

```yaml
levels:
  - level: level1
    inline: |                 # ← click to open YAML editor panel
      entities:
        - type: brick
          grid: { cols: 10, rows: 3 }
```

**YAML Editor Features:**
- Monaco with YAML syntax highlighting
- Schema validation against referenced schema (e.g., `level.schema.json`)
- Autocomplete for known properties
- Inline error markers for validation failures
- Expand to full-screen mode

### Trigger Mechanism

Monaco detects cursor position and field type:

```javascript
// In MonacoEditor.svelte
editor.onDidChangeCursorPosition((e) => {
  const position = e.position;
  const model = editor.getModel();
  const word = model.getWordAtPosition(position);

  // Parse YAML path to current field
  const yamlPath = getYamlPath(model, position);  // e.g., "entity_types.duck.sprite"

  // Look up x-content-type in schema
  const contentType = getContentTypeForPath(schema, yamlPath);

  if (contentType) {
    dispatch('show-content-editor', {
      type: contentType,
      path: yamlPath,
      currentValue: word?.word,
      position: editor.getScrolledVisiblePosition(position)
    });
  }
});
```

### Color Picker Example

```svelte
<!-- ColorPicker.svelte -->
<script>
  export let value = [255, 255, 255];
  export let format = 'rgb';  // 'rgb' | 'hex'

  let r, g, b, a = 255;

  $: if (Array.isArray(value)) {
    [r, g, b, a = 255] = value;
  } else if (typeof value === 'string') {
    [r, g, b] = hexToRgb(value);
  }

  $: hexValue = rgbToHex(r, g, b);
  $: previewStyle = `background-color: rgba(${r}, ${g}, ${b}, ${a/255})`;

  function emit() {
    const result = format === 'hex' ? hexValue : [r, g, b];
    dispatch('select', result);
  }
</script>

<div class="card bg-base-100 shadow-lg p-4 w-64">
  <div class="h-12 rounded mb-4" style={previewStyle}></div>

  <div class="space-y-2">
    <label class="flex items-center gap-2">
      <span class="w-4 text-error">R</span>
      <input type="range" class="range range-xs range-error flex-1"
        min="0" max="255" bind:value={r} on:input={emit} />
      <input type="number" class="input input-xs w-14"
        min="0" max="255" bind:value={r} on:input={emit} />
    </label>
    <label class="flex items-center gap-2">
      <span class="w-4 text-success">G</span>
      <input type="range" class="range range-xs range-success flex-1"
        min="0" max="255" bind:value={g} on:input={emit} />
      <input type="number" class="input input-xs w-14"
        min="0" max="255" bind:value={g} on:input={emit} />
    </label>
    <label class="flex items-center gap-2">
      <span class="w-4 text-info">B</span>
      <input type="range" class="range range-xs range-info flex-1"
        min="0" max="255" bind:value={b} on:input={emit} />
      <input type="number" class="input input-xs w-14"
        min="0" max="255" bind:value={b} on:input={emit} />
    </label>
  </div>

  <div class="divider my-2"></div>

  <label class="flex items-center gap-2">
    <span class="text-xs">Hex:</span>
    <input type="text" class="input input-xs flex-1"
      value={hexValue}
      on:input={(e) => { [r, g, b] = hexToRgb(e.target.value); emit(); }} />
  </label>
</div>
```

### Files to Create

```
src/lib/ide/
├── AssetBrowser.svelte           # Sidebar asset browser
├── AssetManifest.js              # Asset manifest state management
├── content-editors/
│   ├── ContentTypeEditor.svelte  # Router/container component
│   ├── SpritePicker.svelte       # Sprite grid picker
│   ├── SoundPicker.svelte        # Sound list with playback
│   ├── ColorPicker.svelte        # RGB/hex color picker
│   ├── FileBrowser.svelte        # File tree browser
│   ├── BehaviorPicker.svelte     # Behavior selector
│   └── EntityPicker.svelte       # Entity type selector
└── utils/
    └── yaml-path.js              # Parse YAML to get cursor path
```

## 12. Log Streaming Implementation

**Goal:** Real-time engine logs displayed in IDE bottom panel for debugging.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Python Engine (game_runtime.py)                                        │
│    │                                                                    │
│    ├─> js_log() calls                                                   │
│    ├─> ams.logger outputs                                               │
│    ├─> GameEngine debug prints                                          │
│    │                                                                    │
│    ▼                                                                    │
│  ide_bridge.py captures logs → window.ideBridge.notifyLog(level, msg)   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ postMessage
┌─────────────────────────────────────────────────────────────────────────┐
│  ide_bridge.js                                                          │
│    └─> sendToIDE('log', {level: 'INFO', message: '...', module: '...'}) │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ postMessage
┌─────────────────────────────────────────────────────────────────────────┐
│  PreviewFrame.svelte                                                    │
│    └─> dispatch('log', {level, message, module})                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ event
┌─────────────────────────────────────────────────────────────────────────┐
│  Author.svelte                                                          │
│    └─> logs = [...logs, newLog]                                         │
│    └─> <LogPanel {logs} />                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### Log Message Format

```javascript
// Engine → IDE
{
  type: 'log',
  level: 'INFO',      // DEBUG, INFO, WARN, ERROR
  module: 'GameEngine',
  message: 'Loaded 5 entity types',
  timestamp: 1702400000000
}
```

### Python Side: Log Capture

```python
# In game_runtime.py - add log handler

import logging

class IDELogHandler(logging.Handler):
    """Forward Python logs to IDE via postMessage."""

    def __init__(self, bridge):
        super().__init__()
        self._bridge = bridge

    def emit(self, record):
        if self._bridge and sys.platform == "emscripten":
            try:
                browser_platform.window.ideBridge.notifyLog(
                    record.levelname,
                    f"[{record.name}] {record.getMessage()}"
                )
            except:
                pass

# In _init_ide_bridge():
def _init_ide_bridge(self):
    # ... existing code ...

    # Add log handler for IDE streaming
    if self._ide_bridge:
        handler = IDELogHandler(self._ide_bridge)
        handler.setLevel(logging.DEBUG)
        logging.getLogger('ams').addHandler(handler)
        logging.getLogger('games').addHandler(handler)
```

### JS Side: Log Protocol Update

```javascript
// In ide_bridge.js - update notifyLog
notifyLog: function(level, message, module) {
    sendToIDE('log', {
        level: level || 'INFO',
        message: message,
        module: module || 'Engine',
        timestamp: Date.now()
    });
}
```

### Svelte Components

**LogPanel.svelte:**

```svelte
<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  export let logs = [];
  let filter = { level: 'all', search: '' };
  let autoScroll = true;
  let logContainer;

  // Auto-truncation settings (default: 200 lines to prevent memory bloat)
  let maxLines = 200;
  const maxLineOptions = [50, 100, 200, 500, 0]; // 0 = unlimited
  let truncatedCount = 0;

  // Apply truncation when logs exceed limit
  $: if (maxLines > 0 && logs.length > maxLines) {
    truncatedCount += logs.length - maxLines;
    dispatch('truncate', { count: logs.length - maxLines });
    logs = logs.slice(-maxLines);
  }

  $: filteredLogs = logs.filter(log => {
    if (filter.level !== 'all' && log.level !== filter.level) return false;
    if (filter.search && !log.message.toLowerCase().includes(filter.search.toLowerCase())) return false;
    return true;
  });

  $: if (autoScroll && logContainer) {
    logContainer.scrollTop = logContainer.scrollHeight;
  }

  const levelColors = {
    DEBUG: 'text-base-content/50',
    INFO: 'text-info',
    WARN: 'text-warning',
    ERROR: 'text-error'
  };

  const levelBadge = {
    DEBUG: 'badge-ghost',
    INFO: 'badge-info',
    WARN: 'badge-warning',
    ERROR: 'badge-error'
  };

  function formatTime(ts) {
    return new Date(ts).toLocaleTimeString('en-US', { hour12: false });
  }

  function clearLogs() {
    logs = [];
    truncatedCount = 0;
  }
</script>

<div class="flex flex-col h-full bg-base-200">
  <!-- Toolbar -->
  <div class="flex items-center gap-2 px-2 py-1 border-b border-base-300 text-xs">
    <select class="select select-xs" bind:value={filter.level}>
      <option value="all">All Levels</option>
      <option value="DEBUG">DEBUG</option>
      <option value="INFO">INFO</option>
      <option value="WARN">WARN</option>
      <option value="ERROR">ERROR</option>
    </select>

    <input
      type="text"
      class="input input-xs flex-1"
      placeholder="Filter logs..."
      bind:value={filter.search}
    />

    <!-- Auto-truncation limit selector -->
    <select class="select select-xs w-20" bind:value={maxLines} title="Max log lines">
      {#each maxLineOptions as opt}
        <option value={opt}>{opt === 0 ? '∞' : opt}</option>
      {/each}
    </select>

    <label class="flex items-center gap-1 cursor-pointer">
      <input type="checkbox" class="checkbox checkbox-xs" bind:checked={autoScroll} />
      <span>Auto-scroll</span>
    </label>

    <button class="btn btn-xs btn-ghost" on:click={clearLogs}>Clear</button>

    <!-- Show truncation indicator when logs have been trimmed -->
    {#if truncatedCount > 0}
      <span class="text-warning/70" title="{truncatedCount} older logs removed">
        ({truncatedCount} trimmed)
      </span>
    {/if}

    <span class="text-base-content/50">{filteredLogs.length} logs</span>
  </div>

  <!-- Log entries -->
  <div
    class="flex-1 overflow-y-auto font-mono text-xs"
    bind:this={logContainer}
  >
    {#each filteredLogs as log (log.timestamp + log.message)}
      <div class="flex gap-2 px-2 py-0.5 hover:bg-base-300 border-b border-base-300/30">
        <span class="text-base-content/40 w-20 shrink-0">{formatTime(log.timestamp)}</span>
        <span class="badge badge-xs {levelBadge[log.level]} w-14">{log.level}</span>
        <span class="{levelColors[log.level]} whitespace-pre-wrap break-all">{log.message}</span>
      </div>
    {/each}

    {#if filteredLogs.length === 0}
      <div class="flex items-center justify-center h-full text-base-content/40">
        No logs yet. Click "Run" to start the game.
      </div>
    {/if}
  </div>
</div>
```

**Author.svelte updates:**

```svelte
<script>
  // Add to existing script
  let logs = [];
  let showLogPanel = true;
  let logPanelHeight = 200;

  function handleLog(event) {
    const log = event.detail;
    logs = [...logs.slice(-999), log];  // Keep last 1000 logs
  }
</script>

<!-- Add bottom panel after editor-container -->
{#if showLogPanel}
  <div class="border-t border-base-300" style="height: {logPanelHeight}px">
    <div class="flex items-center justify-between px-2 py-1 bg-base-300 text-xs">
      <span class="font-semibold">Console</span>
      <button class="btn btn-xs btn-ghost" on:click={() => showLogPanel = false}>×</button>
    </div>
    <div style="height: calc(100% - 28px)">
      <LogPanel {logs} />
    </div>
  </div>
{/if}

<!-- Update PreviewFrame to forward logs -->
<PreviewFrame {projectFiles} on:log={handleLog} />
```

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/lib/ide/LogPanel.svelte` | Create | Log display with filtering |
| `src/Author.svelte` | Modify | Add bottom log panel, wire events |
| `src/lib/ide/PreviewFrame.svelte` | Modify | Forward 'log' events from engine |
| `games/browser/game_runtime.py` | Modify | Add IDELogHandler class |
| `games/browser/ide_bridge.js` | Modify | Update notifyLog with module/timestamp |

### Success Criteria

- [ ] Engine `js_log()` calls appear in IDE log panel
- [ ] `ams.*` logger outputs appear in IDE
- [ ] Log level filtering works (DEBUG/INFO/WARN/ERROR)
- [ ] Search/filter by text works
- [ ] Auto-scroll follows new logs
- [ ] Clear button empties log panel
- [ ] **Auto-truncation**: Panel keeps only last 200 lines by default
- [ ] Truncation indicator shows "X trimmed" when logs removed
- [ ] Max lines selector allows 50/100/200/500/unlimited
- [ ] Logs persist across hot reloads (within session)

---

## 13. Development

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
