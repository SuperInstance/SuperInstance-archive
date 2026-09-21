"""
Attention Tracking and Engagement Monitoring System

Advanced AI system for monitoring student attention and engagement during digital
learning sessions through behavioral analytics, interaction patterns, and
real-time feedback to optimize learning experiences and maintain focus.
"""

import asyncio
import sqlite3
import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
import numpy as np
from collections import deque
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AttentionState(Enum):
    HIGHLY_ENGAGED = "highly_engaged"
    ENGAGED = "engaged"
    PARTIALLY_ENGAGED = "partially_engaged"
    DISTRACTED = "distracted"
    DISENGAGED = "disengaged"
    OFFLINE = "offline"

class InteractionType(Enum):
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVEMENT = "mouse_movement"
    KEYBOARD_INPUT = "keyboard_input"
    SCROLL = "scroll"
    TAB_SWITCH = "tab_switch"
    WINDOW_FOCUS = "window_focus"
    WINDOW_BLUR = "window_blur"
    CONTENT_VIEW = "content_view"
    VIDEO_PAUSE = "video_pause"
    VIDEO_PLAY = "video_play"
    QUIZ_ATTEMPT = "quiz_attempt"
    PAGE_NAVIGATION = "page_navigation"

class EngagementLevel(Enum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"

class AlertType(Enum):
    ATTENTION_DROP = "attention_drop"
    INACTIVITY = "inactivity"
    DISTRACTION = "distraction"
    CONFUSION = "confusion"
    FATIGUE = "fatigue"
    ENGAGEMENT_SPIKE = "engagement_spike"

@dataclass
class InteractionEvent:
    event_id: str
    student_id: str
    session_id: str
    interaction_type: InteractionType
    timestamp: datetime
    duration: float = 0.0
    coordinates: Optional[Tuple[int, int]] = None
    content_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AttentionMetrics:
    student_id: str
    session_id: str
    timestamp: datetime
    attention_score: float
    engagement_level: EngagementLevel
    attention_state: AttentionState
    focus_duration: float
    interaction_frequency: float
    content_consumption_rate: float
    multitasking_indicator: float
    fatigue_indicator: float
    confusion_indicator: float

@dataclass
class LearningSession:
    session_id: str
    student_id: str
    content_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration: float = 0.0
    active_duration: float = 0.0
    interactions: List[str] = field(default_factory=list)
    attention_metrics: List[str] = field(default_factory=list)
    breaks_taken: List[Dict[str, Any]] = field(default_factory=list)
    completion_status: str = "in_progress"

@dataclass
class EngagementAlert:
    alert_id: str
    student_id: str
    session_id: str
    alert_type: AlertType
    severity: int  # 1-5 scale
    message: str
    timestamp: datetime
    intervention_triggered: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EngagementInsight:
    student_id: str
    analysis_period: Tuple[datetime, datetime]
    avg_attention_score: float
    peak_engagement_times: List[str]
    attention_patterns: Dict[str, Any]
    distraction_triggers: List[str]
    optimal_session_length: float
    recommendations: List[str] = field(default_factory=list)

class EngagementTracker:
    def __init__(self, db_path: str = "education_ai.db"):
        self.db_path = db_path
        self.active_sessions = {}  # session_id -> session data
        self.attention_history = {}  # student_id -> deque of recent metrics
        self.interaction_buffers = {}  # session_id -> deque of recent interactions
        self.alert_thresholds = {
            'min_attention_score': 0.3,
            'max_inactivity_time': 300,  # 5 minutes
            'min_interaction_frequency': 0.1,  # interactions per second
            'fatigue_threshold': 0.7,
            'confusion_threshold': 0.6
        }
        self.init_database()
        
    def init_database(self):
        """Initialize database tables for attention tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_sessions (
                session_id TEXT PRIMARY KEY,
                student_id TEXT,
                content_type TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                total_duration REAL,
                active_duration REAL,
                interactions TEXT,
                attention_metrics TEXT,
                breaks_taken TEXT,
                completion_status TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interaction_events (
                event_id TEXT PRIMARY KEY,
                student_id TEXT,
                session_id TEXT,
                interaction_type TEXT,
                timestamp TIMESTAMP,
                duration REAL,
                coordinates TEXT,
                content_id TEXT,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attention_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                session_id TEXT,
                timestamp TIMESTAMP,
                attention_score REAL,
                engagement_level TEXT,
                attention_state TEXT,
                focus_duration REAL,
                interaction_frequency REAL,
                content_consumption_rate REAL,
                multitasking_indicator REAL,
                fatigue_indicator REAL,
                confusion_indicator REAL,
                FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS engagement_alerts (
                alert_id TEXT PRIMARY KEY,
                student_id TEXT,
                session_id TEXT,
                alert_type TEXT,
                severity INTEGER,
                message TEXT,
                timestamp TIMESTAMP,
                intervention_triggered BOOLEAN,
                resolved BOOLEAN,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES learning_sessions (session_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS engagement_insights (
                insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                analysis_start_date TIMESTAMP,
                analysis_end_date TIMESTAMP,
                avg_attention_score REAL,
                peak_engagement_times TEXT,
                attention_patterns TEXT,
                distraction_triggers TEXT,
                optimal_session_length REAL,
                recommendations TEXT,
                generated_date TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Attention tracking and engagement monitoring database initialized")

    async def start_learning_session(self, student_id: str, content_type: str) -> str:
        """
        Start a new learning session for attention tracking
        
        Args:
            student_id: Student identifier
            content_type: Type of content (video, text, interactive, etc.)
            
        Returns:
            Session ID for tracking
        """
        session_id = f"session_{student_id}_{int(time.time())}"
        
        session = LearningSession(
            session_id=session_id,
            student_id=student_id,
            content_type=content_type,
            start_time=datetime.now()
        )
        
        self.active_sessions[session_id] = session
        self.interaction_buffers[session_id] = deque(maxlen=100)  # Keep last 100 interactions
        
        if student_id not in self.attention_history:
            self.attention_history[student_id] = deque(maxlen=50)  # Keep last 50 attention records
        
        await self._save_session(session)
        
        # Start background monitoring
        asyncio.create_task(self._monitor_session(session_id))
        
        logger.info(f"Started learning session {session_id} for student {student_id}")
        return session_id

    async def record_interaction(self, session_id: str, interaction_type: InteractionType,
                               coordinates: Optional[Tuple[int, int]] = None,
                               content_id: Optional[str] = None,
                               metadata: Dict[str, Any] = None) -> InteractionEvent:
        """
        Record a student interaction event
        
        Args:
            session_id: Active session identifier
            interaction_type: Type of interaction
            coordinates: Mouse coordinates (if applicable)
            content_id: ID of content being interacted with
            metadata: Additional interaction metadata
            
        Returns:
            Recorded interaction event
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found or not active")
        
        session = self.active_sessions[session_id]
        event_id = f"event_{session_id}_{len(session.interactions)}"
        
        event = InteractionEvent(
            event_id=event_id,
            student_id=session.student_id,
            session_id=session_id,
            interaction_type=interaction_type,
            timestamp=datetime.now(),
            coordinates=coordinates,
            content_id=content_id,
            metadata=metadata or {}
        )
        
        # Add to session and buffer
        session.interactions.append(event_id)
        self.interaction_buffers[session_id].append(event)
        
        # Calculate attention metrics
        attention_metrics = await self._calculate_attention_metrics(session_id)
        
        # Check for alerts
        await self._check_engagement_alerts(session_id, attention_metrics)
        
        # Save event and metrics
        await self._save_interaction_event(event)
        await self._save_attention_metrics(attention_metrics)
        
        return event

    async def end_learning_session(self, session_id: str) -> LearningSession:
        """
        End a learning session and generate final analytics
        
        Args:
            session_id: Session to end
            
        Returns:
            Completed session with analytics
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        session.end_time = datetime.now()
        session.total_duration = (session.end_time - session.start_time).total_seconds()
        session.completion_status = "completed"
        
        # Calculate active duration (time with interactions)
        session.active_duration = await self._calculate_active_duration(session_id)
        
        # Generate session summary
        await self._generate_session_summary(session)
        
        # Save final session state
        await self._save_session(session)
        
        # Clean up active tracking
        del self.active_sessions[session_id]
        del self.interaction_buffers[session_id]
        
        logger.info(f"Ended session {session_id} - Duration: {session.total_duration:.1f}s, Active: {session.active_duration:.1f}s")
        return session

    async def _calculate_attention_metrics(self, session_id: str) -> AttentionMetrics:
        """Calculate current attention metrics for a session"""
        session = self.active_sessions[session_id]
        interactions = list(self.interaction_buffers[session_id])
        
        current_time = datetime.now()
        time_window = 60  # Analyze last 60 seconds
        
        # Filter recent interactions
        recent_interactions = [
            event for event in interactions 
            if (current_time - event.timestamp).total_seconds() <= time_window
        ]
        
        # Calculate interaction frequency
        interaction_frequency = len(recent_interactions) / time_window if time_window > 0 else 0
        
        # Calculate focus duration (time since last distraction)
        focus_duration = await self._calculate_current_focus_duration(interactions)
        
        # Calculate content consumption rate
        content_consumption_rate = await self._calculate_content_consumption_rate(session_id, recent_interactions)
        
        # Calculate multitasking indicator
        multitasking_indicator = self._calculate_multitasking_indicator(recent_interactions)
        
        # Calculate fatigue indicator
        fatigue_indicator = await self._calculate_fatigue_indicator(session_id)
        
        # Calculate confusion indicator
        confusion_indicator = self._calculate_confusion_indicator(recent_interactions)
        
        # Overall attention score (weighted combination)
        attention_score = self._calculate_attention_score(
            interaction_frequency, focus_duration, content_consumption_rate,
            multitasking_indicator, fatigue_indicator, confusion_indicator
        )
        
        # Determine engagement level and attention state
        engagement_level = self._determine_engagement_level(attention_score)
        attention_state = self._determine_attention_state(attention_score, recent_interactions)
        
        metrics = AttentionMetrics(
            student_id=session.student_id,
            session_id=session_id,
            timestamp=current_time,
            attention_score=attention_score,
            engagement_level=engagement_level,
            attention_state=attention_state,
            focus_duration=focus_duration,
            interaction_frequency=interaction_frequency,
            content_consumption_rate=content_consumption_rate,
            multitasking_indicator=multitasking_indicator,
            fatigue_indicator=fatigue_indicator,
            confusion_indicator=confusion_indicator
        )
        
        # Add to student's attention history
        self.attention_history[session.student_id].append(metrics)
        
        return metrics

    def _calculate_attention_score(self, interaction_freq: float, focus_duration: float,
                                 consumption_rate: float, multitasking: float,
                                 fatigue: float, confusion: float) -> float:
        """Calculate overall attention score from component metrics"""
        # Normalize components
        interaction_score = min(interaction_freq * 10, 1.0)  # Cap at 1.0
        focus_score = min(focus_duration / 300, 1.0)  # 5 minutes max focus
        consumption_score = min(consumption_rate, 1.0)
        
        # Penalties
        multitasking_penalty = multitasking * 0.3
        fatigue_penalty = fatigue * 0.4
        confusion_penalty = confusion * 0.2
        
        # Weighted combination
        base_score = (interaction_score * 0.3 + focus_score * 0.4 + consumption_score * 0.3)
        penalties = multitasking_penalty + fatigue_penalty + confusion_penalty
        
        attention_score = max(0.0, base_score - penalties)
        return min(1.0, attention_score)

    async def _calculate_current_focus_duration(self, interactions: List[InteractionEvent]) -> float:
        """Calculate current sustained focus duration"""
        if not interactions:
            return 0.0
        
        # Find last distraction event
        distraction_types = [InteractionType.TAB_SWITCH, InteractionType.WINDOW_BLUR]
        last_distraction_time = None
        
        for event in reversed(interactions):
            if event.interaction_type in distraction_types:
                last_distraction_time = event.timestamp
                break
        
        if last_distraction_time:
            return (datetime.now() - last_distraction_time).total_seconds()
        else:
            # No distractions found, use session start or first interaction
            first_interaction = min(interactions, key=lambda x: x.timestamp)
            return (datetime.now() - first_interaction.timestamp).total_seconds()

    async def _calculate_content_consumption_rate(self, session_id: str, 
                                                interactions: List[InteractionEvent]) -> float:
        """Calculate rate of content consumption"""
        content_interactions = [
            event for event in interactions 
            if event.interaction_type in [InteractionType.SCROLL, InteractionType.CONTENT_VIEW, 
                                         InteractionType.PAGE_NAVIGATION]
        ]
        
        if not content_interactions:
            return 0.0
        
        # Simple rate calculation based on content interactions
        time_span = 60  # seconds
        rate = len(content_interactions) / time_span
        
        return min(rate, 1.0)  # Cap at 1.0

    def _calculate_multitasking_indicator(self, interactions: List[InteractionEvent]) -> float:
        """Calculate multitasking/distraction indicator"""
        if not interactions:
            return 0.0
        
        distraction_events = [
            event for event in interactions 
            if event.interaction_type in [InteractionType.TAB_SWITCH, InteractionType.WINDOW_BLUR]
        ]
        
        distraction_ratio = len(distraction_events) / len(interactions)
        return min(distraction_ratio * 2, 1.0)  # Scale and cap

    async def _calculate_fatigue_indicator(self, session_id: str) -> float:
        """Calculate fatigue indicator based on session duration and patterns"""
        session = self.active_sessions[session_id]
        session_duration = (datetime.now() - session.start_time).total_seconds()
        
        # Base fatigue increases with time
        base_fatigue = min(session_duration / 3600, 1.0)  # 1 hour = full fatigue
        
        # Adjust based on interaction patterns
        if session_id in self.interaction_buffers:
            recent_interactions = list(self.interaction_buffers[session_id])[-20:]  # Last 20 interactions
            
            if recent_interactions:
                # Declining interaction frequency indicates fatigue
                time_gaps = []
                for i in range(1, len(recent_interactions)):
                    gap = (recent_interactions[i].timestamp - recent_interactions[i-1].timestamp).total_seconds()
                    time_gaps.append(gap)
                
                if time_gaps:
                    avg_gap = np.mean(time_gaps)
                    if avg_gap > 30:  # Long gaps between interactions
                        base_fatigue += 0.2
        
        return min(base_fatigue, 1.0)

    def _calculate_confusion_indicator(self, interactions: List[InteractionEvent]) -> float:
        """Calculate confusion indicator from interaction patterns"""
        if len(interactions) < 5:
            return 0.0
        
        confusion_indicators = 0
        
        # Rapid back-and-forth navigation
        nav_events = [e for e in interactions if e.interaction_type == InteractionType.PAGE_NAVIGATION]
        if len(nav_events) >= 3:
            quick_nav = 0
            for i in range(1, len(nav_events)):
                time_diff = (nav_events[i].timestamp - nav_events[i-1].timestamp).total_seconds()
                if time_diff < 5:  # Quick navigation
                    quick_nav += 1
            
            if quick_nav >= 2:
                confusion_indicators += 0.3
        
        # Repeated same actions
        interaction_types = [e.interaction_type for e in interactions[-10:]]  # Last 10 interactions
        if len(set(interaction_types)) < len(interaction_types) * 0.5:  # Low diversity
            confusion_indicators += 0.2
        
        # Long pauses followed by bursts
        time_gaps = []
        for i in range(1, len(interactions)):
            gap = (interactions[i].timestamp - interactions[i-1].timestamp).total_seconds()
            time_gaps.append(gap)
        
        if time_gaps:
            long_pauses = sum(1 for gap in time_gaps if gap > 60)  # Pauses > 1 minute
            if long_pauses >= 2:
                confusion_indicators += 0.3
        
        return min(confusion_indicators, 1.0)

    def _determine_engagement_level(self, attention_score: float) -> EngagementLevel:
        """Determine engagement level from attention score"""
        if attention_score >= 0.9:
            return EngagementLevel.VERY_HIGH
        elif attention_score >= 0.7:
            return EngagementLevel.HIGH
        elif attention_score >= 0.5:
            return EngagementLevel.MODERATE
        elif attention_score >= 0.3:
            return EngagementLevel.LOW
        else:
            return EngagementLevel.VERY_LOW

    def _determine_attention_state(self, attention_score: float, 
                                 recent_interactions: List[InteractionEvent]) -> AttentionState:
        """Determine current attention state"""
        if not recent_interactions:
            return AttentionState.OFFLINE
        
        # Check for recent activity
        last_interaction_time = max(recent_interactions, key=lambda x: x.timestamp).timestamp
        time_since_last = (datetime.now() - last_interaction_time).total_seconds()
        
        if time_since_last > 300:  # 5 minutes of inactivity
            return AttentionState.OFFLINE
        
        # Check for distraction indicators
        distraction_events = [
            e for e in recent_interactions
            if e.interaction_type in [InteractionType.TAB_SWITCH, InteractionType.WINDOW_BLUR]
        ]
        
        if len(distraction_events) >= 3:  # Multiple distractions
            return AttentionState.DISTRACTED
        
        # Use attention score for other states
        if attention_score >= 0.8:
            return AttentionState.HIGHLY_ENGAGED
        elif attention_score >= 0.6:
            return AttentionState.ENGAGED
        elif attention_score >= 0.4:
            return AttentionState.PARTIALLY_ENGAGED
        else:
            return AttentionState.DISENGAGED

    async def _check_engagement_alerts(self, session_id: str, metrics: AttentionMetrics):
        """Check for conditions that should trigger engagement alerts"""
        alerts = []
        
        # Low attention alert
        if metrics.attention_score < self.alert_thresholds['min_attention_score']:
            alert = EngagementAlert(
                alert_id=f"alert_attention_{session_id}_{int(time.time())}",
                student_id=metrics.student_id,
                session_id=session_id,
                alert_type=AlertType.ATTENTION_DROP,
                severity=3 if metrics.attention_score < 0.2 else 2,
                message=f"Attention level has dropped to {metrics.attention_score:.1%}",
                timestamp=datetime.now(),
                metadata={"attention_score": metrics.attention_score}
            )
            alerts.append(alert)
        
        # Inactivity alert
        last_interaction = None
        if session_id in self.interaction_buffers and self.interaction_buffers[session_id]:
            last_interaction = self.interaction_buffers[session_id][-1]
            time_since_last = (datetime.now() - last_interaction.timestamp).total_seconds()
            
            if time_since_last > self.alert_thresholds['max_inactivity_time']:
                alert = EngagementAlert(
                    alert_id=f"alert_inactivity_{session_id}_{int(time.time())}",
                    student_id=metrics.student_id,
                    session_id=session_id,
                    alert_type=AlertType.INACTIVITY,
                    severity=2,
                    message=f"No activity for {time_since_last/60:.1f} minutes",
                    timestamp=datetime.now(),
                    metadata={"inactivity_duration": time_since_last}
                )
                alerts.append(alert)
        
        # Fatigue alert
        if metrics.fatigue_indicator > self.alert_thresholds['fatigue_threshold']:
            alert = EngagementAlert(
                alert_id=f"alert_fatigue_{session_id}_{int(time.time())}",
                student_id=metrics.student_id,
                session_id=session_id,
                alert_type=AlertType.FATIGUE,
                severity=2,
                message="Signs of fatigue detected - consider taking a break",
                timestamp=datetime.now(),
                metadata={"fatigue_indicator": metrics.fatigue_indicator}
            )
            alerts.append(alert)
        
        # Confusion alert
        if metrics.confusion_indicator > self.alert_thresholds['confusion_threshold']:
            alert = EngagementAlert(
                alert_id=f"alert_confusion_{session_id}_{int(time.time())}",
                student_id=metrics.student_id,
                session_id=session_id,
                alert_type=AlertType.CONFUSION,
                severity=2,
                message="Confusion patterns detected - may need additional support",
                timestamp=datetime.now(),
                metadata={"confusion_indicator": metrics.confusion_indicator}
            )
            alerts.append(alert)
        
        # Save alerts and potentially trigger interventions
        for alert in alerts:
            await self._save_engagement_alert(alert)
            await self._consider_intervention(alert)

    async def _consider_intervention(self, alert: EngagementAlert):
        """Consider triggering an intervention based on alert"""
        # Simple intervention logic
        if alert.severity >= 3:
            # High severity - immediate intervention
            intervention = await self._trigger_intervention(alert)
            alert.intervention_triggered = True
            logger.info(f"Triggered intervention for alert {alert.alert_id}: {intervention}")
        elif alert.alert_type in [AlertType.FATIGUE, AlertType.INACTIVITY]:
            # Suggest break
            intervention = "break_suggestion"
            alert.intervention_triggered = True
            logger.info(f"Suggested break for student {alert.student_id}")

    async def _trigger_intervention(self, alert: EngagementAlert) -> str:
        """Trigger specific intervention based on alert type"""
        interventions = {
            AlertType.ATTENTION_DROP: "focus_reminder",
            AlertType.INACTIVITY: "activity_prompt",
            AlertType.DISTRACTION: "focus_redirect",
            AlertType.CONFUSION: "help_offer",
            AlertType.FATIGUE: "break_suggestion"
        }
        
        return interventions.get(alert.alert_type, "general_support")

    async def _monitor_session(self, session_id: str):
        """Background monitoring task for active sessions"""
        while session_id in self.active_sessions:
            try:
                # Calculate metrics periodically
                if session_id in self.interaction_buffers:
                    metrics = await self._calculate_attention_metrics(session_id)
                    await self._save_attention_metrics(metrics)
                    await self._check_engagement_alerts(session_id, metrics)
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in session monitoring for {session_id}: {e}")
                break

    async def generate_engagement_insights(self, student_id: str, 
                                         days_back: int = 7) -> EngagementInsight:
        """
        Generate comprehensive engagement insights for a student
        
        Args:
            student_id: Student identifier
            days_back: Number of days to analyze
            
        Returns:
            Engagement insights and recommendations
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Get attention metrics for the period
        metrics = await self._get_attention_metrics_for_period(student_id, start_date, end_date)
        
        if not metrics:
            return EngagementInsight(
                student_id=student_id,
                analysis_period=(start_date, end_date),
                avg_attention_score=0.0,
                peak_engagement_times=[],
                attention_patterns={},
                distraction_triggers=[],
                optimal_session_length=0.0,
                recommendations=["More data needed for comprehensive analysis"]
            )
        
        # Calculate average attention score
        avg_attention_score = np.mean([m.attention_score for m in metrics])
        
        # Identify peak engagement times
        peak_times = await self._identify_peak_engagement_times(metrics)
        
        # Analyze attention patterns
        attention_patterns = await self._analyze_attention_patterns(metrics)
        
        # Identify distraction triggers
        distraction_triggers = await self._identify_distraction_triggers(student_id, start_date, end_date)
        
        # Calculate optimal session length
        optimal_length = await self._calculate_optimal_session_length(student_id, start_date, end_date)
        
        # Generate recommendations
        recommendations = await self._generate_engagement_recommendations(
            avg_attention_score, attention_patterns, distraction_triggers, optimal_length
        )
        
        insight = EngagementInsight(
            student_id=student_id,
            analysis_period=(start_date, end_date),
            avg_attention_score=avg_attention_score,
            peak_engagement_times=peak_times,
            attention_patterns=attention_patterns,
            distraction_triggers=distraction_triggers,
            optimal_session_length=optimal_length,
            recommendations=recommendations
        )
        
        await self._save_engagement_insights(insight)
        
        return insight

    async def _identify_peak_engagement_times(self, metrics: List[AttentionMetrics]) -> List[str]:
        """Identify times of day with highest engagement"""
        hourly_attention = {}
        
        for metric in metrics:
            hour = metric.timestamp.hour
            if hour not in hourly_attention:
                hourly_attention[hour] = []
            hourly_attention[hour].append(metric.attention_score)
        
        # Calculate average attention by hour
        hourly_averages = {
            hour: np.mean(scores) for hour, scores in hourly_attention.items()
        }
        
        # Find peak hours (top 3)
        peak_hours = sorted(hourly_averages.items(), key=lambda x: x[1], reverse=True)[:3]
        
        peak_times = []
        for hour, avg_score in peak_hours:
            time_range = f"{hour:02d}:00-{(hour+1)%24:02d}:00"
            peak_times.append(time_range)
        
        return peak_times

    async def _analyze_attention_patterns(self, metrics: List[AttentionMetrics]) -> Dict[str, Any]:
        """Analyze patterns in attention data"""
        if not metrics:
            return {}
        
        patterns = {}
        
        # Attention score distribution
        scores = [m.attention_score for m in metrics]
        patterns['score_distribution'] = {
            'mean': np.mean(scores),
            'std': np.std(scores),
            'min': np.min(scores),
            'max': np.max(scores)
        }
        
        # Engagement level frequency
        engagement_counts = {}
        for metric in metrics:
            level = metric.engagement_level.value
            engagement_counts[level] = engagement_counts.get(level, 0) + 1
        
        patterns['engagement_distribution'] = engagement_counts
        
        # Attention state frequency
        state_counts = {}
        for metric in metrics:
            state = metric.attention_state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        patterns['attention_state_distribution'] = state_counts
        
        # Focus duration patterns
        focus_durations = [m.focus_duration for m in metrics]
        patterns['focus_patterns'] = {
            'avg_focus_duration': np.mean(focus_durations),
            'max_focus_duration': np.max(focus_durations),
            'focus_variability': np.std(focus_durations)
        }
        
        return patterns

    async def _identify_distraction_triggers(self, student_id: str, 
                                           start_date: datetime, end_date: datetime) -> List[str]:
        """Identify common distraction triggers"""
        # Get interaction events during low attention periods
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get sessions with low attention
        cursor.execute('''
            SELECT session_id, avg(attention_score) as avg_attention
            FROM attention_metrics
            WHERE student_id = ? AND timestamp BETWEEN ? AND ?
            GROUP BY session_id
            HAVING avg_attention < 0.4
        ''', (student_id, start_date, end_date))
        
        low_attention_sessions = [row[0] for row in cursor.fetchall()]
        
        if not low_attention_sessions:
            conn.close()
            return []
        
        # Get interactions from these sessions
        session_placeholders = ','.join('?' * len(low_attention_sessions))
        cursor.execute(f'''
            SELECT interaction_type, COUNT(*) as count
            FROM interaction_events
            WHERE session_id IN ({session_placeholders})
            GROUP BY interaction_type
            ORDER BY count DESC
        ''', low_attention_sessions)
        
        interaction_counts = cursor.fetchall()
        conn.close()
        
        # Common distraction patterns
        distraction_triggers = []
        for interaction_type, count in interaction_counts[:5]:  # Top 5
            if interaction_type in ['tab_switch', 'window_blur']:
                distraction_triggers.append(f"Frequent {interaction_type.replace('_', ' ')}")
        
        return distraction_triggers

    async def _calculate_optimal_session_length(self, student_id: str,
                                              start_date: datetime, end_date: datetime) -> float:
        """Calculate optimal learning session length for student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get completed sessions with their durations and average attention
        cursor.execute('''
            SELECT ls.total_duration, avg(am.attention_score) as avg_attention
            FROM learning_sessions ls
            JOIN attention_metrics am ON ls.session_id = am.session_id
            WHERE ls.student_id = ? AND ls.start_time BETWEEN ? AND ?
            AND ls.completion_status = 'completed'
            GROUP BY ls.session_id
            HAVING COUNT(am.attention_score) > 3
        ''', (student_id, start_date, end_date))
        
        session_data = cursor.fetchall()
        conn.close()
        
        if not session_data:
            return 1800.0  # Default 30 minutes
        
        # Find duration with highest average attention
        duration_attention = [(duration, attention) for duration, attention in session_data]
        
        if duration_attention:
            # Weight by attention score
            weighted_durations = []
            for duration, attention in duration_attention:
                if attention > 0.5:  # Only consider sessions with reasonable attention
                    weighted_durations.append(duration)
            
            if weighted_durations:
                return np.mean(weighted_durations)
        
        return 1800.0  # Default 30 minutes

    async def _generate_engagement_recommendations(self, avg_attention: float,
                                                 patterns: Dict[str, Any],
                                                 distractions: List[str],
                                                 optimal_length: float) -> List[str]:
        """Generate personalized engagement recommendations"""
        recommendations = []
        
        # Attention-based recommendations
        if avg_attention < 0.4:
            recommendations.append("Consider shorter, more focused study sessions")
            recommendations.append("Try active learning techniques to increase engagement")
        elif avg_attention < 0.6:
            recommendations.append("Work on maintaining consistent attention throughout sessions")
            recommendations.append("Take regular breaks to prevent attention fatigue")
        else:
            recommendations.append("Excellent attention levels - consider tackling more challenging content")
        
        # Session length recommendations
        optimal_minutes = optimal_length / 60
        if optimal_minutes < 20:
            recommendations.append("Short focused sessions work best - aim for 15-20 minute blocks")
        elif optimal_minutes > 60:
            recommendations.append("You can maintain attention for longer sessions - consider 45-60 minute blocks")
        else:
            recommendations.append(f"Optimal session length appears to be {optimal_minutes:.0f} minutes")
        
        # Distraction-based recommendations
        if "tab_switch" in ' '.join(distractions).lower():
            recommendations.append("Minimize browser tabs and distracting websites during study time")
        
        if "window_blur" in ' '.join(distractions).lower():
            recommendations.append("Use focus mode or study in a distraction-free environment")
        
        # Pattern-based recommendations
        if patterns.get('focus_patterns', {}).get('focus_variability', 0) > 100:
            recommendations.append("Work on developing more consistent focus patterns")
        
        return recommendations[:5]  # Top 5 recommendations

    async def _calculate_active_duration(self, session_id: str) -> float:
        """Calculate total active duration (time with interactions)"""
        if session_id not in self.interaction_buffers:
            return 0.0
        
        interactions = list(self.interaction_buffers[session_id])
        if not interactions:
            return 0.0
        
        # Calculate periods of activity (interactions within 5 minutes of each other)
        active_periods = []
        current_start = interactions[0].timestamp
        current_end = interactions[0].timestamp
        
        for i in range(1, len(interactions)):
            time_gap = (interactions[i].timestamp - current_end).total_seconds()
            
            if time_gap <= 300:  # 5 minutes gap threshold
                current_end = interactions[i].timestamp
            else:
                # End current period, start new one
                active_periods.append((current_start, current_end))
                current_start = interactions[i].timestamp
                current_end = interactions[i].timestamp
        
        # Add final period
        active_periods.append((current_start, current_end))
        
        # Sum all active periods
        total_active = sum((end - start).total_seconds() for start, end in active_periods)
        return total_active

    async def _generate_session_summary(self, session: LearningSession):
        """Generate summary analytics for completed session"""
        # This would generate detailed session analytics
        logger.info(f"Generated summary for session {session.session_id}")

    async def _get_attention_metrics_for_period(self, student_id: str,
                                              start_date: datetime, 
                                              end_date: datetime) -> List[AttentionMetrics]:
        """Get attention metrics for a specific period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT student_id, session_id, timestamp, attention_score, engagement_level,
                   attention_state, focus_duration, interaction_frequency,
                   content_consumption_rate, multitasking_indicator,
                   fatigue_indicator, confusion_indicator
            FROM attention_metrics
            WHERE student_id = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        ''', (student_id, start_date, end_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        metrics = []
        for row in rows:
            metric = AttentionMetrics(
                student_id=row[0],
                session_id=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                attention_score=row[3],
                engagement_level=EngagementLevel(row[4]),
                attention_state=AttentionState(row[5]),
                focus_duration=row[6],
                interaction_frequency=row[7],
                content_consumption_rate=row[8],
                multitasking_indicator=row[9],
                fatigue_indicator=row[10],
                confusion_indicator=row[11]
            )
            metrics.append(metric)
        
        return metrics

    async def _save_session(self, session: LearningSession):
        """Save learning session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO learning_sessions
            (session_id, student_id, content_type, start_time, end_time,
             total_duration, active_duration, interactions, attention_metrics,
             breaks_taken, completion_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session.session_id, session.student_id, session.content_type,
              session.start_time, session.end_time, session.total_duration,
              session.active_duration, json.dumps(session.interactions),
              json.dumps(session.attention_metrics), json.dumps(session.breaks_taken),
              session.completion_status))
        
        conn.commit()
        conn.close()

    async def _save_interaction_event(self, event: InteractionEvent):
        """Save interaction event to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        coordinates_json = json.dumps(event.coordinates) if event.coordinates else None
        
        cursor.execute('''
            INSERT INTO interaction_events
            (event_id, student_id, session_id, interaction_type, timestamp,
             duration, coordinates, content_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (event.event_id, event.student_id, event.session_id,
              event.interaction_type.value, event.timestamp, event.duration,
              coordinates_json, event.content_id, json.dumps(event.metadata)))
        
        conn.commit()
        conn.close()

    async def _save_attention_metrics(self, metrics: AttentionMetrics):
        """Save attention metrics to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO attention_metrics
            (student_id, session_id, timestamp, attention_score, engagement_level,
             attention_state, focus_duration, interaction_frequency,
             content_consumption_rate, multitasking_indicator,
             fatigue_indicator, confusion_indicator)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (metrics.student_id, metrics.session_id, metrics.timestamp,
              metrics.attention_score, metrics.engagement_level.value,
              metrics.attention_state.value, metrics.focus_duration,
              metrics.interaction_frequency, metrics.content_consumption_rate,
              metrics.multitasking_indicator, metrics.fatigue_indicator,
              metrics.confusion_indicator))
        
        conn.commit()
        conn.close()

    async def _save_engagement_alert(self, alert: EngagementAlert):
        """Save engagement alert to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO engagement_alerts
            (alert_id, student_id, session_id, alert_type, severity, message,
             timestamp, intervention_triggered, resolved, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (alert.alert_id, alert.student_id, alert.session_id,
              alert.alert_type.value, alert.severity, alert.message,
              alert.timestamp, alert.intervention_triggered, alert.resolved,
              json.dumps(alert.metadata)))
        
        conn.commit()
        conn.close()

    async def _save_engagement_insights(self, insights: EngagementInsight):
        """Save engagement insights to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO engagement_insights
            (student_id, analysis_start_date, analysis_end_date, avg_attention_score,
             peak_engagement_times, attention_patterns, distraction_triggers,
             optimal_session_length, recommendations, generated_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (insights.student_id, insights.analysis_period[0], insights.analysis_period[1],
              insights.avg_attention_score, json.dumps(insights.peak_engagement_times),
              json.dumps(insights.attention_patterns), json.dumps(insights.distraction_triggers),
              insights.optimal_session_length, json.dumps(insights.recommendations),
              datetime.now()))
        
        conn.commit()
        conn.close()

async def demo_engagement_tracking():
    """Demonstrate attention tracking and engagement monitoring"""
    tracker = EngagementTracker()
    
    print("=== Attention Tracking and Engagement Monitoring Demo ===")
    
    # Start learning session
    session_id = await tracker.start_learning_session("student_jordan", "interactive_lesson")
    print(f"Started learning session: {session_id}")
    
    # Simulate various interactions over time
    interactions = [
        (InteractionType.CONTENT_VIEW, None, "lesson_intro"),
        (InteractionType.SCROLL, None, "lesson_intro"),
        (InteractionType.MOUSE_CLICK, (500, 300), "quiz_button"),
        (InteractionType.QUIZ_ATTEMPT, None, "quiz_1"),
        (InteractionType.KEYBOARD_INPUT, None, "answer_field"),
        (InteractionType.TAB_SWITCH, None, None),  # Distraction
        (InteractionType.WINDOW_FOCUS, None, None),  # Return to focus
        (InteractionType.SCROLL, None, "lesson_content"),
        (InteractionType.PAGE_NAVIGATION, None, "next_section"),
        (InteractionType.VIDEO_PLAY, None, "explanation_video"),
    ]
    
    print(f"\nSimulating {len(interactions)} interactions...")
    
    for i, (interaction_type, coords, content_id) in enumerate(interactions):
        # Add small delay between interactions
        await asyncio.sleep(0.1)
        
        event = await tracker.record_interaction(
            session_id=session_id,
            interaction_type=interaction_type,
            coordinates=coords,
            content_id=content_id
        )
        
        print(f"Recorded: {interaction_type.value}" + 
              (f" on {content_id}" if content_id else ""))
    
    # Wait a bit to let monitoring run
    await asyncio.sleep(2)
    
    # End session
    completed_session = await tracker.end_learning_session(session_id)
    
    print(f"\n=== SESSION SUMMARY ===")
    print(f"Total Duration: {completed_session.total_duration:.1f} seconds")
    print(f"Active Duration: {completed_session.active_duration:.1f} seconds")
    print(f"Activity Rate: {completed_session.active_duration/completed_session.total_duration:.1%}")
    print(f"Total Interactions: {len(completed_session.interactions)}")
    print(f"Status: {completed_session.completion_status}")
    
    # Generate engagement insights
    insights = await tracker.generate_engagement_insights("student_jordan", days_back=1)
    
    print(f"\n=== ENGAGEMENT INSIGHTS ===")
    print(f"Average Attention Score: {insights.avg_attention_score:.1%}")
    print(f"Optimal Session Length: {insights.optimal_session_length/60:.1f} minutes")
    
    if insights.peak_engagement_times:
        print(f"Peak Engagement Times: {', '.join(insights.peak_engagement_times)}")
    
    if insights.distraction_triggers:
        print(f"Distraction Triggers: {', '.join(insights.distraction_triggers)}")
    
    print(f"\nRecommendations:")
    for rec in insights.recommendations:
        print(f"  • {rec}")
    
    # Show attention patterns
    if insights.attention_patterns:
        patterns = insights.attention_patterns
        print(f"\n=== ATTENTION PATTERNS ===")
        
        if 'score_distribution' in patterns:
            dist = patterns['score_distribution']
            print(f"Attention Score: {dist['mean']:.2f} ± {dist['std']:.2f}")
            print(f"Range: {dist['min']:.2f} - {dist['max']:.2f}")
        
        if 'focus_patterns' in patterns:
            focus = patterns['focus_patterns']
            print(f"Average Focus Duration: {focus['avg_focus_duration']:.1f}s")
            print(f"Maximum Focus Duration: {focus['max_focus_duration']:.1f}s")

if __name__ == "__main__":
    asyncio.run(demo_engagement_tracking())