#!/usr/bin/env python3

import asyncio
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import random
import uuid
import re

class VoicePersonality(Enum):
    FRIENDLY_TEACHER = "friendly_teacher"
    PROFESSIONAL_INSTRUCTOR = "professional_instructor"
    ENCOURAGING_COACH = "encouraging_coach"
    CASUAL_BUDDY = "casual_buddy"
    EXPERT_MENTOR = "expert_mentor"

class SpeechPace(Enum):
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"
    ADAPTIVE = "adaptive"

class VoiceEmphasis(Enum):
    NONE = "none"
    IMPORTANT_POINTS = "important_points"
    WARNINGS = "warnings"
    ENCOURAGEMENT = "encouragement"
    ALL = "all"

class AudioCue(Enum):
    CHIME = "chime"
    BELL = "bell"
    SWOOSH = "swoosh"
    TICK = "tick"
    APPLAUSE = "applause"
    WARNING_BEEP = "warning_beep"
    SUCCESS_SOUND = "success_sound"

@dataclass
class VoiceSettings:
    personality: VoicePersonality
    pace: SpeechPace
    volume: float  # 0.0 to 1.0
    pitch: float   # 0.5 to 2.0 (1.0 is normal)
    emphasis: VoiceEmphasis
    pause_duration: float  # seconds between sentences
    use_audio_cues: bool
    language_code: str  # e.g., "en-US", "es-ES"
    voice_gender: str   # "male", "female", "neutral"

@dataclass
class SpeechSegment:
    id: str
    text: str
    emphasis_level: int  # 1-5 scale
    pause_after: float   # seconds
    audio_cue_before: Optional[AudioCue]
    audio_cue_after: Optional[AudioCue]
    speed_modifier: float  # 0.5 to 2.0 multiplier
    pitch_modifier: float  # 0.5 to 2.0 multiplier
    emotions: List[str]    # happy, excited, concerned, etc.

@dataclass
class VoiceInstruction:
    id: str
    title: str
    context: str  # step, checkpoint, error, encouragement, etc.
    segments: List[SpeechSegment]
    total_estimated_duration: float  # seconds
    interactive_prompts: List[str]    # Questions expecting user response
    fallback_text: str               # Text version if TTS fails
    accessibility_notes: str
    created_at: str

@dataclass
class UserVoiceProfile:
    user_id: str
    preferred_settings: VoiceSettings
    accessibility_needs: List[str]  # hearing_impaired, visual_impaired, etc.
    language_preferences: List[str]
    feedback_history: Dict[str, Any]
    learning_pace: str  # slow, normal, fast
    attention_span: int  # minutes before break suggested
    interaction_preferences: Dict[str, bool]  # likes questions, prefers continuous, etc.

