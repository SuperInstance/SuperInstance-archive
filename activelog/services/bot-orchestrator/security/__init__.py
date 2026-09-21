"""
Security module for bot orchestration system.

Provides authentication, authorization, and encryption capabilities for
secure multi-bot coordination and Claude API integration.
"""

from .authentication import AuthenticationManager, UserRole, Permission
from .encryption import DataEncryptionService as EncryptionService

__all__ = [
    "AuthenticationManager",
    "EncryptionService", 
    "UserRole",
    "Permission"
]