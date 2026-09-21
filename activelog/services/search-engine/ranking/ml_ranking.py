#!/usr/bin/env python3
"""
ActiveLog Unified Search Engine - ML-based Result Ranking
Machine learning model for intelligent search result ranking
"""

import json
import logging
import time
import pickle
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import sqlite3
import threading
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class RankingFeatures:
    """Features for ranking a search result"""
    # Content features
    title_query_similarity: float = 0.0
    content_query_similarity: float = 0.0
    exact_match_count: int = 0
    partial_match_count: int = 0
    
    # Metadata features
    content_length: int = 0
    title_length: int = 0
    has_url: bool = False
    file_size: float = 0.0
    
    # Temporal features
    days_since_created: float = 0.0
    days_since_modified: float = 0.0
    is_recent: bool = False
    
    # Service features
    service_priority: float = 0.0
    content_type_score: float = 0.0
    
    # User interaction features
    click_through_rate: float = 0.0
    historical_relevance: float = 0.0
    user_preference_score: float = 0.0
    
    # Search context features
    query_complexity: float = 0.0
    search_type_match: float = 0.0
    filter_match_score: float = 0.0
    
    def to_vector(self) -> np.ndarray:
        """Convert features to numpy vector"""
        return np.array([
            self.title_query_similarity,
            self.content_query_similarity,
            self.exact_match_count,
            self.partial_match_count,
            self.content_length / 1000.0,  # Normalize
            self.title_length / 100.0,     # Normalize
            1.0 if self.has_url else 0.0,
            min(self.file_size / 1000000.0, 10.0),  # Normalize MB, cap at 10MB
            min(self.days_since_created / 365.0, 5.0),  # Normalize years, cap at 5
            min(self.days_since_modified / 365.0, 5.0),
            1.0 if self.is_recent else 0.0,
            self.service_priority,
            self.content_type_score,
            self.click_through_rate,
            self.historical_relevance,
            self.user_preference_score,
            self.query_complexity,
            self.search_type_match,
            self.filter_match_score
        ])

@dataclass
class RankingExample:
    """Training example for ranking model"""
    query: str
    document_id: str
    features: RankingFeatures
    relevance_score: float  # Ground truth relevance (0-1)
    user_id: Optional[str] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()

