"""
ActiveLog Health Integration - Stress Management and Recommendations

This module provides comprehensive stress monitoring and management capabilities including:
- Multi-modal stress detection (heart rate variability, cortisol, self-reports)
- Personalized stress management recommendations and interventions
- Real-time stress monitoring and alerts
- Guided meditation and breathing exercise integration
- Stress pattern analysis and triggers identification
- Biofeedback and mindfulness training
- Integration with calendar and activity tracking
- Workplace stress management and break reminders
"""

import asyncio
import json
import logging
import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from scipy import signal
from scipy.stats import pearsonr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StressLevel(Enum):
    """Stress level classifications"""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class StressSource(Enum):
    """Common sources of stress"""
    WORK = "work"
    RELATIONSHIPS = "relationships"
    FINANCES = "finances"
    HEALTH = "health"
    FAMILY = "family"
    ENVIRONMENT = "environment"
    TECHNOLOGY = "technology"
    TRAFFIC = "traffic"
    DEADLINES = "deadlines"
    SOCIAL = "social"
    UNKNOWN = "unknown"


class StressSymptom(Enum):
    """Physical and psychological stress symptoms"""
    HEADACHE = "headache"
    MUSCLE_TENSION = "muscle_tension"
    FATIGUE = "fatigue"
    IRRITABILITY = "irritability"
    ANXIETY = "anxiety"
    DIFFICULTY_CONCENTRATING = "difficulty_concentrating"
    SLEEP_PROBLEMS = "sleep_problems"
    APPETITE_CHANGES = "appetite_changes"
    RESTLESSNESS = "restlessness"
    MOOD_SWINGS = "mood_swings"
    RACING_THOUGHTS = "racing_thoughts"
    DIGESTIVE_ISSUES = "digestive_issues"


class InterventionType(Enum):
    """Types of stress management interventions"""
    BREATHING_EXERCISE = "breathing_exercise"
    MEDITATION = "meditation"
    PHYSICAL_ACTIVITY = "physical_activity"
    PROGRESSIVE_RELAXATION = "progressive_relaxation"
    MINDFULNESS = "mindfulness"
    COGNITIVE_RESTRUCTURING = "cognitive_restructuring"
    TIME_MANAGEMENT = "time_management"
    BREAK_REMINDER = "break_reminder"
    ENVIRONMENT_CHANGE = "environment_change"
    SOCIAL_SUPPORT = "social_support"


class StressMeasurementType(Enum):
    """Types of stress measurements"""
    HEART_RATE_VARIABILITY = "heart_rate_variability"
    CORTISOL_LEVEL = "cortisol_level"
    SELF_REPORT = "self_report"
    BEHAVIORAL_MARKERS = "behavioral_markers"
    VOICE_ANALYSIS = "voice_analysis"
    SLEEP_DISRUPTION = "sleep_disruption"
    ACTIVITY_PATTERN = "activity_pattern"


class RecommendationUrgency(Enum):
    """Urgency levels for stress management recommendations"""
    IMMEDIATE = "immediate"
    SOON = "soon"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class StressMeasurement:
    """Individual stress measurement data point"""
    measurement_id: str
    user_id: str
    measurement_type: StressMeasurementType
    value: float
    unit: str
    stress_level: StressLevel
    confidence: float  # 0-1 confidence in the measurement
    context: Dict[str, Any] = field(default_factory=dict)
    location: Optional[str] = None
    activity: Optional[str] = None
    measured_at: datetime = field(default_factory=datetime.now)


@dataclass
class StressEvent:
    """Stress event or episode"""
    event_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    peak_stress_level: StressLevel
    average_stress_level: StressLevel
    stress_sources: List[StressSource]
    symptoms: List[StressSymptom]
    measurements: List[StressMeasurement]
    triggers: List[str] = field(default_factory=list)
    interventions_used: List[str] = field(default_factory=list)
    resolution_method: Optional[str] = None
    notes: Optional[str] = None
    recovery_time: Optional[float] = None  # minutes


@dataclass
class StressPattern:
    """Stress pattern analysis over time"""
    pattern_id: str
    user_id: str
    analysis_period: str  # "7d", "30d", "90d"
    average_stress_level: float
    stress_variability: float
    peak_stress_times: List[time]  # Times of day when stress peaks
    low_stress_times: List[time]
    common_triggers: List[Tuple[StressSource, float]]  # (source, frequency)
    stress_by_day_of_week: Dict[str, float]
    stress_by_activity: Dict[str, float]
    recovery_patterns: Dict[str, float]
    chronic_stress_indicators: List[str]
    resilience_score: float  # 0-100
    analyzed_at: datetime = field(default_factory=datetime.now)


@dataclass
class StressRecommendation:
    """Personalized stress management recommendation"""
    recommendation_id: str
    user_id: str
    intervention_type: InterventionType
    title: str
    description: str
    instructions: List[str]
    duration_minutes: int
    urgency: RecommendationUrgency
    effectiveness_score: float  # Based on user's past responses
    triggers: List[StressSource]  # When to use this recommendation
    prerequisites: List[str] = field(default_factory=list)
    resources: List[Dict[str, str]] = field(default_factory=list)  # Links, apps, etc.
    personalization_factors: Dict[str, Any] = field(default_factory=dict)
    success_rate: Optional[float] = None
    last_suggested: Optional[datetime] = None
    times_used: int = 0
    average_rating: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class InterventionSession:
    """Record of a stress intervention session"""
    session_id: str
    user_id: str
    recommendation_id: str
    intervention_type: InterventionType
    start_time: datetime
    end_time: Optional[datetime] = None
    completed: bool = False
    pre_stress_level: Optional[float] = None
    post_stress_level: Optional[float] = None
    user_rating: Optional[int] = None  # 1-5 scale
    notes: Optional[str] = None
    effectiveness: Optional[float] = None
    side_effects: List[str] = field(default_factory=list)


@dataclass
class StressAlert:
    """Stress level alert for high stress situations"""
    alert_id: str
    user_id: str
    alert_level: StressLevel
    trigger_measurement: StressMeasurement
    suggested_interventions: List[StressRecommendation]
    alert_time: datetime
    acknowledged: bool = False
    action_taken: Optional[str] = None
    resolved_at: Optional[datetime] = None


@dataclass
class BiofeedbackSession:
    """Biofeedback training session data"""
    session_id: str
    user_id: str
    session_type: str  # "hrv_training", "breathing", "meditation"
    duration_minutes: int
    baseline_metrics: Dict[str, float]
    target_metrics: Dict[str, float]
    achieved_metrics: Dict[str, float]
    improvement_score: float
    difficulty_level: int  # 1-10
    user_engagement: float  # 0-100
    session_quality: str  # "excellent", "good", "fair", "poor"
    started_at: datetime
    completed_at: Optional[datetime] = None


