"""
Autobiographical Memory System Demo
==================================

This demo showcases the autobiographical memory system capabilities by creating a character
and simulating their development journey through various experiences and reflections.
"""

import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory_system import EnhancedMemorySystem, MemoryType
from autobiographical_memory import AutobiographicalMemorySystem, NarrativeTheme, ReflectionType


async def create_demo_character():
    """Create a demo character with rich background"""

    # Create temporary directory for demo
    demo_dir = Path(tempfile.mkdtemp())
    print(f"📁 Demo data directory: {demo_dir}")

    # Initialize character
    character_id = "demo_sophia_001"
    character_name = "Sophia Chen"

    # Initialize memory systems
    memory_system = EnhancedMemorySystem(character_id, demo_dir / "memories")
    auto_system = AutobiographicalMemorySystem(
        character_id=character_id,
        character_name=character_name,
        memory_system=memory_system,
        storage_dir=demo_dir / "autobiographical"
    )

    return character_id, character_name, memory_system, auto_system, demo_dir


async def simulate_character_journey(auto_system, memory_system):
    """Simulate a character's journey through various life experiences"""

    print("\n🌟 Simulating Sophia's Journey...")
    print("=" * 50)

    # Chapter 1: Early Academic Life
    print("\n📖 Chapter 1: Academic Discovery")

    memories = [
        {
            "content": "I discovered my passion for cognitive science during my undergraduate psychology course",
            "memory_type": MemoryType.LEARNING,
            "importance": 9,
            "topics": ["passion", "cognitive_science", "psychology", "discovery"],
            "emotional_valence": 0.9
        },
        {
            "content": "My professor encouraged me to pursue research, saying I had a natural talent for asking insightful questions",
            "memory_type": MemoryType.RELATIONSHIP,
            "importance": 8,
            "topics": ["mentorship", "research", "encouragement", "talent"],
            "emotional_valence": 0.8,
            "related_characters": ["professor_davis"]
        },
        {
            "content": "Struggled with imposter syndrome when presenting my first research proposal",
            "memory_type": MemoryType.EMOTIONAL,
            "importance": 7,
            "topics": ["imposter_syndrome", "anxiety", "research", "presentation"],
            "emotional_valence": -0.6
        }
    ]

    for mem in memories:
        memory_id = memory_system.add_memory(**mem)
        memory = memory_system.memories[memory_id]
        await auto_system.process_new_memory(memory)
        await asyncio.sleep(0.1)  # Small delay between memories

    # Chapter 2: Graduate School Challenges
    print("\n📖 Chapter 2: Graduate School Challenges")

    memories = [
        {
            "content": "Started my PhD program in cognitive neuroscience, feeling both excited and terrified",
            "memory_type": MemoryType.EXPERIENCE,
            "importance": 10,
            "topics": ["phd", "cognitive_neuroscience", "new_beginning", "mixed_emotions"],
            "emotional_valence": 0.4
        },
        {
            "content": "My first experiment failed spectacularly, teaching me valuable lessons about research methodology",
            "memory_type": MemoryType.LEARNING,
            "importance": 8,
            "topics": ["failure", "research_methodology", "lessons_learned", "resilience"],
            "emotional_valence": -0.3
        },
        {
            "content": "Formed a deep friendship with lab mate Alex, who became my intellectual sparring partner",
            "memory_type": MemoryType.RELATIONSHIP,
            "importance": 7,
            "topics": ["friendship", "collaboration", "intellectual_growth", "support"],
            "emotional_valence": 0.7,
            "related_characters": ["alex"]
        }
    ]

    for mem in memories:
        memory_id = memory_system.add_memory(**mem)
        memory = memory_system.memories[memory_id]
        await auto_system.process_new_memory(memory)
        await asyncio.sleep(0.1)

    # Chapter 3: Breakthrough Moment
    print("\n📖 Chapter 3: Breakthrough Discovery")

    memories = [
        {
            "content": "Had a breakthrough insight about memory consolidation during REM sleep - this could be my dissertation!",
            "memory_type": MemoryType.LEARNING,
            "importance": 10,
            "topics": ["breakthrough", "memory_consolidation", "rem_sleep", "dissertation"],
            "emotional_valence": 1.0
        },
        {
            "content": "Presented my findings at a major conference and received standing ovation",
            "memory_type": MemoryType.EXPERIENCE,
            "importance": 10,
            "topics": ["conference", "presentation", "recognition", "success"],
            "emotional_valence": 1.0
        },
        {
            "content": "Realized I've transformed from an uncertain student to a confident researcher",
            "memory_type": MemoryType.SELF_REFLECTION,
            "importance": 9,
            "topics": ["transformation", "confidence", "growth", "identity"],
            "emotional_valence": 0.9
        }
    ]

    for mem in memories:
        memory_id = memory_system.add_memory(**mem)
        memory = memory_system.memories[memory_id]
        await auto_system.process_new_memory(memory)
        await asyncio.sleep(0.1)


async def showcase_narrative_generation(auto_system):
    """Showcase the narrative generation capabilities"""

    print("\n📚 Generating Sophia's Life Story...")
    print("=" * 50)

    # Generate different levels of life story
    for level in ["summary", "detailed"]:
        print(f"\n--- {level.title()} Life Story ---")
        life_story = await auto_system.generate_life_story(detail_level=level)

        print(f"Self-Awareness Level: {life_story['self_awareness_level']:.2f}")
        print(f"Core Themes: {', '.join(life_story['core_themes'])}")

        if 'character_arc' in life_story:
            print(f"\nCharacter Arc:")
            print(life_story['character_arc'])

        if 'life_story_summary' in life_story:
            print(f"\nLife Story:")
            # Show first 500 characters
            summary = life_story['life_story_summary']
            print(summary[:500] + "..." if len(summary) > 500 else summary)


