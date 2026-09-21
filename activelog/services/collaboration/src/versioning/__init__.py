"""Version control system for documents package"""

from .version_manager import VersionManager
from .diff_engine import DiffEngine

__all__ = ["VersionManager", "DiffEngine"]