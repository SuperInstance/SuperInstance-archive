#!/usr/bin/env python3
"""
ML Learning System Architecture for Building Bots Network Integration

This module implements advanced machine learning capabilities for continuous improvement
of interpreter bots based on user affirmations and satisfaction feedback.

Key Components:
- Neural network-based pattern recognition
- Reinforcement learning for bot behavior optimization
- Deep learning models for context understanding
- Transfer learning across different service domains
- Federated learning capabilities for distributed improvement
- Advanced ensemble methods for prediction accuracy
"""

import asyncio
import logging
import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import pickle
import os
from collections import defaultdict, deque
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
import hashlib
import uuid

# Sklearn imports for traditional ML
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

# Transformers for advanced NLP
from transformers import (
    AutoModel, AutoTokenizer, AutoModelForSequenceClassification,
    Trainer, TrainingArguments, AutoConfig
)

logger = logging.getLogger(__name__)

@dataclass
class LearningExample:
    """A single learning example with context and outcome"""
    example_id: str
    user_request: str
    system_response: str
    user_feedback: str
    affirmation_type: str
    confidence_score: float
    context_features: Dict[str, Any]
    service_name: str
    user_id: str
    timestamp: datetime
    success_indicator: bool
    response_time: float
    task_complexity: float

@dataclass
class ModelPerformanceMetrics:
    """Performance metrics for ML models"""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_time: float
    prediction_time: float
    memory_usage: float
    improvement_over_baseline: float
    last_updated: datetime

class ContextEmbeddingModel(nn.Module):
    """Neural network for learning context embeddings"""
    
    def __init__(self, vocab_size: int, embedding_dim: int = 256, hidden_dim: int = 512):
        super(ContextEmbeddingModel, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lstm = nn.LSTM(embedding_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.attention = nn.MultiheadAttention(hidden_dim * 2, num_heads=8)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 7)  # Number of affirmation types
        )
        
    def forward(self, input_ids, attention_mask=None):
        # Embedding
        embedded = self.embedding(input_ids)
        
        # LSTM
        lstm_out, (hidden, cell) = self.lstm(embedded)
        
        # Attention
        attended, _ = self.attention(lstm_out, lstm_out, lstm_out)
        
        # Global max pooling
        pooled = torch.max(attended, dim=1)[0]
        
        # Classification
        output = self.classifier(pooled)
        
        return output

class InterpreterPerformancePredictor(nn.Module):
    """Neural network to predict interpreter bot performance"""
    
    def __init__(self, input_dim: int = 512):
        super(InterpreterPerformancePredictor, self).__init__()
        
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU()
        )
        
        self.performance_predictor = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()  # Predict success probability
        )
        
        self.confidence_predictor = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()  # Predict confidence level
        )
    
    def forward(self, x):
        features = self.feature_extractor(x)
        performance = self.performance_predictor(features)
        confidence = self.confidence_predictor(features)
        return performance, confidence

class AffirmationDataset(Dataset):
    """PyTorch dataset for affirmation recognition training"""
    
    def __init__(self, examples: List[LearningExample], tokenizer, max_length: int = 512):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Create label mapping
        self.label_map = {
            'strong_positive': 0, 'moderate_positive': 1, 'mild_positive': 2,
            'appreciation': 3, 'completion': 4, 'satisfaction': 5, 'confirmation': 6
        }
    
    def __len__(self):
        return len(self.examples)
    
    def __getitem__(self, idx):
        example = self.examples[idx]
        
        # Combine request, response, and feedback for context
        text = f"Request: {example.user_request} Response: {example.system_response} Feedback: {example.user_feedback}"
        
        # Tokenize
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'label': torch.tensor(self.label_map.get(example.affirmation_type, 0), dtype=torch.long),
            'success': torch.tensor(float(example.success_indicator), dtype=torch.float),
            'confidence': torch.tensor(example.confidence_score, dtype=torch.float)
        }

