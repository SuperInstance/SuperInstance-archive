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
import math

class WorldType(Enum):
    FANTASY = "fantasy"
    SCIFI = "scifi"
    MODERN = "modern"
    HISTORICAL = "historical"
    POST_APOCALYPTIC = "post_apocalyptic"
    STEAMPUNK = "steampunk"
    CYBERPUNK = "cyberpunk"
    ALTERNATE_HISTORY = "alternate_history"

class BiomeType(Enum):
    FOREST = "forest"
    DESERT = "desert"
    MOUNTAINS = "mountains"
    OCEAN = "ocean"
    TUNDRA = "tundra"
    GRASSLAND = "grassland"
    SWAMP = "swamp"
    URBAN = "urban"
    UNDERGROUND = "underground"
    SKY_REALM = "sky_realm"

class CultureAspect(Enum):
    GOVERNMENT = "government"
    RELIGION = "religion"
    ECONOMY = "economy"
    SOCIAL_STRUCTURE = "social_structure"
    TECHNOLOGY = "technology"
    ARTS = "arts"
    TRADITIONS = "traditions"
    LANGUAGES = "languages"

@dataclass
class Location:
    id: str
    name: str
    biome: BiomeType
    description: str
    notable_features: List[str]
    inhabitants: List[str]
    resources: List[str]
    connections: List[str]  # IDs of connected locations
    climate: Dict[str, Any]
    dangers: List[str]
    coordinates: Dict[str, float]  # x, y coordinates on world map

@dataclass
class Culture:
    id: str
    name: str
    aspects: Dict[CultureAspect, str]
    values: List[str]
    taboos: List[str]
    customs: List[str]
    notable_figures: List[str]
    territories: List[str]  # Location IDs
    relationships: Dict[str, str]  # culture_id: relationship_type

@dataclass
class Organization:
    id: str
    name: str
    type: str  # guild, government, religion, etc.
    description: str
    goals: List[str]
    methods: List[str]
    members: List[str]
    territories: List[str]
    resources: List[str]
    allies: List[str]
    enemies: List[str]

@dataclass
class HistoricalEvent:
    id: str
    name: str
    date: str
    description: str
    participants: List[str]
    consequences: List[str]
    affected_locations: List[str]
    affected_cultures: List[str]

@dataclass
class World:
    id: str
    name: str
    world_type: WorldType
    theme: str
    description: str
    locations: List[Location]
    cultures: List[Culture]
    organizations: List[Organization]
    history: List[HistoricalEvent]
    natural_laws: Dict[str, str]
    calendar_system: Dict[str, Any]
    created_at: str
    updated_at: str

