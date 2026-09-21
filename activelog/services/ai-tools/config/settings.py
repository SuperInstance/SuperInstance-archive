"""
AI Tools Configuration Settings
"""

import os
from typing import Optional, List, Dict
from pydantic import BaseSettings, Field
from decimal import Decimal

class ImageGenerationSettings(BaseSettings):
    """Image generation configuration"""
    # OpenAI DALL-E
    openai_api_key: str = Field(default="")
    dalle_model: str = Field(default="dall-e-3")
    dalle_max_resolution: str = Field(default="1024x1024")
    dalle_cost_per_image: Decimal = Field(default=Decimal("0.04"))  # $0.04 per image
    
    # Midjourney (via Discord bot)
    midjourney_token: str = Field(default="")
    midjourney_server_id: str = Field(default="")
    midjourney_channel_id: str = Field(default="")
    midjourney_cost_per_image: Decimal = Field(default=Decimal("0.03"))
    
    # Stable Diffusion
    stability_api_key: str = Field(default="")
    stability_engine: str = Field(default="stable-diffusion-xl-1024-v1-0")
    stability_cost_per_image: Decimal = Field(default=Decimal("0.02"))
    
    # Local Stable Diffusion
    enable_local_sd: bool = Field(default=True)
    sd_model_path: str = Field(default="/models/stable-diffusion")
    local_sd_cost_per_image: Decimal = Field(default=Decimal("0.005"))  # Much cheaper locally
    
    class Config:
        env_prefix = "IMAGE_"

class LLMSettings(BaseSettings):
    """Large Language Model configuration"""
    # OpenAI
    openai_api_key: str = Field(default="")
    openai_models: List[str] = Field(default=["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"])
    gpt4_cost_per_1k_tokens: Decimal = Field(default=Decimal("0.03"))
    gpt35_cost_per_1k_tokens: Decimal = Field(default=Decimal("0.002"))
    
    # Anthropic Claude
    anthropic_api_key: str = Field(default="")
    claude_models: List[str] = Field(default=["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"])
    claude_opus_cost_per_1k_tokens: Decimal = Field(default=Decimal("0.015"))
    claude_sonnet_cost_per_1k_tokens: Decimal = Field(default=Decimal("0.003"))
    
    # Local models
    enable_local_llm: bool = Field(default=True)
    local_model_path: str = Field(default="/models/llama")
    local_llm_cost_per_1k_tokens: Decimal = Field(default=Decimal("0.0001"))
    
    # Together AI / Replicate
    together_api_key: str = Field(default="")
    replicate_api_token: str = Field(default="")
    
    class Config:
        env_prefix = "LLM_"

class VoiceSettings(BaseSettings):
    """Voice synthesis and cloning configuration"""
    # ElevenLabs
    elevenlabs_api_key: str = Field(default="")
    elevenlabs_cost_per_character: Decimal = Field(default=Decimal("0.00003"))
    
    # OpenAI TTS
    openai_tts_cost_per_character: Decimal = Field(default=Decimal("0.000015"))
    
    # Local TTS
    enable_local_tts: bool = Field(default=True)
    local_tts_model: str = Field(default="tortoise")
    local_tts_cost_per_character: Decimal = Field(default=Decimal("0.000001"))
    
    # Voice cloning
    enable_voice_cloning: bool = Field(default=True)
    min_audio_duration_seconds: int = Field(default=30)
    max_audio_duration_seconds: int = Field(default=300)
    
    class Config:
        env_prefix = "VOICE_"

class VideoSettings(BaseSettings):
    """Video generation configuration"""
    # RunwayML
    runway_api_key: str = Field(default="")
    runway_cost_per_second: Decimal = Field(default=Decimal("0.125"))  # ~$7.5 per minute
    
    # Stable Video Diffusion
    enable_local_video: bool = Field(default=True)
    local_video_model_path: str = Field(default="/models/stable-video-diffusion")
    local_video_cost_per_second: Decimal = Field(default=Decimal("0.01"))
    
    # Video processing
    max_video_length_seconds: int = Field(default=30)
    default_fps: int = Field(default=24)
    max_resolution: str = Field(default="1024x576")
    
    class Config:
        env_prefix = "VIDEO_"

