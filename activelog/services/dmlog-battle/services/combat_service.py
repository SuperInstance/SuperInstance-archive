"""
Combat resolution and management service.
"""

import random
import math
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging

from ..models.base import (
    Position, DamageType, ActionType, CombatState, TurnPhase, 
    AttackRoll, DamageRoll, SavingThrow
)
from ..models.combat import (
    CombatEncounter, CombatAction, CombatRound, InitiativeEntry,
    AttackResult, SpellResult, CombatResolutionOptions, CriticalHitResult, FumbleResult
)
from ..models.combatant import CombatantSchema, DeathSavingThrows
from ..models.battlefield import BattlefieldSchema, AreaOfEffect
from ..services.grid_service import GridService
from ..config import Config

logger = logging.getLogger(__name__)

class CombatService:
    """Service for combat resolution and management."""
    
    def __init__(self):
        self.config = Config()
        self.grid_service = GridService()
        
    def create_encounter(
        self,
        name: str,
        battlefield: BattlefieldSchema,
        combatants: List[CombatantSchema],
        **kwargs
    ) -> CombatEncounter:
        """Create a new combat encounter."""
        
        encounter = CombatEncounter(
            id=str(uuid.uuid4()),
            name=name,
            battlefield=battlefield,
            combatants=combatants,
            state=CombatState.SETUP,
            **kwargs
        )
        
        # Initialize action economy for all combatants
        for combatant in combatants:
            if combatant.action_economy is None:
                combatant.action_economy = self._create_action_economy(combatant)
        
        return encounter
    
    def roll_initiative(self, encounter: CombatEncounter) -> None:
        """Roll initiative for all combatants and set turn order."""
        
        initiative_entries = []
        
        for combatant in encounter.combatants:
            if not combatant.is_alive():
                continue
            
            # Roll d20 + initiative modifier
            roll = random.randint(1, 20)
            modifier = combatant.initiative_modifier
            total = roll + modifier
            
            entry = InitiativeEntry(
                combatant_id=combatant.id,
                initiative_roll=roll,
                initiative_modifier=modifier,
                total_initiative=total
            )
            
            initiative_entries.append(entry)
            combatant.current_initiative = total
        
        # Sort by total initiative (highest first)
        initiative_entries.sort(key=lambda x: x.total_initiative, reverse=True)
        encounter.initiative_order = initiative_entries
        
        logger.info(f"Initiative rolled for encounter {encounter.id}")
    
    def start_combat(self, encounter: CombatEncounter) -> None:
        """Start the combat encounter."""
        
        if encounter.state != CombatState.SETUP:
            raise ValueError("Encounter must be in setup state to start")
        
        # Roll initiative if not already done
        if not encounter.initiative_order:
            self.roll_initiative(encounter)
        
        encounter.state = CombatState.ACTIVE
        encounter.current_round = 1
        encounter.current_turn = 0
        encounter.current_phase = TurnPhase.START
        encounter.started_at = datetime.utcnow()
        
        # Create first round
        encounter.rounds.append(CombatRound(round_number=1))
        
        # Reset action economy for all combatants
        for combatant in encounter.combatants:
            if combatant.action_economy:
                combatant.action_economy.reset_for_new_turn(combatant)
        
        logger.info(f"Combat started for encounter {encounter.id}")
    
    def process_turn(
        self,
        encounter: CombatEncounter,
        actions: List[CombatAction]
    ) -> List[CombatAction]:
        """Process a combatant's turn with their actions."""
        
        if encounter.state != CombatState.ACTIVE:
            raise ValueError("Combat must be active to process turns")
        
        results = []
        current_combatant = encounter.get_active_combatant()
        
        if not current_combatant:
            raise ValueError("No active combatant found")
        
        # Process each action
        for action in actions:
            if action.combatant_id != current_combatant.id:
                raise ValueError("Action must be from current combatant")
            
            result = self.resolve_action(encounter, action)
            results.append(result)
            
            # Add to encounter history
            encounter.action_history.append(result)
            
            # Add to current round
            if encounter.rounds:
                encounter.rounds[-1].actions.append(result)
        
        # Mark combatant as having acted
        if encounter.current_turn < len(encounter.initiative_order):
            encounter.initiative_order[encounter.current_turn].has_acted = True
        
        # Advance to next turn
        self._advance_turn(encounter)
        
        return results
    
    def resolve_action(
        self,
        encounter: CombatEncounter,
        action: CombatAction
    ) -> CombatAction:
        """Resolve a single combat action."""
        
        combatant = encounter.get_combatant_by_id(action.combatant_id)
        if not combatant:
            action.success = False
            action.failure_reason = "Combatant not found"
            return action
        
        # Set round and turn information
        action.round_number = encounter.current_round
        action.turn_number = encounter.current_turn
        
        try:
            if action.action_name.lower() == "attack":
                return self._resolve_attack_action(encounter, action, combatant)
            elif action.action_name.lower().startswith("spell"):
                return self._resolve_spell_action(encounter, action, combatant)
            elif action.action_name.lower() == "move":
                return self._resolve_movement_action(encounter, action, combatant)
            elif action.action_name.lower() == "dash":
                return self._resolve_dash_action(encounter, action, combatant)
            elif action.action_name.lower() == "dodge":
                return self._resolve_dodge_action(encounter, action, combatant)
            elif action.action_name.lower() == "help":
                return self._resolve_help_action(encounter, action, combatant)
            elif action.action_name.lower() == "ready":
                return self._resolve_ready_action(encounter, action, combatant)
            else:
                return self._resolve_special_action(encounter, action, combatant)
                
        except Exception as e:
            logger.error(f"Error resolving action {action.action_name}: {e}")
            action.success = False
            action.failure_reason = str(e)
            return action
    
    def _resolve_attack_action(
        self,
        encounter: CombatEncounter,
        action: CombatAction,
        attacker: CombatantSchema
    ) -> CombatAction:
        """Resolve an attack action."""
        
        if not action.target_ids:
            action.success = False
            action.failure_reason = "No target specified"
            return action
        
        target_id = action.target_ids[0]
        target = encounter.get_combatant_by_id(target_id)
        
        if not target or not target.is_alive():
            action.success = False
            action.failure_reason = "Invalid or dead target"
            return action
        
        # Get weapon (use first weapon or unarmed)
        weapon = attacker.weapons[0] if attacker.weapons else None
        
        # Calculate attack roll
        attack_bonus = weapon.attack_bonus if weapon else attacker.get_ability_modifier("strength")
        attack_bonus += attacker.proficiency_bonus  # Assume proficiency
        
        # Roll attack
        attack_roll = random.randint(1, 20)
        total_attack = attack_roll + attack_bonus
        
        action.attack_roll = attack_roll
        
        # Check for critical hit or fumble
        critical_range = weapon.critical_range if weapon else [20]
        
        if attack_roll in critical_range:
            action.critical_hit = True
        elif attack_roll == 1:
            action.critical_fumble = True
        
        # Check if hit
        target_ac = target.get_ac()
        action.hit = total_attack >= target_ac or action.critical_hit
        
        if action.hit:
            # Roll damage
            damage_rolls = weapon.damage_rolls if weapon else [
                DamageRoll(dice_count=1, dice_size=4, modifier=attacker.get_ability_modifier("strength"), 
                          damage_type=DamageType.BLUDGEONING)
            ]
            
            total_damage = 0
            for damage_roll in damage_rolls:
                damage = self._roll_damage(damage_roll, action.critical_hit)
                total_damage += damage
            
            # Apply damage
            actual_damage = target.take_damage(total_damage, damage_rolls[0].damage_type)
            action.damage_dealt[target_id] = actual_damage
            action.damage_roll = total_damage
            
            # Handle critical hit effects
            if action.critical_hit:
                crit_result = self._roll_critical_hit(weapon, damage_rolls[0].damage_type)
                if crit_result:
                    action.description += f" Critical Hit: {crit_result.description}"
                    # Apply additional effects
                    for condition in crit_result.conditions_applied:
                        target.add_condition(self._create_condition(condition))
        
        # Handle critical fumble
        if action.critical_fumble:
            fumble_result = self._roll_fumble("melee" if weapon and weapon.is_melee else "ranged")
            if fumble_result:
                action.description += f" Fumble: {fumble_result.description}"
                # Apply fumble effects to attacker
                if fumble_result.self_damage > 0:
                    attacker.take_damage(fumble_result.self_damage, DamageType.BLUDGEONING)
        
        action.success = True
        return action
    
    def _resolve_spell_action(
        self,
        encounter: CombatEncounter,
        action: CombatAction,
        caster: CombatantSchema
    ) -> CombatAction:
        """Resolve a spell action."""
        
        # This is a simplified spell resolution
        # In a full implementation, you'd look up the spell details
        
        spell_name = action.description or "Unknown Spell"
        
        # Check spell slots (simplified)
        if not caster.spell_slots or not any(slots > 0 for slots in caster.spell_slots.values()):
            action.success = False
            action.failure_reason = "No spell slots available"
            return action
        
        # Assume 1st level spell for simplicity
        if caster.spell_slots.get(1, 0) > 0:
            caster.spell_slots[1] -= 1
        
        # Handle different spell types
        if "heal" in spell_name.lower():
            return self._resolve_healing_spell(encounter, action, caster)
        elif "damage" in spell_name.lower() or "bolt" in spell_name.lower():
            return self._resolve_damage_spell(encounter, action, caster)
        else:
            return self._resolve_utility_spell(encounter, action, caster)
    
    def _resolve_movement_action(
        self,
        encounter: CombatEncounter,
        action: CombatAction,
        combatant: CombatantSchema
    ) -> CombatAction:
        """Resolve a movement action."""
        
        if not action.target_positions:
            action.success = False
            action.failure_reason = "No target position specified"
            return action
        
        target_pos = action.target_positions[0]
        
        if not combatant.position:
            action.success = False
            action.failure_reason = "Combatant has no current position"
            return action
        
        # Calculate movement path
        remaining_movement = combatant.action_economy.movement_remaining
        path = self.grid_service.calculate_movement_path(
            encounter.battlefield, combatant, combatant.position, target_pos, remaining_movement
        )
        
        if not path:
            action.success = False
            action.failure_reason = "No valid path found"
            return action
        
        # Calculate movement cost
        total_cost = 0
        for i in range(len(path) - 1):
            cost = self.grid_service._get_movement_cost(
                encounter.battlefield, path[i], path[i + 1], combatant
            )
            total_cost += cost
        
        if total_cost > remaining_movement:
            action.success = False
            action.failure_reason = "Insufficient movement"
            return action
        
        # Check for opportunity attacks
        all_combatants = [c for c in encounter.combatants if c.is_alive()]
        opportunity_attacks = self.grid_service.calculate_opportunity_attacks(
            encounter.battlefield, combatant, path, all_combatants
        )
        
        # Update position
        combatant.position = target_pos
        combatant.action_economy.use_movement(total_cost)
        
        action.success = True
        action.description = f"Moved to position ({target_pos.x}, {target_pos.y})"
        
        # Process opportunity attacks
        for attacker_id, attack_pos in opportunity_attacks:
            # This would trigger opportunity attack actions
            pass
        
        return action
    
    def _resolve_dash_action(
        self,
        encounter: CombatEncounter,
        action: CombatAction,
        combatant: CombatantSchema
    ) -> CombatAction:
        """Resolve a dash action (double movement)."""
        
        if not combatant.action_economy.use_action():
            action.success = False
            action.failure_reason = "No action available"
            return action
        
        # Double remaining movement
        combatant.action_economy.movement_remaining += combatant.get_speed()
        
        action.success = True
        action.description = "Dashed - movement doubled"
        return action
    
    def _resolve_dodge_action(
        self,
        encounter: CombatEncounter,
        action: CombatAction,
        combatant: CombatantSchema
    ) -> CombatAction:
        """Resolve a dodge action."""
        
        if not combatant.action_economy.use_action():
            action.success = False
            action.failure_reason = "No action available"
            return action
        
        # Apply dodging condition until start of next turn
        dodge_condition = self._create_condition("dodging")
        combatant.add_condition(dodge_condition)
        
        action.success = True
        action.description = "Dodging - attacks have disadvantage"
        return action
    
    def _resolve_help_action(
        self,
        encounter: CombatEncounter,
        action: CombatAction,
        helper: CombatantSchema
    ) -> CombatAction:
        """Resolve a help action."""
        
        if not helper.action_economy.use_action():
            action.success = False
            action.failure_reason = "No action available"
            return action
        
        if not action.target_ids:
            action.success = False
            action.failure_reason = "No target specified to help"
            return action
        
        target = encounter.get_combatant_by_id(action.target_ids[0])
        if not target:
            action.success = False
            action.failure_reason = "Invalid target"
            return action
        
        # Apply help condition
        help_condition = self._create_condition("helped")
        target.add_condition(help_condition)
        
        action.success = True
        action.description = f"Helped {target.name} - next action has advantage"
        return action
    
    def _resolve_ready_action(
        self,
        encounter: CombatEncounter,
        action: CombatAction,
        combatant: CombatantSchema
    ) -> CombatAction:
        """Resolve a ready action."""
        
        if not combatant.action_economy.use_action():
            action.success = False
            action.failure_reason = "No action available"
            return action
        
        # Store readied action in initiative entry
        for entry in encounter.initiative_order:
            if entry.combatant_id == combatant.id:
                entry.readied_action = action
                break
        
        action.success = True
        action.description = "Action readied"
        return action
    
    def _resolve_special_action(
        self,
        encounter: CombatEncounter,
        action: CombatAction,
        combatant: CombatantSchema
    ) -> CombatAction:
        """Resolve a special ability action."""
        
        # Find the special ability
        ability = None
        for ability_item in combatant.special_abilities:
            if ability_item.name.lower() == action.action_name.lower():
                ability = ability_item
                break
        
        if not ability:
            action.success = False
            action.failure_reason = f"Special ability '{action.action_name}' not found"
            return action
        
        # Check uses remaining
        if ability.uses_per_day > 0 and ability.uses_remaining <= 0:
            action.success = False
            action.failure_reason = "No uses remaining for this ability"
            return action
        
        # Use appropriate action type
        if ability.action_type == ActionType.ACTION and not combatant.action_economy.use_action():
            action.success = False
            action.failure_reason = "No action available"
            return action
        elif ability.action_type == ActionType.BONUS_ACTION and not combatant.action_economy.use_bonus_action():
            action.success = False
            action.failure_reason = "No bonus action available"
            return action
        
        # Consume use
        if ability.uses_per_day > 0:
            ability.uses_remaining -= 1
        
        # Apply ability effects (simplified)
        if ability.damage_rolls:
            return self._resolve_ability_damage(encounter, action, combatant, ability)
        elif ability.healing_rolls:
            return self._resolve_ability_healing(encounter, action, combatant, ability)
        else:
            return self._resolve_ability_utility(encounter, action, combatant, ability)
    
    def _advance_turn(self, encounter: CombatEncounter) -> None:
        """Advance to the next turn or round."""
        
        encounter.current_turn += 1
        
        # Check if round is complete
        if encounter.current_turn >= len(encounter.initiative_order):
            # Start new round
            encounter.current_round += 1
            encounter.current_turn = 0
            
            # End current round
            if encounter.rounds:
                encounter.rounds[-1].end_time = datetime.utcnow()
            
            # Start new round
            new_round = CombatRound(round_number=encounter.current_round)
            encounter.rounds.append(new_round)
            
            # Reset actions for all combatants
            for combatant in encounter.combatants:
                if combatant.action_economy:
                    combatant.action_economy.reset_for_new_turn(combatant)
                
                # Process condition durations
                self._process_condition_durations(combatant)
            
            # Process environmental effects
            self._process_environmental_effects(encounter)
            
            # Reset initiative entries
            for entry in encounter.initiative_order:
                entry.has_acted = False
        
        # Check if combat is over
        if encounter.is_combat_over():
            self._end_combat(encounter)
    
    def _end_combat(self, encounter: CombatEncounter) -> None:
        """End the combat encounter."""
        
        encounter.state = CombatState.COMPLETED
        encounter.ended_at = datetime.utcnow()
        encounter.total_rounds = encounter.current_round
        
        if encounter.started_at and encounter.ended_at:
            encounter.actual_duration = (encounter.ended_at - encounter.started_at).total_seconds()
        
        # Determine victor
        living_types = set()
        for combatant in encounter.combatants:
            if combatant.is_alive():
                living_types.add(combatant.creature_type.value)
        
        if "player_character" in living_types and len(living_types) == 1:
            encounter.victor = "players"
        elif len(living_types) == 1:
            encounter.victor = list(living_types)[0]
        else:
            encounter.victor = "draw"
        
        # Record casualties
        encounter.casualties = [
            c.id for c in encounter.combatants if not c.is_alive()
        ]
        
        logger.info(f"Combat ended for encounter {encounter.id}. Victor: {encounter.victor}")
    
    def _roll_damage(self, damage_roll: DamageRoll, critical_hit: bool = False) -> int:
        """Roll damage dice."""
        
        if damage_roll.dice_count == 0:
            return damage_roll.modifier
        
        total = 0
        dice_to_roll = damage_roll.dice_count
        
        # Critical hits double dice
        if critical_hit:
            dice_to_roll *= 2
        
        # Roll dice
        for _ in range(dice_to_roll):
            total += random.randint(1, damage_roll.die_size)
        
        # Add modifier once
        return total + damage_roll.modifier
    
    def _process_condition_durations(self, combatant: CombatantSchema) -> None:
        """Process condition durations at end of turn."""
        
        conditions_to_remove = []
        for condition in combatant.conditions:
            if condition.duration_rounds > 0:
                condition.duration_rounds -= 1
                if condition.duration_rounds <= 0:
                    conditions_to_remove.append(condition.name)
        
        # Remove expired conditions
        for condition_name in conditions_to_remove:
            combatant.remove_condition(condition_name)
    
    def _process_environmental_effects(self, encounter: CombatEncounter) -> None:
        """Process environmental hazards and effects."""
        
        for hazard in encounter.battlefield.hazards:
            if hazard.active and "start_turn" in hazard.triggers_on:
                # Apply hazard damage to creatures in affected positions
                for combatant in encounter.combatants:
                    if (combatant.position and 
                        combatant.position in hazard.affected_positions and
                        combatant.is_alive()):
                        
                        # Roll hazard damage
                        for damage_dice in hazard.damage_per_turn:
                            damage = self._roll_hazard_damage(damage_dice)
                            
                            # Apply saving throw if applicable
                            if hazard.save_dc and hazard.save_ability:
                                save_roll = random.randint(1, 20)
                                save_bonus = combatant.get_save_bonus(hazard.save_ability)
                                if save_roll + save_bonus >= hazard.save_dc:
                                    damage = damage // 2
                            
                            # Apply damage (assuming fire damage for most hazards)
                            combatant.take_damage(damage, DamageType.FIRE)
    
    def _roll_hazard_damage(self, damage_dice: str) -> int:
        """Roll damage for environmental hazards."""
        
        # Parse dice string like "2d6" or "1d4+2"
        parts = damage_dice.split('+')
        dice_part = parts[0]
        modifier = int(parts[1]) if len(parts) > 1 else 0
        
        if 'd' in dice_part:
            num_dice, die_size = map(int, dice_part.split('d'))
            total = sum(random.randint(1, die_size) for _ in range(num_dice))
            return total + modifier
        else:
            return int(dice_part) + modifier
    
    def _resolve_ability_damage(
        self,
        encounter: CombatEncounter,
        action: CombatAction,
        combatant: CombatantSchema,
        ability: SpecialAbility
    ) -> CombatAction:
        """Resolve damage-dealing special ability."""
        
        for target_id in action.target_ids:
            target = encounter.get_combatant_by_id(target_id)
            if not target or not target.is_alive():
                continue
            
            # Roll damage for each damage roll
            total_damage = 0
            for damage_roll in ability.damage_rolls:
                damage = self._roll_damage(damage_roll)
                total_damage += damage
            
            # Apply damage
            actual_damage = target.take_damage(total_damage, damage_roll.damage_type)
            action.damage_dealt[target_id] = actual_damage
        
        action.success = True
        return action
    
    def _resolve_ability_healing(
        self,
        encounter: CombatEncounter,
        action: CombatAction,
        combatant: CombatantSchema,
        ability: SpecialAbility
    ) -> CombatAction:
        """Resolve healing special ability."""
        
        for target_id in action.target_ids:
            target = encounter.get_combatant_by_id(target_id)
            if not target or not target.is_alive():
                continue
            
            # Roll healing for each healing roll
            total_healing = 0
            for healing_roll in ability.healing_rolls:
                healing = self._roll_damage(healing_roll)  # Same mechanics as damage
                total_healing += healing
            
            # Apply healing
            actual_healing = target.heal(total_healing)
            # Store as negative damage to indicate healing
            action.damage_dealt[target_id] = -actual_healing
        
        action.success = True
        return action
    
    def _resolve_ability_utility(
        self,
        encounter: CombatEncounter,
        action: CombatAction,
        combatant: CombatantSchema,
        ability: SpecialAbility
    ) -> CombatAction:
        """Resolve utility special ability."""
        
        # Apply conditions to targets
        for target_id in action.target_ids:
            target = encounter.get_combatant_by_id(target_id)
            if not target:
                continue
            
            # Apply conditions from ability
            for condition_name in ability.conditions_applied:
                from ..models.base import Condition
                condition = Condition(
                    name=condition_name,
                    duration_rounds=10  # Default duration
                )
                target.add_condition(condition)
                action.conditions_applied.append(condition_name)
        
        action.success = True
        return action
    
    def run_automated_combat(
        self,
        encounter: CombatEncounter,
        options: CombatResolutionOptions = None
    ) -> CombatEncounter:
        """Run fully automated combat resolution."""
        
        if not options:
            options = CombatResolutionOptions()
        
        logger.info(f"Starting automated combat for encounter {encounter.id}")
        
        # Start combat if not already started
        if encounter.state == CombatState.SETUP:
            self.start_combat(encounter)
        
        combat_rounds = 0
        max_rounds = options.max_rounds
        
        # Main combat loop
        while (encounter.state == CombatState.ACTIVE and 
               not encounter.is_combat_over() and 
               combat_rounds < max_rounds):
            
            current_combatant = encounter.get_active_combatant()
            if not current_combatant:
                break
            
            # Skip if combatant is dead or incapacitated
            if not current_combatant.can_take_actions():
                self._advance_turn(encounter)
                continue
            
            # Generate AI action
            ai_action = self._generate_ai_action(
                encounter, current_combatant, options
            )
            
            if ai_action:
                # Resolve the action
                resolved_action = self.resolve_action(encounter, ai_action)
                
                # Add to encounter history
                encounter.action_history.append(resolved_action)
                if encounter.rounds:
                    encounter.rounds[-1].actions.append(resolved_action)
            
            # Advance turn
            self._advance_turn(encounter)
            
            # Track rounds for safety
            if encounter.current_turn == 0:
                combat_rounds += 1
        
        # Handle timeout
        if combat_rounds >= max_rounds:
            encounter.state = CombatState.COMPLETED
            encounter.victor = "timeout"
            logger.warning(f"Combat timed out after {max_rounds} rounds")
        
        logger.info(f"Automated combat completed for encounter {encounter.id}")
        return encounter
    
    def _generate_ai_action(
        self,
        encounter: CombatEncounter,
        combatant: CombatantSchema,
        options: CombatResolutionOptions
    ) -> Optional[CombatAction]:
        """Generate an AI action for a combatant."""
        
        # Use AI for appropriate creature types
        should_use_ai = False
        if combatant.creature_type.value == "monster" and options.use_ai_for_monsters:
            should_use_ai = True
        elif combatant.creature_type.value == "npc" and options.use_ai_for_npcs:
            should_use_ai = True
        elif combatant.creature_type.value == "player_character" and options.use_ai_for_pcs:
            should_use_ai = True
        
        if not should_use_ai:
            return None
        
        # Find valid targets
        enemies = []
        for other in encounter.combatants:
            if (other.id != combatant.id and 
                other.creature_type != combatant.creature_type and
                other.is_alive() and other.position):
                enemies.append(other)
        
        if not enemies:
            # No valid targets, take dodge action
            return CombatAction(
                combatant_id=combatant.id,
                action_type=ActionType.ACTION,
                action_name="dodge",
                round_number=encounter.current_round,
                turn_number=encounter.current_turn,
                automatic=True
            )
        
        # Simple AI: attack the closest enemy
        closest_enemy = min(enemies, 
            key=lambda e: combatant.position.distance_to(e.position) if e.position else float('inf'))
        
        # Choose action type based on what's available
        if combatant.weapons:
            # Use weapon attack
            weapon = combatant.weapons[0]
            return CombatAction(
                combatant_id=combatant.id,
                action_type=ActionType.ACTION,
                action_name="attack",
                target_ids=[closest_enemy.id],
                round_number=encounter.current_round,
                turn_number=encounter.current_turn,
                automatic=True
            )
        
        elif combatant.spells_known:
            # Use spell attack
            damage_spells = [s for s in combatant.spells_known 
                           if s.school == "evocation" and s.damage_dice]
            
            if damage_spells and combatant.spell_slots.get(1, 0) > 0:
                spell = damage_spells[0]
                return CombatAction(
                    combatant_id=combatant.id,
                    action_type=ActionType.ACTION,
                    action_name="spell",
                    target_ids=[closest_enemy.id],
                    target_positions=[closest_enemy.position] if closest_enemy.position else [],
                    round_number=encounter.current_round,
                    turn_number=encounter.current_turn,
                    automatic=True
                )
        
        # Default to dodge
        return CombatAction(
            combatant_id=combatant.id,
            action_type=ActionType.ACTION,
            action_name="dodge",
            round_number=encounter.current_round,
            turn_number=encounter.current_turn,
            automatic=True
        )
    
    def _roll_critical_hit(
        self,
        weapon: Optional[Any],
        damage_type: DamageType
    ) -> Optional[CriticalHitResult]:
        """Roll on critical hit table."""
        
        if not self.config.CRITICAL_TABLES["critical_hits"]:
            return None
        
        weapon_type = damage_type.value
        if weapon_type in self.config.CRITICAL_TABLES["critical_hits"]:
            effects = self.config.CRITICAL_TABLES["critical_hits"][weapon_type]
            effect = random.choice(effects)
            
            return CriticalHitResult(
                weapon_type=weapon_type,
                description=effect
            )
        
        return None
    
    def _roll_fumble(self, action_type: str) -> Optional[FumbleResult]:
        """Roll on fumble table."""
        
        if action_type in self.config.CRITICAL_TABLES["fumbles"]:
            effects = self.config.CRITICAL_TABLES["fumbles"][action_type]
            effect = random.choice(effects)
            
            return FumbleResult(
                action_type=action_type,
                description=effect
            )
        
        return None
    
    def _create_condition(self, condition_name: str) -> Any:
        """Create a condition object."""
        # This would create appropriate condition objects
        # For now, return a simple placeholder
        from ..models.base import Condition
        return Condition(name=condition_name, duration=1)
    
    def _create_action_economy(self, combatant: CombatantSchema) -> Any:
        """Create action economy for combatant."""
        from ..models.combatant import ActionEconomy
        economy = ActionEconomy()
        economy.reset_for_new_turn(combatant)
        return economy
    
    def _process_condition_durations(self, combatant: CombatantSchema) -> None:
        """Process condition durations at start of turn."""
        
        conditions_to_remove = []
        
        for condition in combatant.conditions:
            if condition.duration > 0:
                condition.duration -= 1
                if condition.duration == 0:
                    conditions_to_remove.append(condition.name)
        
        # Remove expired conditions
        for condition_name in conditions_to_remove:
            combatant.remove_condition(condition_name)
    
    def _process_environmental_effects(self, encounter: CombatEncounter) -> None:
        """Process environmental hazards and effects."""
        
        for hazard in encounter.battlefield.hazards:
            if not hazard.active:
                continue
            
            # Check which combatants are affected
            for combatant in encounter.combatants:
                if not combatant.position or not combatant.is_alive():
                    continue
                
                if combatant.position in hazard.affected_positions:
                    # Apply hazard damage
                    if hazard.damage_per_turn:
                        # Parse damage string and apply
                        # This is simplified - would need full dice parsing
                        damage = random.randint(1, 6)  # Placeholder
                        combatant.take_damage(damage, DamageType.FIRE)  # Placeholder type
    
    def calculate_encounter_difficulty(
        self,
        party_level: int,
        party_size: int,
        monsters: List[Dict[str, Any]]
    ) -> str:
        """Calculate encounter difficulty rating."""
        
        # Simplified encounter difficulty calculation
        # Based on D&D 5e encounter building rules
        
        xp_thresholds = {
            1: [25, 50, 75, 100],
            2: [50, 100, 150, 200],
            3: [75, 150, 225, 400],
            4: [125, 250, 375, 500],
            5: [250, 500, 750, 1100],
            # ... more levels would be added
        }
        
        if party_level not in xp_thresholds:
            return "unknown"
        
        easy, medium, hard, deadly = xp_thresholds[party_level]
        
        # Adjust for party size
        if party_size != 4:
            multiplier = party_size / 4
            easy = int(easy * multiplier)
            medium = int(medium * multiplier)
            hard = int(hard * multiplier)
            deadly = int(deadly * multiplier)
        
        # Calculate monster XP (simplified)
        total_xp = sum(monster.get("xp", 100) for monster in monsters)
        
        # Apply encounter multiplier for multiple monsters
        if len(monsters) >= 7:
            total_xp = int(total_xp * 2.5)
        elif len(monsters) >= 3:
            total_xp = int(total_xp * 1.5)
        elif len(monsters) == 2:
            total_xp = int(total_xp * 1.5)
        
        # Determine difficulty
        if total_xp < easy:
            return "easy"
        elif total_xp < medium:
            return "medium"
        elif total_xp < hard:
            return "hard"
        else:
            return "deadly"
    
    # Additional helper methods would be implemented here for:
    # - Healing spells
    # - Damage spells
    # - Utility spells
    # - Ability damage/healing/utility
    # - Death saving throws
    # - Mounted combat
    # - Mass combat
    # - Etc.