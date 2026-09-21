"""
Memory Consolidation Pipeline

Implements memory consolidation with KL divergence surprise detection,
importance-based filtering, and automatic knowledge extraction.
Manages the transfer of memories from working memory to long-term storage
and optimization of memory networks.
"""

import time
import math
import numpy as np
import threading
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class ConsolidationTrigger(Enum):
    """Triggers for memory consolidation"""
    TIME_BASED = "time_based"           # Periodic consolidation
    CAPACITY_BASED = "capacity_based"   # When working memory is full
    IMPORTANCE_BASED = "importance_based"  # High-importance memories
    SURPRISE_BASED = "surprise_based"   # Unexpected events
    SLEEP_BASED = "sleep_based"         # Sleep/periodic consolidation
    EMOTIONAL_BASED = "emotional_based"  # High emotional impact

class MemoryType(Enum):
    """Types of memories for consolidation"""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"

@dataclass
class ConsolidationCandidate:
    """Memory candidate for consolidation"""
    memory_id: str
    memory_type: MemoryType
    content: Any
    importance: float
    novelty: float
    emotional_impact: float
    surprise_score: float
    access_frequency: float
    age_hours: float
    consolidation_priority: float = 0.0

@dataclass
class ConsolidationResult:
    """Result of memory consolidation"""
    success: bool
    consolidated_memories: List[str]
    extracted_facts: List[str]
    extracted_concepts: List[str]
    strengthened_memories: List[str]
    pruned_memories: List[str]
    processing_time: float
    errors: List[str] = field(default_factory=list)

