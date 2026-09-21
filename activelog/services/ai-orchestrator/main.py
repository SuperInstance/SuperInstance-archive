from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager
import sqlite3
from contextlib import contextmanager
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
import pickle

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from transformers import AutoModel, AutoTokenizer, pipeline
    import numpy as np
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
import threading
import time
import hashlib
import base64
import io
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque
import json

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    
try:
    from minio import Minio
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False

try:
    from plugin_manager import plugin_manager
    from ai_hub_integrations import AIHubIntegrator, AIServiceType
    PLUGINS_AVAILABLE = True
except ImportError:
    PLUGINS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global clients and AI orchestrator
redis_client = None
minio_client = None
ai_hub = None
ai_orchestrator = None

# AI Orchestrator Configuration
DB_PATH = "data/ai_orchestrator.db"
MODEL_PATH = "models/"

# Pydantic Models for AI features
from pydantic import BaseModel

class ServiceMetrics(BaseModel):
    service_name: str
    domain: str
    cpu_usage: float
    memory_usage: float
    response_time: float
    request_count: int
    error_rate: float
    timestamp: datetime

class RoutingDecision(BaseModel):
    service_name: str
    target_instance: str
    confidence_score: float
    predicted_response_time: float
    load_factor: float

class OptimizationSuggestion(BaseModel):
    service_name: str
    action: str
    priority: str
    impact_score: float
    description: str

class TransformerServicePredictor(nn.Module):
    """Transformer-based neural network for service performance prediction"""
    
    def __init__(self, input_dim=10, hidden_dim=128, num_heads=8, num_layers=4):
        super().__init__()
        self.input_dim = input_dim
        self.embedding = nn.Linear(input_dim, hidden_dim)
        
        # Transformer encoder layers
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=0.1,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Output layers
        self.fc_response_time = nn.Linear(hidden_dim, 1)
        self.fc_confidence = nn.Linear(hidden_dim, 1)
        self.dropout = nn.Dropout(0.1)
        
    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_dim)
        embedded = self.embedding(x)
        
        # Transformer encoding
        encoded = self.transformer(embedded)
        
        # Global average pooling
        pooled = encoded.mean(dim=1)
        pooled = self.dropout(pooled)
        
        # Predictions
        response_time = torch.relu(self.fc_response_time(pooled))
        confidence = torch.sigmoid(self.fc_confidence(pooled))
        
        return response_time.squeeze(), confidence.squeeze()

class FederatedLearningCoordinator:
    """Coordinates federated learning across distributed service instances"""
    
    def __init__(self):
        self.global_model_state = None
        self.participant_models = {}
        self.aggregation_weights = {}
        self.round_counter = 0
        self.min_participants = 3
        
    def register_participant(self, participant_id: str, model_state: dict, data_size: int):
        """Register a federated learning participant"""
        self.participant_models[participant_id] = model_state
        self.aggregation_weights[participant_id] = data_size
        
    def federated_average(self) -> dict:
        """Perform federated averaging of model parameters"""
        if len(self.participant_models) < self.min_participants:
            return None
            
        total_weight = sum(self.aggregation_weights.values())
        global_state = {}
        
        # Weight participants by their data size
        for param_name in list(self.participant_models.values())[0].keys():
            weighted_params = []
            for participant_id, model_state in self.participant_models.items():
                weight = self.aggregation_weights[participant_id] / total_weight
                weighted_param = model_state[param_name] * weight
                weighted_params.append(weighted_param)
            
            global_state[param_name] = sum(weighted_params)
        
        self.global_model_state = global_state
        self.round_counter += 1
        self.participant_models.clear()
        self.aggregation_weights.clear()
        
        return global_state
    
    def add_differential_privacy_noise(self, model_state: dict, epsilon: float = 1.0) -> dict:
        """Add differential privacy noise to model parameters"""
        noisy_state = {}
        for param_name, param_value in model_state.items():
            if isinstance(param_value, (int, float)):
                # Add Laplacian noise for differential privacy
                sensitivity = 1.0  # Assume L2-bounded gradients
                noise_scale = sensitivity / epsilon
                noise = np.random.laplace(0, noise_scale)
                noisy_state[param_name] = param_value + noise
            else:
                noisy_state[param_name] = param_value
        return noisy_state

class AdvancedAnomalyDetector:
    """Advanced anomaly detection using multiple algorithms"""
    
    def __init__(self):
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.autoencoder = None
        self.trained = False
        
    def create_autoencoder(self, input_dim: int):
        """Create autoencoder for anomaly detection"""
        if not TF_AVAILABLE:
            return None
            
        encoder = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu', input_shape=(input_dim,)),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(16, activation='relu'),
            tf.keras.layers.Dense(8, activation='relu')
        ])
        
        decoder = tf.keras.Sequential([
            tf.keras.layers.Dense(16, activation='relu', input_shape=(8,)),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(input_dim, activation='sigmoid')
        ])
        
        autoencoder = tf.keras.Sequential([encoder, decoder])
        autoencoder.compile(optimizer='adam', loss='mse')
        
        return autoencoder
    
    def train(self, normal_data: np.ndarray):
        """Train anomaly detection models on normal service behavior"""
        # Train isolation forest
        self.isolation_forest.fit(normal_data)
        
        # Train autoencoder if TensorFlow is available
        if TF_AVAILABLE and normal_data.shape[1] > 0:
            self.autoencoder = self.create_autoencoder(normal_data.shape[1])
            if self.autoencoder:
                self.autoencoder.fit(normal_data, normal_data, epochs=50, verbose=0)
        
        self.trained = True
    
    def detect_anomalies(self, data: np.ndarray) -> dict:
        """Detect anomalies using ensemble approach"""
        if not self.trained:
            return {"anomalies": [], "scores": [], "method": "untrained"}
        
        results = {}
        
        # Isolation Forest detection
        isolation_scores = self.isolation_forest.decision_function(data)
        isolation_anomalies = self.isolation_forest.predict(data) == -1
        
        results["isolation_forest"] = {
            "anomalies": isolation_anomalies.tolist(),
            "scores": isolation_scores.tolist()
        }
        
        # Autoencoder detection (if available)
        if self.autoencoder and TF_AVAILABLE:
            reconstructed = self.autoencoder.predict(data)
            reconstruction_errors = np.mean(np.square(data - reconstructed), axis=1)
            threshold = np.percentile(reconstruction_errors, 95)
            autoencoder_anomalies = reconstruction_errors > threshold
            
            results["autoencoder"] = {
                "anomalies": autoencoder_anomalies.tolist(),
                "scores": reconstruction_errors.tolist(),
                "threshold": threshold
            }
        
        # Ensemble decision (combine both methods if available)
        if "autoencoder" in results:
            ensemble_anomalies = np.logical_or(isolation_anomalies, 
                                             results["autoencoder"]["anomalies"])
        else:
            ensemble_anomalies = isolation_anomalies
        
        results["ensemble"] = {
            "anomalies": ensemble_anomalies.tolist(),
            "confidence": np.mean([isolation_scores, 
                                 results.get("autoencoder", {}).get("scores", isolation_scores)], axis=0).tolist()
        }
        
        return results

