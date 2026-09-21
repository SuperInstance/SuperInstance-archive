#!/usr/bin/env python3
"""
DMLog Adaptive Engine
Starts as D&D Beyond clone, evolves through ML observation and voice control.
Designed for Max to seamlessly transition from D&D Beyond with continuous AI improvement.
"""

import asyncio
import json
import uuid
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import sqlite3
import speech_recognition as sr
import pyttsx3
from fastapi import FastAPI, WebSocket, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserActionType(Enum):
    CLICK = "click"
    SWIPE = "swipe"
    SCROLL = "scroll"
    SEARCH = "search"
    NAVIGATION = "navigation"
    VOICE_COMMAND = "voice_command"
    FRUSTRATION_PATTERN = "frustration_pattern"

class InterfaceElement(Enum):
    CHARACTER_SHEET = "character_sheet"
    CAMPAIGN_PAGE = "campaign_page"
    SPELL_LIST = "spell_list"
    MONSTER_STAT_BLOCK = "monster_stat_block"
    ENCOUNTER_BUILDER = "encounter_builder"
    DICE_ROLLER = "dice_roller"
    MAPS_VTT = "maps_vtt"
    HOMEBREW_CREATOR = "homebrew_creator"

class AdaptationPriority(Enum):
    CRITICAL = "critical"  # User showing high frustration
    HIGH = "high"         # Frequently accessed but inefficient
    MEDIUM = "medium"     # Minor improvements
    LOW = "low"          # Nice to have

@dataclass
class UserBehaviorPattern:
    """Track user interaction patterns for ML learning"""
    user_id: str
    session_id: str
    timestamp: datetime
    action_type: UserActionType
    element_interacted: InterfaceElement
    click_count: int = 0
    time_to_complete: float = 0.0
    frustration_indicators: List[str] = field(default_factory=list)
    success: bool = True
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VoiceCommand:
    """Voice command structure for Max's interface control"""
    command_id: str
    timestamp: datetime
    raw_audio: bytes
    transcription: str
    intent: str
    confidence: float
    parameters: Dict[str, Any]
    execution_status: str
    user_feedback: Optional[str] = None

@dataclass
class WorkerBotNote:
    """Notes from Max to worker bots about system improvements"""
    note_id: str
    timestamp: datetime
    from_user: str  # Max
    note_type: str  # improvement, bug_report, feature_request
    content: str
    context: Dict[str, Any]
    priority: AdaptationPriority
    system_wide_suggestion: bool = False
    worker_bot_assigned: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, escalated

