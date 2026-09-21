"""
Logging configuration for video processor service
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime

from .config import settings

def setup_logging():
    """Set up logging configuration"""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(settings.LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=100*1024*1024,  # 100MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Video processing specific logger
    video_logger = logging.getLogger('video_processor')
    video_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'video_processing.log'),
        maxBytes=50*1024*1024,  # 50MB
        backupCount=10
    )
    video_file_handler.setFormatter(detailed_formatter)
    video_logger.addHandler(video_file_handler)
    
    # Streaming specific logger
    streaming_logger = logging.getLogger('streaming')
    streaming_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'streaming.log'),
        maxBytes=25*1024*1024,  # 25MB
        backupCount=5
    )
    streaming_file_handler.setFormatter(detailed_formatter)
    streaming_logger.addHandler(streaming_file_handler)
    
    # OCR specific logger
    ocr_logger = logging.getLogger('ocr')
    ocr_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'ocr_processing.log'),
        maxBytes=25*1024*1024,  # 25MB
        backupCount=5
    )
    ocr_file_handler.setFormatter(detailed_formatter)
    ocr_logger.addHandler(ocr_file_handler)
    
    logging.info("Logging configured for video processor service")

# Set up logging when module is imported
setup_logging()

# Create loggers for different components
logger = logging.getLogger(__name__)
video_logger = logging.getLogger('video_processor')
streaming_logger = logging.getLogger('streaming')
ocr_logger = logging.getLogger('ocr')
ai_logger = logging.getLogger('ai_processing')