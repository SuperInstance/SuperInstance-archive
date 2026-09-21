"""
Emotional Journey Mapping System
Tracks and visualizes emotional patterns and journeys over time
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import sqlite3
import hashlib
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class JourneyPhase(Enum):
    DISCOVERY = "discovery"
    GROWTH = "growth"
    CHALLENGE = "challenge"
    TRANSFORMATION = "transformation"
    STABILITY = "stability"
    DECLINE = "decline"
    RECOVERY = "recovery"
    BREAKTHROUGH = "breakthrough"

class EmotionalEvent(Enum):
    MILESTONE = "milestone"
    SETBACK = "setback"
    TRANSITION = "transition"
    PEAK_EXPERIENCE = "peak_experience"
    VALLEY_EXPERIENCE = "valley_experience"
    PATTERN_SHIFT = "pattern_shift"
    RECURRING_THEME = "recurring_theme"

class TimeScale(Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

@dataclass
class JourneyConfig:
    """Configuration for emotional journey mapping"""
    default_time_window: timedelta = timedelta(days=90)
    min_data_points: int = 10
    smoothing_window: int = 7  # days
    peak_detection_threshold: float = 0.7
    valley_detection_threshold: float = 0.3
    phase_transition_sensitivity: float = 0.5
    enable_predictive_analysis: bool = True
    clustering_eps: float = 0.5
    clustering_min_samples: int = 3

@dataclass
class EmotionalDataPoint:
    """Single data point in emotional journey"""
    timestamp: datetime
    mood_score: float  # -1 to 1
    stress_level: float  # 0 to 1
    energy_level: float  # 0 to 1
    confidence_level: float  # 0 to 1
    social_connection: float  # 0 to 1
    life_satisfaction: float  # 0 to 1
    source: str = "mood_analysis"
    context: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class JourneySegment:
    """A segment of the emotional journey"""
    segment_id: str
    start_time: datetime
    end_time: datetime
    phase: JourneyPhase
    avg_mood: float
    avg_stress: float
    avg_energy: float
    dominant_emotions: List[str]
    key_events: List[str]
    duration_days: int
    stability_score: float  # How stable emotions were in this segment
    growth_indicators: List[str]
    challenges_faced: List[str]

@dataclass
class EmotionalMilestone:
    """Significant emotional milestone or event"""
    milestone_id: str
    timestamp: datetime
    event_type: EmotionalEvent
    title: str
    description: str
    emotional_impact: float  # -1 to 1
    duration_impact: timedelta
    contributing_factors: List[str]
    recovery_time: Optional[timedelta] = None
    lessons_learned: List[str] = field(default_factory=list)
    related_segments: List[str] = field(default_factory=list)

@dataclass
class JourneyInsight:
    """Insight derived from emotional journey analysis"""
    insight_type: str
    confidence: float
    title: str
    description: str
    supporting_data: Dict[str, Any]
    actionable_suggestions: List[str]
    relevance_score: float  # How relevant this insight is to the user

@dataclass
class EmotionalJourneyMap:
    """Complete emotional journey map"""
    user_id: str
    journey_id: str
    start_date: datetime
    end_date: datetime
    total_data_points: int
    segments: List[JourneySegment]
    milestones: List[EmotionalMilestone]
    insights: List[JourneyInsight]
    overall_trends: Dict[str, Any]
    predictive_indicators: Dict[str, Any]
    created_at: datetime
    last_updated: datetime

class EmotionalJourneyMapper:
    """Main engine for emotional journey mapping"""
    
    def __init__(self, config: JourneyConfig = None, db_path: str = None):
        self.config = config or JourneyConfig()
        self.db_path = db_path or "emotional_journey.db"
        
        # Initialize database
        self._init_database()
        
        # Journey analysis components
        self.journey_cache: Dict[str, EmotionalJourneyMap] = {}
        self.pattern_detector = EmotionalPatternDetector()
        self.milestone_detector = MilestoneDetector()
        
        logger.info("Emotional Journey Mapper initialized")

    def _init_database(self):
        """Initialize SQLite database for journey data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emotional_data_points (
                    point_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    timestamp TIMESTAMP,
                    mood_score REAL,
                    stress_level REAL,
                    energy_level REAL,
                    confidence_level REAL,
                    social_connection REAL,
                    life_satisfaction REAL,
                    source TEXT,
                    context TEXT,
                    raw_data TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS journey_segments (
                    segment_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    journey_id TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    phase TEXT,
                    avg_mood REAL,
                    avg_stress REAL,
                    avg_energy REAL,
                    dominant_emotions TEXT,
                    key_events TEXT,
                    duration_days INTEGER,
                    stability_score REAL,
                    growth_indicators TEXT,
                    challenges_faced TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emotional_milestones (
                    milestone_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    timestamp TIMESTAMP,
                    event_type TEXT,
                    title TEXT,
                    description TEXT,
                    emotional_impact REAL,
                    duration_impact INTEGER,
                    contributing_factors TEXT,
                    recovery_time INTEGER,
                    lessons_learned TEXT,
                    related_segments TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS journey_maps (
                    journey_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    total_data_points INTEGER,
                    overall_trends TEXT,
                    predictive_indicators TEXT,
                    created_at TIMESTAMP,
                    last_updated TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_emotional_data_user_timestamp 
                ON emotional_data_points (user_id, timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_journey_segments_user_journey 
                ON journey_segments (user_id, journey_id)
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    async def add_emotional_data_point(self, user_id: str, mood_score: float,
                                     stress_level: float = 0.0, energy_level: float = 0.5,
                                     confidence_level: float = 0.5, social_connection: float = 0.5,
                                     life_satisfaction: float = 0.5, source: str = "manual",
                                     context: Dict[str, Any] = None) -> str:
        """Add a new emotional data point"""
        try:
            point_id = hashlib.md5(
                f"{user_id}_{datetime.now().timestamp()}_{mood_score}".encode()
            ).hexdigest()
            
            data_point = EmotionalDataPoint(
                timestamp=datetime.now(),
                mood_score=max(-1, min(1, mood_score)),
                stress_level=max(0, min(1, stress_level)),
                energy_level=max(0, min(1, energy_level)),
                confidence_level=max(0, min(1, confidence_level)),
                social_connection=max(0, min(1, social_connection)),
                life_satisfaction=max(0, min(1, life_satisfaction)),
                source=source,
                context=context or {},
                raw_data={}
            )
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO emotional_data_points
                (point_id, user_id, timestamp, mood_score, stress_level, energy_level,
                 confidence_level, social_connection, life_satisfaction, source, context, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                point_id,
                user_id,
                data_point.timestamp.isoformat(),
                data_point.mood_score,
                data_point.stress_level,
                data_point.energy_level,
                data_point.confidence_level,
                data_point.social_connection,
                data_point.life_satisfaction,
                data_point.source,
                json.dumps(data_point.context),
                json.dumps(data_point.raw_data)
            ))
            
            conn.commit()
            conn.close()
            
            # Trigger journey update if enough new data
            await self._check_journey_update_trigger(user_id)
            
            logger.info(f"Added emotional data point: {point_id}")
            return point_id
            
        except Exception as e:
            logger.error(f"Error adding emotional data point: {e}")
            return ""

    async def generate_journey_map(self, user_id: str, 
                                 time_window: timedelta = None) -> EmotionalJourneyMap:
        """Generate complete emotional journey map for user"""
        try:
            time_window = time_window or self.config.default_time_window
            
            # Load emotional data points
            data_points = await self._load_emotional_data(user_id, time_window)
            
            if len(data_points) < self.config.min_data_points:
                logger.warning(f"Not enough data points for journey map: {len(data_points)}")
                return None
            
            # Generate journey ID
            journey_id = hashlib.md5(
                f"{user_id}_{time_window.days}_{datetime.now().date()}".encode()
            ).hexdigest()
            
            # Segment the journey into phases
            segments = await self._segment_emotional_journey(data_points, journey_id)
            
            # Detect emotional milestones
            milestones = await self._detect_emotional_milestones(data_points, segments)
            
            # Generate insights
            insights = await self._generate_journey_insights(data_points, segments, milestones)
            
            # Analyze overall trends
            overall_trends = await self._analyze_overall_trends(data_points)
            
            # Generate predictive indicators
            predictive_indicators = await self._generate_predictive_indicators(data_points, segments)
            
            # Create journey map
            journey_map = EmotionalJourneyMap(
                user_id=user_id,
                journey_id=journey_id,
                start_date=min(dp.timestamp for dp in data_points),
                end_date=max(dp.timestamp for dp in data_points),
                total_data_points=len(data_points),
                segments=segments,
                milestones=milestones,
                insights=insights,
                overall_trends=overall_trends,
                predictive_indicators=predictive_indicators,
                created_at=datetime.now(),
                last_updated=datetime.now()
            )
            
            # Save journey map
            await self._save_journey_map(journey_map)
            
            # Cache the journey map
            self.journey_cache[f"{user_id}_{journey_id}"] = journey_map
            
            return journey_map
            
        except Exception as e:
            logger.error(f"Error generating journey map: {e}")
            return None

    async def _load_emotional_data(self, user_id: str, 
                                 time_window: timedelta) -> List[EmotionalDataPoint]:
        """Load emotional data points from database"""
        try:
            cutoff_time = datetime.now() - time_window
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, mood_score, stress_level, energy_level, confidence_level,
                       social_connection, life_satisfaction, source, context, raw_data
                FROM emotional_data_points
                WHERE user_id = ? AND timestamp > ?
                ORDER BY timestamp
            ''', (user_id, cutoff_time.isoformat()))
            
            data_points = []
            for row in cursor.fetchall():
                timestamp_str, mood_score, stress_level, energy_level, confidence_level, \
                social_connection, life_satisfaction, source, context_str, raw_data_str = row
                
                context = json.loads(context_str) if context_str else {}
                raw_data = json.loads(raw_data_str) if raw_data_str else {}
                
                data_point = EmotionalDataPoint(
                    timestamp=datetime.fromisoformat(timestamp_str),
                    mood_score=mood_score,
                    stress_level=stress_level,
                    energy_level=energy_level,
                    confidence_level=confidence_level,
                    social_connection=social_connection,
                    life_satisfaction=life_satisfaction,
                    source=source,
                    context=context,
                    raw_data=raw_data
                )
                data_points.append(data_point)
            
            conn.close()
            return data_points
            
        except Exception as e:
            logger.error(f"Error loading emotional data: {e}")
            return []

    async def _segment_emotional_journey(self, data_points: List[EmotionalDataPoint], 
                                       journey_id: str) -> List[JourneySegment]:
        """Segment the emotional journey into meaningful phases"""
        try:
            if len(data_points) < 3:
                return []
            
            segments = []
            
            # Smooth the mood data for better segmentation
            mood_scores = [dp.mood_score for dp in data_points]
            stress_scores = [dp.stress_level for dp in data_points]
            energy_scores = [dp.energy_level for dp in data_points]
            
            smoothed_mood = self._smooth_data(mood_scores, window=self.config.smoothing_window)
            smoothed_stress = self._smooth_data(stress_scores, window=self.config.smoothing_window)
            smoothed_energy = self._smooth_data(energy_scores, window=self.config.smoothing_window)
            
            # Detect phase changes based on multiple dimensions
            change_points = self._detect_phase_changes(
                smoothed_mood, smoothed_stress, smoothed_energy
            )
            
            # Create segments between change points
            for i in range(len(change_points)):
                start_idx = change_points[i]
                end_idx = change_points[i + 1] if i + 1 < len(change_points) else len(data_points) - 1
                
                segment_data = data_points[start_idx:end_idx + 1]
                if len(segment_data) < 2:
                    continue
                
                # Analyze segment characteristics
                avg_mood = np.mean([dp.mood_score for dp in segment_data])
                avg_stress = np.mean([dp.stress_level for dp in segment_data])
                avg_energy = np.mean([dp.energy_level for dp in segment_data])
                
                # Determine phase based on characteristics
                phase = self._classify_journey_phase(avg_mood, avg_stress, avg_energy, segment_data)
                
                # Calculate stability
                stability = self._calculate_segment_stability(segment_data)
                
                # Identify dominant emotions and events
                dominant_emotions = self._identify_dominant_emotions(segment_data)
                key_events = self._identify_key_events(segment_data)
                
                # Generate insights
                growth_indicators = self._identify_growth_indicators(segment_data)
                challenges_faced = self._identify_challenges(segment_data)
                
                segment_id = hashlib.md5(
                    f"{journey_id}_{start_idx}_{end_idx}".encode()
                ).hexdigest()
                
                segment = JourneySegment(
                    segment_id=segment_id,
                    start_time=segment_data[0].timestamp,
                    end_time=segment_data[-1].timestamp,
                    phase=phase,
                    avg_mood=avg_mood,
                    avg_stress=avg_stress,
                    avg_energy=avg_energy,
                    dominant_emotions=dominant_emotions,
                    key_events=key_events,
                    duration_days=(segment_data[-1].timestamp - segment_data[0].timestamp).days,
                    stability_score=stability,
                    growth_indicators=growth_indicators,
                    challenges_faced=challenges_faced
                )
                
                segments.append(segment)
            
            return segments
            
        except Exception as e:
            logger.error(f"Error segmenting emotional journey: {e}")
            return []

    def _smooth_data(self, data: List[float], window: int) -> List[float]:
        """Smooth data using moving average"""
        if len(data) <= window:
            return data
        
        smoothed = []
        for i in range(len(data)):
            start = max(0, i - window // 2)
            end = min(len(data), i + window // 2 + 1)
            smoothed.append(np.mean(data[start:end]))
        
        return smoothed

    def _detect_phase_changes(self, mood_scores: List[float], 
                            stress_scores: List[float], 
                            energy_scores: List[float]) -> List[int]:
        """Detect significant changes in emotional phases"""
        change_points = [0]  # Always start with first point
        
        # Look for significant changes in trend
        for i in range(1, len(mood_scores) - 1):
            # Check for trend reversals or significant changes
            mood_change = abs(mood_scores[i] - mood_scores[i-1])
            stress_change = abs(stress_scores[i] - stress_scores[i-1])
            energy_change = abs(energy_scores[i] - energy_scores[i-1])
            
            # Combined change score
            total_change = mood_change + stress_change + energy_change
            
            if total_change > self.config.phase_transition_sensitivity:
                # Avoid too frequent changes
                if not change_points or i - change_points[-1] > 3:
                    change_points.append(i)
        
        return change_points

    def _classify_journey_phase(self, avg_mood: float, avg_stress: float, 
                              avg_energy: float, segment_data: List[EmotionalDataPoint]) -> JourneyPhase:
        """Classify the phase of a journey segment"""
        
        # Analyze trends within the segment
        mood_trend = self._calculate_trend([dp.mood_score for dp in segment_data])
        stress_trend = self._calculate_trend([dp.stress_level for dp in segment_data])
        energy_trend = self._calculate_trend([dp.energy_level for dp in segment_data])
        
        # Phase classification logic
        if avg_mood > 0.5 and mood_trend > 0.1:
            return JourneyPhase.GROWTH
        elif avg_mood > 0.3 and avg_stress < 0.3 and avg_energy > 0.6:
            return JourneyPhase.STABILITY
        elif avg_mood < -0.3 or (avg_stress > 0.7 and avg_energy < 0.3):
            return JourneyPhase.CHALLENGE
        elif mood_trend > 0.2 and avg_mood > 0:
            return JourneyPhase.RECOVERY
        elif avg_mood > 0.7 and avg_energy > 0.8:
            return JourneyPhase.BREAKTHROUGH
        elif mood_trend < -0.2 and avg_mood < 0:
            return JourneyPhase.DECLINE
        elif avg_mood < 0.1 and avg_mood > -0.1:
            return JourneyPhase.DISCOVERY
        else:
            return JourneyPhase.TRANSITION

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend (slope) of values"""
        if len(values) < 2:
            return 0.0
        
        x = np.arange(len(values))
        slope, _, _, _, _ = stats.linregress(x, values)
        return slope

    def _calculate_segment_stability(self, segment_data: List[EmotionalDataPoint]) -> float:
        """Calculate stability score for a segment"""
        if len(segment_data) < 2:
            return 1.0
        
        # Calculate variance across different dimensions
        mood_var = np.var([dp.mood_score for dp in segment_data])
        stress_var = np.var([dp.stress_level for dp in segment_data])
        energy_var = np.var([dp.energy_level for dp in segment_data])
        
        # Lower variance = higher stability
        avg_variance = (mood_var + stress_var + energy_var) / 3
        stability = max(0, 1 - avg_variance)
        
        return stability

    def _identify_dominant_emotions(self, segment_data: List[EmotionalDataPoint]) -> List[str]:
        """Identify dominant emotions in a segment"""
        emotions = []
        
        avg_mood = np.mean([dp.mood_score for dp in segment_data])
        avg_stress = np.mean([dp.stress_level for dp in segment_data])
        avg_energy = np.mean([dp.energy_level for dp in segment_data])
        avg_confidence = np.mean([dp.confidence_level for dp in segment_data])
        
        # Map emotional dimensions to emotion labels
        if avg_mood > 0.5:
            emotions.append("joy" if avg_energy > 0.5 else "contentment")
        elif avg_mood < -0.5:
            emotions.append("sadness" if avg_energy < 0.5 else "anger")
        
        if avg_stress > 0.6:
            emotions.append("anxiety" if avg_energy > 0.5 else "overwhelm")
        
        if avg_confidence > 0.7:
            emotions.append("confidence")
        elif avg_confidence < 0.3:
            emotions.append("insecurity")
        
        if avg_energy > 0.8:
            emotions.append("excitement")
        elif avg_energy < 0.2:
            emotions.append("fatigue")
        
        return emotions or ["neutral"]

    def _identify_key_events(self, segment_data: List[EmotionalDataPoint]) -> List[str]:
        """Identify key events in a segment"""
        events = []
        
        # Look for significant changes or extreme values
        mood_scores = [dp.mood_score for dp in segment_data]
        stress_scores = [dp.stress_level for dp in segment_data]
        
        # Find peaks and valleys
        if max(mood_scores) > 0.8:
            events.append("mood_peak")
        if min(mood_scores) < -0.8:
            events.append("mood_valley")
        if max(stress_scores) > 0.9:
            events.append("high_stress_event")
        
        # Look for rapid changes
        for i in range(1, len(mood_scores)):
            change = abs(mood_scores[i] - mood_scores[i-1])
            if change > 0.5:
                events.append("rapid_mood_change")
                break
        
        return events

    def _identify_growth_indicators(self, segment_data: List[EmotionalDataPoint]) -> List[str]:
        """Identify indicators of emotional growth"""
        indicators = []
        
        # Trend analysis
        mood_trend = self._calculate_trend([dp.mood_score for dp in segment_data])
        confidence_trend = self._calculate_trend([dp.confidence_level for dp in segment_data])
        
        if mood_trend > 0.1:
            indicators.append("improving_mood")
        if confidence_trend > 0.1:
            indicators.append("growing_confidence")
        
        # Stability analysis
        stability = self._calculate_segment_stability(segment_data)
        if stability > 0.8:
            indicators.append("emotional_stability")
        
        return indicators

    def _identify_challenges(self, segment_data: List[EmotionalDataPoint]) -> List[str]:
        """Identify challenges faced in a segment"""
        challenges = []
        
        avg_stress = np.mean([dp.stress_level for dp in segment_data])
        avg_mood = np.mean([dp.mood_score for dp in segment_data])
        avg_energy = np.mean([dp.energy_level for dp in segment_data])
        
        if avg_stress > 0.6:
            challenges.append("high_stress_period")
        if avg_mood < -0.3:
            challenges.append("low_mood_period")
        if avg_energy < 0.3:
            challenges.append("low_energy_period")
        
        # Check for volatility
        mood_volatility = np.std([dp.mood_score for dp in segment_data])
        if mood_volatility > 0.5:
            challenges.append("emotional_volatility")
        
        return challenges

    async def _detect_emotional_milestones(self, data_points: List[EmotionalDataPoint],
                                         segments: List[JourneySegment]) -> List[EmotionalMilestone]:
        """Detect significant emotional milestones"""
        milestones = []
        
        try:
            # Peak experiences
            mood_scores = [dp.mood_score for dp in data_points]
            for i, score in enumerate(mood_scores):
                if score > self.config.peak_detection_threshold:
                    # Check if this is a local maximum
                    is_peak = True
                    for j in range(max(0, i-2), min(len(mood_scores), i+3)):
                        if j != i and mood_scores[j] >= score:
                            is_peak = False
                            break
                    
                    if is_peak:
                        milestone_id = hashlib.md5(
                            f"peak_{i}_{data_points[i].timestamp}".encode()
                        ).hexdigest()
                        
                        milestone = EmotionalMilestone(
                            milestone_id=milestone_id,
                            timestamp=data_points[i].timestamp,
                            event_type=EmotionalEvent.PEAK_EXPERIENCE,
                            title="Emotional Peak",
                            description=f"Experienced high positive emotion (score: {score:.2f})",
                            emotional_impact=score,
                            duration_impact=timedelta(days=1),
                            contributing_factors=self._analyze_contributing_factors(data_points[i])
                        )
                        milestones.append(milestone)
            
            # Valley experiences
            for i, score in enumerate(mood_scores):
                if score < self.config.valley_detection_threshold:
                    # Check if this is a local minimum
                    is_valley = True
                    for j in range(max(0, i-2), min(len(mood_scores), i+3)):
                        if j != i and mood_scores[j] <= score:
                            is_valley = False
                            break
                    
                    if is_valley:
                        milestone_id = hashlib.md5(
                            f"valley_{i}_{data_points[i].timestamp}".encode()
                        ).hexdigest()
                        
                        milestone = EmotionalMilestone(
                            milestone_id=milestone_id,
                            timestamp=data_points[i].timestamp,
                            event_type=EmotionalEvent.VALLEY_EXPERIENCE,
                            title="Emotional Valley",
                            description=f"Experienced challenging emotions (score: {score:.2f})",
                            emotional_impact=score,
                            duration_impact=timedelta(days=1),
                            contributing_factors=self._analyze_contributing_factors(data_points[i])
                        )
                        milestones.append(milestone)
            
            # Phase transitions as milestones
            for i in range(1, len(segments)):
                prev_segment = segments[i-1]
                curr_segment = segments[i]
                
                if prev_segment.phase != curr_segment.phase:
                    milestone_id = hashlib.md5(
                        f"transition_{prev_segment.phase.value}_{curr_segment.phase.value}".encode()
                    ).hexdigest()
                    
                    milestone = EmotionalMilestone(
                        milestone_id=milestone_id,
                        timestamp=curr_segment.start_time,
                        event_type=EmotionalEvent.TRANSITION,
                        title=f"Phase Transition: {prev_segment.phase.value} → {curr_segment.phase.value}",
                        description=f"Transitioned from {prev_segment.phase.value} to {curr_segment.phase.value}",
                        emotional_impact=curr_segment.avg_mood - prev_segment.avg_mood,
                        duration_impact=curr_segment.end_time - curr_segment.start_time,
                        contributing_factors=[],
                        related_segments=[prev_segment.segment_id, curr_segment.segment_id]
                    )
                    milestones.append(milestone)
            
        except Exception as e:
            logger.error(f"Error detecting emotional milestones: {e}")
        
        return milestones

    def _analyze_contributing_factors(self, data_point: EmotionalDataPoint) -> List[str]:
        """Analyze factors that contributed to an emotional state"""
        factors = []
        
        if data_point.stress_level > 0.7:
            factors.append("high_stress")
        if data_point.energy_level > 0.8:
            factors.append("high_energy")
        if data_point.social_connection > 0.8:
            factors.append("strong_social_connection")
        if data_point.confidence_level > 0.8:
            factors.append("high_confidence")
        
        # Analyze context
        context = data_point.context
        if 'activity' in context:
            factors.append(f"activity:{context['activity']}")
        if 'location' in context:
            factors.append(f"location:{context['location']}")
        if 'social' in context:
            factors.append(f"social:{context['social']}")
        
        return factors

    async def _generate_journey_insights(self, data_points: List[EmotionalDataPoint],
                                       segments: List[JourneySegment],
                                       milestones: List[EmotionalMilestone]) -> List[JourneyInsight]:
        """Generate insights from journey analysis"""
        insights = []
        
        try:
            # Overall mood trend insight
            mood_trend = self._calculate_trend([dp.mood_score for dp in data_points])
            if abs(mood_trend) > 0.05:
                direction = "improving" if mood_trend > 0 else "declining"
                insight = JourneyInsight(
                    insight_type="mood_trend",
                    confidence=min(abs(mood_trend) * 10, 1.0),
                    title=f"Overall Mood {direction.title()}",
                    description=f"Your emotional state has been {direction} over time (trend: {mood_trend:.3f})",
                    supporting_data={"trend_value": mood_trend},
                    actionable_suggestions=self._get_trend_suggestions(mood_trend),
                    relevance_score=0.8
                )
                insights.append(insight)
            
            # Stress pattern insight
            stress_levels = [dp.stress_level for dp in data_points]
            avg_stress = np.mean(stress_levels)
            if avg_stress > 0.6:
                insight = JourneyInsight(
                    insight_type="stress_pattern",
                    confidence=0.9,
                    title="Elevated Stress Levels",
                    description=f"You've been experiencing consistently high stress (avg: {avg_stress:.2f})",
                    supporting_data={"average_stress": avg_stress},
                    actionable_suggestions=["Consider stress management techniques", "Evaluate workload", "Practice relaxation"],
                    relevance_score=1.0
                )
                insights.append(insight)
            
            # Growth pattern insight
            growth_segments = [s for s in segments if s.phase == JourneyPhase.GROWTH]
            if len(growth_segments) > len(segments) * 0.3:
                insight = JourneyInsight(
                    insight_type="growth_pattern",
                    confidence=0.8,
                    title="Strong Growth Pattern",
                    description=f"You've shown significant emotional growth in {len(growth_segments)} periods",
                    supporting_data={"growth_segments": len(growth_segments)},
                    actionable_suggestions=["Continue current positive practices", "Identify growth catalysts"],
                    relevance_score=0.9
                )
                insights.append(insight)
            
            # Volatility insight
            mood_volatility = np.std([dp.mood_score for dp in data_points])
            if mood_volatility > 0.5:
                insight = JourneyInsight(
                    insight_type="emotional_volatility",
                    confidence=0.7,
                    title="High Emotional Variability",
                    description=f"Your emotions have been quite variable (volatility: {mood_volatility:.2f})",
                    supporting_data={"volatility": mood_volatility},
                    actionable_suggestions=["Work on emotional regulation", "Identify triggers", "Consider mindfulness practices"],
                    relevance_score=0.7
                )
                insights.append(insight)
            
            # Milestone frequency insight
            peak_milestones = [m for m in milestones if m.event_type == EmotionalEvent.PEAK_EXPERIENCE]
            if len(peak_milestones) > 0:
                days_span = (data_points[-1].timestamp - data_points[0].timestamp).days
                frequency = len(peak_milestones) / max(days_span / 30, 1)  # per month
                
                insight = JourneyInsight(
                    insight_type="peak_frequency",
                    confidence=0.6,
                    title="Positive Experience Frequency",
                    description=f"You experience emotional peaks about {frequency:.1f} times per month",
                    supporting_data={"peak_frequency": frequency},
                    actionable_suggestions=["Identify what creates peak experiences", "Try to recreate positive conditions"],
                    relevance_score=0.6
                )
                insights.append(insight)
                
        except Exception as e:
            logger.error(f"Error generating journey insights: {e}")
        
        return insights

    def _get_trend_suggestions(self, trend: float) -> List[str]:
        """Get suggestions based on mood trend"""
        if trend > 0:
            return [
                "Keep doing what's working well",
                "Identify the factors contributing to improvement",
                "Consider sharing your success strategies"
            ]
        else:
            return [
                "Consider seeking support if needed",
                "Reflect on recent changes in your life",
                "Focus on self-care activities",
                "Consider professional guidance if trends continue"
            ]

    async def _analyze_overall_trends(self, data_points: List[EmotionalDataPoint]) -> Dict[str, Any]:
        """Analyze overall trends in the emotional journey"""
        try:
            trends = {}
            
            # Calculate trends for each dimension
            dimensions = ['mood_score', 'stress_level', 'energy_level', 'confidence_level', 
                         'social_connection', 'life_satisfaction']
            
            for dim in dimensions:
                values = [getattr(dp, dim) for dp in data_points]
                trend = self._calculate_trend(values)
                trends[f"{dim}_trend"] = trend
                trends[f"{dim}_average"] = np.mean(values)
                trends[f"{dim}_volatility"] = np.std(values)
            
            # Overall emotional health score
            avg_mood = trends['mood_score_average']
            avg_stress = 1 - trends['stress_level_average']  # Invert stress
            avg_energy = trends['energy_level_average']
            avg_confidence = trends['confidence_level_average']
            avg_social = trends['social_connection_average']
            avg_satisfaction = trends['life_satisfaction_average']
            
            emotional_health_score = (avg_mood + avg_stress + avg_energy + 
                                    avg_confidence + avg_social + avg_satisfaction) / 6
            trends['emotional_health_score'] = emotional_health_score
            
            # Trend direction
            overall_trend = (trends['mood_score_trend'] + 
                           -trends['stress_level_trend'] + 
                           trends['energy_level_trend']) / 3
            trends['overall_trend_direction'] = overall_trend
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing overall trends: {e}")
            return {}

    async def _generate_predictive_indicators(self, data_points: List[EmotionalDataPoint],
                                            segments: List[JourneySegment]) -> Dict[str, Any]:
        """Generate predictive indicators for future emotional states"""
        try:
            indicators = {}
            
            if not self.config.enable_predictive_analysis or len(data_points) < 10:
                return indicators
            
            # Predict mood trajectory
            recent_moods = [dp.mood_score for dp in data_points[-10:]]
            mood_trend = self._calculate_trend(recent_moods)
            indicators['predicted_mood_direction'] = 'improving' if mood_trend > 0 else 'declining'
            indicators['mood_trend_confidence'] = min(abs(mood_trend) * 5, 1.0)
            
            # Stress buildup indicator
            recent_stress = [dp.stress_level for dp in data_points[-7:]]
            stress_trend = self._calculate_trend(recent_stress)
            if stress_trend > 0.1:
                indicators['stress_buildup_risk'] = 'high'
            elif stress_trend > 0.05:
                indicators['stress_buildup_risk'] = 'moderate'
            else:
                indicators['stress_buildup_risk'] = 'low'
            
            # Stability prediction
            recent_volatility = np.std([dp.mood_score for dp in data_points[-14:]])
            if recent_volatility < 0.3:
                indicators['emotional_stability_forecast'] = 'stable'
            elif recent_volatility < 0.6:
                indicators['emotional_stability_forecast'] = 'moderate'
            else:
                indicators['emotional_stability_forecast'] = 'volatile'
            
            # Recovery pattern recognition
            valley_milestones = len([dp for dp in data_points[-30:] if dp.mood_score < -0.5])
            recovery_times = []  # Would calculate actual recovery times
            if valley_milestones > 0:
                # Estimate typical recovery time based on historical patterns
                indicators['typical_recovery_time_days'] = 3  # Simplified
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error generating predictive indicators: {e}")
            return {}

    async def _save_journey_map(self, journey_map: EmotionalJourneyMap):
        """Save journey map to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Save journey map
            cursor.execute('''
                INSERT OR REPLACE INTO journey_maps
                (journey_id, user_id, start_date, end_date, total_data_points,
                 overall_trends, predictive_indicators, created_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                journey_map.journey_id,
                journey_map.user_id,
                journey_map.start_date.isoformat(),
                journey_map.end_date.isoformat(),
                journey_map.total_data_points,
                json.dumps(journey_map.overall_trends),
                json.dumps(journey_map.predictive_indicators),
                journey_map.created_at.isoformat(),
                journey_map.last_updated.isoformat()
            ))
            
            # Save segments
            for segment in journey_map.segments:
                cursor.execute('''
                    INSERT OR REPLACE INTO journey_segments
                    (segment_id, user_id, journey_id, start_time, end_time, phase,
                     avg_mood, avg_stress, avg_energy, dominant_emotions, key_events,
                     duration_days, stability_score, growth_indicators, challenges_faced)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    segment.segment_id,
                    journey_map.user_id,
                    journey_map.journey_id,
                    segment.start_time.isoformat(),
                    segment.end_time.isoformat(),
                    segment.phase.value,
                    segment.avg_mood,
                    segment.avg_stress,
                    segment.avg_energy,
                    json.dumps(segment.dominant_emotions),
                    json.dumps(segment.key_events),
                    segment.duration_days,
                    segment.stability_score,
                    json.dumps(segment.growth_indicators),
                    json.dumps(segment.challenges_faced)
                ))
            
            # Save milestones
            for milestone in journey_map.milestones:
                cursor.execute('''
                    INSERT OR REPLACE INTO emotional_milestones
                    (milestone_id, user_id, timestamp, event_type, title, description,
                     emotional_impact, duration_impact, contributing_factors, recovery_time,
                     lessons_learned, related_segments)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    milestone.milestone_id,
                    journey_map.user_id,
                    milestone.timestamp.isoformat(),
                    milestone.event_type.value,
                    milestone.title,
                    milestone.description,
                    milestone.emotional_impact,
                    milestone.duration_impact.total_seconds(),
                    json.dumps(milestone.contributing_factors),
                    milestone.recovery_time.total_seconds() if milestone.recovery_time else None,
                    json.dumps(milestone.lessons_learned),
                    json.dumps(milestone.related_segments)
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving journey map: {e}")

    async def _check_journey_update_trigger(self, user_id: str):
        """Check if journey map should be updated based on new data"""
        try:
            # Simple trigger: update if there have been 5 new data points since last map
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get last journey update time
            cursor.execute('''
                SELECT MAX(last_updated) FROM journey_maps WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            last_update = result[0] if result and result[0] else None
            
            if last_update:
                last_update_dt = datetime.fromisoformat(last_update)
                
                # Count new data points since last update
                cursor.execute('''
                    SELECT COUNT(*) FROM emotional_data_points 
                    WHERE user_id = ? AND timestamp > ?
                ''', (user_id, last_update))
                
                new_points = cursor.fetchone()[0]
                
                if new_points >= 5:
                    # Trigger journey map update
                    await self.generate_journey_map(user_id)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error checking journey update trigger: {e}")

    async def get_journey_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get journey mapping statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Basic statistics
            cursor.execute('''
                SELECT COUNT(*) FROM emotional_data_points WHERE user_id = ?
            ''', (user_id,))
            total_data_points = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM journey_maps WHERE user_id = ?
            ''', (user_id,))
            total_journeys = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM emotional_milestones WHERE user_id = ?
            ''', (user_id,))
            total_milestones = cursor.fetchone()[0]
            
            # Average emotional health
            cursor.execute('''
                SELECT AVG(mood_score), AVG(stress_level), AVG(energy_level)
                FROM emotional_data_points WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            avg_mood, avg_stress, avg_energy = result if result else (0, 0, 0)
            
            conn.close()
            
            return {
                'total_data_points': total_data_points,
                'total_journey_maps': total_journeys,
                'total_milestones': total_milestones,
                'average_mood': avg_mood or 0,
                'average_stress': avg_stress or 0,
                'average_energy': avg_energy or 0,
                'emotional_health_score': ((avg_mood or 0) + (1 - (avg_stress or 0)) + (avg_energy or 0)) / 3
            }
            
        except Exception as e:
            logger.error(f"Error getting journey statistics: {e}")
            return {}

class EmotionalPatternDetector:
    """Helper class for detecting emotional patterns"""
    
    def detect_cycles(self, data_points: List[EmotionalDataPoint]) -> List[Dict[str, Any]]:
        """Detect cyclical patterns in emotional data"""
        # Simplified cycle detection - would use more sophisticated algorithms in practice
        return []

class MilestoneDetector:
    """Helper class for detecting emotional milestones"""
    
    def detect_breakthroughs(self, data_points: List[EmotionalDataPoint]) -> List[EmotionalMilestone]:
        """Detect breakthrough moments"""
        # Would implement sophisticated breakthrough detection
        return []

# CLI interface for testing
async def main():
    """CLI interface for testing emotional journey mapping"""
    print("Emotional Journey Mapper - Test Interface")
    print("=" * 50)
    
    # Initialize mapper
    config = JourneyConfig(
        default_time_window=timedelta(days=30),
        min_data_points=5
    )
    
    mapper = EmotionalJourneyMapper(config)
    
    print("Available commands:")
    print("1. add-data <user_id> <mood> [stress] [energy] - Add emotional data point")
    print("2. journey <user_id> - Generate journey map")
    print("3. stats <user_id> - Show journey statistics")
    print("4. config - Show current configuration")
    print("5. exit - Exit the program")
    
    while True:
        try:
            command = input("\nEnter command: ").strip()
            
            if command == "exit":
                break
            elif command.startswith("add-data "):
                parts = command.split()
                if len(parts) >= 3:
                    user_id = parts[1]
                    mood = float(parts[2])
                    stress = float(parts[3]) if len(parts) > 3 else 0.3
                    energy = float(parts[4]) if len(parts) > 4 else 0.5
                    
                    point_id = await mapper.add_emotional_data_point(
                        user_id=user_id,
                        mood_score=mood,
                        stress_level=stress,
                        energy_level=energy,
                        context={'source': 'cli_test'}
                    )
                    print(f"Added data point: {point_id}")
                else:
                    print("Usage: add-data <user_id> <mood> [stress] [energy]")
                    
            elif command.startswith("journey "):
                user_id = command.split()[1]
                print(f"Generating journey map for {user_id}...")
                
                journey_map = await mapper.generate_journey_map(user_id)
                if journey_map:
                    print(f"\nJourney Map Generated:")
                    print(f"Journey ID: {journey_map.journey_id}")
                    print(f"Time Period: {journey_map.start_date.date()} to {journey_map.end_date.date()}")
                    print(f"Total Data Points: {journey_map.total_data_points}")
                    print(f"Segments: {len(journey_map.segments)}")
                    print(f"Milestones: {len(journey_map.milestones)}")
                    print(f"Insights: {len(journey_map.insights)}")
                    
                    print(f"\nSegments:")
                    for segment in journey_map.segments[:3]:  # Show first 3
                        print(f"  - {segment.phase.value}: {segment.duration_days} days, "
                              f"mood: {segment.avg_mood:.2f}, stability: {segment.stability_score:.2f}")
                    
                    print(f"\nKey Insights:")
                    for insight in journey_map.insights[:3]:  # Show first 3
                        print(f"  - {insight.title}: {insight.description}")
                else:
                    print("Failed to generate journey map (not enough data?)")
                    
            elif command.startswith("stats "):
                user_id = command.split()[1]
                stats = await mapper.get_journey_statistics(user_id)
                print(f"\nJourney Statistics for {user_id}:")
                print(json.dumps(stats, indent=2))
                
            elif command == "config":
                print("Current configuration:")
                print(f"Default time window: {config.default_time_window.days} days")
                print(f"Min data points: {config.min_data_points}")
                print(f"Smoothing window: {config.smoothing_window} days")
                print(f"Peak threshold: {config.peak_detection_threshold}")
                print(f"Enable predictive analysis: {config.enable_predictive_analysis}")
                
            else:
                print("Unknown command. Try 'add-data', 'journey', 'stats', 'config', or 'exit'.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("Emotional journey mapper test completed.")

if __name__ == "__main__":
    asyncio.run(main())