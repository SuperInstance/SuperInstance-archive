import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import json
import sqlite3
from pathlib import Path
import numpy as np
from collections import defaultdict, deque
import pickle
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class PredictionModel(Enum):
    LINEAR = "linear"
    RANDOM_FOREST = "random_forest"
    TIME_SERIES = "time_series"
    ENSEMBLE = "ensemble"

@dataclass
class WorkloadPattern:
    pattern_id: str
    name: str
    description: str
    time_range: Tuple[int, int]  # Hour range (start, end)
    days_of_week: List[int]  # 0-6, Monday-Sunday
    expected_load_multiplier: float
    confidence: float
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class LoadPrediction:
    timestamp: datetime
    predicted_load: float
    confidence: float
    model_used: str
    features_used: List[str]
    prediction_horizon_minutes: int
    created_at: datetime = field(default_factory=datetime.now)

class TimeSeriesPredictor:
    """Time series prediction using moving averages and seasonal patterns"""
    
    def __init__(self):
        self.seasonal_patterns = {}
        self.trend_data = deque(maxlen=1000)
        self.hourly_patterns = defaultdict(list)
        self.daily_patterns = defaultdict(list)
        self.weekly_patterns = defaultdict(list)
    
    def train(self, historical_data: List[Dict[str, Any]]):
        """Train time series model with historical data"""
        try:
            # Process historical data
            for data_point in historical_data:
                timestamp = datetime.fromisoformat(data_point['timestamp']) if isinstance(data_point['timestamp'], str) else data_point['timestamp']
                load = data_point['load']
                
                # Extract temporal features
                hour = timestamp.hour
                day_of_week = timestamp.weekday()
                day_of_month = timestamp.day
                
                # Store patterns
                self.hourly_patterns[hour].append(load)
                self.daily_patterns[day_of_week].append(load)
                self.weekly_patterns[timestamp.isocalendar()[1] % 4].append(load)  # 4-week cycle
                
                self.trend_data.append((timestamp, load))
            
            # Calculate pattern averages
            self.seasonal_patterns = {
                'hourly': {hour: np.mean(loads) for hour, loads in self.hourly_patterns.items()},
                'daily': {day: np.mean(loads) for day, loads in self.daily_patterns.items()},
                'weekly': {week: np.mean(loads) for week, loads in self.weekly_patterns.items()}
            }
            
            logger.info(f"Time series model trained with {len(historical_data)} data points")
            
        except Exception as e:
            logger.error(f"Failed to train time series model: {e}")
    
    def predict(self, target_time: datetime, horizon_minutes: int = 60) -> LoadPrediction:
        """Predict load at target time"""
        try:
            # Base prediction from seasonal patterns
            hour = target_time.hour
            day_of_week = target_time.weekday()
            week = target_time.isocalendar()[1] % 4
            
            base_load = 1.0
            confidence = 0.5
            
            # Hourly pattern
            if hour in self.seasonal_patterns.get('hourly', {}):
                hourly_load = self.seasonal_patterns['hourly'][hour]
                base_load *= hourly_load
                confidence += 0.2
            
            # Daily pattern
            if day_of_week in self.seasonal_patterns.get('daily', {}):
                daily_load = self.seasonal_patterns['daily'][day_of_week]
                base_load *= daily_load
                confidence += 0.1
            
            # Weekly pattern
            if week in self.seasonal_patterns.get('weekly', {}):
                weekly_load = self.seasonal_patterns['weekly'][week]
                base_load *= weekly_load
                confidence += 0.1
            
            # Trend adjustment
            if len(self.trend_data) > 10:
                recent_trend = self._calculate_trend()
                base_load *= (1 + recent_trend * horizon_minutes / 60)
                confidence += 0.1
            
            # Normalize confidence
            confidence = min(confidence, 1.0)
            
            return LoadPrediction(
                timestamp=target_time,
                predicted_load=max(0.1, base_load),
                confidence=confidence,
                model_used="time_series",
                features_used=['hour', 'day_of_week', 'week', 'trend'],
                prediction_horizon_minutes=horizon_minutes
            )
            
        except Exception as e:
            logger.error(f"Time series prediction failed: {e}")
            return LoadPrediction(
                timestamp=target_time,
                predicted_load=1.0,
                confidence=0.1,
                model_used="time_series_fallback",
                features_used=[],
                prediction_horizon_minutes=horizon_minutes
            )
    
    def _calculate_trend(self) -> float:
        """Calculate recent trend from data"""
        if len(self.trend_data) < 2:
            return 0.0
        
        # Use last 50 points for trend
        recent_data = list(self.trend_data)[-50:]
        
        if len(recent_data) < 2:
            return 0.0
        
        # Calculate simple linear trend
        timestamps = [(point[0] - recent_data[0][0]).total_seconds() / 3600 for point in recent_data]  # Hours
        loads = [point[1] for point in recent_data]
        
        try:
            coeffs = np.polyfit(timestamps, loads, 1)
            return coeffs[0]  # Slope (trend per hour)
        except:
            return 0.0

