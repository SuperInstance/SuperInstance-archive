"""
Configuration settings for user instances service
"""
import os
from typing import Dict, Any
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    SERVICE_NAME: str = "user-instances"
    SERVICE_PORT: int = 8476
    SERVICE_HOST: str = "0.0.0.0"
    
    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_AMI: str = "activelog-base-minimal"
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/user_instances.db"
    BILLING_DATABASE_URL: str = "sqlite:///./data/billing.db"
    
    # External services
    AUTH_SERVICE_URL: str = "http://localhost:8001"
    BILLING_SERVICE_URL: str = "http://localhost:8005"
    MONITORING_SERVICE_URL: str = "http://localhost:8020"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8010"
    AUDIT_SERVICE_URL: str = "http://localhost:8025"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Instance configuration
    DEFAULT_STORAGE_GB: int = 100
    MAX_INSTANCES_PER_USER: int = 1
    INSTANCE_TIMEOUT_HOURS: int = 24
    
    # Monitoring
    METRICS_COLLECTION_INTERVAL: int = 60  # seconds
    HEALTH_CHECK_INTERVAL: int = 300  # seconds
    ALERT_CPU_THRESHOLD: float = 80.0
    ALERT_MEMORY_THRESHOLD: float = 90.0
    
    # Billing
    BILLING_UPDATE_INTERVAL: int = 300  # seconds
    COST_ALERT_THRESHOLD: float = 100.0  # USD
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600  # seconds
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Instance tier configuration
    TIER_INSTANCE_MAPPING: Dict[str, str] = {
        "starter": "t3.small",
        "professional": "t3.medium",
        "business": "t3.large",
        "enterprise": "m5.xlarge", 
        "premium": "m5.2xlarge"
    }
    
    # Instance pricing (USD per hour)
    INSTANCE_PRICING: Dict[str, float] = {
        "t3.micro": 0.0104,
        "t3.small": 0.0208,
        "t3.medium": 0.0416,
        "t3.large": 0.0832,
        "t3.xlarge": 0.1664,
        "m5.large": 0.096,
        "m5.xlarge": 0.192,
        "m5.2xlarge": 0.384,
        "m5.4xlarge": 0.768
    }
    
    # Storage pricing (USD per GB-month)
    STORAGE_PRICING: Dict[str, float] = {
        "gp3": 0.08,
        "gp2": 0.10,
        "io1": 0.125,
        "io2": 0.125
    }
    
    # Network pricing
    DATA_TRANSFER_PRICING: float = 0.09  # USD per GB
    KMS_PRICING: float = 1.00  # USD per key per month
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()

def get_instance_config(tier: str) -> Dict[str, Any]:
    """Get instance configuration for a tier"""
    instance_type = settings.TIER_INSTANCE_MAPPING.get(tier.lower(), "t3.small")
    
    return {
        "instance_type": instance_type,
        "storage_gb": settings.DEFAULT_STORAGE_GB,
        "hourly_cost": settings.INSTANCE_PRICING.get(instance_type, 0.0208),
        "monthly_estimate": calculate_monthly_cost(tier)
    }

def calculate_monthly_cost(tier: str) -> float:
    """Calculate estimated monthly cost for a tier"""
    instance_type = settings.TIER_INSTANCE_MAPPING.get(tier.lower(), "t3.small")
    hourly_rate = settings.INSTANCE_PRICING.get(instance_type, 0.0208)
    
    # 730 hours per month average
    monthly_compute = hourly_rate * 730
    monthly_storage = settings.DEFAULT_STORAGE_GB * settings.STORAGE_PRICING["gp3"]
    monthly_kms = settings.KMS_PRICING
    monthly_network = 10 * settings.DATA_TRANSFER_PRICING  # 10GB estimate
    
    return round(monthly_compute + monthly_storage + monthly_kms + monthly_network, 2)

def get_resource_limits(tier_level: int) -> Dict[str, Any]:
    """Get resource limits for a user tier level"""
    limits = {
        1: {  # starter
            "max_instance_type": "t3.small",
            "max_storage_gb": 100,
            "max_monthly_cost": 50.0,
            "max_cpu_cores": 2,
            "max_memory_gb": 2
        },
        2: {  # professional
            "max_instance_type": "t3.medium", 
            "max_storage_gb": 250,
            "max_monthly_cost": 150.0,
            "max_cpu_cores": 2,
            "max_memory_gb": 4
        },
        3: {  # business
            "max_instance_type": "t3.large",
            "max_storage_gb": 500, 
            "max_monthly_cost": 350.0,
            "max_cpu_cores": 2,
            "max_memory_gb": 8
        },
        4: {  # enterprise
            "max_instance_type": "m5.xlarge",
            "max_storage_gb": 1000,
            "max_monthly_cost": 750.0,
            "max_cpu_cores": 4,
            "max_memory_gb": 16
        },
        5: {  # premium
            "max_instance_type": "m5.2xlarge",
            "max_storage_gb": 2000,
            "max_monthly_cost": 1500.0,
            "max_cpu_cores": 8,
            "max_memory_gb": 32
        }
    }
    
    return limits.get(tier_level, limits[1])

def validate_configuration() -> bool:
    """Validate configuration settings"""
    required_aws_vars = ["AWS_REGION"]
    missing_vars = [var for var in required_aws_vars if not getattr(settings, var)]
    
    if missing_vars:
        print(f"Missing required configuration: {missing_vars}")
        return False
    
    return True