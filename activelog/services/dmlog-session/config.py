"""
Configuration settings for DMLog Session service.
"""

import os
from typing import List, Dict, Any
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    """Main configuration class."""
    
    # Service settings
    SERVICE_NAME: str = "dmlog-session"
    SERVICE_PORT: int = int(os.getenv("DMLOG_SESSION_PORT", 8016))
    SERVICE_HOST: str = os.getenv("DMLOG_SESSION_HOST", "0.0.0.0")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://dmlog:dmlog@localhost:5432/dmlog_session"
    )
    
    # Redis for caching and real-time features
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/2")
    
    # Audio recording settings
    AUDIO_CONFIG: Dict[str, Any] = {
        "sample_rate": 16000,  # 16kHz for speech recognition
        "channels": 1,         # Mono
        "chunk_size": 1024,    # Buffer size
        "format": "int16",     # 16-bit samples
        "max_duration_hours": 8,  # Maximum session duration
        "compression": "opus", # Audio compression format
        "auto_gain": True,     # Automatic gain control
        "noise_reduction": True,
        "echo_cancellation": True
    }
    
    # Speech recognition settings
    SPEECH_CONFIG: Dict[str, Any] = {
        "provider": "whisper",  # whisper, google, azure
        "model": "base",       # tiny, base, small, medium, large
        "language": "en",      # Primary language
        "auto_detect_language": True,
        "speaker_identification": True,
        "confidence_threshold": 0.7,
        "segment_duration": 30,  # seconds
        "overlap_duration": 5,   # seconds
        "realtime_transcription": True
    }
    
    # Speaker identification settings
    SPEAKER_CONFIG: Dict[str, Any] = {
        "min_speakers": 2,
        "max_speakers": 8,
        "clustering_method": "spectral",  # spectral, agglomerative
        "embedding_model": "speechbrain/spkrec-ecapa-voxceleb",
        "similarity_threshold": 0.8,
        "voice_activity_detection": True,
        "enrollment_duration": 30,  # seconds needed for enrollment
        "update_threshold": 0.1     # Re-cluster if speaker changes
    }
    
    # Session recording settings
    SESSION_CONFIG: Dict[str, Any] = {
        "auto_save_interval": 300,  # 5 minutes
        "backup_frequency": 3,      # Keep 3 backups
        "storage_path": os.getenv("SESSION_STORAGE", "./storage/sessions"),
        "audio_path": os.getenv("AUDIO_STORAGE", "./storage/audio"),
        "transcription_delay": 5,   # seconds before processing
        "highlight_detection": True,
        "emotion_detection": False, # Optional advanced feature
        "auto_chapter_detection": True
    }
    
    # Virtual tabletop settings
    VTT_CONFIG: Dict[str, Any] = {
        "map_formats": ["jpg", "jpeg", "png", "webp", "svg"],
        "max_map_size_mb": 50,
        "grid_sizes": [25, 50, 70, 100],  # pixels per grid square
        "fog_of_war": True,
        "dynamic_lighting": True,
        "max_tokens": 100,
        "token_formats": ["png", "jpg", "jpeg", "webp"],
        "layers": ["background", "terrain", "tokens", "effects", "ui"],
        "collaboration_update_rate": 60  # Updates per second
    }
    
    # Fog of war settings
    FOG_CONFIG: Dict[str, Any] = {
        "reveal_methods": ["manual", "line_of_sight", "movement"],
        "sight_ranges": {
            "normal": 30,      # feet
            "darkvision": 60,
            "blindsight": 10,
            "truesight": 120
        },
        "light_sources": {
            "torch": {"bright": 20, "dim": 40},
            "lantern": {"bright": 30, "dim": 60},
            "candle": {"bright": 5, "dim": 10},
            "daylight": {"bright": 60, "dim": 120}
        },
        "fog_opacity": 0.8,
        "transition_speed": 0.3  # seconds
    }
    
    # Music and ambiance settings
    AUDIO_PLAYER_CONFIG: Dict[str, Any] = {
        "supported_formats": ["mp3", "wav", "ogg", "m4a", "flac"],
        "crossfade_duration": 3,  # seconds
        "volume_levels": {
            "master": 1.0,
            "music": 0.7,
            "ambiance": 0.5,
            "sfx": 0.8
        },
        "playlists": {
            "combat": "high_energy",
            "exploration": "ambient",
            "social": "tavern",
            "mystery": "suspenseful"
        },
        "auto_mood_detection": True,
        "spatial_audio": False  # 3D audio positioning
    }
    
    # Scheduling settings
    SCHEDULING_CONFIG: Dict[str, Any] = {
        "timezone_detection": True,
        "reminder_times": [7, 1, 0.25],  # days before session
        "availability_window_days": 14,
        "recurring_sessions": True,
        "calendar_integration": ["google", "outlook", "ical"],
        "auto_scheduling": False,  # AI-powered scheduling suggestions
        "meeting_duration_default": 4,  # hours
        "buffer_time": 15  # minutes between sessions
    }
    
    # Analytics settings
    ANALYTICS_CONFIG: Dict[str, Any] = {
        "track_speaking_time": True,
        "track_character_interactions": True,
        "track_dice_rolls": True,
        "track_rule_lookups": True,
        "engagement_metrics": True,
        "sentiment_analysis": True,
        "keyword_tracking": True,
        "privacy_mode": True,  # Anonymize personal data
        "retention_days": 365,
        "export_formats": ["json", "csv", "pdf"]
    }
    
    # Survey and feedback settings
    FEEDBACK_CONFIG: Dict[str, Any] = {
        "auto_survey_trigger": True,
        "survey_delay_minutes": 15,  # After session ends
        "question_types": [
            "rating_scale",
            "multiple_choice", 
            "text_response",
            "emoji_response"
        ],
        "mandatory_questions": ["overall_rating", "highlight"],
        "anonymous_feedback": True,
        "feedback_aggregation": True,
        "dm_only_questions": True
    }
    
    # Handout and prop settings
    HANDOUT_CONFIG: Dict[str, Any] = {
        "supported_formats": ["pdf", "jpg", "png", "txt", "md", "html"],
        "max_file_size_mb": 25,
        "storage_path": os.getenv("HANDOUT_STORAGE", "./storage/handouts"),
        "auto_ocr": True,  # Extract text from images
        "version_control": True,
        "player_permissions": ["view", "download", "annotate"],
        "batch_distribution": True,
        "reveal_scheduling": True  # Schedule reveals
    }
    
    # Security settings
    SECURITY_CONFIG: Dict[str, Any] = {
        "session_timeout": 3600,  # 1 hour
        "max_file_uploads": 10,
        "rate_limiting": True,
        "audio_encryption": True,
        "end_to_end_encryption": False,  # Future feature
        "audit_logging": True,
        "player_verification": True,
        "dm_privileges": True
    }
    
    # AI and ML settings
    AI_CONFIG: Dict[str, Any] = {
        "enabled": True,
        "recap_generation": True,
        "highlight_detection": True,
        "mood_detection": True,
        "auto_tagging": True,
        "content_warnings": True,
        "language_models": {
            "summary": "gpt-3.5-turbo",
            "analysis": "claude-3-haiku",
            "transcription": "whisper-1"
        },
        "fallback_providers": True,
        "privacy_mode": True
    }
    
    # WebRTC settings for real-time audio
    WEBRTC_CONFIG: Dict[str, Any] = {
        "stun_servers": [
            "stun:stun.l.google.com:19302",
            "stun:stun1.l.google.com:19302"
        ],
        "turn_servers": [],  # Add TURN servers for production
        "ice_gathering_timeout": 5000,
        "connection_timeout": 10000,
        "audio_codecs": ["opus", "pcmu", "pcma"],
        "auto_gain_control": True,
        "echo_cancellation": True,
        "noise_suppression": True
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = True