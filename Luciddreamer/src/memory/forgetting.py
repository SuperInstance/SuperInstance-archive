"""
Forgetting Mechanisms and Memory Pruning

Implements biologically-inspired forgetting curves and memory pruning algorithms.
Manages memory capacity through selective forgetting, compression, and archival.
Supports different forgetting patterns for different memory types.
"""

import time
import math
import random
import threading
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ForgettingCurve(Enum):
    """Types of forgetting curves"""
    EXPONENTIAL = "exponential"         # Ebbinghaus forgetting curve
    POWER_LAW = "power_law"            # Power law forgetting
    LOGARITHMIC = "logarithmic"        # Logarithmic decay
    LINEAR = "linear"                  # Linear decay
    SIGMOID = "sigmoid"                # S-shaped forgetting

class ForgettingTrigger(Enum):
    """Triggers for forgetting processes"""
    TIME_BASED = "time_based"          # Time-based decay
    CAPACITY_BASED = "capacity_based"   # Memory capacity pressure
    INTERFERENCE = "interference"      # Interference-based forgetting
    RETRIEVAL_BASED = "retrieval_based" # Retrieval-induced forgetting
    CONSOLIDATION = "consolidation"    # Consolidation-related pruning
    EMOTIONAL_DECAY = "emotional_decay" # Emotional decay

class MemoryStatus(Enum):
    """Memory status after forgetting evaluation"""
    ACTIVE = "active"                  # Strong and accessible
    WEAKENING = "weakening"           # Starting to decay
    COMPRESSED = "compressed"          # Compressed but preserved
    ARCHIVED = "archived"              # Archived for long-term storage
    PRUNED = "pruned"                 # Marked for deletion

@dataclass
class ForgettingParameters:
    """Parameters for forgetting calculations"""
    curve_type: ForgettingCurve = ForgettingCurve.EXPONENTIAL
    decay_rate: float = 0.1            # Base decay rate
    retention_strength: float = 0.5    # Current retention strength
    last_accessed: float = field(default_factory=time.time)
    creation_time: float = field(default_factory=time.time)
    access_frequency: float = 0.0      # Access frequency
    emotional_importance: float = 0.5  # Emotional significance
    rehearsal_count: int = 0          # Number of rehearsals
    interference_level: float = 0.0    # Interference from other memories

@dataclass
class ForgettingResult:
    """Result of forgetting calculation"""
    memory_id: str
    current_strength: float
    predicted_strength: float
    forgetting_amount: float
    new_status: MemoryStatus
    recommended_action: str
    confidence: float

@dataclass
class PruningCandidate:
    """Memory candidate for pruning"""
    memory_id: str
    memory_type: str
    current_strength: float
    utility_score: float
    redundancy_score: float
    access_frequency: float
    age_days: float
    pruning_priority: float

