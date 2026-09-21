"""
Configuration settings for Data Export Service
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

class ExportSettings(BaseSettings):
    """Export-specific settings"""
    # File paths
    output_dir: str = Field(default="./output")
    temp_dir: str = Field(default="./temp")
    template_dir: str = Field(default="./templates")
    
    # Export limits
    max_export_size_gb: float = Field(default=5.0)
    max_files_per_export: int = Field(default=10000)
    export_timeout_hours: int = Field(default=24)
    
    # PDF settings
    pdf_max_pages: int = Field(default=1000)
    pdf_quality: str = Field(default="high")  # low, medium, high
    pdf_compress_images: bool = Field(default=True)
    
    # Image settings
    image_max_dimension: int = Field(default=2048)
    image_quality: int = Field(default=85)
    thumbnail_size: tuple = Field(default=(300, 300))
    
    # Archive settings
    compression_level: int = Field(default=6)  # 0-9 for gzip
    
    # Website generation
    website_theme: str = Field(default="default")
    website_include_metadata: bool = Field(default=True)
    
    # Progress tracking
    progress_update_interval: int = Field(default=5)  # seconds
    
    class Config:
        env_prefix = "EXPORT_"

class CloudSettings(BaseSettings):
    """Cloud provider settings"""
    # Google Drive
    google_credentials_file: Optional[str] = Field(default=None)
    google_client_id: Optional[str] = Field(default=None)
    google_client_secret: Optional[str] = Field(default=None)
    
    # Dropbox
    dropbox_app_key: Optional[str] = Field(default=None)
    dropbox_app_secret: Optional[str] = Field(default=None)
    dropbox_access_token: Optional[str] = Field(default=None)
    
    # AWS S3
    aws_access_key_id: Optional[str] = Field(default=None)
    aws_secret_access_key: Optional[str] = Field(default=None)
    aws_region: str = Field(default="us-west-2")
    aws_bucket: Optional[str] = Field(default=None)
    
    class Config:
        env_prefix = "CLOUD_"

class SecuritySettings(BaseSettings):
    """Security configuration"""
    jwt_secret_key: str = Field(default="your-secret-key-change-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiry_hours: int = Field(default=24)
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=60)
    rate_limit_burst: int = Field(default=100)
    
    # GDPR compliance
    gdpr_include_logs: bool = Field(default=False)
    gdpr_anonymize_ips: bool = Field(default=True)
    data_retention_days: int = Field(default=30)
    
    class Config:
        env_prefix = "SECURITY_"

class Settings(BaseSettings):
    """Main application settings"""
    # Server settings
    port: int = Field(default=8012)
    host: str = Field(default="0.0.0.0")
    workers: int = Field(default=4)
    debug: bool = Field(default=False)
    
    # Service info
    service_name: str = Field(default="ActiveLog Data Export Service")
    version: str = Field(default="1.0.0")
    
    # Logging
    log_level: str = Field(default="INFO")
    log_file: Optional[str] = Field(default="logs/data-export.log")
    
    # Redis for caching and queues
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # Celery task queue
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/1")
    
    # Sub-configurations
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    export: ExportSettings = Field(default_factory=ExportSettings)
    cloud: CloudSettings = Field(default_factory=CloudSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    
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
    def EXPORT_OUTPUT_DIR(self) -> str:
        """Get absolute path to export output directory"""
        return os.path.abspath(self.export.output_dir)
    
    @property 
    def EXPORT_TEMP_DIR(self) -> str:
        """Get absolute path to export temp directory"""
        return os.path.abspath(self.export.temp_dir)
    
    @property
    def TEMPLATE_DIR(self) -> str:
        """Get absolute path to templates directory"""
        return os.path.abspath(self.export.template_dir)
    
    def get_export_formats(self) -> List[str]:
        """Get list of supported export formats"""
        return [
            "pdf",
            "zip", 
            "tar.gz",
            "website",
            "photobook",
            "gdpr",
            "excel",
            "json",
            "csv"
        ]
    
    def get_cloud_providers(self) -> List[str]:
        """Get list of configured cloud providers"""
        providers = []
        
        if self.cloud.google_credentials_file or self.cloud.google_client_id:
            providers.append("google_drive")
            
        if self.cloud.dropbox_access_token:
            providers.append("dropbox")
            
        if self.cloud.aws_access_key_id:
            providers.append("aws_s3")
            
        return providers
    
    def is_cloud_provider_configured(self, provider: str) -> bool:
        """Check if a cloud provider is properly configured"""
        if provider == "google_drive":
            return bool(self.cloud.google_credentials_file or 
                       (self.cloud.google_client_id and self.cloud.google_client_secret))
        elif provider == "dropbox":
            return bool(self.cloud.dropbox_access_token)
        elif provider == "aws_s3":
            return bool(self.cloud.aws_access_key_id and 
                       self.cloud.aws_secret_access_key and 
                       self.cloud.aws_bucket)
        return False
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.EXPORT_OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.EXPORT_TEMP_DIR, exist_ok=True)
os.makedirs("logs", exist_ok=True)