"""
Excel Differ - Configuration Data Classes
"""

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import os


@dataclass
class RepoConfig:
    """Repository configuration (for source or destination)"""
    implementation: str
    config: dict = field(default_factory=dict)

    def __post_init__(self):
        """Resolve environment variables in config"""
        if 'token' in self.config:
            self.config['token'] = self._resolve_env_var(self.config['token'])

    def _resolve_env_var(self, value: str) -> str:
        """Resolve ${ENV_VAR} references"""
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            resolved = os.getenv(env_var)
            if not resolved:
                raise ValueError(f"Environment variable {env_var} not set")
            return resolved
        return value


@dataclass
class ComponentConfig:
    """Generic component configuration"""
    implementation: str
    config: dict = field(default_factory=dict)


@dataclass
class ExcelDifferConfig:
    """Main configuration"""
    source: RepoConfig
    destination: RepoConfig
    converter: ComponentConfig
    flattener: ComponentConfig
