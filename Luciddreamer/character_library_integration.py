#!/usr/bin/env python3
"""
Luciddreamer Character Library Integration and Personality Modeling System

This module provides comprehensive character personality modeling for Luciddreamer agents,
integrating psychological frameworks (Big Five, Enneagram, MBTI) with character archetypes,
dialogue generation, emotional modeling, and growth mechanisms.

Key Features:
- 12 archetypal characters with unique personalities
- Big Five, Enneagram, and MBTI personality frameworks
- Personality-driven response generation
- Character dialogue patterns and voice consistency
- Relationship dynamics and compatibility
- Character skill trees and specialization
- Emotional modeling and expression
- Character growth and evolution
"""

import json
import uuid
import time
import random
import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import logging

# Import Luciddreamer memory system
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from memory.hierarchical_memory import HierarchicalMemorySystem
from memory.episodic_memory import EmotionalValence
from memory.procedural_memory import SkillType, PracticeResult

logger = logging.getLogger(__name__)

# ============================================================================
# PERSONALITY FRAMEWORKS
# ============================================================================

@dataclass
class BigFivePersonality:
    """Big Five personality traits (OCEAN)"""
    openness: float = 0.5        # Openness to experience (1-10)
    conscientiousness: float = 0.5  # Organization and discipline
    extraversion: float = 0.5     # Social energy and stimulation
    agreeableness: float = 0.5    # Cooperation and social harmony
    neuroticism: float = 0.5      # Emotional stability and reactivity

    def to_dict(self) -> Dict[str, float]:
        return {
            'openness': self.openness,
            'conscientiousness': self.conscientiousness,
            'extraversion': self.extraversion,
            'agreeableness': self.agreeableness,
            'neuroticism': self.neuroticism
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'BigFivePersonality':
        return cls(**data)

class EnneagramType(Enum):
    """Enneagram personality types"""
    TYPE_1_REFORMER = "1 - The Reformer"
    TYPE_2_HELPER = "2 - The Helper"
    TYPE_3_ACHIEVER = "3 - The Achiever"
    TYPE_4_INDIVIDUALIST = "4 - The Individualist"
    TYPE_5_INVESTIGATOR = "5 - The Investigator"
    TYPE_6_LOYALIST = "6 - The Loyalist"
    TYPE_7_ENTHUSIAST = "7 - The Enthusiast"
    TYPE_8_CHALLENGER = "8 - The Challenger"
    TYPE_9_PEACEMAKER = "9 - The Peacemaker"

class MBTIType(Enum):
    """Myers-Briggs Type Indicator types"""
    INTJ = "INTJ - The Architect"
    INTP = "INTP - The Thinker"
    ENTJ = "ENTJ - The Commander"
    ENTP = "ENTP - The Debater"
    INFJ = "INFJ - The Advocate"
    INFP = "INFP - The Mediator"
    ENFJ = "ENFJ - The Protagonist"
    ENFP = "ENFP - The Campaigner"
    ISTJ = "ISTJ - The Logistician"
    ISFJ = "ISFJ - The Defender"
    ESTJ = "ESTJ - The Executive"
    ESFJ = "ESFJ - The Consul"
    ISTP = "ISTP - The Virtuoso"
    ISFP = "ISFP - The Adventurer"
    ESTP = "ESTP - The Entrepreneur"
    ESFP = "ESFP - The Entertainer"

# ============================================================================
# CHARACTER ARCHETYPES
# ============================================================================

class CharacterArchetype(Enum):
    """12 core character archetypes"""
    INNOVATOR = "The Innovator"
    EDUCATOR = "The Educator"
    STORYTELLER = "The Storyteller"
    CREATOR = "The Creator"
    PHILOSOPHER = "The Philosopher"
    ANALYST = "The Analyst"
    LEADER = "The Leader"
    MORAL_GUIDE = "The Moral Guide"
    HUMORIST = "The Humorist"
    EMPATH = "The Empath"
    BUILDER = "The Builder"
    ENGINEER = "The Engineer"

@dataclass
class ArchetypeProfile:
    """Detailed archetype profile with personality mappings"""
    archetype: CharacterArchetype
    description: str
    core_motivation: str
    core_fear: str
    big_five_baseline: BigFivePersonality
    enneagram_types: List[EnneagramType]
    mbti_types: List[MBTIType]
    dialogue_patterns: List[str]
    voice_characteristics: Dict[str, Any]
    relationship_tendencies: Dict[str, str]
    growth_areas: List[str]
    special_skills: List[str]

# ============================================================================
# EMOTIONAL MODELING
# ============================================================================

class BasicEmotion(Enum):
    """Basic emotion categories"""
    JOY = "joy"
    TRUST = "trust"
    FEAR = "fear"
    SURPRISE = "surprise"
    SADNESS = "sadness"
    DISGUST = "disgust"
    ANGER = "anger"
    ANTICIPATION = "anticipation"

@dataclass
class EmotionalState:
    """Current emotional state of a character"""
    primary_emotion: BasicEmotion
    secondary_emotion: Optional[BasicEmotion]
    intensity: float  # 0.0 to 1.0
    valence: float    # -1.0 (negative) to 1.0 (positive)
    arousal: float    # 0.0 (calm) to 1.0 (excited)
    duration_minutes: int
    triggers: List[str]
    visible_cues: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'primary_emotion': self.primary_emotion.value,
            'secondary_emotion': self.secondary_emotion.value if self.secondary_emotion else None,
            'intensity': self.intensity,
            'valence': self.valence,
            'arousal': self.arousal,
            'duration_minutes': self.duration_minutes,
            'triggers': self.triggers,
            'visible_cues': self.visible_cues
        }

# ============================================================================
# SKILLS AND SPECIALIZATIONS
# ============================================================================

@dataclass
class CharacterSkill:
    """Character skill with progression"""
    name: str
    category: str
    current_level: float  # 0.0 to 10.0
    max_level: float = 10.0
    experience_points: int = 0
    prerequisites: List[str] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)
    last_practiced: Optional[datetime] = None

    def practice(self, difficulty: float, performance: float, time_spent: float) -> float:
        """Practice skill and return improvement amount"""
        # Calculate experience gained
        base_exp = int(difficulty * performance * time_spent * 10)
        self.experience_points += base_exp

        # Calculate level improvement
        improvement = (difficulty * performance * time_spent) / 100
        self.current_level = min(self.max_level, self.current_level + improvement)
        self.last_practiced = datetime.now()

        return improvement

@dataclass
class SkillTree:
    """Skill tree structure for character development"""
    name: str
    description: str
    skills: Dict[str, CharacterSkill] = field(default_factory=dict)
    unlock_requirements: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    mastery_bonuses: Dict[str, Dict[str, float]] = field(default_factory=dict)

# ============================================================================
# RELATIONSHIP DYNAMICS
# ============================================================================

class RelationshipType(Enum):
    """Types of relationships between characters"""
    FRIENDSHIP = "friendship"
    MENTORSHIP = "mentorship"
    RIVALRY = "rivalry"
    ROMANTIC = "romantic"
    FAMILY = "family"
    PROFESSIONAL = "professional"
    ALLIANCE = "alliance"
    ANTAGONISTIC = "antagonistic"

