#!/usr/bin/env python3
"""
Configuration module for the Comprehensive Image Generation Service
Manages all configuration settings and environment variables
"""

import os
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import json

class ImageGenerationConfig(BaseSettings):
    """Configuration settings for the image generation service"""
    
    # Service settings
    service_name: str = Field(default="comprehensive-image-generation")
    service_version: str = Field(default="2.0.0")
    service_port: int = Field(default=8480)
    service_host: str = Field(default="0.0.0.0")
    debug_mode: bool = Field(default=False)
    
    # External service URLs
    openai_service_url: str = Field(default="http://localhost:8475")
    generative_hub_url: str = Field(default="http://localhost:8500")
    local_ai_url: str = Field(default="http://localhost:8471")
    
    # Database configuration
    database_path: str = Field(default="/home/activeloguser/activelog/services/image-generation-service/image_generation.db")
    backup_database: bool = Field(default=True)
    backup_interval_hours: int = Field(default=24)
    
    # Image generation settings
    default_quality: str = Field(default="standard")
    default_size: str = Field(default="1024x1024")
    default_format: str = Field(default="png")
    max_batch_size: int = Field(default=20)
    max_image_size: str = Field(default="2048x2048")
    
    # ML Model settings
    enable_prompt_enhancement: bool = Field(default=True)
    enable_style_detection: bool = Field(default=True)
    enable_quality_prediction: bool = Field(default=True)
    model_confidence_threshold: float = Field(default=0.7)
    
    # User preferences and learning
    enable_user_learning: bool = Field(default=True)
    learning_rate: float = Field(default=0.15)
    preference_decay_rate: float = Field(default=0.02)
    min_feedback_samples: int = Field(default=3)
    
    # Performance and optimization
    enable_caching: bool = Field(default=True)
    cache_expiry_minutes: int = Field(default=60)
    max_concurrent_generations: int = Field(default=5)
    generation_timeout_seconds: int = Field(default=300)
    
    # Cost management
    enable_cost_tracking: bool = Field(default=True)
    daily_cost_limit_usd: Optional[float] = Field(default=None)
    warn_cost_threshold_usd: float = Field(default=10.0)
    
    # Hub integration
    enable_hub_integration: bool = Field(default=True)
    hub_heartbeat_interval: int = Field(default=30)
    hub_registration_retry_attempts: int = Field(default=3)
    
    # Security and rate limiting
    enable_rate_limiting: bool = Field(default=True)
    requests_per_minute: int = Field(default=60)
    requests_per_hour: int = Field(default=1000)
    api_key_required: bool = Field(default=False)
    
    # File storage
    temp_file_cleanup: bool = Field(default=True)
    temp_file_max_age_hours: int = Field(default=24)
    generated_images_path: str = Field(default="/tmp/generated_images/")
    max_storage_gb: float = Field(default=10.0)
    
    # Logging and monitoring
    log_level: str = Field(default="INFO")
    enable_structured_logging: bool = Field(default=True)
    enable_performance_monitoring: bool = Field(default=True)
    metrics_export_interval: int = Field(default=60)
    
    # Development and testing
    mock_external_services: bool = Field(default=False)
    enable_test_endpoints: bool = Field(default=False)
    save_debug_info: bool = Field(default=False)
    
    class Config:
        env_prefix = "IMG_GEN_"
        case_sensitive = False
        env_file = ".env"

