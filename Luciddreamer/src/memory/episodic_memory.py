"""
Episodic Memory System

Stores time-stamped experiences with importance scoring and consolidation.
Implements autobiographical memory inspired by human episodic memory systems,
with emotional tagging, spatial context, and relationship mapping.
"""

import time
import uuid
import math
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class EmotionalValence(Enum):
    """Emotional valence categories"""
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2

@dataclass
class SpatialContext:
    """Spatial context information"""
    location: str
    coordinates: Optional[Dict[str, float]] = None  # x, y, z if available
    environment: str = "unknown"  # indoor, outdoor, virtual, etc.
    objects_present: List[str] = field(default_factory=list)

@dataclass
class SocialContext:
    """Social context information"""
    participants: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)  # participant -> relationship
    social_role: str = "participant"  # leader, follower, observer, etc.
    group_size: int = 1

@dataclass
class EpisodicMemoryEntry:
    """Individual episodic memory entry"""

    # Core content
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    summary: str = ""

    # Temporal information
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0  # Duration in seconds

    # Contextual information
    spatial_context: Optional[SpatialContext] = None
    social_context: Optional[SocialContext] = None
    tags: Set[str] = field(default_factory=set)

    # Emotional components
    emotional_valence: EmotionalValence = EmotionalValence.NEUTRAL
    emotional_arousal: float = 0.5  # 0-1, calm to excited
    emotional_intensity: float = 0.5  # 0-1, weak to strong

    # Cognitive components
    importance: float = 0.5  # 0-1, automatically calculated
    novelty: float = 0.5  # 0-1, how novel was the experience
    goal_relevance: float = 0.5  # 0-1, relevance to current goals
    surprise: float = 0.0  # 0-1, unexpectedness

    # Memory metadata
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    consolidation_count: int = 0
    associated_memories: Set[str] = field(default_factory=set)  # Links to related memories

    # Neural activation pattern (simulated)
    activation_pattern: List[float] = field(default_factory=list)

    def mark_accessed(self):
        """Mark memory as accessed"""
        self.access_count += 1
        self.last_accessed = time.time()

        # Slightly increase importance based on access
        self.importance = min(1.0, self.importance + 0.01)

    def get_age_hours(self) -> float:
        """Get age in hours"""
        return (time.time() - self.timestamp) / 3600.0

    def get_age_days(self) -> float:
        """Get age in days"""
        return (time.time() - self.timestamp) / 86400.0

    def get_recency_score(self) -> float:
        """Calculate recency score (exponential decay)"""
        age_hours = self.get_age_hours()
        # Recency decays over time, but important memories decay slower
        decay_rate = 0.1 * (1.0 - self.importance * 0.5)  # Important memories decay slower
        return math.exp(-decay_rate * age_hours)

    def get_frequency_score(self) -> float:
        """Calculate frequency score based on access patterns"""
        if self.access_count == 0:
            return 0.0
        # Logarithmic scaling for frequency
        return math.log(self.access_count + 1) / math.log(100)

    def calculate_composite_importance(self) -> float:
        """Calculate composite importance score"""
        # Weight factors
        weights = {
            'base_importance': 0.3,
            'recency': 0.2,
            'frequency': 0.15,
            'emotional_intensity': 0.15,
            'novelty': 0.1,
            'goal_relevance': 0.1
        }

        recency_score = self.get_recency_score()
        frequency_score = self.get_frequency_score()

        composite = (
            weights['base_importance'] * self.importance +
            weights['recency'] * recency_score +
            weights['frequency'] * frequency_score +
            weights['emotional_intensity'] * self.emotional_intensity +
            weights['novelty'] * self.novelty +
            weights['goal_relevance'] * self.goal_relevance
        )

        return min(1.0, composite)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = asdict(self)
        # Convert enum to string
        if isinstance(data.get('emotional_valence'), EmotionalValence):
            data['emotional_valence'] = self.emotional_valence.name
        # Convert set to list
        if 'tags' in data:
            data['tags'] = list(self.tags)
        if 'associated_memories' in data:
            data['associated_memories'] = list(self.associated_memories)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EpisodicMemoryEntry':
        """Create from dictionary representation"""
        # Convert string back to enum
        if 'emotional_valence' in data and isinstance(data['emotional_valence'], str):
            data['emotional_valence'] = EmotionalValence[data['emotional_valence']]
        # Convert lists back to sets
        if 'tags' in data and isinstance(data['tags'], list):
            data['tags'] = set(data['tags'])
        if 'associated_memories' in data and isinstance(data['associated_memories'], list):
            data['associated_memories'] = set(data['associated_memories'])
        # Handle spatial and social context
        if 'spatial_context' in data and data['spatial_context']:
            data['spatial_context'] = SpatialContext(**data['spatial_context'])
        if 'social_context' in data and data['social_context']:
            data['social_context'] = SocialContext(**data['social_context'])
        return cls(**data)

