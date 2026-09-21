"""
Core module for document AI service
"""

from .config import settings, DOCUMENT_TYPES, LANGUAGE_CONFIGS
from .database import DatabaseManager
from .logging import setup_logging, logger, doc_logger, ocr_logger, nlp_logger, vector_logger

__all__ = [
    'settings', 
    'DOCUMENT_TYPES', 
    'LANGUAGE_CONFIGS',
    'DatabaseManager', 
    'setup_logging', 
    'logger', 
    'doc_logger', 
    'ocr_logger', 
    'nlp_logger', 
    'vector_logger'
]