"""
Configuration settings for ActiveLog Batch Import Service
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "activelog-batch-import"
    PORT: int = 8004
    DEBUG: bool = False
    
    # Directory Paths
    BASE_PATH: str = os.path.expanduser("~/activelog")
    IMPORT_QUEUE_PATH: str = os.path.expanduser("~/activelog/import-queue")
    PROCESSING_PATH: str = os.path.expanduser("~/activelog/processing")
    COMPLETED_PATH: str = os.path.expanduser("~/activelog/completed")
    FAILED_PATH: str = os.path.expanduser("~/activelog/failed")
    REPORTS_PATH: str = os.path.expanduser("~/activelog/reports")
    THUMBNAILS_PATH: str = os.path.expanduser("~/activelog/thumbnails")
    
    # Monitoring Configuration
    MONITOR_INTERVAL: int = 30  # seconds
    BATCH_SIZE: int = 50
    MAX_CONCURRENT_JOBS: int = 5
    CHUNK_SIZE: int = 8192  # bytes for file reading
    
    # File Processing
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    SUPPORTED_IMAGE_FORMATS: List[str] = [
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic'
    ]
    SUPPORTED_VIDEO_FORMATS: List[str] = [
        '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'
    ]
    SUPPORTED_AUDIO_FORMATS: List[str] = [
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'
    ]
    SUPPORTED_DOCUMENT_FORMATS: List[str] = [
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'
    ]
    
    # Thumbnail Generation
    THUMBNAIL_SIZES: List[tuple] = [(150, 150), (300, 300), (800, 600)]
    THUMBNAIL_QUALITY: int = 85
    VIDEO_THUMBNAIL_TIME: int = 5  # seconds into video
    
    # MinIO Configuration
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "activelog-files"
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://activelog:password@localhost:5432/activelog"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    ALLOWED_ORIGINS: List[str] = ["*"]
    SECRET_KEY: str = "your-secret-key-here"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    # Duplicate Detection
    HASH_ALGORITHM: str = "sha256"
    DUPLICATE_ACTION: str = "skip"  # skip, overwrite, rename
    
    # Notification
    WEBHOOK_URL: Optional[str] = None
    EMAIL_NOTIFICATIONS: bool = False
    
    # Performance
    WORKER_THREADS: int = 4
    IO_THREADS: int = 8
    
    @validator('IMPORT_QUEUE_PATH', 'PROCESSING_PATH', 'COMPLETED_PATH', 'FAILED_PATH')
    def validate_paths(cls, v):
        """Ensure paths are absolute"""
        return str(Path(v).resolve())
    
    @validator('SUPPORTED_IMAGE_FORMATS', 'SUPPORTED_VIDEO_FORMATS', 
              'SUPPORTED_AUDIO_FORMATS', 'SUPPORTED_DOCUMENT_FORMATS')
    def validate_formats(cls, v):
        """Ensure formats start with dot and are lowercase"""
        return [fmt.lower() if fmt.startswith('.') else f'.{fmt.lower()}' for fmt in v]
    
    @property
    def all_supported_formats(self) -> List[str]:
        """Get all supported file formats"""
        return (
            self.SUPPORTED_IMAGE_FORMATS +
            self.SUPPORTED_VIDEO_FORMATS +
            self.SUPPORTED_AUDIO_FORMATS +
            self.SUPPORTED_DOCUMENT_FORMATS
        )
    
    class Config:
        env_file = ".env"
        env_prefix = "BATCH_IMPORT_"

# Create settings instance
settings = Settings()

# Ensure required directories exist
for path in [
    settings.IMPORT_QUEUE_PATH,
    settings.PROCESSING_PATH,
    settings.COMPLETED_PATH,
    settings.FAILED_PATH,
    settings.REPORTS_PATH,
    settings.THUMBNAILS_PATH
]:
    Path(path).mkdir(parents=True, exist_ok=True)