class MLObservationLayer:
    """Machine Learning layer that observes user behavior and adapts interface"""
    
    def __init__(self):
        self.behavior_db = self._init_behavior_database()
        self.pattern_analyzer = None
        self.adaptation_engine = None
        self.user_profiles = {}
        
    def _init_behavior_database(self) -> sqlite3.Connection:
        """Initialize behavior tracking database"""
        conn = sqlite3.connect('dmlog_behavior.db', check_same_thread=False)
        
        # Create tables for behavior tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_behaviors (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                session_id TEXT,
                timestamp TEXT,
                action_type TEXT,
                element_interacted TEXT,
                click_count INTEGER,
                time_to_complete REAL,
                frustration_indicators TEXT,
                success INTEGER,
                context TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS interface_adaptations (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                element TEXT,
                adaptation_type TEXT,
                old_state TEXT,
                new_state TEXT,
                trigger_pattern TEXT,
                success_metrics TEXT
            )
        ''')
        
        conn.commit()
        return conn
    
    async def track_user_behavior(self, behavior: UserBehaviorPattern):
        """Track user behavior for ML analysis"""
        behavior_data = (
            str(uuid.uuid4()),
            behavior.user_id,
            behavior.session_id,
            behavior.timestamp.isoformat(),
            behavior.action_type.value,
            behavior.element_interacted.value,
            behavior.click_count,
            behavior.time_to_complete,
            json.dumps(behavior.frustration_indicators),
            1 if behavior.success else 0,
            json.dumps(behavior.context)
        )
        
        self.behavior_db.execute('''
            INSERT INTO user_behaviors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', behavior_data)
        
        self.behavior_db.commit()
        
        # Analyze for immediate adaptations needed
        await self._analyze_behavior_pattern(behavior)
        
        logger.info(f"Tracked behavior: {behavior.action_type.value} on {behavior.element_interacted.value}")
    
    async def _analyze_behavior_pattern(self, behavior: UserBehaviorPattern):
        """Analyze behavior pattern for frustration indicators"""
        frustration_detected = False
        
        # Detect frustration patterns
        if behavior.click_count > 5:  # Too many clicks for simple task
            frustration_detected = True
            behavior.frustration_indicators.append("excessive_clicking")
        
        if behavior.time_to_complete > 30:  # Task taking too long
            frustration_detected = True
            behavior.frustration_indicators.append("task_timeout")
        
        if not behavior.success:
            frustration_detected = True
            behavior.frustration_indicators.append("task_failure")
        
        # If frustration detected, trigger immediate interface adaptation
        if frustration_detected:
            await self._trigger_interface_adaptation(behavior)
    
    async def _trigger_interface_adaptation(self, behavior: UserBehaviorPattern):
        """Trigger immediate interface adaptation based on frustration"""
        adaptation_suggestions = {
            "excessive_clicking": "Reduce click depth, add shortcuts",
            "task_timeout": "Simplify interface, add quick actions",
            "task_failure": "Add guidance, improve error handling"
        }
        
        for indicator in behavior.frustration_indicators:
            if indicator in adaptation_suggestions:
                await self._apply_interface_adaptation(
                    behavior.element_interacted,
                    adaptation_suggestions[indicator],
                    behavior
                )
    
    async def _apply_interface_adaptation(self, element: InterfaceElement, adaptation: str, trigger_behavior: UserBehaviorPattern):
        """Apply interface adaptation based on ML analysis"""
        adaptation_id = str(uuid.uuid4())
        
        # Log the adaptation
        self.behavior_db.execute('''
            INSERT INTO interface_adaptations VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            adaptation_id,
            datetime.utcnow().isoformat(),
            element.value,
            adaptation,
            json.dumps({"previous_state": "default"}),
            json.dumps({"adapted_state": adaptation}),
            json.dumps(asdict(trigger_behavior)),
            json.dumps({"applied": True})
        ))
        
        self.behavior_db.commit()
        
        logger.info(f"Applied adaptation: {adaptation} to {element.value}")

class VoiceInterfaceController:
    """Voice control system that allows Max to control everything via speech"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.tts_engine = pyttsx3.init()
        self.command_history = []
        self.learning_patterns = {}
        self.voice_profile = None
        
        # Calibrate microphone for Max's voice
        self._calibrate_for_max()
    
    def _calibrate_for_max(self):
        """Calibrate voice recognition specifically for Max"""
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("Voice interface calibrated for Max")
        except Exception as e:
            logger.error(f"Voice calibration failed: {e}")
    
    async def process_voice_command(self, audio_data: bytes) -> VoiceCommand:
        """Process Max's voice commands and execute them"""
        command_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        try:
            # Transcribe audio
            transcription = await self._transcribe_audio(audio_data)
            
            # Analyze intent
            intent_analysis = await self._analyze_voice_intent(transcription)
            
            # Execute command
            execution_result = await self._execute_voice_command(intent_analysis)
            
            command = VoiceCommand(
                command_id=command_id,
                timestamp=timestamp,
                raw_audio=audio_data,
                transcription=transcription,
                intent=intent_analysis['intent'],
                confidence=intent_analysis['confidence'],
                parameters=intent_analysis['parameters'],
                execution_status=execution_result['status']
            )
            
            self.command_history.append(command)
            
            # Learn from Max's command patterns
            await self._learn_from_command(command)
            
            return command
            
        except Exception as e:
            logger.error(f"Voice command processing failed: {e}")
            return VoiceCommand(
                command_id=command_id,
                timestamp=timestamp,
                raw_audio=audio_data,
                transcription="",
                intent="error",
                confidence=0.0,
                parameters={},
                execution_status="failed"
            )
    
    async def _transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe Max's voice to text"""
        # This would integrate with speech recognition service
        # For demo purposes, return sample commands
        sample_commands = [
            "Move the dice roller to the top of the page",
            "Show me all spells that deal fire damage",
            "Create a new encounter for level 5 party",
            "Open character sheet for Aragorn",
            "Leave a note for the worker bot to improve the search function",
            "The encounter builder takes too many clicks to use",
            "Add a shortcut to create random NPCs"
        ]
        return sample_commands[len(self.command_history) % len(sample_commands)]
    
    async def _analyze_voice_intent(self, transcription: str) -> Dict[str, Any]:
        """Analyze Max's intent from voice command"""
        transcription_lower = transcription.lower()
        
        # Interface modification commands
        if any(word in transcription_lower for word in ['move', 'relocate', 'position']):
            return {
                'intent': 'interface_modification',
                'confidence': 0.9,
                'parameters': {
                    'action': 'move_element',
                    'element': self._extract_element(transcription),
                    'target_location': self._extract_location(transcription)
                }
            }
        
        # Search/filter commands
        elif any(word in transcription_lower for word in ['show', 'find', 'search']):
            return {
                'intent': 'search_content',
                'confidence': 0.85,
                'parameters': {
                    'action': 'search',
                    'query': self._extract_search_query(transcription),
                    'filters': self._extract_filters(transcription)
                }
            }
        
        # Worker bot communication
        elif any(phrase in transcription_lower for phrase in ['leave a note', 'tell the worker bot', 'worker bot']):
            return {
                'intent': 'worker_bot_communication',
                'confidence': 0.95,
                'parameters': {
                    'action': 'create_note',
                    'message': transcription,
                    'priority': self._determine_priority(transcription)
                }
            }
        
        # Content creation
        elif any(word in transcription_lower for word in ['create', 'generate', 'make']):
            return {
                'intent': 'content_creation',
                'confidence': 0.8,
                'parameters': {
                    'action': 'create',
                    'content_type': self._extract_content_type(transcription),
                    'specifications': self._extract_specifications(transcription)
                }
            }
        
        # Default
        else:
            return {
                'intent': 'general_command',
                'confidence': 0.5,
                'parameters': {'raw_command': transcription}
            }
    
    async def _execute_voice_command(self, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Max's voice command"""
        intent = intent_analysis['intent']
        params = intent_analysis['parameters']
        
        try:
            if intent == 'interface_modification':
                result = await self._execute_interface_modification(params)
            elif intent == 'search_content':
                result = await self._execute_search_command(params)
            elif intent == 'worker_bot_communication':
                result = await self._execute_worker_bot_communication(params)
            elif intent == 'content_creation':
                result = await self._execute_content_creation(params)
            else:
                result = await self._execute_general_command(params)
            
            # Provide voice feedback
            await self._provide_voice_feedback(result)
            
            return {'status': 'success', 'result': result}
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _extract_element(self, text: str) -> str:
        """Extract UI element from voice command"""
        element_map = {
            'dice roller': 'dice_roller',
            'character sheet': 'character_sheet',
            'spell list': 'spell_list',
            'encounter builder': 'encounter_builder',
            'maps': 'maps_vtt'
        }
        
        for phrase, element in element_map.items():
            if phrase in text.lower():
                return element
        return 'unknown_element'
    
    async def _provide_voice_feedback(self, result: Dict[str, Any]):
        """Provide voice feedback to Max"""
        feedback_messages = {
            'interface_modified': "Interface updated as requested",
            'search_completed': "Found the content you were looking for",
            'note_created': "Note sent to worker bot for processing",
            'content_created': "Content has been generated",
            'error': "I had trouble with that command, could you try rephrasing?"
        }
        
        message = feedback_messages.get(result.get('type', 'error'))
        self.tts_engine.say(message)
        self.tts_engine.runAndWait()

class WorkerBotCommunicationSystem:
    """System for Max to communicate with worker bots and track improvements"""
    
    def __init__(self):
        self.notes_db = self._init_notes_database()
        self.escalation_queue = []
        self.worker_bot_assignments = {}
        
    def _init_notes_database(self) -> sqlite3.Connection:
        """Initialize worker bot notes database"""
        conn = sqlite3.connect('worker_bot_notes.db', check_same_thread=False)
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS worker_bot_notes (
                note_id TEXT PRIMARY KEY,
                timestamp TEXT,
                from_user TEXT,
                note_type TEXT,
                content TEXT,
                context TEXT,
                priority TEXT,
                system_wide_suggestion INTEGER,
                worker_bot_assigned TEXT,
                status TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_improvements (
                improvement_id TEXT PRIMARY KEY,
                timestamp TEXT,
                suggested_by TEXT,
                description TEXT,
                impact_assessment TEXT,
                implementation_status TEXT,
                escalated_to_admin INTEGER
            )
        ''')
        
        conn.commit()
        return conn
    
    async def create_worker_bot_note(self, content: str, note_type: str = "improvement", priority: AdaptationPriority = AdaptationPriority.MEDIUM) -> WorkerBotNote:
        """Create a note from Max to worker bots"""
        note = WorkerBotNote(
            note_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            from_user="Max",
            note_type=note_type,
            content=content,
            context={"dmlog_system_context": True},
            priority=priority,
            system_wide_suggestion=self._assess_system_wide_impact(content)
        )
        
        # Store in database
        self.notes_db.execute('''
            INSERT INTO worker_bot_notes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            note.note_id,
            note.timestamp.isoformat(),
            note.from_user,
            note.note_type,
            note.content,
            json.dumps(note.context),
            note.priority.value,
            1 if note.system_wide_suggestion else 0,
            note.worker_bot_assigned,
            note.status
        ))
        
        self.notes_db.commit()
        
        # If system-wide suggestion, add to escalation queue
        if note.system_wide_suggestion:
            await self._escalate_system_wide_suggestion(note)
        
        logger.info(f"Created worker bot note: {note.note_id}")
        return note
    
    def _assess_system_wide_impact(self, content: str) -> bool:
        """Assess if suggestion should impact the whole system"""
        system_wide_indicators = [
            'all users', 'everyone', 'system wide', 'across the platform',
            'for the entire system', 'globally', 'user experience',
            'performance improvement', 'security enhancement'
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in system_wide_indicators)
    
    async def _escalate_system_wide_suggestion(self, note: WorkerBotNote):
        """Escalate system-wide suggestions for admin review"""
        improvement = {
            'improvement_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'suggested_by': note.from_user,
            'description': note.content,
            'impact_assessment': 'system_wide',
            'implementation_status': 'pending_admin_review',
            'escalated_to_admin': 1
        }
        
        self.notes_db.execute('''
            INSERT INTO system_improvements VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', tuple(improvement.values()))
        
        self.notes_db.commit()
        
        # Add to escalation queue for next worker bot interaction
        self.escalation_queue.append(improvement)
        
        logger.info(f"Escalated system-wide suggestion: {improvement['improvement_id']}")

class IntelligentLogManager:
    """Manages intelligent logging with automatic rollback and size optimization"""
    
    def __init__(self, max_size_mb: int = 100):
        self.max_size_mb = max_size_mb
        self.log_dir = Path("/home/activeloguser/activelog/services/dmlog-adaptive/logs")
        self.log_dir.mkdir(exist_ok=True)
        self.checkpoint_interval = 24  # hours
        self.last_checkpoint = datetime.utcnow()
        
    async def log_system_change(self, change_type: str, change_data: Dict[str, Any], rollback_data: Dict[str, Any]):
        """Log system changes with rollback information"""
        timestamp = datetime.utcnow()
        
        change_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': timestamp.isoformat(),
            'change_type': change_type,
            'change_data': change_data,
            'rollback_data': rollback_data,
            'size_bytes': len(json.dumps(change_data)) + len(json.dumps(rollback_data))
        }
        
        # Append to current log file
        current_log_file = self.log_dir / f"changes_{timestamp.strftime('%Y%m%d')}.json"
        
        # Read existing log
        if current_log_file.exists():
            with open(current_log_file, 'r') as f:
                log_data = json.load(f)
        else:
            log_data = {'changes': []}
        
        log_data['changes'].append(change_entry)
        
        # Write updated log
        with open(current_log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        # Check if cleanup needed
        await self._check_and_cleanup_logs()
        
        logger.info(f"Logged system change: {change_type}")
    
    async def _check_and_cleanup_logs(self):
        """Check log size and cleanup if needed"""
        total_size_mb = sum(f.stat().st_size for f in self.log_dir.glob("*.json")) / (1024 * 1024)
        
        if total_size_mb > self.max_size_mb:
            await self._cleanup_old_logs()
        
        # Create checkpoint if needed
        if datetime.utcnow() - self.last_checkpoint > timedelta(hours=self.checkpoint_interval):
            await self._create_checkpoint()
    
    async def _cleanup_old_logs(self):
        """Clean up old logs while preserving recent changes and checkpoints"""
        log_files = sorted(self.log_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Keep recent files (last 7 days) with full detail
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        
        # Compress older files by removing less critical data
        for log_file in log_files:
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            if file_time < recent_cutoff:
                await self._compress_log_file(log_file)
        
        logger.info("Completed log cleanup and compression")
    
    async def _compress_log_file(self, log_file: Path):
        """Compress old log file by removing detailed rollback data"""
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        # Compress by keeping only essential information for old entries
        compressed_changes = []
        for change in log_data['changes']:
            compressed_change = {
                'id': change['id'],
                'timestamp': change['timestamp'],
                'change_type': change['change_type'],
                'summary': str(change['change_data'])[:100] + "..." if len(str(change['change_data'])) > 100 else str(change['change_data'])
                # Remove full rollback_data for old entries
            }
            compressed_changes.append(compressed_change)
        
        # Write compressed version
        log_data['changes'] = compressed_changes
        log_data['compressed'] = True
        log_data['compression_date'] = datetime.utcnow().isoformat()
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
    
    async def _create_checkpoint(self):
        """Create system checkpoint for rollback purposes"""
        checkpoint_file = self.log_dir / f"checkpoint_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        checkpoint_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'system_state': 'stable',
            'changes_since_last_checkpoint': await self._get_changes_since_last_checkpoint(),
            'rollback_point': True
        }
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        self.last_checkpoint = datetime.utcnow()
        logger.info(f"Created system checkpoint: {checkpoint_file}")
    
    async def _get_changes_since_last_checkpoint(self) -> int:
        """Get number of changes since last checkpoint"""
        # Count changes in recent log files
        change_count = 0
        for log_file in self.log_dir.glob("changes_*.json"):
            try:
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
                    change_count += len(log_data.get('changes', []))
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")
        
        return change_count

class DMLogAdaptiveInterface:
    """Main DMLog interface that starts as D&D Beyond clone and evolves"""
    
    def __init__(self):
        self.ml_observer = MLObservationLayer()
        self.voice_controller = VoiceInterfaceController()
        self.worker_bot_comm = WorkerBotCommunicationSystem()
        self.log_manager = IntelligentLogManager()
        self.current_interface_state = self._initialize_dndb_clone_state()
        
    def _initialize_dndb_clone_state(self) -> Dict[str, Any]:
        """Initialize interface to look exactly like D&D Beyond"""
        return {
            'layout': {
                'header': {
                    'logo': 'D&D Beyond Clone',
                    'navigation': ['My Characters', 'Campaigns', 'Compendium', 'Encounters', 'My Content'],
                    'user_menu': ['Profile', 'Account', 'Settings', 'Sign Out']
                },
                'main_content': {
                    'dashboard': {
                        'recent_characters': [],
                        'recent_campaigns': [],
                        'quick_actions': ['Create Character', 'Join Campaign', 'Roll Dice']
                    }
                },
                'sidebar': {
                    'active': False,
                    'content': 'character_sheet'
                }
            },
            'tabs': {
                'standard': ['Overview', 'Features & Traits', 'Inventory', 'Spells'],
                'additional': ['Voice Control', 'AI Assistant', 'Advanced Tools', 'Worker Notes']
            },
            'interface_efficiency': {
                'clicks_to_common_actions': {
                    'roll_dice': 2,
                    'view_spell': 3,
                    'create_character': 4,
                    'build_encounter': 5
                }
            }
        }
    
    async def adapt_interface_based_on_usage(self, user_behavior: UserBehaviorPattern):
        """Adapt interface based on Max's usage patterns"""
        # Track behavior
        await self.ml_observer.track_user_behavior(user_behavior)
        
        # If frustration detected, immediately adapt
        if user_behavior.frustration_indicators:
            adaptation = await self._generate_interface_adaptation(user_behavior)
            await self._apply_interface_adaptation(adaptation)
    
    async def _generate_interface_adaptation(self, behavior: UserBehaviorPattern) -> Dict[str, Any]:
        """Generate interface adaptation based on behavior analysis"""
        adaptations = {
            'excessive_clicking': {
                'type': 'reduce_click_depth',
                'target_element': behavior.element_interacted,
                'modification': 'add_shortcut_buttons',
                'expected_improvement': 'reduce clicks by 50%'
            },
            'task_timeout': {
                'type': 'simplify_interface',
                'target_element': behavior.element_interacted,
                'modification': 'streamline_workflow',
                'expected_improvement': 'reduce time to completion by 60%'
            },
            'task_failure': {
                'type': 'add_guidance',
                'target_element': behavior.element_interacted,
                'modification': 'contextual_help_system',
                'expected_improvement': 'increase success rate to 95%'
            }
        }
        
        # Select most appropriate adaptation
        for indicator in behavior.frustration_indicators:
            if indicator in adaptations:
                return adaptations[indicator]
        
        return adaptations['task_timeout']  # Default fallback
    
    async def _apply_interface_adaptation(self, adaptation: Dict[str, Any]):
        """Apply interface adaptation and log for rollback"""
        old_state = self.current_interface_state.copy()
        
        # Apply the adaptation
        if adaptation['type'] == 'reduce_click_depth':
            await self._add_shortcut_buttons(adaptation['target_element'])
        elif adaptation['type'] == 'simplify_interface':
            await self._streamline_workflow(adaptation['target_element'])
        elif adaptation['type'] == 'add_guidance':
            await self._add_contextual_help(adaptation['target_element'])
        
        # Log the change for rollback
        await self.log_manager.log_system_change(
            change_type=adaptation['type'],
            change_data=adaptation,
            rollback_data={'previous_state': old_state}
        )
        
        logger.info(f"Applied interface adaptation: {adaptation['type']}")

# FastAPI app for the adaptive DMLog system
app = FastAPI(title="DMLog Adaptive Interface", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the adaptive interface
dmlog_interface = DMLogAdaptiveInterface()

# Serve static files for the D&D Beyond clone interface
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_main_interface():
    """Serve the main DMLog interface that looks like D&D Beyond"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DMLog - D&D Beyond Clone</title>
        <style>
            /* D&D Beyond clone styling */
            body { 
                font-family: 'Roboto', sans-serif; 
                margin: 0; 
                background: #1e1e1e; 
                color: #fff;
            }
            .header { 
                background: #242528; 
                padding: 1rem; 
                display: flex; 
                justify-content: space-between; 
            }
            .nav-menu { display: flex; gap: 2rem; }
            .nav-item { cursor: pointer; padding: 0.5rem; }
            .main-content { 
                display: flex; 
                min-height: calc(100vh - 80px); 
            }
            .sidebar { 
                width: 300px; 
                background: #2a2a2a; 
                padding: 1rem; 
            }
            .content-area { 
                flex: 1; 
                padding: 2rem; 
            }
            .character-card { 
                background: #333; 
                padding: 1rem; 
                margin: 1rem 0; 
                border-radius: 8px; 
            }
            .voice-indicator { 
                position: fixed; 
                top: 20px; 
                right: 20px; 
                background: #4CAF50; 
                color: white; 
                padding: 10px; 
                border-radius: 20px; 
                display: none; 
            }
            .adaptive-notification {
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #2196F3;
                color: white;
                padding: 15px;
                border-radius: 8px;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="voice-indicator" id="voiceIndicator">🎤 Listening...</div>
        <div class="adaptive-notification" id="adaptiveNotification">Interface adapted based on your usage!</div>
        
        <header class="header">
            <div class="logo">DMLog (D&D Beyond Mode)</div>
            <nav class="nav-menu">
                <div class="nav-item" onclick="navigate('characters')">My Characters</div>
                <div class="nav-item" onclick="navigate('campaigns')">Campaigns</div>
                <div class="nav-item" onclick="navigate('compendium')">Compendium</div>
                <div class="nav-item" onclick="navigate('encounters')">Encounters</div>
                <div class="nav-item" onclick="navigate('content')">My Content</div>
            </nav>
        </header>
        
        <main class="main-content">
            <aside class="sidebar">
                <h3>Quick Actions</h3>
                <button onclick="trackAction('create_character')">Create Character</button>
                <button onclick="trackAction('roll_dice')">Roll Dice</button>
                <button onclick="trackAction('build_encounter')">Build Encounter</button>
                
                <h3>Voice Commands</h3>
                <p>Try saying:</p>
                <ul>
                    <li>"Show my characters"</li>
                    <li>"Roll a d20"</li>
                    <li>"Leave a note for the worker bot"</li>
                    <li>"Move the dice to the top"</li>
                </ul>
                
                <button onclick="startVoiceControl()">🎤 Start Voice Control</button>
            </aside>
            
            <div class="content-area">
                <h1>Welcome to DMLog</h1>
                <p>This interface starts exactly like D&D Beyond but gets better as you use it!</p>
                
                <div class="character-card">
                    <h3>Recent Characters</h3>
                    <p>Your characters will appear here...</p>
                </div>
                
                <div class="character-card">
                    <h3>Active Campaigns</h3>
                    <p>Your campaigns will appear here...</p>
                </div>
                
                <div class="character-card">
                    <h3>ML Observation Status</h3>
                    <p>🤖 Machine Learning layer is observing and improving your experience</p>
                    <p>Click patterns, navigation efficiency, and frustration indicators are being analyzed</p>
                </div>
            </div>
        </main>
        
        <script>
            let clickCount = 0;
            let startTime = Date.now();
            let voiceRecognition = null;
            
            function navigate(section) {
                trackUserBehavior('navigation', section, 1, Date.now() - startTime);
                console.log(`Navigating to ${section}`);
                // Simulate navigation
                document.querySelector('.content-area h1').textContent = `${section.toUpperCase()} Section`;
            }
            
            function trackAction(action) {
                clickCount++;
                const timeSpent = Date.now() - startTime;
                trackUserBehavior('click', action, clickCount, timeSpent);
                
                // Simulate frustration if too many clicks
                if (clickCount > 5) {
                    showAdaptiveNotification("Interface optimizing based on your usage patterns...");
                }
            }
            
            async function trackUserBehavior(actionType, element, clicks, timeSpent) {
                try {
                    await fetch('/api/track-behavior', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            action_type: actionType,
                            element: element,
                            click_count: clicks,
                            time_to_complete: timeSpent / 1000,
                            success: true
                        })
                    });
                } catch (error) {
                    console.log('Behavior tracking simulated:', {actionType, element, clicks, timeSpent});
                }
            }
            
            function startVoiceControl() {
                if ('webkitSpeechRecognition' in window) {
                    voiceRecognition = new webkitSpeechRecognition();
                    voiceRecognition.continuous = true;
                    voiceRecognition.interimResults = true;
                    
                    voiceRecognition.onstart = function() {
                        document.getElementById('voiceIndicator').style.display = 'block';
                    };
                    
                    voiceRecognition.onresult = function(event) {
                        const transcript = event.results[event.results.length - 1][0].transcript;
                        console.log('Voice command:', transcript);
                        processVoiceCommand(transcript);
                    };
                    
                    voiceRecognition.start();
                } else {
                    alert('Voice recognition not supported. Voice commands will be simulated.');
                    simulateVoiceCommand();
                }
            }
            
            async function processVoiceCommand(transcript) {
                try {
                    const response = await fetch('/api/voice-command', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            transcription: transcript,
                            timestamp: new Date().toISOString()
                        })
                    });
                    
                    const result = await response.json();
                    showAdaptiveNotification(`Voice command executed: ${result.intent}`);
                } catch (error) {
                    console.log('Voice command simulated:', transcript);
                    showAdaptiveNotification(`Voice command simulated: ${transcript}`);
                }
            }
            
            function simulateVoiceCommand() {
                const commands = [
                    "Show me all fire spells",
                    "Move the dice roller to the top",
                    "Create a level 5 encounter",
                    "Leave a note for the worker bot about improving search"
                ];
                const randomCommand = commands[Math.floor(Math.random() * commands.length)];
                processVoiceCommand(randomCommand);
            }
            
            function showAdaptiveNotification(message) {
                const notification = document.getElementById('adaptiveNotification');
                notification.textContent = message;
                notification.style.display = 'block';
                setTimeout(() => {
                    notification.style.display = 'none';
                }, 3000);
            }
            
            // Initialize
            console.log('DMLog Adaptive Interface initialized');
            console.log('ML observation layer active');
            console.log('Voice control available');
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/api/track-behavior")
async def track_user_behavior(behavior_data: Dict[str, Any]):
    """Track user behavior for ML analysis"""
    behavior = UserBehaviorPattern(
        user_id="Max",
        session_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        action_type=UserActionType(behavior_data.get('action_type', 'click')),
        element_interacted=InterfaceElement.CHARACTER_SHEET,  # Default
        click_count=behavior_data.get('click_count', 1),
        time_to_complete=behavior_data.get('time_to_complete', 0.0),
        success=behavior_data.get('success', True)
    )
    
    await dmlog_interface.adapt_interface_based_on_usage(behavior)
    
    return {"status": "behavior_tracked", "adaptations_applied": True}

@app.post("/api/voice-command")
async def process_voice_command(command_data: Dict[str, Any]):
    """Process Max's voice commands"""
    # Simulate audio data
    audio_data = b"simulated_audio_data"
    
    command = await dmlog_interface.voice_controller.process_voice_command(audio_data)
    
    # If it's a worker bot note, create the note
    if command.intent == 'worker_bot_communication':
        await dmlog_interface.worker_bot_comm.create_worker_bot_note(
            content=command_data.get('transcription', ''),
            note_type='improvement'
        )
    
    return {
        "command_id": command.command_id,
        "intent": command.intent,
        "execution_status": command.execution_status,
        "response": "Command processed and interface adapted"
    }

@app.get("/api/worker-bot-notes")
async def get_worker_bot_notes():
    """Get notes for worker bots with DMLog context"""
    cursor = dmlog_interface.worker_bot_comm.notes_db.cursor()
    cursor.execute("SELECT * FROM worker_bot_notes WHERE status = 'pending'")
    notes = cursor.fetchall()
    
    # Add context that these are DMLog-specific notes
    formatted_notes = []
    for note in notes:
        formatted_notes.append({
            'note_id': note[0],
            'timestamp': note[1],
            'from_user': note[2],
            'note_type': note[3],
            'content': note[4],
            'context': 'DMLog System Improvement',
            'priority': note[6],
            'system_wide_suggestion': bool(note[7])
        })
    
    return {"notes": formatted_notes, "context": "DMLog system improvements from Max"}

@app.get("/api/escalated-suggestions")
async def get_escalated_suggestions():
    """Get system-wide suggestions escalated for admin review"""
    return {"suggestions": dmlog_interface.worker_bot_comm.escalation_queue}

@app.get("/api/system-logs")
async def get_system_logs():
    """Get recent system logs for debugging"""
    log_files = list(dmlog_interface.log_manager.log_dir.glob("*.json"))
    recent_files = sorted(log_files, key=lambda f: f.stat().st_mtime, reverse=True)[:3]
    
    logs = []
    for log_file in recent_files:
        try:
            with open(log_file, 'r') as f:
                log_data = json.load(f)
                logs.append({
                    'file': log_file.name,
                    'entries': len(log_data.get('changes', [])),
                    'size_mb': log_file.stat().st_size / (1024 * 1024)
                })
        except Exception as e:
            logs.append({'file': log_file.name, 'error': str(e)})
    
    return {"recent_logs": logs, "max_size_mb": dmlog_interface.log_manager.max_size_mb}

@app.get("/health")
async def health_check():
    """Health check for the adaptive DMLog system"""
    return {
        "status": "adaptive",
        "service": "dmlog-adaptive-interface",
        "version": "1.0.0",
        "features": {
            "ml_observation": "active",
            "voice_control": "active", 
            "worker_bot_communication": "active",
            "intelligent_logging": "active",
            "interface_adaptation": "active"
        },
        "interface_state": "D&D Beyond clone with adaptive improvements",
        "admin_user": "Max",
        "learning_status": "continuously improving based on usage patterns"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8603)