class TrainingSettings(BaseSettings):
    """Model training configuration"""
    # LoRA training
    enable_lora_training: bool = Field(default=True)
    lora_training_cost_per_hour: Decimal = Field(default=Decimal("2.50"))
    max_training_hours: int = Field(default=24)
    
    # Training compute
    training_instance_type: str = Field(default="g4dn.xlarge")
    training_storage_gb: int = Field(default=100)
    
    # Model storage
    model_storage_cost_per_gb_month: Decimal = Field(default=Decimal("0.023"))
    
    class Config:
        env_prefix = "TRAINING_"

class ComputeOptimizerSettings(BaseSettings):
    """Compute optimization configuration"""
    # Local compute detection
    detect_gpu: bool = Field(default=True)
    min_gpu_memory_gb: int = Field(default=8)
    prefer_local_when_available: bool = Field(default=True)
    
    # Cost thresholds
    local_cost_multiplier: Decimal = Field(default=Decimal("0.1"))  # Local is 10x cheaper
    cloud_premium_threshold: Decimal = Field(default=Decimal("1.0"))  # Switch to cloud if >$1
    
    # Performance monitoring
    track_performance_metrics: bool = Field(default=True)
    auto_optimize_routing: bool = Field(default=True)
    
    class Config:
        env_prefix = "COMPUTE_"

class QueueSettings(BaseSettings):
    """Batch processing queue configuration"""
    # Redis for queue
    redis_url: str = Field(default="redis://localhost:6379/3")
    
    # Queue priorities
    high_priority_cost_multiplier: Decimal = Field(default=Decimal("2.0"))
    standard_priority_cost_multiplier: Decimal = Field(default=Decimal("1.0"))
    low_priority_cost_multiplier: Decimal = Field(default=Decimal("0.5"))
    
    # Batch settings
    max_batch_size: int = Field(default=10)
    batch_timeout_minutes: int = Field(default=30)
    max_concurrent_jobs: int = Field(default=5)
    
    class Config:
        env_prefix = "QUEUE_"

class CacheSettings(BaseSettings):
    """Result caching configuration"""
    # Redis for caching
    redis_url: str = Field(default="redis://localhost:6379/4")
    
    # Cache TTL (time to live)
    image_cache_ttl_hours: int = Field(default=168)  # 1 week
    text_cache_ttl_hours: int = Field(default=72)    # 3 days
    voice_cache_ttl_hours: int = Field(default=336)  # 2 weeks
    video_cache_ttl_hours: int = Field(default=168)  # 1 week
    
    # Cache size limits
    max_cache_size_gb: int = Field(default=100)
    enable_cache_compression: bool = Field(default=True)
    
    class Config:
        env_prefix = "CACHE_"

class CostEstimationSettings(BaseSettings):
    """Cost estimation configuration"""
    # Markup for cost estimation
    cost_estimation_buffer: Decimal = Field(default=Decimal("0.15"))  # 15% buffer
    
    # Minimum costs
    min_operation_cost: Decimal = Field(default=Decimal("0.001"))  # 0.1 cent minimum
    
    # Cost tracking
    track_actual_vs_estimated: bool = Field(default=True)
    cost_alert_threshold: Decimal = Field(default=Decimal("10.0"))  # Alert if >$10
    
    class Config:
        env_prefix = "COST_"

class AIToolsSettings(BaseSettings):
    """Main AI Tools settings"""
    app_name: str = Field(default="ActiveLog AI Tools")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    
    # Component settings
    image_generation: ImageGenerationSettings = ImageGenerationSettings()
    llm: LLMSettings = LLMSettings()
    voice: VoiceSettings = VoiceSettings()
    video: VideoSettings = VideoSettings()
    training: TrainingSettings = TrainingSettings()
    compute_optimizer: ComputeOptimizerSettings = ComputeOptimizerSettings()
    queue: QueueSettings = QueueSettings()
    cache: CacheSettings = CacheSettings()
    cost_estimation: CostEstimationSettings = CostEstimationSettings()
    
    # Integration with ActiveLedger
    activeledger_api_url: str = Field(default="http://localhost:8000")
    activeledger_api_key: str = Field(default="")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = AIToolsSettings()

