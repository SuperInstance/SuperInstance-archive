"""
Party banter generation service for dynamic character interactions.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
import logging

from ..models.dialogue import (
    DialogueType, DialogueContext, ConversationTone,
    BanterExchange, ConversationTurn, DialogueGenerationOptions
)
from ..models.base import EmotionType, CharacterType, CharacterRace
from ..models.personality import PersonalityProfileSchema
from ..models.memory import MemorySchema
from ..models.faction import FactionReputationSchema
from ..services.dialogue_service import DialogueService
from ..config import Config

logger = logging.getLogger(__name__)

class BanterService:
    def __init__(self):
        self.config = Config()
        self.dialogue_service = DialogueService()
        self.banter_triggers = self._initialize_banter_triggers()
        self.relationship_dynamics = self._initialize_relationship_dynamics()
        self.banter_templates = self._initialize_banter_templates()
        self.topic_libraries = self._initialize_topic_libraries()
        
    def _initialize_banter_triggers(self) -> Dict[str, Dict[str, Any]]:
        """Initialize triggers that can start banter exchanges."""
        return {
            "location_change": {
                "probability": 0.3,
                "topics": ["environment", "memories", "observations"],
                "min_relationship": 0.2,
                "suitable_contexts": ["travel", "exploration", "rest"]
            },
            
            "combat_victory": {
                "probability": 0.6,
                "topics": ["combat_skills", "teamwork", "adrenaline"],
                "min_relationship": 0.1,
                "suitable_contexts": ["post_combat", "celebration"]
            },
            
            "camp_rest": {
                "probability": 0.8,
                "topics": ["personal_stories", "philosophy", "future_plans", "past_adventures"],
                "min_relationship": 0.3,
                "suitable_contexts": ["rest", "campfire", "downtime"]
            },
            
            "quest_completion": {
                "probability": 0.5,
                "topics": ["achievement", "rewards", "next_steps"],
                "min_relationship": 0.2,
                "suitable_contexts": ["celebration", "planning"]
            },
            
            "character_interaction": {
                "probability": 0.4,
                "topics": ["personality_clash", "mutual_interests", "shared_experiences"],
                "min_relationship": 0.0,  # Can happen even with low relationship
                "suitable_contexts": ["any"]
            },
            
            "environmental_hazard": {
                "probability": 0.3,
                "topics": ["survival", "concern", "problem_solving"],
                "min_relationship": 0.1,
                "suitable_contexts": ["danger", "challenge"]
            },
            
            "story_revelation": {
                "probability": 0.7,
                "topics": ["plot_discussion", "theories", "implications"],
                "min_relationship": 0.4,
                "suitable_contexts": ["exposition", "planning"]
            },
            
            "item_discovery": {
                "probability": 0.2,
                "topics": ["item_value", "memories", "practical_use"],
                "min_relationship": 0.1,
                "suitable_contexts": ["exploration", "loot_division"]
            }
        }
    
    def _initialize_relationship_dynamics(self) -> Dict[str, Dict[str, Any]]:
        """Initialize how different relationship types affect banter."""
        return {
            "strangers": {
                "relationship_range": (0.0, 0.2),
                "common_topics": ["introductions", "surface_observations", "professional_matters"],
                "tone_preferences": [ConversationTone.FORMAL, ConversationTone.CASUAL],
                "exchange_length": (1, 2),
                "personal_sharing": 0.1
            },
            
            "acquaintances": {
                "relationship_range": (0.2, 0.4),
                "common_topics": ["shared_experiences", "opinions", "light_personal_info"],
                "tone_preferences": [ConversationTone.CASUAL, ConversationTone.FRIENDLY],
                "exchange_length": (2, 3),
                "personal_sharing": 0.3
            },
            
            "friends": {
                "relationship_range": (0.4, 0.7),
                "common_topics": ["personal_stories", "jokes", "mutual_support", "memories"],
                "tone_preferences": [ConversationTone.FRIENDLY, ConversationTone.HUMOROUS],
                "exchange_length": (2, 4),
                "personal_sharing": 0.6
            },
            
            "close_friends": {
                "relationship_range": (0.7, 0.9),
                "common_topics": ["deep_thoughts", "fears", "dreams", "intimate_memories"],
                "tone_preferences": [ConversationTone.FRIENDLY, ConversationTone.SERIOUS],
                "exchange_length": (3, 5),
                "personal_sharing": 0.8
            },
            
            "romantic": {
                "relationship_range": (0.5, 1.0),  # Can start at moderate friendship
                "common_topics": ["feelings", "future_together", "intimate_thoughts"],
                "tone_preferences": [ConversationTone.FLIRTATIOUS, ConversationTone.FRIENDLY],
                "exchange_length": (2, 4),
                "personal_sharing": 0.9
            },
            
            "rivals": {
                "relationship_range": (-0.5, 0.3),
                "common_topics": ["competition", "challenges", "disagreements"],
                "tone_preferences": [ConversationTone.HOSTILE, ConversationTone.INTIMIDATING],
                "exchange_length": (1, 3),
                "personal_sharing": 0.2
            },
            
            "enemies": {
                "relationship_range": (-1.0, -0.3),
                "common_topics": ["threats", "past_grievances", "warnings"],
                "tone_preferences": [ConversationTone.HOSTILE, ConversationTone.INTIMIDATING],
                "exchange_length": (1, 2),
                "personal_sharing": 0.0
            }
        }
    
    def _initialize_banter_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize banter templates for different topics."""
        return {
            "combat_skills": [
                {
                    "initiator": "Nice work with that {weapon} back there, {target}.",
                    "response": "Thanks! I've been practicing. Your {skill} was impressive too.",
                    "tone": ConversationTone.FRIENDLY,
                    "relationship_required": 0.3
                },
                {
                    "initiator": "You fight like you learned from a book, {target}.",
                    "response": "Better than fighting like I learned from a tavern brawl.",
                    "tone": ConversationTone.HUMOROUS,
                    "relationship_required": 0.4
                },
                {
                    "initiator": "Try to keep up next time, {target}.",
                    "response": "I was busy making sure you didn't get yourself killed.",
                    "tone": ConversationTone.HOSTILE,
                    "relationship_required": -0.2
                }
            ],
            
            "personal_stories": [
                {
                    "initiator": "This place reminds me of where I grew up.",
                    "response": "Tell me about it. I'd like to hear more about your past.",
                    "tone": ConversationTone.FRIENDLY,
                    "relationship_required": 0.5
                },
                {
                    "initiator": "I had a friend once who would have loved this adventure.",
                    "response": "What happened to them?",
                    "tone": ConversationTone.SERIOUS,
                    "relationship_required": 0.6
                }
            ],
            
            "philosophy": [
                {
                    "initiator": "Do you ever wonder if we're making the right choices?",
                    "response": "Every day. But I think doubting ourselves means we still have a conscience.",
                    "tone": ConversationTone.SERIOUS,
                    "relationship_required": 0.5
                },
                {
                    "initiator": "The world is more complicated than I thought when I was younger.",
                    "response": "Isn't that the truth. Nothing is ever as simple as it seems.",
                    "tone": ConversationTone.SERIOUS,
                    "relationship_required": 0.4
                }
            ],
            
            "environment": [
                {
                    "initiator": "Beautiful view from up here.",
                    "response": "Makes all the climbing worth it. Almost.",
                    "tone": ConversationTone.CASUAL,
                    "relationship_required": 0.2
                },
                {
                    "initiator": "This weather is miserable.",
                    "response": "Could be worse. Could be raining demons.",
                    "tone": ConversationTone.HUMOROUS,
                    "relationship_required": 0.3
                }
            ],
            
            "teamwork": [
                {
                    "initiator": "We make a good team, {target}.",
                    "response": "We do. I'm glad to have you watching my back.",
                    "tone": ConversationTone.FRIENDLY,
                    "relationship_required": 0.4
                },
                {
                    "initiator": "Next time, let's coordinate our attacks better.",
                    "response": "Agreed. We can be more effective working together.",
                    "tone": ConversationTone.CASUAL,
                    "relationship_required": 0.3
                }
            ]
        }
    
    def _initialize_topic_libraries(self) -> Dict[CharacterType, List[str]]:
        """Initialize topic preferences by character type."""
        return {
            CharacterType.WARRIOR: [
                "combat_tactics", "weapons", "training", "honor", "battles", "strength"
            ],
            CharacterType.MAGE: [
                "magic_theory", "ancient_knowledge", "mysteries", "books", "research", "wisdom"
            ],
            CharacterType.ROGUE: [
                "urban_life", "secrets", "opportunities", "survival", "street_smarts", "freedom"
            ],
            CharacterType.CLERIC: [
                "faith", "morality", "helping_others", "divine_will", "community", "healing"
            ],
            CharacterType.RANGER: [
                "nature", "animals", "wilderness", "tracking", "solitude", "balance"
            ],
            CharacterType.BARD: [
                "stories", "music", "culture", "people", "entertainment", "emotions"
            ],
            CharacterType.NOBLE: [
                "politics", "responsibility", "leadership", "etiquette", "legacy", "duty"
            ],
            CharacterType.MERCHANT: [
                "trade", "profit", "negotiations", "travel", "opportunities", "value"
            ],
            CharacterType.SCHOLAR: [
                "knowledge", "research", "history", "theories", "learning", "discovery"
            ]
        }

    async def generate_party_banter(
        self,
        participants: List[str],
        trigger: str,
        context: Dict[str, Any],
        character_data: Dict[str, Dict[str, Any]],
        db_session: Optional[Session] = None
    ) -> Optional[BanterExchange]:
        """Generate a banter exchange between party members."""
        
        if len(participants) < 2:
            return None
        
        # Check if this trigger should generate banter
        trigger_info = self.banter_triggers.get(trigger)
        if not trigger_info:
            return None
        
        # Probability check
        if random.random() > trigger_info["probability"]:
            return None
        
        # Select two participants for the exchange
        initiator_id, target_id = await self._select_banter_participants(
            participants, character_data, context
        )
        
        if not initiator_id or not target_id:
            return None
        
        # Get character information
        initiator_data = character_data.get(initiator_id, {})
        target_data = character_data.get(target_id, {})
        
        # Determine relationship level
        relationship_level = await self._calculate_relationship_level(
            initiator_id, target_id, character_data
        )
        
        # Check minimum relationship requirement
        if relationship_level < trigger_info["min_relationship"]:
            return None
        
        # Select topic
        topic = await self._select_banter_topic(
            trigger_info["topics"], initiator_data, target_data, context
        )
        
        # Generate banter exchange
        banter = await self._generate_banter_exchange(
            initiator_id, target_id, topic, relationship_level,
            initiator_data, target_data, context
        )
        
        return banter

    async def generate_contextual_banter(
        self,
        initiator_id: str,
        target_id: str,
        topic: str,
        character_data: Dict[str, Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[BanterExchange]:
        """Generate banter for a specific topic between two characters."""
        
        initiator_data = character_data.get(initiator_id, {})
        target_data = character_data.get(target_id, {})
        
        if not initiator_data or not target_data:
            return None
        
        # Calculate relationship
        relationship_level = await self._calculate_relationship_level(
            initiator_id, target_id, character_data
        )
        
        # Generate the exchange
        return await self._generate_banter_exchange(
            initiator_id, target_id, topic, relationship_level,
            initiator_data, target_data, context or {}
        )

    async def suggest_banter_opportunities(
        self,
        participants: List[str],
        current_context: Dict[str, Any],
        character_data: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Suggest opportunities for banter based on current context."""
        
        opportunities = []
        
        for trigger, trigger_info in self.banter_triggers.items():
            # Check if current context matches trigger requirements
            if await self._context_matches_trigger(current_context, trigger_info):
                # Find suitable character pairs
                for i, char_a in enumerate(participants):
                    for char_b in participants[i+1:]:
                        relationship = await self._calculate_relationship_level(
                            char_a, char_b, character_data
                        )
                        
                        if relationship >= trigger_info["min_relationship"]:
                            opportunities.append({
                                "trigger": trigger,
                                "participants": [char_a, char_b],
                                "probability": trigger_info["probability"],
                                "potential_topics": trigger_info["topics"],
                                "relationship_level": relationship
                            })
        
        # Sort by probability and relationship strength
        opportunities.sort(
            key=lambda x: (x["probability"] * x["relationship_level"]),
            reverse=True
        )
        
        return opportunities[:5]  # Return top 5 opportunities

    async def analyze_party_dynamics(
        self,
        participants: List[str],
        character_data: Dict[str, Dict[str, Any]],
        interaction_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Analyze party dynamics for banter generation."""
        
        analysis = {
            "total_members": len(participants),
            "relationship_matrix": {},
            "dominant_personalities": [],
            "conflict_pairs": [],
            "synergy_pairs": [],
            "banter_frequency": {},
            "topic_preferences": {},
            "group_cohesion": 0.0
        }
        
        # Build relationship matrix
        total_relationship = 0.0
        relationship_count = 0
        
        for i, char_a in enumerate(participants):
            analysis["relationship_matrix"][char_a] = {}
            for char_b in participants:
                if char_a != char_b:
                    relationship = await self._calculate_relationship_level(
                        char_a, char_b, character_data
                    )
                    analysis["relationship_matrix"][char_a][char_b] = relationship
                    
                    if i < participants.index(char_b):  # Avoid double counting
                        total_relationship += relationship
                        relationship_count += 1
                        
                        # Identify conflicts and synergies
                        if relationship < -0.3:
                            analysis["conflict_pairs"].append([char_a, char_b])
                        elif relationship > 0.6:
                            analysis["synergy_pairs"].append([char_a, char_b])
        
        # Calculate group cohesion
        if relationship_count > 0:
            analysis["group_cohesion"] = total_relationship / relationship_count
        
        # Identify dominant personalities
        for char_id in participants:
            char_data = character_data.get(char_id, {})
            personality = char_data.get("personality", {})
            
            if personality.get("extraversion", 0.5) > 0.7:
                analysis["dominant_personalities"].append({
                    "character_id": char_id,
                    "type": "extraverted",
                    "influence": personality.get("extraversion", 0.5)
                })
            elif personality.get("agreeableness", 0.5) < 0.3:
                analysis["dominant_personalities"].append({
                    "character_id": char_id,
                    "type": "disagreeable",
                    "influence": 1.0 - personality.get("agreeableness", 0.5)
                })
        
        # Analyze topic preferences
        for char_id in participants:
            char_data = character_data.get(char_id, {})
            char_type = char_data.get("character_type", CharacterType.COMMONER)
            
            if char_type in self.topic_libraries:
                for topic in self.topic_libraries[char_type]:
                    if topic not in analysis["topic_preferences"]:
                        analysis["topic_preferences"][topic] = 0
                    analysis["topic_preferences"][topic] += 1
        
        return analysis

    async def _select_banter_participants(
        self,
        participants: List[str],
        character_data: Dict[str, Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Select two characters for a banter exchange."""
        
        # Weight participants by their likelihood to initiate banter
        weighted_participants = []
        
        for char_id in participants:
            char_data = character_data.get(char_id, {})
            personality = char_data.get("personality", {})
            
            # Extraverts more likely to initiate
            weight = personality.get("extraversion", 0.5)
            
            # Agreeable characters also more likely in friendly contexts
            if context.get("mood", "neutral") in ["friendly", "casual"]:
                weight += personality.get("agreeableness", 0.5) * 0.3
            
            # Open characters more likely in new/interesting contexts
            if context.get("novelty", False):
                weight += personality.get("openness", 0.5) * 0.2
            
            weighted_participants.append((char_id, weight))
        
        # Select initiator
        weighted_participants.sort(key=lambda x: x[1], reverse=True)
        initiator_candidates = weighted_participants[:3]  # Top 3 candidates
        
        if not initiator_candidates:
            return None, None
        
        initiator_id = random.choices(
            [p[0] for p in initiator_candidates],
            weights=[p[1] for p in initiator_candidates]
        )[0]
        
        # Select target (prefer those with existing relationship)
        remaining_participants = [p for p in participants if p != initiator_id]
        if not remaining_participants:
            return None, None
        
        # Weight targets by relationship strength
        target_weights = []
        for target_id in remaining_participants:
            relationship = await self._calculate_relationship_level(
                initiator_id, target_id, character_data
            )
            # Higher relationships more likely, but also some chance for new interactions
            weight = abs(relationship) + 0.2  # Small base chance for everyone
            target_weights.append(weight)
        
        target_id = random.choices(remaining_participants, weights=target_weights)[0]
        
        return initiator_id, target_id

    async def _calculate_relationship_level(
        self,
        char_a_id: str,
        char_b_id: str,
        character_data: Dict[str, Dict[str, Any]]
    ) -> float:
        """Calculate relationship level between two characters."""
        
        # In a real implementation, this would check relationship history,
        # shared experiences, faction alignments, etc.
        
        char_a_data = character_data.get(char_a_id, {})
        char_b_data = character_data.get(char_b_id, {})
        
        # Base relationship from personality compatibility
        personality_a = char_a_data.get("personality", {})
        personality_b = char_b_data.get("personality", {})
        
        # Calculate personality compatibility
        compatibility = 0.0
        compatibility_factors = 0
        
        for trait in ["extraversion", "agreeableness", "conscientiousness", "openness"]:
            if trait in personality_a and trait in personality_b:
                # Similar personalities tend to get along (but not always)
                diff = abs(personality_a[trait] - personality_b[trait])
                if trait == "agreeableness":
                    # High agreeableness always helps
                    compatibility += min(personality_a[trait], personality_b[trait]) * 0.3
                elif trait == "extraversion":
                    # Complementary extraversion can work well
                    if diff > 0.3:
                        compatibility += 0.1  # Opposites can attract
                    else:
                        compatibility += (1.0 - diff) * 0.2
                else:
                    compatibility += (1.0 - diff) * 0.1
                compatibility_factors += 1
        
        if compatibility_factors > 0:
            base_relationship = (compatibility / compatibility_factors) - 0.5  # Center around 0
        else:
            base_relationship = 0.0
        
        # Add some randomness for unique relationships
        base_relationship += random.uniform(-0.2, 0.2)
        
        # Clamp to valid range
        return max(-1.0, min(1.0, base_relationship))

    async def _select_banter_topic(
        self,
        available_topics: List[str],
        initiator_data: Dict[str, Any],
        target_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Select an appropriate topic for the banter."""
        
        topic_weights = {}
        
        for topic in available_topics:
            weight = 1.0  # Base weight
            
            # Check character type preferences
            initiator_type = initiator_data.get("character_type", CharacterType.COMMONER)
            target_type = target_data.get("character_type", CharacterType.COMMONER)
            
            initiator_topics = self.topic_libraries.get(initiator_type, [])
            target_topics = self.topic_libraries.get(target_type, [])
            
            if topic in initiator_topics:
                weight += 0.5
            if topic in target_topics:
                weight += 0.5
            
            # Context relevance
            if context.get("recent_combat") and topic == "combat_skills":
                weight += 1.0
            elif context.get("resting") and topic == "personal_stories":
                weight += 0.8
            elif context.get("exploration") and topic == "environment":
                weight += 0.6
            
            topic_weights[topic] = weight
        
        # Select topic based on weights
        if topic_weights:
            topics = list(topic_weights.keys())
            weights = list(topic_weights.values())
            return random.choices(topics, weights=weights)[0]
        
        return random.choice(available_topics)

    async def _generate_banter_exchange(
        self,
        initiator_id: str,
        target_id: str,
        topic: str,
        relationship_level: float,
        initiator_data: Dict[str, Any],
        target_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> BanterExchange:
        """Generate the actual banter exchange."""
        
        # Determine relationship category
        relationship_category = await self._categorize_relationship(relationship_level)
        relationship_info = self.relationship_dynamics[relationship_category]
        
        # Select appropriate tone
        tone = random.choice(relationship_info["tone_preferences"])
        
        # Determine exchange length
        min_length, max_length = relationship_info["exchange_length"]
        exchange_length = random.randint(min_length, max_length)
        
        # Generate exchange text
        exchange_text = []
        
        # Try to use templates first
        if topic in self.banter_templates:
            suitable_templates = [
                template for template in self.banter_templates[topic]
                if template["relationship_required"] <= relationship_level
            ]
            
            if suitable_templates:
                template = random.choice(suitable_templates)
                
                # Fill in template variables
                initiator_name = initiator_data.get("name", initiator_id)
                target_name = target_data.get("name", target_id)
                
                initiator_line = template["initiator"].format(
                    target=target_name,
                    weapon=random.choice(["sword", "bow", "staff", "blade"]),
                    skill=random.choice(["timing", "technique", "strategy", "instincts"])
                )
                
                response_line = template["response"].format(
                    initiator=initiator_name
                )
                
                exchange_text.extend([initiator_line, response_line])
                tone = template.get("tone", tone)
        
        # Generate additional lines if needed
        while len(exchange_text) < exchange_length:
            if len(exchange_text) % 2 == 0:
                # Initiator's turn
                line = await self._generate_banter_line(
                    initiator_id, target_id, topic, tone, initiator_data, target_data, context
                )
            else:
                # Target's turn
                line = await self._generate_banter_line(
                    target_id, initiator_id, topic, tone, target_data, initiator_data, context
                )
            
            exchange_text.append(line)
        
        return BanterExchange(
            initiator_id=initiator_id,
            target_id=target_id,
            banter_type=relationship_category,
            exchange_text=exchange_text,
            relationship_requirement=relationship_level,
            personality_compatibility=await self._calculate_personality_compatibility(
                initiator_data, target_data
            )
        )

    async def _categorize_relationship(self, relationship_level: float) -> str:
        """Categorize relationship level into a type."""
        
        for category, info in self.relationship_dynamics.items():
            min_rel, max_rel = info["relationship_range"]
            if min_rel <= relationship_level <= max_rel:
                return category
        
        return "acquaintances"  # Default fallback

    async def _calculate_personality_compatibility(
        self,
        char_a_data: Dict[str, Any],
        char_b_data: Dict[str, Any]
    ) -> float:
        """Calculate personality compatibility between two characters."""
        
        personality_a = char_a_data.get("personality", {})
        personality_b = char_b_data.get("personality", {})
        
        if not personality_a or not personality_b:
            return 0.5
        
        compatibility = 0.0
        trait_count = 0
        
        for trait in ["extraversion", "agreeableness", "conscientiousness", "neuroticism", "openness"]:
            if trait in personality_a and trait in personality_b:
                # Some traits are better when similar, others when different
                diff = abs(personality_a[trait] - personality_b[trait])
                
                if trait in ["agreeableness", "conscientiousness"]:
                    # These are generally better when both are high
                    compatibility += min(personality_a[trait], personality_b[trait])
                elif trait == "neuroticism":
                    # Lower neuroticism generally better for relationships
                    compatibility += 1.0 - max(personality_a[trait], personality_b[trait])
                else:
                    # For extraversion and openness, moderate differences can be good
                    if diff < 0.3:
                        compatibility += 1.0 - diff
                    else:
                        compatibility += 0.7  # Different but not incompatible
                
                trait_count += 1
        
        if trait_count > 0:
            return compatibility / trait_count
        
        return 0.5

    async def _generate_banter_line(
        self,
        speaker_id: str,
        target_id: str,
        topic: str,
        tone: ConversationTone,
        speaker_data: Dict[str, Any],
        target_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Generate a single line of banter."""
        
        # Get speaker's personality for line generation
        personality = speaker_data.get("personality", {})
        character_type = speaker_data.get("character_type", CharacterType.COMMONER)
        
        # Base templates by topic and tone
        line_templates = {
            "combat_skills": {
                ConversationTone.FRIENDLY: [
                    "You're getting better at this.",
                    "Nice technique back there.",
                    "We make a good team in a fight."
                ],
                ConversationTone.HUMOROUS: [
                    "Try not to hit me next time!",
                    "I think you missed the enemy and hit that tree.",
                    "Remind me to stay behind you in battle."
                ],
                ConversationTone.HOSTILE: [
                    "Try to keep up.",
                    "I've seen children fight better.",
                    "Next time, let me handle it."
                ]
            },
            "environment": {
                ConversationTone.CASUAL: [
                    "Nice view from here.",
                    "This place gives me the creeps.",
                    "I wonder what's over that hill."
                ],
                ConversationTone.HUMOROUS: [
                    "Are we there yet?",
                    "My feet are killing me.",
                    "Next time, I'm bringing a horse."
                ]
            }
        }
        
        # Try to find suitable templates
        if topic in line_templates and tone in line_templates[topic]:
            templates = line_templates[topic][tone]
            base_line = random.choice(templates)
        else:
            # Generic fallback
            generic_templates = [
                "What do you think?",
                "Interesting.",
                "I suppose.",
                "Fair enough."
            ]
            base_line = random.choice(generic_templates)
        
        # Modify line based on personality
        if personality.get("extraversion", 0.5) > 0.7:
            # More enthusiastic
            if "." in base_line:
                base_line = base_line.replace(".", "!")
        elif personality.get("extraversion", 0.5) < 0.3:
            # More reserved
            base_line = base_line.lower()
        
        if personality.get("agreeableness", 0.5) > 0.7:
            # Add politeness
            polite_additions = ["please", "if you don't mind", "I think"]
            if random.random() < 0.3:
                addition = random.choice(polite_additions)
                base_line = f"{addition}, {base_line.lower()}"
        
        return base_line

    async def _context_matches_trigger(
        self,
        current_context: Dict[str, Any],
        trigger_info: Dict[str, Any]
    ) -> bool:
        """Check if current context matches trigger requirements."""
        
        suitable_contexts = trigger_info.get("suitable_contexts", ["any"])
        
        if "any" in suitable_contexts:
            return True
        
        context_type = current_context.get("type", "general")
        return context_type in suitable_contexts