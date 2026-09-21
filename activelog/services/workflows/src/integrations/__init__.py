"""Integrations package for workflow automation service"""

from .integration_manager import IntegrationManager, BaseIntegration, AuthType, ServiceConfig

__all__ = ["IntegrationManager", "BaseIntegration", "AuthType", "ServiceConfig"]