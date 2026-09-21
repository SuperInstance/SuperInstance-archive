"""
Player scheduling and availability tracking service.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, time
import uuid
from itertools import combinations
import math

try:
    from icalendar import Calendar, Event
    ICALENDAR_AVAILABLE = True
except ImportError:
    ICALENDAR_AVAILABLE = False
    logging.warning("iCalendar not available - calendar export disabled")

from ..config import Config
from ..models.scheduling import (
    AvailabilitySlot, SchedulingPreferences, SessionInvite, SchedulingSuggestion,
    AvailabilityAnalysis, CalendarIntegration, RecurrenceRule, TimeRange,
    AvailabilityStatus
)
from ..models.session import SessionSchema

logger = logging.getLogger(__name__)

class AvailabilityTracker:
    """Service for tracking player availability."""
    
    def __init__(self):
        # In-memory storage - would be database in production
        self.availability_slots: Dict[str, List[AvailabilitySlot]] = {}
        self.preferences: Dict[str, SchedulingPreferences] = {}
        self.calendar_integrations: Dict[str, CalendarIntegration] = {}
    
    async def set_availability(
        self,
        user_id: str,
        time_ranges: List[TimeRange],
        status: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
        recurring: bool = False,
        recurrence_rule: Optional[RecurrenceRule] = None,
        notes: Optional[str] = None
    ) -> List[AvailabilitySlot]:
        """Set availability for a user."""
        
        if user_id not in self.availability_slots:
            self.availability_slots[user_id] = []
        
        new_slots = []
        
        for time_range in time_ranges:
            # Create base slot
            slot = AvailabilitySlot(
                user_id=user_id,
                time_range=time_range,
                status=status,
                recurring=recurring,
                recurrence_rule=recurrence_rule,
                notes=notes
            )
            
            new_slots.append(slot)
            
            # Generate recurring slots if needed
            if recurring and recurrence_rule:
                recurring_slots = self._generate_recurring_slots(slot, recurrence_rule)
                new_slots.extend(recurring_slots)
        
        # Remove overlapping slots for the same user
        self.availability_slots[user_id] = self._merge_overlapping_slots(
            self.availability_slots[user_id] + new_slots
        )
        
        logger.info(f"Set availability for user {user_id}: {len(new_slots)} slots")
        return new_slots
    
    def get_user_availability(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AvailabilitySlot]:
        """Get availability slots for a user."""
        
        if user_id not in self.availability_slots:
            return []
        
        slots = self.availability_slots[user_id]
        
        # Filter by date range if provided
        if start_date or end_date:
            filtered_slots = []
            for slot in slots:
                slot_start = slot.time_range.start_time
                slot_end = slot.time_range.end_time
                
                # Check if slot overlaps with requested range
                if start_date and slot_end < start_date:
                    continue
                if end_date and slot_start > end_date:
                    continue
                
                filtered_slots.append(slot)
            
            slots = filtered_slots
        
        return sorted(slots, key=lambda x: x.time_range.start_time)
    
    def get_group_availability(
        self,
        user_ids: List[str],
        start_date: datetime,
        end_date: datetime,
        min_duration_minutes: int = 180
    ) -> Dict[str, List[AvailabilitySlot]]:
        """Get availability for multiple users."""
        
        group_availability = {}
        
        for user_id in user_ids:
            availability = self.get_user_availability(user_id, start_date, end_date)
            
            # Filter by minimum duration
            filtered_availability = []
            for slot in availability:
                duration_minutes = slot.time_range.duration().total_seconds() / 60
                if duration_minutes >= min_duration_minutes:
                    filtered_availability.append(slot)
            
            group_availability[user_id] = filtered_availability
        
        return group_availability
    
    async def set_preferences(
        self,
        user_id: str,
        preferences: SchedulingPreferences
    ) -> SchedulingPreferences:
        """Set scheduling preferences for a user."""
        
        preferences.user_id = user_id
        preferences.updated_at = datetime.utcnow()
        
        self.preferences[user_id] = preferences
        
        logger.info(f"Updated scheduling preferences for user {user_id}")
        return preferences
    
    def get_preferences(self, user_id: str) -> Optional[SchedulingPreferences]:
        """Get scheduling preferences for a user."""
        return self.preferences.get(user_id)
    
    def _generate_recurring_slots(
        self,
        base_slot: AvailabilitySlot,
        recurrence_rule: RecurrenceRule
    ) -> List[AvailabilitySlot]:
        """Generate recurring availability slots."""
        
        slots = []
        current_date = base_slot.time_range.start_time
        
        # Generate slots based on frequency
        for i in range(1, recurrence_rule.count or 52):  # Default to 1 year
            if recurrence_rule.frequency == "weekly":
                next_date = current_date + timedelta(weeks=recurrence_rule.interval)
            elif recurrence_rule.frequency == "daily":
                next_date = current_date + timedelta(days=recurrence_rule.interval)
            elif recurrence_rule.frequency == "monthly":
                # Approximate monthly recurrence
                next_date = current_date + timedelta(days=30 * recurrence_rule.interval)
            else:
                break
            
            # Check if we've exceeded the until date
            if recurrence_rule.until and next_date > recurrence_rule.until:
                break
            
            # Check for exceptions
            if next_date.date() in [exc.date() for exc in recurrence_rule.exceptions]:
                current_date = next_date
                continue
            
            # Create new slot
            duration = base_slot.time_range.duration()
            new_time_range = TimeRange(
                start_time=next_date,
                end_time=next_date + duration,
                timezone=base_slot.time_range.timezone
            )
            
            new_slot = AvailabilitySlot(
                user_id=base_slot.user_id,
                time_range=new_time_range,
                status=base_slot.status,
                recurring=True,
                recurrence_rule=recurrence_rule,
                notes=base_slot.notes
            )
            
            slots.append(new_slot)
            current_date = next_date
        
        return slots
    
    def _merge_overlapping_slots(
        self,
        slots: List[AvailabilitySlot]
    ) -> List[AvailabilitySlot]:
        """Merge overlapping availability slots."""
        
        if not slots:
            return slots
        
        # Sort by start time
        sorted_slots = sorted(slots, key=lambda x: x.time_range.start_time)
        
        merged = [sorted_slots[0]]
        
        for current in sorted_slots[1:]:
            last_merged = merged[-1]
            
            # Check if current overlaps with last merged
            if (current.time_range.start_time <= last_merged.time_range.end_time and
                current.status == last_merged.status):
                
                # Merge by extending the end time
                merged_end = max(
                    current.time_range.end_time,
                    last_merged.time_range.end_time
                )
                
                last_merged.time_range.end_time = merged_end
            else:
                # No overlap, add as separate slot
                merged.append(current)
        
        return merged

class SchedulingOptimizer:
    """Service for finding optimal meeting times."""
    
    def __init__(self, config: Config):
        self.config = config
    
    async def find_optimal_times(
        self,
        user_ids: List[str],
        availability_tracker: AvailabilityTracker,
        duration_minutes: int,
        start_date: datetime,
        end_date: datetime,
        max_suggestions: int = 10
    ) -> List[SchedulingSuggestion]:
        """Find optimal meeting times for a group."""
        
        # Get availability for all users
        group_availability = availability_tracker.get_group_availability(
            user_ids, start_date, end_date, duration_minutes
        )
        
        # Find overlapping time slots
        overlapping_slots = self._find_overlapping_slots(
            group_availability, duration_minutes
        )
        
        # Generate and score suggestions
        suggestions = []
        
        for overlap in overlapping_slots:
            suggestion = self._create_suggestion(
                overlap, user_ids, availability_tracker
            )
            suggestions.append(suggestion)
        
        # Sort by score and return top suggestions
        suggestions.sort(key=lambda x: x.score, reverse=True)
        
        return suggestions[:max_suggestions]
    
    def _find_overlapping_slots(
        self,
        group_availability: Dict[str, List[AvailabilitySlot]],
        duration_minutes: int
    ) -> List[Dict[str, Any]]:
        """Find time slots where multiple users are available."""
        
        overlaps = []
        user_ids = list(group_availability.keys())
        
        if not user_ids:
            return overlaps
        
        # Get all possible time slots from first user as base
        base_user = user_ids[0]
        base_slots = group_availability[base_user]
        
        for base_slot in base_slots:
            # Find overlaps with other users
            overlap_info = {
                "time_range": base_slot.time_range,
                "available_users": [base_user],
                "maybe_users": [],
                "unavailable_users": []
            }
            
            # Check each other user
            for user_id in user_ids[1:]:
                user_slots = group_availability.get(user_id, [])
                
                user_overlap = self._find_user_overlap(
                    base_slot.time_range, user_slots, duration_minutes
                )
                
                if user_overlap["status"] == "available":
                    overlap_info["available_users"].append(user_id)
                elif user_overlap["status"] == "maybe":
                    overlap_info["maybe_users"].append(user_id)
                else:
                    overlap_info["unavailable_users"].append(user_id)
            
            # Only include if at least 50% of users are available
            availability_ratio = len(overlap_info["available_users"]) / len(user_ids)
            if availability_ratio >= 0.5:
                overlaps.append(overlap_info)
        
        return overlaps
    
    def _find_user_overlap(
        self,
        target_range: TimeRange,
        user_slots: List[AvailabilitySlot],
        duration_minutes: int
    ) -> Dict[str, Any]:
        """Find if user has availability overlapping with target range."""
        
        for slot in user_slots:
            if target_range.overlaps_with(slot.time_range):
                # Calculate overlap duration
                overlap_start = max(target_range.start_time, slot.time_range.start_time)
                overlap_end = min(target_range.end_time, slot.time_range.end_time)
                overlap_duration = (overlap_end - overlap_start).total_seconds() / 60
                
                if overlap_duration >= duration_minutes:
                    return {
                        "status": slot.status.value,
                        "overlap_duration": overlap_duration,
                        "slot": slot
                    }
        
        return {"status": "unavailable"}
    
    def _create_suggestion(
        self,
        overlap_info: Dict[str, Any],
        all_user_ids: List[str],
        availability_tracker: AvailabilityTracker
    ) -> SchedulingSuggestion:
        """Create a scheduling suggestion from overlap information."""
        
        time_range = overlap_info["time_range"]
        
        # Calculate score based on multiple factors
        score = self._calculate_suggestion_score(
            overlap_info, all_user_ids, availability_tracker
        )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(overlap_info, all_user_ids)
        
        suggestion = SchedulingSuggestion(
            time_range=time_range,
            confidence=min(1.0, score),
            available_participants=overlap_info["available_users"],
            maybe_participants=overlap_info["maybe_users"],
            unavailable_participants=overlap_info["unavailable_users"],
            reasoning=reasoning,
            score=score
        )
        
        return suggestion
    
    def _calculate_suggestion_score(
        self,
        overlap_info: Dict[str, Any],
        all_user_ids: List[str],
        availability_tracker: AvailabilityTracker
    ) -> float:
        """Calculate quality score for a scheduling suggestion."""
        
        total_users = len(all_user_ids)
        available_users = len(overlap_info["available_users"])
        maybe_users = len(overlap_info["maybe_users"])
        
        # Base score from availability ratio
        availability_score = (available_users + 0.5 * maybe_users) / total_users
        
        # Time preference score
        time_preference_score = self._calculate_time_preference_score(
            overlap_info["time_range"], overlap_info["available_users"], availability_tracker
        )
        
        # Duration score (longer available time is better)
        duration_hours = overlap_info["time_range"].duration().total_seconds() / 3600
        duration_score = min(1.0, duration_hours / 4)  # 4 hours = perfect
        
        # Combine scores
        final_score = (
            availability_score * 0.5 +
            time_preference_score * 0.3 +
            duration_score * 0.2
        )
        
        return min(1.0, final_score)
    
    def _calculate_time_preference_score(
        self,
        time_range: TimeRange,
        user_ids: List[str],
        availability_tracker: AvailabilityTracker
    ) -> float:
        """Calculate how well this time matches user preferences."""
        
        if not user_ids:
            return 0.5
        
        preference_scores = []
        
        for user_id in user_ids:
            preferences = availability_tracker.get_preferences(user_id)
            if not preferences:
                preference_scores.append(0.5)  # Neutral if no preferences
                continue
            
            user_score = 0.0
            
            # Check preferred days
            weekday = time_range.start_time.weekday()  # 0 = Monday
            if weekday in preferences.preferred_days:
                user_score += 0.5
            
            # Check preferred times
            start_time = time_range.start_time.time()
            for pref_range in preferences.preferred_time_ranges:
                pref_start = pref_range.start_time.time()
                pref_end = pref_range.end_time.time()
                
                if pref_start <= start_time <= pref_end:
                    user_score += 0.5
                    break
            
            preference_scores.append(min(1.0, user_score))
        
        return sum(preference_scores) / len(preference_scores)
    
    def _generate_reasoning(
        self,
        overlap_info: Dict[str, Any],
        all_user_ids: List[str]
    ) -> str:
        """Generate human-readable reasoning for suggestion."""
        
        total_users = len(all_user_ids)
        available_users = len(overlap_info["available_users"])
        maybe_users = len(overlap_info["maybe_users"])
        unavailable_users = len(overlap_info["unavailable_users"])
        
        reasoning_parts = []
        
        # Availability summary
        if available_users == total_users:
            reasoning_parts.append("All participants are available")
        elif available_users > total_users * 0.8:
            reasoning_parts.append(f"Most participants ({available_users}/{total_users}) are available")
        else:
            reasoning_parts.append(f"{available_users}/{total_users} participants confirmed available")
        
        # Maybe participants
        if maybe_users > 0:
            reasoning_parts.append(f"{maybe_users} participants marked as maybe")
        
        # Time quality
        time_range = overlap_info["time_range"]
        duration_hours = time_range.duration().total_seconds() / 3600
        
        if duration_hours >= 4:
            reasoning_parts.append("Good duration for full session")
        elif duration_hours >= 2:
            reasoning_parts.append("Adequate duration for session")
        else:
            reasoning_parts.append("Short time window")
        
        # Day of week
        day_name = time_range.start_time.strftime("%A")
        reasoning_parts.append(f"Scheduled for {day_name}")
        
        return ". ".join(reasoning_parts) + "."

class NotificationService:
    """Service for sending scheduling notifications."""
    
    def __init__(self, config: Config):
        self.config = config
    
    async def send_session_invite(
        self,
        invite: SessionInvite,
        recipient_preferences: Optional[SchedulingPreferences] = None
    ) -> bool:
        """Send session invitation notification."""
        
        # In production, this would integrate with email/SMS/push notification services
        logger.info(f"Sending session invite to user {invite.user_id}")
        
        # Simulate notification methods
        methods = recipient_preferences.notification_methods if recipient_preferences else ["email"]
        
        for method in methods:
            await self._send_notification(invite, method)
        
        return True
    
    async def send_reminder(
        self,
        session: SessionSchema,
        user_id: str,
        reminder_type: str,  # "24h", "1h", "15m"
        preferences: Optional[SchedulingPreferences] = None
    ) -> bool:
        """Send session reminder notification."""
        
        logger.info(f"Sending {reminder_type} reminder for session {session.id} to user {user_id}")
        
        # Would implement actual notification sending here
        return True
    
    async def _send_notification(
        self,
        invite: SessionInvite,
        method: str
    ) -> bool:
        """Send notification via specific method."""
        
        # Placeholder for actual notification implementation
        if method == "email":
            logger.info(f"Sending email notification for invite {invite.id}")
        elif method == "sms":
            logger.info(f"Sending SMS notification for invite {invite.id}")
        elif method == "push":
            logger.info(f"Sending push notification for invite {invite.id}")
        elif method == "discord":
            logger.info(f"Sending Discord notification for invite {invite.id}")
        
        return True

class SchedulingService:
    """Main scheduling service."""
    
    def __init__(self, config: Config):
        self.config = config
        self.availability_tracker = AvailabilityTracker()
        self.optimizer = SchedulingOptimizer(config)
        self.notification_service = NotificationService(config)
        
        # Session invites storage
        self.session_invites: Dict[str, List[SessionInvite]] = {}
    
    async def set_user_availability(
        self,
        user_id: str,
        time_ranges: List[TimeRange],
        status: AvailabilityStatus = AvailabilityStatus.AVAILABLE,
        recurring: bool = False,
        recurrence_rule: Optional[RecurrenceRule] = None,
        notes: Optional[str] = None
    ) -> List[AvailabilitySlot]:
        """Set availability for a user."""
        
        return await self.availability_tracker.set_availability(
            user_id, time_ranges, status, recurring, recurrence_rule, notes
        )
    
    async def find_meeting_times(
        self,
        participant_ids: List[str],
        duration_minutes: int,
        earliest_date: Optional[datetime] = None,
        latest_date: Optional[datetime] = None,
        max_suggestions: int = 10
    ) -> List[SchedulingSuggestion]:
        """Find optimal meeting times for participants."""
        
        if not earliest_date:
            earliest_date = datetime.utcnow()
        
        if not latest_date:
            latest_date = earliest_date + timedelta(days=14)  # Default 2 weeks
        
        suggestions = await self.optimizer.find_optimal_times(
            participant_ids,
            self.availability_tracker,
            duration_minutes,
            earliest_date,
            latest_date,
            max_suggestions
        )
        
        logger.info(f"Found {len(suggestions)} scheduling suggestions")
        return suggestions
    
    async def create_session_invites(
        self,
        session: SessionSchema,
        participant_ids: List[str],
        dm_user_id: str,
        send_notifications: bool = True
    ) -> List[SessionInvite]:
        """Create and send session invitations."""
        
        invites = []
        
        for user_id in participant_ids:
            # Determine role
            role = "dm" if user_id == dm_user_id else "player"
            
            invite = SessionInvite(
                session_id=session.id,
                user_id=user_id,
                role=role,
                sent_by=dm_user_id,
                response_deadline=session.scheduled_start - timedelta(hours=24)
            )
            
            invites.append(invite)
            
            # Send notification if requested
            if send_notifications:
                preferences = self.availability_tracker.get_preferences(user_id)
                await self.notification_service.send_session_invite(invite, preferences)
        
        # Store invites
        if session.id not in self.session_invites:
            self.session_invites[session.id] = []
        
        self.session_invites[session.id].extend(invites)
        
        logger.info(f"Created {len(invites)} session invites for session {session.id}")
        return invites
    
    async def respond_to_invite(
        self,
        invite_id: str,
        response: str,  # "accepted", "declined", "maybe"
        response_note: Optional[str] = None
    ) -> Optional[SessionInvite]:
        """Respond to a session invitation."""
        
        # Find invite
        invite = None
        for session_invites in self.session_invites.values():
            invite = next((inv for inv in session_invites if inv.id == invite_id), None)
            if invite:
                break
        
        if not invite:
            return None
        
        # Update invite
        invite.status = response
        invite.responded_at = datetime.utcnow()
        invite.response_note = response_note
        
        logger.info(f"User {invite.user_id} {response} invite {invite_id}")
        return invite
    
    def get_session_invites(self, session_id: str) -> List[SessionInvite]:
        """Get all invites for a session."""
        return self.session_invites.get(session_id, [])
    
    def analyze_group_availability(
        self,
        user_ids: List[str],
        time_window_days: int = 14
    ) -> AvailabilityAnalysis:
        """Analyze availability patterns for a group."""
        
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=time_window_days)
        
        # Get all availability data
        group_availability = self.availability_tracker.get_group_availability(
            user_ids, start_date, end_date, 180  # Minimum 3 hours
        )
        
        # Calculate statistics
        total_hours = 0
        day_counts = [0] * 7  # Monday = 0
        hour_counts = [0] * 24
        user_availability_hours = {}
        
        for user_id, slots in group_availability.items():
            user_hours = 0
            for slot in slots:
                duration_hours = slot.time_range.duration().total_seconds() / 3600
                user_hours += duration_hours
                total_hours += duration_hours
                
                # Track day patterns
                day_counts[slot.time_range.start_time.weekday()] += 1
                
                # Track hour patterns
                hour_counts[slot.time_range.start_time.hour] += 1
            
            user_availability_hours[user_id] = user_hours
        
        # Find optimal times
        optimal_slots = []
        # This would implement complex optimization logic
        
        # Calculate difficulty
        avg_availability = total_hours / len(user_ids) if user_ids else 0
        if avg_availability > 20:  # 20+ hours per week
            difficulty = "easy"
        elif avg_availability > 10:
            difficulty = "moderate"
        elif avg_availability > 5:
            difficulty = "hard"
        else:
            difficulty = "very_hard"
        
        # Get timezone spread
        timezones = set()
        for user_id in user_ids:
            preferences = self.availability_tracker.get_preferences(user_id)
            if preferences:
                timezones.add(preferences.timezone)
        
        analysis = AvailabilityAnalysis(
            participant_count=len(user_ids),
            total_availability_hours=total_hours,
            optimal_times=optimal_slots,
            best_days=[i for i, count in enumerate(day_counts) if count == max(day_counts)],
            best_hours=[i for i, count in enumerate(hour_counts) if count == max(hour_counts)],
            recommended_duration=240,  # 4 hours default
            recommended_frequency="weekly",
            scheduling_difficulty=difficulty,
            average_availability_per_participant=avg_availability,
            timezone_spread=len(timezones)
        )
        
        return analysis
    
    async def export_calendar(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        format_type: str = "ics"
    ) -> Optional[str]:
        """Export user's availability as calendar format."""
        
        if not ICALENDAR_AVAILABLE or format_type.lower() != "ics":
            return None
        
        # Get user availability
        availability = self.availability_tracker.get_user_availability(
            user_id, start_date, end_date
        )
        
        # Create calendar
        cal = Calendar()
        cal.add('prodid', '-//DMLog Session Scheduler//EN')
        cal.add('version', '2.0')
        
        for slot in availability:
            event = Event()
            event.add('summary', f'Available for D&D Session ({slot.status.value})')
            event.add('dtstart', slot.time_range.start_time)
            event.add('dtend', slot.time_range.end_time)
            event.add('description', slot.notes or f'Availability: {slot.status.value}')
            
            if slot.status == AvailabilityStatus.AVAILABLE:
                event.add('status', 'CONFIRMED')
            elif slot.status == AvailabilityStatus.MAYBE:
                event.add('status', 'TENTATIVE')
            else:
                event.add('status', 'CANCELLED')
            
            cal.add_component(event)
        
        return cal.to_ical().decode('utf-8')
    
    async def schedule_reminders(
        self,
        session: SessionSchema,
        reminder_times: List[int] = None  # Minutes before session
    ) -> int:
        """Schedule reminder notifications for a session."""
        
        if not reminder_times:
            reminder_times = [1440, 60, 15]  # 24h, 1h, 15m default
        
        reminders_scheduled = 0
        
        for participant in session.participants:
            preferences = self.availability_tracker.get_preferences(participant.user_id)
            
            # Use user preferences if available, otherwise use defaults
            user_reminder_times = (
                preferences.reminder_times if preferences else reminder_times
            )
            
            for minutes_before in user_reminder_times:
                reminder_time = session.scheduled_start - timedelta(minutes=minutes_before)
                
                # Only schedule future reminders
                if reminder_time > datetime.utcnow():
                    # In production, this would schedule actual notifications
                    logger.info(
                        f"Scheduled reminder for {participant.user_id} "
                        f"{minutes_before} minutes before session {session.id}"
                    )
                    reminders_scheduled += 1
        
        return reminders_scheduled