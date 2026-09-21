"""
Campaign and session management system for DMLog.ai.
Handles campaign creation, session tracking, and story management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid
import logging
import json

from .types import Campaign, Session, CharacterInterface

logger = logging.getLogger(__name__)


class CampaignStatus(Enum):
    """Campaign status options."""
    PLANNING = "planning"
    ACTIVE = "active"
    HIATUS = "hiatus"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SessionStatus(Enum):
    """Session status options."""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventType(Enum):
    """Types of campaign events."""
    STORY_BEAT = "story_beat"
    CHARACTER_DEVELOPMENT = "character_development"
    COMBAT_ENCOUNTER = "combat_encounter"
    ROLEPLAY_SCENE = "roleplay_scene"
    EXPLORATION = "exploration"
    PUZZLE_CHALLENGE = "puzzle_challenge"
    NPC_INTERACTION = "npc_interaction"
    LOCATION_DISCOVERY = "location_discovery"
    TREASURE_FOUND = "treasure_found"
    QUEST_START = "quest_start"
    QUEST_COMPLETION = "quest_completion"
    LEVEL_UP = "level_up"
    CHARACTER_DEATH = "character_death"
    MAJOR_PLOT_POINT = "major_plot_point"


@dataclass
class CampaignEvent:
    """Represents an event that occurred during the campaign."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.STORY_BEAT
    title: str = ""
    description: str = ""
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    characters_involved: List[str] = field(default_factory=list)  # Character IDs
    location: str = ""
    consequences: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlotThread:
    """Represents an ongoing plot thread in the campaign."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: str = "active"  # active, completed, abandoned
    importance: str = "minor"  # minor, major, critical
    related_characters: List[str] = field(default_factory=list)
    related_locations: List[str] = field(default_factory=list)
    key_events: List[str] = field(default_factory=list)  # Event IDs
    notes: str = ""
    created_date: datetime = field(default_factory=datetime.now)
    completion_date: Optional[datetime] = None


@dataclass
class NPC:
    """Non-player character definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    role: str = ""  # "ally", "enemy", "neutral", "questgiver", etc.
    location: str = ""
    personality_traits: List[str] = field(default_factory=list)
    motivations: List[str] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)  # character_id -> relationship
    notes: str = ""
    stats: Optional[Dict[str, Any]] = None  # Combat stats if needed
    alive: bool = True


@dataclass
class Location:
    """Campaign location definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    type: str = ""  # "city", "dungeon", "wilderness", "plane", etc.
    parent_location: Optional[str] = None  # ID of containing location
    sub_locations: List[str] = field(default_factory=list)  # IDs of contained locations
    key_features: List[str] = field(default_factory=list)
    inhabitants: List[str] = field(default_factory=list)  # NPC IDs
    events_occurred: List[str] = field(default_factory=list)  # Event IDs
    notes: str = ""
    discovered: bool = False


@dataclass
class Quest:
    """Quest definition and tracking."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    giver: Optional[str] = None  # NPC ID
    status: str = "available"  # available, accepted, completed, failed, abandoned
    type: str = "main"  # main, side, personal, faction
    objectives: List[Dict[str, Any]] = field(default_factory=list)
    rewards: List[str] = field(default_factory=list)
    deadline: Optional[datetime] = None
    location: str = ""
    notes: str = ""
    created_date: datetime = field(default_factory=datetime.now)
    completion_date: Optional[datetime] = None


@dataclass
class EnhancedSession(Session):
    """Enhanced session with additional campaign management features."""
    status: SessionStatus = SessionStatus.PLANNED
    location: str = ""
    session_notes: str = ""
    dm_notes: str = ""
    player_feedback: Dict[str, str] = field(default_factory=dict)
    handouts: List[str] = field(default_factory=list)
    maps_used: List[str] = field(default_factory=list)
    npcs_encountered: List[str] = field(default_factory=list)
    locations_visited: List[str] = field(default_factory=list)
    quests_progressed: List[str] = field(default_factory=list)
    treasure_found: List[Dict[str, Any]] = field(default_factory=list)
    experience_awarded: Dict[str, int] = field(default_factory=dict)  # character_id -> XP
    next_session_prep: str = ""


