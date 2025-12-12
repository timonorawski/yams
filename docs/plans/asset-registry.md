# Asset Registry System for AMS Game Engine

## Overview

Add an asset registry that discovers YAML definition files in `assets/` directories, allowing games to reference sprites and sounds by registered name without defining them inline in `game.yaml`.

## Goals

1. **Discoverability**: Engine automatically finds asset definitions from YAML files
2. **Named references**: Games can use `sprite: player` instead of inline definitions
3. **Provenance tracking**: Asset metadata (author, license) flows through the system
4. **Backwards compatible**: Inline definitions in game.yaml continue to work (and take precedence)

---

## Current State

**How assets work today:**

1. `game.yaml` defines sprites inline under `assets.sprites`:
   ```yaml
   assets:
     sprites:
       _sheet: { file: sprites.png, transparent: [159, 227, 163] }
       green_right_1: { sprite: _sheet, x: 7, y: 126, width: 37, height: 41 }
   ```

2. `engine.py._parse_sprites_config()` resolves inheritance and creates `SpriteConfig` dict

3. `AssetProvider.load_from_definition()` loads images, extracts regions, applies transforms

4. Entity types reference sprites by name: `sprite: green_right_1`

**We already have:**
- `assets.schema.json` defining sprite, sound, image formats with provenance
- Registration YAML files in `DuckHuntNG/assets/` (currently just metadata)
- `ContentFS` with `walk_files()` for file discovery

---

## Implementation Plan

### Phase 1: Create AssetRegistry Class

**New file: `ams/games/game_engine/asset_registry.py`**

```python
class AssetRegistry:
    """Discovers and loads asset definitions from YAML registration files."""

    def __init__(self, content_fs: ContentFS, assets_base_dir: Path):
        self._content_fs = content_fs
        self._assets_base_dir = assets_base_dir
        self._sprites: Dict[str, SpriteConfig] = {}
        self._sounds: Dict[str, SoundConfig] = {}

    def discover(self, assets_path: str = 'assets/') -> None:
        """Scan assets/ for *.yaml registration files.

        Uses content_fs.walk_files() to find all YAML files,
        parses each, detects type, and registers.
        """

    def merge_sprites(self, inline: Dict[str, SpriteConfig]) -> Dict[str, SpriteConfig]:
        """Merge registered with inline. Inline takes precedence."""
        merged = dict(self._sprites)
        merged.update(inline)
        return merged

    def merge_sounds(self, inline: Dict[str, SoundConfig]) -> Dict[str, SoundConfig]:
        """Merge registered with inline. Inline takes precedence."""
        merged = dict(self._sounds)
        merged.update(inline)
        return merged
```

Key features:
- Uses `ContentFS.walk_files('assets/', filter_glob=['*.yaml'])` for discovery
- Parses YAML files with `yaml.safe_load()`
- Detects asset type from path (`sprites/`, `sounds/`) or content
- Resolves sprite inheritance (`extends:` field)
- Converts to existing `SpriteConfig`/`SoundConfig` dataclasses

### Phase 2: Integrate into Engine

**Modify: `ams/games/game_engine/engine.py`**

In `_load_game_definition()`, after loading game.yaml:

```python
# 1. Ensure game layer is in ContentFS
game_path = path.parent
self._content_fs.add_game_layer(game_path)

# 2. Create registry and discover assets
from ams.games.game_engine.asset_registry import AssetRegistry
registry = AssetRegistry(self._content_fs, game_path / 'assets')
registry.discover('assets/')

# 3. Parse inline assets (existing code)
inline_sprites = self._parse_sprites_config(...)
inline_sounds = self._parse_sounds_config(...)

# 4. Merge: registered + inline (inline wins)
merged_sprites = registry.merge_sprites(inline_sprites)
merged_sounds = registry.merge_sounds(inline_sounds)

# 5. Use merged assets in AssetsConfig
assets_config = AssetsConfig(
    files=files_config,
    sounds=merged_sounds,
    sprites=merged_sprites,
)
```

