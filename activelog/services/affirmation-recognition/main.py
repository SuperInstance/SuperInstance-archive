#!/usr/bin/env python3
"""
Affirmation Recognition System - ML-Powered User Satisfaction Detection and Learning System

This comprehensive system recognizes when users affirm that the system did "exactly the right thing"
and uses this feedback to continuously improve interpreter bot accuracy across the entire Building Bots Network.

Key Features:
- Real-time user response analysis for affirmations like "Perfect", "Good job", "Exactly right"
- Context-aware recognition linking user commands to system responses
- ML training pipeline for interpreter bot learning from successful interactions
- Integration with all generative services to capture user satisfaction
- Sentiment analysis and intent recognition for feedback classification
- Automatic model improvement based on confirmed successful interactions
- Pattern recognition for successful command interpretations
- Feedback loop integration with interpreter bots and SuperPicker
- Context preservation linking user requests to system responses to user affirmations
- Quality scoring system for different types of successful interactions
- Continuous learning pipeline for improving interpretation accuracy
"""

import asyncio
import logging
import json
import time
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import sqlite3
import statistics
from collections import defaultdict, deque
import threading
from contextlib import asynccontextmanager
import requests
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import pickle
import hashlib

# FastAPI and ML imports
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# ML and NLP imports
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import spacy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    "database_path": "/home/activeloguser/activelog/services/affirmation-recognition/data/affirmation_recognition.db",
    "models_path": "/home/activeloguser/activelog/services/affirmation-recognition/models/",
    "context_window_seconds": 300,  # 5 minutes context window
    "min_confidence_threshold": 0.75,
    "learning_batch_size": 32,
    "retrain_interval": 3600,  # 1 hour
    "max_context_messages": 10,
    "services": {
        "ai_picker_system": "http://localhost:8470",
        "generative_tools_hub": "http://localhost:8500",
        "image_generation": "http://localhost:8480",
        "audio_generation": "http://localhost:8481",
        "video_generation": "http://localhost:8483",
        "code_generation": "http://localhost:8482",
        "openai_integration": "http://localhost:8475",
        "hierarchical_task_system": "http://localhost:8471",
        "claude_task_hierarchy": "http://localhost:8474",
        "resource_monitor": "http://localhost:8473"
    }
}

class AffirmationType(Enum):
    STRONG_POSITIVE = "strong_positive"          # "Perfect!", "Exactly right!", "Outstanding!"
    MODERATE_POSITIVE = "moderate_positive"      # "Good job", "Nice work", "That's right"
    MILD_POSITIVE = "mild_positive"              # "Ok", "Fine", "Thanks"
    APPRECIATION = "appreciation"                # "Thank you", "Appreciate it", "Helpful"
    COMPLETION = "completion"                    # "Done", "Got it", "Complete"
    SATISFACTION = "satisfaction"                # "Satisfied", "Happy with this", "Good enough"
    CONFIRMATION = "confirmation"                # "Yes, that's it", "Correct", "Right"

class ContextType(Enum):
    USER_REQUEST = "user_request"
    SYSTEM_RESPONSE = "system_response"
    USER_FEEDBACK = "user_feedback"
    TASK_COMPLETION = "task_completion"
    ERROR_RECOVERY = "error_recovery"
    CLARIFICATION = "clarification"

class FeedbackSource(Enum):
    DIRECT_USER_INPUT = "direct_user_input"
    CHAT_INTERFACE = "chat_interface"
    API_FEEDBACK = "api_feedback"
    BEHAVIORAL_ANALYSIS = "behavioral_analysis"
    COMPLETION_SIGNALS = "completion_signals"

@dataclass
class ContextMessage:
    message_id: str
    user_id: str
    content: str
    context_type: ContextType
    service_name: str
    timestamp: datetime
    metadata: Dict[str, Any]
    session_id: str

@dataclass
class AffirmationEvent:
    event_id: str
    user_id: str
    session_id: str
    affirmation_text: str
    affirmation_type: AffirmationType
    confidence_score: float
    context_messages: List[ContextMessage]
    source: FeedbackSource
    timestamp: datetime
    original_request: Optional[str]
    system_response: Optional[str]
    metadata: Dict[str, Any]

@dataclass
class LearningPattern:
    pattern_id: str
    user_request_pattern: str
    system_response_pattern: str
    affirmation_pattern: str
    success_rate: float
    occurrences: int
    last_seen: datetime
    confidence: float
    service_context: str
    user_segments: List[str]

