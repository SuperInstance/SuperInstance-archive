"""
Configuration for Home Power Sharing service.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service settings."""
    
    # Service configuration
    service_name: str = "home_power_sharing"
    port: int = 8440
    environment: str = "development"
    log_level: str = "INFO"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./home_power_sharing.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = "your-secret-key-here"
    
    class Config:
        env_file = ".env"
        env_prefix = "HOME_POWER_SHARING_"


settings = Settings()
