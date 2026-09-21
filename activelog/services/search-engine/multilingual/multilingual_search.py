#!/usr/bin/env python3
"""
ActiveLog Unified Search Engine - Multilingual Search
Cross-lingual search with language detection and translation
"""

import asyncio
import json
import logging
import time
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class LanguageDetectionResult:
    """Language detection result"""
    language: str
    confidence: float
    alternatives: List[Tuple[str, float]] = None
    
    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []

@dataclass
class TranslationResult:
    """Translation result"""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    confidence: float = 1.0
    translator: str = "mock"

class MockLanguageDetector:
    """Mock language detector for demonstration"""
    
    def __init__(self):
        # Common words by language for basic detection
        self.language_patterns = {
            'en': {
                'common_words': {'the', 'and', 'of', 'to', 'a', 'in', 'is', 'it', 'you', 'that'},
                'patterns': [r'\bthe\b', r'\band\b', r'\bis\b', r'\bare\b']
            },
            'es': {
                'common_words': {'el', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no'},
                'patterns': [r'\bel\b', r'\bde\b', r'\bque\b', r'\ben\b']
            },
            'fr': {
                'common_words': {'le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir'},
                'patterns': [r'\ble\b', r'\bde\b', r'\bet\b', r'\ben\b']
            },
            'de': {
                'common_words': {'der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich'},
                'patterns': [r'\bder\b', r'\bdie\b', r'\bund\b', r'\bdas\b']
            },
            'it': {
                'common_words': {'il', 'di', 'che', 'e', 'la', 'per', 'un', 'in', 'con', 'del'},
                'patterns': [r'\bil\b', r'\bdi\b', r'\bche\b', r'\bper\b']
            },
            'pt': {
                'common_words': {'o', 'de', 'a', 'e', 'do', 'da', 'em', 'um', 'para', 'é'},
                'patterns': [r'\bde\b', r'\bem\b', r'\bpara\b', r'\bcom\b']
            },
            'ru': {
                'common_words': {'в', 'и', 'не', 'на', 'я', 'быть', 'он', 'с', 'что', 'а'},
                'patterns': [r'\bв\b', r'\bи\b', r'\bне\b', r'\bна\b']
            },
            'ja': {
                'common_words': {'の', 'に', 'を', 'は', 'が', 'で', 'た', 'と', 'て', 'だ'},
                'patterns': [r'の', r'に', r'を', r'は', r'が']
            },
            'zh': {
                'common_words': {'的', '了', '和', '是', '在', '我', '有', '他', '这', '为'},
                'patterns': [r'的', r'了', r'和', r'是', r'在']
            }
        }
    
    def detect(self, text: str) -> LanguageDetectionResult:
        """Detect language of text"""
        if not text.strip():
            return LanguageDetectionResult('en', 0.1)
        
        text_lower = text.lower()
        language_scores = {}
        
        # Score based on common words
        for lang, info in self.language_patterns.items():
            score = 0
            words = set(re.findall(r'\b\w+\b', text_lower))
            common_found = words.intersection(info['common_words'])
            score += len(common_found) * 2
            
            # Score based on patterns
            for pattern in info['patterns']:
                matches = len(re.findall(pattern, text_lower))
                score += matches
            
            if score > 0:
                language_scores[lang] = score / len(text.split())
        
        if not language_scores:
            return LanguageDetectionResult('en', 0.5)  # Default to English
        
        # Get best match
        best_lang = max(language_scores, key=language_scores.get)
        confidence = min(language_scores[best_lang], 1.0)
        
        # Get alternatives
        sorted_scores = sorted(language_scores.items(), key=lambda x: x[1], reverse=True)
        alternatives = [(lang, score) for lang, score in sorted_scores[1:4]]
        
        return LanguageDetectionResult(
            language=best_lang,
            confidence=confidence,
            alternatives=alternatives
        )
    
    def detect_batch(self, texts: List[str]) -> List[LanguageDetectionResult]:
        """Detect language for multiple texts"""
        return [self.detect(text) for text in texts]

class MockTranslator:
    """Mock translator for demonstration"""
    
    def __init__(self):
        # Mock translations for common terms
        self.mock_translations = {
            ('es', 'en'): {
                'hola': 'hello',
                'mundo': 'world',
                'buscar': 'search',
                'documento': 'document',
                'archivo': 'file',
                'imagen': 'image',
                'correo': 'email',
                'mensaje': 'message',
                'tarea': 'task',
                'nota': 'note'
            },
            ('fr', 'en'): {
                'bonjour': 'hello',
                'monde': 'world',
                'chercher': 'search',
                'document': 'document',
                'fichier': 'file',
                'image': 'image',
                'courriel': 'email',
                'message': 'message',
                'tâche': 'task',
                'note': 'note'
            },
            ('de', 'en'): {
                'hallo': 'hello',
                'welt': 'world',
                'suchen': 'search',
                'dokument': 'document',
                'datei': 'file',
                'bild': 'image',
                'email': 'email',
                'nachricht': 'message',
                'aufgabe': 'task',
                'notiz': 'note'
            }
        }
    
    def translate(self, text: str, source_lang: str, target_lang: str = 'en') -> TranslationResult:
        """Translate text from source language to target language"""
        if source_lang == target_lang:
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=source_lang,
                target_language=target_lang,
                confidence=1.0
            )
        
        # Check for mock translations
        translation_dict = self.mock_translations.get((source_lang, target_lang), {})
        
        if not translation_dict:
            # No translation available, return original
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=source_lang,
                target_language=target_lang,
                confidence=0.1
            )
        
        # Simple word-by-word translation for demo
        words = text.lower().split()
        translated_words = []
        
        for word in words:
            # Remove punctuation for lookup
            clean_word = re.sub(r'[^\w]', '', word)
            translated_word = translation_dict.get(clean_word, word)
            translated_words.append(translated_word)
        
        translated_text = ' '.join(translated_words)
        
        # Calculate confidence based on how many words were translated
        translated_count = sum(1 for word in words if re.sub(r'[^\w]', '', word.lower()) in translation_dict)
        confidence = translated_count / len(words) if words else 0.1
        
        return TranslationResult(
            original_text=text,
            translated_text=translated_text,
            source_language=source_lang,
            target_language=target_lang,
            confidence=confidence
        )
    
    def translate_batch(self, texts: List[str], source_lang: str, target_lang: str = 'en') -> List[TranslationResult]:
        """Translate multiple texts"""
        return [self.translate(text, source_lang, target_lang) for text in texts]

