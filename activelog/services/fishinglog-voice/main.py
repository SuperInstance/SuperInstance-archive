#!/usr/bin/env python3
"""
Professional Voice Bridge Control System
Advanced voice interface for marine navigation with multi-language support
and marine-specific noise filtering
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import redis
from dotenv import load_dotenv

from src.speech_engine_simple import SpeechEngine
from src.voice_commands import VoiceCommandProcessor
from src.autopilot_control import AutopilotController
from src.chart_voice_control import ChartVoiceController
from src.follow_vessel import FollowVesselController
from src.audio_warnings import AudioWarningSystem
from src.voice_logger import VoiceLogger
from src.multi_language import MultiLanguageProcessor
from src.noise_filter import MarineNoiseFilter
from src.confirmation_protocols import ConfirmationProtocol
from src.emergency_commands import EmergencyCommandHandler

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'voice-bridge-2024-secure-key')
CORS(app, origins=["*"])
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/activeloguser/activelog/services/fishinglog-voice/voice.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VoiceBridgeSystem:
    """
    Professional Voice Bridge Control System
    Provides comprehensive voice interface for marine navigation operations
    """
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=1)
        self.active_sessions = {}
        
        # Voice system components
        self.speech_engine = SpeechEngine()
        self.voice_commands = VoiceCommandProcessor()
        self.autopilot = AutopilotController()
        self.chart_control = ChartVoiceController()
        self.follow_vessel = FollowVesselController()
        self.audio_warnings = AudioWarningSystem()
        self.voice_logger = VoiceLogger()
        self.multi_language = MultiLanguageProcessor()
        self.noise_filter = MarineNoiseFilter()
        self.confirmation = ConfirmationProtocol()
        self.emergency = EmergencyCommandHandler()
        
        # System state
        self.voice_enabled = True
        self.listening = False
        self.current_language = 'en'
        self.voice_sensitivity = 0.7
        self.noise_threshold = 0.3
        
        # Navigation connection
        self.nav_system_url = "http://localhost:8365"
        
        self._setup_voice_callbacks()
        self._start_voice_processing()
        
        logger.info("Voice Bridge System initialized")
    
    def _setup_voice_callbacks(self):
        """Setup callbacks between voice components"""
        self.speech_engine.set_command_callback(self._process_voice_command)
        self.speech_engine.set_audio_callback(self._process_audio_data)
        self.confirmation.set_execute_callback(self._execute_confirmed_command)
        self.emergency.set_emergency_callback(self._handle_emergency)
    
    def _start_voice_processing(self):
        """Start voice processing threads"""
        self.voice_thread = threading.Thread(target=self._voice_processing_loop, daemon=True)
        self.voice_thread.start()
        
        self.audio_monitoring_thread = threading.Thread(target=self._audio_monitoring_loop, daemon=True)
        self.audio_monitoring_thread.start()
    
    def _voice_processing_loop(self):
        """Main voice processing loop"""
        while True:
            try:
                if self.voice_enabled and self.listening:
                    # Get audio input
                    audio_data = self.speech_engine.get_audio_input()
                    
                    if audio_data:
                        # Apply noise filtering
                        filtered_audio = self.noise_filter.filter_audio(audio_data)
                        
                        # Process speech recognition
                        text = self.speech_engine.recognize_speech(filtered_audio)
                        
                        if text:
                            logger.info(f"Voice input received: {text}")
                            
                            # Detect language if multi-language enabled
                            if self.current_language == 'auto':
                                detected_lang = self.multi_language.detect_language(text)
                                if detected_lang:
                                    self.current_language = detected_lang
                            
                            # Translate if necessary
                            if self.current_language != 'en':
                                text = self.multi_language.translate_to_english(text, self.current_language)
                            
                            # Process command
                            self._process_voice_command(text)
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
            except Exception as e:
                logger.error(f"Voice processing error: {e}")
                time.sleep(1)
    
    def _audio_monitoring_loop(self):
        """Monitor audio for collision warnings and alerts"""
        while True:
            try:
                # Check for collision risks from navigation system
                collision_data = self._get_collision_data()
                
                if collision_data:
                    self.audio_warnings.process_collision_warnings(collision_data)
                
                # Check for other system alerts
                system_alerts = self._get_system_alerts()
                if system_alerts:
                    self.audio_warnings.process_system_alerts(system_alerts)
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"Audio monitoring error: {e}")
                time.sleep(5)
    
    def _process_voice_command(self, command_text: str):
        """Process recognized voice command"""
        try:
            # Log the command
            self.voice_logger.log_voice_command(command_text)
            
            # Parse command
            parsed_command = self.voice_commands.parse_command(command_text)
            
            if not parsed_command:
                self._speak_response("Command not recognized. Please try again.")
                return
            
            # Check if it's an emergency command
            if self.emergency.is_emergency_command(parsed_command):
                self._handle_emergency_command(parsed_command)
                return
            
            # Check if command requires confirmation
            if self.confirmation.requires_confirmation(parsed_command):
                self.confirmation.request_confirmation(parsed_command)
                return
            
            # Execute command directly
            self._execute_command(parsed_command)
            
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            self._speak_response("Error processing command.")
    
    def _execute_command(self, command: Dict[str, Any]):
        """Execute voice command"""
        try:
            command_type = command.get('type')
            params = command.get('params', {})
            
            response = None
            
            if command_type == 'chart_control':
                response = self.chart_control.execute_command(command)
                
            elif command_type == 'autopilot':
                response = self.autopilot.execute_command(command)
                
            elif command_type == 'follow_vessel':
                response = self.follow_vessel.execute_command(command)
                
            elif command_type == 'navigation':
                response = self._execute_navigation_command(command)
                
            elif command_type == 'log_entry':
                response = self.voice_logger.create_voice_log(command)
                
            elif command_type == 'system_control':
                response = self._execute_system_command(command)
                
            else:
                response = {"status": "error", "message": "Unknown command type"}
            
            # Provide voice feedback
            if response:
                feedback = self._generate_voice_feedback(response)
                self._speak_response(feedback)
            
            # Broadcast command execution to connected clients
            socketio.emit('voice_command_executed', {
                'command': command,
                'response': response,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            self._speak_response("Error executing command.")
    
    def _execute_confirmed_command(self, command: Dict[str, Any]):
        """Execute command after confirmation"""
        logger.info(f"Executing confirmed command: {command}")
        self._execute_command(command)
    
    def _handle_emergency(self, emergency_data: Dict[str, Any]):
        """Handle emergency situation"""
        logger.critical(f"EMERGENCY: {emergency_data}")
        
        # Execute emergency procedures
        self.emergency.execute_emergency_procedures(emergency_data)
        
        # Broadcast emergency alert
        socketio.emit('emergency_alert', emergency_data)
        
        # Provide immediate voice feedback
        self._speak_response("Emergency procedures activated.")
    
    def _handle_emergency_command(self, command: Dict[str, Any]):
        """Handle emergency voice command"""
        self.emergency.process_emergency_command(command)
    
    def _execute_navigation_command(self, command: Dict[str, Any]):
        """Execute navigation-related command"""
        try:
            # Forward to navigation system
            import requests
            
            endpoint = command.get('endpoint', '')
            method = command.get('method', 'POST')
            data = command.get('data', {})
            
            url = f"{self.nav_system_url}{endpoint}"
            
            if method == 'POST':
                response = requests.post(url, json=data, timeout=5)
            else:
                response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": "Navigation system error"}
                
        except Exception as e:
            logger.error(f"Navigation command error: {e}")
            return {"status": "error", "message": str(e)}
    
    def _execute_system_command(self, command: Dict[str, Any]):
        """Execute system control command"""
        action = command.get('action')
        
        if action == 'voice_enable':
            self.voice_enabled = True
            return {"status": "success", "message": "Voice control enabled"}
            
        elif action == 'voice_disable':
            self.voice_enabled = False
            return {"status": "success", "message": "Voice control disabled"}
            
        elif action == 'start_listening':
            self.listening = True
            return {"status": "success", "message": "Voice listening started"}
            
        elif action == 'stop_listening':
            self.listening = False
            return {"status": "success", "message": "Voice listening stopped"}
            
        elif action == 'set_language':
            language = command.get('params', {}).get('language', 'en')
            self.current_language = language
            return {"status": "success", "message": f"Language set to {language}"}
            
        else:
            return {"status": "error", "message": "Unknown system command"}
    
    def _generate_voice_feedback(self, response: Dict[str, Any]) -> str:
        """Generate appropriate voice feedback"""
        if response.get('status') == 'success':
            return response.get('message', 'Command executed successfully.')
        else:
            return response.get('message', 'Command failed.')
    
    def _speak_response(self, text: str):
        """Provide voice response"""
        try:
            # Translate response if necessary
            if self.current_language != 'en':
                text = self.multi_language.translate_from_english(text, self.current_language)
            
            # Generate speech
            self.speech_engine.speak(text)
            
            # Broadcast to connected clients
            socketio.emit('voice_response', {
                'text': text,
                'language': self.current_language,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Speech generation error: {e}")
    
    def _process_audio_data(self, audio_data: bytes):
        """Process raw audio data for analysis"""
        try:
            # Analyze audio levels for noise filtering
            self.noise_filter.analyze_audio_levels(audio_data)
            
            # Check for wake word detection
            wake_word_detected = self.speech_engine.detect_wake_word(audio_data)
            
            if wake_word_detected and not self.listening:
                self.listening = True
                self._speak_response("Voice control activated.")
                
                socketio.emit('voice_activation', {
                    'active': True,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
    
    def _get_collision_data(self) -> Optional[Dict[str, Any]]:
        """Get collision data from navigation system"""
        try:
            import requests
            response = requests.get(f"{self.nav_system_url}/api/position", timeout=2)
            
            if response.status_code == 200:
                # This would normally get actual collision data
                # For now, return None to avoid issues
                return None
                
        except Exception:
            return None
    
    def _get_system_alerts(self) -> Optional[List[Dict[str, Any]]]:
        """Get system alerts"""
        try:
            # Check Redis for alerts
            alerts_key = 'system_alerts'
            alerts_data = self.redis_client.get(alerts_key)
            
            if alerts_data:
                return json.loads(alerts_data)
                
        except Exception:
            pass
            
        return None
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get voice system status"""
        return {
            'voice_enabled': self.voice_enabled,
            'listening': self.listening,
            'current_language': self.current_language,
            'voice_sensitivity': self.voice_sensitivity,
            'noise_threshold': self.noise_threshold,
            'active_sessions': len(self.active_sessions),
            'components': {
                'speech_engine': self.speech_engine.get_status(),
                'noise_filter': self.noise_filter.get_status(),
                'autopilot': self.autopilot.get_status(),
                'follow_vessel': self.follow_vessel.get_status()
            }
        }

