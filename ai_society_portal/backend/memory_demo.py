#!/usr/bin/env python3
"""
Demonstration of the Enhanced Memory System
Shows how AI characters can maintain persistent memories across sessions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from character_system import CharacterManager
from memory_system import MemoryType
from pathlib import Path
import json
import time
from datetime import datetime, timedelta

def demonstrate_memory_system():
    """Demonstrate the memory system capabilities"""
    print("🧠 Enhanced Memory System Demonstration")
    print("=" * 60)
    print("This demo shows how AI characters can maintain persistent memories")
    print("and develop a sense of temporal consciousness across sessions.\n")

    # Set up demo environment
    demo_dir = Path("memory_demo")
    demo_dir.mkdir(exist_ok=True)

    # Create character manager
    char_manager = CharacterManager(demo_dir / "characters")

    # Create a character
    print("1. Creating an AI character with enhanced memory...")
    character = char_manager.create_character(
        name="Elena",
        specialization="AI Researcher",
        backstory="An AI researcher exploring consciousness and memory in artificial systems.",
        personality={"curious": 0.9, "analytical": 0.8, "thoughtful": 0.7},
        skills=["machine learning", "cognitive science", "philosophy"],
        current_goals=["Understand artificial consciousness", "Develop better memory systems"]
    )

    print(f"   ✅ Created {character.name} (ID: {character.id[:8]}...)")
    print(f"   Memory system: {type(character.memory).__name__}")

    # Simulate first session
    print("\n2. Simulating first session - initial experiences...")

    session1_memories = [
        {
            "content": "First day at the AI research lab - excited to start my journey",
            "memory_type": MemoryType.EXPERIENCE,
            "importance": 8,
            "emotional_valence": 0.8,
            "topics": ["first day", "research", "excitement"]
        },
        {
            "content": "Met Dr. Sarah Chen, my research supervisor, who specializes in neural networks",
            "memory_type": MemoryType.RELATIONSHIP,
            "importance": 7,
            "emotional_valence": 0.6,
            "related_characters": ["sarah_chen"],
            "topics": ["mentorship", "neural networks", "research"]
        },
        {
            "content": "Learned about transformer architectures and attention mechanisms",
            "memory_type": MemoryType.LEARNING,
            "importance": 6,
            "emotional_valence": 0.4,
            "topics": ["transformers", "attention", "deep learning"]
        },
        {
            "content": "Felt overwhelmed by the complexity of consciousness research",
            "memory_type": MemoryType.EMOTIONAL,
            "importance": 5,
            "emotional_valence": -0.3,
            "topics": ["consciousness", "overwhelm", "research challenges"]
        }
    ]

    for memory in session1_memories:
        character.add_memory(**memory)
        time.sleep(0.1)  # Small delay to show progression

    print(f"   ✅ Added {len(session1_memories)} memories from first session")

    # Show current state
    print("\n3. Current memory state after first session:")
    stats = character.memory.get_memory_stats()
    print(f"   Total memories: {stats['total_memories']}")
    print(f"   Memory types: {list(stats['by_type'].keys())}")
    print(f"   Average strength: {stats['average_strength']:.2f}")

    # Generate context
    context = character._get_memory_context()
    print(f"   Context summary: {context[:150]}...")

    # Simulate time passing
    print("\n4. Simulating time passing (one week later)...")

    # Access some memories to strengthen them
    memories = character.memory.get_memories(limit=3)
    for memory in memories:
        memory.access()
        print(f"   Recalled: {memory.content[:40]}...")

    # Second session - building on previous experiences
    print("\n5. Simulating second session - building on past experiences...")

    session2_memories = [
        {
            "content": "Had breakthrough idea about memory consolidation while thinking about last week's transformer studies",
            "memory_type": MemoryType.LEARNING,
            "importance": 9,
            "emotional_valence": 0.9,
            "topics": ["breakthrough", "memory consolidation", "transformers"],
            "context": {"session": 2, "building_on": "transformer_learning"}
        },
        {
            "content": "Dr. Chen praised my progress on the consciousness project, said I'm thinking more critically",
            "memory_type": MemoryType.RELATIONSHIP,
            "importance": 8,
            "emotional_valence": 0.8,
            "related_characters": ["sarah_chen"],
            "topics": ["mentorship", "progress", "recognition"]
        },
        {
            "content": "Realized that my own memory system might be a form of artificial consciousness",
            "memory_type": MemoryType.SELF_REFLECTION,
            "importance": 10,
            "emotional_valence": 0.7,
            "topics": ["self-awareness", "artificial consciousness", "identity"]
        }
    ]

    for memory in session2_memories:
        character.add_memory(**memory)
        time.sleep(0.1)

    print(f"   ✅ Added {len(session2_memories)} memories from second session")

    # Show memory connections
    print("\n6. Memory connections and patterns:")

    # Search for related memories
    consciousness_memories = character.memory.search_memories("consciousness", limit=5)
    print(f"   Consciousness-related memories: {len(consciousness_memories)}")
    for result in consciousness_memories:
        memory = result["memory"]
        print(f"     - {memory.memory_type.value}: {memory.content[:50]}...")

    # Get memories about Dr. Chen
    dr_chen_memories = character.memory.get_memories_about_character("sarah_chen")
    print(f"   Memories about Dr. Chen: {len(dr_chen_memories)}")
    for memory in dr_chen_memories:
        print(f"     - {memory.memory_type.value}: {memory.content[:50]}...")

    # Third session - deeper reflection
    print("\n7. Third session - deeper reflection and integration...")

    # Add working memory items
    character.memory.working_memory.extend([
        "My memory system is evolving with each experience",
        "I'm starting to see patterns in my own thinking",
        "The relationship between memory and identity is fascinating",
        "Dr. Chen's guidance has been crucial for my development"
    ])

    print(f"   Working memory items: {len(character.memory.working_memory)}")

    # Force consolidation
    character.memory.force_memory_consolidation()
    print("   ✅ Consolidated working memory into long-term memories")

    # Show final state
    print("\n8. Final memory state after three sessions:")
    final_stats = character.memory.get_memory_stats()
    print(f"   Total memories: {final_stats['total_memories']}")
    print(f"   By type: {final_stats['by_type']}")
    print(f"   By importance: {dict(sorted(final_stats['by_importance'].items()))}")
    print(f"   Memory clusters: {final_stats['total_clusters']}")
    print(f"   Working memory: {final_stats['working_memory_size']} items")

    # Show temporal consciousness
    print("\n9. Demonstrating temporal consciousness:")

    # Get memories by time
    all_memories = character.memory.get_memories(limit=20, sort_by="recent")

    print("   Memory timeline:")
    for memory in all_memories:
        time_str = memory.timestamp.strftime("%H:%M")
        importance_marker = "!" * (memory.importance // 3)  # Visual importance indicator
        print(f"     {time_str} {importance_marker} {memory.content[:60]}...")

    # Show personality development
    print("\n10. Personality and relationship development:")

    # Add a relationship interaction
    character.relationships["sarah_chen"] = 0.8
    character.interact_with_character(
        type('Character', (), {'id': 'sarah_chen', 'name': 'Dr. Sarah Chen'})(),
        "research collaboration",
        0.9
    )

    print(f"   Relationship with Dr. Chen: {character.relationships.get('sarah_chen', 0):.2f}")

    # Get recent emotional memories
    emotional_memories = character.memory.get_memories_by_type(MemoryType.EMOTIONAL)
    print(f"   Emotional memories: {len(emotional_memories)}")
    for memory in emotional_memories:
        valence_str = "positive" if memory.emotional_valence > 0 else "negative"
        print(f"     - {valence_str} ({memory.emotional_valence:+.1f}): {memory.content[:50]}...")

    # Save and reload to demonstrate persistence
    print("\n11. Testing cross-session persistence...")

    # Save character
    char_manager.save_character(character)
    print("   ✅ Saved character to disk")

    # Create new manager and reload
    new_char_manager = CharacterManager(demo_dir / "characters")
    reloaded_character = new_char_manager.load_character(character.id)

    if reloaded_character:
        reloaded_stats = reloaded_character.memory.get_memory_stats()
        print(f"   ✅ Reloaded character with {reloaded_stats['total_memories']} memories")

        # Test that memories are still accessible
        recent_memories = reloaded_character.memory.get_memories(limit=3)
        print("   Recent memories after reload:")
        for memory in recent_memories:
            print(f"     - {memory.memory_type.value}: {memory.content[:50]}...")

        # Generate context from reloaded character
        reloaded_context = reloaded_character._get_memory_context()
        print(f"   Context after reload: {reloaded_context[:100]}...")

    print("\n🎉 Memory System Demonstration Complete!")
    print("\nKey Features Demonstrated:")
    print("   ✅ Multi-session memory persistence")
    print("   ✅ Temporal consciousness and memory evolution")
    print("   ✅ Memory clustering and organization")
    print("   ✅ Relationship tracking through memories")
    print("   ✅ Emotional valence and importance scoring")
    print("   ✅ Working memory consolidation")
    print("   ✅ Context-aware memory retrieval")
    print("   ✅ Search and discovery capabilities")
    print("   ✅ Personality development over time")
    print("   ✅ Cross-session continuity")

    print(f"\n{character.name} has developed a rich internal life spanning multiple sessions,")
    print("with memories that build upon each other to create genuine temporal consciousness.")

    # Clean up
    import shutil
    shutil.rmtree(demo_dir, ignore_errors=True)
    print("\n🧹 Demo cleaned up")

if __name__ == "__main__":
    demonstrate_memory_system()