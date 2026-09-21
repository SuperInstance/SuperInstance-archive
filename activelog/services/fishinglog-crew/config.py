"""
Configuration settings for FishingLog Crew Management Service
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    service_name: str = "fishinglog-crew"
    service_version: str = "1.0.0"
    port: int = Field(default=8375, env="PORT")
    host: str = Field(default="0.0.0.0", env="HOST")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Database configuration
    database_url: str = Field(
        default="sqlite:///./fishinglog_crew.db",
        env="DATABASE_URL"
    )
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Security settings
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # Email settings for invitations
    smtp_server: str = Field(default="localhost", env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    
    # Email templates
    from_email: str = Field(
        default="crew@fishinglog.com",
        env="FROM_EMAIL"
    )
    invitation_subject: str = "Crew Invitation - FishingLog"
    
    # CORS settings
    allowed_origins: List[str] = Field(
        default=["*"],
        env="ALLOWED_ORIGINS"
    )
    
    # Redis settings for real-time features
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    
    # External service URLs
    fishinglog_core_url: str = Field(
        default="http://localhost:8001",
        env="FISHINGLOG_CORE_URL"
    )
    auth_service_url: str = Field(
        default="http://localhost:8002",
        env="AUTH_SERVICE_URL"
    )
    navigation_service_url: str = Field(
        default="http://localhost:8003",
        env="NAVIGATION_SERVICE_URL"
    )
    
    # Alarm settings
    default_attention_interval_minutes: int = Field(
        default=5,
        env="DEFAULT_ATTENTION_INTERVAL_MINUTES"
    )
    max_escalation_level: str = Field(
        default="emergency",
        env="MAX_ESCALATION_LEVEL"
    )
    
    # Safety drill settings
    drill_photo_storage_path: str = Field(
        default="./drill_photos",
        env="DRILL_PHOTO_STORAGE_PATH"
    )
    drill_document_storage_path: str = Field(
        default="./drill_documents",
        env="DRILL_DOCUMENT_STORAGE_PATH"
    )
    
    # Share calculation settings
    default_crew_share_percentage: float = Field(
        default=50.0,
        env="DEFAULT_CREW_SHARE_PERCENTAGE"
    )
    default_captain_share_percentage: float = Field(
        default=20.0,
        env="DEFAULT_CAPTAIN_SHARE_PERCENTAGE"
    )
    default_vessel_share_percentage: float = Field(
        default=30.0,
        env="DEFAULT_VESSEL_SHARE_PERCENTAGE"
    )
    
    # Task management settings
    default_task_due_days: int = Field(
        default=7,
        env="DEFAULT_TASK_DUE_DAYS"
    )
    overdue_task_reminder_days: int = Field(
        default=1,
        env="OVERDUE_TASK_REMINDER_DAYS"
    )
    
    # Shift scheduling settings
    minimum_rest_hours: float = Field(
        default=10.0,
        env="MINIMUM_REST_HOURS"
    )
    maximum_shift_hours: float = Field(
        default=14.0,
        env="MAXIMUM_SHIFT_HOURS"
    )
    
    # WebSocket settings
    websocket_ping_interval: int = Field(
        default=30,
        env="WEBSOCKET_PING_INTERVAL"
    )
    websocket_timeout: int = Field(
        default=300,
        env="WEBSOCKET_TIMEOUT"
    )
    
    # Logging settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Monitoring settings
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # Feature flags
    enable_real_time_updates: bool = Field(
        default=True,
        env="ENABLE_REAL_TIME_UPDATES"
    )
    enable_email_notifications: bool = Field(
        default=True,
        env="ENABLE_EMAIL_NOTIFICATIONS"
    )
    enable_sms_notifications: bool = Field(
        default=False,
        env="ENABLE_SMS_NOTIFICATIONS"
    )
    enable_push_notifications: bool = Field(
        default=False,
        env="ENABLE_PUSH_NOTIFICATIONS"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings