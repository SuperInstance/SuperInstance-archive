"""
Spell and power system for the DMLog.ai RPG engine.
Supports various magic systems across different RPG games.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any, Callable
from enum import Enum
from datetime import datetime
import uuid
import logging

from .types import (
    AttributeType, DamageType, ConditionType, SpellSchool, Spell,
    CharacterInterface, DiceRoll, RollResult
)
from .dice import DiceRoller, default_roller

logger = logging.getLogger(__name__)


class SpellType(Enum):
    """Types of spells/powers."""
    SPELL = "spell"
    CANTRIP = "cantrip"
    RITUAL = "ritual"
    POWER = "power"  # For psionics/supernatural abilities
    INVOCATION = "invocation"  # Warlock invocations
    MANEUVER = "maneuver"  # Battle master maneuvers
    TECHNIQUE = "technique"  # Monk techniques
    MIRACLE = "miracle"  # Divine interventions


class SpellComponent(Enum):
    """Spell components."""
    VERBAL = "V"
    SOMATIC = "S"
    MATERIAL = "M"
    FOCUS = "F"  # Requires focus/implement
    DIVINE_FOCUS = "DF"  # Divine focus


class CastingTime(Enum):
    """Casting time categories."""
    ACTION = "1_action"
    BONUS_ACTION = "1_bonus_action"
    REACTION = "1_reaction"
    MINUTE = "1_minute"
    TEN_MINUTES = "10_minutes"
    HOUR = "1_hour"
    EIGHT_HOURS = "8_hours"
    TWENTY_FOUR_HOURS = "24_hours"


class SpellRange(Enum):
    """Spell range categories."""
    SELF = "Self"
    TOUCH = "Touch"
    RANGED_5 = "5 feet"
    RANGED_10 = "10 feet"
    RANGED_30 = "30 feet"
    RANGED_60 = "60 feet"
    RANGED_90 = "90 feet"
    RANGED_120 = "120 feet"
    RANGED_150 = "150 feet"
    RANGED_300 = "300 feet"
    RANGED_500 = "500 feet"
    RANGED_1000 = "1000 feet"
    RANGED_1_MILE = "1 mile"
    SIGHT = "Sight"
    UNLIMITED = "Unlimited"


class SpellDuration(Enum):
    """Spell duration categories."""
    INSTANTANEOUS = "Instantaneous"
    CONCENTRATION_1_MINUTE = "Concentration, up to 1 minute"
    CONCENTRATION_10_MINUTES = "Concentration, up to 10 minutes"
    CONCENTRATION_1_HOUR = "Concentration, up to 1 hour"
    CONCENTRATION_8_HOURS = "Concentration, up to 8 hours"
    ONE_MINUTE = "1 minute"
    TEN_MINUTES = "10 minutes"
    ONE_HOUR = "1 hour"
    EIGHT_HOURS = "8 hours"
    TWENTY_FOUR_HOURS = "24 hours"
    ONE_DAY = "1 day"
    SEVEN_DAYS = "7 days"
    THIRTY_DAYS = "30 days"
    PERMANENT = "Until dispelled"


class SpellTarget(Enum):
    """Spell target types."""
    SELF = "Self"
    CREATURE = "One creature"
    CREATURES_MULTIPLE = "Multiple creatures"
    OBJECT = "One object"
    POINT = "A point in space"
    AREA_SPHERE = "Sphere"
    AREA_CUBE = "Cube"
    AREA_CYLINDER = "Cylinder"
    AREA_CONE = "Cone"
    AREA_LINE = "Line"


@dataclass
class SpellEffect:
    """Represents the effect of a spell."""
    type: str  # "damage", "healing", "condition", "buff", "debuff", etc.
    value: Optional[Union[int, str]] = None
    damage_type: Optional[DamageType] = None
    condition: Optional[ConditionType] = None
    duration_rounds: Optional[int] = None
    save_negates: bool = False
    save_half: bool = False
    description: str = ""


@dataclass
class SpellSlotInfo:
    """Information about spell slot usage."""
    level: int
    consumed: bool = True
    cost: int = 1  # Some spells might cost multiple slots
    
    
@dataclass
class SpellCastResult:
    """Result of casting a spell."""
    spell: 'EnhancedSpell'
    caster: CharacterInterface
    targets: List[CharacterInterface]
    cast_level: int
    success: bool = True
    roll_results: List[RollResult] = field(default_factory=list)
    damage_dealt: Dict[str, int] = field(default_factory=dict)  # target_id -> damage
    healing_done: Dict[str, int] = field(default_factory=dict)  # target_id -> healing
    conditions_applied: Dict[str, List[ConditionType]] = field(default_factory=dict)
    slot_used: Optional[SpellSlotInfo] = None
    timestamp: datetime = field(default_factory=datetime.now)
    concentration_started: bool = False


@dataclass
class EnhancedSpell:
    """Enhanced spell definition with more detailed mechanics."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    level: int = 0
    spell_type: SpellType = SpellType.SPELL
    school: SpellSchool = SpellSchool.EVOCATION
    
    # Casting requirements
    casting_time: CastingTime = CastingTime.ACTION
    range: SpellRange = SpellRange.RANGED_60
    components: List[SpellComponent] = field(default_factory=list)
    material_components: str = ""
    duration: SpellDuration = SpellDuration.INSTANTANEOUS
    
    # Targeting
    target_type: SpellTarget = SpellTarget.CREATURE
    area_size: Optional[int] = None  # For area spells
    max_targets: Optional[int] = None
    
    # Effects
    effects: List[SpellEffect] = field(default_factory=list)
    upcast_effects: Dict[int, List[SpellEffect]] = field(default_factory=dict)  # level -> effects
    
    # Mechanics
    requires_attack_roll: bool = False
    save_attribute: Optional[AttributeType] = None
    concentration: bool = False
    ritual: bool = False
    
    # Flavor
    description: str = ""
    higher_level: str = ""  # Description of upcasting effects
    
    # System-specific data
    system_data: Dict[str, Any] = field(default_factory=dict)
    
    def can_be_cast_at_level(self, level: int) -> bool:
        """Check if spell can be cast at a given level."""
        return level >= self.level
    
    def get_effects_for_level(self, cast_level: int) -> List[SpellEffect]:
        """Get spell effects when cast at a specific level."""
        base_effects = self.effects.copy()
        
        # Add upcast effects
        if cast_level > self.level and cast_level in self.upcast_effects:
            base_effects.extend(self.upcast_effects[cast_level])
        
        return base_effects
    
    def requires_concentration(self) -> bool:
        """Check if spell requires concentration."""
        return self.concentration or "concentration" in self.duration.value.lower()