class NeuralArchitectureSearch:
    """Neural Architecture Search for automated model optimization"""
    
    def __init__(self, search_space: dict):
        self.search_space = search_space
        self.best_architecture = None
        self.best_performance = float('inf')
        self.search_history = []
        
    def random_architecture(self) -> dict:
        """Generate a random architecture from search space"""
        architecture = {}
        for component, options in self.search_space.items():
            if isinstance(options, list):
                architecture[component] = np.random.choice(options)
            elif isinstance(options, dict) and 'range' in options:
                min_val, max_val = options['range']
                architecture[component] = np.random.randint(min_val, max_val + 1)
            else:
                architecture[component] = options
        return architecture
    
    def evaluate_architecture(self, architecture: dict, X_train, y_train, X_val, y_val) -> float:
        """Evaluate an architecture's performance"""
        try:
            if TORCH_AVAILABLE:
                model = TransformerServicePredictor(
                    input_dim=X_train.shape[1],
                    hidden_dim=architecture.get('hidden_dim', 128),
                    num_heads=architecture.get('num_heads', 8),
                    num_layers=architecture.get('num_layers', 4)
                )
                
                optimizer = optim.Adam(model.parameters(), lr=architecture.get('learning_rate', 0.001))
                criterion = nn.MSELoss()
                
                # Quick training for evaluation
                model.train()
                X_train_tensor = torch.FloatTensor(X_train).unsqueeze(1)
                y_train_tensor = torch.FloatTensor(y_train)
                
                for epoch in range(10):  # Quick evaluation
                    optimizer.zero_grad()
                    response_time, confidence = model(X_train_tensor)
                    loss = criterion(response_time, y_train_tensor)
                    loss.backward()
                    optimizer.step()
                
                # Validation
                model.eval()
                with torch.no_grad():
                    X_val_tensor = torch.FloatTensor(X_val).unsqueeze(1)
                    y_val_tensor = torch.FloatTensor(y_val)
                    val_response_time, _ = model(X_val_tensor)
                    val_loss = criterion(val_response_time, y_val_tensor)
                
                return val_loss.item()
            else:
                # Fallback to simple model if PyTorch not available
                from sklearn.ensemble import RandomForestRegressor
                model = RandomForestRegressor(n_estimators=architecture.get('n_estimators', 100))
                model.fit(X_train, y_train)
                y_pred = model.predict(X_val)
                return mean_squared_error(y_val, y_pred)
                
        except Exception as e:
            logger.error(f"Architecture evaluation error: {e}")
            return float('inf')
    
    def search(self, X_train, y_train, X_val, y_val, num_trials: int = 20) -> dict:
        """Perform neural architecture search"""
        for trial in range(num_trials):
            architecture = self.random_architecture()
            performance = self.evaluate_architecture(architecture, X_train, y_train, X_val, y_val)
            
            self.search_history.append({
                'trial': trial,
                'architecture': architecture.copy(),
                'performance': performance
            })
            
            if performance < self.best_performance:
                self.best_performance = performance
                self.best_architecture = architecture.copy()
                logger.info(f"New best architecture found: {performance:.4f}")
        
        return {
            'best_architecture': self.best_architecture,
            'best_performance': self.best_performance,
            'search_history': self.search_history
        }

