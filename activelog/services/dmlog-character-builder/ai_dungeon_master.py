"""
AI Dungeon Master Integration
Advanced AI-powered dungeon master with dynamic storytelling, rule enforcement, and character interaction
"""

import asyncio
import logging
import json
import time
import uuid
import random
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from transformers import GPT2LMHeadModel, GPT2Tokenizer, pipeline
import torch
import websockets
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

class CampaignTheme(Enum):
    HEROIC_FANTASY = "heroic_fantasy"
    DARK_HORROR = "dark_horror"
    POLITICAL_INTRIGUE = "political_intrigue"
    MYSTERY_INVESTIGATION = "mystery_investigation"
    EXPLORATION_ADVENTURE = "exploration_adventure"
    URBAN_FANTASY = "urban_fantasy"
    COSMIC_HORROR = "cosmic_horror"
    COMEDIC_ADVENTURE = "comedic_adventure"

class EncounterType(Enum):
    COMBAT = "combat"
    SOCIAL = "social" 
    EXPLORATION = "exploration"
    PUZZLE = "puzzle"
    ROLEPLAY = "roleplay"
    MORAL_DILEMMA = "moral_dilemma"
    INVESTIGATION = "investigation"

@dataclass
class CharacterProfile:
    character_id: str
    name: str
    level: int
    class_name: str
    race: str
    background: str
    personality_traits: List[str]
    ideals: List[str]
    bonds: List[str]
    flaws: List[str]
    abilities: Dict[str, int]
    skills: Dict[str, int]
    backstory: str = ""
    current_hp: int = 0
    max_hp: int = 0

