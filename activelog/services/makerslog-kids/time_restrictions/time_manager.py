import asyncio
import asyncpg
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json


class RestrictionType(Enum):
    SCREEN_TIME = "screen_time"
    BREAK_REQUIRED = "break_required"
    SCHEDULED_ACCESS = "scheduled_access"
    COOLDOWN_PERIOD = "cooldown_period"


@dataclass
class TimeSession:
    user_id: str
    session_start: datetime
    session_end: Optional[datetime] = None
    activity_type: str = "general"
    break_taken: bool = False
    duration_minutes: int = 0


@dataclass
class TimeRestrictionRule:
    restriction_type: RestrictionType
    max_duration_minutes: int
    break_duration_minutes: int
    cooldown_hours: int
    allowed_time_slots: List[Tuple[str, str]]  # (start_time, end_time)
    applies_to_weekdays: bool = True
    applies_to_weekends: bool = True


class TimeManager:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.active_sessions: Dict[str, TimeSession] = {}
        self.restriction_cache: Dict[str, List[TimeRestrictionRule]] = {}
        
    async def initialize_tables(self):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS time_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    session_start TIMESTAMP NOT NULL,
                    session_end TIMESTAMP,
                    activity_type VARCHAR(50) DEFAULT 'general',
                    break_taken BOOLEAN DEFAULT FALSE,
                    duration_minutes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS time_restrictions (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    restriction_type VARCHAR(50) NOT NULL,
                    max_duration_minutes INTEGER NOT NULL,
                    break_duration_minutes INTEGER DEFAULT 15,
                    cooldown_hours INTEGER DEFAULT 1,
                    allowed_time_slots JSONB DEFAULT '[]',
                    applies_to_weekdays BOOLEAN DEFAULT TRUE,
                    applies_to_weekends BOOLEAN DEFAULT TRUE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS break_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    break_start TIMESTAMP NOT NULL,
                    break_end TIMESTAMP,
                    break_type VARCHAR(50) DEFAULT 'mandatory',
                    completed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    async def start_session(self, user_id: str, activity_type: str = "general") -> Dict:
        # Check if user can start a new session
        can_start, reason = await self.can_start_session(user_id)
        if not can_start:
            return {
                "success": False,
                "reason": reason,
                "requires_break": "break_required" in reason.lower(),
                "cooldown_until": await self.get_cooldown_end_time(user_id)
            }
        
        # Create new session
        session = TimeSession(
            user_id=user_id,
            session_start=datetime.now(),
            activity_type=activity_type
        )
        
        self.active_sessions[user_id] = session
        
        # Log to database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO time_sessions (user_id, session_start, activity_type)
                VALUES ($1, $2, $3)
            """, user_id, session.session_start, activity_type)
        
        return {
            "success": True,
            "session_id": user_id,
            "max_duration": await self.get_max_session_duration(user_id),
            "break_reminder_minutes": await self.get_break_reminder_time(user_id)
        }

    async def end_session(self, user_id: str) -> Dict:
        if user_id not in self.active_sessions:
            return {"success": False, "reason": "No active session found"}
        
        session = self.active_sessions[user_id]
        session.session_end = datetime.now()
        session.duration_minutes = int((session.session_end - session.session_start).total_seconds() / 60)
        
        # Update database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE time_sessions 
                SET session_end = $1, duration_minutes = $2
                WHERE user_id = $3 AND session_end IS NULL
            """, session.session_end, session.duration_minutes, user_id)
        
        # Remove from active sessions
        del self.active_sessions[user_id]
        
        # Check if break is required
        requires_break = await self.requires_mandatory_break(user_id, session.duration_minutes)
        
        return {
            "success": True,
            "duration_minutes": session.duration_minutes,
            "requires_break": requires_break,
            "break_duration": await self.get_required_break_duration(user_id) if requires_break else 0
        }

    async def can_start_session(self, user_id: str) -> Tuple[bool, str]:
        now = datetime.now()
        
        # Check if in cooldown period
        cooldown_end = await self.get_cooldown_end_time(user_id)
        if cooldown_end and now < cooldown_end:
            remaining = cooldown_end - now
            return False, f"In cooldown period. {remaining.seconds // 60} minutes remaining."
        
        # Check if in mandatory break
        in_break = await self.is_in_mandatory_break(user_id)
        if in_break:
            return False, "Must complete mandatory break before starting new session."
        
        # Check scheduled access windows
        in_allowed_window = await self.is_in_allowed_time_window(user_id)
        if not in_allowed_window:
            next_window = await self.get_next_allowed_window(user_id)
            return False, f"Outside allowed time window. Next access at {next_window}."
        
        # Check daily time limits
        daily_usage = await self.get_daily_usage(user_id)
        daily_limit = await self.get_daily_limit(user_id)
        if daily_usage >= daily_limit:
            return False, f"Daily time limit of {daily_limit} minutes reached."
        
        return True, "Session can be started"

    async def requires_mandatory_break(self, user_id: str, session_duration: int) -> bool:
        restrictions = await self.get_user_restrictions(user_id)
        
        for rule in restrictions:
            if rule.restriction_type == RestrictionType.BREAK_REQUIRED:
                if session_duration >= rule.max_duration_minutes:
                    return True
        
        return False

    async def start_mandatory_break(self, user_id: str) -> Dict:
        break_duration = await self.get_required_break_duration(user_id)
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO break_sessions (user_id, break_start, break_type)
                VALUES ($1, $2, 'mandatory')
            """, user_id, datetime.now())
        
        return {
            "success": True,
            "break_duration_minutes": break_duration,
            "break_activities": await self.get_break_activities(user_id),
            "break_end_time": datetime.now() + timedelta(minutes=break_duration)
        }

    async def complete_break(self, user_id: str) -> Dict:
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE break_sessions 
                SET break_end = $1, completed = TRUE
                WHERE user_id = $2 AND completed = FALSE
                RETURNING id
            """, datetime.now(), user_id)
        
        if result == "UPDATE 0":
            return {"success": False, "reason": "No active break session found"}
        
        return {
            "success": True,
            "message": "Break completed successfully",
            "can_start_new_session": await self.can_start_session(user_id)
        }

    async def get_session_status(self, user_id: str) -> Dict:
        if user_id not in self.active_sessions:
            return {
                "active": False,
                "can_start": await self.can_start_session(user_id),
                "daily_usage": await self.get_daily_usage(user_id),
                "daily_limit": await self.get_daily_limit(user_id)
            }
        
        session = self.active_sessions[user_id]
        current_duration = int((datetime.now() - session.session_start).total_seconds() / 60)
        max_duration = await self.get_max_session_duration(user_id)
        
        return {
            "active": True,
            "duration_minutes": current_duration,
            "max_duration": max_duration,
            "time_remaining": max(0, max_duration - current_duration),
            "break_recommended": current_duration >= (max_duration * 0.8),
            "activity_type": session.activity_type
        }

    async def get_time_analytics(self, user_id: str, days: int = 7) -> Dict:
        start_date = datetime.now() - timedelta(days=days)
        
        async with self.db_pool.acquire() as conn:
            sessions = await conn.fetch("""
                SELECT * FROM time_sessions
                WHERE user_id = $1 AND session_start >= $2
                ORDER BY session_start DESC
            """, user_id, start_date)
            
            breaks = await conn.fetch("""
                SELECT * FROM break_sessions
                WHERE user_id = $1 AND break_start >= $2
                ORDER BY break_start DESC
            """, user_id, start_date)
        
        total_usage = sum(s['duration_minutes'] for s in sessions if s['duration_minutes'])
        avg_session = total_usage / len(sessions) if sessions else 0
        breaks_taken = len([b for b in breaks if b['completed']])
        
        return {
            "total_usage_minutes": total_usage,
            "total_sessions": len(sessions),
            "average_session_minutes": round(avg_session, 1),
            "breaks_taken": breaks_taken,
            "break_compliance": round(breaks_taken / len(sessions) * 100, 1) if sessions else 0,
            "daily_averages": await self.get_daily_averages(user_id, days),
            "usage_by_activity": await self.get_usage_by_activity(user_id, days)
        }

    async def get_user_restrictions(self, user_id: str) -> List[TimeRestrictionRule]:
        if user_id in self.restriction_cache:
            return self.restriction_cache[user_id]
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM time_restrictions
                WHERE user_id = $1 AND is_active = TRUE
            """, user_id)
        
        restrictions = []
        for row in rows:
            restrictions.append(TimeRestrictionRule(
                restriction_type=RestrictionType(row['restriction_type']),
                max_duration_minutes=row['max_duration_minutes'],
                break_duration_minutes=row['break_duration_minutes'],
                cooldown_hours=row['cooldown_hours'],
                allowed_time_slots=json.loads(row['allowed_time_slots']),
                applies_to_weekdays=row['applies_to_weekdays'],
                applies_to_weekends=row['applies_to_weekends']
            ))
        
        self.restriction_cache[user_id] = restrictions
        return restrictions

    async def get_daily_usage(self, user_id: str) -> int:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT COALESCE(SUM(duration_minutes), 0)
                FROM time_sessions
                WHERE user_id = $1 AND session_start >= $2
            """, user_id, today_start)
        
        # Add current session if active
        if user_id in self.active_sessions:
            current_duration = int((datetime.now() - self.active_sessions[user_id].session_start).total_seconds() / 60)
            result += current_duration
        
        return result

    async def get_daily_limit(self, user_id: str) -> int:
        restrictions = await self.get_user_restrictions(user_id)
        
        for rule in restrictions:
            if rule.restriction_type == RestrictionType.SCREEN_TIME:
                return rule.max_duration_minutes
        
        return 120  # Default 2 hours

    async def get_max_session_duration(self, user_id: str) -> int:
        restrictions = await self.get_user_restrictions(user_id)
        
        for rule in restrictions:
            if rule.restriction_type == RestrictionType.BREAK_REQUIRED:
                return rule.max_duration_minutes
        
        return 45  # Default 45 minutes

    async def get_break_reminder_time(self, user_id: str) -> int:
        max_session = await self.get_max_session_duration(user_id)
        return max(10, int(max_session * 0.8))  # 80% of max session

    async def get_required_break_duration(self, user_id: str) -> int:
        restrictions = await self.get_user_restrictions(user_id)
        
        for rule in restrictions:
            if rule.restriction_type == RestrictionType.BREAK_REQUIRED:
                return rule.break_duration_minutes
        
        return 15  # Default 15 minutes

    async def get_cooldown_end_time(self, user_id: str) -> Optional[datetime]:
        async with self.db_pool.acquire() as conn:
            last_session = await conn.fetchrow("""
                SELECT session_end FROM time_sessions
                WHERE user_id = $1 AND session_end IS NOT NULL
                ORDER BY session_end DESC LIMIT 1
            """, user_id)
        
        if not last_session:
            return None
        
        restrictions = await self.get_user_restrictions(user_id)
        
        for rule in restrictions:
            if rule.restriction_type == RestrictionType.COOLDOWN_PERIOD:
                cooldown_end = last_session['session_end'] + timedelta(hours=rule.cooldown_hours)
                if datetime.now() < cooldown_end:
                    return cooldown_end
        
        return None

    async def is_in_mandatory_break(self, user_id: str) -> bool:
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT COUNT(*) FROM break_sessions
                WHERE user_id = $1 AND completed = FALSE AND break_type = 'mandatory'
            """, user_id)
        
        return result > 0

    async def is_in_allowed_time_window(self, user_id: str) -> bool:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        is_weekday = now.weekday() < 5
        
        restrictions = await self.get_user_restrictions(user_id)
        
        for rule in restrictions:
            if rule.restriction_type == RestrictionType.SCHEDULED_ACCESS:
                applies_today = (is_weekday and rule.applies_to_weekdays) or (not is_weekday and rule.applies_to_weekends)
                
                if applies_today:
                    for start_time, end_time in rule.allowed_time_slots:
                        if start_time <= current_time <= end_time:
                            return True
                    return False
        
        return True  # No scheduled restrictions found

    async def get_next_allowed_window(self, user_id: str) -> str:
        now = datetime.now()
        restrictions = await self.get_user_restrictions(user_id)
        
        for rule in restrictions:
            if rule.restriction_type == RestrictionType.SCHEDULED_ACCESS:
                for start_time, _ in rule.allowed_time_slots:
                    window_start = datetime.strptime(start_time, "%H:%M").time()
                    next_window = datetime.combine(now.date(), window_start)
                    
                    if next_window <= now:
                        next_window = next_window + timedelta(days=1)
                    
                    return next_window.strftime("%H:%M")
        
        return "Always available"

    async def get_break_activities(self, user_id: str) -> List[str]:
        # Age-appropriate break activities
        return [
            "Take a walk outside",
            "Do some stretching exercises", 
            "Drink water and have a healthy snack",
            "Practice deep breathing",
            "Draw or doodle on paper",
            "Play with a pet",
            "Help with a household chore",
            "Read a few pages of a book"
        ]

    async def get_daily_averages(self, user_id: str, days: int) -> Dict:
        start_date = datetime.now() - timedelta(days=days)
        
        async with self.db_pool.acquire() as conn:
            daily_stats = await conn.fetch("""
                SELECT 
                    DATE(session_start) as date,
                    SUM(duration_minutes) as total_minutes,
                    COUNT(*) as session_count
                FROM time_sessions
                WHERE user_id = $1 AND session_start >= $2
                GROUP BY DATE(session_start)
                ORDER BY date DESC
            """, user_id, start_date)
        
        return {
            "daily_usage": [{"date": str(row['date']), "minutes": row['total_minutes'], "sessions": row['session_count']} for row in daily_stats]
        }

    async def get_usage_by_activity(self, user_id: str, days: int) -> Dict:
        start_date = datetime.now() - timedelta(days=days)
        
        async with self.db_pool.acquire() as conn:
            activity_stats = await conn.fetch("""
                SELECT 
                    activity_type,
                    SUM(duration_minutes) as total_minutes,
                    COUNT(*) as session_count
                FROM time_sessions
                WHERE user_id = $1 AND session_start >= $2
                GROUP BY activity_type
                ORDER BY total_minutes DESC
            """, user_id, start_date)
        
        return {
            "by_activity": [{"activity": row['activity_type'], "minutes": row['total_minutes'], "sessions": row['session_count']} for row in activity_stats]
        }

    async def set_user_restrictions(self, user_id: str, restrictions: List[TimeRestrictionRule]):
        async with self.db_pool.acquire() as conn:
            # Deactivate existing restrictions
            await conn.execute("""
                UPDATE time_restrictions SET is_active = FALSE
                WHERE user_id = $1
            """, user_id)
            
            # Insert new restrictions
            for rule in restrictions:
                await conn.execute("""
                    INSERT INTO time_restrictions (
                        user_id, restriction_type, max_duration_minutes,
                        break_duration_minutes, cooldown_hours, allowed_time_slots,
                        applies_to_weekdays, applies_to_weekends
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, 
                    user_id, rule.restriction_type.value, rule.max_duration_minutes,
                    rule.break_duration_minutes, rule.cooldown_hours, 
                    json.dumps(rule.allowed_time_slots),
                    rule.applies_to_weekdays, rule.applies_to_weekends
                )
        
        # Clear cache
        if user_id in self.restriction_cache:
            del self.restriction_cache[user_id]