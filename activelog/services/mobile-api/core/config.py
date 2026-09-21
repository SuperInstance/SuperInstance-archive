"""
Mobile API Configuration
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Mobile API settings configuration"""
    
    # Server configuration
    PORT: int = 8011
    HOST: str = "0.0.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/activelog"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB_CACHE: int = 0
    REDIS_DB_PUBSUB: int = 1
    REDIS_DB_SESSIONS: int = 2
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Mobile optimization
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB
    COMPRESSION_LEVEL: int = 6
    ENABLE_BROTLI: bool = True
    ENABLE_GZIP: bool = True
    PROTOBUF_MAX_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # Image optimization
    IMAGE_QUALITY_HIGH: int = 85
    IMAGE_QUALITY_MEDIUM: int = 70
    IMAGE_QUALITY_LOW: int = 50
    IMAGE_MAX_WIDTH: int = 2048
    IMAGE_MAX_HEIGHT: int = 2048
    IMAGE_WEBP_QUALITY: int = 80
    
    # Sync configuration
    SYNC_BATCH_SIZE: int = 100
    SYNC_TIMEOUT_SECONDS: int = 30
    SYNC_RETRY_ATTEMPTS: int = 3
    SYNC_RETRY_DELAY: int = 5
    OFFLINE_STORAGE_DAYS: int = 30
    
    # Push notifications
    FCM_SERVER_KEY: Optional[str] = None
    APNS_KEY_ID: Optional[str] = None
    APNS_KEY_FILE: Optional[str] = None
    APNS_TEAM_ID: Optional[str] = None
    VAPID_PUBLIC_KEY: Optional[str] = None
    VAPID_PRIVATE_KEY: Optional[str] = None
    VAPID_EMAIL: Optional[str] = None
    
    # Battery optimization
    ENABLE_BATTERY_OPTIMIZATION: bool = True
    MIN_BATTERY_LEVEL: int = 20
    LOW_POWER_MODE_THRESHOLD: int = 15
    BACKGROUND_SYNC_INTERVAL: int = 300  # 5 minutes
    AGGRESSIVE_SYNC_INTERVAL: int = 60   # 1 minute
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_DAY: int = 10000
    
    # Monitoring
    ENABLE_METRICS: bool = True
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    
    # File storage
    UPLOAD_DIR: str = "/tmp/activelog/uploads"
    TEMP_DIR: str = "/tmp/activelog/temp"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_FILE_TYPES: List[str] = [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "video/mp4", "video/webm", "video/quicktime",
        "audio/mpeg", "audio/wav", "audio/ogg",
        "application/pdf", "text/plain", "application/json"
    ]
    
    # Protocol Buffers
    PROTOBUF_MESSAGE_SIZE_LIMIT: int = 64 * 1024 * 1024  # 64MB
    PROTOBUF_COMPRESSION: bool = True
    
    # Mobile-specific features
    ENABLE_OFFLINE_MODE: bool = True
    ENABLE_BACKGROUND_SYNC: bool = True
    ENABLE_ADAPTIVE_QUALITY: bool = True
    ENABLE_SMART_PREFETCH: bool = True
    ENABLE_BATTERY_AWARE_SYNC: bool = True
    
    # Performance tuning
    WORKER_CONNECTIONS: int = 1000
    KEEPALIVE_TIMEOUT: int = 5
    MAX_CONCURRENT_REQUESTS: int = 100
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v):
        if isinstance(v, str):
            return v
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


class MobileClientSettings:
    """Settings specific to mobile client capabilities"""
    
    def __init__(self):
        # Image compression settings by device capability
        self.image_settings = {
            "high_end": {
                "max_width": 2048,
                "max_height": 2048,
                "quality": settings.IMAGE_QUALITY_HIGH,
                "format": "webp"
            },
            "mid_range": {
                "max_width": 1536,
                "max_height": 1536,
                "quality": settings.IMAGE_QUALITY_MEDIUM,
                "format": "webp"
            },
            "low_end": {
                "max_width": 1024,
                "max_height": 1024,
                "quality": settings.IMAGE_QUALITY_LOW,
                "format": "jpeg"
            }
        }
        
        # Sync settings by connection type
        self.sync_settings = {
            "wifi": {
                "batch_size": 100,
                "timeout": 30,
                "max_file_size": 50 * 1024 * 1024,  # 50MB
                "enable_video": True,
                "enable_high_quality": True
            },
            "cellular": {
                "batch_size": 50,
                "timeout": 15,
                "max_file_size": 10 * 1024 * 1024,  # 10MB
                "enable_video": False,
                "enable_high_quality": False
            },
            "slow": {
                "batch_size": 10,
                "timeout": 60,
                "max_file_size": 1 * 1024 * 1024,   # 1MB
                "enable_video": False,
                "enable_high_quality": False
            }
        }
        
        # Battery optimization settings
        self.battery_settings = {
            "normal": {
                "sync_interval": 300,     # 5 minutes
                "background_tasks": True,
                "push_notifications": True,
                "location_services": True
            },
            "low_power": {
                "sync_interval": 900,     # 15 minutes
                "background_tasks": False,
                "push_notifications": True,
                "location_services": False
            },
            "critical": {
                "sync_interval": 3600,    # 1 hour
                "background_tasks": False,
                "push_notifications": False,
                "location_services": False
            }
        }
    
    def get_image_settings(self, device_tier: str = "mid_range"):
        """Get image optimization settings for device tier"""
        return self.image_settings.get(device_tier, self.image_settings["mid_range"])
    
    def get_sync_settings(self, connection_type: str = "wifi"):
        """Get sync settings for connection type"""
        return self.sync_settings.get(connection_type, self.sync_settings["wifi"])
    
    def get_battery_settings(self, battery_level: int = 100):
        """Get battery optimization settings based on level"""
        if battery_level <= settings.LOW_POWER_MODE_THRESHOLD:
            return self.battery_settings["critical"]
        elif battery_level <= settings.MIN_BATTERY_LEVEL:
            return self.battery_settings["low_power"]
        else:
            return self.battery_settings["normal"]


# Global mobile settings instance
mobile_settings = MobileClientSettings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def get_mobile_settings() -> MobileClientSettings:
    """Get mobile-specific settings"""
    return mobile_settings