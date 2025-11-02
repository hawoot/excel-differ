"""
Excel Differ - Workflow Loader

WHAT THIS FILE DOES:
    Loads a workflow definition from a YAML file and converts it to Python
    objects. Handles .env loading, YAML parsing, and validation.

RELATIONSHIP TO OTHER FILES:
    - workflows/workflow_schema.py defines the dataclass models this creates
    - component_registry.py is used later to instantiate actual components
    - This file is the ENTRY POINT for loading any workflow configuration
    - Orchestrator calls this to load the workflow before executing

THE LOADING PROCESS:
    1. Load .env file (if present) to populate environment variables
    2. Read YAML file from explicit path
    3. Parse YAML structure
    4. Validate required sections (source, destination, converter, flattener)
    5. Create WorkflowDefinition dataclass (which resolves ${ENV_VAR} references)
    6. Return validated workflow object

EXPLICIT PATH REQUIRED:
    This loader requires an explicit YAML file path - no auto-discovery.
    The user must know exactly which workflow they're loading.

    Why? Because it's critical to know which configuration is being used.
    No magic, no guessing, no fallbacks.

EXAMPLE USAGE:
    from pathlib import Path
    from components.workflows.workflow_loader import load_workflow

    # Load workflow from explicit path
    workflow = load_workflow(Path('components/workflows/workflow_definition.yaml'))

    # Or from user-specified path (e.g., CLI argument)
    import sys
    workflow = load_workflow(Path(sys.argv[1]))

    # Or from environment variable (but still explicit)
    import os
    workflow_path = os.getenv('EXCEL_DIFFER_WORKFLOW')
    if not workflow_path:
        raise ValueError("EXCEL_DIFFER_WORKFLOW environment variable not set")
    workflow = load_workflow(Path(workflow_path))

    # Now you have a WorkflowDefinition object
    print(f"Source: {workflow.source.implementation}")
    print(f"Destination: {workflow.destination.implementation}")
    print(f"Converter: {workflow.converter.implementation}")
    print(f"Flattener: {workflow.flattener.implementation}")

    # Next step: Use component_registry to create actual instances
    from components.component_registry import registry

    source = registry.create_source(
        workflow.source.implementation,
        workflow.source.config
    )
    destination = registry.create_destination(
        workflow.destination.implementation,
        workflow.destination.config
    )
    converter = registry.create_converter(
        workflow.converter.implementation,
        workflow.converter.config
    )
    flattener = registry.create_flattener(
        workflow.flattener.implementation,
        workflow.flattener.config
    )

ERROR HANDLING:
    - FileNotFoundError: YAML file doesn't exist at specified path
    - ValueError: YAML missing required sections (source, destination, converter, flattener)
    - ValueError: YAML has invalid structure (missing 'implementation' field, etc.)
    - ValueError: Environment variable referenced but not set (e.g., ${MISSING_VAR})

YAML STRUCTURE:
    The YAML file must have this structure:

    source:
      implementation: <name>
      config:
        <key>: <value>

    destination:
      implementation: <name>
      config:
        <key>: <value>

    converter:
      implementation: <name>
      config:
        <key>: <value>

    flattener:
      implementation: <name>
      config:
        <key>: <value>

SEE ALSO:
    - workflows/workflow_schema.py - The dataclass models created by this loader
    - workflows/workflow_definition_templates/ - Example YAML files to load
    - .env.example - Example environment variables file
    - component_registry.py - Uses loaded workflow to create component instances
"""

import yaml
from pathlib import Path
from dotenv import load_dotenv

from .schema import WorkflowDefinition, SourceDestinationSpec, ComponentSpec, StateSpec, LoggingSpec


def load_workflow(yaml_path: Path) -> WorkflowDefinition:
    """
    Load workflow definition from YAML file.

    Args:
        yaml_path: Explicit path to workflow YAML file (no fallbacks or auto-discovery)

    Returns:
        WorkflowDefinition object with all components configured

    Raises:
        FileNotFoundError: If YAML file doesn't exist
        ValueError: If YAML is invalid or missing required sections
        ValueError: If environment variable is referenced but not set

    Example:
        workflow = load_workflow(Path('my-workflow.yaml'))
        print(workflow.source.implementation)  # 'bitbucket'
    """
    # Load .env file if it exists (populates os.environ)
    load_dotenv()

    # Validate file exists
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"Workflow file not found: {yaml_path}")

    # Load YAML
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    # Validate required sections
    required = ['source', 'destination', 'converter', 'flattener']
    for section in required:
        if section not in data:
            raise ValueError(f"Missing required section '{section}' in workflow file: {yaml_path}")

    # Parse workflow definition
    try:
        # Parse optional state section
        state_spec = None
        if 'state' in data:
            state_spec = StateSpec(
                file_path=data['state'].get('file_path', './.excel-differ-state.json')
            )

        # Parse optional logging section
        logging_spec = None
        if 'logging' in data:
            logging_spec = LoggingSpec(
                log_dir=data['logging'].get('log_dir', './logs')
            )

        workflow = WorkflowDefinition(
            source=SourceDestinationSpec(
                implementation=data['source']['implementation'],
                config=data['source'].get('config', {})
            ),
            destination=SourceDestinationSpec(
                implementation=data['destination']['implementation'],
                config=data['destination'].get('config', {})
            ),
            converter=ComponentSpec(
                implementation=data['converter']['implementation'],
                config=data['converter'].get('config', {})
            ),
            flattener=ComponentSpec(
                implementation=data['flattener']['implementation'],
                config=data['flattener'].get('config', {})
            ),
            state=state_spec,
            logging=logging_spec
        )
    except KeyError as e:
        raise ValueError(f"Invalid workflow structure in {yaml_path}: missing {e}")

    return workflow