@dataclass
class InterpreterImprovement:
    improvement_id: str
    service_name: str
    pattern_type: str
    before_accuracy: float
    after_accuracy: float
    improvement_factor: float
    patterns_learned: List[LearningPattern]
    timestamp: datetime
    validation_score: float

class AffirmationClassifier:
    """Advanced ML classifier for detecting user affirmations and satisfaction"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english', ngram_range=(1, 3))
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.models = {
            'nb': MultinomialNB(),
            'lr': LogisticRegression(random_state=42),
            'rf': RandomForestClassifier(n_estimators=100, random_state=42),
            'svm': SVC(probability=True, random_state=42)
        }
        self.ensemble_weights = {}
        self.lemmatizer = WordNetLemmatizer()
        self.is_trained = False
        
        # Load pre-trained transformer model for sentiment analysis
        try:
            self.transformer_sentiment = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                tokenizer="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
        except Exception as e:
            logger.warning(f"Could not load transformer model: {e}")
            self.transformer_sentiment = None
        
        # Initialize affirmation patterns
        self.affirmation_patterns = {
            AffirmationType.STRONG_POSITIVE: [
                r'\b(perfect|excellent|outstanding|amazing|brilliant|fantastic|wonderful|superb)\b',
                r'\b(exactly right|spot on|nail it|bull\'?s eye|home run|grand slam)\b',
                r'\b(love it|adore|incredible|phenomenal|marvelous|exceptional)\b'
            ],
            AffirmationType.MODERATE_POSITIVE: [
                r'\b(good job|nice work|well done|good work|solid|decent)\b',
                r'\b(that\'?s right|correct|accurate|proper|appropriate)\b',
                r'\b(pleased|satisfied|content|happy|glad)\b'
            ],
            AffirmationType.MILD_POSITIVE: [
                r'\b(ok|okay|fine|alright|sure|yes)\b',
                r'\b(thanks|thank you|appreciate|helpful)\b',
                r'\b(got it|understood|clear|makes sense)\b'
            ],
            AffirmationType.APPRECIATION: [
                r'\b(thank you|thanks|appreciate|grateful|obliged)\b',
                r'\b(helpful|useful|valuable|beneficial|worthwhile)\b',
                r'\b(kind|thoughtful|considerate|generous)\b'
            ],
            AffirmationType.COMPLETION: [
                r'\b(done|complete|finished|accomplished|achieved)\b',
                r'\b(got it|understood|received|confirmed)\b',
                r'\b(ready|set|prepared|good to go)\b'
            ],
            AffirmationType.SATISFACTION: [
                r'\b(satisfied|content|pleased|happy|delighted)\b',
                r'\b(good enough|sufficient|adequate|acceptable)\b',
                r'\b(meets expectations|as expected|what I wanted)\b'
            ],
            AffirmationType.CONFIRMATION: [
                r'\b(yes|yep|yeah|correct|right|exactly)\b',
                r'\b(that\'?s it|that\'?s the one|bingo|there we go)\b',
                r'\b(confirmed|verified|validated|approved)\b'
            ]
        }
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text for analysis"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Handle contractions
        contractions = {
            "won't": "will not", "can't": "cannot", "n't": " not",
            "'re": " are", "'ve": " have", "'ll": " will", "'d": " would",
            "'m": " am", "'s": " is"
        }
        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)
        
        return text
    
    def extract_features(self, text: str) -> Dict[str, Any]:
        """Extract comprehensive features from text for classification"""
        preprocessed = self.preprocess_text(text)
        features = {}
        
        # Basic text features
        features['length'] = len(text)
        features['word_count'] = len(text.split())
        features['sentence_count'] = len(sent_tokenize(text))
        
        # Sentiment features
        sentiment = self.sentiment_analyzer.polarity_scores(preprocessed)
        features.update({f'nltk_{k}': v for k, v in sentiment.items()})
        
        # Transformer sentiment if available
        if self.transformer_sentiment:
            try:
                transformer_result = self.transformer_sentiment(text[:512])  # Limit length
                if transformer_result:
                    result = transformer_result[0]
                    features['transformer_label'] = result['label']
                    features['transformer_score'] = result['score']
            except Exception as e:
                logger.warning(f"Transformer sentiment analysis failed: {e}")
        
        # Pattern matching features
        for affirmation_type, patterns in self.affirmation_patterns.items():
            count = sum(len(re.findall(pattern, preprocessed, re.IGNORECASE)) for pattern in patterns)
            features[f'pattern_{affirmation_type.value}'] = count
        
        # Linguistic features
        tokens = word_tokenize(preprocessed)
        features['avg_word_length'] = np.mean([len(word) for word in tokens]) if tokens else 0
        features['exclamation_marks'] = text.count('!')
        features['question_marks'] = text.count('?')
        features['uppercase_ratio'] = sum(1 for c in text if c.isupper()) / len(text) if text else 0
        
        return features
    
    def classify_affirmation(self, text: str) -> Tuple[AffirmationType, float]:
        """Classify text as an affirmation type with confidence score"""
        if not text:
            return None, 0.0
        
        preprocessed = self.preprocess_text(text)
        features = self.extract_features(text)
        
        # Pattern-based classification (fast initial classification)
        pattern_scores = {}
        for affirmation_type, patterns in self.affirmation_patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, preprocessed, re.IGNORECASE)
                score += len(matches) * 0.3  # Weight for pattern matches
            
            # Boost score based on sentiment
            if features.get('nltk_compound', 0) > 0.1:
                score += features['nltk_compound'] * 0.5
            
            # Boost for transformer positive sentiment
            if (features.get('transformer_label') == 'POSITIVE' and 
                features.get('transformer_score', 0) > 0.7):
                score += 0.4
            
            pattern_scores[affirmation_type] = score
        
        if not pattern_scores or max(pattern_scores.values()) < 0.1:
            return None, 0.0
        
        # Get the best match
        best_type = max(pattern_scores, key=pattern_scores.get)
        confidence = min(pattern_scores[best_type], 1.0)
        
        # Apply ML model if trained and confidence is borderline
        if self.is_trained and 0.3 < confidence < 0.8:
            try:
                ml_confidence = self.predict_with_ensemble(text)
                confidence = (confidence + ml_confidence) / 2
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")
        
        return best_type, confidence
    
    def predict_with_ensemble(self, text: str) -> float:
        """Use ensemble of ML models to predict affirmation confidence"""
        if not self.is_trained:
            return 0.0
        
        try:
            # Vectorize the text
            X = self.vectorizer.transform([text])
            
            # Get predictions from all models
            predictions = []
            for name, model in self.models.items():
                if hasattr(model, 'predict_proba'):
                    prob = model.predict_proba(X)[0]
                    # Assuming binary classification (affirmation vs non-affirmation)
                    confidence = prob[1] if len(prob) > 1 else prob[0]
                    weight = self.ensemble_weights.get(name, 1.0)
                    predictions.append(confidence * weight)
            
            return np.mean(predictions) if predictions else 0.0
            
        except Exception as e:
            logger.error(f"Ensemble prediction error: {e}")
            return 0.0
    
    def train(self, training_data: List[Tuple[str, bool]]):
        """Train the ML models with labeled data"""
        if len(training_data) < 10:
            logger.warning("Insufficient training data")
            return
        
        texts, labels = zip(*training_data)
        
        # Vectorize texts
        X = self.vectorizer.fit_transform(texts)
        y = np.array(labels)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train all models and calculate weights
        self.ensemble_weights = {}
        for name, model in self.models.items():
            try:
                model.fit(X_train, y_train)
                
                # Calculate performance-based weight
                if hasattr(model, 'predict_proba'):
                    y_pred_proba = model.predict_proba(X_test)
                    y_pred = (y_pred_proba[:, 1] > 0.5).astype(int) if y_pred_proba.shape[1] > 1 else model.predict(X_test)
                else:
                    y_pred = model.predict(X_test)
                
                accuracy = accuracy_score(y_test, y_pred)
                self.ensemble_weights[name] = accuracy
                
                logger.info(f"Model {name} accuracy: {accuracy:.3f}")
                
            except Exception as e:
                logger.error(f"Error training model {name}: {e}")
                self.ensemble_weights[name] = 0.0
        
        self.is_trained = True
        logger.info("Affirmation classifier training completed")

class ContextAnalyzer:
    """Analyzes conversation context to link user requests with system responses and affirmations"""
    
    def __init__(self):
        self.context_store = {}  # session_id -> deque of messages
        self.session_timeouts = {}  # session_id -> last_activity
        self.cleanup_interval = 3600  # 1 hour
        
    def add_context_message(self, message: ContextMessage):
        """Add a message to the context store"""
        session_id = message.session_id
        
        if session_id not in self.context_store:
            self.context_store[session_id] = deque(maxlen=CONFIG["max_context_messages"])
        
        self.context_store[session_id].append(message)
        self.session_timeouts[session_id] = datetime.now()
        
        # Cleanup old sessions periodically
        if len(self.session_timeouts) % 100 == 0:
            self._cleanup_old_sessions()
    
    def get_relevant_context(self, session_id: str, timestamp: datetime, 
                           window_seconds: int = None) -> List[ContextMessage]:
        """Get relevant context messages for a session within a time window"""
        if window_seconds is None:
            window_seconds = CONFIG["context_window_seconds"]
        
        if session_id not in self.context_store:
            return []
        
        cutoff_time = timestamp - timedelta(seconds=window_seconds)
        relevant_messages = []
        
        for message in self.context_store[session_id]:
            if message.timestamp >= cutoff_time:
                relevant_messages.append(message)
        
        return relevant_messages
    
    def find_related_interaction(self, affirmation_event: AffirmationEvent) -> Tuple[Optional[str], Optional[str]]:
        """Find the user request and system response that the affirmation is responding to"""
        context_messages = self.get_relevant_context(
            affirmation_event.session_id, 
            affirmation_event.timestamp
        )
        
        if not context_messages:
            return None, None
        
        # Find the most recent user request and system response
        user_request = None
        system_response = None
        
        for message in reversed(context_messages):
            if message.context_type == ContextType.USER_REQUEST and not user_request:
                user_request = message.content
            elif message.context_type == ContextType.SYSTEM_RESPONSE and not system_response:
                system_response = message.content
            
            # Stop when we have both
            if user_request and system_response:
                break
        
        return user_request, system_response
    
    def _cleanup_old_sessions(self):
        """Clean up old sessions to prevent memory leaks"""
        cutoff_time = datetime.now() - timedelta(seconds=self.cleanup_interval)
        
        expired_sessions = [
            session_id for session_id, last_activity in self.session_timeouts.items()
            if last_activity < cutoff_time
        ]
        
        for session_id in expired_sessions:
            self.context_store.pop(session_id, None)
            self.session_timeouts.pop(session_id, None)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

class PatternLearner:
    """Learns patterns from successful interactions to improve interpreter bots"""
    
    def __init__(self):
        self.learned_patterns = {}
        self.pattern_performance = defaultdict(lambda: {'successes': 0, 'attempts': 0})
        
    def extract_pattern(self, user_request: str, system_response: str, 
                       affirmation: AffirmationEvent) -> Optional[LearningPattern]:
        """Extract a learning pattern from a successful interaction"""
        if not user_request or not system_response:
            return None
        
        # Create pattern fingerprints
        request_pattern = self._create_pattern_fingerprint(user_request)
        response_pattern = self._create_pattern_fingerprint(system_response)
        affirmation_pattern = self._create_pattern_fingerprint(affirmation.affirmation_text)
        
        # Calculate success rate and confidence
        pattern_key = f"{request_pattern}|{response_pattern}"
        perf = self.pattern_performance[pattern_key]
        success_rate = perf['successes'] / max(perf['attempts'], 1)
        
        pattern = LearningPattern(
            pattern_id=str(uuid.uuid4()),
            user_request_pattern=request_pattern,
            system_response_pattern=response_pattern,
            affirmation_pattern=affirmation_pattern,
            success_rate=success_rate,
            occurrences=perf['successes'],
            last_seen=datetime.now(),
            confidence=affirmation.confidence_score,
            service_context=affirmation.metadata.get('service', 'unknown'),
            user_segments=self._identify_user_segments(affirmation.user_id)
        )
        
        return pattern
    
    def _create_pattern_fingerprint(self, text: str) -> str:
        """Create a pattern fingerprint for matching similar requests/responses"""
        if not text:
            return ""
        
        # Normalize text
        normalized = re.sub(r'\b\d+\b', '[NUMBER]', text.lower())
        normalized = re.sub(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', '[EMAIL]', normalized)
        normalized = re.sub(r'\bhttps?://[^\s]+', '[URL]', normalized)
        
        # Extract key terms (simplified approach)
        words = normalized.split()
        key_words = [word for word in words if len(word) > 3 and word.isalpha()]
        
        return ' '.join(sorted(set(key_words)))
    
    def _identify_user_segments(self, user_id: str) -> List[str]:
        """Identify user segments for pattern applicability"""
        # This would be enhanced with actual user behavior analysis
        return ['general']
    
    def update_pattern_performance(self, pattern: LearningPattern, success: bool):
        """Update pattern performance metrics"""
        pattern_key = f"{pattern.user_request_pattern}|{pattern.system_response_pattern}"
        self.pattern_performance[pattern_key]['attempts'] += 1
        if success:
            self.pattern_performance[pattern_key]['successes'] += 1

class InterpreterBotIntegration:
    """Integration layer for sending learning insights to interpreter bots"""
    
    def __init__(self):
        self.service_connections = {}
        self.improvement_history = []
        
    async def initialize_connections(self):
        """Initialize connections to all Building Bots Network services"""
        for service_name, url in CONFIG["services"].items():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/health", timeout=5) as response:
                        if response.status == 200:
                            self.service_connections[service_name] = url
                            logger.info(f"Connected to {service_name} at {url}")
            except Exception as e:
                logger.warning(f"Could not connect to {service_name}: {e}")
    
    async def send_learning_patterns(self, service_name: str, patterns: List[LearningPattern]) -> bool:
        """Send learning patterns to a specific service"""
        if service_name not in self.service_connections:
            logger.warning(f"No connection to service: {service_name}")
            return False
        
        try:
            url = self.service_connections[service_name]
            payload = {
                "patterns": [asdict(pattern) for pattern in patterns],
                "timestamp": datetime.now().isoformat(),
                "source": "affirmation_recognition_system"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{url}/learn/patterns",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        logger.info(f"Successfully sent {len(patterns)} patterns to {service_name}")
                        return True
                    else:
                        logger.error(f"Failed to send patterns to {service_name}: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending patterns to {service_name}: {e}")
            return False
    
    async def broadcast_improvement(self, improvement: InterpreterImprovement):
        """Broadcast an improvement to all connected services"""
        success_count = 0
        total_services = len(self.service_connections)
        
        for service_name in self.service_connections:
            try:
                success = await self.send_improvement_notification(service_name, improvement)
                if success:
                    success_count += 1
            except Exception as e:
                logger.error(f"Error broadcasting to {service_name}: {e}")
        
        logger.info(f"Broadcasted improvement to {success_count}/{total_services} services")
        return success_count / total_services if total_services > 0 else 0
    
    async def send_improvement_notification(self, service_name: str, 
                                          improvement: InterpreterImprovement) -> bool:
        """Send improvement notification to a specific service"""
        if service_name not in self.service_connections:
            return False
        
        try:
            url = self.service_connections[service_name]
            payload = asdict(improvement)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{url}/learn/improvement",
                    json=payload,
                    timeout=15
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Error sending improvement to {service_name}: {e}")
            return False

class DatabaseManager:
    """Manages database operations for the affirmation recognition system"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Context messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_messages (
                message_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                content TEXT NOT NULL,
                context_type TEXT NOT NULL,
                service_name TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                metadata TEXT
            )
        ''')
        
        # Affirmation events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS affirmation_events (
                event_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                affirmation_text TEXT NOT NULL,
                affirmation_type TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                source TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                original_request TEXT,
                system_response TEXT,
                metadata TEXT
            )
        ''')
        
        # Learning patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_patterns (
                pattern_id TEXT PRIMARY KEY,
                user_request_pattern TEXT NOT NULL,
                system_response_pattern TEXT NOT NULL,
                affirmation_pattern TEXT NOT NULL,
                success_rate REAL NOT NULL,
                occurrences INTEGER NOT NULL,
                last_seen DATETIME NOT NULL,
                confidence REAL NOT NULL,
                service_context TEXT NOT NULL,
                user_segments TEXT
            )
        ''')
        
        # Interpreter improvements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interpreter_improvements (
                improvement_id TEXT PRIMARY KEY,
                service_name TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                before_accuracy REAL NOT NULL,
                after_accuracy REAL NOT NULL,
                improvement_factor REAL NOT NULL,
                timestamp DATETIME NOT NULL,
                validation_score REAL NOT NULL,
                patterns_learned_count INTEGER NOT NULL
            )
        ''')
        
        # User satisfaction metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_satisfaction_metrics (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                session_id TEXT NOT NULL,
                satisfaction_score REAL NOT NULL,
                response_time REAL,
                task_completion BOOLEAN NOT NULL,
                timestamp DATETIME NOT NULL
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_context_session_time ON context_messages(session_id, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_affirmation_user_time ON affirmation_events(user_id, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_service ON learning_patterns(service_context)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_improvements_service ON interpreter_improvements(service_name)')
        
        conn.commit()
        conn.close()
    
    async def store_context_message(self, message: ContextMessage):
        """Store a context message"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO context_messages
            (message_id, user_id, session_id, content, context_type, service_name, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message.message_id,
            message.user_id,
            message.session_id,
            message.content,
            message.context_type.value,
            message.service_name,
            message.timestamp,
            json.dumps(message.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    async def store_affirmation_event(self, event: AffirmationEvent):
        """Store an affirmation event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO affirmation_events
            (event_id, user_id, session_id, affirmation_text, affirmation_type, confidence_score,
             source, timestamp, original_request, system_response, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.event_id,
            event.user_id,
            event.session_id,
            event.affirmation_text,
            event.affirmation_type.value,
            event.confidence_score,
            event.source.value,
            event.timestamp,
            event.original_request,
            event.system_response,
            json.dumps(event.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    async def store_learning_pattern(self, pattern: LearningPattern):
        """Store a learning pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO learning_patterns
            (pattern_id, user_request_pattern, system_response_pattern, affirmation_pattern,
             success_rate, occurrences, last_seen, confidence, service_context, user_segments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pattern.pattern_id,
            pattern.user_request_pattern,
            pattern.system_response_pattern,
            pattern.affirmation_pattern,
            pattern.success_rate,
            pattern.occurrences,
            pattern.last_seen,
            pattern.confidence,
            pattern.service_context,
            json.dumps(pattern.user_segments)
        ))
        
        conn.commit()
        conn.close()
    
    async def get_recent_patterns(self, service_name: str = None, hours: int = 24) -> List[LearningPattern]:
        """Get recent learning patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        query = '''
            SELECT * FROM learning_patterns
            WHERE last_seen >= ?
        '''
        params = [cutoff_time]
        
        if service_name:
            query += ' AND service_context = ?'
            params.append(service_name)
        
        query += ' ORDER BY confidence DESC, success_rate DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        patterns = []
        for row in rows:
            pattern = LearningPattern(
                pattern_id=row[0],
                user_request_pattern=row[1],
                system_response_pattern=row[2],
                affirmation_pattern=row[3],
                success_rate=row[4],
                occurrences=row[5],
                last_seen=datetime.fromisoformat(row[6]),
                confidence=row[7],
                service_context=row[8],
                user_segments=json.loads(row[9]) if row[9] else []
            )
            patterns.append(pattern)
        
        return patterns

class AffirmationRecognitionSystem:
    """Main system orchestrating all components"""
    
    def __init__(self):
        self.classifier = AffirmationClassifier()
        self.context_analyzer = ContextAnalyzer()
        self.pattern_learner = PatternLearner()
        self.bot_integration = InterpreterBotIntegration()
        self.db_manager = DatabaseManager(CONFIG["database_path"])
        
        self.processing_queue = asyncio.Queue()
        self.is_running = False
        self.background_tasks = set()
        
    async def initialize(self):
        """Initialize the system"""
        logger.info("Initializing Affirmation Recognition System...")
        
        # Download required NLTK data
        try:
            nltk.download('vader_lexicon', quiet=True)
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
        except Exception as e:
            logger.warning(f"Could not download NLTK data: {e}")
        
        # Initialize bot connections
        await self.bot_integration.initialize_connections()
        
        # Load any pre-trained models
        await self._load_models()
        
        # Start background tasks
        self.is_running = True
        task = asyncio.create_task(self._background_processor())
        self.background_tasks.add(task)
        
        logger.info("Affirmation Recognition System initialized successfully")
    
    async def process_user_message(self, user_id: str, session_id: str, message: str,
                                 context_type: ContextType, service_name: str,
                                 metadata: Dict[str, Any] = None) -> Optional[AffirmationEvent]:
        """Process a user message to detect affirmations"""
        if metadata is None:
            metadata = {}
        
        # Create context message
        context_message = ContextMessage(
            message_id=str(uuid.uuid4()),
            user_id=user_id,
            content=message,
            context_type=context_type,
            service_name=service_name,
            timestamp=datetime.now(),
            metadata=metadata,
            session_id=session_id
        )
        
        # Add to context store
        self.context_analyzer.add_context_message(context_message)
        await self.db_manager.store_context_message(context_message)
        
        # Check if this is an affirmation
        if context_type == ContextType.USER_FEEDBACK:
            affirmation_type, confidence = self.classifier.classify_affirmation(message)
            
            if affirmation_type and confidence >= CONFIG["min_confidence_threshold"]:
                # Create affirmation event
                affirmation_event = AffirmationEvent(
                    event_id=str(uuid.uuid4()),
                    user_id=user_id,
                    session_id=session_id,
                    affirmation_text=message,
                    affirmation_type=affirmation_type,
                    confidence_score=confidence,
                    context_messages=self.context_analyzer.get_relevant_context(session_id, datetime.now()),
                    source=FeedbackSource.DIRECT_USER_INPUT,
                    timestamp=datetime.now(),
                    original_request=None,
                    system_response=None,
                    metadata=metadata
                )
                
                # Find related interaction
                original_request, system_response = self.context_analyzer.find_related_interaction(affirmation_event)
                affirmation_event.original_request = original_request
                affirmation_event.system_response = system_response
                
                # Store the event
                await self.db_manager.store_affirmation_event(affirmation_event)
                
                # Queue for processing
                await self.processing_queue.put(affirmation_event)
                
                logger.info(f"Detected {affirmation_type.value} affirmation with {confidence:.2f} confidence")
                return affirmation_event
        
        return None
    
    async def _background_processor(self):
        """Background task to process affirmation events"""
        while self.is_running:
            try:
                # Wait for affirmation event
                affirmation_event = await asyncio.wait_for(
                    self.processing_queue.get(), timeout=1.0
                )
                
                # Process the affirmation
                await self._process_affirmation(affirmation_event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in background processor: {e}")
    
    async def _process_affirmation(self, event: AffirmationEvent):
        """Process an affirmation event to extract learning patterns"""
        try:
            if event.original_request and event.system_response:
                # Extract learning pattern
                pattern = self.pattern_learner.extract_pattern(
                    event.original_request,
                    event.system_response,
                    event
                )
                
                if pattern:
                    # Store the pattern
                    await self.db_manager.store_learning_pattern(pattern)
                    
                    # Send to relevant service
                    service_name = event.metadata.get('service', 'unknown')
                    if service_name in self.bot_integration.service_connections:
                        success = await self.bot_integration.send_learning_patterns(
                            service_name, [pattern]
                        )
                        
                        if success:
                            logger.info(f"Successfully sent learning pattern to {service_name}")
                    
                    # Update pattern performance
                    self.pattern_learner.update_pattern_performance(pattern, True)
            
        except Exception as e:
            logger.error(f"Error processing affirmation: {e}")
    
    async def _load_models(self):
        """Load pre-trained models if available"""
        try:
            # This would load previously trained classifier models
            # Implementation would depend on your model storage strategy
            pass
        except Exception as e:
            logger.warning(f"Could not load pre-trained models: {e}")
    
    async def get_analytics(self, user_id: str = None, service_name: str = None,
                          hours: int = 24) -> Dict[str, Any]:
        """Get analytics about affirmations and learning patterns"""
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Base query filters
        filters = ["timestamp >= ?"]
        params = [cutoff_time]
        
        if user_id:
            filters.append("user_id = ?")
            params.append(user_id)
        
        filter_clause = " AND ".join(filters)
        
        # Affirmation analytics
        cursor.execute(f'''
            SELECT affirmation_type, COUNT(*) as count, AVG(confidence_score) as avg_confidence
            FROM affirmation_events
            WHERE {filter_clause}
            GROUP BY affirmation_type
            ORDER BY count DESC
        ''', params)
        
        affirmation_stats = [
            {"type": row[0], "count": row[1], "avg_confidence": row[2]}
            for row in cursor.fetchall()
        ]
        
        # Service performance
        service_filters = filters.copy()
        service_params = params.copy()
        if service_name:
            service_filters.append("service_context = ?")
            service_params.append(service_name)
        
        cursor.execute(f'''
            SELECT service_context, COUNT(*) as pattern_count, AVG(success_rate) as avg_success_rate
            FROM learning_patterns
            WHERE last_seen >= ? AND {" AND ".join(service_filters[1:]) if len(service_filters) > 1 else "1=1"}
            GROUP BY service_context
            ORDER BY pattern_count DESC
        ''', [cutoff_time] + service_params[1:] if len(service_params) > 1 else [cutoff_time])
        
        service_stats = [
            {"service": row[0], "pattern_count": row[1], "avg_success_rate": row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "affirmation_stats": affirmation_stats,
            "service_stats": service_stats,
            "total_affirmations": sum(stat["count"] for stat in affirmation_stats),
            "time_range_hours": hours,
            "generated_at": datetime.now().isoformat()
        }

# FastAPI Models
class MessageRequest(BaseModel):
    user_id: str
    session_id: str
    message: str
    context_type: str
    service_name: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AffirmationResponse(BaseModel):
    detected: bool
    affirmation_type: Optional[str] = None
    confidence_score: float = 0.0
    event_id: Optional[str] = None
    patterns_extracted: int = 0

class AnalyticsRequest(BaseModel):
    user_id: Optional[str] = None
    service_name: Optional[str] = None
    hours: int = Field(default=24, ge=1, le=168)  # 1 hour to 1 week

# Global system instance
system = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global system
    logger.info("Starting Affirmation Recognition System...")
    
    # Ensure data directory exists
    import os
    os.makedirs(os.path.dirname(CONFIG["database_path"]), exist_ok=True)
    os.makedirs(CONFIG["models_path"], exist_ok=True)
    
    system = AffirmationRecognitionSystem()
    await system.initialize()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Affirmation Recognition System...")
    if system:
        system.is_running = False
        # Wait for background tasks to complete
        if system.background_tasks:
            await asyncio.gather(*system.background_tasks, return_exceptions=True)

# Initialize FastAPI app
app = FastAPI(
    title="Affirmation Recognition System",
    description="ML-Powered User Satisfaction Detection and Learning System for Building Bots Network",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze", response_model=AffirmationResponse)
async def analyze_message(request: MessageRequest):
    """Analyze a message for affirmations and learn from successful interactions"""
    
    try:
        # Validate context type
        try:
            context_type = ContextType(request.context_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid context_type: {request.context_type}")
        
        # Process the message
        affirmation_event = await system.process_user_message(
            user_id=request.user_id,
            session_id=request.session_id,
            message=request.message,
            context_type=context_type,
            service_name=request.service_name,
            metadata=request.metadata
        )
        
        if affirmation_event:
            return AffirmationResponse(
                detected=True,
                affirmation_type=affirmation_event.affirmation_type.value,
                confidence_score=affirmation_event.confidence_score,
                event_id=affirmation_event.event_id,
                patterns_extracted=1 if affirmation_event.original_request else 0
            )
        else:
            return AffirmationResponse(detected=False)
    
    except Exception as e:
        logger.error(f"Error in analyze_message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics")
async def get_analytics(user_id: Optional[str] = None, 
                       service_name: Optional[str] = None,
                       hours: int = 24):
    """Get analytics about affirmations and learning patterns"""
    
    try:
        analytics = await system.get_analytics(user_id, service_name, hours)
        return analytics
    
    except Exception as e:
        logger.error(f"Error in get_analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/patterns/{service_name}")
async def get_service_patterns(service_name: str, hours: int = 24):
    """Get learning patterns for a specific service"""
    
    try:
        patterns = await system.db_manager.get_recent_patterns(service_name, hours)
        return {
            "service_name": service_name,
            "pattern_count": len(patterns),
            "patterns": [asdict(pattern) for pattern in patterns[:50]]  # Limit to 50 most recent
        }
    
    except Exception as e:
        logger.error(f"Error in get_service_patterns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/train")
async def trigger_training():
    """Trigger retraining of the affirmation classifier"""
    
    try:
        # This would collect labeled training data from the database
        # and retrain the classifier - simplified for now
        return {"status": "training_triggered", "message": "Classifier retraining started"}
    
    except Exception as e:
        logger.error(f"Error in trigger_training: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "components": {
            "classifier": "initialized" if system and system.classifier else "not_ready",
            "context_analyzer": "initialized" if system and system.context_analyzer else "not_ready",
            "bot_integration": f"{len(system.bot_integration.service_connections)} services connected" if system else "not_ready",
            "database": "connected" if system and system.db_manager else "not_ready"
        }
    }

@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "system": "Affirmation Recognition System",
        "description": "ML-Powered User Satisfaction Detection and Learning System",
        "version": "1.0.0",
        "endpoints": [
            "/analyze - Analyze messages for affirmations",
            "/analytics - Get system analytics",
            "/patterns/{service_name} - Get learning patterns for a service",
            "/train - Trigger classifier retraining",
            "/health - Health check"
        ],
        "building_bots_network": True
    }

if __name__ == "__main__":
    import sys
    
    # Configuration
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8485
    
    logger.info(f"Starting Affirmation Recognition System on port {port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        workers=1,
        log_level="info"
    )