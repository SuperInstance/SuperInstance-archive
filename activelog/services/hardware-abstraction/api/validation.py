"""
API Validation Utilities
"""

from api.models import ConfigValidationResult, SystemConfigUpdate

async def validate_config_update(config_update: SystemConfigUpdate) -> ConfigValidationResult:
    """Validate system configuration update"""
    errors = []
    warnings = []
    
    # Validate discovery config
    if config_update.discovery:
        if config_update.discovery.scan_interval < 10:
            errors.append("Discovery scan interval must be at least 10 seconds")
        if config_update.discovery.timeout > 300:
            warnings.append("Discovery timeout > 300s may cause performance issues")
    
    # Validate communication config
    if config_update.communication:
        if config_update.communication.max_connections > 10000:
            warnings.append("High max_connections may impact performance")
        if config_update.communication.connection_timeout < 5:
            errors.append("Connection timeout must be at least 5 seconds")
    
    # Validate monitoring config
    if config_update.monitoring:
        if config_update.monitoring.health_check_interval < 1:
            errors.append("Health check interval must be at least 1 second")
        if config_update.monitoring.metrics_retention_days > 365:
            warnings.append("Long retention period may consume excessive storage")
    
    return ConfigValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

async def get_security_config():
    """Get security configuration"""
    return {
        "authentication_enabled": True,
        "jwt_expiry_minutes": 30,
        "api_key_support": True,
        "role_based_access": True,
        "encryption_enabled": True
    }