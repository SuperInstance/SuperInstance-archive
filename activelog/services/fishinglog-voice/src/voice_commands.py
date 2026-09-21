"""
Voice Command Processing System
Natural language processing for marine navigation commands
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple
try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    NLTK_AVAILABLE = True
except (ImportError, LookupError) as e:
    logger.warning(f"NLTK not available: {e}")
    NLTK_AVAILABLE = False
    def word_tokenize(text):
        return text.lower().split()
    class WordNetLemmatizer:
        def lemmatize(self, word, pos='n'):
            return word
# import spacy

logger = logging.getLogger(__name__)

class VoiceCommandProcessor:
    """
    Advanced voice command processor for marine navigation
    Handles natural language understanding and command parsing
    """
    
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        if NLTK_AVAILABLE:
            try:
                self.stop_words = set(stopwords.words('english'))
            except LookupError:
                self.stop_words = set(['a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'will', 'with'])
        else:
            self.stop_words = set(['a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'will', 'with'])
        self.nlp = None
        
        # Marine navigation command patterns
        self.command_patterns = {
            'chart_control': {
                'zoom_in': [
                    r'zoom in', r'magnify', r'closer', r'increase scale',
                    r'zoom to (\d+)', r'scale to (\d+)'
                ],
                'zoom_out': [
                    r'zoom out', r'reduce scale', r'wider view', r'pull back',
                    r'decrease zoom'
                ],
                'pan': [
                    r'pan (north|south|east|west)', r'move (up|down|left|right)',
                    r'center on (.*)', r'go to (.*)', r'navigate to (.*)'
                ],
                'show_layer': [
                    r'show (.*) layer', r'display (.*)s?', r'turn on (.*)',
                    r'enable (.*) overlay'
                ],
                'hide_layer': [
                    r'hide (.*) layer', r'turn off (.*)', r'disable (.*)',
                    r'remove (.*) overlay'
                ]
            },
            'autopilot': {
                'engage': [
                    r'engage autopilot', r'turn on autopilot', r'activate autopilot',
                    r'autopilot on', r'start autopilot'
                ],
                'disengage': [
                    r'disengage autopilot', r'turn off autopilot', r'deactivate autopilot',
                    r'autopilot off', r'stop autopilot', r'manual control'
                ],
                'set_heading': [
                    r'set heading (\d+)', r'heading (\d+)', r'turn to (\d+)',
                    r'course (\d+)', r'steer (\d+) degrees?'
                ],
                'adjust_heading': [
                    r'turn (\d+) degrees? (left|right|port|starboard)',
                    r'adjust heading (left|right|port|starboard) (\d+)',
                    r'come (left|right|port|starboard) (\d+)'
                ]
            },
            'follow_vessel': {
                'engage': [
                    r'follow (vessel|ship|boat) (.+)', r'track (vessel|ship|boat) (.+)',
                    r'follow target (.+)', r'engage follow mode'
                ],
                'disengage': [
                    r'stop following', r'end follow mode', r'disengage follow',
                    r'cancel follow'
                ],
                'set_distance': [
                    r'follow at (\d+\.?\d*) (nautical miles?|nm|miles?)',
                    r'maintain (\d+\.?\d*) (nautical miles?|nm|miles?) distance',
                    r'keep (\d+\.?\d*) (nautical miles?|nm|miles?) behind'
                ]
            },
            'navigation': {
                'mark_waypoint': [
                    r'mark waypoint', r'add waypoint', r'set waypoint',
                    r'waypoint here', r'mark position'
                ],
                'goto_waypoint': [
                    r'go to waypoint (.+)', r'navigate to waypoint (.+)',
                    r'set course to (.+)'
                ],
                'mob': [
                    r'man overboard', r'mob', r'emergency mark',
                    r'mark mob', r'person overboard'
                ]
            },
            'log_entry': {
                'create_entry': [
                    r'log entry (.+)', r'add to log (.+)', r'create log (.+)',
                    r'record (.+)', r'note (.+)'
                ],
                'weather_log': [
                    r'log weather (.+)', r'weather entry (.+)',
                    r'record weather (.+)'
                ],
                'position_log': [
                    r'log position', r'record position', r'position entry'
                ]
            },
            'system_control': {
                'voice_control': [
                    r'voice (on|off|enable|disable)', r'listening (on|off)',
                    r'(start|stop) listening'
                ],
                'language': [
                    r'set language (.*)', r'change language to (.*)',
                    r'speak in (.*)' 
                ]
            }
        }
        
        # Command synonyms for better recognition
        self.synonyms = {
            'north': ['up', 'forward', 'ahead'],
            'south': ['down', 'back', 'astern'],
            'east': ['right', 'starboard'],
            'west': ['left', 'port'],
            'vessel': ['ship', 'boat', 'target'],
            'waypoint': ['mark', 'point', 'position'],
            'autopilot': ['auto pilot', 'auto-pilot']
        }
        
        # Critical commands that require confirmation
        self.critical_commands = {
            'autopilot_engage', 'autopilot_disengage', 'follow_vessel_engage',
            'navigation_mob', 'emergency_commands'
        }
        
        self._initialize_nlp()
        logger.info("Voice Command Processor initialized")
    
    def _initialize_nlp(self):
        """Initialize NLP components"""
        try:
            # Download required NLTK data
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt')
            
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords')
                
            try:
                nltk.data.find('corpora/wordnet')
            except LookupError:
                nltk.download('wordnet')
            
            # Disable spaCy for now
            self.nlp = None
            
            logger.info("NLP components initialized")
            
        except Exception as e:
            logger.error(f"NLP initialization error: {e}")
    
    def parse_command(self, command_text: str) -> Optional[Dict[str, Any]]:
        """Parse voice command into structured format"""
        if not command_text:
            return None
        
        try:
            # Preprocess the command
            processed_text = self._preprocess_command(command_text)
            
            # Try to match command patterns
            command = self._match_patterns(processed_text)
            
            if command:
                # Enhance command with NLP analysis
                enhanced_command = self._enhance_with_nlp(command, processed_text)
                
                # Add metadata
                enhanced_command['original_text'] = command_text
                enhanced_command['processed_text'] = processed_text
                enhanced_command['confidence'] = self._calculate_confidence(command, processed_text)
                enhanced_command['requires_confirmation'] = self._requires_confirmation(enhanced_command)
                
                return enhanced_command
            
            # If no pattern match, try NLP-based parsing
            return self._nlp_fallback_parse(processed_text, command_text)
            
        except Exception as e:
            logger.error(f"Command parsing error: {e}")
            return None
    
    def _preprocess_command(self, command_text: str) -> str:
        """Preprocess command text for better recognition"""
        # Convert to lowercase
        text = command_text.lower().strip()
        
        # Handle common marine abbreviations
        abbreviations = {
            'nm': 'nautical miles',
            'kts': 'knots',
            'hdg': 'heading',
            'pos': 'position',
            'wp': 'waypoint',
            'mob': 'man overboard'
        }
        
        for abbr, full in abbreviations.items():
            text = re.sub(r'\b' + abbr + r'\b', full, text)
        
        # Handle numbers
        text = re.sub(r'(\d+)\s*degrees?', r'\1 degrees', text)
        text = re.sub(r'(\d+)\s*nm\b', r'\1 nautical miles', text)
        
        # Apply synonyms
        for word, synonyms in self.synonyms.items():
            for synonym in synonyms:
                text = re.sub(r'\b' + synonym + r'\b', word, text)
        
        return text
    
    def _match_patterns(self, command_text: str) -> Optional[Dict[str, Any]]:
        """Match command against predefined patterns"""
        for category, commands in self.command_patterns.items():
            for command_type, patterns in commands.items():
                for pattern in patterns:
                    match = re.search(pattern, command_text, re.IGNORECASE)
                    if match:
                        command = {
                            'type': category,
                            'action': command_type,
                            'params': {},
                            'groups': match.groups()
                        }
                        
                        # Extract parameters based on command type
                        command['params'] = self._extract_parameters(
                            category, command_type, match, command_text
                        )
                        
                        return command
        
        return None
    
    def _extract_parameters(self, category: str, action: str, match: re.Match, 
                          command_text: str) -> Dict[str, Any]:
        """Extract parameters from matched command"""
        params = {}
        groups = match.groups()
        
        try:
            if category == 'chart_control':
                if action in ['zoom_in', 'zoom_out'] and groups:
                    if groups[0].isdigit():
                        params['level'] = int(groups[0])
                
                elif action == 'pan' and groups:
                    params['direction'] = groups[0]
                
                elif action in ['show_layer', 'hide_layer'] and groups:
                    params['layer'] = groups[0]
            
            elif category == 'autopilot':
                if action == 'set_heading' and groups:
                    if groups[0].isdigit():
                        params['heading'] = int(groups[0])
                
                elif action == 'adjust_heading' and len(groups) >= 2:
                    direction = groups[0] if groups[0] else groups[1]
                    degrees = groups[1] if groups[0] else groups[0]
                    
                    if degrees and degrees.isdigit():
                        params['direction'] = direction
                        params['degrees'] = int(degrees)
            
            elif category == 'follow_vessel':
                if action == 'engage' and groups:
                    params['target'] = groups[1] if len(groups) > 1 else groups[0]
                
                elif action == 'set_distance' and len(groups) >= 2:
                    distance_str = groups[0]
                    unit = groups[1]
                    
                    try:
                        distance = float(distance_str)
                        params['distance'] = distance
                        params['unit'] = unit
                    except ValueError:
                        pass
            
            elif category == 'navigation':
                if action == 'goto_waypoint' and groups:
                    params['waypoint'] = groups[0]
            
            elif category == 'log_entry':
                if groups and groups[0]:
                    params['content'] = groups[0]
            
            elif category == 'system_control':
                if action == 'voice_control' and groups:
                    params['state'] = groups[0]
                elif action == 'language' and groups:
                    params['language'] = groups[0]
        
        except Exception as e:
            logger.debug(f"Parameter extraction error: {e}")
        
        return params
    
    def _enhance_with_nlp(self, command: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Enhance command with NLP analysis"""
        if not self.nlp:
            return command
        
        try:
            doc = self.nlp(text)
            
            # Extract named entities
            entities = []
            for ent in doc.ents:
                entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'description': spacy.explain(ent.label_)
                })
            
            if entities:
                command['entities'] = entities
            
            # Extract numbers and measurements
            numbers = []
            for token in doc:
                if token.like_num:
                    numbers.append({
                        'text': token.text,
                        'value': token.text
                    })
            
            if numbers:
                command['numbers'] = numbers
            
            # Determine intent confidence based on linguistic features
            command['linguistic_features'] = {
                'has_numbers': len(numbers) > 0,
                'has_entities': len(entities) > 0,
                'sentence_length': len(doc),
                'verb_count': len([token for token in doc if token.pos_ == 'VERB'])
            }
            
        except Exception as e:
            logger.debug(f"NLP enhancement error: {e}")
        
        return command
    
    def _nlp_fallback_parse(self, processed_text: str, original_text: str) -> Optional[Dict[str, Any]]:
        """Fallback parsing using NLP when patterns don't match"""
        if not self.nlp:
            return None
        
        try:
            doc = self.nlp(processed_text)
            
            # Look for key maritime verbs and nouns
            maritime_verbs = ['navigate', 'steer', 'follow', 'mark', 'set', 'engage', 'turn']
            maritime_nouns = ['course', 'heading', 'vessel', 'autopilot', 'waypoint']
            
            found_verbs = []
            found_nouns = []
            
            for token in doc:
                if token.lemma_ in maritime_verbs:
                    found_verbs.append(token.lemma_)
                elif token.lemma_ in maritime_nouns:
                    found_nouns.append(token.lemma_)
            
            # Attempt to construct command from linguistic analysis
            if found_verbs and found_nouns:
                command = {
                    'type': 'interpreted_command',
                    'action': found_verbs[0],
                    'params': {
                        'target': found_nouns[0] if found_nouns else None,
                        'verbs': found_verbs,
                        'nouns': found_nouns
                    },
                    'original_text': original_text,
                    'processed_text': processed_text,
                    'confidence': 0.3,  # Lower confidence for interpreted commands
                    'requires_confirmation': True  # Always confirm interpreted commands
                }
                
                return command
        
        except Exception as e:
            logger.debug(f"NLP fallback error: {e}")
        
        return None
    
    def _calculate_confidence(self, command: Dict[str, Any], text: str) -> float:
        """Calculate confidence score for parsed command"""
        confidence = 0.8  # Base confidence for pattern matches
        
        # Adjust based on command complexity
        if command.get('params'):
            confidence += 0.1
        
        # Adjust based on text length and clarity
        if len(text.split()) <= 5:
            confidence += 0.1  # Short, clear commands
        elif len(text.split()) > 10:
            confidence -= 0.1  # Longer commands might be less accurate
        
        # Adjust based on numbers and entities
        if command.get('numbers') or command.get('entities'):
            confidence += 0.05
        
        return min(1.0, max(0.1, confidence))
    
    def _requires_confirmation(self, command: Dict[str, Any]) -> bool:
        """Check if command requires confirmation"""
        command_id = f"{command['type']}_{command['action']}"
        
        # Check against critical commands list
        if command_id in self.critical_commands:
            return True
        
        # Always confirm interpreted commands
        if command['type'] == 'interpreted_command':
            return True
        
        # Confirm commands with low confidence
        if command.get('confidence', 0) < 0.5:
            return True
        
        # Specific command types that always need confirmation
        critical_actions = ['engage', 'disengage', 'mob', 'emergency']
        if command.get('action') in critical_actions:
            return True
        
        return False
    
    def get_available_commands(self) -> Dict[str, Any]:
        """Get list of available voice commands"""
        commands = {}
        
        for category, command_types in self.command_patterns.items():
            commands[category] = {}
            
            for command_type, patterns in command_types.items():
                # Convert patterns to user-friendly examples
                examples = []
                for pattern in patterns:
                    # Clean up regex pattern for display
                    example = re.sub(r'[\(\)\[\]\.\*\+\?\\]', '', pattern)
                    example = re.sub(r'\|', ' or ', example)
                    examples.append(example)
                
                commands[category][command_type] = {
                    'examples': examples[:3],  # Show first 3 examples
                    'requires_confirmation': f"{category}_{command_type}" in self.critical_commands
                }
        
        return commands
    
    def validate_command(self, command: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate parsed command"""
        if not command or not isinstance(command, dict):
            return False, "Invalid command format"
        
        if 'type' not in command:
            return False, "Missing command type"
        
        if 'action' not in command:
            return False, "Missing command action"
        
        # Validate parameters for specific commands
        command_type = command['type']
        action = command['action']
        params = command.get('params', {})
        
        if command_type == 'autopilot' and action == 'set_heading':
            heading = params.get('heading')
            if heading is None or not (0 <= heading <= 360):
                return False, "Invalid heading value (must be 0-360)"
        
        elif command_type == 'follow_vessel' and action == 'set_distance':
            distance = params.get('distance')
            if distance is None or distance <= 0:
                return False, "Invalid follow distance (must be positive)"
        
        return True, "Command valid"
    
    def get_command_help(self, command_type: str = None) -> str:
        """Get help text for commands"""
        if not command_type:
            return """
Available command categories:
- chart_control: Control chart display and navigation
- autopilot: Engage and control autopilot
- follow_vessel: Follow other vessels
- navigation: Waypoints and navigation marks
- log_entry: Voice logging
- system_control: Voice system settings

Say "help [category]" for specific commands.
            """.strip()
        
        if command_type not in self.command_patterns:
            return f"Unknown command category: {command_type}"
        
        commands = self.get_available_commands()[command_type]
        help_text = f"\n{command_type.title()} Commands:\n"
        
        for action, details in commands.items():
            help_text += f"\n{action}:\n"
            for example in details['examples']:
                help_text += f"  - {example}\n"
            
            if details['requires_confirmation']:
                help_text += "  (Requires confirmation)\n"
        
        return help_text