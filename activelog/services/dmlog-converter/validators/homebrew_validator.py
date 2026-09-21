"""
Homebrew content validator for ensuring quality and balance of custom content
"""

import re
import math
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from ..models.base import ValidationResult, Character, Monster, Spell, Item, BalanceCheck
from ..config.systems import GameSystem


class ValidationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BalanceCategory(Enum):
    UNDERPOWERED = "underpowered"
    BALANCED = "balanced"
    OVERPOWERED = "overpowered"
    BROKEN = "broken"


class HomebrewValidator:
    """Validates homebrew content for quality, balance, and system compliance"""
    
    def __init__(self):
        self.validation_rules = {}
        self.balance_benchmarks = {}
        self.system_requirements = {}
        
        self._initialize_validation_rules()
        self._initialize_balance_benchmarks()
        self._initialize_system_requirements()
    
    def validate_character(self, character: Character) -> ValidationResult:
        """Validate a homebrew character"""
        
        result = ValidationResult(
            valid=True,
            content_type="character",
            content_id=character.id,
            system=character.system
        )
        
        try:
            # Basic structure validation
            structure_issues = self._validate_character_structure(character)
            result.syntax_errors.extend(structure_issues["errors"])
            result.warnings.extend(structure_issues["warnings"])
            
            # Attribute validation
            attribute_issues = self._validate_character_attributes(character)
            result.semantic_errors.extend(attribute_issues["errors"])
            result.warnings.extend(attribute_issues["warnings"])
            
            # Level progression validation
            progression_issues = self._validate_character_progression(character)
            result.warnings.extend(progression_issues["warnings"])
            result.suggestions.extend(progression_issues["suggestions"])
            
            # Equipment validation
            equipment_issues = self._validate_character_equipment(character)
            result.warnings.extend(equipment_issues["warnings"])
            
            # Balance validation
            balance_issues = self._validate_character_balance(character)
            result.warnings.extend(balance_issues["warnings"])
            result.suggestions.extend(balance_issues["suggestions"])
            
            # Calculate quality scores
            result.completeness_score = self._calculate_character_completeness(character)
            result.clarity_score = self._calculate_character_clarity(character)
            result.consistency_score = self._calculate_character_consistency(character)
            
            # Overall validation result
            if result.syntax_errors or result.semantic_errors:
                result.valid = False
            elif result.completeness_score < 0.7:
                result.valid = False
                result.suggestions.append("Character needs more complete information")
            
        except Exception as e:
            result.valid = False
            result.semantic_errors.append(f"Validation failed: {str(e)}")
        
        return result
    
    def validate_monster(self, monster: Monster) -> ValidationResult:
        """Validate a homebrew monster"""
        
        result = ValidationResult(
            valid=True,
            content_type="monster",
            content_id=monster.id,
            system=monster.system
        )
        
        try:
            # Basic structure validation
            structure_issues = self._validate_monster_structure(monster)
            result.syntax_errors.extend(structure_issues["errors"])
            result.warnings.extend(structure_issues["warnings"])
            
            # Stat block validation
            statblock_issues = self._validate_monster_statblock(monster)
            result.semantic_errors.extend(statblock_issues["errors"])
            result.warnings.extend(statblock_issues["warnings"])
            
            # Challenge rating validation
            cr_issues = self._validate_monster_challenge_rating(monster)
            result.warnings.extend(cr_issues["warnings"])
            result.suggestions.extend(cr_issues["suggestions"])
            
            # Ability validation
            ability_issues = self._validate_monster_abilities(monster)
            result.warnings.extend(ability_issues["warnings"])
            result.suggestions.extend(ability_issues["suggestions"])
            
            # Balance validation
            balance_issues = self._validate_monster_balance(monster)
            result.warnings.extend(balance_issues["warnings"])
            result.suggestions.extend(balance_issues["suggestions"])
            
            # Calculate quality scores
            result.completeness_score = self._calculate_monster_completeness(monster)
            result.clarity_score = self._calculate_monster_clarity(monster)
            result.consistency_score = self._calculate_monster_consistency(monster)
            
            # Overall validation result
            if result.syntax_errors or result.semantic_errors:
                result.valid = False
            elif result.completeness_score < 0.6:
                result.valid = False
                result.suggestions.append("Monster stat block needs more complete information")
            
        except Exception as e:
            result.valid = False
            result.semantic_errors.append(f"Monster validation failed: {str(e)}")
        
        return result
    
    def validate_spell(self, spell: Spell) -> ValidationResult:
        """Validate a homebrew spell"""
        
        result = ValidationResult(
            valid=True,
            content_type="spell",
            content_id=spell.id,
            system=spell.system
        )
        
        try:
            # Basic structure validation
            structure_issues = self._validate_spell_structure(spell)
            result.syntax_errors.extend(structure_issues["errors"])
            result.warnings.extend(structure_issues["warnings"])
            
            # Spell mechanics validation
            mechanics_issues = self._validate_spell_mechanics(spell)
            result.semantic_errors.extend(mechanics_issues["errors"])
            result.warnings.extend(mechanics_issues["warnings"])
            
            # Spell level validation
            level_issues = self._validate_spell_level(spell)
            result.warnings.extend(level_issues["warnings"])
            result.suggestions.extend(level_issues["suggestions"])
            
            # Balance validation
            balance_issues = self._validate_spell_balance(spell)
            result.warnings.extend(balance_issues["warnings"])
            result.suggestions.extend(balance_issues["suggestions"])
            
            # Calculate quality scores
            result.completeness_score = self._calculate_spell_completeness(spell)
            result.clarity_score = self._calculate_spell_clarity(spell)
            result.consistency_score = self._calculate_spell_consistency(spell)
            
            if result.syntax_errors or result.semantic_errors:
                result.valid = False
            elif result.completeness_score < 0.7:
                result.valid = False
                result.suggestions.append("Spell needs more complete description")
            
        except Exception as e:
            result.valid = False
            result.semantic_errors.append(f"Spell validation failed: {str(e)}")
        
        return result
    
    def validate_item(self, item: Item) -> ValidationResult:
        """Validate a homebrew item"""
        
        result = ValidationResult(
            valid=True,
            content_type="item",
            content_id=item.id,
            system=item.system
        )
        
        try:
            # Basic structure validation
            structure_issues = self._validate_item_structure(item)
            result.syntax_errors.extend(structure_issues["errors"])
            result.warnings.extend(structure_issues["warnings"])
            
            # Item mechanics validation
            mechanics_issues = self._validate_item_mechanics(item)
            result.semantic_errors.extend(mechanics_issues["errors"])
            result.warnings.extend(mechanics_issues["warnings"])
            
            # Rarity validation
            rarity_issues = self._validate_item_rarity(item)
            result.warnings.extend(rarity_issues["warnings"])
            result.suggestions.extend(rarity_issues["suggestions"])
            
            # Balance validation
            balance_issues = self._validate_item_balance(item)
            result.warnings.extend(balance_issues["warnings"])
            result.suggestions.extend(balance_issues["suggestions"])
            
            # Calculate quality scores
            result.completeness_score = self._calculate_item_completeness(item)
            result.clarity_score = self._calculate_item_clarity(item)
            result.consistency_score = self._calculate_item_consistency(item)
            
            if result.syntax_errors or result.semantic_errors:
                result.valid = False
            elif result.completeness_score < 0.6:
                result.valid = False
                result.suggestions.append("Item needs more complete description")
            
        except Exception as e:
            result.valid = False
            result.semantic_errors.append(f"Item validation failed: {str(e)}")
        
        return result
    
    def analyze_balance(self, content: Dict[str, Any], content_type: str) -> BalanceCheck:
        """Analyze balance of homebrew content"""
        
        balance_check = BalanceCheck(
            content_type=content_type,
            content_id=content.get("id", "unknown"),
            system=GameSystem(content.get("system", "dnd5e"))
        )
        
        try:
            if content_type == "character":
                character = Character(**content)
                balance_check = self._analyze_character_balance(character, balance_check)
            elif content_type == "monster":
                monster = Monster(**content)
                balance_check = self._analyze_monster_balance(monster, balance_check)
            elif content_type == "spell":
                spell = Spell(**content)
                balance_check = self._analyze_spell_balance(spell, balance_check)
            elif content_type == "item":
                item = Item(**content)
                balance_check = self._analyze_item_balance(item, balance_check)
            
        except Exception as e:
            balance_check.design_issues.append(f"Balance analysis failed: {str(e)}")
            balance_check.overall_rating = 3  # Default to middle rating on error
        
        return balance_check
    
    def _initialize_validation_rules(self):
        """Initialize validation rules for different content types"""
        
        self.validation_rules = {
            "character": {
                "required_fields": ["name", "system", "level", "attributes"],
                "numeric_fields": ["level", "hit_points"],
                "list_fields": ["skills", "proficiencies", "languages"],
                "dict_fields": ["attributes", "saving_throws"]
            },
            "monster": {
                "required_fields": ["name", "system", "hit_points", "armor_class", "challenge_rating"],
                "numeric_fields": ["hit_points", "armor_class", "challenge_rating"],
                "list_fields": ["actions", "special_abilities"],
                "dict_fields": ["attributes", "skills", "speed"]
            },
            "spell": {
                "required_fields": ["name", "system", "level", "school", "casting_time", "range", "duration"],
                "numeric_fields": ["level"],
                "list_fields": ["components", "classes"],
                "string_fields": ["school", "casting_time", "range", "duration", "description"]
            },
            "item": {
                "required_fields": ["name", "system", "item_type", "rarity"],
                "string_fields": ["item_type", "category", "rarity", "description"],
                "numeric_fields": ["weight"],
                "list_fields": ["properties"]
            }
        }
    
    def _initialize_balance_benchmarks(self):
        """Initialize balance benchmarks for different content types and levels"""
        
        self.balance_benchmarks = {
            GameSystem.D_AND_D_5E: {
                "character_hp_per_level": {1: 8, 5: 38, 10: 68, 15: 98, 20: 128},
                "character_ac_by_level": {1: 13, 5: 15, 10: 17, 15: 18, 20: 19},
                "monster_hp_by_cr": {
                    0.125: 7, 0.25: 9, 0.5: 22, 1: 71, 2: 142, 5: 325, 10: 615, 15: 885, 20: 1180
                },
                "monster_ac_by_cr": {
                    0.125: 12, 0.25: 12, 0.5: 13, 1: 13, 2: 13, 5: 15, 10: 17, 15: 18, 20: 19
                },
                "spell_damage_by_level": {
                    1: 10.5, 2: 16.5, 3: 24, 4: 31.5, 5: 39, 6: 46.5, 7: 54, 8: 61.5, 9: 69
                }
            }
        }
    
    def _initialize_system_requirements(self):
        """Initialize system-specific requirements"""
        
        self.system_requirements = {
            GameSystem.D_AND_D_5E: {
                "attribute_range": (1, 30),
                "level_range": (1, 20),
                "spell_level_range": (0, 9),
                "cr_range": (0, 30),
                "required_attributes": ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"],
                "valid_schools": ["abjuration", "conjuration", "divination", "enchantment", "evocation", "illusion", "necromancy", "transmutation"],
                "valid_rarities": ["common", "uncommon", "rare", "very rare", "legendary", "artifact"]
            },
            GameSystem.PATHFINDER_2E: {
                "attribute_range": (1, 30),
                "level_range": (1, 20),
                "spell_level_range": (0, 10),
                "cr_range": (-1, 25),
                "required_attributes": ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"],
                "valid_schools": ["abjuration", "conjuration", "divination", "enchantment", "evocation", "illusion", "necromancy", "transmutation"],
                "valid_rarities": ["common", "uncommon", "rare", "very rare", "unique", "artifact"]
            }
        }
    
    def _validate_character_structure(self, character: Character) -> Dict[str, List[str]]:
        """Validate character structure"""
        
        errors = []
        warnings = []
        
        rules = self.validation_rules["character"]
        
        # Check required fields
        for field in rules["required_fields"]:
            if not hasattr(character, field) or not getattr(character, field):
                errors.append(f"Missing required field: {field}")
        
        # Check numeric fields
        for field in rules["numeric_fields"]:
            if hasattr(character, field):
                value = getattr(character, field)
                if value is not None and not isinstance(value, (int, float)):
                    errors.append(f"Field {field} must be numeric")
                elif value is not None and value < 0:
                    warnings.append(f"Field {field} has negative value")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_character_attributes(self, character: Character) -> Dict[str, List[str]]:
        """Validate character attributes"""
        
        errors = []
        warnings = []
        
        if not character.attributes:
            errors.append("Character must have attributes")
            return {"errors": errors, "warnings": warnings}
        
        requirements = self.system_requirements.get(character.system, {})
        required_attrs = requirements.get("required_attributes", [])
        attr_range = requirements.get("attribute_range", (1, 30))
        
        # Check required attributes
        for attr in required_attrs:
            if attr not in character.attributes:
                errors.append(f"Missing required attribute: {attr}")
        
        # Check attribute values
        for attr, value in character.attributes.items():
            if not isinstance(value, int):
                errors.append(f"Attribute {attr} must be an integer")
            elif value < attr_range[0] or value > attr_range[1]:
                warnings.append(f"Attribute {attr} ({value}) outside normal range {attr_range}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_character_progression(self, character: Character) -> Dict[str, List[str]]:
        """Validate character level progression"""
        
        warnings = []
        suggestions = []
        
        level = character.level
        system_reqs = self.system_requirements.get(character.system, {})
        level_range = system_reqs.get("level_range", (1, 20))
        
        if level < level_range[0] or level > level_range[1]:
            warnings.append(f"Character level {level} outside normal range {level_range}")
        
        # Check HP progression
        if character.hit_points:
            hp = character.hit_points.get("max", 0)
            benchmarks = self.balance_benchmarks.get(character.system, {})
            hp_benchmarks = benchmarks.get("character_hp_per_level", {})
            
            expected_hp = self._interpolate_benchmark(hp_benchmarks, level)
            if expected_hp and hp < expected_hp * 0.5:
                warnings.append("Character HP significantly below expected for level")
            elif expected_hp and hp > expected_hp * 2:
                warnings.append("Character HP significantly above expected for level")
        
        return {"warnings": warnings, "suggestions": suggestions}
    
    def _validate_character_equipment(self, character: Character) -> Dict[str, List[str]]:
        """Validate character equipment"""
        
        warnings = []
        
        if character.level > 5 and not character.equipment:
            warnings.append("High-level character should have equipment")
        
        return {"warnings": warnings}
    
    def _validate_character_balance(self, character: Character) -> Dict[str, List[str]]:
        """Validate character balance"""
        
        warnings = []
        suggestions = []
        
        # Check AC progression
        if character.armor_class and character.level:
            benchmarks = self.balance_benchmarks.get(character.system, {})
            ac_benchmarks = benchmarks.get("character_ac_by_level", {})
            
            expected_ac = self._interpolate_benchmark(ac_benchmarks, character.level)
            if expected_ac and character.armor_class > expected_ac + 3:
                warnings.append("Character AC may be too high for level")
            elif expected_ac and character.armor_class < expected_ac - 3:
                suggestions.append("Consider increasing character AC for better survivability")
        
        return {"warnings": warnings, "suggestions": suggestions}
    
    def _validate_monster_structure(self, monster: Monster) -> Dict[str, List[str]]:
        """Validate monster structure"""
        
        errors = []
        warnings = []
        
        rules = self.validation_rules["monster"]
        
        # Check required fields
        for field in rules["required_fields"]:
            if not hasattr(monster, field) or getattr(monster, field) is None:
                errors.append(f"Missing required field: {field}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_monster_statblock(self, monster: Monster) -> Dict[str, List[str]]:
        """Validate monster stat block"""
        
        errors = []
        warnings = []
        
        # Check attributes
        if not monster.attributes:
            errors.append("Monster must have attributes")
        else:
            requirements = self.system_requirements.get(monster.system, {})
            required_attrs = requirements.get("required_attributes", [])
            
            for attr in required_attrs:
                if attr not in monster.attributes:
                    errors.append(f"Missing required attribute: {attr}")
        
        # Check basic stats
        if monster.hit_points <= 0:
            errors.append("Monster must have positive hit points")
        
        if monster.armor_class < 10:
            warnings.append("Very low AC may make encounters too easy")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_monster_challenge_rating(self, monster: Monster) -> Dict[str, List[str]]:
        """Validate monster challenge rating"""
        
        warnings = []
        suggestions = []
        
        cr = monster.challenge_rating
        system_reqs = self.system_requirements.get(monster.system, {})
        cr_range = system_reqs.get("cr_range", (0, 30))
        
        if cr < cr_range[0] or cr > cr_range[1]:
            warnings.append(f"Challenge rating {cr} outside normal range {cr_range}")
        
        # Check HP vs CR
        benchmarks = self.balance_benchmarks.get(monster.system, {})
        hp_benchmarks = benchmarks.get("monster_hp_by_cr", {})
        
        expected_hp = self._interpolate_benchmark(hp_benchmarks, cr)
        if expected_hp:
            hp_ratio = monster.hit_points / expected_hp
            if hp_ratio < 0.5:
                suggestions.append("Consider increasing HP or lowering CR")
            elif hp_ratio > 2.0:
                suggestions.append("Consider decreasing HP or raising CR")
        
        return {"warnings": warnings, "suggestions": suggestions}
    
    def _validate_monster_abilities(self, monster: Monster) -> Dict[str, List[str]]:
        """Validate monster abilities"""
        
        warnings = []
        suggestions = []
        
        total_abilities = (
            len(monster.special_abilities) + len(monster.actions) + 
            len(monster.bonus_actions) + len(monster.reactions) + 
            len(monster.legendary_actions)
        )
        
        if total_abilities == 0:
            warnings.append("Monster should have at least one special ability or action")
        elif total_abilities > 15:
            warnings.append("Monster may have too many abilities (complexity)")
        
        return {"warnings": warnings, "suggestions": suggestions}
    
    def _validate_monster_balance(self, monster: Monster) -> Dict[str, List[str]]:
        """Validate monster balance"""
        
        warnings = []
        suggestions = []
        
        # Check damage output
        action_damages = []
        for action in monster.actions:
            if "damage" in action:
                damage_str = action["damage"]
                avg_damage = self._parse_average_damage(damage_str)
                if avg_damage:
                    action_damages.append(avg_damage)
        
        if action_damages:
            max_damage = max(action_damages)
            expected_damage = self._get_expected_damage_by_cr(monster.challenge_rating, monster.system)
            
            if expected_damage and max_damage > expected_damage * 1.5:
                warnings.append("Monster damage output may be too high for CR")
            elif expected_damage and max_damage < expected_damage * 0.5:
                suggestions.append("Consider increasing damage output for CR")
        
        return {"warnings": warnings, "suggestions": suggestions}
    
    def _validate_spell_structure(self, spell: Spell) -> Dict[str, List[str]]:
        """Validate spell structure"""
        
        errors = []
        warnings = []
        
        rules = self.validation_rules["spell"]
        
        # Check required fields
        for field in rules["required_fields"]:
            if not hasattr(spell, field) or not getattr(spell, field):
                errors.append(f"Missing required field: {field}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_spell_mechanics(self, spell: Spell) -> Dict[str, List[str]]:
        """Validate spell mechanics"""
        
        errors = []
        warnings = []
        
        requirements = self.system_requirements.get(spell.system, {})
        
        # Check spell level
        level_range = requirements.get("spell_level_range", (0, 9))
        if spell.level < level_range[0] or spell.level > level_range[1]:
            errors.append(f"Spell level {spell.level} outside valid range {level_range}")
        
        # Check school
        valid_schools = requirements.get("valid_schools", [])
        if valid_schools and spell.school.lower() not in [s.lower() for s in valid_schools]:
            warnings.append(f"Unusual spell school: {spell.school}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_spell_level(self, spell: Spell) -> Dict[str, List[str]]:
        """Validate spell level appropriateness"""
        
        warnings = []
        suggestions = []
        
        # Check damage vs level
        if spell.damage:
            avg_damage = spell.damage.get("average", 0)
            benchmarks = self.balance_benchmarks.get(spell.system, {})
            damage_benchmarks = benchmarks.get("spell_damage_by_level", {})
            
            expected_damage = damage_benchmarks.get(spell.level, 0)
            if expected_damage and avg_damage > expected_damage * 1.3:
                warnings.append("Spell damage may be too high for level")
            elif expected_damage and avg_damage < expected_damage * 0.7:
                suggestions.append("Consider increasing damage or lowering spell level")
        
        return {"warnings": warnings, "suggestions": suggestions}
    
    def _validate_spell_balance(self, spell: Spell) -> Dict[str, List[str]]:
        """Validate spell balance"""
        
        warnings = []
        suggestions = []
        
        # Check for overpowered combinations
        if spell.concentration and spell.duration and "permanent" in spell.duration.lower():
            warnings.append("Permanent concentration spells can be problematic")
        
        if spell.level <= 2 and spell.damage and spell.damage.get("average", 0) > 20:
            warnings.append("High damage at low level may be unbalanced")
        
        return {"warnings": warnings, "suggestions": suggestions}
    
    def _validate_item_structure(self, item: Item) -> Dict[str, List[str]]:
        """Validate item structure"""
        
        errors = []
        warnings = []
        
        rules = self.validation_rules["item"]
        
        # Check required fields
        for field in rules["required_fields"]:
            if not hasattr(item, field) or not getattr(item, field):
                errors.append(f"Missing required field: {field}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_item_mechanics(self, item: Item) -> Dict[str, List[str]]:
        """Validate item mechanics"""
        
        errors = []
        warnings = []
        
        requirements = self.system_requirements.get(item.system, {})
        
        # Check rarity
        valid_rarities = requirements.get("valid_rarities", [])
        if valid_rarities and item.rarity.lower() not in [r.lower() for r in valid_rarities]:
            warnings.append(f"Unusual item rarity: {item.rarity}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_item_rarity(self, item: Item) -> Dict[str, List[str]]:
        """Validate item rarity appropriateness"""
        
        warnings = []
        suggestions = []
        
        # Check if rarity matches power level
        power_indicators = 0
        
        if item.magic:
            power_indicators += 1
        
        if item.attack_bonus and item.attack_bonus > 0:
            power_indicators += item.attack_bonus
        
        if item.armor_class and item.armor_class > 15:
            power_indicators += 1
        
        if item.charges and item.charges > 3:
            power_indicators += 1
        
        rarity_power = {
            "common": 0, "uncommon": 2, "rare": 4, 
            "very rare": 6, "legendary": 8, "artifact": 10
        }
        
        expected_power = rarity_power.get(item.rarity.lower(), 2)
        
        if power_indicators > expected_power + 2:
            warnings.append("Item may be too powerful for its rarity")
        elif power_indicators < expected_power - 1 and expected_power > 0:
            suggestions.append("Consider lowering rarity or adding more abilities")
        
        return {"warnings": warnings, "suggestions": suggestions}
    
    def _validate_item_balance(self, item: Item) -> Dict[str, List[str]]:
        """Validate item balance"""
        
        warnings = []
        suggestions = []
        
        # Check for overpowered combinations
        if item.attack_bonus and item.attack_bonus >= 3 and item.damage:
            warnings.append("High attack bonus with extra damage may be overpowered")
        
        if item.armor_class and item.armor_class >= 20:
            warnings.append("Very high AC items can break game balance")
        
        return {"warnings": warnings, "suggestions": suggestions}
    
    # Quality score calculation methods
    def _calculate_character_completeness(self, character: Character) -> float:
        """Calculate character completeness score"""
        
        score = 0.0
        max_score = 0.0
        
        # Required fields
        required_fields = ["name", "system", "level", "attributes"]
        for field in required_fields:
            max_score += 1.0
            if hasattr(character, field) and getattr(character, field):
                score += 1.0
        
        # Optional but recommended fields
        optional_fields = ["race", "character_class", "background", "skills", "equipment"]
        for field in optional_fields:
            max_score += 0.5
            if hasattr(character, field) and getattr(character, field):
                score += 0.5
        
        return score / max_score if max_score > 0 else 0.0
    
    def _calculate_character_clarity(self, character: Character) -> float:
        """Calculate character clarity score"""
        
        # This would analyze naming consistency, description quality, etc.
        return 0.8  # Placeholder
    
    def _calculate_character_consistency(self, character: Character) -> float:
        """Calculate character consistency score"""
        
        # This would check for logical consistency in stats, abilities, etc.
        return 0.8  # Placeholder
    
    def _calculate_monster_completeness(self, monster: Monster) -> float:
        """Calculate monster completeness score"""
        
        score = 0.0
        max_score = 8.0  # Total possible points
        
        required = ["name", "hit_points", "armor_class", "challenge_rating", "attributes"]
        for field in required:
            if hasattr(monster, field) and getattr(monster, field) is not None:
                score += 1.0
        
        if monster.actions:
            score += 1.0
        
        if monster.special_abilities or monster.reactions or monster.legendary_actions:
            score += 1.0
        
        if monster.languages or monster.senses:
            score += 1.0
        
        return score / max_score
    
    def _calculate_monster_clarity(self, monster: Monster) -> float:
        """Calculate monster clarity score"""
        
        return 0.8  # Placeholder
    
    def _calculate_monster_consistency(self, monster: Monster) -> float:
        """Calculate monster consistency score"""
        
        return 0.8  # Placeholder
    
    def _calculate_spell_completeness(self, spell: Spell) -> float:
        """Calculate spell completeness score"""
        
        score = 0.0
        max_score = 7.0
        
        required = ["name", "level", "school", "casting_time", "range", "duration", "description"]
        for field in required:
            if hasattr(spell, field) and getattr(spell, field):
                score += 1.0
        
        return score / max_score
    
    def _calculate_spell_clarity(self, spell: Spell) -> float:
        """Calculate spell clarity score"""
        
        return 0.8  # Placeholder
    
    def _calculate_spell_consistency(self, spell: Spell) -> float:
        """Calculate spell consistency score"""
        
        return 0.8  # Placeholder
    
    def _calculate_item_completeness(self, item: Item) -> float:
        """Calculate item completeness score"""
        
        score = 0.0
        max_score = 5.0
        
        required = ["name", "item_type", "rarity", "description"]
        for field in required:
            if hasattr(item, field) and getattr(item, field):
                score += 1.0
        
        if item.cost:
            score += 1.0
        
        return score / max_score
    
    def _calculate_item_clarity(self, item: Item) -> float:
        """Calculate item clarity score"""
        
        return 0.8  # Placeholder
    
    def _calculate_item_consistency(self, item: Item) -> float:
        """Calculate item consistency score"""
        
        return 0.8  # Placeholder
    
    # Helper methods
    def _interpolate_benchmark(self, benchmarks: Dict[float, float], target: float) -> Optional[float]:
        """Interpolate benchmark value for a given target"""
        
        if not benchmarks:
            return None
        
        keys = sorted(benchmarks.keys())
        
        if target <= keys[0]:
            return benchmarks[keys[0]]
        if target >= keys[-1]:
            return benchmarks[keys[-1]]
        
        # Find surrounding values
        for i in range(len(keys) - 1):
            if keys[i] <= target <= keys[i + 1]:
                lower_key, upper_key = keys[i], keys[i + 1]
                lower_val, upper_val = benchmarks[lower_key], benchmarks[upper_key]
                
                # Linear interpolation
                ratio = (target - lower_key) / (upper_key - lower_key)
                return lower_val + ratio * (upper_val - lower_val)
        
        return None
    
    def _parse_average_damage(self, damage_str: str) -> Optional[float]:
        """Parse average damage from dice notation"""
        
        if not damage_str:
            return None
        
        # Look for explicit average damage
        if "(" in damage_str and ")" in damage_str:
            match = re.search(r'\((\d+(?:\.\d+)?)\)', damage_str)
            if match:
                return float(match.group(1))
        
        # Parse dice notation
        dice_match = re.search(r'(\d+)d(\d+)([+-]\d+)?', damage_str)
        if dice_match:
            num_dice = int(dice_match.group(1))
            die_size = int(dice_match.group(2))
            modifier = int(dice_match.group(3)) if dice_match.group(3) else 0
            
            return num_dice * (die_size + 1) / 2 + modifier
        
        return None
    
    def _get_expected_damage_by_cr(self, cr: float, system: GameSystem) -> Optional[float]:
        """Get expected damage output for a CR"""
        
        # This would use more sophisticated damage calculations
        # For now, simple approximation
        if cr <= 0.5:
            return 3.5
        elif cr <= 1:
            return 7
        elif cr <= 5:
            return cr * 7
        else:
            return cr * 8.5
    
    # Balance analysis methods
    def _analyze_character_balance(self, character: Character, balance_check: BalanceCheck) -> BalanceCheck:
        """Analyze character balance"""
        
        balance_check.content_type = "character"
        balance_check.overall_rating = 5  # Start neutral
        
        # Analyze power level relative to level
        if character.level and character.attributes:
            avg_stat = sum(character.attributes.values()) / len(character.attributes)
            expected_avg = 13 + (character.level - 1) * 0.5
            
            if avg_stat > expected_avg + 3:
                balance_check.overpowered_aspects.append("Attributes significantly above average")
                balance_check.overall_rating += 1
            elif avg_stat < expected_avg - 3:
                balance_check.underpowered_aspects.append("Attributes significantly below average")
                balance_check.overall_rating -= 1
        
        return balance_check
    
    def _analyze_monster_balance(self, monster: Monster, balance_check: BalanceCheck) -> BalanceCheck:
        """Analyze monster balance"""
        
        balance_check.content_type = "monster"
        balance_check.overall_rating = 5
        
        # Analyze HP vs CR
        benchmarks = self.balance_benchmarks.get(monster.system, {})
        hp_benchmarks = benchmarks.get("monster_hp_by_cr", {})
        
        expected_hp = self._interpolate_benchmark(hp_benchmarks, monster.challenge_rating)
        if expected_hp:
            hp_ratio = monster.hit_points / expected_hp
            if hp_ratio > 1.5:
                balance_check.overpowered_aspects.append("HP significantly above expected")
                balance_check.overall_rating += 1
            elif hp_ratio < 0.5:
                balance_check.underpowered_aspects.append("HP significantly below expected")
                balance_check.overall_rating -= 1
        
        return balance_check
    
    def _analyze_spell_balance(self, spell: Spell, balance_check: BalanceCheck) -> BalanceCheck:
        """Analyze spell balance"""
        
        balance_check.content_type = "spell"
        balance_check.overall_rating = 5
        
        # Analyze damage vs level
        if spell.damage and spell.level > 0:
            avg_damage = spell.damage.get("average", 0)
            benchmarks = self.balance_benchmarks.get(spell.system, {})
            damage_benchmarks = benchmarks.get("spell_damage_by_level", {})
            
            expected_damage = damage_benchmarks.get(spell.level, 0)
            if expected_damage and avg_damage > expected_damage * 1.3:
                balance_check.overpowered_aspects.append("Damage significantly above expected")
                balance_check.overall_rating += 2
            elif expected_damage and avg_damage < expected_damage * 0.7:
                balance_check.underpowered_aspects.append("Damage significantly below expected")
                balance_check.overall_rating -= 1
        
        return balance_check
    
    def _analyze_item_balance(self, item: Item, balance_check: BalanceCheck) -> BalanceCheck:
        """Analyze item balance"""
        
        balance_check.content_type = "item"
        balance_check.overall_rating = 5
        
        # Simple power level assessment
        power_score = 0
        
        if item.magic:
            power_score += 1
        
        if item.attack_bonus:
            power_score += item.attack_bonus
        
        if item.armor_class and item.armor_class > 15:
            power_score += item.armor_class - 15
        
        # Compare to rarity expectations
        rarity_power = {"common": 0, "uncommon": 2, "rare": 4, "very rare": 6, "legendary": 8}
        expected_power = rarity_power.get(item.rarity.lower(), 2)
        
        if power_score > expected_power + 3:
            balance_check.overpowered_aspects.append("Power level significantly above rarity")
            balance_check.overall_rating += 2
        elif power_score < expected_power - 2:
            balance_check.underpowered_aspects.append("Power level significantly below rarity")
            balance_check.overall_rating -= 1
        
        return balance_check