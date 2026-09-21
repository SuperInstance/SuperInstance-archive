"""
Parent-Teacher Communication Portal

Comprehensive system for facilitating communication between parents and teachers,
providing progress sharing, scheduling, messaging, and collaborative support for
student success through transparent and proactive communication channels.
"""

import asyncio
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    GENERAL = "general"
    PROGRESS_UPDATE = "progress_update"
    BEHAVIOR = "behavior"
    ATTENDANCE = "attendance"
    ASSIGNMENT = "assignment"
    CONFERENCE_REQUEST = "conference_request"
    EMERGENCY = "emergency"
    ACHIEVEMENT = "achievement"

class MessagePriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class ConferenceType(Enum):
    VIRTUAL = "virtual"
    IN_PERSON = "in_person"
    PHONE = "phone"

class NotificationPreference(Enum):
    EMAIL = "email"
    SMS = "sms"
    APP_NOTIFICATION = "app_notification"
    WEEKLY_DIGEST = "weekly_digest"

@dataclass
class Message:
    message_id: str
    sender_id: str
    recipient_id: str
    student_id: str
    message_type: MessageType
    priority: MessagePriority
    subject: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    read_status: bool = False
    parent_response: Optional[str] = None
    teacher_response: Optional[str] = None
    attachments: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProgressReport:
    report_id: str
    student_id: str
    teacher_id: str
    report_period: str
    academic_performance: Dict[str, Any] = field(default_factory=dict)
    behavioral_observations: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    areas_for_improvement: List[str] = field(default_factory=list)
    goals_next_period: List[str] = field(default_factory=list)
    teacher_comments: str = ""
    parent_feedback: Optional[str] = None
    generated_date: datetime = field(default_factory=datetime.now)
    shared_date: Optional[datetime] = None

@dataclass
class Conference:
    conference_id: str
    student_id: str
    teacher_id: str
    parent_id: str
    conference_type: ConferenceType
    scheduled_time: datetime
    duration: int = 30
    topic: str = ""
    agenda: List[str] = field(default_factory=list)
    status: str = "scheduled"
    meeting_link: Optional[str] = None
    location: Optional[str] = None
    notes: str = ""
    action_items: List[str] = field(default_factory=list)
    follow_up_required: bool = False

@dataclass
class Parent:
    parent_id: str
    name: str
    email: str
    phone: str
    children_ids: List[str] = field(default_factory=list)
    notification_preferences: List[NotificationPreference] = field(default_factory=list)
    preferred_contact_time: str = "anytime"
    language_preference: str = "english"
    emergency_contact: bool = True

@dataclass
class Teacher:
    teacher_id: str
    name: str
    email: str
    phone: str
    subjects: List[str] = field(default_factory=list)
    grade_levels: List[int] = field(default_factory=list)
    office_hours: Dict[str, str] = field(default_factory=dict)
    students: List[str] = field(default_factory=list)

@dataclass
class StudentSnapshot:
    student_id: str
    snapshot_date: datetime
    academic_summary: Dict[str, float] = field(default_factory=dict)
    recent_assignments: List[Dict[str, Any]] = field(default_factory=list)
    attendance_rate: float = 1.0
    behavior_notes: List[str] = field(default_factory=list)
    upcoming_events: List[Dict[str, Any]] = field(default_factory=list)
    goals_progress: List[Dict[str, Any]] = field(default_factory=list)

