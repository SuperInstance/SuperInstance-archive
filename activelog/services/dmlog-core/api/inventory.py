"""
Inventory management API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.inventory import ItemSchema
# from services.inventory_service import InventoryService  # Service not implemented yet
from database import get_db

router = APIRouter()

# Dependency to get inventory service - temporarily disabled
# def get_inventory_service() -> InventoryService:
#     return InventoryService()

@router.post("/items/", response_model=ItemSchema)
async def create_item(
    item: ItemSchema,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Create a new item definition."""
    try:
        db_item = inventory_service.create_item(item, db)
        return ItemSchema.from_orm(db_item)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/items/{item_id}", response_model=ItemSchema)
async def get_item(
    item_id: str,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Get an item by ID."""
    item = inventory_service.get_item(item_id, db)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemSchema.from_orm(item)

@router.get("/characters/{character_id}/inventory", response_model=InventorySchema)
async def get_character_inventory(
    character_id: str,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Get a character's inventory."""
    try:
        inventory = inventory_service.get_character_inventory(character_id, db)
        if not inventory:
            # Create inventory if it doesn't exist
            from models.inventory import InventorySchema
            new_inventory = InventorySchema(
                character_id=character_id,
                name=f"Character {character_id} Inventory"
            )
            inventory = inventory_service.create_inventory(new_inventory, db)
        
        return InventorySchema.from_orm(inventory)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/characters/{character_id}/inventory/", response_model=InventorySchema)
async def create_character_inventory(
    character_id: str,
    inventory: InventorySchema,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Create an inventory for a character."""
    try:
        inventory.character_id = character_id
        db_inventory = inventory_service.create_inventory(inventory, db)
        return InventorySchema.from_orm(db_inventory)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/inventories/{inventory_id}/items/add")
async def add_item_to_inventory(
    inventory_id: str,
    item_id: str,
    quantity: int = 1,
    container_id: Optional[str] = None,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Add an item to an inventory."""
    try:
        result = inventory_service.add_item_to_inventory(
            inventory_id, item_id, quantity, container_id, db
        )
        return {
            "message": f"Added {quantity} {result['item_name']} to inventory",
            "total_quantity": result["total_quantity"],
            "weight_added": result["weight_added"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/inventories/{inventory_id}/items/remove")
async def remove_item_from_inventory(
    inventory_id: str,
    item_id: str,
    quantity: int = 1,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Remove an item from an inventory."""
    try:
        result = inventory_service.remove_item_from_inventory(inventory_id, item_id, quantity, db)
        return {
            "message": f"Removed {quantity} {result['item_name']} from inventory",
            "remaining_quantity": result["remaining_quantity"],
            "weight_removed": result["weight_removed"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/transfer")
async def transfer_item(
    transfer: ItemTransferRequest,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Transfer an item between inventories."""
    try:
        result = inventory_service.transfer_item(
            transfer.source_inventory_id,
            transfer.target_inventory_id,
            transfer.item_id,
            transfer.quantity,
            db
        )
        return {
            "message": f"Transferred {transfer.quantity} {result['item_name']}",
            "from_inventory": result["source_name"],
            "to_inventory": result["target_name"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/inventories/{inventory_id}/containers/", response_model=ContainerSchema)
async def add_container(
    inventory_id: str,
    container: ContainerSchema,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Add a container to an inventory."""
    try:
        container.inventory_id = inventory_id
        db_container = inventory_service.add_container(container, db)
        return ContainerSchema.from_orm(db_container)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/inventories/{inventory_id}/encumbrance", response_model=EncumbranceCalculation)
async def calculate_encumbrance(
    inventory_id: str,
    strength_score: int = 10,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Calculate encumbrance for an inventory."""
    try:
        encumbrance = inventory_service.calculate_encumbrance(inventory_id, strength_score, db)
        return encumbrance
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/inventories/{inventory_id}/value")
async def calculate_inventory_value(
    inventory_id: str,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Calculate total value of an inventory."""
    try:
        value = inventory_service.calculate_inventory_value(inventory_id, db)
        return {
            "total_value_copper": value,
            "total_value_gold": value / 100,
            "breakdown": inventory_service.get_value_breakdown(inventory_id, db)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/inventories/{inventory_id}/currency")
async def update_currency(
    inventory_id: str,
    copper: Optional[int] = None,
    silver: Optional[int] = None,
    electrum: Optional[int] = None,
    gold: Optional[int] = None,
    platinum: Optional[int] = None,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Update currency in an inventory."""
    try:
        currency_changes = {}
        if copper is not None:
            currency_changes["copper"] = copper
        if silver is not None:
            currency_changes["silver"] = silver
        if electrum is not None:
            currency_changes["electrum"] = electrum
        if gold is not None:
            currency_changes["gold"] = gold
        if platinum is not None:
            currency_changes["platinum"] = platinum
        
        result = inventory_service.update_currency(inventory_id, currency_changes, db)
        return {
            "message": "Currency updated",
            "new_totals": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/inventories/{inventory_id}/items/{item_id}/attune")
async def attune_item(
    inventory_id: str,
    item_id: str,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Attune to a magic item."""
    try:
        result = inventory_service.attune_item(inventory_id, item_id, db)
        return {
            "message": f"Attuned to {result['item_name']}",
            "attunement_slots_used": result["attunement_slots_used"],
            "attunement_slots_max": result["attunement_slots_max"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/inventories/{inventory_id}/items/{item_id}/attune")
async def unattune_item(
    inventory_id: str,
    item_id: str,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Stop attuning to a magic item."""
    try:
        result = inventory_service.unattune_item(inventory_id, item_id, db)
        return {
            "message": f"Stopped attuning to {result['item_name']}",
            "attunement_slots_used": result["attunement_slots_used"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/items/search")
async def search_items(
    query: str,
    item_type: Optional[str] = None,
    rarity: Optional[str] = None,
    limit: int = 20,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Search for items by name or description."""
    try:
        results = inventory_service.search_items(query, item_type, rarity, limit, db)
        return {
            "query": query,
            "results": [ItemSchema.from_orm(item) for item in results],
            "total_found": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/inventories/{inventory_id}/summary")
async def get_inventory_summary(
    inventory_id: str,
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Get a summary of an inventory."""
    try:
        summary = inventory_service.get_inventory_summary(inventory_id, db)
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/inventories/{inventory_id}/sort")
async def sort_inventory(
    inventory_id: str,
    sort_by: str = "type",  # type, value, weight, alphabetical
    inventory_service: InventoryService = Depends(get_inventory_service),
    db: Session = Depends(get_db)
):
    """Sort items in an inventory."""
    try:
        inventory_service.sort_inventory(inventory_id, sort_by, db)
        return {"message": f"Inventory sorted by {sort_by}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))