class SurpriseDetector:
    """
    Detects surprising events using KL divergence and statistical anomaly detection.
    Measures how unexpected new experiences are based on historical patterns.
    """

    def __init__(self, history_window: int = 100, sensitivity: float = 0.5):
        """
        Initialize surprise detector

        Args:
            history_window: Number of past experiences to consider
            sensitivity: Sensitivity threshold for surprise detection
        """
        self.history_window = history_window
        self.sensitivity = sensitivity
        self.experience_history: List[Dict[str, Any]] = []
        self.pattern_models: Dict[str, Any] = {}
        self.vocabulary_counts: Dict[str, int] = defaultdict(int)
        self.topic_distribution: Dict[str, float] = {}
        self.emotion_patterns: Dict[str, float] = defaultdict(float)

    def add_experience(self, content: str, emotional_valence: float,
                      context_tags: Set[str], timestamp: float = None):
        """
        Add a new experience to history

        Args:
            content: Experience content
            emotional_valence: Emotional valence (-1 to 1)
            context_tags: Context tags
            timestamp: Experience timestamp
        """
        if timestamp is None:
            timestamp = time.time()

        experience = {
            "content": content,
            "emotional_valence": emotional_valence,
            "context_tags": context_tags,
            "timestamp": timestamp,
            "word_frequencies": self._extract_word_frequencies(content),
            "topics": self._extract_topics(content)
        }

        self.experience_history.append(experience)

        # Maintain history window
        if len(self.experience_history) > self.history_window:
            self.experience_history.pop(0)

        # Update pattern models
        self._update_patterns(experience)

    def calculate_surprise(self, content: str, emotional_valence: float,
                          context_tags: Set[str]) -> float:
        """
        Calculate surprise score for new experience

        Args:
            content: Experience content
            emotional_valence: Emotional valence
            context_tags: Context tags

        Returns:
            Surprise score (0-1)
        """
        if len(self.experience_history) < 3:  # Need baseline
            return 0.5

        # Extract features
        word_frequencies = self._extract_word_frequencies(content)
        topics = self._extract_topics(content)

        # Calculate KL divergence for content
        content_surprise = self._calculate_content_surprise(word_frequencies)

        # Calculate emotional surprise
        emotional_surprise = self._calculate_emotional_surprise(emotional_valence)

        # Calculate contextual surprise
        contextual_surprise = self._calculate_contextual_surprise(context_tags)

        # Calculate topical surprise
        topical_surprise = self._calculate_topical_surprise(topics)

        # Weighted combination
        surprise = (
            0.4 * content_surprise +
            0.2 * emotional_surprise +
            0.2 * contextual_surprise +
            0.2 * topical_surprise
        )

        return min(1.0, max(0.0, surprise))

    def _extract_word_frequencies(self, content: str) -> Dict[str, float]:
        """Extract normalized word frequencies from content"""
        words = content.lower().split()
        word_counts = defaultdict(int)

        for word in words:
            # Simple word cleaning
            clean_word = ''.join(c for c in word if c.isalnum())
            if clean_word:
                word_counts[clean_word] += 1

        # Normalize
        total_words = sum(word_counts.values())
        if total_words > 0:
            return {word: count / total_words for word, count in word_counts.items()}
        return {}

    def _extract_topics(self, content: str) -> Set[str]:
        """Extract simple topic indicators from content"""
        # Simple keyword-based topic extraction
        topic_keywords = {
            "social": ["friend", "person", "people", "talk", "conversation", "relationship"],
            "combat": ["fight", "battle", "attack", "defend", "weapon", "enemy"],
            "exploration": ["discover", "explore", "find", "search", "location", "place"],
            "survival": ["food", "water", "shelter", "danger", "survive", "resource"],
            "knowledge": ["learn", "know", "information", "book", "study", "understand"],
            "emotion": ["feel", "emotion", "happy", "sad", "angry", "excited"],
            "action": ["do", "action", "move", "go", "run", "walk", "act"]
        }

        content_lower = content.lower()
        topics = set()

        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                topics.add(topic)

        return topics

    def _update_patterns(self, experience: Dict[str, Any]):
        """Update statistical pattern models"""
        # Update vocabulary
        for word, freq in experience["word_frequencies"].items():
            self.vocabulary_counts[word] += int(freq * 100)  # Scale for counting

        # Update topic distribution
        for topic in experience["topics"]:
            self.topic_distribution[topic] = self.topic_distribution.get(topic, 0) + 1

        # Update emotion patterns
        for tag in experience["context_tags"]:
            self.emotion_patterns[tag] = (
                self.emotion_patterns[tag] * 0.9 + experience["emotional_valence"] * 0.1
            )

    def _calculate_content_surprise(self, word_frequencies: Dict[str, float]) -> float:
        """Calculate content surprise using KL divergence"""
        if not self.experience_history:
            return 0.5

        # Build reference distribution from history
        total_words = sum(self.vocabulary_counts.values())
        if total_words == 0:
            return 0.5

        reference_dist = {word: count / total_words for word, count in self.vocabulary_counts.items()}

        # Calculate KL divergence
        kl_divergence = 0.0
        for word, freq in word_frequencies.items():
            if word in reference_dist and freq > 0:
                kl_divergence += freq * math.log(freq / reference_dist[word])

        # Normalize KL divergence (typical range 0-5)
        return min(1.0, kl_divergence / 5.0)

    def _calculate_emotional_surprise(self, emotional_valence: float) -> float:
        """Calculate emotional surprise based on deviation from patterns"""
        if not self.experience_history:
            return 0.5

        # Calculate average emotional valence from history
        avg_emotion = sum(exp["emotional_valence"] for exp in self.experience_history) / len(self.experience_history)

        # Calculate standard deviation
        variance = sum((exp["emotional_valence"] - avg_emotion) ** 2 for exp in self.experience_history) / len(self.experience_history)
        std_dev = math.sqrt(variance) if variance > 0 else 0.1

        # Calculate z-score (how many standard deviations from mean)
        z_score = abs(emotional_valence - avg_emotion) / std_dev

        # Convert to surprise score (0-1)
        return min(1.0, z_score / 3.0)  # 3 standard deviations = max surprise

    def _calculate_contextual_surprise(self, context_tags: Set[str]) -> float:
        """Calculate surprise based on unusual context combinations"""
        if not self.experience_history:
            return 0.5

        # Count context tag frequencies in history
        context_counts = defaultdict(int)
        for exp in self.experience_history:
            for tag in exp["context_tags"]:
                context_counts[tag] += 1

        total_contexts = sum(context_counts.values())
        if total_contexts == 0:
            return 0.5

        # Calculate average surprise for tags
        tag_surprises = []
        for tag in context_tags:
            tag_frequency = context_counts.get(tag, 0) / total_contexts
            # Rare tags are more surprising
            tag_surprise = -math.log(tag_frequency + 1e-10) / 10  # Scale to 0-1 range
            tag_surprises.append(min(1.0, tag_surprise))

        return sum(tag_surprises) / len(tag_surprises) if tag_surprises else 0.5

    def _calculate_topical_surprise(self, topics: Set[str]) -> float:
        """Calculate surprise based on topic novelty"""
        if not topics or not self.topic_distribution:
            return 0.5

        total_topics = sum(self.topic_distribution.values())
        topic_surprises = []

        for topic in topics:
            topic_frequency = self.topic_distribution.get(topic, 0) / total_topics
            # Rare topics are more surprising
            topic_surprise = -math.log(topic_frequency + 1e-10) / 5  # Scale to 0-1 range
            topic_surprises.append(min(1.0, topic_surprise))

        return sum(topic_surprises) / len(topic_surprises) if topic_surprises else 0.5