class ParentTeacherPortal:
    def __init__(self, db_path: str = "education_ai.db"):
        self.db_path = db_path
        self.notification_settings = {
            "smtp_server": "localhost",
            "smtp_port": 587,
            "email_user": "education@school.edu",
            "email_password": "secure_password"
        }
        self.init_database()
        
    def init_database(self):
        """Initialize database tables for parent-teacher communication"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parents (
                parent_id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                phone TEXT,
                children_ids TEXT,
                notification_preferences TEXT,
                preferred_contact_time TEXT,
                language_preference TEXT,
                emergency_contact BOOLEAN,
                created_date TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teachers (
                teacher_id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                phone TEXT,
                subjects TEXT,
                grade_levels TEXT,
                office_hours TEXT,
                students TEXT,
                created_date TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                sender_id TEXT,
                recipient_id TEXT,
                student_id TEXT,
                message_type TEXT,
                priority TEXT,
                subject TEXT,
                content TEXT,
                timestamp TIMESTAMP,
                read_status BOOLEAN,
                parent_response TEXT,
                teacher_response TEXT,
                attachments TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS progress_reports (
                report_id TEXT PRIMARY KEY,
                student_id TEXT,
                teacher_id TEXT,
                report_period TEXT,
                academic_performance TEXT,
                behavioral_observations TEXT,
                achievements TEXT,
                areas_for_improvement TEXT,
                goals_next_period TEXT,
                teacher_comments TEXT,
                parent_feedback TEXT,
                generated_date TIMESTAMP,
                shared_date TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conferences (
                conference_id TEXT PRIMARY KEY,
                student_id TEXT,
                teacher_id TEXT,
                parent_id TEXT,
                conference_type TEXT,
                scheduled_time TIMESTAMP,
                duration INTEGER,
                topic TEXT,
                agenda TEXT,
                status TEXT,
                meeting_link TEXT,
                location TEXT,
                notes TEXT,
                action_items TEXT,
                follow_up_required BOOLEAN
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                snapshot_date TIMESTAMP,
                academic_summary TEXT,
                recent_assignments TEXT,
                attendance_rate REAL,
                behavior_notes TEXT,
                upcoming_events TEXT,
                goals_progress TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS communication_analytics (
                analytics_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                parent_id TEXT,
                teacher_id TEXT,
                message_count INTEGER,
                response_rate REAL,
                avg_response_time REAL,
                engagement_score REAL,
                last_interaction TIMESTAMP,
                analysis_date TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Parent-teacher communication database initialized")

    async def register_parent(self, parent_id: str, name: str, email: str, 
                            phone: str, children_ids: List[str],
                            preferences: List[NotificationPreference] = None) -> Parent:
        """
        Register a parent in the communication portal
        
        Args:
            parent_id: Unique parent identifier
            name: Parent's full name
            email: Contact email
            phone: Phone number
            children_ids: List of student IDs for their children
            preferences: Notification preferences
            
        Returns:
            Parent object
        """
        parent = Parent(
            parent_id=parent_id,
            name=name,
            email=email,
            phone=phone,
            children_ids=children_ids,
            notification_preferences=preferences or [NotificationPreference.EMAIL]
        )
        
        await self._save_parent(parent)
        logger.info(f"Registered parent {name} ({parent_id}) for {len(children_ids)} children")
        return parent

    async def register_teacher(self, teacher_id: str, name: str, email: str,
                             phone: str, subjects: List[str], grade_levels: List[int],
                             students: List[str] = None) -> Teacher:
        """
        Register a teacher in the communication portal
        
        Args:
            teacher_id: Unique teacher identifier
            name: Teacher's full name
            email: Contact email
            phone: Phone number
            subjects: Subjects taught
            grade_levels: Grade levels taught
            students: List of student IDs
            
        Returns:
            Teacher object
        """
        teacher = Teacher(
            teacher_id=teacher_id,
            name=name,
            email=email,
            phone=phone,
            subjects=subjects,
            grade_levels=grade_levels,
            students=students or []
        )
        
        await self._save_teacher(teacher)
        logger.info(f"Registered teacher {name} ({teacher_id}) for subjects: {', '.join(subjects)}")
        return teacher

    async def send_message(self, sender_id: str, recipient_id: str, student_id: str,
                         message_type: MessageType, subject: str, content: str,
                         priority: MessagePriority = MessagePriority.NORMAL,
                         attachments: List[str] = None) -> Message:
        """
        Send a message between parent and teacher
        
        Args:
            sender_id: Sender identifier (parent or teacher)
            recipient_id: Recipient identifier
            student_id: Related student
            message_type: Type of message
            subject: Message subject
            content: Message content
            priority: Message priority
            attachments: File attachments
            
        Returns:
            Message object
        """
        message_id = f"msg_{sender_id}_{recipient_id}_{int(datetime.now().timestamp())}"
        
        message = Message(
            message_id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            student_id=student_id,
            message_type=message_type,
            priority=priority,
            subject=subject,
            content=content,
            attachments=attachments or []
        )
        
        await self._save_message(message)
        
        # Send notifications based on recipient preferences
        await self._send_notification(message)
        
        logger.info(f"Sent {message_type.value} message from {sender_id} to {recipient_id}")
        return message

    async def generate_progress_report(self, student_id: str, teacher_id: str,
                                     report_period: str) -> ProgressReport:
        """
        Generate comprehensive progress report for a student
        
        Args:
            student_id: Student identifier
            teacher_id: Teacher identifier
            report_period: Reporting period (e.g., "Quarter 1", "Semester 1")
            
        Returns:
            Generated progress report
        """
        report_id = f"report_{student_id}_{teacher_id}_{report_period}_{int(datetime.now().timestamp())}"
        
        # Gather academic performance data (from other systems)
        academic_performance = await self._gather_academic_data(student_id)
        
        # Generate behavioral observations
        behavioral_observations = await self._gather_behavioral_data(student_id)
        
        # Identify achievements
        achievements = await self._identify_achievements(student_id)
        
        # Determine improvement areas
        improvement_areas = await self._identify_improvement_areas(student_id)
        
        # Set goals for next period
        next_goals = await self._generate_next_period_goals(student_id)
        
        report = ProgressReport(
            report_id=report_id,
            student_id=student_id,
            teacher_id=teacher_id,
            report_period=report_period,
            academic_performance=academic_performance,
            behavioral_observations=behavioral_observations,
            achievements=achievements,
            areas_for_improvement=improvement_areas,
            goals_next_period=next_goals,
            teacher_comments=await self._generate_teacher_comments(student_id, academic_performance)
        )
        
        await self._save_progress_report(report)
        
        # Automatically share with parents
        await self._share_progress_report(report)
        
        logger.info(f"Generated progress report for student {student_id}, period {report_period}")
        return report

    async def schedule_conference(self, student_id: str, teacher_id: str, parent_id: str,
                                conference_type: ConferenceType, scheduled_time: datetime,
                                topic: str, duration: int = 30) -> Conference:
        """
        Schedule a parent-teacher conference
        
        Args:
            student_id: Student identifier
            teacher_id: Teacher identifier
            parent_id: Parent identifier
            conference_type: Type of conference
            scheduled_time: Scheduled date and time
            topic: Conference topic
            duration: Duration in minutes
            
        Returns:
            Scheduled conference
        """
        conference_id = f"conf_{student_id}_{teacher_id}_{int(scheduled_time.timestamp())}"
        
        # Generate meeting link for virtual conferences
        meeting_link = None
        if conference_type == ConferenceType.VIRTUAL:
            meeting_link = await self._generate_meeting_link(conference_id)
        
        # Create agenda
        agenda = await self._generate_conference_agenda(student_id, topic)
        
        conference = Conference(
            conference_id=conference_id,
            student_id=student_id,
            teacher_id=teacher_id,
            parent_id=parent_id,
            conference_type=conference_type,
            scheduled_time=scheduled_time,
            duration=duration,
            topic=topic,
            agenda=agenda,
            meeting_link=meeting_link
        )
        
        await self._save_conference(conference)
        
        # Send calendar invitations
        await self._send_calendar_invitation(conference)
        
        # Send reminder notifications
        await self._schedule_conference_reminders(conference)
        
        logger.info(f"Scheduled {conference_type.value} conference for student {student_id}")
        return conference

    async def create_student_snapshot(self, student_id: str) -> StudentSnapshot:
        """
        Create current snapshot of student's status for parent viewing
        
        Args:
            student_id: Student identifier
            
        Returns:
            Student snapshot
        """
        # Gather current academic data
        academic_summary = await self._get_current_academic_summary(student_id)
        
        # Get recent assignments
        recent_assignments = await self._get_recent_assignments(student_id)
        
        # Calculate attendance rate
        attendance_rate = await self._calculate_attendance_rate(student_id)
        
        # Get recent behavior notes
        behavior_notes = await self._get_recent_behavior_notes(student_id)
        
        # Get upcoming events
        upcoming_events = await self._get_upcoming_events(student_id)
        
        # Get goals progress
        goals_progress = await self._get_goals_progress(student_id)
        
        snapshot = StudentSnapshot(
            student_id=student_id,
            snapshot_date=datetime.now(),
            academic_summary=academic_summary,
            recent_assignments=recent_assignments,
            attendance_rate=attendance_rate,
            behavior_notes=behavior_notes,
            upcoming_events=upcoming_events,
            goals_progress=goals_progress
        )
        
        await self._save_student_snapshot(snapshot)
        
        # Notify parents if significant changes
        await self._check_snapshot_alerts(snapshot)
        
        return snapshot

    async def send_automated_updates(self, student_id: str):
        """Send automated progress updates to parents based on triggers"""
        parent_ids = await self._get_student_parents(student_id)
        
        for parent_id in parent_ids:
            parent = await self.get_parent(parent_id)
            if not parent:
                continue
            
            # Check if weekly digest is preferred
            if NotificationPreference.WEEKLY_DIGEST in parent.notification_preferences:
                await self._send_weekly_digest(parent_id, student_id)
            else:
                # Send individual updates based on triggers
                await self._check_update_triggers(parent_id, student_id)

    async def _gather_academic_data(self, student_id: str) -> Dict[str, Any]:
        """Gather academic performance data from various sources"""
        # This would integrate with other education AI components
        
        # Simulate academic data
        subjects = ["Mathematics", "English", "Science", "History", "Art"]
        performance = {}
        
        for subject in subjects:
            performance[subject] = {
                "current_grade": round(np.random.uniform(75, 95), 1),
                "grade_trend": np.random.choice(["improving", "stable", "declining"]),
                "assignment_completion": round(np.random.uniform(80, 100), 1),
                "participation": np.random.choice(["excellent", "good", "needs_improvement"]),
                "recent_assessments": [
                    {"name": f"{subject} Quiz", "score": "85%", "date": "2024-01-15"},
                    {"name": f"{subject} Project", "score": "92%", "date": "2024-01-10"}
                ]
            }
        
        return performance

    async def _gather_behavioral_data(self, student_id: str) -> List[str]:
        """Gather behavioral observations"""
        observations = [
            "Shows strong leadership skills in group activities",
            "Consistently helpful to classmates",
            "Demonstrates excellent time management",
            "Active participant in class discussions",
            "Shows creativity in problem-solving approaches"
        ]
        
        # Return 2-3 relevant observations
        return np.random.choice(observations, size=3, replace=False).tolist()

    async def _identify_achievements(self, student_id: str) -> List[str]:
        """Identify recent student achievements"""
        achievements = [
            "Completed advanced math module ahead of schedule",
            "Received peer recognition for collaborative work",
            "Improved reading comprehension by 2 grade levels",
            "Successfully presented research project to class",
            "Demonstrated mastery in scientific inquiry skills"
        ]
        
        return np.random.choice(achievements, size=2, replace=False).tolist()

    async def _identify_improvement_areas(self, student_id: str) -> List[str]:
        """Identify areas needing improvement"""
        areas = [
            "Could benefit from additional practice in mathematical reasoning",
            "Work on time management for larger projects",
            "Encourage more participation in oral discussions",
            "Focus on proofreading written assignments",
            "Develop strategies for organizing study materials"
        ]
        
        return np.random.choice(areas, size=2, replace=False).tolist()

    async def _generate_next_period_goals(self, student_id: str) -> List[str]:
        """Generate goals for next reporting period"""
        goals = [
            "Master multiplication and division of fractions",
            "Complete independent reading of 3 chapter books",
            "Improve essay writing structure and flow",
            "Develop presentation skills through class projects",
            "Build collaboration skills in group work"
        ]
        
        return np.random.choice(goals, size=3, replace=False).tolist()

    async def _generate_teacher_comments(self, student_id: str, academic_performance: Dict) -> str:
        """Generate personalized teacher comments"""
        positive_traits = ["hardworking", "curious", "creative", "responsible", "kind"]
        selected_trait = np.random.choice(positive_traits)
        
        avg_grade = np.mean([perf["current_grade"] for perf in academic_performance.values()])
        
        if avg_grade >= 90:
            performance_comment = "consistently demonstrates exceptional understanding"
        elif avg_grade >= 80:
            performance_comment = "shows solid grasp of concepts"
        else:
            performance_comment = "is working hard to master the material"
        
        return f"This student is {selected_trait} and {performance_comment}. They bring positive energy to our classroom and I enjoy having them as a student. I'm excited to see their continued growth next period."

    async def _generate_meeting_link(self, conference_id: str) -> str:
        """Generate virtual meeting link"""
        # In real implementation, would integrate with Zoom, Teams, etc.
        return f"https://school-meet.edu/conference/{conference_id}"

    async def _generate_conference_agenda(self, student_id: str, topic: str) -> List[str]:
        """Generate conference agenda items"""
        base_agenda = [
            "Welcome and introductions",
            "Review current academic progress",
            "Discuss recent achievements and strengths"
        ]
        
        if topic:
            base_agenda.append(f"Focus discussion: {topic}")
        
        base_agenda.extend([
            "Address any concerns or questions",
            "Set goals for upcoming period",
            "Plan next steps and follow-up"
        ])
        
        return base_agenda

    async def _send_notification(self, message: Message):
        """Send notification to message recipient"""
        recipient = await self.get_parent(message.recipient_id)
        if not recipient:
            recipient = await self.get_teacher(message.recipient_id)
        
        if not recipient:
            logger.warning(f"Recipient {message.recipient_id} not found")
            return
        
        # Send email notification
        if NotificationPreference.EMAIL in getattr(recipient, 'notification_preferences', [NotificationPreference.EMAIL]):
            await self._send_email_notification(recipient.email, message)
        
        # Send SMS (placeholder)
        if NotificationPreference.SMS in getattr(recipient, 'notification_preferences', []):
            await self._send_sms_notification(recipient.phone, message)

    async def _send_email_notification(self, email: str, message: Message):
        """Send email notification"""
        try:
            # Create email content
            msg = MimeMultipart()
            msg['From'] = self.notification_settings['email_user']
            msg['To'] = email
            msg['Subject'] = f"New Message: {message.subject}"
            
            body = f"""
            You have received a new message regarding your student.
            
            Type: {message.message_type.value.replace('_', ' ').title()}
            Priority: {message.priority.value.title()}
            Subject: {message.subject}
            
            Message:
            {message.content}
            
            Please log in to the parent portal to respond.
            
            Best regards,
            School Communication System
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            # In real implementation, would actually send email
            logger.info(f"Email notification sent to {email}")
            
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {e}")

    async def _send_sms_notification(self, phone: str, message: Message):
        """Send SMS notification (placeholder)"""
        # In real implementation, would integrate with SMS service
        logger.info(f"SMS notification would be sent to {phone}")

    async def _share_progress_report(self, report: ProgressReport):
        """Share progress report with parents"""
        parent_ids = await self._get_student_parents(report.student_id)
        
        for parent_id in parent_ids:
            await self.send_message(
                sender_id=report.teacher_id,
                recipient_id=parent_id,
                student_id=report.student_id,
                message_type=MessageType.PROGRESS_UPDATE,
                subject=f"Progress Report - {report.report_period}",
                content=f"A new progress report for {report.report_period} is available for your review. Please check the parent portal to view detailed academic progress, achievements, and goals for the next period.",
                priority=MessagePriority.NORMAL
            )
        
        # Update shared date
        report.shared_date = datetime.now()
        await self._save_progress_report(report)

    async def _send_calendar_invitation(self, conference: Conference):
        """Send calendar invitation for conference"""
        # In real implementation, would create and send calendar invites
        logger.info(f"Calendar invitation sent for conference {conference.conference_id}")

    async def _schedule_conference_reminders(self, conference: Conference):
        """Schedule reminder notifications for conference"""
        # Schedule reminders 24 hours and 1 hour before
        logger.info(f"Reminders scheduled for conference {conference.conference_id}")

    async def get_parent(self, parent_id: str) -> Optional[Parent]:
        """Get parent by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT parent_id, name, email, phone, children_ids, notification_preferences,
                   preferred_contact_time, language_preference, emergency_contact
            FROM parents
            WHERE parent_id = ?
        ''', (parent_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return Parent(
            parent_id=row[0],
            name=row[1],
            email=row[2],
            phone=row[3],
            children_ids=json.loads(row[4]) if row[4] else [],
            notification_preferences=[NotificationPreference(pref) for pref in json.loads(row[5])] if row[5] else [],
            preferred_contact_time=row[6],
            language_preference=row[7],
            emergency_contact=row[8]
        )

    async def get_teacher(self, teacher_id: str) -> Optional[Teacher]:
        """Get teacher by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT teacher_id, name, email, phone, subjects, grade_levels, office_hours, students
            FROM teachers
            WHERE teacher_id = ?
        ''', (teacher_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return Teacher(
            teacher_id=row[0],
            name=row[1],
            email=row[2],
            phone=row[3],
            subjects=json.loads(row[4]) if row[4] else [],
            grade_levels=json.loads(row[5]) if row[5] else [],
            office_hours=json.loads(row[6]) if row[6] else {},
            students=json.loads(row[7]) if row[7] else []
        )

    async def _get_student_parents(self, student_id: str) -> List[str]:
        """Get parent IDs for a student"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT parent_id FROM parents 
            WHERE children_ids LIKE ?
        ''', (f'%"{student_id}"%',))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]

    async def _get_current_academic_summary(self, student_id: str) -> Dict[str, float]:
        """Get current academic summary for student"""
        # Simulate current grades
        subjects = ["Mathematics", "English", "Science", "History"]
        return {subject: round(np.random.uniform(70, 95), 1) for subject in subjects}

    async def _get_recent_assignments(self, student_id: str) -> List[Dict[str, Any]]:
        """Get recent assignments for student"""
        assignments = [
            {"name": "Math Chapter 5 Test", "score": "88%", "due_date": "2024-01-20", "status": "completed"},
            {"name": "Science Lab Report", "score": "92%", "due_date": "2024-01-18", "status": "completed"},
            {"name": "History Essay", "score": "Pending", "due_date": "2024-01-25", "status": "submitted"},
            {"name": "English Book Report", "score": "Not submitted", "due_date": "2024-01-22", "status": "missing"}
        ]
        
        return assignments[:3]  # Return 3 most recent

    async def _calculate_attendance_rate(self, student_id: str) -> float:
        """Calculate student attendance rate"""
        return round(np.random.uniform(85, 100), 1) / 100

    async def _get_recent_behavior_notes(self, student_id: str) -> List[str]:
        """Get recent behavior notes"""
        positive_notes = [
            "Excellent participation in class discussion today",
            "Helped a classmate with challenging math problem",
            "Showed great leadership during group project"
        ]
        
        return np.random.choice(positive_notes, size=2, replace=False).tolist()

    async def _get_upcoming_events(self, student_id: str) -> List[Dict[str, Any]]:
        """Get upcoming events for student"""
        events = [
            {"name": "Science Fair", "date": "2024-02-15", "type": "school_event"},
            {"name": "Parent-Teacher Conferences", "date": "2024-02-10", "type": "conference"},
            {"name": "Math Olympiad", "date": "2024-02-20", "type": "competition"}
        ]
        
        return events

    async def _get_goals_progress(self, student_id: str) -> List[Dict[str, Any]]:
        """Get progress on current goals"""
        goals = [
            {"goal": "Improve reading speed", "progress": 75, "target_date": "2024-03-01"},
            {"goal": "Master multiplication tables", "progress": 90, "target_date": "2024-02-15"},
            {"goal": "Complete science project", "progress": 60, "target_date": "2024-02-28"}
        ]
        
        return goals

    async def _check_snapshot_alerts(self, snapshot: StudentSnapshot):
        """Check for conditions that should trigger parent alerts"""
        # Check for low attendance
        if snapshot.attendance_rate < 0.9:
            parent_ids = await self._get_student_parents(snapshot.student_id)
            for parent_id in parent_ids:
                await self.send_message(
                    sender_id="system",
                    recipient_id=parent_id,
                    student_id=snapshot.student_id,
                    message_type=MessageType.ATTENDANCE,
                    subject="Attendance Alert",
                    content=f"Your child's attendance rate has dropped to {snapshot.attendance_rate:.0%}. Please contact the school if there are any concerns.",
                    priority=MessagePriority.HIGH
                )

    async def _save_parent(self, parent: Parent):
        """Save parent to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO parents
            (parent_id, name, email, phone, children_ids, notification_preferences,
             preferred_contact_time, language_preference, emergency_contact, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (parent.parent_id, parent.name, parent.email, parent.phone,
              json.dumps(parent.children_ids), json.dumps([pref.value for pref in parent.notification_preferences]),
              parent.preferred_contact_time, parent.language_preference,
              parent.emergency_contact, datetime.now()))
        
        conn.commit()
        conn.close()

    async def _save_teacher(self, teacher: Teacher):
        """Save teacher to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO teachers
            (teacher_id, name, email, phone, subjects, grade_levels, office_hours, students, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (teacher.teacher_id, teacher.name, teacher.email, teacher.phone,
              json.dumps(teacher.subjects), json.dumps(teacher.grade_levels),
              json.dumps(teacher.office_hours), json.dumps(teacher.students),
              datetime.now()))
        
        conn.commit()
        conn.close()

    async def _save_message(self, message: Message):
        """Save message to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO messages
            (message_id, sender_id, recipient_id, student_id, message_type, priority,
             subject, content, timestamp, read_status, parent_response, teacher_response,
             attachments, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (message.message_id, message.sender_id, message.recipient_id, message.student_id,
              message.message_type.value, message.priority.value, message.subject,
              message.content, message.timestamp, message.read_status,
              message.parent_response, message.teacher_response,
              json.dumps(message.attachments), json.dumps(message.metadata)))
        
        conn.commit()
        conn.close()

    async def _save_progress_report(self, report: ProgressReport):
        """Save progress report to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO progress_reports
            (report_id, student_id, teacher_id, report_period, academic_performance,
             behavioral_observations, achievements, areas_for_improvement,
             goals_next_period, teacher_comments, parent_feedback,
             generated_date, shared_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (report.report_id, report.student_id, report.teacher_id, report.report_period,
              json.dumps(report.academic_performance), json.dumps(report.behavioral_observations),
              json.dumps(report.achievements), json.dumps(report.areas_for_improvement),
              json.dumps(report.goals_next_period), report.teacher_comments,
              report.parent_feedback, report.generated_date, report.shared_date))
        
        conn.commit()
        conn.close()

    async def _save_conference(self, conference: Conference):
        """Save conference to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO conferences
            (conference_id, student_id, teacher_id, parent_id, conference_type,
             scheduled_time, duration, topic, agenda, status, meeting_link,
             location, notes, action_items, follow_up_required)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (conference.conference_id, conference.student_id, conference.teacher_id,
              conference.parent_id, conference.conference_type.value,
              conference.scheduled_time, conference.duration, conference.topic,
              json.dumps(conference.agenda), conference.status, conference.meeting_link,
              conference.location, conference.notes, json.dumps(conference.action_items),
              conference.follow_up_required))
        
        conn.commit()
        conn.close()

    async def _save_student_snapshot(self, snapshot: StudentSnapshot):
        """Save student snapshot to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO student_snapshots
            (student_id, snapshot_date, academic_summary, recent_assignments,
             attendance_rate, behavior_notes, upcoming_events, goals_progress)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (snapshot.student_id, snapshot.snapshot_date,
              json.dumps(snapshot.academic_summary), json.dumps(snapshot.recent_assignments),
              snapshot.attendance_rate, json.dumps(snapshot.behavior_notes),
              json.dumps(snapshot.upcoming_events), json.dumps(snapshot.goals_progress)))
        
        conn.commit()
        conn.close()

