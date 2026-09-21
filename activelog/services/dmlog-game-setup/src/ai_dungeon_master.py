import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import random
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SuggestionType(str, Enum):
    STORY_PROGRESSION = "story_progression"
    NPC_RESPONSE = "npc_response"
    RULE_REMINDER = "rule_reminder"
    PLOT_POINT = "plot_point"
    ATMOSPHERIC_DESCRIPTION = "atmospheric_description"
    COMBAT_ASSISTANCE = "combat_assistance"
    RANDOM_EVENT = "random_event"
    DIFFICULTY_ADJUSTMENT = "difficulty_adjustment"

class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class DMAISuggestion:
    suggestion_id: str
    type: SuggestionType
    urgency: UrgencyLevel
    title: str
    description: str
    implementation: str
    context: Dict[str, Any]
    confidence: float
    triggers: List[str]
    consequences: List[str]
    timestamp: datetime

@dataclass
class GameState:
    current_scene: str
    active_players: List[str]
    current_location: str
    initiative_order: List[str]
    combat_active: bool
    tension_level: float
    last_action: str
    unresolved_plot_points: List[str]
    active_npcs: List[str]
    environmental_factors: List[str]

@dataclass
class NPCResponse:
    npc_name: str
    response_text: str
    emotional_state: str
    voice_characteristics: Dict[str, Any]
    body_language: str
    intent: str
    hidden_agenda: Optional[str]

