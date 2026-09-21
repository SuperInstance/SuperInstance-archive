"""
Adaptive Component System
Interface generation and compute distribution based on hardware capabilities
"""

from .interface_generator import InterfaceGenerator, ComponentComplexity
from .compute_distributor import ComputeDistributor, TaskComplexity, ExecutionContext

__all__ = [
    'InterfaceGenerator',
    'ComponentComplexity', 
    'ComputeDistributor',
    'TaskComplexity',
    'ExecutionContext'
]