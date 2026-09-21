#!/usr/bin/env python3

import asyncio
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import random
import uuid
import statistics

class MistakeType(Enum):
    PROCEDURAL = "procedural"        # Wrong sequence or steps
    CONCEPTUAL = "conceptual"        # Misunderstanding concepts
    TECHNICAL = "technical"          # Tool/equipment issues
    SAFETY = "safety"               # Safety violations
    PRECISION = "precision"         # Measurement/accuracy errors
    TIMING = "timing"               # Too fast/slow, wrong timing
    ATTENTION = "attention"         # Missing details, skipping steps
    INTERPRETATION = "interpretation" # Misreading instructions

class MistakeSeverity(Enum):
    MINOR = "minor"           # Easily correctable, minimal impact
    MODERATE = "moderate"     # Some rework needed, learning opportunity
    MAJOR = "major"          # Significant correction needed
    CRITICAL = "critical"    # Safety risk or major failure

class LearningStyle(Enum):
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    READING = "reading"
    MULTIMODAL = "multimodal"

class InterventionType(Enum):
    IMMEDIATE_CORRECTION = "immediate_correction"
    GUIDED_DISCOVERY = "guided_discovery"
    PRACTICE_EXERCISE = "practice_exercise"
    CONCEPTUAL_REVIEW = "conceptual_review"
    DEMONSTRATION = "demonstration"
    PEER_EXAMPLE = "peer_example"
    SCAFFOLDED_SUPPORT = "scaffolded_support"

@dataclass
class Mistake:
    id: str
    user_id: str
    tutorial_id: str
    step_id: str
    mistake_type: MistakeType
    severity: MistakeSeverity
    description: str
    user_action: str             # What the user did
    expected_action: str         # What was expected
    context: Dict[str, Any]      # Environmental/situational context
    detection_method: str        # How the mistake was detected
    timestamp: str
    resolution_time: Optional[float]  # Time to correct in minutes
    attempts_to_correct: int
    user_frustration_level: int  # 1-10 scale
    success_after_correction: bool

@dataclass
class LearningIntervention:
    id: str
    mistake_id: str
    intervention_type: InterventionType
    title: str
    description: str
    content: Dict[str, Any]      # Specific intervention content
    estimated_duration: int      # minutes
    difficulty_adjustment: int   # -2 to +2 scale
    learning_objectives: List[str]
    success_criteria: List[str]
    follow_up_actions: List[str]
    created_at: str

@dataclass
class LearningPath:
    id: str
    user_id: str
    original_tutorial_id: str
    path_name: str
    trigger_mistakes: List[str]   # Mistake IDs that triggered this path
    interventions: List[LearningIntervention]
    alternative_explanations: List[Dict[str, Any]]
    practice_exercises: List[Dict[str, Any]]
    assessment_checkpoints: List[Dict[str, Any]]
    personalization_data: Dict[str, Any]
    estimated_total_time: int    # minutes
    completion_rate: float       # 0.0 to 1.0
    effectiveness_score: float   # 0.0 to 1.0
    created_at: str
    updated_at: str

@dataclass
class UserLearningProfile:
    user_id: str
    learning_style: LearningStyle
    mistake_patterns: Dict[MistakeType, int]  # Count of each mistake type
    common_difficulties: List[str]
    strengths: List[str]
    preferred_interventions: List[InterventionType]
    attention_span: int          # minutes
    frustration_tolerance: int   # 1-10 scale
    learning_pace: str          # slow, normal, fast
    help_seeking_behavior: str   # proactive, reactive, resistant
    meta_learning_skills: int    # 1-10 scale (ability to learn how to learn)
    created_at: str
    updated_at: str

