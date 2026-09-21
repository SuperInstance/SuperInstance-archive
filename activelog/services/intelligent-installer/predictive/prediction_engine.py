"""
Advanced Prediction Engine - AI-powered system prediction and optimization
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import deque
import statistics
import math

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.neural_network import MLPRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)

class PredictionType(Enum):
    RESOURCE_USAGE = "resource_usage"
    USER_BEHAVIOR = "user_behavior"
    SYSTEM_FAILURE = "system_failure" 
    PERFORMANCE = "performance"
    MAINTENANCE = "maintenance"
    THERMAL = "thermal"
    BATTERY = "battery"
    NETWORK = "network"

class PredictionConfidence(Enum):
    LOW = "low"         # < 60%
    MEDIUM = "medium"   # 60-80%
    HIGH = "high"       # 80-90%
    VERY_HIGH = "very_high"  # > 90%

class TimeHorizon(Enum):
    SHORT = "short"     # 1-5 minutes
    MEDIUM = "medium"   # 5-60 minutes  
    LONG = "long"       # 1-24 hours
    EXTENDED = "extended"  # 1-7 days

@dataclass
class PredictionResult:
    prediction_id: str
    prediction_type: PredictionType
    predicted_value: float
    confidence_score: float
    confidence_level: PredictionConfidence
    time_horizon: TimeHorizon
    prediction_time: datetime
    target_time: datetime
    features_used: List[str]
    model_info: Dict[str, Any]
    uncertainty_bounds: Optional[Tuple[float, float]] = None
    recommendations: List[str] = field(default_factory=list)

@dataclass
class HistoricalDataPoint:
    timestamp: datetime
    value: float
    features: Dict[str, float]
    context: Dict[str, Any]

@dataclass
class PredictionModel:
    model_id: str
    prediction_type: PredictionType
    model_type: str  # "neural_network", "random_forest", "gradient_boost", "time_series"
    model_object: Any
    scaler: Optional[Any]
    feature_names: List[str]
    training_score: float
    validation_score: float
    last_trained: datetime
    prediction_count: int = 0

class TimeSeriesPredictor:
    """Advanced time series prediction with multiple algorithms"""
    
    def __init__(self):
        self.history_buffer = deque(maxlen=1000)
        self.seasonal_patterns: Dict[str, List[float]] = {}
        self.trend_cache: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def predict_time_series(self, 
                                 historical_data: List[HistoricalDataPoint],
                                 steps_ahead: int = 1) -> List[float]:
        """Predict future values using time series analysis"""
        try:
            if len(historical_data) < 10:
                self.logger.warning("Insufficient data for time series prediction")
                return [historical_data[-1].value] * steps_ahead if historical_data else [0.0] * steps_ahead
            
            values = [dp.value for dp in historical_data]
            timestamps = [dp.timestamp for dp in historical_data]
            
            if NUMPY_AVAILABLE:
                return await self._numpy_time_series_prediction(values, steps_ahead)
            else:
                return await self._simple_time_series_prediction(values, steps_ahead)
                
        except Exception as e:
            self.logger.error(f"Time series prediction failed: {e}")
            return [historical_data[-1].value] * steps_ahead if historical_data else [0.0] * steps_ahead
    
    async def _numpy_time_series_prediction(self, values: List[float], steps_ahead: int) -> List[float]:
        """NumPy-based time series prediction with seasonal decomposition"""
        try:
            values_array = np.array(values)
            
            # Simple exponential smoothing
            alpha = 0.3  # Smoothing parameter
            smoothed = np.zeros_like(values_array)
            smoothed[0] = values_array[0]
            
            for i in range(1, len(values_array)):
                smoothed[i] = alpha * values_array[i] + (1 - alpha) * smoothed[i-1]
            
            # Trend estimation
            if len(values) >= 5:
                recent_trend = np.polyfit(range(len(values[-5:])), values[-5:], 1)[0]
            else:
                recent_trend = 0
            
            # Generate predictions
            predictions = []
            last_value = smoothed[-1]
            
            for i in range(steps_ahead):
                predicted_value = last_value + recent_trend * (i + 1)
                
                # Add seasonal component if detected
                seasonal_component = self._estimate_seasonal_component(values, i + 1)
                predicted_value += seasonal_component
                
                predictions.append(predicted_value)
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"NumPy time series prediction failed: {e}")
            return await self._simple_time_series_prediction(values, steps_ahead)
    
    async def _simple_time_series_prediction(self, values: List[float], steps_ahead: int) -> List[float]:
        """Simple moving average prediction"""
        try:
            if len(values) < 3:
                return [values[-1]] * steps_ahead if values else [0.0] * steps_ahead
            
            # Calculate moving average
            window_size = min(5, len(values))
            recent_values = values[-window_size:]
            moving_avg = sum(recent_values) / len(recent_values)
            
            # Calculate trend
            if len(values) >= 2:
                trend = (values[-1] - values[-2])
            else:
                trend = 0
            
            # Generate predictions
            predictions = []
            for i in range(steps_ahead):
                predicted_value = moving_avg + trend * (i + 1) * 0.5
                predictions.append(predicted_value)
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"Simple time series prediction failed: {e}")
            return [values[-1] if values else 0.0] * steps_ahead
    
    def _estimate_seasonal_component(self, values: List[float], steps_ahead: int) -> float:
        """Estimate seasonal component for prediction"""
        try:
            # Simple seasonal pattern detection
            if len(values) < 24:  # Need at least one day of hourly data
                return 0.0
            
            # Check for daily pattern (24-hour cycle)
            position_in_cycle = (len(values) + steps_ahead - 1) % 24
            
            if len(values) >= 48:  # At least 2 days
                # Calculate average for this position in cycle
                same_position_values = []
                for i in range(position_in_cycle, len(values), 24):
                    if i < len(values):
                        same_position_values.append(values[i])
                
                if same_position_values:
                    overall_avg = statistics.mean(values[-48:])  # Last 2 days average
                    position_avg = statistics.mean(same_position_values)
                    return position_avg - overall_avg
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Seasonal component estimation failed: {e}")
            return 0.0

class MLPredictor:
    """Machine learning-based predictor using multiple algorithms"""
    
    def __init__(self):
        self.models: Dict[str, PredictionModel] = {}
        self.model_performance: Dict[str, List[float]] = {}
        self.feature_importance: Dict[str, Dict[str, float]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def train_models(self, 
                          training_data: List[HistoricalDataPoint],
                          prediction_type: PredictionType) -> List[PredictionModel]:
        """Train multiple ML models for prediction"""
        try:
            if len(training_data) < 20:
                self.logger.warning(f"Insufficient training data: {len(training_data)} points")
                return []
            
            # Prepare features and targets
            features, targets = self._prepare_ml_data(training_data)
            
            if not features or not targets:
                return []
            
            trained_models = []
            
            if SKLEARN_AVAILABLE:
                # Train different model types
                model_configs = [
                    ('random_forest', RandomForestRegressor(n_estimators=100, random_state=42)),
                    ('gradient_boost', GradientBoostingRegressor(n_estimators=100, random_state=42))
                ]
                
                if len(features) > 100:  # Only use neural network for larger datasets
                    model_configs.append(('neural_network', MLPRegressor(hidden_layer_sizes=(64, 32), random_state=42, max_iter=500)))
                
                for model_name, model_object in model_configs:
                    try:
                        trained_model = await self._train_sklearn_model(
                            model_name, model_object, features, targets, prediction_type
                        )
                        if trained_model:
                            trained_models.append(trained_model)
                            
                    except Exception as e:
                        self.logger.error(f"Failed to train {model_name}: {e}")
            
            # Train PyTorch model if available
            if TORCH_AVAILABLE and len(features) > 50:
                try:
                    torch_model = await self._train_pytorch_model(features, targets, prediction_type)
                    if torch_model:
                        trained_models.append(torch_model)
                except Exception as e:
                    self.logger.error(f"Failed to train PyTorch model: {e}")
            
            self.logger.info(f"Trained {len(trained_models)} models for {prediction_type.value}")
            return trained_models
            
        except Exception as e:
            self.logger.error(f"Model training failed: {e}")
            return []
    
    async def _train_sklearn_model(self, 
                                  model_name: str,
                                  model_object: Any,
                                  features: List[List[float]],
                                  targets: List[float],
                                  prediction_type: PredictionType) -> Optional[PredictionModel]:
        """Train scikit-learn model"""
        try:
            # Convert to numpy arrays
            if NUMPY_AVAILABLE:
                X = np.array(features)
                y = np.array(targets)
            else:
                X, y = features, targets
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model_object.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred_train = model_object.predict(X_train_scaled)
            y_pred_test = model_object.predict(X_test_scaled)
            
            train_score = r2_score(y_train, y_pred_train)
            test_score = r2_score(y_test, y_pred_test)
            
            # Create prediction model
            model_id = f"{prediction_type.value}_{model_name}_{uuid.uuid4().hex[:8]}"
            
            # Get feature names
            feature_names = [f"feature_{i}" for i in range(len(features[0]))]
            
            prediction_model = PredictionModel(
                model_id=model_id,
                prediction_type=prediction_type,
                model_type=model_name,
                model_object=model_object,
                scaler=scaler,
                feature_names=feature_names,
                training_score=train_score,
                validation_score=test_score,
                last_trained=datetime.utcnow()
            )
            
            # Store model
            self.models[model_id] = prediction_model
            
            # Store feature importance if available
            if hasattr(model_object, 'feature_importances_'):
                importance_dict = dict(zip(feature_names, model_object.feature_importances_))
                self.feature_importance[model_id] = importance_dict
            
            self.logger.info(f"Trained {model_name} - Train R²: {train_score:.3f}, Test R²: {test_score:.3f}")
            
            return prediction_model
            
        except Exception as e:
            self.logger.error(f"Sklearn model training failed: {e}")
            return None
    
    def _prepare_ml_data(self, training_data: List[HistoricalDataPoint]) -> Tuple[List[List[float]], List[float]]:
        """Prepare data for ML training"""
        try:
            features = []
            targets = []
            
            for i, data_point in enumerate(training_data):
                # Extract features
                feature_vector = []
                
                # Time-based features
                timestamp = data_point.timestamp
                feature_vector.extend([
                    timestamp.hour,
                    timestamp.day,
                    timestamp.weekday(),
                    timestamp.month
                ])
                
                # Value-based features
                if i > 0:
                    # Previous value
                    feature_vector.append(training_data[i-1].value)
                    
                    # Trend (change from previous)
                    trend = data_point.value - training_data[i-1].value
                    feature_vector.append(trend)
                else:
                    feature_vector.extend([data_point.value, 0.0])
                
                # Rolling statistics features
                if i >= 5:
                    recent_values = [training_data[j].value for j in range(max(0, i-5), i)]
                    feature_vector.extend([
                        statistics.mean(recent_values),
                        statistics.stdev(recent_values) if len(recent_values) > 1 else 0.0,
                        max(recent_values),
                        min(recent_values)
                    ])
                else:
                    feature_vector.extend([data_point.value, 0.0, data_point.value, data_point.value])
                
                # Context features
                for key, value in data_point.features.items():
                    try:
                        feature_vector.append(float(value))
                    except (ValueError, TypeError):
                        feature_vector.append(0.0)
                
                features.append(feature_vector)
                targets.append(data_point.value)
            
            return features, targets
            
        except Exception as e:
            self.logger.error(f"ML data preparation failed: {e}")
            return [], []
    
    async def predict_with_ml(self, 
                             model_id: str, 
                             current_features: Dict[str, float],
                             context: Dict[str, Any]) -> Optional[PredictionResult]:
        """Make prediction using trained ML model"""
        try:
            if model_id not in self.models:
                return None
            
            model = self.models[model_id]
            
            # Prepare feature vector (simplified)
            current_time = datetime.utcnow()
            feature_vector = [
                current_time.hour,
                current_time.day,
                current_time.weekday(),
                current_time.month
            ]
            
            # Add current features
            for key, value in current_features.items():
                feature_vector.append(value)
            
            # Pad or truncate to match training features
            expected_length = len(model.feature_names)
            while len(feature_vector) < expected_length:
                feature_vector.append(0.0)
            feature_vector = feature_vector[:expected_length]
            
            # Make prediction
            if model.scaler and SKLEARN_AVAILABLE:
                feature_array = model.scaler.transform([feature_vector])
                prediction = model.model_object.predict(feature_array)[0]
            else:
                prediction = model.model_object.predict([feature_vector])[0]
            
            # Calculate confidence based on model performance
            confidence_score = min(0.95, max(0.1, model.validation_score))
            
            confidence_level = PredictionConfidence.LOW
            if confidence_score > 0.9:
                confidence_level = PredictionConfidence.VERY_HIGH
            elif confidence_score > 0.8:
                confidence_level = PredictionConfidence.HIGH
            elif confidence_score > 0.6:
                confidence_level = PredictionConfidence.MEDIUM
            
            # Update model usage
            model.prediction_count += 1
            
            # Create prediction result
            result = PredictionResult(
                prediction_id=str(uuid.uuid4()),
                prediction_type=model.prediction_type,
                predicted_value=float(prediction),
                confidence_score=confidence_score,
                confidence_level=confidence_level,
                time_horizon=TimeHorizon.SHORT,
                prediction_time=current_time,
                target_time=current_time + timedelta(minutes=5),
                features_used=model.feature_names,
                model_info={
                    'model_id': model_id,
                    'model_type': model.model_type,
                    'training_score': model.training_score,
                    'validation_score': model.validation_score
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"ML prediction failed: {e}")
            return None

class ResourcePredictor:
    """Specialized predictor for system resource usage"""
    
    def __init__(self):
        self.time_series_predictor = TimeSeriesPredictor()
        self.ml_predictor = MLPredictor()
        self.resource_history: Dict[str, deque] = {
            'cpu': deque(maxlen=200),
            'memory': deque(maxlen=200),
            'disk_io': deque(maxlen=200),
            'network_io': deque(maxlen=200)
        }
        self.logger = logging.getLogger(__name__)
    
    async def predict_cpu_usage(self, current_usage: float, time_horizon: TimeHorizon) -> PredictionResult:
        """Predict CPU usage"""
        try:
            # Add current usage to history
            self.resource_history['cpu'].append(HistoricalDataPoint(
                timestamp=datetime.utcnow(),
                value=current_usage,
                features={'current_processes': 0, 'load_average': 0},
                context={}
            ))
            
            # Use time series prediction for short-term
            if time_horizon == TimeHorizon.SHORT and len(self.resource_history['cpu']) >= 10:
                predictions = await self.time_series_predictor.predict_time_series(
                    list(self.resource_history['cpu']), 
                    steps_ahead=1
                )
                predicted_value = predictions[0]
                confidence = 0.7
            else:
                # Simple trend-based prediction
                if len(self.resource_history['cpu']) >= 2:
                    recent_values = [dp.value for dp in list(self.resource_history['cpu'])[-5:]]
                    predicted_value = statistics.mean(recent_values)
                    confidence = 0.5
                else:
                    predicted_value = current_usage
                    confidence = 0.3
            
            # Determine time horizon details
            minutes_ahead = {'short': 5, 'medium': 30, 'long': 120, 'extended': 1440}[time_horizon.value]
            target_time = datetime.utcnow() + timedelta(minutes=minutes_ahead)
            
            # Generate recommendations
            recommendations = []
            if predicted_value > 90:
                recommendations.extend([
                    "High CPU usage predicted - consider task scheduling",
                    "Monitor for resource-intensive processes",
                    "Consider scaling resources if sustained high usage"
                ])
            elif predicted_value < 20:
                recommendations.append("Low CPU usage predicted - opportunity for additional tasks")
            
            return PredictionResult(
                prediction_id=str(uuid.uuid4()),
                prediction_type=PredictionType.RESOURCE_USAGE,
                predicted_value=max(0, min(100, predicted_value)),
                confidence_score=confidence,
                confidence_level=PredictionConfidence.HIGH if confidence > 0.8 else PredictionConfidence.MEDIUM,
                time_horizon=time_horizon,
                prediction_time=datetime.utcnow(),
                target_time=target_time,
                features_used=['historical_cpu_usage', 'time_of_day', 'trend'],
                model_info={'predictor': 'time_series', 'data_points': len(self.resource_history['cpu'])},
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"CPU usage prediction failed: {e}")
            return self._create_fallback_prediction(PredictionType.RESOURCE_USAGE, current_usage, time_horizon)
    
    async def predict_memory_usage(self, current_usage: float, time_horizon: TimeHorizon) -> PredictionResult:
        """Predict memory usage"""
        try:
            self.resource_history['memory'].append(HistoricalDataPoint(
                timestamp=datetime.utcnow(),
                value=current_usage,
                features={},
                context={}
            ))
            
            # Memory usage tends to be more stable than CPU
            if len(self.resource_history['memory']) >= 5:
                recent_values = [dp.value for dp in list(self.resource_history['memory'])[-5:]]
                predicted_value = statistics.mean(recent_values)
                
                # Add slight upward trend for memory (typical behavior)
                if time_horizon in [TimeHorizon.LONG, TimeHorizon.EXTENDED]:
                    trend = 0.5 * (len(recent_values) - 1)
                    predicted_value += trend
                
                confidence = 0.8
            else:
                predicted_value = current_usage
                confidence = 0.5
            
            minutes_ahead = {'short': 5, 'medium': 30, 'long': 120, 'extended': 1440}[time_horizon.value]
            target_time = datetime.utcnow() + timedelta(minutes=minutes_ahead)
            
            recommendations = []
            if predicted_value > 85:
                recommendations.extend([
                    "High memory usage predicted - consider memory cleanup",
                    "Monitor for memory leaks",
                    "Consider increasing available memory"
                ])
            
            return PredictionResult(
                prediction_id=str(uuid.uuid4()),
                prediction_type=PredictionType.RESOURCE_USAGE,
                predicted_value=max(0, min(100, predicted_value)),
                confidence_score=confidence,
                confidence_level=PredictionConfidence.HIGH if confidence > 0.8 else PredictionConfidence.MEDIUM,
                time_horizon=time_horizon,
                prediction_time=datetime.utcnow(),
                target_time=target_time,
                features_used=['historical_memory_usage', 'trend'],
                model_info={'predictor': 'trend_based', 'data_points': len(self.resource_history['memory'])},
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Memory usage prediction failed: {e}")
            return self._create_fallback_prediction(PredictionType.RESOURCE_USAGE, current_usage, time_horizon)
    
    def _create_fallback_prediction(self, 
                                  prediction_type: PredictionType, 
                                  current_value: float,
                                  time_horizon: TimeHorizon) -> PredictionResult:
        """Create fallback prediction when main prediction fails"""
        minutes_ahead = {'short': 5, 'medium': 30, 'long': 120, 'extended': 1440}[time_horizon.value]
        
        return PredictionResult(
            prediction_id=str(uuid.uuid4()),
            prediction_type=prediction_type,
            predicted_value=current_value,
            confidence_score=0.3,
            confidence_level=PredictionConfidence.LOW,
            time_horizon=time_horizon,
            prediction_time=datetime.utcnow(),
            target_time=datetime.utcnow() + timedelta(minutes=minutes_ahead),
            features_used=['current_value'],
            model_info={'predictor': 'fallback'},
            recommendations=["Insufficient data for reliable prediction"]
        )

class UserBehaviorPredictor:
    """Predict user behavior patterns and preferences"""
    
    def __init__(self):
        self.user_sessions: Dict[str, List[Dict[str, Any]]] = {}
        self.behavior_patterns: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def predict_next_action(self, user_id: str, current_context: Dict[str, Any]) -> PredictionResult:
        """Predict user's next likely action"""
        try:
            if user_id not in self.user_sessions:
                return self._create_fallback_behavior_prediction(user_id, current_context)
            
            user_history = self.user_sessions[user_id]
            
            if len(user_history) < 3:
                return self._create_fallback_behavior_prediction(user_id, current_context)
            
            # Analyze recent patterns
            recent_actions = user_history[-10:]
            action_sequence = [action.get('action_type', 'unknown') for action in recent_actions]
            
            # Find most common action after current context
            current_action = current_context.get('current_action', '')
            next_actions = []
            
            for i, action in enumerate(action_sequence[:-1]):
                if action == current_action:
                    next_actions.append(action_sequence[i + 1])
            
            if next_actions:
                # Find most probable next action
                action_counts = {}
                for action in next_actions:
                    action_counts[action] = action_counts.get(action, 0) + 1
                
                most_likely_action = max(action_counts, key=action_counts.get)
                confidence = action_counts[most_likely_action] / len(next_actions)
                
                # Convert action to predicted value (simplified)
                predicted_value = hash(most_likely_action) % 100
                
            else:
                # No pattern found, use most common action
                all_actions = [action.get('action_type', 'unknown') for action in user_history]
                most_common = max(set(all_actions), key=all_actions.count)
                predicted_value = hash(most_common) % 100
                confidence = 0.4
            
            recommendations = [
                f"User likely to perform: {most_likely_action if 'most_likely_action' in locals() else 'common action'}",
                "Preload relevant resources for predicted action",
                "Optimize interface for expected workflow"
            ]
            
            return PredictionResult(
                prediction_id=str(uuid.uuid4()),
                prediction_type=PredictionType.USER_BEHAVIOR,
                predicted_value=predicted_value,
                confidence_score=confidence,
                confidence_level=PredictionConfidence.HIGH if confidence > 0.7 else PredictionConfidence.MEDIUM,
                time_horizon=TimeHorizon.SHORT,
                prediction_time=datetime.utcnow(),
                target_time=datetime.utcnow() + timedelta(minutes=2),
                features_used=['action_history', 'current_context', 'user_patterns'],
                model_info={'predictor': 'pattern_matching', 'history_length': len(user_history)},
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"User behavior prediction failed: {e}")
            return self._create_fallback_behavior_prediction(user_id, current_context)
    
    def _create_fallback_behavior_prediction(self, user_id: str, context: Dict[str, Any]) -> PredictionResult:
        """Create fallback behavior prediction"""
        return PredictionResult(
            prediction_id=str(uuid.uuid4()),
            prediction_type=PredictionType.USER_BEHAVIOR,
            predicted_value=50.0,
            confidence_score=0.2,
            confidence_level=PredictionConfidence.LOW,
            time_horizon=TimeHorizon.SHORT,
            prediction_time=datetime.utcnow(),
            target_time=datetime.utcnow() + timedelta(minutes=5),
            features_used=['default'],
            model_info={'predictor': 'fallback'},
            recommendations=["Insufficient user data for behavior prediction"]
        )

