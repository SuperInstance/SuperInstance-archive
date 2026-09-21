#!/usr/bin/env python3
"""
Intelligent Data Classifier for ActiveLog
Advanced AI-powered classification using machine learning and pattern recognition
"""

import asyncio
import json
import logging
import re
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import numpy as np
from enum import Enum
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ClassificationFeatures:
    """Features extracted for classification"""
    # File-based features
    filename: Optional[str] = None
    file_extension: Optional[str] = None
    file_size: int = 0
    mime_type: Optional[str] = None
    
    # Content-based features
    content_type: str = "unknown"
    text_length: int = 0
    word_count: int = 0
    line_count: int = 0
    character_distribution: Dict[str, float] = None
    
    # Semantic features
    language: Optional[str] = None
    topics: List[str] = None
    entities: List[str] = None
    sentiment: Optional[float] = None
    
    # Temporal features
    creation_time: Optional[datetime] = None
    modification_time: Optional[datetime] = None
    time_of_day: Optional[str] = None
    day_of_week: Optional[str] = None
    
    # Contextual features
    source_platform: Optional[str] = None
    user_activity: Optional[str] = None
    location_context: Optional[str] = None
    
    # Binary signatures
    file_signature: Optional[str] = None
    content_hash: Optional[str] = None

@dataclass
class ClassificationResult:
    """Result of data classification"""
    primary_type: str
    secondary_type: Optional[str] = None
    confidence: float = 0.0
    features_used: List[str] = None
    reasoning: str = ""
    suggested_processors: List[str] = None
    metadata_enrichment: Dict[str, Any] = None
    quality_score: float = 0.0
    
