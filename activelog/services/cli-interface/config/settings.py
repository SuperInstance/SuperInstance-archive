#!/usr/bin/env python3
"""
CLI Interface Configuration Settings
Provides configuration management for the CLI interface service
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CLIInterfaceConfig:
    """Configuration for CLI Interface Service"""
    
    def __init__(self):
        # Service configuration
        self.service_name = "cli-interface"
        self.service_port = 8342
        self.host = "0.0.0.0"
        self.debug = self._get_env_bool("DEBUG", False)
        
        # Paths
        self.project_root = Path("/home/activeloguser/activelog")
        self.service_root = self.project_root / "services" / "cli-interface"
        self.data_dir = self.project_root / "data" / "cli-interface"
        self.logs_dir = self.project_root / "logs"
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Database settings
        self.database_path = self.data_dir / "cli-interface.db"
        
        # API settings
        self.api_timeout = self._get_env_int("API_TIMEOUT", 30)
        self.max_retries = self._get_env_int("MAX_RETRIES", 3)
        
        # Rate limiting
        self.rate_limiting_enabled = self._get_env_bool("RATE_LIMITING_ENABLED", True)
        self.default_rate_limit = self._get_env_int("DEFAULT_RATE_LIMIT", 100)
        
        # Batch processing
        self.max_concurrent_jobs = self._get_env_int("MAX_CONCURRENT_JOBS", 4)
        self.job_timeout = self._get_env_int("JOB_TIMEOUT", 3600)
        
        # Webhook settings
        self.webhook_timeout = self._get_env_int("WEBHOOK_TIMEOUT", 30)
        self.webhook_retry_count = self._get_env_int("WEBHOOK_RETRY_COUNT", 3)
        
        # Event streaming
        self.event_retention_hours = self._get_env_int("EVENT_RETENTION_HOURS", 168)  # 7 days
        self.max_subscribers = self._get_env_int("MAX_SUBSCRIBERS", 1000)
        
        # Pipeline settings
        self.pipeline_work_dir = self.data_dir / "pipeline_work"
        self.pipeline_work_dir.mkdir(exist_ok=True)
        
        # CLI settings
        self.cli_install_dir = self.service_root / "bin"
        self.sdk_dir = self.service_root / "sdks"
        self.docs_dir = self.service_root / "docs"
        
        # Security settings
        self.api_key_header = "X-API-Key"
        self.webhook_signature_header = "X-Webhook-Signature"
        
        # Logging
        self.log_level = self._get_env("LOG_LEVEL", "INFO")
        self.log_file = self.logs_dir / "cli-interface.log"
        
        # External service URLs
        self.base_service_url = self._get_env("BASE_SERVICE_URL", "http://localhost")
        
        # Load custom configuration if exists
        self._load_custom_config()

    def _get_env(self, key: str, default: str = "") -> str:
        """Get environment variable with default"""
        return os.getenv(key, default)

    def _get_env_int(self, key: str, default: int) -> int:
        """Get environment variable as integer with default"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default

    def _get_env_bool(self, key: str, default: bool) -> bool:
        """Get environment variable as boolean with default"""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "yes", "1", "on")

    def _load_custom_config(self):
        """Load custom configuration from file if exists"""
        config_file = self.service_root / "config.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    custom_config = json.load(f)
                
                # Update configuration with custom values
                for key, value in custom_config.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                
                logger.info(f"Loaded custom configuration from {config_file}")
                
            except Exception as e:
                logger.warning(f"Failed to load custom configuration: {e}")

    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.debug or self._get_env("ENVIRONMENT", "production") == "development"

    def get_service_urls(self) -> Dict[str, str]:
        """Get URLs for other services"""
        return {
            "auth": f"{self.base_service_url}:8301",
            "file-manager": f"{self.base_service_url}:8302",
            "search": f"{self.base_service_url}:8303",
            "data-manager": f"{self.base_service_url}:8304",
            "ai-orchestrator": f"{self.base_service_url}:8305",
            "sync-engine": f"{self.base_service_url}:8306",
            "metadata": f"{self.base_service_url}:8307",
            "graphql": f"{self.base_service_url}:8308",
            "batch-import": f"{self.base_service_url}:8309",
            "file-watcher": f"{self.base_service_url}:8310",
            "api-gateway": f"{self.base_service_url}:8311"
        }

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                }
            },
            "handlers": {
                "default": {
                    "level": self.log_level,
                    "formatter": "standard",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "level": self.log_level,
                    "formatter": "standard",
                    "class": "logging.FileHandler",
                    "filename": str(self.log_file),
                    "mode": "a"
                }
            },
            "loggers": {
                "": {
                    "handlers": ["default", "file"],
                    "level": self.log_level,
                    "propagate": False
                }
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "service_name": self.service_name,
            "service_port": self.service_port,
            "host": self.host,
            "debug": self.debug,
            "database_path": str(self.database_path),
            "api_timeout": self.api_timeout,
            "max_retries": self.max_retries,
            "rate_limiting_enabled": self.rate_limiting_enabled,
            "default_rate_limit": self.default_rate_limit,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "job_timeout": self.job_timeout,
            "webhook_timeout": self.webhook_timeout,
            "webhook_retry_count": self.webhook_retry_count,
            "event_retention_hours": self.event_retention_hours,
            "max_subscribers": self.max_subscribers,
            "log_level": self.log_level,
            "log_file": str(self.log_file),
            "base_service_url": self.base_service_url
        }