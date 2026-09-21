"""
Multi-Language Voice Support
Professional multi-language processing for international maritime operations
"""

import logging
from typing import Dict, Any, Optional
try:
    from langdetect import detect
    from langdetect.lang_detect_exception import LangDetectException as LangDetectError
except ImportError:
    def detect(text):
        return 'en'
    class LangDetectError(Exception):
        pass
import requests

logger = logging.getLogger(__name__)

class MultiLanguageProcessor:
    def __init__(self):
        self.supported_languages = {
            'en': 'English',
            'es': 'Spanish', 
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'nl': 'Dutch',
            'no': 'Norwegian',
            'da': 'Danish',
            'sv': 'Swedish'
        }
        
        # Marine navigation terms in different languages
        self.marine_translations = {
            'autopilot': {
                'es': 'piloto automático',
                'fr': 'pilote automatique',
                'de': 'autopilot',
                'it': 'pilota automatico'
            },
            'heading': {
                'es': 'rumbo',
                'fr': 'cap',
                'de': 'kurs',
                'it': 'rotta'
            },
            'port': {
                'es': 'babor',
                'fr': 'bâbord',
                'de': 'backbord',
                'it': 'babordo'
            },
            'starboard': {
                'es': 'estribor',
                'fr': 'tribord',
                'de': 'steuerbord',
                'it': 'tribordo'
            }
        }
        
        logger.info("Multi-Language Processor initialized")
    
    def detect_language(self, text: str) -> Optional[str]:
        """Detect language of input text"""
        try:
            detected = detect(text)
            if detected in self.supported_languages:
                return detected
            return 'en'  # Default to English
            
        except LangDetectError:
            logger.debug(f"Language detection failed for: {text}")
            return 'en'
    
    def translate_to_english(self, text: str, source_lang: str) -> str:
        """Translate text to English for processing"""
        if source_lang == 'en':
            return text
        
        # In production, use proper translation service
        # For now, return original text
        return text
    
    def translate_from_english(self, text: str, target_lang: str) -> str:
        """Translate English text to target language"""
        if target_lang == 'en':
            return text
        
        # In production, use proper translation service
        # For now, return original text
        return text
    
    def is_supported_language(self, language: str) -> bool:
        """Check if language is supported"""
        return language in self.supported_languages
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages"""
        return self.supported_languages.copy()