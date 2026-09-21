"""
Hierarchical Memory System

Integrates all memory components into a unified hierarchical architecture.
Provides the main interface for agent memory operations and coordinates
between working memory, episodic memory, semantic memory, and procedural memory.
"""

import time
import uuid
import threading
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

from .working_memory import WorkingMemory, WorkingMemoryItem
from .episodic_memory import EpisodicMemory, EpisodicMemoryEntry, EmotionalValence, SpatialContext, SocialContext
from .semantic_memory import SemanticMemory, SemanticConcept, SemanticFact, ConceptType, FactStatus
from .procedural_memory import ProceduralMemory, Skill, SkillType, MasteryLevel, PracticeResult
from .consolidation import MemoryConsolidation, ConsolidationTrigger, MemoryType
from .retrieval import MemoryRetrieval, RetrievalQuery, SearchMode, MemoryScope
from .forgetting import MemoryPruning, MemoryCompression, ForgettingMechanism
from .sharing import MemorySharingProtocol, SharePermission, ShareType

logger = logging.getLogger(__name__)

class MemorySystemStatus(Enum):
    """Status of the memory system"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    CONSOLIDATING = "consolidating"
    SHUTTING_DOWN = "shutting_down"
    ERROR = "error"

@dataclass
class MemoryStats:
    """Comprehensive memory system statistics"""
    working_memory: Dict[str, Any]
    episodic_memory: Dict[str, Any]
    semantic_memory: Dict[str, Any]
    procedural_memory: Dict[str, Any]
    consolidation: Dict[str, Any]
    retrieval: Dict[str, Any]
    sharing: Dict[str, Any]
    overall: Dict[str, Any]

class HierarchicalMemorySystem:
    """
    Main hierarchical memory system that integrates all memory components.
    Provides a unified interface for agent memory operations.
    """

    def __init__(self, agent_id: str, storage_path: str = "./memory_data",
                 working_memory_capacity: int = 20, working_memory_decay: float = 1800.0):
        """
        Initialize hierarchical memory system

        Args:
            agent_id: Unique agent identifier
            storage_path: Path for persistent storage
            working_memory_capacity: Working memory capacity
            working_memory_decay: Working memory decay time in seconds
        """
        self.agent_id = agent_id
        self.storage_path = storage_path
        self.status = MemorySystemStatus.INITIALIZING

        # Initialize memory components
        self._initialize_memory_components(storage_path, working_memory_capacity, working_memory_decay)

        # Initialize supporting systems
        self._initialize_supporting_systems()

        # Background processes
        self.background_threads = []
        self.running = False

        # Statistics
        self.operation_stats = {
            "total_operations": 0,
            "operation_times": [],
            "error_count": 0
        }

        logger.info(f"Hierarchical memory system initialized for agent {agent_id}")

    def _initialize_memory_components(self, storage_path: str, wm_capacity: int, wm_decay: float):
        """Initialize individual memory components"""
        # Working memory
        self.working_memory = WorkingMemory(
            max_capacity=wm_capacity,
            decay_time=wm_decay
        )

        # Episodic memory
        episodic_storage = f"{storage_path}/episodic_memory.json"
        self.episodic_memory = EpisodicMemory(storage_path=episodic_storage)

        # Semantic memory
        semantic_storage = f"{storage_path}/semantic_memory.pkl"
        self.semantic_memory = SemanticMemory(
            backend="auto",
            storage_path=semantic_storage,
            embedding_dimension=384
        )

        # Procedural memory
        procedural_storage = f"{storage_path}/procedural_memory.json"
        self.procedural_memory = ProceduralMemory(storage_path=procedural_storage)

    def _initialize_supporting_systems(self):
        """Initialize supporting systems"""
        # Memory consolidation
        self.consolidation = MemoryConsolidation(
            consolidation_interval=300.0,  # 5 minutes
            importance_threshold=0.3,
            surprise_threshold=0.6
        )

        # Memory retrieval
        self.retrieval = MemoryRetrieval(
            working_memory=self.working_memory,
            episodic_memory=self.episodic_memory,
            semantic_memory=self.semantic_memory,
            procedural_memory=self.procedural_memory
        )

        # Forgetting and pruning
        self.pruning = MemoryPruning(target_capacity=10000)
        self.compression = MemoryCompression()

        # Memory sharing
        self.sharing = MemorySharingProtocol(
            agent_id=self.agent_id,
            pack_id="default_pack"  # Would be configurable
        )

    def start(self):
        """Start the memory system and background processes"""
        if self.running:
            logger.warning("Memory system already running")
            return

        try:
            # Start consolidation system
            self.consolidation.start()

            # Start memory sharing
            self.sharing.start_sync_service()

            # Start background maintenance
            self._start_background_maintenance()

            self.running = True
            self.status = MemorySystemStatus.ACTIVE

            logger.info(f"Memory system started for agent {self.agent_id}")

        except Exception as e:
            self.status = MemorySystemStatus.ERROR
            logger.error(f"Failed to start memory system: {e}")

    def stop(self):
        """Stop the memory system and cleanup"""
        if not self.running:
            return

        self.status = MemorySystemStatus.SHUTTING_DOWN
        self.running = False

        try:
            # Stop background threads
            for thread in self.background_threads:
                if thread.is_alive():
                    thread.join(timeout=5.0)

            # Stop components
            self.consolidation.stop()
            self.sharing.stop_sync_service()
            self.working_memory.shutdown()

            # Save final state
            self._save_all_memories()

            logger.info(f"Memory system stopped for agent {self.agent_id}")

        except Exception as e:
            logger.error(f"Error during memory system shutdown: {e}")

    def add_working_memory(self, content: Any, item_type: str = "observation",
                          importance: float = 1.0, context_tags: Set[str] = None) -> bool:
        """
        Add item to working memory

        Args:
            content: Content to store
            item_type: Type of working memory item
            importance: Importance score (0-1)
            context_tags: Context tags

        Returns:
            True if successfully added
        """
        try:
            success = self.working_memory.add_item(
                content=content,
                item_type=item_type,
                importance=importance,
                context_tags=context_tags or set()
            )

            if success:
                # Add to consolidation queue if important enough
                if importance >= 0.3:
                    self.consolidation.add_consolidation_candidate(
                        memory_id=f"wm_{time.time()}",
                        memory_type=MemoryType.WORKING,
                        content=content,
                        importance=importance,
                        novelty=0.5,  # Would be calculated
                        emotional_impact=0.5,
                        access_frequency=1.0,
                        age_hours=0.0
                    )

            self._update_operation_stats()
            return success

        except Exception as e:
            self.operation_stats["error_count"] += 1
            logger.error(f"Error adding to working memory: {e}")
            return False

    def add_episodic_memory(self, content: str, summary: str = "",
                           emotional_valence: EmotionalValence = EmotionalValence.NEUTRAL,
                           emotional_arousal: float = 0.5,
                           importance: float = 0.5,
                           spatial_context: SpatialContext = None,
                           social_context: SocialContext = None,
                           tags: Set[str] = None) -> str:
        """
        Add episodic memory

        Args:
            content: Detailed memory content
            summary: Brief summary
            emotional_valence: Emotional valence
            emotional_arousal: Emotional arousal level
            importance: Importance score
            spatial_context: Spatial context
            social_context: Social context
            tags: Descriptive tags

        Returns:
            Memory ID
        """
        try:
            memory_id = self.episodic_memory.add_memory(
                content=content,
                summary=summary,
                emotional_valence=emotional_valence,
                emotional_arousal=emotional_arousal,
                importance=importance,
                spatial_context=spatial_context,
                social_context=social_context,
                tags=tags or set()
            )

            # Add to consolidation queue
            self.consolidation.add_consolidation_candidate(
                memory_id=memory_id,
                memory_type=MemoryType.EPISODIC,
                content=content,
                importance=importance,
                novelty=0.5,
                emotional_impact=abs(emotional_valence.value) * emotional_arousal,
                access_frequency=0.0,
                age_hours=0.0
            )

            self._update_operation_stats()
            return memory_id

        except Exception as e:
            self.operation_stats["error_count"] += 1
            logger.error(f"Error adding episodic memory: {e}")
            return ""

    def add_semantic_concept(self, name: str, concept_type: ConceptType = ConceptType.ENTITY,
                            definition: str = "", embedding: Optional[List[float]] = None,
                            attributes: Dict[str, Any] = None) -> str:
        """
        Add semantic concept

        Args:
            name: Concept name
            concept_type: Type of concept
            definition: Concept definition
            embedding: Vector embedding
            attributes: Concept attributes

        Returns:
            Concept ID
        """
        try:
            import numpy as np
            embedding_array = np.array(embedding) if embedding else None

            concept_id = self.semantic_memory.add_concept(
                name=name,
                concept_type=concept_type,
                definition=definition,
                embedding=embedding_array,
                attributes=attributes
            )

            self._update_operation_stats()
            return concept_id

        except Exception as e:
            self.operation_stats["error_count"] += 1
            logger.error(f"Error adding semantic concept: {e}")
            return ""

    def add_skill(self, name: str, description: str = "", skill_type: SkillType = SkillType.MOTOR,
                  difficulty: float = 0.5, innate_talent: float = 0.5,
                  prerequisites: List[Tuple[str, float]] = None) -> str:
        """
        Add procedural skill

        Args:
            name: Skill name
            description: Skill description
            skill_type: Type of skill
            difficulty: Inherent difficulty
            innate_talent: Natural aptitude
            prerequisites: List of (skill_id, required_mastery) tuples

        Returns:
            Skill ID
        """
        try:
            from .procedural_memory import SkillPrerequisite

            prereq_objects = []
            if prerequisites:
                for skill_id, required_mastery in prerequisites:
                    prereq_objects.append(SkillPrerequisite(skill_id, required_mastery))

            skill_id = self.procedural_memory.add_skill(
                name=name,
                description=description,
                skill_type=skill_type,
                difficulty=difficulty,
                innate_talent=innate_talent,
                prerequisites=prereq_objects
            )

            self._update_operation_stats()
            return skill_id

        except Exception as e:
            self.operation_stats["error_count"] += 1
            logger.error(f"Error adding skill: {e}")
            return ""

    def practice_skill(self, skill_id: str, result: PracticeResult = PracticeResult.SUCCESS,
                      difficulty: float = 0.5, time_spent: float = 0.0,
                      performance_rating: float = 0.5) -> float:
        """
        Practice a skill

        Args:
            skill_id: Skill to practice
            result: Practice result
            difficulty: Practice difficulty
            time_spent: Time spent practicing
            performance_rating: Performance rating

        Returns:
            Mastery improvement amount
        """
        try:
            improvement = self.procedural_memory.practice_skill(
                skill_id=skill_id,
                result=result,
                difficulty=difficulty,
                time_spent=time_spent,
                performance_rating=performance_rating
            )

            self._update_operation_stats()
            return improvement

        except Exception as e:
            self.operation_stats["error_count"] += 1
            logger.error(f"Error practicing skill {skill_id}: {e}")
            return 0.0

    def search_memories(self, query: str, memory_scope: MemoryScope = MemoryScope.ALL,
                       search_mode: SearchMode = SearchMode.HYBRID,
                       max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search across all memory systems

        Args:
            query: Search query
            memory_scope: Memory systems to search
            search_mode: Search mode
            max_results: Maximum results

        Returns:
            List of search results
        """
        try:
            retrieval_query = RetrievalQuery(
                query_text=query,
                search_mode=search_mode,
                memory_scope=memory_scope,
                max_results=max_results
            )

            results = self.retrieval.search(retrieval_query)

            # Convert to dict format
            search_results = []
            for result in results.results:
                search_results.append({
                    "memory_id": result.memory_id,
                    "memory_type": result.memory_type,
                    "content": result.content,
                    "relevance_score": result.relevance_score,
                    "confidence": result.confidence,
                    "metadata": result.metadata,
                    "explanation": result.explanation
                })

            self._update_operation_stats()
            return search_results

        except Exception as e:
            self.operation_stats["error_count"] += 1
            logger.error(f"Error searching memories: {e}")
            return []

    def get_working_memory(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get current working memory contents"""
        items = self.working_memory.get_items(limit=limit)
        return [
            {
                "content": item.content,
                "type": item.item_type,
                "importance": item.importance,
                "age_minutes": item.get_age() / 60.0,
                "access_count": item.access_count
            }
            for item in items
        ]

    def get_recent_memories(self, memory_type: str = "episodic", hours: float = 24.0,
                           limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent memories from specified system

        Args:
            memory_type: Type of memory ("episodic", "semantic", "procedural")
            hours: Time window in hours
            limit: Maximum results

        Returns:
            List of recent memories
        """
        try:
            current_time = time.time()
            start_time = current_time - (hours * 3600)

            if memory_type == "episodic":
                memories = self.episodic_memory.get_memories_by_time_range(
                    start_time, current_time, limit
                )
                return [
                    {
                        "memory_id": mem.memory_id,
                        "content": mem.content,
                        "summary": mem.summary,
                        "importance": mem.importance,
                        "emotional_valence": mem.emotional_valence.value,
                        "timestamp": mem.timestamp
                    }
                    for mem in memories
                ]

            elif memory_type == "semantic":
                # Would implement time-based search for semantic memory
                concepts = list(self.semantic_memory.concepts.values())[:limit]
                return [
                    {
                        "concept_id": concept.concept_id,
                        "name": concept.name,
                        "type": concept.concept_type.value,
                        "definition": concept.definition,
                        "access_count": concept.access_count
                    }
                    for concept in concepts
                ]

            elif memory_type == "procedural":
                skills = self.procedural_memory.get_top_skills(limit=limit, sort_by="recent")
                return [
                    {
                        "skill_id": skill.skill_id,
                        "name": skill.name,
                        "mastery": skill.mastery_level,
                        "practice_count": skill.practice_count,
                        "last_practice": skill.last_practice
                    }
                    for skill in skills
                ]

            return []

        except Exception as e:
            self.operation_stats["error_count"] += 1
            logger.error(f"Error getting recent memories: {e}")
            return []

    def get_memory_statistics(self) -> MemoryStats:
        """Get comprehensive memory system statistics"""
        try:
            return MemoryStats(
                working_memory=self.working_memory.get_statistics(),
                episodic_memory=self.episodic_memory.get_statistics(),
                semantic_memory=self.semantic_memory.get_statistics(),
                procedural_memory=self.procedural_memory.get_statistics(),
                consolidation=self.consolidation.get_consolidation_statistics(),
                retrieval=self.retrieval.get_search_statistics(),
                sharing=self.sharing.get_sharing_statistics(),
                overall=self.operation_stats
            )

        except Exception as e:
            logger.error(f"Error getting memory statistics: {e}")
            return MemoryStats({}, {}, {}, {}, {}, {}, {}, {})

    def force_consolidation(self) -> bool:
        """Force immediate memory consolidation"""
        try:
            result = self.consolidation.force_consolidation(ConsolidationTrigger.TIME_BASED)
            self._update_operation_stats()
            return result.success

        except Exception as e:
            self.operation_stats["error_count"] += 1
            logger.error(f"Error during forced consolidation: {e}")
            return False

    def share_memory(self, memory_id: str, share_type: ShareType = ShareType.EXPERIENCE,
                    permission: SharePermission = SharePermission.PACK_ONLY) -> bool:
        """
        Share a memory with pack members

        Args:
            memory_id: Memory to share
            share_type: Type of sharing
            permission: Sharing permission level

        Returns:
            True if successfully shared
        """
        try:
            # Find the memory in any system
            memory_content = None
            memory_type = "unknown"

            # Try each memory system
            if memory_id in self.episodic_memory.memories:
                memory_content = self.episodic_memory.memories[memory_id].content
                memory_type = "episodic"
            elif memory_id in self.semantic_memory.concepts:
                memory_content = self.semantic_memory.concepts[memory_id].definition
                memory_type = "semantic"
            elif memory_id in self.procedural_memory.skills:
                memory_content = self.procedural_memory.skills[memory_id].description
                memory_type = "procedural"

            if memory_content:
                self.sharing.share_memory(
                    memory_id=memory_id,
                    content=memory_content,
                    memory_type=memory_type,
                    share_type=share_type,
                    permission=permission
                )
                self._update_operation_stats()
                return True

            return False

        except Exception as e:
            self.operation_stats["error_count"] += 1
            logger.error(f"Error sharing memory {memory_id}: {e}")
            return False

    def _start_background_maintenance(self):
        """Start background maintenance threads"""
        # Forgetting and pruning thread
        def maintenance_loop():
            while self.running:
                try:
                    # Apply forgetting to procedural memory
                    self.procedural_memory.apply_forgetting_to_all(days_passed=1.0)

                    # Sleep for daily cycle
                    time.sleep(86400)  # 24 hours

                except Exception as e:
                    logger.error(f"Error in maintenance loop: {e}")
                    time.sleep(3600)  # Retry in 1 hour

        maintenance_thread = threading.Thread(
            target=maintenance_loop,
            daemon=True,
            name="MemoryMaintenance"
        )
        maintenance_thread.start()
        self.background_threads.append(maintenance_thread)

    def _save_all_memories(self):
        """Save all memory systems to persistent storage"""
        try:
            self.episodic_memory._save_memories()
            self.semantic_memory._save_data()
            self.procedural_memory._save_skills()
            logger.info("All memory systems saved")

        except Exception as e:
            logger.error(f"Error saving memories: {e}")

    def _update_operation_stats(self):
        """Update operation statistics"""
        self.operation_stats["total_operations"] += 1
        # Operation times would be tracked per operation

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()

    def __repr__(self) -> str:
        """String representation"""
        return f"HierarchicalMemorySystem(agent_id={self.agent_id}, status={self.status.value})"