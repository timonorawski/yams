"""
Behavior Loader - loads pure YAML behavior bundles.

Behaviors are collections of interactions that can be applied to entity types.
They provide reusable patterns like gravity, animation, and screen bounds checking.

Usage:
    loader = BehaviorLoader(content_fs)

    # Load a behavior definition
    behavior = loader.load('gravity')

    # Expand behaviors for an entity type
    interactions = loader.expand_behaviors(
        behaviors=['gravity', 'destroy_offscreen'],
        behavior_config={'gravity': {'acceleration': 800}}
    )
"""

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ams.yaml import load as yaml_load
from ams.logging import get_logger

log = get_logger('behavior_loader')


@dataclass
class BehaviorConfig:
    """Configuration parameter for a behavior."""
    type: str = 'number'
    default: Any = None
    description: str = ''


@dataclass
class BehaviorDefinition:
    """A loaded behavior definition."""
    name: str
    description: str = ''
    config: Dict[str, BehaviorConfig] = field(default_factory=dict)
    interactions: Dict[str, Any] = field(default_factory=dict)
    source_path: Optional[str] = None


class BehaviorLoader:
    """
    Loads YAML behavior bundles and expands them into interactions.

    Behavior bundles are pure YAML files that define:
    - name: Behavior identifier
    - config: Configurable parameters with defaults
    - interactions: Interaction definitions to merge into entity types
    """

    def __init__(self, content_fs=None, behaviors_dir: str = 'lua/behaviors'):
        """
        Initialize the behavior loader.

        Args:
            content_fs: Content filesystem for loading files
            behaviors_dir: Directory containing behavior YAML files
        """
        self._content_fs = content_fs
        self._behaviors_dir = behaviors_dir
        self._cache: Dict[str, BehaviorDefinition] = {}

    def load(self, name: str) -> Optional[BehaviorDefinition]:
        """
        Load a behavior definition by name.

        Args:
            name: Behavior name (e.g., 'gravity')

        Returns:
            BehaviorDefinition or None if not found
        """
        if name in self._cache:
            return self._cache[name]

        # Try to load from filesystem
        yaml_path = f'{self._behaviors_dir}/{name}.yaml'

        try:
            if self._content_fs and self._content_fs.exists(yaml_path):
                content = self._content_fs.readtext(yaml_path)
                data = yaml_load(content)
            else:
                # Fallback to direct file access
                full_path = Path(__file__).parent / 'behaviors' / f'{name}.yaml'
                if full_path.exists():
                    with open(full_path, 'r') as f:
                        data = yaml_load(f.read())
                else:
                    log.warning(f"Behavior not found: {name}")
                    return None
        except Exception as e:
            log.error(f"Failed to load behavior {name}: {e}")
            return None

        # Parse the definition
        behavior = self._parse_definition(data, yaml_path)
        if behavior:
            self._cache[name] = behavior

        return behavior

    def _parse_definition(self, data: Dict[str, Any], source_path: str) -> Optional[BehaviorDefinition]:
        """Parse a behavior definition from YAML data."""
        if not isinstance(data, dict):
            log.error(f"Invalid behavior definition: expected dict, got {type(data)}")
            return None

        name = data.get('name', '')
        if not name:
            log.error(f"Behavior missing 'name' field: {source_path}")
            return None

        # Parse config
        config = {}
        raw_config = data.get('config', {})
        for key, value in raw_config.items():
            if isinstance(value, dict):
                config[key] = BehaviorConfig(
                    type=value.get('type', 'number'),
                    default=value.get('default'),
                    description=value.get('description', '')
                )
            else:
                # Simple form: config: {acceleration: 600}
                config[key] = BehaviorConfig(default=value)

        return BehaviorDefinition(
            name=name,
            description=data.get('description', ''),
            config=config,
            interactions=data.get('interactions', {}),
            source_path=source_path
        )

    def expand_behaviors(
        self,
        behaviors: List[str],
        behavior_config: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Expand a list of behaviors into merged interactions.

        Args:
            behaviors: List of behavior names to expand
            behavior_config: Config overrides per behavior

        Returns:
            Merged interactions dict ready to add to entity type
        """
        behavior_config = behavior_config or {}
        merged_interactions: Dict[str, Any] = {}

        for behavior_name in behaviors:
            behavior = self.load(behavior_name)
            if not behavior:
                log.warning(f"Skipping unknown behavior: {behavior_name}")
                continue

            # Get config values (defaults + overrides)
            config_values = {}
            for key, cfg in behavior.config.items():
                config_values[key] = cfg.default

            # Apply user overrides
            if behavior_name in behavior_config:
                config_values.update(behavior_config[behavior_name])

            # Expand interactions with config substitution
            expanded = self._substitute_config(
                copy.deepcopy(behavior.interactions),
                config_values
            )

            # Merge into result
            self._merge_interactions(merged_interactions, expanded)

        return merged_interactions

    def _substitute_config(self, data: Any, config: Dict[str, Any]) -> Any:
        """
        Substitute $config.X references with actual values.

        Args:
            data: Data structure to process
            config: Config values to substitute

        Returns:
            Data with substitutions applied
        """
        if isinstance(data, str):
            # Check for $config.X pattern
            match = re.match(r'^\$config\.(\w+)$', data)
            if match:
                key = match.group(1)
                return config.get(key, data)
            return data

        elif isinstance(data, dict):
            return {k: self._substitute_config(v, config) for k, v in data.items()}

        elif isinstance(data, list):
            return [self._substitute_config(item, config) for item in data]

        return data

    def _merge_interactions(
        self,
        target: Dict[str, Any],
        source: Dict[str, Any]
    ) -> None:
        """
        Merge source interactions into target.

        Handles array syntax for multiple interactions with same target.
        """
        for target_entity, interactions in source.items():
            if target_entity not in target:
                target[target_entity] = interactions
            else:
                # Both have interactions for this target - merge
                existing = target[target_entity]

                # Normalize to lists
                if not isinstance(existing, list):
                    existing = [existing]
                if not isinstance(interactions, list):
                    interactions = [interactions]

                target[target_entity] = existing + interactions

    def clear_cache(self) -> None:
        """Clear the behavior cache."""
        self._cache.clear()
