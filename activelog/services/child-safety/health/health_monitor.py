"""
Health Monitoring System for Child Safety

This module provides comprehensive health monitoring with focus on digital wellness
for children, including eye strain prevention, posture monitoring, learning fatigue
detection, and proactive health interventions.
"""

import asyncio
import asyncpg
import json
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import math

class HealthAlertLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

class HealthMetricType(Enum):
    EYE_STRAIN = "eye_strain"
    POSTURE = "posture"
    FATIGUE = "fatigue"
    HYDRATION = "hydration"
    PHYSICAL_ACTIVITY = "physical_activity"
    SLEEP_SCHEDULE = "sleep_schedule"

class InterventionType(Enum):
    REMINDER = "reminder"
    BREAK = "break"
    EXERCISE = "exercise"
    HYDRATION = "hydration"
    POSTURE_CORRECTION = "posture_correction"
    SLEEP_GUIDANCE = "sleep_guidance"

@dataclass
class HealthAlert:
    alert_id: str
    user_id: str
    metric_type: HealthMetricType
    alert_level: HealthAlertLevel
    timestamp: datetime
    message: str
    intervention_suggestions: List[str]
    parent_notification: bool
    requires_immediate_action: bool
    acknowledged: bool

@dataclass
class EyeStrainMetrics:
    user_id: str
    timestamp: datetime
    blink_rate_per_minute: float
    screen_distance_cm: Optional[float]
    brightness_level: float
    consecutive_screen_minutes: int
    eye_movement_patterns: Dict[str, int]
    strain_score: float
    symptoms_reported: List[str]

@dataclass
class PostureMetrics:
    user_id: str
    timestamp: datetime
    head_position: Dict[str, float]
    shoulder_alignment: Dict[str, float]
    sitting_duration_minutes: int
    posture_score: float
    slouch_incidents: int
    movement_frequency: float
    ergonomic_violations: List[str]

@dataclass
class FatigueMetrics:
    user_id: str
    timestamp: datetime
    cognitive_load_score: float
    task_switching_frequency: int
    error_rate: float
    response_time_ms: float
    concentration_periods: List[Dict[str, Any]]
    fatigue_indicators: List[str]
    learning_effectiveness: float

@dataclass
class HealthIntervention:
    intervention_id: str
    user_id: str
    intervention_type: InterventionType
    trigger_metrics: List[HealthMetricType]
    instructions: List[str]
    duration_minutes: int
    visual_demonstrations: List[str]
    success_criteria: Dict[str, Any]
    completed: bool
    effectiveness_rating: Optional[float]