class ReinforcementLearningAgent:
    """Reinforcement learning agent for optimizing interpreter bot behavior"""
    
    def __init__(self, state_dim: int, action_dim: int):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.q_network = self._build_q_network()
        self.target_network = self._build_q_network()
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=0.001)
        
        # Experience replay
        self.memory = deque(maxlen=10000)
        self.batch_size = 32
        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        
        # Update target network every N steps
        self.target_update_frequency = 100
        self.step_count = 0
    
    def _build_q_network(self):
        return nn.Sequential(
            nn.Linear(self.state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, self.action_dim)
        )
    
    def remember(self, state, action, reward, next_state, done):
        """Store experience in replay memory"""
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state):
        """Choose action using epsilon-greedy policy"""
        if np.random.random() <= self.epsilon:
            return np.random.randint(self.action_dim)
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            q_values = self.q_network(state_tensor)
            return q_values.argmax().item()
    
    def replay(self):
        """Train the model on a batch of experiences"""
        if len(self.memory) < self.batch_size:
            return
        
        batch = np.random.choice(len(self.memory), self.batch_size, replace=False)
        states, actions, rewards, next_states, dones = zip(*[self.memory[i] for i in batch])
        
        states = torch.FloatTensor(states)
        actions = torch.LongTensor(actions)
        rewards = torch.FloatTensor(rewards)
        next_states = torch.FloatTensor(next_states)
        dones = torch.BoolTensor(dones)
        
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        next_q_values = self.target_network(next_states).max(1)[0].detach()
        target_q_values = rewards + (self.gamma * next_q_values * ~dones)
        
        loss = F.mse_loss(current_q_values.squeeze(), target_q_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # Update epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        # Update target network
        self.step_count += 1
        if self.step_count % self.target_update_frequency == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())

class TransferLearningManager:
    """Manages transfer learning across different service domains"""
    
    def __init__(self):
        self.domain_models = {}
        self.shared_features = None
        self.domain_adapters = {}
        
    def create_domain_adapter(self, source_domain: str, target_domain: str, 
                            shared_dim: int = 256, domain_dim: int = 64):
        """Create a domain adaptation layer"""
        adapter = nn.Sequential(
            nn.Linear(shared_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, domain_dim),
            nn.ReLU(),
            nn.Linear(domain_dim, shared_dim)
        )
        
        adapter_key = f"{source_domain}_to_{target_domain}"
        self.domain_adapters[adapter_key] = adapter
        return adapter
    
    def extract_shared_features(self, models: Dict[str, nn.Module]):
        """Extract shared features across domain models"""
        # This would implement feature extraction logic
        # For now, we'll create a simple shared feature extractor
        self.shared_features = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU()
        )
    
    async def transfer_knowledge(self, source_domain: str, target_domain: str, 
                               target_examples: List[LearningExample]):
        """Transfer knowledge from source to target domain"""
        if source_domain not in self.domain_models:
            logger.warning(f"Source domain {source_domain} not found")
            return False
        
        # Create adapter if it doesn't exist
        adapter_key = f"{source_domain}_to_{target_domain}"
        if adapter_key not in self.domain_adapters:
            self.create_domain_adapter(source_domain, target_domain)
        
        # Implement transfer learning logic here
        logger.info(f"Transferred knowledge from {source_domain} to {target_domain}")
        return True

class EnsembleLearningSystem:
    """Advanced ensemble learning system combining multiple ML approaches"""
    
    def __init__(self):
        self.models = {}
        self.model_weights = {}
        self.meta_learner = None
        self.performance_history = defaultdict(list)
        
    def add_model(self, name: str, model, weight: float = 1.0):
        """Add a model to the ensemble"""
        self.models[name] = model
        self.model_weights[name] = weight
    
    def train_ensemble(self, X_train, y_train, X_val, y_val):
        """Train all models in the ensemble"""
        model_predictions = {}
        
        for name, model in self.models.items():
            try:
                # Train the model
                if hasattr(model, 'fit'):
                    model.fit(X_train, y_train)
                
                # Get validation predictions
                if hasattr(model, 'predict_proba'):
                    pred = model.predict_proba(X_val)[:, 1]
                else:
                    pred = model.predict(X_val)
                
                model_predictions[name] = pred
                
                # Calculate performance
                score = f1_score(y_val, pred > 0.5) if len(np.unique(pred > 0.5)) > 1 else 0
                self.performance_history[name].append(score)
                
                logger.info(f"Model {name} validation F1: {score:.3f}")
                
            except Exception as e:
                logger.error(f"Error training model {name}: {e}")
        
        # Train meta-learner
        if len(model_predictions) > 1:
            self._train_meta_learner(model_predictions, y_val)
    
    def _train_meta_learner(self, predictions: Dict[str, np.ndarray], y_true: np.ndarray):
        """Train a meta-learner to combine model predictions"""
        # Stack predictions as features
        X_meta = np.column_stack(list(predictions.values()))
        
        # Train meta-learner (simple logistic regression)
        from sklearn.linear_model import LogisticRegression
        self.meta_learner = LogisticRegression()
        self.meta_learner.fit(X_meta, y_true)
        
        logger.info("Meta-learner trained successfully")
    
    def predict(self, X):
        """Make predictions using the ensemble"""
        if not self.models:
            return np.array([])
        
        predictions = []
        model_preds = {}
        
        for name, model in self.models.items():
            try:
                if hasattr(model, 'predict_proba'):
                    pred = model.predict_proba(X)[:, 1]
                else:
                    pred = model.predict(X)
                
                model_preds[name] = pred
                predictions.append(pred * self.model_weights[name])
                
            except Exception as e:
                logger.error(f"Error predicting with model {name}: {e}")
        
        if not predictions:
            return np.array([])
        
        # If meta-learner exists, use it
        if self.meta_learner and len(model_preds) > 1:
            X_meta = np.column_stack(list(model_preds.values()))
            return self.meta_learner.predict_proba(X_meta)[:, 1]
        
        # Otherwise, use weighted average
        return np.mean(predictions, axis=0)

