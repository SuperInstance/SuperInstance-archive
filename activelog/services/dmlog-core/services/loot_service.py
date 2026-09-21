"""
Loot generation and treasure table service.
"""

import random
import math
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session
from uuid import uuid4

from models.loot import (
    LootTable, LootTableEntry, GeneratedLoot,
    LootTableSchema, LootTableEntrySchema, LootGeneration, LootItem,
    LootGenerationRequest, CurrencyAmount, TreasureBudget, MagicItemProperties,
    LootType, TreasureType, CurrencyType
)
from models.base import Rarity, DamageType

class TreasureCalculator:
    """Calculates treasure budgets based on CR and party composition."""
    
    # Base treasure values by CR (from D&D 5e DMG)
    INDIVIDUAL_TREASURE_CR = {
        0: {"cp": (5, 6), "sp": (0, 0), "ep": (0, 0), "gp": (0, 0), "pp": (0, 0)},
        0.125: {"cp": (5, 6), "sp": (0, 0), "ep": (0, 0), "gp": (0, 0), "pp": (0, 0)},
        0.25: {"cp": (5, 6), "sp": (0, 0), "ep": (0, 0), "gp": (0, 0), "pp": (0, 0)},
        0.5: {"cp": (5, 6), "sp": (0, 0), "ep": (0, 0), "gp": (0, 0), "pp": (0, 0)},
        1: {"cp": (2, 6), "sp": (1, 6), "ep": (0, 0), "gp": (0, 0), "pp": (0, 0)},
        2: {"cp": (3, 6), "sp": (2, 6), "ep": (0, 0), "gp": (1, 6), "pp": (0, 0)},
        3: {"cp": (4, 6), "sp": (4, 6), "ep": (1, 6), "gp": (2, 6), "pp": (0, 0)},
        4: {"cp": (4, 6), "sp": (4, 6), "ep": (1, 6), "gp": (2, 6), "pp": (0, 0)},
        5: {"cp": (0, 0), "sp": (2, 6), "ep": (2, 6), "gp": (6, 6), "pp": (1, 6)},
    }
    
    # Hoard treasure by CR ranges
    HOARD_TREASURE = {
        (0, 4): {
            "currency": {"cp": (600, 6), "sp": (200, 6), "gp": (20, 6)},
            "magic_chance": 0.06,  # 6% chance for magic items
            "base_value": 300
        },
        (5, 10): {
            "currency": {"cp": (200, 6), "sp": (200, 6), "gp": (100, 6), "pp": (10, 6)},
            "magic_chance": 0.16,
            "base_value": 1600
        },
        (11, 16): {
            "currency": {"gp": (400, 6), "pp": (50, 6)},
            "magic_chance": 0.36,
            "base_value": 7500
        },
        (17, 30): {
            "currency": {"gp": (1200, 6), "pp": (100, 6)},
            "magic_chance": 0.52,
            "base_value": 17500
        }
    }
    
    @classmethod
    def calculate_individual_treasure_budget(cls, cr: float) -> TreasureBudget:
        """Calculate treasure budget for individual monster."""
        # Get the closest CR entry
        closest_cr = min(cls.INDIVIDUAL_TREASURE_CR.keys(), 
                        key=lambda x: abs(x - cr))
        
        currency_data = cls.INDIVIDUAL_TREASURE_CR[closest_cr]
        
        # Calculate expected currency value
        total_cp = 0
        for currency, (dice_count, dice_sides) in currency_data.items():
            if dice_count > 0:
                expected_roll = dice_count * (dice_sides + 1) / 2
                if currency == "cp":
                    total_cp += expected_roll
                elif currency == "sp":
                    total_cp += expected_roll * 10
                elif currency == "ep":
                    total_cp += expected_roll * 50
                elif currency == "gp":
                    total_cp += expected_roll * 100
                elif currency == "pp":
                    total_cp += expected_roll * 1000
        
        total_gp = int(total_cp / 100)
        
        return TreasureBudget(
            total_budget_gp=total_gp,
            currency_budget_gp=int(total_gp * 0.8),  # 80% currency for individuals
            item_budget_gp=int(total_gp * 0.2),      # 20% items
            currency_percentage=0.8
        )
    
    @classmethod
    def calculate_hoard_treasure_budget(cls, cr: float) -> TreasureBudget:
        """Calculate treasure budget for hoard treasure."""
        # Find appropriate CR range
        for (cr_min, cr_max), data in cls.HOARD_TREASURE.items():
            if cr_min <= cr <= cr_max:
                base_value = data["base_value"]
                currency_pct = 0.3  # 30% currency, 70% items for hoards
                
                return TreasureBudget(
                    total_budget_gp=base_value,
                    currency_budget_gp=int(base_value * currency_pct),
                    item_budget_gp=int(base_value * (1 - currency_pct)),
                    currency_percentage=currency_pct
                )
        
        # Default for very high CR
        return TreasureBudget(
            total_budget_gp=25000,
            currency_budget_gp=7500,
            item_budget_gp=17500,
            currency_percentage=0.3
        )

