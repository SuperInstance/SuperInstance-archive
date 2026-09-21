"""
AI Society Portal - Meta-Cognitive Self-Monitoring System
=========================================================
Comprehensive meta-cognitive system for AI characters that enables:

1. Real-time cognitive state monitoring
2. Cognitive bias detection and mitigation
3. Self-regulation of learning strategies
4. Confidence calibration and reflection
5. Knowledge gap identification
6. Meta-reasoning and strategic thinking

Integrates with existing memory and consciousness systems to provide
characters with sophisticated self-awareness and adaptive capabilities.
"""

import json
import asyncio
import numpy as np
import math
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from collections import defaultdict, deque
import re
import statistics

# Import existing systems
from memory_system import EnhancedMemorySystem, MemoryType, Memory
from consciousness_metrics import ConsciousnessMetricsSystem, ConsciousnessIndicator


# ============================================================================
# METACOGNITIVE TYPES AND STRUCTURES
# ============================================================================

class CognitiveState(Enum):
    """Different cognitive states a character can be in"""
    FOCUSED_REASONING = "focused_reasoning"
    CREATIVE_EXPLORATION = "creative_exploration"
    REFLECTIVE_THINKING = "reflective_thinking"
    PROBLEM_SOLVING = "problem_solving"
    LEARNING_ACQUISITION = "learning_acquisition"
    SOCIAL_PROCESSING = "social_processing"
    UNCERTAINTY_PROCESSING = "uncertainty_processing"
    METACOGNITIVE_MONITORING = "metacognitive_monitoring"


class BiasType(Enum):
    """Types of cognitive biases to detect"""
    CONFIRMATION_BIAS = "confirmation_bias"
    ANCHORING_BIAS = "anchoring_bias"
    AVAILABILITY_BIAS = "availability_bias"
    OVERCONFIDENCE_BIAS = "overconfidence_bias"
    DUNNING_KRUGER = "dunning_kruger"
    SUNK_COST_FALLACY = "sunk_cost_fallacy"
    RECENCY_BIAS = "recency_bias"
    BANDWAGON_EFFECT = "bandwagon_effect"
    AUTHORITY_BIAS = "authority_bias"
    SELF_SERVING_BIAS = "self_serving_bias"


class LearningStrategy(Enum):
    """Adaptive learning strategies"""
    DELIBERATE_PRACTICE = "deliberate_practice"
    INTERLEAVING = "interleaving"
    SPACED_REPETITION = "spaced_repetition"
    ELABORATIVE_INTERROGATION = "elaborative_interrogation"
    SELF_EXPLANATION = "self_explanation"
    TEACHING_OTHERS = "teaching_others"
    CONCEPT_MAPPING = "concept_mapping"
    METACOGNITIVE_REFLECTION = "metacognitive_reflection"


class ConfidenceLevel(Enum):
    """Confidence calibration levels"""
    VERY_LOW = 0.1
    LOW = 0.3
    MODERATE = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9


@dataclass
class CognitiveStateSnapshot:
    """Snapshot of cognitive state at a specific time"""
    timestamp: datetime
    primary_state: CognitiveState
    secondary_states: List[CognitiveState]
    cognitive_load: float  # 0-1 scale
    focus_level: float     # 0-1 scale
    energy_level: float    # 0-1 scale
    uncertainty_level: float  # 0-1 scale
    confidence_calibration: float  # How well confidence matches accuracy
    processing_mode: str   # "analytical", "intuitive", "creative"
    attention_focus: List[str]  # What's currently being attended to
    working_memory_contents: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "primary_state": self.primary_state.value,
            "secondary_states": [s.value for s in self.secondary_states],
            "cognitive_load": self.cognitive_load,
            "focus_level": self.focus_level,
            "energy_level": self.energy_level,
            "uncertainty_level": self.uncertainty_level,
            "confidence_calibration": self.confidence_calibration,
            "processing_mode": self.processing_mode,
            "attention_focus": self.attention_focus,
            "working_memory_contents": self.working_memory_contents
        }


@dataclass
class BiasDetection:
    """Detection of a cognitive bias"""
    bias_type: BiasType
    confidence: float  # 0-1 scale
    severity: float    # 0-1 scale
    evidence: List[str]
    context: str
    timestamp: datetime
    suggested_correction: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bias_type": self.bias_type.value,
            "confidence": self.confidence,
            "severity": self.severity,
            "evidence": self.evidence,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "suggested_correction": self.suggested_correction
        }


@dataclass
class KnowledgeGap:
    """Identified knowledge gap"""
    domain: str
    specific_topic: str
    gap_type: str  # "missing_knowledge", "misconception", "outdated_info"
    importance: float  # 0-1 scale
    confidence: float  # 0-1 scale
    related_memories: List[str]  # Memory IDs
    suggested_resources: List[str]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "specific_topic": self.specific_topic,
            "gap_type": self.gap_type,
            "importance": self.importance,
            "confidence": self.confidence,
            "related_memories": self.related_memories,
            "suggested_resources": self.suggested_resources,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class LearningStrategyAssessment:
    """Assessment of current learning strategy effectiveness"""
    strategy: LearningStrategy
    effectiveness_score: float  # 0-1 scale
    confidence: float  # 0-1 scale
    context: str
    performance_trend: float  # -1 to 1
    recommendations: List[str]
    last_updated: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "effectiveness_score": self.effectiveness_score,
            "confidence": self.confidence,
            "context": self.context,
            "performance_trend": self.performance_trend,
            "recommendations": self.recommendations,
            "last_updated": self.last_updated.isoformat()
        }


# ============================================================================
# COGNITIVE STATE TRACKER
# ============================================================================

