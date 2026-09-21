"""
Campaign management and timeline tracking service.
"""

from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from uuid import uuid4
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter

from models.campaign import (
    Campaign, CampaignEvent, GameSession, WorldCalendar,
    CampaignSchema, CampaignEventSchema, GameSessionSchema, WorldCalendarSchema,
    TimelineFilter, TimelineEntry, CampaignSummary, EventConnection,
    CampaignStatus, EventType, EventPriority
)

class TimelineManager:
    """Manages campaign timeline and event organization."""
    
    @staticmethod
    def create_timeline_entry(item: Any, entry_type: str) -> TimelineEntry:
        """Convert a session or event to a timeline entry."""
        if entry_type == "session":
            return TimelineEntry(
                type="session",
                id=item.id,
                title=item.title,
                description=item.summary,
                session_number=item.session_number,
                world_date=item.world_date_start,
                real_date=item.actual_date.date() if item.actual_date else None,
                location=item.locations_visited[0] if item.locations_visited else None,
                participants=item.character_ids,
                tags=["session"],
                event_type=EventType.SESSION
            )
        else:  # event
            return TimelineEntry(
                type="event",
                id=item.id,
                title=item.title,
                description=item.description,
                session_number=item.session_number,
                world_date=item.world_date,
                real_date=item.real_date,
                location=item.location,
                participants=item.participants,
                priority=EventPriority(item.priority),
                tags=item.tags,
                event_type=EventType(item.event_type)
            )
    
    @staticmethod
    def sort_timeline_entries(entries: List[TimelineEntry]) -> List[TimelineEntry]:
        """Sort timeline entries chronologically."""
        def sort_key(entry):
            # Primary sort by session number
            session_num = entry.session_number or 999999
            
            # Secondary sort by real date
            real_date = entry.real_date or date.max
            
            # Tertiary sort by priority for same session/date
            priority_order = {
                EventPriority.CRITICAL: 0,
                EventPriority.HIGH: 1,
                EventPriority.MEDIUM: 2,
                EventPriority.LOW: 3
            }
            priority = priority_order.get(entry.priority, 4)
            
            return (session_num, real_date, priority)
        
        return sorted(entries, key=sort_key)
    
    @staticmethod
    def filter_timeline_entries(entries: List[TimelineEntry], filters: TimelineFilter) -> List[TimelineEntry]:
        """Apply filters to timeline entries."""
        filtered = entries
        
        if filters.event_types:
            filtered = [e for e in filtered if e.event_type in filters.event_types]
        
        if filters.start_session:
            filtered = [e for e in filtered if not e.session_number or e.session_number >= filters.start_session]
        
        if filters.end_session:
            filtered = [e for e in filtered if not e.session_number or e.session_number <= filters.end_session]
        
        if filters.start_date:
            filtered = [e for e in filtered if not e.real_date or e.real_date >= filters.start_date]
        
        if filters.end_date:
            filtered = [e for e in filtered if not e.real_date or e.real_date <= filters.end_date]
        
        if filters.participants:
            filtered = [e for e in filtered if e.participants and any(p in e.participants for p in filters.participants)]
        
        if filters.locations:
            filtered = [e for e in filtered if e.location and e.location in filters.locations]
        
        if filters.tags:
            filtered = [e for e in filtered if e.tags and any(t in e.tags for t in filters.tags)]
        
        priority_order = {
            EventPriority.LOW: 0,
            EventPriority.MEDIUM: 1,
            EventPriority.HIGH: 2,
            EventPriority.CRITICAL: 3
        }
        min_priority = priority_order.get(filters.priority_min, 0)
        filtered = [e for e in filtered if priority_order.get(e.priority, 0) >= min_priority]
        
        return filtered

