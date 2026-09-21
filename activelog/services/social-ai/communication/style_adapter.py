"""
Communication Style Adaptation System

AI-powered system for analyzing communication styles and providing personalized
recommendations for effective communication based on personality types, cultural
context, relationship dynamics, and situational awareness.
"""

import asyncio
import sqlite3
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from enum import Enum
import numpy as np
from collections import Counter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonalityType(Enum):
    # MBTI Types
    INTJ = "intj"  # Architect
    INTP = "intp"  # Thinker
    ENTJ = "entj"  # Commander
    ENTP = "entp"  # Debater
    INFJ = "infj"  # Advocate
    INFP = "infp"  # Mediator
    ENFJ = "enfj"  # Protagonist
    ENFP = "enfp"  # Campaigner
    ISTJ = "istj"  # Logistician
    ISFJ = "isfj"  # Protector
    ESTJ = "estj"  # Executive
    ESFJ = "esfj"  # Consul
    ISTP = "istp"  # Virtuoso
    ISFP = "isfp"  # Adventurer
    ESTP = "estp"  # Entrepreneur
    ESFP = "esfp"  # Entertainer

class CommunicationStyle(Enum):
    DIRECT = "direct"
    DIPLOMATIC = "diplomatic"
    SUPPORTIVE = "supportive"
    ANALYTICAL = "analytical"
    EXPRESSIVE = "expressive"
    COLLABORATIVE = "collaborative"
    ASSERTIVE = "assertive"
    EMPATHETIC = "empathetic"

class CulturalContext(Enum):
    HIGH_CONTEXT = "high_context"      # Implicit, indirect communication
    LOW_CONTEXT = "low_context"        # Explicit, direct communication
    HIERARCHICAL = "hierarchical"      # Formal, status-aware
    EGALITARIAN = "egalitarian"        # Informal, equality-focused
    INDIVIDUALISTIC = "individualistic" # Self-focused
    COLLECTIVISTIC = "collectivistic"   # Group-focused

class CommunicationChannel(Enum):
    EMAIL = "email"
    TEXT = "text"
    PHONE = "phone"
    VIDEO_CALL = "video_call"
    IN_PERSON = "in_person"
    INSTANT_MESSAGE = "instant_message"
    FORMAL_LETTER = "formal_letter"
    SOCIAL_MEDIA = "social_media"