class HealthMonitor:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.active_monitors: Dict[str, Dict] = {}
        self.alert_thresholds = self._initialize_thresholds()
        self.intervention_templates = self._initialize_interventions()
        self.logger = logging.getLogger(__name__)
        
        # Health monitoring intervals (in minutes)
        self.monitoring_intervals = {
            HealthMetricType.EYE_STRAIN: 5,
            HealthMetricType.POSTURE: 3,
            HealthMetricType.FATIGUE: 10,
            HealthMetricType.HYDRATION: 30,
            HealthMetricType.PHYSICAL_ACTIVITY: 15,
            HealthMetricType.SLEEP_SCHEDULE: 60
        }

    def _initialize_thresholds(self) -> Dict[str, Dict]:
        """Initialize health alert thresholds by age group"""
        return {
            "eye_strain": {
                (3, 6): {"moderate": 15, "high": 25, "critical": 35},
                (7, 12): {"moderate": 20, "high": 30, "critical": 45},
                (13, 17): {"moderate": 25, "high": 40, "critical": 60}
            },
            "posture": {
                (3, 6): {"moderate": 10, "high": 15, "critical": 20},
                (7, 12): {"moderate": 15, "high": 25, "critical": 35},
                (13, 17): {"moderate": 20, "high": 30, "critical": 45}
            },
            "fatigue": {
                (3, 6): {"moderate": 20, "high": 30, "critical": 40},
                (7, 12): {"moderate": 30, "high": 45, "critical": 60},
                (13, 17): {"moderate": 45, "high": 75, "critical": 90}
            }
        }

    def _initialize_interventions(self) -> Dict[InterventionType, Dict]:
        """Initialize intervention templates"""
        return {
            InterventionType.REMINDER: {
                "eye_strain": [
                    "Look at something 20 feet away for 20 seconds",
                    "Blink slowly 10 times",
                    "Close your eyes for 30 seconds"
                ],
                "posture": [
                    "Sit up straight with feet flat on the floor",
                    "Adjust your screen to eye level",
                    "Roll your shoulders back and down"
                ],
                "hydration": [
                    "Take a sip of water",
                    "Remember to stay hydrated",
                    "Get a fresh glass of water"
                ]
            },
            InterventionType.EXERCISE: {
                "general": [
                    "Stand up and stretch your arms above your head",
                    "Do 5 gentle neck rolls",
                    "March in place for 30 seconds",
                    "Do 10 shoulder shrugs"
                ],
                "eye_strain": [
                    "Focus on distant objects",
                    "Practice eye tracking exercises",
                    "Do figure-8 eye movements"
                ],
                "posture": [
                    "Do wall push-ups (10 reps)",
                    "Practice cat-cow stretches",
                    "Do doorway chest stretches"
                ]
            },
            InterventionType.BREAK: {
                "short": [
                    "Take a 5-minute break from screens",
                    "Walk around your room or house",
                    "Get some fresh air"
                ],
                "long": [
                    "Take a 15-minute break from all screens",
                    "Go outside if possible",
                    "Do a non-screen activity you enjoy"
                ]
            }
        }

    async def initialize_database(self):
        """Initialize database tables for health monitoring"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS health_alerts (
                    alert_id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    metric_type VARCHAR NOT NULL,
                    alert_level VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    message TEXT NOT NULL,
                    intervention_suggestions JSONB NOT NULL,
                    parent_notification BOOLEAN NOT NULL,
                    requires_immediate_action BOOLEAN NOT NULL,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS eye_strain_metrics (
                    user_id VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    blink_rate_per_minute FLOAT NOT NULL,
                    screen_distance_cm FLOAT,
                    brightness_level FLOAT NOT NULL,
                    consecutive_screen_minutes INTEGER NOT NULL,
                    eye_movement_patterns JSONB NOT NULL,
                    strain_score FLOAT NOT NULL,
                    symptoms_reported JSONB NOT NULL DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, timestamp)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS posture_metrics (
                    user_id VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    head_position JSONB NOT NULL,
                    shoulder_alignment JSONB NOT NULL,
                    sitting_duration_minutes INTEGER NOT NULL,
                    posture_score FLOAT NOT NULL,
                    slouch_incidents INTEGER NOT NULL DEFAULT 0,
                    movement_frequency FLOAT NOT NULL,
                    ergonomic_violations JSONB NOT NULL DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, timestamp)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fatigue_metrics (
                    user_id VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    cognitive_load_score FLOAT NOT NULL,
                    task_switching_frequency INTEGER NOT NULL,
                    error_rate FLOAT NOT NULL,
                    response_time_ms FLOAT NOT NULL,
                    concentration_periods JSONB NOT NULL DEFAULT '[]',
                    fatigue_indicators JSONB NOT NULL DEFAULT '[]',
                    learning_effectiveness FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, timestamp)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS health_interventions (
                    intervention_id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    intervention_type VARCHAR NOT NULL,
                    trigger_metrics JSONB NOT NULL,
                    instructions JSONB NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    visual_demonstrations JSONB NOT NULL DEFAULT '[]',
                    success_criteria JSONB NOT NULL DEFAULT '{}',
                    completed BOOLEAN DEFAULT FALSE,
                    effectiveness_rating FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)

    async def start_monitoring(self, user_id: str, age: int) -> bool:
        """Start comprehensive health monitoring for a user"""
        
        if user_id in self.active_monitors:
            return False
        
        monitor_config = {
            "user_id": user_id,
            "age": age,
            "start_time": datetime.now(),
            "active_metrics": [metric.value for metric in HealthMetricType],
            "last_checks": {metric.value: datetime.now() for metric in HealthMetricType},
            "baseline_established": False,
            "cumulative_scores": {
                "eye_strain": 0.0,
                "posture": 0.0,
                "fatigue": 0.0
            }
        }
        
        self.active_monitors[user_id] = monitor_config
        
        # Start monitoring tasks
        asyncio.create_task(self._monitoring_loop(user_id))
        
        self.logger.info(f"Started health monitoring for user {user_id}")
        return True

    async def stop_monitoring(self, user_id: str) -> bool:
        """Stop health monitoring for a user"""
        
        if user_id not in self.active_monitors:
            return False
        
        del self.active_monitors[user_id]
        self.logger.info(f"Stopped health monitoring for user {user_id}")
        return True

    async def _monitoring_loop(self, user_id: str):
        """Main monitoring loop for a user"""
        
        while user_id in self.active_monitors:
            try:
                monitor_config = self.active_monitors[user_id]
                now = datetime.now()
                
                # Check each metric type based on its interval
                for metric_type in HealthMetricType:
                    interval = self.monitoring_intervals[metric_type]
                    last_check = monitor_config["last_checks"][metric_type.value]
                    
                    if (now - last_check).total_seconds() >= interval * 60:
                        await self._check_health_metric(user_id, metric_type)
                        monitor_config["last_checks"][metric_type.value] = now
                
                # Sleep before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop for {user_id}: {e}")
                await asyncio.sleep(60)

    async def _check_health_metric(self, user_id: str, metric_type: HealthMetricType):
        """Check a specific health metric for a user"""
        
        if metric_type == HealthMetricType.EYE_STRAIN:
            await self._check_eye_strain(user_id)
        elif metric_type == HealthMetricType.POSTURE:
            await self._check_posture(user_id)
        elif metric_type == HealthMetricType.FATIGUE:
            await self._check_fatigue(user_id)
        elif metric_type == HealthMetricType.HYDRATION:
            await self._check_hydration(user_id)
        elif metric_type == HealthMetricType.PHYSICAL_ACTIVITY:
            await self._check_physical_activity(user_id)

    async def _check_eye_strain(self, user_id: str):
        """Monitor and assess eye strain indicators"""
        
        # In a real implementation, this would integrate with camera/sensors
        # For now, we simulate realistic metrics
        now = datetime.now()
        
        # Simulate eye strain metrics (would be actual sensor data)
        consecutive_minutes = await self._get_consecutive_screen_time(user_id)
        
        # Calculate strain score based on multiple factors
        base_strain = min(consecutive_minutes / 30.0, 1.0) * 50  # Base strain from screen time
        brightness_factor = 0.8  # Simulated brightness level
        distance_factor = 1.2 if consecutive_minutes > 20 else 1.0  # Simulated poor distance
        blink_rate = max(5, 15 - (consecutive_minutes * 0.2))  # Reduced blinking over time
        
        strain_score = base_strain * brightness_factor * distance_factor
        if blink_rate < 10:
            strain_score += 15
        
        # Create metrics record
        eye_metrics = EyeStrainMetrics(
            user_id=user_id,
            timestamp=now,
            blink_rate_per_minute=blink_rate,
            screen_distance_cm=50.0 if consecutive_minutes < 30 else 35.0,
            brightness_level=brightness_factor,
            consecutive_screen_minutes=consecutive_minutes,
            eye_movement_patterns={"fixations": 45, "saccades": 120, "tracking": 30},
            strain_score=strain_score,
            symptoms_reported=[]
        )
        
        # Store metrics
        await self._store_eye_strain_metrics(eye_metrics)
        
        # Check for alerts
        await self._evaluate_eye_strain_alerts(user_id, eye_metrics)

    async def _check_posture(self, user_id: str):
        """Monitor and assess posture indicators"""
        
        now = datetime.now()
        sitting_duration = await self._get_sitting_duration(user_id)
        
        # Simulate posture metrics
        base_posture_score = max(0, 100 - (sitting_duration * 2))  # Score decreases with sitting time
        
        # Simulate posture degradation over time
        if sitting_duration > 30:
            slouch_incidents = min(sitting_duration // 10, 8)
            head_forward = min(sitting_duration * 0.5, 15)  # Forward head posture
            shoulder_roll = min(sitting_duration * 0.3, 10)  # Shoulder rolling
        else:
            slouch_incidents = 0
            head_forward = 0
            shoulder_roll = 0
        
        posture_score = base_posture_score - (slouch_incidents * 5) - head_forward - shoulder_roll
        posture_score = max(0, posture_score)
        
        posture_metrics = PostureMetrics(
            user_id=user_id,
            timestamp=now,
            head_position={"forward_degrees": head_forward, "tilt_degrees": 2},
            shoulder_alignment={"roll_forward_degrees": shoulder_roll, "height_difference": 1},
            sitting_duration_minutes=sitting_duration,
            posture_score=posture_score,
            slouch_incidents=slouch_incidents,
            movement_frequency=max(0.1, 1.0 - (sitting_duration * 0.02)),
            ergonomic_violations=["head_forward", "shoulders_rolled"] if sitting_duration > 20 else []
        )
        
        await self._store_posture_metrics(posture_metrics)
        await self._evaluate_posture_alerts(user_id, posture_metrics)

    async def _check_fatigue(self, user_id: str):
        """Monitor and assess learning fatigue indicators"""
        
        now = datetime.now()
        
        # Get recent activity data to assess fatigue
        session_duration = await self._get_current_session_duration(user_id)
        
        # Simulate cognitive load based on session length and activity
        base_load = min(session_duration / 60.0, 1.0) * 70  # Increase with session time
        
        # Simulate task switching (higher = more fatigue)
        task_switches = max(1, session_duration // 5)  # Switch every 5 minutes
        
        # Simulate error rate increase with fatigue
        error_rate = min(0.15, 0.02 + (session_duration * 0.001))
        
        # Simulate response time increase
        response_time = 500 + (session_duration * 2)  # Slower responses over time
        
        # Calculate overall fatigue score
        fatigue_indicators = []
        if session_duration > 45:
            fatigue_indicators.extend(["prolonged_session", "attention_decline"])
        if error_rate > 0.08:
            fatigue_indicators.append("increased_errors")
        if response_time > 800:
            fatigue_indicators.append("slow_responses")
        
        learning_effectiveness = max(0.3, 1.0 - (len(fatigue_indicators) * 0.2))
        
        fatigue_metrics = FatigueMetrics(
            user_id=user_id,
            timestamp=now,
            cognitive_load_score=base_load,
            task_switching_frequency=task_switches,
            error_rate=error_rate,
            response_time_ms=response_time,
            concentration_periods=[
                {"start": 0, "end": min(20, session_duration), "focus_score": 0.9},
                {"start": 20, "end": min(40, session_duration), "focus_score": 0.7},
                {"start": 40, "end": session_duration, "focus_score": 0.5}
            ] if session_duration > 20 else [],
            fatigue_indicators=fatigue_indicators,
            learning_effectiveness=learning_effectiveness
        )
        
        await self._store_fatigue_metrics(fatigue_metrics)
        await self._evaluate_fatigue_alerts(user_id, fatigue_metrics)

    async def _check_hydration(self, user_id: str):
        """Check and remind about hydration"""
        
        # Simple hydration reminder based on time since last reminder
        last_hydration_reminder = await self._get_last_hydration_reminder(user_id)
        now = datetime.now()
        
        if not last_hydration_reminder or (now - last_hydration_reminder).total_seconds() > 1800:  # 30 minutes
            intervention = await self._create_intervention(
                user_id=user_id,
                intervention_type=InterventionType.HYDRATION,
                trigger_metrics=[HealthMetricType.HYDRATION],
                duration_minutes=1
            )
            
            await self._trigger_intervention(intervention)

    async def _check_physical_activity(self, user_id: str):
        """Check and encourage physical activity"""
        
        sitting_time = await self._get_sitting_duration(user_id)
        
        if sitting_time > 45:  # More than 45 minutes sitting
            intervention = await self._create_intervention(
                user_id=user_id,
                intervention_type=InterventionType.EXERCISE,
                trigger_metrics=[HealthMetricType.PHYSICAL_ACTIVITY],
                duration_minutes=5
            )
            
            await self._trigger_intervention(intervention)

    async def _evaluate_eye_strain_alerts(self, user_id: str, metrics: EyeStrainMetrics):
        """Evaluate eye strain metrics and trigger alerts if needed"""
        
        age = self.active_monitors[user_id]["age"]
        thresholds = self._get_thresholds_for_age("eye_strain", age)
        
        alert_level = None
        if metrics.strain_score >= thresholds["critical"]:
            alert_level = HealthAlertLevel.CRITICAL
        elif metrics.strain_score >= thresholds["high"]:
            alert_level = HealthAlertLevel.HIGH
        elif metrics.strain_score >= thresholds["moderate"]:
            alert_level = HealthAlertLevel.MODERATE
        
        if alert_level:
            await self._create_health_alert(
                user_id=user_id,
                metric_type=HealthMetricType.EYE_STRAIN,
                alert_level=alert_level,
                message=f"Eye strain detected (score: {metrics.strain_score:.1f}). Time for a break!",
                intervention_suggestions=self.intervention_templates[InterventionType.REMINDER]["eye_strain"],
                requires_immediate_action=alert_level in [HealthAlertLevel.HIGH, HealthAlertLevel.CRITICAL]
            )

    async def _evaluate_posture_alerts(self, user_id: str, metrics: PostureMetrics):
        """Evaluate posture metrics and trigger alerts if needed"""
        
        age = self.active_monitors[user_id]["age"]
        thresholds = self._get_thresholds_for_age("posture", age)
        
        # Invert score for threshold comparison (lower posture score = higher alert level)
        inverted_score = 100 - metrics.posture_score
        
        alert_level = None
        if inverted_score >= thresholds["critical"]:
            alert_level = HealthAlertLevel.CRITICAL
        elif inverted_score >= thresholds["high"]:
            alert_level = HealthAlertLevel.HIGH
        elif inverted_score >= thresholds["moderate"]:
            alert_level = HealthAlertLevel.MODERATE
        
        if alert_level:
            await self._create_health_alert(
                user_id=user_id,
                metric_type=HealthMetricType.POSTURE,
                alert_level=alert_level,
                message=f"Poor posture detected. Please adjust your position!",
                intervention_suggestions=self.intervention_templates[InterventionType.REMINDER]["posture"],
                requires_immediate_action=len(metrics.ergonomic_violations) > 2
            )

    async def _evaluate_fatigue_alerts(self, user_id: str, metrics: FatigueMetrics):
        """Evaluate fatigue metrics and trigger alerts if needed"""
        
        age = self.active_monitors[user_id]["age"]
        thresholds = self._get_thresholds_for_age("fatigue", age)
        
        alert_level = None
        if metrics.cognitive_load_score >= thresholds["critical"]:
            alert_level = HealthAlertLevel.CRITICAL
        elif metrics.cognitive_load_score >= thresholds["high"]:
            alert_level = HealthAlertLevel.HIGH
        elif metrics.cognitive_load_score >= thresholds["moderate"]:
            alert_level = HealthAlertLevel.MODERATE
        
        if alert_level or len(metrics.fatigue_indicators) >= 3:
            alert_level = alert_level or HealthAlertLevel.HIGH
            await self._create_health_alert(
                user_id=user_id,
                metric_type=HealthMetricType.FATIGUE,
                alert_level=alert_level,
                message=f"Learning fatigue detected. Consider taking a longer break!",
                intervention_suggestions=self.intervention_templates[InterventionType.BREAK]["long"],
                requires_immediate_action=alert_level == HealthAlertLevel.CRITICAL
            )

    async def _create_health_alert(self, user_id: str, metric_type: HealthMetricType,
                                 alert_level: HealthAlertLevel, message: str,
                                 intervention_suggestions: List[str],
                                 requires_immediate_action: bool = False):
        """Create and store a health alert"""
        
        alert_id = f"alert_{user_id}_{metric_type.value}_{int(datetime.now().timestamp())}"
        
        alert = HealthAlert(
            alert_id=alert_id,
            user_id=user_id,
            metric_type=metric_type,
            alert_level=alert_level,
            timestamp=datetime.now(),
            message=message,
            intervention_suggestions=intervention_suggestions,
            parent_notification=alert_level in [HealthAlertLevel.HIGH, HealthAlertLevel.CRITICAL],
            requires_immediate_action=requires_immediate_action,
            acknowledged=False
        )
        
        # Store alert
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO health_alerts 
                (alert_id, user_id, metric_type, alert_level, timestamp, message,
                 intervention_suggestions, parent_notification, requires_immediate_action)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, alert_id, user_id, metric_type.value, alert_level.value,
                alert.timestamp, message, json.dumps(intervention_suggestions),
                alert.parent_notification, requires_immediate_action
            )
        
        # Create automatic intervention for high/critical alerts
        if alert_level in [HealthAlertLevel.HIGH, HealthAlertLevel.CRITICAL]:
            intervention_type = InterventionType.BREAK if metric_type == HealthMetricType.FATIGUE else InterventionType.REMINDER
            intervention = await self._create_intervention(
                user_id=user_id,
                intervention_type=intervention_type,
                trigger_metrics=[metric_type],
                duration_minutes=5 if intervention_type == InterventionType.REMINDER else 15
            )
            await self._trigger_intervention(intervention)
        
        self.logger.info(f"Created health alert: {alert_id} for {user_id}")

    async def _create_intervention(self, user_id: str, intervention_type: InterventionType,
                                 trigger_metrics: List[HealthMetricType],
                                 duration_minutes: int) -> HealthIntervention:
        """Create a health intervention"""
        
        intervention_id = f"intervention_{user_id}_{intervention_type.value}_{int(datetime.now().timestamp())}"
        
        # Get appropriate instructions
        if intervention_type == InterventionType.HYDRATION:
            instructions = self.intervention_templates[InterventionType.REMINDER]["hydration"]
        elif intervention_type == InterventionType.EXERCISE:
            instructions = self.intervention_templates[InterventionType.EXERCISE]["general"]
        elif intervention_type == InterventionType.BREAK:
            instructions = self.intervention_templates[InterventionType.BREAK]["short" if duration_minutes <= 10 else "long"]
        else:
            # Choose based on primary trigger metric
            primary_metric = trigger_metrics[0].value.replace("_", " ")
            instructions = self.intervention_templates[intervention_type].get(
                primary_metric, self.intervention_templates[intervention_type].get("general", ["Take a break"])
            )
        
        intervention = HealthIntervention(
            intervention_id=intervention_id,
            user_id=user_id,
            intervention_type=intervention_type,
            trigger_metrics=trigger_metrics,
            instructions=instructions,
            duration_minutes=duration_minutes,
            visual_demonstrations=[],
            success_criteria={"completion_required": True, "duration_met": True},
            completed=False,
            effectiveness_rating=None
        )
        
        return intervention

    async def _trigger_intervention(self, intervention: HealthIntervention):
        """Trigger and store a health intervention"""
        
        # Store intervention
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO health_interventions 
                (intervention_id, user_id, intervention_type, trigger_metrics,
                 instructions, duration_minutes, visual_demonstrations, success_criteria)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, intervention.intervention_id, intervention.user_id,
                intervention.intervention_type.value,
                json.dumps([m.value for m in intervention.trigger_metrics]),
                json.dumps(intervention.instructions),
                intervention.duration_minutes,
                json.dumps(intervention.visual_demonstrations),
                json.dumps(intervention.success_criteria)
            )
        
        self.logger.info(f"Triggered intervention: {intervention.intervention_id}")

    def _get_thresholds_for_age(self, metric_type: str, age: int) -> Dict[str, float]:
        """Get alert thresholds for a specific age"""
        
        thresholds_by_age = self.alert_thresholds[metric_type]
        
        for age_range, thresholds in thresholds_by_age.items():
            if age_range[0] <= age <= age_range[1]:
                return thresholds
        
        # Default to oldest age group if outside ranges
        return thresholds_by_age[(13, 17)]

    async def _get_consecutive_screen_time(self, user_id: str) -> int:
        """Get consecutive screen time in minutes"""
        # Simulate consecutive screen time (would integrate with screen time manager)
        return min(120, int(datetime.now().timestamp()) % 90)

    async def _get_sitting_duration(self, user_id: str) -> int:
        """Get current sitting duration in minutes"""
        # Simulate sitting duration (would integrate with activity sensors)
        return min(60, int(datetime.now().timestamp()) % 70)

    async def _get_current_session_duration(self, user_id: str) -> int:
        """Get current session duration in minutes"""
        # Simulate session duration (would integrate with session manager)
        return min(90, int(datetime.now().timestamp()) % 80)

    async def _get_last_hydration_reminder(self, user_id: str) -> Optional[datetime]:
        """Get timestamp of last hydration reminder"""
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT MAX(created_at) FROM health_interventions
                WHERE user_id = $1 AND intervention_type = $2
            """, user_id, InterventionType.HYDRATION.value)
        
        return result

    async def _store_eye_strain_metrics(self, metrics: EyeStrainMetrics):
        """Store eye strain metrics"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO eye_strain_metrics 
                (user_id, timestamp, blink_rate_per_minute, screen_distance_cm,
                 brightness_level, consecutive_screen_minutes, eye_movement_patterns,
                 strain_score, symptoms_reported)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (user_id, timestamp) DO UPDATE SET
                strain_score = EXCLUDED.strain_score,
                blink_rate_per_minute = EXCLUDED.blink_rate_per_minute
            """, metrics.user_id, metrics.timestamp, metrics.blink_rate_per_minute,
                metrics.screen_distance_cm, metrics.brightness_level,
                metrics.consecutive_screen_minutes,
                json.dumps(metrics.eye_movement_patterns),
                metrics.strain_score, json.dumps(metrics.symptoms_reported)
            )

    async def _store_posture_metrics(self, metrics: PostureMetrics):
        """Store posture metrics"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO posture_metrics 
                (user_id, timestamp, head_position, shoulder_alignment,
                 sitting_duration_minutes, posture_score, slouch_incidents,
                 movement_frequency, ergonomic_violations)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (user_id, timestamp) DO UPDATE SET
                posture_score = EXCLUDED.posture_score,
                slouch_incidents = EXCLUDED.slouch_incidents
            """, metrics.user_id, metrics.timestamp,
                json.dumps(metrics.head_position),
                json.dumps(metrics.shoulder_alignment),
                metrics.sitting_duration_minutes, metrics.posture_score,
                metrics.slouch_incidents, metrics.movement_frequency,
                json.dumps(metrics.ergonomic_violations)
            )

    async def _store_fatigue_metrics(self, metrics: FatigueMetrics):
        """Store fatigue metrics"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO fatigue_metrics 
                (user_id, timestamp, cognitive_load_score, task_switching_frequency,
                 error_rate, response_time_ms, concentration_periods,
                 fatigue_indicators, learning_effectiveness)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (user_id, timestamp) DO UPDATE SET
                cognitive_load_score = EXCLUDED.cognitive_load_score,
                learning_effectiveness = EXCLUDED.learning_effectiveness
            """, metrics.user_id, metrics.timestamp, metrics.cognitive_load_score,
                metrics.task_switching_frequency, metrics.error_rate,
                metrics.response_time_ms,
                json.dumps(metrics.concentration_periods),
                json.dumps(metrics.fatigue_indicators),
                metrics.learning_effectiveness
            )

    async def get_health_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Generate comprehensive health dashboard for a user"""
        
        async with self.db_pool.acquire() as conn:
            # Get recent alerts
            alerts = await conn.fetch("""
                SELECT * FROM health_alerts
                WHERE user_id = $1 AND timestamp > $2
                ORDER BY timestamp DESC LIMIT 10
            """, user_id, datetime.now() - timedelta(hours=24))
            
            # Get recent metrics summary
            eye_strain_avg = await conn.fetchval("""
                SELECT AVG(strain_score) FROM eye_strain_metrics
                WHERE user_id = $1 AND timestamp > $2
            """, user_id, datetime.now() - timedelta(hours=4))
            
            posture_avg = await conn.fetchval("""
                SELECT AVG(posture_score) FROM posture_metrics
                WHERE user_id = $1 AND timestamp > $2
            """, user_id, datetime.now() - timedelta(hours=4))
            
            fatigue_avg = await conn.fetchval("""
                SELECT AVG(cognitive_load_score) FROM fatigue_metrics
                WHERE user_id = $1 AND timestamp > $2
            """, user_id, datetime.now() - timedelta(hours=4))
            
            # Get intervention completion rate
            intervention_stats = await conn.fetchrow("""
                SELECT COUNT(*) as total, COUNT(completed_at) as completed
                FROM health_interventions
                WHERE user_id = $1 AND created_at > $2
            """, user_id, datetime.now() - timedelta(hours=24))
        
        # Calculate overall health score
        scores = [eye_strain_avg or 0, posture_avg or 100, 100 - (fatigue_avg or 0)]
        overall_score = sum(scores) / len(scores) if scores else 0
        
        # Determine health status
        if overall_score >= 80:
            status = "Excellent"
            status_color = "green"
        elif overall_score >= 65:
            status = "Good"
            status_color = "lightgreen"
        elif overall_score >= 50:
            status = "Fair"
            status_color = "yellow"
        else:
            status = "Needs Attention"
            status_color = "orange"
        
        dashboard = {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "overall_health_score": round(overall_score, 1),
            "health_status": status,
            "status_color": status_color,
            "metrics": {
                "eye_strain": {
                    "score": round(eye_strain_avg or 0, 1),
                    "status": "Good" if (eye_strain_avg or 0) < 25 else "Needs Attention"
                },
                "posture": {
                    "score": round(posture_avg or 100, 1),
                    "status": "Good" if (posture_avg or 100) > 70 else "Needs Attention"
                },
                "fatigue": {
                    "score": round(100 - (fatigue_avg or 0), 1),
                    "status": "Good" if (fatigue_avg or 0) < 40 else "Needs Attention"
                }
            },
            "recent_alerts": [dict(alert) for alert in alerts],
            "interventions": {
                "total": intervention_stats["total"] if intervention_stats else 0,
                "completed": intervention_stats["completed"] if intervention_stats else 0,
                "completion_rate": (intervention_stats["completed"] / max(1, intervention_stats["total"]) * 100) if intervention_stats else 0
            },
            "recommendations": self._generate_recommendations(overall_score, eye_strain_avg or 0, posture_avg or 100, fatigue_avg or 0)
        }
        
        return dashboard

    def _generate_recommendations(self, overall_score: float, eye_strain: float, 
                                posture: float, fatigue: float) -> List[str]:
        """Generate personalized health recommendations"""
        
        recommendations = []
        
        if eye_strain > 30:
            recommendations.append("Take more frequent eye breaks and adjust screen brightness")
        if posture < 60:
            recommendations.append("Focus on maintaining good posture and take movement breaks")
        if fatigue > 50:
            recommendations.append("Consider shorter learning sessions with longer breaks")
        if overall_score < 60:
            recommendations.append("Schedule more physical activity and outdoor time")
        
        if not recommendations:
            recommendations.append("Great job maintaining healthy digital habits!")
        
        return recommendations