"""
Medication Reminder System for ActiveLog Health Suite
Smart medication management with reminders, tracking, and adherence monitoring
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta, time
import json
from abc import ABC, abstractmethod
import uuid

logger = logging.getLogger(__name__)

class MedicationType(Enum):
    """Types of medications"""
    PRESCRIPTION = "prescription"
    OVER_THE_COUNTER = "over_the_counter"
    SUPPLEMENT = "supplement"
    VITAMIN = "vitamin"
    HERBAL = "herbal"
    INJECTION = "injection"
    INHALER = "inhaler"
    TOPICAL = "topical"
    EYE_DROPS = "eye_drops"
    PATCH = "patch"

class DosageForm(Enum):
    """Forms of medication dosage"""
    TABLET = "tablet"
    CAPSULE = "capsule"
    LIQUID = "liquid"
    INJECTION = "injection"
    CREAM = "cream"
    OINTMENT = "ointment"
    SPRAY = "spray"
    PATCH = "patch"
    DROPS = "drops"
    INHALER = "inhaler"
    POWDER = "powder"

class FrequencyType(Enum):
    """Medication frequency types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    AS_NEEDED = "as_needed"
    SPECIFIC_DAYS = "specific_days"
    INTERVAL = "interval"  # Every X hours
    CUSTOM = "custom"

class ReminderStatus(Enum):
    """Status of medication reminders"""
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    TAKEN = "taken"
    MISSED = "missed"
    SKIPPED = "skipped"
    DELAYED = "delayed"

class AdherenceLevel(Enum):
    """Medication adherence levels"""
    EXCELLENT = "excellent"    # >95%
    GOOD = "good"             # 85-95%
    FAIR = "fair"             # 70-84%
    POOR = "poor"             # <70%

class InteractionSeverity(Enum):
    """Drug interaction severity levels"""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    SEVERE = "severe"

@dataclass
class Medication:
    """Medication definition"""
    medication_id: str
    name: str
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None
    medication_type: MedicationType = MedicationType.PRESCRIPTION
    dosage_form: DosageForm = DosageForm.TABLET
    strength: str = ""  # e.g., "500mg", "10mg/ml"
    ndc_number: Optional[str] = None  # National Drug Code
    instructions: str = ""
    side_effects: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)
    storage_requirements: str = "Room temperature"
    manufacturer: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class MedicationSchedule:
    """Medication dosing schedule"""
    schedule_id: str
    medication_id: str
    user_id: str
    dosage: str  # Amount per dose
    frequency_type: FrequencyType
    times_per_day: Optional[int] = None
    specific_times: List[time] = field(default_factory=list)
    specific_days: List[str] = field(default_factory=list)  # Days of week
    interval_hours: Optional[int] = None
    start_date: datetime = field(default_factory=datetime.now)
    end_date: Optional[datetime] = None
    with_food: Optional[bool] = None
    special_instructions: str = ""
    is_active: bool = True
    prescriber: Optional[str] = None
    pharmacy: Optional[str] = None

@dataclass
class MedicationReminder:
    """Individual medication reminder"""
    reminder_id: str
    schedule_id: str
    user_id: str
    medication_name: str
    dosage: str
    scheduled_time: datetime
    status: ReminderStatus = ReminderStatus.PENDING
    sent_time: Optional[datetime] = None
    acknowledged_time: Optional[datetime] = None
    taken_time: Optional[datetime] = None
    notes: str = ""
    snooze_count: int = 0
    max_snoozes: int = 3
    snooze_minutes: int = 15

@dataclass
class MedicationLog:
    """Log of medication taking"""
    log_id: str
    schedule_id: str
    user_id: str
    medication_name: str
    dosage: str
    scheduled_time: datetime
    actual_time: Optional[datetime] = None
    taken: bool = False
    missed_reason: Optional[str] = None
    side_effects_noted: List[str] = field(default_factory=list)
    effectiveness_rating: Optional[int] = None  # 1-10 scale
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class AdherenceReport:
    """Medication adherence analysis"""
    user_id: str
    medication_id: str
    period_start: datetime
    period_end: datetime
    scheduled_doses: int
    taken_doses: int
    missed_doses: int
    adherence_percentage: float
    adherence_level: AdherenceLevel
    missed_patterns: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