class VoiceContentGenerator:
    def __init__(self):
        self.personality_styles = {
            VoicePersonality.FRIENDLY_TEACHER: {
                "greeting": ["Hello there!", "Welcome!", "Great to see you!", "Let's learn together!"],
                "encouragement": ["You're doing great!", "Excellent work!", "Keep it up!", "Nice job!"],
                "transition": ["Now let's move on to", "Next, we'll", "Time for", "Let's continue with"],
                "warning": ["Let's be careful here", "This is important", "Pay attention to this"],
                "conclusion": ["Well done!", "You've completed", "Fantastic job!", "Mission accomplished!"],
                "tone": "warm and supportive",
                "formality": "casual but educational"
            },
            
            VoicePersonality.PROFESSIONAL_INSTRUCTOR: {
                "greeting": ["Welcome to the tutorial", "Let's begin", "Today we'll cover", "Please follow along"],
                "encouragement": ["Excellent", "Well executed", "Precisely", "Correct"],
                "transition": ["Proceeding to", "The next step is", "We will now", "Moving forward"],
                "warning": ["Please note", "It's crucial that", "Ensure that you", "Be certain to"],
                "conclusion": ["Tutorial completed", "You have successfully", "Objectives achieved", "Process finished"],
                "tone": "clear and authoritative",
                "formality": "professional"
            },
            
            VoicePersonality.ENCOURAGING_COACH: {
                "greeting": ["You've got this!", "Ready to rock?", "Let's make this happen!", "Time to shine!"],
                "encouragement": ["Amazing!", "You're crushing it!", "Phenomenal!", "Outstanding!"],
                "transition": ["Alright, next up", "Here we go with", "Time to tackle", "Let's dive into"],
                "warning": ["Heads up!", "Super important here", "Don't miss this", "This is key"],
                "conclusion": ["Victory!", "You absolutely nailed it!", "Champion!", "What a success!"],
                "tone": "energetic and motivating",
                "formality": "very casual"
            },
            
            VoicePersonality.CASUAL_BUDDY: {
                "greeting": ["Hey!", "What's up?", "Ready?", "Let's do this!"],
                "encouragement": ["Nice!", "Sweet!", "Cool!", "Awesome!"],
                "transition": ["So next", "Okay, now", "Alright, let's", "Time to"],
                "warning": ["Yo, watch out", "Hey, this is important", "Don't forget", "Make sure you"],
                "conclusion": ["Done!", "All good!", "We did it!", "That's a wrap!"],
                "tone": "relaxed and friendly",
                "formality": "very casual"
            },
            
            VoicePersonality.EXPERT_MENTOR: {
                "greeting": ["Let me guide you", "I'll walk you through", "Follow my lead", "Let's explore"],
                "encouragement": ["Precisely executed", "You understand well", "Your technique is improving", "Good insight"],
                "transition": ["Now, consider", "Let's examine", "Observe how", "Notice that"],
                "warning": ["This requires attention", "Critical point here", "Take special care", "This is where mistakes happen"],
                "conclusion": ["Mastery achieved", "You've learned well", "Knowledge gained", "Skills developed"],
                "tone": "wise and patient",
                "formality": "moderately formal"
            }
        }
        
        self.emotional_modifiers = {
            "happy": {"pitch": 1.1, "speed": 1.1, "emphasis": True},
            "excited": {"pitch": 1.2, "speed": 1.2, "emphasis": True},
            "concerned": {"pitch": 0.9, "speed": 0.9, "emphasis": True},
            "calm": {"pitch": 1.0, "speed": 0.95, "emphasis": False},
            "urgent": {"pitch": 1.1, "speed": 1.15, "emphasis": True},
            "proud": {"pitch": 1.05, "speed": 1.0, "emphasis": True}
        }

    def generate_instruction_audio(self, content: str, context: str, 
                                 personality: VoicePersonality,
                                 user_progress: Dict[str, Any] = None) -> VoiceInstruction:
        """Generate voice instruction from text content."""
        
        instruction_id = str(uuid.uuid4())
        
        # Parse content and create segments
        segments = self._create_speech_segments(content, context, personality, user_progress)
        
        # Calculate total duration
        total_duration = sum(
            len(segment.text) * 0.08 + segment.pause_after  # ~0.08 seconds per character
            for segment in segments
        )
        
        # Generate interactive prompts if appropriate
        interactive_prompts = []
        if context in ["step", "checkpoint"]:
            interactive_prompts = self._generate_interactive_prompts(content, personality)
        
        return VoiceInstruction(
            id=instruction_id,
            title=self._generate_instruction_title(content, context),
            context=context,
            segments=segments,
            total_estimated_duration=total_duration,
            interactive_prompts=interactive_prompts,
            fallback_text=content,
            accessibility_notes=self._generate_accessibility_notes(content, segments),
            created_at=datetime.now().isoformat()
        )

    def _create_speech_segments(self, content: str, context: str, 
                              personality: VoicePersonality,
                              user_progress: Dict[str, Any]) -> List[SpeechSegment]:
        """Break content into speech segments with appropriate timing and emphasis."""
        
        segments = []
        style = self.personality_styles[personality]
        
        # Add contextual greeting/opener
        if context == "step_start":
            opener_text = random.choice(style["transition"])
            segments.append(SpeechSegment(
                id=str(uuid.uuid4()),
                text=opener_text,
                emphasis_level=2,
                pause_after=0.5,
                audio_cue_before=AudioCue.CHIME,
                audio_cue_after=None,
                speed_modifier=1.0,
                pitch_modifier=1.0,
                emotions=["happy"]
            ))
        
        # Process main content
        sentences = self._split_into_sentences(content)
        
        for i, sentence in enumerate(sentences):
            # Determine emphasis and emotion
            emphasis_level = self._calculate_emphasis_level(sentence, context)
            emotions = self._detect_emotions(sentence, context)
            
            # Add encouraging interjections for long content
            if i > 0 and i % 3 == 0 and len(sentences) > 5:
                encouragement = random.choice(style["encouragement"])
                segments.append(SpeechSegment(
                    id=str(uuid.uuid4()),
                    text=encouragement,
                    emphasis_level=3,
                    pause_after=0.3,
                    audio_cue_before=None,
                    audio_cue_after=None,
                    speed_modifier=1.05,
                    pitch_modifier=1.05,
                    emotions=["encouraging"]
                ))
            
            # Apply emotional modifiers
            speed_mod = 1.0
            pitch_mod = 1.0
            
            for emotion in emotions:
                if emotion in self.emotional_modifiers:
                    modifiers = self.emotional_modifiers[emotion]
                    speed_mod *= modifiers.get("speed", 1.0)
                    pitch_mod *= modifiers.get("pitch", 1.0)
            
            # Determine pauses
            pause_duration = 0.5 if sentence.endswith('.') else 0.3
            if emphasis_level >= 4:
                pause_duration += 0.2  # Extra pause for emphasis
            
            # Audio cues for warnings or important points
            audio_cue_before = None
            audio_cue_after = None
            
            if emphasis_level >= 4:
                audio_cue_before = AudioCue.CHIME
            
            if "warning" in emotions or "caution" in sentence.lower():
                audio_cue_before = AudioCue.WARNING_BEEP
            
            segment = SpeechSegment(
                id=str(uuid.uuid4()),
                text=sentence,
                emphasis_level=emphasis_level,
                pause_after=pause_duration,
                audio_cue_before=audio_cue_before,
                audio_cue_after=audio_cue_after,
                speed_modifier=speed_mod,
                pitch_modifier=pitch_mod,
                emotions=emotions
            )
            
            segments.append(segment)
        
        # Add contextual closer
        if context in ["step_complete", "tutorial_complete"]:
            closer_text = random.choice(style["encouragement"])
            segments.append(SpeechSegment(
                id=str(uuid.uuid4()),
                text=closer_text,
                emphasis_level=3,
                pause_after=0.8,
                audio_cue_before=None,
                audio_cue_after=AudioCue.SUCCESS_SOUND,
                speed_modifier=1.0,
                pitch_modifier=1.1,
                emotions=["proud", "happy"]
            ))
        
        return segments

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for better pacing."""
        
        # Simple sentence splitting (could be enhanced with NLP)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Break up very long sentences
        processed_sentences = []
        for sentence in sentences:
            if len(sentence) > 150:  # Very long sentence
                # Try to split on commas or conjunctions
                parts = re.split(r'[,;]|\band\b|\bbut\b|\bor\b', sentence)
                processed_sentences.extend([part.strip() for part in parts if part.strip()])
            else:
                processed_sentences.append(sentence)
        
        return processed_sentences

    def _calculate_emphasis_level(self, sentence: str, context: str) -> int:
        """Calculate emphasis level for a sentence (1-5 scale)."""
        
        emphasis = 1  # Base level
        
        # Context-based emphasis
        if context in ["warning", "error", "critical"]:
            emphasis += 2
        elif context in ["success", "achievement"]:
            emphasis += 1
        
        # Content-based emphasis
        emphasis_keywords = {
            5: ["danger", "warning", "critical", "important", "never", "always", "must"],
            4: ["careful", "attention", "note", "remember", "ensure"],
            3: ["should", "recommended", "consider", "notice"],
            2: ["might", "could", "perhaps", "usually"]
        }
        
        sentence_lower = sentence.lower()
        for level, keywords in emphasis_keywords.items():
            if any(keyword in sentence_lower for keyword in keywords):
                emphasis = max(emphasis, level)
                break
        
        # Punctuation-based emphasis
        if sentence.endswith('!'):
            emphasis += 1
        if sentence.isupper():
            emphasis += 2
        
        return min(5, emphasis)

    def _detect_emotions(self, sentence: str, context: str) -> List[str]:
        """Detect emotional context for the sentence."""
        
        emotions = []
        sentence_lower = sentence.lower()
        
        # Context-based emotions
        if context == "success":
            emotions.append("happy")
        elif context == "warning":
            emotions.append("concerned")
        elif context == "achievement":
            emotions.extend(["proud", "excited"])
        
        # Content-based emotions
        positive_words = ["great", "excellent", "good", "success", "complete", "done", "perfect"]
        negative_words = ["error", "wrong", "failed", "problem", "issue", "mistake"]
        urgent_words = ["quickly", "immediately", "now", "urgent", "fast"]
        
        if any(word in sentence_lower for word in positive_words):
            emotions.append("happy")
        
        if any(word in sentence_lower for word in negative_words):
            emotions.append("concerned")
        
        if any(word in sentence_lower for word in urgent_words):
            emotions.append("urgent")
        
        # Default to calm if no emotions detected
        if not emotions:
            emotions.append("calm")
        
        return list(set(emotions))  # Remove duplicates

    def _generate_interactive_prompts(self, content: str, 
                                    personality: VoicePersonality) -> List[str]:
        """Generate interactive prompts for user engagement."""
        
        prompts = []
        style = self.personality_styles[personality]
        
        # General prompts based on content type
        if "step" in content.lower():
            prompts.extend([
                "Are you ready to proceed?",
                "Do you understand so far?",
                "Would you like me to repeat anything?"
            ])
        
        if "complete" in content.lower() or "finish" in content.lower():
            prompts.extend([
                "How did that go?",
                "Did you encounter any difficulties?",
                "Are you ready for the next step?"
            ])
        
        # Personality-specific prompts
        if personality == VoicePersonality.FRIENDLY_TEACHER:
            prompts.extend([
                "Any questions before we continue?",
                "Is everything making sense?"
            ])
        elif personality == VoicePersonality.ENCOURAGING_COACH:
            prompts.extend([
                "How are you feeling about this?",
                "Ready to tackle the next challenge?"
            ])
        elif personality == VoicePersonality.EXPERT_MENTOR:
            prompts.extend([
                "Do you see how this connects to what we learned before?",
                "What do you think will happen next?"
            ])
        
        return prompts[:3]  # Limit to 3 prompts

    def _generate_instruction_title(self, content: str, context: str) -> str:
        """Generate a title for the instruction."""
        
        if context == "step_start":
            return "Step Instructions"
        elif context == "warning":
            return "Important Warning"
        elif context == "success":
            return "Success Message"
        elif context == "error":
            return "Error Guidance"
        elif context == "checkpoint":
            return "Checkpoint Validation"
        else:
            return "Tutorial Guidance"

    def _generate_accessibility_notes(self, content: str, 
                                    segments: List[SpeechSegment]) -> str:
        """Generate accessibility notes for the instruction."""
        
        notes = []
        
        # Audio cue information
        audio_cues = [s.audio_cue_before for s in segments if s.audio_cue_before]
        audio_cues.extend([s.audio_cue_after for s in segments if s.audio_cue_after])
        
        if audio_cues:
            unique_cues = list(set(audio_cues))
            notes.append(f"Audio cues used: {', '.join([cue.value for cue in unique_cues])}")
        
        # Emphasis information
        high_emphasis_count = sum(1 for s in segments if s.emphasis_level >= 4)
        if high_emphasis_count > 0:
            notes.append(f"{high_emphasis_count} highly emphasized segments")
        
        # Duration information
        total_duration = sum(s.pause_after for s in segments)
        notes.append(f"Total pauses: {total_duration:.1f} seconds")
        
        return "; ".join(notes)

class VoiceInteractionEngine:
    def __init__(self):
        self.content_generator = VoiceContentGenerator()
        
        self.speech_patterns = {
            "questioning": {
                "pitch_increase": 0.1,
                "pace_decrease": 0.1,
                "pause_after": 1.0
            },
            "listing": {
                "pace_decrease": 0.05,
                "pause_between_items": 0.5
            },
            "emphasizing": {
                "volume_increase": 0.2,
                "pace_decrease": 0.2,
                "pitch_increase": 0.05
            }
        }

    async def create_voice_guidance(self, tutorial_step: Dict[str, Any], 
                                  user_profile: UserVoiceProfile,
                                  progress_context: Dict[str, Any] = None) -> VoiceInstruction:
        """Create voice guidance for a tutorial step."""
        
        # Extract step information
        step_title = tutorial_step.get("title", "Tutorial Step")
        instructions = tutorial_step.get("instructions", [])
        context = tutorial_step.get("context", "step")
        
        # Combine instructions into narrative
        narrative = self._create_step_narrative(
            step_title, instructions, user_profile.preferred_settings.personality
        )
        
        # Generate voice instruction
        voice_instruction = self.content_generator.generate_instruction_audio(
            narrative, context, user_profile.preferred_settings.personality, progress_context
        )
        
        # Apply user preferences
        voice_instruction = await self._apply_user_preferences(voice_instruction, user_profile)
        
        return voice_instruction

    def _create_step_narrative(self, title: str, instructions: List[str], 
                             personality: VoicePersonality) -> str:
        """Create a flowing narrative from step instructions."""
        
        style = self.content_generator.personality_styles[personality]
        
        # Start with transition
        opener = random.choice(style["transition"])
        narrative_parts = [f"{opener} {title.lower()}."]
        
        # Add instructions with connecting words
        connectors = ["First,", "Next,", "Then,", "After that,", "Now,", "Finally,"]
        
        for i, instruction in enumerate(instructions):
            if i < len(connectors):
                connector = connectors[i]
            else:
                connector = "Also," if i % 2 == 0 else "Next,"
            
            narrative_parts.append(f"{connector} {instruction}")
        
        return " ".join(narrative_parts)

    async def _apply_user_preferences(self, instruction: VoiceInstruction, 
                                    user_profile: UserVoiceProfile) -> VoiceInstruction:
        """Apply user preferences to the voice instruction."""
        
        settings = user_profile.preferred_settings
        
        # Adjust pace based on user preference
        pace_multiplier = {
            SpeechPace.SLOW: 0.8,
            SpeechPace.NORMAL: 1.0,
            SpeechPace.FAST: 1.2,
            SpeechPace.ADAPTIVE: await self._calculate_adaptive_pace(user_profile)
        }.get(settings.pace, 1.0)
        
        # Apply pace to all segments
        for segment in instruction.segments:
            segment.speed_modifier *= pace_multiplier
            
            # Adjust pauses based on user attention span
            if user_profile.attention_span < 5:  # Short attention span
                segment.pause_after *= 0.8  # Shorter pauses
            elif user_profile.attention_span > 15:  # Long attention span
                segment.pause_after *= 1.2  # Longer pauses for processing
        
        # Adjust emphasis based on user preferences
        if settings.emphasis == VoiceEmphasis.ALL:
            for segment in instruction.segments:
                segment.emphasis_level = min(5, segment.emphasis_level + 1)
        elif settings.emphasis == VoiceEmphasis.NONE:
            for segment in instruction.segments:
                segment.emphasis_level = max(1, segment.emphasis_level - 1)
        
        # Remove audio cues if user doesn't want them
        if not settings.use_audio_cues:
            for segment in instruction.segments:
                segment.audio_cue_before = None
                segment.audio_cue_after = None
        
        # Recalculate duration
        instruction.total_estimated_duration = sum(
            len(segment.text) * 0.08 / segment.speed_modifier + segment.pause_after
            for segment in instruction.segments
        )
        
        return instruction

    async def _calculate_adaptive_pace(self, user_profile: UserVoiceProfile) -> float:
        """Calculate adaptive pace based on user's learning pattern."""
        
        feedback_history = user_profile.feedback_history
        
        # Analyze past pace preferences
        pace_feedback = feedback_history.get("pace_feedback", [])
        if pace_feedback:
            avg_requested_pace = sum(pace_feedback) / len(pace_feedback)
            return max(0.7, min(1.5, avg_requested_pace))
        
        # Default based on learning pace
        pace_defaults = {
            "slow": 0.85,
            "normal": 1.0,
            "fast": 1.15
        }
        
        return pace_defaults.get(user_profile.learning_pace, 1.0)

    async def generate_contextual_response(self, user_input: str, 
                                         current_context: Dict[str, Any],
                                         user_profile: UserVoiceProfile) -> VoiceInstruction:
        """Generate contextual voice response to user input."""
        
        # Analyze user input intent
        intent = self._analyze_user_intent(user_input)
        
        # Generate appropriate response
        if intent == "clarification":
            response_text = await self._generate_clarification_response(user_input, current_context)
        elif intent == "encouragement":
            response_text = await self._generate_encouragement_response(user_profile)
        elif intent == "help":
            response_text = await self._generate_help_response(current_context)
        elif intent == "repeat":
            response_text = "Let me repeat that for you."
        else:
            response_text = await self._generate_generic_response(user_input, user_profile)
        
        return self.content_generator.generate_instruction_audio(
            response_text, "response", user_profile.preferred_settings.personality
        )

    def _analyze_user_intent(self, user_input: str) -> str:
        """Analyze user input to determine intent."""
        
        user_input_lower = user_input.lower()
        
        clarification_words = ["what", "how", "why", "when", "where", "explain", "clarify"]
        encouragement_words = ["help", "stuck", "confused", "difficult", "hard"]
        repeat_words = ["repeat", "again", "say that again", "didn't hear"]
        
        if any(word in user_input_lower for word in clarification_words):
            return "clarification"
        elif any(word in user_input_lower for word in encouragement_words):
            return "encouragement"
        elif any(word in user_input_lower for word in repeat_words):
            return "repeat"
        else:
            return "generic"

    async def _generate_clarification_response(self, user_input: str, 
                                             context: Dict[str, Any]) -> str:
        """Generate response to clarification requests."""
        
        responses = [
            "Let me break that down for you.",
            "Here's another way to think about it.",
            "I'll explain that step in more detail.",
            "Good question! Let me clarify."
        ]
        
        return random.choice(responses)

    async def _generate_encouragement_response(self, user_profile: UserVoiceProfile) -> str:
        """Generate encouraging response."""
        
        personality = user_profile.preferred_settings.personality
        style = self.content_generator.personality_styles[personality]
        
        encouragements = style["encouragement"] + [
            "Don't worry, this is a common challenge.",
            "You're making progress, even if it doesn't feel like it.",
            "Every expert was once a beginner.",
            "Take your time, there's no rush."
        ]
        
        return random.choice(encouragements)

    async def _generate_help_response(self, context: Dict[str, Any]) -> str:
        """Generate helpful response based on current context."""
        
        current_step = context.get("current_step", "this step")
        
        responses = [
            f"I'm here to help with {current_step}. What specifically would you like me to explain?",
            "Let's work through this together. What part is causing trouble?",
            "No problem! I can provide more guidance on any part of this process.",
            "That's what I'm here for. What would be most helpful right now?"
        ]
        
        return random.choice(responses)

    async def _generate_generic_response(self, user_input: str, 
                                       user_profile: UserVoiceProfile) -> str:
        """Generate generic response for unclear input."""
        
        personality = user_profile.preferred_settings.personality
        
        if personality == VoicePersonality.FRIENDLY_TEACHER:
            return "I want to make sure I understand what you need. Could you tell me more?"
        elif personality == VoicePersonality.ENCOURAGING_COACH:
            return "I'm here to support you! What can I help you with?"
        elif personality == VoicePersonality.PROFESSIONAL_INSTRUCTOR:
            return "Please specify what aspect you'd like me to address."
        else:
            return "How can I help you with this step?"

