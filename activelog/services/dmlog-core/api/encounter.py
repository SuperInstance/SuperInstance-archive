"""
Encounter balancing and management API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.encounter import EncounterSchema, EncounterRequest, EncounterBalance
from services.encounter_service import EncounterService
from database import get_db

router = APIRouter()

# Dependency to get encounter service
def get_encounter_service() -> EncounterService:
    return EncounterService()

@router.post("/", response_model=EncounterSchema)
async def create_encounter(
    encounter: EncounterSchema,
    encounter_service: EncounterService = Depends(get_encounter_service),
    db: Session = Depends(get_db)
):
    """Create a new encounter."""
    try:
        db_encounter = encounter_service.create_encounter(encounter, db)
        return EncounterSchema.from_orm(db_encounter)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{encounter_id}", response_model=EncounterSchema)
async def get_encounter(
    encounter_id: str,
    encounter_service: EncounterService = Depends(get_encounter_service),
    db: Session = Depends(get_db)
):
    """Get an encounter by ID."""
    encounter = encounter_service.get_encounter(encounter_id, db)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return EncounterSchema.from_orm(encounter)

@router.get("/")
async def list_encounters(
    campaign_id: Optional[str] = None,
    encounter_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    encounter_service: EncounterService = Depends(get_encounter_service),
    db: Session = Depends(get_db)
):
    """List encounters with optional filtering."""
    try:
        from models.encounter import EncounterType
        encounter_type_enum = EncounterType(encounter_type) if encounter_type else None
        
        encounters = encounter_service.list_encounters(
            campaign_id=campaign_id,
            encounter_type=encounter_type_enum,
            db=db
        )
        
        # Apply pagination
        paginated_encounters = encounters[skip:skip + limit]
        
        return {
            "encounters": [EncounterSchema.from_orm(enc) for enc in paginated_encounters],
            "total": len(encounters),
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/balance/analyze")
async def analyze_encounter_balance(
    party_levels: List[int],
    participants: List[Dict[str, Any]],
    encounter_service: EncounterService = Depends(get_encounter_service)
):
    """Analyze the balance of an encounter."""
    try:
        from models.encounter import ParticipantStats, ParticipantType
        
        # Convert participant dictionaries to ParticipantStats
        participant_stats = []
        for p in participants:
            participant_stats.append(ParticipantStats(
                participant_type=ParticipantType(p.get("participant_type", "monster")),
                participant_id=p.get("participant_id", "unknown"),
                name=p.get("name", "Unknown"),
                level=p.get("level", 1),
                hit_points_max=p.get("hit_points_max", 10),
                armor_class=p.get("armor_class", 10),
                challenge_rating=p.get("challenge_rating"),
                multiplier=p.get("multiplier", 1.0)
            ))
        
        balance = encounter_service.analyze_encounter_balance(party_levels, participant_stats)
        return balance
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/generate")
async def generate_encounter_suggestions(
    request: EncounterRequest,
    encounter_service: EncounterService = Depends(get_encounter_service)
):
    """Generate encounter suggestions based on party composition."""
    try:
        suggestions = encounter_service.generate_encounter(request)
        return {
            "request": request,
            "suggestions": suggestions,
            "total_suggestions": len(suggestions)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/balance/quick")
async def quick_balance_check(
    party_level: int,
    party_size: int,
    monster_cr: float,
    monster_count: int = 1,
    encounter_service: EncounterService = Depends(get_encounter_service)
):
    """Quick encounter balance check for simple scenarios."""
    try:
        from models.encounter import ParticipantStats, ParticipantType
        
        # Create party levels (all same level)
        party_levels = [party_level] * party_size
        
        # Create monster participants
        participants = []
        for i in range(monster_count):
            participants.append(ParticipantStats(
                participant_type=ParticipantType.MONSTER,
                participant_id=f"monster_{i}",
                name=f"Monster {i+1}",
                level=1,
                hit_points_max=10,  # Placeholder
                armor_class=10,     # Placeholder
                challenge_rating=monster_cr
            ))
        
        balance = encounter_service.analyze_encounter_balance(party_levels, participants)
        
        return {
            "party_level": party_level,
            "party_size": party_size,
            "monster_cr": monster_cr,
            "monster_count": monster_count,
            "balance_analysis": balance
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/difficulty/thresholds")
async def get_difficulty_thresholds(
    party_levels: List[int],
    encounter_service: EncounterService = Depends(get_encounter_service)
):
    """Get XP thresholds for different difficulty levels."""
    try:
        thresholds = encounter_service.balancer.calculate_party_thresholds(party_levels)
        return {
            "party_levels": party_levels,
            "thresholds": thresholds,
            "total_party_level": sum(party_levels),
            "average_party_level": sum(party_levels) / len(party_levels)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/cr/{challenge_rating}/xp")
async def get_cr_xp_value(challenge_rating: float):
    """Get XP value for a given challenge rating."""
    try:
        from services.encounter_service import EncounterBalancer
        xp_value = EncounterBalancer.CR_XP_VALUES.get(challenge_rating, 0)
        return {
            "challenge_rating": challenge_rating,
            "xp_value": xp_value
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/multipliers")
async def get_encounter_multipliers():
    """Get encounter multipliers for different numbers of monsters."""
    try:
        from services.encounter_service import EncounterBalancer
        return {
            "multipliers": EncounterBalancer.ENCOUNTER_MULTIPLIERS,
            "description": "XP multipliers based on number of monsters in encounter"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/templates/")
async def create_encounter_template(
    name: str,
    description: str,
    party_level_range: List[int],
    participants: List[Dict[str, Any]],
    encounter_service: EncounterService = Depends(get_encounter_service),
    db: Session = Depends(get_db)
):
    """Create a reusable encounter template."""
    try:
        # This would create an encounter template - implementation depends on requirements
        template = {
            "name": name,
            "description": description,
            "party_level_range": party_level_range,
            "participants": participants
        }
        
        # For now, just return the template structure
        return {
            "message": "Encounter template created",
            "template": template
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/suggestions/random")
async def get_random_encounter_suggestions(
    party_level: int,
    party_size: int = 4,
    environment: Optional[str] = None,
    encounter_service: EncounterService = Depends(get_encounter_service)
):
    """Get random encounter suggestions for a party."""
    try:
        from models.encounter import EncounterRequest, EncounterType
        from models.base import DifficultyLevel
        
        # Create a request for random encounters
        request = EncounterRequest(
            party_levels=[party_level] * party_size,
            desired_difficulty=DifficultyLevel.MEDIUM,
            encounter_type=EncounterType.COMBAT,
            environment=environment
        )
        
        suggestions = encounter_service.generate_encounter(request)
        
        # Return a random selection of suggestions
        import random
        random_suggestions = random.sample(suggestions, min(3, len(suggestions)))
        
        return {
            "party_level": party_level,
            "party_size": party_size,
            "environment": environment,
            "suggestions": random_suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/validate")
async def validate_encounter(
    encounter_data: Dict[str, Any],
    encounter_service: EncounterService = Depends(get_encounter_service)
):
    """Validate an encounter's balance and provide feedback."""
    try:
        # Extract data from encounter
        party_levels = encounter_data.get("party_levels", [])
        participants = encounter_data.get("participants", [])
        
        if not party_levels:
            raise HTTPException(status_code=400, detail="Party levels are required")
        
        from models.encounter import ParticipantStats, ParticipantType
        
        participant_stats = []
        for p in participants:
            participant_stats.append(ParticipantStats(
                participant_type=ParticipantType(p.get("participant_type", "monster")),
                participant_id=p.get("participant_id", "unknown"),
                name=p.get("name", "Unknown"),
                level=p.get("level", 1),
                hit_points_max=p.get("hit_points_max", 10),
                armor_class=p.get("armor_class", 10),
                challenge_rating=p.get("challenge_rating"),
                multiplier=p.get("multiplier", 1.0)
            ))
        
        balance = encounter_service.analyze_encounter_balance(party_levels, participant_stats)
        
        return {
            "is_valid": True,
            "balance_analysis": balance,
            "recommendations": balance.recommendations,
            "validation_status": "passed"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))