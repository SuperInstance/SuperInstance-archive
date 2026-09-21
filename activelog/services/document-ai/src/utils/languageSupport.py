#!/usr/bin/env python3
"""
Multi-Language Support Module
Handles language detection, translation, and localized processing
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import uuid
from datetime import datetime

# Language detection
from langdetect import detect, detect_langs, DetectorFactory
import langdetect.lang_detect_exception

# Text processing
import spacy
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

# Translation
try:
    from googletrans import Translator
    HAS_GOOGLETRANS = True
except ImportError:
    HAS_GOOGLETRANS = False

import requests
import aiohttp

# Language-specific libraries
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize

# Utilities
import warnings
warnings.filterwarnings('ignore')

class LanguageSupport:
    """Multi-language support for document processing"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', './output/language')
        self.ai_orchestrator_url = self.config.get('ai_orchestrator_url', 'http://localhost:8003')
        
        # Supported languages
        self.supported_languages = {
            'en': {'name': 'English', 'spacy_model': 'en_core_web_sm'},
            'es': {'name': 'Spanish', 'spacy_model': 'es_core_news_sm'},
            'fr': {'name': 'French', 'spacy_model': 'fr_core_news_sm'},
            'de': {'name': 'German', 'spacy_model': 'de_core_news_sm'},
            'it': {'name': 'Italian', 'spacy_model': 'it_core_news_sm'},
            'pt': {'name': 'Portuguese', 'spacy_model': 'pt_core_news_sm'},
            'nl': {'name': 'Dutch', 'spacy_model': 'nl_core_news_sm'},
            'zh': {'name': 'Chinese', 'spacy_model': 'zh_core_web_sm'},
            'ja': {'name': 'Japanese', 'spacy_model': 'ja_core_news_sm'},
            'ko': {'name': 'Korean', 'spacy_model': 'ko_core_news_sm'},
            'ru': {'name': 'Russian', 'spacy_model': 'ru_core_news_sm'},
            'ar': {'name': 'Arabic', 'spacy_model': None},  # Limited spaCy support
            'hi': {'name': 'Hindi', 'spacy_model': None},
            'tr': {'name': 'Turkish', 'spacy_model': None}
        }
        
        # OCR language mappings
        self.ocr_language_mapping = {
            'en': 'eng',
            'es': 'spa',
            'fr': 'fra',
            'de': 'deu',
            'it': 'ita',
            'pt': 'por',
            'nl': 'nld',
            'zh': 'chi_sim',
            'ja': 'jpn',
            'ko': 'kor',
            'ru': 'rus',
            'ar': 'ara',
            'hi': 'hin',
            'tr': 'tur'
        }
        
        # Translation services
        self.translator = None
        self.translation_pipeline = None
        
        # Language models
        self.spacy_models = {}
        
        # Setup directories
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize language detection
        DetectorFactory.seed = 0
        
        # Initialize components
        self._initialize_language_models()
    
    def _initialize_language_models(self):
        """Initialize language detection and translation models"""
        
        try:
            # Initialize Google Translate if available
            if HAS_GOOGLETRANS:
                try:
                    self.translator = Translator()
                    self.logger.info("Google Translator initialized")
                except Exception as e:
                    self.logger.warning(f"Could not initialize Google Translator: {str(e)}")
                    self.translator = None
            
            # Initialize translation pipeline
            try:
                self.translation_pipeline = pipeline(
                    "translation",
                    model="Helsinki-NLP/opus-mt-mul-en",  # Multilingual to English
                    device=-1
                )
                self.logger.info("Translation pipeline initialized")
            except Exception as e:
                self.logger.warning(f"Could not initialize translation pipeline: {str(e)}")
                self.translation_pipeline = None
            
            # Download NLTK data for supported languages
            try:
                nltk.download('punkt', quiet=True)
                for lang_code in ['english', 'spanish', 'french', 'german', 'portuguese']:
                    try:
                        nltk.download(f'stopwords', quiet=True)
                    except:
                        pass
            except:
                pass
            
        except Exception as e:
            self.logger.error(f"Language model initialization failed: {str(e)}")
    
    def detect_language(self, text: str, options: Dict = None) -> Dict:
        """
        Detect the language of the given text
        """
        session_id = str(uuid.uuid4())
        options = options or {}
        
        try:
            self.logger.info(f"Detecting language (session: {session_id})")
            
            result = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'text_length': len(text),
                'detection_methods': {},
                'final_detection': {}
            }
            
            # Method 1: langdetect library
            langdetect_result = self._detect_with_langdetect(text)
            result['detection_methods']['langdetect'] = langdetect_result
            
            # Method 2: Character frequency analysis
            char_analysis_result = self._detect_with_char_analysis(text)
            result['detection_methods']['character_analysis'] = char_analysis_result
            
            # Method 3: Common words analysis
            word_analysis_result = self._detect_with_word_analysis(text)
            result['detection_methods']['word_analysis'] = word_analysis_result
            
            # Method 4: Script detection
            script_result = self._detect_script_type(text)
            result['detection_methods']['script_detection'] = script_result
            
            # Combine results
            final_detection = self._combine_language_detections(result['detection_methods'])
            result['final_detection'] = final_detection
            
            # Add language metadata
            if final_detection.get('language'):
                lang_code = final_detection['language']
                result['language_info'] = self._get_language_info(lang_code)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Language detection failed: {str(e)}")
            return {
                'session_id': session_id,
                'error': str(e),
                'success': False
            }
    
    def _detect_with_langdetect(self, text: str) -> Dict:
        """Detect language using langdetect library"""
        
        try:
            # Primary detection
            detected_lang = detect(text)
            
            # Get probabilities for multiple languages
            lang_probs = detect_langs(text)
            
            probabilities = {}
            for lang_prob in lang_probs:
                probabilities[lang_prob.lang] = lang_prob.prob
            
            return {
                'detected_language': detected_lang,
                'confidence': probabilities.get(detected_lang, 0),
                'probabilities': probabilities,
                'method': 'langdetect',
                'success': True
            }
            
        except langdetect.lang_detect_exception.LangDetectException as e:
            return {
                'error': str(e),
                'method': 'langdetect',
                'success': False
            }
        except Exception as e:
            return {
                'error': str(e),
                'method': 'langdetect',
                'success': False
            }
    
    def _detect_with_char_analysis(self, text: str) -> Dict:
        """Detect language based on character frequency analysis"""
        
        try:
            # Character frequency patterns for different languages
            char_patterns = {
                'en': {'common_chars': 'etaoinshrdlu', 'special_chars': set()},
                'es': {'common_chars': 'eaosrnidltuc', 'special_chars': {'ñ', 'á', 'é', 'í', 'ó', 'ú', 'ü'}},
                'fr': {'common_chars': 'esaitrnulod', 'special_chars': {'é', 'è', 'à', 'ç', 'ê', 'ë', 'î', 'ï', 'ô', 'ö', 'ù', 'û', 'ü', 'ÿ'}},
                'de': {'common_chars': 'enisratdhul', 'special_chars': {'ä', 'ö', 'ü', 'ß'}},
                'it': {'common_chars': 'eaiorntlsc', 'special_chars': {'à', 'è', 'é', 'ì', 'í', 'î', 'ò', 'ó', 'ù', 'ú'}},
                'pt': {'common_chars': 'eaosrindmt', 'special_chars': {'ã', 'á', 'à', 'â', 'é', 'ê', 'í', 'ó', 'ô', 'õ', 'ú', 'ç'}},
                'ru': {'common_chars': 'оеаитнсрв', 'special_chars': set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')},
                'ar': {'common_chars': 'الرينمت', 'special_chars': set('ابتثجحخدذرزسشصضطظعغفقكلمنهوي')},
                'zh': {'common_chars': '的一是了我不人在他', 'special_chars': set()}
            }
            
            # Clean text for analysis
            cleaned_text = re.sub(r'[^\w\s]', '', text.lower())
            
            scores = {}
            for lang, pattern in char_patterns.items():
                score = 0
                
                # Check special characters
                special_char_count = sum(1 for char in text if char in pattern['special_chars'])
                if special_char_count > 0:
                    score += special_char_count * 10
                
                # Check common character frequency
                for i, char in enumerate(pattern['common_chars'][:5]):
                    char_freq = cleaned_text.count(char)
                    score += char_freq * (5 - i)  # Weight early characters more
                
                scores[lang] = score
            
            # Normalize scores
            total_score = sum(scores.values())
            if total_score > 0:
                probabilities = {lang: score / total_score for lang, score in scores.items()}
            else:
                probabilities = scores
            
            # Get top detection
            if probabilities:
                detected_lang = max(probabilities.items(), key=lambda x: x[1])
                return {
                    'detected_language': detected_lang[0],
                    'confidence': detected_lang[1],
                    'probabilities': probabilities,
                    'method': 'character_analysis',
                    'success': True
                }
            else:
                return {
                    'detected_language': 'unknown',
                    'confidence': 0,
                    'method': 'character_analysis',
                    'success': False
                }
                
        except Exception as e:
            return {
                'error': str(e),
                'method': 'character_analysis',
                'success': False
            }
    
    def _detect_with_word_analysis(self, text: str) -> Dict:
        """Detect language based on common words"""
        
        try:
            # Common words for different languages
            common_words = {
                'en': ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our'],
                'es': ['que', 'de', 'no', 'a', 'la', 'el', 'es', 'y', 'en', 'lo', 'un', 'por', 'qué', 'me'],
                'fr': ['que', 'de', 'je', 'est', 'pas', 'le', 'vous', 'la', 'tu', 'il', 'et', 'à', 'un', 'ce'],
                'de': ['und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich', 'des', 'auf', 'für', 'ist', 'im', 'dem'],
                'it': ['che', 'per', 'una', 'in', 'con', 'il', 'da', 'su', 'un', 'la', 'di', 'e', 'a', 'sono'],
                'pt': ['que', 'de', 'não', 'o', 'a', 'para', 'uma', 'é', 'do', 'em', 'um', 'na', 'com', 'se'],
                'ru': ['в', 'и', 'не', 'на', 'я', 'с', 'то', 'что', 'он', 'как', 'по', 'это', 'она', 'за'],
                'zh': ['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '个', '上']
            }
            
            # Tokenize text
            words = re.findall(r'\w+', text.lower())
            word_count = len(words)
            
            if word_count == 0:
                return {
                    'detected_language': 'unknown',
                    'confidence': 0,
                    'method': 'word_analysis',
                    'success': False
                }
            
            scores = {}
            for lang, lang_words in common_words.items():
                matches = sum(1 for word in words if word in lang_words)
                scores[lang] = matches / word_count
            
            # Get top detection
            if scores:
                detected_lang = max(scores.items(), key=lambda x: x[1])
                return {
                    'detected_language': detected_lang[0],
                    'confidence': detected_lang[1],
                    'probabilities': scores,
                    'method': 'word_analysis',
                    'success': True
                }
            else:
                return {
                    'detected_language': 'unknown',
                    'confidence': 0,
                    'method': 'word_analysis',
                    'success': False
                }
                
        except Exception as e:
            return {
                'error': str(e),
                'method': 'word_analysis',
                'success': False
            }
    
    def _detect_script_type(self, text: str) -> Dict:
        """Detect script type (Latin, Cyrillic, Arabic, etc.)"""
        
        try:
            script_patterns = {
                'latin': r'[a-zA-ZÀ-ÿ]',
                'cyrillic': r'[а-яё]',
                'arabic': r'[ا-ي]',
                'chinese': r'[\u4e00-\u9fff]',
                'japanese': r'[\u3040-\u309f\u30a0-\u30ff]',
                'korean': r'[\uac00-\ud7af]',
                'devanagari': r'[\u0900-\u097f]'
            }
            
            script_counts = {}
            total_chars = 0
            
            for script, pattern in script_patterns.items():
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                script_counts[script] = matches
                total_chars += matches
            
            if total_chars == 0:
                return {
                    'detected_script': 'unknown',
                    'confidence': 0,
                    'method': 'script_detection',
                    'success': False
                }
            
            # Calculate probabilities
            probabilities = {script: count / total_chars for script, count in script_counts.items()}
            
            # Get dominant script
            detected_script = max(probabilities.items(), key=lambda x: x[1])
            
            # Map scripts to likely languages
            script_to_languages = {
                'latin': ['en', 'es', 'fr', 'de', 'it', 'pt', 'nl'],
                'cyrillic': ['ru'],
                'arabic': ['ar'],
                'chinese': ['zh'],
                'japanese': ['ja'],
                'korean': ['ko'],
                'devanagari': ['hi']
            }
            
            likely_languages = script_to_languages.get(detected_script[0], [])
            
            return {
                'detected_script': detected_script[0],
                'confidence': detected_script[1],
                'script_probabilities': probabilities,
                'likely_languages': likely_languages,
                'method': 'script_detection',
                'success': True
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'method': 'script_detection',
                'success': False
            }
    
    def _combine_language_detections(self, detection_methods: Dict) -> Dict:
        """Combine results from multiple detection methods"""
        
        # Collect all language predictions
        language_scores = {}
        total_weight = 0
        
        # Weight different methods
        method_weights = {
            'langdetect': 0.5,
            'character_analysis': 0.2,
            'word_analysis': 0.2,
            'script_detection': 0.1
        }
        
        for method, result in detection_methods.items():
            if not result.get('success', False):
                continue
            
            weight = method_weights.get(method, 0.1)
            
            if method == 'script_detection':
                # Use likely languages from script detection
                likely_langs = result.get('likely_languages', [])
                script_confidence = result.get('confidence', 0)
                
                for lang in likely_langs:
                    if lang not in language_scores:
                        language_scores[lang] = 0
                    language_scores[lang] += weight * script_confidence / len(likely_langs)
                
                total_weight += weight
                
            else:
                detected_lang = result.get('detected_language')
                confidence = result.get('confidence', 0)
                
                if detected_lang and detected_lang != 'unknown':
                    if detected_lang not in language_scores:
                        language_scores[detected_lang] = 0
                    
                    language_scores[detected_lang] += weight * confidence
                    total_weight += weight
        
        # Normalize scores
        if total_weight > 0:
            normalized_scores = {lang: score / total_weight for lang, score in language_scores.items()}
        else:
            normalized_scores = {}
        
        # Get final detection
        if normalized_scores:
            final_lang = max(normalized_scores.items(), key=lambda x: x[1])
            return {
                'language': final_lang[0],
                'confidence': final_lang[1],
                'all_probabilities': normalized_scores,
                'method': 'combined'
            }
        else:
            return {
                'language': 'unknown',
                'confidence': 0,
                'method': 'combined'
            }
    
    def _get_language_info(self, lang_code: str) -> Dict:
        """Get information about a detected language"""
        
        info = self.supported_languages.get(lang_code, {})
        
        return {
            'code': lang_code,
            'name': info.get('name', 'Unknown'),
            'spacy_model': info.get('spacy_model'),
            'ocr_code': self.ocr_language_mapping.get(lang_code),
            'is_supported': lang_code in self.supported_languages,
            'has_spacy_model': info.get('spacy_model') is not None,
            'writing_direction': self._get_writing_direction(lang_code),
            'character_set': self._get_character_set(lang_code)
        }
    
    def _get_writing_direction(self, lang_code: str) -> str:
        """Get writing direction for language"""
        
        rtl_languages = {'ar', 'he', 'fa', 'ur'}
        return 'rtl' if lang_code in rtl_languages else 'ltr'
    
    def _get_character_set(self, lang_code: str) -> str:
        """Get character set for language"""
        
        character_sets = {
            'en': 'latin', 'es': 'latin', 'fr': 'latin', 'de': 'latin',
            'it': 'latin', 'pt': 'latin', 'nl': 'latin',
            'ru': 'cyrillic',
            'ar': 'arabic',
            'zh': 'chinese',
            'ja': 'japanese',
            'ko': 'korean',
            'hi': 'devanagari'
        }
        
        return character_sets.get(lang_code, 'unknown')
    
    async def translate_text(self, text: str, target_language: str = 'en', source_language: str = None, options: Dict = None) -> Dict:
        """
        Translate text to target language
        """
        session_id = str(uuid.uuid4())
        options = options or {}
        
        try:
            self.logger.info(f"Translating text to {target_language} (session: {session_id})")
            
            result = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'source_text': text,
                'target_language': target_language,
                'source_language': source_language,
                'translations': {}
            }
            
            # Auto-detect source language if not provided
            if not source_language:
                detection_result = self.detect_language(text)
                if detection_result.get('final_detection', {}).get('language'):
                    source_language = detection_result['final_detection']['language']
                    result['auto_detected_language'] = source_language
                else:
                    source_language = 'auto'
            
            # Method 1: AI Orchestrator translation
            try:
                ai_translation = await self._translate_with_ai_orchestrator(
                    text, target_language, source_language, options
                )
                result['translations']['ai_orchestrator'] = ai_translation
            except Exception as e:
                self.logger.warning(f"AI orchestrator translation failed: {str(e)}")
                result['translations']['ai_orchestrator'] = {'error': str(e)}
            
            # Method 2: Google Translate (if available)
            if self.translator:
                try:
                    google_translation = self._translate_with_google(
                        text, target_language, source_language
                    )
                    result['translations']['google'] = google_translation
                except Exception as e:
                    self.logger.warning(f"Google translation failed: {str(e)}")
                    result['translations']['google'] = {'error': str(e)}
            
            # Method 3: Hugging Face translation pipeline
            if self.translation_pipeline:
                try:
                    hf_translation = self._translate_with_huggingface(
                        text, target_language, source_language
                    )
                    result['translations']['huggingface'] = hf_translation
                except Exception as e:
                    self.logger.warning(f"Hugging Face translation failed: {str(e)}")
                    result['translations']['huggingface'] = {'error': str(e)}
            
            # Select best translation
            best_translation = self._select_best_translation(result['translations'])
            result['best_translation'] = best_translation
            
            return result
            
        except Exception as e:
            self.logger.error(f"Translation failed: {str(e)}")
            return {
                'session_id': session_id,
                'error': str(e),
                'success': False
            }
    
    async def _translate_with_ai_orchestrator(self, text: str, target_lang: str, source_lang: str, options: Dict) -> Dict:
        """Translate using AI orchestrator"""
        
        try:
            prompt = f"Translate the following text from {source_lang} to {target_lang}. Provide only the translation without any additional text:\n\n{text}"
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    'provider': options.get('ai_provider', 'openai'),
                    'model': options.get('ai_model', 'gpt-3.5-turbo'),
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': len(text) * 2,  # Allow for translation expansion
                    'temperature': 0.1  # Low temperature for consistent translation
                }
                
                async with session.post(
                    f'{self.ai_orchestrator_url}/process',
                    json=payload,
                    timeout=120
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        translated_text = result['choices'][0]['message']['content'].strip()
                        
                        return {
                            'translated_text': translated_text,
                            'method': 'ai_orchestrator',
                            'provider': payload['provider'],
                            'model': payload['model'],
                            'confidence': 0.8,
                            'success': True
                        }
                    else:
                        raise Exception(f"AI service returned status {response.status}")
        
        except Exception as e:
            raise Exception(f"AI orchestrator translation failed: {str(e)}")
    
    def _translate_with_google(self, text: str, target_lang: str, source_lang: str) -> Dict:
        """Translate using Google Translate"""
        
        try:
            if source_lang == 'auto':
                result = self.translator.translate(text, dest=target_lang)
                detected_lang = result.src
            else:
                result = self.translator.translate(text, src=source_lang, dest=target_lang)
                detected_lang = source_lang
            
            return {
                'translated_text': result.text,
                'method': 'google',
                'detected_source_language': detected_lang,
                'confidence': 0.9,  # Google Translate is generally reliable
                'success': True
            }
            
        except Exception as e:
            raise Exception(f"Google translation failed: {str(e)}")
    
    def _translate_with_huggingface(self, text: str, target_lang: str, source_lang: str) -> Dict:
        """Translate using Hugging Face pipeline"""
        
        try:
            # The model we initialized is multilingual to English
            # For other target languages, we'd need different models
            if target_lang != 'en':
                raise Exception("Hugging Face pipeline only supports translation to English")
            
            # Split text into chunks if too long
            max_length = 512
            if len(text) > max_length:
                chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
                translated_chunks = []
                
                for chunk in chunks:
                    if chunk.strip():
                        result = self.translation_pipeline(chunk)
                        translated_chunks.append(result[0]['translation_text'])
                
                translated_text = ' '.join(translated_chunks)
            else:
                result = self.translation_pipeline(text)
                translated_text = result[0]['translation_text']
            
            return {
                'translated_text': translated_text,
                'method': 'huggingface',
                'model': 'Helsinki-NLP/opus-mt-mul-en',
                'confidence': 0.7,
                'success': True
            }
            
        except Exception as e:
            raise Exception(f"Hugging Face translation failed: {str(e)}")
    
    def _select_best_translation(self, translations: Dict) -> Dict:
        """Select the best translation from available options"""
        
        # Priority order for translation methods
        method_priority = ['ai_orchestrator', 'google', 'huggingface']
        
        for method in method_priority:
            if method in translations and translations[method].get('success', False):
                translation = translations[method]
                translation['selected_method'] = method
                return translation
        
        # If no successful translation found
        return {
            'translated_text': '',
            'method': 'none',
            'confidence': 0,
            'success': False,
            'error': 'No successful translation method available'
        }
    
    def get_language_specific_config(self, language: str) -> Dict:
        """Get language-specific configuration for processing"""
        
        config = {
            'language': language,
            'ocr_language': self.ocr_language_mapping.get(language, 'eng'),
            'spacy_model': None,
            'stopwords': [],
            'writing_direction': self._get_writing_direction(language),
            'character_set': self._get_character_set(language)
        }
        
        # Get spaCy model if available
        lang_info = self.supported_languages.get(language, {})
        spacy_model_name = lang_info.get('spacy_model')
        
        if spacy_model_name:
            try:
                if spacy_model_name not in self.spacy_models:
                    self.spacy_models[spacy_model_name] = spacy.load(spacy_model_name)
                config['spacy_model'] = self.spacy_models[spacy_model_name]
            except OSError:
                self.logger.warning(f"spaCy model {spacy_model_name} not found")
                config['spacy_model'] = None
        
        # Get stopwords if available
        try:
            language_names = {
                'en': 'english', 'es': 'spanish', 'fr': 'french', 
                'de': 'german', 'pt': 'portuguese', 'it': 'italian',
                'nl': 'dutch', 'ru': 'russian', 'ar': 'arabic'
            }
            
            nltk_lang = language_names.get(language)
            if nltk_lang:
                config['stopwords'] = stopwords.words(nltk_lang)
        except:
            config['stopwords'] = []
        
        return config
    
    def create_multilingual_summary(self, text: str, target_languages: List[str], options: Dict = None) -> Dict:
        """Create summaries in multiple languages"""
        
        session_id = str(uuid.uuid4())
        options = options or {}
        
        result = {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'source_text_length': len(text),
            'target_languages': target_languages,
            'summaries': {}
        }
        
        try:
            # First, create summary in source language (or English)
            source_summary_prompt = f"Create a concise summary of the following text:\n\n{text[:2000]}"
            
            # Get source summary
            # This would integrate with the document summarizer
            source_summary = "This is a placeholder summary that would be generated by the document summarizer."
            
            # Translate summary to target languages
            for target_lang in target_languages:
                try:
                    translation_result = self.translate_text(
                        source_summary, 
                        target_lang, 
                        options=options
                    )
                    
                    if translation_result.get('best_translation', {}).get('success', False):
                        result['summaries'][target_lang] = {
                            'summary': translation_result['best_translation']['translated_text'],
                            'translation_method': translation_result['best_translation']['method'],
                            'confidence': translation_result['best_translation']['confidence']
                        }
                    else:
                        result['summaries'][target_lang] = {
                            'error': 'Translation failed',
                            'summary': ''
                        }
                        
                except Exception as e:
                    result['summaries'][target_lang] = {
                        'error': str(e),
                        'summary': ''
                    }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Multilingual summary creation failed: {str(e)}")
            result['error'] = str(e)
            return result
    
    def save_language_results(self, results: Dict):
        """Save language processing results"""
        
        try:
            session_id = results['session_id']
            output_file = os.path.join(self.output_dir, f"language_results_{session_id}.json")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Language results saved to {output_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save language results: {str(e)}")

def main():
    """Command line interface for language support"""
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description='Language detection and translation')
    parser.add_argument('text', help='Text to process or file path')
    parser.add_argument('--action', choices=['detect', 'translate'], default='detect', help='Action to perform')
    parser.add_argument('--target-language', default='en', help='Target language for translation')
    parser.add_argument('--source-language', help='Source language (auto-detect if not specified)')
    parser.add_argument('--output-dir', default='./output/language', help='Output directory')
    parser.add_argument('--file', action='store_true', help='Input is a file path')
    
    args = parser.parse_args()
    
    # Configure language support
    config = {
        'output_dir': args.output_dir
    }
    
    # Get text
    if args.file:
        with open(args.text, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = args.text
    
    # Process
    lang_support = LanguageSupport(config)
    
    async def run_processing():
        if args.action == 'detect':
            result = lang_support.detect_language(text)
            
            if 'final_detection' in result:
                detection = result['final_detection']
                print(f"✓ Language detected")
                print(f"  Language: {detection.get('language', 'unknown')}")
                print(f"  Confidence: {detection.get('confidence', 0):.3f}")
                print(f"  Session ID: {result['session_id']}")
                
                if 'language_info' in result:
                    info = result['language_info']
                    print(f"  Language name: {info.get('name', 'Unknown')}")
                    print(f"  Writing direction: {info.get('writing_direction', 'unknown')}")
                    print(f"  Has spaCy model: {info.get('has_spacy_model', False)}")
            else:
                print(f"✗ Language detection failed: {result.get('error', 'Unknown error')}")
        
        elif args.action == 'translate':
            result = await lang_support.translate_text(
                text, 
                args.target_language, 
                args.source_language
            )
            
            if 'best_translation' in result and result['best_translation'].get('success', False):
                translation = result['best_translation']
                print(f"✓ Translation completed")
                print(f"  Method: {translation.get('method', 'unknown')}")
                print(f"  Confidence: {translation.get('confidence', 0):.3f}")
                print(f"  Translation: {translation.get('translated_text', '')[:200]}...")
                print(f"  Session ID: {result['session_id']}")
            else:
                print(f"✗ Translation failed: {result.get('error', 'Unknown error')}")
    
    asyncio.run(run_processing())

if __name__ == '__main__':
    main()