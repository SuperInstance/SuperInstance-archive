"""
Configuration for {{SERVICE_NAME_TITLE}} service.
"""

import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Service settings."""
    
    # Service configuration
    service_name: str = "{{SERVICE_NAME_SNAKE}}"
    port: int = {{SERVICE_PORT}}
    environment: str = "development"
    log_level: str = "INFO"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./{{SERVICE_NAME_SNAKE}}.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = "your-secret-key-here"
    
    class Config:
        env_file = ".env"
        env_prefix = "{{SERVICE_NAME_UPPER}}_"


settings = Settings()