@dataclass 
class EnhancedCampaign(Campaign):
    """Enhanced campaign with full campaign management features."""
    status: CampaignStatus = CampaignStatus.PLANNING
    system_version: str = ""
    expected_level_range: str = ""
    theme: str = ""
    tone: str = ""
    house_rules: List[str] = field(default_factory=list)
    
    # Story management
    plot_threads: Dict[str, PlotThread] = field(default_factory=dict)
    events: List[CampaignEvent] = field(default_factory=list)
    
    # World building
    npcs: Dict[str, NPC] = field(default_factory=dict)
    locations: Dict[str, Location] = field(default_factory=dict)
    quests: Dict[str, Quest] = field(default_factory=dict)
    
    # Session management
    sessions: Dict[str, EnhancedSession] = field(default_factory=dict)
    next_session_date: Optional[datetime] = None
    session_frequency: str = "weekly"  # weekly, biweekly, monthly, irregular
    typical_session_length: int = 240  # minutes
    
    # Player management
    player_notes: Dict[str, str] = field(default_factory=dict)  # player_id -> notes
    character_backgrounds: Dict[str, str] = field(default_factory=dict)  # character_id -> background
    
    # Campaign resources
    handouts: List[Dict[str, Any]] = field(default_factory=list)
    maps: List[Dict[str, Any]] = field(default_factory=list)
    music_playlists: List[Dict[str, Any]] = field(default_factory=list)
    reference_materials: List[Dict[str, Any]] = field(default_factory=list)


