"""
ActiveLog Plugin SDK for Python

A comprehensive SDK for building plugins for the ActiveLog platform.
"""

from .plugin import Plugin
from .types import (
    PluginContext,
    PluginManifest,
    TriggerEvent,
    TriggerResult,
    UserContext,
    OrganizationContext,
    PluginError,
    PermissionError,
    ResourceLimitError,
    ValidationError,
)
from .decorators import api_endpoint, trigger_handler, validate_params
from .utils import (
    validate_manifest,
    generate_plugin_template,
    parse_memory_size,
    format_bytes,
    is_valid_semver,
    compare_semver,
)

__version__ = "1.0.0"
__author__ = "ActiveLog Team"
__email__ = "sdk@activelog.ai"

__all__ = [
    # Core classes
    "Plugin",
    # Types
    "PluginContext",
    "PluginManifest", 
    "TriggerEvent",
    "TriggerResult",
    "UserContext",
    "OrganizationContext",
    # Exceptions
    "PluginError",
    "PermissionError", 
    "ResourceLimitError",
    "ValidationError",
    # Decorators
    "api_endpoint",
    "trigger_handler",
    "validate_params",
    # Utilities
    "validate_manifest",
    "generate_plugin_template",
    "parse_memory_size",
    "format_bytes",
    "is_valid_semver",
    "compare_semver",
    # Version info
    "__version__",
    "__author__",
    "__email__",
]