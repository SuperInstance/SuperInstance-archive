"""
NPC generation and management API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.npc import NPCSchema, NPCGenerationRequest, PersonalityProfile
from services.npc_service import NPCService
from database import get_db

router = APIRouter()

# Dependency to get NPC service
def get_npc_service() -> NPCService:
    return NPCService()

@router.post("/generate")
async def generate_npc(
    request: NPCGenerationRequest,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Generate a new NPC with personality, stats, and backstory."""
    try:
        generated_npc = npc_service.generate_npc(request, db)
        return {
            "message": "NPC generated successfully",
            "npc": generated_npc
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/", response_model=NPCSchema)
async def create_npc(
    npc: NPCSchema,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Create a new NPC manually."""
    try:
        db_npc = npc_service.create_npc(npc, db)
        return NPCSchema.from_orm(db_npc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[NPCSchema])
async def list_npcs(
    skip: int = 0,
    limit: int = 50,
    campaign_id: Optional[str] = None,
    location: Optional[str] = None,
    faction: Optional[str] = None,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """List NPCs with optional filtering."""
    try:
        npcs = npc_service.list_npcs(
            skip=skip,
            limit=limit,
            campaign_id=campaign_id,
            location=location,
            faction=faction,
            db=db
        )
        return [NPCSchema.from_orm(npc) for npc in npcs]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{npc_id}", response_model=NPCSchema)
async def get_npc(
    npc_id: str,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Get a specific NPC by ID."""
    npc = npc_service.get_npc(npc_id, db)
    if not npc:
        raise HTTPException(status_code=404, detail="NPC not found")
    return NPCSchema.from_orm(npc)

@router.put("/{npc_id}", response_model=NPCSchema)
async def update_npc(
    npc_id: str,
    npc_update: NPCSchema,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Update an existing NPC."""
    try:
        updated_npc = npc_service.update_npc(npc_id, npc_update, db)
        if not updated_npc:
            raise HTTPException(status_code=404, detail="NPC not found")
        return NPCSchema.from_orm(updated_npc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{npc_id}")
async def delete_npc(
    npc_id: str,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Delete an NPC."""
    try:
        success = npc_service.delete_npc(npc_id, db)
        if not success:
            raise HTTPException(status_code=404, detail="NPC not found")
        return {"message": "NPC deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{npc_id}/personality/analyze")
async def analyze_personality(
    npc_id: str,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Analyze and generate personality insights for an NPC."""
    try:
        analysis = npc_service.analyze_personality(npc_id, db)
        return {
            "npc_id": npc_id,
            "personality_analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/generate/quick")
async def quick_generate_npc(
    name: Optional[str] = None,
    role: Optional[str] = None,
    location: Optional[str] = None,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Quickly generate an NPC with minimal parameters."""
    try:
        from models.npc import NPCGenerationRequest
        request = NPCGenerationRequest(
            name=name,
            role=role,
            location=location,
            include_stats=True,
            include_personality=True,
            include_backstory=True
        )
        
        generated_npc = npc_service.generate_npc(request, db)
        return {
            "message": "Quick NPC generated",
            "npc": generated_npc
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/campaign/{campaign_id}/by-location")
async def get_npcs_by_location(
    campaign_id: str,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Get NPCs grouped by location for a campaign."""
    try:
        npcs_by_location = npc_service.get_npcs_by_location(campaign_id, db)
        return {
            "campaign_id": campaign_id,
            "locations": npcs_by_location
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/campaign/{campaign_id}/by-faction")
async def get_npcs_by_faction(
    campaign_id: str,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Get NPCs grouped by faction for a campaign."""
    try:
        npcs_by_faction = npc_service.get_npcs_by_faction(campaign_id, db)
        return {
            "campaign_id": campaign_id,
            "factions": npcs_by_faction
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{npc_id}/interactions/")
async def add_interaction(
    npc_id: str,
    interaction_title: str,
    interaction_description: str,
    session_number: Optional[int] = None,
    participants: Optional[List[str]] = None,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Add an interaction record for an NPC."""
    try:
        interaction = npc_service.add_interaction(
            npc_id=npc_id,
            title=interaction_title,
            description=interaction_description,
            session_number=session_number,
            participants=participants,
            db=db
        )
        return {
            "message": "Interaction added successfully",
            "interaction": interaction
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{npc_id}/interactions/")
async def get_npc_interactions(
    npc_id: str,
    limit: int = 20,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Get interaction history for an NPC."""
    try:
        interactions = npc_service.get_npc_interactions(npc_id, limit, db)
        return {
            "npc_id": npc_id,
            "interactions": interactions,
            "total_interactions": len(interactions)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/search")
async def search_npcs(
    query: str,
    campaign_id: Optional[str] = None,
    limit: int = 20,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Search NPCs by name, description, or other attributes."""
    try:
        results = npc_service.search_npcs(query, campaign_id, limit, db)
        return {
            "query": query,
            "results": [NPCSchema.from_orm(npc) for npc in results],
            "total_found": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/generate/batch")
async def generate_multiple_npcs(
    count: int,
    base_request: NPCGenerationRequest,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Generate multiple NPCs at once."""
    try:
        if count > 20:
            raise HTTPException(status_code=400, detail="Cannot generate more than 20 NPCs at once")
        
        generated_npcs = []
        for _ in range(count):
            npc = npc_service.generate_npc(base_request, db)
            generated_npcs.append(npc)
        
        return {
            "message": f"Generated {count} NPCs successfully",
            "npcs": generated_npcs,
            "count": len(generated_npcs)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/roles")
async def get_available_roles():
    """Get list of available NPC roles."""
    from models.npc import NPCRole
    return {
        "roles": [role.value for role in NPCRole],
        "descriptions": {
            "merchant": "Shopkeeper, trader, or vendor",
            "guard": "City watch, bouncer, or security",
            "noble": "Aristocrat, politician, or court official",
            "commoner": "Farmer, laborer, or ordinary citizen",
            "scholar": "Sage, researcher, or academic",
            "priest": "Cleric, temple worker, or religious figure",
            "criminal": "Thief, smuggler, or outlaw",
            "artisan": "Crafter, blacksmith, or skilled worker",
            "entertainer": "Bard, actor, or performer",
            "soldier": "Military personnel or warrior",
            "innkeeper": "Tavern or inn owner/worker",
            "traveler": "Adventurer, pilgrim, or wanderer"
        }
    }

@router.get("/{npc_id}/stats/combat")
async def get_combat_stats(
    npc_id: str,
    npc_service: NPCService = Depends(get_npc_service),
    db: Session = Depends(get_db)
):
    """Get combat-ready stats for an NPC."""
    try:
        stats = npc_service.get_combat_stats(npc_id, db)
        return {
            "npc_id": npc_id,
            "combat_stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))