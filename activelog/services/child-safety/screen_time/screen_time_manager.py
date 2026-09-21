"""
Screen Time Management System for Child Safety

This module provides comprehensive screen time tracking and management capabilities
with age-appropriate limits, educational content preferences, and health-focused
break reminders. Designed with child safety and well-being as primary concerns.
"""

import asyncio
import asyncpg
import json
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging

class ActivityType(Enum):
    EDUCATIONAL = "educational"
    CREATIVE = "creative"
    SOCIAL = "social"
    ENTERTAINMENT = "entertainment"
    GAMING = "gaming"
    PHYSICAL = "physical"

class DayType(Enum):
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"

class BreakType(Enum):
    MICRO = "micro"  # 30-60 seconds
    SHORT = "short"  # 5-10 minutes
    LONG = "long"    # 15-30 minutes
    MEAL = "meal"    # 30+ minutes

@dataclass
class ScreenTimeLimits:
    user_id: str
    age: int
    weekday_minutes: int
    weekend_minutes: int
    holiday_minutes: int
    educational_bonus_minutes: int
    bedtime_hour: int
    morning_start_hour: int
    break_intervals: Dict[str, int]
    activity_priorities: List[str]
    restricted_periods: List[Dict[str, Any]]

@dataclass
class ScreenTimeSession:
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    activity_type: ActivityType
    app_category: str
    educational_value: float
    total_minutes: int
    breaks_taken: List[Dict[str, Any]]
    parent_approved_extension: bool

@dataclass
class HealthMetrics:
    user_id: str
    date: datetime
    total_screen_minutes: int
    educational_minutes: int
    break_compliance_rate: float
    eye_strain_indicators: int
    posture_reminders: int
    activity_balance_score: float
    sleep_schedule_impact: float

@dataclass
class BreakReminder:
    reminder_id: str
    user_id: str
    break_type: BreakType
    trigger_time: datetime
    activity_suggestions: List[str]
    duration_minutes: int
    is_mandatory: bool
    parent_notification: bool

