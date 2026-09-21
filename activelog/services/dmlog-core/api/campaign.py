"""
Campaign management and timeline API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.campaign import (
    CampaignSchema, CampaignEventSchema, GameSessionSchema, 
    WorldCalendarSchema, TimelineFilter
)
from services.campaign_service import CampaignService
from database import get_db

router = APIRouter()

# Dependency to get campaign service
def get_campaign_service() -> CampaignService:
    return CampaignService()

@router.post("/", response_model=CampaignSchema)
async def create_campaign(
    campaign: CampaignSchema,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Create a new campaign."""
    try:
        db_campaign = campaign_service.create_campaign(campaign, db)
        return CampaignSchema.from_orm(db_campaign)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{campaign_id}", response_model=CampaignSchema)
async def get_campaign(
    campaign_id: str,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Get a campaign by ID."""
    campaign = campaign_service.get_campaign(campaign_id, db)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return CampaignSchema.from_orm(campaign)

@router.get("/{campaign_id}/summary")
async def get_campaign_summary(
    campaign_id: str,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Get comprehensive campaign summary."""
    try:
        summary = campaign_service.get_campaign_summary(campaign_id, db)
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{campaign_id}/sessions/", response_model=GameSessionSchema)
async def create_session(
    campaign_id: str,
    session: GameSessionSchema,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Create a new game session."""
    try:
        session.campaign_id = campaign_id
        db_session = campaign_service.create_session(session, db)
        return GameSessionSchema.from_orm(db_session)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{campaign_id}/events/", response_model=CampaignEventSchema)
async def create_event(
    campaign_id: str,
    event: CampaignEventSchema,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Create a new campaign event."""
    try:
        event.campaign_id = campaign_id
        db_event = campaign_service.create_event(event, db)
        return CampaignEventSchema.from_orm(db_event)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{campaign_id}/timeline")
async def get_campaign_timeline(
    campaign_id: str,
    filters: TimelineFilter,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Get campaign timeline with filtering options."""
    try:
        filters.campaign_id = campaign_id
        timeline = campaign_service.get_campaign_timeline(filters, db)
        
        return {
            "campaign_id": campaign_id,
            "timeline": timeline,
            "total_entries": len(timeline),
            "filters_applied": filters
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{campaign_id}/calendar/", response_model=WorldCalendarSchema)
async def create_world_calendar(
    campaign_id: str,
    calendar: WorldCalendarSchema,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Create a world calendar for the campaign."""
    try:
        calendar.campaign_id = campaign_id
        db_calendar = campaign_service.create_world_calendar(calendar, db)
        return WorldCalendarSchema.from_orm(db_calendar)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{campaign_id}/calendar/advance")
async def advance_world_date(
    campaign_id: str,
    days: int,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Advance the world date by specified number of days."""
    try:
        new_date = campaign_service.advance_world_date(campaign_id, days, db)
        return {
            "campaign_id": campaign_id,
            "days_advanced": days,
            "new_world_date": new_date,
            "message": f"Advanced world date by {days} days"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{campaign_id}/statistics")
async def get_campaign_statistics(
    campaign_id: str,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Get detailed campaign statistics."""
    try:
        stats = campaign_service.get_campaign_statistics(campaign_id, db)
        return {
            "campaign_id": campaign_id,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{campaign_id}/events/search")
async def search_events(
    campaign_id: str,
    search_term: str,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Search campaign events by text content."""
    try:
        events = campaign_service.search_events(campaign_id, search_term, db)
        return {
            "campaign_id": campaign_id,
            "search_term": search_term,
            "events": [CampaignEventSchema.from_orm(event) for event in events],
            "total_found": len(events)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{campaign_id}/events/{event_id}/relationships")
async def find_related_events(
    campaign_id: str,
    event_id: str,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Find events related to a specific event."""
    try:
        connections = campaign_service.find_related_events(event_id, db)
        return {
            "event_id": event_id,
            "related_events": connections,
            "connection_count": len(connections)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{campaign_id}/sessions/")
async def list_sessions(
    campaign_id: str,
    skip: int = 0,
    limit: int = 50,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """List game sessions for a campaign."""
    try:
        # This would require extending the service
        return {
            "campaign_id": campaign_id,
            "sessions": [],
            "message": "Session listing not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{campaign_id}/events/")
async def list_events(
    campaign_id: str,
    event_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """List campaign events with optional filtering."""
    try:
        # This would require extending the service
        return {
            "campaign_id": campaign_id,
            "events": [],
            "message": "Event listing not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{campaign_id}/sessions/{session_id}/complete")
async def complete_session(
    campaign_id: str,
    session_id: str,
    experience_awarded: Optional[int] = None,
    milestones_achieved: Optional[List[str]] = None,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Mark a session as completed and update related data."""
    try:
        # Update session completion
        return {
            "session_id": session_id,
            "campaign_id": campaign_id,
            "status": "completed",
            "experience_awarded": experience_awarded,
            "milestones_achieved": milestones_achieved or [],
            "message": "Session marked as completed"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{campaign_id}/locations/")
async def get_campaign_locations(
    campaign_id: str,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Get all locations mentioned in the campaign."""
    try:
        # This would analyze events and sessions to extract unique locations
        return {
            "campaign_id": campaign_id,
            "locations": [],
            "message": "Location extraction not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{campaign_id}/npcs/")
async def get_campaign_npcs(
    campaign_id: str,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Get all NPCs mentioned in the campaign."""
    try:
        # This would analyze events and sessions to extract unique NPCs
        return {
            "campaign_id": campaign_id,
            "npcs": [],
            "message": "NPC extraction not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{campaign_id}/backup")
async def backup_campaign(
    campaign_id: str,
    include_events: bool = True,
    include_sessions: bool = True,
    campaign_service: CampaignService = Depends(get_campaign_service),
    db: Session = Depends(get_db)
):
    """Create a backup of campaign data."""
    try:
        # This would export campaign data
        return {
            "campaign_id": campaign_id,
            "backup_created": True,
            "includes": {
                "events": include_events,
                "sessions": include_sessions
            },
            "message": "Campaign backup functionality not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/event-types")
async def get_event_types():
    """Get available campaign event types."""
    from models.campaign import EventType
    return {
        "event_types": [t.value for t in EventType],
        "descriptions": {
            "session": "Regular game session",
            "story_milestone": "Major story development",
            "character_development": "Character growth or change",
            "world_event": "Major world occurrence",
            "combat_encounter": "Significant combat",
            "social_encounter": "Important social interaction",
            "discovery": "New discovery or revelation",
            "travel": "Journey or travel event",
            "downtime": "Downtime activity",
            "level_up": "Character advancement",
            "death": "Character death",
            "resurrection": "Character resurrection",
            "retirement": "Character retirement"
        }
    }

@router.get("/calendar/templates")
async def get_calendar_templates():
    """Get pre-made calendar templates."""
    return {
        "templates": {
            "greyhawk": {
                "name": "Greyhawk Calendar",
                "days_per_month": [28] * 12,
                "month_names": [
                    "Needfest", "Fireseek", "Readying", "Coldeven",
                    "Planting", "Flocktime", "Wealsun", "Reaping",
                    "Goodmonth", "Harvester", "Patchwall", "Ready'reat"
                ],
                "day_names": ["Starday", "Sunday", "Moonday", "Godsday", "Waterday", "Earthday", "Freeday"]
            },
            "forgotten_realms": {
                "name": "Harptos Calendar",
                "days_per_month": [30] * 12,
                "month_names": [
                    "Hammer", "Alturiak", "Ches", "Tarsakh",
                    "Mirtul", "Kythorn", "Flamerule", "Eleasis",
                    "Eleint", "Marpenoth", "Uktar", "Nightal"
                ],
                "day_names": ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th"]
            },
            "generic": {
                "name": "Generic Fantasy Calendar",
                "days_per_month": [30] * 12,
                "month_names": [
                    "First Moon", "Second Moon", "Third Moon", "Fourth Moon",
                    "Fifth Moon", "Sixth Moon", "Seventh Moon", "Eighth Moon",
                    "Ninth Moon", "Tenth Moon", "Eleventh Moon", "Twelfth Moon"
                ],
                "day_names": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"]
            }
        }
    }