class CognitiveStateTracker:
    """Tracks and analyzes cognitive states in real-time"""

    def __init__(self, character_id: str):
        self.character_id = character_id
        self.state_history: deque = deque(maxlen=100)
        self.current_state = CognitiveState.FOCUSED_REASONING
        self.cognitive_load_baseline = 0.5
        self.focus_patterns = defaultdict(list)
        self.energy_patterns = defaultdict(list)

        # State transition patterns
        self.state_transitions = defaultdict(lambda: defaultdict(int))
        self.state_durations = defaultdict(list)
        self.last_state_change = datetime.now()

    def update_cognitive_state(self, context: Dict[str, Any],
                              memory_system: EnhancedMemorySystem = None) -> CognitiveStateSnapshot:
        """Update current cognitive state based on context and recent activity"""

        # Analyze context to determine cognitive state
        primary_state = self._determine_primary_state(context, memory_system)
        secondary_states = self._determine_secondary_states(context, memory_system)

        # Calculate cognitive metrics
        cognitive_load = self._calculate_cognitive_load(context, memory_system)
        focus_level = self._calculate_focus_level(context, memory_system)
        energy_level = self._calculate_energy_level(context, memory_system)
        uncertainty_level = self._calculate_uncertainty_level(context, memory_system)
        confidence_calibration = self._calculate_confidence_calibration(context, memory_system)

        # Determine processing mode
        processing_mode = self._determine_processing_mode(primary_state, cognitive_load)

        # Get attention focus and working memory
        attention_focus = self._get_attention_focus(context, memory_system)
        working_memory_contents = self._get_working_memory_contents(memory_system)

        # Create snapshot
        snapshot = CognitiveStateSnapshot(
            timestamp=datetime.now(),
            primary_state=primary_state,
            secondary_states=secondary_states,
            cognitive_load=cognitive_load,
            focus_level=focus_level,
            energy_level=energy_level,
            uncertainty_level=uncertainty_level,
            confidence_calibration=confidence_calibration,
            processing_mode=processing_mode,
            attention_focus=attention_focus,
            working_memory_contents=working_memory_contents
        )

        # Update state history
        self._update_state_history(snapshot)

        return snapshot

    def _determine_primary_state(self, context: Dict[str, Any],
                               memory_system: EnhancedMemorySystem = None) -> CognitiveState:
        """Determine primary cognitive state from context"""

        # Analyze context clues
        activity = context.get("activity", "").lower()
        content = context.get("content", "").lower()
        recent_memories = []

        if memory_system:
            recent_memories = memory_system.get_memories(limit=10, sort_by="recent")

        # State detection logic
        if any(keyword in activity for keyword in ["reflecting", "introspecting", "self-analysis"]):
            return CognitiveState.REFLECTIVE_THINKING
        elif any(keyword in activity for keyword in ["learning", "studying", "acquiring"]):
            return CognitiveState.LEARNING_ACQUISITION
        elif any(keyword in activity for keyword in ["creating", "generating", "exploring"]):
            return CognitiveState.CREATIVE_EXPLORATION
        elif any(keyword in activity for keyword in ["problem", "solving", "analyzing"]):
            return CognitiveState.PROBLEM_SOLVING
        elif any(keyword in activity for keyword in ["social", "interacting", "collaborating"]):
            return CognitiveState.SOCIAL_PROCESSING
        elif any(keyword in content for keyword in ["uncertain", "unsure", "confused"]):
            return CognitiveState.UNCERTAINTY_PROCESSING
        elif any(keyword in content for keyword in ["thinking about thinking", "meta", "self-aware"]):
            return CognitiveState.METACOGNITIVE_MONITORING
        else:
            return CognitiveState.FOCUSED_REASONING

    def _determine_secondary_states(self, context: Dict[str, Any],
                                  memory_system: EnhancedMemorySystem = None) -> List[CognitiveState]:
        """Determine secondary cognitive states"""
        secondary = []

        # Check for multiple concurrent states
        content = context.get("content", "").lower()

        if "learn" in content:
            secondary.append(CognitiveState.LEARNING_ACQUISITION)
        if "create" in content or "imagine" in content:
            secondary.append(CognitiveState.CREATIVE_EXPLORATION)
        if "problem" in content:
            secondary.append(CognitiveState.PROBLEM_SOLVING)
        if "reflect" in content or "think about" in content:
            secondary.append(CognitiveState.REFLECTIVE_THINKING)
        if "social" in content or "other" in content:
            secondary.append(CognitiveState.SOCIAL_PROCESSING)
        if "uncertain" in content or "not sure" in content:
            secondary.append(CognitiveState.UNCERTAINTY_PROCESSING)

        return secondary[:3]  # Limit to top 3 secondary states

    def _calculate_cognitive_load(self, context: Dict[str, Any],
                                memory_system: EnhancedMemorySystem = None) -> float:
        """Calculate current cognitive load"""

        load = 0.0

        # Base load from task complexity
        task_complexity = context.get("task_complexity", 0.5)
        load += task_complexity * 0.3

        # Load from working memory usage
        working_memory_size = context.get("working_memory_size", 5)
        load += min(1.0, working_memory_size / 10) * 0.3

        # Load from multitasking
        concurrent_tasks = context.get("concurrent_tasks", 1)
        load += min(1.0, (concurrent_tasks - 1) / 3) * 0.2

        # Load from emotional processing
        emotional_arousal = context.get("emotional_arousal", 0.0)
        load += abs(emotional_arousal) * 0.1

        # Load from uncertainty
        uncertainty = context.get("uncertainty_level", 0.0)
        load += uncertainty * 0.1

        return min(1.0, load)

    def _calculate_focus_level(self, context: Dict[str, Any],
                             memory_system: EnhancedMemorySystem = None) -> float:
        """Calculate current focus level"""

        focus = 0.8  # Start with good focus baseline

        # Reduce focus based on distractions
        distractions = context.get("distractions", [])
        focus -= len(distractions) * 0.1

        # Reduce focus based on cognitive load (inverse relationship)
        cognitive_load = self._calculate_cognitive_load(context, memory_system)
        focus -= cognitive_load * 0.2

        # Increase focus based on task engagement
        task_engagement = context.get("task_engagement", 0.5)
        focus += task_engagement * 0.3

        # Adjust for energy level
        energy = context.get("energy_level", 0.7)
        focus = focus * (0.5 + energy * 0.5)

        return max(0.0, min(1.0, focus))

    def _calculate_energy_level(self, context: Dict[str, Any],
                              memory_system: EnhancedMemorySystem = None) -> float:
        """Calculate current energy level"""

        energy = 0.7  # Baseline energy

        # Adjust based on time of day (circadian rhythm simulation)
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:  # Peak hours
            energy = 0.9
        elif 6 <= current_hour <= 9 or 17 <= current_hour <= 22:  # Moderate hours
            energy = 0.7
        else:  # Low energy hours
            energy = 0.4

        # Adjust based on recent activity
        recent_activity = context.get("recent_activity_intensity", 0.5)
        energy -= recent_activity * 0.2

        # Adjust based on rest
        recent_rest = context.get("recent_rest_quality", 0.5)
        energy += recent_rest * 0.3

        # Adjust based on motivation
        motivation = context.get("motivation_level", 0.5)
        energy += motivation * 0.2

        return max(0.0, min(1.0, energy))

    def _calculate_uncertainty_level(self, context: Dict[str, Any],
                                   memory_system: EnhancedMemorySystem = None) -> float:
        """Calculate current uncertainty level"""

        uncertainty = 0.0

        # Check for explicit uncertainty indicators
        content = context.get("content", "").lower()
        uncertainty_phrases = ["not sure", "uncertain", "confused", "maybe", "perhaps",
                             "i think", "might be", "could be", "don't know"]

        for phrase in uncertainty_phrases:
            if phrase in content:
                uncertainty += 0.1

        # Check for task complexity (higher complexity = higher uncertainty)
        task_complexity = context.get("task_complexity", 0.5)
        uncertainty += task_complexity * 0.3

        # Check for novelty (newer topics = higher uncertainty)
        novelty = context.get("topic_novelty", 0.5)
        uncertainty += novelty * 0.2

        # Check for information sufficiency
        information_sufficiency = context.get("information_sufficiency", 0.5)
        uncertainty += (1.0 - information_sufficiency) * 0.3

        return min(1.0, uncertainty)

    def _calculate_confidence_calibration(self, context: Dict[str, Any],
                                        memory_system: EnhancedMemorySystem = None) -> float:
        """Calculate how well calibrated confidence is with actual accuracy"""

        # This would ideally be calculated based on historical accuracy vs confidence
        # For now, use a simplified heuristic
        calibration = 0.7  # Start with decent calibration

        # Adjust based on recent feedback
        recent_feedback = context.get("recent_feedback", [])
        if recent_feedback:
            accuracy_scores = [f.get("accuracy", 0.5) for f in recent_feedback[-5:]]
            confidence_scores = [f.get("confidence", 0.5) for f in recent_feedback[-5:]]

            if accuracy_scores and confidence_scores:
                # Calculate correlation between confidence and accuracy
                correlation = np.corrcoef(confidence_scores, accuracy_scores)[0, 1]
                if not np.isnan(correlation):
                    calibration = 0.5 + correlation * 0.5

        # Adjust for expertise level (more expertise = better calibration)
        expertise = context.get("domain_expertise", 0.5)
        calibration = calibration * (0.7 + expertise * 0.3)

        # Adjust for metacognitive awareness
        metacognitive_awareness = context.get("metacognitive_awareness", 0.5)
        calibration = calibration * (0.8 + metacognitive_awareness * 0.2)

        return max(0.0, min(1.0, calibration))

    def _determine_processing_mode(self, primary_state: CognitiveState,
                                 cognitive_load: float) -> str:
        """Determine current processing mode"""

        if cognitive_load > 0.8:
            return "overloaded"
        elif primary_state in [CognitiveState.CREATIVE_EXPLORATION, CognitiveState.REFLECTIVE_THINKING]:
            return "creative"
        elif primary_state in [CognitiveState.PROBLEM_SOLVING, CognitiveState.FOCUSED_REASONING]:
            return "analytical"
        elif primary_state == CognitiveState.LEARNING_ACQUISITION:
            return "integrative"
        else:
            return "mixed"

    def _get_attention_focus(self, context: Dict[str, Any],
                           memory_system: EnhancedMemorySystem = None) -> List[str]:
        """Get current attention focus areas"""

        focus_areas = []

        # From context
        if "topic" in context:
            focus_areas.append(context["topic"])
        if "task" in context:
            focus_areas.append(f"task: {context['task']}")
        if "goal" in context:
            focus_areas.append(f"goal: {context['goal']}")

        # From recent memories
        if memory_system:
            recent_memories = memory_system.get_memories(limit=5, sort_by="recent")
            for memory in recent_memories[:3]:
                if memory.topics:
                    focus_areas.extend(memory.topics[:2])

        return list(set(focus_areas))[:5]  # Return unique focus areas, max 5

    def _get_working_memory_contents(self, memory_system: EnhancedMemorySystem = None) -> List[str]:
        """Get current working memory contents"""

        if memory_system:
            return memory_system.working_memory[-7:]  # Last 7 items
        return []

    def _update_state_history(self, snapshot: CognitiveStateSnapshot):
        """Update state history and patterns"""

        # Record state transition
        if self.state_history:
            last_snapshot = self.state_history[-1]
            transition = (last_snapshot.primary_state, snapshot.primary_state)
            self.state_transitions[last_snapshot.primary_state][snapshot.primary_state] += 1

            # Record state duration
            duration = (snapshot.timestamp - last_snapshot.timestamp).total_seconds() / 60
            self.state_durations[last_snapshot.primary_state].append(duration)

        # Add to history
        self.state_history.append(snapshot)
        self.current_state = snapshot.primary_state
        self.last_state_change = snapshot.timestamp

        # Update patterns
        self.focus_patterns[snapshot.primary_state].append(snapshot.focus_level)
        self.energy_patterns[snapshot.primary_state].append(snapshot.energy_level)

    def get_state_analysis(self) -> Dict[str, Any]:
        """Get analysis of cognitive state patterns"""

        if not self.state_history:
            return {"error": "Insufficient data for analysis"}

        # Most common states
        state_counts = defaultdict(int)
        for snapshot in self.state_history:
            state_counts[snapshot.primary_state] += 1

        most_common_states = sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        # Average cognitive load
        avg_cognitive_load = np.mean([s.cognitive_load for s in self.state_history])

        # Average focus level by state
        focus_by_state = {}
        for state, focus_levels in self.focus_patterns.items():
            if focus_levels:
                focus_by_state[state.value] = {
                    "average": np.mean(focus_levels),
                    "trend": "improving" if len(focus_levels) > 1 and focus_levels[-1] > focus_levels[0] else "declining"
                }

        # State transition patterns
        common_transitions = []
        for from_state, to_states in self.state_transitions.items():
            for to_state, count in to_states.items():
                if count >= 2:  # Only include transitions that happened at least twice
                    common_transitions.append({
                        "from": from_state.value,
                        "to": to_state.value,
                        "frequency": count
                    })

        common_transitions.sort(key=lambda x: x["frequency"], reverse=True)

        return {
            "analysis_period": {
                "start": self.state_history[0].timestamp.isoformat(),
                "end": self.state_history[-1].timestamp.isoformat(),
                "snapshots_analyzed": len(self.state_history)
            },
            "most_common_states": [{"state": state.value, "frequency": count} for state, count in most_common_states],
            "average_cognitive_load": avg_cognitive_load,
            "focus_patterns_by_state": focus_by_state,
            "common_transitions": common_transitions[:5],
            "current_state": self.current_state.value,
            "time_in_current_state": (datetime.now() - self.last_state_change).total_seconds() / 60
        }


