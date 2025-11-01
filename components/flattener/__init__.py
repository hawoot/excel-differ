"""
Excel Differ - Flattener Component

Contains multiple flattener implementations:
- openpyxl: Production flattener using openpyxl library
- noop: NoOp flattener for converter-only workflows
- (future implementations)
"""

from .openpyxl_impl.src.flattener_plugin import OpenpyxlFlattener
from .noop import NoOpFlattener

__all__ = ['OpenpyxlFlattener', 'NoOpFlattener']
