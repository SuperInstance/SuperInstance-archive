"""
Experience and leveling API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.experience import (
    ExperienceGainSchema, LevelProgressionSchema, MilestoneSchema,
    ExperienceAward, LevelUpRequest, ExperienceCalculation
)
from services.experience_service import ExperienceService
from database import get_db

router = APIRouter()

# Dependency to get experience service
def get_experience_service() -> ExperienceService:
    return ExperienceService()

@router.post("/award")
async def award_experience(
    award: ExperienceAward,
    experience_service: ExperienceService = Depends(get_experience_service),
    db: Session = Depends(get_db)
):
    """Award experience points to characters."""
    try:
        gains = experience_service.award_experience(award, db)
        return {
            "message": f"Awarded {award.amount} XP to {len(award.character_ids)} characters",
            "experience_type": award.experience_type.value,
            "total_awarded": award.amount * len(award.character_ids),
            "experience_gains": [ExperienceGainSchema.from_orm(gain) for gain in gains]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/calculate")
async def calculate_experience(
    experience_type: str,
    parameters: Dict[str, Any],
    experience_service: ExperienceService = Depends(get_experience_service)
):
    """Calculate experience points for different activities."""
    try:
        from models.experience import ExperienceType
        exp_type = ExperienceType(experience_type)
        
        calculation = experience_service.calculate_experience(exp_type, **parameters)
        return calculation
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/levelup")
async def level_up_character(
    request: LevelUpRequest,
    experience_service: ExperienceService = Depends(get_experience_service),
    db: Session = Depends(get_db)
):
    """Level up a character manually."""
    try:
        progression = experience_service.level_up_character(request, db)
        return {
            "message": f"Character leveled up to level {request.new_level}",
            "progression": LevelProgressionSchema.from_orm(progression)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/characters/{character_id}/progression")
async def get_character_progression(
    character_id: str,
    experience_service: ExperienceService = Depends(get_experience_service),
    db: Session = Depends(get_db)
):
    """Get comprehensive progression data for a character."""
    try:
        progression = experience_service.get_character_progression(character_id, db)
        return progression
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/milestones/", response_model=MilestoneSchema)
async def create_milestone(
    milestone: MilestoneSchema,
    experience_service: ExperienceService = Depends(get_experience_service),
    db: Session = Depends(get_db)
):
    """Create a new milestone for a campaign."""
    try:
        db_milestone = experience_service.create_milestone(milestone, db)
        return MilestoneSchema.from_orm(db_milestone)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/milestones/{milestone_id}/complete")
async def complete_milestone(
    milestone_id: str,
    character_ids: List[str],
    experience_service: ExperienceService = Depends(get_experience_service),
    db: Session = Depends(get_db)
):
    """Complete a milestone and award experience."""
    try:
        milestone = experience_service.complete_milestone(milestone_id, character_ids, db)
        return {
            "message": f"Milestone '{milestone.milestone_name}' completed",
            "experience_awarded": milestone.experience_value,
            "characters_affected": len(character_ids),
            "milestone": MilestoneSchema.from_orm(milestone)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/combat/calculate")
async def calculate_combat_experience(
    monster_cr: float,
    party_size: int,
    outcome: str = "kill",
    experience_service: ExperienceService = Depends(get_experience_service)
):
    """Calculate experience for combat encounters."""
    try:
        xp_per_character = experience_service.calculator.calculate_combat_xp(
            monster_cr, party_size, outcome
        )
        total_xp = xp_per_character * party_size
        
        return {
            "monster_cr": monster_cr,
            "party_size": party_size,
            "outcome": outcome,
            "xp_per_character": xp_per_character,
            "total_encounter_xp": total_xp,
            "breakdown": {
                "base_xp": experience_service.calculator.calculator.CR_XP_VALUES.get(monster_cr, 0) if hasattr(experience_service.calculator, 'calculator') else 0,
                "outcome_multiplier": experience_service.calculator.COMBAT_XP_BASE.get(outcome, 1.0),
                "party_division": party_size
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tables/xp-by-level")
async def get_xp_requirements():
    """Get XP requirements for each character level."""
    try:
        from services.experience_service import LevelingSystem
        return {
            "xp_table": LevelingSystem.DND5E_XP_TABLE,
            "game_system": "D&D 5e",
            "max_level": 20
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tables/proficiency-bonus")
async def get_proficiency_bonus_table():
    """Get proficiency bonus progression by level."""
    try:
        from services.experience_service import LevelingSystem
        return {
            "proficiency_table": LevelingSystem.PROFICIENCY_BONUS,
            "description": "Proficiency bonus by character level"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/quest/calculate")
async def calculate_quest_experience(
    base_xp: int,
    quest_type: str = "side_quest",
    difficulty_multiplier: float = 1.0,
    experience_service: ExperienceService = Depends(get_experience_service)
):
    """Calculate experience for quest completion."""
    try:
        xp_awarded = experience_service.calculator.calculate_quest_xp(
            base_xp, quest_type, difficulty_multiplier
        )
        
        return {
            "base_xp": base_xp,
            "quest_type": quest_type,
            "difficulty_multiplier": difficulty_multiplier,
            "final_xp": xp_awarded,
            "type_multiplier": experience_service.calculator.QUEST_XP_MULTIPLIERS.get(quest_type, 1.0)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/discovery/calculate")
async def calculate_discovery_experience(
    discovery_type: str,
    significance_multiplier: float = 1.0,
    experience_service: ExperienceService = Depends(get_experience_service)
):
    """Calculate experience for discoveries."""
    try:
        xp_awarded = experience_service.calculator.calculate_discovery_xp(
            discovery_type, significance_multiplier
        )
        
        return {
            "discovery_type": discovery_type,
            "significance_multiplier": significance_multiplier,
            "final_xp": xp_awarded,
            "base_value": experience_service.calculator.DISCOVERY_XP_VALUES.get(discovery_type, 25)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/roleplay/calculate")
async def calculate_roleplay_experience(
    character_level: int,
    quality_multiplier: float = 1.0,
    experience_service: ExperienceService = Depends(get_experience_service)
):
    """Calculate experience for roleplay activities."""
    try:
        xp_awarded = experience_service.calculator.calculate_roleplay_xp(
            character_level, quality_multiplier
        )
        
        return {
            "character_level": character_level,
            "quality_multiplier": quality_multiplier,
            "final_xp": xp_awarded,
            "base_calculation": f"max(10, {character_level} * 5) = {max(10, character_level * 5)}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/level/{level}/features")
async def get_level_features(
    level: int,
    character_class: str = "fighter",
    experience_service: ExperienceService = Depends(get_experience_service)
):
    """Get class features gained at a specific level."""
    try:
        features = experience_service.leveling_system.get_class_features(character_class, level)
        spell_slots = experience_service.leveling_system.get_spell_slots(character_class, level)
        proficiency_bonus = experience_service.leveling_system.get_proficiency_bonus(level)
        
        return {
            "level": level,
            "character_class": character_class,
            "features": features,
            "spell_slots": spell_slots,
            "proficiency_bonus": proficiency_bonus
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/batch/award")
async def batch_award_experience(
    awards: List[ExperienceAward],
    experience_service: ExperienceService = Depends(get_experience_service),
    db: Session = Depends(get_db)
):
    """Award experience to multiple groups of characters."""
    try:
        all_gains = []
        total_awards = 0
        
        for award in awards:
            gains = experience_service.award_experience(award, db)
            all_gains.extend(gains)
            total_awards += len(gains)
        
        return {
            "message": f"Processed {len(awards)} award batches",
            "total_individual_awards": total_awards,
            "experience_gains": [ExperienceGainSchema.from_orm(gain) for gain in all_gains]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/campaigns/{campaign_id}/milestones")
async def get_campaign_milestones(
    campaign_id: str,
    include_completed: bool = True,
    experience_service: ExperienceService = Depends(get_experience_service),
    db: Session = Depends(get_db)
):
    """Get milestones for a campaign."""
    try:
        # This would require extending the service to query milestones by campaign
        # For now, return a placeholder structure
        return {
            "campaign_id": campaign_id,
            "milestones": [],
            "message": "Milestone querying by campaign not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))