@dataclass
class MindfulnessActivity:
    """Mindfulness and meditation activity"""
    activity_id: str
    user_id: str
    activity_type: str  # "meditation", "breathing", "body_scan", "mindful_walking"
    guided: bool
    duration_minutes: int
    focus_quality: Optional[int] = None  # 1-10 scale
    distractions: int = 0
    pre_mood: Optional[int] = None  # 1-10 scale
    post_mood: Optional[int] = None
    environment: Optional[str] = None
    instructor: Optional[str] = None
    completed_at: datetime = field(default_factory=datetime.now)


class StressDetector(ABC):
    """Abstract interface for stress detection implementations"""
    
    @abstractmethod
    async def detect_stress(self, user_id: str, measurement_data: Dict[str, Any]) -> StressMeasurement:
        """Detect stress level from measurement data"""
        pass
    
    @abstractmethod
    async def analyze_patterns(self, measurements: List[StressMeasurement]) -> Dict[str, Any]:
        """Analyze stress patterns from measurements"""
        pass
    
    @abstractmethod
    async def predict_stress_episode(self, user_id: str, current_context: Dict[str, Any]) -> float:
        """Predict likelihood of stress episode"""
        pass


class RecommendationEngine(ABC):
    """Abstract interface for stress management recommendations"""
    
    @abstractmethod
    async def generate_recommendations(self, user_id: str, current_stress: StressLevel,
                                     context: Dict[str, Any]) -> List[StressRecommendation]:
        """Generate personalized stress management recommendations"""
        pass
    
    @abstractmethod
    async def prioritize_recommendations(self, recommendations: List[StressRecommendation]) -> List[StressRecommendation]:
        """Prioritize recommendations based on effectiveness and context"""
        pass
    
    @abstractmethod
    async def adapt_recommendations(self, user_id: str, feedback: List[InterventionSession]) -> None:
        """Adapt recommendations based on user feedback and effectiveness"""
        pass


class InterventionProvider(ABC):
    """Abstract interface for stress intervention delivery"""
    
    @abstractmethod
    async def deliver_intervention(self, intervention: StressRecommendation, user_context: Dict[str, Any]) -> InterventionSession:
        """Deliver a stress management intervention"""
        pass
    
    @abstractmethod
    async def track_progress(self, session: InterventionSession) -> Dict[str, Any]:
        """Track progress during intervention"""
        pass
    
    @abstractmethod
    async def provide_guidance(self, intervention_type: InterventionType, user_level: str) -> Dict[str, Any]:
        """Provide guidance for intervention execution"""
        pass