class ForgettingMechanism:
    """
    Implements biologically-inspired forgetting mechanisms.
    Models how memories decay over time based on usage patterns and interference.
    """

    def __init__(self):
        """Initialize forgetting mechanism"""
        self.forgetting_history: List[ForgettingResult] = []
        self.forgetting_statistics = {
            "total_forgetting_events": 0,
            "average_decay_rate": 0.0,
            "memory_status_distribution": {}
        }

    def calculate_forgetting(self, params: ForgettingParameters,
                           current_time: float = None) -> float:
        """
        Calculate memory strength decay based on forgetting parameters

        Args:
            params: Forgetting parameters
            current_time: Current timestamp

        Returns:
            New memory strength (0-1)
        """
        if current_time is None:
            current_time = time.time()

        time_elapsed = current_time - params.last_accessed
        days_elapsed = time_elapsed / (24 * 3600)

        # Calculate decay based on curve type
        if params.curve_type == ForgettingCurve.EXPONENTIAL:
            # Ebbinghaus forgetting curve: R(t) = R₀ * e^(-t/S)
            decay_factor = math.exp(-days_elapsed / (1.0 / params.decay_rate))
        elif params.curve_type == ForgettingCurve.POWER_LAW:
            # Power law: R(t) = R₀ * t^(-α)
            if days_elapsed > 0:
                decay_factor = days_elapsed ** (-params.decay_rate)
            else:
                decay_factor = 1.0
        elif params.curve_type == ForgettingCurve.LOGARITHMIC:
            # Logarithmic decay
            decay_factor = 1.0 / (1.0 + params.decay_rate * math.log(1 + days_elapsed))
        elif params.curve_type == ForgettingCurve.LINEAR:
            # Linear decay
            decay_factor = max(0.0, 1.0 - params.decay_rate * days_elapsed)
        elif params.curve_type == ForgettingCurve.SIGMOID:
            # S-shaped decay
            x = days_elapsed * params.decay_rate - 2.0
            decay_factor = 1.0 / (1.0 + math.exp(x))
        else:
            # Default to exponential
            decay_factor = math.exp(-days_elapsed / (1.0 / params.decay_rate))

        # Apply modifiers
        # Frequency modifier (frequently accessed memories decay slower)
        frequency_modifier = 1.0 + (params.access_frequency * 0.5)

        # Rehearsal modifier (rehearsed memories are strengthened)
        rehearsal_modifier = 1.0 + (params.rehearsal_count * 0.1)

        # Emotional modifier (emotionally significant memories decay slower)
        emotional_modifier = 1.0 + (params.emotional_importance * 0.3)

        # Interference modifier (interference speeds up forgetting)
        interference_modifier = 1.0 - (params.interference_level * 0.4)

        # Apply all modifiers
        total_modifier = (frequency_modifier * rehearsal_modifier *
                         emotional_modifier * interference_modifier)

        # Calculate new strength
        new_strength = params.retention_strength * decay_factor * total_modifier

        # Clamp to valid range
        return max(0.0, min(1.0, new_strength))

    def evaluate_memory_status(self, current_strength: float,
                             age_days: float, access_frequency: float,
                             utility_score: float = 0.5) -> MemoryStatus:
        """
        Evaluate the status of a memory based on its strength and usage

        Args:
            current_strength: Current memory strength
            age_days: Age in days
            access_frequency: Access frequency
            utility_score: Utility/importance score

        Returns:
            Memory status
        """
        # Strong, recently accessed memories
        if current_strength > 0.7 and access_frequency > 0.5:
            return MemoryStatus.ACTIVE

        # Weakening but still useful
        elif current_strength > 0.4 and utility_score > 0.3:
            return MemoryStatus.WEAKENING

        # Old but potentially valuable memories
        elif age_days > 30 and utility_score > 0.6:
            return MemoryStatus.ARCHIVED

        # Low strength, compress to save space
        elif current_strength > 0.2 and utility_score > 0.2:
            return MemoryStatus.COMPRESSED

        # Very weak or unused memories
        else:
            return MemoryStatus.PRUNED

    def recommend_action(self, status: MemoryStatus, current_strength: float,
                        utility_score: float) -> str:
        """
        Recommend action for a memory based on its status

        Args:
            status: Memory status
            current_strength: Current strength
            utility_score: Utility score

        Returns:
            Recommended action
        """
        if status == MemoryStatus.ACTIVE:
            return "maintain"
        elif status == MemoryStatus.WEAKENING:
            if current_strength < 0.3:
                return "rehearse"
            else:
                return "monitor"
        elif status == MemoryStatus.COMPRESSED:
            return "compress"
        elif status == MemoryStatus.ARCHIVED:
            return "archive"
        elif status == MemoryStatus.PRUNED:
            if utility_score > 0.3:
                return "review_before_delete"
            else:
                return "delete"
        else:
            return "monitor"

