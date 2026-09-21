"""
Configuration settings for DMLog Characters AI Service.
"""

import os
from typing import List, Dict, Any
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Service Configuration
    SERVICE_NAME: str = "DMLog Characters AI"
    SERVICE_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8013
    DEBUG: bool = False
    RELOAD: bool = False
    API_PREFIX: str = "/api/v1"
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./dmlog_characters.db"
    
    # Redis Configuration for caching and memory
    REDIS_URL: str = "redis://localhost:6379/1"
    MEMORY_CACHE_TTL: int = 3600  # 1 hour
    
    # Voice Synthesis Configuration
    TTS_ENGINE: str = "coqui"  # Options: coqui, espeak, custom
    VOICE_MODEL_PATH: str = "./models/voice"
    VOICE_SAMPLE_RATE: int = 22050
    VOICE_CACHE_SIZE: int = 1000
    MAX_TEXT_LENGTH: int = 1000
    
    # Voice Cloning Configuration
    VOICE_CLONE_MODEL: str = "your_tts"
    MIN_CLONE_AUDIO_SECONDS: int = 5
    MAX_CLONE_AUDIO_SECONDS: int = 300
    SUPPORTED_AUDIO_FORMATS: List[str] = ["wav", "mp3", "ogg", "flac"]
    
    # AI Model Configuration
    PERSONALITY_MODEL: str = "microsoft/DialoGPT-large"
    DIALOGUE_MODEL: str = "microsoft/DialoGPT-medium"
    EMOTION_MODEL: str = "j-hartmann/emotion-english-distilroberta-base"
    
    # Image Generation Configuration
    PORTRAIT_MODEL: str = "runwayml/stable-diffusion-v1-5"
    IMAGE_SIZE: int = 512
    MAX_GENERATION_STEPS: int = 50
    GUIDANCE_SCALE: float = 7.5
    
    # Memory System Configuration
    MEMORY_RETENTION_DAYS: int = 30
    MAX_MEMORIES_PER_CHARACTER: int = 1000
    MEMORY_IMPORTANCE_THRESHOLD: float = 0.5
    
    # Personality System Configuration
    PERSONALITY_DIMENSIONS: List[str] = [
        "extraversion", "agreeableness", "conscientiousness", 
        "neuroticism", "openness"
    ]
    TRAIT_CONSISTENCY_WEIGHT: float = 0.7
    SITUATION_ADAPTATION_WEIGHT: float = 0.3
    
    # Dialogue Generation Configuration
    MAX_DIALOGUE_LENGTH: int = 500
    CONTEXT_WINDOW_SIZE: int = 2000
    TEMPERATURE: float = 0.8
    TOP_P: float = 0.9
    
    # Emotion Configuration
    EMOTION_DECAY_RATE: float = 0.1  # Per hour
    MAX_EMOTION_INTENSITY: float = 10.0
    BASE_EMOTIONS: List[str] = [
        "joy", "anger", "fear", "sadness", "surprise", 
        "disgust", "trust", "anticipation"
    ]
    
    # Speech Pattern Configuration
    ACCENT_CATEGORIES: List[str] = [
        "british", "scottish", "irish", "american_south", 
        "american_west", "australian", "fantasy_elvish", 
        "fantasy_dwarven", "fantasy_orcish", "noble", "commoner"
    ]
    
    SPEECH_PATTERNS: Dict[str, Any] = {
        "formal": {"contractions": False, "politeness": "high"},
        "casual": {"contractions": True, "politeness": "medium"},
        "rough": {"contractions": True, "politeness": "low"},
        "archaic": {"old_english": True, "formality": "high"},
        "scholarly": {"vocabulary": "advanced", "precision": "high"}
    }
    
    # Art Style Configuration
    ART_STYLES: List[str] = [
        "fantasy_realistic", "anime", "cartoon", "oil_painting",
        "digital_art", "medieval", "steampunk", "cyberpunk", "watercolor"
    ]
    
    # Faction System Configuration
    REPUTATION_RANGE: Tuple[int, int] = (-100, 100)
    REPUTATION_DECAY_RATE: float = 0.01  # Per day
    MAJOR_ACTION_THRESHOLD: int = 10
    
    # Character Arc Configuration
    ARC_TYPES: List[str] = [
        "redemption", "fall", "growth", "discovery", "revenge",
        "love", "sacrifice", "power", "wisdom", "corruption"
    ]
    ARC_PROGRESSION_STEPS: int = 10
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_VOICE_SYNTHESIS_PER_MINUTE: int = 10
    RATE_LIMIT_IMAGE_GENERATION_PER_HOUR: int = 20
    
    # Security Configuration
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"

# Global settings instance
settings = Settings()