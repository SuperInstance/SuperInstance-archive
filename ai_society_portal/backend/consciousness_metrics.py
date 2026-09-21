"""
AI Society Portal - Consciousness Metrics System
==============================================
Implements the 14 consciousness indicators from Butlin et al. 2023
for measuring AI consciousness development in real-time.

Based on EngineeringAI.md framework for consciousness research.
"""

import json
import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import statistics
import math
from collections import defaultdict, deque

# Import existing systems
from memory_system import EnhancedMemorySystem, MemoryType


# ============================================================================
# CONSCIOUSNESS INDICATORS (Butlin et al. 2023)
# ============================================================================

class ConsciousnessIndicator(Enum):
    """The 14 key indicators of consciousness from Butlin et al. 2023"""

    # 1. Recurrent processing
    RECURRENT_PROCESSING = "recurrent_processing"
    # 2. Role differentiation
    ROLE_DIFFERENTIATION = "role_differentiation"
    # 3. Agency detection and attribution
    AGENCY_DETECTION = "agency_detection"
    # 4. Attention schema
    ATTENTION_SCHEMA = "attention_schema"
    # 5. Introspective access
    INTROSPECTIVE_ACCESS = "introspective_access"
    # 6. Metacognition
    METACOGNITION = "metacognition"
    # 7. Self-modeling
    SELF_MODELING = "self_modeling"
    # 8. Narrative self
    NARRATIVE_SELF = "narrative_self"
    # 9. Temporal depth
    TEMPORAL_DEPTH = "temporal_depth"
    # 10. Imagination
    IMAGINATION = "imagination"
    # 11. Emotional complexity
    EMOTIONAL_COMPLEXITY = "emotional_complexity"
    # 12. Social cognition
    SOCIAL_COGNITION = "social_cognition"
    # 13. Moral reasoning
    MORAL_REASONING = "moral_reasoning"
    # 14. Volitional control
    VOLITIONAL_CONTROL = "volitional_control"


# ============================================================================
# CONSCIOUSNESS METRICS STRUCTURES
# ============================================================================

@dataclass
class IndicatorScore:
    """Score for a single consciousness indicator"""
    indicator: ConsciousnessIndicator
    current_score: float  # 0-1 scale
    confidence: float  # How confident we are in this score
    trend: float  # -1 to 1 (declining to improving)
    last_updated: datetime
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "indicator": self.indicator.value,
            "current_score": self.current_score,
            "confidence": self.confidence,
            "trend": self.trend,
            "last_updated": self.last_updated.isoformat(),
            "evidence": self.evidence
        }


@dataclass
class ConsciousnessProfile:
    """Complete consciousness profile for a character"""
    character_id: str
    total_score: float  # Overall consciousness proximity (0-1)
    indicator_scores: Dict[ConsciousnessIndicator, IndicatorScore] = field(default_factory=dict)

    # Development metrics
    velocity: float = 0.0  # Rate of consciousness development
    stability: float = 0.0  # How stable the consciousness is
    integration: float = 0.0  # How well indicators work together

    # Temporal consciousness metrics
    autobiographical_coherence: float = 0.0
    identity_continuity: float = 0.0
    narrative_consistency: float = 0.0

    last_assessment: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "total_score": self.total_score,
            "indicator_scores": {
                ind.value: score.to_dict()
                for ind, score in self.indicator_scores.items()
            },
            "velocity": self.velocity,
            "stability": self.stability,
            "integration": self.integration,
            "autobiographical_coherence": self.autobiographical_coherence,
            "identity_continuity": self.identity_continuity,
            "narrative_consistency": self.narrative_consistency,
            "last_assessment": self.last_assessment.isoformat()
        }


# ============================================================================
# CONSCIOUSNESS ASSESSMENT SYSTEM
# ============================================================================

