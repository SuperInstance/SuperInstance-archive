"""
Calendar system and event tracking service.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
import logging

from ..models.calendar import (
    EventType, EventScope, EventStatus, RecurrenceType, CalendarType, TimeOfDay,
    CalendarSchema, WorldEventSchema, CalendarEraSchema, WorldDate,
    MonthDefinition, SeasonDefinition, HolidayDefinition,
    CalendarCreationRequest, EventCreationRequest, CalendarQueryRequest,
    TimeAdvanceRequest, CalendarResponse, EventSchedule, CalendarTimeline,
    TimelineEntry, EventConsequence, RecurrentEventPattern
)
from ..config import Config

logger = logging.getLogger(__name__)

class CalendarService:
    def __init__(self):
        self.config = Config()
        self.calendar_templates = self._initialize_calendar_templates()
        self.event_templates = self._initialize_event_templates()
        self.naming_libraries = self._initialize_naming_libraries()
        
    def _initialize_calendar_templates(self) -> Dict[str, Any]:
        """Initialize predefined calendar templates."""
        
        templates = {}
        
        # Standard fantasy calendar (similar to Forgotten Realms)
        templates["fantasy_standard"] = {
            "name": "Faerunian Calendar",
            "calendar_type": CalendarType.SOLAR,
            "days_per_week": 10,
            "weeks_per_month": 3,
            "months": [
                {"name": "Hammer", "days": 30, "season": "winter"},
                {"name": "Alturiak", "days": 30, "season": "winter"},
                {"name": "Ches", "days": 30, "season": "spring"},
                {"name": "Tarsakh", "days": 30, "season": "spring"},
                {"name": "Mirtul", "days": 30, "season": "spring"},
                {"name": "Kythorn", "days": 30, "season": "summer"},
                {"name": "Flamerule", "days": 30, "season": "summer"},
                {"name": "Eleasis", "days": 30, "season": "summer"},
                {"name": "Eleint", "days": 30, "season": "autumn"},
                {"name": "Marpenoth", "days": 30, "season": "autumn"},
                {"name": "Uktar", "days": 30, "season": "autumn"},
                {"name": "Nightal", "days": 30, "season": "winter"}
            ],
            "holidays": [
                {"name": "Midwinter", "month": 1, "day": 1, "type": "religious"},
                {"name": "Greengrass", "month": 4, "day": 30, "type": "seasonal"},
                {"name": "Midsummer", "month": 7, "day": 15, "type": "seasonal"},
                {"name": "Harvestide", "month": 10, "day": 15, "type": "seasonal"},
                {"name": "Feast of the Moon", "month": 11, "day": 30, "type": "religious"}
            ]
        }
        
        # Simple medieval calendar
        templates["medieval_simple"] = {
            "name": "Kingdom Calendar",
            "calendar_type": CalendarType.SOLAR,
            "days_per_week": 7,
            "weeks_per_month": 4,
            "months": [
                {"name": "Firstmoon", "days": 28, "season": "winter"},
                {"name": "Lastcold", "days": 28, "season": "winter"},
                {"name": "Thawing", "days": 31, "season": "spring"},
                {"name": "Plantmoon", "days": 30, "season": "spring"},
                {"name": "Flowering", "days": 31, "season": "spring"},
                {"name": "Warmdays", "days": 30, "season": "summer"},
                {"name": "Highheat", "days": 31, "season": "summer"},
                {"name": "Harvestmoon", "days": 31, "season": "summer"},
                {"name": "Goldfall", "days": 30, "season": "autumn"},
                {"name": "Leafdeath", "days": 31, "season": "autumn"},
                {"name": "Firstfrost", "days": 30, "season": "autumn"},
                {"name": "Longdark", "days": 31, "season": "winter"}
            ]
        }
        
        return templates

    def _initialize_event_templates(self) -> Dict[EventType, List[Dict[str, Any]]]:
        """Initialize event templates for automatic generation."""
        
        templates = {}
        
        # Political events
        templates[EventType.POLITICAL] = [
            {
                "title_templates": ["Royal {event}", "The {political_event} of {location}"],
                "events": ["coronation", "succession", "treaty signing", "diplomatic summit"],
                "participants": ["nobles", "diplomats", "royal court", "foreign dignitaries"],
                "consequences": ["policy changes", "trade agreements", "military alliances"]
            }
        ]
        
        # Religious events
        templates[EventType.RELIGIOUS] = [
            {
                "title_templates": ["Festival of {deity}", "The {holy_event}", "Sacred {ceremony}"],
                "events": ["pilgrimage", "blessing ceremony", "religious festival", "holy day"],
                "participants": ["clergy", "pilgrims", "faithful", "temple guards"],
                "consequences": ["increased faith", "divine blessings", "religious unity"]
            }
        ]
        
        # Economic events
        templates[EventType.ECONOMIC] = [
            {
                "title_templates": ["{trade_event}", "The Great {market_event}"],
                "events": ["market fair", "trade caravan arrival", "merchant guild meeting"],
                "participants": ["merchants", "traders", "craftsmen", "buyers"],
                "consequences": ["price changes", "new trade routes", "economic prosperity"]
            }
        ]
        
        # Natural events
        templates[EventType.NATURAL] = [
            {
                "title_templates": ["The {natural_disaster}", "{weather_event} Season"],
                "events": ["harvest season", "migration", "natural phenomenon", "seasonal change"],
                "participants": ["farmers", "hunters", "travelers", "animals"],
                "consequences": ["crop yields", "food availability", "travel conditions"]
            }
        ]
        
        return templates

    def _initialize_naming_libraries(self) -> Dict[str, List[str]]:
        """Initialize naming libraries for calendar elements."""
        
        return {
            "month_prefixes": [
                "First", "Last", "High", "Deep", "Long", "Short", "Bright", "Dark",
                "Gold", "Silver", "Green", "Red", "Blue", "White", "Black"
            ],
            "month_suffixes": [
                "moon", "tide", "wind", "sun", "star", "frost", "heat", "rain",
                "snow", "bloom", "fall", "rise", "dawn", "dusk", "night", "day"
            ],
            "seasonal_names": [
                "Planting", "Growing", "Harvest", "Resting", "Warming", "Cooling",
                "Blooming", "Withering", "Awakening", "Sleeping"
            ],
            "deity_names": [
                "Solaris", "Lunara", "Tempestas", "Verdania", "Igneus", "Glacies",
                "Fortuna", "Bellona", "Minerva", "Ceres", "Bacchus", "Diana"
            ],
            "locations": [
                "Capital City", "Royal Palace", "Great Temple", "Market Square",
                "Northern Provinces", "Southern Reaches", "Eastern Marches", "Western Lands"
            ]
        }

    async def create_calendar(
        self,
        request: CalendarCreationRequest,
        db_session: Optional[Session] = None
    ) -> CalendarResponse:
        """Create a new calendar system."""
        
        start_time = datetime.utcnow()
        
        try:
            # Use template if cultural theme matches
            template = None
            if request.cultural_theme == "fantasy":
                template = self.calendar_templates.get("fantasy_standard")
            elif request.cultural_theme == "medieval":
                template = self.calendar_templates.get("medieval_simple")
            
            if template:
                calendar = await self._create_from_template(template, request.name)
            else:
                calendar = await self._create_custom_calendar(request)
            
            # Generate default holidays
            calendar.holidays = await self._generate_holidays(calendar, request.cultural_theme)
            
            # Create default eras
            current_era = CalendarEraSchema(
                id=str(uuid.uuid4()),
                name="Current Age",
                description="The present era",
                start_year=1,
                end_year=None
            )
            
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            return CalendarResponse(
                success=True,
                calendar_data=calendar,
                current_date=calendar.current_date,
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"Error creating calendar: {e}")
            return CalendarResponse(
                success=False,
                message=f"Failed to create calendar: {str(e)}",
                errors=[str(e)]
            )

    async def _create_from_template(self, template: Dict[str, Any], name: str) -> CalendarSchema:
        """Create calendar from predefined template."""
        
        months = []
        for month_data in template["months"]:
            months.append(MonthDefinition(
                name=month_data["name"],
                days=month_data["days"],
                season=month_data.get("season")
            ))
        
        # Create seasons based on month data
        seasons = await self._generate_seasons_from_months(months)
        
        return CalendarSchema(
            id=str(uuid.uuid4()),
            name=name,
            calendar_type=CalendarType(template["calendar_type"]),
            months=months,
            days_per_week=template["days_per_week"],
            weeks_per_month=template.get("weeks_per_month", 4),
            seasons=seasons,
            current_date=WorldDate(year=1, month=1, day=1),
            epoch_description="The founding of the realm"
        )

    async def _create_custom_calendar(self, request: CalendarCreationRequest) -> CalendarSchema:
        """Create custom calendar from request parameters."""
        
        # Generate month names
        month_names = request.month_names or await self._generate_month_names(
            request.month_count, request.naming_style
        )
        
        # Calculate days per month
        days_per_month = (request.days_per_week * request.weeks_per_month)
        
        # Create months
        months = []
        for i, name in enumerate(month_names):
            season = self._determine_season(i, request.month_count, request.season_count)
            months.append(MonthDefinition(
                name=name,
                days=days_per_month,
                season=season
            ))
        
        # Generate seasons
        seasons = await self._generate_seasons(request.season_count, request.cultural_theme)
        
        return CalendarSchema(
            id=str(uuid.uuid4()),
            name=request.name,
            calendar_type=request.calendar_type,
            months=months,
            days_per_week=request.days_per_week,
            weeks_per_month=request.weeks_per_month,
            seasons=seasons,
            current_date=WorldDate(year=1, month=1, day=1)
        )

    async def _generate_month_names(self, count: int, style: str) -> List[str]:
        """Generate month names based on style."""
        
        names = []
        naming = self.naming_libraries
        
        if style == "medieval":
            # Combine prefixes and suffixes
            prefixes = naming["month_prefixes"]
            suffixes = naming["month_suffixes"]
            
            for i in range(count):
                prefix = random.choice(prefixes)
                suffix = random.choice(suffixes)
                names.append(f"{prefix}{suffix}")
        
        elif style == "seasonal":
            seasonal_names = naming["seasonal_names"]
            for i in range(count):
                base_name = random.choice(seasonal_names)
                names.append(f"{base_name} {i + 1}" if count > len(seasonal_names) else base_name)
        
        else:  # classical/default
            classical_names = [
                "Primaris", "Secundus", "Tertius", "Quartus", "Quintus", "Sextus",
                "Septimus", "Octavus", "Nonus", "Decimus", "Undecimus", "Duodecimus"
            ]
            names = classical_names[:count]
        
        return names

    def _determine_season(self, month_index: int, total_months: int, season_count: int) -> str:
        """Determine season for a month based on its position."""
        
        months_per_season = total_months / season_count
        season_index = int(month_index / months_per_season)
        
        season_names = ["spring", "summer", "autumn", "winter"]
        if season_count == 2:
            season_names = ["warm season", "cold season"]
        elif season_count == 3:
            season_names = ["growing", "harvest", "rest"]
        elif season_count > 4:
            season_names = [f"season_{i+1}" for i in range(season_count)]
        
        return season_names[min(season_index, len(season_names) - 1)]

    async def _generate_seasons_from_months(self, months: List[MonthDefinition]) -> List[SeasonDefinition]:
        """Generate season definitions from month data."""
        
        seasons = []
        current_season = None
        season_start_month = 1
        season_days = 0
        
        for i, month in enumerate(months):
            if current_season != month.season:
                # Save previous season
                if current_season:
                    seasons.append(SeasonDefinition(
                        name=current_season,
                        start_month=season_start_month,
                        start_day=1,
                        duration_days=season_days
                    ))
                
                # Start new season
                current_season = month.season
                season_start_month = i + 1
                season_days = month.days
            else:
                season_days += month.days
        
        # Add final season
        if current_season:
            seasons.append(SeasonDefinition(
                name=current_season,
                start_month=season_start_month,
                start_day=1,
                duration_days=season_days
            ))
        
        return seasons

    async def _generate_seasons(self, count: int, cultural_theme: str) -> List[SeasonDefinition]:
        """Generate season definitions."""
        
        seasons = []
        
        if count == 4:  # Standard four seasons
            season_names = ["Spring", "Summer", "Autumn", "Winter"]
            season_descriptions = [
                "The season of renewal and growth",
                "The season of warmth and abundance", 
                "The season of harvest and preparation",
                "The season of rest and contemplation"
            ]
        else:
            season_names = [f"Season {i+1}" for i in range(count)]
            season_descriptions = [f"The {i+1} season of the year" for i in range(count)]
        
        days_per_season = 360 // count  # Assume 360 day year
        
        for i in range(count):
            seasons.append(SeasonDefinition(
                name=season_names[i],
                start_month=(i * 3) + 1,  # Rough approximation
                start_day=1,
                duration_days=days_per_season,
                description=season_descriptions[i] if i < len(season_descriptions) else ""
            ))
        
        return seasons

    async def _generate_holidays(self, calendar: CalendarSchema, cultural_theme: str) -> List[HolidayDefinition]:
        """Generate holidays for the calendar."""
        
        holidays = []
        
        # Seasonal holidays
        for season in calendar.seasons:
            # Holiday at start of season
            holidays.append(HolidayDefinition(
                name=f"{season.name} Festival",
                date=WorldDate(year=1, month=season.start_month, day=1),
                description=f"Celebration marking the beginning of {season.name.lower()}",
                type="seasonal",
                traditional_activities=[f"{season.name.lower()} ceremonies", "feasting", "community gathering"]
            ))
        
        # Religious holidays (based on cultural theme)
        if cultural_theme in ["fantasy", "medieval"]:
            deities = random.sample(self.naming_libraries["deity_names"], 3)
            for i, deity in enumerate(deities):
                month = (i * 4) + 2  # Spread throughout year
                holidays.append(HolidayDefinition(
                    name=f"Day of {deity}",
                    date=WorldDate(year=1, month=min(month, len(calendar.months)), day=15),
                    description=f"Sacred day honoring {deity}",
                    type="religious",
                    observance_level="major",
                    traditional_activities=["prayer", "offerings", "pilgrimage"]
                ))
        
        # New Year
        holidays.append(HolidayDefinition(
            name="New Year's Day",
            date=WorldDate(year=1, month=1, day=1),
            description="Celebration of the new year",
            type="civic",
            observance_level="major",
            traditional_activities=["celebration", "resolutions", "ceremonies"]
        ))
        
        return holidays

    async def create_event(
        self,
        request: EventCreationRequest,
        calendar: CalendarSchema,
        db_session: Optional[Session] = None
    ) -> CalendarResponse:
        """Create a new world event."""
        
        try:
            end_date = request.start_date.add_days(request.duration_days - 1, calendar)
            
            event = WorldEventSchema(
                id=str(uuid.uuid4()),
                title=request.title,
                description=request.description,
                event_type=request.event_type,
                scope=request.scope,
                start_date=request.start_date,
                end_date=end_date if request.duration_days > 1 else None,
                time_of_day=request.time_of_day,
                participants=request.required_participants.copy()
            )
            
            # Generate additional content if requested
            if request.generate_participants and not request.required_participants:
                event.participants = await self._generate_event_participants(
                    request.event_type, request.scope
                )
            
            if request.generate_consequences:
                event.consequences = await self._generate_event_consequences(
                    request.event_type, request.scope
                )
            
            if request.generate_news_description:
                event.news_description = await self._generate_news_description(event)
                event.rumor_variants = await self._generate_rumor_variants(event)
            
            return CalendarResponse(
                success=True,
                message="Event created successfully",
                events=[event]
            )
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return CalendarResponse(
                success=False,
                message=f"Failed to create event: {str(e)}",
                errors=[str(e)]
            )

    async def _generate_event_participants(self, event_type: EventType, scope: EventScope) -> List[str]:
        """Generate appropriate participants for an event."""
        
        participants = []
        templates = self.event_templates.get(event_type, [])
        
        if templates:
            template = random.choice(templates)
            participant_types = template.get("participants", [])
            
            # Select 2-4 participant types
            selected = random.sample(participant_types, min(len(participant_types), random.randint(2, 4)))
            participants.extend(selected)
        
        # Add scope-appropriate participants
        if scope in [EventScope.NATIONAL, EventScope.CONTINENTAL]:
            participants.append("government officials")
        if scope == EventScope.GLOBAL:
            participants.append("international representatives")
        
        return participants

    async def _generate_event_consequences(self, event_type: EventType, scope: EventScope) -> List[str]:
        """Generate consequences for an event."""
        
        consequences = []
        templates = self.event_templates.get(event_type, [])
        
        if templates:
            template = random.choice(templates)
            consequence_types = template.get("consequences", [])
            consequences.extend(random.sample(consequence_types, min(len(consequence_types), 3)))
        
        # Add scope-appropriate consequences
        scope_consequences = {
            EventScope.LOCAL: ["local impact", "community changes"],
            EventScope.REGIONAL: ["regional effects", "trade disruption"],
            EventScope.NATIONAL: ["national policy changes", "widespread impact"],
            EventScope.GLOBAL: ["international relations shift", "worldwide consequences"]
        }
        
        consequences.extend(scope_consequences.get(scope, []))
        
        return consequences[:5]  # Limit to 5 consequences

    async def _generate_news_description(self, event: WorldEventSchema) -> str:
        """Generate news description for an event."""
        
        templates = {
            EventType.POLITICAL: [
                "Political tensions rise as {title} unfolds in {location}.",
                "Leaders gather for {title}, with far-reaching implications expected.",
                "The {title} marks a significant shift in regional politics."
            ],
            EventType.RELIGIOUS: [
                "Faithful from across the land participate in {title}.",
                "The sacred {title} draws pilgrims and worshippers.",
                "Religious authorities announce the {title} will bring divine blessings."
            ],
            EventType.ECONOMIC: [
                "Trade and commerce flourish during {title}.",
                "Economic opportunities abound as {title} attracts merchants.",
                "The {title} promises to boost local prosperity."
            ],
            EventType.NATURAL: [
                "Natural forces bring about {title} in the region.",
                "The {title} affects travel and daily life across the area.",
                "Locals prepare for the seasonal {title}."
            ]
        }
        
        event_templates = templates.get(event.event_type, ["The {title} takes place."])
        template = random.choice(event_templates)
        
        return template.format(
            title=event.title.lower(),
            location=event.location_description or "the region"
        )

    async def _generate_rumor_variants(self, event: WorldEventSchema) -> List[str]:
        """Generate rumor variants for an event."""
        
        base_rumors = [
            f"I heard {event.title.lower()} is more than it seems...",
            f"Word is that {event.title.lower()} will change everything.",
            f"They say {event.title.lower()} is connected to ancient prophecies.",
            f"Rumors suggest {event.title.lower()} hides a deeper purpose."
        ]
        
        return random.sample(base_rumors, min(len(base_rumors), 3))

    async def advance_time(
        self,
        request: TimeAdvanceRequest,
        calendar: CalendarSchema,
        db_session: Optional[Session] = None
    ) -> CalendarResponse:
        """Advance calendar time and trigger events."""
        
        try:
            # Calculate total minutes to advance
            total_minutes = request.minutes + (request.hours * 60) + (request.days * 24 * 60)
            
            # Advance the calendar
            new_date = await self._advance_calendar_time(calendar, total_minutes)
            calendar.current_date = new_date
            
            # Get triggered events
            triggered_events = []
            upcoming_events = []
            
            if request.trigger_scheduled_events:
                triggered_events = await self._get_triggered_events(calendar, new_date)
            
            # Generate random events if requested
            if request.generate_random_events and request.days > 0:
                random_events = await self._generate_random_events(calendar, request.days)
                triggered_events.extend(random_events)
            
            # Get upcoming events
            upcoming_events = await self._get_upcoming_events(calendar, new_date, 30)  # Next 30 days
            
            return CalendarResponse(
                success=True,
                message=f"Time advanced successfully",
                calendar_data=calendar,
                current_date=new_date,
                events=triggered_events,
                upcoming_events=upcoming_events
            )
            
        except Exception as e:
            logger.error(f"Error advancing time: {e}")
            return CalendarResponse(
                success=False,
                message=f"Failed to advance time: {str(e)}",
                errors=[str(e)]
            )

    async def _advance_calendar_time(self, calendar: CalendarSchema, minutes: int) -> WorldDate:
        """Advance calendar by specified minutes."""
        
        current = calendar.current_date
        
        # Add minutes
        new_minute = current.minute + minutes
        hours_to_add = new_minute // 60
        new_minute = new_minute % 60
        
        # Add hours
        new_hour = current.hour + hours_to_add
        days_to_add = new_hour // 24
        new_hour = new_hour % 24
        
        # Add days if needed
        if days_to_add > 0:
            return current.add_days(days_to_add, calendar)
        
        return WorldDate(
            year=current.year,
            month=current.month,
            day=current.day,
            hour=new_hour,
            minute=new_minute
        )

    async def _get_triggered_events(self, calendar: CalendarSchema, current_date: WorldDate) -> List[WorldEventSchema]:
        """Get events that should trigger on this date."""
        
        triggered_events = []
        
        # Check holidays
        for holiday in calendar.holidays:
            if (holiday.date.month == current_date.month and 
                holiday.date.day == current_date.day and
                holiday.annual):
                
                event = WorldEventSchema(
                    id=str(uuid.uuid4()),
                    title=holiday.name,
                    description=holiday.description,
                    event_type=EventType.RELIGIOUS if holiday.type == "religious" else EventType.SOCIAL,
                    scope=EventScope.REGIONAL,
                    start_date=current_date,
                    status=EventStatus.ACTIVE,
                    participants=["citizens", "celebrants"],
                    tags=["holiday", holiday.type]
                )
                triggered_events.append(event)
        
        return triggered_events

    async def _generate_random_events(self, calendar: CalendarSchema, days: int) -> List[WorldEventSchema]:
        """Generate random events for the advanced time period."""
        
        events = []
        
        # Base chance of 5% per day for a random event
        event_chance = 0.05 * days
        
        if random.random() < event_chance:
            # Generate a random event
            event_types = list(EventType)
            event_type = random.choice(event_types)
            
            # Create random event
            event = WorldEventSchema(
                id=str(uuid.uuid4()),
                title=await self._generate_random_event_title(event_type),
                description=await self._generate_random_event_description(event_type),
                event_type=event_type,
                scope=random.choice(list(EventScope)),
                start_date=calendar.current_date,
                status=EventStatus.ACTIVE,
                participants=await self._generate_event_participants(event_type, EventScope.LOCAL),
                tags=["random", "generated"]
            )
            
            events.append(event)
        
        return events

    async def _generate_random_event_title(self, event_type: EventType) -> str:
        """Generate random event title."""
        
        titles = {
            EventType.POLITICAL: ["Unexpected Alliance", "Border Dispute", "Leadership Change"],
            EventType.RELIGIOUS: ["Divine Manifestation", "Pilgrim Arrival", "Sacred Discovery"],
            EventType.ECONOMIC: ["Market Boom", "Trade Disruption", "Merchant Gathering"],
            EventType.NATURAL: ["Seasonal Phenomenon", "Wildlife Migration", "Weather Pattern"],
            EventType.SOCIAL: ["Community Festival", "Cultural Exchange", "Public Gathering"]
        }
        
        event_titles = titles.get(event_type, ["Random Event"])
        return random.choice(event_titles)

    async def _generate_random_event_description(self, event_type: EventType) -> str:
        """Generate random event description."""
        
        descriptions = {
            EventType.POLITICAL: "Political circumstances have created an unexpected situation.",
            EventType.RELIGIOUS: "A spiritual event has captured the attention of the faithful.",
            EventType.ECONOMIC: "Economic forces have created new opportunities and challenges.",
            EventType.NATURAL: "Natural forces have brought about a notable phenomenon.",
            EventType.SOCIAL: "The community comes together for a significant social occasion."
        }
        
        return descriptions.get(event_type, "An unexpected event has occurred.")

    async def _get_upcoming_events(self, calendar: CalendarSchema, current_date: WorldDate, days: int) -> List[WorldEventSchema]:
        """Get events scheduled in the next N days."""
        
        upcoming = []
        
        # Check holidays in the coming period
        for day_offset in range(1, days + 1):
            check_date = current_date.add_days(day_offset, calendar)
            
            for holiday in calendar.holidays:
                if (holiday.date.month == check_date.month and 
                    holiday.date.day == check_date.day):
                    
                    event = WorldEventSchema(
                        id=str(uuid.uuid4()),
                        title=holiday.name,
                        description=holiday.description,
                        event_type=EventType.RELIGIOUS if holiday.type == "religious" else EventType.SOCIAL,
                        scope=EventScope.REGIONAL,
                        start_date=check_date,
                        status=EventStatus.PLANNED,
                        tags=["holiday", "upcoming"]
                    )
                    upcoming.append(event)
        
        return upcoming

    async def query_calendar(
        self,
        request: CalendarQueryRequest,
        calendar: CalendarSchema,
        db_session: Optional[Session] = None
    ) -> CalendarResponse:
        """Query calendar information and events."""
        
        try:
            events = []
            active_holidays = []
            
            # Determine date range
            start_date = request.start_date or calendar.current_date
            end_date = request.end_date or start_date.add_days(30, calendar)
            
            # Collect events in date range
            if request.include_events:
                events = await self._get_events_in_range(calendar, start_date, end_date)
            
            # Collect active holidays
            if request.include_holidays:
                active_holidays = await self._get_active_holidays(calendar, calendar.current_date)
            
            # Filter by event types if specified
            if request.event_types:
                events = [e for e in events if e.event_type in request.event_types]
            
            # Filter by scopes if specified
            if request.scopes:
                events = [e for e in events if e.scope in request.scopes]
            
            return CalendarResponse(
                success=True,
                calendar_data=calendar,
                events=events,
                current_date=calendar.current_date,
                active_holidays=active_holidays
            )
            
        except Exception as e:
            logger.error(f"Error querying calendar: {e}")
            return CalendarResponse(
                success=False,
                message=f"Failed to query calendar: {str(e)}",
                errors=[str(e)]
            )

    async def _get_events_in_range(
        self,
        calendar: CalendarSchema,
        start_date: WorldDate,
        end_date: WorldDate
    ) -> List[WorldEventSchema]:
        """Get all events within a date range."""
        
        events = []
        
        # In a real implementation, this would query the database
        # For now, we'll generate some sample events
        
        current_check = start_date
        while current_check.to_days(calendar) <= end_date.to_days(calendar):
            # Check holidays
            for holiday in calendar.holidays:
                if (holiday.date.month == current_check.month and 
                    holiday.date.day == current_check.day):
                    
                    event = WorldEventSchema(
                        id=str(uuid.uuid4()),
                        title=holiday.name,
                        description=holiday.description,
                        event_type=EventType.RELIGIOUS if holiday.type == "religious" else EventType.SOCIAL,
                        scope=EventScope.REGIONAL,
                        start_date=current_check,
                        status=EventStatus.PLANNED,
                        tags=["holiday"]
                    )
                    events.append(event)
            
            current_check = current_check.add_days(1, calendar)
        
        return events

    async def _get_active_holidays(self, calendar: CalendarSchema, current_date: WorldDate) -> List[HolidayDefinition]:
        """Get currently active holidays."""
        
        active = []
        
        for holiday in calendar.holidays:
            if (holiday.date.month == current_date.month and 
                holiday.date.day == current_date.day):
                active.append(holiday)
        
        return active

    async def create_event_schedule(
        self,
        calendar: CalendarSchema,
        start_date: WorldDate,
        duration_days: int
    ) -> EventSchedule:
        """Create an event schedule showing events over time."""
        
        end_date = start_date.add_days(duration_days, calendar)
        events = await self._get_events_in_range(calendar, start_date, end_date)
        
        # Organize events by date
        scheduled_events = {}
        for event in events:
            date_key = f"{event.start_date.year}-{event.start_date.month:02d}-{event.start_date.day:02d}"
            if date_key not in scheduled_events:
                scheduled_events[date_key] = []
            scheduled_events[date_key].append(event)
        
        # Find busiest day
        busiest_day = None
        max_events = 0
        for date_key, day_events in scheduled_events.items():
            if len(day_events) > max_events:
                max_events = len(day_events)
                busiest_day = date_key
        
        # Count events by type
        events_by_type = {}
        for event in events:
            events_by_type[event.event_type] = events_by_type.get(event.event_type, 0) + 1
        
        return EventSchedule(
            calendar_id=calendar.id or "unknown",
            start_date=start_date,
            end_date=end_date,
            scheduled_events=scheduled_events,
            total_events=len(events),
            events_by_type=events_by_type,
            busiest_day=busiest_day
        )

    async def get_current_season(self, calendar: CalendarSchema, date: Optional[WorldDate] = None) -> Optional[SeasonDefinition]:
        """Get the current season for a given date."""
        
        check_date = date or calendar.current_date
        
        for season in calendar.seasons:
            season_end_day = season.start_day + season.duration_days - 1
            
            if season.start_month <= check_date.month:
                if (season.start_month == check_date.month and check_date.day >= season.start_day) or \
                   season.start_month < check_date.month:
                    # Check if we're still in this season
                    season_end_month = season.start_month
                    season_end_day_check = season_end_day
                    
                    # Handle season spanning multiple months
                    while season_end_day_check > 30:  # Assuming max 30 days per month
                        season_end_month += 1
                        season_end_day_check -= 30
                    
                    if check_date.month < season_end_month or \
                       (check_date.month == season_end_month and check_date.day <= season_end_day_check):
                        return season
        
        # Default to first season if none found
        return calendar.seasons[0] if calendar.seasons else None