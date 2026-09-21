"""
Voice Control System
Comprehensive voice control for all ActiveLog applications
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class VoiceCommandType(Enum):
    NAVIGATION = "navigation"
    ACTION = "action"
    DICTATION = "dictation"
    FORM_CONTROL = "form_control"
    SYSTEM = "system"
    APPLICATION = "application"

class VoiceRecognitionEngine(Enum):
    WEB_SPEECH_API = "web_speech_api"
    SPEECH_RECOGNITION = "speech_recognition"  # Python library
    AZURE_SPEECH = "azure_speech"
    GOOGLE_SPEECH = "google_speech"
    AWS_TRANSCRIBE = "aws_transcribe"
    WHISPER = "whisper"

class CommandState(Enum):
    LISTENING = "listening"
    PROCESSING = "processing"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class VoiceCommand:
    command_id: str
    patterns: List[str]  # Regex patterns or phrases
    action: str
    command_type: VoiceCommandType
    description: str
    examples: List[str]
    enabled: bool = True
    confidence_threshold: float = 0.7
    context: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.command_id:
            self.command_id = str(uuid.uuid4())
        if self.parameters is None:
            self.parameters = {}
    
    def matches(self, text: str, confidence: float = 1.0) -> bool:
        """Check if spoken text matches this command"""
        if not self.enabled or confidence < self.confidence_threshold:
            return False
        
        text_lower = text.lower().strip()
        
        for pattern in self.patterns:
            # Simple phrase matching
            if pattern.lower() in text_lower:
                return True
            
            # Regex pattern matching
            try:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return True
            except re.error:
                continue
        
        return False
    
    def extract_parameters(self, text: str) -> Dict[str, Any]:
        """Extract parameters from spoken text"""
        params = {}
        text_lower = text.lower().strip()
        
        # Common parameter patterns
        patterns = {
            'number': r'\b(\d+)\b',
            'text': r'"([^"]*)"',
            'direction': r'\b(up|down|left|right|forward|back|backward)\b',
            'element': r'\b(button|link|input|field|menu|dialog)\b'
        }
        
        for param_name, pattern in patterns.items():
            matches = re.findall(pattern, text_lower)
            if matches:
                params[param_name] = matches[0] if len(matches) == 1 else matches
        
        return params
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['command_type'] = self.command_type.value
        return result

@dataclass
class VoiceSession:
    session_id: str
    user_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    commands_executed: int = 0
    total_utterances: int = 0
    success_rate: float = 0.0
    language: str = "en-US"
    
    def __post_init__(self):
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
        if self.start_time is None:
            self.start_time = datetime.now(timezone.utc)
    
    def end_session(self):
        """End the voice session"""
        self.end_time = datetime.now(timezone.utc)
        if self.total_utterances > 0:
            self.success_rate = self.commands_executed / self.total_utterances
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if result.get('start_time'):
            result['start_time'] = result['start_time'].isoformat()
        if result.get('end_time'):
            result['end_time'] = result['end_time'].isoformat()
        return result

@dataclass
class VoiceUtterance:
    utterance_id: str
    session_id: str
    text: str
    confidence: float
    timestamp: datetime
    matched_command: Optional[str] = None
    executed_action: Optional[str] = None
    state: CommandState = CommandState.PROCESSING
    processing_time_ms: Optional[float] = None
    
    def __post_init__(self):
        if not self.utterance_id:
            self.utterance_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['state'] = self.state.value
        return result

class VoiceControlManager:
    """Main voice control system manager"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.commands: Dict[str, VoiceCommand] = {}
        self.sessions: Dict[str, VoiceSession] = {}
        self.current_session: Optional[VoiceSession] = None
        
        # Voice recognition settings
        self.recognition_engine = VoiceRecognitionEngine(
            self.config.get('recognition_engine', 'web_speech_api')
        )
        self.language = self.config.get('language', 'en-US')
        self.continuous = self.config.get('continuous', True)
        self.interim_results = self.config.get('interim_results', True)
        
        # Command handlers
        self.command_handlers: Dict[str, Callable] = {}
        
        # Recognition state
        self.is_listening = False
        self.is_processing = False
        
        # Initialize default commands
        self._setup_default_commands()
    
    def _setup_default_commands(self):
        """Setup default voice commands"""
        default_commands = [
            # Navigation commands
            VoiceCommand(
                command_id="scroll-up",
                patterns=["scroll up", "page up", "go up"],
                action="scroll_up",
                command_type=VoiceCommandType.NAVIGATION,
                description="Scroll page up",
                examples=["scroll up", "page up"]
            ),
            
            VoiceCommand(
                command_id="scroll-down", 
                patterns=["scroll down", "page down", "go down"],
                action="scroll_down",
                command_type=VoiceCommandType.NAVIGATION,
                description="Scroll page down",
                examples=["scroll down", "page down"]
            ),
            
            VoiceCommand(
                command_id="go-back",
                patterns=["go back", "back", "previous page"],
                action="go_back",
                command_type=VoiceCommandType.NAVIGATION,
                description="Navigate back",
                examples=["go back", "back"]
            ),
            
            VoiceCommand(
                command_id="go-forward",
                patterns=["go forward", "forward", "next page"],
                action="go_forward",
                command_type=VoiceCommandType.NAVIGATION,
                description="Navigate forward",
                examples=["go forward", "forward"]
            ),
            
            VoiceCommand(
                command_id="go-home",
                patterns=["go home", "home", "go to home"],
                action="go_home",
                command_type=VoiceCommandType.NAVIGATION,
                description="Go to home page",
                examples=["go home", "home"]
            ),
            
            # Action commands
            VoiceCommand(
                command_id="click",
                patterns=[r"click (\w+)", "click", "select"],
                action="click_element",
                command_type=VoiceCommandType.ACTION,
                description="Click element",
                examples=["click button", "click link", "click"]
            ),
            
            VoiceCommand(
                command_id="submit",
                patterns=["submit", "submit form", "send"],
                action="submit_form",
                command_type=VoiceCommandType.ACTION,
                description="Submit form",
                examples=["submit", "submit form"]
            ),
            
            VoiceCommand(
                command_id="save",
                patterns=["save", "save document", "save file"],
                action="save",
                command_type=VoiceCommandType.ACTION,
                description="Save current document",
                examples=["save", "save document"]
            ),
            
            # Form control commands
            VoiceCommand(
                command_id="focus-field",
                patterns=[r"focus (\w+)", r"go to (\w+)", "next field"],
                action="focus_field",
                command_type=VoiceCommandType.FORM_CONTROL,
                description="Focus form field",
                examples=["focus name", "go to email", "next field"]
            ),
            
            VoiceCommand(
                command_id="clear-field",
                patterns=["clear", "clear field", "delete all"],
                action="clear_field",
                command_type=VoiceCommandType.FORM_CONTROL,
                description="Clear current field",
                examples=["clear", "clear field"]
            ),
            
            # System commands
            VoiceCommand(
                command_id="help",
                patterns=["help", "show help", "what can I say"],
                action="show_help",
                command_type=VoiceCommandType.SYSTEM,
                description="Show voice commands help",
                examples=["help", "what can I say"]
            ),
            
            VoiceCommand(
                command_id="stop-listening",
                patterns=["stop listening", "voice off", "disable voice"],
                action="stop_listening",
                command_type=VoiceCommandType.SYSTEM,
                description="Stop voice recognition",
                examples=["stop listening", "voice off"]
            ),
            
            VoiceCommand(
                command_id="start-dictation",
                patterns=["start dictation", "dictate", "begin dictation"],
                action="start_dictation",
                command_type=VoiceCommandType.DICTATION,
                description="Start dictation mode",
                examples=["start dictation", "dictate"]
            ),
            
            VoiceCommand(
                command_id="stop-dictation",
                patterns=["stop dictation", "end dictation"],
                action="stop_dictation", 
                command_type=VoiceCommandType.DICTATION,
                description="Stop dictation mode",
                examples=["stop dictation", "end dictation"]
            )
        ]
        
        for command in default_commands:
            self.commands[command.command_id] = command
    
    def start_session(self, user_id: Optional[str] = None) -> VoiceSession:
        """Start a new voice control session"""
        session = VoiceSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            language=self.language
        )
        
        self.sessions[session.session_id] = session
        self.current_session = session
        
        logger.info(f"Started voice session: {session.session_id}")
        return session
    
    def end_session(self, session_id: Optional[str] = None):
        """End voice control session"""
        session = None
        if session_id:
            session = self.sessions.get(session_id)
        elif self.current_session:
            session = self.current_session
        
        if session:
            session.end_session()
            if self.current_session and self.current_session.session_id == session.session_id:
                self.current_session = None
            
            logger.info(f"Ended voice session: {session.session_id} (Success rate: {session.success_rate:.2f})")
    
    def register_command(self, command: VoiceCommand) -> bool:
        """Register a voice command"""
        try:
            self.commands[command.command_id] = command
            logger.info(f"Registered voice command: {command.command_id} -> {command.action}")
            return True
        except Exception as e:
            logger.error(f"Failed to register command {command.command_id}: {e}")
            return False
    
    def unregister_command(self, command_id: str) -> bool:
        """Unregister a voice command"""
        if command_id in self.commands:
            del self.commands[command_id]
            logger.info(f"Unregistered voice command: {command_id}")
            return True
        return False
    
    def register_command_handler(self, action: str, handler: Callable):
        """Register handler for command action"""
        self.command_handlers[action] = handler
        logger.info(f"Registered command handler for action: {action}")
    
    def process_utterance(self, text: str, confidence: float = 1.0) -> Optional[VoiceUtterance]:
        """Process voice utterance and execute matching command"""
        if not self.current_session:
            self.start_session()
        
        # Create utterance record
        utterance = VoiceUtterance(
            utterance_id=str(uuid.uuid4()),
            session_id=self.current_session.session_id,
            text=text,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc)
        )
        
        start_time = datetime.now()
        
        try:
            # Update session stats
            self.current_session.total_utterances += 1
            
            # Find matching command
            matched_command = self._find_matching_command(text, confidence)
            
            if matched_command:
                utterance.matched_command = matched_command.command_id
                utterance.executed_action = matched_command.action
                
                # Extract parameters
                parameters = matched_command.extract_parameters(text)
                
                # Execute command
                success = self._execute_command(matched_command, parameters, text)
                
                if success:
                    utterance.state = CommandState.EXECUTED
                    self.current_session.commands_executed += 1
                    logger.info(f"Executed voice command: {matched_command.action} for '{text}'")
                else:
                    utterance.state = CommandState.FAILED
                    logger.warning(f"Failed to execute voice command: {matched_command.action}")
            else:
                utterance.state = CommandState.FAILED
                logger.info(f"No matching command found for: '{text}'")
            
        except Exception as e:
            utterance.state = CommandState.FAILED
            logger.error(f"Error processing utterance: {e}")
        
        # Calculate processing time
        processing_time = datetime.now() - start_time
        utterance.processing_time_ms = processing_time.total_seconds() * 1000
        
        return utterance
    
    def _find_matching_command(self, text: str, confidence: float) -> Optional[VoiceCommand]:
        """Find command that matches the utterance"""
        best_command = None
        best_score = 0
        
        for command in self.commands.values():
            if command.matches(text, confidence):
                # Simple scoring based on pattern length and specificity
                score = sum(len(pattern) for pattern in command.patterns)
                if score > best_score:
                    best_score = score
                    best_command = command
        
        return best_command
    
    def _execute_command(self, command: VoiceCommand, parameters: Dict[str, Any], text: str) -> bool:
        """Execute a matched command"""
        try:
            # Check if we have a registered handler
            if command.action in self.command_handlers:
                return self.command_handlers[command.action](command, parameters, text)
            
            # Built-in command handlers
            return self._execute_builtin_command(command, parameters, text)
            
        except Exception as e:
            logger.error(f"Error executing command {command.action}: {e}")
            return False
    
    def _execute_builtin_command(self, command: VoiceCommand, parameters: Dict[str, Any], text: str) -> bool:
        """Execute built-in commands"""
        action = command.action
        
        if action == "show_help":
            self._show_voice_help()
            return True
        elif action == "stop_listening":
            self.stop_listening()
            return True
        elif action == "start_dictation":
            self._start_dictation_mode()
            return True
        elif action == "stop_dictation":
            self._stop_dictation_mode()
            return True
        
        # For other actions, we need handlers to be registered
        logger.warning(f"No handler registered for action: {action}")
        return False
    
    def start_listening(self) -> bool:
        """Start voice recognition"""
        if self.is_listening:
            return True
        
        try:
            self.is_listening = True
            if not self.current_session:
                self.start_session()
            
            logger.info("Started voice recognition")
            return True
        except Exception as e:
            logger.error(f"Failed to start voice recognition: {e}")
            self.is_listening = False
            return False
    
    def stop_listening(self) -> bool:
        """Stop voice recognition"""
        if not self.is_listening:
            return True
        
        try:
            self.is_listening = False
            logger.info("Stopped voice recognition")
            return True
        except Exception as e:
            logger.error(f"Failed to stop voice recognition: {e}")
            return False
    
    def _start_dictation_mode(self):
        """Start dictation mode"""
        logger.info("Started dictation mode")
        # In dictation mode, we would pass through speech as text
        # rather than trying to match commands
    
    def _stop_dictation_mode(self):
        """Stop dictation mode"""
        logger.info("Stopped dictation mode")
    
    def _show_voice_help(self):
        """Show available voice commands"""
        logger.info("Showing voice command help")
        # This would trigger UI to show help dialog
    
    def get_available_commands(self, command_type: Optional[VoiceCommandType] = None,
                              context: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of available voice commands"""
        commands = []
        
        for command in self.commands.values():
            if not command.enabled:
                continue
            
            if command_type and command.command_type != command_type:
                continue
            
            if context and command.context and command.context != context:
                continue
            
            commands.append(command.to_dict())
        
        # Sort by command type and then by description
        commands.sort(key=lambda x: (x['command_type'], x['description']))
        return commands
    
    def get_command_help_text(self) -> str:
        """Generate help text for voice commands"""
        commands = self.get_available_commands()
        
        help_sections = {}
        for command in commands:
            cmd_type = command['command_type']
            if cmd_type not in help_sections:
                help_sections[cmd_type] = []
            
            help_sections[cmd_type].append({
                'examples': command['examples'],
                'description': command['description']
            })
        
        help_text = ["Available Voice Commands:", ""]
        
        type_names = {
            'navigation': 'Navigation',
            'action': 'Actions',
            'form_control': 'Form Control',
            'dictation': 'Dictation',
            'system': 'System',
            'application': 'Application'
        }
        
        for cmd_type, commands in help_sections.items():
            section_name = type_names.get(cmd_type, cmd_type.title())
            help_text.append(f"{section_name}:")
            
            for command in commands:
                examples = ", ".join(command['examples'][:2])  # Show first 2 examples
                help_text.append(f"  • \"{examples}\" - {command['description']}")
            
            help_text.append("")
        
        return "\n".join(help_text)
    
    def get_session_stats(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get session statistics"""
        session = None
        if session_id:
            session = self.sessions.get(session_id)
        elif self.current_session:
            session = self.current_session
        
        if not session:
            return None
        
        stats = session.to_dict()
        
        # Add additional computed stats
        if session.start_time and session.end_time:
            duration = session.end_time - session.start_time
            stats['duration_minutes'] = duration.total_seconds() / 60
        elif session.start_time:
            duration = datetime.now(timezone.utc) - session.start_time
            stats['duration_minutes'] = duration.total_seconds() / 60
        
        return stats
    
    def generate_voice_config(self) -> Dict[str, Any]:
        """Generate configuration for voice recognition"""
        return {
            'recognition_engine': self.recognition_engine.value,
            'language': self.language,
            'continuous': self.continuous,
            'interim_results': self.interim_results,
            'commands_count': len(self.commands),
            'enabled_commands': len([c for c in self.commands.values() if c.enabled]),
            'is_listening': self.is_listening,
            'current_session': self.current_session.session_id if self.current_session else None
        }

class VoiceControlDatabase:
    """Database for voice control sessions and usage analytics"""
    
    def __init__(self, db_path: str = "voice_control.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    commands_executed INTEGER DEFAULT 0,
                    total_utterances INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    language TEXT DEFAULT 'en-US'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_utterances (
                    utterance_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    matched_command TEXT,
                    executed_action TEXT,
                    state TEXT NOT NULL,
                    processing_time_ms REAL,
                    FOREIGN KEY (session_id) REFERENCES voice_sessions (session_id)
                )
            """)

async def main():
    """Example usage of voice control system"""
    
    # Initialize voice control manager
    voice_manager = VoiceControlManager({
        'recognition_engine': 'web_speech_api',
        'language': 'en-US',
        'continuous': True
    })
    
    print("=== Voice Control System Demo ===")
    
    # Start voice session
    session = voice_manager.start_session("demo_user")
    print(f"Started voice session: {session.session_id}")
    
    # Start listening
    voice_manager.start_listening()
    print(f"Voice recognition started: {voice_manager.is_listening}")
    
    # Simulate voice commands
    test_utterances = [
        ("scroll down", 0.9),
        ("click button", 0.8),
        ("go home", 0.95),
        ("help", 1.0),
        ("unknown command", 0.7),
        ("submit form", 0.85)
    ]
    
    print(f"\nProcessing {len(test_utterances)} voice utterances:")
    
    for text, confidence in test_utterances:
        utterance = voice_manager.process_utterance(text, confidence)
        if utterance:
            print(f"'{text}' -> {utterance.state.value} ({utterance.processing_time_ms:.1f}ms)")
    
    # Register custom command
    custom_command = VoiceCommand(
        command_id="open-settings",
        patterns=["open settings", "show settings", "settings"],
        action="open_settings",
        command_type=VoiceCommandType.APPLICATION,
        description="Open application settings",
        examples=["open settings", "settings"]
    )
    
    def settings_handler(command, parameters, text):
        print(f"Opening settings (triggered by: '{text}')")
        return True
    
    voice_manager.register_command(custom_command)
    voice_manager.register_command_handler("open_settings", settings_handler)
    
    # Test custom command
    utterance = voice_manager.process_utterance("open settings", 0.9)
    print(f"Custom command result: {utterance.state.value}")
    
    # Get available commands
    commands = voice_manager.get_available_commands(VoiceCommandType.NAVIGATION)
    print(f"\nNavigation commands available: {len(commands)}")
    for cmd in commands[:3]:  # Show first 3
        print(f"  • {', '.join(cmd['examples'][:2])} - {cmd['description']}")
    
    # Generate help text
    help_text = voice_manager.get_command_help_text()
    print(f"\nGenerated help text ({len(help_text)} characters):")
    print(help_text[:300] + "..." if len(help_text) > 300 else help_text)
    
    # Get session statistics
    stats = voice_manager.get_session_stats()
    if stats:
        print(f"\nSession Statistics:")
        print(f"  • Commands executed: {stats['commands_executed']}")
        print(f"  • Total utterances: {stats['total_utterances']}")
        print(f"  • Success rate: {stats['success_rate']:.2f}")
        print(f"  • Duration: {stats.get('duration_minutes', 0):.1f} minutes")
    
    # End session
    voice_manager.end_session()
    voice_manager.stop_listening()
    print("Voice session ended")

if __name__ == "__main__":
    asyncio.run(main())