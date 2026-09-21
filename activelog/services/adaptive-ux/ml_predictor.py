#!/usr/bin/env python3
"""
Machine Learning Predictor for Adaptive UX System

This module provides advanced machine learning capabilities including user behavior
prediction, feature recommendation, interface optimization, and adaptive learning
for the adaptive UX system.
"""

import asyncio
import json
import logging
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque, Counter
import numpy as np
from scipy import stats
from scipy.spatial.distance import cosine
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error, precision_recall_fscore_support
import pandas as pd

from interface_intelligence import ExpertiseLevel, InteractionContext
from analytics_engine import AnalyticsEvent, AnalyticsEventType

class ModelType(Enum):
    """Types of ML models"""
    CLASSIFICATION = "classification"
    REGRESSION = "regression" 
    CLUSTERING = "clustering"
    RECOMMENDATION = "recommendation"
    ANOMALY_DETECTION = "anomaly_detection"
    REINFORCEMENT = "reinforcement"

class PredictionType(Enum):
    """Types of predictions"""
    USER_CHURN = "user_churn"
    FEATURE_ADOPTION = "feature_adoption"
    INTERFACE_PREFERENCE = "interface_preference"
    NEXT_ACTION = "next_action"
    ENGAGEMENT_SCORE = "engagement_score"
    ERROR_LIKELIHOOD = "error_likelihood"
    HELP_NEED = "help_need"
    OPTIMAL_TIMING = "optimal_timing"

@dataclass
class MLModel:
    """Machine learning model container"""
    model_id: str
    model_type: ModelType
    prediction_type: PredictionType
    model: Any
    scaler: Optional[Any] = None
    encoder: Optional[Any] = None
    feature_names: List[str] = field(default_factory=list)
    training_data_size: int = 0
    accuracy: float = 0.0
    last_trained: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0"

@dataclass
class FeatureVector:
    """Feature vector for ML models"""
    user_id: str
    features: Dict[str, float]
    target: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Prediction:
    """ML prediction result"""
    prediction_id: str
    user_id: str
    prediction_type: PredictionType
    predicted_value: Union[float, str, Dict[str, Any]]
    confidence: float
    model_version: str
    features_used: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    explanation: Optional[str] = None

