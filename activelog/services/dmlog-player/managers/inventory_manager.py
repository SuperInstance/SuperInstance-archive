"""
Inventory management system with encumbrance tracking
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from ..models.base import InventoryItem, Character


class InventoryManager:
    """Manages character inventory and encumbrance"""
    
    def __init__(self):
        self.inventories: Dict[str, List[InventoryItem]] = {}  # character_id -> items
        self.item_templates: Dict[str, Dict[str, Any]] = {}
        self.encumbrance_rules = {
            "variant": False,  # Use variant encumbrance rules
            "push_drag_lift_multiplier": 2,
            "carrying_capacity_multiplier": 15  # STR * 15 = carrying capacity
        }
        
        self._initialize_item_templates()
    
    def add_item(
        self, 
        character_id: str,
        name: str,
        quantity: int = 1,
        weight: float = 0.0,
        value: Optional[Dict[str, float]] = None,
        description: str = "",
        item_type: str = "gear",
        source: str = "",
        notes: str = ""
    ) -> InventoryItem:
        """Add an item to character's inventory"""
        
        # Check if item already exists and can be stacked
        existing_item = self._find_stackable_item(character_id, name, description)
        
        if existing_item:
            existing_item.quantity += quantity
            existing_item.updated_at = datetime.utcnow()
            if source and source not in existing_item.notes:
                existing_item.notes += f"; {source}"
            return existing_item
        
        # Create new item
        item = InventoryItem(
            character_id=character_id,
            name=name,
            description=description,
            quantity=quantity,
            weight=weight,
            value=value or {},
            item_type=item_type,
            source=source,
            notes=notes
        )
        
        # Add to inventory
        if character_id not in self.inventories:
            self.inventories[character_id] = []
        
        self.inventories[character_id].append(item)
        return item
    
    def remove_item(self, character_id: str, item_id: str, quantity: int = 1) -> bool:
        """Remove quantity of an item from inventory"""
        
        if character_id not in self.inventories:
            return False
        
        for item in self.inventories[character_id]:
            if item.id == item_id:
                if quantity >= item.quantity:
                    # Remove entire item
                    self.inventories[character_id].remove(item)
                else:
                    # Reduce quantity
                    item.quantity -= quantity
                    item.updated_at = datetime.utcnow()
                return True
        
        return False
    
    def update_item(
        self, 
        character_id: str, 
        item_id: str,
        **updates
    ) -> Optional[InventoryItem]:
        """Update an inventory item"""
        
        item = self.get_item(character_id, item_id)
        if not item:
            return None
        
        for field, value in updates.items():
            if hasattr(item, field):
                setattr(item, field, value)
        
        item.updated_at = datetime.utcnow()
        return item
    
    def get_item(self, character_id: str, item_id: str) -> Optional[InventoryItem]:
        """Get a specific item by ID"""
        
        if character_id not in self.inventories:
            return None
        
        for item in self.inventories[character_id]:
            if item.id == item_id:
                return item
        
        return None
    
    def get_inventory(self, character_id: str) -> List[InventoryItem]:
        """Get character's full inventory"""
        
        return self.inventories.get(character_id, []).copy()
    
    def get_items_by_type(self, character_id: str, item_type: str) -> List[InventoryItem]:
        """Get items of a specific type"""
        
        inventory = self.get_inventory(character_id)
        return [item for item in inventory if item.item_type == item_type]
    
    def get_equipped_items(self, character_id: str) -> List[InventoryItem]:
        """Get all equipped items"""
        
        inventory = self.get_inventory(character_id)
        return [item for item in inventory if item.equipped]
    
    def get_magical_items(self, character_id: str) -> List[InventoryItem]:
        """Get all magical items"""
        
        inventory = self.get_inventory(character_id)
        return [item for item in inventory if item.magical]
    
    def search_inventory(
        self, 
        character_id: str,
        query: str = "",
        item_type: Optional[str] = None,
        magical_only: bool = False,
        equipped_only: bool = False
    ) -> List[InventoryItem]:
        """Search inventory with filters"""
        
        inventory = self.get_inventory(character_id)
        results = []
        
        query_lower = query.lower() if query else ""
        
        for item in inventory:
            # Text search
            if query and query_lower not in item.name.lower() and \
               query_lower not in item.description.lower():
                continue
            
            # Type filter
            if item_type and item.item_type != item_type:
                continue
            
            # Magical filter
            if magical_only and not item.magical:
                continue
            
            # Equipped filter
            if equipped_only and not item.equipped:
                continue
            
            results.append(item)
        
        return results
    
    def calculate_encumbrance(self, character: Character) -> Dict[str, Any]:
        """Calculate character's encumbrance status"""
        
        inventory = self.get_inventory(character.id)
        
        # Calculate total weight
        total_weight = sum(item.weight * item.quantity for item in inventory)
        
        # Get strength score
        strength = character.attributes.get("strength", 10)
        
        # Calculate carrying capacity
        carrying_capacity = strength * self.encumbrance_rules["carrying_capacity_multiplier"]
        
        # Determine encumbrance level
        encumbrance_level = "normal"
        speed_penalty = 0
        disadvantage_on_checks = False
        
        if self.encumbrance_rules["variant"]:
            # Variant encumbrance rules
            if total_weight > carrying_capacity:
                encumbrance_level = "over_capacity"
                speed_penalty = 20
                disadvantage_on_checks = True
            elif total_weight > carrying_capacity * 2/3:
                encumbrance_level = "heavily_encumbered"
                speed_penalty = 20
                disadvantage_on_checks = True
            elif total_weight > carrying_capacity * 1/3:
                encumbrance_level = "lightly_encumbered"
                speed_penalty = 10
        else:
            # Standard encumbrance rules
            if total_weight > carrying_capacity:
                encumbrance_level = "over_capacity"
                speed_penalty = 20
                disadvantage_on_checks = True
        
        # Calculate push/drag/lift capacity
        push_drag_lift = carrying_capacity * self.encumbrance_rules["push_drag_lift_multiplier"]
        
        return {
            "total_weight": total_weight,
            "carrying_capacity": carrying_capacity,
            "push_drag_lift_capacity": push_drag_lift,
            "encumbrance_level": encumbrance_level,
            "speed_penalty": speed_penalty,
            "disadvantage_on_checks": disadvantage_on_checks,
            "weight_percentage": (total_weight / carrying_capacity * 100) if carrying_capacity > 0 else 0
        }
    
    def calculate_inventory_value(self, character_id: str) -> Dict[str, float]:
        """Calculate total value of inventory"""
        
        inventory = self.get_inventory(character_id)
        total_value = {"gp": 0.0, "sp": 0.0, "cp": 0.0, "pp": 0.0}
        
        for item in inventory:
            for currency, amount in item.value.items():
                if currency in total_value:
                    total_value[currency] += amount * item.quantity
        
        return total_value
    
    def organize_inventory(
        self, 
        character_id: str, 
        organization_type: str = "type"
    ) -> Dict[str, List[InventoryItem]]:
        """Organize inventory by different criteria"""
        
        inventory = self.get_inventory(character_id)
        organized = {}
        
        if organization_type == "type":
            for item in inventory:
                item_type = item.item_type
                if item_type not in organized:
                    organized[item_type] = []
                organized[item_type].append(item)
        
        elif organization_type == "value":
            # Group by value ranges
            for item in inventory:
                total_gp_value = self._convert_to_gp(item.value) * item.quantity
                
                if total_gp_value >= 1000:
                    category = "very_valuable"
                elif total_gp_value >= 100:
                    category = "valuable"
                elif total_gp_value >= 10:
                    category = "moderate"
                else:
                    category = "low_value"
                
                if category not in organized:
                    organized[category] = []
                organized[category].append(item)
        
        elif organization_type == "weight":
            # Group by weight
            for item in inventory:
                total_weight = item.weight * item.quantity
                
                if total_weight >= 10:
                    category = "heavy"
                elif total_weight >= 1:
                    category = "medium"
                else:
                    category = "light"
                
                if category not in organized:
                    organized[category] = []
                organized[category].append(item)
        
        elif organization_type == "alphabetical":
            # Sort alphabetically
            sorted_items = sorted(inventory, key=lambda x: x.name.lower())
            current_letter = ""
            
            for item in sorted_items:
                first_letter = item.name[0].upper() if item.name else "?"
                
                if first_letter != current_letter:
                    current_letter = first_letter
                    organized[current_letter] = []
                
                organized[current_letter].append(item)
        
        return organized
    
    def create_equipment_loadout(
        self, 
        character_id: str, 
        loadout_name: str,
        item_ids: List[str]
    ) -> Dict[str, Any]:
        """Create a saved equipment loadout"""
        
        loadout_items = []
        total_weight = 0.0
        
        for item_id in item_ids:
            item = self.get_item(character_id, item_id)
            if item:
                loadout_items.append({
                    "id": item.id,
                    "name": item.name,
                    "equipped": item.equipped,
                    "attuned": item.attuned
                })
                total_weight += item.weight * item.quantity
        
        return {
            "name": loadout_name,
            "items": loadout_items,
            "total_weight": total_weight,
            "created_at": datetime.utcnow()
        }
    
    def apply_equipment_loadout(
        self, 
        character_id: str, 
        loadout: Dict[str, Any]
    ) -> bool:
        """Apply a saved equipment loadout"""
        
        # First, unequip all items
        inventory = self.get_inventory(character_id)
        for item in inventory:
            item.equipped = False
            item.attuned = False
        
        # Apply loadout
        success_count = 0
        for loadout_item in loadout.get("items", []):
            item = self.get_item(character_id, loadout_item["id"])
            if item:
                item.equipped = loadout_item.get("equipped", False)
                item.attuned = loadout_item.get("attuned", False)
                success_count += 1
        
        return success_count == len(loadout.get("items", []))
    
    def get_inventory_statistics(self, character_id: str) -> Dict[str, Any]:
        """Get inventory statistics"""
        
        inventory = self.get_inventory(character_id)
        
        if not inventory:
            return {
                "total_items": 0,
                "total_weight": 0.0,
                "total_value_gp": 0.0,
                "magical_items": 0,
                "equipped_items": 0,
                "item_types": {},
                "heaviest_item": None,
                "most_valuable_item": None
            }
        
        total_items = sum(item.quantity for item in inventory)
        total_weight = sum(item.weight * item.quantity for item in inventory)
        
        # Calculate total value in GP
        total_value_gp = 0.0
        for item in inventory:
            total_value_gp += self._convert_to_gp(item.value) * item.quantity
        
        magical_items = sum(1 for item in inventory if item.magical)
        equipped_items = sum(1 for item in inventory if item.equipped)
        
        # Count by type
        item_types = {}
        for item in inventory:
            item_type = item.item_type
            item_types[item_type] = item_types.get(item_type, 0) + item.quantity
        
        # Find heaviest and most valuable items
        heaviest_item = max(inventory, key=lambda x: x.weight * x.quantity, default=None)
        most_valuable_item = max(
            inventory, 
            key=lambda x: self._convert_to_gp(x.value) * x.quantity,
            default=None
        )
        
        return {
            "total_items": total_items,
            "unique_items": len(inventory),
            "total_weight": total_weight,
            "total_value_gp": total_value_gp,
            "magical_items": magical_items,
            "equipped_items": equipped_items,
            "item_types": item_types,
            "heaviest_item": heaviest_item.name if heaviest_item else None,
            "most_valuable_item": most_valuable_item.name if most_valuable_item else None
        }
    
    def create_shopping_list(
        self, 
        character_id: str, 
        desired_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a shopping list with cost analysis"""
        
        shopping_list = {
            "items": desired_items,
            "total_cost": {"gp": 0.0, "sp": 0.0, "cp": 0.0},
            "affordable": True,
            "created_at": datetime.utcnow()
        }
        
        # Calculate total cost
        for item_data in desired_items:
            cost = item_data.get("cost", {})
            quantity = item_data.get("quantity", 1)
            
            for currency, amount in cost.items():
                if currency in shopping_list["total_cost"]:
                    shopping_list["total_cost"][currency] += amount * quantity
        
        # Check if character can afford it (would need character's money)
        # This would be expanded to check actual character funds
        
        return shopping_list
    
    def _find_stackable_item(
        self, 
        character_id: str, 
        name: str, 
        description: str
    ) -> Optional[InventoryItem]:
        """Find an existing item that can be stacked with the new one"""
        
        if character_id not in self.inventories:
            return None
        
        for item in self.inventories[character_id]:
            if (item.name == name and 
                item.description == description and 
                not item.magical and  # Don't stack magical items
                item.item_type in ["consumable", "gear", "ammunition"]):  # Only stack these types
                return item
        
        return None
    
    def _convert_to_gp(self, value: Dict[str, float]) -> float:
        """Convert mixed currency to gold pieces"""
        
        conversion_rates = {"pp": 10, "gp": 1, "sp": 0.1, "cp": 0.01}
        total_gp = 0.0
        
        for currency, amount in value.items():
            if currency in conversion_rates:
                total_gp += amount * conversion_rates[currency]
        
        return total_gp
    
    def _initialize_item_templates(self):
        """Initialize common item templates"""
        
        self.item_templates = {
            "longsword": {
                "name": "Longsword",
                "item_type": "weapon",
                "weight": 3.0,
                "value": {"gp": 15},
                "damage": "1d8",
                "damage_type": "slashing",
                "properties": ["versatile (1d10)"]
            },
            "leather_armor": {
                "name": "Leather Armor",
                "item_type": "armor",
                "weight": 10.0,
                "value": {"gp": 10},
                "armor_class": 11,
                "properties": ["light"]
            },
            "health_potion": {
                "name": "Potion of Healing",
                "item_type": "consumable",
                "weight": 0.5,
                "value": {"gp": 50},
                "magical": True,
                "description": "Restores 2d4+2 hit points"
            },
            "rope": {
                "name": "Rope (50 feet)",
                "item_type": "gear",
                "weight": 10.0,
                "value": {"gp": 2},
                "description": "Hempen rope, 50 feet"
            },
            "torch": {
                "name": "Torch",
                "item_type": "gear",
                "weight": 1.0,
                "value": {"cp": 2},
                "description": "Burns for 1 hour, 20-foot bright light radius"
            }
        }