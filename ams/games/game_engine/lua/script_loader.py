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
        definition={'code': '...', 'description': '...'}
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

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


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

    VALID_TYPES = {'behavior', 'collision_action', 'generator', 'input_action'}

    VALID_HOOKS = {
        'behavior': {'on_spawn', 'on_update', 'on_destroy', 'on_hit'},
        'collision_action': {'execute'},
        'generator': {'generate'},
        'input_action': {'execute'},
    }

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
            import warnings
            warnings.warn("PyYAML not installed; .lua.yaml validation disabled")

        if validate and not HAS_JSONSCHEMA:
            import warnings
            warnings.warn("jsonschema not installed; schema validation disabled")

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
            with open(schema_path, 'r') as f:
                return json.load(f)
        return None

    def load_file(self, path: Union[str, Path]) -> ScriptMetadata:
        """
        Load a script from a file.

        Supports both .lua and .lua.yaml extensions. For .lua files,
        metadata is inferred from the path.

        Args:
            path: Path to the script file

        Returns:
            ScriptMetadata with parsed content

        Raises:
            FileNotFoundError: If file doesn't exist
            ScriptValidationError: If validation fails (in strict mode)
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Script not found: {path}")

        if path.suffix == '.yaml' and path.stem.endswith('.lua'):
            # .lua.yaml file
            return self._load_yaml_file(path)
        elif path.suffix == '.lua':
            # Legacy .lua file
            return self._load_lua_file(path)
        else:
            raise ValueError(f"Unknown script extension: {path.suffix}")

    def _load_yaml_file(self, path: Path) -> ScriptMetadata:
        """Load a .lua.yaml file."""
        if not HAS_YAML:
            raise ImportError("PyYAML required for .lua.yaml files")

        with open(path, 'r') as f:
            content = yaml.safe_load(f)

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

        if script_type not in self.VALID_TYPES:
            raise ScriptValidationError(
                f"Invalid type '{script_type}', must be one of {self.VALID_TYPES}",
                path=str(path)
            )

        # Code is required
        code = content.get('code')
        if not code:
            raise ScriptValidationError(
                "Missing required field 'code'",
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

    def _load_lua_file(self, path: Path) -> ScriptMetadata:
        """Load a legacy .lua file (code only, metadata inferred)."""
        with open(path, 'r') as f:
            code = f.read()

        # Infer name from filename
        name = path.stem  # 'animate'

        # Infer type from parent directory
        parent_dir = path.parent.name
        type_mapping = {
            'behavior': 'behavior',
            'behaviors': 'behavior',
            'collision_action': 'collision_action',
            'collision_actions': 'collision_action',
            'generator': 'generator',
            'generators': 'generator',
            'input_action': 'input_action',
            'input_actions': 'input_action',
        }
        script_type = type_mapping.get(parent_dir, 'behavior')

        # Try to extract description from leading comment
        description = self._extract_description_from_lua(code)

        return ScriptMetadata(
            name=name,
            type=script_type,
            code=code,
            description=description,
            source_path=str(path),
            source_format='lua',
        )

    def _extract_description_from_lua(self, code: str) -> Optional[str]:
        """Extract description from Lua comment block."""
        lines = code.strip().split('\n')

        # Check for --[[ block comment ]]
        if lines and lines[0].strip().startswith('--[['):
            description_lines = []
            for line in lines[1:]:
                if ']]' in line:
                    break
                description_lines.append(line)
            if description_lines:
                # Take first non-empty line as description
                for line in description_lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith('Config') and not stripped.startswith('Usage'):
                        return stripped

        # Check for -- single line comment
        elif lines and lines[0].strip().startswith('--'):
            first_comment = lines[0].strip()[2:].strip()
            if first_comment:
                return first_comment

        return None

    def _validate_against_schema(self, content: Dict, path: Path) -> None:
        """Validate content against JSON schema."""
        if not HAS_JSONSCHEMA:
            return

        try:
            jsonschema.validate(content, self.schema)
        except jsonschema.ValidationError as e:
            error_msg = f"Schema validation failed: {e.message}"
            if self.strict:
                raise ScriptValidationError(error_msg, path=str(path), errors=[str(e)])
            else:
                import warnings
                warnings.warn(f"{path}: {error_msg}")

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
            definition: Dict with 'code' and optional metadata

        Returns:
            ScriptMetadata with parsed content
        """
        if script_type not in self.VALID_TYPES:
            raise ScriptValidationError(
                f"Invalid type '{script_type}', must be one of {self.VALID_TYPES}"
            )

        code = definition.get('code')
        if not code:
            raise ScriptValidationError(
                f"Inline script '{name}' missing required 'code' field"
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
        Load all scripts from a directory.

        Prefers .lua.yaml files over .lua files when both exist.

        Args:
            directory: Path to directory
            script_type: Override type (otherwise inferred from directory name)

        Returns:
            List of ScriptMetadata objects
        """
        directory = Path(directory)

        if not directory.is_dir():
            return []

        scripts = []
        seen_names = set()

        # First pass: .lua.yaml files (preferred)
        for path in directory.glob('*.lua.yaml'):
            try:
                script = self._load_yaml_file(path)
                if script_type:
                    script.type = script_type
                scripts.append(script)
                seen_names.add(script.name)
            except Exception as e:
                if self.strict:
                    raise
                import warnings
                warnings.warn(f"Failed to load {path}: {e}")

        # Second pass: .lua files (only if no .lua.yaml version)
        for path in directory.glob('*.lua'):
            name = path.stem
            if name not in seen_names:
                try:
                    script = self._load_lua_file(path)
                    if script_type:
                        script.type = script_type
                    scripts.append(script)
                except Exception as e:
                    if self.strict:
                        raise
                    import warnings
                    warnings.warn(f"Failed to load {path}: {e}")

        return scripts

    def find_script(
        self,
        name: str,
        script_type: str,
        search_paths: List[Union[str, Path]],
    ) -> Optional[ScriptMetadata]:
        """
        Find and load a script by name.

        Searches in order: .lua.yaml then .lua in each search path.

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
                # Try .lua.yaml first
                yaml_path = type_dir / f"{name}.lua.yaml"
                if yaml_path.exists():
                    return self.load_file(yaml_path)

                # Fall back to .lua
                lua_path = type_dir / f"{name}.lua"
                if lua_path.exists():
                    return self.load_file(lua_path)

            # Try base directory
            yaml_path = base_path / f"{name}.lua.yaml"
            if yaml_path.exists():
                return self.load_file(yaml_path)

            lua_path = base_path / f"{name}.lua"
            if lua_path.exists():
                return self.load_file(lua_path)

        return None


# Convenience function
def load_script(path: Union[str, Path]) -> ScriptMetadata:
    """Load a single script file."""
    return ScriptLoader().load_file(path)