class LootGenerator:
    """Generates random loot based on tables and parameters."""
    
    def __init__(self):
        self.treasure_calc = TreasureCalculator()
    
    def generate_currency(self, budget_gp: int, treasure_type: TreasureType = TreasureType.INDIVIDUAL) -> CurrencyAmount:
        """Generate currency within the specified budget."""
        if budget_gp <= 0:
            return CurrencyAmount()
        
        budget_cp = budget_gp * 100
        currency = CurrencyAmount()
        
        # Different distributions based on treasure type
        if treasure_type == TreasureType.INDIVIDUAL:
            # Smaller denominations for individuals
            if budget_cp >= 1000:  # 10+ gp
                currency.platinum = random.randint(0, budget_cp // 2000)
                budget_cp -= currency.platinum * 1000
            
            if budget_cp >= 100:  # 1+ gp
                currency.gold = random.randint(0, budget_cp // 200)
                budget_cp -= currency.gold * 100
            
            if budget_cp >= 50:  # 5+ sp
                currency.electrum = random.randint(0, budget_cp // 100)
                budget_cp -= currency.electrum * 50
            
            if budget_cp >= 10:  # 1+ sp
                currency.silver = random.randint(0, budget_cp // 20)
                budget_cp -= currency.silver * 10
            
            currency.copper = random.randint(0, budget_cp)
            
        elif treasure_type == TreasureType.HOARD:
            # Larger denominations for hoards
            currency.platinum = random.randint(budget_cp // 2000, budget_cp // 1000)
            budget_cp -= currency.platinum * 1000
            
            currency.gold = random.randint(budget_cp // 200, budget_cp // 100)
            budget_cp -= currency.gold * 100
            
            # Remainder in smaller denominations
            remaining_value = budget_cp
            if remaining_value > 0:
                currency.electrum = random.randint(0, remaining_value // 50)
                remaining_value -= currency.electrum * 50
                
                currency.silver = random.randint(0, remaining_value // 10)
                remaining_value -= currency.silver * 10
                
                currency.copper = remaining_value
        
        return currency
    
    def generate_items(self, budget_gp: int, cr: float, rarity_bias: Optional[Rarity] = None) -> List[LootItem]:
        """Generate items within the specified budget."""
        items = []
        remaining_budget = budget_gp
        
        if remaining_budget <= 0:
            return items
        
        # Determine number of items to generate
        max_items = min(10, max(1, budget_gp // 10))  # 1 item per 10gp, max 10 items
        item_count = random.randint(1, max_items)
        
        for _ in range(item_count):
            if remaining_budget <= 0:
                break
            
            # Determine item rarity based on CR and bias
            rarity = self._determine_item_rarity(cr, rarity_bias)
            
            # Generate item within rarity constraints
            item = self._generate_random_item(rarity, min(remaining_budget, self._get_rarity_budget(rarity)))
            
            if item and item.value_gp and item.value_gp <= remaining_budget:
                items.append(item)
                remaining_budget -= item.value_gp
        
        return items
    
    def _determine_item_rarity(self, cr: float, bias: Optional[Rarity] = None) -> Rarity:
        """Determine item rarity based on CR and bias."""
        if bias:
            # 60% chance for biased rarity, 40% for others
            if random.random() < 0.6:
                return bias
        
        # CR-based rarity distribution
        if cr <= 4:
            weights = {Rarity.COMMON: 70, Rarity.UNCOMMON: 25, Rarity.RARE: 5}
        elif cr <= 10:
            weights = {Rarity.COMMON: 40, Rarity.UNCOMMON: 40, Rarity.RARE: 15, Rarity.VERY_RARE: 5}
        elif cr <= 16:
            weights = {Rarity.COMMON: 20, Rarity.UNCOMMON: 35, Rarity.RARE: 30, Rarity.VERY_RARE: 15}
        else:
            weights = {Rarity.UNCOMMON: 25, Rarity.RARE: 35, Rarity.VERY_RARE: 30, Rarity.LEGENDARY: 10}
        
        # Weighted random selection
        total_weight = sum(weights.values())
        rand_num = random.randint(1, total_weight)
        
        current_weight = 0
        for rarity, weight in weights.items():
            current_weight += weight
            if rand_num <= current_weight:
                return rarity
        
        return Rarity.COMMON
    
    def _get_rarity_budget(self, rarity: Rarity) -> int:
        """Get typical value range for item rarity."""
        ranges = {
            Rarity.COMMON: (5, 50),
            Rarity.UNCOMMON: (50, 500),
            Rarity.RARE: (500, 5000),
            Rarity.VERY_RARE: (5000, 50000),
            Rarity.LEGENDARY: (50000, 200000)
        }
        
        min_val, max_val = ranges.get(rarity, (5, 50))
        return random.randint(min_val, max_val)
    
    def _generate_random_item(self, rarity: Rarity, max_value: int) -> Optional[LootItem]:
        """Generate a random item of specified rarity."""
        # Item type distribution
        type_weights = {
            LootType.WEAPON: 20,
            LootType.ARMOR: 15,
            LootType.POTION: 15,
            LootType.SCROLL: 10,
            LootType.RING: 8,
            LootType.AMULET: 6,
            LootType.CLOAK: 5,
            LootType.BOOTS: 4,
            LootType.GLOVES: 4,
            LootType.GEMSTONE: 8,
            LootType.ART_OBJECT: 5
        }
        
        item_type = self._weighted_choice(type_weights)
        
        # Generate item name and properties based on type and rarity
        name = self._generate_item_name(item_type, rarity)
        properties = self._generate_item_properties(item_type, rarity)
        
        # Calculate value within constraints
        base_value = self._get_rarity_budget(rarity)
        actual_value = min(base_value, max_value)
        
        return LootItem(
            name=name,
            item_type=item_type,
            rarity=rarity,
            quantity=1,
            properties=properties,
            value_gp=actual_value,
            is_magical=rarity != Rarity.COMMON,
            requires_attunement=rarity in [Rarity.RARE, Rarity.VERY_RARE, Rarity.LEGENDARY] and random.random() < 0.3
        )
    
    def _weighted_choice(self, weights: Dict[Any, int]) -> Any:
        """Make a weighted random choice."""
        total_weight = sum(weights.values())
        rand_num = random.randint(1, total_weight)
        
        current_weight = 0
        for item, weight in weights.items():
            current_weight += weight
            if rand_num <= current_weight:
                return item
        
        return list(weights.keys())[0]
    
    def _generate_item_name(self, item_type: LootType, rarity: Rarity) -> str:
        """Generate item name based on type and rarity."""
        # Base names by type
        base_names = {
            LootType.WEAPON: ["Sword", "Axe", "Bow", "Dagger", "Mace", "Spear"],
            LootType.ARMOR: ["Leather Armor", "Chain Mail", "Plate Armor", "Scale Mail"],
            LootType.POTION: ["Healing Potion", "Magic Potion", "Elixir"],
            LootType.SCROLL: ["Spell Scroll", "Ancient Scroll", "Magical Scroll"],
            LootType.RING: ["Ring", "Signet Ring", "Band"],
            LootType.AMULET: ["Amulet", "Pendant", "Talisman"],
            LootType.GEMSTONE: ["Ruby", "Sapphire", "Diamond", "Emerald", "Amethyst"],
            LootType.ART_OBJECT: ["Painting", "Sculpture", "Tapestry", "Vase"]
        }
        
        # Rarity prefixes
        prefixes = {
            Rarity.COMMON: ["", "Simple", "Basic"],
            Rarity.UNCOMMON: ["Fine", "Quality", "Enhanced", "Masterwork"],
            Rarity.RARE: ["Magical", "Enchanted", "Superior", "Ancient"],
            Rarity.VERY_RARE: ["Powerful", "Legendary", "Arcane", "Divine"],
            Rarity.LEGENDARY: ["Artifact", "Legendary", "Mythical", "Ultimate"]
        }
        
        base_name = random.choice(base_names.get(item_type, ["Item"]))
        prefix = random.choice(prefixes.get(rarity, [""]))
        
        if prefix:
            return f"{prefix} {base_name}"
        return base_name
    
    def _generate_item_properties(self, item_type: LootType, rarity: Rarity) -> Dict[str, Any]:
        """Generate item properties based on type and rarity."""
        properties = {}
        
        if item_type == LootType.WEAPON and rarity != Rarity.COMMON:
            properties["enhancement_bonus"] = min(3, max(1, rarity.value))
            if random.random() < 0.3:
                properties["special_damage"] = random.choice(["fire", "cold", "lightning", "acid"])
        
        elif item_type == LootType.ARMOR and rarity != Rarity.COMMON:
            properties["ac_bonus"] = min(3, max(1, rarity.value))
            if random.random() < 0.2:
                properties["resistance"] = random.choice(["fire", "cold", "lightning"])
        
        elif item_type == LootType.POTION:
            if "Healing" in properties.get("name", ""):
                healing_amounts = {
                    Rarity.COMMON: "2d4+2",
                    Rarity.UNCOMMON: "4d4+4", 
                    Rarity.RARE: "8d4+8",
                    Rarity.VERY_RARE: "10d4+20"
                }
                properties["healing"] = healing_amounts.get(rarity, "2d4+2")
        
        elif item_type == LootType.SCROLL:
            spell_levels = {
                Rarity.COMMON: 1,
                Rarity.UNCOMMON: 3,
                Rarity.RARE: 6,
                Rarity.VERY_RARE: 8,
                Rarity.LEGENDARY: 9
            }
            properties["spell_level"] = spell_levels.get(rarity, 1)
        
        return properties

class LootService:
    """Main loot service handling database operations and generation."""
    
    def __init__(self):
        self.generator = LootGenerator()
        self.treasure_calc = TreasureCalculator()
    
    def generate_loot(self, request: LootGenerationRequest) -> LootGeneration:
        """Generate loot based on request parameters."""
        # Calculate treasure budget
        if request.treasure_type == TreasureType.INDIVIDUAL and request.challenge_rating:
            budget = self.treasure_calc.calculate_individual_treasure_budget(request.challenge_rating)
        elif request.treasure_type == TreasureType.HOARD and request.challenge_rating:
            budget = self.treasure_calc.calculate_hoard_treasure_budget(request.challenge_rating)
        else:
            # Default budget calculation
            base_value = (request.party_level or 5) * (request.party_size or 4) * 25
            budget = TreasureBudget(
                total_budget_gp=int(base_value * request.wealth_modifier),
                currency_budget_gp=int(base_value * 0.4 * request.wealth_modifier),
                item_budget_gp=int(base_value * 0.6 * request.wealth_modifier),
                currency_percentage=0.4
            )
        
        # Apply wealth modifier
        budget.total_budget_gp = int(budget.total_budget_gp * request.wealth_modifier)
        budget.currency_budget_gp = int(budget.currency_budget_gp * request.wealth_modifier)
        budget.item_budget_gp = int(budget.item_budget_gp * request.wealth_modifier)
        
        # Generate currency
        currency = CurrencyAmount()
        if request.include_currency:
            currency = self.generator.generate_currency(budget.currency_budget_gp, request.treasure_type)
        
        # Generate items
        items = []
        if request.include_items:
            cr = request.challenge_rating or request.party_level or 5
            items = self.generator.generate_items(budget.item_budget_gp, cr, request.item_rarity_bias)
        
        # Calculate total value
        total_value = currency.total_gold_value() + sum(item.value_gp or 0 for item in items)
        
        return LootGeneration(
            currency=currency,
            items=items,
            total_value_gp=int(total_value),
            source_type=request.treasure_type,
            source_cr=request.challenge_rating,
            generation_details={
                "budget": {
                    "total": budget.total_budget_gp,
                    "currency": budget.currency_budget_gp,
                    "items": budget.item_budget_gp
                },
                "modifiers": {
                    "wealth_modifier": request.wealth_modifier,
                    "party_level": request.party_level,
                    "party_size": request.party_size
                }
            }
        )
    
    def create_loot_table(self, table_data: LootTableSchema, db: Session) -> LootTable:
        """Create a new loot table."""
        table = LootTable(
            id=str(uuid4()),
            name=table_data.name,
            description=table_data.description,
            treasure_type=table_data.treasure_type.value,
            cr_min=table_data.cr_min,
            cr_max=table_data.cr_max,
            currency_rolls=table_data.currency_rolls,
            item_rolls=table_data.item_rolls,
            tags=table_data.tags,
            is_active=table_data.is_active
        )
        
        db.add(table)
        db.commit()
        db.refresh(table)
        
        return table
    
    def add_table_entry(self, entry_data: LootTableEntrySchema, db: Session) -> LootTableEntry:
        """Add entry to a loot table."""
        entry = LootTableEntry(
            id=str(uuid4()),
            table_id=entry_data.table_id,
            item_name=entry_data.item_name,
            item_type=entry_data.item_type.value,
            rarity=entry_data.rarity.value,
            weight=entry_data.weight,
            min_quantity=entry_data.min_quantity,
            max_quantity=entry_data.max_quantity,
            properties=entry_data.properties,
            value_range=entry_data.value_range,
            condition_cr_min=entry_data.condition_cr_min,
            condition_cr_max=entry_data.condition_cr_max,
            condition_tags=entry_data.condition_tags
        )
        
        db.add(entry)
        db.commit()
        db.refresh(entry)
        
        return entry
    
    def generate_from_table(self, table_id: str, cr: float, db: Session) -> List[LootItem]:
        """Generate loot from a specific table."""
        table = db.query(LootTable).filter(LootTable.id == table_id).first()
        if not table or not table.is_active:
            return []
        
        # Get applicable entries
        applicable_entries = []
        for entry in table.entries:
            if self._entry_applies(entry, cr):
                applicable_entries.extend([entry] * entry.weight)
        
        if not applicable_entries:
            return []
        
        # Generate items
        items = []
        num_rolls = random.randint(1, 3)  # 1-3 items per table
        
        for _ in range(num_rolls):
            entry = random.choice(applicable_entries)
            quantity = random.randint(entry.min_quantity, entry.max_quantity)
            
            # Calculate value
            value = 0
            if entry.value_range:
                value = random.randint(entry.value_range[0], entry.value_range[1])
            
            item = LootItem(
                name=entry.item_name,
                item_type=LootType(entry.item_type),
                rarity=Rarity(entry.rarity),
                quantity=quantity,
                properties=entry.properties or {},
                value_gp=value,
                is_magical=entry.rarity != "common"
            )
            
            items.append(item)
        
        return items
    
    def _entry_applies(self, entry: LootTableEntry, cr: float) -> bool:
        """Check if a loot table entry applies to the given CR."""
        if entry.condition_cr_min is not None and cr < entry.condition_cr_min:
            return False
        if entry.condition_cr_max is not None and cr > entry.condition_cr_max:
            return False
        return True
    
    def save_generated_loot(self, loot: LootGeneration, source_info: Dict[str, Any], db: Session) -> GeneratedLoot:
        """Save generated loot to database."""
        generated_loot = GeneratedLoot(
            id=str(uuid4()),
            generation_id=source_info.get("generation_id", str(uuid4())),
            encounter_id=source_info.get("encounter_id"),
            campaign_id=source_info.get("campaign_id"),
            source_type=loot.source_type.value,
            source_cr=loot.source_cr,
            currency=loot.currency.dict(),
            items=[item.dict() for item in loot.items],
            total_value_gp=loot.total_value_gp,
            notes=source_info.get("notes")
        )
        
        db.add(generated_loot)
        db.commit()
        db.refresh(generated_loot)
        
        return generated_loot
    
    def get_loot_tables(self, treasure_type: TreasureType = None, tags: List[str] = None, db: Session = None) -> List[LootTable]:
        """Get loot tables with optional filtering."""
        query = db.query(LootTable).filter(LootTable.is_active == True)
        
        if treasure_type:
            query = query.filter(LootTable.treasure_type == treasure_type.value)
        
        if tags:
            # Simple tag filtering - in reality would use more sophisticated JSON queries
            for tag in tags:
                query = query.filter(LootTable.tags.contains(tag))
        
        return query.all()