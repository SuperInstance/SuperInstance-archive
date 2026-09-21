"""
Important Date Reminder Engine with Social Context

AI-powered system for tracking and managing important dates in relationships
with intelligent contextual reminders and personalized action suggestions.
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import json

class DateType(Enum):
    BIRTHDAY = "birthday"
    ANNIVERSARY = "anniversary"
    WORK_ANNIVERSARY = "work_anniversary"
    WEDDING = "wedding"
    GRADUATION = "graduation"
    PROMOTION = "promotion"
    PERSONAL_MILESTONE = "personal_milestone"
    HOLIDAY = "holiday"
    CUSTOM = "custom"

class ReminderPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ActionType(Enum):
    SEND_MESSAGE = "send_message"
    SCHEDULE_CALL = "schedule_call"
    SEND_GIFT = "send_gift"
    PLAN_CELEBRATION = "plan_celebration"
    SEND_CARD = "send_card"
    MAKE_RESERVATION = "make_reservation"
    ORGANIZE_EVENT = "organize_event"

@dataclass
class ImportantDate:
    id: Optional[int] = None
    person_id: str = ""
    title: str = ""
    date_type: DateType = DateType.CUSTOM
    date: datetime = datetime.now()
    is_recurring: bool = False
    recurrence_pattern: str = "yearly"
    description: str = ""
    relationship_context: str = ""
    cultural_context: str = ""
    personal_significance: int = 5  # 1-10 scale
    privacy_level: str = "personal"  # personal, shared, public
    tags: List[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class ReminderNotification:
    id: Optional[int] = None
    date_id: int = 0
    reminder_time: datetime = datetime.now()
    priority: ReminderPriority = ReminderPriority.MEDIUM
    message: str = ""
    is_sent: bool = False
    channel: str = "app"  # app, email, sms, push
    context_data: Dict[str, Any] = None
    created_at: datetime = datetime.now()

    def __post_init__(self):
        if self.context_data is None:
            self.context_data = {}

@dataclass
class ContextualAction:
    id: Optional[int] = None
    date_id: int = 0
    action_type: ActionType = ActionType.SEND_MESSAGE
    title: str = ""
    description: str = ""
    suggested_timing: str = "1_day_before"
    priority_score: float = 0.5
    personalization_data: Dict[str, Any] = None
    estimated_effort: str = "low"  # low, medium, high
    cost_estimate: Optional[float] = None
    is_completed: bool = False
    completion_notes: str = ""

    def __post_init__(self):
        if self.personalization_data is None:
            self.personalization_data = {}

class DateReminderEngine:
    """AI-powered important date reminder system with social context awareness"""
    
    def __init__(self, db_path: str = "date_reminders.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the date reminders database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS important_dates (
                id INTEGER PRIMARY KEY,
                person_id TEXT NOT NULL,
                title TEXT NOT NULL,
                date_type TEXT NOT NULL,
                date TEXT NOT NULL,
                is_recurring BOOLEAN DEFAULT TRUE,
                recurrence_pattern TEXT DEFAULT 'yearly',
                description TEXT,
                relationship_context TEXT,
                cultural_context TEXT,
                personal_significance INTEGER DEFAULT 5,
                privacy_level TEXT DEFAULT 'personal',
                tags TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminder_notifications (
                id INTEGER PRIMARY KEY,
                date_id INTEGER,
                reminder_time TEXT NOT NULL,
                priority TEXT NOT NULL,
                message TEXT NOT NULL,
                is_sent BOOLEAN DEFAULT FALSE,
                channel TEXT DEFAULT 'app',
                context_data TEXT,
                created_at TEXT,
                FOREIGN KEY (date_id) REFERENCES important_dates (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contextual_actions (
                id INTEGER PRIMARY KEY,
                date_id INTEGER,
                action_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                suggested_timing TEXT DEFAULT '1_day_before',
                priority_score REAL DEFAULT 0.5,
                personalization_data TEXT,
                estimated_effort TEXT DEFAULT 'low',
                cost_estimate REAL,
                is_completed BOOLEAN DEFAULT FALSE,
                completion_notes TEXT,
                FOREIGN KEY (date_id) REFERENCES important_dates (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def add_important_date(self, date_info: ImportantDate) -> int:
        """Add a new important date to track"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO important_dates 
            (person_id, title, date_type, date, is_recurring, recurrence_pattern,
             description, relationship_context, cultural_context, personal_significance,
             privacy_level, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date_info.person_id, date_info.title, date_info.date_type.value,
            date_info.date.isoformat(), date_info.is_recurring, date_info.recurrence_pattern,
            date_info.description, date_info.relationship_context, date_info.cultural_context,
            date_info.personal_significance, date_info.privacy_level, json.dumps(date_info.tags),
            date_info.created_at.isoformat(), date_info.updated_at.isoformat()
        ))
        
        date_id = cursor.lastrowid
        conn.commit()
        
        # Generate contextual actions for this date
        await self._generate_contextual_actions(date_id, date_info)
        
        # Create reminder notifications
        await self._schedule_reminders(date_id, date_info)
        
        conn.close()
        return date_id
    
    async def _generate_contextual_actions(self, date_id: int, date_info: ImportantDate):
        """Generate AI-powered contextual action suggestions"""
        actions = []
        
        # Birthday-specific actions
        if date_info.date_type == DateType.BIRTHDAY:
            actions.extend([
                ContextualAction(
                    date_id=date_id,
                    action_type=ActionType.SEND_MESSAGE,
                    title="Send Birthday Wishes",
                    description=f"Send personalized birthday message to {date_info.person_id}",
                    suggested_timing="on_day",
                    priority_score=0.9,
                    estimated_effort="low"
                ),
                ContextualAction(
                    date_id=date_id,
                    action_type=ActionType.SEND_GIFT,
                    title="Consider Birthday Gift",
                    description="Review gift suggestions based on relationship and preferences",
                    suggested_timing="1_week_before",
                    priority_score=0.7,
                    estimated_effort="medium"
                )
            ])
        
        # Anniversary actions
        elif date_info.date_type == DateType.ANNIVERSARY:
            actions.extend([
                ContextualAction(
                    date_id=date_id,
                    action_type=ActionType.PLAN_CELEBRATION,
                    title="Plan Anniversary Celebration",
                    description="Organize special celebration or activity",
                    suggested_timing="2_weeks_before",
                    priority_score=0.8,
                    estimated_effort="high"
                ),
                ContextualAction(
                    date_id=date_id,
                    action_type=ActionType.MAKE_RESERVATION,
                    title="Make Dinner Reservation",
                    description="Book restaurant or special venue",
                    suggested_timing="1_week_before",
                    priority_score=0.6,
                    estimated_effort="low"
                )
            ])
        
        # Work-related actions
        elif date_info.date_type in [DateType.WORK_ANNIVERSARY, DateType.PROMOTION]:
            actions.append(
                ContextualAction(
                    date_id=date_id,
                    action_type=ActionType.SEND_MESSAGE,
                    title="Professional Congratulations",
                    description="Send professional congratulatory message",
                    suggested_timing="on_day",
                    priority_score=0.7,
                    estimated_effort="low"
                )
            )
        
        # Store actions in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for action in actions:
            cursor.execute("""
                INSERT INTO contextual_actions 
                (date_id, action_type, title, description, suggested_timing,
                 priority_score, personalization_data, estimated_effort, cost_estimate,
                 is_completed, completion_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action.date_id, action.action_type.value, action.title, action.description,
                action.suggested_timing, action.priority_score, json.dumps(action.personalization_data),
                action.estimated_effort, action.cost_estimate, action.is_completed, action.completion_notes
            ))
        
        conn.commit()
        conn.close()
    
    async def _schedule_reminders(self, date_id: int, date_info: ImportantDate):
        """Schedule intelligent reminders based on date importance and type"""
        reminders = []
        base_date = date_info.date
        
        # High significance dates get more reminders
        if date_info.personal_significance >= 8:
            reminder_schedule = [
                (timedelta(weeks=2), ReminderPriority.LOW, "2 weeks advance notice"),
                (timedelta(weeks=1), ReminderPriority.MEDIUM, "1 week reminder"),
                (timedelta(days=3), ReminderPriority.HIGH, "3 days to prepare"),
                (timedelta(days=1), ReminderPriority.HIGH, "Tomorrow reminder"),
                (timedelta(hours=2), ReminderPriority.CRITICAL, "Today - 2 hours notice")
            ]
        elif date_info.personal_significance >= 6:
            reminder_schedule = [
                (timedelta(weeks=1), ReminderPriority.MEDIUM, "1 week reminder"),
                (timedelta(days=2), ReminderPriority.HIGH, "2 days notice"),
                (timedelta(hours=4), ReminderPriority.HIGH, "Same day reminder")
            ]
        else:
            reminder_schedule = [
                (timedelta(days=3), ReminderPriority.MEDIUM, "3 days notice"),
                (timedelta(hours=6), ReminderPriority.MEDIUM, "Same day reminder")
            ]
        
        # Create reminders
        for offset, priority, description in reminder_schedule:
            reminder_time = base_date - offset
            if reminder_time > datetime.now():  # Only future reminders
                message = f"{description}: {date_info.title} for {date_info.person_id}"
                
                reminders.append(ReminderNotification(
                    date_id=date_id,
                    reminder_time=reminder_time,
                    priority=priority,
                    message=message,
                    context_data={
                        "date_type": date_info.date_type.value,
                        "significance": date_info.personal_significance,
                        "relationship_context": date_info.relationship_context
                    }
                ))
        
        # Store reminders in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for reminder in reminders:
            cursor.execute("""
                INSERT INTO reminder_notifications 
                (date_id, reminder_time, priority, message, is_sent, channel, context_data, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reminder.date_id, reminder.reminder_time.isoformat(), reminder.priority.value,
                reminder.message, reminder.is_sent, reminder.channel, json.dumps(reminder.context_data),
                reminder.created_at.isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    async def get_upcoming_dates(self, days_ahead: int = 30) -> List[Dict]:
        """Get upcoming important dates within specified timeframe"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        end_date = datetime.now() + timedelta(days=days_ahead)
        
        cursor.execute("""
            SELECT * FROM important_dates 
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC
        """, (datetime.now().isoformat(), end_date.isoformat()))
        
        dates = []
        for row in cursor.fetchall():
            date_dict = dict(zip([col[0] for col in cursor.description], row))
            date_dict['tags'] = json.loads(date_dict['tags']) if date_dict['tags'] else []
            dates.append(date_dict)
        
        conn.close()
        return dates
    
    async def get_pending_reminders(self) -> List[Dict]:
        """Get pending reminder notifications"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT rn.*, id_table.title, id_table.person_id, id_table.date_type 
            FROM reminder_notifications rn
            JOIN important_dates id_table ON rn.date_id = id_table.id
            WHERE rn.reminder_time <= ? AND rn.is_sent = FALSE
            ORDER BY rn.priority DESC, rn.reminder_time ASC
        """, (datetime.now().isoformat(),))
        
        reminders = []
        for row in cursor.fetchall():
            reminder_dict = dict(zip([col[0] for col in cursor.description], row))
            reminder_dict['context_data'] = json.loads(reminder_dict['context_data']) if reminder_dict['context_data'] else {}
            reminders.append(reminder_dict)
        
        conn.close()
        return reminders
    
    async def get_contextual_actions(self, date_id: int, timing: str = None) -> List[Dict]:
        """Get contextual action suggestions for a specific date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM contextual_actions WHERE date_id = ?"
        params = [date_id]
        
        if timing:
            query += " AND suggested_timing = ?"
            params.append(timing)
        
        query += " ORDER BY priority_score DESC"
        
        cursor.execute(query, params)
        
        actions = []
        for row in cursor.fetchall():
            action_dict = dict(zip([col[0] for col in cursor.description], row))
            action_dict['personalization_data'] = json.loads(action_dict['personalization_data']) if action_dict['personalization_data'] else {}
            actions.append(action_dict)
        
        conn.close()
        return actions
    
    async def mark_reminder_sent(self, reminder_id: int):
        """Mark a reminder as sent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE reminder_notifications 
            SET is_sent = TRUE 
            WHERE id = ?
        """, (reminder_id,))
        
        conn.commit()
        conn.close()
    
    async def complete_action(self, action_id: int, completion_notes: str = ""):
        """Mark an action as completed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE contextual_actions 
            SET is_completed = TRUE, completion_notes = ? 
            WHERE id = ?
        """, (completion_notes, action_id))
        
        conn.commit()
        conn.close()
    
    async def analyze_date_patterns(self, person_id: str) -> Dict[str, Any]:
        """Analyze patterns in important dates for relationship insights"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT date_type, COUNT(*) as count, AVG(personal_significance) as avg_significance
            FROM important_dates 
            WHERE person_id = ?
            GROUP BY date_type
        """, (person_id,))
        
        type_patterns = {}
        for row in cursor.fetchall():
            type_patterns[row[0]] = {
                'count': row[1],
                'avg_significance': round(row[2], 2)
            }
        
        # Calculate relationship investment score
        cursor.execute("""
            SELECT COUNT(*), AVG(personal_significance), MAX(date) as last_date
            FROM important_dates 
            WHERE person_id = ?
        """, (person_id,))
        
        row = cursor.fetchone()
        total_dates = row[0]
        avg_significance = row[1] if row[1] else 0
        last_date = row[2]
        
        investment_score = (total_dates * 0.3) + (avg_significance * 0.7)
        
        conn.close()
        
        return {
            'person_id': person_id,
            'total_tracked_dates': total_dates,
            'average_significance': round(avg_significance, 2) if avg_significance else 0,
            'last_recorded_date': last_date,
            'investment_score': round(investment_score, 2),
            'date_type_patterns': type_patterns,
            'relationship_strength_indicator': 'high' if investment_score > 7 else 'medium' if investment_score > 4 else 'low'
        }

