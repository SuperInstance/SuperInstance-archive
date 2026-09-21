"""
Skill System Integration Demo
=============================
Shows how to integrate the skill system with character creation and management.
"""

import asyncio
from pathlib import Path

# Import the required systems
from character_system import CharacterManager
from skill_system import SkillSystem, SkillType, recommend_starter_skills


async def create_character_with_skills():
    """Create a character and automatically add recommended skills"""
    print("🎭 Creating Character with Integrated Skills")
    print("=" * 45)

    # Initialize systems
    character_manager = CharacterManager(Path("ai_society_data") / "characters")
    skill_system = SkillSystem(Path("ai_society_data") / "skills")

    # Create a new character
    character = character_manager.create_character(
        name="Dr. Alex Thompson",
        specialization="Data Scientist",
        backstory="Passionate about uncovering insights from complex datasets and building predictive models",
        personality={
            "curious": 0.9,
            "analytical": 0.8,
            "creative": 0.6,
            "methodical": 0.7
        }
    )

    print(f"✅ Created character: {character.name}")
    print(f"📚 Specialization: {character.specialization}")

    # Get and add recommended skills
    recommended_skills = recommend_starter_skills(character.specialization)
    print(f"\n🎓 Adding recommended skills:")

    for skill_type in recommended_skills:
        skill = skill_system.add_skill(character.id, skill_type)
        print(f"  + {skill_type.value.replace('_', ' ').title()} (Level: {skill.skill_level.value})")

    # Save everything
    character_manager.save_character(character)
    skill_system.save_to_disk()

    print(f"\n💾 Saved character and skills")
    print(f"🔍 Character ID: {character.id}")

    # Show how to practice skills
    print(f"\n💪 Example: Practicing Data Analysis skill")
    result = skill_system.practice_skill(
        character_id=character.id,
        skill_type=SkillType.DATA_ANALYSIS,
        difficulty=0.4,
        duration_minutes=45
    )

    print(f"  XP Gained: {result['session_results']['total_xp_gained']:.2f}")
    print(f"  Success Rate: {result['session_results']['session_success_rate']:.2%}")
    print(f"  New Level: {result['skill_after_practice']['skill_level']}")

    # Save after practice
    skill_system.save_to_disk()

    return character.id


def show_api_examples(character_id: str):
    """Show examples of API calls that would work with this character"""
    print(f"\n🌐 API Examples for Character {character_id}")
    print("=" * 50)

    examples = [
        {
            "description": "Get all character skills",
            "curl": f"curl -X GET http://localhost:8001/characters/{character_id}/skills"
        },
        {
            "description": "Practice data analysis skill",
            "curl": f"""curl -X POST http://localhost:8001/characters/{character_id}/practice/data_analysis \\
  -H "Content-Type: application/json" \\
  -d '{{"difficulty": 0.5, "duration_minutes": 30}}'"""
        },
        {
            "description": "Get detailed progress for data analysis",
            "curl": f"curl -X GET http://localhost:8001/characters/{character_id}/skills/data_analysis/progress"
        },
        {
            "description": "Add a new skill (machine learning)",
            "curl": f"""curl -X POST http://localhost:8001/characters/{character_id}/skills \\
  -H "Content-Type: application/json" \\
  -d '{{"skill_type": "programming", "learning_rate": 1.2}}'"""
        },
        {
            "description": "Get all earned badges",
            "curl": f"curl -X GET http://localhost:8001/characters/{character_id}/badges"
        }
    ]

    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['description']}:")
        print(f"   {example['curl']}")


async def main():
    """Main demo function"""
    print("🚀 AI Society Portal - Skill System Integration Demo")
    print("=" * 60)

    # Create character with skills
    character_id = await create_character_with_skills()

    # Show API examples
    show_api_examples(character_id)

    print(f"\n✨ Demo completed! Character {character_id} is ready for skill development.")
    print("\nNext steps:")
    print("1. Start the API server: python api_server.py")
    print("2. Use the curl commands above to interact with the character")
    print("3. Add more characters and have them practice together")
    print("4. Create skill workshops in rooms for collaborative learning")


if __name__ == "__main__":
    asyncio.run(main())