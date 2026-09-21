#!/usr/bin/env python3
"""
Advanced Analytics Engine for Adaptive UX System

This module provides comprehensive analytics including user behavior analysis,
feature adoption tracking, predictive modeling, and business intelligence
for the adaptive UX system.
"""

import asyncio
import json
import logging
import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque, Counter
import numpy as np
from scipy import stats
import pandas as pd

from interface_intelligence import ExpertiseLevel, InteractionContext
from performance_optimizer import PerformanceOptimizer, MetricType

class AnalyticsEventType(Enum):
    """Types of analytics events"""
    USER_INTERACTION = "user_interaction"
    FEATURE_ADOPTION = "feature_adoption"
    ONBOARDING_PROGRESS = "onboarding_progress"
    ERROR_OCCURRENCE = "error_occurrence"
    HELP_REQUEST = "help_request"
    CONFIGURATION_CHANGE = "configuration_change"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    GOAL_COMPLETION = "goal_completion"
    CONVERSION_EVENT = "conversion_event"

class InsightType(Enum):
    """Types of analytical insights"""
    USAGE_PATTERN = "usage_pattern"
    PERFORMANCE_TREND = "performance_trend"
    USER_SEGMENT = "user_segment"
    FEATURE_IMPACT = "feature_impact"
    PREDICTIVE_MODEL = "predictive_model"
    ANOMALY_DETECTION = "anomaly_detection"
    CONVERSION_FUNNEL = "conversion_funnel"
    RETENTION_ANALYSIS = "retention_analysis"

class MetricAggregationType(Enum):
    """Types of metric aggregations"""
    SUM = "sum"
    AVERAGE = "average"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    COUNT = "count"
    UNIQUE_COUNT = "unique_count"
    RATE = "rate"
    RATIO = "ratio"

@dataclass
class AnalyticsEvent:
    """Analytics event data structure"""
    event_id: str
    event_type: AnalyticsEventType
    user_id: str
    timestamp: datetime
    session_id: str
    properties: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class UserSegment:
    """User segment definition"""
    segment_id: str
    name: str
    description: str
    criteria: Dict[str, Any]
    user_count: int = 0
    characteristics: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class Insight:
    """Analytics insight"""
    insight_id: str
    insight_type: InsightType
    title: str
    description: str
    confidence: float
    data: Dict[str, Any]
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
@dataclass
class KPI:
    """Key Performance Indicator"""
    kpi_id: str
    name: str
    description: str
    current_value: float
    target_value: Optional[float] = None
    trend: str = "stable"  # "up", "down", "stable"
    change_percentage: float = 0.0
    unit: str = ""
    category: str = "general"