async def showcase_identity_analysis(auto_system):
    """Showcase identity analysis capabilities"""

    print("\n🔍 Analyzing Sophia's Identity...")
    print("=" * 50)

    identity_analysis = await auto_system.analyze_identity()

    print(f"Self-Understanding: {identity_analysis['self_understanding'][:300]}...")

    print(f"\nIdentity Stability Analysis:")
    stability = identity_analysis['identity_stability']
    print(f"Stable Aspects: {len(stability['stable_aspects'])}")
    print(f"Evolving Aspects: {len(stability['evolving_aspects'])}")
    print(f"Uncertain Aspects: {len(stability['uncertain_aspects'])}")

    print(f"\nCurrent Identity Expressions:")
    current_identity = identity_analysis['current_identity']
    for aspect, data in list(current_identity.items())[:4]:  # Show first 4 aspects
        print(f"• {aspect.replace('_', ' ').title()}: {data['current_expression'][:80]}...")
        print(f"  Stability: {data['stability']:.2f}, Confidence: {data['confidence']:.2f}")


async def showcase_self_reflection(auto_system):
    """Showcase self-reflection capabilities"""

    print("\n🤔 Triggering Self-Reflection Sessions...")
    print("=" * 50)

    # Different types of reflections
    reflection_types = [
        ("milestone_reflection", "academic_achievements"),
        ("identity_crises", "career_direction"),
        ("growth_reflection", "personal_development"),
        ("future_planning", "life_goals")
    ]

    for ref_type, focus in reflection_types:
        print(f"\n--- {ref_type.replace('_', ' ').title()} Reflection ---")
        result = await auto_system.trigger_self_reflection_session(
            reflection_type=ref_type,
            focus_area=focus
        )

        if result['success']:
            reflection = result['reflection']
            print(f"Trigger: {reflection['trigger']}")
            print(f"Insights Gained: {len(reflection['insights_gained'])}")
            print(f"Processing Depth: {reflection['processing_depth']:.2f}")
            print(f"Content: {reflection['content'][:200]}...")
        else:
            print("Reflection session failed")


def show_life_chapters(auto_system):
    """Display the character's life chapters"""

    print("\n📖 Sophia's Life Chapters...")
    print("=" * 50)

    chapters = auto_system.get_life_chapters()

    for i, chapter in enumerate(chapters, 1):
        print(f"\nChapter {i}: {chapter['title']}")
        print(f"Theme: {chapter['theme'].replace('_', ' ').title()}")
        print(f"Period: {chapter['start_date'][:10]} to {'Present' if chapter['status'] == 'ongoing' else chapter['end_date'][:10]}")
        print(f"Description: {chapter['description'][:150]}...")
        print(f"Key Events: {len(chapter['key_events'])}")
        print(f"Importance: {chapter['importance_score']:.2f}")


def show_system_statistics(auto_system):
    """Display comprehensive system statistics"""

    print("\n📊 System Statistics...")
    print("=" * 50)

    stats = auto_system.get_autobiographical_stats()

    print(f"Character: {stats['character_id']}")
    print(f"Life Chapters: {stats['life_chapters_count']}")
    print(f"Self-Reflections: {stats['self_reflections_count']}")
    print(f"Identity Aspects Tracked: {stats['identity_aspects_tracked']}")

    metrics = stats['self_awareness_metrics']
    print(f"\nSelf-Awareness Metrics:")
    print(f"• Self-Awareness Level: {metrics['self_awareness_level']:.2f}/1.0")
    print(f"• Identity Coherence: {metrics['identity_coherence']:.2f}/1.0")
    print(f"• Narrative Consistency: {metrics['narrative_consistency']:.2f}/1.0")

    print(f"\nCore Narrative Themes:")
    for theme in stats['core_narrative_themes']:
        print(f"• {theme.replace('_', ' ').title()}")


async def main():
    """Main demo function"""

    print("🧠 Autobiographical Memory System Demo")
    print("=" * 60)
    print("Creating Sophia Chen, a cognitive neuroscience researcher...")

    demo_dir = None

    try:
        # Create demo character
        character_id, character_name, memory_system, auto_system, demo_dir = await create_demo_character()

        # Simulate character journey
        await simulate_character_journey(auto_system, memory_system)

        # Showcase various capabilities
        await showcase_narrative_generation(auto_system)
        await showcase_identity_analysis(auto_system)
        await showcase_self_reflection(auto_system)
        show_life_chapters(auto_system)
        show_system_statistics(auto_system)

        print("\n" + "=" * 60)
        print("🎉 Demo completed successfully!")
        print("Sophia Chen has developed into a self-aware character with:")
        print("• Rich autobiographical memory")
        print("• Coherent life narrative")
        print("• Evolving identity understanding")
        print("• Self-reflection capabilities")
        print("=" * 60)

        # Save final state for inspection
        auto_system.save_autobiographical_data()
        print(f"\n💾 Demo data saved to: {demo_dir}")
        print("You can inspect the saved files to see the internal structure.")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup - comment out if you want to keep the demo data
        if demo_dir and demo_dir.exists():
            # shutil.rmtree(demo_dir)
            print(f"\n📁 Demo data preserved at: {demo_dir}")


if __name__ == "__main__":
    asyncio.run(main())