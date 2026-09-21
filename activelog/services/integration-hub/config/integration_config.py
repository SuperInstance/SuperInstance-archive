"""
Integration Hub Configuration
Configuration management for all third-party integrations
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class IntegrationConfig:
    """Configuration settings for integration services"""
    
    # Service configuration
    service_name: str = "ActiveLog Integration Hub"
    service_version: str = "1.0.0"
    port: int = 8348
    host: str = "0.0.0.0"
    debug: bool = False
    
    # Database configuration
    database_path: str = "/home/activeloguser/activelog/services/integration-hub/database/integrations.db"
    
    # Security configuration
    api_key_header: str = "X-ActiveLog-API-Key"
    webhook_secret_header: str = "X-Hub-Signature-256"
    
    # Rate limiting
    rate_limit_per_minute: int = 100
    rate_limit_per_hour: int = 1000
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: int = 5
    
    # Webhook configuration
    webhook_timeout_seconds: int = 30
    webhook_max_payload_size: int = 1048576  # 1MB
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        # Service configuration
        self.service_name = os.getenv('INTEGRATION_HUB_SERVICE_NAME', self.service_name)
        self.service_version = os.getenv('INTEGRATION_HUB_VERSION', self.service_version)
        self.port = int(os.getenv('INTEGRATION_HUB_PORT', str(self.port)))
        self.host = os.getenv('INTEGRATION_HUB_HOST', self.host)
        self.debug = os.getenv('INTEGRATION_HUB_DEBUG', 'False').lower() == 'true'
        
        # Database configuration
        self.database_path = os.getenv('INTEGRATION_HUB_DB_PATH', self.database_path)
        
        # Load integration-specific configurations
        self._load_integration_configs()
        
    def _load_integration_configs(self):
        """Load configuration for each integration"""
        # Zapier configuration
        self.zapier_api_key = os.getenv('ZAPIER_API_KEY')
        self.zapier_webhook_url = os.getenv('ZAPIER_WEBHOOK_URL')
        
        # IFTTT configuration
        self.ifttt_webhook_key = os.getenv('IFTTT_WEBHOOK_KEY')
        
        # Microsoft Power Automate configuration
        self.power_automate_client_id = os.getenv('POWER_AUTOMATE_CLIENT_ID')
        self.power_automate_client_secret = os.getenv('POWER_AUTOMATE_CLIENT_SECRET')
        self.power_automate_tenant_id = os.getenv('POWER_AUTOMATE_TENANT_ID')
        self.power_automate_environment_id = os.getenv('POWER_AUTOMATE_ENVIRONMENT_ID')
        
        # Google Workspace configuration
        self.google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.google_service_account_key = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY')
        self.google_workspace_domain = os.getenv('GOOGLE_WORKSPACE_DOMAIN')
        
        # Salesforce configuration
        self.salesforce_client_id = os.getenv('SALESFORCE_CLIENT_ID')
        self.salesforce_client_secret = os.getenv('SALESFORCE_CLIENT_SECRET')
        self.salesforce_username = os.getenv('SALESFORCE_USERNAME')
        self.salesforce_password = os.getenv('SALESFORCE_PASSWORD')
        self.salesforce_security_token = os.getenv('SALESFORCE_SECURITY_TOKEN')
        self.salesforce_instance_url = os.getenv('SALESFORCE_INSTANCE_URL', 'https://na1.salesforce.com')
        self.salesforce_sandbox = os.getenv('SALESFORCE_SANDBOX', 'False').lower() == 'true'
        
        # QuickBooks configuration
        self.quickbooks_client_id = os.getenv('QUICKBOOKS_CLIENT_ID')
        self.quickbooks_client_secret = os.getenv('QUICKBOOKS_CLIENT_SECRET')
        self.quickbooks_company_id = os.getenv('QUICKBOOKS_COMPANY_ID')
        self.quickbooks_access_token = os.getenv('QUICKBOOKS_ACCESS_TOKEN')
        self.quickbooks_refresh_token = os.getenv('QUICKBOOKS_REFRESH_TOKEN')
        self.quickbooks_sandbox = os.getenv('QUICKBOOKS_SANDBOX', 'True').lower() == 'true'
        
        # Shopify configuration
        self.shopify_shop_domain = os.getenv('SHOPIFY_SHOP_DOMAIN')
        self.shopify_access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        self.shopify_api_version = os.getenv('SHOPIFY_API_VERSION', '2023-10')
        self.shopify_webhook_secret = os.getenv('SHOPIFY_WEBHOOK_SECRET')
        
        # WordPress configuration
        self.wordpress_site_url = os.getenv('WORDPRESS_SITE_URL')
        self.wordpress_username = os.getenv('WORDPRESS_USERNAME')
        self.wordpress_password = os.getenv('WORDPRESS_PASSWORD')
        self.wordpress_app_password = os.getenv('WORDPRESS_APP_PASSWORD')
        self.wordpress_plugin_api_key = os.getenv('WORDPRESS_PLUGIN_API_KEY')
        
        # Discord configuration
        self.discord_bot_token = os.getenv('DISCORD_BOT_TOKEN')
        self.discord_application_id = os.getenv('DISCORD_APPLICATION_ID')
        self.discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.discord_command_prefix = os.getenv('DISCORD_COMMAND_PREFIX', '!')
        
        # Slack configuration
        self.slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
        self.slack_app_token = os.getenv('SLACK_APP_TOKEN')
        self.slack_signing_secret = os.getenv('SLACK_SIGNING_SECRET')
        self.slack_client_id = os.getenv('SLACK_CLIENT_ID')
        self.slack_client_secret = os.getenv('SLACK_CLIENT_SECRET')
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        
        # Microsoft Teams configuration
        self.teams_client_id = os.getenv('TEAMS_CLIENT_ID')
        self.teams_client_secret = os.getenv('TEAMS_CLIENT_SECRET')
        self.teams_tenant_id = os.getenv('TEAMS_TENANT_ID')
        self.teams_bot_id = os.getenv('TEAMS_BOT_ID')
        self.teams_bot_password = os.getenv('TEAMS_BOT_PASSWORD')
        self.teams_webhook_url = os.getenv('TEAMS_WEBHOOK_URL')
        
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get configuration value by key"""
        return getattr(self, key, default)
        
    def get_integration_config(self, integration_name: str) -> Dict[str, Any]:
        """Get configuration for specific integration"""
        configs = {
            'zapier': {
                'zapier_api_key': self.zapier_api_key,
                'zapier_webhook_url': self.zapier_webhook_url
            },
            'ifttt': {
                'ifttt_webhook_key': self.ifttt_webhook_key
            },
            'power_automate': {
                'power_automate_client_id': self.power_automate_client_id,
                'power_automate_client_secret': self.power_automate_client_secret,
                'power_automate_tenant_id': self.power_automate_tenant_id,
                'power_automate_environment_id': self.power_automate_environment_id
            },
            'google_workspace': {
                'google_client_id': self.google_client_id,
                'google_client_secret': self.google_client_secret,
                'google_service_account_key': self.google_service_account_key,
                'google_workspace_domain': self.google_workspace_domain
            },
            'salesforce': {
                'salesforce_client_id': self.salesforce_client_id,
                'salesforce_client_secret': self.salesforce_client_secret,
                'salesforce_username': self.salesforce_username,
                'salesforce_password': self.salesforce_password,
                'salesforce_security_token': self.salesforce_security_token,
                'salesforce_instance_url': self.salesforce_instance_url,
                'salesforce_sandbox': self.salesforce_sandbox
            },
            'quickbooks': {
                'quickbooks_client_id': self.quickbooks_client_id,
                'quickbooks_client_secret': self.quickbooks_client_secret,
                'quickbooks_company_id': self.quickbooks_company_id,
                'quickbooks_access_token': self.quickbooks_access_token,
                'quickbooks_refresh_token': self.quickbooks_refresh_token,
                'quickbooks_sandbox': self.quickbooks_sandbox
            },
            'shopify': {
                'shopify_shop_domain': self.shopify_shop_domain,
                'shopify_access_token': self.shopify_access_token,
                'shopify_api_version': self.shopify_api_version,
                'shopify_webhook_secret': self.shopify_webhook_secret
            },
            'wordpress': {
                'wordpress_site_url': self.wordpress_site_url,
                'wordpress_username': self.wordpress_username,
                'wordpress_password': self.wordpress_password,
                'wordpress_app_password': self.wordpress_app_password,
                'wordpress_plugin_api_key': self.wordpress_plugin_api_key
            },
            'discord': {
                'discord_bot_token': self.discord_bot_token,
                'discord_application_id': self.discord_application_id,
                'discord_webhook_url': self.discord_webhook_url,
                'discord_command_prefix': self.discord_command_prefix
            },
            'slack': {
                'slack_bot_token': self.slack_bot_token,
                'slack_app_token': self.slack_app_token,
                'slack_signing_secret': self.slack_signing_secret,
                'slack_client_id': self.slack_client_id,
                'slack_client_secret': self.slack_client_secret,
                'slack_webhook_url': self.slack_webhook_url
            },
            'teams': {
                'teams_client_id': self.teams_client_id,
                'teams_client_secret': self.teams_client_secret,
                'teams_tenant_id': self.teams_tenant_id,
                'teams_bot_id': self.teams_bot_id,
                'teams_bot_password': self.teams_bot_password,
                'teams_webhook_url': self.teams_webhook_url
            }
        }
        
        return configs.get(integration_name, {})
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        config_dict = {}
        
        # Service configuration
        config_dict.update({
            'service_name': self.service_name,
            'service_version': self.service_version,
            'port': self.port,
            'host': self.host,
            'debug': self.debug,
            'database_path': self.database_path,
            'api_key_header': self.api_key_header,
            'webhook_secret_header': self.webhook_secret_header,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'rate_limit_per_hour': self.rate_limit_per_hour,
            'max_retries': self.max_retries,
            'retry_delay_seconds': self.retry_delay_seconds,
            'webhook_timeout_seconds': self.webhook_timeout_seconds,
            'webhook_max_payload_size': self.webhook_max_payload_size
        })
        
        # Integration configurations (without sensitive data)
        config_dict['integrations'] = {
            'zapier': {
                'configured': bool(self.zapier_api_key),
                'webhook_configured': bool(self.zapier_webhook_url)
            },
            'ifttt': {
                'configured': bool(self.ifttt_webhook_key)
            },
            'power_automate': {
                'configured': bool(self.power_automate_client_id and self.power_automate_client_secret),
                'tenant_id': self.power_automate_tenant_id
            },
            'google_workspace': {
                'configured': bool(self.google_client_id and self.google_client_secret),
                'domain': self.google_workspace_domain
            },
            'salesforce': {
                'configured': bool(self.salesforce_client_id and self.salesforce_client_secret),
                'instance_url': self.salesforce_instance_url,
                'sandbox': self.salesforce_sandbox
            },
            'quickbooks': {
                'configured': bool(self.quickbooks_client_id and self.quickbooks_client_secret),
                'sandbox': self.quickbooks_sandbox
            },
            'shopify': {
                'configured': bool(self.shopify_shop_domain and self.shopify_access_token),
                'shop_domain': self.shopify_shop_domain,
                'api_version': self.shopify_api_version
            },
            'wordpress': {
                'configured': bool(self.wordpress_site_url),
                'site_url': self.wordpress_site_url,
                'plugin_configured': bool(self.wordpress_plugin_api_key)
            },
            'discord': {
                'configured': bool(self.discord_bot_token),
                'application_id': self.discord_application_id,
                'command_prefix': self.discord_command_prefix
            },
            'slack': {
                'configured': bool(self.slack_bot_token),
                'webhook_configured': bool(self.slack_webhook_url)
            },
            'teams': {
                'configured': bool(self.teams_client_id and self.teams_client_secret),
                'tenant_id': self.teams_tenant_id,
                'bot_configured': bool(self.teams_bot_id)
            }
        }
        
        return config_dict
        
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'IntegrationHubConfig':
        """Create configuration from dictionary"""
        config = cls()
        
        # Update service configuration
        for key, value in config_dict.items():
            if hasattr(config, key) and key != 'integrations':
                setattr(config, key, value)
                
        return config
        
    def validate(self) -> Dict[str, Any]:
        """Validate configuration settings"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate required service settings
        if not self.service_name:
            validation_results['errors'].append('Service name is required')
            validation_results['valid'] = False
            
        if not (1 <= self.port <= 65535):
            validation_results['errors'].append('Port must be between 1 and 65535')
            validation_results['valid'] = False
            
        if self.rate_limit_per_minute <= 0:
            validation_results['errors'].append('Rate limit per minute must be positive')
            validation_results['valid'] = False
            
        if self.max_retries < 0:
            validation_results['errors'].append('Max retries cannot be negative')
            validation_results['valid'] = False
            
        # Validate database path
        if not self.database_path:
            validation_results['errors'].append('Database path is required')
            validation_results['valid'] = False
            
        # Check integration configurations
        configured_integrations = 0
        
        if self.zapier_api_key:
            configured_integrations += 1
        else:
            validation_results['warnings'].append('Zapier integration not configured')
            
        if self.ifttt_webhook_key:
            configured_integrations += 1
        else:
            validation_results['warnings'].append('IFTTT integration not configured')
            
        if self.power_automate_client_id and self.power_automate_client_secret:
            configured_integrations += 1
        else:
            validation_results['warnings'].append('Power Automate integration not configured')
            
        if self.google_client_id and self.google_client_secret:
            configured_integrations += 1
        else:
            validation_results['warnings'].append('Google Workspace integration not configured')
            
        if self.salesforce_client_id and self.salesforce_client_secret:
            configured_integrations += 1
        else:
            validation_results['warnings'].append('Salesforce integration not configured')
            
        if self.quickbooks_client_id and self.quickbooks_client_secret:
            configured_integrations += 1
        else:
            validation_results['warnings'].append('QuickBooks integration not configured')
            
        if self.shopify_shop_domain and self.shopify_access_token:
            configured_integrations += 1
        else:
            validation_results['warnings'].append('Shopify integration not configured')
            
        if self.wordpress_site_url:
            configured_integrations += 1
        else:
            validation_results['warnings'].append('WordPress integration not configured')
            
        if self.discord_bot_token:
            configured_integrations += 1
        else:
            validation_results['warnings'].append('Discord integration not configured')
            
        if self.slack_bot_token:
            configured_integrations += 1
        else:
            validation_results['warnings'].append('Slack integration not configured')
            
        if self.teams_client_id and self.teams_client_secret:
            configured_integrations += 1
        else:
            validation_results['warnings'].append('Teams integration not configured')
            
        if configured_integrations == 0:
            validation_results['warnings'].append('No integrations are configured')
            
        validation_results['configured_integrations_count'] = configured_integrations
        validation_results['total_integrations_count'] = 11
        
        return validation_results


class IntegrationHubConfig(IntegrationConfig):
    """Main integration hub configuration class"""
    pass