class ScreenTimeManager:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.active_sessions: Dict[str, ScreenTimeSession] = {}
        self.user_limits: Dict[str, ScreenTimeLimits] = {}
        self.pending_reminders: Dict[str, List[BreakReminder]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Age-appropriate default limits (in minutes)
        self.default_limits = {
            (3, 5): {"weekday": 30, "weekend": 60, "educational_bonus": 15},
            (6, 8): {"weekday": 60, "weekend": 90, "educational_bonus": 30},
            (9, 12): {"weekday": 90, "weekend": 120, "educational_bonus": 45},
            (13, 17): {"weekday": 120, "weekend": 180, "educational_bonus": 60}
        }
        
        # Activity-specific break intervals
        self.break_schedules = {
            ActivityType.EDUCATIONAL: {"micro": 15, "short": 45, "long": 90},
            ActivityType.CREATIVE: {"micro": 20, "short": 60, "long": 120},
            ActivityType.GAMING: {"micro": 10, "short": 30, "long": 60},
            ActivityType.ENTERTAINMENT: {"micro": 15, "short": 45, "long": 90},
            ActivityType.SOCIAL: {"micro": 20, "short": 60, "long": 90}
        }

    async def initialize_database(self):
        """Initialize database tables for screen time management"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS screen_time_limits (
                    user_id VARCHAR PRIMARY KEY,
                    age INTEGER NOT NULL,
                    weekday_minutes INTEGER NOT NULL,
                    weekend_minutes INTEGER NOT NULL,
                    holiday_minutes INTEGER NOT NULL,
                    educational_bonus_minutes INTEGER NOT NULL,
                    bedtime_hour INTEGER NOT NULL,
                    morning_start_hour INTEGER NOT NULL,
                    break_intervals JSONB NOT NULL,
                    activity_priorities JSONB NOT NULL,
                    restricted_periods JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS screen_time_sessions (
                    session_id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    activity_type VARCHAR NOT NULL,
                    app_category VARCHAR NOT NULL,
                    educational_value FLOAT NOT NULL,
                    total_minutes INTEGER DEFAULT 0,
                    breaks_taken JSONB NOT NULL DEFAULT '[]',
                    parent_approved_extension BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES screen_time_limits(user_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS health_metrics (
                    user_id VARCHAR NOT NULL,
                    date DATE NOT NULL,
                    total_screen_minutes INTEGER NOT NULL,
                    educational_minutes INTEGER NOT NULL,
                    break_compliance_rate FLOAT NOT NULL,
                    eye_strain_indicators INTEGER NOT NULL,
                    posture_reminders INTEGER NOT NULL,
                    activity_balance_score FLOAT NOT NULL,
                    sleep_schedule_impact FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, date),
                    FOREIGN KEY (user_id) REFERENCES screen_time_limits(user_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS break_reminders (
                    reminder_id VARCHAR PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    break_type VARCHAR NOT NULL,
                    trigger_time TIMESTAMP NOT NULL,
                    activity_suggestions JSONB NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    is_mandatory BOOLEAN NOT NULL,
                    parent_notification BOOLEAN NOT NULL,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES screen_time_limits(user_id)
                )
            """)

    async def set_user_limits(self, user_id: str, age: int, custom_limits: Optional[Dict] = None) -> ScreenTimeLimits:
        """Set screen time limits for a user based on age and custom preferences"""
        
        # Determine default limits based on age
        default_limit = None
        for age_range, limits in self.default_limits.items():
            if age_range[0] <= age <= age_range[1]:
                default_limit = limits
                break
        
        if not default_limit:
            # For users outside defined ranges, use most appropriate
            if age < 3:
                default_limit = self.default_limits[(3, 5)]
                default_limit["weekday"] = 15  # Very restricted for very young
            else:
                default_limit = self.default_limits[(13, 17)]
        
        # Apply custom overrides
        if custom_limits:
            default_limit.update(custom_limits)
        
        # Create comprehensive limits object
        limits = ScreenTimeLimits(
            user_id=user_id,
            age=age,
            weekday_minutes=default_limit["weekday"],
            weekend_minutes=default_limit["weekend"],
            holiday_minutes=default_limit.get("holiday", default_limit["weekend"]),
            educational_bonus_minutes=default_limit["educational_bonus"],
            bedtime_hour=custom_limits.get("bedtime_hour", 20 if age < 10 else 21),
            morning_start_hour=custom_limits.get("morning_start_hour", 7),
            break_intervals={
                "micro_minutes": 1,
                "short_minutes": 5,
                "long_minutes": 15,
                "micro_interval": 15,
                "short_interval": 45,
                "long_interval": 90
            },
            activity_priorities=[
                ActivityType.EDUCATIONAL.value,
                ActivityType.CREATIVE.value,
                ActivityType.PHYSICAL.value,
                ActivityType.SOCIAL.value,
                ActivityType.ENTERTAINMENT.value,
                ActivityType.GAMING.value
            ],
            restricted_periods=custom_limits.get("restricted_periods", [
                {"start_hour": 20, "end_hour": 7, "reason": "bedtime"},
                {"start_hour": 12, "end_hour": 13, "reason": "lunch_break"}
            ])
        )
        
        # Store in database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO screen_time_limits 
                (user_id, age, weekday_minutes, weekend_minutes, holiday_minutes, 
                 educational_bonus_minutes, bedtime_hour, morning_start_hour, 
                 break_intervals, activity_priorities, restricted_periods, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                age = EXCLUDED.age,
                weekday_minutes = EXCLUDED.weekday_minutes,
                weekend_minutes = EXCLUDED.weekend_minutes,
                holiday_minutes = EXCLUDED.holiday_minutes,
                educational_bonus_minutes = EXCLUDED.educational_bonus_minutes,
                bedtime_hour = EXCLUDED.bedtime_hour,
                morning_start_hour = EXCLUDED.morning_start_hour,
                break_intervals = EXCLUDED.break_intervals,
                activity_priorities = EXCLUDED.activity_priorities,
                restricted_periods = EXCLUDED.restricted_periods,
                updated_at = CURRENT_TIMESTAMP
            """, user_id, age, limits.weekday_minutes, limits.weekend_minutes,
                limits.holiday_minutes, limits.educational_bonus_minutes,
                limits.bedtime_hour, limits.morning_start_hour,
                json.dumps(limits.break_intervals),
                json.dumps(limits.activity_priorities),
                json.dumps(limits.restricted_periods)
            )
        
        self.user_limits[user_id] = limits
        return limits

    async def start_session(self, user_id: str, activity_type: ActivityType, 
                          app_category: str, educational_value: float = 0.0) -> Optional[str]:
        """Start a new screen time session"""
        
        # Check if user can start session
        can_start, reason = await self.can_start_session(user_id, activity_type)
        if not can_start:
            self.logger.warning(f"Session start blocked for {user_id}: {reason}")
            return None
        
        session_id = f"session_{user_id}_{int(datetime.now().timestamp())}"
        session = ScreenTimeSession(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.now(),
            end_time=None,
            activity_type=activity_type,
            app_category=app_category,
            educational_value=educational_value,
            total_minutes=0,
            breaks_taken=[],
            parent_approved_extension=False
        )
        
        # Store in database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO screen_time_sessions 
                (session_id, user_id, start_time, activity_type, app_category, 
                 educational_value, breaks_taken)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, session_id, user_id, session.start_time, activity_type.value,
                app_category, educational_value, json.dumps([])
            )
        
        self.active_sessions[session_id] = session
        
        # Schedule break reminders
        await self.schedule_break_reminders(session_id)
        
        return session_id

    async def can_start_session(self, user_id: str, activity_type: ActivityType) -> Tuple[bool, str]:
        """Check if user can start a new screen time session"""
        
        # Load user limits
        if user_id not in self.user_limits:
            await self.load_user_limits(user_id)
        
        if user_id not in self.user_limits:
            return False, "User limits not configured"
        
        limits = self.user_limits[user_id]
        now = datetime.now()
        
        # Check restricted periods
        current_hour = now.hour
        for period in limits.restricted_periods:
            start_hour = period["start_hour"]
            end_hour = period["end_hour"]
            
            if start_hour > end_hour:  # Overnight restriction
                if current_hour >= start_hour or current_hour <= end_hour:
                    return False, f"Restricted period: {period.get('reason', 'No screen time allowed')}"
            else:
                if start_hour <= current_hour <= end_hour:
                    return False, f"Restricted period: {period.get('reason', 'No screen time allowed')}"
        
        # Check daily limits
        today_minutes = await self.get_daily_usage(user_id, now.date())
        daily_limit = await self.get_daily_limit(user_id, now.date())
        
        if today_minutes >= daily_limit:
            # Check if educational bonus applies
            if activity_type == ActivityType.EDUCATIONAL:
                educational_today = await self.get_daily_educational_usage(user_id, now.date())
                if educational_today < limits.educational_bonus_minutes:
                    return True, "Educational bonus time available"
            
            return False, "Daily screen time limit reached"
        
        return True, "Session can start"

    async def end_session(self, session_id: str) -> Optional[ScreenTimeSession]:
        """End a screen time session and update records"""
        
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        session.end_time = datetime.now()
        session.total_minutes = int((session.end_time - session.start_time).total_seconds() / 60)
        
        # Update database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE screen_time_sessions 
                SET end_time = $1, total_minutes = $2, breaks_taken = $3
                WHERE session_id = $4
            """, session.end_time, session.total_minutes, 
                json.dumps(session.breaks_taken), session_id
            )
        
        # Update daily health metrics
        await self.update_health_metrics(session.user_id, session)
        
        # Remove from active sessions
        del self.active_sessions[session_id]
        
        return session

    async def schedule_break_reminders(self, session_id: str):
        """Schedule break reminders for a session"""
        
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        break_schedule = self.break_schedules.get(session.activity_type, self.break_schedules[ActivityType.ENTERTAINMENT])
        
        # Schedule micro breaks
        micro_interval = break_schedule["micro"]
        micro_reminder = BreakReminder(
            reminder_id=f"micro_{session_id}_{int(datetime.now().timestamp())}",
            user_id=session.user_id,
            break_type=BreakType.MICRO,
            trigger_time=session.start_time + timedelta(minutes=micro_interval),
            activity_suggestions=[
                "Blink your eyes 10 times slowly",
                "Look at something far away for 20 seconds",
                "Stretch your neck gently"
            ],
            duration_minutes=1,
            is_mandatory=True,
            parent_notification=False
        )
        
        # Schedule short breaks
        short_interval = break_schedule["short"]
        short_reminder = BreakReminder(
            reminder_id=f"short_{session_id}_{int(datetime.now().timestamp())}",
            user_id=session.user_id,
            break_type=BreakType.SHORT,
            trigger_time=session.start_time + timedelta(minutes=short_interval),
            activity_suggestions=[
                "Stand up and walk around",
                "Do some jumping jacks",
                "Get a drink of water",
                "Look out the window"
            ],
            duration_minutes=5,
            is_mandatory=True,
            parent_notification=False
        )
        
        # Schedule long breaks
        long_interval = break_schedule["long"]
        long_reminder = BreakReminder(
            reminder_id=f"long_{session_id}_{int(datetime.now().timestamp())}",
            user_id=session.user_id,
            break_type=BreakType.LONG,
            trigger_time=session.start_time + timedelta(minutes=long_interval),
            activity_suggestions=[
                "Go outside for fresh air",
                "Play with a pet or toy",
                "Help with a household chore",
                "Read a book",
                "Draw or color"
            ],
            duration_minutes=15,
            is_mandatory=True,
            parent_notification=True
        )
        
        reminders = [micro_reminder, short_reminder, long_reminder]
        
        # Store reminders
        if session.user_id not in self.pending_reminders:
            self.pending_reminders[session.user_id] = []
        self.pending_reminders[session.user_id].extend(reminders)
        
        # Store in database
        async with self.db_pool.acquire() as conn:
            for reminder in reminders:
                await conn.execute("""
                    INSERT INTO break_reminders 
                    (reminder_id, user_id, break_type, trigger_time, 
                     activity_suggestions, duration_minutes, is_mandatory, parent_notification)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, reminder.reminder_id, reminder.user_id, reminder.break_type.value,
                    reminder.trigger_time, json.dumps(reminder.activity_suggestions),
                    reminder.duration_minutes, reminder.is_mandatory, reminder.parent_notification
                )

    async def get_daily_usage(self, user_id: str, date: datetime.date) -> int:
        """Get total screen time usage for a specific date"""
        
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT COALESCE(SUM(total_minutes), 0)
                FROM screen_time_sessions
                WHERE user_id = $1 AND DATE(start_time) = $2 AND end_time IS NOT NULL
            """, user_id, date)
        
        return result or 0

    async def get_daily_educational_usage(self, user_id: str, date: datetime.date) -> int:
        """Get educational screen time usage for a specific date"""
        
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT COALESCE(SUM(total_minutes), 0)
                FROM screen_time_sessions
                WHERE user_id = $1 AND DATE(start_time) = $2 AND end_time IS NOT NULL
                AND activity_type = $3
            """, user_id, date, ActivityType.EDUCATIONAL.value)
        
        return result or 0

    async def get_daily_limit(self, user_id: str, date: datetime.date) -> int:
        """Get daily screen time limit for a user on a specific date"""
        
        if user_id not in self.user_limits:
            await self.load_user_limits(user_id)
        
        if user_id not in self.user_limits:
            return 60  # Default fallback
        
        limits = self.user_limits[user_id]
        
        # Determine day type
        weekday = date.weekday()
        if weekday < 5:  # Monday = 0, Friday = 4
            return limits.weekday_minutes
        else:
            return limits.weekend_minutes

    async def load_user_limits(self, user_id: str):
        """Load user limits from database"""
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM screen_time_limits WHERE user_id = $1
            """, user_id)
        
        if row:
            limits = ScreenTimeLimits(
                user_id=row["user_id"],
                age=row["age"],
                weekday_minutes=row["weekday_minutes"],
                weekend_minutes=row["weekend_minutes"],
                holiday_minutes=row["holiday_minutes"],
                educational_bonus_minutes=row["educational_bonus_minutes"],
                bedtime_hour=row["bedtime_hour"],
                morning_start_hour=row["morning_start_hour"],
                break_intervals=json.loads(row["break_intervals"]),
                activity_priorities=json.loads(row["activity_priorities"]),
                restricted_periods=json.loads(row["restricted_periods"])
            )
            self.user_limits[user_id] = limits

    async def update_health_metrics(self, user_id: str, session: ScreenTimeSession):
        """Update daily health metrics based on completed session"""
        
        date = session.start_time.date()
        
        # Calculate metrics
        educational_minutes = session.total_minutes if session.activity_type == ActivityType.EDUCATIONAL else 0
        break_compliance = len(session.breaks_taken) / max(1, session.total_minutes // 15)  # Expected break every 15 min
        break_compliance = min(1.0, break_compliance)
        
        # Get current day's totals
        total_today = await self.get_daily_usage(user_id, date)
        educational_today = await self.get_daily_educational_usage(user_id, date)
        
        # Calculate activity balance (educational vs entertainment ratio)
        if total_today > 0:
            activity_balance = educational_today / total_today
        else:
            activity_balance = 1.0 if educational_minutes > 0 else 0.0
        
        # Estimate sleep schedule impact based on evening usage
        sleep_impact = 0.0
        if session.end_time and session.end_time.hour >= 18:
            sleep_impact = min(1.0, session.total_minutes / 60)  # Higher impact for longer evening sessions
        
        # Store metrics
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO health_metrics 
                (user_id, date, total_screen_minutes, educational_minutes, 
                 break_compliance_rate, eye_strain_indicators, posture_reminders, 
                 activity_balance_score, sleep_schedule_impact)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (user_id, date) DO UPDATE SET
                total_screen_minutes = health_metrics.total_screen_minutes + EXCLUDED.total_screen_minutes,
                educational_minutes = health_metrics.educational_minutes + EXCLUDED.educational_minutes,
                break_compliance_rate = (health_metrics.break_compliance_rate + EXCLUDED.break_compliance_rate) / 2,
                activity_balance_score = EXCLUDED.activity_balance_score,
                sleep_schedule_impact = GREATEST(health_metrics.sleep_schedule_impact, EXCLUDED.sleep_schedule_impact)
            """, user_id, date, session.total_minutes, educational_minutes,
                break_compliance, 0, 0, activity_balance, sleep_impact
            )

    async def get_usage_report(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive usage report for a user"""
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        async with self.db_pool.acquire() as conn:
            # Get daily usage
            daily_usage = await conn.fetch("""
                SELECT DATE(start_time) as date, 
                       SUM(total_minutes) as total_minutes,
                       SUM(CASE WHEN activity_type = $1 THEN total_minutes ELSE 0 END) as educational_minutes,
                       COUNT(*) as sessions,
                       AVG(educational_value) as avg_educational_value
                FROM screen_time_sessions
                WHERE user_id = $2 AND DATE(start_time) BETWEEN $3 AND $4 
                AND end_time IS NOT NULL
                GROUP BY DATE(start_time)
                ORDER BY date
            """, ActivityType.EDUCATIONAL.value, user_id, start_date, end_date)
            
            # Get health metrics
            health_metrics = await conn.fetch("""
                SELECT * FROM health_metrics
                WHERE user_id = $1 AND date BETWEEN $2 AND $3
                ORDER BY date
            """, user_id, start_date, end_date)
            
            # Get break compliance
            break_stats = await conn.fetchrow("""
                SELECT COUNT(*) as total_reminders,
                       COUNT(completed_at) as completed_reminders
                FROM break_reminders
                WHERE user_id = $1 AND DATE(trigger_time) BETWEEN $2 AND $3
            """, user_id, start_date, end_date)
        
        # Process data for report
        report = {
            "user_id": user_id,
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "daily_usage": [dict(row) for row in daily_usage],
            "health_metrics": [dict(row) for row in health_metrics],
            "summary": {
                "total_screen_time": sum(row["total_minutes"] for row in daily_usage),
                "total_educational_time": sum(row["educational_minutes"] for row in daily_usage),
                "average_daily_usage": sum(row["total_minutes"] for row in daily_usage) / days,
                "educational_percentage": 0,
                "break_compliance": 0,
                "health_score": 0
            }
        }
        
        # Calculate summary statistics
        total_time = report["summary"]["total_screen_time"]
        educational_time = report["summary"]["total_educational_time"]
        
        if total_time > 0:
            report["summary"]["educational_percentage"] = (educational_time / total_time) * 100
        
        if break_stats and break_stats["total_reminders"] > 0:
            report["summary"]["break_compliance"] = (break_stats["completed_reminders"] / break_stats["total_reminders"]) * 100
        
        # Calculate overall health score (0-100)
        if health_metrics:
            avg_balance = sum(row["activity_balance_score"] for row in health_metrics) / len(health_metrics)
            avg_compliance = sum(row["break_compliance_rate"] for row in health_metrics) / len(health_metrics)
            avg_sleep_impact = sum(row["sleep_schedule_impact"] for row in health_metrics) / len(health_metrics)
            
            health_score = (avg_balance * 40 + avg_compliance * 40 + (1 - avg_sleep_impact) * 20)
            report["summary"]["health_score"] = round(health_score, 1)
        
        return report

    async def request_time_extension(self, user_id: str, additional_minutes: int, 
                                   reason: str) -> Dict[str, Any]:
        """Request additional screen time (requires parent approval)"""
        
        current_usage = await self.get_daily_usage(user_id, datetime.now().date())
        daily_limit = await self.get_daily_limit(user_id, datetime.now().date())
        
        extension_request = {
            "user_id": user_id,
            "request_time": datetime.now().isoformat(),
            "additional_minutes": additional_minutes,
            "reason": reason,
            "current_usage": current_usage,
            "daily_limit": daily_limit,
            "status": "pending_approval",
            "approval_required": True
        }
        
        # In a real implementation, this would trigger parent notification
        self.logger.info(f"Time extension requested: {extension_request}")
        
        return extension_request

    async def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old screen time data beyond retention period"""
        
        cutoff_date = datetime.now().date() - timedelta(days=days_to_keep)
        
        async with self.db_pool.acquire() as conn:
            # Clean old sessions
            await conn.execute("""
                DELETE FROM screen_time_sessions 
                WHERE DATE(start_time) < $1
            """, cutoff_date)
            
            # Clean old health metrics
            await conn.execute("""
                DELETE FROM health_metrics 
                WHERE date < $1
            """, cutoff_date)
            
            # Clean old break reminders
            await conn.execute("""
                DELETE FROM break_reminders 
                WHERE DATE(trigger_time) < $1
            """, cutoff_date)
        
        self.logger.info(f"Cleaned up screen time data older than {cutoff_date}")