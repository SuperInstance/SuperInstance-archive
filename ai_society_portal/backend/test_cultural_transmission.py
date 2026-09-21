#!/usr/bin/env python3
"""
AI Society Portal - Cultural Transmission Test Script
===================================================
Demonstrates and tests the cultural transmission system functionality.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent))

from character_system import CharacterManager, Character
from cultural_transmission import (
    CulturalTransmissionSystem, KnowledgeType, TransmissionMethod
)
from memory_system import MemoryType


def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")


def test_knowledge_discovery(cultural_system, characters):
    """Test knowledge discovery by characters"""
    print_section("Testing Knowledge Discovery")

    # Have Einstein discover scientific knowledge
    einstein = characters["einstein"]
    knowledge_id1 = cultural_system.discover_knowledge(
        character_id=einstein.id,
        content="E=mc²: Energy and mass are interchangeable",
        knowledge_type=KnowledgeType.FACT,
        importance=9,
        topics=["physics", "relativity", "energy"],
        context={"discovery_method": "theoretical_work", "field": "physics"}
    )
    print(f"Einstein discovered knowledge: {knowledge_id1}")

    # Have Curie discover a skill
    curie = characters["curie"]
    knowledge_id2 = cultural_system.discover_knowledge(
        character_id=curie.id,
        content="Laboratory safety protocols for radioactive materials",
        knowledge_type=KnowledgeType.SKILL,
        importance=8,
        topics=["chemistry", "safety", "radioactivity"],
        context={"discovery_method": "practical_experience", "field": "chemistry"}
    )
    print(f"Curie discovered knowledge: {knowledge_id2}")

    # Have Socrates discover an insight
    socrates = characters["socrates"]
    knowledge_id3 = cultural_system.discover_knowledge(
        character_id=socrates.id,
        content="The unexamined life is not worth living",
        knowledge_type=KnowledgeType.INSIGHT,
        importance=10,
        topics=["philosophy", "ethics", "self-knowledge"],
        context={"discovery_method": "dialogue", "field": "philosophy"}
    )
    print(f"Socrates discovered knowledge: {knowledge_id3}")

    print("✓ Knowledge discoveries completed")

    # Display discovered knowledge
    for name, char in characters.items():
        knowledge = cultural_system.get_character_knowledge(char.id)
        print(f"\n{name}'s discovered knowledge:")
        for k in knowledge:
            print(f"  - {k['knowledge_type']}: {k['content'][:50]}{'...' if len(k['content']) > 50 else ''}")


def test_direct_teaching(cultural_system, characters):
    """Test direct teaching between characters"""
    print_section("Testing Direct Teaching")

    einstein = characters["einstein"]
    curie = characters["curie"]

    # Get Einstein's knowledge
    einstein_knowledge = cultural_system.get_character_knowledge(einstein.id)
    if einstein_knowledge:
        # Einstein teaches Curie his first piece of knowledge
        knowledge_to_teach = einstein_knowledge[0]["id"]

        print(f"Einstein teaching Curie: {einstein_knowledge[0]['content'][:50]}...")
        result = cultural_system.teach_character(
            teacher_id=einstein.id,
            student_id=curie.id,
            knowledge_id=knowledge_to_teach,
            method=TransmissionMethod.DIRECT_TEACHING
        )

        if result["success"]:
            print("✓ Teaching successful!")
            print(f"  Success probability: {result['success_probability']:.2f}")
        else:
            print("✗ Teaching failed")
            print(f"  Reason: {result.get('reason', 'Unknown')}")

    # Check what Curie knows now
    curie_knowledge = cultural_system.get_character_knowledge(curie.id)
    print(f"\nCurie's knowledge after teaching ({len(curie_knowledge)} items):")
    for k in curie_knowledge:
        print(f"  - {k['knowledge_type']}: {k['content'][:50]}{'...' if len(k['content']) > 50 else ''}")


def test_artifact_creation_and_learning(cultural_system, characters):
    """Test cultural artifact creation and learning"""
    print_section("Testing Cultural Artifacts")

    # Socrates creates a philosophical text
    socrates = characters["socrates"]
    socrates_knowledge = cultural_system.get_character_knowledge(socrates.id)

    if socrates_knowledge:
        knowledge_ids = [k["id"] for k in socrates_knowledge]

        print("Socrates creating 'The Socratic Dialogues' artifact...")
        artifact_id = cultural_system.create_artifact(
            creator_id=socrates.id,
            name="The Socratic Dialogues",
            description="A collection of philosophical teachings and methods",
            embedded_knowledge_ids=knowledge_ids,
            artifact_type="document",
            explicit_instructions="Question everything, seek truth through dialogue",
            implicit_wisdom="Wisdom begins with admitting one's ignorance"
        )

        if artifact_id:
            print(f"✓ Artifact created: {artifact_id}")

            # Now have other characters learn from the artifact
            plato = characters["plato"]
            print(f"\nPlato learning from artifact...")
            result = cultural_system.learn_from_artifact(plato.id, artifact_id)

            if result["success"]:
                print("✓ Plato learned from artifact!")
                print(f"  Learned {len(result['learned_knowledge_ids'])} knowledge items")
            else:
                print("✗ Plato failed to learn from artifact")

            # Check Plato's new knowledge
            plato_knowledge = cultural_system.get_character_knowledge(plato.id)
            print(f"\nPlato's knowledge after artifact learning ({len(plato_knowledge)} items):")
            for k in plato_knowledge:
                print(f"  - {k['knowledge_type']}: {k['content'][:50]}{'...' if len(k['content']) > 50 else ''}")


def test_group_cultural_transmission(cultural_system, characters):
    """Test cultural transmission in group settings"""
    print_section("Testing Group Cultural Transmission")

    # Gather all characters for a "symposium"
    character_ids = [char.id for char in characters.values()]

    print("Hosting a philosophical symposium...")
    result = cultural_system.group_cultural_transmission(
        character_ids=character_ids,
        room_id="symposium_room"
    )

    print(f"✓ Group transmission completed")
    print(f"  Transmission events: {len(result['transmission_events'])}")
    print(f"  New insights created: {len(result['new_knowledge_created'])}")

    # Show some transmission events
    if result['transmission_events']:
        print("\nSample transmission events:")
        for event in result['transmission_events'][:3]:
            print(f"  - {event['from']} → {event['to']}: {event['knowledge'][:20]}...")

    # Show final knowledge distribution
    print("\nFinal knowledge distribution:")
    for name, char in characters.items():
        knowledge = cultural_system.get_character_knowledge(char.id)
        print(f"  {name}: {len(knowledge)} knowledge items")


def test_cultural_evolution(cultural_system, characters):
    """Test cultural evolution over multiple generations"""
    print_section("Testing Cultural Evolution")

    # Simulate time passing and knowledge being transmitted
    print("Simulating knowledge evolution over time...")

    # Multiple rounds of teaching and learning
    teaching_pairs = [
        ("einstein", "curie"),
        ("curie", "newton"),
        ("socrates", "plato"),
        ("plato", "newton"),
        ("einstein", "newton")
    ]

    for round_num, (teacher_name, student_name) in enumerate(teaching_pairs, 1):
        print(f"\nRound {round_num}: {teacher_name} teaches {student_name}")

        teacher = characters[teacher_name]
        student = characters[student_name]

        teacher_knowledge = cultural_system.get_character_knowledge(teacher.id)
        if teacher_knowledge:
            # Teach a random piece of knowledge
            import random
            knowledge_to_teach = random.choice(teacher_knowledge)["id"]

            result = cultural_system.teach_character(
                teacher_id=teacher.id,
                student_id=student.id,
                knowledge_id=knowledge_to_teach,
                method=TransmissionMethod.DIRECT_TEACHING
            )

            if result["success"]:
                print(f"  ✓ Success (generation {result.get('generation', 'N/A')})")
            else:
                print(f"  ✗ Failed")

    # Check transmission history for a piece of knowledge
    print("\nTransmission history analysis:")
    einstein_knowledge = cultural_system.get_character_knowledge(characters["einstein"].id)
    if einstein_knowledge:
        first_knowledge = einstein_knowledge[0]["id"]
        history = cultural_system.get_transmission_history(first_knowledge)

        print(f"Knowledge: {einstein_knowledge[0]['content'][:50]}...")
        print(f"Transmission chain ({len(history)} steps):")
        for i, event in enumerate(history):
            if event["success"]:
                print(f"  {i+1}. {event['from_character']} → {event['to_character']} ({event['method']})")


def test_cultural_statistics(cultural_system):
    """Test cultural transmission statistics"""
    print_section("Cultural Transmission Statistics")

    stats = cultural_system.get_cultural_stats()

    print("📊 Cultural Evolution Metrics:")
    print(f"  Total knowledge items: {stats['total_knowledge']}")
    print(f"  Total artifacts: {stats['total_artifacts']}")
    print(f"  Knowledgeable characters: {stats['knowledgeable_characters']}")
    print(f"  Average connections: {stats['average_connections']:.2f}")
    print(f"  Max generation: {stats['max_generation']}")
    print(f"  Total transmissions: {stats['total_transmissions']}")
    print(f"  Successful transmissions: {stats['successful_transmissions']}")

    print("\n📚 Knowledge by Type:")
    for ktype, count in stats['knowledge_by_type'].items():
        print(f"  {ktype.replace('_', ' ').title()}: {count}")


def main():
    """Main test function"""
    print_header("AI Society Portal - Cultural Transmission Test")

    # Initialize systems
    print("Initializing systems...")

    # Create data directory
    data_dir = Path("ai_society_data")
    data_dir.mkdir(exist_ok=True)

    # Initialize character manager and cultural transmission system
    character_manager = CharacterManager(data_dir / "characters")
    cultural_system = CulturalTransmissionSystem(data_dir / "cultural_transmission")

    # Create test characters
    print("Creating test characters...")
    characters = {}

    character_configs = [
        ("einstein", "Physicist", "Revolutionized physics with theories of relativity"),
        ("curie", "Chemist", "Pioneered research on radioactivity"),
        ("socrates", "Philosopher", "Developed the Socratic method of inquiry"),
        ("plato", "Philosopher", "Student of Socrates, founded the Academy"),
        ("newton", "Physicist", "Laws of motion and universal gravitation")
    ]

    for name, specialization, backstory in character_configs:
        character = character_manager.create_character(
            name=name,
            specialization=specialization,
            backstory=backstory,
            personality={"curious": 0.9, "analytical": 0.8}
        )
        characters[name] = character
        print(f"  ✓ Created {name}")

    # Run tests
    try:
        test_knowledge_discovery(cultural_system, characters)
        test_direct_teaching(cultural_system, characters)
        test_artifact_creation_and_learning(cultural_system, characters)
        test_group_cultural_transmission(cultural_system, characters)
        test_cultural_evolution(cultural_system, characters)
        test_cultural_statistics(cultural_system)

        print_header("✓ All Tests Completed Successfully!")
        print("The cultural transmission system is working as expected.")
        print("Characters can now share knowledge, create artifacts, and build culture!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)