class ModelConfiguration:
    """Configuration for AI models and their parameters"""
    
    def __init__(self, config: ImageGenerationConfig):
        self.config = config
        self.model_configs = self._load_model_configurations()
    
    def _load_model_configurations(self) -> Dict[str, Dict]:
        """Load model-specific configurations"""
        return {
            "dall-e-3": {
                "enabled": True,
                "default_quality": "standard",
                "supported_sizes": [
                    "1024x1024", "1024x1792", "1792x1024"
                ],
                "cost_per_image": {
                    "standard": 0.040,
                    "hd": 0.080
                },
                "max_concurrent": 3,
                "timeout_seconds": 120,
                "retry_attempts": 2,
                "quality_score_weight": 0.9
            },
            "stable-diffusion": {
                "enabled": True,
                "default_quality": "standard",
                "supported_sizes": [
                    "512x512", "768x768", "1024x1024", 
                    "1536x1536", "2048x2048"
                ],
                "cost_per_image": 0.0,  # Local generation
                "max_concurrent": 2,  # Limited by local GPU
                "timeout_seconds": 60,
                "retry_attempts": 1,
                "quality_score_weight": 0.7,
                "local_model_path": "/models/stable-diffusion",
                "use_gpu": True,
                "inference_steps": 50,
                "guidance_scale": 7.5
            }
        }
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get configuration for a specific model"""
        return self.model_configs.get(model_name, {})
    
    def is_model_enabled(self, model_name: str) -> bool:
        """Check if a model is enabled"""
        return self.model_configs.get(model_name, {}).get("enabled", False)
    
    def get_supported_models(self) -> list:
        """Get list of enabled models"""
        return [name for name, config in self.model_configs.items() 
                if config.get("enabled", False)]

class StyleConfiguration:
    """Configuration for style detection and optimization"""
    
    def __init__(self):
        self.style_configs = self._load_style_configurations()
    
    def _load_style_configurations(self) -> Dict[str, Dict]:
        """Load style-specific configurations"""
        return {
            "photorealistic": {
                "keywords": ["photorealistic", "realistic", "photo", "lifelike", "natural"],
                "enhancement_prompts": [
                    "professional photography", "sharp focus", "high resolution",
                    "DSLR quality", "perfect lighting", "ultra-realistic"
                ],
                "recommended_model": "dall-e-3",
                "quality_boost": 0.2,
                "typical_use_cases": ["product photography", "portraits", "real estate"]
            },
            "artistic": {
                "keywords": ["artistic", "painting", "art", "canvas", "brush strokes"],
                "enhancement_prompts": [
                    "oil painting", "masterpiece", "artistic composition",
                    "fine art", "gallery quality", "expressive brushwork"
                ],
                "recommended_model": "stable-diffusion",
                "quality_boost": 0.15,
                "typical_use_cases": ["book covers", "gallery art", "creative projects"]
            },
            "digital_art": {
                "keywords": ["digital art", "cgi", "3d render", "digital painting"],
                "enhancement_prompts": [
                    "digital illustration", "concept art", "trending on artstation",
                    "highly detailed", "professional digital art", "cg artwork"
                ],
                "recommended_model": "dall-e-3",
                "quality_boost": 0.18,
                "typical_use_cases": ["game assets", "digital illustrations", "concept art"]
            },
            "anime": {
                "keywords": ["anime", "manga", "japanese animation", "cartoon"],
                "enhancement_prompts": [
                    "anime style", "manga art", "japanese animation",
                    "cel shading", "anime character design", "studio quality"
                ],
                "recommended_model": "stable-diffusion",
                "quality_boost": 0.1,
                "typical_use_cases": ["character design", "manga illustrations", "animation"]
            }
        }
    
    def get_style_config(self, style_name: str) -> Dict[str, Any]:
        """Get configuration for a specific style"""
        return self.style_configs.get(style_name, {})
    
    def get_enhancement_prompts(self, style_name: str) -> list:
        """Get enhancement prompts for a style"""
        return self.style_configs.get(style_name, {}).get("enhancement_prompts", [])
    
    def get_recommended_model(self, style_name: str) -> str:
        """Get recommended model for a style"""
        return self.style_configs.get(style_name, {}).get("recommended_model", "dall-e-3")

class QualityConfiguration:
    """Configuration for quality levels and scoring"""
    
    def __init__(self):
        self.quality_configs = self._load_quality_configurations()
    
    def _load_quality_configurations(self) -> Dict[str, Dict]:
        """Load quality-specific configurations"""
        return {
            "draft": {
                "description": "Quick, low-cost generation for rapid iteration",
                "cost_multiplier": 0.5,
                "time_multiplier": 0.6,
                "quality_score_target": 5.0,
                "recommended_models": ["stable-diffusion"],
                "enhancement_level": "minimal",
                "typical_use_cases": ["concept sketches", "rapid prototyping", "iteration"]
            },
            "standard": {
                "description": "Good quality for most use cases",
                "cost_multiplier": 1.0,
                "time_multiplier": 1.0,
                "quality_score_target": 7.0,
                "recommended_models": ["dall-e-3", "stable-diffusion"],
                "enhancement_level": "moderate",
                "typical_use_cases": ["general content", "social media", "presentations"]
            },
            "high": {
                "description": "High quality for professional use",
                "cost_multiplier": 1.5,
                "time_multiplier": 1.3,
                "quality_score_target": 8.5,
                "recommended_models": ["dall-e-3"],
                "enhancement_level": "significant", 
                "typical_use_cases": ["marketing materials", "publications", "client work"]
            },
            "professional": {
                "description": "Maximum quality for critical applications",
                "cost_multiplier": 2.0,
                "time_multiplier": 1.8,
                "quality_score_target": 9.5,
                "recommended_models": ["dall-e-3"],
                "enhancement_level": "maximum",
                "typical_use_cases": ["premium content", "commercial use", "print quality"]
            }
        }
    
    def get_quality_config(self, quality_level: str) -> Dict[str, Any]:
        """Get configuration for a quality level"""
        return self.quality_configs.get(quality_level, self.quality_configs["standard"])
    
    def get_cost_multiplier(self, quality_level: str) -> float:
        """Get cost multiplier for quality level"""
        return self.quality_configs.get(quality_level, {}).get("cost_multiplier", 1.0)
    
    def get_target_score(self, quality_level: str) -> float:
        """Get target quality score for level"""
        return self.quality_configs.get(quality_level, {}).get("quality_score_target", 7.0)

# Global configuration instance
config = ImageGenerationConfig()
model_config = ModelConfiguration(config)
style_config = StyleConfiguration()
quality_config = QualityConfiguration()

def get_config() -> ImageGenerationConfig:
    """Get the global configuration instance"""
    return config

def get_model_config() -> ModelConfiguration:
    """Get the model configuration instance"""
    return model_config

def get_style_config() -> StyleConfiguration:
    """Get the style configuration instance"""
    return style_config

def get_quality_config() -> QualityConfiguration:
    """Get the quality configuration instance"""
    return quality_config

def load_custom_config(config_path: str) -> Dict[str, Any]:
    """Load custom configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load custom config from {config_path}: {e}")
        return {}

