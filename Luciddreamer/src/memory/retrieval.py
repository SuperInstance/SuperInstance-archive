"""
Memory Retrieval System

Provides sophisticated memory retrieval with temporal and semantic search capabilities.
Implements multi-modal search, relevance ranking, and contextual memory access.
Supports working memory, episodic, semantic, and procedural memory retrieval.
"""

import time
import math
import re
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SearchMode(Enum):
    """Memory search modes"""
    SEMANTIC = "semantic"           # Search by meaning/similarity
    TEMPORAL = "temporal"           # Search by time
    SPATIAL = "spatial"             # Search by location
    CONTEXTUAL = "contextual"       # Search by context
    HYBRID = "hybrid"               # Combined search
    ASSOCIATIVE = "associative"     # Search by associations

class MemoryScope(Enum):
    """Scope of memory search"""
    WORKING = "working"             # Working memory only
    EPISODIC = "episodic"           # Episodic memory only
    SEMANTIC = "semantic"           # Semantic memory only
    PROCEDURAL = "procedural"       # Procedural memory only
    ALL = "all"                     # All memory systems

class RelevanceFactor(Enum):
    """Factors affecting relevance calculation"""
    SEMANTIC_SIMILARITY = "semantic_similarity"
    TEMPORAL_PROXIMITY = "temporal_proximity"
    FREQUENCY = "frequency"
    RECENCY = "recency"
    IMPORTANCE = "importance"
    EMOTIONAL_IMPACT = "emotional_impact"
    CONTEXT_MATCH = "context_match"
    ASSOCIATION_STRENGTH = "association_strength"

@dataclass
class RetrievalQuery:
    """Structured query for memory retrieval"""
    query_text: str = ""
    search_mode: SearchMode = SearchMode.HYBRID
    memory_scope: MemoryScope = MemoryScope.ALL
    time_range: Optional[Tuple[float, float]] = None  # (start_time, end_time)
    spatial_filter: Optional[str] = None
    context_tags: Set[str] = field(default_factory=set)
    emotional_filter: Optional[str] = None  # "positive", "negative", "neutral"
    importance_threshold: float = 0.0
    max_results: int = 10
    include_associations: bool = True
    relevance_weights: Dict[RelevanceFactor, float] = field(default_factory=dict)

@dataclass
class RetrievalResult:
    """Single memory retrieval result"""
    memory_id: str
    memory_type: str
    content: Any
    relevance_score: float
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    associated_memories: List[str] = field(default_factory=list)

@dataclass
class RetrievalResults:
    """Container for memory retrieval results"""
    query: RetrievalQuery
    results: List[RetrievalResult]
    total_results: int
    search_time: float
    memory_systems_searched: List[str]
    search_metadata: Dict[str, Any] = field(default_factory=dict)

