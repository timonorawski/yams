"""
Game Mode Loader - YAML configuration loading with Pydantic validation.

This module provides functionality to load and validate game mode configurations
from YAML files using Pydantic models. It discovers available modes and provides
a clean interface for loading mode configurations.

Examples:
    >>> loader = GameModeLoader()
    >>> mode_config = loader.load_mode("classic_ducks")
    >>> print(mode_config.name)
    'Classic Duck Hunt'
    >>> available = loader.list_available_modes()
    ['classic_ducks', 'classic_linear']
"""

from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import ValidationError

from models.duckhunt import GameModeConfig


class GameModeLoader:
    """Loads and validates game mode configurations from YAML files.

    This class discovers game mode YAML files in the modes/ directory,
    loads them, and validates them using Pydantic models. It provides
    error handling for missing files and invalid configurations.

    Attributes:
        modes_dir: Path to the directory containing mode YAML files

    Examples:
        >>> loader = GameModeLoader()
        >>> config = loader.load_mode("classic_ducks")
        >>> config.name
        'Classic Duck Hunt'
        >>> loader.mode_exists("classic_ducks")
        True
    """

    def __init__(self, modes_dir: Optional[Path] = None):
        """Initialize the game mode loader.

        Args:
            modes_dir: Optional custom path to modes directory.
                      Defaults to ./modes/ relative to current directory.
        """
        if modes_dir is None:
            # Default to modes/ directory in current working directory
            modes_dir = Path.cwd() / "modes"

        self.modes_dir = Path(modes_dir)

        # Create modes directory if it doesn't exist
        if not self.modes_dir.exists():
            self.modes_dir.mkdir(parents=True, exist_ok=True)

    def load_mode(self, mode_id: str) -> GameModeConfig:
        """Load and validate a game mode configuration from YAML.

        Reads the YAML file, parses it with PyYAML, and validates
        it using the Pydantic GameModeConfig model.

        Args:
            mode_id: The ID of the mode to load (without .yaml extension)

        Returns:
            Validated GameModeConfig instance

        Raises:
            FileNotFoundError: If the mode YAML file doesn't exist
            ValidationError: If the YAML content is invalid
            yaml.YAMLError: If the YAML syntax is malformed

        Examples:
            >>> loader = GameModeLoader()
            >>> config = loader.load_mode("classic_ducks")
            >>> config.trajectory.algorithm
            'bezier_3d'
        """
        yaml_path = self.modes_dir / f"{mode_id}.yaml"

        if not yaml_path.exists():
            raise FileNotFoundError(
                f"Game mode '{mode_id}' not found. "
                f"Expected file: {yaml_path}"
            )

        # Load YAML file
        try:
            with open(yaml_path, 'r') as f:
                config_dict = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Failed to parse YAML file '{yaml_path}': {e}"
            )

        # Validate with Pydantic
        try:
            config = GameModeConfig(**config_dict)
        except ValidationError as e:
            raise ValueError(
                f"Invalid game mode configuration in '{yaml_path}':\n{e}"
            ) from e

        return config

    def list_available_modes(self) -> List[str]:
        """List all available game mode IDs.

        Discovers all .yaml files in the modes directory and returns
        their IDs (filenames without .yaml extension).

        Returns:
            List of mode IDs sorted alphabetically

        Examples:
            >>> loader = GameModeLoader()
            >>> modes = loader.list_available_modes()
            >>> 'classic_ducks' in modes
            True
        """
        if not self.modes_dir.exists():
            return []

        mode_files = self.modes_dir.glob("*.yaml")
        mode_ids = [f.stem for f in mode_files]
        return sorted(mode_ids)

    def mode_exists(self, mode_id: str) -> bool:
        """Check if a game mode exists.

        Args:
            mode_id: The ID of the mode to check

        Returns:
            True if the mode YAML file exists, False otherwise

        Examples:
            >>> loader = GameModeLoader()
            >>> loader.mode_exists("classic_ducks")
            True
            >>> loader.mode_exists("nonexistent_mode")
            False
        """
        yaml_path = self.modes_dir / f"{mode_id}.yaml"
        return yaml_path.exists()

    def get_mode_info(self, mode_id: str) -> dict:
        """Get basic metadata about a mode without full validation.

        This is useful for displaying mode information in menus
        without loading the entire configuration.

        Args:
            mode_id: The ID of the mode

        Returns:
            Dictionary with mode metadata (name, description, etc.)

        Raises:
            FileNotFoundError: If the mode doesn't exist
            yaml.YAMLError: If the YAML is malformed

        Examples:
            >>> loader = GameModeLoader()
            >>> info = loader.get_mode_info("classic_ducks")
            >>> info['name']
            'Classic Duck Hunt'
        """
        yaml_path = self.modes_dir / f"{mode_id}.yaml"

        if not yaml_path.exists():
            raise FileNotFoundError(f"Game mode '{mode_id}' not found")

        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)

        # Return only metadata fields
        return {
            'name': config_dict.get('name', mode_id),
            'description': config_dict.get('description', ''),
            'author': config_dict.get('author', 'Unknown'),
            'version': config_dict.get('version', '0.0.0'),
            'unlock_requirement': config_dict.get('unlock_requirement', 0),
        }