# Demo function
async def demo_date_reminder_engine():
    """Demonstrate the Date Reminder Engine functionality"""
    print("🗓️ Date Reminder Engine Demo")
    print("=" * 50)
    
    engine = DateReminderEngine()
    
    # Add important dates
    print("\n1. Adding Important Dates...")
    
    sarah_birthday = ImportantDate(
        person_id="sarah_j",
        title="Sarah's Birthday",
        date_type=DateType.BIRTHDAY,
        date=datetime(2024, 9, 15),
        is_recurring=True,
        description="Best friend's birthday - loves art and books",
        relationship_context="close_friend",
        cultural_context="western",
        personal_significance=9,
        tags=["birthday", "friend", "celebration"]
    )
    
    anniversary = ImportantDate(
        person_id="partner",
        title="Our Anniversary",
        date_type=DateType.ANNIVERSARY,
        date=datetime(2024, 10, 12),
        is_recurring=True,
        description="5-year relationship anniversary",
        relationship_context="romantic_partner",
        personal_significance=10,
        tags=["anniversary", "romantic", "milestone"]
    )
    
    work_anniversary = ImportantDate(
        person_id="john_m",
        title="John's Work Anniversary",
        date_type=DateType.WORK_ANNIVERSARY,
        date=datetime(2024, 9, 1),
        description="Colleague's 3rd year at company",
        relationship_context="colleague",
        personal_significance=6,
        tags=["work", "colleague", "milestone"]
    )
    
    date_id1 = await engine.add_important_date(sarah_birthday)
    date_id2 = await engine.add_important_date(anniversary)
    date_id3 = await engine.add_important_date(work_anniversary)
    
    print(f"✅ Added Sarah's birthday (ID: {date_id1})")
    print(f"✅ Added anniversary (ID: {date_id2})")
    print(f"✅ Added work anniversary (ID: {date_id3})")
    
    # Get upcoming dates
    print("\n2. Upcoming Important Dates (Next 60 days)...")
    upcoming = await engine.get_upcoming_dates(60)
    for date in upcoming:
        print(f"📅 {date['title']} - {date['date'][:10]} (Significance: {date['personal_significance']}/10)")
    
    # Check pending reminders
    print("\n3. Pending Reminders...")
    reminders = await engine.get_pending_reminders()
    for reminder in reminders[:3]:  # Show first 3
        print(f"🔔 {reminder['priority'].upper()}: {reminder['message']}")
        print(f"   Scheduled: {reminder['reminder_time'][:16]}")
    
    # Get contextual actions
    print(f"\n4. Suggested Actions for Sarah's Birthday...")
    actions = await engine.get_contextual_actions(date_id1)
    for action in actions:
        print(f"💡 {action['title']} ({action['estimated_effort']} effort)")
        print(f"   {action['description']}")
        print(f"   Suggested timing: {action['suggested_timing'].replace('_', ' ')}")
        print(f"   Priority score: {action['priority_score']}")
    
    # Analyze relationship patterns
    print(f"\n5. Relationship Analysis for Sarah...")
    analysis = await engine.analyze_date_patterns("sarah_j")
    print(f"📊 Total tracked dates: {analysis['total_tracked_dates']}")
    print(f"📊 Average significance: {analysis['average_significance']}/10")
    print(f"📊 Investment score: {analysis['investment_score']}/10")
    print(f"📊 Relationship strength: {analysis['relationship_strength_indicator']}")
    
    print("\n6. Date Type Patterns:")
    for date_type, stats in analysis['date_type_patterns'].items():
        print(f"   {date_type}: {stats['count']} dates, avg significance {stats['avg_significance']}")
    
    print("\n✅ Date Reminder Engine Demo Complete!")

if __name__ == "__main__":
    asyncio.run(demo_date_reminder_engine())