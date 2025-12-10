# Skins System for DuckHunt (and BaseGame)

**Status**: In Progress
**Date**: 2024-12-10

## Goal

Add a skins registry to BaseGame that allows games to define multiple visual representations. For DuckHunt:
- **geometric**: Circle-based targets (CV-friendly, testing, accessibility)
- **classic**: Sprite-based Duck Hunt visuals with sounds

## Design Principles

1. **Mirror the levels pattern** - `--skin` CLI arg, SKINS registry
2. **Skins are presentation-only** - No game logic changes, just visuals + audio
3. **Registry-based** - Games declare available skins, not file-based discovery
4. **Skin abstraction** - Each skin provides rendering AND audio for game entities

## Architecture

### Simple Registry (Chosen Approach)

Skins are simpler than levels - just named skin classes. No need for YAML files or directory scanning.

```python
# In DuckHuntMode
SKINS = {
    'geometric': GeometricSkin,
    'classic': ClassicSkin,
}
```

## Implementation Plan

### Phase 1: Skin Classes

**New files:**
```
games/DuckHunt/game/skins/
├── __init__.py           # Exports
├── base.py               # GameSkin ABC
├── geometric.py          # GeometricSkin (circles, no audio)
└── classic.py            # ClassicSkin (sprites + sounds)
```

**GameSkin interface:**
- `render_target(target, screen)` - Render a target
- `update(dt)` - Update animations
- `play_hit_sound()` - Play on hit
- `play_miss_sound()` - Play on miss
- `play_spawn_sound()` - Play on spawn

### Phase 2: Modify DuckTarget

- Remove render() method from DuckTarget
- Keep DuckTarget as pure data/state container
- Rendering done externally via skin

### Phase 3: Wire Up in DuckHuntMode

- Add `--skin` argument
- Create skin instance based on selection
- Use skin for rendering in render()
- Use skin for audio in hit handling

## Files to Modify

| File | Changes |
|------|---------|
| `games/DuckHunt/game/skins/__init__.py` | NEW - exports |
| `games/DuckHunt/game/skins/base.py` | NEW - GameSkin ABC |
| `games/DuckHunt/game/skins/geometric.py` | NEW - GeometricSkin |
| `games/DuckHunt/game/skins/classic.py` | NEW - ClassicSkin |
| `games/DuckHunt/game/duck_target.py` | Remove render() method |
| `games/DuckHunt/game_mode.py` | Add --skin arg, use skin |

## Testing

```bash
# Geometric skin (CV testing)
python ams_game.py --game duckhunt --backend mouse --skin geometric

# Classic skin (full experience)
python ams_game.py --game duckhunt --backend mouse --skin classic
```

## Future Extensibility

- Add more skins (holiday themes, custom branding)
- Skin-specific sound effects beyond hit/miss
- UI theming beyond just targets
- BaseGame integration for other games
- Skin definitions in YAML (like levels) if complexity grows