class EpisodicMemory:
    """
    Episodic memory system for storing and retrieving autobiographical experiences.
    Implements importance-based consolidation and forgetting curves.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize episodic memory system

        Args:
            storage_path: Path for persistent storage (optional)
        """
        self.memories: Dict[str, EpisodicMemoryEntry] = {}
        self.temporal_index: List[Tuple[float, str]] = []  # (timestamp, memory_id)
        self.tag_index: Dict[str, Set[str]] = {}  # tag -> set of memory_ids
        self.location_index: Dict[str, Set[str]] = {}  # location -> set of memory_ids
        self.participant_index: Dict[str, Set[str]] = {}  # participant -> set of memory_ids

        self.storage_path = storage_path
        self._load_memories()

        # Statistics
        self.total_memories_created = 0
        self.total_consolidations = 0
        self.total_forgettings = 0

    def add_memory(self, content: str, summary: str = "",
                   emotional_valence: EmotionalValence = EmotionalValence.NEUTRAL,
                   emotional_arousal: float = 0.5,
                   emotional_intensity: float = 0.5,
                   importance: float = 0.5,
                   novelty: float = 0.5,
                   goal_relevance: float = 0.5,
                   surprise: float = 0.0,
                   spatial_context: Optional[SpatialContext] = None,
                   social_context: Optional[SocialContext] = None,
                   tags: Set[str] = None,
                   duration: float = 0.0) -> str:
        """
        Add a new episodic memory

        Args:
            content: Detailed memory content
            summary: Brief summary of the memory
            emotional_valence: Emotional valence of the memory
            emotional_arousal: Arousal level (0-1)
            emotional_intensity: Intensity level (0-1)
            importance: Base importance score (0-1)
            novelty: Novelty of the experience (0-1)
            goal_relevance: Relevance to current goals (0-1)
            surprise: How unexpected the experience was (0-1)
            spatial_context: Spatial context information
            social_context: Social context information
            tags: Descriptive tags
            duration: Duration of the experience in seconds

        Returns:
            Memory ID of the created memory
        """
        memory = EpisodicMemoryEntry(
            content=content,
            summary=summary or content[:100] + "..." if len(content) > 100 else content,
            emotional_valence=emotional_valence,
            emotional_arousal=emotional_arousal,
            emotional_intensity=emotional_intensity,
            importance=importance,
            novelty=novelty,
            goal_relevance=goal_relevance,
            surprise=surprise,
            spatial_context=spatial_context,
            social_context=social_context,
            tags=tags or set(),
            duration=duration
        )

        # Store memory
        self.memories[memory.memory_id] = memory

        # Update indexes
        self.temporal_index.append((memory.timestamp, memory.memory_id))
        self.temporal_index.sort()  # Keep sorted by timestamp

        for tag in memory.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(memory.memory_id)

        if memory.spatial_context and memory.spatial_context.location:
            location = memory.spatial_context.location
            if location not in self.location_index:
                self.location_index[location] = set()
            self.location_index[location].add(memory.memory_id)

        if memory.social_context:
            for participant in memory.social_context.participants:
                if participant not in self.participant_index:
                    self.participant_index[participant] = set()
                self.participant_index[participant].add(memory.memory_id)

        self.total_memories_created += 1

        logger.debug(f"Added episodic memory: {memory.memory_id[:8]}...")
        return memory.memory_id

    def get_memory(self, memory_id: str) -> Optional[EpisodicMemoryEntry]:
        """Retrieve a specific memory by ID"""
        memory = self.memories.get(memory_id)
        if memory:
            memory.mark_accessed()
        return memory

    def search_by_content(self, query: str, limit: int = 10,
                          time_range: Optional[Tuple[float, float]] = None) -> List[EpisodicMemoryEntry]:
        """
        Search memories by content

        Args:
            query: Search query
            limit: Maximum results
            time_range: Optional (start_time, end_time) tuple

        Returns:
            List of matching memories
        """
        query_lower = query.lower()
        matches = []

        for memory in self.memories.values():
            # Time range filter
            if time_range:
                start_time, end_time = time_range
                if not (start_time <= memory.timestamp <= end_time):
                    continue

            # Content matching
            content_match = (query_lower in memory.content.lower() or
                           query_lower in memory.summary.lower())

            if content_match:
                # Calculate relevance score
                relevance = self._calculate_relevance_score(memory, query_lower)
                matches.append((relevance, memory))

        # Sort by relevance and return top results
        matches.sort(reverse=True)
        results = [memory for _, memory in matches[:limit]]

        # Mark accessed
        for memory in results:
            memory.mark_accessed()

        return results

    def search_by_tags(self, tags: Set[str], require_all: bool = False,
                       limit: int = 10) -> List[EpisodicMemoryEntry]:
        """
        Search memories by tags

        Args:
            tags: Set of tags to search for
            require_all: If True, require all tags; if False, any tag
            limit: Maximum results

        Returns:
            List of matching memories
        """
        if not tags:
            return []

        candidate_ids = None

        for tag in tags:
            if tag in self.tag_index:
                tag_ids = self.tag_index[tag]
                if candidate_ids is None:
                    candidate_ids = tag_ids.copy()
                elif require_all:
                    candidate_ids &= tag_ids
                else:
                    candidate_ids |= tag_ids
            elif require_all:
                # Required tag not found
                return []

        if not candidate_ids:
            return []

        # Get memories and sort by importance
        memories = [self.memories[mid] for mid in candidate_ids if mid in self.memories]
        memories.sort(key=lambda m: m.calculate_composite_importance(), reverse=True)

        results = memories[:limit]

        # Mark accessed
        for memory in results:
            memory.mark_accessed()

        return results

    def get_memories_by_time_range(self, start_time: float, end_time: float,
                                   limit: int = 50) -> List[EpisodicMemoryEntry]:
        """
        Get memories within a time range

        Args:
            start_time: Start timestamp
            end_time: End timestamp
            limit: Maximum results

        Returns:
            List of memories in time range
        """
        # Binary search in temporal index
        start_idx = 0
        end_idx = len(self.temporal_index)

        # Find start position
        while start_idx < end_idx:
            mid = (start_idx + end_idx) // 2
            if self.temporal_index[mid][0] < start_time:
                start_idx = mid + 1
            else:
                end_idx = mid

        # Collect memories in range
        results = []
        for timestamp, memory_id in self.temporal_index[start_idx:]:
            if timestamp > end_time:
                break

            if memory_id in self.memories:
                memory = self.memories[memory_id]
                results.append(memory)

                if len(results) >= limit:
                    break

        # Mark accessed
        for memory in results:
            memory.mark_accessed()

        return results

    def get_memories_by_location(self, location: str, radius: float = 0.0,
                                 limit: int = 20) -> List[EpisodicMemoryEntry]:
        """
        Get memories by location

        Args:
            location: Location name
            radius: Search radius (if coordinates available)
            limit: Maximum results

        Returns:
            List of memories at location
        """
        if location not in self.location_index:
            return []

        memory_ids = self.location_index[location]
        memories = [self.memories[mid] for mid in memory_ids if mid in self.memories]

        # Sort by importance
        memories.sort(key=lambda m: m.calculate_composite_importance(), reverse=True)

        results = memories[:limit]

        # Mark accessed
        for memory in results:
            memory.mark_accessed()

        return results

    def get_memories_by_participant(self, participant: str,
                                    limit: int = 20) -> List[EpisodicMemoryEntry]:
        """
        Get memories involving a specific participant

        Args:
            participant: Participant name
            limit: Maximum results

        Returns:
            List of memories with participant
        """
        if participant not in self.participant_index:
            return []

        memory_ids = self.participant_index[participant]
        memories = [self.memories[mid] for mid in memory_ids if mid in self.memories]

        # Sort by importance
        memories.sort(key=lambda m: m.calculate_composite_importance(), reverse=True)

        results = memories[:limit]

        # Mark accessed
        for memory in results:
            memory.mark_accessed()

        return results

    def get_related_memories(self, memory_id: str, limit: int = 10) -> List[EpisodicMemoryEntry]:
        """
        Get memories related to a specific memory

        Args:
            memory_id: Reference memory ID
            limit: Maximum results

        Returns:
            List of related memories
        """
        if memory_id not in self.memories:
            return []

        reference_memory = self.memories[memory_id]
        related_memories = []

        # Find associated memories
        for assoc_id in reference_memory.associated_memories:
            if assoc_id in self.memories:
                related_memories.append(self.memories[assoc_id])

        # Find memories with similar tags
        shared_tags = set()
        for tag in reference_memory.tags:
            if tag in self.tag_index:
                shared_ids = self.tag_index[tag] - {memory_id}
                for mid in shared_ids:
                    if mid in self.memories:
                        shared_tags.add(mid)

        for mid in shared_tags:
            if mid in self.memories and len(related_memories) < limit:
                related_memories.append(self.memories[mid])

        # Sort by similarity score
        related_memories.sort(
            key=lambda m: self._calculate_memory_similarity(reference_memory, m),
            reverse=True
        )

        return related_memories[:limit]

    def associate_memories(self, memory_id1: str, memory_id2: str):
        """
        Create association between two memories

        Args:
            memory_id1: First memory ID
            memory_id2: Second memory ID
        """
        if memory_id1 in self.memories and memory_id2 in self.memories:
            self.memories[memory_id1].associated_memories.add(memory_id2)
            self.memories[memory_id2].associated_memories.add(memory_id1)

    def consolidate_memory(self, memory_id: str, new_importance: float = None):
        """
        Consolidate a memory, strengthening its importance

        Args:
            memory_id: Memory ID to consolidate
            new_importance: Optional new importance score
        """
        if memory_id not in self.memories:
            return

        memory = self.memories[memory_id]
        memory.consolidation_count += 1

        if new_importance is not None:
            memory.importance = min(1.0, new_importance)
        else:
            # Increase importance based on consolidation
            memory.importance = min(1.0, memory.importance + 0.1)

        self.total_consolidations += 1
        logger.debug(f"Consolidated memory: {memory_id[:8]}...")

    def forget_memory(self, memory_id: str):
        """
        Remove a memory from storage

        Args:
            memory_id: Memory ID to forget
        """
        if memory_id not in self.memories:
            return

        memory = self.memories[memory_id]

        # Remove from indexes
        # Temporal index
        self.temporal_index = [(ts, mid) for ts, mid in self.temporal_index if mid != memory_id]

        # Tag indexes
        for tag in memory.tags:
            if tag in self.tag_index:
                self.tag_index[tag].discard(memory_id)
                if not self.tag_index[tag]:
                    del self.tag_index[tag]

        # Location index
        if memory.spatial_context and memory.spatial_context.location:
            location = memory.spatial_context.location
            if location in self.location_index:
                self.location_index[location].discard(memory_id)
                if not self.location_index[location]:
                    del self.location_index[location]

        # Participant indexes
        if memory.social_context:
            for participant in memory.social_context.participants:
                if participant in self.participant_index:
                    self.participant_index[participant].discard(memory_id)
                    if not self.participant_index[participant]:
                        del self.participant_index[participant]

        # Remove associated memory links
        for assoc_id in memory.associated_memories:
            if assoc_id in self.memories:
                self.memories[assoc_id].associated_memories.discard(memory_id)

        # Remove memory
        del self.memories[memory_id]
        self.total_forgettings += 1

        logger.debug(f"Forgot memory: {memory_id[:8]}...")

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about episodic memory"""
        if not self.memories:
            return {
                "total_memories": 0,
                "average_importance": 0.0,
                "oldest_memory_age": 0.0,
                "newest_memory_age": 0.0,
                "total_tags": 0,
                "total_locations": 0,
                "total_participants": 0
            }

        # Calculate statistics
        current_time = time.time()
        ages = [(current_time - m.timestamp) / 86400.0 for m in self.memories.values()]  # days

        emotional_distribution = {}
        for memory in self.memories.values():
            valence = memory.emotional_valence.name
            emotional_distribution[valence] = emotional_distribution.get(valence, 0) + 1

        return {
            "total_memories": len(self.memories),
            "total_memories_created": self.total_memories_created,
            "total_consolidations": self.total_consolidations,
            "total_forgettings": self.total_forgettings,
            "average_importance": sum(m.importance for m in self.memories.values()) / len(self.memories),
            "average_composite_importance": sum(m.calculate_composite_importance() for m in self.memories.values()) / len(self.memories),
            "oldest_memory_age": max(ages) if ages else 0.0,
            "newest_memory_age": min(ages) if ages else 0.0,
            "total_tags": len(self.tag_index),
            "total_locations": len(self.location_index),
            "total_participants": len(self.participant_index),
            "emotional_distribution": emotional_distribution,
            "average_access_count": sum(m.access_count for m in self.memories.values()) / len(self.memories)
        }

    def _calculate_relevance_score(self, memory: EpisodicMemoryEntry, query: str) -> float:
        """Calculate relevance score for memory search"""
        # Content matching score
        content_score = 0.0
        query_words = query.split()

        for word in query_words:
            if word in memory.content.lower():
                content_score += 1.0
            if word in memory.summary.lower():
                content_score += 0.5

        content_score = min(1.0, content_score / len(query_words))

        # Importance boost
        importance_boost = memory.calculate_composite_importance()

        # Recency boost
        recency_boost = memory.get_recency_score()

        return (content_score * 0.5 + importance_boost * 0.3 + recency_boost * 0.2)

    def _calculate_memory_similarity(self, memory1: EpisodicMemoryEntry, memory2: EpisodicMemoryEntry) -> float:
        """Calculate similarity between two memories"""
        # Tag overlap
        tag_overlap = len(memory1.tags & memory2.tags) / max(1, len(memory1.tags | memory2.tags))

        # Spatial proximity
        spatial_score = 0.0
        if memory1.spatial_context and memory2.spatial_context:
            if memory1.spatial_context.location == memory2.spatial_context.location:
                spatial_score = 1.0

        # Temporal proximity
        time_diff = abs(memory1.timestamp - memory2.timestamp)
        temporal_score = max(0.0, 1.0 - time_diff / (7 * 24 * 3600))  # Decay over 7 days

        # Participant overlap
        participant_score = 0.0
        if memory1.social_context and memory2.social_context:
            participants1 = set(memory1.social_context.participants)
            participants2 = set(memory2.social_context.participants)
            if participants1 or participants2:
                participant_score = len(participants1 & participants2) / max(1, len(participants1 | participants2))

        # Weighted combination
        return (tag_overlap * 0.4 + spatial_score * 0.2 + temporal_score * 0.2 + participant_score * 0.2)

    def _save_memories(self):
        """Save memories to persistent storage"""
        if not self.storage_path:
            return

        try:
            data = {
                'memories': {mid: memory.to_dict() for mid, memory in self.memories.items()},
                'statistics': {
                    'total_memories_created': self.total_memories_created,
                    'total_consolidations': self.total_consolidations,
                    'total_forgettings': self.total_forgettings
                }
            }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save episodic memories: {e}")

    def _load_memories(self):
        """Load memories from persistent storage"""
        if not self.storage_path:
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            # Load memories
            for memory_id, memory_data in data.get('memories', {}).items():
                memory = EpisodicMemoryEntry.from_dict(memory_data)
                self.memories[memory_id] = memory

                # Rebuild indexes
                self.temporal_index.append((memory.timestamp, memory_id))

                for tag in memory.tags:
                    if tag not in self.tag_index:
                        self.tag_index[tag] = set()
                    self.tag_index[tag].add(memory_id)

                if memory.spatial_context and memory.spatial_context.location:
                    location = memory.spatial_context.location
                    if location not in self.location_index:
                        self.location_index[location] = set()
                    self.location_index[location].add(memory_id)

                if memory.social_context:
                    for participant in memory.social_context.participants:
                        if participant not in self.participant_index:
                            self.participant_index[participant] = set()
                        self.participant_index[participant].add(memory_id)

            # Sort temporal index
            self.temporal_index.sort()

            # Load statistics
            stats = data.get('statistics', {})
            self.total_memories_created = stats.get('total_memories_created', 0)
            self.total_consolidations = stats.get('total_consolidations', 0)
            self.total_forgettings = stats.get('total_forgettings', 0)

            logger.info(f"Loaded {len(self.memories)} episodic memories from storage")

        except FileNotFoundError:
            logger.info("No existing episodic memory storage found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load episodic memories: {e}")

    def __len__(self) -> int:
        """Return number of stored memories"""
        return len(self.memories)

    def __contains__(self, memory_id: str) -> bool:
        """Check if memory ID exists"""
        return memory_id in self.memories