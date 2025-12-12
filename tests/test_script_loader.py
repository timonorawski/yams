"""
Script Loader Tests

Tests for the YAML-based Lua script loader (ScriptLoader).
Validates loading of .lua.yaml files, inline scripts, and error handling.

Run with: pytest tests/test_script_loader.py -v
"""

import pytest
import tempfile
import os
from pathlib import Path

from ams.games.game_engine.lua.script_loader import (
    ScriptLoader,
    ScriptMetadata,
    ScriptValidationError,
)


# Sample valid script content
VALID_BEHAVIOR_YAML = """
type: behavior
name: test_gravity
description: Apply gravity to entities
version: "1.0"
tags: [physics, motion]

config:
  acceleration:
    type: float
    description: Gravity in pixels/second^2
    default: 800

provides:
  hooks: [on_update]
  properties: [vy]

lua: |
  local gravity = {}
  function gravity.on_update(entity_id, dt)
    local vy = ams.get_prop(entity_id, "vy") or 0
    vy = vy + 800 * dt
    ams.set_prop(entity_id, "vy", vy)
  end
  return gravity
"""

VALID_GENERATOR_YAML = """
type: generator
name: random_color
description: Generate a random color

args:
  saturation:
    type: float
    default: 1.0
    min: 0
    max: 1

provides:
  hooks: [generate]

lua: |
  local gen = {}
  function gen.generate(args)
    local s = args.saturation or 1.0
    return string.format("#%02x%02x%02x",
      math.floor(math.random() * 255 * s),
      math.floor(math.random() * 255 * s),
      math.floor(math.random() * 255 * s))
  end
  return gen
"""

VALID_COLLISION_ACTION_YAML = """
type: collision_action
description: Take damage on collision

config:
  damage:
    type: int
    default: 1

lua: |
  local action = {}
  function action.execute(a_id, b_id, modifier)
    local damage = (modifier and modifier.damage) or 1
    local hp = ams.get_prop(b_id, "hp") or 0
    ams.set_prop(b_id, "hp", hp - damage)
  end
  return action
"""

MINIMAL_VALID_YAML = """
type: behavior
lua: |
  local b = {}
  function b.on_update(id, dt) end
  return b
"""


class TestScriptLoaderInit:
    """Test ScriptLoader initialization."""

    def test_init_default(self):
        """ScriptLoader initializes with defaults."""
        loader = ScriptLoader()
        assert loader is not None

    def test_init_with_schema_validation_disabled(self):
        """ScriptLoader can disable schema validation."""
        loader = ScriptLoader(validate=False)
        assert loader is not None


class TestLoadYamlFile:
    """Test loading .lua.yaml files."""

    def test_load_valid_behavior(self, tmp_path):
        """Load a valid behavior script."""
        script_file = tmp_path / "gravity.lua.yaml"
        script_file.write_text(VALID_BEHAVIOR_YAML)

        loader = ScriptLoader(validate=False)
        metadata = loader.load_file(script_file)

        assert metadata.name == "test_gravity"
        assert metadata.type == "behavior"
        assert metadata.description == "Apply gravity to entities"
        assert metadata.version == "1.0"
        assert "physics" in metadata.tags
        assert "on_update" in metadata.provides.get("hooks", [])
        assert "vy" in metadata.provides.get("properties", [])
        assert "gravity" in metadata.code  # Lua code present

    def test_load_valid_generator(self, tmp_path):
        """Load a valid generator script."""
        script_file = tmp_path / "random_color.lua.yaml"
        script_file.write_text(VALID_GENERATOR_YAML)

        loader = ScriptLoader(validate=False)
        metadata = loader.load_file(script_file)

        assert metadata.name == "random_color"
        assert metadata.type == "generator"
        assert "saturation" in metadata.args
        assert metadata.args["saturation"]["type"] == "float"

    def test_load_valid_collision_action(self, tmp_path):
        """Load a valid collision_action script."""
        script_file = tmp_path / "take_damage.lua.yaml"
        script_file.write_text(VALID_COLLISION_ACTION_YAML)

        loader = ScriptLoader(validate=False)
        metadata = loader.load_file(script_file)

        # Name should be derived from filename
        assert metadata.name == "take_damage"
        assert metadata.type == "collision_action"

    def test_load_minimal_script(self, tmp_path):
        """Load script with only required fields."""
        script_file = tmp_path / "minimal.lua.yaml"
        script_file.write_text(MINIMAL_VALID_YAML)

        loader = ScriptLoader(validate=False)
        metadata = loader.load_file(script_file)

        assert metadata.name == "minimal"
        assert metadata.type == "behavior"
        assert "function b.on_update" in metadata.code

    def test_name_from_filename(self, tmp_path):
        """Script name defaults to filename if not specified."""
        script_content = """
type: behavior
lua: |
  local b = {}
  return b
"""
        script_file = tmp_path / "my_custom_behavior.lua.yaml"
        script_file.write_text(script_content)

        loader = ScriptLoader(validate=False)
        metadata = loader.load_file(script_file)

        assert metadata.name == "my_custom_behavior"

    def test_explicit_name_overrides_filename(self, tmp_path):
        """Explicit name in YAML overrides filename."""
        script_content = """
type: behavior
name: explicit_name
lua: |
  local b = {}
  return b
"""
        script_file = tmp_path / "filename.lua.yaml"
        script_file.write_text(script_content)

        loader = ScriptLoader(validate=False)
        metadata = loader.load_file(script_file)

        assert metadata.name == "explicit_name"


