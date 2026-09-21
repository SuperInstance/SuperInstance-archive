"""
Advanced Voice-Guided Character Creation
Natural language processing for intuitive character building
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import sqlite3
from dataclasses import dataclass
import random

logger = logging.getLogger(__name__)

@dataclass
class VoiceCommand:
    text: str
    intent: str
    entities: Dict[str, Any]
    confidence: float
    timestamp: datetime

class VoiceCharacterGuide:
    """Advanced voice-guided character creation system"""
    
    def __init__(self):
        self.sessions = {}  # In-memory session storage
        
        # Intent patterns for natural language understanding
        self.intent_patterns = {
            'create_character': [
                r'create.*(character|hero|pc)',
                r'make.*(character|hero|pc)',
                r'build.*(character|hero|pc)',
                r'new (character|hero|pc)'
            ],
            'choose_race': [
                r'(i want|i\'d like|make).*(elf|dwarf|human|halfling|dragonborn|gnome|half-elf|half-orc|tiefling)',
                r'(race|ancestry).*(elf|dwarf|human|halfling|dragonborn|gnome|half-elf|half-orc|tiefling)',
                r'(elf|dwarf|human|halfling|dragonborn|gnome|half-elf|half-orc|tiefling).*(race|character)'
            ],
            'choose_class': [
                r'(i want|i\'d like|make).*(fighter|wizard|rogue|cleric|ranger|barbarian|bard|druid|monk|paladin|sorcerer|warlock)',
                r'(class).*(fighter|wizard|rogue|cleric|ranger|barbarian|bard|druid|monk|paladin|sorcerer|warlock)',
                r'(fighter|wizard|rogue|cleric|ranger|barbarian|bard|druid|monk|paladin|sorcerer|warlock).*(class|character)'
            ],
            'character_concept': [
                r'(tank|damage dealer|healer|support|utility|scout|face|controller)',
                r'(tanky|tough|strong|smart|wise|charismatic|sneaky|magical)',
                r'(front.?line|back.?line|melee|ranged|spellcaster|warrior|mage)'
            ],
            'ability_preference': [
                r'(high|good|strong).*(strength|dexterity|constitution|intelligence|wisdom|charisma)',
                r'(strength|dexterity|constitution|intelligence|wisdom|charisma).*(focused|based|build)',
                r'(str|dex|con|int|wis|cha).*(high|good|strong|focused)'
            ],
            'roleplay_concept': [
                r'(noble|criminal|folk hero|acolyte|entertainer|guild artisan|hermit|outlander|sage|soldier)',
                r'(backstory|background|history)',
                r'(personality|trait|ideal|bond|flaw)'
            ],
            'optimization_request': [
                r'(optimize|best|optimal|min.?max|power.?game)',
                r'(strongest|most effective|highest damage)',
                r'(build guide|optimization|advice|suggestions)'
            ],
            'random_request': [
                r'(random|surprise me|don\'t care|whatever|anything)',
                r'(roll|generate|make something)',
                r'(quick|fast|simple) (character|build)'
            ]
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            'race': r'(elf|dwarf|human|halfling|dragonborn|gnome|half-elf|half-orc|tiefling)',
            'class': r'(fighter|wizard|rogue|cleric|ranger|barbarian|bard|druid|monk|paladin|sorcerer|warlock)',
            'ability': r'(strength|dexterity|constitution|intelligence|wisdom|charisma|str|dex|con|int|wis|cha)',
            'background': r'(noble|criminal|folk hero|acolyte|entertainer|guild artisan|hermit|outlander|sage|soldier)',
            'alignment': r'(lawful good|neutral good|chaotic good|lawful neutral|true neutral|chaotic neutral|lawful evil|neutral evil|chaotic evil)',
            'level': r'level\s*(\d+)|(\d+)(?:st|nd|rd|th)?\s*level',
            'build_type': r'(tank|damage|healer|support|utility|scout|face|controller|dps|crowd control)'
        }
        
        # Character concept templates
        self.concept_templates = {
            'tank': {
                'description': 'A sturdy frontline fighter who protects the party',
                'suggested_races': ['dwarf', 'dragonborn', 'half-orc'],
                'suggested_classes': ['fighter', 'paladin', 'barbarian'],
                'key_abilities': ['strength', 'constitution'],
                'backgrounds': ['soldier', 'folk hero', 'noble']
            },
            'damage': {
                'description': 'A specialized damage dealer who eliminates threats',
                'suggested_races': ['elf', 'human', 'half-elf'],
                'suggested_classes': ['fighter', 'ranger', 'rogue', 'wizard'],
                'key_abilities': ['strength', 'dexterity', 'intelligence'],
                'backgrounds': ['outlander', 'criminal', 'soldier']
            },
            'healer': {
                'description': 'A supportive character who keeps the party alive',
                'suggested_races': ['human', 'elf', 'halfling'],
                'suggested_classes': ['cleric', 'druid', 'bard'],
                'key_abilities': ['wisdom', 'charisma'],
                'backgrounds': ['acolyte', 'hermit', 'folk hero']
            },
            'utility': {
                'description': 'A versatile problem-solver with many skills',
                'suggested_races': ['human', 'half-elf', 'gnome'],
                'suggested_classes': ['rogue', 'bard', 'ranger', 'wizard'],
                'key_abilities': ['dexterity', 'intelligence', 'charisma'],
                'backgrounds': ['criminal', 'guild artisan', 'entertainer']
            }
        }
        
        # Conversation flow states
        self.flow_states = [
            'welcome',
            'concept_discovery',
            'race_selection', 
            'class_selection',
            'ability_scores',
            'background_selection',
            'details_and_finalization'
        ]
        
    def start_session(self, session_id: str, player_preferences: Dict[str, Any] = None, 
                     campaign_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Initialize a new voice-guided character creation session"""
        
        session_data = {
            'session_id': session_id,
            'state': 'welcome',
            'character_data': {},
            'conversation_history': [],
            'player_preferences': player_preferences or {},
            'campaign_info': campaign_info or {},
            'suggested_concepts': [],
            'confidence_scores': {},
            'created_at': datetime.now()
        }
        
        self.sessions[session_id] = session_data
        
        # Generate welcome message and initial suggestions
        welcome_message = self._generate_welcome_message(player_preferences, campaign_info)
        initial_suggestions = self._generate_initial_suggestions(campaign_info)
        
        return {
            'welcome': welcome_message,
            'initial_suggestions': initial_suggestions,
            'state': 'welcome'
        }
    
    def process_command(self, session_id: str, text_input: str) -> Dict[str, Any]:
        """Process natural language input and provide intelligent response"""
        
        if session_id not in self.sessions:
            return {'error': 'Session not found'}
        
        session = self.sessions[session_id]
        
        # Analyze the input
        command = self._analyze_input(text_input)
        session['conversation_history'].append(command)
        
        # Process based on current state and intent
        response = self._generate_response(session, command)
        
        # Update session state
        if 'new_state' in response:
            session['state'] = response['new_state']
        
        # Update character data
        if 'character_updates' in response:
            session['character_data'].update(response['character_updates'])
        
        return response
    
    def _analyze_input(self, text: str) -> VoiceCommand:
        """Analyze natural language input to extract intent and entities"""
        text_lower = text.lower()
        
        # Determine intent
        detected_intent = 'unknown'
        max_confidence = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    confidence = len(match.group(0)) / len(text_lower)  # Simple confidence metric
                    if confidence > max_confidence:
                        max_confidence = confidence
                        detected_intent = intent
        
        # Extract entities
        entities = {}
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text_lower)
            if matches:
                if entity_type == 'level':
                    # Special handling for level numbers
                    level_nums = [int(m) for match_group in matches for m in match_group if m.isdigit()]
                    if level_nums:
                        entities[entity_type] = level_nums[0]
                else:
                    entities[entity_type] = matches[0] if isinstance(matches[0], str) else matches[0][0]
        
        return VoiceCommand(
            text=text,
            intent=detected_intent,
            entities=entities,
            confidence=max_confidence,
            timestamp=datetime.now()
        )
    
    def _generate_response(self, session: Dict[str, Any], command: VoiceCommand) -> Dict[str, Any]:
        """Generate contextual response based on session state and command"""
        
        current_state = session['state']
        intent = command.intent
        entities = command.entities
        
        response = {
            'message': '',
            'actions': [],
            'character_updates': {},
            'next_question': None,
            'confidence': command.confidence
        }
        
        # Handle based on current conversation state
        if current_state == 'welcome':
            return self._handle_welcome_state(session, command, response)
        
        elif current_state == 'concept_discovery':
            return self._handle_concept_discovery(session, command, response)
        
        elif current_state == 'race_selection':
            return self._handle_race_selection(session, command, response)
        
        elif current_state == 'class_selection':
            return self._handle_class_selection(session, command, response)
        
        elif current_state == 'ability_scores':
            return self._handle_ability_scores(session, command, response)
        
        elif current_state == 'background_selection':
            return self._handle_background_selection(session, command, response)
        
        else:
            response['message'] = "I'm not sure what you'd like to do next. Could you be more specific?"
        
        return response
    
    def _handle_welcome_state(self, session: Dict[str, Any], command: VoiceCommand, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the welcome/initial state"""
        
        if command.intent == 'character_concept':
            concept_type = self._infer_concept_type(command.text)
            if concept_type:
                response['message'] = f"Great! I understand you want to create a {concept_type} character. {self.concept_templates[concept_type]['description']}"
                response['character_updates'] = {'concept_type': concept_type}
                response['new_state'] = 'race_selection'
                response['next_question'] = f"For a {concept_type}, I'd recommend these races: {', '.join(self.concept_templates[concept_type]['suggested_races'])}. Which appeals to you?"
            else:
                response['new_state'] = 'concept_discovery'
                response['message'] = "I'd love to help you create a character! Could you tell me what kind of character you have in mind?"
        
        elif command.intent == 'choose_race' and 'race' in command.entities:
            race = command.entities['race']
            response['message'] = f"Excellent choice! {race.title()} is a great race. Now, what class interests you?"
            response['character_updates'] = {'race': race}
            response['new_state'] = 'class_selection'
            response['actions'] = [f'suggest_classes_for_race:{race}']
        
        elif command.intent == 'choose_class' and 'class' in command.entities:
            char_class = command.entities['class']
            response['message'] = f"A {char_class} is an awesome choice! What race were you thinking?"
            response['character_updates'] = {'class': char_class}
            response['new_state'] = 'race_selection'
            response['actions'] = [f'suggest_races_for_class:{char_class}']
        
        elif command.intent == 'random_request':
            response['message'] = "I'll create something fun for you! Let me generate a random character concept..."
            response['actions'] = ['generate_random_concept']
            response['new_state'] = 'concept_discovery'
        
        else:
            response['message'] = "Welcome to the advanced character builder! I can help you create an optimized D&D character. What kind of character do you want to play?"
            response['new_state'] = 'concept_discovery'
        
        return response
    
    def _handle_concept_discovery(self, session: Dict[str, Any], command: VoiceCommand, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle concept discovery phase"""
        
        concept_type = self._infer_concept_type(command.text)
        
        if concept_type:
            template = self.concept_templates[concept_type]
            response['message'] = f"Perfect! A {concept_type} character - {template['description']}. "
            response['message'] += f"I recommend these races: {', '.join(template['suggested_races'][:3])}. Which sounds good?"
            
            response['character_updates'] = {
                'concept_type': concept_type,
                'suggested_races': template['suggested_races'],
                'suggested_classes': template['suggested_classes']
            }
            response['new_state'] = 'race_selection'
        
        elif 'race' in command.entities:
            race = command.entities['race']
            response['message'] = f"I see you're interested in playing a {race}. What role do you want to fill in the party?"
            response['character_updates'] = {'race': race}
            response['actions'] = [f'suggest_concepts_for_race:{race}']
        
        elif 'class' in command.entities:
            char_class = command.entities['class']
            response['message'] = f"A {char_class} is a great choice! What's your character concept or role?"
            response['character_updates'] = {'class': char_class}
            response['actions'] = [f'suggest_concepts_for_class:{char_class}']
        
        else:
            response['message'] = "I'm trying to understand your character concept. Are you thinking more of a tank, damage dealer, healer, or utility character?"
            response['actions'] = ['provide_concept_examples']
        
        return response
    
    def _handle_race_selection(self, session: Dict[str, Any], command: VoiceCommand, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle race selection phase"""
        
        if 'race' in command.entities:
            race = command.entities['race']
            current_class = session['character_data'].get('class')
            
            response['character_updates'] = {'race': race}
            response['message'] = f"Excellent! {race.title()} selected. "
            
            if current_class:
                response['message'] += f"A {race} {current_class} is a solid combination! "
                response['new_state'] = 'ability_scores'
                response['next_question'] = "Now let's talk about your ability scores. Do you want to optimize for combat, or do you prefer a more balanced approach?"
            else:
                response['message'] += "Now, what class appeals to you?"
                response['new_state'] = 'class_selection'
                
                # Suggest optimal classes for this race
                concept_type = session['character_data'].get('concept_type')
                if concept_type and concept_type in self.concept_templates:
                    suggested_classes = self.concept_templates[concept_type]['suggested_classes']
                    response['actions'] = [f'suggest_classes:{",".join(suggested_classes)}']
        
        else:
            response['message'] = "Which race would you like? I can recommend some based on your character concept if you'd like."
            if 'concept_type' in session['character_data']:
                concept = session['character_data']['concept_type']
                races = self.concept_templates[concept]['suggested_races']
                response['message'] += f" For a {concept}, I suggest: {', '.join(races)}."
        
        return response
    
    def _handle_class_selection(self, session: Dict[str, Any], command: VoiceCommand, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle class selection phase"""
        
        if 'class' in command.entities:
            char_class = command.entities['class']
            current_race = session['character_data'].get('race')
            
            response['character_updates'] = {'class': char_class}
            response['message'] = f"Perfect! {char_class.title()} is a fantastic class. "
            
            if current_race:
                # Analyze race-class synergy
                response['message'] += f"The {current_race}-{char_class} combination has good synergy! "
                response['new_state'] = 'ability_scores'
                response['next_question'] = "Let's optimize your ability scores. Are you going for maximum effectiveness or a more roleplay-focused build?"
            else:
                response['message'] += "What race were you considering?"
                response['new_state'] = 'race_selection'
        
        else:
            response['message'] = "What class interests you? "
            concept_type = session['character_data'].get('concept_type')
            if concept_type:
                classes = self.concept_templates[concept_type]['suggested_classes']
                response['message'] += f"For a {concept_type}, I recommend: {', '.join(classes)}."
        
        return response
    
    def _handle_ability_scores(self, session: Dict[str, Any], command: VoiceCommand, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ability score optimization"""
        
        char_class = session['character_data'].get('class')
        race = session['character_data'].get('race')
        
        if command.intent == 'optimization_request':
            response['message'] = "Great! I'll optimize your ability scores for maximum effectiveness. "
            response['actions'] = [f'optimize_abilities:{char_class}:{race}']
            response['new_state'] = 'background_selection'
            response['next_question'] = "Now let's choose a background that fits your character's story."
        
        elif 'ability' in command.entities:
            ability = command.entities['ability']
            response['message'] = f"Focusing on {ability} - that's a good choice for your build! "
            response['character_updates'] = {'primary_ability': ability}
            response['actions'] = [f'prioritize_ability:{ability}']
        
        elif command.intent == 'random_request':
            response['message'] = "I'll use the standard array and apply racial bonuses optimally. "
            response['actions'] = [f'apply_standard_array:{char_class}:{race}']
            response['new_state'] = 'background_selection'
        
        else:
            response['message'] = "For ability scores, I can use point buy for optimization, standard array for simplicity, or we can roll for randomness. What would you prefer?"
            response['actions'] = ['explain_ability_methods']
        
        return response
    
    def _handle_background_selection(self, session: Dict[str, Any], command: VoiceCommand, response: Dict[str, Any]) -> Dict[str, Any]:
        """Handle background selection"""
        
        if 'background' in command.entities:
            background = command.entities['background']
            response['character_updates'] = {'background': background}
            response['message'] = f"Excellent choice! {background.title()} adds great flavor to your character. "
            response['new_state'] = 'details_and_finalization'
            response['next_question'] = "Your character is almost ready! Would you like me to generate a backstory, or do you have specific personality traits in mind?"
        
        else:
            concept_type = session['character_data'].get('concept_type')
            if concept_type:
                backgrounds = self.concept_templates[concept_type]['backgrounds']
                response['message'] = f"For your {concept_type} character, I suggest these backgrounds: {', '.join(backgrounds)}. Which fits your character's story?"
            else:
                response['message'] = "What background fits your character's story? Popular choices include Noble, Criminal, Folk Hero, Acolyte, and Entertainer."
        
        return response
    
    def _infer_concept_type(self, text: str) -> Optional[str]:
        """Infer character concept type from natural language"""
        text_lower = text.lower()
        
        concept_keywords = {
            'tank': ['tank', 'tanky', 'tough', 'front', 'protect', 'defense', 'shield', 'armor', 'guardian'],
            'damage': ['damage', 'dps', 'kill', 'destroy', 'attack', 'weapon', 'fight', 'warrior', 'striker'],
            'healer': ['heal', 'support', 'help', 'cure', 'medicine', 'cleric', 'life', 'divine'],
            'utility': ['utility', 'skill', 'versatile', 'problem', 'solve', 'sneak', 'scout', 'investigate']
        }
        
        concept_scores = {}
        
        for concept, keywords in concept_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                concept_scores[concept] = score
        
        if concept_scores:
            return max(concept_scores, key=concept_scores.get)
        
        return None
    
    def _generate_welcome_message(self, player_preferences: Dict[str, Any], 
                                campaign_info: Dict[str, Any]) -> str:
        """Generate personalized welcome message"""
        
        base_message = "Welcome to the Advanced Character Builder! I'm your AI guide, and I'll help you create an optimized D&D character using voice commands and natural conversation."
        
        if campaign_info:
            if 'theme' in campaign_info:
                base_message += f" I see you're joining a {campaign_info['theme']} campaign - I'll keep that in mind for suggestions."
            
            if 'level' in campaign_info:
                base_message += f" Starting at level {campaign_info['level']} gives us some great options!"
        
        if player_preferences:
            if 'experience_level' in player_preferences:
                exp_level = player_preferences['experience_level']
                if exp_level == 'beginner':
                    base_message += " Since you're new to D&D, I'll explain things as we go and suggest beginner-friendly options."
                elif exp_level == 'expert':
                    base_message += " I can see you're experienced, so I'll focus on optimization and advanced techniques."
        
        base_message += " Just tell me what kind of character you want to play, and we'll build it together!"
        
        return base_message
    
    def _generate_initial_suggestions(self, campaign_info: Dict[str, Any]) -> List[str]:
        """Generate initial character concept suggestions"""
        
        suggestions = [
            "A sturdy tank to protect the party",
            "A damage-focused character to eliminate threats", 
            "A supportive healer to keep everyone alive",
            "A versatile utility character with lots of skills"
        ]
        
        # Customize based on campaign info
        if campaign_info:
            if campaign_info.get('theme') == 'intrigue':
                suggestions.insert(0, "A charismatic face character for social encounters")
            elif campaign_info.get('theme') == 'dungeon_crawl':
                suggestions.insert(0, "A well-rounded explorer for dungeon delving")
            elif campaign_info.get('theme') == 'wilderness':
                suggestions.insert(0, "A ranger or druid for wilderness survival")
        
        return suggestions[:4]  # Return top 4 suggestions
    
    def speech_to_text(self, audio_data: str) -> str:
        """Convert speech to text (placeholder implementation)"""
        # In a real implementation, this would use a speech recognition service
        # like Google Speech-to-Text, Azure Speech, or a local solution
        
        # For demo purposes, return a placeholder
        return "I want to create a tough fighter character"
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data for a given session ID"""
        return self.sessions.get(session_id)
    
    def apply_session_preferences(self, character_data: Dict[str, Any], 
                                session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply session preferences to generated character"""
        
        if not session_data:
            return character_data
        
        preferences = session_data.get('player_preferences', {})
        
        # Apply complexity preferences
        if preferences.get('complexity') == 'simple':
            # Simplify character for new players
            character_data['complexity_notes'] = 'Simplified for new players'
        
        # Apply campaign-specific modifications
        campaign_info = session_data.get('campaign_info', {})
        if campaign_info.get('theme'):
            character_data['campaign_theme'] = campaign_info['theme']
        
        return character_data