class MLPredictor:
    """Machine learning-based load predictor"""
    
    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.feature_names = []
        self.trained = False
        self.model_performance = {}
    
    def train(self, historical_data: List[Dict[str, Any]], model_type: PredictionModel = PredictionModel.RANDOM_FOREST):
        """Train ML model with historical data"""
        try:
            if len(historical_data) < 50:
                logger.warning("Insufficient data for ML training")
                return
            
            # Prepare features and targets
            X, y = self._prepare_features(historical_data)
            
            if X.shape[0] == 0:
                logger.error("No valid features extracted")
                return
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train models
            if model_type in [PredictionModel.LINEAR, PredictionModel.ENSEMBLE]:
                linear_model = LinearRegression()
                linear_model.fit(X_train_scaled, y_train)
                self.models['linear'] = linear_model
                
                # Evaluate
                y_pred = linear_model.predict(X_test_scaled)
                mae = mean_absolute_error(y_test, y_pred)
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                self.model_performance['linear'] = {'mae': mae, 'rmse': rmse}
            
            if model_type in [PredictionModel.RANDOM_FOREST, PredictionModel.ENSEMBLE]:
                rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
                rf_model.fit(X_train_scaled, y_train)
                self.models['random_forest'] = rf_model
                
                # Evaluate
                y_pred = rf_model.predict(X_test_scaled)
                mae = mean_absolute_error(y_test, y_pred)
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                self.model_performance['random_forest'] = {'mae': mae, 'rmse': rmse}
            
            self.trained = True
            logger.info(f"ML models trained with {len(historical_data)} data points")
            
        except Exception as e:
            logger.error(f"Failed to train ML models: {e}")
    
    def predict(self, target_time: datetime, current_metrics: Dict[str, float], horizon_minutes: int = 60) -> LoadPrediction:
        """Predict load using ML models"""
        try:
            if not self.trained or not self.models:
                return LoadPrediction(
                    timestamp=target_time,
                    predicted_load=1.0,
                    confidence=0.1,
                    model_used="ml_fallback",
                    features_used=[],
                    prediction_horizon_minutes=horizon_minutes
                )
            
            # Prepare features for prediction
            features = self._extract_features(target_time, current_metrics)
            features_array = np.array([features]).reshape(1, -1)
            features_scaled = self.scaler.transform(features_array)
            
            predictions = {}
            confidences = {}
            
            # Make predictions with all available models
            for model_name, model in self.models.items():
                pred = model.predict(features_scaled)[0]
                predictions[model_name] = max(0.1, pred)
                
                # Calculate confidence based on model performance
                if model_name in self.model_performance:
                    mae = self.model_performance[model_name]['mae']
                    confidence = 1.0 / (1.0 + mae)  # Higher MAE = lower confidence
                    confidences[model_name] = min(confidence, 0.9)
                else:
                    confidences[model_name] = 0.5
            
            # Use ensemble if multiple models available
            if len(predictions) > 1:
                # Weighted average based on confidence
                total_weight = sum(confidences.values())
                weighted_prediction = sum(
                    pred * confidences[model_name] 
                    for model_name, pred in predictions.items()
                ) / total_weight
                
                avg_confidence = np.mean(list(confidences.values()))
                model_used = "ensemble"
            else:
                model_name = list(predictions.keys())[0]
                weighted_prediction = predictions[model_name]
                avg_confidence = confidences[model_name]
                model_used = model_name
            
            return LoadPrediction(
                timestamp=target_time,
                predicted_load=weighted_prediction,
                confidence=avg_confidence,
                model_used=model_used,
                features_used=self.feature_names,
                prediction_horizon_minutes=horizon_minutes
            )
            
        except Exception as e:
            logger.error(f"ML prediction failed: {e}")
            return LoadPrediction(
                timestamp=target_time,
                predicted_load=1.0,
                confidence=0.1,
                model_used="ml_error_fallback",
                features_used=[],
                prediction_horizon_minutes=horizon_minutes
            )
    
    def _prepare_features(self, historical_data: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and targets from historical data"""
        features = []
        targets = []
        
        for data_point in historical_data:
            try:
                timestamp = datetime.fromisoformat(data_point['timestamp']) if isinstance(data_point['timestamp'], str) else data_point['timestamp']
                load = data_point['load']
                metrics = data_point.get('metrics', {})
                
                feature_vector = self._extract_features(timestamp, metrics)
                
                features.append(feature_vector)
                targets.append(load)
                
            except Exception as e:
                logger.debug(f"Skipping data point due to error: {e}")
                continue
        
        return np.array(features), np.array(targets)
    
    def _extract_features(self, timestamp: datetime, metrics: Dict[str, float]) -> List[float]:
        """Extract features from timestamp and metrics"""
        features = []
        feature_names = []
        
        # Temporal features
        features.extend([
            timestamp.hour,
            timestamp.weekday(),
            timestamp.day,
            timestamp.month,
            int(timestamp.strftime('%U'))  # Week of year
        ])
        feature_names.extend(['hour', 'weekday', 'day', 'month', 'week_of_year'])
        
        # Cyclical temporal features (to handle wraparound)
        features.extend([
            np.sin(2 * np.pi * timestamp.hour / 24),
            np.cos(2 * np.pi * timestamp.hour / 24),
            np.sin(2 * np.pi * timestamp.weekday() / 7),
            np.cos(2 * np.pi * timestamp.weekday() / 7)
        ])
        feature_names.extend(['hour_sin', 'hour_cos', 'weekday_sin', 'weekday_cos'])
        
        # Metric features
        metric_keys = ['cpu_utilization', 'memory_utilization', 'queue_length', 'active_tasks', 'throughput']
        for key in metric_keys:
            features.append(metrics.get(key, 0.0))
            feature_names.append(key)
        
        # Derived features
        features.extend([
            metrics.get('cpu_utilization', 0) * metrics.get('memory_utilization', 0),  # Resource pressure
            metrics.get('queue_length', 0) / max(metrics.get('active_tasks', 1), 1),  # Queue pressure
            metrics.get('throughput', 0) / max(metrics.get('active_tasks', 1), 1)  # Efficiency
        ])
        feature_names.extend(['resource_pressure', 'queue_pressure', 'efficiency'])
        
        if not self.feature_names:
            self.feature_names = feature_names
        
        return features
    
    def save_models(self, file_path: str):
        """Save trained models to file"""
        try:
            model_data = {
                'models': self.models,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'trained': self.trained,
                'model_performance': self.model_performance
            }
            
            with open(file_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Models saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
    
    def load_models(self, file_path: str):
        """Load trained models from file"""
        try:
            with open(file_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.models = model_data['models']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.trained = model_data['trained']
            self.model_performance = model_data.get('model_performance', {})
            
            logger.info(f"Models loaded from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")

class LoadPredictor:
    """Main load prediction system"""
    
    def __init__(self, db_path: str = "/home/activeloguser/activelog/data/load_predictor.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.time_series_predictor = TimeSeriesPredictor()
        self.ml_predictor = MLPredictor()
        self.workload_patterns = []
        
        self.running = False
        self.prediction_history = deque(maxlen=1000)
        self.training_data = deque(maxlen=10000)
        
        # Model paths
        self.models_dir = Path("/home/activeloguser/activelog/models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        self._load_workload_patterns()
    
    def _init_database(self):
        """Initialize load predictor database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS load_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    actual_load REAL,
                    cpu_utilization REAL,
                    memory_utilization REAL,
                    queue_length INTEGER,
                    active_tasks INTEGER,
                    throughput REAL,
                    error_rate REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    target_time TIMESTAMP,
                    predicted_load REAL,
                    actual_load REAL,
                    confidence REAL,
                    model_used TEXT,
                    features_used TEXT,
                    prediction_horizon_minutes INTEGER,
                    error REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workload_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id TEXT UNIQUE,
                    name TEXT,
                    description TEXT,
                    time_range_start INTEGER,
                    time_range_end INTEGER,
                    days_of_week TEXT,
                    expected_load_multiplier REAL,
                    confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def _load_workload_patterns(self):
        """Load workload patterns from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT pattern_id, name, description, time_range_start, time_range_end,
                           days_of_week, expected_load_multiplier, confidence
                    FROM workload_patterns
                """)
                
                for row in cursor.fetchall():
                    pattern = WorkloadPattern(
                        pattern_id=row[0],
                        name=row[1],
                        description=row[2],
                        time_range=(row[3], row[4]),
                        days_of_week=json.loads(row[5]),
                        expected_load_multiplier=row[6],
                        confidence=row[7]
                    )
                    self.workload_patterns.append(pattern)
            
            # Add default patterns if none exist
            if not self.workload_patterns:
                self._create_default_patterns()
            
            logger.info(f"Loaded {len(self.workload_patterns)} workload patterns")
            
        except Exception as e:
            logger.error(f"Failed to load workload patterns: {e}")
    
    def _create_default_patterns(self):
        """Create default workload patterns"""
        default_patterns = [
            WorkloadPattern(
                pattern_id="business_hours",
                name="Business Hours",
                description="High load during business hours",
                time_range=(9, 17),
                days_of_week=[0, 1, 2, 3, 4],  # Monday-Friday
                expected_load_multiplier=1.5,
                confidence=0.8
            ),
            WorkloadPattern(
                pattern_id="evening_peak",
                name="Evening Peak",
                description="Peak load in the evening",
                time_range=(18, 22),
                days_of_week=[0, 1, 2, 3, 4, 5, 6],  # All days
                expected_load_multiplier=1.3,
                confidence=0.7
            ),
            WorkloadPattern(
                pattern_id="night_low",
                name="Night Low",
                description="Low load during night hours",
                time_range=(0, 6),
                days_of_week=[0, 1, 2, 3, 4, 5, 6],  # All days
                expected_load_multiplier=0.3,
                confidence=0.9
            ),
            WorkloadPattern(
                pattern_id="weekend_moderate",
                name="Weekend Moderate",
                description="Moderate load during weekends",
                time_range=(10, 20),
                days_of_week=[5, 6],  # Saturday-Sunday
                expected_load_multiplier=0.8,
                confidence=0.6
            )
        ]
        
        for pattern in default_patterns:
            self.add_workload_pattern(pattern)
    
    async def start(self):
        """Start the load predictor"""
        try:
            logger.info("Starting Load Predictor...")
            
            # Load historical data
            await self._load_training_data()
            
            # Train models
            await self._train_models()
            
            self.running = True
            logger.info("Load Predictor started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Load Predictor: {e}")
            raise
    
    async def stop(self):
        """Stop the load predictor"""
        logger.info("Stopping Load Predictor...")
        
        # Save models
        self.ml_predictor.save_models(str(self.models_dir / "ml_models.pkl"))
        
        self.running = False
        logger.info("Load Predictor stopped")
    
    async def predict_load(
        self, 
        target_time: datetime, 
        current_metrics: Dict[str, float],
        horizon_minutes: int = 60,
        model_preference: Optional[PredictionModel] = None
    ) -> LoadPrediction:
        """Predict load at target time"""
        try:
            predictions = []
            
            # Time series prediction
            ts_prediction = self.time_series_predictor.predict(target_time, horizon_minutes)
            predictions.append(ts_prediction)
            
            # ML prediction
            ml_prediction = self.ml_predictor.predict(target_time, current_metrics, horizon_minutes)
            predictions.append(ml_prediction)
            
            # Pattern-based prediction
            pattern_prediction = self._pattern_based_prediction(target_time, horizon_minutes)
            if pattern_prediction:
                predictions.append(pattern_prediction)
            
            # Select best prediction
            if model_preference and model_preference != PredictionModel.ENSEMBLE:
                # Use specific model
                for pred in predictions:
                    if model_preference.value in pred.model_used:
                        final_prediction = pred
                        break
                else:
                    final_prediction = predictions[0] if predictions else None
            else:
                # Use ensemble or best confidence
                if len(predictions) > 1:
                    final_prediction = self._ensemble_prediction(predictions, target_time, horizon_minutes)
                else:
                    final_prediction = predictions[0] if predictions else None
            
            if not final_prediction:
                final_prediction = LoadPrediction(
                    timestamp=target_time,
                    predicted_load=1.0,
                    confidence=0.1,
                    model_used="fallback",
                    features_used=[],
                    prediction_horizon_minutes=horizon_minutes
                )
            
            # Store prediction
            await self._store_prediction(final_prediction)
            self.prediction_history.append(final_prediction)
            
            return final_prediction
            
        except Exception as e:
            logger.error(f"Load prediction failed: {e}")
            return LoadPrediction(
                timestamp=target_time,
                predicted_load=1.0,
                confidence=0.1,
                model_used="error_fallback",
                features_used=[],
                prediction_horizon_minutes=horizon_minutes
            )
    
    def _pattern_based_prediction(self, target_time: datetime, horizon_minutes: int) -> Optional[LoadPrediction]:
        """Make prediction based on workload patterns"""
        try:
            hour = target_time.hour
            day_of_week = target_time.weekday()
            
            matching_patterns = []
            
            for pattern in self.workload_patterns:
                # Check if time matches pattern
                if (pattern.time_range[0] <= hour <= pattern.time_range[1] and 
                    day_of_week in pattern.days_of_week):
                    matching_patterns.append(pattern)
            
            if not matching_patterns:
                return None
            
            # Calculate weighted prediction
            total_weight = sum(p.confidence for p in matching_patterns)
            weighted_multiplier = sum(
                p.expected_load_multiplier * p.confidence 
                for p in matching_patterns
            ) / total_weight
            
            avg_confidence = np.mean([p.confidence for p in matching_patterns])
            
            return LoadPrediction(
                timestamp=target_time,
                predicted_load=weighted_multiplier,
                confidence=avg_confidence,
                model_used="pattern_based",
                features_used=['hour', 'day_of_week', 'patterns'],
                prediction_horizon_minutes=horizon_minutes
            )
            
        except Exception as e:
            logger.error(f"Pattern-based prediction failed: {e}")
            return None
    
    def _ensemble_prediction(
        self, 
        predictions: List[LoadPrediction], 
        target_time: datetime, 
        horizon_minutes: int
    ) -> LoadPrediction:
        """Combine multiple predictions into ensemble prediction"""
        try:
            # Weight predictions by confidence
            total_weight = sum(p.confidence for p in predictions)
            weighted_prediction = sum(
                p.predicted_load * p.confidence 
                for p in predictions
            ) / total_weight
            
            # Average confidence
            avg_confidence = np.mean([p.confidence for p in predictions])
            
            # Combine features used
            all_features = []
            for p in predictions:
                all_features.extend(p.features_used)
            unique_features = list(set(all_features))
            
            # Combine models used
            models_used = "_".join([p.model_used for p in predictions])
            
            return LoadPrediction(
                timestamp=target_time,
                predicted_load=weighted_prediction,
                confidence=min(avg_confidence * 1.1, 1.0),  # Slight boost for ensemble
                model_used=f"ensemble({models_used})",
                features_used=unique_features,
                prediction_horizon_minutes=horizon_minutes
            )
            
        except Exception as e:
            logger.error(f"Ensemble prediction failed: {e}")
            return predictions[0]
    
    async def record_actual_load(
        self, 
        timestamp: datetime, 
        actual_load: float,
        metrics: Dict[str, float]
    ):
        """Record actual load for model training and evaluation"""
        try:
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO load_history 
                    (timestamp, actual_load, cpu_utilization, memory_utilization,
                     queue_length, active_tasks, throughput, error_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    actual_load,
                    metrics.get('cpu_utilization', 0),
                    metrics.get('memory_utilization', 0),
                    metrics.get('queue_length', 0),
                    metrics.get('active_tasks', 0),
                    metrics.get('throughput', 0),
                    metrics.get('error_rate', 0)
                ))
            
            # Add to training data
            training_point = {
                'timestamp': timestamp,
                'load': actual_load,
                'metrics': metrics
            }
            self.training_data.append(training_point)
            
            # Update prediction errors
            await self._update_prediction_errors(timestamp, actual_load)
            
            # Retrain models periodically
            if len(self.training_data) % 100 == 0:
                await self._retrain_models()
            
        except Exception as e:
            logger.error(f"Failed to record actual load: {e}")
    
    async def _update_prediction_errors(self, timestamp: datetime, actual_load: float):
        """Update prediction errors for evaluation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Find recent predictions for this timestamp
                cursor = conn.execute("""
                    SELECT id, predicted_load, confidence, model_used
                    FROM predictions
                    WHERE target_time BETWEEN ? AND ?
                    AND actual_load IS NULL
                """, (
                    timestamp - timedelta(minutes=5),
                    timestamp + timedelta(minutes=5)
                ))
                
                for row in cursor.fetchall():
                    pred_id, predicted_load, confidence, model_used = row
                    error = abs(predicted_load - actual_load)
                    
                    # Update prediction record
                    conn.execute("""
                        UPDATE predictions
                        SET actual_load = ?, error = ?
                        WHERE id = ?
                    """, (actual_load, error, pred_id))
                    
        except Exception as e:
            logger.error(f"Failed to update prediction errors: {e}")
    
    async def _load_training_data(self):
        """Load historical data for training"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT timestamp, actual_load, cpu_utilization, memory_utilization,
                           queue_length, active_tasks, throughput, error_rate
                    FROM load_history
                    ORDER BY timestamp DESC
                    LIMIT 5000
                """)
                
                for row in cursor.fetchall():
                    training_point = {
                        'timestamp': datetime.fromisoformat(row[0]) if isinstance(row[0], str) else row[0],
                        'load': row[1],
                        'metrics': {
                            'cpu_utilization': row[2] or 0,
                            'memory_utilization': row[3] or 0,
                            'queue_length': row[4] or 0,
                            'active_tasks': row[5] or 0,
                            'throughput': row[6] or 0,
                            'error_rate': row[7] or 0
                        }
                    }
                    self.training_data.append(training_point)
            
            logger.info(f"Loaded {len(self.training_data)} training data points")
            
        except Exception as e:
            logger.error(f"Failed to load training data: {e}")
    
    async def _train_models(self):
        """Train prediction models"""
        try:
            if len(self.training_data) < 50:
                logger.info("Insufficient data for training")
                return
            
            training_list = list(self.training_data)
            
            # Train time series model
            self.time_series_predictor.train(training_list)
            
            # Train ML models
            self.ml_predictor.train(training_list, PredictionModel.ENSEMBLE)
            
            logger.info("Prediction models trained successfully")
            
        except Exception as e:
            logger.error(f"Failed to train models: {e}")
    
    async def _retrain_models(self):
        """Retrain models with new data"""
        logger.info("Retraining prediction models...")
        await self._train_models()
    
    async def _store_prediction(self, prediction: LoadPrediction):
        """Store prediction to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO predictions 
                    (timestamp, target_time, predicted_load, confidence, 
                     model_used, features_used, prediction_horizon_minutes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    prediction.created_at,
                    prediction.timestamp,
                    prediction.predicted_load,
                    prediction.confidence,
                    prediction.model_used,
                    json.dumps(prediction.features_used),
                    prediction.prediction_horizon_minutes
                ))
        except Exception as e:
            logger.error(f"Failed to store prediction: {e}")
    
    def add_workload_pattern(self, pattern: WorkloadPattern):
        """Add a workload pattern"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO workload_patterns 
                    (pattern_id, name, description, time_range_start, time_range_end,
                     days_of_week, expected_load_multiplier, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.pattern_id,
                    pattern.name,
                    pattern.description,
                    pattern.time_range[0],
                    pattern.time_range[1],
                    json.dumps(pattern.days_of_week),
                    pattern.expected_load_multiplier,
                    pattern.confidence
                ))
            
            # Update in-memory patterns
            self.workload_patterns = [p for p in self.workload_patterns if p.pattern_id != pattern.pattern_id]
            self.workload_patterns.append(pattern)
            
            logger.info(f"Added workload pattern: {pattern.name}")
            
        except Exception as e:
            logger.error(f"Failed to add workload pattern: {e}")
    
    def get_prediction_accuracy(self, hours: int = 24) -> Dict[str, Any]:
        """Get prediction accuracy metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT model_used, AVG(error), COUNT(*), AVG(confidence)
                    FROM predictions
                    WHERE created_at > datetime('now', '-{} hours')
                    AND error IS NOT NULL
                    GROUP BY model_used
                """.format(hours))
                
                accuracy_by_model = {}
                for row in cursor.fetchall():
                    model_name, avg_error, count, avg_confidence = row
                    accuracy_by_model[model_name] = {
                        'avg_error': avg_error,
                        'prediction_count': count,
                        'avg_confidence': avg_confidence,
                        'accuracy_rate': max(0, 1 - avg_error) if avg_error else 0
                    }
                
                return accuracy_by_model
                
        except Exception as e:
            logger.error(f"Failed to get prediction accuracy: {e}")
            return {}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get load predictor system status"""
        return {
            'running': self.running,
            'training_data_points': len(self.training_data),
            'prediction_history_points': len(self.prediction_history),
            'workload_patterns': len(self.workload_patterns),
            'models_trained': {
                'time_series': len(self.time_series_predictor.seasonal_patterns) > 0,
                'ml_models': self.ml_predictor.trained
            },
            'model_performance': self.ml_predictor.model_performance,
            'recent_predictions': len([
                p for p in self.prediction_history 
                if p.created_at > datetime.now() - timedelta(hours=1)
            ])
        }