"""
D&D 5th Edition game system implementation for DMLog.ai.
Implements the core mechanics of D&D 5e including skills, saves, combat, and spellcasting.
"""

from typing import Dict, List, Optional, Tuple, Any
import logging

from ..core.types import (
    AttributeType, SkillType, DiceType, DiceRoll, RollResult,
    GameSystemInterface, CharacterInterface, DamageType, ConditionType
)
from ..core.dice import DiceRoller, default_roller
from ..core.character import BaseCharacter, Skill, CharacterClass, Race, Background

logger = logging.getLogger(__name__)


class DnD5eSystem(GameSystemInterface):
    """D&D 5th Edition game system implementation."""
    
    # D&D 5e ability scores
    ATTRIBUTES = [
        AttributeType.STRENGTH,
        AttributeType.DEXTERITY, 
        AttributeType.CONSTITUTION,
        AttributeType.INTELLIGENCE,
        AttributeType.WISDOM,
        AttributeType.CHARISMA
    ]
    
    # D&D 5e skills and their associated abilities
    SKILLS = {
        SkillType.ATHLETICS: AttributeType.STRENGTH,
        SkillType.DECEPTION: AttributeType.CHARISMA,
        SkillType.HISTORY: AttributeType.INTELLIGENCE,
        SkillType.INSIGHT: AttributeType.WISDOM,
        SkillType.INVESTIGATION: AttributeType.INTELLIGENCE,
        SkillType.MEDICINE: AttributeType.WISDOM,
        SkillType.PERCEPTION: AttributeType.WISDOM,
        SkillType.PERSUASION: AttributeType.CHARISMA,
        SkillType.STEALTH: AttributeType.DEXTERITY,
        SkillType.SURVIVAL: AttributeType.WISDOM
    }
    
    # Difficulty classes for various tasks
    DIFFICULTY_CLASSES = {
        "very_easy": 5,
        "easy": 10,
        "medium": 15,
        "hard": 20,
        "very_hard": 25,
        "nearly_impossible": 30
    }
    
    # Proficiency bonus by level
    PROFICIENCY_BONUS = {
        1: 2, 2: 2, 3: 2, 4: 2,
        5: 3, 6: 3, 7: 3, 8: 3,
        9: 4, 10: 4, 11: 4, 12: 4,
        13: 5, 14: 5, 15: 5, 16: 5,
        17: 6, 18: 6, 19: 6, 20: 6
    }
    
    def __init__(self, dice_roller: Optional[DiceRoller] = None):
        self.dice_roller = dice_roller or default_roller
    
    @property
    def name(self) -> str:
        return "Dungeons & Dragons 5th Edition"
    
    @property
    def version(self) -> str:
        return "5.0"
    
    @property
    def supported_attributes(self) -> List[AttributeType]:
        return self.ATTRIBUTES.copy()
    
    @property
    def supported_skills(self) -> List[SkillType]:
        return list(self.SKILLS.keys())
    
    def calculate_attribute_modifier(self, score: int) -> int:
        """Calculate D&D 5e ability modifier: (score - 10) / 2 rounded down."""
        return (score - 10) // 2
    
    def calculate_skill_bonus(self, skill: Skill, character: CharacterInterface) -> int:
        """Calculate total skill bonus for D&D 5e."""
        attribute_mod = self.calculate_attribute_modifier(
            character.get_attribute_score(skill.attribute)
        )
        
        bonus = attribute_mod + skill.custom_bonus
        
        if skill.proficient:
            proficiency = self.PROFICIENCY_BONUS.get(character.level, 2)
            if skill.expertise:
                bonus += proficiency * 2
            else:
                bonus += proficiency
        
        return bonus
    
    def roll_skill_check(self, skill: Skill, character: CharacterInterface, 
                        difficulty_class: Optional[int] = None,
                        advantage: bool = False, disadvantage: bool = False) -> RollResult:
        """Roll a D&D 5e skill check."""
        skill_bonus = self.calculate_skill_bonus(skill, character)
        
        # Check for conditions that affect rolls
        conditions = character.conditions
        for condition in conditions:
            if condition.type == ConditionType.POISONED:
                disadvantage = True
            elif condition.type in [ConditionType.STUNNED, ConditionType.PARALYZED, 
                                  ConditionType.UNCONSCIOUS]:
                # These conditions prevent skill checks in most cases
                logger.warning(f"{character.name} cannot make skill checks while {condition.type.value}")
                return self._create_failed_roll()
        
        dice_roll = DiceRoll(
            dice_count=1,
            dice_type=DiceType.D20,
            modifier=skill_bonus,
            advantage=advantage,
            disadvantage=disadvantage
        )
        
        result = self.dice_roller.roll(dice_roll)
        
        # Determine success if DC provided
        if difficulty_class is not None:
            result.success = result.total >= difficulty_class
        
        logger.info(f"{character.name} rolled {skill.name}: {result.total} "
                   f"(nat {result.individual_rolls[0]}{'+' if skill_bonus >= 0 else ''}{skill_bonus})")
        
        return result
    
    def roll_saving_throw(self, attribute: AttributeType, character: CharacterInterface,
                         difficulty_class: int, advantage: bool = False, 
                         disadvantage: bool = False) -> RollResult:
        """Roll a D&D 5e saving throw."""
        attribute_mod = self.calculate_attribute_modifier(
            character.get_attribute_score(attribute)
        )
        
        # Check for proficiency in saving throws
        proficiency_bonus = 0
        if hasattr(character, 'character_class') and character.character_class:
            if attribute in character.character_class.saving_throws:
                proficiency_bonus = self.PROFICIENCY_BONUS.get(character.level, 2)
        
        total_bonus = attribute_mod + proficiency_bonus
        
        # Check for conditions
        conditions = character.conditions
        for condition in conditions:
            if condition.type == ConditionType.POISONED:
                disadvantage = True
            elif condition.type in [ConditionType.STUNNED, ConditionType.PARALYZED, 
                                  ConditionType.UNCONSCIOUS, ConditionType.INCAPACITATED]:
                # These conditions prevent saving throws or impose disadvantage
                if attribute in [AttributeType.STRENGTH, AttributeType.DEXTERITY]:
                    return self._create_failed_roll()
        
        dice_roll = DiceRoll(
            dice_count=1,
            dice_type=DiceType.D20,
            modifier=total_bonus,
            advantage=advantage,
            disadvantage=disadvantage
        )
        
        result = self.dice_roller.roll(dice_roll)
        result.success = result.total >= difficulty_class
        
        logger.info(f"{character.name} {attribute.value} save: {result.total} vs DC {difficulty_class} "
                   f"({'SUCCESS' if result.success else 'FAILURE'})")
        
        return result
    
    def calculate_armor_class(self, character: CharacterInterface) -> int:
        """Calculate D&D 5e armor class."""
        if hasattr(character, 'calculate_armor_class'):
            return character.calculate_armor_class()
        
        # Fallback calculation
        base_ac = 10
        dex_mod = self.calculate_attribute_modifier(
            character.get_attribute_score(AttributeType.DEXTERITY)
        )
        return base_ac + dex_mod
    
    def calculate_hit_points(self, character: CharacterInterface) -> int:
        """Calculate D&D 5e maximum hit points."""
        if not hasattr(character, 'character_class') or not character.character_class:
            return 8  # Default
        
        con_mod = self.calculate_attribute_modifier(
            character.get_attribute_score(AttributeType.CONSTITUTION)
        )
        
        # First level: max hit die + con mod
        # Subsequent levels: average of hit die + con mod
        hit_die = character.character_class.hit_die
        base_hp = hit_die + con_mod
        
        if character.level > 1:
            avg_per_level = (hit_die // 2) + 1 + con_mod
            avg_per_level = max(1, avg_per_level)  # Minimum 1 per level
            base_hp += (character.level - 1) * avg_per_level
        
        return max(1, base_hp)  # Minimum 1 HP total
    
    def roll_attack(self, character: CharacterInterface, weapon_name: str,
                   target_ac: int, advantage: bool = False, disadvantage: bool = False) -> Tuple[RollResult, bool]:
        """Roll an attack roll for D&D 5e."""
        # Get weapon from equipment
        weapon = None
        if hasattr(character, 'equipment'):
            for item in character.equipment:
                if item.name == weapon_name and item.equipped:
                    weapon = item
                    break
        
        if not weapon:
            raise ValueError(f"Weapon {weapon_name} not found or not equipped")
        
        # Determine attack attribute (STR for melee, DEX for ranged, finesse allows choice)
        attack_attr = AttributeType.STRENGTH
        if weapon.properties.get("ranged"):
            attack_attr = AttributeType.DEXTERITY
        elif weapon.properties.get("finesse"):
            # Choose higher of STR or DEX
            str_mod = self.calculate_attribute_modifier(
                character.get_attribute_score(AttributeType.STRENGTH)
            )
            dex_mod = self.calculate_attribute_modifier(
                character.get_attribute_score(AttributeType.DEXTERITY)
            )
            attack_attr = AttributeType.DEXTERITY if dex_mod > str_mod else AttributeType.STRENGTH
        
        attack_mod = self.calculate_attribute_modifier(
            character.get_attribute_score(attack_attr)
        )
        
        # Add proficiency if proficient with weapon
        proficiency_bonus = 0
        if weapon.properties.get("proficient", True):  # Assume proficient by default
            proficiency_bonus = self.PROFICIENCY_BONUS.get(character.level, 2)
        
        # Add weapon's magic bonus if any
        magic_bonus = weapon.properties.get("attack_bonus", 0)
        
        total_bonus = attack_mod + proficiency_bonus + magic_bonus
        
        dice_roll = DiceRoll(
            dice_count=1,
            dice_type=DiceType.D20,
            modifier=total_bonus,
            advantage=advantage,
            disadvantage=disadvantage
        )
        
        result = self.dice_roller.roll(dice_roll)
        hit = result.total >= target_ac
        
        logger.info(f"{character.name} attacks with {weapon_name}: {result.total} vs AC {target_ac} "
                   f"({'HIT' if hit else 'MISS'})")
        
        return result, hit
    
    def roll_damage(self, character: CharacterInterface, weapon_name: str,
                   critical: bool = False) -> RollResult:
        """Roll weapon damage for D&D 5e."""
        # Get weapon from equipment
        weapon = None
        if hasattr(character, 'equipment'):
            for item in character.equipment:
                if item.name == weapon_name and item.equipped:
                    weapon = item
                    break
        
        if not weapon:
            raise ValueError(f"Weapon {weapon_name} not found or not equipped")
        
        # Get damage dice from weapon properties
        damage_dice = weapon.properties.get("damage_dice", "1d4")
        damage_type = weapon.properties.get("damage_type", "bludgeoning")
        
        # Parse damage dice (simplified - assumes format like "1d8" or "2d6")
        parts = damage_dice.split('d')
        dice_count = int(parts[0])
        dice_sides = int(parts[1])
        
        # Map dice sides to DiceType
        dice_type_map = {4: DiceType.D4, 6: DiceType.D6, 8: DiceType.D8, 
                        10: DiceType.D10, 12: DiceType.D12, 20: DiceType.D20}
        dice_type = dice_type_map.get(dice_sides, DiceType.D6)
        
        # Critical hits double the dice
        if critical:
            dice_count *= 2
        
        # Determine damage attribute
        damage_attr = AttributeType.STRENGTH
        if weapon.properties.get("ranged"):
            damage_attr = AttributeType.DEXTERITY
        elif weapon.properties.get("finesse"):
            str_mod = self.calculate_attribute_modifier(
                character.get_attribute_score(AttributeType.STRENGTH)
            )
            dex_mod = self.calculate_attribute_modifier(
                character.get_attribute_score(AttributeType.DEXTERITY)
            )
            damage_attr = AttributeType.DEXTERITY if dex_mod > str_mod else AttributeType.STRENGTH
        
        damage_mod = self.calculate_attribute_modifier(
            character.get_attribute_score(damage_attr)
        )
        
        # Add weapon's magic damage bonus
        magic_bonus = weapon.properties.get("damage_bonus", 0)
        total_modifier = damage_mod + magic_bonus
        
        dice_roll = DiceRoll(
            dice_count=dice_count,
            dice_type=dice_type,
            modifier=total_modifier
        )
        
        result = self.dice_roller.roll(dice_roll)
        
        crit_text = " (CRITICAL)" if critical else ""
        logger.info(f"{character.name} deals {result.total} {damage_type} damage{crit_text}")
        
        return result
    
    def _create_failed_roll(self) -> RollResult:
        """Create a failed roll result for impossible rolls."""
        dice_roll = DiceRoll(1, DiceType.D20)
        return RollResult(
            roll=dice_roll,
            individual_rolls=[1],
            total=1,
            success=False
        )
    
    def create_character(self, name: str, race_name: str = "human", 
                        class_name: str = "fighter") -> 'DnD5eCharacter':
        """Create a new D&D 5e character with race and class."""
        character = DnD5eCharacter(name)
        
        # Set race
        race = self.get_race(race_name)
        if race:
            character.set_race(race)
        
        # Set class
        char_class = self.get_character_class(class_name)
        if char_class:
            character.set_character_class(char_class)
        
        # Initialize attributes with standard array
        standard_array = [15, 14, 13, 12, 10, 8]
        for i, attr in enumerate(self.ATTRIBUTES):
            if i < len(standard_array):
                character.add_attribute(attr, standard_array[i])
            else:
                character.add_attribute(attr, 10)
        
        # Initialize skills
        for skill_type, attribute in self.SKILLS.items():
            character.add_skill(skill_type, attribute)
        
        return character
    
    def get_race(self, name: str) -> Optional[Race]:
        """Get race definition by name."""
        races = {
            "human": Race(
                name="Human",
                size="Medium",
                speed=30,
                attribute_bonuses={attr: 1 for attr in self.ATTRIBUTES},
                languages=["Common"],
                racial_traits=["Versatile", "Extra Language", "Extra Skill"]
            ),
            "elf": Race(
                name="Elf", 
                size="Medium",
                speed=30,
                attribute_bonuses={AttributeType.DEXTERITY: 2},
                languages=["Common", "Elvish"],
                racial_traits=["Darkvision", "Keen Senses", "Fey Ancestry", "Trance"],
                skill_bonuses={SkillType.PERCEPTION: 2}
            ),
            "dwarf": Race(
                name="Dwarf",
                size="Medium", 
                speed=25,
                attribute_bonuses={AttributeType.CONSTITUTION: 2},
                languages=["Common", "Dwarvish"],
                racial_traits=["Darkvision", "Dwarven Resilience", "Stonecunning"]
            ),
            "halfling": Race(
                name="Halfling",
                size="Small",
                speed=25,
                attribute_bonuses={AttributeType.DEXTERITY: 2},
                languages=["Common", "Halfling"],
                racial_traits=["Lucky", "Brave", "Halfling Nimbleness"]
            )
        }
        return races.get(name.lower())
    
    def get_character_class(self, name: str) -> Optional[CharacterClass]:
        """Get character class definition by name."""
        classes = {
            "fighter": CharacterClass(
                name="Fighter",
                hit_die=10,
                primary_attributes=[AttributeType.STRENGTH, AttributeType.DEXTERITY],
                class_skills=[SkillType.ATHLETICS, SkillType.SURVIVAL],
                saving_throws=[AttributeType.STRENGTH, AttributeType.CONSTITUTION],
                proficiencies={
                    "armor": ["light", "medium", "heavy", "shields"],
                    "weapons": ["simple", "martial"],
                    "tools": []
                },
                class_features=["Fighting Style", "Second Wind", "Action Surge"],
                spell_casting=False
            ),
            "wizard": CharacterClass(
                name="Wizard",
                hit_die=6,
                primary_attributes=[AttributeType.INTELLIGENCE],
                class_skills=[SkillType.HISTORY, SkillType.INVESTIGATION],
                saving_throws=[AttributeType.INTELLIGENCE, AttributeType.WISDOM],
                proficiencies={
                    "armor": [],
                    "weapons": ["simple"],
                    "tools": []
                },
                class_features=["Spellcasting", "Arcane Recovery", "Spell Mastery"],
                spell_casting=True,
                spell_attribute=AttributeType.INTELLIGENCE,
                spell_slots_per_level={
                    1: [2], 2: [3], 3: [4, 2], 4: [4, 3], 5: [4, 3, 2],
                    # ... continued for all levels
                }
            ),
            "rogue": CharacterClass(
                name="Rogue",
                hit_die=8,
                primary_attributes=[AttributeType.DEXTERITY],
                class_skills=[SkillType.STEALTH, SkillType.PERCEPTION, 
                             SkillType.DECEPTION, SkillType.INSIGHT],
                saving_throws=[AttributeType.DEXTERITY, AttributeType.INTELLIGENCE],
                proficiencies={
                    "armor": ["light"],
                    "weapons": ["simple", "hand crossbows", "longswords", "rapiers", "shortswords"],
                    "tools": ["thieves' tools"]
                },
                class_features=["Expertise", "Sneak Attack", "Cunning Action"],
                spell_casting=False
            )
        }
        return classes.get(name.lower())


class DnD5eCharacter(BaseCharacter):
    """D&D 5e specific character implementation."""
    
    def __init__(self, name: str):
        super().__init__(name, "dnd5e")
        self.system = DnD5eSystem()
        
        # D&D 5e specific attributes
        self.inspiration = False
        self.passive_perception = 10
        
        # Combat specific
        self.death_save_successes = 0
        self.death_save_failures = 0
        self.hit_dice_remaining = 1  # Hit dice for short rests
    
    def set_race(self, race: Race) -> None:
        """Set character race and apply bonuses."""
        self.race = race
        
        # Apply racial attribute bonuses
        for attr_type, bonus in race.attribute_bonuses.items():
            if attr_type in self._attributes:
                self._attributes[attr_type].score += bonus
            else:
                self.add_attribute(attr_type, 10 + bonus)
        
        self.updated_at = datetime.now()
    
    def set_character_class(self, char_class: CharacterClass) -> None:
        """Set character class and apply features."""
        self.character_class = char_class
        self.hit_dice_remaining = self.level
        
        # Set hit points based on class
        con_mod = self.get_attribute_modifier(AttributeType.CONSTITUTION)
        self.hit_points.maximum = char_class.hit_die + con_mod
        self.hit_points.current = self.hit_points.maximum
        
        # Add spell slots if spellcaster
        if char_class.spell_casting and char_class.spell_slots_per_level:
            slots_for_level = char_class.spell_slots_per_level.get(self.level, [])
            for spell_level, slot_count in enumerate(slots_for_level, 1):
                if slot_count > 0:
                    self.add_spell_slot(spell_level, slot_count)
        
        self.updated_at = datetime.now()
    
    def calculate_passive_perception(self) -> int:
        """Calculate passive Perception score."""
        perception_bonus = self.get_skill_bonus(SkillType.PERCEPTION)
        return 10 + perception_bonus
    
    def roll_death_saving_throw(self) -> RollResult:
        """Roll a death saving throw."""
        dice_roll = DiceRoll(1, DiceType.D20)
        result = self.system.dice_roller.roll(dice_roll)
        
        if result.individual_rolls[0] == 20:
            # Natural 20: regain 1 HP
            self.hit_points.current = 1
            self.death_save_successes = 0
            self.death_save_failures = 0
            result.success = True
            logger.info(f"{self.name} rolled natural 20 on death save - back to 1 HP!")
        elif result.individual_rolls[0] == 1:
            # Natural 1: two failures
            self.death_save_failures += 2
            result.success = False
            logger.info(f"{self.name} rolled natural 1 on death save - 2 failures!")
        elif result.total >= 10:
            # Success
            self.death_save_successes += 1
            result.success = True
            logger.info(f"{self.name} succeeded death save ({self.death_save_successes}/3)")
        else:
            # Failure
            self.death_save_failures += 1
            result.success = False
            logger.info(f"{self.name} failed death save ({self.death_save_failures}/3)")
        
        # Check for stabilization or death
        if self.death_save_successes >= 3:
            # Stabilized
            self.death_save_successes = 0
            self.death_save_failures = 0
            logger.info(f"{self.name} has stabilized!")
        elif self.death_save_failures >= 3:
            # Dead
            logger.warning(f"{self.name} has died!")
        
        self.updated_at = datetime.now()
        return result