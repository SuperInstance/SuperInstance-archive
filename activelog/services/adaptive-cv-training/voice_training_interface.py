"""
Voice Training Interface
Advanced voice command processing for hands-free ML training
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import whisper
import pyaudio
import wave
import threading
import time
from collections import deque, defaultdict
import speech_recognition as sr
from dataclasses import dataclass
import sqlite3

logger = logging.getLogger(__name__)

@dataclass
class VoiceCommand:
    """Processed voice command with context"""
    raw_text: str
    command_type: str
    parameters: Dict[str, Any]
    confidence: float
    timestamp: datetime
    session_id: str
    user_id: str

class AdvancedVoiceProcessor:
    """Advanced voice processing with context awareness and learning"""
    
    def __init__(self):
        # Load Whisper model for transcription
        self.whisper_model = whisper.load_model("base")
        
        # Speech recognition fallback
        self.recognizer = sr.Recognizer()
        
        # Context-aware command patterns
        self.command_patterns = {
            # Tote/Container Setup
            'tote_assignment': [
                r'(?:that|this)\s+(?:tote|box|container|cooler|bin)\s+(?:is\s+)?(?:for|contains?)\s+(.+)',
                r'(?:the\s+)?(.+)\s+(?:go|goes)\s+in(?:to)?\s+(?:that|this)\s+(?:tote|box|container|cooler|bin)',
                r'(?:put|place)\s+(.+)\s+in(?:to)?\s+(?:that|this)\s+(?:tote|box|container|cooler|bin)',
                r'(?:left|right|port|starboard|front|back|bow|stern|center|middle)\s+(?:tote|box|container|cooler|bin)\s+(?:is\s+)?(?:for|contains?)\s+(.+)',
            ],
            
            # Species Identification/Correction
            'species_correction': [
                r'(?:that\'s|this\s+is|actually)\s+(?:a\s+)?(.+)',
                r'no[,\s]*(?:that\'s|this\s+is)\s+(?:a\s+)?(.+)',
                r'correction[:\s]*(?:that\'s|this\s+is)\s+(?:a\s+)?(.+)',
                r'wrong[,\s]*(?:it\'s|that\'s)\s+(?:a\s+)?(.+)',
            ],
            
            # Training Control
            'training_control': [
                r'(?:start|begin|commence)\s+(?:training|learning)',
                r'(?:stop|end|finish|halt)\s+(?:training|learning)',
                r'(?:pause|suspend)\s+(?:training|learning)',
                r'(?:resume|continue)\s+(?:training|learning)',
                r'(?:save|backup)\s+(?:model|progress|data)',
            ],
            
            # Quality Assessment
            'quality_assessment': [
                r'(?:good|great|excellent|perfect)\s+(?:catch|identification|prediction)',
                r'(?:bad|wrong|incorrect|poor)\s+(?:catch|identification|prediction)',
                r'(?:that\'s|this\s+is)\s+(?:correct|right|accurate)',
                r'(?:that\'s|this\s+is)\s+(?:wrong|incorrect|inaccurate)',
            ],
            
            # Environmental Context
            'environmental_context': [
                r'(?:we\'re\s+)?(?:fishing|working)\s+in\s+(.+)',
                r'(?:depth|water)\s+(?:is|at)\s+(.+)(?:\s+feet|\s+ft|\s+meters|\s+m)?',
                r'(?:weather|conditions?)\s+(?:is|are)\s+(.+)',
                r'(?:tide|tidal)\s+(?:is|conditions?)\s+(.+)',
            ],
            
            # Fishing Technique Context  
            'technique_context': [
                r'(?:using|with)\s+(.+)\s+(?:bait|lure|tackle)',
                r'(?:trolling|casting|jigging|drifting)\s+(?:with|using)?\s*(.+)?',
                r'(?:at|fishing)\s+(.+)\s+(?:depth|feet|ft)',
            ],
        }
        
        # Species vocabulary with common names and variations
        self.species_vocabulary = {
            'salmon': {
                'king_salmon': ['king', 'chinook', 'spring', 'tyee', 'blackmouth', 'big salmon'],
                'coho_salmon': ['coho', 'silver', 'silver salmon', 'silvers'],
                'pink_salmon': ['pink', 'humpy', 'humpback', 'humpies'],
                'sockeye_salmon': ['sockeye', 'red', 'red salmon', 'blueback'],
                'chum_salmon': ['chum', 'dog', 'dog salmon', 'keta'],
                'atlantic_salmon': ['atlantic', 'atlantic salmon', 'farmed salmon'],
            },
            'trout': {
                'steelhead': ['steelhead', 'steel head', 'sea run rainbow'],
                'rainbow_trout': ['rainbow', 'rainbow trout', 'bow'],
                'cutthroat_trout': ['cutthroat', 'cut throat', 'coastal cutthroat'],
                'brown_trout': ['brown', 'brown trout', 'brownie'],
                'lake_trout': ['lake', 'lake trout', 'mackinaw'],
            },
            'groundfish': {
                'halibut': ['halibut', 'barn door', 'chicken', 'flatty'],
                'lingcod': ['lingcod', 'ling cod', 'ling', 'greenling'],
                'rockfish': ['rockfish', 'rock fish', 'red snapper', 'yelloweye', 'canary'],
                'flounder': ['flounder', 'sole', 'dover sole', 'petrale'],
            },
            'shellfish': {
                'dungeness_crab': ['dungeness', 'crab', 'dungie'],
                'spot_prawns': ['prawns', 'spot prawns', 'shrimp'],
            },
            'other': {
                'tuna': ['tuna', 'albacore', 'yellowfin'],
                'cod': ['cod', 'pacific cod', 'true cod'],
                'mackerel': ['mackerel', 'pacific mackerel'],
            }
        }
        
        # Location vocabulary
        self.location_vocabulary = {
            'left': ['left', 'port', 'port side', 'starboard side'],
            'right': ['right', 'starboard', 'starboard side'],
            'front': ['front', 'bow', 'forward', 'up front'],
            'back': ['back', 'stern', 'aft', 'rear', 'behind'],
            'center': ['center', 'middle', 'central'],
            'upper': ['upper', 'top', 'above'],
            'lower': ['lower', 'bottom', 'below'],
        }
        
        # Command context tracking
        self.recent_commands = deque(maxlen=10)
        self.session_context = {}
        
        # Learning from user patterns
        self.user_patterns = defaultdict(lambda: defaultdict(int))
        self.correction_patterns = defaultdict(list)
        
    def process_audio_stream(self, audio_data: bytes, session_id: str, user_id: str) -> List[VoiceCommand]:
        """Process audio stream and extract commands"""
        commands = []
        
        try:
            # Primary transcription with Whisper
            result = self.whisper_model.transcribe(audio_data)
            text = result["text"].strip().lower()
            confidence = result.get("confidence", 0.8)  # Whisper doesn't return confidence directly
            
            if not text:
                return commands
            
            logger.info(f"Voice transcription: '{text}' (confidence: {confidence:.2f})")
            
            # Process with context awareness
            processed_commands = self._process_text_with_context(
                text, confidence, session_id, user_id
            )
            
            commands.extend(processed_commands)
            
            # Learn from user patterns
            self._learn_user_patterns(text, processed_commands, user_id)
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            
            # Fallback to speech recognition
            try:
                with sr.AudioFile(audio_data) as source:
                    audio = self.recognizer.record(source)
                    text = self.recognizer.recognize_google(audio).lower()
                    
                    processed_commands = self._process_text_with_context(
                        text, 0.6, session_id, user_id  # Lower confidence for fallback
                    )
                    commands.extend(processed_commands)
                    
            except Exception as fallback_error:
                logger.error(f"Fallback speech recognition error: {fallback_error}")
        
        return commands
    
    def _process_text_with_context(self, text: str, confidence: float, 
                                 session_id: str, user_id: str) -> List[VoiceCommand]:
        """Process text with contextual understanding"""
        commands = []
        
        # Check each command pattern
        for command_type, patterns in self.command_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    parameters = self._extract_parameters(command_type, match, text)
                    
                    if parameters:
                        command = VoiceCommand(
                            raw_text=text,
                            command_type=command_type,
                            parameters=parameters,
                            confidence=confidence,
                            timestamp=datetime.now(),
                            session_id=session_id,
                            user_id=user_id
                        )
                        commands.append(command)
                        
                        # Update context
                        self._update_session_context(session_id, command)
                        break
        
        # Store for context
        self.recent_commands.append({
            'text': text,
            'timestamp': datetime.now(),
            'session_id': session_id,
            'user_id': user_id
        })
        
        return commands
    
    def _extract_parameters(self, command_type: str, match: re.Match, full_text: str) -> Dict[str, Any]:
        """Extract parameters based on command type"""
        parameters = {}
        
        if command_type == 'tote_assignment':
            # Extract species
            species_text = match.group(1) if match.groups() else ""
            species = self._resolve_species(species_text)
            if species:
                parameters['species'] = species
                parameters['original_species_text'] = species_text
            
            # Extract location from full text
            location = self._extract_location(full_text)
            if location:
                parameters['location'] = location
                
        elif command_type == 'species_correction':
            species_text = match.group(1) if match.groups() else ""
            species = self._resolve_species(species_text)
            if species:
                parameters['correct_species'] = species
                parameters['original_species_text'] = species_text
                
        elif command_type == 'training_control':
            if 'start' in full_text or 'begin' in full_text:
                parameters['action'] = 'start'
            elif 'stop' in full_text or 'end' in full_text:
                parameters['action'] = 'stop'
            elif 'pause' in full_text:
                parameters['action'] = 'pause'
            elif 'resume' in full_text:
                parameters['action'] = 'resume'
            elif 'save' in full_text:
                parameters['action'] = 'save'
                
        elif command_type == 'quality_assessment':
            if any(word in full_text for word in ['good', 'great', 'excellent', 'perfect', 'correct', 'right']):
                parameters['quality'] = 'positive'
            else:
                parameters['quality'] = 'negative'
                
        elif command_type == 'environmental_context':
            context_text = match.group(1) if match.groups() else ""
            parameters['context'] = context_text
            
            # Specific environmental parameters
            if 'depth' in full_text:
                depth_match = re.search(r'(\d+)\s*(?:feet|ft|meters?|m)', context_text)
                if depth_match:
                    parameters['depth'] = int(depth_match.group(1))
                    parameters['depth_unit'] = depth_match.group(0).split()[-1]
                    
        elif command_type == 'technique_context':
            technique_text = match.group(1) if match.groups() else ""
            parameters['technique'] = technique_text
        
        return parameters
    
    def _resolve_species(self, species_text: str) -> Optional[str]:
        """Resolve species name from text using vocabulary"""
        species_text = species_text.lower().strip()
        
        # Direct matching first
        for category, species_dict in self.species_vocabulary.items():
            for species_key, variations in species_dict.items():
                for variation in variations:
                    if variation in species_text or species_text in variation:
                        return species_key
        
        # Fuzzy matching for partial matches
        best_match = None
        best_score = 0
        
        for category, species_dict in self.species_vocabulary.items():
            for species_key, variations in species_dict.items():
                for variation in variations:
                    # Simple word overlap score
                    species_words = set(species_text.split())
                    variation_words = set(variation.split())
                    
                    if species_words and variation_words:
                        overlap = len(species_words & variation_words)
                        score = overlap / min(len(species_words), len(variation_words))
                        
                        if score > best_score and score > 0.5:
                            best_score = score
                            best_match = species_key
        
        return best_match
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text"""
        for location, variations in self.location_vocabulary.items():
            for variation in variations:
                if variation in text.lower():
                    return location
        return None
    
    def _update_session_context(self, session_id: str, command: VoiceCommand):
        """Update session context with new command"""
        if session_id not in self.session_context:
            self.session_context[session_id] = {
                'tote_assignments': {},
                'recent_species': [],
                'environment': {},
                'techniques': [],
                'quality_feedback': []
            }
        
        context = self.session_context[session_id]
        
        if command.command_type == 'tote_assignment':
            if 'location' in command.parameters and 'species' in command.parameters:
                context['tote_assignments'][command.parameters['location']] = command.parameters['species']
                
        elif command.command_type == 'species_correction':
            if 'correct_species' in command.parameters:
                context['recent_species'].append(command.parameters['correct_species'])
                if len(context['recent_species']) > 5:
                    context['recent_species'] = context['recent_species'][-5:]
                    
        elif command.command_type == 'environmental_context':
            context['environment'].update(command.parameters)
            
        elif command.command_type == 'technique_context':
            context['techniques'].append(command.parameters)
            if len(context['techniques']) > 3:
                context['techniques'] = context['techniques'][-3:]
                
        elif command.command_type == 'quality_assessment':
            context['quality_feedback'].append({
                'quality': command.parameters.get('quality'),
                'timestamp': command.timestamp
            })
            if len(context['quality_feedback']) > 10:
                context['quality_feedback'] = context['quality_feedback'][-10:]
    
    def _learn_user_patterns(self, text: str, commands: List[VoiceCommand], user_id: str):
        """Learn from user speech patterns"""
        # Track common phrases
        words = text.split()
        for i, word in enumerate(words):
            if i < len(words) - 1:
                bigram = f"{word} {words[i+1]}"
                self.user_patterns[user_id][bigram] += 1
        
        # Track correction patterns
        for command in commands:
            if command.command_type == 'species_correction':
                self.correction_patterns[user_id].append({
                    'text': text,
                    'species': command.parameters.get('correct_species'),
                    'timestamp': command.timestamp
                })
    
    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get current session context"""
        return self.session_context.get(session_id, {})
    
    def suggest_species_from_context(self, session_id: str) -> List[str]:
        """Suggest species based on session context"""
        context = self.get_session_context(session_id)
        suggestions = []
        
        # From recent corrections
        if 'recent_species' in context:
            suggestions.extend(context['recent_species'])
        
        # From tote assignments
        if 'tote_assignments' in context:
            suggestions.extend(context['tote_assignments'].values())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for species in suggestions:
            if species not in seen:
                seen.add(species)
                unique_suggestions.append(species)
        
        return unique_suggestions[:5]  # Top 5 suggestions

class VoiceTrainingInterface:
    """Complete voice training interface with continuous learning"""
    
    def __init__(self, adaptive_system):
        self.adaptive_system = adaptive_system
        self.voice_processor = AdvancedVoiceProcessor()
        
        # Audio recording
        self.audio_interface = pyaudio.PyAudio()
        self.is_recording = False
        self.recording_thread = None
        
        # Command processing
        self.command_queue = asyncio.Queue()
        self.processing_task = None
        
        # Performance tracking
        self.command_stats = defaultdict(int)
        self.accuracy_tracking = {}
        
    async def start_voice_training(self, session_id: str):
        """Start voice training for session"""
        logger.info(f"Starting voice training for session {session_id}")
        
        # Start audio recording
        self.is_recording = True
        self.recording_thread = threading.Thread(
            target=self._audio_recording_loop, 
            args=(session_id,)
        )
        self.recording_thread.start()
        
        # Start command processing
        self.processing_task = asyncio.create_task(
            self._command_processing_loop(session_id)
        )
    
    def stop_voice_training(self):
        """Stop voice training"""
        logger.info("Stopping voice training")
        
        # Stop recording
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join()
        
        # Stop processing
        if self.processing_task:
            self.processing_task.cancel()
    
    def _audio_recording_loop(self, session_id: str):
        """Continuous audio recording loop"""
        # Audio parameters
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        RECORD_SECONDS = 2  # Process in 2-second chunks
        
        stream = self.audio_interface.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        logger.info("Voice recording started")
        
        try:
            while self.is_recording:
                frames = []
                for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                    if not self.is_recording:
                        break
                    data = stream.read(CHUNK)
                    frames.append(data)
                
                if frames:
                    # Convert to audio data
                    audio_data = b''.join(frames)
                    
                    # Add to processing queue
                    asyncio.run_coroutine_threadsafe(
                        self.command_queue.put((audio_data, session_id)),
                        asyncio.get_event_loop()
                    )
                    
        except Exception as e:
            logger.error(f"Audio recording error: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            logger.info("Voice recording stopped")
    
    async def _command_processing_loop(self, session_id: str):
        """Process voice commands from queue"""
        logger.info("Command processing started")
        
        try:
            while True:
                audio_data, current_session_id = await self.command_queue.get()
                
                # Process audio to commands
                commands = self.voice_processor.process_audio_stream(
                    audio_data, current_session_id, "current_user"  # TODO: Get actual user ID
                )
                
                # Execute commands
                for command in commands:
                    await self._execute_voice_command(command)
                    self.command_stats[command.command_type] += 1
                    
        except asyncio.CancelledError:
            logger.info("Command processing stopped")
        except Exception as e:
            logger.error(f"Command processing error: {e}")
    
    async def _execute_voice_command(self, command: VoiceCommand):
        """Execute a processed voice command"""
        logger.info(f"Executing command: {command.command_type} - {command.parameters}")
        
        try:
            if command.command_type == 'tote_assignment':
                await self._handle_tote_assignment(command)
                
            elif command.command_type == 'species_correction':
                await self._handle_species_correction(command)
                
            elif command.command_type == 'training_control':
                await self._handle_training_control(command)
                
            elif command.command_type == 'quality_assessment':
                await self._handle_quality_assessment(command)
                
            elif command.command_type == 'environmental_context':
                await self._handle_environmental_context(command)
                
            elif command.command_type == 'technique_context':
                await self._handle_technique_context(command)
                
        except Exception as e:
            logger.error(f"Command execution error: {e}")
    
    async def _handle_tote_assignment(self, command: VoiceCommand):
        """Handle tote assignment command"""
        params = command.parameters
        
        if 'species' in params and 'location' in params:
            # Update session with tote assignment
            session_id = command.session_id
            if session_id in self.adaptive_system.active_sessions:
                session = self.adaptive_system.active_sessions[session_id]
                session.active_totes[params['location']] = params['species']
                
                # Add species adapter to model
                self.adaptive_system.model.add_species_adapter(
                    params['species'], 
                    command.user_id
                )
                
                logger.info(f"Tote assignment: {params['location']} -> {params['species']}")
                
                # Broadcast update
                await self.adaptive_system.broadcast_update({
                    "type": "tote_assignment",
                    "location": params['location'],
                    "species": params['species'],
                    "session_id": session_id
                })
    
    async def _handle_species_correction(self, command: VoiceCommand):
        """Handle species correction command"""
        params = command.parameters
        
        if 'correct_species' in params:
            session_id = command.session_id
            if session_id in self.adaptive_system.active_sessions:
                session = self.adaptive_system.active_sessions[session_id]
                
                # Find latest prediction to correct
                if session.predictions:
                    latest_prediction = session.predictions[-1]
                    
                    correction = {
                        "prediction_id": latest_prediction.get("id"),
                        "original_species": latest_prediction.get("species"),
                        "correct_species": params['correct_species'],
                        "timestamp": command.timestamp,
                        "confidence": command.confidence
                    }
                    
                    session.corrections.append(correction)
                    
                    logger.info(f"Species correction: {correction['original_species']} -> {correction['correct_species']}")
                    
                    # Broadcast correction
                    await self.adaptive_system.broadcast_update({
                        "type": "species_correction",
                        "correction": correction,
                        "session_id": session_id
                    })
    
    async def _handle_training_control(self, command: VoiceCommand):
        """Handle training control commands"""
        action = command.parameters.get('action')
        
        if action == 'start':
            logger.info("Training started via voice command")
        elif action == 'stop':
            logger.info("Training stopped via voice command")
        elif action == 'pause':
            logger.info("Training paused via voice command")
        elif action == 'resume':
            logger.info("Training resumed via voice command")
        elif action == 'save':
            logger.info("Model save requested via voice command")
            # TODO: Implement model saving
    
    async def _handle_quality_assessment(self, command: VoiceCommand):
        """Handle quality assessment feedback"""
        quality = command.parameters.get('quality')
        session_id = command.session_id
        
        if session_id in self.adaptive_system.active_sessions:
            session = self.adaptive_system.active_sessions[session_id]
            
            # Update accuracy tracking
            if session.predictions:
                latest_prediction = session.predictions[-1]
                prediction_id = latest_prediction.get("id")
                
                if prediction_id:
                    self.accuracy_tracking[prediction_id] = {
                        "quality": quality,
                        "timestamp": command.timestamp,
                        "user_feedback": True
                    }
        
        logger.info(f"Quality feedback: {quality}")
    
    async def _handle_environmental_context(self, command: VoiceCommand):
        """Handle environmental context updates"""
        context = command.parameters.get('context', '')
        logger.info(f"Environmental context: {context}")
        
        # Could be used to adjust model predictions based on conditions
        
    async def _handle_technique_context(self, command: VoiceCommand):
        """Handle fishing technique context"""
        technique = command.parameters.get('technique', '')
        logger.info(f"Technique context: {technique}")
        
        # Could be used to inform species probability distributions
    
    def get_command_statistics(self) -> Dict[str, Any]:
        """Get voice command usage statistics"""
        return {
            "total_commands": sum(self.command_stats.values()),
            "command_breakdown": dict(self.command_stats),
            "accuracy_feedback": len(self.accuracy_tracking),
            "positive_feedback": sum(1 for v in self.accuracy_tracking.values() if v.get("quality") == "positive"),
            "negative_feedback": sum(1 for v in self.accuracy_tracking.values() if v.get("quality") == "negative")
        }

if __name__ == "__main__":
    # Test voice interface
    import asyncio
    from main import AdaptiveCVTrainingSystem
    
    async def test_voice_interface():
        # Create adaptive system
        cv_system = AdaptiveCVTrainingSystem()
        
        # Create voice interface
        voice_interface = VoiceTrainingInterface(cv_system)
        
        # Start session
        session_id = await cv_system.start_training_session("test_user", "test_boat")
        await voice_interface.start_voice_training(session_id)
        
        # Run for 60 seconds
        await asyncio.sleep(60)
        
        # Stop and show stats
        voice_interface.stop_voice_training()
        stats = voice_interface.get_command_statistics()
        print("Voice Command Statistics:", json.dumps(stats, indent=2))
    
    # Run test
    asyncio.run(test_voice_interface())