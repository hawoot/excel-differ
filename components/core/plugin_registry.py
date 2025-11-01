"""
Excel Differ - Plugin Registry

Central registry for all component implementations.
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
