"""
Common level support for AMS games.

Provides base classes and utilities for games that use YAML-based level definitions.
Games can opt-in to level support by defining a LEVELS_DIR class attribute and
implementing _load_level_data() to parse their game-specific level format.

Level Groups:
Level groups define sequences of levels for campaigns, tutorials, or challenges.
They are defined in YAML files with a `group: true` marker.

Example level group (campaign.yaml):
    group: true
    name: "Campaign"
    description: "The main story campaign"
    levels:
      - tutorial_01
      - tutorial_02
      - level_01
      - level_02
      - boss_01
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic

# YAML is optional - not available in WASM/browser environment
# Browser builds use JSON files converted from YAML during build
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None  # type: ignore


# =============================================================================
# Schema Validation
# =============================================================================

import os

_level_schema: Optional[Dict[str, Any]] = None
_SCHEMAS_DIR = Path(__file__).parent.parent.parent / 'schemas'

# Set AMS_SKIP_SCHEMA_VALIDATION=1 to disable strict validation
_SKIP_VALIDATION = os.environ.get('AMS_SKIP_SCHEMA_VALIDATION', '').lower() in ('1', 'true', 'yes')


class SchemaValidationError(Exception):
    """Raised when YAML data fails schema validation."""
    pass


def _get_level_schema() -> Optional[Dict[str, Any]]:
    """Lazy-load level schema."""
    global _level_schema
    if _level_schema is None:
        schema_path = _SCHEMAS_DIR / 'level.schema.json'
        if schema_path.exists():
            with open(schema_path) as f:
                _level_schema = json.load(f)
    return _level_schema


def validate_level_yaml(data: Dict[str, Any], source_path: Optional[Path] = None) -> None:
    """Validate level YAML data against schema.

    Args:
        data: Parsed YAML data
        source_path: Optional path for error messages

    Raises:
        SchemaValidationError: If validation fails (unless AMS_SKIP_SCHEMA_VALIDATION=1)
        ImportError: If jsonschema is not installed (unless AMS_SKIP_SCHEMA_VALIDATION=1)
    """
    schema = _get_level_schema()
    if schema is None:
        error_msg = f"Schema file not found: {_SCHEMAS_DIR / 'level.schema.json'}"
        if _SKIP_VALIDATION:
            print(f"[LevelLoader] Warning: {error_msg}")
            return
        raise SchemaValidationError(error_msg)

    try:
        import jsonschema
    except ImportError as e:
        error_msg = "jsonschema package not installed - required for YAML validation"
        if _SKIP_VALIDATION:
            print(f"[LevelLoader] Warning: {error_msg}")
            return
        raise ImportError(error_msg) from e

    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        path_str = f" in {source_path}" if source_path else ""
        error_msg = f"Schema validation error{path_str}: {e.message} at {'/'.join(str(p) for p in e.absolute_path)}"
        if _SKIP_VALIDATION:
            print(f"[LevelLoader] Warning: {error_msg}")
        else:
            raise SchemaValidationError(error_msg) from e
    except jsonschema.SchemaError as e:
        error_msg = f"Invalid schema: {e.message}"
        if _SKIP_VALIDATION:
            print(f"[LevelLoader] Warning: {error_msg}")
        else:
            raise SchemaValidationError(error_msg) from e


def _load_data_file(path: Path) -> Dict[str, Any]:
    """Load data from YAML or JSON file.

    In browser environment, uses JSON. In native environment, uses YAML.
    """
    # Check for JSON version first (browser-compatible)
    json_path = path.with_suffix('.json')
    if json_path.exists():
        with open(json_path, 'r') as f:
            return json.load(f) or {}

    # Fall back to YAML if available
    if path.suffix == '.yaml' and path.exists():
        if not HAS_YAML:
            raise ImportError(
                f"Cannot load {path}: PyYAML not available. "
                "In browser builds, use JSON files instead."
            )
        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}

    raise FileNotFoundError(f"No data file found: {path}")


# =============================================================================
# Level Data Classes
# =============================================================================

@dataclass
class LevelInfo:
    """Basic level metadata (common to all games).

    This is the minimal info needed for level selection UI.
    Games extend this with their own LevelData class for full config.
    """
    name: str
    slug: str  # Filename without extension, used as identifier
    description: str = ""
    difficulty: int = 1  # 1-5 scale
    author: str = "unknown"
    version: int = 1
    file_path: Optional[Path] = None

    # For level groups
    is_group: bool = False
    levels: List[str] = field(default_factory=list)


@dataclass
class LevelGroup:
    """A sequence of levels (campaign, tutorial series, etc.).

    Level groups provide:
    - Ordered progression through multiple levels
    - Group-level metadata (name, description)
    - Progress tracking (current level index)
    """
    name: str
    slug: str
    description: str = ""
    author: str = "unknown"
    levels: List[str] = field(default_factory=list)  # Level slugs in order
    file_path: Optional[Path] = None

    # Runtime state (not persisted)
    current_index: int = 0

    @property
    def current_level(self) -> Optional[str]:
        """Get current level slug."""
        if 0 <= self.current_index < len(self.levels):
            return self.levels[self.current_index]
        return None

    @property
    def is_complete(self) -> bool:
        """Check if all levels completed."""
        return self.current_index >= len(self.levels)

    @property
    def progress(self) -> float:
        """Progress as 0-1 fraction."""
        if not self.levels:
            return 1.0
        return self.current_index / len(self.levels)

    def advance(self) -> Optional[str]:
        """Advance to next level. Returns next level slug or None if complete."""
        self.current_index += 1
        return self.current_level

    def reset(self) -> None:
        """Reset to first level."""
        self.current_index = 0


# Generic type for game-specific level data
T = TypeVar('T')


class LevelLoader(Generic[T], ABC):
    """Base class for game-specific level loaders.

    Subclasses implement _parse_level_data() to convert YAML dicts
    into their game-specific level configuration dataclass.

    Usage:
        class MyLevelLoader(LevelLoader[MyLevelData]):
            def _parse_level_data(self, data: dict, file_path: Path) -> MyLevelData:
                return MyLevelData(
                    name=data.get('name', 'Untitled'),
                    enemies=data.get('enemies', []),
                    # ... game-specific parsing
                )

        loader = MyLevelLoader(levels_dir)
        levels = loader.list_levels()
        level_data = loader.load_level('tutorial_01')
    """

    def __init__(self, levels_dir: Path):
        """Initialize the level loader.

        Args:
            levels_dir: Directory containing level YAML files
        """
        self._levels_dir = Path(levels_dir)
        self._info_cache: Dict[str, LevelInfo] = {}
        self._group_cache: Dict[str, LevelGroup] = {}

    @property
    def levels_dir(self) -> Path:
        """Get the levels directory."""
        return self._levels_dir

    @abstractmethod
    def _parse_level_data(self, data: Dict[str, Any], file_path: Path) -> T:
        """Parse YAML data into game-specific level configuration.

        Args:
            data: Raw YAML data dict
            file_path: Path to the level file (for error messages)

        Returns:
            Game-specific level data object
        """
        pass

    def list_levels(self, category: Optional[str] = None) -> List[str]:
        """List available level slugs.

        Args:
            category: Optional subdirectory to search in

        Returns:
            List of level slugs (sorted)
        """
        search_dir = self._levels_dir / category if category else self._levels_dir

        if not search_dir.exists():
            return []

        levels = set()  # Use set to avoid duplicates from .yaml and .json
        for ext in ['*.yaml', '*.json']:
            for path in search_dir.rglob(ext):
                # Skip hidden files and groups
                if path.name.startswith("_") or path.name.startswith("."):
                    continue

                # Check if it's a group file
                info = self.get_level_info(path.stem)
                if info and not info.is_group:
                    levels.add(path.stem)

        return sorted(levels)

    def list_groups(self) -> List[str]:
        """List available level group slugs.

        Returns:
            List of group slugs (sorted)
        """
        if not self._levels_dir.exists():
            return []

        groups = set()  # Use set to avoid duplicates from .yaml and .json
        for ext in ['*.yaml', '*.json']:
            for path in self._levels_dir.rglob(ext):
                if path.name.startswith("_") or path.name.startswith("."):
                    continue

                info = self.get_level_info(path.stem)
                if info and info.is_group:
                    groups.add(path.stem)

        return sorted(groups)

    def get_level_info(self, slug: str) -> Optional[LevelInfo]:
        """Get level metadata without loading full configuration.

        Args:
            slug: Level identifier (filename without .yaml)

        Returns:
            LevelInfo or None if not found
        """
        if slug in self._info_cache:
            return self._info_cache[slug]

        path = self._find_level_file(slug)
        if not path:
            return None

        try:
            data = _load_data_file(path)

            is_group = data.get('group', False)

            info = LevelInfo(
                name=data.get('name', slug),
                slug=slug,
                description=data.get('description', ''),
                difficulty=data.get('difficulty', 1),
                author=data.get('author', 'unknown'),
                version=data.get('version', 1),
                file_path=path,
                is_group=is_group,
                levels=data.get('levels', []) if is_group else [],
            )

            self._info_cache[slug] = info
            return info

        except Exception:
            return None

    def load_level(self, slug: str) -> T:
        """Load a level by slug.

        Args:
            slug: Level identifier (filename without .yaml)

        Returns:
            Game-specific level data object

        Raises:
            FileNotFoundError: If level file doesn't exist
            ValueError: If level file is invalid
        """
        path = self._find_level_file(slug)
        if not path:
            raise FileNotFoundError(f"Level not found: {slug}")

        data = _load_data_file(path)

        if not data:
            raise ValueError(f"Empty level file: {slug}")

        # Validate against schema (raises SchemaValidationError unless AMS_SKIP_SCHEMA_VALIDATION=1)
        validate_level_yaml(data, path)

        if data.get('group', False):
            raise ValueError(f"'{slug}' is a level group, not a level")

        return self._parse_level_data(data, path)

    def load_group(self, slug: str) -> LevelGroup:
        """Load a level group by slug.

        Args:
            slug: Group identifier (filename without .yaml)

        Returns:
            LevelGroup object

        Raises:
            FileNotFoundError: If group file doesn't exist
            ValueError: If file is not a group
        """
        if slug in self._group_cache:
            group = self._group_cache[slug]
            group.reset()  # Reset progress for new load
            return group

        path = self._find_level_file(slug)
        if not path:
            raise FileNotFoundError(f"Level group not found: {slug}")

        data = _load_data_file(path)

        if not data:
            raise ValueError(f"Empty group file: {slug}")

        if not data.get('group', False):
            raise ValueError(f"'{slug}' is a level, not a group")

        group = LevelGroup(
            name=data.get('name', slug),
            slug=slug,
            description=data.get('description', ''),
            author=data.get('author', 'unknown'),
            levels=data.get('levels', []),
            file_path=path,
        )

        self._group_cache[slug] = group
        return group

    def _find_level_file(self, slug: str) -> Optional[Path]:
        """Find the level file for a slug.

        Searches in the levels directory and common subdirectories.
        Checks for both .yaml and .json extensions.

        Args:
            slug: Level identifier

        Returns:
            Path to level file, or None if not found
        """
        # Check both extensions (.json preferred for browser compatibility)
        extensions = ['.json', '.yaml']

        # Direct path
        for ext in extensions:
            direct = self._levels_dir / f"{slug}{ext}"
            if direct.exists():
                return direct

        # Check subdirectories
        subdirs = ['tutorial', 'campaign', 'challenge', 'examples', 'custom']
        for subdir in subdirs:
            for ext in extensions:
                path = self._levels_dir / subdir / f"{slug}{ext}"
                if path.exists():
                    return path

        # Search recursively as last resort
        for ext in extensions:
            for path in self._levels_dir.rglob(f"{slug}{ext}"):
                return path

        return None

    def get_all_info(self) -> Dict[str, LevelInfo]:
        """Get info for all levels (cached).

        Returns:
            Dict mapping slug to LevelInfo
        """
        # Populate cache
        for slug in self.list_levels():
            self.get_level_info(slug)

        for slug in self.list_groups():
            self.get_level_info(slug)

        return self._info_cache.copy()


# =============================================================================
# Simple Level Loader (for games with basic level needs)
# =============================================================================

class SimpleLevelLoader(LevelLoader[Dict[str, Any]]):
    """Simple level loader that returns raw YAML dicts.

    For games that don't need a custom level data class,
    or want to handle parsing themselves.
    """

    def _parse_level_data(self, data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Return the raw YAML data with file_path added."""
        data['_file_path'] = str(file_path)
        return data


