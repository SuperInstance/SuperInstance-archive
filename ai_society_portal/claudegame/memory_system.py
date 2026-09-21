"""
AI Society Portal - Memory System (Temporal Consciousness Foundation)
======================================================================
Implements hierarchical memory consolidation, autobiographical narratives,
and temporal landmarks. This is the neural foundation of character consciousness.

Weeks 1-2 Implementation: Core Memory Infrastructure
"""

import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import math
import numpy as np
from collections import defaultdict


# ============================================================================
# MEMORY TYPES & ENUMS
# ============================================================================

class MemoryType(Enum):
    """Hierarchical memory tiers (inspired by neuroscience)"""
    WORKING = "working"              # Current attention (LLM context)
    MID_TERM = "mid_term"            # Session buffer (1-6 hours)
    LONG_TERM = "long_term"          # Consolidated storage (1+ weeks)
    EPISODIC = "episodic"            # Specific events "what-where-when"
    SEMANTIC = "semantic"            # Consolidated patterns & facts
    PROCEDURAL = "procedural"        # Skills & learned behaviors


class MemoryImportance(Enum):
    """Importance scoring (affects consolidation priority)"""
    FORGOTTEN = 1.0     # Low priority
    ROUTINE = 3.0       # Normal daily memory
    NOTABLE = 6.0       # Worth remembering
    SIGNIFICANT = 8.0   # Life-changing
    CORE_IDENTITY = 10.0 # Defines who they are


@dataclass
class Memory:
    """Individual memory unit"""
    id: str
    content: str                          # What happened/was learned
    memory_type: MemoryType
    timestamp: datetime
    
    # Metadata
    importance: float = 5.0                # 1-10 scale
    emotional_valence: float = 0.0         # -1 (bad) to +1 (good)
    participants: List[str] = field(default_factory=list)  # Who was involved
    location: str = ""                    # Where it happened
    
    # Consolidation tracking
    access_count: int = 0                 # Times retrieved (boosts importance)
    last_accessed: Optional[datetime] = None
    consolidated: bool = False            # Has it moved to semantic?
    consolidation_source_ids: List[str] = field(default_factory=list)
    
    # Relationship to other memories
    related_memory_ids: List[str] = field(default_factory=list)
    contradicts_memory_ids: List[str] = field(default_factory=list)
    
    # For temporal landmarks
    is_temporal_landmark: bool = False
    landmark_type: Optional[str] = None   # "first", "peak_emotion", "transition", etc
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp.isoformat(),
            "importance": self.importance,
            "emotional_valence": self.emotional_valence,
            "participants": self.participants,
            "location": self.location,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "consolidated": self.consolidated,
            "is_temporal_landmark": self.is_temporal_landmark,
            "landmark_type": self.landmark_type,
        }


@dataclass
class TemporalLandmark:
    """Anchor points in autobiographical memory (like memories form clusters around them)"""
    id: str
    memory_id: str
    landmark_type: str  # "first", "peak_emotion", "transition", "social", "achievement"
    importance_boost: float = 2.0
    related_memory_ids: List[str] = field(default_factory=list)
    narrative_summary: str = ""


@dataclass
class AutobiographicalNarrative:
    """Life story constructed from memories and temporal landmarks"""
    character_id: str
    narrative: str                          # Coherent life story text
    key_themes: List[str] = field(default_factory=list)
    core_identity_traits: Dict[str, float] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    memory_ids_used: List[str] = field(default_factory=list)
    coherence_score: float = 0.0  # 0-1: how coherent is the narrative?
    

# ============================================================================
# MEMORY CONSOLIDATION ENGINE
# ============================================================================