# Import numpy for random data generation
import numpy as np

async def demo_parent_teacher_portal():
    """Demonstrate parent-teacher communication portal"""
    portal = ParentTeacherPortal()
    
    print("=== Parent-Teacher Communication Portal Demo ===")
    
    # Register users
    parent = await portal.register_parent(
        "parent_susan",
        "Susan Johnson",
        "susan.johnson@email.com",
        "+1-555-0123",
        ["student_alex", "student_emma"],
        [NotificationPreference.EMAIL, NotificationPreference.SMS]
    )
    
    teacher = await portal.register_teacher(
        "teacher_smith",
        "Mr. Robert Smith",
        "r.smith@school.edu",
        "+1-555-0456",
        ["Mathematics", "Science"],
        [6, 7, 8],
        ["student_alex", "student_emma", "student_maya"]
    )
    
    print(f"Registered parent: {parent.name}")
    print(f"Registered teacher: {teacher.name}")
    
    # Send a message
    message = await portal.send_message(
        sender_id="teacher_smith",
        recipient_id="parent_susan",
        student_id="student_alex",
        message_type=MessageType.PROGRESS_UPDATE,
        subject="Great Progress in Mathematics",
        content="Alex has shown excellent improvement in algebraic thinking this week. He successfully completed all homework assignments and actively participated in class discussions. Keep up the great work!",
        priority=MessagePriority.NORMAL
    )
    
    print(f"\nMessage sent: {message.subject}")
    
    # Generate progress report
    progress_report = await portal.generate_progress_report(
        "student_alex",
        "teacher_smith",
        "Quarter 1"
    )
    
    print(f"\nProgress Report Generated:")
    print(f"Period: {progress_report.report_period}")
    print(f"Academic Performance: {len(progress_report.academic_performance)} subjects")
    print(f"Achievements: {len(progress_report.achievements)}")
    print(f"Teacher Comments: {progress_report.teacher_comments[:100]}...")
    
    # Schedule conference
    conference_time = datetime.now() + timedelta(days=7)
    conference = await portal.schedule_conference(
        "student_alex",
        "teacher_smith",
        "parent_susan",
        ConferenceType.VIRTUAL,
        conference_time,
        "Discuss Advanced Math Placement"
    )
    
    print(f"\nConference Scheduled:")
    print(f"Type: {conference.conference_type.value}")
    print(f"Time: {conference.scheduled_time}")
    print(f"Topic: {conference.topic}")
    print(f"Meeting Link: {conference.meeting_link}")
    print(f"Agenda Items: {len(conference.agenda)}")
    
    # Create student snapshot
    snapshot = await portal.create_student_snapshot("student_alex")
    
    print(f"\nStudent Snapshot Created:")
    print(f"Academic Summary: {snapshot.academic_summary}")
    print(f"Attendance Rate: {snapshot.attendance_rate:.1%}")
    print(f"Recent Assignments: {len(snapshot.recent_assignments)}")
    print(f"Upcoming Events: {len(snapshot.upcoming_events)}")
    print(f"Goals Progress: {len(snapshot.goals_progress)}")
    
    # Show behavior notes
    if snapshot.behavior_notes:
        print(f"Recent Positive Behaviors:")
        for note in snapshot.behavior_notes:
            print(f"  • {note}")

if __name__ == "__main__":
    asyncio.run(demo_parent_teacher_portal())