class TestLoadYamlFileErrors:
    """Test error handling when loading files."""

    def test_missing_type_field(self, tmp_path):
        """Error when 'type' field is missing."""
        script_content = """
lua: |
  local b = {}
  return b
"""
        script_file = tmp_path / "no_type.lua.yaml"
        script_file.write_text(script_content)

        loader = ScriptLoader(validate=False)
        with pytest.raises(ScriptValidationError, match="Missing required field 'type'"):
            loader.load_file(script_file)

    def test_missing_lua_field(self, tmp_path):
        """Error when 'lua' field is missing."""
        script_content = """
type: behavior
name: no_code
"""
        script_file = tmp_path / "no_code.lua.yaml"
        script_file.write_text(script_content)

        loader = ScriptLoader(validate=False)
        with pytest.raises(ScriptValidationError, match="Missing required field 'lua'"):
            loader.load_file(script_file)

    def test_invalid_type_value(self, tmp_path):
        """Error when 'type' has invalid value."""
        script_content = """
type: invalid_type
lua: |
  return {}
"""
        script_file = tmp_path / "bad_type.lua.yaml"
        script_file.write_text(script_content)

        loader = ScriptLoader(validate=False)
        with pytest.raises(ScriptValidationError, match="Invalid type"):
            loader.load_file(script_file)

    def test_invalid_yaml_syntax(self, tmp_path):
        """Error on invalid YAML syntax."""
        import yaml
        script_content = """
type: behavior
  bad_indent: this is invalid
lua: |
  return {}
"""
        script_file = tmp_path / "bad_yaml.lua.yaml"
        script_file.write_text(script_content)

        loader = ScriptLoader(validate=False)
        # YAML raises ScannerError for invalid syntax
        with pytest.raises(yaml.YAMLError):
            loader.load_file(script_file)

    def test_file_not_found(self):
        """Error when file doesn't exist."""
        loader = ScriptLoader(validate=False)
        with pytest.raises(FileNotFoundError):
            loader.load_file(Path("/nonexistent/file.lua.yaml"))


class TestLoadInline:
    """Test loading inline script definitions."""

    def test_load_inline_behavior(self):
        """Load inline behavior definition."""
        loader = ScriptLoader(validate=False)
        definition = {
            "lua": "local b = {}\nreturn b",
            "description": "Test behavior",
        }

        metadata = loader.load_inline("test_inline", "behavior", definition)

        assert metadata.name == "test_inline"
        assert metadata.type == "behavior"
        assert metadata.description == "Test behavior"
        assert "local b = {}" in metadata.code

    def test_load_inline_with_config(self):
        """Load inline script with config."""
        loader = ScriptLoader(validate=False)
        definition = {
            "lua": "local b = {}\nreturn b",
            "config": {
                "speed": {"type": "float", "default": 100}
            }
        }

        metadata = loader.load_inline("configured", "behavior", definition)

        assert "speed" in metadata.config
        assert metadata.config["speed"]["default"] == 100

    def test_load_inline_generator_with_args(self):
        """Load inline generator with args."""
        loader = ScriptLoader(validate=False)
        definition = {
            "lua": "local g = {}\nfunction g.generate(args) return args.x end\nreturn g",
            "args": {
                "x": {"type": "int", "required": True}
            }
        }

        metadata = loader.load_inline("my_gen", "generator", definition)

        assert metadata.type == "generator"
        assert "x" in metadata.args
        assert metadata.args["x"]["required"] is True

    def test_load_inline_missing_lua(self):
        """Error when inline definition missing 'lua' field."""
        loader = ScriptLoader(validate=False)
        definition = {"description": "No code"}

        with pytest.raises(ScriptValidationError, match="missing required 'lua' field"):
            loader.load_inline("no_code", "behavior", definition)

    def test_load_inline_invalid_type(self):
        """Error when inline type is invalid."""
        loader = ScriptLoader(validate=False)
        definition = {"lua": "return {}"}

        with pytest.raises(ScriptValidationError, match="Invalid type"):
            loader.load_inline("test", "invalid_type", definition)


