"""
Item and spell converter for transforming items and spells between game systems
"""

import re
import math
from typing import Dict, List, Any, Optional, Tuple
from ..models.base import Item, Spell, ConversionResult
from ..config.systems import GameSystem, SPELL_MAPPINGS, ITEM_MAPPINGS


class ItemSpellConverter:
    """Converts items and spells between different game systems"""
    
    def __init__(self):
        self.damage_type_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "slashing": "slashing", "piercing": "piercing", "bludgeoning": "bludgeoning",
                "acid": "acid", "cold": "cold", "fire": "fire", "lightning": "electricity",
                "thunder": "sonic", "poison": "poison", "psychic": "mental",
                "radiant": "positive", "necrotic": "negative", "force": "force"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "slashing": "slashing", "piercing": "piercing", "bludgeoning": "bludgeoning",
                "acid": "acid", "cold": "cold", "fire": "fire", "electricity": "lightning",
                "sonic": "thunder", "poison": "poison", "mental": "psychic",
                "positive": "radiant", "negative": "necrotic", "force": "force"
            }
        }
        
        self.rarity_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "common": "common", "uncommon": "uncommon", "rare": "rare",
                "very rare": "very rare", "legendary": "unique", "artifact": "artifact"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "common": "common", "uncommon": "uncommon", "rare": "rare",
                "very rare": "very rare", "unique": "legendary", "artifact": "artifact"
            }
        }
    
    def convert_item(self, item: Item, target_system: GameSystem) -> ConversionResult:
        """Convert an item to target system"""
        
        if item.system == target_system:
            return ConversionResult(
                success=True,
                source_system=item.system,
                target_system=target_system,
                converted_data=item.dict(),
                conversion_notes=["No conversion needed - same system"]
            )
        
        result = ConversionResult(
            success=True,
            source_system=item.system,
            target_system=target_system
        )
        
        try:
            # Convert item type and category
            converted_type, converted_category = self._convert_item_type(
                item.item_type, item.category, item.system, target_system
            )
            
            # Convert rarity
            converted_rarity = self._convert_rarity(
                item.rarity, item.system, target_system
            )
            
            # Convert cost
            converted_cost = self._convert_cost(
                item.cost, item.system, target_system
            )
            
            # Convert combat stats
            converted_damage = self._convert_item_damage(
                item.damage, item.damage_type, item.system, target_system
            )
            
            converted_ac = self._convert_armor_class(
                item.armor_class, item.system, target_system
            )
            
            converted_attack_bonus = self._convert_attack_bonus(
                item.attack_bonus, item.system, target_system
            )
            
            # Convert properties
            converted_properties = self._convert_item_properties(
                item.properties, item.system, target_system
            )
            
            # Convert magic item specifics
            converted_charges = self._convert_charges(
                item.charges, item.system, target_system
            )
            
            # Apply system-specific mappings
            mapped_item = self._apply_item_mappings(item, target_system)
            
            # Build converted item
            converted_item = Item(
                name=mapped_item.get("name", item.name),
                system=target_system,
                item_type=converted_type,
                category=converted_category,
                rarity=converted_rarity,
                cost=converted_cost,
                weight=item.weight,  # Weight usually translates directly
                properties=converted_properties,
                description=item.description,  # May need text conversion in future
                damage=converted_damage[0],
                damage_type=converted_damage[1],
                armor_class=converted_ac,
                attack_bonus=converted_attack_bonus,
                magic=item.magic,
                attunement_required=self._convert_attunement(
                    item.attunement_required, item.system, target_system
                ),
                charges=converted_charges,
                system_specific={}
            )
            
            result.converted_data = converted_item.dict()
            result.conversion_confidence = self._calculate_item_confidence(
                item, converted_item
            )
            
            if result.conversion_confidence < 0.7:
                result.manual_review_required = True
                result.warnings.append("Item conversion needs manual review")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Item conversion failed: {str(e)}")
            result.conversion_confidence = 0.0
        
        return result
    
    def convert_spell(self, spell: Spell, target_system: GameSystem) -> ConversionResult:
        """Convert a spell to target system"""
        
        if spell.system == target_system:
            return ConversionResult(
                success=True,
                source_system=spell.system,
                target_system=target_system,
                converted_data=spell.dict(),
                conversion_notes=["No conversion needed - same system"]
            )
        
        result = ConversionResult(
            success=True,
            source_system=spell.system,
            target_system=target_system
        )
        
        try:
            # Convert spell level
            converted_level = self._convert_spell_level(
                spell.level, spell.system, target_system
            )
            
            # Convert school
            converted_school = self._convert_spell_school(
                spell.school, spell.system, target_system
            )
            
            # Convert casting time
            converted_casting_time = self._convert_casting_time(
                spell.casting_time, spell.system, target_system
            )
            
            # Convert range
            converted_range = self._convert_spell_range(
                spell.range, spell.system, target_system
            )
            
            # Convert components
            converted_components = self._convert_spell_components(
                spell.components, spell.system, target_system
            )
            
            # Convert duration
            converted_duration = self._convert_spell_duration(
                spell.duration, spell.concentration, spell.system, target_system
            )
            
            # Convert damage
            converted_damage = self._convert_spell_damage(
                spell.damage, spell.system, target_system
            )
            
            # Convert save information
            converted_save = self._convert_spell_save(
                spell.save, spell.system, target_system
            )
            
            # Convert class availability
            converted_classes = self._convert_spell_classes(
                spell.classes, spell.system, target_system
            )
            
            # Apply system-specific mappings
            mapped_spell = self._apply_spell_mappings(spell, target_system)
            
            # Build converted spell
            converted_spell = Spell(
                name=mapped_spell.get("name", spell.name),
                system=target_system,
                level=converted_level,
                school=converted_school,
                casting_time=converted_casting_time,
                range=converted_range,
                components=converted_components,
                duration=converted_duration[0],
                concentration=converted_duration[1],
                ritual=self._convert_ritual(spell.ritual, spell.system, target_system),
                description=spell.description,  # May need text conversion
                damage=converted_damage,
                save=converted_save,
                classes=converted_classes,
                system_specific={}
            )
            
            result.converted_data = converted_spell.dict()
            result.conversion_confidence = self._calculate_spell_confidence(
                spell, converted_spell
            )
            
            if result.conversion_confidence < 0.6:
                result.manual_review_required = True
                result.warnings.append("Spell conversion needs manual review")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Spell conversion failed: {str(e)}")
            result.conversion_confidence = 0.0
        
        return result
    
    def _convert_item_type(
        self, 
        item_type: str, 
        category: str,
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Tuple[str, str]:
        """Convert item type and category between systems"""
        
        type_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "weapon": "weapon", "armor": "armor", "shield": "shield",
                "gear": "gear", "magic_item": "magical", "wondrous_item": "magical",
                "consumable": "consumable", "tool": "tool"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "weapon": "weapon", "armor": "armor", "shield": "shield",
                "gear": "gear", "magical": "magic_item", "consumable": "consumable",
                "tool": "tool", "alchemical": "gear"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key in type_mappings:
            converted_type = type_mappings[mapping_key].get(item_type, item_type)
        else:
            converted_type = item_type
        
        # Category usually stays the same or gets refined
        converted_category = category
        
        return converted_type, converted_category
    
    def _convert_rarity(
        self, 
        rarity: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert item rarity between systems"""
        
        mapping_key = (source_system, target_system)
        if mapping_key in self.rarity_mappings:
            return self.rarity_mappings[mapping_key].get(rarity.lower(), rarity)
        
        return rarity
    
    def _convert_cost(
        self, 
        cost: Dict[str, Any], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Convert item cost between systems"""
        
        if not cost:
            return {}
        
        converted_cost = cost.copy()
        
        # Convert currency names if needed
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # Both use similar currency (gp, sp, cp)
            pass
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            # Both use similar currency
            pass
        
        # Apply economic scaling between systems
        scaling_factor = self._get_cost_scaling_factor(source_system, target_system)
        for currency, amount in converted_cost.items():
            if isinstance(amount, (int, float)):
                converted_cost[currency] = amount * scaling_factor
        
        return converted_cost
    
    def _get_cost_scaling_factor(
        self, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> float:
        """Get cost scaling factor between systems"""
        
        # Economic differences between systems
        scaling_factors = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): 0.8,  # PF2E items slightly cheaper
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): 1.25,
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_1E): 0.9,
            (GameSystem.PATHFINDER_1E, GameSystem.D_AND_D_5E): 1.1
        }
        
        return scaling_factors.get((source_system, target_system), 1.0)
    
    def _convert_item_damage(
        self, 
        damage: Optional[str], 
        damage_type: Optional[str],
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert item damage and damage type"""
        
        converted_damage = damage
        converted_type = damage_type
        
        # Convert damage type
        if damage_type:
            mapping_key = (source_system, target_system)
            if mapping_key in self.damage_type_mappings:
                converted_type = self.damage_type_mappings[mapping_key].get(
                    damage_type.lower(), damage_type
                )
        
        # Convert damage dice if needed
        if damage:
            converted_damage = self._convert_damage_dice(
                damage, source_system, target_system
            )
        
        return converted_damage, converted_type
    
    def _convert_damage_dice(
        self, 
        damage_str: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert damage dice notation between systems"""
        
        # Parse dice notation
        dice_pattern = r"(\d+d\d+)([+-]\d+)?"
        match = re.match(dice_pattern, damage_str)
        
        if not match:
            return damage_str
        
        dice_part = match.group(1)
        modifier = match.group(2) or ""
        
        # System-specific damage scaling
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # PF2E weapons tend to have slightly higher damage
            if "d4" in dice_part:
                dice_part = dice_part.replace("d4", "d6")
            elif "d6" in dice_part and "1d6" in dice_part:
                dice_part = dice_part.replace("1d6", "1d8")
        
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            # D&D 5E weapons tend to have slightly lower damage
            if "d8" in dice_part and "1d8" in dice_part:
                dice_part = dice_part.replace("1d8", "1d6")
            elif "d6" in dice_part and "1d6" in dice_part:
                dice_part = dice_part.replace("1d6", "1d4")
        
        return dice_part + modifier
    
    def _convert_armor_class(
        self, 
        ac: Optional[int], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Optional[int]:
        """Convert armor class values between systems"""
        
        if ac is None:
            return None
        
        # AC scaling between systems
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            return ac + 1  # PF2E AC tends to be slightly higher
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            return max(10, ac - 1)  # D&D 5E AC tends to be slightly lower
        
        return ac
    
    def _convert_attack_bonus(
        self, 
        bonus: Optional[int], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Optional[int]:
        """Convert attack bonus between systems"""
        
        if bonus is None:
            return None
        
        # Attack bonus scaling
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            return bonus + 1  # PF2E tends to have higher attack bonuses
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            return bonus - 1  # D&D 5E tends to have lower attack bonuses
        
        return bonus
    
    def _convert_item_properties(
        self, 
        properties: List[str], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[str]:
        """Convert item properties between systems"""
        
        property_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "light": "agile", "finesse": "finesse", "heavy": "two-hand",
                "reach": "reach", "thrown": "thrown", "versatile": "versatile",
                "ammunition": "ammunition", "loading": "reload", "special": "special"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "agile": "light", "finesse": "finesse", "two-hand": "heavy",
                "reach": "reach", "thrown": "thrown", "versatile": "versatile",
                "ammunition": "ammunition", "reload": "loading", "special": "special"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key not in property_mappings:
            return properties
        
        property_mapping = property_mappings[mapping_key]
        converted_properties = []
        
        for prop in properties:
            mapped_prop = property_mapping.get(prop.lower(), prop)
            converted_properties.append(mapped_prop)
        
        return converted_properties
    
    def _convert_charges(
        self, 
        charges: Optional[int], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Optional[int]:
        """Convert magic item charges between systems"""
        
        if charges is None:
            return None
        
        # Most systems use similar charge mechanics
        return charges
    
    def _convert_attunement(
        self, 
        attunement: bool, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> bool:
        """Convert attunement requirement between systems"""
        
        # D&D 5E uses attunement, PF2E uses investment
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            return attunement  # Investment works similarly
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            return attunement  # Attunement works similarly
        
        return attunement
    
    def _convert_spell_level(
        self, 
        level: int, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> int:
        """Convert spell level between systems"""
        
        # Most systems use 0-9 spell levels with similar power distribution
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # Direct mapping works well
            return level
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            # Direct mapping works well
            return level
        
        return level
    
    def _convert_spell_school(
        self, 
        school: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert spell school between systems"""
        
        school_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "abjuration": "abjuration", "conjuration": "conjuration",
                "divination": "divination", "enchantment": "enchantment",
                "evocation": "evocation", "illusion": "illusion",
                "necromancy": "necromancy", "transmutation": "transmutation"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "abjuration": "abjuration", "conjuration": "conjuration",
                "divination": "divination", "enchantment": "enchantment",
                "evocation": "evocation", "illusion": "illusion",
                "necromancy": "necromancy", "transmutation": "transmutation"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key in school_mappings:
            return school_mappings[mapping_key].get(school.lower(), school)
        
        return school
    
    def _convert_casting_time(
        self, 
        casting_time: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert casting time between systems"""
        
        time_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "1 action": "2 actions", "1 bonus action": "1 action",
                "1 reaction": "reaction", "1 minute": "1 minute",
                "10 minutes": "10 minutes", "1 hour": "1 hour"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "1 action": "1 bonus action", "2 actions": "1 action",
                "3 actions": "1 action", "reaction": "1 reaction",
                "1 minute": "1 minute", "10 minutes": "10 minutes"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key in time_mappings:
            return time_mappings[mapping_key].get(casting_time.lower(), casting_time)
        
        return casting_time
    
    def _convert_spell_range(
        self, 
        range_str: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert spell range between systems"""
        
        # Most systems use similar range measurements (feet)
        # Convert touch/self/etc. as needed
        range_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "self": "self", "touch": "touch", "self (15-foot cone)": "15-foot cone",
                "self (30-foot line)": "30-foot line"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "self": "self", "touch": "touch", "15-foot cone": "self (15-foot cone)",
                "30-foot line": "self (30-foot line)"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key in range_mappings:
            return range_mappings[mapping_key].get(range_str.lower(), range_str)
        
        return range_str
    
    def _convert_spell_components(
        self, 
        components: List[str], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[str]:
        """Convert spell components between systems"""
        
        component_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "v": "verbal", "s": "somatic", "m": "material"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "verbal": "V", "somatic": "S", "material": "M"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key not in component_mappings:
            return components
        
        component_mapping = component_mappings[mapping_key]
        converted_components = []
        
        for component in components:
            mapped_component = component_mapping.get(component.lower(), component)
            converted_components.append(mapped_component)
        
        return converted_components
    
    def _convert_spell_duration(
        self, 
        duration: str, 
        concentration: bool,
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Tuple[str, bool]:
        """Convert spell duration and concentration"""
        
        duration_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "instantaneous": "instantaneous", "1 round": "1 round",
                "1 minute": "1 minute", "10 minutes": "10 minutes",
                "1 hour": "1 hour", "8 hours": "8 hours", "24 hours": "1 day"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "instantaneous": "instantaneous", "1 round": "1 round",
                "1 minute": "1 minute", "10 minutes": "10 minutes",
                "1 hour": "1 hour", "8 hours": "8 hours", "1 day": "24 hours"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key in duration_mappings:
            converted_duration = duration_mappings[mapping_key].get(duration.lower(), duration)
        else:
            converted_duration = duration
        
        # Concentration mechanics work similarly across systems
        converted_concentration = concentration
        
        return converted_duration, converted_concentration
    
    def _convert_spell_damage(
        self, 
        damage: Optional[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Optional[Dict[str, Any]]:
        """Convert spell damage between systems"""
        
        if not damage:
            return None
        
        converted_damage = damage.copy()
        
        # Convert damage type
        if "type" in damage:
            mapping_key = (source_system, target_system)
            if mapping_key in self.damage_type_mappings:
                damage_type = damage["type"].lower()
                converted_damage["type"] = self.damage_type_mappings[mapping_key].get(
                    damage_type, damage["type"]
                )
        
        # Convert damage dice
        if "dice" in damage:
            converted_damage["dice"] = self._convert_damage_dice(
                damage["dice"], source_system, target_system
            )
        
        # Scale damage values
        if "average" in damage:
            scaling_factor = self._get_spell_damage_scaling(source_system, target_system)
            converted_damage["average"] = int(damage["average"] * scaling_factor)
        
        return converted_damage
    
    def _get_spell_damage_scaling(
        self, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> float:
        """Get spell damage scaling factor between systems"""
        
        scaling_factors = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): 1.1,  # PF2E spells slightly stronger
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): 0.9,  # D&D 5E spells slightly weaker
        }
        
        return scaling_factors.get((source_system, target_system), 1.0)
    
    def _convert_spell_save(
        self, 
        save: Optional[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Optional[Dict[str, Any]]:
        """Convert spell save information between systems"""
        
        if not save:
            return None
        
        converted_save = save.copy()
        
        # Convert save type
        if "type" in save:
            save_mappings = {
                (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                    "strength": "fortitude", "dexterity": "reflex", "constitution": "fortitude",
                    "intelligence": "will", "wisdom": "will", "charisma": "will"
                },
                (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                    "fortitude": "constitution", "reflex": "dexterity", "will": "wisdom"
                }
            }
            
            mapping_key = (source_system, target_system)
            if mapping_key in save_mappings:
                save_type = save["type"].lower()
                converted_save["type"] = save_mappings[mapping_key].get(save_type, save["type"])
        
        return converted_save
    
    def _convert_spell_classes(
        self, 
        classes: List[str], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[str]:
        """Convert spell class availability between systems"""
        
        class_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "wizard": "wizard", "sorcerer": "sorcerer", "warlock": "witch",
                "bard": "bard", "cleric": "cleric", "druid": "druid",
                "paladin": "champion", "ranger": "ranger", "artificer": "inventor"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "wizard": "wizard", "sorcerer": "sorcerer", "witch": "warlock",
                "bard": "bard", "cleric": "cleric", "druid": "druid",
                "champion": "paladin", "ranger": "ranger", "inventor": "artificer"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key not in class_mappings:
            return classes
        
        class_mapping = class_mappings[mapping_key]
        converted_classes = []
        
        for class_name in classes:
            mapped_class = class_mapping.get(class_name.lower(), class_name)
            converted_classes.append(mapped_class)
        
        return converted_classes
    
    def _convert_ritual(
        self, 
        ritual: bool, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> bool:
        """Convert ritual casting between systems"""
        
        # Ritual mechanics work similarly across most systems
        return ritual
    
    def _apply_item_mappings(self, item: Item, target_system: GameSystem) -> Dict[str, Any]:
        """Apply system-specific item mappings"""
        
        mapping_key = (item.system, target_system)
        if mapping_key not in ITEM_MAPPINGS:
            return {}
        
        item_mappings = ITEM_MAPPINGS[mapping_key]
        item_key = f"{item.item_type}:{item.name}".lower()
        
        return item_mappings.get(item_key, {})
    
    def _apply_spell_mappings(self, spell: Spell, target_system: GameSystem) -> Dict[str, Any]:
        """Apply system-specific spell mappings"""
        
        mapping_key = (spell.system, target_system)
        if mapping_key not in SPELL_MAPPINGS:
            return {}
        
        spell_mappings = SPELL_MAPPINGS[mapping_key]
        spell_key = f"{spell.level}:{spell.name}".lower()
        
        return spell_mappings.get(spell_key, {})
    
    def _calculate_item_confidence(self, original: Item, converted: Item) -> float:
        """Calculate confidence score for item conversion"""
        
        confidence_factors = []
        
        # Type preservation
        if converted.item_type == original.item_type:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.7)
        
        # Combat stats preservation
        if original.damage and converted.damage:
            confidence_factors.append(0.9)
        elif not original.damage and not converted.damage:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.6)
        
        # Properties preservation
        if len(converted.properties) >= len(original.properties) * 0.7:
            confidence_factors.append(0.85)
        else:
            confidence_factors.append(0.6)
        
        # Magic item complexity
        if original.magic:
            confidence_factors.append(0.75)  # Magic items are more complex
        else:
            confidence_factors.append(0.95)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _calculate_spell_confidence(self, original: Spell, converted: Spell) -> float:
        """Calculate confidence score for spell conversion"""
        
        confidence_factors = []
        
        # Level preservation
        if converted.level == original.level:
            confidence_factors.append(1.0)
        elif abs(converted.level - original.level) <= 1:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.5)
        
        # School preservation
        if converted.school == original.school:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.8)
        
        # Damage conversion confidence
        if original.damage and converted.damage:
            confidence_factors.append(0.8)
        elif not original.damage and not converted.damage:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.6)
        
        # Class availability
        if len(converted.classes) >= len(original.classes) * 0.7:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.7)
        
        return sum(confidence_factors) / len(confidence_factors)