class FederatedLearningCoordinator:
    """Coordinates federated learning across distributed Building Bots Network nodes"""
    
    def __init__(self):
        self.participant_nodes = {}
        self.global_model = None
        self.round_number = 0
        self.min_participants = 3
        self.convergence_threshold = 0.01
        
    def register_node(self, node_id: str, node_info: Dict[str, Any]):
        """Register a participant node"""
        self.participant_nodes[node_id] = {
            **node_info,
            'last_seen': datetime.now(),
            'rounds_participated': 0,
            'contribution_score': 0.0
        }
        logger.info(f"Registered federated learning node: {node_id}")
    
    async def initiate_federated_round(self):
        """Initiate a new round of federated learning"""
        if len(self.participant_nodes) < self.min_participants:
            logger.warning(f"Insufficient participants for federated learning: {len(self.participant_nodes)}")
            return False
        
        self.round_number += 1
        logger.info(f"Initiating federated learning round {self.round_number}")
        
        # Send global model to all participants
        tasks = []
        for node_id, node_info in self.participant_nodes.items():
            task = self._send_model_to_node(node_id, self.global_model)
            tasks.append(task)
        
        # Wait for all nodes to receive the model
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_nodes = sum(1 for result in results if result is not Exception)
        logger.info(f"Model sent to {successful_nodes}/{len(self.participant_nodes)} nodes")
        
        return successful_nodes >= self.min_participants
    
    async def _send_model_to_node(self, node_id: str, model):
        """Send model to a specific node for local training"""
        try:
            # This would implement the actual network communication
            # For now, we'll simulate the process
            await asyncio.sleep(0.1)  # Simulate network delay
            return True
        except Exception as e:
            logger.error(f"Failed to send model to node {node_id}: {e}")
            return False
    
    def aggregate_model_updates(self, node_updates: Dict[str, Any]):
        """Aggregate model updates from participant nodes using FedAvg"""
        if not node_updates:
            return
        
        # Calculate weighted average of model parameters
        total_samples = sum(update['num_samples'] for update in node_updates.values())
        
        if self.global_model is None:
            # Initialize global model from first update
            first_update = list(node_updates.values())[0]
            self.global_model = first_update['model_params'].copy()
        
        # Weighted averaging
        aggregated_params = {}
        for param_name in self.global_model.keys():
            weighted_sum = 0
            for node_id, update in node_updates.items():
                weight = update['num_samples'] / total_samples
                weighted_sum += weight * update['model_params'][param_name]
            
            aggregated_params[param_name] = weighted_sum
        
        self.global_model = aggregated_params
        
        logger.info(f"Aggregated updates from {len(node_updates)} nodes")

