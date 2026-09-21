#!/usr/bin/env python3
"""
Preference Transfer Manager for ActiveLog Migration Service
Handles user preference migration and synchronization between applications
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class PreferenceCategory(Enum):
    """Categories of user preferences"""
    APPEARANCE = "appearance"
    NOTIFICATIONS = "notifications"
    PRIVACY = "privacy"
    ACCESSIBILITY = "accessibility"
    WORKFLOW = "workflow"
    INTEGRATIONS = "integrations"
    DISPLAY = "display"
    BEHAVIOR = "behavior"
    SECURITY = "security"
    ADVANCED = "advanced"


class PreferenceType(Enum):
    """Types of preference values"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    COLOR = "color"
    ENUM = "enum"


class TransferStrategy(Enum):
    """Preference transfer strategies"""
    DIRECT_MAP = "direct_map"
    SMART_MAP = "smart_map"
    DEFAULT_VALUE = "default_value"
    USER_PROMPT = "user_prompt"
    SKIP = "skip"


@dataclass
class PreferenceDefinition:
    """Definition of a preference setting"""
    key: str
    category: PreferenceCategory
    preference_type: PreferenceType
    default_value: Any
    description: str
    possible_values: Optional[List[Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    app_specific: bool = False
    sensitive: bool = False


@dataclass
class PreferenceMapping:
    """Mapping between source and target preferences"""
    source_key: str
    target_key: str
    source_app: str
    target_app: str
    strategy: TransferStrategy
    transformer_function: Optional[str] = None
    confidence_score: float = 1.0
    requires_validation: bool = False


@dataclass
class TransferResult:
    """Result of preference transfer"""
    preference_key: str
    source_value: Any
    target_value: Any
    strategy_used: TransferStrategy
    success: bool
    warning_message: Optional[str] = None
    error_message: Optional[str] = None


class PreferenceManager:
    """Manages user preference transfers between applications"""
    
    def __init__(self, config):
        self.config = config
        self.preference_definitions = {}
        self.preference_mappings = {}
        self.transfer_history = {}
        
        # Initialize preference definitions for each app
        self._initialize_preference_definitions()
        
        # Initialize preference mappings between apps
        self._initialize_preference_mappings()
        
        logger.info("PreferenceManager initialized")
    
    def transfer_preferences(self, user_id: str, source_app: str, target_app: str) -> Dict[str, Any]:
        """Transfer user preferences between applications"""
        try:
            # Get current preferences from source app
            source_preferences = self._get_user_preferences(user_id, source_app)
            
            if not source_preferences:
                return {
                    'success': True,
                    'message': 'No preferences to transfer',
                    'transferred_preferences': {},
                    'transfer_summary': {
                        'total_preferences': 0,
                        'successfully_transferred': 0,
                        'failed_transfers': 0,
                        'skipped_preferences': 0,
                        'warnings': []
                    }
                }
            
            # Get existing preferences from target app
            target_preferences = self._get_user_preferences(user_id, target_app) or {}
            
            # Execute preference transfer
            transfer_results = self._execute_preference_transfer(
                user_id, source_app, target_app, source_preferences, target_preferences
            )
            
            # Apply transferred preferences to target app
            self._apply_preferences_to_target(user_id, target_app, transfer_results)
            
            # Generate transfer summary
            transfer_summary = self._generate_transfer_summary(transfer_results)
            
            # Store transfer record
            transfer_record_id = f"pref_transfer_{uuid.uuid4().hex[:8]}"
            self.transfer_history[transfer_record_id] = {
                'transfer_id': transfer_record_id,
                'user_id': user_id,
                'source_app': source_app,
                'target_app': target_app,
                'transfer_results': transfer_results,
                'transfer_summary': transfer_summary,
                'timestamp': datetime.utcnow()
            }
            
            logger.info(f"Preferences transferred for user {user_id}: {source_app} -> {target_app}")
            
            return {
                'success': True,
                'transfer_id': transfer_record_id,
                'source_app': source_app,
                'target_app': target_app,
                'transferred_preferences': {
                    result.preference_key: result.target_value 
                    for result in transfer_results 
                    if result.success
                },
                'transfer_summary': transfer_summary,
                'recommendations': self._get_post_transfer_recommendations(
                    target_app, transfer_results
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to transfer preferences: {e}")
            return {
                'success': False,
                'error': str(e),
                'transferred_preferences': {}
            }
    
    def get_preference_compatibility(self, source_app: str, target_app: str) -> Dict[str, Any]:
        """Get preference compatibility analysis between apps"""
        try:
            source_prefs = self.preference_definitions.get(source_app, {})
            target_prefs = self.preference_definitions.get(target_app, {})
            
            compatibility_analysis = {
                'source_app': source_app,
                'target_app': target_app,
                'total_source_preferences': len(source_prefs),
                'total_target_preferences': len(target_prefs),
                'direct_mappings': 0,
                'smart_mappings': 0,
                'unmappable_preferences': 0,
                'compatibility_score': 0.0,
                'preference_analysis': []
            }
            
            mapping_key = (source_app, target_app)
            mappings = self.preference_mappings.get(mapping_key, {})
            
            for source_key, source_pref in source_prefs.items():
                analysis_item = {
                    'source_preference': source_key,
                    'category': source_pref.category.value,
                    'type': source_pref.preference_type.value,
                    'mappable': False,
                    'target_preference': None,
                    'strategy': None,
                    'confidence': 0.0
                }
                
                if source_key in mappings:
                    mapping = mappings[source_key]
                    analysis_item.update({
                        'mappable': True,
                        'target_preference': mapping.target_key,
                        'strategy': mapping.strategy.value,
                        'confidence': mapping.confidence_score
                    })
                    
                    if mapping.strategy == TransferStrategy.DIRECT_MAP:
                        compatibility_analysis['direct_mappings'] += 1
                    elif mapping.strategy == TransferStrategy.SMART_MAP:
                        compatibility_analysis['smart_mappings'] += 1
                else:
                    compatibility_analysis['unmappable_preferences'] += 1
                
                compatibility_analysis['preference_analysis'].append(analysis_item)
            
            # Calculate compatibility score
            mappable_prefs = compatibility_analysis['direct_mappings'] + compatibility_analysis['smart_mappings']
            total_prefs = compatibility_analysis['total_source_preferences']
            compatibility_analysis['compatibility_score'] = (mappable_prefs / total_prefs * 100) if total_prefs > 0 else 0
            
            return compatibility_analysis
            
        except Exception as e:
            logger.error(f"Failed to get preference compatibility: {e}")
            return {'error': str(e)}
    
    def _initialize_preference_definitions(self):
        """Initialize preference definitions for all apps"""
        
        # ActiveLog Core preferences
        self.preference_definitions['activelog-core'] = {
            'theme': PreferenceDefinition(
                key='theme',
                category=PreferenceCategory.APPEARANCE,
                preference_type=PreferenceType.ENUM,
                default_value='light',
                description='Application color theme',
                possible_values=['light', 'dark', 'auto']
            ),
            'notifications_enabled': PreferenceDefinition(
                key='notifications_enabled',
                category=PreferenceCategory.NOTIFICATIONS,
                preference_type=PreferenceType.BOOLEAN,
                default_value=True,
                description='Enable push notifications'
            ),
            'entries_per_page': PreferenceDefinition(
                key='entries_per_page',
                category=PreferenceCategory.DISPLAY,
                preference_type=PreferenceType.INTEGER,
                default_value=25,
                description='Number of entries to display per page',
                possible_values=[10, 25, 50, 100]
            ),
            'auto_save_interval': PreferenceDefinition(
                key='auto_save_interval',
                category=PreferenceCategory.BEHAVIOR,
                preference_type=PreferenceType.INTEGER,
                default_value=30,
                description='Auto-save interval in seconds'
            ),
            'default_privacy_level': PreferenceDefinition(
                key='default_privacy_level',
                category=PreferenceCategory.PRIVACY,
                preference_type=PreferenceType.ENUM,
                default_value='private',
                description='Default privacy level for new entries',
                possible_values=['private', 'friends', 'public']
            )
        }
        
        # StudyLog preferences
        self.preference_definitions['studylog'] = {
            'study_theme': PreferenceDefinition(
                key='study_theme',
                category=PreferenceCategory.APPEARANCE,
                preference_type=PreferenceType.ENUM,
                default_value='focus',
                description='Study interface theme',
                possible_values=['focus', 'minimal', 'colorful', 'dark']
            ),
            'study_reminders': PreferenceDefinition(
                key='study_reminders',
                category=PreferenceCategory.NOTIFICATIONS,
                preference_type=PreferenceType.BOOLEAN,
                default_value=True,
                description='Enable study session reminders'
            ),
            'sessions_per_page': PreferenceDefinition(
                key='sessions_per_page',
                category=PreferenceCategory.DISPLAY,
                preference_type=PreferenceType.INTEGER,
                default_value=20,
                description='Study sessions per page'
            ),
            'pomodoro_duration': PreferenceDefinition(
                key='pomodoro_duration',
                category=PreferenceCategory.WORKFLOW,
                preference_type=PreferenceType.INTEGER,
                default_value=25,
                description='Pomodoro timer duration in minutes'
            ),
            'progress_sharing': PreferenceDefinition(
                key='progress_sharing',
                category=PreferenceCategory.PRIVACY,
                preference_type=PreferenceType.ENUM,
                default_value='private',
                description='Study progress sharing level',
                possible_values=['private', 'study_group', 'public']
            )
        }
        
        # BusinessLog preferences
        self.preference_definitions['businesslog'] = {
            'business_theme': PreferenceDefinition(
                key='business_theme',
                category=PreferenceCategory.APPEARANCE,
                preference_type=PreferenceType.ENUM,
                default_value='professional',
                description='Business interface theme',
                possible_values=['professional', 'modern', 'classic', 'dark']
            ),
            'meeting_notifications': PreferenceDefinition(
                key='meeting_notifications',
                category=PreferenceCategory.NOTIFICATIONS,
                preference_type=PreferenceType.BOOLEAN,
                default_value=True,
                description='Enable meeting and deadline notifications'
            ),
            'activities_per_page': PreferenceDefinition(
                key='activities_per_page',
                category=PreferenceCategory.DISPLAY,
                preference_type=PreferenceType.INTEGER,
                default_value=30,
                description='Business activities per page'
            ),
            'working_hours_start': PreferenceDefinition(
                key='working_hours_start',
                category=PreferenceCategory.WORKFLOW,
                preference_type=PreferenceType.INTEGER,
                default_value=9,
                description='Working hours start time (24h format)'
            ),
            'working_hours_end': PreferenceDefinition(
                key='working_hours_end',
                category=PreferenceCategory.WORKFLOW,
                preference_type=PreferenceType.INTEGER,
                default_value=17,
                description='Working hours end time (24h format)'
            ),
            'data_sharing_level': PreferenceDefinition(
                key='data_sharing_level',
                category=PreferenceCategory.PRIVACY,
                preference_type=PreferenceType.ENUM,
                default_value='team',
                description='Business data sharing level',
                possible_values=['private', 'team', 'department', 'company']
            )
        }
        
        # MakerLog preferences
        self.preference_definitions['makerlog'] = {
            'maker_theme': PreferenceDefinition(
                key='maker_theme',
                category=PreferenceCategory.APPEARANCE,
                preference_type=PreferenceType.ENUM,
                default_value='creative',
                description='Maker interface theme',
                possible_values=['creative', 'minimal', 'vibrant', 'dark']
            ),
            'project_notifications': PreferenceDefinition(
                key='project_notifications',
                category=PreferenceCategory.NOTIFICATIONS,
                preference_type=PreferenceType.BOOLEAN,
                default_value=True,
                description='Enable project milestone notifications'
            ),
            'projects_per_page': PreferenceDefinition(
                key='projects_per_page',
                category=PreferenceCategory.DISPLAY,
                preference_type=PreferenceType.INTEGER,
                default_value=15,
                description='Projects displayed per page'
            ),
            'showcase_privacy': PreferenceDefinition(
                key='showcase_privacy',
                category=PreferenceCategory.PRIVACY,
                preference_type=PreferenceType.ENUM,
                default_value='community',
                description='Project showcase privacy level',
                possible_values=['private', 'friends', 'community', 'public']
            )
        }
        
        # DMLog preferences
        self.preference_definitions['dmlog'] = {
            'dm_theme': PreferenceDefinition(
                key='dm_theme',
                category=PreferenceCategory.APPEARANCE,
                preference_type=PreferenceType.ENUM,
                default_value='fantasy',
                description='DM interface theme',
                possible_values=['fantasy', 'modern', 'classic', 'dark']
            ),
            'session_reminders': PreferenceDefinition(
                key='session_reminders',
                category=PreferenceCategory.NOTIFICATIONS,
                preference_type=PreferenceType.BOOLEAN,
                default_value=True,
                description='Enable D&D session reminders'
            ),
            'campaigns_per_page': PreferenceDefinition(
                key='campaigns_per_page',
                category=PreferenceCategory.DISPLAY,
                preference_type=PreferenceType.INTEGER,
                default_value=10,
                description='Campaigns displayed per page'
            ),
            'dice_sound_enabled': PreferenceDefinition(
                key='dice_sound_enabled',
                category=PreferenceCategory.BEHAVIOR,
                preference_type=PreferenceType.BOOLEAN,
                default_value=True,
                description='Enable dice rolling sound effects',
                app_specific=True
            ),
            'campaign_privacy': PreferenceDefinition(
                key='campaign_privacy',
                category=PreferenceCategory.PRIVACY,
                preference_type=PreferenceType.ENUM,
                default_value='players_only',
                description='Campaign data privacy level',
                possible_values=['private', 'players_only', 'dm_network', 'public']
            )
        }
    
    def _initialize_preference_mappings(self):
        """Initialize preference mappings between apps"""
        
        # ActiveLog Core to StudyLog
        self.preference_mappings[('activelog-core', 'studylog')] = {
            'theme': PreferenceMapping(
                source_key='theme',
                target_key='study_theme',
                source_app='activelog-core',
                target_app='studylog',
                strategy=TransferStrategy.SMART_MAP,
                transformer_function='transform_theme_to_study',
                confidence_score=0.85
            ),
            'notifications_enabled': PreferenceMapping(
                source_key='notifications_enabled',
                target_key='study_reminders',
                source_app='activelog-core',
                target_app='studylog',
                strategy=TransferStrategy.DIRECT_MAP,
                confidence_score=1.0
            ),
            'entries_per_page': PreferenceMapping(
                source_key='entries_per_page',
                target_key='sessions_per_page',
                source_app='activelog-core',
                target_app='studylog',
                strategy=TransferStrategy.SMART_MAP,
                transformer_function='adjust_page_size',
                confidence_score=0.9
            ),
            'default_privacy_level': PreferenceMapping(
                source_key='default_privacy_level',
                target_key='progress_sharing',
                source_app='activelog-core',
                target_app='studylog',
                strategy=TransferStrategy.SMART_MAP,
                transformer_function='map_privacy_levels',
                confidence_score=0.8
            )
        }
        
        # ActiveLog Core to BusinessLog
        self.preference_mappings[('activelog-core', 'businesslog')] = {
            'theme': PreferenceMapping(
                source_key='theme',
                target_key='business_theme',
                source_app='activelog-core',
                target_app='businesslog',
                strategy=TransferStrategy.SMART_MAP,
                transformer_function='transform_theme_to_business',
                confidence_score=0.85
            ),
            'notifications_enabled': PreferenceMapping(
                source_key='notifications_enabled',
                target_key='meeting_notifications',
                source_app='activelog-core',
                target_app='businesslog',
                strategy=TransferStrategy.DIRECT_MAP,
                confidence_score=1.0
            ),
            'entries_per_page': PreferenceMapping(
                source_key='entries_per_page',
                target_key='activities_per_page',
                source_app='activelog-core',
                target_app='businesslog',
                strategy=TransferStrategy.SMART_MAP,
                transformer_function='adjust_business_page_size',
                confidence_score=0.9
            ),
            'default_privacy_level': PreferenceMapping(
                source_key='default_privacy_level',
                target_key='data_sharing_level',
                source_app='activelog-core',
                target_app='businesslog',
                strategy=TransferStrategy.SMART_MAP,
                transformer_function='map_business_privacy_levels',
                confidence_score=0.75
            )
        }
        
        # StudyLog to BusinessLog
        self.preference_mappings[('studylog', 'businesslog')] = {
            'study_theme': PreferenceMapping(
                source_key='study_theme',
                target_key='business_theme',
                source_app='studylog',
                target_app='businesslog',
                strategy=TransferStrategy.SMART_MAP,
                transformer_function='transform_study_to_business_theme',
                confidence_score=0.7
            ),
            'study_reminders': PreferenceMapping(
                source_key='study_reminders',
                target_key='meeting_notifications',
                source_app='studylog',
                target_app='businesslog',
                strategy=TransferStrategy.DIRECT_MAP,
                confidence_score=0.9
            ),
            'sessions_per_page': PreferenceMapping(
                source_key='sessions_per_page',
                target_key='activities_per_page',
                source_app='studylog',
                target_app='businesslog',
                strategy=TransferStrategy.SMART_MAP,
                transformer_function='convert_sessions_to_activities_page_size',
                confidence_score=0.85
            )
        }
        
        # Add more mappings for other app combinations...
    
    def _get_user_preferences(self, user_id: str, app_id: str) -> Optional[Dict[str, Any]]:
        """Get user preferences for specific app"""
        # Simulate getting preferences from database
        if app_id == 'activelog-core':
            return {
                'theme': 'dark',
                'notifications_enabled': True,
                'entries_per_page': 50,
                'auto_save_interval': 60,
                'default_privacy_level': 'private'
            }
        elif app_id == 'studylog':
            return {
                'study_theme': 'focus',
                'study_reminders': True,
                'sessions_per_page': 20,
                'pomodoro_duration': 25,
                'progress_sharing': 'private'
            }
        elif app_id == 'businesslog':
            return {
                'business_theme': 'professional',
                'meeting_notifications': True,
                'activities_per_page': 30,
                'working_hours_start': 9,
                'working_hours_end': 17,
                'data_sharing_level': 'team'
            }
        else:
            return {}
    
    def _execute_preference_transfer(self, user_id: str, source_app: str, target_app: str,
                                   source_preferences: Dict[str, Any], 
                                   target_preferences: Dict[str, Any]) -> List[TransferResult]:
        """Execute the preference transfer process"""
        transfer_results = []
        mapping_key = (source_app, target_app)
        mappings = self.preference_mappings.get(mapping_key, {})
        
        for source_key, source_value in source_preferences.items():
            if source_key in mappings:
                mapping = mappings[source_key]
                result = self._transfer_single_preference(
                    source_key, source_value, mapping, target_preferences
                )
            else:
                # Handle unmapped preferences
                result = self._handle_unmapped_preference(
                    source_key, source_value, source_app, target_app
                )
            
            transfer_results.append(result)
        
        return transfer_results
    
    def _transfer_single_preference(self, source_key: str, source_value: Any,
                                  mapping: PreferenceMapping, 
                                  target_preferences: Dict[str, Any]) -> TransferResult:
        """Transfer a single preference using its mapping"""
        try:
            if mapping.strategy == TransferStrategy.DIRECT_MAP:
                target_value = source_value
            elif mapping.strategy == TransferStrategy.SMART_MAP:
                target_value = self._apply_transformation(
                    source_value, mapping.transformer_function, mapping
                )
            elif mapping.strategy == TransferStrategy.DEFAULT_VALUE:
                target_value = self._get_default_value(mapping.target_key, mapping.target_app)
            else:
                return TransferResult(
                    preference_key=source_key,
                    source_value=source_value,
                    target_value=None,
                    strategy_used=mapping.strategy,
                    success=False,
                    error_message=f"Unsupported transfer strategy: {mapping.strategy.value}"
                )
            
            # Validate target value
            validation_result = self._validate_preference_value(
                mapping.target_key, target_value, mapping.target_app
            )
            
            if not validation_result['valid']:
                return TransferResult(
                    preference_key=source_key,
                    source_value=source_value,
                    target_value=None,
                    strategy_used=mapping.strategy,
                    success=False,
                    error_message=f"Validation failed: {validation_result['error']}"
                )
            
            # Check for conflicts with existing target preferences
            warning_message = None
            if mapping.target_key in target_preferences:
                existing_value = target_preferences[mapping.target_key]
                if existing_value != target_value:
                    warning_message = f"Overriding existing value '{existing_value}' with '{target_value}'"
            
            return TransferResult(
                preference_key=mapping.target_key,
                source_value=source_value,
                target_value=target_value,
                strategy_used=mapping.strategy,
                success=True,
                warning_message=warning_message
            )
            
        except Exception as e:
            logger.error(f"Failed to transfer preference {source_key}: {e}")
            return TransferResult(
                preference_key=source_key,
                source_value=source_value,
                target_value=None,
                strategy_used=mapping.strategy,
                success=False,
                error_message=str(e)
            )
    
    def _handle_unmapped_preference(self, source_key: str, source_value: Any,
                                  source_app: str, target_app: str) -> TransferResult:
        """Handle preferences that don't have explicit mappings"""
        # Check if target app has the same preference key
        target_preferences = self.preference_definitions.get(target_app, {})
        
        if source_key in target_preferences:
            # Direct transfer if same key exists in target
            validation_result = self._validate_preference_value(source_key, source_value, target_app)
            
            if validation_result['valid']:
                return TransferResult(
                    preference_key=source_key,
                    source_value=source_value,
                    target_value=source_value,
                    strategy_used=TransferStrategy.DIRECT_MAP,
                    success=True
                )
            else:
                # Use default value if validation fails
                default_value = self._get_default_value(source_key, target_app)
                return TransferResult(
                    preference_key=source_key,
                    source_value=source_value,
                    target_value=default_value,
                    strategy_used=TransferStrategy.DEFAULT_VALUE,
                    success=True,
                    warning_message=f"Used default value due to validation failure: {validation_result['error']}"
                )
        else:
            # Skip unmappable preferences
            return TransferResult(
                preference_key=source_key,
                source_value=source_value,
                target_value=None,
                strategy_used=TransferStrategy.SKIP,
                success=False,
                warning_message=f"No mapping found for preference '{source_key}' in target app '{target_app}'"
            )
    
    def _apply_transformation(self, source_value: Any, transformer_function: str,
                            mapping: PreferenceMapping) -> Any:
        """Apply transformation function to convert preference values"""
        try:
            if transformer_function == 'transform_theme_to_study':
                theme_mapping = {'light': 'minimal', 'dark': 'focus', 'auto': 'focus'}
                return theme_mapping.get(source_value, 'focus')
            
            elif transformer_function == 'transform_theme_to_business':
                theme_mapping = {'light': 'professional', 'dark': 'modern', 'auto': 'professional'}
                return theme_mapping.get(source_value, 'professional')
            
            elif transformer_function == 'adjust_page_size':
                # Convert entries per page to sessions per page with adjustment
                if isinstance(source_value, int):
                    return max(10, min(50, int(source_value * 0.8)))  # Reduce by 20%
                return 20
            
            elif transformer_function == 'adjust_business_page_size':
                # Convert entries per page to activities per page with adjustment
                if isinstance(source_value, int):
                    return max(15, min(100, int(source_value * 1.2)))  # Increase by 20%
                return 30
            
            elif transformer_function == 'map_privacy_levels':
                privacy_mapping = {
                    'private': 'private',
                    'friends': 'study_group',
                    'public': 'public'
                }
                return privacy_mapping.get(source_value, 'private')
            
            elif transformer_function == 'map_business_privacy_levels':
                privacy_mapping = {
                    'private': 'private',
                    'friends': 'team',
                    'public': 'company'
                }
                return privacy_mapping.get(source_value, 'team')
            
            else:
                logger.warning(f"Unknown transformer function: {transformer_function}")
                return source_value
                
        except Exception as e:
            logger.error(f"Transformation failed: {transformer_function}, Error: {e}")
            return self._get_default_value(mapping.target_key, mapping.target_app)
    
    def _validate_preference_value(self, preference_key: str, value: Any, app_id: str) -> Dict[str, Any]:
        """Validate preference value against its definition"""
        app_preferences = self.preference_definitions.get(app_id, {})
        
        if preference_key not in app_preferences:
            return {'valid': False, 'error': f'Unknown preference: {preference_key}'}
        
        pref_def = app_preferences[preference_key]
        
        # Type validation
        if pref_def.preference_type == PreferenceType.BOOLEAN and not isinstance(value, bool):
            return {'valid': False, 'error': f'Expected boolean, got {type(value).__name__}'}
        
        elif pref_def.preference_type == PreferenceType.INTEGER and not isinstance(value, int):
            return {'valid': False, 'error': f'Expected integer, got {type(value).__name__}'}
        
        elif pref_def.preference_type == PreferenceType.STRING and not isinstance(value, str):
            return {'valid': False, 'error': f'Expected string, got {type(value).__name__}'}
        
        elif pref_def.preference_type == PreferenceType.FLOAT and not isinstance(value, (int, float)):
            return {'valid': False, 'error': f'Expected number, got {type(value).__name__}'}
        
        # Value validation
        if pref_def.possible_values and value not in pref_def.possible_values:
            return {
                'valid': False, 
                'error': f'Value {value} not in allowed values: {pref_def.possible_values}'
            }
        
        return {'valid': True}
    
    def _get_default_value(self, preference_key: str, app_id: str) -> Any:
        """Get default value for a preference"""
        app_preferences = self.preference_definitions.get(app_id, {})
        if preference_key in app_preferences:
            return app_preferences[preference_key].default_value
        return None
    
    def _apply_preferences_to_target(self, user_id: str, target_app: str, 
                                   transfer_results: List[TransferResult]):
        """Apply successfully transferred preferences to target app"""
        successful_preferences = {
            result.preference_key: result.target_value
            for result in transfer_results
            if result.success and result.target_value is not None
        }
        
        if successful_preferences:
            # In production, this would update the user's preferences in the target app's database
            logger.info(f"Applied {len(successful_preferences)} preferences to {target_app} for user {user_id}")
    
    def _generate_transfer_summary(self, transfer_results: List[TransferResult]) -> Dict[str, Any]:
        """Generate summary of preference transfer results"""
        total_preferences = len(transfer_results)
        successful_transfers = sum(1 for result in transfer_results if result.success)
        failed_transfers = sum(1 for result in transfer_results if not result.success)
        skipped_preferences = sum(1 for result in transfer_results 
                                if result.strategy_used == TransferStrategy.SKIP)
        
        warnings = [result.warning_message for result in transfer_results 
                   if result.warning_message]
        errors = [result.error_message for result in transfer_results 
                 if result.error_message]
        
        return {
            'total_preferences': total_preferences,
            'successfully_transferred': successful_transfers,
            'failed_transfers': failed_transfers,
            'skipped_preferences': skipped_preferences,
            'success_rate': (successful_transfers / total_preferences * 100) if total_preferences > 0 else 0,
            'warnings': warnings,
            'errors': errors,
            'strategies_used': {
                strategy.value: sum(1 for result in transfer_results 
                                   if result.strategy_used == strategy)
                for strategy in TransferStrategy
            }
        }
    
    def _get_post_transfer_recommendations(self, target_app: str, 
                                         transfer_results: List[TransferResult]) -> List[Dict[str, Any]]:
        """Get recommendations after preference transfer"""
        recommendations = []
        
        # Check for failed transfers
        failed_transfers = [result for result in transfer_results if not result.success]
        if failed_transfers:
            recommendations.append({
                'type': 'review_required',
                'title': 'Review failed preference transfers',
                'description': f'{len(failed_transfers)} preferences could not be transferred automatically',
                'action': 'Review and manually set these preferences in your new app'
            })
        
        # Check for default value usage
        default_value_usage = sum(1 for result in transfer_results 
                                if result.strategy_used == TransferStrategy.DEFAULT_VALUE)
        if default_value_usage > 0:
            recommendations.append({
                'type': 'customization',
                'title': 'Customize default settings',
                'description': f'{default_value_usage} preferences were set to default values',
                'action': 'Consider customizing these settings to match your workflow'
            })
        
        # App-specific recommendations
        if target_app == 'studylog':
            recommendations.append({
                'type': 'feature_discovery',
                'title': 'Explore StudyLog features',
                'description': 'Configure study-specific settings like Pomodoro timers and progress tracking',
                'action': 'Visit Settings > Study Preferences to customize your learning experience'
            })
        elif target_app == 'businesslog':
            recommendations.append({
                'type': 'feature_discovery',
                'title': 'Set up business workflow',
                'description': 'Configure working hours, team collaboration, and notification preferences',
                'action': 'Visit Settings > Business Preferences to optimize your productivity'
            })
        
        return recommendations
    
    def get_preference_transfer_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's preference transfer history"""
        user_transfers = []
        
        for transfer_id, transfer_data in self.transfer_history.items():
            if transfer_data['user_id'] == user_id:
                summary_data = {
                    'transfer_id': transfer_id,
                    'source_app': transfer_data['source_app'],
                    'target_app': transfer_data['target_app'],
                    'timestamp': transfer_data['timestamp'].isoformat(),
                    'summary': transfer_data['transfer_summary']
                }
                user_transfers.append(summary_data)
        
        # Sort by timestamp, most recent first
        user_transfers.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return user_transfers
    
    def sync_preferences_across_apps(self, user_id: str, preference_keys: List[str]) -> Dict[str, Any]:
        """Sync specific preferences across all user's active apps"""
        try:
            # Get user's active apps (simulated)
            active_apps = ['activelog-core', 'studylog', 'businesslog']  # Would be fetched from database
            
            sync_results = {}
            sync_errors = []
            
            for source_app in active_apps:
                source_preferences = self._get_user_preferences(user_id, source_app)
                if not source_preferences:
                    continue
                
                for target_app in active_apps:
                    if source_app == target_app:
                        continue
                    
                    # Sync specific preferences
                    preferences_to_sync = {
                        key: value for key, value in source_preferences.items()
                        if key in preference_keys
                    }
                    
                    if preferences_to_sync:
                        try:
                            sync_result = self._execute_preference_transfer(
                                user_id, source_app, target_app, preferences_to_sync, {}
                            )
                            sync_key = f"{source_app}_{target_app}"
                            sync_results[sync_key] = sync_result
                        except Exception as e:
                            sync_errors.append(f"Failed to sync {source_app} -> {target_app}: {str(e)}")
            
            return {
                'success': len(sync_errors) == 0,
                'synced_preferences': preference_keys,
                'sync_results': sync_results,
                'errors': sync_errors
            }
            
        except Exception as e:
            logger.error(f"Failed to sync preferences: {e}")
            return {'success': False, 'error': str(e)}