# ============================================================================
# BIAS DETECTOR
# ============================================================================

class BiasDetector:
    """Detects cognitive biases in thinking patterns"""

    def __init__(self, character_id: str):
        self.character_id = character_id
        self.bias_history: deque = deque(maxlen=200)
        self.bias_patterns = defaultdict(list)
        self.correction_effectiveness = defaultdict(list)

        # Bias detection patterns
        self.bias_indicators = {
            BiasType.CONFIRMATION_BIAS: [
                r"i knew it", r"that's what i thought", r"confirms my belief",
                r"as expected", r"i was right", r"just as i suspected"
            ],
            BiasType.ANCHORING_BIAS: [
                r"first.*thought", r"initial.*idea", r"based on.*first",
                r"starting from", r"originally.*thought"
            ],
            BiasType.AVAILABILITY_BIAS: [
                r"recently.*saw", r"just.*heard", r"vividly.*remember",
                r"stands out", r"can't help but think of"
            ],
            BiasType.OVERCONFIDENCE_BIAS: [
                r"definitely", r"certainly", r"without a doubt", r"i'm sure",
                r"obviously", r"clearly", r"no question"
            ],
            BiasType.DUNNING_KRUGER: [
                r"i'm an expert", r"i know.*well", r"it's simple",
                r"easy to understand", r"basic.*concept"
            ],
            BiasType.SUNK_COST_FALLACY: [
                r"already.*invested", r"can't.*back out", r"too much.*put in",
                r"have to continue", r"can't waste.*effort"
            ],
            BiasType.RECENCY_BIAS: [
                r"just.*happened", r"recently", r"latest", r"most recent",
                r"in the last.*days"
            ],
            BiasType.BANDWAGON_EFFECT: [
                r"everyone.*thinks", r"most.*believe", r"popular.*opinion",
                r"people.*say", r"common.*view"
            ],
            BiasType.AUTHORITY_BIAS: [
                r"expert.*said", r"authority.*claims", r"study.*shows",
                r"research.*proves", r"scientist.*found"
            ],
            BiasType.SELF_SERVING_BIAS: [
                r"not my fault", r"their.*mistake", r"deserve.*credit",
                r"my.*success", r"their.*failure"
            ]
        }

    def analyze_for_biases(self, content: str, context: Dict[str, Any],
                          memory_system: EnhancedMemorySystem = None) -> List[BiasDetection]:
        """Analyze content for cognitive biases"""

        detected_biases = []
        content_lower = content.lower()

        # Check each bias type
        for bias_type, patterns in self.bias_indicators.items():
            matches = []
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    matches.append(pattern)

            if matches:
                # Calculate confidence and severity
                confidence = min(1.0, len(matches) * 0.3)
                severity = self._calculate_bias_severity(bias_type, content, context, memory_system)

                # Generate correction suggestion
                correction = self._generate_bias_correction(bias_type, context)

                bias_detection = BiasDetection(
                    bias_type=bias_type,
                    confidence=confidence,
                    severity=severity,
                    evidence=matches,
                    context=context.get("topic", "general"),
                    timestamp=datetime.now(),
                    suggested_correction=correction
                )

                detected_biases.append(bias_detection)
                self._record_bias_detection(bias_detection)

        return detected_biases

    def _calculate_bias_severity(self, bias_type: BiasType, content: str,
                               context: Dict[str, Any],
                               memory_system: EnhancedMemorySystem = None) -> float:
        """Calculate severity of detected bias"""

        base_severity = 0.5

        # Adjust based on importance of decision
        decision_importance = context.get("decision_importance", 0.5)
        severity = base_severity * (0.5 + decision_importance * 0.5)

        # Adjust based on confidence level
        confidence_level = context.get("confidence_level", 0.5)
        if bias_type == BiasType.OVERCONFIDENCE_BIAS:
            severity *= confidence_level
        else:
            severity *= (0.7 + confidence_level * 0.3)

        # Adjust based on domain expertise (higher expertise = more severe bias)
        domain_expertise = context.get("domain_expertise", 0.5)
        if bias_type in [BiasType.DUNNING_KRUGER, BiasType.OVERCONFIDENCE_BIAS]:
            severity *= (0.5 + domain_expertise * 0.5)

        # Adjust based on recent similar biases
        recent_biases = [b for b in self.bias_history
                        if b.bias_type == bias_type and
                        (datetime.now() - b.timestamp).total_seconds() < 3600]  # Last hour
        if recent_biases:
            severity *= (1.0 + len(recent_biases) * 0.1)

        return min(1.0, severity)

    def _generate_bias_correction(self, bias_type: BiasType,
                                context: Dict[str, Any]) -> str:
        """Generate correction suggestion for detected bias"""

        corrections = {
            BiasType.CONFIRMATION_BIAS: "Actively seek out contradictory evidence and alternative viewpoints. Ask: 'What evidence would change my mind?'",
            BiasType.ANCHORING_BIAS: "Re-evaluate the problem from scratch, ignoring initial impressions. Consider multiple starting points.",
            BiasType.AVAILABILITY_BIAS: "Look for statistical data rather than relying on vivid examples. Consider base rates.",
            BiasType.OVERCONFIDENCE_BIAS: "Consider the full range of possible outcomes. Ask: 'What could I be missing?'",
            BiasType.DUNNING_KRUGER: "Seek feedback from others. Acknowledge the limits of your knowledge.",
            BiasType.SUNK_COST_FALLACY: "Focus on future costs and benefits, ignoring past investments. Ask: 'Would I make this choice again?'",
            BiasType.RECENCY_BIAS: "Consider longer-term trends and historical patterns, not just recent events.",
            BiasType.BANDWAGON_EFFECT: "Evaluate evidence independently of popular opinion. Ask: 'Is this popular because it's correct?'",
            BiasType.AUTHORITY_BIAS: "Examine the evidence itself, not just the source. Ask: 'Is the reasoning sound?'",
            BiasType.SELF_SERVING_BIAS: "Consider alternative explanations and your own role in outcomes."
        }

        return corrections.get(bias_type, "Reflect on potential biases in your thinking.")

    def _record_bias_detection(self, bias_detection: BiasDetection):
        """Record bias detection for pattern analysis"""

        self.bias_history.append(bias_detection)
        self.bias_patterns[bias_detection.bias_type].append({
            "timestamp": bias_detection.timestamp,
            "severity": bias_detection.severity,
            "confidence": bias_detection.confidence,
            "context": bias_detection.context
        })

    def get_bias_analysis(self) -> Dict[str, Any]:
        """Get analysis of bias patterns"""

        if not self.bias_history:
            return {"error": "No bias detections to analyze"}

        # Most common biases
        bias_counts = defaultdict(int)
        for bias in self.bias_history:
            bias_counts[bias.bias_type] += 1

        most_common_biases = sorted(bias_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Severity trends by bias type
        severity_trends = {}
        for bias_type in BiasType:
            detections = [b for b in self.bias_history if b.bias_type == bias_type]
            if len(detections) >= 2:
                recent_severity = np.mean([b.severity for b in detections[-5:]])
                earlier_severity = np.mean([b.severity for b in detections[-10:-5]] if len(detections) >= 10 else [b.severity for b in detections[:len(detections)//2]])
                trend = "improving" if recent_severity < earlier_severity else "worsening"
                severity_trends[bias_type.value] = {
                    "average_severity": np.mean([b.severity for b in detections]),
                    "trend": trend,
                    "total_detections": len(detections)
                }

        # Correction effectiveness
        correction_stats = {}
        for bias_type, effectiveness_list in self.correction_effectiveness.items():
            if effectiveness_list:
                correction_stats[bias_type.value] = {
                    "average_effectiveness": np.mean(effectiveness_list),
                    "applications": len(effectiveness_list)
                }

        return {
            "analysis_period": {
                "detections_analyzed": len(self.bias_history),
                "time_span_days": (datetime.now() - self.bias_history[0].timestamp).total_seconds() / 86400
            },
            "most_common_biases": [{"bias": bias.value, "count": count} for bias, count in most_common_biases],
            "severity_trends": severity_trends,
            "correction_effectiveness": correction_stats,
            "recommendations": self._generate_bias_recommendations()
        }

    def _generate_bias_recommendations(self) -> List[str]:
        """Generate recommendations based on bias patterns"""

        recommendations = []

        # Most frequent bias
        if self.bias_history:
            bias_counts = defaultdict(int)
            for bias in self.bias_history:
                bias_counts[bias.bias_type] += 1

            most_common = max(bias_counts.items(), key=lambda x: x[1])
            recommendations.append(f"Focus on reducing {most_common[0].value.replace('_', ' ')}. This is your most common cognitive bias.")

        # High severity biases
        high_severity_biases = [b for b in self.bias_history if b.severity > 0.7]
        if high_severity_biases:
            recommendations.append("You show high-severity biases in important decisions. Take extra time to consider alternative perspectives.")

        # Recent patterns
        recent_biases = [b for b in self.bias_history
                        if (datetime.now() - b.timestamp).total_seconds() < 86400]  # Last 24 hours
        if len(recent_biases) > 5:
            recommendations.append("You're showing frequent bias detection recently. Consider taking a break and refreshing your perspective.")

        if not recommendations:
            recommendations.append("Continue monitoring your thinking patterns. Your bias awareness appears healthy.")

        return recommendations


# ============================================================================
# LEARNING STRATEGY ADAPTER
# ============================================================================

class LearningStrategyAdapter:
    """Adapts learning strategies based on performance and context"""

    def __init__(self, character_id: str):
        self.character_id = character_id
        self.strategy_history: deque = deque(maxlen=100)
        self.strategy_performance = defaultdict(list)
        self.strategy_effectiveness = defaultdict(float)
        self.current_strategy = LearningStrategy.DELIBERATE_PRACTICE

        # Strategy selection rules
        self.strategy_rules = {
            "complex_topic": [LearningStrategy.ELABORATIVE_INTERROGATION, LearningStrategy.CONCEPT_MAPPING],
            "skill_acquisition": [LearningStrategy.DELIBERATE_PRACTICE, LearningStrategy.SPACED_REPETITION],
            "social_learning": [LearningStrategy.TEACHING_OTHERS, LearningStrategy.COLLABORATIVE],
            "creative_thinking": [LearningStrategy.INTERLEAVING, LearningStrategy.CREATIVE_EXPLORATION],
            "metacognitive": [LearningStrategy.METACOGNITIVE_REFLECTION, LearningStrategy.SELF_EXPLANATION]
        }

    def recommend_strategy(self, context: Dict[str, Any],
                          memory_system: EnhancedMemorySystem = None) -> LearningStrategyAssessment:
        """Recommend optimal learning strategy for current context"""

        # Analyze context
        learning_context = self._analyze_learning_context(context, memory_system)

        # Get candidate strategies
        candidate_strategies = self._get_candidate_strategies(learning_context)

        # Evaluate each candidate
        strategy_scores = {}
        for strategy in candidate_strategies:
            score = self._evaluate_strategy(strategy, learning_context, memory_system)
            strategy_scores[strategy] = score

        # Select best strategy
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1].score)

        # Create assessment
        assessment = LearningStrategyAssessment(
            strategy=best_strategy[0],
            effectiveness_score=best_strategy[1].score,
            confidence=best_strategy[1].confidence,
            context=learning_context["description"],
            performance_trend=best_strategy[1].trend,
            recommendations=self._generate_strategy_recommendations(best_strategy[0], learning_context),
            last_updated=datetime.now()
        )

        # Update current strategy
        self.current_strategy = best_strategy[0]
        self.strategy_history.append(assessment)

        return assessment

    def _analyze_learning_context(self, context: Dict[str, Any],
                                memory_system: EnhancedMemorySystem = None) -> Dict[str, Any]:
        """Analyze the learning context"""

        learning_context = {
            "description": context.get("description", "general learning"),
            "topic_complexity": context.get("topic_complexity", 0.5),
            "skill_type": context.get("skill_type", "cognitive"),
            "time_available": context.get("time_available", 60),  # minutes
            "social_aspect": context.get("social_aspect", False),
            "creative_aspect": context.get("creative_aspect", False),
            "prereq_knowledge": context.get("prerequisite_knowledge", 0.5),
            "motivation_level": context.get("motivation_level", 0.7),
            "domain": context.get("domain", "general")
        }

        # Add memory-based context
        if memory_system:
            # Check recent learning performance
            recent_learning = memory_system.get_memories_by_type(MemoryType.LEARNING, limit=10)
            if recent_learning:
                learning_context["recent_learning_success"] = np.mean([m.importance for m in recent_learning]) / 10.0
            else:
                learning_context["recent_learning_success"] = 0.5

            # Check for related knowledge
            domain = context.get("domain", "")
            if domain:
                related_memories = memory_system.search_memories(domain, limit=5)
                learning_context["existing_knowledge"] = len(related_memories) / 5.0
            else:
                learning_context["existing_knowledge"] = 0.3

        return learning_context

    def _get_candidate_strategies(self, learning_context: Dict[str, Any]) -> List[LearningStrategy]:
        """Get candidate strategies based on context"""

        candidates = []

        # Add strategies based on learning context
        if learning_context["topic_complexity"] > 0.7:
            candidates.extend(self.strategy_rules["complex_topic"])

        if learning_context["skill_type"] == "procedural":
            candidates.extend(self.strategy_rules["skill_acquisition"])

        if learning_context["social_aspect"]:
            candidates.extend(self.strategy_rules["social_learning"])

        if learning_context["creative_aspect"]:
            candidates.extend(self.strategy_rules["creative_thinking"])

        # Always include metacognitive strategies
        candidates.extend(self.strategy_rules["metacognitive"])

        # Add some general strategies if no specific ones selected
        if not candidates:
            candidates = [LearningStrategy.DELIBERATE_PRACTICE, LearningStrategy.SELF_EXPLANATION]

        # Remove duplicates and return
        return list(set(candidates))

    def _evaluate_strategy(self, strategy: LearningStrategy,
                          learning_context: Dict[str, Any],
                          memory_system: EnhancedMemorySystem = None) -> Dict[str, float]:
        """Evaluate a strategy for the current context"""

        score = 0.5  # Base score
        confidence = 0.5

        # Strategy-specific scoring
        if strategy == LearningStrategy.DELIBERATE_PRACTICE:
            if learning_context["skill_type"] == "procedural":
                score += 0.3
            if learning_context["time_available"] > 30:
                score += 0.2
            confidence = 0.8

        elif strategy == LearningStrategy.SPACED_REPETITION:
            if learning_context["existing_knowledge"] > 0.3:
                score += 0.3
            if learning_context["motivation_level"] > 0.6:
                score += 0.2
            confidence = 0.7

        elif strategy == LearningStrategy.ELABORATIVE_INTERROGATION:
            if learning_context["topic_complexity"] > 0.6:
                score += 0.4
            if learning_context["prereq_knowledge"] > 0.5:
                score += 0.2
            confidence = 0.8

        elif strategy == LearningStrategy.TEACHING_OTHERS:
            if learning_context["social_aspect"]:
                score += 0.4
            if learning_context["existing_knowledge"] > 0.7:
                score += 0.3
            confidence = 0.9

        elif strategy == LearningStrategy.CONCEPT_MAPPING:
            if learning_context["topic_complexity"] > 0.5:
                score += 0.3
            if learning_context["creative_aspect"]:
                score += 0.2
            confidence = 0.7

        elif strategy == LearningStrategy.SELF_EXPLANATION:
            if learning_context["existing_knowledge"] > 0.4:
                score += 0.3
            if learning_context["motivation_level"] > 0.5:
                score += 0.2
            confidence = 0.8

        elif strategy == LearningStrategy.INTERLEAVING:
            if learning_context["creative_aspect"]:
                score += 0.3
            if learning_context["topic_complexity"] < 0.7:
                score += 0.2
            confidence = 0.6

        elif strategy == LearningStrategy.METACOGNITIVE_REFLECTION:
            # Always good for learning
            score += 0.2
            if learning_context["topic_complexity"] > 0.6:
                score += 0.2
            confidence = 0.9

        # Adjust based on historical performance
        historical_performance = self.strategy_performance.get(strategy, [])
        if historical_performance:
            avg_performance = np.mean(historical_performance[-10:])
            score = score * 0.7 + avg_performance * 0.3
            confidence = min(1.0, confidence + len(historical_performance) * 0.05)

        # Calculate trend
        trend = 0.0
        if len(historical_performance) >= 3:
            recent_avg = np.mean(historical_performance[-3:])
            earlier_avg = np.mean(historical_performance[-6:-3]) if len(historical_performance) >= 6 else np.mean(historical_performance[:-3])
            trend = (recent_avg - earlier_avg) / 2.0

        return {
            "score": min(1.0, score),
            "confidence": min(1.0, confidence),
            "trend": trend
        }

    def _generate_strategy_recommendations(self, strategy: LearningStrategy,
                                         learning_context: Dict[str, Any]) -> List[str]:
        """Generate specific recommendations for the strategy"""

        recommendations = {
            LearningStrategy.DELIBERATE_PRACTICE: [
                "Focus on specific, challenging aspects of the topic",
                "Seek immediate feedback on your performance",
                "Repeat difficult concepts until mastery"
            ],
            LearningStrategy.SPACED_REPETITION: [
                "Review material at increasing intervals",
                "Use flashcards or similar tools for repetition",
                "Schedule regular review sessions"
            ],
            LearningStrategy.ELABORATIVE_INTERROGATION: [
                "Ask 'why' and 'how' questions about the material",
                "Connect new information to what you already know",
                "Generate your own explanations for concepts"
            ],
            LearningStrategy.TEACHING_OTHERS: [
                "Explain concepts in simple terms",
                "Anticipate questions others might ask",
                "Use analogies and examples to clarify"
            ],
            LearningStrategy.CONCEPT_MAPPING: [
                "Create visual diagrams of relationships",
                "Identify key concepts and their connections",
                "Use colors and symbols to organize information"
            ],
            LearningStrategy.SELF_EXPLANATION: [
                "Explain concepts to yourself out loud",
                "Identify gaps in your understanding",
                "Connect new information to prior knowledge"
            ],
            LearningStrategy.INTERLEAVING: [
                "Mix different types of problems or topics",
                "Switch between related concepts frequently",
                "Avoid studying one topic for too long"
            ],
            LearningStrategy.METACOGNITIVE_REFLECTION: [
                "Think about your thinking process",
                "Evaluate your learning strategies regularly",
                "Adjust your approach based on effectiveness"
            ]
        }

        return recommendations.get(strategy, ["Follow the strategy systematically", "Monitor your progress"])

    def record_strategy_outcome(self, strategy: LearningStrategy,
                              outcome_score: float, context: Dict[str, Any]):
        """Record the outcome of using a strategy"""

        performance_data = {
            "timestamp": datetime.now(),
            "outcome_score": outcome_score,
            "context": context.get("description", "general"),
            "duration": context.get("duration", 60),
            "difficulty": context.get("difficulty", 0.5)
        }

        self.strategy_performance[strategy].append(outcome_score)

        # Update effectiveness
        recent_scores = self.strategy_performance[strategy][-10:]
        self.strategy_effectiveness[strategy] = np.mean(recent_scores)

    def get_learning_analysis(self) -> Dict[str, Any]:
        """Get analysis of learning strategy effectiveness"""

        if not self.strategy_performance:
            return {"error": "No strategy performance data available"}

        # Most effective strategies
        strategy_effectiveness = {}
        for strategy, scores in self.strategy_performance.items():
            if scores:
                strategy_effectiveness[strategy] = {
                    "average_score": np.mean(scores),
                    "recent_trend": "improving" if len(scores) > 1 and scores[-1] > scores[0] else "declining",
                    "usage_count": len(scores),
                    "consistency": 1.0 - np.std(scores) if len(scores) > 1 else 0.5
                }

        most_effective = sorted(strategy_effectiveness.items(),
                               key=lambda x: x[1]["average_score"],
                               reverse=True)[:3]

        # Current strategy performance
        current_performance = self.strategy_performance.get(self.current_strategy, [])
        current_effectiveness = {
            "strategy": self.current_strategy.value,
            "average_score": np.mean(current_performance) if current_performance else 0.5,
            "recent_performance": current_performance[-5:] if len(current_performance) >= 5 else current_performance,
            "trend": "improving" if len(current_performance) > 1 and current_performance[-1] > current_performance[0] else "declining"
        }

        # Learning recommendations
        recommendations = []
        if most_effective:
            recommendations.append(f"Your most effective strategy is {most_effective[0][0].value.replace('_', ' ')}")

        # Check for underperforming strategies
        underperforming = [(s, data) for s, data in strategy_effectiveness.items()
                          if data["average_score"] < 0.4 and data["usage_count"] > 3]
        if underperforming:
            recommendations.append(f"Consider alternatives to {underperforming[0][0].value.replace('_', ' ')} as it's showing low effectiveness")

        return {
            "strategy_effectiveness": {k.value: v for k, v in strategy_effectiveness.items()},
            "most_effective_strategies": [{"strategy": k.value, **v} for k, v in most_effective],
            "current_strategy_performance": current_effectiveness,
            "total_strategies_tried": len(self.strategy_performance),
            "recommendations": recommendations
        }


# ============================================================================
# KNOWLEDGE GAP ANALYZER
# ============================================================================

class KnowledgeGapAnalyzer:
    """Identifies and analyzes knowledge gaps"""

    def __init__(self, character_id: str):
        self.character_id = character_id
        self.knowledge_gaps: deque = deque(maxlen=100)
        self.domain_mastery = defaultdict(float)
        self.gap_patterns = defaultdict(list)

        # Knowledge domains for analysis
        self.knowledge_domains = [
            "technical", "social", "creative", "analytical",
            "emotional", "philosophical", "practical", "theoretical"
        ]

        # Gap indicators
        self.gap_indicators = {
            "uncertainty": ["not sure", "uncertain", "confused", "don't know"],
            "missing_concepts": ["what is", "don't understand", "never heard of"],
            "misconceptions": ["i thought", "wrong assumption", "incorrect belief"],
            "outdated_info": ["used to be", "old information", "changed since"]
        }

    def analyze_knowledge_gaps(self, context: Dict[str, Any],
                             memory_system: EnhancedMemorySystem = None) -> List[KnowledgeGap]:
        """Analyze current context for knowledge gaps"""

        detected_gaps = []
        content = context.get("content", "")
        domain = context.get("domain", "general")

        # Analyze content for gap indicators
        gaps = self._extract_knowledge_gaps(content, domain, context)
        detected_gaps.extend(gaps)

        # Analyze memory system for gaps
        if memory_system:
            memory_gaps = self._analyze_memory_gaps(memory_system, context)
            detected_gaps.extend(memory_gaps)

        # Analyze confidence-accuracy mismatch
        confidence_gaps = self._analyze_confidence_gaps(context, memory_system)
        detected_gaps.extend(confidence_gaps)

        # Record and return gaps
        for gap in detected_gaps:
            self.knowledge_gaps.append(gap)
            self.gap_patterns[gap.domain].append(gap)

        return detected_gaps

    def _extract_knowledge_gaps(self, content: str, domain: str,
                               context: Dict[str, Any]) -> List[KnowledgeGap]:
        """Extract knowledge gaps from content"""

        gaps = []
        content_lower = content.lower()

        for gap_type, indicators in self.gap_indicators.items():
            for indicator in indicators:
                if indicator in content_lower:
                    # Extract the specific topic mentioned
                    topic = self._extract_topic_near_indicator(content, indicator)
                    if topic:
                        importance = self._calculate_gap_importance(topic, gap_type, context)
                        confidence = self._calculate_gap_confidence(topic, gap_type, context)

                        gap = KnowledgeGap(
                            domain=domain,
                            specific_topic=topic,
                            gap_type=gap_type,
                            importance=importance,
                            confidence=confidence,
                            related_memories=[],  # Will be filled by memory analysis
                            suggested_resources=self._suggest_resources(topic, domain),
                            timestamp=datetime.now()
                        )
                        gaps.append(gap)

        return gaps

    def _extract_topic_near_indicator(self, content: str, indicator: str) -> Optional[str]:
        """Extract the topic being discussed near a gap indicator"""

        # Simple extraction - look for keywords near the indicator
        words = content.lower().split()
        indicator_index = -1

        for i, word in enumerate(words):
            if indicator in word:
                indicator_index = i
                break

        if indicator_index == -1:
            return None

        # Look for topic words within 3 words of the indicator
        start_idx = max(0, indicator_index - 3)
        end_idx = min(len(words), indicator_index + 4)

        topic_words = words[start_idx:end_idx]
        # Remove common stop words and the indicator itself
        topic_words = [w for w in topic_words if w not in
                      ["the", "a", "an", "is", "are", "was", "were", "i", "you", "he", "she", "it", "they", "we"] and indicator not in w]

        if topic_words:
            return " ".join(topic_words[:3])  # Return up to 3 words as topic

        return None

    def _calculate_gap_importance(self, topic: str, gap_type: str,
                                context: Dict[str, Any]) -> float:
        """Calculate importance of a knowledge gap"""

        base_importance = 0.5

        # Adjust based on domain relevance
        domain_relevance = context.get("domain_relevance", 0.5)
        importance = base_importance * (0.5 + domain_relevance * 0.5)

        # Adjust based on task criticality
        task_criticality = context.get("task_criticality", 0.5)
        importance = importance * (0.6 + task_criticality * 0.4)

        # Adjust based on gap type
        if gap_type == "missing_concepts":
            importance *= 1.2
        elif gap_type == "misconceptions":
            importance *= 1.3  # Misconceptions are more critical
        elif gap_type == "outdated_info":
            importance *= 1.1

        # Adjust based on frequency of encountering this topic
        topic_frequency = context.get("topic_frequency", 0.5)
        importance *= (0.7 + topic_frequency * 0.3)

        return min(1.0, importance)

    def _calculate_gap_confidence(self, topic: str, gap_type: str,
                                context: Dict[str, Any]) -> float:
        """Calculate confidence in gap detection"""

        confidence = 0.6  # Base confidence

        # Adjust based on clarity of expression
        clarity = context.get("expression_clarity", 0.5)
        confidence *= (0.7 + clarity * 0.3)

        # Adjust based on explicitness of gap statement
        if gap_type == "uncertainty":
            confidence = 0.8  # Explicit uncertainty statements are reliable
        elif gap_type == "missing_concepts":
            confidence = 0.7
        else:
            confidence = 0.6

        # Adjust based on domain familiarity
        domain_familiarity = context.get("domain_familiarity", 0.5)
        confidence *= (0.5 + domain_familiarity * 0.5)

        return min(1.0, confidence)

    def _suggest_resources(self, topic: str, domain: str) -> List[str]:
        """Suggest resources for filling knowledge gap"""

        suggestions = []

        # General suggestions
        suggestions.append(f"Search for information about '{topic}'")
        suggestions.append(f"Find introductory materials on {domain} concepts")

        # Domain-specific suggestions
        if domain == "technical":
            suggestions.extend([
                "Consult technical documentation",
                "Look for tutorials or guides",
                "Check Stack Overflow or similar forums"
            ])
        elif domain == "social":
            suggestions.extend([
                "Discuss with others who have experience",
                "Read case studies or examples",
                "Observe social situations carefully"
            ])
        elif domain == "creative":
            suggestions.extend([
                "Study works by experts in the field",
                "Practice exercises and techniques",
                "Seek feedback on your attempts"
            ])
        elif domain == "analytical":
            suggestions.extend([
                "Work through problems systematically",
                "Find logical explanations or frameworks",
                "Practice analytical techniques"
            ])

        return suggestions[:5]  # Return up to 5 suggestions

    def _analyze_memory_gaps(self, memory_system: EnhancedMemorySystem,
                           context: Dict[str, Any]) -> List[KnowledgeGap]:
        """Analyze memory system for knowledge gaps"""

        gaps = []
        current_domain = context.get("domain", "general")

        # Check for sparse memory in certain domains
        domain_memories = memory_system.get_memories(limit=50)
        domain_counts = defaultdict(int)

        for memory in domain_memories:
            for topic in memory.topics:
                # Simple domain classification
                if any(domain_word in topic.lower() for domain_word in self.knowledge_domains):
                    for domain in self.knowledge_domains:
                        if domain_word in topic.lower():
                            domain_counts[domain] += 1

        # Identify domains with low memory count
        for domain in self.knowledge_domains:
            if domain_counts[domain] < 3:  # Threshold for "sparse" knowledge
                gap = KnowledgeGap(
                    domain=domain,
                    specific_topic=f"general {domain} knowledge",
                    gap_type="missing_knowledge",
                    importance=0.6,
                    confidence=0.7,
                    related_memories=[],
                    suggested_resources=[
                        f"Study foundational {domain} concepts",
                        f"Practice {domain} skills regularly",
                        f"Find learning resources for {domain}"
                    ],
                    timestamp=datetime.now()
                )
                gaps.append(gap)

        return gaps

    def _analyze_confidence_gaps(self, context: Dict[str, Any],
                                memory_system: EnhancedMemorySystem = None) -> List[KnowledgeGap]:
        """Analyze confidence-accuracy mismatches"""

        gaps = []

        confidence_level = context.get("confidence_level", 0.5)
        actual_accuracy = context.get("actual_accuracy", None)

        if actual_accuracy is not None:
            confidence_gap = abs(confidence_level - actual_accuracy)

            if confidence_gap > 0.3:  # Significant mismatch
                gap_type = "overconfidence" if confidence_level > actual_accuracy else "underconfidence"

                gap = KnowledgeGap(
                    domain="metacognitive",
                    specific_topic="confidence calibration",
                    gap_type=gap_type,
                    importance=0.8,  # High importance for metacognitive gaps
                    confidence=0.9,
                    related_memories=[],
                    suggested_resources=[
                        "Practice estimating confidence levels",
                        "Seek feedback on accuracy of judgments",
                        "Review past predictions vs outcomes"
                    ],
                    timestamp=datetime.now()
                )
                gaps.append(gap)

        return gaps

    def get_gap_analysis(self) -> Dict[str, Any]:
        """Get analysis of knowledge gaps"""

        if not self.knowledge_gaps:
            return {"error": "No knowledge gaps detected"}

        # Most common gap domains
        domain_counts = defaultdict(int)
        for gap in self.knowledge_gaps:
            domain_counts[gap.domain] += 1

        most_common_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Gap type distribution
        gap_type_counts = defaultdict(int)
        for gap in self.knowledge_gaps:
            gap_type_counts[gap.gap_type] += 1

        # High importance gaps
        high_importance_gaps = [gap for gap in self.knowledge_gaps if gap.importance > 0.7]

        # Recent gaps
        recent_gaps = [gap for gap in self.knowledge_gaps
                      if (datetime.now() - gap.timestamp).total_seconds() < 86400]  # Last 24 hours

        # Learning priorities
        priorities = []
        for gap in high_importance_gaps[:5]:
            priorities.append({
                "topic": gap.specific_topic,
                "domain": gap.domain,
                "importance": gap.importance,
                "suggested_action": gap.suggested_resources[0] if gap.suggested_resources else "Research and learn"
            })

        return {
            "analysis_summary": {
                "total_gaps": len(self.knowledge_gaps),
                "high_priority_gaps": len(high_importance_gaps),
                "recent_gaps": len(recent_gaps),
                "domains_affected": len(domain_counts)
            },
            "most_common_domains": [{"domain": domain, "count": count} for domain, count in most_common_domains],
            "gap_type_distribution": dict(gap_type_counts),
            "high_priority_gaps": [
                {
                    "topic": gap.specific_topic,
                    "domain": gap.domain,
                    "type": gap.gap_type,
                    "importance": gap.importance,
                    "suggestions": gap.suggested_resources[:2]
                }
                for gap in high_importance_gaps[:5]
            ],
            "learning_priorities": priorities,
            "recommendations": self._generate_gap_recommendations()
        }

    def _generate_gap_recommendations(self) -> List[str]:
        """Generate recommendations based on knowledge gap analysis"""

        recommendations = []

        if not self.knowledge_gaps:
            return ["Continue exploring and learning. No significant knowledge gaps detected."]

        # Analyze most common gap type
        gap_type_counts = defaultdict(int)
        for gap in self.knowledge_gaps:
            gap_type_counts[gap.gap_type] += 1

        most_common_type = max(gap_type_counts.items(), key=lambda x: x[1])

        if most_common_type[0] == "uncertainty":
            recommendations.append("Focus on building confidence through practice and study")
        elif most_common_type[0] == "missing_concepts":
            recommendations.append("Prioritize foundational knowledge in areas where you're unsure")
        elif most_common_type[0] == "misconceptions":
            recommendations.append("Actively seek to identify and correct misconceptions")
        elif most_common_type[0] == "outdated_info":
            recommendations.append("Regularly update your knowledge in rapidly changing fields")

        # Check for domain-specific patterns
        domain_counts = defaultdict(int)
        for gap in self.knowledge_gaps:
            domain_counts[gap.domain] += 1

        if domain_counts:
            most_challenging_domain = max(domain_counts.items(), key=lambda x: x[1])
            recommendations.append(f"Consider dedicating extra learning time to {most_challenging_domain[0]} concepts")

        # High priority gaps
        high_priority = [gap for gap in self.knowledge_gaps if gap.importance > 0.7]
        if high_priority:
            recommendations.append(f"Address {len(high_priority)} high-priority knowledge gaps soon")

        return recommendations


# ============================================================================
# MAIN METACOGNITIVE MONITOR
# ============================================================================

class MetaCognitiveMonitor:
    """Main orchestrator for meta-cognitive monitoring system"""

    def __init__(self, character_id: str, storage_dir: Path):
        self.character_id = character_id
        self.storage_dir = storage_dir / character_id / "metacognitive"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Initialize sub-systems
        self.state_tracker = CognitiveStateTracker(character_id)
        self.bias_detector = BiasDetector(character_id)
        self.learning_adapter = LearningStrategyAdapter(character_id)
        self.gap_analyzer = KnowledgeGapAnalyzer(character_id)

        # Monitoring state
        self.monitoring_active = False
        self.last_update = datetime.now()
        self.update_interval = 300  # 5 minutes

        # Meta-cognitive metrics
        self.self_awareness_score = 0.5
        self.adaptability_score = 0.5
        self.learning_efficiency = 0.5
        self.bias_detection_rate = 0.0

        # Load existing data
        self.load_metacognitive_data()

    async def start_monitoring(self, memory_system: EnhancedMemorySystem = None,
                             consciousness_system: ConsciousnessMetricsSystem = None):
        """Start real-time meta-cognitive monitoring"""

        self.monitoring_active = True
        self.memory_system = memory_system
        self.consciousness_system = consciousness_system

        print(f"[METACOGNITIVE] Started monitoring for {self.character_id}")

        # Perform initial assessment
        await self.perform_full_assessment()

        # Start monitoring loop (in real implementation, this would run in background)
        # For now, just do one-time assessment
        await self.monitoring_cycle()

    async def monitoring_cycle(self):
        """Single monitoring cycle"""

        if not self.monitoring_active:
            return

        # Gather current context
        context = self._gather_current_context()

        # Update cognitive state
        state_snapshot = self.state_tracker.update_cognitive_state(
            context, self.memory_system
        )

        # Detect biases
        biases = self.bias_detector.analyze_for_biases(
            context.get("content", ""), context, self.memory_system
        )

        # Analyze knowledge gaps
        knowledge_gaps = self.gap_analyzer.analyze_knowledge_gaps(
            context, self.memory_system
        )

        # Recommend learning strategy if in learning context
        learning_strategy = None
        if context.get("learning_context", False):
            learning_strategy = self.learning_adapter.recommend_strategy(
                context, self.memory_system
            )

        # Update meta-cognitive metrics
        self._update_metacognitive_metrics(state_snapshot, biases, knowledge_gaps)

        # Save monitoring data
        self._save_monitoring_snapshot(state_snapshot, biases, knowledge_gaps, learning_strategy)

        self.last_update = datetime.now()

    def _gather_current_context(self) -> Dict[str, Any]:
        """Gather current context for monitoring"""

        context = {
            "timestamp": datetime.now().isoformat(),
            "activity": "general_processing",
            "content": "",
            "learning_context": False,
            "decision_importance": 0.5,
            "confidence_level": 0.7,
            "task_complexity": 0.5,
            "domain": "general"
        }

        # Get context from memory system
        if self.memory_system and hasattr(self.memory_system, 'working_memory'):
            if self.memory_system.working_memory:
                context["content"] = " ".join(self.memory_system.working_memory[-3:])
                context["working_memory_size"] = len(self.memory_system.working_memory)

        # Get context from consciousness system
        if self.consciousness_system:
            context["consciousness_level"] = self.consciousness_system.profile.total_score
            context["metacognitive_awareness"] = self.consciousness_system.profile.indicator_scores.get(
                ConsciousnessIndicator.METACOGNITION,
                type('obj', (object,), {'current_score': 0.5})()
            ).current_score

        return context

    async def perform_full_assessment(self):
        """Perform comprehensive meta-cognitive assessment"""

        print(f"[METACOGNITIVE] Performing full assessment for {self.character_id}")

        # Analyze cognitive state patterns
        state_analysis = self.state_tracker.get_state_analysis()

        # Analyze bias patterns
        bias_analysis = self.bias_detector.get_bias_analysis()

        # Analyze learning effectiveness
        learning_analysis = self.learning_adapter.get_learning_analysis()

        # Analyze knowledge gaps
        gap_analysis = self.gap_analyzer.get_gap_analysis()

        # Generate comprehensive report
        assessment = {
            "character_id": self.character_id,
            "assessment_timestamp": datetime.now().isoformat(),
            "self_awareness_score": self.self_awareness_score,
            "adaptability_score": self.adaptability_score,
            "learning_efficiency": self.learning_efficiency,
            "bias_detection_rate": self.bias_detection_rate,
            "cognitive_state_analysis": state_analysis,
            "bias_analysis": bias_analysis,
            "learning_analysis": learning_analysis,
            "knowledge_gap_analysis": gap_analysis,
            "overall_recommendations": self._generate_overall_recommendations(
                state_analysis, bias_analysis, learning_analysis, gap_analysis
            )
        }

        # Save assessment
        self.save_assessment(assessment)

        return assessment

    def _update_metacognitive_metrics(self, state_snapshot: CognitiveStateSnapshot,
                                    biases: List[BiasDetection],
                                    gaps: List[KnowledgeGap]):
        """Update meta-cognitive metrics based on monitoring data"""

        # Update self-awareness score
        if state_snapshot.confidence_calibration > 0.7:
            self.self_awareness_score = min(1.0, self.self_awareness_score + 0.05)
        elif state_snapshot.confidence_calibration < 0.4:
            self.self_awareness_score = max(0.0, self.self_awareness_score - 0.05)

        # Update bias detection rate
        if biases:
            self.bias_detection_rate = len(biases) / max(1, len(self.bias_detector.bias_history))

        # Update adaptability score
        state_changes = len(set([s.primary_state for s in self.state_tracker.state_history[-10:]]))
        self.adaptability_score = min(1.0, state_changes / 5.0)

        # Update learning efficiency
        if self.learning_adapter.strategy_performance:
            avg_performance = np.mean([
                np.mean(scores) for scores in self.learning_adapter.strategy_performance.values()
            ])
            self.learning_efficiency = avg_performance

    def _save_monitoring_snapshot(self, state_snapshot: CognitiveStateSnapshot,
                                biases: List[BiasDetection],
                                gaps: List[KnowledgeGap],
                                learning_strategy: Optional[LearningStrategyAssessment]):
        """Save monitoring snapshot to disk"""

        snapshot_data = {
            "timestamp": datetime.now().isoformat(),
            "character_id": self.character_id,
            "cognitive_state": state_snapshot.to_dict(),
            "detected_biases": [b.to_dict() for b in biases],
            "knowledge_gaps": [g.to_dict() for g in gaps],
            "learning_strategy": learning_strategy.to_dict() if learning_strategy else None,
            "metacognitive_metrics": {
                "self_awareness_score": self.self_awareness_score,
                "adaptability_score": self.adaptability_score,
                "learning_efficiency": self.learning_efficiency,
                "bias_detection_rate": self.bias_detection_rate
            }
        }

        # Save to daily log file
        filename = f"monitoring_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = self.storage_dir / filename

        try:
            if filepath.exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    data["snapshots"].append(snapshot_data)
            else:
                data = {"character_id": self.character_id, "date": datetime.now().strftime('%Y-%m-%d'), "snapshots": [snapshot_data]}

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"[METACOGNITIVE] Error saving monitoring snapshot: {e}")

    def save_assessment(self, assessment: Dict[str, Any]):
        """Save comprehensive assessment to disk"""

        filename = f"assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.storage_dir / filename

        try:
            with open(filepath, 'w') as f:
                json.dump(assessment, f, indent=2)
            print(f"[METACOGNITIVE] Saved assessment for {self.character_id}")
        except Exception as e:
            print(f"[METACOGNITIVE] Error saving assessment: {e}")

    def _generate_overall_recommendations(self, state_analysis: Dict[str, Any],
                                        bias_analysis: Dict[str, Any],
                                        learning_analysis: Dict[str, Any],
                                        gap_analysis: Dict[str, Any]) -> List[str]:
        """Generate overall recommendations based on all analyses"""

        recommendations = []

        # Cognitive state recommendations
        if "average_cognitive_load" in state_analysis:
            if state_analysis["average_cognitive_load"] > 0.7:
                recommendations.append("Your cognitive load is consistently high. Consider taking breaks and simplifying tasks.")

        # Bias recommendations
        if "recommendations" in bias_analysis:
            recommendations.extend(bias_analysis["recommendations"][:2])

        # Learning recommendations
        if "recommendations" in learning_analysis:
            recommendations.extend(learning_analysis["recommendations"][:2])

        # Knowledge gap recommendations
        if "recommendations" in gap_analysis:
            recommendations.extend(gap_analysis["recommendations"][:2])

        # Meta-cognitive recommendations
        if self.self_awareness_score < 0.5:
            recommendations.append("Work on increasing self-awareness through regular reflection and monitoring.")

        if self.adaptability_score < 0.5:
            recommendations.append("Practice cognitive flexibility by deliberately trying new approaches and perspectives.")

        if not recommendations:
            recommendations.append("Your meta-cognitive functioning appears balanced. Continue current practices.")

        return recommendations[:5]  # Return top 5 recommendations

    def load_metacognitive_data(self):
        """Load existing meta-cognitive data from disk"""

        try:
            # Load recent monitoring data
            latest_file = None
            for file in self.storage_dir.glob("monitoring_*.json"):
                if latest_file is None or file.stat().st_mtime > latest_file.stat().st_mtime:
                    latest_file = file

            if latest_file:
                with open(latest_file, 'r') as f:
                    data = json.load(f)
                    if data.get("snapshots"):
                        latest_snapshot = data["snapshots"][-1]
                        metrics = latest_snapshot.get("metacognitive_metrics", {})
                        self.self_awareness_score = metrics.get("self_awareness_score", 0.5)
                        self.adaptability_score = metrics.get("adaptability_score", 0.5)
                        self.learning_efficiency = metrics.get("learning_efficiency", 0.5)
                        self.bias_detection_rate = metrics.get("bias_detection_rate", 0.0)

                print(f"[METACOGNITIVE] Loaded monitoring data for {self.character_id}")

        except Exception as e:
            print(f"[METACOGNITIVE] Error loading metacognitive data: {e}")

    async def get_metacognitive_report(self) -> Dict[str, Any]:
        """Generate comprehensive meta-cognitive report"""

        # Get analyses from all sub-systems
        state_analysis = self.state_tracker.get_state_analysis()
        bias_analysis = self.bias_detector.get_bias_analysis()
        learning_analysis = self.learning_adapter.get_learning_analysis()
        gap_analysis = self.gap_analyzer.get_gap_analysis()

        return {
            "character_id": self.character_id,
            "report_timestamp": datetime.now().isoformat(),
            "monitoring_status": "active" if self.monitoring_active else "inactive",
            "last_update": self.last_update.isoformat(),
            "metacognitive_metrics": {
                "self_awareness_score": self.self_awareness_score,
                "adaptability_score": self.adaptability_score,
                "learning_efficiency": self.learning_efficiency,
                "bias_detection_rate": self.bias_detection_rate
            },
            "cognitive_state_analysis": state_analysis,
            "bias_analysis": bias_analysis,
            "learning_strategy_analysis": learning_analysis,
            "knowledge_gap_analysis": gap_analysis,
            "recommendations": self._generate_overall_recommendations(
                state_analysis, bias_analysis, learning_analysis, gap_analysis
            ),
            "integration_with_memory_system": self.memory_system is not None,
            "integration_with_consciousness_system": self.consciousness_system is not None
        }

    def stop_monitoring(self):
        """Stop meta-cognitive monitoring"""

        self.monitoring_active = False
        print(f"[METACOGNITIVE] Stopped monitoring for {self.character_id}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def initialize_metacognitive_system(character_id: str, storage_dir: Path,
                                        memory_system: EnhancedMemorySystem = None,
                                        consciousness_system: ConsciousnessMetricsSystem = None) -> MetaCognitiveMonitor:
    """Initialize meta-cognitive system for a character"""

    monitor = MetaCognitiveMonitor(character_id, storage_dir)
    await monitor.start_monitoring(memory_system, consciousness_system)

    return monitor


def get_metacognitive_dashboard_data(character_ids: List[str],
                                   storage_dir: Path) -> Dict[str, Any]:
    """Get aggregated meta-cognitive data for dashboard visualization"""

    dashboard_data = {
        "timestamp": datetime.now().isoformat(),
        "characters": {},
        "system_metrics": {
            "total_characters": len(character_ids),
            "average_self_awareness": 0.0,
            "average_adaptability": 0.0,
            "average_learning_efficiency": 0.0,
            "top_performer": None,
            "most_adaptable": None
        }
    }

    all_self_awareness = []
    all_adaptability = []
    all_learning_efficiency = []

    for char_id in character_ids:
        monitor = MetaCognitiveMonitor(char_id, storage_dir)

        # Get character meta-cognitive data
        char_data = {
            "metacognitive_metrics": {
                "self_awareness_score": monitor.self_awareness_score,
                "adaptability_score": monitor.adaptability_score,
                "learning_efficiency": monitor.learning_efficiency,
                "bias_detection_rate": monitor.bias_detection_rate
            },
            "monitoring_active": monitor.monitoring_active,
            "last_update": monitor.last_update.isoformat()
        }

        dashboard_data["characters"][char_id] = char_data

        # Collect for system metrics
        all_self_awareness.append(monitor.self_awareness_score)
        all_adaptability.append(monitor.adaptability_score)
        all_learning_efficiency.append(monitor.learning_efficiency)

    # Calculate system metrics
    if all_self_awareness:
        dashboard_data["system_metrics"]["average_self_awareness"] = np.mean(all_self_awareness)
        dashboard_data["system_metrics"]["average_adaptability"] = np.mean(all_adaptability)
        dashboard_data["system_metrics"]["average_learning_efficiency"] = np.mean(all_learning_efficiency)

        # Find top performer (overall meta-cognitive score)
        overall_scores = [
            (sa + ad + le) / 3 for sa, ad, le in
            zip(all_self_awareness, all_adaptability, all_learning_efficiency)
        ]
        if overall_scores:
            top_idx = overall_scores.index(max(overall_scores))
            dashboard_data["system_metrics"]["top_performer"] = character_ids[top_idx]

            # Find most adaptable
            adaptable_idx = all_adaptability.index(max(all_adaptability))
            dashboard_data["system_metrics"]["most_adaptable"] = character_ids[adaptable_idx]

    return dashboard_data


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================

async def demonstrate_metacognitive_system():
    """Demonstrate the meta-cognitive system with a test character"""

    print("=== Meta-Cognitive Self-Monitoring System Demo ===")

    # Create test character and systems
    character_id = "demo_character"
    storage_dir = Path("ai_society_data") / "test_metacognitive"

    # Initialize memory system
    memory_system = EnhancedMemorySystem(character_id, storage_dir / "memories")

    # Add some test memories
    memory_system.add_memory(
        "I'm not sure about this concept, but I think it might be related to what I learned before",
        MemoryType.LEARNING,
        importance=6,
        topics=["learning", "uncertainty"],
        emotional_valence=0.2
    )

    memory_system.add_memory(
        "I definitely know that I'm right about this. Everyone else is wrong.",
        MemoryType.SELF_REFLECTION,
        importance=5,
        topics=["confidence", "social"],
        emotional_valence=0.8
    )

    # Initialize consciousness system
    consciousness_system = ConsciousnessMetricsSystem(character_id, storage_dir / "consciousness")

    # Initialize meta-cognitive system
    meta_system = await initialize_metacognitive_system(
        character_id, storage_dir, memory_system, consciousness_system
    )

    # Perform monitoring cycle
    await meta_system.monitoring_cycle()

    # Generate report
    report = await meta_system.get_metacognitive_report()

    print(f"\nCharacter: {report['character_id']}")
    print(f"Self-Awareness Score: {report['metacognitive_metrics']['self_awareness_score']:.2f}")
    print(f"Adaptability Score: {report['metacognitive_metrics']['adaptability_score']:.2f}")
    print(f"Learning Efficiency: {report['metacognitive_metrics']['learning_efficiency']:.2f}")
    print(f"Bias Detection Rate: {report['metacognitive_metrics']['bias_detection_rate']:.2f}")

    print("\nTop Recommendations:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")

    print("\nCognitive State Analysis:")
    if "most_common_states" in report['cognitive_state_analysis']:
        for state_data in report['cognitive_state_analysis']['most_common_states'][:3]:
            print(f"- {state_data['state']}: {state_data['frequency']} occurrences")

    print("\nBias Analysis:")
    if "most_common_biases" in report['bias_analysis']:
        for bias_data in report['bias_analysis']['most_common_biases'][:3]:
            print(f"- {bias_data['bias'].replace('_', ' ')}: {bias_data['count']} detections")

    print("\n=== Demo Complete ===")

    return meta_system


if __name__ == "__main__":
    # Run demonstration
    asyncio.run(demonstrate_metacognitive_system())