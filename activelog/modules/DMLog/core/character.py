"""
Flexible character sheet system for the DMLog.ai RPG engine.
Supports multiple game systems with different attribute and skill structures.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import uuid
import logging

from .types import (
    AttributeType, SkillType, Attribute, Skill, Condition, Equipment, Spell,
    CharacterInterface, DamageType, ConditionType, SpellSchool, RPGEngineError
)

logger = logging.getLogger(__name__)


@dataclass
class CharacterClass:
    """Character class/profession definition."""
    name: str
    hit_die: int  # Hit die size (6, 8, 10, 12)
    primary_attributes: List[AttributeType]
    class_skills: List[SkillType]
    saving_throws: List[AttributeType]
    proficiencies: Dict[str, List[str]] = field(default_factory=dict)
    class_features: List[str] = field(default_factory=list)
    spell_casting: bool = False
    spell_attribute: Optional[AttributeType] = None
    spell_slots_per_level: Dict[int, List[int]] = field(default_factory=dict)


@dataclass
class Race:
    """Character race/ancestry definition."""
    name: str
    size: str = "Medium"
    speed: int = 30
    attribute_bonuses: Dict[AttributeType, int] = field(default_factory=dict)
    racial_traits: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    skill_bonuses: Dict[SkillType, int] = field(default_factory=dict)
    resistances: List[DamageType] = field(default_factory=list)
    immunities: List[DamageType] = field(default_factory=list)
    special_abilities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Background:
    """Character background definition."""
    name: str
    skill_proficiencies: List[SkillType] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    equipment: List[Equipment] = field(default_factory=list)
    personality_traits: List[str] = field(default_factory=list)
    ideals: List[str] = field(default_factory=list)
    bonds: List[str] = field(default_factory=list)
    flaws: List[str] = field(default_factory=list)


@dataclass
class SpellSlot:
    """Spell slot tracking."""
    level: int
    total: int
    used: int = 0
    
    @property
    def remaining(self) -> int:
        return max(0, self.total - self.used)
    
    def use_slot(self) -> bool:
        """Use a spell slot if available."""
        if self.remaining > 0:
            self.used += 1
            return True
        return False
    
    def restore_slot(self, count: int = 1) -> int:
        """Restore spell slots, returns actual restored count."""
        restored = min(count, self.used)
        self.used -= restored
        return restored


@dataclass
class HitPoints:
    """Hit point tracking."""
    maximum: int
    current: int
    temporary: int = 0
    
    @property
    def total_current(self) -> int:
        """Total current hit points including temporary."""
        return self.current + self.temporary
    
    def take_damage(self, damage: int) -> int:
        """Take damage, returns actual damage taken."""
        # Temporary hit points are lost first
        if self.temporary > 0:
            temp_lost = min(damage, self.temporary)
            self.temporary -= temp_lost
            damage -= temp_lost
        
        # Then regular hit points
        if damage > 0:
            actual_damage = min(damage, self.current)
            self.current -= actual_damage
            return temp_lost + actual_damage
        
        return temp_lost
    
    def heal(self, healing: int) -> int:
        """Heal damage, returns actual healing."""
        max_heal = self.maximum - self.current
        actual_heal = min(healing, max_heal)
        self.current += actual_heal
        return actual_heal
    
    def add_temporary_hp(self, temp_hp: int) -> None:
        """Add temporary hit points (doesn't stack)."""
        self.temporary = max(self.temporary, temp_hp)


class BaseCharacter(CharacterInterface):
    """Base character implementation with flexible attribute system."""
    
    def __init__(self, name: str, game_system: str = "generic"):
        self._id = str(uuid.uuid4())
        self._name = name
        self.game_system = game_system
        self._level = 1
        self.experience_points = 0
        
        # Core stats
        self._attributes: Dict[AttributeType, Attribute] = {}
        self._skills: Dict[SkillType, Skill] = {}
        self.proficiency_bonus = 2
        
        # Character identity
        self.race: Optional[Race] = None
        self.character_class: Optional[CharacterClass] = None
        self.background: Optional[Background] = None
        
        # Combat stats
        self.hit_points = HitPoints(maximum=8, current=8)
        self.armor_class = 10
        self.initiative_bonus = 0
        
        # Status tracking
        self._conditions: List[Condition] = []
        self.death_saves_successes = 0
        self.death_saves_failures = 0
        self.exhaustion_level = 0
        
        # Equipment and resources
        self.equipment: List[Equipment] = []
        self.currency = {"gold": 0, "silver": 0, "copper": 0}
        
        # Spellcasting (if applicable)
        self.spell_slots: Dict[int, SpellSlot] = {}
        self.spells_known: List[Spell] = []
        self.spells_prepared: List[str] = []  # Spell names
        self.spell_attack_bonus = 0
        self.spell_save_dc = 8
        
        # Roleplay elements
        self.personality_traits: List[str] = []
        self.ideals: List[str] = []
        self.bonds: List[str] = []
        self.flaws: List[str] = []
        self.backstory = ""
        
        # Metadata
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.notes = ""
        
    @property
    def id(self) -> str:
        return self._id
    
    @property
    def name(self) -> str:
        return self._name
    
    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self.updated_at = datetime.now()
    
    @property
    def level(self) -> int:
        return self._level
    
    @level.setter
    def level(self, value: int) -> None:
        if value < 1:
            raise ValueError("Level must be at least 1")
        if value > 20:
            raise ValueError("Level cannot exceed 20")
        
        old_level = self._level
        self._level = value
        
        # Update proficiency bonus
        self.proficiency_bonus = (value - 1) // 4 + 2
        
        # Level up hit points if gaining levels
        if value > old_level and self.character_class:
            for _ in range(value - old_level):
                self._level_up_hit_points()
        
        self.updated_at = datetime.now()
    
    @property
    def attributes(self) -> Dict[AttributeType, Attribute]:
        return self._attributes.copy()
    
    @property
    def skills(self) -> Dict[SkillType, Skill]:
        return self._skills.copy()
    
    @property
    def conditions(self) -> List[Condition]:
        return self._conditions.copy()
    
    def add_attribute(self, attr_type: AttributeType, score: int) -> None:
        """Add or update an attribute."""
        self._attributes[attr_type] = Attribute(
            name=attr_type.value,
            score=score,
            proficiency_bonus=self.proficiency_bonus
        )
        self.updated_at = datetime.now()
    
    def add_skill(self, skill_type: SkillType, attribute: AttributeType, 
                  proficient: bool = False, expertise: bool = False) -> None:
        """Add or update a skill."""
        self._skills[skill_type] = Skill(
            name=skill_type.value,
            attribute=attribute,
            proficient=proficient,
            expertise=expertise
        )
        self.updated_at = datetime.now()
    
    def get_attribute_score(self, attribute: AttributeType) -> int:
        """Get attribute score."""
        if attribute not in self._attributes:
            return 10  # Default score
        return self._attributes[attribute].score
    
    def get_attribute_modifier(self, attribute: AttributeType) -> int:
        """Get attribute modifier."""
        if attribute not in self._attributes:
            return 0
        return self._attributes[attribute].get_modifier()
    
    def get_skill_bonus(self, skill: SkillType) -> int:
        """Get total skill bonus including attribute modifier and proficiency."""
        if skill not in self._skills:
            return 0
        
        skill_obj = self._skills[skill]
        attribute_mod = self.get_attribute_modifier(skill_obj.attribute)
        bonus = attribute_mod + skill_obj.custom_bonus
        
        if skill_obj.proficient:
            if skill_obj.expertise:
                bonus += self.proficiency_bonus * 2
            else:
                bonus += self.proficiency_bonus
        
        return bonus
    
    def add_condition(self, condition: Condition) -> None:
        """Add a condition to the character."""
        # Remove existing condition of same type
        self.remove_condition(condition.type)
        self._conditions.append(condition)
        self.updated_at = datetime.now()
        logger.info(f"Added condition {condition.type.value} to {self.name}")
    
    def remove_condition(self, condition_type: ConditionType) -> None:
        """Remove a condition from the character."""
        self._conditions = [c for c in self._conditions if c.type != condition_type]
        self.updated_at = datetime.now()
        logger.info(f"Removed condition {condition_type.value} from {self.name}")
    
    def has_condition(self, condition_type: ConditionType) -> bool:
        """Check if character has a specific condition."""
        return any(c.type == condition_type for c in self._conditions)
    
    def get_condition(self, condition_type: ConditionType) -> Optional[Condition]:
        """Get a specific condition if present."""
        for condition in self._conditions:
            if condition.type == condition_type:
                return condition
        return None
    
    def process_condition_duration(self) -> List[ConditionType]:
        """Process condition durations, return list of expired conditions."""
        expired = []
        remaining_conditions = []
        
        for condition in self._conditions:
            if condition.duration is not None:
                condition.duration -= 1
                if condition.duration <= 0:
                    expired.append(condition.type)
                else:
                    remaining_conditions.append(condition)
            else:
                remaining_conditions.append(condition)
        
        self._conditions = remaining_conditions
        
        if expired:
            self.updated_at = datetime.now()
            logger.info(f"Expired conditions for {self.name}: {[c.value for c in expired]}")
        
        return expired
    
    def add_equipment(self, equipment: Equipment) -> None:
        """Add equipment to character."""
        self.equipment.append(equipment)
        self.updated_at = datetime.now()
    
    def remove_equipment(self, equipment_name: str) -> bool:
        """Remove equipment by name."""
        for i, item in enumerate(self.equipment):
            if item.name == equipment_name:
                del self.equipment[i]
                self.updated_at = datetime.now()
                return True
        return False
    
    def get_equipped_items(self) -> List[Equipment]:
        """Get all equipped items."""
        return [item for item in self.equipment if item.equipped]
    
    def equip_item(self, equipment_name: str) -> bool:
        """Equip an item by name."""
        for item in self.equipment:
            if item.name == equipment_name:
                item.equipped = True
                self.updated_at = datetime.now()
                return True
        return False
    
    def unequip_item(self, equipment_name: str) -> bool:
        """Unequip an item by name."""
        for item in self.equipment:
            if item.name == equipment_name:
                item.equipped = False
                self.updated_at = datetime.now()
                return True
        return False
    
    def add_spell_slot(self, level: int, total: int) -> None:
        """Add spell slots of a given level."""
        if level not in self.spell_slots:
            self.spell_slots[level] = SpellSlot(level, total)
        else:
            self.spell_slots[level].total = total
        self.updated_at = datetime.now()
    
    def use_spell_slot(self, level: int) -> bool:
        """Use a spell slot of the given level."""
        if level in self.spell_slots:
            success = self.spell_slots[level].use_slot()
            if success:
                self.updated_at = datetime.now()
            return success
        return False
    
    def restore_spell_slots(self, level: Optional[int] = None, count: int = 1) -> int:
        """Restore spell slots. If level is None, restore all levels."""
        total_restored = 0
        
        if level is not None:
            if level in self.spell_slots:
                total_restored = self.spell_slots[level].restore_slot(count)
        else:
            # Restore all levels
            for slot in self.spell_slots.values():
                slot.used = 0
            total_restored = sum(slot.total for slot in self.spell_slots.values())
        
        if total_restored > 0:
            self.updated_at = datetime.now()
        
        return total_restored
    
    def add_spell(self, spell: Spell, prepared: bool = True) -> None:
        """Add a spell to the character's spell list."""
        if spell not in self.spells_known:
            self.spells_known.append(spell)
        
        if prepared and spell.name not in self.spells_prepared:
            self.spells_prepared.append(spell.name)
        
        self.updated_at = datetime.now()
    
    def prepare_spell(self, spell_name: str) -> bool:
        """Prepare a known spell."""
        # Check if spell is known
        if not any(spell.name == spell_name for spell in self.spells_known):
            return False
        
        if spell_name not in self.spells_prepared:
            self.spells_prepared.append(spell_name)
            self.updated_at = datetime.now()
        
        return True
    
    def unprepare_spell(self, spell_name: str) -> bool:
        """Unprepare a spell."""
        if spell_name in self.spells_prepared:
            self.spells_prepared.remove(spell_name)
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_prepared_spells(self) -> List[Spell]:
        """Get all prepared spells."""
        return [spell for spell in self.spells_known 
                if spell.name in self.spells_prepared]
    
    def can_cast_spell(self, spell: Spell) -> bool:
        """Check if character can cast a spell."""
        # Must be prepared
        if spell.name not in self.spells_prepared:
            return False
        
        # Must have spell slot available
        if spell.level > 0:  # Cantrips don't need slots
            for level in range(spell.level, 10):  # Can upcast
                if level in self.spell_slots and self.spell_slots[level].remaining > 0:
                    return True
            return False
        
        return True
    
    def cast_spell(self, spell: Spell, spell_level: Optional[int] = None) -> bool:
        """Cast a spell, using appropriate spell slot."""
        if not self.can_cast_spell(spell):
            return False
        
        # Use spell slot if not a cantrip
        if spell.level > 0:
            cast_level = spell_level or spell.level
            if not self.use_spell_slot(cast_level):
                return False
        
        self.updated_at = datetime.now()
        return True
    
    def long_rest(self) -> None:
        """Perform a long rest, restoring resources."""
        # Restore hit points
        self.hit_points.current = self.hit_points.maximum
        self.hit_points.temporary = 0
        
        # Restore spell slots
        self.restore_spell_slots()
        
        # Reset death saves
        self.death_saves_successes = 0
        self.death_saves_failures = 0
        
        # Reduce exhaustion by 1 level
        if self.exhaustion_level > 0:
            self.exhaustion_level -= 1
        
        self.updated_at = datetime.now()
        logger.info(f"{self.name} completed a long rest")
    
    def short_rest(self) -> None:
        """Perform a short rest."""
        # Hit die recovery could be implemented here
        # Some class features recover on short rest
        
        self.updated_at = datetime.now()
        logger.info(f"{self.name} completed a short rest")
    
    def _level_up_hit_points(self) -> None:
        """Calculate hit point increase on level up."""
        if not self.character_class:
            return
        
        # Average hit points (can be overridden for rolling)
        hit_die = self.character_class.hit_die
        con_modifier = self.get_attribute_modifier(AttributeType.CONSTITUTION)
        
        # Use average: (hit_die / 2) + 1 + con_modifier
        hp_increase = (hit_die // 2) + 1 + con_modifier
        hp_increase = max(1, hp_increase)  # Minimum 1 HP per level
        
        self.hit_points.maximum += hp_increase
        self.hit_points.current += hp_increase
    
    def calculate_armor_class(self) -> int:
        """Calculate armor class from equipment and abilities."""
        base_ac = 10
        dex_modifier = self.get_attribute_modifier(AttributeType.DEXTERITY)
        
        # Find armor
        armor_items = [item for item in self.get_equipped_items() 
                      if item.properties.get("armor_type")]
        
        if armor_items:
            # Use the first armor found (should validate only one)
            armor = armor_items[0]
            armor_ac = armor.properties.get("armor_class", 10)
            max_dex = armor.properties.get("max_dex_bonus")
            
            if max_dex is not None:
                dex_modifier = min(dex_modifier, max_dex)
            
            base_ac = armor_ac + dex_modifier
        else:
            base_ac += dex_modifier
        
        # Add shield bonus
        shield_items = [item for item in self.get_equipped_items() 
                       if item.properties.get("shield")]
        if shield_items:
            base_ac += shield_items[0].properties.get("ac_bonus", 2)
        
        return base_ac
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert character to dictionary for serialization."""
        return {
            "id": self._id,
            "name": self._name,
            "game_system": self.game_system,
            "level": self._level,
            "experience_points": self.experience_points,
            "attributes": {k.value: {"score": v.score, "modifier": v.modifier, "proficiency_bonus": v.proficiency_bonus} 
                          for k, v in self._attributes.items()},
            "skills": {k.value: {"attribute": v.attribute.value, "proficient": v.proficient, 
                                "expertise": v.expertise, "custom_bonus": v.custom_bonus} 
                      for k, v in self._skills.items()},
            "hit_points": {
                "maximum": self.hit_points.maximum,
                "current": self.hit_points.current,
                "temporary": self.hit_points.temporary
            },
            "armor_class": self.armor_class,
            "conditions": [{"type": c.type.value, "duration": c.duration, "source": c.source} 
                          for c in self._conditions],
            "equipment": [{"name": e.name, "equipped": e.equipped, "quantity": e.quantity} 
                         for e in self.equipment],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseCharacter':
        """Create character from dictionary."""
        char = cls(data["name"], data.get("game_system", "generic"))
        char._id = data["id"]
        char._level = data["level"]
        char.experience_points = data.get("experience_points", 0)
        
        # Restore attributes
        for attr_name, attr_data in data.get("attributes", {}).items():
            try:
                attr_type = AttributeType(attr_name)
                char.add_attribute(attr_type, attr_data["score"])
            except ValueError:
                logger.warning(f"Unknown attribute type: {attr_name}")
        
        # Restore skills
        for skill_name, skill_data in data.get("skills", {}).items():
            try:
                skill_type = SkillType(skill_name)
                attr_type = AttributeType(skill_data["attribute"])
                char.add_skill(skill_type, attr_type, 
                             skill_data.get("proficient", False),
                             skill_data.get("expertise", False))
            except ValueError:
                logger.warning(f"Unknown skill or attribute type: {skill_name}")
        
        # Restore hit points
        if "hit_points" in data:
            hp_data = data["hit_points"]
            char.hit_points = HitPoints(
                maximum=hp_data["maximum"],
                current=hp_data["current"],
                temporary=hp_data.get("temporary", 0)
            )
        
        char.created_at = datetime.fromisoformat(data["created_at"])
        char.updated_at = datetime.fromisoformat(data["updated_at"])
        
        return char