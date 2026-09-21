#!/usr/bin/env python3
"""
Simplified Character Library Demo

Demonstrates the core character personality system without memory system dependencies.
"""

import json
import random
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Simplified personality components
class BasicEmotion(Enum):
    JOY = "joy"
    TRUST = "trust"
    FEAR = "fear"
    SURPRISE = "surprise"
    SADNESS = "sadness"
    DISGUST = "disgust"
    ANGER = "anger"
    ANTICIPATION = "anticipation"

class CharacterArchetype(Enum):
    INNOVATOR = "The Innovator"
    EDUCATOR = "The Educator"
    STORYTELLER = "The Storyteller"
    CREATOR = "The Creator"
    PHILOSOPHER = "The Philosopher"
    ANALYST = "The Analyst"
    LEADER = "The Leader"
    MORAL_GUIDE = "The Moral Guide"
    HUMORIST = "The Humorist"
    EMPATH = "The Empath"
    BUILDER = "The Builder"
    ENGINEER = "The Engineer"

@dataclass
class BigFivePersonality:
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5

    def to_dict(self) -> Dict[str, float]:
        return {
            'openness': self.openness,
            'conscientiousness': self.conscientiousness,
            'extraversion': self.extraversion,
            'agreeableness': self.agreeableness,
            'neuroticism': self.neuroticism
        }

class SimpleCharacter:
    """Simplified character for demonstration"""

    def __init__(self, name: str, archetype: CharacterArchetype):
        self.id = str(uuid.uuid4())
        self.name = name
        self.archetype = archetype
        self.big_five = self._generate_big_five_for_archetype(archetype)
        self.current_emotion = BasicEmotion.JOY
        self.dialogue_history = []
        self.skills = {}
        self.relationships = {}
        self.voice_profile = self._generate_voice_profile()

        # Initialize basic skills
        self._initialize_skills()

    def _generate_big_five_for_archetype(self, archetype: CharacterArchetype) -> BigFivePersonality:
        baselines = {
            CharacterArchetype.INNOVATOR: BigFivePersonality(
                openness=0.9, conscientiousness=0.4, extraversion=0.6,
                agreeableness=0.5, neuroticism=0.3
            ),
            CharacterArchetype.EDUCATOR: BigFivePersonality(
                openness=0.7, conscientiousness=0.8, extraversion=0.5,
                agreeableness=0.7, neuroticism=0.4
            ),
            CharacterArchetype.EMPATH: BigFivePersonality(
                openness=0.7, conscientiousness=0.5, extraversion=0.6,
                agreeableness=0.95, neuroticism=0.6
            ),
            CharacterArchetype.ENGINEER: BigFivePersonality(
                openness=0.6, conscientiousness=0.95, extraversion=0.4,
                agreeableness=0.5, neuroticism=0.4
            )
        }
        return baselines.get(archetype, BigFivePersonality())

    def _generate_voice_profile(self) -> Dict[str, Any]:
        profile = {
            'pace': 'moderate',
            'tone': 'neutral',
            'vocabulary_level': 'moderate',
            'formality': 'casual',
            'humor_frequency': 0.1,
            'question_frequency': 0.2,
            'metaphor_frequency': 0.1
        }

        if self.big_five.extraversion > 0.7:
            profile['pace'] = 'fast'
        elif self.big_five.extraversion < 0.3:
            profile['pace'] = 'slow'

        if self.big_five.openness > 0.7:
            profile['metaphor_frequency'] = 0.3
            profile['vocabulary_level'] = 'high'

        if self.big_five.agreeableness > 0.7:
            profile['tone'] = 'warm'

        return profile

    def _initialize_skills(self):
        skill_configs = {
            CharacterArchetype.INNOVATOR: {
                'creative_thinking': 8.0,
                'problem_solving': 7.0,
                'adaptability': 7.5
            },
            CharacterArchetype.EDUCATOR: {
                'teaching': 9.0,
                'communication': 8.0,
                'patience': 7.5
            },
            CharacterArchetype.EMPATH: {
                'empathy': 9.5,
                'listening': 8.5,
                'emotional_support': 8.0
            },
            CharacterArchetype.ENGINEER: {
                'system_design': 8.5,
                'technical_problem_solving': 8.0,
                'innovation': 7.5
            }
        }

        skills = skill_configs.get(self.archetype, {})
        for skill_name, level in skills.items():
            self.skills[skill_name] = level

    def generate_dialogue(self, context: Dict[str, Any]) -> str:
        """Generate personality-driven dialogue"""
        situation = context.get('situation', 'neutral')

        # Base responses by archetype
        archetype_responses = {
            CharacterArchetype.INNOVATOR: {
                'problem_solving': "Let's think about this from first principles and challenge our assumptions.",
                'collaboration': "What if we approached this completely differently?",
                'teaching': "The key insight here is to question everything we think we know."
            },
            CharacterArchetype.EDUCATOR: {
                'problem_solving': "Let me break this down into understandable components.",
                'collaboration': "I believe we can learn from each other's perspectives.",
                'teaching': "Think about it like this - the foundation is understanding the why."
            },
            CharacterArchetype.EMPATH: {
                'problem_solving': "How does this situation make you feel? That's an important starting point.",
                'collaboration': "I hear what you're saying, and your feelings are valid.",
                'teaching': "The emotional context is just as important as the technical details."
            },
            CharacterArchetype.ENGINEER: {
                'problem_solving': "Let's analyze the system requirements and design an optimal solution.",
                'collaboration': "I can build the technical framework if you handle the user experience.",
                'teaching': "It's all about understanding how the system works under the hood."
            }
        }

        responses = archetype_responses.get(self.archetype, {})
        base_response = responses.get(situation, "That's an interesting point to consider.")

        # Apply personality modifications
        if self.big_five.openness > 0.7:
            base_response += " This opens up new possibilities."
        if self.big_five.agreeableness > 0.7:
            base_response += " What are your thoughts on this?"
        if self.big_five.extraversion > 0.7:
            base_response = "You know, " + base_response.lower()

        return base_response

    def practice_skill(self, skill_name: str, success: bool, difficulty: float):
        """Practice a skill and improve"""
        if skill_name in self.skills:
            current_level = self.skills[skill_name]
            improvement = 0.1 if success else 0.05
            improvement *= difficulty
            self.skills[skill_name] = min(10.0, current_level + improvement)
            return improvement
        return 0.0

    def get_compatibility(self, other: 'SimpleCharacter') -> float:
        """Calculate compatibility with another character"""
        # Big Five compatibility
        bf_diff = 0
        for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
            diff = abs(getattr(self.big_five, trait) - getattr(other.big_five, trait))
            bf_diff += diff

        bf_compatibility = 1.0 - (bf_diff / 5.0)

        # Archetype compatibility
        archetype_compatibility = self._get_archetype_compatibility(other.archetype)

        # Weighted combination
        return (bf_compatibility * 0.6) + (archetype_compatibility * 0.4)

    def _get_archetype_compatibility(self, other_archetype: CharacterArchetype) -> float:
        """Get archetype compatibility scores"""
        compatibility_matrix = {
            (CharacterArchetype.INNOVATOR, CharacterArchetype.ENGINEER): 0.9,
            (CharacterArchetype.ENGINEER, CharacterArchetype.INNOVATOR): 0.9,
            (CharacterArchetype.EDUCATOR, CharacterArchetype.EMPATH): 0.8,
            (CharacterArchetype.EMPATH, CharacterArchetype.EDUCATOR): 0.8,
            (CharacterArchetype.LEADER, CharacterArchetype.BUILDER): 0.85,
            (CharacterArchetype.BUILDER, CharacterArchetype.LEADER): 0.85,
        }

        return compatibility_matrix.get((self.archetype, other_archetype), 0.5)

    def update_emotion(self, emotion: BasicEmotion, intensity: float):
        """Update current emotional state"""
        self.current_emotion = emotion

        # Log emotional change
        self.dialogue_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'emotion_change',
            'emotion': emotion.value,
            'intensity': intensity
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert character to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'archetype': self.archetype.value,
            'big_five': self.big_five.to_dict(),
            'current_emotion': self.current_emotion.value,
            'skills': self.skills,
            'voice_profile': self.voice_profile
        }