# =============================================================================
# Level Support Mixin for BaseGame
# =============================================================================

class LevelSupportMixin:
    """Mixin providing level support for BaseGame subclasses.

    Add this mixin and define LEVELS_DIR to enable:
    - --level CLI argument
    - --list-levels CLI argument
    - --level-group CLI argument
    - Level loading and group progression

    Usage:
        class MyGame(LevelSupportMixin, BaseGame):
            LEVELS_DIR = Path(__file__).parent / 'levels'

            def _create_level_loader(self) -> LevelLoader:
                return MyLevelLoader(self.LEVELS_DIR)

            def _apply_level_config(self, level_data) -> None:
                # Apply level configuration to game state
                self._enemies = level_data.enemies
                # ...
    """

    # Override in subclass
    LEVELS_DIR: Optional[Path] = None

    # Level-related CLI arguments (added to game's ARGUMENTS)
    _LEVEL_ARGUMENTS = [
        {
            'name': '--level',
            'type': str,
            'default': None,
            'help': 'Level to play (slug or path)'
        },
        {
            'name': '--list-levels',
            'action': 'store_true',
            'default': False,
            'help': 'List available levels and exit'
        },
        {
            'name': '--level-group',
            'type': str,
            'default': None,
            'help': 'Play through a level group (campaign, tutorial, etc.)'
        },
        {
            'name': '--choose-level',
            'action': 'store_true',
            'default': False,
            'help': 'Show level chooser UI before starting'
        },
    ]

    def _init_level_support(
        self,
        level: Optional[str] = None,
        level_group: Optional[str] = None,
        list_levels: bool = False,
        choose_level: bool = False,
    ) -> None:
        """Initialize level support.

        Call this in __init__ after super().__init__().

        Args:
            level: Level slug to load
            level_group: Level group slug to load
            list_levels: Print level list and exit
            choose_level: Show level chooser UI
        """
        self._level_loader: Optional[LevelLoader] = None
        self._current_level_slug: Optional[str] = None
        self._current_level_data: Any = None
        self._current_group: Optional[LevelGroup] = None
        self._show_level_chooser = choose_level and level is None and level_group is None

        # Create loader if levels dir is defined
        if self.LEVELS_DIR and self.LEVELS_DIR.exists():
            self._level_loader = self._create_level_loader()

        # Handle list-levels request
        if list_levels:
            self._print_levels()
            import sys
            sys.exit(0)

        # Load level group if specified
        if level_group and self._level_loader:
            self._current_group = self._level_loader.load_group(level_group)
            level = self._current_group.current_level

        # Load specific level if specified
        if level and self._level_loader:
            self._load_level(level)

    def _create_level_loader(self) -> LevelLoader:
        """Create the level loader instance.

        Override in subclass to return a game-specific loader.
        Default returns SimpleLevelLoader.
        """
        return SimpleLevelLoader(self.LEVELS_DIR)

    def _load_level(self, slug: str) -> bool:
        """Load a level by slug.

        Args:
            slug: Level identifier

        Returns:
            True if loaded successfully
        """
        if not self._level_loader:
            return False

        try:
            self._current_level_data = self._level_loader.load_level(slug)
            self._current_level_slug = slug
            self._apply_level_config(self._current_level_data)
            return True
        except (FileNotFoundError, ValueError) as e:
            print(f"Failed to load level '{slug}': {e}")
            return False

    def _apply_level_config(self, level_data: Any) -> None:
        """Apply loaded level configuration to game state.

        Override in subclass to handle game-specific level setup.

        Args:
            level_data: The loaded level data object
        """
        pass  # Default: no-op

    def _advance_to_next_level(self) -> bool:
        """Advance to next level in group (if playing a group).

        Returns:
            True if advanced to next level, False if group complete
        """
        if not self._current_group:
            return False

        next_level = self._current_group.advance()
        if next_level:
            return self._load_level(next_level)

        return False

    def _print_levels(self) -> None:
        """Print available levels to stdout."""
        if not self._level_loader:
            print("No levels directory configured")
            return

        print("\nAvailable levels:")
        print("-" * 40)

        levels = self._level_loader.list_levels()
        for slug in levels:
            info = self._level_loader.get_level_info(slug)
            if info:
                diff_str = "*" * info.difficulty
                print(f"  {slug:20} [{diff_str:5}] {info.name}")
            else:
                print(f"  {slug}")

        groups = self._level_loader.list_groups()
        if groups:
            print("\nLevel groups:")
            print("-" * 40)
            for slug in groups:
                info = self._level_loader.get_level_info(slug)
                if info:
                    count = len(info.levels)
                    print(f"  {slug:20} ({count} levels) {info.name}")
                else:
                    print(f"  {slug}")

        print()

    @property
    def current_level_name(self) -> str:
        """Get current level display name."""
        if self._level_loader and self._current_level_slug:
            info = self._level_loader.get_level_info(self._current_level_slug)
            if info:
                return info.name
        return ""

    @property
    def current_level_slug(self) -> Optional[str]:
        """Get current level slug."""
        return self._current_level_slug

    @property
    def current_group(self) -> Optional[LevelGroup]:
        """Get current level group (if playing a group)."""
        return self._current_group

    @property
    def has_levels(self) -> bool:
        """Check if this game has level support."""
        return self._level_loader is not None

    @classmethod
    def get_level_arguments(cls) -> List[Dict[str, Any]]:
        """Get level-related CLI arguments."""
        if cls.LEVELS_DIR:
            return cls._LEVEL_ARGUMENTS.copy()
        return []
