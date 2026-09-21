"""
Character management API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.character import (
    Character, CharacterSchema, CharacterTemplate, CharacterTemplateSchema,
    CharacterLevel, CharacterLevelSchema
)
from database import get_db

router = APIRouter()

@router.post("/", response_model=CharacterSchema)
async def create_character(character: CharacterSchema, db: Session = Depends(get_db)):
    """Create a new character."""
    try:
        db_character = Character(**character.dict(exclude={"id", "created_at", "updated_at"}))
        db.add(db_character)
        db.commit()
        db.refresh(db_character)
        return CharacterSchema.from_orm(db_character)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[CharacterSchema])
async def list_characters(
    skip: int = 0,
    limit: int = 100,
    game_system: Optional[str] = None,
    campaign_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List characters with optional filtering."""
    query = db.query(Character)
    
    if game_system:
        query = query.filter(Character.game_system == game_system)
    if campaign_id:
        query = query.filter(Character.campaign_id == campaign_id)
    
    characters = query.offset(skip).limit(limit).all()
    return [CharacterSchema.from_orm(char) for char in characters]

@router.get("/{character_id}", response_model=CharacterSchema)
async def get_character(character_id: str, db: Session = Depends(get_db)):
    """Get a specific character."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return CharacterSchema.from_orm(character)

@router.put("/{character_id}", response_model=CharacterSchema)
async def update_character(
    character_id: str, 
    character_update: CharacterSchema, 
    db: Session = Depends(get_db)
):
    """Update a character."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    try:
        update_data = character_update.dict(exclude={"id", "created_at"}, exclude_unset=True)
        for field, value in update_data.items():
            setattr(character, field, value)
        
        db.commit()
        db.refresh(character)
        return CharacterSchema.from_orm(character)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{character_id}")