class MultiModalStressDetector(StressDetector):
    """Multi-modal stress detection using various physiological and behavioral signals"""
    
    def __init__(self):
        self.hrv_model = None  # Would be trained ML model
        self.behavioral_model = None
        self.baseline_metrics: Dict[str, Dict[str, float]] = {}
        
        # Stress level thresholds (would be personalized)
        self.thresholds = {
            StressMeasurementType.HEART_RATE_VARIABILITY: {
                StressLevel.VERY_LOW: 50,
                StressLevel.LOW: 40,
                StressLevel.MODERATE: 30,
                StressLevel.HIGH: 20,
                StressLevel.VERY_HIGH: 10
            },
            StressMeasurementType.CORTISOL_LEVEL: {
                StressLevel.VERY_LOW: 5,
                StressLevel.LOW: 10,
                StressLevel.MODERATE: 15,
                StressLevel.HIGH: 25,
                StressLevel.VERY_HIGH: 35
            }
        }
    
    async def detect_stress(self, user_id: str, measurement_data: Dict[str, Any]) -> StressMeasurement:
        """Detect stress level from multi-modal data"""
        try:
            stress_scores = []
            confidence_scores = []
            
            # Heart Rate Variability analysis
            if 'hrv' in measurement_data:
                hrv_stress, hrv_confidence = await self._analyze_hrv(user_id, measurement_data['hrv'])
                stress_scores.append(hrv_stress)
                confidence_scores.append(hrv_confidence)
            
            # Cortisol level analysis
            if 'cortisol' in measurement_data:
                cortisol_stress, cortisol_confidence = await self._analyze_cortisol(measurement_data['cortisol'])
                stress_scores.append(cortisol_stress)
                confidence_scores.append(cortisol_confidence)
            
            # Behavioral markers analysis
            if 'behavior' in measurement_data:
                behavior_stress, behavior_confidence = await self._analyze_behavior(user_id, measurement_data['behavior'])
                stress_scores.append(behavior_stress)
                confidence_scores.append(behavior_confidence)
            
            # Self-report data
            if 'self_report' in measurement_data:
                self_report_stress = measurement_data['self_report']
                stress_scores.append(self_report_stress)
                confidence_scores.append(0.9)  # High confidence in self-reports
            
            # Combine scores using weighted average
            if stress_scores:
                weights = np.array(confidence_scores)
                weights = weights / weights.sum()
                final_stress_score = np.average(stress_scores, weights=weights)
                final_confidence = np.mean(confidence_scores)
            else:
                final_stress_score = 50.0  # Default moderate stress
                final_confidence = 0.1
            
            # Convert to stress level
            stress_level = await self._score_to_level(final_stress_score)
            
            return StressMeasurement(
                measurement_id=str(uuid4()),
                user_id=user_id,
                measurement_type=StressMeasurementType.SELF_REPORT,
                value=final_stress_score,
                unit="stress_score",
                stress_level=stress_level,
                confidence=final_confidence,
                context=measurement_data
            )
            
        except Exception as e:
            logger.error(f"Error detecting stress: {e}")
            return StressMeasurement(
                measurement_id=str(uuid4()),
                user_id=user_id,
                measurement_type=StressMeasurementType.SELF_REPORT,
                value=50.0,
                unit="stress_score",
                stress_level=StressLevel.MODERATE,
                confidence=0.1
            )
    
    async def analyze_patterns(self, measurements: List[StressMeasurement]) -> Dict[str, Any]:
        """Analyze stress patterns from measurements"""
        if not measurements:
            return {}
        
        # Extract stress values and times
        stress_values = [m.value for m in measurements]
        times = [m.measured_at for m in measurements]
        
        # Basic statistics
        avg_stress = statistics.mean(stress_values)
        stress_variability = statistics.stdev(stress_values) if len(stress_values) > 1 else 0
        
        # Time-based patterns
        hourly_stress = {}
        for measurement in measurements:
            hour = measurement.measured_at.hour
            if hour not in hourly_stress:
                hourly_stress[hour] = []
            hourly_stress[hour].append(measurement.value)
        
        # Calculate hourly averages
        hourly_averages = {hour: statistics.mean(values) for hour, values in hourly_stress.items()}
        
        # Find peak and low stress times
        peak_hours = [hour for hour, avg in hourly_averages.items() if avg > avg_stress + stress_variability]
        low_hours = [hour for hour, avg in hourly_averages.items() if avg < avg_stress - stress_variability]
        
        # Day of week analysis
        daily_stress = {}
        for measurement in measurements:
            day = measurement.measured_at.strftime('%A')
            if day not in daily_stress:
                daily_stress[day] = []
            daily_stress[day].append(measurement.value)
        
        daily_averages = {day: statistics.mean(values) for day, values in daily_stress.items()}
        
        return {
            'average_stress': avg_stress,
            'stress_variability': stress_variability,
            'hourly_patterns': hourly_averages,
            'peak_stress_hours': peak_hours,
            'low_stress_hours': low_hours,
            'daily_patterns': daily_averages,
            'total_measurements': len(measurements),
            'high_stress_episodes': len([m for m in measurements if m.stress_level in [StressLevel.HIGH, StressLevel.VERY_HIGH]])
        }
    
    async def predict_stress_episode(self, user_id: str, current_context: Dict[str, Any]) -> float:
        """Predict likelihood of stress episode"""
        try:
            # Simplified prediction based on context factors
            risk_factors = []
            
            # Time-based factors
            current_hour = datetime.now().hour
            if 9 <= current_hour <= 11 or 14 <= current_hour <= 16:  # Common stress peaks
                risk_factors.append(0.3)
            
            # Calendar-based factors
            if current_context.get('upcoming_meetings', 0) > 2:
                risk_factors.append(0.4)
            
            if current_context.get('deadline_proximity', 0) > 0.7:  # Close deadline
                risk_factors.append(0.5)
            
            # Environmental factors
            if current_context.get('noise_level', 0) > 70:  # High noise
                risk_factors.append(0.2)
            
            if current_context.get('interruptions', 0) > 5:  # Many interruptions
                risk_factors.append(0.3)
            
            # Recent stress history
            if current_context.get('recent_high_stress', False):
                risk_factors.append(0.4)
            
            # Combine risk factors
            if risk_factors:
                base_risk = np.mean(risk_factors)
                # Add some random variation
                prediction = min(1.0, base_risk + np.random.normal(0, 0.1))
            else:
                prediction = 0.1  # Base low risk
            
            return max(0.0, prediction)
            
        except Exception as e:
            logger.error(f"Error predicting stress episode: {e}")
            return 0.1
    
    async def _analyze_hrv(self, user_id: str, hrv_data: Dict[str, Any]) -> Tuple[float, float]:
        """Analyze Heart Rate Variability for stress"""
        try:
            rmssd = hrv_data.get('rmssd', 50)  # Root Mean Square of Successive Differences
            
            # Get user baseline (would be stored in database)
            baseline_rmssd = self.baseline_metrics.get(user_id, {}).get('rmssd', 50)
            
            # Calculate stress score (lower HRV = higher stress)
            stress_ratio = baseline_rmssd / max(rmssd, 1)
            stress_score = min(100, stress_ratio * 50)
            
            confidence = 0.8  # HRV is fairly reliable for stress
            
            return stress_score, confidence
            
        except Exception as e:
            logger.error(f"Error analyzing HRV: {e}")
            return 50.0, 0.1
    
    async def _analyze_cortisol(self, cortisol_level: float) -> Tuple[float, float]:
        """Analyze cortisol level for stress"""
        try:
            # Normal cortisol range is roughly 6-23 mcg/dL
            normal_max = 23.0
            
            if cortisol_level <= normal_max:
                stress_score = (cortisol_level / normal_max) * 50
            else:
                # Elevated cortisol indicates higher stress
                excess = cortisol_level - normal_max
                stress_score = 50 + (excess / normal_max) * 50
            
            stress_score = min(100, stress_score)
            confidence = 0.9  # Cortisol is a reliable stress indicator
            
            return stress_score, confidence
            
        except Exception as e:
            logger.error(f"Error analyzing cortisol: {e}")
            return 50.0, 0.1
    
    async def _analyze_behavior(self, user_id: str, behavior_data: Dict[str, Any]) -> Tuple[float, float]:
        """Analyze behavioral markers for stress"""
        try:
            stress_indicators = 0
            total_indicators = 0
            
            # Screen time (excessive use can indicate stress/avoidance)
            screen_time = behavior_data.get('screen_time_hours', 0)
            if screen_time > 8:
                stress_indicators += 1
            total_indicators += 1
            
            # Sleep quality (poor sleep often correlates with stress)
            sleep_quality = behavior_data.get('sleep_quality', 5)
            if sleep_quality < 6:
                stress_indicators += 1
            total_indicators += 1
            
            # Physical activity (reduced activity can indicate stress)
            activity_level = behavior_data.get('activity_level', 5)
            if activity_level < 4:
                stress_indicators += 1
            total_indicators += 1
            
            # Social interaction (isolation can indicate stress)
            social_interactions = behavior_data.get('social_interactions', 3)
            if social_interactions < 2:
                stress_indicators += 1
            total_indicators += 1
            
            # Calculate stress score
            if total_indicators > 0:
                stress_ratio = stress_indicators / total_indicators
                stress_score = stress_ratio * 100
                confidence = 0.6  # Behavioral markers are less direct
            else:
                stress_score = 50.0
                confidence = 0.1
            
            return stress_score, confidence
            
        except Exception as e:
            logger.error(f"Error analyzing behavior: {e}")
            return 50.0, 0.1
    
    async def _score_to_level(self, score: float) -> StressLevel:
        """Convert numerical stress score to stress level"""
        if score < 20:
            return StressLevel.VERY_LOW
        elif score < 40:
            return StressLevel.LOW
        elif score < 60:
            return StressLevel.MODERATE
        elif score < 80:
            return StressLevel.HIGH
        else:
            return StressLevel.VERY_HIGH


