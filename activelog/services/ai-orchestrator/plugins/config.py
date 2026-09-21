"""
Configuration management for AI Orchestrator plugins
"""
import os
from typing import Dict, Any

class PluginConfig:
    """Configuration manager for AI plugins"""
    
    @staticmethod
    def get_openai_config() -> Dict[str, Any]:
        """Get OpenAI plugin configuration from environment"""
        return {
            # API Configuration
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
            
            # Model Configuration
            'OPENAI_TEXT_MODEL': os.getenv('OPENAI_TEXT_MODEL', 'gpt-4'),
            'OPENAI_EMBEDDING_MODEL': os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-ada-002'),
            'OPENAI_VISION_MODEL': os.getenv('OPENAI_VISION_MODEL', 'gpt-4-vision-preview'),
            'OPENAI_DALLE_MODEL': os.getenv('OPENAI_DALLE_MODEL', 'dall-e-3'),
            
            # Generation Parameters
            'OPENAI_MAX_TOKENS': int(os.getenv('OPENAI_MAX_TOKENS', '4000')),
            'OPENAI_TEMPERATURE': float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
            'OPENAI_TIMEOUT': int(os.getenv('OPENAI_TIMEOUT', '30')),
            
            # Caching Configuration
            'OPENAI_ENABLE_CACHING': os.getenv('OPENAI_ENABLE_CACHING', 'true').lower() == 'true',
            'OPENAI_CACHE_TTL': int(os.getenv('OPENAI_CACHE_TTL', '3600')),
            
            # Rate Limiting
            'OPENAI_RATE_LIMIT_RPM': int(os.getenv('OPENAI_RATE_LIMIT_RPM', '60')),
            'OPENAI_RATE_LIMIT_TPM': int(os.getenv('OPENAI_RATE_LIMIT_TPM', '150000')),
            'OPENAI_RATE_LIMIT_RPD': int(os.getenv('OPENAI_RATE_LIMIT_RPD', '5000')),
        }
    
    @staticmethod
    def get_redis_config() -> Dict[str, Any]:
        """Get Redis configuration for caching"""
        return {
            'REDIS_HOST': os.getenv('REDIS_HOST', 'localhost'),
            'REDIS_PORT': int(os.getenv('REDIS_PORT', '6379')),
            'REDIS_DB': int(os.getenv('REDIS_DB', '0')),
            'REDIS_PASSWORD': os.getenv('REDIS_PASSWORD', ''),
        }

# Environment variable documentation
ENV_DOCS = {
    'OPENAI_API_KEY': 'OpenAI API key (required)',
    'OPENAI_TEXT_MODEL': 'Model for text generation and analysis (default: gpt-4)',
    'OPENAI_EMBEDDING_MODEL': 'Model for text embeddings (default: text-embedding-ada-002)',
    'OPENAI_VISION_MODEL': 'Model for image analysis (default: gpt-4-vision-preview)',
    'OPENAI_DALLE_MODEL': 'Model for image generation (default: dall-e-3)',
    'OPENAI_MAX_TOKENS': 'Maximum tokens for generation (default: 4000)',
    'OPENAI_TEMPERATURE': 'Temperature for generation (default: 0.7)',
    'OPENAI_TIMEOUT': 'Request timeout in seconds (default: 30)',
    'OPENAI_ENABLE_CACHING': 'Enable Redis caching (default: true)',
    'OPENAI_CACHE_TTL': 'Cache TTL in seconds (default: 3600)',
    'OPENAI_RATE_LIMIT_RPM': 'Requests per minute limit (default: 60)',
    'OPENAI_RATE_LIMIT_TPM': 'Tokens per minute limit (default: 150000)',
    'OPENAI_RATE_LIMIT_RPD': 'Requests per day limit (default: 5000)',
}