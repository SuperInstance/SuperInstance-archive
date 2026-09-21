"""
Plot Twist Generator

Generates plot twists, story complications, and narrative surprises
to enhance D&D campaigns and adventures.
"""

import random
from typing import List, Dict, Any, Optional, Tuple

from ..models.base import Twist, ComplexityLevel, ThemeType
from ..models.adventure import Adventure, Chapter
from ..models.character import Character, Relationship, Motivation
from ..config import PLOT_CONFIG
from .base_generator import BaseGenerator


class PlotTwistGenerator(BaseGenerator):
    """Generates plot twists and story complications"""
    
    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.twist_templates = self._load_twist_templates()
        self.story_structures = PLOT_CONFIG["story_structures"]
        self.foreshadowing_database = self._build_foreshadowing_database()
    
    def _load_twist_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load twist templates by category"""
        return {
            "identity_reveal": {
                "templates": [
                    "The {character} is actually {secret_identity}",
                    "{ally} has been {villain} all along",
                    "The real {important_person} died years ago - this is an impostor",
                    "{character} is the {family_relation} of {antagonist}",
                    "The {mentor} is actually working for the enemy"
                ],
                "elements": {
                    "secret_identities": [
                        "the lost heir to the throne", "a famous criminal", "an ancient dragon",
                        "a celestial in disguise", "the thought-dead hero", "a time traveler",
                        "a shapeshifter", "the prophecied chosen one", "a fallen god",
                        "the antagonist's child", "a mind-controlled victim"
                    ],
                    "family_relations": [
                        "parent", "sibling", "child", "cousin", "twin", "clone",
                        "reincarnation", "alternate timeline version"
                    ]
                },
                "foreshadowing": [
                    "Character knows things they shouldn't", "Unusual reactions to certain topics",
                    "Mysterious past with gaps", "Unexplained skills or knowledge",
                    "Others recognize them but they deny it"
                ]
            },
            "betrayal": {
                "templates": [
                    "{trusted_ally} betrays the party for {motivation}",
                    "The {organization} the party works for has ulterior motives",
                    "{mentor} has been manipulating events from the beginning",
                    "The party's mission was designed to {hidden_purpose}",
                    "{ally} is forced to betray the party to save {loved_one}"
                ],
                "elements": {
                    "motivations": [
                        "personal gain", "family loyalty", "blackmail", "greater good",
                        "revenge", "fear", "love", "duty", "survival", "ideology"
                    ],
                    "hidden_purposes": [
                        "eliminate the party", "test their loyalty", "distract from real plan",
                        "gather intelligence", "remove political enemies", "trigger a prophecy"
                    ]
                },
                "foreshadowing": [
                    "Ally knows too much about enemy plans", "Unexplained absences",
                    "Conflicted behavior", "Secret meetings", "Reluctance to act"
                ]
            },
            "false_information": {
                "templates": [
                    "The {mcguffin} was never real - it was a distraction",
                    "Everything they know about {important_event} is wrong",
                    "The {prophecy} has been deliberately mistranslated",
                    "The party has been chasing the wrong {target}",
                    "The {threat} they're fighting is actually trying to help"
                ],
                "elements": {
                    "mcguffins": [
                        "ancient artifact", "magical weapon", "important document",
                        "treasure map", "secret formula", "divine relic", "lost spell"
                    ],
                    "important_events": [
                        "the ancient war", "the king's death", "the great disaster",
                        "the hero's sacrifice", "the villain's defeat", "the prophecy"
                    ]
                },
                "foreshadowing": [
                    "Information sources are unreliable", "Conflicting accounts of events",
                    "Documents seem too convenient", "Witnesses change their stories"
                ]
            },
            "hidden_connection": {
                "templates": [
                    "The {location} is actually {secret_nature}",
                    "All the {events} are connected to {master_plan}",
                    "{character_a} and {character_b} share a {connection}",
                    "The party's {actions} have been fulfilling {prophecy}",
                    "Every {villain} they've faced serves {master_villain}"
                ],
                "elements": {
                    "secret_natures": [
                        "a prison for an ancient evil", "a portal to another plane",
                        "alive and sentient", "an elaborate illusion", "a testing ground",
                        "the villain's true body", "a divine trial"
                    ],
                    "connections": [
                        "secret past", "shared destiny", "magical bond", "family tie",
                        "curse", "shared trauma", "common enemy", "divine connection"
                    ]
                },
                "foreshadowing": [
                    "Seemingly unrelated events follow patterns", "Recurring symbols",
                    "Similar reactions from different NPCs", "Prophetic dreams"
                ]
            },
            "power_corruption": {
                "templates": [
                    "The {power_source} is slowly corrupting {character}",
                    "Using the {artifact} comes at a terrible price",
                    "Victory against {enemy} requires becoming like them",
                    "The {ally} has been changed by their experiences",
                    "The party's growing power attracts unwanted attention"
                ],
                "elements": {
                    "power_sources": [
                        "magical artifact", "divine blessing", "demonic pact",
                        "ancient knowledge", "draconic heritage", "fel energy",
                        "time manipulation", "mind control abilities"
                    ],
                    "corruption_signs": [
                        "personality changes", "physical transformation",
                        "nightmares and visions", "loss of empathy",
                        "addiction to power", "paranoia", "isolation"
                    ]
                },
                "foreshadowing": [
                    "Gradual personality shifts", "Strange dreams or visions",
                    "Physical changes", "Power feels too easy to use",
                    "NPCs react with fear or suspicion"
                ]
            },
            "time_manipulation": {
                "templates": [
                    "The party has been trapped in a {time_effect}",
                    "Events are happening out of chronological order",
                    "The {character} is from a different timeline",
                    "The party's actions created a temporal paradox",
                    "Someone is manipulating time to change the outcome"
                ],
                "elements": {
                    "time_effects": [
                        "time loop", "time dilation field", "temporal stasis",
                        "accelerated time", "reversed causality", "branching timeline"
                    ],
                    "paradoxes": [
                        "grandfather paradox", "bootstrap paradox", "predestination paradox",
                        "butterfly effect", "causal loop", "temporal displacement"
                    ]
                },
                "foreshadowing": [
                    "Events repeat with variations", "Anachronistic elements",
                    "Prophecies that seem too accurate", "Déjà vu experiences",
                    "Characters knowing things they shouldn't yet know"
                ]
            },
            "parallel_reality": {
                "templates": [
                    "This is actually an alternate version of {familiar_place}",
                    "The party has been shifted to a parallel dimension",
                    "Everyone they know has evil/good counterparts here",
                    "Their actions in this reality affect the real world",
                    "They must choose which reality to preserve"
                ],
                "elements": {
                    "reality_differences": [
                        "moral alignments reversed", "different historical outcomes",
                        "magic works differently", "different physical laws",
                        "roles reversed", "time flows backward"
                    ]
                },
                "foreshadowing": [
                    "Subtle differences in familiar places", "NPCs acting out of character",
                    "Strange reactions to known information", "Impossible coincidences"
                ]
            },
            "moral_dilemma": {
                "templates": [
                    "Defeating {villain} will cause {terrible_consequence}",
                    "The party must choose between saving {option_a} or {option_b}",
                    "The only way to win requires {moral_compromise}",
                    "The {artifact} can save everyone but costs {sacrifice}",
                    "Their greatest enemy was right about {important_truth}"
                ],
                "elements": {
                    "terrible_consequences": [
                        "innocent deaths", "economic collapse", "magical disaster",
                        "planar instability", "breaking natural law", "divine wrath"
                    ],
                    "moral_compromises": [
                        "sacrificing innocents", "using evil methods", "breaking oaths",
                        "betraying allies", "destroying something beautiful", "becoming tyrants"
                    ]
                },
                "foreshadowing": [
                    "Hints about unintended consequences", "Similar moral dilemmas on smaller scales",
                    "NPCs expressing difficult ethical positions", "Benefits of villain's actions"
                ]
            }
        }
    
    def _build_foreshadowing_database(self) -> Dict[str, List[str]]:
        """Build database of foreshadowing techniques"""
        return {
            "subtle_clues": [
                "NPC mentions seemingly unimportant detail",
                "Strange reaction to common object/word",
                "Inconsistency in established facts",
                "Prophecy with multiple interpretations",
                "Recurring symbol or number pattern"
            ],
            "behavioral_hints": [
                "Character acts out of established personality",
                "Unusual knowledge about obscure topics",
                "Emotional reactions that don't match situation",
                "Reluctance to discuss specific subjects",
                "Body language contradicts words"
            ],
            "environmental_clues": [
                "Architecture that doesn't match the region",
                "Anachronistic technology or magic",
                "Animals/plants that shouldn't exist here",
                "Weather patterns that defy explanation",
                "Impossible geometric layouts"
            ],
            "narrative_hints": [
                "Dreams that seem too vivid or prophetic",
                "Legends that mirror current events",
                "Historical records with suspicious gaps",
                "Multiple sources tell conflicting stories",
                "Events happen at suspiciously convenient times"
            ]
        }
    
    async def generate_plot_twist(self, category: Optional[str] = None,
                                impact_level: str = "moderate",
                                context: Optional[Dict[str, Any]] = None) -> Twist:
        """Generate a plot twist"""
        
        # Select category
        if not category:
            categories = list(self.twist_templates.keys())
            category = self.rng.choice(categories)
        
        if category not in self.twist_templates:
            category = "identity_reveal"  # Fallback
        
        template_data = self.twist_templates[category]
        
        # Select template
        template = self.rng.choice(template_data["templates"])
        
        # Fill in template variables
        twist_description = await self._fill_twist_template(template, template_data, context)
        
        # Generate twist
        twist = Twist(
            name=f"{category.replace('_', ' ').title()} Twist",
            description=twist_description,
            twist_type=category,
            impact_level=impact_level,
            timing=self._determine_optimal_timing(category, context)
        )
        
        # Add foreshadowing
        twist.foreshadowing_clues = await self._generate_foreshadowing(category, template_data)
        
        # Add consequences
        twist.consequences = await self._generate_consequences(category, impact_level, context)
        
        # Add prerequisites
        twist.prerequisites = await self._generate_prerequisites(category, context)
        
        return twist
    
    async def _fill_twist_template(self, template: str, template_data: Dict[str, Any],
                                 context: Optional[Dict[str, Any]]) -> str:
        """Fill in template variables with appropriate content"""
        filled_template = template
        
        # Extract variables from template
        import re
        variables = re.findall(r'\{(\w+)\}', template)
        
        for var in variables:
            replacement = await self._get_variable_replacement(var, template_data, context)
            filled_template = filled_template.replace(f"{{{var}}}", replacement)
        
        return filled_template
    
    async def _get_variable_replacement(self, variable: str, template_data: Dict[str, Any],
                                     context: Optional[Dict[str, Any]]) -> str:
        """Get replacement for a template variable"""
        
        # Check context first
        if context and variable in context:
            return str(context[variable])
        
        # Check template elements
        elements = template_data.get("elements", {})
        if variable in elements:
            return self.rng.choice(elements[variable])
        
        # Generate based on variable type
        if variable in ["character", "ally", "mentor", "villain", "antagonist"]:
            return self.generate_name("fantasy")
        elif variable in ["location", "familiar_place"]:
            return self._generate_location_name()
        elif variable in ["organization", "faction"]:
            return self._generate_organization_name()
        elif variable in ["prophecy", "legend"]:
            return "an ancient prophecy"
        elif variable in ["mcguffin", "artifact"]:
            return "a mysterious artifact"
        elif variable in ["loved_one", "important_person"]:
            return "someone dear to them"
        elif variable in ["threat", "enemy"]:
            return "the threat they face"
        elif variable in ["power", "ability"]:
            return "their newfound power"
        elif variable in ["option_a", "option_b"]:
            return "those they swore to protect"
        else:
            return f"[{variable}]"  # Placeholder if no replacement found
    
    def _generate_location_name(self) -> str:
        """Generate a location name for twists"""
        prefixes = ["Ancient", "Lost", "Hidden", "Forgotten", "Sacred", "Cursed"]
        types = ["City", "Temple", "Tower", "Vault", "Sanctum", "Realm"]
        
        return f"the {self.rng.choice(prefixes)} {self.rng.choice(types)}"
    
    def _generate_organization_name(self) -> str:
        """Generate an organization name"""
        adjectives = ["Shadow", "Silver", "Golden", "Iron", "Crimson", "Azure"]
        nouns = ["Circle", "Order", "Brotherhood", "Alliance", "Council", "Guild"]
        
        return f"the {self.rng.choice(adjectives)} {self.rng.choice(nouns)}"
    
    def _determine_optimal_timing(self, category: str, context: Optional[Dict[str, Any]]) -> str:
        """Determine optimal timing for the twist"""
        timing_preferences = {
            "identity_reveal": ["climax", "mid_story"],
            "betrayal": ["mid_story", "climax"],
            "false_information": ["early", "mid_story"],
            "hidden_connection": ["mid_story", "climax"],
            "power_corruption": ["mid_story", "resolution"],
            "time_manipulation": ["climax", "mid_story"],
            "parallel_reality": ["early", "mid_story"],
            "moral_dilemma": ["climax", "resolution"]
        }
        
        preferred_timings = timing_preferences.get(category, ["mid_story"])
        return self.rng.choice(preferred_timings)
    
    async def _generate_foreshadowing(self, category: str, template_data: Dict[str, Any]) -> List[str]:
        """Generate foreshadowing clues for the twist"""
        clues = []
        
        # Category-specific foreshadowing
        if "foreshadowing" in template_data:
            category_clues = template_data["foreshadowing"]
            clues.extend(self.rng.sample(category_clues, min(2, len(category_clues))))
        
        # General foreshadowing techniques
        technique_categories = list(self.foreshadowing_database.keys())
        chosen_categories = self.rng.sample(technique_categories, min(2, len(technique_categories)))
        
        for tech_category in chosen_categories:
            techniques = self.foreshadowing_database[tech_category]
            clues.append(self.rng.choice(techniques))
        
        return clues[:4]  # Limit to 4 clues
    
    async def _generate_consequences(self, category: str, impact_level: str,
                                   context: Optional[Dict[str, Any]]) -> List[str]:
        """Generate consequences of the twist"""
        base_consequences = {
            "identity_reveal": [
                "Relationships fundamentally change",
                "Previous assumptions proven wrong",
                "New alliances and enemies emerge"
            ],
            "betrayal": [
                "Trust becomes a precious commodity",
                "Party must question all their allies",
                "Plans must be completely revised"
            ],
            "false_information": [
                "Previous victories may be meaningless",
                "New quest objectives emerge",
                "Characters question their judgment"
            ],
            "hidden_connection": [
                "Seemingly random events make sense",
                "New patterns emerge in past events",
                "Larger conspiracy revealed"
            ],
            "power_corruption": [
                "Character relationships strain",
                "Moral boundaries tested",
                "Power must be controlled or abandoned"
            ],
            "time_manipulation": [
                "Causality becomes questionable",
                "Actions may have unintended effects",
                "Reality becomes fluid"
            ],
            "parallel_reality": [
                "Identity becomes questionable",
                "Home seems foreign",
                "Choices carry more weight"
            ],
            "moral_dilemma": [
                "Clear right and wrong disappear",
                "Characters must choose lesser evils",
                "Principles tested against pragmatism"
            ]
        }
        
        consequences = base_consequences.get(category, ["Situation becomes more complex"])
        
        # Scale consequences by impact level
        if impact_level == "major":
            consequences.append("Campaign direction fundamentally altered")
        elif impact_level == "campaign_changing":
            consequences.extend([
                "World state permanently changed",
                "Character arcs dramatically shifted",
                "Future adventures completely different"
            ])
        
        return consequences
    
    async def _generate_prerequisites(self, category: str, 
                                    context: Optional[Dict[str, Any]]) -> List[str]:
        """Generate prerequisites for the twist to work"""
        
        general_prerequisites = [
            "Players are invested in current understanding",
            "Sufficient setup has been established",
            "Timing allows for proper revelation"
        ]
        
        category_prerequisites = {
            "identity_reveal": [
                "Character has been established as trustworthy",
                "Secret identity has been hinted at subtly"
            ],
            "betrayal": [
                "Betrayer has earned players' trust",
                "Motivation for betrayal exists and makes sense"
            ],
            "false_information": [
                "Information source seemed reliable",
                "False information has influenced party actions"
            ],
            "hidden_connection": [
                "Enough separate elements exist to connect",
                "Connection reveals meaningful pattern"
            ],
            "power_corruption": [
                "Character has been using/exposed to power source",
                "Corruption signs have been building gradually"
            ],
            "time_manipulation": [
                "Time-related elements have been introduced",
                "Temporal inconsistencies have been noticed"
            ],
            "parallel_reality": [
                "Reality has seemed slightly 'off'",
                "Players have established expectations about world"
            ],
            "moral_dilemma": [
                "Stakes are high enough to matter",
                "Multiple valid perspectives exist"
            ]
        }
        
        prerequisites = general_prerequisites.copy()
        if category in category_prerequisites:
            prerequisites.extend(category_prerequisites[category])
        
        return prerequisites
    
    async def generate_twist_chain(self, adventure: Adventure, 
                                 num_twists: int = 3) -> List[Twist]:
        """Generate a chain of connected twists for an adventure"""
        twists = []
        
        # First twist - setup
        setup_categories = ["false_information", "hidden_connection"]
        first_twist = await self.generate_plot_twist(
            category=self.rng.choice(setup_categories),
            impact_level="minor"
        )
        twists.append(first_twist)
        
        # Middle twists - complications
        middle_categories = ["betrayal", "identity_reveal", "power_corruption"]
        for i in range(num_twists - 2):
            middle_twist = await self.generate_plot_twist(
                category=self.rng.choice(middle_categories),
                impact_level="moderate"
            )
            twists.append(middle_twist)
        
        # Final twist - revelation
        final_categories = ["moral_dilemma", "time_manipulation", "parallel_reality"]
        final_twist = await self.generate_plot_twist(
            category=self.rng.choice(final_categories),
            impact_level="major"
        )
        twists.append(final_twist)
        
        # Connect the twists
        await self._connect_twists(twists, adventure)
        
        return twists
    
    async def _connect_twists(self, twists: List[Twist], adventure: Adventure):
        """Create connections between twists in a chain"""
        for i in range(len(twists) - 1):
            current_twist = twists[i]
            next_twist = twists[i + 1]
            
            # Add connection in consequences
            connection = f"Sets up revelation: {next_twist.description}"
            if connection not in current_twist.consequences:
                current_twist.consequences.append(connection)
            
            # Add prerequisite to next twist
            prerequisite = f"Previous twist established: {current_twist.twist_type}"
            if prerequisite not in next_twist.prerequisites:
                next_twist.prerequisites.append(prerequisite)
    
    async def generate_character_twist(self, character: Character) -> Twist:
        """Generate a twist specific to a character's backstory"""
        context = {}
        
        if character.backstory:
            # Use character's relationships
            if character.backstory.relationships:
                rel = self.rng.choice(character.backstory.relationships)
                context["ally"] = rel.person_name
                context["character"] = rel.person_name
            
            # Use character's motivations
            if character.backstory.motivations:
                motivation = self.rng.choice(character.backstory.motivations)
                if motivation.motivation_type == "revenge":
                    category = "identity_reveal"
                elif motivation.motivation_type == "redemption":
                    category = "moral_dilemma"
                else:
                    category = None
            else:
                category = None
        else:
            category = None
        
        return await self.generate_plot_twist(category=category, context=context)
    
    async def generate_campaign_twists(self, theme: ThemeType, 
                                     complexity: ComplexityLevel) -> List[Twist]:
        """Generate thematic twists for a campaign"""
        theme_categories = {
            ThemeType.HORROR: ["power_corruption", "identity_reveal", "parallel_reality"],
            ThemeType.MYSTERY: ["false_information", "hidden_connection", "identity_reveal"],
            ThemeType.POLITICAL: ["betrayal", "hidden_connection", "moral_dilemma"],
            ThemeType.PLANAR: ["parallel_reality", "time_manipulation", "identity_reveal"],
            ThemeType.DARK_FANTASY: ["power_corruption", "moral_dilemma", "betrayal"]
        }
        
        # Get categories for theme
        categories = theme_categories.get(theme, list(self.twist_templates.keys()))
        
        # Determine number of twists based on complexity
        twist_counts = {
            ComplexityLevel.SIMPLE: 1,
            ComplexityLevel.MODERATE: 2,
            ComplexityLevel.COMPLEX: 3,
            ComplexityLevel.EPIC: 5
        }
        
        num_twists = twist_counts[complexity]
        twists = []
        
        # Generate twists
        used_categories = set()
        for i in range(num_twists):
            # Avoid repeating categories
            available_categories = [cat for cat in categories if cat not in used_categories]
            if not available_categories:
                available_categories = categories
            
            category = self.rng.choice(available_categories)
            used_categories.add(category)
            
            # Scale impact by position
            if i == 0:
                impact = "minor"
            elif i == num_twists - 1:
                impact = "major"
            else:
                impact = "moderate"
            
            twist = await self.generate_plot_twist(category=category, impact_level=impact)
            twists.append(twist)
        
        return twists
    
    async def generate_session_complications(self, num_complications: int = 2) -> List[str]:
        """Generate minor complications for a session"""
        complications = [
            "An unexpected ally arrives with their own agenda",
            "Weather turns dangerous at the worst moment",
            "A rival party competing for the same goal appears",
            "Local authorities become suspicious of party activities",
            "Equipment breaks down at a crucial moment",
            "An old enemy's agent infiltrates the group",
            "Information proves outdated or incomplete",
            "A moral dilemma forces the party to choose sides",
            "Time pressure increases due to unforeseen circumstances",
            "A helpful NPC has divided loyalties",
            "The party's reputation precedes them in unexpected ways",
            "A random encounter reveals larger patterns",
            "Resources become scarce or contaminated",
            "Communication breaks down at a critical moment",
            "An ally's past catches up with them"
        ]
        
        return self.rng.sample(complications, min(num_complications, len(complications)))
    
    async def generate_red_herrings(self, main_plot: str, num_herrings: int = 3) -> List[str]:
        """Generate red herrings to mislead players"""
        herring_templates = [
            "Evidence points to {suspect} as the culprit",
            "The {mcguffin} appears to be the real objective",
            "{location} seems to hold the key to everything",
            "The {event} appears more important than it actually is",
            "{character} acts suspiciously, drawing attention from real threat"
        ]
        
        suspects = ["mysterious stranger", "trusted ally", "authority figure", "obvious villain"]
        mcguffins = ["ancient tome", "magical crystal", "royal seal", "treasure map"]
        locations = ["abandoned tower", "secret chamber", "old cemetery", "hidden cave"]
        events = ["recent murder", "strange prophecy", "unusual weather", "political scandal"]
        characters = ["local merchant", "village elder", "court wizard", "tavern keeper"]
        
        herrings = []
        for _ in range(num_herrings):
            template = self.rng.choice(herring_templates)
            herring = template.format(
                suspect=self.rng.choice(suspects),
                mcguffin=self.rng.choice(mcguffins),
                location=self.rng.choice(locations),
                event=self.rng.choice(events),
                character=self.rng.choice(characters)
            )
            herrings.append(herring)
        
        return herrings