#!/usr/bin/env python3
"""
Luciddreamer Memory System Example

Demonstrates the comprehensive hierarchical memory system for AI agents.
Shows working memory, episodic memory, semantic memory, procedural memory,
consolidation, retrieval, forgetting, and sharing capabilities.
"""

import time
import os
import sys
import numpy as np
from typing import Set

# Add the src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from memory.hierarchical_memory import HierarchicalMemorySystem
from memory.episodic_memory import EmotionalValence, SpatialContext, SocialContext
from memory.semantic_memory import ConceptType
from memory.procedural_memory import SkillType, PracticeResult
from memory.retrieval import SearchMode, MemoryScope
from memory.sharing import ShareType, SharePermission

def demonstrate_working_memory(memory_system):
    """Demonstrate working memory capabilities"""
    print("\n=== Working Memory Demo ===")

    # Add various items to working memory
    memory_system.add_working_memory(
        content="Saw a strange glowing artifact in the forest",
        item_type="observation",
        importance=0.8,
        context_tags={"exploration", "mystery"}
    )

    memory_system.add_working_memory(
        content="Need to investigate the artifact further",
        item_type="thought",
        importance=0.7,
        context_tags={"planning", "investigation"}
    )

    memory_system.add_working_memory(
        content="Feeling curious and cautious",
        item_type="emotion",
        importance=0.6,
        context_tags={"emotion", "caution"}
    )

    # Show working memory contents
    wm_contents = memory_system.get_working_memory()
    print(f"Working memory contains {len(wm_contents)} items:")
    for i, item in enumerate(wm_contents, 1):
        print(f"  {i}. [{item['type']}] {item['content'][:50]}... (importance: {item['importance']:.2f})")

def demonstrate_episodic_memory(memory_system):
    """Demonstrate episodic memory capabilities"""
    print("\n=== Episodic Memory Demo ===")

    # Add detailed episodic memories
    memory_id1 = memory_system.add_episodic_memory(
        content="While exploring the ancient forest at dawn, I discovered a mysterious crystal artifact pulsing with blue light. The artifact was hovering above a stone pedestal, emitting a low humming sound. As I approached, the light intensified and I felt a strange energy field.",
        summary="Found mysterious crystal artifact in ancient forest",
        emotional_valence=EmotionalValence.POSITIVE,
        emotional_arousal=0.8,
        importance=0.9,
        spatial_context=SpatialContext(
            location="ancient_forest",
            environment="outdoor",
            objects_present=["crystal_artifact", "stone_pedestal", "trees"]
        ),
        social_context=SocialContext(
            participants=["self"],
            social_role="explorer",
            group_size=1
        ),
        tags={"discovery", "artifact", "supernatural", "exploration"}
    )

    memory_id2 = memory_system.add_episodic_memory(
        content="Later that evening, I met with Sarah, the village elder, to discuss my discovery. She seemed worried and mentioned old legends about similar artifacts. She warned me that some artifacts choose their bearers and cannot be separated from them once touched.",
        summary="Met with village elder about artifact discovery",
        emotional_valence=EmotionalValence.NEUTRAL,
        emotional_arousal=0.5,
        importance=0.7,
        social_context=SocialContext(
            participants=["self", "Sarah"],
            social_role="adventurer",
            group_size=2
        ),
        tags={"social_interaction", "warning", "legend", "elder"}
    )

    print(f"Added {len([memory_id1, memory_id2])} episodic memories")