class CrossLingualQueryExpander:
    """Expand queries across multiple languages"""
    
    def __init__(self, translator: MockTranslator):
        self.translator = translator
        
        # Supported language pairs for expansion
        self.expansion_languages = ['en', 'es', 'fr', 'de', 'it', 'pt']
        
        # Query expansion cache
        self.expansion_cache = {}
    
    def expand_query(self, query: str, source_language: str) -> Dict[str, str]:
        """Expand query to multiple languages"""
        # Check cache
        cache_key = f"{source_language}:{query}"
        if cache_key in self.expansion_cache:
            return self.expansion_cache[cache_key]
        
        expanded_queries = {source_language: query}
        
        # Translate to other languages
        for target_lang in self.expansion_languages:
            if target_lang != source_language:
                translation = self.translator.translate(query, source_language, target_lang)
                if translation.confidence > 0.3:  # Only use confident translations
                    expanded_queries[target_lang] = translation.translated_text
        
        # Cache the result
        self.expansion_cache[cache_key] = expanded_queries
        
        return expanded_queries
    
    def expand_terms(self, terms: List[str], source_language: str) -> Dict[str, List[str]]:
        """Expand individual terms to multiple languages"""
        expanded_terms = {source_language: terms}
        
        for target_lang in self.expansion_languages:
            if target_lang != source_language:
                translated_terms = []
                for term in terms:
                    translation = self.translator.translate(term, source_language, target_lang)
                    if translation.confidence > 0.3:
                        translated_terms.append(translation.translated_text)
                    else:
                        translated_terms.append(term)  # Keep original if translation uncertain
                
                expanded_terms[target_lang] = translated_terms
        
        return expanded_terms

