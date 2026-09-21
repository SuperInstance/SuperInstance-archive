"""
AI Society Portal - Enhanced Memory System
==========================================
Advanced memory persistence system for AI characters with importance scoring,
cross-session persistence, and intelligent retrieval mechanisms.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import hashlib
import re
from collections import defaultdict


# ============================================================================
# MEMORY TYPES AND STRUCTURES
# ============================================================================

class MemoryType(Enum):
    """Different types of memories a character can have"""
    CONVERSATIONAL = "conversational"  # What was discussed with others
    LEARNING = "learning"             # New insights, skills, knowledge
    RELATIONSHIP = "relationship"     # Connections and interactions with others
    SELF_REFLECTION = "self_reflection"  # Thoughts about own development
    EXPERIENCE = "experience"         # Significant events and experiences
    EMOTIONAL = "emotional"           # Emotional responses and feelings


class MemoryImportance(Enum):
    """Importance levels for memory scoring (1-10 scale)"""
    TRIVIAL = 1      # Barely worth remembering
    MINOR = 3        # Slightly notable
    NOTABLE = 5      # Worth keeping for a while
    SIGNIFICANT = 7  # Important for identity/relationships
    PIVOTAL = 9      # Life-changing or core to identity
    DEFINING = 10    # Absolutely essential to who they are


@dataclass
class Memory:
    """A single memory with metadata"""
    id: str
    content: str
    memory_type: MemoryType
    importance: int  # 1-10 scale
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)

    # Associated entities
    related_characters: List[str] = field(default_factory=list)
    related_rooms: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)

    # Emotional metadata
    emotional_valence: float = 0.0  # -1 (negative) to 1 (positive)
    emotional_arousal: float = 0.0  # 0 (calm) to 1 (excited)

    # Access and retrieval metadata
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    # Decay and forgetting
    decay_rate: float = 0.1  # How quickly memory fades
    current_strength: float = 1.0  # Current memory strength (0-1)

    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
        if isinstance(self.memory_type, str):
            self.memory_type = MemoryType(self.memory_type)
        if self.last_accessed and isinstance(self.last_accessed, str):
            self.last_accessed = datetime.fromisoformat(self.last_accessed)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["memory_type"] = self.memory_type.value
        if self.last_accessed:
            data["last_accessed"] = self.last_accessed.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """Create from dictionary"""
        return cls(**data)

    def access(self):
        """Record that this memory was accessed"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        # Boost strength slightly when accessed
        self.current_strength = min(1.0, self.current_strength + 0.1)

    def decay(self, time_delta: timedelta):
        """Apply memory decay based on time passed"""
        decay_amount = self.decay_rate * time_delta.total_seconds() / 86400  # Daily decay
        self.current_strength = max(0.1, self.current_strength - decay_amount)

    def get_retrieval_score(self, query_relevance: float = 1.0, recency_weight: float = 0.1) -> float:
        """Calculate retrieval score for this memory"""
        # Factors: importance, current strength, recency, query relevance
        age_days = (datetime.now() - self.timestamp).total_seconds() / 86400
        recency_score = 1.0 / (1.0 + age_days * recency_weight)

        return (
            self.importance / 10.0 * 0.3 +  # Importance (30%)
            self.current_strength * 0.3 +     # Memory strength (30%)
            recency_score * 0.2 +             # Recency (20%)
            query_relevance * 0.2            # Query relevance (20%)
        )


@dataclass
class MemoryCluster:
    """A cluster of related memories"""
    id: str
    name: str
    topic: str
    memory_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    importance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryCluster':
        """Create from dictionary"""
        if isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


