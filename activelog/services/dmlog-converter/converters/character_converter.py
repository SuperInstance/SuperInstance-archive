"""
Character converter for transforming characters between game systems
"""

import math
from typing import Dict, List, Any, Optional
from ..models.base import Character, ConversionResult, ConversionRule
from ..config.systems import (
    GameSystem, ATTRIBUTE_MAPPINGS, SKILL_MAPPINGS, 
    POWER_LEVEL_MAPPINGS, CLASS_MAPPINGS, RACE_MAPPINGS
)


class CharacterConverter:
    """Converts characters between different game systems"""
    
    def __init__(self):
        self.conversion_rules: List[ConversionRule] = []
    
    def convert_character(
        self, 
        character: Character, 
        target_system: GameSystem
    ) -> ConversionResult:
        """Convert a character to target system"""
        
        if character.system == target_system:
            return ConversionResult(
                success=True,
                source_system=character.system,
                target_system=target_system,
                converted_data=character.dict(),
                conversion_notes=["No conversion needed - same system"]
            )
        
        result = ConversionResult(
            success=True,
            source_system=character.system,
            target_system=target_system
        )
        
        try:
            # Convert core attributes
            converted_attributes = self._convert_attributes(
                character.attributes, character.system, target_system
            )
            
            # Convert level and experience
            converted_level, converted_xp = self._convert_level_and_xp(
                character.level, character.experience_points, 
                character.system, target_system
            )
            
            # Convert race and class
            converted_race = self._convert_race(
                character.race, character.system, target_system
            )
            converted_class = self._convert_class(
                character.character_class, character.system, target_system
            )
            
            # Convert skills
            converted_skills = self._convert_skills(
                character.skills, character.system, target_system
            )
            
            # Convert hit points and combat stats
            converted_hp = self._convert_hit_points(
                character.hit_points, character.level,
                character.system, target_system
            )
            
            converted_ac = self._convert_armor_class(
                character.armor_class, character.system, target_system
            )
            
            # Convert saves
            converted_saves = self._convert_saving_throws(
                character.saving_throws, character.system, target_system
            )
            
            # Build converted character data
            converted_character = Character(
                name=character.name,
                system=target_system,
                attributes=converted_attributes,
                level=converted_level,
                experience_points=converted_xp,
                race=converted_race,
                character_class=converted_class,
                subclass=character.subclass,  # May need system-specific conversion
                background=character.background,
                skills=converted_skills,
                proficiencies=character.proficiencies.copy(),
                languages=character.languages.copy(),
                hit_points=converted_hp,
                armor_class=converted_ac,
                speed=character.speed.copy(),
                saving_throws=converted_saves,
                attack_bonuses=character.attack_bonuses.copy(),
                features=character.features.copy(),
                spells=character.spells.copy(),
                equipment=character.equipment.copy(),
                system_specific={}
            )
            
            result.converted_data = converted_character.dict()
            result.conversion_confidence = self._calculate_confidence(
                character, converted_character
            )
            
            if result.conversion_confidence < 0.8:
                result.manual_review_required = True
                result.warnings.append("Low conversion confidence - manual review recommended")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Conversion failed: {str(e)}")
            result.conversion_confidence = 0.0
        
        return result
    
    def _convert_attributes(
        self, 
        attributes: Dict[str, int], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, int]:
        """Convert attribute scores between systems"""
        
        mapping_key = (source_system, target_system)
        if mapping_key not in ATTRIBUTE_MAPPINGS:
            # Use reverse mapping if available
            reverse_key = (target_system, source_system)
            if reverse_key in ATTRIBUTE_MAPPINGS:
                reverse_mapping = {v: k for k, v in ATTRIBUTE_MAPPINGS[reverse_key].items()}
                mapping = reverse_mapping
            else:
                # No mapping available - return as-is
                return attributes.copy()
        else:
            mapping = ATTRIBUTE_MAPPINGS[mapping_key]
        
        converted = {}
        for source_attr, value in attributes.items():
            if source_attr in mapping:
                target_attr = mapping[source_attr]
                # Apply system-specific scaling
                converted_value = self._scale_attribute_value(
                    value, source_system, target_system
                )
                converted[target_attr] = converted_value
            else:
                # Attribute doesn't exist in target system
                converted[source_attr] = value
        
        return converted
    
    def _scale_attribute_value(
        self, 
        value: int, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> int:
        """Scale attribute values between different systems"""
        
        # D&D 5E uses 3-20 range, Pathfinder 2E uses 10-24 range
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # Convert D&D 5E (8-20) to Pathfinder 2E (10-24)
            if value <= 8:
                return 10
            elif value >= 20:
                return 24
            else:
                # Linear scaling: 8->10, 14->18, 20->24
                return int(10 + (value - 8) * (24 - 10) / (20 - 8))
        
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            # Convert Pathfinder 2E (10-24) to D&D 5E (8-20)
            if value <= 10:
                return 8
            elif value >= 24:
                return 20
            else:
                return int(8 + (value - 10) * (20 - 8) / (24 - 10))
        
        # For other systems or same system, return unchanged
        return value
    
    def _convert_level_and_xp(
        self, 
        level: int, 
        xp: Optional[int], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> tuple[int, Optional[int]]:
        """Convert character level and experience points"""
        
        power_mapping_key = (source_system, target_system)
        if power_mapping_key in POWER_LEVEL_MAPPINGS:
            level_mapping = POWER_LEVEL_MAPPINGS[power_mapping_key]
            converted_level = level_mapping.get(level, level)
        else:
            converted_level = level
        
        # XP conversion is complex and system-dependent
        # For now, set to None and let target system calculate
        converted_xp = None
        
        return converted_level, converted_xp
    
    def _convert_race(
        self, 
        race: Optional[str], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Optional[str]:
        """Convert character race between systems"""
        
        if not race:
            return race
        
        mapping_key = (source_system, target_system)
        if mapping_key in RACE_MAPPINGS:
            return RACE_MAPPINGS[mapping_key].get(race.lower(), race)
        
        return race
    
    def _convert_class(
        self, 
        char_class: Optional[str], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Optional[str]:
        """Convert character class between systems"""
        
        if not char_class:
            return char_class
        
        mapping_key = (source_system, target_system)
        if mapping_key in CLASS_MAPPINGS:
            return CLASS_MAPPINGS[mapping_key].get(char_class.lower(), char_class)
        
        return char_class
    
    def _convert_skills(
        self, 
        skills: Dict[str, Any], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Convert skills between systems"""
        
        mapping_key = (source_system, target_system)
        if mapping_key not in SKILL_MAPPINGS:
            return skills.copy()
        
        skill_mapping = SKILL_MAPPINGS[mapping_key]
        converted = {}
        
        for skill_name, skill_value in skills.items():
            mapped_skill = skill_mapping.get(skill_name.lower(), skill_name)
            converted[mapped_skill] = skill_value
        
        return converted
    
    def _convert_hit_points(
        self, 
        hp_dict: Dict[str, int], 
        level: int,
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, int]:
        """Convert hit points between systems"""
        
        if not hp_dict:
            return {"max": level * 8, "current": level * 8, "temp": 0}
        
        # Hit points are often system-dependent due to different HD sizes
        # For now, preserve the structure but may need scaling
        converted = hp_dict.copy()
        
        # Apply system-specific HP scaling if needed
        if source_system != target_system:
            max_hp = hp_dict.get("max", 0)
            if max_hp > 0:
                # Simple scaling based on level expectations
                scaling_factor = self._get_hp_scaling_factor(source_system, target_system)
                converted["max"] = int(max_hp * scaling_factor)
                converted["current"] = min(hp_dict.get("current", max_hp), converted["max"])
        
        return converted
    
    def _get_hp_scaling_factor(
        self, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> float:
        """Get HP scaling factor between systems"""
        
        # System-specific HP expectations per level
        hp_per_level = {
            GameSystem.D_AND_D_5E: 8.0,
            GameSystem.PATHFINDER_2E: 10.0,
            GameSystem.PATHFINDER_1E: 8.5,
            GameSystem.CALL_OF_CTHULHU_7E: 12.0
        }
        
        source_hp = hp_per_level.get(source_system, 8.0)
        target_hp = hp_per_level.get(target_system, 8.0)
        
        return target_hp / source_hp
    
    def _convert_armor_class(
        self, 
        ac: Optional[int], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Optional[int]:
        """Convert armor class between systems"""
        
        if ac is None:
            return None
        
        # AC scaling between systems
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # Pathfinder 2E typically has higher AC values
            return ac + 2
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            # D&D 5E typically has lower AC values
            return max(10, ac - 2)
        
        return ac
    
    def _convert_saving_throws(
        self, 
        saves: Dict[str, int], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, int]:
        """Convert saving throws between systems"""
        
        if not saves:
            return {}
        
        # Map save names between systems
        save_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "strength": "fortitude",
                "dexterity": "reflex", 
                "constitution": "fortitude",
                "intelligence": "will",
                "wisdom": "will",
                "charisma": "will"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "fortitude": "constitution",
                "reflex": "dexterity",
                "will": "wisdom"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key not in save_mappings:
            return saves.copy()
        
        save_mapping = save_mappings[mapping_key]
        converted = {}
        
        for save_name, save_value in saves.items():
            mapped_save = save_mapping.get(save_name.lower(), save_name)
            if mapped_save in converted:
                # Take the higher value if multiple source saves map to same target
                converted[mapped_save] = max(converted[mapped_save], save_value)
            else:
                converted[mapped_save] = save_value
        
        return converted
    
    def _calculate_confidence(
        self, 
        original: Character, 
        converted: Character
    ) -> float:
        """Calculate conversion confidence score"""
        
        confidence_factors = []
        
        # Attribute mapping confidence
        if len(converted.attributes) >= len(original.attributes) * 0.8:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.6)
        
        # Class mapping confidence
        if converted.character_class and original.character_class:
            if converted.character_class.lower() == original.character_class.lower():
                confidence_factors.append(1.0)
            else:
                confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.8)
        
        # Race mapping confidence
        if converted.race and original.race:
            if converted.race.lower() == original.race.lower():
                confidence_factors.append(1.0)
            else:
                confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.9)
        
        # Skill mapping confidence
        if len(converted.skills) >= len(original.skills) * 0.7:
            confidence_factors.append(0.85)
        else:
            confidence_factors.append(0.6)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def add_conversion_rule(self, rule: ConversionRule):
        """Add a custom conversion rule"""
        self.conversion_rules.append(rule)
    
    def get_conversion_preview(
        self, 
        character: Character, 
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Get a preview of what the conversion will produce"""
        
        preview = {
            "source_system": character.system.value,
            "target_system": target_system.value,
            "character_name": character.name,
            "changes": []
        }
        
        # Preview attribute changes
        converted_attrs = self._convert_attributes(
            character.attributes, character.system, target_system
        )
        for attr, old_val in character.attributes.items():
            if attr in converted_attrs and converted_attrs[attr] != old_val:
                preview["changes"].append({
                    "type": "attribute",
                    "name": attr,
                    "old_value": old_val,
                    "new_value": converted_attrs[attr]
                })
        
        # Preview class/race changes
        new_class = self._convert_class(
            character.character_class, character.system, target_system
        )
        if new_class != character.character_class:
            preview["changes"].append({
                "type": "class",
                "old_value": character.character_class,
                "new_value": new_class
            })
        
        new_race = self._convert_race(
            character.race, character.system, target_system
        )
        if new_race != character.race:
            preview["changes"].append({
                "type": "race", 
                "old_value": character.race,
                "new_value": new_race
            })
        
        return preview