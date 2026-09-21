"""Core package for workflow automation service"""

from .config import settings
from .database import db_manager, init_db, close_db

__all__ = ["settings", "db_manager", "init_db", "close_db"]