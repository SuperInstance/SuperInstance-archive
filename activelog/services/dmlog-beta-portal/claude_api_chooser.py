#!/usr/bin/env python3
"""
Claude API Chooser Bot - Intelligent Model Selection System
Selects optimal Claude model for each task and learns from response quality
"""

import os
import json
import time
import hashlib
import logging
import asyncio
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import sqlite3
import pickle
import gzip
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
import anthropic

# Configure logging
logger = logging.getLogger(__name__)

class ClaudeModel(Enum):
    HAIKU = "claude-3-haiku-20240307"
    SONNET = "claude-3-sonnet-20240229" 
    OPUS = "claude-3-opus-20240229"
    OPUS_41 = "claude-opus-4-1-20250805"

class TaskType(Enum):
    CODING = "coding"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    CONVERSATION = "conversation"
    TECHNICAL = "technical"
    RESEARCH = "research"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"

@dataclass
class TaskFeatures:
    """Compact task features for ML training"""
    task_type: str
    text_length: int
    complexity_score: float
    technical_keywords: int
    code_blocks: int
    question_marks: int
    urgency_words: int
    timestamp: float
    
    def to_vector(self) -> List[float]:
        """Convert to feature vector for ML"""
        return [
            hash(self.task_type) % 1000 / 1000.0,  # Normalized hash
            min(self.text_length / 10000.0, 1.0),  # Normalized length
            self.complexity_score,
            min(self.technical_keywords / 20.0, 1.0),
            min(self.code_blocks / 10.0, 1.0),
            min(self.question_marks / 5.0, 1.0),
            min(self.urgency_words / 5.0, 1.0)
        ]

@dataclass 
class ResponseQuality:
    """Compact response quality metrics"""
    model: str
    task_features: TaskFeatures
    user_rating: float  # 0.0-1.0
    response_time: float
    token_efficiency: float
    task_completion: float  # 0.0-1.0
    user_feedback: str  # "good", "bad", "excellent", "poor"
    timestamp: float
    
    def to_compact_note(self) -> Dict[str, Any]:
        """Convert to compact note for storage"""
        return {
            'm': self.model[-4:],  # Last 4 chars of model
            't': self.task_features.task_type[:3],  # First 3 chars
            'l': min(int(self.task_features.text_length / 100), 255),  # Scaled length
            'c': int(self.task_features.complexity_score * 10),
            'r': int(self.user_rating * 10),
            'rt': min(int(self.response_time), 999),
            'te': int(self.token_efficiency * 10),
            'tc': int(self.task_completion * 10),
            'f': self.user_feedback[0],  # First char of feedback
            'ts': int(self.timestamp)
        }
    
    @classmethod
    def from_compact_note(cls, note: Dict[str, Any]) -> 'ResponseQuality':
        """Reconstruct from compact note"""
        # This is for reference - actual reconstruction would need model mapping
        pass