class MessageTone(Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    URGENT = "urgent"
    SUPPORTIVE = "supportive"
    PERSUASIVE = "persuasive"
    INFORMATIVE = "informative"

@dataclass
class PersonalityProfile:
    user_id: str
    personality_type: PersonalityType
    communication_style: CommunicationStyle
    cultural_context: List[CulturalContext] = field(default_factory=list)
    preferred_channels: List[CommunicationChannel] = field(default_factory=list)
    communication_preferences: Dict[str, Any] = field(default_factory=dict)
    assessed_date: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0
    behavioral_indicators: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CommunicationAnalysis:
    analysis_id: str
    user_id: str
    sample_text: str
    detected_style: CommunicationStyle
    tone_analysis: Dict[str, float] = field(default_factory=dict)
    formality_level: float = 0.5
    emotional_indicators: Dict[str, float] = field(default_factory=dict)
    complexity_metrics: Dict[str, float] = field(default_factory=dict)
    cultural_indicators: List[str] = field(default_factory=list)
    confidence: float = 0.0
    analyzed_date: datetime = field(default_factory=datetime.now)

@dataclass
class CommunicationRecommendation:
    recommendation_id: str
    user_id: str
    target_id: str
    context: str
    recommended_style: CommunicationStyle
    suggested_tone: MessageTone
    preferred_channel: CommunicationChannel
    message_structure: Dict[str, str] = field(default_factory=dict)
    key_points: List[str] = field(default_factory=list)
    things_to_avoid: List[str] = field(default_factory=list)
    cultural_considerations: List[str] = field(default_factory=list)
    example_phrases: List[str] = field(default_factory=list)
    confidence: float = 0.0
    generated_date: datetime = field(default_factory=datetime.now)

@dataclass
class AdaptationRule:
    rule_id: str
    source_style: CommunicationStyle
    target_style: CommunicationStyle
    adaptation_strategies: List[str] = field(default_factory=list)
    tone_adjustments: Dict[str, str] = field(default_factory=dict)
    structure_changes: Dict[str, str] = field(default_factory=dict)
    vocabulary_suggestions: Dict[str, List[str]] = field(default_factory=dict)
    effectiveness_score: float = 0.0

class CommunicationStyleAdapter:
    def __init__(self, db_path: str = "social_ai.db"):
        self.db_path = db_path
        self.personality_indicators = self._load_personality_indicators()
        self.style_patterns = self._load_style_patterns()
        self.cultural_patterns = self._load_cultural_patterns()
        self.adaptation_rules = self._load_adaptation_rules()
        self.init_database()
        
    def init_database(self):
        """Initialize database tables for communication style adaptation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personality_profiles (
                user_id TEXT PRIMARY KEY,
                personality_type TEXT,
                communication_style TEXT,
                cultural_context TEXT,
                preferred_channels TEXT,
                communication_preferences TEXT,
                assessed_date TIMESTAMP,
                confidence_score REAL,
                behavioral_indicators TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS communication_analyses (
                analysis_id TEXT PRIMARY KEY,
                user_id TEXT,
                sample_text TEXT,
                detected_style TEXT,
                tone_analysis TEXT,
                formality_level REAL,
                emotional_indicators TEXT,
                complexity_metrics TEXT,
                cultural_indicators TEXT,
                confidence REAL,
                analyzed_date TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS communication_recommendations (
                recommendation_id TEXT PRIMARY KEY,
                user_id TEXT,
                target_id TEXT,
                context TEXT,
                recommended_style TEXT,
                suggested_tone TEXT,
                preferred_channel TEXT,
                message_structure TEXT,
                key_points TEXT,
                things_to_avoid TEXT,
                cultural_considerations TEXT,
                example_phrases TEXT,
                confidence REAL,
                generated_date TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adaptation_feedback (
                feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_id TEXT,
                user_id TEXT,
                success_rating REAL,
                response_quality REAL,
                relationship_impact REAL,
                feedback_text TEXT,
                feedback_date TIMESTAMP,
                FOREIGN KEY (recommendation_id) REFERENCES communication_recommendations (recommendation_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS style_learning (
                learning_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                interaction_context TEXT,
                original_style TEXT,
                adapted_style TEXT,
                outcome_success REAL,
                learning_points TEXT,
                learned_date TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Communication style adaptation database initialized")

    def _load_personality_indicators(self) -> Dict[str, Dict[str, List[str]]]:
        """Load personality type indicators for analysis"""
        return {
            PersonalityType.INTJ.value: {
                "vocabulary": ["strategic", "efficient", "logical", "systematic", "analyze"],
                "patterns": ["structured thinking", "future-focused", "independent"],
                "communication": ["direct", "concise", "goal-oriented"]
            },
            PersonalityType.ENFP.value: {
                "vocabulary": ["exciting", "possibility", "people", "creative", "inspiring"],
                "patterns": ["enthusiastic", "people-focused", "idea-generating"],
                "communication": ["expressive", "warm", "collaborative"]
            },
            PersonalityType.ISTJ.value: {
                "vocabulary": ["reliable", "traditional", "practical", "detailed", "proven"],
                "patterns": ["methodical", "fact-based", "conservative"],
                "communication": ["formal", "structured", "thorough"]
            },
            PersonalityType.ESFJ.value: {
                "vocabulary": ["team", "support", "harmony", "helpful", "caring"],
                "patterns": ["relationship-focused", "supportive", "consensus-building"],
                "communication": ["warm", "personal", "diplomatic"]
            }
        }

    def _load_style_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load communication style patterns"""
        return {
            CommunicationStyle.DIRECT.value: {
                "sentence_length": "short",
                "vocabulary": ["clear", "bottom line", "specific", "immediate"],
                "structure": ["conclusion first", "bullet points", "action items"],
                "tone_indicators": ["assertive", "straightforward", "efficient"]
            },
            CommunicationStyle.DIPLOMATIC.value: {
                "sentence_length": "medium",
                "vocabulary": ["perhaps", "consider", "might", "suggest", "possibly"],
                "structure": ["context setting", "gentle transition", "collaborative"],
                "tone_indicators": ["tactful", "respectful", "consensus-seeking"]
            },
            CommunicationStyle.ANALYTICAL.value: {
                "sentence_length": "long",
                "vocabulary": ["data", "analysis", "evidence", "research", "conclude"],
                "structure": ["detailed background", "logical progression", "supporting facts"],
                "tone_indicators": ["objective", "thorough", "fact-based"]
            },
            CommunicationStyle.EXPRESSIVE.value: {
                "sentence_length": "varied",
                "vocabulary": ["amazing", "fantastic", "exciting", "love", "feel"],
                "structure": ["emotional opening", "personal stories", "enthusiastic"],
                "tone_indicators": ["energetic", "emotional", "passionate"]
            }
        }

    def _load_cultural_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load cultural communication patterns"""
        return {
            CulturalContext.HIGH_CONTEXT.value: {
                "directness": "low",
                "formality": "high",
                "relationship_first": True,
                "silence_comfort": "high",
                "indicators": ["respectfully", "humbly", "honored", "grateful"]
            },
            CulturalContext.LOW_CONTEXT.value: {
                "directness": "high",
                "formality": "low",
                "relationship_first": False,
                "silence_comfort": "low",
                "indicators": ["specifically", "exactly", "clearly", "directly"]
            },
            CulturalContext.HIERARCHICAL.value: {
                "formality": "high",
                "status_awareness": "high",
                "deference": True,
                "indicators": ["sir", "madam", "please", "kindly", "respectfully"]
            },
            CulturalContext.EGALITARIAN.value: {
                "formality": "low",
                "status_awareness": "low",
                "deference": False,
                "indicators": ["hey", "thanks", "cool", "awesome", "let's"]
            }
        }

    def _load_adaptation_rules(self) -> List[AdaptationRule]:
        """Load communication adaptation rules"""
        return [
            AdaptationRule(
                rule_id="direct_to_diplomatic",
                source_style=CommunicationStyle.DIRECT,
                target_style=CommunicationStyle.DIPLOMATIC,
                adaptation_strategies=[
                    "Add softening language",
                    "Include context and rationale",
                    "Use collaborative language",
                    "Acknowledge other perspectives"
                ],
                tone_adjustments={
                    "must" : "might consider",
                    "need to" : "it would be helpful if",
                    "wrong" : "different perspective",
                    "no" : "that's an interesting point, however"
                },
                effectiveness_score=0.85
            ),
            AdaptationRule(
                rule_id="analytical_to_expressive",
                source_style=CommunicationStyle.ANALYTICAL,
                target_style=CommunicationStyle.EXPRESSIVE,
                adaptation_strategies=[
                    "Add emotional context",
                    "Use more vivid language",
                    "Include personal stories",
                    "Express enthusiasm"
                ],
                tone_adjustments={
                    "data shows" : "it's exciting that data shows",
                    "results indicate" : "the results are really interesting",
                    "conclude" : "it's amazing how this shows"
                },
                effectiveness_score=0.75
            )
        ]

    async def analyze_communication_style(self, user_id: str, text_samples: List[str]) -> PersonalityProfile:
        """
        Analyze user's communication style from text samples
        
        Args:
            user_id: User identifier
            text_samples: List of text samples to analyze
            
        Returns:
            Personality profile with communication style analysis
        """
        if not text_samples:
            raise ValueError("At least one text sample is required")
        
        # Combine all text samples
        combined_text = " ".join(text_samples)
        
        # Analyze individual components
        style_analysis = await self._analyze_style_patterns(combined_text)
        personality_analysis = await self._analyze_personality_indicators(combined_text)
        cultural_analysis = await self._analyze_cultural_patterns(combined_text)
        tone_analysis = await self._analyze_tone_patterns(combined_text)
        
        # Determine primary communication style
        detected_style = self._determine_primary_style(style_analysis)
        
        # Infer personality type
        personality_type = self._infer_personality_type(personality_analysis, detected_style)
        
        # Identify cultural context
        cultural_contexts = self._identify_cultural_contexts(cultural_analysis)
        
        # Analyze channel preferences (would integrate with interaction history)
        preferred_channels = await self._infer_channel_preferences(user_id)
        
        # Calculate confidence score
        confidence = self._calculate_analysis_confidence(
            style_analysis, personality_analysis, cultural_analysis, len(text_samples)
        )
        
        # Create personality profile
        profile = PersonalityProfile(
            user_id=user_id,
            personality_type=personality_type,
            communication_style=detected_style,
            cultural_context=cultural_contexts,
            preferred_channels=preferred_channels,
            communication_preferences={
                "formality_level": tone_analysis.get("formality", 0.5),
                "directness_level": style_analysis.get("directness_score", 0.5),
                "emotional_expressiveness": tone_analysis.get("emotional_score", 0.5),
                "detail_orientation": style_analysis.get("detail_score", 0.5)
            },
            confidence_score=confidence,
            behavioral_indicators={
                "avg_sentence_length": self._calculate_avg_sentence_length(combined_text),
                "vocabulary_complexity": self._calculate_vocabulary_complexity(combined_text),
                "punctuation_patterns": self._analyze_punctuation_patterns(combined_text),
                "emotional_markers": tone_analysis.get("emotional_markers", [])
            }
        )
        
        # Save analysis
        analysis = CommunicationAnalysis(
            analysis_id=f"analysis_{user_id}_{int(datetime.now().timestamp())}",
            user_id=user_id,
            sample_text=combined_text[:1000],  # Store first 1000 chars
            detected_style=detected_style,
            tone_analysis=tone_analysis,
            formality_level=tone_analysis.get("formality", 0.5),
            emotional_indicators=tone_analysis.get("emotional_indicators", {}),
            complexity_metrics=style_analysis,
            cultural_indicators=list(cultural_analysis.keys()),
            confidence=confidence
        )
        
        await self._save_personality_profile(profile)
        await self._save_communication_analysis(analysis)
        
        logger.info(f"Analyzed communication style for {user_id}: {detected_style.value} ({confidence:.1%} confidence)")
        return profile

    async def get_communication_recommendations(self, user_id: str, target_id: str,
                                             context: str = "general",
                                             channel: CommunicationChannel = None) -> CommunicationRecommendation:
        """
        Get personalized communication recommendations
        
        Args:
            user_id: User requesting recommendations
            target_id: Target person to communicate with
            context: Communication context (meeting, email, feedback, etc.)
            channel: Preferred communication channel
            
        Returns:
            Detailed communication recommendations
        """
        # Get personality profiles
        user_profile = await self.get_personality_profile(user_id)
        target_profile = await self.get_personality_profile(target_id)
        
        if not target_profile:
            # Create default profile for unknown target
            target_profile = PersonalityProfile(
                user_id=target_id,
                personality_type=PersonalityType.ISFJ,  # Default to common, diplomatic type
                communication_style=CommunicationStyle.DIPLOMATIC
            )
        
        # Determine optimal communication approach
        recommended_style = self._determine_optimal_style(
            user_profile.communication_style if user_profile else CommunicationStyle.DIPLOMATIC,
            target_profile.communication_style,
            context
        )
        
        # Determine appropriate tone
        suggested_tone = self._determine_appropriate_tone(context, target_profile)
        
        # Determine best channel
        preferred_channel = channel or self._determine_optimal_channel(
            context, target_profile.preferred_channels if target_profile else []
        )
        
        # Generate adaptation strategies
        adaptation_strategies = self._get_adaptation_strategies(
            user_profile.communication_style if user_profile else CommunicationStyle.DIPLOMATIC,
            recommended_style
        )
        
        # Create message structure recommendations
        message_structure = self._create_message_structure(
            recommended_style, suggested_tone, context
        )
        
        # Generate key points and considerations
        key_points = self._generate_key_points(context, recommended_style)
        things_to_avoid = self._generate_things_to_avoid(target_profile, context)
        cultural_considerations = self._generate_cultural_considerations(target_profile)
        example_phrases = self._generate_example_phrases(recommended_style, context)
        
        # Calculate recommendation confidence
        confidence = self._calculate_recommendation_confidence(
            user_profile, target_profile, context
        )
        
        recommendation = CommunicationRecommendation(
            recommendation_id=f"rec_{user_id}_{target_id}_{int(datetime.now().timestamp())}",
            user_id=user_id,
            target_id=target_id,
            context=context,
            recommended_style=recommended_style,
            suggested_tone=suggested_tone,
            preferred_channel=preferred_channel,
            message_structure=message_structure,
            key_points=key_points,
            things_to_avoid=things_to_avoid,
            cultural_considerations=cultural_considerations,
            example_phrases=example_phrases,
            confidence=confidence
        )
        
        await self._save_communication_recommendation(recommendation)
        
        logger.info(f"Generated communication recommendations for {user_id} → {target_id}")
        return recommendation

    async def adapt_message(self, original_message: str, source_style: CommunicationStyle,
                          target_style: CommunicationStyle) -> str:
        """
        Adapt a message from one communication style to another
        
        Args:
            original_message: Original message text
            source_style: Current communication style
            target_style: Target communication style
            
        Returns:
            Adapted message
        """
        if source_style == target_style:
            return original_message
        
        # Find appropriate adaptation rule
        adaptation_rule = self._find_adaptation_rule(source_style, target_style)
        
        if not adaptation_rule:
            logger.warning(f"No adaptation rule found for {source_style.value} → {target_style.value}")
            return original_message
        
        adapted_message = original_message
        
        # Apply tone adjustments
        for original_phrase, replacement in adaptation_rule.tone_adjustments.items():
            adapted_message = re.sub(
                r'\b' + re.escape(original_phrase) + r'\b',
                replacement,
                adapted_message,
                flags=re.IGNORECASE
            )
        
        # Apply structural changes based on target style
        adapted_message = self._apply_structural_adaptations(
            adapted_message, source_style, target_style
        )
        
        logger.info(f"Adapted message from {source_style.value} to {target_style.value}")
        return adapted_message

    async def _analyze_style_patterns(self, text: str) -> Dict[str, float]:
        """Analyze communication style patterns in text"""
        words = text.lower().split()
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        analysis = {}
        
        # Calculate directness score
        direct_indicators = ["must", "need", "will", "should", "immediately", "now"]
        diplomatic_indicators = ["perhaps", "might", "could", "suggest", "consider", "possibly"]
        
        direct_count = sum(1 for word in words if word in direct_indicators)
        diplomatic_count = sum(1 for word in words if word in diplomatic_indicators)
        
        total_indicators = direct_count + diplomatic_count
        if total_indicators > 0:
            analysis["directness_score"] = direct_count / total_indicators
        else:
            analysis["directness_score"] = 0.5
        
        # Calculate detail orientation
        detail_indicators = ["specifically", "detailed", "exactly", "precise", "thorough"]
        detail_count = sum(1 for word in words if word in detail_indicators)
        analysis["detail_score"] = min(detail_count / max(len(words), 1) * 100, 1.0)
        
        # Calculate sentence complexity
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            analysis["complexity_score"] = min(avg_sentence_length / 20, 1.0)  # Normalize to 0-1
        else:
            analysis["complexity_score"] = 0.0
        
        # Calculate formality score
        formal_indicators = ["furthermore", "therefore", "however", "consequently", "regarding"]
        informal_indicators = ["yeah", "okay", "cool", "awesome", "hey", "gonna"]
        
        formal_count = sum(1 for word in words if word in formal_indicators)
        informal_count = sum(1 for word in words if word in informal_indicators)
        
        total_formality_indicators = formal_count + informal_count
        if total_formality_indicators > 0:
            analysis["formality_score"] = formal_count / total_formality_indicators
        else:
            analysis["formality_score"] = 0.5
        
        return analysis

    async def _analyze_personality_indicators(self, text: str) -> Dict[str, float]:
        """Analyze personality type indicators in text"""
        words = text.lower().split()
        word_count = len(words)
        
        personality_scores = {}
        
        for personality_type, indicators in self.personality_indicators.items():
            score = 0.0
            
            # Check vocabulary indicators
            vocab_matches = sum(1 for word in words if word in indicators.get("vocabulary", []))
            score += (vocab_matches / word_count) * 100 if word_count > 0 else 0
            
            # Check pattern indicators (simplified)
            for pattern in indicators.get("patterns", []):
                if pattern.replace(" ", "").lower() in text.lower().replace(" ", ""):
                    score += 0.1
            
            personality_scores[personality_type] = min(score, 1.0)
        
        return personality_scores

    async def _analyze_cultural_patterns(self, text: str) -> Dict[str, float]:
        """Analyze cultural communication patterns"""
        words = text.lower().split()
        cultural_scores = {}
        
        for cultural_context, patterns in self.cultural_patterns.items():
            score = 0.0
            
            # Check cultural indicators
            indicators = patterns.get("indicators", [])
            indicator_matches = sum(1 for word in words if word in indicators)
            
            if indicator_matches > 0:
                score = min(indicator_matches / len(words) * 100, 1.0)
            
            cultural_scores[cultural_context] = score
        
        return cultural_scores

    async def _analyze_tone_patterns(self, text: str) -> Dict[str, Any]:
        """Analyze tone and emotional patterns"""
        words = text.lower().split()
        
        # Emotional indicators
        positive_emotions = ["happy", "excited", "love", "amazing", "fantastic", "great"]
        negative_emotions = ["sad", "angry", "frustrated", "disappointed", "terrible"]
        neutral_emotions = ["okay", "fine", "normal", "standard", "regular"]
        
        positive_count = sum(1 for word in words if word in positive_emotions)
        negative_count = sum(1 for word in words if word in negative_emotions)
        neutral_count = sum(1 for word in words if word in neutral_emotions)
        
        total_emotional = positive_count + negative_count + neutral_count
        
        tone_analysis = {
            "emotional_score": total_emotional / len(words) * 10 if words else 0,
            "sentiment_balance": {
                "positive": positive_count / total_emotional if total_emotional > 0 else 0,
                "negative": negative_count / total_emotional if total_emotional > 0 else 0,
                "neutral": neutral_count / total_emotional if total_emotional > 0 else 1
            },
            "emotional_markers": [],
            "formality": 0.5  # Would be calculated based on formal language patterns
        }
        
        # Add detected emotional markers
        if positive_count > 0:
            tone_analysis["emotional_markers"].append("positive")
        if negative_count > 0:
            tone_analysis["emotional_markers"].append("negative")
        
        return tone_analysis

    def _determine_primary_style(self, style_analysis: Dict[str, float]) -> CommunicationStyle:
        """Determine primary communication style from analysis"""
        directness = style_analysis.get("directness_score", 0.5)
        detail_orientation = style_analysis.get("detail_score", 0.5)
        complexity = style_analysis.get("complexity_score", 0.5)
        formality = style_analysis.get("formality_score", 0.5)
        
        # Simple decision tree for style classification
        if directness > 0.7 and complexity < 0.5:
            return CommunicationStyle.DIRECT
        elif directness < 0.3 and formality > 0.6:
            return CommunicationStyle.DIPLOMATIC
        elif detail_orientation > 0.7 and complexity > 0.6:
            return CommunicationStyle.ANALYTICAL
        elif formality < 0.3 and directness > 0.5:
            return CommunicationStyle.ASSERTIVE
        else:
            return CommunicationStyle.COLLABORATIVE

    def _infer_personality_type(self, personality_analysis: Dict[str, float], 
                              communication_style: CommunicationStyle) -> PersonalityType:
        """Infer personality type from analysis"""
        if not personality_analysis:
            # Default based on communication style
            style_defaults = {
                CommunicationStyle.DIRECT: PersonalityType.ESTJ,
                CommunicationStyle.DIPLOMATIC: PersonalityType.ISFJ,
                CommunicationStyle.ANALYTICAL: PersonalityType.INTJ,
                CommunicationStyle.EXPRESSIVE: PersonalityType.ENFP,
                CommunicationStyle.SUPPORTIVE: PersonalityType.ESFJ,
                CommunicationStyle.ASSERTIVE: PersonalityType.ENTJ,
                CommunicationStyle.COLLABORATIVE: PersonalityType.ENFJ,
                CommunicationStyle.EMPATHETIC: PersonalityType.INFP
            }
            return style_defaults.get(communication_style, PersonalityType.ISFJ)
        
        # Find highest scoring personality type
        best_match = max(personality_analysis.items(), key=lambda x: x[1])
        return PersonalityType(best_match[0])

    def _identify_cultural_contexts(self, cultural_analysis: Dict[str, float]) -> List[CulturalContext]:
        """Identify cultural contexts from analysis"""
        contexts = []
        
        for context, score in cultural_analysis.items():
            if score > 0.1:  # Threshold for cultural context identification
                contexts.append(CulturalContext(context))
        
        # Default to low context if none identified
        if not contexts:
            contexts.append(CulturalContext.LOW_CONTEXT)
        
        return contexts

    async def _infer_channel_preferences(self, user_id: str) -> List[CommunicationChannel]:
        """Infer channel preferences from interaction history"""
        # This would analyze actual interaction data
        # For now, return common defaults
        return [
            CommunicationChannel.EMAIL,
            CommunicationChannel.TEXT,
            CommunicationChannel.VIDEO_CALL
        ]

    def _calculate_analysis_confidence(self, style_analysis: Dict[str, float],
                                     personality_analysis: Dict[str, float],
                                     cultural_analysis: Dict[str, float],
                                     sample_count: int) -> float:
        """Calculate confidence in the analysis"""
        base_confidence = 0.6
        
        # Boost confidence with more samples
        sample_boost = min(sample_count * 0.1, 0.3)
        
        # Boost confidence with clear indicators
        style_clarity = max(style_analysis.values()) if style_analysis else 0
        personality_clarity = max(personality_analysis.values()) if personality_analysis else 0
        
        clarity_boost = (style_clarity + personality_clarity) * 0.1
        
        total_confidence = base_confidence + sample_boost + clarity_boost
        return min(total_confidence, 1.0)

    def _determine_optimal_style(self, user_style: CommunicationStyle,
                               target_style: CommunicationStyle,
                               context: str) -> CommunicationStyle:
        """Determine optimal communication style for the interaction"""
        
        # Context-specific adjustments
        context_preferences = {
            "feedback": CommunicationStyle.SUPPORTIVE,
            "meeting": CommunicationStyle.COLLABORATIVE,
            "urgent": CommunicationStyle.DIRECT,
            "formal": CommunicationStyle.DIPLOMATIC,
            "brainstorming": CommunicationStyle.EXPRESSIVE
        }
        
        if context in context_preferences:
            return context_preferences[context]
        
        # Default to target's preferred style with slight adaptation
        return target_style

    def _determine_appropriate_tone(self, context: str, target_profile: PersonalityProfile) -> MessageTone:
        """Determine appropriate message tone"""
        context_tones = {
            "meeting": MessageTone.PROFESSIONAL,
            "feedback": MessageTone.SUPPORTIVE,
            "urgent": MessageTone.URGENT,
            "social": MessageTone.FRIENDLY,
            "formal": MessageTone.FORMAL,
            "update": MessageTone.INFORMATIVE
        }
        
        return context_tones.get(context, MessageTone.PROFESSIONAL)

    def _determine_optimal_channel(self, context: str, 
                                 target_preferences: List[CommunicationChannel]) -> CommunicationChannel:
        """Determine optimal communication channel"""
        context_channels = {
            "urgent": CommunicationChannel.PHONE,
            "formal": CommunicationChannel.EMAIL,
            "quick": CommunicationChannel.INSTANT_MESSAGE,
            "detailed": CommunicationChannel.EMAIL,
            "personal": CommunicationChannel.IN_PERSON
        }
        
        # Prefer context-appropriate channel if target doesn't have preferences
        if not target_preferences:
            return context_channels.get(context, CommunicationChannel.EMAIL)
        
        # Try to match context with target preferences
        context_preferred = context_channels.get(context)
        if context_preferred in target_preferences:
            return context_preferred
        
        # Fall back to target's first preference
        return target_preferences[0]

    def _get_adaptation_strategies(self, source_style: CommunicationStyle,
                                 target_style: CommunicationStyle) -> List[str]:
        """Get adaptation strategies for style conversion"""
        adaptation_rule = self._find_adaptation_rule(source_style, target_style)
        
        if adaptation_rule:
            return adaptation_rule.adaptation_strategies
        
        # Default strategies
        return [
            "Mirror the recipient's communication style",
            "Adjust formality level to match context",
            "Consider cultural and personal preferences"
        ]

    def _create_message_structure(self, style: CommunicationStyle, 
                                tone: MessageTone, context: str) -> Dict[str, str]:
        """Create recommended message structure"""
        
        structures = {
            CommunicationStyle.DIRECT: {
                "opening": "Clear, direct greeting",
                "body": "Main points first, supporting details after",
                "closing": "Clear action items and next steps"
            },
            CommunicationStyle.DIPLOMATIC: {
                "opening": "Warm greeting with relationship acknowledgment",
                "body": "Context setting, gentle presentation of main points",
                "closing": "Collaborative next steps and appreciation"
            },
            CommunicationStyle.ANALYTICAL: {
                "opening": "Context and background information",
                "body": "Detailed analysis with supporting data",
                "closing": "Summary of conclusions and recommendations"
            },
            CommunicationStyle.EXPRESSIVE: {
                "opening": "Enthusiastic greeting with personal touch",
                "body": "Engaging narrative with examples and stories",
                "closing": "Inspiring call to action with positive outlook"
            }
        }
        
        return structures.get(style, structures[CommunicationStyle.DIPLOMATIC])

    def _generate_key_points(self, context: str, style: CommunicationStyle) -> List[str]:
        """Generate key points to remember for communication"""
        general_points = [
            "Be clear about your main objective",
            "Consider the recipient's perspective",
            "Choose appropriate timing for the message"
        ]
        
        style_specific = {
            CommunicationStyle.DIRECT: [
                "Get to the point quickly",
                "Use concrete language and specific examples",
                "Include clear deadlines and expectations"
            ],
            CommunicationStyle.DIPLOMATIC: [
                "Use softening language to avoid offense",
                "Acknowledge different viewpoints",
                "Build consensus and seek agreement"
            ],
            CommunicationStyle.ANALYTICAL: [
                "Provide sufficient background and context",
                "Include supporting data and evidence",
                "Present logical reasoning for conclusions"
            ]
        }
        
        return general_points + style_specific.get(style, [])

    def _generate_things_to_avoid(self, target_profile: PersonalityProfile, context: str) -> List[str]:
        """Generate things to avoid in communication"""
        avoid_list = ["Being overly pushy or demanding"]
        
        if target_profile:
            if target_profile.communication_style == CommunicationStyle.DIPLOMATIC:
                avoid_list.extend([
                    "Being too direct or blunt",
                    "Ignoring social pleasantries",
                    "Creating confrontational situations"
                ])
            elif target_profile.communication_style == CommunicationStyle.ANALYTICAL:
                avoid_list.extend([
                    "Making unsupported claims",
                    "Rushing to conclusions",
                    "Omitting important details"
                ])
        
        return avoid_list

    def _generate_cultural_considerations(self, target_profile: PersonalityProfile) -> List[str]:
        """Generate cultural considerations"""
        considerations = []
        
        if target_profile and target_profile.cultural_context:
            for context in target_profile.cultural_context:
                if context == CulturalContext.HIGH_CONTEXT:
                    considerations.append("Allow for indirect communication and reading between the lines")
                elif context == CulturalContext.HIERARCHICAL:
                    considerations.append("Show appropriate respect for status and authority")
                elif context == CulturalContext.COLLECTIVISTIC:
                    considerations.append("Consider group harmony and collective decision-making")
        
        if not considerations:
            considerations.append("Be respectful of cultural differences in communication style")
        
        return considerations

    def _generate_example_phrases(self, style: CommunicationStyle, context: str) -> List[str]:
        """Generate example phrases for the communication style"""
        
        phrase_bank = {
            CommunicationStyle.DIRECT: [
                "I need you to...",
                "The bottom line is...",
                "Here's what we need to do:",
                "To be clear..."
            ],
            CommunicationStyle.DIPLOMATIC: [
                "I was wondering if we might consider...",
                "Perhaps we could explore...",
                "I'd appreciate your thoughts on...",
                "It might be helpful if..."
            ],
            CommunicationStyle.SUPPORTIVE: [
                "I understand your perspective...",
                "You've done great work on...",
                "I'm here to support you with...",
                "How can I help you succeed?"
            ],
            CommunicationStyle.ANALYTICAL: [
                "Based on the data...",
                "The evidence suggests...",
                "After careful analysis...",
                "The research indicates..."
            ]
        }
        
        return phrase_bank.get(style, phrase_bank[CommunicationStyle.DIPLOMATIC])

    def _calculate_recommendation_confidence(self, user_profile: Optional[PersonalityProfile],
                                           target_profile: Optional[PersonalityProfile],
                                           context: str) -> float:
        """Calculate confidence in recommendations"""
        base_confidence = 0.6
        
        if user_profile and user_profile.confidence_score > 0:
            base_confidence += user_profile.confidence_score * 0.2
        
        if target_profile and target_profile.confidence_score > 0:
            base_confidence += target_profile.confidence_score * 0.2
        
        return min(base_confidence, 1.0)

    def _find_adaptation_rule(self, source_style: CommunicationStyle,
                            target_style: CommunicationStyle) -> Optional[AdaptationRule]:
        """Find adaptation rule for style conversion"""
        for rule in self.adaptation_rules:
            if rule.source_style == source_style and rule.target_style == target_style:
                return rule
        return None

    def _apply_structural_adaptations(self, message: str, source_style: CommunicationStyle,
                                    target_style: CommunicationStyle) -> str:
        """Apply structural adaptations to message"""
        # This would implement more sophisticated structural changes
        # For now, return the tone-adjusted message
        return message

    def _calculate_avg_sentence_length(self, text: str) -> float:
        """Calculate average sentence length"""
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if not sentences:
            return 0.0
        
        total_words = sum(len(s.split()) for s in sentences)
        return total_words / len(sentences)

    def _calculate_vocabulary_complexity(self, text: str) -> float:
        """Calculate vocabulary complexity score"""
        words = text.lower().split()
        if not words:
            return 0.0
        
        # Simple complexity based on average word length
        avg_word_length = sum(len(word) for word in words) / len(words)
        return min(avg_word_length / 10, 1.0)  # Normalize to 0-1

    def _analyze_punctuation_patterns(self, text: str) -> Dict[str, int]:
        """Analyze punctuation usage patterns"""
        punctuation_counts = {
            "exclamation": text.count("!"),
            "question": text.count("?"),
            "ellipsis": text.count("..."),
            "comma": text.count(","),
            "semicolon": text.count(";")
        }
        return punctuation_counts

    async def get_personality_profile(self, user_id: str) -> Optional[PersonalityProfile]:
        """Get user's personality profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, personality_type, communication_style, cultural_context,
                   preferred_channels, communication_preferences, assessed_date,
                   confidence_score, behavioral_indicators
            FROM personality_profiles
            WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return PersonalityProfile(
            user_id=row[0],
            personality_type=PersonalityType(row[1]),
            communication_style=CommunicationStyle(row[2]),
            cultural_context=[CulturalContext(c) for c in json.loads(row[3])] if row[3] else [],
            preferred_channels=[CommunicationChannel(c) for c in json.loads(row[4])] if row[4] else [],
            communication_preferences=json.loads(row[5]) if row[5] else {},
            assessed_date=datetime.fromisoformat(row[6]),
            confidence_score=row[7],
            behavioral_indicators=json.loads(row[8]) if row[8] else {}
        )

    async def _save_personality_profile(self, profile: PersonalityProfile):
        """Save personality profile to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO personality_profiles
            (user_id, personality_type, communication_style, cultural_context,
             preferred_channels, communication_preferences, assessed_date,
             confidence_score, behavioral_indicators)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (profile.user_id, profile.personality_type.value, profile.communication_style.value,
              json.dumps([c.value for c in profile.cultural_context]),
              json.dumps([c.value for c in profile.preferred_channels]),
              json.dumps(profile.communication_preferences), profile.assessed_date,
              profile.confidence_score, json.dumps(profile.behavioral_indicators)))
        
        conn.commit()
        conn.close()

    async def _save_communication_analysis(self, analysis: CommunicationAnalysis):
        """Save communication analysis to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO communication_analyses
            (analysis_id, user_id, sample_text, detected_style, tone_analysis,
             formality_level, emotional_indicators, complexity_metrics,
             cultural_indicators, confidence, analyzed_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (analysis.analysis_id, analysis.user_id, analysis.sample_text,
              analysis.detected_style.value, json.dumps(analysis.tone_analysis),
              analysis.formality_level, json.dumps(analysis.emotional_indicators),
              json.dumps(analysis.complexity_metrics), json.dumps(analysis.cultural_indicators),
              analysis.confidence, analysis.analyzed_date))
        
        conn.commit()
        conn.close()

    async def _save_communication_recommendation(self, recommendation: CommunicationRecommendation):
        """Save communication recommendation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO communication_recommendations
            (recommendation_id, user_id, target_id, context, recommended_style,
             suggested_tone, preferred_channel, message_structure, key_points,
             things_to_avoid, cultural_considerations, example_phrases,
             confidence, generated_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (recommendation.recommendation_id, recommendation.user_id, recommendation.target_id,
              recommendation.context, recommendation.recommended_style.value,
              recommendation.suggested_tone.value, recommendation.preferred_channel.value,
              json.dumps(recommendation.message_structure), json.dumps(recommendation.key_points),
              json.dumps(recommendation.things_to_avoid), json.dumps(recommendation.cultural_considerations),
              json.dumps(recommendation.example_phrases), recommendation.confidence,
              recommendation.generated_date))
        
        conn.commit()
        conn.close()

async def demo_communication_style_adaptation():
    """Demonstrate communication style adaptation"""
    adapter = CommunicationStyleAdapter()
    
    print("=== Communication Style Adaptation Demo ===")
    
    # Sample text for analysis
    text_samples = [
        "We need to implement these changes immediately. The deadline is firm and there's no room for delays. Here are the specific requirements that must be met.",
        "I'll handle the technical implementation while you focus on the user interface. We should coordinate regularly to ensure everything aligns.",
        "The data clearly shows a 23% improvement in performance. Based on this analysis, I recommend we proceed with the proposed solution."
    ]
    
    print("Analyzing communication style from text samples...")
    
    # Analyze communication style
    profile = await adapter.analyze_communication_style("user_alex", text_samples)
    
    print(f"\n=== Communication Style Analysis ===")
    print(f"Personality Type: {profile.personality_type.value.upper()}")
    print(f"Communication Style: {profile.communication_style.value.replace('_', ' ').title()}")
    print(f"Cultural Context: {', '.join(c.value for c in profile.cultural_context)}")
    print(f"Analysis Confidence: {profile.confidence_score:.1%}")
    
    print(f"\nCommunication Preferences:")
    for key, value in profile.communication_preferences.items():
        if isinstance(value, float):
            print(f"  {key.replace('_', ' ').title()}: {value:.2f}")
        else:
            print(f"  {key.replace('_', ' ').title()}: {value}")
    
    print(f"\nBehavioral Indicators:")
    for key, value in profile.behavioral_indicators.items():
        if isinstance(value, (int, float)):
            print(f"  {key.replace('_', ' ').title()}: {value:.2f}")
        else:
            print(f"  {key.replace('_', ' ').title()}: {value}")
    
    # Create a target profile for demonstration
    target_profile = PersonalityProfile(
        user_id="user_sarah",
        personality_type=PersonalityType.INFP,
        communication_style=CommunicationStyle.DIPLOMATIC,
        cultural_context=[CulturalContext.HIGH_CONTEXT],
        preferred_channels=[CommunicationChannel.EMAIL, CommunicationChannel.IN_PERSON]
    )
    await adapter._save_personality_profile(target_profile)
    
    # Get communication recommendations
    recommendations = await adapter.get_communication_recommendations(
        user_id="user_alex",
        target_id="user_sarah",
        context="feedback",
        channel=CommunicationChannel.EMAIL
    )
    
    print(f"\n=== Communication Recommendations ===")
    print(f"Context: Providing feedback to Sarah")
    print(f"Recommended Style: {recommendations.recommended_style.value.replace('_', ' ').title()}")
    print(f"Suggested Tone: {recommendations.suggested_tone.value.replace('_', ' ').title()}")
    print(f"Preferred Channel: {recommendations.preferred_channel.value.replace('_', ' ').title()}")
    print(f"Confidence: {recommendations.confidence:.1%}")
    
    print(f"\nMessage Structure:")
    for section, description in recommendations.message_structure.items():
        print(f"  {section.title()}: {description}")
    
    print(f"\nKey Points:")
    for point in recommendations.key_points:
        print(f"  • {point}")
    
    print(f"\nThings to Avoid:")
    for avoid in recommendations.things_to_avoid:
        print(f"  • {avoid}")
    
    print(f"\nExample Phrases:")
    for phrase in recommendations.example_phrases:
        print(f"  • \"{phrase}\"")
    
    # Demonstrate message adaptation
    original_message = "You need to fix this issue immediately. The current approach is wrong and we must change it now."
    
    adapted_message = await adapter.adapt_message(
        original_message,
        CommunicationStyle.DIRECT,
        CommunicationStyle.DIPLOMATIC
    )
    
    print(f"\n=== Message Adaptation Demo ===")
    print(f"Original (Direct): \"{original_message}\"")
    print(f"Adapted (Diplomatic): \"{adapted_message}\"")

if __name__ == "__main__":
    asyncio.run(demo_communication_style_adaptation())