# Initialize voice bridge system
voice_bridge = VoiceBridgeSystem()

@app.route('/')
def index():
    return render_template('voice_control.html')

@app.route('/api/voice/enable', methods=['POST'])
def enable_voice():
    voice_bridge.voice_enabled = True
    voice_bridge.listening = True
    return jsonify({"status": "success", "message": "Voice control enabled"})

@app.route('/api/voice/disable', methods=['POST'])
def disable_voice():
    voice_bridge.voice_enabled = False
    voice_bridge.listening = False
    return jsonify({"status": "success", "message": "Voice control disabled"})

@app.route('/api/voice/status')
def voice_status():
    return jsonify(voice_bridge.get_system_status())

@app.route('/api/voice/language', methods=['POST'])
def set_language():
    data = request.json
    language = data.get('language', 'en')
    
    if voice_bridge.multi_language.is_supported_language(language):
        voice_bridge.current_language = language
        return jsonify({"status": "success", "language": language})
    else:
        return jsonify({"status": "error", "message": "Language not supported"}), 400

@app.route('/api/voice/commands')
def get_available_commands():
    commands = voice_bridge.voice_commands.get_available_commands()
    return jsonify(commands)

@app.route('/api/voice/test', methods=['POST'])
def test_voice():
    data = request.json
    text = data.get('text', 'Voice system test')
    
    voice_bridge._speak_response(text)
    return jsonify({"status": "success", "message": "Test speech generated"})

