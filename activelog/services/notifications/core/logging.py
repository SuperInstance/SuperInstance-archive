"""
Logging configuration for Notification Service
"""

import sys
import structlog
from pathlib import Path
from typing import Optional

from .config import settings


def setup_logging(log_file: Optional[str] = None, log_level: str = "INFO"):
    """Configure structured logging for notification service"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.LOG_LEVEL == "json" 
            else structlog.dev.ConsoleRenderer(colors=True)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Get logger
    logger = structlog.get_logger("notifications")
    
    return logger


# Global logger instance
logger = setup_logging(settings.LOG_FILE, settings.LOG_LEVEL)