def save_config_template(output_path: str = "config_template.json"):
    """Save a configuration template for customization"""
    template = {
        "service": {
            "name": "comprehensive-image-generation",
            "version": "2.0.0",
            "port": 8480,
            "debug_mode": False
        },
        "models": {
            "dall-e-3": {
                "enabled": True,
                "quality_levels": ["standard", "hd"],
                "cost_per_standard": 0.040,
                "cost_per_hd": 0.080
            },
            "stable-diffusion": {
                "enabled": True,
                "local_path": "/models/stable-diffusion",
                "use_gpu": True
            }
        },
        "features": {
            "prompt_enhancement": True,
            "style_detection": True,
            "user_learning": True,
            "hub_integration": True,
            "cost_tracking": True
        },
        "limits": {
            "max_batch_size": 20,
            "daily_cost_limit": None,
            "requests_per_minute": 60,
            "max_concurrent_generations": 5
        }
    }
    
    try:
        with open(output_path, 'w') as f:
            json.dump(template, f, indent=2)
        print(f"Configuration template saved to {output_path}")
    except Exception as e:
        print(f"Failed to save config template: {e}")

if __name__ == "__main__":
    # Print current configuration
    print("Current Configuration:")
    print(f"Service: {config.service_name} v{config.service_version}")
    print(f"Port: {config.service_port}")
    print(f"Debug Mode: {config.debug_mode}")
    print(f"Database: {config.database_path}")
    
    print("\nEnabled Models:")
    for model in model_config.get_supported_models():
        print(f"  - {model}")
    
    print("\nSupported Styles:")
    for style in style_config.style_configs.keys():
        print(f"  - {style}")
    
    print("\nQuality Levels:")
    for quality in quality_config.quality_configs.keys():
        config_data = quality_config.get_quality_config(quality)
        print(f"  - {quality}: {config_data['description']}")
    
    # Save template
    save_config_template()