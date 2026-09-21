"""
Personality engine for consistent character behavior.
"""

import random
import math
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import numpy as np

from ..models.personality import (
    PersonalityProfile, PersonalityState, BehaviorPattern, PersonalityEvolution,
    PersonalityProfileSchema, PersonalityStateSchema, BehaviorPatternSchema,
    PersonalityAnalysis, BehaviorPrediction, PersonalityCompatibility,
    PersonalityDevelopmentPlan, PersonalityGenerationRequest,
    SituationalPersonalityModifier,
    PersonalityDimension, MoralAlignment, CoreValue, BehavioralTendency, CharacterArchetype
)
from ..models.base import EmotionType
from ..config import settings

class PersonalityGenerator:
    """Generates personality profiles for characters."""
    
    # Trait correlations and constraints
    TRAIT_CORRELATIONS = {
        "extraversion": {"agreeableness": 0.2, "neuroticism": -0.3},
        "agreeableness": {"conscientiousness": 0.3, "neuroticism": -0.2},
        "conscientiousness": {"neuroticism": -0.4, "openness": 0.1},
        "neuroticism": {"openness": -0.1},
        "openness": {"extraversion": 0.2}
    }
    
    # Archetype trait tendencies
    ARCHETYPE_TRAITS = {
        CharacterArchetype.HERO: {
            "extraversion": 0.7, "agreeableness": 0.8, "conscientiousness": 0.8,
            "neuroticism": 0.3, "openness": 0.6
        },
        CharacterArchetype.MENTOR: {
            "extraversion": 0.6, "agreeableness": 0.9, "conscientiousness": 0.9,
            "neuroticism": 0.2, "openness": 0.9
        },
        CharacterArchetype.SHADOW: {
            "extraversion": 0.5, "agreeableness": 0.2, "conscientiousness": 0.4,
            "neuroticism": 0.6, "openness": 0.3
        },
        CharacterArchetype.TRICKSTER: {
            "extraversion": 0.8, "agreeableness": 0.4, "conscientiousness": 0.3,
            "neuroticism": 0.4, "openness": 0.9
        },
        CharacterArchetype.ALLY: {
            "extraversion": 0.6, "agreeableness": 0.8, "conscientiousness": 0.7,
            "neuroticism": 0.4, "openness": 0.6
        }
    }
    
    # Alignment-based value preferences
    ALIGNMENT_VALUES = {
        MoralAlignment.LAWFUL_GOOD: [CoreValue.JUSTICE, CoreValue.HONOR, CoreValue.FAMILY],
        MoralAlignment.CHAOTIC_GOOD: [CoreValue.FREEDOM, CoreValue.JUSTICE, CoreValue.LOVE],
        MoralAlignment.LAWFUL_EVIL: [CoreValue.POWER, CoreValue.LOYALTY, CoreValue.HONOR],
        MoralAlignment.CHAOTIC_EVIL: [CoreValue.POWER, CoreValue.REVENGE, CoreValue.WEALTH],
        MoralAlignment.TRUE_NEUTRAL: [CoreValue.SURVIVAL, CoreValue.KNOWLEDGE, CoreValue.PEACE]
    }
    
    @classmethod
    def generate_personality(cls, request: PersonalityGenerationRequest) -> PersonalityProfileSchema:
        """Generate a complete personality profile."""
        
        # Start with base traits or preferences
        if request.trait_preferences:
            traits = dict(request.trait_preferences)
        else:
            traits = {dim: random.uniform(0.1, 0.9) for dim in PersonalityDimension}
        
        # Apply archetype influence
        if request.desired_archetype:
            archetype_traits = cls.ARCHETYPE_TRAITS.get(request.desired_archetype, {})
            for trait, target in archetype_traits.items():
                # Blend with existing trait (70% archetype, 30% original)
                traits[trait] = traits[trait] * 0.3 + target * 0.7
        
        # Apply trait correlations for realism
        traits = cls._apply_trait_correlations(traits)
        
        # Ensure traits are within bounds
        for trait in traits:
            traits[trait] = max(0.0, min(1.0, traits[trait]))
        
        # Determine moral alignment
        alignment = request.moral_alignment or cls._determine_alignment(traits)
        
        # Select core values based on alignment and traits
        core_values = request.core_values or cls._select_core_values(alignment, traits)
        
        # Generate behavioral tendencies
        behavioral_tendencies = cls._generate_behavioral_tendencies(traits, alignment)
        
        # Generate trait descriptions
        positive_traits = cls._generate_positive_traits(traits, core_values)
        negative_traits = cls._generate_negative_traits(traits, alignment)
        quirks = cls._generate_quirks(traits)
        
        # Determine decision making and social styles
        decision_style = cls._determine_decision_making_style(traits)
        stress_response = cls._determine_stress_response(traits)
        social_style = cls._determine_social_style(traits)
        
        # Calculate consistency and adaptation parameters
        consistency = cls._calculate_trait_consistency(traits)
        adaptation = 1.0 - consistency
        
        return PersonalityProfileSchema(
            character_id="temp",  # Will be set by caller
            extraversion=traits.get(PersonalityDimension.EXTRAVERSION, 0.5),
            agreeableness=traits.get(PersonalityDimension.AGREEABLENESS, 0.5),
            conscientiousness=traits.get(PersonalityDimension.CONSCIENTIOUSNESS, 0.5),
            neuroticism=traits.get(PersonalityDimension.NEUROTICISM, 0.5),
            openness=traits.get(PersonalityDimension.OPENNESS, 0.5),
            moral_alignment=alignment,
            archetype=request.desired_archetype or CharacterArchetype.ALLY,
            core_values=core_values,
            behavioral_tendencies=behavioral_tendencies,
            positive_traits=positive_traits,
            negative_traits=negative_traits,
            quirks=quirks,
            decision_making_style=decision_style,
            stress_response=stress_response,
            social_style=social_style,
            trait_consistency=consistency,
            situational_adaptation=adaptation
        )
    
    @classmethod
    def _apply_trait_correlations(cls, traits: Dict[str, float]) -> Dict[str, float]:
        """Apply realistic correlations between personality traits."""
        adjusted_traits = traits.copy()
        
        for trait, correlations in cls.TRAIT_CORRELATIONS.items():
            if trait in traits:
                for correlated_trait, correlation in correlations.items():
                    if correlated_trait in traits:
                        # Apply correlation influence
                        influence = traits[trait] * correlation * 0.2
                        adjusted_traits[correlated_trait] += influence
        
        return adjusted_traits
    
    @classmethod
    def _determine_alignment(cls, traits: Dict[str, float]) -> MoralAlignment:
        """Determine moral alignment based on personality traits."""
        agreeableness = traits.get(PersonalityDimension.AGREEABLENESS, 0.5)
        conscientiousness = traits.get(PersonalityDimension.CONSCIENTIOUSNESS, 0.5)
        
        # Simple heuristic for alignment determination
        lawful = conscientiousness > 0.6
        chaotic = conscientiousness < 0.4
        good = agreeableness > 0.6
        evil = agreeableness < 0.4
        
        if lawful and good:
            return MoralAlignment.LAWFUL_GOOD
        elif lawful and evil:
            return MoralAlignment.LAWFUL_EVIL
        elif chaotic and good:
            return MoralAlignment.CHAOTIC_GOOD
        elif chaotic and evil:
            return MoralAlignment.CHAOTIC_EVIL
        elif good:
            return MoralAlignment.NEUTRAL_GOOD
        elif evil:
            return MoralAlignment.NEUTRAL_EVIL
        elif lawful:
            return MoralAlignment.LAWFUL_NEUTRAL
        elif chaotic:
            return MoralAlignment.CHAOTIC_NEUTRAL
        else:
            return MoralAlignment.TRUE_NEUTRAL
    
    @classmethod
    def _select_core_values(cls, alignment: MoralAlignment, traits: Dict[str, float]) -> List[CoreValue]:
        """Select core values based on alignment and traits."""
        base_values = cls.ALIGNMENT_VALUES.get(alignment, [CoreValue.SURVIVAL])
        
        # Add trait-influenced values
        additional_values = []
        
        if traits.get(PersonalityDimension.OPENNESS, 0.5) > 0.7:
            additional_values.append(CoreValue.KNOWLEDGE)
        
        if traits.get(PersonalityDimension.EXTRAVERSION, 0.5) > 0.7:
            additional_values.append(CoreValue.FAMILY)
        
        if traits.get(PersonalityDimension.NEUROTICISM, 0.5) > 0.7:
            additional_values.append(CoreValue.SURVIVAL)
        
        # Combine and limit to 3-5 values
        all_values = list(set(base_values + additional_values))
        return random.sample(all_values, min(5, len(all_values)))
    
    @classmethod
    def _generate_behavioral_tendencies(cls, traits: Dict[str, float], 
                                      alignment: MoralAlignment) -> List[BehavioralTendency]:
        """Generate behavioral tendencies based on traits and alignment."""
        tendencies = []
        
        agreeableness = traits.get(PersonalityDimension.AGREEABLENESS, 0.5)
        extraversion = traits.get(PersonalityDimension.EXTRAVERSION, 0.5)
        neuroticism = traits.get(PersonalityDimension.NEUROTICISM, 0.5)
        
        if agreeableness > 0.6:
            tendencies.append(BehavioralTendency.COOPERATIVE)
        elif agreeableness < 0.4:
            tendencies.append(BehavioralTendency.COMPETITIVE)
        
        if extraversion > 0.6:
            tendencies.append(BehavioralTendency.ASSERTIVE)
        elif extraversion < 0.4:
            tendencies.append(BehavioralTendency.PASSIVE)
        
        if neuroticism > 0.6:
            tendencies.append(BehavioralTendency.AGGRESSIVE)
        
        # Alignment influences
        if alignment in [MoralAlignment.LAWFUL_GOOD, MoralAlignment.NEUTRAL_GOOD]:
            tendencies.append(BehavioralTendency.ALTRUISTIC)
        elif alignment in [MoralAlignment.LAWFUL_EVIL, MoralAlignment.NEUTRAL_EVIL]:
            tendencies.append(BehavioralTendency.MANIPULATIVE)
        
        return list(set(tendencies))  # Remove duplicates
    
    @classmethod
    def _generate_positive_traits(cls, traits: Dict[str, float], 
                                core_values: List[CoreValue]) -> List[str]:
        """Generate positive personality trait descriptions."""
        positive_traits = []
        
        if traits.get(PersonalityDimension.AGREEABLENESS, 0.5) > 0.6:
            positive_traits.extend(["kind", "compassionate", "cooperative"])
        
        if traits.get(PersonalityDimension.CONSCIENTIOUSNESS, 0.5) > 0.6:
            positive_traits.extend(["reliable", "organized", "disciplined"])
        
        if traits.get(PersonalityDimension.EXTRAVERSION, 0.5) > 0.6:
            positive_traits.extend(["outgoing", "energetic", "sociable"])
        
        if traits.get(PersonalityDimension.OPENNESS, 0.5) > 0.6:
            positive_traits.extend(["creative", "curious", "open-minded"])
        
        if traits.get(PersonalityDimension.NEUROTICISM, 0.5) < 0.4:
            positive_traits.extend(["calm", "stable", "resilient"])
        
        # Add value-based traits
        if CoreValue.JUSTICE in core_values:
            positive_traits.append("fair")
        if CoreValue.LOYALTY in core_values:
            positive_traits.append("loyal")
        if CoreValue.HONOR in core_values:
            positive_traits.append("honorable")
        
        return random.sample(positive_traits, min(5, len(positive_traits)))
    
    @classmethod
    def _generate_negative_traits(cls, traits: Dict[str, float], 
                                alignment: MoralAlignment) -> List[str]:
        """Generate negative personality trait descriptions."""
        negative_traits = []
        
        if traits.get(PersonalityDimension.NEUROTICISM, 0.5) > 0.6:
            negative_traits.extend(["anxious", "moody", "irritable"])
        
        if traits.get(PersonalityDimension.AGREEABLENESS, 0.5) < 0.4:
            negative_traits.extend(["stubborn", "suspicious", "cold"])
        
        if traits.get(PersonalityDimension.CONSCIENTIOUSNESS, 0.5) < 0.4:
            negative_traits.extend(["disorganized", "careless", "impulsive"])
        
        if traits.get(PersonalityDimension.EXTRAVERSION, 0.5) < 0.4:
            negative_traits.extend(["withdrawn", "reserved", "solitary"])
        
        if traits.get(PersonalityDimension.OPENNESS, 0.5) < 0.4:
            negative_traits.extend(["conventional", "rigid", "close-minded"])
        
        # Alignment-based negative traits
        if alignment in [MoralAlignment.CHAOTIC_NEUTRAL, MoralAlignment.CHAOTIC_EVIL]:
            negative_traits.append("unpredictable")
        if alignment in [MoralAlignment.LAWFUL_EVIL, MoralAlignment.NEUTRAL_EVIL]:
            negative_traits.append("manipulative")
        
        return random.sample(negative_traits, min(3, len(negative_traits)))
    
    @classmethod
    def _generate_quirks(cls, traits: Dict[str, float]) -> List[str]:
        """Generate unique personality quirks."""
        quirk_pool = [
            "always adjusts their clothing before speaking",
            "tends to quote obscure literature",
            "collects small unusual objects",
            "has an excellent memory for faces but not names",
            "laughs at inappropriate moments",
            "speaks to animals as if they understand",
            "never sits with their back to a door",
            "counts things compulsively",
            "has strong opinions about food combinations",
            "remembers every slight ever committed against them"
        ]
        
        # Select 1-3 quirks based on openness
        openness = traits.get(PersonalityDimension.OPENNESS, 0.5)
        num_quirks = 1 if openness < 0.3 else 2 if openness < 0.7 else 3
        
        return random.sample(quirk_pool, num_quirks)
    
    @classmethod
    def _determine_decision_making_style(cls, traits: Dict[str, float]) -> str:
        """Determine decision making style from traits."""
        conscientiousness = traits.get(PersonalityDimension.CONSCIENTIOUSNESS, 0.5)
        openness = traits.get(PersonalityDimension.OPENNESS, 0.5)
        neuroticism = traits.get(PersonalityDimension.NEUROTICISM, 0.5)
        
        if conscientiousness > 0.7 and neuroticism < 0.4:
            return "analytical"
        elif openness > 0.7 and conscientiousness < 0.4:
            return "intuitive"
        elif neuroticism > 0.7:
            return "impulsive"
        else:
            return "balanced"
    
    @classmethod
    def _determine_stress_response(cls, traits: Dict[str, float]) -> str:
        """Determine stress response pattern from traits."""
        neuroticism = traits.get(PersonalityDimension.NEUROTICISM, 0.5)
        extraversion = traits.get(PersonalityDimension.EXTRAVERSION, 0.5)
        
        if neuroticism > 0.7:
            return "fight" if extraversion > 0.5 else "freeze"
        elif neuroticism > 0.4:
            return "flight" if extraversion < 0.5 else "fight"
        else:
            return "adaptive"
    
    @classmethod
    def _determine_social_style(cls, traits: Dict[str, float]) -> str:
        """Determine social interaction style from traits."""
        extraversion = traits.get(PersonalityDimension.EXTRAVERSION, 0.5)
        
        if extraversion > 0.6:
            return "extroverted"
        elif extraversion < 0.4:
            return "introverted"
        else:
            return "balanced"
    
    @classmethod
    def _calculate_trait_consistency(cls, traits: Dict[str, float]) -> float:
        """Calculate how consistent the character should be to their traits."""
        conscientiousness = traits.get(PersonalityDimension.CONSCIENTIOUSNESS, 0.5)
        neuroticism = traits.get(PersonalityDimension.NEUROTICISM, 0.5)
        
        # Higher conscientiousness and lower neuroticism = more consistent
        base_consistency = (conscientiousness + (1.0 - neuroticism)) / 2
        
        # Add some randomness but keep within reasonable bounds
        consistency = base_consistency + random.uniform(-0.1, 0.1)
        return max(0.3, min(0.9, consistency))