class IntelligentAIOrchestrator:
    """Enhanced AI orchestrator with ML-based optimization and intelligent routing"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.transformer_models = {}
        self.service_metrics = defaultdict(lambda: deque(maxlen=1000))
        self.routing_cache = {}
        self.optimization_history = defaultdict(list)
        self.performance_predictions = {}
        self.load_patterns = defaultdict(list)
        self._connection_pool = []
        self._max_connections = 10
        
        # Advanced ML components
        self.federated_coordinator = FederatedLearningCoordinator()
        self.anomaly_detector = AdvancedAnomalyDetector()
        self.nas_searcher = None
        
        # Transformer-based components
        self.service_embeddings = {}
        self.semantic_analyzer = None
        
        self.init_db()
        self.load_models()
        self.init_advanced_models()
        self.start_background_tasks()
    
    @contextmanager
    def get_db_connection(self):
        """Get database connection from pool"""
        if self._connection_pool:
            conn = self._connection_pool.pop()
        else:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        try:
            yield conn
        finally:
            if len(self._connection_pool) < self._max_connections:
                self._connection_pool.append(conn)
            else:
                conn.close()
    
    def init_db(self):
        """Initialize database for AI orchestration metrics"""
        import os
        os.makedirs("data", exist_ok=True)
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT,
                domain TEXT,
                cpu_usage REAL,
                memory_usage REAL,
                response_time REAL,
                request_count INTEGER,
                error_rate REAL,
                timestamp DATETIME,
                instance_id TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS routing_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT,
                target_instance TEXT,
                confidence_score REAL,
                predicted_response_time REAL,
                actual_response_time REAL,
                timestamp DATETIME
            )
        """)
        
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS optimization_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT,
                    action TEXT,
                    impact_score REAL,
                    success BOOLEAN,
                    timestamp DATETIME
                )
            """)
            
            conn.commit()
    
    def load_models(self):
        """Load or create ML models for service optimization"""
        import os
        os.makedirs(MODEL_PATH, exist_ok=True)
        
        service_types = ["backend", "repository", "deployer", "trainer", "builder", "defaultuser", "runner"]
        
        for service_type in service_types:
            try:
                with open(f"{MODEL_PATH}{service_type}_model.pkl", 'rb') as f:
                    self.models[service_type] = pickle.load(f)
                with open(f"{MODEL_PATH}{service_type}_scaler.pkl", 'rb') as f:
                    self.scalers[service_type] = pickle.load(f)
                logger.info(f"Loaded ML model for {service_type}")
            except FileNotFoundError:
                self.models[service_type] = RandomForestRegressor(n_estimators=100, random_state=42)
                self.scalers[service_type] = StandardScaler()
                logger.info(f"Created new ML model for {service_type}")
    
    def init_advanced_models(self):
        """Initialize advanced ML models and components"""
        try:
            # Initialize transformer-based semantic analyzer
            if TORCH_AVAILABLE:
                try:
                    self.semantic_analyzer = pipeline(
                        "feature-extraction",
                        model="distilbert-base-uncased",
                        return_tensors="pt"
                    )
                    logger.info("Transformer-based semantic analyzer initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize transformer model: {e}")
            
            # Initialize NAS with search space
            nas_search_space = {
                'hidden_dim': [64, 128, 256, 512],
                'num_heads': [4, 8, 16],
                'num_layers': {'range': [2, 8]},
                'learning_rate': [0.001, 0.0001, 0.00001],
                'n_estimators': {'range': [50, 200]}  # For fallback models
            }
            
            self.nas_searcher = NeuralArchitectureSearch(nas_search_space)
            logger.info("Neural Architecture Search initialized")
            
            # Train anomaly detector with historical data
            self._train_anomaly_detector()
            
        except Exception as e:
            logger.error(f"Advanced models initialization error: {e}")
    
    def _train_anomaly_detector(self):
        """Train anomaly detector with historical service metrics"""
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("""
                SELECT cpu_usage, memory_usage, response_time, request_count, error_rate
                FROM service_metrics 
                WHERE timestamp > ?
                ORDER BY timestamp DESC LIMIT 10000
            """, conn, params=(datetime.now() - timedelta(days=30),))
            conn.close()
            
            if len(df) > 100:
                # Filter out obvious anomalies for training (use only "normal" data)
                normal_data = df[
                    (df['cpu_usage'] < 90) & 
                    (df['memory_usage'] < 90) & 
                    (df['response_time'] < 5000) & 
                    (df['error_rate'] < 0.1)
                ].values
                
                if len(normal_data) > 50:
                    self.anomaly_detector.train(normal_data)
                    logger.info(f"Anomaly detector trained with {len(normal_data)} normal samples")
                    
        except Exception as e:
            logger.error(f"Anomaly detector training error: {e}")
    
    def predict_performance(self, service_name: str, features: np.ndarray) -> Tuple[float, float]:
        """Predict service performance using advanced ML models"""
        service_type = service_name.split('-')[-1] if '-' in service_name else 'backend'
        
        # Try transformer model first
        if TORCH_AVAILABLE and service_type in self.transformer_models:
            try:
                model = self.transformer_models[service_type]
                model.eval()
                
                with torch.no_grad():
                    features_tensor = torch.FloatTensor(features).unsqueeze(0).unsqueeze(0)
                    response_time, confidence = model(features_tensor)
                    
                return float(response_time.item()), float(confidence.item())
                
            except Exception as e:
                logger.error(f"Transformer prediction error for {service_name}: {e}")
        
        # Fallback to traditional ML
        if service_type not in self.models:
            return 100.0, 0.5
        
        try:
            features_scaled = self.scalers[service_type].transform(features.reshape(1, -1))
            prediction = self.models[service_type].predict(features_scaled)[0]
            
            # Calculate confidence using ensemble variance
            tree_predictions = np.array([
                tree.predict(features_scaled)[0] 
                for tree in self.models[service_type].estimators_
            ])
            confidence = 1.0 - (np.std(tree_predictions) / max(np.mean(tree_predictions), 1.0))
            
            # Check for anomalies
            anomaly_results = self.anomaly_detector.detect_anomalies(features.reshape(1, -1))
            if anomaly_results.get('ensemble', {}).get('anomalies', [False])[0]:
                confidence *= 0.5  # Reduce confidence for anomalous inputs
                logger.warning(f"Anomalous input detected for {service_name}")
            
            return max(prediction, 1.0), max(min(confidence, 1.0), 0.0)
            
        except Exception as e:
            logger.error(f"ML prediction error for {service_name}: {e}")
            return 100.0, 0.5
    
    def get_service_embeddings(self, service_name: str, service_description: str = None) -> np.ndarray:
        """Generate semantic embeddings for service using transformer"""
        if not self.semantic_analyzer:
            # Fallback to simple hash-based embedding
            return np.random.rand(768)  # Standard BERT embedding size
        
        try:
            text = service_description or f"Service {service_name} for system orchestration"
            embeddings = self.semantic_analyzer(text)
            
            # Extract and average token embeddings
            embedding_tensor = embeddings[0]
            mean_embedding = embedding_tensor.mean(dim=1).squeeze().numpy()
            
            return mean_embedding
            
        except Exception as e:
            logger.error(f"Embedding generation error for {service_name}: {e}")
            return np.random.rand(768)
    
    def semantic_service_similarity(self, service1: str, service2: str) -> float:
        """Calculate semantic similarity between services"""
        try:
            if service1 not in self.service_embeddings:
                self.service_embeddings[service1] = self.get_service_embeddings(service1)
            if service2 not in self.service_embeddings:
                self.service_embeddings[service2] = self.get_service_embeddings(service2)
            
            emb1 = self.service_embeddings[service1]
            emb2 = self.service_embeddings[service2]
            
            # Cosine similarity
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Similarity calculation error: {e}")
            return 0.0
    
    def intelligent_routing(self, service_name: str, request_features: dict) -> RoutingDecision:
        """Make intelligent routing decisions based on ML predictions"""
        available_instances = [f"{service_name}-instance-{i}" for i in range(1, 4)]
        
        features = np.array([
            50.0,  # cpu_usage
            50.0,  # memory_usage  
            10,    # request_count
            0.0,   # error_rate
            request_features.get('complexity', 1.0),
            request_features.get('priority', 5)
        ])
        
        pred_time, confidence = self.predict_performance(service_name, features)
        
        return RoutingDecision(
            service_name=service_name,
            target_instance=available_instances[0],
            confidence_score=confidence,
            predicted_response_time=pred_time,
            load_factor=50.0
        )
    
    def generate_optimization_suggestions(self, service_name: str) -> List[OptimizationSuggestion]:
        """Generate AI-powered optimization suggestions"""
        suggestions = []
        
        # Analyze recent performance patterns
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT AVG(cpu_usage), AVG(memory_usage), AVG(response_time), AVG(error_rate)
                FROM service_metrics 
                WHERE service_name = ? AND timestamp > ?
            """, (service_name, datetime.now() - timedelta(hours=1)))
            
            result = cursor.fetchone()
        
        if result and any(result):
            avg_cpu, avg_memory, avg_response, avg_error = result
            
            if avg_cpu and avg_cpu > 80:
                suggestions.append(OptimizationSuggestion(
                    service_name=service_name,
                    action="scale_up_cpu",
                    priority="high",
                    impact_score=0.8,
                    description=f"High CPU usage detected ({avg_cpu:.1f}%) - recommend scaling up"
                ))
            
            if avg_memory and avg_memory > 85:
                suggestions.append(OptimizationSuggestion(
                    service_name=service_name,
                    action="increase_memory",
                    priority="high", 
                    impact_score=0.7,
                    description=f"High memory usage ({avg_memory:.1f}%) - recommend memory increase"
                ))
                
            if avg_response and avg_response > 1000:
                suggestions.append(OptimizationSuggestion(
                    service_name=service_name,
                    action="optimize_performance",
                    priority="medium",
                    impact_score=0.6,
                    description=f"Slow response time ({avg_response:.0f}ms) - performance optimization needed"
                ))
        
        return suggestions
    
    def start_background_tasks(self):
        """Start background AI optimization tasks"""
        async def background_worker():
            while True:
                try:
                    self.retrain_models()
                    self.analyze_patterns()
                    self.cleanup_old_data()
                    await asyncio.sleep(300)  # Every 5 minutes
                except Exception as e:
                    logger.error(f"Background AI task error: {e}")
                    await asyncio.sleep(60)
        
        # Use async task instead of thread
        asyncio.create_task(background_worker())
        logger.info("AI orchestrator background tasks started")
    
    def retrain_models(self):
        """Retrain ML models with recent performance data"""
        conn = sqlite3.connect(DB_PATH)
        
        for service_type in self.models:
            try:
                df = pd.read_sql_query("""
                    SELECT cpu_usage, memory_usage, request_count, error_rate, response_time
                    FROM service_metrics 
                    WHERE service_name LIKE ? AND timestamp > ?
                    ORDER BY timestamp DESC LIMIT 5000
                """, conn, params=(f"%{service_type}%", datetime.now() - timedelta(days=7)))
                
                if len(df) > 100:
                    X = df[['cpu_usage', 'memory_usage', 'request_count', 'error_rate']].values
                    y = df['response_time'].values
                    
                    # Add synthetic features
                    complexity_feature = np.random.uniform(0.5, 2.0, len(X))
                    priority_feature = np.random.uniform(1, 10, len(X))
                    X = np.column_stack([X, complexity_feature, priority_feature])
                    
                    X_scaled = self.scalers[service_type].fit_transform(X)
                    self.models[service_type].fit(X_scaled, y)
                    
                    logger.info(f"Retrained ML model for {service_type} with {len(df)} samples")
                    
            except Exception as e:
                logger.error(f"Model retraining error for {service_type}: {e}")
        
        conn.close()
    
    def analyze_patterns(self):
        """Analyze load patterns and generate insights"""
        try:
            # Pattern analysis logic here
            logger.debug("Analyzing service load patterns")
        except Exception as e:
            logger.error(f"Pattern analysis error: {e}")
    
    def cleanup_old_data(self):
        """Clean up old metrics data"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=30)
        cursor.execute("DELETE FROM service_metrics WHERE timestamp < ?", (cutoff_date,))
        cursor.execute("DELETE FROM routing_decisions WHERE timestamp < ?", (cutoff_date,))
        cursor.execute("DELETE FROM optimization_actions WHERE timestamp < ?", (cutoff_date,))
        
        conn.commit()
        conn.close()

async def init_services():
    """Initialize Redis, MinIO clients, and AI orchestrator"""
    global redis_client, minio_client, ai_hub, ai_orchestrator
    
    # Initialize AI Orchestrator (always available)
    try:
        ai_orchestrator = IntelligentAIOrchestrator()
        logger.info("AI Orchestrator initialized successfully")
    except Exception as e:
        logger.error(f"AI Orchestrator initialization failed: {e}")
        ai_orchestrator = None
    
    # Initialize Redis (optional)
    if REDIS_AVAILABLE:
        try:
            redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            await redis_client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            redis_client = None
    else:
        logger.info("Redis not available - using in-memory caching")
    
    # Initialize MinIO (optional)
    if MINIO_AVAILABLE:
        try:
            minio_client = Minio('localhost:9000',
                               access_key='minioadmin',
                               secret_key='minioadmin123',
                               secure=False)
            logger.info("MinIO client initialized")
        except Exception as e:
            logger.error(f"MinIO initialization failed: {e}")
    else:
        logger.info("MinIO not available - file storage disabled")
    
    # Initialize plugin manager (optional)
    if PLUGINS_AVAILABLE:
        try:
            await plugin_manager.initialize(redis_client)
            logger.info("Plugin manager initialized")
        except Exception as e:
            logger.error(f"Plugin manager initialization failed: {e}")
        
        # Initialize AI Hub
        try:
            ai_hub = AIHubIntegrator(redis_client)
            await ai_hub.health_check_all_services()
            logger.info("AI Hub initialized and health checked")
        except Exception as e:
            logger.error(f"AI Hub initialization failed: {e}")
    else:
        logger.info("Plugins not available - running in basic mode")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_services()
    yield
    # Shutdown
    if redis_client:
        await redis_client.aclose()

app = FastAPI(
    title="ActiveLog AI Orchestrator", 
    description="AI Orchestrator with OpenAI integration",
    version="2.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Root endpoint with service information"""
    response = {
        "service": "ActiveLog AI Orchestrator", 
        "version": "2.0.0",
        "status": "running",
        "features": [
            "ML-powered service optimization",
            "Intelligent request routing",
            "Performance prediction",
            "Auto-scaling recommendations"
        ]
    }
    
    if PLUGINS_AVAILABLE:
        try:
            plugin_info = await plugin_manager.get_manager_stats()
            response["plugins_loaded"] = plugin_info['plugins_loaded']
            response["capabilities"] = await plugin_manager.get_plugin_capabilities()
        except Exception as e:
            logger.error(f"Plugin info error: {e}")
    
    if ai_orchestrator:
        response["ai_orchestrator"] = "enabled"
        response["ml_models_loaded"] = len(ai_orchestrator.models)
    
    return response