class PersonalizedRecommendationEngine(RecommendationEngine):
    """Personalized stress management recommendation engine"""
    
    def __init__(self):
        self.recommendation_templates = {
            InterventionType.BREATHING_EXERCISE: {
                'title': '4-7-8 Breathing Exercise',
                'base_description': 'A simple breathing technique to reduce stress and anxiety',
                'base_instructions': [
                    'Sit comfortably with your back straight',
                    'Exhale completely through your mouth',
                    'Inhale through your nose for 4 counts',
                    'Hold your breath for 7 counts',
                    'Exhale through your mouth for 8 counts',
                    'Repeat 3-4 times'
                ],
                'duration': 5
            },
            InterventionType.MEDITATION: {
                'title': 'Mindfulness Meditation',
                'base_description': 'Focus on the present moment to reduce stress',
                'base_instructions': [
                    'Find a quiet, comfortable place to sit',
                    'Close your eyes or soften your gaze',
                    'Focus on your breath',
                    'When thoughts arise, gently return focus to breathing',
                    'Continue for the full duration'
                ],
                'duration': 10
            },
            InterventionType.PROGRESSIVE_RELAXATION: {
                'title': 'Progressive Muscle Relaxation',
                'base_description': 'Systematically tense and release muscle groups',
                'base_instructions': [
                    'Start with your toes and work upward',
                    'Tense each muscle group for 5 seconds',
                    'Release and notice the relaxation',
                    'Move to the next muscle group',
                    'Finish with whole-body awareness'
                ],
                'duration': 15
            }
        }
        
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
        self.effectiveness_history: Dict[str, List[float]] = {}
    
    async def generate_recommendations(self, user_id: str, current_stress: StressLevel,
                                     context: Dict[str, Any]) -> List[StressRecommendation]:
        """Generate personalized stress management recommendations"""
        try:
            recommendations = []
            
            # Get user preferences
            user_prefs = self.user_preferences.get(user_id, {})
            
            # Determine urgency based on stress level
            if current_stress in [StressLevel.HIGH, StressLevel.VERY_HIGH]:
                urgency = RecommendationUrgency.IMMEDIATE
                target_interventions = [
                    InterventionType.BREATHING_EXERCISE,
                    InterventionType.PROGRESSIVE_RELAXATION
                ]
            elif current_stress == StressLevel.MODERATE:
                urgency = RecommendationUrgency.SOON
                target_interventions = [
                    InterventionType.MEDITATION,
                    InterventionType.MINDFULNESS,
                    InterventionType.BREAK_REMINDER
                ]
            else:
                urgency = RecommendationUrgency.DAILY
                target_interventions = [
                    InterventionType.PHYSICAL_ACTIVITY,
                    InterventionType.MINDFULNESS
                ]
            
            # Generate recommendations for each intervention type
            for intervention_type in target_interventions:
                rec = await self._create_personalized_recommendation(
                    user_id, intervention_type, urgency, context, user_prefs
                )
                if rec:
                    recommendations.append(rec)
            
            # Add context-specific recommendations
            context_recs = await self._generate_contextual_recommendations(user_id, context, urgency)
            recommendations.extend(context_recs)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    async def prioritize_recommendations(self, recommendations: List[StressRecommendation]) -> List[StressRecommendation]:
        """Prioritize recommendations based on effectiveness and urgency"""
        def priority_score(rec: StressRecommendation) -> float:
            urgency_scores = {
                RecommendationUrgency.IMMEDIATE: 100,
                RecommendationUrgency.SOON: 75,
                RecommendationUrgency.DAILY: 50,
                RecommendationUrgency.WEEKLY: 25,
                RecommendationUrgency.MONTHLY: 10
            }
            
            urgency_score = urgency_scores.get(rec.urgency, 50)
            effectiveness_score = rec.effectiveness_score * 10
            success_rate_score = (rec.success_rate or 0.5) * 20
            
            # Penalize recently used recommendations
            recency_penalty = 0
            if rec.last_suggested:
                hours_since = (datetime.now() - rec.last_suggested).total_seconds() / 3600
                if hours_since < 6:
                    recency_penalty = 20
                elif hours_since < 24:
                    recency_penalty = 10
            
            return urgency_score + effectiveness_score + success_rate_score - recency_penalty
        
        sorted_recs = sorted(recommendations, key=priority_score, reverse=True)
        return sorted_recs[:5]  # Return top 5 recommendations
    
    async def adapt_recommendations(self, user_id: str, feedback: List[InterventionSession]) -> None:
        """Adapt recommendations based on user feedback and effectiveness"""
        try:
            if not feedback:
                return
            
            # Analyze feedback by intervention type
            type_effectiveness = {}
            
            for session in feedback:
                if session.effectiveness is not None:
                    intervention_type = session.intervention_type
                    if intervention_type not in type_effectiveness:
                        type_effectiveness[intervention_type] = []
                    type_effectiveness[intervention_type].append(session.effectiveness)
            
            # Update effectiveness scores
            for intervention_type, effectiveness_scores in type_effectiveness.items():
                avg_effectiveness = statistics.mean(effectiveness_scores)
                
                if user_id not in self.effectiveness_history:
                    self.effectiveness_history[user_id] = {}
                
                self.effectiveness_history[user_id][intervention_type.value] = avg_effectiveness
            
            # Update user preferences based on ratings
            user_ratings = {}
            for session in feedback:
                if session.user_rating is not None:
                    intervention_type = session.intervention_type
                    if intervention_type not in user_ratings:
                        user_ratings[intervention_type] = []
                    user_ratings[intervention_type].append(session.user_rating)
            
            # Update preferences
            if user_id not in self.user_preferences:
                self.user_preferences[user_id] = {}
            
            for intervention_type, ratings in user_ratings.items():
                avg_rating = statistics.mean(ratings)
                self.user_preferences[user_id][f'{intervention_type.value}_preference'] = avg_rating
            
            logger.info(f"Updated recommendations for user {user_id} based on {len(feedback)} sessions")
            
        except Exception as e:
            logger.error(f"Error adapting recommendations: {e}")
    
    async def _create_personalized_recommendation(self, user_id: str, intervention_type: InterventionType,
                                                urgency: RecommendationUrgency, context: Dict[str, Any],
                                                user_prefs: Dict[str, Any]) -> Optional[StressRecommendation]:
        """Create a personalized recommendation for a specific intervention type"""
        try:
            template = self.recommendation_templates.get(intervention_type)
            if not template:
                return None
            
            # Get effectiveness score from history
            effectiveness_score = self.effectiveness_history.get(user_id, {}).get(intervention_type.value, 7.0)
            
            # Personalize based on context and preferences
            title = template['title']
            description = template['base_description']
            instructions = template['base_instructions'].copy()
            duration = template['duration']
            
            # Adjust duration based on available time
            available_time = context.get('available_time_minutes', duration)
            if available_time < duration:
                duration = max(2, available_time)
                if intervention_type == InterventionType.BREATHING_EXERCISE:
                    instructions[-1] = f'Repeat {max(1, duration//2)} times'
            
            # Add contextual instructions
            if context.get('location') == 'office':
                instructions.insert(0, 'Find a private space or use noise-canceling headphones')
            
            if context.get('high_anxiety', False) and intervention_type == InterventionType.BREATHING_EXERCISE:
                description += ' - especially effective for anxiety'
            
            # Determine triggers for this recommendation
            triggers = []
            if intervention_type == InterventionType.BREATHING_EXERCISE:
                triggers = [StressSource.WORK, StressSource.DEADLINES, StressSource.ANXIETY]
            elif intervention_type == InterventionType.MEDITATION:
                triggers = [StressSource.WORK, StressSource.RELATIONSHIPS, StressSource.HEALTH]
            
            return StressRecommendation(
                recommendation_id=str(uuid4()),
                user_id=user_id,
                intervention_type=intervention_type,
                title=title,
                description=description,
                instructions=instructions,
                duration_minutes=duration,
                urgency=urgency,
                effectiveness_score=effectiveness_score,
                triggers=triggers,
                success_rate=user_prefs.get(f'{intervention_type.value}_success_rate'),
                personalization_factors={
                    'preferred_duration': user_prefs.get('preferred_duration', duration),
                    'context': context
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating personalized recommendation: {e}")
            return None
    
    async def _generate_contextual_recommendations(self, user_id: str, context: Dict[str, Any],
                                                 urgency: RecommendationUrgency) -> List[StressRecommendation]:
        """Generate recommendations based on specific context"""
        contextual_recs = []
        
        # Work-related stress
        if context.get('location') == 'office' and context.get('workload_high', False):
            contextual_recs.append(StressRecommendation(
                recommendation_id=str(uuid4()),
                user_id=user_id,
                intervention_type=InterventionType.BREAK_REMINDER,
                title='Take a Micro-Break',
                description='Step away from your desk for 2-3 minutes',
                instructions=[
                    'Stand up and stretch your arms and legs',
                    'Look away from your screen and focus on distant objects',
                    'Take 5 deep breaths',
                    'Walk around if possible'
                ],
                duration_minutes=3,
                urgency=urgency,
                effectiveness_score=6.0,
                triggers=[StressSource.WORK, StressSource.DEADLINES]
            ))
        
        # Environmental stress
        if context.get('noise_level', 0) > 70:
            contextual_recs.append(StressRecommendation(
                recommendation_id=str(uuid4()),
                user_id=user_id,
                intervention_type=InterventionType.ENVIRONMENT_CHANGE,
                title='Reduce Environmental Stress',
                description='Change your environment to reduce noise and distractions',
                instructions=[
                    'Use noise-canceling headphones or earplugs',
                    'Move to a quieter location if possible',
                    'Close unnecessary browser tabs and applications',
                    'Organize your immediate workspace'
                ],
                duration_minutes=5,
                urgency=urgency,
                effectiveness_score=5.5,
                triggers=[StressSource.ENVIRONMENT, StressSource.WORK]
            ))
        
        # Time pressure stress
        if context.get('deadline_proximity', 0) > 0.8:
            contextual_recs.append(StressRecommendation(
                recommendation_id=str(uuid4()),
                user_id=user_id,
                intervention_type=InterventionType.TIME_MANAGEMENT,
                title='Priority Focus Technique',
                description='Reduce overwhelm by focusing on the most important task',
                instructions=[
                    'List all tasks that need to be completed',
                    'Identify the top 3 most critical items',
                    'Focus on completing one task at a time',
                    'Set a timer for focused work sessions',
                    'Ignore non-essential tasks for now'
                ],
                duration_minutes=10,
                urgency=urgency,
                effectiveness_score=7.5,
                triggers=[StressSource.DEADLINES, StressSource.WORK]
            ))
        
        return contextual_recs


class ComprehensiveInterventionProvider(InterventionProvider):
    """Comprehensive intervention delivery system"""
    
    def __init__(self):
        self.active_sessions: Dict[str, InterventionSession] = {}
        self.guided_content = {
            InterventionType.BREATHING_EXERCISE: {
                'audio_files': ['4-7-8-breathing.mp3', 'box-breathing.mp3'],
                'video_files': ['breathing-demo.mp4'],
                'instructions': 'Follow the visual or audio guide for proper timing'
            },
            InterventionType.MEDITATION: {
                'audio_files': ['mindfulness-5min.mp3', 'mindfulness-10min.mp3', 'mindfulness-20min.mp3'],
                'instructions': 'Choose a guided meditation that matches your available time'
            }
        }
    
    async def deliver_intervention(self, intervention: StressRecommendation, user_context: Dict[str, Any]) -> InterventionSession:
        """Deliver a stress management intervention"""
        try:
            session = InterventionSession(
                session_id=str(uuid4()),
                user_id=intervention.user_id,
                recommendation_id=intervention.recommendation_id,
                intervention_type=intervention.intervention_type,
                start_time=datetime.now()
            )
            
            # Record pre-intervention stress level if available
            if 'current_stress_level' in user_context:
                session.pre_stress_level = user_context['current_stress_level']
            
            # Store active session
            self.active_sessions[session.session_id] = session
            
            # Provide intervention-specific setup
            setup_info = await self._setup_intervention(intervention, user_context)
            session.notes = f"Setup: {setup_info}"
            
            logger.info(f"Started intervention session {session.session_id} for user {intervention.user_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error delivering intervention: {e}")
            return InterventionSession(
                session_id=str(uuid4()),
                user_id=intervention.user_id,
                recommendation_id=intervention.recommendation_id,
                intervention_type=intervention.intervention_type,
                start_time=datetime.now()
            )
    
    async def track_progress(self, session: InterventionSession) -> Dict[str, Any]:
        """Track progress during intervention"""
        try:
            if session.session_id not in self.active_sessions:
                return {'error': 'Session not found'}
            
            current_session = self.active_sessions[session.session_id]
            elapsed_time = (datetime.now() - current_session.start_time).total_seconds() / 60
            
            progress = {
                'session_id': session.session_id,
                'elapsed_time_minutes': elapsed_time,
                'intervention_type': current_session.intervention_type.value,
                'completion_percentage': min(100, (elapsed_time / session.duration_minutes) * 100) if hasattr(session, 'duration_minutes') else 0
            }
            
            # Add intervention-specific tracking
            if current_session.intervention_type == InterventionType.BREATHING_EXERCISE:
                progress['breathing_cycles_completed'] = max(0, int(elapsed_time / 2))  # Assuming 2 minutes per cycle
                
            elif current_session.intervention_type == InterventionType.MEDITATION:
                progress['meditation_quality'] = await self._assess_meditation_quality(current_session)
            
            return progress
            
        except Exception as e:
            logger.error(f"Error tracking progress: {e}")
            return {'error': str(e)}
    
    async def provide_guidance(self, intervention_type: InterventionType, user_level: str) -> Dict[str, Any]:
        """Provide guidance for intervention execution"""
        try:
            guidance = {
                'intervention_type': intervention_type.value,
                'user_level': user_level,
                'tips': [],
                'resources': [],
                'common_mistakes': []
            }
            
            if intervention_type == InterventionType.BREATHING_EXERCISE:
                guidance['tips'] = [
                    'Start slowly and don\'t force the breathing pattern',
                    'If you feel dizzy, return to normal breathing',
                    'Practice in a comfortable, seated position',
                    'Focus on the exhale to activate relaxation response'
                ]
                guidance['common_mistakes'] = [
                    'Breathing too fast or forcefully',
                    'Holding breath too long initially',
                    'Not maintaining consistent rhythm'
                ]
                
            elif intervention_type == InterventionType.MEDITATION:
                if user_level == 'beginner':
                    guidance['tips'] = [
                        'Start with short sessions (5-10 minutes)',
                        'It\'s normal for your mind to wander',
                        'Gently return focus to your breath when distracted',
                        'Find a quiet, comfortable space'
                    ]
                else:
                    guidance['tips'] = [
                        'Experiment with different meditation styles',
                        'Try longer sessions when ready',
                        'Notice thoughts without judgment',
                        'Develop a consistent daily practice'
                    ]
            
            # Add available resources
            if intervention_type in self.guided_content:
                guidance['resources'] = self.guided_content[intervention_type]
            
            return guidance
            
        except Exception as e:
            logger.error(f"Error providing guidance: {e}")
            return {'error': str(e)}
    
    async def complete_session(self, session_id: str, user_rating: Optional[int] = None,
                             post_stress_level: Optional[float] = None, notes: Optional[str] = None) -> bool:
        """Complete an intervention session"""
        try:
            if session_id not in self.active_sessions:
                return False
            
            session = self.active_sessions[session_id]
            session.end_time = datetime.now()
            session.completed = True
            session.user_rating = user_rating
            session.post_stress_level = post_stress_level
            
            if notes:
                session.notes = f"{session.notes or ''}\nCompletion notes: {notes}"
            
            # Calculate effectiveness if we have both pre and post stress levels
            if session.pre_stress_level is not None and session.post_stress_level is not None:
                stress_reduction = session.pre_stress_level - session.post_stress_level
                session.effectiveness = max(0, stress_reduction / session.pre_stress_level) * 100
            
            logger.info(f"Completed intervention session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing session: {e}")
            return False
    
    async def _setup_intervention(self, intervention: StressRecommendation, context: Dict[str, Any]) -> str:
        """Setup intervention based on type and context"""
        setup_info = []
        
        if intervention.intervention_type == InterventionType.BREATHING_EXERCISE:
            setup_info.append("Prepared breathing exercise timing")
            if context.get('location') == 'office':
                setup_info.append("Suggested private space or headphones")
                
        elif intervention.intervention_type == InterventionType.MEDITATION:
            setup_info.append("Selected appropriate guided meditation")
            duration = intervention.duration_minutes
            if duration <= 5:
                setup_info.append("Short session for quick stress relief")
            elif duration >= 15:
                setup_info.append("Extended session for deep relaxation")
        
        return "; ".join(setup_info)
    
    async def _assess_meditation_quality(self, session: InterventionSession) -> str:
        """Assess meditation quality based on session duration and type"""
        elapsed_time = (datetime.now() - session.start_time).total_seconds() / 60
        
        if elapsed_time < 2:
            return "just_started"
        elif elapsed_time < 5:
            return "settling_in"
        elif elapsed_time < 10:
            return "focused"
        else:
            return "deep_practice"


class StressManagement:
    """Main stress management service"""
    
    def __init__(self,
                 stress_detector: StressDetector,
                 recommendation_engine: RecommendationEngine,
                 intervention_provider: InterventionProvider):
        self.stress_detector = stress_detector
        self.recommendation_engine = recommendation_engine
        self.intervention_provider = intervention_provider
        
        # In-memory storage (replace with database in production)
        self.stress_measurements: Dict[str, List[StressMeasurement]] = {}
        self.stress_events: Dict[str, List[StressEvent]] = {}
        self.stress_patterns: Dict[str, StressPattern] = {}
        self.recommendations: Dict[str, List[StressRecommendation]] = {}
        self.intervention_sessions: Dict[str, List[InterventionSession]] = {}
        self.stress_alerts: Dict[str, List[StressAlert]] = {}
        self.biofeedback_sessions: Dict[str, List[BiofeedbackSession]] = {}
        self.mindfulness_activities: Dict[str, List[MindfulnessActivity]] = {}
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._running = False
        self._alert_thresholds = {
            StressLevel.HIGH: True,
            StressLevel.VERY_HIGH: True
        }
    
    async def start(self):
        """Start the stress management service"""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting Stress Management Service")
        
        # Start background tasks
        self._background_tasks = [
            asyncio.create_task(self._monitor_stress_levels()),
            asyncio.create_task(self._analyze_patterns()),
            asyncio.create_task(self._generate_recommendations_periodic()),
            asyncio.create_task(self._send_proactive_interventions()),
            asyncio.create_task(self._track_intervention_effectiveness())
        ]
    
    async def stop(self):
        """Stop the stress management service"""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping Stress Management Service")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
    
    async def record_stress_measurement(self, user_id: str, measurement_data: Dict[str, Any]) -> StressMeasurement:
        """Record a new stress measurement"""
        try:
            measurement = await self.stress_detector.detect_stress(user_id, measurement_data)
            
            # Store measurement
            if user_id not in self.stress_measurements:
                self.stress_measurements[user_id] = []
            
            self.stress_measurements[user_id].append(measurement)
            
            # Check for alert conditions
            if measurement.stress_level in self._alert_thresholds:
                await self._create_stress_alert(user_id, measurement)
            
            logger.info(f"Recorded stress measurement for user {user_id}: {measurement.stress_level.value}")
            return measurement
            
        except Exception as e:
            logger.error(f"Error recording stress measurement: {e}")
            return StressMeasurement(
                measurement_id=str(uuid4()),
                user_id=user_id,
                measurement_type=StressMeasurementType.SELF_REPORT,
                value=50.0,
                unit="stress_score",
                stress_level=StressLevel.MODERATE,
                confidence=0.1
            )
    
    async def get_stress_recommendations(self, user_id: str, current_context: Dict[str, Any] = None) -> List[StressRecommendation]:
        """Get current stress management recommendations"""
        try:
            if current_context is None:
                current_context = {}
            
            # Get recent stress level
            recent_measurements = self.stress_measurements.get(user_id, [])
            if recent_measurements:
                current_stress = recent_measurements[-1].stress_level
            else:
                current_stress = StressLevel.MODERATE
            
            # Generate recommendations
            recommendations = await self.recommendation_engine.generate_recommendations(
                user_id, current_stress, current_context
            )
            
            # Prioritize recommendations
            prioritized = await self.recommendation_engine.prioritize_recommendations(recommendations)
            
            # Store recommendations
            self.recommendations[user_id] = prioritized
            
            return prioritized
            
        except Exception as e:
            logger.error(f"Error getting stress recommendations: {e}")
            return []
    
    async def start_intervention(self, user_id: str, recommendation_id: str, context: Dict[str, Any] = None) -> Optional[InterventionSession]:
        """Start a stress management intervention"""
        try:
            if context is None:
                context = {}
            
            # Find the recommendation
            user_recommendations = self.recommendations.get(user_id, [])
            recommendation = next((r for r in user_recommendations if r.recommendation_id == recommendation_id), None)
            
            if not recommendation:
                logger.warning(f"Recommendation {recommendation_id} not found for user {user_id}")
                return None
            
            # Start intervention session
            session = await self.intervention_provider.deliver_intervention(recommendation, context)
            
            # Store session
            if user_id not in self.intervention_sessions:
                self.intervention_sessions[user_id] = []
            
            self.intervention_sessions[user_id].append(session)
            
            # Update recommendation usage
            recommendation.times_used += 1
            recommendation.last_suggested = datetime.now()
            
            logger.info(f"Started intervention session {session.session_id} for user {user_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error starting intervention: {e}")
            return None
    
    async def complete_intervention(self, session_id: str, user_rating: Optional[int] = None,
                                  post_stress_level: Optional[float] = None, notes: Optional[str] = None) -> bool:
        """Complete an intervention session"""
        try:
            success = await self.intervention_provider.complete_session(
                session_id, user_rating, post_stress_level, notes
            )
            
            if success:
                # Find and update the session in our storage
                for user_id, sessions in self.intervention_sessions.items():
                    for session in sessions:
                        if session.session_id == session_id:
                            session.completed = True
                            session.user_rating = user_rating
                            session.post_stress_level = post_stress_level
                            if notes:
                                session.notes = f"{session.notes or ''}\n{notes}"
                            break
                
                logger.info(f"Completed intervention session {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error completing intervention: {e}")
            return False
    
    async def log_mindfulness_activity(self, user_id: str, activity: MindfulnessActivity) -> bool:
        """Log a mindfulness activity"""
        try:
            if user_id not in self.mindfulness_activities:
                self.mindfulness_activities[user_id] = []
            
            self.mindfulness_activities[user_id].append(activity)
            
            logger.info(f"Logged mindfulness activity for user {user_id}: {activity.activity_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging mindfulness activity: {e}")
            return False
    
    async def get_stress_analysis(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive stress analysis"""
        try:
            # Get recent measurements
            all_measurements = self.stress_measurements.get(user_id, [])
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_measurements = [m for m in all_measurements if m.measured_at >= cutoff_date]
            
            if not recent_measurements:
                return {'error': 'No stress data available'}
            
            # Analyze patterns
            patterns = await self.stress_detector.analyze_patterns(recent_measurements)
            
            # Get current pattern if available
            current_pattern = self.stress_patterns.get(user_id)
            
            # Get recent interventions
            recent_interventions = []
            if user_id in self.intervention_sessions:
                recent_interventions = [s for s in self.intervention_sessions[user_id] 
                                      if s.start_time >= cutoff_date]
            
            # Calculate intervention effectiveness
            intervention_effectiveness = {}
            for session in recent_interventions:
                if session.effectiveness is not None:
                    intervention_type = session.intervention_type.value
                    if intervention_type not in intervention_effectiveness:
                        intervention_effectiveness[intervention_type] = []
                    intervention_effectiveness[intervention_type].append(session.effectiveness)
            
            # Average effectiveness by intervention type
            avg_effectiveness = {
                intervention_type: statistics.mean(scores)
                for intervention_type, scores in intervention_effectiveness.items()
            }
            
            return {
                'summary': {
                    'total_measurements': len(recent_measurements),
                    'average_stress_level': patterns.get('average_stress', 0),
                    'stress_variability': patterns.get('stress_variability', 0),
                    'high_stress_episodes': patterns.get('high_stress_episodes', 0),
                    'interventions_completed': len([s for s in recent_interventions if s.completed])
                },
                'patterns': patterns,
                'current_pattern': current_pattern,
                'intervention_effectiveness': avg_effectiveness,
                'recent_measurements': recent_measurements[-7:],  # Last 7 measurements
                'active_recommendations': len(self.recommendations.get(user_id, [])),
                'mindfulness_sessions': len(self.mindfulness_activities.get(user_id, []))
            }
            
        except Exception as e:
            logger.error(f"Error getting stress analysis: {e}")
            return {'error': str(e)}
    
    async def predict_stress_risk(self, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Predict stress risk and provide preventive recommendations"""
        try:
            # Get stress prediction
            risk_score = await self.stress_detector.predict_stress_episode(user_id, context)
            
            # Determine risk level
            if risk_score < 0.2:
                risk_level = "low"
            elif risk_score < 0.4:
                risk_level = "moderate"
            elif risk_score < 0.6:
                risk_level = "high"
            else:
                risk_level = "very_high"
            
            # Generate preventive recommendations if risk is moderate or higher
            preventive_recs = []
            if risk_score >= 0.3:
                preventive_recs = await self.recommendation_engine.generate_recommendations(
                    user_id, StressLevel.MODERATE, context
                )
                # Focus on preventive interventions
                preventive_recs = [rec for rec in preventive_recs 
                                 if rec.intervention_type in [InterventionType.MINDFULNESS, 
                                                            InterventionType.BREAK_REMINDER,
                                                            InterventionType.TIME_MANAGEMENT]]
            
            return {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'prediction_factors': context,
                'preventive_recommendations': preventive_recs[:3],  # Top 3 preventive recommendations
                'predicted_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error predicting stress risk: {e}")
            return {'error': str(e)}
    
    async def _create_stress_alert(self, user_id: str, measurement: StressMeasurement) -> None:
        """Create a stress alert for high stress levels"""
        try:
            # Get immediate recommendations
            context = measurement.context or {}
            recommendations = await self.recommendation_engine.generate_recommendations(
                user_id, measurement.stress_level, context
            )
            
            # Prioritize for immediate use
            immediate_recs = [rec for rec in recommendations if rec.urgency == RecommendationUrgency.IMMEDIATE]
            
            alert = StressAlert(
                alert_id=str(uuid4()),
                user_id=user_id,
                alert_level=measurement.stress_level,
                trigger_measurement=measurement,
                suggested_interventions=immediate_recs[:3],  # Top 3 immediate interventions
                alert_time=datetime.now()
            )
            
            # Store alert
            if user_id not in self.stress_alerts:
                self.stress_alerts[user_id] = []
            
            self.stress_alerts[user_id].append(alert)
            
            logger.warning(f"Created stress alert for user {user_id}: {measurement.stress_level.value}")
            
        except Exception as e:
            logger.error(f"Error creating stress alert: {e}")
    
    async def _monitor_stress_levels(self):
        """Background task to monitor stress levels"""
        while self._running:
            try:
                # Check for users who haven't reported stress recently
                current_time = datetime.now()
                
                for user_id, measurements in self.stress_measurements.items():
                    if measurements:
                        last_measurement = measurements[-1]
                        hours_since = (current_time - last_measurement.measured_at).total_seconds() / 3600
                        
                        # If no measurement in 6+ hours and last was high stress, send check-in
                        if (hours_since > 6 and 
                            last_measurement.stress_level in [StressLevel.HIGH, StressLevel.VERY_HIGH]):
                            logger.info(f"User {user_id} may need stress check-in")
                
                await asyncio.sleep(3600)  # Check every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in stress level monitoring: {e}")
                await asyncio.sleep(3600)
    
    async def _analyze_patterns(self):
        """Background task to analyze stress patterns"""
        while self._running:
            try:
                for user_id, measurements in self.stress_measurements.items():
                    if len(measurements) >= 14:  # Need at least 2 weeks of data
                        try:
                            # Get recent measurements for pattern analysis
                            recent_measurements = measurements[-30:]  # Last 30 measurements
                            
                            # Create stress pattern
                            pattern_analysis = await self.stress_detector.analyze_patterns(recent_measurements)
                            
                            # Create comprehensive pattern object
                            pattern = StressPattern(
                                pattern_id=str(uuid4()),
                                user_id=user_id,
                                analysis_period="30d",
                                average_stress_level=pattern_analysis.get('average_stress', 50),
                                stress_variability=pattern_analysis.get('stress_variability', 0),
                                peak_stress_times=[time(hour=h) for h in pattern_analysis.get('peak_stress_hours', [])],
                                low_stress_times=[time(hour=h) for h in pattern_analysis.get('low_stress_hours', [])],
                                common_triggers=[(StressSource.WORK, 0.7), (StressSource.DEADLINES, 0.5)],  # Simplified
                                stress_by_day_of_week=pattern_analysis.get('daily_patterns', {}),
                                stress_by_activity={},  # Would be populated from context data
                                recovery_patterns={},
                                chronic_stress_indicators=[],
                                resilience_score=max(0, 100 - pattern_analysis.get('average_stress', 50))
                            )
                            
                            self.stress_patterns[user_id] = pattern
                            logger.info(f"Updated stress pattern for user {user_id}")
                            
                        except Exception as e:
                            logger.error(f"Error analyzing pattern for user {user_id}: {e}")
                
                await asyncio.sleep(21600)  # Analyze every 6 hours
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in pattern analysis: {e}")
                await asyncio.sleep(21600)
    
    async def _generate_recommendations_periodic(self):
        """Background task to generate periodic recommendations"""
        while self._running:
            try:
                # Generate daily recommendations for all users
                for user_id in self.stress_measurements.keys():
                    try:
                        # Get current context (simplified)
                        current_context = {
                            'time_of_day': datetime.now().hour,
                            'day_of_week': datetime.now().weekday()
                        }
                        
                        recommendations = await self.get_stress_recommendations(user_id, current_context)
                        
                        if recommendations:
                            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
                        
                    except Exception as e:
                        logger.error(f"Error generating recommendations for user {user_id}: {e}")
                
                await asyncio.sleep(86400)  # Generate daily
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recommendation generation: {e}")
                await asyncio.sleep(86400)
    
    async def _send_proactive_interventions(self):
        """Background task to send proactive interventions"""
        while self._running:
            try:
                current_hour = datetime.now().hour
                
                # Send break reminders during work hours
                if 9 <= current_hour <= 17:
                    for user_id in self.stress_patterns.keys():
                        pattern = self.stress_patterns[user_id]
                        
                        # Check if current time is a typical high-stress period
                        current_time = datetime.now().time()
                        for peak_time in pattern.peak_stress_times:
                            if abs((current_time.hour * 60 + current_time.minute) - 
                                   (peak_time.hour * 60 + peak_time.minute)) < 30:  # Within 30 minutes
                                logger.info(f"Proactive intervention suggested for user {user_id}")
                                break
                
                await asyncio.sleep(1800)  # Check every 30 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in proactive interventions: {e}")
                await asyncio.sleep(1800)
    
    async def _track_intervention_effectiveness(self):
        """Background task to track and update intervention effectiveness"""
        while self._running:
            try:
                # Analyze completed interventions
                for user_id, sessions in self.intervention_sessions.items():
                    completed_sessions = [s for s in sessions if s.completed and s.end_time]
                    
                    if len(completed_sessions) >= 5:  # Need enough data
                        # Update recommendation engine with feedback
                        await self.recommendation_engine.adapt_recommendations(user_id, completed_sessions)
                        
                        logger.info(f"Updated intervention effectiveness for user {user_id}")
                
                await asyncio.sleep(43200)  # Update twice daily
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error tracking intervention effectiveness: {e}")
                await asyncio.sleep(43200)


# Singleton instance
_stress_management_instance: Optional[StressManagement] = None


def get_stress_management_service() -> StressManagement:
    """Get the singleton stress management service instance"""
    global _stress_management_instance
    
    if _stress_management_instance is None:
        # Initialize with default implementations
        stress_detector = MultiModalStressDetector()
        recommendation_engine = PersonalizedRecommendationEngine()
        intervention_provider = ComprehensiveInterventionProvider()
        
        _stress_management_instance = StressManagement(
            stress_detector=stress_detector,
            recommendation_engine=recommendation_engine,
            intervention_provider=intervention_provider
        )
    
    return _stress_management_instance


async def main():
    """Example usage of the stress management service"""
    stress_service = get_stress_management_service()
    
    try:
        await stress_service.start()
        
        user_id = "user123"
        
        # Example 1: Record stress measurement
        measurement_data = {
            'self_report': 75,  # High stress self-report
            'hrv': {'rmssd': 25},  # Low HRV indicates stress
            'context': {
                'location': 'office',
                'activity': 'working',
                'upcoming_meetings': 3
            }
        }
        
        measurement = await stress_service.record_stress_measurement(user_id, measurement_data)
        print(f"Recorded stress measurement: {measurement.stress_level.value} ({measurement.value:.1f})")
        
        # Example 2: Get recommendations
        context = {
            'available_time_minutes': 10,
            'location': 'office',
            'high_anxiety': True
        }
        
        recommendations = await stress_service.get_stress_recommendations(user_id, context)
        print(f"Generated {len(recommendations)} recommendations")
        
        if recommendations:
            top_rec = recommendations[0]
            print(f"Top recommendation: {top_rec.title} ({top_rec.duration_minutes} min)")
        
        # Example 3: Start intervention
        if recommendations:
            session = await stress_service.start_intervention(user_id, recommendations[0].recommendation_id, context)
            if session:
                print(f"Started intervention session: {session.session_id}")
                
                # Simulate intervention completion
                await asyncio.sleep(2)  # Simulate some intervention time
                
                success = await stress_service.complete_intervention(
                    session.session_id, 
                    user_rating=4, 
                    post_stress_level=45.0,
                    notes="Felt much more relaxed after the breathing exercise"
                )
                print(f"Completed intervention: {success}")
        
        # Example 4: Log mindfulness activity
        mindfulness_activity = MindfulnessActivity(
            activity_id=str(uuid4()),
            user_id=user_id,
            activity_type="meditation",
            guided=True,
            duration_minutes=10,
            focus_quality=7,
            pre_mood=4,
            post_mood=7,
            environment="bedroom"
        )
        
        logged = await stress_service.log_mindfulness_activity(user_id, mindfulness_activity)
        print(f"Logged mindfulness activity: {logged}")
        
        # Example 5: Predict stress risk
        future_context = {
            'upcoming_meetings': 4,
            'deadline_proximity': 0.8,
            'current_hour': 14,
            'recent_high_stress': True
        }
        
        risk_prediction = await stress_service.predict_stress_risk(user_id, future_context)
        print(f"Stress risk prediction: {risk_prediction['risk_level']} ({risk_prediction['risk_score']:.2f})")
        
        # Let background tasks run briefly
        await asyncio.sleep(5)
        
        # Example 6: Get comprehensive analysis
        analysis = await stress_service.get_stress_analysis(user_id, days=7)
        if 'error' not in analysis:
            print(f"Stress analysis - Average level: {analysis['summary']['average_stress_level']:.1f}")
            print(f"High stress episodes: {analysis['summary']['high_stress_episodes']}")
            print(f"Interventions completed: {analysis['summary']['interventions_completed']}")
        
    finally:
        await stress_service.stop()


if __name__ == "__main__":
    asyncio.run(main())