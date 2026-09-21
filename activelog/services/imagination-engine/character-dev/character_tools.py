#!/usr/bin/env python3

import asyncio
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import random
import uuid

class PersonalityType(Enum):
    HERO = "hero"
    MENTOR = "mentor"
    TRICKSTER = "trickster"
    GUARDIAN = "guardian"
    HERALD = "herald"
    SHAPESHIFTER = "shapeshifter"
    SHADOW = "shadow"
    ALLY = "ally"

class CharacterArc(Enum):
    GROWTH = "growth"
    FALL = "fall"
    REDEMPTION = "redemption"
    CORRUPTION = "corruption"
    STEADFAST = "steadfast"
    DISILLUSIONMENT = "disillusionment"

@dataclass
class CharacterTrait:
    name: str
    value: int  # 1-10 scale
    description: str

@dataclass
class CharacterRelationship:
    character_id: str
    relationship_type: str
    strength: int  # 1-10 scale
    description: str
    history: List[str]

@dataclass
class CharacterBackground:
    origin: str
    motivation: str
    fear: str
    secret: str
    defining_moment: str
    family: Dict[str, str]
    skills: List[str]
    flaws: List[str]

@dataclass
class Character:
    id: str
    name: str
    age: int
    personality_type: PersonalityType
    character_arc: CharacterArc
    traits: Dict[str, CharacterTrait]
    background: CharacterBackground
    relationships: List[CharacterRelationship]
    dialogue_style: Dict[str, Any]
    physical_description: str
    created_at: str
    updated_at: str

