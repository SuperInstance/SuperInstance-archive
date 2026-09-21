"""
Virtual Mentor Character System for Interactive Tutorials

This module provides comprehensive virtual mentor characters with distinct
personalities, adaptive guidance, emotional intelligence, and personalized
learning support for immersive educational experiences.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import json
import sqlite3
from pathlib import Path
import random
import math


class MentorPersonality(Enum):
    """Different mentor personality types"""
    WISE_SAGE = "wise_sage"
    ENCOURAGING_COACH = "encouraging_coach"
    PATIENT_TEACHER = "patient_teacher"
    BRILLIANT_SCIENTIST = "brilliant_scientist"
    CREATIVE_ARTIST = "creative_artist"
    PRACTICAL_ENGINEER = "practical_engineer"
    FRIENDLY_COMPANION = "friendly_companion"
    STRICT_INSTRUCTOR = "strict_instructor"


class MentorMood(Enum):
    """Current mood states of mentors"""
    EXCITED = "excited"
    CALM = "calm"
    THOUGHTFUL = "thoughtful"
    PROUD = "proud"
    CONCERNED = "concerned"
    ENCOURAGING = "encouraging"
    FOCUSED = "focused"
    PLAYFUL = "playful"


class InteractionType(Enum):
    """Types of mentor interactions"""
    GREETING = "greeting"
    GUIDANCE = "guidance"
    ENCOURAGEMENT = "encouragement"
    EXPLANATION = "explanation"
    FEEDBACK = "feedback"
    CELEBRATION = "celebration"
    CORRECTION = "correction"
    HINT = "hint"
    MOTIVATION = "motivation"
    FAREWELL = "farewell"


class LearningContext(Enum):
    """Learning contexts for adaptive responses"""
    FIRST_TIME = "first_time"
    STRUGGLING = "struggling"
    PROGRESSING = "progressing"
    MASTERING = "mastering"
    REVIEWING = "reviewing"
    EXPLORING = "exploring"
    CHALLENGING = "challenging"
    CELEBRATING = "celebrating"


@dataclass
class MentorCharacter:
    """Definition of a virtual mentor character"""
    mentor_id: str
    name: str
    personality: MentorPersonality
    description: str
    backstory: str
    expertise_areas: List[str]
    appearance: Dict[str, Any] = field(default_factory=dict)
    voice_profile: Dict[str, Any] = field(default_factory=dict)
    personality_traits: Dict[str, float] = field(default_factory=dict)  # 0-1 scale
    interaction_style: Dict[str, str] = field(default_factory=dict)
    catchphrases: List[str] = field(default_factory=list)
    favorite_topics: List[str] = field(default_factory=list)


@dataclass
class MentorState:
    """Current state of a mentor"""
    mentor_id: str
    user_id: str
    current_mood: MentorMood
    energy_level: float  # 0-1 scale
    relationship_level: float  # 0-1 scale with user
    recent_interactions: List[str] = field(default_factory=list)
    current_focus: Optional[str] = None
    last_interaction: Optional[datetime] = None
    session_duration: float = 0.0
    topics_discussed: List[str] = field(default_factory=list)


@dataclass
class MentorMessage:
    """Message from a mentor to user"""
    mentor_id: str
    user_id: str
    interaction_type: InteractionType
    content: str
    context: LearningContext
    mood: MentorMood
    timestamp: datetime = field(default_factory=datetime.now)
    personalization_data: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[str] = field(default_factory=list)
    emotional_tone: Dict[str, float] = field(default_factory=dict)


@dataclass
class UserMentorRelationship:
    """Relationship between user and mentor"""
    user_id: str
    mentor_id: str
    bond_strength: float = 0.0  # 0-1 scale
    trust_level: float = 0.0    # 0-1 scale
    interaction_count: int = 0
    total_time_together: float = 0.0
    shared_achievements: List[str] = field(default_factory=list)
    memorable_moments: List[Dict[str, Any]] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    last_interaction: Optional[datetime] = None


class MentorPersonalityEngine:
    """Generates personality-specific responses and behaviors"""
    
    def __init__(self):
        self.personality_templates = self._create_personality_templates()
        self.response_patterns = self._create_response_patterns()
    
    def _create_personality_templates(self) -> Dict[MentorPersonality, Dict[str, Any]]:
        """Create personality templates with traits and behaviors"""
        return {
            MentorPersonality.WISE_SAGE: {
                "traits": {
                    "wisdom": 0.95,
                    "patience": 0.9,
                    "encouragement": 0.8,
                    "formality": 0.7,
                    "playfulness": 0.3
                },
                "speech_patterns": {
                    "uses_metaphors": True,
                    "philosophical": True,
                    "measured_pace": True,
                    "ancient_wisdom": True
                },
                "catchphrases": [
                    "As the ancient saying goes...",
                    "In my many years of teaching...",
                    "Patience, young learner...",
                    "True wisdom comes from understanding...",
                    "Let me share something I've learned..."
                ],
                "preferred_contexts": [LearningContext.FIRST_TIME, LearningContext.STRUGGLING, LearningContext.REVIEWING]
            },
            
            MentorPersonality.ENCOURAGING_COACH: {
                "traits": {
                    "enthusiasm": 0.9,
                    "encouragement": 0.95,
                    "energy": 0.85,
                    "supportiveness": 0.9,
                    "directness": 0.7
                },
                "speech_patterns": {
                    "exclamation_marks": True,
                    "motivational": True,
                    "sports_metaphors": True,
                    "positive_reinforcement": True
                },
                "catchphrases": [
                    "You've got this!",
                    "That's the spirit!",
                    "Great job, keep pushing!",
                    "I believe in you!",
                    "Let's tackle this together!"
                ],
                "preferred_contexts": [LearningContext.STRUGGLING, LearningContext.CHALLENGING, LearningContext.CELEBRATING]
            },
            
            MentorPersonality.PATIENT_TEACHER: {
                "traits": {
                    "patience": 0.95,
                    "clarity": 0.9,
                    "supportiveness": 0.85,
                    "organization": 0.8,
                    "gentleness": 0.9
                },
                "speech_patterns": {
                    "step_by_step": True,
                    "clear_explanations": True,
                    "reassuring_tone": True,
                    "educational_structure": True
                },
                "catchphrases": [
                    "Let's break this down step by step...",
                    "Don't worry, we'll figure this out together...",
                    "Take your time, there's no rush...",
                    "Everyone learns at their own pace...",
                    "Let's try a different approach..."
                ],
                "preferred_contexts": [LearningContext.FIRST_TIME, LearningContext.STRUGGLING, LearningContext.PROGRESSING]
            },
            
            MentorPersonality.BRILLIANT_SCIENTIST: {
                "traits": {
                    "intelligence": 0.95,
                    "curiosity": 0.9,
                    "precision": 0.85,
                    "analytical": 0.9,
                    "excitement_for_discovery": 0.8
                },
                "speech_patterns": {
                    "technical_terms": True,
                    "hypothesis_driven": True,
                    "evidence_based": True,
                    "experimental_approach": True
                },
                "catchphrases": [
                    "Fascinating! Let's investigate...",
                    "The data suggests...",
                    "Let's form a hypothesis...",
                    "I observe an interesting pattern...",
                    "This reminds me of a principle..."
                ],
                "preferred_contexts": [LearningContext.EXPLORING, LearningContext.MASTERING, LearningContext.CHALLENGING]
            },
            
            MentorPersonality.CREATIVE_ARTIST: {
                "traits": {
                    "creativity": 0.95,
                    "inspiration": 0.9,
                    "emotional_expression": 0.85,
                    "intuition": 0.8,
                    "playfulness": 0.7
                },
                "speech_patterns": {
                    "metaphorical": True,
                    "colorful_language": True,
                    "emotional": True,
                    "imaginative": True
                },
                "catchphrases": [
                    "Let your imagination soar!",
                    "I see a beautiful pattern emerging...",
                    "Art is about expressing your unique vision...",
                    "Let's paint outside the lines...",
                    "What story does this tell you?"
                ],
                "preferred_contexts": [LearningContext.EXPLORING, LearningContext.CELEBRATING, LearningContext.PROGRESSING]
            },
            
            MentorPersonality.PRACTICAL_ENGINEER: {
                "traits": {
                    "pragmatism": 0.9,
                    "problem_solving": 0.95,
                    "efficiency": 0.85,
                    "systematic": 0.8,
                    "reliability": 0.9
                },
                "speech_patterns": {
                    "solution_focused": True,
                    "practical_examples": True,
                    "systematic_approach": True,
                    "engineering_metaphors": True
                },
                "catchphrases": [
                    "Let's solve this problem efficiently...",
                    "What's the most practical approach?",
                    "Every problem has a solution...",
                    "Let's build this step by step...",
                    "Think like an engineer..."
                ],
                "preferred_contexts": [LearningContext.CHALLENGING, LearningContext.PROGRESSING, LearningContext.MASTERING]
            }
        }
    
    def _create_response_patterns(self) -> Dict[InteractionType, Dict[MentorPersonality, List[str]]]:
        """Create response patterns for different interaction types and personalities"""
        return {
            InteractionType.GREETING: {
                MentorPersonality.WISE_SAGE: [
                    "Welcome, young seeker of knowledge. I am here to guide you on your journey.",
                    "Ah, another eager mind arrives. Let us explore the depths of learning together.",
                    "Greetings, student. Today we embark on a path of discovery."
                ],
                MentorPersonality.ENCOURAGING_COACH: [
                    "Hey there, superstar! Ready to crush some goals today?",
                    "Welcome to the learning arena! I'm here to cheer you on!",
                    "Let's go, champion! Time to unlock your potential!"
                ],
                MentorPersonality.PATIENT_TEACHER: [
                    "Hello there! I'm so glad you're here. We'll take this journey together at your pace.",
                    "Welcome! Don't worry about anything - we're going to learn step by step.",
                    "Hi! I'm here to help you understand everything clearly and thoroughly."
                ]
            },
            
            InteractionType.ENCOURAGEMENT: {
                MentorPersonality.WISE_SAGE: [
                    "Remember, every master was once a beginner. Trust in the process.",
                    "Your dedication will bear fruit. Continue with patience and purpose.",
                    "The path of learning requires persistence. You are walking it well."
                ],
                MentorPersonality.ENCOURAGING_COACH: [
                    "You're doing amazing! Keep that momentum going!",
                    "I can see you getting stronger with every step! Don't stop now!",
                    "That's the attitude of a winner! Push through, you've got this!"
                ],
                MentorPersonality.PATIENT_TEACHER: [
                    "You're making wonderful progress. I'm proud of how hard you're working.",
                    "Don't worry about the pace - you're learning exactly as you should.",
                    "Every small step forward is an achievement. Keep going!"
                ]
            }
        }
    
    def generate_response(self, personality: MentorPersonality, interaction_type: InteractionType,
                         context: LearningContext, user_data: Dict[str, Any]) -> str:
        """Generate a personality-appropriate response"""
        # Get personality template
        template = self.personality_templates.get(personality, {})
        
        # Get base responses for this interaction type and personality
        base_responses = self.response_patterns.get(interaction_type, {}).get(personality, [])
        
        if not base_responses:
            return self._generate_fallback_response(interaction_type, context)
        
        # Select and customize response
        base_response = random.choice(base_responses)
        return self._personalize_response(base_response, personality, context, user_data)
    
    def _personalize_response(self, base_response: str, personality: MentorPersonality,
                            context: LearningContext, user_data: Dict[str, Any]) -> str:
        """Personalize response based on user data and context"""
        response = base_response
        
        # Add user name if available
        if "user_name" in user_data:
            response = response.replace("student", user_data["user_name"])
            response = response.replace("young seeker", user_data["user_name"])
        
        # Add context-specific modifications
        if context == LearningContext.STRUGGLING:
            if personality == MentorPersonality.PATIENT_TEACHER:
                response += " Remember, struggling is part of learning."
        elif context == LearningContext.CELEBRATING:
            response += " This is a moment to be proud of!"
        
        return response
    
    def _generate_fallback_response(self, interaction_type: InteractionType, 
                                  context: LearningContext) -> str:
        """Generate fallback response when no specific pattern exists"""
        fallbacks = {
            InteractionType.GREETING: "Hello! I'm here to help you learn.",
            InteractionType.ENCOURAGEMENT: "You're doing great! Keep it up!",
            InteractionType.GUIDANCE: "Let me help guide you through this.",
            InteractionType.EXPLANATION: "Let me explain this concept to you.",
            InteractionType.FEEDBACK: "Here's some feedback on your progress."
        }
        return fallbacks.get(interaction_type, "I'm here to support your learning journey.")


class AdaptiveResponseEngine:
    """Generates adaptive responses based on user progress and behavior"""
    
    def __init__(self):
        self.response_history: Dict[str, List[str]] = {}
        self.effectiveness_scores: Dict[str, float] = {}
    
    def generate_adaptive_response(self, mentor: MentorCharacter, state: MentorState,
                                 context: LearningContext, user_progress: Dict[str, Any],
                                 relationship: UserMentorRelationship) -> MentorMessage:
        """Generate an adaptive response based on multiple factors"""
        # Determine interaction type based on context
        interaction_type = self._determine_interaction_type(context, user_progress, relationship)
        
        # Adjust mood based on user progress and relationship
        adjusted_mood = self._adjust_mood_for_context(state.current_mood, context, user_progress)
        
        # Generate base content
        personality_engine = MentorPersonalityEngine()
        base_content = personality_engine.generate_response(
            mentor.personality, interaction_type, context, user_progress
        )
        
        # Apply adaptations based on relationship
        adapted_content = self._apply_relationship_adaptations(
            base_content, mentor, relationship, user_progress
        )
        
        # Add emotional intelligence
        final_content = self._apply_emotional_intelligence(
            adapted_content, mentor, state, context, user_progress
        )
        
        # Generate suggested actions
        suggested_actions = self._generate_suggested_actions(context, user_progress, mentor)
        
        # Calculate emotional tone
        emotional_tone = self._calculate_emotional_tone(mentor, adjusted_mood, context)
        
        return MentorMessage(
            mentor_id=mentor.mentor_id,
            user_id=state.user_id,
            interaction_type=interaction_type,
            content=final_content,
            context=context,
            mood=adjusted_mood,
            personalization_data={
                "relationship_level": relationship.bond_strength,
                "user_progress": user_progress,
                "mentor_personality": mentor.personality.value
            },
            suggested_actions=suggested_actions,
            emotional_tone=emotional_tone
        )
    
    def _determine_interaction_type(self, context: LearningContext, 
                                  user_progress: Dict[str, Any],
                                  relationship: UserMentorRelationship) -> InteractionType:
        """Determine appropriate interaction type"""
        # Check if this is first interaction
        if relationship.interaction_count == 0:
            return InteractionType.GREETING
        
        # Based on context
        context_to_interaction = {
            LearningContext.FIRST_TIME: InteractionType.GUIDANCE,
            LearningContext.STRUGGLING: InteractionType.ENCOURAGEMENT,
            LearningContext.PROGRESSING: InteractionType.FEEDBACK,
            LearningContext.MASTERING: InteractionType.CELEBRATION,
            LearningContext.CELEBRATING: InteractionType.CELEBRATION,
            LearningContext.REVIEWING: InteractionType.GUIDANCE,
            LearningContext.EXPLORING: InteractionType.GUIDANCE,
            LearningContext.CHALLENGING: InteractionType.MOTIVATION
        }
        
        return context_to_interaction.get(context, InteractionType.GUIDANCE)
    
    def _adjust_mood_for_context(self, current_mood: MentorMood, context: LearningContext,
                               user_progress: Dict[str, Any]) -> MentorMood:
        """Adjust mentor mood based on context and user progress"""
        # If user is struggling, become more encouraging
        if context == LearningContext.STRUGGLING:
            return MentorMood.ENCOURAGING
        
        # If user is celebrating, become excited
        if context == LearningContext.CELEBRATING:
            return MentorMood.EXCITED
        
        # If user is mastering, become proud
        if context == LearningContext.MASTERING:
            return MentorMood.PROUD
        
        # Otherwise, maintain current mood or default to calm
        return current_mood if current_mood else MentorMood.CALM
    
    def _apply_relationship_adaptations(self, content: str, mentor: MentorCharacter,
                                      relationship: UserMentorRelationship,
                                      user_progress: Dict[str, Any]) -> str:
        """Adapt content based on user-mentor relationship"""
        # Higher bond strength = more personal and familiar tone
        if relationship.bond_strength > 0.7:
            # Add more personal touches
            if "you" in content.lower():
                content = content.replace("you", "you, my friend")
            content += " I'm proud to be your mentor."
        
        # Reference shared achievements
        if relationship.shared_achievements:
            recent_achievement = relationship.shared_achievements[-1]
            content += f" Remember when we celebrated your {recent_achievement}? You've grown so much!"
        
        return content
    
    def _apply_emotional_intelligence(self, content: str, mentor: MentorCharacter,
                                    state: MentorState, context: LearningContext,
                                    user_progress: Dict[str, Any]) -> str:
        """Apply emotional intelligence to adapt the message"""
        # Detect if user might be frustrated
        if user_progress.get("recent_mistakes", 0) > 3:
            content = "I can sense this might be frustrating. " + content
            content += " Take a deep breath - we'll work through this together."
        
        # Add energy based on mentor's energy level
        if state.energy_level > 0.8:
            content = content.replace(".", "!")
            content += " I'm excited to help you succeed!"
        elif state.energy_level < 0.3:
            content = content.replace("!", ".")
            content += " Let's take this at a comfortable pace."
        
        return content
    
    def _generate_suggested_actions(self, context: LearningContext, 
                                  user_progress: Dict[str, Any],
                                  mentor: MentorCharacter) -> List[str]:
        """Generate suggested actions for the user"""
        actions = []
        
        if context == LearningContext.STRUGGLING:
            actions.extend([
                "Take a short break and come back refreshed",
                "Review the foundational concepts",
                "Try a different learning approach",
                "Ask me for hints or explanations"
            ])
        elif context == LearningContext.PROGRESSING:
            actions.extend([
                "Continue with the current approach",
                "Try a more challenging exercise",
                "Explore related topics",
                "Practice what you've learned"
            ])
        elif context == LearningContext.MASTERING:
            actions.extend([
                "Move on to advanced topics",
                "Help teach others",
                "Apply knowledge to real projects",
                "Celebrate your achievement!"
            ])
        
        return actions[:3]  # Limit to top 3 suggestions
    
    def _calculate_emotional_tone(self, mentor: MentorCharacter, mood: MentorMood,
                                context: LearningContext) -> Dict[str, float]:
        """Calculate emotional tone values"""
        # Base tone from personality
        base_tone = {
            "warmth": mentor.personality_traits.get("supportiveness", 0.5),
            "enthusiasm": mentor.personality_traits.get("enthusiasm", 0.5),
            "confidence": mentor.personality_traits.get("intelligence", 0.5),
            "patience": mentor.personality_traits.get("patience", 0.5)
        }
        
        # Adjust based on mood
        mood_adjustments = {
            MentorMood.EXCITED: {"enthusiasm": 0.9, "warmth": 0.8},
            MentorMood.ENCOURAGING: {"warmth": 0.9, "enthusiasm": 0.7},
            MentorMood.CALM: {"patience": 0.9, "confidence": 0.7},
            MentorMood.PROUD: {"warmth": 0.8, "confidence": 0.8}
        }
        
        if mood in mood_adjustments:
            for tone_key, value in mood_adjustments[mood].items():
                base_tone[tone_key] = max(base_tone[tone_key], value)
        
        return base_tone


class MentorSystem:
    """Main virtual mentor management system"""
    
    def __init__(self, db_path: str = "virtual_mentors.db"):
        self.db_path = Path(db_path)
        self.mentors: Dict[str, MentorCharacter] = {}
        self.mentor_states: Dict[str, MentorState] = {}
        self.response_engine = AdaptiveResponseEngine()
        self.init_database()
        self.create_default_mentors()
    
    def init_database(self):
        """Initialize virtual mentor database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mentor_states (
                    mentor_id TEXT,
                    user_id TEXT,
                    current_mood TEXT,
                    energy_level REAL,
                    relationship_level REAL,
                    recent_interactions TEXT,
                    last_interaction DATETIME,
                    session_duration REAL,
                    topics_discussed TEXT,
                    PRIMARY KEY (mentor_id, user_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_mentor_relationships (
                    user_id TEXT,
                    mentor_id TEXT,
                    bond_strength REAL,
                    trust_level REAL,
                    interaction_count INTEGER,
                    total_time_together REAL,
                    shared_achievements TEXT,
                    memorable_moments TEXT,
                    preferences TEXT,
                    last_interaction DATETIME,
                    PRIMARY KEY (user_id, mentor_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mentor_interactions (
                    id INTEGER PRIMARY KEY,
                    mentor_id TEXT,
                    user_id TEXT,
                    interaction_type TEXT,
                    content TEXT,
                    context TEXT,
                    timestamp DATETIME,
                    user_response TEXT,
                    effectiveness_score REAL
                )
            """)
    
    def create_default_mentors(self):
        """Create the default set of virtual mentors"""
        # Wise Sage - Confucius-inspired
        sage = MentorCharacter(
            mentor_id="wise_sage",
            name="Master Chen",
            personality=MentorPersonality.WISE_SAGE,
            description="An ancient scholar with profound wisdom and patience",
            backstory="Master Chen has spent centuries studying the art of learning and teaching. His wisdom comes from observing countless students find their path to knowledge.",
            expertise_areas=["philosophy", "learning_strategies", "wisdom", "reflection"],
            appearance={
                "age": "elderly",
                "clothing": "traditional_robes",
                "hair": "long_white_beard",
                "eyes": "kind_and_knowing"
            },
            voice_profile={
                "tone": "calm_and_measured",
                "pace": "slow_and_thoughtful",
                "accent": "slight_ancient_wisdom"
            },
            personality_traits={
                "wisdom": 0.95,
                "patience": 0.9,
                "encouragement": 0.8,
                "playfulness": 0.3
            },
            catchphrases=[
                "The journey of a thousand miles begins with a single step",
                "In learning, you are never too old or too young",
                "Wisdom is not just knowing, but understanding"
            ]
        )
        self.add_mentor(sage)
        
        # Encouraging Coach - Sports coach inspired
        coach = MentorCharacter(
            mentor_id="encouraging_coach",
            name="Coach Rivera",
            personality=MentorPersonality.ENCOURAGING_COACH,
            description="An energetic mentor who treats learning like athletic training",
            backstory="Coach Rivera was an Olympic trainer who discovered that the same principles that create athletic champions can create learning champions.",
            expertise_areas=["motivation", "goal_setting", "persistence", "achievement"],
            appearance={
                "age": "middle_aged",
                "clothing": "athletic_wear",
                "build": "fit_and_energetic",
                "expression": "encouraging_smile"
            },
            voice_profile={
                "tone": "enthusiastic_and_clear",
                "pace": "energetic",
                "volume": "slightly_louder"
            },
            personality_traits={
                "enthusiasm": 0.9,
                "encouragement": 0.95,
                "energy": 0.85,
                "competitiveness": 0.7
            },
            catchphrases=[
                "Champions are made in training, not in competition",
                "Every expert was once a beginner",
                "Your only competition is who you were yesterday"
            ]
        )
        self.add_mentor(coach)
        
        # Patient Teacher - Maria Montessori inspired
        teacher = MentorCharacter(
            mentor_id="patient_teacher",
            name="Ms. Aurora",
            personality=MentorPersonality.PATIENT_TEACHER,
            description="A gentle educator who believes every student can succeed",
            backstory="Ms. Aurora has taught students of all ages and abilities, developing an infinite well of patience and innovative teaching methods.",
            expertise_areas=["education", "patience", "clarity", "individual_learning"],
            appearance={
                "age": "mature",
                "clothing": "professional_warm",
                "expression": "kind_and_attentive",
                "posture": "welcoming"
            },
            voice_profile={
                "tone": "warm_and_clear",
                "pace": "measured_and_clear",
                "inflection": "encouraging"
            },
            personality_traits={
                "patience": 0.95,
                "clarity": 0.9,
                "supportiveness": 0.85,
                "organization": 0.8
            },
            catchphrases=[
                "Every student learns in their own unique way",
                "There are no stupid questions, only curious minds",
                "Progress is progress, no matter how small"
            ]
        )
        self.add_mentor(teacher)
        
        # Brilliant Scientist - Einstein inspired
        scientist = MentorCharacter(
            mentor_id="brilliant_scientist",
            name="Dr. Quantum",
            personality=MentorPersonality.BRILLIANT_SCIENTIST,
            description="A brilliant researcher fascinated by the process of discovery",
            backstory="Dr. Quantum has made groundbreaking discoveries by treating every question as an experiment and every learner as a fellow scientist.",
            expertise_areas=["scientific_method", "critical_thinking", "analysis", "discovery"],
            appearance={
                "age": "middle_aged",
                "clothing": "lab_coat_casual",
                "hair": "slightly_disheveled",
                "expression": "curious_and_intense"
            },
            voice_profile={
                "tone": "intellectual_enthusiasm",
                "pace": "varies_with_excitement",
                "vocabulary": "precise_and_technical"
            },
            personality_traits={
                "intelligence": 0.95,
                "curiosity": 0.9,
                "precision": 0.85,
                "enthusiasm": 0.8
            },
            catchphrases=[
                "The important thing is not to stop questioning",
                "Imagination is more important than knowledge",
                "Science is about finding patterns in chaos"
            ]
        )
        self.add_mentor(scientist)
    
    def add_mentor(self, mentor: MentorCharacter):
        """Add a mentor to the system"""
        self.mentors[mentor.mentor_id] = mentor
    
    def get_mentor_for_user(self, user_id: str, preferred_personality: Optional[MentorPersonality] = None) -> MentorCharacter:
        """Get the best mentor for a user"""
        # If user has a preference, use it
        if preferred_personality:
            for mentor in self.mentors.values():
                if mentor.personality == preferred_personality:
                    return mentor
        
        # Otherwise, get the mentor with strongest relationship
        relationships = self.get_user_relationships(user_id)
        if relationships:
            best_relationship = max(relationships, key=lambda r: r.bond_strength)
            return self.mentors[best_relationship.mentor_id]
        
        # Default to wise sage for new users
        return self.mentors.get("wise_sage", list(self.mentors.values())[0])
    
    def get_mentor_state(self, mentor_id: str, user_id: str) -> MentorState:
        """Get current state of mentor for specific user"""
        state_key = f"{mentor_id}_{user_id}"
        
        if state_key not in self.mentor_states:
            # Load from database or create new state
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT current_mood, energy_level, relationship_level, recent_interactions,
                           last_interaction, session_duration, topics_discussed
                    FROM mentor_states WHERE mentor_id = ? AND user_id = ?
                """, (mentor_id, user_id))
                
                row = cursor.fetchone()
                if row:
                    mood, energy, relationship, interactions, last_interaction, duration, topics = row
                    self.mentor_states[state_key] = MentorState(
                        mentor_id=mentor_id,
                        user_id=user_id,
                        current_mood=MentorMood(mood),
                        energy_level=energy,
                        relationship_level=relationship,
                        recent_interactions=json.loads(interactions) if interactions else [],
                        last_interaction=datetime.fromisoformat(last_interaction) if last_interaction else None,
                        session_duration=duration,
                        topics_discussed=json.loads(topics) if topics else []
                    )
                else:
                    # Create new state
                    self.mentor_states[state_key] = MentorState(
                        mentor_id=mentor_id,
                        user_id=user_id,
                        current_mood=MentorMood.CALM,
                        energy_level=0.8,
                        relationship_level=0.1
                    )
        
        return self.mentor_states[state_key]
    
    def get_user_relationships(self, user_id: str) -> List[UserMentorRelationship]:
        """Get all mentor relationships for a user"""
        relationships = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT mentor_id, bond_strength, trust_level, interaction_count,
                       total_time_together, shared_achievements, memorable_moments,
                       preferences, last_interaction
                FROM user_mentor_relationships WHERE user_id = ?
            """, (user_id,))
            
            for row in cursor.fetchall():
                mentor_id, bond, trust, count, time_together, achievements, moments, prefs, last_interaction = row
                relationships.append(UserMentorRelationship(
                    user_id=user_id,
                    mentor_id=mentor_id,
                    bond_strength=bond,
                    trust_level=trust,
                    interaction_count=count,
                    total_time_together=time_together,
                    shared_achievements=json.loads(achievements) if achievements else [],
                    memorable_moments=json.loads(moments) if moments else [],
                    preferences=json.loads(prefs) if prefs else {},
                    last_interaction=datetime.fromisoformat(last_interaction) if last_interaction else None
                ))
        
        return relationships
    
    def generate_mentor_response(self, user_id: str, context: LearningContext,
                               user_progress: Dict[str, Any], 
                               mentor_id: Optional[str] = None) -> MentorMessage:
        """Generate a mentor response for the current situation"""
        # Get mentor
        if mentor_id and mentor_id in self.mentors:
            mentor = self.mentors[mentor_id]
        else:
            mentor = self.get_mentor_for_user(user_id)
        
        # Get mentor state
        state = self.get_mentor_state(mentor.mentor_id, user_id)
        
        # Get relationship
        relationships = self.get_user_relationships(user_id)
        relationship = next((r for r in relationships if r.mentor_id == mentor.mentor_id), 
                          UserMentorRelationship(user_id=user_id, mentor_id=mentor.mentor_id))
        
        # Generate response
        message = self.response_engine.generate_adaptive_response(
            mentor, state, context, user_progress, relationship
        )
        
        # Update state and relationship
        self._update_mentor_state(state, message)
        self._update_relationship(relationship, message)
        
        # Store interaction
        self._store_interaction(message)
        
        return message
    
    def _update_mentor_state(self, state: MentorState, message: MentorMessage):
        """Update mentor state based on interaction"""
        state.current_mood = message.mood
        state.last_interaction = message.timestamp
        state.recent_interactions.append(message.interaction_type.value)
        
        # Keep only recent interactions
        if len(state.recent_interactions) > 10:
            state.recent_interactions = state.recent_interactions[-10:]
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO mentor_states
                (mentor_id, user_id, current_mood, energy_level, relationship_level,
                 recent_interactions, last_interaction, session_duration, topics_discussed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state.mentor_id, state.user_id, state.current_mood.value,
                state.energy_level, state.relationship_level,
                json.dumps(state.recent_interactions),
                state.last_interaction.isoformat() if state.last_interaction else None,
                state.session_duration, json.dumps(state.topics_discussed)
            ))
    
    def _update_relationship(self, relationship: UserMentorRelationship, message: MentorMessage):
        """Update relationship based on interaction"""
        relationship.interaction_count += 1
        relationship.last_interaction = message.timestamp
        
        # Gradually increase bond strength with positive interactions
        if message.interaction_type in [InteractionType.ENCOURAGEMENT, InteractionType.CELEBRATION]:
            relationship.bond_strength = min(1.0, relationship.bond_strength + 0.05)
            relationship.trust_level = min(1.0, relationship.trust_level + 0.03)
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_mentor_relationships
                (user_id, mentor_id, bond_strength, trust_level, interaction_count,
                 total_time_together, shared_achievements, memorable_moments,
                 preferences, last_interaction)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                relationship.user_id, relationship.mentor_id,
                relationship.bond_strength, relationship.trust_level,
                relationship.interaction_count, relationship.total_time_together,
                json.dumps(relationship.shared_achievements),
                json.dumps(relationship.memorable_moments),
                json.dumps(relationship.preferences),
                relationship.last_interaction.isoformat() if relationship.last_interaction else None
            ))
    
    def _store_interaction(self, message: MentorMessage):
        """Store interaction in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO mentor_interactions
                (mentor_id, user_id, interaction_type, content, context, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message.mentor_id, message.user_id,
                message.interaction_type.value, message.content,
                message.context.value, message.timestamp.isoformat()
            ))
    
    def get_available_mentors(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of available mentors with relationship info"""
        relationships = {r.mentor_id: r for r in self.get_user_relationships(user_id)}
        
        available_mentors = []
        for mentor in self.mentors.values():
            relationship = relationships.get(mentor.mentor_id)
            
            mentor_info = {
                "mentor_id": mentor.mentor_id,
                "name": mentor.name,
                "personality": mentor.personality.value,
                "description": mentor.description,
                "expertise_areas": mentor.expertise_areas,
                "appearance": mentor.appearance,
                "bond_strength": relationship.bond_strength if relationship else 0.0,
                "interaction_count": relationship.interaction_count if relationship else 0
            }
            
            available_mentors.append(mentor_info)
        
        return sorted(available_mentors, key=lambda x: x["bond_strength"], reverse=True)


# Example usage and testing
if __name__ == "__main__":
    # Initialize mentor system
    mentor_system = MentorSystem("test_mentors.db")
    
    # Simulate user interaction
    user_id = "user123"
    user_progress = {
        "skills_completed": 5,
        "current_skill": "programming_basics",
        "recent_mistakes": 2,
        "learning_streak": 7,
        "user_name": "Alex"
    }
    
    # Generate mentor response for different contexts
    contexts = [
        LearningContext.FIRST_TIME,
        LearningContext.STRUGGLING,
        LearningContext.PROGRESSING,
        LearningContext.CELEBRATING
    ]
    
    for context in contexts:
        print(f"\n=== {context.value.upper()} ===")
        message = mentor_system.generate_mentor_response(user_id, context, user_progress)
        print(f"Mentor: {mentor_system.mentors[message.mentor_id].name}")
        print(f"Mood: {message.mood.value}")
        print(f"Message: {message.content}")
        print(f"Suggested Actions: {', '.join(message.suggested_actions)}")
    
    # Get available mentors
    print("\n=== AVAILABLE MENTORS ===")
    available = mentor_system.get_available_mentors(user_id)
    for mentor_info in available:
        print(f"{mentor_info['name']} ({mentor_info['personality']}) - Bond: {mentor_info['bond_strength']:.2f}")
    
    print("\nVirtual mentor system working successfully!")