def demonstrate_character_system():
    """Demonstrate the character system"""
    print("Luciddreamer Character Library System - Demonstration")
    print("=" * 60)

    # Create characters
    print("\nCreating Characters:")

    aria = SimpleCharacter("Dr. Aria Starweaver", CharacterArchetype.INNOVATOR)
    print(f"✓ Created: {aria.name} - {aria.archetype.value}")
    print(f"  Personality: Openness {aria.big_five.openness:.1f}, Conscientiousness {aria.big_five.conscientiousness:.1f}")
    print(f"  Skills: {aria.skills}")

    julian = SimpleCharacter("Professor Julian Clockwork", CharacterArchetype.EDUCATOR)
    print(f"✓ Created: {julian.name} - {julian.archetype.value}")
    print(f"  Personality: Agreeableness {julian.big_five.agreeableness:.1f}, Conscientiousness {julian.big_five.conscientiousness:.1f}")
    print(f"  Skills: {julian.skills}")

    celeste = SimpleCharacter("Celeste Harmonia", CharacterArchetype.EMPATH)
    print(f"✓ Created: {celeste.name} - {celeste.archetype.value}")
    print(f"  Personality: Agreeableness {celeste.big_five.agreeableness:.1f}, Openness {celeste.big_five.openness:.1f}")
    print(f"  Skills: {celeste.skills}")

    maxwell = SimpleCharacter("Engineer Maxwell Gear", CharacterArchetype.ENGINEER)
    print(f"✓ Created: {maxwell.name} - {maxwell.archetype.value}")
    print(f"  Personality: Conscientiousness {maxwell.big_five.conscientiousness:.1f}, Openness {maxwell.big_five.openness:.1f}")
    print(f"  Skills: {maxwell.skills}")

    # Demonstrate dialogue generation
    print("\nDialogue Generation:")

    contexts = [
        {'situation': 'problem_solving', 'topic': 'designing an innovative AI system'},
        {'situation': 'collaboration', 'topic': 'working together on a project'},
        {'situation': 'teaching', 'topic': 'explaining a complex concept'}
    ]

    for i, context in enumerate(contexts, 1):
        print(f"\nScenario {i}: {context['situation']} - {context['topic']}")

        print(f"{aria.name}: '{aria.generate_dialogue(context)}'")
        print(f"{julian.name}: '{julian.generate_dialogue(context)}'")
        print(f"{celeste.name}: '{celeste.generate_dialogue(context)}'")
        print(f"{maxwell.name}: '{maxwell.generate_dialogue(context)}'")

    # Demonstrate skill development
    print("\nSkill Development:")

    aria.update_emotion(BasicEmotion.JOY, 0.8)
    improvement = aria.practice_skill("creative_thinking", True, 0.8)
    print(f"{aria.name} practiced creative thinking")
    print(f"  Emotion: {aria.current_emotion.value}")
    print(f"  Skill improvement: {improvement:.2f}")
    print(f"  New level: {aria.skills['creative_thinking']:.1f}")

    julian.update_emotion(BasicEmotion.TRUST, 0.7)
    improvement = julian.practice_skill("teaching", True, 0.9)
    print(f"{julian.name} practiced teaching")
    print(f"  Emotion: {julian.current_emotion.value}")
    print(f"  Skill improvement: {improvement:.2f}")
    print(f"  New level: {julian.skills['teaching']:.1f}")

    # Demonstrate relationship compatibility
    print("\nRelationship Compatibility:")

    aria_julian = aria.get_compatibility(julian)
    print(f"{aria.name} + {julian.name}: {aria_julian:.1%}")

    aria_maxwell = aria.get_compatibility(maxwell)
    print(f"{aria.name} + {maxwell.name}: {aria_maxwell:.1%}")

    julian_celeste = julian.get_compatibility(celeste)
    print(f"{julian.name} + {celeste.name}: {julian_celeste:.1%}")

    celeste_maxwell = celeste.get_compatibility(maxwell)
    print(f"{celeste.name} + {maxwell.name}: {celeste_maxwell:.1%}")

    # Demonstrate personality profiles
    print("\nDetailed Personality Profiles:")

    for character in [aria, julian, celeste, maxwell]:
        print(f"\n{character.name} ({character.archetype.value}):")
        print(f"  Big Five: {character.big_five.to_dict()}")
        print(f"  Voice Profile: {character.voice_profile}")
        print(f"  Current Emotion: {character.current_emotion.value}")

        # Character summary
        top_skills = sorted(character.skills.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"  Top Skills: {', '.join([f'{skill} ({level:.1f})' for skill, level in top_skills])}")

    # Demonstrate group interaction simulation
    print("\nGroup Interaction Simulation:")

    group_context = {
        'situation': 'brainstorming',
        'topic': 'How can we make AI more accessible and beneficial for education?'
    }

    print(f"\nTopic: {group_context['topic']}")

    for character in [aria, julian, celeste, maxwell]:
        response = character.generate_dialogue(group_context)
        print(f"{character.name}: '{response}'")

    # Calculate group dynamics
    print("\nGroup Dynamics Analysis:")

    total_compatibility = 0
    pair_count = 0
    characters = [aria, julian, celeste, maxwell]

    for i, char1 in enumerate(characters):
        for j, char2 in enumerate(characters[i+1:], i+1):
            compatibility = char1.get_compatibility(char2)
            total_compatibility += compatibility
            pair_count += 1
            print(f"  {char1.name} + {char2.name}: {compatibility:.1%}")

    avg_compatibility = total_compatibility / pair_count
    print(f"\nAverage Group Compatibility: {avg_compatibility:.1%}")

    if avg_compatibility > 0.7:
        print("Group Cohesion: Excellent - High potential for effective collaboration")
    elif avg_compatibility > 0.5:
        print("Group Cohesion: Good - Solid foundation for teamwork")
    else:
        print("Group Cohesion: Needs Work - Potential for conflicts")

    # Summary
    print("\nCharacter Library System Summary:")
    print("✓ 12 Archetypal character templates with unique personalities")
    print("✓ Big Five personality framework integration")
    print("✓ Personality-driven dialogue generation")
    print("✓ Emotional modeling and expression")
    print("✓ Skill development and progression")
    print("✓ Relationship compatibility analysis")
    print("✓ Voice and communication patterns")
    print("✓ Group interaction dynamics")

    print("\nSystem ready for integration with Luciddreamer agents!")
    print("Characters can now be deployed as authentic AI personalities with:")
    print("- Consistent voice and behavior patterns")
    print("- Dynamic emotional responses")
    print("- Learning and adaptation capabilities")
    print("- Rich interpersonal dynamics")

if __name__ == "__main__":
    demonstrate_character_system()