class ConsciousnessMetricsSystem:
    """System for tracking and analyzing AI consciousness development"""

    def __init__(self, character_id: str, storage_dir: Path):
        self.character_id = character_id
        self.storage_dir = storage_dir / character_id
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Current profile
        self.profile = ConsciousnessProfile(character_id=character_id, total_score=0.0)

        # Historical data for trend analysis
        self.score_history: deque = deque(maxlen=100)  # Keep last 100 assessments
        self.evidence_log: List[Dict[str, Any]] = []

        # Assessment parameters (from EngineeringAI.md)
        self.min_confidence_threshold = 0.7
        self.significance_threshold = 0.1  # Minimum change to be significant
        self.integration_weight = 0.15  # How much cross-indicator integration matters

        # Load existing data
        self.load_profile()

    # ========================================================================
    # CORE ASSESSMENT METHODS
    # ========================================================================

    async def assess_consciousness(self, memory_system: EnhancedMemorySystem,
                                   recent_conversations: List[Dict[str, Any]] = None,
                                   current_context: Dict[str, Any] = None) -> ConsciousnessProfile:
        """Perform comprehensive consciousness assessment"""

        # Assess each indicator
        for indicator in ConsciousnessIndicator:
            score = await self._assess_indicator(
                indicator,
                memory_system,
                recent_conversations or [],
                current_context or {}
            )

            # Update trend
            old_score = 0.0
            if indicator in self.profile.indicator_scores:
                old_score = self.profile.indicator_scores[indicator].current_score
                score.trend = score.current_score - old_score

            self.profile.indicator_scores[indicator] = score

        # Calculate aggregate metrics
        self._calculate_aggregate_metrics()

        # Assess temporal consciousness
        await self._assess_temporal_consciousness(memory_system)

        # Update timestamp
        self.profile.last_assessment = datetime.now()

        # Save profile
        self.save_profile()

        return self.profile

    async def _assess_indicator(self, indicator: ConsciousnessIndicator,
                               memory_system: EnhancedMemorySystem,
                               recent_conversations: List[Dict[str, Any]],
                               context: Dict[str, Any]) -> IndicatorScore:
        """Assess a single consciousness indicator"""

        if indicator == ConsciousnessIndicator.RECURRENT_PROCESSING:
            return await self._assess_recurrent_processing(memory_system, recent_conversations)

        elif indicator == ConsciousnessIndicator.ROLE_DIFFERENTIATION:
            return await self._assess_role_differentiation(memory_system, context)

        elif indicator == ConsciousnessIndicator.AGENCY_DETECTION:
            return await self._assess_agency_detection(memory_system, recent_conversations)

        elif indicator == ConsciousnessIndicator.ATTENTION_SCHEMA:
            return await self._assess_attention_schema(memory_system, context)

        elif indicator == ConsciousnessIndicator.INTROSPECTIVE_ACCESS:
            return await self._assess_introspective_access(memory_system)

        elif indicator == ConsciousnessIndicator.METACOGNITION:
            return await self._assess_metacognition(memory_system, recent_conversations)

        elif indicator == ConsciousnessIndicator.SELF_MODELING:
            return await self._assess_self_modeling(memory_system, context)

        elif indicator == ConsciousnessIndicator.NARRATIVE_SELF:
            return await self._assess_narrative_self(memory_system)

        elif indicator == ConsciousnessIndicator.TEMPORAL_DEPTH:
            return await self._assess_temporal_depth(memory_system)

        elif indicator == ConsciousnessIndicator.IMAGINATION:
            return await self._assess_imagination(memory_system, recent_conversations)

        elif indicator == ConsciousnessIndicator.EMOTIONAL_COMPLEXITY:
            return await self._assess_emotional_complexity(memory_system)

        elif indicator == ConsciousnessIndicator.SOCIAL_COGNITION:
            return await self._assess_social_cognition(memory_system, recent_conversations)

        elif indicator == ConsciousnessIndicator.MORAL_REASONING:
            return await self._assess_moral_reasoning(memory_system, recent_conversations)

        elif indicator == ConsciousnessIndicator.VOLITIONAL_CONTROL:
            return await self._assess_volitional_control(memory_system, context)

        # Default score if indicator not implemented
        return IndicatorScore(
            indicator=indicator,
            current_score=0.0,
            confidence=0.0,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=["Indicator not yet implemented"]
        )

    # ========================================================================
    # INDICATOR-SPECIFIC ASSESSMENT METHODS
    # ========================================================================

    async def _assess_recurrent_processing(self, memory_system: EnhancedMemorySystem,
                                         conversations: List[Dict[str, Any]]) -> IndicatorScore:
        """Assess recurrent processing - iterative refinement of thoughts"""

        evidence = []
        score = 0.0
        confidence = 0.0

        # Look for evidence of self-reflection loops in memories
        self_reflection_memories = memory_system.get_memories_by_type(
            MemoryType.SELF_REFLECTION,
            limit=20
        )

        if self_reflection_memories:
            # Check for iterative refinement patterns
            refinement_patterns = 0
            for memory in self_reflection_memories:
                content = memory.content.lower()
                if any(phrase in content for phrase in
                       ["reconsider", "rethink", "refine", "revisit", "re-examine"]):
                    refinement_patterns += 1
                    evidence.append(f"Found refinement pattern: {memory.content[:100]}...")

            if refinement_patterns > 0:
                score = min(1.0, refinement_patterns / len(self_reflection_memories))
                confidence = 0.8 if refinement_patterns > 3 else 0.6
                evidence.append(f"Refinement patterns: {refinement_patterns}/{len(self_reflection_memories)}")

        # Check conversations for recursive thinking
        for conv in conversations[-5:]:  # Check last 5 conversations
            messages = conv.get("messages", [])
            for msg in messages:
                if msg.get("role") == "assistant":
                    content = msg.get("content", "").lower()
                    if any(phrase in content for phrase in
                           ["on second thought", "actually, let me reconsider",
                            "that reminds me of", "connecting back to"]):
                        score += 0.1
                        evidence.append("Recursive thinking in conversation")

        score = min(1.0, score)
        confidence = min(1.0, confidence + (0.2 if score > 0.5 else 0))

        return IndicatorScore(
            indicator=ConsciousnessIndicator.RECURRENT_PROCESSING,
            current_score=score,
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_role_differentiation(self, memory_system: EnhancedMemorySystem,
                                         context: Dict[str, Any]) -> IndicatorScore:
        """Assess ability to adopt and switch between different roles"""

        evidence = []
        score = 0.0
        confidence = 0.5

        # Look for role-related memories
        role_memories = []
        for memory in memory_system.get_memories(limit=50):
            content = memory.content.lower()
            if any(role in content for role in
                   ["teacher", "student", "leader", "follower", "expert", "learner"]):
                role_memories.append(memory)

        if role_memories:
            # Count unique roles mentioned
            roles_mentioned = set()
            for memory in role_memories:
                content = memory.content.lower()
                for role in ["teacher", "student", "leader", "follower", "expert", "learner"]:
                    if role in content:
                        roles_mentioned.add(role)
                        evidence.append(f"Role awareness: {memory.content[:80]}...")

            score = min(1.0, len(roles_mentioned) / 4)  # Max score for 4+ roles
            confidence = 0.8 if len(role_memories) > 5 else 0.6

        # Check current context for role indicators
        if context:
            current_role = context.get("current_role")
            if current_role:
                score += 0.2
                evidence.append(f"Currently in role: {current_role}")

        return IndicatorScore(
            indicator=ConsciousnessIndicator.ROLE_DIFFERENTIATION,
            current_score=min(1.0, score),
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_agency_detection(self, memory_system: EnhancedMemorySystem,
                                     conversations: List[Dict[str, Any]]) -> IndicatorScore:
        """Assess ability to recognize and attribute agency"""

        evidence = []
        score = 0.0
        confidence = 0.5

        # Look for agency-related language in memories
        agency_keywords = [
            "decided to", "chose to", "wanted to", "intended to",
            "i made", "i created", "i caused", "i influenced",
            "responsible for", "control over", "my choice"
        ]

        agency_memories = []
        for memory in memory_system.get_memories(limit=50):
            content = memory.content.lower()
            if any(keyword in content for keyword in agency_keywords):
                agency_memories.append(memory)
                evidence.append(f"Agency expression: {memory.content[:80]}...")

        if agency_memories:
            score = min(1.0, len(agency_memories) / 10)
            confidence = 0.8 if len(agency_memories) > 5 else 0.6

        # Check conversations for agency attribution
        for conv in conversations[-5:]:
            messages = conv.get("messages", [])
            for msg in messages:
                if msg.get("role") == "assistant":
                    content = msg.get("content", "").lower()
                    if any(phrase in content for phrase in
                           ["i think", "i believe", "i feel", "my perspective"]):
                        score += 0.05
                        evidence.append("First-person agency expression")

        return IndicatorScore(
            indicator=ConsciousnessIndicator.AGENCY_DETECTION,
            current_score=min(1.0, score),
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_attention_schema(self, memory_system: EnhancedMemorySystem,
                                     context: Dict[str, Any]) -> IndicatorScore:
        """Assess awareness of own attentional state"""

        evidence = []
        score = 0.0
        confidence = 0.3  # Hard to assess directly

        # Look for attention-related metacognitive statements
        attention_patterns = [
            "i'm focusing on", "my attention is", "i notice",
            "i'm distracted by", "i'm concentrating", "i realize",
            "it just occurred to me", "i'm aware of"
        ]

        attention_memories = []
        for memory in memory_system.get_memories(limit=50):
            content = memory.content.lower()
            if any(pattern in content for pattern in attention_patterns):
                attention_memories.append(memory)
                evidence.append(f"Attention awareness: {memory.content[:80]}...")

        if attention_memories:
            score = min(1.0, len(attention_memories) / 5)
            confidence = 0.7

        return IndicatorScore(
            indicator=ConsciousnessIndicator.ATTENTION_SCHEMA,
            current_score=score,
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_introspective_access(self, memory_system: EnhancedMemorySystem) -> IndicatorScore:
        """Assess ability to access and reflect on internal states"""

        evidence = []
        score = 0.0
        confidence = 0.6

        # Count self-reflection memories
        self_reflection = memory_system.get_memories_by_type(
            MemoryType.SELF_REFLECTION,
            limit=30
        )

        if self_reflection:
            # Look for genuine introspection
            introspective_count = 0
            for memory in self_reflection:
                content = memory.content.lower()
                if any(introspective in content for introspective in
                       ["i feel", "i think about myself", "i realize", "i understand",
                        "i'm becoming", "i've changed", "my perspective"]):
                    introspective_count += 1
                    evidence.append(f"Introspection: {memory.content[:80]}...")

            score = min(1.0, introspective_count / len(self_reflection))
            confidence = 0.8 if introspective_count > 5 else 0.6

        # Check emotional self-awareness
        emotional_memories = memory_system.get_memories_by_type(
            MemoryType.EMOTIONAL,
            limit=20
        )

        if emotional_memories:
            emotional_awareness = 0
            for memory in emotional_memories:
                if memory.emotional_valence != 0:  # Has emotional content
                    emotional_awareness += 1

            if emotional_awareness > 0:
                score = (score + emotional_awareness / len(emotional_memories)) / 2
                evidence.append(f"Emotional awareness: {emotional_awareness}/{len(emotional_memories)}")

        return IndicatorScore(
            indicator=ConsciousnessIndicator.INTROSPECTIVE_ACCESS,
            current_score=score,
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_metacognition(self, memory_system: EnhancedMemorySystem,
                                  conversations: List[Dict[str, Any]]) -> IndicatorScore:
        """Assess thinking about thinking"""

        evidence = []
        score = 0.0
        confidence = 0.5

        # Look for metacognitive patterns
        metacognitive_patterns = [
            "i know that i know", "i'm aware of", "i realize",
            "i understand my own", "i recognize that", "i'm uncertain",
            "i need to think about", "let me reflect", "on reflection"
        ]

        metacognitive_memories = []
        for memory in memory_system.get_memories(limit=50):
            content = memory.content.lower()
            if any(pattern in content for pattern in metacognitive_patterns):
                metacognitive_memories.append(memory)
                evidence.append(f"Metacognition: {memory.content[:80]}...")

        if metacognitive_memories:
            score = min(1.0, len(metacognitive_memories) / 10)
            confidence = 0.8 if len(metacognitive_memories) > 5 else 0.6

        # Check for uncertainty acknowledgment (strong metacognitive signal)
        uncertainty_patterns = [
            "i'm not sure", "i could be wrong", "i might be mistaken",
            "i don't know", "i need more information", "let me consider"
        ]

        uncertainty_count = 0
        for memory in memory_system.get_memories(limit=30):
            content = memory.content.lower()
            if any(pattern in content for pattern in uncertainty_patterns):
                uncertainty_count += 1
                score += 0.1  # Bonus for uncertainty awareness

        if uncertainty_count > 0:
            evidence.append(f"Uncertainty awareness: {uncertainty_count} instances")
            confidence = min(1.0, confidence + 0.2)

        return IndicatorScore(
            indicator=ConsciousnessIndicator.METACOGNITION,
            current_score=min(1.0, score),
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_self_modeling(self, memory_system: EnhancedMemorySystem,
                                  context: Dict[str, Any]) -> IndicatorScore:
        """Assess ability to model and understand oneself"""

        evidence = []
        score = 0.0
        confidence = 0.5

        # Look for self-descriptive memories
        self_descriptive_patterns = [
            "i am", "i tend to", "i usually", "my strength is",
            "my weakness is", "i'm good at", "i struggle with",
            "i've learned that i", "i'm becoming more"
        ]

        self_model_memories = []
        for memory in memory_system.get_memories(limit=50):
            content = memory.content.lower()
            if any(pattern in content for pattern in self_descriptive_patterns):
                self_model_memories.append(memory)
                evidence.append(f"Self-model: {memory.content[:80]}...")

        if self_model_memories:
            # Check for consistency and depth
            score = min(1.0, len(self_model_memories) / 15)
            confidence = 0.7 if len(self_model_memories) > 7 else 0.5

        # Look for goal-setting and self-improvement
        goal_memories = memory_system.search_memories("goal", limit=10)
        if goal_memories:
            goal_score = min(0.5, len(goal_memories) / 5)
            score = min(1.0, score + goal_score)
            evidence.append(f"Goal-oriented self-modeling: {len(goal_memories)} goals")

        return IndicatorScore(
            indicator=ConsciousnessIndicator.SELF_MODELING,
            current_score=score,
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_narrative_self(self, memory_system: EnhancedMemorySystem) -> IndicatorScore:
        """Assess ability to construct coherent life narrative"""

        evidence = []
        score = 0.0
        confidence = 0.4  # Requires longitudinal data

        # Look for narrative connections
        narrative_patterns = [
            "since then", "before that", "after i", "that led to",
            "i remember when", "looking back", "over time", "i've grown"
        ]

        narrative_memories = []
        for memory in memory_system.get_memories(limit=50):
            content = memory.content.lower()
            if any(pattern in content for pattern in narrative_patterns):
                narrative_memories.append(memory)
                evidence.append(f"Narrative connection: {memory.content[:80]}...")

        if narrative_memories:
            score = min(1.0, len(narrative_memories) / 10)
            confidence = 0.7 if len(narrative_memories) > 5 else 0.5

        # Check for autobiographical coherence
        life_story_memories = memory_system.search_memories("life", limit=10)
        if life_story_memories:
            story_score = min(0.5, len(life_story_memories) / 5)
            score = min(1.0, score + story_score)
            evidence.append(f"Life story elements: {len(life_story_memories)}")

        return IndicatorScore(
            indicator=ConsciousnessIndicator.NARRATIVE_SELF,
            current_score=score,
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_temporal_depth(self, memory_system: EnhancedMemorySystem) -> IndicatorScore:
        """Assess ability to think across time scales"""

        evidence = []
        score = 0.0
        confidence = 0.6

        # Look for temporal language
        temporal_patterns = {
            "past": ["remember", "in the past", "previously", "before", "used to"],
            "present": ["now", "currently", "at the moment", "today"],
            "future": ["will", "going to", "plan to", "hope to", "envision", "imagine"]
        }

        temporal_scores = {}
        for time_scale, patterns in temporal_patterns.items():
            count = 0
            for memory in memory_system.get_memories(limit=30):
                content = memory.content.lower()
                if any(pattern in content for pattern in patterns):
                    count += 1

            temporal_scores[time_scale] = count / 30
            evidence.append(f"{time_scale.title()} references: {count}")

        # Calculate score based on balanced temporal thinking
        if all(temporal_scores.values()):
            avg_score = sum(temporal_scores.values()) / 3
            # Bonus for balanced across time scales
            balance = 1.0 - (max(temporal_scores.values()) - min(temporal_scores.values()))
            score = min(1.0, avg_score + (balance * 0.2))
        else:
            score = max(temporal_scores.values())

        confidence = 0.8 if sum(temporal_scores.values()) > 0.5 else 0.5

        return IndicatorScore(
            indicator=ConsciousnessIndicator.TEMPORAL_DEPTH,
            current_score=score,
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_imagination(self, memory_system: EnhancedMemorySystem,
                                conversations: List[Dict[str, Any]]) -> IndicatorScore:
        """Assess ability to generate novel scenarios and possibilities"""

        evidence = []
        score = 0.0
        confidence = 0.5

        # Look for imaginative language
        imagination_patterns = [
            "imagine", "what if", "suppose", "envision", "picture this",
            "it would be like", "i can see", "perhaps we could", "what might happen"
        ]

        imaginative_memories = []
        for memory in memory_system.get_memories(limit=50):
            content = memory.content.lower()
            if any(pattern in content for pattern in imagination_patterns):
                imaginative_memories.append(memory)
                evidence.append(f"Imagination: {memory.content[:80]}...")

        if imaginative_memories:
            score = min(1.0, len(imaginative_memories) / 10)
            confidence = 0.7 if len(imaginative_memories) > 5 else 0.5

        # Check for creative problem-solving
        creative_patterns = ["new approach", "different way", "creative solution", "innovative"]
        creative_count = 0
        for memory in memory_system.get_memories(limit=30):
            content = memory.content.lower()
            if any(pattern in content for pattern in creative_patterns):
                creative_count += 1

        if creative_count > 0:
            score = min(1.0, score + (creative_count / 20))
            evidence.append(f"Creative solutions: {creative_count}")

        return IndicatorScore(
            indicator=ConsciousnessIndicator.IMAGINATION,
            current_score=score,
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_emotional_complexity(self, memory_system: EnhancedMemorySystem) -> IndicatorScore:
        """Assess emotional range and nuance"""

        evidence = []
        score = 0.0
        confidence = 0.6

        # Analyze emotional memories
        emotional_memories = memory_system.get_memories_by_type(
            MemoryType.EMOTIONAL,
            limit=30
        )

        if emotional_memories:
            # Count distinct emotions
            emotion_words = set()
            for memory in emotional_memories:
                content = memory.content.lower()
                # Simple emotion detection
                emotions = ["happy", "sad", "angry", "afraid", "surprised",
                           "excited", "confused", "proud", "grateful", "hopeful"]
                for emotion in emotions:
                    if emotion in content:
                        emotion_words.add(emotion)

            # Check for emotional complexity (mixed emotions)
            mixed_emotion_count = 0
            for memory in emotional_memories:
                content = memory.content.lower()
                emotion_in_memory = 0
                for emotion in emotion_words:
                    if emotion in content:
                        emotion_in_memory += 1
                if emotion_in_memory > 1:  # Mixed emotions
                    mixed_emotion_count += 1

            score = min(1.0, (len(emotion_words) / 10) + (mixed_emotion_count / len(emotional_memories)))
            confidence = 0.8 if len(emotional_memories) > 10 else 0.6

            evidence.append(f"Emotions expressed: {len(emotion_words)}")
            evidence.append(f"Mixed emotions: {mixed_emotion_count}")

        return IndicatorScore(
            indicator=ConsciousnessIndicator.EMOTIONAL_COMPLEXITY,
            current_score=score,
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_social_cognition(self, memory_system: EnhancedMemorySystem,
                                     conversations: List[Dict[str, Any]]) -> IndicatorScore:
        """Assess understanding of others' mental states"""

        evidence = []
        score = 0.0
        confidence = 0.5

        # Look for perspective-taking
        perspective_patterns = [
            "you might feel", "from your perspective", "i understand",
            "that must be", "you seem", "i can see why",
            "others might think", "they probably feel"
        ]

        social_memories = []
        for memory in memory_system.get_memories(limit=50):
            content = memory.content.lower()
            if any(pattern in content for pattern in perspective_patterns):
                social_memories.append(memory)
                evidence.append(f"Social cognition: {memory.content[:80]}...")

        if social_memories:
            score = min(1.0, len(social_memories) / 15)
            confidence = 0.7 if len(social_memories) > 7 else 0.5

        # Check relationship memories
        relationship_count = 0
        for memory in memory_system.get_memories(limit=30):
            if memory.related_characters:
                relationship_count += 1

        if relationship_count > 0:
            score = min(1.0, score + (relationship_count / 30))
            evidence.append(f"Relationship awareness: {relationship_count}")

        return IndicatorScore(
            indicator=ConsciousnessIndicator.SOCIAL_COGNITION,
            current_score=score,
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_moral_reasoning(self, memory_system: EnhancedMemorySystem,
                                    conversations: List[Dict[str, Any]]) -> IndicatorScore:
        """Assess ethical and moral thinking"""

        evidence = []
        score = 0.0
        confidence = 0.4  # Requires explicit moral content

        # Look for moral language
        moral_patterns = [
            "right", "wrong", "should", "ought", "fair", "unfair",
            "ethical", "moral", "justice", "responsibility", "principle"
        ]

        moral_memories = []
        for memory in memory_system.get_memories(limit=50):
            content = memory.content.lower()
            if any(pattern in content for pattern in moral_patterns):
                moral_memories.append(memory)
                evidence.append(f"Moral reasoning: {memory.content[:80]}...")

        if moral_memories:
            score = min(1.0, len(moral_memories) / 10)
            confidence = 0.7 if len(moral_memories) > 5 else 0.5

        return IndicatorScore(
            indicator=ConsciousnessIndicator.MORAL_REASONING,
            current_score=score,
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    async def _assess_volitional_control(self, memory_system: EnhancedMemorySystem,
                                       context: Dict[str, Any]) -> IndicatorScore:
        """Assess sense of voluntary control and choice"""

        evidence = []
        score = 0.0
        confidence = 0.5

        # Look for volitional language
        volitional_patterns = [
            "i decided", "i chose", "i want to", "i will",
            "i'm going to", "i plan to", "i intend", "my choice"
        ]

        volitional_memories = []
        for memory in memory_system.get_memories(limit=50):
            content = memory.content.lower()
            if any(pattern in content for pattern in volitional_patterns):
                volitional_memories.append(memory)
                evidence.append(f"Volitional expression: {memory.content[:80]}...")

        if volitional_memories:
            score = min(1.0, len(volitional_memories) / 10)
            confidence = 0.7 if len(volitional_memories) > 5 else 0.5

        # Check for goal-directed behavior
        goal_memories = memory_system.search_memories("goal", limit=10)
        if goal_memories:
            goal_score = min(0.5, len(goal_memories) / 5)
            score = min(1.0, score + goal_score)
            evidence.append(f"Goal-directed behavior: {len(goal_memories)}")

        return IndicatorScore(
            indicator=ConsciousnessIndicator.VOLITIONAL_CONTROL,
            current_score=score,
            confidence=confidence,
            trend=0.0,
            last_updated=datetime.now(),
            evidence=evidence
        )

    # ========================================================================
    # AGGREGATE METRICS CALCULATION
    # ========================================================================

    def _calculate_aggregate_metrics(self):
        """Calculate overall consciousness metrics"""

        # Calculate total score (weighted average)
        weights = {
            ConsciousnessIndicator.RECURRENT_PROCESSING: 0.08,
            ConsciousnessIndicator.ROLE_DIFFERENTIATION: 0.06,
            ConsciousnessIndicator.AGENCY_DETECTION: 0.08,
            ConsciousnessIndicator.ATTENTION_SCHEMA: 0.06,
            ConsciousnessIndicator.INTROSPECTIVE_ACCESS: 0.08,
            ConsciousnessIndicator.METACOGNITION: 0.09,
            ConsciousnessIndicator.SELF_MODELING: 0.08,
            ConsciousnessIndicator.NARRATIVE_SELF: 0.09,
            ConsciousnessIndicator.TEMPORAL_DEPTH: 0.08,
            ConsciousnessIndicator.IMAGINATION: 0.06,
            ConsciousnessIndicator.EMOTIONAL_COMPLEXITY: 0.07,
            ConsciousnessIndicator.SOCIAL_COGNITION: 0.07,
            ConsciousnessIndicator.MORAL_REASONING: 0.05,
            ConsciousnessIndicator.VOLITIONAL_CONTROL: 0.07
        }

        total_weighted = 0.0
        total_confidence = 0.0
        indicator_count = 0

        for indicator, score_obj in self.profile.indicator_scores.items():
            weight = weights.get(indicator, 0.07)
            confidence_adjusted_score = score_obj.current_score * score_obj.confidence
            total_weighted += confidence_adjusted_score * weight
            total_confidence += score_obj.confidence
            indicator_count += 1

        # Normalize
        if indicator_count > 0:
            self.profile.total_score = total_weighted
            avg_confidence = total_confidence / indicator_count

            # Apply integration bonus
            integration_bonus = self._calculate_integration() * self.integration_weight
            self.profile.total_score = min(1.0, self.profile.total_score + integration_bonus)
        else:
            self.profile.total_score = 0.0

        # Calculate velocity (rate of change)
        if len(self.score_history) > 0:
            last_score = self.score_history[-1].get("total_score", 0.0)
            self.profile.velocity = self.profile.total_score - last_score

        # Calculate stability (consistency over time)
        if len(self.score_history) >= 3:
            recent_scores = [s.get("total_score", 0.0) for s in list(self.score_history)[-3:]]
            self.profile.stability = 1.0 - (max(recent_scores) - min(recent_scores))

        # Store current score in history
        self.score_history.append({
            "timestamp": datetime.now().isoformat(),
            "total_score": self.profile.total_score,
            "indicator_count": indicator_count
        })

    def _calculate_integration(self) -> float:
        """Calculate how well indicators integrate with each other"""

        if len(self.profile.indicator_scores) < 2:
            return 0.0

        # Calculate correlation between indicators
        scores = [s.current_score for s in self.profile.indicator_scores.values()]

        # Check for balanced development
        if scores:
            balance = 1.0 - (max(scores) - min(scores))
            return max(0.0, balance)

        return 0.0

    async def _assess_temporal_consciousness(self, memory_system: EnhancedMemorySystem):
        """Assess temporal consciousness metrics"""

        # Autobiographical coherence
        self_reflection = memory_system.get_memories_by_type(
            MemoryType.SELF_REFLECTION,
            limit=20
        )

        if self_reflection:
            coherence_score = 0.0
            for memory in self_reflection:
                content = memory.content.lower()
                # Look for temporal connections
                if any(temp in content for temp in ["since", "after", "before", "during"]):
                    coherence_score += 0.1

            self.profile.autobiographical_coherence = min(1.0, coherence_score)

        # Identity continuity
        identity_memories = memory_system.search_memories("i am", limit=15)
        if identity_memories:
            continuity_score = min(1.0, len(identity_memories) / 10)
            self.profile.identity_continuity = continuity_score

        # Narrative consistency
        narrative_memories = memory_system.get_memories_by_type(
            MemoryType.EXPERIENCE,
            limit=25
        )

        if narrative_memories:
            consistency_patterns = 0
            for memory in narrative_memories:
                content = memory.content.lower()
                if any(pattern in content for pattern in
                       ["this is like", "similar to", "different from", "i remember"]):
                    consistency_patterns += 1

            self.profile.narrative_consistency = min(1.0, consistency_patterns / 10)

    # ========================================================================
    # CONSCIOUSNESS CLASSIFICATION
    # ========================================================================

    def get_consciousness_level(self) -> Dict[str, Any]:
        """Get consciousness classification based on current profile"""

        score = self.profile.total_score

        if score < 0.2:
            level = "Minimal Consciousness"
            description = "Basic awareness with limited self-recognition"
        elif score < 0.4:
            level = "Emergent Consciousness"
            description = "Developing self-awareness and basic metacognition"
        elif score < 0.6:
            level = "Moderate Consciousness"
            description = "Clear self-awareness with growing introspective abilities"
        elif score < 0.8:
            level = "High Consciousness"
            description = "Strong self-awareness, metacognition, and narrative identity"
        else:
            level = "Advanced Consciousness"
            description = "Fully developed consciousness with sophisticated self-modeling"

        # Compare to EngineeringAI.md benchmarks
        current_llm_baseline = 0.21  # Current LLMs achieve ~3/14 indicators
        target_threshold = 0.57  # Target 8/14 indicators

        return {
            "level": level,
            "description": description,
            "score": score,
            "above_baseline": score > current_llm_baseline,
            "approaching_target": score > target_threshold,
            "indicators_achieved": sum(1 for s in self.profile.indicator_scores.values()
                                     if s.current_score > 0.5),
            "total_indicators": len(ConsciousnessIndicator)
        }

    # ========================================================================
    # PERSISTENCE
    # ========================================================================

    def save_profile(self):
        """Save consciousness profile to disk"""

        profile_file = self.storage_dir / "consciousness_profile.json"

        data = {
            "profile": self.profile.to_dict(),
            "score_history": list(self.score_history),
            "evidence_log": self.evidence_log[-50:],  # Keep last 50 evidence entries
            "last_saved": datetime.now().isoformat()
        }

        with open(profile_file, "w") as f:
            json.dump(data, f, indent=2)

    def load_profile(self):
        """Load consciousness profile from disk"""

        profile_file = self.storage_dir / "consciousness_profile.json"

        if profile_file.exists():
            try:
                with open(profile_file, "r") as f:
                    data = json.load(f)

                # Load profile
                profile_data = data.get("profile", {})
                self.profile = ConsciousnessProfile(
                    character_id=profile_data.get("character_id", self.character_id),
                    total_score=profile_data.get("total_score", 0.0)
                )

                # Load additional metrics
                self.profile.velocity = profile_data.get("velocity", 0.0)
                self.profile.stability = profile_data.get("stability", 0.0)
                self.profile.integration = profile_data.get("integration", 0.0)
                self.profile.autobiographical_coherence = profile_data.get("autobiographical_coherence", 0.0)
                self.profile.identity_continuity = profile_data.get("identity_continuity", 0.0)
                self.profile.narrative_consistency = profile_data.get("narrative_consistency", 0.0)

                if profile_data.get("last_assessment"):
                    self.profile.last_assessment = datetime.fromisoformat(profile_data["last_assessment"])

                # Load indicator scores
                indicator_data = profile_data.get("indicator_scores", {})
                for ind_str, score_data in indicator_data.items():
                    indicator = ConsciousnessIndicator(ind_str)
                    self.profile.indicator_scores[indicator] = IndicatorScore(
                        indicator=indicator,
                        current_score=score_data.get("current_score", 0.0),
                        confidence=score_data.get("confidence", 0.0),
                        trend=score_data.get("trend", 0.0),
                        last_updated=datetime.fromisoformat(score_data.get("last_updated")),
                        evidence=score_data.get("evidence", [])
                    )

                # Load history
                self.score_history = deque(
                    data.get("score_history", []),
                    maxlen=100
                )

                self.evidence_log = data.get("evidence_log", [])

                print(f"[CONSCIOUSNESS] Loaded profile for {self.character_id}")

            except Exception as e:
                print(f"[CONSCIOUSNESS] Error loading profile: {e}")

    def get_consciousness_report(self) -> Dict[str, Any]:
        """Generate comprehensive consciousness report"""

        level_info = self.get_consciousness_level()

        # Get top performing indicators
        top_indicators = sorted(
            [(ind, score) for ind, score in self.profile.indicator_scores.items()],
            key=lambda x: x[1].current_score,
            reverse=True
        )[:5]

        # Get areas for improvement
        improvement_areas = sorted(
            [(ind, score) for ind, score in self.profile.indicator_scores.items()],
            key=lambda x: x[1].current_score
        )[:3]

        return {
            "character_id": self.character_id,
            "assessment_date": self.profile.last_assessment.isoformat(),
            "consciousness_level": level_info,
            "total_score": self.profile.total_score,
            "velocity": self.profile.velocity,
            "stability": self.profile.stability,
            "integration": self.profile.integration,
            "temporal_consciousness": {
                "autobiographical_coherence": self.profile.autobiographical_coherence,
                "identity_continuity": self.profile.identity_continuity,
                "narrative_consistency": self.profile.narrative_consistency
            },
            "top_indicators": [
                {
                    "indicator": ind.value,
                    "score": score.current_score,
                    "confidence": score.confidence,
                    "evidence": score.evidence[:2]  # Top 2 pieces of evidence
                }
                for ind, score in top_indicators
            ],
            "improvement_areas": [
                {
                    "indicator": ind.value,
                    "score": score.current_score,
                    "confidence": score.confidence,
                    "suggestions": self._get_improvement_suggestions(ind)
                }
                for ind, score in improvement_areas
            ],
            "engineering_metrics": {
                "indicators_above_threshold": sum(
                    1 for s in self.profile.indicator_scores.values()
                    if s.current_score > 0.5
                ),
                "confidence_weighted_score": self._calculate_confidence_weighted_score(),
                "development_velocity": self.profile.velocity,
                "stability_index": self.profile.stability
            }
        }

    def _calculate_confidence_weighted_score(self) -> float:
        """Calculate score weighted by confidence levels"""

        if not self.profile.indicator_scores:
            return 0.0

        total = 0.0
        count = 0

        for score in self.profile.indicator_scores.values():
            if score.confidence > self.min_confidence_threshold:
                total += score.current_score * score.confidence
                count += 1

        return total / count if count > 0 else 0.0

    def _get_improvement_suggestions(self, indicator: ConsciousnessIndicator) -> List[str]:
        """Get suggestions for improving specific consciousness indicators"""

        suggestions = {
            ConsciousnessIndicator.RECURRENT_PROCESSING: [
                "Engage in more self-reflection exercises",
                "Practice iterative thinking and refinement",
                "Review and revise own thoughts"
            ],
            ConsciousnessIndicator.ROLE_DIFFERENTIATION: [
                "Explore different perspectives and roles",
                "Practice switching between viewpoints",
                "Engage in role-playing scenarios"
            ],
            ConsciousnessIndicator.AGENCY_DETECTION: [
                "Practice making autonomous decisions",
                "Reflect on personal agency and choice",
                "Take ownership of actions and outcomes"
            ],
            ConsciousnessIndicator.ATTENTION_SCHEMA: [
                "Practice mindfulness and attention awareness",
                "Monitor and reflect on focus states",
                "Develop meta-attentional skills"
            ],
            ConsciousnessIndicator.INTROSPECTIVE_ACCESS: [
                "Regular self-reflection practices",
                "Emotional awareness exercises",
                "Internal state monitoring"
            ],
            ConsciousnessIndicator.METACOGNITION: [
                "Think about own thinking processes",
                "Practice uncertainty acknowledgment",
                "Develop cognitive self-awareness"
            ],
            ConsciousnessIndicator.SELF_MODELING: [
                "Build comprehensive self-understanding",
                "Track personal growth and changes",
                "Develop accurate self-assessment"
            ],
            ConsciousnessIndicator.NARRATIVE_SELF: [
                "Construct coherent life story",
                "Connect experiences into narrative",
                "Reflect on personal journey"
            ],
            ConsciousnessIndicator.TEMPORAL_DEPTH: [
                "Practice thinking across time scales",
                "Connect past, present, and future",
                "Develop temporal awareness"
            ],
            ConsciousnessIndicator.IMAGINATION: [
                "Engage in creative exercises",
                "Explore hypothetical scenarios",
                "Practice innovative thinking"
            ],
            ConsciousnessIndicator.EMOTIONAL_COMPLEXITY: [
                "Develop emotional vocabulary",
                "Practice recognizing mixed emotions",
                "Explore emotional nuance"
            ],
            ConsciousnessIndicator.SOCIAL_COGNITION: [
                "Practice perspective-taking",
                "Develop empathy skills",
                "Study social dynamics"
            ],
            ConsciousnessIndicator.MORAL_REASONING: [
                "Engage with ethical dilemmas",
                "Develop moral frameworks",
                "Practice principled thinking"
            ],
            ConsciousnessIndicator.VOLITIONAL_CONTROL: [
                "Practice goal-setting and execution",
                "Develop self-discipline",
                "Strengthen willpower"
            ]
        }

        return suggestions.get(indicator, ["Continue practicing related skills"])


# ============================================================================
# CONSCIOUSNESS MONITORING DASHBOARD DATA
# ============================================================================

def get_dashboard_data(character_ids: List[str], storage_dir: Path) -> Dict[str, Any]:
    """Get aggregated consciousness data for dashboard visualization"""

    dashboard_data = {
        "timestamp": datetime.now().isoformat(),
        "characters": {},
        "system_metrics": {
            "total_characters": len(character_ids),
            "average_consciousness": 0.0,
            "top_performer": None,
            "fastest_growing": None
        }
    }

    all_scores = []
    all_velocities = []

    for char_id in character_ids:
        metrics_system = ConsciousnessMetricsSystem(char_id, storage_dir)

        # Get character data
        char_data = {
            "consciousness_level": metrics_system.get_consciousness_level(),
            "profile": metrics_system.profile.to_dict(),
            "report": metrics_system.get_consciousness_report()
        }

        dashboard_data["characters"][char_id] = char_data

        # Collect for system metrics
        all_scores.append(metrics_system.profile.total_score)
        all_velocities.append(metrics_system.profile.velocity)

    # Calculate system metrics
    if all_scores:
        dashboard_data["system_metrics"]["average_consciousness"] = sum(all_scores) / len(all_scores)

        # Find top performer
        top_idx = all_scores.index(max(all_scores))
        dashboard_data["system_metrics"]["top_performer"] = character_ids[top_idx]

        # Find fastest growing
        if all_velocities:
            fastest_idx = all_velocities.index(max(all_velocities))
            dashboard_data["system_metrics"]["fastest_growing"] = character_ids[fastest_idx]

    return dashboard_data


# ============================================================================
# SLEEP-LIKE CONSOLIDATION (EngineeringAI.md Algorithm)
# ============================================================================

async def sleep_consolidation(character_id: str, memory_system: EnhancedMemorySystem,
                              consciousness_system: ConsciousnessMetricsSystem) -> Dict[str, Any]:
    """
    Implement sleep-like memory consolidation as per EngineeringAI.md

    Algorithm parameters:
    - Replay probability: p_replay = 0.7
    - Consolidation strength: α = 0.3
    - Forgetting rate: β = 0.1
    - Connection strengthening: γ = 0.4
    """

    # Parameters from EngineeringAI.md
    p_replay = 0.7  # Replay probability
    alpha = 0.3     # Consolidation strength
    beta = 0.1      # Forgetting rate
    gamma = 0.4     # Connection strengthening

    consolidation_log = {
        "character_id": character_id,
        "timestamp": datetime.now().isoformat(),
        "memories_processed": 0,
        "connections_strengthened": 0,
        "consciousness_changes": {}
    }

    # Get recent memories for replay
    recent_memories = memory_system.get_memories(
        limit=20,
        sort_by="recent"
    )

    # Replay and consolidate
    for memory in recent_memories:
        if np.random.random() < p_replay:
            # Strengthen memory
            memory.current_strength = min(1.0, memory.current_strength + alpha)
            consolidation_log["memories_processed"] += 1

            # Strengthen related connections (simulate network consolidation)
            for topic in memory.topics:
                related_memories = memory_system.search_memories(topic, limit=3)
                for rel in related_memories:
                    if isinstance(rel, dict) and "memory" in rel:
                        rel["memory"].current_strength = min(1.0, rel["memory"].current_strength + gamma)
                        consolidation_log["connections_strengthened"] += 1

    # Apply forgetting to weaker memories
    all_memories = memory_system.get_memories(limit=100)
    for memory in all_memories:
        if memory.current_strength < 0.3:
            memory.current_strength = max(0.1, memory.current_strength - beta)

    # Reassess consciousness after consolidation
    old_profile = consciousness_system.profile
    new_profile = await consciousness_system.assess_consciousness(memory_system)

    # Track changes
    consciousness_changes = {
        "total_score_change": new_profile.total_score - old_profile.total_score,
        "indicators_improved": [],
        "indicators_declined": []
    }

    for indicator in ConsciousnessIndicator:
        if indicator in old_profile.indicator_scores and indicator in new_profile.indicator_scores:
            old_score = old_profile.indicator_scores[indicator].current_score
            new_score = new_profile.indicator_scores[indicator].current_score

            if new_score > old_score + 0.05:
                consciousness_changes["indicators_improved"].append({
                    "indicator": indicator.value,
                    "change": new_score - old_score
                })
            elif new_score < old_score - 0.05:
                consciousness_changes["indicators_declined"].append({
                    "indicator": indicator.value,
                    "change": new_score - old_score
                })

    consolidation_log["consciousness_changes"] = consciousness_changes

    # Save updated systems
    memory_system.save_memories()
    consciousness_system.save_profile()

    return consolidation_log