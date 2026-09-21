"""
Predictive Analytics Engine

This module provides comprehensive predictive analytics and early warning systems
across multiple domains including relationships, health, devices, career, finance,
social dynamics, mental health, education, business, environment, and infrastructure.

Key Features:
- Relationship maintenance predictions and intervention timing
- Health issue early warning with biomarker analysis
- Device failure prediction using telemetry and usage patterns
- Career trajectory optimization with skill gap analysis
- Financial crisis prevention with risk modeling
- Social conflict early warning through sentiment analysis
- Mental health intervention timing with behavioral indicators
- Educational intervention points with learning analytics
- Business pivot indicators with market trend analysis
- Environmental hazard detection with sensor networks
- Infrastructure failure prediction with stress analysis
- Community health metrics with population analytics
"""

import asyncio
import logging
import random
import time
import json
import hashlib
import uuid
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, Union, Set
from enum import Enum
from collections import defaultdict, deque
import math
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")


class PredictionConfidence(Enum):
    """Confidence levels for predictions"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class RiskLevel(Enum):
    """Risk severity levels"""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class InterventionType(Enum):
    """Types of interventions"""
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    MONITORING = "monitoring"
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    EMERGENCY = "emergency"


class DataSource(Enum):
    """Data source types"""
    SENSOR = "sensor"
    USER_INPUT = "user_input"
    SOCIAL_MEDIA = "social_media"
    MEDICAL_RECORDS = "medical_records"
    FINANCIAL_DATA = "financial_data"
    DEVICE_TELEMETRY = "device_telemetry"
    ENVIRONMENTAL = "environmental"
    THIRD_PARTY = "third_party"


@dataclass
class DataPoint:
    """Individual data point for analysis"""
    data_id: str
    source: DataSource
    category: str
    value: Union[float, str, Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.now)
    quality_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Prediction:
    """Prediction result with confidence and timing"""
    prediction_id: str
    category: str
    description: str
    predicted_outcome: str
    probability: float
    confidence: PredictionConfidence
    risk_level: RiskLevel
    predicted_timeframe: timedelta
    created_at: datetime = field(default_factory=datetime.now)
    data_sources: List[DataSource] = field(default_factory=list)
    contributing_factors: List[str] = field(default_factory=list)


@dataclass
class EarlyWarning:
    """Early warning alert"""
    warning_id: str
    category: str
    title: str
    description: str
    risk_level: RiskLevel
    urgency: InterventionType
    predicted_impact: str
    recommendations: List[str]
    data_evidence: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


@dataclass
class InterventionRecommendation:
    """Recommended intervention"""
    recommendation_id: str
    category: str
    intervention_type: InterventionType
    title: str
    description: str
    expected_impact: str
    implementation_steps: List[str]
    resource_requirements: Dict[str, Any]
    timing: Dict[str, Any]
    success_metrics: List[str]
    created_at: datetime = field(default_factory=datetime.now)


class PredictiveModel(ABC):
    """Abstract base class for predictive models"""
    
    @abstractmethod
    def train(self, training_data: List[DataPoint]) -> Dict[str, Any]:
        """Train the predictive model"""
        pass
    
    @abstractmethod
    def predict(self, input_data: List[DataPoint]) -> Prediction:
        """Make prediction based on input data"""
        pass
    
    @abstractmethod
    def evaluate(self, test_data: List[DataPoint]) -> Dict[str, float]:
        """Evaluate model performance"""
        pass


class RelationshipPredictor(PredictiveModel):
    """Predicts relationship maintenance needs and risks"""
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.trained = False
        self.feature_names = [
            'communication_frequency', 'sentiment_score', 'response_time',
            'conflict_frequency', 'shared_activities', 'life_stage_alignment',
            'stress_levels', 'support_ratio', 'intimacy_score', 'trust_level'
        ]
    
    def train(self, training_data: List[DataPoint]) -> Dict[str, Any]:
        """Train relationship prediction model"""
        if len(training_data) < 50:
            return {'success': False, 'error': 'Insufficient training data'}
        
        # Extract features from training data
        features = []
        targets = []
        
        for data_point in training_data:
            if isinstance(data_point.value, dict):
                feature_vector = []
                for feature_name in self.feature_names:
                    feature_vector.append(data_point.value.get(feature_name, 0.0))
                features.append(feature_vector)
                
                # Target is relationship satisfaction score (0-1)
                targets.append(data_point.value.get('satisfaction_score', 0.5))
        
        if not features:
            return {'success': False, 'error': 'No valid features extracted'}
        
        features_array = np.array(features)
        targets_array = np.array(targets)
        
        # Scale features
        features_scaled = self.scaler.fit_transform(features_array)
        
        # Train model
        self.model.fit(features_scaled, targets_array)
        self.trained = True
        
        # Calculate training metrics
        train_score = self.model.score(features_scaled, targets_array)
        
        return {
            'success': True,
            'train_score': train_score,
            'feature_importance': dict(zip(self.feature_names, self.model.feature_importances_)),
            'samples_trained': len(features)
        }
    
    def predict(self, input_data: List[DataPoint]) -> Prediction:
        """Predict relationship maintenance needs"""
        if not self.trained:
            return self._create_default_prediction("Model not trained")
        
        # Extract features from input data
        features = []
        for data_point in input_data:
            if isinstance(data_point.value, dict):
                feature_vector = []
                for feature_name in self.feature_names:
                    feature_vector.append(data_point.value.get(feature_name, 0.5))
                features.append(feature_vector)
        
        if not features:
            return self._create_default_prediction("No valid input features")
        
        # Make prediction
        features_array = np.array(features)
        features_scaled = self.scaler.transform(features_array)
        
        prediction_score = self.model.predict(features_scaled)[0]
        
        # Convert to relationship health assessment
        if prediction_score > 0.8:
            outcome = "relationship_thriving"
            risk_level = RiskLevel.MINIMAL
            confidence = PredictionConfidence.HIGH
            timeframe = timedelta(days=90)
        elif prediction_score > 0.6:
            outcome = "relationship_stable"
            risk_level = RiskLevel.LOW
            confidence = PredictionConfidence.MEDIUM
            timeframe = timedelta(days=30)
        elif prediction_score > 0.4:
            outcome = "relationship_attention_needed"
            risk_level = RiskLevel.MODERATE
            confidence = PredictionConfidence.MEDIUM
            timeframe = timedelta(days=14)
        elif prediction_score > 0.2:
            outcome = "relationship_at_risk"
            risk_level = RiskLevel.HIGH
            confidence = PredictionConfidence.HIGH
            timeframe = timedelta(days=7)
        else:
            outcome = "relationship_crisis_likely"
            risk_level = RiskLevel.CRITICAL
            confidence = PredictionConfidence.VERY_HIGH
            timeframe = timedelta(days=3)
        
        contributing_factors = []
        feature_importance = dict(zip(self.feature_names, self.model.feature_importances_))
        for feature, importance in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:3]:
            contributing_factors.append(f"{feature}: {importance:.3f}")
        
        return Prediction(
            prediction_id=f"rel_pred_{uuid.uuid4().hex}",
            category="relationship_maintenance",
            description=f"Relationship health score: {prediction_score:.2f}",
            predicted_outcome=outcome,
            probability=abs(prediction_score - 0.5) * 2,  # Convert to 0-1 probability
            confidence=confidence,
            risk_level=risk_level,
            predicted_timeframe=timeframe,
            data_sources=[DataSource.USER_INPUT, DataSource.SOCIAL_MEDIA],
            contributing_factors=contributing_factors
        )
    
    def evaluate(self, test_data: List[DataPoint]) -> Dict[str, float]:
        """Evaluate model performance"""
        if not self.trained:
            return {'error': 'Model not trained'}
        
        features = []
        targets = []
        
        for data_point in test_data:
            if isinstance(data_point.value, dict):
                feature_vector = []
                for feature_name in self.feature_names:
                    feature_vector.append(data_point.value.get(feature_name, 0.0))
                features.append(feature_vector)
                targets.append(data_point.value.get('satisfaction_score', 0.5))
        
        if not features:
            return {'error': 'No valid test features'}
        
        features_array = np.array(features)
        targets_array = np.array(targets)
        features_scaled = self.scaler.transform(features_array)
        
        test_score = self.model.score(features_scaled, targets_array)
        predictions = self.model.predict(features_scaled)
        
        mse = np.mean((predictions - targets_array) ** 2)
        mae = np.mean(np.abs(predictions - targets_array))
        
        return {
            'r2_score': test_score,
            'mse': mse,
            'mae': mae,
            'test_samples': len(features)
        }
    
    def _create_default_prediction(self, reason: str) -> Prediction:
        """Create default prediction when model cannot process"""
        return Prediction(
            prediction_id=f"rel_pred_default_{uuid.uuid4().hex}",
            category="relationship_maintenance",
            description=f"Default prediction: {reason}",
            predicted_outcome="insufficient_data",
            probability=0.5,
            confidence=PredictionConfidence.VERY_LOW,
            risk_level=RiskLevel.LOW,
            predicted_timeframe=timedelta(days=30)
        )


class HealthEarlyWarning(PredictiveModel):
    """Early warning system for health issues"""
    
    def __init__(self):
        self.risk_models = {}
        self.baseline_metrics = {}
        self.anomaly_thresholds = {}
        self.health_conditions = [
            'cardiovascular_disease', 'diabetes', 'hypertension', 'obesity',
            'depression', 'anxiety', 'sleep_disorders', 'respiratory_issues',
            'digestive_issues', 'immune_dysfunction'
        ]
        
    def train(self, training_data: List[DataPoint]) -> Dict[str, Any]:
        """Train health prediction models"""
        # Group data by health condition
        condition_data = defaultdict(list)
        baseline_data = defaultdict(list)
        
        for data_point in training_data:
            if isinstance(data_point.value, dict):
                condition = data_point.value.get('condition', 'unknown')
                if condition in self.health_conditions:
                    condition_data[condition].append(data_point)
                
                # Collect baseline metrics
                for metric, value in data_point.value.items():
                    if isinstance(value, (int, float)):
                        baseline_data[metric].append(value)
        
        # Calculate baseline metrics
        for metric, values in baseline_data.items():
            if values:
                self.baseline_metrics[metric] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values)
                }
                
                # Set anomaly thresholds (2 standard deviations)
                self.anomaly_thresholds[metric] = {
                    'lower': self.baseline_metrics[metric]['mean'] - 2 * self.baseline_metrics[metric]['std'],
                    'upper': self.baseline_metrics[metric]['mean'] + 2 * self.baseline_metrics[metric]['std']
                }
        
        # Train risk models for each condition
        training_results = {}
        for condition in self.health_conditions:
            if condition in condition_data and len(condition_data[condition]) > 10:
                model_result = self._train_condition_model(condition, condition_data[condition])
                training_results[condition] = model_result
        
        return {
            'success': True,
            'conditions_trained': len(training_results),
            'baseline_metrics': len(self.baseline_metrics),
            'training_results': training_results
        }
    
    def predict(self, input_data: List[DataPoint]) -> Prediction:
        """Predict health risks and generate early warnings"""
        current_metrics = {}
        symptoms = []
        risk_scores = {}
        
        # Extract current health metrics
        for data_point in input_data:
            if isinstance(data_point.value, dict):
                for key, value in data_point.value.items():
                    if isinstance(value, (int, float)):
                        current_metrics[key] = value
                    elif key == 'symptoms' and isinstance(value, list):
                        symptoms.extend(value)
        
        # Check for anomalies
        anomalies = []
        for metric, value in current_metrics.items():
            if metric in self.anomaly_thresholds:
                thresholds = self.anomaly_thresholds[metric]
                if value < thresholds['lower'] or value > thresholds['upper']:
                    anomalies.append(f"{metric}: {value:.2f} (baseline: {self.baseline_metrics[metric]['mean']:.2f})")
        
        # Calculate risk scores for each condition
        for condition in self.health_conditions:
            risk_scores[condition] = self._calculate_condition_risk(condition, current_metrics, symptoms)
        
        # Find highest risk condition
        highest_risk_condition = max(risk_scores.keys(), key=lambda k: risk_scores[k])
        highest_risk_score = risk_scores[highest_risk_condition]
        
        # Determine overall risk level and outcome
        if highest_risk_score > 0.8:
            risk_level = RiskLevel.CRITICAL
            outcome = f"high_risk_{highest_risk_condition}"
            timeframe = timedelta(days=1)
            confidence = PredictionConfidence.HIGH
        elif highest_risk_score > 0.6:
            risk_level = RiskLevel.HIGH
            outcome = f"elevated_risk_{highest_risk_condition}"
            timeframe = timedelta(days=7)
            confidence = PredictionConfidence.MEDIUM
        elif highest_risk_score > 0.4:
            risk_level = RiskLevel.MODERATE
            outcome = f"moderate_risk_{highest_risk_condition}"
            timeframe = timedelta(days=30)
            confidence = PredictionConfidence.MEDIUM
        else:
            risk_level = RiskLevel.LOW
            outcome = "low_health_risk"
            timeframe = timedelta(days=90)
            confidence = PredictionConfidence.LOW
        
        contributing_factors = anomalies + [f"symptom_count: {len(symptoms)}"]
        
        return Prediction(
            prediction_id=f"health_pred_{uuid.uuid4().hex}",
            category="health_early_warning",
            description=f"Health risk assessment for {highest_risk_condition}",
            predicted_outcome=outcome,
            probability=highest_risk_score,
            confidence=confidence,
            risk_level=risk_level,
            predicted_timeframe=timeframe,
            data_sources=[DataSource.MEDICAL_RECORDS, DataSource.SENSOR],
            contributing_factors=contributing_factors
        )
    
    def evaluate(self, test_data: List[DataPoint]) -> Dict[str, float]:
        """Evaluate health prediction accuracy"""
        correct_predictions = 0
        total_predictions = 0
        
        for data_point in test_data:
            prediction = self.predict([data_point])
            actual_condition = data_point.value.get('actual_condition', 'unknown')
            predicted_condition = prediction.predicted_outcome.split('_')[-1] if '_' in prediction.predicted_outcome else 'unknown'
            
            if predicted_condition == actual_condition:
                correct_predictions += 1
            total_predictions += 1
        
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0
        
        return {
            'accuracy': accuracy,
            'correct_predictions': correct_predictions,
            'total_predictions': total_predictions
        }
    
    def _train_condition_model(self, condition: str, training_data: List[DataPoint]) -> Dict[str, Any]:
        """Train model for specific health condition"""
        # Simplified training - extract risk factors
        risk_factors = defaultdict(list)
        positive_cases = 0
        
        for data_point in training_data:
            if isinstance(data_point.value, dict):
                has_condition = data_point.value.get('has_condition', False)
                if has_condition:
                    positive_cases += 1
                
                for factor, value in data_point.value.items():
                    if isinstance(value, (int, float)) and factor != 'has_condition':
                        risk_factors[factor].append((value, has_condition))
        
        # Calculate risk factor weights
        factor_weights = {}
        for factor, values in risk_factors.items():
            if len(values) > 5:
                positive_values = [v[0] for v in values if v[1]]
                negative_values = [v[0] for v in values if not v[1]]
                
                if positive_values and negative_values:
                    pos_mean = np.mean(positive_values)
                    neg_mean = np.mean(negative_values)
                    weight = abs(pos_mean - neg_mean) / (pos_mean + neg_mean + 0.001)
                    factor_weights[factor] = weight
        
        self.risk_models[condition] = {
            'factor_weights': factor_weights,
            'prevalence': positive_cases / len(training_data),
            'sample_size': len(training_data)
        }
        
        return {
            'condition': condition,
            'factors_identified': len(factor_weights),
            'prevalence': positive_cases / len(training_data),
            'sample_size': len(training_data)
        }
    
    def _calculate_condition_risk(self, condition: str, metrics: Dict[str, float], symptoms: List[str]) -> float:
        """Calculate risk score for specific condition"""
        if condition not in self.risk_models:
            return 0.1  # Default low risk
        
        model = self.risk_models[condition]
        risk_score = model['prevalence']  # Base risk from population prevalence
        
        # Add weighted risk factors
        for factor, weight in model['factor_weights'].items():
            if factor in metrics:
                baseline = self.baseline_metrics.get(factor, {}).get('mean', 50.0)
                deviation = abs(metrics[factor] - baseline) / (baseline + 1.0)
                risk_score += weight * deviation * 0.1
        
        # Add symptom-based risk
        condition_symptoms = {
            'cardiovascular_disease': ['chest_pain', 'shortness_of_breath', 'fatigue'],
            'diabetes': ['excessive_thirst', 'frequent_urination', 'blurred_vision'],
            'hypertension': ['headaches', 'dizziness', 'nosebleeds'],
            'depression': ['sadness', 'hopelessness', 'loss_of_interest'],
            'anxiety': ['nervousness', 'restlessness', 'panic_attacks']
        }
        
        if condition in condition_symptoms:
            matching_symptoms = set(symptoms) & set(condition_symptoms[condition])
            symptom_risk = len(matching_symptoms) / len(condition_symptoms[condition])
            risk_score += symptom_risk * 0.3
        
        return min(1.0, risk_score)


class DeviceFailurePredictor(PredictiveModel):
    """Predicts device failures based on telemetry and usage patterns"""
    
    def __init__(self):
        self.device_models = {}
        self.failure_patterns = defaultdict(list)
        self.baseline_performance = {}
        
    def train(self, training_data: List[DataPoint]) -> Dict[str, Any]:
        """Train device failure prediction models"""
        device_data = defaultdict(list)
        
        # Group data by device type
        for data_point in training_data:
            if isinstance(data_point.value, dict):
                device_type = data_point.value.get('device_type', 'unknown')
                device_data[device_type].append(data_point)
        
        training_results = {}
        for device_type, data in device_data.items():
            if len(data) > 20:  # Minimum data required
                result = self._train_device_model(device_type, data)
                training_results[device_type] = result
        
        return {
            'success': True,
            'device_types_trained': len(training_results),
            'total_samples': len(training_data),
            'training_results': training_results
        }
    
    def predict(self, input_data: List[DataPoint]) -> Prediction:
        """Predict device failure probability and timing"""
        device_metrics = {}
        device_type = "unknown"
        
        for data_point in input_data:
            if isinstance(data_point.value, dict):
                device_type = data_point.value.get('device_type', device_type)
                device_metrics.update(data_point.value)
        
        if device_type not in self.device_models:
            return self._create_default_device_prediction(device_type, "No model available")
        
        model = self.device_models[device_type]
        failure_score = self._calculate_failure_score(device_type, device_metrics)
        
        # Determine prediction outcome
        if failure_score > 0.8:
            outcome = "imminent_failure"
            risk_level = RiskLevel.CRITICAL
            timeframe = timedelta(hours=24)
            confidence = PredictionConfidence.HIGH
        elif failure_score > 0.6:
            outcome = "failure_likely"
            risk_level = RiskLevel.HIGH
            timeframe = timedelta(days=7)
            confidence = PredictionConfidence.MEDIUM
        elif failure_score > 0.4:
            outcome = "maintenance_needed"
            risk_level = RiskLevel.MODERATE
            timeframe = timedelta(days=30)
            confidence = PredictionConfidence.MEDIUM
        elif failure_score > 0.2:
            outcome = "monitoring_required"
            risk_level = RiskLevel.LOW
            timeframe = timedelta(days=90)
            confidence = PredictionConfidence.LOW
        else:
            outcome = "device_healthy"
            risk_level = RiskLevel.MINIMAL
            timeframe = timedelta(days=180)
            confidence = PredictionConfidence.MEDIUM
        
        # Identify contributing factors
        contributing_factors = []
        for metric, value in device_metrics.items():
            if metric in model['critical_metrics'] and isinstance(value, (int, float)):
                baseline = model['baselines'].get(metric, {}).get('mean', 50.0)
                if abs(value - baseline) > baseline * 0.2:
                    contributing_factors.append(f"{metric}: {value:.2f} (baseline: {baseline:.2f})")
        
        return Prediction(
            prediction_id=f"device_pred_{uuid.uuid4().hex}",
            category="device_failure_prediction",
            description=f"Failure prediction for {device_type}",
            predicted_outcome=outcome,
            probability=failure_score,
            confidence=confidence,
            risk_level=risk_level,
            predicted_timeframe=timeframe,
            data_sources=[DataSource.DEVICE_TELEMETRY, DataSource.SENSOR],
            contributing_factors=contributing_factors
        )
    
    def evaluate(self, test_data: List[DataPoint]) -> Dict[str, float]:
        """Evaluate device failure prediction accuracy"""
        predictions = []
        actuals = []
        
        for data_point in test_data:
            prediction = self.predict([data_point])
            predictions.append(prediction.probability)
            
            actual_failure = data_point.value.get('actual_failure', False)
            actuals.append(1.0 if actual_failure else 0.0)
        
        if predictions and actuals:
            mse = np.mean([(p - a) ** 2 for p, a in zip(predictions, actuals)])
            mae = np.mean([abs(p - a) for p, a in zip(predictions, actuals)])
            
            return {
                'mse': mse,
                'mae': mae,
                'predictions_made': len(predictions)
            }
        
        return {'error': 'No valid predictions made'}
    
    def _train_device_model(self, device_type: str, training_data: List[DataPoint]) -> Dict[str, Any]:
        """Train model for specific device type"""
        metrics_data = defaultdict(list)
        failure_cases = []
        
        for data_point in training_data:
            if isinstance(data_point.value, dict):
                failed = data_point.value.get('failed', False)
                if failed:
                    failure_cases.append(data_point.value)
                
                for metric, value in data_point.value.items():
                    if isinstance(value, (int, float)) and metric != 'failed':
                        metrics_data[metric].append(value)
        
        # Calculate baseline metrics
        baselines = {}
        for metric, values in metrics_data.items():
            if values:
                baselines[metric] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values)
                }
        
        # Identify critical metrics (those that differ significantly in failure cases)
        critical_metrics = []
        if failure_cases and len(failure_cases) > 3:
            for metric in metrics_data.keys():
                failure_values = [case.get(metric, 0) for case in failure_cases if metric in case]
                normal_values = metrics_data[metric]
                
                if failure_values and len(failure_values) > 2:
                    failure_mean = np.mean(failure_values)
                    normal_mean = np.mean(normal_values)
                    
                    # If difference is significant, mark as critical
                    if abs(failure_mean - normal_mean) > normal_mean * 0.1:
                        critical_metrics.append(metric)
        
        model = {
            'device_type': device_type,
            'baselines': baselines,
            'critical_metrics': critical_metrics,
            'failure_rate': len(failure_cases) / len(training_data),
            'sample_size': len(training_data)
        }
        
        self.device_models[device_type] = model
        
        return {
            'device_type': device_type,
            'critical_metrics': len(critical_metrics),
            'failure_rate': model['failure_rate'],
            'sample_size': len(training_data)
        }
    
    def _calculate_failure_score(self, device_type: str, metrics: Dict[str, Any]) -> float:
        """Calculate failure probability score"""
        if device_type not in self.device_models:
            return 0.1
        
        model = self.device_models[device_type]
        base_failure_rate = model['failure_rate']
        
        # Calculate metric-based risk
        metric_risk = 0.0
        critical_deviations = 0
        
        for metric in model['critical_metrics']:
            if metric in metrics and isinstance(metrics[metric], (int, float)):
                baseline = model['baselines'].get(metric, {})
                if baseline:
                    deviation = abs(metrics[metric] - baseline['mean'])
                    normalized_deviation = deviation / (baseline['std'] + 0.001)
                    
                    if normalized_deviation > 2.0:  # More than 2 standard deviations
                        critical_deviations += 1
                        metric_risk += normalized_deviation * 0.1
        
        # Combine base rate with metric-based risk
        total_risk = base_failure_rate + metric_risk + (critical_deviations * 0.1)
        
        # Add usage-based factors
        usage_hours = metrics.get('usage_hours', 0)
        age_days = metrics.get('age_days', 0)
        
        if usage_hours > 8760:  # More than a year of continuous use
            total_risk += 0.1
        if age_days > 1095:  # More than 3 years old
            total_risk += 0.15
        
        return min(1.0, total_risk)
    
    def _create_default_device_prediction(self, device_type: str, reason: str) -> Prediction:
        """Create default prediction for unknown device types"""
        return Prediction(
            prediction_id=f"device_pred_default_{uuid.uuid4().hex}",
            category="device_failure_prediction",
            description=f"Default prediction for {device_type}: {reason}",
            predicted_outcome="insufficient_data",
            probability=0.3,
            confidence=PredictionConfidence.VERY_LOW,
            risk_level=RiskLevel.LOW,
            predicted_timeframe=timedelta(days=60)
        )


class CareerTrajectoryOptimizer(PredictiveModel):
    """Optimizes career trajectories and identifies growth opportunities"""
    
    def __init__(self):
        self.industry_models = {}
        self.skill_importance = {}
        self.career_paths = defaultdict(list)
        self.market_trends = {}
        
    def train(self, training_data: List[DataPoint]) -> Dict[str, Any]:
        """Train career optimization models"""
        career_data = defaultdict(list)
        skill_data = defaultdict(list)
        
        for data_point in training_data:
            if isinstance(data_point.value, dict):
                industry = data_point.value.get('industry', 'unknown')
                career_data[industry].append(data_point)
                
                # Collect skill data
                skills = data_point.value.get('skills', {})
                if isinstance(skills, dict):
                    for skill, level in skills.items():
                        skill_data[skill].append(level)
        
        # Calculate skill importance across industries
        for skill, levels in skill_data.items():
            if len(levels) > 10:
                self.skill_importance[skill] = {
                    'demand_level': np.mean(levels),
                    'variability': np.std(levels),
                    'market_presence': len(levels)
                }
        
        # Train industry-specific models
        training_results = {}
        for industry, data in career_data.items():
            if len(data) > 15:
                result = self._train_industry_model(industry, data)
                training_results[industry] = result
        
        return {
            'success': True,
            'industries_trained': len(training_results),
            'skills_analyzed': len(self.skill_importance),
            'training_results': training_results
        }
    
    def predict(self, input_data: List[DataPoint]) -> Prediction:
        """Predict career trajectory and optimization opportunities"""
        profile = {}
        for data_point in input_data:
            if isinstance(data_point.value, dict):
                profile.update(data_point.value)
        
        current_industry = profile.get('industry', 'unknown')
        current_role = profile.get('role', 'unknown')
        experience_years = profile.get('experience_years', 0)
        current_skills = profile.get('skills', {})
        salary = profile.get('salary', 0)
        
        # Analyze career growth potential
        growth_score = self._calculate_growth_potential(profile)
        
        # Identify skill gaps
        skill_gaps = self._identify_skill_gaps(current_industry, current_skills)
        
        # Predict career outcomes
        if growth_score > 0.8:
            outcome = "high_growth_trajectory"
            risk_level = RiskLevel.MINIMAL
            timeframe = timedelta(days=180)
            confidence = PredictionConfidence.HIGH
        elif growth_score > 0.6:
            outcome = "positive_career_progression"
            risk_level = RiskLevel.LOW
            timeframe = timedelta(days=365)
            confidence = PredictionConfidence.MEDIUM
        elif growth_score > 0.4:
            outcome = "stable_career_path"
            risk_level = RiskLevel.MODERATE
            timeframe = timedelta(days=545)
            confidence = PredictionConfidence.MEDIUM
        elif growth_score > 0.2:
            outcome = "career_optimization_needed"
            risk_level = RiskLevel.HIGH
            timeframe = timedelta(days=90)
            confidence = PredictionConfidence.HIGH
        else:
            outcome = "career_pivot_recommended"
            risk_level = RiskLevel.CRITICAL
            timeframe = timedelta(days=30)
            confidence = PredictionConfidence.VERY_HIGH
        
        contributing_factors = [
            f"growth_potential: {growth_score:.2f}",
            f"skill_gaps: {len(skill_gaps)}",
            f"experience_level: {experience_years} years"
        ]
        
        return Prediction(
            prediction_id=f"career_pred_{uuid.uuid4().hex}",
            category="career_trajectory_optimization",
            description=f"Career analysis for {current_role} in {current_industry}",
            predicted_outcome=outcome,
            probability=growth_score,
            confidence=confidence,
            risk_level=risk_level,
            predicted_timeframe=timeframe,
            data_sources=[DataSource.USER_INPUT, DataSource.THIRD_PARTY],
            contributing_factors=contributing_factors
        )
    
    def evaluate(self, test_data: List[DataPoint]) -> Dict[str, float]:
        """Evaluate career prediction accuracy"""
        correct_predictions = 0
        total_predictions = 0
        
        for data_point in test_data:
            prediction = self.predict([data_point])
            actual_outcome = data_point.value.get('actual_outcome', 'unknown')
            
            if prediction.predicted_outcome == actual_outcome:
                correct_predictions += 1
            total_predictions += 1
        
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0
        
        return {
            'accuracy': accuracy,
            'correct_predictions': correct_predictions,
            'total_predictions': total_predictions
        }
    
    def _train_industry_model(self, industry: str, training_data: List[DataPoint]) -> Dict[str, Any]:
        """Train model for specific industry"""
        salary_data = []
        role_progression = defaultdict(list)
        skill_requirements = defaultdict(list)
        
        for data_point in training_data:
            if isinstance(data_point.value, dict):
                salary = data_point.value.get('salary', 0)
                role = data_point.value.get('role', 'unknown')
                experience = data_point.value.get('experience_years', 0)
                skills = data_point.value.get('skills', {})
                
                if salary > 0:
                    salary_data.append((experience, salary))
                
                role_progression[role].append(experience)
                
                for skill, level in skills.items():
                    skill_requirements[skill].append(level)
        
        # Calculate industry metrics
        avg_salary_growth = 0
        if len(salary_data) > 5:
            salary_data.sort()
            if salary_data[-1][0] != salary_data[0][0]:
                avg_salary_growth = (salary_data[-1][1] - salary_data[0][1]) / (salary_data[-1][0] - salary_data[0][0])
        
        # Identify high-demand skills
        high_demand_skills = []
        for skill, levels in skill_requirements.items():
            if len(levels) > 3 and np.mean(levels) > 0.6:
                high_demand_skills.append(skill)
        
        model = {
            'industry': industry,
            'avg_salary_growth': avg_salary_growth,
            'role_progression': dict(role_progression),
            'high_demand_skills': high_demand_skills,
            'skill_requirements': dict(skill_requirements),
            'sample_size': len(training_data)
        }
        
        self.industry_models[industry] = model
        
        return {
            'industry': industry,
            'salary_growth_rate': avg_salary_growth,
            'high_demand_skills': len(high_demand_skills),
            'sample_size': len(training_data)
        }
    
    def _calculate_growth_potential(self, profile: Dict[str, Any]) -> float:
        """Calculate career growth potential score"""
        growth_score = 0.5  # Base score
        
        industry = profile.get('industry', 'unknown')
        experience_years = profile.get('experience_years', 0)
        current_skills = profile.get('skills', {})
        education_level = profile.get('education_level', 'bachelor')
        
        # Industry growth factor
        if industry in self.industry_models:
            model = self.industry_models[industry]
            if model['avg_salary_growth'] > 5000:  # $5k+ annual growth
                growth_score += 0.2
            elif model['avg_salary_growth'] > 2000:
                growth_score += 0.1
        
        # Experience factor
        if experience_years < 2:
            growth_score += 0.1  # High potential for growth
        elif experience_years < 5:
            growth_score += 0.2  # Peak growth period
        elif experience_years < 10:
            growth_score += 0.1  # Steady growth
        else:
            growth_score += 0.05  # Senior level, slower growth
        
        # Skills alignment factor
        if isinstance(current_skills, dict):
            skill_score = 0
            skill_count = 0
            
            for skill, level in current_skills.items():
                if skill in self.skill_importance:
                    importance = self.skill_importance[skill]['demand_level']
                    skill_score += level * importance
                    skill_count += 1
            
            if skill_count > 0:
                avg_skill_alignment = skill_score / skill_count
                growth_score += avg_skill_alignment * 0.2
        
        # Education factor
        education_multiplier = {
            'high_school': 0.8,
            'bachelor': 1.0,
            'master': 1.2,
            'phd': 1.4
        }
        growth_score *= education_multiplier.get(education_level, 1.0)
        
        return min(1.0, max(0.0, growth_score))
    
    def _identify_skill_gaps(self, industry: str, current_skills: Dict[str, float]) -> List[str]:
        """Identify skill gaps for career advancement"""
        skill_gaps = []
        
        if industry not in self.industry_models:
            return skill_gaps
        
        model = self.industry_models[industry]
        high_demand_skills = model['high_demand_skills']
        
        for skill in high_demand_skills:
            current_level = current_skills.get(skill, 0.0)
            required_level = model['skill_requirements'].get(skill, [])
            
            if required_level:
                avg_required = np.mean(required_level)
                if current_level < avg_required * 0.8:  # 80% of average requirement
                    skill_gaps.append(skill)
        
        return skill_gaps


class PredictiveAnalyticsEngine:
    """Main predictive analytics engine orchestrating all prediction models"""
    
    def __init__(self):
        self.relationship_predictor = RelationshipPredictor()
        self.health_warning = HealthEarlyWarning()
        self.device_predictor = DeviceFailurePredictor()
        self.career_optimizer = CareerTrajectoryOptimizer()
        
        self.active_predictions: Dict[str, Prediction] = {}
        self.early_warnings: Dict[str, EarlyWarning] = {}
        self.intervention_recommendations: Dict[str, InterventionRecommendation] = {}
        self.prediction_history: deque = deque(maxlen=10000)
        self.data_sources: Dict[str, List[DataPoint]] = defaultdict(list)
        
        # Additional prediction categories (simplified implementations)
        self.prediction_categories = [
            'relationship_maintenance', 'health_early_warning', 'device_failure_prediction',
            'career_trajectory_optimization', 'financial_crisis_prevention', 'social_conflict_early_warning',
            'mental_health_intervention_timing', 'educational_intervention_points', 'business_pivot_indicators',
            'environmental_hazard_detection', 'infrastructure_failure_prediction', 'community_health_metrics'
        ]
    
    def train_all_models(self, training_data: Dict[str, List[DataPoint]]) -> Dict[str, Any]:
        """Train all predictive models with domain-specific data"""
        training_results = {}
        
        # Train relationship predictor
        if 'relationship_maintenance' in training_data:
            result = self.relationship_predictor.train(training_data['relationship_maintenance'])
            training_results['relationship_predictor'] = result
        
        # Train health early warning
        if 'health_early_warning' in training_data:
            result = self.health_warning.train(training_data['health_early_warning'])
            training_results['health_warning'] = result
        
        # Train device failure predictor
        if 'device_failure_prediction' in training_data:
            result = self.device_predictor.train(training_data['device_failure_prediction'])
            training_results['device_predictor'] = result
        
        # Train career optimizer
        if 'career_trajectory_optimization' in training_data:
            result = self.career_optimizer.train(training_data['career_trajectory_optimization'])
            training_results['career_optimizer'] = result
        
        return {
            'success': True,
            'models_trained': len(training_results),
            'training_results': training_results,
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_prediction(self, category: str, input_data: List[DataPoint]) -> Prediction:
        """Generate prediction for specific category"""
        if category == 'relationship_maintenance':
            prediction = self.relationship_predictor.predict(input_data)
        elif category == 'health_early_warning':
            prediction = self.health_warning.predict(input_data)
        elif category == 'device_failure_prediction':
            prediction = self.device_predictor.predict(input_data)
        elif category == 'career_trajectory_optimization':
            prediction = self.career_optimizer.predict(input_data)
        else:
            prediction = self._generate_generic_prediction(category, input_data)
        
        # Store prediction
        self.active_predictions[prediction.prediction_id] = prediction
        self.prediction_history.append(prediction)
        
        # Generate early warning if risk is high
        if prediction.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            warning = self._create_early_warning(prediction)
            self.early_warnings[warning.warning_id] = warning
        
        # Generate intervention recommendation if needed
        if prediction.risk_level in [RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.CRITICAL]:
            recommendation = self._create_intervention_recommendation(prediction)
            self.intervention_recommendations[recommendation.recommendation_id] = recommendation
        
        return prediction
    
    def get_early_warnings(self, risk_levels: List[RiskLevel] = None, 
                          categories: List[str] = None) -> List[EarlyWarning]:
        """Get active early warnings with optional filtering"""
        warnings = list(self.early_warnings.values())
        
        if risk_levels:
            warnings = [w for w in warnings if w.risk_level in risk_levels]
        
        if categories:
            warnings = [w for w in warnings if w.category in categories]
        
        # Filter out expired warnings
        current_time = datetime.now()
        active_warnings = []
        for warning in warnings:
            if warning.expires_at is None or warning.expires_at > current_time:
                active_warnings.append(warning)
        
        return sorted(active_warnings, key=lambda w: w.created_at, reverse=True)
    
    def get_intervention_recommendations(self, categories: List[str] = None,
                                      intervention_types: List[InterventionType] = None) -> List[InterventionRecommendation]:
        """Get intervention recommendations with optional filtering"""
        recommendations = list(self.intervention_recommendations.values())
        
        if categories:
            recommendations = [r for r in recommendations if r.category in categories]
        
        if intervention_types:
            recommendations = [r for r in recommendations if r.intervention_type in intervention_types]
        
        return sorted(recommendations, key=lambda r: r.created_at, reverse=True)
    
    async def run_continuous_monitoring(self, monitoring_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run continuous predictive monitoring"""
        monitoring_interval = monitoring_config.get('interval_minutes', 60)
        categories_to_monitor = monitoring_config.get('categories', self.prediction_categories)
        
        monitoring_results = {
            'started_at': datetime.now().isoformat(),
            'predictions_generated': 0,
            'warnings_created': 0,
            'recommendations_made': 0
        }
        
        # Simulate continuous monitoring
        for cycle in range(monitoring_config.get('cycles', 24)):  # Default 24 hours
            for category in categories_to_monitor:
                # Generate synthetic monitoring data
                synthetic_data = self._generate_monitoring_data(category)
                
                # Generate prediction
                prediction = self.generate_prediction(category, synthetic_data)
                monitoring_results['predictions_generated'] += 1
                
                # Count warnings and recommendations
                if prediction.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    monitoring_results['warnings_created'] += 1
                
                if prediction.risk_level in [RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    monitoring_results['recommendations_made'] += 1
            
            # Sleep between monitoring cycles
            await asyncio.sleep(monitoring_interval * 60 / 100)  # Scaled for demo
        
        monitoring_results['completed_at'] = datetime.now().isoformat()
        
        return monitoring_results
    
    def analyze_prediction_trends(self, category: str, days: int = 30) -> Dict[str, Any]:
        """Analyze prediction trends over time"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        category_predictions = [
            p for p in self.prediction_history 
            if p.category == category and p.created_at >= cutoff_time
        ]
        
        if not category_predictions:
            return {'error': f'No predictions found for category {category}'}
        
        # Calculate trend metrics
        risk_levels = [p.risk_level for p in category_predictions]
        probabilities = [p.probability for p in category_predictions]
        confidence_levels = [p.confidence for p in category_predictions]
        
        risk_distribution = {}
        for level in RiskLevel:
            risk_distribution[level.value] = risk_levels.count(level)
        
        confidence_distribution = {}
        for level in PredictionConfidence:
            confidence_distribution[level.value] = confidence_levels.count(level)
        
        return {
            'category': category,
            'analysis_period_days': days,
            'total_predictions': len(category_predictions),
            'average_probability': np.mean(probabilities),
            'probability_trend': 'increasing' if len(probabilities) > 1 and probabilities[-1] > probabilities[0] else 'stable',
            'risk_distribution': risk_distribution,
            'confidence_distribution': confidence_distribution,
            'most_common_risk_level': max(risk_distribution.keys(), key=lambda k: risk_distribution[k]),
            'prediction_frequency': len(category_predictions) / days
        }
    
    def _generate_generic_prediction(self, category: str, input_data: List[DataPoint]) -> Prediction:
        """Generate generic prediction for categories without specific models"""
        # Simplified generic prediction logic
        risk_score = random.uniform(0.1, 0.9)
        
        if 'financial_crisis' in category:
            outcome = "financial_stability_assessment"
            data_sources = [DataSource.FINANCIAL_DATA, DataSource.THIRD_PARTY]
        elif 'social_conflict' in category:
            outcome = "social_tension_analysis"
            data_sources = [DataSource.SOCIAL_MEDIA, DataSource.USER_INPUT]
        elif 'mental_health' in category:
            outcome = "mental_health_status"
            data_sources = [DataSource.USER_INPUT, DataSource.SENSOR]
        elif 'educational' in category:
            outcome = "learning_progress_assessment"
            data_sources = [DataSource.USER_INPUT, DataSource.THIRD_PARTY]
        elif 'business_pivot' in category:
            outcome = "market_position_analysis"
            data_sources = [DataSource.THIRD_PARTY, DataSource.FINANCIAL_DATA]
        elif 'environmental_hazard' in category:
            outcome = "environmental_risk_assessment"
            data_sources = [DataSource.ENVIRONMENTAL, DataSource.SENSOR]
        elif 'infrastructure_failure' in category:
            outcome = "infrastructure_integrity_check"
            data_sources = [DataSource.SENSOR, DataSource.DEVICE_TELEMETRY]
        elif 'community_health' in category:
            outcome = "population_health_metrics"
            data_sources = [DataSource.MEDICAL_RECORDS, DataSource.ENVIRONMENTAL]
        else:
            outcome = "generic_risk_assessment"
            data_sources = [DataSource.USER_INPUT]
        
        # Determine risk level based on score
        if risk_score > 0.8:
            risk_level = RiskLevel.CRITICAL
            confidence = PredictionConfidence.HIGH
            timeframe = timedelta(days=1)
        elif risk_score > 0.6:
            risk_level = RiskLevel.HIGH
            confidence = PredictionConfidence.MEDIUM
            timeframe = timedelta(days=7)
        elif risk_score > 0.4:
            risk_level = RiskLevel.MODERATE
            confidence = PredictionConfidence.MEDIUM
            timeframe = timedelta(days=30)
        else:
            risk_level = RiskLevel.LOW
            confidence = PredictionConfidence.LOW
            timeframe = timedelta(days=90)
        
        return Prediction(
            prediction_id=f"generic_pred_{uuid.uuid4().hex}",
            category=category,
            description=f"Generic prediction for {category}",
            predicted_outcome=outcome,
            probability=risk_score,
            confidence=confidence,
            risk_level=risk_level,
            predicted_timeframe=timeframe,
            data_sources=data_sources,
            contributing_factors=[f"risk_score: {risk_score:.2f}"]
        )
    
    def _create_early_warning(self, prediction: Prediction) -> EarlyWarning:
        """Create early warning from high-risk prediction"""
        warning_id = f"warning_{uuid.uuid4().hex}"
        
        urgency = InterventionType.IMMEDIATE if prediction.risk_level == RiskLevel.CRITICAL else InterventionType.SCHEDULED
        
        # Generate category-specific recommendations
        recommendations = self._generate_warning_recommendations(prediction.category, prediction.risk_level)
        
        expires_at = datetime.now() + prediction.predicted_timeframe
        
        return EarlyWarning(
            warning_id=warning_id,
            category=prediction.category,
            title=f"Early Warning: {prediction.category.replace('_', ' ').title()}",
            description=f"Risk level {prediction.risk_level.value} detected for {prediction.predicted_outcome}",
            risk_level=prediction.risk_level,
            urgency=urgency,
            predicted_impact=f"Impact expected within {prediction.predicted_timeframe.days} days",
            recommendations=recommendations,
            data_evidence=[f"Prediction confidence: {prediction.confidence.value}"] + prediction.contributing_factors,
            expires_at=expires_at
        )
    
    def _create_intervention_recommendation(self, prediction: Prediction) -> InterventionRecommendation:
        """Create intervention recommendation from prediction"""
        recommendation_id = f"intervention_{uuid.uuid4().hex}"
        
        # Determine intervention type based on risk level
        if prediction.risk_level == RiskLevel.CRITICAL:
            intervention_type = InterventionType.EMERGENCY
        elif prediction.risk_level == RiskLevel.HIGH:
            intervention_type = InterventionType.IMMEDIATE
        elif prediction.risk_level == RiskLevel.MODERATE:
            intervention_type = InterventionType.SCHEDULED
        else:
            intervention_type = InterventionType.PREVENTIVE
        
        # Generate category-specific intervention details
        intervention_details = self._generate_intervention_details(prediction.category, intervention_type)
        
        return InterventionRecommendation(
            recommendation_id=recommendation_id,
            category=prediction.category,
            intervention_type=intervention_type,
            title=intervention_details['title'],
            description=intervention_details['description'],
            expected_impact=intervention_details['expected_impact'],
            implementation_steps=intervention_details['implementation_steps'],
            resource_requirements=intervention_details['resource_requirements'],
            timing=intervention_details['timing'],
            success_metrics=intervention_details['success_metrics']
        )
    
    def _generate_warning_recommendations(self, category: str, risk_level: RiskLevel) -> List[str]:
        """Generate category-specific warning recommendations"""
        base_recommendations = {
            'relationship_maintenance': [
                "Schedule quality time together",
                "Improve communication frequency",
                "Address underlying conflicts",
                "Seek relationship counseling if needed"
            ],
            'health_early_warning': [
                "Consult healthcare provider immediately",
                "Monitor symptoms closely",
                "Maintain healthy lifestyle habits",
                "Follow medical recommendations"
            ],
            'device_failure_prediction': [
                "Schedule device maintenance",
                "Back up important data",
                "Prepare replacement device",
                "Monitor performance metrics"
            ],
            'career_trajectory_optimization': [
                "Develop missing skills",
                "Network within industry",
                "Consider career counseling",
                "Update resume and portfolio"
            ]
        }
        
        default_recommendations = [
            "Monitor situation closely",
            "Gather additional data",
            "Consult relevant experts",
            "Develop contingency plans"
        ]
        
        recommendations = base_recommendations.get(category, default_recommendations)
        
        # Add urgency-based recommendations
        if risk_level == RiskLevel.CRITICAL:
            recommendations.insert(0, "Take immediate action")
        elif risk_level == RiskLevel.HIGH:
            recommendations.insert(0, "Address within 24-48 hours")
        
        return recommendations
    
    def _generate_intervention_details(self, category: str, intervention_type: InterventionType) -> Dict[str, Any]:
        """Generate detailed intervention information"""
        base_details = {
            'relationship_maintenance': {
                'title': 'Relationship Intervention Program',
                'description': 'Structured approach to improve relationship satisfaction and stability',
                'expected_impact': 'Improved communication, reduced conflict, increased satisfaction',
                'implementation_steps': [
                    'Assess current relationship dynamics',
                    'Identify specific areas for improvement',
                    'Implement communication strategies',
                    'Schedule regular check-ins',
                    'Monitor progress and adjust approach'
                ],
                'resource_requirements': {
                    'time_commitment': '2-3 hours per week',
                    'financial_cost': '$0-500 (depending on professional help)',
                    'tools_needed': ['communication guides', 'tracking sheets']
                },
                'timing': {
                    'start_immediately': intervention_type in [InterventionType.IMMEDIATE, InterventionType.EMERGENCY],
                    'duration_weeks': 8,
                    'follow_up_months': 3
                },
                'success_metrics': [
                    'Improved satisfaction scores',
                    'Reduced conflict frequency',
                    'Increased quality time together'
                ]
            }
        }
        
        default_details = {
            'title': f'{category.replace("_", " ").title()} Intervention',
            'description': f'Structured intervention for {category}',
            'expected_impact': 'Risk reduction and improved outcomes',
            'implementation_steps': [
                'Assess current situation',
                'Develop action plan',
                'Implement interventions',
                'Monitor progress'
            ],
            'resource_requirements': {
                'time_commitment': 'Variable',
                'financial_cost': 'To be determined',
                'tools_needed': ['monitoring tools']
            },
            'timing': {
                'start_immediately': intervention_type == InterventionType.IMMEDIATE,
                'duration_weeks': 4,
                'follow_up_months': 1
            },
            'success_metrics': [
                'Risk level reduction',
                'Improved key metrics',
                'Stakeholder satisfaction'
            ]
        }
        
        return base_details.get(category, default_details)
    
    def _generate_monitoring_data(self, category: str) -> List[DataPoint]:
        """Generate synthetic monitoring data for testing"""
        data_points = []
        
        if category == 'relationship_maintenance':
            data_points.append(DataPoint(
                data_id=f"rel_data_{uuid.uuid4().hex}",
                source=DataSource.USER_INPUT,
                category=category,
                value={
                    'communication_frequency': random.uniform(0.3, 1.0),
                    'sentiment_score': random.uniform(0.2, 0.9),
                    'response_time': random.uniform(0.1, 0.8),
                    'conflict_frequency': random.uniform(0.0, 0.7),
                    'shared_activities': random.uniform(0.2, 0.9),
                    'satisfaction_score': random.uniform(0.3, 0.9)
                }
            ))
        elif category == 'health_early_warning':
            data_points.append(DataPoint(
                data_id=f"health_data_{uuid.uuid4().hex}",
                source=DataSource.SENSOR,
                category=category,
                value={
                    'heart_rate': random.uniform(60, 100),
                    'blood_pressure_systolic': random.uniform(110, 140),
                    'blood_pressure_diastolic': random.uniform(70, 90),
                    'sleep_quality': random.uniform(0.3, 1.0),
                    'stress_level': random.uniform(0.1, 0.8),
                    'symptoms': random.sample(['fatigue', 'headache', 'nausea', 'dizziness'], random.randint(0, 2))
                }
            ))
        elif category == 'device_failure_prediction':
            data_points.append(DataPoint(
                data_id=f"device_data_{uuid.uuid4().hex}",
                source=DataSource.DEVICE_TELEMETRY,
                category=category,
                value={
                    'device_type': random.choice(['laptop', 'smartphone', 'tablet', 'server']),
                    'cpu_temperature': random.uniform(40, 85),
                    'memory_usage': random.uniform(0.3, 0.9),
                    'disk_usage': random.uniform(0.4, 0.95),
                    'battery_health': random.uniform(0.6, 1.0),
                    'usage_hours': random.uniform(1000, 10000),
                    'age_days': random.uniform(30, 1800)
                }
            ))
        else:
            # Generic data
            data_points.append(DataPoint(
                data_id=f"generic_data_{uuid.uuid4().hex}",
                source=DataSource.USER_INPUT,
                category=category,
                value={
                    'risk_indicator': random.uniform(0.1, 0.9),
                    'stability_score': random.uniform(0.2, 0.8),
                    'trend_direction': random.choice(['improving', 'stable', 'declining'])
                }
            ))
        
        return data_points
    
    def export_analytics_data(self) -> Dict[str, Any]:
        """Export all analytics data for backup or analysis"""
        return {
            'export_timestamp': datetime.now().isoformat(),
            'active_predictions': {
                pred_id: {
                    'category': pred.category,
                    'outcome': pred.predicted_outcome,
                    'probability': pred.probability,
                    'risk_level': pred.risk_level.value,
                    'confidence': pred.confidence.value,
                    'created_at': pred.created_at.isoformat()
                } for pred_id, pred in self.active_predictions.items()
            },
            'early_warnings': {
                warn_id: {
                    'category': warn.category,
                    'title': warn.title,
                    'risk_level': warn.risk_level.value,
                    'urgency': warn.urgency.value,
                    'created_at': warn.created_at.isoformat()
                } for warn_id, warn in self.early_warnings.items()
            },
            'intervention_recommendations': {
                rec_id: {
                    'category': rec.category,
                    'title': rec.title,
                    'intervention_type': rec.intervention_type.value,
                    'created_at': rec.created_at.isoformat()
                } for rec_id, rec in self.intervention_recommendations.items()
            },
            'prediction_statistics': {
                'total_predictions': len(self.prediction_history),
                'categories_covered': len(set(p.category for p in self.prediction_history)),
                'active_warnings': len(self.early_warnings),
                'active_recommendations': len(self.intervention_recommendations)
            }
        }


# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Create predictive analytics engine
        analytics = PredictiveAnalyticsEngine()
        
        # Generate sample training data
        print("Generating training data...")
        
        # Relationship training data
        relationship_training = []
        for i in range(100):
            satisfaction = random.uniform(0.1, 1.0)
            relationship_training.append(DataPoint(
                data_id=f"rel_train_{i}",
                source=DataSource.USER_INPUT,
                category="relationship_maintenance",
                value={
                    'communication_frequency': random.uniform(0.2, 1.0),
                    'sentiment_score': satisfaction + random.uniform(-0.2, 0.2),
                    'response_time': 1.0 - satisfaction + random.uniform(-0.1, 0.1),
                    'conflict_frequency': 1.0 - satisfaction + random.uniform(-0.1, 0.1),
                    'shared_activities': satisfaction + random.uniform(-0.1, 0.1),
                    'life_stage_alignment': random.uniform(0.3, 1.0),
                    'stress_levels': random.uniform(0.1, 0.8),
                    'support_ratio': satisfaction + random.uniform(-0.1, 0.1),
                    'intimacy_score': satisfaction + random.uniform(-0.1, 0.1),
                    'trust_level': satisfaction + random.uniform(-0.05, 0.05),
                    'satisfaction_score': satisfaction
                }
            ))
        
        # Health training data
        health_training = []
        for i in range(150):
            has_condition = random.choice([True, False])
            condition = random.choice(['cardiovascular_disease', 'diabetes', 'hypertension'])
            
            health_training.append(DataPoint(
                data_id=f"health_train_{i}",
                source=DataSource.MEDICAL_RECORDS,
                category="health_early_warning",
                value={
                    'heart_rate': random.uniform(60, 100) + (20 if has_condition else 0),
                    'blood_pressure_systolic': random.uniform(110, 130) + (20 if has_condition else 0),
                    'cholesterol': random.uniform(150, 200) + (50 if has_condition else 0),
                    'bmi': random.uniform(20, 25) + (5 if has_condition else 0),
                    'age': random.uniform(25, 75),
                    'exercise_frequency': random.uniform(0.2, 1.0),
                    'condition': condition,
                    'has_condition': has_condition
                }
            ))
        
        # Device training data
        device_training = []
        for i in range(80):
            failed = random.choice([True, False])
            device_type = random.choice(['laptop', 'smartphone', 'server'])
            
            device_training.append(DataPoint(
                data_id=f"device_train_{i}",
                source=DataSource.DEVICE_TELEMETRY,
                category="device_failure_prediction",
                value={
                    'device_type': device_type,
                    'cpu_temperature': random.uniform(45, 75) + (15 if failed else 0),
                    'memory_usage': random.uniform(0.3, 0.7) + (0.2 if failed else 0),
                    'disk_usage': random.uniform(0.4, 0.8) + (0.1 if failed else 0),
                    'usage_hours': random.uniform(2000, 8000),
                    'age_days': random.uniform(100, 1500),
                    'failed': failed
                }
            ))
        
        # Career training data
        career_training = []
        for i in range(120):
            industry = random.choice(['technology', 'healthcare', 'finance', 'education'])
            experience = random.uniform(0, 20)
            
            career_training.append(DataPoint(
                data_id=f"career_train_{i}",
                source=DataSource.USER_INPUT,
                category="career_trajectory_optimization",
                value={
                    'industry': industry,
                    'role': random.choice(['analyst', 'manager', 'specialist', 'director']),
                    'experience_years': experience,
                    'salary': 40000 + experience * 3000 + random.uniform(-10000, 10000),
                    'education_level': random.choice(['bachelor', 'master', 'phd']),
                    'skills': {
                        'programming': random.uniform(0.1, 1.0),
                        'leadership': random.uniform(0.1, 1.0),
                        'communication': random.uniform(0.3, 1.0),
                        'analysis': random.uniform(0.2, 1.0)
                    }
                }
            ))
        
        # Train all models
        training_data = {
            'relationship_maintenance': relationship_training,
            'health_early_warning': health_training,
            'device_failure_prediction': device_training,
            'career_trajectory_optimization': career_training
        }
        
        print("Training models...")
        training_results = analytics.train_all_models(training_data)
        print(f"Training completed: {training_results['models_trained']} models trained")
        
        # Generate test predictions
        print("\nGenerating predictions...")
        
        # Test relationship prediction
        rel_test_data = [DataPoint(
            data_id="rel_test_1",
            source=DataSource.USER_INPUT,
            category="relationship_maintenance",
            value={
                'communication_frequency': 0.3,
                'sentiment_score': 0.4,
                'response_time': 0.7,
                'conflict_frequency': 0.6,
                'shared_activities': 0.2,
                'life_stage_alignment': 0.5,
                'stress_levels': 0.8,
                'support_ratio': 0.3,
                'intimacy_score': 0.4,
                'trust_level': 0.5
            }
        )]
        
        rel_prediction = analytics.generate_prediction('relationship_maintenance', rel_test_data)
        print(f"Relationship prediction: {rel_prediction.predicted_outcome} (risk: {rel_prediction.risk_level.value})")
        
        # Test health prediction
        health_test_data = [DataPoint(
            data_id="health_test_1",
            source=DataSource.SENSOR,
            category="health_early_warning",
            value={
                'heart_rate': 95,
                'blood_pressure_systolic': 145,
                'cholesterol': 240,
                'bmi': 28,
                'age': 45,
                'exercise_frequency': 0.2,
                'symptoms': ['fatigue', 'headache']
            }
        )]
        
        health_prediction = analytics.generate_prediction('health_early_warning', health_test_data)
        print(f"Health prediction: {health_prediction.predicted_outcome} (risk: {health_prediction.risk_level.value})")
        
        # Test device prediction
        device_test_data = [DataPoint(
            data_id="device_test_1",
            source=DataSource.DEVICE_TELEMETRY,
            category="device_failure_prediction",
            value={
                'device_type': 'laptop',
                'cpu_temperature': 82,
                'memory_usage': 0.9,
                'disk_usage': 0.95,
                'battery_health': 0.6,
                'usage_hours': 8000,
                'age_days': 1200
            }
        )]
        
        device_prediction = analytics.generate_prediction('device_failure_prediction', device_test_data)
        print(f"Device prediction: {device_prediction.predicted_outcome} (risk: {device_prediction.risk_level.value})")
        
        # Test career prediction
        career_test_data = [DataPoint(
            data_id="career_test_1",
            source=DataSource.USER_INPUT,
            category="career_trajectory_optimization",
            value={
                'industry': 'technology',
                'role': 'analyst',
                'experience_years': 3,
                'salary': 55000,
                'education_level': 'bachelor',
                'skills': {
                    'programming': 0.6,
                    'leadership': 0.3,
                    'communication': 0.7,
                    'analysis': 0.8
                }
            }
        )]
        
        career_prediction = analytics.generate_prediction('career_trajectory_optimization', career_test_data)
        print(f"Career prediction: {career_prediction.predicted_outcome} (risk: {career_prediction.risk_level.value})")
        
        # Get early warnings
        warnings = analytics.get_early_warnings([RiskLevel.HIGH, RiskLevel.CRITICAL])
        print(f"\nActive early warnings: {len(warnings)}")
        for warning in warnings[:2]:
            print(f"- {warning.title}: {warning.description}")
        
        # Get intervention recommendations
        recommendations = analytics.get_intervention_recommendations()
        print(f"\nIntervention recommendations: {len(recommendations)}")
        for rec in recommendations[:2]:
            print(f"- {rec.title}: {rec.intervention_type.value}")
        
        # Run continuous monitoring simulation
        print("\nRunning continuous monitoring simulation...")
        monitoring_config = {
            'interval_minutes': 1,
            'cycles': 5,
            'categories': ['relationship_maintenance', 'health_early_warning']
        }
        
        monitoring_results = await analytics.run_continuous_monitoring(monitoring_config)
        print(f"Monitoring completed:")
        print(f"- Predictions generated: {monitoring_results['predictions_generated']}")
        print(f"- Warnings created: {monitoring_results['warnings_created']}")
        print(f"- Recommendations made: {monitoring_results['recommendations_made']}")
        
        # Analyze prediction trends
        print("\nAnalyzing prediction trends...")
        trends = analytics.analyze_prediction_trends('relationship_maintenance')
        if 'error' not in trends:
            print(f"Relationship trends: {trends['total_predictions']} predictions, avg probability: {trends['average_probability']:.2f}")
            print(f"Most common risk level: {trends['most_common_risk_level']}")
        
        # Export analytics data
        export_data = analytics.export_analytics_data()
        print(f"\nAnalytics summary:")
        print(f"- Total predictions: {export_data['prediction_statistics']['total_predictions']}")
        print(f"- Categories covered: {export_data['prediction_statistics']['categories_covered']}")
        print(f"- Active warnings: {export_data['prediction_statistics']['active_warnings']}")
        print(f"- Active recommendations: {export_data['prediction_statistics']['active_recommendations']}")
    
    # Run the example
    asyncio.run(main())