class CharacterGenerator:
    def __init__(self):
        self.trait_templates = {
            "courage": ["Brave and bold", "Cautious but determined", "Fearless to a fault"],
            "intelligence": ["Quick-witted", "Deep thinker", "Street smart"],
            "empathy": ["Highly compassionate", "Struggles to connect", "Selectively caring"],
            "ambition": ["Driven to succeed", "Content with simple life", "Ruthlessly ambitious"],
            "loyalty": ["Fiercely loyal", "Questions authority", "Changes sides easily"],
            "humor": ["Natural comedian", "Dry wit", "Takes everything seriously"],
            "curiosity": ["Insatiably curious", "Focused interests", "Avoids new things"],
            "patience": ["Extremely patient", "Quick to act", "Varies by situation"]
        }
        
        self.origins = [
            "Raised in a small village by loving grandparents",
            "Grew up on the streets, learning to survive",
            "Noble family with high expectations",
            "Raised by a mysterious mentor figure",
            "Ordinary family with extraordinary secret",
            "Orphaned young, raised by community",
            "Traveled constantly with merchant parents",
            "Isolated childhood in remote location"
        ]
        
        self.motivations = [
            "Prove themselves worthy of love and respect",
            "Uncover the truth about their past",
            "Protect those who cannot protect themselves",
            "Find their place in the world",
            "Restore family honor",
            "Discover their true potential",
            "Escape their predetermined fate",
            "Unite divided communities"
        ]
        
        self.fears = [
            "Being abandoned by those they love",
            "Losing control of their power",
            "Being ordinary or unremarkable",
            "Failing to live up to expectations",
            "Their dark past being revealed",
            "Hurting innocent people",
            "Being trapped or confined",
            "Making the wrong choice"
        ]

    def generate_character(self, name: str = None, personality_type: PersonalityType = None) -> Character:
        character_id = str(uuid.uuid4())
        
        if not name:
            name = self._generate_name()
        
        if not personality_type:
            personality_type = random.choice(list(PersonalityType))
        
        traits = self._generate_traits(personality_type)
        background = self._generate_background()
        dialogue_style = self._generate_dialogue_style(personality_type, traits)
        
        return Character(
            id=character_id,
            name=name,
            age=random.randint(16, 65),
            personality_type=personality_type,
            character_arc=random.choice(list(CharacterArc)),
            traits=traits,
            background=background,
            relationships=[],
            dialogue_style=dialogue_style,
            physical_description=self._generate_physical_description(),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

    def _generate_name(self) -> str:
        first_names = ["Alex", "Jamie", "River", "Phoenix", "Sage", "Quinn", "Rowan", "Ember", "Luna", "Kai"]
        last_names = ["Storm", "Stone", "Rivers", "Cross", "Vale", "Hart", "Moon", "Silver", "Gold", "Swift"]
        return f"{random.choice(first_names)} {random.choice(last_names)}"

    def _generate_traits(self, personality_type: PersonalityType) -> Dict[str, CharacterTrait]:
        traits = {}
        
        for trait_name, descriptions in self.trait_templates.items():
            value = random.randint(1, 10)
            
            # Adjust based on personality type
            if personality_type == PersonalityType.HERO and trait_name == "courage":
                value = max(7, value)
            elif personality_type == PersonalityType.MENTOR and trait_name == "intelligence":
                value = max(8, value)
            elif personality_type == PersonalityType.TRICKSTER and trait_name == "humor":
                value = max(7, value)
            
            traits[trait_name] = CharacterTrait(
                name=trait_name,
                value=value,
                description=random.choice(descriptions)
            )
        
        return traits

    def _generate_background(self) -> CharacterBackground:
        return CharacterBackground(
            origin=random.choice(self.origins),
            motivation=random.choice(self.motivations),
            fear=random.choice(self.fears),
            secret=self._generate_secret(),
            defining_moment=self._generate_defining_moment(),
            family=self._generate_family(),
            skills=self._generate_skills(),
            flaws=self._generate_flaws()
        )

    def _generate_secret(self) -> str:
        secrets = [
            "Has magical abilities they hide from others",
            "Is related to someone important they've never met",
            "Made a terrible mistake in their past",
            "Knows something that could change everything",
            "Has a hidden talent they're ashamed of",
            "Is not who they appear to be",
            "Has witnessed something they shouldn't have",
            "Is carrying out someone else's mission"
        ]
        return random.choice(secrets)

    def _generate_defining_moment(self) -> str:
        moments = [
            "Watched their hometown burn in a disaster",
            "Saved someone's life at great personal cost",
            "Failed to help someone in desperate need",
            "Discovered their true heritage",
            "Made a difficult moral choice",
            "Lost someone they couldn't protect",
            "Found an unexpected mentor",
            "Stood up to powerful oppressors"
        ]
        return random.choice(moments)

    def _generate_family(self) -> Dict[str, str]:
        family_roles = ["parent", "sibling", "mentor", "rival"]
        family = {}
        
        for _ in range(random.randint(1, 4)):
            role = random.choice(family_roles)
            if role not in family:
                family[role] = self._generate_name()
        
        return family

    def _generate_skills(self) -> List[str]:
        skills = ["combat", "diplomacy", "stealth", "magic", "crafting", "healing", "knowledge", "survival", "leadership", "art"]
        return random.sample(skills, random.randint(2, 5))

    def _generate_flaws(self) -> List[str]:
        flaws = ["overconfident", "impatient", "stubborn", "trusting", "pessimistic", "reckless", "secretive", "prideful"]
        return random.sample(flaws, random.randint(1, 3))

    def _generate_dialogue_style(self, personality_type: PersonalityType, traits: Dict[str, CharacterTrait]) -> Dict[str, Any]:
        style = {
            "formality": "casual",
            "vocabulary": "simple",
            "speech_patterns": [],
            "catchphrases": []
        }
        
        if personality_type == PersonalityType.MENTOR:
            style["formality"] = "formal"
            style["vocabulary"] = "complex"
            style["speech_patterns"] = ["asks probing questions", "speaks in metaphors"]
        elif personality_type == PersonalityType.TRICKSTER:
            style["speech_patterns"] = ["uses wordplay", "speaks in riddles", "makes jokes"]
            style["catchphrases"] = ["Well, well, well...", "That's interesting..."]
        elif personality_type == PersonalityType.GUARDIAN:
            style["speech_patterns"] = ["gives warnings", "speaks protectively"]
            style["catchphrases"] = ["Be careful", "I've got your back"]
        
        if traits["intelligence"].value > 7:
            style["vocabulary"] = "complex"
        if traits["humor"].value > 7:
            style["speech_patterns"].append("uses humor to deflect")
        
        return style

    def _generate_physical_description(self) -> str:
        heights = ["short", "average height", "tall"]
        builds = ["lean", "muscular", "stocky", "athletic"]
        features = ["sharp features", "soft features", "weathered features", "youthful features"]
        
        return f"{random.choice(heights)}, {random.choice(builds)}, with {random.choice(features)}"

class CharacterDevelopmentTools:
    def __init__(self, db_path: str = "character_development.db"):
        self.db_path = db_path
        self.character_generator = CharacterGenerator()
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            personality_type TEXT,
            character_arc TEXT,
            traits TEXT,
            background TEXT,
            relationships TEXT,
            dialogue_style TEXT,
            physical_description TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS character_relationships (
            id TEXT PRIMARY KEY,
            character1_id TEXT,
            character2_id TEXT,
            relationship_type TEXT,
            strength INTEGER,
            description TEXT,
            history TEXT,
            created_at TEXT,
            FOREIGN KEY (character1_id) REFERENCES characters (id),
            FOREIGN KEY (character2_id) REFERENCES characters (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS character_arcs (
            id TEXT PRIMARY KEY,
            character_id TEXT,
            arc_name TEXT,
            current_stage TEXT,
            stages TEXT,
            milestones TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (character_id) REFERENCES characters (id)
        )
        ''')
        
        conn.commit()
        conn.close()

    async def create_character(self, name: str = None, personality_type: str = None) -> Character:
        pt = PersonalityType(personality_type) if personality_type else None
        character = self.character_generator.generate_character(name, pt)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO characters VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            character.id, character.name, character.age,
            character.personality_type.value, character.character_arc.value,
            json.dumps({k: asdict(v) for k, v in character.traits.items()}),
            json.dumps(asdict(character.background)),
            json.dumps([asdict(r) for r in character.relationships]),
            json.dumps(character.dialogue_style),
            character.physical_description,
            character.created_at, character.updated_at
        ))
        
        conn.commit()
        conn.close()
        
        return character

    async def get_character(self, character_id: str) -> Optional[Character]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM characters WHERE id = ?', (character_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        traits_data = json.loads(row[5])
        traits = {k: CharacterTrait(**v) for k, v in traits_data.items()}
        
        background_data = json.loads(row[6])
        background = CharacterBackground(**background_data)
        
        relationships_data = json.loads(row[7])
        relationships = [CharacterRelationship(**r) for r in relationships_data]
        
        return Character(
            id=row[0], name=row[1], age=row[2],
            personality_type=PersonalityType(row[3]),
            character_arc=CharacterArc(row[4]),
            traits=traits, background=background,
            relationships=relationships,
            dialogue_style=json.loads(row[8]),
            physical_description=row[9],
            created_at=row[10], updated_at=row[11]
        )

    async def list_characters(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, personality_type, character_arc FROM characters')
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": row[0],
                "name": row[1],
                "personality_type": row[2],
                "character_arc": row[3]
            }
            for row in rows
        ]

    async def develop_character_arc(self, character_id: str, target_arc: CharacterArc) -> Dict[str, Any]:
        character = await self.get_character(character_id)
        if not character:
            return {"error": "Character not found"}
        
        arc_stages = self._generate_arc_stages(character.character_arc, target_arc)
        milestones = self._generate_arc_milestones(character, target_arc)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        arc_id = str(uuid.uuid4())
        cursor.execute('''
        INSERT INTO character_arcs VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            arc_id, character_id, target_arc.value, "beginning",
            json.dumps(arc_stages), json.dumps(milestones),
            datetime.now().isoformat(), datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "arc_id": arc_id,
            "character_name": character.name,
            "target_arc": target_arc.value,
            "stages": arc_stages,
            "milestones": milestones
        }

    def _generate_arc_stages(self, current_arc: CharacterArc, target_arc: CharacterArc) -> List[str]:
        stages = ["Beginning", "Call to Change", "Resistance", "Exploration", "Commitment", "Transformation", "Resolution"]
        
        if target_arc == CharacterArc.GROWTH:
            stages = ["Ordinary World", "Call to Adventure", "Refusal", "Meeting Mentor", "Crossing Threshold", "Tests", "Growth", "Return"]
        elif target_arc == CharacterArc.FALL:
            stages = ["Success", "Temptation", "First Compromise", "Escalation", "Point of No Return", "Consequences", "Destruction"]
        elif target_arc == CharacterArc.REDEMPTION:
            stages = ["Rock Bottom", "Recognition", "Desire to Change", "First Steps", "Setbacks", "Commitment", "Redemption"]
        
        return stages

    def _generate_arc_milestones(self, character: Character, target_arc: CharacterArc) -> List[Dict[str, Any]]:
        milestones = []
        
        if target_arc == CharacterArc.GROWTH:
            milestones = [
                {"stage": "Call to Adventure", "description": f"{character.name} faces a challenge that requires growth"},
                {"stage": "Meeting Mentor", "description": f"{character.name} finds guidance for their journey"},
                {"stage": "Crossing Threshold", "description": f"{character.name} commits to change"},
                {"stage": "Growth", "description": f"{character.name} demonstrates newfound wisdom/ability"},
                {"stage": "Return", "description": f"{character.name} shares their growth with others"}
            ]
        elif target_arc == CharacterArc.REDEMPTION:
            milestones = [
                {"stage": "Recognition", "description": f"{character.name} acknowledges their mistakes"},
                {"stage": "First Steps", "description": f"{character.name} makes initial efforts to change"},
                {"stage": "Commitment", "description": f"{character.name} fully commits to redemption"},
                {"stage": "Redemption", "description": f"{character.name} achieves redemption through action"}
            ]
        
        return milestones

    async def create_relationship(self, character1_id: str, character2_id: str, 
                                relationship_type: str, strength: int, description: str) -> Dict[str, Any]:
        relationship_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO character_relationships VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            relationship_id, character1_id, character2_id,
            relationship_type, strength, description, "[]",
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "relationship_id": relationship_id,
            "type": relationship_type,
            "strength": strength,
            "description": description
        }

    async def generate_dialogue_sample(self, character_id: str, situation: str) -> Dict[str, Any]:
        character = await self.get_character(character_id)
        if not character:
            return {"error": "Character not found"}
        
        dialogue_lines = self._generate_character_dialogue(character, situation)
        
        return {
            "character_name": character.name,
            "situation": situation,
            "dialogue": dialogue_lines,
            "style_notes": character.dialogue_style
        }

    def _generate_character_dialogue(self, character: Character, situation: str) -> List[str]:
        lines = []
        style = character.dialogue_style
        
        base_responses = {
            "conflict": [
                "I won't stand for this.",
                "There has to be another way.",
                "You're making a mistake."
            ],
            "friendship": [
                "I'm glad you're here.",
                "We make a good team.",
                "You can count on me."
            ],
            "discovery": [
                "This changes everything.",
                "I never expected this.",
                "What does this mean?"
            ]
        }
        
        situation_key = "conflict" if "fight" in situation.lower() or "argue" in situation.lower() else \
                       "friendship" if "friend" in situation.lower() or "ally" in situation.lower() else \
                       "discovery"
        
        base_line = random.choice(base_responses.get(situation_key, ["Interesting..."]))
        
        # Modify based on character traits
        if character.traits["humor"].value > 7:
            base_line += " *chuckles*"
        if character.personality_type == PersonalityType.MENTOR:
            base_line = f"Consider this: {base_line}"
        elif character.personality_type == PersonalityType.TRICKSTER:
            base_line = f"Well, well... {base_line}"
        
        lines.append(base_line)
        
        # Add follow-up based on personality
        if character.personality_type == PersonalityType.HERO:
            lines.append("We have to do what's right.")
        elif character.personality_type == PersonalityType.GUARDIAN:
            lines.append("I'll protect what matters.")
        
        return lines

if __name__ == "__main__":
    async def main():
        char_tools = CharacterDevelopmentTools()
        
        # Create sample characters
        hero = await char_tools.create_character("Elena Brightblade", "hero")
        mentor = await char_tools.create_character("Master Aldric", "mentor")
        
        print(f"Created hero: {hero.name} - {hero.background.motivation}")
        print(f"Created mentor: {mentor.name} - {mentor.background.origin}")
        
        # Develop character arc
        arc = await char_tools.develop_character_arc(hero.id, CharacterArc.GROWTH)
        print(f"\nDeveloped growth arc for {hero.name}:")
        for milestone in arc["milestones"]:
            print(f"  - {milestone['stage']}: {milestone['description']}")
        
        # Generate dialogue
        dialogue = await char_tools.generate_dialogue_sample(hero.id, "facing a difficult moral choice")
        print(f"\nDialogue sample for {dialogue['character_name']}:")
        for line in dialogue["dialogue"]:
            print(f"  {dialogue['character_name']}: \"{line}\"")
    
    asyncio.run(main())