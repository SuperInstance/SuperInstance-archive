"""
Combat tracking service with initiative, hit points, conditions, and effects.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from models.combat import (
    CombatEncounter, CombatParticipant, InitiativeEntry, CombatAction,
    ParticipantCondition, CombatEffect, CombatState, TurnPhase,
    CombatEncounterSchema, CombatParticipantSchema, InitiativeEntrySchema,
    CombatActionSchema, ParticipantConditionSchema, CombatEffectSchema,
    StartCombatRequest, AddParticipantRequest, RollInitiativeRequest,
    TakeDamageRequest, HealParticipantRequest, ApplyConditionRequest,
    RemoveConditionRequest, NextTurnRequest, CombatSummaryResponse
)
from models.base import DamageType, ConditionType, ActionType
from .dice_service import DiceService, DiceRollRequest


class CombatService:
    """Service for managing combat encounters."""
    
    def __init__(self, db: Session, dice_service: Optional[DiceService] = None):
        self.db = db
        self.dice_service = dice_service or DiceService()
    
    def create_encounter(self, request: StartCombatRequest) -> CombatSummaryResponse:
        """Create a new combat encounter."""
        # Create the encounter
        encounter = CombatEncounter(
            name=request.name,
            description=request.description,
            campaign_id=request.campaign_id,
            session_id=request.session_id,
            state=CombatState.SETUP,
            settings=request.settings
        )
        
        self.db.add(encounter)
        self.db.flush()  # Get the ID
        
        # Add participants
        participants = []
        for participant_data in request.participants:
            participant = CombatParticipant(
                encounter_id=encounter.id,
                character_id=participant_data.character_id,
                name=participant_data.name,
                participant_type=participant_data.participant_type,
                team=participant_data.team,
                armor_class=participant_data.armor_class,
                hit_points_max=participant_data.hit_points_max,
                hit_points_current=participant_data.hit_points_current,
                hit_points_temp=participant_data.hit_points_temp,
                initiative_modifier=participant_data.initiative_modifier,
                position_x=participant_data.position_x,
                position_y=participant_data.position_y,
                movement_speed=participant_data.movement_speed,
                spell_slots=participant_data.spell_slots,
                other_resources=participant_data.other_resources,
                notes=participant_data.notes,
                participant_data=participant_data.participant_data
            )
            self.db.add(participant)
            participants.append(participant)
        
        self.db.commit()
        
        return self.get_combat_summary(encounter.id)
    
    def add_participant(self, encounter_id: str, request: AddParticipantRequest) -> CombatSummaryResponse:
        """Add a participant to an existing combat encounter."""
        encounter = self._get_encounter(encounter_id)
        
        participant = CombatParticipant(
            encounter_id=encounter.id,
            character_id=request.participant.character_id,
            name=request.participant.name,
            participant_type=request.participant.participant_type,
            team=request.participant.team,
            armor_class=request.participant.armor_class,
            hit_points_max=request.participant.hit_points_max,
            hit_points_current=request.participant.hit_points_current,
            hit_points_temp=request.participant.hit_points_temp,
            initiative_modifier=request.participant.initiative_modifier,
            position_x=request.participant.position_x,
            position_y=request.participant.position_y,
            movement_speed=request.participant.movement_speed,
            spell_slots=request.participant.spell_slots,
            other_resources=request.participant.other_resources,
            notes=request.participant.notes,
            participant_data=request.participant.participant_data
        )
        
        self.db.add(participant)
        self.db.commit()
        
        return self.get_combat_summary(encounter_id)
    
    def roll_initiative(self, encounter_id: str, request: RollInitiativeRequest) -> CombatSummaryResponse:
        """Roll initiative for specified participants."""
        encounter = self._get_encounter(encounter_id)
        
        # Get participants
        participants = self.db.query(CombatParticipant).filter(
            CombatParticipant.encounter_id == encounter.id,
            CombatParticipant.id.in_(request.participant_ids)
        ).all()
        
        # Clear existing initiative entries for these participants
        self.db.query(InitiativeEntry).filter(
            InitiativeEntry.encounter_id == encounter.id,
            InitiativeEntry.participant_id.in_(request.participant_ids)
        ).delete()
        
        # Roll initiative for each participant
        for participant in participants:
            # Roll d20 + modifier
            if request.auto_roll or participant.participant_type != "player":
                dice_request = DiceRollRequest(expression="1d20")
                roll_result = self.dice_service.roll(dice_request)
                initiative_roll = roll_result.rolls[0].kept_rolls[0] if roll_result.rolls else 10
            else:
                # For players, use existing roll or default
                initiative_roll = participant.initiative_roll or 10
            
            initiative_total = initiative_roll + participant.initiative_modifier
            
            # Update participant
            participant.initiative_roll = initiative_roll
            participant.initiative_total = initiative_total
            
            # Create initiative entry
            initiative_entry = InitiativeEntry(
                encounter_id=encounter.id,
                participant_id=participant.id,
                initiative_roll=initiative_roll,
                initiative_modifier=participant.initiative_modifier,
                initiative_total=initiative_total,
                order_position=0  # Will be set when sorting
            )
            self.db.add(initiative_entry)
        
        # Sort initiative order
        self._sort_initiative_order(encounter.id)
        
        # If all participants have rolled, start combat
        total_participants = self.db.query(CombatParticipant).filter(
            CombatParticipant.encounter_id == encounter.id
        ).count()
        
        initiative_count = self.db.query(InitiativeEntry).filter(
            InitiativeEntry.encounter_id == encounter.id
        ).count()
        
        if initiative_count >= total_participants:
            encounter.state = CombatState.ACTIVE
            encounter.current_round = 1
            encounter.current_turn = 0
            encounter.started_at = datetime.utcnow()
        else:
            encounter.state = CombatState.ROLLING_INITIATIVE
        
        self.db.commit()
        
        return self.get_combat_summary(encounter_id)
    
    def take_damage(self, encounter_id: str, request: TakeDamageRequest) -> CombatSummaryResponse:
        """Apply damage to a participant."""
        encounter = self._get_encounter(encounter_id)
        participant = self._get_participant(request.participant_id)
        
        # Apply damage (temp HP first)
        damage_remaining = request.damage
        
        if participant.hit_points_temp > 0:
            temp_damage = min(damage_remaining, participant.hit_points_temp)
            participant.hit_points_temp -= temp_damage
            damage_remaining -= temp_damage
        
        if damage_remaining > 0:
            participant.hit_points_current = max(0, participant.hit_points_current - damage_remaining)
        
        # Check if participant is unconscious or dead
        if participant.hit_points_current == 0:
            participant.is_conscious = False
            
            # Apply unconscious condition
            unconscious_condition = ParticipantCondition(
                participant_id=participant.id,
                condition_type=ConditionType.UNCONSCIOUS,
                condition_name="Unconscious",
                duration_type="permanent",
                source=request.source or "damage",
                effects={
                    "incapacitated": True,
                    "prone": True,
                    "blinded": True,
                    "deafened": True,
                    "attack_advantage": True  # Attacks against have advantage
                }
            )
            self.db.add(unconscious_condition)
        
        # Record the damage action
        damage_action = CombatAction(
            encounter_id=encounter.id,
            actor_id=None,  # Damage source might not be a participant
            target_id=participant.id,
            round_number=encounter.current_round,
            action_type="damage",
            action_name=f"Take {request.damage} damage",
            description=f"Took {request.damage} {request.damage_type or 'untyped'} damage",
            damage_roll=request.damage,
            damage_type=request.damage_type,
            action_data={
                "source": request.source,
                "temp_hp_absorbed": request.damage - damage_remaining
            }
        )
        self.db.add(damage_action)
        
        self.db.commit()
        
        return self.get_combat_summary(encounter_id)
    
    def heal_participant(self, encounter_id: str, request: HealParticipantRequest) -> CombatSummaryResponse:
        """Heal a participant."""
        encounter = self._get_encounter(encounter_id)
        participant = self._get_participant(request.participant_id)
        
        if request.temporary:
            # Temporary HP doesn't stack, use highest
            participant.hit_points_temp = max(participant.hit_points_temp, request.healing)
        else:
            # Regular healing
            max_heal = participant.hit_points_max - participant.hit_points_current
            actual_heal = min(request.healing, max_heal)
            participant.hit_points_current += actual_heal
            
            # If healed from 0, remove unconscious condition
            if participant.hit_points_current > 0 and not participant.is_conscious:
                participant.is_conscious = True
                participant.death_saves_successes = 0
                participant.death_saves_failures = 0
                
                # Remove unconscious condition
                self.db.query(ParticipantCondition).filter(
                    ParticipantCondition.participant_id == participant.id,
                    ParticipantCondition.condition_type == ConditionType.UNCONSCIOUS
                ).delete()
        
        # Record the healing action
        heal_action = CombatAction(
            encounter_id=encounter.id,
            target_id=participant.id,
            round_number=encounter.current_round,
            action_type="heal",
            action_name=f"Heal {request.healing} HP",
            description=f"Healed {request.healing} {'temporary ' if request.temporary else ''}hit points",
            healing_amount=request.healing,
            action_data={
                "source": request.source,
                "temporary": request.temporary
            }
        )
        self.db.add(heal_action)
        
        self.db.commit()
        
        return self.get_combat_summary(encounter_id)
    
    def apply_condition(self, encounter_id: str, request: ApplyConditionRequest) -> CombatSummaryResponse:
        """Apply a condition to a participant."""
        encounter = self._get_encounter(encounter_id)
        participant = self._get_participant(request.participant_id)
        
        # Check if condition already exists
        existing = self.db.query(ParticipantCondition).filter(
            ParticipantCondition.participant_id == participant.id,
            ParticipantCondition.condition_type == request.condition.condition_type
        ).first()
        
        if existing:
            # Update existing condition
            existing.duration_remaining = request.condition.duration_remaining
            existing.severity = max(existing.severity, request.condition.severity)
            existing.source = request.condition.source
            existing.effects.update(request.condition.effects)
        else:
            # Create new condition
            condition = ParticipantCondition(
                participant_id=request.participant_id,
                condition_type=request.condition.condition_type,
                condition_name=request.condition.condition_name,
                duration_type=request.condition.duration_type,
                duration_remaining=request.condition.duration_remaining,
                source=request.condition.source,
                source_id=request.condition.source_id,
                severity=request.condition.severity,
                save_dc=request.condition.save_dc,
                save_attribute=request.condition.save_attribute,
                save_end_of_turn=request.condition.save_end_of_turn,
                effects=request.condition.effects
            )
            self.db.add(condition)
        
        # Record the condition application
        condition_action = CombatAction(
            encounter_id=encounter.id,
            target_id=participant.id,
            round_number=encounter.current_round,
            action_type="condition",
            action_name=f"Apply {request.condition.condition_name}",
            description=f"Applied condition: {request.condition.condition_name}",
            action_data={
                "condition_type": request.condition.condition_type,
                "duration": request.condition.duration_remaining,
                "source": request.condition.source
            }
        )
        self.db.add(condition_action)
        
        self.db.commit()
        
        return self.get_combat_summary(encounter_id)
    
    def remove_condition(self, encounter_id: str, request: RemoveConditionRequest) -> CombatSummaryResponse:
        """Remove a condition from a participant."""
        encounter = self._get_encounter(encounter_id)
        
        condition = self.db.query(ParticipantCondition).filter(
            ParticipantCondition.id == request.condition_id
        ).first()
        
        if not condition:
            raise ValueError(f"Condition {request.condition_id} not found")
        
        condition_name = condition.condition_name
        self.db.delete(condition)
        
        # Record the condition removal
        remove_action = CombatAction(
            encounter_id=encounter.id,
            target_id=request.participant_id,
            round_number=encounter.current_round,
            action_type="condition",
            action_name=f"Remove {condition_name}",
            description=f"Removed condition: {condition_name}"
        )
        self.db.add(remove_action)
        
        self.db.commit()
        
        return self.get_combat_summary(encounter_id)
    
    def next_turn(self, encounter_id: str, request: NextTurnRequest) -> CombatSummaryResponse:
        """Advance to the next turn in combat."""
        encounter = self._get_encounter(encounter_id)
        
        if encounter.state != CombatState.ACTIVE:
            raise ValueError("Combat is not active")
        
        # Process end-of-turn effects for current participant
        self._process_end_of_turn_effects(encounter)
        
        if request.skip_to_participant_id:
            # Skip to specific participant
            initiative_entries = self.db.query(InitiativeEntry).filter(
                InitiativeEntry.encounter_id == encounter.id
            ).order_by(desc(InitiativeEntry.initiative_total), desc(InitiativeEntry.initiative_modifier)).all()
            
            for i, entry in enumerate(initiative_entries):
                if entry.participant_id == request.skip_to_participant_id:
                    encounter.current_turn = i
                    break
        else:
            # Normal turn advancement
            initiative_count = self.db.query(InitiativeEntry).filter(
                InitiativeEntry.encounter_id == encounter.id
            ).count()
            
            encounter.current_turn += 1
            
            if encounter.current_turn >= initiative_count:
                # New round
                encounter.current_turn = 0
                encounter.current_round += 1
                
                # Reset has_acted_this_round for all participants
                self.db.query(InitiativeEntry).filter(
                    InitiativeEntry.encounter_id == encounter.id
                ).update({"has_acted_this_round": False})
                
                # Process start-of-round effects
                self._process_start_of_round_effects(encounter)
        
        # Mark current participant as having acted
        initiative_entries = self.db.query(InitiativeEntry).filter(
            InitiativeEntry.encounter_id == encounter.id
        ).order_by(desc(InitiativeEntry.initiative_total), desc(InitiativeEntry.initiative_modifier)).all()
        
        if encounter.current_turn < len(initiative_entries):
            current_entry = initiative_entries[encounter.current_turn]
            current_entry.has_acted_this_round = True
        
        self.db.commit()
        
        return self.get_combat_summary(encounter_id)
    
    def end_encounter(self, encounter_id: str) -> CombatSummaryResponse:
        """End a combat encounter."""
        encounter = self._get_encounter(encounter_id)
        
        encounter.state = CombatState.ENDED
        encounter.ended_at = datetime.utcnow()
        
        if encounter.started_at:
            duration = encounter.ended_at - encounter.started_at
            encounter.duration_seconds = int(duration.total_seconds())
        
        # Clear temporary effects
        self.db.query(ParticipantCondition).filter(
            ParticipantCondition.participant_id.in_(
                self.db.query(CombatParticipant.id).filter(
                    CombatParticipant.encounter_id == encounter.id
                )
            ),
            ParticipantCondition.duration_type == "rounds"
        ).delete()
        
        self.db.commit()
        
        return self.get_combat_summary(encounter_id)
    
    def get_combat_summary(self, encounter_id: str) -> CombatSummaryResponse:
        """Get a complete summary of the combat encounter."""
        encounter = self._get_encounter(encounter_id)
        
        # Get participants with conditions
        participants = self.db.query(CombatParticipant).filter(
            CombatParticipant.encounter_id == encounter.id
        ).all()
        
        participant_schemas = []
        for participant in participants:
            # Get conditions for this participant
            conditions = self.db.query(ParticipantCondition).filter(
                ParticipantCondition.participant_id == participant.id
            ).all()
            
            participant_schema = CombatParticipantSchema.from_orm(participant)
            participant_schemas.append(participant_schema)
        
        # Get initiative order
        initiative_entries = self.db.query(InitiativeEntry).filter(
            InitiativeEntry.encounter_id == encounter.id
        ).order_by(desc(InitiativeEntry.initiative_total), desc(InitiativeEntry.initiative_modifier)).all()
        
        initiative_schemas = [InitiativeEntrySchema.from_orm(entry) for entry in initiative_entries]
        
        # Get current participant
        current_participant = None
        if (encounter.state == CombatState.ACTIVE and 
            encounter.current_turn < len(initiative_entries)):
            current_entry = initiative_entries[encounter.current_turn]
            current_participant = next(
                (p for p in participant_schemas if p.id == current_entry.participant_id),
                None
            )
        
        # Get active effects
        active_effects = self.db.query(CombatEffect).filter(
            CombatEffect.encounter_id == encounter.id
        ).all()
        
        effect_schemas = [CombatEffectSchema.from_orm(effect) for effect in active_effects]
        
        # Get recent actions (last 10)
        recent_actions = self.db.query(CombatAction).filter(
            CombatAction.encounter_id == encounter.id
        ).order_by(desc(CombatAction.created_at)).limit(10).all()
        
        action_schemas = [CombatActionSchema.from_orm(action) for action in recent_actions]
        
        return CombatSummaryResponse(
            encounter=CombatEncounterSchema.from_orm(encounter),
            participants=participant_schemas,
            initiative_order=initiative_schemas,
            current_participant=current_participant,
            active_effects=effect_schemas,
            recent_actions=action_schemas
        )
    
    def _get_encounter(self, encounter_id: str) -> CombatEncounter:
        """Get encounter by ID or raise exception."""
        encounter = self.db.query(CombatEncounter).filter(
            CombatEncounter.id == encounter_id
        ).first()
        
        if not encounter:
            raise ValueError(f"Combat encounter {encounter_id} not found")
        
        return encounter
    
    def _get_participant(self, participant_id: str) -> CombatParticipant:
        """Get participant by ID or raise exception."""
        participant = self.db.query(CombatParticipant).filter(
            CombatParticipant.id == participant_id
        ).first()
        
        if not participant:
            raise ValueError(f"Combat participant {participant_id} not found")
        
        return participant
    
    def _sort_initiative_order(self, encounter_id: str) -> None:
        """Sort initiative entries by total initiative (highest first)."""
        entries = self.db.query(InitiativeEntry).filter(
            InitiativeEntry.encounter_id == encounter_id
        ).order_by(desc(InitiativeEntry.initiative_total), desc(InitiativeEntry.initiative_modifier)).all()
        
        for i, entry in enumerate(entries):
            entry.order_position = i
    
    def _process_end_of_turn_effects(self, encounter: CombatEncounter) -> None:
        """Process effects that trigger at the end of a turn."""
        # Get current participant
        initiative_entries = self.db.query(InitiativeEntry).filter(
            InitiativeEntry.encounter_id == encounter.id
        ).order_by(desc(InitiativeEntry.initiative_total), desc(InitiativeEntry.initiative_modifier)).all()
        
        if encounter.current_turn >= len(initiative_entries):
            return
        
        current_entry = initiative_entries[encounter.current_turn]
        participant = self._get_participant(current_entry.participant_id)
        
        # Process conditions that allow saves at end of turn
        conditions = self.db.query(ParticipantCondition).filter(
            ParticipantCondition.participant_id == participant.id,
            ParticipantCondition.save_end_of_turn == True
        ).all()
        
        for condition in conditions:
            if condition.save_dc and condition.save_attribute:
                # Roll saving throw
                dice_request = DiceRollRequest(expression="1d20")
                roll_result = self.dice_service.roll(dice_request)
                save_roll = roll_result.rolls[0].total if roll_result.rolls else 10
                
                # TODO: Add ability modifier based on save_attribute
                
                if save_roll >= condition.save_dc:
                    # Save successful, remove condition
                    self.db.delete(condition)
                    
                    # Record the save
                    save_action = CombatAction(
                        encounter_id=encounter.id,
                        actor_id=participant.id,
                        round_number=encounter.current_round,
                        action_type="save",
                        action_name=f"{condition.save_attribute.title()} Save",
                        description=f"Saved against {condition.condition_name}",
                        saved=True,
                        roll_details={"save_roll": save_roll, "dc": condition.save_dc}
                    )
                    self.db.add(save_action)
        
        # Reduce duration of timed conditions
        timed_conditions = self.db.query(ParticipantCondition).filter(
            ParticipantCondition.participant_id == participant.id,
            ParticipantCondition.duration_type == "rounds",
            ParticipantCondition.duration_remaining.isnot(None)
        ).all()
        
        for condition in timed_conditions:
            condition.duration_remaining -= 1
            if condition.duration_remaining <= 0:
                self.db.delete(condition)
    
    def _process_start_of_round_effects(self, encounter: CombatEncounter) -> None:
        """Process effects that trigger at the start of each round."""
        # Process ongoing damage/effects for all participants
        participants = self.db.query(CombatParticipant).filter(
            CombatParticipant.encounter_id == encounter.id
        ).all()
        
        for participant in participants:
            conditions = self.db.query(ParticipantCondition).filter(
                ParticipantCondition.participant_id == participant.id
            ).all()
            
            for condition in conditions:
                # Process conditions with ongoing effects (like poison damage)
                if "ongoing_damage" in condition.effects:
                    damage = condition.effects["ongoing_damage"]
                    participant.hit_points_current = max(0, participant.hit_points_current - damage)
                    
                    # Record ongoing damage
                    damage_action = CombatAction(
                        encounter_id=encounter.id,
                        target_id=participant.id,
                        round_number=encounter.current_round,
                        action_type="ongoing_damage",
                        action_name=f"{condition.condition_name} damage",
                        description=f"Takes {damage} damage from {condition.condition_name}",
                        damage_roll=damage,
                        action_data={"condition_id": condition.id}
                    )
                    self.db.add(damage_action)