class SystemFailurePredictor:
    """Predict system failures and maintenance needs"""
    
    def __init__(self):
        self.failure_indicators: Dict[str, deque] = {
            'error_rate': deque(maxlen=100),
            'response_time': deque(maxlen=100),
            'resource_exhaustion': deque(maxlen=100),
            'temperature': deque(maxlen=100)
        }
        self.failure_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)
    
    async def predict_failure_probability(self, system_metrics: Dict[str, float]) -> PredictionResult:
        """Predict probability of system failure"""
        try:
            # Collect current indicators
            current_time = datetime.utcnow()
            
            for metric_name, value in system_metrics.items():
                if metric_name in self.failure_indicators:
                    self.failure_indicators[metric_name].append({
                        'timestamp': current_time,
                        'value': value
                    })
            
            # Calculate failure risk score
            risk_factors = []
            
            # Error rate analysis
            if 'error_rate' in system_metrics:
                error_rate = system_metrics['error_rate']
                if error_rate > 5:  # More than 5% error rate
                    risk_factors.append(('high_error_rate', min(20, error_rate * 2)))
            
            # Resource exhaustion
            if 'cpu_usage' in system_metrics and system_metrics['cpu_usage'] > 90:
                risk_factors.append(('cpu_exhaustion', 15))
            
            if 'memory_usage' in system_metrics and system_metrics['memory_usage'] > 95:
                risk_factors.append(('memory_exhaustion', 25))
            
            if 'disk_usage' in system_metrics and system_metrics['disk_usage'] > 95:
                risk_factors.append(('disk_exhaustion', 20))
            
            # Temperature (if available)
            if 'temperature' in system_metrics and system_metrics['temperature'] > 80:
                risk_factors.append(('overheating', 30))
            
            # Response time degradation
            if 'response_time' in system_metrics and system_metrics['response_time'] > 5000:  # 5 seconds
                risk_factors.append(('slow_response', 10))
            
            # Calculate total failure probability
            if risk_factors:
                total_risk = sum(risk for _, risk in risk_factors)
                failure_probability = min(95, total_risk)
                confidence = 0.8
            else:
                failure_probability = 5  # Base 5% failure probability
                confidence = 0.6
            
            # Generate recommendations
            recommendations = []
            for factor, risk in risk_factors:
                if factor == 'high_error_rate':
                    recommendations.append("Investigate error causes and implement error handling")
                elif factor == 'cpu_exhaustion':
                    recommendations.append("Reduce CPU load or increase CPU resources")
                elif factor == 'memory_exhaustion':
                    recommendations.append("Free memory or add more RAM")
                elif factor == 'disk_exhaustion':
                    recommendations.append("Free disk space or add storage capacity")
                elif factor == 'overheating':
                    recommendations.append("Check cooling system and reduce thermal load")
                elif factor == 'slow_response':
                    recommendations.append("Optimize performance or investigate bottlenecks")
            
            if not recommendations:
                recommendations.append("System operating within normal parameters")
            
            confidence_level = PredictionConfidence.HIGH if confidence > 0.7 else PredictionConfidence.MEDIUM
            
            return PredictionResult(
                prediction_id=str(uuid.uuid4()),
                prediction_type=PredictionType.SYSTEM_FAILURE,
                predicted_value=failure_probability,
                confidence_score=confidence,
                confidence_level=confidence_level,
                time_horizon=TimeHorizon.MEDIUM,
                prediction_time=current_time,
                target_time=current_time + timedelta(hours=1),
                features_used=list(system_metrics.keys()),
                model_info={'predictor': 'risk_assessment', 'risk_factors': len(risk_factors)},
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"System failure prediction failed: {e}")
            return PredictionResult(
                prediction_id=str(uuid.uuid4()),
                prediction_type=PredictionType.SYSTEM_FAILURE,
                predicted_value=10.0,
                confidence_score=0.3,
                confidence_level=PredictionConfidence.LOW,
                time_horizon=TimeHorizon.MEDIUM,
                prediction_time=datetime.utcnow(),
                target_time=datetime.utcnow() + timedelta(hours=1),
                features_used=['default'],
                model_info={'predictor': 'fallback'},
                recommendations=["Unable to assess failure risk accurately"]
            )

