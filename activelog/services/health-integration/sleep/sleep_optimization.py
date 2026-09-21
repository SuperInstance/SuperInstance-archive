"""
ActiveLog Health Integration - Sleep Pattern Optimization

This module provides comprehensive sleep tracking and optimization capabilities including:
- Sleep stage detection and analysis (light, deep, REM sleep)
- Sleep quality scoring and trends
- Personalized sleep recommendations and coaching
- Smart alarm and wake-up optimization
- Environmental factor correlation (temperature, light, noise)
- Sleep hygiene tracking and improvement suggestions
- Integration with wearable devices and sleep sensors
- Circadian rhythm analysis and optimization
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
from scipy import signal
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SleepStage(Enum):
    """Sleep stages based on sleep science"""
    AWAKE = "awake"
    LIGHT_SLEEP = "light_sleep"
    DEEP_SLEEP = "deep_sleep"
    REM_SLEEP = "rem_sleep"
    UNKNOWN = "unknown"


class SleepQualityFactor(Enum):
    """Factors affecting sleep quality"""
    SLEEP_DURATION = "sleep_duration"
    SLEEP_EFFICIENCY = "sleep_efficiency"
    SLEEP_LATENCY = "sleep_latency"
    WAKE_EPISODES = "wake_episodes"
    DEEP_SLEEP_PERCENTAGE = "deep_sleep_percentage"
    REM_PERCENTAGE = "rem_percentage"
    REGULARITY = "regularity"
    RESTFULNESS = "restfulness"


class SleepEnvironmentFactor(Enum):
    """Environmental factors that can affect sleep"""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    LIGHT_LEVEL = "light_level"
    NOISE_LEVEL = "noise_level"
    AIR_QUALITY = "air_quality"
    ROOM_DARKNESS = "room_darkness"


class SleepHygieneCategory(Enum):
    """Categories of sleep hygiene practices"""
    BEDTIME_ROUTINE = "bedtime_routine"
    EXERCISE = "exercise"
    DIET_AND_CAFFEINE = "diet_and_caffeine"
    SCREEN_TIME = "screen_time"
    STRESS_MANAGEMENT = "stress_management"
    SLEEP_ENVIRONMENT = "sleep_environment"


class SleepRecommendationType(Enum):
    """Types of sleep recommendations"""
    BEDTIME_ADJUSTMENT = "bedtime_adjustment"
    WAKE_TIME_ADJUSTMENT = "wake_time_adjustment"
    ENVIRONMENT_OPTIMIZATION = "environment_optimization"
    LIFESTYLE_CHANGE = "lifestyle_change"
    ROUTINE_IMPROVEMENT = "routine_improvement"
    MEDICAL_CONSULTATION = "medical_consultation"


class AlarmType(Enum):
    """Types of smart alarms"""
    LIGHT_SLEEP_WINDOW = "light_sleep_window"
    CIRCADIAN_OPTIMIZED = "circadian_optimized"
    GRADUAL_WAKE = "gradual_wake"
    NATURAL_LIGHT = "natural_light"
    TEMPERATURE_BASED = "temperature_based"


@dataclass
class SleepStageData:
    """Data for a specific sleep stage during a period"""
    stage: SleepStage
    start_time: datetime
    duration_minutes: float
    heart_rate_avg: Optional[float] = None
    heart_rate_variability: Optional[float] = None
    movement_score: Optional[float] = None
    breathing_rate: Optional[float] = None


@dataclass
class SleepSession:
    """Complete sleep session data"""
    session_id: str
    user_id: str
    bedtime: datetime
    sleep_time: datetime
    wake_time: datetime
    get_up_time: datetime
    total_sleep_time: float  # minutes
    sleep_efficiency: float  # percentage
    sleep_latency: float  # minutes to fall asleep
    wake_episodes: int
    stages: List[SleepStageData]
    average_heart_rate: Optional[float] = None
    heart_rate_variability: Optional[float] = None
    movement_score: float = 0.0
    environmental_data: Dict[SleepEnvironmentFactor, float] = field(default_factory=dict)
    subjective_rating: Optional[int] = None  # 1-10 scale
    notes: Optional[str] = None
    recorded_at: datetime = field(default_factory=datetime.now)


@dataclass
class SleepQualityScore:
    """Comprehensive sleep quality scoring"""
    score_id: str
    user_id: str
    session_id: str
    overall_score: float  # 0-100
    factor_scores: Dict[SleepQualityFactor, float]
    percentile_rank: Optional[float] = None
    improvement_areas: List[SleepQualityFactor] = field(default_factory=list)
    strengths: List[SleepQualityFactor] = field(default_factory=list)
    calculated_at: datetime = field(default_factory=datetime.now)


@dataclass
class SleepRecommendation:
    """Personalized sleep improvement recommendation"""
    recommendation_id: str
    user_id: str
    type: SleepRecommendationType
    title: str
    description: str
    priority: int  # 1-5, where 1 is highest priority
    expected_improvement: float  # expected score improvement
    implementation_difficulty: int  # 1-5, where 1 is easiest
    category: SleepHygieneCategory
    action_items: List[str]
    tracking_metrics: List[str]
    estimated_timeframe: str
    scientific_basis: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class SleepPattern:
    """User's sleep pattern analysis over time"""
    pattern_id: str
    user_id: str
    analysis_period: str  # "7d", "30d", "90d"
    average_bedtime: time
    average_wake_time: time
    average_sleep_duration: float
    sleep_duration_variability: float
    bedtime_consistency: float  # 0-100 score
    wake_time_consistency: float  # 0-100 score
    chronotype: str  # "morning_lark", "night_owl", "intermediate"
    optimal_sleep_window: Tuple[time, time]  # (bedtime, wake_time)
    sleep_debt: float  # cumulative sleep debt in hours
    trends: Dict[str, float]  # trending metrics
    analyzed_at: datetime = field(default_factory=datetime.now)


@dataclass
class SmartAlarm:
    """Smart alarm configuration and data"""
    alarm_id: str
    user_id: str
    target_wake_time: time
    wake_window: int  # minutes before target time to find optimal wake moment
    alarm_type: AlarmType
    enabled: bool
    days_of_week: Set[int]  # 0-6, Monday=0
    last_triggered: Optional[datetime] = None
    effectiveness_score: Optional[float] = None
    snooze_count: int = 0
    user_feedback: Optional[str] = None


@dataclass
class CircadianRhythm:
    """Circadian rhythm analysis and optimization"""
    analysis_id: str
    user_id: str
    phase_shift: float  # hours shift from average
    amplitude: float  # strength of rhythm
    period: float  # cycle length in hours (typically ~24)
    light_exposure_pattern: Dict[int, float]  # hour -> light level
    melatonin_prediction: Dict[int, float]  # hour -> predicted melatonin level
    optimal_light_therapy: List[Tuple[time, time, float]]  # (start, end, intensity)
    social_jet_lag: float  # difference between weekday and weekend patterns
    analyzed_at: datetime = field(default_factory=datetime.now)


@dataclass
class SleepHygieneMetrics:
    """Sleep hygiene tracking metrics"""
    metrics_id: str
    user_id: str
    date: datetime
    bedtime_routine_score: float  # 0-100
    screen_time_before_bed: float  # minutes
    caffeine_cutoff_time: Optional[time] = None
    alcohol_consumption: float = 0.0  # units
    exercise_timing: Optional[time] = None
    exercise_intensity: Optional[float] = None
    bedroom_temperature: Optional[float] = None
    bedroom_darkness: Optional[float] = None  # 0-100 scale
    stress_level: Optional[int] = None  # 1-10 scale
    nap_duration: float = 0.0  # minutes
    recorded_manually: bool = False


