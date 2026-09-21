"""
Application configuration settings.

This module provides centralized configuration management for the FastAPI application,
including database settings, CORS configuration, logging, and other environment-based settings.
"""

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    All settings can be overridden by environment variables.
    The environment variables follow the pattern: UPPERCASE_SETTING_NAME.
    """

    # Application settings
    APP_NAME: str = "Unified Agent Backend API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "API for managing AI agents, workflows, and executions"
    DEBUG: bool = Field(default=False, env="DEBUG")

    # API settings
    API_V1_PREFIX: str = "/api/v1"
    TITLE: str = "Unified Agent Backend API"
    CONTACT: Dict[str, str] = {
        "name": "Support Team",
        "email": "support@example.com"
    }

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/unified_agent",
        env="DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    # Security settings
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="BACKEND_CORS_ORIGINS"
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "json"  # or "text"
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")

    # Rate limiting settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # Monitoring and metrics
    METRICS_ENABLED: bool = Field(default=False, env="METRICS_ENABLED")
    METRICS_PORT: int = 9090
    HEALTH_CHECK_INTERVAL: int = 30  # seconds

    # Agent settings
    AGENT_TIMEOUT_DEFAULT: int = 300  # seconds
    AGENT_MAX_CONCURRENT_TASKS: int = 10
    AGENT_HEARTBEAT_TIMEOUT: int = 300  # seconds

    # Workflow settings
    WORKFLOW_MAX_NODES: int = 1000
    WORKFLOW_MAX_EXECUTION_TIME: int = 3600  # seconds
    WORKFLOW_RETRY_ATTEMPTS: int = 3

    # File storage settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".json", ".yaml", ".yml", ".txt"]

    # Redis settings (for caching and session storage)
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    CACHE_TTL: int = 3600  # seconds

    # External service settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")

    # Environment settings
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    @validator("LOG_LEVEL", pre=True)
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @validator("ENVIRONMENT", pre=True)
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        valid_envs = ["development", "testing", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v.lower()

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == "testing"

    def get_database_url(self, async_db: bool = True) -> str:
        """
        Get database URL with appropriate driver.

        Args:
            async_db: Whether to use async driver

        Returns:
            Database URL string
        """
        if async_db:
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
            elif not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
                raise ValueError("Async database URL must use postgresql+asyncpg:// driver")
        else:
            if self.DATABASE_URL.startswith("postgresql+asyncpg://"):
                return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

        return self.DATABASE_URL


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance
    """
    return Settings()