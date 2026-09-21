"""
Configuration for Fitness Tracker service.
"""

import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Service settings."""
    
    # Service configuration
    service_name: str = "fitness_tracker"
    port: int = 8500
    environment: str = "development"
    log_level: str = "INFO"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./fitness_tracker.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = "your-secret-key-here"
    
    class Config:
        env_file = ".env"
        env_prefix = "FITNESS_TRACKER_"


settings = Settings()
