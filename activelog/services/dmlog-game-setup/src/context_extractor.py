import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime
import openai
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class ExtractedContext(BaseModel):
    structured_data: Dict[str, Any]
    key_points: List[str]
    characters_mentioned: List[Dict[str, Any]]
    locations_mentioned: List[Dict[str, Any]]
    items_mentioned: List[Dict[str, Any]]
    plot_elements: List[Dict[str, Any]]
    tone_indicators: Dict[str, float]
    narrative_tension: float
    contains_character_voice: bool
    campaign_style: str
    complexity_level: str

@dataclass
class NPCData:
    name: str
    description: str
    personality_traits: List[str]
    role: str
    relationships: List[str]
    voice_notes: Optional[str] = None

@dataclass
class LocationData:
    name: str
    description: str
    type: str
    features: List[str]
    connections: List[str]
    atmosphere: str

@dataclass
class ItemData:
    name: str
    description: str
    type: str
    properties: List[str]
    value: str
    rarity: str

@dataclass
class EncounterData:
    name: str
    type: str
    difficulty: str
    participants: List[str]
    location: str
    narrative_purpose: str

class ContextExtractor:
    def __init__(self):
        try:
            # Only initialize OpenAI client if API key is available
            import os
            if os.getenv('OPENAI_API_KEY'):
                self.openai_client = openai.OpenAI() if hasattr(openai, 'OpenAI') else None
            else:
                self.openai_client = None
                logger.warning("OpenAI API key not found. AI-powered features will be limited.")
        except Exception as e:
            logger.warning(f"OpenAI client initialization failed: {e}")
            self.openai_client = None
        self.extraction_patterns = self._initialize_patterns()
        self.campaign_style_indicators = self._initialize_campaign_styles()
        self.narrative_tension_keywords = self._initialize_tension_keywords()

    def _initialize_patterns(self) -> Dict[str, re.Pattern]:
        """Initialize regex patterns for content extraction."""
        return {
            'character_names': re.compile(r'\b[A-Z][a-z]+ (?:the [A-Z][a-z]+|[A-Z][a-z]+)\b'),
            'locations': re.compile(r'\b(?:in|at|from|to) ([A-Z][a-z]+(?: [A-Z][a-z]+)*)\b'),
            'items': re.compile(r'\b(?:sword|shield|armor|potion|ring|staff|bow|dagger|tome|scroll|amulet|cloak)\b', re.IGNORECASE),
            'dice_rolls': re.compile(r'\bd\d+\b|\b\d+d\d+\b'),
            'stats': re.compile(r'\b(?:strength|dexterity|constitution|intelligence|wisdom|charisma|STR|DEX|CON|INT|WIS|CHA)\b', re.IGNORECASE),
            'actions': re.compile(r'\b(?:attack|defend|cast|heal|sneak|persuade|investigate|intimidate)\b', re.IGNORECASE),
            'emotions': re.compile(r'\b(?:angry|happy|sad|excited|nervous|confident|scared|determined)\b', re.IGNORECASE)
        }

    def _initialize_campaign_styles(self) -> Dict[str, List[str]]:
        """Initialize campaign style indicators."""
        return {
            'heroic_fantasy': ['hero', 'quest', 'save', 'kingdom', 'evil', 'noble', 'epic'],
            'dark_fantasy': ['horror', 'death', 'curse', 'shadow', 'nightmare', 'doom', 'corruption'],
            'urban_fantasy': ['modern', 'city', 'technology', 'contemporary', 'urban', 'street'],
            'high_fantasy': ['magic', 'wizard', 'dragon', 'elves', 'dwarves', 'ancient', 'mystical'],
            'political': ['intrigue', 'politics', 'court', 'nobility', 'alliance', 'betrayal', 'diplomacy'],
            'exploration': ['discover', 'explore', 'unknown', 'wilderness', 'adventure', 'journey', 'frontier'],
            'mystery': ['investigate', 'clues', 'mystery', 'secret', 'hidden', 'puzzle', 'reveal'],
            'comedy': ['funny', 'joke', 'laugh', 'silly', 'humor', 'comedy', 'amusing']
        }

    def _initialize_tension_keywords(self) -> Dict[str, float]:
        """Initialize narrative tension keywords with weights."""
        return {
            'conflict': 0.8, 'battle': 0.9, 'fight': 0.7, 'war': 0.9,
            'danger': 0.7, 'threat': 0.8, 'enemy': 0.6, 'villain': 0.7,
            'crisis': 0.9, 'urgent': 0.8, 'emergency': 0.9, 'deadline': 0.7,
            'betrayal': 0.8, 'trap': 0.8, 'ambush': 0.9, 'surprise': 0.6,
            'death': 0.9, 'dying': 0.8, 'wounded': 0.6, 'injured': 0.5,
            'chase': 0.8, 'pursuit': 0.7, 'escape': 0.7, 'flee': 0.7,
            'mystery': 0.5, 'secret': 0.4, 'hidden': 0.4, 'unknown': 0.5
        }

    async def extract_structured_data(self, transcription: str, context_history: List[str]) -> ExtractedContext:
        """Extract structured data from rambling descriptions."""
        try:
            # Basic pattern matching
            characters = self._extract_characters(transcription)
            locations = self._extract_locations(transcription)
            items = self._extract_items(transcription)
            plot_elements = self._extract_plot_elements(transcription)
            
            # Analyze tone and style
            tone_indicators = self._analyze_tone(transcription)
            narrative_tension = self._calculate_narrative_tension(transcription)
            campaign_style = self._determine_campaign_style(transcription, context_history)
            complexity_level = self._assess_complexity_level(transcription)
            
            # Check for character voice indicators
            contains_character_voice = self._detect_character_voice(transcription)
            
            # Generate key points summary
            key_points = await self._generate_key_points(transcription, context_history)
            
            # Structure the extracted data
            structured_data = {
                'main_topics': self._extract_main_topics(transcription),
                'game_mechanics': self._extract_game_mechanics(transcription),
                'world_building': self._extract_world_building_elements(transcription),
                'story_hooks': self._extract_story_hooks(transcription)
            }
            
            return ExtractedContext(
                structured_data=structured_data,
                key_points=key_points,
                characters_mentioned=characters,
                locations_mentioned=locations,
                items_mentioned=items,
                plot_elements=plot_elements,
                tone_indicators=tone_indicators,
                narrative_tension=narrative_tension,
                contains_character_voice=contains_character_voice,
                campaign_style=campaign_style,
                complexity_level=complexity_level
            )
            
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return self._create_fallback_context()

    def _extract_characters(self, text: str) -> List[Dict[str, Any]]:
        """Extract character information from text."""
        characters = []
        
        # Find potential character names
        names = self.extraction_patterns['character_names'].findall(text)
        
        for name in set(names):  # Remove duplicates
            character_info = {
                'name': name,
                'context_mentions': [],
                'personality_hints': [],
                'role_hints': []
            }
            
            # Find sentences mentioning this character
            sentences = text.split('.')
            for sentence in sentences:
                if name.lower() in sentence.lower():
                    character_info['context_mentions'].append(sentence.strip())
                    
                    # Extract personality hints
                    emotions = self.extraction_patterns['emotions'].findall(sentence)
                    character_info['personality_hints'].extend(emotions)
                    
                    # Extract role hints
                    if any(word in sentence.lower() for word in ['king', 'queen', 'lord', 'lady', 'captain']):
                        character_info['role_hints'].append('nobility')
                    elif any(word in sentence.lower() for word in ['wizard', 'mage', 'sorcerer', 'witch']):
                        character_info['role_hints'].append('spellcaster')
                    elif any(word in sentence.lower() for word in ['thief', 'rogue', 'assassin', 'spy']):
                        character_info['role_hints'].append('rogue')
            
            if character_info['context_mentions']:
                characters.append(character_info)
        
        return characters

    def _extract_locations(self, text: str) -> List[Dict[str, Any]]:
        """Extract location information from text."""
        locations = []
        
        # Find location mentions
        location_matches = self.extraction_patterns['locations'].findall(text)
        
        for location in set(location_matches):
            location_info = {
                'name': location,
                'type': 'unknown',
                'features': [],
                'atmosphere_hints': []
            }
            
            # Determine location type
            if any(word in location.lower() for word in ['castle', 'fortress', 'keep', 'tower']):
                location_info['type'] = 'stronghold'
            elif any(word in location.lower() for word in ['forest', 'woods', 'grove']):
                location_info['type'] = 'wilderness'
            elif any(word in location.lower() for word in ['city', 'town', 'village']):
                location_info['type'] = 'settlement'
            elif any(word in location.lower() for word in ['dungeon', 'cave', 'cavern', 'crypt']):
                location_info['type'] = 'underground'
            
            # Extract features and atmosphere
            sentences = text.split('.')
            for sentence in sentences:
                if location.lower() in sentence.lower():
                    if any(word in sentence.lower() for word in ['dark', 'gloomy', 'shadowy']):
                        location_info['atmosphere_hints'].append('dark')
                    elif any(word in sentence.lower() for word in ['bright', 'sunny', 'cheerful']):
                        location_info['atmosphere_hints'].append('bright')
                    elif any(word in sentence.lower() for word in ['ancient', 'old', 'ruined']):
                        location_info['features'].append('ancient')
                    elif any(word in sentence.lower() for word in ['magical', 'enchanted', 'mystical']):
                        location_info['features'].append('magical')
            
            locations.append(location_info)
        
        return locations

    def _extract_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract item information from text."""
        items = []
        
        # Find item mentions
        item_matches = self.extraction_patterns['items'].findall(text)
        
        for item in set(item_matches):
            item_info = {
                'name': item,
                'type': self._classify_item_type(item),
                'properties': [],
                'rarity_hints': []
            }
            
            # Extract properties from context
            sentences = text.split('.')
            for sentence in sentences:
                if item.lower() in sentence.lower():
                    if any(word in sentence.lower() for word in ['magical', 'enchanted', 'cursed']):
                        item_info['properties'].append('magical')
                    if any(word in sentence.lower() for word in ['rare', 'legendary', 'artifact']):
                        item_info['rarity_hints'].append('rare')
                    if any(word in sentence.lower() for word in ['powerful', 'mighty', 'strong']):
                        item_info['properties'].append('enhanced')
            
            items.append(item_info)
        
        return items

    def _classify_item_type(self, item: str) -> str:
        """Classify item type based on name."""
        item_lower = item.lower()
        if item_lower in ['sword', 'dagger', 'bow', 'staff']:
            return 'weapon'
        elif item_lower in ['shield', 'armor', 'cloak']:
            return 'armor'
        elif item_lower in ['potion', 'scroll', 'tome']:
            return 'consumable'
        elif item_lower in ['ring', 'amulet']:
            return 'accessory'
        return 'misc'

    def _extract_plot_elements(self, text: str) -> List[Dict[str, Any]]:
        """Extract plot elements from text."""
        plot_elements = []
        
        sentences = text.split('.')
        for sentence in sentences:
            element = {
                'content': sentence.strip(),
                'type': 'unknown',
                'importance': 0.5
            }
            
            # Classify plot element type
            if any(word in sentence.lower() for word in ['quest', 'mission', 'task']):
                element['type'] = 'quest'
                element['importance'] = 0.8
            elif any(word in sentence.lower() for word in ['secret', 'mystery', 'hidden']):
                element['type'] = 'mystery'
                element['importance'] = 0.7
            elif any(word in sentence.lower() for word in ['conflict', 'problem', 'trouble']):
                element['type'] = 'conflict'
                element['importance'] = 0.9
            elif any(word in sentence.lower() for word in ['backstory', 'history', 'past']):
                element['type'] = 'backstory'
                element['importance'] = 0.6
            
            if element['content'] and len(element['content']) > 10:
                plot_elements.append(element)
        
        return plot_elements

    def _analyze_tone(self, text: str) -> Dict[str, float]:
        """Analyze tone indicators in text."""
        tone_indicators = {
            'excitement': 0.0,
            'seriousness': 0.0,
            'humor': 0.0,
            'tension': 0.0,
            'mystery': 0.0,
            'heroic': 0.0
        }
        
        words = text.lower().split()
        total_words = len(words)
        
        if total_words == 0:
            return tone_indicators
        
        # Count tone indicators
        excitement_words = ['exciting', 'amazing', 'awesome', 'incredible', 'fantastic']
        serious_words = ['serious', 'grave', 'important', 'critical', 'dire']
        humor_words = ['funny', 'joke', 'laugh', 'amusing', 'silly', 'ridiculous']
        tension_words = ['tense', 'dangerous', 'scary', 'threatening', 'ominous']
        mystery_words = ['mysterious', 'strange', 'weird', 'puzzling', 'enigmatic']
        heroic_words = ['heroic', 'brave', 'courageous', 'noble', 'valiant']
        
        tone_indicators['excitement'] = sum(1 for word in words if word in excitement_words) / total_words
        tone_indicators['seriousness'] = sum(1 for word in words if word in serious_words) / total_words
        tone_indicators['humor'] = sum(1 for word in words if word in humor_words) / total_words
        tone_indicators['tension'] = sum(1 for word in words if word in tension_words) / total_words
        tone_indicators['mystery'] = sum(1 for word in words if word in mystery_words) / total_words
        tone_indicators['heroic'] = sum(1 for word in words if word in heroic_words) / total_words
        
        return tone_indicators

    def _calculate_narrative_tension(self, text: str) -> float:
        """Calculate narrative tension level."""
        words = text.lower().split()
        tension_score = 0.0
        
        for word in words:
            if word in self.narrative_tension_keywords:
                tension_score += self.narrative_tension_keywords[word]
        
        # Normalize by text length
        if len(words) > 0:
            tension_score /= len(words)
            tension_score *= 10  # Scale up for readability
        
        return min(1.0, tension_score)

    def _determine_campaign_style(self, text: str, context_history: List[str]) -> str:
        """Determine campaign style from text and history."""
        all_text = text + ' ' + ' '.join(context_history)
        words = all_text.lower().split()
        
        style_scores = {}
        for style, keywords in self.campaign_style_indicators.items():
            score = sum(1 for word in words if word in keywords)
            style_scores[style] = score
        
        if not style_scores or max(style_scores.values()) == 0:
            return 'general'
        
        return max(style_scores, key=style_scores.get)

    def _assess_complexity_level(self, text: str) -> str:
        """Assess complexity level of the described content."""
        # Count complex indicators
        complex_indicators = 0
        
        if self.extraction_patterns['dice_rolls'].search(text):
            complex_indicators += 1
        if self.extraction_patterns['stats'].search(text):
            complex_indicators += 1
        if len(self.extraction_patterns['character_names'].findall(text)) > 3:
            complex_indicators += 1
        if len(text.split()) > 200:
            complex_indicators += 1
        
        if complex_indicators >= 3:
            return 'expert'
        elif complex_indicators >= 2:
            return 'intermediate'
        else:
            return 'beginner'

    def _detect_character_voice(self, text: str) -> bool:
        """Detect if text contains character voice acting."""
        voice_indicators = [
            'says', 'shouts', 'whispers', 'growls', 'laughs',
            'in a', 'voice', 'accent', 'tone', 'speaking as'
        ]
        
        return any(indicator in text.lower() for indicator in voice_indicators)

    async def _generate_key_points(self, transcription: str, context_history: List[str]) -> List[str]:
        """Generate key points summary using AI if available."""
        try:
            if self.openai_client and len(transcription) > 50:
                # Use OpenAI to generate structured summary
                prompt = f"""
                Analyze this D&D setup discussion and extract the key points:
                
                Current: {transcription}
                History: {' '.join(context_history[-3:]) if context_history else 'None'}
                
                Extract 3-5 key points that are most important for game setup.
                Focus on actionable items, character details, plot elements, and world-building.
                """
                
                # Note: This would require proper OpenAI API setup
                # For now, fall back to manual extraction
                pass
        except:
            pass
        
        # Manual key point extraction
        sentences = transcription.split('.')
        important_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
                
            # Score sentence importance
            importance_score = 0
            if any(word in sentence.lower() for word in ['character', 'npc', 'player']):
                importance_score += 2
            if any(word in sentence.lower() for word in ['location', 'place', 'setting']):
                importance_score += 2
            if any(word in sentence.lower() for word in ['quest', 'mission', 'plot']):
                importance_score += 3
            if any(word in sentence.lower() for word in ['rule', 'mechanic', 'system']):
                importance_score += 1
            
            if importance_score >= 2:
                important_sentences.append((sentence, importance_score))
        
        # Sort by importance and return top points
        important_sentences.sort(key=lambda x: x[1], reverse=True)
        return [sentence for sentence, _ in important_sentences[:5]]

    def _extract_main_topics(self, text: str) -> List[str]:
        """Extract main topics from text."""
        topics = []
        
        if any(word in text.lower() for word in ['character', 'npc', 'player']):
            topics.append('characters')
        if any(word in text.lower() for word in ['location', 'place', 'setting', 'world']):
            topics.append('world_building')
        if any(word in text.lower() for word in ['quest', 'mission', 'adventure', 'story']):
            topics.append('plot')
        if any(word in text.lower() for word in ['combat', 'battle', 'fight', 'encounter']):
            topics.append('encounters')
        if any(word in text.lower() for word in ['rule', 'mechanic', 'system', 'dice']):
            topics.append('mechanics')
        
        return topics

    def _extract_game_mechanics(self, text: str) -> List[Dict[str, Any]]:
        """Extract game mechanics mentions."""
        mechanics = []
        
        # Find dice references
        dice_matches = self.extraction_patterns['dice_rolls'].findall(text)
        for dice in dice_matches:
            mechanics.append({'type': 'dice', 'value': dice, 'context': 'roll'})
        
        # Find stat references
        stat_matches = self.extraction_patterns['stats'].findall(text)
        for stat in stat_matches:
            mechanics.append({'type': 'ability_score', 'value': stat.upper(), 'context': 'character'})
        
        return mechanics

    def _extract_world_building_elements(self, text: str) -> List[Dict[str, Any]]:
        """Extract world-building elements."""
        elements = []
        
        # Extract cultural elements
        if any(word in text.lower() for word in ['culture', 'religion', 'language', 'custom']):
            elements.append({'type': 'culture', 'importance': 'medium'})
        
        # Extract geographical elements
        if any(word in text.lower() for word in ['mountain', 'river', 'forest', 'desert', 'ocean']):
            elements.append({'type': 'geography', 'importance': 'high'})
        
        # Extract political elements
        if any(word in text.lower() for word in ['kingdom', 'empire', 'government', 'politics']):
            elements.append({'type': 'politics', 'importance': 'medium'})
        
        return elements

    def _extract_story_hooks(self, text: str) -> List[str]:
        """Extract potential story hooks."""
        hooks = []
        sentences = text.split('.')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if any(word in sentence.lower() for word in ['mysterious', 'strange', 'missing', 'lost', 'secret']):
                hooks.append(sentence)
            elif any(word in sentence.lower() for word in ['threat', 'danger', 'enemy', 'villain']):
                hooks.append(sentence)
            elif any(word in sentence.lower() for word in ['treasure', 'artifact', 'reward', 'prize']):
                hooks.append(sentence)
        
        return hooks[:3]  # Return top 3 hooks

    def _create_fallback_context(self) -> ExtractedContext:
        """Create fallback context when extraction fails."""
        return ExtractedContext(
            structured_data={},
            key_points=[],
            characters_mentioned=[],
            locations_mentioned=[],
            items_mentioned=[],
            plot_elements=[],
            tone_indicators={},
            narrative_tension=0.0,
            contains_character_voice=False,
            campaign_style='general',
            complexity_level='beginner'
        )

    async def extract_npcs_from_context(self, context: Dict[str, Any]) -> List[NPCData]:
        """Extract NPC data from context."""
        npcs = []
        
        for char in context.get('characters_mentioned', []):
            npc = NPCData(
                name=char['name'],
                description=f"Character mentioned in setup: {' '.join(char['context_mentions'][:2])}",
                personality_traits=char.get('personality_hints', []),
                role=char['role_hints'][0] if char.get('role_hints') else 'unknown',
                relationships=[],
                voice_notes=None
            )
            npcs.append(npc)
        
        return npcs

    async def extract_locations_from_context(self, context: Dict[str, Any]) -> List[LocationData]:
        """Extract location data from context."""
        locations = []
        
        for loc in context.get('locations_mentioned', []):
            location = LocationData(
                name=loc['name'],
                description=f"{loc['type'].title()} location",
                type=loc['type'],
                features=loc.get('features', []),
                connections=[],
                atmosphere=loc['atmosphere_hints'][0] if loc.get('atmosphere_hints') else 'neutral'
            )
            locations.append(location)
        
        return locations

    async def extract_items_from_context(self, context: Dict[str, Any]) -> List[ItemData]:
        """Extract item data from context."""
        items = []
        
        for item in context.get('items_mentioned', []):
            item_data = ItemData(
                name=item['name'],
                description=f"{item['type'].title()} item",
                type=item['type'],
                properties=item.get('properties', []),
                value='unknown',
                rarity=item['rarity_hints'][0] if item.get('rarity_hints') else 'common'
            )
            items.append(item_data)
        
        return items

    async def generate_encounters_from_tension(self, context: Dict[str, Any]) -> List[EncounterData]:
        """Generate encounters based on narrative tension."""
        encounters = []
        
        tension_level = context.get('narrative_tension', 0.0)
        
        if tension_level > 0.7:
            encounters.append(EncounterData(
                name="High-Stakes Confrontation",
                type="combat",
                difficulty="hard",
                participants=["Unknown enemies"],
                location="To be determined",
                narrative_purpose="Resolve high tension"
            ))
        elif tension_level > 0.4:
            encounters.append(EncounterData(
                name="Challenging Obstacle",
                type="skill_challenge",
                difficulty="medium",
                participants=["Environmental hazards"],
                location="Current area",
                narrative_purpose="Build tension"
            ))
        else:
            encounters.append(EncounterData(
                name="Social Interaction",
                type="roleplay",
                difficulty="easy",
                participants=["Local NPCs"],
                location="Settlement",
                narrative_purpose="Character development"
            ))
        
        return encounters