class CampaignManager:
    """Manages campaigns and sessions for DMLog.ai."""
    
    def __init__(self):
        self.campaigns: Dict[str, EnhancedCampaign] = {}
        self.active_campaign_id: Optional[str] = None
    
    def create_campaign(self, name: str, description: str, game_system: str, 
                       dm_id: str, **kwargs) -> EnhancedCampaign:
        """Create a new campaign."""
        campaign = EnhancedCampaign(
            name=name,
            description=description,
            game_system=game_system,
            dm_id=dm_id,
            **kwargs
        )
        
        self.campaigns[campaign.id] = campaign
        logger.info(f"Created campaign: {name}")
        
        return campaign
    
    def get_campaign(self, campaign_id: str) -> Optional[EnhancedCampaign]:
        """Get a campaign by ID."""
        return self.campaigns.get(campaign_id)
    
    def set_active_campaign(self, campaign_id: str) -> bool:
        """Set the active campaign."""
        if campaign_id in self.campaigns:
            self.active_campaign_id = campaign_id
            logger.info(f"Set active campaign: {self.campaigns[campaign_id].name}")
            return True
        return False
    
    def get_active_campaign(self) -> Optional[EnhancedCampaign]:
        """Get the currently active campaign."""
        if self.active_campaign_id:
            return self.campaigns.get(self.active_campaign_id)
        return None
    
    def add_player_to_campaign(self, campaign_id: str, player_id: str, 
                              character_id: Optional[str] = None) -> bool:
        """Add a player to a campaign."""
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return False
        
        if player_id not in campaign.player_ids:
            campaign.player_ids.append(player_id)
        
        if character_id and character_id not in campaign.character_ids:
            campaign.character_ids.append(character_id)
        
        campaign.updated_at = datetime.now()
        logger.info(f"Added player {player_id} to campaign {campaign.name}")
        return True
    
    def create_session(self, campaign_id: str, name: str, date: datetime,
                      **kwargs) -> Optional[EnhancedSession]:
        """Create a new session for a campaign."""
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return None
        
        session_number = len(campaign.sessions) + 1
        
        session = EnhancedSession(
            campaign_id=campaign_id,
            session_number=session_number,
            name=name,
            date=date,
            participants=campaign.player_ids.copy(),
            **kwargs
        )
        
        campaign.sessions[session.id] = session
        campaign.session_count += 1
        campaign.updated_at = datetime.now()
        
        logger.info(f"Created session {session_number}: {name}")
        return session
    
    def start_session(self, session_id: str) -> bool:
        """Start a session."""
        for campaign in self.campaigns.values():
            if session_id in campaign.sessions:
                session = campaign.sessions[session_id]
                session.status = SessionStatus.IN_PROGRESS
                logger.info(f"Started session: {session.name}")
                return True
        return False
    
    def end_session(self, session_id: str, duration_minutes: Optional[int] = None) -> bool:
        """End a session."""
        for campaign in self.campaigns.values():
            if session_id in campaign.sessions:
                session = campaign.sessions[session_id]
                session.status = SessionStatus.COMPLETED
                session.completed = True
                if duration_minutes:
                    session.duration_minutes = duration_minutes
                logger.info(f"Ended session: {session.name}")
                return True
        return False
    
    def add_event(self, campaign_id: str, event_type: EventType, title: str,
                 description: str, session_id: Optional[str] = None, **kwargs) -> Optional[CampaignEvent]:
        """Add an event to a campaign."""
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return None
        
        event = CampaignEvent(
            type=event_type,
            title=title,
            description=description,
            session_id=session_id or "",
            **kwargs
        )
        
        campaign.events.append(event)
        campaign.updated_at = datetime.now()
        
        logger.info(f"Added event to {campaign.name}: {title}")
        return event
    
    def create_plot_thread(self, campaign_id: str, name: str, description: str,
                          importance: str = "minor", **kwargs) -> Optional[PlotThread]:
        """Create a new plot thread."""
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return None
        
        plot_thread = PlotThread(
            name=name,
            description=description,
            importance=importance,
            **kwargs
        )
        
        campaign.plot_threads[plot_thread.id] = plot_thread
        campaign.updated_at = datetime.now()
        
        logger.info(f"Created plot thread in {campaign.name}: {name}")
        return plot_thread
    
    def add_npc(self, campaign_id: str, name: str, description: str = "",
               role: str = "neutral", **kwargs) -> Optional[NPC]:
        """Add an NPC to a campaign."""
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return None
        
        npc = NPC(
            name=name,
            description=description,
            role=role,
            **kwargs
        )
        
        campaign.npcs[npc.id] = npc
        campaign.updated_at = datetime.now()
        
        logger.info(f"Added NPC to {campaign.name}: {name}")
        return npc
    
    def add_location(self, campaign_id: str, name: str, description: str = "",
                    location_type: str = "", **kwargs) -> Optional[Location]:
        """Add a location to a campaign."""
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return None
        
        location = Location(
            name=name,
            description=description,
            type=location_type,
            **kwargs
        )
        
        campaign.locations[location.id] = location
        campaign.updated_at = datetime.now()
        
        logger.info(f"Added location to {campaign.name}: {name}")
        return location
    
    def create_quest(self, campaign_id: str, name: str, description: str = "",
                    quest_type: str = "side", giver: Optional[str] = None,
                    **kwargs) -> Optional[Quest]:
        """Create a quest for a campaign."""
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return None
        
        quest = Quest(
            name=name,
            description=description,
            type=quest_type,
            giver=giver,
            **kwargs
        )
        
        campaign.quests[quest.id] = quest
        campaign.updated_at = datetime.now()
        
        logger.info(f"Created quest in {campaign.name}: {name}")
        return quest
    
    def award_experience(self, campaign_id: str, session_id: str,
                        character_awards: Dict[str, int]) -> bool:
        """Award experience points to characters."""
        campaign = self.get_campaign(campaign_id)
        if not campaign or session_id not in campaign.sessions:
            return False
        
        session = campaign.sessions[session_id]
        session.experience_awarded.update(character_awards)
        
        # Add event for XP award
        total_xp = sum(character_awards.values())
        self.add_event(
            campaign_id,
            EventType.LEVEL_UP,
            f"Experience Awarded",
            f"Awarded {total_xp} total XP to party",
            session_id
        )
        
        logger.info(f"Awarded XP in session {session.name}: {character_awards}")
        return True
    
    def get_campaign_timeline(self, campaign_id: str) -> List[CampaignEvent]:
        """Get the timeline of events for a campaign."""
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return []
        
        # Sort events by timestamp
        return sorted(campaign.events, key=lambda x: x.timestamp)
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a session."""
        for campaign in self.campaigns.values():
            if session_id in campaign.sessions:
                session = campaign.sessions[session_id]
                
                # Get events from this session
                session_events = [e for e in campaign.events if e.session_id == session_id]
                
                return {
                    "session": session,
                    "events": session_events,
                    "npcs_met": [campaign.npcs.get(npc_id) for npc_id in session.npcs_encountered],
                    "locations_visited": [campaign.locations.get(loc_id) for loc_id in session.locations_visited],
                    "quests_advanced": [campaign.quests.get(q_id) for q_id in session.quests_progressed]
                }
        
        return None
    
    def get_campaign_statistics(self, campaign_id: str) -> Dict[str, Any]:
        """Get statistics for a campaign."""
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return {}
        
        completed_sessions = [s for s in campaign.sessions.values() 
                            if s.status == SessionStatus.COMPLETED]
        
        total_playtime = sum(s.duration_minutes for s in completed_sessions)
        
        return {
            "total_sessions": len(campaign.sessions),
            "completed_sessions": len(completed_sessions),
            "total_playtime_hours": total_playtime / 60,
            "average_session_length": total_playtime / len(completed_sessions) if completed_sessions else 0,
            "total_events": len(campaign.events),
            "active_plot_threads": len([p for p in campaign.plot_threads.values() if p.status == "active"]),
            "total_npcs": len(campaign.npcs),
            "total_locations": len(campaign.locations),
            "active_quests": len([q for q in campaign.quests.values() if q.status in ["available", "accepted"]]),
            "campaign_age_days": (datetime.now() - campaign.created_at).days
        }
    
    def export_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Export a campaign to a dictionary for backup/sharing."""
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return {}
        
        def serialize_datetime(obj):
            """Helper to serialize datetime objects."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: serialize_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_datetime(item) for item in obj]
            else:
                return obj
        
        # Convert campaign to dict and serialize datetimes
        campaign_dict = {
            "id": campaign.id,
            "name": campaign.name,
            "description": campaign.description,
            "game_system": campaign.game_system,
            "status": campaign.status.value,
            "dm_id": campaign.dm_id,
            "player_ids": campaign.player_ids,
            "character_ids": campaign.character_ids,
            "created_at": campaign.created_at.isoformat(),
            "updated_at": campaign.updated_at.isoformat(),
            "sessions": {
                k: serialize_datetime({
                    "id": v.id,
                    "name": v.name,
                    "session_number": v.session_number,
                    "date": v.date.isoformat(),
                    "status": v.status.value,
                    "duration_minutes": v.duration_minutes,
                    "notes": v.notes,
                    "participants": v.participants
                })
                for k, v in campaign.sessions.items()
            },
            "events": [serialize_datetime({
                "id": e.id,
                "type": e.type.value,
                "title": e.title,
                "description": e.description,
                "timestamp": e.timestamp.isoformat(),
                "session_id": e.session_id,
                "characters_involved": e.characters_involved
            }) for e in campaign.events],
            "npcs": {
                k: serialize_datetime({
                    "id": v.id,
                    "name": v.name,
                    "description": v.description,
                    "role": v.role,
                    "location": v.location,
                    "alive": v.alive
                })
                for k, v in campaign.npcs.items()
            },
            "locations": {
                k: serialize_datetime({
                    "id": v.id,
                    "name": v.name,
                    "description": v.description,
                    "type": v.type,
                    "discovered": v.discovered
                })
                for k, v in campaign.locations.items()
            },
            "quests": {
                k: serialize_datetime({
                    "id": v.id,
                    "name": v.name,
                    "description": v.description,
                    "status": v.status,
                    "type": v.type,
                    "created_date": v.created_date.isoformat()
                })
                for k, v in campaign.quests.items()
            }
        }
        
        return campaign_dict
    
    def import_campaign(self, campaign_data: Dict[str, Any]) -> Optional[str]:
        """Import a campaign from exported data."""
        try:
            # Create basic campaign
            campaign = EnhancedCampaign(
                id=campaign_data["id"],
                name=campaign_data["name"],
                description=campaign_data["description"],
                game_system=campaign_data["game_system"],
                dm_id=campaign_data["dm_id"],
                player_ids=campaign_data["player_ids"],
                character_ids=campaign_data["character_ids"],
                created_at=datetime.fromisoformat(campaign_data["created_at"]),
                updated_at=datetime.fromisoformat(campaign_data["updated_at"])
            )
            
            # Import sessions
            for session_data in campaign_data.get("sessions", {}).values():
                session = EnhancedSession(
                    id=session_data["id"],
                    campaign_id=campaign.id,
                    name=session_data["name"],
                    session_number=session_data["session_number"],
                    date=datetime.fromisoformat(session_data["date"]),
                    status=SessionStatus(session_data["status"]),
                    duration_minutes=session_data["duration_minutes"],
                    notes=session_data["notes"],
                    participants=session_data["participants"]
                )
                campaign.sessions[session.id] = session
            
            # Import events
            for event_data in campaign_data.get("events", []):
                event = CampaignEvent(
                    id=event_data["id"],
                    type=EventType(event_data["type"]),
                    title=event_data["title"],
                    description=event_data["description"],
                    timestamp=datetime.fromisoformat(event_data["timestamp"]),
                    session_id=event_data["session_id"],
                    characters_involved=event_data["characters_involved"]
                )
                campaign.events.append(event)
            
            # Import NPCs
            for npc_data in campaign_data.get("npcs", {}).values():
                npc = NPC(
                    id=npc_data["id"],
                    name=npc_data["name"],
                    description=npc_data["description"],
                    role=npc_data["role"],
                    location=npc_data["location"],
                    alive=npc_data["alive"]
                )
                campaign.npcs[npc.id] = npc
            
            # Import locations
            for loc_data in campaign_data.get("locations", {}).values():
                location = Location(
                    id=loc_data["id"],
                    name=loc_data["name"],
                    description=loc_data["description"],
                    type=loc_data["type"],
                    discovered=loc_data["discovered"]
                )
                campaign.locations[location.id] = location
            
            # Import quests
            for quest_data in campaign_data.get("quests", {}).values():
                quest = Quest(
                    id=quest_data["id"],
                    name=quest_data["name"],
                    description=quest_data["description"],
                    status=quest_data["status"],
                    type=quest_data["type"],
                    created_date=datetime.fromisoformat(quest_data["created_date"])
                )
                campaign.quests[quest.id] = quest
            
            self.campaigns[campaign.id] = campaign
            logger.info(f"Imported campaign: {campaign.name}")
            return campaign.id
            
        except Exception as e:
            logger.error(f"Failed to import campaign: {e}")
            return None


# Global campaign manager
default_campaign_manager = CampaignManager()


def create_campaign(name: str, description: str, game_system: str, dm_id: str) -> EnhancedCampaign:
    """Convenience function to create a campaign."""
    return default_campaign_manager.create_campaign(name, description, game_system, dm_id)


def get_active_campaign() -> Optional[EnhancedCampaign]:
    """Convenience function to get the active campaign."""
    return default_campaign_manager.get_active_campaign()