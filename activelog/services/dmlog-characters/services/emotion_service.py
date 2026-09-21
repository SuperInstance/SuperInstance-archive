"""
Emotion engine service for dynamic character emotional states.
"""

import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
import logging

from ..models.emotion import (
    EmotionIntensity, EmotionTrigger, EmotionDecayType,
    EmotionalStateSchema, EmotionalTriggerEvent, EmotionalResponse,
    EmotionAnalysis, MoodState, EmotionalContagion, StressResponse,
    EmotionalExpression, EmotionalPrediction, EmotionalGrowth,
    EmotionalState, EmotionalModifier, EmotionalEvent, EmotionalProfile
)
from ..models.base import EmotionType
from ..models.personality import PersonalityProfileSchema
from ..models.memory import MemorySchema
from ..config import Config

logger = logging.getLogger(__name__)

class EmotionService:
    def __init__(self):
        self.config = Config()
        self.emotion_relationships = self._initialize_emotion_relationships()
        self.trigger_mappings = self._initialize_trigger_mappings()
        self.decay_functions = self._initialize_decay_functions()
        
    def _initialize_emotion_relationships(self) -> Dict[EmotionType, Dict[str, List[EmotionType]]]:
        """Initialize relationships between emotions (reinforcing, opposing, etc.)."""
        return {
            EmotionType.JOY: {
                "reinforces": [EmotionType.TRUST, EmotionType.ANTICIPATION],
                "opposes": [EmotionType.SADNESS, EmotionType.FEAR, EmotionType.ANGER],
                "triggers": [EmotionType.SURPRISE]
            },
            EmotionType.SADNESS: {
                "reinforces": [EmotionType.FEAR],
                "opposes": [EmotionType.JOY, EmotionType.ANTICIPATION],
                "triggers": [EmotionType.ANGER, EmotionType.DISGUST]
            },
            EmotionType.ANGER: {
                "reinforces": [EmotionType.DISGUST],
                "opposes": [EmotionType.JOY, EmotionType.TRUST, EmotionType.FEAR],
                "triggers": [EmotionType.ANTICIPATION]
            },
            EmotionType.FEAR: {
                "reinforces": [EmotionType.SADNESS],
                "opposes": [EmotionType.JOY, EmotionType.TRUST, EmotionType.ANGER],
                "triggers": [EmotionType.SURPRISE, EmotionType.ANTICIPATION]
            },
            EmotionType.TRUST: {
                "reinforces": [EmotionType.JOY, EmotionType.ANTICIPATION],
                "opposes": [EmotionType.FEAR, EmotionType.DISGUST, EmotionType.ANGER],
                "triggers": []
            },
            EmotionType.DISGUST: {
                "reinforces": [EmotionType.ANGER],
                "opposes": [EmotionType.JOY, EmotionType.TRUST],
                "triggers": [EmotionType.SADNESS]
            },
            EmotionType.SURPRISE: {
                "reinforces": [],
                "opposes": [],
                "triggers": [EmotionType.JOY, EmotionType.FEAR, EmotionType.ANGER]
            },
            EmotionType.ANTICIPATION: {
                "reinforces": [EmotionType.JOY, EmotionType.TRUST],
                "opposes": [EmotionType.SADNESS],
                "triggers": [EmotionType.SURPRISE]
            }
        }
    
    def _initialize_trigger_mappings(self) -> Dict[EmotionTrigger, Dict[EmotionType, float]]:
        """Initialize how different triggers affect emotions."""
        return {
            EmotionTrigger.DIALOGUE: {
                EmotionType.JOY: 0.1,
                EmotionType.TRUST: 0.2,
                EmotionType.SURPRISE: 0.3
            },
            EmotionTrigger.COMBAT: {
                EmotionType.ANGER: 0.4,
                EmotionType.FEAR: 0.3,
                EmotionType.ANTICIPATION: 0.2
            },
            EmotionTrigger.QUEST_COMPLETION: {
                EmotionType.JOY: 0.6,
                EmotionType.TRUST: 0.2,
                EmotionType.ANTICIPATION: -0.3
            },
            EmotionTrigger.RELATIONSHIP_CHANGE: {
                EmotionType.JOY: 0.3,
                EmotionType.SADNESS: 0.2,
                EmotionType.TRUST: 0.4,
                EmotionType.FEAR: 0.1
            },
            EmotionTrigger.ITEM_LOSS: {
                EmotionType.SADNESS: 0.4,
                EmotionType.ANGER: 0.3,
                EmotionType.SURPRISE: 0.2
            },
            EmotionTrigger.ITEM_GAIN: {
                EmotionType.JOY: 0.4,
                EmotionType.SURPRISE: 0.3,
                EmotionType.ANTICIPATION: 0.2
            }
        }
    
    def _initialize_decay_functions(self) -> Dict[EmotionDecayType, callable]:
        """Initialize emotion decay function calculations."""
        return {
            EmotionDecayType.LINEAR: lambda intensity, time, rate: max(0, intensity - (rate * time)),
            EmotionDecayType.EXPONENTIAL: lambda intensity, time, rate: intensity * math.exp(-rate * time),
            EmotionDecayType.LOGARITHMIC: lambda intensity, time, rate: intensity * (1 - (rate * math.log(time + 1))),
            EmotionDecayType.STEP: lambda intensity, time, rate: intensity * (0.9 ** int(time * rate)),
            EmotionDecayType.PLATEAU: lambda intensity, time, rate: max(intensity * 0.3, intensity - (rate * time))
        }

    async def get_emotional_state(
        self,
        character_id: str,
        db_session: Optional[Session] = None
    ) -> EmotionalStateSchema:
        """Get current emotional state of a character."""
        
        # In a real implementation, this would query the database
        # For now, return a default emotional state
        return EmotionalStateSchema(
            character_id=character_id,
            joy=0.6,
            trust=0.7,
            sadness=0.1,
            anger=0.0,
            fear=0.1,
            surprise=0.0,
            disgust=0.0,
            anticipation=0.3,
            emotional_stability=0.7,
            baseline_mood=0.6,
            dominant_emotion=EmotionType.JOY,
            dominant_intensity=0.6
        )

    async def trigger_emotional_event(
        self,
        event: EmotionalTriggerEvent,
        personality: PersonalityProfileSchema,
        current_state: Optional[EmotionalStateSchema] = None,
        db_session: Optional[Session] = None
    ) -> EmotionalResponse:
        """Process an emotional trigger and update character's emotional state."""
        
        if current_state is None:
            current_state = await self.get_emotional_state(event.character_id, db_session)
        
        # Calculate base emotional changes from trigger
        base_changes = self._calculate_base_emotional_changes(event, current_state)
        
        # Apply personality modifiers
        personality_changes = await self._apply_personality_modifiers(
            base_changes, personality, event
        )
        
        # Apply existing emotional state influences
        state_modified_changes = await self._apply_emotional_state_influences(
            personality_changes, current_state
        )
        
        # Apply emotional relationships (reinforcement/opposition)
        final_changes = await self._apply_emotional_relationships(
            state_modified_changes, current_state
        )
        
        # Update emotional state
        new_state = await self._update_emotional_state(
            current_state, final_changes, event
        )
        
        # Generate behavioral response
        behavioral_changes = await self._generate_behavioral_changes(
            new_state, final_changes, personality
        )
        
        # Generate dialogue modifiers
        dialogue_modifiers = await self._generate_dialogue_modifiers(
            new_state, event.trigger
        )
        
        # Generate voice modifiers
        voice_modifiers = await self._generate_voice_modifiers(new_state)
        
        # Check for triggered memories
        triggered_memories = await self._check_memory_triggers(
            event, new_state, current_state
        )
        
        # Generate response text if appropriate
        response_text = await self._generate_emotional_response_text(
            event, new_state, personality
        )
        
        # Save emotional event
        await self._save_emotional_event(event, current_state, new_state, db_session)
        
        return EmotionalResponse(
            character_id=event.character_id,
            emotional_state=new_state,
            response_text=response_text,
            behavioral_changes=behavioral_changes,
            dialogue_modifiers=dialogue_modifiers,
            voice_modifiers=voice_modifiers,
            triggered_memories=triggered_memories
        )

    async def update_emotional_state_over_time(
        self,
        character_id: str,
        time_passed: timedelta,
        personality: PersonalityProfileSchema,
        db_session: Optional[Session] = None
    ) -> EmotionalStateSchema:
        """Update emotional state based on natural decay over time."""
        
        current_state = await self.get_emotional_state(character_id, db_session)
        minutes_passed = time_passed.total_seconds() / 60
        
        # Calculate decay for each emotion
        new_emotions = {}
        for emotion_type in [EmotionType.JOY, EmotionType.SADNESS, EmotionType.ANGER,
                           EmotionType.FEAR, EmotionType.SURPRISE, EmotionType.DISGUST,
                           EmotionType.TRUST, EmotionType.ANTICIPATION]:
            
            current_value = getattr(current_state, emotion_type.value.lower())
            
            # Calculate decay rate based on personality and emotion type
            decay_rate = await self._calculate_decay_rate(
                emotion_type, personality, current_state
            )
            
            # Apply decay (emotions tend toward baseline/neutral)
            baseline = current_state.baseline_mood if emotion_type in [EmotionType.JOY, EmotionType.TRUST] else 0.1
            
            if current_value > baseline:
                decay = decay_rate * minutes_passed
                new_value = max(baseline, current_value - decay)
            else:
                # Gradual recovery toward baseline
                recovery = (decay_rate * 0.5) * minutes_passed
                new_value = min(baseline, current_value + recovery)
                
            new_emotions[emotion_type.value.lower()] = new_value
        
        # Update state
        for emotion, value in new_emotions.items():
            setattr(current_state, emotion, value)
            
        # Update dominant emotion
        current_state.dominant_emotion, current_state.dominant_intensity = \
            await self._calculate_dominant_emotion(current_state)
            
        current_state.state_duration += int(minutes_passed)
        current_state.updated_at = datetime.utcnow()
        
        return current_state

    async def analyze_emotional_patterns(
        self,
        character_id: str,
        time_period: Optional[timedelta] = None,
        db_session: Optional[Session] = None
    ) -> EmotionAnalysis:
        """Analyze character's emotional patterns over time."""
        
        # In a real implementation, this would analyze historical emotional data
        return EmotionAnalysis(
            character_id=character_id,
            dominant_emotions=[EmotionType.JOY, EmotionType.TRUST],
            emotional_range={
                EmotionType.JOY: {"min": 0.2, "max": 0.9, "average": 0.6},
                EmotionType.TRUST: {"min": 0.3, "max": 0.8, "average": 0.6},
                EmotionType.ANGER: {"min": 0.0, "max": 0.4, "average": 0.1}
            },
            stability_score=0.7,
            volatility_score=0.3,
            emotional_intelligence_assessment=0.6,
            common_triggers=["dialogue", "quest_completion", "relationship_change"],
            emotional_blind_spots=["subtle_manipulation", "delayed_consequences"],
            recovery_patterns={"anger": 0.8, "sadness": 0.6, "fear": 0.7}
        )

    async def calculate_emotional_contagion(
        self,
        source_character_id: str,
        target_character_id: str,
        source_emotion: EmotionType,
        source_intensity: float,
        relationship_strength: float,
        proximity: float = 1.0
    ) -> EmotionalContagion:
        """Calculate how emotions spread between characters."""
        
        # Base transmission strength
        base_transmission = source_intensity * 0.3
        
        # Relationship influence
        relationship_modifier = relationship_strength * 0.4
        
        # Proximity influence
        proximity_modifier = proximity * 0.2
        
        # Emotion-specific transmission rates
        transmission_rates = {
            EmotionType.JOY: 0.8,
            EmotionType.ANGER: 0.6,
            EmotionType.FEAR: 0.7,
            EmotionType.SADNESS: 0.4,
            EmotionType.SURPRISE: 0.9,
            EmotionType.TRUST: 0.3,
            EmotionType.DISGUST: 0.5,
            EmotionType.ANTICIPATION: 0.5
        }
        
        emotion_modifier = transmission_rates.get(source_emotion, 0.5)
        
        transmission_strength = min(1.0, 
            base_transmission + relationship_modifier + proximity_modifier
        ) * emotion_modifier
        
        return EmotionalContagion(
            source_character_id=source_character_id,
            target_character_id=target_character_id,
            transmitted_emotion=source_emotion,
            transmission_strength=transmission_strength,
            transmission_factors={
                "relationship": relationship_modifier,
                "proximity": proximity_modifier,
                "emotion_type": emotion_modifier
            },
            resistance_factors={}  # Would be calculated based on target's personality
        )

    async def assess_stress_response(
        self,
        character_id: str,
        stress_source: str,
        stress_intensity: float,
        personality: PersonalityProfileSchema,
        current_state: EmotionalStateSchema
    ) -> StressResponse:
        """Assess how a character responds to stress."""
        
        # Determine coping mechanism based on personality
        coping_mechanisms = {
            "high_extraversion": "seek_social_support",
            "high_conscientiousness": "problem_solving",
            "high_neuroticism": "emotional_regulation_difficulty",
            "high_openness": "creative_coping",
            "high_agreeableness": "accommodative_coping"
        }
        
        # Find dominant personality trait
        personality_scores = {
            "extraversion": personality.extraversion,
            "conscientiousness": personality.conscientiousness,
            "neuroticism": personality.neuroticism,
            "openness": personality.openness,
            "agreeableness": personality.agreeableness
        }
        
        dominant_trait = max(personality_scores.items(), key=lambda x: x[1])
        coping_mechanism = coping_mechanisms.get(f"high_{dominant_trait[0]}", "adaptive_coping")
        
        # Calculate emotional impact
        emotional_impact = {
            EmotionType.ANGER: stress_intensity * 0.3,
            EmotionType.FEAR: stress_intensity * 0.4,
            EmotionType.SADNESS: stress_intensity * 0.2,
            EmotionType.JOY: -stress_intensity * 0.2,
            EmotionType.TRUST: -stress_intensity * 0.1
        }
        
        # Calculate recovery time based on personality and coping mechanism
        base_recovery = 60  # 60 minutes
        recovery_modifiers = {
            "seek_social_support": 0.8,
            "problem_solving": 0.7,
            "emotional_regulation_difficulty": 1.5,
            "creative_coping": 0.9,
            "accommodative_coping": 1.1
        }
        
        recovery_time = int(base_recovery * recovery_modifiers.get(coping_mechanism, 1.0))
        
        return StressResponse(
            character_id=character_id,
            stress_level=min(1.0, current_state.fear + current_state.anger + stress_intensity),
            stress_source=stress_source,
            coping_mechanism=coping_mechanism,
            emotional_impact=emotional_impact,
            behavioral_changes={
                "dialogue_directness": stress_intensity * 0.3,
                "risk_tolerance": -stress_intensity * 0.4,
                "social_interaction": -stress_intensity * 0.2
            },
            recovery_time=recovery_time
        )

    def _calculate_base_emotional_changes(
        self,
        event: EmotionalTriggerEvent,
        current_state: EmotionalStateSchema
    ) -> Dict[EmotionType, float]:
        """Calculate base emotional changes from trigger."""
        
        trigger_effects = self.trigger_mappings.get(event.trigger, {})
        changes = {}
        
        for emotion, base_change in trigger_effects.items():
            # Scale by event intensity
            actual_change = base_change * event.intensity
            
            # Add some randomness
            actual_change *= random.uniform(0.8, 1.2)
            
            changes[emotion] = actual_change
            
        return changes

    async def _apply_personality_modifiers(
        self,
        base_changes: Dict[EmotionType, float],
        personality: PersonalityProfileSchema,
        event: EmotionalTriggerEvent
    ) -> Dict[EmotionType, float]:
        """Apply personality-based modifiers to emotional changes."""
        
        modified_changes = base_changes.copy()
        
        # Neuroticism amplifies negative emotions
        if personality.neuroticism > 0.6:
            for emotion in [EmotionType.FEAR, EmotionType.SADNESS, EmotionType.ANGER]:
                if emotion in modified_changes and modified_changes[emotion] > 0:
                    modified_changes[emotion] *= (1.0 + personality.neuroticism * 0.5)
                    
        # Extraversion amplifies positive emotions
        if personality.extraversion > 0.6:
            for emotion in [EmotionType.JOY, EmotionType.ANTICIPATION]:
                if emotion in modified_changes and modified_changes[emotion] > 0:
                    modified_changes[emotion] *= (1.0 + personality.extraversion * 0.3)
                    
        # Conscientiousness provides emotional stability
        if personality.conscientiousness > 0.6:
            for emotion, change in modified_changes.items():
                modified_changes[emotion] = change * (0.7 + personality.conscientiousness * 0.3)
                
        return modified_changes

    async def _apply_emotional_state_influences(
        self,
        changes: Dict[EmotionType, float],
        current_state: EmotionalStateSchema
    ) -> Dict[EmotionType, float]:
        """Apply current emotional state influences to changes."""
        
        modified_changes = changes.copy()
        
        # High emotional instability amplifies changes
        instability = 1.0 - current_state.emotional_stability
        
        for emotion, change in modified_changes.items():
            # Amplify based on instability
            amplification = 1.0 + (instability * 0.5)
            modified_changes[emotion] = change * amplification
            
        return modified_changes

    async def _apply_emotional_relationships(
        self,
        changes: Dict[EmotionType, float],
        current_state: EmotionalStateSchema
    ) -> Dict[EmotionType, float]:
        """Apply emotional relationships (reinforcement, opposition)."""
        
        final_changes = changes.copy()
        
        for emotion, change in changes.items():
            if change > 0.1:  # Only apply for significant changes
                relationships = self.emotion_relationships.get(emotion, {})
                
                # Reinforce supporting emotions
                for reinforced_emotion in relationships.get("reinforces", []):
                    if reinforced_emotion not in final_changes:
                        final_changes[reinforced_emotion] = 0.0
                    final_changes[reinforced_emotion] += change * 0.2
                    
                # Reduce opposing emotions
                for opposed_emotion in relationships.get("opposes", []):
                    current_value = getattr(current_state, opposed_emotion.value.lower())
                    if current_value > 0.1:  # Only if there's something to reduce
                        if opposed_emotion not in final_changes:
                            final_changes[opposed_emotion] = 0.0
                        final_changes[opposed_emotion] -= change * 0.3
                        
        return final_changes

    async def _update_emotional_state(
        self,
        current_state: EmotionalStateSchema,
        changes: Dict[EmotionType, float],
        event: EmotionalTriggerEvent
    ) -> EmotionalStateSchema:
        """Update emotional state with calculated changes."""
        
        new_state = current_state.copy()
        significant_change = False
        
        # Apply changes with bounds checking
        for emotion, change in changes.items():
            current_value = getattr(current_state, emotion.value.lower())
            new_value = max(0.0, min(1.0, current_value + change))
            
            # Check if this is a significant change
            if abs(change) > 0.2:
                significant_change = True
                
            setattr(new_state, emotion.value.lower(), new_value)
            
        # Update metadata
        if significant_change:
            new_state.last_major_change = datetime.utcnow()
            new_state.state_duration = 0  # Reset duration counter
        else:
            new_state.state_duration += 1  # Increment by 1 minute
            
        # Update dominant emotion
        new_state.dominant_emotion, new_state.dominant_intensity = \
            await self._calculate_dominant_emotion(new_state)
            
        # Update triggers
        if not new_state.current_triggers:
            new_state.current_triggers = []
        new_state.current_triggers.append(event.trigger.value)
        
        # Keep only recent triggers
        if len(new_state.current_triggers) > 5:
            new_state.current_triggers = new_state.current_triggers[-5:]
            
        new_state.updated_at = datetime.utcnow()
        
        return new_state

    async def _calculate_dominant_emotion(
        self,
        state: EmotionalStateSchema
    ) -> Tuple[EmotionType, float]:
        """Calculate the dominant emotion and its intensity."""
        
        emotions = {
            EmotionType.JOY: state.joy,
            EmotionType.SADNESS: state.sadness,
            EmotionType.ANGER: state.anger,
            EmotionType.FEAR: state.fear,
            EmotionType.SURPRISE: state.surprise,
            EmotionType.DISGUST: state.disgust,
            EmotionType.TRUST: state.trust,
            EmotionType.ANTICIPATION: state.anticipation
        }
        
        dominant_emotion = max(emotions.items(), key=lambda x: x[1])
        return dominant_emotion[0], dominant_emotion[1]

    async def _calculate_decay_rate(
        self,
        emotion: EmotionType,
        personality: PersonalityProfileSchema,
        current_state: EmotionalStateSchema
    ) -> float:
        """Calculate decay rate for a specific emotion."""
        
        # Base decay rates
        base_rates = {
            EmotionType.JOY: 0.02,
            EmotionType.SADNESS: 0.015,
            EmotionType.ANGER: 0.025,
            EmotionType.FEAR: 0.02,
            EmotionType.SURPRISE: 0.05,  # Surprise fades quickly
            EmotionType.DISGUST: 0.02,
            EmotionType.TRUST: 0.005,    # Trust changes slowly
            EmotionType.ANTICIPATION: 0.03
        }
        
        base_rate = base_rates.get(emotion, 0.02)
        
        # Personality modifiers
        if personality.emotional_stability and hasattr(personality, 'emotional_stability'):
            stability_modifier = 0.8 + (personality.emotional_stability * 0.4)
        else:
            # Estimate from conscientiousness and neuroticism
            stability = (personality.conscientiousness + (1.0 - personality.neuroticism)) / 2
            stability_modifier = 0.8 + (stability * 0.4)
            
        return base_rate * stability_modifier

    async def _generate_behavioral_changes(
        self,
        new_state: EmotionalStateSchema,
        changes: Dict[EmotionType, float],
        personality: PersonalityProfileSchema
    ) -> Dict[str, Any]:
        """Generate behavioral changes based on emotional state."""
        
        behavioral_changes = {}
        
        # Dominant emotion influences behavior
        if new_state.dominant_intensity > 0.6:
            if new_state.dominant_emotion == EmotionType.ANGER:
                behavioral_changes.update({
                    "aggression_level": new_state.dominant_intensity,
                    "patience_level": 1.0 - new_state.dominant_intensity,
                    "risk_tolerance": new_state.dominant_intensity * 0.8
                })
            elif new_state.dominant_emotion == EmotionType.FEAR:
                behavioral_changes.update({
                    "caution_level": new_state.dominant_intensity,
                    "social_withdrawal": new_state.dominant_intensity * 0.6,
                    "risk_tolerance": 1.0 - new_state.dominant_intensity
                })
            elif new_state.dominant_emotion == EmotionType.JOY:
                behavioral_changes.update({
                    "friendliness_level": new_state.dominant_intensity,
                    "optimism_level": new_state.dominant_intensity,
                    "risk_tolerance": new_state.dominant_intensity * 0.7
                })
                
        return behavioral_changes

    async def _generate_dialogue_modifiers(
        self,
        state: EmotionalStateSchema,
        trigger: EmotionTrigger
    ) -> Dict[str, float]:
        """Generate dialogue modifiers based on emotional state."""
        
        modifiers = {}
        
        # Emotional intensity affects speech patterns
        if state.dominant_intensity > 0.5:
            if state.dominant_emotion == EmotionType.ANGER:
                modifiers.update({
                    "directness": state.dominant_intensity,
                    "politeness": 1.0 - state.dominant_intensity,
                    "volume": 1.0 + (state.dominant_intensity * 0.5)
                })
            elif state.dominant_emotion == EmotionType.SADNESS:
                modifiers.update({
                    "verbosity": 1.0 - (state.dominant_intensity * 0.5),
                    "energy": 1.0 - state.dominant_intensity,
                    "pessimism": state.dominant_intensity
                })
            elif state.dominant_emotion == EmotionType.JOY:
                modifiers.update({
                    "enthusiasm": state.dominant_intensity,
                    "positivity": state.dominant_intensity,
                    "talkativeness": 1.0 + (state.dominant_intensity * 0.3)
                })
                
        return modifiers

    async def _generate_voice_modifiers(
        self,
        state: EmotionalStateSchema
    ) -> Dict[str, float]:
        """Generate voice synthesis modifiers based on emotional state."""
        
        modifiers = {"pitch": 1.0, "speed": 1.0, "volume": 1.0}
        
        if state.dominant_intensity > 0.3:
            if state.dominant_emotion == EmotionType.ANGER:
                modifiers.update({
                    "pitch": 0.9 - (state.dominant_intensity * 0.2),
                    "speed": 1.0 + (state.dominant_intensity * 0.3),
                    "volume": 1.0 + (state.dominant_intensity * 0.4)
                })
            elif state.dominant_emotion == EmotionType.SADNESS:
                modifiers.update({
                    "pitch": 0.8 - (state.dominant_intensity * 0.2),
                    "speed": 0.8 - (state.dominant_intensity * 0.2),
                    "volume": 0.8 - (state.dominant_intensity * 0.2)
                })
            elif state.dominant_emotion == EmotionType.JOY:
                modifiers.update({
                    "pitch": 1.0 + (state.dominant_intensity * 0.3),
                    "speed": 1.0 + (state.dominant_intensity * 0.2),
                    "volume": 1.0 + (state.dominant_intensity * 0.2)
                })
            elif state.dominant_emotion == EmotionType.FEAR:
                modifiers.update({
                    "pitch": 1.0 + (state.dominant_intensity * 0.4),
                    "speed": 1.0 + (state.dominant_intensity * 0.5),
                    "volume": 0.9 - (state.dominant_intensity * 0.3)
                })
                
        return modifiers

    async def _check_memory_triggers(
        self,
        event: EmotionalTriggerEvent,
        new_state: EmotionalStateSchema,
        old_state: EmotionalStateSchema
    ) -> List[str]:
        """Check if emotional changes trigger memory recalls."""
        
        triggered_memories = []
        
        # Strong emotional changes can trigger related memories
        if new_state.dominant_intensity > 0.7:
            # In a real implementation, this would query memory service
            mock_memories = ["mem_001", "mem_002"]
            triggered_memories.extend(mock_memories)
            
        return triggered_memories

    async def _generate_emotional_response_text(
        self,
        event: EmotionalTriggerEvent,
        new_state: EmotionalStateSchema,
        personality: PersonalityProfileSchema
    ) -> Optional[str]:
        """Generate text response for strong emotional reactions."""
        
        if new_state.dominant_intensity < 0.6:
            return None
            
        response_templates = {
            EmotionType.ANGER: [
                "This is infuriating!",
                "I can't stand this anymore!",
                "How dare they!"
            ],
            EmotionType.JOY: [
                "This is wonderful!",
                "I couldn't be happier!",
                "What great news!"
            ],
            EmotionType.FEAR: [
                "I'm not sure about this...",
                "This makes me nervous.",
                "What if something goes wrong?"
            ],
            EmotionType.SADNESS: [
                "This is so disappointing.",
                "I feel terrible about this.",
                "Nothing seems to go right."
            ]
        }
        
        templates = response_templates.get(new_state.dominant_emotion, [])
        if templates:
            return random.choice(templates)
            
        return None

    async def _save_emotional_event(
        self,
        event: EmotionalTriggerEvent,
        old_state: EmotionalStateSchema,
        new_state: EmotionalStateSchema,
        db_session: Optional[Session]
    ) -> None:
        """Save emotional event to database."""
        
        # In a real implementation, this would save to database
        logger.info(f"Saved emotional event for character {event.character_id}: {event.trigger.value}")