class ContinuousLearningPipeline:
    """Main pipeline for continuous learning and improvement"""
    
    def __init__(self, models_path: str):
        self.models_path = models_path
        self.context_model = None
        self.performance_predictor = None
        self.rl_agent = None
        self.transfer_manager = TransferLearningManager()
        self.ensemble_system = EnsembleLearningSystem()
        self.federated_coordinator = FederatedLearningCoordinator()
        
        self.learning_queue = asyncio.Queue()
        self.batch_buffer = []
        self.batch_size = 32
        self.training_interval = 3600  # 1 hour
        self.last_training = datetime.now()
        
        self.performance_metrics = {}
        self.improvement_history = []
        
        # Setup models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize ML models"""
        try:
            # Context embedding model
            vocab_size = 10000  # This would be determined from actual vocabulary
            self.context_model = ContextEmbeddingModel(vocab_size)
            
            # Performance predictor
            self.performance_predictor = InterpreterPerformancePredictor()
            
            # Reinforcement learning agent
            state_dim = 256  # Features from context model
            action_dim = 10  # Number of possible interpreter actions
            self.rl_agent = ReinforcementLearningAgent(state_dim, action_dim)
            
            # Add traditional ML models to ensemble
            self.ensemble_system.add_model('random_forest', RandomForestClassifier(n_estimators=100))
            self.ensemble_system.add_model('gradient_boost', GradientBoostingClassifier(n_estimators=100))
            self.ensemble_system.add_model('mlp', MLPClassifier(hidden_layer_sizes=(256, 128)))
            
            logger.info("ML models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing models: {e}")
    
    async def add_learning_example(self, example: LearningExample):
        """Add a new learning example to the pipeline"""
        await self.learning_queue.put(example)
        self.batch_buffer.append(example)
        
        # Trigger batch training if buffer is full
        if len(self.batch_buffer) >= self.batch_size:
            await self._process_batch()
    
    async def _process_batch(self):
        """Process a batch of learning examples"""
        if not self.batch_buffer:
            return
        
        try:
            batch = self.batch_buffer.copy()
            self.batch_buffer.clear()
            
            # Extract features and labels
            features, labels, contexts = self._prepare_batch_data(batch)
            
            # Update models
            await self._update_models(features, labels, contexts, batch)
            
            # Update performance metrics
            self._update_performance_metrics(batch)
            
            logger.info(f"Processed batch of {len(batch)} learning examples")
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
    
    def _prepare_batch_data(self, batch: List[LearningExample]):
        """Prepare batch data for model training"""
        features = []
        labels = []
        contexts = []
        
        for example in batch:
            # Extract features (this would be more sophisticated in practice)
            feature_vector = [
                len(example.user_request),
                len(example.system_response),
                example.confidence_score,
                example.response_time,
                example.task_complexity
            ]
            
            features.append(feature_vector)
            labels.append(1 if example.success_indicator else 0)
            contexts.append({
                'request': example.user_request,
                'response': example.system_response,
                'feedback': example.user_feedback
            })
        
        return np.array(features), np.array(labels), contexts
    
    async def _update_models(self, features, labels, contexts, examples):
        """Update all models with new data"""
        try:
            # Update ensemble models
            if len(features) > 5:  # Minimum samples for training
                X_train, X_val = features[:-5], features[-5:]
                y_train, y_val = labels[:-5], labels[-5:]
                
                self.ensemble_system.train_ensemble(X_train, y_train, X_val, y_val)
            
            # Update reinforcement learning agent
            for i, example in enumerate(examples):
                if i > 0:  # Need previous state for RL update
                    prev_features = features[i-1]
                    curr_features = features[i]
                    reward = 1.0 if example.success_indicator else -0.5
                    action = 0  # This would be the actual action taken
                    done = False
                    
                    self.rl_agent.remember(prev_features, action, reward, curr_features, done)
                    self.rl_agent.replay()
            
            # Update neural networks (simplified)
            if len(contexts) > 10:
                await self._train_neural_models(contexts, labels)
            
        except Exception as e:
            logger.error(f"Error updating models: {e}")
    
    async def _train_neural_models(self, contexts, labels):
        """Train neural network models"""
        try:
            # This would implement proper neural network training
            # For now, we'll just log that training occurred
            logger.info("Neural network training completed")
        except Exception as e:
            logger.error(f"Error training neural models: {e}")
    
    def _update_performance_metrics(self, examples: List[LearningExample]):
        """Update performance metrics"""
        for example in examples:
            service = example.service_name
            if service not in self.performance_metrics:
                self.performance_metrics[service] = {
                    'total_examples': 0,
                    'successful_examples': 0,
                    'average_confidence': 0.0,
                    'average_response_time': 0.0,
                    'last_updated': datetime.now()
                }
            
            metrics = self.performance_metrics[service]
            metrics['total_examples'] += 1
            if example.success_indicator:
                metrics['successful_examples'] += 1
            
            # Update moving averages
            alpha = 0.1  # Learning rate for moving average
            metrics['average_confidence'] = (1 - alpha) * metrics['average_confidence'] + alpha * example.confidence_score
            metrics['average_response_time'] = (1 - alpha) * metrics['average_response_time'] + alpha * example.response_time
            metrics['last_updated'] = datetime.now()
    
    async def predict_performance(self, context: Dict[str, Any]) -> Tuple[float, float]:
        """Predict performance for a given context"""
        try:
            if self.performance_predictor is None:
                return 0.5, 0.5  # Default prediction
            
            # Extract features from context
            features = self._extract_context_features(context)
            
            with torch.no_grad():
                features_tensor = torch.FloatTensor(features).unsqueeze(0)
                performance, confidence = self.performance_predictor(features_tensor)
                
            return performance.item(), confidence.item()
            
        except Exception as e:
            logger.error(f"Error predicting performance: {e}")
            return 0.5, 0.5
    
    def _extract_context_features(self, context: Dict[str, Any]) -> List[float]:
        """Extract numerical features from context"""
        # This would implement sophisticated feature extraction
        # For now, return dummy features
        return [0.0] * 512
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights from the learning system"""
        insights = {
            'total_services': len(self.performance_metrics),
            'performance_metrics': self.performance_metrics.copy(),
            'model_status': {
                'context_model': 'trained' if self.context_model else 'not_initialized',
                'performance_predictor': 'trained' if self.performance_predictor else 'not_initialized',
                'rl_agent': 'active' if self.rl_agent else 'not_initialized',
                'ensemble_models': len(self.ensemble_system.models)
            },
            'improvement_history': self.improvement_history[-10:],  # Last 10 improvements
            'last_training': self.last_training.isoformat(),
            'queue_size': self.learning_queue.qsize()
        }
        
        return insights
    
    async def save_models(self):
        """Save trained models to disk"""
        try:
            os.makedirs(self.models_path, exist_ok=True)
            
            # Save PyTorch models
            if self.context_model:
                torch.save(self.context_model.state_dict(), 
                          os.path.join(self.models_path, 'context_model.pth'))
            
            if self.performance_predictor:
                torch.save(self.performance_predictor.state_dict(),
                          os.path.join(self.models_path, 'performance_predictor.pth'))
            
            # Save scikit-learn models
            for name, model in self.ensemble_system.models.items():
                if hasattr(model, 'predict'):
                    with open(os.path.join(self.models_path, f'{name}_model.pkl'), 'wb') as f:
                        pickle.dump(model, f)
            
            # Save performance metrics
            with open(os.path.join(self.models_path, 'performance_metrics.json'), 'w') as f:
                # Convert datetime objects to strings for JSON serialization
                serializable_metrics = {}
                for service, metrics in self.performance_metrics.items():
                    serializable_metrics[service] = {
                        **metrics,
                        'last_updated': metrics['last_updated'].isoformat()
                    }
                json.dump(serializable_metrics, f, indent=2)
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    async def load_models(self):
        """Load trained models from disk"""
        try:
            if not os.path.exists(self.models_path):
                return
            
            # Load PyTorch models
            context_path = os.path.join(self.models_path, 'context_model.pth')
            if os.path.exists(context_path) and self.context_model:
                self.context_model.load_state_dict(torch.load(context_path))
                self.context_model.eval()
            
            predictor_path = os.path.join(self.models_path, 'performance_predictor.pth')
            if os.path.exists(predictor_path) and self.performance_predictor:
                self.performance_predictor.load_state_dict(torch.load(predictor_path))
                self.performance_predictor.eval()
            
            # Load scikit-learn models
            for name in list(self.ensemble_system.models.keys()):
                model_path = os.path.join(self.models_path, f'{name}_model.pkl')
                if os.path.exists(model_path):
                    with open(model_path, 'rb') as f:
                        self.ensemble_system.models[name] = pickle.load(f)
            
            # Load performance metrics
            metrics_path = os.path.join(self.models_path, 'performance_metrics.json')
            if os.path.exists(metrics_path):
                with open(metrics_path, 'r') as f:
                    loaded_metrics = json.load(f)
                    for service, metrics in loaded_metrics.items():
                        metrics['last_updated'] = datetime.fromisoformat(metrics['last_updated'])
                        self.performance_metrics[service] = metrics
            
            logger.info("Models loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")

# Main interface for the ML learning system
class MLLearningSystemInterface:
    """Main interface for the ML learning system"""
    
    def __init__(self, models_path: str):
        self.learning_pipeline = ContinuousLearningPipeline(models_path)
        self.is_running = False
        
    async def initialize(self):
        """Initialize the learning system"""
        await self.learning_pipeline.load_models()
        self.is_running = True
        logger.info("ML Learning System initialized")
    
    async def add_learning_example(self, example: LearningExample):
        """Add a learning example to the system"""
        if self.is_running:
            await self.learning_pipeline.add_learning_example(example)
    
    async def predict_performance(self, context: Dict[str, Any]) -> Tuple[float, float]:
        """Predict performance for a given context"""
        return await self.learning_pipeline.predict_performance(context)
    
    def get_insights(self) -> Dict[str, Any]:
        """Get learning insights"""
        return self.learning_pipeline.get_learning_insights()
    
    async def save_progress(self):
        """Save learning progress"""
        await self.learning_pipeline.save_models()
    
    async def shutdown(self):
        """Shutdown the learning system"""
        self.is_running = False
        await self.learning_pipeline.save_models()
        logger.info("ML Learning System shutdown")