"""
Spell and ability management API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.spells import SpellSchema
from services.spell_service import SpellService
from database import get_db

router = APIRouter()

# Dependency to get spell service
def get_spell_service() -> SpellService:
    return SpellService()

@router.post("/", response_model=SpellSchema)
async def create_spell(
    spell: SpellSchema, 
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Create a new spell definition."""
    try:
        db_spell = spell_service.create_spell(spell, db)
        return SpellSchema.from_orm(db_spell)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[SpellSchema])
async def list_spells(
    skip: int = 0,
    limit: int = 100,
    spell_level: Optional[int] = None,
    school: Optional[str] = None,
    character_class: Optional[str] = None,
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """List spells with optional filtering."""
    try:
        spells = spell_service.list_spells(
            skip=skip, 
            limit=limit, 
            spell_level=spell_level,
            school=school,
            character_class=character_class,
            db=db
        )
        return [SpellSchema.from_orm(spell) for spell in spells]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{spell_id}", response_model=SpellSchema)
async def get_spell(
    spell_id: str, 
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Get a specific spell by ID."""
    spell = spell_service.get_spell(spell_id, db)
    if not spell:
        raise HTTPException(status_code=404, detail="Spell not found")
    return SpellSchema.from_orm(spell)

@router.post("/instances/", response_model=Dict[str, Any])
async def create_spell_instance(
    spell_instance: Dict[str, Any],
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Create a spell instance for a character."""
    try:
        db_instance = spell_service.create_spell_instance(spell_instance, db)
        return SpellInstanceSchema.from_orm(db_instance)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/instances/{instance_id}/cast")
async def cast_spell(
    instance_id: str,
    spell_level: Optional[int] = None,
    consume_slot: bool = True,
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Cast a spell instance."""
    try:
        result = spell_service.cast_spell(instance_id, spell_level, consume_slot, db)
        return {
            "message": f"Spell cast successfully",
            "spell_name": result["spell_name"],
            "level_cast": result["level_cast"],
            "resource_consumed": result["resource_consumed"],
            "cooldown_applied": result.get("cooldown_applied", False)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/characters/{character_id}/spells")
async def get_character_spells(
    character_id: str,
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Get all spells known by a character."""
    try:
        spells = spell_service.get_character_spells(character_id, db)
        return {
            "character_id": character_id,
            "spell_instances": [SpellInstanceSchema.from_orm(instance) for instance in spells],
            "total_spells": len(spells)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/characters/{character_id}/resources/", response_model=Dict[str, Any])
async def create_resource_pool(
    character_id: str,
    resource_pool: Dict[str, Any],
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Create a resource pool for a character."""
    try:
        resource_pool.character_id = character_id
        db_pool = spell_service.create_resource_pool(resource_pool, db)
        return Dict[str, Any].from_orm(db_pool)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/characters/{character_id}/resources/")
async def get_character_resources(
    character_id: str,
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Get all resource pools for a character."""
    try:
        pools = spell_service.get_character_resource_pools(character_id, db)
        return {
            "character_id": character_id,
            "resource_pools": [Dict[str, Any].from_orm(pool) for pool in pools]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/resources/{pool_id}/consume")
async def consume_resource(
    pool_id: str,
    amount: int,
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Consume resources from a pool."""
    try:
        result = spell_service.consume_resource(pool_id, amount, db)
        return {
            "message": f"Consumed {amount} resources",
            "remaining": result["remaining"],
            "pool_name": result["pool_name"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/resources/{pool_id}/restore")
async def restore_resource(
    pool_id: str,
    amount: Optional[int] = None,
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Restore resources to a pool (partial or full)."""
    try:
        result = spell_service.restore_resource(pool_id, amount, db)
        return {
            "message": f"Restored {result['restored']} resources",
            "current": result["current"],
            "maximum": result["maximum"],
            "pool_name": result["pool_name"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/characters/{character_id}/spell-slots/configure")
async def configure_spell_slots(
    character_id: str,
    configuration: Dict[str, Any],
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Configure spell slots for a character."""
    try:
        spell_service.configure_spell_slots(character_id, configuration, db)
        return {"message": "Spell slots configured successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/characters/{character_id}/rest/short")
async def short_rest(
    character_id: str,
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Perform a short rest for a character."""
    try:
        result = spell_service.short_rest(character_id, db)
        return {
            "message": "Short rest completed",
            "resources_restored": result["resources_restored"],
            "spells_recharged": result["spells_recharged"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/characters/{character_id}/rest/long")
async def long_rest(
    character_id: str,
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Perform a long rest for a character."""
    try:
        result = spell_service.long_rest(character_id, db)
        return {
            "message": "Long rest completed",
            "resources_restored": result["resources_restored"],
            "spell_slots_restored": result["spell_slots_restored"],
            "spells_recharged": result["spells_recharged"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/search")
async def search_spells(
    query: str,
    spell_level: Optional[int] = None,
    school: Optional[str] = None,
    character_class: Optional[str] = None,
    limit: int = 20,
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Search spells by name, description, or keywords."""
    try:
        results = spell_service.search_spells(
            query=query,
            spell_level=spell_level,
            school=school,
            character_class=character_class,
            limit=limit,
            db=db
        )
        return {
            "query": query,
            "results": [SpellSchema.from_orm(spell) for spell in results],
            "total_found": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/schools")
async def get_spell_schools():
    """Get list of all spell schools."""
    return {
        "schools": [
            "abjuration", "conjuration", "divination", "enchantment",
            "evocation", "illusion", "necromancy", "transmutation"
        ]
    }

@router.get("/levels/{spell_level}/spells")
async def get_spells_by_level(
    spell_level: int,
    character_class: Optional[str] = None,
    spell_service: SpellService = Depends(get_spell_service),
    db: Session = Depends(get_db)
):
    """Get all spells of a specific level."""
    try:
        spells = spell_service.list_spells(
            spell_level=spell_level,
            character_class=character_class,
            db=db
        )
        return {
            "spell_level": spell_level,
            "character_class": character_class,
            "spells": [SpellSchema.from_orm(spell) for spell in spells],
            "total_count": len(spells)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))