### Phase 3: Update Config Dataclasses (Optional)

**Modify: `ams/games/game_engine/config.py`**

Add optional provenance field:

```python
@dataclass
class SpriteConfig:
    file: str = ""
    data: Optional[str] = None
    transparent: Optional[Tuple[int, int, int]] = None
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    flip_x: bool = False
    flip_y: bool = False
    provenance: Optional[Dict[str, Any]] = None  # NEW
```

### Phase 4: Asset Type Detection

Detection logic for YAML files:

| Signal | Asset Type |
|--------|-----------|
| Path contains `sprites/` | sprite |
| Path contains `sounds/` | sound |
| Path contains `images/` | image |
| Has `x`, `y`, `width`, `height` | sprite |
| Has `volume`, `loop`, `pitch` | sound |
| References `.png`, `.jpg` file | sprite/image |
| References `.wav`, `.mp3` file | sound |

### Phase 5: Sprite Sheet Support

Handle sprite sheets with multiple sprite regions in one file:

```yaml
# assets/sprites.yaml
name: sprites
file: sprites.png
transparent: [159, 227, 163]

sprites:
  player_idle: { x: 0, y: 0, width: 32, height: 32 }
  player_run_1: { x: 32, y: 0, width: 32, height: 32 }
  player_run_2: { x: 64, y: 0, width: 32, height: 32 }
```

When registry sees a `sprites:` map in a file, it registers each entry as a separate sprite, inheriting the parent's `file` and `transparent` settings.

---

## Files to Modify

| File | Change |
|------|--------|
| `ams/games/game_engine/asset_registry.py` | **NEW** - AssetRegistry class |
| `ams/games/game_engine/engine.py` | Integrate registry in `_load_game_definition()` |
| `ams/games/game_engine/config.py` | Add optional `provenance` field |

---

## File Discovery Pattern

```
my-game/
├── game.yaml
├── assets/
│   ├── sprites.png              # Raw file (ignored by registry)
│   ├── sprites.yaml             # Sheet registration → registers multiple sprites
│   ├── shot.wav                 # Raw file (ignored)
│   ├── shot.yaml                # Sound registration
│   ├── sprites/
│   │   └── player.yaml          # Individual sprite definition
│   └── sounds/
│       └── explosion.yaml       # Individual sound definition
```

---

## Merge Priority (highest wins)

1. **Inline definitions** in `game.yaml` `assets.sprites`/`assets.sounds`
2. **Individual YAML files** (`assets/sprites/player.yaml`)
3. **Sprite sheet definitions** (`assets/sprites.yaml` with `sprites:` map)

---

## Example Usage

### Before: Inline Only

```yaml
# game.yaml
assets:
  sprites:
    player: { file: sprites.png, x: 0, y: 0, width: 32, height: 32, transparent: [255, 0, 255] }
    enemy: { file: sprites.png, x: 32, y: 0, width: 32, height: 32, transparent: [255, 0, 255] }

entity_types:
  hero:
    sprite: player
```

### After: Registered Assets

```yaml
# assets/sprites/player.yaml
name: player
file: ../sprites.png
x: 0
y: 0
width: 32
height: 32
transparent: [255, 0, 255]
provenance:
  author: Pixel Artist
  license: CC0
```

```yaml
# game.yaml - much cleaner!
entity_types:
  hero:
    sprite: player  # References registered sprite
```

---

## Backwards Compatibility

- Games without registration files work unchanged
- Inline definitions in `game.yaml` always take precedence
- Existing `DuckHuntNG/assets/*.yaml` files become functional (currently just metadata)

---

## Testing Strategy

1. **Unit tests for AssetRegistry**:
   - Discovery finds files in nested directories
   - Sprite inheritance resolves correctly
   - Merge with inline (inline precedence)
   - Invalid YAML files are skipped gracefully

2. **Integration test**:
   - Create test game with both registered and inline sprites
   - Verify all sprites load and render correctly

3. **Backwards compatibility**:
   - Existing games (BrickBreakerNG, DuckHuntNG) work unchanged