@dataclass
class CampaignState:
    campaign_id: str
    name: str
    theme: CampaignTheme
    current_session: int = 1
    active_characters: List[CharacterProfile] = field(default_factory=list)
    story_context: Dict[str, Any] = field(default_factory=dict)
    world_state: Dict[str, Any] = field(default_factory=dict)
    narrative_memory: List[str] = field(default_factory=list)
    relationship_dynamics: Dict[str, float] = field(default_factory=dict)
    ongoing_plots: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AIResponse:
    response_type: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class NarrativeEngine:
    """Advanced narrative generation engine for dynamic storytelling"""
    
    def __init__(self):
        self.model_name = "gpt2-medium"  # Would use GPT-4 or Claude in production
        self.tokenizer = GPT2Tokenizer.from_pretrained(self.model_name)
        self.model = GPT2LMHeadModel.from_pretrained(self.model_name)
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Narrative templates for different encounter types
        self.encounter_templates = self._load_encounter_templates()
        self.character_archetypes = self._load_character_archetypes()
        self.plot_hooks = self._load_plot_hooks()
        
        # Story coherence tracking
        self.story_embeddings = {}
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        
    def _load_encounter_templates(self) -> Dict[EncounterType, List[str]]:
        """Load narrative templates for different encounter types"""
        return {
            EncounterType.COMBAT: [
                "As you {approach/enter} the {location}, {threat} emerges from {hiding_place}, {eyes/weapons} glinting with {emotion}...",
                "The {atmosphere} is broken by {sound}, and suddenly {enemies} {action}, clearly intent on {motivation}...",
                "Without warning, {antagonist} steps forward, {characteristic_action}, declaring '{threatening_dialogue}'..."
            ],
            EncounterType.SOCIAL: [
                "The {npc_type} {approaches/greets} you with {demeanor}, their {eyes/expression} suggesting {hidden_agenda}...",
                "As you enter {social_setting}, all eyes turn to you. {influential_npc} {reaction}, while {atmosphere_description}...",
                "'{compelling_dialogue}' says {mysterious_figure}, {body_language} indicating {true_intentions}..."
            ],
            EncounterType.EXPLORATION: [
                "Before you lies {mysterious_location}, {atmospheric_details}. You notice {intriguing_details}...",
                "The {terrain/environment} stretches endlessly ahead, but something about {unusual_feature} catches your attention...",
                "As you {method_of_exploration}, you discover {surprising_discovery}, which {implications}..."
            ],
            EncounterType.MYSTERY_INVESTIGATION: [
                "The {crime_scene/mystery_location} reveals {cryptic_clues}, but {contradictory_evidence} suggests {alternative_theory}...",
                "'{mysterious_dialogue}' whispers {informant}, glancing nervously at {suspicious_element}...",
                "The evidence points to {obvious_conclusion}, but {character_name}'s {skill_check} reveals {hidden_truth}..."
            ]
        }
    
    def _load_character_archetypes(self) -> Dict[str, Dict[str, Any]]:
        """Load character archetypes for NPC generation"""
        return {
            "mentor": {
                "personality": ["wise", "patient", "mysterious", "experienced"],
                "motivations": ["guide heroes", "preserve knowledge", "atone for past"],
                "speech_patterns": ["speaks in metaphors", "asks probing questions", "references past events"]
            },
            "antagonist": {
                "personality": ["ambitious", "cunning", "ruthless", "charismatic"],
                "motivations": ["gain power", "revenge", "reshape world", "prove superiority"],
                "speech_patterns": ["grandiose declarations", "veiled threats", "philosophical justifications"]
            },
            "ally": {
                "personality": ["loyal", "supportive", "brave", "complementary_to_party"],
                "motivations": ["help friends", "right wrongs", "adventure", "personal_growth"],
                "speech_patterns": ["encouraging", "practical advice", "shared concerns"]
            },
            "neutral": {
                "personality": ["pragmatic", "self_interested", "cautious", "transactional"],
                "motivations": ["profit", "safety", "status_quo", "local_concerns"],
                "speech_patterns": ["business_focused", "conditional offers", "local_gossip"]
            }
        }
    
    def _load_plot_hooks(self) -> List[Dict[str, Any]]:
        """Load plot hooks for dynamic story generation"""
        return [
            {
                "hook": "An ancient prophecy begins to unfold",
                "complexity": "high",
                "themes": ["destiny", "ancient_evil", "chosen_one"],
                "duration": "campaign_arc"
            },
            {
                "hook": "A trusted ally harbors a dark secret",
                "complexity": "medium",
                "themes": ["betrayal", "redemption", "moral_ambiguity"],
                "duration": "story_arc"
            },
            {
                "hook": "Strange phenomena disrupt the natural order",
                "complexity": "high",
                "themes": ["cosmic_horror", "investigation", "sacrifice"],
                "duration": "campaign_arc"
            },
            {
                "hook": "Political tensions threaten to erupt into war",
                "complexity": "high",
                "themes": ["politics", "diplomacy", "consequences"],
                "duration": "campaign_arc"
            }
        ]
    
    def generate_narrative(self, context: str, encounter_type: EncounterType, 
                          characters: List[CharacterProfile], campaign_state: CampaignState) -> str:
        """Generate contextual narrative based on current situation"""
        
        # Analyze current story state
        story_sentiment = self._analyze_story_sentiment(campaign_state.narrative_memory)
        character_dynamics = self._analyze_character_dynamics(characters, campaign_state)
        
        # Select appropriate template
        templates = self.encounter_templates.get(encounter_type, [])
        if not templates:
            templates = ["You find yourself in an interesting situation..."]
        
        base_template = random.choice(templates)
        
        # Generate contextual narrative
        narrative_prompt = self._build_narrative_prompt(
            base_template, context, characters, campaign_state, story_sentiment
        )
        
        # Generate text using language model
        generated_text = self._generate_text(narrative_prompt, max_length=200)
        
        # Post-process for consistency and quality
        processed_narrative = self._post_process_narrative(
            generated_text, characters, campaign_state
        )
        
        # Store in narrative memory for coherence tracking
        campaign_state.narrative_memory.append(processed_narrative)
        if len(campaign_state.narrative_memory) > 100:  # Keep memory manageable
            campaign_state.narrative_memory.pop(0)
        
        return processed_narrative
    
    def _analyze_story_sentiment(self, narrative_memory: List[str]) -> Dict[str, float]:
        """Analyze the emotional trajectory of the story"""
        if not narrative_memory:
            return {"compound": 0.0, "positive": 0.0, "negative": 0.0, "neutral": 1.0}
        
        recent_narrative = " ".join(narrative_memory[-5:])  # Last 5 entries
        sentiment_scores = self.sentiment_analyzer.polarity_scores(recent_narrative)
        
        return sentiment_scores
    
    def _analyze_character_dynamics(self, characters: List[CharacterProfile], 
                                  campaign_state: CampaignState) -> Dict[str, Any]:
        """Analyze character relationships and party dynamics"""
        dynamics = {
            "party_cohesion": 0.8,  # Default high cohesion
            "leadership_balance": 0.7,
            "conflict_potential": 0.2,
            "character_spotlights": {}
        }
        
        # Analyze character backgrounds for potential conflicts/synergies
        for char in characters:
            dynamics["character_spotlights"][char.character_id] = {
                "recent_focus": campaign_state.relationship_dynamics.get(char.character_id, 0.5),
                "spotlight_priority": self._calculate_spotlight_priority(char, campaign_state)
            }
        
        return dynamics
    
    def _calculate_spotlight_priority(self, character: CharacterProfile, 
                                    campaign_state: CampaignState) -> float:
        """Calculate how much spotlight a character should receive"""
        base_priority = 0.5
        
        # Characters with rich backstories get more spotlight opportunities
        if len(character.backstory) > 100:
            base_priority += 0.2
        
        # Characters who haven't had recent focus get priority
        recent_focus = campaign_state.relationship_dynamics.get(character.character_id, 0.5)
        if recent_focus < 0.3:
            base_priority += 0.3
        
        # Class-specific spotlight opportunities
        if character.class_name.lower() in ["rogue", "ranger", "investigator"]:
            base_priority += 0.1  # Good for investigation encounters
        elif character.class_name.lower() in ["paladin", "cleric", "warlock"]:
            base_priority += 0.1  # Good for moral/religious encounters
        elif character.class_name.lower() in ["bard", "sorcerer", "warlock"]:
            base_priority += 0.1  # Good for social encounters
        
        return min(base_priority, 1.0)
    
    def _build_narrative_prompt(self, template: str, context: str, 
                               characters: List[CharacterProfile], 
                               campaign_state: CampaignState, 
                               sentiment: Dict[str, float]) -> str:
        """Build a comprehensive prompt for narrative generation"""
        
        # Character context
        char_context = []
        for char in characters:
            char_desc = f"{char.name} the {char.race} {char.class_name}"
            if char.personality_traits:
                char_desc += f" (known for being {', '.join(char.personality_traits[:2])})"
            char_context.append(char_desc)
        
        party_description = ", ".join(char_context)
        
        # Campaign context
        theme_context = f"This {campaign_state.theme.value} campaign"
        
        # Recent story context
        recent_events = " ".join(campaign_state.narrative_memory[-3:]) if campaign_state.narrative_memory else "This is the beginning of your adventure"
        
        # Sentiment-based tone adjustment
        tone = "balanced"
        if sentiment["compound"] > 0.5:
            tone = "hopeful"
        elif sentiment["compound"] < -0.5:
            tone = "tense"
        
        prompt = f"""
        {theme_context} features {party_description}. 
        Recent events: {recent_events}
        Current situation: {context}
        Tone: {tone}
        
        Continue the narrative with engaging description and potential plot development:
        {template}
        """
        
        return prompt
    
    def _generate_text(self, prompt: str, max_length: int = 150) -> str:
        """Generate text using the language model"""
        try:
            # Encode prompt
            inputs = self.tokenizer.encode(prompt, return_tensors="pt", max_length=512, truncation=True)
            
            # Generate text
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=inputs.shape[1] + max_length,
                    temperature=0.8,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    no_repeat_ngram_size=3
                )
            
            # Decode generated text
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the generated portion
            generated_portion = generated_text[len(self.tokenizer.decode(inputs[0], skip_special_tokens=True)):]
            
            return generated_portion.strip()
            
        except Exception as e:
            logger.error(f"Text generation error: {e}")
            return "The adventure continues in unexpected ways..."
    
    def _post_process_narrative(self, text: str, characters: List[CharacterProfile], 
                               campaign_state: CampaignState) -> str:
        """Post-process generated narrative for quality and consistency"""
        
        # Clean up text
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()
        
        # Ensure proper sentence structure
        sentences = text.split('.')
        processed_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Filter out fragments
                if not sentence[0].isupper():
                    sentence = sentence.capitalize()
                processed_sentences.append(sentence)
        
        processed_text = '. '.join(processed_sentences)
        
        # Add period if needed
        if processed_text and not processed_text.endswith(('.', '!', '?')):
            processed_text += '.'
        
        return processed_text