class EnhancedMemorySystem:
    """Advanced memory system for AI characters with intelligent retrieval"""

    def __init__(self, character_id: str, storage_dir: Path):
        self.character_id = character_id
        self.storage_dir = storage_dir / character_id
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Memory storage
        self.memories: Dict[str, Memory] = {}
        self.clusters: Dict[str, MemoryCluster] = {}

        # Indexing for fast retrieval
        self.topic_index: Dict[str, Set[str]] = defaultdict(set)
        self.character_index: Dict[str, Set[str]] = defaultdict(set)
        self.type_index: Dict[MemoryType, Set[str]] = defaultdict(set)

        # Working memory (current session)
        self.working_memory: List[str] = []
        self.max_working_memory = 20

        # Memory management settings
        self.max_memories = 1000
        self.decay_interval_hours = 24

        # Load existing memories
        self.load_memories()

    def add_memory(self, content: str, memory_type: MemoryType,
                   importance: int, context: Dict[str, Any] = None,
                   related_characters: List[str] = None,
                   related_rooms: List[str] = None,
                   topics: List[str] = None,
                   emotional_valence: float = 0.0,
                   emotional_arousal: float = 0.0) -> str:
        """Add a new memory to the system"""

        # Create memory
        memory_id = hashlib.md5(
            f"{content}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=max(1, min(10, importance)),
            timestamp=datetime.now(),
            context=context or {},
            related_characters=related_characters or [],
            related_rooms=related_rooms or [],
            topics=topics or [],
            emotional_valence=emotional_valence,
            emotional_arousal=emotional_arousal,
            decay_rate=self._calculate_decay_rate(importance)
        )

        # Store memory
        self.memories[memory_id] = memory

        # Update indexes
        self._update_indexes(memory)

        # Add to working memory if recent
        self.working_memory.append(content)
        if len(self.working_memory) > self.max_working_memory:
            self.working_memory = self.working_memory[-self.max_working_memory:]

        # Check if we need to create/update clusters
        self._update_clusters(memory)

        # Save to disk
        self.save_memories()

        return memory_id

    def _calculate_decay_rate(self, importance: int) -> float:
        """Calculate decay rate based on importance"""
        # More important memories decay slower
        base_decay = 0.1
        importance_factor = (11 - importance) / 10.0
        return base_decay * importance_factor

    def _update_indexes(self, memory: Memory):
        """Update search indexes for a memory"""
        # Topic index
        for topic in memory.topics:
            self.topic_index[topic.lower()].add(memory.id)

        # Character index
        for char_id in memory.related_characters:
            self.character_index[char_id].add(memory.id)

        # Type index
        self.type_index[memory.memory_type].add(memory.id)

    def _update_clusters(self, memory: Memory):
        """Create or update memory clusters based on topics"""
        for topic in memory.topics:
            # Find existing clusters for this topic
            matching_clusters = [
                cluster for cluster in self.clusters.values()
                if cluster.topic.lower() == topic.lower()
            ]

            if matching_clusters:
                # Add to existing cluster
                cluster = matching_clusters[0]
                if memory.id not in cluster.memory_ids:
                    cluster.memory_ids.append(memory.id)
                    cluster.importance = max(cluster.importance, memory.importance)
            else:
                # Create new cluster
                cluster_id = hashlib.md5(f"{topic}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
                cluster = MemoryCluster(
                    id=cluster_id,
                    name=f"{topic.title()} Memories",
                    topic=topic,
                    memory_ids=[memory.id],
                    importance=memory.importance
                )
                self.clusters[cluster_id] = cluster

    def get_memories(self, limit: int = 50,
                    memory_type: Optional[MemoryType] = None,
                    related_character: Optional[str] = None,
                    topic: Optional[str] = None,
                    min_importance: int = 1,
                    sort_by: str = "retrieval_score") -> List[Memory]:
        """Retrieve memories with optional filters"""

        # Start with all memories
        candidate_ids = set(self.memories.keys())

        # Apply filters
        if memory_type:
            candidate_ids &= self.type_index.get(memory_type, set())

        if related_character:
            candidate_ids &= self.character_index.get(related_character, set())

        if topic:
            candidate_ids &= self.topic_index.get(topic.lower(), set())

        # Get memory objects and apply importance filter
        filtered_memories = [
            self.memories[mid] for mid in candidate_ids
            if self.memories[mid].importance >= min_importance
        ]

        # Sort memories
        if sort_by == "retrieval_score":
            filtered_memories.sort(
                key=lambda m: m.get_retrieval_score(),
                reverse=True
            )
        elif sort_by == "importance":
            filtered_memories.sort(key=lambda m: m.importance, reverse=True)
        elif sort_by == "recent":
            filtered_memories.sort(key=lambda m: m.timestamp, reverse=True)

        # Apply decay before returning
        self._apply_decay_to_memories()

        return filtered_memories[:limit]

    def search_memories(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search memories by content with relevance scoring"""
        query_lower = query.lower()
        query_terms = query_lower.split()

        results = []
        for memory in self.memories.values():
            relevance = self._calculate_relevance(memory, query_terms)
            if relevance > 0.1:  # Threshold for inclusion
                results.append({
                    "memory": memory,
                    "relevance": relevance,
                    "retrieval_score": memory.get_retrieval_score(relevance)
                })

        # Sort by combined relevance and retrieval score
        results.sort(
            key=lambda r: r["retrieval_score"],
            reverse=True
        )

        # Update access counts for returned memories
        for result in results[:limit]:
            result["memory"].access()

        return results[:limit]

    def _calculate_relevance(self, memory: Memory, query_terms: List[str]) -> float:
        """Calculate relevance score for a memory against query terms"""
        content_lower = memory.content.lower()
        relevance = 0.0

        # Exact phrase match gets highest score
        if " ".join(query_terms) in content_lower:
            relevance += 2.0

        # Individual term matches
        for term in query_terms:
            if term in content_lower:
                relevance += 0.5

            # Check topics
            for topic in memory.topics:
                if term in topic.lower():
                    relevance += 0.3

            # Check context
            for key, value in memory.context.items():
                if isinstance(value, str) and term in value.lower():
                    relevance += 0.2

        return relevance

    def get_memories_about_character(self, character_id: str,
                                   limit: int = 10) -> List[Memory]:
        """Get memories specifically about another character"""
        return self.get_memories(
            limit=limit,
            related_character=character_id,
            sort_by="retrieval_score"
        )

    def get_memories_by_type(self, memory_type: MemoryType,
                           limit: int = 20) -> List[Memory]:
        """Get memories of a specific type"""
        return self.get_memories(
            limit=limit,
            memory_type=memory_type,
            sort_by="retrieval_score"
        )

    def get_context_summary(self, max_memories: int = 5,
                          max_length: int = 800) -> str:
        """Get a summary of relevant memories for context window"""

        # Get most relevant recent memories
        recent_memories = self.get_memories(
            limit=max_memories,
            sort_by="retrieval_score"
        )

        if not recent_memories:
            return "No significant memories yet."

        summary_parts = []

        # Group by type for better organization
        by_type = defaultdict(list)
        for memory in recent_memories:
            by_type[memory.memory_type.value].append(memory)

        for memory_type, memories in by_type.items():
            if memories:
                type_name = memory_type.replace("_", " ").title()
                memories_text = "; ".join([
                    f"{m.content[:100]}{'...' if len(m.content) > 100 else ''}"
                    for m in memories[:3]
                ])
                summary_parts.append(f"{type_name}: {memories_text}")

        summary = " | ".join(summary_parts)
        return summary[:max_length]

    def _apply_decay_to_memories(self):
        """Apply memory decay based on time passed"""
        now = datetime.now()

        for memory in self.memories.values():
            time_delta = now - memory.timestamp
            memory.decay(time_delta)

        # Remove memories that have decayed too much (unless very important)
        to_remove = [
            mid for mid, memory in self.memories.items()
            if memory.current_strength < 0.1 and memory.importance < 7
        ]

        for mid in to_remove:
            self._remove_memory(mid)

    def _remove_memory(self, memory_id: str):
        """Remove a memory from the system"""
        if memory_id not in self.memories:
            return

        memory = self.memories[memory_id]

        # Remove from indexes
        for topic in memory.topics:
            self.topic_index[topic.lower()].discard(memory_id)

        for char_id in memory.related_characters:
            self.character_index[char_id].discard(memory_id)

        self.type_index[memory.memory_type].discard(memory_id)

        # Remove from clusters
        for cluster in self.clusters.values():
            if memory_id in cluster.memory_ids:
                cluster.memory_ids.remove(memory_id)

        # Remove memory
        del self.memories[memory_id]

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory system"""
        if not self.memories:
            return {
                "total_memories": 0,
                "by_type": {},
                "by_importance": {},
                "average_strength": 0.0,
                "total_clusters": 0
            }

        # Count by type
        by_type = defaultdict(int)
        for memory in self.memories.values():
            by_type[memory.memory_type.value] += 1

        # Count by importance
        by_importance = defaultdict(int)
        total_strength = 0.0
        for memory in self.memories.values():
            by_importance[memory.importance] += 1
            total_strength += memory.current_strength

        return {
            "total_memories": len(self.memories),
            "by_type": dict(by_type),
            "by_importance": dict(by_importance),
            "average_strength": total_strength / len(self.memories),
            "total_clusters": len(self.clusters),
            "working_memory_size": len(self.working_memory)
        }

    def save_memories(self):
        """Save memories to disk"""
        # Save memories
        memories_file = self.storage_dir / "memories.json"
        memories_data = {
            "character_id": self.character_id,
            "memories": [m.to_dict() for m in self.memories.values()],
            "last_saved": datetime.now().isoformat()
        }

        with open(memories_file, "w") as f:
            json.dump(memories_data, f, indent=2)

        # Save clusters
        clusters_file = self.storage_dir / "memory_clusters.json"
        clusters_data = {
            "character_id": self.character_id,
            "clusters": [c.to_dict() for c in self.clusters.values()],
            "last_saved": datetime.now().isoformat()
        }

        with open(clusters_file, "w") as f:
            json.dump(clusters_data, f, indent=2)

        # Save indexes for faster loading
        indexes_file = self.storage_dir / "memory_indexes.json"
        indexes_data = {
            "topic_index": {k: list(v) for k, v in self.topic_index.items()},
            "character_index": {k: list(v) for k, v in self.character_index.items()},
            "type_index": {k.value: list(v) for k, v in self.type_index.items()}
        }

        with open(indexes_file, "w") as f:
            json.dump(indexes_data, f, indent=2)

    def load_memories(self):
        """Load memories from disk"""
        try:
            # Load memories
            memories_file = self.storage_dir / "memories.json"
            if memories_file.exists():
                with open(memories_file, "r") as f:
                    memories_data = json.load(f)

                for memory_data in memories_data.get("memories", []):
                    memory = Memory.from_dict(memory_data)
                    self.memories[memory.id] = memory
                    self._update_indexes(memory)

            # Load clusters
            clusters_file = self.storage_dir / "memory_clusters.json"
            if clusters_file.exists():
                with open(clusters_file, "r") as f:
                    clusters_data = json.load(f)

                for cluster_data in clusters_data.get("clusters", []):
                    cluster = MemoryCluster.from_dict(cluster_data)
                    self.clusters[cluster.id] = cluster

            # Load indexes if available (faster than rebuilding)
            indexes_file = self.storage_dir / "memory_indexes.json"
            if indexes_file.exists():
                with open(indexes_file, "r") as f:
                    indexes_data = json.load(f)

                self.topic_index = defaultdict(set, {
                    k: set(v) for k, v in indexes_data.get("topic_index", {}).items()
                })
                self.character_index = defaultdict(set, {
                    k: set(v) for k, v in indexes_data.get("character_index", {}).items()
                })
                self.type_index = defaultdict(set, {
                    MemoryType(k): set(v) for k, v in indexes_data.get("type_index", {}).items()
                })

            print(f"[MEMORY] Loaded {len(self.memories)} memories for character {self.character_id}")

        except Exception as e:
            print(f"[MEMORY] Error loading memories for {self.character_id}: {e}")

    def force_memory_consolidation(self):
        """Force consolidation of working memory into long-term storage"""
        if not self.working_memory:
            return

        # Take the most important working memories and convert to proper memories
        for thought in self.working_memory[-5:]:  # Keep last 5 thoughts
            # Assess importance based on length and content
            importance = 3  # Base importance
            if len(thought) > 100:
                importance += 1
            if any(keyword in thought.lower() for keyword in
                   ["realized", "learned", "discovered", "important", "remember"]):
                importance += 2

            # Add as self-reflection memory
            self.add_memory(
                content=thought,
                memory_type=MemoryType.SELF_REFLECTION,
                importance=importance,
                context={"source": "working_memory_consolidation"}
            )

        # Clear working memory
        self.working_memory = []