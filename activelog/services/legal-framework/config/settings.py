#!/usr/bin/env python3
"""
Configuration settings for Legal Framework
"""

import os
from typing import Dict, Any

class LegalFrameworkConfig:
    """Configuration management for legal framework"""
    
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.debug_mode = os.getenv('DEBUG', 'true').lower() == 'true'
        self.database_path = '/home/activeloguser/activelog/data/legal-framework/'
        self.templates_path = '/home/activeloguser/activelog/services/legal-framework/templates/'
        
        # API Keys and external services
        self.api_keys = {
            'encryption_key': os.getenv('LEGAL_ENCRYPTION_KEY', 'default-development-key-change-in-production'),
            'signing_key': os.getenv('LEGAL_SIGNING_KEY', 'default-signing-key'),
        }
        
        # Service configuration
        self.service_config = {
            'max_license_activations': 100,
            'default_license_duration_days': 365,
            'gdpr_response_deadline_days': 30,
            'partnership_review_period_days': 90
        }
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment == 'development'
    
    def get_database_url(self, service_name: str) -> str:
        """Get database URL for specific service"""
        return f"{self.database_path}{service_name}.db"
    
    def get_config(self, key: str, default=None):
        """Get configuration value"""
        return self.service_config.get(key, default)