#!/usr/bin/env python3
"""
Self-Improving ML Capabilities with Feedback Loops
=================================================

- Train garbage collection bot on deletion success/failure
- Train summarization bot on summary quality and usefulness
- Learn from bot queries to understand data value
- Adapt storage allocation based on service usage patterns
- Continuous optimization of data management policies
- Advanced reinforcement learning for decision making
"""

import os
import json
import sqlite3
import logging
import asyncio
import numpy as np
import pandas as pd
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, deque
import threading
import time

import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
import torch.nn.functional as F

logger = logging.getLogger(__name__)

@dataclass
class FeedbackEvent:
    """Represents a feedback event from users or bots"""
    timestamp: datetime
    feedback_type: str  # deletion_quality, summary_quality, data_value, allocation_efficiency
    source: str  # human, bot, system
    action_id: str  # ID of the action being rated
    rating: float  # 0.0 to 1.0
    details: Dict[str, Any]
    context: Dict[str, Any]

@dataclass
class LearningMetric:
    """Tracks learning progress of ML models"""
    model_name: str
    timestamp: datetime
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_samples: int
    validation_samples: int
    learning_rate: float
    improvement_rate: float

@dataclass
class DecisionOutcome:
    """Tracks the outcome of ML-based decisions"""
    decision_id: str
    timestamp: datetime
    decision_type: str  # deletion, allocation, summarization, etc.
    ml_confidence: float
    actual_outcome: str  # success, failure, partial_success
    feedback_score: float
    context_features: Dict[str, float]
    learned_lesson: Optional[str] = None

