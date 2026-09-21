"""
D&D 5e Rules and Data Database
Comprehensive database of D&D 5e rules, classes, races, spells, and items
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class AbilityScore(Enum):
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"

@dataclass
class Race:
    name: str
    size: str
    speed: int
    ability_score_increases: Dict[str, int]
    traits: List[str]
    languages: List[str]
    proficiencies: List[str]
    subraces: List[str] = None
    description: str = ""

@dataclass
class CharacterClass:
    name: str
    hit_die: int
    primary_abilities: List[str]
    saving_throws: List[str]
    skill_choices: int
    skill_options: List[str]
    armor_proficiencies: List[str]
    weapon_proficiencies: List[str]
    tool_proficiencies: List[str]
    equipment: Dict[str, Any]
    features: Dict[int, List[str]]  # Level -> Features
    spellcasting: Optional[Dict[str, Any]] = None
    subclass_levels: List[int] = None
    description: str = ""

@dataclass
class Background:
    name: str
    skill_proficiencies: List[str]
    languages: Optional[int]
    tools: List[str]
    equipment: List[str]
    feature: str
    suggested_characteristics: Dict[str, List[str]]
    description: str = ""

@dataclass
class Spell:
    name: str
    level: int
    school: str
    casting_time: str
    range: str
    components: List[str]
    duration: str
    description: str
    classes: List[str]
    damage: Optional[str] = None
    save: Optional[str] = None
    concentration: bool = False
    ritual: bool = False

class DnDDatabase:
    def __init__(self):
        self.races = self._load_races()
        self.classes = self._load_classes()
        self.backgrounds = self._load_backgrounds()
        self.spells = self._load_spells()
        self.skills = self._load_skills()
        self.equipment = self._load_equipment()
        
    def _load_races(self) -> Dict[str, Race]:
        """Load D&D 5e races"""
        return {
            "human": Race(
                name="Human",
                size="Medium",
                speed=30,
                ability_score_increases={"all": 1},
                traits=["Extra Language", "Extra Skill"],
                languages=["Common"],
                proficiencies=[],
                description="Versatile and adaptable, humans are the most common race."
            ),
            "elf": Race(
                name="Elf",
                size="Medium", 
                speed=30,
                ability_score_increases={"dexterity": 2},
                traits=["Darkvision", "Keen Senses", "Fey Ancestry", "Trance"],
                languages=["Common", "Elvish"],
                proficiencies=["Perception"],
                subraces=["High Elf", "Wood Elf", "Drow"],
                description="Graceful and long-lived, elves are masters of magic and nature."
            ),
            "dwarf": Race(
                name="Dwarf",
                size="Medium",
                speed=25,
                ability_score_increases={"constitution": 2},
                traits=["Darkvision", "Dwarven Resilience", "Stonecunning"],
                languages=["Common", "Dwarvish"],
                proficiencies=["Battleaxe", "Handaxe", "Light Hammer", "Warhammer"],
                subraces=["Hill Dwarf", "Mountain Dwarf"],
                description="Hardy and traditional, dwarves are master craftsmen and warriors."
            ),
            "halfling": Race(
                name="Halfling",
                size="Small",
                speed=25,
                ability_score_increases={"dexterity": 2},
                traits=["Lucky", "Brave", "Halfling Nimbleness"],
                languages=["Common", "Halfling"],
                proficiencies=[],
                subraces=["Lightfoot", "Stout"],
                description="Small but brave, halflings value comfort and community."
            ),
            "dragonborn": Race(
                name="Dragonborn",
                size="Medium",
                speed=30,
                ability_score_increases={"strength": 2, "charisma": 1},
                traits=["Draconic Ancestry", "Breath Weapon", "Damage Resistance"],
                languages=["Common", "Draconic"],
                proficiencies=[],
                description="Proud dragon-like humanoids with elemental breath weapons."
            ),
            "gnome": Race(
                name="Gnome",
                size="Small",
                speed=25,
                ability_score_increases={"intelligence": 2},
                traits=["Darkvision", "Gnome Cunning"],
                languages=["Common", "Gnomish"],
                proficiencies=[],
                subraces=["Forest Gnome", "Rock Gnome"],
                description="Small and curious, gnomes are natural inventors and spellcasters."
            ),
            "half-elf": Race(
                name="Half-Elf",
                size="Medium",
                speed=30,
                ability_score_increases={"charisma": 2, "choice": 1},
                traits=["Darkvision", "Fey Ancestry", "Extra Skill Versatility"],
                languages=["Common", "Elvish"],
                proficiencies=[],
                description="Caught between two worlds, half-elves are versatile and charismatic."
            ),
            "half-orc": Race(
                name="Half-Orc",
                size="Medium",
                speed=30,
                ability_score_increases={"strength": 2, "constitution": 1},
                traits=["Darkvision", "Relentless Endurance", "Savage Attacks"],
                languages=["Common", "Orc"],
                proficiencies=["Intimidation"],
                description="Strong and determined, half-orcs struggle with their dual heritage."
            ),
            "tiefling": Race(
                name="Tiefling",
                size="Medium",
                speed=30,
                ability_score_increases={"charisma": 2, "intelligence": 1},
                traits=["Darkvision", "Hellish Resistance", "Infernal Legacy"],
                languages=["Common", "Infernal"],
                proficiencies=[],
                description="Bearing infernal heritage, tieflings face prejudice but possess inner fire."
            )
        }
    
    def _load_classes(self) -> Dict[str, CharacterClass]:
        """Load D&D 5e classes"""
        return {
            "fighter": CharacterClass(
                name="Fighter",
                hit_die=10,
                primary_abilities=["Strength", "Dexterity"],
                saving_throws=["Strength", "Constitution"],
                skill_choices=2,
                skill_options=["Acrobatics", "Animal Handling", "Athletics", "History", 
                             "Insight", "Intimidation", "Perception", "Survival"],
                armor_proficiencies=["Light", "Medium", "Heavy", "Shields"],
                weapon_proficiencies=["Simple", "Martial"],
                tool_proficiencies=[],
                equipment={
                    "armor": "Chain mail or leather armor",
                    "weapons": "Martial weapon and shield or two martial weapons",
                    "tools": "None",
                    "other": "Light crossbow and 20 bolts, explorer's pack"
                },
                features={
                    1: ["Fighting Style", "Second Wind"],
                    2: ["Action Surge"],
                    3: ["Martial Archetype"],
                    4: ["Ability Score Improvement"],
                    5: ["Extra Attack"],
                    6: ["Ability Score Improvement"],
                    7: ["Martial Archetype Feature"],
                    8: ["Ability Score Improvement"],
                    9: ["Indomitable"],
                    10: ["Martial Archetype Feature"],
                    11: ["Extra Attack (2)"],
                    12: ["Ability Score Improvement"],
                    13: ["Indomitable (2 uses)"],
                    14: ["Ability Score Improvement"],
                    15: ["Martial Archetype Feature"],
                    16: ["Ability Score Improvement"],
                    17: ["Action Surge (2 uses)", "Indomitable (3 uses)"],
                    18: ["Martial Archetype Feature"],
                    19: ["Ability Score Improvement"],
                    20: ["Extra Attack (3)"]
                },
                subclass_levels=[3, 7, 10, 15, 18],
                description="Master of martial combat, skilled with a variety of weapons and armor."
            ),
            "wizard": CharacterClass(
                name="Wizard",
                hit_die=6,
                primary_abilities=["Intelligence"],
                saving_throws=["Intelligence", "Wisdom"],
                skill_choices=2,
                skill_options=["Arcana", "History", "Insight", "Investigation", 
                             "Medicine", "Religion"],
                armor_proficiencies=[],
                weapon_proficiencies=["Daggers", "Darts", "Slings", "Quarterstaffs", "Light Crossbows"],
                tool_proficiencies=[],
                equipment={
                    "armor": "None",
                    "weapons": "Quarterstaff or dagger",
                    "tools": "None",
                    "other": "Spellbook, component pouch, scholar's pack"
                },
                features={
                    1: ["Spellcasting", "Arcane Recovery"],
                    2: ["Arcane Tradition"],
                    3: [],
                    4: ["Ability Score Improvement"],
                    5: [],
                    6: ["Arcane Tradition Feature"],
                    7: [],
                    8: ["Ability Score Improvement"],
                    9: [],
                    10: ["Arcane Tradition Feature"],
                    11: [],
                    12: ["Ability Score Improvement"],
                    13: [],
                    14: ["Arcane Tradition Feature"],
                    15: [],
                    16: ["Ability Score Improvement"],
                    17: [],
                    18: ["Spell Mastery"],
                    19: ["Ability Score Improvement"],
                    20: ["Signature Spells"]
                },
                spellcasting={
                    "ability": "Intelligence",
                    "ritual_casting": True,
                    "spellcasting_focus": "Arcane Focus",
                    "spells_known": "Spellbook",
                    "cantrips": {1: 3, 4: 4, 10: 5},
                    "spell_slots": {
                        1: [2, 0, 0, 0, 0, 0, 0, 0, 0],
                        2: [3, 0, 0, 0, 0, 0, 0, 0, 0],
                        3: [4, 2, 0, 0, 0, 0, 0, 0, 0],
                        4: [4, 3, 0, 0, 0, 0, 0, 0, 0],
                        5: [4, 3, 2, 0, 0, 0, 0, 0, 0]
                    }
                },
                subclass_levels=[2, 6, 10, 14],
                description="Master of arcane magic, learning spells through study and practice."
            ),
            "rogue": CharacterClass(
                name="Rogue",
                hit_die=8,
                primary_abilities=["Dexterity"],
                saving_throws=["Dexterity", "Intelligence"],
                skill_choices=4,
                skill_options=["Acrobatics", "Athletics", "Deception", "Insight", 
                             "Intimidation", "Investigation", "Perception", "Performance",
                             "Persuasion", "Sleight of Hand", "Stealth"],
                armor_proficiencies=["Light"],
                weapon_proficiencies=["Simple", "Hand crossbows", "Longswords", 
                                    "Rapiers", "Shortswords"],
                tool_proficiencies=["Thieves' tools"],
                equipment={
                    "armor": "Leather armor",
                    "weapons": "Rapier or shortsword, shortbow and quiver of 20 arrows",
                    "tools": "Thieves' tools",
                    "other": "Burglar's pack, two daggers"
                },
                features={
                    1: ["Expertise", "Sneak Attack", "Thieves' Cant"],
                    2: ["Cunning Action"],
                    3: ["Roguish Archetype"],
                    4: ["Ability Score Improvement"],
                    5: ["Uncanny Dodge"],
                    6: ["Expertise"],
                    7: ["Evasion"],
                    8: ["Ability Score Improvement"],
                    9: ["Roguish Archetype Feature"],
                    10: ["Ability Score Improvement"],
                    11: ["Reliable Talent"],
                    12: ["Ability Score Improvement"],
                    13: ["Roguish Archetype Feature"],
                    14: ["Blindsense"],
                    15: ["Slippery Mind"],
                    16: ["Ability Score Improvement"],
                    17: ["Roguish Archetype Feature"],
                    18: ["Elusive"],
                    19: ["Ability Score Improvement"],
                    20: ["Stroke of Luck"]
                },
                subclass_levels=[3, 9, 13, 17],
                description="Master of stealth and precision, skilled in subterfuge and sneak attacks."
            )
        }
    
    def _load_backgrounds(self) -> Dict[str, Background]:
        """Load D&D 5e backgrounds"""
        return {
            "acolyte": Background(
                name="Acolyte",
                skill_proficiencies=["Insight", "Religion"],
                languages=2,
                tools=[],
                equipment=["Holy symbol", "Prayer book", "5 sticks of incense", 
                          "Vestments", "Common clothes", "Belt pouch with 15 gp"],
                feature="Shelter of the Faithful",
                suggested_characteristics={
                    "personality_traits": [
                        "I idolize a particular hero of my faith.",
                        "I can find common ground between the fiercest enemies.",
                        "I see omens in every event and action.",
                        "Nothing can shake my optimistic attitude."
                    ],
                    "ideals": [
                        "Tradition. The ancient traditions must be preserved.",
                        "Charity. I always try to help those in need.",
                        "Change. We must help bring about the changes the gods desire.",
                        "Power. I hope to one day rise to the top of my faith's hierarchy."
                    ],
                    "bonds": [
                        "I would die to recover an ancient relic of my faith.",
                        "I will someday get revenge on the corrupt temple hierarchy.",
                        "I owe my life to the priest who took me in when my parents died.",
                        "Everything I do is for the common people."
                    ],
                    "flaws": [
                        "I judge others harshly, and myself even more severely.",
                        "I put too much trust in those who wield power within my temple's hierarchy.",
                        "My piety sometimes leads me to blindly trust those that profess faith in my god.",
                        "I am inflexible in my thinking."
                    ]
                },
                description="You have spent your life in service to a temple of a specific god."
            ),
            "criminal": Background(
                name="Criminal",
                skill_proficiencies=["Deception", "Stealth"],
                languages=0,
                tools=["Gaming set", "Thieves' tools"],
                equipment=["Crowbar", "Dark common clothes with hood", "Belt pouch with 15 gp"],
                feature="Criminal Contact",
                suggested_characteristics={
                    "personality_traits": [
                        "I always have a plan for what to do when things go wrong.",
                        "I am always calm, no matter what the situation.",
                        "The first thing I do in a new place is note the locations of everything valuable.",
                        "I would rather make a new friend than a new enemy."
                    ],
                    "ideals": [
                        "Honor. I don't steal from others in the trade.",
                        "Freedom. Chains are meant to be broken, as are those who would forge them.",
                        "Charity. I steal from the wealthy so that I can help people in need.",
                        "Greed. I will do whatever it takes to become wealthy."
                    ],
                    "bonds": [
                        "I'm trying to pay off an old debt I owe to a generous benefactor.",
                        "My ill-gotten gains go to support my family.",
                        "Something important was taken from me, and I aim to steal it back.",
                        "I will become the greatest thief that ever lived."
                    ],
                    "flaws": [
                        "When I see something valuable, I can't think about anything but how to steal it.",
                        "When faced with a choice between money and my friends, I usually choose the money.",
                        "If there's a plan, I'll forget it. If I don't forget it, I'll ignore it.",
                        "I have a 'tell' that reveals when I'm lying."
                    ]
                },
                description="You are an experienced criminal with a history of breaking the law."
            ),
            "folk_hero": Background(
                name="Folk Hero",
                skill_proficiencies=["Animal Handling", "Survival"],
                languages=0,
                tools=["Artisan's tools", "Vehicles (land)"],
                equipment=["Artisan's tools", "Shovel", "Iron pot", "Common clothes", 
                          "Belt pouch with 10 gp"],
                feature="Rustic Hospitality",
                suggested_characteristics={
                    "personality_traits": [
                        "I judge people by their actions, not their words.",
                        "If someone is in trouble, I'm always ready to lend help.",
                        "When I set my mind to something, I follow through no matter what gets in my way.",
                        "I have a strong sense of fair play and always try to find the most equitable solution."
                    ],
                    "ideals": [
                        "Respect. People deserve to be treated with dignity and respect.",
                        "Fairness. No one should get preferential treatment before the law.",
                        "Freedom. Tyrants must not be allowed to oppress the people.",
                        "Might. If I become strong, I can take what I want—what I deserve."
                    ],
                    "bonds": [
                        "I have a family, but I have no idea where they are.",
                        "I worked the land, I love the land, and I will protect the land.",
                        "A proud noble once gave me a horrible beating, and I will take my revenge.",
                        "My tools are symbols of my past life, and I carry them so that I will never forget."
                    ],
                    "flaws": [
                        "The tyrant who rules my land will stop at nothing to see me killed.",
                        "I'm convinced of the significance of my destiny, and blind to my shortcomings.",
                        "The people who knew me when I was young know my shameful secret.",
                        "I have trouble trusting in my allies."
                    ]
                },
                description="You come from a humble social rank, but you are destined for much more."
            )
        }
    
    def _load_spells(self) -> Dict[str, Spell]:
        """Load D&D 5e spells"""
        return {
            "fireball": Spell(
                name="Fireball",
                level=3,
                school="Evocation",
                casting_time="1 action",
                range="150 feet",
                components=["V", "S", "M"],
                duration="Instantaneous",
                description="A bright streak flashes from your pointing finger to a point within range and blossoms with a low roar into an explosion of flame.",
                classes=["Wizard", "Sorcerer"],
                damage="8d6 fire",
                save="Dexterity"
            ),
            "magic_missile": Spell(
                name="Magic Missile",
                level=1,
                school="Evocation", 
                casting_time="1 action",
                range="120 feet",
                components=["V", "S"],
                duration="Instantaneous",
                description="You create three glowing darts of magical force that automatically hit their targets.",
                classes=["Wizard", "Sorcerer"],
                damage="1d4+1 force per missile"
            ),
            "cure_wounds": Spell(
                name="Cure Wounds",
                level=1,
                school="Evocation",
                casting_time="1 action", 
                range="Touch",
                components=["V", "S"],
                duration="Instantaneous",
                description="A creature you touch regains hit points equal to 1d8 + your spellcasting ability modifier.",
                classes=["Cleric", "Druid", "Paladin", "Ranger"],
                damage="1d8 + modifier healing"
            )
        }
    
    def _load_skills(self) -> Dict[str, Dict[str, str]]:
        """Load D&D 5e skills"""
        return {
            "Acrobatics": {"ability": "Dexterity", "description": "Stay on your feet in tricky situations"},
            "Animal Handling": {"ability": "Wisdom", "description": "Calm or train animals"},
            "Arcana": {"ability": "Intelligence", "description": "Knowledge of magic and magical phenomena"},
            "Athletics": {"ability": "Strength", "description": "Physical challenges like climbing and swimming"},
            "Deception": {"ability": "Charisma", "description": "Hide the truth with words or actions"},
            "History": {"ability": "Intelligence", "description": "Knowledge of historical events and figures"},
            "Insight": {"ability": "Wisdom", "description": "Determine the intentions of others"},
            "Intimidation": {"ability": "Charisma", "description": "Influence others through threats"},
            "Investigation": {"ability": "Intelligence", "description": "Look for clues and make deductions"},
            "Medicine": {"ability": "Wisdom", "description": "Stabilize the dying and diagnose illness"},
            "Nature": {"ability": "Intelligence", "description": "Knowledge of terrain, plants, animals"},
            "Perception": {"ability": "Wisdom", "description": "Spot, hear, or detect the presence of something"},
            "Performance": {"ability": "Charisma", "description": "Delight an audience with music, dance, or storytelling"},
            "Persuasion": {"ability": "Charisma", "description": "Influence others through tact and social grace"},
            "Religion": {"ability": "Intelligence", "description": "Knowledge of deities, rites, and holy symbols"},
            "Sleight of Hand": {"ability": "Dexterity", "description": "Plant or conceal objects on others"},
            "Stealth": {"ability": "Dexterity", "description": "Conceal yourself from enemies"},
            "Survival": {"ability": "Wisdom", "description": "Follow tracks, navigate, and forage"}
        }
    
    def _load_equipment(self) -> Dict[str, Dict[str, Any]]:
        """Load D&D 5e equipment"""
        return {
            "weapons": {
                "longsword": {
                    "name": "Longsword",
                    "damage": "1d8",
                    "damage_type": "slashing",
                    "weight": 3,
                    "cost": "15 gp",
                    "properties": ["Versatile (1d10)"]
                },
                "shortbow": {
                    "name": "Shortbow",
                    "damage": "1d6",
                    "damage_type": "piercing",
                    "weight": 2,
                    "cost": "25 gp",
                    "range": "80/320",
                    "properties": ["Ammunition", "Two-handed"]
                }
            },
            "armor": {
                "leather": {
                    "name": "Leather Armor",
                    "ac": 11,
                    "dex_bonus": True,
                    "weight": 10,
                    "cost": "10 gp",
                    "type": "Light"
                },
                "chain_mail": {
                    "name": "Chain Mail",
                    "ac": 16,
                    "dex_bonus": False,
                    "weight": 55,
                    "cost": "75 gp",
                    "type": "Heavy",
                    "strength_requirement": 13
                }
            }
        }

    def get_race(self, race_name: str) -> Optional[Race]:
        """Get race by name"""
        return self.races.get(race_name.lower())
    
    def get_class(self, class_name: str) -> Optional[CharacterClass]:
        """Get class by name"""
        return self.classes.get(class_name.lower())
    
    def get_background(self, background_name: str) -> Optional[Background]:
        """Get background by name"""
        return self.backgrounds.get(background_name.lower())
    
    def get_spell(self, spell_name: str) -> Optional[Spell]:
        """Get spell by name"""
        return self.spells.get(spell_name.lower().replace(" ", "_"))
    
    def get_spells_by_class(self, class_name: str, level: int = None) -> List[Spell]:
        """Get all spells available to a class"""
        spells = []
        for spell in self.spells.values():
            if class_name.title() in spell.classes:
                if level is None or spell.level <= level:
                    spells.append(spell)
        return spells
    
    def calculate_ability_modifier(self, score: int) -> int:
        """Calculate ability modifier from ability score"""
        return (score - 10) // 2
    
    def get_proficiency_bonus(self, level: int) -> int:
        """Get proficiency bonus by character level"""
        return 2 + ((level - 1) // 4)