# AI Operation Cost Models
AI_OPERATION_COSTS = {
    "image_generation": {
        "dalle_3": {"cost_per_image": Decimal("0.04"), "resolution": "1024x1024"},
        "dalle_2": {"cost_per_image": Decimal("0.02"), "resolution": "1024x1024"},
        "midjourney": {"cost_per_image": Decimal("0.03"), "resolution": "1024x1024"},
        "stable_diffusion_cloud": {"cost_per_image": Decimal("0.02"), "resolution": "1024x1024"},
        "stable_diffusion_local": {"cost_per_image": Decimal("0.005"), "resolution": "1024x1024"}
    },
    "text_generation": {
        "gpt_4": {"cost_per_1k_tokens": Decimal("0.03")},
        "gpt_35_turbo": {"cost_per_1k_tokens": Decimal("0.002")},
        "claude_opus": {"cost_per_1k_tokens": Decimal("0.015")},
        "claude_sonnet": {"cost_per_1k_tokens": Decimal("0.003")},
        "claude_haiku": {"cost_per_1k_tokens": Decimal("0.00025")},
        "llama_2_70b": {"cost_per_1k_tokens": Decimal("0.001")},
        "local_llm": {"cost_per_1k_tokens": Decimal("0.0001")}
    },
    "voice_synthesis": {
        "elevenlabs": {"cost_per_character": Decimal("0.00003")},
        "openai_tts": {"cost_per_character": Decimal("0.000015")},
        "local_tts": {"cost_per_character": Decimal("0.000001")}
    },
    "video_generation": {
        "runway_ml": {"cost_per_second": Decimal("0.125")},
        "stable_video": {"cost_per_second": Decimal("0.05")},
        "local_video": {"cost_per_second": Decimal("0.01")}
    },
    "training": {
        "lora_training": {"cost_per_hour": Decimal("2.50")},
        "full_fine_tuning": {"cost_per_hour": Decimal("15.0")},
        "model_storage": {"cost_per_gb_month": Decimal("0.023")}
    }
}

# Model Marketplace Categories
MARKETPLACE_CATEGORIES = {
    "image_models": {
        "stable_diffusion": ["realistic", "anime", "artistic", "portraits"],
        "lora_adapters": ["style", "character", "object", "concept"],
        "controlnets": ["pose", "depth", "canny", "segmentation"]
    },
    "text_models": {
        "language_models": ["chat", "completion", "instruction"],
        "fine_tuned": ["domain_specific", "style", "task_specific"],
        "embeddings": ["semantic", "code", "multilingual"]
    },
    "voice_models": {
        "tts_voices": ["celebrity", "character", "language", "accent"],
        "voice_clones": ["custom", "verified", "premium"],
        "audio_effects": ["music", "sound_effects", "ambient"]
    },
    "video_models": {
        "generation": ["text_to_video", "image_to_video", "style_transfer"],
        "editing": ["upscaling", "interpolation", "effects"],
        "animation": ["2d", "3d", "motion_graphics"]
    }
}

# Compute Optimization Rules
COMPUTE_OPTIMIZATION_RULES = {
    "image_generation": {
        "prefer_local_if": {
            "batch_size": ">= 5",
            "gpu_memory": ">= 8GB",
            "estimated_cost": "> $1.00"
        },
        "use_cloud_if": {
            "urgent": True,
            "no_local_gpu": True,
            "model_not_available_locally": True
        }
    },
    "text_generation": {
        "prefer_local_if": {
            "context_length": "< 4096",
            "batch_size": ">= 3",
            "privacy_required": True
        },
        "use_cloud_if": {
            "context_length": "> 32000",
            "model_size": "> 70B",
            "latest_model_required": True
        }
    }
}