"""
Collaboration service configuration
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseSettings, Field, validator

class Settings(BaseSettings):
    """Collaboration service settings"""
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8015, description="Server port")
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment")
    
    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql://collab_user:collab_pass@localhost:5432/collaboration_db",
        description="PostgreSQL database URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, description="Database max overflow connections")
    
    # Redis settings for real-time features
    REDIS_URL: str = Field(default="redis://localhost:6379/3", description="Redis URL for real-time features")
    REDIS_POOL_SIZE: int = Field(default=20, description="Redis connection pool size")
    
    # Security settings
    SECRET_KEY: str = Field(default="collaboration_secret_key_change_in_production", description="Secret key for JWT")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, description="JWT token expiry in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, description="Refresh token expiry in days")
    
    # File storage settings
    STORAGE_PATH: str = Field(default="./storage", description="File storage path")
    MAX_FILE_SIZE: int = Field(default=100 * 1024 * 1024, description="Maximum file size in bytes (100MB)")
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=[
            "pdf", "doc", "docx", "txt", "md", "rtf",
            "xls", "xlsx", "csv",
            "ppt", "pptx",
            "jpg", "jpeg", "png", "gif", "svg",
            "mp4", "avi", "mov", "wmv",
            "zip", "rar", "tar", "gz"
        ],
        description="Allowed file extensions"
    )
    
    # Real-time settings
    WEBSOCKET_PING_INTERVAL: int = Field(default=25, description="WebSocket ping interval in seconds")
    WEBSOCKET_PING_TIMEOUT: int = Field(default=60, description="WebSocket ping timeout in seconds")
    MAX_CONCURRENT_CONNECTIONS: int = Field(default=1000, description="Maximum concurrent WebSocket connections")
    
    # Collaboration settings
    MAX_ANNOTATIONS_PER_DOCUMENT: int = Field(default=1000, description="Maximum annotations per document")
    MAX_COMMENTS_PER_THREAD: int = Field(default=100, description="Maximum comments per thread")
    ANNOTATION_EXPIRE_DAYS: int = Field(default=365, description="Days to keep annotations")
    
    # Version control settings
    MAX_VERSIONS_PER_DOCUMENT: int = Field(default=50, description="Maximum versions to keep per document")
    VERSION_CLEANUP_DAYS: int = Field(default=90, description="Days to keep old versions")
    AUTO_VERSION_ON_SAVE: bool = Field(default=True, description="Automatically create versions on save")
    
    # Workspace settings
    MAX_WORKSPACES_PER_USER: int = Field(default=50, description="Maximum workspaces per user")
    MAX_MEMBERS_PER_WORKSPACE: int = Field(default=100, description="Maximum members per workspace")
    WORKSPACE_INACTIVITY_DAYS: int = Field(default=180, description="Days before workspace is considered inactive")
    
    # Guest access settings
    GUEST_TOKEN_EXPIRE_HOURS: int = Field(default=72, description="Guest token expiry in hours")
    MAX_GUEST_SESSIONS_PER_DOCUMENT: int = Field(default=10, description="Maximum guest sessions per document")
    GUEST_RATE_LIMIT_PER_MINUTE: int = Field(default=100, description="Rate limit for guests per minute")
    
    # Notification settings
    NOTIFICATION_BATCH_SIZE: int = Field(default=100, description="Batch size for notifications")
    ACTIVITY_FEED_PAGE_SIZE: int = Field(default=20, description="Activity feed page size")
    REAL_TIME_NOTIFICATION_TIMEOUT: int = Field(default=30, description="Real-time notification timeout")
    
    # Search and indexing
    SEARCH_INDEX_PATH: str = Field(default="./search_index", description="Search index storage path")
    ENABLE_FULL_TEXT_SEARCH: bool = Field(default=True, description="Enable full-text search")
    REINDEX_INTERVAL_HOURS: int = Field(default=24, description="Hours between search reindexing")
    
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
    
    @validator("MAX_FILE_SIZE")
    def validate_file_size(cls, v):
        if v > 1024 * 1024 * 1024:  # 1GB limit
            raise ValueError("MAX_FILE_SIZE cannot exceed 1GB")
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
            "filename": "logs/collaboration.log",
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
        },
        "websockets": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False
        }
    }
}