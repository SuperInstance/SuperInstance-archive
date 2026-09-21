import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class StepPrediction:
    step_id: str
    step_name: str
    confidence: float
    reasons: List[str]
    estimated_time: int  # in minutes
    prerequisites: List[str]
    skip_conditions: List[str]

@dataclass
class FieldPrediction:
    field_name: str
    predicted_value: Any
    confidence: float
    source: str  # 'context', 'pattern', 'default'

class UIComplexityLevel(BaseModel):
    level: str  # 'beginner', 'intermediate', 'expert'
    show_advanced_options: bool
    auto_fill_suggestions: bool
    step_by_step_guidance: bool
    quick_setup_available: bool

class RelevantOption(BaseModel):
    option_id: str
    label: str
    description: str
    relevance_score: float
    category: str

class PredictiveInterface:
    def __init__(self):
        self.setup_flow = self._initialize_setup_flow()
        self.field_patterns = self._initialize_field_patterns()
        self.complexity_indicators = self._initialize_complexity_indicators()
        self.campaign_style_options = self._initialize_campaign_options()

    def _initialize_setup_flow(self) -> Dict[str, Dict]:
        """Initialize the standard setup flow with branching logic."""
        return {
            'initial_setup': {
                'name': 'Campaign Overview',
                'next_steps': ['world_setting', 'character_creation', 'session_zero'],
                'required_fields': ['campaign_name', 'setting_type', 'player_count'],
                'estimated_time': 10,
                'skip_conditions': ['existing_campaign_import']
            },
            'world_setting': {
                'name': 'World & Setting',
                'next_steps': ['character_creation', 'location_design', 'npc_creation'],
                'required_fields': ['world_name', 'setting_genre', 'starting_location'],
                'estimated_time': 15,
                'skip_conditions': ['pre_built_world_selected']
            },
            'character_creation': {
                'name': 'Character Setup',
                'next_steps': ['party_dynamics', 'backstory_integration', 'npc_creation'],
                'required_fields': ['character_sheets', 'starting_levels', 'party_composition'],
                'estimated_time': 20,
                'skip_conditions': ['characters_pre_created']
            },
            'npc_creation': {
                'name': 'NPC Development',
                'next_steps': ['location_design', 'plot_hooks', 'encounter_design'],
                'required_fields': ['key_npcs', 'npc_relationships', 'voice_profiles'],
                'estimated_time': 25,
                'skip_conditions': ['minimal_npc_campaign']
            },
            'location_design': {
                'name': 'Locations & Maps',
                'next_steps': ['encounter_design', 'item_creation', 'plot_hooks'],
                'required_fields': ['key_locations', 'travel_routes', 'location_details'],
                'estimated_time': 20,
                'skip_conditions': ['theater_of_mind_only']
            },
            'encounter_design': {
                'name': 'Encounters & Combat',
                'next_steps': ['item_creation', 'session_planning', 'final_review'],
                'required_fields': ['encounter_list', 'difficulty_scaling', 'combat_mechanics'],
                'estimated_time': 30,
                'skip_conditions': ['roleplay_focused_campaign']
            },
            'item_creation': {
                'name': 'Items & Rewards',
                'next_steps': ['economy_setup', 'session_planning', 'final_review'],
                'required_fields': ['starting_equipment', 'treasure_tables', 'magic_items'],
                'estimated_time': 15,
                'skip_conditions': ['low_magic_campaign']
            },
            'plot_hooks': {
                'name': 'Story & Plot Hooks',
                'next_steps': ['session_planning', 'backstory_integration', 'final_review'],
                'required_fields': ['main_quest', 'side_quests', 'story_threads'],
                'estimated_time': 20,
                'skip_conditions': ['sandbox_campaign']
            },
            'session_planning': {
                'name': 'Session Planning',
                'next_steps': ['final_review', 'player_handouts', 'launch_preparation'],
                'required_fields': ['session_structure', 'pacing_notes', 'backup_plans'],
                'estimated_time': 15,
                'skip_conditions': ['improvisation_only']
            },
            'final_review': {
                'name': 'Final Review & Launch',
                'next_steps': [],
                'required_fields': ['review_checklist', 'player_communication', 'session_zero_plan'],
                'estimated_time': 10,
                'skip_conditions': []
            }
        }

    def _initialize_field_patterns(self) -> Dict[str, Dict]:
        """Initialize patterns for field prediction."""
        return {
            'campaign_name': {
                'patterns': ['The .* Campaign', '.* Chronicles', 'Tales of .*', '.* Adventures'],
                'context_sources': ['world_mentions', 'character_names', 'location_names']
            },
            'setting_genre': {
                'keywords': {
                    'high_fantasy': ['dragon', 'magic', 'wizard', 'elf', 'dwarf'],
                    'urban_fantasy': ['modern', 'city', 'technology', 'urban'],
                    'horror': ['horror', 'dark', 'scary', 'nightmare', 'undead'],
                    'steampunk': ['steam', 'mechanical', 'inventor', 'airship'],
                    'sci_fi': ['space', 'alien', 'technology', 'future', 'robot']
                }
            },
            'starting_location': {
                'defaults_by_genre': {
                    'high_fantasy': 'Village Tavern',
                    'urban_fantasy': 'City District',
                    'horror': 'Isolated Manor',
                    'steampunk': 'Industrial City',
                    'sci_fi': 'Space Station'
                }
            },
            'party_size': {
                'optimal_ranges': {
                    'new_dm': (3, 4),
                    'experienced_dm': (4, 6),
                    'expert_dm': (5, 8)
                }
            }
        }

    def _initialize_complexity_indicators(self) -> Dict[str, List[str]]:
        """Initialize complexity level indicators."""
        return {
            'beginner': [
                'first time', 'new to', 'simple', 'basic', 'easy',
                'learning', 'starter', 'introduction'
            ],
            'intermediate': [
                'some experience', 'familiar with', 'moderate',
                'expanding', 'developing', 'improving'
            ],
            'expert': [
                'experienced', 'advanced', 'complex', 'detailed',
                'custom rules', 'homebrew', 'sophisticated'
            ]
        }

    def _initialize_campaign_options(self) -> Dict[str, List[Dict]]:
        """Initialize campaign style options."""
        return {
            'heroic_fantasy': [
                {'id': 'epic_quest', 'label': 'Epic Quest Structure', 'description': 'Classic hero\'s journey'},
                {'id': 'chosen_one', 'label': 'Chosen One Narrative', 'description': 'Destiny-driven story'},
                {'id': 'kingdom_politics', 'label': 'Kingdom Politics', 'description': 'Court intrigue and nobility'}
            ],
            'dark_fantasy': [
                {'id': 'horror_elements', 'label': 'Horror Elements', 'description': 'Psychological and supernatural scares'},
                {'id': 'moral_ambiguity', 'label': 'Moral Ambiguity', 'description': 'Complex ethical choices'},
                {'id': 'survival_mechanics', 'label': 'Survival Focus', 'description': 'Resource management and danger'}
            ],
            'urban_fantasy': [
                {'id': 'modern_integration', 'label': 'Modern Integration', 'description': 'Magic meets technology'},
                {'id': 'hidden_world', 'label': 'Hidden World', 'description': 'Secret supernatural society'},
                {'id': 'conspiracy', 'label': 'Conspiracy Elements', 'description': 'Hidden agendas and secrets'}
            ],
            'exploration': [
                {'id': 'hexcrawl', 'label': 'Hex Crawl', 'description': 'Grid-based exploration'},
                {'id': 'discovery', 'label': 'Discovery Focus', 'description': 'Unknown lands and mysteries'},
                {'id': 'settlement_building', 'label': 'Settlement Building', 'description': 'Establish communities'}
            ]
        }

    async def predict_next_steps(self, session, current_step_data: Dict) -> List[StepPrediction]:
        """Analyze conversation to predict the most likely next setup steps."""
        current_step = current_step_data.get('step_id', 'initial_setup')
        predictions = []
        
        if current_step not in self.setup_flow:
            return predictions
        
        step_info = self.setup_flow[current_step]
        potential_next_steps = step_info.get('next_steps', [])
        
        for next_step_id in potential_next_steps:
            if next_step_id not in self.setup_flow:
                continue
                
            next_step_info = self.setup_flow[next_step_id]
            
            # Calculate confidence based on context
            confidence = await self._calculate_step_confidence(
                session, current_step, next_step_id
            )
            
            # Check skip conditions
            skip_reasons = await self._check_skip_conditions(
                session, next_step_info.get('skip_conditions', [])
            )
            
            # Generate reasons for prediction
            reasons = await self._generate_step_reasons(
                session, current_step, next_step_id
            )
            
            prediction = StepPrediction(
                step_id=next_step_id,
                step_name=next_step_info['name'],
                confidence=confidence,
                reasons=reasons,
                estimated_time=next_step_info.get('estimated_time', 15),
                prerequisites=await self._check_prerequisites(session, next_step_id),
                skip_conditions=skip_reasons
            )
            
            predictions.append(prediction)
        
        # Sort by confidence
        predictions.sort(key=lambda x: x.confidence, reverse=True)
        return predictions[:3]  # Return top 3 predictions

    async def _calculate_step_confidence(self, session, current_step: str, next_step: str) -> float:
        """Calculate confidence score for next step prediction."""
        base_confidence = 0.5
        
        # Check if context mentions relevant topics
        context_history = getattr(session, 'context_history', [])
        recent_context = ' '.join(context_history[-3:]).lower() if context_history else ''
        
        # Step-specific confidence adjustments
        if next_step == 'npc_creation' and any(word in recent_context for word in ['character', 'npc', 'person']):
            base_confidence += 0.3
        elif next_step == 'location_design' and any(word in recent_context for word in ['place', 'location', 'map']):
            base_confidence += 0.3
        elif next_step == 'encounter_design' and any(word in recent_context for word in ['combat', 'fight', 'encounter']):
            base_confidence += 0.3
        elif next_step == 'plot_hooks' and any(word in recent_context for word in ['story', 'plot', 'quest']):
            base_confidence += 0.3
        
        # Reduce confidence if skip conditions are met
        next_step_info = self.setup_flow.get(next_step, {})
        skip_conditions = next_step_info.get('skip_conditions', [])
        if await self._check_skip_conditions(session, skip_conditions):
            base_confidence -= 0.2
        
        return max(0.1, min(1.0, base_confidence))

    async def _check_skip_conditions(self, session, skip_conditions: List[str]) -> List[str]:
        """Check which skip conditions are met."""
        met_conditions = []
        
        for condition in skip_conditions:
            if await self._evaluate_skip_condition(session, condition):
                met_conditions.append(condition)
        
        return met_conditions

    async def _evaluate_skip_condition(self, session, condition: str) -> bool:
        """Evaluate if a specific skip condition is met."""
        context_history = getattr(session, 'context_history', [])
        recent_context = ' '.join(context_history[-5:]).lower() if context_history else ''
        
        condition_checks = {
            'existing_campaign_import': 'import' in recent_context or 'existing' in recent_context,
            'pre_built_world_selected': 'pre-built' in recent_context or 'published' in recent_context,
            'characters_pre_created': 'pre-made' in recent_context or 'already created' in recent_context,
            'minimal_npc_campaign': 'minimal npc' in recent_context or 'few characters' in recent_context,
            'theater_of_mind_only': 'theater of mind' in recent_context or 'no maps' in recent_context,
            'roleplay_focused_campaign': 'roleplay focused' in recent_context or 'no combat' in recent_context,
            'low_magic_campaign': 'low magic' in recent_context or 'no magic items' in recent_context,
            'sandbox_campaign': 'sandbox' in recent_context or 'open world' in recent_context,
            'improvisation_only': 'improv' in recent_context or 'no planning' in recent_context
        }
        
        return condition_checks.get(condition, False)

    async def _generate_step_reasons(self, session, current_step: str, next_step: str) -> List[str]:
        """Generate reasons why this step is predicted."""
        reasons = []
        
        context_history = getattr(session, 'context_history', [])
        recent_context = ' '.join(context_history[-3:]).lower() if context_history else ''
        
        # Step-specific reasoning
        step_reasoning = {
            'npc_creation': [
                'Characters and NPCs mentioned in conversation',
                'Story elements require character interaction',
                'Voice acting detected in recent input'
            ],
            'location_design': [
                'Multiple locations mentioned',
                'Travel and geography discussed',
                'Spatial relationships important to story'
            ],
            'encounter_design': [
                'Combat or conflict anticipated',
                'Challenge level considerations needed',
                'Tactical situations discussed'
            ],
            'plot_hooks': [
                'Story elements and narrative focus evident',
                'Player motivation and engagement needed',
                'Quest structure emerging'
            ]
        }
        
        potential_reasons = step_reasoning.get(next_step, ['Natural progression from current step'])
        
        # Filter reasons based on context
        for reason in potential_reasons:
            reason_keywords = reason.lower().split()
            if any(keyword in recent_context for keyword in reason_keywords[:2]):
                reasons.append(reason)
        
        return reasons[:2]  # Return top 2 reasons

    async def _check_prerequisites(self, session, step_id: str) -> List[str]:
        """Check prerequisites for a step."""
        prerequisites = []
        
        step_info = self.setup_flow.get(step_id, {})
        required_fields = step_info.get('required_fields', [])
        
        # Check if required information is available
        for field in required_fields:
            if not await self._is_field_satisfied(session, field):
                prerequisites.append(f"Need {field.replace('_', ' ')}")
        
        return prerequisites

    async def _is_field_satisfied(self, session, field_name: str) -> bool:
        """Check if a required field has been satisfied."""
        # This would check session data for completion
        # For now, assume basic fields are satisfied if mentioned in context
        context_history = getattr(session, 'context_history', [])
        recent_context = ' '.join(context_history).lower() if context_history else ''
        
        field_keywords = {
            'campaign_name': ['campaign', 'name', 'title'],
            'setting_type': ['setting', 'world', 'genre'],
            'player_count': ['player', 'party', 'group'],
            'world_name': ['world', 'realm', 'setting'],
            'starting_location': ['start', 'begin', 'location', 'town', 'village']
        }
        
        keywords = field_keywords.get(field_name, [field_name.replace('_', ' ')])
        return any(keyword in recent_context for keyword in keywords)

    async def pre_populate_fields(self, session, step_type: str) -> Dict[str, FieldPrediction]:
        """Pre-populate fields based on context analysis."""
        predictions = {}
        
        context_history = getattr(session, 'context_history', [])
        recent_context = ' '.join(context_history[-5:]).lower() if context_history else ''
        
        if step_type == 'world_setting':
            predictions.update(await self._predict_world_fields(session, recent_context))
        elif step_type == 'character_creation':
            predictions.update(await self._predict_character_fields(session, recent_context))
        elif step_type == 'npc_creation':
            predictions.update(await self._predict_npc_fields(session, recent_context))
        elif step_type == 'location_design':
            predictions.update(await self._predict_location_fields(session, recent_context))
        
        return predictions

    async def _predict_world_fields(self, session, context: str) -> Dict[str, FieldPrediction]:
        """Predict world setting fields."""
        predictions = {}
        
        # Predict genre
        genre_keywords = self.field_patterns['setting_genre']['keywords']
        detected_genre = 'high_fantasy'  # default
        max_matches = 0
        
        for genre, keywords in genre_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in context)
            if matches > max_matches:
                max_matches = matches
                detected_genre = genre
        
        if max_matches > 0:
            predictions['setting_genre'] = FieldPrediction(
                field_name='setting_genre',
                predicted_value=detected_genre.replace('_', ' ').title(),
                confidence=min(1.0, max_matches / 3),
                source='context'
            )
        
        # Predict starting location based on genre
        starting_locations = self.field_patterns['starting_location']['defaults_by_genre']
        if detected_genre in starting_locations:
            predictions['starting_location'] = FieldPrediction(
                field_name='starting_location',
                predicted_value=starting_locations[detected_genre],
                confidence=0.7,
                source='pattern'
            )
        
        return predictions

    async def _predict_character_fields(self, session, context: str) -> Dict[str, FieldPrediction]:
        """Predict character creation fields."""
        predictions = {}
        
        # Predict party size based on mentions
        import re
        number_mentions = re.findall(r'\b(one|two|three|four|five|six|seven|eight|\d+)\b', context)
        
        if number_mentions:
            try:
                number_map = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8}
                last_number = number_mentions[-1]
                party_size = number_map.get(last_number, int(last_number) if last_number.isdigit() else 4)
                
                predictions['party_size'] = FieldPrediction(
                    field_name='party_size',
                    predicted_value=party_size,
                    confidence=0.8,
                    source='context'
                )
            except:
                pass
        
        return predictions

    async def _predict_npc_fields(self, session, context: str) -> Dict[str, FieldPrediction]:
        """Predict NPC creation fields."""
        predictions = {}
        
        # Use extracted NPCs from session
        npcs = getattr(session, 'npcs', [])
        if npcs:
            predictions['suggested_npcs'] = FieldPrediction(
                field_name='suggested_npcs',
                predicted_value=[npc.name for npc in npcs[:5]],
                confidence=0.9,
                source='context'
            )
        
        return predictions

    async def _predict_location_fields(self, session, context: str) -> Dict[str, FieldPrediction]:
        """Predict location design fields."""
        predictions = {}
        
        # Use extracted locations from session
        locations = getattr(session, 'locations', [])
        if locations:
            predictions['suggested_locations'] = FieldPrediction(
                field_name='suggested_locations',
                predicted_value=[loc.name for loc in locations[:5]],
                confidence=0.9,
                source='context'
            )
        
        return predictions

    async def analyze_conversation_flow(self, session) -> StepPrediction:
        """Analyze conversation flow to predict the immediate next step."""
        context_history = getattr(session, 'context_history', [])
        current_step = getattr(session, 'current_step', 'initial_setup')
        
        if not context_history:
            next_step = 'world_setting'
            confidence = 0.8
        else:
            recent_context = ' '.join(context_history[-2:]).lower()
            
            # Determine next step based on recent conversation
            if 'done' in recent_context or 'finished' in recent_context:
                # Look for next logical step
                predictions = await self.predict_next_steps(session, {'step_id': current_step})
                if predictions:
                    return predictions[0]
            
            # Default progression
            step_order = list(self.setup_flow.keys())
            current_index = step_order.index(current_step) if current_step in step_order else 0
            
            if current_index < len(step_order) - 1:
                next_step = step_order[current_index + 1]
                confidence = 0.6
            else:
                next_step = 'final_review'
                confidence = 0.9
        
        return StepPrediction(
            step_id=next_step,
            step_name=self.setup_flow[next_step]['name'],
            confidence=confidence,
            reasons=['Natural conversation flow progression'],
            estimated_time=self.setup_flow[next_step]['estimated_time'],
            prerequisites=[],
            skip_conditions=[]
        )

    async def determine_ui_complexity(self, session) -> UIComplexityLevel:
        """Determine UI complexity based on user expertise."""
        context_history = getattr(session, 'context_history', [])
        all_context = ' '.join(context_history).lower() if context_history else ''
        
        # Score complexity indicators
        complexity_scores = {'beginner': 0, 'intermediate': 0, 'expert': 0}
        
        for level, indicators in self.complexity_indicators.items():
            for indicator in indicators:
                if indicator in all_context:
                    complexity_scores[level] += 1
        
        # Determine level
        max_score = max(complexity_scores.values())
        if max_score == 0:
            level = 'beginner'  # default for new users
        else:
            level = max(complexity_scores, key=complexity_scores.get)
        
        return UIComplexityLevel(
            level=level,
            show_advanced_options=level in ['intermediate', 'expert'],
            auto_fill_suggestions=level == 'beginner',
            step_by_step_guidance=level in ['beginner', 'intermediate'],
            quick_setup_available=level == 'expert'
        )

    async def get_relevant_options(self, session) -> List[RelevantOption]:
        """Get relevant options based on campaign style."""
        campaign_style = getattr(session, 'campaign_style', 'heroic_fantasy')
        context_history = getattr(session, 'context_history', [])
        all_context = ' '.join(context_history).lower() if context_history else ''
        
        relevant_options = []
        
        # Get base options for campaign style
        if campaign_style in self.campaign_style_options:
            base_options = self.campaign_style_options[campaign_style]
            
            for option in base_options:
                relevance_score = 0.5  # base relevance
                
                # Increase relevance based on context mentions
                option_keywords = option['description'].lower().split()
                context_matches = sum(1 for word in option_keywords if word in all_context)
                relevance_score += (context_matches / len(option_keywords)) * 0.4
                
                relevant_options.append(RelevantOption(
                    option_id=option['id'],
                    label=option['label'],
                    description=option['description'],
                    relevance_score=relevance_score,
                    category=campaign_style
                ))
        
        # Add cross-style options if they're highly relevant
        for style, options in self.campaign_style_options.items():
            if style == campaign_style:
                continue
                
            for option in options:
                option_keywords = option['description'].lower().split()
                context_matches = sum(1 for word in option_keywords if word in all_context)
                relevance_score = (context_matches / len(option_keywords)) if option_keywords else 0
                
                if relevance_score > 0.6:  # High relevance threshold for cross-style
                    relevant_options.append(RelevantOption(
                        option_id=option['id'],
                        label=option['label'],
                        description=option['description'],
                        relevance_score=relevance_score,
                        category=style
                    ))
        
        # Sort by relevance and return top options
        relevant_options.sort(key=lambda x: x.relevance_score, reverse=True)
        return relevant_options[:8]