"""
Mounted combat rules and mechanics service.
"""

import random
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from ..models.base import Position, CreatureSize, ActionType, DamageType
from ..models.combatant import CombatantSchema, Mount
from ..models.combat import CombatEncounter, CombatAction
from ..config import Config

logger = logging.getLogger(__name__)

@dataclass
class MountedCombatAction:
    """Special action for mounted combat."""
    rider_id: str
    mount_id: str
    action_type: str  # mount_attack, controlled_mount, dismount, etc.
    mount_action: Optional[str] = None
    success: bool = True
    description: str = ""
    effects: List[str] = None
    
    def __post_init__(self):
        if self.effects is None:
            self.effects = []

@dataclass
class MountingResult:
    """Result of mounting or dismounting."""
    rider_id: str
    mount_id: str
    action_type: str  # mount, dismount
    success: bool
    reason: str
    movement_used: int = 0
    provokes_opportunity_attacks: bool = False

class MountedCombatService:
    """Service for handling mounted combat mechanics."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
    
    def mount_creature(
        self,
        encounter: CombatEncounter,
        rider: CombatantSchema,
        mount_target: CombatantSchema
    ) -> MountingResult:
        """Attempt to mount a creature."""
        
        # Validate mounting is possible
        validation_result = self._validate_mounting(rider, mount_target)
        if not validation_result[0]:
            return MountingResult(
                rider_id=rider.id,
                mount_id=mount_target.id,
                action_type="mount",
                success=False,
                reason=validation_result[1]
            )
        
        # Check if mount is willing (for controlled mounts)
        if mount_target.creature_type.value in ["player_character", "npc"]:
            # Require consent for PC/NPC mounts
            # This would typically require player/GM input
            pass
        
        # Mounting uses half movement
        movement_cost = rider.get_speed() // 2
        if not rider.action_economy.use_movement(movement_cost):
            return MountingResult(
                rider_id=rider.id,
                mount_id=mount_target.id,
                action_type="mount",
                success=False,
                reason="Not enough movement remaining",
                movement_used=0
            )
        
        # Create mount relationship
        mount = Mount(
            id=mount_target.id,
            name=mount_target.name,
            size=mount_target.size,
            speed=mount_target.stats.speed,
            armor_class=mount_target.stats.armor_class,
            hit_points=mount_target.stats.hit_points,
            max_hit_points=mount_target.stats.max_hit_points,
            abilities=mount_target.abilities,
            mount_type=self._determine_mount_type(mount_target),
            intelligence=mount_target.abilities.intelligence,
            can_attack=self._can_mount_attack(mount_target),
            natural_attacks=self._get_natural_attacks(mount_target),
            is_controlled=self._is_controlled_mount(mount_target),
            shares_initiative=True,
            conditions=mount_target.conditions.copy()
        )
        
        # Set up mounted relationship
        rider.mount = mount
        rider.is_mounted = True
        
        # Mount and rider share position
        if mount_target.position:
            rider.position = mount_target.position
        
        # Remove mount from separate initiative (they share now)
        encounter.initiative_order = [
            entry for entry in encounter.initiative_order 
            if entry.combatant_id != mount_target.id
        ]
        
        logger.info(f"{rider.name} mounted {mount_target.name}")
        
        return MountingResult(
            rider_id=rider.id,
            mount_id=mount_target.id,
            action_type="mount",
            success=True,
            reason="Successfully mounted",
            movement_used=movement_cost
        )
    
    def dismount_creature(
        self,
        encounter: CombatEncounter,
        rider: CombatantSchema,
        forced: bool = False
    ) -> MountingResult:
        """Dismount from a creature."""
        
        if not rider.is_mounted or not rider.mount:
            return MountingResult(
                rider_id=rider.id,
                mount_id="",
                action_type="dismount",
                success=False,
                reason="Not currently mounted"
            )
        
        mount_id = rider.mount.id
        mount_name = rider.mount.name
        
        if not forced:
            # Voluntary dismount uses half movement
            movement_cost = rider.get_speed() // 2
            if not rider.action_economy.use_movement(movement_cost):
                return MountingResult(
                    rider_id=rider.id,
                    mount_id=mount_id,
                    action_type="dismount",
                    success=False,
                    reason="Not enough movement remaining"
                )
        else:
            movement_cost = 0
        
        # Find adjacent empty position for dismounting
        if rider.position:
            adjacent_positions = rider.position.adjacent_positions()
            empty_position = None
            
            for pos in adjacent_positions:
                if self._is_position_empty(encounter, pos):
                    empty_position = pos
                    break
            
            if not empty_position:
                # Force dismount in current position if no adjacent space
                empty_position = rider.position
        
        # Restore mount as separate combatant
        mount_combatant = self._restore_mount_combatant(encounter, rider.mount)
        if mount_combatant and empty_position:
            # Place mount in an adjacent position if possible
            mount_positions = rider.position.adjacent_positions()
            mount_position = None
            for pos in mount_positions:
                if self._is_position_empty(encounter, pos) and pos != empty_position:
                    mount_position = pos
                    break
            
            mount_combatant.position = mount_position or rider.position
        
        # Clear mounted status
        rider.mount = None
        rider.is_mounted = False
        rider.position = empty_position
        
        # Add mount back to initiative if it was controlled
        if mount_combatant and not rider.mount.is_controlled:
            self._add_mount_to_initiative(encounter, mount_combatant)
        
        logger.info(f"{rider.name} dismounted from {mount_name}")
        
        return MountingResult(
            rider_id=rider.id,
            mount_id=mount_id,
            action_type="dismount",
            success=True,
            reason="Successfully dismounted",
            movement_used=movement_cost,
            provokes_opportunity_attacks=forced
        )
    
    def resolve_mounted_movement(
        self,
        encounter: CombatEncounter,
        rider: CombatantSchema,
        target_position: Position,
        use_mount_speed: bool = True
    ) -> Tuple[bool, str, int]:
        """Handle movement for mounted combatants."""
        
        if not rider.is_mounted or not rider.mount:
            return False, "Not mounted", 0
        
        # Use mount's speed if controlled, otherwise rider's speed
        speed = rider.mount.speed if use_mount_speed and rider.mount.is_controlled else rider.get_speed()
        
        # Calculate movement cost
        if not rider.position:
            return False, "No current position", 0
        
        distance_feet = rider.position.distance_to(target_position) * encounter.battlefield.square_size_feet
        
        if distance_feet > speed:
            return False, f"Distance {distance_feet} exceeds speed {speed}", 0
        
        # Check for opportunity attacks (mount provokes, not rider)
        grid_service = encounter._grid_service if hasattr(encounter, '_grid_service') else None
        provokes_attacks = False
        
        if grid_service:
            # This would use the grid service to check opportunity attacks
            pass
        
        # Move both rider and mount
        rider.position = target_position
        if rider.mount:
            # Mount position is same as rider
            pass
        
        return True, "Movement successful", int(distance_feet)
    
    def resolve_mounted_attack(
        self,
        encounter: CombatEncounter,
        action: CombatAction,
        rider: CombatantSchema
    ) -> MountedCombatAction:
        """Resolve attacks while mounted."""
        
        if not rider.is_mounted or not rider.mount:
            return MountedCombatAction(
                rider_id=rider.id,
                mount_id="",
                action_type="mounted_attack",
                success=False,
                description="Not mounted"
            )
        
        mount_action = MountedCombatAction(
            rider_id=rider.id,
            mount_id=rider.mount.id,
            action_type="mounted_attack",
            success=True,
            description="Mounted attack"
        )
        
        # Check for advantage on melee attacks against unmounted creatures
        if action.action_name.lower() == "attack" and rider.weapons:
            weapon = rider.weapons[0] if rider.weapons else None
            
            if weapon and hasattr(weapon, 'range_feet') and weapon.range_feet <= 10:
                # Melee attack - check if target is smaller and unmounted
                target_id = action.target_ids[0] if action.target_ids else None
                if target_id:
                    target = encounter.get_combatant_by_id(target_id)
                    if target and not target.is_mounted:
                        # Get size comparison
                        rider_size_value = self._get_size_value(rider.size)
                        target_size_value = self._get_size_value(target.size)
                        
                        if rider_size_value > target_size_value:
                            mount_action.effects.append("Advantage on melee attack (mounted vs unmounted)")
                            action.advantage = True
        
        # Check for mount attacks (if mount can attack)
        if rider.mount.can_attack and rider.mount.natural_attacks:
            if rider.mount.is_controlled:
                # Controlled mount can attack if rider uses action to command it
                if action.action_name.lower() == "attack" and action.mount_action == "attack":
                    mount_action.mount_action = "attack"
                    mount_action.effects.append("Mount attacks with natural weapons")
            else:
                # Independent mount acts on its own
                mount_action.mount_action = "independent_attack"
                mount_action.effects.append("Independent mount may attack")
        
        return mount_action
    
    def handle_mount_damage(
        self,
        encounter: CombatEncounter,
        mount: Mount,
        damage: int,
        damage_type: DamageType
    ) -> Tuple[int, List[str]]:
        """Handle damage to a mount and potential rider effects."""
        
        effects = []
        
        # Apply damage to mount
        original_hp = mount.hit_points
        
        # Apply resistances/immunities (simplified)
        actual_damage = damage
        
        mount.hit_points = max(0, mount.hit_points - actual_damage)
        
        # Check for mount death
        if mount.hit_points <= 0 and original_hp > 0:
            effects.append("Mount killed")
            
            # Rider must make a DC 15 Dexterity saving throw or be dismounted
            rider = self._find_rider_for_mount(encounter, mount.id)
            if rider:
                save_roll = random.randint(1, 20)
                save_bonus = rider.get_save_bonus("dexterity")
                
                if save_roll + save_bonus < 15:
                    # Forced dismount
                    self.dismount_creature(encounter, rider, forced=True)
                    effects.append("Rider dismounted due to mount death")
                    
                    # Rider takes damage
                    fall_damage = random.randint(1, 6)
                    rider.take_damage(fall_damage, DamageType.BLUDGEONING)
                    effects.append(f"Rider takes {fall_damage} fall damage")
        
        # Check for mount incapacitation
        elif mount.hit_points <= mount.max_hit_points // 4:
            # Mount is badly wounded - check for panic/control issues
            if not mount.is_controlled:
                effects.append("Mount may panic or become difficult to control")
        
        return actual_damage, effects
    
    def check_mount_panic(
        self,
        encounter: CombatEncounter,
        mount: Mount,
        trigger: str
    ) -> Tuple[bool, List[str]]:
        """Check if mount panics due to various triggers."""
        
        effects = []
        panics = False
        
        # Base panic DC based on mount intelligence and type
        base_dc = 10
        
        # Modify DC based on trigger
        trigger_modifiers = {
            "fire": 5,      # Horses fear fire
            "loud_noise": 3,
            "combat": 2,
            "injury": 4,
            "death_nearby": 6
        }
        
        dc = base_dc + trigger_modifiers.get(trigger, 0)
        
        # Mount makes a Wisdom saving throw
        save_roll = random.randint(1, 20)
        wisdom_modifier = (mount.abilities.wisdom - 10) // 2
        
        if save_roll + wisdom_modifier < dc:
            panics = True
            mount.panicked = True
            effects.append(f"Mount panicked due to {trigger}")
            
            # Rider must make Animal Handling check to regain control
            rider = self._find_rider_for_mount(encounter, mount.id)
            if rider:
                effects.append("Rider must make Animal Handling check to regain control")
        
        return panics, effects
    
    def handle_animal_handling(
        self,
        rider: CombatantSchema,
        mount: Mount,
        dc: int = 15
    ) -> Tuple[bool, str]:
        """Handle Animal Handling check to control mount."""
        
        handling_roll = random.randint(1, 20)
        wisdom_modifier = rider.get_ability_modifier("wisdom")
        proficiency = rider.proficiency_bonus  # Assuming proficiency in Animal Handling
        
        total = handling_roll + wisdom_modifier + proficiency
        
        if total >= dc:
            mount.panicked = False
            return True, f"Successfully controlled mount (rolled {total} vs DC {dc})"
        else:
            return False, f"Failed to control mount (rolled {total} vs DC {dc})"
    
    def _validate_mounting(
        self,
        rider: CombatantSchema,
        mount_target: CombatantSchema
    ) -> Tuple[bool, str]:
        """Validate that mounting is possible."""
        
        # Check if already mounted
        if rider.is_mounted:
            return False, "Already mounted"
        
        # Check if target is already a mount
        if mount_target.is_mounted:
            return False, "Target is already mounted"
        
        # Check size restrictions
        rider_size_value = self._get_size_value(rider.size)
        mount_size_value = self._get_size_value(mount_target.size)
        
        if rider_size_value >= mount_size_value:
            return False, "Rider must be at least one size smaller than mount"
        
        # Check if mount is alive and conscious
        if not mount_target.is_alive() or not mount_target.is_conscious():
            return False, "Mount must be alive and conscious"
        
        # Check proximity
        if rider.position and mount_target.position:
            distance = rider.position.distance_to(mount_target.position)
            if distance > 1:  # Must be adjacent
                return False, "Must be adjacent to mount"
        
        # Check if mount is suitable (has appropriate anatomy)
        if mount_target.creature_type.value == "player_character":
            # Generally can't mount other PCs without consent
            return False, "Cannot mount player characters"
        
        return True, "Mounting is possible"
    
    def _determine_mount_type(self, mount_target: CombatantSchema) -> str:
        """Determine the type of mount based on the creature."""
        
        creature_name = mount_target.name.lower()
        
        if "horse" in creature_name:
            return "horse"
        elif "warhorse" in creature_name:
            return "warhorse"
        elif "pony" in creature_name:
            return "pony"
        elif "camel" in creature_name:
            return "camel"
        elif "elephant" in creature_name:
            return "elephant"
        elif "griffon" in creature_name or "griffin" in creature_name:
            return "griffon"
        elif "pegasus" in creature_name:
            return "pegasus"
        elif "dragon" in creature_name:
            return "dragon"
        else:
            return "beast"
    
    def _can_mount_attack(self, mount_target: CombatantSchema) -> bool:
        """Determine if mount can make attacks."""
        
        # Warhorses and aggressive mounts can attack
        mount_type = self._determine_mount_type(mount_target)
        
        attacking_mounts = ["warhorse", "griffon", "dragon", "pegasus"]
        return mount_type in attacking_mounts
    
    def _get_natural_attacks(self, mount_target: CombatantSchema) -> List:
        """Get natural attacks for a mount."""
        
        # Simplified - would normally be more complex
        attacks = []
        mount_type = self._determine_mount_type(mount_target)
        
        if mount_type == "warhorse":
            # Warhorse has hooves attack
            from ..models.base import AttackRoll
            hooves = AttackRoll(
                attack_bonus=6,
                damage_dice="2d6+4",
                damage_type=DamageType.BLUDGEONING,
                name="Hooves"
            )
            attacks.append(hooves)
        
        return attacks
    
    def _is_controlled_mount(self, mount_target: CombatantSchema) -> bool:
        """Determine if mount is controlled or independent."""
        
        # Most domestic animals are controlled
        # Wild or intelligent creatures are independent
        mount_type = self._determine_mount_type(mount_target)
        intelligence = mount_target.abilities.intelligence
        
        # High intelligence mounts are usually independent
        if intelligence >= 6:
            return False
        
        # Wild creatures are independent
        wild_types = ["dragon", "griffon"]
        if mount_type in wild_types:
            return False
        
        return True
    
    def _get_size_value(self, size) -> int:
        """Get numeric value for size comparison."""
        
        size_values = {
            CreatureSize.TINY: 1,
            CreatureSize.SMALL: 2,
            CreatureSize.MEDIUM: 3,
            CreatureSize.LARGE: 4,
            CreatureSize.HUGE: 5,
            CreatureSize.GARGANTUAN: 6
        }
        
        return size_values.get(size, 3)  # Default to medium
    
    def _is_position_empty(
        self,
        encounter: CombatEncounter,
        position: Position
    ) -> bool:
        """Check if a position is empty."""
        
        # Check battlefield bounds
        if not encounter.battlefield.is_valid_position(position):
            return False
        
        # Check for other combatants
        for combatant in encounter.combatants:
            if combatant.position == position:
                return False
        
        # Check for blocking terrain
        cell = encounter.battlefield.get_cell(position)
        if cell and cell.blocks_movement:
            return False
        
        return True
    
    def _restore_mount_combatant(
        self,
        encounter: CombatEncounter,
        mount: Mount
    ) -> Optional[CombatantSchema]:
        """Restore mount as an independent combatant."""
        
        # Find the original mount combatant
        mount_combatant = None
        for combatant in encounter.combatants:
            if combatant.id == mount.id:
                mount_combatant = combatant
                break
        
        if mount_combatant:
            # Update mount stats from Mount object
            mount_combatant.stats.hit_points = mount.hit_points
            mount_combatant.conditions = mount.conditions.copy()
            mount_combatant.is_mounted = False
        
        return mount_combatant
    
    def _add_mount_to_initiative(
        self,
        encounter: CombatEncounter,
        mount_combatant: CombatantSchema
    ) -> None:
        """Add mount back to initiative order."""
        
        from ..models.combat import InitiativeEntry
        
        # Roll new initiative for mount
        initiative_roll = random.randint(1, 20)
        initiative_modifier = mount_combatant.get_ability_modifier("dexterity")
        total_initiative = initiative_roll + initiative_modifier
        
        entry = InitiativeEntry(
            combatant_id=mount_combatant.id,
            initiative_roll=initiative_roll,
            initiative_modifier=initiative_modifier,
            total_initiative=total_initiative
        )
        
        # Insert in correct position based on initiative
        encounter.initiative_order.append(entry)
        encounter.initiative_order.sort(key=lambda x: x.total_initiative, reverse=True)
    
    def _find_rider_for_mount(
        self,
        encounter: CombatEncounter,
        mount_id: str
    ) -> Optional[CombatantSchema]:
        """Find the rider for a specific mount."""
        
        for combatant in encounter.combatants:
            if combatant.is_mounted and combatant.mount and combatant.mount.id == mount_id:
                return combatant
        
        return None