class TestLoadDirectory:
    """Test loading scripts from a directory."""

    def test_load_from_directory(self, tmp_path):
        """Load all scripts from a directory."""
        # Create test scripts
        (tmp_path / "gravity.lua.yaml").write_text("""
type: behavior
lua: |
  local g = {}
  return g
""")
        (tmp_path / "bounce.lua.yaml").write_text("""
type: behavior
lua: |
  local b = {}
  return b
""")

        loader = ScriptLoader(validate=False)
        scripts = loader.load_directory(tmp_path)

        assert len(scripts) == 2
        names = {s.name for s in scripts}
        assert "gravity" in names
        assert "bounce" in names

    def test_load_directory_loads_both_formats(self, tmp_path):
        """Loading directory loads both .lua.yaml and .lua files."""
        (tmp_path / "yaml_script.lua.yaml").write_text("""
type: behavior
lua: return {}
""")
        (tmp_path / "readme.txt").write_text("Not a script")
        (tmp_path / "legacy_script.lua").write_text("-- legacy lua file\nlocal b = {}\nreturn b")

        loader = ScriptLoader(validate=False)
        scripts = loader.load_directory(tmp_path)

        # Loads both .lua.yaml and .lua files (not .txt)
        assert len(scripts) == 2
        names = {s.name for s in scripts}
        assert "yaml_script" in names
        assert "legacy_script" in names

    def test_load_directory_prefers_yaml_over_lua(self, tmp_path):
        """When both .lua.yaml and .lua exist, prefer .lua.yaml."""
        (tmp_path / "same.lua.yaml").write_text("""
type: behavior
description: From YAML
lua: return {}
""")
        (tmp_path / "same.lua").write_text("-- From .lua\nlocal b = {}\nreturn b")

        loader = ScriptLoader(validate=False)
        scripts = loader.load_directory(tmp_path)

        # Only one script loaded (the .lua.yaml version)
        assert len(scripts) == 1
        assert scripts[0].description == "From YAML"

    def test_load_empty_directory(self, tmp_path):
        """Loading empty directory returns empty list."""
        loader = ScriptLoader(validate=False)
        scripts = loader.load_directory(tmp_path)

        assert scripts == []


class TestFindScript:
    """Test finding scripts by name."""

    def test_find_by_name(self, tmp_path):
        """Find script by name in directory."""
        behavior_dir = tmp_path / "behavior"
        behavior_dir.mkdir()
        (behavior_dir / "target.lua.yaml").write_text("""
type: behavior
lua: return {}
""")
        (behavior_dir / "other.lua.yaml").write_text("""
type: behavior
lua: return {}
""")

        loader = ScriptLoader(validate=False)
        # find_script(name, script_type, search_paths)
        result = loader.find_script("target", "behavior", [tmp_path])

        assert result is not None
        assert result.name == "target"

    def test_find_returns_none_if_not_found(self, tmp_path):
        """find_script returns None if script not found."""
        behavior_dir = tmp_path / "behavior"
        behavior_dir.mkdir()

        loader = ScriptLoader(validate=False)
        result = loader.find_script("nonexistent", "behavior", [tmp_path])

        assert result is None