@dataclass
class DrugInteraction:
    """Drug interaction information"""
    interaction_id: str
    medication1_id: str
    medication2_id: str
    medication1_name: str
    medication2_name: str
    severity: InteractionSeverity
    description: str
    mechanism: str = ""
    clinical_significance: str = ""
    management: str = ""
    references: List[str] = field(default_factory=list)

class NotificationProvider(ABC):
    """Abstract notification provider"""
    
    @abstractmethod
    async def send_notification(self, user_id: str, message: str, title: str = "") -> bool:
        """Send notification to user"""
        pass

class SMSNotificationProvider(NotificationProvider):
    """SMS notification provider"""
    
    async def send_notification(self, user_id: str, message: str, title: str = "") -> bool:
        """Send SMS notification"""
        # This would integrate with SMS service like Twilio
        logger.info(f"SMS to {user_id}: {title} - {message}")
        return True

class PushNotificationProvider(NotificationProvider):
    """Push notification provider"""
    
    async def send_notification(self, user_id: str, message: str, title: str = "") -> bool:
        """Send push notification"""
        # This would integrate with push notification service
        logger.info(f"Push to {user_id}: {title} - {message}")
        return True

class EmailNotificationProvider(NotificationProvider):
    """Email notification provider"""
    
    async def send_notification(self, user_id: str, message: str, title: str = "") -> bool:
        """Send email notification"""
        # This would integrate with email service
        logger.info(f"Email to {user_id}: {title} - {message}")
        return True