class FeatureExtractor:
    """Extract ranking features from search results"""
    
    def __init__(self):
        # Text similarity vectorizer
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )
        self.vectorizer_fitted = False
        
        # Service priorities (can be configured)
        self.service_priorities = {
            'PersonalLog': 1.0,
            'BusinessLog': 0.9,
            'TaskManager': 0.8,
            'NoteTaker': 0.7,
            'Calendar': 0.6,
            'Contacts': 0.5,
            'FinanceLog': 0.9,
            'HealthLog': 0.8,
        }
        
        # Content type scores
        self.content_type_scores = {
            'document': 1.0,
            'email': 0.9,
            'note': 0.8,
            'task': 0.7,
            'image': 0.6,
            'audio': 0.5,
            'video': 0.4
        }
    
    def fit_vectorizer(self, corpus: List[str]):
        """Fit TF-IDF vectorizer on corpus"""
        if not corpus:
            return
        
        try:
            self.tfidf_vectorizer.fit(corpus)
            self.vectorizer_fitted = True
            logger.info(f"Fitted TF-IDF vectorizer on {len(corpus)} documents")
        except Exception as e:
            logger.error(f"Error fitting vectorizer: {e}")
    
    def extract_features(self, query: str, result: Dict[str, Any], 
                        user_id: str = None) -> RankingFeatures:
        """Extract ranking features for a search result"""
        features = RankingFeatures()
        
        # Get text content
        title = result.get('title', '')
        content = result.get('content', '')
        metadata = result.get('metadata', {})
        
        # Content similarity features
        if self.vectorizer_fitted:
            features.title_query_similarity = self._calculate_similarity(query, title)
            features.content_query_similarity = self._calculate_similarity(query, content)
        
        # Exact and partial match counts
        query_terms = query.lower().split()
        title_lower = title.lower()
        content_lower = content.lower()
        
        for term in query_terms:
            if term in title_lower:
                features.exact_match_count += title_lower.count(term)
            if term in content_lower:
                features.partial_match_count += content_lower.count(term)
        
        # Metadata features
        features.content_length = len(content)
        features.title_length = len(title)
        features.has_url = bool(result.get('url', ''))
        features.file_size = metadata.get('file_size', 0)
        
        # Temporal features
        current_time = time.time()
        created_at = metadata.get('created_at', current_time)
        modified_at = metadata.get('last_modified', current_time)
        
        features.days_since_created = (current_time - created_at) / 86400
        features.days_since_modified = (current_time - modified_at) / 86400
        features.is_recent = features.days_since_modified <= 7
        
        # Service and content type features
        service_id = result.get('service_id', '')
        content_type = result.get('content_type', 'document')
        
        features.service_priority = self.service_priorities.get(service_id, 0.5)
        features.content_type_score = self.content_type_scores.get(content_type, 0.5)
        
        # Query complexity
        features.query_complexity = len(query.split()) / 10.0  # Normalize
        
        # Search type match (if available)
        search_type = metadata.get('search_type', 'text')
        if search_type == 'semantic':
            features.search_type_match = 1.0
        elif search_type == 'fuzzy':
            features.search_type_match = 0.8
        else:
            features.search_type_match = 0.6
        
        return features
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts"""
        if not text1 or not text2 or not self.vectorizer_fitted:
            return 0.0
        
        try:
            vectors = self.tfidf_vectorizer.transform([text1, text2])
            similarity = cosine_similarity(vectors[0], vectors[1])[0, 0]
            return float(similarity)
        except Exception:
            return 0.0

class UserBehaviorTracker:
    """Track user behavior for ranking model training"""
    
    def __init__(self, db_path: str = "user_behavior.db"):
        self.db_path = db_path
        self.db_lock = threading.Lock()
        
        # In-memory caches
        self.click_through_rates = defaultdict(float)
        self.user_preferences = defaultdict(lambda: defaultdict(float))
        self.query_result_interactions = defaultdict(list)
        
        self._init_database()
        self._load_behavior_data()
    
    def _init_database(self):
        """Initialize database for user behavior tracking"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            
            # Click tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS click_events (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    user_id TEXT,
                    position INTEGER,
                    timestamp REAL NOT NULL,
                    session_id TEXT,
                    INDEX(query),
                    INDEX(document_id),
                    INDEX(user_id)
                )
            """)
            
            # Relevance feedback
            conn.execute("""
                CREATE TABLE IF NOT EXISTS relevance_feedback (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    user_id TEXT,
                    relevance_score REAL NOT NULL,
                    timestamp REAL NOT NULL,
                    INDEX(query),
                    INDEX(document_id)
                )
            """)
            
            conn.commit()
            conn.close()
    
    def _load_behavior_data(self):
        """Load behavior data from database"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                
                # Load click-through rates
                cursor = conn.execute("""
                    SELECT document_id, COUNT(*) as clicks,
                           COUNT(DISTINCT query) as queries
                    FROM click_events 
                    WHERE timestamp > ?
                    GROUP BY document_id
                """, (time.time() - 2592000,))  # Last 30 days
                
                for row in cursor.fetchall():
                    doc_id, clicks, queries = row
                    self.click_through_rates[doc_id] = clicks / max(queries, 1)
                
                conn.close()
                
        except sqlite3.Error as e:
            logger.error(f"Error loading behavior data: {e}")
    
    def record_click(self, query: str, document_id: str, position: int, 
                    user_id: str = None, session_id: str = None):
        """Record a click event"""
        click_id = hashlib.md5(f"{query}{document_id}{time.time()}".encode()).hexdigest()
        
        # Update in-memory cache
        self.click_through_rates[document_id] = (
            self.click_through_rates[document_id] * 0.9 + 0.1
        )  # Exponential moving average
        
        # Record interaction
        self.query_result_interactions[query].append({
            'document_id': document_id,
            'position': position,
            'clicked': True,
            'timestamp': time.time()
        })
        
        # Persist to database
        def _db_insert():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    INSERT INTO click_events 
                    (id, query, document_id, user_id, position, timestamp, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (click_id, query, document_id, user_id, position, time.time(), session_id))
                conn.commit()
                conn.close()
        
        # Run in background
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(_db_insert)
    
    def record_relevance_feedback(self, query: str, document_id: str, 
                                 relevance_score: float, user_id: str = None):
        """Record explicit relevance feedback"""
        feedback_id = hashlib.md5(f"{query}{document_id}{relevance_score}{time.time()}".encode()).hexdigest()
        
        # Persist to database
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO relevance_feedback 
                (id, query, document_id, user_id, relevance_score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (feedback_id, query, document_id, user_id, relevance_score, time.time()))
            conn.commit()
            conn.close()
    
    def get_click_through_rate(self, document_id: str) -> float:
        """Get click-through rate for document"""
        return self.click_through_rates.get(document_id, 0.0)
    
    def get_user_preference_score(self, user_id: str, service_id: str) -> float:
        """Get user preference score for service"""
        return self.user_preferences[user_id].get(service_id, 0.5)

