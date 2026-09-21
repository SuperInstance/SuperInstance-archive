"""
Configuration for Hatchery Management service.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service settings."""
    
    # Service configuration
    service_name: str = "hatchery_management"
    port: int = 8441
    environment: str = "development"
    log_level: str = "INFO"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./hatchery_management.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = "your-secret-key-here"
    
    class Config:
        env_file = ".env"
        env_prefix = "HATCHERY_MANAGEMENT_"


settings = Settings()