async def delete_character(character_id: str, db: Session = Depends(get_db)):
    """Delete a character."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    try:
        db.delete(character)
        db.commit()
        return {"message": "Character deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{character_id}/level-up")
async def level_up_character(
    character_id: str,
    new_level: int,
    hit_points_gained: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Level up a character."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    if new_level <= character.level:
        raise HTTPException(status_code=400, detail="New level must be higher than current level")
    
    try:
        # Calculate HP gain if not provided
        if hit_points_gained is None:
            # Use average hit die value + CON modifier
            con_modifier = (character.attributes.get("constitution", {}).get("score", 10) - 10) // 2
            hit_die = 8  # Default, could be based on class
            hit_points_gained = (hit_die // 2) + 1 + con_modifier
            hit_points_gained = max(1, hit_points_gained)
        
        # Update character level and HP
        old_level = character.level
        character.level = new_level
        character.hit_points_max += hit_points_gained
        character.hit_points_current += hit_points_gained
        
        # Record level progression
        level_record = CharacterLevel(
            character_id=character.id,
            level=new_level,
            experience_required=0,  # Could calculate based on system
            hit_points_gained=hit_points_gained,
            features_gained=[],
            spell_slots_gained={}
        )
        
        db.add(level_record)
        db.commit()
        db.refresh(character)
        
        return {
            "message": f"Character leveled up from {old_level} to {new_level}",
            "hit_points_gained": hit_points_gained,
            "new_hit_points_max": character.hit_points_max
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{character_id}/summary")
async def get_character_summary(character_id: str, db: Session = Depends(get_db)):
    """Get a comprehensive character summary."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Calculate derived stats
    def calc_modifier(score):
        return (score - 10) // 2
    
    # Ability modifiers
    ability_mods = {}
    for ability, data in character.attributes.items():
        if isinstance(data, dict) and "score" in data:
            ability_mods[f"{ability}_modifier"] = calc_modifier(data["score"])
    
    # Proficiency bonus
    proficiency_bonus = ((character.level - 1) // 4) + 2
    
    # Skill bonuses
    skill_bonuses = {}
    for skill, data in character.skills.items():
        if isinstance(data, dict):
            base_ability = data.get("attribute", "strength")
            ability_mod = ability_mods.get(f"{base_ability}_modifier", 0)
            prof_bonus = proficiency_bonus if data.get("proficient", False) else 0
            expertise_bonus = proficiency_bonus if data.get("expertise", False) else 0
            skill_bonuses[skill] = ability_mod + prof_bonus + expertise_bonus
    
    # Combat stats
    ac = character.armor_class
    hp_current = character.hit_points_current
    hp_max = character.hit_points_max
    
    return {
        "character": CharacterSchema.from_orm(character),
        "derived_stats": {
            "ability_modifiers": ability_mods,
            "proficiency_bonus": proficiency_bonus,
            "skill_bonuses": skill_bonuses,
            "armor_class": ac,
            "hit_points": {
                "current": hp_current,
                "maximum": hp_max,
                "temporary": character.hit_points_temp,
                "percentage": (hp_current / hp_max * 100) if hp_max > 0 else 0
            },
            "is_bloodied": hp_current <= (hp_max // 2),
            "is_unconscious": hp_current <= 0
        }
    }

@router.post("/{character_id}/damage")
async def take_damage(
    character_id: str,
    damage: int,
    damage_type: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Apply damage to a character."""
    if damage < 0:
        raise HTTPException(status_code=400, detail="Damage must be positive")
    
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    try:
        # Apply damage (temp HP first)
        damage_taken = 0
        
        if character.hit_points_temp > 0:
            temp_damage = min(damage, character.hit_points_temp)
            character.hit_points_temp -= temp_damage
            damage -= temp_damage
            damage_taken += temp_damage
        
        if damage > 0:
            actual_damage = min(damage, character.hit_points_current)
            character.hit_points_current -= actual_damage
            damage_taken += actual_damage
        
        db.commit()
        db.refresh(character)
        
        return {
            "message": f"Character took {damage_taken} damage",
            "damage_taken": damage_taken,
            "damage_type": damage_type,
            "source": source,
            "hit_points": {
                "current": character.hit_points_current,
                "temporary": character.hit_points_temp,
                "maximum": character.hit_points_max
            },
            "is_unconscious": character.hit_points_current <= 0
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{character_id}/heal")
async def heal_character(
    character_id: str,
    healing: int,
    temporary: bool = False,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Heal a character."""
    if healing < 0:
        raise HTTPException(status_code=400, detail="Healing must be positive")
    
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    try:
        if temporary:
            # Temporary HP doesn't stack
            old_temp = character.hit_points_temp
            character.hit_points_temp = max(character.hit_points_temp, healing)
            actual_healing = character.hit_points_temp - old_temp
        else:
            # Regular healing
            max_healing = character.hit_points_max - character.hit_points_current
            actual_healing = min(healing, max_healing)
            character.hit_points_current += actual_healing
        
        db.commit()
        db.refresh(character)
        
        return {
            "message": f"Character healed for {actual_healing} {'temporary ' if temporary else ''}HP",
            "healing_applied": actual_healing,
            "temporary": temporary,
            "source": source,
            "hit_points": {
                "current": character.hit_points_current,
                "temporary": character.hit_points_temp,
                "maximum": character.hit_points_max
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# Template endpoints
@router.get("/templates/", response_model=List[CharacterTemplateSchema])
async def list_character_templates(
    game_system: Optional[str] = None,
    template_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List character templates."""
    query = db.query(CharacterTemplate)
    
    if game_system:
        query = query.filter(CharacterTemplate.game_system == game_system)
    if template_type:
        query = query.filter(CharacterTemplate.template_type == template_type)
    
    templates = query.all()
    return [CharacterTemplateSchema.from_orm(template) for template in templates]

@router.post("/templates/", response_model=CharacterTemplateSchema)
async def create_character_template(
    template: CharacterTemplateSchema, 
    db: Session = Depends(get_db)
):
    """Create a character template."""
    try:
        db_template = CharacterTemplate(**template.dict(exclude={"id", "created_at", "updated_at"}))
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        return CharacterTemplateSchema.from_orm(db_template)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))