class ClaudeAPIChooser:
    """Intelligent Claude model selector with ML training"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None
        
        # Model configurations
        self.models = {
            ClaudeModel.HAIKU: {
                'speed': 0.95,
                'cost': 0.25,  # Relative cost
                'capability': 0.7,
                'context_limit': 200000,
                'best_for': ['simple', 'fast', 'conversation']
            },
            ClaudeModel.SONNET: {
                'speed': 0.8,
                'cost': 1.0,
                'capability': 0.85,
                'context_limit': 200000,
                'best_for': ['analysis', 'coding', 'technical']
            },
            ClaudeModel.OPUS: {
                'speed': 0.6,
                'cost': 5.0,
                'capability': 0.95,
                'context_limit': 200000,
                'best_for': ['complex', 'creative', 'research']
            },
            ClaudeModel.OPUS_41: {
                'speed': 0.65,
                'cost': 6.0,
                'capability': 1.0,
                'context_limit': 200000,
                'best_for': ['advanced', 'optimization', 'debugging']
            }
        }
        
        # ML Components
        self.vectorizer = TfidfVectorizer(max_features=100, ngram_range=(1, 2))
        self.scaler = StandardScaler()
        self.classifier = RandomForestClassifier(n_estimators=50, max_depth=10)
        self.is_trained = False
        
        # Data storage
        self.db_path = './data/claude_chooser.db'
        self.notes_batch_size = 1000
        self.compact_notes = deque(maxlen=10000)  # Keep last 10k notes
        self.training_queue = deque(maxlen=5000)
        
        # Performance tracking
        self.model_performance = defaultdict(lambda: {
            'total_requests': 0,
            'avg_rating': 0.0,
            'avg_response_time': 0.0,
            'success_rate': 0.0,
            'last_updated': time.time()
        })
        
        # Initialize database and load existing data
        self._initialize_database()
        self._load_existing_data()
        
        # Background training task
        self.training_active = False
        self.last_training = 0
        
    def _initialize_database(self):
        """Initialize SQLite database for compact storage"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Compact notes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compact_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_short TEXT,
                task_type_short TEXT,
                length_scaled INTEGER,
                complexity INTEGER,
                rating INTEGER,
                response_time INTEGER,
                token_efficiency INTEGER,
                task_completion INTEGER,
                feedback_char TEXT,
                timestamp INTEGER,
                batch_id INTEGER DEFAULT 0
            )
        ''')
        
        # Model performance cache
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_performance (
                model TEXT PRIMARY KEY,
                total_requests INTEGER,
                avg_rating REAL,
                avg_response_time REAL,
                success_rate REAL,
                last_updated INTEGER
            )
        ''')
        
        # Training batches metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_batches (
                batch_id INTEGER PRIMARY KEY,
                note_count INTEGER,
                training_accuracy REAL,
                created_at INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def _load_existing_data(self):
        """Load existing performance data and recent notes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load model performance
        cursor.execute('SELECT * FROM model_performance')
        for row in cursor.fetchall():
            model, total, rating, response_time, success_rate, updated = row
            self.model_performance[model] = {
                'total_requests': total,
                'avg_rating': rating,
                'avg_response_time': response_time,
                'success_rate': success_rate,
                'last_updated': updated
            }
        
        # Load recent compact notes for training queue
        cursor.execute('''
            SELECT * FROM compact_notes 
            ORDER BY timestamp DESC 
            LIMIT 1000
        ''')
        
        for row in cursor.fetchall():
            note = {
                'm': row[1], 't': row[2], 'l': row[3], 'c': row[4],
                'r': row[5], 'rt': row[6], 'te': row[7], 'tc': row[8],
                'f': row[9], 'ts': row[10]
            }
            self.compact_notes.append(note)
            
        conn.close()
        logger.info(f"Loaded {len(self.model_performance)} model performance records")
        logger.info(f"Loaded {len(self.compact_notes)} recent notes")
        
    def analyze_task(self, text: str, context: Dict[str, Any] = None) -> TaskFeatures:
        """Analyze task to extract features for model selection"""
        context = context or {}
        
        # Basic text analysis
        text_length = len(text)
        words = text.lower().split()
        
        # Detect task type
        task_type = self._detect_task_type(text, context)
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity(text, words)
        
        # Count technical indicators
        technical_keywords = self._count_technical_keywords(words)
        code_blocks = text.count('```') + text.count('def ') + text.count('class ')
        question_marks = text.count('?')
        urgency_words = len([w for w in words if w in ['urgent', 'asap', 'quickly', 'fast', 'immediate']])
        
        return TaskFeatures(
            task_type=task_type.value,
            text_length=text_length,
            complexity_score=complexity_score,
            technical_keywords=technical_keywords,
            code_blocks=code_blocks,
            question_marks=question_marks,
            urgency_words=urgency_words,
            timestamp=time.time()
        )
    
    def _detect_task_type(self, text: str, context: Dict[str, Any]) -> TaskType:
        """Detect the type of task from text and context"""
        text_lower = text.lower()
        
        # Code-related keywords
        if any(word in text_lower for word in ['code', 'function', 'debug', 'error', 'python', 'javascript', 'bug']):
            if 'debug' in text_lower or 'error' in text_lower or 'fix' in text_lower:
                return TaskType.DEBUGGING
            elif 'optimize' in text_lower or 'improve' in text_lower or 'performance' in text_lower:
                return TaskType.OPTIMIZATION
            else:
                return TaskType.CODING
                
        # Analysis keywords
        elif any(word in text_lower for word in ['analyze', 'analysis', 'data', 'statistics', 'metrics']):
            return TaskType.ANALYSIS
            
        # Creative keywords
        elif any(word in text_lower for word in ['write', 'story', 'creative', 'poem', 'article']):
            return TaskType.CREATIVE
            
        # Research keywords  
        elif any(word in text_lower for word in ['research', 'find', 'search', 'investigate', 'study']):
            return TaskType.RESEARCH
            
        # Technical keywords
        elif any(word in text_lower for word in ['technical', 'system', 'architecture', 'design', 'implementation']):
            return TaskType.TECHNICAL
            
        # Default to conversation
        else:
            return TaskType.CONVERSATION
    
    def _calculate_complexity(self, text: str, words: List[str]) -> float:
        """Calculate task complexity score (0.0-1.0)"""
        complexity = 0.0
        
        # Length factor (longer = more complex)
        complexity += min(len(words) / 1000.0, 0.3)
        
        # Technical depth
        technical_terms = ['algorithm', 'optimization', 'architecture', 'implementation', 'infrastructure']
        complexity += min(sum(1 for term in technical_terms if term in text.lower()) / 10.0, 0.2)
        
        # Code complexity
        code_indicators = ['class', 'function', 'async', 'await', 'import', 'from']
        complexity += min(sum(1 for indicator in code_indicators if indicator in text.lower()) / 10.0, 0.2)
        
        # Question complexity (multiple questions = complex)
        complexity += min(text.count('?') / 10.0, 0.1)
        
        # Abstract concepts
        abstract_terms = ['design', 'strategy', 'approach', 'methodology', 'framework']
        complexity += min(sum(1 for term in abstract_terms if term in text.lower()) / 10.0, 0.2)
        
        return min(complexity, 1.0)
        
    def _count_technical_keywords(self, words: List[str]) -> int:
        """Count technical keywords in text"""
        technical_keywords = {
            'api', 'database', 'server', 'client', 'http', 'json', 'xml',
            'python', 'javascript', 'sql', 'html', 'css', 'react', 'vue',
            'docker', 'kubernetes', 'aws', 'cloud', 'microservice', 'rest',
            'authentication', 'security', 'encryption', 'algorithm', 'ml',
            'ai', 'machine', 'learning', 'neural', 'network', 'model'
        }
        
        return sum(1 for word in words if word in technical_keywords)
    
    async def choose_model(self, text: str, context: Dict[str, Any] = None,
                          preferences: Dict[str, float] = None) -> ClaudeModel:
        """Choose the best Claude model for the given task"""
        
        # Analyze task
        features = self.analyze_task(text, context)
        
        # Default preferences (can be overridden)
        prefs = {
            'speed': 0.3,
            'cost': 0.2,
            'capability': 0.5
        }
        if preferences:
            prefs.update(preferences)
        
        # Use ML model if trained
        if self.is_trained:
            try:
                prediction = await self._ml_predict_model(features)
                if prediction:
                    logger.info(f"ML prediction: {prediction}")
                    return prediction
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")
        
        # Fallback to rule-based selection
        return self._rule_based_selection(features, prefs)
    
    async def _ml_predict_model(self, features: TaskFeatures) -> Optional[ClaudeModel]:
        """Use trained ML model to predict best Claude model"""
        if not self.is_trained:
            return None
            
        try:
            # Convert features to vector
            feature_vector = np.array([features.to_vector()])
            
            # Predict model
            prediction = self.classifier.predict(feature_vector)[0]
            
            # Map prediction back to model
            model_mapping = {
                0: ClaudeModel.HAIKU,
                1: ClaudeModel.SONNET, 
                2: ClaudeModel.OPUS,
                3: ClaudeModel.OPUS_41
            }
            
            return model_mapping.get(prediction, ClaudeModel.SONNET)
            
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            return None
    
    def _rule_based_selection(self, features: TaskFeatures, 
                            preferences: Dict[str, float]) -> ClaudeModel:
        """Rule-based model selection as fallback"""
        
        # High complexity tasks
        if features.complexity_score > 0.7:
            if features.task_type in ['debugging', 'optimization']:
                return ClaudeModel.OPUS_41
            else:
                return ClaudeModel.OPUS
                
        # Code-heavy tasks
        if features.code_blocks > 3 or features.technical_keywords > 10:
            if features.task_type == 'debugging':
                return ClaudeModel.OPUS_41
            else:
                return ClaudeModel.SONNET
                
        # Fast/simple tasks
        if (features.complexity_score < 0.3 and 
            features.text_length < 1000 and
            preferences.get('speed', 0) > 0.7):
            return ClaudeModel.HAIKU
            
        # Creative tasks
        if features.task_type == 'creative':
            return ClaudeModel.OPUS
            
        # Default balanced choice
        return ClaudeModel.SONNET
    
    async def make_request(self, text: str, model: ClaudeModel = None,
                          context: Dict[str, Any] = None, 
                          max_tokens: int = 4000) -> Dict[str, Any]:
        """Make request to chosen Claude model"""
        
        if not self.client:
            return {
                'success': False,
                'error': 'No API key configured',
                'model_used': None,
                'response_time': 0
            }
        
        # Choose model if not specified
        if not model:
            model = await self.choose_model(text, context)
            
        start_time = time.time()
        
        try:
            # Make API request
            response = self.client.messages.create(
                model=model.value,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": text}]
            )
            
            response_time = time.time() - start_time
            
            # Extract response text
            response_text = response.content[0].text if response.content else ""
            
            # Calculate token efficiency (response length / response time)
            token_efficiency = len(response_text) / max(response_time, 0.1)
            
            result = {
                'success': True,
                'response': response_text,
                'model_used': model.value,
                'response_time': response_time,
                'token_efficiency': token_efficiency,
                'usage': getattr(response, 'usage', None)
            }
            
            # Update model performance
            self._update_model_performance(model.value, response_time, True)
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"API request failed: {e}")
            
            # Update model performance for failure
            self._update_model_performance(model.value, response_time, False)
            
            return {
                'success': False,
                'error': str(e),
                'model_used': model.value,
                'response_time': response_time,
                'token_efficiency': 0
            }
    
    def record_feedback(self, request_id: str, user_rating: float,
                       task_features: TaskFeatures, model_used: str,
                       response_time: float, token_efficiency: float,
                       task_completion: float = 1.0,
                       user_feedback: str = "good"):
        """Record user feedback for ML training"""
        
        # Create response quality record
        quality = ResponseQuality(
            model=model_used,
            task_features=task_features,
            user_rating=max(0.0, min(user_rating, 1.0)),
            response_time=response_time,
            token_efficiency=token_efficiency,
            task_completion=task_completion,
            user_feedback=user_feedback,
            timestamp=time.time()
        )
        
        # Convert to compact note and store
        compact_note = quality.to_compact_note()
        self.compact_notes.append(compact_note)
        self.training_queue.append(quality)
        
        # Save to database
        self._save_compact_note(compact_note)
        
        # Update model performance
        self._update_model_performance_with_feedback(model_used, user_rating)
        
        # Trigger training if queue is full
        if len(self.training_queue) >= self.notes_batch_size:
            asyncio.create_task(self._trigger_batch_training())
            
        logger.info(f"Recorded feedback: {user_rating:.1f} for {model_used}")
    
    def _save_compact_note(self, note: Dict[str, Any]):
        """Save compact note to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO compact_notes 
            (model_short, task_type_short, length_scaled, complexity, rating,
             response_time, token_efficiency, task_completion, feedback_char, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            note['m'], note['t'], note['l'], note['c'], note['r'],
            note['rt'], note['te'], note['tc'], note['f'], note['ts']
        ))
        
        conn.commit()
        conn.close()
    
    def _update_model_performance(self, model: str, response_time: float, success: bool):
        """Update model performance metrics"""
        perf = self.model_performance[model]
        
        # Update counters
        perf['total_requests'] += 1
        
        # Update averages using exponential moving average
        alpha = 0.1  # Learning rate
        if perf['avg_response_time'] == 0:
            perf['avg_response_time'] = response_time
        else:
            perf['avg_response_time'] = (1 - alpha) * perf['avg_response_time'] + alpha * response_time
        
        # Update success rate
        if success:
            perf['success_rate'] = (1 - alpha) * perf['success_rate'] + alpha * 1.0
        else:
            perf['success_rate'] = (1 - alpha) * perf['success_rate'] + alpha * 0.0
            
        perf['last_updated'] = time.time()
        
        # Save to database periodically
        if perf['total_requests'] % 10 == 0:
            self._save_model_performance(model, perf)
    
    def _update_model_performance_with_feedback(self, model: str, rating: float):
        """Update model performance with user feedback"""
        perf = self.model_performance[model]
        
        # Update rating using exponential moving average
        alpha = 0.1
        if perf['avg_rating'] == 0:
            perf['avg_rating'] = rating
        else:
            perf['avg_rating'] = (1 - alpha) * perf['avg_rating'] + alpha * rating
            
        perf['last_updated'] = time.time()
        self._save_model_performance(model, perf)
    
    def _save_model_performance(self, model: str, perf: Dict[str, Any]):
        """Save model performance to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO model_performance
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            model, perf['total_requests'], perf['avg_rating'],
            perf['avg_response_time'], perf['success_rate'], perf['last_updated']
        ))
        
        conn.commit()
        conn.close()
    
    async def _trigger_batch_training(self):
        """Trigger ML model training with current batch"""
        if self.training_active:
            return
            
        self.training_active = True
        
        try:
            # Prepare training data from queue
            training_data = list(self.training_queue)
            self.training_queue.clear()
            
            if len(training_data) < 50:  # Need minimum data
                logger.info("Insufficient data for training")
                return
            
            logger.info(f"Starting batch training with {len(training_data)} samples")
            
            # Prepare features and labels
            X_features = []
            X_text = []
            y_labels = []
            
            for quality in training_data:
                X_features.append(quality.task_features.to_vector())
                X_text.append(f"{quality.task_features.task_type} {quality.task_features.complexity_score}")
                
                # Map model to label
                model_to_label = {
                    'haiku': 0, 'sonnet': 1, 'opus': 2, 'opus_41': 3
                }
                
                # Find model label
                model_label = 1  # Default to sonnet
                for key, value in model_to_label.items():
                    if key in quality.model.lower():
                        model_label = value
                        break
                
                # Weight label by quality (better responses more likely to be chosen)
                if quality.user_rating > 0.8:
                    y_labels.append(model_label)
                elif quality.user_rating < 0.3:
                    # Poor responses - suggest different model
                    y_labels.append((model_label + 1) % 4)
                else:
                    y_labels.append(model_label)
            
            # Train if we have diverse enough data
            if len(set(y_labels)) > 1:
                X_combined = np.array(X_features)
                y_combined = np.array(y_labels)
                
                # Train classifier
                self.classifier.fit(X_combined, y_combined)
                self.is_trained = True
                
                # Calculate training accuracy
                accuracy = self.classifier.score(X_combined, y_combined)
                
                # Save training batch info
                self._save_training_batch(len(training_data), accuracy)
                
                logger.info(f"Training completed. Accuracy: {accuracy:.3f}")
            else:
                logger.info("Not enough diverse data for training")
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
        finally:
            self.training_active = False
            self.last_training = time.time()
    
    def _save_training_batch(self, note_count: int, accuracy: float):
        """Save training batch metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO training_batches (note_count, training_accuracy, created_at)
            VALUES (?, ?, ?)
        ''', (note_count, accuracy, int(time.time())))
        
        conn.commit()
        conn.close()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        stats = {
            'model_performance': dict(self.model_performance),
            'total_notes': len(self.compact_notes),
            'training_queue_size': len(self.training_queue),
            'is_trained': self.is_trained,
            'last_training': self.last_training,
            'training_active': self.training_active
        }
        
        # Add model recommendations
        if self.model_performance:
            best_model = max(
                self.model_performance.items(),
                key=lambda x: x[1]['avg_rating'] * x[1]['success_rate']
            )
            stats['best_model'] = {
                'model': best_model[0],
                'score': best_model[1]['avg_rating'] * best_model[1]['success_rate']
            }
        
        return stats
    
    def cleanup_old_notes(self, days_to_keep: int = 30):
        """Clean up old notes to manage space"""
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count notes to be deleted
        cursor.execute('SELECT COUNT(*) FROM compact_notes WHERE timestamp < ?', (cutoff_time,))
        delete_count = cursor.fetchone()[0]
        
        # Delete old notes
        cursor.execute('DELETE FROM compact_notes WHERE timestamp < ?', (cutoff_time,))
        
        # Delete old training batches
        cursor.execute('DELETE FROM training_batches WHERE created_at < ?', (cutoff_time,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {delete_count} old notes")
        return delete_count

# Global instance
claude_chooser = ClaudeAPIChooser()

# Convenience functions for integration
async def choose_claude_model(text: str, context: Dict[str, Any] = None) -> ClaudeModel:
    """Choose best Claude model for task"""
    return await claude_chooser.choose_model(text, context)

async def make_claude_request(text: str, model: ClaudeModel = None, 
                             context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make request to chosen Claude model"""
    return await claude_chooser.make_request(text, model, context)

def record_claude_feedback(request_id: str, user_rating: float, 
                          task_text: str, model_used: str,
                          response_time: float, context: Dict[str, Any] = None):
    """Record user feedback for ML training"""
    features = claude_chooser.analyze_task(task_text, context)
    claude_chooser.record_feedback(
        request_id, user_rating, features, model_used,
        response_time, response_time * 100, 1.0, "good" if user_rating > 0.7 else "poor"
    )

def get_claude_chooser_stats() -> Dict[str, Any]:
    """Get chooser performance statistics"""
    return claude_chooser.get_performance_stats()

# Example usage and testing
async def example_usage():
    """Example of how to use the Claude API Chooser"""
    
    # Example tasks
    tasks = [
        ("Fix this Python bug: def hello(): print('Hello World'", {'urgency': 'high'}),
        ("Write a creative story about a robot", {'type': 'creative'}),
        ("Analyze the performance metrics of this system", {'type': 'analysis'}),
        ("How's the weather?", {'type': 'simple'})
    ]
    
    for task_text, context in tasks:
        # Choose and use model
        model = await choose_claude_model(task_text, context)
        print(f"Chose {model.value} for: {task_text[:50]}...")
        
        # Simulate making request (without actual API)
        result = {
            'success': True,
            'response': f"Mock response from {model.value}",
            'model_used': model.value,
            'response_time': 1.5,
            'token_efficiency': 100
        }
        
        # Record feedback (simulate user rating)
        import random
        user_rating = random.uniform(0.6, 1.0)
        record_claude_feedback(
            f"req_{int(time.time())}", user_rating, 
            task_text, result['model_used'], result['response_time'], context
        )
        
        print(f"Recorded feedback: {user_rating:.2f}")
    
    # Show stats
    stats = get_claude_chooser_stats()
    print(f"\nStats: {json.dumps(stats, indent=2)}")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run example
    asyncio.run(example_usage())