class WorldGenerator:
    def __init__(self):
        self.location_names = {
            BiomeType.FOREST: ["Whisperwood", "Shadowgrove", "Eldertree Vale", "Moonleaf Forest", "Thornwick"],
            BiomeType.DESERT: ["Sunscorch Dunes", "Mirage Wastes", "Oasis Springs", "Sandwhisper Desert", "Drysalt Plains"],
            BiomeType.MOUNTAINS: ["Stormcrown Peaks", "Ironback Range", "Cloudreacher Mountains", "Frostspire Heights", "Dragonbone Ridge"],
            BiomeType.OCEAN: ["Sapphire Deeps", "Coral Gardens", "Stormwall Straits", "Pearl Harbor", "Kraken's Domain"],
            BiomeType.URBAN: ["Goldenheart", "Irongate", "Starfall City", "Crossroads", "Haven's Rest"]
        }
        
        self.culture_templates = {
            "government": ["Democratic Council", "Absolute Monarchy", "Tribal Confederation", "Merchant Republic", "Theocracy", "Military Junta"],
            "religion": ["Nature Worship", "Ancestor Veneration", "Monotheistic Faith", "Elemental Spirits", "Star Worship", "Philosophy-based"],
            "economy": ["Trade-based", "Agricultural", "Mining", "Crafting Guilds", "Nomadic Herding", "Magical Services"],
            "technology": ["Pre-industrial", "Steam Power", "Magical Enhancement", "Advanced Science", "Organic Technology", "Lost Ancient Tech"]
        }
        
        self.organization_types = ["Guild", "Religious Order", "Secret Society", "Government Agency", "Trading Company", "Military Order", "Academic Institution"]

    def generate_world(self, name: str, world_type: WorldType, theme: str = None) -> World:
        world_id = str(uuid.uuid4())
        
        if not theme:
            themes = {
                WorldType.FANTASY: "Magic vs. Technology",
                WorldType.SCIFI: "Exploration of the Unknown",
                WorldType.POST_APOCALYPTIC: "Rebuilding from Ruins",
                WorldType.CYBERPUNK: "Technology vs. Humanity"
            }
            theme = themes.get(world_type, "Adventure and Discovery")
        
        # Generate interconnected world elements
        locations = self._generate_locations(world_type, 5 + random.randint(0, 5))
        cultures = self._generate_cultures(world_type, len(locations))
        organizations = self._generate_organizations(locations, cultures)
        history = self._generate_history(locations, cultures, organizations)
        natural_laws = self._generate_natural_laws(world_type)
        calendar = self._generate_calendar_system(world_type)
        
        return World(
            id=world_id,
            name=name,
            world_type=world_type,
            theme=theme,
            description=f"A {world_type.value} world centered around {theme}",
            locations=locations,
            cultures=cultures,
            organizations=organizations,
            history=history,
            natural_laws=natural_laws,
            calendar_system=calendar,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

    def _generate_locations(self, world_type: WorldType, count: int) -> List[Location]:
        locations = []
        used_names = set()
        
        # Distribute biomes based on world type
        biome_weights = self._get_biome_weights(world_type)
        
        for i in range(count):
            biome = self._weighted_choice(biome_weights)
            name = self._generate_unique_location_name(biome, used_names)
            used_names.add(name)
            
            location = Location(
                id=str(uuid.uuid4()),
                name=name,
                biome=biome,
                description=self._generate_location_description(biome, world_type),
                notable_features=self._generate_location_features(biome, world_type),
                inhabitants=self._generate_location_inhabitants(biome, world_type),
                resources=self._generate_location_resources(biome),
                connections=[],  # Will be filled later
                climate=self._generate_climate(biome),
                dangers=self._generate_location_dangers(biome, world_type),
                coordinates={"x": random.uniform(0, 1000), "y": random.uniform(0, 1000)}
            )
            locations.append(location)
        
        # Create connections between nearby locations
        self._create_location_connections(locations)
        
        return locations

    def _get_biome_weights(self, world_type: WorldType) -> Dict[BiomeType, int]:
        base_weights = {biome: 1 for biome in BiomeType}
        
        if world_type == WorldType.FANTASY:
            base_weights[BiomeType.FOREST] = 3
            base_weights[BiomeType.MOUNTAINS] = 2
        elif world_type == WorldType.SCIFI:
            base_weights[BiomeType.URBAN] = 3
            base_weights[BiomeType.DESERT] = 2
        elif world_type == WorldType.POST_APOCALYPTIC:
            base_weights[BiomeType.URBAN] = 4
            base_weights[BiomeType.DESERT] = 2
        elif world_type == WorldType.CYBERPUNK:
            base_weights[BiomeType.URBAN] = 5
            base_weights[BiomeType.UNDERGROUND] = 2
        
        return base_weights

    def _weighted_choice(self, weights: Dict[BiomeType, int]) -> BiomeType:
        total = sum(weights.values())
        choice = random.randint(1, total)
        current = 0
        
        for biome, weight in weights.items():
            current += weight
            if choice <= current:
                return biome
        
        return list(weights.keys())[0]

    def _generate_unique_location_name(self, biome: BiomeType, used_names: set) -> str:
        base_names = self.location_names.get(biome, ["Unnamed Place"])
        
        for _ in range(10):  # Try to find unique name
            name = random.choice(base_names)
            if name not in used_names:
                return name
        
        # Generate new name if all base names are used
        prefixes = ["North", "South", "East", "West", "Upper", "Lower", "New", "Old"]
        return f"{random.choice(prefixes)} {random.choice(base_names)}"

    def _generate_location_description(self, biome: BiomeType, world_type: WorldType) -> str:
        base_descriptions = {
            BiomeType.FOREST: "A dense woodland filled with ancient trees",
            BiomeType.DESERT: "Vast expanses of sand and stone under blazing sun",
            BiomeType.MOUNTAINS: "Towering peaks that scrape the sky",
            BiomeType.OCEAN: "Endless waters hiding mysteries in their depths",
            BiomeType.URBAN: "A bustling center of civilization and commerce"
        }
        
        base = base_descriptions.get(biome, "A unique location")
        
        if world_type == WorldType.FANTASY:
            base += " imbued with magical energy"
        elif world_type == WorldType.SCIFI:
            base += " shaped by advanced technology"
        elif world_type == WorldType.POST_APOCALYPTIC:
            base += " scarred by past catastrophes"
        
        return base

    def _generate_location_features(self, biome: BiomeType, world_type: WorldType) -> List[str]:
        features = {
            BiomeType.FOREST: ["Ancient standing stones", "Hidden groves", "Treehouse villages", "Sacred clearings"],
            BiomeType.DESERT: ["Oasis springs", "Sand dune mazes", "Rock formations", "Underground rivers"],
            BiomeType.MOUNTAINS: ["Hidden caves", "Steep cliffs", "Mountain passes", "Alpine meadows"],
            BiomeType.OCEAN: ["Coral reefs", "Underwater caves", "Floating islands", "Deep trenches"],
            BiomeType.URBAN: ["Grand plazas", "Towering spires", "Underground tunnels", "Market districts"]
        }
        
        base_features = features.get(biome, ["Notable landmarks"])
        selected = random.sample(base_features, min(3, len(base_features)))
        
        # Add world-type specific features
        if world_type == WorldType.FANTASY:
            selected.append("Magical phenomenon")
        elif world_type == WorldType.SCIFI:
            selected.append("Advanced technology installation")
        
        return selected

    def _generate_location_inhabitants(self, biome: BiomeType, world_type: WorldType) -> List[str]:
        inhabitants = []
        
        if world_type == WorldType.FANTASY:
            fantasy_inhabitants = {
                BiomeType.FOREST: ["Elves", "Druids", "Forest spirits"],
                BiomeType.MOUNTAINS: ["Dwarves", "Giants", "Mountain clans"],
                BiomeType.DESERT: ["Nomadic tribes", "Sand mages", "Desert dwellers"],
                BiomeType.URBAN: ["Humans", "Mixed races", "Merchants"]
            }
            inhabitants = fantasy_inhabitants.get(biome, ["Local population"])
        elif world_type == WorldType.SCIFI:
            scifi_inhabitants = {
                BiomeType.URBAN: ["Corporate citizens", "Cyborgs", "AI entities"],
                BiomeType.DESERT: ["Mining colonists", "Terraformers", "Research teams"],
                BiomeType.OCEAN: ["Aquatic settlers", "Submarine crews", "Marine researchers"]
            }
            inhabitants = scifi_inhabitants.get(biome, ["Colonists", "Scientists"])
        else:
            inhabitants = ["Local population", "Travelers", "Traders"]
        
        return random.sample(inhabitants, min(2, len(inhabitants)))

    def _generate_location_resources(self, biome: BiomeType) -> List[str]:
        resources = {
            BiomeType.FOREST: ["Timber", "Medicinal herbs", "Wild game", "Nuts and berries"],
            BiomeType.DESERT: ["Minerals", "Rare metals", "Crystal formations", "Solar energy"],
            BiomeType.MOUNTAINS: ["Stone", "Precious metals", "Gems", "Fresh water"],
            BiomeType.OCEAN: ["Fish", "Pearls", "Seaweed", "Salt"],
            BiomeType.URBAN: ["Manufactured goods", "Knowledge", "Services", "Trade networks"]
        }
        
        available = resources.get(biome, ["Basic materials"])
        return random.sample(available, min(3, len(available)))

    def _generate_climate(self, biome: BiomeType) -> Dict[str, Any]:
        climate_data = {
            BiomeType.FOREST: {"temperature": "temperate", "humidity": "high", "precipitation": "moderate"},
            BiomeType.DESERT: {"temperature": "hot", "humidity": "low", "precipitation": "rare"},
            BiomeType.MOUNTAINS: {"temperature": "cold", "humidity": "low", "precipitation": "snow"},
            BiomeType.OCEAN: {"temperature": "mild", "humidity": "high", "precipitation": "frequent"},
            BiomeType.URBAN: {"temperature": "variable", "humidity": "moderate", "precipitation": "modified"}
        }
        
        return climate_data.get(biome, {"temperature": "temperate", "humidity": "moderate", "precipitation": "seasonal"})

    def _generate_location_dangers(self, biome: BiomeType, world_type: WorldType) -> List[str]:
        dangers = {
            BiomeType.FOREST: ["Wild beasts", "Getting lost", "Poisonous plants"],
            BiomeType.DESERT: ["Extreme heat", "Sandstorms", "Dehydration"],
            BiomeType.MOUNTAINS: ["Avalanches", "Falling rocks", "Extreme cold"],
            BiomeType.OCEAN: ["Storms", "Drowning", "Sea monsters"],
            BiomeType.URBAN: ["Crime", "Disease", "Political unrest"]
        }
        
        base_dangers = dangers.get(biome, ["Environmental hazards"])
        
        if world_type == WorldType.FANTASY:
            base_dangers.append("Magical creatures")
        elif world_type == WorldType.POST_APOCALYPTIC:
            base_dangers.extend(["Radiation", "Mutant creatures"])
        
        return random.sample(base_dangers, min(2, len(base_dangers)))

    def _create_location_connections(self, locations: List[Location]):
        for i, location in enumerate(locations):
            # Connect to nearby locations based on distance
            for j, other_location in enumerate(locations):
                if i != j:
                    distance = math.sqrt(
                        (location.coordinates["x"] - other_location.coordinates["x"]) ** 2 +
                        (location.coordinates["y"] - other_location.coordinates["y"]) ** 2
                    )
                    
                    # Connect if within reasonable distance
                    if distance < 300 and len(location.connections) < 3:
                        location.connections.append(other_location.id)

    def _generate_cultures(self, world_type: WorldType, location_count: int) -> List[Culture]:
        cultures = []
        culture_count = max(2, location_count // 2)
        
        for i in range(culture_count):
            culture_id = str(uuid.uuid4())
            
            aspects = {}
            for aspect in CultureAspect:
                if aspect in self.culture_templates:
                    aspects[aspect] = random.choice(self.culture_templates[aspect.value])
                else:
                    aspects[aspect] = f"Unique {aspect.value.replace('_', ' ')} system"
            
            culture = Culture(
                id=culture_id,
                name=self._generate_culture_name(world_type),
                aspects=aspects,
                values=self._generate_cultural_values(),
                taboos=self._generate_cultural_taboos(),
                customs=self._generate_cultural_customs(),
                notable_figures=[],  # Would be filled with character references
                territories=[],  # Would be assigned later
                relationships={}  # Would be developed based on conflicts/alliances
            )
            cultures.append(culture)
        
        # Create relationships between cultures
        self._create_culture_relationships(cultures)
        
        return cultures

    def _generate_culture_name(self, world_type: WorldType) -> str:
        prefixes = ["Northern", "Southern", "Eastern", "Western", "Highland", "Lowland", "River", "Desert", "Forest", "Mountain"]
        suffixes = ["Empire", "Kingdom", "Tribes", "Confederation", "Alliance", "Republic", "Clans", "Federation", "Union", "Coalition"]
        
        return f"{random.choice(prefixes)} {random.choice(suffixes)}"

    def _generate_cultural_values(self) -> List[str]:
        values = ["Honor", "Wisdom", "Courage", "Community", "Independence", "Tradition", "Innovation", "Harmony", "Strength", "Knowledge"]
        return random.sample(values, random.randint(2, 4))

    def _generate_cultural_taboos(self) -> List[str]:
        taboos = ["Speaking ill of ancestors", "Wasting resources", "Breaking hospitality", "Dishonoring family", "Destroying nature", "Questioning authority"]
        return random.sample(taboos, random.randint(1, 3))

    def _generate_cultural_customs(self) -> List[str]:
        customs = ["Coming of age ceremonies", "Seasonal festivals", "Ancestor worship", "Gift exchanges", "Storytelling traditions", "Ritual combat"]
        return random.sample(customs, random.randint(2, 4))

    def _create_culture_relationships(self, cultures: List[Culture]):
        relationship_types = ["Allies", "Enemies", "Neutral", "Trading Partners", "Rivals", "Suspicious"]
        
        for i, culture in enumerate(cultures):
            for j, other_culture in enumerate(cultures):
                if i != j and other_culture.id not in culture.relationships:
                    relationship = random.choice(relationship_types)
                    culture.relationships[other_culture.id] = relationship
                    # Make relationships somewhat reciprocal
                    if relationship == "Allies":
                        other_culture.relationships[culture.id] = "Allies"
                    elif relationship == "Enemies":
                        other_culture.relationships[culture.id] = "Enemies"

    def _generate_organizations(self, locations: List[Location], cultures: List[Culture]) -> List[Organization]:
        organizations = []
        
        for org_type in self.organization_types[:random.randint(3, 6)]:
            org_id = str(uuid.uuid4())
            
            organization = Organization(
                id=org_id,
                name=self._generate_organization_name(org_type),
                type=org_type,
                description=f"A {org_type.lower()} that {self._generate_organization_purpose(org_type)}",
                goals=self._generate_organization_goals(org_type),
                methods=self._generate_organization_methods(org_type),
                members=[],  # Would be populated with character references
                territories=random.sample([loc.id for loc in locations], random.randint(1, 3)),
                resources=self._generate_organization_resources(org_type),
                allies=[],
                enemies=[]
            )
            organizations.append(organization)
        
        # Create relationships between organizations
        self._create_organization_relationships(organizations)
        
        return organizations

    def _generate_organization_name(self, org_type: str) -> str:
        prefixes = {
            "Guild": ["Craftsmen's", "Merchant", "Artisan", "Master"],
            "Religious Order": ["Sacred", "Divine", "Holy", "Blessed"],
            "Secret Society": ["Shadow", "Hidden", "Silent", "Veiled"],
            "Military Order": ["Iron", "Steel", "Crimson", "Golden"]
        }
        
        suffixes = {
            "Guild": ["Guild", "Brotherhood", "Union", "Consortium"],
            "Religious Order": ["Order", "Brotherhood", "Sisterhood", "Temple"],
            "Secret Society": ["Circle", "Lodge", "Society", "Brotherhood"],
            "Military Order": ["Guard", "Legion", "Company", "Battalion"]
        }
        
        prefix_list = prefixes.get(org_type, ["Great"])
        suffix_list = suffixes.get(org_type, ["Organization"])
        
        return f"{random.choice(prefix_list)} {random.choice(suffix_list)}"

    def _generate_organization_purpose(self, org_type: str) -> str:
        purposes = {
            "Guild": "regulates trade and maintains quality standards",
            "Religious Order": "spreads faith and provides spiritual guidance",
            "Secret Society": "pursues hidden knowledge and influences from shadows",
            "Military Order": "protects the realm and maintains order",
            "Trading Company": "facilitates commerce across distant lands",
            "Academic Institution": "preserves knowledge and trains scholars"
        }
        
        return purposes.get(org_type, "serves the common good")

    def _generate_organization_goals(self, org_type: str) -> List[str]:
        goals = {
            "Guild": ["Maintain trade monopoly", "Train new apprentices", "Protect member interests"],
            "Religious Order": ["Spread the faith", "Protect the innocent", "Preserve sacred texts"],
            "Secret Society": ["Gather forbidden knowledge", "Influence political decisions", "Maintain secrecy"],
            "Military Order": ["Defend the realm", "Maintain peace", "Train elite warriors"]
        }
        
        base_goals = goals.get(org_type, ["Achieve organizational objectives", "Expand influence", "Serve members"])
        return random.sample(base_goals, min(3, len(base_goals)))

    def _generate_organization_methods(self, org_type: str) -> List[str]:
        methods = {
            "Guild": ["Quality control", "Price regulation", "Apprenticeship programs"],
            "Religious Order": ["Prayer and ritual", "Charitable works", "Missionary activities"],
            "Secret Society": ["Infiltration", "Blackmail", "Hidden communications"],
            "Military Order": ["Combat training", "Strategic planning", "Intelligence gathering"]
        }
        
        base_methods = methods.get(org_type, ["Formal meetings", "Member networking", "Resource pooling"])
        return random.sample(base_methods, min(3, len(base_methods)))

    def _generate_organization_resources(self, org_type: str) -> List[str]:
        resources = {
            "Guild": ["Gold reserves", "Trade connections", "Skilled craftsmen"],
            "Religious Order": ["Sacred artifacts", "Devoted followers", "Temple grounds"],
            "Secret Society": ["Hidden assets", "Information networks", "Safe houses"],
            "Military Order": ["Weapons and armor", "Training facilities", "Elite soldiers"]
        }
        
        base_resources = resources.get(org_type, ["Financial assets", "Member loyalty", "Strategic locations"])
        return random.sample(base_resources, min(3, len(base_resources)))

    def _create_organization_relationships(self, organizations: List[Organization]):
        for i, org in enumerate(organizations):
            potential_allies = random.randint(0, 2)
            potential_enemies = random.randint(0, 2)
            
            other_orgs = [o for j, o in enumerate(organizations) if j != i]
            
            if potential_allies > 0 and other_orgs:
                allies = random.sample(other_orgs, min(potential_allies, len(other_orgs)))
                org.allies = [ally.id for ally in allies]
                for ally in allies:
                    if org.id not in ally.allies:
                        ally.allies.append(org.id)
            
            if potential_enemies > 0 and other_orgs:
                remaining_orgs = [o for o in other_orgs if o.id not in org.allies]
                if remaining_orgs:
                    enemies = random.sample(remaining_orgs, min(potential_enemies, len(remaining_orgs)))
                    org.enemies = [enemy.id for enemy in enemies]
                    for enemy in enemies:
                        if org.id not in enemy.enemies:
                            enemy.enemies.append(org.id)

    def _generate_history(self, locations: List[Location], cultures: List[Culture], organizations: List[Organization]) -> List[HistoricalEvent]:
        events = []
        
        event_templates = [
            "The Great War between cultures",
            "Discovery of ancient ruins",
            "Natural disaster reshapes the land",
            "Rise of a powerful organization",
            "Diplomatic alliance formation",
            "Magical/technological breakthrough",
            "Collapse of an old empire",
            "Migration of peoples"
        ]
        
        for i, template in enumerate(random.sample(event_templates, random.randint(3, 6))):
            event_id = str(uuid.uuid4())
            
            event = HistoricalEvent(
                id=event_id,
                name=f"{template} ({100 + i * 50} years ago)",
                date=f"Year {1000 - (100 + i * 50)}",
                description=self._generate_event_description(template, cultures, organizations),
                participants=self._select_event_participants(template, cultures, organizations),
                consequences=self._generate_event_consequences(template),
                affected_locations=random.sample([loc.id for loc in locations], random.randint(1, 3)),
                affected_cultures=random.sample([cult.id for cult in cultures], random.randint(1, 2))
            )
            events.append(event)
        
        return events

    def _generate_event_description(self, template: str, cultures: List[Culture], organizations: List[Organization]) -> str:
        if "War" in template:
            return f"A devastating conflict that changed the balance of power"
        elif "Discovery" in template:
            return f"Ancient secrets were unearthed, changing understanding of the world"
        elif "disaster" in template:
            return f"Natural forces reshaped the landscape and displaced populations"
        elif "organization" in template:
            return f"A new power emerged to fill a vacuum in leadership"
        elif "alliance" in template:
            return f"Former enemies joined together against a common threat"
        else:
            return f"A significant event that shaped the current world"

    def _select_event_participants(self, template: str, cultures: List[Culture], organizations: List[Organization]) -> List[str]:
        if "War" in template or "alliance" in template:
            return random.sample([c.name for c in cultures], min(2, len(cultures)))
        elif "organization" in template:
            return random.sample([o.name for o in organizations], min(1, len(organizations)))
        else:
            return ["Unknown participants", "Multiple groups"]

    def _generate_event_consequences(self, template: str) -> List[str]:
        consequences = {
            "War": ["Territorial changes", "Population displacement", "Political restructuring"],
            "Discovery": ["Technological advancement", "Religious upheaval", "New trade routes"],
            "disaster": ["Geographic changes", "Population migration", "Resource scarcity"],
            "organization": ["Power shift", "New laws or customs", "Economic changes"]
        }
        
        for key in consequences:
            if key.lower() in template.lower():
                return random.sample(consequences[key], min(2, len(consequences[key])))
        
        return ["Lasting cultural impact", "Changed political landscape"]

    def _generate_natural_laws(self, world_type: WorldType) -> Dict[str, str]:
        laws = {}
        
        if world_type == WorldType.FANTASY:
            laws = {
                "Magic System": "Magic flows from natural sources and requires focus and training",
                "Divine Intervention": "Gods occasionally interfere in mortal affairs",
                "Magical Creatures": "Supernatural beings exist alongside mundane animals"
            }
        elif world_type == WorldType.SCIFI:
            laws = {
                "FTL Travel": "Faster-than-light travel possible through hyperspace",
                "AI Limitations": "Artificial intelligence cannot fully replicate consciousness",
                "Energy Sources": "Clean fusion provides unlimited power"
            }
        elif world_type == WorldType.POST_APOCALYPTIC:
            laws = {
                "Radiation Effects": "Certain areas remain dangerous due to lingering radiation",
                "Mutation": "Some life forms have adapted to harsh conditions",
                "Technology Decay": "Pre-war technology gradually fails without maintenance"
            }
        else:
            laws = {
                "Physics": "Standard physical laws apply",
                "Technology": "Current technological limitations",
                "Society": "Human nature drives social organization"
            }
        
        return laws

    def _generate_calendar_system(self, world_type: WorldType) -> Dict[str, Any]:
        calendar = {
            "days_per_week": random.choice([5, 6, 7, 8]),
            "weeks_per_month": random.choice([3, 4, 5]),
            "months_per_year": random.choice([10, 12, 13, 16]),
            "seasons": random.choice([["Spring", "Summer", "Fall", "Winter"], 
                                    ["Wet", "Dry"], 
                                    ["Growing", "Harvest", "Rest"]]),
            "year_zero_event": "Founding of the Great Alliance" if world_type == WorldType.FANTASY else "First Colony Landing"
        }
        
        total_days = calendar["days_per_week"] * calendar["weeks_per_month"] * calendar["months_per_year"]
        calendar["days_per_year"] = total_days
        
        return calendar

class WorldBuildingAssistant:
    def __init__(self, db_path: str = "world_building.db"):
        self.db_path = db_path
        self.world_generator = WorldGenerator()
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS worlds (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            world_type TEXT,
            theme TEXT,
            description TEXT,
            locations TEXT,
            cultures TEXT,
            organizations TEXT,
            history TEXT,
            natural_laws TEXT,
            calendar_system TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        conn.commit()
        conn.close()

    async def create_world(self, name: str, world_type: str, theme: str = None) -> World:
        wt = WorldType(world_type)
        world = self.world_generator.generate_world(name, wt, theme)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO worlds VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            world.id, world.name, world.world_type.value, world.theme, world.description,
            json.dumps([asdict(loc) for loc in world.locations]),
            json.dumps([asdict(cult) for cult in world.cultures]),
            json.dumps([asdict(org) for org in world.organizations]),
            json.dumps([asdict(event) for event in world.history]),
            json.dumps(world.natural_laws),
            json.dumps(world.calendar_system),
            world.created_at, world.updated_at
        ))
        
        conn.commit()
        conn.close()
        
        return world

    async def get_world(self, world_id: str) -> Optional[World]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM worlds WHERE id = ?', (world_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        locations = [Location(**loc_data) for loc_data in json.loads(row[5])]
        cultures = [Culture(**cult_data) for cult_data in json.loads(row[6])]
        organizations = [Organization(**org_data) for org_data in json.loads(row[7])]
        history = [HistoricalEvent(**event_data) for event_data in json.loads(row[8])]
        
        return World(
            id=row[0], name=row[1], world_type=WorldType(row[2]), theme=row[3], description=row[4],
            locations=locations, cultures=cultures, organizations=organizations, history=history,
            natural_laws=json.loads(row[9]), calendar_system=json.loads(row[10]),
            created_at=row[11], updated_at=row[12]
        )

    async def explore_location_connections(self, world_id: str) -> Dict[str, Any]:
        world = await self.get_world(world_id)
        if not world:
            return {"error": "World not found"}
        
        # Create network analysis of location connections
        connections = {}
        for location in world.locations:
            connections[location.name] = []
            for conn_id in location.connections:
                connected_loc = next((loc for loc in world.locations if loc.id == conn_id), None)
                if connected_loc:
                    connections[location.name].append(connected_loc.name)
        
        # Find central locations (most connected)
        centrality = {name: len(conns) for name, conns in connections.items()}
        most_central = max(centrality.items(), key=lambda x: x[1]) if centrality else ("None", 0)
        
        return {
            "world_name": world.name,
            "total_locations": len(world.locations),
            "connections": connections,
            "most_central_location": most_central[0],
            "connectivity_score": most_central[1]
        }

    async def analyze_cultural_tensions(self, world_id: str) -> Dict[str, Any]:
        world = await self.get_world(world_id)
        if not world:
            return {"error": "World not found"}
        
        tensions = []
        alliances = []
        
        for culture in world.cultures:
            for other_id, relationship in culture.relationships.items():
                other_culture = next((c for c in world.cultures if c.id == other_id), None)
                if other_culture:
                    if relationship in ["Enemies", "Rivals", "Suspicious"]:
                        tensions.append({
                            "cultures": [culture.name, other_culture.name],
                            "relationship": relationship,
                            "potential_conflict": self._assess_conflict_potential(culture, other_culture)
                        })
                    elif relationship in ["Allies", "Trading Partners"]:
                        alliances.append({
                            "cultures": [culture.name, other_culture.name],
                            "relationship": relationship,
                            "stability": self._assess_alliance_stability(culture, other_culture)
                        })
        
        return {
            "world_name": world.name,
            "tensions": tensions,
            "alliances": alliances,
            "stability_assessment": "High tension" if len(tensions) > len(alliances) else "Relatively stable"
        }

    def _assess_conflict_potential(self, culture1: Culture, culture2: Culture) -> str:
        # Analyze cultural values and aspects for conflict potential
        conflicting_aspects = 0
        
        if culture1.aspects[CultureAspect.GOVERNMENT] != culture2.aspects[CultureAspect.GOVERNMENT]:
            conflicting_aspects += 1
        if culture1.aspects[CultureAspect.RELIGION] != culture2.aspects[CultureAspect.RELIGION]:
            conflicting_aspects += 1
        
        common_values = len(set(culture1.values) & set(culture2.values))
        
        if conflicting_aspects > 1 and common_values < 2:
            return "High"
        elif conflicting_aspects > 0 or common_values < 1:
            return "Medium"
        else:
            return "Low"

    def _assess_alliance_stability(self, culture1: Culture, culture2: Culture) -> str:
        common_values = len(set(culture1.values) & set(culture2.values))
        similar_aspects = sum(1 for aspect in CultureAspect 
                            if culture1.aspects[aspect] == culture2.aspects[aspect])
        
        if common_values >= 2 and similar_aspects >= 3:
            return "Very Stable"
        elif common_values >= 1 and similar_aspects >= 2:
            return "Stable"
        else:
            return "Fragile"

    async def generate_plot_hooks(self, world_id: str, location_name: str = None) -> Dict[str, Any]:
        world = await self.get_world(world_id)
        if not world:
            return {"error": "World not found"}
        
        location = None
        if location_name:
            location = next((loc for loc in world.locations if loc.name.lower() == location_name.lower()), None)
        else:
            location = random.choice(world.locations)
        
        hooks = []
        
        # Location-based hooks
        hooks.append(f"Strange occurrences in {location.name} threaten the {random.choice(location.inhabitants)}")
        if location.dangers:
            hooks.append(f"The {random.choice(location.dangers)} in {location.name} has grown worse")
        if location.resources:
            hooks.append(f"A dispute over {random.choice(location.resources)} in {location.name} escalates")
        
        # Culture-based hooks
        if world.cultures:
            culture = random.choice(world.cultures)
            hooks.append(f"The {culture.name} face a crisis that challenges their core values")
            if culture.taboos:
                hooks.append(f"Someone has violated the {random.choice(culture.taboos)} taboo among the {culture.name}")
        
        # Organization-based hooks
        if world.organizations:
            org = random.choice(world.organizations)
            hooks.append(f"The {org.name} seeks adventurers for a dangerous mission")
            if org.enemies:
                enemy_org = next((o for o in world.organizations if o.id in org.enemies), None)
                if enemy_org:
                    hooks.append(f"Conflict between {org.name} and {enemy_org.name} reaches a tipping point")
        
        # Historical hooks
        if world.history:
            event = random.choice(world.history)
            hooks.append(f"Secrets from {event.name} are discovered, changing everything")
            hooks.append(f"The consequences of {event.name} finally catch up to the present")
        
        return {
            "world_name": world.name,
            "focus_location": location.name,
            "plot_hooks": random.sample(hooks, min(5, len(hooks))),
            "hook_types": ["Mystery", "Conflict", "Discovery", "Political", "Personal"]
        }

if __name__ == "__main__":
    async def main():
        world_assistant = WorldBuildingAssistant()
        
        # Create a sample fantasy world
        world = await world_assistant.create_world(
            "Aethermoor", 
            "fantasy", 
            "Ancient magic awakens in a modern world"
        )
        
        print(f"Created world: {world.name}")
        print(f"Theme: {world.theme}")
        print(f"Locations: {len(world.locations)}")
        print(f"Cultures: {len(world.cultures)}")
        
        # Explore connections
        connections = await world_assistant.explore_location_connections(world.id)
        print(f"\nMost connected location: {connections['most_central_location']}")
        
        # Analyze tensions
        tensions = await world_assistant.analyze_cultural_tensions(world.id)
        print(f"Political climate: {tensions['stability_assessment']}")
        
        # Generate plot hooks
        hooks = await world_assistant.generate_plot_hooks(world.id)
        print(f"\nSample plot hooks:")
        for hook in hooks["plot_hooks"][:3]:
            print(f"- {hook}")
    
    asyncio.run(main())