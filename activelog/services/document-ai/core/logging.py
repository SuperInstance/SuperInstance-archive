"""
Logging configuration for document AI service
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
    log_dir = os.path.dirname(settings.log_file)
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
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
        settings.log_file,
        maxBytes=100*1024*1024,  # 100MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Document processing specific logger
    doc_logger = logging.getLogger('document_processing')
    doc_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'document_processing.log'),
        maxBytes=50*1024*1024,  # 50MB
        backupCount=10
    )
    doc_file_handler.setFormatter(detailed_formatter)
    doc_logger.addHandler(doc_file_handler)
    
    # OCR specific logger
    ocr_logger = logging.getLogger('ocr')
    ocr_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'ocr_processing.log'),
        maxBytes=25*1024*1024,  # 25MB
        backupCount=5
    )
    ocr_file_handler.setFormatter(detailed_formatter)
    ocr_logger.addHandler(ocr_file_handler)
    
    # NLP/AI specific logger
    nlp_logger = logging.getLogger('nlp')
    nlp_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'nlp_processing.log'),
        maxBytes=25*1024*1024,  # 25MB
        backupCount=5
    )
    nlp_file_handler.setFormatter(detailed_formatter)
    nlp_logger.addHandler(nlp_file_handler)
    
    # Vector database logger
    vector_logger = logging.getLogger('vector_db')
    vector_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'vector_db.log'),
        maxBytes=25*1024*1024,  # 25MB
        backupCount=5
    )
    vector_file_handler.setFormatter(detailed_formatter)
    vector_logger.addHandler(vector_file_handler)
    
    logging.info("Logging configured for document AI service")

# Set up logging when module is imported
setup_logging()

# Create loggers for different components
logger = logging.getLogger(__name__)
doc_logger = logging.getLogger('document_processing')
ocr_logger = logging.getLogger('ocr')
nlp_logger = logging.getLogger('nlp')
vector_logger = logging.getLogger('vector_db')