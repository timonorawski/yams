# x-content-type Schema Extension

Custom JSON Schema extension for annotating fields with content type hints, enabling smart editing in the Web IDE.

## Syntax

```
x-content-type: "<type>" | "<type>|<type>" | "@ref:<category>" | "@ref:<category>:<subtype>"
```

## Content Types

### Language Types (inline code)

| Type | Description | IDE Action |
|------|-------------|------------|
| `lua` | Lua source code | Open Lua editor modal |
| `yaml` | YAML content | Open YAML editor modal |
| `data-uri` | Base64 data URI | Show preview, offer file upload |

### Reference Types (project references)

| Type | Description | IDE Action |
|------|-------------|------------|
| `@ref:behavior` | Behavior script name | Autocomplete from behaviors, link to file |
| `@ref:generator` | Generator script name | Autocomplete from generators, link to file |
| `@ref:collision_action` | Collision action name | Autocomplete from collision_actions |
| `@ref:input_action` | Input action name | Autocomplete from input_actions |
| `@ref:asset` | Asset file reference | Autocomplete from assets.files, file picker |
| `@ref:asset:sound` | Sound asset reference | Autocomplete, audio preview |
| `@ref:asset:image` | Image asset reference | Autocomplete, image preview |
| `@ref:sprite` | Sprite definition name | Autocomplete from assets.sprites, preview |
| `@ref:entity_type` | Entity type name | Autocomplete from entity_types |
| `@ref:level` | Level file reference | Autocomplete from levels/ |

### Compound Types

Use `|` to specify multiple valid types:
```json
"x-content-type": "@ref:asset:sound|data-uri"
```

## Schema Examples

### Inline Lua Code
```json
{
  "lua": {
    "type": "string",
    "description": "Lua expression to evaluate",
    "x-content-type": "lua"
  }
}
```

### Script Reference
```json
{
  "call": {
    "type": "string",
    "description": "Name of the generator to call",
    "x-content-type": "@ref:generator"
  }
}
```

### Asset Reference
```json
{
  "file": {
    "type": "string",
    "description": "File path or @reference",
    "x-content-type": "@ref:asset:image"
  }
}
```

## Web IDE Implementation Plan

### Phase 1: Schema Parsing
1. Fetch schema from `/api/schemas/{schema}.json`
2. Walk schema tree to build map of JSON paths → content types
3. Cache parsed schema info per filetype

### Phase 2: Language Editor Integration
For `lua`, `yaml` types:
- Detect field focus/cursor position in YAML
- Show "Edit" button or keyboard shortcut
- Open modal with language-specific Monaco editor
- On save, update the YAML field value

### Phase 3: Reference Autocomplete
For `@ref:*` types:
- Parse current document to extract defined names
- Scan project files for external definitions
- Register Monaco completion provider
- Provide hover info with "Go to definition"

### Phase 4: Asset Preview & Upload
For `@ref:asset:*` and `data-uri` types:
- Show inline preview (image thumbnail, audio waveform)
- Offer file upload to convert to data-uri
- Asset picker modal for @ref types

### Phase 5: Enhanced Navigation
- Ctrl/Cmd+Click on references to jump to definition
- "Find All References" for scripts and assets
- Breadcrumb navigation showing entity_types → behaviors → etc.

## Discovery API

The IDE can fetch content type metadata:

```
GET /api/filetypes
→ Returns filetypes with schema URLs

GET /api/schemas/game.schema.json
→ Returns schema with x-content-type annotations

GET /api/project/{name}/references
→ Returns discovered references by category:
  {
    "behaviors": ["bounce", "gravity", ...],
    "generators": ["random_position", ...],
    "assets": {"sounds": [...], "images": [...], "files": [...]},
    "sprites": ["duck_flying", ...],
    "entity_types": ["target", "player", ...]
  }
```

## Future Extensions

- `x-content-type: "color"` - Color picker
- `x-content-type: "path"` - File path with browser
- `x-content-type: "expression"` - Math expression editor
- `x-content-type: "@ref:tag"` - Tag autocomplete
