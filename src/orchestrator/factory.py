"""
Orchestrator Factory - Centralized orchestrator creation

Provides a single place to build orchestrators from workflow config files.
"""

from pathlib import Path
from typing import Tuple

from src.workflows.loader import load_workflow
from src.workflows.schema import WorkflowDefinition
from src.registry import registry
from src.utils.state_manager import StateManager
from .orchestrator import Orchestrator


def create_orchestrator_from_config(config_file: Path) -> Tuple[Orchestrator, WorkflowDefinition]:
    """
    Create an orchestrator from a workflow config file.

    This is the centralized factory for building orchestrators. It handles:
    1. Loading the workflow definition from YAML
    2. Creating StateManager instance
    3. Creating all component instances from the registry
    4. Building and returning the orchestrator with StateManager

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

    # Create StateManager (centralized state management)
    state_manager = StateManager(workflow.state.file_path)

    # Create component instances from workflow definition
    # Note: No state_file_path injection - StateManager handles all state
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

    # Create orchestrator with StateManager
    orchestrator = Orchestrator(
        source=source,
        destination=destination,
        converter=converter,
        flattener=flattener,
        state_manager=state_manager
    )

    return orchestrator, workflow