class UserBehaviorAnalyzer:
    """Analyzes user behavior patterns and segments"""
    
    def __init__(self):
        self.behavior_patterns: Dict[str, Dict[str, Any]] = {}
        self.user_segments: Dict[str, UserSegment] = {}
        self.session_data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
    def analyze_user_journey(self, user_id: str, events: List[AnalyticsEvent]) -> Dict[str, Any]:
        """Analyze a user's journey through the system"""
        if not events:
            return {"error": "No events provided"}
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        journey_analysis = {
            "user_id": user_id,
            "total_events": len(events),
            "journey_duration": (sorted_events[-1].timestamp - sorted_events[0].timestamp).total_seconds(),
            "event_types": Counter(e.event_type.value for e in events),
            "sessions": self._identify_sessions(events),
            "conversion_events": [e for e in events if e.event_type == AnalyticsEventType.CONVERSION_EVENT],
            "drop_off_points": self._identify_drop_off_points(events),
            "engagement_score": self._calculate_engagement_score(events)
        }
        
        # Add path analysis
        journey_analysis["path_analysis"] = self._analyze_user_path(events)
        
        return journey_analysis
    
    def _identify_sessions(self, events: List[AnalyticsEvent]) -> List[Dict[str, Any]]:
        """Identify user sessions from events"""
        sessions = []
        current_session = None
        session_timeout = timedelta(minutes=30)  # 30 minute session timeout
        
        for event in sorted(events, key=lambda e: e.timestamp):
            if (current_session is None or 
                event.timestamp - current_session["last_event"] > session_timeout):
                
                # Start new session
                if current_session:
                    sessions.append(current_session)
                
                current_session = {
                    "session_id": event.session_id or f"auto_{len(sessions)}",
                    "start_time": event.timestamp,
                    "last_event": event.timestamp,
                    "events": [event],
                    "event_count": 1
                }
            else:
                # Continue current session
                current_session["last_event"] = event.timestamp
                current_session["events"].append(event)
                current_session["event_count"] += 1
        
        if current_session:
            sessions.append(current_session)
        
        # Calculate session metrics
        for session in sessions:
            session["duration"] = (session["last_event"] - session["start_time"]).total_seconds()
            session["events_per_minute"] = session["event_count"] / max(session["duration"] / 60, 1)
            session["bounce"] = session["event_count"] <= 1
        
        return sessions
    
    def _identify_drop_off_points(self, events: List[AnalyticsEvent]) -> List[Dict[str, Any]]:
        """Identify points where users typically drop off"""
        drop_offs = []
        
        # Group events by type to find common sequences
        event_sequence = [e.event_type.value for e in sorted(events, key=lambda e: e.timestamp)]
        
        # Look for incomplete sequences (ending with errors or help requests)
        for i, event_type in enumerate(event_sequence[:-1]):
            next_event = event_sequence[i + 1]
            
            # Common drop-off patterns
            if (event_type == "user_interaction" and 
                next_event in ["error_occurrence", "help_request"]):
                
                drop_offs.append({
                    "sequence_index": i,
                    "trigger_event": event_type,
                    "drop_off_event": next_event,
                    "timestamp": events[i].timestamp
                })
        
        return drop_offs
    
    def _calculate_engagement_score(self, events: List[AnalyticsEvent]) -> float:
        """Calculate user engagement score based on behavior"""
        if not events:
            return 0.0
        
        score = 0.0
        
        # Session frequency (sessions per day)
        sessions = self._identify_sessions(events)
        if sessions:
            time_span_days = max((events[-1].timestamp - events[0].timestamp).days, 1)
            session_frequency = len(sessions) / time_span_days
            score += min(session_frequency * 10, 30)  # Max 30 points
        
        # Feature usage diversity
        unique_features = set()
        for event in events:
            if event.event_type == AnalyticsEventType.USER_INTERACTION:
                feature = event.properties.get("feature_id")
                if feature:
                    unique_features.add(feature)
        
        feature_diversity = min(len(unique_features) * 5, 25)  # Max 25 points
        score += feature_diversity
        
        # Goal completion rate
        interactions = [e for e in events if e.event_type == AnalyticsEventType.USER_INTERACTION]
        completions = [e for e in events if e.event_type == AnalyticsEventType.GOAL_COMPLETION]
        
        if interactions:
            completion_rate = len(completions) / len(interactions)
            score += completion_rate * 20  # Max 20 points
        
        # Help request frequency (negative impact)
        help_requests = [e for e in events if e.event_type == AnalyticsEventType.HELP_REQUEST]
        if interactions:
            help_rate = len(help_requests) / len(interactions)
            score -= help_rate * 15  # Max -15 points
        
        # Error rate (negative impact)
        errors = [e for e in events if e.event_type == AnalyticsEventType.ERROR_OCCURRENCE]
        if interactions:
            error_rate = len(errors) / len(interactions)
            score -= error_rate * 10  # Max -10 points
        
        return max(0, min(score, 100))  # Scale 0-100
    
    def _analyze_user_path(self, events: List[AnalyticsEvent]) -> Dict[str, Any]:
        """Analyze the path users take through features"""
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        # Extract feature sequence
        feature_path = []
        for event in sorted_events:
            if event.event_type == AnalyticsEventType.USER_INTERACTION:
                feature = event.properties.get("feature_id", "unknown")
                feature_path.append(feature)
        
        if len(feature_path) < 2:
            return {"message": "Insufficient path data"}
        
        # Find common transitions
        transitions = Counter()
        for i in range(len(feature_path) - 1):
            transition = (feature_path[i], feature_path[i + 1])
            transitions[transition] += 1
        
        # Calculate path efficiency
        unique_features = len(set(feature_path))
        total_interactions = len(feature_path)
        path_efficiency = unique_features / total_interactions if total_interactions > 0 else 0
        
        return {
            "path_length": len(feature_path),
            "unique_features": unique_features,
            "path_efficiency": path_efficiency,
            "most_common_transitions": transitions.most_common(5),
            "feature_sequence": feature_path[:10]  # First 10 for brevity
        }
    
    def segment_users(self, user_data: Dict[str, Dict[str, Any]]) -> Dict[str, UserSegment]:
        """Segment users based on behavior patterns"""
        segments = {}
        
        # Define segmentation criteria
        segmentation_rules = [
            {
                "id": "power_users",
                "name": "Power Users",
                "description": "Highly engaged users with advanced feature usage",
                "criteria": lambda u: (u.get("engagement_score", 0) > 80 and 
                                     u.get("feature_diversity", 0) > 15)
            },
            {
                "id": "casual_users", 
                "name": "Casual Users",
                "description": "Regular users with moderate engagement",
                "criteria": lambda u: (30 <= u.get("engagement_score", 0) <= 80 and
                                     5 <= u.get("feature_diversity", 0) <= 15)
            },
            {
                "id": "struggling_users",
                "name": "Struggling Users", 
                "description": "Users who need more help and support",
                "criteria": lambda u: (u.get("help_request_rate", 0) > 0.2 or
                                     u.get("error_rate", 0) > 0.15)
            },
            {
                "id": "new_users",
                "name": "New Users",
                "description": "Recently joined users still learning",
                "criteria": lambda u: (u.get("days_since_first_session", 0) <= 7 and
                                     u.get("session_count", 0) <= 5)
            },
            {
                "id": "churning_users",
                "name": "At-Risk Users",
                "description": "Users showing signs of churn",
                "criteria": lambda u: (u.get("days_since_last_session", 0) > 14 and
                                     u.get("engagement_score", 0) < 30)
            }
        ]
        
        # Apply segmentation rules
        for rule in segmentation_rules:
            matching_users = [
                user_id for user_id, data in user_data.items()
                if rule["criteria"](data)
            ]
            
            if matching_users:
                segment = UserSegment(
                    segment_id=rule["id"],
                    name=rule["name"],
                    description=rule["description"],
                    criteria={"rule": rule["criteria"].__name__},
                    user_count=len(matching_users)
                )
                
                # Calculate segment characteristics
                segment.characteristics = self._calculate_segment_characteristics(
                    [user_data[uid] for uid in matching_users]
                )
                
                segments[rule["id"]] = segment
        
        return segments
    
    def _calculate_segment_characteristics(self, segment_users: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate characteristics of a user segment"""
        if not segment_users:
            return {}
        
        characteristics = {}
        
        # Numerical characteristics
        numerical_fields = [
            "engagement_score", "feature_diversity", "session_count", 
            "help_request_rate", "error_rate", "conversion_rate"
        ]
        
        for field in numerical_fields:
            values = [user.get(field, 0) for user in segment_users]
            if values:
                characteristics[field] = {
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values)
                }
        
        # Categorical characteristics
        device_types = Counter(user.get("device_type", "unknown") for user in segment_users)
        characteristics["device_distribution"] = dict(device_types.most_common())
        
        expertise_levels = Counter(user.get("expertise_level", "unknown") for user in segment_users)
        characteristics["expertise_distribution"] = dict(expertise_levels.most_common())
        
        return characteristics

class FeatureAdoptionTracker:
    """Tracks feature adoption and usage patterns"""
    
    def __init__(self):
        self.feature_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_users": set(),
            "active_users": set(),
            "first_use_dates": [],
            "usage_frequency": defaultdict(int),
            "user_segments": defaultdict(set)
        })
    
    def track_feature_usage(self, user_id: str, feature_id: str, 
                          timestamp: datetime, user_segment: str = None):
        """Track feature usage event"""
        metrics = self.feature_metrics[feature_id]
        
        # Track users
        metrics["total_users"].add(user_id)
        
        # Track active users (used in last 30 days)
        cutoff = datetime.utcnow() - timedelta(days=30)
        if timestamp > cutoff:
            metrics["active_users"].add(user_id)
        
        # Track first uses
        user_key = f"{user_id}_first_use"
        if user_key not in metrics:
            metrics["first_use_dates"].append(timestamp)
            metrics[user_key] = True
        
        # Track usage frequency
        metrics["usage_frequency"][user_id] += 1
        
        # Track by segment
        if user_segment:
            metrics["user_segments"][user_segment].add(user_id)
    
    def calculate_adoption_metrics(self, feature_id: str, total_users: int) -> Dict[str, Any]:
        """Calculate adoption metrics for a feature"""
        metrics = self.feature_metrics[feature_id]
        
        if not metrics["total_users"]:
            return {"error": "No usage data for feature"}
        
        adoption_rate = len(metrics["total_users"]) / total_users if total_users > 0 else 0
        retention_rate = len(metrics["active_users"]) / len(metrics["total_users"]) if metrics["total_users"] else 0
        
        # Calculate adoption curve
        first_uses_by_week = self._group_by_time_period(metrics["first_use_dates"], "week")
        
        # Calculate usage intensity
        usage_frequencies = list(metrics["usage_frequency"].values())
        avg_usage_per_user = statistics.mean(usage_frequencies) if usage_frequencies else 0
        
        return {
            "feature_id": feature_id,
            "adoption_rate": adoption_rate,
            "retention_rate": retention_rate,
            "total_adopters": len(metrics["total_users"]),
            "active_users": len(metrics["active_users"]),
            "average_usage_per_user": avg_usage_per_user,
            "adoption_curve": first_uses_by_week,
            "usage_distribution": Counter(usage_frequencies),
            "segment_adoption": {
                segment: len(users) for segment, users in metrics["user_segments"].items()
            }
        }
    
    def _group_by_time_period(self, timestamps: List[datetime], period: str = "week") -> Dict[str, int]:
        """Group timestamps by time period"""
        grouped = defaultdict(int)
        
        for ts in timestamps:
            if period == "week":
                # Get start of week
                week_start = ts - timedelta(days=ts.weekday())
                key = week_start.strftime("%Y-W%U")
            elif period == "month":
                key = ts.strftime("%Y-%m")
            elif period == "day":
                key = ts.strftime("%Y-%m-%d")
            else:
                key = str(ts.date())
            
            grouped[key] += 1
        
        return dict(grouped)
    
    def get_feature_comparison(self, feature_ids: List[str], total_users: int) -> Dict[str, Any]:
        """Compare adoption metrics across multiple features"""
        comparisons = {}
        
        for feature_id in feature_ids:
            metrics = self.calculate_adoption_metrics(feature_id, total_users)
            if "error" not in metrics:
                comparisons[feature_id] = {
                    "adoption_rate": metrics["adoption_rate"],
                    "retention_rate": metrics["retention_rate"],
                    "usage_intensity": metrics["average_usage_per_user"]
                }
        
        if not comparisons:
            return {"error": "No valid feature data"}
        
        # Find best and worst performers
        best_adoption = max(comparisons.items(), key=lambda x: x[1]["adoption_rate"])
        best_retention = max(comparisons.items(), key=lambda x: x[1]["retention_rate"])
        
        return {
            "feature_comparison": comparisons,
            "insights": {
                "best_adoption": {"feature": best_adoption[0], "rate": best_adoption[1]["adoption_rate"]},
                "best_retention": {"feature": best_retention[0], "rate": best_retention[1]["retention_rate"]},
                "total_features_compared": len(comparisons)
            }
        }

class PredictiveAnalytics:
    """Predictive analytics for user behavior and system optimization"""
    
    def __init__(self):
        self.models = {}
        self.prediction_cache = {}
    
    def predict_user_churn(self, user_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Predict likelihood of user churn"""
        # Simple heuristic-based model (could be replaced with ML model)
        churn_indicators = {
            "days_since_last_session": user_metrics.get("days_since_last_session", 0),
            "engagement_score": user_metrics.get("engagement_score", 50),
            "error_rate": user_metrics.get("error_rate", 0),
            "help_request_rate": user_metrics.get("help_request_rate", 0),
            "feature_adoption_rate": user_metrics.get("feature_adoption_rate", 0)
        }
        
        # Calculate churn probability
        churn_score = 0
        
        # Days since last session (strong indicator)
        if churn_indicators["days_since_last_session"] > 30:
            churn_score += 40
        elif churn_indicators["days_since_last_session"] > 14:
            churn_score += 25
        elif churn_indicators["days_since_last_session"] > 7:
            churn_score += 10
        
        # Low engagement
        if churn_indicators["engagement_score"] < 20:
            churn_score += 30
        elif churn_indicators["engagement_score"] < 40:
            churn_score += 15
        
        # High error rate
        if churn_indicators["error_rate"] > 0.2:
            churn_score += 20
        elif churn_indicators["error_rate"] > 0.1:
            churn_score += 10
        
        # Low feature adoption
        if churn_indicators["feature_adoption_rate"] < 0.1:
            churn_score += 15
        
        churn_probability = min(churn_score / 100, 1.0)
        
        # Determine risk level
        if churn_probability > 0.7:
            risk_level = "high"
        elif churn_probability > 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "churn_probability": churn_probability,
            "risk_level": risk_level,
            "contributing_factors": [
                factor for factor, value in churn_indicators.items()
                if self._is_churn_factor(factor, value)
            ],
            "recommendations": self._get_churn_prevention_recommendations(risk_level, churn_indicators)
        }
    
    def _is_churn_factor(self, factor: str, value: Any) -> bool:
        """Check if a factor contributes to churn risk"""
        thresholds = {
            "days_since_last_session": 7,
            "engagement_score": 40,
            "error_rate": 0.1,
            "help_request_rate": 0.15,
            "feature_adoption_rate": 0.2
        }
        
        threshold = thresholds.get(factor)
        if threshold is None:
            return False
        
        if factor in ["days_since_last_session", "error_rate", "help_request_rate"]:
            return value > threshold
        else:
            return value < threshold
    
    def _get_churn_prevention_recommendations(self, risk_level: str, 
                                            indicators: Dict[str, Any]) -> List[str]:
        """Get recommendations to prevent churn"""
        recommendations = []
        
        if risk_level == "high":
            recommendations.append("Immediate outreach with personalized re-engagement campaign")
            recommendations.append("Offer one-on-one support session")
        
        if indicators.get("engagement_score", 50) < 30:
            recommendations.append("Suggest features aligned with user's goals")
            recommendations.append("Provide gamification elements to boost engagement")
        
        if indicators.get("error_rate", 0) > 0.1:
            recommendations.append("Proactive error detection and prevention")
            recommendations.append("Enhanced onboarding for problem areas")
        
        if indicators.get("help_request_rate", 0) > 0.15:
            recommendations.append("Improve contextual help and documentation")
            recommendations.append("Consider interface simplification")
        
        if indicators.get("feature_adoption_rate", 0) < 0.2:
            recommendations.append("Progressive disclosure of relevant features")
            recommendations.append("Targeted feature introduction tutorials")
        
        return recommendations
    
    def predict_feature_success(self, feature_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Predict likelihood of feature success"""
        # Analyze feature characteristics
        adoption_velocity = feature_metrics.get("adoption_velocity", 0)  # Users/day
        user_satisfaction = feature_metrics.get("user_satisfaction", 0.5)  # 0-1 score
        usage_retention = feature_metrics.get("usage_retention", 0.5)  # 0-1 score
        complexity_score = feature_metrics.get("complexity_score", 0.5)  # 0-1 score
        
        # Calculate success probability
        success_factors = {
            "adoption_velocity": min(adoption_velocity / 10, 1.0) * 25,  # Max 25 points
            "user_satisfaction": user_satisfaction * 30,  # Max 30 points
            "usage_retention": usage_retention * 25,  # Max 25 points
            "simplicity": (1 - complexity_score) * 20  # Max 20 points (simpler = better)
        }
        
        success_score = sum(success_factors.values())
        success_probability = success_score / 100
        
        # Determine success level
        if success_probability > 0.8:
            success_level = "high"
        elif success_probability > 0.6:
            success_level = "medium"
        else:
            success_level = "low"
        
        return {
            "success_probability": success_probability,
            "success_level": success_level,
            "success_factors": success_factors,
            "recommendations": self._get_feature_improvement_recommendations(success_factors)
        }
    
    def _get_feature_improvement_recommendations(self, factors: Dict[str, float]) -> List[str]:
        """Get recommendations to improve feature success"""
        recommendations = []
        
        if factors.get("adoption_velocity", 0) < 15:
            recommendations.append("Improve feature discoverability")
            recommendations.append("Add feature promotion in key user flows")
        
        if factors.get("user_satisfaction", 0) < 20:
            recommendations.append("Conduct user research to identify pain points")
            recommendations.append("Improve feature usability and design")
        
        if factors.get("usage_retention", 0) < 15:
            recommendations.append("Add progressive onboarding for feature")
            recommendations.append("Improve feature stickiness with better integration")
        
        if factors.get("simplicity", 0) < 15:
            recommendations.append("Simplify feature interface and workflow")
            recommendations.append("Consider breaking complex feature into simpler parts")
        
        return recommendations

class AnalyticsEngine:
    """
    Main analytics engine that coordinates all analytics components
    """
    
    def __init__(self, performance_optimizer: PerformanceOptimizer):
        self.performance_optimizer = performance_optimizer
        self.behavior_analyzer = UserBehaviorAnalyzer()
        self.adoption_tracker = FeatureAdoptionTracker()
        self.predictive_analytics = PredictiveAnalytics()
        
        self.events: deque = deque(maxlen=100000)  # Store recent events
        self.insights_cache: Dict[str, Insight] = {}
        self.kpis: Dict[str, KPI] = {}
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize KPIs
        self._initialize_kpis()
    
    def _initialize_kpis(self):
        """Initialize key performance indicators"""
        self.kpis = {
            "user_engagement": KPI(
                "user_engagement", "User Engagement Score", 
                "Average engagement score across all users",
                0.0, 75.0, category="user_experience"
            ),
            "feature_adoption_rate": KPI(
                "feature_adoption_rate", "Feature Adoption Rate",
                "Percentage of users adopting new features",
                0.0, 0.6, unit="%", category="product"
            ),
            "churn_rate": KPI(
                "churn_rate", "User Churn Rate",
                "Percentage of users at risk of churning",
                0.0, 0.05, unit="%", category="retention"
            ),
            "error_rate": KPI(
                "error_rate", "System Error Rate",
                "Percentage of interactions resulting in errors",
                0.0, 0.02, unit="%", category="performance"
            ),
            "help_request_rate": KPI(
                "help_request_rate", "Help Request Rate",
                "Percentage of sessions with help requests",
                0.0, 0.1, unit="%", category="user_experience"
            )
        }
    
    async def track_event(self, event: AnalyticsEvent):
        """Track an analytics event"""
        self.events.append(event)
        
        # Update feature adoption tracking
        if event.event_type == AnalyticsEventType.USER_INTERACTION:
            feature_id = event.properties.get("feature_id")
            if feature_id:
                user_segment = event.context.get("user_segment")
                self.adoption_tracker.track_feature_usage(
                    event.user_id, feature_id, event.timestamp, user_segment
                )
        
        # Batch process for performance
        self.performance_optimizer.batch_operation("analytics", asdict(event))
        
        # Trigger real-time insights for critical events
        if event.event_type in [AnalyticsEventType.ERROR_OCCURRENCE, 
                               AnalyticsEventType.CONVERSION_EVENT]:
            await self._generate_realtime_insights(event)
    
    async def _generate_realtime_insights(self, event: AnalyticsEvent):
        """Generate real-time insights for critical events"""
        try:
            if event.event_type == AnalyticsEventType.ERROR_OCCURRENCE:
                # Check for error patterns
                recent_errors = [
                    e for e in list(self.events)[-100:]  # Last 100 events
                    if (e.event_type == AnalyticsEventType.ERROR_OCCURRENCE and
                        e.user_id == event.user_id and
                        (event.timestamp - e.timestamp).total_seconds() < 3600)  # Last hour
                ]
                
                if len(recent_errors) >= 3:
                    insight = Insight(
                        insight_id=f"error_pattern_{event.user_id}_{datetime.utcnow().isoformat()}",
                        insight_type=InsightType.ANOMALY_DETECTION,
                        title="Frequent Errors Detected",
                        description=f"User {event.user_id} experienced {len(recent_errors)} errors in the last hour",
                        confidence=0.9,
                        data={"error_count": len(recent_errors), "user_id": event.user_id},
                        recommendations=["Provide proactive assistance", "Review user's workflow"]
                    )
                    
                    self.insights_cache[insight.insight_id] = insight
                    self.logger.warning(f"Real-time insight generated: {insight.title}")
        
        except Exception as e:
            self.logger.error(f"Error generating real-time insights: {e}")
    
    async def generate_insights(self, time_window: timedelta = None) -> List[Insight]:
        """Generate analytical insights"""
        insights = []
        
        # Filter events by time window
        cutoff = datetime.utcnow() - time_window if time_window else None
        relevant_events = [
            e for e in self.events
            if cutoff is None or e.timestamp > cutoff
        ]
        
        if not relevant_events:
            return insights
        
        # Group events by user
        events_by_user = defaultdict(list)
        for event in relevant_events:
            events_by_user[event.user_id].append(event)
        
        # Generate user behavior insights
        for user_id, user_events in events_by_user.items():
            if len(user_events) >= 10:  # Minimum events for analysis
                journey_analysis = self.behavior_analyzer.analyze_user_journey(user_id, user_events)
                
                # Generate insights based on journey analysis
                if journey_analysis.get("engagement_score", 0) < 30:
                    insight = Insight(
                        insight_id=f"low_engagement_{user_id}",
                        insight_type=InsightType.USER_SEGMENT,
                        title=f"Low Engagement Detected",
                        description=f"User {user_id} shows low engagement (score: {journey_analysis.get('engagement_score', 0):.1f})",
                        confidence=0.8,
                        data=journey_analysis,
                        recommendations=[
                            "Offer personalized assistance",
                            "Simplify user interface",
                            "Provide guided tutorials"
                        ]
                    )
                    insights.append(insight)
        
        # Generate feature adoption insights
        feature_usage = defaultdict(set)
        for event in relevant_events:
            if event.event_type == AnalyticsEventType.USER_INTERACTION:
                feature_id = event.properties.get("feature_id")
                if feature_id:
                    feature_usage[feature_id].add(event.user_id)
        
        total_users = len(events_by_user)
        for feature_id, users in feature_usage.items():
            adoption_rate = len(users) / total_users if total_users > 0 else 0
            
            if adoption_rate < 0.1:  # Less than 10% adoption
                insight = Insight(
                    insight_id=f"low_adoption_{feature_id}",
                    insight_type=InsightType.FEATURE_IMPACT,
                    title=f"Low Feature Adoption: {feature_id}",
                    description=f"Feature {feature_id} has only {adoption_rate:.1%} adoption rate",
                    confidence=0.9,
                    data={"feature_id": feature_id, "adoption_rate": adoption_rate, "user_count": len(users)},
                    recommendations=[
                        "Review feature discoverability",
                        "Improve feature onboarding",
                        "Consider feature redesign"
                    ]
                )
                insights.append(insight)
        
        return insights
    
    async def update_kpis(self):
        """Update KPI values based on recent data"""
        try:
            # Get recent events (last 24 hours)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_events = [e for e in self.events if e.timestamp > cutoff]
            
            if not recent_events:
                return
            
            # Group by user
            events_by_user = defaultdict(list)
            for event in recent_events:
                events_by_user[event.user_id].append(event)
            
            # Calculate engagement scores
            engagement_scores = []
            for user_id, user_events in events_by_user.items():
                if len(user_events) >= 3:  # Minimum for meaningful analysis
                    journey = self.behavior_analyzer.analyze_user_journey(user_id, user_events)
                    engagement_scores.append(journey.get("engagement_score", 0))
            
            if engagement_scores:
                avg_engagement = statistics.mean(engagement_scores)
                self._update_kpi("user_engagement", avg_engagement)
            
            # Calculate error rate
            interactions = [e for e in recent_events if e.event_type == AnalyticsEventType.USER_INTERACTION]
            errors = [e for e in recent_events if e.event_type == AnalyticsEventType.ERROR_OCCURRENCE]
            
            if interactions:
                error_rate = len(errors) / len(interactions)
                self._update_kpi("error_rate", error_rate)
            
            # Calculate help request rate
            sessions = set(e.session_id for e in recent_events if e.session_id)
            help_sessions = set(
                e.session_id for e in recent_events 
                if e.event_type == AnalyticsEventType.HELP_REQUEST and e.session_id
            )
            
            if sessions:
                help_rate = len(help_sessions) / len(sessions)
                self._update_kpi("help_request_rate", help_rate)
            
            # Calculate feature adoption (new features adopted in last week)
            week_ago = datetime.utcnow() - timedelta(days=7)
            new_adoptions = set()
            
            for event in recent_events:
                if (event.event_type == AnalyticsEventType.FEATURE_ADOPTION and
                    event.timestamp > week_ago):
                    new_adoptions.add(event.user_id)
            
            total_active_users = len(events_by_user)
            if total_active_users > 0:
                adoption_rate = len(new_adoptions) / total_active_users
                self._update_kpi("feature_adoption_rate", adoption_rate)
            
        except Exception as e:
            self.logger.error(f"Error updating KPIs: {e}")
    
    def _update_kpi(self, kpi_id: str, new_value: float):
        """Update a KPI with trend analysis"""
        if kpi_id not in self.kpis:
            return
        
        kpi = self.kpis[kpi_id]
        old_value = kpi.current_value
        
        # Calculate change
        if old_value > 0:
            change_percentage = ((new_value - old_value) / old_value) * 100
        else:
            change_percentage = 0
        
        # Determine trend
        if abs(change_percentage) < 5:  # Less than 5% change
            trend = "stable"
        elif change_percentage > 0:
            trend = "up"
        else:
            trend = "down"
        
        # Update KPI
        kpi.current_value = new_value
        kpi.change_percentage = change_percentage
        kpi.trend = trend
        
        self.logger.info(f"KPI updated: {kpi_id} = {new_value:.3f} ({trend}, {change_percentage:+.1f}%)")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        return {
            "kpis": {kpi_id: asdict(kpi) for kpi_id, kpi in self.kpis.items()},
            "recent_insights": [
                asdict(insight) for insight in 
                sorted(self.insights_cache.values(), key=lambda i: i.created_at, reverse=True)[:10]
            ],
            "system_health": self.performance_optimizer.get_performance_summary(),
            "event_summary": {
                "total_events": len(self.events),
                "events_last_hour": len([
                    e for e in self.events 
                    if (datetime.utcnow() - e.timestamp).total_seconds() < 3600
                ]),
                "unique_users_today": len(set(
                    e.user_id for e in self.events
                    if (datetime.utcnow() - e.timestamp).total_seconds() < 86400
                ))
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics for a specific user"""
        user_events = [e for e in self.events if e.user_id == user_id]
        
        if not user_events:
            return {"error": "No data found for user"}
        
        # Basic journey analysis
        journey = self.behavior_analyzer.analyze_user_journey(user_id, user_events)
        
        # Churn prediction
        user_metrics = {
            "days_since_last_session": (datetime.utcnow() - max(e.timestamp for e in user_events)).days,
            "engagement_score": journey.get("engagement_score", 0),
            "error_rate": len([e for e in user_events if e.event_type == AnalyticsEventType.ERROR_OCCURRENCE]) / len(user_events),
            "help_request_rate": len([e for e in user_events if e.event_type == AnalyticsEventType.HELP_REQUEST]) / len(user_events)
        }
        
        churn_prediction = self.predictive_analytics.predict_user_churn(user_metrics)
        
        return {
            "user_id": user_id,
            "journey_analysis": journey,
            "churn_prediction": churn_prediction,
            "event_summary": {
                "total_events": len(user_events),
                "first_seen": min(e.timestamp for e in user_events).isoformat(),
                "last_seen": max(e.timestamp for e in user_events).isoformat(),
                "event_types": dict(Counter(e.event_type.value for e in user_events))
            }
        }