class FeatureEngineering:
    """Feature engineering for user behavior data"""
    
    def __init__(self):
        self.feature_cache = {}
        self.logger = logging.getLogger(__name__)
    
    def extract_user_features(self, user_id: str, events: List[AnalyticsEvent], 
                            time_window: timedelta = None) -> FeatureVector:
        """Extract comprehensive features for a user"""
        if time_window:
            cutoff = datetime.utcnow() - time_window
            events = [e for e in events if e.timestamp > cutoff]
        
        if not events:
            return FeatureVector(user_id, {})
        
        features = {}
        
        # Temporal features
        features.update(self._extract_temporal_features(events))
        
        # Behavioral features
        features.update(self._extract_behavioral_features(events))
        
        # Interaction features
        features.update(self._extract_interaction_features(events))
        
        # Engagement features
        features.update(self._extract_engagement_features(events))
        
        # Error and help features
        features.update(self._extract_error_help_features(events))
        
        # Session features
        features.update(self._extract_session_features(events))
        
        # Feature usage features
        features.update(self._extract_feature_usage_features(events))
        
        return FeatureVector(user_id, features)
    
    def _extract_temporal_features(self, events: List[AnalyticsEvent]) -> Dict[str, float]:
        """Extract time-based features"""
        features = {}
        
        timestamps = [e.timestamp for e in events]
        
        # Basic temporal stats
        features["days_active"] = (max(timestamps) - min(timestamps)).days + 1
        features["events_per_day"] = len(events) / features["days_active"]
        
        # Activity patterns
        hours = [t.hour for t in timestamps]
        weekdays = [t.weekday() for t in timestamps]
        
        features["most_active_hour"] = Counter(hours).most_common(1)[0][0]
        features["weekend_activity_ratio"] = len([w for w in weekdays if w >= 5]) / len(weekdays)
        
        # Recency
        features["days_since_last_activity"] = (datetime.utcnow() - max(timestamps)).days
        features["days_since_first_activity"] = (datetime.utcnow() - min(timestamps)).days
        
        # Activity distribution
        hourly_counts = Counter(hours)
        features["activity_variance"] = np.var(list(hourly_counts.values()))
        features["peak_activity_concentration"] = max(hourly_counts.values()) / len(events)
        
        return features
    
    def _extract_behavioral_features(self, events: List[AnalyticsEvent]) -> Dict[str, float]:
        """Extract behavioral pattern features"""
        features = {}
        
        # Event type distribution
        event_types = [e.event_type.value for e in events]
        type_counts = Counter(event_types)
        total_events = len(events)
        
        for event_type in AnalyticsEventType:
            features[f"{event_type.value}_ratio"] = type_counts.get(event_type.value, 0) / total_events
        
        # Sequence patterns
        features.update(self._extract_sequence_patterns(events))
        
        # Interaction depth
        interactions = [e for e in events if e.event_type == AnalyticsEventType.USER_INTERACTION]
        if interactions:
            durations = []
            for event in interactions:
                duration = event.properties.get("duration", 0)
                if duration and duration > 0:
                    durations.append(duration)
            
            if durations:
                features["avg_interaction_duration"] = np.mean(durations)
                features["max_interaction_duration"] = max(durations)
                features["interaction_duration_variance"] = np.var(durations)
            else:
                features["avg_interaction_duration"] = 0
                features["max_interaction_duration"] = 0
                features["interaction_duration_variance"] = 0
        
        return features
    
    def _extract_sequence_patterns(self, events: List[AnalyticsEvent]) -> Dict[str, float]:
        """Extract behavioral sequence patterns"""
        features = {}
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        event_sequence = [e.event_type.value for e in sorted_events]
        
        if len(event_sequence) < 2:
            return features
        
        # Common transitions
        transitions = []
        for i in range(len(event_sequence) - 1):
            transitions.append((event_sequence[i], event_sequence[i + 1]))
        
        transition_counts = Counter(transitions)
        
        # Most common transition patterns
        if transition_counts:
            most_common_transition = transition_counts.most_common(1)[0]
            features["most_common_transition_freq"] = most_common_transition[1] / len(transitions)
        
        # Error recovery patterns
        error_recovery_count = 0
        for i in range(len(event_sequence) - 1):
            if (event_sequence[i] == "error_occurrence" and 
                event_sequence[i + 1] in ["user_interaction", "help_request"]):
                error_recovery_count += 1
        
        features["error_recovery_rate"] = error_recovery_count / max(
            len([e for e in event_sequence if e == "error_occurrence"]), 1
        )
        
        # Help-seeking patterns
        help_to_success = 0
        for i in range(len(event_sequence) - 2):
            if (event_sequence[i] == "help_request" and
                event_sequence[i + 1] == "user_interaction" and
                event_sequence[i + 2] == "goal_completion"):
                help_to_success += 1
        
        help_requests = len([e for e in event_sequence if e == "help_request"])
        features["help_success_rate"] = help_to_success / max(help_requests, 1)
        
        return features
    
    def _extract_interaction_features(self, events: List[AnalyticsEvent]) -> Dict[str, float]:
        """Extract interaction-specific features"""
        features = {}
        
        interactions = [e for e in events if e.event_type == AnalyticsEventType.USER_INTERACTION]
        
        if not interactions:
            return {"interaction_count": 0}
        
        # Feature diversity
        features_used = set()
        for event in interactions:
            feature_id = event.properties.get("feature_id")
            if feature_id:
                features_used.add(feature_id)
        
        features["unique_features_used"] = len(features_used)
        features["feature_diversity_ratio"] = len(features_used) / len(interactions)
        
        # Success patterns
        successes = [e for e in interactions if e.properties.get("success", True)]
        features["interaction_success_rate"] = len(successes) / len(interactions)
        
        # Complexity progression
        complexity_scores = []
        for event in interactions:
            complexity = event.properties.get("complexity_score", 0.5)
            complexity_scores.append(complexity)
        
        if complexity_scores:
            features["avg_complexity"] = np.mean(complexity_scores)
            features["complexity_progression"] = self._calculate_trend(complexity_scores)
        
        return features
    
    def _extract_engagement_features(self, events: List[AnalyticsEvent]) -> Dict[str, float]:
        """Extract engagement-related features"""
        features = {}
        
        # Session lengths and frequencies
        sessions = self._group_events_into_sessions(events)
        
        if sessions:
            session_lengths = [s["duration"] for s in sessions]
            features["avg_session_length"] = np.mean(session_lengths)
            features["max_session_length"] = max(session_lengths)
            features["session_length_variance"] = np.var(session_lengths)
            features["total_sessions"] = len(sessions)
        
        # Conversion events
        conversions = [e for e in events if e.event_type == AnalyticsEventType.CONVERSION_EVENT]
        features["conversion_count"] = len(conversions)
        features["conversion_rate"] = len(conversions) / len(events) if events else 0
        
        # Goal completions
        goals = [e for e in events if e.event_type == AnalyticsEventType.GOAL_COMPLETION]
        features["goal_completion_count"] = len(goals)
        features["goal_completion_rate"] = len(goals) / len(events) if events else 0
        
        return features
    
    def _extract_error_help_features(self, events: List[AnalyticsEvent]) -> Dict[str, float]:
        """Extract error and help-related features"""
        features = {}
        
        errors = [e for e in events if e.event_type == AnalyticsEventType.ERROR_OCCURRENCE]
        help_requests = [e for e in events if e.event_type == AnalyticsEventType.HELP_REQUEST]
        
        total_events = len(events)
        
        features["error_count"] = len(errors)
        features["error_rate"] = len(errors) / total_events if total_events > 0 else 0
        features["help_request_count"] = len(help_requests)
        features["help_request_rate"] = len(help_requests) / total_events if total_events > 0 else 0
        
        # Error clustering (types of errors)
        if errors:
            error_types = [e.properties.get("error_type", "unknown") for e in errors]
            unique_error_types = len(set(error_types))
            features["error_type_diversity"] = unique_error_types / len(errors)
        
        # Help request patterns
        if help_requests:
            help_contexts = [e.context.get("context", "unknown") for e in help_requests]
            help_diversity = len(set(help_contexts)) / len(help_requests)
            features["help_context_diversity"] = help_diversity
        
        return features
    
    def _extract_session_features(self, events: List[AnalyticsEvent]) -> Dict[str, float]:
        """Extract session-based features"""
        features = {}
        
        sessions = self._group_events_into_sessions(events)
        
        if not sessions:
            return {"session_count": 0}
        
        # Session metrics
        features["session_count"] = len(sessions)
        
        session_event_counts = [s["event_count"] for s in sessions]
        features["avg_events_per_session"] = np.mean(session_event_counts)
        features["max_events_per_session"] = max(session_event_counts)
        
        # Session quality metrics
        productive_sessions = 0
        for session in sessions:
            session_events = session["events"]
            goals = [e for e in session_events if e.event_type == AnalyticsEventType.GOAL_COMPLETION]
            errors = [e for e in session_events if e.event_type == AnalyticsEventType.ERROR_OCCURRENCE]
            
            # Session is productive if goals > errors
            if len(goals) > len(errors):
                productive_sessions += 1
        
        features["productive_session_rate"] = productive_sessions / len(sessions)
        
        # Bounce rate (single-event sessions)
        bounce_sessions = len([s for s in sessions if s["event_count"] <= 1])
        features["bounce_rate"] = bounce_sessions / len(sessions)
        
        return features
    
    def _extract_feature_usage_features(self, events: List[AnalyticsEvent]) -> Dict[str, float]:
        """Extract feature usage patterns"""
        features = {}
        
        # Feature adoption events
        adoptions = [e for e in events if e.event_type == AnalyticsEventType.FEATURE_ADOPTION]
        features["feature_adoption_count"] = len(adoptions)
        
        # Feature usage frequency
        interactions = [e for e in events if e.event_type == AnalyticsEventType.USER_INTERACTION]
        feature_usage = Counter()
        
        for event in interactions:
            feature_id = event.properties.get("feature_id")
            if feature_id:
                feature_usage[feature_id] += 1
        
        if feature_usage:
            # Most used feature frequency
            most_used_count = feature_usage.most_common(1)[0][1]
            features["max_feature_usage"] = most_used_count
            features["feature_usage_concentration"] = most_used_count / sum(feature_usage.values())
            
            # Feature exploration (using less common features)
            usage_values = list(feature_usage.values())
            features["feature_usage_variance"] = np.var(usage_values)
            features["feature_exploration_tendency"] = len([v for v in usage_values if v <= 2]) / len(usage_values)
        
        return features
    
    def _group_events_into_sessions(self, events: List[AnalyticsEvent], 
                                  timeout_minutes: int = 30) -> List[Dict[str, Any]]:
        """Group events into sessions based on time gaps"""
        if not events:
            return []
        
        sessions = []
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        current_session = {
            "start_time": sorted_events[0].timestamp,
            "events": [sorted_events[0]],
            "event_count": 1
        }
        
        timeout_delta = timedelta(minutes=timeout_minutes)
        
        for event in sorted_events[1:]:
            time_since_last = event.timestamp - current_session["events"][-1].timestamp
            
            if time_since_last > timeout_delta:
                # End current session
                current_session["end_time"] = current_session["events"][-1].timestamp
                current_session["duration"] = (
                    current_session["end_time"] - current_session["start_time"]
                ).total_seconds()
                sessions.append(current_session)
                
                # Start new session
                current_session = {
                    "start_time": event.timestamp,
                    "events": [event],
                    "event_count": 1
                }
            else:
                # Continue current session
                current_session["events"].append(event)
                current_session["event_count"] += 1
        
        # Don't forget the last session
        if current_session["events"]:
            current_session["end_time"] = current_session["events"][-1].timestamp
            current_session["duration"] = (
                current_session["end_time"] - current_session["start_time"]
            ).total_seconds()
            sessions.append(current_session)
        
        return sessions
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction (-1 to 1)"""
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression slope
        x = np.arange(len(values))
        try:
            slope, _, _, _, _ = stats.linregress(x, values)
            # Normalize slope to -1, 1 range
            return max(-1, min(1, slope))
        except:
            return 0.0

class ChurnPredictor:
    """Advanced churn prediction using machine learning"""
    
    def __init__(self):
        self.model: Optional[MLModel] = None
        self.feature_engineering = FeatureEngineering()
        self.logger = logging.getLogger(__name__)
    
    def train_model(self, training_data: List[Tuple[FeatureVector, bool]]) -> MLModel:
        """Train churn prediction model"""
        if len(training_data) < 50:
            raise ValueError("Insufficient training data (minimum 50 samples required)")
        
        # Prepare features and targets
        X = []
        y = []
        
        for feature_vector, churned in training_data:
            X.append(list(feature_vector.features.values()))
            y.append(1 if churned else 0)
        
        X = np.array(X)
        y = np.array(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train Random Forest model
        model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
        model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='binary')
        
        self.logger.info(f"Churn model trained - Accuracy: {accuracy:.3f}, F1: {f1:.3f}")
        
        # Create ML model container
        feature_names = list(training_data[0][0].features.keys())
        ml_model = MLModel(
            model_id="churn_predictor_v1",
            model_type=ModelType.CLASSIFICATION,
            prediction_type=PredictionType.USER_CHURN,
            model=model,
            scaler=scaler,
            feature_names=feature_names,
            training_data_size=len(training_data),
            accuracy=accuracy
        )
        
        self.model = ml_model
        return ml_model
    
    def predict_churn(self, feature_vector: FeatureVector) -> Prediction:
        """Predict churn probability for a user"""
        if not self.model:
            raise ValueError("Model not trained yet")
        
        # Prepare features
        features = [feature_vector.features.get(name, 0.0) for name in self.model.feature_names]
        X = np.array([features])
        
        # Scale features
        X_scaled = self.model.scaler.transform(X)
        
        # Make prediction
        churn_probability = self.model.model.predict_proba(X_scaled)[0][1]  # Probability of class 1 (churn)
        
        # Get feature importance for explanation
        feature_importance = dict(zip(self.model.feature_names, self.model.model.feature_importances_))
        top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
        
        explanation = f"Top factors: {', '.join([f'{feat}({imp:.3f})' for feat, imp in top_features])}"
        
        return Prediction(
            prediction_id=f"churn_{feature_vector.user_id}_{datetime.utcnow().isoformat()}",
            user_id=feature_vector.user_id,
            prediction_type=PredictionType.USER_CHURN,
            predicted_value=churn_probability,
            confidence=max(churn_probability, 1 - churn_probability),  # Distance from 0.5
            model_version=self.model.version,
            features_used=self.model.feature_names,
            explanation=explanation
        )

class FeatureRecommender:
    """ML-based feature recommendation system"""
    
    def __init__(self):
        self.user_feature_matrix = {}
        self.feature_similarity_matrix = {}
        self.collaborative_model = None
        self.content_features = {}
        self.logger = logging.getLogger(__name__)
    
    def build_user_feature_matrix(self, user_interactions: Dict[str, List[AnalyticsEvent]]):
        """Build user-feature interaction matrix"""
        # Extract feature usage patterns
        for user_id, events in user_interactions.items():
            interactions = [e for e in events if e.event_type == AnalyticsEventType.USER_INTERACTION]
            
            feature_scores = defaultdict(float)
            for event in interactions:
                feature_id = event.properties.get("feature_id")
                if feature_id:
                    # Score based on usage frequency, duration, and success
                    score = 1.0
                    if event.properties.get("duration"):
                        score *= min(event.properties.get("duration", 0) / 60, 3)  # Cap at 3x
                    if event.properties.get("success", True):
                        score *= 1.2
                    else:
                        score *= 0.5
                    
                    feature_scores[feature_id] += score
            
            self.user_feature_matrix[user_id] = dict(feature_scores)
    
    def calculate_feature_similarity(self):
        """Calculate feature-to-feature similarity"""
        if not self.user_feature_matrix:
            return
        
        # Get all features
        all_features = set()
        for user_features in self.user_feature_matrix.values():
            all_features.update(user_features.keys())
        
        all_features = list(all_features)
        
        # Build feature vectors (users who used each feature)
        feature_vectors = {}
        for feature in all_features:
            vector = []
            for user_id in self.user_feature_matrix.keys():
                score = self.user_feature_matrix[user_id].get(feature, 0)
                vector.append(score)
            feature_vectors[feature] = np.array(vector)
        
        # Calculate pairwise similarities
        similarity_matrix = {}
        for i, feature1 in enumerate(all_features):
            similarity_matrix[feature1] = {}
            for j, feature2 in enumerate(all_features):
                if i == j:
                    similarity_matrix[feature1][feature2] = 1.0
                else:
                    vec1 = feature_vectors[feature1]
                    vec2 = feature_vectors[feature2]
                    
                    # Use cosine similarity
                    if np.linalg.norm(vec1) > 0 and np.linalg.norm(vec2) > 0:
                        similarity = 1 - cosine(vec1, vec2)
                    else:
                        similarity = 0.0
                    
                    similarity_matrix[feature1][feature2] = similarity
        
        self.feature_similarity_matrix = similarity_matrix
    
    def recommend_features(self, user_id: str, n_recommendations: int = 5) -> List[Dict[str, Any]]:
        """Recommend features for a user"""
        if user_id not in self.user_feature_matrix:
            return []
        
        user_features = self.user_feature_matrix[user_id]
        
        # Get features user hasn't used much
        all_features = set()
        for features in self.user_feature_matrix.values():
            all_features.update(features.keys())
        
        candidate_features = [f for f in all_features if user_features.get(f, 0) < 2]
        
        if not candidate_features:
            return []
        
        # Score candidates based on similarity to user's preferred features
        feature_scores = {}
        
        for candidate in candidate_features:
            score = 0.0
            
            # Content-based scoring (similarity to used features)
            for used_feature, usage_score in user_features.items():
                if used_feature in self.feature_similarity_matrix:
                    similarity = self.feature_similarity_matrix[used_feature].get(candidate, 0)
                    score += similarity * usage_score
            
            # Collaborative filtering (what similar users liked)
            similar_users_score = self._get_collaborative_score(user_id, candidate)
            score += similar_users_score
            
            feature_scores[candidate] = score
        
        # Sort by score and return top recommendations
        recommendations = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)[:n_recommendations]
        
        return [
            {
                "feature_id": feature_id,
                "score": score,
                "reasoning": self._generate_recommendation_reasoning(user_id, feature_id)
            }
            for feature_id, score in recommendations
        ]
    
    def _get_collaborative_score(self, user_id: str, feature_id: str) -> float:
        """Get collaborative filtering score"""
        if user_id not in self.user_feature_matrix:
            return 0.0
        
        user_vector = self.user_feature_matrix[user_id]
        
        # Find similar users
        similar_users = []
        for other_user_id, other_vector in self.user_feature_matrix.items():
            if other_user_id == user_id:
                continue
            
            # Calculate user similarity
            common_features = set(user_vector.keys()) & set(other_vector.keys())
            if len(common_features) < 2:
                continue
            
            user_scores = [user_vector[f] for f in common_features]
            other_scores = [other_vector[f] for f in common_features]
            
            if len(user_scores) > 1:
                try:
                    correlation, p_value = stats.pearsonr(user_scores, other_scores)
                    if p_value < 0.05 and correlation > 0.3:
                        similar_users.append((other_user_id, correlation))
                except:
                    continue
        
        # Score based on similar users' usage
        if not similar_users:
            return 0.0
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for similar_user_id, similarity in similar_users[:10]:  # Top 10 similar users
            usage_score = self.user_feature_matrix[similar_user_id].get(feature_id, 0)
            weighted_score += usage_score * similarity
            total_weight += similarity
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _generate_recommendation_reasoning(self, user_id: str, feature_id: str) -> str:
        """Generate explanation for recommendation"""
        user_features = self.user_feature_matrix.get(user_id, {})
        
        # Find most similar features user has used
        similar_used_features = []
        if feature_id in self.feature_similarity_matrix:
            for used_feature, usage_score in user_features.items():
                if usage_score > 1:  # Significantly used
                    similarity = self.feature_similarity_matrix[feature_id].get(used_feature, 0)
                    if similarity > 0.3:
                        similar_used_features.append((used_feature, similarity))
        
        if similar_used_features:
            most_similar = max(similar_used_features, key=lambda x: x[1])
            return f"Similar to {most_similar[0]} which you use frequently (similarity: {most_similar[1]:.2f})"
        else:
            return "Popular among users with similar usage patterns"

class InterfaceOptimizer:
    """ML-based interface optimization"""
    
    def __init__(self):
        self.optimization_model = None
        self.user_preferences = {}
        self.a_b_test_results = {}
        self.logger = logging.getLogger(__name__)
    
    def learn_preferences(self, user_id: str, interface_interactions: List[Dict[str, Any]]):
        """Learn user interface preferences from interactions"""
        preferences = defaultdict(list)
        
        for interaction in interface_interactions:
            interface_config = interaction.get("interface_config", {})
            satisfaction_score = interaction.get("satisfaction_score", 0.5)
            
            # Extract interface features
            for config_key, config_value in interface_config.items():
                preferences[config_key].append((config_value, satisfaction_score))
        
        # Calculate preference scores
        user_prefs = {}
        for config_key, value_scores in preferences.items():
            if len(value_scores) > 3:  # Need minimum data
                # Group by configuration value
                value_groups = defaultdict(list)
                for value, score in value_scores:
                    value_groups[str(value)].append(score)
                
                # Find best performing configuration
                best_value = None
                best_score = 0
                
                for value, scores in value_groups.items():
                    if len(scores) >= 2:  # Minimum for meaningful average
                        avg_score = np.mean(scores)
                        if avg_score > best_score:
                            best_score = avg_score
                            best_value = value
                
                if best_value is not None:
                    user_prefs[config_key] = {
                        "preferred_value": best_value,
                        "confidence": best_score,
                        "sample_size": len(value_groups[best_value])
                    }
        
        self.user_preferences[user_id] = user_prefs
    
    def optimize_interface(self, user_id: str, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize interface configuration for user"""
        if user_id not in self.user_preferences:
            return base_config
        
        optimized_config = base_config.copy()
        user_prefs = self.user_preferences[user_id]
        
        for config_key, preference in user_prefs.items():
            if preference["confidence"] > 0.6 and preference["sample_size"] >= 3:
                # Apply user's preferred configuration
                optimized_config[config_key] = preference["preferred_value"]
                self.logger.info(f"Applied preference for {user_id}: {config_key} = {preference['preferred_value']}")
        
        return optimized_config
    
    def suggest_a_b_test(self, feature_name: str, variants: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest A/B test configuration"""
        return {
            "test_id": f"ab_test_{feature_name}_{datetime.utcnow().strftime('%Y%m%d')}",
            "feature_name": feature_name,
            "variants": variants,
            "success_metric": "user_satisfaction",
            "minimum_sample_size": 100,
            "significance_threshold": 0.05,
            "estimated_duration_days": 14
        }

class MLPredictor:
    """
    Main ML predictor that coordinates all machine learning components
    """
    
    def __init__(self):
        self.churn_predictor = ChurnPredictor()
        self.feature_recommender = FeatureRecommender()
        self.interface_optimizer = InterfaceOptimizer()
        self.feature_engineering = FeatureEngineering()
        
        self.models: Dict[str, MLModel] = {}
        self.prediction_cache: Dict[str, Prediction] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def train_models(self, training_data: Dict[str, Any]):
        """Train all ML models with provided data"""
        try:
            # Train churn prediction model
            if "churn_data" in training_data:
                churn_model = self.churn_predictor.train_model(training_data["churn_data"])
                self.models["churn_predictor"] = churn_model
                self.logger.info("Churn prediction model trained successfully")
            
            # Build feature recommendation matrices
            if "user_interactions" in training_data:
                self.feature_recommender.build_user_feature_matrix(training_data["user_interactions"])
                self.feature_recommender.calculate_feature_similarity()
                self.logger.info("Feature recommendation system initialized")
            
            # Learn interface preferences
            if "interface_interactions" in training_data:
                for user_id, interactions in training_data["interface_interactions"].items():
                    self.interface_optimizer.learn_preferences(user_id, interactions)
                self.logger.info("Interface optimization preferences learned")
            
        except Exception as e:
            self.logger.error(f"Error training ML models: {e}")
            raise
    
    async def predict_user_behavior(self, user_id: str, events: List[AnalyticsEvent]) -> Dict[str, Prediction]:
        """Generate comprehensive user behavior predictions"""
        predictions = {}
        
        try:
            # Extract features
            feature_vector = self.feature_engineering.extract_user_features(
                user_id, events, timedelta(days=30)
            )
            
            # Churn prediction
            if "churn_predictor" in self.models:
                churn_pred = self.churn_predictor.predict_churn(feature_vector)
                predictions["churn"] = churn_pred
            
            # Feature recommendations
            feature_recs = self.feature_recommender.recommend_features(user_id)
            if feature_recs:
                rec_prediction = Prediction(
                    prediction_id=f"feature_rec_{user_id}_{datetime.utcnow().isoformat()}",
                    user_id=user_id,
                    prediction_type=PredictionType.FEATURE_ADOPTION,
                    predicted_value=feature_recs,
                    confidence=0.8,
                    model_version="1.0",
                    features_used=["collaborative_filtering", "content_similarity"]
                )
                predictions["feature_recommendations"] = rec_prediction
            
            # Engagement score prediction
            engagement_pred = self._predict_engagement_score(feature_vector)
            predictions["engagement"] = engagement_pred
            
            # Error likelihood prediction
            error_pred = self._predict_error_likelihood(feature_vector)
            predictions["error_likelihood"] = error_pred
            
        except Exception as e:
            self.logger.error(f"Error predicting user behavior for {user_id}: {e}")
        
        return predictions
    
    def _predict_engagement_score(self, feature_vector: FeatureVector) -> Prediction:
        """Predict user engagement score"""
        features = feature_vector.features
        
        # Simple heuristic model (could be replaced with trained model)
        score = 50.0  # Base score
        
        # Activity frequency
        if features.get("events_per_day", 0) > 10:
            score += 20
        elif features.get("events_per_day", 0) > 5:
            score += 10
        
        # Feature diversity
        if features.get("unique_features_used", 0) > 10:
            score += 15
        elif features.get("unique_features_used", 0) > 5:
            score += 8
        
        # Success rate
        success_rate = features.get("interaction_success_rate", 0.5)
        score += (success_rate - 0.5) * 40  # -20 to +20 points
        
        # Error rate (negative impact)
        error_rate = features.get("error_rate", 0)
        score -= error_rate * 50
        
        # Help seeking (can be positive or negative)
        help_rate = features.get("help_request_rate", 0)
        if help_rate > 0.3:  # Too much help needed
            score -= 15
        elif 0.05 < help_rate < 0.15:  # Healthy help seeking
            score += 5
        
        final_score = max(0, min(100, score))
        
        return Prediction(
            prediction_id=f"engagement_{feature_vector.user_id}_{datetime.utcnow().isoformat()}",
            user_id=feature_vector.user_id,
            prediction_type=PredictionType.ENGAGEMENT_SCORE,
            predicted_value=final_score,
            confidence=0.7,
            model_version="heuristic_v1",
            features_used=["activity_frequency", "feature_diversity", "success_rate", "error_rate"]
        )
    
    def _predict_error_likelihood(self, feature_vector: FeatureVector) -> Prediction:
        """Predict likelihood of user encountering errors"""
        features = feature_vector.features
        
        # Historical error rate
        historical_error_rate = features.get("error_rate", 0)
        
        # Complexity of recent interactions
        avg_complexity = features.get("avg_complexity", 0.5)
        
        # User's success pattern
        success_rate = features.get("interaction_success_rate", 0.5)
        
        # Calculate error likelihood
        base_likelihood = historical_error_rate
        complexity_factor = avg_complexity * 0.3  # Higher complexity = more errors
        success_factor = (1 - success_rate) * 0.4  # Lower success = more errors
        
        error_likelihood = min(1.0, base_likelihood + complexity_factor + success_factor)
        
        return Prediction(
            prediction_id=f"error_{feature_vector.user_id}_{datetime.utcnow().isoformat()}",
            user_id=feature_vector.user_id,
            prediction_type=PredictionType.ERROR_LIKELIHOOD,
            predicted_value=error_likelihood,
            confidence=0.6,
            model_version="heuristic_v1",
            features_used=["historical_errors", "complexity", "success_rate"]
        )
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all ML models"""
        return {
            "models": {
                model_id: {
                    "type": model.model_type.value,
                    "prediction_type": model.prediction_type.value,
                    "accuracy": model.accuracy,
                    "training_size": model.training_data_size,
                    "last_trained": model.last_trained.isoformat(),
                    "version": model.version
                }
                for model_id, model in self.models.items()
            },
            "feature_recommender": {
                "users_in_matrix": len(self.feature_recommender.user_feature_matrix),
                "similarity_matrix_size": len(self.feature_recommender.feature_similarity_matrix)
            },
            "interface_optimizer": {
                "users_with_preferences": len(self.interface_optimizer.user_preferences)
            },
            "cache_size": len(self.prediction_cache)
        }
    
    async def retrain_models(self, new_data: Dict[str, Any]):
        """Retrain models with new data"""
        self.logger.info("Starting model retraining...")
        
        try:
            await self.train_models(new_data)
            
            # Clear prediction cache to ensure fresh predictions
            self.prediction_cache.clear()
            
            self.logger.info("Model retraining completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during model retraining: {e}")
            raise
    
    def cache_prediction(self, prediction: Prediction, ttl_hours: int = 24):
        """Cache a prediction with TTL"""
        cache_key = f"{prediction.user_id}_{prediction.prediction_type.value}"
        
        # Add expiration time to prediction metadata
        expiry_time = datetime.utcnow() + timedelta(hours=ttl_hours)
        prediction.metadata = prediction.metadata or {}
        prediction.metadata["cache_expiry"] = expiry_time.isoformat()
        
        self.prediction_cache[cache_key] = prediction
        
        # Clean expired predictions periodically
        self._clean_expired_predictions()
    
    def _clean_expired_predictions(self):
        """Remove expired predictions from cache"""
        now = datetime.utcnow()
        expired_keys = []
        
        for key, prediction in self.prediction_cache.items():
            if prediction.metadata and "cache_expiry" in prediction.metadata:
                expiry_time = datetime.fromisoformat(prediction.metadata["cache_expiry"])
                if now > expiry_time:
                    expired_keys.append(key)
        
        for key in expired_keys:
            del self.prediction_cache[key]
        
        if expired_keys:
            self.logger.info(f"Cleaned {len(expired_keys)} expired predictions from cache")