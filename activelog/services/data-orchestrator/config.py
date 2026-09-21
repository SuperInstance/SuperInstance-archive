"""
Data Orchestrator Configuration
Simple configuration for service startup
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class DatabaseConfig:
    url: str = "sqlite:///data_orchestrator.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20

@dataclass
class RedisConfig:
    url: str = "redis://localhost:6379"
    
@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8204

@dataclass
class HTTPConfig:
    timeout: int = 30
    connector_limit: int = 100

@dataclass
class Config:
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    server: ServerConfig = ServerConfig()
    http: HTTPConfig = HTTPConfig()

def load_config() -> Config:
    return Config()

def get_database_url(config: Config) -> str:
    return config.database.url