"""
Building Bots Network - Code Generation Service Configuration

Configuration management for the code generation service with support for
different environments and Building Bots Network integration.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AIProviderConfig:
    """Configuration for AI providers"""
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    local_llama_endpoint: str = "http://localhost:11434"
    local_codellama_endpoint: str = "http://localhost:11435"
    local_starcoder_endpoint: str = "http://localhost:11436"
    default_provider: str = "claude"
    provider_timeouts: Dict[str, int] = None
    
    def __post_init__(self):
        if self.provider_timeouts is None:
            self.provider_timeouts = {
                "claude": 60,
                "gpt4": 60,
                "local_llama": 120,
                "local_codellama": 120,
                "local_starcoder": 120
            }

@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_path: str = "code_generation.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    max_cache_age_hours: int = 24
    enable_analytics: bool = True

@dataclass
class SecurityConfig:
    """Security configuration"""
    enable_auth: bool = True
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    token_expire_minutes: int = 30
    rate_limit_per_minute: int = 100
    enable_cors: bool = True
    allowed_origins: List[str] = None
    
    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ["*"]

@dataclass
class MLConfig:
    """Machine Learning configuration"""
    enable_ml_features: bool = True
    model_cache_dir: str = "./ml_models"
    retrain_interval_days: int = 7
    quality_threshold: float = 0.7
    complexity_threshold: float = 0.8
    enable_auto_learning: bool = True

@dataclass
class GenerationConfig:
    """Code generation configuration"""
    max_tokens_default: int = 4000
    temperature_default: float = 0.1
    max_context_files: int = 10
    max_file_size_mb: int = 5
    supported_languages: List[str] = None
    supported_frameworks: List[str] = None
    enable_caching: bool = True
    cache_ttl_hours: int = 24
    
    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = [
                "python", "javascript", "typescript", "rust", "go", "java",
                "cpp", "csharp", "php", "ruby", "swift", "kotlin", "scala",
                "clojure", "haskell", "html", "css", "sql"
            ]
        
        if self.supported_frameworks is None:
            self.supported_frameworks = [
                "react", "vue", "angular", "fastapi", "django", "flask",
                "express", "spring", "rails", "laravel", "nextjs", "nuxtjs",
                "svelte", "flutter", "react_native"
            ]

@dataclass
class BuildingBotsNetworkConfig:
    """Building Bots Network integration configuration"""
    hub_endpoint: str = "http://localhost:8080"
    service_name: str = "code-generation-service"
    service_version: str = "1.0.0"
    enable_cross_service_learning: bool = True
    enable_network_analytics: bool = True
    quality_standards_level: str = "production"  # development, testing, production
    enable_excellence_monitoring: bool = True
    construction_principles: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.construction_principles is None:
            self.construction_principles = {
                "production_ready": True,
                "best_practices": True,
                "continuous_learning": True,
                "security_first": True,
                "performance_optimized": True,
                "maintainable_code": True,
                "comprehensive_testing": True,
                "detailed_documentation": True
            }

@dataclass
class ServiceConfig:
    """Main service configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    workers: int = 1
    reload: bool = False
    
    # Component configurations
    ai_providers: AIProviderConfig = None
    database: DatabaseConfig = None
    security: SecurityConfig = None
    ml: MLConfig = None
    generation: GenerationConfig = None
    bbn: BuildingBotsNetworkConfig = None
    
    def __post_init__(self):
        if self.ai_providers is None:
            self.ai_providers = AIProviderConfig()
        if self.database is None:
            self.database = DatabaseConfig()
        if self.security is None:
            self.security = SecurityConfig()
        if self.ml is None:
            self.ml = MLConfig()
        if self.generation is None:
            self.generation = GenerationConfig()
        if self.bbn is None:
            self.bbn = BuildingBotsNetworkConfig()

