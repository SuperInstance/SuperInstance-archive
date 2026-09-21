"""
Test Suite for Autobiographical Memory System
============================================

This test suite validates the autobiographical memory system functionality,
including life narrative generation, identity continuity tracking, and self-reflection mechanics.
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

from memory_system import EnhancedMemorySystem, MemoryType, Memory
from autobiographical_memory import (
    AutobiographicalMemorySystem, NarrativeTheme, IdentityAspect, ReflectionType
)


class TestAutobiographicalMemory:
    """Test class for autobiographical memory system"""

    def __init__(self):
        self.test_dir = None
        self.memory_system = None
        self.auto_system = None
        self.character_id = "test_character_001"
        self.character_name = "Test Character"

    def setup(self):
        """Set up test environment"""
        # Create temporary directory for test data
        self.test_dir = Path(tempfile.mkdtemp())
        print(f"Created test directory: {self.test_dir}")

        # Initialize memory system
        self.memory_system = EnhancedMemorySystem(self.character_id, self.test_dir / "memories")

        # Initialize autobiographical memory system
        self.auto_system = AutobiographicalMemorySystem(
            character_id=self.character_id,
            character_name=self.character_name,
            memory_system=self.memory_system,
            storage_dir=self.test_dir / "autobiographical"
        )

    def cleanup(self):
        """Clean up test environment"""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            print(f"Cleaned up test directory: {self.test_dir}")

    async def test_memory_addition_and_processing(self):
        """Test adding memories and processing them for autobiographical understanding"""
        print("\n=== Testing Memory Addition and Processing ===")

        # Test different types of memories
        test_memories = [
            {
                "content": "I discovered my passion for philosophy while reading Plato's Republic",
                "memory_type": MemoryType.LEARNING,
                "importance": 8,
                "topics": ["philosophy", "passion", "discovery"],
                "emotional_valence": 0.8
            },
            {
                "content": "Had a challenging debate with colleagues about ethics, which made me question my own values",
                "memory_type": MemoryType.RELATIONSHIP,
                "importance": 7,
                "topics": ["debate", "ethics", "values", "challenge"],
                "emotional_valence": -0.2
            },
            {
                "content": "Realized I've grown significantly as a thinker over the past year",
                "memory_type": MemoryType.SELF_REFLECTION,
                "importance": 9,
                "topics": ["growth", "self_awareness", "development"],
                "emotional_valence": 0.9
            },
            {
                "content": "Completed my first major research paper on consciousness studies",
                "memory_type": MemoryType.EXPERIENCE,
                "importance": 10,
                "topics": ["research", "achievement", "consciousness"],
                "emotional_valence": 1.0
            },
            {
                "content": "Felt lonely during the conference but made meaningful connections by the end",
                "memory_type": MemoryType.EMOTIONAL,
                "importance": 6,
                "topics": ["loneliness", "connection", "social"],
                "emotional_valence": 0.3
            }
        ]

        memory_ids = []
        for i, mem_data in enumerate(test_memories):
            # Add some time separation between memories
            if i > 0:
                await asyncio.sleep(0.1)

            memory_id = self.memory_system.add_memory(**mem_data)
            memory_ids.append(memory_id)

            # Process for autobiographical understanding
            memory = self.memory_system.memories[memory_id]
            await self.auto_system.process_new_memory(memory)

            print(f"✓ Added and processed memory {i+1}: {mem_data['content'][:50]}...")

        print(f"✓ Successfully processed {len(memory_ids)} memories")
        return memory_ids

    async def test_life_chapter_creation(self):
        """Test automatic life chapter creation"""
        print("\n=== Testing Life Chapter Creation ===")

        # Add a significant memory that should trigger chapter creation
        significant_memory = self.memory_system.add_memory(
            content="I made a major career change from engineering to philosophy",
            memory_type=MemoryType.EXPERIENCE,
            importance=10,
            topics=["career_change", "philosophy", "transformation"],
            emotional_valence=0.7,
            context={"event_type": "major_life_change"}
        )

        memory = self.memory_system.memories[significant_memory]
        await self.auto_system.process_new_memory(memory)

        # Check if chapters were created
        chapters = list(self.auto_system.life_chapters.values())
        print(f"✓ Created {len(chapters)} life chapters")

        for chapter in chapters:
            print(f"  - Chapter: {chapter.title}")
            print(f"    Theme: {chapter.theme.value}")
            print(f"    Start: {chapter.start_date}")
            print(f"    Description: {chapter.description[:100]}...")

        return chapters

    async def test_identity_continuity_tracking(self):
        """Test identity continuity tracking"""
        print("\n=== Testing Identity Continuity Tracking ===")

        # Get initial identity state
        initial_identity = self.auto_system.identity_continuity.copy()
        print(f"✓ Initial identity aspects: {len(initial_identity)}")

        # Add memories that relate to different identity aspects
        identity_memories = [
            {
                "content": "I am becoming more confident in my professional identity as a philosopher",
                "memory_type": MemoryType.SELF_REFLECTION,
                "importance": 7,
                "topics": ["professional_identity", "confidence", "philosophy"]
            },
            {
                "content": "My core values emphasize truth, wisdom, and compassion",
                "memory_type": MemoryType.SELF_REFLECTION,
                "importance": 8,
                "topics": ["values", "ethics", "core_beliefs"]
            },
            {
                "content": "I've discovered that I'm naturally curious and analytical in my thinking",
                "memory_type": MemoryType.SELF_REFLECTION,
                "importance": 6,
                "topics": ["personality", "curiosity", "analytical_thinking"]
            }
        ]

        for mem_data in identity_memories:
            memory_id = self.memory_system.add_memory(**mem_data)
            memory = self.memory_system.memories[memory_id]
            await self.auto_system.process_new_memory(memory)

        # Check identity updates
        updated_identity = self.auto_system.identity_continuity
        print("✓ Updated identity aspects:")

        for aspect, continuity in updated_identity.items():
            print(f"  - {aspect.value}:")
            print(f"    Core value: {continuity.core_value}")
            print(f"    Current expression: {continuity.current_expression}")
            print(f"    Stability: {continuity.stability_score:.2f}")
            print(f"    Related memories: {len(continuity.related_memories)}")

        return updated_identity

    async def test_self_reflection_mechanics(self):
        """Test self-reflection triggering and processing"""
        print("\n=== Testing Self-Reflection Mechanics ===")

        # Trigger different types of reflections
        reflection_tests = [
            {
                "type": "milestone_reflection",
                "trigger_memory": {
                    "content": "I achieved a major breakthrough in my research on consciousness",
                    "memory_type": MemoryType.EXPERIENCE,
                    "importance": 9,
                    "topics": ["breakthrough", "research", "achievement"],
                    "emotional_valence": 1.0
                }
            },
            {
                "type": "identity_crises",
                "trigger_memory": {
                    "content": "I'm questioning whether I'm truly qualified to be a philosopher",
                    "memory_type": MemoryType.SELF_REFLECTION,
                    "importance": 8,
                    "topics": ["doubt", "qualification", "identity"],
                    "emotional_valence": -0.6
                }
            },
            {
                "type": "growth_reflection",
                "trigger_memory": {
                    "content": "Looking back, I can see how much I've grown as a thinker",
                    "memory_type": MemoryType.SELF_REFLECTION,
                    "importance": 7,
                    "topics": ["growth", "development", "reflection"],
                    "emotional_valence": 0.8
                }
            }
        ]

        for test in reflection_tests:
            # Add trigger memory
            memory_id = self.memory_system.add_memory(**test["trigger_memory"])
            memory = self.memory_system.memories[memory_id]
            await self.auto_system.process_new_memory(memory)

            # Manually trigger reflection for this test
            await self.auto_system._trigger_self_reflection(memory)

            print(f"✓ Triggered {test['type']} reflection")

        # Check reflections
        reflections = list(self.auto_system.self_reflections.values())
        print(f"✓ Created {len(reflections)} self-reflections")

        for reflection in reflections[-3:]:  # Show last 3 reflections
            print(f"  - Reflection type: {reflection.reflection_type.value}")
            print(f"    Trigger: {reflection.trigger}")
            print(f"    Insights: {len(reflection.insights_gained)}")
            print(f"    Impact: {reflection.impact_score:.2f}")
            print(f"    Processing depth: {reflection.processing_depth:.2f}")

        return reflections

    async def test_narrative_generation(self):
        """Test life story and narrative generation"""
        print("\n=== Testing Narrative Generation ===")

        # Generate life story at different detail levels
        detail_levels = ["summary", "detailed", "comprehensive"]

        for level in detail_levels:
            print(f"\n--- Testing {level} life story ---")
            life_story = await self.auto_system.generate_life_story(detail_level=level)

            print(f"✓ Generated {level} life story:")
            print(f"  - Self-awareness level: {life_story.get('self_awareness_level', 0):.2f}")

            if 'life_story_summary' in life_story:
                summary = life_story['life_story_summary']
                print(f"  - Story length: {len(summary)} characters")
                print(f"  - Preview: {summary[:150]}...")

            if 'character_arc' in life_story:
                arc = life_story['character_arc']
                print(f"  - Character arc length: {len(arc)} characters")
                print(f"  - Arc preview: {arc[:150]}...")

            if 'core_themes' in life_story:
                themes = life_story['core_themes']
                print(f"  - Core themes: {themes}")

            if 'chapters' in life_story:
                chapters = life_story['chapters']
                print(f"  - Number of chapters: {len(chapters)}")

        return life_story

    async def test_identity_analysis(self):
        """Test identity analysis functionality"""
        print("\n=== Testing Identity Analysis ===")

        identity_analysis = await self.auto_system.analyze_identity()

        print("✓ Generated identity analysis:")
        print(f"  - Character name: {identity_analysis.get('character_name')}")
        print(f"  - Self-understanding length: {len(identity_analysis.get('self_understanding', ''))}")

        if 'current_identity' in identity_analysis:
            current_identity = identity_analysis['current_identity']
            print(f"  - Identity aspects tracked: {len(current_identity)}")
            for aspect, data in current_identity.items():
                print(f"    - {aspect}: {data.get('current_expression', 'N/A')}")

        if 'identity_stability' in identity_analysis:
            stability = identity_analysis['identity_stability']
            print(f"  - Stable aspects: {stability.get('stable_aspects', [])}")
            print(f"  - Evolving aspects: {stability.get('evolving_aspects', [])}")
            print(f"  - Uncertain aspects: {stability.get('uncertain_aspects', [])}")

        if 'core_values' in identity_analysis:
            core_values = identity_analysis['core_values']
            print(f"  - Core values identified: {len(core_values)}")

        return identity_analysis

    def test_persistence_and_loading(self):
        """Test data persistence and loading"""
        print("\n=== Testing Persistence and Loading ===")

        # Save current data
        self.auto_system.save_autobiographical_data()
        print("✓ Saved autobiographical data")

        # Create new system instance and load data
        new_auto_system = AutobiographicalMemorySystem(
            character_id=self.character_id,
            character_name=self.character_name,
            memory_system=self.memory_system,
            storage_dir=self.test_dir / "autobiographical"
        )

        print("✓ Created new autobiographical system instance")

        # Check if data loaded correctly
        print(f"✓ Loaded {len(new_auto_system.life_chapters)} life chapters")
        print(f"✓ Loaded {len(new_auto_system.self_reflections)} self-reflections")
        print(f"✓ Loaded {len(new_auto_system.identity_continuity)} identity aspects")
        print(f"✓ Self-awareness level: {new_auto_system.self_awareness_level:.2f}")

        # Verify data integrity
        original_chapters = {ch.id: ch.title for ch in self.auto_system.life_chapters.values()}
        loaded_chapters = {ch.id: ch.title for ch in new_auto_system.life_chapters.values()}

        if original_chapters == loaded_chapters:
            print("✓ Chapter data integrity verified")
        else:
            print("✗ Chapter data integrity check failed")

        return new_auto_system

    async def test_api_integration_simulation(self):
        """Simulate API endpoint functionality"""
        print("\n=== Testing API Integration Simulation ===")

        # Simulate GET /characters/{id}/life-story
        life_story = await self.auto_system.generate_life_story(detail_level="detailed")
        api_response_life_story = {
            "character_id": self.character_id,
            "life_story": life_story,
            "generated_at": datetime.now().isoformat()
        }
        print("✓ Simulated GET /life-story endpoint")

        # Simulate GET /characters/{id}/identity-analysis
        identity_analysis = await self.auto_system.analyze_identity()
        api_response_identity = {
            "character_id": self.character_id,
            "identity_analysis": identity_analysis,
            "generated_at": datetime.now().isoformat()
        }
        print("✓ Simulated GET /identity-analysis endpoint")

        # Simulate POST /characters/{id}/self-reflection
        reflection_result = await self.auto_system.trigger_self_reflection_session(
            reflection_type="periodic_review",
            focus_area="personal_growth"
        )
        api_response_reflection = {
            "character_id": self.character_id,
            "reflection_result": reflection_result,
            "triggered_at": datetime.now().isoformat()
        }
        print("✓ Simulated POST /self-reflection endpoint")

        # Simulate GET /characters/{id}/life-chapters
        chapters = self.auto_system.get_life_chapters()
        api_response_chapters = {
            "character_id": self.character_id,
            "life_chapters": chapters,
            "total_chapters": len(chapters),
            "retrieved_at": datetime.now().isoformat()
        }
        print("✓ Simulated GET /life-chapters endpoint")

        # Simulate GET /characters/{id}/autobiographical-stats
        stats = self.auto_system.get_autobiographical_stats()
        api_response_stats = {
            "character_id": self.character_id,
            "autobiographical_stats": stats,
            "retrieved_at": datetime.now().isoformat()
        }
        print("✓ Simulated GET /autobiographical-stats endpoint")

        return {
            "life_story": api_response_life_story,
            "identity_analysis": api_response_identity,
            "reflection": api_response_reflection,
            "chapters": api_response_chapters,
            "stats": api_response_stats
        }

    async def run_all_tests(self):
        """Run all tests"""
        print("🧠 Starting Autobiographical Memory System Tests")
        print("=" * 60)

        try:
            self.setup()

            # Run individual test suites
            await self.test_memory_addition_and_processing()
            await self.test_life_chapter_creation()
            await self.test_identity_continuity_tracking()
            await self.test_self_reflection_mechanics()
            await self.test_narrative_generation()
            await self.test_identity_analysis()
            self.test_persistence_and_loading()
            await self.test_api_integration_simulation()

            print("\n" + "=" * 60)
            print("🎉 All tests completed successfully!")
            print("=" * 60)

            # Print final statistics
            print(f"\n📊 Final System Statistics:")
            print(f"  - Total memories: {len(self.memory_system.memories)}")
            print(f"  - Life chapters: {len(self.auto_system.life_chapters)}")
            print(f"  - Self-reflections: {len(self.auto_system.self_reflections)}")
            print(f"  - Identity aspects: {len(self.auto_system.identity_continuity)}")
            print(f"  - Self-awareness level: {self.auto_system.self_awareness_level:.2f}")
            print(f"  - Identity coherence: {self.auto_system.identity_coherence:.2f}")
            print(f"  - Narrative consistency: {self.auto_system.narrative_consistency:.2f}")

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()


async def main():
    """Main test runner"""
    tester = TestAutobiographicalMemory()
    await tester.run_all_tests()


if __name__ == "__main__":
    # Run the tests
    asyncio.run(main())