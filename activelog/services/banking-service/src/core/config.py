import os
from decimal import Decimal
from typing import Optional

class Settings:
    # Banking API Configuration
    API_VERSION: str = "v1"
    SERVICE_NAME: str = "Banking Service"
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://user:pass@localhost/banking_db"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
    
    # External Banking APIs
    FED_WIRE_ENDPOINT: Optional[str] = None
    ACH_NETWORK_ENDPOINT: Optional[str] = None
    CARD_NETWORK_ENDPOINT: Optional[str] = None
    
    # Security Configuration
    SECRET_KEY: str = "banking-service-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Banking Limits
    DAILY_WIRE_LIMIT: Decimal = Decimal("250000.00")
    DAILY_ACH_LIMIT: Decimal = Decimal("100000.00")
    DAILY_CARD_LIMIT: Decimal = Decimal("10000.00")
    MONTHLY_WITHDRAWAL_LIMIT: Decimal = Decimal("500000.00")
    
    # Interest Rates (annual percentages)
    SAVINGS_INTEREST_RATE: Decimal = Decimal("0.015")  # 1.5%
    CHECKING_INTEREST_RATE: Decimal = Decimal("0.001")  # 0.1%
    CD_INTEREST_RATE: Decimal = Decimal("0.025")  # 2.5%
    LOAN_BASE_RATE: Decimal = Decimal("0.06")  # 6%
    
    # Compliance Configuration
    BSA_REPORTING_THRESHOLD: Decimal = Decimal("10000.00")
    CTR_THRESHOLD: Decimal = Decimal("10000.00")
    SAR_THRESHOLD: Decimal = Decimal("5000.00")
    KYC_VERIFICATION_REQUIRED: bool = True
    AML_MONITORING_ENABLED: bool = True
    
    # Fraud Detection Thresholds
    FRAUD_VELOCITY_THRESHOLD: int = 5  # transactions per minute
    FRAUD_AMOUNT_THRESHOLD: Decimal = Decimal("5000.00")
    UNUSUAL_LOCATION_RADIUS_KM: float = 100.0
    
    # Card Issuing Configuration
    CARD_BIN_RANGE: str = "555555"  # First 6 digits
    CARD_EXPIRY_YEARS: int = 3
    CARD_CVV_LENGTH: int = 3
    
    # Lending Configuration
    MIN_CREDIT_SCORE: int = 600
    MAX_LOAN_AMOUNT: Decimal = Decimal("1000000.00")
    MIN_LOAN_AMOUNT: Decimal = Decimal("1000.00")
    DEFAULT_LOAN_TERM_MONTHS: int = 60
    
    # Check Processing
    CHECK_HOLD_DAYS: int = 2
    CHECK_IMAGE_RETENTION_DAYS: int = 2555  # 7 years
    
    # Statement Generation
    STATEMENT_GENERATION_DAY: int = 1  # First day of month
    STATEMENT_RETENTION_MONTHS: int = 84  # 7 years
    
    # External Service URLs
    PLAID_CLIENT_ID: Optional[str] = None
    PLAID_SECRET: Optional[str] = None
    PLAID_ENVIRONMENT: str = "sandbox"
    
    EXPERIAN_API_KEY: Optional[str] = None
    EQUIFAX_API_KEY: Optional[str] = None
    TRANSUNION_API_KEY: Optional[str] = None
    
    # Notification Configuration
    EMAIL_SMTP_HOST: Optional[str] = None
    EMAIL_SMTP_PORT: int = 587
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    
    SMS_PROVIDER_API_KEY: Optional[str] = None
    
    # Encryption Configuration
    ENCRYPTION_KEY: str = "banking-encryption-key-32-chars"
    PII_ENCRYPTION_ENABLED: bool = True
    

settings = Settings()