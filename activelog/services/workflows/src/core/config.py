"""
Workflow service configuration
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseSettings, Field, validator

class Settings(BaseSettings):
    """Workflow service settings"""
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8014, description="Server port")
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment")
    
    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql://workflow_user:workflow_pass@localhost:5432/workflows_db",
        description="PostgreSQL database URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, description="Database max overflow connections")
    
    # Redis settings
    REDIS_URL: str = Field(default="redis://localhost:6379/2", description="Redis URL for caching and queues")
    REDIS_POOL_SIZE: int = Field(default=20, description="Redis connection pool size")
    
    # Security settings
    SECRET_KEY: str = Field(default="workflow_secret_key_change_in_production", description="Secret key for JWT")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT token expiry in minutes")
    
    # Worker settings
    WORKERS: int = Field(default=4, description="Number of worker threads")
    MAX_CONCURRENT_WORKFLOWS: int = Field(default=100, description="Maximum concurrent workflow executions")
    WORKFLOW_TIMEOUT_SECONDS: int = Field(default=300, description="Workflow execution timeout")
    
    # Webhook settings
    WEBHOOK_SECRET: str = Field(default="webhook_secret_change_in_production", description="Webhook signature secret")
    WEBHOOK_TIMEOUT_SECONDS: int = Field(default=30, description="Webhook request timeout")
    MAX_WEBHOOK_RETRIES: int = Field(default=3, description="Maximum webhook retry attempts")
    
    # Scheduling settings
    SCHEDULER_TIMEZONE: str = Field(default="UTC", description="Scheduler timezone")
    MAX_SCHEDULED_WORKFLOWS: int = Field(default=1000, description="Maximum scheduled workflows")
    
    # External service limits
    MAX_HTTP_REQUESTS_PER_MINUTE: int = Field(default=1000, description="HTTP rate limit per minute")
    MAX_EMAIL_SENDS_PER_HOUR: int = Field(default=100, description="Email send limit per hour")
    
    # Template marketplace settings
    MARKETPLACE_ENABLED: bool = Field(default=True, description="Enable template marketplace")
    ALLOW_CUSTOM_TEMPLATES: bool = Field(default=True, description="Allow users to create custom templates")
    
    # Integration settings
    INTEGRATION_CONFIGS: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "slack": {
                "enabled": True,
                "rate_limit": 100
            },
            "email": {
                "enabled": True,
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587
            },
            "aws": {
                "enabled": False,
                "region": "us-east-1"
            },
            "stripe": {
                "enabled": False,
                "api_version": "2023-10-16"
            }
        },
        description="External service integration configurations"
    )
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v
    
    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must be a Redis URL")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
        }
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "level": "DEBUG" if settings.DEBUG else "INFO",
            "formatter": "detailed",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/workflows.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["default", "file"],
            "level": "DEBUG" if settings.DEBUG else "INFO",
            "propagate": False
        },
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False
        },
        "databases": {
            "handlers": ["default"],
            "level": "WARNING",
            "propagate": False
        }
    }
}