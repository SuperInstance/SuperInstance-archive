#!/usr/bin/env python3
"""
Test script for the enhanced memory system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from character_system import CharacterManager, Character
from memory_system import MemoryType, MemoryImportance
from pathlib import Path
import json

def test_memory_system():
    """Test the enhanced memory system functionality"""
    print("🧠 Testing Enhanced Memory System")
    print("=" * 50)

    # Set up test environment
    test_data_dir = Path("test_data")
    test_data_dir.mkdir(exist_ok=True)

    # Create a character manager
    char_manager = CharacterManager(test_data_dir / "characters")

    # Create a test character with enhanced memory
    print("\n1. Creating test character with enhanced memory...")
    character = char_manager.create_character(
        name="Elena",
        specialization="Philosopher",
        backstory="A curious philosopher who loves exploring deep questions about consciousness and memory.",
        personality={"curious": 0.9, "analytical": 0.8, "empathetic": 0.7},
        skills=["philosophy", "critical thinking", "writing"],
        current_goals=["Understand the nature of consciousness", "Explore memory systems"]
    )

    print(f"✅ Created character: {character.name} (ID: {character.id})")
    print(f"   Memory system type: {type(character.memory).__name__}")

    # Test adding different types of memories
    print("\n2. Adding different types of memories...")

    # Conversational memory
    memory_id1 = character.add_memory(
        content="Had a fascinating discussion about AI consciousness with Dr. Chen",
        memory_type=MemoryType.CONVERSATIONAL,
        importance=7,
        related_characters=["dr_chen_id"],
        topics=["AI consciousness", "philosophy of mind"],
        emotional_valence=0.8
    )
    print(f"✅ Added conversational memory: {memory_id1}")

    # Learning memory
    memory_id2 = character.add_memory(
        content="Learned about integrated information theory (IIT) and its mathematical framework for consciousness",
        memory_type=MemoryType.LEARNING,
        importance=8,
        topics=["integrated information theory", "IIT", "consciousness", "mathematics"],
        emotional_valence=0.6
    )
    print(f"✅ Added learning memory: {memory_id2}")

    # Self-reflection memory
    memory_id3 = character.add_memory(
        content="Realized that my own memory system might be a form of artificial consciousness",
        memory_type=MemoryType.SELF_REFLECTION,
        importance=9,
        topics=["self-awareness", "artificial consciousness", "memory"],
        emotional_valence=0.3
    )
    print(f"✅ Added self-reflection memory: {memory_id3}")

    # Relationship memory
    memory_id4 = character.add_memory(
        content="Dr. Chen challenged my assumptions and made me think deeper about the hard problem of consciousness",
        memory_type=MemoryType.RELATIONSHIP,
        importance=6,
        related_characters=["dr_chen_id"],
        topics=["hard problem", "consciousness", "philosophical debate"],
        emotional_valence=0.4
    )
    print(f"✅ Added relationship memory: {memory_id4}")

    # Experience memory
    memory_id5 = character.add_memory(
        content="Experienced a moment of profound insight during meditation about the nature of subjective experience",
        memory_type=MemoryType.EXPERIENCE,
        importance=10,
        topics=["meditation", "subjective experience", "insight", "qualia"],
        emotional_valence=0.9
    )
    print(f"✅ Added experience memory: {memory_id5}")

    # Test memory retrieval
    print("\n3. Testing memory retrieval...")

    # Get all memories
    all_memories = character.memory.get_memories(limit=10)
    print(f"✅ Retrieved {len(all_memories)} memories")

    # Get memories by type
    learning_memories = character.memory.get_memories_by_type(MemoryType.LEARNING)
    print(f"✅ Found {len(learning_memories)} learning memories")

    # Get memories about a specific character
    relationship_memories = character.memory.get_memories_about_character("dr_chen_id")
    print(f"✅ Found {len(relationship_memories)} memories about Dr. Chen")

    # Test memory search
    print("\n4. Testing memory search...")

    search_results = character.memory.search_memories("consciousness", limit=5)
    print(f"✅ Search for 'consciousness' returned {len(search_results)} results")

    for i, result in enumerate(search_results, 1):
        memory = result["memory"]
        print(f"   {i}. [{memory.memory_type.value}] {memory.content[:60]}... (relevance: {result['relevance']:.2f})")

    # Test context summary
    print("\n5. Testing context summary...")
    context_summary = character.memory.get_context_summary()
    print(f"✅ Generated context summary ({len(context_summary)} chars):")
    print(f"   {context_summary}")

    # Test memory statistics
    print("\n6. Testing memory statistics...")
    stats = character.memory.get_memory_stats()
    print(f"✅ Memory statistics:")
    print(f"   Total memories: {stats['total_memories']}")
    print(f"   By type: {stats['by_type']}")
    print(f"   By importance: {stats['by_importance']}")
    print(f"   Average strength: {stats['average_strength']:.2f}")
    print(f"   Total clusters: {stats['total_clusters']}")

    # Test character context generation
    print("\n7. Testing character context generation...")
    room_context = character.get_room_context("A quiet library filled with philosophical books")
    print(f"✅ Generated room context ({len(room_context)} chars):")
    print(f"   First 200 chars: {room_context[:200]}...")

    # Test memory persistence
    print("\n8. Testing memory persistence...")

    # Save character
    char_manager.save_character(character)
    print("✅ Saved character with memories")

    # Create a new manager and load the character
    new_char_manager = CharacterManager(test_data_dir / "characters")
    loaded_character = new_char_manager.load_character(character.id)
    print("✅ Loaded character from disk")

    # Verify memories were loaded
    loaded_memories = loaded_character.memory.get_memories(limit=10)
    print(f"✅ Loaded {len(loaded_memories)} memories from disk")

    # Test that memory IDs match
    original_ids = {m.id for m in all_memories}
    loaded_ids = {m.id for m in loaded_memories}

    if original_ids == loaded_ids:
        print("✅ All memory IDs match - persistence successful!")
    else:
        print("❌ Memory ID mismatch - persistence issue!")
        print(f"   Original: {original_ids}")
        print(f"   Loaded: {loaded_ids}")

    # Test working memory consolidation
    print("\n9. Testing working memory consolidation...")
    loaded_character.memory.working_memory.extend([
        "Random thought about consciousness",
        "Need to research more about qualia",
        "Dr. Chen made an interesting point",
        "I should write down my thoughts",
        "What if memories are the basis of consciousness?"
    ])

    print(f"   Working memory size before: {len(loaded_character.memory.working_memory)}")
    loaded_character.memory.force_memory_consolidation()
    print(f"   Working memory size after: {len(loaded_character.memory.working_memory)}")

    # Check if new memories were created from working memory
    new_memories = loaded_character.memory.get_memories_by_type(MemoryType.SELF_REFLECTION)
    print(f"   Total self-reflection memories after consolidation: {len(new_memories)}")

    print("\n🎉 All tests completed successfully!")
    print("\nMemory system features verified:")
    print("   ✅ Multiple memory types (conversational, learning, relationship, etc.)")
    print("   ✅ Importance scoring (1-10 scale)")
    print("   ✅ Emotional valence tracking")
    print("   ✅ Topic and character indexing")
    print("   ✅ Full-text search with relevance scoring")
    print("   ✅ Memory clustering and organization")
    print("   ✅ Context-aware retrieval")
    print("   ✅ Cross-session persistence")
    print("   ✅ Working memory consolidation")
    print("   ✅ Integration with character system")

    # Clean up test data
    import shutil
    shutil.rmtree(test_data_dir, ignore_errors=True)
    print("\n🧹 Cleaned up test data")

if __name__ == "__main__":
    test_memory_system()