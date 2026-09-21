"""
Appointment Scheduling System
"""

import uuid
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from ..database import Appointment, BusinessHours, AppointmentStatus


class AppointmentScheduler:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
        # Default business configuration
        self.default_business_hours = {
            0: {"open": "09:00", "close": "17:00"},  # Monday
            1: {"open": "09:00", "close": "17:00"},  # Tuesday
            2: {"open": "09:00", "close": "17:00"},  # Wednesday
            3: {"open": "09:00", "close": "17:00"},  # Thursday
            4: {"open": "09:00", "close": "17:00"},  # Friday
            5: {"open": "10:00", "close": "14:00"},  # Saturday
            6: {"open": None, "close": None}        # Sunday (closed)
        }
        
        # Appointment types and their default durations
        self.appointment_types = {
            "consultation": {"duration": 60, "description": "General consultation"},
            "demo": {"duration": 45, "description": "Product demonstration"},
            "support": {"duration": 30, "description": "Technical support session"},
            "sales": {"duration": 30, "description": "Sales meeting"},
            "follow_up": {"duration": 15, "description": "Follow-up call"},
            "training": {"duration": 90, "description": "Training session"},
            "interview": {"duration": 60, "description": "Interview session"}
        }
        
        # Time slot intervals (in minutes)
        self.slot_interval = 15
        
        # Buffer time between appointments (in minutes)
        self.buffer_time = 5
    
    async def schedule_appointment(
        self,
        title: str,
        description: str,
        scheduled_date: datetime,
        duration_minutes: int,
        attendee_name: str,
        attendee_phone: str = None,
        attendee_email: str = None,
        appointment_type: str = "consultation",
        conversation_id: str = None
    ) -> Dict[str, Any]:
        """Schedule a new appointment"""
        
        # Validate appointment time
        validation = await self.validate_appointment_time(scheduled_date, duration_minutes)
        if not validation["is_valid"]:
            return {
                "success": False,
                "error": validation["reason"],
                "suggested_times": await self.get_next_available_slots(scheduled_date, duration_minutes, 3)
            }
        
        # Check for conflicts
        conflicts = await self.check_appointment_conflicts(scheduled_date, duration_minutes)
        if conflicts:
            return {
                "success": False,
                "error": "Time slot conflicts with existing appointment",
                "conflicting_appointments": conflicts,
                "suggested_times": await self.get_next_available_slots(scheduled_date, duration_minutes, 3)
            }
        
        # Create appointment
        appointment = Appointment(
            title=title,
            description=description,
            scheduled_date=scheduled_date,
            duration_minutes=duration_minutes,
            attendee_name=attendee_name,
            attendee_phone=attendee_phone,
            attendee_email=attendee_email,
            appointment_type=appointment_type,
            status=AppointmentStatus.SCHEDULED,
            conversation_id=uuid.UUID(conversation_id) if conversation_id else None
        )
        
        self.db.add(appointment)
        await self.db.commit()
        
        # Schedule reminders (would integrate with notification system)
        await self._schedule_appointment_reminders(appointment)
        
        return {
            "success": True,
            "appointment_id": str(appointment.id),
            "scheduled_date": scheduled_date.isoformat(),
            "confirmation_details": {
                "title": title,
                "date": scheduled_date.strftime("%Y-%m-%d"),
                "time": scheduled_date.strftime("%H:%M"),
                "duration": f"{duration_minutes} minutes",
                "type": appointment_type,
                "attendee": attendee_name
            }
        }
    
    async def check_availability(
        self,
        date: datetime,
        duration_minutes: int = 30,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """Check availability for appointment scheduling"""
        
        available_slots = []
        end_date = date + timedelta(days=days_ahead)
        
        current_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current_date <= end_date:
            daily_slots = await self._get_available_slots_for_date(current_date, duration_minutes)
            if daily_slots:
                available_slots.extend(daily_slots)
            
            current_date += timedelta(days=1)
        
        return {
            "requested_duration": duration_minutes,
            "search_period": f"{date.date()} to {end_date.date()}",
            "total_available_slots": len(available_slots),
            "next_available": available_slots[0] if available_slots else None,
            "available_slots": available_slots[:20],  # Limit to first 20 slots
            "daily_breakdown": await self._get_daily_availability_breakdown(date, days_ahead)
        }
    
    async def get_appointment_details(self, appointment_id: str) -> Dict[str, Any]:
        """Get detailed information about an appointment"""
        
        stmt = select(Appointment).where(Appointment.id == uuid.UUID(appointment_id))
        result = await self.db.execute(stmt)
        appointment = result.scalar_one_or_none()
        
        if not appointment:
            return {"error": "Appointment not found"}
        
        return {
            "appointment_id": str(appointment.id),
            "title": appointment.title,
            "description": appointment.description,
            "scheduled_date": appointment.scheduled_date.isoformat(),
            "duration_minutes": appointment.duration_minutes,
            "status": appointment.status.value,
            "attendee_info": {
                "name": appointment.attendee_name,
                "phone": appointment.attendee_phone,
                "email": appointment.attendee_email
            },
            "appointment_type": appointment.appointment_type,
            "location": appointment.location,
            "notes": appointment.notes,
            "reminder_sent": appointment.reminder_sent,
            "confirmation_sent": appointment.confirmation_sent,
            "created_at": appointment.created_at.isoformat()
        }
    
    async def reschedule_appointment(
        self,
        appointment_id: str,
        new_date: datetime,
        new_duration: int = None
    ) -> Dict[str, Any]:
        """Reschedule an existing appointment"""
        
        # Get existing appointment
        stmt = select(Appointment).where(Appointment.id == uuid.UUID(appointment_id))
        result = await self.db.execute(stmt)
        appointment = result.scalar_one_or_none()
        
        if not appointment:
            return {"success": False, "error": "Appointment not found"}
        
        duration = new_duration or appointment.duration_minutes
        
        # Validate new time
        validation = await self.validate_appointment_time(new_date, duration)
        if not validation["is_valid"]:
            return {
                "success": False,
                "error": validation["reason"],
                "suggested_times": await self.get_next_available_slots(new_date, duration, 3)
            }
        
        # Check for conflicts (excluding current appointment)
        conflicts = await self.check_appointment_conflicts(new_date, duration, exclude_appointment_id=appointment_id)
        if conflicts:
            return {
                "success": False,
                "error": "New time slot conflicts with existing appointment",
                "suggested_times": await self.get_next_available_slots(new_date, duration, 3)
            }
        
        # Update appointment
        old_date = appointment.scheduled_date
        stmt = update(Appointment).where(
            Appointment.id == uuid.UUID(appointment_id)
        ).values(
            scheduled_date=new_date,
            duration_minutes=duration,
            status=AppointmentStatus.RESCHEDULED,
            reminder_sent=False,
            confirmation_sent=False
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "old_date": old_date.isoformat(),
            "new_date": new_date.isoformat(),
            "message": "Appointment successfully rescheduled"
        }
    
    async def cancel_appointment(
        self,
        appointment_id: str,
        reason: str = None
    ) -> Dict[str, Any]:
        """Cancel an appointment"""
        
        stmt = update(Appointment).where(
            Appointment.id == uuid.UUID(appointment_id)
        ).values(
            status=AppointmentStatus.CANCELLED,
            notes=Appointment.notes.op('||')(f" | Cancelled: {reason or 'No reason provided'}")
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        if result.rowcount == 0:
            return {"success": False, "error": "Appointment not found"}
        
        return {
            "success": True,
            "appointment_id": appointment_id,
            "status": "cancelled",
            "message": "Appointment successfully cancelled"
        }
    
    async def get_upcoming_appointments(
        self,
        days_ahead: int = 7,
        attendee_email: str = None,
        attendee_phone: str = None
    ) -> List[Dict[str, Any]]:
        """Get upcoming appointments"""
        
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=days_ahead)
        
        stmt = select(Appointment).where(
            and_(
                Appointment.scheduled_date >= start_date,
                Appointment.scheduled_date <= end_date,
                Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
            )
        )
        
        if attendee_email:
            stmt = stmt.where(Appointment.attendee_email == attendee_email)
        if attendee_phone:
            stmt = stmt.where(Appointment.attendee_phone == attendee_phone)
        
        stmt = stmt.order_by(Appointment.scheduled_date)
        
        result = await self.db.execute(stmt)
        appointments = result.scalars().all()
        
        upcoming = []
        for appointment in appointments:
            upcoming.append({
                "appointment_id": str(appointment.id),
                "title": appointment.title,
                "scheduled_date": appointment.scheduled_date.isoformat(),
                "duration_minutes": appointment.duration_minutes,
                "attendee_name": appointment.attendee_name,
                "appointment_type": appointment.appointment_type,
                "status": appointment.status.value,
                "time_until": self._calculate_time_until(appointment.scheduled_date)
            })
        
        return upcoming
    
    async def validate_appointment_time(
        self,
        scheduled_date: datetime,
        duration_minutes: int
    ) -> Dict[str, Any]:
        """Validate if appointment time is acceptable"""
        
        now = datetime.utcnow()
        
        # Check if appointment is in the past
        if scheduled_date <= now:
            return {
                "is_valid": False,
                "reason": "Cannot schedule appointments in the past"
            }
        
        # Check if too far in the future (e.g., more than 6 months)
        if scheduled_date > now + timedelta(days=180):
            return {
                "is_valid": False,
                "reason": "Cannot schedule appointments more than 6 months in advance"
            }
        
        # Check if within business hours
        business_hours_check = await self._is_within_business_hours(scheduled_date)
        if not business_hours_check["is_valid"]:
            return {
                "is_valid": False,
                "reason": business_hours_check["reason"]
            }
        
        # Check duration
        if duration_minutes < 15:
            return {
                "is_valid": False,
                "reason": "Minimum appointment duration is 15 minutes"
            }
        
        if duration_minutes > 240:  # 4 hours
            return {
                "is_valid": False,
                "reason": "Maximum appointment duration is 4 hours"
            }
        
        return {"is_valid": True, "reason": "Valid appointment time"}
    
    async def check_appointment_conflicts(
        self,
        scheduled_date: datetime,
        duration_minutes: int,
        exclude_appointment_id: str = None
    ) -> List[Dict[str, Any]]:
        """Check for appointment conflicts"""
        
        start_time = scheduled_date
        end_time = scheduled_date + timedelta(minutes=duration_minutes)
        
        # Add buffer time
        buffer_start = start_time - timedelta(minutes=self.buffer_time)
        buffer_end = end_time + timedelta(minutes=self.buffer_time)
        
        stmt = select(Appointment).where(
            and_(
                Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
                or_(
                    and_(
                        Appointment.scheduled_date <= buffer_start,
                        Appointment.scheduled_date + timedelta(minutes=Appointment.duration_minutes) >= buffer_start
                    ),
                    and_(
                        Appointment.scheduled_date <= buffer_end,
                        Appointment.scheduled_date + timedelta(minutes=Appointment.duration_minutes) >= buffer_end
                    ),
                    and_(
                        Appointment.scheduled_date >= buffer_start,
                        Appointment.scheduled_date <= buffer_end
                    )
                )
            )
        )
        
        if exclude_appointment_id:
            stmt = stmt.where(Appointment.id != uuid.UUID(exclude_appointment_id))
        
        result = await self.db.execute(stmt)
        conflicting_appointments = result.scalars().all()
        
        conflicts = []
        for appointment in conflicting_appointments:
            conflicts.append({
                "appointment_id": str(appointment.id),
                "title": appointment.title,
                "scheduled_date": appointment.scheduled_date.isoformat(),
                "duration_minutes": appointment.duration_minutes,
                "attendee_name": appointment.attendee_name
            })
        
        return conflicts
    
    async def get_next_available_slots(
        self,
        preferred_date: datetime,
        duration_minutes: int,
        num_slots: int = 5
    ) -> List[Dict[str, Any]]:
        """Get next available appointment slots"""
        
        available_slots = []
        current_date = preferred_date.replace(minute=0, second=0, microsecond=0)
        
        # Search up to 30 days ahead
        search_limit = current_date + timedelta(days=30)
        
        while len(available_slots) < num_slots and current_date < search_limit:
            daily_slots = await self._get_available_slots_for_date(current_date, duration_minutes)
            
            for slot in daily_slots:
                if len(available_slots) >= num_slots:
                    break
                
                if slot["start_time"] > datetime.utcnow():  # Only future slots
                    available_slots.append(slot)
            
            current_date += timedelta(days=1)
        
        return available_slots
    
    # Private helper methods
    async def _get_available_slots_for_date(
        self,
        date: datetime,
        duration_minutes: int
    ) -> List[Dict[str, Any]]:
        """Get available slots for a specific date"""
        
        day_of_week = date.weekday()
        business_hours = self.default_business_hours.get(day_of_week)
        
        if not business_hours or not business_hours["open"]:
            return []  # Closed on this day
        
        # Parse business hours
        open_time = datetime.strptime(business_hours["open"], "%H:%M").time()
        close_time = datetime.strptime(business_hours["close"], "%H:%M").time()
        
        # Create datetime objects for the day
        day_start = datetime.combine(date.date(), open_time)
        day_end = datetime.combine(date.date(), close_time)
        
        # Get existing appointments for the day
        stmt = select(Appointment).where(
            and_(
                Appointment.scheduled_date >= day_start,
                Appointment.scheduled_date < day_start + timedelta(days=1),
                Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
            )
        ).order_by(Appointment.scheduled_date)
        
        result = await self.db.execute(stmt)
        existing_appointments = result.scalars().all()
        
        # Generate time slots
        available_slots = []
        current_time = day_start
        
        while current_time + timedelta(minutes=duration_minutes) <= day_end:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            # Check if slot conflicts with existing appointments
            is_available = True
            for appointment in existing_appointments:
                apt_start = appointment.scheduled_date
                apt_end = apt_start + timedelta(minutes=appointment.duration_minutes)
                
                # Add buffer time
                buffer_start = apt_start - timedelta(minutes=self.buffer_time)
                buffer_end = apt_end + timedelta(minutes=self.buffer_time)
                
                if not (slot_end <= buffer_start or current_time >= buffer_end):
                    is_available = False
                    break
            
            if is_available:
                available_slots.append({
                    "start_time": current_time,
                    "end_time": slot_end,
                    "date": current_time.strftime("%Y-%m-%d"),
                    "time": current_time.strftime("%H:%M"),
                    "duration_minutes": duration_minutes
                })
            
            current_time += timedelta(minutes=self.slot_interval)
        
        return available_slots
    
    async def _is_within_business_hours(self, scheduled_date: datetime) -> Dict[str, Any]:
        """Check if appointment is within business hours"""
        
        day_of_week = scheduled_date.weekday()
        business_hours = self.default_business_hours.get(day_of_week)
        
        if not business_hours or not business_hours["open"]:
            return {
                "is_valid": False,
                "reason": "We are closed on this day"
            }
        
        appointment_time = scheduled_date.time()
        open_time = datetime.strptime(business_hours["open"], "%H:%M").time()
        close_time = datetime.strptime(business_hours["close"], "%H:%M").time()
        
        if appointment_time < open_time or appointment_time >= close_time:
            return {
                "is_valid": False,
                "reason": f"Outside business hours ({business_hours['open']}-{business_hours['close']})"
            }
        
        return {"is_valid": True, "reason": "Within business hours"}
    
    async def _get_daily_availability_breakdown(
        self,
        start_date: datetime,
        days_ahead: int
    ) -> Dict[str, Dict[str, Any]]:
        """Get daily availability breakdown"""
        
        daily_breakdown = {}
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(days_ahead + 1):
            date_key = current_date.strftime("%Y-%m-%d")
            daily_slots = await self._get_available_slots_for_date(current_date, 30)  # 30-minute slots
            
            daily_breakdown[date_key] = {
                "date": date_key,
                "day_of_week": current_date.strftime("%A"),
                "total_slots": len(daily_slots),
                "first_available": daily_slots[0]["time"] if daily_slots else None,
                "last_available": daily_slots[-1]["time"] if daily_slots else None
            }
            
            current_date += timedelta(days=1)
        
        return daily_breakdown
    
    def _calculate_time_until(self, scheduled_date: datetime) -> str:
        """Calculate time until appointment"""
        
        now = datetime.utcnow()
        time_diff = scheduled_date - now
        
        if time_diff.total_seconds() < 0:
            return "Past appointment"
        
        days = time_diff.days
        hours, remainder = divmod(time_diff.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"In {days} days, {hours} hours"
        elif hours > 0:
            return f"In {hours} hours, {minutes} minutes"
        else:
            return f"In {minutes} minutes"
    
    async def _schedule_appointment_reminders(self, appointment: Appointment):
        """Schedule appointment reminders (mock implementation)"""
        
        # In production, this would integrate with notification systems
        # to send reminders 24 hours and 1 hour before appointment
        print(f"Reminders scheduled for appointment {appointment.id}")
        
        return {
            "reminder_24h": True,
            "reminder_1h": True,
            "confirmation_sent": True
        }