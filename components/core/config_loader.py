"""
Excel Differ - Configuration Loader

Loads and validates YAML configuration files.
"""

import yaml
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from .config import ExcelDifferConfig, RepoConfig, ComponentConfig


def load_config(config_path: Optional[Path] = None) -> ExcelDifferConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML config file. If None, looks for:
                    - $EXCEL_DIFFER_CONFIG environment variable
                    - ./config/excel-differ.yaml
                    - ./excel-differ.yaml

    Returns:
        ExcelDifferConfig object

    Raises:
        FileNotFoundError: If config file not found
        ValueError: If config is invalid
    """
    # Load .env file if it exists
    load_dotenv()

    # Determine config file path
    if config_path is None:
        import os
        env_config = os.getenv('EXCEL_DIFFER_CONFIG')
        if env_config:
            config_path = Path(env_config)
        elif Path('config/excel-differ.yaml').exists():
            config_path = Path('config/excel-differ.yaml')
        elif Path('excel-differ.yaml').exists():
            config_path = Path('excel-differ.yaml')
        else:
            raise FileNotFoundError(
                "No config file found. Provide path or set EXCEL_DIFFER_CONFIG environment variable."
            )

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load YAML
    with open(config_path) as f:
        data = yaml.safe_load(f)

    # Validate required sections
    required = ['source', 'destination', 'converter', 'flattener']
    for section in required:
        if section not in data:
            raise ValueError(f"Missing required section '{section}' in config")

    # Parse configuration
    try:
        config = ExcelDifferConfig(
            source=RepoConfig(
                implementation=data['source']['implementation'],
                config=data['source'].get('config', {})
            ),
            destination=RepoConfig(
                implementation=data['destination']['implementation'],
                config=data['destination'].get('config', {})
            ),
            converter=ComponentConfig(
                implementation=data['converter']['implementation'],
                config=data['converter'].get('config', {})
            ),
            flattener=ComponentConfig(
                implementation=data['flattener']['implementation'],
                config=data['flattener'].get('config', {})
            )
        )
    except KeyError as e:
        raise ValueError(f"Invalid config structure: missing {e}")

    return config
