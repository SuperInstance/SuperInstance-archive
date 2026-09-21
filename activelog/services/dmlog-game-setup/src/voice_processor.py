import asyncio
import logging
import io
import wave
import json
import numpy as np
from typing import Dict, List, Optional, Tuple
import speech_recognition as sr
import librosa
import soundfile as sf
from pydantic import BaseModel
import tempfile
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class VoiceCharacteristics(BaseModel):
    pitch_mean: float
    pitch_std: float
    pitch_range: Tuple[float, float]
    speaking_rate: float
    energy_mean: float
    spectral_centroid: float
    formant_frequencies: List[float]
    voice_quality: str
    accent_indicators: Dict[str, float]
    emotional_markers: Dict[str, float]
    speech_patterns: List[str]

class VoiceRecording(BaseModel):
    recording_id: str
    file_path: str
    transcription: str
    voice_characteristics: VoiceCharacteristics
    timestamp: datetime
    duration: float
    quality_score: float

class VoiceProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.voice_samples = {}
        self.character_voices = {}
        
        # Initialize microphone only if PyAudio is available
        try:
            self.microphone = sr.Microphone()
            # Adjust for ambient noise
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
        except Exception as e:
            logger.warning(f"Microphone initialization failed: {e}. Voice recording will be handled by client.")
            self.microphone = None

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio data to text using speech recognition."""
        try:
            # Create temporary file for audio processing
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Load audio with speech_recognition
            with sr.AudioFile(temp_file_path) as source:
                audio = self.recognizer.record(source)
            
            # Transcribe using Google Speech Recognition
            try:
                transcription = self.recognizer.recognize_google(audio)
                logger.info(f"Transcription successful: {transcription[:100]}...")
                return transcription
            except sr.UnknownValueError:
                logger.warning("Could not understand audio")
                return "[Inaudible speech]"
            except sr.RequestError as e:
                logger.error(f"Speech recognition error: {e}")
                return "[Recognition error]"
                
        except Exception as e:
            logger.error(f"Error in transcription: {e}")
            return "[Transcription failed]"
        finally:
            # Clean up temp file
            if 'temp_file_path' in locals():
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

    async def analyze_voice_characteristics(self, audio_data: bytes) -> VoiceCharacteristics:
        """Analyze voice characteristics from audio data."""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Load audio with librosa
            y, sr_rate = librosa.load(temp_file_path, sr=None)
            
            # Extract pitch information
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr_rate)
            pitch_values = []
            
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if pitch_values:
                pitch_mean = float(np.mean(pitch_values))
                pitch_std = float(np.std(pitch_values))
                pitch_range = (float(np.min(pitch_values)), float(np.max(pitch_values)))
            else:
                pitch_mean = pitch_std = 0.0
                pitch_range = (0.0, 0.0)
            
            # Calculate speaking rate (approximate)
            duration = len(y) / sr_rate
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr_rate)
            speaking_rate = len(onset_frames) / duration if duration > 0 else 0
            
            # Energy analysis
            energy = librosa.feature.rms(y=y)[0]
            energy_mean = float(np.mean(energy))
            
            # Spectral centroid (brightness indicator)
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr_rate)[0]
            spectral_centroid = float(np.mean(spectral_centroids))
            
            # Formant estimation (simplified)
            formant_frequencies = self._estimate_formants(y, sr_rate)
            
            # Voice quality assessment
            voice_quality = self._assess_voice_quality(y, pitch_values, energy_mean)
            
            # Accent indicators (basic pattern detection)
            accent_indicators = self._detect_accent_indicators(y, sr_rate, pitch_values)
            
            # Emotional markers
            emotional_markers = self._detect_emotional_markers(y, pitch_values, energy_mean, spectral_centroid)
            
            # Speech pattern detection
            speech_patterns = self._detect_speech_patterns(y, sr_rate)
            
            return VoiceCharacteristics(
                pitch_mean=pitch_mean,
                pitch_std=pitch_std,
                pitch_range=pitch_range,
                speaking_rate=speaking_rate,
                energy_mean=energy_mean,
                spectral_centroid=spectral_centroid,
                formant_frequencies=formant_frequencies,
                voice_quality=voice_quality,
                accent_indicators=accent_indicators,
                emotional_markers=emotional_markers,
                speech_patterns=speech_patterns
            )
            
        except Exception as e:
            logger.error(f"Error analyzing voice characteristics: {e}")
            return VoiceCharacteristics(
                pitch_mean=0.0, pitch_std=0.0, pitch_range=(0.0, 0.0),
                speaking_rate=0.0, energy_mean=0.0, spectral_centroid=0.0,
                formant_frequencies=[], voice_quality="unknown",
                accent_indicators={}, emotional_markers={}, speech_patterns=[]
            )
        finally:
            # Clean up temp file
            if 'temp_file_path' in locals():
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

    def _estimate_formants(self, y: np.ndarray, sr: int) -> List[float]:
        """Estimate formant frequencies (simplified approach)."""
        try:
            # Get the spectrum
            fft = np.abs(np.fft.rfft(y))
            freqs = np.fft.rfftfreq(len(y), 1/sr)
            
            # Find peaks in spectrum (simplified formant detection)
            from scipy.signal import find_peaks
            peaks, _ = find_peaks(fft, height=np.max(fft) * 0.1, distance=int(sr/1000))
            
            # Get top 4 formants
            formant_freqs = sorted(freqs[peaks][:4])
            return formant_freqs
        except:
            return [500.0, 1500.0, 2500.0, 3500.0]  # Default formants

    def _assess_voice_quality(self, y: np.ndarray, pitch_values: List[float], energy: float) -> str:
        """Assess overall voice quality."""
        if not pitch_values:
            return "unclear"
        
        pitch_stability = 1.0 - (np.std(pitch_values) / np.mean(pitch_values))
        
        if energy > 0.1 and pitch_stability > 0.8:
            return "clear"
        elif energy > 0.05 and pitch_stability > 0.6:
            return "good"
        elif energy > 0.02:
            return "fair"
        else:
            return "poor"

    def _detect_accent_indicators(self, y: np.ndarray, sr: int, pitch_values: List[float]) -> Dict[str, float]:
        """Detect accent indicators (basic implementation)."""
        indicators = {}
        
        if pitch_values:
            # Pitch variation (some accents have more variation)
            pitch_variation = np.std(pitch_values) / np.mean(pitch_values)
            indicators["pitch_variation"] = float(pitch_variation)
            
            # Intonation patterns
            pitch_trend = np.polyfit(range(len(pitch_values)), pitch_values, 1)[0]
            indicators["intonation_slope"] = float(pitch_trend)
        
        # Rhythm analysis (simplified)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        indicators["rhythm_regularity"] = float(tempo / 120.0)  # Normalized to typical speech
        
        return indicators

    def _detect_emotional_markers(self, y: np.ndarray, pitch_values: List[float], 
                                energy: float, spectral_centroid: float) -> Dict[str, float]:
        """Detect emotional markers in voice."""
        markers = {}
        
        if pitch_values:
            avg_pitch = np.mean(pitch_values)
            pitch_range = np.max(pitch_values) - np.min(pitch_values)
            
            # Excitement/arousal indicators
            markers["excitement"] = min(1.0, (pitch_range / 200.0) * (energy * 10))
            
            # Stress indicators
            markers["stress"] = min(1.0, (np.std(pitch_values) / avg_pitch) * 2)
            
            # Confidence indicators
            markers["confidence"] = min(1.0, energy * 2 * (1 - np.std(pitch_values) / avg_pitch))
            
            # Calmness indicators
            markers["calmness"] = max(0.0, 1.0 - markers["excitement"] - markers["stress"])
        
        # Brightness/warmth from spectral centroid
        markers["brightness"] = min(1.0, spectral_centroid / 4000.0)
        
        return markers

    def _detect_speech_patterns(self, y: np.ndarray, sr: int) -> List[str]:
        """Detect speech patterns."""
        patterns = []
        
        # Detect pauses
        silence_threshold = np.max(np.abs(y)) * 0.01
        silent_samples = np.abs(y) < silence_threshold
        
        # Find pause lengths
        pause_lengths = []
        in_pause = False
        pause_start = 0
        
        for i, is_silent in enumerate(silent_samples):
            if is_silent and not in_pause:
                in_pause = True
                pause_start = i
            elif not is_silent and in_pause:
                in_pause = False
                pause_length = (i - pause_start) / sr
                pause_lengths.append(pause_length)
        
        if pause_lengths:
            avg_pause = np.mean(pause_lengths)
            if avg_pause > 1.0:
                patterns.append("long_pauses")
            elif avg_pause > 0.5:
                patterns.append("thoughtful_pauses")
            else:
                patterns.append("quick_speech")
        
        # Detect vocal fry, uptalk, etc. (simplified)
        if len(y) > 0:
            low_freq_energy = np.sum(np.abs(np.fft.rfft(y)[:100]))
            total_energy = np.sum(np.abs(np.fft.rfft(y)))
            
            if low_freq_energy / total_energy > 0.3:
                patterns.append("vocal_fry")
        
        return patterns

    async def compare_voice_samples(self, voice1_data: bytes, voice2_data: bytes) -> float:
        """Compare two voice samples and return similarity score."""
        try:
            char1 = await self.analyze_voice_characteristics(voice1_data)
            char2 = await self.analyze_voice_characteristics(voice2_data)
            
            # Calculate similarity based on multiple factors
            pitch_similarity = 1.0 - abs(char1.pitch_mean - char2.pitch_mean) / max(char1.pitch_mean, char2.pitch_mean, 1.0)
            rate_similarity = 1.0 - abs(char1.speaking_rate - char2.speaking_rate) / max(char1.speaking_rate, char2.speaking_rate, 1.0)
            energy_similarity = 1.0 - abs(char1.energy_mean - char2.energy_mean) / max(char1.energy_mean, char2.energy_mean, 1.0)
            
            # Weighted average
            similarity = (pitch_similarity * 0.4 + rate_similarity * 0.3 + energy_similarity * 0.3)
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"Error comparing voice samples: {e}")
            return 0.0

    async def save_voice_profile(self, character_name: str, voice_data: bytes, 
                               characteristics: VoiceCharacteristics) -> str:
        """Save a voice profile for a character."""
        try:
            profile_id = f"{character_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Save audio file
            voice_dir = "static/voice_profiles"
            os.makedirs(voice_dir, exist_ok=True)
            
            file_path = os.path.join(voice_dir, f"{profile_id}.wav")
            with open(file_path, "wb") as f:
                f.write(voice_data)
            
            # Save characteristics
            self.character_voices[character_name] = {
                "profile_id": profile_id,
                "file_path": file_path,
                "characteristics": characteristics,
                "created_at": datetime.now()
            }
            
            logger.info(f"Saved voice profile for {character_name}: {profile_id}")
            return profile_id
            
        except Exception as e:
            logger.error(f"Error saving voice profile: {e}")
            return ""

    async def generate_tts_voice_config(self, characteristics: VoiceCharacteristics) -> Dict:
        """Generate TTS voice configuration based on voice characteristics."""
        config = {
            "pitch": "medium",
            "rate": "medium", 
            "volume": "medium",
            "voice_type": "neutral"
        }
        
        # Adjust pitch
        if characteristics.pitch_mean > 200:
            config["pitch"] = "high"
        elif characteristics.pitch_mean < 120:
            config["pitch"] = "low"
        
        # Adjust rate
        if characteristics.speaking_rate > 5:
            config["rate"] = "fast"
        elif characteristics.speaking_rate < 2:
            config["rate"] = "slow"
        
        # Determine voice type from emotional markers
        if characteristics.emotional_markers.get("excitement", 0) > 0.7:
            config["voice_type"] = "enthusiastic"
        elif characteristics.emotional_markers.get("calmness", 0) > 0.7:
            config["voice_type"] = "calm"
        elif characteristics.emotional_markers.get("confidence", 0) > 0.7:
            config["voice_type"] = "confident"
        
        return config