class SpellcastingSystem:
    """Handles spellcasting mechanics."""
    
    def __init__(self, dice_roller: Optional[DiceRoller] = None):
        self.dice_roller = dice_roller or default_roller
        self.spell_library: Dict[str, EnhancedSpell] = {}
        self.active_concentrations: Dict[str, str] = {}  # character_id -> spell_name
        
    def add_spell_to_library(self, spell: EnhancedSpell) -> None:
        """Add a spell to the spell library."""
        self.spell_library[spell.name.lower()] = spell
        logger.info(f"Added spell {spell.name} to library")
    
    def get_spell(self, spell_name: str) -> Optional[EnhancedSpell]:
        """Get a spell from the library."""
        return self.spell_library.get(spell_name.lower())
    
    def cast_spell(self, caster: CharacterInterface, spell_name: str, 
                  targets: List[CharacterInterface], cast_level: Optional[int] = None) -> SpellCastResult:
        """Cast a spell."""
        spell = self.get_spell(spell_name)
        if not spell:
            raise ValueError(f"Spell '{spell_name}' not found in library")
        
        # Determine cast level
        if cast_level is None:
            cast_level = spell.level
        
        if not spell.can_be_cast_at_level(cast_level):
            raise ValueError(f"Cannot cast {spell.name} at level {cast_level}")
        
        # Check if caster can cast the spell
        if not self._can_cast_spell(caster, spell, cast_level):
            result = SpellCastResult(spell, caster, targets, cast_level, success=False)
            logger.warning(f"{caster.name} cannot cast {spell.name}")
            return result
        
        # Use spell slot if required
        slot_info = None
        if spell.level > 0:  # Not a cantrip
            slot_info = self._use_spell_slot(caster, cast_level)
            if not slot_info:
                result = SpellCastResult(spell, caster, targets, cast_level, success=False)
                logger.warning(f"{caster.name} has no spell slots for level {cast_level}")
                return result
        
        # Handle concentration
        concentration_started = False
        if spell.requires_concentration():
            self._end_concentration(caster)
            self._start_concentration(caster, spell.name)
            concentration_started = True
        
        # Create result object
        result = SpellCastResult(
            spell=spell,
            caster=caster,
            targets=targets,
            cast_level=cast_level,
            slot_used=slot_info,
            concentration_started=concentration_started
        )
        
        # Apply spell effects
        self._apply_spell_effects(result)
        
        logger.info(f"{caster.name} cast {spell.name} at level {cast_level}")
        return result
    
    def _can_cast_spell(self, caster: CharacterInterface, spell: EnhancedSpell, cast_level: int) -> bool:
        """Check if a character can cast a spell."""
        # Check if spell is known/prepared
        if hasattr(caster, 'spells_prepared'):
            if spell.name not in caster.spells_prepared:
                return False
        elif hasattr(caster, 'spells_known'):
            if not any(s.name == spell.name for s in caster.spells_known):
                return False
        
        # Check spell slot availability (for non-cantrips)
        if spell.level > 0:
            if not self._has_spell_slot(caster, cast_level):
                return False
        
        # Check conditions that prevent spellcasting
        for condition in caster.conditions:
            if condition.type in [ConditionType.STUNNED, ConditionType.PARALYZED, 
                                ConditionType.UNCONSCIOUS]:
                return False
            elif condition.type == ConditionType.INCAPACITATED and spell.casting_time != CastingTime.REACTION:
                return False
        
        return True
    
    def _has_spell_slot(self, caster: CharacterInterface, level: int) -> bool:
        """Check if caster has an available spell slot of the given level or higher."""
        if not hasattr(caster, 'spell_slots'):
            return False
        
        for slot_level in range(level, 10):  # Check from requested level up to 9th
            if slot_level in caster.spell_slots:
                if caster.spell_slots[slot_level].remaining > 0:
                    return True
        
        return False
    
    def _use_spell_slot(self, caster: CharacterInterface, level: int) -> Optional[SpellSlotInfo]:
        """Use a spell slot of the given level or higher."""
        if not hasattr(caster, 'spell_slots'):
            return None
        
        # Find available slot at level or higher
        for slot_level in range(level, 10):
            if slot_level in caster.spell_slots:
                slot = caster.spell_slots[slot_level]
                if slot.use_slot():
                    return SpellSlotInfo(level=slot_level)
        
        return None
    
    def _start_concentration(self, caster: CharacterInterface, spell_name: str) -> None:
        """Start concentration on a spell."""
        self.active_concentrations[caster.id] = spell_name
        logger.info(f"{caster.name} started concentrating on {spell_name}")
    
    def _end_concentration(self, caster: CharacterInterface) -> None:
        """End concentration for a caster."""
        if caster.id in self.active_concentrations:
            old_spell = self.active_concentrations[caster.id]
            del self.active_concentrations[caster.id]
            logger.info(f"{caster.name} stopped concentrating on {old_spell}")
    
    def make_concentration_save(self, caster: CharacterInterface, 
                              damage_taken: int) -> bool:
        """Make a Constitution saving throw to maintain concentration."""
        if caster.id not in self.active_concentrations:
            return True  # Not concentrating
        
        # DC is 10 or half the damage taken, whichever is higher
        dc = max(10, damage_taken // 2)
        
        # Make Constitution saving throw
        con_mod = 0
        if hasattr(caster, 'get_attribute_modifier'):
            con_mod = caster.get_attribute_modifier(AttributeType.CONSTITUTION)
        
        # Add proficiency if proficient in Con saves
        proficiency = 0
        if (hasattr(caster, 'character_class') and caster.character_class and
            hasattr(caster.character_class, 'saving_throws') and
            AttributeType.CONSTITUTION in caster.character_class.saving_throws):
            proficiency = (caster.level - 1) // 4 + 2
        
        dice_roll = DiceRoll(1, self.dice_roller.PRESET_ROLLS['d20'].dice_type, 
                           con_mod + proficiency)
        result = self.dice_roller.roll(dice_roll)
        
        success = result.total >= dc
        
        if not success:
            spell_name = self.active_concentrations.get(caster.id, "unknown spell")
            self._end_concentration(caster)
            logger.info(f"{caster.name} lost concentration on {spell_name} "
                       f"(rolled {result.total} vs DC {dc})")
        
        return success
    
    def _apply_spell_effects(self, cast_result: SpellCastResult) -> None:
        """Apply the effects of a cast spell."""
        effects = cast_result.spell.get_effects_for_level(cast_result.cast_level)
        
        for effect in effects:
            if effect.type == "damage":
                self._apply_damage_effect(cast_result, effect)
            elif effect.type == "healing":
                self._apply_healing_effect(cast_result, effect)
            elif effect.type == "condition":
                self._apply_condition_effect(cast_result, effect)
            # Add more effect types as needed
    
    def _apply_damage_effect(self, cast_result: SpellCastResult, effect: SpellEffect) -> None:
        """Apply damage effect to targets."""
        spell = cast_result.spell
        
        for target in cast_result.targets:
            # Check for attack roll if required
            hit = True
            if spell.requires_attack_roll:
                attack_roll = self._make_spell_attack_roll(cast_result.caster, target)
                cast_result.roll_results.append(attack_roll)
                hit = attack_roll.total >= target.armor_class if hasattr(target, 'armor_class') else True
            
            # Check for saving throw
            if spell.save_attribute and not spell.requires_attack_roll:
                save_dc = self._calculate_spell_save_dc(cast_result.caster)
                save_result = self._make_saving_throw(target, spell.save_attribute, save_dc)
                cast_result.roll_results.append(save_result)
                
                if save_result.success:
                    if effect.save_negates:
                        continue  # No damage on successful save
                    elif effect.save_half:
                        # Half damage will be applied below
                        pass
            
            if hit:
                # Roll damage
                damage_roll = self._roll_spell_damage(effect, cast_result.cast_level)
                cast_result.roll_results.append(damage_roll)
                
                damage = damage_roll.total
                
                # Apply save for half if applicable
                if (spell.save_attribute and effect.save_half and 
                    cast_result.roll_results[-2].success):  # Previous roll was the save
                    damage //= 2
                
                # Apply damage
                if hasattr(target, 'hit_points') and hasattr(target.hit_points, 'take_damage'):
                    actual_damage = target.hit_points.take_damage(damage)
                    cast_result.damage_dealt[target.id] = actual_damage
                
                logger.info(f"{spell.name} deals {damage} {effect.damage_type.value if effect.damage_type else 'force'} "
                           f"damage to {target.name}")
    
    def _apply_healing_effect(self, cast_result: SpellCastResult, effect: SpellEffect) -> None:
        """Apply healing effect to targets."""
        for target in cast_result.targets:
            # Roll healing
            healing_roll = self._roll_spell_healing(effect, cast_result.cast_level)
            cast_result.roll_results.append(healing_roll)
            
            healing = healing_roll.total
            
            # Apply healing
            if hasattr(target, 'hit_points') and hasattr(target.hit_points, 'heal'):
                actual_healing = target.hit_points.heal(healing)
                cast_result.healing_done[target.id] = actual_healing
            
            logger.info(f"{cast_result.spell.name} heals {healing} HP to {target.name}")
    
    def _apply_condition_effect(self, cast_result: SpellCastResult, effect: SpellEffect) -> None:
        """Apply condition effect to targets."""
        if not effect.condition:
            return
        
        spell = cast_result.spell
        
        for target in cast_result.targets:
            apply_condition = True
            
            # Check for saving throw
            if spell.save_attribute:
                save_dc = self._calculate_spell_save_dc(cast_result.caster)
                save_result = self._make_saving_throw(target, spell.save_attribute, save_dc)
                cast_result.roll_results.append(save_result)
                
                if save_result.success and effect.save_negates:
                    apply_condition = False
            
            if apply_condition:
                from .types import Condition
                condition = Condition(
                    type=effect.condition,
                    duration=effect.duration_rounds,
                    source=cast_result.spell.name
                )
                target.add_condition(condition)
                
                if target.id not in cast_result.conditions_applied:
                    cast_result.conditions_applied[target.id] = []
                cast_result.conditions_applied[target.id].append(effect.condition)
                
                logger.info(f"{target.name} gains condition: {effect.condition.value}")
    
    def _make_spell_attack_roll(self, caster: CharacterInterface, target: CharacterInterface) -> RollResult:
        """Make a spell attack roll."""
        # Calculate spell attack bonus
        spell_attack_bonus = 0
        if hasattr(caster, 'spell_attack_bonus'):
            spell_attack_bonus = caster.spell_attack_bonus
        else:
            # Calculate from spellcasting attribute + proficiency
            if hasattr(caster, 'character_class') and caster.character_class:
                if hasattr(caster.character_class, 'spell_attribute'):
                    spell_attr = caster.character_class.spell_attribute
                    if spell_attr and hasattr(caster, 'get_attribute_modifier'):
                        attr_mod = caster.get_attribute_modifier(spell_attr)
                        proficiency = (caster.level - 1) // 4 + 2
                        spell_attack_bonus = attr_mod + proficiency
        
        dice_roll = DiceRoll(1, self.dice_roller.PRESET_ROLLS['d20'].dice_type, spell_attack_bonus)
        return self.dice_roller.roll(dice_roll)
    
    def _calculate_spell_save_dc(self, caster: CharacterInterface) -> int:
        """Calculate the save DC for a caster's spells."""
        if hasattr(caster, 'spell_save_dc'):
            return caster.spell_save_dc
        
        # Calculate from spellcasting attribute
        base_dc = 8
        proficiency = (caster.level - 1) // 4 + 2
        
        if hasattr(caster, 'character_class') and caster.character_class:
            if hasattr(caster.character_class, 'spell_attribute'):
                spell_attr = caster.character_class.spell_attribute
                if spell_attr and hasattr(caster, 'get_attribute_modifier'):
                    attr_mod = caster.get_attribute_modifier(spell_attr)
                    return base_dc + proficiency + attr_mod
        
        return base_dc + proficiency
    
    def _make_saving_throw(self, character: CharacterInterface, 
                          attribute: AttributeType, dc: int) -> RollResult:
        """Make a saving throw for a character."""
        # This is a simplified version - could use the check system
        attr_mod = 0
        if hasattr(character, 'get_attribute_modifier'):
            attr_mod = character.get_attribute_modifier(attribute)
        
        # Add proficiency if proficient in this save
        proficiency = 0
        if (hasattr(character, 'character_class') and character.character_class and
            hasattr(character.character_class, 'saving_throws') and
            attribute in character.character_class.saving_throws):
            proficiency = (character.level - 1) // 4 + 2
        
        dice_roll = DiceRoll(1, self.dice_roller.PRESET_ROLLS['d20'].dice_type, 
                           attr_mod + proficiency)
        result = self.dice_roller.roll(dice_roll)
        result.success = result.total >= dc
        
        return result
    
    def _roll_spell_damage(self, effect: SpellEffect, cast_level: int) -> RollResult:
        """Roll damage for a spell effect."""
        # This is a simplified implementation
        # In practice, you'd parse the damage string and handle scaling
        dice_roll = DiceRoll(cast_level, self.dice_roller.PRESET_ROLLS['hit_die_d6'].dice_type)
        return self.dice_roller.roll(dice_roll)
    
    def _roll_spell_healing(self, effect: SpellEffect, cast_level: int) -> RollResult:
        """Roll healing for a spell effect."""
        # Simplified implementation
        dice_roll = DiceRoll(cast_level, self.dice_roller.PRESET_ROLLS['hit_die_d8'].dice_type)
        return self.dice_roller.roll(dice_roll)


# Create some common spells
def create_common_spells() -> List[EnhancedSpell]:
    """Create a library of common spells."""
    spells = []
    
    # Magic Missile
    magic_missile = EnhancedSpell(
        name="Magic Missile",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range=SpellRange.RANGED_120,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        duration=SpellDuration.INSTANTANEOUS,
        target_type=SpellTarget.CREATURES_MULTIPLE,
        max_targets=3,
        effects=[
            SpellEffect(
                type="damage",
                damage_type=DamageType.FORCE,
                description="1d4+1 force damage per missile"
            )
        ],
        description="Create three glowing darts of magical force. Each dart hits automatically."
    )
    spells.append(magic_missile)
    
    # Cure Wounds
    cure_wounds = EnhancedSpell(
        name="Cure Wounds",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range=SpellRange.TOUCH,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        duration=SpellDuration.INSTANTANEOUS,
        target_type=SpellTarget.CREATURE,
        effects=[
            SpellEffect(
                type="healing",
                description="1d8 + spellcasting modifier"
            )
        ],
        description="Heal a creature you touch."
    )
    spells.append(cure_wounds)
    
    # Hold Person
    hold_person = EnhancedSpell(
        name="Hold Person",
        level=2,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.ACTION,
        range=SpellRange.RANGED_60,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        duration=SpellDuration.CONCENTRATION_1_MINUTE,
        target_type=SpellTarget.CREATURE,
        save_attribute=AttributeType.WISDOM,
        concentration=True,
        effects=[
            SpellEffect(
                type="condition",
                condition=ConditionType.PARALYZED,
                duration_rounds=10,  # 1 minute
                save_negates=True
            )
        ],
        description="Choose a humanoid you can see. The target must make a Wisdom saving throw or be paralyzed."
    )
    spells.append(hold_person)
    
    # Fireball
    fireball = EnhancedSpell(
        name="Fireball",
        level=3,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range=SpellRange.RANGED_150,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        duration=SpellDuration.INSTANTANEOUS,
        target_type=SpellTarget.AREA_SPHERE,
        area_size=20,  # 20-foot radius
        save_attribute=AttributeType.DEXTERITY,
        effects=[
            SpellEffect(
                type="damage",
                damage_type=DamageType.FIRE,
                save_half=True,
                description="8d6 fire damage"
            )
        ],
        description="A bright flash expands from a point into a 20-foot radius sphere of fire."
    )
    spells.append(fireball)
    
    return spells


# Global spellcasting system
default_spellcasting_system = SpellcastingSystem()

# Add common spells to the system
for spell in create_common_spells():
    default_spellcasting_system.add_spell_to_library(spell)


def cast_spell(caster: CharacterInterface, spell_name: str, 
              targets: List[CharacterInterface], cast_level: Optional[int] = None) -> SpellCastResult:
    """Convenience function to cast a spell."""
    return default_spellcasting_system.cast_spell(caster, spell_name, targets, cast_level)