class WorldCalendarManager:
    """Manages world calendar and date progression."""
    
    @staticmethod
    def advance_date(calendar: WorldCalendar, days: int) -> Tuple[int, int, int]:
        """Advance the calendar by specified days and return new date."""
        current_day = calendar.current_day
        current_month = calendar.current_month
        current_year = calendar.current_year
        
        days_per_month = calendar.days_per_month
        
        remaining_days = days
        
        while remaining_days > 0:
            # Days remaining in current month
            days_in_current_month = days_per_month[current_month - 1]
            days_left_in_month = days_in_current_month - current_day + 1
            
            if remaining_days < days_left_in_month:
                # Advance within current month
                current_day += remaining_days
                remaining_days = 0
            else:
                # Move to next month
                remaining_days -= days_left_in_month
                current_day = 1
                current_month += 1
                
                if current_month > len(days_per_month):
                    current_month = 1
                    current_year += 1
        
        return current_year, current_month, current_day
    
    @staticmethod
    def format_date(calendar: WorldCalendar, year: int = None, month: int = None, day: int = None) -> str:
        """Format a date according to the world calendar."""
        year = year or calendar.current_year
        month = month or calendar.current_month
        day = day or calendar.current_day
        
        month_name = calendar.month_names[month - 1] if month <= len(calendar.month_names) else str(month)
        
        return f"{day} {month_name}, {year}"
    
    @staticmethod
    def calculate_days_between(calendar: WorldCalendar, 
                              year1: int, month1: int, day1: int,
                              year2: int, month2: int, day2: int) -> int:
        """Calculate days between two dates in the world calendar."""
        if year1 == year2 and month1 == month2:
            return abs(day2 - day1)
        
        # Simplified calculation - in a real implementation, this would be more precise
        days_per_year = sum(calendar.days_per_month)
        
        total_days1 = (year1 - 1) * days_per_year + sum(calendar.days_per_month[:month1-1]) + day1
        total_days2 = (year2 - 1) * days_per_year + sum(calendar.days_per_month[:month2-1]) + day2
        
        return abs(total_days2 - total_days1)

class CampaignAnalyzer:
    """Analyzes campaign data for insights and summaries."""
    
    @staticmethod
    def analyze_campaign_statistics(campaign: Campaign, sessions: List[GameSession], 
                                  events: List[CampaignEvent]) -> Dict[str, Any]:
        """Generate comprehensive campaign statistics."""
        stats = {
            "total_sessions": len(sessions),
            "total_events": len(events),
            "campaign_duration_days": 0,
            "total_experience_awarded": sum(s.experience_awarded for s in sessions),
            "average_session_duration": 0,
            "most_visited_locations": [],
            "most_encountered_npcs": [],
            "event_type_distribution": {},
            "session_frequency": {},
            "player_attendance": {}
        }
        
        if sessions:
            # Calculate duration statistics
            durations = [s.duration_minutes for s in sessions if s.duration_minutes]
            if durations:
                stats["average_session_duration"] = sum(durations) / len(durations)
            
            # Calculate campaign duration
            if campaign.start_date and sessions:
                last_session = max(sessions, key=lambda s: s.actual_date or datetime.min)
                if last_session.actual_date:
                    duration = (last_session.actual_date.date() - campaign.start_date).days
                    stats["campaign_duration_days"] = duration
            
            # Analyze locations
            location_counter = Counter()
            for session in sessions:
                if session.locations_visited:
                    location_counter.update(session.locations_visited)
            stats["most_visited_locations"] = location_counter.most_common(5)
            
            # Analyze NPCs
            npc_counter = Counter()
            for session in sessions:
                if session.npcs_encountered:
                    npc_counter.update(session.npcs_encountered)
            stats["most_encountered_npcs"] = npc_counter.most_common(5)
            
            # Analyze player attendance
            attendance = defaultdict(int)
            for session in sessions:
                if session.player_ids:
                    for player_id in session.player_ids:
                        attendance[player_id] += 1
            stats["player_attendance"] = dict(attendance)
        
        # Analyze event types
        event_type_counter = Counter(event.event_type for event in events)
        stats["event_type_distribution"] = dict(event_type_counter)
        
        return stats

