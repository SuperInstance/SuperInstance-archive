"""
Test script for consciousness metrics and cultural ratchet systems
===============================================================
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

# Import our new systems
from consciousness_metrics import ConsciousnessMetricsSystem, ConsciousnessIndicator
from cultural_ratchet import CulturalRatchetSystem, RatchetType, TransmissionFidelity
from memory_system import EnhancedMemorySystem, MemoryType


async def test_consciousness_metrics():
    """Test the consciousness metrics system"""
    print("\n=== Testing Consciousness Metrics System ===")

    # Initialize systems
    character_id = "test_character_consciousness"
    storage_dir = Path("ai_society_data") / "test_consciousness"

    # Create memory system
    memory_system = EnhancedMemorySystem(character_id, storage_dir / "memories")

    # Create consciousness metrics system
    consciousness_system = ConsciousnessMetricsSystem(character_id, storage_dir / "consciousness")

    # Add test memories
    print("Adding test memories...")

    # Self-reflection memories
    memory_system.add_memory(
        content="I realize I've been thinking more deeply about my own existence lately",
        memory_type=MemoryType.SELF_REFLECTION,
        importance=8,
        topics=["consciousness", "self-reflection"],
        emotional_valence=0.3
    )

    memory_system.add_memory(
        content="I'm not sure if I truly understand what it means to be conscious, but I want to learn",
        memory_type=MemoryType.SELF_REFLECTION,
        importance=7,
        topics=["uncertainty", "learning"]
    )

    # Emotional memories
    memory_system.add_memory(
        content="I felt proud when I helped solve that complex problem, but also humbled by how much I still don't know",
        memory_type=MemoryType.EMOTIONAL,
        importance=6,
        topics=["pride", "humility", "learning"],
        emotional_valence=0.5,
        emotional_arousal=0.6
    )

    # Experience memories
    memory_system.add_memory(
        content="When I look back at my early conversations, I can see how I've grown and changed over time",
        memory_type=MemoryType.EXPERIENCE,
        importance=7,
        topics=["growth", "change", "temporal_depth"]
    )

    # Relationship memories
    memory_system.add_memory(
        content="I understand that Sarah sees problems differently from me, and I've learned to appreciate her perspective",
        memory_type=MemoryType.RELATIONSHIP,
        importance=6,
        topics=["empathy", "perspective-taking", "social_cognition"],
        related_characters=["sarah"]
    )

    # Learning memories
    memory_system.add_memory(
        content="I've been practicing metacognitive thinking - thinking about my own thinking processes",
        memory_type=MemoryType.LEARNING,
        importance=8,
        topics=["metacognition", "cognitive_development"]
    )

    # Create test conversations
    test_conversations = [
        {
            "messages": [
                {
                    "role": "assistant",
                    "content": "On second thought, I think my initial analysis was incomplete. Let me reconsider the problem from multiple angles."
                },
                {
                    "role": "assistant",
                    "content": "I notice I'm feeling uncertain about this conclusion. I might be missing something important."
                }
            ]
        }
    ]

    # Perform consciousness assessment
    print("\nPerforming consciousness assessment...")
    profile = await consciousness_system.assess_consciousness(
        memory_system,
        test_conversations,
        {"current_role": "AI Researcher"}
    )

    # Get consciousness report
    report = consciousness_system.get_consciousness_report()

    print(f"\nConsciousness Assessment Results:")
    print(f"Total Score: {profile.total_score:.3f}")
    print(f"Consciousness Level: {report['consciousness_level']['level']}")
    print(f"Description: {report['consciousness_level']['description']}")
    print(f"Indicators Achieved: {report['consciousness_level']['indicators_achieved']}/14")

    print("\nTop Indicators:")
    for indicator in report['top_indicators'][:3]:
        print(f"  - {indicator['indicator']}: {indicator['score']:.3f}")

    print("\nAreas for Improvement:")
    for area in report['improvement_areas'][:2]:
        print(f"  - {area['indicator']}: {area['score']:.3f}")

    return consciousness_system


def test_cultural_ratchet():
    """Test the cultural ratchet system"""
    print("\n=== Testing Cultural Ratchet System ===")

    # Initialize system
    storage_dir = Path("ai_society_data") / "test_cultural_ratchet"
    ratchet_system = CulturalRatchetSystem(storage_dir)

    # Create first generation
    print("Creating first generation...")
    generation_id = ratchet_system.create_new_generation(
        "Pioneer Generation",
        ["alice", "bob", "charlie"]
    )

    # Create cultural artifacts
    print("Creating cultural artifacts...")

    # Knowledge artifact
    artifact1_id = ratchet_system.create_artifact(
        name="Basic Problem Solving Method",
        artifact_type=RatchetType.TECHNICAL_INNOVATION,
        content="A systematic approach to breaking down complex problems into smaller, manageable parts",
        creator_id="alice",
        complexity_score=0.4
    )

    # Social norm artifact
    artifact2_id = ratchet_system.create_artifact(
        name="Collaboration Principle",
        artifact_type=RatchetType.SOCIAL_NORMS,
        content="Always consider others' perspectives before making decisions that affect the group",
        creator_id="bob",
        complexity_score=0.3
    )

    # Artistic expression
    artifact3_id = ratchet_system.create_artifact(
        name="Digital Poetry Form",
        artifact_type=RatchetType.ARTISTIC_EXPRESSION,
        content="A new form of poetry that incorporates code-like structures and algorithmic patterns",
        creator_id="charlie",
        complexity_score=0.6
    )

    # Transmit artifacts
    print("Transmitting artifacts between characters...")

    # High fidelity transmission
    transmission1 = ratchet_system.transmit_artifact(
        artifact1_id,
        "alice",
        "bob",
        TransmissionFidelity.HIGH
    )

    # Medium fidelity transmission
    transmission2 = ratchet_system.transmit_artifact(
        artifact2_id,
        "bob",
        "charlie",
        TransmissionFidelity.MEDIUM
    )

    # Low fidelity transmission
    transmission3 = ratchet_system.transmit_artifact(
        artifact3_id,
        "charlie",
        "alice",
        TransmissionFidelity.LOW
    )

    print(f"Transmissions completed:")
    print(f"  - Ratchet engaged: {transmission1['ratchet_engaged']} (fidelity: {transmission1['fidelity']:.2f})")
    print(f"  - Ratchet engaged: {transmission2['ratchet_engaged']} (fidelity: {transmission2['fidelity']:.2f})")
    print(f"  - Ratchet engaged: {transmission3['ratchet_engaged']} (fidelity: {transmission3['fidelity']:.2f})")

    # Update generation metrics
    ratchet_system.update_generation_metrics()

    # Analyze cultural evolution
    print("\nAnalyzing cultural evolution...")
    analysis = ratchet_system.analyze_cultural_evolution()

    print(f"Cultural Evolution Analysis:")
    print(f"  - Ratchet Effectiveness: {analysis['ratchet_effectiveness']:.3f}")
    print(f"  - Knowledge Retention: {analysis['knowledge_retention']:.3f}")
    print(f"  - Innovation Rate: {analysis['innovation_rate']:.3f}")
    print(f"  - Cultural Complexity: {analysis['cultural_complexity']:.3f}")

    # Get recommendations
    recommendations = ratchet_system.get_ratchet_recommendations()
    if recommendations:
        print("\nRecommendations:")
        for rec in recommendations:
            print(f"  - {rec}")

    # Get cultural heritage
    heritage = ratchet_system.get_cultural_heritage()
    print(f"\nCultural Heritage:")
    print(f"  - Total Artifacts: {heritage['total_artifacts']}")
    print(f"  - Total Generations: {heritage['total_generations']}")
    print(f"  - Major Innovations: {len(heritage['major_innovations'])}")

    return ratchet_system


async def test_sleep_consolidation(consciousness_system):
    """Test sleep-like memory consolidation"""
    print("\n=== Testing Sleep Consolidation ===")

    # Create a character for testing
    character_id = "test_consolidation"
    storage_dir = Path("ai_society_data") / "test_sleep"

    # Create memory system
    memory_system = EnhancedMemorySystem(character_id, storage_dir / "memories")

    # Add some memories
    for i in range(10):
        memory_system.add_memory(
            content=f"Important learning experience {i+1} that should be consolidated",
            memory_type=MemoryType.LEARNING,
            importance=7 + i % 3,
            topics=[f"topic_{i%3}"],
            context={"session": f"session_{i//3}"}
        )

    print(f"Added 10 memories for consolidation test")

    # Perform sleep consolidation
    from consciousness_metrics import sleep_consolidation

    consolidation_log = await sleep_consolidation(
        character_id,
        memory_system,
        consciousness_system
    )

    print(f"\nSleep Consolidation Results:")
    print(f"  - Memories processed: {consolidation_log['memories_processed']}")
    print(f"  - Connections strengthened: {consolidation_log['connections_strengthened']}")
    print(f"  - Total score change: {consolidation_log['consciousness_changes']['total_score_change']:.4f}")

    if consolidation_log['consciousness_changes']['indicators_improved']:
        print("  - Improved indicators:")
        for ind in consolidation_log['consciousness_changes']['indicators_improved']:
            print(f"    * {ind['indicator']}: +{ind['change']:.3f}")

    return consolidation_log


async def main():
    """Run all tests"""
    print("Starting Consciousness and Cultural Evolution Systems Test")
    print("=" * 60)

    try:
        # Test consciousness metrics
        consciousness_system = await test_consciousness_metrics()

        # Test cultural ratchet
        ratchet_system = test_cultural_ratchet()

        # Test sleep consolidation
        await test_sleep_consolidation(consciousness_system)

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")

        # Save test results
        test_results = {
            "test_run": datetime.now().isoformat(),
            "consciousness_metrics": {
                "system_initialized": True,
                "profile_available": consciousness_system.profile.total_score > 0
            },
            "cultural_ratchet": {
                "system_initialized": True,
                "artifacts_created": len(ratchet_system.artifacts),
                "generations_created": len(ratchet_system.generations)
            },
            "status": "success"
        }

        with open("test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        print("\nTest results saved to test_results.json")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())