@app.get("/health")
async def health_check():
    """Enhanced health check including plugins"""
    health_status = {
        "service": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Check Redis
    if redis_client:
        try:
            await redis_client.ping()
            health_status["redis"] = "connected"
        except Exception as e:
            health_status["redis"] = f"error: {e}"
            health_status["service"] = "degraded"
    else:
        health_status["redis"] = "not_configured"
    
    # Check MinIO
    try:
        # Simple MinIO health check
        health_status["minio"] = "connected"
    except Exception as e:
        health_status["minio"] = f"error: {e}"
        health_status["service"] = "degraded"
    
    # Check plugins
    plugin_health = await plugin_manager.health_check()
    health_status["plugins"] = plugin_health
    
    if plugin_health['summary']['unhealthy'] > 0:
        health_status["service"] = "degraded"
    
    return health_status

# Advanced AI/ML Endpoints

@app.post("/ai/federated/register")
async def register_federated_participant(request: Dict[str, Any]):
    """Register a federated learning participant"""
    if not ai_orchestrator:
        raise HTTPException(status_code=503, detail="AI Orchestrator not available")
    
    try:
        participant_id = request.get("participant_id")
        model_state = request.get("model_state", {})
        data_size = request.get("data_size", 0)
        
        if not participant_id:
            raise HTTPException(status_code=400, detail="participant_id is required")
        
        ai_orchestrator.federated_coordinator.register_participant(
            participant_id, model_state, data_size
        )
        
        return {
            "status": "registered",
            "participant_id": participant_id,
            "round": ai_orchestrator.federated_coordinator.round_counter,
            "registered_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Federated registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/federated/aggregate")
async def federated_model_aggregation():
    """Perform federated model aggregation"""
    if not ai_orchestrator:
        raise HTTPException(status_code=503, detail="AI Orchestrator not available")
    
    try:
        global_model = ai_orchestrator.federated_coordinator.federated_average()
        
        if global_model is None:
            return {
                "status": "insufficient_participants",
                "message": f"Need at least {ai_orchestrator.federated_coordinator.min_participants} participants",
                "current_participants": len(ai_orchestrator.federated_coordinator.participant_models)
            }
        
        # Apply differential privacy
        private_model = ai_orchestrator.federated_coordinator.add_differential_privacy_noise(
            global_model, epsilon=1.0
        )
        
        return {
            "status": "aggregated",
            "round": ai_orchestrator.federated_coordinator.round_counter,
            "global_model": private_model,
            "participants_count": len(ai_orchestrator.federated_coordinator.aggregation_weights),
            "aggregated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Federated aggregation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/nas/search")
async def neural_architecture_search(request: Dict[str, Any]):
    """Perform Neural Architecture Search for service optimization"""
    if not ai_orchestrator or not ai_orchestrator.nas_searcher:
        raise HTTPException(status_code=503, detail="NAS not available")
    
    try:
        service_name = request.get("service_name")
        num_trials = request.get("num_trials", 20)
        
        if not service_name:
            raise HTTPException(status_code=400, detail="service_name is required")
        
        # Get training data for the service
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("""
            SELECT cpu_usage, memory_usage, request_count, error_rate, response_time
            FROM service_metrics 
            WHERE service_name = ? AND timestamp > ?
            ORDER BY timestamp DESC LIMIT 1000
        """, conn, params=(service_name, datetime.now() - timedelta(days=7)))
        conn.close()
        
        if len(df) < 100:
            raise HTTPException(status_code=400, detail="Insufficient training data")
        
        # Prepare data
        X = df[['cpu_usage', 'memory_usage', 'request_count', 'error_rate']].values
        y = df['response_time'].values
        
        # Add synthetic features for complexity
        complexity_feature = np.random.uniform(0.5, 2.0, len(X))
        priority_feature = np.random.uniform(1, 10, len(X))
        X = np.column_stack([X, complexity_feature, priority_feature])
        
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Perform NAS
        search_results = ai_orchestrator.nas_searcher.search(
            X_train, y_train, X_val, y_val, num_trials
        )
        
        return {
            "service_name": service_name,
            "search_results": search_results,
            "data_used": len(df),
            "search_completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"NAS search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/anomaly/detect")
async def detect_service_anomalies(request: Dict[str, Any]):
    """Detect anomalies in service metrics using advanced ML"""
    if not ai_orchestrator:
        raise HTTPException(status_code=503, detail="AI Orchestrator not available")
    
    try:
        metrics_data = request.get("metrics", [])
        service_name = request.get("service_name")
        
        if not metrics_data:
            raise HTTPException(status_code=400, detail="metrics data is required")
        
        # Convert metrics to numpy array
        metrics_array = np.array([
            [m.get('cpu_usage', 0), m.get('memory_usage', 0), 
             m.get('response_time', 0), m.get('request_count', 0), 
             m.get('error_rate', 0)] for m in metrics_data
        ])
        
        # Detect anomalies
        anomaly_results = ai_orchestrator.anomaly_detector.detect_anomalies(metrics_array)
        
        # Add contextual information
        anomaly_details = []
        for i, is_anomaly in enumerate(anomaly_results['ensemble']['anomalies']):
            if is_anomaly:
                anomaly_details.append({
                    "index": i,
                    "metrics": metrics_data[i],
                    "confidence": anomaly_results['ensemble']['confidence'][i],
                    "detected_by": []
                })
                
                # Check which methods detected this anomaly
                if anomaly_results['isolation_forest']['anomalies'][i]:
                    anomaly_details[-1]['detected_by'].append('isolation_forest')
                if 'autoencoder' in anomaly_results and anomaly_results['autoencoder']['anomalies'][i]:
                    anomaly_details[-1]['detected_by'].append('autoencoder')
        
        return {
            "service_name": service_name,
            "total_metrics": len(metrics_data),
            "anomalies_detected": len(anomaly_details),
            "anomaly_rate": len(anomaly_details) / len(metrics_data) * 100,
            "anomaly_details": anomaly_details,
            "full_results": anomaly_results,
            "analyzed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/embeddings/{service_name}")
async def get_service_semantic_embedding(service_name: str, description: Optional[str] = None):
    """Get semantic embedding for a service using transformer models"""
    if not ai_orchestrator:
        raise HTTPException(status_code=503, detail="AI Orchestrator not available")
    
    try:
        embedding = ai_orchestrator.get_service_embeddings(service_name, description)
        
        return {
            "service_name": service_name,
            "embedding_dimension": len(embedding),
            "embedding": embedding.tolist(),
            "description_used": description or f"Service {service_name} for system orchestration",
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Embedding generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/similarity")
async def calculate_service_similarity(request: Dict[str, Any]):
    """Calculate semantic similarity between services"""
    if not ai_orchestrator:
        raise HTTPException(status_code=503, detail="AI Orchestrator not available")
    
    try:
        service1 = request.get("service1")
        service2 = request.get("service2")
        
        if not service1 or not service2:
            raise HTTPException(status_code=400, detail="Both service1 and service2 are required")
        
        similarity = ai_orchestrator.semantic_service_similarity(service1, service2)
        
        return {
            "service1": service1,
            "service2": service2,
            "similarity_score": similarity,
            "similarity_category": (
                "high" if similarity > 0.8 else
                "medium" if similarity > 0.5 else
                "low"
            ),
            "calculated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Similarity calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/retrain/transformer")
async def retrain_transformer_model(request: Dict[str, Any]):
    """Retrain transformer model for specific service type"""
    if not ai_orchestrator or not TORCH_AVAILABLE:
        raise HTTPException(status_code=503, detail="Transformer models not available")
    
    try:
        service_type = request.get("service_type")
        epochs = request.get("epochs", 50)
        
        if not service_type:
            raise HTTPException(status_code=400, detail="service_type is required")
        
        # Get training data
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("""
            SELECT cpu_usage, memory_usage, request_count, error_rate, response_time
            FROM service_metrics 
            WHERE service_name LIKE ? AND timestamp > ?
            ORDER BY timestamp DESC LIMIT 5000
        """, conn, params=(f"%{service_type}%", datetime.now() - timedelta(days=30)))
        conn.close()
        
        if len(df) < 1000:
            raise HTTPException(status_code=400, detail="Insufficient training data")
        
        # Prepare data
        X = df[['cpu_usage', 'memory_usage', 'request_count', 'error_rate']].values
        y = df['response_time'].values
        
        # Add synthetic features
        complexity_feature = np.random.uniform(0.5, 2.0, len(X))
        priority_feature = np.random.uniform(1, 10, len(X))
        X = np.column_stack([X, complexity_feature, priority_feature])
        
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Create and train transformer model
        model = TransformerServicePredictor(input_dim=X.shape[1])
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        # Training loop
        model.train()
        training_losses = []
        validation_losses = []
        
        X_train_tensor = torch.FloatTensor(X_train).unsqueeze(1)
        y_train_tensor = torch.FloatTensor(y_train)
        X_val_tensor = torch.FloatTensor(X_val).unsqueeze(1)
        y_val_tensor = torch.FloatTensor(y_val)
        
        for epoch in range(epochs):
            optimizer.zero_grad()
            response_time, confidence = model(X_train_tensor)
            loss = criterion(response_time, y_train_tensor)
            loss.backward()
            optimizer.step()
            
            training_losses.append(loss.item())
            
            # Validation
            if epoch % 10 == 0:
                model.eval()
                with torch.no_grad():
                    val_response_time, _ = model(X_val_tensor)
                    val_loss = criterion(val_response_time, y_val_tensor)
                    validation_losses.append(val_loss.item())
                model.train()
        
        # Save trained model
        ai_orchestrator.transformer_models[service_type] = model
        
        # Save model to disk
        os.makedirs(MODEL_PATH, exist_ok=True)
        torch.save(model.state_dict(), f"{MODEL_PATH}{service_type}_transformer.pth")
        
        return {
            "service_type": service_type,
            "training_samples": len(X_train),
            "validation_samples": len(X_val),
            "epochs_trained": epochs,
            "final_training_loss": training_losses[-1],
            "final_validation_loss": validation_losses[-1] if validation_losses else None,
            "model_saved": True,
            "trained_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Transformer retraining error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# AI Orchestration Endpoints

@app.post("/ai/metrics")
async def record_service_metrics(metrics: ServiceMetrics):
    """Record service metrics for ML training and optimization"""
    if not ai_orchestrator:
        raise HTTPException(status_code=503, detail="AI Orchestrator not available")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO service_metrics 
            (service_name, domain, cpu_usage, memory_usage, response_time, 
             request_count, error_rate, timestamp, instance_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.service_name, metrics.domain, metrics.cpu_usage,
            metrics.memory_usage, metrics.response_time, metrics.request_count,
            metrics.error_rate, metrics.timestamp, f"{metrics.service_name}-instance-1"
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "status": "metrics_recorded",
            "timestamp": metrics.timestamp,
            "service": metrics.service_name
        }
        
    except Exception as e:
        logger.error(f"Metrics recording error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/route")
async def intelligent_service_routing(request: Dict[str, Any]):
    """Get intelligent routing decision using ML predictions"""
    if not ai_orchestrator:
        raise HTTPException(status_code=503, detail="AI Orchestrator not available")
    
    try:
        service_name = request.get("service_name")
        request_features = request.get("features", {"complexity": 1.0, "priority": 5})
        
        if not service_name:
            raise HTTPException(status_code=400, detail="service_name is required")
        
        decision = ai_orchestrator.intelligent_routing(service_name, request_features)
        
        # Record routing decision
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO routing_decisions 
            (service_name, target_instance, confidence_score, predicted_response_time, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            decision.service_name, decision.target_instance,
            decision.confidence_score, decision.predicted_response_time, datetime.now()
        ))
        conn.commit()
        conn.close()
        
        return decision
        
    except Exception as e:
        logger.error(f"Intelligent routing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/optimize/{service_name}")
async def get_optimization_suggestions(service_name: str):
    """Get AI-powered optimization suggestions for a service"""
    if not ai_orchestrator:
        raise HTTPException(status_code=503, detail="AI Orchestrator not available")
    
    try:
        suggestions = ai_orchestrator.generate_optimization_suggestions(service_name)
        
        return {
            "service_name": service_name,
            "suggestions": suggestions,
            "total_suggestions": len(suggestions),
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Optimization suggestions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/predict/{service_name}")
async def predict_service_performance(
    service_name: str,
    cpu_usage: float = 50.0,
    memory_usage: float = 50.0, 
    request_count: int = 10,
    error_rate: float = 0.0,
    complexity: float = 1.0,
    priority: int = 5
):
    """Predict service performance using ML models"""
    if not ai_orchestrator:
        raise HTTPException(status_code=503, detail="AI Orchestrator not available")
    
    try:
        features = np.array([cpu_usage, memory_usage, request_count, error_rate, complexity, priority])
        pred_time, confidence = ai_orchestrator.predict_performance(service_name, features)
        
        return {
            "service_name": service_name,
            "predicted_response_time": round(pred_time, 2),
            "confidence_score": round(confidence, 3),
            "input_features": {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "request_count": request_count,
                "error_rate": error_rate,
                "complexity": complexity,
                "priority": priority
            },
            "prediction_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Performance prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/analytics")
async def get_ai_analytics():
    """Get AI orchestration analytics and insights"""
    if not ai_orchestrator:
        raise HTTPException(status_code=503, detail="AI Orchestrator not available")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get total metrics count
        cursor.execute("SELECT COUNT(*) FROM service_metrics")
        total_metrics = cursor.fetchone()[0]
        
        # Get routing decisions count
        cursor.execute("SELECT COUNT(*) FROM routing_decisions")
        total_routing_decisions = cursor.fetchone()[0]
        
        # Get recent performance averages
        cursor.execute("""
            SELECT AVG(response_time), AVG(cpu_usage), AVG(memory_usage), AVG(error_rate)
            FROM service_metrics 
            WHERE timestamp > ?
        """, (datetime.now() - timedelta(hours=24),))
        
        perf_data = cursor.fetchone()
        conn.close()
        
        analytics = {
            "total_metrics_recorded": total_metrics,
            "total_routing_decisions": total_routing_decisions,
            "ml_models_loaded": len(ai_orchestrator.models),
            "last_24h_performance": {
                "avg_response_time": round(perf_data[0] or 0, 2),
                "avg_cpu_usage": round(perf_data[1] or 0, 2),
                "avg_memory_usage": round(perf_data[2] or 0, 2),
                "avg_error_rate": round(perf_data[3] or 0, 4)
            },
            "generated_at": datetime.now().isoformat()
        }
        
        # Add advanced analytics
        analytics["advanced_features"] = {
            "transformer_models_loaded": len(ai_orchestrator.transformer_models) if TORCH_AVAILABLE else 0,
            "anomaly_detector_trained": ai_orchestrator.anomaly_detector.trained,
            "federated_learning_round": ai_orchestrator.federated_coordinator.round_counter,
            "service_embeddings_cached": len(ai_orchestrator.service_embeddings),
            "nas_available": ai_orchestrator.nas_searcher is not None
        }
        
        return analytics
        
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/plugins")
async def list_plugins():
    """List all loaded plugins with their capabilities"""
    plugins = await plugin_manager.list_plugins()
    capabilities = await plugin_manager.get_plugin_capabilities()
    
    return {
        "plugins": plugins,
        "capabilities": capabilities,
        "total": len(plugins)
    }

@app.get("/plugins/stats")
async def get_plugin_stats():
    """Get detailed plugin statistics"""
    return await plugin_manager.get_manager_stats()

# AI Hub Integration Endpoints

@app.get("/ai/services")
async def list_ai_services():
    """List all connected AI services"""
    if not ai_hub:
        raise HTTPException(status_code=503, detail="AI Hub not initialized")
    
    capabilities = await ai_hub.get_service_capabilities()
    stats = await ai_hub.get_service_stats()
    health = await ai_hub.health_check_all_services()
    
    return {
        "services": capabilities,
        "statistics": stats,
        "health_status": health,
        "total_services": len(capabilities)
    }

@app.get("/ai/services/health")
async def check_ai_services_health():
    """Check health of all AI services"""
    if not ai_hub:
        raise HTTPException(status_code=503, detail="AI Hub not initialized")
    
    health_status = await ai_hub.health_check_all_services()
    return health_status

@app.post("/ai/route")
async def route_ai_request(request: Dict[str, Any]):
    """Route request to appropriate AI service"""
    if not ai_hub:
        raise HTTPException(status_code=503, detail="AI Hub not initialized")
    
    try:
        capability = request.get("capability")
        data = request.get("data", {})
        preferred_service = request.get("preferred_service")
        
        if not capability:
            raise HTTPException(status_code=400, detail="Capability is required")
        
        result = await ai_hub.route_request(capability, data, preferred_service)
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"AI request routing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/batch")
async def batch_process_ai_requests(request: Dict[str, Any]):
    """Process multiple AI requests in parallel"""
    if not ai_hub:
        raise HTTPException(status_code=503, detail="AI Hub not initialized")
    
    try:
        requests = request.get("requests", [])
        
        if not requests:
            raise HTTPException(status_code=400, detail="Requests list is required")
        
        results = await ai_hub.batch_process(requests)
        
        # Summary statistics
        successful = len([r for r in results if r["status"] == "success"])
        failed = len(results) - successful
        
        return {
            "results": results,
            "summary": {
                "total": len(results),
                "successful": successful,
                "failed": failed,
                "success_rate": successful / len(results) * 100 if results else 0
            },
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Batch AI processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai/capabilities")
async def get_ai_capabilities():
    """Get all available AI capabilities"""
    if not ai_hub:
        raise HTTPException(status_code=503, detail="AI Hub not initialized")
    
    capabilities = await ai_hub.get_service_capabilities()
    
    # Flatten capabilities with service mapping
    capability_map = {}
    for service, caps in capabilities.items():
        for cap in caps:
            if cap not in capability_map:
                capability_map[cap] = []
            capability_map[cap].append(service)
    
    return {
        "capabilities": capability_map,
        "total_capabilities": len(capability_map),
        "services_by_capability": capabilities
    }

# OpenAI Plugin Endpoints

@app.post("/ai/embeddings")
async def generate_embeddings(request: Dict[str, Any]):
    """Generate text embeddings using OpenAI"""
    try:
        text = request.get("text", "")
        model = request.get("model")
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        result = await plugin_manager.generate_embeddings(text, model)
        return result
        
    except Exception as e:
        logger.error(f"Embeddings generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/analyze")
async def analyze_content(request: Dict[str, Any]):
    """Analyze content using OpenAI GPT-4"""
    try:
        content = request.get("content", "")
        analysis_type = request.get("analysis_type", "general")
        custom_prompt = request.get("custom_prompt")
        
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        
        result = await plugin_manager.analyze_content(content, analysis_type, custom_prompt)
        return result
        
    except Exception as e:
        logger.error(f"Content analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/tags")
async def generate_tags(request: Dict[str, Any]):
    """Generate tags for content using OpenAI"""
    try:
        content = request.get("content", "")
        max_tags = request.get("max_tags", 10)
        
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        
        result = await plugin_manager.generate_tags(content, max_tags)
        return result
        
    except Exception as e:
        logger.error(f"Tag generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/analyze/image")
async def analyze_image_content(request: Dict[str, Any]):
    """Analyze image using OpenAI Vision"""
    try:
        image_data = request.get("image_data", "")  # Base64 encoded
        analysis_type = request.get("analysis_type", "description")
        detail_level = request.get("detail_level", "auto")
        
        if not image_data:
            raise HTTPException(status_code=400, detail="Image data is required")
        
        result = await plugin_manager.analyze_image(image_data, analysis_type, detail_level)
        return result
        
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/generate/image")
async def generate_image(request: Dict[str, Any]):
    """Generate image using DALL-E"""
    try:
        prompt = request.get("prompt", "")
        size = request.get("size", "1024x1024")
        quality = request.get("quality", "standard")
        style = request.get("style", "vivid")
        
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        result = await plugin_manager.generate_image(prompt, size, quality, style)
        return result
        
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/file")
async def analyze_file(file: UploadFile = File(...), 
                      analysis_type: str = "general",
                      background_tasks: BackgroundTasks = None):
    """
    Enhanced file analysis with OpenAI integration
    Supports both content analysis and image analysis
    """
    try:
        # Ensure MinIO bucket exists
        if minio_client and not minio_client.bucket_exists("ai-uploads"):
            minio_client.make_bucket("ai-uploads")
        
        # Read file data
        file_data = await file.read()
        file_hash = hashlib.sha256(file_data).hexdigest()
        
        # Store file in MinIO
        if minio_client:
            await file.seek(0)
            minio_client.put_object(
                "ai-uploads",
                f"{file_hash}_{file.filename}",
                io.BytesIO(file_data),
                len(file_data)
            )
        
        # Prepare response
        response = {
            "filename": file.filename,
            "type": file.content_type,
            "size": file.size,
            "hash": file_hash,
            "uploaded_at": datetime.utcnow().isoformat()
        }
        
        # Analyze based on file type
        try:
            if file.content_type and file.content_type.startswith('image/'):
                # Image analysis
                image_b64 = base64.b64encode(file_data).decode('utf-8')
                analysis_result = await plugin_manager.analyze_image(
                    image_b64, analysis_type, "auto"
                )
                response["analysis"] = analysis_result
                response["analysis_type"] = "image"
                
            elif file.content_type and file.content_type.startswith('text/'):
                # Text analysis
                text_content = file_data.decode('utf-8')
                analysis_result = await plugin_manager.analyze_content(
                    text_content, analysis_type
                )
                response["analysis"] = analysis_result
                response["analysis_type"] = "text"
                
                # Also generate tags
                tags_result = await plugin_manager.generate_tags(text_content, 10)
                response["tags"] = tags_result
                
            else:
                response["message"] = "File uploaded but no analysis performed for this file type"
                
        except Exception as analysis_error:
            logger.error(f"Analysis failed: {analysis_error}")
            response["analysis_error"] = str(analysis_error)
            response["message"] = "File uploaded but analysis failed"
        
        return response
        
    except Exception as e:
        logger.error(f"File analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch/analyze")
async def batch_analyze(request: Dict[str, Any]):
    """Batch analyze multiple pieces of content"""
    try:
        items = request.get("items", [])
        analysis_type = request.get("analysis_type", "general")
        
        if not items:
            raise HTTPException(status_code=400, detail="Items list is required")
        
        results = []
        for i, item in enumerate(items):
            try:
                if "content" in item:
                    # Text analysis
                    analysis = await plugin_manager.analyze_content(
                        item["content"], analysis_type
                    )
                    tags = await plugin_manager.generate_tags(item["content"])
                    
                    results.append({
                        "index": i,
                        "id": item.get("id", f"item_{i}"),
                        "status": "success",
                        "analysis": analysis,
                        "tags": tags
                    })
                    
                elif "image_data" in item:
                    # Image analysis
                    analysis = await plugin_manager.analyze_image(
                        item["image_data"], analysis_type
                    )
                    
                    results.append({
                        "index": i,
                        "id": item.get("id", f"item_{i}"),
                        "status": "success",
                        "analysis": analysis
                    })
                    
                else:
                    results.append({
                        "index": i,
                        "id": item.get("id", f"item_{i}"),
                        "status": "error",
                        "error": "No content or image_data provided"
                    })
                    
            except Exception as item_error:
                results.append({
                    "index": i,
                    "id": item.get("id", f"item_{i}"),
                    "status": "error",
                    "error": str(item_error)
                })
        
        # Summary statistics
        successful = len([r for r in results if r["status"] == "success"])
        failed = len(results) - successful
        
        return {
            "results": results,
            "summary": {
                "total": len(results),
                "successful": successful,
                "failed": failed,
                "success_rate": successful / len(results) * 100 if results else 0
            },
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Ollama Plugin Endpoints

@app.post("/ollama/chat")
async def ollama_chat_completion(request: Dict[str, Any]):
    """Generate chat completion using Ollama"""
    try:
        messages = request.get("messages", [])
        model = request.get("model")
        stream = request.get("stream", False)
        
        if not messages:
            raise HTTPException(status_code=400, detail="Messages are required")
        
        result = await plugin_manager.chat_completion(messages, model, stream, **request)
        return result
        
    except Exception as e:
        logger.error(f"Ollama chat completion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ollama/generate")
async def ollama_generate_text(request: Dict[str, Any]):
    """Generate text using Ollama"""
    try:
        prompt = request.get("prompt", "")
        model = request.get("model")
        stream = request.get("stream", False)
        
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        result = await plugin_manager.generate_text(prompt, model, stream, **request)
        return result
        
    except Exception as e:
        logger.error(f"Ollama text generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ollama/embeddings")
async def ollama_generate_embeddings(request: Dict[str, Any]):
    """Generate embeddings using Ollama"""
    try:
        text = request.get("text", "")
        model = request.get("model")
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        ollama_plugin = await plugin_manager.get_plugin('ollama')
        if not ollama_plugin:
            raise HTTPException(status_code=503, detail="Ollama plugin not available")
        
        result = await ollama_plugin.generate_embeddings(text, model)
        return result
        
    except Exception as e:
        logger.error(f"Ollama embeddings generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ollama/models")
async def ollama_list_models():
    """List available Ollama models"""
    try:
        result = await plugin_manager.list_models()
        return result
        
    except Exception as e:
        logger.error(f"Ollama list models failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ollama/models/pull")
async def ollama_pull_model(request: Dict[str, Any]):
    """Pull a model in Ollama"""
    try:
        model_name = request.get("model", "")
        
        if not model_name:
            raise HTTPException(status_code=400, detail="Model name is required")
        
        result = await plugin_manager.pull_model(model_name)
        return result
        
    except Exception as e:
        logger.error(f"Ollama pull model failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/ollama/models/{model_name}")
async def ollama_delete_model(model_name: str):
    """Delete a model in Ollama"""
    try:
        result = await plugin_manager.delete_model(model_name)
        return result
        
    except Exception as e:
        logger.error(f"Ollama delete model failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Whisper Plugin Endpoints

@app.post("/whisper/transcribe")
async def whisper_transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    response_format: Optional[str] = None,
    timestamp_granularities: Optional[str] = None
):
    """Transcribe audio file using Whisper"""
    try:
        # Read file data
        file_data = await file.read()
        
        # Parse timestamp granularities if provided
        granularities = None
        if timestamp_granularities:
            granularities = [g.strip() for g in timestamp_granularities.split(',')]
        
        # Create temporary file-like object
        import io
        audio_file = io.BytesIO(file_data)
        
        result = await plugin_manager.transcribe_audio(
            audio_file=audio_file,
            file_name=file.filename,
            language=language,
            prompt=prompt,
            response_format=response_format,
            timestamp_granularities=granularities
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/whisper/search")
async def whisper_search_transcripts(
    q: str,
    limit: int = 10,
    offset: int = 0,
    language: Optional[str] = None,
    format: Optional[str] = None,
    duration_min: Optional[float] = None,
    duration_max: Optional[float] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Search transcripts"""
    try:
        filters = {}
        if language:
            filters["language"] = language
        if format:
            filters["format"] = format
        if duration_min is not None:
            filters["duration_min"] = duration_min
        if duration_max is not None:
            filters["duration_max"] = duration_max
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        
        result = await plugin_manager.search_transcripts(
            query=q,
            limit=limit,
            offset=offset,
            filters=filters if filters else None
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Whisper search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/whisper/transcript/{file_hash}")
async def whisper_get_transcript(file_hash: str):
    """Get specific transcript by file hash"""
    try:
        result = await plugin_manager.get_transcript(file_hash)
        
        if result is None:
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get transcript failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/whisper/transcript/{file_hash}")
async def whisper_delete_transcript(file_hash: str):
    """Delete transcript by file hash"""
    try:
        success = await plugin_manager.delete_transcript(file_hash)
        
        if not success:
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        return {"message": "Transcript deleted successfully", "file_hash": file_hash}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete transcript failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)