class ReinforcementLearningAgent(nn.Module):
    """Reinforcement learning agent for data management decisions"""
    
    def __init__(self, state_size: int = 20, action_size: int = 10, hidden_sizes: List[int] = [128, 64, 32]):
        super(ReinforcementLearningAgent, self).__init__()
        
        self.state_size = state_size
        self.action_size = action_size
        
        # Q-Network architecture
        layers = []
        prev_size = state_size
        
        for hidden_size in hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU(),
                nn.BatchNorm1d(hidden_size),
                nn.Dropout(0.3)
            ])
            prev_size = hidden_size
        
        layers.append(nn.Linear(prev_size, action_size))
        
        self.q_network = nn.Sequential(*layers)
        
        # Experience replay buffer
        self.memory = deque(maxlen=10000)
        self.epsilon = 0.1  # Exploration rate
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        self.learning_rate = 0.001
        self.gamma = 0.95  # Discount factor
        
        self.optimizer = optim.Adam(self.parameters(), lr=self.learning_rate)
        
    def forward(self, state):
        return self.q_network(state)
    
    def remember(self, state, action, reward, next_state, done):
        """Store experience in replay buffer"""
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state, training=True):
        """Choose action using epsilon-greedy policy"""
        if training and np.random.random() <= self.epsilon:
            return np.random.choice(self.action_size)
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        q_values = self.forward(state_tensor)
        return q_values.argmax().item()
    
    def replay(self, batch_size=32):
        """Train the agent on a batch of experiences"""
        if len(self.memory) < batch_size:
            return
        
        batch = np.random.choice(len(self.memory), batch_size, replace=False)
        states = torch.FloatTensor([self.memory[i][0] for i in batch])
        actions = torch.LongTensor([self.memory[i][1] for i in batch])
        rewards = torch.FloatTensor([self.memory[i][2] for i in batch])
        next_states = torch.FloatTensor([self.memory[i][3] for i in batch])
        dones = torch.BoolTensor([self.memory[i][4] for i in batch])
        
        current_q_values = self.forward(states).gather(1, actions.unsqueeze(1))
        next_q_values = self.forward(next_states).max(1)[0].detach()
        target_q_values = rewards + (self.gamma * next_q_values * ~dones)
        
        loss = F.mse_loss(current_q_values.squeeze(), target_q_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

class FeedbackCollector:
    """Collects and processes feedback from various sources"""
    
    def __init__(self, db_path: str = "feedback_learning.db"):
        self.db_path = db_path
        self.feedback_queue = deque()
        self.feedback_processors = {}
        self.active_learning_sessions = {}
        self._init_feedback_db()
        
    def _init_feedback_db(self):
        """Initialize feedback database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Feedback events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                feedback_type TEXT NOT NULL,
                source TEXT NOT NULL,
                action_id TEXT NOT NULL,
                rating REAL NOT NULL,
                details TEXT,  -- JSON
                context TEXT   -- JSON
            )
        ''')
        
        # Decision outcomes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decision_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT UNIQUE NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                decision_type TEXT NOT NULL,
                ml_confidence REAL NOT NULL,
                actual_outcome TEXT NOT NULL,
                feedback_score REAL NOT NULL,
                context_features TEXT,  -- JSON
                learned_lesson TEXT
            )
        ''')
        
        # Learning metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                accuracy REAL NOT NULL,
                precision_score REAL NOT NULL,
                recall_score REAL NOT NULL,
                f1_score REAL NOT NULL,
                training_samples INTEGER NOT NULL,
                validation_samples INTEGER NOT NULL,
                learning_rate REAL NOT NULL,
                improvement_rate REAL NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def record_feedback(self, feedback: FeedbackEvent):
        """Record a feedback event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feedback_events 
            (timestamp, feedback_type, source, action_id, rating, details, context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            feedback.timestamp,
            feedback.feedback_type,
            feedback.source,
            feedback.action_id,
            feedback.rating,
            json.dumps(feedback.details),
            json.dumps(feedback.context)
        ))
        
        conn.commit()
        conn.close()
        
        # Add to processing queue
        self.feedback_queue.append(feedback)
        
        logger.info(f"Recorded {feedback.feedback_type} feedback: {feedback.rating}")
    
    def record_decision_outcome(self, outcome: DecisionOutcome):
        """Record the outcome of an ML decision"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO decision_outcomes 
            (decision_id, timestamp, decision_type, ml_confidence, actual_outcome, 
             feedback_score, context_features, learned_lesson)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            outcome.decision_id,
            outcome.timestamp,
            outcome.decision_type,
            outcome.ml_confidence,
            outcome.actual_outcome,
            outcome.feedback_score,
            json.dumps(outcome.context_features),
            outcome.learned_lesson
        ))
        
        conn.commit()
        conn.close()
    
    def get_feedback_history(self, feedback_type: str = None, days: int = 30) -> List[FeedbackEvent]:
        """Get feedback history for analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if feedback_type:
            cursor.execute('''
                SELECT * FROM feedback_events 
                WHERE feedback_type = ? AND timestamp > datetime('now', '-{} days')
                ORDER BY timestamp DESC
            '''.format(days), (feedback_type,))
        else:
            cursor.execute('''
                SELECT * FROM feedback_events 
                WHERE timestamp > datetime('now', '-{} days')
                ORDER BY timestamp DESC
            '''.format(days))
        
        rows = cursor.fetchall()
        conn.close()
        
        feedback_events = []
        for row in rows:
            feedback_events.append(FeedbackEvent(
                timestamp=datetime.fromisoformat(row[1]),
                feedback_type=row[2],
                source=row[3],
                action_id=row[4],
                rating=row[5],
                details=json.loads(row[6]) if row[6] else {},
                context=json.loads(row[7]) if row[7] else {}
            ))
        
        return feedback_events
    
    def analyze_feedback_patterns(self, feedback_type: str) -> Dict[str, Any]:
        """Analyze patterns in feedback for a specific type"""
        feedback_history = self.get_feedback_history(feedback_type, days=60)
        
        if not feedback_history:
            return {'error': 'No feedback data available'}
        
        ratings = [f.rating for f in feedback_history]
        sources = [f.source for f in feedback_history]
        
        # Calculate trends over time
        recent_feedback = [f for f in feedback_history if f.timestamp > datetime.now() - timedelta(days=7)]
        older_feedback = [f for f in feedback_history if f.timestamp <= datetime.now() - timedelta(days=7)]
        
        recent_avg = np.mean([f.rating for f in recent_feedback]) if recent_feedback else 0
        older_avg = np.mean([f.rating for f in older_feedback]) if older_feedback else 0
        
        return {
            'feedback_type': feedback_type,
            'total_feedback_count': len(feedback_history),
            'average_rating': np.mean(ratings),
            'rating_std': np.std(ratings),
            'rating_trend': recent_avg - older_avg,
            'source_distribution': dict(pd.Series(sources).value_counts()),
            'recent_performance': recent_avg,
            'improvement_needed': recent_avg < 0.6,
            'feedback_velocity': len(recent_feedback) / 7  # Feedback per day
        }

