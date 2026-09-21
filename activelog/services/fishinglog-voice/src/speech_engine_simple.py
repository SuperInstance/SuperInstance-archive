"""
Simplified Speech Engine for Demonstration
Provides voice interface simulation without audio hardware requirements
"""

import logging
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)

class SpeechEngine:
    """
    Simplified speech engine for demonstration purposes
    """
    
    def __init__(self):
        self.listening = False
        self.speaking = False
        self.command_callback: Optional[Callable] = None
        self.audio_callback: Optional[Callable] = None
        self.wake_words = ['bridge', 'navigator', 'autopilot', 'computer']
        
        logger.info("Speech Engine initialized (simulation mode)")
    
    def set_command_callback(self, callback: Callable):
        """Set callback for processed commands"""
        self.command_callback = callback
    
    def set_audio_callback(self, callback: Callable):
        """Set callback for raw audio processing"""
        self.audio_callback = callback
    
    def get_audio_input(self) -> Optional[bytes]:
        """Simulated audio input"""
        if self.listening:
            # Simulate audio data
            return b"simulated_audio_data"
        return None
    
    def recognize_speech(self, audio_data: bytes) -> Optional[str]:
        """Simulated speech recognition"""
        if audio_data:
            # Return None to indicate no speech recognized (for demo)
            return None
        return None
    
    def detect_wake_word(self, audio_data: bytes) -> bool:
        """Simulated wake word detection"""
        return False
    
    def speak(self, text: str):
        """Simulated speech output"""
        if text:
            self.speaking = True
            logger.info(f"TTS Output: {text}")
            self.speaking = False
    
    def start_listening(self):
        """Start listening"""
        self.listening = True
        logger.info("Speech listening started")
    
    def stop_listening(self):
        """Stop listening"""
        self.listening = False
        logger.info("Speech listening stopped")
    
    def is_speaking(self) -> bool:
        """Check if currently speaking"""
        return self.speaking
    
    def is_listening(self) -> bool:
        """Check if currently listening"""
        return self.listening
    
    def get_status(self) -> Dict[str, Any]:
        """Get speech engine status"""
        return {
            'listening': self.listening,
            'speaking': self.speaking,
            'microphone_available': True,
            'tts_available': True,
            'wake_words': self.wake_words,
            'mode': 'simulation'
        }