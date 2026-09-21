"""
Configuration for ActiveLog Authentication Service
"""

import os
from typing import Optional

class AuthConfig:
    """Authentication service configuration"""
    
    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', 'your-super-secret-jwt-key-here')
    JWT_ALGORITHM: str = os.getenv('JWT_ALGORITHM', 'HS256')
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '1440'))  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '7'))  # 7 days
    
    # Database Configuration
    DATABASE_PATH: str = os.getenv('AUTH_DATABASE_PATH', 'auth_data.db')
    
    # Rate Limiting
    RATE_LIMIT_WINDOW: int = int(os.getenv('RATE_LIMIT_WINDOW', '3600'))  # 1 hour
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))
    MAX_REGISTRATION_ATTEMPTS: int = int(os.getenv('MAX_REGISTRATION_ATTEMPTS', '3'))
    
    # Security
    ACCOUNT_LOCKOUT_DURATION: int = int(os.getenv('ACCOUNT_LOCKOUT_DURATION', '3600'))  # 1 hour
    PASSWORD_MIN_LENGTH: int = int(os.getenv('PASSWORD_MIN_LENGTH', '8'))
    REQUIRE_EMAIL_VERIFICATION: bool = os.getenv('REQUIRE_EMAIL_VERIFICATION', 'false').lower() == 'true'
    
    # Service Configuration
    SERVICE_NAME: str = os.getenv('SERVICE_NAME', 'auth-service')
    SERVICE_PORT: int = int(os.getenv('PORT', '8080'))
    SERVICE_HOST: str = os.getenv('HOST', '0.0.0.0')
    
    # CORS Configuration
    CORS_ORIGINS: list = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'auth_service.log')
    
    # External Services
    EMAIL_SERVICE_URL: Optional[str] = os.getenv('EMAIL_SERVICE_URL')
    NOTIFICATION_SERVICE_URL: Optional[str] = os.getenv('NOTIFICATION_SERVICE_URL')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        required_vars = ['JWT_SECRET_KEY']
        
        for var in required_vars:
            if not getattr(cls, var):
                print(f"Error: {var} is required but not set")
                return False
        
        return True

# Create global config instance
config = AuthConfig()

# Validation
if not config.validate():
    raise RuntimeError("Invalid configuration. Please check environment variables.")