class MemoryPruning:
    """
    Manages memory capacity through selective pruning and optimization.
    Implements various pruning strategies to maintain optimal memory usage.
    """

    def __init__(self, target_capacity: int = 10000, pruning_threshold: float = 0.9):
        """
        Initialize memory pruning system

        Args:
            target_capacity: Target memory capacity
            pruning_threshold: Threshold for triggering pruning (0-1)
        """
        self.target_capacity = target_capacity
        self.pruning_threshold = pruning_threshold
        self.forgetting_mechanism = ForgettingMechanism()

        # Pruning strategies
        self.pruning_strategies = {
            "least_recently_used": self._prune_lru,
            "least_frequently_used": self._prune_lfu,
            "lowest_utility": self._prune_utility,
            "highest_redundancy": self._prune_redundancy,
            "combined_score": self._prune_combined
        }

        # Statistics
        self.pruning_history: List[Dict[str, Any]] = []
        self.total_pruned = 0
        self.total_compressed = 0
        self.total_archived = 0

    def evaluate_pruning_candidates(self, memories: Dict[str, Dict[str, Any]],
                                   strategy: str = "combined_score") -> List[PruningCandidate]:
        """
        Evaluate memories for pruning based on selected strategy

        Args:
            memories: Dictionary of memory data
            strategy: Pruning strategy to use

        Returns:
            List of pruning candidates sorted by priority
        """
        if strategy not in self.pruning_strategies:
            strategy = "combined_score"

        candidates = []

        for memory_id, memory_data in memories.items():
            candidate = self._create_pruning_candidate(memory_id, memory_data)
            if candidate:
                candidates.append(candidate)

        # Apply selected pruning strategy
        strategy_func = self.pruning_strategies[strategy]
        ranked_candidates = strategy_func(candidates)

        return ranked_candidates

    def prune_memories(self, memories: Dict[str, Dict[str, Any]],
                      target_count: int = None, strategy: str = "combined_score") -> Dict[str, List[str]]:
        """
        Prune memories based on selected strategy

        Args:
            memories: Dictionary of memory data
            target_count: Number of memories to prune
            strategy: Pruning strategy

        Returns:
            Dictionary with pruning results by action type
        """
        current_count = len(memories)
        if current_count <= self.target_capacity:
            return {"to_prune": [], "to_compress": [], "to_archive": []}

        # Calculate how many to prune
        if target_count is None:
            excess = current_count - int(self.target_capacity * self.pruning_threshold)
            target_count = max(1, excess)

        # Get candidates
        candidates = self.evaluate_pruning_candidates(memories, strategy)

        # Categorize candidates
        results = {"to_prune": [], "to_compress": [], "to_archive": []}

        for candidate in candidates[:target_count]:
            if candidate.pruning_priority > 0.8:
                results["to_prune"].append(candidate.memory_id)
            elif candidate.pruning_priority > 0.6:
                results["to_compress"].append(candidate.memory_id)
            else:
                results["to_archive"].append(candidate.memory_id)

        # Update statistics
        self.total_pruned += len(results["to_prune"])
        self.total_compressed += len(results["to_compress"])
        self.total_archived += len(results["to_archive"])

        # Record pruning event
        self.pruning_history.append({
            "timestamp": time.time(),
            "strategy": strategy,
            "total_memories": current_count,
            "pruned_count": len(results["to_prune"]),
            "compressed_count": len(results["to_compress"]),
            "archived_count": len(results["to_archive"]),
            "target_capacity": self.target_capacity
        })

        return results

    def _create_pruning_candidate(self, memory_id: str, memory_data: Dict[str, Any]) -> Optional[PruningCandidate]:
        """Create a pruning candidate from memory data"""
        try:
            # Extract required information
            memory_type = memory_data.get("type", "unknown")
            current_strength = memory_data.get("strength", 0.5)
            utility_score = memory_data.get("utility", 0.5)
            access_frequency = memory_data.get("access_frequency", 0.0)
            creation_time = memory_data.get("created_at", time.time())
            age_days = (time.time() - creation_time) / (24 * 3600)

            # Calculate redundancy score (simplified)
            redundancy_score = self._calculate_redundancy(memory_data)

            # Calculate pruning priority
            pruning_priority = self._calculate_pruning_priority(
                current_strength, utility_score, access_frequency,
                age_days, redundancy_score
            )

            return PruningCandidate(
                memory_id=memory_id,
                memory_type=memory_type,
                current_strength=current_strength,
                utility_score=utility_score,
                redundancy_score=redundancy_score,
                access_frequency=access_frequency,
                age_days=age_days,
                pruning_priority=pruning_priority
            )
        except Exception as e:
            logger.error(f"Error creating pruning candidate for {memory_id}: {e}")
            return None

    def _calculate_redundancy(self, memory_data: Dict[str, Any]) -> float:
        """Calculate redundancy score for a memory"""
        # Simplified redundancy calculation
        # In practice, this would compare content similarity with other memories
        content_length = len(str(memory_data.get("content", "")))
        if content_length == 0:
            return 0.0

        # Heuristic: shorter memories might be more redundant
        redundancy = min(1.0, 100.0 / content_length)
        return redundancy

    def _calculate_pruning_priority(self, strength: float, utility: float,
                                  frequency: float, age_days: float,
                                  redundancy: float) -> float:
        """Calculate overall pruning priority"""
        # Lower strength and utility = higher priority
        strength_factor = 1.0 - strength
        utility_factor = 1.0 - utility

        # Lower frequency = higher priority
        frequency_factor = 1.0 - frequency

        # Higher age = higher priority (but with diminishing returns)
        age_factor = min(1.0, age_days / 365.0)  # Normalize to years

        # Higher redundancy = higher priority
        redundancy_factor = redundancy

        # Weighted combination
        priority = (
            strength_factor * 0.3 +
            utility_factor * 0.25 +
            frequency_factor * 0.2 +
            age_factor * 0.15 +
            redundancy_factor * 0.1
        )

        return min(1.0, priority)

    def _prune_lru(self, candidates: List[PruningCandidate]) -> List[PruningCandidate]:
        """Least Recently Used pruning strategy"""
        # Sort by last access time (use age_days as proxy)
        candidates.sort(key=lambda c: c.age_days, reverse=True)
        return candidates

    def _prune_lfu(self, candidates: List[PruningCandidate]) -> List[PruningCandidate]:
        """Least Frequently Used pruning strategy"""
        candidates.sort(key=lambda c: c.access_frequency)
        return candidates

    def _prune_utility(self, candidates: List[PruningCandidate]) -> List[PruningCandidate]:
        """Lowest utility pruning strategy"""
        candidates.sort(key=lambda c: c.utility_score)
        return candidates

    def _prune_redundancy(self, candidates: List[PruningCandidate]) -> List[PruningCandidate]:
        """Highest redundancy pruning strategy"""
        candidates.sort(key=lambda c: c.redundancy_score, reverse=True)
        return candidates

    def _prune_combined(self, candidates: List[PruningCandidate]) -> List[PruningCandidate]:
        """Combined score pruning strategy"""
        candidates.sort(key=lambda c: c.pruning_priority, reverse=True)
        return candidates

    def get_pruning_statistics(self) -> Dict[str, Any]:
        """Get pruning statistics"""
        return {
            "total_pruned": self.total_pruned,
            "total_compressed": self.total_compressed,
            "total_archived": self.total_archived,
            "target_capacity": self.target_capacity,
            "pruning_threshold": self.pruning_threshold,
            "pruning_events": len(self.pruning_history),
            "available_strategies": list(self.pruning_strategies.keys())
        }

class MemoryCompression:
    """
    Implements memory compression techniques to preserve important information
    while reducing storage requirements.
    """

    def __init__(self):
        """Initialize memory compression system"""
        self.compression_history: List[Dict[str, Any]] = []
        self.compression_statistics = {
            "total_compressed": 0,
            "space_saved": 0,
            "average_compression_ratio": 0.0
        }

    def compress_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compress a memory while preserving essential information

        Args:
            memory_data: Original memory data

        Returns:
            Compressed memory data
        """
        original_size = self._estimate_size(memory_data)

        compressed_data = {
            "id": memory_data.get("id"),
            "type": memory_data.get("type"),
            "created_at": memory_data.get("created_at"),
            "compressed": True,
            "compression_version": "1.0"
        }

        # Extract key information based on memory type
        if memory_data.get("type") == "episodic":
            compressed_data.update(self._compress_episodic_memory(memory_data))
        elif memory_data.get("type") == "semantic":
            compressed_data.update(self._compress_semantic_memory(memory_data))
        elif memory_data.get("type") == "procedural":
            compressed_data.update(self._compress_procedural_memory(memory_data))
        else:
            # Generic compression
            compressed_data.update(self._compress_generic_memory(memory_data))

        compressed_size = self._estimate_size(compressed_data)
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0

        # Record compression
        self.compression_history.append({
            "timestamp": time.time(),
            "memory_id": memory_data.get("id"),
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": compression_ratio
        })

        # Update statistics
        self.total_compressed += 1
        self.space_saved += original_size - compressed_size
        self.average_compression_ratio = (
            (self.average_compression_ratio * (self.total_compressed - 1) + compression_ratio) /
            self.total_compressed
        )

        logger.debug(f"Compressed memory {memory_data.get('id')}: {compression_ratio:.2f} ratio")
        return compressed_data

    def _compress_episodic_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress episodic memory"""
        content = memory_data.get("content", "")

        # Extract key elements
        summary = content[:200] + "..." if len(content) > 200 else content
        key_entities = self._extract_entities(content)
        emotional_summary = memory_data.get("emotional_valence", "neutral")

        return {
            "summary": summary,
            "key_entities": key_entities[:10],  # Keep top 10 entities
            "emotional_summary": emotional_summary,
            "importance": memory_data.get("importance", 0.5)
        }

    def _compress_semantic_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress semantic memory"""
        return {
            "concept": memory_data.get("concept", ""),
            "definition": memory_data.get("definition", "")[:200],
            "relationships": memory_data.get("relationships", {})[:20],  # Keep top 20 relationships
            "importance": memory_data.get("importance", 0.5)
        }

    def _compress_procedural_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress procedural memory"""
        return {
            "skill": memory_data.get("skill", ""),
            "mastery_level": memory_data.get("mastery_level", 0.0),
            "practice_count": memory_data.get("practice_count", 0),
            "key_steps": memory_data.get("steps", [])[:5]  # Keep key steps
        }

    def _compress_generic_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress generic memory"""
        content = memory_data.get("content", "")
        summary = content[:300] + "..." if len(content) > 300 else content

        return {
            "summary": summary,
            "tags": memory_data.get("tags", [])[:10],
            "importance": memory_data.get("importance", 0.5)
        }

    def _extract_entities(self, text: str) -> List[str]:
        """Extract key entities from text (simplified)"""
        # Simple keyword extraction
        words = text.lower().split()
        # Filter out common words and keep important ones
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        entities = [word for word in words if word not in stop_words and len(word) > 3]

        # Return most common entities
        from collections import Counter
        common_entities = [word for word, count in Counter(entities).most_common(20)]
        return common_entities

    def _estimate_size(self, data: Any) -> int:
        """Estimate memory size of data structure"""
        import sys
        return sys.getsizeof(str(data))

    def get_compression_statistics(self) -> Dict[str, Any]:
        """Get compression statistics"""
        return self.compression_statistics.copy()