class MistakeDetector:
    def __init__(self):
        self.detection_patterns = {
            MistakeType.PROCEDURAL: {
                "indicators": ["wrong_sequence", "skipped_step", "repeated_step"],
                "context_clues": ["user_went_back", "confused_navigation", "long_pause"],
                "validation_methods": ["step_sequence_check", "prerequisite_validation"]
            },
            MistakeType.CONCEPTUAL: {
                "indicators": ["incorrect_answer", "wrong_approach", "misapplied_concept"],
                "context_clues": ["multiple_wrong_attempts", "consistent_error_pattern"],
                "validation_methods": ["concept_understanding_test", "explanation_analysis"]
            },
            MistakeType.TECHNICAL: {
                "indicators": ["tool_misuse", "equipment_error", "technical_failure"],
                "context_clues": ["repeated_failures", "error_messages", "system_issues"],
                "validation_methods": ["tool_usage_check", "system_diagnostics"]
            },
            MistakeType.SAFETY: {
                "indicators": ["unsafe_action", "skipped_safety_step", "risk_behavior"],
                "context_clues": ["safety_warning_ignored", "protective_equipment_not_used"],
                "validation_methods": ["safety_protocol_check", "risk_assessment"]
            }
        }

    async def detect_mistake(self, user_action: Dict[str, Any], 
                           expected_action: Dict[str, Any],
                           context: Dict[str, Any]) -> Optional[Mistake]:
        """Detect if a user action constitutes a mistake."""
        
        # Compare user action with expected action
        discrepancies = self._find_action_discrepancies(user_action, expected_action)
        
        if not discrepancies:
            return None  # No mistake detected
        
        # Classify the mistake type
        mistake_type = await self._classify_mistake_type(discrepancies, context)
        
        # Determine severity
        severity = await self._assess_mistake_severity(discrepancies, context, mistake_type)
        
        # Create mistake record
        mistake = Mistake(
            id=str(uuid.uuid4()),
            user_id=context.get("user_id", "unknown"),
            tutorial_id=context.get("tutorial_id", "unknown"),
            step_id=context.get("step_id", "unknown"),
            mistake_type=mistake_type,
            severity=severity,
            description=await self._generate_mistake_description(discrepancies, mistake_type),
            user_action=json.dumps(user_action),
            expected_action=json.dumps(expected_action),
            context=context,
            detection_method="automated_comparison",
            timestamp=datetime.now().isoformat(),
            resolution_time=None,
            attempts_to_correct=0,
            user_frustration_level=context.get("frustration_level", 3),
            success_after_correction=False
        )
        
        return mistake

    def _find_action_discrepancies(self, user_action: Dict[str, Any], 
                                 expected_action: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find discrepancies between user and expected actions."""
        
        discrepancies = []
        
        # Check action type
        if user_action.get("type") != expected_action.get("type"):
            discrepancies.append({
                "category": "action_type",
                "user_value": user_action.get("type"),
                "expected_value": expected_action.get("type"),
                "severity": "major"
            })
        
        # Check parameters
        user_params = user_action.get("parameters", {})
        expected_params = expected_action.get("parameters", {})
        
        for key, expected_value in expected_params.items():
            user_value = user_params.get(key)
            
            if user_value != expected_value:
                # Check if it's a numerical tolerance issue
                if isinstance(expected_value, (int, float)) and isinstance(user_value, (int, float)):
                    tolerance = expected_params.get(f"{key}_tolerance", 0.1)
                    if abs(user_value - expected_value) <= tolerance:
                        continue  # Within tolerance
                
                discrepancies.append({
                    "category": "parameter",
                    "parameter": key,
                    "user_value": user_value,
                    "expected_value": expected_value,
                    "severity": self._assess_parameter_severity(key, user_value, expected_value)
                })
        
        # Check timing
        user_timing = user_action.get("timing", {})
        expected_timing = expected_action.get("timing", {})
        
        if expected_timing:
            if user_timing.get("duration") and expected_timing.get("max_duration"):
                if user_timing["duration"] > expected_timing["max_duration"]:
                    discrepancies.append({
                        "category": "timing",
                        "issue": "too_slow",
                        "user_duration": user_timing["duration"],
                        "max_duration": expected_timing["max_duration"],
                        "severity": "minor"
                    })
        
        # Check sequence
        if "sequence_position" in user_action and "sequence_position" in expected_action:
            if user_action["sequence_position"] != expected_action["sequence_position"]:
                discrepancies.append({
                    "category": "sequence",
                    "user_position": user_action["sequence_position"],
                    "expected_position": expected_action["sequence_position"],
                    "severity": "moderate"
                })
        
        return discrepancies

    async def _classify_mistake_type(self, discrepancies: List[Dict[str, Any]], 
                                   context: Dict[str, Any]) -> MistakeType:
        """Classify the type of mistake based on discrepancies and context."""
        
        # Analyze discrepancy categories
        categories = [d["category"] for d in discrepancies]
        
        if "sequence" in categories:
            return MistakeType.PROCEDURAL
        
        if "action_type" in categories:
            # Could be conceptual or procedural
            if context.get("concept_heavy", False):
                return MistakeType.CONCEPTUAL
            else:
                return MistakeType.PROCEDURAL
        
        if "timing" in categories:
            return MistakeType.TIMING
        
        if "parameter" in categories:
            # Check if parameters are safety-related
            safety_params = ["temperature", "pressure", "voltage", "safety_setting"]
            if any(d.get("parameter") in safety_params for d in discrepancies):
                return MistakeType.SAFETY
            else:
                return MistakeType.PRECISION
        
        # Default classification
        return MistakeType.ATTENTION

    async def _assess_mistake_severity(self, discrepancies: List[Dict[str, Any]], 
                                     context: Dict[str, Any],
                                     mistake_type: MistakeType) -> MistakeSeverity:
        """Assess the severity of the mistake."""
        
        # Safety mistakes are always critical
        if mistake_type == MistakeType.SAFETY:
            return MistakeSeverity.CRITICAL
        
        # Count high severity discrepancies
        major_count = sum(1 for d in discrepancies if d.get("severity") == "major")
        moderate_count = sum(1 for d in discrepancies if d.get("severity") == "moderate")
        
        # Context factors
        is_beginner = context.get("user_level", "intermediate") == "beginner"
        is_complex_step = context.get("step_complexity", "medium") == "high"
        
        if major_count >= 2 or (major_count >= 1 and is_complex_step):
            return MistakeSeverity.MAJOR
        elif major_count >= 1 or moderate_count >= 2:
            return MistakeSeverity.MODERATE
        else:
            return MistakeSeverity.MINOR

    def _assess_parameter_severity(self, parameter: str, user_value: Any, expected_value: Any) -> str:
        """Assess severity of a parameter mismatch."""
        
        critical_params = ["safety_setting", "temperature", "voltage", "pressure"]
        important_params = ["position", "orientation", "size", "count"]
        
        if parameter in critical_params:
            return "major"
        elif parameter in important_params:
            return "moderate"
        else:
            return "minor"

    async def _generate_mistake_description(self, discrepancies: List[Dict[str, Any]], 
                                          mistake_type: MistakeType) -> str:
        """Generate human-readable mistake description."""
        
        if not discrepancies:
            return "Unknown mistake detected"
        
        primary_discrepancy = discrepancies[0]
        
        descriptions = {
            "action_type": f"Performed {primary_discrepancy['user_value']} instead of {primary_discrepancy['expected_value']}",
            "parameter": f"Used {primary_discrepancy['user_value']} for {primary_discrepancy['parameter']} instead of {primary_discrepancy['expected_value']}",
            "sequence": f"Performed step {primary_discrepancy['user_position']} instead of step {primary_discrepancy['expected_position']}",
            "timing": f"Action took too long ({primary_discrepancy['user_duration']} vs max {primary_discrepancy['max_duration']})"
        }
        
        base_description = descriptions.get(primary_discrepancy["category"], "Action did not match expectations")
        
        if len(discrepancies) > 1:
            base_description += f" (and {len(discrepancies) - 1} other issues)"
        
        return base_description

class LearningPathGenerator:
    def __init__(self):
        self.intervention_templates = {
            MistakeType.PROCEDURAL: [
                {
                    "type": InterventionType.DEMONSTRATION,
                    "title": "Step-by-step demonstration",
                    "content_template": "Watch this demonstration of the correct procedure"
                },
                {
                    "type": InterventionType.PRACTICE_EXERCISE,
                    "title": "Procedure practice",
                    "content_template": "Practice the correct sequence with guided feedback"
                }
            ],
            MistakeType.CONCEPTUAL: [
                {
                    "type": InterventionType.CONCEPTUAL_REVIEW,
                    "title": "Concept explanation",
                    "content_template": "Review the underlying concepts and principles"
                },
                {
                    "type": InterventionType.GUIDED_DISCOVERY,
                    "title": "Guided exploration",
                    "content_template": "Explore the concept through guided questions"
                }
            ],
            MistakeType.SAFETY: [
                {
                    "type": InterventionType.IMMEDIATE_CORRECTION,
                    "title": "Safety correction",
                    "content_template": "Immediate safety instruction and protocol review"
                }
            ],
            MistakeType.PRECISION: [
                {
                    "type": InterventionType.PRACTICE_EXERCISE,
                    "title": "Precision practice",
                    "content_template": "Practice exercises focused on accuracy and measurement"
                }
            ]
        }
        
        self.learning_style_adaptations = {
            LearningStyle.VISUAL: {
                "preferred_media": ["diagrams", "videos", "animations", "infographics"],
                "content_modifications": ["add_visual_aids", "color_coding", "spatial_organization"]
            },
            LearningStyle.AUDITORY: {
                "preferred_media": ["audio_explanations", "discussions", "verbal_instructions"],
                "content_modifications": ["add_narration", "verbal_emphasis", "sound_cues"]
            },
            LearningStyle.KINESTHETIC: {
                "preferred_media": ["hands_on_practice", "simulations", "physical_models"],
                "content_modifications": ["interactive_elements", "movement_based", "tactile_feedback"]
            },
            LearningStyle.READING: {
                "preferred_media": ["text_explanations", "written_instructions", "reference_materials"],
                "content_modifications": ["detailed_text", "structured_content", "additional_reading"]
            }
        }

    async def generate_learning_path(self, mistake: Mistake, 
                                   user_profile: UserLearningProfile,
                                   tutorial_context: Dict[str, Any]) -> LearningPath:
        """Generate a personalized learning path based on a mistake."""
        
        path_id = str(uuid.uuid4())
        
        # Generate interventions based on mistake type and user profile
        interventions = await self._generate_interventions(mistake, user_profile)
        
        # Create alternative explanations
        alternatives = await self._generate_alternative_explanations(mistake, user_profile)
        
        # Create practice exercises
        practice_exercises = await self._generate_practice_exercises(mistake, user_profile)
        
        # Create assessment checkpoints
        assessments = await self._generate_assessment_checkpoints(mistake, user_profile)
        
        # Calculate estimated time
        total_time = sum(intervention.estimated_duration for intervention in interventions)
        total_time += sum(ex.get("duration", 10) for ex in practice_exercises)
        total_time += sum(assess.get("duration", 5) for assess in assessments)
        
        # Personalization data
        personalization = {
            "learning_style": user_profile.learning_style.value,
            "difficulty_adjustment": self._calculate_difficulty_adjustment(mistake, user_profile),
            "pacing_adjustment": self._calculate_pacing_adjustment(user_profile),
            "support_level": self._calculate_support_level(mistake, user_profile)
        }
        
        return LearningPath(
            id=path_id,
            user_id=user_profile.user_id,
            original_tutorial_id=mistake.tutorial_id,
            path_name=f"Learning path for {mistake.mistake_type.value} mistake",
            trigger_mistakes=[mistake.id],
            interventions=interventions,
            alternative_explanations=alternatives,
            practice_exercises=practice_exercises,
            assessment_checkpoints=assessments,
            personalization_data=personalization,
            estimated_total_time=total_time,
            completion_rate=0.0,
            effectiveness_score=0.0,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

    async def _generate_interventions(self, mistake: Mistake, 
                                    user_profile: UserLearningProfile) -> List[LearningIntervention]:
        """Generate appropriate interventions for the mistake."""
        
        interventions = []
        templates = self.intervention_templates.get(mistake.mistake_type, [])
        
        # Select interventions based on mistake severity
        if mistake.severity in [MistakeSeverity.CRITICAL, MistakeSeverity.MAJOR]:
            # Use all available interventions
            selected_templates = templates
        else:
            # Use subset based on user preferences
            selected_templates = templates[:2]  # Use first two
        
        for template in selected_templates:
            intervention = await self._create_intervention_from_template(
                template, mistake, user_profile
            )
            interventions.append(intervention)
        
        return interventions

    async def _create_intervention_from_template(self, template: Dict[str, Any], 
                                               mistake: Mistake,
                                               user_profile: UserLearningProfile) -> LearningIntervention:
        """Create intervention from template."""
        
        intervention_id = str(uuid.uuid4())
        
        # Adapt content for learning style
        content = await self._adapt_content_for_learning_style(
            template["content_template"], 
            user_profile.learning_style,
            mistake
        )
        
        # Calculate duration based on user profile
        base_duration = self._get_base_intervention_duration(template["type"])
        duration_adjustment = 1.0
        
        if user_profile.learning_pace == "slow":
            duration_adjustment = 1.5
        elif user_profile.learning_pace == "fast":
            duration_adjustment = 0.7
        
        estimated_duration = int(base_duration * duration_adjustment)
        
        # Generate learning objectives
        objectives = await self._generate_learning_objectives(mistake, template["type"])
        
        # Generate success criteria
        criteria = await self._generate_success_criteria(mistake, template["type"])
        
        # Generate follow-up actions
        follow_ups = await self._generate_follow_up_actions(mistake, user_profile)
        
        return LearningIntervention(
            id=intervention_id,
            mistake_id=mistake.id,
            intervention_type=template["type"],
            title=template["title"],
            description=template["content_template"],
            content=content,
            estimated_duration=estimated_duration,
            difficulty_adjustment=self._calculate_difficulty_adjustment(mistake, user_profile),
            learning_objectives=objectives,
            success_criteria=criteria,
            follow_up_actions=follow_ups,
            created_at=datetime.now().isoformat()
        )

    async def _adapt_content_for_learning_style(self, base_content: str, 
                                              learning_style: LearningStyle,
                                              mistake: Mistake) -> Dict[str, Any]:
        """Adapt intervention content for user's learning style."""
        
        adaptations = self.learning_style_adaptations.get(learning_style, {})
        preferred_media = adaptations.get("preferred_media", [])
        modifications = adaptations.get("content_modifications", [])
        
        content = {
            "base_text": base_content,
            "media_elements": [],
            "interactive_elements": [],
            "style_modifications": modifications
        }
        
        # Add media elements based on learning style
        if "videos" in preferred_media:
            content["media_elements"].append({
                "type": "video",
                "title": "Visual demonstration",
                "url": f"/videos/mistake_correction_{mistake.mistake_type.value}.mp4",
                "duration": 120
            })
        
        if "audio_explanations" in preferred_media:
            content["media_elements"].append({
                "type": "audio",
                "title": "Audio explanation",
                "url": f"/audio/explanation_{mistake.mistake_type.value}.mp3",
                "duration": 90
            })
        
        if "hands_on_practice" in preferred_media:
            content["interactive_elements"].append({
                "type": "simulation",
                "title": "Interactive practice",
                "url": f"/simulations/practice_{mistake.mistake_type.value}",
                "estimated_time": 300
            })
        
        return content

    def _get_base_intervention_duration(self, intervention_type: InterventionType) -> int:
        """Get base duration in minutes for intervention type."""
        
        durations = {
            InterventionType.IMMEDIATE_CORRECTION: 5,
            InterventionType.GUIDED_DISCOVERY: 15,
            InterventionType.PRACTICE_EXERCISE: 20,
            InterventionType.CONCEPTUAL_REVIEW: 12,
            InterventionType.DEMONSTRATION: 8,
            InterventionType.PEER_EXAMPLE: 10,
            InterventionType.SCAFFOLDED_SUPPORT: 25
        }
        
        return durations.get(intervention_type, 15)

    async def _generate_learning_objectives(self, mistake: Mistake, 
                                          intervention_type: InterventionType) -> List[str]:
        """Generate learning objectives for the intervention."""
        
        base_objectives = {
            MistakeType.PROCEDURAL: [
                "Understand the correct sequence of steps",
                "Identify key decision points in the procedure",
                "Apply the procedure consistently"
            ],
            MistakeType.CONCEPTUAL: [
                "Grasp the underlying concepts",
                "Connect theory to practice",
                "Apply concepts to new situations"
            ],
            MistakeType.SAFETY: [
                "Understand safety protocols",
                "Identify safety risks",
                "Implement safety measures consistently"
            ],
            MistakeType.PRECISION: [
                "Achieve required accuracy standards",
                "Use measurement tools correctly",
                "Verify precision of results"
            ]
        }
        
        return base_objectives.get(mistake.mistake_type, ["Correct the identified mistake"])

    async def _generate_success_criteria(self, mistake: Mistake, 
                                       intervention_type: InterventionType) -> List[str]:
        """Generate success criteria for the intervention."""
        
        criteria = [
            "Demonstrates correct understanding",
            "Applies knowledge accurately",
            "Shows confidence in execution"
        ]
        
        if mistake.severity == MistakeSeverity.CRITICAL:
            criteria.append("Passes safety verification")
        
        if mistake.mistake_type == MistakeType.PRECISION:
            criteria.append("Achieves required precision standards")
        
        return criteria

    async def _generate_follow_up_actions(self, mistake: Mistake, 
                                        user_profile: UserLearningProfile) -> List[str]:
        """Generate follow-up actions for the intervention."""
        
        actions = ["Complete practice exercises", "Self-assessment quiz"]
        
        if user_profile.help_seeking_behavior == "resistant":
            actions.append("Optional additional resources")
        else:
            actions.append("Schedule follow-up check")
        
        if mistake.severity in [MistakeSeverity.MAJOR, MistakeSeverity.CRITICAL]:
            actions.append("Supervisor/mentor review required")
        
        return actions

    async def _generate_alternative_explanations(self, mistake: Mistake, 
                                               user_profile: UserLearningProfile) -> List[Dict[str, Any]]:
        """Generate alternative explanations for the concept."""
        
        explanations = []
        
        # Different perspectives based on learning style
        if user_profile.learning_style == LearningStyle.VISUAL:
            explanations.append({
                "type": "visual_analogy",
                "title": "Visual analogy explanation",
                "content": "Think of this like...",
                "media": "diagram"
            })
        
        if user_profile.learning_style == LearningStyle.KINESTHETIC:
            explanations.append({
                "type": "physical_analogy",
                "title": "Physical world comparison",
                "content": "This is similar to when you...",
                "media": "animation"
            })
        
        # Difficulty level alternatives
        explanations.append({
            "type": "simplified",
            "title": "Simplified explanation",
            "content": "In simple terms...",
            "difficulty": "easy"
        })
        
        explanations.append({
            "type": "detailed",
            "title": "Detailed explanation",
            "content": "The complete technical explanation...",
            "difficulty": "advanced"
        })
        
        return explanations

    async def _generate_practice_exercises(self, mistake: Mistake, 
                                         user_profile: UserLearningProfile) -> List[Dict[str, Any]]:
        """Generate practice exercises for the mistake type."""
        
        exercises = []
        
        if mistake.mistake_type == MistakeType.PROCEDURAL:
            exercises.append({
                "type": "sequence_practice",
                "title": "Step sequence practice",
                "description": "Practice the correct sequence multiple times",
                "duration": 15,
                "difficulty": "medium",
                "feedback_type": "immediate"
            })
        
        elif mistake.mistake_type == MistakeType.CONCEPTUAL:
            exercises.append({
                "type": "concept_application",
                "title": "Apply the concept",
                "description": "Apply the concept to different scenarios",
                "duration": 20,
                "difficulty": "medium",
                "feedback_type": "explanatory"
            })
        
        elif mistake.mistake_type == MistakeType.PRECISION:
            exercises.append({
                "type": "measurement_practice",
                "title": "Precision practice",
                "description": "Practice achieving required precision",
                "duration": 25,
                "difficulty": "high",
                "feedback_type": "performance_based"
            })
        
        # Adjust difficulty based on user profile
        for exercise in exercises:
            exercise["difficulty"] = self._adjust_exercise_difficulty(
                exercise["difficulty"], user_profile
            )
        
        return exercises

    async def _generate_assessment_checkpoints(self, mistake: Mistake, 
                                             user_profile: UserLearningProfile) -> List[Dict[str, Any]]:
        """Generate assessment checkpoints for the learning path."""
        
        assessments = []
        
        # Knowledge check
        assessments.append({
            "type": "knowledge_check",
            "title": "Understanding verification",
            "description": "Quick questions to verify understanding",
            "duration": 5,
            "questions": 3,
            "passing_score": 0.8
        })
        
        # Practical application
        if mistake.mistake_type in [MistakeType.PROCEDURAL, MistakeType.PRECISION]:
            assessments.append({
                "type": "practical_demonstration",
                "title": "Demonstrate correct procedure",
                "description": "Show that you can perform the task correctly",
                "duration": 10,
                "attempts_allowed": 3,
                "success_criteria": "Completes task without errors"
            })
        
        return assessments

    def _calculate_difficulty_adjustment(self, mistake: Mistake, 
                                       user_profile: UserLearningProfile) -> int:
        """Calculate difficulty adjustment (-2 to +2)."""
        
        adjustment = 0
        
        # Based on mistake severity
        if mistake.severity == MistakeSeverity.CRITICAL:
            adjustment -= 1  # Make easier
        elif mistake.severity == MistakeSeverity.MINOR:
            adjustment += 1  # Can be slightly harder
        
        # Based on user's pattern
        mistake_count = user_profile.mistake_patterns.get(mistake.mistake_type, 0)
        if mistake_count > 3:  # Recurring issue
            adjustment -= 1
        
        # Based on frustration level
        if mistake.user_frustration_level > 7:
            adjustment -= 1
        
        return max(-2, min(2, adjustment))

    def _calculate_pacing_adjustment(self, user_profile: UserLearningProfile) -> float:
        """Calculate pacing adjustment multiplier."""
        
        base_multiplier = 1.0
        
        if user_profile.learning_pace == "slow":
            base_multiplier = 1.3
        elif user_profile.learning_pace == "fast":
            base_multiplier = 0.8
        
        # Adjust for attention span
        if user_profile.attention_span < 10:
            base_multiplier *= 0.9  # Slightly faster to maintain attention
        elif user_profile.attention_span > 20:
            base_multiplier *= 1.1  # Can go slower for deeper understanding
        
        return base_multiplier

    def _calculate_support_level(self, mistake: Mistake, 
                               user_profile: UserLearningProfile) -> str:
        """Calculate required support level."""
        
        if mistake.severity == MistakeSeverity.CRITICAL:
            return "high"
        
        if user_profile.help_seeking_behavior == "resistant":
            return "minimal"
        elif user_profile.help_seeking_behavior == "proactive":
            return "moderate"
        else:
            return "standard"

    def _adjust_exercise_difficulty(self, base_difficulty: str, 
                                  user_profile: UserLearningProfile) -> str:
        """Adjust exercise difficulty based on user profile."""
        
        difficulty_levels = ["easy", "medium", "hard"]
        current_index = difficulty_levels.index(base_difficulty)
        
        # Adjust based on user's overall pattern
        if user_profile.frustration_tolerance < 5:
            current_index = max(0, current_index - 1)  # Make easier
        elif user_profile.frustration_tolerance > 8:
            current_index = min(2, current_index + 1)  # Make harder
        
        return difficulty_levels[current_index]

class MistakeBasedLearningSystem:
    def __init__(self, db_path: str = "mistake_learning.db"):
        self.db_path = db_path
        self.mistake_detector = MistakeDetector()
        self.path_generator = LearningPathGenerator()
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mistakes (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            tutorial_id TEXT,
            step_id TEXT,
            mistake_type TEXT,
            severity TEXT,
            description TEXT,
            user_action TEXT,
            expected_action TEXT,
            context TEXT,
            detection_method TEXT,
            timestamp TEXT,
            resolution_time REAL,
            attempts_to_correct INTEGER,
            user_frustration_level INTEGER,
            success_after_correction BOOLEAN
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_paths (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            original_tutorial_id TEXT,
            path_name TEXT,
            trigger_mistakes TEXT,
            interventions TEXT,
            alternative_explanations TEXT,
            practice_exercises TEXT,
            assessment_checkpoints TEXT,
            personalization_data TEXT,
            estimated_total_time INTEGER,
            completion_rate REAL,
            effectiveness_score REAL,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_learning_profiles (
            user_id TEXT PRIMARY KEY,
            learning_style TEXT,
            mistake_patterns TEXT,
            common_difficulties TEXT,
            strengths TEXT,
            preferred_interventions TEXT,
            attention_span INTEGER,
            frustration_tolerance INTEGER,
            learning_pace TEXT,
            help_seeking_behavior TEXT,
            meta_learning_skills INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        conn.commit()
        conn.close()

    async def process_user_action(self, user_action: Dict[str, Any], 
                                expected_action: Dict[str, Any],
                                context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user action and detect/handle mistakes."""
        
        # Detect mistake
        mistake = await self.mistake_detector.detect_mistake(user_action, expected_action, context)
        
        if not mistake:
            return {"mistake_detected": False, "message": "Action completed successfully"}
        
        # Save mistake
        await self._save_mistake(mistake)
        
        # Get or create user learning profile
        user_profile = await self.get_user_learning_profile(mistake.user_id)
        if not user_profile:
            user_profile = await self.create_user_learning_profile(mistake.user_id)
        
        # Update user profile with mistake pattern
        await self._update_mistake_patterns(user_profile, mistake)
        
        # Generate learning path
        learning_path = await self.path_generator.generate_learning_path(
            mistake, user_profile, context
        )
        
        # Save learning path
        await self._save_learning_path(learning_path)
        
        return {
            "mistake_detected": True,
            "mistake": asdict(mistake),
            "learning_path": asdict(learning_path),
            "immediate_action": await self._get_immediate_action(mistake),
            "encouragement_message": await self._generate_encouragement_message(mistake, user_profile)
        }

    async def _save_mistake(self, mistake: Mistake):
        """Save mistake to database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO mistakes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            mistake.id, mistake.user_id, mistake.tutorial_id, mistake.step_id,
            mistake.mistake_type.value, mistake.severity.value, mistake.description,
            mistake.user_action, mistake.expected_action, json.dumps(mistake.context),
            mistake.detection_method, mistake.timestamp, mistake.resolution_time,
            mistake.attempts_to_correct, mistake.user_frustration_level,
            mistake.success_after_correction
        ))
        
        conn.commit()
        conn.close()

    async def _save_learning_path(self, learning_path: LearningPath):
        """Save learning path to database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO learning_paths VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            learning_path.id, learning_path.user_id, learning_path.original_tutorial_id,
            learning_path.path_name, json.dumps(learning_path.trigger_mistakes),
            json.dumps([asdict(i) for i in learning_path.interventions]),
            json.dumps(learning_path.alternative_explanations),
            json.dumps(learning_path.practice_exercises),
            json.dumps(learning_path.assessment_checkpoints),
            json.dumps(learning_path.personalization_data),
            learning_path.estimated_total_time, learning_path.completion_rate,
            learning_path.effectiveness_score, learning_path.created_at,
            learning_path.updated_at
        ))
        
        conn.commit()
        conn.close()

    async def create_user_learning_profile(self, user_id: str, 
                                         initial_data: Dict[str, Any] = None) -> UserLearningProfile:
        """Create initial user learning profile."""
        
        if initial_data is None:
            initial_data = {}
        
        profile = UserLearningProfile(
            user_id=user_id,
            learning_style=LearningStyle(initial_data.get("learning_style", "multimodal")),
            mistake_patterns={},
            common_difficulties=[],
            strengths=[],
            preferred_interventions=[],
            attention_span=initial_data.get("attention_span", 15),
            frustration_tolerance=initial_data.get("frustration_tolerance", 5),
            learning_pace=initial_data.get("learning_pace", "normal"),
            help_seeking_behavior=initial_data.get("help_seeking_behavior", "reactive"),
            meta_learning_skills=initial_data.get("meta_learning_skills", 5),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        await self._save_user_learning_profile(profile)
        return profile

    async def _save_user_learning_profile(self, profile: UserLearningProfile):
        """Save user learning profile to database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO user_learning_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile.user_id, profile.learning_style.value,
            json.dumps(profile.mistake_patterns), json.dumps(profile.common_difficulties),
            json.dumps(profile.strengths), json.dumps([i.value for i in profile.preferred_interventions]),
            profile.attention_span, profile.frustration_tolerance, profile.learning_pace,
            profile.help_seeking_behavior, profile.meta_learning_skills,
            profile.created_at, profile.updated_at
        ))
        
        conn.commit()
        conn.close()

    async def get_user_learning_profile(self, user_id: str) -> Optional[UserLearningProfile]:
        """Get user learning profile from database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user_learning_profiles WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Reconstruct profile
        mistake_patterns = {MistakeType(k): v for k, v in json.loads(row[2]).items()}
        preferred_interventions = [InterventionType(i) for i in json.loads(row[5])]
        
        return UserLearningProfile(
            user_id=row[0], learning_style=LearningStyle(row[1]),
            mistake_patterns=mistake_patterns, common_difficulties=json.loads(row[3]),
            strengths=json.loads(row[4]), preferred_interventions=preferred_interventions,
            attention_span=row[6], frustration_tolerance=row[7], learning_pace=row[8],
            help_seeking_behavior=row[9], meta_learning_skills=row[10],
            created_at=row[11], updated_at=row[12]
        )

    async def _update_mistake_patterns(self, profile: UserLearningProfile, mistake: Mistake):
        """Update user's mistake patterns."""
        
        if mistake.mistake_type not in profile.mistake_patterns:
            profile.mistake_patterns[mistake.mistake_type] = 0
        
        profile.mistake_patterns[mistake.mistake_type] += 1
        profile.updated_at = datetime.now().isoformat()
        
        # Update common difficulties if this mistake type becomes frequent
        if profile.mistake_patterns[mistake.mistake_type] >= 3:
            difficulty_description = f"Frequent {mistake.mistake_type.value} mistakes"
            if difficulty_description not in profile.common_difficulties:
                profile.common_difficulties.append(difficulty_description)
        
        await self._save_user_learning_profile(profile)

    async def _get_immediate_action(self, mistake: Mistake) -> Dict[str, Any]:
        """Get immediate action to take for the mistake."""
        
        if mistake.severity == MistakeSeverity.CRITICAL:
            return {
                "type": "stop_and_correct",
                "message": "Please stop and correct this safety issue immediately",
                "priority": "high"
            }
        elif mistake.severity == MistakeSeverity.MAJOR:
            return {
                "type": "guided_correction",
                "message": "Let's work through the correct approach together",
                "priority": "medium"
            }
        else:
            return {
                "type": "gentle_redirect",
                "message": "Here's a tip to help you get back on track",
                "priority": "low"
            }

    async def _generate_encouragement_message(self, mistake: Mistake, 
                                            user_profile: UserLearningProfile) -> str:
        """Generate encouraging message for the user."""
        
        messages = [
            "Mistakes are part of learning! Let's figure this out together.",
            "No worries - this is a common challenge. Here's how to handle it.",
            "Great effort! Let me show you a technique that might help.",
            "You're making progress! This mistake will help you learn something important."
        ]
        
        if user_profile.frustration_tolerance < 5:
            # More supportive messages for low frustration tolerance
            supportive_messages = [
                "Take a deep breath. You're doing fine, and I'm here to help.",
                "This happens to everyone. Let's take it one step at a time.",
                "You're learning, and that's what matters. Let's try a different approach."
            ]
            return random.choice(supportive_messages)
        
        return random.choice(messages)

    async def get_learning_path_progress(self, path_id: str) -> Dict[str, Any]:
        """Get progress information for a learning path."""
        
        # This would track user progress through the learning path
        # For now, returning sample data
        return {
            "path_id": path_id,
            "completion_rate": 0.65,
            "current_intervention": "practice_exercise",
            "time_spent": 35,  # minutes
            "estimated_remaining": 20,  # minutes
            "interventions_completed": 2,
            "assessments_passed": 1,
            "next_action": "Complete precision practice exercise"
        }

if __name__ == "__main__":
    async def main():
        learning_system = MistakeBasedLearningSystem()
        
        # Create a user profile
        user_profile = await learning_system.create_user_learning_profile(
            "user123", 
            {
                "learning_style": "visual",
                "attention_span": 12,
                "frustration_tolerance": 4,
                "learning_pace": "normal"
            }
        )
        
        print(f"Created learning profile for user: {user_profile.user_id}")
        print(f"Learning style: {user_profile.learning_style.value}")
        print(f"Attention span: {user_profile.attention_span} minutes")
        
        # Simulate a user action that contains a mistake
        user_action = {
            "type": "measurement",
            "parameters": {"value": 15.8, "unit": "cm", "tool": "ruler"},
            "timing": {"duration": 45},
            "sequence_position": 3
        }
        
        expected_action = {
            "type": "measurement", 
            "parameters": {"value": 12.5, "unit": "cm", "tool": "ruler"},
            "timing": {"max_duration": 60},
            "sequence_position": 3
        }
        
        context = {
            "user_id": "user123",
            "tutorial_id": "tutorial_001", 
            "step_id": "step_05",
            "user_level": "beginner",
            "step_complexity": "medium",
            "frustration_level": 6
        }
        
        # Process the action
        result = await learning_system.process_user_action(user_action, expected_action, context)
        
        print(f"\nMistake detected: {result['mistake_detected']}")
        
        if result["mistake_detected"]:
            mistake = result["mistake"]
            print(f"Mistake type: {mistake['mistake_type']}")
            print(f"Severity: {mistake['severity']}")
            print(f"Description: {mistake['description']}")
            
            learning_path = result["learning_path"]
            print(f"\nLearning path created: {learning_path['path_name']}")
            print(f"Estimated time: {learning_path['estimated_total_time']} minutes")
            print(f"Number of interventions: {len(learning_path['interventions'])}")
            
            print(f"\nEncouragement: {result['encouragement_message']}")
            print(f"Immediate action: {result['immediate_action']['message']}")
    
    asyncio.run(main())