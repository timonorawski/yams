"""
Lua Script Loader - Load and validate .lua.yaml script files.

Provides a standalone loader that can read both legacy .lua files and
new .lua.yaml files with metadata. Validates against JSON Schema when
available.

Usage:
    from ams.games.game_engine.lua.script_loader import ScriptLoader

    loader = ScriptLoader()

    # Load a single script
    script = loader.load_file('/path/to/behavior/animate.lua.yaml')
    print(script.name)        # 'animate'
    print(script.type)        # 'behavior'
    print(script.code)        # Lua source code
    print(script.config)      # Config schema dict

    # Load all scripts from a directory
    scripts = loader.load_directory('/path/to/behavior', script_type='behavior')

    # Load from content (for inline scripts)
    script = loader.load_inline(
        name='my_behavior',
        script_type='behavior',
        definition={'lua': '...', 'description': '...'}
    )

Integration with LuaEngine:
    When ready to integrate, replace direct .lua file reads with:

    script = loader.load_file(path)
    lua_engine.load_inline_subroutine(script.type, script.name, script.code)
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ams.logging import get_logger
from ams.yaml import (
    load as yaml_load,
    loads as yaml_loads,
    validate as yaml_validate,
    load_schema,
    HAS_YAML,
    HAS_JSONSCHEMA,
    SchemaValidationError,
)

log = get_logger('script_loader')


@dataclass
class ScriptMetadata:
    """Parsed Lua script with metadata."""

    # Required
    name: str
    type: str  # behavior, collision_action, generator, input_action
    code: str

    # Optional metadata
    description: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Schema definitions
    config: Dict[str, Any] = field(default_factory=dict)  # For behaviors/collision_actions
    args: Dict[str, Any] = field(default_factory=dict)    # For generators/input_actions

    # Dependencies
    requires: Dict[str, List[str]] = field(default_factory=dict)
    provides: Dict[str, Any] = field(default_factory=dict)

    # Examples
    examples: List[Dict[str, str]] = field(default_factory=list)

    # Source info
    source_path: Optional[str] = None
    source_format: str = 'lua'  # 'lua' or 'lua.yaml'

    @property
    def hooks(self) -> List[str]:
        """Get implemented hooks from provides."""
        return self.provides.get('hooks', [])

    @property
    def provided_properties(self) -> List[str]:
        """Get properties created by this script."""
        return self.provides.get('properties', [])

    @property
    def required_behaviors(self) -> List[str]:
        """Get required behaviors."""
        return self.requires.get('behaviors', [])

    @property
    def required_properties(self) -> List[str]:
        """Get required properties."""
        return self.requires.get('properties', [])

    @property
    def required_api(self) -> List[str]:
        """Get required API methods."""
        return self.requires.get('api', [])


class ScriptValidationError(Exception):
    """Raised when script validation fails."""

    def __init__(self, message: str, path: Optional[str] = None, errors: Optional[List[str]] = None):
        self.path = path
        self.errors = errors or []
        super().__init__(message)

VALID_SUBROUTINE_TYPES = {'action', 'generator'}
VALID_HOOK_TYPES = {
    'action': {'execute'},
    'generator': {'generate'},
}
class ScriptLoader:
    """
    Load and validate Lua scripts from .lua and .lua.yaml files.

    Supports:
    - Legacy .lua files (code only, metadata inferred)
    - New .lua.yaml files (code + metadata, validated)
    - Inline script definitions (for game.yaml embedding)

    Args:
        schema_path: Path to lua_script.schema.json (auto-detected if None)
        validate: Whether to validate .lua.yaml files against schema
        strict: If True, raise on validation errors; if False, warn and continue
    """


    

    def __init__(
        self,
        schema_path: Optional[str] = None,
        validate: bool = True,
        strict: bool = False,
    ):
        self.validate = validate and HAS_JSONSCHEMA and HAS_YAML
        self.strict = strict
        self._schema = None
        self._schema_path = schema_path

        if validate and not HAS_YAML:
            log.warning("PyYAML not installed; .lua.yaml validation disabled")

        if validate and not HAS_JSONSCHEMA:
            log.warning("jsonschema not installed; schema validation disabled")

    @property
    def schema(self) -> Optional[Dict]:
        """Lazy-load the JSON schema."""
        if self._schema is None and self.validate:
            self._schema = self._load_schema()
        return self._schema

    def _load_schema(self) -> Optional[Dict]:
        """Load the JSON schema file."""
        if self._schema_path:
            schema_path = Path(self._schema_path)
        else:
            # Auto-detect schema location relative to this file
            schema_path = Path(__file__).parent / 'lua_script.schema.json'

        if schema_path.exists():
            return load_schema(schema_path)
        return None

    def load_file(self, path: Union[str, Path]) -> ScriptMetadata:
        """
        Load a script from a .lua.yaml file.

        Args:
            path: Path to the .lua.yaml script file

        Returns:
            ScriptMetadata with parsed content

        Raises:
            FileNotFoundError: If file doesn't exist
            ScriptValidationError: If validation fails (in strict mode)
            ValueError: If file is not a .lua.yaml file
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Script not found: {path}")

        if path.suffix == '.yaml' and path.stem.endswith('.lua'):
            return self._load_yaml_file(path)
        else:
            raise ValueError(f"Only .lua.yaml files are supported, got: {path}")

    def _load_yaml_file(self, path: Path) -> ScriptMetadata:
        """Load a .lua.yaml file."""
        content = yaml_load(path)

        if not isinstance(content, dict):
            raise ScriptValidationError(
                f"Invalid .lua.yaml format: expected dict, got {type(content).__name__}",
                path=str(path)
            )

        # Validate against schema
        if self.validate and self.schema:
            self._validate_against_schema(content, path)

        # Extract name from filename if not specified
        # filename: animate.lua.yaml -> name: animate
        name = content.get('name')
        if not name:
            name = path.stem  # 'animate.lua'
            if name.endswith('.lua'):
                name = name[:-4]  # 'animate'

        # Type is required in .lua.yaml
        script_type = content.get('type')
        if not script_type:
            raise ScriptValidationError(
                "Missing required field 'type'",
                path=str(path)
            )

        if script_type not in VALID_SUBROUTINE_TYPES:
            raise ScriptValidationError(
                f"Invalid type '{script_type}', must be one of {VALID_SUBROUTINE_TYPES}",
                path=str(path)
            )

        # Lua code is required
        code = content.get('lua')
        if not code:
            raise ScriptValidationError(
                "Missing required field 'lua'",
                path=str(path)
            )

        return ScriptMetadata(
            name=name,
            type=script_type,
            code=code,
            description=content.get('description'),
            version=content.get('version'),
            author=content.get('author'),
            tags=content.get('tags', []),
            config=content.get('config', {}),
            args=content.get('args', {}),
            requires=content.get('requires', {}),
            provides=content.get('provides', {}),
            examples=content.get('examples', []),
            source_path=str(path),
            source_format='lua.yaml',
        )

    def _validate_against_schema(self, content: Dict, path: Path) -> None:
        """Validate content against JSON schema."""
        if not self.schema:
            return

        try:
            yaml_validate(content, self.schema, raise_on_error=True)
        except SchemaValidationError as e:
            if self.strict:
                raise ScriptValidationError(str(e), path=str(path), errors=e.errors)
            else:
                log.warning(f"{path}: {e}")

    def load_inline(
        self,
        name: str,
        script_type: str,
        definition: Dict[str, Any],
    ) -> ScriptMetadata:
        """
        Load an inline script definition (e.g., from game.yaml).

        Args:
            name: Script name (from YAML key)
            script_type: One of behavior, collision_action, generator, input_action
            definition: Dict with 'lua' and optional metadata

        Returns:
            ScriptMetadata with parsed content
        """
        if script_type not in VALID_SUBROUTINE_TYPES:
            raise ScriptValidationError(
                f"Invalid type '{script_type}', must be one of {VALID_SUBROUTINE_TYPES}"
            )

        code = definition.get('lua')
        if not code:
            raise ScriptValidationError(
                f"Inline script '{name}' missing required 'lua' field"
            )

        return ScriptMetadata(
            name=name,
            type=script_type,
            code=code,
            description=definition.get('description'),
            config=definition.get('config', {}),
            args=definition.get('args', {}),
            provides=definition.get('provides', {}),
            source_format='inline',
        )

    def load_directory(
        self,
        directory: Union[str, Path],
        script_type: Optional[str] = None,
    ) -> List[ScriptMetadata]:
        """
        Load all .lua.yaml scripts from a directory.

        Args:
            directory: Path to directory
            script_type: Override type (otherwise inferred from file content)

        Returns:
            List of ScriptMetadata objects
        """
        directory = Path(directory)

        if not directory.is_dir():
            return []

        scripts = []

        for path in directory.glob('*.lua.yaml'):
            try:
                script = self._load_yaml_file(path)
                if script_type:
                    script.type = script_type
                scripts.append(script)
            except Exception as e:
                if self.strict:
                    raise
                log.warning(f"Failed to load {path}: {e}")

        return scripts

    def find_script(
        self,
        name: str,
        script_type: str,
        search_paths: List[Union[str, Path]],
    ) -> Optional[ScriptMetadata]:
        """
        Find and load a .lua.yaml script by name.

        Args:
            name: Script name
            script_type: Script type (used for directory name)
            search_paths: List of base directories to search

        Returns:
            ScriptMetadata if found, None otherwise
        """
        for base_path in search_paths:
            base_path = Path(base_path)

            # Try type-specific subdirectory
            type_dir = base_path / script_type
            if type_dir.is_dir():
                yaml_path = type_dir / f"{name}.lua.yaml"
                if yaml_path.exists():
                    return self.load_file(yaml_path)

            # Try base directory
            yaml_path = base_path / f"{name}.lua.yaml"
            if yaml_path.exists():
                return self.load_file(yaml_path)

        return None


# Convenience function
def load_script(path: Union[str, Path]) -> ScriptMetadata:
    """Load a single script file."""
    return ScriptLoader().load_file(path)
