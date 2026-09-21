"""
Core type definitions for the DMLog.ai RPG engine.
Provides base interfaces and enums for all game systems.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Union, Any, Callable
from datetime import datetime
import uuid


class DiceType(Enum):
    """Standard dice types used in RPGs."""
    D4 = 4
    D6 = 6
    D8 = 8
    D10 = 10
    D12 = 12
    D20 = 20
    D100 = 100


class AttributeType(Enum):
    """Common attribute types across RPG systems."""
    # D&D/Pathfinder style
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"
    
    # Call of Cthulhu style
    APPEARANCE = "appearance"
    EDUCATION = "education"
    POWER = "power"
    SIZE = "size"
    
    # Shadowrun style
    BODY = "body"
    AGILITY = "agility"
    REACTION = "reaction"
    LOGIC = "logic"
    INTUITION = "intuition"
    WILLPOWER = "willpower"
    EDGE = "edge"
    
    # Vampire style
    COMPOSURE = "composure"
    RESOLVE = "resolve"
    STAMINA = "stamina"
    PRESENCE = "presence"
    MANIPULATION = "manipulation"


class SkillType(Enum):
    """Common skill types."""
    ATHLETICS = "athletics"
    DECEPTION = "deception"
    HISTORY = "history"
    INSIGHT = "insight"
    INVESTIGATION = "investigation"
    MEDICINE = "medicine"
    PERCEPTION = "perception"
    PERSUASION = "persuasion"
    STEALTH = "stealth"
    SURVIVAL = "survival"


class DamageType(Enum):
    """Damage types for combat."""
    BLUDGEONING = "bludgeoning"
    PIERCING = "piercing"
    SLASHING = "slashing"
    ACID = "acid"
    COLD = "cold"
    FIRE = "fire"
    FORCE = "force"
    LIGHTNING = "lightning"
    NECROTIC = "necrotic"
    POISON = "poison"
    PSYCHIC = "psychic"
    RADIANT = "radiant"
    THUNDER = "thunder"


class ConditionType(Enum):
    """Status conditions."""
    BLINDED = "blinded"
    CHARMED = "charmed"
    DEAFENED = "deafened"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"
    PRONE = "prone"
    RESTRAINED = "restrained"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"


class SpellSchool(Enum):
    """Magic schools for spellcasters."""
    ABJURATION = "abjuration"
    CONJURATION = "conjuration"
    DIVINATION = "divination"
    ENCHANTMENT = "enchantment"
    EVOCATION = "evocation"
    ILLUSION = "illusion"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"


@dataclass
class DiceRoll:
    """Represents a dice roll with modifiers."""
    dice_count: int
    dice_type: DiceType
    modifier: int = 0
    advantage: bool = False
    disadvantage: bool = False
    exploding: bool = False
    reroll_ones: bool = False
    
    def __str__(self) -> str:
        base = f"{self.dice_count}d{self.dice_type.value}"
        if self.modifier > 0:
            base += f"+{self.modifier}"
        elif self.modifier < 0:
            base += str(self.modifier)
        
        modifiers = []
        if self.advantage:
            modifiers.append("advantage")
        if self.disadvantage:
            modifiers.append("disadvantage")
        if self.exploding:
            modifiers.append("exploding")
        if self.reroll_ones:
            modifiers.append("reroll_ones")
        
        if modifiers:
            base += f" ({', '.join(modifiers)})"
        
        return base


@dataclass
class RollResult:
    """Result of a dice roll."""
    roll: DiceRoll
    individual_rolls: List[int]
    total: int
    success: Optional[bool] = None
    critical: Optional[bool] = None
    fumble: Optional[bool] = None
    timestamp: datetime = field(default_factory=datetime.now)
    roll_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class Attribute:
    """Character attribute with score and modifiers."""
    name: str
    score: int
    modifier: Optional[int] = None
    proficiency_bonus: int = 0
    
    def get_modifier(self) -> int:
        """Calculate attribute modifier (D&D style by default)."""
        if self.modifier is not None:
            return self.modifier
        return (self.score - 10) // 2


@dataclass
class Skill:
    """Character skill with proficiency and specialization."""
    name: str
    attribute: AttributeType
    proficient: bool = False
    expertise: bool = False  # Double proficiency
    specialization: Optional[str] = None
    custom_bonus: int = 0


@dataclass
class Condition:
    """Status condition affecting a character."""
    type: ConditionType
    duration: Optional[int] = None  # Rounds remaining, None for permanent
    source: Optional[str] = None
    description: Optional[str] = None
    effects: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Equipment:
    """Equipment item."""
    name: str
    description: str
    weight: float = 0.0
    value: float = 0.0
    quantity: int = 1
    equipped: bool = False
    magical: bool = False
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Spell:
    """Spell definition."""
    name: str
    level: int
    school: SpellSchool
    casting_time: str
    range: str
    components: List[str]
    duration: str
    description: str
    damage: Optional[DiceRoll] = None
    damage_type: Optional[DamageType] = None
    save_attribute: Optional[AttributeType] = None
    concentration: bool = False
    ritual: bool = False


class GameSystemInterface(ABC):
    """Abstract interface for RPG game systems."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the game system."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Version of the game system."""
        pass
    
    @property
    @abstractmethod
    def supported_attributes(self) -> List[AttributeType]:
        """List of attributes this system uses."""
        pass
    
    @property
    @abstractmethod
    def supported_skills(self) -> List[SkillType]:
        """List of skills this system uses."""
        pass
    
    @abstractmethod
    def calculate_attribute_modifier(self, score: int) -> int:
        """Calculate attribute modifier from score."""
        pass
    
    @abstractmethod
    def calculate_skill_bonus(self, skill: Skill, character: 'Character') -> int:
        """Calculate total skill bonus for a character."""
        pass
    
    @abstractmethod
    def roll_skill_check(self, skill: Skill, character: 'Character', 
                        difficulty_class: Optional[int] = None) -> RollResult:
        """Roll a skill check."""
        pass
    
    @abstractmethod
    def roll_saving_throw(self, attribute: AttributeType, character: 'Character',
                         difficulty_class: int) -> RollResult:
        """Roll a saving throw."""
        pass
    
    @abstractmethod
    def calculate_armor_class(self, character: 'Character') -> int:
        """Calculate character's armor class."""
        pass
    
    @abstractmethod
    def calculate_hit_points(self, character: 'Character') -> int:
        """Calculate character's maximum hit points."""
        pass


