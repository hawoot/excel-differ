"""
Excel Differ - Workflow Schema

WHAT THIS FILE DOES:
    Defines the Python dataclass models that represent an Excel Differ workflow.
    These are the "shape" of a valid workflow configuration - what fields are
    required and what they mean.

RELATIONSHIP TO OTHER FILES:
    - workflows/workflow_loader.py reads YAML and converts it to these dataclass instances
    - interfaces.py defines what components DO; this file defines what they're CALLED
    - component_registry.py receives the config dicts from these dataclasses
    - Orchestrator receives a WorkflowDefinition and executes it

THE WORKFLOW STRUCTURE:
    WorkflowDefinition (top level)
    ├── source: SourceDestinationSpec
    ├── destination: SourceDestinationSpec
    ├── converter: ComponentSpec
    └── flattener: ComponentSpec

ENVIRONMENT VARIABLE RESOLUTION:
    This file handles ${ENV_VAR} resolution in config values.
    When YAML contains 'token: ${BITBUCKET_TOKEN}', this is resolved
    to the actual environment variable value during dataclass construction.

EXAMPLE USAGE:
    from components.workflows.workflow_schema import (
        WorkflowDefinition,
        SourceDestinationSpec,
        ComponentSpec
    )

    # Typically you don't create these manually - workflow_loader does it
    # But here's what it looks like:
    workflow = WorkflowDefinition(
        source=SourceDestinationSpec(
            implementation='bitbucket',
            config={
                'url': 'https://bitbucket.org/workspace/repo',
                'branch': 'main',
                'token': 'abc123'  # Already resolved from ${BITBUCKET_TOKEN}
            }
        ),
        destination=SourceDestinationSpec(
            implementation='local_folder',
            config={'folder_path': '/output'}
        ),
        converter=ComponentSpec(
            implementation='noop',
            config={}
        ),
        flattener=ComponentSpec(
            implementation='openpyxl',
            config={'include_computed': False, 'include_literal': True}
        )
    )

    # Access workflow components
    print(workflow.source.implementation)  # 'bitbucket'
    print(workflow.source.config['url'])   # 'https://bitbucket.org/workspace/repo'

    # The orchestrator then uses component_registry to create actual instances:
    from components.component_registry import registry
    source_instance = registry.create_source(
        workflow.source.implementation,  # 'bitbucket'
        workflow.source.config           # {url, branch, token}
    )

SEE ALSO:
    - workflows/workflow_loader.py - Creates these objects from YAML
    - workflows/workflow_definition_templates/ - Example YAML files
    - component_registry.py - Uses these specs to create component instances
"""

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import os


@dataclass
class SourceDestinationSpec:
    """
    Source or destination specification.

    Attributes:
        implementation: Component type (e.g., 'bitbucket', 'local_folder')
        config: Implementation-specific configuration dict

    Environment Variables:
        The 'token' field in config is automatically resolved from ${ENV_VAR} format
        during __post_init__. For example:
        - YAML contains: token: ${BITBUCKET_TOKEN}
        - .env contains: BITBUCKET_TOKEN=my_secret
        - Result: config['token'] = 'my_secret'
    """
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
class ComponentSpec:
    """
    Component specification (converter/flattener).

    Attributes:
        implementation: Component type (e.g., 'openpyxl', 'noop', 'windows_excel')
        config: Implementation-specific configuration dict

    Example:
        flattener = ComponentSpec(
            implementation='openpyxl',
            config={
                'include_computed': False,
                'include_literal': True,
                'include_formats': True,
                'timeout': 900
            }
        )
    """
    implementation: str
    config: dict = field(default_factory=dict)


@dataclass
class StateSpec:
    """
    State file configuration.

    Attributes:
        file_path: Path to the state file (e.g., './state/sync-state.json')

    Example:
        state = StateSpec(file_path='./state/sync-state.json')
    """
    file_path: str


@dataclass
class WorkflowDefinition:
    """
    Complete Excel Differ workflow definition.

    Attributes:
        source: Where to get Excel files (Bitbucket, local folder, etc.)
        destination: Where to upload flattened results
        converter: How to convert files (noop, windows_excel, etc.)
        flattener: How to flatten Excel files (openpyxl, noop, etc.)
        state: Optional state file configuration (defaults to ./.excel-differ-state.json)

    Example:
        workflow = WorkflowDefinition(
            source=SourceDestinationSpec(
                implementation='local_folder',
                config={'folder_path': '/data/excel'}
            ),
            destination=SourceDestinationSpec(
                implementation='bitbucket',
                config={
                    'url': 'https://bitbucket.org/workspace/repo',
                    'token': 'resolved_from_env'
                }
            ),
            converter=ComponentSpec(
                implementation='noop',
                config={}
            ),
            flattener=ComponentSpec(
                implementation='openpyxl',
                config={'include_computed': False}
            ),
            state=StateSpec(file_path='./state/sync-state.json')
        )
    """
    source: SourceDestinationSpec
    destination: SourceDestinationSpec
    converter: ComponentSpec
    flattener: ComponentSpec
    state: Optional[StateSpec] = None

    def __post_init__(self):
        """Set default state config if not provided"""
        if self.state is None:
            self.state = StateSpec(file_path='./.excel-differ-state.json')