class MemoryConsolidation:
    """
    Memory consolidation pipeline that manages the transfer and optimization
    of memories across different memory systems.
    """

    def __init__(self, consolidation_interval: float = 300.0,  # 5 minutes
                 importance_threshold: float = 0.3,
                 surprise_threshold: float = 0.6):
        """
        Initialize memory consolidation system

        Args:
            consolidation_interval: Time between consolidation cycles (seconds)
            importance_threshold: Minimum importance for consolidation
            surprise_threshold: Surprise threshold for immediate consolidation
        """
        self.consolidation_interval = consolidation_interval
        self.importance_threshold = importance_threshold
        self.surprise_threshold = surprise_threshold

        self.surprise_detector = SurpriseDetector()
        self.consolidation_queue: List[ConsolidationCandidate] = []
        self.consolidation_history: List[ConsolidationResult] = []

        self.running = False
        self.consolidation_thread = None

        # Statistics
        self.total_consolidations = 0
        self.successful_consolidations = 0
        self.total_surprising_events = 0

    def start(self):
        """Start the consolidation background thread"""
        if self.running:
            return

        self.running = True
        self.consolidation_thread = threading.Thread(
            target=self._consolidation_loop,
            daemon=True,
            name="MemoryConsolidation"
        )
        self.consolidation_thread.start()
        logger.info("Memory consolidation system started")

    def stop(self):
        """Stop the consolidation system"""
        self.running = False
        if self.consolidation_thread and self.consolidation_thread.is_alive():
            self.consolidation_thread.join(timeout=10.0)
        logger.info("Memory consolidation system stopped")

    def add_consolidation_candidate(self, memory_id: str, memory_type: MemoryType,
                                   content: Any, importance: float, novelty: float,
                                   emotional_impact: float, access_frequency: float,
                                   age_hours: float):
        """
        Add a memory as a consolidation candidate

        Args:
            memory_id: Memory identifier
            memory_type: Type of memory
            content: Memory content
            importance: Importance score (0-1)
            novelty: Novelty score (0-1)
            emotional_impact: Emotional impact (0-1)
            access_frequency: Access frequency
            age_hours: Age in hours
        """
        # Calculate surprise score
        content_str = str(content) if isinstance(content, str) else ""
        if content_str:
            surprise_score = self.surprise_detector.calculate_surprise(
                content_str, emotional_impact, set()
            )
        else:
            surprise_score = 0.0

        # Create candidate
        candidate = ConsolidationCandidate(
            memory_id=memory_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            novelty=novelty,
            emotional_impact=emotional_impact,
            surprise_score=surprise_score,
            access_frequency=access_frequency,
            age_hours=age_hours
        )

        # Calculate consolidation priority
        candidate.consolidation_priority = self._calculate_consolidation_priority(candidate)

        # Add to queue if meets threshold
        if candidate.consolidation_priority >= self.importance_threshold:
            self.consolidation_queue.append(candidate)

            # Immediate consolidation for surprising events
            if surprise_score >= self.surprise_threshold:
                self.total_surprising_events += 1
                logger.info(f"Immediate consolidation triggered by surprising event: {memory_id[:8]}...")
                self._perform_consolidation([candidate])

    def force_consolidation(self, trigger: ConsolidationTrigger = ConsolidationTrigger.TIME_BASED) -> ConsolidationResult:
        """
        Force immediate consolidation

        Args:
            trigger: Reason for forced consolidation

        Returns:
            Consolidation result
        """
        if not self.consolidation_queue:
            return ConsolidationResult(
                success=False,
                consolidated_memories=[],
                extracted_facts=[],
                extracted_concepts=[],
                strengthened_memories=[],
                pruned_memories=[],
                processing_time=0.0,
                errors=["No consolidation candidates available"]
            )

        # Select candidates for consolidation
        candidates = self._select_consolidation_candidates()

        return self._perform_consolidation(candidates, trigger)

    def _consolidation_loop(self):
        """Background consolidation loop"""
        while self.running:
            try:
                # Check if consolidation is needed
                if self._should_consolidate():
                    candidates = self._select_consolidation_candidates()
                    if candidates:
                        self._perform_consolidation(candidates, ConsolidationTrigger.TIME_BASED)

                # Wait for next cycle
                time.sleep(self.consolidation_interval)

            except Exception as e:
                logger.error(f"Error in consolidation loop: {e}")

    def _should_consolidate(self) -> bool:
        """Check if consolidation should be triggered"""
        # Consolidate if queue is large enough
        if len(self.consolidation_queue) >= 10:
            return True

        # Consolidate if high-priority items exist
        for candidate in self.consolidation_queue:
            if candidate.consolidation_priority >= 0.8:
                return True

        return False

    def _select_consolidation_candidates(self, max_candidates: int = 20) -> List[ConsolidationCandidate]:
        """Select best candidates for consolidation"""
        if not self.consolidation_queue:
            return []

        # Sort by priority
        sorted_candidates = sorted(self.consolidation_queue, key=lambda c: c.consolidation_priority, reverse=True)

        # Select top candidates
        selected = sorted_candidates[:max_candidates]

        # Remove selected from queue
        for candidate in selected:
            if candidate in self.consolidation_queue:
                self.consolidation_queue.remove(candidate)

        return selected

    def _perform_consolidation(self, candidates: List[ConsolidationCandidate],
                              trigger: ConsolidationTrigger = ConsolidationTrigger.TIME_BASED) -> ConsolidationResult:
        """
        Perform consolidation on selected candidates

        Args:
            candidates: List of consolidation candidates
            trigger: Consolidation trigger

        Returns:
            Consolidation result
        """
        start_time = time.time()
        result = ConsolidationResult(
            success=True,
            consolidated_memories=[],
            extracted_facts=[],
            extracted_concepts=[],
            strengthened_memories=[],
            pruned_memories=[],
            processing_time=0.0,
            errors=[]
        )

        try:
            for candidate in candidates:
                try:
                    # Process each candidate based on memory type
                    if candidate.memory_type == MemoryType.WORKING:
                        self._consolidate_working_memory(candidate, result)
                    elif candidate.memory_type == MemoryType.EPISODIC:
                        self._consolidate_episodic_memory(candidate, result)
                    elif candidate.memory_type == MemoryType.SEMANTIC:
                        self._consolidate_semantic_memory(candidate, result)
                    elif candidate.memory_type == MemoryType.PROCEDURAL:
                        self._consolidate_procedural_memory(candidate, result)

                    result.consolidated_memories.append(candidate.memory_id)

                except Exception as e:
                    error_msg = f"Failed to consolidate {candidate.memory_id}: {e}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)

            # Perform post-consolidation optimization
            self._optimize_memory_network(result)

            self.total_consolidations += 1
            if result.success:
                self.successful_consolidations += 1

        except Exception as e:
            result.success = False
            result.errors.append(f"Consolidation failed: {e}")

        result.processing_time = time.time() - start_time
        self.consolidation_history.append(result)

        # Keep history manageable
        if len(self.consolidation_history) > 100:
            self.consolidation_history = self.consolidation_history[-50:]

        logger.info(f"Consolidation completed: {len(result.consolidated_memories)} memories, {result.processing_time:.2f}s")
        return result

    def _consolidate_working_memory(self, candidate: ConsolidationCandidate, result: ConsolidationResult):
        """Consolidate working memory to episodic memory"""
        # Extract episodic memory from working memory content
        content_str = str(candidate.content)

        # Create episodic memory entry
        episodic_data = {
            "content": content_str,
            "importance": candidate.importance,
            "emotional_valence": candidate.emotional_impact,
            "novelty": candidate.novelty,
            "surprise": candidate.surprise_score
        }

        # This would interface with the episodic memory system
        # For now, just track what would be extracted
        result.consolidated_memories.append(candidate.memory_id)

    def _consolidate_episodic_memory(self, candidate: ConsolidationCandidate, result: ConsolidationResult):
        """Consolidate and strengthen episodic memory"""
        # Strengthen existing episodic memory
        result.strengthened_memories.append(candidate.memory_id)

        # Extract semantic facts from episodic content
        content_str = str(candidate.content)
        extracted_facts = self._extract_facts_from_content(content_str)
        result.extracted_facts.extend(extracted_facts)

        # Extract semantic concepts
        extracted_concepts = self._extract_concepts_from_content(content_str)
        result.extracted_concepts.extend(extracted_concepts)

    def _consolidate_semantic_memory(self, candidate: ConsolidationCandidate, result: ConsolidationResult):
        """Consolidate semantic memory and strengthen connections"""
        # Strengthen semantic memory connections
        result.strengthened_memories.append(candidate.memory_id)

    def _consolidate_procedural_memory(self, candidate: ConsolidationCandidate, result: ConsolidationResult):
        """Consolidate procedural memory and update skill mastery"""
        # Update procedural memory
        result.strengthened_memories.append(candidate.memory_id)

    def _extract_facts_from_content(self, content: str) -> List[str]:
        """Extract semantic facts from content"""
        facts = []

        # Simple pattern-based fact extraction
        # In a real implementation, this would use NLP techniques
        content_lower = content.lower()

        # Look for simple factual patterns
        fact_patterns = [
            "is a",
            "is an",
            "has a",
            "can",
            "was",
            "were",
            "will be"
        ]

        words = content_lower.split()
        for i, word in enumerate(words):
            if word in fact_patterns and i < len(words) - 1:
                # Simple fact extraction
                fact = f"{words[i-1] if i > 0 else ''} {word} {words[i+1]}"
                facts.append(fact.strip())

        return facts[:5]  # Limit to top 5 facts

    def _extract_concepts_from_content(self, content: str) -> List[str]:
        """Extract semantic concepts from content"""
        concepts = []

        # Simple keyword-based concept extraction
        # In a real implementation, this would use more sophisticated NLP
        important_words = [
            "person", "place", "thing", "idea", "emotion", "action",
            "relationship", "conflict", "resolution", "discovery",
            "knowledge", "skill", "ability", "problem", "solution"
        ]

        content_lower = content.lower()
        for concept in important_words:
            if concept in content_lower:
                concepts.append(concept)

        return list(set(concepts))  # Remove duplicates

    def _optimize_memory_network(self, result: ConsolidationResult):
        """Optimize memory network after consolidation"""
        # This would implement memory pruning, connection strengthening, etc.
        # For now, just a placeholder
        pass

    def _calculate_consolidation_priority(self, candidate: ConsolidationCandidate) -> float:
        """Calculate consolidation priority for a memory candidate"""
        # Base priority from importance
        priority = candidate.importance * 0.3

        # Novelty factor
        priority += candidate.novelty * 0.2

        # Emotional impact
        priority += candidate.emotional_impact * 0.2

        # Surprise factor (high surprise = high priority)
        priority += candidate.surprise_score * 0.2

        # Access frequency (frequently accessed = higher priority)
        priority += candidate.access_frequency * 0.1

        return min(1.0, priority)

    def get_consolidation_statistics(self) -> Dict[str, Any]:
        """Get statistics about consolidation performance"""
        if not self.consolidation_history:
            return {
                "total_consolidations": 0,
                "success_rate": 0.0,
                "average_processing_time": 0.0,
                "queue_size": 0
            }

        successful = sum(1 for r in self.consolidation_history if r.success)
        avg_time = sum(r.processing_time for r in self.consolidation_history) / len(self.consolidation_history)

        return {
            "total_consolidations": self.total_consolidations,
            "successful_consolidations": self.successful_consolidations,
            "success_rate": successful / len(self.consolidation_history),
            "average_processing_time": avg_time,
            "queue_size": len(self.consolidation_queue),
            "total_surprising_events": self.total_surprising_events,
            "average_queue_priority": sum(c.consolidation_priority for c in self.consolidation_queue) / len(self.consolidation_queue) if self.consolidation_queue else 0.0
        }

    def get_consolidation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent consolidation history"""
        history = []
        for result in self.consolidation_history[-limit:]:
            history.append({
                "timestamp": time.time(),  # Would be stored in actual result
                "success": result.success,
                "consolidated_count": len(result.consolidated_memories),
                "extracted_facts": len(result.extracted_facts),
                "extracted_concepts": len(result.extracted_concepts),
                "strengthened": len(result.strengthened_memories),
                "pruned": len(result.pruned_memories),
                "processing_time": result.processing_time,
                "errors": len(result.errors)
            })
        return history