class BehaviorPredictor:
    """Predicts character behavior based on personality and situation."""
    
    def __init__(self):
        self.behavior_weights = self._initialize_behavior_weights()
    
    def _initialize_behavior_weights(self) -> Dict[str, Dict[str, float]]:
        """Initialize weights for behavior prediction."""
        return {
            "conversation": {
                PersonalityDimension.EXTRAVERSION: 0.8,
                PersonalityDimension.AGREEABLENESS: 0.6,
                PersonalityDimension.OPENNESS: 0.4
            },
            "combat": {
                PersonalityDimension.NEUROTICISM: -0.6,
                PersonalityDimension.CONSCIENTIOUSNESS: 0.7,
                PersonalityDimension.AGREEABLENESS: -0.3
            },
            "social": {
                PersonalityDimension.EXTRAVERSION: 0.9,
                PersonalityDimension.AGREEABLENESS: 0.8,
                PersonalityDimension.CONSCIENTIOUSNESS: 0.3
            },
            "decision": {
                PersonalityDimension.CONSCIENTIOUSNESS: 0.8,
                PersonalityDimension.OPENNESS: 0.5,
                PersonalityDimension.NEUROTICISM: -0.4
            }
        }
    
    def predict_behavior(self, 
                        personality: PersonalityProfileSchema,
                        situation_type: str,
                        context: Dict[str, Any]) -> BehaviorPrediction:
        """Predict behavior for a given situation."""
        
        # Get trait weights for situation
        weights = self.behavior_weights.get(situation_type, {})
        
        # Calculate behavior scores
        behavior_scores = {}
        
        if situation_type == "conversation":
            behavior_scores = self._predict_conversation_behavior(personality, context)
        elif situation_type == "combat":
            behavior_scores = self._predict_combat_behavior(personality, context)
        elif situation_type == "social":
            behavior_scores = self._predict_social_behavior(personality, context)
        elif situation_type == "decision":
            behavior_scores = self._predict_decision_behavior(personality, context)
        
        # Predict dialogue style
        dialogue_style = self._predict_dialogue_style(personality, situation_type, context)
        
        # Predict emotional response
        emotional_response = self._predict_emotional_response(personality, context)
        
        # Identify decision factors
        decision_factors = self._identify_decision_factors(personality, context)
        
        # Calculate confidence based on trait consistency
        confidence = personality.trait_consistency * 0.8 + random.uniform(0.1, 0.2)
        
        return BehaviorPrediction(
            situation_type=situation_type,
            predicted_actions=behavior_scores,
            dialogue_style=dialogue_style,
            emotional_response=emotional_response,
            decision_factors=decision_factors,
            confidence_level=confidence
        )
    
    def _predict_conversation_behavior(self, 
                                     personality: PersonalityProfileSchema,
                                     context: Dict[str, Any]) -> List[Dict[str, float]]:
        """Predict conversation behaviors."""
        behaviors = []
        
        if personality.extraversion > 0.6:
            behaviors.append({"action": "initiate_conversation", "probability": 0.8})
            behaviors.append({"action": "share_personal_stories", "probability": 0.7})
        else:
            behaviors.append({"action": "listen_actively", "probability": 0.8})
            behaviors.append({"action": "respond_when_asked", "probability": 0.9})
        
        if personality.agreeableness > 0.6:
            behaviors.append({"action": "show_empathy", "probability": 0.8})
            behaviors.append({"action": "avoid_conflict", "probability": 0.7})
        
        if personality.openness > 0.6:
            behaviors.append({"action": "ask_questions", "probability": 0.8})
            behaviors.append({"action": "discuss_ideas", "probability": 0.7})
        
        return behaviors
    
    def _predict_combat_behavior(self, 
                                personality: PersonalityProfileSchema,
                                context: Dict[str, Any]) -> List[Dict[str, float]]:
        """Predict combat behaviors."""
        behaviors = []
        
        if personality.neuroticism < 0.4:
            behaviors.append({"action": "stay_calm", "probability": 0.8})
            behaviors.append({"action": "tactical_thinking", "probability": 0.7})
        else:
            behaviors.append({"action": "aggressive_attack", "probability": 0.6})
            behaviors.append({"action": "panic_response", "probability": 0.4})
        
        if personality.conscientiousness > 0.6:
            behaviors.append({"action": "follow_strategy", "probability": 0.8})
            behaviors.append({"action": "protect_allies", "probability": 0.7})
        
        if personality.agreeableness < 0.4:
            behaviors.append({"action": "ruthless_tactics", "probability": 0.6})
        else:
            behaviors.append({"action": "minimize_harm", "probability": 0.7})
        
        return behaviors
    
    def _predict_social_behavior(self, 
                               personality: PersonalityProfileSchema,
                               context: Dict[str, Any]) -> List[Dict[str, float]]:
        """Predict social behaviors."""
        behaviors = []
        
        if personality.extraversion > 0.6:
            behaviors.append({"action": "seek_attention", "probability": 0.7})
            behaviors.append({"action": "make_jokes", "probability": 0.6})
        
        if personality.agreeableness > 0.6:
            behaviors.append({"action": "help_others", "probability": 0.8})
            behaviors.append({"action": "mediate_conflicts", "probability": 0.7})
        
        # Consider core values
        if CoreValue.JUSTICE in (personality.core_values or []):
            behaviors.append({"action": "defend_underdog", "probability": 0.8})
        
        if CoreValue.LOYALTY in (personality.core_values or []):
            behaviors.append({"action": "support_friends", "probability": 0.9})
        
        return behaviors
    
    def _predict_decision_behavior(self, 
                                 personality: PersonalityProfileSchema,
                                 context: Dict[str, Any]) -> List[Dict[str, float]]:
        """Predict decision-making behaviors."""
        behaviors = []
        
        if personality.conscientiousness > 0.6:
            behaviors.append({"action": "gather_information", "probability": 0.8})
            behaviors.append({"action": "consider_consequences", "probability": 0.9})
        
        if personality.openness > 0.6:
            behaviors.append({"action": "consider_alternatives", "probability": 0.8})
            behaviors.append({"action": "think_creatively", "probability": 0.7})
        
        if personality.neuroticism > 0.6:
            behaviors.append({"action": "worry_about_outcome", "probability": 0.8})
            behaviors.append({"action": "seek_reassurance", "probability": 0.6})
        
        return behaviors
    
    def _predict_dialogue_style(self, 
                              personality: PersonalityProfileSchema,
                              situation_type: str,
                              context: Dict[str, Any]) -> Dict[str, Any]:
        """Predict dialogue style modifications."""
        style = {
            "formality": "neutral",
            "emotiveness": 0.5,
            "directness": 0.5,
            "verbosity": 0.5
        }
        
        # Adjust based on personality
        if personality.conscientiousness > 0.6:
            style["formality"] = "formal"
        elif personality.conscientiousness < 0.4:
            style["formality"] = "casual"
        
        style["emotiveness"] = personality.neuroticism
        style["directness"] = 1.0 - personality.agreeableness
        style["verbosity"] = personality.extraversion
        
        return style
    
    def _predict_emotional_response(self, 
                                  personality: PersonalityProfileSchema,
                                  context: Dict[str, Any]) -> Dict[str, float]:
        """Predict emotional response intensities."""
        # Base emotional tendencies from personality
        emotions = {
            EmotionType.JOY: personality.extraversion * 0.6 + (1.0 - personality.neuroticism) * 0.4,
            EmotionType.ANGER: (1.0 - personality.agreeableness) * 0.7 + personality.neuroticism * 0.3,
            EmotionType.FEAR: personality.neuroticism * 0.8,
            EmotionType.SADNESS: personality.neuroticism * 0.6 + (1.0 - personality.extraversion) * 0.4,
            EmotionType.SURPRISE: personality.openness * 0.7,
            EmotionType.TRUST: personality.agreeableness * 0.8,
            EmotionType.DISGUST: (1.0 - personality.agreeableness) * 0.5,
            EmotionType.ANTICIPATION: personality.openness * 0.6 + personality.extraversion * 0.4
        }
        
        # Normalize emotions
        total = sum(emotions.values())
        if total > 0:
            emotions = {k: v / total for k, v in emotions.items()}
        
        return emotions
    
    def _identify_decision_factors(self, 
                                 personality: PersonalityProfileSchema,
                                 context: Dict[str, Any]) -> List[str]:
        """Identify factors that influence the character's decisions."""
        factors = []
        
        # Core value influences
        for value in (personality.core_values or []):
            factors.append(f"core_value_{value.value}")
        
        # Personality trait influences
        if personality.conscientiousness > 0.6:
            factors.append("long_term_consequences")
        if personality.agreeableness > 0.6:
            factors.append("impact_on_others")
        if personality.neuroticism > 0.6:
            factors.append("potential_risks")
        if personality.openness > 0.6:
            factors.append("novel_possibilities")
        
        # Behavioral tendency influences
        for tendency in (personality.behavioral_tendencies or []):
            factors.append(f"tendency_{tendency.value}")
        
        return factors

