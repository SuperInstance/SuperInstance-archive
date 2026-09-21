"""
Loot generation and treasure management API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.loot import (
    LootTableSchema, LootTableEntrySchema, LootGenerationRequest, 
    LootGeneration, TreasureType
)
from services.loot_service import LootService
from database import get_db

router = APIRouter()

# Dependency to get loot service
def get_loot_service() -> LootService:
    return LootService()

@router.post("/generate")
async def generate_loot(
    request: LootGenerationRequest,
    loot_service: LootService = Depends(get_loot_service)
):
    """Generate loot based on specified parameters."""
    try:
        loot = loot_service.generate_loot(request)
        return {
            "message": "Loot generated successfully",
            "loot": loot
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/generate/quick")
async def quick_generate_loot(
    party_level: int,
    party_size: int = 4,
    treasure_type: str = "individual",
    challenge_rating: Optional[float] = None,
    wealth_modifier: float = 1.0,
    loot_service: LootService = Depends(get_loot_service)
):
    """Quickly generate loot with minimal parameters."""
    try:
        request = LootGenerationRequest(
            party_levels=[party_level] * party_size,
            desired_difficulty=None,
            treasure_type=TreasureType(treasure_type),
            challenge_rating=challenge_rating,
            wealth_modifier=wealth_modifier
        )
        
        loot = loot_service.generate_loot(request)
        return {
            "message": "Quick loot generated",
            "parameters": {
                "party_level": party_level,
                "party_size": party_size,
                "treasure_type": treasure_type,
                "challenge_rating": challenge_rating,
                "wealth_modifier": wealth_modifier
            },
            "loot": loot
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tables/", response_model=LootTableSchema)
async def create_loot_table(
    table: LootTableSchema,
    loot_service: LootService = Depends(get_loot_service),
    db: Session = Depends(get_db)
):
    """Create a new loot table."""
    try:
        db_table = loot_service.create_loot_table(table, db)
        return LootTableSchema.from_orm(db_table)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tables/{table_id}/entries/", response_model=LootTableEntrySchema)
async def add_table_entry(
    table_id: str,
    entry: LootTableEntrySchema,
    loot_service: LootService = Depends(get_loot_service),
    db: Session = Depends(get_db)
):
    """Add an entry to a loot table."""
    try:
        entry.table_id = table_id
        db_entry = loot_service.add_table_entry(entry, db)
        return LootTableEntrySchema.from_orm(db_entry)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tables/")
async def list_loot_tables(
    treasure_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    loot_service: LootService = Depends(get_loot_service),
    db: Session = Depends(get_db)
):
    """List available loot tables."""
    try:
        treasure_type_enum = TreasureType(treasure_type) if treasure_type else None
        tables = loot_service.get_loot_tables(treasure_type_enum, tags, db)
        
        return {
            "tables": [LootTableSchema.from_orm(table) for table in tables],
            "total_count": len(tables),
            "filters": {
                "treasure_type": treasure_type,
                "tags": tags
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tables/{table_id}/generate")
async def generate_from_table(
    table_id: str,
    challenge_rating: float = 1.0,
    loot_service: LootService = Depends(get_loot_service),
    db: Session = Depends(get_db)
):
    """Generate loot from a specific table."""
    try:
        items = loot_service.generate_from_table(table_id, challenge_rating, db)
        return {
            "table_id": table_id,
            "challenge_rating": challenge_rating,
            "generated_items": items,
            "item_count": len(items)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/treasure/individual/{challenge_rating}")
async def get_individual_treasure_budget(
    challenge_rating: float,
    loot_service: LootService = Depends(get_loot_service)
):
    """Get treasure budget for individual monster treasure."""
    try:
        budget = loot_service.treasure_calc.calculate_individual_treasure_budget(challenge_rating)
        return {
            "challenge_rating": challenge_rating,
            "budget": budget,
            "treasure_type": "individual"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/treasure/hoard/{challenge_rating}")
async def get_hoard_treasure_budget(
    challenge_rating: float,
    loot_service: LootService = Depends(get_loot_service)
):
    """Get treasure budget for hoard treasure."""
    try:
        budget = loot_service.treasure_calc.calculate_hoard_treasure_budget(challenge_rating)
        return {
            "challenge_rating": challenge_rating,
            "budget": budget,
            "treasure_type": "hoard"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/currency/generate")
async def generate_currency(
    budget_gp: int,
    treasure_type: str = "individual",
    loot_service: LootService = Depends(get_loot_service)
):
    """Generate currency within a specified budget."""
    try:
        treasure_type_enum = TreasureType(treasure_type)
        currency = loot_service.generator.generate_currency(budget_gp, treasure_type_enum)
        
        return {
            "budget_gp": budget_gp,
            "treasure_type": treasure_type,
            "currency": currency,
            "total_value_gp": currency.total_gold_value()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/items/generate")
async def generate_items(
    budget_gp: int,
    challenge_rating: float = 1.0,
    rarity_bias: Optional[str] = None,
    loot_service: LootService = Depends(get_loot_service)
):
    """Generate items within a specified budget."""
    try:
        from models.base import Rarity
        rarity_enum = Rarity(rarity_bias) if rarity_bias else None
        
        items = loot_service.generator.generate_items(budget_gp, challenge_rating, rarity_enum)
        
        total_value = sum(item.value_gp or 0 for item in items)
        
        return {
            "budget_gp": budget_gp,
            "challenge_rating": challenge_rating,
            "rarity_bias": rarity_bias,
            "items": items,
            "item_count": len(items),
            "total_value_gp": total_value
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/save")
async def save_generated_loot(
    loot: LootGeneration,
    encounter_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    notes: Optional[str] = None,
    loot_service: LootService = Depends(get_loot_service),
    db: Session = Depends(get_db)
):
    """Save generated loot to database."""
    try:
        source_info = {
            "encounter_id": encounter_id,
            "campaign_id": campaign_id,
            "notes": notes
        }
        
        saved_loot = loot_service.save_generated_loot(loot, source_info, db)
        
        return {
            "message": "Loot saved successfully",
            "loot_id": saved_loot.id,
            "total_value_gp": saved_loot.total_value_gp
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/types")
async def get_treasure_types():
    """Get available treasure types."""
    return {
        "treasure_types": [t.value for t in TreasureType],
        "descriptions": {
            "individual": "Individual monster treasure (coins and small items)",
            "hoard": "Large accumulated treasure (hoards, vaults)",
            "merchant": "Shop inventory and trade goods", 
            "quest_reward": "Specific rewards for completing quests",
            "random_encounter": "Random finds and discoveries"
        }
    }

@router.get("/rarities")
async def get_item_rarities():
    """Get available item rarities."""
    from models.base import Rarity
    return {
        "rarities": [r.value for r in Rarity],
        "descriptions": {
            "common": "Everyday items, basic equipment",
            "uncommon": "Well-made items, minor magical properties",
            "rare": "Exceptional items, moderate magical abilities",
            "very_rare": "Masterwork items, powerful magical effects",
            "legendary": "Legendary artifacts, game-changing abilities"
        }
    }

@router.get("/generate/random")
async def generate_random_loot(
    loot_service: LootService = Depends(get_loot_service)
):
    """Generate completely random loot for testing or inspiration."""
    try:
        import random
        
        # Random parameters
        party_level = random.randint(1, 10)
        party_size = random.randint(3, 6)
        treasure_types = list(TreasureType)
        treasure_type = random.choice(treasure_types)
        challenge_rating = random.uniform(0.5, party_level + 2)
        wealth_modifier = random.uniform(0.5, 2.0)
        
        request = LootGenerationRequest(
            party_levels=[party_level] * party_size,
            treasure_type=treasure_type,
            challenge_rating=challenge_rating,
            wealth_modifier=wealth_modifier
        )
        
        loot = loot_service.generate_loot(request)
        
        return {
            "message": "Random loot generated",
            "parameters": {
                "party_level": party_level,
                "party_size": party_size,
                "treasure_type": treasure_type.value,
                "challenge_rating": challenge_rating,
                "wealth_modifier": wealth_modifier
            },
            "loot": loot
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/templates/create")
async def create_loot_template(
    name: str,
    description: str,
    template_data: LootGenerationRequest,
    loot_service: LootService = Depends(get_loot_service)
):
    """Create a reusable loot generation template."""
    try:
        template = {
            "name": name,
            "description": description,
            "parameters": template_data
        }
        
        # In a full implementation, this would save to database
        return {
            "message": "Loot template created",
            "template": template
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))