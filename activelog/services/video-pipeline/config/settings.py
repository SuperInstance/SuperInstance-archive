"""
Video Pipeline Configuration Settings
"""
from typing import List, Optional
from pydantic import BaseSettings, Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Video Processing Pipeline"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8004
    workers: int = 1
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://activelog_admin:SecurePass123!@localhost:5432/activelog",
        env="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    
    # MinIO Object Storage
    minio_endpoint: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin123", env="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, env="MINIO_SECURE")
    minio_bucket_videos: str = Field(default="videos", env="MINIO_BUCKET_VIDEOS")
    minio_bucket_thumbnails: str = Field(default="thumbnails", env="MINIO_BUCKET_THUMBNAILS")
    minio_bucket_processed: str = Field(default="processed", env="MINIO_BUCKET_PROCESSED")
    
    # Elasticsearch
    elasticsearch_url: str = Field(
        default="http://localhost:9200",
        env="ELASTICSEARCH_URL"
    )
    elasticsearch_index_videos: str = Field(
        default="videos",
        env="ELASTICSEARCH_INDEX_VIDEOS"
    )
    
    # NATS Message Queue
    nats_url: str = Field(default="nats://localhost:4222", env="NATS_URL")
    nats_subjects: dict = {
        "video_uploaded": "video.uploaded",
        "video_processed": "video.processed",
        "video_failed": "video.failed",
        "transcode_request": "video.transcode",
        "analysis_request": "video.analysis",
        "notification": "notifications"
    }
    
    # Celery (alternative to NATS for heavy processing)
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        env="CELERY_RESULT_BACKEND"
    )
    
    # External Services
    ai_orchestrator_url: str = Field(
        default="http://localhost:8001",
        env="AI_ORCHESTRATOR_URL"
    )
    auth_service_url: str = Field(
        default="http://localhost:8002",
        env="AUTH_SERVICE_URL"
    )
    metadata_service_url: str = Field(
        default="http://localhost:8003",
        env="METADATA_SERVICE_URL"
    )
    api_gateway_url: str = Field(
        default="http://localhost:8088",
        env="API_GATEWAY_URL"
    )
    
    # Video Processing Settings
    max_file_size_mb: int = Field(default=2048, env="MAX_FILE_SIZE_MB")  # 2GB
    supported_formats: List[str] = [
        "mp4", "avi", "mov", "mkv", "wmv", "flv", "webm", "m4v", "3gp"
    ]
    
    # Transcoding Settings
    transcode_formats: List[str] = ["mp4", "webm"]
    transcode_resolutions: List[str] = ["480p", "720p", "1080p"]
    transcode_bitrates: dict = {
        "480p": "1000k",
        "720p": "2500k", 
        "1080p": "5000k"
    }
    
    # AI Processing Settings
    enable_scene_detection: bool = True
    enable_object_detection: bool = True
    enable_face_detection: bool = True
    enable_ocr: bool = True
    enable_speech_to_text: bool = True
    enable_sentiment_analysis: bool = True
    
    # OCR Settings
    ocr_languages: List[str] = ["en", "es", "fr", "de", "it"]
    ocr_confidence_threshold: float = 0.6
    
    # Speech Recognition Settings
    whisper_model: str = "base"
    speech_languages: List[str] = ["en", "es", "fr", "de", "it"]
    
    # Computer Vision Settings
    scene_detection_threshold: float = 0.3
    object_detection_confidence: float = 0.5
    face_detection_confidence: float = 0.7
    
    # Thumbnail Generation
    thumbnail_sizes: List[tuple] = [(160, 120), (320, 240), (640, 480)]
    thumbnail_intervals: List[int] = [10, 30, 60]  # seconds
    
    # Security
    jwt_secret_key: str = Field(default="your-secret-key", env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst_size: int = 100
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = "json"
    log_file_path: Optional[str] = None
    
    # Development
    reload: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()