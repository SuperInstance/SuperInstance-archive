"""
Mannerism and gesture description generation service.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
import logging

from ..models.mannerism import (
    MannerismCategory, GestureType, IntensityLevel, TriggerType,
    MannerismSchema, GestureSchema, MannerismGenerationRequest,
    MannerismGenerationResponse, GestureGenerationRequest, GestureGenerationResponse,
    MannerismAnalysis, MannerismCombination, ContextualMannerism,
    CharacterMannerism, GestureLibrary, MannerismTemplate
)
from ..models.base import EmotionType, CharacterType, CharacterRace
from ..models.personality import PersonalityProfileSchema, MoralAlignment
from ..config import Config

logger = logging.getLogger(__name__)

class MannerismService:
    def __init__(self):
        self.config = Config()
        self.mannerism_library = self._initialize_mannerism_library()
        self.gesture_library = self._initialize_gesture_library()
        self.cultural_mannerisms = self._initialize_cultural_mannerisms()
        self.personality_correlations = self._initialize_personality_correlations()
        
    def _initialize_mannerism_library(self) -> Dict[str, Dict[str, Any]]:
        """Initialize library of common mannerisms."""
        return {
            # Physical mannerisms
            "fidgets_with_jewelry": {
                "category": MannerismCategory.PHYSICAL,
                "description": "Habitually touches, twists, or adjusts jewelry when nervous or thinking",
                "trigger_type": TriggerType.STRESS,
                "intensity": IntensityLevel.MILD,
                "frequency": 0.6,
                "personality_correlation": {"neuroticism": 0.7, "conscientiousness": -0.3}
            },
            
            "drums_fingers": {
                "category": MannerismCategory.PHYSICAL,
                "description": "Drums fingers on surfaces when impatient or thinking",
                "trigger_type": TriggerType.SITUATIONAL,
                "intensity": IntensityLevel.MODERATE,
                "frequency": 0.5,
                "personality_correlation": {"extraversion": 0.6, "neuroticism": 0.4}
            },
            
            "adjusts_clothing": {
                "category": MannerismCategory.PHYSICAL,
                "description": "Frequently straightens or adjusts clothing and appearance",
                "trigger_type": TriggerType.SOCIAL,
                "intensity": IntensityLevel.MILD,
                "frequency": 0.4,
                "personality_correlation": {"conscientiousness": 0.8, "neuroticism": 0.3}
            },
            
            # Facial mannerisms
            "raises_eyebrow": {
                "category": MannerismCategory.FACIAL,
                "description": "Raises one eyebrow when skeptical or amused",
                "trigger_type": TriggerType.EMOTIONAL,
                "intensity": IntensityLevel.SUBTLE,
                "frequency": 0.7,
                "personality_correlation": {"openness": 0.5, "agreeableness": -0.2}
            },
            
            "bites_lower_lip": {
                "category": MannerismCategory.FACIAL,
                "description": "Bites or chews lower lip when concentrating or worried",
                "trigger_type": TriggerType.STRESS,
                "intensity": IntensityLevel.MILD,
                "frequency": 0.5,
                "personality_correlation": {"neuroticism": 0.8, "conscientiousness": 0.4}
            },
            
            "squints_when_thinking": {
                "category": MannerismCategory.FACIAL,
                "description": "Squints eyes slightly when deep in thought",
                "trigger_type": TriggerType.SITUATIONAL,
                "intensity": IntensityLevel.SUBTLE,
                "frequency": 0.6,
                "personality_correlation": {"openness": 0.6, "conscientiousness": 0.5}
            },
            
            # Verbal mannerisms
            "uses_filler_words": {
                "category": MannerismCategory.VERBAL,
                "description": "Uses specific filler words like 'you know', 'um', or 'like'",
                "trigger_type": TriggerType.SOCIAL,
                "intensity": IntensityLevel.MODERATE,
                "frequency": 0.8,
                "personality_correlation": {"extraversion": -0.3, "neuroticism": 0.5}
            },
            
            "repeats_key_phrases": {
                "category": MannerismCategory.VERBAL,
                "description": "Tends to repeat important phrases for emphasis",
                "trigger_type": TriggerType.EMOTIONAL,
                "intensity": IntensityLevel.MODERATE,
                "frequency": 0.4,
                "personality_correlation": {"conscientiousness": 0.6, "extraversion": 0.4}
            },
            
            "clears_throat": {
                "category": MannerismCategory.VERBAL,
                "description": "Clears throat before speaking, especially in formal situations",
                "trigger_type": TriggerType.SOCIAL,
                "intensity": IntensityLevel.MILD,
                "frequency": 0.3,
                "personality_correlation": {"neuroticism": 0.4, "conscientiousness": 0.3}
            },
            
            # Postural mannerisms
            "crosses_arms": {
                "category": MannerismCategory.POSTURAL,
                "description": "Frequently crosses arms when defensive or uncomfortable",
                "trigger_type": TriggerType.SOCIAL,
                "intensity": IntensityLevel.MODERATE,
                "frequency": 0.5,
                "personality_correlation": {"agreeableness": -0.4, "neuroticism": 0.3}
            },
            
            "leans_forward": {
                "category": MannerismCategory.POSTURAL,
                "description": "Leans forward when interested or engaged in conversation",
                "trigger_type": TriggerType.SOCIAL,
                "intensity": IntensityLevel.MODERATE,
                "frequency": 0.6,
                "personality_correlation": {"extraversion": 0.7, "openness": 0.5}
            },
            
            "shifts_weight": {
                "category": MannerismCategory.POSTURAL,
                "description": "Shifts weight from foot to foot when standing",
                "trigger_type": TriggerType.SITUATIONAL,
                "intensity": IntensityLevel.MILD,
                "frequency": 0.4,
                "personality_correlation": {"neuroticism": 0.5, "extraversion": -0.2}
            },
            
            # Interactive mannerisms
            "organizes_objects": {
                "category": MannerismCategory.INTERACTIVE,
                "description": "Habitually straightens or organizes nearby objects",
                "trigger_type": TriggerType.HABITUAL,
                "intensity": IntensityLevel.MILD,
                "frequency": 0.5,
                "personality_correlation": {"conscientiousness": 0.9, "neuroticism": 0.3}
            },
            
            "fiddles_with_tools": {
                "category": MannerismCategory.INTERACTIVE,
                "description": "Plays with tools, pens, or small objects while talking",
                "trigger_type": TriggerType.SOCIAL,
                "intensity": IntensityLevel.MODERATE,
                "frequency": 0.4,
                "personality_correlation": {"openness": 0.6, "neuroticism": 0.4}
            }
        }
    
    def _initialize_gesture_library(self) -> Dict[str, Dict[str, Any]]:
        """Initialize library of gestures and their descriptions."""
        return {
            # Greeting gestures
            "firm_handshake": {
                "type": GestureType.GREETING,
                "description": "Extends hand with firm, confident grip and direct eye contact",
                "body_parts": ["hand", "arm", "eyes"],
                "formality": "formal",
                "intensity": IntensityLevel.MODERATE,
                "cultural_origins": ["western", "business"]
            },
            
            "casual_wave": {
                "type": GestureType.GREETING,
                "description": "Raises hand and waves with a friendly, relaxed motion",
                "body_parts": ["hand", "arm"],
                "formality": "casual",
                "intensity": IntensityLevel.MILD,
                "cultural_origins": ["universal", "informal"]
            },
            
            "respectful_bow": {
                "type": GestureType.GREETING,
                "description": "Bends at waist in respectful acknowledgment",
                "body_parts": ["torso", "head", "arms"],
                "formality": "formal",
                "intensity": IntensityLevel.PRONOUNCED,
                "cultural_origins": ["eastern", "formal"]
            },
            
            # Agreement gestures
            "enthusiastic_nod": {
                "type": GestureType.AGREEMENT,
                "description": "Nods head vigorously with bright expression",
                "body_parts": ["head", "face"],
                "formality": "casual",
                "intensity": IntensityLevel.PRONOUNCED,
                "personality_correlation": {"extraversion": 0.7, "agreeableness": 0.6}
            },
            
            "thoughtful_nod": {
                "type": GestureType.AGREEMENT,
                "description": "Slow, deliberate nod while considering the point",
                "body_parts": ["head"],
                "formality": "neutral",
                "intensity": IntensityLevel.SUBTLE,
                "personality_correlation": {"conscientiousness": 0.7, "openness": 0.5}
            },
            
            # Thinking gestures
            "strokes_chin": {
                "type": GestureType.THINKING,
                "description": "Runs fingers along chin or beard while contemplating",
                "body_parts": ["hand", "chin"],
                "formality": "neutral",
                "intensity": IntensityLevel.MILD,
                "personality_correlation": {"openness": 0.6, "conscientiousness": 0.4}
            },
            
            "steeples_fingers": {
                "type": GestureType.THINKING,
                "description": "Presses fingertips together in a steeple formation",
                "body_parts": ["hands", "fingers"],
                "formality": "formal",
                "intensity": IntensityLevel.MODERATE,
                "personality_correlation": {"conscientiousness": 0.8, "openness": 0.7}
            },
            
            # Emotional gestures
            "throws_hands_up": {
                "type": GestureType.SURPRISE,
                "description": "Throws both hands up in surprise or exasperation",
                "body_parts": ["hands", "arms"],
                "formality": "casual",
                "intensity": IntensityLevel.EXTREME,
                "personality_correlation": {"extraversion": 0.7, "neuroticism": 0.5}
            },
            
            "clenches_fists": {
                "type": GestureType.ANGER,
                "description": "Slowly clenches hands into tight fists",
                "body_parts": ["hands", "arms"],
                "formality": "universal",
                "intensity": IntensityLevel.PRONOUNCED,
                "personality_correlation": {"agreeableness": -0.6, "neuroticism": 0.4}
            },
            
            "covers_mouth": {
                "type": GestureType.SURPRISE,
                "description": "Quickly covers mouth with hand in shock",
                "body_parts": ["hand", "mouth"],
                "formality": "universal",
                "intensity": IntensityLevel.MODERATE,
                "personality_correlation": {"neuroticism": 0.4, "agreeableness": 0.3}
            }
        }
    
    def _initialize_cultural_mannerisms(self) -> Dict[str, List[str]]:
        """Initialize culture-specific mannerism sets."""
        return {
            "noble": [
                "maintains perfect posture",
                "speaks in measured tones",
                "gestures with practiced elegance",
                "never touches face in public",
                "adjusts cufflinks when thinking"
            ],
            "common_folk": [
                "scratches head when confused",
                "spits when angry",
                "wipes hands on clothing",
                "slouches when relaxed",
                "talks with hands"
            ],
            "military": [
                "stands at attention when addressed",
                "salutes automatically",
                "keeps hands behind back",
                "scans surroundings regularly",
                "speaks in clipped sentences"
            ],
            "scholarly": [
                "adjusts spectacles frequently",
                "quotes ancient texts",
                "stacks books compulsively",
                "traces words while reading",
                "mutters calculations"
            ],
            "criminal": [
                "checks exits constantly",
                "speaks in code",
                "avoids direct eye contact",
                "fidgets with concealed weapons",
                "whispers important information"
            ]
        }
    
    def _initialize_personality_correlations(self) -> Dict[str, Dict[str, float]]:
        """Initialize personality trait correlations with mannerism types."""
        return {
            "high_extraversion": {
                "talks_with_hands": 0.8,
                "maintains_eye_contact": 0.7,
                "gestures_broadly": 0.8,
                "speaks_loudly": 0.6,
                "interrupts_others": 0.4
            },
            "low_extraversion": {
                "avoids_eye_contact": 0.6,
                "speaks_softly": 0.7,
                "minimal_gestures": 0.8,
                "fidgets_quietly": 0.5,
                "pauses_before_speaking": 0.6
            },
            "high_conscientiousness": {
                "maintains_posture": 0.9,
                "organizes_space": 0.8,
                "checks_appearance": 0.7,
                "follows_routines": 0.9,
                "punctual_gestures": 0.6
            },
            "high_neuroticism": {
                "nervous_laughter": 0.7,
                "fidgets_excessively": 0.8,
                "bites_nails": 0.6,
                "stammers_under_pressure": 0.5,
                "wrings_hands": 0.7
            },
            "high_openness": {
                "expressive_gestures": 0.7,
                "dramatic_movements": 0.6,
                "uses_metaphors": 0.8,
                "creative_poses": 0.7,
                "unconventional_habits": 0.8
            },
            "high_agreeableness": {
                "nods_frequently": 0.7,
                "smiles_often": 0.8,
                "mirroring_behavior": 0.6,
                "gentle_touches": 0.5,
                "apologetic_gestures": 0.6
            }
        }

    async def generate_character_mannerisms(
        self,
        request: MannerismGenerationRequest,
        db_session: Optional[Session] = None
    ) -> MannerismGenerationResponse:
        """Generate a set of mannerisms for a character."""
        
        generated_mannerisms = []
        generation_reasoning = {}
        personality_connections = {}
        
        # Determine mannerism categories based on personality
        category_preferences = await self._determine_category_preferences(request)
        
        # Generate core mannerisms
        core_count = min(3, request.desired_count)
        core_mannerisms = await self._generate_core_mannerisms(
            request, category_preferences, core_count
        )
        generated_mannerisms.extend(core_mannerisms)
        
        # Generate supplementary mannerisms
        remaining_count = request.desired_count - len(core_mannerisms)
        if remaining_count > 0:
            supplementary_mannerisms = await self._generate_supplementary_mannerisms(
                request, category_preferences, remaining_count, core_mannerisms
            )
            generated_mannerisms.extend(supplementary_mannerisms)
        
        # Analyze personality connections
        for mannerism in generated_mannerisms:
            if mannerism.personality_correlation:
                for trait, correlation in mannerism.personality_correlation.items():
                    if trait not in personality_connections:
                        personality_connections[trait] = []
                    personality_connections[trait].append(mannerism.name)
        
        # Generate reasoning
        generation_reasoning = await self._generate_reasoning(
            request, generated_mannerisms, category_preferences
        )
        
        # Suggest combinations
        suggested_combinations = await self._suggest_mannerism_combinations(
            generated_mannerisms
        )
        
        return MannerismGenerationResponse(
            character_id=request.character_id,
            generated_mannerisms=generated_mannerisms,
            total_generated=len(generated_mannerisms),
            generation_reasoning=generation_reasoning,
            personality_connections=personality_connections,
            suggested_combinations=suggested_combinations
        )

    async def generate_contextual_gesture(
        self,
        request: GestureGenerationRequest,
        personality: Optional[PersonalityProfileSchema] = None,
        db_session: Optional[Session] = None
    ) -> GestureGenerationResponse:
        """Generate an appropriate gesture for a specific context."""
        
        # Find gestures matching the type
        matching_gestures = []
        for gesture_id, gesture_data in self.gesture_library.items():
            if gesture_data["type"] == request.gesture_type:
                # Check formality level
                if gesture_data.get("formality") == request.formality_level:
                    matching_gestures.append((gesture_id, gesture_data))
        
        if not matching_gestures:
            # Fallback to any gesture of the right type
            matching_gestures = [
                (gid, gdata) for gid, gdata in self.gesture_library.items()
                if gdata["type"] == request.gesture_type
            ]
        
        if not matching_gestures:
            raise ValueError(f"No gestures found for type {request.gesture_type}")
        
        # Select best gesture based on personality and context
        selected_gesture_data = await self._select_best_gesture(
            matching_gestures, personality, request
        )
        
        gesture_id, gesture_info = selected_gesture_data
        
        # Create gesture schema
        selected_gesture = GestureSchema(
            id=gesture_id,
            gesture_name=gesture_id.replace("_", " ").title(),
            gesture_type=request.gesture_type,
            category=MannerismCategory.PHYSICAL,  # Default category
            description=gesture_info["description"],
            body_parts_involved=gesture_info["body_parts"],
            formality_level=gesture_info.get("formality", "neutral"),
            cultural_origins=gesture_info.get("cultural_origins", [])
        )
        
        # Generate execution description
        execution_description = await self._generate_execution_description(
            selected_gesture, request, personality
        )
        
        # Find alternative gestures
        alternative_gestures = await self._find_alternative_gestures(
            request.gesture_type, selected_gesture, personality
        )
        
        # Generate contextual notes
        contextual_notes = await self._generate_contextual_notes(
            selected_gesture, request
        )
        
        return GestureGenerationResponse(
            character_id=request.character_id,
            selected_gesture=selected_gesture,
            alternative_gestures=alternative_gestures,
            execution_description=execution_description,
            contextual_notes=contextual_notes,
            cultural_considerations=self._get_cultural_considerations(selected_gesture)
        )

    async def analyze_character_mannerisms(
        self,
        character_id: str,
        db_session: Optional[Session] = None
    ) -> MannerismAnalysis:
        """Analyze a character's existing mannerisms."""
        
        # In a real implementation, this would query the database
        # For now, return mock analysis
        return MannerismAnalysis(
            character_id=character_id,
            total_mannerisms=8,
            category_distribution={
                MannerismCategory.PHYSICAL: 3,
                MannerismCategory.FACIAL: 2,
                MannerismCategory.VERBAL: 2,
                MannerismCategory.POSTURAL: 1
            },
            intensity_profile={
                IntensityLevel.SUBTLE: 2,
                IntensityLevel.MILD: 3,
                IntensityLevel.MODERATE: 2,
                IntensityLevel.PRONOUNCED: 1
            },
            trigger_analysis={
                TriggerType.SOCIAL: 4,
                TriggerType.STRESS: 2,
                TriggerType.EMOTIONAL: 1,
                TriggerType.HABITUAL: 1
            },
            frequency_patterns={
                "average_frequency": 0.52,
                "highest_frequency": 0.8,
                "lowest_frequency": 0.2
            },
            personality_alignment=0.78,
            uniqueness_score=0.65,
            social_impact_assessment={
                "positive": 3,
                "neutral": 4,
                "negative": 1
            },
            improvement_suggestions=[
                "Consider adding a signature physical gesture",
                "Balance nervous habits with confident mannerisms",
                "Develop context-specific variations"
            ]
        )

    async def _determine_category_preferences(
        self,
        request: MannerismGenerationRequest
    ) -> Dict[MannerismCategory, float]:
        """Determine preference weights for different mannerism categories."""
        
        preferences = {}
        
        # Base preferences
        for category in MannerismCategory:
            preferences[category] = 0.5  # Neutral base
        
        # Personality influences
        traits = request.personality_traits
        
        # High extraversion favors verbal and interactive mannerisms
        if traits.get("extraversion", 0.5) > 0.6:
            preferences[MannerismCategory.VERBAL] += 0.3
            preferences[MannerismCategory.INTERACTIVE] += 0.2
            preferences[MannerismCategory.PHYSICAL] += 0.2
        
        # High conscientiousness favors postural and organized behaviors
        if traits.get("conscientiousness", 0.5) > 0.6:
            preferences[MannerismCategory.POSTURAL] += 0.3
            preferences[MannerismCategory.INTERACTIVE] += 0.2
        
        # High neuroticism favors nervous habits
        if traits.get("neuroticism", 0.5) > 0.6:
            preferences[MannerismCategory.NERVOUS] += 0.4
            preferences[MannerismCategory.PHYSICAL] += 0.2
        
        # Apply focus/avoid categories
        if request.focus_categories:
            for category in request.focus_categories:
                preferences[category] += 0.4
        
        if request.avoid_categories:
            for category in request.avoid_categories:
                preferences[category] = max(0.1, preferences[category] - 0.5)
        
        # Normalize preferences
        total = sum(preferences.values())
        if total > 0:
            for category in preferences:
                preferences[category] /= total
        
        return preferences

    async def _generate_core_mannerisms(
        self,
        request: MannerismGenerationRequest,
        category_preferences: Dict[MannerismCategory, float],
        count: int
    ) -> List[MannerismSchema]:
        """Generate core mannerisms based on personality."""
        
        core_mannerisms = []
        used_mannerisms = set()
        
        # Sort categories by preference
        sorted_categories = sorted(
            category_preferences.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for category, preference in sorted_categories[:count]:
            # Find suitable mannerisms for this category
            suitable_mannerisms = [
                (mid, mdata) for mid, mdata in self.mannerism_library.items()
                if mdata["category"] == category and mid not in used_mannerisms
            ]
            
            if suitable_mannerisms:
                # Select best match based on personality
                selected_id, selected_data = await self._select_best_mannerism(
                    suitable_mannerisms, request.personality_traits
                )
                
                mannerism = await self._create_mannerism_schema(
                    request.character_id, selected_id, selected_data
                )
                
                core_mannerisms.append(mannerism)
                used_mannerisms.add(selected_id)
        
        return core_mannerisms

    async def _generate_supplementary_mannerisms(
        self,
        request: MannerismGenerationRequest,
        category_preferences: Dict[MannerismCategory, float],
        count: int,
        existing_mannerisms: List[MannerismSchema]
    ) -> List[MannerismSchema]:
        """Generate additional mannerisms to complement core ones."""
        
        supplementary_mannerisms = []
        used_mannerisms = {m.name for m in existing_mannerisms}
        
        # Get available mannerisms
        available_mannerisms = [
            (mid, mdata) for mid, mdata in self.mannerism_library.items()
            if mid not in used_mannerisms
        ]
        
        # Sort by personality compatibility
        scored_mannerisms = []
        for mid, mdata in available_mannerisms:
            score = await self._calculate_personality_compatibility(
                mdata, request.personality_traits
            )
            scored_mannerisms.append((score, mid, mdata))
        
        scored_mannerisms.sort(reverse=True)
        
        # Select top scoring mannerisms
        for score, mid, mdata in scored_mannerisms[:count]:
            mannerism = await self._create_mannerism_schema(
                request.character_id, mid, mdata
            )
            supplementary_mannerisms.append(mannerism)
        
        return supplementary_mannerisms

    async def _select_best_mannerism(
        self,
        candidate_mannerisms: List[Tuple[str, Dict[str, Any]]],
        personality_traits: Dict[str, float]
    ) -> Tuple[str, Dict[str, Any]]:
        """Select the best mannerism from candidates based on personality."""
        
        best_score = -1
        best_mannerism = candidate_mannerisms[0]
        
        for mid, mdata in candidate_mannerisms:
            score = await self._calculate_personality_compatibility(
                mdata, personality_traits
            )
            
            if score > best_score:
                best_score = score
                best_mannerism = (mid, mdata)
        
        return best_mannerism

    async def _calculate_personality_compatibility(
        self,
        mannerism_data: Dict[str, Any],
        personality_traits: Dict[str, float]
    ) -> float:
        """Calculate how well a mannerism matches personality traits."""
        
        correlation = mannerism_data.get("personality_correlation", {})
        if not correlation:
            return 0.5  # Neutral compatibility
        
        compatibility_score = 0.0
        total_weight = 0.0
        
        for trait, expected_correlation in correlation.items():
            if trait in personality_traits:
                actual_trait_value = personality_traits[trait]
                
                # Positive correlation: high trait value should match high correlation
                # Negative correlation: high trait value should match low correlation
                if expected_correlation > 0:
                    compatibility = actual_trait_value * expected_correlation
                else:
                    compatibility = (1.0 - actual_trait_value) * abs(expected_correlation)
                
                compatibility_score += compatibility
                total_weight += abs(expected_correlation)
        
        if total_weight > 0:
            return compatibility_score / total_weight
        
        return 0.5

    async def _create_mannerism_schema(
        self,
        character_id: str,
        mannerism_id: str,
        mannerism_data: Dict[str, Any]
    ) -> MannerismSchema:
        """Create a MannerismSchema from library data."""
        
        return MannerismSchema(
            character_id=character_id,
            name=mannerism_id.replace("_", " ").title(),
            category=mannerism_data["category"],
            description=mannerism_data["description"],
            frequency=mannerism_data.get("frequency", 0.5),
            intensity=mannerism_data.get("intensity", IntensityLevel.MODERATE),
            trigger_type=mannerism_data["trigger_type"],
            personality_correlation=mannerism_data.get("personality_correlation", {}),
            social_impact=mannerism_data.get("social_impact", "neutral")
        )

    async def _select_best_gesture(
        self,
        candidate_gestures: List[Tuple[str, Dict[str, Any]]],
        personality: Optional[PersonalityProfileSchema],
        request: GestureGenerationRequest
    ) -> Tuple[str, Dict[str, Any]]:
        """Select the best gesture from candidates."""
        
        if not personality:
            return random.choice(candidate_gestures)
        
        best_score = -1
        best_gesture = candidate_gestures[0]
        
        for gesture_id, gesture_data in candidate_gestures:
            score = 0.0
            
            # Intensity matching
            gesture_intensity = gesture_data.get("intensity", IntensityLevel.MODERATE)
            if gesture_intensity == request.intensity_required:
                score += 0.3
            
            # Personality correlation
            if "personality_correlation" in gesture_data:
                correlation = gesture_data["personality_correlation"]
                for trait, correlation_value in correlation.items():
                    trait_value = getattr(personality, trait, 0.5)
                    if correlation_value > 0:
                        score += trait_value * correlation_value * 0.2
                    else:
                        score += (1.0 - trait_value) * abs(correlation_value) * 0.2
            
            # Formality matching
            if gesture_data.get("formality") == request.formality_level:
                score += 0.2
            
            # Cultural filter
            if request.cultural_filter:
                cultural_origins = gesture_data.get("cultural_origins", [])
                if any(culture in cultural_origins for culture in request.cultural_filter):
                    score += 0.3
            
            if score > best_score:
                best_score = score
                best_gesture = (gesture_id, gesture_data)
        
        return best_gesture

    async def _generate_execution_description(
        self,
        gesture: GestureSchema,
        request: GestureGenerationRequest,
        personality: Optional[PersonalityProfileSchema]
    ) -> str:
        """Generate detailed execution description for the gesture."""
        
        base_description = gesture.description
        
        # Add intensity modifiers
        intensity_modifiers = {
            IntensityLevel.SUBTLE: "with barely perceptible movement",
            IntensityLevel.MILD: "with gentle, controlled motion",
            IntensityLevel.MODERATE: "with clear, deliberate movement",
            IntensityLevel.PRONOUNCED: "with emphatic, noticeable action",
            IntensityLevel.EXTREME: "with dramatic, unmistakable intensity"
        }
        
        intensity_modifier = intensity_modifiers.get(
            request.intensity_required, "with natural movement"
        )
        
        # Add personality influences
        personality_additions = []
        if personality:
            if personality.extraversion > 0.7:
                personality_additions.append("with confident energy")
            elif personality.extraversion < 0.3:
                personality_additions.append("with reserved hesitation")
            
            if personality.neuroticism > 0.7:
                personality_additions.append("with slight nervousness")
            
            if personality.conscientiousness > 0.7:
                personality_additions.append("with precise control")
        
        # Combine descriptions
        full_description = base_description
        if intensity_modifier:
            full_description += f", {intensity_modifier}"
        if personality_additions:
            full_description += f", {', '.join(personality_additions)}"
        
        return full_description

    async def _find_alternative_gestures(
        self,
        gesture_type: GestureType,
        selected_gesture: GestureSchema,
        personality: Optional[PersonalityProfileSchema]
    ) -> List[GestureSchema]:
        """Find alternative gestures of the same type."""
        
        alternatives = []
        
        for gesture_id, gesture_data in self.gesture_library.items():
            if (gesture_data["type"] == gesture_type and 
                gesture_id != selected_gesture.id):
                
                alternative = GestureSchema(
                    id=gesture_id,
                    gesture_name=gesture_id.replace("_", " ").title(),
                    gesture_type=gesture_type,
                    category=MannerismCategory.PHYSICAL,
                    description=gesture_data["description"],
                    body_parts_involved=gesture_data["body_parts"],
                    formality_level=gesture_data.get("formality", "neutral")
                )
                
                alternatives.append(alternative)
        
        # Limit to top 3 alternatives
        return alternatives[:3]

    async def _generate_contextual_notes(
        self,
        gesture: GestureSchema,
        request: GestureGenerationRequest
    ) -> Optional[str]:
        """Generate contextual notes about when/how to use the gesture."""
        
        notes = []
        
        # Emotional context notes
        if request.emotional_context:
            notes.append(f"Best used when feeling {request.emotional_context.value}")
        
        # Social context notes
        if request.social_context:
            if request.social_context.get("audience_size"):
                size = request.social_context["audience_size"]
                if size == "large":
                    notes.append("Effective for large audiences")
                elif size == "small":
                    notes.append("Suitable for intimate conversations")
        
        # Formality notes
        if gesture.formality_level == "formal":
            notes.append("Appropriate for formal occasions")
        elif gesture.formality_level == "casual":
            notes.append("Best used in casual settings")
        
        return "; ".join(notes) if notes else None

    def _get_cultural_considerations(
        self,
        gesture: GestureSchema
    ) -> Optional[str]:
        """Get cultural considerations for the gesture."""
        
        if gesture.cultural_origins:
            origins = ", ".join(gesture.cultural_origins)
            return f"Originated from {origins} cultural contexts"
        
        return None

    async def _generate_reasoning(
        self,
        request: MannerismGenerationRequest,
        mannerisms: List[MannerismSchema],
        preferences: Dict[MannerismCategory, float]
    ) -> Dict[str, str]:
        """Generate reasoning for why specific mannerisms were chosen."""
        
        reasoning = {}
        
        # Overall strategy
        reasoning["strategy"] = "Selected mannerisms based on personality trait analysis and cultural context"
        
        # Category distribution
        category_counts = {}
        for mannerism in mannerisms:
            category_counts[mannerism.category] = category_counts.get(mannerism.category, 0) + 1
        
        reasoning["distribution"] = f"Emphasized {max(category_counts.items(), key=lambda x: x[1])[0].value} mannerisms due to personality profile"
        
        # Personality alignment
        high_traits = [trait for trait, value in request.personality_traits.items() if value > 0.7]
        if high_traits:
            reasoning["personality_focus"] = f"Focused on mannerisms matching high {', '.join(high_traits)} traits"
        
        return reasoning

    async def _suggest_mannerism_combinations(
        self,
        mannerisms: List[MannerismSchema]
    ) -> List[List[str]]:
        """Suggest combinations of mannerisms that work well together."""
        
        combinations = []
        
        # Find mannerisms that could work together
        physical_mannerisms = [m.name for m in mannerisms if m.category == MannerismCategory.PHYSICAL]
        facial_mannerisms = [m.name for m in mannerisms if m.category == MannerismCategory.FACIAL]
        verbal_mannerisms = [m.name for m in mannerisms if m.category == MannerismCategory.VERBAL]
        
        # Suggest stress response combinations
        stress_mannerisms = [m.name for m in mannerisms if m.trigger_type == TriggerType.STRESS]
        if len(stress_mannerisms) >= 2:
            combinations.append(stress_mannerisms[:2])
        
        # Suggest social interaction combinations
        social_mannerisms = [m.name for m in mannerisms if m.trigger_type == TriggerType.SOCIAL]
        if len(social_mannerisms) >= 2:
            combinations.append(social_mannerisms[:2])
        
        # Suggest complementary combinations
        if physical_mannerisms and facial_mannerisms:
            combinations.append([physical_mannerisms[0], facial_mannerisms[0]])
        
        return combinations[:3]  # Limit to 3 suggestions