"""
Excel Differ - Component Registry

WHAT THIS FILE DOES:
    Central registry that stores all available component implementations and
    creates instances of them on demand. Think of it as a factory that knows
    how to build any component type.

RELATIONSHIP TO OTHER FILES:
    - interfaces.py defines what components must implement
    - Component folders (source/*, destination/*, etc.) register implementations here
    - workflows/workflow_loader.py reads YAML, then uses this registry to create actual instances
    - Orchestrator uses this to instantiate the workflow

HOW IT WORKS:
    1. Component implementations register themselves:
       registry.register_source('bitbucket', BitbucketSource)

    2. Workflow loader creates config objects from YAML

    3. Registry creates actual instances:
       registry.create_source('bitbucket', config_dict)

EXAMPLE USAGE:
    # Registration (done by component implementations, usually in __init__.py)
    from components.component_registry import registry
    from components.source.bitbucket import BitbucketSource
    from components.source.local_folder import LocalFolderSource
    from components.destination.bitbucket import BitbucketDestination
    from components.destination.local_folder import LocalFolderDestination

    # Register all implementations
    registry.register_source('bitbucket', BitbucketSource)
    registry.register_source('local_folder', LocalFolderSource)
    registry.register_destination('bitbucket', BitbucketDestination)
    registry.register_destination('local_folder', LocalFolderDestination)

    # Later: Creating instances (done by orchestrator)
    config = {
        'url': 'https://bitbucket.org/workspace/repo',
        'token': 'abc123',
        'branch': 'main'
    }
    source = registry.create_source('bitbucket', config)

    # The registry validates the implementation exists
    # If 'bitbucket' wasn't registered, you get a clear error:
    # ValueError: Unknown source implementation 'bitbucket'.
    #             Available: ['local_folder']

GLOBAL INSTANCE:
    This file exports a singleton 'registry' instance that should be used
    throughout the application. Do not create new PluginRegistry instances.

    from components.component_registry import registry

WORKFLOW INTEGRATION:
    The typical flow is:
    1. Workflow YAML specifies implementation names:
       source:
         implementation: bitbucket
         config: {...}

    2. workflow_loader.py parses YAML into WorkflowDefinition dataclass

    3. Orchestrator uses registry to create actual component instances:
       source = registry.create_source(
           workflow.source.implementation,  # 'bitbucket'
           workflow.source.config           # {...}
       )

SEE ALSO:
    - interfaces.py - The interfaces that components must implement
    - workflows/workflow_loader.py - Uses this registry to instantiate components
    - components/source/__init__.py - Example of registration
    - components/destination/__init__.py - Example of registration
"""

from typing import Dict, Type
from .interfaces import (
    SourceInterface,
    DestinationInterface,
    ConverterInterface,
    FlattenerInterface
)


class PluginRegistry:
    """Central registry for all plugin implementations"""

    def __init__(self):
        self._sources: Dict[str, Type[SourceInterface]] = {}
        self._destinations: Dict[str, Type[DestinationInterface]] = {}
        self._converters: Dict[str, Type[ConverterInterface]] = {}
        self._flatteners: Dict[str, Type[FlattenerInterface]] = {}

    def register_source(self, name: str, source_class: Type[SourceInterface]):
        """Register a source implementation"""
        self._sources[name] = source_class

    def register_destination(self, name: str, dest_class: Type[DestinationInterface]):
        """Register a destination implementation"""
        self._destinations[name] = dest_class

    def register_converter(self, name: str, converter_class: Type[ConverterInterface]):
        """Register a converter implementation"""
        self._converters[name] = converter_class

    def register_flattener(self, name: str, flattener_class: Type[FlattenerInterface]):
        """Register a flattener implementation"""
        self._flatteners[name] = flattener_class

    def create_source(self, implementation: str, config: dict) -> SourceInterface:
        """Create source instance"""
        if implementation not in self._sources:
            raise ValueError(
                f"Unknown source implementation '{implementation}'. "
                f"Available: {list(self._sources.keys())}"
            )
        return self._sources[implementation](config)

    def create_destination(self, implementation: str, config: dict) -> DestinationInterface:
        """Create destination instance"""
        if implementation not in self._destinations:
            raise ValueError(
                f"Unknown destination implementation '{implementation}'. "
                f"Available: {list(self._destinations.keys())}"
            )
        return self._destinations[implementation](config)

    def create_converter(self, implementation: str, config: dict) -> ConverterInterface:
        """Create converter instance"""
        if implementation not in self._converters:
            raise ValueError(
                f"Unknown converter implementation '{implementation}'. "
                f"Available: {list(self._converters.keys())}"
            )
        return self._converters[implementation](config)

    def create_flattener(self, implementation: str, config: dict) -> FlattenerInterface:
        """Create flattener instance"""
        if implementation not in self._flatteners:
            raise ValueError(
                f"Unknown flattener implementation '{implementation}'. "
                f"Available: {list(self._flatteners.keys())}"
            )
        return self._flatteners[implementation](config)


# Global registry instance
registry = PluginRegistry()