class MemoryRetrieval:
    """
    Advanced memory retrieval system with multi-modal search capabilities.
    Integrates with all memory systems to provide unified access to memories.
    """

    def __init__(self, working_memory=None, episodic_memory=None,
                 semantic_memory=None, procedural_memory=None):
        """
        Initialize memory retrieval system

        Args:
            working_memory: Working memory system
            episodic_memory: Episodic memory system
            semantic_memory: Semantic memory system
            procedural_memory: Procedural memory system
        """
        self.working_memory = working_memory
        self.episodic_memory = episodic_memory
        self.semantic_memory = semantic_memory
        self.procedural_memory = procedural_memory

        # Search configuration
        self.default_relevance_weights = {
            RelevanceFactor.SEMANTIC_SIMILARITY: 0.3,
            RelevanceFactor.TEMPORAL_PROXIMITY: 0.2,
            RelevanceFactor.RECENCY: 0.15,
            RelevanceFactor.IMPORTANCE: 0.15,
            RelevanceFactor.FREQUENCY: 0.1,
            RelevanceFactor.EMOTIONAL_IMPACT: 0.1
        }

        # Search statistics
        self.total_searches = 0
        self.search_times: List[float] = []
        self.search_patterns: Dict[str, int] = {}

    def search(self, query: RetrievalQuery) -> RetrievalResults:
        """
        Perform memory search using the provided query

        Args:
            query: Retrieval query parameters

        Returns:
            Retrieval results
        """
        start_time = time.time()

        # Update search statistics
        self.total_searches += 1
        search_key = f"{query.search_mode.value}_{query.memory_scope.value}"
        self.search_patterns[search_key] = self.search_patterns.get(search_key, 0) + 1

        # Determine which memory systems to search
        memory_systems = self._get_memory_systems(query.memory_scope)

        # Normalize relevance weights
        weights = self._normalize_relevance_weights(query.relevance_weights)

        # Search each memory system
        all_results = []
        for system_name, system in memory_systems.items():
            try:
                system_results = self._search_memory_system(system, query, weights)
                all_results.extend(system_results)
            except Exception as e:
                logger.error(f"Error searching {system_name}: {e}")

        # Rank and filter results
        ranked_results = self._rank_results(all_results, weights, query)

        # Apply result limit
        final_results = ranked_results[:query.max_results]

        # Generate explanations
        for result in final_results:
            result.explanation = self._generate_explanation(result, query, weights)

        search_time = time.time() - start_time
        self.search_times.append(search_time)

        # Keep search times manageable
        if len(self.search_times) > 1000:
            self.search_times = self.search_times[-500:]

        results = RetrievalResults(
            query=query,
            results=final_results,
            total_results=len(all_results),
            search_time=search_time,
            memory_systems_searched=list(memory_systems.keys()),
            search_metadata={
                "systems_searched": len(memory_systems),
                "raw_results": len(all_results),
                "final_results": len(final_results),
                "average_relevance": sum(r.relevance_score for r in final_results) / len(final_results) if final_results else 0.0
            }
        )

        logger.debug(f"Search completed: {len(final_results)} results in {search_time:.3f}s")
        return results

    def quick_search(self, query_text: str, max_results: int = 5,
                    memory_scope: MemoryScope = MemoryScope.ALL) -> List[RetrievalResult]:
        """
        Quick search with minimal parameters

        Args:
            query_text: Search query
            max_results: Maximum results
            memory_scope: Memory systems to search

        Returns:
            List of retrieval results
        """
        query = RetrievalQuery(
            query_text=query_text,
            search_mode=SearchMode.HYBRID,
            memory_scope=memory_scope,
            max_results=max_results
        )

        results = self.search(query)
        return results.results

    def temporal_search(self, query_text: str, start_time: float, end_time: float,
                       max_results: int = 10) -> List[RetrievalResult]:
        """
        Search memories within a specific time range

        Args:
            query_text: Search query
            start_time: Start timestamp
            end_time: End timestamp
            max_results: Maximum results

        Returns:
            List of retrieval results
        """
        query = RetrievalQuery(
            query_text=query_text,
            search_mode=SearchMode.TEMPORAL,
            time_range=(start_time, end_time),
            max_results=max_results
        )

        results = self.search(query)
        return results.results

    def associative_search(self, memory_id: str, max_results: int = 10,
                          max_depth: int = 2) -> List[RetrievalResult]:
        """
        Search for memories associated with a specific memory

        Args:
            memory_id: Reference memory ID
            max_results: Maximum results
            max_depth: Maximum association depth

        Returns:
            List of associated memories
        """
        # This would require association tracking in memory systems
        # For now, implement a simple version
        associated_results = []

        # Search episodic memory for related memories
        if self.episodic_memory and memory_id in self.episodic_memory.memories:
            related_memories = self.episodic_memory.get_related_memories(memory_id, max_results)
            for memory in related_memories:
                result = RetrievalResult(
                    memory_id=memory.memory_id,
                    memory_type="episodic",
                    content=memory.content,
                    relevance_score=memory.calculate_composite_importance(),
                    confidence=0.8,
                    metadata={"association_type": "episodic_relation"}
                )
                associated_results.append(result)

        return associated_results[:max_results]

    def context_search(self, context_tags: Set[str], query_text: str = "",
                      max_results: int = 10) -> List[RetrievalResult]:
        """
        Search memories by context tags

        Args:
            context_tags: Context tags to match
            query_text: Optional text query
            max_results: Maximum results

        Returns:
            List of matching memories
        """
        query = RetrievalQuery(
            query_text=query_text,
            search_mode=SearchMode.CONTEXTUAL,
            context_tags=context_tags,
            max_results=max_results
        )

        results = self.search(query)
        return results.results

    def get_memory_by_id(self, memory_id: str, memory_type: str = None) -> Optional[RetrievalResult]:
        """
        Retrieve a specific memory by ID

        Args:
            memory_id: Memory identifier
            memory_type: Optional memory type hint

        Returns:
            Memory result or None
        """
        # Try each memory system
        if memory_type:
            systems = self._get_memory_systems(MemoryScope(memory_type))
        else:
            systems = self._get_memory_systems(MemoryScope.ALL)

        for system_name, system in systems.items():
            try:
                memory = None
                if system_name == "working" and hasattr(system, 'get_items'):
                    # Search working memory
                    items = system.search(memory_id, limit=1)
                    if items:
                        memory = items[0]
                elif system_name == "episodic" and hasattr(system, 'get_memory'):
                    memory = system.get_memory(memory_id)
                elif system_name == "semantic" and hasattr(system, 'get_concept'):
                    memory = system.get_concept(memory_id)
                elif system_name == "procedural" and hasattr(system, 'get_skill'):
                    memory = system.get_skill(memory_id)

                if memory:
                    return RetrievalResult(
                        memory_id=memory_id,
                        memory_type=system_name,
                        content=getattr(memory, 'content', memory),
                        relevance_score=1.0,
                        confidence=1.0,
                        metadata={"direct_access": True}
                    )
            except Exception as e:
                logger.error(f"Error retrieving {memory_id} from {system_name}: {e}")

        return None

    def _get_memory_systems(self, scope: MemoryScope) -> Dict[str, Any]:
        """Get memory systems to search based on scope"""
        systems = {}

        if scope in [MemoryScope.WORKING, MemoryScope.ALL] and self.working_memory:
            systems["working"] = self.working_memory

        if scope in [MemoryScope.EPISODIC, MemoryScope.ALL] and self.episodic_memory:
            systems["episodic"] = self.episodic_memory

        if scope in [MemoryScope.SEMANTIC, MemoryScope.ALL] and self.semantic_memory:
            systems["semantic"] = self.semantic_memory

        if scope in [MemoryScope.PROCEDURAL, MemoryScope.ALL] and self.procedural_memory:
            systems["procedural"] = self.procedural_memory

        return systems

    def _normalize_relevance_weights(self, weights: Dict[RelevanceFactor, float]) -> Dict[RelevanceFactor, float]:
        """Normalize relevance weights to sum to 1.0"""
        if not weights:
            return self.default_relevance_weights.copy()

        # Combine with defaults
        combined_weights = self.default_relevance_weights.copy()
        for factor, weight in weights.items():
            combined_weights[factor] = weight

        # Normalize
        total_weight = sum(combined_weights.values())
        if total_weight > 0:
            return {factor: weight / total_weight for factor, weight in combined_weights.items()}
        else:
            return self.default_relevance_weights.copy()

    def _search_memory_system(self, system: Any, query: RetrievalQuery,
                             weights: Dict[RelevanceFactor, float]) -> List[RetrievalResult]:
        """Search a specific memory system"""
        results = []

        try:
            # Determine system type and call appropriate search method
            system_name = type(system).__name__.lower()

            if "working" in system_name:
                results = self._search_working_memory(system, query, weights)
            elif "episodic" in system_name:
                results = self._search_episodic_memory(system, query, weights)
            elif "semantic" in system_name:
                results = self._search_semantic_memory(system, query, weights)
            elif "procedural" in system_name:
                results = self._search_procedural_memory(system, query, weights)

        except Exception as e:
            logger.error(f"Error searching memory system: {e}")

        return results

    def _search_working_memory(self, working_memory, query: RetrievalQuery,
                              weights: Dict[RelevanceFactor, float]) -> List[RetrievalResult]:
        """Search working memory"""
        results = []

        if query.query_text:
            # Text search in working memory
            items = working_memory.search(query.query_text, limit=query.max_results)
        else:
            # Get recent items
            items = working_memory.get_recent_items(limit=query.max_results)

        for item in items:
            relevance_score = self._calculate_working_memory_relevance(item, query, weights)

            if relevance_score >= query.importance_threshold:
                result = RetrievalResult(
                    memory_id=f"wm_{time.time()}_{id(item)}",  # Temporary ID
                    memory_type="working",
                    content=item.content,
                    relevance_score=relevance_score,
                    confidence=0.9,
                    metadata={
                        "item_type": item.item_type,
                        "importance": item.importance,
                        "age_minutes": item.get_age() / 60.0,
                        "access_count": item.access_count
                    }
                )
                results.append(result)

        return results

    def _search_episodic_memory(self, episodic_memory, query: RetrievalQuery,
                               weights: Dict[RelevanceFactor, float]) -> List[RetrievalResult]:
        """Search episodic memory"""
        results = []

        # Content-based search
        if query.query_text:
            memories = episodic_memory.search_by_content(
                query.query_text,
                limit=query.max_results,
                time_range=query.time_range
            )
        elif query.time_range:
            memories = episodic_memory.get_memories_by_time_range(
                query.time_range[0],
                query.time_range[1],
                limit=query.max_results
            )
        else:
            # Get recent important memories
            all_memories = list(episodic_memory.memories.values())
            all_memories.sort(key=lambda m: m.calculate_composite_importance(), reverse=True)
            memories = all_memories[:query.max_results]

        for memory in memories:
            relevance_score = self._calculate_episodic_relevance(memory, query, weights)

            if relevance_score >= query.importance_threshold:
                result = RetrievalResult(
                    memory_id=memory.memory_id,
                    memory_type="episodic",
                    content=memory.content,
                    relevance_score=relevance_score,
                    confidence=0.8,
                    metadata={
                        "summary": memory.summary,
                        "emotional_valence": memory.emotional_valence.value,
                        "emotional_arousal": memory.emotional_arousal,
                        "importance": memory.importance,
                        "age_days": memory.get_age_days(),
                        "access_count": memory.access_count,
                        "spatial_context": memory.spatial_context.location if memory.spatial_context else None,
                        "social_context": memory.social_context.participants if memory.social_context else []
                    }
                )
                results.append(result)

        return results

    def _search_semantic_memory(self, semantic_memory, query: RetrievalQuery,
                               weights: Dict[RelevanceFactor, float]) -> List[RetrievalResult]:
        """Search semantic memory"""
        results = []

        # Concept search
        if query.query_text:
            concepts = semantic_memory.search_concepts(query.query_text, limit=query.max_results)
        else:
            # Get recent concepts
            concepts = list(semantic_memory.concepts.values())[:query.max_results]

        for concept, similarity_score in concepts:
            relevance_score = self._calculate_semantic_relevance(concept, similarity_score, query, weights)

            if relevance_score >= query.importance_threshold:
                result = RetrievalResult(
                    memory_id=concept.concept_id,
                    memory_type="semantic",
                    content=concept.definition,
                    relevance_score=relevance_score,
                    confidence=0.7,
                    metadata={
                        "concept_name": concept.name,
                        "concept_type": concept.concept_type.value,
                        "similarity_score": similarity_score,
                        "access_count": concept.access_count
                    }
                )
                results.append(result)

        return results

    def _search_procedural_memory(self, procedural_memory, query: RetrievalQuery,
                                 weights: Dict[RelevanceFactor, float]) -> List[RetrievalResult]:
        """Search procedural memory"""
        results = []

        # Skill search
        if query.query_text:
            # Simple text matching in skill names and descriptions
            matching_skills = []
            query_lower = query.query_text.lower()
            for skill in procedural_memory.skills.values():
                if (query_lower in skill.name.lower() or
                    query_lower in skill.description.lower() or
                    any(query_lower in tag.lower() for tag in skill.tags)):
                    matching_skills.append(skill)
        else:
            # Get top skills by mastery
            matching_skills = procedural_memory.get_top_skills(limit=query.max_results)

        for skill in matching_skills:
            relevance_score = self._calculate_procedural_relevance(skill, query, weights)

            if relevance_score >= query.importance_threshold:
                result = RetrievalResult(
                    memory_id=skill.skill_id,
                    memory_type="procedural",
                    content=skill.description,
                    relevance_score=relevance_score,
                    confidence=0.75,
                    metadata={
                        "skill_name": skill.name,
                        "skill_type": skill.skill_type.value,
                        "mastery_level": skill.mastery_level,
                        "practice_count": skill.practice_count,
                        "success_rate": skill.success_rate
                    }
                )
                results.append(result)

        return results

    def _calculate_working_memory_relevance(self, item, query: RetrievalQuery,
                                           weights: Dict[RelevanceFactor, float]) -> float:
        """Calculate relevance score for working memory item"""
        relevance = 0.0

        # Importance factor
        if RelevanceFactor.IMPORTANCE in weights:
            relevance += weights[RelevanceFactor.IMPORTANCE] * item.importance

        # Recency factor
        if RelevanceFactor.RECENCY in weights:
            age_minutes = item.get_age() / 60.0
            recency = math.exp(-age_minutes / 30.0)  # Decay over 30 minutes
            relevance += weights[RelevanceFactor.RECENCY] * recency

        # Frequency factor
        if RelevanceFactor.FREQUENCY in weights:
            frequency = math.log(item.access_count + 1) / math.log(100)
            relevance += weights[RelevanceFactor.FREQUENCY] * frequency

        return min(1.0, relevance)

    def _calculate_episodic_relevance(self, memory, query: RetrievalQuery,
                                     weights: Dict[RelevanceFactor, float]) -> float:
        """Calculate relevance score for episodic memory"""
        relevance = 0.0

        # Composite importance
        if RelevanceFactor.IMPORTANCE in weights:
            composite_importance = memory.calculate_composite_importance()
            relevance += weights[RelevanceFactor.IMPORTANCE] * composite_importance

        # Temporal proximity
        if RelevanceFactor.TEMPORAL_PROXIMITY in weights and query.time_range:
            current_time = time.time()
            if query.time_range[0] <= memory.timestamp <= query.time_range[1]:
                temporal_score = 1.0
            else:
                # Distance from time range
                if memory.timestamp < query.time_range[0]:
                    distance = query.time_range[0] - memory.timestamp
                else:
                    distance = memory.timestamp - query.time_range[1]
                temporal_score = math.exp(-distance / (7 * 24 * 3600))  # Decay over 7 days
            relevance += weights[RelevanceFactor.TEMPORAL_PROXIMITY] * temporal_score

        # Emotional impact
        if RelevanceFactor.EMOTIONAL_IMPACT in weights:
            emotional_impact = abs(memory.emotional_valence.value) * memory.emotional_arousal
            relevance += weights[RelevanceFactor.EMOTIONAL_IMPACT] * emotional_impact

        # Frequency/recency
        if RelevanceFactor.FREQUENCY in weights:
            frequency_score = memory.get_frequency_score()
            relevance += weights[RelevanceFactor.FREQUENCY] * frequency_score

        return min(1.0, relevance)

    def _calculate_semantic_relevance(self, concept, similarity_score, query: RetrievalQuery,
                                     weights: Dict[RelevanceFactor, float]) -> float:
        """Calculate relevance score for semantic concept"""
        relevance = 0.0

        # Semantic similarity
        if RelevanceFactor.SEMANTIC_SIMILARITY in weights:
            relevance += weights[RelevanceFactor.SEMANTIC_SIMILARITY] * similarity_score

        # Frequency of access
        if RelevanceFactor.FREQUENCY in weights:
            frequency_score = math.log(concept.access_count + 1) / math.log(100)
            relevance += weights[RelevanceFactor.FREQUENCY] * frequency_score

        return min(1.0, relevance)

    def _calculate_procedural_relevance(self, skill, query: RetrievalQuery,
                                       weights: Dict[RelevanceFactor, float]) -> float:
        """Calculate relevance score for procedural skill"""
        relevance = 0.0

        # Text matching score
        if query.query_text:
            query_lower = query.query_text.lower()
            text_score = 0.0
            if query_lower in skill.name.lower():
                text_score += 0.5
            if query_lower in skill.description.lower():
                text_score += 0.3
            if any(query_lower in tag.lower() for tag in skill.tags):
                text_score += 0.2

            if RelevanceFactor.SEMANTIC_SIMILARITY in weights:
                relevance += weights[RelevanceFactor.SEMANTIC_SIMILARITY] * text_score

        # Mastery level
        if RelevanceFactor.IMPORTANCE in weights:
            relevance += weights[RelevanceFactor.IMPORTANCE] * skill.mastery_level

        # Recent practice
        if RelevanceFactor.RECENCY in weights:
            days_since_practice = skill.get_days_since_practice()
            recency_score = math.exp(-days_since_practice / 30.0)  # Decay over 30 days
            relevance += weights[RelevanceFactor.RECENCY] * recency_score

        return min(1.0, relevance)

    def _rank_results(self, results: List[RetrievalResult], weights: Dict[RelevanceFactor, float],
                     query: RetrievalQuery) -> List[RetrievalResult]:
        """Rank and sort search results"""
        # Apply additional ranking based on query type
        for result in results:
            # Boost results that match context tags
            if query.context_tags and hasattr(result, 'metadata'):
                context_match = 0.0
                result_tags = result.metadata.get('tags', set())
                common_tags = query.context_tags & set(result_tags) if isinstance(result_tags, set) else set()
                if common_tags:
                    context_match = len(common_tags) / len(query.context_tags)
                    result.relevance_score += context_match * 0.2

        # Sort by relevance score
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results

    def _generate_explanation(self, result: RetrievalResult, query: RetrievalQuery,
                             weights: Dict[RelevanceFactor, float]) -> str:
        """Generate explanation for why a result was returned"""
        explanations = []

        # High relevance score
        if result.relevance_score > 0.8:
            explanations.append("High relevance match")

        # Memory type specific explanations
        if result.memory_type == "episodic":
            if result.metadata.get("emotional_valence"):
                explanations.append(f"Emotional content: {result.metadata['emotional_valence']}")
            if result.metadata.get("age_days", 0) < 1:
                explanations.append("Recent memory")
        elif result.memory_type == "procedural":
            if result.metadata.get("mastery_level", 0) > 0.7:
                explanations.append("Well-developed skill")
        elif result.memory_type == "working":
            if result.metadata.get("age_minutes", 0) < 5:
                explanations.append("Currently active")

        # Context matching
        if query.context_tags:
            explanations.append("Contextually relevant")

        return "; ".join(explanations) if explanations else "Matching memory found"

    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search performance statistics"""
        return {
            "total_searches": self.total_searches,
            "average_search_time": sum(self.search_times) / len(self.search_times) if self.search_times else 0.0,
            "search_patterns": self.search_patterns.copy(),
            "memory_systems_available": {
                "working_memory": self.working_memory is not None,
                "episodic_memory": self.episodic_memory is not None,
                "semantic_memory": self.semantic_memory is not None,
                "procedural_memory": self.procedural_memory is not None
            }
        }