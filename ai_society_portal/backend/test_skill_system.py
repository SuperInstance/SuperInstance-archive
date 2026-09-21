"""
Test Script for Skill System
============================
Demonstrates the skill acquisition and practice system with example characters.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

# Import our systems
from skill_system import SkillSystem, SkillType, SkillCategory, SkillLevel, recommend_starter_skills
from character_system import CharacterManager


async def test_skill_system():
    """Test the skill system with example characters"""
    print("🎯 Testing AI Character Skill System")
    print("=" * 50)

    # Initialize systems
    skill_system = SkillSystem(Path("test_data/skills"))
    character_manager = CharacterManager(Path("test_data/characters"))

    # Create test characters
    print("\n📝 Creating test characters...")

    # Scientist character
    scientist = character_manager.create_character(
        name="Dr. Elena Chen",
        specialization="Quantum Physicist",
        backstory="A brilliant researcher exploring the mysteries of quantum mechanics",
        personality={"curious": 0.9, "analytical": 0.8, "methodical": 0.7}
    )

    # Artist character
    artist = character_manager.create_character(
        name="Marcus Rivera",
        specialization="Digital Artist",
        backstory="Creates stunning digital art that blends technology and emotion",
        personality={"creative": 0.9, "empathetic": 0.7, "playful": 0.6}
    )

    # Programmer character
    programmer = character_manager.create_character(
        name="Sarah Kim",
        specialization="Software Engineer",
        backstory="Builds elegant solutions to complex problems",
        personality={"analytical": 0.8, "logical": 0.9, "methodical": 0.8}
    )

    characters = [scientist, artist, programmer]
    print(f"✅ Created {len(characters)} characters")

    # Add starter skills based on specializations
    print("\n🎓 Adding starter skills...")

    for character in characters:
        recommended = recommend_starter_skills(character.specialization)
        print(f"\n{character.name} ({character.specialization}):")

        for skill_type in recommended:
            skill = skill_system.add_skill(character.id, skill_type)
            print(f"  + Added {skill_type.value} (Level: {skill.skill_level.value})")

    # Test individual practice sessions
    print("\n💪 Testing individual practice sessions...")

    # Scientist practices research
    print(f"\n{scientist.name} practices Research:")
    result = skill_system.practice_skill(
        character_id=scientist.id,
        skill_type=SkillType.RESEARCH,
        difficulty=0.3,  # Start with easier difficulty
        duration_minutes=30
    )
    print(f"  XP Gained: {result['session_results']['total_xp_gained']:.2f}")
    print(f"  Success Rate: {result['session_results']['session_success_rate']:.2%}")
    print(f"  New Level: {result['skill_after_practice']['skill_level']}")

    # Artist practices creative thinking
    print(f"\n{artist.name} practices Creative Thinking:")
    result = skill_system.practice_skill(
        character_id=artist.id,
        skill_type=SkillType.INNOVATION,
        difficulty=0.5,
        duration_minutes=45
    )
    print(f"  XP Gained: {result['session_results']['total_xp_gained']:.2f}")
    print(f"  Success Rate: {result['session_results']['session_success_rate']:.2%}")
    if result['new_badges']:
        print(f"  🏆 New Badge: {result['new_badges'][0]['badge_name']}")

    # Programmer practices programming
    print(f"\n{programmer.name} practices Programming:")
    result = skill_system.practice_skill(
        character_id=programmer.id,
        skill_type=SkillType.PROGRAMMING,
        difficulty=0.4,
        duration_minutes=60
    )
    print(f"  XP Gained: {result['session_results']['total_xp_gained']:.2f}")
    print(f"  Success Rate: {result['session_results']['session_success_rate']:.2%}")

    # Test skill progression over multiple sessions
    print("\n📈 Testing skill progression...")

    print(f"\n{scientist.name} practicing Analytical Thinking (multiple sessions):")
    skill_system.add_skill(scientist.id, SkillType.ANALYTICAL_THINKING, learning_rate=1.2)

    for session in range(5):
        difficulty = 0.2 + (session * 0.15)  # Gradually increase difficulty
        result = skill_system.practice_skill(
            character_id=scientist.id,
            skill_type=SkillType.ANALYTICAL_THINKING,
            difficulty=difficulty,
            duration_minutes=30
        )

        skill_progress = result['skill_after_practice']
        print(f"  Session {session + 1}: Level {skill_progress['skill_level']} "
              f"({skill_progress['experience_points']:.1f} XP) - "
              f"Breakthrough: {skill_progress['breakthrough_required']}")

    # Test breakthrough mechanics
    print("\n🚀 Testing breakthrough mechanics...")

    # Get a skill to high level to trigger breakthrough
    print(f"\n{programmer.name} pushing Programming to expert level:")
    skill_system.add_skill(programmer.id, SkillType.PROGRAMMING, learning_rate=1.5)

    # Rapid progression to trigger breakthrough
    for session in range(15):
        difficulty = 0.6 + (session * 0.02)
        result = skill_system.practice_skill(
            character_id=programmer.id,
            skill_type=SkillType.PROGRAMMING,
            difficulty=min(difficulty, 0.9),
            duration_minutes=45
        )

        skill_progress = result['skill_after_practice']
        if session % 3 == 0:  # Print every 3rd session
            print(f"  Session {session + 1}: Level {skill_progress['skill_level']} "
                  f"({skill_progress['experience_points']:.1f} XP)")

        if skill_progress['breakthrough_required']:
            print(f"  ⚡ BREAKTHROUGH REQUIRED! Progress: {skill_progress['breakthrough_progress']:.1f}/10")

        if result['session_results']['breakthrough_achieved']:
            print(f"  🎉 BREAKTHROUGH ACHIEVED!")
            break

    # Test group skill workshop
    print("\n👥 Testing group skill workshop...")

    workshop_result = skill_system.conduct_skill_workshop(
        character_ids=[scientist.id, artist.id, programmer.id],
        skill_type=SkillType.PROBLEM_SOLVING,
        duration_minutes=90
    )

    print(f"Workshop Results:")
    print(f"  Total XP Earned: {workshop_result['total_xp_earned']:.2f}")
    print(f"  Collaboration Bonus: {workshop_result['group_benefits']['collaboration_bonus_percent']:.1f}%")
    print(f"  Total Bonus XP: {workshop_result['group_benefits']['total_bonus_xp']:.2f}")

    for char_id, individual_result in workshop_result['individual_results'].items():
        char_name = next(c.name for c in characters if c.id == char_id)
        print(f"  {char_name}: {individual_result['session_results']['total_xp_gained']:.2f} XP")

    # Test skill overview and recommendations
    print("\n📊 Testing skill overview and recommendations...")

    for character in characters:
        overview = skill_system.get_all_skills_overview(character.id)
        print(f"\n{character.name} - Skill Overview:")
        print(f"  Total Skills: {overview['total_skills']}")
        print(f"  Overall Mastery: {overview['overall_mastery_level']}")
        print(f"  Total Badges: {overview['total_badges']}")

        if overview.get('top_skills'):
            print(f"  Top Skills:")
            for skill in overview['top_skills'][:3]:
                print(f"    - {skill['skill_type']}: {skill['skill_level']} ({skill['experience_points']:.1f} XP)")

        # Get detailed progress for top skill
        if overview.get('top_skills'):
            top_skill_type = SkillType(overview['top_skills'][0]['skill_type'])
            progress = skill_system.get_skill_progress(character.id, top_skill_type)

            print(f"  Detailed Progress for {top_skill_type.value}:")
            print(f"    Success Rate: {progress['skill']['success_rate']:.2%}")
            print(f"    Progress to Next Level: {progress['skill']['progress_to_next_level']:.1%}")

            if progress.get('recommendations'):
                print(f"    Recommendations:")
                for rec in progress['recommendations'][:3]:
                    print(f"      • {rec}")

    # Test skill decay
    print("\n⏰ Testing skill decay mechanics...")

    # Simulate time passing by modifying last_practiced
    research_skill = skill_system.get_skill(scientist.id, SkillType.RESEARCH)
    if research_skill:
        # Set last practiced to 10 days ago
        from datetime import timedelta
        research_skill.last_practiced = datetime.now() - timedelta(days=10)

        # Apply decay
        old_xp = research_skill.experience_points
        research_skill.apply_decay()
        new_xp = research_skill.experience_points

        print(f"Research Skill Decay:")
        print(f"  Before: {old_xp:.2f} XP")
        print(f"  After: {new_xp:.2f} XP")
        print(f"  Lost: {old_xp - new_xp:.2f} XP")

    # Save test data
    print("\n💾 Saving test data...")
    skill_system.save_to_disk()
    for character in characters:
        character_manager.save_character(character)

    print("\n✅ Skill system test completed successfully!")
    print(f"📁 Test data saved to: {Path('test_data').absolute()}")


async def demonstrate_api_usage():
    """Demonstrate how the skill system would be used via API calls"""
    print("\n🌐 API Usage Examples")
    print("=" * 30)

    # Show example API calls and their expected responses
    examples = [
        {
            "method": "GET",
            "endpoint": "/skills/available",
            "description": "Get all available skills grouped by category"
        },
        {
            "method": "GET",
            "endpoint": "/skills/recommendations/scientist",
            "description": "Get recommended skills for a scientist"
        },
        {
            "method": "GET",
            "endpoint": "/characters/{character_id}/skills",
            "description": "Get all skills for a character"
        },
        {
            "method": "POST",
            "endpoint": "/characters/{character_id}/skills",
            "data": {
                "skill_type": "research",
                "learning_rate": 1.2,
                "plateau_resistance": 1.0
            },
            "description": "Add a new skill to a character"
        },
        {
            "method": "POST",
            "endpoint": "/characters/{character_id}/practice/research",
            "data": {
                "difficulty": 0.5,
                "duration_minutes": 30
            },
            "description": "Practice a skill"
        },
        {
            "method": "GET",
            "endpoint": "/characters/{character_id}/skills/research/progress",
            "description": "Get detailed progress for a specific skill"
        },
        {
            "method": "POST",
            "endpoint": "/rooms/{room_id}/skill-workshop",
            "data": {
                "character_ids": ["char1", "char2"],
                "skill_type": "problem_solving",
                "duration_minutes": 60
            },
            "description": "Conduct a group skill workshop"
        },
        {
            "method": "GET",
            "endpoint": "/characters/{character_id}/badges",
            "description": "Get all badges earned by a character"
        }
    ]

    for example in examples:
        print(f"\n{example['method']} {example['endpoint']}")
        print(f"Description: {example['description']}")
        if 'data' in example:
            print(f"Request Body: {json.dumps(example['data'], indent=2)}")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_skill_system())
    asyncio.run(demonstrate_api_usage())