class FeatureExtractor:
    """Extract features from data for classification"""
    
    def __init__(self):
        self.binary_signatures = self._load_binary_signatures()
        self.text_patterns = self._load_text_patterns()
        
    def _load_binary_signatures(self) -> Dict[str, Tuple[bytes, str, float]]:
        """Load binary file signatures for classification"""
        return {
            # Images
            'jpeg': (b'\xFF\xD8\xFF', 'image/jpeg', 0.95),
            'png': (b'\x89PNG\r\n\x1a\n', 'image/png', 0.95),
            'gif87': (b'GIF87a', 'image/gif', 0.95),
            'gif89': (b'GIF89a', 'image/gif', 0.95),
            'webp': (b'RIFF....WEBP', 'image/webp', 0.9),
            'bmp': (b'BM', 'image/bmp', 0.9),
            'tiff': (b'II*\x00', 'image/tiff', 0.9),
            'tiff_be': (b'MM\x00*', 'image/tiff', 0.9),
            
            # Videos
            'mp4': (b'\x00\x00\x00\x18ftypmp4', 'video/mp4', 0.95),
            'avi': (b'RIFF....AVI ', 'video/avi', 0.9),
            'mov': (b'\x00\x00\x00\x14ftypqt  ', 'video/quicktime', 0.9),
            'wmv': (b'\x30\x26\xB2\x75\x8E\x66\xCF\x11', 'video/x-ms-wmv', 0.9),
            'flv': (b'FLV\x01', 'video/x-flv', 0.9),
            'webm': (b'\x1A\x45\xDF\xA3', 'video/webm', 0.85),
            
            # Audio
            'mp3': (b'ID3', 'audio/mpeg', 0.9),
            'mp3_alt': (b'\xFF\xFB', 'audio/mpeg', 0.8),
            'wav': (b'RIFF....WAVE', 'audio/wav', 0.95),
            'flac': (b'fLaC', 'audio/flac', 0.95),
            'ogg': (b'OggS', 'audio/ogg', 0.9),
            'aac': (b'\xFF\xF1', 'audio/aac', 0.8),
            'm4a': (b'\x00\x00\x00\x20ftypM4A ', 'audio/mp4', 0.9),
            
            # Documents
            'pdf': (b'%PDF', 'application/pdf', 0.95),
            'doc': (b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1', 'application/msword', 0.8),
            'docx': (b'PK\x03\x04', 'application/vnd.openxmlformats-officedocument', 0.7),
            'rtf': (b'{\\rtf', 'application/rtf', 0.9),
            'ps': (b'%!PS-Adobe', 'application/postscript', 0.9),
            
            # Archives
            'zip': (b'PK\x03\x04', 'application/zip', 0.8),
            'rar': (b'Rar!\x1a\x07\x00', 'application/x-rar-compressed', 0.95),
            'tar': (b'ustar\x00\x00', 'application/x-tar', 0.9),
            'gzip': (b'\x1f\x8b', 'application/gzip', 0.9),
            '7z': (b'7z\xBC\xAF\x27\x1C', 'application/x-7z-compressed', 0.95),
            
            # Executables
            'exe': (b'MZ', 'application/x-msdownload', 0.9),
            'elf': (b'\x7fELF', 'application/x-executable', 0.95),
            'mach_o': (b'\xFE\xED\xFA\xCE', 'application/x-mach-binary', 0.9),
        }
    
    def _load_text_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load text patterns for content classification"""
        return {
            'programming_languages': [
                {'pattern': r'^\s*#include\s*<.*>', 'language': 'c', 'confidence': 0.8},
                {'pattern': r'^\s*import\s+\w+', 'language': 'python', 'confidence': 0.7},
                {'pattern': r'^\s*function\s+\w+\s*\(', 'language': 'javascript', 'confidence': 0.7},
                {'pattern': r'^\s*public\s+class\s+\w+', 'language': 'java', 'confidence': 0.8},
                {'pattern': r'^\s*<?php', 'language': 'php', 'confidence': 0.9},
                {'pattern': r'^\s*SELECT\s+.*\s+FROM\s+', 'language': 'sql', 'confidence': 0.8},
                {'pattern': r'^\s*<!DOCTYPE\s+html', 'language': 'html', 'confidence': 0.9},
                {'pattern': r'^\s*\{\s*".*":\s*', 'language': 'json', 'confidence': 0.8},
            ],
            'log_formats': [
                {'pattern': r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}.*ERROR', 'type': 'error_log', 'confidence': 0.9},
                {'pattern': r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}.*INFO', 'type': 'info_log', 'confidence': 0.8},
                {'pattern': r'\[.*\]\s+(ERROR|WARN|INFO|DEBUG)', 'type': 'application_log', 'confidence': 0.8},
                {'pattern': r'\d+\.\d+\.\d+\.\d+.*GET|POST|PUT|DELETE', 'type': 'access_log', 'confidence': 0.9},
            ],
            'data_formats': [
                {'pattern': r'^[^,\n]*,[^,\n]*,', 'type': 'csv', 'confidence': 0.7},
                {'pattern': r'^\s*\{.*\}\s*$', 'type': 'json_object', 'confidence': 0.8},
                {'pattern': r'^\s*\[.*\]\s*$', 'type': 'json_array', 'confidence': 0.8},
                {'pattern': r'<\?xml\s+version.*\?>', 'type': 'xml', 'confidence': 0.9},
                {'pattern': r'^\w+:\s*.*', 'type': 'yaml', 'confidence': 0.6},
            ],
            'communication': [
                {'pattern': r'From:.*To:.*Subject:', 'type': 'email', 'confidence': 0.9},
                {'pattern': r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}.*:', 'type': 'chat_message', 'confidence': 0.7},
                {'pattern': r'@\w+', 'type': 'social_media', 'confidence': 0.6},
            ]
        }
    
    async def extract_features(self, content: Any, metadata: Dict[str, Any] = None) -> ClassificationFeatures:
        """Extract comprehensive features from data"""
        features = ClassificationFeatures()
        metadata = metadata or {}
        
        # Extract file-based features
        if 'filename' in metadata:
            features.filename = metadata['filename']
            features.file_extension = Path(features.filename).suffix.lower().lstrip('.')
        
        if 'mime_type' in metadata:
            features.mime_type = metadata['mime_type']
        
        # Calculate content size
        features.file_size = self._calculate_size(content)
        
        # Extract content-based features
        if isinstance(content, str):
            await self._extract_text_features(content, features)
        elif isinstance(content, bytes):
            await self._extract_binary_features(content, features)
        elif isinstance(content, (dict, list)):
            await self._extract_structured_features(content, features)
        
        # Extract temporal features
        if 'created_at' in metadata:
            features.creation_time = metadata['created_at']
            if isinstance(features.creation_time, str):
                features.creation_time = datetime.fromisoformat(features.creation_time.replace('Z', '+00:00'))
        
        if features.creation_time:
            features.time_of_day = self._get_time_of_day(features.creation_time)
            features.day_of_week = features.creation_time.strftime('%A')
        
        # Extract contextual features
        features.source_platform = metadata.get('source', '').lower()
        
        # Generate content hash
        features.content_hash = self._calculate_content_hash(content)
        
        return features
    
    async def _extract_text_features(self, content: str, features: ClassificationFeatures):
        """Extract features from text content"""
        features.content_type = "text"
        features.text_length = len(content)
        features.word_count = len(content.split())
        features.line_count = len(content.split('\n'))
        
        # Character distribution analysis
        total_chars = len(content)
        if total_chars > 0:
            features.character_distribution = {
                'alphabetic': sum(1 for c in content if c.isalpha()) / total_chars,
                'numeric': sum(1 for c in content if c.isdigit()) / total_chars,
                'whitespace': sum(1 for c in content if c.isspace()) / total_chars,
                'punctuation': sum(1 for c in content if c in '.,!?;:') / total_chars,
                'special': sum(1 for c in content if not c.isalnum() and not c.isspace()) / total_chars
            }
        
        # Language detection (simplified)
        features.language = await self._detect_language(content)
        
        # Topic extraction (simplified)
        features.topics = await self._extract_topics(content)
        
        # Entity extraction (simplified)
        features.entities = await self._extract_entities(content)
        
        # Sentiment analysis (simplified)
        features.sentiment = await self._analyze_sentiment(content)
    
    async def _extract_binary_features(self, content: bytes, features: ClassificationFeatures):
        """Extract features from binary content"""
        features.content_type = "binary"
        
        # Check binary signatures
        for sig_name, (signature, mime_type, confidence) in self.binary_signatures.items():
            if signature.count(b'.') > 0:  # Handle wildcards
                pattern = signature.replace(b'....', b'.{4}')
                if re.match(pattern, content):
                    features.file_signature = sig_name
                    features.mime_type = features.mime_type or mime_type
                    break
            elif content.startswith(signature):
                features.file_signature = sig_name
                features.mime_type = features.mime_type or mime_type
                break
        
        # Analyze byte distribution
        if len(content) > 0:
            byte_counts = np.bincount(content, minlength=256)
            entropy = -np.sum((byte_counts / len(content)) * np.log2(byte_counts / len(content) + 1e-10))
            features.character_distribution = {
                'entropy': float(entropy),
                'null_bytes': int(byte_counts[0]),
                'printable_ratio': sum(byte_counts[32:127]) / len(content)
            }
    
    async def _extract_structured_features(self, content: Union[dict, list], features: ClassificationFeatures):
        """Extract features from structured data"""
        features.content_type = "structured"
        
        if isinstance(content, dict):
            features.word_count = len(content)
            # Analyze structure
            has_timestamps = any(key in str(content) for key in ['timestamp', 'created_at', 'date', 'time'])
            has_coordinates = any(key in str(content) for key in ['lat', 'lon', 'latitude', 'longitude'])
            has_metrics = any(isinstance(v, (int, float)) for v in content.values() if v is not None)
            
            topics = []
            if has_timestamps:
                topics.append('temporal_data')
            if has_coordinates:
                topics.append('geospatial_data')
            if has_metrics:
                topics.append('quantitative_data')
            
            features.topics = topics
        
        elif isinstance(content, list):
            features.word_count = len(content)
            if content and isinstance(content[0], dict):
                # Array of objects
                features.topics = ['tabular_data', 'record_collection']
    
    async def _detect_language(self, content: str) -> Optional[str]:
        """Detect language of text content (simplified implementation)"""
        # Check for common programming language patterns
        for pattern_info in self.text_patterns['programming_languages']:
            if re.search(pattern_info['pattern'], content, re.MULTILINE | re.IGNORECASE):
                return pattern_info['language']
        
        # Simple natural language detection based on common words
        content_lower = content.lower()
        
        # English indicators
        english_words = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with']
        english_score = sum(1 for word in english_words if word in content_lower)
        
        # Spanish indicators
        spanish_words = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no']
        spanish_score = sum(1 for word in spanish_words if word in content_lower)
        
        # French indicators
        french_words = ['le', 'de', 'et', 'un', 'il', 'être', 'et', 'en', 'avoir', 'que']
        french_score = sum(1 for word in french_words if word in content_lower)
        
        if english_score >= spanish_score and english_score >= french_score and english_score > 2:
            return 'english'
        elif spanish_score > english_score and spanish_score >= french_score and spanish_score > 2:
            return 'spanish'
        elif french_score > english_score and french_score > spanish_score and french_score > 2:
            return 'french'
        
        return 'unknown'
    
    async def _extract_topics(self, content: str) -> List[str]:
        """Extract topics from text content (simplified implementation)"""
        topics = []
        content_lower = content.lower()
        
        # Technology topics
        tech_keywords = {
            'programming': ['code', 'function', 'variable', 'algorithm', 'debug'],
            'data_science': ['data', 'analysis', 'model', 'prediction', 'statistics'],
            'web_development': ['html', 'css', 'javascript', 'website', 'browser'],
            'mobile': ['android', 'ios', 'mobile', 'app', 'smartphone'],
            'ai_ml': ['machine learning', 'artificial intelligence', 'neural network', 'ai']
        }
        
        # Business topics
        business_keywords = {
            'finance': ['money', 'budget', 'investment', 'profit', 'revenue'],
            'marketing': ['campaign', 'brand', 'customer', 'market', 'advertising'],
            'sales': ['sales', 'deal', 'prospect', 'lead', 'conversion'],
            'hr': ['employee', 'hiring', 'recruitment', 'performance', 'training']
        }
        
        # Personal topics
        personal_keywords = {
            'health': ['health', 'fitness', 'exercise', 'diet', 'medical'],
            'travel': ['travel', 'trip', 'vacation', 'hotel', 'flight'],
            'food': ['food', 'recipe', 'cooking', 'restaurant', 'meal'],
            'entertainment': ['movie', 'music', 'game', 'book', 'show']
        }
        
        all_keywords = {**tech_keywords, **business_keywords, **personal_keywords}
        
        for topic, keywords in all_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                topics.append(topic)
        
        return topics[:5]  # Return top 5 topics
    
    async def _extract_entities(self, content: str) -> List[str]:
        """Extract entities from text content (simplified implementation)"""
        entities = []
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content)
        entities.extend([f"email:{email}" for email in emails[:5]])
        
        # URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, content)
        entities.extend([f"url:{url}" for url in urls[:3]])
        
        # Phone numbers (simplified)
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        phones = re.findall(phone_pattern, content)
        entities.extend([f"phone:{phone}" for phone in phones[:3]])
        
        # Dates (simplified)
        date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        dates = re.findall(date_pattern, content)
        entities.extend([f"date:{date}" for date in dates[:3]])
        
        return entities[:10]  # Return top 10 entities
    
    async def _analyze_sentiment(self, content: str) -> Optional[float]:
        """Analyze sentiment of text content (simplified implementation)"""
        # Simple keyword-based sentiment analysis
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'love', 'like', 'happy', 'best']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'dislike', 'sad', 'worst', 'horrible', 'disappointing']
        
        content_lower = content.lower()
        words = content_lower.split()
        
        positive_score = sum(1 for word in words if word in positive_words)
        negative_score = sum(1 for word in words if word in negative_words)
        
        total_sentiment_words = positive_score + negative_score
        if total_sentiment_words == 0:
            return 0.0  # Neutral
        
        # Return score between -1 (negative) and 1 (positive)
        return (positive_score - negative_score) / total_sentiment_words
    
    def _get_time_of_day(self, dt: datetime) -> str:
        """Get time of day category"""
        hour = dt.hour
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 21:
            return 'evening'
        else:
            return 'night'
    
    def _calculate_size(self, content: Any) -> int:
        """Calculate content size in bytes"""
        if isinstance(content, str):
            return len(content.encode('utf-8'))
        elif isinstance(content, bytes):
            return len(content)
        elif isinstance(content, (dict, list)):
            return len(json.dumps(content, default=str).encode('utf-8'))
        else:
            return len(str(content).encode('utf-8'))
    
    def _calculate_content_hash(self, content: Any) -> str:
        """Calculate SHA-256 hash of content"""
        if isinstance(content, str):
            data = content.encode('utf-8')
        elif isinstance(content, bytes):
            data = content
        else:
            data = json.dumps(content, sort_keys=True, default=str).encode('utf-8')
        
        return hashlib.sha256(data).hexdigest()

class IntelligentClassifier:
    """Advanced AI classifier using multiple classification strategies"""
    
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.classification_rules = self._load_classification_rules()
        self.confidence_threshold = 0.6
        
    def _load_classification_rules(self) -> Dict[str, Any]:
        """Load advanced classification rules"""
        return {
            'content_type_rules': {
                'document': {
                    'conditions': [
                        {'feature': 'file_extension', 'values': ['pdf', 'doc', 'docx', 'rtf', 'odt'], 'weight': 0.9},
                        {'feature': 'mime_type', 'patterns': ['application/pdf', 'application/msword'], 'weight': 0.9},
                        {'feature': 'file_signature', 'values': ['pdf', 'doc', 'docx'], 'weight': 0.95}
                    ],
                    'processors': ['document_parser', 'text_extractor', 'metadata_extractor'],
                    'subcategories': {
                        'pdf': {'extension': 'pdf', 'signature': 'pdf'},
                        'word_document': {'extension': ['doc', 'docx'], 'signature': ['doc', 'docx']},
                        'text_document': {'extension': ['txt', 'rtf'], 'mime_type': 'text/plain'}
                    }
                },
                'image': {
                    'conditions': [
                        {'feature': 'file_extension', 'values': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'], 'weight': 0.9},
                        {'feature': 'mime_type', 'patterns': ['image/'], 'weight': 0.9},
                        {'feature': 'file_signature', 'values': ['jpeg', 'png', 'gif87', 'gif89', 'webp'], 'weight': 0.95}
                    ],
                    'processors': ['image_analyzer', 'thumbnail_generator', 'metadata_extractor', 'face_detector'],
                    'subcategories': {
                        'photo': {'topics': ['personal'], 'source_platform': ['google_photos', 'icloud']},
                        'screenshot': {'filename_patterns': ['screen', 'capture'], 'aspect_ratios': ['16:9', '16:10']},
                        'graphic': {'file_extension': ['svg', 'ai'], 'topics': ['design']},
                        'icon': {'file_size_range': [0, 100000], 'filename_patterns': ['icon', 'favicon']}
                    }
                },
                'video': {
                    'conditions': [
                        {'feature': 'file_extension', 'values': ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm'], 'weight': 0.9},
                        {'feature': 'mime_type', 'patterns': ['video/'], 'weight': 0.9},
                        {'feature': 'file_signature', 'values': ['mp4', 'avi', 'mov'], 'weight': 0.95}
                    ],
                    'processors': ['video_analyzer', 'thumbnail_generator', 'transcoder', 'scene_detector'],
                    'subcategories': {
                        'personal_video': {'source_platform': ['google_photos', 'icloud'], 'topics': ['personal']},
                        'presentation': {'topics': ['business', 'education'], 'filename_patterns': ['presentation']},
                        'tutorial': {'topics': ['education'], 'filename_patterns': ['tutorial', 'howto']},
                        'entertainment': {'topics': ['entertainment'], 'file_size_range': [100000000, None]}
                    }
                },
                'audio': {
                    'conditions': [
                        {'feature': 'file_extension', 'values': ['mp3', 'wav', 'flac', 'aac', 'ogg'], 'weight': 0.9},
                        {'feature': 'mime_type', 'patterns': ['audio/'], 'weight': 0.9},
                        {'feature': 'file_signature', 'values': ['mp3', 'wav', 'flac'], 'weight': 0.95}
                    ],
                    'processors': ['audio_analyzer', 'waveform_generator', 'transcriber', 'music_analyzer'],
                    'subcategories': {
                        'music': {'topics': ['entertainment'], 'file_size_range': [1000000, None]},
                        'podcast': {'topics': ['education', 'entertainment'], 'filename_patterns': ['podcast', 'episode']},
                        'voice_memo': {'file_size_range': [0, 10000000], 'source_platform': ['mobile']},
                        'call_recording': {'filename_patterns': ['call', 'recording'], 'topics': ['communication']}
                    }
                },
                'text': {
                    'conditions': [
                        {'feature': 'content_type', 'values': ['text'], 'weight': 0.8},
                        {'feature': 'file_extension', 'values': ['txt', 'md', 'log'], 'weight': 0.7},
                        {'feature': 'character_distribution', 'check': 'is_text', 'weight': 0.6}
                    ],
                    'processors': ['text_analyzer', 'sentiment_analyzer', 'keyword_extractor', 'language_detector'],
                    'subcategories': {
                        'code': {'language': ['python', 'javascript', 'java', 'c'], 'topics': ['programming']},
                        'log_file': {'filename_patterns': ['log'], 'topics': ['system', 'application']},
                        'email': {'entities': ['email:'], 'topics': ['communication']},
                        'chat': {'topics': ['communication'], 'entities': ['@', '#']},
                        'note': {'topics': ['personal'], 'word_count_range': [10, 1000]},
                        'article': {'word_count_range': [1000, None], 'topics': ['education', 'information']}
                    }
                },
                'structured_data': {
                    'conditions': [
                        {'feature': 'content_type', 'values': ['structured'], 'weight': 0.8},
                        {'feature': 'language', 'values': ['json', 'xml', 'csv'], 'weight': 0.9},
                        {'feature': 'file_extension', 'values': ['json', 'xml', 'csv', 'yaml'], 'weight': 0.7}
                    ],
                    'processors': ['schema_analyzer', 'data_profiler', 'validator', 'transformer'],
                    'subcategories': {
                        'configuration': {'filename_patterns': ['config', 'settings'], 'file_extension': ['json', 'yaml']},
                        'api_response': {'topics': ['api'], 'language': ['json', 'xml']},
                        'dataset': {'file_extension': ['csv'], 'word_count_range': [100, None]},
                        'backup_data': {'filename_patterns': ['backup', 'export'], 'topics': ['system']}
                    }
                }
            },
            'context_rules': {
                'source_platform_mapping': {
                    'google_photos': {
                        'primary_types': ['image', 'video'],
                        'context_tags': ['personal', 'photos', 'social'],
                        'confidence_boost': 0.1
                    },
                    'dropbox': {
                        'primary_types': ['document', 'image', 'text'],
                        'context_tags': ['cloud_storage', 'files', 'backup'],
                        'confidence_boost': 0.05
                    },
                    'email': {
                        'primary_types': ['text', 'document'],
                        'context_tags': ['communication', 'personal', 'business'],
                        'confidence_boost': 0.1
                    },
                    'fitness_tracker': {
                        'primary_types': ['structured_data'],
                        'context_tags': ['health', 'fitness', 'quantified_self'],
                        'confidence_boost': 0.2
                    }
                },
                'temporal_rules': {
                    'morning': {'context_tags': ['work', 'productivity'], 'confidence_boost': 0.05},
                    'afternoon': {'context_tags': ['work', 'business'], 'confidence_boost': 0.05},
                    'evening': {'context_tags': ['personal', 'leisure'], 'confidence_boost': 0.05},
                    'night': {'context_tags': ['personal', 'entertainment'], 'confidence_boost': 0.05}
                }
            }
        }
    
    async def classify(self, content: Any, metadata: Dict[str, Any] = None) -> ClassificationResult:
        """Perform intelligent classification of data"""
        # Extract features
        features = await self.feature_extractor.extract_features(content, metadata)
        
        # Run multiple classification strategies
        strategies = [
            await self._signature_based_classification(features),
            await self._content_based_classification(features),
            await self._context_based_classification(features),
            await self._heuristic_classification(features)
        ]
        
        # Combine results using weighted voting
        final_result = await self._combine_classification_results(strategies, features)
        
        # Add metadata enrichment suggestions
        final_result.metadata_enrichment = await self._suggest_metadata_enrichment(features, final_result)
        
        # Calculate quality score
        final_result.quality_score = await self._calculate_quality_score(features, final_result)
        
        return final_result
    
    async def _signature_based_classification(self, features: ClassificationFeatures) -> ClassificationResult:
        """Classification based on file signatures and extensions"""
        confidence = 0.0
        primary_type = "unknown"
        reasoning = "No signature match found"
        
        # Check file signature first (highest confidence)
        if features.file_signature:
            signature_mapping = {
                'jpeg': 'image', 'png': 'image', 'gif87': 'image', 'gif89': 'image', 'webp': 'image',
                'mp4': 'video', 'avi': 'video', 'mov': 'video',
                'mp3': 'audio', 'wav': 'audio', 'flac': 'audio',
                'pdf': 'document', 'doc': 'document', 'docx': 'document'
            }
            
            if features.file_signature in signature_mapping:
                primary_type = signature_mapping[features.file_signature]
                confidence = 0.95
                reasoning = f"File signature {features.file_signature} indicates {primary_type}"
        
        # Check MIME type (high confidence)
        elif features.mime_type:
            mime_prefix = features.mime_type.split('/')[0]
            mime_mapping = {
                'image': 'image',
                'video': 'video', 
                'audio': 'audio',
                'text': 'text',
                'application': 'document'
            }
            
            if mime_prefix in mime_mapping:
                primary_type = mime_mapping[mime_prefix]
                confidence = 0.8
                reasoning = f"MIME type {features.mime_type} indicates {primary_type}"
        
        # Check file extension (medium confidence)
        elif features.file_extension:
            extension_mapping = {
                'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image',
                'mp4': 'video', 'avi': 'video', 'mov': 'video',
                'mp3': 'audio', 'wav': 'audio', 'flac': 'audio',
                'pdf': 'document', 'doc': 'document', 'docx': 'document',
                'txt': 'text', 'md': 'text', 'log': 'text',
                'json': 'structured_data', 'xml': 'structured_data', 'csv': 'structured_data'
            }
            
            if features.file_extension in extension_mapping:
                primary_type = extension_mapping[features.file_extension]
                confidence = 0.7
                reasoning = f"File extension .{features.file_extension} indicates {primary_type}"
        
        return ClassificationResult(
            primary_type=primary_type,
            confidence=confidence,
            features_used=['file_signature', 'mime_type', 'file_extension'],
            reasoning=reasoning
        )
    
    async def _content_based_classification(self, features: ClassificationFeatures) -> ClassificationResult:
        """Classification based on content analysis"""
        confidence = 0.0
        primary_type = "unknown"
        secondary_type = None
        reasoning = "Content analysis inconclusive"
        
        if features.content_type == "text":
            # Programming language detection
            if features.language in ['python', 'javascript', 'java', 'c', 'php', 'sql', 'html', 'json']:
                primary_type = "text"
                secondary_type = "code"
                confidence = 0.8
                reasoning = f"Programming language {features.language} detected"
            
            # Log file detection
            elif any(topic in ['system', 'application'] for topic in (features.topics or [])):
                primary_type = "text"
                secondary_type = "log"
                confidence = 0.75
                reasoning = "Log file patterns detected"
            
            # Communication content
            elif any('email:' in entity for entity in (features.entities or [])):
                primary_type = "text"
                secondary_type = "email"
                confidence = 0.8
                reasoning = "Email format detected"
            
            # General text classification
            else:
                primary_type = "text"
                if features.word_count > 500:
                    secondary_type = "article"
                    confidence = 0.6
                    reasoning = f"Long text content ({features.word_count} words)"
                else:
                    secondary_type = "note"
                    confidence = 0.5
                    reasoning = f"Short text content ({features.word_count} words)"
        
        elif features.content_type == "structured":
            primary_type = "structured_data"
            
            # Time series data
            if any(topic in ['temporal_data', 'quantitative_data'] for topic in (features.topics or [])):
                secondary_type = "time_series"
                confidence = 0.8
                reasoning = "Temporal and quantitative data patterns detected"
            
            # Geospatial data
            elif 'geospatial_data' in (features.topics or []):
                secondary_type = "geospatial"
                confidence = 0.8
                reasoning = "Geospatial data patterns detected"
            
            # Generic structured data
            else:
                secondary_type = "generic"
                confidence = 0.6
                reasoning = "Structured data format detected"
        
        elif features.content_type == "binary":
            # Binary content classification already handled by signature
            confidence = 0.3
            reasoning = "Binary content requires signature analysis"
        
        return ClassificationResult(
            primary_type=primary_type,
            secondary_type=secondary_type,
            confidence=confidence,
            features_used=['content_type', 'language', 'topics', 'entities', 'word_count'],
            reasoning=reasoning
        )
    
    async def _context_based_classification(self, features: ClassificationFeatures) -> ClassificationResult:
        """Classification based on context and metadata"""
        confidence = 0.0
        primary_type = "unknown"
        reasoning = "No contextual indicators found"
        context_boost = 0.0
        
        # Source platform context
        if features.source_platform:
            platform_rules = self.classification_rules['context_rules']['source_platform_mapping']
            
            for platform, rules in platform_rules.items():
                if platform in features.source_platform:
                    # This context supports certain types
                    if primary_type in rules['primary_types']:
                        context_boost += rules['confidence_boost']
                    
                    confidence = 0.4
                    reasoning = f"Source platform {platform} context"
                    break
        
        # Temporal context
        if features.time_of_day:
            temporal_rules = self.classification_rules['context_rules']['temporal_rules']
            if features.time_of_day in temporal_rules:
                context_boost += temporal_rules[features.time_of_day]['confidence_boost']
                confidence = max(confidence, 0.2)
                reasoning += f", {features.time_of_day} timing"
        
        # File size context
        if features.file_size > 0:
            if features.file_size > 100_000_000:  # > 100MB
                # Likely video or large dataset
                if primary_type == "unknown":
                    primary_type = "video"
                    confidence = 0.5
                    reasoning += ", large file size suggests video"
            elif features.file_size < 10_000:  # < 10KB
                # Likely text or small image
                if primary_type == "unknown":
                    primary_type = "text"
                    confidence = 0.3
                    reasoning += ", small file size suggests text"
        
        return ClassificationResult(
            primary_type=primary_type,
            confidence=min(confidence + context_boost, 1.0),
            features_used=['source_platform', 'time_of_day', 'file_size'],
            reasoning=reasoning
        )
    
    async def _heuristic_classification(self, features: ClassificationFeatures) -> ClassificationResult:
        """Classification using heuristic rules and patterns"""
        confidence = 0.0
        primary_type = "unknown"
        secondary_type = None
        reasoning = "Heuristic analysis"
        
        # Filename pattern analysis
        if features.filename:
            filename_lower = features.filename.lower()
            
            # Common patterns
            patterns = {
                'screenshot': (['screen', 'capture', 'shot'], 'image', 'screenshot'),
                'download': (['download', 'file'], 'document', 'downloaded'),
                'backup': (['backup', 'bak', 'archive'], 'structured_data', 'backup'),
                'config': (['config', 'settings', 'pref'], 'structured_data', 'configuration'),
                'temp': (['temp', 'tmp', 'cache'], 'unknown', 'temporary'),
                'log': (['log', 'trace', 'debug'], 'text', 'log')
            }
            
            for pattern_name, (keywords, suggested_type, subtype) in patterns.items():
                if any(keyword in filename_lower for keyword in keywords):
                    primary_type = suggested_type
                    secondary_type = subtype
                    confidence = 0.6
                    reasoning = f"Filename pattern '{pattern_name}' detected"
                    break
        
        # Content entropy analysis (for binary files)
        if (features.character_distribution and 
            'entropy' in features.character_distribution):
            
            entropy = features.character_distribution['entropy']
            
            if entropy > 7.5:  # High entropy
                if primary_type == "unknown":
                    primary_type = "binary"
                    secondary_type = "encrypted_or_compressed"
                    confidence = 0.7
                    reasoning = f"High entropy ({entropy:.2f}) suggests encrypted/compressed data"
            
            elif entropy < 2.0:  # Low entropy
                if primary_type == "unknown":
                    primary_type = "text"
                    secondary_type = "simple_text"
                    confidence = 0.5
                    reasoning = f"Low entropy ({entropy:.2f}) suggests simple text"
        
        # Aspect ratio analysis for images
        if primary_type == "image" and features.metadata:
            width = features.metadata.get('width', 0)
            height = features.metadata.get('height', 0)
            
            if width and height:
                aspect_ratio = width / height
                
                if abs(aspect_ratio - 16/9) < 0.1:  # ~16:9
                    secondary_type = "screenshot"
                    confidence = max(confidence, 0.6)
                    reasoning += ", 16:9 aspect ratio suggests screenshot"
                elif abs(aspect_ratio - 1.0) < 0.1:  # ~1:1
                    secondary_type = "social_media"
                    confidence = max(confidence, 0.5)
                    reasoning += ", square aspect ratio suggests social media"
        
        return ClassificationResult(
            primary_type=primary_type,
            secondary_type=secondary_type,
            confidence=confidence,
            features_used=['filename', 'character_distribution', 'metadata'],
            reasoning=reasoning
        )
    
    async def _combine_classification_results(self, strategies: List[ClassificationResult], 
                                           features: ClassificationFeatures) -> ClassificationResult:
        """Combine results from multiple classification strategies"""
        # Weight the strategies
        strategy_weights = [0.4, 0.3, 0.2, 0.1]  # signature, content, context, heuristic
        
        # Collect all type votes with weighted confidence
        type_votes = {}
        total_confidence = 0
        reasoning_parts = []
        all_features_used = set()
        all_processors = set()
        
        for strategy, weight in zip(strategies, strategy_weights):
            if strategy.primary_type != "unknown":
                weighted_confidence = strategy.confidence * weight
                
                if strategy.primary_type in type_votes:
                    type_votes[strategy.primary_type] += weighted_confidence
                else:
                    type_votes[strategy.primary_type] = weighted_confidence
                
                total_confidence += weighted_confidence
                reasoning_parts.append(f"({strategy.reasoning})")
                all_features_used.update(strategy.features_used or [])
                all_processors.update(strategy.suggested_processors or [])
        
        # Select the type with highest weighted vote
        if type_votes:
            final_type = max(type_votes.items(), key=lambda x: x[1])[0]
            final_confidence = type_votes[final_type]
        else:
            final_type = "unknown"
            final_confidence = 0.0
        
        # Determine secondary type
        secondary_type = None
        for strategy in strategies:
            if strategy.primary_type == final_type and strategy.secondary_type:
                secondary_type = strategy.secondary_type
                break
        
        # Get suggested processors for the final type
        suggested_processors = list(all_processors)
        if final_type in self.classification_rules['content_type_rules']:
            rule_processors = self.classification_rules['content_type_rules'][final_type].get('processors', [])
            suggested_processors.extend(rule_processors)
        
        # Remove duplicates while preserving order
        suggested_processors = list(dict.fromkeys(suggested_processors))
        
        return ClassificationResult(
            primary_type=final_type,
            secondary_type=secondary_type,
            confidence=min(final_confidence, 1.0),
            features_used=list(all_features_used),
            reasoning=" | ".join(reasoning_parts),
            suggested_processors=suggested_processors
        )
    
    async def _suggest_metadata_enrichment(self, features: ClassificationFeatures, 
                                         result: ClassificationResult) -> Dict[str, Any]:
        """Suggest metadata enrichment based on classification"""
        enrichment = {}
        
        # Add extracted entities as metadata
        if features.entities:
            enrichment['extracted_entities'] = features.entities
        
        # Add topic information
        if features.topics:
            enrichment['topics'] = features.topics
        
        # Add language information
        if features.language and features.language != 'unknown':
            enrichment['detected_language'] = features.language
        
        # Add sentiment for text content
        if features.sentiment is not None and abs(features.sentiment) > 0.1:
            enrichment['sentiment'] = {
                'score': features.sentiment,
                'label': 'positive' if features.sentiment > 0 else 'negative'
            }
        
        # Add content statistics
        if features.word_count > 0:
            enrichment['content_stats'] = {
                'word_count': features.word_count,
                'character_count': features.text_length,
                'line_count': features.line_count
            }
        
        # Add quality indicators
        quality_indicators = []
        if features.confidence_score and features.confidence_score > 0.8:
            quality_indicators.append('high_confidence_classification')
        
        if features.file_size > 0:
            if features.file_size < 1000:
                quality_indicators.append('small_file')
            elif features.file_size > 100_000_000:
                quality_indicators.append('large_file')
        
        if quality_indicators:
            enrichment['quality_indicators'] = quality_indicators
        
        return enrichment
    
    async def _calculate_quality_score(self, features: ClassificationFeatures, 
                                     result: ClassificationResult) -> float:
        """Calculate overall quality score for the classification"""
        score_components = []
        
        # Confidence score (40% weight)
        score_components.append(('confidence', result.confidence, 0.4))
        
        # Feature completeness (30% weight)
        total_possible_features = 15  # Approximate number of extractable features
        extracted_features = sum([
            1 if features.filename else 0,
            1 if features.file_extension else 0,
            1 if features.mime_type else 0,
            1 if features.file_signature else 0,
            1 if features.language else 0,
            1 if features.topics else 0,
            1 if features.entities else 0,
            1 if features.sentiment is not None else 0,
            1 if features.source_platform else 0,
            1 if features.creation_time else 0,
            1 if features.character_distribution else 0,
            1 if features.content_hash else 0,
            1 if features.word_count > 0 else 0,
            1 if features.file_size > 0 else 0,
            1 if features.time_of_day else 0
        ])
        
        feature_completeness = extracted_features / total_possible_features
        score_components.append(('features', feature_completeness, 0.3))
        
        # Consistency across strategies (20% weight)
        consistency_score = 1.0 if result.confidence > 0.7 else 0.5
        score_components.append(('consistency', consistency_score, 0.2))
        
        # Metadata richness (10% weight)
        metadata_richness = min(len(result.metadata_enrichment or {}) / 5, 1.0)
        score_components.append(('metadata', metadata_richness, 0.1))
        
        # Calculate weighted average
        total_score = sum(score * weight for _, score, weight in score_components)
        
        return round(total_score, 3)

# CLI Interface
async def main():
    """Command-line interface for intelligent classifier"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Intelligent Data Classifier')
    parser.add_argument('action', choices=['classify', 'extract_features', 'test'])
    parser.add_argument('--content', help='Content to classify (text or file path)')
    parser.add_argument('--metadata', help='Metadata JSON string')
    parser.add_argument('--output', help='Output file for results')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    classifier = IntelligentClassifier()
    
    if args.action == 'classify':
        if not args.content:
            print("Error: --content required for classification")
            return
        
        # Load content
        content = args.content
        if os.path.exists(args.content):
            with open(args.content, 'rb') as f:
                content = f.read()
                # Try to decode as text
                try:
                    content = content.decode('utf-8')
                except UnicodeDecodeError:
                    pass  # Keep as bytes
        
        # Parse metadata
        metadata = {}
        if args.metadata:
            metadata = json.loads(args.metadata)
        
        if os.path.exists(args.content):
            metadata['filename'] = os.path.basename(args.content)
        
        # Classify
        result = await classifier.classify(content, metadata)
        
        # Output results
        output = {
            'primary_type': result.primary_type,
            'secondary_type': result.secondary_type,
            'confidence': result.confidence,
            'quality_score': result.quality_score,
            'reasoning': result.reasoning,
            'suggested_processors': result.suggested_processors,
            'metadata_enrichment': result.metadata_enrichment
        }
        
        if args.verbose:
            output['features_used'] = result.features_used
        
        result_json = json.dumps(output, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(result_json)
            print(f"Classification results saved to {args.output}")
        else:
            print("Classification Results:")
            print(result_json)
    
    elif args.action == 'extract_features':
        if not args.content:
            print("Error: --content required for feature extraction")
            return
        
        # Load content
        content = args.content
        if os.path.exists(args.content):
            with open(args.content, 'rb') as f:
                content = f.read()
                try:
                    content = content.decode('utf-8')
                except UnicodeDecodeError:
                    pass
        
        metadata = {}
        if args.metadata:
            metadata = json.loads(args.metadata)
        
        if os.path.exists(args.content):
            metadata['filename'] = os.path.basename(args.content)
        
        # Extract features
        features = await classifier.feature_extractor.extract_features(content, metadata)
        
        # Convert to dict for JSON serialization
        features_dict = asdict(features)
        
        result_json = json.dumps(features_dict, indent=2, default=str)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(result_json)
            print(f"Features saved to {args.output}")
        else:
            print("Extracted Features:")
            print(result_json)
    
    elif args.action == 'test':
        # Test the classifier with various content types
        test_cases = [
            ("Hello world!", {"source": "manual"}, "Simple text"),
            ('{"name": "John", "age": 30}', {"source": "api"}, "JSON data"),
            (b'\xFF\xD8\xFF\xE0', {"filename": "photo.jpg"}, "JPEG image"),
            ("import numpy as np\nprint('Hello')", {"filename": "script.py"}, "Python code"),
            ("2024-01-01 10:30:00 ERROR: Connection failed", {"filename": "app.log"}, "Log file")
        ]
        
        print("Testing Intelligent Classifier:")
        print("=" * 50)
        
        for i, (content, metadata, description) in enumerate(test_cases, 1):
            print(f"\nTest Case {i}: {description}")
            print("-" * 30)
            
            result = await classifier.classify(content, metadata)
            
            print(f"Type: {result.primary_type}")
            if result.secondary_type:
                print(f"Subtype: {result.secondary_type}")
            print(f"Confidence: {result.confidence:.2f}")
            print(f"Quality: {result.quality_score:.2f}")
            print(f"Reasoning: {result.reasoning}")
            
            if result.suggested_processors:
                print(f"Processors: {', '.join(result.suggested_processors[:3])}")

if __name__ == "__main__":
    asyncio.run(main())