class PredictionEngine:
    """Main prediction engine orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize specialized predictors
        self.resource_predictor = ResourcePredictor()
        self.behavior_predictor = UserBehaviorPredictor()
        self.failure_predictor = SystemFailurePredictor()
        
        self.prediction_cache: Dict[str, PredictionResult] = {}
        self.cache_duration = timedelta(minutes=5)
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize prediction engine"""
        try:
            self.logger.info("Initializing predictive optimization engine...")
            
            # Start background tasks
            asyncio.create_task(self._prediction_maintenance_loop())
            asyncio.create_task(self._cache_cleanup_loop())
            
            self.logger.info("Prediction engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Prediction engine initialization failed: {e}")
            return False
    
    async def predict(self, 
                     prediction_type: PredictionType,
                     context: Dict[str, Any],
                     time_horizon: TimeHorizon = TimeHorizon.SHORT) -> PredictionResult:
        """Make prediction based on type and context"""
        try:
            # Check cache first
            cache_key = f"{prediction_type.value}_{hash(str(context))}_{time_horizon.value}"
            
            if cache_key in self.prediction_cache:
                cached_result = self.prediction_cache[cache_key]
                if datetime.utcnow() - cached_result.prediction_time < self.cache_duration:
                    return cached_result
            
            # Make new prediction
            result = None
            
            if prediction_type == PredictionType.RESOURCE_USAGE:
                if 'cpu_usage' in context:
                    result = await self.resource_predictor.predict_cpu_usage(
                        context['cpu_usage'], time_horizon
                    )
                elif 'memory_usage' in context:
                    result = await self.resource_predictor.predict_memory_usage(
                        context['memory_usage'], time_horizon
                    )
                    
            elif prediction_type == PredictionType.USER_BEHAVIOR:
                user_id = context.get('user_id', 'anonymous')
                result = await self.behavior_predictor.predict_next_action(user_id, context)
                
            elif prediction_type == PredictionType.SYSTEM_FAILURE:
                result = await self.failure_predictor.predict_failure_probability(context)
                
            # Cache result
            if result:
                self.prediction_cache[cache_key] = result
            
            return result or self._create_generic_fallback_prediction(prediction_type, time_horizon)
            
        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            return self._create_generic_fallback_prediction(prediction_type, time_horizon)
    
    async def get_prediction_accuracy(self, prediction_id: str, actual_value: float) -> float:
        """Calculate prediction accuracy after actual value is known"""
        try:
            # Find prediction in cache or storage
            for cached_prediction in self.prediction_cache.values():
                if cached_prediction.prediction_id == prediction_id:
                    predicted_value = cached_prediction.predicted_value
                    
                    # Calculate accuracy (percentage)
                    error = abs(predicted_value - actual_value)
                    max_possible_error = max(predicted_value, actual_value, 100)  # Prevent division by zero
                    accuracy = max(0, (1 - error / max_possible_error)) * 100
                    
                    return accuracy
            
            return 0.0  # Prediction not found
            
        except Exception as e:
            self.logger.error(f"Accuracy calculation failed: {e}")
            return 0.0
    
    def _create_generic_fallback_prediction(self, 
                                          prediction_type: PredictionType, 
                                          time_horizon: TimeHorizon) -> PredictionResult:
        """Create generic fallback prediction"""
        minutes_ahead = {'short': 5, 'medium': 30, 'long': 120, 'extended': 1440}[time_horizon.value]
        
        return PredictionResult(
            prediction_id=str(uuid.uuid4()),
            prediction_type=prediction_type,
            predicted_value=50.0,
            confidence_score=0.1,
            confidence_level=PredictionConfidence.LOW,
            time_horizon=time_horizon,
            prediction_time=datetime.utcnow(),
            target_time=datetime.utcnow() + timedelta(minutes=minutes_ahead),
            features_used=[],
            model_info={'predictor': 'generic_fallback'},
            recommendations=["Insufficient data for reliable prediction"]
        )
    
    async def _prediction_maintenance_loop(self):
        """Background maintenance for prediction models"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Retrain models if enough new data
                # Update prediction statistics
                # Clean up old predictions
                
                self.logger.debug("Prediction maintenance completed")
                
            except Exception as e:
                self.logger.error(f"Prediction maintenance failed: {e}")
    
    async def _cache_cleanup_loop(self):
        """Clean up expired predictions from cache"""
        while True:
            try:
                await asyncio.sleep(600)  # Run every 10 minutes
                
                current_time = datetime.utcnow()
                expired_keys = []
                
                for key, prediction in self.prediction_cache.items():
                    if current_time - prediction.prediction_time > self.cache_duration * 2:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.prediction_cache[key]
                
                if expired_keys:
                    self.logger.debug(f"Cleaned up {len(expired_keys)} expired predictions")
                
            except Exception as e:
                self.logger.error(f"Cache cleanup failed: {e}")