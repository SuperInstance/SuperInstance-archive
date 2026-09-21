"""
Combat mechanics framework for the DMLog.ai RPG engine.
Provides turn-based combat with initiative, actions, and effects tracking.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any, Callable
from enum import Enum
from datetime import datetime
import uuid
import logging

from .types import (
    CharacterInterface, DiceRoll, RollResult, DamageType, 
    ConditionType, CombatEngineInterface, Equipment, RPGEngineError
)
from .dice import DiceRoller, default_roller

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions that can be taken in combat."""
    ACTION = "action"
    BONUS_ACTION = "bonus_action"
    REACTION = "reaction"
    MOVEMENT = "movement"
    FREE_ACTION = "free_action"
    LEGENDARY_ACTION = "legendary_action"
    LAIR_ACTION = "lair_action"


class CombatPhase(Enum):
    """Phases of combat."""
    INITIATIVE = "initiative"
    COMBAT = "combat"
    END = "end"


class CombatState(Enum):
    """States of a combat encounter."""
    NOT_STARTED = "not_started"
    INITIATIVE_PHASE = "initiative_phase"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


@dataclass
class CombatAction:
    """Represents an action taken in combat."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    character_id: str = ""
    action_type: ActionType = ActionType.ACTION
    name: str = ""
    description: str = ""
    target_ids: List[str] = field(default_factory=list)
    roll_results: List[RollResult] = field(default_factory=list)
    damage_dealt: Dict[str, int] = field(default_factory=dict)  # target_id -> damage
    effects_applied: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    
    def add_roll_result(self, result: RollResult) -> None:
        """Add a roll result to this action."""
        self.roll_results.append(result)
    
    def add_damage(self, target_id: str, damage: int) -> None:
        """Record damage dealt to a target."""
        self.damage_dealt[target_id] = self.damage_dealt.get(target_id, 0) + damage
    
    def add_effect(self, effect: str) -> None:
        """Add an effect that was applied."""
        self.effects_applied.append(effect)


@dataclass
class InitiativeEntry:
    """Initiative tracker entry."""
    character_id: str
    character_name: str
    initiative_score: int
    initiative_modifier: int = 0
    roll_result: Optional[RollResult] = None
    has_acted: bool = False
    delay_count: int = 0
    
    def __lt__(self, other: 'InitiativeEntry') -> bool:
        """Compare initiative entries for sorting."""
        if self.initiative_score != other.initiative_score:
            return self.initiative_score > other.initiative_score  # Higher first
        return self.initiative_modifier > other.initiative_modifier  # Higher modifier wins ties


@dataclass
class CombatRound:
    """Represents one round of combat."""
    number: int
    actions: List[CombatAction] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    def add_action(self, action: CombatAction) -> None:
        """Add an action to this round."""
        self.actions.append(action)
    
    def end_round(self) -> None:
        """Mark this round as ended."""
        self.end_time = datetime.now()


@dataclass
class AttackResult:
    """Result of an attack roll and damage."""
    attack_roll: RollResult
    hit: bool
    critical: bool = False
    damage_rolls: List[RollResult] = field(default_factory=list)
    total_damage: int = 0
    damage_types: List[DamageType] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)


class CombatEngine(CombatEngineInterface):
    """Core combat engine implementing turn-based combat."""
    
    def __init__(self, dice_roller: Optional[DiceRoller] = None):
        self.dice_roller = dice_roller or default_roller
        
        # Combat state
        self.state: CombatState = CombatState.NOT_STARTED
        self.participants: Dict[str, CharacterInterface] = {}
        self.initiative_order: List[InitiativeEntry] = []
        self.current_turn_index: int = 0
        self.current_round: int = 0
        self.rounds: List[CombatRound] = []
        
        # Combat tracking
        self.combat_id: str = str(uuid.uuid4())
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Event callbacks
        self.callbacks: Dict[str, List[Callable]] = {
            'combat_start': [],
            'combat_end': [],
            'turn_start': [],
            'turn_end': [],
            'round_start': [],
            'round_end': [],
            'character_defeated': [],
            'damage_dealt': []
        }
    
    def add_participant(self, character: CharacterInterface) -> None:
        """Add a character to the combat."""
        if self.state != CombatState.NOT_STARTED:
            raise RPGEngineError("Cannot add participants after combat has started")
        
        self.participants[character.id] = character
        logger.info(f"Added {character.name} to combat")
    
    def remove_participant(self, character_id: str) -> None:
        """Remove a character from combat."""
        if character_id in self.participants:
            character_name = self.participants[character_id].name
            del self.participants[character_id]
            
            # Remove from initiative order
            self.initiative_order = [entry for entry in self.initiative_order 
                                   if entry.character_id != character_id]
            
            logger.info(f"Removed {character_name} from combat")
    
    def roll_initiative(self, characters: Optional[List[CharacterInterface]] = None) -> Dict[str, int]:
        """Roll initiative for all participants."""
        if characters is None:
            characters = list(self.participants.values())
        
        initiative_results = {}
        self.initiative_order.clear()
        
        for character in characters:
            # Calculate initiative modifier (usually Dex modifier)
            initiative_mod = 0
            if hasattr(character, 'get_attribute_modifier'):
                from .types import AttributeType
                initiative_mod = character.get_attribute_modifier(AttributeType.DEXTERITY)
            
            # Roll initiative
            dice_roll = DiceRoll(1, self.dice_roller.PRESET_ROLLS['d20'].dice_type, initiative_mod)
            roll_result = self.dice_roller.roll(dice_roll)
            
            # Create initiative entry
            entry = InitiativeEntry(
                character_id=character.id,
                character_name=character.name,
                initiative_score=roll_result.total,
                initiative_modifier=initiative_mod,
                roll_result=roll_result
            )
            
            self.initiative_order.append(entry)
            initiative_results[character.id] = roll_result.total
            
            logger.info(f"{character.name} rolled initiative: {roll_result.total} "
                       f"(d20: {roll_result.individual_rolls[0]} + {initiative_mod})")
        
        # Sort by initiative (highest first)
        self.initiative_order.sort()
        
        self.state = CombatState.INITIATIVE_PHASE
        return initiative_results
    
    def start_combat(self, participants: Optional[List[CharacterInterface]] = None) -> None:
        """Start the combat encounter."""
        if participants:
            for participant in participants:
                self.add_participant(participant)
        
        if not self.participants:
            raise RPGEngineError("Cannot start combat without participants")
        
        # Roll initiative if not done
        if self.state == CombatState.NOT_STARTED:
            self.roll_initiative()
        
        self.state = CombatState.ACTIVE
        self.current_round = 1
        self.current_turn_index = 0
        self.start_time = datetime.now()
        
        # Start first round
        self._start_new_round()
        
        logger.info(f"Combat started with {len(self.participants)} participants")
        self._trigger_callbacks('combat_start', combat=self)
    
    def next_turn(self) -> Optional[CharacterInterface]:
        """Advance to the next character's turn."""
        if self.state != CombatState.ACTIVE:
            return None
        
        # End current turn
        if self.initiative_order:
            current_entry = self.initiative_order[self.current_turn_index]
            current_entry.has_acted = True
            
            current_character = self.participants.get(current_entry.character_id)
            if current_character:
                self._trigger_callbacks('turn_end', character=current_character, combat=self)
        
        # Advance to next turn
        self.current_turn_index += 1
        
        # Check if round is complete
        if self.current_turn_index >= len(self.initiative_order):
            self._end_round()
            self._start_new_round()
        
        # Get next character
        if self.current_turn_index < len(self.initiative_order):
            next_entry = self.initiative_order[self.current_turn_index]
            next_character = self.participants.get(next_entry.character_id)
            
            if next_character:
                logger.info(f"It's {next_character.name}'s turn (Round {self.current_round})")
                self._trigger_callbacks('turn_start', character=next_character, combat=self)
                return next_character
        
        return None
    
    def get_current_character(self) -> Optional[CharacterInterface]:
        """Get the character whose turn it currently is."""
        if (self.state == CombatState.ACTIVE and 
            0 <= self.current_turn_index < len(self.initiative_order)):
            
            entry = self.initiative_order[self.current_turn_index]
            return self.participants.get(entry.character_id)
        
        return None
    
    def calculate_attack_roll(self, attacker: CharacterInterface, 
                            weapon: Equipment, target: Optional[CharacterInterface] = None) -> RollResult:
        """Calculate attack roll for a weapon."""
        # Determine attack attribute
        from .types import AttributeType
        attack_attr = AttributeType.STRENGTH
        
        if weapon.properties.get("ranged"):
            attack_attr = AttributeType.DEXTERITY
        elif weapon.properties.get("finesse"):
            # Use higher of STR or DEX
            if hasattr(attacker, 'get_attribute_modifier'):
                str_mod = attacker.get_attribute_modifier(AttributeType.STRENGTH)
                dex_mod = attacker.get_attribute_modifier(AttributeType.DEXTERITY)
                attack_attr = AttributeType.DEXTERITY if dex_mod > str_mod else AttributeType.STRENGTH
        
        # Calculate attack bonus
        attack_mod = 0
        if hasattr(attacker, 'get_attribute_modifier'):
            attack_mod = attacker.get_attribute_modifier(attack_attr)
        
        # Add proficiency bonus if proficient
        proficiency_bonus = 0
        if weapon.properties.get("proficient", True):
            proficiency_bonus = (attacker.level - 1) // 4 + 2  # Standard D&D progression
        
        # Add weapon's magic bonus
        magic_bonus = weapon.properties.get("attack_bonus", 0)
        
        total_bonus = attack_mod + proficiency_bonus + magic_bonus
        
        # Check for conditions affecting attacks
        advantage = False
        disadvantage = False
        
        for condition in attacker.conditions:
            if condition.type == ConditionType.POISONED:
                disadvantage = True
            elif condition.type == ConditionType.BLINDED:
                disadvantage = True
            # Add more condition effects as needed
        
        # Create and roll attack
        dice_roll = DiceRoll(1, self.dice_roller.PRESET_ROLLS['d20'].dice_type, 
                           total_bonus, advantage, disadvantage)
        
        result = self.dice_roller.roll(dice_roll)
        
        logger.info(f"{attacker.name} attack roll with {weapon.name}: {result.total}")
        
        return result
    
    def calculate_damage(self, attacker: CharacterInterface, weapon: Equipment, 
                        target: CharacterInterface, critical: bool = False) -> RollResult:
        """Calculate damage roll for a weapon."""
        # Get damage dice from weapon
        damage_dice = weapon.properties.get("damage_dice", "1d4")
        
        # Parse damage dice (simplified)
        if 'd' in damage_dice:
            parts = damage_dice.split('d')
            dice_count = int(parts[0])
            dice_sides = int(parts[1])
        else:
            dice_count, dice_sides = 1, 4
        
        # Map dice sides to DiceType
        from .types import DiceType
        dice_type_map = {4: DiceType.D4, 6: DiceType.D6, 8: DiceType.D8, 
                        10: DiceType.D10, 12: DiceType.D12, 20: DiceType.D20}
        dice_type = dice_type_map.get(dice_sides, DiceType.D6)
        
        # Critical hits double the dice
        if critical:
            dice_count *= 2
        
        # Determine damage attribute (same as attack attribute)
        from .types import AttributeType
        damage_attr = AttributeType.STRENGTH
        
        if weapon.properties.get("ranged"):
            damage_attr = AttributeType.DEXTERITY
        elif weapon.properties.get("finesse"):
            if hasattr(attacker, 'get_attribute_modifier'):
                str_mod = attacker.get_attribute_modifier(AttributeType.STRENGTH)
                dex_mod = attacker.get_attribute_modifier(AttributeType.DEXTERITY)
                damage_attr = AttributeType.DEXTERITY if dex_mod > str_mod else AttributeType.STRENGTH
        
        # Calculate damage modifier
        damage_mod = 0
        if hasattr(attacker, 'get_attribute_modifier'):
            damage_mod = attacker.get_attribute_modifier(damage_attr)
        
        # Add weapon's magic damage bonus
        magic_bonus = weapon.properties.get("damage_bonus", 0)
        total_modifier = damage_mod + magic_bonus
        
        # Roll damage
        dice_roll = DiceRoll(dice_count, dice_type, total_modifier)
        result = self.dice_roller.roll(dice_roll)
        
        logger.info(f"{attacker.name} damage roll with {weapon.name}: {result.total}")
        
        return result
    
    def make_attack(self, attacker: CharacterInterface, target: CharacterInterface,
                   weapon: Equipment) -> AttackResult:
        """Make a complete attack including roll, hit determination, and damage."""
        # Calculate target's AC
        target_ac = 10
        if hasattr(target, 'armor_class'):
            target_ac = target.armor_class
        elif hasattr(target, 'calculate_armor_class'):
            target_ac = target.calculate_armor_class()
        
        # Roll attack
        attack_roll = self.calculate_attack_roll(attacker, weapon, target)
        
        # Determine hit and critical
        hit = attack_roll.total >= target_ac
        critical = attack_roll.critical or False
        
        damage_rolls = []
        total_damage = 0
        
        if hit:
            # Roll damage
            damage_roll = self.calculate_damage(attacker, weapon, target, critical)
            damage_rolls.append(damage_roll)
            total_damage = max(0, damage_roll.total)  # Damage can't be negative
            
            # Apply damage
            if total_damage > 0:
                self.apply_damage(target, total_damage, 
                                DamageType(weapon.properties.get("damage_type", "bludgeoning")))
        
        result = AttackResult(
            attack_roll=attack_roll,
            hit=hit,
            critical=critical,
            damage_rolls=damage_rolls,
            total_damage=total_damage,
            damage_types=[DamageType(weapon.properties.get("damage_type", "bludgeoning"))],
        )
        
        # Log the attack
        hit_text = "HIT" if hit else "MISS"
        crit_text = " (CRITICAL)" if critical else ""
        damage_text = f" for {total_damage} damage" if hit else ""
        
        logger.info(f"{attacker.name} attacks {target.name}: {hit_text}{crit_text}{damage_text}")
        
        return result
    
    def apply_damage(self, target: CharacterInterface, damage: int, damage_type: DamageType) -> None:
        """Apply damage to a character."""
        if not hasattr(target, 'hit_points'):
            logger.warning(f"Cannot apply damage to {target.name} - no hit points")
            return
        
        # Apply resistances/immunities if implemented
        actual_damage = damage
        
        # Apply the damage
        if hasattr(target.hit_points, 'take_damage'):
            actual_damage = target.hit_points.take_damage(damage)
        else:
            # Fallback for basic damage application
            if hasattr(target.hit_points, 'current'):
                target.hit_points.current = max(0, target.hit_points.current - damage)
        
        logger.info(f"{target.name} takes {actual_damage} {damage_type.value} damage")
        
        # Check if character is defeated
        current_hp = getattr(target.hit_points, 'current', 0)
        if current_hp <= 0:
            self._character_defeated(target)
        
        self._trigger_callbacks('damage_dealt', target=target, damage=actual_damage, 
                              damage_type=damage_type, combat=self)
    
    def end_combat(self) -> None:
        """End the combat encounter."""
        if self.state != CombatState.ACTIVE:
            return
        
        self.state = CombatState.ENDED
        self.end_time = datetime.now()
        
        # End current round if active
        if self.rounds and not self.rounds[-1].end_time:
            self.rounds[-1].end_round()
        
        logger.info(f"Combat ended after {self.current_round} rounds")
        self._trigger_callbacks('combat_end', combat=self)
    
    def pause_combat(self) -> None:
        """Pause the combat encounter."""
        if self.state == CombatState.ACTIVE:
            self.state = CombatState.PAUSED
            logger.info("Combat paused")
    
    def resume_combat(self) -> None:
        """Resume a paused combat encounter."""
        if self.state == CombatState.PAUSED:
            self.state = CombatState.ACTIVE
            logger.info("Combat resumed")
    
    def add_callback(self, event: str, callback: Callable) -> None:
        """Add an event callback."""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def remove_callback(self, event: str, callback: Callable) -> None:
        """Remove an event callback."""
        if event in self.callbacks and callback in self.callbacks[event]:
            self.callbacks[event].remove(callback)
    
    def get_combat_summary(self) -> Dict[str, Any]:
        """Get a summary of the combat encounter."""
        return {
            "combat_id": self.combat_id,
            "state": self.state.value,
            "current_round": self.current_round,
            "participants": len(self.participants),
            "initiative_order": [
                {
                    "name": entry.character_name,
                    "initiative": entry.initiative_score,
                    "has_acted": entry.has_acted
                }
                for entry in self.initiative_order
            ],
            "current_character": self.get_current_character().name if self.get_current_character() else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "duration": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        }
    
    def _start_new_round(self) -> None:
        """Start a new combat round."""
        # Reset acted flags
        for entry in self.initiative_order:
            entry.has_acted = False
        
        self.current_turn_index = 0
        
        # Create new round
        new_round = CombatRound(self.current_round)
        self.rounds.append(new_round)
        
        logger.info(f"Starting Round {self.current_round}")
        self._trigger_callbacks('round_start', round_number=self.current_round, combat=self)
        
        # Start first character's turn
        if self.initiative_order:
            first_character = self.participants.get(self.initiative_order[0].character_id)
            if first_character:
                self._trigger_callbacks('turn_start', character=first_character, combat=self)
    
    def _end_round(self) -> None:
        """End the current round."""
        if self.rounds:
            self.rounds[-1].end_round()
        
        logger.info(f"Round {self.current_round} ended")
        self._trigger_callbacks('round_end', round_number=self.current_round, combat=self)
        
        self.current_round += 1
    
    def _character_defeated(self, character: CharacterInterface) -> None:
        """Handle character defeat."""
        logger.info(f"{character.name} has been defeated!")
        self._trigger_callbacks('character_defeated', character=character, combat=self)
        
        # Check if combat should end
        # This is a basic implementation - could be more sophisticated
        active_enemies = 0
        active_allies = 0
        
        for participant in self.participants.values():
            if hasattr(participant, 'hit_points') and participant.hit_points.current > 0:
                # This is a simplified check - in a real implementation,
                # you'd need to track which characters are on which side
                active_allies += 1
        
        if active_allies <= 1:  # Only one character left
            self.end_combat()
    
    def _trigger_callbacks(self, event: str, **kwargs) -> None:
        """Trigger all callbacks for an event."""
        for callback in self.callbacks.get(event, []):
            try:
                callback(**kwargs)
            except Exception as e:
                logger.error(f"Error in combat callback for {event}: {e}")


# Global combat engine instance
default_combat_engine = CombatEngine()


def start_combat(*participants: CharacterInterface) -> CombatEngine:
    """Convenience function to start a new combat encounter."""
    combat = CombatEngine()
    combat.start_combat(list(participants))
    return combat