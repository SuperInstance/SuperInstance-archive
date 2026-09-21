"""
Professional Speech Engine for Marine Voice Control
Handles speech recognition, synthesis, and wake word detection
"""

import logging
import threading
import queue
import time
import numpy as np
from typing import Optional, Callable, Dict, Any
# import speech_recognition as sr
# import pyttsx3
# import pyaudio
# import webrtcvad
import wave
import io
from collections import deque

logger = logging.getLogger(__name__)

class SpeechEngine:
    """
    Professional speech engine with marine-optimized settings
    """
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.tts_engine = None
        self.vad = webrtcvad.Vad(2)  # Aggressiveness level 2 (0-3)
        
        # Audio settings optimized for marine environment
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        
        # Voice detection parameters
        self.voice_timeout = 1.0  # seconds of silence before stopping
        self.phrase_timeout = 0.3  # seconds of non-speaking before phrase is complete
        
        # Wake words
        self.wake_words = ['bridge', 'navigator', 'autopilot', 'computer']
        self.wake_word_sensitivity = 0.6
        
        # Audio processing
        self.audio_queue = queue.Queue()
        self.command_callback: Optional[Callable] = None
        self.audio_callback: Optional[Callable] = None
        
        # Status
        self.listening = False
        self.speaking = False
        
        self._initialize_audio()
        self._initialize_tts()
        
        logger.info("Speech Engine initialized")
    
    def _initialize_audio(self):
        """Initialize audio input/output"""
        try:
            # Simulated audio initialization
            self.microphone = "simulated"
            logger.info("Audio input initialized (simulated)")
            
        except Exception as e:
            logger.error(f"Audio initialization error: {e}")
    
    def _find_best_microphone(self):
        """Find the best available microphone"""
        try:
            # Try to find a specific marine/USB microphone first
            for i in range(self.audio.get_device_count()):
                device_info = self.audio.get_device_info_by_index(i)
                device_name = device_info.get('name', '').lower()
                
                # Prefer external/USB microphones for marine use
                if ('usb' in device_name or 'external' in device_name or 
                    'headset' in device_name or 'marine' in device_name):
                    try:
                        self.microphone = sr.Microphone(device_index=i)
                        logger.info(f"Selected microphone: {device_info['name']}")
                        return
                    except Exception:
                        continue
            
            # Fall back to default microphone
            self.microphone = sr.Microphone()
            logger.info("Using default microphone")
            
        except Exception as e:
            logger.error(f"Microphone selection error: {e}")
            self.microphone = None
    
    def _initialize_tts(self):
        """Initialize text-to-speech engine"""
        try:
            self.tts_engine = pyttsx3.init()
            
            # Configure TTS for marine environment
            voices = self.tts_engine.getProperty('voices')
            
            # Prefer clear, authoritative voice
            selected_voice = None
            for voice in voices:
                if 'english' in voice.name.lower():
                    selected_voice = voice.id
                    break
            
            if selected_voice:
                self.tts_engine.setProperty('voice', selected_voice)
            
            # Set speech rate and volume for bridge environment
            self.tts_engine.setProperty('rate', 180)  # Slightly slower for clarity
            self.tts_engine.setProperty('volume', 0.9)  # High volume for noisy environment
            
            logger.info("TTS engine initialized")
            
        except Exception as e:
            logger.error(f"TTS initialization error: {e}")
            self.tts_engine = None
    
    def set_command_callback(self, callback: Callable):
        """Set callback for processed commands"""
        self.command_callback = callback
    
    def set_audio_callback(self, callback: Callable):
        """Set callback for raw audio processing"""
        self.audio_callback = callback
    
    def get_audio_input(self) -> Optional[bytes]:
        """Get audio input for processing"""
        if not self.microphone or not self.listening:
            return None
        
        try:
            with self.microphone as source:
                # Listen for audio with timeout
                audio = self.recognizer.listen(
                    source, 
                    timeout=0.5,  # Quick timeout for responsiveness
                    phrase_time_limit=5  # Max phrase length
                )
                
                return audio.get_raw_data()
                
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            logger.debug(f"Audio input error: {e}")
            return None
    
    def recognize_speech(self, audio_data: bytes) -> Optional[str]:
        """Recognize speech from audio data"""
        if not audio_data:
            return None
        
        try:
            # Convert bytes to AudioData
            audio = sr.AudioData(audio_data, self.sample_rate, 2)
            
            # Try multiple recognition engines for robustness
            text = None
            
            # Try Google Speech Recognition (requires internet)
            try:
                text = self.recognizer.recognize_google(audio, language='en-US')
                logger.debug(f"Google recognition: {text}")
            except (sr.UnknownValueError, sr.RequestError):
                pass
            
            # Try built-in Sphinx as fallback (offline)
            if not text:
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                    logger.debug(f"Sphinx recognition: {text}")
                except (sr.UnknownValueError, sr.RequestError):
                    pass
            
            if text:
                # Clean up recognized text
                text = text.strip().lower()
                
                # Filter out very short or nonsensical results
                if len(text) < 3:
                    return None
                
                return text
                
        except Exception as e:
            logger.debug(f"Speech recognition error: {e}")
        
        return None
    
    def detect_wake_word(self, audio_data: bytes) -> bool:
        """Detect wake word in audio"""
        if not audio_data:
            return False
        
        try:
            # Quick recognition for wake word detection
            audio = sr.AudioData(audio_data, self.sample_rate, 2)
            
            try:
                text = self.recognizer.recognize_google(audio, language='en-US')
                text = text.lower()
                
                # Check for wake words
                for wake_word in self.wake_words:
                    if wake_word in text:
                        logger.info(f"Wake word detected: {wake_word}")
                        return True
                        
            except (sr.UnknownValueError, sr.RequestError):
                pass
            
        except Exception as e:
            logger.debug(f"Wake word detection error: {e}")
        
        return False
    
    def speak(self, text: str):
        """Generate speech output"""
        if not self.tts_engine or not text:
            return
        
        try:
            self.speaking = True
            
            # Generate speech in separate thread to avoid blocking
            def _speak():
                try:
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                except Exception as e:
                    logger.error(f"TTS error: {e}")
                finally:
                    self.speaking = False
            
            speech_thread = threading.Thread(target=_speak, daemon=True)
            speech_thread.start()
            
            logger.info(f"Speaking: {text}")
            
        except Exception as e:
            logger.error(f"Speech generation error: {e}")
            self.speaking = False
    
    def start_listening(self):
        """Start continuous listening"""
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
    
    def set_wake_words(self, wake_words: list):
        """Set custom wake words"""
        self.wake_words = [word.lower() for word in wake_words]
        logger.info(f"Wake words updated: {self.wake_words}")
    
    def set_voice_parameters(self, rate: int = None, volume: float = None):
        """Set TTS voice parameters"""
        if not self.tts_engine:
            return
        
        try:
            if rate is not None:
                self.tts_engine.setProperty('rate', max(100, min(300, rate)))
            
            if volume is not None:
                self.tts_engine.setProperty('volume', max(0.0, min(1.0, volume)))
                
            logger.info(f"Voice parameters updated: rate={rate}, volume={volume}")
            
        except Exception as e:
            logger.error(f"Voice parameter error: {e}")
    
    def get_available_voices(self) -> list:
        """Get list of available TTS voices"""
        if not self.tts_engine:
            return []
        
        try:
            voices = self.tts_engine.getProperty('voices')
            voice_list = []
            
            for voice in voices:
                voice_info = {
                    'id': voice.id,
                    'name': voice.name,
                    'languages': getattr(voice, 'languages', []),
                    'gender': getattr(voice, 'gender', 'unknown')
                }
                voice_list.append(voice_info)
            
            return voice_list
            
        except Exception as e:
            logger.error(f"Voice enumeration error: {e}")
            return []
    
    def set_voice(self, voice_id: str):
        """Set specific TTS voice"""
        if not self.tts_engine:
            return False
        
        try:
            voices = self.tts_engine.getProperty('voices')
            
            for voice in voices:
                if voice.id == voice_id:
                    self.tts_engine.setProperty('voice', voice_id)
                    logger.info(f"Voice changed to: {voice.name}")
                    return True
            
            logger.warning(f"Voice not found: {voice_id}")
            return False
            
        except Exception as e:
            logger.error(f"Voice change error: {e}")
            return False
    
    def get_audio_devices(self) -> list:
        """Get list of available audio devices"""
        devices = []
        
        try:
            for i in range(self.audio.get_device_count()):
                device_info = self.audio.get_device_info_by_index(i)
                
                # Only include input devices
                if device_info.get('maxInputChannels', 0) > 0:
                    devices.append({
                        'index': i,
                        'name': device_info.get('name', 'Unknown'),
                        'channels': device_info.get('maxInputChannels', 0),
                        'sample_rate': device_info.get('defaultSampleRate', 0)
                    })
            
        except Exception as e:
            logger.error(f"Audio device enumeration error: {e}")
        
        return devices
    
    def set_microphone(self, device_index: int) -> bool:
        """Set specific microphone device"""
        try:
            test_mic = sr.Microphone(device_index=device_index)
            
            # Test the microphone
            with test_mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            self.microphone = test_mic
            logger.info(f"Microphone changed to device {device_index}")
            return True
            
        except Exception as e:
            logger.error(f"Microphone change error: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get speech engine status"""
        return {
            'listening': self.listening,
            'speaking': self.speaking,
            'microphone_available': self.microphone is not None,
            'tts_available': self.tts_engine is not None,
            'wake_words': self.wake_words,
            'sample_rate': self.sample_rate,
            'chunk_size': self.chunk_size
        }
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.listening = False
            
            if hasattr(self, 'audio'):
                self.audio.terminate()
            
            if self.tts_engine:
                self.tts_engine.stop()
            
            logger.info("Speech engine cleanup completed")
            
        except Exception as e:
            logger.error(f"Speech engine cleanup error: {e}")