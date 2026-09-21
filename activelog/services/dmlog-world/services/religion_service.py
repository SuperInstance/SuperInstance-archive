"""
Pantheon and religion generation service.
"""

import random
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from sqlalchemy.orm import Session
import logging

from ..models.religion import (
    ReligionType, DeityRank, Alignment, ClericDomain, WorshipPractice,
    DeitySchema, PantheonSchema, ReligiousOrderSchema, TempleSchema,
    PantheonGenerationRequest, DeityGenerationRequest, ReligionQueryRequest,
    ReligionResponse, DeityRelationship, DivineManifestation
)
from ..config import Config

logger = logging.getLogger(__name__)

class ReligionService:
    def __init__(self):
        self.config = Config()
        self.naming_libraries = self._initialize_naming_libraries()
        self.domain_relationships = self._initialize_domain_relationships()
        self.mythology_templates = self._initialize_mythology_templates()
        self.order_templates = self._initialize_order_templates()
        
    def _initialize_naming_libraries(self) -> Dict[str, List[str]]:
        """Initialize naming libraries for religious elements."""
        
        return {
            "deity_prefixes": [
                "Aether", "Sol", "Luna", "Ignis", "Aqua", "Terra", "Ventus", 
                "Lux", "Umbra", "Vita", "Mortis", "Tempus", "Fatum", "Vis"
            ],
            "deity_suffixes": [
                "ius", "ia", "us", "a", "on", "is", "os", "ara", "iel", "eth",
                "anis", "oris", "alis", "tha", "dur", "mol", "grim", "thor"
            ],
            "divine_titles": [
                "the Eternal", "the Wise", "the Mighty", "the Merciful", "the Just",
                "the Creator", "the Destroyer", "the Protector", "the Guide", "the Judge",
                "Lightbringer", "Stormcaller", "Earthshaker", "Lifegiver", "Soulguard"
            ],
            "pantheon_themes": {
                "nature": ["Forest", "Mountain", "Ocean", "Sky", "Earth", "Wild"],
                "elemental": ["Fire", "Water", "Earth", "Air", "Lightning", "Ice"],
                "cosmic": ["Star", "Moon", "Sun", "Void", "Time", "Fate"],
                "civilization": ["Order", "Justice", "Knowledge", "Art", "Trade", "War"]
            },
            "order_types": [
                "Brotherhood", "Sisterhood", "Order", "Circle", "Guild", "Covenant",
                "Legion", "Watch", "Guard", "Temple", "Sanctuary", "Abbey"
            ],
            "temple_names": [
                "Temple", "Cathedral", "Shrine", "Sanctuary", "Chapel", "Abbey",
                "Monastery", "Basilica", "Tabernacle", "Holy Site"
            ]
        }

    def _initialize_domain_relationships(self) -> Dict[ClericDomain, Dict[str, List[ClericDomain]]]:
        """Initialize relationships between domains."""
        
        return {
            ClericDomain.LIFE: {
                "allies": [ClericDomain.LIGHT, ClericDomain.NATURE, ClericDomain.PEACE],
                "enemies": [ClericDomain.DEATH, ClericDomain.GRAVE],
                "neutral": [ClericDomain.KNOWLEDGE, ClericDomain.ORDER]
            },
            ClericDomain.DEATH: {
                "allies": [ClericDomain.GRAVE, ClericDomain.TWILIGHT],
                "enemies": [ClericDomain.LIFE, ClericDomain.LIGHT],
                "neutral": [ClericDomain.KNOWLEDGE, ClericDomain.ORDER]
            },
            ClericDomain.WAR: {
                "allies": [ClericDomain.FORGE, ClericDomain.ORDER],
                "enemies": [ClericDomain.PEACE],
                "neutral": [ClericDomain.TEMPEST, ClericDomain.LIGHT]
            },
            ClericDomain.KNOWLEDGE: {
                "allies": [ClericDomain.LIGHT, ClericDomain.ORDER, ClericDomain.ARCANA],
                "enemies": [ClericDomain.TRICKERY],
                "neutral": [ClericDomain.NATURE, ClericDomain.TEMPEST]
            },
            ClericDomain.NATURE: {
                "allies": [ClericDomain.LIFE, ClericDomain.TEMPEST],
                "enemies": [ClericDomain.FORGE],
                "neutral": [ClericDomain.KNOWLEDGE, ClericDomain.PEACE]
            },
            ClericDomain.TRICKERY: {
                "allies": [ClericDomain.TWILIGHT],
                "enemies": [ClericDomain.LIGHT, ClericDomain.ORDER, ClericDomain.KNOWLEDGE],
                "neutral": [ClericDomain.NATURE]
            }
        }

    def _initialize_mythology_templates(self) -> Dict[str, List[str]]:
        """Initialize templates for generating mythology."""
        
        return {
            "creation_myths": [
                "{deity} forged the world from the {material} of the {realm}",
                "In the beginning, {deity} separated {element1} from {element2}",
                "{deity} dreamed the world into existence during the {time_period}",
                "The tears of {deity} became the {feature}, giving life to all",
                "{deity} sacrificed {sacrifice} to create {creation}"
            ],
            "heroic_myths": [
                "{deity} battled the {monster} for {duration} to protect {protected}",
                "When {deity} lost {lost_item}, {consequence} befell the world",
                "{deity} taught {taught_skill} to mortals, earning their devotion",
                "The {artifact} was created when {deity} {creation_method}"
            ],
            "materials": ["essence", "bones", "blood", "breath", "dreams", "song"],
            "realms": ["void", "primordial chaos", "first light", "eternal flame", "endless sea"],
            "time_periods": ["great silence", "first age", "time before time", "eternal moment"],
            "features": ["oceans", "mountains", "forests", "rivers", "stars", "souls"],
            "monsters": ["chaos serpent", "void dragon", "shadow titan", "primordial beast"]
        }

    def _initialize_order_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize templates for religious orders."""
        
        return {
            "monastery": {
                "hierarchy": ["Novice", "Brother/Sister", "Prior", "Abbot/Abbess"],
                "practices": [WorshipPractice.DAILY_PRAYER, WorshipPractice.MEDITATION, WorshipPractice.STUDY],
                "requirements": ["vow of poverty", "vow of chastity", "vow of obedience"],
                "activities": ["copying manuscripts", "healing", "farming", "brewing"]
            },
            "knighthood": {
                "hierarchy": ["Squire", "Knight", "Knight-Commander", "Grand Master"],
                "practices": [WorshipPractice.DAILY_PRAYER, WorshipPractice.COMBAT_TRAINING],
                "requirements": ["noble birth or sponsorship", "martial prowess", "code of honor"],
                "activities": ["protecting pilgrims", "crusading", "training", "charity"]
            },
            "cult": {
                "hierarchy": ["Initiate", "Devotee", "Fanatic", "High Priest"],
                "practices": [WorshipPractice.SACRIFICE, WorshipPractice.RITUAL, WorshipPractice.SECRECY],
                "requirements": ["absolute loyalty", "secrecy oath", "initiation ritual"],
                "activities": ["secret rituals", "recruiting", "eliminating enemies", "gathering power"]
            }
        }

    async def generate_pantheon(
        self,
        request: PantheonGenerationRequest,
        db_session: Optional[Session] = None
    ) -> ReligionResponse:
        """Generate a complete pantheon with deities and relationships."""
        
        start_time = datetime.utcnow()
        
        try:
            # Set random seed if provided
            if request.seed:
                random.seed(request.seed)
            
            # Generate pantheon name if not provided
            pantheon_name = request.name or await self._generate_pantheon_name(request.cultural_theme)
            
            # Create base pantheon
            pantheon = PantheonSchema(
                id=str(uuid.uuid4()),
                name=pantheon_name,
                religion_type=request.religion_type,
                cultural_origin=request.cultural_theme,
                primary_alignment=request.alignment_tendency
            )
            
            # Generate deities
            deities = await self._generate_deities_for_pantheon(pantheon, request)
            pantheon.deities = deities
            
            # Set pantheon leader
            pantheon.pantheon_leader = await self._select_pantheon_leader(deities)
            
            # Generate relationships if requested
            if request.generate_relationships:
                await self._generate_deity_relationships(deities)
            
            # Generate mythology if requested
            if request.generate_mythology:
                pantheon.creation_story = await self._generate_creation_story(pantheon, deities)
                pantheon.afterlife_beliefs = await self._generate_afterlife_beliefs(pantheon)
                
                for deity in deities:
                    deity.major_myths = await self._generate_deity_myths(deity, deities)
            
            # Generate religious orders if requested
            religious_orders = []
            if request.generate_orders:
                religious_orders = await self._generate_religious_orders(pantheon, deities)
            
            # Calculate follower demographics
            pantheon.total_followers = await self._estimate_followers(pantheon, request.predominant_race)
            pantheon.follower_demographics = await self._generate_follower_demographics(
                pantheon.total_followers, request.predominant_race
            )
            
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            return ReligionResponse(
                success=True,
                pantheon=pantheon,
                deities=deities,
                religious_orders=religious_orders,
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"Error generating pantheon: {e}")
            return ReligionResponse(
                success=False,
                message=f"Failed to generate pantheon: {str(e)}",
                errors=[str(e)]
            )

    async def _generate_pantheon_name(self, cultural_theme: str) -> str:
        """Generate name for pantheon based on cultural theme."""
        
        theme_names = {
            "fantasy": ["Celestial Court", "Divine Circle", "Sacred Assembly", "Eternal Pantheon"],
            "mythological": ["Ancient Gods", "Primordial Powers", "Elder Divinities", "First Born"],
            "historical": ["Temple Gods", "City Protectors", "Tribal Spirits", "Royal Deities"],
            "elemental": ["Elemental Lords", "Primal Forces", "Nature's Guardians", "Storm Callers"],
            "cosmic": ["Star Council", "Void Walkers", "Time Keepers", "Fate Weavers"]
        }
        
        names = theme_names.get(cultural_theme, theme_names["fantasy"])
        return random.choice(names)

    async def _generate_deities_for_pantheon(
        self,
        pantheon: PantheonSchema,
        request: PantheonGenerationRequest
    ) -> List[DeitySchema]:
        """Generate deities for the pantheon."""
        
        deities = []
        
        # Determine deity distribution by rank
        greater_count = max(1, request.deity_count // 6)  # ~15% greater gods
        intermediate_count = max(2, request.deity_count // 3)  # ~33% intermediate
        lesser_count = request.deity_count - greater_count - intermediate_count
        
        # Generate greater deities
        for _ in range(greater_count):
            deity = await self._generate_single_deity(
                pantheon.id, DeityRank.GREATER, request
            )
            deities.append(deity)
        
        # Generate intermediate deities
        for _ in range(intermediate_count):
            deity = await self._generate_single_deity(
                pantheon.id, DeityRank.INTERMEDIATE, request
            )
            deities.append(deity)
        
        # Generate lesser deities
        for _ in range(lesser_count):
            rank = DeityRank.LESSER
            if request.include_lesser_deities and random.random() < 0.3:
                rank = DeityRank.DEMIGOD
            
            deity = await self._generate_single_deity(pantheon.id, rank, request)
            deities.append(deity)
        
        # Generate hero deities if requested
        if request.include_hero_deities:
            hero_count = min(3, request.deity_count // 8)
            for _ in range(hero_count):
                deity = await self._generate_single_deity(
                    pantheon.id, DeityRank.HERO_DEITY, request
                )
                deities.append(deity)
        
        return deities

    async def _generate_single_deity(
        self,
        pantheon_id: str,
        rank: DeityRank,
        request: PantheonGenerationRequest
    ) -> DeitySchema:
        """Generate a single deity."""
        
        # Generate name
        name = await self._generate_deity_name(request.cultural_theme)
        
        # Select alignment
        alignment = await self._select_deity_alignment(request.alignment_tendency, rank)
        
        # Select domains
        domains = await self._select_deity_domains(rank, request.domain_focus)
        
        # Generate portfolio
        portfolio = await self._generate_deity_portfolio(domains, request.cultural_theme)
        
        # Generate appearance and personality
        appearance = await self._generate_deity_appearance(domains, alignment, request.cultural_theme)
        personality = await self._generate_deity_personality(domains, alignment)
        
        # Generate worship details
        worshiper_types = await self._generate_worshiper_types(domains, portfolio)
        holy_symbol = await self._generate_holy_symbol(domains, name)
        
        # Generate titles
        titles = await self._generate_deity_titles(name, domains, portfolio)
        
        deity = DeitySchema(
            id=str(uuid.uuid4()),
            name=name,
            titles=titles,
            rank=rank,
            alignment=alignment,
            domains=domains,
            portfolio=portfolio,
            appearance=appearance,
            personality=personality,
            worshiper_types=worshiper_types,
            holy_symbol=holy_symbol,
            pantheon_id=pantheon_id
        )
        
        # Generate additional details based on rank
        if rank in [DeityRank.GREATER, DeityRank.INTERMEDIATE]:
            deity.divine_realm = await self._generate_divine_realm(deity)
            deity.divine_abilities = await self._generate_divine_abilities(deity)
        
        if rank != DeityRank.HERO_DEITY:
            deity.preferred_practices = await self._select_worship_practices(domains)
            deity.commandments = await self._generate_commandments(deity)
        
        return deity

    async def _generate_deity_name(self, cultural_theme: str) -> str:
        """Generate deity name based on cultural theme."""
        
        naming = self.naming_libraries
        
        if cultural_theme == "fantasy":
            prefix = random.choice(naming["deity_prefixes"])
            suffix = random.choice(naming["deity_suffixes"])
            return prefix + suffix
        
        elif cultural_theme == "mythological":
            # Use more traditional-sounding names
            mythological_names = [
                "Aethon", "Caelus", "Dione", "Erebus", "Fortuna", "Gaia",
                "Helios", "Iris", "Janus", "Kore", "Luna", "Minerva"
            ]
            return random.choice(mythological_names)
        
        else:
            # Generate compound names
            elements = ["Sol", "Luna", "Ignis", "Aqua", "Terra", "Aer", "Lux", "Umbra"]
            descriptors = ["Magnus", "Prima", "Eternal", "Sacred", "Divine"]
            
            if random.random() < 0.6:
                return random.choice(elements) + random.choice(naming["deity_suffixes"])
            else:
                return random.choice(descriptors) + " " + random.choice(elements)

    async def _select_deity_alignment(
        self,
        tendency: Optional[Alignment],
        rank: DeityRank
    ) -> Alignment:
        """Select appropriate alignment for deity."""
        
        if tendency:
            # 70% chance to follow pantheon tendency
            if random.random() < 0.7:
                return tendency
        
        # Greater deities more likely to be extreme alignments
        if rank == DeityRank.GREATER:
            weights = {
                Alignment.LAWFUL_GOOD: 15,
                Alignment.NEUTRAL_GOOD: 10,
                Alignment.CHAOTIC_GOOD: 10,
                Alignment.LAWFUL_NEUTRAL: 10,
                Alignment.TRUE_NEUTRAL: 5,
                Alignment.CHAOTIC_NEUTRAL: 10,
                Alignment.LAWFUL_EVIL: 15,
                Alignment.NEUTRAL_EVIL: 10,
                Alignment.CHAOTIC_EVIL: 15
            }
        else:
            # Other deities more balanced
            weights = {alignment: 10 for alignment in Alignment}
            weights[Alignment.TRUE_NEUTRAL] = 15  # Neutral more common
        
        return random.choices(list(weights.keys()), weights=list(weights.values()))[0]

    async def _select_deity_domains(
        self,
        rank: DeityRank,
        focus_domains: List[ClericDomain]
    ) -> List[ClericDomain]:
        """Select domains for deity based on rank."""
        
        # Domain count by rank
        domain_counts = {
            DeityRank.OVERGOD: (4, 6),
            DeityRank.GREATER: (3, 4),
            DeityRank.INTERMEDIATE: (2, 3),
            DeityRank.LESSER: (1, 2),
            DeityRank.DEMIGOD: (1, 2),
            DeityRank.HERO_DEITY: (1, 1)
        }
        
        min_domains, max_domains = domain_counts.get(rank, (1, 2))
        domain_count = random.randint(min_domains, max_domains)
        
        # Start with focus domains if provided
        selected_domains = []
        if focus_domains:
            selected_domains.extend(random.sample(focus_domains, min(len(focus_domains), domain_count)))
        
        # Add additional domains if needed
        available_domains = [d for d in ClericDomain if d not in selected_domains]
        while len(selected_domains) < domain_count and available_domains:
            # Prefer domains that have good relationships with existing ones
            if selected_domains:
                compatible_domains = []
                for existing_domain in selected_domains:
                    relationships = self.domain_relationships.get(existing_domain, {})
                    compatible_domains.extend(relationships.get("allies", []))
                    compatible_domains.extend(relationships.get("neutral", []))
                
                compatible_available = [d for d in compatible_domains if d in available_domains]
                if compatible_available:
                    next_domain = random.choice(compatible_available)
                else:
                    next_domain = random.choice(available_domains)
            else:
                next_domain = random.choice(available_domains)
            
            selected_domains.append(next_domain)
            available_domains.remove(next_domain)
        
        return selected_domains

    async def _generate_deity_portfolio(
        self,
        domains: List[ClericDomain],
        cultural_theme: str
    ) -> List[str]:
        """Generate deity's portfolio (areas of influence)."""
        
        domain_portfolios = {
            ClericDomain.WAR: ["battle", "strategy", "courage", "victory", "soldiers"],
            ClericDomain.DEATH: ["death", "undeath", "murder", "funeral rites", "graves"],
            ClericDomain.LIFE: ["birth", "healing", "growth", "fertility", "vitality"],
            ClericDomain.LIGHT: ["sun", "truth", "revelation", "hope", "dawn"],
            ClericDomain.KNOWLEDGE: ["wisdom", "learning", "magic", "prophecy", "secrets"],
            ClericDomain.NATURE: ["wilderness", "animals", "seasons", "weather", "plants"],
            ClericDomain.TEMPEST: ["storms", "sea", "lightning", "rain", "wind"],
            ClericDomain.TRICKERY: ["thieves", "lies", "illusion", "luck", "rogues"],
            ClericDomain.FORGE: ["crafting", "creation", "smithing", "invention", "artisans"],
            ClericDomain.GRAVE: ["burial", "rest", "memory", "ancestors", "mourning"],
            ClericDomain.ORDER: ["law", "justice", "civilization", "honor", "tradition"],
            ClericDomain.PEACE: ["harmony", "diplomacy", "friendship", "calm", "meditation"]
        }
        
        portfolio = []
        for domain in domains:
            domain_items = domain_portfolios.get(domain, [domain.value])
            # Select 2-3 items from each domain
            selected = random.sample(domain_items, min(len(domain_items), random.randint(2, 3)))
            portfolio.extend(selected)
        
        # Add cultural theme-specific elements
        if cultural_theme == "elemental":
            elemental_additions = ["fire", "water", "earth", "air", "ice", "lightning"]
            portfolio.extend(random.sample(elemental_additions, min(2, len(elemental_additions))))
        elif cultural_theme == "nature":
            nature_additions = ["forests", "mountains", "rivers", "animals", "seasons"]
            portfolio.extend(random.sample(nature_additions, min(2, len(nature_additions))))
        
        return list(set(portfolio))  # Remove duplicates

    async def _generate_deity_appearance(
        self,
        domains: List[ClericDomain],
        alignment: Alignment,
        cultural_theme: str
    ) -> str:
        """Generate deity appearance description."""
        
        # Base templates
        templates = [
            "Appears as {form} with {feature1} and {feature2}",
            "Manifests as {form} surrounded by {aura}",
            "Takes the form of {form}, {detail}"
        ]
        
        # Determine form based on domains
        forms = []
        if ClericDomain.WAR in domains:
            forms.extend(["armored warrior", "battle-scarred veteran", "strategic commander"])
        if ClericDomain.NATURE in domains:
            forms.extend(["wild hunter", "forest guardian", "seasonal avatar"])
        if ClericDomain.KNOWLEDGE in domains:
            forms.extend(["wise sage", "scholarly figure", "ancient librarian"])
        if ClericDomain.LIGHT in domains:
            forms.extend(["radiant being", "sun-crowned figure", "glowing presence"])
        
        if not forms:
            forms = ["majestic figure", "divine presence", "ethereal being"]
        
        # Determine features based on alignment
        good_features = ["compassionate eyes", "benevolent smile", "healing hands"]
        evil_features = ["cruel gaze", "menacing presence", "shadowy aura"]
        neutral_features = ["impassive countenance", "balanced demeanor", "measured gaze"]
        
        if "good" in alignment.value:
            features = good_features
        elif "evil" in alignment.value:
            features = evil_features
        else:
            features = neutral_features
        
        template = random.choice(templates)
        return template.format(
            form=random.choice(forms),
            feature1=random.choice(features),
            feature2=random.choice(features),
            aura=f"an aura of {random.choice(['power', 'wisdom', 'mystery', 'authority'])}",
            detail=f"often {random.choice(['contemplating', 'observing', 'commanding', 'teaching'])}"
        )

    async def _generate_deity_personality(
        self,
        domains: List[ClericDomain],
        alignment: Alignment
    ) -> str:
        """Generate deity personality description."""
        
        # Base traits from alignment
        alignment_traits = {
            Alignment.LAWFUL_GOOD: ["just", "merciful", "honorable", "protective"],
            Alignment.NEUTRAL_GOOD: ["kind", "helpful", "compassionate", "generous"],
            Alignment.CHAOTIC_GOOD: ["free-spirited", "rebellious", "passionate", "artistic"],
            Alignment.LAWFUL_NEUTRAL: ["orderly", "traditional", "methodical", "dutiful"],
            Alignment.TRUE_NEUTRAL: ["balanced", "pragmatic", "impartial", "natural"],
            Alignment.CHAOTIC_NEUTRAL: ["unpredictable", "whimsical", "changeable", "free"],
            Alignment.LAWFUL_EVIL: ["tyrannical", "oppressive", "manipulative", "calculating"],
            Alignment.NEUTRAL_EVIL: ["selfish", "cruel", "opportunistic", "malicious"],
            Alignment.CHAOTIC_EVIL: ["destructive", "chaotic", "sadistic", "unpredictable"]
        }
        
        base_traits = alignment_traits.get(alignment, ["mysterious"])
        
        # Add domain-specific traits
        domain_traits = {
            ClericDomain.WAR: ["aggressive", "tactical", "courageous"],
            ClericDomain.KNOWLEDGE: ["intellectual", "curious", "patient"],
            ClericDomain.NATURE: ["wild", "instinctual", "protective"],
            ClericDomain.TRICKERY: ["clever", "mischievous", "cunning"],
            ClericDomain.PEACE: ["calm", "diplomatic", "serene"]
        }
        
        all_traits = base_traits[:]
        for domain in domains:
            all_traits.extend(domain_traits.get(domain, []))
        
        # Select 3-4 traits
        selected_traits = random.sample(all_traits, min(len(all_traits), random.randint(3, 4)))
        
        return f"Known for being {', '.join(selected_traits[:-1])}, and {selected_traits[-1]}"

    async def _generate_worshiper_types(self, domains: List[ClericDomain], portfolio: List[str]) -> List[str]:
        """Generate types of people who worship this deity."""
        
        domain_worshipers = {
            ClericDomain.WAR: ["soldiers", "mercenaries", "generals", "veterans"],
            ClericDomain.KNOWLEDGE: ["scholars", "wizards", "students", "researchers"],
            ClericDomain.NATURE: ["druids", "rangers", "hunters", "farmers"],
            ClericDomain.FORGE: ["smiths", "craftsmen", "inventors", "artisans"],
            ClericDomain.LIFE: ["healers", "midwives", "doctors", "caretakers"],
            ClericDomain.TRICKERY: ["thieves", "spies", "gamblers", "rogues"],
            ClericDomain.TEMPEST: ["sailors", "fishermen", "storm-riders", "sea merchants"]
        }
        
        worshipers = []
        for domain in domains:
            worshipers.extend(domain_worshipers.get(domain, []))
        
        # Add general worshipers
        general_worshipers = ["common folk", "nobles", "clergy", "pilgrims"]
        worshipers.extend(random.sample(general_worshipers, 2))
        
        return list(set(worshipers))

    async def _generate_holy_symbol(self, domains: List[ClericDomain], deity_name: str) -> str:
        """Generate holy symbol description."""
        
        domain_symbols = {
            ClericDomain.WAR: ["crossed swords", "shield", "spear", "war hammer"],
            ClericDomain.LIFE: ["ankh", "tree of life", "healing hands", "blooming flower"],
            ClericDomain.LIGHT: ["sun disc", "radiant star", "golden flame", "glowing orb"],
            ClericDomain.DEATH: ["skull", "scythe", "raven", "black rose"],
            ClericDomain.KNOWLEDGE: ["open book", "eye", "scroll", "crystal orb"],
            ClericDomain.NATURE: ["oak leaf", "antlers", "wolf head", "mountain peak"],
            ClericDomain.TEMPEST: ["lightning bolt", "storm cloud", "trident", "whirlwind"],
            ClericDomain.FORGE: ["hammer and anvil", "forge flame", "crafting tools"]
        }
        
        possible_symbols = []
        for domain in domains:
            possible_symbols.extend(domain_symbols.get(domain, []))
        
        if possible_symbols:
            return random.choice(possible_symbols)
        else:
            return f"stylized {deity_name[0].lower()}"

    async def _generate_deity_titles(
        self,
        name: str,
        domains: List[ClericDomain],
        portfolio: List[str]
    ) -> List[str]:
        """Generate titles/epithets for deity."""
        
        titles = []
        
        # Add domain-based titles
        domain_titles = {
            ClericDomain.WAR: ["the Conqueror", "Battle-Lord", "the Strategic"],
            ClericDomain.KNOWLEDGE: ["the Wise", "the All-Seeing", "the Teacher"],
            ClericDomain.LIGHT: ["the Radiant", "Dawn-Bringer", "the Illuminator"],
            ClericDomain.NATURE: ["the Wild", "Forest-Walker", "the Seasonal"]
        }
        
        for domain in domains:
            domain_title_list = domain_titles.get(domain, [])
            if domain_title_list:
                titles.append(random.choice(domain_title_list))
        
        # Add portfolio-based titles
        if "sun" in portfolio:
            titles.append("the Solar")
        if "storm" in portfolio or "lightning" in portfolio:
            titles.append("Storm-Caller")
        if "death" in portfolio:
            titles.append("the Final")
        
        # Add general divine titles
        general_titles = self.naming_libraries["divine_titles"]
        if len(titles) < 3:
            additional = random.sample(general_titles, min(2, len(general_titles)))
            titles.extend(additional)
        
        return titles[:3]  # Limit to 3 titles

    async def _select_pantheon_leader(self, deities: List[DeitySchema]) -> Optional[str]:
        """Select the leader/head of the pantheon."""
        
        # Prefer greater deities
        greater_deities = [d for d in deities if d.rank == DeityRank.GREATER]
        if greater_deities:
            # Among greater deities, prefer those with appropriate domains
            leadership_domains = [ClericDomain.ORDER, ClericDomain.LIGHT, ClericDomain.KNOWLEDGE]
            suitable_leaders = [
                d for d in greater_deities 
                if any(domain in d.domains for domain in leadership_domains)
            ]
            
            if suitable_leaders:
                return random.choice(suitable_leaders).id
            else:
                return random.choice(greater_deities).id
        
        # Fallback to intermediate deities
        intermediate_deities = [d for d in deities if d.rank == DeityRank.INTERMEDIATE]
        if intermediate_deities:
            return random.choice(intermediate_deities).id
        
        # Last resort - any deity
        return random.choice(deities).id if deities else None

    async def _generate_deity_relationships(self, deities: List[DeitySchema]) -> None:
        """Generate relationships between deities."""
        
        for i, deity1 in enumerate(deities):
            for deity2 in deities[i+1:]:
                relationship = await self._determine_deity_relationship(deity1, deity2)
                
                if relationship == "ally":
                    deity1.allies.append(deity2.id)
                    deity2.allies.append(deity1.id)
                elif relationship == "enemy":
                    deity1.enemies.append(deity2.id)
                    deity2.enemies.append(deity1.id)
                elif relationship == "rival":
                    deity1.rivals.append(deity2.id)
                    deity2.rivals.append(deity1.id)

    async def _determine_deity_relationship(
        self,
        deity1: DeitySchema,
        deity2: DeitySchema
    ) -> str:
        """Determine relationship between two deities."""
        
        # Check domain compatibility
        domain_score = 0
        for domain1 in deity1.domains:
            for domain2 in deity2.domains:
                relationships = self.domain_relationships.get(domain1, {})
                if domain2 in relationships.get("allies", []):
                    domain_score += 2
                elif domain2 in relationships.get("enemies", []):
                    domain_score -= 2
                elif domain2 in relationships.get("neutral", []):
                    domain_score += 0
        
        # Check alignment compatibility
        alignment_score = await self._calculate_alignment_compatibility(
            deity1.alignment, deity2.alignment
        )
        
        total_score = domain_score + alignment_score
        
        # Determine relationship based on score
        if total_score >= 3:
            return "ally"
        elif total_score <= -3:
            return "enemy"
        elif abs(total_score) <= 1:
            return "rival"  # Similar enough to be rivals
        else:
            return "neutral"

    async def _calculate_alignment_compatibility(
        self,
        alignment1: Alignment,
        alignment2: Alignment
    ) -> int:
        """Calculate compatibility score between alignments."""
        
        # Parse alignments
        def parse_alignment(alignment):
            parts = alignment.value.split('_')
            ethics = parts[0]  # lawful, neutral, chaotic
            morals = parts[-1]  # good, neutral, evil
            return ethics, morals
        
        ethics1, morals1 = parse_alignment(alignment1)
        ethics2, morals2 = parse_alignment(alignment2)
        
        score = 0
        
        # Ethics compatibility
        if ethics1 == ethics2:
            score += 1
        elif (ethics1 == "lawful" and ethics2 == "chaotic") or (ethics1 == "chaotic" and ethics2 == "lawful"):
            score -= 2
        
        # Morals compatibility
        if morals1 == morals2:
            score += 1
        elif (morals1 == "good" and morals2 == "evil") or (morals1 == "evil" and morals2 == "good"):
            score -= 2
        
        return score

    async def _generate_creation_story(
        self,
        pantheon: PantheonSchema,
        deities: List[DeitySchema]
    ) -> str:
        """Generate creation story for the pantheon."""
        
        templates = self.mythology_templates["creation_myths"]
        template = random.choice(templates)
        
        # Find suitable creator deity
        creator_candidates = [
            d for d in deities
            if d.rank in [DeityRank.GREATER, DeityRank.OVERGOD] and
            any(domain in [ClericDomain.LIFE, ClericDomain.LIGHT, ClericDomain.FORGE, ClericDomain.NATURE] 
                for domain in d.domains)
        ]
        
        creator = random.choice(creator_candidates) if creator_candidates else random.choice(deities)
        
        return template.format(
            deity=creator.name,
            material=random.choice(self.mythology_templates["materials"]),
            realm=random.choice(self.mythology_templates["realms"]),
            element1="light",
            element2="darkness",
            time_period=random.choice(self.mythology_templates["time_periods"]),
            feature=random.choice(self.mythology_templates["features"]),
            sacrifice="divine essence",
            creation="the mortal realm"
        )

    async def _generate_afterlife_beliefs(self, pantheon: PantheonSchema) -> Dict[str, str]:
        """Generate afterlife beliefs for the pantheon."""
        
        beliefs = {}
        
        if pantheon.religion_type == ReligionType.MONOTHEISTIC:
            beliefs["heaven"] = "Eternal paradise for the faithful"
            beliefs["hell"] = "Punishment for the wicked"
        else:
            # Multiple afterlife destinations
            beliefs["heroic_afterlife"] = "Hall of heroes for the brave and noble"
            beliefs["peaceful_rest"] = "Quiet meadows for the good-hearted"
            beliefs["scholarly_realm"] = "Great library for seekers of knowledge"
            beliefs["punishment"] = "Dark realm for the evil and corrupt"
            beliefs["reincarnation"] = "Return to life in new form based on deeds"
        
        return beliefs

    async def _generate_deity_myths(
        self,
        deity: DeitySchema,
        all_deities: List[DeitySchema]
    ) -> List[str]:
        """Generate myths for a specific deity."""
        
        myths = []
        templates = self.mythology_templates["heroic_myths"]
        
        # Generate 2-4 myths per deity
        for _ in range(random.randint(2, 4)):
            template = random.choice(templates)
            
            myth = template.format(
                deity=deity.name,
                monster=random.choice(self.mythology_templates["monsters"]),
                duration=random.choice(["seven days", "a full year", "countless ages"]),
                protected=random.choice(["mortals", "the innocent", "sacred sites"]),
                lost_item=random.choice(["sacred weapon", "divine crown", "power"]),
                consequence=random.choice(["darkness", "chaos", "suffering"]),
                taught_skill=random.choice(deity.portfolio[:3] if deity.portfolio else ["wisdom"]),
                artifact=f"Sacred {random.choice(['sword', 'amulet', 'crown', 'staff'])}",
                creation_method=f"wept tears of {random.choice(['joy', 'sorrow', 'power'])}"
            )
            
            myths.append(myth)
        
        return myths

    async def _generate_religious_orders(
        self,
        pantheon: PantheonSchema,
        deities: List[DeitySchema]
    ) -> List[ReligiousOrderSchema]:
        """Generate religious orders for the pantheon."""
        
        orders = []
        
        # Generate 3-6 orders
        order_count = random.randint(3, 6)
        
        for _ in range(order_count):
            # Select deity for this order
            deity = random.choice(deities)
            
            # Select order type
            order_types = ["monastery", "knighthood", "cult"]
            weights = [30, 25, 10]  # Monasteries most common, cults rare
            
            # Adjust weights based on deity domains
            if ClericDomain.WAR in deity.domains:
                weights[1] = 40  # More knightly orders
            if any(domain in deity.domains for domain in [ClericDomain.DEATH, ClericDomain.TRICKERY]):
                weights[2] = 25  # More cults for dark deities
            
            order_type = random.choices(order_types, weights=weights)[0]
            
            order = await self._generate_single_religious_order(deity, order_type)
            orders.append(order)
        
        return orders

    async def _generate_single_religious_order(
        self,
        deity: DeitySchema,
        order_type: str
    ) -> ReligiousOrderSchema:
        """Generate a single religious order."""
        
        template = self.order_templates[order_type]
        naming = self.naming_libraries
        
        # Generate name
        order_name = f"{random.choice(naming['order_types'])} of {deity.name}"
        
        # Generate membership size
        size_ranges = {
            "monastery": (20, 100),
            "knighthood": (50, 300),
            "cult": (10, 50)
        }
        min_size, max_size = size_ranges[order_type]
        membership_size = random.randint(min_size, max_size)
        
        order = ReligiousOrderSchema(
            id=str(uuid.uuid4()),
            name=order_name,
            description=f"A {order_type} dedicated to {deity.name}",
            primary_deity=deity.id,
            order_type=order_type,
            leadership_structure=template["hierarchy"],
            membership_size=membership_size,
            membership_requirements=template["requirements"],
            daily_practices=template["practices"],
            core_tenets=await self._generate_order_tenets(deity, order_type)
        )
        
        return order

    async def _generate_order_tenets(self, deity: DeitySchema, order_type: str) -> List[str]:
        """Generate core tenets for a religious order."""
        
        tenets = []
        
        # Add tenets based on deity domains
        domain_tenets = {
            ClericDomain.WAR: ["Protect the innocent through strength", "Honor in battle above all"],
            ClericDomain.KNOWLEDGE: ["Seek truth in all things", "Share wisdom freely"],
            ClericDomain.LIFE: ["Preserve life wherever possible", "Heal the sick and wounded"],
            ClericDomain.LIGHT: ["Illuminate the darkness of ignorance", "Bring hope to the desperate"],
            ClericDomain.NATURE: ["Live in harmony with the natural world", "Protect the wilderness"]
        }
        
        for domain in deity.domains:
            domain_tenet_list = domain_tenets.get(domain, [])
            if domain_tenet_list:
                tenets.append(random.choice(domain_tenet_list))
        
        # Add order type specific tenets
        if order_type == "monastery":
            tenets.append("Live simply and humbly")
        elif order_type == "knighthood":
            tenets.append("Uphold honor and chivalry")
        elif order_type == "cult":
            tenets.append("Absolute devotion to the cause")
        
        return tenets

    async def _estimate_followers(self, pantheon: PantheonSchema, predominant_race: str) -> int:
        """Estimate total followers for the pantheon."""
        
        # Base follower count based on pantheon type
        base_followers = {
            ReligionType.MONOTHEISTIC: 100000,
            ReligionType.POLYTHEISTIC: 500000,
            ReligionType.PANTHEISTIC: 200000,
            ReligionType.ANCESTOR_WORSHIP: 150000,
            ReligionType.ELEMENTAL: 80000,
            ReligionType.NATURE_WORSHIP: 60000
        }
        
        base = base_followers.get(pantheon.religion_type, 100000)
        
        # Add some randomness
        multiplier = random.uniform(0.5, 2.0)
        
        return int(base * multiplier)

    async def _generate_follower_demographics(
        self,
        total_followers: int,
        predominant_race: str
    ) -> Dict[str, int]:
        """Generate demographic breakdown of followers."""
        
        demographics = {}
        
        # Predominant race gets 60-80% of followers
        main_percentage = random.uniform(0.6, 0.8)
        demographics[predominant_race] = int(total_followers * main_percentage)
        
        remaining = total_followers - demographics[predominant_race]
        
        # Distribute remaining among other races
        other_races = ["human", "elf", "dwarf", "halfling", "gnome", "dragonborn", "tiefling"]
        if predominant_race in other_races:
            other_races.remove(predominant_race)
        
        # Select 3-5 other races
        selected_races = random.sample(other_races, min(len(other_races), random.randint(3, 5)))
        
        # Distribute remaining followers
        for i, race in enumerate(selected_races):
            if i == len(selected_races) - 1:
                # Last race gets all remaining
                demographics[race] = remaining
            else:
                # Others get random portion
                portion = random.randint(1, remaining // 2)
                demographics[race] = portion
                remaining -= portion
        
        return demographics

    async def _select_worship_practices(self, domains: List[ClericDomain]) -> List[WorshipPractice]:
        """Select appropriate worship practices for deity domains."""
        
        domain_practices = {
            ClericDomain.WAR: [WorshipPractice.COMBAT_TRAINING, WorshipPractice.DAILY_PRAYER],
            ClericDomain.KNOWLEDGE: [WorshipPractice.STUDY, WorshipPractice.MEDITATION],
            ClericDomain.LIFE: [WorshipPractice.DAILY_PRAYER, WorshipPractice.CHARITY],
            ClericDomain.NATURE: [WorshipPractice.SEASONAL_RITUAL, WorshipPractice.PILGRIMAGE],
            ClericDomain.DEATH: [WorshipPractice.SACRIFICE, WorshipPractice.WEEKLY_SERVICE]
        }
        
        practices = set()
        for domain in domains:
            practices.update(domain_practices.get(domain, [WorshipPractice.DAILY_PRAYER]))
        
        # Ensure at least 2 practices
        if len(practices) < 2:
            all_practices = list(WorshipPractice)
            practices.update(random.sample(all_practices, 2 - len(practices)))
        
        return list(practices)

    async def _generate_commandments(self, deity: DeitySchema) -> List[str]:
        """Generate commandments/moral guidelines for deity."""
        
        commandments = []
        
        # Generate based on alignment
        if "good" in deity.alignment.value:
            commandments.extend([
                "Show compassion to those in need",
                "Protect the innocent from harm",
                "Act with honor and integrity"
            ])
        elif "evil" in deity.alignment.value:
            commandments.extend([
                "Strength conquers weakness",
                "Take what you can, give nothing back",
                "Show no mercy to enemies"
            ])
        else:  # Neutral
            commandments.extend([
                "Maintain balance in all things",
                "Judge each situation on its own merits",
                "Preserve the natural order"
            ])
        
        # Add domain-specific commandments
        domain_commandments = {
            ClericDomain.WAR: ["Never retreat from a just battle"],
            ClericDomain.KNOWLEDGE: ["Never willingly destroy knowledge"],
            ClericDomain.LIFE: ["Take life only when absolutely necessary"],
            ClericDomain.NATURE: ["Respect the balance of nature"]
        }
        
        for domain in deity.domains:
            if domain in domain_commandments:
                commandments.append(domain_commandments[domain])
        
        return commandments[:5]  # Limit to 5 commandments

    async def _generate_divine_realm(self, deity: DeitySchema) -> str:
        """Generate description of deity's divine realm."""
        
        domain_realms = {
            ClericDomain.WAR: "an eternal battlefield where heroes train",
            ClericDomain.KNOWLEDGE: "a vast library containing all knowledge",
            ClericDomain.NATURE: "a pristine wilderness of endless beauty",
            ClericDomain.LIGHT: "a realm of perpetual golden dawn",
            ClericDomain.DEATH: "a quiet realm where souls find rest"
        }
        
        for domain in deity.domains:
            if domain in domain_realms:
                return domain_realms[domain]
        
        return "a magnificent palace in the divine realm"

    async def _generate_divine_abilities(self, deity: DeitySchema) -> List[str]:
        """Generate divine abilities for deity."""
        
        abilities = []
        
        # Base abilities by rank
        if deity.rank == DeityRank.GREATER:
            abilities.extend([
                "Omniscience within portfolio",
                "Avatar creation",
                "Divine intervention",
                "Plane creation"
            ])
        elif deity.rank == DeityRank.INTERMEDIATE:
            abilities.extend([
                "Limited omniscience",
                "Avatar creation",
                "Divine intervention"
            ])
        
        # Domain-specific abilities
        domain_abilities = {
            ClericDomain.WAR: ["Battle foresight", "Weapon blessing", "Tactical omniscience"],
            ClericDomain.KNOWLEDGE: ["Truth detection", "Memory access", "Future sight"],
            ClericDomain.NATURE: ["Animal communication", "Weather control", "Plant growth"],
            ClericDomain.LIGHT: ["Blindness cure", "Darkness banishment", "Hope inspiration"]
        }
        
        for domain in deity.domains:
            if domain in domain_abilities:
                abilities.extend(random.sample(domain_abilities[domain], 2))
        
        return abilities[:6]  # Limit to 6 abilities