def demonstrate_semantic_memory(memory_system):
    """Demonstrate semantic memory capabilities"""
    print("\n=== Semantic Memory Demo ===")

    # Add semantic concepts
    artifact_id = memory_system.add_semantic_concept(
        name="Crystal Artifact",
        concept_type=ConceptType.ENTITY,
        definition="A supernatural object made of crystalline material that emits energy and appears to have magical properties.",
        embedding=np.random.rand(384).tolist(),  # Simulated embedding
        attributes={
            "material": "crystal",
            "properties": ["glowing", "energy_emitting", "supernatural"],
            "danger_level": "unknown"
        }
    )

    forest_id = memory_system.add_semantic_concept(
        name="Ancient Forest",
        concept_type=ConceptType.ENTITY,
        definition="An old-growth forest with mysterious properties and supernatural phenomena.",
        embedding=np.random.rand(384).tolist(),
        attributes={
            "location": "near_village",
            "danger_level": "moderate",
            "features": ["old_trees", "stone_structures", "wildlife"]
        }
    )

    elder_id = memory_system.add_semantic_concept(
        name="Village Elder",
        concept_type=ConceptType.ENTITY,
        definition="A respected older person in the village who possesses knowledge of local history and legends.",
        embedding=np.random.rand(384).tolist(),
        attributes={
            "role": "knowledge_keeper",
            "trustworthiness": "high",
            "specialization": "legends"
        }
    )

    print(f"Added {len([artifact_id, forest_id, elder_id])} semantic concepts")

def demonstrate_procedural_memory(memory_system):
    """Demonstrate procedural memory capabilities"""
    print("\n=== Procedural Memory Demo ===")

    # Add skills
    exploration_id = memory_system.add_skill(
        name="Wilderness Exploration",
        description="Ability to navigate and survive in wilderness environments, identify landmarks, and track wildlife.",
        skill_type=SkillType.SURVIVAL,
        difficulty=0.6,
        innate_talent=0.7
    )

    artifact_id = memory_system.add_skill(
        name="Artifact Investigation",
        description="Careful examination and analysis of unknown artifacts to determine their properties and origins.",
        skill_type=SkillType.TECHNICAL,
        difficulty=0.8,
        innate_talent=0.5
    )

    communication_id = memory_system.add_skill(
        name="Elder Communication",
        description="Ability to communicate respectfully with village elders and extract valuable information.",
        skill_type=SkillType.SOCIAL,
        difficulty=0.4,
        innate_talent=0.6
    )

    # Practice some skills
    improvement1 = memory_system.practice_skill(
        skill_id=exploration_id,
        result=PracticeResult.SUCCESS,
        difficulty=0.5,
        time_spent=3600,  # 1 hour
        performance_rating=0.8
    )

    improvement2 = memory_system.practice_skill(
        skill_id=artifact_id,
        result=PracticeResult.IMPROVEMENT,
        difficulty=0.7,
        time_spent=1800,  # 30 minutes
        performance_rating=0.6
    )

    print(f"Added 3 skills and practiced them (improvements: {improvement1:.3f}, {improvement2:.3f})")

def demonstrate_memory_search(memory_system):
    """Demonstrate memory search capabilities"""
    print("\n=== Memory Search Demo ===")

    # Search for different types of memories
    searches = [
        ("artifact", MemoryScope.ALL, SearchMode.HYBRID),
        ("forest", MemoryScope.ALL, SearchMode.SEMANTIC),
        ("elder", MemoryScope.ALL, SearchMode.CONTEXTUAL),
        ("crystal glowing", MemoryScope.EPISODIC, SearchMode.TEMPORAL)
    ]

    for query, scope, mode in searches:
        print(f"\nSearching for '{query}' in {scope.value} memory using {mode.value} mode:")
        results = memory_system.search_memories(query, scope, mode, max_results=5)

        for i, result in enumerate(results, 1):
            print(f"  {i}. [{result['memory_type']}] {str(result['content'])[:80]}...")
            print(f"     Relevance: {result['relevance_score']:.3f}, Confidence: {result['confidence']:.3f}")
            if result['explanation']:
                print(f"     Why: {result['explanation']}")

def demonstrate_consolidation(memory_system):
    """Demonstrate memory consolidation"""
    print("\n=== Memory Consolidation Demo ===")

    # Force consolidation
    print("Triggering memory consolidation...")
    success = memory_system.force_consolidation()

    if success:
        print("Consolidation completed successfully!")

        # Show consolidation statistics
        stats = memory_system.get_memory_statistics()
        print(f"Consolidation stats: {stats.consolidation}")
    else:
        print("Consolidation failed or no memories to consolidate")