class MLRankingModel:
    """Machine learning-based ranking model"""
    
    def __init__(self, model_path: str = "ranking_model.pkl"):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Feature extractor and behavior tracker
        self.feature_extractor = FeatureExtractor()
        self.behavior_tracker = UserBehaviorTracker()
        
        # Training data
        self.training_examples: List[RankingExample] = []
        
        # Model performance
        self.model_metrics = {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "training_examples": 0
        }
        
        # Try to load existing model
        self._load_model()
    
    def _load_model(self):
        """Load pre-trained model"""
        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
                self.model = model_data['model']
                self.scaler = model_data['scaler']
                self.model_metrics = model_data.get('metrics', self.model_metrics)
                self.is_trained = True
                
            logger.info("Loaded pre-trained ranking model")
            
        except FileNotFoundError:
            logger.info("No pre-trained model found, will train from scratch")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
    
    def _save_model(self):
        """Save trained model"""
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'metrics': self.model_metrics
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
                
            logger.info("Saved ranking model")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def add_training_example(self, query: str, document_id: str, result: Dict[str, Any],
                           relevance_score: float, user_id: str = None):
        """Add training example"""
        features = self.feature_extractor.extract_features(query, result, user_id)
        
        # Add behavior-based features
        features.click_through_rate = self.behavior_tracker.get_click_through_rate(document_id)
        features.historical_relevance = relevance_score
        
        if user_id:
            service_id = result.get('service_id', '')
            features.user_preference_score = self.behavior_tracker.get_user_preference_score(user_id, service_id)
        
        example = RankingExample(
            query=query,
            document_id=document_id,
            features=features,
            relevance_score=relevance_score,
            user_id=user_id
        )
        
        self.training_examples.append(example)
        
        # Auto-retrain if we have enough examples
        if len(self.training_examples) % 100 == 0:
            asyncio.create_task(self.train_model())
    
    async def train_model(self):
        """Train the ranking model"""
        if len(self.training_examples) < 50:  # Minimum examples needed
            logger.info(f"Need more training examples: {len(self.training_examples)}/50")
            return
        
        try:
            logger.info(f"Training ranking model with {len(self.training_examples)} examples")
            
            # Prepare training data
            X = []
            y = []
            
            for example in self.training_examples:
                X.append(example.features.to_vector())
                y.append(example.relevance_score)
            
            X = np.array(X)
            y = np.array(y)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model (using Gradient Boosting for better performance)
            self.model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
            
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            train_score = self.model.score(X_train_scaled, y_train)
            test_score = self.model.score(X_test_scaled, y_test)
            
            self.model_metrics.update({
                "training_score": train_score,
                "test_score": test_score,
                "training_examples": len(self.training_examples)
            })
            
            self.is_trained = True
            
            # Save model
            self._save_model()
            
            logger.info(f"Model trained - Train score: {train_score:.3f}, Test score: {test_score:.3f}")
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
    
    async def rerank_results(self, query, results: List[Dict[str, Any]], 
                           user_id: str = None) -> List[Dict[str, Any]]:
        """Rerank search results using ML model"""
        if not self.is_trained or not results:
            return results
        
        try:
            # Extract features for each result
            scored_results = []
            
            for result in results:
                features = self.feature_extractor.extract_features(query.query if hasattr(query, 'query') else str(query), result, user_id)
                
                # Add behavior features
                doc_id = result.get('document_id', '')
                features.click_through_rate = self.behavior_tracker.get_click_through_rate(doc_id)
                
                if user_id:
                    service_id = result.get('service_id', '')
                    features.user_preference_score = self.behavior_tracker.get_user_preference_score(user_id, service_id)
                
                # Get ML prediction
                feature_vector = features.to_vector().reshape(1, -1)
                feature_vector_scaled = self.scaler.transform(feature_vector)
                ml_score = self.model.predict(feature_vector_scaled)[0]
                
                # Combine with original score
                original_score = result.get('score', 0.5)
                combined_score = 0.7 * ml_score + 0.3 * original_score
                
                # Update result score
                result_copy = result.copy()
                result_copy['score'] = combined_score
                result_copy['ml_score'] = ml_score
                result_copy['original_score'] = original_score
                
                scored_results.append(result_copy)
            
            # Sort by combined score
            scored_results.sort(key=lambda x: x['score'], reverse=True)
            
            return scored_results
            
        except Exception as e:
            logger.error(f"Error in ML reranking: {e}")
            return results
    
    def record_click(self, query: str, document_id: str, position: int, user_id: str = None):
        """Record click for learning"""
        self.behavior_tracker.record_click(query, document_id, position, user_id)
        
        # Implicit positive feedback
        relevance_score = max(0.5, 1.0 - (position * 0.1))  # Higher positions get higher scores
        self.behavior_tracker.record_relevance_feedback(query, document_id, relevance_score, user_id)
    
    def record_explicit_feedback(self, query: str, document_id: str, relevance_score: float, 
                                result: Dict[str, Any], user_id: str = None):
        """Record explicit relevance feedback"""
        self.behavior_tracker.record_relevance_feedback(query, document_id, relevance_score, user_id)
        self.add_training_example(query, document_id, result, relevance_score, user_id)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and metrics"""
        return {
            "is_trained": self.is_trained,
            "training_examples": len(self.training_examples),
            "model_type": type(self.model).__name__ if self.model else "None",
            "metrics": self.model_metrics,
            "feature_count": 19  # Number of features in RankingFeatures
        }
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from trained model"""
        if not self.is_trained or not hasattr(self.model, 'feature_importances_'):
            return {}
        
        feature_names = [
            'title_query_similarity', 'content_query_similarity', 'exact_match_count',
            'partial_match_count', 'content_length', 'title_length', 'has_url',
            'file_size', 'days_since_created', 'days_since_modified', 'is_recent',
            'service_priority', 'content_type_score', 'click_through_rate',
            'historical_relevance', 'user_preference_score', 'query_complexity',
            'search_type_match', 'filter_match_score'
        ]
        
        importances = self.model.feature_importances_
        
        return dict(zip(feature_names, importances.tolist()))