class SleepDataSource(ABC):
    """Abstract interface for sleep data sources"""
    
    @abstractmethod
    async def get_sleep_data(self, user_id: str, start_date: datetime, end_date: datetime) -> List[SleepSession]:
        """Get sleep data for a user within a date range"""
        pass
    
    @abstractmethod
    async def get_real_time_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get real-time sleep monitoring data"""
        pass
    
    @abstractmethod
    async def validate_data(self, session: SleepSession) -> bool:
        """Validate sleep session data"""
        pass


class SleepQualityAnalyzer(ABC):
    """Abstract interface for sleep quality analysis"""
    
    @abstractmethod
    async def calculate_quality_score(self, session: SleepSession) -> SleepQualityScore:
        """Calculate comprehensive sleep quality score"""
        pass
    
    @abstractmethod
    async def analyze_trends(self, user_id: str, sessions: List[SleepSession]) -> Dict[str, Any]:
        """Analyze sleep quality trends over time"""
        pass
    
    @abstractmethod
    async def identify_patterns(self, sessions: List[SleepSession]) -> SleepPattern:
        """Identify sleep patterns from session data"""
        pass


class RecommendationEngine(ABC):
    """Abstract interface for sleep recommendation generation"""
    
    @abstractmethod
    async def generate_recommendations(self, user_id: str, pattern: SleepPattern, 
                                     recent_scores: List[SleepQualityScore]) -> List[SleepRecommendation]:
        """Generate personalized sleep recommendations"""
        pass
    
    @abstractmethod
    async def prioritize_recommendations(self, recommendations: List[SleepRecommendation]) -> List[SleepRecommendation]:
        """Prioritize recommendations by impact and feasibility"""
        pass
    
    @abstractmethod
    async def track_recommendation_effectiveness(self, recommendation: SleepRecommendation, 
                                               before_scores: List[float], after_scores: List[float]) -> float:
        """Track the effectiveness of recommendations"""
        pass


class WearableDeviceSleepSource(SleepDataSource):
    """Sleep data source from wearable devices"""
    
    def __init__(self, device_integrations: Dict[str, Any]):
        self.device_integrations = device_integrations
        self.data_cache: Dict[str, List[SleepSession]] = {}
    
    async def get_sleep_data(self, user_id: str, start_date: datetime, end_date: datetime) -> List[SleepSession]:
        """Get sleep data from connected wearable devices"""
        try:
            sessions = []
            
            # Check cache first
            cache_key = f"{user_id}_{start_date.date()}_{end_date.date()}"
            if cache_key in self.data_cache:
                return self.data_cache[cache_key]
            
            # Simulate getting data from various wearable devices
            for device_type, integration in self.device_integrations.items():
                device_sessions = await self._get_device_data(device_type, user_id, start_date, end_date)
                sessions.extend(device_sessions)
            
            # Remove duplicates and merge overlapping sessions
            sessions = await self._merge_sessions(sessions)
            
            # Cache the results
            self.data_cache[cache_key] = sessions
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting sleep data: {e}")
            return []
    
    async def get_real_time_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get real-time sleep monitoring data"""
        try:
            # Simulate real-time data from wearable device
            import random
            
            current_hour = datetime.now().hour
            
            if 22 <= current_hour or current_hour <= 8:  # Night time
                return {
                    'is_sleeping': random.choice([True, False]),
                    'current_stage': random.choice(list(SleepStage)).value,
                    'heart_rate': random.randint(45, 80),
                    'movement': random.uniform(0, 10),
                    'environment': {
                        'temperature': random.uniform(18, 24),
                        'light_level': random.uniform(0, 5),
                        'noise_level': random.uniform(20, 40)
                    }
                }
            else:
                return {'is_sleeping': False}
                
        except Exception as e:
            logger.error(f"Error getting real-time data: {e}")
            return None
    
    async def validate_data(self, session: SleepSession) -> bool:
        """Validate sleep session data"""
        try:
            # Basic validation checks
            if session.sleep_time >= session.wake_time:
                return False
            
            if session.total_sleep_time < 0 or session.total_sleep_time > 24 * 60:
                return False
            
            if session.sleep_efficiency < 0 or session.sleep_efficiency > 100:
                return False
            
            # Check stage consistency
            total_stage_time = sum(stage.duration_minutes for stage in session.stages)
            if abs(total_stage_time - session.total_sleep_time) > 30:  # 30 minute tolerance
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating sleep data: {e}")
            return False
    
    async def _get_device_data(self, device_type: str, user_id: str, start_date: datetime, end_date: datetime) -> List[SleepSession]:
        """Get data from a specific device type"""
        sessions = []
        
        # Simulate different device data formats
        current_date = start_date
        while current_date <= end_date:
            # Generate a sleep session for each night
            bedtime = current_date.replace(hour=22, minute=30) + timedelta(minutes=np.random.randint(-60, 60))
            sleep_time = bedtime + timedelta(minutes=np.random.randint(5, 30))
            wake_time = sleep_time + timedelta(minutes=np.random.randint(360, 540))  # 6-9 hours
            get_up_time = wake_time + timedelta(minutes=np.random.randint(0, 30))
            
            # Generate sleep stages
            stages = await self._generate_sleep_stages(sleep_time, wake_time)
            
            session = SleepSession(
                session_id=str(uuid4()),
                user_id=user_id,
                bedtime=bedtime,
                sleep_time=sleep_time,
                wake_time=wake_time,
                get_up_time=get_up_time,
                total_sleep_time=(wake_time - sleep_time).total_seconds() / 60,
                sleep_efficiency=np.random.uniform(75, 95),
                sleep_latency=(sleep_time - bedtime).total_seconds() / 60,
                wake_episodes=np.random.randint(0, 5),
                stages=stages,
                average_heart_rate=np.random.uniform(50, 70),
                heart_rate_variability=np.random.uniform(20, 60),
                movement_score=np.random.uniform(1, 10),
                environmental_data={
                    SleepEnvironmentFactor.TEMPERATURE: np.random.uniform(18, 24),
                    SleepEnvironmentFactor.NOISE_LEVEL: np.random.uniform(25, 45),
                    SleepEnvironmentFactor.LIGHT_LEVEL: np.random.uniform(0, 5)
                }
            )
            
            sessions.append(session)
            current_date += timedelta(days=1)
        
        return sessions
    
    async def _generate_sleep_stages(self, sleep_time: datetime, wake_time: datetime) -> List[SleepStageData]:
        """Generate realistic sleep stage progression"""
        stages = []
        current_time = sleep_time
        total_minutes = (wake_time - sleep_time).total_seconds() / 60
        
        # Simulate sleep cycles (typically 90-110 minutes each)
        cycle_length = 100  # minutes
        num_cycles = int(total_minutes // cycle_length)
        
        for cycle in range(num_cycles):
            cycle_start = current_time
            
            # Light sleep (N1/N2) - 45-55% of cycle
            light_duration = cycle_length * np.random.uniform(0.45, 0.55)
            stages.append(SleepStageData(
                stage=SleepStage.LIGHT_SLEEP,
                start_time=current_time,
                duration_minutes=light_duration,
                heart_rate_avg=np.random.uniform(55, 70),
                movement_score=np.random.uniform(2, 5)
            ))
            current_time += timedelta(minutes=light_duration)
            
            # Deep sleep (N3) - 15-25% of cycle
            deep_duration = cycle_length * np.random.uniform(0.15, 0.25)
            stages.append(SleepStageData(
                stage=SleepStage.DEEP_SLEEP,
                start_time=current_time,
                duration_minutes=deep_duration,
                heart_rate_avg=np.random.uniform(45, 60),
                movement_score=np.random.uniform(0, 2)
            ))
            current_time += timedelta(minutes=deep_duration)
            
            # REM sleep - 20-25% of cycle
            rem_duration = cycle_length * np.random.uniform(0.20, 0.25)
            stages.append(SleepStageData(
                stage=SleepStage.REM_SLEEP,
                start_time=current_time,
                duration_minutes=rem_duration,
                heart_rate_avg=np.random.uniform(65, 80),
                movement_score=np.random.uniform(0, 1)
            ))
            current_time += timedelta(minutes=rem_duration)
            
            # Brief wake episodes
            if cycle < num_cycles - 1 and np.random.random() < 0.3:
                wake_duration = np.random.uniform(1, 5)
                stages.append(SleepStageData(
                    stage=SleepStage.AWAKE,
                    start_time=current_time,
                    duration_minutes=wake_duration,
                    heart_rate_avg=np.random.uniform(70, 90),
                    movement_score=np.random.uniform(5, 10)
                ))
                current_time += timedelta(minutes=wake_duration)
        
        return stages
    
    async def _merge_sessions(self, sessions: List[SleepSession]) -> List[SleepSession]:
        """Merge overlapping sessions from different devices"""
        # Simple implementation - in practice, would use more sophisticated merging
        unique_sessions = {}
        
        for session in sessions:
            date_key = session.sleep_time.date()
            if date_key not in unique_sessions:
                unique_sessions[date_key] = session
            else:
                # Keep the session with more complete data
                existing = unique_sessions[date_key]
                if len(session.stages) > len(existing.stages):
                    unique_sessions[date_key] = session
        
        return list(unique_sessions.values())


class ComprehensiveSleepQualityAnalyzer(SleepQualityAnalyzer):
    """Comprehensive sleep quality analysis implementation"""
    
    def __init__(self):
        self.ideal_ranges = {
            SleepQualityFactor.SLEEP_DURATION: (7 * 60, 9 * 60),  # 7-9 hours in minutes
            SleepQualityFactor.SLEEP_EFFICIENCY: (85, 100),  # 85-100%
            SleepQualityFactor.SLEEP_LATENCY: (5, 20),  # 5-20 minutes
            SleepQualityFactor.WAKE_EPISODES: (0, 2),  # 0-2 times
            SleepQualityFactor.DEEP_SLEEP_PERCENTAGE: (15, 25),  # 15-25% of total sleep
            SleepQualityFactor.REM_PERCENTAGE: (20, 25),  # 20-25% of total sleep
            SleepQualityFactor.REGULARITY: (80, 100),  # consistency score
            SleepQualityFactor.RESTFULNESS: (70, 100)  # subjective feeling
        }
    
    async def calculate_quality_score(self, session: SleepSession) -> SleepQualityScore:
        """Calculate comprehensive sleep quality score"""
        try:
            factor_scores = {}
            
            # Sleep Duration Score
            duration_score = await self._score_sleep_duration(session.total_sleep_time)
            factor_scores[SleepQualityFactor.SLEEP_DURATION] = duration_score
            
            # Sleep Efficiency Score
            efficiency_score = await self._score_sleep_efficiency(session.sleep_efficiency)
            factor_scores[SleepQualityFactor.SLEEP_EFFICIENCY] = efficiency_score
            
            # Sleep Latency Score
            latency_score = await self._score_sleep_latency(session.sleep_latency)
            factor_scores[SleepQualityFactor.SLEEP_LATENCY] = latency_score
            
            # Wake Episodes Score
            wake_score = await self._score_wake_episodes(session.wake_episodes)
            factor_scores[SleepQualityFactor.WAKE_EPISODES] = wake_score
            
            # Deep Sleep Percentage Score
            deep_sleep_score = await self._score_deep_sleep_percentage(session)
            factor_scores[SleepQualityFactor.DEEP_SLEEP_PERCENTAGE] = deep_sleep_score
            
            # REM Percentage Score
            rem_score = await self._score_rem_percentage(session)
            factor_scores[SleepQualityFactor.REM_PERCENTAGE] = rem_score
            
            # Restfulness Score (if available)
            if session.subjective_rating:
                restfulness_score = (session.subjective_rating / 10) * 100
                factor_scores[SleepQualityFactor.RESTFULNESS] = restfulness_score
            
            # Calculate overall score (weighted average)
            weights = {
                SleepQualityFactor.SLEEP_DURATION: 0.20,
                SleepQualityFactor.SLEEP_EFFICIENCY: 0.20,
                SleepQualityFactor.SLEEP_LATENCY: 0.15,
                SleepQualityFactor.WAKE_EPISODES: 0.15,
                SleepQualityFactor.DEEP_SLEEP_PERCENTAGE: 0.15,
                SleepQualityFactor.REM_PERCENTAGE: 0.15
            }
            
            if SleepQualityFactor.RESTFULNESS in factor_scores:
                # Adjust weights to include restfulness
                for factor in weights:
                    weights[factor] *= 0.85  # Scale down other factors
                weights[SleepQualityFactor.RESTFULNESS] = 0.15
            
            overall_score = sum(score * weights.get(factor, 0) 
                               for factor, score in factor_scores.items())
            
            # Identify improvement areas and strengths
            improvement_areas = [factor for factor, score in factor_scores.items() if score < 70]
            strengths = [factor for factor, score in factor_scores.items() if score >= 85]
            
            return SleepQualityScore(
                score_id=str(uuid4()),
                user_id=session.user_id,
                session_id=session.session_id,
                overall_score=overall_score,
                factor_scores=factor_scores,
                improvement_areas=improvement_areas,
                strengths=strengths
            )
            
        except Exception as e:
            logger.error(f"Error calculating sleep quality score: {e}")
            return SleepQualityScore(
                score_id=str(uuid4()),
                user_id=session.user_id,
                session_id=session.session_id,
                overall_score=0.0,
                factor_scores={}
            )
    
    async def analyze_trends(self, user_id: str, sessions: List[SleepSession]) -> Dict[str, Any]:
        """Analyze sleep quality trends over time"""
        if not sessions:
            return {}
        
        # Sort sessions by date
        sorted_sessions = sorted(sessions, key=lambda x: x.sleep_time)
        
        # Calculate scores for all sessions
        scores = []
        for session in sorted_sessions:
            score = await self.calculate_quality_score(session)
            scores.append(score)
        
        # Analyze trends
        overall_scores = [score.overall_score for score in scores]
        
        trends = {
            'score_trend': await self._calculate_trend(overall_scores),
            'average_score': statistics.mean(overall_scores),
            'score_variability': statistics.stdev(overall_scores) if len(overall_scores) > 1 else 0,
            'improvement_rate': await self._calculate_improvement_rate(overall_scores),
            'best_week_score': max(overall_scores) if overall_scores else 0,
            'worst_week_score': min(overall_scores) if overall_scores else 0
        }
        
        # Factor-specific trends
        for factor in SleepQualityFactor:
            factor_scores = [score.factor_scores.get(factor, 0) for score in scores if factor in score.factor_scores]
            if factor_scores:
                trends[f'{factor.value}_trend'] = await self._calculate_trend(factor_scores)
                trends[f'{factor.value}_average'] = statistics.mean(factor_scores)
        
        return trends
    
    async def identify_patterns(self, sessions: List[SleepSession]) -> SleepPattern:
        """Identify sleep patterns from session data"""
        if not sessions:
            raise ValueError("No sessions provided for pattern analysis")
        
        user_id = sessions[0].user_id
        
        # Extract timing data
        bedtimes = []
        wake_times = []
        durations = []
        
        weekday_bedtimes = []
        weekend_bedtimes = []
        weekday_wake_times = []
        weekend_wake_times = []
        
        for session in sessions:
            bedtime_minutes = session.bedtime.hour * 60 + session.bedtime.minute
            wake_time_minutes = session.wake_time.hour * 60 + session.wake_time.minute
            
            bedtimes.append(bedtime_minutes)
            wake_times.append(wake_time_minutes)
            durations.append(session.total_sleep_time)
            
            # Separate weekday vs weekend
            if session.bedtime.weekday() < 5:  # Monday = 0, Friday = 4
                weekday_bedtimes.append(bedtime_minutes)
                weekday_wake_times.append(wake_time_minutes)
            else:
                weekend_bedtimes.append(bedtime_minutes)
                weekend_wake_times.append(wake_time_minutes)
        
        # Calculate averages
        avg_bedtime = statistics.mean(bedtimes)
        avg_wake_time = statistics.mean(wake_times)
        avg_duration = statistics.mean(durations)
        
        # Calculate variability
        bedtime_variability = statistics.stdev(bedtimes) if len(bedtimes) > 1 else 0
        wake_time_variability = statistics.stdev(wake_times) if len(wake_times) > 1 else 0
        duration_variability = statistics.stdev(durations) if len(durations) > 1 else 0
        
        # Consistency scores (higher variability = lower consistency)
        bedtime_consistency = max(0, 100 - (bedtime_variability / 60 * 100))  # Convert to 0-100 scale
        wake_time_consistency = max(0, 100 - (wake_time_variability / 60 * 100))
        
        # Determine chronotype based on average bedtime and wake time
        chronotype = await self._determine_chronotype(avg_bedtime, avg_wake_time)
        
        # Calculate optimal sleep window
        optimal_bedtime = time(hour=int(avg_bedtime // 60), minute=int(avg_bedtime % 60))
        optimal_wake_time = time(hour=int(avg_wake_time // 60), minute=int(avg_wake_time % 60))
        
        # Calculate sleep debt (simplified)
        target_sleep = 8 * 60  # 8 hours in minutes
        sleep_debt = sum(max(0, target_sleep - duration) for duration in durations) / 60  # Convert to hours
        
        # Calculate social jet lag
        social_jet_lag = 0.0
        if weekday_bedtimes and weekend_bedtimes:
            weekday_avg = statistics.mean(weekday_bedtimes)
            weekend_avg = statistics.mean(weekend_bedtimes)
            social_jet_lag = abs(weekend_avg - weekday_avg) / 60  # Convert to hours
        
        return SleepPattern(
            pattern_id=str(uuid4()),
            user_id=user_id,
            analysis_period=f"{len(sessions)}d",
            average_bedtime=optimal_bedtime,
            average_wake_time=optimal_wake_time,
            average_sleep_duration=avg_duration,
            sleep_duration_variability=duration_variability,
            bedtime_consistency=bedtime_consistency,
            wake_time_consistency=wake_time_consistency,
            chronotype=chronotype,
            optimal_sleep_window=(optimal_bedtime, optimal_wake_time),
            sleep_debt=sleep_debt,
            trends={'social_jet_lag': social_jet_lag}
        )
    
    async def _score_sleep_duration(self, duration_minutes: float) -> float:
        """Score sleep duration (0-100)"""
        ideal_min, ideal_max = self.ideal_ranges[SleepQualityFactor.SLEEP_DURATION]
        
        if ideal_min <= duration_minutes <= ideal_max:
            return 100.0
        elif duration_minutes < ideal_min:
            # Penalize short sleep more severely
            deviation = ideal_min - duration_minutes
            return max(0, 100 - (deviation / 60) * 20)  # -20 points per hour short
        else:
            # Penalize long sleep less severely
            deviation = duration_minutes - ideal_max
            return max(0, 100 - (deviation / 60) * 10)  # -10 points per hour over
    
    async def _score_sleep_efficiency(self, efficiency: float) -> float:
        """Score sleep efficiency (0-100)"""
        ideal_min, ideal_max = self.ideal_ranges[SleepQualityFactor.SLEEP_EFFICIENCY]
        
        if efficiency >= ideal_min:
            return min(100, efficiency)
        else:
            return (efficiency / ideal_min) * 100
    
    async def _score_sleep_latency(self, latency_minutes: float) -> float:
        """Score sleep latency (0-100)"""
        ideal_min, ideal_max = self.ideal_ranges[SleepQualityFactor.SLEEP_LATENCY]
        
        if ideal_min <= latency_minutes <= ideal_max:
            return 100.0
        elif latency_minutes < ideal_min:
            # Very quick sleep onset might indicate sleep debt
            return 80.0
        else:
            # Long sleep latency is problematic
            excess = latency_minutes - ideal_max
            return max(0, 100 - excess * 2)  # -2 points per minute over 20
    
    async def _score_wake_episodes(self, wake_episodes: int) -> float:
        """Score wake episodes (0-100)"""
        ideal_min, ideal_max = self.ideal_ranges[SleepQualityFactor.WAKE_EPISODES]
        
        if wake_episodes <= ideal_max:
            return 100.0
        else:
            excess = wake_episodes - ideal_max
            return max(0, 100 - excess * 15)  # -15 points per extra wake episode
    
    async def _score_deep_sleep_percentage(self, session: SleepSession) -> float:
        """Score deep sleep percentage (0-100)"""
        if not session.stages:
            return 50.0  # Default score if no stage data
        
        total_sleep_time = sum(stage.duration_minutes for stage in session.stages 
                              if stage.stage != SleepStage.AWAKE)
        deep_sleep_time = sum(stage.duration_minutes for stage in session.stages 
                             if stage.stage == SleepStage.DEEP_SLEEP)
        
        if total_sleep_time == 0:
            return 0.0
        
        deep_sleep_percentage = (deep_sleep_time / total_sleep_time) * 100
        ideal_min, ideal_max = self.ideal_ranges[SleepQualityFactor.DEEP_SLEEP_PERCENTAGE]
        
        if ideal_min <= deep_sleep_percentage <= ideal_max:
            return 100.0
        elif deep_sleep_percentage < ideal_min:
            return (deep_sleep_percentage / ideal_min) * 100
        else:
            # Too much deep sleep is unusual but not necessarily bad
            return 90.0
    
    async def _score_rem_percentage(self, session: SleepSession) -> float:
        """Score REM sleep percentage (0-100)"""
        if not session.stages:
            return 50.0  # Default score if no stage data
        
        total_sleep_time = sum(stage.duration_minutes for stage in session.stages 
                              if stage.stage != SleepStage.AWAKE)
        rem_sleep_time = sum(stage.duration_minutes for stage in session.stages 
                            if stage.stage == SleepStage.REM_SLEEP)
        
        if total_sleep_time == 0:
            return 0.0
        
        rem_sleep_percentage = (rem_sleep_time / total_sleep_time) * 100
        ideal_min, ideal_max = self.ideal_ranges[SleepQualityFactor.REM_PERCENTAGE]
        
        if ideal_min <= rem_sleep_percentage <= ideal_max:
            return 100.0
        elif rem_sleep_percentage < ideal_min:
            return (rem_sleep_percentage / ideal_min) * 100
        else:
            # Slightly too much REM is less concerning than too little
            return 95.0
    
    async def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a series of values"""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear trend analysis
        x = list(range(len(values)))
        correlation = np.corrcoef(x, values)[0, 1]
        
        if correlation > 0.3:
            return "improving"
        elif correlation < -0.3:
            return "declining"
        else:
            return "stable"
    
    async def _calculate_improvement_rate(self, scores: List[float]) -> float:
        """Calculate rate of improvement in scores"""
        if len(scores) < 2:
            return 0.0
        
        # Calculate average change per period
        total_change = scores[-1] - scores[0]
        periods = len(scores) - 1
        
        return total_change / periods
    
    async def _determine_chronotype(self, avg_bedtime_minutes: float, avg_wake_time_minutes: float) -> str:
        """Determine chronotype based on sleep timing"""
        # Convert to hours for easier comparison
        bedtime_hour = avg_bedtime_minutes / 60
        wake_time_hour = avg_wake_time_minutes / 60
        
        # Adjust for next-day wake times (e.g., 7 AM = 31 hours from start of previous day)
        if wake_time_hour < bedtime_hour:
            wake_time_hour += 24
        
        midpoint = (bedtime_hour + wake_time_hour) / 2
        
        # Classify based on sleep midpoint
        if midpoint < 2.5:  # Before 2:30 AM
            return "morning_lark"
        elif midpoint > 4.5:  # After 4:30 AM
            return "night_owl"
        else:
            return "intermediate"


class IntelligentRecommendationEngine(RecommendationEngine):
    """Intelligent sleep recommendation engine"""
    
    def __init__(self):
        self.recommendation_templates = {
            SleepRecommendationType.BEDTIME_ADJUSTMENT: {
                'title': 'Optimize Your Bedtime',
                'category': SleepHygieneCategory.BEDTIME_ROUTINE,
                'scientific_basis': 'Consistent sleep timing helps regulate circadian rhythms'
            },
            SleepRecommendationType.ENVIRONMENT_OPTIMIZATION: {
                'title': 'Improve Sleep Environment',
                'category': SleepHygieneCategory.SLEEP_ENVIRONMENT,
                'scientific_basis': 'Optimal temperature (65-68°F) and darkness promote better sleep quality'
            },
            SleepRecommendationType.LIFESTYLE_CHANGE: {
                'title': 'Adjust Daily Habits',
                'category': SleepHygieneCategory.EXERCISE,
                'scientific_basis': 'Regular exercise and limited caffeine improve sleep quality'
            }
        }
    
    async def generate_recommendations(self, user_id: str, pattern: SleepPattern, 
                                     recent_scores: List[SleepQualityScore]) -> List[SleepRecommendation]:
        """Generate personalized sleep recommendations"""
        recommendations = []
        
        if not recent_scores:
            return recommendations
        
        # Analyze recent performance
        avg_score = statistics.mean(score.overall_score for score in recent_scores)
        common_weaknesses = await self._identify_common_weaknesses(recent_scores)
        
        # Generate recommendations based on weaknesses
        for weakness in common_weaknesses:
            rec = await self._create_recommendation_for_weakness(user_id, weakness, pattern, avg_score)
            if rec:
                recommendations.append(rec)
        
        # Add pattern-specific recommendations
        pattern_recs = await self._generate_pattern_based_recommendations(user_id, pattern)
        recommendations.extend(pattern_recs)
        
        # Prioritize recommendations
        return await self.prioritize_recommendations(recommendations)
    
    async def prioritize_recommendations(self, recommendations: List[SleepRecommendation]) -> List[SleepRecommendation]:
        """Prioritize recommendations by impact and feasibility"""
        def priority_score(rec: SleepRecommendation) -> float:
            # Combine expected improvement and ease of implementation
            impact_score = rec.expected_improvement * 10  # Scale up impact
            ease_score = (6 - rec.implementation_difficulty) * 5  # Easier = higher score
            priority_bonus = (6 - rec.priority) * 3  # Higher priority = higher score
            
            return impact_score + ease_score + priority_bonus
        
        # Sort by priority score (descending)
        sorted_recommendations = sorted(recommendations, key=priority_score, reverse=True)
        
        # Update priority values based on new order
        for i, rec in enumerate(sorted_recommendations):
            rec.priority = i + 1
        
        return sorted_recommendations
    
    async def track_recommendation_effectiveness(self, recommendation: SleepRecommendation, 
                                               before_scores: List[float], after_scores: List[float]) -> float:
        """Track the effectiveness of recommendations"""
        if not before_scores or not after_scores:
            return 0.0
        
        before_avg = statistics.mean(before_scores)
        after_avg = statistics.mean(after_scores)
        
        improvement = after_avg - before_avg
        
        # Normalize by expected improvement
        effectiveness = (improvement / recommendation.expected_improvement) * 100 if recommendation.expected_improvement > 0 else 0
        
        return max(0, min(200, effectiveness))  # Cap at 200% effectiveness
    
    async def _identify_common_weaknesses(self, scores: List[SleepQualityScore]) -> List[SleepQualityFactor]:
        """Identify factors that consistently score poorly"""
        factor_averages = {}
        
        for factor in SleepQualityFactor:
            factor_scores = []
            for score in scores:
                if factor in score.factor_scores:
                    factor_scores.append(score.factor_scores[factor])
            
            if factor_scores:
                factor_averages[factor] = statistics.mean(factor_scores)
        
        # Return factors with average scores below 70
        weaknesses = [factor for factor, avg_score in factor_averages.items() if avg_score < 70]
        
        # Sort by severity (lowest scores first)
        weaknesses.sort(key=lambda f: factor_averages[f])
        
        return weaknesses
    
    async def _create_recommendation_for_weakness(self, user_id: str, weakness: SleepQualityFactor, 
                                                pattern: SleepPattern, avg_score: float) -> Optional[SleepRecommendation]:
        """Create a specific recommendation for a weakness"""
        if weakness == SleepQualityFactor.SLEEP_DURATION:
            if pattern.average_sleep_duration < 7 * 60:  # Less than 7 hours
                return SleepRecommendation(
                    recommendation_id=str(uuid4()),
                    user_id=user_id,
                    type=SleepRecommendationType.BEDTIME_ADJUSTMENT,
                    title="Increase Sleep Duration",
                    description="Your average sleep is below the recommended 7-9 hours. Try going to bed 30 minutes earlier.",
                    priority=1,
                    expected_improvement=15.0,
                    implementation_difficulty=2,
                    category=SleepHygieneCategory.BEDTIME_ROUTINE,
                    action_items=[
                        "Set a bedtime alarm 30 minutes earlier than current bedtime",
                        "Start winding down 1 hour before new bedtime",
                        "Avoid screens 30 minutes before bed"
                    ],
                    tracking_metrics=["bedtime", "total_sleep_time", "sleep_quality_score"],
                    estimated_timeframe="2-3 weeks",
                    scientific_basis="Adults need 7-9 hours of sleep for optimal health and cognitive function"
                )
        
        elif weakness == SleepQualityFactor.SLEEP_LATENCY:
            return SleepRecommendation(
                recommendation_id=str(uuid4()),
                user_id=user_id,
                type=SleepRecommendationType.ROUTINE_IMPROVEMENT,
                title="Improve Sleep Onset",
                description="It's taking you too long to fall asleep. Let's create a better bedtime routine.",
                priority=2,
                expected_improvement=12.0,
                implementation_difficulty=3,
                category=SleepHygieneCategory.BEDTIME_ROUTINE,
                action_items=[
                    "Practice relaxation techniques before bed (deep breathing, meditation)",
                    "Keep bedroom cool (65-68°F) and dark",
                    "Avoid caffeine after 2 PM",
                    "Try reading a book instead of using electronic devices"
                ],
                tracking_metrics=["sleep_latency", "bedtime_routine_score"],
                estimated_timeframe="1-2 weeks",
                scientific_basis="Consistent bedtime routines help signal to your brain that it's time to sleep"
            )
        
        elif weakness == SleepQualityFactor.SLEEP_EFFICIENCY:
            return SleepRecommendation(
                recommendation_id=str(uuid4()),
                user_id=user_id,
                type=SleepRecommendationType.ENVIRONMENT_OPTIMIZATION,
                title="Reduce Sleep Disruptions",
                description="You're experiencing frequent awakenings. Let's optimize your sleep environment.",
                priority=2,
                expected_improvement=10.0,
                implementation_difficulty=2,
                category=SleepHygieneCategory.SLEEP_ENVIRONMENT,
                action_items=[
                    "Use blackout curtains or eye mask",
                    "Try white noise machine or earplugs",
                    "Ensure room temperature is 65-68°F",
                    "Remove electronic devices from bedroom"
                ],
                tracking_metrics=["sleep_efficiency", "wake_episodes", "environmental_factors"],
                estimated_timeframe="1 week",
                scientific_basis="Optimal sleep environments minimize disruptions and promote deeper sleep"
            )
        
        return None
    
    async def _generate_pattern_based_recommendations(self, user_id: str, pattern: SleepPattern) -> List[SleepRecommendation]:
        """Generate recommendations based on sleep patterns"""
        recommendations = []
        
        # Consistency recommendations
        if pattern.bedtime_consistency < 80:
            recommendations.append(SleepRecommendation(
                recommendation_id=str(uuid4()),
                user_id=user_id,
                type=SleepRecommendationType.BEDTIME_ADJUSTMENT,
                title="Improve Sleep Schedule Consistency",
                description=f"Your bedtime varies significantly. Consistent sleep timing improves sleep quality.",
                priority=3,
                expected_improvement=8.0,
                implementation_difficulty=3,
                category=SleepHygieneCategory.BEDTIME_ROUTINE,
                action_items=[
                    "Choose a consistent bedtime and wake time",
                    "Use bedtime reminders on your phone",
                    "Avoid sleeping in on weekends (limit to 1 hour extra)",
                    "Gradually adjust current schedule by 15 minutes per day"
                ],
                tracking_metrics=["bedtime_consistency", "wake_time_consistency"],
                estimated_timeframe="3-4 weeks",
                scientific_basis="Consistent sleep schedules help maintain circadian rhythm alignment"
            ))
        
        # Social jet lag recommendations
        social_jet_lag = pattern.trends.get('social_jet_lag', 0)
        if social_jet_lag > 1.5:  # More than 1.5 hours difference
            recommendations.append(SleepRecommendation(
                recommendation_id=str(uuid4()),
                user_id=user_id,
                type=SleepRecommendationType.LIFESTYLE_CHANGE,
                title="Reduce Social Jet Lag",
                description="Large differences between weekday and weekend sleep patterns can disrupt your circadian rhythm.",
                priority=4,
                expected_improvement=6.0,
                implementation_difficulty=4,
                category=SleepHygieneCategory.BEDTIME_ROUTINE,
                action_items=[
                    "Try to keep weekend bedtime within 1 hour of weekday bedtime",
                    "Use light exposure in the morning to maintain rhythm",
                    "Avoid excessive weekend sleep-ins",
                    "Plan social activities earlier on weekends"
                ],
                tracking_metrics=["weekend_bedtime", "weekday_bedtime", "social_jet_lag"],
                estimated_timeframe="4-6 weeks",
                scientific_basis="Social jet lag is associated with metabolic and mood disruptions"
            ))
        
        # Sleep debt recommendations
        if pattern.sleep_debt > 10:  # More than 10 hours of cumulative sleep debt
            recommendations.append(SleepRecommendation(
                recommendation_id=str(uuid4()),
                user_id=user_id,
                type=SleepRecommendationType.BEDTIME_ADJUSTMENT,
                title="Address Sleep Debt",
                description=f"You have accumulated {pattern.sleep_debt:.1f} hours of sleep debt. Let's create a recovery plan.",
                priority=1,
                expected_improvement=12.0,
                implementation_difficulty=2,
                category=SleepHygieneCategory.BEDTIME_ROUTINE,
                action_items=[
                    "Go to bed 30-60 minutes earlier for the next week",
                    "Avoid naps longer than 20 minutes",
                    "Consider a short nap (10-20 min) in early afternoon if very tired",
                    "Gradually return to normal schedule once debt is reduced"
                ],
                tracking_metrics=["sleep_debt", "total_sleep_time", "energy_levels"],
                estimated_timeframe="1-2 weeks",
                scientific_basis="Sleep debt accumulates and can only be repaid with additional sleep"
            ))
        
        return recommendations


class SleepOptimization:
    """Main sleep pattern optimization service"""
    
    def __init__(self,
                 data_source: SleepDataSource,
                 quality_analyzer: SleepQualityAnalyzer,
                 recommendation_engine: RecommendationEngine):
        self.data_source = data_source
        self.quality_analyzer = quality_analyzer
        self.recommendation_engine = recommendation_engine
        
        # In-memory storage (replace with database in production)
        self.sleep_sessions: Dict[str, List[SleepSession]] = {}
        self.quality_scores: Dict[str, List[SleepQualityScore]] = {}
        self.sleep_patterns: Dict[str, SleepPattern] = {}
        self.recommendations: Dict[str, List[SleepRecommendation]] = {}
        self.smart_alarms: Dict[str, List[SmartAlarm]] = {}
        self.circadian_rhythms: Dict[str, CircadianRhythm] = {}
        self.hygiene_metrics: Dict[str, List[SleepHygieneMetrics]] = {}
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._running = False
    
    async def start(self):
        """Start the sleep optimization service"""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting Sleep Optimization Service")
        
        # Start background tasks
        self._background_tasks = [
            asyncio.create_task(self._sync_sleep_data()),
            asyncio.create_task(self._analyze_patterns()),
            asyncio.create_task(self._generate_recommendations_periodic()),
            asyncio.create_task(self._process_smart_alarms()),
            asyncio.create_task(self._monitor_real_time_data())
        ]
    
    async def stop(self):
        """Stop the sleep optimization service"""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping Sleep Optimization Service")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
    
    async def get_sleep_analysis(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive sleep analysis for a user"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get recent sleep sessions
            sessions = await self.data_source.get_sleep_data(user_id, start_date, end_date)
            
            if not sessions:
                return {'error': 'No sleep data available'}
            
            # Calculate quality scores
            quality_scores = []
            for session in sessions:
                score = await self.quality_analyzer.calculate_quality_score(session)
                quality_scores.append(score)
            
            # Analyze patterns
            pattern = await self.quality_analyzer.identify_patterns(sessions)
            
            # Get trends
            trends = await self.quality_analyzer.analyze_trends(user_id, sessions)
            
            # Get current recommendations
            current_recommendations = self.recommendations.get(user_id, [])
            active_recommendations = [rec for rec in current_recommendations if rec.is_active]
            
            return {
                'summary': {
                    'total_nights': len(sessions),
                    'average_sleep_duration': pattern.average_sleep_duration / 60,  # Convert to hours
                    'average_quality_score': statistics.mean(score.overall_score for score in quality_scores),
                    'sleep_efficiency': statistics.mean(session.sleep_efficiency for session in sessions),
                    'chronotype': pattern.chronotype
                },
                'pattern': pattern,
                'trends': trends,
                'recent_scores': quality_scores[-7:],  # Last 7 nights
                'recommendations': active_recommendations[:5],  # Top 5 recommendations
                'sleep_debt': pattern.sleep_debt,
                'consistency_scores': {
                    'bedtime': pattern.bedtime_consistency,
                    'wake_time': pattern.wake_time_consistency
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting sleep analysis: {e}")
            return {'error': str(e)}
    
    async def add_sleep_session(self, user_id: str, session: SleepSession) -> bool:
        """Add a new sleep session"""
        try:
            # Validate session
            if not await self.data_source.validate_data(session):
                logger.warning(f"Invalid sleep session data for user {user_id}")
                return False
            
            # Store session
            if user_id not in self.sleep_sessions:
                self.sleep_sessions[user_id] = []
            
            self.sleep_sessions[user_id].append(session)
            
            # Calculate quality score
            quality_score = await self.quality_analyzer.calculate_quality_score(session)
            
            if user_id not in self.quality_scores:
                self.quality_scores[user_id] = []
            
            self.quality_scores[user_id].append(quality_score)
            
            logger.info(f"Added sleep session for user {user_id}, quality score: {quality_score.overall_score:.1f}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding sleep session: {e}")
            return False
    
    async def create_smart_alarm(self, user_id: str, target_wake_time: time, 
                                wake_window: int = 30, alarm_type: AlarmType = AlarmType.LIGHT_SLEEP_WINDOW,
                                days_of_week: Optional[Set[int]] = None) -> SmartAlarm:
        """Create a smart alarm for optimal wake timing"""
        if days_of_week is None:
            days_of_week = {0, 1, 2, 3, 4}  # Weekdays by default
        
        alarm = SmartAlarm(
            alarm_id=str(uuid4()),
            user_id=user_id,
            target_wake_time=target_wake_time,
            wake_window=wake_window,
            alarm_type=alarm_type,
            enabled=True,
            days_of_week=days_of_week
        )
        
        # Store alarm
        if user_id not in self.smart_alarms:
            self.smart_alarms[user_id] = []
        
        self.smart_alarms[user_id].append(alarm)
        
        logger.info(f"Created smart alarm for user {user_id} at {target_wake_time}")
        return alarm
    
    async def log_sleep_hygiene(self, user_id: str, metrics: SleepHygieneMetrics) -> bool:
        """Log sleep hygiene metrics"""
        try:
            if user_id not in self.hygiene_metrics:
                self.hygiene_metrics[user_id] = []
            
            self.hygiene_metrics[user_id].append(metrics)
            
            logger.info(f"Logged sleep hygiene metrics for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging sleep hygiene: {e}")
            return False
    
    async def get_sleep_recommendations(self, user_id: str) -> List[SleepRecommendation]:
        """Get current sleep recommendations for a user"""
        return self.recommendations.get(user_id, [])
    
    async def complete_recommendation(self, user_id: str, recommendation_id: str) -> bool:
        """Mark a recommendation as completed"""
        try:
            user_recommendations = self.recommendations.get(user_id, [])
            
            for rec in user_recommendations:
                if rec.recommendation_id == recommendation_id:
                    rec.is_active = False
                    rec.completed_at = datetime.now()
                    logger.info(f"Completed recommendation {recommendation_id} for user {user_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error completing recommendation: {e}")
            return False
    
    async def get_optimal_bedtime(self, user_id: str, target_wake_time: time) -> Optional[time]:
        """Calculate optimal bedtime for a target wake time"""
        try:
            # Get user's sleep pattern
            pattern = self.sleep_patterns.get(user_id)
            
            if not pattern:
                # Use general recommendation (8 hours)
                target_datetime = datetime.combine(datetime.now().date(), target_wake_time)
                optimal_bedtime = target_datetime - timedelta(hours=8)
                return optimal_bedtime.time()
            
            # Use user's average sleep duration
            sleep_duration_hours = pattern.average_sleep_duration / 60
            target_datetime = datetime.combine(datetime.now().date(), target_wake_time)
            optimal_bedtime = target_datetime - timedelta(hours=sleep_duration_hours)
            
            return optimal_bedtime.time()
            
        except Exception as e:
            logger.error(f"Error calculating optimal bedtime: {e}")
            return None
    
    async def _sync_sleep_data(self):
        """Background task to sync sleep data from devices"""
        while self._running:
            try:
                # Get all users (in production, would query from database)
                all_users = set()
                all_users.update(self.sleep_sessions.keys())
                all_users.update(self.quality_scores.keys())
                
                for user_id in all_users:
                    try:
                        # Sync last 3 days of data
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=3)
                        
                        new_sessions = await self.data_source.get_sleep_data(user_id, start_date, end_date)
                        
                        # Process new sessions
                        for session in new_sessions:
                            # Check if we already have this session
                            existing_sessions = self.sleep_sessions.get(user_id, [])
                            session_exists = any(s.session_id == session.session_id for s in existing_sessions)
                            
                            if not session_exists:
                                await self.add_sleep_session(user_id, session)
                        
                    except Exception as e:
                        logger.error(f"Error syncing data for user {user_id}: {e}")
                
                # Sleep for 1 hour before next sync
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in sleep data sync: {e}")
                await asyncio.sleep(3600)
    
    async def _analyze_patterns(self):
        """Background task to analyze sleep patterns"""
        while self._running:
            try:
                # Analyze patterns for all users
                for user_id, sessions in self.sleep_sessions.items():
                    if len(sessions) >= 7:  # Need at least a week of data
                        try:
                            # Analyze recent 30 days
                            recent_sessions = sessions[-30:]
                            pattern = await self.quality_analyzer.identify_patterns(recent_sessions)
                            self.sleep_patterns[user_id] = pattern
                            
                            logger.info(f"Updated sleep pattern for user {user_id}")
                            
                        except Exception as e:
                            logger.error(f"Error analyzing pattern for user {user_id}: {e}")
                
                # Run pattern analysis every 6 hours
                await asyncio.sleep(21600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in pattern analysis: {e}")
                await asyncio.sleep(21600)
    
    async def _generate_recommendations_periodic(self):
        """Background task to generate and update recommendations"""
        while self._running:
            try:
                # Generate recommendations for all users with sufficient data
                for user_id in self.sleep_patterns.keys():
                    try:
                        pattern = self.sleep_patterns[user_id]
                        recent_scores = self.quality_scores.get(user_id, [])[-14:]  # Last 2 weeks
                        
                        if len(recent_scores) >= 7:  # Need at least a week of scores
                            recommendations = await self.recommendation_engine.generate_recommendations(
                                user_id, pattern, recent_scores
                            )
                            
                            self.recommendations[user_id] = recommendations
                            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
                        
                    except Exception as e:
                        logger.error(f"Error generating recommendations for user {user_id}: {e}")
                
                # Generate recommendations daily
                await asyncio.sleep(86400)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recommendation generation: {e}")
                await asyncio.sleep(86400)
    
    async def _process_smart_alarms(self):
        """Background task to process smart alarms"""
        while self._running:
            try:
                current_time = datetime.now()
                
                # Check all smart alarms
                for user_id, alarms in self.smart_alarms.items():
                    for alarm in alarms:
                        if not alarm.enabled:
                            continue
                        
                        # Check if today is an alarm day
                        if current_time.weekday() not in alarm.days_of_week:
                            continue
                        
                        # Check if it's time to trigger the alarm
                        target_time = datetime.combine(current_time.date(), alarm.target_wake_time)
                        wake_window_start = target_time - timedelta(minutes=alarm.wake_window)
                        
                        if wake_window_start <= current_time <= target_time:
                            # Check if user is in light sleep (if real-time data available)
                            real_time_data = await self.data_source.get_real_time_data(user_id)
                            
                            should_trigger = False
                            if real_time_data and real_time_data.get('is_sleeping'):
                                current_stage = real_time_data.get('current_stage')
                                if current_stage == SleepStage.LIGHT_SLEEP.value or current_stage == SleepStage.AWAKE.value:
                                    should_trigger = True
                            elif current_time >= target_time:
                                # If no real-time data or past target time, trigger anyway
                                should_trigger = True
                            
                            if should_trigger and alarm.last_triggered != current_time.date():
                                logger.info(f"Triggering smart alarm for user {user_id}")
                                alarm.last_triggered = current_time
                                # Here would be the actual alarm trigger logic
                
                # Check every minute
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing smart alarms: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_real_time_data(self):
        """Background task to monitor real-time sleep data"""
        while self._running:
            try:
                # Monitor real-time data for all users with smart alarms
                monitored_users = set(self.smart_alarms.keys())
                
                for user_id in monitored_users:
                    try:
                        real_time_data = await self.data_source.get_real_time_data(user_id)
                        
                        if real_time_data:
                            # Log interesting events (e.g., sleep stage changes, wake episodes)
                            current_hour = datetime.now().hour
                            
                            if real_time_data.get('is_sleeping') and 22 <= current_hour or current_hour <= 8:
                                # User is sleeping during expected hours - this is good
                                pass
                            elif not real_time_data.get('is_sleeping') and 2 <= current_hour <= 6:
                                # User is awake during core sleep hours - potential issue
                                logger.info(f"User {user_id} awake during core sleep hours")
                        
                    except Exception as e:
                        logger.error(f"Error monitoring real-time data for user {user_id}: {e}")
                
                # Check every 5 minutes
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in real-time monitoring: {e}")
                await asyncio.sleep(300)


# Singleton instance
_sleep_optimization_instance: Optional[SleepOptimization] = None


def get_sleep_optimization_service() -> SleepOptimization:
    """Get the singleton sleep optimization service instance"""
    global _sleep_optimization_instance
    
    if _sleep_optimization_instance is None:
        # Initialize with default implementations
        device_integrations = {
            'fitbit': {},
            'apple_watch': {},
            'oura': {},
            'garmin': {}
        }
        
        data_source = WearableDeviceSleepSource(device_integrations)
        quality_analyzer = ComprehensiveSleepQualityAnalyzer()
        recommendation_engine = IntelligentRecommendationEngine()
        
        _sleep_optimization_instance = SleepOptimization(
            data_source=data_source,
            quality_analyzer=quality_analyzer,
            recommendation_engine=recommendation_engine
        )
    
    return _sleep_optimization_instance


async def main():
    """Example usage of the sleep optimization service"""
    sleep_service = get_sleep_optimization_service()
    
    try:
        await sleep_service.start()
        
        user_id = "user123"
        
        # Example 1: Create a smart alarm
        smart_alarm = await sleep_service.create_smart_alarm(
            user_id=user_id,
            target_wake_time=time(7, 0),  # 7:00 AM
            wake_window=30,  # 30 minute window
            alarm_type=AlarmType.LIGHT_SLEEP_WINDOW,
            days_of_week={0, 1, 2, 3, 4}  # Weekdays
        )
        
        print(f"Created smart alarm: {smart_alarm.alarm_id}")
        
        # Example 2: Log sleep hygiene metrics
        hygiene_metrics = SleepHygieneMetrics(
            metrics_id=str(uuid4()),
            user_id=user_id,
            date=datetime.now(),
            bedtime_routine_score=75.0,
            screen_time_before_bed=45.0,  # 45 minutes
            caffeine_cutoff_time=time(14, 0),  # 2 PM
            exercise_timing=time(17, 30),  # 5:30 PM
            bedroom_temperature=20.0,  # 20°C
            bedroom_darkness=85.0,
            stress_level=3
        )
        
        success = await sleep_service.log_sleep_hygiene(user_id, hygiene_metrics)
        print(f"Logged sleep hygiene: {success}")
        
        # Example 3: Get optimal bedtime
        optimal_bedtime = await sleep_service.get_optimal_bedtime(user_id, time(7, 0))
        if optimal_bedtime:
            print(f"Optimal bedtime for 7 AM wake: {optimal_bedtime}")
        
        # Example 4: Add a sample sleep session
        sample_session = SleepSession(
            session_id=str(uuid4()),
            user_id=user_id,
            bedtime=datetime.now().replace(hour=22, minute=30, second=0, microsecond=0),
            sleep_time=datetime.now().replace(hour=22, minute=45, second=0, microsecond=0),
            wake_time=datetime.now().replace(hour=6, minute=30, second=0, microsecond=0),
            get_up_time=datetime.now().replace(hour=6, minute=45, second=0, microsecond=0),
            total_sleep_time=465,  # 7 hours 45 minutes
            sleep_efficiency=88.5,
            sleep_latency=15.0,
            wake_episodes=1,
            stages=[],  # Would be populated with real stage data
            average_heart_rate=58.0,
            movement_score=3.2,
            subjective_rating=8
        )
        
        success = await sleep_service.add_sleep_session(user_id, sample_session)
        print(f"Added sleep session: {success}")
        
        # Let background tasks run for a bit
        await asyncio.sleep(10)
        
        # Example 5: Get sleep analysis
        analysis = await sleep_service.get_sleep_analysis(user_id, days=7)
        if 'error' not in analysis:
            print(f"Sleep analysis - Average quality: {analysis['summary']['average_quality_score']:.1f}")
            print(f"Chronotype: {analysis['summary']['chronotype']}")
            print(f"Active recommendations: {len(analysis['recommendations'])}")
        
    finally:
        await sleep_service.stop()


if __name__ == "__main__":
    asyncio.run(main())