"""
Monster/NPC stat block converter for transforming creatures between game systems
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from ..models.base import Monster, ConversionResult
from ..config.systems import GameSystem
from .difficulty_converter import DifficultyConverter


class MonsterConverter:
    """Converts monsters and NPCs between different game systems"""
    
    def __init__(self):
        self.difficulty_converter = DifficultyConverter()
        
        # Size mappings between systems
        self.size_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "tiny": "tiny", "small": "small", "medium": "medium",
                "large": "large", "huge": "huge", "gargantuan": "gargantuan"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "tiny": "tiny", "small": "small", "medium": "medium", 
                "large": "large", "huge": "huge", "gargantuan": "gargantuan"
            }
        }
        
        # Creature type mappings
        self.creature_type_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "aberration": "aberration", "beast": "beast", "celestial": "celestial",
                "construct": "construct", "dragon": "dragon", "elemental": "elemental",
                "fey": "fey", "fiend": "fiend", "giant": "giant", "humanoid": "humanoid",
                "monstrosity": "beast", "ooze": "ooze", "plant": "plant",
                "undead": "undead"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "aberration": "aberration", "beast": "beast", "celestial": "celestial",
                "construct": "construct", "dragon": "dragon", "elemental": "elemental",
                "fey": "fey", "fiend": "fiend", "giant": "giant", "humanoid": "humanoid",
                "ooze": "ooze", "plant": "plant", "undead": "undead"
            }
        }
        
        # Alignment mappings
        self.alignment_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "lawful good": "lawful good", "neutral good": "neutral good",
                "chaotic good": "chaotic good", "lawful neutral": "lawful neutral",
                "neutral": "true neutral", "chaotic neutral": "chaotic neutral",
                "lawful evil": "lawful evil", "neutral evil": "neutral evil",
                "chaotic evil": "chaotic evil", "unaligned": "true neutral"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "lawful good": "lawful good", "neutral good": "neutral good",
                "chaotic good": "chaotic good", "lawful neutral": "lawful neutral",
                "true neutral": "neutral", "chaotic neutral": "chaotic neutral",
                "lawful evil": "lawful evil", "neutral evil": "neutral evil",
                "chaotic evil": "chaotic evil"
            }
        }
    
    def convert_monster(self, monster: Monster, target_system: GameSystem) -> ConversionResult:
        """Convert a monster to target system"""
        
        if monster.system == target_system:
            return ConversionResult(
                success=True,
                source_system=monster.system,
                target_system=target_system,
                converted_data=monster.dict(),
                conversion_notes=["No conversion needed - same system"]
            )
        
        result = ConversionResult(
            success=True,
            source_system=monster.system,
            target_system=target_system
        )
        
        try:
            # Convert basic properties
            converted_size = self._convert_size(monster.size, monster.system, target_system)
            converted_type = self._convert_creature_type(
                monster.creature_type, monster.system, target_system
            )
            converted_alignment = self._convert_alignment(
                monster.alignment, monster.system, target_system
            )
            
            # Convert attributes
            converted_attributes = self._convert_attributes(
                monster.attributes, monster.system, target_system
            )
            
            # Convert hit points
            converted_hp = self._convert_hit_points(
                monster.hit_points, monster.challenge_rating, monster.system, target_system
            )
            
            # Convert armor class
            converted_ac = self._convert_armor_class(
                monster.armor_class, monster.system, target_system
            )
            
            # Convert speed
            converted_speed = self._convert_speed(
                monster.speed, monster.system, target_system
            )
            
            # Convert challenge rating
            cr_result = self.difficulty_converter.convert_challenge_rating(
                monster.challenge_rating, 
                self._estimate_party_level_from_cr(monster.challenge_rating, monster.system),
                monster.system, target_system
            )
            converted_cr = cr_result.converted_data.get("challenge_rating", monster.challenge_rating)
            
            # Convert experience value
            converted_xp = self._convert_experience_value(
                monster.experience_value, converted_cr, target_system
            )
            
            # Convert saves and skills
            converted_saves = self._convert_saving_throws(
                monster.saving_throws, monster.system, target_system
            )
            converted_skills = self._convert_skills(
                monster.skills, monster.system, target_system
            )
            
            # Convert resistances and immunities
            converted_resistances = self._convert_damage_resistances(
                monster.damage_resistances, monster.system, target_system
            )
            converted_immunities = self._convert_damage_immunities(
                monster.damage_immunities, monster.system, target_system
            )
            converted_condition_immunities = self._convert_condition_immunities(
                monster.condition_immunities, monster.system, target_system
            )
            
            # Convert senses
            converted_senses = self._convert_senses(
                monster.senses, monster.system, target_system
            )
            
            # Convert abilities and actions
            converted_abilities = self._convert_special_abilities(
                monster.special_abilities, monster.system, target_system
            )
            converted_actions = self._convert_actions(
                monster.actions, monster.system, target_system
            )
            converted_bonus_actions = self._convert_bonus_actions(
                monster.bonus_actions, monster.system, target_system
            )
            converted_reactions = self._convert_reactions(
                monster.reactions, monster.system, target_system
            )
            converted_legendary_actions = self._convert_legendary_actions(
                monster.legendary_actions, monster.system, target_system
            )
            
            # Convert spellcasting
            converted_spellcasting = self._convert_spellcasting(
                monster.spellcasting, monster.system, target_system
            )
            
            # Build converted monster
            converted_monster = Monster(
                name=monster.name,
                system=target_system,
                size=converted_size,
                creature_type=converted_type,
                alignment=converted_alignment,
                attributes=converted_attributes,
                hit_points=converted_hp,
                armor_class=converted_ac,
                speed=converted_speed,
                challenge_rating=converted_cr,
                experience_value=converted_xp,
                saving_throws=converted_saves,
                skills=converted_skills,
                damage_resistances=converted_resistances,
                damage_immunities=converted_immunities,
                condition_immunities=converted_condition_immunities,
                senses=converted_senses,
                languages=monster.languages.copy(),
                special_abilities=converted_abilities,
                actions=converted_actions,
                bonus_actions=converted_bonus_actions,
                reactions=converted_reactions,
                legendary_actions=converted_legendary_actions,
                spellcasting=converted_spellcasting,
                system_specific={}
            )
            
            result.converted_data = converted_monster.dict()
            result.conversion_confidence = self._calculate_monster_confidence(
                monster, converted_monster
            )
            
            if result.conversion_confidence < 0.7:
                result.manual_review_required = True
                result.warnings.append("Complex monster conversion needs manual review")
            
            # Add conversion notes
            if abs(converted_cr - monster.challenge_rating) > 1:
                result.conversion_notes.append(f"Challenge rating changed significantly: {monster.challenge_rating} -> {converted_cr}")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Monster conversion failed: {str(e)}")
            result.conversion_confidence = 0.0
        
        return result
    
    def _convert_size(self, size: str, source_system: GameSystem, target_system: GameSystem) -> str:
        """Convert creature size between systems"""
        
        mapping_key = (source_system, target_system)
        if mapping_key in self.size_mappings:
            return self.size_mappings[mapping_key].get(size.lower(), size)
        
        return size
    
    def _convert_creature_type(
        self, 
        creature_type: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert creature type between systems"""
        
        mapping_key = (source_system, target_system)
        if mapping_key in self.creature_type_mappings:
            return self.creature_type_mappings[mapping_key].get(creature_type.lower(), creature_type)
        
        return creature_type
    
    def _convert_alignment(
        self, 
        alignment: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert alignment between systems"""
        
        mapping_key = (source_system, target_system)
        if mapping_key in self.alignment_mappings:
            return self.alignment_mappings[mapping_key].get(alignment.lower(), alignment)
        
        return alignment
    
    def _convert_attributes(
        self, 
        attributes: Dict[str, int], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, int]:
        """Convert attribute scores between systems"""
        
        # Use the same attribute conversion from character converter
        from ..config.systems import ATTRIBUTE_MAPPINGS
        
        mapping_key = (source_system, target_system)
        if mapping_key not in ATTRIBUTE_MAPPINGS:
            return attributes.copy()
        
        mapping = ATTRIBUTE_MAPPINGS[mapping_key]
        converted = {}
        
        for source_attr, value in attributes.items():
            if source_attr in mapping:
                target_attr = mapping[source_attr]
                converted_value = self._scale_attribute_value(
                    value, source_system, target_system
                )
                converted[target_attr] = converted_value
            else:
                converted[source_attr] = value
        
        return converted
    
    def _scale_attribute_value(
        self, 
        value: int, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> int:
        """Scale attribute values between different systems"""
        
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # PF2E uses different attribute scaling
            if value <= 8:
                return 10
            elif value >= 20:
                return 24
            else:
                return int(10 + (value - 8) * (24 - 10) / (20 - 8))
        
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            if value <= 10:
                return 8
            elif value >= 24:
                return 20
            else:
                return int(8 + (value - 10) * (20 - 8) / (24 - 10))
        
        return value
    
    def _convert_hit_points(
        self, 
        hp: int, 
        cr: float, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> int:
        """Convert hit points between systems"""
        
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # PF2E monsters tend to have slightly more HP
            return int(hp * 1.1)
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            # D&D 5E monsters tend to have slightly less HP
            return int(hp * 0.9)
        
        return hp
    
    def _convert_armor_class(
        self, 
        ac: int, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> int:
        """Convert armor class between systems"""
        
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            return ac + 2  # PF2E AC tends to be higher
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            return max(10, ac - 2)  # D&D 5E AC tends to be lower
        
        return ac
    
    def _convert_speed(
        self, 
        speed: Dict[str, int], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, int]:
        """Convert movement speeds between systems"""
        
        # Most systems use similar speed mechanics (feet per round/turn)
        # Just need to map speed types
        speed_mappings = {
            "walk": "walk", "fly": "fly", "swim": "swim", "climb": "climb",
            "burrow": "burrow", "hover": "fly"
        }
        
        converted_speed = {}
        for speed_type, speed_value in speed.items():
            mapped_type = speed_mappings.get(speed_type, speed_type)
            converted_speed[mapped_type] = speed_value
        
        return converted_speed
    
    def _estimate_party_level_from_cr(self, cr: float, system: GameSystem) -> int:
        """Estimate appropriate party level for a given CR"""
        
        if system == GameSystem.D_AND_D_5E:
            if cr <= 0.25:
                return 1
            elif cr <= 2:
                return int(cr) + 1
            else:
                return min(20, int(cr) + 2)
        elif system == GameSystem.PATHFINDER_2E:
            # In PF2E, creature level roughly equals party level for moderate encounters
            return max(1, min(20, int(cr)))
        else:
            return max(1, min(20, int(cr)))
    
    def _convert_experience_value(
        self, 
        xp: int, 
        new_cr: float, 
        target_system: GameSystem
    ) -> int:
        """Convert experience value for new system"""
        
        if target_system == GameSystem.D_AND_D_5E:
            # D&D 5E XP by CR
            xp_table = {
                0: 10, 0.125: 25, 0.25: 50, 0.5: 100, 1: 200, 2: 450, 3: 700,
                4: 1100, 5: 1800, 6: 2300, 7: 2900, 8: 3900, 9: 5000, 10: 5900,
                11: 7200, 12: 8400, 13: 10000, 14: 11500, 15: 13000, 16: 15000,
                17: 18000, 18: 20000, 19: 22000, 20: 25000
            }
            return xp_table.get(new_cr, xp)
        elif target_system == GameSystem.PATHFINDER_2E:
            # PF2E doesn't use XP in the same way, return 0
            return 0
        else:
            # For other systems, scale proportionally
            return xp
    
    def _convert_saving_throws(
        self, 
        saves: Dict[str, int], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, int]:
        """Convert saving throws between systems"""
        
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
        if mapping_key not in save_mappings:
            return saves.copy()
        
        save_mapping = save_mappings[mapping_key]
        converted = {}
        
        for save_name, save_value in saves.items():
            mapped_save = save_mapping.get(save_name.lower(), save_name)
            if mapped_save in converted:
                # Take the higher value if multiple saves map to same target
                converted[mapped_save] = max(converted[mapped_save], save_value)
            else:
                converted[mapped_save] = save_value
        
        return converted
    
    def _convert_skills(
        self, 
        skills: Dict[str, int], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, int]:
        """Convert skills between systems"""
        
        from ..config.systems import SKILL_MAPPINGS
        
        mapping_key = (source_system, target_system)
        if mapping_key not in SKILL_MAPPINGS:
            return skills.copy()
        
        skill_mapping = SKILL_MAPPINGS[mapping_key]
        converted = {}
        
        for skill_name, skill_value in skills.items():
            mapped_skill = skill_mapping.get(skill_name.lower(), skill_name)
            converted[mapped_skill] = skill_value
        
        return converted
    
    def _convert_damage_resistances(
        self, 
        resistances: List[str], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[str]:
        """Convert damage resistances between systems"""
        
        damage_type_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "lightning": "electricity", "thunder": "sonic", "psychic": "mental",
                "radiant": "positive", "necrotic": "negative"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "electricity": "lightning", "sonic": "thunder", "mental": "psychic",
                "positive": "radiant", "negative": "necrotic"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key not in damage_type_mappings:
            return resistances.copy()
        
        type_mapping = damage_type_mappings[mapping_key]
        converted = []
        
        for resistance in resistances:
            mapped_resistance = type_mapping.get(resistance.lower(), resistance)
            converted.append(mapped_resistance)
        
        return converted
    
    def _convert_damage_immunities(
        self, 
        immunities: List[str], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[str]:
        """Convert damage immunities between systems"""
        
        # Use same mapping as resistances
        return self._convert_damage_resistances(immunities, source_system, target_system)
    
    def _convert_condition_immunities(
        self, 
        immunities: List[str], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[str]:
        """Convert condition immunities between systems"""
        
        condition_mappings = {
            (GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E): {
                "blinded": "blinded", "charmed": "controlled", "deafened": "deafened",
                "frightened": "frightened", "grappled": "grabbed", "incapacitated": "stunned",
                "invisible": "invisible", "paralyzed": "paralyzed", "petrified": "petrified",
                "poisoned": "sickened", "prone": "prone", "restrained": "restrained",
                "stunned": "stunned", "unconscious": "unconscious"
            },
            (GameSystem.PATHFINDER_2E, GameSystem.D_AND_D_5E): {
                "blinded": "blinded", "controlled": "charmed", "deafened": "deafened",
                "frightened": "frightened", "grabbed": "grappled", "stunned": "stunned",
                "invisible": "invisible", "paralyzed": "paralyzed", "petrified": "petrified",
                "sickened": "poisoned", "prone": "prone", "restrained": "restrained",
                "unconscious": "unconscious"
            }
        }
        
        mapping_key = (source_system, target_system)
        if mapping_key not in condition_mappings:
            return immunities.copy()
        
        condition_mapping = condition_mappings[mapping_key]
        converted = []
        
        for immunity in immunities:
            mapped_immunity = condition_mapping.get(immunity.lower(), immunity)
            converted.append(mapped_immunity)
        
        return converted
    
    def _convert_senses(
        self, 
        senses: Dict[str, int], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Dict[str, int]:
        """Convert senses between systems"""
        
        # Most senses translate directly
        sense_mappings = {
            "blindsight": "blindsight", "darkvision": "darkvision", 
            "tremorsense": "tremorsense", "truesight": "truesight"
        }
        
        converted = {}
        for sense_type, sense_range in senses.items():
            mapped_sense = sense_mappings.get(sense_type, sense_type)
            converted[mapped_sense] = sense_range
        
        return converted
    
    def _convert_special_abilities(
        self, 
        abilities: List[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Convert special abilities between systems"""
        
        converted_abilities = []
        
        for ability in abilities:
            converted_ability = ability.copy()
            
            # Convert ability descriptions using mechanic converter patterns
            if "description" in ability:
                converted_ability["description"] = self._convert_ability_text(
                    ability["description"], source_system, target_system
                )
            
            converted_abilities.append(converted_ability)
        
        return converted_abilities
    
    def _convert_actions(
        self, 
        actions: List[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Convert actions between systems"""
        
        converted_actions = []
        
        for action in actions:
            converted_action = action.copy()
            
            # Convert attack bonuses
            if "attack_bonus" in action:
                converted_action["attack_bonus"] = self._scale_attack_bonus(
                    action["attack_bonus"], source_system, target_system
                )
            
            # Convert damage
            if "damage" in action:
                converted_action["damage"] = self._convert_action_damage(
                    action["damage"], source_system, target_system
                )
            
            # Convert save DCs
            if "save_dc" in action:
                converted_action["save_dc"] = self._convert_save_dc(
                    action["save_dc"], source_system, target_system
                )
            
            # Convert description text
            if "description" in action:
                converted_action["description"] = self._convert_ability_text(
                    action["description"], source_system, target_system
                )
            
            converted_actions.append(converted_action)
        
        return converted_actions
    
    def _convert_bonus_actions(
        self, 
        bonus_actions: List[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Convert bonus actions between systems"""
        
        # Bonus actions become single actions in PF2E
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            converted = []
            for bonus_action in bonus_actions:
                converted_action = bonus_action.copy()
                if "action_cost" not in converted_action:
                    converted_action["action_cost"] = "1 action"
                converted.append(converted_action)
            return converted
        
        return self._convert_actions(bonus_actions, source_system, target_system)
    
    def _convert_reactions(
        self, 
        reactions: List[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Convert reactions between systems"""
        
        return self._convert_actions(reactions, source_system, target_system)
    
    def _convert_legendary_actions(
        self, 
        legendary_actions: List[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Convert legendary actions between systems"""
        
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            # Legendary actions become "extra actions" or special abilities
            converted = []
            for leg_action in legendary_actions:
                converted_action = leg_action.copy()
                # Mark as special ability in PF2E
                converted_action["type"] = "special_ability"
                converted.append(converted_action)
            return converted
        
        return self._convert_actions(legendary_actions, source_system, target_system)
    
    def _convert_spellcasting(
        self, 
        spellcasting: Optional[Dict[str, Any]], 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> Optional[Dict[str, Any]]:
        """Convert spellcasting abilities between systems"""
        
        if not spellcasting:
            return None
        
        converted = spellcasting.copy()
        
        # Convert spell save DC
        if "spell_save_dc" in spellcasting:
            converted["spell_save_dc"] = self._convert_save_dc(
                spellcasting["spell_save_dc"], source_system, target_system
            )
        
        # Convert spell attack bonus
        if "spell_attack_bonus" in spellcasting:
            converted["spell_attack_bonus"] = self._scale_attack_bonus(
                spellcasting["spell_attack_bonus"], source_system, target_system
            )
        
        # Convert spellcaster level
        if "caster_level" in spellcasting:
            # Most systems use similar caster level progressions
            converted["caster_level"] = spellcasting["caster_level"]
        
        return converted
    
    def _convert_ability_text(
        self, 
        text: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert ability description text between systems"""
        
        # Use patterns from mechanic converter
        from .mechanic_converter import MechanicConverter
        
        mechanic_converter = MechanicConverter()
        
        # Convert dice mechanics
        converted_text = mechanic_converter._convert_dice_mechanics(
            text, source_system, target_system
        )
        
        # Convert DC references
        converted_text = mechanic_converter._convert_dc_references(
            converted_text, source_system, target_system
        )
        
        # Convert saving throw references
        converted_text = mechanic_converter._convert_saving_throw_references(
            converted_text, source_system, target_system
        )
        
        # Convert action economy terms
        converted_text = mechanic_converter._convert_action_economy(
            converted_text, source_system, target_system
        )
        
        return converted_text
    
    def _scale_attack_bonus(
        self, 
        bonus: int, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> int:
        """Scale attack bonus between systems"""
        
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            return bonus + 2  # PF2E has higher attack bonuses
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            return max(0, bonus - 2)  # D&D 5E has lower attack bonuses
        
        return bonus
    
    def _convert_action_damage(
        self, 
        damage: str, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> str:
        """Convert action damage between systems"""
        
        # Use similar logic to item damage conversion
        from .item_spell_converter import ItemSpellConverter
        
        converter = ItemSpellConverter()
        return converter._convert_damage_dice(damage, source_system, target_system)
    
    def _convert_save_dc(
        self, 
        dc: int, 
        source_system: GameSystem, 
        target_system: GameSystem
    ) -> int:
        """Convert save DC between systems"""
        
        if source_system == GameSystem.D_AND_D_5E and target_system == GameSystem.PATHFINDER_2E:
            return dc + 4  # PF2E DCs are generally higher
        elif source_system == GameSystem.PATHFINDER_2E and target_system == GameSystem.D_AND_D_5E:
            return max(10, dc - 4)  # D&D 5E DCs are generally lower
        
        return dc
    
    def _calculate_monster_confidence(
        self, 
        original: Monster, 
        converted: Monster
    ) -> float:
        """Calculate confidence score for monster conversion"""
        
        confidence_factors = []
        
        # Basic properties preservation
        if converted.size == original.size:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.9)
        
        if converted.creature_type == original.creature_type:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.8)
        
        # Combat stats scaling confidence
        hp_ratio = converted.hit_points / original.hit_points if original.hit_points > 0 else 1.0
        if 0.8 <= hp_ratio <= 1.2:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.7)
        
        # Abilities preservation
        if len(converted.actions) >= len(original.actions) * 0.8:
            confidence_factors.append(0.85)
        else:
            confidence_factors.append(0.6)
        
        if len(converted.special_abilities) >= len(original.special_abilities) * 0.7:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        # Complexity assessment
        total_abilities = (
            len(original.special_abilities) + len(original.actions) + 
            len(original.bonus_actions) + len(original.reactions) + 
            len(original.legendary_actions)
        )
        
        if total_abilities <= 5:
            confidence_factors.append(0.9)  # Simple monsters convert well
        elif total_abilities <= 10:
            confidence_factors.append(0.75)  # Moderate complexity
        else:
            confidence_factors.append(0.6)  # Complex monsters need more review
        
        return sum(confidence_factors) / len(confidence_factors)