def demonstrate_memory_sharing(memory_system):
    """Demonstrate memory sharing capabilities"""
    print("\n=== Memory Sharing Demo ===")

    # Get recent episodic memories
    recent_memories = memory_system.get_recent_memories("episodic", hours=24, limit=3)

    if recent_memories:
        # Share the most important memory
        top_memory = recent_memories[0]
        print(f"Sharing memory: {top_memory['summary']}")

        success = memory_system.share_memory(
            memory_id=top_memory['memory_id'],
            share_type=ShareType.EXPERIENCE,
            permission=SharePermission.PACK_ONLY
        )

        if success:
            print("Memory shared successfully!")
        else:
            print("Failed to share memory")
    else:
        print("No recent episodic memories to share")

def demonstrate_statistics(memory_system):
    """Display comprehensive memory system statistics"""
    print("\n=== Memory System Statistics ===")

    stats = memory_system.get_memory_statistics()

    print(f"\nWorking Memory:")
    print(f"  Items: {stats.working_memory.get('current_items', 0)}/{stats.working_memory.get('max_capacity', 0)}")
    print(f"  Usage: {stats.working_memory.get('usage_ratio', 0):.2%}")

    print(f"\nEpisodic Memory:")
    print(f"  Total memories: {stats.episodic_memory.get('total_memories', 0)}")
    print(f"  Average importance: {stats.episodic_memory.get('average_importance', 0):.3f}")

    print(f"\nSemantic Memory:")
    print(f"  Total concepts: {stats.semantic_memory.get('total_concepts', 0)}")
    print(f"  Total facts: {stats.semantic_memory.get('total_facts', 0)}")
    print(f"  Vector DB: {stats.semantic_memory.get('vector_db_backend', 'Unknown')}")

    print(f"\nProcedural Memory:")
    print(f"  Total skills: {stats.procedural_memory.get('total_skills', 0)}")
    print(f"  Average mastery: {stats.procedural_memory.get('average_mastery', 0):.3f}")
    print(f"  Total practice time: {stats.procedural_memory.get('total_practice_time', 0):.1f} hours")

    print(f"\nConsolidation System:")
    print(f"  Total consolidations: {stats.consolidation.get('total_consolidations', 0)}")
    print(f"  Success rate: {stats.consolidation.get('success_rate', 0):.2%}")

    print(f"\nRetrieval System:")
    print(f"  Total searches: {stats.retrieval.get('total_searches', 0)}")
    print(f"  Average search time: {stats.retrieval.get('average_search_time', 0):.3f}s")

    print(f"\nOverall Performance:")
    print(f"  Total operations: {stats.overall.get('total_operations', 0)}")
    print(f"  Error count: {stats.overall.get('error_count', 0)}")

def main():
    """Main demonstration function"""
    print("Luciddreamer Hierarchical Memory System Demonstration")
    print("=" * 60)

    # Create memory storage directory
    storage_path = "./luciddreamer_memory_demo"
    os.makedirs(storage_path, exist_ok=True)

    # Initialize memory system
    print("\nInitializing memory system...")
    with HierarchicalMemorySystem(
        agent_id="demo_agent_001",
        storage_path=storage_path,
        working_memory_capacity=20,
        working_memory_decay=1800.0  # 30 minutes
    ) as memory_system:

        print("Memory system initialized successfully!")

        # Run demonstrations
        demonstrate_working_memory(memory_system)
        demonstrate_episodic_memory(memory_system)
        demonstrate_semantic_memory(memory_system)
        demonstrate_procedural_memory(memory_system)
        demonstrate_memory_search(memory_system)
        demonstrate_consolidation(memory_system)
        demonstrate_memory_sharing(memory_system)
        demonstrate_statistics(memory_system)

        print("\n" + "=" * 60)
        print("Demonstration completed!")
        print(f"Memory data saved in: {storage_path}")

if __name__ == "__main__":
    main()