class TestScriptMetadata:
    """Test ScriptMetadata dataclass."""

    def test_metadata_defaults(self):
        """ScriptMetadata has sensible defaults."""
        metadata = ScriptMetadata(
            name="test",
            type="behavior",
            code="return {}"
        )

        assert metadata.name == "test"
        assert metadata.type == "behavior"
        assert metadata.code == "return {}"
        assert metadata.description is None
        assert metadata.version is None
        assert metadata.author is None
        assert metadata.tags == []
        assert metadata.config == {}
        assert metadata.args == {}
        assert metadata.provides == {}
        assert metadata.requires == {}
        assert metadata.examples == []

    def test_metadata_with_all_fields(self):
        """ScriptMetadata stores all fields."""
        metadata = ScriptMetadata(
            name="full",
            type="generator",
            code="return {}",
            description="A full script",
            version="2.0",
            author="Test Author",
            tags=["tag1", "tag2"],
            config={"speed": {"type": "float"}},
            args={"input": {"type": "string"}},
            provides={"hooks": ["generate"]},
            requires={"behaviors": ["other"]},
            examples=[{"yaml": "example: true"}],
            source_path=Path("/test/path.lua.yaml"),
            source_format="yaml"
        )

        assert metadata.description == "A full script"
        assert metadata.version == "2.0"
        assert metadata.author == "Test Author"
        assert len(metadata.tags) == 2
        assert "speed" in metadata.config
        assert metadata.source_format == "yaml"


class TestValidTypes:
    """Test all valid script types are accepted."""

    @pytest.mark.parametrize("script_type", [
        "behavior",
        "collision_action",
        "generator",
        "input_action",
    ])
    def test_valid_type_accepted(self, tmp_path, script_type):
        """All valid script types are accepted."""
        script_file = tmp_path / f"{script_type}_test.lua.yaml"
        script_file.write_text(f"""
type: {script_type}
lua: return {{}}
""")

        loader = ScriptLoader(validate=False)
        metadata = loader.load_file(script_file)

        assert metadata.type == script_type


class TestRealScripts:
    """Test loading actual scripts from the codebase."""

    @pytest.fixture
    def lua_dir(self):
        """Path to the actual Lua scripts directory."""
        project_root = Path(__file__).parent.parent
        return project_root / "ams" / "games" / "game_engine" / "lua"

    def test_load_gravity_behavior(self, lua_dir):
        """Load the real gravity.lua.yaml."""
        gravity_path = lua_dir / "behavior" / "gravity.lua.yaml"
        if not gravity_path.exists():
            pytest.skip("gravity.lua.yaml not found")

        loader = ScriptLoader(validate=False)
        metadata = loader.load_file(gravity_path)

        assert metadata.name == "gravity"
        assert metadata.type == "behavior"
        assert "on_update" in metadata.provides.get("hooks", [])

    def test_load_all_behaviors(self, lua_dir):
        """Load all behavior scripts without errors."""
        behavior_dir = lua_dir / "behavior"
        if not behavior_dir.exists():
            pytest.skip("behavior directory not found")

        loader = ScriptLoader(validate=False)
        scripts = loader.load_directory(behavior_dir)

        # Should have loaded multiple behaviors
        assert len(scripts) > 0
        for script in scripts:
            assert script.type == "behavior"
            assert script.code  # Has Lua code

    def test_load_all_generators(self, lua_dir):
        """Load all generator scripts without errors."""
        generator_dir = lua_dir / "generator"
        if not generator_dir.exists():
            pytest.skip("generator directory not found")

        loader = ScriptLoader(validate=False)
        scripts = loader.load_directory(generator_dir)

        for script in scripts:
            assert script.type == "generator"

    def test_load_all_collision_actions(self, lua_dir):
        """Load all collision_action scripts without errors."""
        action_dir = lua_dir / "collision_action"
        if not action_dir.exists():
            pytest.skip("collision_action directory not found")

        loader = ScriptLoader(validate=False)
        scripts = loader.load_directory(action_dir)

        for script in scripts:
            assert script.type == "collision_action"


class TestSourceTracking:
    """Test that source information is tracked."""

    def test_source_path_tracked(self, tmp_path):
        """Source path is stored in metadata."""
        script_file = tmp_path / "tracked.lua.yaml"
        script_file.write_text("""
type: behavior
lua: return {}
""")

        loader = ScriptLoader(validate=False)
        metadata = loader.load_file(script_file)

        # source_path is stored as a string
        assert metadata.source_path == str(script_file)
        assert metadata.source_format == "lua.yaml"

    def test_inline_source_format(self):
        """Inline scripts have 'inline' source format."""
        loader = ScriptLoader(validate=False)
        metadata = loader.load_inline("test", "behavior", {"lua": "return {}"})

        assert metadata.source_path is None
        assert metadata.source_format == "inline"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
