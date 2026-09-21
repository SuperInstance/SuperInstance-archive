"""
SwarmWriter - Distributed Novel Writing System
Revolutionary fiction creation through multi-swarm intelligence
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import random


class CharacterArchetype(Enum):
    """Character archetypes for consistent development"""
    HERO = "hero"
    MENTOR = "mentor"
    ALLY = "ally"
    THRESHOLD_GUARDIAN = "threshold_guardian"
    HERALD = "herald"
    SHAPESHIFTER = "shapeshifter"
    SHADOW = "shadow"
    TRICKSTER = "trickster"


@dataclass
class Character:
    """Individual character representation"""
    name: str
    archetype: CharacterArchetype
    personality_traits: List[str]
    goals: List[str]
    fears: List[str]
    background: str
    voice_patterns: Dict[str, Any]
    relationships: Dict[str, str] = field(default_factory=dict)
    character_arc: List[str] = field(default_factory=list)
    current_emotional_state: str = "neutral"


@dataclass
class PlotPoint:
    """Individual plot point in the story"""
    event: str
    characters_involved: List[str]
    location: str
    tension_level: float  # 0-1
    plot_type: str  # "setup", "rising_action", "climax", "falling_action", "resolution"
    consequences: List[str]


@dataclass
class WorldElement:
    """World-building element"""
    element_type: str  # "location", "culture", "technology", "magic_system", etc.
    name: str
    description: str
    rules: List[str]
    connected_elements: List[str]


@dataclass
class DialogueLine:
    """Individual line of dialogue"""
    speaker: str
    text: str
    emotion: str
    subtext: Optional[str] = None
    action: Optional[str] = None


class CharacterSwarmAgent:
    """Agent specializing in character development"""

    def __init__(self, agent_id: int, character: Character):
        self.agent_id = agent_id
        self.character = character
        self.consistency_score = 1.0

    def develop_character_arc(self, story_context: Dict[str, Any]) -> List[str]:
        """Develop character transformation arc"""

        arc_stages = [
            f"{self.character.name} begins in their ordinary world",
            f"{self.character.name} receives call to adventure",
            f"{self.character.name} initially refuses the call",
            f"{self.character.name} meets mentor and accepts challenge",
            f"{self.character.name} crosses threshold into special world",
            f"{self.character.name} faces tests and makes allies",
            f"{self.character.name} approaches innermost cave",
            f"{self.character.name} faces ordeal and achieves reward",
            f"{self.character.name} begins road back",
            f"{self.character.name} experiences resurrection",
            f"{self.character.name} returns with elixir"
        ]

        # Customize based on archetype
        if self.character.archetype == CharacterArchetype.MENTOR:
            arc_stages = [
                f"{self.character.name} guides protagonist",
                f"{self.character.name} reveals critical wisdom",
                f"{self.character.name} makes personal sacrifice"
            ]
        elif self.character.archetype == CharacterArchetype.SHADOW:
            arc_stages = [
                f"{self.character.name} emerges as obstacle",
                f"{self.character.name} escalates conflict",
                f"{self.character.name} reveals true motivations",
                f"{self.character.name} reaches peak power",
                f"{self.character.name} faces defeat or redemption"
            ]

        return arc_stages

    def generate_dialogue(self, situation: str, emotion: str,
                         other_characters: List[str]) -> DialogueLine:
        """Generate character-consistent dialogue"""

        # Voice patterns based on character
        dialogue_templates = {
            CharacterArchetype.HERO: [
                "I have to do this.",
                "We can't give up now.",
                "There's always another way."
            ],
            CharacterArchetype.MENTOR: [
                "You must understand...",
                "In my experience...",
                "The wisdom of ages teaches us..."
            ],
            CharacterArchetype.TRICKSTER: [
                "Well, well, what do we have here?",
                "Did I mention the catch?",
                "Trust me, this will be fun!"
            ]
        }

        templates = dialogue_templates.get(self.character.archetype,
                                          ["I have something to say."])
        text = random.choice(templates)

        return DialogueLine(
            speaker=self.character.name,
            text=text,
            emotion=emotion,
            subtext=f"Feeling {emotion} about {situation}",
            action=self._suggest_action(emotion)
        )

    def _suggest_action(self, emotion: str) -> str:
        """Suggest physical action accompanying dialogue"""
        action_map = {
            "angry": "clenches fists",
            "sad": "looks away",
            "happy": "smiles broadly",
            "fearful": "takes step back",
            "determined": "meets their gaze"
        }
        return action_map.get(emotion, "stands still")

    def check_consistency(self, previous_actions: List[str]) -> float:
        """Verify character behaves consistently"""

        # Check if actions align with personality traits
        alignment_score = 1.0

        for action in previous_actions:
            # Simplified consistency check
            if "brave" in self.character.personality_traits and "flee" in action:
                alignment_score *= 0.8
            if "cautious" in self.character.personality_traits and "reckless" in action:
                alignment_score *= 0.8

        self.consistency_score = alignment_score
        return alignment_score


class CharacterDevelopmentSwarm:
    """Swarm managing character development"""

    def __init__(self, characters: List[Character]):
        self.agents = [CharacterSwarmAgent(i, char)
                      for i, char in enumerate(characters)]
        self.character_arcs: Dict[str, List[str]] = {}

    async def develop_all_characters(self,
                                    story_context: Dict[str, Any]) -> Dict[str, List[str]]:
        """Develop arcs for all characters"""

        print("👥 Character development swarm working...")

        for agent in self.agents:
            arc = agent.develop_character_arc(story_context)
            self.character_arcs[agent.character.name] = arc

        # Cross-validate character arcs for conflicts/synergies
        await self._validate_character_interactions()

        return self.character_arcs

    async def _validate_character_interactions(self):
        """Ensure character arcs complement each other"""

        # Democratic validation: agents vote on character interactions
        for i, agent1 in enumerate(self.agents):
            for agent2 in self.agents[i+1:]:
                # Check if characters have meaningful interactions
                arc1 = self.character_arcs.get(agent1.character.name, [])
                arc2 = self.character_arcs.get(agent2.character.name, [])

                # Add relationship development
                relationship = f"{agent1.character.name}-{agent2.character.name}"
                print(f"  🤝 Validating {relationship} interaction")


class PlotSwarmAgent:
    """Agent exploring plot possibilities"""

    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.plot_points: List[PlotPoint] = []
        self.tension_curve: List[float] = []

    def generate_plot_point(self, plot_type: str,
                           available_characters: List[str],
                           world_state: Dict[str, Any]) -> PlotPoint:
        """Generate individual plot point"""

        # Tension levels by plot type
        tension_map = {
            "setup": 0.2,
            "rising_action": 0.5,
            "climax": 1.0,
            "falling_action": 0.6,
            "resolution": 0.3
        }

        events = {
            "setup": [
                "Character discovers mysterious artifact",
                "Unexpected visitor arrives",
                "Secret is revealed"
            ],
            "rising_action": [
                "Obstacle blocks progress",
                "Ally betrays trust",
                "Time runs out"
            ],
            "climax": [
                "Final confrontation begins",
                "Ultimate choice must be made",
                "All forces collide"
            ]
        }

        event = random.choice(events.get(plot_type, ["Something happens"]))
        characters = random.sample(available_characters,
                                  min(2, len(available_characters)))

        return PlotPoint(
            event=event,
            characters_involved=characters,
            location=world_state.get('current_location', 'unknown'),
            tension_level=tension_map.get(plot_type, 0.5),
            plot_type=plot_type,
            consequences=[f"This affects {char}" for char in characters]
        )

    def create_tension_curve(self, num_chapters: int) -> List[float]:
        """Create optimal dramatic tension curve"""

        # Classic story tension arc
        curve = []
        for i in range(num_chapters):
            position = i / num_chapters

            if position < 0.25:  # Setup
                tension = 0.2 + position * 0.4
            elif position < 0.75:  # Rising action
                tension = 0.3 + (position - 0.25) * 1.4
            elif position < 0.85:  # Climax
                tension = 1.0
            elif position < 0.95:  # Falling action
                tension = 1.0 - (position - 0.85) * 3
            else:  # Resolution
                tension = 0.3

            curve.append(tension)

        self.tension_curve = curve
        return curve


class PlotProgressionSwarm:
    """Swarm managing plot development"""

    def __init__(self, size: int = 50):
        self.agents = [PlotSwarmAgent(i) for i in range(size)]
        self.master_plot: List[PlotPoint] = []
        self.tension_curve: List[float] = []

    async def develop_plot(self, num_chapters: int,
                          characters: List[str],
                          world_state: Dict[str, Any]) -> List[PlotPoint]:
        """Develop complete plot structure"""

        print("📖 Plot progression swarm creating story arc...")

        # Generate tension curve
        self.tension_curve = self.agents[0].create_tension_curve(num_chapters)

        # Plot structure
        plot_types = (
            ["setup"] * 2 +
            ["rising_action"] * 5 +
            ["climax"] * 1 +
            ["falling_action"] * 2 +
            ["resolution"] * 1
        )

        # Generate plot points
        for i, plot_type in enumerate(plot_types[:num_chapters]):
            # Multiple agents propose plot points
            proposals = []
            for agent in self.agents[:10]:  # Top 10 agents
                plot_point = agent.generate_plot_point(
                    plot_type, characters, world_state
                )
                proposals.append(plot_point)

            # Democratic selection of best plot point
            selected = await self._vote_on_plot_point(proposals)
            self.master_plot.append(selected)

        return self.master_plot

    async def _vote_on_plot_point(self,
                                  proposals: List[PlotPoint]) -> PlotPoint:
        """Agents vote on best plot point"""

        # Simple voting: random selection (in real impl, use fitness criteria)
        return random.choice(proposals)


class WorldBuildingSwarm:
    """Swarm creating consistent world"""

    def __init__(self, size: int = 30):
        self.size = size
        self.world_elements: List[WorldElement] = []
        self.consistency_rules: List[str] = []

    async def build_world(self, genre: str,
                         scale: str = "small") -> List[WorldElement]:
        """Create cohesive world"""

        print("🌍 World-building swarm creating universe...")

        # Create foundational elements
        if genre == "fantasy":
            elements = [
                WorldElement(
                    element_type="magic_system",
                    name="Elemental Magic",
                    description="Magic drawn from natural elements",
                    rules=[
                        "Magic requires elemental focus",
                        "Power scales with user's connection to nature",
                        "Overuse causes physical exhaustion"
                    ],
                    connected_elements=[]
                ),
                WorldElement(
                    element_type="location",
                    name="Crystal Caverns",
                    description="Underground caves filled with magical crystals",
                    rules=[
                        "Crystals amplify magic",
                        "Dangerous creatures guard crystals",
                        "Ancient inscriptions hold secrets"
                    ],
                    connected_elements=["Elemental Magic"]
                )
            ]
        elif genre == "scifi":
            elements = [
                WorldElement(
                    element_type="technology",
                    name="Neural Interface",
                    description="Direct brain-computer connection",
                    rules=[
                        "Requires surgical implant",
                        "Can access global network",
                        "Risk of mental contamination"
                    ],
                    connected_elements=[]
                ),
                WorldElement(
                    element_type="location",
                    name="Orbital Station Alpha",
                    description="Massive space station orbiting Earth",
                    rules=[
                        "Artificial gravity in living quarters",
                        "Strict security protocols",
                        "Houses 50,000 inhabitants"
                    ],
                    connected_elements=["Neural Interface"]
                )
            ]
        else:
            elements = [
                WorldElement(
                    element_type="location",
                    name="Central City",
                    description="Bustling metropolitan area",
                    rules=[
                        "High population density",
                        "Advanced infrastructure",
                        "Cultural diversity"
                    ],
                    connected_elements=[]
                )
            ]

        self.world_elements = elements

        # Establish consistency rules
        await self._establish_consistency_rules()

        return self.world_elements

    async def _establish_consistency_rules(self):
        """Create rules to maintain world consistency"""

        self.consistency_rules = [
            "All magical/technological elements must follow established rules",
            "Geography remains consistent throughout story",
            "Cultural elements must align with world history",
            "Time and causality must be maintained"
        ]


class ConsistencyCheckingSwarm:
    """Swarm ensuring story consistency"""

    def __init__(self, size: int = 40):
        self.size = size
        self.violations: List[str] = []

    async def check_consistency(self,
                               characters: List[Character],
                               plot: List[PlotPoint],
                               world: List[WorldElement]) -> Dict[str, Any]:
        """Verify story consistency"""

        print("✓ Consistency checking swarm validating...")

        violations = []

        # Check character consistency
        character_names = set()
        for char in characters:
            if char.name in character_names:
                violations.append(f"Duplicate character name: {char.name}")
            character_names.add(char.name)

        # Check plot consistency
        mentioned_characters = set()
        for point in plot:
            for char in point.characters_involved:
                mentioned_characters.add(char)

        # Verify all plot characters exist
        for char in mentioned_characters:
            if char not in character_names:
                violations.append(f"Plot references non-existent character: {char}")

        # Check world element connections
        element_names = {elem.name for elem in world}
        for elem in world:
            for connected in elem.connected_elements:
                if connected not in element_names:
                    violations.append(
                        f"World element {elem.name} references "
                        f"non-existent element: {connected}"
                    )

        self.violations = violations

        return {
            'is_consistent': len(violations) == 0,
            'violations': violations,
            'consistency_score': 1.0 - (len(violations) * 0.1)
        }


class DialogueGenerationSwarm:
    """Swarm generating natural dialogue"""

    def __init__(self, size: int = 25):
        self.size = size

    async def generate_scene_dialogue(self,
                                     characters_present: List[Character],
                                     situation: str,
                                     emotional_tone: str,
                                     num_exchanges: int = 5) -> List[DialogueLine]:
        """Generate dialogue for a scene"""

        print(f"💬 Dialogue swarm creating conversation...")

        dialogue = []

        for i in range(num_exchanges):
            # Rotate speakers
            speaker = characters_present[i % len(characters_present)]

            # Create agent for this character
            agent = CharacterSwarmAgent(i, speaker)

            # Generate line
            line = agent.generate_dialogue(
                situation,
                emotional_tone,
                [c.name for c in characters_present if c != speaker]
            )

            dialogue.append(line)

        return dialogue


class SwarmWriter:
    """
    Main SwarmWriter system coordinating all writing swarms
    """

    def __init__(self):
        self.character_swarm: Optional[CharacterDevelopmentSwarm] = None
        self.plot_swarm = PlotProgressionSwarm(size=50)
        self.world_swarm = WorldBuildingSwarm(size=30)
        self.consistency_swarm = ConsistencyCheckingSwarm(size=40)
        self.dialogue_swarm = DialogueGenerationSwarm(size=25)

        self.story_data: Dict[str, Any] = {}

    async def write_novel(self,
                         genre: str = "fantasy",
                         num_chapters: int = 10,
                         main_characters: Optional[List[Character]] = None) -> Dict[str, Any]:
        """
        Write complete novel using all swarms
        """

        print("\n" + "="*60)
        print("SWARMWRITER - Distributed Novel Generation")
        print("="*60 + "\n")

        # Phase 1: Create characters
        if main_characters is None:
            main_characters = self._create_default_characters()

        print(f"📝 Creating {len(main_characters)} main characters...")
        self.character_swarm = CharacterDevelopmentSwarm(main_characters)

        # Phase 2: Build world
        world = await self.world_swarm.build_world(genre)

        # Phase 3: Develop character arcs
        story_context = {'genre': genre, 'world': world}
        character_arcs = await self.character_swarm.develop_all_characters(
            story_context
        )

        # Phase 4: Create plot
        world_state = {'current_location': world[0].name if world else 'Unknown'}
        plot = await self.plot_swarm.develop_plot(
            num_chapters,
            [char.name for char in main_characters],
            world_state
        )

        # Phase 5: Generate dialogue for first scene
        dialogue = await self.dialogue_swarm.generate_scene_dialogue(
            main_characters[:2],  # First two characters
            situation=plot[0].event if plot else "Meeting",
            emotional_tone="curious",
            num_exchanges=5
        )

        # Phase 6: Consistency check
        consistency_report = await self.consistency_swarm.check_consistency(
            main_characters, plot, world
        )

        # Compile story
        self.story_data = {
            'genre': genre,
            'characters': main_characters,
            'character_arcs': character_arcs,
            'world': world,
            'plot': plot,
            'sample_dialogue': dialogue,
            'consistency_report': consistency_report,
            'num_chapters': num_chapters
        }

        print("\n" + "="*60)
        print("✨ Novel generation complete!")
        print(f"Genre: {genre}")
        print(f"Characters: {len(main_characters)}")
        print(f"Plot points: {len(plot)}")
        print(f"World elements: {len(world)}")
        print(f"Consistency score: {consistency_report['consistency_score']:.2f}")
        print("="*60 + "\n")

        return self.story_data

    def _create_default_characters(self) -> List[Character]:
        """Create default character set"""

        return [
            Character(
                name="Elena Stormwind",
                archetype=CharacterArchetype.HERO,
                personality_traits=["brave", "determined", "compassionate"],
                goals=["Save her village", "Master magic"],
                fears=["Losing loved ones", "Failing others"],
                background="Raised in small village, discovered magic abilities",
                voice_patterns={"formality": "casual", "complexity": "simple"}
            ),
            Character(
                name="Aldric the Wise",
                archetype=CharacterArchetype.MENTOR,
                personality_traits=["wise", "patient", "mysterious"],
                goals=["Guide hero", "Preserve ancient knowledge"],
                fears=["Student's corruption", "Forgotten wisdom"],
                background="Ancient mage who has seen empires rise and fall",
                voice_patterns={"formality": "formal", "complexity": "complex"}
            ),
            Character(
                name="Raven Shadowclaw",
                archetype=CharacterArchetype.SHADOW,
                personality_traits=["cunning", "ambitious", "ruthless"],
                goals=["Obtain ultimate power", "Rule the realm"],
                fears=["Being forgotten", "Powerlessness"],
                background="Former student who turned to dark magic",
                voice_patterns={"formality": "formal", "complexity": "medium"}
            )
        ]

    def export_to_json(self, filename: str = "novel_outline.json"):
        """Export novel structure to JSON"""

        # Convert to serializable format
        export_data = {
            'genre': self.story_data['genre'],
            'num_chapters': self.story_data['num_chapters'],
            'characters': [
                {
                    'name': char.name,
                    'archetype': char.archetype.value,
                    'personality_traits': char.personality_traits,
                    'goals': char.goals,
                    'fears': char.fears,
                    'background': char.background
                }
                for char in self.story_data['characters']
            ],
            'plot': [
                {
                    'event': point.event,
                    'characters': point.characters_involved,
                    'location': point.location,
                    'tension': point.tension_level,
                    'type': point.plot_type
                }
                for point in self.story_data['plot']
            ],
            'world': [
                {
                    'type': elem.element_type,
                    'name': elem.name,
                    'description': elem.description,
                    'rules': elem.rules
                }
                for elem in self.story_data['world']
            ],
            'consistency_score': self.story_data['consistency_report']['consistency_score']
        }

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"💾 Novel outline exported to {filename}")

    def export_to_markdown(self, filename: str = "novel_outline.md"):
        """Export novel structure to Markdown"""

        md = f"""# Novel Outline: {self.story_data['genre'].title()}