class MultilingualIndex:
    """Multilingual search index"""
    
    def __init__(self):
        # Language-specific indexes
        self.language_indexes: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        
        # Cross-language mapping
        self.translation_map: Dict[str, Dict[str, str]] = defaultdict(dict)  # term -> {lang: translated_term}
        
        # Document language mapping
        self.document_languages: Dict[str, str] = {}
        
        # Statistics
        self.language_stats = Counter()
    
    def add_document(self, document_id: str, content: str, language: str):
        """Add document to multilingual index"""
        # Store document language
        self.document_languages[document_id] = language
        self.language_stats[language] += 1
        
        # Tokenize content
        terms = self._tokenize(content)
        
        # Add to language-specific index
        for term in terms:
            self.language_indexes[language][term].add(document_id)
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text (language-agnostic)"""
        # Basic tokenization that works across languages
        tokens = re.findall(r'\b\w+\b', text.lower())
        return [token for token in tokens if len(token) > 2]
    
    def search_multilingual(self, terms: Dict[str, List[str]]) -> Dict[str, List[Tuple[str, float]]]:
        """Search across multiple languages"""
        results_by_language = {}
        
        for language, lang_terms in terms.items():
            if language in self.language_indexes:
                results = self._search_language(lang_terms, language)
                if results:
                    results_by_language[language] = results
        
        return results_by_language
    
    def _search_language(self, terms: List[str], language: str) -> List[Tuple[str, float]]:
        """Search within a specific language index"""
        document_scores = defaultdict(float)
        lang_index = self.language_indexes[language]
        
        for term in terms:
            if term in lang_index:
                document_ids = lang_index[term]
                for doc_id in document_ids:
                    document_scores[doc_id] += 1.0
        
        # Normalize by number of terms
        if terms:
            for doc_id in document_scores:
                document_scores[doc_id] /= len(terms)
        
        # Sort by score
        results = sorted(document_scores.items(), key=lambda x: x[1], reverse=True)
        return results
    
    def get_language_stats(self) -> Dict[str, Any]:
        """Get language distribution statistics"""
        total_docs = sum(self.language_stats.values())
        
        return {
            'total_documents': total_docs,
            'languages': dict(self.language_stats),
            'language_percentages': {
                lang: (count / total_docs) * 100 
                for lang, count in self.language_stats.items()
            } if total_docs > 0 else {}
        }

class MultilingualSearchEngine:
    """Main multilingual search engine"""
    
    def __init__(self):
        # Core components
        self.language_detector = MockLanguageDetector()
        self.translator = MockTranslator()
        self.query_expander = CrossLingualQueryExpander(self.translator)
        self.multilingual_index = MultilingualIndex()
        
        # Configuration
        self.config = {
            'auto_detect_language': True,
            'expand_queries': True,
            'translate_results': True,
            'confidence_threshold': 0.3,
            'max_languages': 5
        }
        
        # Statistics
        self.stats = {
            'queries_processed': 0,
            'languages_detected': Counter(),
            'translations_performed': 0,
            'cross_lingual_matches': 0,
            'avg_processing_time_ms': 0
        }
    
    async def search(self, query, target_language: str = 'en', limit: int = 50) -> List[Tuple[str, float]]:
        """Perform multilingual search"""
        start_time = time.time()
        
        try:
            # Handle different query types
            if hasattr(query, 'query'):
                query_text = query.query
            else:
                query_text = str(query)
            
            # Detect query language
            if self.config['auto_detect_language']:
                detection_result = self.language_detector.detect(query_text)
                source_language = detection_result.language
                logger.debug(f"Detected query language: {source_language} (confidence: {detection_result.confidence})")
            else:
                source_language = target_language
            
            self.stats['languages_detected'][source_language] += 1
            
            # Expand query to multiple languages
            if self.config['expand_queries']:
                expanded_queries = self.query_expander.expand_query(query_text, source_language)
                
                # Convert to term expansions
                expanded_terms = {}
                for lang, lang_query in expanded_queries.items():
                    terms = self._tokenize(lang_query)
                    expanded_terms[lang] = terms
            else:
                # Single language search
                terms = self._tokenize(query_text)
                expanded_terms = {source_language: terms}
            
            # Search multilingual index
            results_by_language = self.multilingual_index.search_multilingual(expanded_terms)
            
            # Combine results from all languages
            combined_results = self._combine_multilingual_results(results_by_language, source_language)
            
            # Update statistics
            processing_time = (time.time() - start_time) * 1000
            self.stats['queries_processed'] += 1
            
            if len(results_by_language) > 1:
                self.stats['cross_lingual_matches'] += 1
            
            # Update average processing time
            current_avg = self.stats['avg_processing_time_ms']
            total_queries = self.stats['queries_processed']
            self.stats['avg_processing_time_ms'] = ((current_avg * (total_queries - 1)) + processing_time) / total_queries
            
            return combined_results[:limit]
            
        except Exception as e:
            logger.error(f"Multilingual search error: {e}")
            return []
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for search"""
        return self.multilingual_index._tokenize(text)
    
    def _combine_multilingual_results(self, results_by_language: Dict[str, List[Tuple[str, float]]], 
                                    source_language: str) -> List[Tuple[str, float]]:
        """Combine results from multiple languages"""
        combined_scores = defaultdict(float)
        
        # Weight results by language relevance
        language_weights = {
            source_language: 1.0,  # Highest weight for source language
        }
        
        # Lower weights for other languages
        for lang in results_by_language.keys():
            if lang not in language_weights:
                language_weights[lang] = 0.7
        
        # Combine results with weighting
        for language, results in results_by_language.items():
            weight = language_weights.get(language, 0.5)
            
            for doc_id, score in results:
                # Boost score if document is in same language as query
                doc_language = self.multilingual_index.document_languages.get(doc_id, 'en')
                if doc_language == source_language:
                    weight *= 1.2
                
                combined_scores[doc_id] += score * weight
        
        # Sort by combined score
        sorted_results = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results
    
    def add_document(self, document_id: str, content: str, title: str = "", 
                    language: str = None) -> str:
        """Add document to multilingual index"""
        # Combine title and content
        full_text = f"{title} {content}".strip()
        
        # Detect language if not provided
        if language is None:
            detection_result = self.language_detector.detect(full_text)
            language = detection_result.language
        
        # Add to index
        self.multilingual_index.add_document(document_id, full_text, language)
        
        return language
    
    def translate_text(self, text: str, source_language: str, target_language: str = 'en') -> TranslationResult:
        """Translate text between languages"""
        self.stats['translations_performed'] += 1
        return self.translator.translate(text, source_language, target_language)
    
    def detect_language(self, text: str) -> LanguageDetectionResult:
        """Detect language of text"""
        return self.language_detector.detect(text)
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return self.query_expander.expansion_languages
    
    def configure(self, **config):
        """Update multilingual search configuration"""
        self.config.update(config)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get multilingual search statistics"""
        return {
            **self.stats,
            'languages_detected': dict(self.stats['languages_detected']),
            'index_stats': self.multilingual_index.get_language_stats(),
            'supported_languages': self.get_supported_languages(),
            'configuration': self.config
        }
    
    async def cross_lingual_similarity(self, text1: str, text2: str, 
                                     lang1: str = None, lang2: str = None) -> float:
        """Calculate similarity between texts in different languages"""
        # Detect languages if not provided
        if lang1 is None:
            detection1 = self.language_detector.detect(text1)
            lang1 = detection1.language
        
        if lang2 is None:
            detection2 = self.language_detector.detect(text2)
            lang2 = detection2.language
        
        # If same language, use direct comparison
        if lang1 == lang2:
            # Simple token overlap similarity
            tokens1 = set(self._tokenize(text1))
            tokens2 = set(self._tokenize(text2))
            
            if not tokens1 or not tokens2:
                return 0.0
            
            intersection = len(tokens1.intersection(tokens2))
            union = len(tokens1.union(tokens2))
            
            return intersection / union if union > 0 else 0.0
        
        # Translate both to English for comparison
        if lang1 != 'en':
            translation1 = self.translator.translate(text1, lang1, 'en')
            text1_en = translation1.translated_text
        else:
            text1_en = text1
        
        if lang2 != 'en':
            translation2 = self.translator.translate(text2, lang2, 'en')
            text2_en = translation2.translated_text
        else:
            text2_en = text2
        
        # Calculate similarity on translated texts
        tokens1 = set(self._tokenize(text1_en))
        tokens2 = set(self._tokenize(text2_en))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return intersection / union if union > 0 else 0.0