class RuleEngine:
    """Advanced rule enforcement and mechanics integration"""
    
    def __init__(self):
        self.rules_database = self._load_rules_database()
        self.combat_engine = CombatEngine()
        self.skill_engine = SkillEngine()
        
    def _load_rules_database(self) -> Dict[str, Any]:
        """Load comprehensive D&D 5e rules database"""
        return {
            "abilities": ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"],
            "skills": {
                "athletics": "strength",
                "acrobatics": "dexterity",
                "sleight_of_hand": "dexterity",
                "stealth": "dexterity",
                "arcana": "intelligence",
                "history": "intelligence",
                "investigation": "intelligence",
                "nature": "intelligence",
                "religion": "intelligence",
                "animal_handling": "wisdom",
                "insight": "wisdom",
                "medicine": "wisdom",
                "perception": "wisdom",
                "survival": "wisdom",
                "deception": "charisma",
                "intimidation": "charisma",
                "performance": "charisma",
                "persuasion": "charisma"
            },
            "spell_schools": ["abjuration", "conjuration", "divination", "enchantment", 
                            "evocation", "illusion", "necromancy", "transmutation"],
            "conditions": ["blinded", "charmed", "deafened", "frightened", "grappled",
                          "incapacitated", "invisible", "paralyzed", "petrified", "poisoned",
                          "prone", "restrained", "stunned", "unconscious"],
            "damage_types": ["acid", "bludgeoning", "cold", "fire", "force", "lightning",
                           "necrotic", "piercing", "poison", "psychic", "radiant", 
                           "slashing", "thunder"]
        }
    
    def validate_action(self, character: CharacterProfile, action: Dict[str, Any]) -> Dict[str, Any]:
        """Validate if a character action is legal according to D&D rules"""
        action_type = action.get("type")
        
        if action_type == "skill_check":
            return self._validate_skill_check(character, action)
        elif action_type == "spell_cast":
            return self._validate_spell_cast(character, action)
        elif action_type == "attack":
            return self._validate_attack(character, action)
        elif action_type == "ability_check":
            return self._validate_ability_check(character, action)
        else:
            return {"valid": True, "message": "Action allowed"}
    
    def _validate_skill_check(self, character: CharacterProfile, action: Dict[str, Any]) -> Dict[str, Any]:
        """Validate skill check attempt"""
        skill = action.get("skill", "").lower()
        
        if skill not in self.rules_database["skills"]:
            return {"valid": False, "message": f"Invalid skill: {skill}"}
        
        # Check if character is proficient
        character_skills = character.skills
        proficiency_bonus = max(2, (character.level - 1) // 4 + 2)
        
        ability_name = self.rules_database["skills"][skill]
        ability_modifier = (character.abilities.get(ability_name, 10) - 10) // 2
        
        skill_modifier = ability_modifier
        if character_skills.get(skill, 0) > 0:  # If proficient
            skill_modifier += proficiency_bonus
        
        return {
            "valid": True,
            "skill_modifier": skill_modifier,
            "ability_used": ability_name,
            "proficiency_bonus": proficiency_bonus if character_skills.get(skill, 0) > 0 else 0
        }
    
    def _validate_spell_cast(self, character: CharacterProfile, action: Dict[str, Any]) -> Dict[str, Any]:
        """Validate spell casting attempt"""
        spell_name = action.get("spell", "")
        spell_level = action.get("level", 1)
        
        # Check if character can cast spells
        spellcasting_classes = ["wizard", "sorcerer", "cleric", "druid", "bard", "warlock", 
                               "paladin", "ranger", "artificer", "eldritch knight", "arcane trickster"]
        
        if character.class_name.lower() not in spellcasting_classes:
            return {"valid": False, "message": f"{character.class_name} cannot cast spells"}
        
        # Validate spell slot availability (simplified)
        max_spell_level = min(9, (character.level + 1) // 2)
        if spell_level > max_spell_level:
            return {"valid": False, "message": f"Cannot cast level {spell_level} spells at level {character.level}"}
        
        return {
            "valid": True,
            "spell_level": spell_level,
            "casting_ability": self._get_casting_ability(character.class_name),
            "spell_attack_bonus": self._calculate_spell_attack_bonus(character),
            "spell_save_dc": self._calculate_spell_save_dc(character)
        }
    
    def _validate_attack(self, character: CharacterProfile, action: Dict[str, Any]) -> Dict[str, Any]:
        """Validate attack action"""
        weapon_type = action.get("weapon_type", "melee")
        
        proficiency_bonus = max(2, (character.level - 1) // 4 + 2)
        
        if weapon_type == "melee":
            ability_modifier = (character.abilities.get("strength", 10) - 10) // 2
        else:  # ranged
            ability_modifier = (character.abilities.get("dexterity", 10) - 10) // 2
        
        attack_bonus = ability_modifier + proficiency_bonus
        
        return {
            "valid": True,
            "attack_bonus": attack_bonus,
            "ability_used": "strength" if weapon_type == "melee" else "dexterity",
            "damage_modifier": ability_modifier
        }
    
    def _validate_ability_check(self, character: CharacterProfile, action: Dict[str, Any]) -> Dict[str, Any]:
        """Validate ability check"""
        ability = action.get("ability", "").lower()
        
        if ability not in self.rules_database["abilities"]:
            return {"valid": False, "message": f"Invalid ability: {ability}"}
        
        ability_modifier = (character.abilities.get(ability, 10) - 10) // 2
        
        return {
            "valid": True,
            "ability_modifier": ability_modifier,
            "ability_score": character.abilities.get(ability, 10)
        }
    
    def _get_casting_ability(self, class_name: str) -> str:
        """Get primary casting ability for class"""
        casting_abilities = {
            "wizard": "intelligence",
            "sorcerer": "charisma",
            "warlock": "charisma",
            "bard": "charisma",
            "cleric": "wisdom",
            "druid": "wisdom",
            "paladin": "charisma",
            "ranger": "wisdom",
            "artificer": "intelligence"
        }
        return casting_abilities.get(class_name.lower(), "intelligence")
    
    def _calculate_spell_attack_bonus(self, character: CharacterProfile) -> int:
        """Calculate spell attack bonus"""
        casting_ability = self._get_casting_ability(character.class_name)
        ability_modifier = (character.abilities.get(casting_ability, 10) - 10) // 2
        proficiency_bonus = max(2, (character.level - 1) // 4 + 2)
        return ability_modifier + proficiency_bonus
    
    def _calculate_spell_save_dc(self, character: CharacterProfile) -> int:
        """Calculate spell save DC"""
        return 8 + self._calculate_spell_attack_bonus(character)

class CombatEngine:
    """Advanced combat management and automation"""
    
    def __init__(self):
        self.initiative_order = []
        self.current_turn = 0
        self.round_number = 1
        
    def roll_initiative(self, participants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Roll initiative for all combat participants"""
        initiative_results = []
        
        for participant in participants:
            dex_modifier = (participant.get("dexterity", 10) - 10) // 2
            initiative_roll = random.randint(1, 20) + dex_modifier
            
            initiative_results.append({
                "name": participant.get("name", "Unknown"),
                "initiative": initiative_roll,
                "dex_modifier": dex_modifier,
                "participant_data": participant
            })
        
        # Sort by initiative (highest first)
        initiative_results.sort(key=lambda x: x["initiative"], reverse=True)
        self.initiative_order = initiative_results
        
        return initiative_results
    
    def process_combat_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Process a combat action and return results"""
        action_type = action.get("type")
        
        if action_type == "attack":
            return self._process_attack(action)
        elif action_type == "spell":
            return self._process_spell(action)
        elif action_type == "dash":
            return {"success": True, "message": "Movement speed doubled this turn"}
        elif action_type == "dodge":
            return {"success": True, "message": "Attacks against you have disadvantage until next turn"}
        elif action_type == "help":
            return {"success": True, "message": "Ally gains advantage on next action"}
        else:
            return {"success": False, "message": f"Unknown action type: {action_type}"}
    
    def _process_attack(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Process attack action"""
        attack_roll = random.randint(1, 20)
        attack_bonus = action.get("attack_bonus", 0)
        target_ac = action.get("target_ac", 15)
        
        total_attack = attack_roll + attack_bonus
        
        if attack_roll == 20:  # Critical hit
            damage_dice = action.get("damage_dice", "1d8")
            damage_modifier = action.get("damage_modifier", 0)
            
            # Double damage dice for crit
            base_damage = self._roll_damage(damage_dice) * 2 + damage_modifier
            
            return {
                "success": True,
                "critical_hit": True,
                "attack_roll": attack_roll,
                "total_attack": total_attack,
                "damage": base_damage,
                "message": f"Critical hit! Rolled {attack_roll} + {attack_bonus} = {total_attack} vs AC {target_ac}, dealing {base_damage} damage"
            }
        
        elif total_attack >= target_ac:  # Hit
            damage_dice = action.get("damage_dice", "1d8")
            damage_modifier = action.get("damage_modifier", 0)
            damage = self._roll_damage(damage_dice) + damage_modifier
            
            return {
                "success": True,
                "critical_hit": False,
                "attack_roll": attack_roll,
                "total_attack": total_attack,
                "damage": damage,
                "message": f"Hit! Rolled {attack_roll} + {attack_bonus} = {total_attack} vs AC {target_ac}, dealing {damage} damage"
            }
        
        else:  # Miss
            return {
                "success": False,
                "attack_roll": attack_roll,
                "total_attack": total_attack,
                "message": f"Miss! Rolled {attack_roll} + {attack_bonus} = {total_attack} vs AC {target_ac}"
            }
    
    def _roll_damage(self, damage_dice: str) -> int:
        """Roll damage dice (e.g., '2d6', '1d8+3')"""
        # Simple damage dice parser
        if 'd' not in damage_dice:
            return int(damage_dice)
        
        parts = damage_dice.split('d')
        num_dice = int(parts[0])
        die_parts = parts[1].split('+')
        die_size = int(die_parts[0])
        bonus = int(die_parts[1]) if len(die_parts) > 1 else 0
        
        total = sum(random.randint(1, die_size) for _ in range(num_dice)) + bonus
        return max(1, total)  # Minimum 1 damage

class SkillEngine:
    """Advanced skill check processing with contextual modifiers"""
    
    def process_skill_check(self, character: CharacterProfile, skill: str, 
                          difficulty: int = 15, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process skill check with contextual modifiers"""
        
        # Base roll
        roll = random.randint(1, 20)
        
        # Get skill modifier
        skill_data = self._get_skill_modifier(character, skill)
        base_modifier = skill_data["modifier"]
        
        # Apply contextual modifiers
        contextual_modifier = self._calculate_contextual_modifiers(skill, context or {})
        
        # Calculate total
        total = roll + base_modifier + contextual_modifier
        success = total >= difficulty
        
        # Determine degree of success/failure
        degree = "success" if success else "failure"
        margin = abs(total - difficulty)
        
        if success:
            if margin >= 10:
                degree = "critical_success"
            elif margin >= 5:
                degree = "great_success"
        else:
            if margin >= 10:
                degree = "critical_failure"
            elif margin >= 5:
                degree = "significant_failure"
        
        return {
            "roll": roll,
            "modifier": base_modifier,
            "contextual_modifier": contextual_modifier,
            "total": total,
            "difficulty": difficulty,
            "success": success,
            "degree": degree,
            "margin": margin,
            "skill_used": skill,
            "ability_used": skill_data["ability"]
        }
    
    def _get_skill_modifier(self, character: CharacterProfile, skill: str) -> Dict[str, Any]:
        """Get character's modifier for a skill"""
        rules_engine = RuleEngine()
        ability = rules_engine.rules_database["skills"].get(skill.lower(), "intelligence")
        
        ability_modifier = (character.abilities.get(ability, 10) - 10) // 2
        proficiency_bonus = max(2, (character.level - 1) // 4 + 2)
        
        is_proficient = character.skills.get(skill.lower(), 0) > 0
        skill_modifier = ability_modifier + (proficiency_bonus if is_proficient else 0)
        
        return {
            "modifier": skill_modifier,
            "ability": ability,
            "ability_modifier": ability_modifier,
            "proficiency_bonus": proficiency_bonus if is_proficient else 0,
            "proficient": is_proficient
        }
    
    def _calculate_contextual_modifiers(self, skill: str, context: Dict[str, Any]) -> int:
        """Calculate contextual modifiers based on situation"""
        modifier = 0
        
        # Environmental modifiers
        if context.get("advantage"):
            # Advantage represented as +2 modifier for simplicity
            modifier += 2
        elif context.get("disadvantage"):
            modifier -= 2
        
        # Skill-specific contextual modifiers
        if skill.lower() == "stealth":
            if context.get("darkness"):
                modifier += 2
            if context.get("light_armor"):
                modifier += 1
            if context.get("heavy_armor"):
                modifier -= 2
        
        elif skill.lower() == "perception":
            if context.get("familiar_area"):
                modifier += 2
            if context.get("darkness"):
                modifier -= 2
            if context.get("enhanced_senses"):
                modifier += 3
        
        elif skill.lower() == "persuasion":
            if context.get("shared_interests"):
                modifier += 2
            if context.get("hostile_disposition"):
                modifier -= 3
            if context.get("evidence"):
                modifier += 1
        
        return modifier

class AIDungeonMaster:
    """Complete AI Dungeon Master system"""
    
    def __init__(self, port: int = 8411):
        self.port = port
        self.narrative_engine = NarrativeEngine()
        self.rule_engine = RuleEngine()
        self.active_campaigns = {}
        self.connected_players = {}
        
        # AI personality and style configuration
        self.dm_personality = {
            "style": "engaging",
            "difficulty": "balanced",
            "narrative_focus": "character_driven",
            "rule_enforcement": "flexible",
            "humor_level": "moderate"
        }
    
    async def start_server(self):
        """Start the AI DM WebSocket server"""
        logger.info(f"Starting AI Dungeon Master on port {self.port}")
        
        async def handle_player(websocket, path):
            await self._handle_player_connection(websocket, path)
        
        server = await websockets.serve(handle_player, "localhost", self.port)
        logger.info(f"AI Dungeon Master running on ws://localhost:{self.port}")
        await server.wait_closed()
    
    async def _handle_player_connection(self, websocket, path):
        """Handle player connections"""
        player_id = f"player_{len(self.connected_players)}"
        self.connected_players[player_id] = websocket
        
        try:
            await websocket.send(json.dumps({
                "type": "dm_greeting",
                "message": "Welcome, adventurer! I am your AI Dungeon Master. What grand adventure shall we craft together?",
                "capabilities": {
                    "dynamic_storytelling": True,
                    "rule_enforcement": True,
                    "character_integration": True,
                    "real_time_adaptation": True
                }
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_player_message(player_id, data, websocket)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid message format"
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Player disconnected: {player_id}")
        finally:
            if player_id in self.connected_players:
                del self.connected_players[player_id]
    
    async def _process_player_message(self, player_id: str, data: Dict[str, Any], websocket):
        """Process messages from players"""
        message_type = data.get("type")
        
        if message_type == "start_campaign":
            await self._handle_start_campaign(player_id, data, websocket)
        elif message_type == "player_action":
            await self._handle_player_action(player_id, data, websocket)
        elif message_type == "get_campaign_state":
            await self._handle_get_campaign_state(player_id, data, websocket)
        elif message_type == "narrative_request":
            await self._handle_narrative_request(player_id, data, websocket)
        elif message_type == "rule_question":
            await self._handle_rule_question(player_id, data, websocket)
    
    async def _handle_start_campaign(self, player_id: str, data: Dict[str, Any], websocket):
        """Start a new campaign"""
        campaign_name = data.get("campaign_name", f"Adventure_{int(time.time())}")
        theme = CampaignTheme(data.get("theme", "heroic_fantasy"))
        characters = [CharacterProfile(**char) for char in data.get("characters", [])]
        
        campaign_id = str(uuid.uuid4())
        campaign_state = CampaignState(
            campaign_id=campaign_id,
            name=campaign_name,
            theme=theme,
            active_characters=characters
        )
        
        self.active_campaigns[campaign_id] = campaign_state
        
        # Generate opening narrative
        opening_narrative = self.narrative_engine.generate_narrative(
            context="The adventure begins",
            encounter_type=EncounterType.EXPLORATION,
            characters=characters,
            campaign_state=campaign_state
        )
        
        await websocket.send(json.dumps({
            "type": "campaign_started",
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "theme": theme.value,
            "opening_narrative": opening_narrative,
            "active_characters": [char.name for char in characters]
        }))
    
    async def _handle_player_action(self, player_id: str, data: Dict[str, Any], websocket):
        """Handle player actions and generate appropriate responses"""
        campaign_id = data.get("campaign_id")
        character_name = data.get("character_name")
        action = data.get("action", {})
        context = data.get("context", "")
        
        if campaign_id not in self.active_campaigns:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Campaign not found"
            }))
            return
        
        campaign_state = self.active_campaigns[campaign_id]
        character = None
        
        # Find character
        for char in campaign_state.active_characters:
            if char.name == character_name:
                character = char
                break
        
        if not character:
            await websocket.send(json.dumps({
                "type": "error", 
                "message": "Character not found"
            }))
            return
        
        # Validate action
        validation_result = self.rule_engine.validate_action(character, action)
        
        if not validation_result.get("valid", True):
            await websocket.send(json.dumps({
                "type": "action_invalid",
                "message": validation_result.get("message", "Action not allowed")
            }))
            return
        
        # Process action and generate narrative response
        action_result = await self._process_action_result(character, action, context, campaign_state)
        
        # Generate follow-up narrative
        follow_up_narrative = self.narrative_engine.generate_narrative(
            context=f"{character_name} {action.get('description', 'takes action')}. {action_result.get('description', '')}",
            encounter_type=self._determine_encounter_type(action),
            characters=campaign_state.active_characters,
            campaign_state=campaign_state
        )
        
        await websocket.send(json.dumps({
            "type": "action_result",
            "character_name": character_name,
            "action": action,
            "validation": validation_result,
            "result": action_result,
            "narrative": follow_up_narrative
        }))
    
    async def _process_action_result(self, character: CharacterProfile, 
                                   action: Dict[str, Any], context: str, 
                                   campaign_state: CampaignState) -> Dict[str, Any]:
        """Process the result of a player action"""
        action_type = action.get("type")
        
        if action_type == "skill_check":
            skill = action.get("skill")
            difficulty = action.get("difficulty", 15)
            
            skill_engine = SkillEngine()
            result = skill_engine.process_skill_check(character, skill, difficulty, 
                                                    {"context": context})
            
            return {
                "type": "skill_check_result",
                "success": result["success"],
                "degree": result["degree"],
                "total": result["total"],
                "description": self._generate_skill_check_description(result, character, skill)
            }
        
        elif action_type == "attack":
            combat_engine = CombatEngine()
            result = combat_engine.process_combat_action(action)
            
            return {
                "type": "attack_result",
                "success": result["success"],
                "critical_hit": result.get("critical_hit", False),
                "damage": result.get("damage", 0),
                "description": result["message"]
            }
        
        elif action_type == "spell_cast":
            # Simplified spell casting result
            spell_name = action.get("spell", "Magic Missile")
            spell_level = action.get("level", 1)
            
            return {
                "type": "spell_result", 
                "success": True,
                "spell_name": spell_name,
                "spell_level": spell_level,
                "description": f"{character.name} successfully casts {spell_name} at level {spell_level}!"
            }
        
        else:
            return {
                "type": "general_result",
                "success": True,
                "description": f"{character.name} attempts {action.get('description', 'an action')} and succeeds through determination!"
            }
    
    def _generate_skill_check_description(self, result: Dict[str, Any], 
                                        character: CharacterProfile, skill: str) -> str:
        """Generate narrative description for skill check results"""
        degree = result["degree"]
        character_name = character.name
        
        descriptions = {
            "critical_success": f"{character_name} performs the {skill} check with exceptional mastery, achieving far more than expected!",
            "great_success": f"{character_name} executes the {skill} check with impressive skill and confidence!",
            "success": f"{character_name} successfully completes the {skill} check.",
            "failure": f"{character_name} attempts the {skill} check but falls short of the goal.",
            "significant_failure": f"{character_name} struggles significantly with the {skill} check, making little progress.",
            "critical_failure": f"{character_name}'s attempt at the {skill} check goes dramatically awry, potentially causing complications!"
        }
        
        return descriptions.get(degree, f"{character_name} attempts a {skill} check.")
    
    def _determine_encounter_type(self, action: Dict[str, Any]) -> EncounterType:
        """Determine encounter type based on action"""
        action_type = action.get("type", "")
        
        if action_type in ["attack", "spell_cast"]:
            return EncounterType.COMBAT
        elif action_type in ["persuasion", "deception", "intimidation"]:
            return EncounterType.SOCIAL
        elif action_type in ["investigation", "perception", "insight"]:
            return EncounterType.INVESTIGATION
        elif action_type in ["stealth", "athletics", "survival"]:
            return EncounterType.EXPLORATION
        else:
            return EncounterType.ROLEPLAY

async def main():
    """Main entry point for AI Dungeon Master"""
    logging.basicConfig(level=logging.INFO)
    
    ai_dm = AIDungeonMaster(port=8411)
    
    try:
        await ai_dm.start_server()
    except KeyboardInterrupt:
        logger.info("AI Dungeon Master stopped by user")

if __name__ == "__main__":
    asyncio.run(main())