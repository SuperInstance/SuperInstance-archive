"""
AI-Powered Character Generation and Visualization
Advanced AI systems for generating character backstories, personalities, and visual representations
"""

import random
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import base64
from io import BytesIO

@dataclass
class CharacterPersonality:
    traits: List[str]
    ideals: List[str] 
    bonds: List[str]
    flaws: List[str]
    alignment: str
    motivation: str
    fears: List[str]
    goals: List[str]

@dataclass
class CharacterBackstory:
    origin: str
    family: str
    early_life: str
    formative_events: List[str]
    relationships: List[str]
    secrets: List[str]
    current_situation: str
    future_aspirations: str

class CharacterAIGenerator:
    """Advanced AI-powered character generation system"""
    
    def __init__(self):
        self.personality_templates = self._load_personality_templates()
        self.backstory_templates = self._load_backstory_templates()
        self.name_generators = self._load_name_generators()
        
    def _load_personality_templates(self) -> Dict[str, Any]:
        """Load personality generation templates"""
        return {
            "archetypes": {
                "hero": {
                    "traits": ["Brave", "Determined", "Compassionate", "Righteous"],
                    "ideals": ["Justice", "Protection", "Honor", "Courage"],
                    "motivations": ["Protect the innocent", "Right wrongs", "Seek justice"],
                    "fears": ["Failure", "Losing loved ones", "Becoming corrupt"],
                    "alignments": ["Lawful Good", "Neutral Good", "Chaotic Good"]
                },
                "scholar": {
                    "traits": ["Curious", "Methodical", "Patient", "Analytical"],
                    "ideals": ["Knowledge", "Truth", "Discovery", "Understanding"],
                    "motivations": ["Uncover ancient secrets", "Advance knowledge", "Solve mysteries"],
                    "fears": ["Ignorance", "Lost knowledge", "Being wrong"],
                    "alignments": ["Lawful Neutral", "True Neutral", "Lawful Good"]
                },
                "rogue": {
                    "traits": ["Cunning", "Independent", "Pragmatic", "Resourceful"],
                    "ideals": ["Freedom", "Opportunity", "Self-reliance", "Cleverness"],
                    "motivations": ["Personal gain", "Survive by wit", "Escape the past"],
                    "fears": ["Captivity", "Poverty", "Being caught"],
                    "alignments": ["Chaotic Neutral", "Neutral Evil", "Chaotic Good"]
                },
                "mystic": {
                    "traits": ["Mystical", "Wise", "Contemplative", "Intuitive"],
                    "ideals": ["Balance", "Harmony", "Enlightenment", "Destiny"],
                    "motivations": ["Seek enlightenment", "Maintain balance", "Follow destiny"],
                    "fears": ["Chaos", "Spiritual corruption", "Loss of connection"],
                    "alignments": ["True Neutral", "Lawful Neutral", "Chaotic Neutral"]
                }
            },
            "trait_combinations": {
                "complementary": [
                    ("Brave", "Reckless"), ("Wise", "Secretive"), ("Kind", "Naive"),
                    ("Loyal", "Stubborn"), ("Clever", "Arrogant"), ("Patient", "Passive")
                ],
                "conflicting": [
                    ("Honest", "Secretive"), ("Trusting", "Paranoid"), ("Generous", "Greedy"),
                    ("Humble", "Proud"), ("Cautious", "Impulsive"), ("Forgiving", "Vengeful")
                ]
            }
        }
    
    def _load_backstory_templates(self) -> Dict[str, Any]:
        """Load backstory generation templates"""
        return {
            "origins": {
                "noble": {
                    "description": "Born into nobility with privilege and responsibility",
                    "family_types": ["Ancient bloodline", "New money", "Fallen house", "Merchant princes"],
                    "formative_events": ["Court intrigue", "Family scandal", "Loss of fortune", "Political marriage"],
                    "skills": ["History", "Persuasion", "Insight", "Intimidation"]
                },
                "peasant": {
                    "description": "Humble origins in farming communities or urban slums", 
                    "family_types": ["Farming family", "Urban poor", "Craftspeople", "Traveling merchants"],
                    "formative_events": ["Natural disaster", "War displaced family", "Apprenticeship", "Local heroism"],
                    "skills": ["Animal Handling", "Survival", "Athletics", "Medicine"]
                },
                "orphan": {
                    "description": "Raised without parents in difficult circumstances",
                    "family_types": ["Street orphan", "Monastery raised", "Foster family", "Guild apprentice"],
                    "formative_events": ["Finding family truth", "Mentor's death", "First crime", "Discovering talents"],
                    "skills": ["Stealth", "Sleight of Hand", "Survival", "Deception"]
                },
                "exotic": {
                    "description": "Unusual origin from foreign lands or other planes",
                    "family_types": ["Planar travelers", "Exiled nobility", "Refugee family", "Monster heritage"],
                    "formative_events": ["Dimensional travel", "Cultural clash", "Hidden heritage revealed", "Prophecy"],
                    "skills": ["Arcana", "Investigation", "Insight", "History"]
                }
            },
            "relationships": {
                "mentors": ["Wise elder", "Former adventurer", "Guild master", "Religious leader", "Mysterious stranger"],
                "rivals": ["Childhood friend", "Fellow student", "Sibling", "Professional competitor", "Love interest"],
                "allies": ["Loyal companion", "Saved life", "Shared hardship", "Common enemy", "Professional respect"],
                "enemies": ["Betrayer", "Family enemy", "Professional rival", "Ideological opposite", "Past victim"]
            },
            "secrets": [
                "Hidden magical ability", "Secret parentage", "Past crime", "Forbidden love",
                "Cursed item", "Prophetic destiny", "Monster heritage", "Lost memory",
                "Double identity", "Sacred duty", "Ancient pact", "Stolen identity"
            ]
        }
    
    def _load_name_generators(self) -> Dict[str, Dict[str, List[str]]]:
        """Load name generation patterns by race and culture"""
        return {
            "human": {
                "first_names": {
                    "male": ["Aerdyn", "Ahvain", "Aramil", "Aranea", "Berris", "Cithreth", "Dayereth", "Drannor"],
                    "female": ["Adrie", "Ahvain", "Aramil", "Aranea", "Berris", "Caelynn", "Dayereth", "Enna"]
                },
                "surnames": ["Amakir", "Amakuri", "Galanodel", "Holimion", "Liadon", "Meliamne", "Nailo", "Siannodel"]
            },
            "elf": {
                "first_names": {
                    "male": ["Adran", "Aelar", "Aramil", "Aranea", "Berris", "Dayereth", "Drannor", "Enna"],
                    "female": ["Adrie", "Caelynn", "Dara", "Enna", "Galinndan", "Hadarai", "Immeral", "Ivellios"]
                },
                "surnames": ["Amakir", "Amakuri", "Galanodel", "Holimion", "Liadon", "Meliamne", "Nailo", "Siannodel"]
            },
            "dwarf": {
                "first_names": {
                    "male": ["Adrik", "Alberich", "Baern", "Darrak", "Delg", "Eberk", "Einkil", "Fargrim"],
                    "female": ["Amber", "Bardryn", "Diesa", "Eldeth", "Gunnloda", "Greta", "Helja", "Hlin"]
                },
                "clan_names": ["Battlehammer", "Brawnanvil", "Dankil", "Fireforge", "Frostbeard", "Gorunn", "Holderhek", "Ironfist"]
            },
            "halfling": {
                "first_names": {
                    "male": ["Alton", "Ander", "Cade", "Corrin", "Eldon", "Errich", "Finnan", "Garret"],
                    "female": ["Andry", "Bree", "Callie", "Cora", "Euphemia", "Jillian", "Kithri", "Lavinia"]
                },
                "surnames": ["Brushgather", "Goodbarrel", "Greenbottle", "High-hill", "Hilltopple", "Leagallow", "Tealeaf", "Thorngage"]
            }
        }
    
    def generate_personality(self, race: str = None, character_class: str = None, background: str = None) -> CharacterPersonality:
        """Generate a comprehensive character personality"""
        
        # Determine archetype based on class
        archetype = self._determine_archetype(character_class, background)
        archetype_data = self.personality_templates["archetypes"].get(archetype, 
                                                                    self.personality_templates["archetypes"]["hero"])
        
        # Generate traits with some randomness
        traits = random.sample(archetype_data["traits"], 2)
        
        # Add complementary or conflicting traits for depth
        trait_type = random.choice(["complementary", "conflicting"])
        additional_traits = random.choice(self.personality_templates["trait_combinations"][trait_type])
        traits.extend(additional_traits[:2])
        
        # Generate ideals, bonds, and flaws
        ideals = random.sample(archetype_data["ideals"], 2)
        motivation = random.choice(archetype_data["motivations"])
        fears = random.sample(archetype_data["fears"], random.randint(1, 2))
        alignment = random.choice(archetype_data["alignments"])
        
        # Generate bonds and flaws based on background
        bonds = self._generate_bonds(background)
        flaws = self._generate_flaws(traits)
        goals = self._generate_goals(motivation, character_class)
        
        return CharacterPersonality(
            traits=traits,
            ideals=ideals,
            bonds=bonds,
            flaws=flaws,
            alignment=alignment,
            motivation=motivation,
            fears=fears,
            goals=goals
        )
    
    def generate_backstory(self, race: str, character_class: str, background: str, personality: CharacterPersonality) -> CharacterBackstory:
        """Generate a detailed character backstory"""
        
        # Determine origin based on background
        origin_type = self._map_background_to_origin(background)
        origin_data = self.backstory_templates["origins"][origin_type]
        
        # Generate family background
        family_type = random.choice(origin_data["family_types"])
        family_description = self._generate_family_description(family_type, race)
        
        # Generate early life
        early_life = self._generate_early_life(origin_type, family_type)
        
        # Generate formative events
        formative_events = random.sample(origin_data["formative_events"], random.randint(2, 3))
        formative_events = [self._elaborate_event(event, character_class, race) for event in formative_events]
        
        # Generate relationships
        relationships = self._generate_relationships(personality)
        
        # Generate secrets
        num_secrets = random.randint(1, 3)
        secrets = random.sample(self.backstory_templates["secrets"], num_secrets)
        secrets = [self._elaborate_secret(secret, race, character_class) for secret in secrets]
        
        # Generate current situation and future
        current_situation = self._generate_current_situation(background, character_class)
        future_aspirations = self._generate_aspirations(personality.goals, character_class)
        
        return CharacterBackstory(
            origin=f"{origin_type.title()}: {origin_data['description']}",
            family=family_description,
            early_life=early_life,
            formative_events=formative_events,
            relationships=relationships,
            secrets=secrets,
            current_situation=current_situation,
            future_aspirations=future_aspirations
        )
    
    def generate_name(self, race: str, gender: str = None) -> Tuple[str, str]:
        """Generate appropriate name for race and gender"""
        race = race.lower()
        if race not in self.name_generators:
            race = "human"
        
        generator = self.name_generators[race]
        
        if gender is None:
            gender = random.choice(["male", "female"])
        
        # Generate first name
        first_name = random.choice(generator["first_names"][gender])
        
        # Generate surname based on race conventions
        if "surnames" in generator:
            surname = random.choice(generator["surnames"])
        elif "clan_names" in generator:
            surname = random.choice(generator["clan_names"])
        else:
            surname = random.choice(generator["surnames"] if "surnames" in generator else [""])
        
        return first_name, surname
    
    def _determine_archetype(self, character_class: str, background: str) -> str:
        """Determine personality archetype from class and background"""
        if not character_class:
            return "hero"
            
        class_archetypes = {
            "fighter": "hero",
            "paladin": "hero", 
            "barbarian": "hero",
            "wizard": "scholar",
            "artificer": "scholar",
            "rogue": "rogue",
            "ranger": "rogue",
            "cleric": "mystic",
            "druid": "mystic",
            "warlock": "mystic",
            "sorcerer": "mystic",
            "bard": "rogue",
            "monk": "mystic"
        }
        
        return class_archetypes.get(character_class.lower(), "hero")
    
    def _generate_bonds(self, background: str) -> List[str]:
        """Generate character bonds based on background"""
        bond_templates = {
            "acolyte": ["My temple/faith", "Fellow believers", "Sacred texts", "Divine mission"],
            "criminal": ["Criminal contact", "Partner in crime", "Victim of past crime", "Gang/organization"],
            "folk_hero": ["Home community", "People I saved", "Mentor figure", "Symbol of hope"],
            "noble": ["Family honor", "Noble house", "Loyal retainers", "Political allies"],
            "soldier": ["Military unit", "War comrades", "Fallen friends", "Military code"]
        }
        
        if background and background.lower() in bond_templates:
            available_bonds = bond_templates[background.lower()]
        else:
            available_bonds = ["Family", "Friends", "Mentor", "Home", "Cause", "Memory"]
        
        return random.sample(available_bonds, random.randint(1, 3))
    
    def _generate_flaws(self, traits: List[str]) -> List[str]:
        """Generate character flaws that complement or oppose traits"""
        flaw_templates = [
            "I have a weakness for the vices of the city",
            "I secretly believe that everyone is beneath me",
            "I hide a truly scandalous secret that could ruin my family",
            "I too often hear veiled insults and threats in every word",
            "I have an insatiable desire for carnal pleasures",
            "I can't resist a pretty face",
            "I'm always in debt and spend my share of every treasure unwisely",
            "I'm convinced that people are always trying to steal my secrets"
        ]
        
        return [random.choice(flaw_templates)]
    
    def _generate_goals(self, motivation: str, character_class: str) -> List[str]:
        """Generate character goals based on motivation and class"""
        base_goals = [
            f"Fulfill my motivation: {motivation}",
            "Grow stronger and more capable",
            "Protect those I care about"
        ]
        
        class_goals = {
            "wizard": ["Master new spells", "Uncover arcane secrets", "Build a tower"],
            "fighter": ["Become legendary warrior", "Protect the innocent", "Master all weapons"],
            "rogue": ["Pull off the perfect heist", "Escape my past", "Become invisible"],
            "cleric": ["Spread my faith", "Perform divine miracles", "Build a temple"]
        }
        
        if character_class and character_class.lower() in class_goals:
            base_goals.extend(class_goals[character_class.lower()][:2])
        
        return base_goals
    
    def _map_background_to_origin(self, background: str) -> str:
        """Map D&D background to origin type"""
        background_mapping = {
            "acolyte": "noble",
            "criminal": "orphan", 
            "folk_hero": "peasant",
            "noble": "noble",
            "hermit": "exotic",
            "outlander": "exotic",
            "sage": "noble",
            "soldier": "peasant"
        }
        
        return background_mapping.get(background.lower() if background else "", "peasant")
    
    def _generate_family_description(self, family_type: str, race: str) -> str:
        """Generate detailed family background"""
        descriptions = {
            "farming_family": f"Your {race} family worked the land for generations, teaching you the value of hard work and connection to nature.",
            "urban_poor": f"Growing up in the crowded {race} districts of a major city, your family struggled but remained close-knit.",
            "ancient_bloodline": f"Your {race} family traces its lineage back centuries, carrying both honor and burden of tradition.",
            "merchant_princes": f"Your {race} family built wealth through trade, giving you connections across many lands."
        }
        
        return descriptions.get(family_type.lower().replace(" ", "_"), 
                                f"Your {race} family shaped who you are through their own unique circumstances.")
    
    def _generate_early_life(self, origin_type: str, family_type: str) -> str:
        """Generate early life narrative"""
        templates = {
            "noble": "You were educated by private tutors and learned the intricacies of court life from an early age.",
            "peasant": "Your childhood was spent helping with daily survival, learning practical skills and the importance of community.",
            "orphan": "Without parents to guide you, you learned to be self-reliant and developed street smarts.",
            "exotic": "Your unusual circumstances set you apart from others, making you adaptable but sometimes isolated."
        }
        
        return templates.get(origin_type, "Your early years shaped your worldview in unexpected ways.")
    
    def _elaborate_event(self, event: str, character_class: str, race: str) -> str:
        """Add detail to formative events based on character specifics"""
        elaborations = {
            "court_intrigue": f"As a young {race}, you witnessed the dangerous games of nobles that would later influence your {character_class} training.",
            "family_scandal": f"A scandal involving your {race} family forced you to seek a new path as a {character_class}.",
            "natural_disaster": f"A devastating event in your {race} community taught you the importance of being prepared as a {character_class}.",
            "mentor's_death": f"The loss of your {race} mentor drove you to excel in your {character_class} abilities."
        }
        
        key = event.lower().replace(" ", "_")
        return elaborations.get(key, f"The {event.lower()} significantly influenced your path to becoming a {character_class}.")
    
    def _elaborate_secret(self, secret: str, race: str, character_class: str) -> str:
        """Elaborate on character secrets with race/class context"""
        return f"As a {race} {character_class}, you carry the burden of {secret.lower()}, which could change everything if revealed."
    
    def _generate_relationships(self, personality: CharacterPersonality) -> List[str]:
        """Generate relationships based on personality"""
        relationship_types = random.sample(["mentor", "rival", "ally", "enemy"], random.randint(2, 4))
        
        relationships = []
        for rel_type in relationship_types:
            if rel_type in self.backstory_templates["relationships"]:
                person = random.choice(self.backstory_templates["relationships"][rel_type])
                relationships.append(f"{rel_type.title()}: {person}")
        
        return relationships
    
    def _generate_current_situation(self, background: str, character_class: str) -> str:
        """Generate current life situation"""
        return f"Having completed your {background} background, you now pursue the path of a {character_class}, ready for adventure."
    
    def _generate_aspirations(self, goals: List[str], character_class: str) -> str:
        """Generate future aspirations"""
        primary_goal = goals[0] if goals else f"Master the arts of the {character_class}"
        return f"You dream of achieving {primary_goal.lower()} and leaving a lasting legacy."


