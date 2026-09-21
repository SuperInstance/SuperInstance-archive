"""
Combat tracking API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.combat import CombatEncounterSchema, CombatParticipantSchema
from services.combat_service import CombatService
from database import get_db

router = APIRouter()

# Dependency to get combat service
def get_combat_service() -> CombatService:
    return CombatService()

@router.post("/encounters/", response_model=CombatEncounterSchema)
async def create_encounter(
    encounter: CombatEncounterSchema, 
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """Create a new combat encounter."""
    try:
        db_encounter = combat_service.create_encounter(encounter, db)
        return CombatEncounterSchema.from_orm(db_encounter)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/encounters/{encounter_id}", response_model=CombatEncounterSchema)
async def get_encounter(
    encounter_id: str, 
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """Get a combat encounter by ID."""
    encounter = combat_service.get_encounter(encounter_id, db)
    if not encounter:
        raise HTTPException(status_code=404, detail="Combat encounter not found")
    return CombatEncounterSchema.from_orm(encounter)

@router.post("/encounters/{encounter_id}/start")
async def start_encounter(
    encounter_id: str,
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """Start a combat encounter and roll initiative."""
    try:
        encounter = combat_service.start_encounter(encounter_id, db)
        return {
            "message": "Combat encounter started",
            "encounter_id": encounter.id,
            "current_turn": encounter.current_turn,
            "initiative_order": combat_service.get_initiative_order(encounter_id, db)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/encounters/{encounter_id}/next-turn")
async def next_turn(
    encounter_id: str,
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """Advance to the next turn in combat."""
    try:
        encounter = combat_service.next_turn(encounter_id, db)
        return {
            "message": "Advanced to next turn",
            "current_turn": encounter.current_turn,
            "current_round": encounter.current_round,
            "active_participant": combat_service.get_current_participant(encounter_id, db)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/encounters/{encounter_id}/participants/", response_model=CombatParticipantSchema)
async def add_participant(
    encounter_id: str,
    participant: CombatParticipantSchema,
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """Add a participant to a combat encounter."""
    try:
        participant.encounter_id = encounter_id
        db_participant = combat_service.add_participant(participant, db)
        return CombatParticipantSchema.from_orm(db_participant)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/encounters/{encounter_id}/actions/")
async def perform_action(
    encounter_id: str,
    action: Dict[str, Any],
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """Perform a combat action."""
    try:
        result = combat_service.perform_action(encounter_id, action, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/participants/{participant_id}/damage")
async def apply_damage(
    participant_id: str,
    damage: int,
    damage_type: Optional[str] = None,
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """Apply damage to a combat participant."""
    try:
        result = combat_service.apply_damage(participant_id, damage, damage_type, db)
        return {
            "message": f"Applied {damage} {damage_type or ''} damage",
            "damage_dealt": result["damage_dealt"],
            "hit_points_remaining": result["hit_points_current"],
            "is_unconscious": result["is_unconscious"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/participants/{participant_id}/heal")
async def apply_healing(
    participant_id: str,
    healing: int,
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """Apply healing to a combat participant."""
    try:
        result = combat_service.apply_healing(participant_id, healing, db)
        return {
            "message": f"Applied {healing} healing",
            "healing_applied": result["healing_applied"],
            "hit_points_current": result["hit_points_current"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/participants/{participant_id}/conditions/")
async def add_condition(
    participant_id: str,
    condition_name: str,
    duration: Optional[int] = None,
    description: Optional[str] = None,
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """Add a condition to a combat participant."""
    try:
        combat_service.add_condition(participant_id, condition_name, duration, description, db)
        return {"message": f"Applied {condition_name} condition"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/participants/{participant_id}/conditions/{condition_name}")
async def remove_condition(
    participant_id: str,
    condition_name: str,
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """Remove a condition from a combat participant."""
    try:
        combat_service.remove_condition(participant_id, condition_name, db)
        return {"message": f"Removed {condition_name} condition"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/encounters/{encounter_id}/initiative")
async def get_initiative_order(
    encounter_id: str,
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """Get the initiative order for a combat encounter."""
    try:
        order = combat_service.get_initiative_order(encounter_id, db)
        return {"initiative_order": order}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/encounters/{encounter_id}/status")
async def get_encounter_status(
    encounter_id: str,
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """Get the current status of a combat encounter."""
    try:
        status = combat_service.get_encounter_status(encounter_id, db)
        return status
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/encounters/{encounter_id}/end")
async def end_encounter(
    encounter_id: str,
    combat_service: CombatService = Depends(get_combat_service),
    db: Session = Depends(get_db)
):
    """End a combat encounter."""
    try:
        encounter = combat_service.end_encounter(encounter_id, db)
        return {
            "message": "Combat encounter ended",
            "duration_rounds": encounter.current_round,
            "final_status": encounter.status
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))