class VoiceGuidanceSystem:
    def __init__(self, db_path: str = "voice_guidance.db"):
        self.db_path = db_path
        self.interaction_engine = VoiceInteractionEngine()
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS voice_instructions (
            id TEXT PRIMARY KEY,
            title TEXT,
            context TEXT,
            segments TEXT,
            total_duration REAL,
            interactive_prompts TEXT,
            fallback_text TEXT,
            accessibility_notes TEXT,
            created_at TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_voice_profiles (
            user_id TEXT PRIMARY KEY,
            preferred_settings TEXT,
            accessibility_needs TEXT,
            language_preferences TEXT,
            feedback_history TEXT,
            learning_pace TEXT,
            attention_span INTEGER,
            interaction_preferences TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS voice_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            tutorial_id TEXT,
            instructions_played TEXT,
            user_interactions TEXT,
            session_duration REAL,
            feedback_rating INTEGER,
            session_notes TEXT,
            created_at TEXT
        )
        ''')
        
        conn.commit()
        conn.close()

    async def create_user_voice_profile(self, user_id: str, 
                                      preferences: Dict[str, Any] = None) -> UserVoiceProfile:
        """Create a voice profile for a user."""
        
        if preferences is None:
            preferences = {}
        
        # Default voice settings
        default_settings = VoiceSettings(
            personality=VoicePersonality(preferences.get("personality", "friendly_teacher")),
            pace=SpeechPace(preferences.get("pace", "normal")),
            volume=preferences.get("volume", 0.8),
            pitch=preferences.get("pitch", 1.0),
            emphasis=VoiceEmphasis(preferences.get("emphasis", "important_points")),
            pause_duration=preferences.get("pause_duration", 0.5),
            use_audio_cues=preferences.get("use_audio_cues", True),
            language_code=preferences.get("language_code", "en-US"),
            voice_gender=preferences.get("voice_gender", "neutral")
        )
        
        profile = UserVoiceProfile(
            user_id=user_id,
            preferred_settings=default_settings,
            accessibility_needs=preferences.get("accessibility_needs", []),
            language_preferences=preferences.get("language_preferences", ["en-US"]),
            feedback_history={},
            learning_pace=preferences.get("learning_pace", "normal"),
            attention_span=preferences.get("attention_span", 10),
            interaction_preferences=preferences.get("interaction_preferences", {
                "likes_questions": True,
                "prefers_continuous": False,
                "wants_encouragement": True
            })
        )
        
        # Save to database
        await self._save_user_profile(profile)
        
        return profile

    async def _save_user_profile(self, profile: UserVoiceProfile):
        """Save user voice profile to database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO user_voice_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile.user_id,
            json.dumps(asdict(profile.preferred_settings)),
            json.dumps(profile.accessibility_needs),
            json.dumps(profile.language_preferences),
            json.dumps(profile.feedback_history),
            profile.learning_pace,
            profile.attention_span,
            json.dumps(profile.interaction_preferences),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()

    async def get_user_voice_profile(self, user_id: str) -> Optional[UserVoiceProfile]:
        """Get user voice profile from database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user_voice_profiles WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        settings_data = json.loads(row[1])
        preferred_settings = VoiceSettings(**settings_data)
        
        return UserVoiceProfile(
            user_id=row[0],
            preferred_settings=preferred_settings,
            accessibility_needs=json.loads(row[2]),
            language_preferences=json.loads(row[3]),
            feedback_history=json.loads(row[4]),
            learning_pace=row[5],
            attention_span=row[6],
            interaction_preferences=json.loads(row[7])
        )

    async def generate_step_guidance(self, tutorial_step: Dict[str, Any], 
                                   user_id: str,
                                   progress_context: Dict[str, Any] = None) -> VoiceInstruction:
        """Generate voice guidance for a tutorial step."""
        
        # Get user profile
        user_profile = await self.get_user_voice_profile(user_id)
        if not user_profile:
            # Create default profile
            user_profile = await self.create_user_voice_profile(user_id)
        
        # Generate voice instruction
        instruction = await self.interaction_engine.create_voice_guidance(
            tutorial_step, user_profile, progress_context
        )
        
        # Save instruction to database
        await self._save_voice_instruction(instruction)
        
        return instruction

    async def _save_voice_instruction(self, instruction: VoiceInstruction):
        """Save voice instruction to database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO voice_instructions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            instruction.id, instruction.title, instruction.context,
            json.dumps([asdict(s) for s in instruction.segments]),
            instruction.total_estimated_duration,
            json.dumps(instruction.interactive_prompts),
            instruction.fallback_text, instruction.accessibility_notes,
            instruction.created_at
        ))
        
        conn.commit()
        conn.close()

    async def handle_user_voice_input(self, user_input: str, user_id: str,
                                    current_context: Dict[str, Any]) -> VoiceInstruction:
        """Handle user voice input and generate appropriate response."""
        
        # Get user profile
        user_profile = await self.get_user_voice_profile(user_id)
        if not user_profile:
            user_profile = await self.create_user_voice_profile(user_id)
        
        # Generate contextual response
        response = await self.interaction_engine.generate_contextual_response(
            user_input, current_context, user_profile
        )
        
        # Save interaction for learning
        await self._record_user_interaction(user_id, user_input, response, current_context)
        
        return response

    async def _record_user_interaction(self, user_id: str, user_input: str,
                                     response: VoiceInstruction,
                                     context: Dict[str, Any]):
        """Record user interaction for improving future responses."""
        
        interaction_record = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "response_id": response.id,
            "context": context,
            "response_type": response.context
        }
        
        # This would typically be stored in a dedicated interactions table
        # For now, we'll update the user's feedback history
        user_profile = await self.get_user_voice_profile(user_id)
        if user_profile:
            if "interactions" not in user_profile.feedback_history:
                user_profile.feedback_history["interactions"] = []
            
            user_profile.feedback_history["interactions"].append(interaction_record)
            
            # Keep only recent interactions (last 50)
            user_profile.feedback_history["interactions"] = \
                user_profile.feedback_history["interactions"][-50:]
            
            await self._save_user_profile(user_profile)

    async def update_user_preferences(self, user_id: str, 
                                    preference_updates: Dict[str, Any]) -> bool:
        """Update user voice preferences."""
        
        user_profile = await self.get_user_voice_profile(user_id)
        if not user_profile:
            return False
        
        # Update preferences
        settings = user_profile.preferred_settings
        
        if "personality" in preference_updates:
            settings.personality = VoicePersonality(preference_updates["personality"])
        if "pace" in preference_updates:
            settings.pace = SpeechPace(preference_updates["pace"])
        if "volume" in preference_updates:
            settings.volume = preference_updates["volume"]
        if "pitch" in preference_updates:
            settings.pitch = preference_updates["pitch"]
        if "use_audio_cues" in preference_updates:
            settings.use_audio_cues = preference_updates["use_audio_cues"]
        
        # Update other profile settings
        if "learning_pace" in preference_updates:
            user_profile.learning_pace = preference_updates["learning_pace"]
        if "attention_span" in preference_updates:
            user_profile.attention_span = preference_updates["attention_span"]
        
        # Save updated profile
        await self._save_user_profile(user_profile)
        
        return True

    async def get_voice_guidance_summary(self, user_id: str, 
                                       tutorial_id: str) -> Dict[str, Any]:
        """Get summary of voice guidance usage for a tutorial."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM voice_sessions WHERE user_id = ? AND tutorial_id = ?
        ''', (user_id, tutorial_id))
        
        sessions = cursor.fetchall()
        conn.close()
        
        if not sessions:
            return {"message": "No voice sessions found"}
        
        total_duration = sum(session[5] for session in sessions)  # session_duration
        avg_rating = sum(session[6] for session in sessions if session[6]) / len(sessions)
        
        return {
            "total_sessions": len(sessions),
            "total_duration_minutes": round(total_duration / 60, 1),
            "average_rating": round(avg_rating, 1) if avg_rating else None,
            "most_recent_session": sessions[-1][8],  # created_at
            "user_engagement": "high" if len(sessions) > 5 else "moderate" if len(sessions) > 2 else "low"
        }

    async def suggest_voice_improvements(self, user_id: str) -> List[Dict[str, Any]]:
        """Suggest improvements to voice guidance based on user feedback."""
        
        user_profile = await self.get_user_voice_profile(user_id)
        if not user_profile:
            return []
        
        suggestions = []
        feedback_history = user_profile.feedback_history
        
        # Analyze interaction patterns
        interactions = feedback_history.get("interactions", [])
        
        if len(interactions) > 10:
            # Analyze common requests
            clarification_requests = sum(1 for i in interactions if "clarification" in str(i))
            repeat_requests = sum(1 for i in interactions if "repeat" in str(i))
            
            if clarification_requests > len(interactions) * 0.3:
                suggestions.append({
                    "type": "pace_adjustment",
                    "suggestion": "Consider slowing down the speech pace for better comprehension",
                    "confidence": 0.8
                })
            
            if repeat_requests > len(interactions) * 0.2:
                suggestions.append({
                    "type": "volume_adjustment",
                    "suggestion": "Consider increasing volume or checking audio quality",
                    "confidence": 0.7
                })
        
        # Attention span analysis
        if user_profile.attention_span < 5:
            suggestions.append({
                "type": "content_structure",
                "suggestion": "Break instructions into shorter segments with more frequent pauses",
                "confidence": 0.9
            })
        
        return suggestions