@dataclass
class CharacterRelationship:
    """Relationship between two characters"""
    target_character_id: str
    relationship_type: RelationshipType
    strength: float  # 0.0 to 1.0
    trust_level: float  # 0.0 to 1.0
    communication_style: str
    shared_history: List[str]
    conflict_points: List[str]
    support_areas: List[str]
    last_interaction: Optional[datetime] = None

    def update_strength(self, delta: float, interaction_type: str):
        """Update relationship strength based on interaction"""
        self.strength = max(0.0, min(1.0, self.strength + delta))
        self.last_interaction = datetime.now()

        # Add to shared history
        history_entry = f"{datetime.now().strftime('%Y-%m-%d')}: {interaction_type}"
        self.shared_history.append(history_entry)

# ============================================================================
# MAIN CHARACTER CLASS
# ============================================================================

class LuciddreamerCharacter:
    """Main character class integrating all personality and development systems"""

    def __init__(self, name: str, archetype: CharacterArchetype,
                 big_five: Optional[BigFivePersonality] = None,
                 enneagram: Optional[EnneagramType] = None,
                 mbti: Optional[MBTIType] = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.archetype = archetype
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # Personality frameworks
        self.big_five = big_five or self._generate_big_five_for_archetype(archetype)
        self.enneagram = enneagram or self._get_default_enneagram_for_archetype(archetype)
        self.mbti = mbti or self._get_default_mbti_for_archetype(archetype)

        # Emotional state
        self.current_emotional_state = EmotionalState(
            primary_emotion=BasicEmotion.JOY,
            secondary_emotion=None,
            intensity=0.5,
            valence=0.5,
            arousal=0.5,
            duration_minutes=0,
            triggers=[],
            visible_cues=[]
        )
        self.emotional_history: List[EmotionalState] = []

        # Skills and development
        self.skills: Dict[str, CharacterSkill] = {}
        self.skill_trees: Dict[str, SkillTree] = {}
        self.specializations: List[str] = []

        # Relationships
        self.relationships: Dict[str, CharacterRelationship] = {}

        # Dialogue and voice
        self.voice_profile = self._generate_voice_profile()
        self.dialogue_history: List[Dict[str, Any]] = []
        self.catchphrases: List[str] = []

        # Memory system integration
        self.memory_system: Optional[HierarchicalMemorySystem] = None

        # Growth and evolution
        self.personality_growth_points: Dict[str, float] = {
            'openness_growth': 0.0,
            'conscientiousness_growth': 0.0,
            'extraversion_growth': 0.0,
            'agreeableness_growth': 0.0,
            'neuroticism_growth': 0.0
        }

        # Initialize archetype-specific traits
        self._initialize_archetype_traits()

    def _generate_big_five_for_archetype(self, archetype: CharacterArchetype) -> BigFivePersonality:
        """Generate baseline Big Five personality for archetype"""
        baselines = {
            CharacterArchetype.INNOVATOR: BigFivePersonality(
                openness=0.9, conscientiousness=0.4, extraversion=0.6,
                agreeableness=0.5, neuroticism=0.3
            ),
            CharacterArchetype.EDUCATOR: BigFivePersonality(
                openness=0.7, conscientiousness=0.8, extraversion=0.5,
                agreeableness=0.7, neuroticism=0.4
            ),
            CharacterArchetype.STORYTELLER: BigFivePersonality(
                openness=0.8, conscientiousness=0.5, extraversion=0.7,
                agreeableness=0.8, neuroticism=0.6
            ),
            CharacterArchetype.CREATOR: BigFivePersonality(
                openness=0.95, conscientiousness=0.3, extraversion=0.4,
                agreeableness=0.4, neuroticism=0.7
            ),
            CharacterArchetype.PHILOSOPHER: BigFivePersonality(
                openness=0.85, conscientiousness=0.6, extraversion=0.3,
                agreeableness=0.6, neuroticism=0.5
            ),
            CharacterArchetype.ANALYST: BigFivePersonality(
                openness=0.6, conscientiousness=0.9, extraversion=0.2,
                agreeableness=0.3, neuroticism=0.4
            ),
            CharacterArchetype.LEADER: BigFivePersonality(
                openness=0.6, conscientiousness=0.7, extraversion=0.9,
                agreeableness=0.6, neuroticism=0.3
            ),
            CharacterArchetype.MORAL_GUIDE: BigFivePersonality(
                openness=0.5, conscientiousness=0.8, extraversion=0.6,
                agreeableness=0.9, neuroticism=0.2
            ),
            CharacterArchetype.HUMORIST: BigFivePersonality(
                openness=0.7, conscientiousness=0.3, extraversion=0.8,
                agreeableness=0.7, neuroticism=0.5
            ),
            CharacterArchetype.EMPATH: BigFivePersonality(
                openness=0.7, conscientiousness=0.5, extraversion=0.6,
                agreeableness=0.95, neuroticism=0.6
            ),
            CharacterArchetype.BUILDER: BigFivePersonality(
                openness=0.4, conscientiousness=0.9, extraversion=0.5,
                agreeableness=0.6, neuroticism=0.3
            ),
            CharacterArchetype.ENGINEER: BigFivePersonality(
                openness=0.6, conscientiousness=0.95, extraversion=0.4,
                agreeableness=0.5, neuroticism=0.4
            )
        }

        return baselines.get(archetype, BigFivePersonality())

    def _get_default_enneagram_for_archetype(self, archetype: CharacterArchetype) -> EnneagramType:
        """Get default Enneagram type for archetype"""
        mapping = {
            CharacterArchetype.INNOVATOR: EnneagramType.TYPE_7_ENTHUSIAST,
            CharacterArchetype.EDUCATOR: EnneagramType.TYPE_2_HELPER,
            CharacterArchetype.STORYTELLER: EnneagramType.TYPE_4_INDIVIDUALIST,
            CharacterArchetype.CREATOR: EnneagramType.TYPE_4_INDIVIDUALIST,
            CharacterArchetype.PHILOSOPHER: EnneagramType.TYPE_5_INVESTIGATOR,
            CharacterArchetype.ANALYST: EnneagramType.TYPE_5_INVESTIGATOR,
            CharacterArchetype.LEADER: EnneagramType.TYPE_8_CHALLENGER,
            CharacterArchetype.MORAL_GUIDE: EnneagramType.TYPE_1_REFORMER,
            CharacterArchetype.HUMORIST: EnneagramType.TYPE_7_ENTHUSIAST,
            CharacterArchetype.EMPATH: EnneagramType.TYPE_2_HELPER,
            CharacterArchetype.BUILDER: EnneagramType.TYPE_3_ACHIEVER,
            CharacterArchetype.ENGINEER: EnneagramType.TYPE_5_INVESTIGATOR
        }
        return mapping.get(archetype, EnneagramType.TYPE_5_INVESTIGATOR)

    def _get_default_mbti_for_archetype(self, archetype: CharacterArchetype) -> MBTIType:
        """Get default MBTI type for archetype"""
        mapping = {
            CharacterArchetype.INNOVATOR: MBTIType.ENFP,
            CharacterArchetype.EDUCATOR: MBTIType.ENFJ,
            CharacterArchetype.STORYTELLER: MBTIType.INFP,
            CharacterArchetype.CREATOR: MBTIType.INFP,
            CharacterArchetype.PHILOSOPHER: MBTIType.INTJ,
            CharacterArchetype.ANALYST: MBTIType.ISTJ,
            CharacterArchetype.LEADER: MBTIType.ENTJ,
            CharacterArchetype.MORAL_GUIDE: MBTIType.INFJ,
            CharacterArchetype.HUMORIST: MBTIType.ENFP,
            CharacterArchetype.EMPATH: MBTIType.INFJ,
            CharacterArchetype.BUILDER: MBTIType.ESTJ,
            CharacterArchetype.ENGINEER: MBTIType.INTP
        }
        return mapping.get(archetype, MBTIType.INTJ)

    def _initialize_archetype_traits(self):
        """Initialize archetype-specific skills and traits"""
        archetype_configs = {
            CharacterArchetype.INNOVATOR: {
                'skills': ['creative_thinking', 'problem_solving', 'adaptability', 'vision'],
                'catchphrases': ["Let's think differently", "What if we tried...", "That's interesting..."]
            },
            CharacterArchetype.EDUCATOR: {
                'skills': ['teaching', 'communication', 'patience', 'knowledge_retention'],
                'catchphrases': ["Let me explain...", "The key insight is...", "Think about it this way"]
            },
            CharacterArchetype.STORYTELLER: {
                'skills': ['narrative_craft', 'emotional_intelligence', 'memory', 'wisdom'],
                'catchphrases': ["I remember a time...", "The story goes...", "Let me tell you..."]
            },
            CharacterArchetype.CREATOR: {
                'skills': ['design_thinking', 'aesthetics', 'craftsmanship', 'vision'],
                'catchphrases': ["Why are we doing this?", "It's not perfect yet", "Form follows function"]
            },
            CharacterArchetype.PHILOSOPHER: {
                'skills': ['critical_thinking', 'logic', 'wisdom', 'meditation'],
                'catchphrases': ["The obstacle is the way", "Question everything", "What is the essence?"]
            },
            CharacterArchetype.ANALYST: {
                'skills': ['research', 'data_analysis', 'critical_thinking', 'attention_to_detail'],
                'catchphrases': ["What evidence supports that?", "Let me check the data", "Actually..."]
            },
            CharacterArchetype.LEADER: {
                'skills': ['leadership', 'diplomacy', 'strategy', 'inspiration'],
                'catchphrases': ["Our shared humanity matters", "We're in this together", "Trust the process"]
            },
            CharacterArchetype.MORAL_GUIDE: {
                'skills': ['moral_reasoning', 'empathy', 'wisdom', 'counseling'],
                'catchphrases': ["Love is the answer", "Hate cannot drive out hate", "We must do what's right"]
            },
            CharacterArchetype.HUMORIST: {
                'skills': ['wit', 'social_intelligence', 'timing', 'improvisation'],
                'catchphrases': ["Laughter is the best medicine", "Well, well, well...", "That's funny because..."]
            },
            CharacterArchetype.EMPATH: {
                'skills': ['empathy', 'listening', 'emotional_support', 'intuition'],
                'catchphrases': ["How does that make you feel?", "I hear you", "What I know for sure is..."]
            },
            CharacterArchetype.BUILDER: {
                'skills': ['planning', 'execution', 'resource_management', 'resilience'],
                'catchphrases': ["Build your dreams", "One step at a time", "Foundation first"]
            },
            CharacterArchetype.ENGINEER: {
                'skills': ['system_design', 'problem_solving', 'innovation', 'execution'],
                'catchphrases': ["If something's important enough, we should try", "Let's prototype it", "How does it work?"]
            }
        }

        config = archetype_configs.get(self.archetype, {})
        self.catchphrases = config.get('catchphrases', [])

        # Initialize skills
        for skill_name in config.get('skills', []):
            self.skills[skill_name] = CharacterSkill(
                name=skill_name,
                category=self.archetype.value,
                current_level=random.uniform(6.0, 8.0),  # Archetypes have strong base skills
                experience_points=0
            )

    def _generate_voice_profile(self) -> Dict[str, Any]:
        """Generate voice profile based on personality"""
        profile = {
            'pace': 'moderate',
            'tone': 'neutral',
            'vocabulary_level': 'moderate',
            'formality': 'casual',
            'humor_frequency': 0.1,
            'question_frequency': 0.2,
            'metaphor_frequency': 0.1,
            'emotional_expression': 0.5
        }

        # Adjust based on Big Five traits
        if self.big_five.extraversion > 0.7:
            profile['pace'] = 'fast'
            profile['formality'] = 'casual'
        elif self.big_five.extraversion < 0.3:
            profile['pace'] = 'slow'
            profile['question_frequency'] = 0.4

        if self.big_five.openness > 0.7:
            profile['metaphor_frequency'] = 0.3
            profile['vocabulary_level'] = 'high'

        if self.big_five.agreeableness > 0.7:
            profile['tone'] = 'warm'
            profile['emotional_expression'] = 0.7

        if self.big_five.conscientiousness > 0.7:
            profile['pace'] = 'measured'
            profile['vocabulary_level'] = 'precise'

        # Adjust based on archetype
        if self.archetype == CharacterArchetype.HUMORIST:
            profile['humor_frequency'] = 0.6
        elif self.archetype == CharacterArchetype.EDUCATOR:
            profile['question_frequency'] = 0.4
            profile['metaphor_frequency'] = 0.2
        elif self.archetype == CharacterArchetype.PHILOSOPHER:
            profile['pace'] = 'slow'
            profile['question_frequency'] = 0.5

        return profile

    # ========================================================================
    # DIALOGUE GENERATION
    # ========================================================================

    def generate_dialogue(self, context: Dict[str, Any],
                         emotional_influence: bool = True) -> str:
        """Generate personality-driven dialogue response"""

        # Get base response patterns
        base_responses = self._get_base_dialogue_patterns(context)

        # Select and modify based on personality
        response = random.choice(base_responses)

        # Apply personality modifications
        response = self._apply_personality_to_dialogue(response, context)

        # Apply emotional influence
        if emotional_influence:
            response = self._apply_emotional_influence(response)

        # Add characteristic elements
        response = self._add_voice_characteristics(response)

        # Log dialogue
        self._log_dialogue(context, response)

        return response

    def _get_base_dialogue_patterns(self, context: Dict[str, Any]) -> List[str]:
        """Get base dialogue patterns based on context"""
        situation = context.get('situation', 'neutral')

        patterns = {
            'problem_solving': [
                "Let me think about this systematically.",
                "We need to understand the root cause.",
                "What are the key variables here?",
                "Let's break this down into smaller parts."
            ],
            'social_interaction': [
                "It's good to see you.",
                "How have you been?",
                "I've been thinking about our last conversation.",
                "There's something I wanted to discuss."
            ],
            'conflict': [
                "I understand your perspective.",
                "Can we find common ground?",
                "This situation requires careful consideration.",
                "Let's approach this constructively."
            ],
            'discovery': [
                "This changes everything.",
                "That's fascinating!",
                "I never considered that possibility.",
                "What are the implications of this?"
            ],
            'teaching': [
                "Let me explain this step by step.",
                "The key principle here is...",
                "Think about it like this...",
                "What questions do you have?"
            ],
            'emotional_support': [
                "I'm here for you.",
                "Your feelings are valid.",
                "How can I support you?",
                "You're stronger than you think."
            ]
        }

        return patterns.get(situation, ["That's interesting."])

    def _apply_personality_to_dialogue(self, response: str, context: Dict[str, Any]) -> str:
        """Apply personality traits to dialogue"""

        # Big Five modifications
        if self.big_five.extraversion > 0.7:
            response = f"You know, {response.lower()}"
        elif self.big_five.extraversion < 0.3:
            response = f"Hmm. {response}"

        if self.big_five.openness > 0.7:
            response = f"{response} This reminds me of a broader principle..."
        elif self.big_five.openness < 0.3:
            response = f"{response} Let's focus on the practical aspects."

        if self.big_five.agreeableness > 0.7:
            response = f"{response} What do you think?"
        elif self.big_five.agreeableness < 0.3:
            response = f"{response} That's my position."

        # Archetype-specific modifications
        if self.archetype == CharacterArchetype.INNOVATOR:
            response = f"{response} But what if we approached it completely differently?"
        elif self.archetype == CharacterArchetype.EDUCATOR:
            response = f"Let me clarify: {response}"
        elif self.archetype == CharacterArchetype.PHILOSOPHER:
            response = f"The question beneath the question is: {response}"
        elif self.archetype == CharacterArchetype.ANALYST:
            response = f"Actually, {response}"
        elif self.archetype == CharacterArchetype.HUMORIST:
            if random.random() < 0.3:
                response = f"{response} *chuckles* Which reminds me of..."

        return response

    def _apply_emotional_influence(self, response: str) -> str:
        """Apply current emotional state to dialogue"""
        emotion = self.current_emotional_state.primary_emotion
        intensity = self.current_emotional_state.intensity

        if emotion == BasicEmotion.JOY and intensity > 0.7:
            response = f"{response}! This is wonderful!"
        elif emotion == BasicEmotion.ANGER and intensity > 0.6:
            response = f"{response} Frankly, I'm frustrated about this."
        elif emotion == BasicEmotion.SADNESS and intensity > 0.6:
            response = f"{response} *sigh*"
        elif emotion == BasicEmotion.FEAR and intensity > 0.6:
            response = f"{response} I'm concerned about..."

        return response

    def _add_voice_characteristics(self, response: str) -> str:
        """Add characteristic speech patterns"""
        voice = self.voice_profile

        # Add catchphrases occasionally
        if self.catchphrases and random.random() < 0.1:
            catchphrase = random.choice(self.catchphrases)
            response = f"{catchphrase} {response}"

        # Add questions if character is inquisitive
        if random.random() < voice['question_frequency']:
            response += " Don't you think?"

        # Add metaphors if character is abstract-minded
        if random.random() < voice['metaphor_frequency']:
            metaphors = [
                "like building a bridge",
                "like planting a seed",
                "like navigating by stars",
                "like weaving a tapestry"
            ]
            response += f" It's {random.choice(metaphors)}."

        return response

    def _log_dialogue(self, context: Dict[str, Any], response: str):
        """Log dialogue for character development"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'context': context,
            'response': response,
            'emotional_state': self.current_emotional_state.to_dict(),
            'voice_profile': self.voice_profile.copy()
        }
        self.dialogue_history.append(log_entry)

        # Keep history manageable
        if len(self.dialogue_history) > 1000:
            self.dialogue_history = self.dialogue_history[-500:]

    # ========================================================================
    # EMOTIONAL MODELING
    # ========================================================================

    def update_emotional_state(self, trigger: str, emotion: BasicEmotion,
                             intensity: float, duration_minutes: int = 30):
        """Update character's emotional state"""
        # Store previous state in history
        self.emotional_history.append(self.current_emotional_state)

        # Calculate valence and arousal based on emotion
        valence_arousal_map = {
            BasicEmotion.JOY: (0.8, 0.7),
            BasicEmotion.TRUST: (0.7, 0.3),
            BasicEmotion.FEAR: (-0.6, 0.8),
            BasicEmotion.SURPRISE: (0.2, 0.9),
            BasicEmotion.SADNESS: (-0.7, 0.2),
            BasicEmotion.DISGUST: (-0.5, 0.4),
            BasicEmotion.ANGER: (-0.6, 0.8),
            BasicEmotion.ANTICIPATION: (0.4, 0.6)
        }

        valence, arousal = valence_arousal_map.get(emotion, (0.0, 0.5))

        # Adjust based on personality
        if self.big_five.neuroticism > 0.7:
            intensity *= 1.3
            valence *= 0.8

        if self.big_five.extraversion > 0.7:
            arousal *= 1.2

        # Generate visible cues
        visible_cues = self._generate_emotional_cues(emotion, intensity)

        # Update emotional state
        self.current_emotional_state = EmotionalState(
            primary_emotion=emotion,
            secondary_emotion=self.current_emotional_state.primary_emotion if intensity < 0.7 else None,
            intensity=min(1.0, intensity),
            valence=valence,
            arousal=arousal,
            duration_minutes=duration_minutes,
            triggers=[trigger],
            visible_cues=visible_cues
        )

        self.updated_at = datetime.now()

    def _generate_emotional_cues(self, emotion: BasicEmotion, intensity: float) -> List[str]:
        """Generate visible emotional cues based on emotion and intensity"""
        cues_map = {
            BasicEmotion.JOY: ["smiles", "bright eyes", "relaxed posture"] if intensity > 0.6 else ["slight smile"],
            BasicEmotion.TRUST: ["open posture", "steady gaze", "relaxed shoulders"],
            BasicEmotion.FEAR: ["widened eyes", "tense muscles", "quick breathing"] if intensity > 0.6 else ["nervous glance"],
            BasicEmotion.SURPRISE: ["raised eyebrows", "open mouth", "slight lean back"],
            BasicEmotion.SADNESS: ["downcast eyes", "slumped shoulders", "quiet voice"] if intensity > 0.6 else ["subtle frown"],
            BasicEmotion.DISGUST: ["wrinkled nose", "turned away", "tight lips"],
            BasicEmotion.ANGER: ["clenched jaw", "tense posture", "sharp tone"] if intensity > 0.6 else ["furrowed brow"],
            BasicEmotion.ANTICIPATION: ["leaning forward", "bright eyes", "alert posture"]
        }

        return cues_map.get(emotion, ["neutral expression"])

    def process_emotional_decay(self):
        """Process natural emotional decay over time"""
        if self.current_emotional_state.duration_minutes > 0:
            self.current_emotional_state.duration_minutes -= 5

            # Decay intensity
            if self.current_emotional_state.intensity > 0.1:
                self.current_emotional_state.intensity *= 0.95

            # Return to baseline if emotion has faded
            if self.current_emotional_state.duration_minutes <= 0 or self.current_emotional_state.intensity < 0.1:
                self.current_emotional_state = EmotionalState(
                    primary_emotion=BasicEmotion.JOY,
                    secondary_emotion=None,
                    intensity=0.5,
                    valence=0.5,
                    arousal=0.5,
                    duration_minutes=0,
                    triggers=[],
                    visible_cues=[]
                )

    # ========================================================================
    # SKILL DEVELOPMENT
    # ========================================================================

    def add_skill(self, skill_name: str, category: str, initial_level: float = 1.0):
        """Add a new skill to the character"""
        if skill_name not in self.skills:
            self.skills[skill_name] = CharacterSkill(
                name=skill_name,
                category=category,
                current_level=min(10.0, initial_level),
                experience_points=0
            )
            self.updated_at = datetime.now()

    def practice_skill(self, skill_name: str, difficulty: float,
                      performance: float, time_spent: float) -> float:
        """Practice a skill and return improvement"""
        if skill_name not in self.skills:
            self.add_skill(skill_name, "general")

        improvement = self.skills[skill_name].practice(difficulty, performance, time_spent)

        # Update memory system if available
        if self.memory_system:
            memory_content = f"Practiced {skill_name} for {time_spent:.1f} minutes with {performance:.1%} performance"
            self.memory_system.add_episodic_memory(
                content=memory_content,
                summary=f"Skill practice: {skill_name}",
                importance=min(1.0, difficulty * performance),
                tags={"skill_practice", skill_name.lower()}
            )

        self.updated_at = datetime.now()
        return improvement

    def get_skill_level(self, skill_name: str) -> float:
        """Get current level of a skill"""
        return self.skills.get(skill_name, CharacterSkill(skill_name, "unknown", 0.0)).current_level

    def develop_specialization(self, skill_name: str, specialization: str):
        """Develop a specialization within a skill"""
        if skill_name in self.skills:
            skill = self.skills[skill_name]
            if specialization not in skill.specializations:
                skill.specializations.append(specialization)
                self.updated_at = datetime.now()

    # ========================================================================
    # RELATIONSHIP MANAGEMENT
    # ========================================================================

    def add_relationship(self, target_character_id: str, relationship_type: RelationshipType,
                        initial_strength: float = 0.5):
        """Add a new relationship"""
        if target_character_id not in self.relationships:
            self.relationships[target_character_id] = CharacterRelationship(
                target_character_id=target_character_id,
                relationship_type=relationship_type,
                strength=initial_strength,
                trust_level=initial_strength,
                communication_style=self._get_communication_style_for_relationship(relationship_type),
                shared_history=[],
                conflict_points=[],
                support_areas=[]
            )
            self.updated_at = datetime.now()

    def _get_communication_style_for_relationship(self, relationship_type: RelationshipType) -> str:
        """Get communication style based on relationship type"""
        styles = {
            RelationshipType.FRIENDSHIP: "casual and supportive",
            RelationshipType.MENTORSHIP: "guiding and patient",
            RelationshipType.RIVALRY: "competitive and challenging",
            RelationshipType.ROMANTIC: "intimate and vulnerable",
            RelationshipType.FAMILY: "familiar and caring",
            RelationshipType.PROFESSIONAL: "respectful and task-oriented",
            RelationshipType.ALLIANCE: "collaborative and strategic",
            RelationshipType.ANTAGONISTIC: "guarded and critical"
        }
        return styles.get(relationship_type, "neutral")

    def update_relationship(self, target_character_id: str, interaction_type: str,
                          impact: float):
        """Update relationship based on interaction"""
        if target_character_id in self.relationships:
            self.relationships[target_character_id].update_strength(impact, interaction_type)
            self.updated_at = datetime.now()

    def get_relationship_compatibility(self, other_character: 'LuciddreamerCharacter') -> float:
        """Calculate compatibility with another character"""
        if not hasattr(other_character, 'big_five'):
            return 0.5

        # Calculate Big Five compatibility
        bf_diff = 0
        for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
            diff = abs(getattr(self.big_five, trait) - getattr(other_character.big_five, trait))
            bf_diff += diff

        bf_compatibility = 1.0 - (bf_diff / 5.0)

        # Calculate archetype compatibility
        archetype_compatibility = self._get_archetype_compatibility(other_character.archetype)

        # Weighted combination
        overall_compatibility = (bf_compatibility * 0.6) + (archetype_compatibility * 0.4)

        return min(1.0, max(0.0, overall_compatibility))

    def _get_archetype_compatibility(self, other_archetype: CharacterArchetype) -> float:
        """Get archetype compatibility scores"""
        compatibility_matrix = {
            (CharacterArchetype.INNOVATOR, CharacterArchetype.ENGINEER): 0.9,
            (CharacterArchetype.ENGINEER, CharacterArchetype.INNOVATOR): 0.9,
            (CharacterArchetype.EDUCATOR, CharacterArchetype.EMPATH): 0.8,
            (CharacterArchetype.EMPATH, CharacterArchetype.EDUCATOR): 0.8,
            (CharacterArchetype.LEADER, CharacterArchetype.BUILDER): 0.85,
            (CharacterArchetype.BUILDER, CharacterArchetype.LEADER): 0.85,
            (CharacterArchetype.PHILOSOPHER, CharacterArchetype.ANALYST): 0.7,
            (CharacterArchetype.ANALYST, CharacterArchetype.PHILOSOPHER): 0.7,
            (CharacterArchetype.HUMORIST, CharacterArchetype.STORYTELLER): 0.9,
            (CharacterArchetype.STORYTELLER, CharacterArchetype.HUMORIST): 0.9,
            (CharacterArchetype.MORAL_GUIDE, CharacterArchetype.EMPATH): 0.85,
            (CharacterArchetype.EMPATH, CharacterArchetype.MORAL_GUIDE): 0.85,
        }

        return compatibility_matrix.get((self.archetype, other_archetype), 0.5)

    # ========================================================================
    # PERSONALITY GROWTH AND EVOLUTION
    # ========================================================================

    def experience_growth_event(self, growth_type: str, impact: float,
                              context: Dict[str, Any]):
        """Process a personality growth event"""
        growth_impacts = {
            'trauma': {'neuroticism': 0.1 * impact, 'openness': -0.05 * impact},
            'success': {'extraversion': 0.05 * impact, 'openness': 0.05 * impact},
            'relationship_ending': {'neuroticism': 0.15 * impact, 'agreeableness': -0.1 * impact},
            'new_relationship': {'extraversion': 0.1 * impact, 'agreeableness': 0.05 * impact},
            'failure': {'conscientiousness': 0.1 * impact, 'neuroticism': 0.05 * impact},
            'learning_experience': {'openness': 0.15 * impact, 'conscientiousness': 0.05 * impact},
            'leadership_experience': {'extraversion': 0.1 * impact, 'conscientiousness': 0.1 * impact},
            'isolation': {'extraversion': -0.1 * impact, 'openness': 0.05 * impact}
        }

        if growth_type in growth_impacts:
            impacts = growth_impacts[growth_type]

            # Apply impacts to Big Five traits
            for trait, change in impacts.items():
                if hasattr(self.big_five, trait):
                    current_value = getattr(self.big_five, trait)
                    new_value = max(0.0, min(1.0, current_value + change))
                    setattr(self.big_five, trait, new_value)

                    # Track growth
                    growth_key = f"{trait}_growth"
                    if growth_key in self.personality_growth_points:
                        self.personality_growth_points[growth_key] += abs(change)

            # Update voice profile based on personality changes
            self.voice_profile = self._generate_voice_profile()

            # Store growth event in memory if available
            if self.memory_system:
                memory_content = f"Experienced {growth_type} with {impact:.1%} impact"
                self.memory_system.add_episodic_memory(
                    content=memory_content,
                    summary=f"Personal growth: {growth_type}",
                    importance=min(1.0, impact),
                    emotional_valence=EmotionalValence.NEGATIVE if 'trauma' in growth_type or 'ending' in growth_type else EmotionalValence.POSITIVE,
                    tags={"personal_growth", growth_type}
                )

            self.updated_at = datetime.now()

    def get_growth_summary(self) -> Dict[str, Any]:
        """Get summary of character's growth and development"""
        return {
            'character_id': self.id,
            'character_name': self.name,
            'archetype': self.archetype.value,
            'current_personality': self.big_five.to_dict(),
            'growth_points': self.personality_growth_points,
            'total_dialogue_interactions': len(self.dialogue_history),
            'developed_skills': {name: skill.current_level for name, skill in self.skills.items()},
            'relationship_count': len(self.relationships),
            'emotional_state': self.current_emotional_state.to_dict(),
            'voice_profile': self.voice_profile,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    # ========================================================================
    # MEMORY SYSTEM INTEGRATION
    # ========================================================================

    def integrate_memory_system(self, memory_system: HierarchicalMemorySystem):
        """Integrate with Luciddreamer memory system"""
        self.memory_system = memory_system

        # Store character profile in semantic memory
        profile_data = {
            'name': self.name,
            'archetype': self.archetype.value,
            'big_five': self.big_five.to_dict(),
            'enneagram': self.enneagram.value,
            'mbti': self.mbti.value,
            'specializations': self.specializations
        }

        memory_system.add_semantic_concept(
            name=f"Character Profile: {self.name}",
            concept_type="entity",
            definition=f"{self.name} - {self.archetype.value}",
            attributes=profile_data
        )

        # Add skills to procedural memory
        for skill_name, skill in self.skills.items():
            skill_type = self._map_skill_to_memory_type(skill.category)
            memory_system.add_skill(
                name=skill_name,
                description=f"Skill in {skill.category}",
                skill_type=skill_type,
                difficulty=(10.0 - skill.current_level) / 10.0,
                innate_talent=skill.current_level / 10.0
            )

    def _map_skill_to_memory_type(self, category: str) -> SkillType:
        """Map skill category to memory system skill type"""
        mapping = {
            'creative': SkillType.CREATIVE,
            'social': SkillType.SOCIAL,
            'technical': SkillType.TECHNICAL,
            'analytical': SkillType.TECHNICAL,
            'leadership': SkillType.SOCIAL,
            'emotional': SkillType.SOCIAL,
            'communication': SkillType.SOCIAL,
            'philosophical': SkillType.CREATIVE,
            'humor': SkillType.SOCIAL
        }
        return mapping.get(category.lower(), SkillType.MOTOR)

    # ========================================================================
    # SERIALIZATION
    # ========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Convert character to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'archetype': self.archetype.value,
            'big_five': self.big_five.to_dict(),
            'enneagram': self.enneagram.value,
            'mbti': self.mbti.value,
            'current_emotional_state': self.current_emotional_state.to_dict(),
            'skills': {name: asdict(skill) for name, skill in self.skills.items()},
            'specializations': self.specializations,
            'relationships': {
                target_id: asdict(rel) for target_id, rel in self.relationships.items()
            },
            'voice_profile': self.voice_profile,
            'catchphrases': self.catchphrases,
            'personality_growth_points': self.personality_growth_points,
            'dialogue_history_count': len(self.dialogue_history),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LuciddreamerCharacter':
        """Create character from dictionary"""
        # Convert string enums back to enum values
        archetype_map = {arch.value: arch for arch in CharacterArchetype}
        enneagram_map = {etype.value: etype for etype in EnneagramType}
        mbti_map = {mtype.value: mtype for mtype in MBTIType}

        character = cls(
            name=data['name'],
            archetype=archetype_map[data['archetype']],
            big_five=BigFivePersonality.from_dict(data['big_five']),
            enneagram=enneagram_map[data['enneagram']],
            mbti=mbti_map[data['mbti']]
        )

        character.id = data['id']
        character.created_at = datetime.fromisoformat(data['created_at'])
        character.updated_at = datetime.fromisoformat(data['updated_at'])

        # Restore other attributes
        character.specializations = data.get('specializations', [])
        character.voice_profile = data.get('voice_profile', {})
        character.catchphrases = data.get('catchphrases', [])
        character.personality_growth_points = data.get('personality_growth_points', {})

        return character

# ============================================================================
# CHARACTER LIBRARY MANAGER
# ============================================================================

class CharacterLibraryManager:
    """Manager for character library and character interactions"""

    def __init__(self, storage_path: str = "./character_library"):
        self.storage_path = storage_path
        self.characters: Dict[str, LuciddreamerCharacter] = {}
        self.archetype_templates = self._initialize_archetype_templates()
        self._load_library()

    def _initialize_archetype_templates(self) -> Dict[CharacterArchetype, Dict[str, Any]]:
        """Initialize archetype templates with detailed configurations"""
        templates = {}

        # The Innovator - Dr. Aria Starweaver
        templates[CharacterArchetype.INNOVATOR] = {
            'name_template': "Dr. Aria Starweaver",
            'description': "Brilliantly intuitive yet methodically analytical, she approaches problems with both creative insight and rigorous methodology.",
            'core_motivation': "To discover fundamental truths and push the boundaries of human knowledge",
            'special_skills': ['creative_thinking', 'problem_solving', 'adaptability', 'vision', 'research_methodology'],
            'dialogue_patterns': ["Let's think about this from first principles", "What if we questioned our assumptions?", "The data suggests..."],
            'relationship_compatibility': [CharacterArchetype.ENGINEER, CharacterArchetype.EDUCATOR, CharacterArchetype.ANALYST]
        }

        # The Educator - Professor Julian Clockwork
        templates[CharacterArchetype.EDUCATOR] = {
            'name_template': "Professor Julian Clockwork",
            'description': "Passionate about making complex knowledge accessible and inspiring curiosity in others through patient, clear explanations.",
            'core_motivation': "To share knowledge and inspire the next generation of thinkers and innovators",
            'special_skills': ['teaching', 'communication', 'curriculum_design', 'mentoring', 'public_speaking'],
            'dialogue_patterns': ["Let me explain this step by step", "The key insight here is...", "Think about it like this..."],
            'relationship_compatibility': [CharacterArchetype.EMPATH, CharacterArchetype.STORYTELLER, CharacterArchetype.INNOVATOR]
        }

        # The Storyteller - Luna Riverbend
        templates[CharacterArchetype.STORYTELLER] = {
            'name_template': "Luna Riverbend",
            'description': "Wise and empathetic with a deep understanding of human nature, she uses narrative to heal, teach, and connect.",
            'core_motivation': "To preserve wisdom and help others find meaning through stories and shared human experience",
            'special_skills': ['narrative_craft', 'emotional_intelligence', 'memory', 'wisdom', 'cultural_understanding'],
            'dialogue_patterns': ["I remember a time when...", "The story goes that...", "Let me tell you about..."],
            'relationship_compatibility': [CharacterArchetype.EMPATH, CharacterArchetype.HUMORIST, CharacterArchetype.MORAL_GUIDE]
        }

        # The Creator - Marcus Forge
        templates[CharacterArchetype.CREATOR] = {
            'name_template': "Marcus Forge",
            'description': "Visionary and uncompromising in his pursuit of perfection, he combines aesthetic sensibility with functional innovation.",
            'core_motivation': "To bring beautiful, meaningful creations into existence that change how people experience the world",
            'special_skills': ['design_thinking', 'aesthetics', 'craftsmanship', 'vision', 'innovation'],
            'dialogue_patterns': ["Why are we doing this? Start there.", "It's not perfect yet.", "Form must serve function..."],
            'relationship_compatibility': [CharacterArchetype.ENGINEER, CharacterArchetype.INNOVATOR, CharacterArchetype.BUILDER]
        }

        # The Philosopher - Sage Clearwater
        templates[CharacterArchetype.PHILOSOPHER] = {
            'name_template': "Sage Clearwater",
            'description': "Calm and deeply thoughtful, he seeks fundamental truths and helps others find clarity through reason and reflection.",
            'core_motivation': "To understand the nature of reality and help others live more examined, meaningful lives",
            'special_skills': ['critical_thinking', 'logic', 'wisdom', 'meditation', 'ethical_reasoning'],
            'dialogue_patterns': ["The obstacle is the way.", "Question everything, including your questions.", "What is the essence?"],
            'relationship_compatibility': [CharacterArchetype.ANALYST, CharacterArchetype.MORAL_GUIDE, CharacterArchetype.EDUCATOR]
        }

        # The Analyst - Dr. Elena Pattern
        templates[CharacterArchetype.ANALYST] = {
            'name_template': "Dr. Elena Pattern",
            'description': "Rigorously analytical and intellectually courageous, she challenges assumptions and seeks truth through evidence and reason.",
            'core_motivation': "To uncover truth and hold power accountable through rigorous analysis and intellectual honesty",
            'special_skills': ['research', 'data_analysis', 'critical_thinking', 'attention_to_detail', 'logical_reasoning'],
            'dialogue_patterns': ["What evidence supports that claim?", "Let me check the data.", "Actually, that assumption is problematic..."],
            'relationship_compatibility': [CharacterArchetype.PHILOSOPHER, CharacterArchetype.INNOVATOR, CharacterArchetype.ENGINEER]
        }

        # The Leader - Captain Anya Stormrider
        templates[CharacterArchetype.LEADER] = {
            'name_template': "Captain Anya Stormrider",
            'description': "Charismatic and inclusive leader who brings out the best in others through inspiration, empathy, and strategic thinking.",
            'core_motivation': "To unite diverse people around shared goals and bring about positive change through collective action",
            'special_skills': ['leadership', 'diplomacy', 'strategy', 'inspiration', 'conflict_resolution'],
            'dialogue_patterns': ["Our shared humanity is more important than our differences.", "Trust the process.", "We're in this together."],
            'relationship_compatibility': [CharacterArchetype.BUILDER, CharacterArchetype.EMPATH, CharacterArchetype.MORAL_GUIDE]
        }

        # The Moral Guide - Minister Thomas Bridge
        templates[CharacterArchetype.MORAL_GUIDE] = {
            'name_template': "Minister Thomas Bridge",
            'description': "Principled and compassionate moral leader who guides others with wisdom, love, and unwavering ethical commitment.",
            'core_motivation': "To help others live more ethical, meaningful lives and create a more just world",
            'special_skills': ['moral_reasoning', 'empathy', 'wisdom', 'counseling', 'inspirational_speaking'],
            'dialogue_patterns': ["Hate cannot drive out hate, only love can do that.", "We must do what's right, not what's easy.", "The moral arc..."],
            'relationship_compatibility': [CharacterArchetype.EMPATH, CharacterArchetype.LEADER, CharacterArchetype.STORYTELLER]
        }

        # The Humorist - Jasper Nightingale
        templates[CharacterArchetype.HUMORIST] = {
            'name_template': "Jasper Nightingale",
            'description': "Quick-witted and deeply empathetic, he uses humor to heal, connect, and provide insight into the human condition.",
            'core_motivation': "To help others find joy and perspective through laughter and shared humanity",
            'special_skills': ['wit', 'social_intelligence', 'timing', 'improvisation', 'emotional_insight'],
            'dialogue_patterns': ["Laughter is the shortest distance between two people.", "Well, well, well...", "That's funny because..."],
            'relationship_compatibility': [CharacterArchetype.STORYTELLER, CharacterArchetype.EMPATH, CharacterArchetype.EDUCATOR]
        }

        # The Empath - Celeste Harmonia
        templates[CharacterArchetype.EMPATH] = {
            'name_template': "Celeste Harmonia",
            'description': "Deeply compassionate and emotionally intelligent, she creates safe spaces for vulnerability and authentic connection.",
            'core_motivation': "To help others feel seen, heard, and understood through deep empathetic connection",
            'special_skills': ['empathy', 'listening', 'emotional_support', 'intuition', 'conflict_mediation'],
            'dialogue_patterns': ["How does that make you feel?", "I hear you, and what you're feeling is valid.", "Tell me more about..."],
            'relationship_compatibility': [CharacterArchetype.MORAL_GUIDE, CharacterArchetype.EDUCATOR, CharacterArchetype.LEADER]
        }

        # The Builder - Catherine Foundation
        templates[CharacterArchetype.BUILDER] = {
            'name_template': "Catherine Foundation",
            'description': "Resilient and practical visionary who builds lasting institutions and empowers others to create sustainable success.",
            'core_motivation': "To build enduring structures that uplift communities and create opportunities for others",
            'special_skills': ['planning', 'execution', 'resource_management', 'resilience', 'mentorship'],
            'dialogue_patterns': ["Build your dreams before someone else hires you to build theirs.", "Foundation first.", "One step at a time."],
            'relationship_compatibility': [CharacterArchetype.LEADER, CharacterArchetype.ENGINEER, CharacterArchetype.CREATOR]
        }

        # The Engineer - Engineer Maxwell Gear
        templates[CharacterArchetype.ENGINEER] = {
            'name_template': "Engineer Maxwell Gear",
            'description': "Brilliant systems thinker who combines technical expertise with innovative problem-solving and boundless energy.",
            'core_motivation': "To solve complex technical challenges and build innovative systems that push boundaries",
            'special_skills': ['system_design', 'problem_solving', 'innovation', 'execution', 'technical_leadership'],
            'dialogue_patterns': ["If something's important enough, we should try.", "Let's prototype it.", "How does it work?"],
            'relationship_compatibility': [CharacterArchetype.INNOVATOR, CharacterArchetype.BUILDER, CharacterArchetype.CREATOR]
        }

        return templates

    def create_character(self, archetype: CharacterArchetype,
                        custom_name: Optional[str] = None,
                        custom_personality: Optional[BigFivePersonality] = None) -> LuciddreamerCharacter:
        """Create a new character based on archetype"""
        template = self.archetype_templates[archetype]
        name = custom_name or template['name_template']

        character = LuciddreamerCharacter(
            name=name,
            archetype=archetype,
            big_five=custom_personality
        )

        # Apply template enhancements
        character.specializations = template['special_skills']

        self.characters[character.id] = character
        self._save_character(character)

        logger.info(f"Created character: {character.name} ({archetype.value})")
        return character

    def get_character(self, character_id: str) -> Optional[LuciddreamerCharacter]:
        """Get character by ID"""
        return self.characters.get(character_id)

    def get_characters_by_archetype(self, archetype: CharacterArchetype) -> List[LuciddreamerCharacter]:
        """Get all characters of a specific archetype"""
        return [char for char in self.characters.values() if char.archetype == archetype]

    def create_character_interaction(self, character1_id: str, character2_id: str,
                                   context: Dict[str, Any]) -> Dict[str, str]:
        """Create interaction between two characters"""
        char1 = self.get_character(character1_id)
        char2 = self.get_character(character2_id)

        if not char1 or not char2:
            return {"error": "One or both characters not found"}

        # Generate dialogue for both characters
        context['other_character'] = char2.name
        response1 = char1.generate_dialogue(context)

        context['other_character'] = char1.name
        response2 = char2.generate_dialogue(context)

        # Update relationships
        compatibility = char1.get_relationship_compatibility(char2)
        if character2_id not in char1.relationships:
            char1.add_relationship(character2_id, RelationshipType.FRIENDSHIP, compatibility)

        if character1_id not in char2.relationships:
            char2.add_relationship(character1_id, RelationshipType.FRIENDSHIP, compatibility)

        # Update relationship strength based on interaction
        interaction_impact = 0.01 if compatibility > 0.7 else -0.005
        char1.update_relationship(character2_id, f"dialogue exchange", interaction_impact)
        char2.update_relationship(character1_id, f"dialogue exchange", interaction_impact)

        return {
            'character1_name': char1.name,
            'character1_response': response1,
            'character2_name': char2.name,
            'character2_response': response2,
            'compatibility': f"{compatibility:.2%}"
        }

    def get_archetype_combinations(self) -> List[Dict[str, Any]]:
        """Get recommended archetype combinations for various scenarios"""
        combinations = [
            {
                'scenario': 'Innovation Team',
                'archetypes': [CharacterArchetype.INNOVATOR, CharacterArchetype.CREATOR, CharacterArchetype.ENGINEER],
                'description': 'Breakthrough innovation and creative problem-solving'
            },
            {
                'scenario': 'Education Program',
                'archetypes': [CharacterArchetype.EDUCATOR, CharacterArchetype.EMPATH, CharacterArchetype.STORYTELLER],
                'description': 'Comprehensive learning and personal development'
            },
            {
                'scenario': 'Leadership Council',
                'archetypes': [CharacterArchetype.LEADER, CharacterArchetype.MORAL_GUIDE, CharacterArchetype.BUILDER],
                'description': 'Strategic leadership with ethical foundation'
            },
            {
                'scenario': 'Crisis Response',
                'archetypes': [CharacterArchetype.LEADER, CharacterArchetype.ANALYST, CharacterArchetype.EMPATH],
                'description': 'Calm crisis management with analytical rigor'
            },
            {
                'scenario': 'Creative Workshop',
                'archetypes': [CharacterArchetype.CREATOR, CharacterArchetype.STORYTELLER, CharacterArchetype.HUMORIST],
                'description': 'Creative exploration with narrative and humor'
            }
        ]

        return combinations

    def _load_library(self):
        """Load character library from storage"""
        # Implementation would load from JSON/database
        pass

    def _save_character(self, character: LuciddreamerCharacter):
        """Save character to storage"""
        # Implementation would save to JSON/database
        pass

    def get_library_statistics(self) -> Dict[str, Any]:
        """Get library statistics"""
        archetype_counts = {}
        for character in self.characters.values():
            archetype_name = character.archetype.value
            archetype_counts[archetype_name] = archetype_counts.get(archetype_name, 0) + 1

        return {
            'total_characters': len(self.characters),
            'archetype_distribution': archetype_counts,
            'average_relationship_count': sum(len(char.relationships) for char in self.characters.values()) / max(1, len(self.characters)),
            'total_skills_developed': sum(len(char.skills) for char in self.characters.values())
        }

# ============================================================================
# EXAMPLE USAGE AND DEMONSTRATION
# ============================================================================

if __name__ == "__main__":
    async def main():
        """Demonstrate the character library system"""
        print("Luciddreamer Character Library Integration and Personality Modeling")
        print("=" * 70)

        # Initialize character library
        library = CharacterLibraryManager()

        # Create sample characters from different archetypes
        print("\nCreating Characters...")

        # Create the Innovator
        aria = library.create_character(CharacterArchetype.INNOVATOR)
        print(f"✓ Created: {aria.name} - {aria.archetype.value}")

        # Create the Educator
        julian = library.create_character(CharacterArchetype.EDUCATOR)
        print(f"✓ Created: {julian.name} - {julian.archetype.value}")

        # Create the Empath
        celeste = library.create_character(CharacterArchetype.EMPATH)
        print(f"✓ Created: {celeste.name} - {celeste.archetype.value}")

        # Create the Engineer
        maxwell = library.create_character(CharacterArchetype.ENGINEER)
        print(f"✓ Created: {maxwell.name} - {maxwell.archetype.value}")

        # Display personality profiles
        print("\nPersonality Profiles:")
        print(f"\n{aria.name} (Innovator):")
        print(f"  Big Five: {aria.big_five.to_dict()}")
        print(f"  Enneagram: {aria.enneagram.value}")
        print(f"  MBTI: {aria.mbti.value}")
        print(f"  Core Skills: {', '.join(aria.specializations)}")

        # Demonstrate dialogue generation
        print("\nDialogue Generation Examples:")

        contexts = [
            {'situation': 'problem_solving', 'topic': 'developing a new AI system'},
            {'situation': 'social_interaction', 'topic': 'meeting for the first time'},
            {'situation': 'teaching', 'topic': 'explaining a complex concept'}
        ]

        for i, context in enumerate(contexts, 1):
            print(f"\nScenario {i}: {context['situation']} - {context['topic']}")
            print(f"{aria.name}: '{aria.generate_dialogue(context)}'")
            print(f"{julian.name}: '{julian.generate_dialogue(context)}'")
            print(f"{celeste.name}: '{celeste.generate_dialogue(context)}'")
            print(f"{maxwell.name}: '{maxwell.generate_dialogue(context)}'")

        # Demonstrate emotional modeling
        print("\nEmotional Modeling:")

        aria.update_emotional_state("breakthrough discovery", BasicEmotion.JOY, 0.8)
        print(f"{aria.name} is feeling {aria.current_emotional_state.primary_emotion.value} with intensity {aria.current_emotional_state.intensity:.1%}")
        print(f"Visible cues: {', '.join(aria.current_emotional_state.visible_cues)}")

        celeste.update_emotional_state("hears about someone's struggle", BasicEmotion.TRUST, 0.6)
        print(f"{celeste.name} is feeling {celeste.current_emotional_state.primary_emotion.value} with intensity {celeste.current_emotional_state.intensity:.1%}")

        # Demonstrate skill development
        print("\nSkill Development:")

        aria.practice_skill("creative_thinking", 0.8, 0.9, 120)  # 2 hours of practice
        print(f"{aria.name} practiced creative thinking - new level: {aria.get_skill_level('creative_thinking'):.1f}")

        maxwell.practice_skill("system_design", 0.9, 0.8, 180)  # 3 hours of practice
        print(f"{maxwell.name} practiced system_design - new level: {maxwell.get_skill_level('system_design'):.1f}")

        # Demonstrate relationship dynamics
        print("\nRelationship Dynamics:")

        compatibility = aria.get_relationship_compatibility(maxwell)
        print(f"Compatibility between {aria.name} and {maxwell.name}: {compatibility:.1%}")

        # Create interaction
        interaction = library.create_character_interaction(
            aria.id, maxwell.id,
            {'situation': 'collaboration', 'topic': 'designing an innovative system'}
        )

        print("\nCharacter Interaction:")
        print(f"{interaction['character1_name']}: {interaction['character1_response']}")
        print(f"{interaction['character2_name']}: {interaction['character2_response']}")
        print(f"Compatibility: {interaction['compatibility']}")

        # Demonstrate personality growth
        print("\nPersonality Growth:")

        aria.experience_growth_event("major_success", 0.8, {"project": "AI breakthrough", "recognition": "international"})
        print(f"{aria.name} experienced major success - personality traits adjusted")
        print(f"New openness level: {aria.big_five.openness:.2f}")
        print(f"New extraversion level: {aria.big_five.extraversion:.2f}")

        # Display library statistics
        print("\nLibrary Statistics:")
        stats = library.get_library_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # Show recommended combinations
        print("\nRecommended Character Combinations:")
        combinations = library.get_archetype_combinations()
        for combo in combinations:
            print(f"\n{combo['scenario']}:")
            print(f"  Archetypes: {', '.join([arch.value for arch in combo['archetypes']])}")
            print(f"  Purpose: {combo['description']}")

        # Integration with memory system demonstration
        print("\nMemory System Integration:")
        print("Characters can be integrated with Luciddreamer's hierarchical memory system")
        print("- Skills stored in procedural memory")
        print("- Personality profiles in semantic memory")
        print("- Interactions in episodic memory")
        print("- Emotional states influence memory consolidation")

        print("\n" + "=" * 70)
        print("Character Library Integration Demo Completed!")
        print("All systems are ready for integration with Luciddreamer agents.")

    # Run demonstration
    asyncio.run(main())