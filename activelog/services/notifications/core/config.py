"""
Configuration settings for ActiveLog Notification Service
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "activelog-notifications"
    PORT: int = 8006
    DEBUG: bool = False
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://activelog:password@localhost:5432/activelog"
    
    # Redis Configuration (for queues and caching)
    REDIS_URL: str = "redis://localhost:6379/2"
    
    # Email Configuration (SMTP)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    
    # SendGrid Configuration
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: str = "noreply@activelog.com"
    SENDGRID_FROM_NAME: str = "ActiveLog"
    
    # AWS SES Configuration
    AWS_SES_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SES_FROM_EMAIL: str = "noreply@activelog.com"
    
    # Email Provider Priority
    EMAIL_PROVIDER: str = "smtp"  # smtp, sendgrid, aws_ses
    EMAIL_FALLBACK_PROVIDERS: List[str] = ["smtp"]
    
    # Email Settings
    DEFAULT_FROM_EMAIL: str = "noreply@activelog.com"
    DEFAULT_FROM_NAME: str = "ActiveLog"
    EMAIL_RATE_LIMIT: int = 100  # emails per minute
    EMAIL_RETRY_ATTEMPTS: int = 3
    EMAIL_RETRY_DELAY: int = 300  # seconds
    
    # SMS Configuration (Twilio)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_PHONE: Optional[str] = None
    SMS_RATE_LIMIT: int = 10  # SMS per minute
    SMS_RETRY_ATTEMPTS: int = 2
    
    # Webhook Configuration
    WEBHOOK_TIMEOUT: int = 30  # seconds
    WEBHOOK_RETRY_ATTEMPTS: int = 5
    WEBHOOK_RETRY_DELAY: int = 60  # seconds
    WEBHOOK_MAX_PAYLOAD_SIZE: int = 1024 * 1024  # 1MB
    
    # In-App Notifications
    INAPP_RETENTION_DAYS: int = 30
    INAPP_MAX_NOTIFICATIONS: int = 1000  # per user
    
    # Digest Settings
    DIGEST_ENABLED: bool = True
    DIGEST_BATCH_SIZE: int = 50
    DIGEST_SCHEDULE_TIMES: List[str] = ["08:00", "18:00"]  # UTC times
    DIGEST_TIMEZONE: str = "UTC"
    
    # Template Settings
    TEMPLATE_CACHE_TTL: int = 3600  # seconds
    CUSTOM_TEMPLATE_LIMIT: int = 100  # per tenant
    
    # Notification Preferences
    DEFAULT_EMAIL_ENABLED: bool = True
    DEFAULT_INAPP_ENABLED: bool = True
    DEFAULT_SMS_ENABLED: bool = False
    DEFAULT_WEBHOOK_ENABLED: bool = False
    
    # Rate Limiting
    GLOBAL_RATE_LIMIT: int = 1000  # notifications per minute
    USER_RATE_LIMIT: int = 50  # notifications per user per hour
    
    # Security
    ALLOWED_ORIGINS: List[str] = ["*"]
    SECRET_KEY: str = "your-secret-key-here"
    WEBHOOK_SECRET_KEY: str = "webhook-secret-key"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    # External Service URLs
    ACTIVELOG_API_URL: str = "http://localhost:8000"
    SYNC_ENGINE_URL: str = "http://localhost:8003"
    ANALYTICS_URL: str = "http://localhost:8005"
    
    # Notification Types
    NOTIFICATION_TYPES: Dict[str, str] = {
        "file_uploaded": "File Upload",
        "file_processed": "File Processing",
        "sync_conflict": "Sync Conflict",
        "sync_complete": "Sync Complete",
        "ai_analysis_complete": "AI Analysis Complete",
        "batch_import_complete": "Batch Import Complete",
        "quota_warning": "Quota Warning",
        "quota_exceeded": "Quota Exceeded",
        "security_alert": "Security Alert",
        "system_maintenance": "System Maintenance",
        "welcome": "Welcome",
        "password_reset": "Password Reset",
        "email_verification": "Email Verification"
    }
    
    # Priority Levels
    PRIORITY_LEVELS: Dict[str, int] = {
        "low": 1,
        "normal": 2,
        "high": 3,
        "urgent": 4,
        "critical": 5
    }
    
    # Performance Settings
    ASYNC_POOL_SIZE: int = 20
    BATCH_NOTIFICATION_SIZE: int = 100
    QUEUE_TIMEOUT: int = 300  # seconds
    
    # File Upload Settings
    MAX_ATTACHMENT_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_ATTACHMENT_TYPES: List[str] = [".pdf", ".doc", ".docx", ".txt", ".csv"]
    
    @field_validator('EMAIL_PROVIDER')
    @classmethod
    def validate_email_provider(cls, v):
        """Validate email provider"""
        allowed_providers = ["smtp", "sendgrid", "aws_ses"]
        if v not in allowed_providers:
            raise ValueError(f"Email provider must be one of: {allowed_providers}")
        return v
    
    @field_validator('DIGEST_SCHEDULE_TIMES')
    @classmethod
    def validate_digest_times(cls, v):
        """Validate digest schedule times format"""
        for time_str in v:
            try:
                hour, minute = time_str.split(":")
                if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
                    raise ValueError(f"Invalid time format: {time_str}")
            except ValueError:
                raise ValueError(f"Invalid time format: {time_str}. Use HH:MM format")
        return v
    
    @property
    def email_configured(self) -> bool:
        """Check if email is configured"""
        if self.EMAIL_PROVIDER == "smtp":
            return bool(self.SMTP_HOST and self.SMTP_USERNAME and self.SMTP_PASSWORD)
        elif self.EMAIL_PROVIDER == "sendgrid":
            return bool(self.SENDGRID_API_KEY)
        elif self.EMAIL_PROVIDER == "aws_ses":
            return bool(self.AWS_ACCESS_KEY_ID and self.AWS_SECRET_ACCESS_KEY)
        return False
    
    @property
    def sms_configured(self) -> bool:
        """Check if SMS is configured"""
        return bool(self.TWILIO_ACCOUNT_SID and self.TWILIO_AUTH_TOKEN and self.TWILIO_FROM_PHONE)
    
    model_config = {
        "env_file": ".env",
        "env_prefix": "NOTIFICATIONS_"
    }

# Create settings instance
settings = Settings()