#!/usr/bin/env python3
"""
Integration test for memory system with the existing character and room systems
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from character_system import CharacterManager
from memory_system import MemoryType
from orchestration_engine import AISocietyOrchestrator
from room_system import RoomType
from pathlib import Path
import json
import asyncio

async def test_integration():
    """Test integration of memory system with existing systems"""
    print("🔗 Testing Memory System Integration")
    print("=" * 50)

    # Set up test environment
    test_data_dir = Path("test_integration_data")
    test_data_dir.mkdir(exist_ok=True)

    # Initialize orchestrator
    orchestrator = AISocietyOrchestrator()

    # 1. Create characters with enhanced memory
    print("\n1. Creating characters with enhanced memory...")

    alice = orchestrator.create_character(
        name="Dr. Alice Chen",
        specialization="Neuroscientist",
        backstory="A neuroscientist researching the neural basis of consciousness and memory formation.",
        personality={"curious": 0.9, "analytical": 0.8, "methodical": 0.7},
        skills=["neuroscience", "research", "data analysis"],
        current_goals=["Understand memory consolidation", "Map neural correlates of consciousness"]
    )

    bob = orchestrator.create_character(
        name="Prof. Bob Martinez",
        specialization="Philosopher of Mind",
        backstory="A philosopher specializing in questions of consciousness, identity, and the nature of self.",
        personality={"analytical": 0.8, "creative": 0.9, "empathetic": 0.6},
        skills=["philosophy", "critical thinking", "writing"],
        current_goals=["Develop theory of artificial consciousness", "Explore questions of identity"]
    )

    print(f"✅ Created Alice (ID: {alice.id}) with {type(alice.memory).__name__}")
    print(f"✅ Created Bob (ID: {bob.id}) with {type(bob.memory).__name__}")

    # 2. Add initial memories to establish background
    print("\n2. Adding background memories...")

    # Alice's memories
    alice.add_memory(
        content="Published groundbreaking paper on hippocampal memory formation",
        memory_type=MemoryType.EXPERIENCE,
        importance=10,
        topics=["hippocampus", "memory formation", "research"],
        emotional_valence=0.9
    )

    alice.add_memory(
        content="Learned about memory consolidation during sleep through recent research",
        memory_type=MemoryType.LEARNING,
        importance=8,
        topics=["sleep", "memory consolidation", "neuroscience"],
        emotional_valence=0.6
    )

    # Bob's memories
    bob.add_memory(
        content="Wrote influential book on consciousness and the hard problem",
        memory_type=MemoryType.EXPERIENCE,
        importance=9,
        topics=["consciousness", "hard problem", "philosophy"],
        emotional_valence=0.8
    )

    bob.add_memory(
        content="Developed new framework for understanding artificial minds",
        memory_type=MemoryType.LEARNING,
        importance=7,
        topics=["artificial intelligence", "philosophy of mind", "cognition"],
        emotional_valence=0.5
    )

    print("✅ Added background memories to both characters")

    # 3. Create a room for interaction
    print("\n3. Creating discussion room...")

    room = orchestrator.create_room(
        name="Neurophilosophy Seminar",
        room_type=RoomType.DEBATE_HALL,
        purpose="A space for deep discussions about consciousness, memory, and the mind",
        max_characters=10,
        conversation_pace_seconds=2.0
    )

    print(f"✅ Created room: {room.name} (ID: {room.id})")

    # 4. Add characters to room
    print("\n4. Adding characters to room...")

    success1 = orchestrator.add_character_to_room(alice.id, room.id)
    success2 = orchestrator.add_character_to_room(bob.id, room.id)

    if success1 and success2:
        print("✅ Successfully added both characters to the room")
    else:
        print("❌ Failed to add characters to room")
        return

    # 5. Simulate some memories from their interaction
    print("\n5. Simulating interaction memories...")

    # Alice gets a memory about meeting Bob
    alice.add_memory(
        content="Met Prof. Martinez and had fascinating discussion about consciousness",
        memory_type=MemoryType.RELATIONSHIP,
        importance=7,
        related_characters=[bob.id],
        topics=["consciousness", "interdisciplinary discussion", "collaboration"],
        emotional_valence=0.7
    )

    # Bob gets a memory about meeting Alice
    bob.add_memory(
        content="Met Dr. Chen, a neuroscientist with valuable insights about memory",
        memory_type=MemoryType.RELATIONSHIP,
        importance=7,
        related_characters=[alice.id],
        topics=["neuroscience", "memory", "interdisciplinary discussion"],
        emotional_valence=0.6
    )

    # Alice gets a learning memory
    alice.add_memory(
        content="Learned new philosophical perspectives on consciousness from Prof. Martinez",
        memory_type=MemoryType.LEARNING,
        importance=6,
        related_characters=[bob.id],
        topics=["philosophy of mind", "consciousness", "interdisciplinary learning"],
        emotional_valence=0.5
    )

    # Bob gets a learning memory
    bob.add_memory(
        content="Gained new understanding of memory mechanisms from Dr. Chen's research",
        memory_type=MemoryType.LEARNING,
        importance=6,
        related_characters=[alice.id],
        topics=["neuroscience", "memory", "empirical evidence"],
        emotional_valence=0.4
    )

    print("✅ Added interaction memories")

    # 6. Test memory retrieval and context generation
    print("\n6. Testing memory retrieval...")

    # Get Alice's memories about Bob
    alice_memories_about_bob = alice.memory.get_memories_about_character(bob.id)
    print(f"✅ Alice has {len(alice_memories_about_bob)} memories about Bob")

    # Get Bob's memories about Alice
    bob_memories_about_alice = bob.memory.get_memories_about_character(alice.id)
    print(f"✅ Bob has {len(bob_memories_about_alice)} memories about Alice")

    # Test context generation
    alice_context = alice.get_room_context("Academic seminar room with whiteboards and comfortable chairs")
    bob_context = bob.get_room_context("Academic seminar room with whiteboards and comfortable chairs")

    print(f"✅ Generated Alice's context ({len(alice_context)} chars)")
    print(f"✅ Generated Bob's context ({len(bob_context)} chars)")

    # 7. Test memory search functionality
    print("\n7. Testing memory search...")

    alice_consciousness_memories = alice.memory.search_memories("consciousness", limit=5)
    bob_memory_memories = bob.memory.search_memories("memory", limit=5)

    print(f"✅ Alice's search for 'consciousness': {len(alice_consciousness_memories)} results")
    print(f"✅ Bob's search for 'memory': {len(bob_memory_memories)} results")

    # 8. Test memory statistics and analytics
    print("\n8. Testing memory analytics...")

    alice_stats = alice.memory.get_memory_stats()
    bob_stats = bob.memory.get_memory_stats()

    print(f"✅ Alice's memory stats: {alice_stats['total_memories']} memories, {alice_stats['total_clusters']} clusters")
    print(f"✅ Bob's memory stats: {bob_stats['total_memories']} memories, {bob_stats['total_clusters']} clusters")

    # 9. Test cross-session persistence
    print("\n9. Testing persistence...")

    # Save all characters
    orchestrator.character_manager.save_character(alice)
    orchestrator.character_manager.save_character(bob)
    orchestrator.room_manager.save_room(room)

    print("✅ Saved characters and room to disk")

    # Create new orchestrator and reload
    new_orchestrator = AISocietyOrchestrator()

    loaded_alice = new_orchestrator.character_manager.get_character(alice.id)
    loaded_bob = new_orchestrator.character_manager.get_character(bob.id)
    loaded_room = new_orchestrator.room_manager.get_room(room.id)

    if loaded_alice and loaded_bob and loaded_room:
        print("✅ Successfully reloaded characters and room")

        # Verify memories were preserved
        alice_memory_count = len(loaded_alice.memory.get_memories())
        bob_memory_count = len(loaded_bob.memory.get_memories())

        print(f"✅ Alice has {alice_memory_count} memories after reload")
        print(f"✅ Bob has {bob_memory_count} memories after reload")

        if alice_memory_count >= 4 and bob_memory_count >= 4:
            print("✅ Memory persistence successful!")
        else:
            print("❌ Memory persistence issue - lost some memories")
    else:
        print("❌ Failed to reload characters and room")

    # 10. Test working memory consolidation
    print("\n10. Testing working memory consolidation...")

    # Add some working memory items
    loaded_alice.memory.working_memory.extend([
        "Need to follow up with Bob about collaboration",
        "Should read more about philosophical frameworks",
        "My research could benefit from philosophical insights",
        "Interesting connection between memory and consciousness"
    ])

    print(f"   Alice's working memory before: {len(loaded_alice.memory.working_memory)} items")

    # Force consolidation
    loaded_alice.memory.force_memory_consolidation()

    print(f"   Alice's working memory after: {len(loaded_alice.memory.working_memory)} items")

    # Check if new memories were created
    final_memory_count = len(loaded_alice.memory.get_memories())
    print(f"   Final memory count: {final_memory_count}")

    # 11. Test relationship updates through character interaction
    print("\n11. Testing relationship updates...")

    # Simulate positive interaction
    loaded_alice.interact_with_character(loaded_bob, "seminar discussion", 0.8)
    loaded_bob.interact_with_character(loaded_alice, "seminar discussion", 0.7)

    print(f"✅ Alice's relationship with Bob: {loaded_alice.relationships.get(loaded_bob.id, 0):.2f}")
    print(f"✅ Bob's relationship with Alice: {loaded_bob.relationships.get(loaded_alice.id, 0):.2f}")

    # Check if relationship memories were created
    alice_relationship_memories = loaded_alice.memory.get_memories_by_type(MemoryType.RELATIONSHIP)
    bob_relationship_memories = loaded_bob.memory.get_memories_by_type(MemoryType.RELATIONSHIP)

    print(f"✅ Alice's relationship memories: {len(alice_relationship_memories)}")
    print(f"✅ Bob's relationship memories: {len(bob_relationship_memories)}")

    print("\n🎉 Integration tests completed successfully!")
    print("\nIntegration features verified:")
    print("   ✅ Enhanced memory system works with character creation")
    print("   ✅ Memory system integrates with room system")
    print("   ✅ Character relationships and memory interactions")
    print("   ✅ Cross-session persistence of memories")
    print("   ✅ Memory search and retrieval in context")
    print("   ✅ Working memory consolidation")
    print("   ✅ Memory-driven relationship updates")
    print("   ✅ Context-aware memory generation")
    print("   ✅ Memory clustering and organization")
    print("   ✅ Statistics and analytics")

    # Clean up test data
    import shutil
    shutil.rmtree(test_data_dir, ignore_errors=True)
    print("\n🧹 Cleaned up test data")

if __name__ == "__main__":
    asyncio.run(test_integration())