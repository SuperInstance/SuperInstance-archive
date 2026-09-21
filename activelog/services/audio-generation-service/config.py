#!/usr/bin/env python3
"""
Configuration for the Comprehensive Audio Generation Service
Building Bots Network - Audio Construction Excellence
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ServiceConfig:
    """Main service configuration"""
    
    # Service Identity
    service_name: str = "comprehensive-audio-generation"
    service_version: str = "3.0.0"
    service_port: int = int(os.getenv("PORT", 8485))
    service_host: str = "0.0.0.0"
    
    # Building Bots Network Mission
    building_bots_network: bool = True
    construction_excellence: bool = True
    system_integration: bool = True
    interconnected_intelligence: bool = True
    
    # External Service URLs
    openai_service_url: str = "http://localhost:8475"
    generative_hub_url: str = "http://localhost:8500"
    image_service_url: str = "http://localhost:8480"
    local_ai_url: str = "http://localhost:8471"
    
    # Database Configuration
    database_path: str = "/home/activeloguser/activelog/services/audio-generation-service/audio_generation.db"
    backup_database: bool = True
    backup_interval_hours: int = 24
    
    # Audio Processing Configuration
    temp_audio_dir: str = "/tmp/audio_generation"
    max_audio_duration_seconds: int = 600  # 10 minutes max
    supported_formats: List[str] = None
    default_format: str = "mp3"
    default_quality: str = "standard"
    
    # TTS Model Configuration
    openai_tts_enabled: bool = True
    festival_enabled: bool = True
    espeak_enabled: bool = True
    piper_enabled: bool = True
    
    # Voice Cloning Configuration
    voice_cloning_enabled: bool = True
    max_reference_audio_size_mb: int = 50
    voice_similarity_threshold: float = 0.7
    
    # Music Generation Configuration
    music_generation_enabled: bool = True
    max_music_duration_seconds: int = 300  # 5 minutes max
    procedural_music_styles: List[str] = None
    
    # Audio Enhancement Configuration
    noise_reduction_enabled: bool = True
    voice_clarity_enabled: bool = True
    dynamic_compression_enabled: bool = True
    spatial_enhancement_enabled: bool = False  # Future feature
    
    # ML and Intelligence Configuration
    ml_optimization_enabled: bool = True
    user_preference_learning: bool = True
    intelligent_model_selection: bool = True
    quality_prediction_enabled: bool = True
    cost_optimization_enabled: bool = True
    
    # Performance Configuration
    max_concurrent_generations: int = 10
    generation_timeout_seconds: int = 120
    cache_audio_files: bool = True
    cache_duration_hours: int = 48
    
    # Security Configuration
    rate_limiting_enabled: bool = True
    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000
    api_key_required: bool = False
    
    # Logging Configuration
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "/home/activeloguser/activelog/services/audio-generation-service/audio_service.log"
    max_log_file_size_mb: int = 100
    
    # Building Bots Network Integration
    hub_integration_enabled: bool = True
    heartbeat_interval_seconds: int = 30
    service_discovery_enabled: bool = True
    cross_service_optimization: bool = True
    
    def __post_init__(self):
        """Initialize lists and create directories"""
        
        if self.supported_formats is None:
            self.supported_formats = ["mp3", "wav", "ogg", "flac", "aac", "m4a"]
        
        if self.procedural_music_styles is None:
            self.procedural_music_styles = [
                "ambient", "classical", "electronic", "jazz", "rock", "pop",
                "cinematic", "lo-fi", "orchestral", "meditation", "upbeat", "dramatic"
            ]
        
        # Create necessary directories
        Path(self.temp_audio_dir).mkdir(parents=True, exist_ok=True)
        Path(os.path.dirname(self.database_path)).mkdir(parents=True, exist_ok=True)
        
        if self.log_to_file:
            Path(os.path.dirname(self.log_file_path)).mkdir(parents=True, exist_ok=True)

@dataclass 
class TTSModelConfig:
    """TTS model specific configuration"""
    
    # OpenAI TTS Configuration
    openai_model: str = "tts-1"
    openai_voice_options: List[str] = None
    openai_quality_levels: List[str] = None
    openai_cost_per_1k_chars: float = 0.015
    
    # Festival TTS Configuration
    festival_voice_options: List[str] = None
    festival_sample_rate: int = 16000
    festival_audio_format: str = "wav"
    
    # eSpeak TTS Configuration
    espeak_languages: List[str] = None
    espeak_default_speed: int = 150  # words per minute
    espeak_default_pitch: int = 50
    espeak_default_amplitude: int = 100
    
    # Piper TTS Configuration
    piper_model_path: str = "/opt/piper/models"
    piper_default_model: str = "en_US-lessac-medium"
    piper_quality: str = "medium"
    
    def __post_init__(self):
        """Initialize model-specific lists"""
        
        if self.openai_voice_options is None:
            self.openai_voice_options = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        
        if self.openai_quality_levels is None:
            self.openai_quality_levels = ["standard", "hd"]
        
        if self.festival_voice_options is None:
            self.festival_voice_options = ["kal_diphone", "nitech_us_awb_arctic_hts"]
        
        if self.espeak_languages is None:
            self.espeak_languages = [
                "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
                "ar", "hi", "tr", "pl", "nl", "sv", "da", "no", "fi"
            ]

@dataclass
class MLConfig:
    """Machine Learning configuration"""
    
    # Model Training Configuration
    enable_online_learning: bool = True
    learning_rate: float = 0.1
    batch_size: int = 32
    max_training_samples: int = 10000
    
    # Voice Analysis Configuration
    voice_analysis_features: List[str] = None
    quality_assessment_threshold: float = 7.0
    naturalness_threshold: float = 7.5
    clarity_threshold: float = 8.0
    
    # Optimization Configuration
    optimization_confidence_threshold: float = 0.7
    max_optimizations_per_request: int = 5
    optimization_cache_size: int = 1000
    
    # User Preference Learning
    preference_adaptation_rate: float = 0.2
    min_samples_for_preference: int = 3
    preference_decay_days: int = 90
    
    # Building Bots Intelligence
    network_learning_enabled: bool = True
    cross_user_insights: bool = True
    global_optimization: bool = True
    construction_excellence_metrics: bool = True
    
    def __post_init__(self):
        """Initialize ML feature lists"""
        
        if self.voice_analysis_features is None:
            self.voice_analysis_features = [
                "spectral_centroid", "spectral_rolloff", "spectral_bandwidth",
                "zero_crossing_rate", "mfcc_coefficients", "pitch_stability",
                "harmonic_ratio", "noise_ratio", "speaking_rate", "pause_frequency"
            ]

@dataclass
class AudioProcessingConfig:
    """Audio processing and enhancement configuration"""
    
    # Audio Quality Settings
    default_sample_rate: int = 22050
    high_quality_sample_rate: int = 44100
    premium_sample_rate: int = 48000
    
    # Enhancement Settings
    noise_reduction_strength: float = 0.8
    voice_clarity_boost: float = 1.2
    dynamic_compression_ratio: float = 4.0
    normalization_target_lufs: float = -23.0
    
    # Processing Limits
    max_file_size_mb: int = 500
    max_processing_time_seconds: int = 300
    parallel_processing_workers: int = 4
    
    # Audio Effects Configuration
    reverb_room_size: float = 0.5
    echo_delay_ms: int = 150
    echo_decay: float = 0.4
    chorus_depth: float = 0.25
    
    # Building Bots Audio Excellence
    construction_grade_processing: bool = True
    precision_audio_analysis: bool = True
    system_integration_optimization: bool = True

@dataclass
class CacheConfig:
    """Caching configuration for performance optimization"""
    
    # Audio File Caching
    cache_enabled: bool = True
    cache_directory: str = "/tmp/audio_cache"
    max_cache_size_gb: float = 5.0
    cache_cleanup_interval_hours: int = 6
    
    # Model Caching
    model_cache_enabled: bool = True
    ml_model_cache_size: int = 100
    voice_profile_cache_size: int = 1000
    
    # Response Caching
    api_response_cache_enabled: bool = True
    response_cache_ttl_seconds: int = 300
    max_cached_responses: int = 500
    
    def __post_init__(self):
        """Create cache directories"""
        Path(self.cache_directory).mkdir(parents=True, exist_ok=True)

# Global Configuration Instances
service_config = ServiceConfig()
tts_model_config = TTSModelConfig()
ml_config = MLConfig()
audio_processing_config = AudioProcessingConfig()
cache_config = CacheConfig()

# Environment Variable Overrides
def load_config_from_env():
    """Load configuration overrides from environment variables"""
    
    # Service configuration overrides
    if os.getenv("AUDIO_SERVICE_PORT"):
        service_config.service_port = int(os.getenv("AUDIO_SERVICE_PORT"))
    
    if os.getenv("OPENAI_SERVICE_URL"):
        service_config.openai_service_url = os.getenv("OPENAI_SERVICE_URL")
    
    if os.getenv("GENERATIVE_HUB_URL"):
        service_config.generative_hub_url = os.getenv("GENERATIVE_HUB_URL")
    
    if os.getenv("AUDIO_DB_PATH"):
        service_config.database_path = os.getenv("AUDIO_DB_PATH")
    
    # TTS model configuration overrides
    if os.getenv("OPENAI_TTS_MODEL"):
        tts_model_config.openai_model = os.getenv("OPENAI_TTS_MODEL")
    
    # ML configuration overrides
    if os.getenv("ML_LEARNING_RATE"):
        ml_config.learning_rate = float(os.getenv("ML_LEARNING_RATE"))
    
    # Audio processing overrides
    if os.getenv("AUDIO_SAMPLE_RATE"):
        audio_processing_config.default_sample_rate = int(os.getenv("AUDIO_SAMPLE_RATE"))
    
    # Cache configuration overrides
    if os.getenv("AUDIO_CACHE_DIR"):
        cache_config.cache_directory = os.getenv("AUDIO_CACHE_DIR")

def get_building_bots_config() -> Dict:
    """Get building bots network specific configuration"""
    
    return {
        "mission": {
            "primary": "Excellence in audio construction and system integration",
            "secondary": "Building interconnected audio intelligence for the ecosystem",
            "values": ["precision", "innovation", "interconnectedness", "excellence"]
        },
        "network_integration": {
            "service_discovery": service_config.service_discovery_enabled,
            "cross_service_optimization": service_config.cross_service_optimization,
            "hub_integration": service_config.hub_integration_enabled,
            "construction_excellence": service_config.construction_excellence
        },
        "audio_specialization": {
            "multi_model_tts": True,
            "voice_cloning": service_config.voice_cloning_enabled,
            "music_generation": service_config.music_generation_enabled,
            "audio_enhancement": True,
            "intelligent_optimization": ml_config.network_learning_enabled
        },
        "quality_standards": {
            "construction_grade": audio_processing_config.construction_grade_processing,
            "precision_analysis": audio_processing_config.precision_audio_analysis,
            "excellence_metrics": ml_config.construction_excellence_metrics,
            "system_integration": audio_processing_config.system_integration_optimization
        }
    }

def get_service_capabilities() -> Dict:
    """Get comprehensive service capabilities"""
    
    return {
        "text_to_speech": {
            "models": ["openai-tts", "festival", "espeak", "piper"],
            "languages": tts_model_config.espeak_languages,
            "voices": tts_model_config.openai_voice_options + tts_model_config.festival_voice_options,
            "formats": service_config.supported_formats,
            "quality_levels": ["draft", "standard", "high", "premium"]
        },
        "voice_cloning": {
            "enabled": service_config.voice_cloning_enabled,
            "max_reference_size": service_config.max_reference_audio_size_mb,
            "similarity_control": True,
            "stability_control": True
        },
        "music_generation": {
            "enabled": service_config.music_generation_enabled,
            "styles": service_config.procedural_music_styles,
            "max_duration": service_config.max_music_duration_seconds,
            "procedural": True,
            "midi_support": True
        },
        "audio_editing": {
            "operations": ["trim", "merge", "enhance", "normalize", "add_effects", "change_speed"],
            "batch_processing": True,
            "format_conversion": True,
            "enhancement": True
        },
        "transcription": {
            "models": ["whisper"],
            "languages": tts_model_config.espeak_languages,
            "timestamps": True,
            "translation": True
        },
        "ai_features": {
            "intelligent_model_selection": ml_config.enable_online_learning,
            "user_preference_learning": service_config.ml_optimization_enabled,
            "quality_optimization": ml_config.optimization_confidence_threshold,
            "cost_optimization": service_config.cost_optimization_enabled,
            "building_bots_intelligence": ml_config.network_learning_enabled
        }
    }

# Initialize configuration from environment
load_config_from_env()

# Export main configurations
__all__ = [
    'service_config',
    'tts_model_config', 
    'ml_config',
    'audio_processing_config',
    'cache_config',
    'get_building_bots_config',
    'get_service_capabilities'
]