"""
Instance Manager Configuration
Configuration management for the instance manager service
"""

import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class InstanceManagerConfig:
    """Configuration settings for the Instance Manager"""
    
    # AWS Configuration
    aws_region: str = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
    aws_access_key_id: str = os.getenv('AWS_ACCESS_KEY_ID', '')
    aws_secret_access_key: str = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    
    # Service Configuration
    service_port: int = int(os.getenv('INSTANCE_MANAGER_PORT', '8330'))
    service_host: str = os.getenv('INSTANCE_MANAGER_HOST', '0.0.0.0')
    debug_mode: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Database Configuration
    data_directory: str = os.getenv('DATA_DIRECTORY', '/home/activeloguser/activelog/data/instance-manager')
    
    # Scaling Configuration
    auto_scaling_enabled: bool = True
    scaling_check_interval_minutes: int = 5
    scaling_cooldown_minutes: int = 15
    max_scale_up_per_hour: int = 3
    max_scale_down_per_hour: int = 2
    
    # Scheduling Configuration
    schedule_check_interval_minutes: int = 1
    schedule_execution_timeout_minutes: int = 30
    
    # Cost Configuration
    cost_alert_threshold_usd: float = 1000.0
    cost_check_interval_hours: int = 1
    currency: str = 'USD'
    
    # Notification Configuration
    smtp_host: str = os.getenv('SMTP_HOST', '')
    smtp_port: int = int(os.getenv('SMTP_PORT', '587'))
    smtp_username: str = os.getenv('SMTP_USERNAME', '')
    smtp_password: str = os.getenv('SMTP_PASSWORD', '')
    notification_from_email: str = os.getenv('NOTIFICATION_FROM_EMAIL', 'noreply@activelog.com')
    
    # Multi-cloud Configuration
    enable_multi_cloud: bool = False
    azure_subscription_id: str = os.getenv('AZURE_SUBSCRIPTION_ID', '')
    azure_resource_group: str = os.getenv('AZURE_RESOURCE_GROUP', '')
    gcp_project_id: str = os.getenv('GCP_PROJECT_ID', '')
    gcp_zone: str = os.getenv('GCP_ZONE', 'us-central1-a')
    
    # Backup Configuration
    backup_enabled: bool = True
    backup_retention_days: int = 30
    backup_check_interval_hours: int = 24
    
    # Security Configuration
    api_key_required: bool = True
    allowed_ips: List[str] = None
    rate_limit_requests_per_minute: int = 100
    
    # Logging Configuration
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: str = '/home/activeloguser/activelog/logs/instance-manager.log'
    log_max_size_mb: int = 100
    log_backup_count: int = 5
    
    def __post_init__(self):
        if self.allowed_ips is None:
            self.allowed_ips = []
        
        # Ensure data directory exists
        os.makedirs(self.data_directory, exist_ok=True)
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
    
    @classmethod
    def from_file(cls, config_path: str) -> 'InstanceManagerConfig':
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            return cls(**config_data)
        except FileNotFoundError:
            print(f"Config file {config_path} not found, using defaults")
            return cls()
        except Exception as e:
            print(f"Error loading config file {config_path}: {e}")
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'aws_region': self.aws_region,
            'service_port': self.service_port,
            'service_host': self.service_host,
            'debug_mode': self.debug_mode,
            'data_directory': self.data_directory,
            'auto_scaling_enabled': self.auto_scaling_enabled,
            'scaling_check_interval_minutes': self.scaling_check_interval_minutes,
            'scaling_cooldown_minutes': self.scaling_cooldown_minutes,
            'max_scale_up_per_hour': self.max_scale_up_per_hour,
            'max_scale_down_per_hour': self.max_scale_down_per_hour,
            'schedule_check_interval_minutes': self.schedule_check_interval_minutes,
            'schedule_execution_timeout_minutes': self.schedule_execution_timeout_minutes,
            'cost_alert_threshold_usd': self.cost_alert_threshold_usd,
            'cost_check_interval_hours': self.cost_check_interval_hours,
            'currency': self.currency,
            'smtp_host': self.smtp_host,
            'smtp_port': self.smtp_port,
            'notification_from_email': self.notification_from_email,
            'enable_multi_cloud': self.enable_multi_cloud,
            'azure_resource_group': self.azure_resource_group,
            'gcp_project_id': self.gcp_project_id,
            'gcp_zone': self.gcp_zone,
            'backup_enabled': self.backup_enabled,
            'backup_retention_days': self.backup_retention_days,
            'backup_check_interval_hours': self.backup_check_interval_hours,
            'api_key_required': self.api_key_required,
            'allowed_ips': self.allowed_ips,
            'rate_limit_requests_per_minute': self.rate_limit_requests_per_minute,
            'log_level': self.log_level,
            'log_file': self.log_file,
            'log_max_size_mb': self.log_max_size_mb,
            'log_backup_count': self.log_backup_count
        }
    
    def save_to_file(self, config_path: str):
        """Save configuration to JSON file"""
        try:
            config_data = self.to_dict()
            
            # Remove sensitive data before saving
            sensitive_fields = ['aws_access_key_id', 'aws_secret_access_key', 
                              'smtp_password', 'azure_subscription_id']
            for field in sensitive_fields:
                config_data.pop(field, None)
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving config to {config_path}: {e}")
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # AWS Configuration
        if not self.aws_region:
            errors.append("AWS region is required")
        
        # Service Configuration
        if not (1 <= self.service_port <= 65535):
            errors.append("Service port must be between 1 and 65535")
        
        # Scaling Configuration
        if self.scaling_check_interval_minutes < 1:
            errors.append("Scaling check interval must be at least 1 minute")
        
        if self.scaling_cooldown_minutes < 1:
            errors.append("Scaling cooldown must be at least 1 minute")
        
        # Cost Configuration
        if self.cost_alert_threshold_usd <= 0:
            errors.append("Cost alert threshold must be positive")
        
        # Multi-cloud Configuration
        if self.enable_multi_cloud:
            if not self.azure_subscription_id and not self.gcp_project_id:
                errors.append("At least one cloud provider must be configured for multi-cloud")
        
        # Notification Configuration
        if self.smtp_host and not self.smtp_username:
            errors.append("SMTP username is required when SMTP host is configured")
        
        return errors

