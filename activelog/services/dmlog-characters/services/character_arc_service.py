"""
Character arc progression service.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
import logging

from ..models.character_arc import (
    ArcType, ArcStage, ProgressTrigger, ChangeType, ArcIntensity,
    CharacterArcSchema, ArcProgressRequest, ArcProgressResponse,
    ArcCreationRequest, ArcAnalysis, ArcSuggestion, CharacterDevelopmentPlan,
    ArcMilestoneSchema, ArcNarrativeElement, ArcPrediction,
    CharacterArc, ArcProgress, ArcMilestone, ArcTemplate
)
from ..models.base import EmotionType, CharacterType
from ..models.personality import PersonalityProfileSchema, MoralAlignment
from ..config import Config

logger = logging.getLogger(__name__)

class CharacterArcService:
    def __init__(self):
        self.config = Config()
        self.arc_templates = self._initialize_arc_templates()
        self.stage_progressions = self._initialize_stage_progressions()
        self.development_catalysts = self._initialize_development_catalysts()
        self.milestone_templates = self._initialize_milestone_templates()
        
    def _initialize_arc_templates(self) -> Dict[ArcType, Dict[str, Any]]:
        """Initialize templates for different arc types."""
        return {
            ArcType.HERO_JOURNEY: {
                "stages": [
                    ArcStage.ORDINARY_WORLD,
                    ArcStage.CALL_TO_ADVENTURE,
                    ArcStage.REFUSAL,
                    ArcStage.MENTOR,
                    ArcStage.CROSSING_THRESHOLD,
                    ArcStage.TESTS,
                    ArcStage.APPROACH,
                    ArcStage.ORDEAL,
                    ArcStage.REWARD,
                    ArcStage.ROAD_BACK,
                    ArcStage.RESURRECTION,
                    ArcStage.RETURN
                ],
                "typical_duration": "long",
                "personality_changes": {
                    "extraversion": 0.2,
                    "conscientiousness": 0.3,
                    "openness": 0.2
                },
                "key_developments": [
                    "courage_development",
                    "leadership_skills",
                    "self_confidence",
                    "moral_clarity"
                ]
            },
            
            ArcType.REDEMPTION: {
                "stages": [
                    ArcStage.ORDINARY_WORLD,    # Life of moral corruption
                    ArcStage.CALL_TO_ADVENTURE, # Opportunity for change
                    ArcStage.REFUSAL,           # Resistance to change
                    ArcStage.CROSSING_THRESHOLD, # First step toward redemption
                    ArcStage.TESTS,             # Proving worthiness
                    ArcStage.ORDEAL,            # Major sacrifice required
                    ArcStage.REWARD,            # Acceptance/forgiveness
                    ArcStage.RETURN             # New life achieved
                ],
                "typical_duration": "medium",
                "alignment_change": "toward_good",
                "personality_changes": {
                    "agreeableness": 0.4,
                    "conscientiousness": 0.3,
                    "neuroticism": -0.2
                },
                "key_developments": [
                    "moral_awakening",
                    "empathy_growth",
                    "self_forgiveness",
                    "making_amends"
                ]
            },
            
            ArcType.FALL_FROM_GRACE: {
                "stages": [
                    ArcStage.ORDINARY_WORLD,    # Virtuous beginning
                    ArcStage.CALL_TO_ADVENTURE, # Temptation presented
                    ArcStage.CROSSING_THRESHOLD, # First moral compromise
                    ArcStage.TESTS,             # Escalating corruption
                    ArcStage.APPROACH,          # Planning the great fall
                    ArcStage.ORDEAL,            # The great betrayal/sin
                    ArcStage.REWARD,            # Temporary gains from evil
                    ArcStage.ROAD_BACK,         # Consequences manifest
                    ArcStage.RESURRECTION,      # Final moral choice
                    ArcStage.RETURN             # New corrupt equilibrium
                ],
                "typical_duration": "long",
                "alignment_change": "toward_evil",
                "personality_changes": {
                    "agreeableness": -0.4,
                    "conscientiousness": -0.2,
                    "openness": -0.1
                },
                "key_developments": [
                    "moral_corruption",
                    "rationalization_skills",
                    "emotional_hardening",
                    "power_hunger"
                ]
            },
            
            ArcType.COMING_OF_AGE: {
                "stages": [
                    ArcStage.ORDINARY_WORLD,    # Childhood innocence
                    ArcStage.CALL_TO_ADVENTURE, # Adult responsibility calls
                    ArcStage.CROSSING_THRESHOLD, # Leaving childhood behind
                    ArcStage.TESTS,             # Learning about the world
                    ArcStage.ORDEAL,            # Loss of innocence
                    ArcStage.REWARD,            # Wisdom gained
                    ArcStage.RETURN             # Mature adult
                ],
                "typical_duration": "medium",
                "personality_changes": {
                    "conscientiousness": 0.3,
                    "emotional_stability": 0.2,
                    "openness": 0.1
                },
                "key_developments": [
                    "emotional_maturity",
                    "responsibility_acceptance",
                    "world_understanding",
                    "identity_formation"
                ]
            }
        }
    
    def _initialize_stage_progressions(self) -> Dict[ArcStage, Dict[str, Any]]:
        """Initialize requirements and effects for stage progressions."""
        return {
            ArcStage.CALL_TO_ADVENTURE: {
                "typical_triggers": [ProgressTrigger.EXTERNAL_EVENT, ProgressTrigger.REVELATION],
                "requirements": ["significant_event", "character_ready"],
                "character_effects": ["motivation_increase", "curiosity_spike"],
                "minimum_progress": 0.1
            },
            
            ArcStage.REFUSAL: {
                "typical_triggers": [ProgressTrigger.MAJOR_DECISION],
                "requirements": ["fear_or_doubt", "attachment_to_status_quo"],
                "character_effects": ["internal_conflict", "hesitation"],
                "minimum_progress": 0.05
            },
            
            ArcStage.CROSSING_THRESHOLD: {
                "typical_triggers": [ProgressTrigger.MAJOR_DECISION, ProgressTrigger.EXTERNAL_EVENT],
                "requirements": ["commitment_made", "point_of_no_return"],
                "character_effects": ["determination_boost", "fear_override"],
                "minimum_progress": 0.15
            },
            
            ArcStage.TESTS: {
                "typical_triggers": [ProgressTrigger.QUEST_COMPLETION, ProgressTrigger.RELATIONSHIP_CHANGE],
                "requirements": ["challenges_faced", "allies_or_enemies_made"],
                "character_effects": ["skill_development", "relationship_growth"],
                "minimum_progress": 0.2
            },
            
            ArcStage.ORDEAL: {
                "typical_triggers": [ProgressTrigger.DEFEAT, ProgressTrigger.LOSS, ProgressTrigger.BETRAYAL],
                "requirements": ["major_crisis", "everything_at_stake"],
                "character_effects": ["transformation_catalyst", "core_change"],
                "minimum_progress": 0.3
            },
            
            ArcStage.REWARD: {
                "typical_triggers": [ProgressTrigger.VICTORY, ProgressTrigger.REVELATION],
                "requirements": ["ordeal_survived", "growth_demonstrated"],
                "character_effects": ["confidence_gain", "new_abilities"],
                "minimum_progress": 0.1
            },
            
            ArcStage.RETURN: {
                "typical_triggers": [ProgressTrigger.TIME_PASSAGE, ProgressTrigger.QUEST_COMPLETION],
                "requirements": ["journey_complete", "wisdom_gained"],
                "character_effects": ["integration", "new_equilibrium"],
                "minimum_progress": 0.1
            }
        }
    
    def _initialize_development_catalysts(self) -> Dict[str, List[str]]:
        """Initialize catalysts that promote character development."""
        return {
            "personality_growth": [
                "meaningful_relationships",
                "challenging_situations",
                "moral_dilemmas",
                "failure_and_recovery",
                "mentor_guidance"
            ],
            "moral_development": [
                "ethical_choices",
                "consequences_of_actions",
                "victim_encounters",
                "philosophical_discussions",
                "witnessing_injustice"
            ],
            "skill_development": [
                "practice_opportunities",
                "expert_instruction",
                "necessity_driven_learning",
                "competitive_pressure",
                "life_threatening_situations"
            ],
            "emotional_growth": [
                "trust_building",
                "vulnerability_moments",
                "empathy_exercises",
                "trauma_processing",
                "love_experiences"
            ]
        }
    
    def _initialize_milestone_templates(self) -> Dict[ArcType, List[Dict[str, Any]]]:
        """Initialize milestone templates for each arc type."""
        return {
            ArcType.HERO_JOURNEY: [
                {
                    "name": "First Refusal",
                    "stage": ArcStage.REFUSAL,
                    "type": "character_growth",
                    "description": "Character initially refuses the call to adventure",
                    "changes": [{"type": ChangeType.FEAR, "value": "adventure_fear"}]
                },
                {
                    "name": "Mentor Meeting",
                    "stage": ArcStage.MENTOR,
                    "type": "relationship",
                    "description": "Character meets their guide/mentor",
                    "changes": [{"type": ChangeType.RELATIONSHIP, "value": "mentor_bond"}]
                },
                {
                    "name": "Point of No Return",
                    "stage": ArcStage.CROSSING_THRESHOLD,
                    "type": "plot_point",
                    "description": "Character commits fully to the journey",
                    "changes": [{"type": ChangeType.MOTIVATION, "value": "unwavering_commitment"}]
                }
            ],
            
            ArcType.REDEMPTION: [
                {
                    "name": "Moral Awakening",
                    "stage": ArcStage.CALL_TO_ADVENTURE,
                    "type": "character_growth",
                    "description": "Character realizes the harm they've caused",
                    "changes": [{"type": ChangeType.MORAL, "value": "guilt_recognition"}]
                },
                {
                    "name": "First Act of Redemption",
                    "stage": ArcStage.TESTS,
                    "type": "character_growth",
                    "description": "Character performs their first selfless act",
                    "changes": [{"type": ChangeType.PERSONALITY, "value": "agreeableness_increase"}]
                }
            ]
        }

    async def create_character_arc(
        self,
        request: ArcCreationRequest,
        personality: PersonalityProfileSchema,
        current_alignment: MoralAlignment,
        db_session: Optional[Session] = None
    ) -> CharacterArcSchema:
        """Create a new character arc."""
        
        # Get arc template
        template = self.arc_templates.get(request.arc_type)
        if not template:
            raise ValueError(f"Unknown arc type: {request.arc_type}")
        
        # Generate arc name if not provided
        arc_name = request.arc_name or await self._generate_arc_name(request.arc_type, personality)
        
        # Determine stages for this arc
        stages = template["stages"]
        
        # Set up initial state
        arc_id = f"arc_{request.character_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        arc = CharacterArcSchema(
            id=arc_id,
            character_id=request.character_id,
            arc_name=arc_name,
            arc_type=request.arc_type,
            arc_description=request.custom_description or template.get("description"),
            current_stage=request.starting_stage,
            stages_completed=[],
            stages_remaining=stages,
            arc_intensity=request.intensity,
            estimated_duration=request.estimated_duration or template.get("typical_duration", "medium"),
            starting_personality=personality.dict(),
            starting_alignment=current_alignment,
            target_personality=request.target_changes.get("personality") if request.target_changes else None,
            target_alignment=request.target_changes.get("alignment") if request.target_changes else None
        )
        
        # Create milestones for this arc
        await self._create_arc_milestones(arc, db_session)
        
        # Calculate estimated completion
        arc.estimated_completion = await self._calculate_estimated_completion(arc)
        
        logger.info(f"Created new arc: {arc_name} for character {request.character_id}")
        
        return arc

    async def progress_character_arc(
        self,
        request: ArcProgressRequest,
        personality: PersonalityProfileSchema,
        db_session: Optional[Session] = None
    ) -> ArcProgressResponse:
        """Progress a character arc based on a trigger event."""
        
        # Get current arc
        arc = await self._get_character_arc(request.arc_id, db_session)
        if not arc:
            raise ValueError(f"Arc {request.arc_id} not found")
        
        if not arc.is_active:
            return ArcProgressResponse(
                character_id=request.character_id,
                arc_id=request.arc_id,
                progress_occurred=False,
                previous_stage=arc.current_stage,
                new_stage=arc.current_stage,
                progress_amount=0.0,
                changes_applied=[],
                milestones_achieved=[]
            )
        
        # Check if this trigger can cause progression
        can_progress = await self._can_progress_stage(
            arc, request.trigger_event, request.context, request.forced_progression
        )
        
        if not can_progress:
            return ArcProgressResponse(
                character_id=request.character_id,
                arc_id=request.arc_id,
                progress_occurred=False,
                previous_stage=arc.current_stage,
                new_stage=arc.current_stage,
                progress_amount=0.0,
                changes_applied=[],
                milestones_achieved=[]
            )
        
        # Calculate progression amount
        progress_amount = await self._calculate_progress_amount(
            arc, request.trigger_event, request.context
        )
        
        previous_stage = arc.current_stage
        
        # Update stage progress
        arc.stage_progress += progress_amount
        
        # Check for stage completion
        new_stage = arc.current_stage
        stage_changed = False
        
        if arc.stage_progress >= 1.0:
            # Move to next stage
            next_stage = await self._get_next_stage(arc)
            if next_stage:
                new_stage = next_stage
                arc.current_stage = next_stage
                arc.stages_completed.append(previous_stage)
                arc.stages_remaining = [s for s in arc.stages_remaining if s != next_stage]
                arc.stage_progress = 0.0
                stage_changed = True
        
        # Calculate overall progress
        total_stages = len(arc.stages_completed) + len(arc.stages_remaining)
        arc.overall_progress = len(arc.stages_completed) / total_stages if total_stages > 0 else 0.0
        
        # Apply character changes
        changes_applied = await self._apply_character_changes(
            arc, request, progress_amount, stage_changed
        )
        
        # Check for achieved milestones
        milestones_achieved = await self._check_milestones(arc, new_stage, request.context)
        
        # Generate narrative elements
        narrative_elements = await self._generate_narrative_elements(
            arc, request, previous_stage, new_stage, changes_applied
        )
        
        # Update arc metadata
        arc.last_progress = datetime.utcnow()
        
        # Check for arc completion
        if len(arc.stages_remaining) == 0:
            arc.is_completed = True
            arc.actual_completion = datetime.utcnow()
            arc.completion_reason = "natural_progression"
        
        # Save progress event
        await self._save_arc_progress(
            arc, request, previous_stage, new_stage, progress_amount, changes_applied, db_session
        )
        
        # Identify new opportunities
        new_opportunities = await self._identify_new_opportunities(arc, new_stage, changes_applied)
        
        return ArcProgressResponse(
            character_id=request.character_id,
            arc_id=request.arc_id,
            progress_occurred=True,
            previous_stage=previous_stage,
            new_stage=new_stage,
            progress_amount=progress_amount,
            changes_applied=changes_applied,
            milestones_achieved=milestones_achieved,
            new_opportunities=new_opportunities,
            narrative_elements=narrative_elements
        )

    async def analyze_character_arcs(
        self,
        character_id: str,
        db_session: Optional[Session] = None
    ) -> ArcAnalysis:
        """Analyze all character arcs for a character."""
        
        arcs = await self._get_character_arcs(character_id, db_session)
        
        active_arcs = sum(1 for arc in arcs if arc.is_active)
        completed_arcs = sum(1 for arc in arcs if arc.is_completed)
        abandoned_arcs = sum(1 for arc in arcs if arc.is_abandoned)
        
        # Calculate total growth
        total_growth = 0.0
        for arc in arcs:
            if arc.overall_progress:
                total_growth += arc.overall_progress
        total_growth = total_growth / len(arcs) if arcs else 0.0
        
        # Find dominant arc types
        arc_type_counts = {}
        for arc in arcs:
            arc_type_counts[arc.arc_type] = arc_type_counts.get(arc.arc_type, 0) + 1
        
        dominant_types = sorted(arc_type_counts.items(), key=lambda x: x[1], reverse=True)
        dominant_arc_types = [arc_type for arc_type, _ in dominant_types[:3]]
        
        # Analyze current development focus
        development_focus = []
        for arc in arcs:
            if arc.is_active:
                template = self.arc_templates.get(arc.arc_type, {})
                developments = template.get("key_developments", [])
                development_focus.extend(developments)
        
        # Project completion dates
        completion_dates = {}
        for arc in arcs:
            if arc.is_active and arc.estimated_completion:
                completion_dates[arc.id] = arc.estimated_completion
        
        # Identify conflicts
        conflicts = await self._identify_arc_conflicts(arcs)
        
        # Generate recommendations
        recommendations = await self._generate_arc_recommendations(arcs, character_id)
        
        return ArcAnalysis(
            character_id=character_id,
            active_arcs=active_arcs,
            completed_arcs=completed_arcs,
            abandoned_arcs=abandoned_arcs,
            total_character_growth=total_growth,
            dominant_arc_types=dominant_arc_types,
            current_development_focus=list(set(development_focus)),
            projected_completion_dates=completion_dates,
            potential_conflicts=conflicts,
            recommended_actions=recommendations
        )

    async def suggest_new_arc(
        self,
        character_id: str,
        personality: PersonalityProfileSchema,
        current_alignment: MoralAlignment,
        existing_arcs: List[CharacterArcSchema],
        db_session: Optional[Session] = None
    ) -> List[ArcSuggestion]:
        """Suggest new character arcs based on current state."""
        
        suggestions = []
        
        # Analyze current state
        active_arc_types = [arc.arc_type for arc in existing_arcs if arc.is_active]
        
        # Check each arc type for suitability
        for arc_type, template in self.arc_templates.items():
            if arc_type in active_arc_types:
                continue  # Skip if already active
            
            compatibility = await self._calculate_arc_compatibility(
                arc_type, personality, current_alignment, existing_arcs
            )
            
            if compatibility > 0.5:  # Threshold for suggestion
                suggestion = ArcSuggestion(
                    suggested_arc_type=arc_type,
                    arc_name=await self._generate_arc_name(arc_type, personality),
                    reasoning=await self._generate_arc_reasoning(
                        arc_type, personality, existing_arcs, compatibility
                    ),
                    compatibility_score=compatibility,
                    estimated_duration=template.get("typical_duration", "medium"),
                    key_development_areas=template.get("key_developments", []),
                    potential_obstacles=await self._identify_potential_obstacles(
                        arc_type, personality, existing_arcs
                    ),
                    synergy_with_existing_arcs=await self._identify_arc_synergies(
                        arc_type, existing_arcs
                    )
                )
                suggestions.append(suggestion)
        
        # Sort by compatibility score
        suggestions.sort(key=lambda x: x.compatibility_score, reverse=True)
        
        return suggestions[:3]  # Return top 3 suggestions

    async def get_arc_predictions(
        self,
        arc_id: str,
        character_context: Dict[str, Any],
        db_session: Optional[Session] = None
    ) -> ArcPrediction:
        """Predict the next developments in a character arc."""
        
        arc = await self._get_character_arc(arc_id, db_session)
        if not arc:
            raise ValueError(f"Arc {arc_id} not found")
        
        # Predict next stage
        next_stage = await self._get_next_stage(arc)
        if not next_stage:
            next_stage = arc.current_stage  # Arc complete
        
        # Calculate confidence based on current progress
        confidence = min(0.9, 0.5 + arc.stage_progress)
        
        # Estimate time to next stage
        time_estimate = await self._estimate_time_to_next_stage(arc, character_context)
        
        # Identify likely triggers
        stage_info = self.stage_progressions.get(next_stage, {})
        likely_triggers = stage_info.get("typical_triggers", [])
        
        # Identify potential obstacles
        obstacles = await self._identify_stage_obstacles(arc, next_stage, character_context)
        
        # Generate alternative paths
        alternatives = await self._generate_alternative_paths(arc, character_context)
        
        # Recommend catalysts
        catalysts = await self._recommend_progression_catalysts(arc, next_stage)
        
        return ArcPrediction(
            character_id=arc.character_id,
            arc_id=arc_id,
            predicted_next_stage=next_stage,
            confidence=confidence,
            estimated_time_to_next_stage=time_estimate,
            likely_triggers=likely_triggers,
            potential_obstacles=obstacles,
            alternative_paths=alternatives,
            recommended_catalysts=catalysts
        )

    async def _generate_arc_name(
        self,
        arc_type: ArcType,
        personality: PersonalityProfileSchema
    ) -> str:
        """Generate a name for the arc based on type and personality."""
        
        name_templates = {
            ArcType.HERO_JOURNEY: [
                "The Call to Greatness",
                "Journey of Courage",
                "The Heroic Path",
                "Rise of a Champion"
            ],
            ArcType.REDEMPTION: [
                "Path to Redemption",
                "Second Chances",
                "The Atonement",
                "Seeking Forgiveness"
            ],
            ArcType.FALL_FROM_GRACE: [
                "The Corruption",
                "Fall from Light",
                "The Temptation",
                "Lost Innocence"
            ],
            ArcType.COMING_OF_AGE: [
                "Growing Up",
                "The Maturation",
                "Finding Identity",
                "Becoming Adult"
            ]
        }
        
        templates = name_templates.get(arc_type, ["Character Development"])
        return random.choice(templates)

    async def _can_progress_stage(
        self,
        arc: CharacterArcSchema,
        trigger: ProgressTrigger,
        context: Optional[Dict[str, Any]],
        forced: bool
    ) -> bool:
        """Check if the trigger can cause stage progression."""
        
        if forced:
            return True
        
        stage_info = self.stage_progressions.get(arc.current_stage, {})
        typical_triggers = stage_info.get("typical_triggers", [])
        
        # Check if trigger is appropriate for current stage
        if trigger not in typical_triggers:
            return False
        
        # Check minimum progress requirement
        minimum_progress = stage_info.get("minimum_progress", 0.1)
        return arc.stage_progress >= minimum_progress

    async def _calculate_progress_amount(
        self,
        arc: CharacterArcSchema,
        trigger: ProgressTrigger,
        context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate how much progress this trigger creates."""
        
        # Base progress amounts for different triggers
        trigger_progress = {
            ProgressTrigger.QUEST_COMPLETION: 0.3,
            ProgressTrigger.MAJOR_DECISION: 0.2,
            ProgressTrigger.REVELATION: 0.4,
            ProgressTrigger.LOSS: 0.3,
            ProgressTrigger.VICTORY: 0.2,
            ProgressTrigger.BETRAYAL: 0.4,
            ProgressTrigger.SACRIFICE: 0.5
        }
        
        base_progress = trigger_progress.get(trigger, 0.1)
        
        # Modify based on arc intensity
        intensity_modifiers = {
            ArcIntensity.SUBTLE: 0.5,
            ArcIntensity.MODERATE: 1.0,
            ArcIntensity.DRAMATIC: 1.5,
            ArcIntensity.LIFE_CHANGING: 2.0
        }
        
        intensity_modifier = intensity_modifiers.get(arc.arc_intensity, 1.0)
        
        # Context modifiers
        context_modifier = 1.0
        if context:
            if context.get("high_stakes"):
                context_modifier += 0.3
            if context.get("public_event"):
                context_modifier += 0.2
            if context.get("personal_significance"):
                context_modifier += 0.2
        
        final_progress = base_progress * intensity_modifier * context_modifier
        return min(1.0, final_progress)  # Cap at 1.0

    async def _get_next_stage(self, arc: CharacterArcSchema) -> Optional[ArcStage]:
        """Get the next stage in the arc progression."""
        
        template = self.arc_templates.get(arc.arc_type)
        if not template:
            return None
        
        stages = template["stages"]
        
        try:
            current_index = stages.index(arc.current_stage)
            if current_index + 1 < len(stages):
                return stages[current_index + 1]
        except ValueError:
            pass
        
        return None

    async def _apply_character_changes(
        self,
        arc: CharacterArcSchema,
        request: ArcProgressRequest,
        progress_amount: float,
        stage_changed: bool
    ) -> List[Dict[str, Any]]:
        """Apply character changes based on arc progression."""
        
        changes = []
        
        # Get template changes for this arc type
        template = self.arc_templates.get(arc.arc_type, {})
        
        # Apply personality changes if stage changed
        if stage_changed and "personality_changes" in template:
            personality_changes = template["personality_changes"]
            for trait, change_amount in personality_changes.items():
                # Scale change by arc intensity and progress
                actual_change = change_amount * progress_amount
                if arc.arc_intensity == ArcIntensity.DRAMATIC:
                    actual_change *= 1.5
                elif arc.arc_intensity == ArcIntensity.LIFE_CHANGING:
                    actual_change *= 2.0
                
                changes.append({
                    "type": ChangeType.PERSONALITY.value,
                    "target": trait,
                    "change": actual_change,
                    "reason": f"Arc progression: {arc.arc_name}"
                })
        
        # Apply alignment changes
        if stage_changed and "alignment_change" in template:
            alignment_direction = template["alignment_change"]
            changes.append({
                "type": ChangeType.MORAL.value,
                "target": "alignment",
                "change": alignment_direction,
                "reason": f"Moral development in {arc.arc_name}"
            })
        
        # Apply skill/ability changes based on stage
        stage_developments = await self._get_stage_developments(arc.current_stage, progress_amount)
        changes.extend(stage_developments)
        
        return changes

    async def _check_milestones(
        self,
        arc: CharacterArcSchema,
        current_stage: ArcStage,
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Check for achieved milestones."""
        
        milestones_achieved = []
        
        # Get milestone templates for this arc type
        milestone_templates = self.milestone_templates.get(arc.arc_type, [])
        
        for milestone in milestone_templates:
            if milestone["stage"] == current_stage:
                # Check if conditions are met
                if await self._milestone_conditions_met(milestone, context):
                    milestones_achieved.append(milestone["name"])
        
        return milestones_achieved

    async def _generate_narrative_elements(
        self,
        arc: CharacterArcSchema,
        request: ArcProgressRequest,
        previous_stage: ArcStage,
        new_stage: ArcStage,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Generate narrative elements for the progression."""
        
        elements = {}
        
        # Internal thoughts based on stage transition
        if new_stage != previous_stage:
            stage_thoughts = {
                ArcStage.CALL_TO_ADVENTURE: "Something calls to me... a chance for change, for growth.",
                ArcStage.REFUSAL: "But do I really want this? Maybe I should stay where it's safe.",
                ArcStage.CROSSING_THRESHOLD: "There's no turning back now. I've committed to this path.",
                ArcStage.ORDEAL: "This is it... everything I've worked for comes down to this moment.",
                ArcStage.REWARD: "I've grown stronger, wiser. I'm not the same person I was before."
            }
            
            elements["internal_thoughts"] = stage_thoughts.get(
                new_stage, "I can feel myself changing, becoming someone new."
            )
        
        # External manifestations
        if changes:
            change_descriptions = []
            for change in changes:
                if change["type"] == ChangeType.PERSONALITY.value:
                    change_descriptions.append(f"shows more {change['target']}")
                elif change["type"] == ChangeType.MORAL.value:
                    change_descriptions.append("demonstrates moral growth")
            
            if change_descriptions:
                elements["external_manifestation"] = "Others notice that they " + " and ".join(change_descriptions)
        
        return elements

    async def _calculate_arc_compatibility(
        self,
        arc_type: ArcType,
        personality: PersonalityProfileSchema,
        alignment: MoralAlignment,
        existing_arcs: List[CharacterArcSchema]
    ) -> float:
        """Calculate compatibility score for an arc type."""
        
        compatibility = 0.5  # Base compatibility
        
        template = self.arc_templates.get(arc_type, {})
        
        # Check personality fit
        if "personality_changes" in template:
            personality_changes = template["personality_changes"]
            for trait, target_change in personality_changes.items():
                current_value = getattr(personality, trait, 0.5)
                
                # If change would move toward extreme, check if there's room
                if target_change > 0 and current_value < 0.8:
                    compatibility += 0.1
                elif target_change < 0 and current_value > 0.2:
                    compatibility += 0.1
        
        # Check alignment compatibility
        if "alignment_change" in template:
            alignment_change = template["alignment_change"]
            if alignment_change == "toward_good" and alignment in [
                MoralAlignment.CHAOTIC_NEUTRAL, MoralAlignment.TRUE_NEUTRAL, MoralAlignment.LAWFUL_NEUTRAL
            ]:
                compatibility += 0.2
            elif alignment_change == "toward_evil" and alignment in [
                MoralAlignment.CHAOTIC_NEUTRAL, MoralAlignment.TRUE_NEUTRAL, MoralAlignment.LAWFUL_NEUTRAL
            ]:
                compatibility += 0.2
        
        # Check for conflicts with existing arcs
        for existing_arc in existing_arcs:
            if existing_arc.is_active:
                # Some arc types conflict
                conflicts = {
                    ArcType.REDEMPTION: [ArcType.FALL_FROM_GRACE, ArcType.CORRUPTION],
                    ArcType.FALL_FROM_GRACE: [ArcType.REDEMPTION, ArcType.HERO_JOURNEY],
                    ArcType.HERO_JOURNEY: [ArcType.FALL_FROM_GRACE, ArcType.CORRUPTION]
                }
                
                if existing_arc.arc_type in conflicts.get(arc_type, []):
                    compatibility -= 0.3
        
        return max(0.0, min(1.0, compatibility))

    async def _get_character_arc(
        self,
        arc_id: str,
        db_session: Optional[Session]
    ) -> Optional[CharacterArcSchema]:
        """Get character arc from database."""
        
        # Mock implementation
        return CharacterArcSchema(
            id=arc_id,
            character_id="char_123",
            arc_name="Hero's Journey",
            arc_type=ArcType.HERO_JOURNEY,
            current_stage=ArcStage.TESTS,
            stages_completed=[ArcStage.ORDINARY_WORLD, ArcStage.CALL_TO_ADVENTURE],
            stages_remaining=[ArcStage.APPROACH, ArcStage.ORDEAL, ArcStage.REWARD],
            stage_progress=0.6,
            overall_progress=0.4
        )

    async def _get_character_arcs(
        self,
        character_id: str,
        db_session: Optional[Session]
    ) -> List[CharacterArcSchema]:
        """Get all arcs for a character."""
        
        # Mock implementation
        return [
            CharacterArcSchema(
                id="arc_001",
                character_id=character_id,
                arc_name="Hero's Journey",
                arc_type=ArcType.HERO_JOURNEY,
                current_stage=ArcStage.TESTS,
                stages_completed=[ArcStage.ORDINARY_WORLD],
                stages_remaining=[ArcStage.APPROACH, ArcStage.ORDEAL],
                overall_progress=0.6,
                is_active=True
            ),
            CharacterArcSchema(
                id="arc_002",
                character_id=character_id,
                arc_name="Coming of Age",
                arc_type=ArcType.COMING_OF_AGE,
                current_stage=ArcStage.RETURN,
                stages_completed=[ArcStage.ORDINARY_WORLD, ArcStage.TESTS],
                stages_remaining=[],
                overall_progress=1.0,
                is_completed=True
            )
        ]

    async def _create_arc_milestones(
        self,
        arc: CharacterArcSchema,
        db_session: Optional[Session]
    ) -> None:
        """Create milestones for the arc."""
        
        # In a real implementation, this would create milestone records
        logger.info(f"Created milestones for arc {arc.id}")

    async def _calculate_estimated_completion(
        self,
        arc: CharacterArcSchema
    ) -> Optional[datetime]:
        """Calculate estimated completion date for arc."""
        
        duration_mapping = {
            "short": 30,    # 30 days
            "medium": 90,   # 3 months
            "long": 180,    # 6 months
            "epic": 365     # 1 year
        }
        
        days = duration_mapping.get(arc.estimated_duration, 90)
        return datetime.utcnow() + timedelta(days=days)

    async def _save_arc_progress(
        self,
        arc: CharacterArcSchema,
        request: ArcProgressRequest,
        previous_stage: ArcStage,
        new_stage: ArcStage,
        progress_amount: float,
        changes: List[Dict[str, Any]],
        db_session: Optional[Session]
    ) -> None:
        """Save arc progress event."""
        
        # In a real implementation, this would save to database
        logger.info(f"Arc progress: {arc.character_id} - {arc.arc_name} - {progress_amount:.2f}")

    async def _identify_new_opportunities(
        self,
        arc: CharacterArcSchema,
        stage: ArcStage,
        changes: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify new opportunities from arc progression."""
        
        opportunities = []
        
        # Stage-specific opportunities
        stage_opportunities = {
            ArcStage.MENTOR: ["Seek guidance", "Learn new skills", "Form mentor relationship"],
            ArcStage.TESTS: ["Form alliances", "Develop abilities", "Prove worthiness"],
            ArcStage.ORDEAL: ["Face greatest fear", "Make ultimate sacrifice", "Transform completely"],
            ArcStage.REWARD: ["Gain new abilities", "Achieve recognition", "Access hidden knowledge"]
        }
        
        opportunities.extend(stage_opportunities.get(stage, []))
        
        # Change-based opportunities
        for change in changes:
            if change["type"] == ChangeType.PERSONALITY.value:
                opportunities.append(f"Explore new aspects of {change['target']}")
            elif change["type"] == ChangeType.SKILL.value:
                opportunities.append(f"Apply new {change['target']} abilities")
        
        return opportunities

    async def _identify_arc_conflicts(
        self,
        arcs: List[CharacterArcSchema]
    ) -> List[str]:
        """Identify conflicts between active arcs."""
        
        conflicts = []
        active_arcs = [arc for arc in arcs if arc.is_active]
        
        for i, arc_a in enumerate(active_arcs):
            for arc_b in active_arcs[i+1:]:
                # Check for conflicting arc types
                if (arc_a.arc_type == ArcType.REDEMPTION and 
                    arc_b.arc_type == ArcType.FALL_FROM_GRACE):
                    conflicts.append("Redemption arc conflicts with fall from grace")
                
                # Check for conflicting target alignments
                if (arc_a.target_alignment and arc_b.target_alignment and
                    arc_a.target_alignment != arc_b.target_alignment):
                    conflicts.append("Conflicting moral development paths")
        
        return conflicts

    async def _generate_arc_recommendations(
        self,
        arcs: List[CharacterArcSchema],
        character_id: str
    ) -> List[str]:
        """Generate recommendations for arc management."""
        
        recommendations = []
        
        active_arcs = [arc for arc in arcs if arc.is_active]
        
        if len(active_arcs) == 0:
            recommendations.append("Consider starting a new character development arc")
        elif len(active_arcs) > 3:
            recommendations.append("Too many active arcs - consider focusing on 2-3 main storylines")
        
        # Check for stalled arcs
        for arc in active_arcs:
            if arc.last_progress and (datetime.utcnow() - arc.last_progress).days > 30:
                recommendations.append(f"Arc '{arc.arc_name}' hasn't progressed recently - create catalyst events")
        
        # Check for completion opportunities
        near_complete = [arc for arc in active_arcs if arc.overall_progress > 0.8]
        if near_complete:
            recommendations.append("Some arcs are near completion - plan climactic events")
        
        return recommendations