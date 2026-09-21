"""
Healthcare module configuration with HIPAA compliance settings
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseSettings, Field, validator

class HealthcareSettings(BaseSettings):
    """Healthcare module settings with HIPAA compliance"""
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8020, description="Server port")
    DEBUG: bool = Field(default=False, description="Debug mode (should be False in production)")
    ENVIRONMENT: str = Field(default="production", description="Environment")
    
    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql://healthcare_user:healthcare_pass@localhost:5432/healthcare_db",
        description="PostgreSQL database URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, description="Database max overflow connections")
    
    # Redis settings for caching
    REDIS_URL: str = Field(default="redis://localhost:6379/4", description="Redis URL for caching")
    REDIS_POOL_SIZE: int = Field(default=20, description="Redis connection pool size")
    
    # HIPAA Compliance settings
    ENCRYPTION_KEY: str = Field(
        default="change_this_encryption_key_in_production_32_bytes_long",
        description="32-byte encryption key for PHI data"
    )
    AUDIT_LOG_RETENTION_DAYS: int = Field(default=2555, description="Audit log retention (7 years)")
    PHI_ENCRYPTION_ENABLED: bool = Field(default=True, description="Enable PHI encryption")
    DATA_MINIMIZATION_ENABLED: bool = Field(default=True, description="Enable data minimization")
    ACCESS_LOGGING_ENABLED: bool = Field(default=True, description="Enable access logging")
    
    # Patient data settings
    PATIENT_ID_FORMAT: str = Field(default="MRN-{:08d}", description="Patient ID format")
    MIN_PASSWORD_LENGTH: int = Field(default=12, description="Minimum password length")
    SESSION_TIMEOUT_MINUTES: int = Field(default=30, description="Session timeout for inactivity")
    MAX_LOGIN_ATTEMPTS: int = Field(default=3, description="Maximum login attempts")
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = Field(default=30, description="Account lockout duration")
    
    # DICOM settings
    DICOM_STORAGE_PATH: str = Field(default="./storage/dicom", description="DICOM file storage path")
    DICOM_MAX_FILE_SIZE: int = Field(default=500 * 1024 * 1024, description="Max DICOM file size (500MB)")
    DICOM_ALLOWED_MODALITIES: List[str] = Field(
        default=["CT", "MR", "US", "XA", "DX", "CR", "MG", "PT", "NM", "RF", "SC"],
        description="Allowed DICOM modalities"
    )
    DICOM_ANONYMIZATION_ENABLED: bool = Field(default=True, description="Enable DICOM anonymization")
    
    # HL7/FHIR settings
    FHIR_SERVER_URL: str = Field(default="http://localhost:8080/fhir", description="FHIR server URL")
    FHIR_VERSION: str = Field(default="R4", description="FHIR version")
    HL7_MLLP_HOST: str = Field(default="localhost", description="HL7 MLLP server host")
    HL7_MLLP_PORT: int = Field(default=2575, description="HL7 MLLP server port")
    HL7_TIMEOUT_SECONDS: int = Field(default=30, description="HL7 message timeout")
    
    # Consent management
    CONSENT_DEFAULT_DURATION_DAYS: int = Field(default=365, description="Default consent duration")
    CONSENT_REMINDER_DAYS: int = Field(default=30, description="Days before consent expiry to remind")
    CONSENT_GRANULAR_PERMISSIONS: bool = Field(default=True, description="Enable granular consent permissions")
    
    # Audit trail settings
    AUDIT_REAL_TIME_ALERTS: bool = Field(default=True, description="Enable real-time audit alerts")
    AUDIT_SUSPICIOUS_ACTIVITY_THRESHOLD: int = Field(default=10, description="Threshold for suspicious activity")
    AUDIT_EXPORT_ENABLED: bool = Field(default=True, description="Enable audit export")
    
    # Medical device integration
    DEVICE_API_TIMEOUT_SECONDS: int = Field(default=30, description="Device API timeout")
    DEVICE_MAX_CONNECTIONS: int = Field(default=100, description="Maximum device connections")
    DEVICE_HEARTBEAT_INTERVAL_SECONDS: int = Field(default=60, description="Device heartbeat interval")
    DEVICE_ENCRYPTION_REQUIRED: bool = Field(default=True, description="Require device encryption")
    
    # Clinical NLP settings
    NLP_MODEL_PATH: str = Field(default="./models/clinical_nlp", description="Clinical NLP model path")
    NLP_BATCH_SIZE: int = Field(default=32, description="NLP processing batch size")
    NLP_MAX_TEXT_LENGTH: int = Field(default=10000, description="Maximum text length for NLP")
    NLP_ANONYMIZE_OUTPUT: bool = Field(default=True, description="Anonymize NLP output")
    NLP_CONFIDENCE_THRESHOLD: float = Field(default=0.8, description="NLP confidence threshold")
    
    # File storage settings
    STORAGE_PATH: str = Field(default="./storage/healthcare", description="Healthcare file storage path")
    BACKUP_PATH: str = Field(default="./backups/healthcare", description="Backup storage path")
    TEMP_FILE_CLEANUP_HOURS: int = Field(default=24, description="Hours to keep temp files")
    
    # Security settings
    JWT_SECRET_KEY: str = Field(
        default="healthcare_jwt_secret_key_change_in_production",
        description="JWT secret key"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRY_MINUTES: int = Field(default=60, description="JWT token expiry")
    
    # Rate limiting
    API_RATE_LIMIT_PER_MINUTE: int = Field(default=100, description="API rate limit per minute")
    DICOM_UPLOAD_RATE_LIMIT: int = Field(default=10, description="DICOM upload rate limit per minute")
    
    # Monitoring and alerts
    ENABLE_PROMETHEUS_METRICS: bool = Field(default=True, description="Enable Prometheus metrics")
    ALERT_EMAIL_RECIPIENTS: List[str] = Field(default=[], description="Alert email recipients")
    ALERT_WEBHOOK_URL: Optional[str] = Field(default=None, description="Alert webhook URL")
    
    # Cloud storage (for HIPAA-compliant backup)
    AWS_S3_BUCKET: Optional[str] = Field(default=None, description="AWS S3 bucket for backups")
    AWS_KMS_KEY_ID: Optional[str] = Field(default=None, description="AWS KMS key for encryption")
    AZURE_STORAGE_ACCOUNT: Optional[str] = Field(default=None, description="Azure storage account")
    
    @validator("ENCRYPTION_KEY")
    def validate_encryption_key(cls, v):
        if len(v.encode()) != 32:
            raise ValueError("Encryption key must be exactly 32 bytes")
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith("postgresql://"):
            raise ValueError("Database URL must be PostgreSQL")
        return v
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError("Environment must be development, staging, or production")
        return v
    
    @validator("DEBUG")
    def validate_debug_in_production(cls, v, values):
        if values.get("ENVIRONMENT") == "production" and v:
            raise ValueError("DEBUG must be False in production environment")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = HealthcareSettings()

# Logging configuration for HIPAA compliance
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "hipaa_audit": {
            "format": "%(asctime)s [AUDIT] %(name)s: user=%(user_id)s action=%(action)s resource=%(resource)s result=%(result)s ip=%(ip_address)s"
        },
        "security": {
            "format": "%(asctime)s [SECURITY] %(name)s:%(lineno)d: %(message)s"
        }
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout"
        },
        "audit_file": {
            "level": "INFO",
            "formatter": "hipaa_audit",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/hipaa_audit.log",
            "maxBytes": 50485760,  # 50MB
            "backupCount": 10
        },
        "security_file": {
            "level": "WARNING",
            "formatter": "security", 
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/security.log",
            "maxBytes": 50485760,  # 50MB
            "backupCount": 10
        },
        "application_file": {
            "level": "DEBUG" if settings.DEBUG else "INFO",
            "formatter": "standard",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/healthcare.log",
            "maxBytes": 50485760,  # 50MB
            "backupCount": 10
        }
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["default", "application_file"],
            "level": "DEBUG" if settings.DEBUG else "INFO",
            "propagate": False
        },
        "hipaa_audit": {
            "handlers": ["audit_file"],
            "level": "INFO",
            "propagate": False
        },
        "security": {
            "handlers": ["security_file", "default"],
            "level": "WARNING",
            "propagate": False
        },
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False
        }
    }
}