class CharacterVisualizer:
    """Generate character portraits and visual representations"""
    
    def __init__(self):
        self.art_styles = ["realistic", "fantasy_art", "anime", "cartoon", "sketch"]
        self.pose_options = ["portrait", "action", "casual", "heroic", "mysterious"]
        
    def generate_character_portrait(self, character_data: Dict[str, Any], style: str = "fantasy_art") -> Dict[str, Any]:
        """Generate character portrait description and mock image data"""
        
        # Extract character details
        race = character_data.get("race", "human")
        character_class = character_data.get("class", "fighter") 
        gender = character_data.get("gender", "unspecified")
        personality = character_data.get("personality", {})
        
        # Generate appearance description
        appearance = self._generate_appearance_description(race, character_class, gender, personality)
        
        # Generate art prompt
        art_prompt = self._create_art_prompt(appearance, character_class, style)
        
        # Mock image generation (in real implementation, would call DALL-E or similar)
        mock_image_data = self._generate_mock_image()
        
        return {
            "appearance_description": appearance,
            "art_prompt": art_prompt,
            "style": style,
            "image_data": mock_image_data,
            "metadata": {
                "generated_for": f"{race} {character_class}",
                "style": style,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    
    def _generate_appearance_description(self, race: str, character_class: str, gender: str, personality: Dict[str, Any]) -> str:
        """Generate detailed appearance description"""
        
        # Race-specific features
        race_features = {
            "human": "varied features reflecting diverse heritage",
            "elf": "pointed ears, graceful features, and an otherworldly beauty",
            "dwarf": "sturdy build, impressive beard, and weathered hands",
            "halfling": "small stature, curly hair, and a warm, friendly face",
            "dragonborn": "draconic features, scaled skin, and reptilian eyes",
            "tiefling": "infernal heritage with horns, tail, and unusual skin tone"
        }
        
        # Class-specific elements
        class_appearance = {
            "fighter": "battle-scarred and muscular with confident bearing",
            "wizard": "scholarly appearance with ink-stained fingers and keen eyes", 
            "rogue": "lithe build with quick eyes and subtle movements",
            "cleric": "serene expression with holy symbols and peaceful demeanor"
        }
        
        base_features = race_features.get(race.lower(), "distinctive features")
        class_elements = class_appearance.get(character_class.lower(), "adventurous appearance")
        
        return f"A {gender} {race} with {base_features}. They have a {class_elements}, reflecting their life as a {character_class}."
    
    def _create_art_prompt(self, appearance: str, character_class: str, style: str) -> str:
        """Create detailed art generation prompt"""
        
        style_modifiers = {
            "fantasy_art": "high fantasy digital art, detailed, epic",
            "realistic": "photorealistic, detailed, professional photography", 
            "anime": "anime style, vibrant colors, expressive",
            "cartoon": "cartoon style, stylized, colorful",
            "sketch": "pencil sketch, artistic, black and white"
        }
        
        modifier = style_modifiers.get(style, "fantasy art")
        
        return f"{appearance} Portrait of a {character_class}, {modifier}, high quality, detailed character design"
    
    def _generate_mock_image(self) -> str:
        """Generate mock image data (placeholder for actual AI image generation)"""
        # In real implementation, this would call an AI image generation API
        # For now, return a placeholder data URI
        
        # Create a simple colored rectangle as placeholder
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # Create a 400x400 image with a gradient background
            img = Image.new('RGB', (400, 400), color='lightblue')
            draw = ImageDraw.Draw(img)
            
            # Add some basic shapes to represent a character silhouette
            draw.ellipse([150, 100, 250, 200], fill='lightcoral')  # Head
            draw.rectangle([175, 200, 225, 350], fill='darkblue')  # Body
            
            # Add text
            try:
                draw.text((150, 360), "Generated Character", fill='black')
            except:
                pass  # Font loading might fail, skip text
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except ImportError:
            # If PIL is not available, return a placeholder
            return "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgZmlsbD0iIzRBOTBFMiIvPjx0ZXh0IHg9IjIwMCIgeT0iMjAwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+R2VuZXJhdGVkIENoYXJhY3RlcjwvdGV4dD48L3N2Zz4="
    
    def generate_party_visualization(self, party_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate visualization of entire party composition"""
        
        if not party_members:
            return {"error": "No party members provided"}
        
        # Generate group composition analysis
        classes = [member.get("class", "Unknown") for member in party_members]
        races = [member.get("race", "Unknown") for member in party_members]
        
        composition = {
            "size": len(party_members),
            "classes": {cls: classes.count(cls) for cls in set(classes)},
            "races": {race: races.count(race) for race in set(races)},
            "balance_analysis": self._analyze_party_balance(classes)
        }
        
        # Generate party image prompt
        party_prompt = self._create_party_art_prompt(party_members)
        
        # Mock party image
        party_image = self._generate_party_mock_image(len(party_members))
        
        return {
            "composition": composition,
            "art_prompt": party_prompt,
            "image_data": party_image,
            "suggestions": self._generate_party_suggestions(classes)
        }
    
    def _analyze_party_balance(self, classes: List[str]) -> Dict[str, Any]:
        """Analyze party role balance"""
        
        role_mapping = {
            "fighter": "tank", "paladin": "tank", "barbarian": "tank",
            "wizard": "damage", "sorcerer": "damage", "warlock": "damage",
            "rogue": "damage", "ranger": "damage",
            "cleric": "support", "bard": "support", "druid": "support"
        }
        
        roles = [role_mapping.get(cls.lower(), "utility") for cls in classes]
        role_counts = {role: roles.count(role) for role in set(roles)}
        
        # Assess balance
        total = len(classes)
        balance_score = 0
        
        # Ideal: 25% tank, 50% damage, 25% support
        ideal = {"tank": 0.25, "damage": 0.5, "support": 0.25}
        
        for role, count in role_counts.items():
            actual_ratio = count / total
            ideal_ratio = ideal.get(role, 0.1)
            balance_score += abs(actual_ratio - ideal_ratio)
        
        balance_rating = "Excellent" if balance_score < 0.3 else "Good" if balance_score < 0.6 else "Needs Work"
        
        return {
            "roles": role_counts,
            "balance_score": round(balance_score, 2),
            "rating": balance_rating,
            "recommendations": self._get_balance_recommendations(role_counts)
        }
    
    def _create_party_art_prompt(self, party_members: List[Dict[str, Any]]) -> str:
        """Create art prompt for party group portrait"""
        
        member_descriptions = []
        for member in party_members:
            race = member.get("race", "human")
            character_class = member.get("class", "adventurer")
            member_descriptions.append(f"{race} {character_class}")
        
        return f"Fantasy art group portrait of an adventuring party: {', '.join(member_descriptions)}, standing together, heroic pose, detailed fantasy art style"
    
    def _generate_party_mock_image(self, party_size: int) -> str:
        """Generate mock image for party visualization"""
        
        try:
            from PIL import Image, ImageDraw
            import io
            
            # Create wider image for group
            width = min(600, party_size * 120)
            img = Image.new('RGB', (width, 400), color='lightgreen')
            draw = ImageDraw.Draw(img)
            
            # Draw simple figures for each party member
            figure_width = width // party_size
            colors = ['red', 'blue', 'yellow', 'purple', 'orange', 'pink']
            
            for i in range(party_size):
                x_start = i * figure_width + figure_width // 4
                color = colors[i % len(colors)]
                
                # Simple figure
                draw.ellipse([x_start, 100, x_start + 50, 150], fill=color)  # Head
                draw.rectangle([x_start + 20, 150, x_start + 30, 250], fill=color)  # Body
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except ImportError:
            return "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNjAwIiBoZWlnaHQ9IjQwMCIgZmlsbD0iIzY4RDM5MSIvPjx0ZXh0IHg9IjMwMCIgeT0iMjAwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+UGFydHkgVmlzdWFsaXphdGlvbjwvdGV4dD48L3N2Zz4="
    
    def _get_balance_recommendations(self, role_counts: Dict[str, int]) -> List[str]:
        """Get recommendations for improving party balance"""
        recommendations = []
        
        if role_counts.get("tank", 0) == 0:
            recommendations.append("Consider adding a tank class (Fighter, Paladin, Barbarian)")
        
        if role_counts.get("support", 0) == 0:
            recommendations.append("Consider adding a support class (Cleric, Bard, Druid)")
        
        if role_counts.get("damage", 0) < 2:
            recommendations.append("Consider adding more damage dealers")
        
        if not recommendations:
            recommendations.append("Party balance looks good!")
        
        return recommendations
    
    def _generate_party_suggestions(self, classes: List[str]) -> List[str]:
        """Generate suggestions for party improvement"""
        suggestions = []
        
        class_set = set(c.lower() for c in classes)
        
        if "cleric" not in class_set and "druid" not in class_set:
            suggestions.append("Consider adding a divine spellcaster for healing")
        
        if "wizard" not in class_set and "sorcerer" not in class_set:
            suggestions.append("An arcane spellcaster could provide utility spells")
        
        if len(classes) < 4:
            suggestions.append("A party of 4-6 members is typically optimal")
        
        return suggestions if suggestions else ["Your party composition looks solid!"]