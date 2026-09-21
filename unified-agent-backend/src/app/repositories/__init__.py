"""
Repository layer for data access operations.

Provides a clean abstraction over database operations using the repository pattern.
"""

from .base import BaseRepository
from .agent_repository import AgentRepository

__all__ = [
    "BaseRepository",
    "AgentRepository",
]