@app.route('/api/autopilot/status')
def autopilot_status():
    status = voice_bridge.autopilot.get_status()
    return jsonify(status)

@app.route('/api/follow-vessel/status')
def follow_vessel_status():
    status = voice_bridge.follow_vessel.get_status()
    return jsonify(status)

@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    voice_bridge.active_sessions[session_id] = {
        'connected_at': datetime.now(timezone.utc).isoformat(),
        'station_type': 'voice_control'
    }
    
    emit('connected', {
        'session_id': session_id,
        'voice_status': voice_bridge.get_system_status()
    })
    
    logger.info(f"Voice client connected: {session_id}")

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id in voice_bridge.active_sessions:
        del voice_bridge.active_sessions[session_id]
    logger.info(f"Voice client disconnected: {session_id}")

@socketio.on('voice_command')
def handle_voice_command(data):
    command_text = data.get('command', '')
    
    if command_text:
        voice_bridge._process_voice_command(command_text)
        emit('command_received', {'command': command_text})

@socketio.on('voice_settings')
def handle_voice_settings(data):
    if 'sensitivity' in data:
        voice_bridge.voice_sensitivity = float(data['sensitivity'])
    
    if 'noise_threshold' in data:
        voice_bridge.noise_threshold = float(data['noise_threshold'])
    
    if 'language' in data:
        language = data['language']
        if voice_bridge.multi_language.is_supported_language(language):
            voice_bridge.current_language = language
    
    emit('settings_updated', voice_bridge.get_system_status())

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8366))
    logger.info(f"Starting Voice Bridge System on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)