class EnvironmentConfig:
    """Environment-specific configuration profiles"""
    
    @staticmethod
    def development() -> InstanceManagerConfig:
        """Development environment configuration"""
        config = InstanceManagerConfig()
        config.debug_mode = True
        config.auto_scaling_enabled = False  # Disable auto-scaling in dev
        config.cost_alert_threshold_usd = 100.0  # Lower threshold for dev
        config.log_level = 'DEBUG'
        return config
    
    @staticmethod
    def staging() -> InstanceManagerConfig:
        """Staging environment configuration"""
        config = InstanceManagerConfig()
        config.debug_mode = False
        config.auto_scaling_enabled = True
        config.cost_alert_threshold_usd = 500.0
        config.log_level = 'INFO'
        return config
    
    @staticmethod
    def production() -> InstanceManagerConfig:
        """Production environment configuration"""
        config = InstanceManagerConfig()
        config.debug_mode = False
        config.auto_scaling_enabled = True
        config.cost_alert_threshold_usd = 2000.0
        config.log_level = 'WARNING'
        config.api_key_required = True
        config.rate_limit_requests_per_minute = 1000
        return config

class ConfigurationManager:
    """Manages configuration loading and environment-specific settings"""
    
    def __init__(self):
        self.config: Optional[InstanceManagerConfig] = None
        self.environment = os.getenv('ENVIRONMENT', 'development').lower()
    
    def load_config(self, config_path: str = None) -> InstanceManagerConfig:
        """Load configuration from file or environment"""
        
        # Try to load from file first
        if config_path and os.path.exists(config_path):
            self.config = InstanceManagerConfig.from_file(config_path)
        else:
            # Load environment-specific defaults
            if self.environment == 'production':
                self.config = EnvironmentConfig.production()
            elif self.environment == 'staging':
                self.config = EnvironmentConfig.staging()
            else:
                self.config = EnvironmentConfig.development()
        
        # Override with environment variables
        self._apply_environment_overrides()
        
        # Validate configuration
        errors = self.config.validate()
        if errors:
            print(f"Configuration errors: {errors}")
            # In production, might want to exit here
        
        return self.config
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides"""
        if not self.config:
            return
        
        # AWS overrides
        if os.getenv('AWS_REGION'):
            self.config.aws_region = os.getenv('AWS_REGION')
        
        # Service overrides
        if os.getenv('SERVICE_PORT'):
            self.config.service_port = int(os.getenv('SERVICE_PORT'))
        
        if os.getenv('DEBUG'):
            self.config.debug_mode = os.getenv('DEBUG').lower() == 'true'
        
        # Scaling overrides
        if os.getenv('AUTO_SCALING_ENABLED'):
            self.config.auto_scaling_enabled = os.getenv('AUTO_SCALING_ENABLED').lower() == 'true'
        
        # Cost overrides
        if os.getenv('COST_ALERT_THRESHOLD'):
            self.config.cost_alert_threshold_usd = float(os.getenv('COST_ALERT_THRESHOLD'))
    
    def get_config(self) -> InstanceManagerConfig:
        """Get current configuration"""
        if not self.config:
            self.load_config()
        return self.config
    
    def reload_config(self, config_path: str = None):
        """Reload configuration"""
        self.load_config(config_path)

# Global configuration manager instance
config_manager = ConfigurationManager()