class PersonalityService:
    """Main service for personality management and behavior prediction."""
    
    def __init__(self):
        self.generator = PersonalityGenerator()
        self.predictor = BehaviorPredictor()
    
    def create_personality_profile(self, 
                                 profile_data: PersonalityProfileSchema, 
                                 db: Session) -> PersonalityProfile:
        """Create a new personality profile."""
        
        profile = PersonalityProfile(
            id=str(uuid4()),
            character_id=profile_data.character_id,
            extraversion=profile_data.extraversion,
            agreeableness=profile_data.agreeableness,
            conscientiousness=profile_data.conscientiousness,
            neuroticism=profile_data.neuroticism,
            openness=profile_data.openness,
            moral_alignment=profile_data.moral_alignment.value,
            archetype=profile_data.archetype.value,
            core_values=[v.value for v in profile_data.core_values] if profile_data.core_values else None,
            behavioral_tendencies=[t.value for t in profile_data.behavioral_tendencies] if profile_data.behavioral_tendencies else None,
            positive_traits=profile_data.positive_traits,
            negative_traits=profile_data.negative_traits,
            quirks=profile_data.quirks,
            decision_making_style=profile_data.decision_making_style,
            stress_response=profile_data.stress_response,
            social_style=profile_data.social_style,
            trait_consistency=profile_data.trait_consistency,
            situational_adaptation=profile_data.situational_adaptation,
            personality_plasticity=profile_data.personality_plasticity,
            character_development_rate=profile_data.character_development_rate
        )
        
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
        return profile
    
    def generate_personality_profile(self, 
                                   character_id: str,
                                   request: PersonalityGenerationRequest,
                                   db: Session) -> PersonalityProfile:
        """Generate and create a personality profile."""
        
        # Generate personality
        personality_schema = self.generator.generate_personality(request)
        personality_schema.character_id = character_id
        
        # Create in database
        return self.create_personality_profile(personality_schema, db)
    
    def predict_behavior(self, 
                        character_id: str,
                        situation_type: str,
                        context: Dict[str, Any],
                        db: Session) -> BehaviorPrediction:
        """Predict character behavior for a situation."""
        
        # Get personality profile
        profile = db.query(PersonalityProfile).filter(
            PersonalityProfile.character_id == character_id
        ).first()
        
        if not profile:
            raise ValueError("No personality profile found for character")
        
        # Convert to schema
        personality_schema = PersonalityProfileSchema.from_orm(profile)
        
        # Get current state modifiers
        current_state = db.query(PersonalityState).filter(
            PersonalityState.character_id == character_id
        ).order_by(PersonalityState.created_at.desc()).first()
        
        if current_state:
            # Apply state modifiers to context
            context["stress_level"] = current_state.stress_level
            context["fatigue_level"] = current_state.fatigue_level
            context["confidence_level"] = current_state.confidence_level
        
        # Predict behavior
        return self.predictor.predict_behavior(personality_schema, situation_type, context)
    
    def analyze_personality(self, character_id: str, db: Session) -> PersonalityAnalysis:
        """Analyze character personality for insights."""
        
        profile = db.query(PersonalityProfile).filter(
            PersonalityProfile.character_id == character_id
        ).first()
        
        if not profile:
            raise ValueError("No personality profile found for character")
        
        # Identify dominant traits
        traits = {
            "extraversion": profile.extraversion,
            "agreeableness": profile.agreeableness,
            "conscientiousness": profile.conscientiousness,
            "neuroticism": profile.neuroticism,
            "openness": profile.openness
        }
        
        dominant_traits = [
            {"trait": trait, "score": score, "level": self._categorize_trait_level(score)}
            for trait, score in sorted(traits.items(), key=lambda x: x[1], reverse=True)[:3]
        ]
        
        # Generate behavioral predictions
        behavioral_predictions = self._generate_behavioral_predictions(profile)
        
        # Determine interaction style
        interaction_style = self._analyze_interaction_style(profile)
        
        # Identify conflict triggers
        conflict_triggers = self._identify_conflict_triggers(profile)
        
        # Analyze motivation drivers
        motivation_drivers = self._analyze_motivation_drivers(profile)
        
        # Predict relationship patterns
        relationship_patterns = self._predict_relationship_patterns(profile)
        
        # Assess growth potential
        growth_potential = self._assess_growth_potential(profile)
        
        return PersonalityAnalysis(
            character_id=character_id,
            dominant_traits=dominant_traits,
            behavioral_predictions=behavioral_predictions,
            interaction_style=interaction_style,
            conflict_triggers=conflict_triggers,
            motivation_drivers=motivation_drivers,
            relationship_patterns=relationship_patterns,
            growth_potential=growth_potential,
            consistency_score=profile.trait_consistency
        )
    
    def calculate_compatibility(self, 
                              character_a_id: str,
                              character_b_id: str,
                              db: Session) -> PersonalityCompatibility:
        """Calculate compatibility between two characters."""
        
        profile_a = db.query(PersonalityProfile).filter(
            PersonalityProfile.character_id == character_a_id
        ).first()
        
        profile_b = db.query(PersonalityProfile).filter(
            PersonalityProfile.character_id == character_b_id
        ).first()
        
        if not profile_a or not profile_b:
            raise ValueError("Personality profiles not found for one or both characters")
        
        # Calculate trait differences
        trait_diffs = {
            "extraversion": abs(profile_a.extraversion - profile_b.extraversion),
            "agreeableness": abs(profile_a.agreeableness - profile_b.agreeableness),
            "conscientiousness": abs(profile_a.conscientiousness - profile_b.conscientiousness),
            "neuroticism": abs(profile_a.neuroticism - profile_b.neuroticism),
            "openness": abs(profile_a.openness - profile_b.openness)
        }
        
        # Some differences are good (complementary), others bad (conflicting)
        compatibility_factors = {}
        
        # Complementary traits (moderate differences are good)
        complementary_score = 1.0 - abs(trait_diffs["extraversion"] - 0.3)  # Some difference in social style is good
        compatibility_factors["social_complement"] = max(0.0, complementary_score)
        
        # Similar values are good
        value_similarity = self._calculate_value_similarity(profile_a, profile_b)
        compatibility_factors["value_alignment"] = value_similarity
        
        # Similar conscientiousness is important for cooperation
        compatibility_factors["reliability_match"] = 1.0 - trait_diffs["conscientiousness"]
        
        # Low neuroticism in both is good for stability
        stability_score = (1.0 - profile_a.neuroticism) * (1.0 - profile_b.neuroticism)
        compatibility_factors["emotional_stability"] = stability_score
        
        # Calculate overall compatibility
        overall_score = np.mean(list(compatibility_factors.values()))
        
        # Identify potential conflicts
        potential_conflicts = self._identify_potential_conflicts(profile_a, profile_b)
        
        # Identify synergy opportunities
        synergy_opportunities = self._identify_synergy_opportunities(profile_a, profile_b)
        
        # Predict relationship types
        relationship_predictions = self._predict_relationship_types(profile_a, profile_b, overall_score)
        
        return PersonalityCompatibility(
            character_a_id=character_a_id,
            character_b_id=character_b_id,
            compatibility_score=overall_score,
            compatibility_factors=compatibility_factors,
            potential_conflicts=potential_conflicts,
            synergy_opportunities=synergy_opportunities,
            relationship_type_predictions=relationship_predictions
        )
    
    def update_personality_state(self, 
                               character_id: str,
                               state_data: PersonalityStateSchema,
                               db: Session) -> PersonalityState:
        """Update character's current personality state."""
        
        state = PersonalityState(
            id=str(uuid4()),
            character_id=character_id,
            stress_level=state_data.stress_level,
            fatigue_level=state_data.fatigue_level,
            confidence_level=state_data.confidence_level,
            current_context=state_data.current_context,
            recent_events=state_data.recent_events,
            social_pressure=state_data.social_pressure,
            trait_modifiers=state_data.trait_modifiers,
            behavior_overrides=state_data.behavior_overrides,
            expected_duration=state_data.expected_duration
        )
        
        db.add(state)
        db.commit()
        db.refresh(state)
        
        return state
    
    def get_personality_profile(self, character_id: str, db: Session) -> Optional[PersonalityProfile]:
        """Get personality profile for a character."""
        return db.query(PersonalityProfile).filter(
            PersonalityProfile.character_id == character_id
        ).first()
    
    # Helper methods
    def _categorize_trait_level(self, score: float) -> str:
        """Categorize trait score into descriptive level."""
        if score > 0.8:
            return "very_high"
        elif score > 0.6:
            return "high"
        elif score > 0.4:
            return "moderate"
        elif score > 0.2:
            return "low"
        else:
            return "very_low"
    
    def _generate_behavioral_predictions(self, profile: PersonalityProfile) -> List[str]:
        """Generate behavioral predictions based on personality."""
        predictions = []
        
        if profile.extraversion > 0.6:
            predictions.append("Likely to initiate social interactions")
        if profile.agreeableness > 0.6:
            predictions.append("Tends to avoid conflict and seek compromise")
        if profile.conscientiousness > 0.6:
            predictions.append("Reliable and follows through on commitments")
        if profile.neuroticism > 0.6:
            predictions.append("May react strongly to stress and unexpected events")
        if profile.openness > 0.6:
            predictions.append("Open to new experiences and creative solutions")
        
        return predictions
    
    def _analyze_interaction_style(self, profile: PersonalityProfile) -> Dict[str, str]:
        """Analyze how character typically interacts."""
        return {
            "communication": "direct" if profile.extraversion > 0.6 else "reserved",
            "conflict_resolution": "collaborative" if profile.agreeableness > 0.6 else "competitive",
            "decision_making": profile.decision_making_style,
            "social_approach": profile.social_style
        }
    
    def _identify_conflict_triggers(self, profile: PersonalityProfile) -> List[str]:
        """Identify what situations might trigger conflict for this character."""
        triggers = []
        
        if profile.neuroticism > 0.6:
            triggers.append("High-pressure situations")
        if profile.agreeableness < 0.4:
            triggers.append("Being asked to compromise their values")
        if profile.conscientiousness > 0.6:
            triggers.append("Dealing with unreliable people")
        if profile.openness < 0.4:
            triggers.append("Being forced to accept change")
        
        return triggers
    
    def _analyze_motivation_drivers(self, profile: PersonalityProfile) -> List[str]:
        """Analyze what motivates this character."""
        drivers = []
        
        if profile.core_values:
            for value in profile.core_values:
                drivers.append(f"Pursuing {value}")
        
        if profile.extraversion > 0.6:
            drivers.append("Social recognition and interaction")
        if profile.conscientiousness > 0.6:
            drivers.append("Achievement and accomplishment")
        if profile.openness > 0.6:
            drivers.append("Learning and new experiences")
        
        return drivers
    
    def _predict_relationship_patterns(self, profile: PersonalityProfile) -> Dict[str, str]:
        """Predict how character forms and maintains relationships."""
        patterns = {}
        
        if profile.extraversion > 0.6:
            patterns["formation"] = "quickly forms many connections"
        else:
            patterns["formation"] = "slowly builds deep connections"
        
        if profile.agreeableness > 0.6:
            patterns["maintenance"] = "nurturing and supportive"
        else:
            patterns["maintenance"] = "challenging and demanding"
        
        if profile.neuroticism > 0.6:
            patterns["conflict_style"] = "emotionally reactive"
        else:
            patterns["conflict_style"] = "calm and rational"
        
        return patterns
    
    def _assess_growth_potential(self, profile: PersonalityProfile) -> Dict[str, float]:
        """Assess potential for personality growth in different areas."""
        return {
            "emotional_stability": 1.0 - profile.neuroticism,
            "social_skills": profile.extraversion * profile.agreeableness,
            "adaptability": profile.openness * profile.personality_plasticity,
            "reliability": profile.conscientiousness,
            "overall_plasticity": profile.personality_plasticity
        }
    
    def _calculate_value_similarity(self, profile_a: PersonalityProfile, profile_b: PersonalityProfile) -> float:
        """Calculate similarity in core values between two profiles."""
        values_a = set(profile_a.core_values or [])
        values_b = set(profile_b.core_values or [])
        
        if not values_a and not values_b:
            return 1.0
        if not values_a or not values_b:
            return 0.0
        
        intersection = values_a.intersection(values_b)
        union = values_a.union(values_b)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _identify_potential_conflicts(self, profile_a: PersonalityProfile, profile_b: PersonalityProfile) -> List[str]:
        """Identify potential sources of conflict between two characters."""
        conflicts = []
        
        # High neuroticism differences can cause issues
        if abs(profile_a.neuroticism - profile_b.neuroticism) > 0.5:
            conflicts.append("Different stress responses and emotional stability")
        
        # Opposing moral alignments
        if profile_a.moral_alignment != profile_b.moral_alignment:
            if ("good" in profile_a.moral_alignment and "evil" in profile_b.moral_alignment) or \
               ("evil" in profile_a.moral_alignment and "good" in profile_b.moral_alignment):
                conflicts.append("Fundamentally opposed moral values")
        
        # Very different conscientiousness levels
        if abs(profile_a.conscientiousness - profile_b.conscientiousness) > 0.6:
            conflicts.append("Different standards for reliability and organization")
        
        return conflicts
    
    def _identify_synergy_opportunities(self, profile_a: PersonalityProfile, profile_b: PersonalityProfile) -> List[str]:
        """Identify potential synergies between two characters."""
        synergies = []
        
        # Complementary extraversion levels
        if 0.3 < abs(profile_a.extraversion - profile_b.extraversion) < 0.7:
            synergies.append("Balanced social dynamic - one can draw out the other")
        
        # Both high in conscientiousness
        if profile_a.conscientiousness > 0.6 and profile_b.conscientiousness > 0.6:
            synergies.append("Both are reliable and can count on each other")
        
        # High openness in both
        if profile_a.openness > 0.6 and profile_b.openness > 0.6:
            synergies.append("Both enjoy exploring new ideas and experiences together")
        
        # Shared core values
        shared_values = set(profile_a.core_values or []).intersection(set(profile_b.core_values or []))
        if shared_values:
            synergies.append(f"Share important values: {', '.join(shared_values)}")
        
        return synergies
    
    def _predict_relationship_types(self, profile_a: PersonalityProfile, profile_b: PersonalityProfile, compatibility: float) -> Dict[str, float]:
        """Predict likely relationship types between two characters."""
        predictions = {}
        
        # Base probabilities on compatibility
        if compatibility > 0.7:
            predictions["close_friend"] = 0.8
            predictions["romantic_interest"] = 0.6
            predictions["trusted_ally"] = 0.9
        elif compatibility > 0.5:
            predictions["friend"] = 0.7
            predictions["colleague"] = 0.8
            predictions["ally"] = 0.6
        else:
            predictions["acquaintance"] = 0.7
            predictions["rival"] = 0.4
            predictions["conflict"] = 0.3
        
        # Adjust based on specific traits
        if profile_a.agreeableness > 0.7 and profile_b.agreeableness > 0.7:
            predictions["mentor_student"] = 0.5
        
        if abs(profile_a.extraversion - profile_b.extraversion) > 0.5:
            predictions["complementary_pair"] = 0.6
        
        return predictions