class MedicationReminderSystem:
    """Comprehensive medication reminder and management system"""
    
    def __init__(self):
        self.medications: Dict[str, Medication] = {}
        self.schedules: Dict[str, MedicationSchedule] = {}
        self.reminders: Dict[str, MedicationReminder] = {}
        self.logs: Dict[str, List[MedicationLog]] = {}
        self.interactions: Dict[str, List[DrugInteraction]] = {}
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
        
        # Notification providers
        self.notification_providers: Dict[str, NotificationProvider] = {
            'sms': SMSNotificationProvider(),
            'push': PushNotificationProvider(),
            'email': EmailNotificationProvider()
        }
        
        # Background tasks
        self.reminder_tasks: Dict[str, asyncio.Task] = {}
        
        # Start reminder scheduler
        asyncio.create_task(self._reminder_scheduler())
        asyncio.create_task(self._adherence_monitor())
    
    async def add_medication(self, medication: Medication) -> str:
        """Add a new medication to the database"""
        try:
            # Check for duplicates
            existing = self._find_existing_medication(medication.name, medication.strength)
            if existing:
                logger.warning(f"Medication {medication.name} already exists: {existing}")
                return existing
            
            # Store medication
            self.medications[medication.medication_id] = medication
            
            logger.info(f"Added medication: {medication.name} ({medication.medication_id})")
            return medication.medication_id
            
        except Exception as e:
            logger.error(f"Failed to add medication {medication.name}: {e}")
            raise
    
    async def create_medication_schedule(self, schedule: MedicationSchedule) -> str:
        """Create a medication dosing schedule"""
        try:
            # Validate medication exists
            if schedule.medication_id not in self.medications:
                raise ValueError(f"Medication {schedule.medication_id} not found")
            
            # Validate schedule parameters
            await self._validate_schedule(schedule)
            
            # Store schedule
            self.schedules[schedule.schedule_id] = schedule
            
            # Initialize user logs
            if schedule.user_id not in self.logs:
                self.logs[schedule.user_id] = []
            
            # Check for drug interactions
            await self._check_drug_interactions(schedule.user_id)
            
            # Start reminder task for this schedule
            await self._start_schedule_reminders(schedule)
            
            logger.info(f"Created medication schedule: {schedule.schedule_id}")
            return schedule.schedule_id
            
        except Exception as e:
            logger.error(f"Failed to create medication schedule: {e}")
            raise
    
    async def _validate_schedule(self, schedule: MedicationSchedule):
        """Validate medication schedule parameters"""
        if schedule.frequency_type == FrequencyType.DAILY:
            if not schedule.specific_times and not schedule.times_per_day:
                raise ValueError("Daily schedule requires specific times or times per day")
        
        elif schedule.frequency_type == FrequencyType.INTERVAL:
            if not schedule.interval_hours:
                raise ValueError("Interval schedule requires interval hours")
        
        elif schedule.frequency_type == FrequencyType.SPECIFIC_DAYS:
            if not schedule.specific_days or not schedule.specific_times:
                raise ValueError("Specific days schedule requires days and times")
    
    async def _start_schedule_reminders(self, schedule: MedicationSchedule):
        """Start reminder task for medication schedule"""
        
        async def reminder_loop():
            while schedule.is_active:
                try:
                    # Calculate next reminder time
                    next_reminder_time = await self._calculate_next_reminder(schedule)
                    
                    if next_reminder_time is None:
                        break
                    
                    # Wait until reminder time
                    now = datetime.now()
                    if next_reminder_time > now:
                        wait_seconds = (next_reminder_time - now).total_seconds()
                        await asyncio.sleep(wait_seconds)
                    
                    # Create and send reminder
                    await self._create_and_send_reminder(schedule, next_reminder_time)
                    
                    # Wait a bit before calculating next reminder
                    await asyncio.sleep(60)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Reminder loop error for schedule {schedule.schedule_id}: {e}")
                    await asyncio.sleep(300)  # Wait 5 minutes on error
        
        task = asyncio.create_task(reminder_loop())
        self.reminder_tasks[schedule.schedule_id] = task
    
    async def _calculate_next_reminder(self, schedule: MedicationSchedule) -> Optional[datetime]:
        """Calculate the next reminder time for a schedule"""
        
        now = datetime.now()
        
        if schedule.end_date and now > schedule.end_date:
            return None
        
        if schedule.frequency_type == FrequencyType.DAILY:
            if schedule.specific_times:
                # Find next occurrence of any scheduled time
                today = now.date()
                next_times = []
                
                for scheduled_time in schedule.specific_times:
                    # Today's occurrence
                    today_occurrence = datetime.combine(today, scheduled_time)
                    if today_occurrence > now:
                        next_times.append(today_occurrence)
                    
                    # Tomorrow's occurrence
                    tomorrow_occurrence = datetime.combine(today + timedelta(days=1), scheduled_time)
                    next_times.append(tomorrow_occurrence)
                
                return min(next_times) if next_times else None
            
            elif schedule.times_per_day:
                # Distribute evenly throughout the day
                interval_hours = 24 / schedule.times_per_day
                
                # Find next interval
                today_start = datetime.combine(now.date(), time(6, 0))  # Start at 6 AM
                
                for i in range(schedule.times_per_day):
                    reminder_time = today_start + timedelta(hours=i * interval_hours)
                    if reminder_time > now:
                        return reminder_time
                
                # Next day
                tomorrow_start = today_start + timedelta(days=1)
                return tomorrow_start
        
        elif schedule.frequency_type == FrequencyType.INTERVAL:
            # Find last taken time or start from now
            last_log = self._get_last_medication_log(schedule.user_id, schedule.schedule_id)
            
            if last_log and last_log.actual_time:
                next_time = last_log.actual_time + timedelta(hours=schedule.interval_hours)
            else:
                next_time = now + timedelta(hours=schedule.interval_hours)
            
            return next_time
        
        elif schedule.frequency_type == FrequencyType.SPECIFIC_DAYS:
            # Find next occurrence on specified days
            current_weekday = now.strftime('%A')
            
            # Check today first
            if current_weekday in schedule.specific_days:
                for scheduled_time in schedule.specific_times:
                    today_occurrence = datetime.combine(now.date(), scheduled_time)
                    if today_occurrence > now:
                        return today_occurrence
            
            # Check next 7 days
            for days_ahead in range(1, 8):
                future_date = now.date() + timedelta(days=days_ahead)
                future_weekday = future_date.strftime('%A')
                
                if future_weekday in schedule.specific_days:
                    first_time = min(schedule.specific_times)
                    return datetime.combine(future_date, first_time)
        
        elif schedule.frequency_type == FrequencyType.WEEKLY:
            # Weekly reminders (simplified - same day/time each week)
            if schedule.specific_times and schedule.specific_days:
                target_day = schedule.specific_days[0]  # First specified day
                target_time = schedule.specific_times[0]  # First specified time
                
                # Find next occurrence
                days_until_target = (
                    list(calendar.day_name).index(target_day) - now.weekday()
                ) % 7
                
                if days_until_target == 0:  # Today
                    today_occurrence = datetime.combine(now.date(), target_time)
                    if today_occurrence > now:
                        return today_occurrence
                    days_until_target = 7  # Next week
                
                target_date = now.date() + timedelta(days=days_until_target)
                return datetime.combine(target_date, target_time)
        
        return None
    
    async def _create_and_send_reminder(self, schedule: MedicationSchedule, reminder_time: datetime):
        """Create and send a medication reminder"""
        
        try:
            medication = self.medications[schedule.medication_id]
            
            # Create reminder
            reminder = MedicationReminder(
                reminder_id=str(uuid.uuid4()),
                schedule_id=schedule.schedule_id,
                user_id=schedule.user_id,
                medication_name=medication.name,
                dosage=schedule.dosage,
                scheduled_time=reminder_time
            )
            
            # Store reminder
            self.reminders[reminder.reminder_id] = reminder
            
            # Get user preferences
            prefs = self.user_preferences.get(schedule.user_id, {})
            notification_methods = prefs.get('notification_methods', ['push'])
            
            # Prepare message
            title = "Medication Reminder"
            message = f"Time to take {medication.name} ({schedule.dosage})"
            
            if schedule.with_food is not None:
                message += " with food" if schedule.with_food else " on empty stomach"
            
            if schedule.special_instructions:
                message += f". {schedule.special_instructions}"
            
            # Send notifications
            notification_sent = False
            for method in notification_methods:
                if method in self.notification_providers:
                    try:
                        success = await self.notification_providers[method].send_notification(
                            schedule.user_id, message, title
                        )
                        if success:
                            notification_sent = True
                    except Exception as e:
                        logger.warning(f"Failed to send {method} notification: {e}")
            
            # Update reminder status
            if notification_sent:
                reminder.status = ReminderStatus.SENT
                reminder.sent_time = datetime.now()
            
            # Schedule follow-up if not acknowledged
            asyncio.create_task(self._schedule_follow_up(reminder))
            
            logger.info(f"Created reminder for {medication.name} at {reminder_time}")
            
        except Exception as e:
            logger.error(f"Failed to create reminder: {e}")
    
    async def _schedule_follow_up(self, reminder: MedicationReminder):
        """Schedule follow-up reminders if medication not taken"""
        
        # Wait for initial response window (30 minutes)
        await asyncio.sleep(1800)
        
        # Check if reminder was handled
        current_reminder = self.reminders.get(reminder.reminder_id)
        if not current_reminder or current_reminder.status in [ReminderStatus.TAKEN, ReminderStatus.SKIPPED]:
            return
        
        # Send follow-up reminders
        for i in range(3):  # Up to 3 follow-ups
            if current_reminder.status != ReminderStatus.PENDING:
                break
            
            # Send follow-up
            message = f"Reminder: You haven't confirmed taking {current_reminder.medication_name}"
            
            prefs = self.user_preferences.get(current_reminder.user_id, {})
            notification_methods = prefs.get('notification_methods', ['push'])
            
            for method in notification_methods:
                if method in self.notification_providers:
                    await self.notification_providers[method].send_notification(
                        current_reminder.user_id, message, "Medication Follow-up"
                    )
            
            # Wait before next follow-up
            await asyncio.sleep(600)  # 10 minutes
        
        # Mark as missed if still not acknowledged
        if current_reminder.status == ReminderStatus.PENDING:
            current_reminder.status = ReminderStatus.MISSED
            await self._log_medication_event(current_reminder, taken=False, missed_reason="No response")
    
    async def acknowledge_reminder(self, reminder_id: str, user_id: str) -> bool:
        """User acknowledges receiving a reminder"""
        
        if reminder_id not in self.reminders:
            return False
        
        reminder = self.reminders[reminder_id]
        
        if reminder.user_id != user_id:
            return False
        
        reminder.status = ReminderStatus.ACKNOWLEDGED
        reminder.acknowledged_time = datetime.now()
        
        logger.info(f"Reminder acknowledged: {reminder_id}")
        return True
    
    async def confirm_medication_taken(
        self,
        reminder_id: str,
        user_id: str,
        actual_time: Optional[datetime] = None,
        notes: str = "",
        side_effects: Optional[List[str]] = None,
        effectiveness_rating: Optional[int] = None
    ) -> bool:
        """User confirms they took their medication"""
        
        if reminder_id not in self.reminders:
            return False
        
        reminder = self.reminders[reminder_id]
        
        if reminder.user_id != user_id:
            return False
        
        # Update reminder
        reminder.status = ReminderStatus.TAKEN
        reminder.taken_time = actual_time or datetime.now()
        reminder.notes = notes
        
        # Log the medication event
        await self._log_medication_event(
            reminder,
            taken=True,
            actual_time=actual_time,
            notes=notes,
            side_effects=side_effects or [],
            effectiveness_rating=effectiveness_rating
        )
        
        logger.info(f"Medication taken confirmed: {reminder_id}")
        return True
    
    async def skip_medication(
        self,
        reminder_id: str,
        user_id: str,
        reason: str = ""
    ) -> bool:
        """User skips a medication dose"""
        
        if reminder_id not in self.reminders:
            return False
        
        reminder = self.reminders[reminder_id]
        
        if reminder.user_id != user_id:
            return False
        
        reminder.status = ReminderStatus.SKIPPED
        reminder.notes = reason
        
        # Log as skipped
        await self._log_medication_event(
            reminder,
            taken=False,
            missed_reason=f"Intentionally skipped: {reason}"
        )
        
        logger.info(f"Medication skipped: {reminder_id} - {reason}")
        return True
    
    async def snooze_reminder(
        self,
        reminder_id: str,
        user_id: str,
        snooze_minutes: Optional[int] = None
    ) -> bool:
        """Snooze a medication reminder"""
        
        if reminder_id not in self.reminders:
            return False
        
        reminder = self.reminders[reminder_id]
        
        if reminder.user_id != user_id or reminder.snooze_count >= reminder.max_snoozes:
            return False
        
        # Update snooze info
        reminder.snooze_count += 1
        snooze_time = snooze_minutes or reminder.snooze_minutes
        
        # Schedule snoozed reminder
        async def snoozed_reminder():
            await asyncio.sleep(snooze_time * 60)
            
            # Send reminder again if still pending
            if reminder.status == ReminderStatus.PENDING:
                prefs = self.user_preferences.get(user_id, {})
                notification_methods = prefs.get('notification_methods', ['push'])
                
                message = f"Snoozed reminder: Time to take {reminder.medication_name} ({reminder.dosage})"
                
                for method in notification_methods:
                    if method in self.notification_providers:
                        await self.notification_providers[method].send_notification(
                            user_id, message, "Medication Reminder"
                        )
        
        asyncio.create_task(snoozed_reminder())
        
        logger.info(f"Reminder snoozed: {reminder_id} for {snooze_time} minutes")
        return True
    
    async def _log_medication_event(
        self,
        reminder: MedicationReminder,
        taken: bool,
        actual_time: Optional[datetime] = None,
        missed_reason: Optional[str] = None,
        notes: str = "",
        side_effects: Optional[List[str]] = None,
        effectiveness_rating: Optional[int] = None
    ):
        """Log a medication taking event"""
        
        log = MedicationLog(
            log_id=str(uuid.uuid4()),
            schedule_id=reminder.schedule_id,
            user_id=reminder.user_id,
            medication_name=reminder.medication_name,
            dosage=reminder.dosage,
            scheduled_time=reminder.scheduled_time,
            actual_time=actual_time,
            taken=taken,
            missed_reason=missed_reason,
            side_effects_noted=side_effects or [],
            effectiveness_rating=effectiveness_rating,
            notes=notes
        )
        
        # Add to user's log
        if reminder.user_id not in self.logs:
            self.logs[reminder.user_id] = []
        
        self.logs[reminder.user_id].append(log)
        
        logger.info(f"Logged medication event: {log.log_id}")
    
    def _get_last_medication_log(self, user_id: str, schedule_id: str) -> Optional[MedicationLog]:
        """Get the last log entry for a specific medication schedule"""
        
        if user_id not in self.logs:
            return None
        
        user_logs = [log for log in self.logs[user_id] if log.schedule_id == schedule_id]
        
        if not user_logs:
            return None
        
        return max(user_logs, key=lambda x: x.scheduled_time)
    
    async def _check_drug_interactions(self, user_id: str):
        """Check for drug interactions for a user"""
        
        # Get all active medications for user
        user_schedules = [s for s in self.schedules.values() 
                         if s.user_id == user_id and s.is_active]
        
        if len(user_schedules) < 2:
            return
        
        # Clear existing interactions for user
        if user_id in self.interactions:
            self.interactions[user_id] = []
        else:
            self.interactions[user_id] = []
        
        # Check all pairs
        for i, schedule1 in enumerate(user_schedules):
            for schedule2 in user_schedules[i+1:]:
                interaction = await self._check_interaction_pair(schedule1, schedule2)
                if interaction:
                    self.interactions[user_id].append(interaction)
        
        # Notify user of significant interactions
        significant_interactions = [
            i for i in self.interactions[user_id] 
            if i.severity in [InteractionSeverity.MAJOR, InteractionSeverity.SEVERE]
        ]
        
        if significant_interactions:
            await self._notify_drug_interactions(user_id, significant_interactions)
    
    async def _check_interaction_pair(
        self,
        schedule1: MedicationSchedule,
        schedule2: MedicationSchedule
    ) -> Optional[DrugInteraction]:
        """Check for interaction between two medications"""
        
        # This would integrate with a drug interaction database
        # For now, simulate some common interactions
        
        med1 = self.medications[schedule1.medication_id]
        med2 = self.medications[schedule2.medication_id]
        
        # Simplified interaction rules (in practice, use a comprehensive database)
        known_interactions = {
            ('warfarin', 'aspirin'): {
                'severity': InteractionSeverity.MAJOR,
                'description': 'Increased risk of bleeding',
                'management': 'Monitor INR closely and watch for signs of bleeding'
            },
            ('lisinopril', 'potassium'): {
                'severity': InteractionSeverity.MODERATE,
                'description': 'Risk of hyperkalemia',
                'management': 'Monitor serum potassium levels'
            }
        }
        
        # Check both directions
        key1 = (med1.name.lower(), med2.name.lower())
        key2 = (med2.name.lower(), med1.name.lower())
        
        interaction_info = known_interactions.get(key1) or known_interactions.get(key2)
        
        if interaction_info:
            return DrugInteraction(
                interaction_id=str(uuid.uuid4()),
                medication1_id=schedule1.medication_id,
                medication2_id=schedule2.medication_id,
                medication1_name=med1.name,
                medication2_name=med2.name,
                severity=interaction_info['severity'],
                description=interaction_info['description'],
                management=interaction_info['management']
            )
        
        return None
    
    async def _notify_drug_interactions(self, user_id: str, interactions: List[DrugInteraction]):
        """Notify user of drug interactions"""
        
        prefs = self.user_preferences.get(user_id, {})
        notification_methods = prefs.get('notification_methods', ['push'])
        
        for interaction in interactions:
            message = f"Drug Interaction Alert: {interaction.medication1_name} and {interaction.medication2_name}. {interaction.description}"
            
            for method in notification_methods:
                if method in self.notification_providers:
                    await self.notification_providers[method].send_notification(
                        user_id, message, "Drug Interaction Alert"
                    )
    
    async def generate_adherence_report(
        self,
        user_id: str,
        medication_id: Optional[str] = None,
        days: int = 30
    ) -> List[AdherenceReport]:
        """Generate medication adherence report"""
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            reports = []
            
            # Get schedules to analyze
            if medication_id:
                schedules_to_analyze = [s for s in self.schedules.values() 
                                     if s.user_id == user_id and s.medication_id == medication_id]
            else:
                schedules_to_analyze = [s for s in self.schedules.values() 
                                     if s.user_id == user_id and s.is_active]
            
            for schedule in schedules_to_analyze:
                # Get logs for this schedule in the time period
                schedule_logs = [
                    log for log in self.logs.get(user_id, [])
                    if (log.schedule_id == schedule.schedule_id and 
                        start_date <= log.scheduled_time <= end_date)
                ]
                
                if not schedule_logs:
                    continue
                
                # Calculate adherence
                total_scheduled = len(schedule_logs)
                taken_doses = len([log for log in schedule_logs if log.taken])
                missed_doses = total_scheduled - taken_doses
                
                adherence_percentage = (taken_doses / total_scheduled * 100) if total_scheduled > 0 else 0
                
                # Classify adherence level
                if adherence_percentage >= 95:
                    adherence_level = AdherenceLevel.EXCELLENT
                elif adherence_percentage >= 85:
                    adherence_level = AdherenceLevel.GOOD
                elif adherence_percentage >= 70:
                    adherence_level = AdherenceLevel.FAIR
                else:
                    adherence_level = AdherenceLevel.POOR
                
                # Analyze missed patterns
                missed_patterns = self._analyze_missed_patterns(schedule_logs)
                
                # Generate recommendations
                recommendations = self._generate_adherence_recommendations(
                    adherence_level, missed_patterns
                )
                
                report = AdherenceReport(
                    user_id=user_id,
                    medication_id=schedule.medication_id,
                    period_start=start_date,
                    period_end=end_date,
                    scheduled_doses=total_scheduled,
                    taken_doses=taken_doses,
                    missed_doses=missed_doses,
                    adherence_percentage=adherence_percentage,
                    adherence_level=adherence_level,
                    missed_patterns=missed_patterns,
                    recommendations=recommendations
                )
                
                reports.append(report)
            
            logger.info(f"Generated {len(reports)} adherence reports for user {user_id}")
            return reports
            
        except Exception as e:
            logger.error(f"Failed to generate adherence report for user {user_id}: {e}")
            return []
    
    def _analyze_missed_patterns(self, logs: List[MedicationLog]) -> Dict[str, Any]:
        """Analyze patterns in missed medications"""
        
        missed_logs = [log for log in logs if not log.taken]
        
        if not missed_logs:
            return {}
        
        patterns = {}
        
        # Time of day pattern
        missed_hours = [log.scheduled_time.hour for log in missed_logs]
        if missed_hours:
            most_missed_hour = max(set(missed_hours), key=missed_hours.count)
            patterns['most_missed_time'] = f"{most_missed_hour:02d}:00"
        
        # Day of week pattern
        missed_weekdays = [log.scheduled_time.strftime('%A') for log in missed_logs]
        if missed_weekdays:
            most_missed_day = max(set(missed_weekdays), key=missed_weekdays.count)
            patterns['most_missed_day'] = most_missed_day
        
        # Consecutive misses
        consecutive_count = 0
        max_consecutive = 0
        
        for log in sorted(logs, key=lambda x: x.scheduled_time):
            if not log.taken:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 0
        
        patterns['max_consecutive_misses'] = max_consecutive
        
        return patterns
    
    def _generate_adherence_recommendations(
        self,
        adherence_level: AdherenceLevel,
        missed_patterns: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on adherence patterns"""
        
        recommendations = []
        
        if adherence_level == AdherenceLevel.EXCELLENT:
            recommendations.append("Great job maintaining excellent medication adherence!")
            recommendations.append("Continue your current routine")
        
        elif adherence_level == AdherenceLevel.GOOD:
            recommendations.append("Good adherence! Small improvements could help reach excellent levels")
            
            if missed_patterns.get('most_missed_time'):
                recommendations.append(f"Consider setting an additional reminder for {missed_patterns['most_missed_time']}")
        
        elif adherence_level in [AdherenceLevel.FAIR, AdherenceLevel.POOR]:
            recommendations.append("Consider discussing adherence challenges with your healthcare provider")
            recommendations.append("Try using pill organizers or medication apps")
            
            if missed_patterns.get('most_missed_day'):
                recommendations.append(f"Pay extra attention to medication on {missed_patterns['most_missed_day']}")
            
            if missed_patterns.get('max_consecutive_misses', 0) > 2:
                recommendations.append("Try to avoid missing multiple doses in a row")
                recommendations.append("Set multiple reminder methods (phone, alarm, family member)")
        
        return recommendations
    
    async def set_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ):
        """Set user notification and reminder preferences"""
        
        self.user_preferences[user_id] = {
            **self.user_preferences.get(user_id, {}),
            **preferences
        }
        
        logger.info(f"Updated preferences for user {user_id}")
    
    async def _reminder_scheduler(self):
        """Background scheduler for medication reminders"""
        
        while True:
            try:
                # This runs the main reminder scheduling
                # Individual schedules handle their own timing
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Reminder scheduler error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _adherence_monitor(self):
        """Background monitor for medication adherence"""
        
        while True:
            try:
                # Run adherence analysis for all users daily
                await asyncio.sleep(86400)  # Run daily
                
                # Get all active users
                active_users = set(s.user_id for s in self.schedules.values() if s.is_active)
                
                for user_id in active_users:
                    # Generate weekly adherence report
                    reports = await self.generate_adherence_report(user_id, days=7)
                    
                    # Check for poor adherence and notify
                    poor_adherence = [r for r in reports if r.adherence_level == AdherenceLevel.POOR]
                    
                    if poor_adherence:
                        # Notify user about poor adherence
                        prefs = self.user_preferences.get(user_id, {})
                        notification_methods = prefs.get('notification_methods', ['push'])
                        
                        message = f"Your medication adherence is below 70% for {len(poor_adherence)} medication(s). Consider speaking with your healthcare provider."
                        
                        for method in notification_methods:
                            if method in self.notification_providers:
                                await self.notification_providers[method].send_notification(
                                    user_id, message, "Adherence Alert"
                                )
                
            except Exception as e:
                logger.error(f"Adherence monitor error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    def _find_existing_medication(self, name: str, strength: str) -> Optional[str]:
        """Find existing medication by name and strength"""
        
        for med_id, med in self.medications.items():
            if (med.name.lower() == name.lower() and 
                med.strength.lower() == strength.lower()):
                return med_id
        
        return None
    
    async def get_user_medications(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all medications for a user"""
        
        user_schedules = [s for s in self.schedules.values() 
                         if s.user_id == user_id and s.is_active]
        
        medications = []
        
        for schedule in user_schedules:
            medication = self.medications.get(schedule.medication_id)
            if medication:
                medications.append({
                    'schedule_id': schedule.schedule_id,
                    'medication': medication.__dict__,
                    'schedule': schedule.__dict__,
                    'next_dose': await self._calculate_next_reminder(schedule)
                })
        
        return medications
    
    async def get_user_reminders(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent and upcoming reminders for a user"""
        
        end_date = datetime.now() + timedelta(days=days)
        start_date = datetime.now() - timedelta(days=1)
        
        user_reminders = [
            r for r in self.reminders.values()
            if (r.user_id == user_id and 
                start_date <= r.scheduled_time <= end_date)
        ]
        
        return [r.__dict__ for r in sorted(user_reminders, key=lambda x: x.scheduled_time)]
    
    async def get_medication_logs(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get medication logs for a user"""
        
        if user_id not in self.logs:
            return []
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        recent_logs = [
            log for log in self.logs[user_id]
            if start_date <= log.scheduled_time <= end_date
        ]
        
        return [log.__dict__ for log in sorted(recent_logs, key=lambda x: x.scheduled_time, reverse=True)]

# Global singleton instance
medication_reminder_system = MedicationReminderSystem()