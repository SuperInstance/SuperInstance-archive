"""
Dialogue generation service for character AI system.
"""

import random
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
from sqlalchemy.orm import Session

from ..models.dialogue import (
    DialogueType, DialogueContext, ConversationTone,
    DialogueRequest, DialogueResponse, ConversationTurn,
    DialogueTemplate, ConversationHistory, ConversationPattern,
    DialogueTemplateSchema, ConversationSchema, BanterExchange,
    DialogueGenerationOptions, TopicKnowledge, ConversationGoal,
    DialogueVariables
)
from ..models.personality import PersonalityProfileSchema, MoralAlignment
from ..models.base import EmotionType, CharacterType, AccentType, SpeechPattern
from ..config import Config

logger = logging.getLogger(__name__)

class DialogueService:
    def __init__(self):
        self.config = Config()
        self.dialogue_templates = {}
        self.conversation_patterns = {}
        self.speech_modifiers = self._initialize_speech_modifiers()
        self.accent_patterns = self._initialize_accent_patterns()
        
    def _initialize_speech_modifiers(self) -> Dict[str, Dict[str, Any]]:
        """Initialize speech pattern modifiers for different character types."""
        return {
            SpeechPattern.FORMAL.value: {
                "word_choices": ["indeed", "certainly", "perhaps", "quite"],
                "sentence_structure": "formal",
                "contractions": False,
                "politeness_level": 0.9
            },
            SpeechPattern.CASUAL.value: {
                "word_choices": ["yeah", "sure", "maybe", "kinda"],
                "sentence_structure": "casual",
                "contractions": True,
                "politeness_level": 0.5
            },
            SpeechPattern.ARCHAIC.value: {
                "word_choices": ["thee", "thou", "doth", "verily"],
                "sentence_structure": "archaic",
                "contractions": False,
                "politeness_level": 0.8
            },
            SpeechPattern.MILITARY.value: {
                "word_choices": ["sir", "affirmative", "negative", "understood"],
                "sentence_structure": "direct",
                "contractions": False,
                "politeness_level": 0.7
            }
        }
        
    def _initialize_accent_patterns(self) -> Dict[str, Dict[str, str]]:
        """Initialize accent-specific pronunciation patterns."""
        return {
            AccentType.BRITISH.value: {
                "r_dropping": True,
                "vowel_shifts": {"a": "ah", "o": "ou"},
                "vocabulary": {"elevator": "lift", "apartment": "flat"}
            },
            AccentType.SCOTTISH.value: {
                "r_rolling": True,
                "vowel_shifts": {"u": "oo", "i": "ee"},
                "vocabulary": {"small": "wee", "know": "ken"}
            },
            AccentType.DWARVEN.value: {
                "consonant_emphasis": True,
                "vowel_shifts": {"a": "ah", "e": "eh"},
                "vocabulary": {"friend": "kinsman", "gold": "precious metal"}
            }
        }

    async def generate_dialogue(
        self,
        request: DialogueRequest,
        personality: PersonalityProfileSchema,
        character_background: Dict[str, Any],
        options: Optional[DialogueGenerationOptions] = None
    ) -> DialogueResponse:
        """Generate dialogue based on character personality and context."""
        
        if options is None:
            options = DialogueGenerationOptions()
            
        # Get dialogue template
        template = await self._select_dialogue_template(
            request, personality, character_background
        )
        
        # Generate base dialogue text
        dialogue_text = await self._generate_dialogue_text(
            template, request, personality, character_background, options
        )
        
        # Apply personality influence
        dialogue_text = await self._apply_personality_influence(
            dialogue_text, personality, options
        )
        
        # Apply speech patterns and accents
        dialogue_text = await self._apply_speech_patterns(
            dialogue_text, character_background, options
        )
        
        # Determine tone and emotion
        tone = await self._determine_conversation_tone(
            request, personality, character_background
        )
        emotion = await self._determine_emotion(
            request, personality, character_background
        )
        
        # Calculate confidence based on personality and situation
        confidence = await self._calculate_confidence(
            request, personality, character_background
        )
        
        # Generate suggested responses for dialogue tree
        suggested_responses = await self._generate_suggested_responses(
            request, personality, dialogue_text
        )
        
        # Calculate personality influence scores
        personality_influence = await self._calculate_personality_influence(
            personality, request.dialogue_type, request.context
        )
        
        return DialogueResponse(
            dialogue_text=dialogue_text,
            tone=tone,
            emotion=emotion,
            confidence=confidence,
            template_used=template.get("name") if template else None,
            variables_filled=template.get("variables", {}) if template else {},
            personality_influence=personality_influence,
            suggested_responses=suggested_responses
        )

    async def _select_dialogue_template(
        self,
        request: DialogueRequest,
        personality: PersonalityProfileSchema,
        background: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Select appropriate dialogue template based on context."""
        
        # Check for existing templates matching criteria
        suitable_templates = []
        
        # In a real implementation, this would query the database
        # For now, we'll generate templates dynamically
        base_templates = {
            DialogueType.GREETING: [
                "Hello there! How are you doing?",
                "Greetings, {target_name}. What brings you here?",
                "Well met, traveler. Welcome to {location}."
            ],
            DialogueType.FAREWELL: [
                "Safe travels, {target_name}.",
                "Until we meet again.",
                "May fortune smile upon you."
            ],
            DialogueType.QUEST_OFFER: [
                "I have a task that requires someone of your skills.",
                "There's something I need help with, if you're interested.",
                "A quest awaits, should you choose to accept it."
            ],
            DialogueType.SHOP_INTERACTION: [
                "What can I interest you in today?",
                "Browse my wares, {target_name}.",
                "I have the finest goods in all the land."
            ]
        }
        
        templates = base_templates.get(request.dialogue_type, [
            "I'm not sure what to say about that.",
            "That's interesting, {target_name}.",
            "Tell me more."
        ])
        
        selected_template = random.choice(templates)
        
        return {
            "name": f"{request.dialogue_type.value}_template",
            "text": selected_template,
            "variables": {
                "target_name": request.target_character_id or "friend",
                "location": request.situation_context.get("location", "here") if request.situation_context else "here"
            }
        }

    async def _generate_dialogue_text(
        self,
        template: Optional[Dict[str, Any]],
        request: DialogueRequest,
        personality: PersonalityProfileSchema,
        background: Dict[str, Any],
        options: DialogueGenerationOptions
    ) -> str:
        """Generate the actual dialogue text from template and context."""
        
        if not template:
            return "I'm at a loss for words."
            
        dialogue_text = template["text"]
        variables = template.get("variables", {})
        
        # Fill in template variables
        for var_name, var_value in variables.items():
            placeholder = "{" + var_name + "}"
            dialogue_text = dialogue_text.replace(placeholder, str(var_value))
            
        # Add personality-based modifications
        if options.creativity_level > 0.5:
            dialogue_text = await self._add_creative_elements(
                dialogue_text, personality, options
            )
            
        return dialogue_text

    async def _apply_personality_influence(
        self,
        text: str,
        personality: PersonalityProfileSchema,
        options: DialogueGenerationOptions
    ) -> str:
        """Modify dialogue based on personality traits."""
        
        modified_text = text
        
        # High extraversion - more enthusiastic
        if personality.extraversion > 0.7:
            modified_text = modified_text.replace(".", "!")
            if not modified_text.endswith("!") and not modified_text.endswith("?"):
                modified_text += " It's great to meet you!"
                
        # High neuroticism - add uncertainty
        elif personality.neuroticism > 0.7:
            uncertainty_words = ["perhaps", "maybe", "I think", "possibly"]
            if random.random() < 0.3:
                word = random.choice(uncertainty_words)
                modified_text = f"{word}, {modified_text.lower()}"
                
        # Low agreeableness - more direct/blunt
        if personality.agreeableness < 0.3:
            modified_text = modified_text.replace("please", "")
            modified_text = modified_text.replace("if you don't mind", "")
            
        # High conscientiousness - more structured
        if personality.conscientiousness > 0.7:
            if "." not in modified_text[-10:]:
                modified_text += "."
                
        return modified_text

    async def _apply_speech_patterns(
        self,
        text: str,
        background: Dict[str, Any],
        options: DialogueGenerationOptions
    ) -> str:
        """Apply speech patterns and accents to dialogue."""
        
        if not options.include_speech_patterns:
            return text
            
        speech_pattern = background.get("speech_pattern", SpeechPattern.NEUTRAL.value)
        accent = background.get("accent", AccentType.NEUTRAL.value)
        
        modified_text = text
        
        # Apply speech pattern modifications
        if speech_pattern in self.speech_modifiers:
            modifiers = self.speech_modifiers[speech_pattern]
            
            # Handle contractions
            if not modifiers["contractions"]:
                modified_text = modified_text.replace("can't", "cannot")
                modified_text = modified_text.replace("won't", "will not")
                modified_text = modified_text.replace("don't", "do not")
                
            # Add formal words if appropriate
            if modifiers["sentence_structure"] == "formal":
                if random.random() < 0.3:
                    formal_word = random.choice(modifiers["word_choices"])
                    modified_text = f"{formal_word}, {modified_text.lower()}"
                    
        # Apply accent modifications
        if accent in self.accent_patterns:
            patterns = self.accent_patterns[accent]
            
            # Apply vocabulary changes
            if "vocabulary" in patterns:
                for original, replacement in patterns["vocabulary"].items():
                    modified_text = modified_text.replace(original, replacement)
                    
            # Apply pronunciation changes (simplified)
            if "vowel_shifts" in patterns:
                for original, replacement in patterns["vowel_shifts"].items():
                    # Only apply to word boundaries to avoid over-replacement
                    modified_text = re.sub(
                        r'\b' + original + r'\b',
                        replacement,
                        modified_text,
                        flags=re.IGNORECASE
                    )
                    
        return modified_text

    async def _determine_conversation_tone(
        self,
        request: DialogueRequest,
        personality: PersonalityProfileSchema,
        background: Dict[str, Any]
    ) -> ConversationTone:
        """Determine appropriate conversation tone."""
        
        # Base tone on context
        context_tones = {
            DialogueContext.HOSTILE: ConversationTone.HOSTILE,
            DialogueContext.FRIENDLY: ConversationTone.FRIENDLY,
            DialogueContext.FORMAL: ConversationTone.FORMAL,
            DialogueContext.CASUAL: ConversationTone.CASUAL,
            DialogueContext.ROMANTIC: ConversationTone.FLIRTATIOUS
        }
        
        if request.context and request.context in context_tones:
            base_tone = context_tones[request.context]
        else:
            base_tone = ConversationTone.FRIENDLY
            
        # Modify based on personality
        if personality.extraversion > 0.7:
            if base_tone == ConversationTone.FRIENDLY:
                return ConversationTone.HUMOROUS
        elif personality.neuroticism > 0.7:
            if base_tone == ConversationTone.FRIENDLY:
                return ConversationTone.SERIOUS
                
        return base_tone

    async def _determine_emotion(
        self,
        request: DialogueRequest,
        personality: PersonalityProfileSchema,
        background: Dict[str, Any]
    ) -> EmotionType:
        """Determine emotional state for dialogue."""
        
        # Use requested emotional state if provided
        if request.emotional_state:
            return request.emotional_state
            
        # Base emotion on dialogue type and personality
        dialogue_emotions = {
            DialogueType.GREETING: EmotionType.JOY,
            DialogueType.FAREWELL: EmotionType.SADNESS,
            DialogueType.QUEST_OFFER: EmotionType.ANTICIPATION,
            DialogueType.COMBAT_TAUNT: EmotionType.ANGER,
            DialogueType.ROMANCE: EmotionType.LOVE
        }
        
        base_emotion = dialogue_emotions.get(request.dialogue_type, EmotionType.NEUTRAL)
        
        # Modify based on personality traits
        if personality.neuroticism > 0.7:
            if base_emotion == EmotionType.JOY:
                return EmotionType.ANXIETY
        elif personality.agreeableness < 0.3:
            if base_emotion == EmotionType.NEUTRAL:
                return EmotionType.ANGER
                
        return base_emotion

    async def _calculate_confidence(
        self,
        request: DialogueRequest,
        personality: PersonalityProfileSchema,
        background: Dict[str, Any]
    ) -> float:
        """Calculate confidence level for dialogue delivery."""
        
        base_confidence = 0.7
        
        # Personality influences
        confidence_modifiers = {
            "extraversion": personality.extraversion * 0.2,
            "conscientiousness": personality.conscientiousness * 0.15,
            "neuroticism": -personality.neuroticism * 0.3,
            "openness": personality.openness * 0.1
        }
        
        total_modifier = sum(confidence_modifiers.values())
        confidence = max(0.1, min(1.0, base_confidence + total_modifier))
        
        # Context adjustments
        if request.context == DialogueContext.HOSTILE:
            confidence *= 0.8
        elif request.context == DialogueContext.FAMILIAR:
            confidence *= 1.2
            
        return round(confidence, 2)

    async def _generate_suggested_responses(
        self,
        request: DialogueRequest,
        personality: PersonalityProfileSchema,
        dialogue_text: str
    ) -> List[str]:
        """Generate suggested player responses to the NPC dialogue."""
        
        response_templates = {
            DialogueType.GREETING: [
                "Hello! Nice to meet you.",
                "Greetings.",
                "Good day to you too."
            ],
            DialogueType.QUEST_OFFER: [
                "Tell me more about this quest.",
                "What's in it for me?",
                "I'm interested. What do you need?",
                "Sorry, I'm not available right now."
            ],
            DialogueType.SHOP_INTERACTION: [
                "What do you have for sale?",
                "I'm looking for [specific item].",
                "Your prices are too high.",
                "I'll take a look around."
            ]
        }
        
        suggestions = response_templates.get(request.dialogue_type, [
            "That's interesting.",
            "Tell me more.",
            "I understand.",
            "I have to go."
        ])
        
        # Limit to 3-4 suggestions
        return random.sample(suggestions, min(4, len(suggestions)))

    async def _calculate_personality_influence(
        self,
        personality: PersonalityProfileSchema,
        dialogue_type: DialogueType,
        context: Optional[DialogueContext]
    ) -> Dict[str, float]:
        """Calculate how much each personality trait influenced the dialogue."""
        
        influence_scores = {
            "extraversion": 0.0,
            "agreeableness": 0.0,
            "conscientiousness": 0.0,
            "neuroticism": 0.0,
            "openness": 0.0
        }
        
        # Base influence on dialogue type
        type_influences = {
            DialogueType.GREETING: {"extraversion": 0.8, "agreeableness": 0.6},
            DialogueType.COMBAT_TAUNT: {"extraversion": 0.9, "agreeableness": -0.7},
            DialogueType.QUEST_OFFER: {"conscientiousness": 0.7, "openness": 0.5},
            DialogueType.ROMANCE: {"extraversion": 0.6, "agreeableness": 0.8}
        }
        
        if dialogue_type in type_influences:
            for trait, influence in type_influences[dialogue_type].items():
                trait_value = getattr(personality, trait)
                influence_scores[trait] = trait_value * abs(influence)
                
        return influence_scores

    async def _add_creative_elements(
        self,
        text: str,
        personality: PersonalityProfileSchema,
        options: DialogueGenerationOptions
    ) -> str:
        """Add creative elements to dialogue based on personality."""
        
        if personality.openness > 0.7 and options.include_personality_quirks:
            creative_additions = [
                " *gestures expressively*",
                " *pauses thoughtfully*",
                " *smiles warmly*",
                " *looks distant for a moment*"
            ]
            
            if random.random() < 0.3:
                addition = random.choice(creative_additions)
                text += addition
                
        return text

    async def generate_banter(
        self,
        participants: List[str],
        banter_type: str,
        personalities: Dict[str, PersonalityProfileSchema],
        context: Dict[str, Any]
    ) -> List[ConversationTurn]:
        """Generate party banter between characters."""
        
        banter_turns = []
        
        # Generate 2-4 exchanges
        num_exchanges = random.randint(2, 4)
        
        for i in range(num_exchanges):
            # Alternate speakers
            speaker_id = participants[i % len(participants)]
            target_id = participants[(i + 1) % len(participants)]
            
            # Generate banter line
            banter_templates = {
                "friendly": [
                    "You know, {target}, I was just thinking...",
                    "Hey {target}, remember when we...",
                    "{target}, you always know how to make me laugh."
                ],
                "competitive": [
                    "Think you can keep up, {target}?",
                    "I bet I can do that better than you, {target}.",
                    "You're not as good as you think, {target}."
                ],
                "romantic": [
                    "You look beautiful today, {target}.",
                    "I can't stop thinking about you, {target}.",
                    "Stay close to me, {target}."
                ]
            }
            
            templates = banter_templates.get(banter_type, banter_templates["friendly"])
            banter_text = random.choice(templates).format(target=target_id)
            
            # Apply personality influence
            personality = personalities.get(speaker_id)
            if personality:
                if personality.extraversion > 0.7:
                    banter_text += "!"
                if personality.agreeableness < 0.3 and banter_type == "competitive":
                    banter_text = banter_text.replace("I bet", "I know")
                    
            turn = ConversationTurn(
                speaker_id=speaker_id,
                text=banter_text,
                tone=ConversationTone.CASUAL,
                context_data={"banter_type": banter_type}
            )
            
            banter_turns.append(turn)
            
        return banter_turns

    async def save_conversation(
        self,
        conversation: ConversationSchema,
        db_session: Session
    ) -> str:
        """Save conversation to database."""
        
        # In a real implementation, this would save to database
        # For now, just return a mock conversation ID
        conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Saved conversation {conversation_id} with {len(conversation.dialogue_entries)} turns")
        
        return conversation_id