"""
Skill and ability check system for the DMLog.ai RPG engine.
Provides unified interface for rolling various types of checks across different RPG systems.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any, Callable
from enum import Enum
import logging

from .types import (
    AttributeType, SkillType, DiceRoll, RollResult, 
    CharacterInterface, ConditionType, RPGEngineError
)
from .dice import DiceRoller, default_roller

logger = logging.getLogger(__name__)


class CheckType(Enum):
    """Types of checks that can be made."""
    SKILL_CHECK = "skill_check"
    ABILITY_CHECK = "ability_check"
    SAVING_THROW = "saving_throw"
    ATTACK_ROLL = "attack_roll"
    CONTEST = "contest"
    GROUP_CHECK = "group_check"


class CheckDifficulty(Enum):
    """Standard difficulty levels for checks."""
    TRIVIAL = 5
    EASY = 10
    MEDIUM = 15
    HARD = 20
    VERY_HARD = 25
    LEGENDARY = 30


@dataclass
class CheckModifier:
    """Represents a modifier that can be applied to a check."""
    name: str
    value: int
    source: str
    description: Optional[str] = None


@dataclass
class CheckContext:
    """Context information for a check."""
    check_type: CheckType
    difficulty_class: Optional[int] = None
    advantage: bool = False
    disadvantage: bool = False
    modifiers: List[CheckModifier] = field(default_factory=list)
    description: str = ""
    situational_factors: Dict[str, Any] = field(default_factory=dict)
    
    def add_modifier(self, modifier: CheckModifier) -> None:
        """Add a modifier to this check."""
        self.modifiers.append(modifier)
    
    def get_total_modifier(self) -> int:
        """Calculate total modifier from all modifiers."""
        return sum(mod.value for mod in self.modifiers)
    
    def has_advantage(self) -> bool:
        """Check if this check has advantage (accounting for disadvantage cancellation)."""
        return self.advantage and not self.disadvantage
    
    def has_disadvantage(self) -> bool:
        """Check if this check has disadvantage (accounting for advantage cancellation)."""
        return self.disadvantage and not self.advantage


@dataclass
class CheckResult:
    """Result of a check with additional context."""
    roll_result: RollResult
    context: CheckContext
    character: CharacterInterface
    success: bool
    degree_of_success: Optional[str] = None  # "critical_success", "success", "failure", "critical_failure"
    additional_effects: List[str] = field(default_factory=list)
    
    @property
    def natural_roll(self) -> int:
        """Get the natural die roll (before modifiers)."""
        if self.roll_result.individual_rolls:
            return self.roll_result.individual_rolls[0]
        return 0
    
    @property
    def total(self) -> int:
        """Get the total result including all modifiers."""
        return self.roll_result.total
    
    @property
    def was_critical(self) -> bool:
        """Check if this was a critical result."""
        return self.roll_result.critical or False
    
    @property
    def was_fumble(self) -> bool:
        """Check if this was a fumble/critical failure."""
        return self.roll_result.fumble or False


class CheckEngine:
    """Engine for handling various types of checks."""
    
    def __init__(self, dice_roller: Optional[DiceRoller] = None):
        self.dice_roller = dice_roller or default_roller
        self.check_modifiers: Dict[str, List[Callable]] = {}
        self.condition_effects: Dict[ConditionType, Dict[str, Any]] = {}
        
        # Register default condition effects
        self._register_default_condition_effects()
    
    def make_skill_check(self, character: CharacterInterface, skill: SkillType,
                        difficulty_class: Optional[int] = None,
                        context: Optional[CheckContext] = None) -> CheckResult:
        """Make a skill check for a character."""
        if context is None:
            context = CheckContext(
                check_type=CheckType.SKILL_CHECK,
                difficulty_class=difficulty_class
            )
        
        # Get skill information
        skills = character.skills
        if skill not in skills:
            logger.warning(f"{character.name} does not have skill {skill.value}")
            # Create a basic skill with no proficiency
            from .character import Skill
            skill_obj = Skill(skill.value, AttributeType.STRENGTH, False)  # Default attribute
        else:
            skill_obj = skills[skill]
        
        # Calculate base bonus
        base_bonus = character.get_skill_bonus(skill)
        
        # Apply condition effects
        self._apply_condition_effects(character, context, "skill_check")
        
        # Create dice roll
        dice_roll = DiceRoll(
            dice_count=1,
            dice_type=self.dice_roller.PRESET_ROLLS['d20'].dice_type,
            modifier=base_bonus + context.get_total_modifier(),
            advantage=context.has_advantage(),
            disadvantage=context.has_disadvantage()
        )
        
        # Roll the dice
        roll_result = self.dice_roller.roll(dice_roll)
        
        # Determine success
        success = False
        degree = None
        if difficulty_class is not None:
            success = roll_result.total >= difficulty_class
            
            # Determine degree of success
            if roll_result.critical:
                degree = "critical_success"
            elif roll_result.fumble:
                degree = "critical_failure"
            elif success:
                degree = "success"
            else:
                degree = "failure"
        
        result = CheckResult(
            roll_result=roll_result,
            context=context,
            character=character,
            success=success,
            degree_of_success=degree
        )
        
        logger.info(f"{character.name} {skill.value} check: {roll_result.total} "
                   f"({'SUCCESS' if success else 'FAILURE'} vs DC {difficulty_class})")
        
        return result
    
    def make_ability_check(self, character: CharacterInterface, attribute: AttributeType,
                          difficulty_class: Optional[int] = None,
                          context: Optional[CheckContext] = None) -> CheckResult:
        """Make an ability check for a character."""
        if context is None:
            context = CheckContext(
                check_type=CheckType.ABILITY_CHECK,
                difficulty_class=difficulty_class
            )
        
        # Get attribute modifier
        attribute_mod = 0
        attributes = character.attributes
        if attribute in attributes:
            attribute_mod = attributes[attribute].get_modifier()
        
        # Apply condition effects
        self._apply_condition_effects(character, context, "ability_check")
        
        # Create dice roll
        dice_roll = DiceRoll(
            dice_count=1,
            dice_type=self.dice_roller.PRESET_ROLLS['d20'].dice_type,
            modifier=attribute_mod + context.get_total_modifier(),
            advantage=context.has_advantage(),
            disadvantage=context.has_disadvantage()
        )
        
        # Roll the dice
        roll_result = self.dice_roller.roll(dice_roll)
        
        # Determine success
        success = False
        degree = None
        if difficulty_class is not None:
            success = roll_result.total >= difficulty_class
            
            if roll_result.critical:
                degree = "critical_success"
            elif roll_result.fumble:
                degree = "critical_failure"
            elif success:
                degree = "success"
            else:
                degree = "failure"
        
        result = CheckResult(
            roll_result=roll_result,
            context=context,
            character=character,
            success=success,
            degree_of_success=degree
        )
        
        logger.info(f"{character.name} {attribute.value} check: {roll_result.total} "
                   f"({'SUCCESS' if success else 'FAILURE'} vs DC {difficulty_class})")
        
        return result
    
    def make_saving_throw(self, character: CharacterInterface, attribute: AttributeType,
                         difficulty_class: int, context: Optional[CheckContext] = None) -> CheckResult:
        """Make a saving throw for a character."""
        if context is None:
            context = CheckContext(
                check_type=CheckType.SAVING_THROW,
                difficulty_class=difficulty_class
            )
        
        # Get attribute modifier
        attribute_mod = 0
        attributes = character.attributes
        if attribute in attributes:
            attribute_mod = attributes[attribute].get_modifier()
        
        # Add proficiency bonus if proficient in this save
        proficiency_bonus = 0
        if hasattr(character, 'character_class') and character.character_class:
            if hasattr(character.character_class, 'saving_throws'):
                if attribute in character.character_class.saving_throws:
                    # Calculate proficiency bonus based on level
                    proficiency_bonus = (character.level - 1) // 4 + 2
        
        total_bonus = attribute_mod + proficiency_bonus
        
        # Apply condition effects
        self._apply_condition_effects(character, context, "saving_throw")
        
        # Create dice roll
        dice_roll = DiceRoll(
            dice_count=1,
            dice_type=self.dice_roller.PRESET_ROLLS['d20'].dice_type,
            modifier=total_bonus + context.get_total_modifier(),
            advantage=context.has_advantage(),
            disadvantage=context.has_disadvantage()
        )
        
        # Roll the dice
        roll_result = self.dice_roller.roll(dice_roll)
        
        # Determine success
        success = roll_result.total >= difficulty_class
        
        degree = None
        if roll_result.critical:
            degree = "critical_success"
            success = True  # Critical saves always succeed
        elif roll_result.fumble:
            degree = "critical_failure"
            success = False  # Critical fails always fail
        elif success:
            degree = "success"
        else:
            degree = "failure"
        
        result = CheckResult(
            roll_result=roll_result,
            context=context,
            character=character,
            success=success,
            degree_of_success=degree
        )
        
        logger.info(f"{character.name} {attribute.value} save: {roll_result.total} vs DC {difficulty_class} "
                   f"({'SUCCESS' if success else 'FAILURE'})")
        
        return result
    
    def make_contest(self, character1: CharacterInterface, character2: CharacterInterface,
                    check_type1: Union[SkillType, AttributeType], 
                    check_type2: Union[SkillType, AttributeType],
                    context1: Optional[CheckContext] = None,
                    context2: Optional[CheckContext] = None) -> tuple[CheckResult, CheckResult, CharacterInterface]:
        """Make a contested check between two characters."""
        
        # Make checks for both characters
        if isinstance(check_type1, SkillType):
            result1 = self.make_skill_check(character1, check_type1, context=context1)
        else:
            result1 = self.make_ability_check(character1, check_type1, context=context1)
        
        if isinstance(check_type2, SkillType):
            result2 = self.make_skill_check(character2, check_type2, context=context2)
        else:
            result2 = self.make_ability_check(character2, check_type2, context=context2)
        
        # Determine winner
        if result1.total > result2.total:
            winner = character1
            result1.success = True
            result2.success = False
        elif result2.total > result1.total:
            winner = character2
            result1.success = False
            result2.success = True
        else:
            # Tie - could be handled differently by system
            winner = character1  # Default to first character
            result1.success = True
            result2.success = False
        
        logger.info(f"Contest: {character1.name} ({result1.total}) vs "
                   f"{character2.name} ({result2.total}) - Winner: {winner.name}")
        
        return result1, result2, winner
    
    def make_group_check(self, participants: List[tuple[CharacterInterface, Union[SkillType, AttributeType]]],
                        difficulty_class: int, success_threshold: Optional[int] = None) -> tuple[List[CheckResult], bool]:
        """Make a group check where multiple characters participate."""
        if success_threshold is None:
            success_threshold = len(participants) // 2 + 1  # Majority must succeed
        
        results = []
        successes = 0
        
        for character, check_type in participants:
            if isinstance(check_type, SkillType):
                result = self.make_skill_check(character, check_type, difficulty_class)
            else:
                result = self.make_ability_check(character, check_type, difficulty_class)
            
            results.append(result)
            if result.success:
                successes += 1
        
        group_success = successes >= success_threshold
        
        logger.info(f"Group check: {successes}/{len(participants)} succeeded "
                   f"(needed {success_threshold}) - {'SUCCESS' if group_success else 'FAILURE'}")
        
        return results, group_success
    
    def add_situational_modifier(self, context: CheckContext, name: str, 
                                value: int, source: str, description: str = "") -> None:
        """Add a situational modifier to a check context."""
        modifier = CheckModifier(
            name=name,
            value=value,
            source=source,
            description=description
        )
        context.add_modifier(modifier)
    
    def _apply_condition_effects(self, character: CharacterInterface, 
                               context: CheckContext, check_category: str) -> None:
        """Apply effects from character conditions to the check context."""
        for condition in character.conditions:
            if condition.type in self.condition_effects:
                effects = self.condition_effects[condition.type]
                
                # Apply disadvantage/advantage
                if effects.get("disadvantage") and check_category in effects.get("applies_to", []):
                    context.disadvantage = True
                
                if effects.get("advantage") and check_category in effects.get("applies_to", []):
                    context.advantage = True
                
                # Apply modifiers
                modifier_value = effects.get("modifier", 0)
                if modifier_value != 0 and check_category in effects.get("applies_to", []):
                    self.add_situational_modifier(
                        context,
                        f"{condition.type.value}_penalty",
                        modifier_value,
                        "condition",
                        f"Effect from {condition.type.value} condition"
                    )
    
    def _register_default_condition_effects(self) -> None:
        """Register default effects for common conditions."""
        self.condition_effects = {
            ConditionType.POISONED: {
                "disadvantage": True,
                "applies_to": ["skill_check", "ability_check", "attack_roll"]
            },
            ConditionType.FRIGHTENED: {
                "disadvantage": True,
                "applies_to": ["skill_check", "ability_check", "attack_roll"]
            },
            ConditionType.CHARMED: {
                "special": "cannot_attack_charmer"
            },
            ConditionType.BLINDED: {
                "disadvantage": True,
                "applies_to": ["attack_roll"],
                "special": "perception_auto_fail"
            },
            ConditionType.DEAFENED: {
                "special": "hearing_auto_fail"
            },
            ConditionType.STUNNED: {
                "special": "incapacitated"
            },
            ConditionType.PARALYZED: {
                "special": "incapacitated"
            },
            ConditionType.UNCONSCIOUS: {
                "special": "incapacitated"
            }
        }
    
    def register_condition_effect(self, condition: ConditionType, effects: Dict[str, Any]) -> None:
        """Register custom effects for a condition."""
        self.condition_effects[condition] = effects
    
    def get_difficulty_class(self, difficulty: Union[CheckDifficulty, str, int]) -> int:
        """Convert difficulty to DC value."""
        if isinstance(difficulty, int):
            return difficulty
        elif isinstance(difficulty, CheckDifficulty):
            return difficulty.value
        elif isinstance(difficulty, str):
            difficulty_map = {
                "trivial": CheckDifficulty.TRIVIAL.value,
                "easy": CheckDifficulty.EASY.value,
                "medium": CheckDifficulty.MEDIUM.value,
                "hard": CheckDifficulty.HARD.value,
                "very_hard": CheckDifficulty.VERY_HARD.value,
                "legendary": CheckDifficulty.LEGENDARY.value
            }
            return difficulty_map.get(difficulty.lower(), CheckDifficulty.MEDIUM.value)
        else:
            return CheckDifficulty.MEDIUM.value


# Global check engine instance
default_check_engine = CheckEngine()


def make_skill_check(character: CharacterInterface, skill: SkillType,
                    difficulty: Union[CheckDifficulty, str, int] = CheckDifficulty.MEDIUM,
                    advantage: bool = False, disadvantage: bool = False) -> CheckResult:
    """Convenience function for making skill checks."""
    dc = default_check_engine.get_difficulty_class(difficulty)
    context = CheckContext(
        check_type=CheckType.SKILL_CHECK,
        difficulty_class=dc,
        advantage=advantage,
        disadvantage=disadvantage
    )
    return default_check_engine.make_skill_check(character, skill, dc, context)


def make_ability_check(character: CharacterInterface, attribute: AttributeType,
                      difficulty: Union[CheckDifficulty, str, int] = CheckDifficulty.MEDIUM,
                      advantage: bool = False, disadvantage: bool = False) -> CheckResult:
    """Convenience function for making ability checks."""
    dc = default_check_engine.get_difficulty_class(difficulty)
    context = CheckContext(
        check_type=CheckType.ABILITY_CHECK,
        difficulty_class=dc,
        advantage=advantage,
        disadvantage=disadvantage
    )
    return default_check_engine.make_ability_check(character, attribute, dc, context)


def make_saving_throw(character: CharacterInterface, attribute: AttributeType,
                     difficulty_class: int, advantage: bool = False, 
                     disadvantage: bool = False) -> CheckResult:
    """Convenience function for making saving throws."""
    context = CheckContext(
        check_type=CheckType.SAVING_THROW,
        difficulty_class=difficulty_class,
        advantage=advantage,
        disadvantage=disadvantage
    )
    return default_check_engine.make_saving_throw(character, attribute, difficulty_class, context)