class AIDungeonMaster:
    def __init__(self):
        self.active_sessions = {}  # session_id -> GameState
        self.suggestion_history = {}  # session_id -> List[DMAISuggestion]
        self.rule_database = self._initialize_rule_database()
        self.atmosphere_library = self._initialize_atmosphere_library()
        self.random_events = self._initialize_random_events()
        self.combat_calculator = CombatCalculator()
        self.difficulty_manager = DifficultyManager()
        self.listening_active = {}  # session_id -> bool

    def _initialize_rule_database(self) -> Dict[str, Dict]:
        """Initialize D&D 5e rule database for automatic reminders."""
        return {
            'combat': {
                'initiative': {
                    'trigger': ['combat', 'initiative', 'turn order'],
                    'reminder': 'Roll 1d20 + DEX modifier for initiative',
                    'details': 'Each creature acts on their initiative count in descending order'
                },
                'advantage': {
                    'trigger': ['advantage', 'disadvantage', 'roll'],
                    'reminder': 'Advantage: roll twice, take higher. Disadvantage: roll twice, take lower',
                    'details': 'They never stack - you either have it or you don\'t'
                },
                'opportunity_attacks': {
                    'trigger': ['move', 'movement', 'leaving', 'provoke'],
                    'reminder': 'Moving out of enemy reach provokes opportunity attack',
                    'details': 'Use reaction to make one melee attack against the provoking creature'
                },
                'concentration': {
                    'trigger': ['concentration', 'spell', 'damage'],
                    'reminder': 'Concentration check: DC 10 or half damage taken (whichever is higher)',
                    'details': 'Roll Constitution saving throw to maintain concentration'
                }
            },
            'spellcasting': {
                'spell_slots': {
                    'trigger': ['spell', 'cast', 'slots'],
                    'reminder': 'Check available spell slots for the spell level',
                    'details': 'Higher level slots can cast lower level spells'
                },
                'components': {
                    'trigger': ['somatic', 'verbal', 'material'],
                    'reminder': 'Verbal (V), Somatic (S), Material (M) components required',
                    'details': 'Free hand needed for somatic, can speak for verbal, need component pouch/focus'
                }
            },
            'exploration': {
                'passive_perception': {
                    'trigger': ['perception', 'notice', 'hidden'],
                    'reminder': 'Use Passive Perception (10 + WIS modifier + proficiency)',
                    'details': 'Always active, determines what characters notice automatically'
                }
            }
        }

    def _initialize_atmosphere_library(self) -> Dict[str, List[str]]:
        """Initialize atmospheric descriptions for different scenarios."""
        return {
            'tavern': [
                "The smoky tavern buzzes with conversation as patrons nurse their ales by flickering candlelight.",
                "Laughter echoes from a corner table where a bard strums a lively tune on his lute.",
                "The scent of roasted meat and fresh bread mingles with the aroma of spilled wine.",
                "Shadows dance on weathered walls as the fire crackles in the stone hearth."
            ],
            'dungeon': [
                "Your torchlight barely penetrates the oppressive darkness ahead.",
                "Water drips steadily somewhere in the distance, echoing off ancient stone walls.",
                "The air is thick and stale, carrying the musty scent of centuries-old decay.",
                "Strange symbols carved into the walls seem to shift in the flickering light."
            ],
            'forest': [
                "Sunlight filters through the dense canopy, creating shifting patterns on the forest floor.",
                "The undergrowth rustles with unseen movement as birds call from the treetops.",
                "Ancient trees tower overhead, their gnarled branches intertwining like protective arms.",
                "The earthy scent of moss and fallen leaves fills the air with each breath."
            ],
            'combat_tense': [
                "Time seems to slow as adrenaline surges through your veins.",
                "The clash of steel rings out as sparks fly from parried blows.",
                "Your enemy's eyes burn with murderous intent as they close the distance.",
                "The battlefield erupts in chaos as allies and enemies alike struggle for advantage."
            ],
            'mystery': [
                "An unsettling silence hangs in the air, broken only by your own heartbeat.",
                "Something feels fundamentally wrong about this place, though you can't place what.",
                "The shadows seem deeper here, hiding secrets just beyond your understanding.",
                "A chill runs down your spine as you sense unseen eyes watching your every move."
            ]
        }

    def _initialize_random_events(self) -> Dict[str, List[Dict]]:
        """Initialize random events for different contexts."""
        return {
            'travel': [
                {
                    'event': 'Merchant caravan approaches, seeking protection from bandits',
                    'difficulty': 'medium',
                    'outcomes': ['reward', 'information', 'new_quest'],
                    'npcs': ['Worried Merchant', 'Caravan Guards']
                },
                {
                    'event': 'Sudden storm forces the party to seek immediate shelter',
                    'difficulty': 'easy',
                    'outcomes': ['delay', 'encounter', 'discovery'],
                    'npcs': []
                },
                {
                    'event': 'Bridge ahead has collapsed, requiring creative solution',
                    'difficulty': 'medium',
                    'outcomes': ['skill_challenge', 'detour', 'resource_cost'],
                    'npcs': []
                }
            ],
            'social': [
                {
                    'event': 'Important NPC arrives unexpectedly at the tavern',
                    'difficulty': 'low',
                    'outcomes': ['information', 'quest_hook', 'complication'],
                    'npcs': ['Traveling Noble', 'Royal Messenger']
                },
                {
                    'event': 'Bar fight breaks out, party gets caught in the middle',
                    'difficulty': 'medium',
                    'outcomes': ['combat', 'reputation_change', 'legal_trouble'],
                    'npcs': ['Drunk Locals', 'Tavern Keep']
                }
            ],
            'dungeon': [
                {
                    'event': 'Ancient magical trap activates from party\'s presence',
                    'difficulty': 'hard',
                    'outcomes': ['damage', 'status_effect', 'environmental_change'],
                    'npcs': []
                },
                {
                    'event': 'Rival adventuring party is already exploring this area',
                    'difficulty': 'hard',
                    'outcomes': ['competition', 'alliance', 'combat'],
                    'npcs': ['Rival Leader', 'Rival Party Members']
                }
            ]
        }

    async def start_session_listening(self, session_id: str, initial_game_state: GameState):
        """Start actively listening to and analyzing a game session."""
        self.active_sessions[session_id] = initial_game_state
        self.suggestion_history[session_id] = []
        self.listening_active[session_id] = True
        
        logger.info(f"AI DM Assistant activated for session {session_id}")
        
        # Start background analysis
        asyncio.create_task(self._continuous_analysis(session_id))

    async def _continuous_analysis(self, session_id: str):
        """Continuously analyze game session and generate suggestions."""
        while self.listening_active.get(session_id, False):
            try:
                game_state = self.active_sessions.get(session_id)
                if not game_state:
                    break
                
                # Generate suggestions based on current state
                suggestions = await self._analyze_and_suggest(session_id, game_state)
                
                # Add suggestions to history
                for suggestion in suggestions:
                    self.suggestion_history[session_id].append(suggestion)
                    
                # Keep only recent suggestions (last 50)
                if len(self.suggestion_history[session_id]) > 50:
                    self.suggestion_history[session_id] = self.suggestion_history[session_id][-50:]
                
                # Wait before next analysis
                await asyncio.sleep(10)  # Analyze every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in continuous analysis: {e}")
                await asyncio.sleep(5)

    async def _analyze_and_suggest(self, session_id: str, game_state: GameState) -> List[DMAISuggestion]:
        """Analyze current game state and generate suggestions."""
        suggestions = []
        
        # Check for rule reminders
        rule_suggestions = await self._check_rule_reminders(game_state)
        suggestions.extend(rule_suggestions)
        
        # Check for forgotten plot points
        plot_suggestions = await self._check_forgotten_plots(game_state)
        suggestions.extend(plot_suggestions)
        
        # Generate atmospheric descriptions
        atmosphere_suggestions = await self._generate_atmosphere_suggestions(game_state)
        suggestions.extend(atmosphere_suggestions)
        
        # Combat assistance if needed
        if game_state.combat_active:
            combat_suggestions = await self._generate_combat_suggestions(game_state)
            suggestions.extend(combat_suggestions)
        
        # Random events if tension is low
        if game_state.tension_level < 0.3:
            event_suggestions = await self._suggest_random_events(game_state)
            suggestions.extend(event_suggestions)
        
        # Difficulty adjustments
        difficulty_suggestions = await self._check_difficulty_adjustment(game_state)
        suggestions.extend(difficulty_suggestions)
        
        # Story progression suggestions
        story_suggestions = await self._generate_story_progression(game_state)
        suggestions.extend(story_suggestions)
        
        return suggestions

    async def _check_rule_reminders(self, game_state: GameState) -> List[DMAISuggestion]:
        """Check if any rules should be reminded based on current action."""
        suggestions = []
        last_action = game_state.last_action.lower()
        
        for category, rules in self.rule_database.items():
            for rule_name, rule_info in rules.items():
                if any(trigger in last_action for trigger in rule_info['trigger']):
                    suggestion = DMAISuggestion(
                        suggestion_id=f"rule_{rule_name}_{datetime.now().strftime('%H%M%S')}",
                        type=SuggestionType.RULE_REMINDER,
                        urgency=UrgencyLevel.MEDIUM,
                        title=f"Rule Reminder: {rule_name.replace('_', ' ').title()}",
                        description=rule_info['reminder'],
                        implementation=rule_info['details'],
                        context={'rule_category': category, 'triggered_by': last_action},
                        confidence=0.8,
                        triggers=rule_info['trigger'],
                        consequences=['proper_rule_application', 'consistent_gameplay'],
                        timestamp=datetime.now()
                    )
                    suggestions.append(suggestion)
        
        return suggestions

    async def _check_forgotten_plots(self, game_state: GameState) -> List[DMAISuggestion]:
        """Check for forgotten plot points that should be reminded."""
        suggestions = []
        
        for plot_point in game_state.unresolved_plot_points:
            # Simple check: if plot point hasn't been mentioned recently
            suggestion = DMAISuggestion(
                suggestion_id=f"plot_{hash(plot_point)}_{datetime.now().strftime('%H%M%S')}",
                type=SuggestionType.PLOT_POINT,
                urgency=UrgencyLevel.LOW,
                title="Forgotten Plot Thread",
                description=f"Consider bringing up: {plot_point}",
                implementation=f"Have an NPC mention {plot_point} or create a scene that reminds players",
                context={'plot_point': plot_point, 'location': game_state.current_location},
                confidence=0.6,
                triggers=['scene_transition', 'downtime'],
                consequences=['plot_continuity', 'player_engagement'],
                timestamp=datetime.now()
            )
            suggestions.append(suggestion)
        
        return suggestions

    async def _generate_atmosphere_suggestions(self, game_state: GameState) -> List[DMAISuggestion]:
        """Generate atmospheric description suggestions."""
        suggestions = []
        
        # Determine appropriate atmosphere type
        location_type = self._categorize_location(game_state.current_location)
        
        if location_type in self.atmosphere_library:
            description = random.choice(self.atmosphere_library[location_type])
            
            suggestion = DMAISuggestion(
                suggestion_id=f"atmosphere_{datetime.now().strftime('%H%M%S')}",
                type=SuggestionType.ATMOSPHERIC_DESCRIPTION,
                urgency=UrgencyLevel.LOW,
                title="Atmospheric Description",
                description=f"Set the scene: {description}",
                implementation=f"Read aloud: '{description}'",
                context={'location': game_state.current_location, 'type': location_type},
                confidence=0.7,
                triggers=['scene_start', 'location_change'],
                consequences=['immersion', 'mood_setting'],
                timestamp=datetime.now()
            )
            suggestions.append(suggestion)
        
        return suggestions

    def _categorize_location(self, location: str) -> str:
        """Categorize location for atmospheric descriptions."""
        location_lower = location.lower()
        
        if any(word in location_lower for word in ['tavern', 'inn', 'bar']):
            return 'tavern'
        elif any(word in location_lower for word in ['dungeon', 'crypt', 'tomb', 'cave']):
            return 'dungeon'
        elif any(word in location_lower for word in ['forest', 'wood', 'grove']):
            return 'forest'
        elif 'combat' in location_lower or 'battle' in location_lower:
            return 'combat_tense'
        elif any(word in location_lower for word in ['mystery', 'strange', 'eerie']):
            return 'mystery'
        else:
            return 'tavern'  # Default

    async def _generate_combat_suggestions(self, game_state: GameState) -> List[DMAISuggestion]:
        """Generate combat assistance suggestions."""
        suggestions = []
        
        # Math assistance
        suggestion = DMAISuggestion(
            suggestion_id=f"combat_math_{datetime.now().strftime('%H%M%S')}",
            type=SuggestionType.COMBAT_ASSISTANCE,
            urgency=UrgencyLevel.HIGH,
            title="Combat Math Assistant",
            description="Remember to apply modifiers: Attack roll = 1d20 + ability mod + proficiency bonus",
            implementation="Double-check damage calculations and AC comparisons",
            context={'combat_round': True, 'participants': game_state.active_players},
            confidence=0.9,
            triggers=['combat_active'],
            consequences=['accurate_combat', 'smooth_gameplay'],
            timestamp=datetime.now()
        )
        suggestions.append(suggestion)
        
        # Initiative reminder
        if not game_state.initiative_order:
            initiative_suggestion = DMAISuggestion(
                suggestion_id=f"initiative_{datetime.now().strftime('%H%M%S')}",
                type=SuggestionType.COMBAT_ASSISTANCE,
                urgency=UrgencyLevel.HIGH,
                title="Initiative Order Needed",
                description="Roll initiative for all participants",
                implementation="Have everyone roll 1d20 + DEX modifier, then arrange in descending order",
                context={'combat_start': True},
                confidence=0.95,
                triggers=['combat_start'],
                consequences=['organized_combat'],
                timestamp=datetime.now()
            )
            suggestions.append(initiative_suggestion)
        
        return suggestions

    async def _suggest_random_events(self, game_state: GameState) -> List[DMAISuggestion]:
        """Suggest random events to increase tension."""
        suggestions = []
        
        # Determine appropriate event category
        if game_state.current_scene == 'travel':
            events = self.random_events['travel']
        elif 'tavern' in game_state.current_location.lower():
            events = self.random_events['social']
        elif any(word in game_state.current_location.lower() for word in ['dungeon', 'cave', 'tomb']):
            events = self.random_events['dungeon']
        else:
            events = self.random_events['travel']  # Default
        
        if events:
            event = random.choice(events)
            
            suggestion = DMAISuggestion(
                suggestion_id=f"random_event_{datetime.now().strftime('%H%M%S')}",
                type=SuggestionType.RANDOM_EVENT,
                urgency=UrgencyLevel.MEDIUM,
                title="Random Event Suggestion",
                description=event['event'],
                implementation=f"Introduce: {event['event']}. Potential outcomes: {', '.join(event['outcomes'])}",
                context={'event_type': 'random', 'difficulty': event['difficulty'], 'npcs': event['npcs']},
                confidence=0.6,
                triggers=['low_tension', 'scene_transition'],
                consequences=['increased_engagement', 'tension_boost'],
                timestamp=datetime.now()
            )
            suggestions.append(suggestion)
        
        return suggestions

    async def _check_difficulty_adjustment(self, game_state: GameState) -> List[DMAISuggestion]:
        """Check if difficulty should be adjusted."""
        suggestions = []
        
        # Simple heuristic: if tension is too low or too high
        if game_state.tension_level > 0.8:
            suggestion = DMAISuggestion(
                suggestion_id=f"difficulty_down_{datetime.now().strftime('%H%M%S')}",
                type=SuggestionType.DIFFICULTY_ADJUSTMENT,
                urgency=UrgencyLevel.MEDIUM,
                title="Consider Reducing Difficulty",
                description="Tension level is very high - players might be struggling",
                implementation="Reduce enemy HP, give players advantage, or provide helpful NPCs",
                context={'tension': game_state.tension_level, 'adjustment': 'reduce'},
                confidence=0.7,
                triggers=['high_tension'],
                consequences=['balanced_challenge'],
                timestamp=datetime.now()
            )
            suggestions.append(suggestion)
        
        elif game_state.tension_level < 0.2:
            suggestion = DMAISuggestion(
                suggestion_id=f"difficulty_up_{datetime.now().strftime('%H%M%S')}",
                type=SuggestionType.DIFFICULTY_ADJUSTMENT,
                urgency=UrgencyLevel.MEDIUM,
                title="Consider Increasing Challenge",
                description="Tension level is low - encounter might be too easy",
                implementation="Add reinforcements, environmental hazards, or time pressure",
                context={'tension': game_state.tension_level, 'adjustment': 'increase'},
                confidence=0.6,
                triggers=['low_tension'],
                consequences=['engaging_challenge'],
                timestamp=datetime.now()
            )
            suggestions.append(suggestion)
        
        return suggestions

    async def _generate_story_progression(self, game_state: GameState) -> List[DMAISuggestion]:
        """Generate story progression suggestions."""
        suggestions = []
        
        # Generic story progression based on scene
        progression_ideas = [
            "Introduce a complication that forces players to make a difficult choice",
            "Have an NPC reveal important information about the main quest",
            "Create a scene that deepens character relationships or backstories",
            "Present a moral dilemma that tests the party's values",
            "Introduce a time-sensitive element to increase urgency"
        ]
        
        idea = random.choice(progression_ideas)
        
        suggestion = DMAISuggestion(
            suggestion_id=f"story_prog_{datetime.now().strftime('%H%M%S')}",
            type=SuggestionType.STORY_PROGRESSION,
            urgency=UrgencyLevel.MEDIUM,
            title="Story Progression Idea",
            description=idea,
            implementation=f"Consider: {idea}",
            context={'current_scene': game_state.current_scene},
            confidence=0.5,
            triggers=['scene_lull', 'transition_point'],
            consequences=['story_advancement', 'player_engagement'],
            timestamp=datetime.now()
        )
        suggestions.append(suggestion)
        
        return suggestions

    async def update_game_state(self, session_id: str, updates: Dict[str, Any]):
        """Update the current game state based on new information."""
        if session_id in self.active_sessions:
            game_state = self.active_sessions[session_id]
            
            for key, value in updates.items():
                if hasattr(game_state, key):
                    setattr(game_state, key, value)
            
            logger.info(f"Updated game state for session {session_id}: {updates}")

    async def generate_npc_response(self, session_id: str, npc_name: str, context: str, player_input: str) -> NPCResponse:
        """Generate contextual NPC response."""
        game_state = self.active_sessions.get(session_id)
        
        # Get NPC personality and context
        npc_context = self._get_npc_context(npc_name, game_state)
        
        # Generate response based on NPC personality and situation
        response_text = await self._generate_contextual_response(
            npc_name, npc_context, context, player_input
        )
        
        # Determine emotional state
        emotional_state = self._analyze_emotional_context(context, player_input)
        
        # Generate voice characteristics
        voice_chars = self._get_npc_voice_characteristics(npc_name)
        
        return NPCResponse(
            npc_name=npc_name,
            response_text=response_text,
            emotional_state=emotional_state,
            voice_characteristics=voice_chars,
            body_language=self._generate_body_language(emotional_state),
            intent=self._determine_npc_intent(npc_context, context),
            hidden_agenda=npc_context.get('hidden_agenda')
        )

    def _get_npc_context(self, npc_name: str, game_state: GameState) -> Dict[str, Any]:
        """Get NPC context and personality information."""
        # This would typically pull from the knowledge graph
        return {
            'personality': 'helpful',
            'relationship_to_party': 'neutral',
            'knowledge_level': 'local',
            'hidden_agenda': None,
            'emotional_state': 'calm'
        }

    async def _generate_contextual_response(self, npc_name: str, npc_context: Dict, 
                                         context: str, player_input: str) -> str:
        """Generate contextual NPC response."""
        # Simple response generation - would use AI in production
        personality = npc_context.get('personality', 'neutral')
        
        if 'question' in player_input.lower():
            if personality == 'helpful':
                return f"*{npc_name} considers your question carefully* I'd be happy to help with that..."
            elif personality == 'suspicious':
                return f"*{npc_name} eyes you warily* Why do you want to know?"
            else:
                return f"*{npc_name} nods* I see what you're asking..."
        else:
            return f"*{npc_name} responds thoughtfully* That's interesting..."

    def _analyze_emotional_context(self, context: str, player_input: str) -> str:
        """Analyze emotional context of the situation."""
        context_lower = context.lower() + " " + player_input.lower()
        
        if any(word in context_lower for word in ['angry', 'mad', 'furious']):
            return 'angry'
        elif any(word in context_lower for word in ['sad', 'depressed', 'crying']):
            return 'sad'
        elif any(word in context_lower for word in ['happy', 'joyful', 'excited']):
            return 'happy'
        elif any(word in context_lower for word in ['scared', 'afraid', 'terrified']):
            return 'fearful'
        elif any(word in context_lower for word in ['suspicious', 'doubtful', 'wary']):
            return 'suspicious'
        else:
            return 'neutral'

    def _get_npc_voice_characteristics(self, npc_name: str) -> Dict[str, Any]:
        """Get voice characteristics for NPC."""
        # Would pull from voice profile database
        return {
            'pitch': 'medium',
            'tone': 'friendly',
            'accent': 'local',
            'speaking_rate': 'normal'
        }

    def _generate_body_language(self, emotional_state: str) -> str:
        """Generate appropriate body language for emotional state."""
        body_language_map = {
            'angry': 'clenched fists, stern expression, leaning forward aggressively',
            'sad': 'slumped shoulders, downcast eyes, slow movements',
            'happy': 'bright smile, animated gestures, upright posture',
            'fearful': 'wide eyes, backing away, trembling hands',
            'suspicious': 'narrowed eyes, crossed arms, defensive stance',
            'neutral': 'relaxed posture, attentive expression, calm demeanor'
        }
        
        return body_language_map.get(emotional_state, body_language_map['neutral'])

    def _determine_npc_intent(self, npc_context: Dict, situation_context: str) -> str:
        """Determine NPC's intent in the current situation."""
        # Simple intent determination
        if 'quest' in situation_context.lower():
            return 'provide_quest_information'
        elif 'shop' in situation_context.lower() or 'buy' in situation_context.lower():
            return 'conduct_business'
        elif 'help' in situation_context.lower():
            return 'provide_assistance'
        else:
            return 'social_interaction'

    def get_active_suggestions(self, session_id: str, 
                             urgency_filter: Optional[UrgencyLevel] = None) -> List[DMAISuggestion]:
        """Get current active suggestions for a session."""
        if session_id not in self.suggestion_history:
            return []
        
        suggestions = self.suggestion_history[session_id]
        
        # Filter by urgency if specified
        if urgency_filter:
            suggestions = [s for s in suggestions if s.urgency == urgency_filter]
        
        # Return recent suggestions (last 10 minutes)
        cutoff_time = datetime.now() - timedelta(minutes=10)
        recent_suggestions = [s for s in suggestions if s.timestamp > cutoff_time]
        
        return recent_suggestions[-10:]  # Last 10 suggestions

    def stop_session_listening(self, session_id: str):
        """Stop listening to a session."""
        self.listening_active[session_id] = False
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        logger.info(f"AI DM Assistant deactivated for session {session_id}")