class AdaptiveLearningEngine:
    """Main engine for adaptive learning and self-improvement"""
    
    def __init__(self, feedback_collector: FeedbackCollector):
        self.feedback_collector = feedback_collector
        self.rl_agent = ReinforcementLearningAgent()
        self.learning_models = {}
        self.adaptation_strategies = {}
        self.learning_history = defaultdict(list)
        self.model_performance = {}
        
        # Initialize specialized learning modules
        self._init_learning_modules()
        
    def _init_learning_modules(self):
        """Initialize specialized learning modules"""
        self.learning_models = {
            'garbage_collector': GarbageCollectionLearner(self.feedback_collector),
            'summarizer': SummarizationLearner(self.feedback_collector),
            'data_value_assessor': DataValueLearner(self.feedback_collector),
            'storage_allocator': StorageAllocationLearner(self.feedback_collector)
        }
    
    async def continuous_learning_loop(self):
        """Main continuous learning loop"""
        logger.info("Starting continuous learning loop")
        
        while True:
            try:
                # Process pending feedback
                await self._process_feedback_queue()
                
                # Update learning models
                await self._update_learning_models()
                
                # Adapt strategies based on performance
                await self._adapt_strategies()
                
                # Generate learning insights
                insights = await self._generate_learning_insights()
                
                if insights:
                    logger.info(f"Learning insights generated: {len(insights)} items")
                
                # Sleep for learning cycle interval
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in continuous learning loop: {e}")
                await asyncio.sleep(60)  # Wait on error
    
    async def _process_feedback_queue(self):
        """Process pending feedback events"""
        processed = 0
        
        while self.feedback_collector.feedback_queue:
            try:
                feedback = self.feedback_collector.feedback_queue.popleft()
                
                # Route feedback to appropriate learning module
                if feedback.feedback_type in self.learning_models:
                    await self.learning_models[feedback.feedback_type].process_feedback(feedback)
                    processed += 1
                    
            except Exception as e:
                logger.error(f"Error processing feedback: {e}")
        
        if processed > 0:
            logger.debug(f"Processed {processed} feedback events")
    
    async def _update_learning_models(self):
        """Update all learning models"""
        update_tasks = []
        
        for name, model in self.learning_models.items():
            task = asyncio.create_task(self._update_single_model(name, model))
            update_tasks.append(task)
        
        await asyncio.gather(*update_tasks)
    
    async def _update_single_model(self, name: str, model):
        """Update a single learning model"""
        try:
            improvement = await model.update_model()
            
            if improvement:
                self.learning_history[name].append({
                    'timestamp': datetime.now(),
                    'improvement': improvement,
                    'performance_metrics': improvement.get('metrics', {})
                })
                
                logger.info(f"Model '{name}' improved: {improvement.get('improvement_score', 0):.3f}")
                
        except Exception as e:
            logger.error(f"Error updating model {name}: {e}")
    
    async def _adapt_strategies(self):
        """Adapt strategies based on learning outcomes"""
        for model_name, history in self.learning_history.items():
            if len(history) < 3:  # Need minimum history
                continue
            
            recent_performance = [h['improvement']['improvement_score'] for h in history[-5:]]
            avg_performance = np.mean(recent_performance)
            
            # Adapt based on performance
            if avg_performance < 0.1:  # Low improvement
                await self._adjust_learning_strategy(model_name, 'increase_exploration')
            elif avg_performance > 0.8:  # High improvement
                await self._adjust_learning_strategy(model_name, 'fine_tune')
    
    async def _adjust_learning_strategy(self, model_name: str, strategy: str):
        """Adjust learning strategy for a specific model"""
        if model_name not in self.adaptation_strategies:
            self.adaptation_strategies[model_name] = []
        
        adaptation = {
            'timestamp': datetime.now(),
            'strategy': strategy,
            'reason': f'Performance-based adaptation'
        }
        
        self.adaptation_strategies[model_name].append(adaptation)
        
        # Apply strategy to the model
        if model_name in self.learning_models:
            await self.learning_models[model_name].apply_strategy(strategy)
        
        logger.info(f"Applied strategy '{strategy}' to model '{model_name}'")
    
    async def _generate_learning_insights(self) -> List[Dict[str, Any]]:
        """Generate insights from learning patterns"""
        insights = []
        
        # Analyze feedback patterns
        for feedback_type in ['deletion_quality', 'summary_quality', 'data_value']:
            pattern_analysis = self.feedback_collector.analyze_feedback_patterns(feedback_type)
            
            if not pattern_analysis.get('error') and pattern_analysis.get('improvement_needed'):
                insights.append({
                    'type': 'performance_concern',
                    'model': feedback_type,
                    'issue': f"Low performance in {feedback_type}",
                    'current_rating': pattern_analysis.get('recent_performance', 0),
                    'recommendation': 'increase_training_data_and_model_complexity'
                })
        
        # Analyze model convergence
        for model_name, history in self.learning_history.items():
            if len(history) >= 5:
                recent_improvements = [h['improvement']['improvement_score'] for h in history[-5:]]
                trend = np.polyfit(range(len(recent_improvements)), recent_improvements, 1)[0]
                
                if trend < -0.05:  # Declining performance
                    insights.append({
                        'type': 'model_degradation',
                        'model': model_name,
                        'trend': trend,
                        'recommendation': 'model_refresh_or_architecture_change'
                    })
                elif trend > 0.1:  # Strong improvement
                    insights.append({
                        'type': 'model_success',
                        'model': model_name,
                        'trend': trend,
                        'recommendation': 'continue_current_approach'
                    })
        
        return insights
    
    def get_learning_status(self) -> Dict[str, Any]:
        """Get current learning status"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'active_models': len(self.learning_models),
            'total_feedback_processed': 0,
            'model_performance': {},
            'recent_adaptations': {},
            'learning_velocity': {}
        }
        
        # Calculate total feedback processed
        for model_name, model in self.learning_models.items():
            if hasattr(model, 'feedback_processed'):
                status['total_feedback_processed'] += model.feedback_processed
        
        # Model performance
        for model_name, history in self.learning_history.items():
            if history:
                recent_performance = history[-1]['improvement']['improvement_score']
                status['model_performance'][model_name] = recent_performance
        
        # Recent adaptations
        for model_name, adaptations in self.adaptation_strategies.items():
            recent_adaptations = [a for a in adaptations 
                                if a['timestamp'] > datetime.now() - timedelta(hours=24)]
            status['recent_adaptations'][model_name] = len(recent_adaptations)
        
        # Learning velocity (improvements per day)
        for model_name, history in self.learning_history.items():
            recent_history = [h for h in history 
                            if h['timestamp'] > datetime.now() - timedelta(days=7)]
            status['learning_velocity'][model_name] = len(recent_history) / 7
        
        return status

class GarbageCollectionLearner:
    """Specialized learner for garbage collection decisions"""
    
    def __init__(self, feedback_collector: FeedbackCollector):
        self.feedback_collector = feedback_collector
        self.model = None
        self.training_data = []
        self.feedback_processed = 0
        self.performance_history = deque(maxlen=100)
        
    async def process_feedback(self, feedback: FeedbackEvent):
        """Process feedback for garbage collection decisions"""
        if feedback.feedback_type != 'deletion_quality':
            return
        
        # Extract features from the deletion decision
        features = self._extract_decision_features(feedback)
        label = 1 if feedback.rating > 0.7 else 0  # Binary: good deletion or not
        
        self.training_data.append((features, label, feedback.rating))
        self.feedback_processed += 1
        
        # Update model if we have enough new data
        if len(self.training_data) >= 10:
            await self.update_model()
    
    def _extract_decision_features(self, feedback: FeedbackEvent) -> np.ndarray:
        """Extract features from deletion decision context"""
        context = feedback.context
        details = feedback.details
        
        features = np.array([
            context.get('file_age_days', 0),
            context.get('file_size_mb', 0),
            context.get('access_frequency', 0),
            context.get('service_importance', 0.5),
            context.get('file_type_score', 0.5),
            details.get('ml_confidence', 0.5),
            details.get('storage_pressure', 0.5),
            len(str(context.get('file_path', ''))),  # Path complexity
            context.get('redundancy_score', 0),
            context.get('backup_available', 0)  # Binary
        ])
        
        return features
    
    async def update_model(self) -> Optional[Dict[str, Any]]:
        """Update the garbage collection model"""
        if len(self.training_data) < 5:
            return None
        
        try:
            # Prepare training data
            X = np.array([data[0] for data in self.training_data])
            y = np.array([data[1] for data in self.training_data])
            weights = np.array([data[2] for data in self.training_data])  # Use rating as sample weight
            
            # Split data
            X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Simple neural network for binary classification
            model = nn.Sequential(
                nn.Linear(X.shape[1], 32),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(32, 16),
                nn.ReLU(),
                nn.Linear(16, 1),
                nn.Sigmoid()
            )
            
            # Train model
            optimizer = optim.Adam(model.parameters(), lr=0.001)
            criterion = nn.BCELoss()
            
            model.train()
            for epoch in range(50):
                optimizer.zero_grad()
                outputs = model(torch.FloatTensor(X_train)).squeeze()
                loss = criterion(outputs, torch.FloatTensor(y_train))
                loss.backward()
                optimizer.step()
            
            # Evaluate
            model.eval()
            with torch.no_grad():
                val_outputs = model(torch.FloatTensor(X_val)).squeeze()
                val_predictions = (val_outputs > 0.5).float()
                accuracy = (val_predictions == torch.FloatTensor(y_val)).float().mean().item()
            
            self.model = model
            self.training_data = []  # Clear training data
            
            improvement = {
                'improvement_score': accuracy,
                'metrics': {
                    'accuracy': accuracy,
                    'training_samples': len(X_train),
                    'validation_samples': len(X_val)
                },
                'model_updated': True
            }
            
            self.performance_history.append(improvement)
            return improvement
            
        except Exception as e:
            logger.error(f"Error updating garbage collection model: {e}")
            return None
    
    async def apply_strategy(self, strategy: str):
        """Apply learning strategy"""
        if strategy == 'increase_exploration':
            # Add more diverse training examples
            logger.info("Increasing exploration for garbage collection model")
        elif strategy == 'fine_tune':
            # Fine-tune existing model
            logger.info("Fine-tuning garbage collection model")

class SummarizationLearner:
    """Specialized learner for summarization quality"""
    
    def __init__(self, feedback_collector: FeedbackCollector):
        self.feedback_collector = feedback_collector
        self.quality_predictors = {}
        self.feedback_processed = 0
        self.summary_performance = deque(maxlen=50)
        
    async def process_feedback(self, feedback: FeedbackEvent):
        """Process feedback for summarization quality"""
        if feedback.feedback_type != 'summary_quality':
            return
        
        summary_id = feedback.action_id
        quality_score = feedback.rating
        
        # Learn what makes a good summary
        summary_features = self._extract_summary_features(feedback)
        
        if summary_id not in self.quality_predictors:
            self.quality_predictors[summary_id] = []
        
        self.quality_predictors[summary_id].append({
            'features': summary_features,
            'quality': quality_score,
            'timestamp': feedback.timestamp
        })
        
        self.feedback_processed += 1
    
    def _extract_summary_features(self, feedback: FeedbackEvent) -> Dict[str, float]:
        """Extract features that influence summary quality"""
        details = feedback.details
        context = feedback.context
        
        return {
            'summary_length': details.get('summary_length', 0),
            'original_content_length': context.get('original_length', 0),
            'compression_ratio': details.get('compression_ratio', 0),
            'readability_score': details.get('readability', 0.5),
            'coverage_score': details.get('coverage', 0.5),
            'coherence_score': details.get('coherence', 0.5),
            'information_density': details.get('info_density', 0.5),
            'domain_relevance': context.get('domain_relevance', 0.5)
        }
    
    async def update_model(self) -> Optional[Dict[str, Any]]:
        """Update summarization quality model"""
        if not self.quality_predictors:
            return None
        
        # Aggregate learning from all summaries
        all_features = []
        all_qualities = []
        
        for summary_data in self.quality_predictors.values():
            for entry in summary_data:
                feature_vector = list(entry['features'].values())
                all_features.append(feature_vector)
                all_qualities.append(entry['quality'])
        
        if len(all_features) < 10:
            return None
        
        # Simple regression model for quality prediction
        X = np.array(all_features)
        y = np.array(all_qualities)
        
        # Calculate correlation between features and quality
        correlations = {}
        feature_names = list(self.quality_predictors[list(self.quality_predictors.keys())[0]][0]['features'].keys())
        
        for i, feature_name in enumerate(feature_names):
            correlation = np.corrcoef(X[:, i], y)[0, 1]
            correlations[feature_name] = correlation
        
        # Identify most important features for quality
        important_features = {k: v for k, v in correlations.items() if abs(v) > 0.3}
        
        avg_quality = np.mean(all_qualities)
        improvement_score = avg_quality
        
        improvement = {
            'improvement_score': improvement_score,
            'metrics': {
                'avg_quality': avg_quality,
                'feature_correlations': correlations,
                'important_features': important_features,
                'sample_count': len(all_features)
            },
            'insights': self._generate_summarization_insights(correlations)
        }
        
        self.summary_performance.append(improvement)
        return improvement
    
    def _generate_summarization_insights(self, correlations: Dict[str, float]) -> List[str]:
        """Generate insights about what makes good summaries"""
        insights = []
        
        for feature, correlation in correlations.items():
            if correlation > 0.5:
                insights.append(f"Higher {feature} strongly correlates with better summary quality")
            elif correlation < -0.5:
                insights.append(f"Lower {feature} correlates with better summary quality")
        
        return insights
    
    async def apply_strategy(self, strategy: str):
        """Apply learning strategy for summarization"""
        logger.info(f"Applying strategy '{strategy}' to summarization learner")

class DataValueLearner:
    """Specialized learner for data value assessment"""
    
    def __init__(self, feedback_collector: FeedbackCollector):
        self.feedback_collector = feedback_collector
        self.value_model = None
        self.feedback_processed = 0
        self.value_predictions = deque(maxlen=200)
        
    async def process_feedback(self, feedback: FeedbackEvent):
        """Process feedback for data value predictions"""
        if feedback.feedback_type != 'data_value':
            return
        
        # Learn from bot queries about data usefulness
        data_features = self._extract_data_features(feedback)
        actual_value = feedback.rating
        
        self.value_predictions.append({
            'features': data_features,
            'actual_value': actual_value,
            'predicted_value': feedback.details.get('predicted_value', 0.5),
            'timestamp': feedback.timestamp,
            'source': feedback.source
        })
        
        self.feedback_processed += 1
    
    def _extract_data_features(self, feedback: FeedbackEvent) -> np.ndarray:
        """Extract features for data value prediction"""
        context = feedback.context
        
        features = np.array([
            context.get('file_age_hours', 0) / 24,  # Normalize to days
            context.get('access_frequency_per_day', 0),
            context.get('file_size_mb', 0) / 100,  # Normalize
            context.get('data_type_score', 0.5),
            context.get('service_importance', 0.5),
            context.get('ml_training_potential', 0),
            context.get('human_readability', 0.5),
            context.get('cross_reference_count', 0) / 10,  # Normalize
            context.get('update_frequency', 0),
            context.get('domain_relevance', 0.5)
        ])
        
        return features
    
    async def update_model(self) -> Optional[Dict[str, Any]]:
        """Update data value prediction model"""
        if len(self.value_predictions) < 20:
            return None
        
        # Analyze prediction accuracy
        predictions = list(self.value_predictions)
        
        actual_values = [p['actual_value'] for p in predictions]
        predicted_values = [p['predicted_value'] for p in predictions]
        
        # Calculate accuracy metrics
        mse = np.mean([(a - p) ** 2 for a, p in zip(actual_values, predicted_values)])
        mae = np.mean([abs(a - p) for a, p in zip(actual_values, predicted_values)])
        
        # Analyze by source (bot vs human feedback)
        bot_feedback = [p for p in predictions if 'bot' in p['source'].lower()]
        human_feedback = [p for p in predictions if 'human' in p['source'].lower()]
        
        bot_accuracy = 1 - np.mean([abs(p['actual_value'] - p['predicted_value']) for p in bot_feedback]) if bot_feedback else 0
        human_accuracy = 1 - np.mean([abs(p['actual_value'] - p['predicted_value']) for p in human_feedback]) if human_feedback else 0
        
        improvement = {
            'improvement_score': 1 - mae,  # Convert MAE to improvement score
            'metrics': {
                'mse': mse,
                'mae': mae,
                'bot_accuracy': bot_accuracy,
                'human_accuracy': human_accuracy,
                'total_predictions': len(predictions),
                'bot_feedback_count': len(bot_feedback),
                'human_feedback_count': len(human_feedback)
            },
            'insights': self._generate_value_insights(predictions)
        }
        
        return improvement
    
    def _generate_value_insights(self, predictions: List[Dict]) -> List[str]:
        """Generate insights about data value patterns"""
        insights = []
        
        # Analyze what bots find valuable vs humans
        bot_values = [p['actual_value'] for p in predictions if 'bot' in p['source'].lower()]
        human_values = [p['actual_value'] for p in predictions if 'human' in p['source'].lower()]
        
        if bot_values and human_values:
            bot_avg = np.mean(bot_values)
            human_avg = np.mean(human_values)
            
            if bot_avg > human_avg + 0.2:
                insights.append("Bots tend to value data higher than humans - focus on automation benefits")
            elif human_avg > bot_avg + 0.2:
                insights.append("Humans value data higher than bots - consider human-centric features")
        
        return insights
    
    async def apply_strategy(self, strategy: str):
        """Apply learning strategy for data value assessment"""
        logger.info(f"Applying strategy '{strategy}' to data value learner")

class StorageAllocationLearner:
    """Specialized learner for storage allocation optimization"""
    
    def __init__(self, feedback_collector: FeedbackCollector):
        self.feedback_collector = feedback_collector
        self.allocation_history = deque(maxlen=100)
        self.feedback_processed = 0
        self.service_patterns = {}
        
    async def process_feedback(self, feedback: FeedbackEvent):
        """Process feedback for storage allocation decisions"""
        if feedback.feedback_type != 'allocation_efficiency':
            return
        
        # Learn from allocation success/failure
        allocation_data = {
            'timestamp': feedback.timestamp,
            'service': feedback.details.get('service_name'),
            'allocated_gb': feedback.details.get('allocated_gb', 0),
            'actual_usage_gb': feedback.details.get('actual_usage_gb', 0),
            'efficiency_score': feedback.rating,
            'growth_rate': feedback.context.get('growth_rate', 0),
            'importance_score': feedback.context.get('importance_score', 0.5)
        }
        
        self.allocation_history.append(allocation_data)
        self.feedback_processed += 1
        
        # Update service patterns
        service = allocation_data['service']
        if service not in self.service_patterns:
            self.service_patterns[service] = []
        
        self.service_patterns[service].append(allocation_data)
    
    async def update_model(self) -> Optional[Dict[str, Any]]:
        """Update storage allocation model"""
        if len(self.allocation_history) < 10:
            return None
        
        # Analyze allocation efficiency patterns
        recent_allocations = list(self.allocation_history)
        
        # Calculate overall efficiency
        efficiency_scores = [a['efficiency_score'] for a in recent_allocations]
        avg_efficiency = np.mean(efficiency_scores)
        
        # Analyze by service
        service_efficiency = {}
        for service, allocations in self.service_patterns.items():
            if allocations:
                service_efficiency[service] = {
                    'avg_efficiency': np.mean([a['efficiency_score'] for a in allocations]),
                    'allocation_accuracy': self._calculate_allocation_accuracy(allocations),
                    'growth_prediction_accuracy': self._calculate_growth_prediction_accuracy(allocations)
                }
        
        # Identify patterns
        insights = self._analyze_allocation_patterns(recent_allocations)
        
        improvement = {
            'improvement_score': avg_efficiency,
            'metrics': {
                'overall_efficiency': avg_efficiency,
                'service_efficiency': service_efficiency,
                'total_allocations': len(recent_allocations),
                'services_tracked': len(self.service_patterns)
            },
            'insights': insights,
            'recommendations': self._generate_allocation_recommendations(service_efficiency)
        }
        
        return improvement
    
    def _calculate_allocation_accuracy(self, allocations: List[Dict]) -> float:
        """Calculate how accurately we allocate vs actual usage"""
        if not allocations:
            return 0.0
        
        accuracies = []
        for alloc in allocations:
            allocated = alloc['allocated_gb']
            actual = alloc['actual_usage_gb']
            if allocated > 0:
                accuracy = 1 - abs(allocated - actual) / allocated
                accuracies.append(max(0, accuracy))
        
        return np.mean(accuracies) if accuracies else 0.0
    
    def _calculate_growth_prediction_accuracy(self, allocations: List[Dict]) -> float:
        """Calculate how accurately we predict service growth"""
        if len(allocations) < 3:
            return 0.5  # Default
        
        # This would be more sophisticated in practice
        growth_rates = [a['growth_rate'] for a in allocations]
        growth_variance = np.var(growth_rates)
        
        # Lower variance in growth rates indicates better prediction
        return max(0, 1 - growth_variance)
    
    def _analyze_allocation_patterns(self, allocations: List[Dict]) -> List[str]:
        """Analyze patterns in allocation efficiency"""
        insights = []
        
        # Find services with consistently poor allocation
        service_problems = defaultdict(list)
        for alloc in allocations:
            if alloc['efficiency_score'] < 0.5:
                service_problems[alloc['service']].append(alloc)
        
        for service, problem_allocations in service_problems.items():
            if len(problem_allocations) >= 3:
                insights.append(f"Service '{service}' consistently has poor allocation efficiency")
        
        # Find allocation vs usage patterns
        over_allocated = [a for a in allocations if a['allocated_gb'] > a['actual_usage_gb'] * 1.5]
        under_allocated = [a for a in allocations if a['allocated_gb'] < a['actual_usage_gb'] * 0.8]
        
        if len(over_allocated) > len(allocations) * 0.3:
            insights.append("Tendency to over-allocate storage - consider more conservative approach")
        
        if len(under_allocated) > len(allocations) * 0.2:
            insights.append("Tendency to under-allocate storage - services running out of space")
        
        return insights
    
    def _generate_allocation_recommendations(self, service_efficiency: Dict) -> List[str]:
        """Generate recommendations for improving allocation"""
        recommendations = []
        
        # Find services needing attention
        low_efficiency_services = [
            service for service, metrics in service_efficiency.items()
            if metrics['avg_efficiency'] < 0.6
        ]
        
        if low_efficiency_services:
            recommendations.append(f"Focus allocation optimization on: {', '.join(low_efficiency_services)}")
        
        # Find high-performing patterns
        high_efficiency_services = [
            service for service, metrics in service_efficiency.items()
            if metrics['avg_efficiency'] > 0.8
        ]
        
        if high_efficiency_services:
            recommendations.append(f"Apply successful patterns from: {', '.join(high_efficiency_services)}")
        
        return recommendations
    
    async def apply_strategy(self, strategy: str):
        """Apply learning strategy for storage allocation"""
        logger.info(f"Applying strategy '{strategy}' to storage allocation learner")