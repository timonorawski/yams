"""Schema validation for game YAML files."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


_game_schema: Optional[Dict[str, Any]] = None
_SCHEMAS_DIR = Path(__file__).parent.parent.parent / 'schemas'

# Set AMS_SKIP_SCHEMA_VALIDATION=1 to disable strict validation
_SKIP_VALIDATION = os.environ.get('AMS_SKIP_SCHEMA_VALIDATION', '').lower() in ('1', 'true', 'yes')


class SchemaValidationError(Exception):
    """Raised when YAML data fails schema validation."""
    pass


def _get_game_schema() -> Optional[Dict[str, Any]]:
    """Lazy-load game schema."""
    global _game_schema
    if _game_schema is None:
        schema_path = _SCHEMAS_DIR / 'game.schema.json'
        if schema_path.exists():
            with open(schema_path) as f:
                _game_schema = json.load(f)
    return _game_schema


def validate_game_yaml(data: Dict[str, Any], source_path: Optional[Path] = None) -> None:
    """Validate game YAML data against schema.

    Args:
        data: Parsed YAML data
        source_path: Optional path for error messages

    Raises:
        SchemaValidationError: If validation fails (unless AMS_SKIP_SCHEMA_VALIDATION=1)
        ImportError: If jsonschema is not installed (unless AMS_SKIP_SCHEMA_VALIDATION=1)
    """
    schema = _get_game_schema()
    if schema is None:
        error_msg = f"Schema file not found: {_SCHEMAS_DIR / 'game.schema.json'}"
        if _SKIP_VALIDATION:
            print(f"[GameEngine] Warning: {error_msg}")
            return
        raise SchemaValidationError(error_msg)

    try:
        import jsonschema
        from jsonschema import RefResolver
    except ImportError as e:
        error_msg = "jsonschema package not installed - required for YAML validation"
        if _SKIP_VALIDATION:
            print(f"[GameEngine] Warning: {error_msg}")
            return
        raise ImportError(error_msg) from e

    try:
        # Create resolver with local schema store for external $ref
        schema_store = {}
        for schema_file in _SCHEMAS_DIR.glob('*.json'):
            with open(schema_file) as f:
                schema_store[schema_file.name] = json.load(f)

        resolver = RefResolver.from_schema(schema, store=schema_store)
        jsonschema.validate(data, schema, resolver=resolver)
    except jsonschema.ValidationError as e:
        path_str = f" in {source_path}" if source_path else ""
        error_msg = f"Schema validation error{path_str}: {e.message} at {'/'.join(str(p) for p in e.absolute_path)}"
        if _SKIP_VALIDATION:
            print(f"[GameEngine] Warning: {error_msg}")
        else:
            raise SchemaValidationError(error_msg) from e
    except jsonschema.SchemaError as e:
        error_msg = f"Invalid schema: {e.message}"
        if _SKIP_VALIDATION:
            print(f"[GameEngine] Warning: {error_msg}")
        else:
            raise SchemaValidationError(error_msg) from e