class CharacterInterface(ABC):
    """Abstract interface for character implementations."""
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique character identifier."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Character name."""
        pass
    
    @property
    @abstractmethod
    def level(self) -> int:
        """Character level."""
        pass
    
    @property
    @abstractmethod
    def attributes(self) -> Dict[AttributeType, Attribute]:
        """Character attributes."""
        pass
    
    @property
    @abstractmethod
    def skills(self) -> Dict[SkillType, Skill]:
        """Character skills."""
        pass
    
    @property
    @abstractmethod
    def conditions(self) -> List[Condition]:
        """Active conditions on character."""
        pass
    
    @abstractmethod
    def get_attribute_score(self, attribute: AttributeType) -> int:
        """Get attribute score."""
        pass
    
    @abstractmethod
    def get_skill_bonus(self, skill: SkillType) -> int:
        """Get total skill bonus."""
        pass
    
    @abstractmethod
    def add_condition(self, condition: Condition) -> None:
        """Add a condition to the character."""
        pass
    
    @abstractmethod
    def remove_condition(self, condition_type: ConditionType) -> None:
        """Remove a condition from the character."""
        pass


class DiceRollerInterface(ABC):
    """Abstract interface for dice rolling systems."""
    
    @abstractmethod
    def roll(self, dice_roll: DiceRoll) -> RollResult:
        """Roll dice and return result."""
        pass
    
    @abstractmethod
    def roll_multiple(self, rolls: List[DiceRoll]) -> List[RollResult]:
        """Roll multiple dice and return results."""
        pass
    
    @abstractmethod
    def roll_with_callback(self, dice_roll: DiceRoll, 
                          callback: Callable[[RollResult], None]) -> RollResult:
        """Roll dice and execute callback with result."""
        pass


class CombatEngineInterface(ABC):
    """Abstract interface for combat systems."""
    
    @abstractmethod
    def roll_initiative(self, characters: List[CharacterInterface]) -> Dict[str, int]:
        """Roll initiative for all characters."""
        pass
    
    @abstractmethod
    def calculate_attack_roll(self, attacker: CharacterInterface, 
                            weapon: Equipment) -> RollResult:
        """Calculate attack roll."""
        pass
    
    @abstractmethod
    def calculate_damage(self, attacker: CharacterInterface, 
                       weapon: Equipment, target: CharacterInterface) -> RollResult:
        """Calculate damage roll."""
        pass
    
    @abstractmethod
    def apply_damage(self, target: CharacterInterface, 
                    damage: int, damage_type: DamageType) -> None:
        """Apply damage to a character."""
        pass
    
    @abstractmethod
    def start_combat(self, participants: List[CharacterInterface]) -> None:
        """Start a combat encounter."""
        pass
    
    @abstractmethod
    def next_turn(self) -> Optional[CharacterInterface]:
        """Advance to next character's turn."""
        pass
    
    @abstractmethod
    def end_combat(self) -> None:
        """End combat encounter."""
        pass


@dataclass
class Campaign:
    """Campaign data structure."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    game_system: str = ""
    dm_id: str = ""
    player_ids: List[str] = field(default_factory=list)
    character_ids: List[str] = field(default_factory=list)
    session_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """Game session data structure."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str = ""
    session_number: int = 1
    name: str = ""
    date: datetime = field(default_factory=datetime.now)
    duration_minutes: int = 0
    notes: str = ""
    participants: List[str] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    completed: bool = False


class RPGEngineError(Exception):
    """Base exception for RPG engine errors."""
    pass


class InvalidGameSystemError(RPGEngineError):
    """Raised when an invalid game system is specified."""
    pass


class CharacterCreationError(RPGEngineError):
    """Raised when character creation fails."""
    pass


class DiceRollError(RPGEngineError):
    """Raised when dice rolling fails."""
    pass


class CombatError(RPGEngineError):
    """Raised when combat operations fail."""
    pass