if __name__ == "__main__":
    async def main():
        voice_system = VoiceGuidanceSystem()
        
        # Create a user voice profile
        user_profile = await voice_system.create_user_voice_profile(
            "user123", 
            {
                "personality": "friendly_teacher",
                "pace": "normal",
                "volume": 0.8,
                "learning_pace": "normal",
                "attention_span": 12,
                "use_audio_cues": True
            }
        )
        
        print(f"Created voice profile for user: {user_profile.user_id}")
        print(f"Personality: {user_profile.preferred_settings.personality.value}")
        print(f"Pace: {user_profile.preferred_settings.pace.value}")
        print(f"Attention span: {user_profile.attention_span} minutes")
        
        # Generate voice guidance for a tutorial step
        sample_step = {
            "title": "Connect the LED to the breadboard",
            "instructions": [
                "Take the red LED from your kit",
                "Insert the long leg into hole A1 on the breadboard",
                "Insert the short leg into hole A2",
                "Double-check the connections are secure"
            ],
            "context": "step"
        }
        
        instruction = await voice_system.generate_step_guidance(
            sample_step, "user123", {"step_number": 3, "total_steps": 10}
        )
        
        print(f"\nGenerated voice instruction: {instruction.title}")
        print(f"Total duration: {instruction.total_estimated_duration:.1f} seconds")
        print(f"Number of segments: {len(instruction.segments)}")
        print(f"Interactive prompts: {len(instruction.interactive_prompts)}")
        
        # Show first few segments
        print("\nFirst few speech segments:")
        for i, segment in enumerate(instruction.segments[:3]):
            print(f"  {i+1}. {segment.text}")
            print(f"     Emphasis: {segment.emphasis_level}/5, Emotions: {segment.emotions}")
            if segment.audio_cue_before:
                print(f"     Audio cue: {segment.audio_cue_before.value}")
        
        # Handle user voice input
        user_input = "Can you repeat the part about the LED connections?"
        response = await voice_system.handle_user_voice_input(
            user_input, "user123", {"current_step": sample_step}
        )
        
        print(f"\nUser input: {user_input}")
        print(f"System response: {response.segments[0].text if response.segments else 'No response'}")
    
    asyncio.run(main())