"""
Stress Detection from Data Patterns
Analyzes behavioral and data patterns to detect stress levels and triggers
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
import re
from collections import defaultdict, deque
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)

class StressLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"

class StressType(Enum):
    ACUTE = "acute"              # Short-term, intense stress
    CHRONIC = "chronic"          # Long-term, persistent stress
    EPISODIC = "episodic"        # Recurring stress episodes
    ANTICIPATORY = "anticipatory" # Stress about future events
    SITUATIONAL = "situational"  # Context-specific stress

class StressTrigger(Enum):
    WORKLOAD = "workload"
    SOCIAL = "social"
    FINANCIAL = "financial"
    HEALTH = "health"
    FAMILY = "family"
    TECHNOLOGY = "technology"
    TIME_PRESSURE = "time_pressure"
    UNCERTAINTY = "uncertainty"
    PERFECTIONISM = "perfectionism"
    ISOLATION = "isolation"

@dataclass
class StressDetectionConfig:
    """Configuration for stress detection"""
    detection_window: timedelta = timedelta(hours=24)
    analysis_frequency: timedelta = timedelta(hours=6)
    stress_threshold: float = 0.6
    chronic_threshold_days: int = 14
    acute_spike_threshold: float = 0.8
    pattern_memory_days: int = 90
    enable_predictive_analysis: bool = True
    physiological_weight: float = 0.3
    behavioral_weight: float = 0.4
    contextual_weight: float = 0.3
    min_data_points: int = 5

@dataclass
class StressIndicator:
    """Individual stress indicator"""
    indicator_type: str
    value: float
    timestamp: datetime
    confidence: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StressPattern:
    """Identified stress pattern"""
    pattern_id: str
    pattern_type: str
    triggers: List[StressTrigger]
    frequency: float  # occurrences per time period
    intensity: float  # average stress level during pattern
    duration: timedelta  # typical duration of stress episodes
    time_of_day_pattern: List[int]  # hours when pattern occurs
    day_of_week_pattern: List[int]  # days when pattern occurs
    seasonal_pattern: Optional[str] = None
    environmental_factors: List[str] = field(default_factory=list)

@dataclass
class StressEvent:
    """Specific stress event"""
    event_id: str
    timestamp: datetime
    stress_level: StressLevel
    stress_type: StressType
    duration: timedelta
    triggers: List[StressTrigger]
    contributing_indicators: List[StressIndicator]
    recovery_time: Optional[timedelta] = None
    impact_areas: List[str] = field(default_factory=list)
    coping_strategies_used: List[str] = field(default_factory=list)
    effectiveness_score: Optional[float] = None

@dataclass
class StressAnalysis:
    """Complete stress analysis result"""
    analysis_id: str
    user_id: str
    analysis_timestamp: datetime
    current_stress_level: StressLevel
    stress_trend: float  # -1 to 1, negative is decreasing
    dominant_stress_type: StressType
    primary_triggers: List[StressTrigger]
    stress_patterns: List[StressPattern]
    recent_events: List[StressEvent]
    risk_factors: List[str]
    protective_factors: List[str]
    recommendations: List[str]
    urgency_level: str  # low, medium, high, critical

class StressDetector:
    """Main engine for stress detection from data patterns"""
    
    def __init__(self, config: StressDetectionConfig = None, db_path: str = None):
        self.config = config or StressDetectionConfig()
        self.db_path = db_path or "stress_detection.db"
        
        # Initialize database
        self._init_database()
        
        # Pattern analysis components
        self.stress_indicators_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.pattern_cache: Dict[str, List[StressPattern]] = {}
        self.ml_models: Dict[str, Any] = {}
        
        # Stress detection rules and patterns
        self.stress_indicators_config = self._initialize_stress_indicators()
        self.trigger_patterns = self._initialize_trigger_patterns()
        
        # Initialize ML models for anomaly detection
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        
        logger.info("Stress Detection Engine initialized")

    def _init_database(self):
        """Initialize SQLite database for stress data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stress_indicators (
                    indicator_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    indicator_type TEXT,
                    value REAL,
                    timestamp TIMESTAMP,
                    confidence REAL,
                    source TEXT,
                    metadata TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stress_events (
                    event_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    timestamp TIMESTAMP,
                    stress_level TEXT,
                    stress_type TEXT,
                    duration INTEGER,
                    triggers TEXT,
                    contributing_indicators TEXT,
                    recovery_time INTEGER,
                    impact_areas TEXT,
                    coping_strategies_used TEXT,
                    effectiveness_score REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stress_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    pattern_type TEXT,
                    triggers TEXT,
                    frequency REAL,
                    intensity REAL,
                    duration INTEGER,
                    time_of_day_pattern TEXT,
                    day_of_week_pattern TEXT,
                    seasonal_pattern TEXT,
                    environmental_factors TEXT,
                    created_at TIMESTAMP,
                    last_updated TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stress_analyses (
                    analysis_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    analysis_timestamp TIMESTAMP,
                    current_stress_level TEXT,
                    stress_trend REAL,
                    dominant_stress_type TEXT,
                    primary_triggers TEXT,
                    risk_factors TEXT,
                    protective_factors TEXT,
                    recommendations TEXT,
                    urgency_level TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_stress_indicators_user_timestamp 
                ON stress_indicators (user_id, timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_stress_events_user_timestamp 
                ON stress_events (user_id, timestamp)
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def _initialize_stress_indicators(self) -> Dict[str, Dict[str, Any]]:
        """Initialize stress indicator configurations"""
        return {
            'behavioral': {
                'typing_speed_variance': {
                    'weight': 0.4,
                    'threshold_high': 0.3,  # High variance indicates stress
                    'threshold_critical': 0.5
                },
                'app_switching_frequency': {
                    'weight': 0.3,
                    'threshold_high': 20,  # switches per hour
                    'threshold_critical': 40
                },
                'file_access_erratic': {
                    'weight': 0.3,
                    'threshold_high': 0.4,  # erratic pattern score
                    'threshold_critical': 0.7
                },
                'work_hour_extension': {
                    'weight': 0.5,
                    'threshold_high': 2,    # hours beyond normal
                    'threshold_critical': 4
                },
                'break_frequency_decrease': {
                    'weight': 0.3,
                    'threshold_high': 0.3,  # 30% decrease
                    'threshold_critical': 0.5
                }
            },
            'communication': {
                'message_tone_negative': {
                    'weight': 0.4,
                    'threshold_high': 0.6,  # sentiment score
                    'threshold_critical': 0.8
                },
                'response_time_increase': {
                    'weight': 0.3,
                    'threshold_high': 2.0,  # multiplier of normal
                    'threshold_critical': 5.0
                },
                'communication_decrease': {
                    'weight': 0.3,
                    'threshold_high': 0.4,  # 40% decrease
                    'threshold_critical': 0.7
                },
                'urgent_keyword_increase': {
                    'weight': 0.5,
                    'threshold_high': 3,    # times more than usual
                    'threshold_critical': 5
                }
            },
            'cognitive': {
                'focus_duration_decrease': {
                    'weight': 0.4,
                    'threshold_high': 0.3,
                    'threshold_critical': 0.5
                },
                'task_completion_rate': {
                    'weight': 0.5,
                    'threshold_high': 0.7,  # completion rate
                    'threshold_critical': 0.5
                },
                'error_rate_increase': {
                    'weight': 0.4,
                    'threshold_high': 2.0,  # multiplier
                    'threshold_critical': 3.0
                },
                'decision_making_delay': {
                    'weight': 0.3,
                    'threshold_high': 1.5,
                    'threshold_critical': 2.5
                }
            },
            'physiological': {
                'sleep_pattern_disruption': {
                    'weight': 0.5,
                    'threshold_high': 0.3,
                    'threshold_critical': 0.6
                },
                'activity_level_change': {
                    'weight': 0.3,
                    'threshold_high': 0.4,
                    'threshold_critical': 0.7
                }
            }
        }

    def _initialize_trigger_patterns(self) -> Dict[StressTrigger, List[str]]:
        """Initialize patterns that indicate different stress triggers"""
        return {
            StressTrigger.WORKLOAD: [
                'high_work_hours', 'frequent_app_switching', 'late_night_activity',
                'urgent_communications', 'task_overload_indicators'
            ],
            StressTrigger.SOCIAL: [
                'decreased_communication', 'negative_message_tone', 
                'social_isolation_indicators', 'conflict_keywords'
            ],
            StressTrigger.TIME_PRESSURE: [
                'urgent_keyword_increase', 'rapid_task_switching',
                'shortened_break_periods', 'deadline_proximity_stress'
            ],
            StressTrigger.TECHNOLOGY: [
                'frequent_system_issues', 'software_error_encounters',
                'connectivity_problems', 'device_performance_issues'
            ],
            StressTrigger.UNCERTAINTY: [
                'information_seeking_increase', 'planning_behavior_change',
                'decision_delay_patterns', 'anxiety_keywords'
            ]
        }

    async def add_stress_indicator(self, user_id: str, indicator_type: str,
                                 value: float, source: str = "system",
                                 metadata: Dict[str, Any] = None) -> str:
        """Add a stress indicator data point"""
        try:
            indicator_id = hashlib.md5(
                f"{user_id}_{indicator_type}_{datetime.now().timestamp()}_{value}".encode()
            ).hexdigest()
            
            indicator = StressIndicator(
                indicator_type=indicator_type,
                value=value,
                timestamp=datetime.now(),
                confidence=self._calculate_indicator_confidence(indicator_type, value, source),
                source=source,
                metadata=metadata or {}
            )
            
            # Add to buffer for real-time analysis
            self.stress_indicators_buffer[user_id].append(indicator)
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO stress_indicators
                (indicator_id, user_id, indicator_type, value, timestamp, confidence, source, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                indicator_id,
                user_id,
                indicator.indicator_type,
                indicator.value,
                indicator.timestamp.isoformat(),
                indicator.confidence,
                indicator.source,
                json.dumps(indicator.metadata)
            ))
            
            conn.commit()
            conn.close()
            
            # Check if analysis should be triggered
            await self._check_stress_analysis_trigger(user_id)
            
            logger.debug(f"Added stress indicator: {indicator_type} = {value}")
            return indicator_id
            
        except Exception as e:
            logger.error(f"Error adding stress indicator: {e}")
            return ""

    def _calculate_indicator_confidence(self, indicator_type: str, value: float, source: str) -> float:
        """Calculate confidence level for a stress indicator"""
        base_confidence = 0.7
        
        # Adjust based on source reliability
        source_weights = {
            'system': 0.9,
            'behavioral_analysis': 0.8,
            'text_analysis': 0.7,
            'user_input': 0.6,
            'inferred': 0.5
        }
        
        source_weight = source_weights.get(source, 0.5)
        
        # Adjust based on indicator type reliability
        type_weights = {
            'typing_speed_variance': 0.8,
            'work_hour_extension': 0.9,
            'message_tone_negative': 0.7,
            'sleep_pattern_disruption': 0.8
        }
        
        type_weight = type_weights.get(indicator_type, 0.6)
        
        return min(base_confidence * source_weight * type_weight, 1.0)

    async def analyze_user_stress(self, user_id: str, 
                                time_window: timedelta = None) -> StressAnalysis:
        """Perform comprehensive stress analysis for a user"""
        try:
            time_window = time_window or self.config.detection_window
            cutoff_time = datetime.now() - time_window
            
            # Load stress indicators
            indicators = await self._load_stress_indicators(user_id, cutoff_time)
            
            if len(indicators) < self.config.min_data_points:
                logger.warning(f"Not enough stress indicators for analysis: {len(indicators)}")
                return None
            
            # Calculate current stress level
            current_stress_level = await self._calculate_current_stress_level(indicators)
            
            # Analyze stress trend
            stress_trend = await self._calculate_stress_trend(indicators)
            
            # Identify dominant stress type
            dominant_stress_type = await self._identify_dominant_stress_type(indicators)
            
            # Identify primary triggers
            primary_triggers = await self._identify_primary_triggers(indicators, user_id)
            
            # Detect stress patterns
            stress_patterns = await self._detect_stress_patterns(user_id, indicators)
            
            # Identify recent stress events
            recent_events = await self._identify_recent_stress_events(user_id, indicators)
            
            # Assess risk and protective factors
            risk_factors = await self._assess_risk_factors(indicators, stress_patterns)
            protective_factors = await self._assess_protective_factors(user_id, indicators)
            
            # Generate recommendations
            recommendations = await self._generate_stress_recommendations(
                current_stress_level, primary_triggers, risk_factors
            )
            
            # Determine urgency level
            urgency_level = await self._determine_urgency_level(
                current_stress_level, stress_trend, risk_factors
            )
            
            # Create analysis
            analysis_id = hashlib.md5(
                f"{user_id}_stress_analysis_{datetime.now().timestamp()}".encode()
            ).hexdigest()
            
            analysis = StressAnalysis(
                analysis_id=analysis_id,
                user_id=user_id,
                analysis_timestamp=datetime.now(),
                current_stress_level=current_stress_level,
                stress_trend=stress_trend,
                dominant_stress_type=dominant_stress_type,
                primary_triggers=primary_triggers,
                stress_patterns=stress_patterns,
                recent_events=recent_events,
                risk_factors=risk_factors,
                protective_factors=protective_factors,
                recommendations=recommendations,
                urgency_level=urgency_level
            )
            
            # Save analysis
            await self._save_stress_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing user stress: {e}")
            return None

    async def _load_stress_indicators(self, user_id: str, cutoff_time: datetime) -> List[StressIndicator]:
        """Load stress indicators from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT indicator_type, value, timestamp, confidence, source, metadata
                FROM stress_indicators
                WHERE user_id = ? AND timestamp > ?
                ORDER BY timestamp
            ''', (user_id, cutoff_time.isoformat()))
            
            indicators = []
            for row in cursor.fetchall():
                indicator_type, value, timestamp_str, confidence, source, metadata_str = row
                
                metadata = json.loads(metadata_str) if metadata_str else {}
                
                indicator = StressIndicator(
                    indicator_type=indicator_type,
                    value=value,
                    timestamp=datetime.fromisoformat(timestamp_str),
                    confidence=confidence,
                    source=source,
                    metadata=metadata
                )
                indicators.append(indicator)
            
            conn.close()
            return indicators
            
        except Exception as e:
            logger.error(f"Error loading stress indicators: {e}")
            return []

    async def _calculate_current_stress_level(self, indicators: List[StressIndicator]) -> StressLevel:
        """Calculate current stress level from indicators"""
        try:
            if not indicators:
                return StressLevel.LOW
            
            # Get recent indicators (last 6 hours)
            recent_cutoff = datetime.now() - timedelta(hours=6)
            recent_indicators = [i for i in indicators if i.timestamp > recent_cutoff]
            
            if not recent_indicators:
                recent_indicators = indicators[-10:]  # Last 10 indicators
            
            # Calculate weighted stress score
            total_score = 0.0
            total_weight = 0.0
            
            for indicator in recent_indicators:
                # Get weight for this indicator type
                weight = self._get_indicator_weight(indicator.indicator_type)
                
                # Normalize value to 0-1 scale
                normalized_value = self._normalize_indicator_value(indicator.indicator_type, indicator.value)
                
                # Weight by confidence
                weighted_score = normalized_value * weight * indicator.confidence
                
                total_score += weighted_score
                total_weight += weight * indicator.confidence
            
            # Calculate average stress score
            if total_weight == 0:
                stress_score = 0.0
            else:
                stress_score = total_score / total_weight
            
            # Map to stress level enum
            if stress_score >= 0.9:
                return StressLevel.CRITICAL
            elif stress_score >= 0.7:
                return StressLevel.VERY_HIGH
            elif stress_score >= 0.5:
                return StressLevel.HIGH
            elif stress_score >= 0.3:
                return StressLevel.MODERATE
            elif stress_score >= 0.1:
                return StressLevel.LOW
            else:
                return StressLevel.VERY_LOW
                
        except Exception as e:
            logger.error(f"Error calculating current stress level: {e}")
            return StressLevel.MODERATE

    def _get_indicator_weight(self, indicator_type: str) -> float:
        """Get weight for specific indicator type"""
        for category, indicators in self.stress_indicators_config.items():
            if indicator_type in indicators:
                return indicators[indicator_type]['weight']
        return 0.3  # Default weight

    def _normalize_indicator_value(self, indicator_type: str, value: float) -> float:
        """Normalize indicator value to 0-1 stress scale"""
        # Find indicator configuration
        for category, indicators in self.stress_indicators_config.items():
            if indicator_type in indicators:
                config = indicators[indicator_type]
                threshold_high = config.get('threshold_high', 1.0)
                threshold_critical = config.get('threshold_critical', 2.0)
                
                # Normalize based on thresholds
                if value >= threshold_critical:
                    return 1.0
                elif value >= threshold_high:
                    return 0.5 + 0.5 * (value - threshold_high) / (threshold_critical - threshold_high)
                else:
                    return 0.5 * value / threshold_high
        
        # Default normalization
        return min(value, 1.0)

    async def _calculate_stress_trend(self, indicators: List[StressIndicator]) -> float:
        """Calculate stress trend over time"""
        try:
            if len(indicators) < 5:
                return 0.0
            
            # Group indicators by time periods
            time_periods = 6  # hours
            period_duration = timedelta(hours=24 / time_periods)
            
            period_scores = []
            current_time = datetime.now()
            
            for i in range(time_periods):
                period_start = current_time - timedelta(hours=(i+1) * 4)
                period_end = current_time - timedelta(hours=i * 4)
                
                period_indicators = [
                    ind for ind in indicators 
                    if period_start <= ind.timestamp <= period_end
                ]
                
                if period_indicators:
                    # Calculate average stress for this period
                    period_stress = np.mean([
                        self._normalize_indicator_value(ind.indicator_type, ind.value) 
                        for ind in period_indicators
                    ])
                    period_scores.append(period_stress)
            
            if len(period_scores) < 3:
                return 0.0
            
            # Calculate trend using linear regression
            x = np.arange(len(period_scores))
            coefficients = np.polyfit(x, period_scores, 1)
            trend = coefficients[0]  # Slope
            
            # Normalize to -1 to 1 range
            return max(-1.0, min(1.0, trend * 10))
            
        except Exception as e:
            logger.error(f"Error calculating stress trend: {e}")
            return 0.0

    async def _identify_dominant_stress_type(self, indicators: List[StressIndicator]) -> StressType:
        """Identify the dominant type of stress"""
        try:
            # Analyze patterns to determine stress type
            stress_scores = []
            for indicator in indicators[-50:]:  # Last 50 indicators
                normalized_value = self._normalize_indicator_value(
                    indicator.indicator_type, indicator.value
                )
                stress_scores.append((indicator.timestamp, normalized_value))
            
            if not stress_scores:
                return StressType.SITUATIONAL
            
            # Sort by timestamp
            stress_scores.sort(key=lambda x: x[0])
            
            # Analyze patterns
            high_stress_periods = [
                (timestamp, score) for timestamp, score in stress_scores 
                if score > 0.6
            ]
            
            if not high_stress_periods:
                return StressType.SITUATIONAL
            
            # Check for chronic stress (persistent high stress)
            if len(high_stress_periods) > len(stress_scores) * 0.7:
                return StressType.CHRONIC
            
            # Check for acute stress (short bursts of very high stress)
            very_high_stress = [score for _, score in high_stress_periods if score > 0.8]
            if len(very_high_stress) > 0 and len(high_stress_periods) < len(stress_scores) * 0.3:
                return StressType.ACUTE
            
            # Check for episodic stress (recurring patterns)
            time_diffs = []
            for i in range(1, len(high_stress_periods)):
                time_diff = (high_stress_periods[i][0] - high_stress_periods[i-1][0]).total_seconds() / 3600
                time_diffs.append(time_diff)
            
            if time_diffs and np.std(time_diffs) < np.mean(time_diffs) * 0.5:
                return StressType.EPISODIC
            
            return StressType.SITUATIONAL
            
        except Exception as e:
            logger.error(f"Error identifying dominant stress type: {e}")
            return StressType.SITUATIONAL

    async def _identify_primary_triggers(self, indicators: List[StressIndicator], 
                                       user_id: str) -> List[StressTrigger]:
        """Identify primary stress triggers"""
        try:
            trigger_scores = defaultdict(float)
            
            # Analyze indicators for trigger patterns
            for indicator in indicators:
                indicator_triggers = self._map_indicator_to_triggers(indicator)
                
                normalized_value = self._normalize_indicator_value(
                    indicator.indicator_type, indicator.value
                )
                
                for trigger in indicator_triggers:
                    trigger_scores[trigger] += normalized_value * indicator.confidence
            
            # Sort triggers by score
            sorted_triggers = sorted(
                trigger_scores.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Return top triggers with significant scores
            primary_triggers = [
                trigger for trigger, score in sorted_triggers[:5] 
                if score > 0.3
            ]
            
            return primary_triggers
            
        except Exception as e:
            logger.error(f"Error identifying primary triggers: {e}")
            return [StressTrigger.WORKLOAD]  # Default fallback

    def _map_indicator_to_triggers(self, indicator: StressIndicator) -> List[StressTrigger]:
        """Map stress indicator to potential triggers"""
        trigger_mapping = {
            'work_hour_extension': [StressTrigger.WORKLOAD, StressTrigger.TIME_PRESSURE],
            'app_switching_frequency': [StressTrigger.WORKLOAD, StressTrigger.TECHNOLOGY],
            'message_tone_negative': [StressTrigger.SOCIAL, StressTrigger.WORKLOAD],
            'communication_decrease': [StressTrigger.SOCIAL, StressTrigger.ISOLATION],
            'urgent_keyword_increase': [StressTrigger.TIME_PRESSURE, StressTrigger.WORKLOAD],
            'sleep_pattern_disruption': [StressTrigger.WORKLOAD, StressTrigger.HEALTH],
            'task_completion_rate': [StressTrigger.WORKLOAD, StressTrigger.PERFECTIONISM],
            'typing_speed_variance': [StressTrigger.TIME_PRESSURE, StressTrigger.UNCERTAINTY]
        }
        
        return trigger_mapping.get(indicator.indicator_type, [StressTrigger.WORKLOAD])

    async def _detect_stress_patterns(self, user_id: str, 
                                    indicators: List[StressIndicator]) -> List[StressPattern]:
        """Detect recurring stress patterns"""
        try:
            patterns = []
            
            # Group indicators by type and time
            type_groups = defaultdict(list)
            for indicator in indicators:
                type_groups[indicator.indicator_type].append(indicator)
            
            # Analyze each indicator type for patterns
            for indicator_type, type_indicators in type_groups.items():
                if len(type_indicators) < 10:  # Need minimum data for pattern detection
                    continue
                
                # Time-based pattern analysis
                timestamps = [ind.timestamp for ind in type_indicators]
                values = [ind.value for ind in type_indicators]
                
                # Hour of day pattern
                hour_pattern = self._analyze_time_pattern(timestamps, values, 'hour')
                
                # Day of week pattern
                day_pattern = self._analyze_time_pattern(timestamps, values, 'day')
                
                # Only create pattern if significant
                if max(hour_pattern) > np.mean(hour_pattern) * 1.5:
                    pattern_id = hashlib.md5(
                        f"{user_id}_{indicator_type}_pattern".encode()
                    ).hexdigest()
                    
                    pattern = StressPattern(
                        pattern_id=pattern_id,
                        pattern_type=f"{indicator_type}_temporal",
                        triggers=self._map_indicator_to_triggers(type_indicators[0]),
                        frequency=len(type_indicators) / 30,  # per month
                        intensity=np.mean(values),
                        duration=timedelta(hours=2),  # Estimated
                        time_of_day_pattern=[i for i, v in enumerate(hour_pattern) if v > np.mean(hour_pattern) * 1.2],
                        day_of_week_pattern=[i for i, v in enumerate(day_pattern) if v > np.mean(day_pattern) * 1.2]
                    )
                    
                    patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting stress patterns: {e}")
            return []

    def _analyze_time_pattern(self, timestamps: List[datetime], 
                            values: List[float], pattern_type: str) -> List[float]:
        """Analyze temporal patterns in stress indicators"""
        if pattern_type == 'hour':
            periods = 24
            extract_fn = lambda dt: dt.hour
        elif pattern_type == 'day':
            periods = 7
            extract_fn = lambda dt: dt.weekday()
        else:
            return []
        
        period_values = [[] for _ in range(periods)]
        
        for timestamp, value in zip(timestamps, values):
            period = extract_fn(timestamp)
            period_values[period].append(value)
        
        # Calculate average for each period
        pattern = []
        for period_vals in period_values:
            if period_vals:
                pattern.append(np.mean(period_vals))
            else:
                pattern.append(0.0)
        
        return pattern

    async def _identify_recent_stress_events(self, user_id: str, 
                                           indicators: List[StressIndicator]) -> List[StressEvent]:
        """Identify recent stress events"""
        try:
            events = []
            
            # Look for stress spikes in recent data
            recent_cutoff = datetime.now() - timedelta(days=7)
            recent_indicators = [i for i in indicators if i.timestamp > recent_cutoff]
            
            if not recent_indicators:
                return events
            
            # Find periods of elevated stress
            stress_scores = []
            for indicator in recent_indicators:
                normalized_value = self._normalize_indicator_value(
                    indicator.indicator_type, indicator.value
                )
                stress_scores.append((indicator.timestamp, normalized_value, indicator))
            
            # Sort by timestamp
            stress_scores.sort(key=lambda x: x[0])
            
            # Identify stress events (periods above threshold)
            in_event = False
            event_start = None
            event_indicators = []
            
            for timestamp, score, indicator in stress_scores:
                if score > 0.6 and not in_event:
                    # Start of stress event
                    in_event = True
                    event_start = timestamp
                    event_indicators = [indicator]
                elif score > 0.6 and in_event:
                    # Continue stress event
                    event_indicators.append(indicator)
                elif score <= 0.6 and in_event:
                    # End of stress event
                    in_event = False
                    
                    if event_indicators and event_start:
                        event_id = hashlib.md5(
                            f"{user_id}_{event_start}_{len(event_indicators)}".encode()
                        ).hexdigest()
                        
                        # Calculate event characteristics
                        avg_stress = np.mean([
                            self._normalize_indicator_value(ind.indicator_type, ind.value)
                            for ind in event_indicators
                        ])
                        
                        stress_level = self._score_to_stress_level(avg_stress)
                        duration = timestamp - event_start
                        triggers = list(set([
                            trigger for indicator in event_indicators
                            for trigger in self._map_indicator_to_triggers(indicator)
                        ]))
                        
                        event = StressEvent(
                            event_id=event_id,
                            timestamp=event_start,
                            stress_level=stress_level,
                            stress_type=StressType.ACUTE,  # Recent events are typically acute
                            duration=duration,
                            triggers=triggers,
                            contributing_indicators=event_indicators
                        )
                        
                        events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error identifying recent stress events: {e}")
            return []

    def _score_to_stress_level(self, score: float) -> StressLevel:
        """Convert numeric stress score to StressLevel enum"""
        if score >= 0.9:
            return StressLevel.CRITICAL
        elif score >= 0.7:
            return StressLevel.VERY_HIGH
        elif score >= 0.5:
            return StressLevel.HIGH
        elif score >= 0.3:
            return StressLevel.MODERATE
        elif score >= 0.1:
            return StressLevel.LOW
        else:
            return StressLevel.VERY_LOW

    async def _assess_risk_factors(self, indicators: List[StressIndicator],
                                 patterns: List[StressPattern]) -> List[str]:
        """Assess risk factors for stress escalation"""
        risk_factors = []
        
        # High baseline stress
        recent_stress = np.mean([
            self._normalize_indicator_value(ind.indicator_type, ind.value)
            for ind in indicators[-20:]
        ]) if indicators else 0
        
        if recent_stress > 0.6:
            risk_factors.append("Consistently elevated stress levels")
        
        # Multiple stress patterns
        if len(patterns) > 3:
            risk_factors.append("Multiple recurring stress patterns")
        
        # Work-life balance indicators
        work_indicators = [
            ind for ind in indicators
            if ind.indicator_type in ['work_hour_extension', 'urgent_keyword_increase']
        ]
        
        if len(work_indicators) > len(indicators) * 0.4:
            risk_factors.append("Work-related stress dominance")
        
        # Sleep disruption
        sleep_indicators = [
            ind for ind in indicators
            if ind.indicator_type == 'sleep_pattern_disruption' and ind.value > 0.5
        ]
        
        if sleep_indicators:
            risk_factors.append("Sleep pattern disruption")
        
        # Social isolation
        social_indicators = [
            ind for ind in indicators
            if ind.indicator_type in ['communication_decrease', 'social_isolation_indicators']
        ]
        
        if social_indicators:
            risk_factors.append("Social isolation indicators")
        
        return risk_factors

    async def _assess_protective_factors(self, user_id: str, 
                                       indicators: List[StressIndicator]) -> List[str]:
        """Assess protective factors against stress"""
        protective_factors = []
        
        # Regular activity patterns (indicates structure)
        activity_regularity = self._calculate_activity_regularity(indicators)
        if activity_regularity > 0.7:
            protective_factors.append("Consistent activity patterns")
        
        # Social engagement
        social_engagement = self._calculate_social_engagement(indicators)
        if social_engagement > 0.6:
            protective_factors.append("Healthy social engagement")
        
        # Stress recovery indicators
        recovery_indicators = [
            ind for ind in indicators
            if 'recovery' in ind.metadata.get('context', '')
        ]
        
        if recovery_indicators:
            protective_factors.append("Active stress recovery practices")
        
        # Work-life boundaries
        boundary_indicators = self._analyze_work_life_boundaries(indicators)
        if boundary_indicators > 0.6:
            protective_factors.append("Good work-life boundaries")
        
        return protective_factors

    def _calculate_activity_regularity(self, indicators: List[StressIndicator]) -> float:
        """Calculate regularity of activities as protective factor"""
        if not indicators:
            return 0.0
        
        # Simplified calculation based on indicator timing patterns
        timestamps = [ind.timestamp for ind in indicators]
        hours = [ts.hour for ts in timestamps]
        
        # Calculate consistency in timing
        hour_counts = defaultdict(int)
        for hour in hours:
            hour_counts[hour] += 1
        
        # Higher variance in timing indicates regularity
        regularity_score = len(hour_counts) / 24.0
        return min(regularity_score, 1.0)

    def _calculate_social_engagement(self, indicators: List[StressIndicator]) -> float:
        """Calculate social engagement level"""
        social_indicators = [
            ind for ind in indicators
            if 'social' in ind.indicator_type or 'communication' in ind.indicator_type
        ]
        
        if not social_indicators:
            return 0.5  # Neutral if no data
        
        # Calculate engagement based on communication patterns
        positive_social = [
            ind for ind in social_indicators
            if ind.value > 0.5  # Assuming higher values indicate positive engagement
        ]
        
        engagement_ratio = len(positive_social) / len(social_indicators)
        return engagement_ratio

    def _analyze_work_life_boundaries(self, indicators: List[StressIndicator]) -> float:
        """Analyze work-life boundary health"""
        work_indicators = [
            ind for ind in indicators
            if ind.indicator_type in ['work_hour_extension', 'urgent_keyword_increase']
        ]
        
        if not work_indicators:
            return 0.7  # Assume good boundaries if no work stress indicators
        
        # Lower work stress indicators suggest better boundaries
        avg_work_stress = np.mean([
            self._normalize_indicator_value(ind.indicator_type, ind.value)
            for ind in work_indicators
        ])
        
        return max(0, 1 - avg_work_stress)

    async def _generate_stress_recommendations(self, stress_level: StressLevel,
                                             triggers: List[StressTrigger],
                                             risk_factors: List[str]) -> List[str]:
        """Generate personalized stress management recommendations"""
        recommendations = []
        
        # General recommendations based on stress level
        if stress_level in [StressLevel.HIGH, StressLevel.VERY_HIGH, StressLevel.CRITICAL]:
            recommendations.append("Consider taking immediate steps to reduce current stressors")
            recommendations.append("Practice deep breathing or meditation techniques")
            
            if stress_level == StressLevel.CRITICAL:
                recommendations.append("Seek immediate support from mental health professional")
        
        # Trigger-specific recommendations
        for trigger in triggers:
            if trigger == StressTrigger.WORKLOAD:
                recommendations.extend([
                    "Review current workload and prioritize essential tasks",
                    "Consider delegating or postponing non-critical tasks",
                    "Schedule regular breaks throughout workday"
                ])
            elif trigger == StressTrigger.TIME_PRESSURE:
                recommendations.extend([
                    "Use time management techniques like time blocking",
                    "Break large tasks into smaller, manageable chunks",
                    "Set realistic deadlines and expectations"
                ])
            elif trigger == StressTrigger.SOCIAL:
                recommendations.extend([
                    "Reach out to trusted friends or family members",
                    "Consider setting boundaries with difficult relationships",
                    "Engage in positive social activities"
                ])
            elif trigger == StressTrigger.TECHNOLOGY:
                recommendations.extend([
                    "Take regular breaks from screens and devices",
                    "Ensure technology tools are working properly",
                    "Consider digital detox periods"
                ])
        
        # Risk factor specific recommendations
        for risk_factor in risk_factors:
            if "sleep" in risk_factor.lower():
                recommendations.append("Prioritize consistent sleep schedule and sleep hygiene")
            elif "social isolation" in risk_factor.lower():
                recommendations.append("Make an effort to connect with others regularly")
            elif "work-related" in risk_factor.lower():
                recommendations.append("Establish clear work-life boundaries")
        
        return list(set(recommendations))  # Remove duplicates

    async def _determine_urgency_level(self, stress_level: StressLevel, 
                                     stress_trend: float, 
                                     risk_factors: List[str]) -> str:
        """Determine urgency level for intervention"""
        
        if stress_level == StressLevel.CRITICAL:
            return "critical"
        elif stress_level == StressLevel.VERY_HIGH:
            if stress_trend > 0.3 or len(risk_factors) > 3:
                return "critical"
            else:
                return "high"
        elif stress_level == StressLevel.HIGH:
            if stress_trend > 0.5:
                return "high"
            elif len(risk_factors) > 2:
                return "high"
            else:
                return "medium"
        elif stress_level == StressLevel.MODERATE:
            if stress_trend > 0.7 or len(risk_factors) > 2:
                return "medium"
            else:
                return "low"
        else:
            return "low"

    async def _save_stress_analysis(self, analysis: StressAnalysis):
        """Save stress analysis to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO stress_analyses
                (analysis_id, user_id, analysis_timestamp, current_stress_level, stress_trend,
                 dominant_stress_type, primary_triggers, risk_factors, protective_factors,
                 recommendations, urgency_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis.analysis_id,
                analysis.user_id,
                analysis.analysis_timestamp.isoformat(),
                analysis.current_stress_level.value,
                analysis.stress_trend,
                analysis.dominant_stress_type.value,
                json.dumps([t.value for t in analysis.primary_triggers]),
                json.dumps(analysis.risk_factors),
                json.dumps(analysis.protective_factors),
                json.dumps(analysis.recommendations),
                analysis.urgency_level
            ))
            
            # Save patterns
            for pattern in analysis.stress_patterns:
                cursor.execute('''
                    INSERT OR REPLACE INTO stress_patterns
                    (pattern_id, user_id, pattern_type, triggers, frequency, intensity, duration,
                     time_of_day_pattern, day_of_week_pattern, seasonal_pattern, environmental_factors,
                     created_at, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pattern.pattern_id,
                    analysis.user_id,
                    pattern.pattern_type,
                    json.dumps([t.value for t in pattern.triggers]),
                    pattern.frequency,
                    pattern.intensity,
                    pattern.duration.total_seconds(),
                    json.dumps(pattern.time_of_day_pattern),
                    json.dumps(pattern.day_of_week_pattern),
                    pattern.seasonal_pattern,
                    json.dumps(pattern.environmental_factors),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            
            # Save events
            for event in analysis.recent_events:
                cursor.execute('''
                    INSERT OR REPLACE INTO stress_events
                    (event_id, user_id, timestamp, stress_level, stress_type, duration, triggers,
                     contributing_indicators, recovery_time, impact_areas, coping_strategies_used,
                     effectiveness_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.event_id,
                    analysis.user_id,
                    event.timestamp.isoformat(),
                    event.stress_level.value,
                    event.stress_type.value,
                    event.duration.total_seconds(),
                    json.dumps([t.value for t in event.triggers]),
                    json.dumps([ind.indicator_type for ind in event.contributing_indicators]),
                    event.recovery_time.total_seconds() if event.recovery_time else None,
                    json.dumps(event.impact_areas),
                    json.dumps(event.coping_strategies_used),
                    event.effectiveness_score
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving stress analysis: {e}")

    async def _check_stress_analysis_trigger(self, user_id: str):
        """Check if stress analysis should be triggered"""
        try:
            # Trigger analysis if buffer has enough new indicators
            buffer = self.stress_indicators_buffer.get(user_id, deque())
            
            if len(buffer) >= 10:  # Enough indicators for analysis
                await self.analyze_user_stress(user_id)
                
                # Clear some indicators from buffer to avoid constant reanalysis
                for _ in range(5):
                    if buffer:
                        buffer.popleft()
                        
        except Exception as e:
            logger.error(f"Error checking stress analysis trigger: {e}")

    async def get_stress_statistics(self, user_id: str,
                                  time_range: timedelta = timedelta(days=30)) -> Dict[str, Any]:
        """Get stress detection statistics"""
        try:
            cutoff_time = datetime.now() - time_range
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Basic statistics
            cursor.execute('''
                SELECT COUNT(*) FROM stress_indicators 
                WHERE user_id = ? AND timestamp > ?
            ''', (user_id, cutoff_time.isoformat()))
            total_indicators = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM stress_analyses 
                WHERE user_id = ? AND analysis_timestamp > ?
            ''', (user_id, cutoff_time.isoformat()))
            total_analyses = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM stress_events 
                WHERE user_id = ? AND timestamp > ?
            ''', (user_id, cutoff_time.isoformat()))
            total_events = cursor.fetchone()[0]
            
            # Recent stress level
            cursor.execute('''
                SELECT current_stress_level, stress_trend 
                FROM stress_analyses 
                WHERE user_id = ? 
                ORDER BY analysis_timestamp DESC LIMIT 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            current_level = result[0] if result else "unknown"
            current_trend = result[1] if result else 0.0
            
            conn.close()
            
            return {
                'total_stress_indicators': total_indicators,
                'total_stress_analyses': total_analyses,
                'total_stress_events': total_events,
                'current_stress_level': current_level,
                'current_stress_trend': current_trend,
                'time_range_days': time_range.days,
                'analysis_period': {
                    'start': cutoff_time.isoformat(),
                    'end': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting stress statistics: {e}")
            return {}

# CLI interface for testing
async def main():
    """CLI interface for testing stress detection"""
    print("Stress Detection Engine - Test Interface")
    print("=" * 50)
    
    # Initialize detector
    config = StressDetectionConfig(
        detection_window=timedelta(hours=12),
        stress_threshold=0.6
    )
    
    detector = StressDetector(config)
    
    print("Available commands:")
    print("1. add-indicator <user_id> <type> <value> - Add stress indicator")
    print("2. analyze <user_id> - Analyze user stress")
    print("3. stats <user_id> - Show stress statistics")
    print("4. config - Show current configuration")
    print("5. exit - Exit the program")
    
    while True:
        try:
            command = input("\nEnter command: ").strip()
            
            if command == "exit":
                break
            elif command.startswith("add-indicator "):
                parts = command.split()
                if len(parts) >= 4:
                    user_id = parts[1]
                    indicator_type = parts[2]
                    value = float(parts[3])
                    
                    indicator_id = await detector.add_stress_indicator(
                        user_id=user_id,
                        indicator_type=indicator_type,
                        value=value,
                        source="cli_test"
                    )
                    print(f"Added stress indicator: {indicator_id}")
                else:
                    print("Usage: add-indicator <user_id> <type> <value>")
                    
            elif command.startswith("analyze "):
                user_id = command.split()[1]
                print(f"Analyzing stress for {user_id}...")
                
                analysis = await detector.analyze_user_stress(user_id)
                if analysis:
                    print(f"\nStress Analysis Results:")
                    print(f"Current Stress Level: {analysis.current_stress_level.value}")
                    print(f"Stress Trend: {analysis.stress_trend:.2f}")
                    print(f"Dominant Type: {analysis.dominant_stress_type.value}")
                    print(f"Primary Triggers: {[t.value for t in analysis.primary_triggers]}")
                    print(f"Urgency Level: {analysis.urgency_level}")
                    print(f"Risk Factors: {analysis.risk_factors}")
                    print(f"Protective Factors: {analysis.protective_factors}")
                    print(f"Recommendations: {analysis.recommendations[:3]}...")
                    print(f"Recent Events: {len(analysis.recent_events)}")
                    print(f"Stress Patterns: {len(analysis.stress_patterns)}")
                else:
                    print("Failed to analyze stress (not enough data?)")
                    
            elif command.startswith("stats "):
                user_id = command.split()[1]
                stats = await detector.get_stress_statistics(user_id)
                print(f"\nStress Statistics for {user_id}:")
                print(json.dumps(stats, indent=2))
                
            elif command == "config":
                print("Current configuration:")
                print(f"Detection window: {config.detection_window}")
                print(f"Analysis frequency: {config.analysis_frequency}")
                print(f"Stress threshold: {config.stress_threshold}")
                print(f"Chronic threshold: {config.chronic_threshold_days} days")
                print(f"Acute spike threshold: {config.acute_spike_threshold}")
                print(f"Enable predictive analysis: {config.enable_predictive_analysis}")
                
            else:
                print("Unknown command. Try 'add-indicator', 'analyze', 'stats', 'config', or 'exit'.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("Stress detection engine test completed.")

if __name__ == "__main__":
    asyncio.run(main())