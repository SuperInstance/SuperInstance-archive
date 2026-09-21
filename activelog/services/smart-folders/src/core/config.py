"""
Configuration settings for Smart Folders Service
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, Field, validator

class DatabaseSettings(BaseSettings):
    """Database configuration"""
    url: str = Field(default="postgresql://user:pass@localhost/activelog")
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=20)
    
    class Config:
        env_prefix = "DB_"

class SmartFolderSettings(BaseSettings):
    """Smart folder specific settings"""
    # Rule evaluation
    rule_evaluation_interval: int = Field(default=300)  # 5 minutes
    max_rules_per_folder: int = Field(default=10)
    
    # AI suggestions
    ai_model_name: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    ai_suggestions_enabled: bool = Field(default=True)
    ai_cache_ttl: int = Field(default=3600)  # 1 hour
    
    # Virtual folders
    virtual_folder_limit: int = Field(default=1000)
    virtual_folder_cache_size: int = Field(default=10000)
    
    # Templates
    template_cache_enabled: bool = Field(default=True)
    custom_templates_allowed: bool = Field(default=True)
    
    # Inheritance
    max_inheritance_depth: int = Field(default=10)
    inheritance_cache_ttl: int = Field(default=1800)  # 30 minutes
    
    # Performance
    max_folder_items: int = Field(default=10000)
    batch_processing_size: int = Field(default=100)
    
    class Config:
        env_prefix = "SMART_FOLDER_"

class SecuritySettings(BaseSettings):
    """Security configuration"""
    jwt_secret_key: str = Field(default="your-secret-key-change-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiry_hours: int = Field(default=24)
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=100)
    rate_limit_burst: int = Field(default=200)
    
    # Permissions
    default_folder_permissions: List[str] = Field(default=["read"])
    admin_permissions: List[str] = Field(default=["read", "write", "share", "manage"])
    
    class Config:
        env_prefix = "SECURITY_"

class CacheSettings(BaseSettings):
    """Caching configuration"""
    redis_url: str = Field(default="redis://localhost:6379/0")
    cache_ttl: int = Field(default=3600)  # 1 hour
    cache_enabled: bool = Field(default=True)
    
    # Cache keys TTL
    folder_content_ttl: int = Field(default=300)  # 5 minutes
    ai_suggestions_ttl: int = Field(default=3600)  # 1 hour
    permissions_ttl: int = Field(default=1800)  # 30 minutes
    
    class Config:
        env_prefix = "CACHE_"

class Settings(BaseSettings):
    """Main application settings"""
    # Server settings
    port: int = Field(default=8013)
    host: str = Field(default="0.0.0.0")
    workers: int = Field(default=4)
    debug: bool = Field(default=False)
    
    # Service info
    service_name: str = Field(default="ActiveLog Smart Folders Service")
    version: str = Field(default="1.0.0")
    
    # Logging
    log_level: str = Field(default="INFO")
    log_file: Optional[str] = Field(default="logs/smart-folders.log")
    
    # File system paths
    data_dir: str = Field(default="./data")
    templates_dir: str = Field(default="./templates")
    
    # Background tasks
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/1")
    
    # Sub-configurations
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    smart_folders: SmartFolderSettings = Field(default_factory=SmartFolderSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    
    @validator('port')
    def validate_port(cls, v):
        if not 1024 <= v <= 65535:
            raise ValueError('Port must be between 1024 and 65535')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    @property
    def PORT(self) -> int:
        """Backwards compatibility"""
        return self.port
    
    @property
    def WORKERS(self) -> int:
        """Backwards compatibility"""
        return self.workers
    
    @property
    def DEBUG(self) -> bool:
        """Backwards compatibility"""
        return self.debug
    
    def get_folder_types(self) -> List[str]:
        """Get supported folder types"""
        return [
            "smart",      # Rule-based dynamic folders
            "virtual",    # Virtual folders without moving files
            "template",   # Template-based folders
            "ai",         # AI-suggested folders
            "shared",     # Shared folders with permissions
            "inherited"   # Folders with inheritance rules
        ]
    
    def get_rule_operators(self) -> List[str]:
        """Get supported rule operators"""
        return [
            "equals", "not_equals", "contains", "not_contains",
            "starts_with", "ends_with", "regex", "greater_than",
            "less_than", "between", "in", "not_in", "exists",
            "not_exists", "and", "or", "not"
        ]
    
    def get_rule_conditions(self) -> List[str]:
        """Get supported rule conditions"""
        return [
            "file_name", "file_extension", "file_size", "created_date",
            "modified_date", "accessed_date", "file_type", "mime_type",
            "tags", "metadata", "content", "path", "owner", "permissions"
        ]
    
    def get_ai_models(self) -> Dict[str, Dict[str, Any]]:
        """Get available AI models for suggestions"""
        return {
            "sentence-transformers/all-MiniLM-L6-v2": {
                "name": "All MiniLM L6 v2",
                "description": "Lightweight sentence embedding model",
                "size": "small",
                "speed": "fast"
            },
            "sentence-transformers/all-mpnet-base-v2": {
                "name": "All MPNet Base v2", 
                "description": "High-quality sentence embedding model",
                "size": "medium",
                "speed": "medium"
            }
        }
    
    def get_template_categories(self) -> Dict[str, List[str]]:
        """Get folder template categories"""
        return {
            "work": [
                "projects", "documents", "presentations", "spreadsheets",
                "reports", "meetings", "emails", "resources"
            ],
            "personal": [
                "photos", "videos", "music", "documents", "downloads",
                "books", "hobbies", "travel", "family"
            ],
            "creative": [
                "designs", "artwork", "photography", "videos", "audio",
                "projects", "inspiration", "drafts", "final"
            ],
            "academic": [
                "courses", "assignments", "research", "papers", "references",
                "notes", "presentations", "data", "publications"
            ],
            "development": [
                "projects", "repositories", "documentation", "resources",
                "tools", "libraries", "scripts", "configs"
            ]
        }
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.data_dir, exist_ok=True)
os.makedirs(settings.templates_dir, exist_ok=True)
os.makedirs("logs", exist_ok=True)