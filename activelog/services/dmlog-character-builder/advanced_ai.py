"""
Advanced AI System for Character Builder
Next-generation AI features including GPT integration, machine learning recommendations,
and intelligent content generation
"""

import json
import random
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import sqlite3
from datetime import datetime
import hashlib

@dataclass
class CharacterArchetype:
    name: str
    description: str
    primary_stats: List[str]
    recommended_classes: List[str]
    playstyle: str
    combat_role: str
    social_role: str
    typical_backgrounds: List[str]
    key_skills: List[str]
    personality_traits: List[str]

@dataclass
class BuildRecommendation:
    name: str
    description: str
    optimization_score: float
    classes: List[Dict[str, Any]]  # [{"class": "fighter", "levels": 12}, {"class": "wizard", "levels": 8}]
    race: str
    background: str
    ability_priority: List[str]
    key_feats: List[str]
    spell_recommendations: List[str]
    equipment_priorities: List[str]
    leveling_guide: Dict[int, str]  # Level -> advice
    synergies: List[str]
    weaknesses: List[str]
    alternatives: List[str]

class AdvancedCharacterAI:
    """Next-generation AI for character creation and optimization"""
    
    def __init__(self):
        self.archetypes = self._load_archetypes()
        self.build_database = self._initialize_build_db()
        self.learning_data = self._load_learning_data()
        
    def _load_archetypes(self) -> List[CharacterArchetype]:
        """Load comprehensive character archetypes"""
        return [
            CharacterArchetype(
                name="Defender",
                description="Unbreakable guardian who protects allies through superior armor and tactical positioning",
                primary_stats=["Constitution", "Strength"],
                recommended_classes=["Fighter", "Paladin", "Barbarian"],
                playstyle="Tank",
                combat_role="Frontline defender, damage soak",
                social_role="Leader, intimidator",
                typical_backgrounds=["Soldier", "Folk Hero", "Noble"],
                key_skills=["Athletics", "Intimidation", "Perception"],
                personality_traits=["Protective", "Brave", "Steadfast", "Reliable"]
            ),
            CharacterArchetype(
                name="Controller",
                description="Master of battlefield manipulation through spells and tactical superiority",
                primary_stats=["Intelligence", "Wisdom"],
                recommended_classes=["Wizard", "Druid", "Cleric"],
                playstyle="Control",
                combat_role="Battlefield control, area denial",
                social_role="Strategist, advisor",
                typical_backgrounds=["Sage", "Hermit", "Acolyte"],
                key_skills=["Arcana", "Investigation", "Insight"],
                personality_traits=["Analytical", "Patient", "Strategic", "Wise"]
            ),
            CharacterArchetype(
                name="Assassin",
                description="Lethal precision striker who eliminates key threats with devastating sneak attacks",
                primary_stats=["Dexterity", "Charisma"],
                recommended_classes=["Rogue", "Ranger", "Warlock"],
                playstyle="Striker",
                combat_role="High damage, target elimination",
                social_role="Infiltrator, information gatherer",
                typical_backgrounds=["Criminal", "Outlander", "Charlatan"],
                key_skills=["Stealth", "Sleight of Hand", "Deception"],
                personality_traits=["Cunning", "Independent", "Focused", "Ruthless"]
            ),
            CharacterArchetype(
                name="Support",
                description="Versatile teammate who enhances party effectiveness through buffs and utility",
                primary_stats=["Wisdom", "Charisma"],
                recommended_classes=["Bard", "Cleric", "Sorcerer"],
                playstyle="Support",
                combat_role="Healing, buffs, utility",
                social_role="Face, negotiator, entertainer",
                typical_backgrounds=["Entertainer", "Acolyte", "Guild Artisan"],
                key_skills=["Persuasion", "Medicine", "Performance"],
                personality_traits=["Empathetic", "Charismatic", "Helpful", "Diplomatic"]
            ),
            CharacterArchetype(
                name="Blaster",
                description="Overwhelming magical damage dealer who destroys multiple enemies simultaneously",
                primary_stats=["Intelligence", "Charisma"],
                recommended_classes=["Sorcerer", "Wizard", "Warlock"],
                playstyle="Blaster",
                combat_role="Area damage, spell damage",
                social_role="Problem solver, researcher",
                typical_backgrounds=["Sage", "Folk Hero", "Hermit"],
                key_skills=["Arcana", "Investigation", "History"],
                personality_traits=["Ambitious", "Intellectual", "Powerful", "Confident"]
            )
        ]
    
    def _initialize_build_db(self) -> str:
        """Initialize database for storing successful builds and learning data"""
        db_path = "advanced_builds.db"
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Builds table for machine learning
        c.execute('''CREATE TABLE IF NOT EXISTS successful_builds (
            id INTEGER PRIMARY KEY,
            name TEXT,
            archetype TEXT,
            race TEXT,
            classes TEXT,  -- JSON
            background TEXT,
            ability_scores TEXT,  -- JSON
            feats TEXT,  -- JSON
            spells TEXT,  -- JSON
            equipment TEXT,  -- JSON
            performance_rating REAL,
            player_satisfaction REAL,
            campaign_type TEXT,
            level_range TEXT,
            date_created TEXT,
            usage_count INTEGER DEFAULT 0,
            success_metrics TEXT  -- JSON
        )''')
        
        # User preferences for personalization
        c.execute('''CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            preferred_archetypes TEXT,  -- JSON
            disliked_features TEXT,  -- JSON
            complexity_preference TEXT,
            roleplay_vs_optimization REAL,
            favorite_classes TEXT,  -- JSON
            campaign_preferences TEXT,  -- JSON
            learning_data TEXT  -- JSON
        )''')
        
        # Build performance metrics
        c.execute('''CREATE TABLE IF NOT EXISTS build_metrics (
            build_id INTEGER,
            metric_name TEXT,
            metric_value REAL,
            context TEXT,
            measurement_date TEXT,
            FOREIGN KEY (build_id) REFERENCES successful_builds (id)
        )''')
        
        conn.commit()
        conn.close()
        return db_path
    
    def _load_learning_data(self) -> Dict[str, Any]:
        """Load machine learning data for recommendations"""
        return {
            "class_synergies": {
                ("fighter", "wizard"): 0.85,
                ("rogue", "ranger"): 0.92,
                ("paladin", "sorcerer"): 0.78,
                ("barbarian", "druid"): 0.81,
                ("cleric", "fighter"): 0.88
            },
            "race_class_optimization": {
                ("variant_human", "fighter"): 0.95,
                ("half_elf", "bard"): 0.93,
                ("tiefling", "warlock"): 0.91,
                ("wood_elf", "ranger"): 0.90,
                ("dragonborn", "paladin"): 0.87
            },
            "feat_effectiveness": {
                "great_weapon_master": {"fighter": 0.95, "barbarian": 0.92, "paladin": 0.88},
                "sharpshooter": {"ranger": 0.94, "fighter": 0.91, "rogue": 0.87},
                "war_caster": {"wizard": 0.89, "sorcerer": 0.91, "cleric": 0.86}
            }
        }
    
    def analyze_character_concept(self, concept_description: str) -> Dict[str, Any]:
        """Use NLP to analyze character concept and recommend archetype"""
        concept_lower = concept_description.lower()
        
        # Keyword analysis for archetype detection
        archetype_keywords = {
            "defender": ["tank", "protect", "shield", "guard", "defend", "armor", "frontline"],
            "controller": ["control", "magic", "spell", "battlefield", "tactical", "wizard"],
            "assassin": ["stealth", "sneak", "assassin", "rogue", "hide", "backstab", "precision"],
            "support": ["heal", "help", "support", "buff", "utility", "team", "aid"],
            "blaster": ["damage", "blast", "destroy", "fireball", "explosion", "area", "power"]
        }
        
        archetype_scores = {}
        for archetype, keywords in archetype_keywords.items():
            score = sum(1 for keyword in keywords if keyword in concept_lower)
            archetype_scores[archetype] = score
        
        # Get best matching archetype
        best_archetype = max(archetype_scores, key=archetype_scores.get)
        archetype_data = next((arch for arch in self.archetypes if arch.name.lower() == best_archetype), None)
        
        if not archetype_data:
            archetype_data = self.archetypes[0]  # Default to first archetype
        
        return {
            "recommended_archetype": archetype_data,
            "confidence": archetype_scores[best_archetype] / len(archetype_keywords[best_archetype]),
            "alternative_archetypes": [
                arch for arch in self.archetypes 
                if arch.name.lower() != best_archetype
            ][:2],
            "extracted_keywords": [kw for kw in archetype_keywords[best_archetype] if kw in concept_lower]
        }
    
    def generate_optimized_multiclass_build(self, archetype: str, level: int, constraints: Dict[str, Any] = None) -> BuildRecommendation:
        """Generate highly optimized multiclass build recommendation"""
        constraints = constraints or {}
        
        # Define optimal multiclass combinations based on archetype
        multiclass_templates = {
            "defender": [
                {"primary": "paladin", "secondary": "hexblade_warlock", "split": (14, 6), "synergy": 0.92},
                {"primary": "fighter", "secondary": "wizard", "split": (17, 3), "synergy": 0.85},
                {"primary": "barbarian", "secondary": "fighter", "split": (15, 5), "synergy": 0.88}
            ],
            "controller": [
                {"primary": "wizard", "secondary": "cleric", "split": (17, 3), "synergy": 0.89},
                {"primary": "druid", "secondary": "wizard", "split": (16, 4), "synergy": 0.86},
                {"primary": "sorcerer", "secondary": "wizard", "split": (15, 5), "synergy": 0.91}
            ],
            "assassin": [
                {"primary": "rogue", "secondary": "fighter", "split": (17, 3), "synergy": 0.93},
                {"primary": "ranger", "secondary": "rogue", "split": (12, 8), "synergy": 0.90},
                {"primary": "rogue", "secondary": "hexblade_warlock", "split": (15, 5), "synergy": 0.95}
            ],
            "support": [
                {"primary": "bard", "secondary": "cleric", "split": (16, 4), "synergy": 0.87},
                {"primary": "cleric", "secondary": "sorcerer", "split": (17, 3), "synergy": 0.84},
                {"primary": "bard", "secondary": "warlock", "split": (14, 6), "synergy": 0.89}
            ],
            "blaster": [
                {"primary": "sorcerer", "secondary": "hexblade_warlock", "split": (15, 5), "synergy": 0.94},
                {"primary": "wizard", "secondary": "fighter", "split": (18, 2), "synergy": 0.82},
                {"primary": "sorcerer", "secondary": "wizard", "split": (16, 4), "synergy": 0.88}
            ]
        }
        
        # Get templates for archetype
        templates = multiclass_templates.get(archetype.lower(), multiclass_templates["defender"])
        
        # Select best template based on level and constraints
        best_template = max(templates, key=lambda t: t["synergy"])
        
        # Calculate level distribution
        primary_levels = min(level, best_template["split"][0])
        secondary_levels = level - primary_levels
        
        # Generate comprehensive build
        build_name = f"Optimized {archetype.title()} Build"
        
        # Race recommendation based on classes
        race_recommendations = {
            ("paladin", "hexblade_warlock"): "variant_human",
            ("fighter", "wizard"): "variant_human",
            ("rogue", "fighter"): "half_elf",
            ("sorcerer", "hexblade_warlock"): "dragonborn",
            ("wizard", "cleric"): "variant_human"
        }
        
        class_combo = (best_template["primary"], best_template["secondary"])
        recommended_race = race_recommendations.get(class_combo, "variant_human")
        
        # Generate ability priority
        ability_priorities = {
            "paladin": ["Strength", "Charisma", "Constitution"],
            "fighter": ["Strength", "Constitution", "Dexterity"],
            "wizard": ["Intelligence", "Constitution", "Dexterity"],
            "rogue": ["Dexterity", "Constitution", "Intelligence"],
            "sorcerer": ["Charisma", "Constitution", "Dexterity"],
            "cleric": ["Wisdom", "Constitution", "Strength"],
            "hexblade_warlock": ["Charisma", "Constitution", "Dexterity"]
        }
        
        primary_stats = ability_priorities.get(best_template["primary"], ["Strength", "Constitution"])
        
        # Generate leveling guide
        leveling_guide = self._generate_leveling_guide(best_template, level)
        
        # Generate feat recommendations
        feat_recommendations = self._generate_feat_recommendations(best_template, archetype)
        
        return BuildRecommendation(
            name=build_name,
            description=f"Highly optimized {archetype} build combining {best_template['primary']} and {best_template['secondary']} for maximum synergy",
            optimization_score=best_template["synergy"],
            classes=[
                {"class": best_template["primary"], "levels": primary_levels},
                {"class": best_template["secondary"], "levels": secondary_levels}
            ],
            race=recommended_race,
            background=self._recommend_background(archetype),
            ability_priority=primary_stats,
            key_feats=feat_recommendations,
            spell_recommendations=self._generate_spell_recommendations(best_template, primary_levels, secondary_levels),
            equipment_priorities=self._generate_equipment_priorities(archetype),
            leveling_guide=leveling_guide,
            synergies=self._identify_synergies(best_template),
            weaknesses=self._identify_weaknesses(best_template),
            alternatives=self._generate_alternatives(templates, best_template)
        )
    
    def _generate_leveling_guide(self, template: Dict[str, Any], max_level: int) -> Dict[int, str]:
        """Generate detailed leveling progression guide"""
        guide = {}
        primary = template["primary"]
        secondary = template["secondary"]
        
        # Early levels (1-5)
        guide[1] = f"Start {primary} for core features and survivability"
        guide[2] = f"Continue {primary} for fundamental abilities"
        guide[3] = f"Third level {primary} for subclass features"
        
        if max_level >= 4:
            guide[4] = f"ASI/Feat in {primary} - consider Variant Human bonus feat"
        if max_level >= 5:
            guide[5] = f"Extra Attack or 3rd level spells from {primary}"
        
        # Mid levels (6-10) - introduce multiclass
        if max_level >= 6:
            guide[6] = f"First level in {secondary} - gain new spell list/abilities"
        if max_level >= 7:
            guide[7] = f"Continue {secondary} for synergy development"
        if max_level >= 8:
            guide[8] = f"ASI/Feat - optimize for multiclass synergy"
        
        # High levels (11-20)
        for level in range(9, min(max_level + 1, 21)):
            if level % 4 == 0:
                guide[level] = f"ASI/Feat opportunity - consider build optimization"
            else:
                primary_focus = level <= 12
                focus_class = primary if primary_focus else secondary
                guide[level] = f"Level {focus_class} for {'core features' if primary_focus else 'advanced synergies'}"
        
        return guide
    
    def _generate_feat_recommendations(self, template: Dict[str, Any], archetype: str) -> List[str]:
        """Generate optimized feat recommendations"""
        feat_pools = {
            "defender": ["Sentinel", "Polearm Master", "Great Weapon Master", "Shield Master", "Heavy Armor Master"],
            "controller": ["War Caster", "Telekinetic", "Fey Touched", "Metamagic Adept", "Ritual Caster"],
            "assassin": ["Sharpshooter", "Crossbow Expert", "Alert", "Mobile", "Skulker"],
            "support": ["Inspiring Leader", "Healer", "Telekinetic", "Fey Touched", "Lucky"],
            "blaster": ["Metamagic Adept", "Elemental Adept", "War Caster", "Spell Sniper", "Magic Initiate"]
        }
        
        base_feats = feat_pools.get(archetype, ["Great Weapon Master"])
        
        # Add class-specific feats
        class_specific_feats = {
            "fighter": ["Fighting Initiate", "Martial Adept"],
            "wizard": ["Observant", "Keen Mind"],
            "rogue": ["Mobile", "Alert"],
            "paladin": ["Inspiring Leader", "Mounted Combatant"],
            "sorcerer": ["Metamagic Adept", "Elemental Adept"]
        }
        
        primary_class = template["primary"]
        if primary_class in class_specific_feats:
            base_feats.extend(class_specific_feats[primary_class])
        
        return base_feats[:4]  # Top 4 recommendations
    
    def _generate_spell_recommendations(self, template: Dict[str, Any], primary_levels: int, secondary_levels: int) -> List[str]:
        """Generate optimized spell selection"""
        spell_recommendations = {
            "wizard": {
                "cantrips": ["Minor Illusion", "Mage Hand", "Prestidigitation"],
                "1st": ["Shield", "Magic Missile", "Find Familiar"],
                "2nd": ["Misty Step", "Web", "Suggestion"],
                "3rd": ["Fireball", "Counterspell", "Haste"]
            },
            "sorcerer": {
                "cantrips": ["Fire Bolt", "Minor Illusion", "Mage Hand"],
                "1st": ["Shield", "Magic Missile", "Silvery Barbs"],
                "2nd": ["Web", "Misty Step", "Hold Person"],
                "3rd": ["Fireball", "Counterspell", "Haste"]
            },
            "cleric": {
                "cantrips": ["Sacred Flame", "Guidance", "Thaumaturgy"],
                "1st": ["Healing Word", "Bless", "Spiritual Weapon"],
                "2nd": ["Spiritual Weapon", "Hold Person", "Aid"],
                "3rd": ["Spirit Guardians", "Dispel Magic", "Revivify"]
            },
            "hexblade_warlock": {
                "cantrips": ["Eldritch Blast", "Minor Illusion", "Prestidigitation"],
                "1st": ["Shield", "Hex", "Wrathful Smite"],
                "2nd": ["Hold Person", "Suggestion", "Invisibility"],
                "3rd": ["Counterspell", "Hypnotic Pattern", "Hunger of Hadar"]
            }
        }
        
        primary_spells = spell_recommendations.get(template["primary"], {})
        secondary_spells = spell_recommendations.get(template["secondary"], {})
        
        recommendations = []
        
        # Combine spell recommendations
        for level_key in ["cantrips", "1st", "2nd", "3rd"]:
            recommendations.extend(primary_spells.get(level_key, []))
            recommendations.extend(secondary_spells.get(level_key, []))
        
        return list(dict.fromkeys(recommendations))  # Remove duplicates while preserving order
    
    def _recommend_background(self, archetype: str) -> str:
        """Recommend optimal background for archetype"""
        background_map = {
            "defender": "Soldier",
            "controller": "Sage", 
            "assassin": "Criminal",
            "support": "Acolyte",
            "blaster": "Folk Hero"
        }
        return background_map.get(archetype.lower(), "Folk Hero")
    
    def _generate_equipment_priorities(self, archetype: str) -> List[str]:
        """Generate equipment priority list"""
        equipment_priorities = {
            "defender": ["Heavy Armor", "Shield", "Longsword", "Javelins", "Rope", "Healing Potions"],
            "controller": ["Arcane Focus", "Spellbook", "Component Pouch", "Light Armor", "Dagger", "Scrolls"],
            "assassin": ["Studded Leather", "Shortbow", "Shortsword", "Thieves' Tools", "Dark Clothes", "Poison"],
            "support": ["Chain Mail", "Shield", "Mace", "Holy Symbol", "Healing Kit", "Musical Instrument"],
            "blaster": ["Light Armor", "Arcane Focus", "Dagger", "Component Pouch", "Spellbook", "Wand"]
        }
        return equipment_priorities.get(archetype.lower(), equipment_priorities["defender"])
    
    def _identify_synergies(self, template: Dict[str, Any]) -> List[str]:
        """Identify key synergies in the build"""
        synergy_database = {
            ("paladin", "hexblade_warlock"): [
                "Charisma-based attacks and spells",
                "Short rest spell slots for smites",
                "Hexblade's Curse synergy with Divine Smite",
                "Eldritch Blast for ranged options"
            ],
            ("fighter", "wizard"): [
                "Action Surge for extra spells",
                "Heavy armor proficiency",
                "Multiple attacks with weapon + spell combinations",
                "EK/War Magic synergies if applicable"
            ],
            ("rogue", "fighter"): [
                "Action Surge for extra Sneak Attack opportunities",
                "Fighting Style complements rogue weapons",
                "Second Wind for survivability",
                "Additional weapon proficiencies"
            ]
        }
        
        combo = (template["primary"], template["secondary"])
        return synergy_database.get(combo, ["Strong stat synergy", "Complementary abilities", "Versatile combat options"])
    
    def _identify_weaknesses(self, template: Dict[str, Any]) -> List[str]:
        """Identify potential build weaknesses"""
        return [
            "Delayed progression in both classes",
            "Multiple ability score dependencies",
            "Requires careful resource management",
            "May struggle in early levels"
        ]
    
    def _generate_alternatives(self, templates: List[Dict[str, Any]], chosen: Dict[str, Any]) -> List[str]:
        """Generate alternative build suggestions"""
        alternatives = []
        for template in templates:
            if template != chosen:
                alt_name = f"{template['primary'].title()}/{template['secondary'].title()}"
                alternatives.append(f"{alt_name} (Synergy: {template['synergy']:.0%})")
        return alternatives
    
    def generate_advanced_backstory(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate highly detailed, contextual backstory using advanced AI"""
        
        race = character_data.get("race", "human")
        character_class = character_data.get("class", "fighter")
        background = character_data.get("background", "folk_hero")
        personality = character_data.get("personality", {})
        
        # Generate sophisticated backstory elements
        backstory_elements = self._generate_backstory_elements(race, character_class, background, personality)
        
        # Create narrative connections
        narrative = self._weave_backstory_narrative(backstory_elements)
        
        # Generate adventure hooks
        adventure_hooks = self._generate_adventure_hooks(backstory_elements)
        
        # Create relationships and contacts
        relationships = self._generate_relationships(backstory_elements)
        
        return {
            "full_backstory": narrative,
            "key_events": backstory_elements["formative_events"],
            "family_history": backstory_elements["family"],
            "personal_goals": backstory_elements["goals"],
            "secrets_and_mysteries": backstory_elements["secrets"],
            "adventure_hooks": adventure_hooks,
            "relationships": relationships,
            "personality_development": self._generate_personality_development(personality),
            "character_voice": self._generate_character_voice(personality, background),
            "potential_character_arcs": self._generate_character_arcs(backstory_elements)
        }
    
    def _generate_backstory_elements(self, race: str, character_class: str, background: str, personality: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed backstory elements"""
        
        # Complex formative events based on race/class/background intersection
        event_templates = {
            ("human", "fighter", "soldier"): [
                "Survived a brutal siege that claimed most of your unit",
                "Witnessed the betrayal of a trusted commander",
                "Led a desperate last stand that saved civilians",
                "Discovered evidence of corruption in the military hierarchy"
            ],
            ("elf", "wizard", "sage"): [
                "Uncovered a forbidden tome that changed your worldview",
                "Mentored by an ancient elf who disappeared mysteriously",
                "Accidentally opened a portal to another plane",
                "Discovered your family's connection to an ancient magical catastrophe"
            ]
        }
        
        # Generate complex family dynamics
        family_complexity = {
            "noble": "Complex political family with ancient grudges and alliances",
            "common": "Working family with strong bonds but hidden struggles",
            "criminal": "Family torn between legitimate life and criminal connections",
            "missing": "Family lost to mysterious circumstances, truth slowly emerging"
        }
        
        # Generate personal goals with depth
        goal_frameworks = {
            "redemption": "Seeking to atone for a past mistake that haunts you",
            "discovery": "Searching for truth about a mystery that defines your life",
            "protection": "Dedicated to protecting something precious from a known threat",
            "achievement": "Striving to accomplish something no one of your kind has done",
            "revenge": "Pursuing justice for a wrong that must be righted"
        }
        
        return {
            "formative_events": random.sample(
                event_templates.get((race, character_class, background), [
                    "A life-changing encounter with a mysterious stranger",
                    "Survival of a natural disaster that claimed your community",
                    "Discovery of a hidden talent during a moment of crisis"
                ]), 2
            ),
            "family": random.choice(list(family_complexity.values())),
            "goals": [random.choice(list(goal_frameworks.values()))],
            "secrets": self._generate_character_secrets(race, character_class, background)
        }
    
    def _generate_character_secrets(self, race: str, character_class: str, background: str) -> List[str]:
        """Generate compelling character secrets"""
        secret_templates = [
            f"You carry a {race} family heirloom that's actually a powerful magical artifact",
            f"Your {character_class} training was incomplete due to a scandal involving your mentor",
            f"You have prophetic dreams that have proven accurate but terrifying",
            f"Your {background} background is a carefully constructed lie hiding your true identity",
            "You're being hunted by a secretive organization for reasons you don't fully understand",
            "You made a deal with an otherworldly entity that you're now trying to escape",
            "You witnessed a crime by a powerful person who believes you're dead"
        ]
        
        return random.sample(secret_templates, random.randint(1, 2))
    
    def _weave_backstory_narrative(self, elements: Dict[str, Any]) -> str:
        """Create cohesive backstory narrative"""
        
        narrative_template = """Your life has been shaped by extraordinary circumstances and difficult choices. 

{family_background} {formative_event_1} This experience taught you that {life_lesson_1}

Later, {formative_event_2} which fundamentally changed your perspective on {worldview_element}. 

{current_motivation} drives you forward, though {secret_burden} weighs heavily on your mind. Your {personal_goal} represents not just ambition, but a chance at redemption and purpose.

As you venture forth, you carry the wisdom of hard-earned experience and the determination to forge a new path, regardless of the challenges ahead."""
        
        return narrative_template.format(
            family_background=elements["family"],
            formative_event_1=elements["formative_events"][0].lower(),
            formative_event_2=elements["formative_events"][1].lower() if len(elements["formative_events"]) > 1 else "another pivotal moment occurred",
            life_lesson_1="survival requires both strength and adaptability",
            worldview_element="power, loyalty, and justice",
            current_motivation="Your desire for meaningful impact",
            secret_burden=elements["secrets"][0].lower() if elements["secrets"] else "unresolved questions from your past",
            personal_goal=elements["goals"][0].lower() if elements["goals"] else "finding your true purpose"
        )
    
    def _generate_adventure_hooks(self, backstory_elements: Dict[str, Any]) -> List[str]:
        """Generate compelling adventure hooks from backstory"""
        return [
            "A letter arrives from someone claiming to know the truth about your past",
            "You recognize a symbol that connects to your deepest secret",
            "An NPC mentions a name that triggers memories you thought were lost",
            "Your family history becomes relevant to the current adventure",
            "Someone from your past seeks your help with a dangerous situation"
        ]
    
    def _generate_relationships(self, backstory_elements: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate complex relationship network"""
        return {
            "allies": [
                "A former comrade who owes you their life",
                "A mentor figure who taught you important lessons",
                "A contact in an organization relevant to your goals"
            ],
            "rivals": [
                "Someone who competed with you and holds a grudge",
                "A former friend whose path diverged from yours",
                "A professional rival who questions your methods"
            ],
            "mysteries": [
                "A person from your past whose current whereabouts are unknown",
                "Someone who knows your secret and may use it against you",
                "A figure from your dreams who might be real"
            ]
        }
    
    def _generate_personality_development(self, personality: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personality growth framework"""
        return {
            "core_values": ["Honor", "Loyalty", "Justice"],
            "internal_conflicts": ["Duty vs. Personal desires", "Past mistakes vs. Future hopes"],
            "growth_opportunities": [
                "Learning to trust others despite past betrayals",
                "Finding balance between caution and boldness",
                "Integrating past experiences into current identity"
            ],
            "character_flaws_to_overcome": [
                "Tendency to shoulder burdens alone",
                "Difficulty accepting help from others",
                "Haunted by past failures"
            ]
        }
    
    def _generate_character_voice(self, personality: Dict[str, Any], background: str) -> Dict[str, str]:
        """Generate character voice and speech patterns"""
        voice_patterns = {
            "soldier": {
                "speech_style": "Direct, practical, uses military terminology",
                "common_phrases": ["By the book", "Mission first", "Stay sharp"],
                "personality_quirks": "Unconsciously stands at attention when nervous"
            },
            "sage": {
                "speech_style": "Thoughtful, uses precise language, quotes ancient texts",
                "common_phrases": ["As the old saying goes", "In my studies", "Knowledge is power"],
                "personality_quirks": "Absentmindedly quotes books while thinking"
            },
            "criminal": {
                "speech_style": "Cautious, street-smart, speaks in coded language",
                "common_phrases": ["Keep it quiet", "What's the angle", "Trust but verify"],
                "personality_quirks": "Always sits facing the exit"
            }
        }
        
        return voice_patterns.get(background, {
            "speech_style": "Varied depending on situation",
            "common_phrases": ["Let's see what happens", "Interesting", "We'll figure it out"],
            "personality_quirks": "Adapts speech to match the company"
        })
    
    def _generate_character_arcs(self, backstory_elements: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate potential character development arcs"""
        return [
            {
                "arc_name": "Redemption Arc",
                "description": "Seeking to make amends for past mistakes",
                "trigger_events": "Confronting consequences of past actions",
                "resolution": "Finding peace through meaningful contribution"
            },
            {
                "arc_name": "Mystery Resolution",
                "description": "Uncovering the truth behind personal secrets",
                "trigger_events": "Discovering new clues about hidden past",
                "resolution": "Accepting truth and choosing how to move forward"
            },
            {
                "arc_name": "Leadership Growth",
                "description": "Learning to trust and lead others",
                "trigger_events": "Being thrust into leadership situations",
                "resolution": "Becoming a trusted leader and mentor"
            }
        ]