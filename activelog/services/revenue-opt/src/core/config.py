from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Revenue targets
    MONTHLY_TARGET: float = 1.0  # $1 monthly minimum target
    QUARTERLY_TARGET: float = 3.0
    ANNUAL_TARGET: float = 12.0
    
    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost/revenue_opt"
    
    # Redis for caching
    REDIS_URL: str = "redis://localhost:6379"
    
    # External APIs
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # ML Model settings
    CHURN_MODEL_THRESHOLD: float = 0.7
    UPSELL_CONFIDENCE_THRESHOLD: float = 0.6
    
    # A/B Testing
    AB_TEST_MIN_SAMPLE_SIZE: int = 100
    AB_TEST_SIGNIFICANCE_LEVEL: float = 0.05
    
    # Referral program
    DEFAULT_REFERRAL_REWARD: float = 5.0
    REFERRER_COMMISSION_RATE: float = 0.1
    
    # Recovery settings
    PAYMENT_RETRY_ATTEMPTS: int = 3
    PAYMENT_RETRY_DELAY_HOURS: int = 24
    
    # Monitoring
    ALERT_EMAIL: Optional[str] = None
    SLACK_WEBHOOK_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"

settings = Settings()