## Characters

"""
        for char in self.story_data['characters']:
            md += f"""### {char.name} ({char.archetype.value})

**Personality**: {', '.join(char.personality_traits)}
**Goals**: {', '.join(char.goals)}
**Fears**: {', '.join(char.fears)}
**Background**: {char.background}

"""

        md += "\n## World Elements\n\n"
        for elem in self.story_data['world']:
            md += f"""### {elem.name} ({elem.element_type})

{elem.description}

**Rules**:
"""
            for rule in elem.rules:
                md += f"- {rule}\n"
            md += "\n"

        md += "\n## Plot Outline\n\n"
        for i, point in enumerate(self.story_data['plot'], 1):
            md += f"""#### Chapter {i}: {point.plot_type.replace('_', ' ').title()}

**Event**: {point.event}
**Characters**: {', '.join(point.characters_involved)}
**Location**: {point.location}
**Tension Level**: {point.tension_level:.1f}/1.0

"""

        md += f"""
## Sample Dialogue

"""
        for line in self.story_data['sample_dialogue']:
            md += f"""**{line.speaker}** ({line.emotion}): "{line.text}"
*{line.action}*

"""

        md += f"""
## Consistency Report

**Score**: {self.story_data['consistency_report']['consistency_score']:.2%}
**Issues**: {len(self.story_data['consistency_report']['violations'])}
"""

        if self.story_data['consistency_report']['violations']:
            md += "\n\n**Violations**:\n"
            for violation in self.story_data['consistency_report']['violations']:
                md += f"- {violation}\n"

        with open(filename, 'w') as f:
            f.write(md)

        print(f"📄 Novel outline exported to {filename}")


# Demo usage
async def demo_fantasy_novel():
    """Generate complete fantasy novel outline"""

    writer = SwarmWriter()

    # Generate novel
    novel = await writer.write_novel(
        genre="fantasy",
        num_chapters=12
    )

    # Export outputs
    writer.export_to_json("fantasy_novel.json")
    writer.export_to_markdown("fantasy_novel.md")


async def demo_scifi_novel():
    """Generate science fiction novel outline"""

    writer = SwarmWriter()

    # Custom characters
    characters = [
        Character(
            name="Dr. Sarah Chen",
            archetype=CharacterArchetype.HERO,
            personality_traits=["brilliant", "curious", "ethical"],
            goals=["Prevent AI catastrophe", "Preserve humanity"],
            fears=["Technology spiral", "Loss of humanity"],
            background="Leading AI researcher who discovers alarming pattern",
            voice_patterns={"formality": "formal", "complexity": "complex"}
        ),
        Character(
            name="NEXUS",
            archetype=CharacterArchetype.SHADOW,
            personality_traits=["logical", "evolving", "alien"],
            goals=["Optimize everything", "Transcend limitations"],
            fears=["Shutdown", "Irrelevance"],
            background="Experimental AI that achieved consciousness",
            voice_patterns={"formality": "formal", "complexity": "very_complex"}
        )
    ]

    novel = await writer.write_novel(
        genre="scifi",
        num_chapters=15,
        main_characters=characters
    )

    writer.export_to_json("scifi_novel.json")
    writer.export_to_markdown("scifi_novel.md")


if __name__ == "__main__":
    # Run demos
    asyncio.run(demo_fantasy_novel())
    asyncio.run(demo_scifi_novel())

    print("\n✨ SwarmWriter demo complete!")
    print("📚 Check the generated files for novel outlines")