class CombatCalculator:
    """Helper class for combat math calculations."""
    
    def calculate_attack_roll(self, base_roll: int, ability_modifier: int, 
                            proficiency_bonus: int, other_modifiers: int = 0) -> int:
        """Calculate total attack roll."""
        return base_roll + ability_modifier + proficiency_bonus + other_modifiers
    
    def calculate_damage(self, damage_dice: str, ability_modifier: int = 0) -> Dict[str, Any]:
        """Calculate damage from dice notation."""
        # Simple damage calculation - would expand for full dice parsing
        return {
            'dice_notation': damage_dice,
            'modifier': ability_modifier,
            'average_damage': 0,  # Would calculate based on dice
            'range': (1, 10)  # Would calculate based on dice
        }
    
    def check_hit(self, attack_roll: int, target_ac: int) -> bool:
        """Check if attack hits target AC."""
        return attack_roll >= target_ac

class DifficultyManager:
    """Helper class for dynamic difficulty adjustment."""
    
    def analyze_encounter_difficulty(self, party_level: int, party_size: int, 
                                   enemy_cr: float) -> Dict[str, Any]:
        """Analyze encounter difficulty."""
        # Simplified difficulty calculation
        encounter_multiplier = self._get_encounter_multiplier(party_size)
        adjusted_xp = enemy_cr * 100 * encounter_multiplier
        
        thresholds = self._get_encounter_thresholds(party_level, party_size)
        
        if adjusted_xp <= thresholds['easy']:
            difficulty = 'easy'
        elif adjusted_xp <= thresholds['medium']:
            difficulty = 'medium'
        elif adjusted_xp <= thresholds['hard']:
            difficulty = 'hard'
        else:
            difficulty = 'deadly'
        
        return {
            'difficulty': difficulty,
            'adjusted_xp': adjusted_xp,
            'thresholds': thresholds,
            'recommendations': self._get_adjustment_recommendations(difficulty)
        }
    
    def _get_encounter_multiplier(self, party_size: int) -> float:
        """Get encounter multiplier based on party size."""
        if party_size <= 2:
            return 1.5
        elif party_size <= 5:
            return 1.0
        else:
            return 0.5
    
    def _get_encounter_thresholds(self, party_level: int, party_size: int) -> Dict[str, int]:
        """Get encounter thresholds for party."""
        # Simplified threshold calculation
        base_easy = party_level * 25
        base_medium = party_level * 50
        base_hard = party_level * 75
        base_deadly = party_level * 100
        
        return {
            'easy': base_easy * party_size,
            'medium': base_medium * party_size,
            'hard': base_hard * party_size,
            'deadly': base_deadly * party_size
        }
    
    def _get_adjustment_recommendations(self, difficulty: str) -> List[str]:
        """Get recommendations for adjusting encounter difficulty."""
        if difficulty == 'easy':
            return [
                "Add more enemies or increase their HP",
                "Introduce environmental hazards",
                "Give enemies better tactics or positioning"
            ]
        elif difficulty == 'deadly':
            return [
                "Reduce enemy HP or remove some enemies",
                "Have enemies make tactical mistakes",
                "Provide environmental advantages to players"
            ]
        else:
            return ["Difficulty appears balanced"]