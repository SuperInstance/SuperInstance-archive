"""
Configuration settings for ActiveLog Video Processor Service
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "activelog-video-processor"
    PORT: int = 8007
    DEBUG: bool = False
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://activelog:password@localhost:5432/activelog"
    
    # Redis Configuration (for job queues and progress tracking)
    REDIS_URL: str = "redis://localhost:6379/4"
    
    # File Paths
    TEMP_PATH: str = "/tmp/activelog_video"
    OUTPUT_PATH: str = "/home/activeloguser/activelog/services/video-processor/output"
    UPLOAD_PATH: str = "/home/activeloguser/activelog/uploads"
    
    # Video Processing Configuration
    MAX_VIDEO_SIZE_MB: int = 500  # Maximum video file size in MB
    MAX_VIDEO_DURATION_MINUTES: int = 120  # Maximum video duration
    SUPPORTED_VIDEO_FORMATS: List[str] = [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"]
    SUPPORTED_AUDIO_FORMATS: List[str] = [".mp3", ".wav", ".aac", ".m4a", ".ogg"]
    
    # Keyframe Extraction
    KEYFRAME_INTERVAL_SECONDS: float = 2.0  # Extract keyframe every N seconds
    MAX_KEYFRAMES_PER_VIDEO: int = 1000
    KEYFRAME_QUALITY: int = 95  # JPEG quality for keyframes
    KEYFRAME_SIZE: tuple = (640, 360)  # Default keyframe resolution
    
    # Thumbnail Generation
    THUMBNAIL_SIZES: List[tuple] = [(320, 180), (640, 360), (1280, 720)]
    THUMBNAIL_QUALITY: int = 85
    PREVIEW_DURATION_SECONDS: int = 30  # Duration of preview videos
    PREVIEW_FPS: int = 24
    
    # Scene Detection
    SCENE_DETECTION_THRESHOLD: float = 0.3  # Scene change sensitivity
    MIN_SCENE_DURATION_SECONDS: float = 1.0  # Minimum scene length
    MAX_SCENES_PER_VIDEO: int = 200
    
    # OCR Configuration
    OCR_ENABLED: bool = True
    OCR_LANGUAGES: List[str] = ["eng", "spa", "fra", "deu"]  # Tesseract language codes
    OCR_CONFIDENCE_THRESHOLD: int = 60  # Minimum OCR confidence
    OCR_FRAME_INTERVAL_SECONDS: float = 5.0  # OCR analysis interval
    OCR_TEXT_MIN_LENGTH: int = 3  # Minimum text length to keep
    
    # AI Summary Configuration
    AI_SUMMARY_ENABLED: bool = True
    AI_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    SUMMARY_MAX_LENGTH: int = 500  # Maximum summary length
    SUMMARY_MIN_LENGTH: int = 50   # Minimum summary length
    SUMMARY_FRAME_SAMPLE_RATE: float = 10.0  # Analyze every N seconds for summary
    
    # Subtitle Processing
    SUBTITLE_FORMATS: List[str] = [".srt", ".vtt", ".ass", ".ssa"]
    SUBTITLE_CONFIDENCE_THRESHOLD: float = 0.7
    AUTO_SUBTITLE_GENERATION: bool = True
    SUBTITLE_LANGUAGES: List[str] = ["en", "es", "fr", "de"]
    
    # Streaming Configuration
    STREAMING_ENABLED: bool = True
    STREAM_CHUNK_SIZE: int = 1024 * 1024  # 1MB chunks
    MAX_CONCURRENT_STREAMS: int = 10
    STREAM_TIMEOUT_SECONDS: int = 300  # 5 minutes
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30  # seconds
    
    # Performance Settings
    MAX_CONCURRENT_JOBS: int = 4
    WORKER_THREADS: int = 2
    FFMPEG_THREADS: int = 0  # 0 = auto-detect CPU cores
    GPU_ACCELERATION: bool = False  # Enable GPU acceleration if available
    MEMORY_LIMIT_MB: int = 2048  # Memory limit per job
    
    # Quality Settings
    VIDEO_CODEC: str = "libx264"
    AUDIO_CODEC: str = "aac"
    CRF_VALUE: int = 23  # Constant Rate Factor for encoding quality
    PRESET: str = "medium"  # FFmpeg encoding preset
    
    # Advanced Processing
    MOTION_DETECTION_ENABLED: bool = True
    FACE_DETECTION_ENABLED: bool = False  # Requires additional models
    OBJECT_DETECTION_ENABLED: bool = False  # Requires additional models
    AUDIO_ANALYSIS_ENABLED: bool = True
    
    # API Configuration
    MAX_REQUEST_SIZE_MB: int = 1000
    REQUEST_TIMEOUT_SECONDS: int = 300
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    
    # Storage Configuration
    CLEANUP_TEMP_FILES: bool = True
    TEMP_FILE_RETENTION_HOURS: int = 24
    OUTPUT_FILE_RETENTION_DAYS: int = 30
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "/home/activeloguser/activelog/services/video-processor/logs/video_processor.log"
    
    # External Service URLs
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8006"
    ANALYTICS_SERVICE_URL: str = "http://localhost:8005"
    
    # Security
    ALLOWED_ORIGINS: List[str] = ["*"]
    API_KEY_REQUIRED: bool = False
    MAX_UPLOAD_SIZE_MB: int = 1000
    
    # Feature Flags
    ENABLE_BATCH_PROCESSING: bool = True
    ENABLE_REAL_TIME_ANALYSIS: bool = True
    ENABLE_METADATA_EXTRACTION: bool = True
    ENABLE_AUDIO_TRANSCRIPTION: bool = True
    
    @field_validator('THUMBNAIL_SIZES')
    @classmethod
    def validate_thumbnail_sizes(cls, v):
        """Validate thumbnail sizes are tuples of two integers"""
        for size in v:
            if not isinstance(size, tuple) or len(size) != 2:
                raise ValueError("Thumbnail sizes must be tuples of (width, height)")
            if not all(isinstance(dim, int) and dim > 0 for dim in size):
                raise ValueError("Thumbnail dimensions must be positive integers")
        return v
    
    @field_validator('SCENE_DETECTION_THRESHOLD')
    @classmethod
    def validate_scene_threshold(cls, v):
        """Validate scene detection threshold"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Scene detection threshold must be between 0.0 and 1.0")
        return v
    
    @field_validator('OCR_CONFIDENCE_THRESHOLD')
    @classmethod
    def validate_ocr_confidence(cls, v):
        """Validate OCR confidence threshold"""
        if not 0 <= v <= 100:
            raise ValueError("OCR confidence threshold must be between 0 and 100")
        return v
    
    @property
    def temp_path_exists(self) -> bool:
        """Check if temp path exists"""
        return os.path.exists(self.TEMP_PATH)
    
    @property
    def output_path_exists(self) -> bool:
        """Check if output path exists"""
        return os.path.exists(self.OUTPUT_PATH)
    
    @property
    def ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    @property
    def tesseract_available(self) -> bool:
        """Check if Tesseract is available"""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    model_config = {
        "env_file": ".env",
        "env_prefix": "VIDEO_PROCESSOR_"
    }

# Create settings instance
settings = Settings()

# Ensure required directories exist
for path in [settings.TEMP_PATH, settings.OUTPUT_PATH]:
    os.makedirs(path, exist_ok=True)