def load_config() -> ServiceConfig:
    """Load configuration from environment variables and defaults"""
    config = ServiceConfig()
    
    # Load environment variables
    config.host = os.getenv("HOST", config.host)
    config.port = int(os.getenv("PORT", config.port))
    config.debug = os.getenv("DEBUG", "false").lower() == "true"
    config.log_level = os.getenv("LOG_LEVEL", config.log_level)
    config.workers = int(os.getenv("WORKERS", config.workers))
    
    # AI Provider configuration
    config.ai_providers.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    config.ai_providers.openai_api_key = os.getenv("OPENAI_API_KEY")
    config.ai_providers.local_llama_endpoint = os.getenv("LOCAL_LLAMA_ENDPOINT", config.ai_providers.local_llama_endpoint)
    config.ai_providers.default_provider = os.getenv("DEFAULT_AI_PROVIDER", config.ai_providers.default_provider)
    
    # Database configuration
    config.database.db_path = os.getenv("DB_PATH", config.database.db_path)
    config.database.backup_enabled = os.getenv("DB_BACKUP_ENABLED", "true").lower() == "true"
    
    # Security configuration
    config.security.enable_auth = os.getenv("ENABLE_AUTH", "true").lower() == "true"
    config.security.jwt_secret_key = os.getenv("JWT_SECRET_KEY", config.security.jwt_secret_key)
    config.security.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", config.security.rate_limit_per_minute))
    
    # ML configuration
    config.ml.enable_ml_features = os.getenv("ENABLE_ML_FEATURES", "true").lower() == "true"
    config.ml.model_cache_dir = os.getenv("ML_MODEL_CACHE_DIR", config.ml.model_cache_dir)
    
    # Building Bots Network configuration
    config.bbn.hub_endpoint = os.getenv("BBN_HUB_ENDPOINT", config.bbn.hub_endpoint)
    config.bbn.enable_cross_service_learning = os.getenv("BBN_CROSS_SERVICE_LEARNING", "true").lower() == "true"
    config.bbn.quality_standards_level = os.getenv("BBN_QUALITY_LEVEL", config.bbn.quality_standards_level)
    
    return config

def get_config() -> ServiceConfig:
    """Get the current configuration"""
    return load_config()

# Environment-specific configurations
DEVELOPMENT_CONFIG = ServiceConfig(
    debug=True,
    log_level="DEBUG",
    reload=True,
    security=SecurityConfig(enable_auth=False),
    ml=MLConfig(enable_auto_learning=True)
)

TESTING_CONFIG = ServiceConfig(
    debug=True,
    log_level="DEBUG",
    database=DatabaseConfig(db_path=":memory:"),
    security=SecurityConfig(enable_auth=False),
    bbn=BuildingBotsNetworkConfig(quality_standards_level="testing")
)

PRODUCTION_CONFIG = ServiceConfig(
    debug=False,
    log_level="INFO",
    workers=4,
    security=SecurityConfig(
        enable_auth=True,
        rate_limit_per_minute=50
    ),
    database=DatabaseConfig(
        backup_enabled=True,
        backup_interval_hours=6
    ),
    bbn=BuildingBotsNetworkConfig(
        quality_standards_level="production",
        enable_excellence_monitoring=True
    )
)

# Quality standards based on Building Bots Network principles
QUALITY_STANDARDS = {
    "development": {
        "min_quality_score": 0.5,
        "max_complexity_score": 0.9,
        "require_tests": False,
        "require_docs": False,
        "security_level": "basic"
    },
    "testing": {
        "min_quality_score": 0.6,
        "max_complexity_score": 0.8,
        "require_tests": True,
        "require_docs": False,
        "security_level": "enhanced"
    },
    "production": {
        "min_quality_score": 0.8,
        "max_complexity_score": 0.7,
        "require_tests": True,
        "require_docs": True,
        "security_level": "strict"
    }
}

def get_quality_standards(level: str) -> Dict[str, Any]:
    """Get quality standards for the specified level"""
    return QUALITY_STANDARDS.get(level, QUALITY_STANDARDS["production"])