class CampaignService:
    """Main campaign service handling database operations."""
    
    def __init__(self):
        self.timeline_manager = TimelineManager()
        self.calendar_manager = WorldCalendarManager()
        self.analyzer = CampaignAnalyzer()
    
    def create_campaign(self, campaign_data: CampaignSchema, db: Session) -> Campaign:
        """Create a new campaign."""
        campaign = Campaign(
            id=str(uuid4()),
            name=campaign_data.name,
            description=campaign_data.description,
            game_system=campaign_data.game_system,
            status=campaign_data.status.value,
            start_date=campaign_data.start_date,
            end_date=campaign_data.end_date,
            dm_id=campaign_data.dm_id,
            player_ids=campaign_data.player_ids,
            world_name=campaign_data.world_name,
            current_location=campaign_data.current_location,
            current_date_in_world=campaign_data.current_date_in_world,
            campaign_notes=campaign_data.campaign_notes,
            house_rules=campaign_data.house_rules,
            campaign_tags=campaign_data.campaign_tags
        )
        
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        return campaign
    
    def create_session(self, session_data: GameSessionSchema, db: Session) -> GameSession:
        """Create a new game session."""
        session = GameSession(
            id=str(uuid4()),
            campaign_id=session_data.campaign_id,
            session_number=session_data.session_number,
            title=session_data.title,
            summary=session_data.summary,
            scheduled_date=session_data.scheduled_date,
            actual_date=session_data.actual_date,
            duration_minutes=session_data.duration_minutes,
            dm_id=session_data.dm_id,
            player_ids=session_data.player_ids,
            character_ids=session_data.character_ids,
            locations_visited=session_data.locations_visited,
            npcs_encountered=session_data.npcs_encountered,
            monsters_fought=session_data.monsters_fought,
            treasure_found=session_data.treasure_found,
            experience_awarded=session_data.experience_awarded,
            milestones_achieved=session_data.milestones_achieved,
            dm_notes=session_data.dm_notes,
            player_notes=session_data.player_notes,
            memorable_quotes=session_data.memorable_quotes,
            world_date_start=session_data.world_date_start,
            world_date_end=session_data.world_date_end
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session
    
    def create_event(self, event_data: CampaignEventSchema, db: Session) -> CampaignEvent:
        """Create a new campaign event."""
        event = CampaignEvent(
            id=str(uuid4()),
            campaign_id=event_data.campaign_id,
            session_id=event_data.session_id,
            event_type=event_data.event_type.value,
            title=event_data.title,
            description=event_data.description,
            session_number=event_data.session_number,
            world_date=event_data.world_date,
            real_date=event_data.real_date,
            location=event_data.location,
            participants=event_data.participants,
            consequences=event_data.consequences,
            priority=event_data.priority.value,
            is_secret=event_data.is_secret,
            related_events=event_data.related_events,
            references=event_data.references,
            tags=event_data.tags,
            notes=event_data.notes
        )
        
        db.add(event)
        db.commit()
        db.refresh(event)
        
        return event
    
    def get_campaign_timeline(self, filters: TimelineFilter, db: Session) -> List[TimelineEntry]:
        """Get campaign timeline with filtering."""
        # Get sessions
        session_query = db.query(GameSession).filter(
            GameSession.campaign_id == filters.campaign_id
        )
        sessions = session_query.all()
        
        # Get events
        event_query = db.query(CampaignEvent).filter(
            CampaignEvent.campaign_id == filters.campaign_id
        )
        
        if not filters.include_secret:
            event_query = event_query.filter(CampaignEvent.is_secret == False)
        
        events = event_query.all()
        
        # Convert to timeline entries
        timeline_entries = []
        
        for session in sessions:
            entry = self.timeline_manager.create_timeline_entry(session, "session")
            timeline_entries.append(entry)
        
        for event in events:
            entry = self.timeline_manager.create_timeline_entry(event, "event")
            timeline_entries.append(entry)
        
        # Apply filters
        filtered_entries = self.timeline_manager.filter_timeline_entries(timeline_entries, filters)
        
        # Sort chronologically
        sorted_entries = self.timeline_manager.sort_timeline_entries(filtered_entries)
        
        return sorted_entries
    
    def create_world_calendar(self, calendar_data: WorldCalendarSchema, db: Session) -> WorldCalendar:
        """Create a world calendar for a campaign."""
        calendar = WorldCalendar(
            id=str(uuid4()),
            campaign_id=calendar_data.campaign_id,
            calendar_name=calendar_data.calendar_name,
            description=calendar_data.description,
            days_per_month=calendar_data.days_per_month,
            month_names=calendar_data.month_names,
            day_names=calendar_data.day_names,
            holidays=calendar_data.holidays,
            historical_events=calendar_data.historical_events,
            current_year=calendar_data.current_year,
            current_month=calendar_data.current_month,
            current_day=calendar_data.current_day,
            notes=calendar_data.notes
        )
        
        db.add(calendar)
        db.commit()
        db.refresh(calendar)
        
        return calendar
    
    def advance_world_date(self, campaign_id: str, days: int, db: Session) -> str:
        """Advance the world date for a campaign."""
        calendar = db.query(WorldCalendar).filter(
            WorldCalendar.campaign_id == campaign_id
        ).first()
        
        if not calendar:
            raise ValueError("No world calendar found for campaign")
        
        new_year, new_month, new_day = self.calendar_manager.advance_date(calendar, days)
        
        calendar.current_year = new_year
        calendar.current_month = new_month
        calendar.current_day = new_day
        
        db.commit()
        
        # Update campaign current date
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.current_date_in_world = self.calendar_manager.format_date(
                calendar, new_year, new_month, new_day
            )
            db.commit()
        
        return campaign.current_date_in_world
    
    def get_campaign_summary(self, campaign_id: str, db: Session) -> CampaignSummary:
        """Get comprehensive campaign summary."""
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError("Campaign not found")
        
        sessions = db.query(GameSession).filter(
            GameSession.campaign_id == campaign_id
        ).all()
        
        events = db.query(CampaignEvent).filter(
            CampaignEvent.campaign_id == campaign_id,
            CampaignEvent.is_secret == False
        ).all()
        
        # Get statistics
        stats = self.analyzer.analyze_campaign_statistics(campaign, sessions, events)
        
        # Get recent and upcoming events (last 5 and next 5)
        all_timeline = self.get_campaign_timeline(
            TimelineFilter(campaign_id=campaign_id, include_secret=False), db
        )
        
        recent_events = all_timeline[-5:] if len(all_timeline) > 5 else all_timeline
        upcoming_events = []  # Would be populated from scheduled future events
        
        # Calculate level range (would query character data)
        current_level_range = (1, 5)  # Placeholder
        active_characters = campaign.player_ids or []
        
        return CampaignSummary(
            campaign=CampaignSchema.from_orm(campaign),
            total_sessions=stats["total_sessions"],
            total_events=stats["total_events"],
            active_characters=active_characters,
            current_level_range=current_level_range,
            total_experience_awarded=stats["total_experience_awarded"],
            campaign_duration_days=stats["campaign_duration_days"],
            most_visited_locations=stats["most_visited_locations"],
            most_encountered_npcs=stats["most_encountered_npcs"],
            recent_events=recent_events,
            upcoming_events=upcoming_events
        )
    
    def find_related_events(self, event_id: str, db: Session) -> List[EventConnection]:
        """Find events related to the given event."""
        event = db.query(CampaignEvent).filter(CampaignEvent.id == event_id).first()
        if not event:
            return []
        
        connections = []
        
        # Direct relationships from event data
        if event.related_events:
            for related_id in event.related_events:
                connections.append(EventConnection(
                    from_event_id=event_id,
                    to_event_id=related_id,
                    connection_type="related_to",
                    weight=1.0
                ))
        
        # Find events with shared participants
        if event.participants:
            related_events = db.query(CampaignEvent).filter(
                and_(
                    CampaignEvent.campaign_id == event.campaign_id,
                    CampaignEvent.id != event_id,
                    CampaignEvent.participants.op('&&')(event.participants)  # PostgreSQL array overlap
                )
            ).all()
            
            for related in related_events:
                connections.append(EventConnection(
                    from_event_id=event_id,
                    to_event_id=related.id,
                    connection_type="shared_participants",
                    weight=0.5
                ))
        
        # Find events in the same location
        if event.location:
            location_events = db.query(CampaignEvent).filter(
                and_(
                    CampaignEvent.campaign_id == event.campaign_id,
                    CampaignEvent.id != event_id,
                    CampaignEvent.location == event.location
                )
            ).all()
            
            for related in location_events:
                connections.append(EventConnection(
                    from_event_id=event_id,
                    to_event_id=related.id,
                    connection_type="same_location",
                    weight=0.3
                ))
        
        return connections
    
    def search_events(self, campaign_id: str, search_term: str, db: Session) -> List[CampaignEvent]:
        """Search events by text content."""
        search_query = db.query(CampaignEvent).filter(
            and_(
                CampaignEvent.campaign_id == campaign_id,
                or_(
                    CampaignEvent.title.ilike(f"%{search_term}%"),
                    CampaignEvent.description.ilike(f"%{search_term}%"),
                    CampaignEvent.notes.ilike(f"%{search_term}%")
                )
            )
        )
        
        return search_query.all()
    
    def get_campaign_statistics(self, campaign_id: str, db: Session) -> Dict[str, Any]:
        """Get detailed campaign statistics."""
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {}
        
        sessions = db.query(GameSession).filter(
            GameSession.campaign_id == campaign_id
        ).all()
        
        events = db.query(CampaignEvent).filter(
            CampaignEvent.campaign_id == campaign_id
        ).all()
        
        return self.analyzer.analyze_campaign_statistics(campaign, sessions, events)