#!/usr/bin/env python3
"""
Configuration settings for ActiveLog Membership Migration Service
"""

import os
from typing import Dict, Any


class MembershipMigrationConfig:
    """Configuration management for membership migration service"""
    
    def __init__(self):
        self.service_port = int(os.getenv('MEMBERSHIP_MIGRATION_PORT', 8336))
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        # Service configuration
        self.service_config = {
            'name': 'ActiveLog Membership Migration',
            'version': '1.0.0',
            'description': 'Comprehensive membership migration with cross-frontend transfers, billing consolidation, and advanced discount systems',
            'port': self.service_port,
            'host': '0.0.0.0',
            'debug': self.environment == 'development'
        }
        
        # Database configuration
        self.database_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'activelog_migration'),
            'username': os.getenv('DB_USERNAME', 'activelog'),
            'password': os.getenv('DB_PASSWORD', 'password'),
            'pool_size': int(os.getenv('DB_POOL_SIZE', 10)),
            'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', 20))
        }
        
        # Cross-frontend transfer configuration
        self.transfer_config = {
            'max_concurrent_transfers': int(os.getenv('MAX_CONCURRENT_TRANSFERS', 5)),
            'transfer_timeout_minutes': int(os.getenv('TRANSFER_TIMEOUT_MINUTES', 30)),
            'retry_attempts': int(os.getenv('TRANSFER_RETRY_ATTEMPTS', 3)),
            'validation_enabled': os.getenv('TRANSFER_VALIDATION_ENABLED', 'true').lower() == 'true',
            'backup_enabled': os.getenv('TRANSFER_BACKUP_ENABLED', 'true').lower() == 'true'
        }
        
        # Credit preservation configuration
        self.credits_config = {
            'preservation_enabled': True,
            'minimum_credit_threshold': float(os.getenv('MIN_CREDIT_THRESHOLD', 1.0)),
            'max_preservation_attempts': int(os.getenv('MAX_PRESERVATION_ATTEMPTS', 3)),
            'conversion_accuracy_threshold': float(os.getenv('CONVERSION_ACCURACY_THRESHOLD', 0.95)),
            'auto_top_up_enabled': os.getenv('AUTO_TOP_UP_ENABLED', 'true').lower() == 'true'
        }
        
        # Data migration configuration
        self.migration_config = {
            'chunk_size': int(os.getenv('MIGRATION_CHUNK_SIZE', 1000)),
            'parallel_workers': int(os.getenv('MIGRATION_PARALLEL_WORKERS', 3)),
            'integrity_validation': os.getenv('MIGRATION_INTEGRITY_VALIDATION', 'true').lower() == 'true',
            'data_anonymization': os.getenv('MIGRATION_DATA_ANONYMIZATION', 'false').lower() == 'true',
            'retention_period_days': int(os.getenv('MIGRATION_RETENTION_DAYS', 90))
        }
        
        # Subscription consolidation configuration
        self.billing_config = {
            'consolidation_enabled': True,
            'proration_enabled': os.getenv('PRORATION_ENABLED', 'true').lower() == 'true',
            'billing_cycle_alignment': os.getenv('BILLING_CYCLE_ALIGNMENT', 'true').lower() == 'true',
            'discount_stacking_enabled': os.getenv('DISCOUNT_STACKING_ENABLED', 'false').lower() == 'true',
            'payment_processor': os.getenv('PAYMENT_PROCESSOR', 'stripe'),
            'webhook_secret': os.getenv('WEBHOOK_SECRET', 'webhook_secret_key')
        }
        
        # Family plan configuration
        self.family_config = {
            'max_family_members': int(os.getenv('MAX_FAMILY_MEMBERS', 6)),
            'family_discount_percentage': float(os.getenv('FAMILY_DISCOUNT_PERCENTAGE', 20.0)),
            'organizer_privileges': os.getenv('ORGANIZER_PRIVILEGES', 'true').lower() == 'true',
            'child_account_restrictions': os.getenv('CHILD_ACCOUNT_RESTRICTIONS', 'true').lower() == 'true'
        }
        
        # Discount configuration
        self.discount_config = {
            'student_discount_percentage': float(os.getenv('STUDENT_DISCOUNT_PERCENTAGE', 50.0)),
            'senior_discount_percentage': float(os.getenv('SENIOR_DISCOUNT_PERCENTAGE', 30.0)),
            'verification_required': os.getenv('DISCOUNT_VERIFICATION_REQUIRED', 'true').lower() == 'true',
            'verification_expiry_months': int(os.getenv('VERIFICATION_EXPIRY_MONTHS', 12)),
            'stackable_discounts': os.getenv('STACKABLE_DISCOUNTS', 'false').lower() == 'true'
        }
        
        # Bulk transfer configuration
        self.bulk_config = {
            'max_bulk_size': int(os.getenv('MAX_BULK_SIZE', 1000)),
            'batch_processing_size': int(os.getenv('BATCH_PROCESSING_SIZE', 100)),
            'corporate_verification_required': os.getenv('CORPORATE_VERIFICATION_REQUIRED', 'true').lower() == 'true',
            'bulk_discount_threshold': int(os.getenv('BULK_DISCOUNT_THRESHOLD', 50)),
            'bulk_discount_percentage': float(os.getenv('BULK_DISCOUNT_PERCENTAGE', 15.0))
        }
        
        # Security configuration
        self.security_config = {
            'encryption_key': os.getenv('ENCRYPTION_KEY', 'default_encryption_key'),
            'jwt_secret': os.getenv('JWT_SECRET', 'jwt_secret_key'),
            'api_key_required': self.environment == 'production',
            'rate_limiting_enabled': True,
            'max_requests_per_minute': int(os.getenv('MAX_REQUESTS_PER_MINUTE', 100)),
            'cors_enabled': True,
            'allowed_origins': os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,https://activelog.com').split(',')
        }
        
        # Notification configuration
        self.notification_config = {
            'email_enabled': os.getenv('EMAIL_ENABLED', 'true').lower() == 'true',
            'sms_enabled': os.getenv('SMS_ENABLED', 'false').lower() == 'true',
            'push_enabled': os.getenv('PUSH_ENABLED', 'true').lower() == 'true',
            'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'smtp_username': os.getenv('SMTP_USERNAME', ''),
            'smtp_password': os.getenv('SMTP_PASSWORD', ''),
            'from_email': os.getenv('FROM_EMAIL', 'noreply@activelog.com')
        }
        
        # Logging configuration
        self.logging_config = {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': f'/home/activeloguser/activelog/logs/membership-migration.log',
            'max_file_size_mb': int(os.getenv('LOG_MAX_FILE_SIZE_MB', 100)),
            'backup_count': int(os.getenv('LOG_BACKUP_COUNT', 5)),
            'structured_logging': os.getenv('STRUCTURED_LOGGING', 'false').lower() == 'true'
        }
        
        # Monitoring configuration
        self.monitoring_config = {
            'metrics_enabled': True,
            'metrics_port': int(os.getenv('METRICS_PORT', 9336)),
            'health_check_enabled': True,
            'performance_tracking': True,
            'alerts_enabled': self.environment == 'production',
            'prometheus_enabled': os.getenv('PROMETHEUS_ENABLED', 'true').lower() == 'true'
        }
        
        # Integration configuration
        self.integration_config = {
            'stripe_secret_key': os.getenv('STRIPE_SECRET_KEY', ''),
            'stripe_webhook_secret': os.getenv('STRIPE_WEBHOOK_SECRET', ''),
            'sendgrid_api_key': os.getenv('SENDGRID_API_KEY', ''),
            'twilio_account_sid': os.getenv('TWILIO_ACCOUNT_SID', ''),
            'twilio_auth_token': os.getenv('TWILIO_AUTH_TOKEN', ''),
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID', ''),
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', ''),
            'aws_region': os.getenv('AWS_REGION', 'us-west-2')
        }
        
        # App endpoints configuration
        self.app_endpoints = {
            'activelog-core': {
                'base_url': os.getenv('ACTIVELOG_CORE_URL', 'http://localhost:8300'),
                'api_version': 'v1',
                'auth_header': 'Authorization',
                'timeout_seconds': 30
            },
            'studylog': {
                'base_url': os.getenv('STUDYLOG_URL', 'http://localhost:8301'),
                'api_version': 'v1',
                'auth_header': 'Authorization',
                'timeout_seconds': 30
            },
            'businesslog': {
                'base_url': os.getenv('BUSINESSLOG_URL', 'http://localhost:8302'),
                'api_version': 'v1',
                'auth_header': 'Authorization',
                'timeout_seconds': 30
            },
            'makerlog': {
                'base_url': os.getenv('MAKERLOG_URL', 'http://localhost:8303'),
                'api_version': 'v1',
                'auth_header': 'Authorization',
                'timeout_seconds': 30
            },
            'dmlog': {
                'base_url': os.getenv('DMLOG_URL', 'http://localhost:8304'),
                'api_version': 'v1',
                'auth_header': 'Authorization',
                'timeout_seconds': 30
            }
        }

    def get_config(self, section: str) -> Dict[str, Any]:
        """Get configuration for a specific section"""
        return getattr(self, f'{section}_config', {})
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration sections"""
        return {
            'service': self.service_config,
            'database': self.database_config,
            'transfer': self.transfer_config,
            'credits': self.credits_config,
            'migration': self.migration_config,
            'billing': self.billing_config,
            'family': self.family_config,
            'discount': self.discount_config,
            'bulk': self.bulk_config,
            'security': self.security_config,
            'notification': self.notification_config,
            'logging': self.logging_config,
            'monitoring': self.monitoring_config,
            'integration': self.integration_config,
            'app_endpoints': self.app_endpoints
        }
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == 'development'
    
    def get_app_endpoint(self, app_id: str) -> str:
        """Get full API endpoint for an app"""
        if app_id not in self.app_endpoints:
            raise ValueError(f"Unknown app ID: {app_id}")
        
        config = self.app_endpoints[app_id]
        return f"{config['base_url']}/api/{config['api_version']}"
    
    def get_database_url(self) -> str:
        """Get database connection URL"""
        db_config = self.database_config
        return (f"postgresql://{db_config['username']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['database']}")