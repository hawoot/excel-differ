"""
Orchestrator Factory - Centralized orchestrator creation

Provides a single place to build orchestrators from workflow config files.
"""

from pathlib import Path
from typing import Tuple

from src.workflows.loader import load_workflow
from src.workflows.schema import WorkflowDefinition
from src.registry import registry
from .orchestrator import Orchestrator


def create_orchestrator_from_config(config_file: Path) -> Tuple[Orchestrator, WorkflowDefinition]:
    """
    Create an orchestrator from a workflow config file.

    This is the centralized factory for building orchestrators. It handles:
    1. Loading the workflow definition from YAML
    2. Creating all component instances from the registry
    3. Building and returning the orchestrator

    The orchestrator gets its configuration (patterns, depth, etc.) directly
    from the source component - no need to pass config around.

    Args:
        config_file: Path to workflow YAML config file

    Returns:
        Tuple of (orchestrator, workflow_definition)

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If workflow is invalid or components can't be created

    Example:
        >>> orchestrator, workflow = create_orchestrator_from_config(
        ...     Path('workflow_definitions/default.yaml')
        ... )
        >>> result = orchestrator.run()
    """
    # Load workflow definition
    workflow = load_workflow(config_file)

    # Inject state file path into source and destination configs
    source_config = workflow.source.config.copy()
    source_config['state_file_path'] = workflow.state.file_path

    destination_config = workflow.destination.config.copy()
    destination_config['state_file_path'] = workflow.state.file_path

    # Create component instances from workflow definition
    source = registry.create_source(
        workflow.source.implementation,
        source_config
    )

    destination = registry.create_destination(
        workflow.destination.implementation,
        destination_config
    )

    converter = registry.create_converter(
        workflow.converter.implementation,
        workflow.converter.config
    )

    flattener = registry.create_flattener(
        workflow.flattener.implementation,
        workflow.flattener.config
    )

    # Create orchestrator
    # Note: Orchestrator gets patterns/depth directly from source component
    orchestrator = Orchestrator(
        source=source,
        destination=destination,
        converter=converter,
        flattener=flattener
    )

    return orchestrator, workflow