class MemoryConsolidationEngine:
    """
    Implements sleep-like consolidation cycles inspired by neuroscience.
    Moves memories from episodic → semantic with pattern extraction.
    """
    
    def __init__(self, character_id: str):
        self.character_id = character_id
        
        # Memory storage (6-tier system)
        self.memories: Dict[str, Memory] = {}
        self.temporal_landmarks: Dict[str, TemporalLandmark] = {}
        self.autobiographical_narratives: List[AutobiographicalNarrative] = []
        
        # Consolidation state
        self.importance_accumulator: float = 0.0
        self.last_reflection_time: datetime = datetime.now()
        self.last_consolidation_time: datetime = datetime.now()
        
        # Parameters (from research)
        self.REFLECTION_THRESHOLD = 150.0        # Trigger reflection when accumulated
        self.CONSOLIDATION_WINDOW_HOURS = 24     # Consolidate daily
        self.RECENCY_DECAY_RATE = 0.995          # Per hour
        self.EPISODIC_CLUSTER_SIMILARITY = 0.85  # For semantic extraction
        self.TEMPORAL_LANDMARK_SIMILARITY_THRESHOLD = 0.85
        
    def store_memory(self, content: str, memory_type: MemoryType = MemoryType.EPISODIC,
                    importance: float = 5.0, emotional_valence: float = 0.0,
                    participants: List[str] = None, location: str = "") -> Memory:
        """
        Store a new memory and update consolidation tracking.
        """
        memory_id = hashlib.md5(
            f"{self.character_id}{content}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            timestamp=datetime.now(),
            importance=importance,
            emotional_valence=emotional_valence,
            participants=participants or [],
            location=location,
        )
        
        self.memories[memory_id] = memory
        
        # Update importance accumulator for reflection trigger
        self.importance_accumulator += importance
        
        # Check for temporal landmarks (immediate)
        self._check_temporal_landmark(memory)
        
        return memory
    
    def _check_temporal_landmark(self, memory: Memory):
        """
        Detect if memory qualifies as temporal landmark.
        Research: Landmarks organize autobiographical memory into clusters.
        """
        score = 0.0
        landmark_type = None
        
        # FIRST: Check if this is first of its kind in recent history
        recent_similar = self._find_similar_memories(
            memory.content, hours_back=168, limit=3  # Last week
        )
        if len(recent_similar) == 0:
            score += 0.3
            landmark_type = "first"
        
        # PEAK: Check emotional intensity (top 10% of experiences)
        if abs(memory.emotional_valence) > 0.7:
            score += 0.3
            if landmark_type is None:
                landmark_type = "peak_emotion"
        
        # TRANSITION: Check location change
        recent_locations = [
            m.location for m in list(self.memories.values())[-5:]
            if m.location
        ]
        if memory.location and memory.location not in recent_locations:
            score += 0.2
            if landmark_type is None:
                landmark_type = "transition"
        
        # SOCIAL: Check participant count
        if len(memory.participants) >= 3:
            score += 0.2
            if landmark_type is None:
                landmark_type = "social"
        
        # Create landmark if threshold exceeded
        if score >= 0.6:
            landmark_id = f"landmark_{memory.id}"
            landmark = TemporalLandmark(
                id=landmark_id,
                memory_id=memory.id,
                landmark_type=landmark_type or "significant",
                importance_boost=min(score * 2.0, 3.0)
            )
            self.temporal_landmarks[landmark_id] = landmark
            memory.is_temporal_landmark = True
            memory.landmark_type = landmark_type
    
    def reflection_consolidation(self) -> Dict[str, Any]:
        """
        Immediate reflection consolidation (insights phase).
        Triggered when importance_accumulator >= REFLECTION_THRESHOLD.
        Mimics the default mode network synthesizing meaning.
        """
        if self.importance_accumulator < self.REFLECTION_THRESHOLD:
            return {"triggered": False}
        
        # Get recent important memories
        recent_important = self._get_memories_by_importance(
            limit=100, 
            hours_back=24,
            importance_threshold=6.0
        )
        
        if not recent_important:
            return {"triggered": False, "reason": "No important memories"}
        
        # Extract key patterns (simplified - would use LLM in production)
        reflection_content = self._generate_reflection_from_memories(recent_important)
        
        # Store reflection as high-importance memory
        reflection_memory = self.store_memory(
            content=reflection_content,
            memory_type=MemoryType.SEMANTIC,
            importance=8.0,  # Reflections are important
            emotional_valence=np.mean([m.emotional_valence for m in recent_important]),
        )
        
        # Link to source memories
        reflection_memory.consolidation_source_ids = [m.id for m in recent_important]
        
        self.importance_accumulator = 0.0
        self.last_reflection_time = datetime.now()
        
        return {
            "triggered": True,
            "reflection_id": reflection_memory.id,
            "memories_processed": len(recent_important),
            "reflection_summary": reflection_content[:200] + "..."
        }
    
    def episodic_to_semantic_consolidation(self) -> Dict[str, Any]:
        """
        Sleep-like consolidation: Episodic → Semantic (hours/days to weeks).
        Extracts patterns from multiple episodic memories into semantic knowledge.
        Mimics hippocampus → neocortex transfer.
        """
        hours_since_last = (datetime.now() - self.last_consolidation_time).total_seconds() / 3600
        
        if hours_since_last < self.CONSOLIDATION_WINDOW_HOURS:
            return {
                "triggered": False,
                "reason": f"Too soon (consolidation every {self.CONSOLIDATION_WINDOW_HOURS}h)"
            }
        
        # Get unconsolidated episodic memories older than 24h
        unconsolidated = [
            m for m in self.memories.values()
            if not m.consolidated
            and m.memory_type == MemoryType.EPISODIC
            and (datetime.now() - m.timestamp).total_seconds() > 86400
        ]
        
        if len(unconsolidated) < 3:
            return {
                "triggered": False,
                "reason": "Insufficient episodic memories to consolidate"
            }
        
        # Cluster similar memories
        clusters = self._cluster_similar_memories(unconsolidated, threshold=0.85)
        
        consolidated_count = 0
        created_patterns = []
        
        for cluster in clusters:
            if len(cluster) >= 3:  # Need at least 3 instances to be a pattern
                # Extract pattern
                pattern_content = self._extract_pattern_from_cluster(cluster)
                
                # Create semantic memory (consolidated)
                semantic_memory = self.store_memory(
                    content=pattern_content,
                    memory_type=MemoryType.SEMANTIC,
                    importance=7.0,  # Patterns are valuable
                    emotional_valence=np.mean([m.emotional_valence for m in cluster])
                )
                semantic_memory.consolidated = True
                semantic_memory.consolidation_source_ids = [m.id for m in cluster]
                
                # Mark originals as consolidated
                for memory in cluster:
                    memory.consolidated = True
                
                consolidated_count += len(cluster)
                created_patterns.append({
                    "pattern": pattern_content[:100] + "...",
                    "source_count": len(cluster)
                })
        
        self.last_consolidation_time = datetime.now()
        
        return {
            "triggered": True,
            "memories_consolidated": consolidated_count,
            "patterns_created": len(created_patterns),
            "patterns": created_patterns
        }
    
    def generate_autobiographical_narrative(self) -> AutobiographicalNarrative:
        """
        Generate coherent life story from memories, landmarks, and themes.
        This is the autobiographical narrative identity theory component.
        """
        # Get temporal landmarks and important memories
        landmarks = sorted(
            self.temporal_landmarks.values(),
            key=lambda x: self.memories[x.memory_id].timestamp
        )
        
        # Get key memories for narrative
        key_memories = self._get_memories_by_importance(
            limit=20,
            importance_threshold=6.0
        )
        
        # Build narrative structure
        narrative_parts = []
        
        # Opening: Who am I?
        core_traits = self._extract_core_traits()
        core_traits_str = ", ".join([f"{k}:{v:.1f}" for k, v in core_traits.items()])
        narrative_parts.append(f"I am fundamentally: {core_traits_str}")
        
        # Body: Key life events
        for landmark in landmarks[:5]:  # Top 5 landmarks
            memory = self.memories[landmark.memory_id]
            narrative_parts.append(f"• {landmark.landmark_type.upper()}: {memory.content[:150]}")
        
        # Patterns: What I've learned
        semantic_memories = [
            m for m in self.memories.values()
            if m.memory_type == MemoryType.SEMANTIC
        ]
        if semantic_memories:
            narrative_parts.append("What I've learned:")
            for m in semantic_memories[:3]:
                narrative_parts.append(f"  - {m.content[:100]}")
        
        # Closing: Who am I becoming?
        narrative_parts.append("I continue to grow and learn from my experiences.")
        
        narrative_text = "\n".join(narrative_parts)
        
        autobio_narrative = AutobiographicalNarrative(
            character_id=self.character_id,
            narrative=narrative_text,
            key_themes=self._extract_themes_from_memories(key_memories),
            core_identity_traits=core_traits,
            memory_ids_used=[m.id for m in key_memories],
            coherence_score=self._calculate_narrative_coherence(narrative_text, key_memories)
        )
        
        self.autobiographical_narratives.append(autobio_narrative)
        return autobio_narrative
    
    # ======================================================================
    # RETRIEVAL & QUERY METHODS
    # ======================================================================
    
    def retrieve_memories(self, query: str, top_k: int = 10,
                         α_recency: float = 1.0,
                         α_importance: float = 1.0,
                         α_relevance: float = 1.0) -> List[Memory]:
        """
        Weighted retrieval: combines recency, importance, and semantic relevance.
        Mimics human memory retrieval based on multiple factors.
        """
        results = []
        
        for memory in self.memories.values():
            # Recency score (exponential decay per hour)
            hours_ago = (datetime.now() - memory.timestamp).total_seconds() / 3600
            recency = self.RECENCY_DECAY_RATE ** hours_ago
            
            # Importance score (normalized)
            importance = memory.importance / 10.0
            
            # Relevance score (simplified: word overlap, in production use embeddings)
            relevance = self._calculate_relevance(query, memory.content)
            
            # Combined score
            total_weight = α_recency + α_importance + α_relevance
            score = (
                α_recency * recency +
                α_importance * importance +
                α_relevance * relevance
            ) / total_weight
            
            results.append((score, memory))
        
        # Sort by score and return top_k
        results.sort(reverse=True, key=lambda x: x[0])
        retrieved = [m for _, m in results[:top_k]]
        
        # Update access counts
        for memory in retrieved:
            memory.access_count += 1
            memory.last_accessed = datetime.now()
            # Boost importance slightly on retrieval
            memory.importance = min(memory.importance * 1.05, 10.0)
        
        return retrieved
    
    def get_narrative_context(self, limit: int = 5) -> str:
        """Get recent autobiographical narrative for character context"""
        if not self.autobiographical_narratives:
            return "No autobiography generated yet."
        
        latest = self.autobiographical_narratives[-1]
        return latest.narrative
    
    # ======================================================================
    # HELPER METHODS
    # ======================================================================
    
    def _find_similar_memories(self, content: str, hours_back: int = 168,
                              limit: int = 5) -> List[Memory]:
        """Find memories similar to content"""
        cutoff = datetime.now() - timedelta(hours=hours_back)
        recent = [
            m for m in self.memories.values()
            if m.timestamp > cutoff
        ]
        
        # Simple similarity (word overlap, would use embeddings in production)
        scored = [
            (self._calculate_relevance(content, m.content), m)
            for m in recent
        ]
        scored.sort(reverse=True, key=lambda x: x[0])
        
        return [m for _, m in scored[:limit] if scored]
    
    def _get_memories_by_importance(self, limit: int = 10,
                                   hours_back: int = 24,
                                   importance_threshold: float = 0.0) -> List[Memory]:
        """Get most important memories within timeframe"""
        cutoff = datetime.now() - timedelta(hours=hours_back)
        relevant = [
            m for m in self.memories.values()
            if m.timestamp > cutoff and m.importance >= importance_threshold
        ]
        relevant.sort(key=lambda x: x.importance, reverse=True)
        return relevant[:limit]
    
    def _cluster_similar_memories(self, memories: List[Memory],
                                 threshold: float = 0.85) -> List[List[Memory]]:
        """Cluster memories by similarity (for consolidation)"""
        if not memories:
            return []
        
        clusters = []
        used = set()
        
        for i, mem1 in enumerate(memories):
            if i in used:
                continue
            
            cluster = [mem1]
            used.add(i)
            
            for j, mem2 in enumerate(memories[i+1:], start=i+1):
                if j in used:
                    continue
                
                similarity = self._calculate_relevance(mem1.content, mem2.content)
                if similarity >= threshold:
                    cluster.append(mem2)
                    used.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def _calculate_relevance(self, text1: str, text2: str) -> float:
        """Simple relevance calculation (word overlap)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _generate_reflection_from_memories(self, memories: List[Memory]) -> str:
        """Generate reflection/insight from memories"""
        topics = defaultdict(list)
        
        for mem in memories:
            # Extract main topic (first few words)
            words = mem.content.split()[:3]
            topic = " ".join(words)
            topics[topic].append(mem.content)
        
        reflection_parts = []
        for topic, contents in sorted(topics.items(), key=lambda x: len(x[1]), reverse=True)[:3]:
            reflection_parts.append(f"I notice I've been focused on: {topic}")
        
        return "\n".join(reflection_parts) if reflection_parts else "Recent reflections on my experiences."
    
    def _extract_pattern_from_cluster(self, cluster: List[Memory]) -> str:
        """Extract general pattern from similar memories"""
        topics = defaultdict(int)
        
        for mem in cluster:
            words = mem.content.split()[:5]
            for word in words:
                if len(word) > 3:
                    topics[word.lower()] += 1
        
        top_words = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:3]
        words = [w for w, _ in top_words]
        
        return f"Pattern: I consistently experience situations involving {', '.join(words)}"
    
    def _extract_core_traits(self) -> Dict[str, float]:
        """Extract character core traits from memories"""
        traits = defaultdict(lambda: [])
        
        for mem in self.memories.values():
            if mem.importance >= 7.0:  # Only significant memories
                if mem.emotional_valence > 0.5:
                    traits["optimistic"].append(mem.emotional_valence)
                elif mem.emotional_valence < -0.5:
                    traits["cautious"].append(-mem.emotional_valence)
                
                if len(mem.participants) >= 2:
                    traits["social"].append(0.8)
                elif "alone" in mem.content.lower():
                    traits["introspective"].append(0.8)
        
        # Average trait values
        return {
            trait: np.mean(values)
            for trait, values in traits.items()
            if values
        }
    
    def _extract_themes_from_memories(self, memories: List[Memory]) -> List[str]:
        """Extract themes/topics from memories"""
        themes = defaultdict(int)
        
        for mem in memories:
            words = set(w.lower() for w in mem.content.split() if len(w) > 4)
            for word in words:
                themes[word] += 1
        
        sorted_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_themes[:5]]
    
    def _calculate_narrative_coherence(self, narrative: str,
                                       memories: List[Memory]) -> float:
        """Calculate how coherent the narrative is (0-1)"""
        # Check consistency: do memories align with narrative themes?
        words_in_narrative = set(narrative.lower().split())
        
        coherence_scores = []
        for mem in memories:
            words_in_memory = set(mem.content.lower().split())
            overlap = len(words_in_narrative & words_in_memory)
            if overlap > 0:
                coherence_scores.append(min(overlap / len(words_in_narrative), 1.0))
        
        return np.mean(coherence_scores) if coherence_scores else 0.5


# ============================================================================
# IDENTITY PERSISTENCE SYSTEM
# ============================================================================

class IdentityPersistenceSystem:
    """
    Maintains consistent identity while allowing growth.
    Implements psychological continuity theory + personality stability.
    """
    
    def __init__(self, character_id: str, core_traits: Dict[str, float] = None):
        self.character_id = character_id
        
        # Core identity (locked, change very slowly)
        self.core_traits = core_traits or {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5
        }
        
        # Temporal state (changes more frequently)
        self.temporal_traits = self.core_traits.copy()
        
        # Personality evolution history
        self.personality_history: List[Dict] = []
        self.baseline_embedding = None
        
        # Drift detection (EWMA smoothing)
        self.drift_ewma = 0.5
        self.drift_lambda = 0.3  # Exponential smoothing factor
        
        # Parameters
        self.CORE_TRAIT_LEARNING_RATE = 0.001   # Very slow core change
        self.TEMPORAL_TRAIT_LEARNING_RATE = 0.1  # Faster temporal change
        self.DRIFT_THRESHOLD = 0.15              # Alert if drift > 15%
        self.DRIFT_INTERVENTION_THRESHOLD = 0.25
    
    def update_from_behavior(self, behavior_embedding: np.ndarray,
                            confidence: float = 1.0):
        """Update temporal traits based on observed behavior"""
        if self.baseline_embedding is None:
            self.baseline_embedding = behavior_embedding
        
        # Calculate behavioral drift
        drift = self._calculate_drift(behavior_embedding)
        
        # Update EWMA drift tracker
        self.drift_ewma = self.drift_lambda * drift + (1 - self.drift_lambda) * self.drift_ewma
        
        # Update temporal traits based on behavior
        for trait_name in self.temporal_traits:
            delta = np.random.normal(0, 0.02) * confidence  # Small random movement
            self.temporal_traits[trait_name] = np.clip(
                self.temporal_traits[trait_name] + delta * self.TEMPORAL_TRAIT_LEARNING_RATE,
                0.0, 1.0
            )
        
        # Slowly drift core traits (much slower)
        if abs(drift) > 0.1:  # Only if significant drift
            for trait in self.core_traits:
                delta = (self.temporal_traits[trait] - self.core_traits[trait]) * 0.05
                self.core_traits[trait] = np.clip(
                    self.core_traits[trait] + delta * self.CORE_TRAIT_LEARNING_RATE,
                    0.0, 1.0
                )
    
    def get_drift_score(self) -> float:
        """Return current identity drift (0-1)"""
        return max(0.0, self.drift_ewma)
    
    def get_identity_coherence_index(self, recent_memories: List[Memory],
                                     window_days: int = 30) -> float:
        """
        Calculate Identity Coherence Index (ICI).
        Ranges: >0.7 healthy | 0.4-0.7 monitor | <0.4 intervention
        """
        if not recent_memories:
            return 0.7  # Default
        
        # Personality stability: how much core traits are changing
        trait_changes = np.mean([
            abs(self.temporal_traits[k] - self.core_traits[k])
            for k in self.core_traits
        ])
        personality_stability = 1.0 - trait_changes
        
        # Memory retention: can character retrieve old memories?
        memory_retention = min(len(recent_memories) / 10.0, 1.0)
        
        # Drift score
        drift_score = self.get_drift_score()
        
        # Composite ICI
        ICI = (
            0.35 * personality_stability +
            0.35 * memory_retention +
            0.3 * (1.0 - drift_score)
        )
        
        return max(0.0, min(1.0, ICI))
    
    def get_identity_reinforcement_prompt(self) -> str:
        """Generate prompt to reinforce core identity"""
        core_traits_str = ", ".join([
            f"{k}: {v:.1f}"
            for k, v in self.core_traits.items()
        ])
        
        return (
            f"Remember who you are fundamentally. Your core identity traits are: {core_traits_str}. "
            f"These define you. Growth means becoming more authentically yourself, not someone else."
        )
    
    def _calculate_drift(self, current_embedding: np.ndarray) -> float:
        """Calculate drift from baseline"""
        if self.baseline_embedding is None:
            return 0.0
        
        # Cosine distance
        dot_product = np.dot(current_embedding, self.baseline_embedding)
        norm1 = np.linalg.norm(current_embedding)
        norm2 = np.linalg.norm(self.baseline_embedding)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        cosine_sim = dot_product / (norm1 * norm2)
        drift = 1.0 - cosine_sim  # 0 = same, 1 = opposite
        
        return np.clip(drift, 0.0, 1.0)
    
    def snapshot_personality(self, reason: str = ""):
        """Save personality state snapshot"""
        self.personality_history.append({
            "timestamp": datetime.now().isoformat(),
            "core_traits": self.core_traits.copy(),
            "temporal_traits": self.temporal_traits.copy(),
            "drift": self.get_drift_score(),
            "reason": reason
        })


# ============================================================================
# MEMORY MONITORING & STATS
# ============================================================================

class MemoryStats:
    """Statistics and health monitoring for memory systems"""
    
    @staticmethod
    def get_memory_health_report(consolidation_engine: MemoryConsolidationEngine) -> Dict[str, Any]:
        """Generate comprehensive memory health report"""
        total_memories = len(consolidation_engine.memories)
        
        memory_counts = defaultdict(int)
        consolidation_counts = defaultdict(int)
        
        for mem in consolidation_engine.memories.values():
            memory_counts[mem.memory_type.value] += 1
            if mem.consolidated:
                consolidation_counts["consolidated"] += 1
            else:
                consolidation_counts["unconsolidated"] += 1
        
        # Calculate average importance
        if consolidation_engine.memories:
            avg_importance = np.mean([
                m.importance for m in consolidation_engine.memories.values()
            ])
        else:
            avg_importance = 0.0
        
        return {
            "total_memories": total_memories,
            "by_type": dict(memory_counts),
            "consolidation_status": dict(consolidation_counts),
            "average_importance": avg_importance,
            "temporal_landmarks": len(consolidation_engine.temporal_landmarks),
            "narratives_generated": len(consolidation_engine.autobiographical_narratives),
            "importance_accumulator": consolidation_engine.importance_accumulator,
            "last_consolidation": consolidation_engine.last_consolidation_time.isoformat()
        }