"""Schema validation for game YAML files."""

from pathlib import Path
from typing import Any, Dict, Optional

from ams.yaml import (
    load_schema,
    HAS_JSONSCHEMA,
    SKIP_VALIDATION,
    SchemaValidationError,
)


_game_schema: Optional[Dict[str, Any]] = None
_SCHEMAS_DIR = Path(__file__).parent / 'schemas'


def _get_game_schema() -> Optional[Dict[str, Any]]:
    """Lazy-load game schema."""
    global _game_schema
    if _game_schema is None:
        schema_path = _SCHEMAS_DIR / 'game.schema.json'
        if schema_path.exists():
            _game_schema = load_schema(schema_path)
    return _game_schema


def validate_game_yaml(data: Dict[str, Any], source_path: Optional[Path] = None) -> None:
    """Validate game YAML data against schema.

    Uses RefResolver for external $ref support (game schema references other schemas).

    Args:
        data: Parsed YAML data
        source_path: Optional path for error messages

    Raises:
        SchemaValidationError: If validation fails (unless AMS_SKIP_SCHEMA_VALIDATION=1)
    """
    schema = _get_game_schema()
    if schema is None:
        error_msg = f"Schema file not found: {_SCHEMAS_DIR / 'game.schema.json'}"
        if SKIP_VALIDATION:
            print(f"[GameEngine] Warning: {error_msg}")
            return
        raise SchemaValidationError(error_msg)

    if not HAS_JSONSCHEMA:
        # jsonschema not available (e.g., browser/WASM builds)
        print(f"[GameEngine] Warning: Schema validation skipped (jsonschema not available)")
        return

    import jsonschema
    from jsonschema import RefResolver

    try:
        # Create resolver with local schema store for external $ref
        # Map both filename and relative path forms that might appear in $ref
        schema_store = {}

        # Load schemas from schemas/ directory
        for schema_file in _SCHEMAS_DIR.glob('*.json'):
            loaded = load_schema(schema_file)
            schema_store[schema_file.name] = loaded
            # Also map by $id if present
            if '$id' in loaded:
                schema_store[loaded['$id']] = loaded

        # Load schemas from lua/ directory (referenced by game.schema.json)
        # The game.schema.json uses $ref: "../lua/lua_script_inline.schema.json"
        # which resolves to https://ams.games/lua/... based on game.schema.json's $id
        lua_dir = _SCHEMAS_DIR.parent / 'lua'
        for schema_file in lua_dir.glob('*.schema.json'):
            loaded = load_schema(schema_file)
            # Map by relative path as used in $ref: "../lua/..."
            schema_store[f"../lua/{schema_file.name}"] = loaded
            # Map by resolved URL (relative to game.schema.json's $id)
            schema_store[f"https://ams.games/lua/{schema_file.name}"] = loaded
            # Also map by $id if present
            if '$id' in loaded:
                schema_store[loaded['$id']] = loaded

        resolver = RefResolver.from_schema(schema, store=schema_store)
        jsonschema.validate(data, schema, resolver=resolver)
    except jsonschema.ValidationError as e:
        path_str = f" in {source_path}" if source_path else ""
        error_msg = f"Schema validation error{path_str}: {e.message} at {'/'.join(str(p) for p in e.absolute_path)}"
        if SKIP_VALIDATION:
            print(f"[GameEngine] Warning: {error_msg}")
        else:
            raise SchemaValidationError(error_msg, errors=[str(e)], path=source_path) from e
    except jsonschema.SchemaError as e:
        error_msg = f"Invalid schema: {e.message}"
        if SKIP_VALIDATION:
            print(f"[GameEngine] Warning: {error_msg}")
        else:
            raise SchemaValidationError(error_msg) from e
    except (OSError, IOError) as e:
        # Handle network errors (e.g., offline mode trying to fetch remote schemas)
        error_msg = f"Schema validation failed (network error): {e}"
        if SKIP_VALIDATION:
            print(f"[GameEngine] Warning: {error_msg}")
        else:
            raise SchemaValidationError(error_msg) from e
