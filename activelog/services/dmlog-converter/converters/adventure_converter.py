"""
Adventure module converter for transforming adventures between game systems
"""

from typing import Dict, List, Any, Optional
from ..models.base import Adventure, ConversionResult, Monster, Item
from ..config.systems import GameSystem, POWER_LEVEL_MAPPINGS
from .character_converter import CharacterConverter


class AdventureConverter:
    """Converts adventure modules between different game systems"""
    
    def __init__(self):
        self.character_converter = CharacterConverter()
    
    def convert_adventure(
        self, 
        adventure: Adventure, 
        target_system: GameSystem
    ) -> ConversionResult:
        """Convert an adventure module to target system"""
        
        if adventure.system == target_system:
            return ConversionResult(
                success=True,
                source_system=adventure.system,
                target_system=target_system,
                converted_data=adventure.dict(),
                conversion_notes=["No conversion needed - same system"]
            )
        
        result = ConversionResult(
            success=True,
            source_system=adventure.system,
            target_system=target_system
        )
        
        try:
            # Convert level range
            converted_level_range = self._convert_level_range(
                adventure.level_range, adventure.system, target_system
            )
            
            # Convert encounters
            converted_encounters = self._convert_encounters(
                adventure.encounters, adventure.system, target_system
            )
            
            # Convert NPCs
            converted_npcs = []
            for npc in adventure.npcs:
                npc_result = self._convert_monster(npc, target_system)
                if npc_result.success:
                    converted_npcs.append(Monster(**npc_result.converted_data))
                else:
                    result.warnings.append(f"Failed to convert NPC: {npc.name}")
            
            # Convert magic items
            converted_items = []
            for item in adventure.magic_items:
                item_result = self._convert_item(item, target_system)
                if item_result.success:
                    converted_items.append(Item(**item_result.converted_data))
                else:
                    result.warnings.append(f"Failed to convert item: {item.name}")
            
            # Convert locations (mostly descriptive, minimal conversion needed)
            converted_locations = self._convert_locations(
                adventure.locations, adventure.system, target_system
            )
            
            # Convert DM scaling advice
            converted_scaling = self._convert_scaling_advice(
                adventure.scaling_advice, adventure.system, target_system
            )
            
            # Build converted adventure
            converted_adventure = Adventure(
                title=adventure.title,
                system=target_system,
                level_range=converted_level_range,
                party_size=adventure.party_size,
                estimated_playtime=adventure.estimated_playtime,
                background=adventure.background,
                synopsis=adventure.synopsis,
                adventure_hooks=adventure.adventure_hooks.copy(),
                encounters=converted_encounters,
                npcs=converted_npcs,
                locations=converted_locations,
                magic_items=converted_items,
                dm_notes=adventure.dm_notes.copy(),
                scaling_advice=converted_scaling,
                system_specific={}
            )
            
            result.converted_data = converted_adventure.dict()
            result.conversion_confidence = self._calculate_adventure_confidence(
                adventure, converted_adventure
            )
            
            if result.conversion_confidence < 0.7:
                result.manual_review_required = True
                result.warnings.append("Adventure conversion needs manual review")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Adventure conversion failed: {str(e)}")
            result.conversion_confidence = 0.0
        
        return result
    
    def _convert_level_range(
        self, 
        level_range: tuple, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> tuple:
        """Convert level range between systems"""
        
        min_level, max_level = level_range
        
        power_mapping_key = (source_system, target_system)
        if power_mapping_key in POWER_LEVEL_MAPPINGS:
            level_mapping = POWER_LEVEL_MAPPINGS[power_mapping_key]
            converted_min = level_mapping.get(min_level, min_level)
            converted_max = level_mapping.get(max_level, max_level)
            return (converted_min, converted_max)
        
        return level_range
    
    def _convert_encounters(
        self, 
        encounters: List[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Convert encounter data between systems"""
        
        converted_encounters = []
        
        for encounter in encounters:
            converted_encounter = encounter.copy()
            
            # Convert challenge rating/difficulty
            if "challenge_rating" in encounter:
                converted_encounter["challenge_rating"] = self._convert_challenge_rating(
                    encounter["challenge_rating"], source_system, target_system
                )
            
            if "difficulty" in encounter:
                converted_encounter["difficulty"] = self._convert_difficulty(
                    encounter["difficulty"], source_system, target_system
                )
            
            # Convert DCs for skill checks
            if "skill_checks" in encounter:
                converted_encounter["skill_checks"] = self._convert_skill_checks(
                    encounter["skill_checks"], source_system, target_system
                )
            
            # Convert damage values
            if "damage" in encounter:
                converted_encounter["damage"] = self._convert_damage_values(
                    encounter["damage"], source_system, target_system
                )
            
            converted_encounters.append(converted_encounter)
        
        return converted_encounters
    
    def _convert_challenge_rating(
        self, 
        cr: Any, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Any:
        """Convert challenge rating between systems"""
        
        if isinstance(cr, (int, float)):
            # D&D 5E to Pathfinder 2E level conversion
            if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
                cr_to_level = {
                    0: -1, 0.125: 0, 0.25: 1, 0.5: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 7,
                    6: 8, 7: 9, 8: 10, 9: 11, 10: 12, 11: 13, 12: 14, 13: 15,
                    14: 16, 15: 17, 16: 18, 17: 19, 18: 20, 19: 21, 20: 22
                }
                return cr_to_level.get(cr, int(cr) + 2)
            
            # Pathfinder 2E to D&D 5E CR conversion
            elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
                level_to_cr = {
                    -1: 0, 0: 0.125, 1: 0.25, 2: 0.5, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5,
                    8: 6, 9: 7, 10: 8, 11: 9, 12: 10, 13: 11, 14: 12, 15: 13,
                    16: 14, 17: 15, 18: 16, 19: 17, 20: 18, 21: 19, 22: 20
                }
                return level_to_cr.get(int(cr), max(0, cr - 2))
        
        return cr
    
    def _convert_difficulty(
        self, 
        difficulty: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert difficulty descriptors between systems"""
        
        # Most systems use similar difficulty terms
        difficulty_mappings = {
            "trivial": "trivial",
            "easy": "low", 
            "medium": "moderate",
            "hard": "severe",
            "deadly": "extreme"
        }
        
        return difficulty_mappings.get(difficulty.lower(), difficulty)
    
    def _convert_skill_checks(
        self, 
        skill_checks: List[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Convert skill check DCs between systems"""
        
        converted_checks = []
        
        for check in skill_checks:
            converted_check = check.copy()
            
            if "dc" in check:
                converted_check["dc"] = self._convert_dc(
                    check["dc"], source_system, target_system
                )
            
            if "skill" in check:
                converted_check["skill"] = self._convert_skill_name(
                    check["skill"], source_system, target_system
                )
            
            converted_checks.append(converted_check)
        
        return converted_checks
    
    def _convert_dc(
        self, 
        dc: int, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> int:
        """Convert difficulty class values between systems"""
        
        # D&D 5E to Pathfinder 2E DC conversion
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            dc_conversion = {
                5: 10, 10: 14, 15: 18, 20: 22, 25: 26, 30: 30
            }
            # Linear interpolation for values not in table
            for threshold in sorted(dc_conversion.keys()):
                if dc <= threshold:
                    return dc_conversion[threshold]
            return dc + 5  # Fallback for very high DCs
        
        # Pathfinder 2E to D&D 5E DC conversion
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            dc_conversion = {
                10: 5, 14: 10, 18: 15, 22: 20, 26: 25, 30: 30
            }
            for threshold in sorted(dc_conversion.keys()):
                if dc <= threshold:
                    return dc_conversion[threshold]
            return max(5, dc - 5)  # Fallback
        
        return dc
    
    def _convert_skill_name(
        self, 
        skill: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert skill names between systems"""
        
        # Import skill mappings from config
        from ..config.systems import SKILL_MAPPINGS
        
        mapping_key = (source_system, target_system)
        if mapping_key in SKILL_MAPPINGS:
            skill_mapping = SKILL_MAPPINGS[mapping_key]
            return skill_mapping.get(skill.lower(), skill)
        
        return skill
    
    def _convert_damage_values(
        self, 
        damage_data: Dict[str, Any], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Convert damage values between systems"""
        
        converted = damage_data.copy()
        
        # Convert dice notation and damage amounts
        if "dice" in damage_data:
            converted["dice"] = self._convert_dice_notation(
                damage_data["dice"], source_system, target_system
            )
        
        if "average" in damage_data:
            converted["average"] = self._scale_damage_value(
                damage_data["average"], source_system, target_system
            )
        
        return converted
    
    def _convert_dice_notation(
        self, 
        dice_str: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert dice notation between systems"""
        
        # Most systems use similar dice notation
        # May need scaling for different damage expectations
        return dice_str
    
    def _scale_damage_value(
        self, 
        damage: int, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> int:
        """Scale damage values between systems"""
        
        # Different systems have different damage expectations
        damage_scaling = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): 1.2,
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): 0.85
        }
        
        scaling_key = (source_system, target_system)
        if scaling_key in damage_scaling:
            return int(damage * damage_scaling[scaling_key])
        
        return damage
    
    def _convert_monster(self, monster: Monster, target_system: GameSystem) -> ConversionResult:
        """Convert a monster to target system"""
        # This would use a monster converter (to be implemented)
        # For now, return a basic conversion
        result = ConversionResult(
            success=True,
            source_system=monster.system,
            target_system=target_system,
            converted_data=monster.dict()
        )
        result.converted_data["system"] = target_system
        return result
    
    def _convert_item(self, item: Item, target_system: GameSystem) -> ConversionResult:
        """Convert an item to target system"""
        # This would use an item converter (to be implemented)
        # For now, return a basic conversion
        result = ConversionResult(
            success=True,
            source_system=item.system,
            target_system=target_system,
            converted_data=item.dict()
        )
        result.converted_data["system"] = target_system
        return result
    
    def _convert_locations(
        self, 
        locations: List[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Convert location data between systems"""
        
        # Locations are mostly descriptive and need minimal conversion
        converted_locations = []
        
        for location in locations:
            converted_location = location.copy()
            
            # Convert any mechanical elements
            if "hazards" in location:
                converted_location["hazards"] = self._convert_hazards(
                    location["hazards"], source_system, target_system
                )
            
            if "traps" in location:
                converted_location["traps"] = self._convert_traps(
                    location["traps"], source_system, target_system
                )
            
            converted_locations.append(converted_location)
        
        return converted_locations
    
    def _convert_hazards(
        self, 
        hazards: List[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Convert environmental hazards between systems"""
        
        converted_hazards = []
        
        for hazard in hazards:
            converted_hazard = hazard.copy()
            
            if "dc" in hazard:
                converted_hazard["dc"] = self._convert_dc(
                    hazard["dc"], source_system, target_system
                )
            
            if "damage" in hazard:
                converted_hazard["damage"] = self._convert_damage_values(
                    hazard["damage"], source_system, target_system
                )
            
            converted_hazards.append(converted_hazard)
        
        return converted_hazards
    
    def _convert_traps(
        self, 
        traps: List[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Convert traps between systems"""
        
        converted_traps = []
        
        for trap in traps:
            converted_trap = trap.copy()
            
            # Convert detection and disarm DCs
            if "detection_dc" in trap:
                converted_trap["detection_dc"] = self._convert_dc(
                    trap["detection_dc"], source_system, target_system
                )
            
            if "disarm_dc" in trap:
                converted_trap["disarm_dc"] = self._convert_dc(
                    trap["disarm_dc"], source_system, target_system
                )
            
            if "trigger_dc" in trap:
                converted_trap["trigger_dc"] = self._convert_dc(
                    trap["trigger_dc"], source_system, target_system
                )
            
            if "damage" in trap:
                converted_trap["damage"] = self._convert_damage_values(
                    trap["damage"], source_system, target_system
                )
            
            converted_traps.append(converted_trap)
        
        return converted_traps
    
    def _convert_scaling_advice(
        self, 
        scaling_advice: Dict[str, str], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, str]:
        """Convert DM scaling advice between systems"""
        
        converted_advice = {}
        
        for level_range, advice in scaling_advice.items():
            # Convert level range in key
            if "-" in level_range:
                start_level, end_level = level_range.split("-")
                start_level = int(start_level.strip())
                end_level = int(end_level.strip())
                
                converted_start, _ = self._convert_level_range(
                    (start_level, end_level), source_system, target_system
                )
                _, converted_end = self._convert_level_range(
                    (start_level, end_level), source_system, target_system
                )
                
                converted_key = f"{converted_start}-{converted_end}"
            else:
                converted_key = level_range
            
            # Convert advice text (mostly stays the same)
            converted_advice[converted_key] = advice
        
        return converted_advice
    
    def _calculate_adventure_confidence(
        self, 
        original: Adventure, 
        converted: Adventure
    ) -> float:
        """Calculate confidence score for adventure conversion"""
        
        confidence_factors = []
        
        # Level range conversion confidence
        if converted.level_range[1] - converted.level_range[0] == \
           original.level_range[1] - original.level_range[0]:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.8)
        
        # Content preservation confidence
        if len(converted.encounters) >= len(original.encounters) * 0.9:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.6)
        
        if len(converted.npcs) >= len(original.npcs) * 0.8:
            confidence_factors.append(0.85)
        else:
            confidence_factors.append(0.7)
        
        # Mechanical conversion confidence
        confidence_factors.append(0.8)  # Base mechanical conversion confidence
        
        return sum(confidence_factors) / len(confidence_factors)