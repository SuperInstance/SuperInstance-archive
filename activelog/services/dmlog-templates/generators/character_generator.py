"""
Character Backstory Generator

Generates detailed character backstories with relationships, motivations,
secrets, and plot hooks for D&D characters.
"""

import random
from typing import List, Dict, Any, Optional

from ..models.character import (
    Backstory, Background, Personality, Relationship, Motivation, Secret,
    Character, CharacterConcept, NPCProfile
)
from ..models.base import SkillType
from ..config import BACKSTORY_CONFIG
from .base_generator import BaseGenerator


class CharacterGenerator(BaseGenerator):
    """Generates character backstories and NPCs"""
    
    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.backgrounds_data = self._load_backgrounds_data()
        self.personality_data = self._load_personality_data()
        self.relationship_data = self._load_relationship_data()
        self.motivation_data = self._load_motivation_data()
        self.names_data = self._load_names_data()
    
    def _load_backgrounds_data(self) -> Dict[str, Any]:
        """Load background generation data"""
        return {
            "backgrounds": {
                "acolyte": {
                    "professions": ["priest", "monk", "temple servant", "missionary"],
                    "social_classes": ["common", "middle"],
                    "life_events": [
                        "Experienced a divine vision",
                        "Lost faith temporarily",
                        "Discovered a religious artifact",
                        "Witnessed a miracle"
                    ],
                    "skills": [SkillType.INSIGHT, SkillType.RELIGION]
                },
                "criminal": {
                    "professions": ["thief", "smuggler", "fence", "con artist"],
                    "social_classes": ["poor", "common"],
                    "life_events": [
                        "Pulled off a legendary heist",
                        "Was betrayed by partner",
                        "Went to prison",
                        "Reformed after tragedy"
                    ],
                    "skills": [SkillType.DECEPTION, SkillType.STEALTH]
                },
                "folk_hero": {
                    "professions": ["blacksmith", "farmer", "miller", "innkeeper"],
                    "social_classes": ["common", "poor"],
                    "life_events": [
                        "Stood up to a tyrant",
                        "Saved village from disaster",
                        "Led a rebellion",
                        "Discovered corruption"
                    ],
                    "skills": [SkillType.ANIMAL_HANDLING, SkillType.SURVIVAL]
                },
                "noble": {
                    "professions": ["courtier", "politician", "diplomat", "military officer"],
                    "social_classes": ["noble", "upper"],
                    "life_events": [
                        "Lost family fortune",
                        "Involved in political scandal",
                        "Arranged marriage fell through",
                        "Inherited unexpected title"
                    ],
                    "skills": [SkillType.HISTORY, SkillType.PERSUASION]
                },
                "sage": {
                    "professions": ["scholar", "researcher", "librarian", "tutor"],
                    "social_classes": ["middle", "upper"],
                    "life_events": [
                        "Made groundbreaking discovery",
                        "Lost important research",
                        "Found ancient text",
                        "Debunked false theory"
                    ],
                    "skills": [SkillType.ARCANA, SkillType.HISTORY]
                },
                "soldier": {
                    "professions": ["guard", "mercenary", "officer", "veteran"],
                    "social_classes": ["common", "middle"],
                    "life_events": [
                        "Survived major battle",
                        "Lost entire unit",
                        "Received medal of honor",
                        "Court-martialed unfairly"
                    ],
                    "skills": [SkillType.ATHLETICS, SkillType.INTIMIDATION]
                }
            },
            "social_classes": {
                "destitute": {"wealth": "none", "property": [], "education": "none"},
                "poor": {"wealth": "minimal", "property": ["simple clothes"], "education": "basic"},
                "common": {"wealth": "modest", "property": ["home", "tools"], "education": "basic"},
                "middle": {"wealth": "comfortable", "property": ["house", "business"], "education": "apprentice"},
                "upper": {"wealth": "wealthy", "property": ["manor", "servants"], "education": "scholarly"},
                "noble": {"wealth": "rich", "property": ["estate", "title"], "education": "expert"}
            }
        }
    
    def _load_personality_data(self) -> Dict[str, Any]:
        """Load personality trait data"""
        return {
            "traits": {
                "positive": [
                    "Brave and courageous", "Loyal and trustworthy", "Wise and insightful",
                    "Kind and compassionate", "Clever and quick-witted", "Honest and forthright",
                    "Determined and persistent", "Charismatic and charming", "Patient and understanding",
                    "Generous and giving", "Optimistic and hopeful", "Creative and imaginative"
                ],
                "negative": [
                    "Stubborn and inflexible", "Reckless and impulsive", "Suspicious and paranoid",
                    "Arrogant and prideful", "Greedy and selfish", "Cowardly and fearful",
                    "Dishonest and deceptive", "Lazy and unmotivated", "Cruel and callous",
                    "Jealous and envious", "Quick-tempered", "Pessimistic and gloomy"
                ],
                "neutral": [
                    "Quiet and reserved", "Curious and inquisitive", "Methodical and organized",
                    "Spontaneous and unpredictable", "Diplomatic and tactful", "Direct and blunt",
                    "Cautious and careful", "Confident and assertive", "Humble and modest",
                    "Independent and self-reliant", "Social and outgoing", "Serious and focused"
                ]
            },
            "ideals": {
                "good": ["Justice", "Freedom", "Honor", "Compassion", "Truth", "Beauty"],
                "evil": ["Power", "Domination", "Revenge", "Greed", "Destruction", "Corruption"],
                "lawful": ["Order", "Tradition", "Responsibility", "Duty", "Hierarchy", "Stability"],
                "chaotic": ["Independence", "Change", "Creativity", "Freedom", "Spontaneity", "Innovation"],
                "neutral": ["Balance", "Knowledge", "Survival", "Nature", "Self-improvement", "Pragmatism"]
            },
            "bonds": [
                "My family means everything to me",
                "I owe my life to someone who saved me",
                "I will prove myself worthy of my mentor's teaching",
                "I seek to restore honor to my family name",
                "My hometown will always be my true home",
                "I carry a reminder of someone important to me",
                "I am searching for someone dear to me",
                "I will return to reclaim what was taken from me"
            ],
            "flaws": [
                "I have a weakness for the vices of the city",
                "I am inflexible in my thinking",
                "I am suspicious of strangers and expect the worst",
                "I have trouble trusting members of other races",
                "I put too much trust in those who wield power",
                "I am slow to make friends and quick to suspect treachery",
                "I have a dark secret that could ruin me",
                "I let my need to win arguments overshadow friendships"
            ]
        }
    
    def _load_relationship_data(self) -> Dict[str, Any]:
        """Load relationship generation data"""
        return {
            "types": {
                "family": {
                    "relationships": ["parent", "sibling", "child", "spouse", "grandparent", "cousin"],
                    "common_hooks": [
                        "Family member in danger",
                        "Family secret revealed",
                        "Inheritance dispute",
                        "Family reunion needed"
                    ]
                },
                "friend": {
                    "relationships": ["childhood friend", "traveling companion", "former colleague", "neighbor"],
                    "common_hooks": [
                        "Friend needs help",
                        "Shared adventure opportunity",
                        "Friend has important information",
                        "Reunion after long separation"
                    ]
                },
                "mentor": {
                    "relationships": ["teacher", "master", "guide", "patron"],
                    "common_hooks": [
                        "Final lesson to be learned",
                        "Mentor's legacy in danger",
                        "Following mentor's example",
                        "Surpassing mentor's achievements"
                    ]
                },
                "rival": {
                    "relationships": ["competitor", "former friend", "professional rival", "romantic rival"],
                    "common_hooks": [
                        "Competition escalates",
                        "Rival seeks revenge",
                        "Forced to work together",
                        "Rival in trouble"
                    ]
                },
                "enemy": {
                    "relationships": ["former friend", "betrayer", "oppressor", "victim of character's actions"],
                    "common_hooks": [
                        "Enemy seeks revenge",
                        "Enemy threatens innocents",
                        "Past comes back to haunt",
                        "Opportunity for reconciliation"
                    ]
                }
            },
            "strengths": ["weak", "moderate", "strong", "intense"],
            "statuses": ["active", "distant", "severed", "complicated"]
        }
    
    def _load_motivation_data(self) -> Dict[str, Any]:
        """Load motivation generation data"""
        return {
            "types": {
                "revenge": {
                    "origins": [
                        "Someone killed a loved one",
                        "Betrayed by trusted ally",
                        "Lost everything to villain",
                        "Wrongfully accused and punished"
                    ],
                    "conflicts": ["Revenge vs justice", "Collateral damage", "Becoming what you hate"],
                    "resolutions": ["Justice served", "Forgiveness found", "Moving on", "Revenge completed"]
                },
                "redemption": {
                    "origins": [
                        "Past crimes haunt them",
                        "Failed someone important",
                        "Made terrible mistake",
                        "Led others to doom"
                    ],
                    "conflicts": ["Past catching up", "Self-doubt", "Others' lack of trust"],
                    "resolutions": ["Forgiveness earned", "Amends made", "Peace found", "New purpose"]
                },
                "knowledge": {
                    "origins": [
                        "Mysterious family history",
                        "Ancient prophecy mentions them",
                        "Witnessed something unexplained",
                        "Found cryptic message"
                    ],
                    "conflicts": ["Dangerous knowledge", "Knowledge comes at cost", "Others seek same knowledge"],
                    "resolutions": ["Truth revealed", "Mystery solved", "Knowledge shared", "Wisdom gained"]
                },
                "power": {
                    "origins": [
                        "Felt powerless to help",
                        "Witnessed abuse of power",
                        "Born to responsibility",
                        "Power thrust upon them"
                    ],
                    "conflicts": ["Power corrupts", "Responsibility burden", "Others fear your power"],
                    "resolutions": ["Power used wisely", "Leadership accepted", "Balance found", "Power shared"]
                }
            }
        }
    
    def _load_names_data(self) -> Dict[str, Any]:
        """Load name generation data"""
        return {
            "fantasy": {
                "male": [
                    "Aerdrie", "Beiro", "Carric", "Dayereth", "Enna", "Galinndan",
                    "Halimath", "Immeral", "Lamlis", "Mindartis", "Nutae", "Paelynn"
                ],
                "female": [
                    "Adrie", "Birel", "Caelynn", "Dara", "Enna", "Galinndan",
                    "Hadarai", "Immeral", "Ivellios", "Korfel", "Lamlis", "Mindartis"
                ],
                "surnames": [
                    "Amakir", "Amakra", "Galanodel", "Holimion", "Liadon",
                    "Meliamne", "Nailo", "Siannodel", "Xiloscient", "Alderleaf"
                ]
            },
            "human": {
                "male": ["Abeir", "Borivik", "Fodel", "Glar", "Grigor", "Igan", "Ivor", "Kosef"],
                "female": ["Alethra", "Kara", "Katernin", "Mara", "Natali", "Olma", "Tana", "Zora"],
                "surnames": ["Bersk", "Chernin", "Dotsk", "Kulenov", "Marsk", "Nemetsk", "Shemov", "Starag"]
            }
        }
    
    async def generate_backstory(self, character_name: str = "", character_class: str = "",
                               character_race: str = "", level: int = 1) -> Backstory:
        """Generate a complete character backstory"""
        
        # Generate name if not provided
        if not character_name:
            character_name = self._generate_character_name(character_race)
        
        # Generate background
        background = await self._generate_background()
        
        # Generate personality
        personality = await self._generate_personality()
        
        # Generate relationships
        relationships = await self._generate_relationships(background)
        
        # Generate motivations
        motivations = await self._generate_motivations()
        
        # Generate secrets
        secrets = await self._generate_secrets(background, relationships)
        
        # Create backstory
        backstory = Backstory(
            name=f"{character_name}'s Backstory",
            description=f"Complete backstory for {character_name}",
            character_name=character_name,
            character_class=character_class,
            character_race=character_race,
            character_level=level,
            background=background,
            personality=personality,
            relationships=relationships,
            motivations=motivations,
            secrets=secrets
        )
        
        # Generate story elements
        backstory.origin_story = await self._generate_origin_story(backstory)
        backstory.defining_moment = await self._generate_defining_moment(backstory)
        backstory.call_to_adventure = await self._generate_call_to_adventure(backstory)
        
        # Generate hooks
        backstory.personal_hooks = await self._generate_personal_hooks(backstory)
        backstory.relationship_hooks = await self._generate_relationship_hooks(relationships)
        backstory.background_hooks = await self._generate_background_hooks(background)
        
        # Generate world connections
        backstory.faction_affiliations = await self._generate_faction_affiliations(background)
        backstory.reputation = await self._generate_reputation(background, personality)
        
        # Generate DM notes
        backstory.roleplay_notes = await self._generate_roleplay_notes(personality)
        backstory.plot_potential = await self._generate_plot_potential(backstory)
        
        return backstory
    
    def _generate_character_name(self, race: str = "") -> str:
        """Generate a character name based on race"""
        race_lower = race.lower() if race else "fantasy"
        
        # Map race names to name categories
        race_mappings = {
            "human": "human",
            "elf": "fantasy",
            "dwarf": "fantasy", 
            "halfling": "fantasy",
            "dragonborn": "fantasy",
            "gnome": "fantasy",
            "half-elf": "fantasy",
            "half-orc": "fantasy",
            "tiefling": "fantasy"
        }
        
        name_category = race_mappings.get(race_lower, "fantasy")
        gender = self.rng.choice(["male", "female"])
        
        names = self.names_data.get(name_category, self.names_data["fantasy"])
        first_name = self.rng.choice(names.get(gender, names.get("male", ["Adventurer"])))
        
        if "surnames" in names and self.rng.random() > 0.3:  # 70% chance of surname
            surname = self.rng.choice(names["surnames"])
            return f"{first_name} {surname}"
        
        return first_name
    
    async def _generate_background(self) -> Background:
        """Generate character background"""
        # Choose background based on weights
        bg_name = self.weighted_choice(BACKSTORY_CONFIG["background_weights"])
        bg_data = self.backgrounds_data["backgrounds"].get(bg_name, {})
        
        # Generate basic info
        background = Background(
            name=f"{bg_name.title()} Background",
            official_background=bg_name,
            profession=self.rng.choice(bg_data.get("professions", ["adventurer"])),
            social_class=self.rng.choice(bg_data.get("social_classes", ["common"])),
            education_level=self.rng.choice(["basic", "apprentice", "scholarly"])
        )
        
        # Generate life details
        background.birthplace = self._generate_place_name()
        background.current_home = self._generate_place_name() if self.rng.random() > 0.6 else background.birthplace
        background.family_status = self.rng.choice(["intact", "scattered", "deceased", "complicated"])
        background.marital_status = self.rng.choice(["single", "married", "widowed", "complicated"])
        
        # Generate life events
        available_events = bg_data.get("life_events", ["Had an ordinary life"])
        num_events = min(self.rng.randint(1, 3), len(available_events))
        background.major_life_events = self.rng.sample(available_events, num_events)
        
        # Generate skills and knowledge
        background.learned_skills = bg_data.get("skills", [])
        background.languages_known = self._generate_languages()
        background.areas_of_expertise = [background.profession]
        
        # Generate financial status
        class_wealth = self.backgrounds_data["social_classes"][background.social_class]["wealth"]
        background.financial_status = class_wealth
        
        return background
    
    async def _generate_personality(self) -> Personality:
        """Generate character personality"""
        personality = Personality(
            name="Character Personality",
            alignment=self.rng.choice([
                "lawful_good", "neutral_good", "chaotic_good",
                "lawful_neutral", "true_neutral", "chaotic_neutral",
                "lawful_evil", "neutral_evil", "chaotic_evil"
            ])
        )
        
        # Generate traits (mix of positive, negative, and neutral)
        trait_types = ["positive", "negative", "neutral"]
        for trait_type in trait_types:
            if self.rng.random() > 0.3:  # 70% chance for each type
                available_traits = self.personality_data["traits"][trait_type]
                personality.personality_traits.append(self.rng.choice(available_traits))
        
        # Generate ideals based on alignment
        alignment_parts = personality.alignment.split('_')
        ethical_part = alignment_parts[0] if alignment_parts[0] in ["lawful", "chaotic"] else "neutral"
        moral_part = alignment_parts[-1] if alignment_parts[-1] in ["good", "evil"] else "neutral"
        
        ideal_categories = [ethical_part, moral_part] if ethical_part != moral_part else [moral_part]
        for category in ideal_categories:
            if category in self.personality_data["ideals"]:
                ideal = self.rng.choice(self.personality_data["ideals"][category])
                personality.ideals.append(ideal)
        
        # Generate bonds and flaws
        personality.bonds.append(self.rng.choice(self.personality_data["bonds"]))
        personality.flaws.append(self.rng.choice(self.personality_data["flaws"]))
        
        # Generate behavioral patterns
        personality.communication_style = self.rng.choice(["direct", "indirect", "verbose", "terse"])
        personality.conflict_resolution = self.rng.choice(["aggressive", "passive", "compromise", "avoidance"])
        personality.stress_response = self.rng.choice(["fight", "flight", "freeze", "plan"])
        personality.trust_level = self.rng.choice(["trusting", "cautious", "suspicious"])
        
        # Generate likes, dislikes, fears
        personality.likes = self._generate_likes_dislikes("likes")
        personality.dislikes = self._generate_likes_dislikes("dislikes")
        personality.fears = self._generate_fears()
        
        return personality
    
    async def _generate_relationships(self, background: Background) -> List[Relationship]:
        """Generate character relationships"""
        relationships = []
        
        # Determine number of relationships
        num_relationships = self.rng.randint(2, 5)
        
        # Generate family relationships first
        if background.family_status in ["intact", "scattered", "complicated"]:
            family_types = ["parent", "sibling", "other_family"]
            for _ in range(min(2, num_relationships)):
                rel_type = self.rng.choice(family_types)
                relationship = await self._generate_single_relationship("family", rel_type)
                relationships.append(relationship)
        
        # Generate other relationships
        remaining_slots = num_relationships - len(relationships)
        other_types = ["friend", "mentor", "rival", "enemy"]
        
        for _ in range(remaining_slots):
            rel_category = self.rng.choice(other_types)
            rel_type = self.rng.choice(
                self.relationship_data["types"][rel_category]["relationships"]
            )
            relationship = await self._generate_single_relationship(rel_category, rel_type)
            relationships.append(relationship)
        
        return relationships
    
    async def _generate_single_relationship(self, category: str, rel_type: str) -> Relationship:
        """Generate a single relationship"""
        person_name = self._generate_character_name()
        
        relationship = Relationship(
            name=f"{person_name} ({rel_type})",
            relationship_type=rel_type,
            person_name=person_name,
            person_description=self._generate_person_description(),
            relationship_strength=self.rng.choice(self.relationship_data["strengths"]),
            current_status=self.rng.choice(self.relationship_data["statuses"]),
            shared_history=self._generate_shared_history(category, rel_type),
            current_location=self._generate_place_name() if self.rng.random() > 0.4 else "unknown"
        )
        
        # Generate hooks for this relationship
        relationship.hooks = self.relationship_data["types"][category].get("common_hooks", [])[:2]
        
        return relationship
    
    async def _generate_motivations(self) -> List[Motivation]:
        """Generate character motivations"""
        motivations = []
        num_motivations = self.rng.randint(1, 3)
        
        motivation_types = list(self.motivation_data["types"].keys())
        chosen_types = self.rng.sample(motivation_types, min(num_motivations, len(motivation_types)))
        
        for mot_type in chosen_types:
            mot_data = self.motivation_data["types"][mot_type]
            
            motivation = Motivation(
                name=f"{mot_type.title()} Motivation",
                motivation_type=mot_type,
                intensity=self.rng.choice(["weak", "moderate", "strong", "obsessive"]),
                origin_story=self.rng.choice(mot_data["origins"]),
                current_relevance=self.rng.choice(["active", "dormant", "complicated"])
            )
            
            motivation.potential_conflicts = mot_data.get("conflicts", [])
            motivation.resolution_paths = mot_data.get("resolutions", [])
            
            motivations.append(motivation)
        
        return motivations
    
    async def _generate_secrets(self, background: Background, relationships: List[Relationship]) -> List[Secret]:
        """Generate character secrets"""
        secrets = []
        
        # Chance for secrets based on background and relationships
        secret_chance = 0.7
        if background.official_background in ["criminal", "charlatan"]:
            secret_chance = 0.9
        if any(rel.relationship_type == "enemy" for rel in relationships):
            secret_chance += 0.2
        
        if self.rng.random() < secret_chance:
            secret_types = ["identity", "crime", "knowledge", "curse", "debt", "shame"]
            secret_type = self.rng.choice(secret_types)
            
            secret = Secret(
                name=f"Hidden {secret_type.title()}",
                secret_type=secret_type,
                severity=self.rng.choice(["minor", "moderate", "serious", "devastating"]),
                description=self._generate_secret_description(secret_type, background)
            )
            
            # Determine who might know
            if relationships and self.rng.random() > 0.6:
                knowing_person = self.rng.choice(relationships)
                secret.who_knows.append(knowing_person.person_name)
            
            secret.consequences_if_revealed = self._generate_secret_consequences(secret_type)
            secret.clues_that_exist = self._generate_secret_clues(secret_type)
            
            secrets.append(secret)
        
        return secrets
    
    def _generate_place_name(self) -> str:
        """Generate a place name"""
        prefixes = [
            "Green", "Old", "New", "High", "Low", "North", "South", "East", "West",
            "Silver", "Gold", "Iron", "Stone", "Wood", "Fair", "Dark", "Bright"
        ]
        suffixes = [
            "ford", "burg", "haven", "town", "vale", "hill", "brook", "wood",
            "field", "bridge", "gate", "port", "mount", "ridge", "meadow"
        ]
        
        if self.rng.random() > 0.3:
            return f"{self.rng.choice(prefixes)}{self.rng.choice(suffixes)}"
        else:
            return self.rng.choice(suffixes).title()
    
    def _generate_languages(self) -> List[str]:
        """Generate known languages"""
        common_languages = ["Common"]
        other_languages = ["Elvish", "Dwarvish", "Halfling", "Orcish", "Draconic", "Giant", "Gnomish"]
        
        num_languages = self.rng.randint(1, 3)
        additional = self.rng.sample(other_languages, min(num_languages - 1, len(other_languages)))
        
        return common_languages + additional
    
    def _generate_likes_dislikes(self, category: str) -> List[str]:
        """Generate likes or dislikes"""
        items = {
            "likes": [
                "good food", "fine wine", "music", "books", "animals", "nature",
                "craftsmanship", "art", "stories", "games", "learning", "helping others"
            ],
            "dislikes": [
                "crowds", "lies", "violence", "injustice", "rudeness", "waste",
                "disorder", "loud noises", "being rushed", "dishonesty", "cruelty", "ignorance"
            ]
        }
        
        available = items.get(category, [])
        num_items = self.rng.randint(1, 3)
        return self.rng.sample(available, min(num_items, len(available)))
    
    def _generate_fears(self) -> List[str]:
        """Generate character fears"""
        fears = [
            "death", "failure", "abandonment", "heights", "darkness", "water",
            "confined spaces", "spiders", "public speaking", "being alone",
            "losing loved ones", "being forgotten", "betrayal", "powerlessness"
        ]
        
        num_fears = self.rng.randint(1, 2)
        return self.rng.sample(fears, num_fears)
    
    def _generate_person_description(self) -> str:
        """Generate a brief person description"""
        descriptors = [
            "kind-hearted", "stern", "cheerful", "mysterious", "wise", "eccentric",
            "ambitious", "gentle", "fierce", "scholarly", "practical", "artistic"
        ]
        
        professions = [
            "merchant", "farmer", "soldier", "scholar", "priest", "artisan",
            "noble", "guard", "healer", "performer", "criminal", "sailor"
        ]
        
        descriptor = self.rng.choice(descriptors)
        profession = self.rng.choice(professions)
        
        return f"A {descriptor} {profession}"
    
    def _generate_shared_history(self, category: str, rel_type: str) -> str:
        """Generate shared history description"""
        history_templates = {
            "family": [
                "Grew up together in the same household",
                "Shared childhood adventures and misadventures",
                "Supported each other through difficult times",
                "Had a falling out over family matters"
            ],
            "friend": [
                "Met during a chance encounter",
                "Bonded over shared interests",
                "Went through training together",
                "Traveled together for a time"
            ],
            "mentor": [
                "Took character under their wing",
                "Taught valuable skills and wisdom",
                "Provided guidance during formative years",
                "Challenged character to grow"
            ],
            "rival": [
                "Competed for the same goal",
                "Had philosophical differences",
                "Fought over a misunderstanding",
                "Both sought the same person's approval"
            ],
            "enemy": [
                "Betrayed character's trust",
                "Caused harm to character's loved ones",
                "Represents everything character opposes",
                "Past conflict escalated beyond repair"
            ]
        }
        
        templates = history_templates.get(category, ["Had some kind of relationship"])
        return self.rng.choice(templates)
    
    def _generate_secret_description(self, secret_type: str, background: Background) -> str:
        """Generate secret description"""
        descriptions = {
            "identity": f"Is not actually who they claim to be",
            "crime": f"Committed a serious crime in their past",
            "knowledge": f"Knows dangerous information that others would kill for",
            "curse": f"Is under a magical curse",
            "debt": f"Owes a significant debt to dangerous people",
            "shame": f"Did something shameful they've never admitted"
        }
        
        return descriptions.get(secret_type, "Has a mysterious secret")
    
    def _generate_secret_consequences(self, secret_type: str) -> List[str]:
        """Generate consequences if secret is revealed"""
        consequences = {
            "identity": ["Arrest warrant issued", "Previous life catches up", "Lose current position"],
            "crime": ["Face justice", "Victims seek revenge", "Reputation ruined"],
            "knowledge": ["Become target", "Others seek information", "Forced into hiding"],
            "curse": ["Discrimination", "Fear from others", "Curse spreads"],
            "debt": ["Collectors come calling", "Threats to loved ones", "Property seized"],
            "shame": ["Social ostracism", "Loss of respect", "Emotional trauma"]
        }
        
        return consequences.get(secret_type, ["Face unknown consequences"])
    
    def _generate_secret_clues(self, secret_type: str) -> List[str]:
        """Generate clues that hint at the secret"""
        clues = {
            "identity": ["Wrong name used", "Familiar face recognized", "Old documents found"],
            "crime": ["Witness surfaces", "Evidence discovered", "Accomplice talks"],
            "knowledge": ["Slip of tongue", "Mysterious contacts", "Unusual behavior"],
            "curse": ["Strange symptoms", "Magical aura", "Unusual reactions"],
            "debt": ["Mysterious letters", "Nervous behavior", "Unexpected visitors"],
            "shame": ["Old acquaintances", "Guilty reactions", "Overcompensation"]
        }
        
        return clues.get(secret_type, ["Mysterious behavior"])
    
    async def _generate_origin_story(self, backstory: Backstory) -> str:
        """Generate character origin story"""
        background = backstory.background
        personality = backstory.personality
        
        templates = [
            f"Born in {background.birthplace} to a {background.social_class} family, {backstory.character_name} became a {background.profession}.",
            f"{backstory.character_name} grew up as a {background.profession} in {background.birthplace}, shaped by {background.major_life_events[0] if background.major_life_events else 'ordinary circumstances'}.",
            f"Coming from {background.social_class} origins in {background.birthplace}, {backstory.character_name} learned the ways of a {background.profession}."
        ]
        
        return self.rng.choice(templates)
    
    async def _generate_defining_moment(self, backstory: Backstory) -> str:
        """Generate character's defining moment"""
        if backstory.background.major_life_events:
            event = backstory.background.major_life_events[0]
            return f"The defining moment came when {event.lower()}, changing {backstory.character_name}'s outlook on life."
        
        if backstory.motivations:
            motivation = backstory.motivations[0]
            return f"Everything changed when {motivation.origin_story.lower()}, driving {backstory.character_name} toward {motivation.motivation_type}."
        
        return f"A moment of crisis forced {backstory.character_name} to discover their true calling."
    
    async def _generate_call_to_adventure(self, backstory: Backstory) -> str:
        """Generate what calls the character to adventure"""
        calls = [
            "A mysterious stranger brought news of opportunity",
            "Dreams and visions pointed toward a greater destiny",
            "Circumstances forced them to leave their old life behind",
            "A quest for answers led them into the wider world",
            "The desire to right old wrongs drove them to act"
        ]
        
        return self.rng.choice(calls)
    
    async def _generate_personal_hooks(self, backstory: Backstory) -> List[str]:
        """Generate personal adventure hooks"""
        hooks = []
        
        # Hooks from motivations
        for motivation in backstory.motivations:
            if motivation.motivation_type == "revenge":
                hooks.append("The target of their revenge surfaces")
            elif motivation.motivation_type == "knowledge":
                hooks.append("New clues about the mystery appear")
            elif motivation.motivation_type == "redemption":
                hooks.append("Opportunity to make amends presents itself")
        
        # Hooks from background
        if backstory.background.official_background == "criminal":
            hooks.append("Old criminal contacts need help")
        elif backstory.background.official_background == "noble":
            hooks.append("Family political situation requires attention")
        
        # Generic personal hooks
        generic_hooks = [
            "Receive mysterious letter from the past",
            "Encounter reminds them of their goals",
            "Opportunity to prove themselves arises"
        ]
        
        hooks.extend(self.rng.sample(generic_hooks, min(2, len(generic_hooks))))
        
        return hooks[:4]  # Limit to 4 hooks
    
    async def _generate_relationship_hooks(self, relationships: List[Relationship]) -> List[str]:
        """Generate hooks from relationships"""
        hooks = []
        
        for relationship in relationships:
            if relationship.relationship_type in ["friend", "family"]:
                hooks.append(f"{relationship.person_name} needs help")
            elif relationship.relationship_type == "enemy":
                hooks.append(f"{relationship.person_name} threatens innocents")
            elif relationship.relationship_type == "mentor":
                hooks.append(f"{relationship.person_name} has a final lesson")
            elif relationship.relationship_type == "rival":
                hooks.append(f"Competition with {relationship.person_name} escalates")
        
        return hooks[:3]  # Limit to 3 hooks
    
    async def _generate_background_hooks(self, background: Background) -> List[str]:
        """Generate hooks from character background"""
        bg_hooks = {
            "acolyte": ["Temple needs champions", "Religious artifact discovered"],
            "criminal": ["Old crew reunites", "Heist opportunity arises"],
            "folk_hero": ["Village in danger again", "Tyrant threatens homeland"],
            "noble": ["Political crisis emerges", "Family honor at stake"],
            "sage": ["Ancient knowledge surfaces", "Research proves dangerous"],
            "soldier": ["War breaks out", "Old unit needs help"]
        }
        
        return bg_hooks.get(background.official_background, ["Adventure calls"])
    
    async def _generate_faction_affiliations(self, background: Background) -> List[str]:
        """Generate faction affiliations"""
        faction_map = {
            "acolyte": ["Temple organization", "Religious order"],
            "criminal": ["Thieves guild", "Criminal syndicate"],
            "folk_hero": ["Local militia", "Resistance movement"],
            "noble": ["Noble house", "Political party"],
            "sage": ["Academy", "Scholarly society"],
            "soldier": ["Military unit", "Veterans organization"]
        }
        
        return faction_map.get(background.official_background, [])[:1]
    
    async def _generate_reputation(self, background: Background, personality: Personality) -> Dict[str, str]:
        """Generate reputation with different groups"""
        reputation = {}
        
        if background.official_background == "folk_hero":
            reputation["Common folk"] = "Hero"
            reputation["Nobles"] = "Troublemaker"
        elif background.official_background == "criminal":
            reputation["Criminals"] = "Professional"
            reputation["Guards"] = "Wanted"
        elif background.official_background == "noble":
            reputation["Nobles"] = "Peer"
            reputation["Common folk"] = "Out of touch"
        
        return reputation
    
    async def _generate_roleplay_notes(self, personality: Personality) -> List[str]:
        """Generate roleplay notes for DMs"""
        notes = []
        
        # Notes based on personality traits
        if personality.communication_style == "direct":
            notes.append("Speaks plainly and to the point")
        elif personality.communication_style == "verbose":
            notes.append("Tends to elaborate and tell long stories")
        
        if personality.trust_level == "suspicious":
            notes.append("Questions others' motives frequently")
        elif personality.trust_level == "trusting":
            notes.append("Gives others the benefit of the doubt")
        
        # Generic roleplay notes
        notes.extend([
            "Use personality traits to guide dialogue",
            "Remember character's bonds and flaws in social situations",
            "Play up ideals when character faces moral choices"
        ])
        
        return notes
    
    async def _generate_plot_potential(self, backstory: Backstory) -> List[str]:
        """Generate plot potential for DMs"""
        potential = []
        
        # From relationships
        for rel in backstory.relationships:
            if rel.relationship_type == "enemy":
                potential.append(f"{rel.person_name} could return as antagonist")
            elif rel.relationship_type == "mentor":
                potential.append(f"{rel.person_name} could provide guidance or final test")
        
        # From secrets
        for secret in backstory.secrets:
            potential.append(f"Secret {secret.secret_type} could be revealed at dramatic moment")
        
        # From motivations
        for motivation in backstory.motivations:
            potential.append(f"{motivation.motivation_type.title()} arc could span multiple sessions")
        
        return potential[:5]  # Limit to 5 items
    
    async def generate_npc(self, role: str = "neutral", importance: str = "minor") -> NPCProfile:
        """Generate an NPC profile"""
        name = self._generate_character_name()
        
        npc = NPCProfile(
            name=f"{name} (NPC)",
            description=f"Generated NPC: {name}",
            npc_role=role,
            importance_level=importance,
            appearance=self._generate_npc_appearance(),
            personality_summary=self._generate_npc_personality(),
            motivation_summary=self._generate_npc_motivation(),
            occupation=self._generate_npc_occupation(),
            attitude_toward_party=self._generate_npc_attitude(role)
        )
        
        return npc
    
    def _generate_npc_appearance(self) -> str:
        """Generate NPC appearance description"""
        builds = ["tall", "short", "average height", "stocky", "lean", "burly"]
        features = ["kind eyes", "stern expression", "weathered face", "youthful appearance", "distinctive scar"]
        clothing = ["simple clothes", "fine garments", "work attire", "traveling gear", "formal wear"]
        
        build = self.rng.choice(builds)
        feature = self.rng.choice(features)
        attire = self.rng.choice(clothing)
        
        return f"{build.title()} with {feature} wearing {attire}"
    
    def _generate_npc_personality(self) -> str:
        """Generate brief NPC personality"""
        traits = ["friendly", "gruff", "nervous", "confident", "mysterious", "cheerful", "serious", "eccentric"]
        return self.rng.choice(traits)
    
    def _generate_npc_motivation(self) -> str:
        """Generate NPC motivation"""
        motivations = [
            "wants to help others", "seeks personal gain", "follows orders",
            "protects family", "pursues knowledge", "maintains order",
            "causes trouble", "seeks revenge", "finds adventure"
        ]
        return self.rng.choice(motivations)
    
    def _generate_npc_occupation(self) -> str:
        """Generate NPC occupation"""
        occupations = [
            "merchant", "farmer", "guard", "innkeeper", "blacksmith", "scholar",
            "priest", "soldier", "noble", "artisan", "sailor", "performer"
        ]
        return self.rng.choice(occupations)
    
    def _generate_npc_attitude(self, role: str) -> str:
        """Generate NPC attitude toward party"""
        attitudes = {
            "ally": self.rng.choice(["friendly", "helpful", "supportive"]),
            "enemy": self.rng.choice(["hostile", "suspicious", "threatening"]),
            "neutral": self.rng.choice(["indifferent", "cautious", "curious"]),
            "questgiver": self.rng.choice(["desperate", "authoritative", "pleading"])
        }
        
        return attitudes.get(role, "neutral")