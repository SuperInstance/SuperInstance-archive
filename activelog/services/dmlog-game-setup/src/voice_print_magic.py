import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime
import json
import numpy as np
from dataclasses import dataclass
import tempfile
import os
import io
import base64
from scipy import signal
from scipy.interpolate import interp1d
import wave

logger = logging.getLogger(__name__)

@dataclass
class VoicePrint:
    voice_id: str
    character_name: str
    sample_path: str
    fundamental_freq: float
    formant_frequencies: List[float]
    spectral_envelope: np.ndarray
    pitch_contour: np.ndarray
    energy_profile: np.ndarray
    voice_quality_markers: Dict[str, float]
    prosodic_features: Dict[str, float]
    phonetic_characteristics: Dict[str, Any]
    emotional_baseline: Dict[str, float]
    accent_markers: Dict[str, float]
    created_at: datetime

@dataclass
class VoiceTransformation:
    source_voice_id: str
    target_voice_id: str
    transformation_matrix: np.ndarray
    pitch_shift_ratio: float
    formant_shifts: List[float]
    energy_adjustment: float
    quality_modifications: Dict[str, float]
    confidence_score: float

class VoiceCommand(BaseModel):
    command_type: str
    parameters: Dict[str, Any]
    voice_trigger: Optional[str] = None
    confidence_threshold: float = 0.8

@dataclass
class RealTimeVoiceConfig:
    target_character: str
    transformation: VoiceTransformation
    emotional_modifiers: Dict[str, float]
    age_adjustment: float
    gender_shift: float
    accent_preservation: float
    quality_enhancement: bool

class VoicePrintMagic:
    def __init__(self):
        self.voice_prints = {}  # voice_id -> VoicePrint
        self.transformations = {}  # (source, target) -> VoiceTransformation
        self.active_transformations = {}  # session_id -> RealTimeVoiceConfig
        self.voice_commands = self._initialize_voice_commands()
        self.language_models = self._initialize_language_support()
        self.neural_vocoder = None  # Would integrate actual neural vocoder
        self.real_time_processor = RealTimeVoiceProcessor()

    def _initialize_voice_commands(self) -> Dict[str, VoiceCommand]:
        """Initialize voice command recognition patterns."""
        return {
            'roll_dice': VoiceCommand(
                command_type='dice_roll',
                parameters={'pattern': r'roll (\d+)d(\d+)(?:\+(\d+))?'},
                voice_trigger='roll',
                confidence_threshold=0.8
            ),
            'attack': VoiceCommand(
                command_type='combat_action',
                parameters={'action': 'attack', 'pattern': r'(?:I )?attack (\w+)'},
                voice_trigger='attack',
                confidence_threshold=0.7
            ),
            'cast_spell': VoiceCommand(
                command_type='spell_cast',
                parameters={'pattern': r'(?:I )?cast (\w+)(?: at (\w+))?'},
                voice_trigger='cast',
                confidence_threshold=0.8
            ),
            'use_skill': VoiceCommand(
                command_type='skill_check',
                parameters={'pattern': r'(?:I )?use (\w+)(?: on (\w+))?'},
                voice_trigger='use',
                confidence_threshold=0.7
            ),
            'switch_character': VoiceCommand(
                command_type='character_switch',
                parameters={'pattern': r'switch to (\w+)'},
                voice_trigger='switch',
                confidence_threshold=0.9
            ),
            'create_encounter': VoiceCommand(
                command_type='dm_action',
                parameters={'pattern': r'create (\w+) encounter'},
                voice_trigger='create',
                confidence_threshold=0.8
            )
        }

    def _initialize_language_support(self) -> Dict[str, Dict]:
        """Initialize multi-language support configurations."""
        return {
            'english': {
                'phoneme_set': ['ae', 'ah', 'aw', 'ay', 'eh', 'er', 'ey', 'ih', 'iy', 'ow', 'oy', 'uh', 'uw'],
                'stress_patterns': ['primary', 'secondary', 'unstressed'],
                'intonation_patterns': ['rising', 'falling', 'flat', 'question']
            },
            'fantasy_common': {
                'phoneme_set': ['ae', 'ah', 'eh', 'ih', 'ow', 'th', 'kh', 'zh'],
                'accent_markers': ['rolled_r', 'aspirated_consonants', 'elongated_vowels'],
                'magical_intonations': ['incantation', 'blessing', 'curse']
            },
            'draconic': {
                'phoneme_set': ['kh', 'gh', 'zh', 'th', 'ss', 'rr'],
                'accent_markers': ['guttural', 'sibilant', 'resonant'],
                'power_modulations': ['ancient', 'primordial', 'commanding']
            },
            'elvish': {
                'phoneme_set': ['ih', 'ey', 'ah', 'th', 'lh', 'ng'],
                'accent_markers': ['melodic', 'flowing', 'crystalline'],
                'emotional_resonance': ['serene', 'melancholy', 'ethereal']
            }
        }

    async def create_voice_print_from_sample(self, character_name: str, audio_data: bytes, 
                                           duration_seconds: float = 10.0) -> VoicePrint:
        """Create a comprehensive voice print from a short audio sample."""
        try:
            # Save audio sample
            voice_id = f"{character_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            sample_path = await self._save_audio_sample(voice_id, audio_data)
            
            # Load and preprocess audio
            audio_array, sample_rate = await self._load_audio(audio_data)
            
            # Extract fundamental frequency (pitch)
            fundamental_freq = await self._extract_fundamental_frequency(audio_array, sample_rate)
            
            # Extract formant frequencies
            formant_frequencies = await self._extract_formants(audio_array, sample_rate)
            
            # Extract spectral envelope
            spectral_envelope = await self._extract_spectral_envelope(audio_array, sample_rate)
            
            # Extract pitch contour
            pitch_contour = await self._extract_pitch_contour(audio_array, sample_rate)
            
            # Extract energy profile
            energy_profile = await self._extract_energy_profile(audio_array, sample_rate)
            
            # Analyze voice quality
            voice_quality_markers = await self._analyze_voice_quality(audio_array, sample_rate)
            
            # Extract prosodic features
            prosodic_features = await self._extract_prosodic_features(audio_array, sample_rate)
            
            # Analyze phonetic characteristics
            phonetic_characteristics = await self._analyze_phonetics(audio_array, sample_rate)
            
            # Determine emotional baseline
            emotional_baseline = await self._determine_emotional_baseline(audio_array, sample_rate)
            
            # Extract accent markers
            accent_markers = await self._extract_accent_markers(audio_array, sample_rate)
            
            # Create voice print
            voice_print = VoicePrint(
                voice_id=voice_id,
                character_name=character_name,
                sample_path=sample_path,
                fundamental_freq=fundamental_freq,
                formant_frequencies=formant_frequencies,
                spectral_envelope=spectral_envelope,
                pitch_contour=pitch_contour,
                energy_profile=energy_profile,
                voice_quality_markers=voice_quality_markers,
                prosodic_features=prosodic_features,
                phonetic_characteristics=phonetic_characteristics,
                emotional_baseline=emotional_baseline,
                accent_markers=accent_markers,
                created_at=datetime.now()
            )
            
            # Store voice print
            self.voice_prints[voice_id] = voice_print
            
            logger.info(f"Created voice print for {character_name}: {voice_id}")
            return voice_print
            
        except Exception as e:
            logger.error(f"Error creating voice print: {e}")
            raise

    async def _save_audio_sample(self, voice_id: str, audio_data: bytes) -> str:
        """Save audio sample to file system."""
        samples_dir = "static/voice_prints"
        os.makedirs(samples_dir, exist_ok=True)
        
        file_path = os.path.join(samples_dir, f"{voice_id}.wav")
        with open(file_path, "wb") as f:
            f.write(audio_data)
        
        return file_path

    async def _load_audio(self, audio_data: bytes) -> Tuple[np.ndarray, int]:
        """Load audio data into numpy array."""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Read with wave library
            with wave.open(temp_file_path, 'rb') as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
                sample_rate = wav_file.getframerate()
                
                # Convert to numpy array
                audio_array = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                audio_array = audio_array / 32768.0  # Normalize to [-1, 1]
                
            # Clean up
            os.unlink(temp_file_path)
            
            return audio_array, sample_rate
            
        except Exception as e:
            logger.error(f"Error loading audio: {e}")
            # Return empty array as fallback
            return np.array([]), 16000

    async def _extract_fundamental_frequency(self, audio: np.ndarray, sample_rate: int) -> float:
        """Extract fundamental frequency (average pitch) from audio."""
        if len(audio) == 0:
            return 150.0  # Default frequency
        
        try:
            # Simple autocorrelation-based pitch detection
            correlation = np.correlate(audio, audio, mode='full')
            correlation = correlation[len(correlation)//2:]
            
            # Find peak (excluding zero lag)
            min_period = int(sample_rate / 500)  # 500 Hz max
            max_period = int(sample_rate / 50)   # 50 Hz min
            
            if max_period < len(correlation):
                peak_idx = np.argmax(correlation[min_period:max_period]) + min_period
                fundamental_freq = sample_rate / peak_idx
                return float(fundamental_freq)
            
        except Exception as e:
            logger.error(f"Error extracting fundamental frequency: {e}")
        
        return 150.0  # Default fallback

    async def _extract_formants(self, audio: np.ndarray, sample_rate: int) -> List[float]:
        """Extract formant frequencies from audio."""
        if len(audio) == 0:
            return [800.0, 1200.0, 2400.0, 3200.0]  # Default formants
        
        try:
            # Simple spectral peak detection for formants
            fft = np.abs(np.fft.rfft(audio))
            freqs = np.fft.rfftfreq(len(audio), 1/sample_rate)
            
            # Find peaks in spectrum
            peaks = []
            for i in range(1, len(fft)-1):
                if fft[i] > fft[i-1] and fft[i] > fft[i+1] and fft[i] > np.max(fft) * 0.1:
                    peaks.append((freqs[i], fft[i]))
            
            # Sort by amplitude and take top 4 as formants
            peaks.sort(key=lambda x: x[1], reverse=True)
            formants = [peak[0] for peak in peaks[:4]]
            formants.sort()  # Sort by frequency
            
            # Ensure we have 4 formants
            while len(formants) < 4:
                formants.append(formants[-1] * 1.2 if formants else 800.0)
            
            return formants[:4]
            
        except Exception as e:
            logger.error(f"Error extracting formants: {e}")
            return [800.0, 1200.0, 2400.0, 3200.0]

    async def _extract_spectral_envelope(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Extract spectral envelope representing overall voice timbre."""
        if len(audio) == 0:
            return np.ones(256)  # Default envelope
        
        try:
            # Compute magnitude spectrum
            fft = np.abs(np.fft.rfft(audio))
            
            # Smooth to get envelope
            window_size = max(1, len(fft) // 64)
            envelope = np.convolve(fft, np.ones(window_size)/window_size, mode='same')
            
            # Downsample to standard size
            if len(envelope) > 256:
                indices = np.linspace(0, len(envelope)-1, 256, dtype=int)
                envelope = envelope[indices]
            elif len(envelope) < 256:
                # Interpolate to 256 points
                old_indices = np.linspace(0, 255, len(envelope))
                new_indices = np.linspace(0, 255, 256)
                f = interp1d(old_indices, envelope, kind='linear', fill_value='extrapolate')
                envelope = f(new_indices)
            
            return envelope
            
        except Exception as e:
            logger.error(f"Error extracting spectral envelope: {e}")
            return np.ones(256)

    async def _extract_pitch_contour(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Extract pitch contour over time."""
        if len(audio) == 0:
            return np.array([150.0] * 100)  # Default contour
        
        try:
            # Divide audio into frames
            frame_size = int(sample_rate * 0.025)  # 25ms frames
            hop_size = int(sample_rate * 0.01)     # 10ms hop
            
            pitch_values = []
            
            for i in range(0, len(audio) - frame_size, hop_size):
                frame = audio[i:i + frame_size]
                
                # Simple autocorrelation pitch detection for frame
                correlation = np.correlate(frame, frame, mode='full')
                correlation = correlation[len(correlation)//2:]
                
                min_period = int(sample_rate * 0.002)  # 2ms (500 Hz)
                max_period = int(sample_rate * 0.02)   # 20ms (50 Hz)
                
                if max_period < len(correlation):
                    peak_idx = np.argmax(correlation[min_period:max_period]) + min_period
                    pitch = sample_rate / peak_idx
                else:
                    pitch = 150.0  # Default
                
                pitch_values.append(pitch)
            
            return np.array(pitch_values)
            
        except Exception as e:
            logger.error(f"Error extracting pitch contour: {e}")
            return np.array([150.0] * 100)

    async def _extract_energy_profile(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Extract energy profile over time."""
        if len(audio) == 0:
            return np.array([0.1] * 100)
        
        try:
            # RMS energy in frames
            frame_size = int(sample_rate * 0.025)  # 25ms frames
            hop_size = int(sample_rate * 0.01)     # 10ms hop
            
            energy_values = []
            
            for i in range(0, len(audio) - frame_size, hop_size):
                frame = audio[i:i + frame_size]
                rms_energy = np.sqrt(np.mean(frame**2))
                energy_values.append(rms_energy)
            
            return np.array(energy_values)
            
        except Exception as e:
            logger.error(f"Error extracting energy profile: {e}")
            return np.array([0.1] * 100)

    async def _analyze_voice_quality(self, audio: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """Analyze voice quality characteristics."""
        if len(audio) == 0:
            return {'clarity': 0.5, 'breathiness': 0.3, 'roughness': 0.2, 'strain': 0.1}
        
        try:
            # Compute spectral characteristics
            fft = np.abs(np.fft.rfft(audio))
            freqs = np.fft.rfftfreq(len(audio), 1/sample_rate)
            
            # Harmonic-to-noise ratio (clarity indicator)
            fundamental = await self._extract_fundamental_frequency(audio, sample_rate)
            harmonic_energy = 0
            noise_energy = 0
            
            for i, freq in enumerate(freqs):
                if freq > 50 and freq < sample_rate/2:
                    # Check if frequency is near a harmonic
                    harmonic_distance = min(abs(freq - n*fundamental) for n in range(1, 10))
                    if harmonic_distance < 20:  # Within 20 Hz of harmonic
                        harmonic_energy += fft[i]**2
                    else:
                        noise_energy += fft[i]**2
            
            hnr = harmonic_energy / max(noise_energy, 1e-10)
            clarity = min(1.0, hnr / 10.0)  # Normalize
            
            # Spectral centroid (brightness)
            spectral_centroid = np.sum(freqs * fft) / np.sum(fft)
            brightness = min(1.0, spectral_centroid / 2000.0)
            
            # High-frequency energy (breathiness indicator)
            high_freq_energy = np.sum(fft[freqs > 4000]**2)
            total_energy = np.sum(fft**2)
            breathiness = high_freq_energy / max(total_energy, 1e-10)
            
            # Spectral irregularity (roughness indicator)
            spectral_diff = np.diff(fft)
            roughness = np.mean(np.abs(spectral_diff)) / np.mean(fft)
            
            return {
                'clarity': float(clarity),
                'brightness': float(brightness),
                'breathiness': float(min(1.0, breathiness * 5)),
                'roughness': float(min(1.0, roughness))
            }
            
        except Exception as e:
            logger.error(f"Error analyzing voice quality: {e}")
            return {'clarity': 0.5, 'brightness': 0.5, 'breathiness': 0.3, 'roughness': 0.2}

    async def _extract_prosodic_features(self, audio: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """Extract prosodic features (rhythm, stress, intonation)."""
        if len(audio) == 0:
            return {'rhythm_regularity': 0.5, 'stress_variation': 0.5, 'intonation_range': 0.5}
        
        try:
            # Extract pitch and energy contours
            pitch_contour = await self._extract_pitch_contour(audio, sample_rate)
            energy_profile = await self._extract_energy_profile(audio, sample_rate)
            
            # Rhythm regularity (based on energy peaks)
            peaks = []
            for i in range(1, len(energy_profile)-1):
                if energy_profile[i] > energy_profile[i-1] and energy_profile[i] > energy_profile[i+1]:
                    if energy_profile[i] > np.mean(energy_profile) * 1.2:
                        peaks.append(i)
            
            if len(peaks) > 2:
                intervals = np.diff(peaks)
                rhythm_regularity = 1.0 - (np.std(intervals) / np.mean(intervals))
                rhythm_regularity = max(0.0, min(1.0, rhythm_regularity))
            else:
                rhythm_regularity = 0.5
            
            # Stress variation (based on pitch and energy changes)
            pitch_variation = np.std(pitch_contour) / np.mean(pitch_contour)
            energy_variation = np.std(energy_profile) / np.mean(energy_profile)
            stress_variation = min(1.0, (pitch_variation + energy_variation) / 2)
            
            # Intonation range (pitch range)
            if len(pitch_contour) > 0:
                pitch_range = np.max(pitch_contour) - np.min(pitch_contour)
                intonation_range = min(1.0, pitch_range / 200.0)  # Normalize to 200 Hz range
            else:
                intonation_range = 0.5
            
            return {
                'rhythm_regularity': float(rhythm_regularity),
                'stress_variation': float(stress_variation),
                'intonation_range': float(intonation_range)
            }
            
        except Exception as e:
            logger.error(f"Error extracting prosodic features: {e}")
            return {'rhythm_regularity': 0.5, 'stress_variation': 0.5, 'intonation_range': 0.5}

    async def _analyze_phonetics(self, audio: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """Analyze phonetic characteristics of the voice."""
        if len(audio) == 0:
            return {'vowel_space': 'average', 'consonant_clarity': 0.5, 'articulation_rate': 'medium'}
        
        try:
            # Simplified phonetic analysis
            formants = await self._extract_formants(audio, sample_rate)
            
            # Vowel space analysis (based on F1 and F2)
            f1, f2 = formants[0], formants[1]
            
            if f1 < 400 and f2 > 2000:
                vowel_space = 'front_high'  # i, e sounds
            elif f1 > 700 and f2 > 1500:
                vowel_space = 'front_low'   # ae sounds
            elif f1 > 700 and f2 < 1000:
                vowel_space = 'back_low'    # ah sounds
            elif f1 < 400 and f2 < 1000:
                vowel_space = 'back_high'   # u sounds
            else:
                vowel_space = 'central'     # schwa, etc.
            
            # Consonant clarity (based on spectral characteristics)
            fft = np.abs(np.fft.rfft(audio))
            freqs = np.fft.rfftfreq(len(audio), 1/sample_rate)
            
            # High-frequency content indicates good consonant articulation
            high_freq_energy = np.sum(fft[freqs > 2000]**2)
            total_energy = np.sum(fft**2)
            consonant_clarity = high_freq_energy / max(total_energy, 1e-10)
            consonant_clarity = min(1.0, consonant_clarity * 3)  # Scale appropriately
            
            # Articulation rate (estimated from zero crossings)
            zero_crossings = np.sum(np.diff(np.sign(audio)) != 0)
            articulation_rate_hz = zero_crossings / (2 * len(audio) / sample_rate)
            
            if articulation_rate_hz < 5:
                articulation_rate = 'slow'
            elif articulation_rate_hz > 15:
                articulation_rate = 'fast'
            else:
                articulation_rate = 'medium'
            
            return {
                'vowel_space': vowel_space,
                'consonant_clarity': float(consonant_clarity),
                'articulation_rate': articulation_rate,
                'formant_density': len([f for f in formants if 200 < f < 4000])
            }
            
        except Exception as e:
            logger.error(f"Error analyzing phonetics: {e}")
            return {'vowel_space': 'central', 'consonant_clarity': 0.5, 'articulation_rate': 'medium'}

    async def _determine_emotional_baseline(self, audio: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """Determine emotional baseline of the voice sample."""
        if len(audio) == 0:
            return {'neutral': 1.0, 'happy': 0.0, 'sad': 0.0, 'angry': 0.0, 'excited': 0.0}
        
        try:
            # Extract features for emotion recognition
            pitch_contour = await self._extract_pitch_contour(audio, sample_rate)
            energy_profile = await self._extract_energy_profile(audio, sample_rate)
            
            # Emotion indicators
            emotions = {'neutral': 0.5, 'happy': 0.0, 'sad': 0.0, 'angry': 0.0, 'excited': 0.0}
            
            if len(pitch_contour) > 0 and len(energy_profile) > 0:
                avg_pitch = np.mean(pitch_contour)
                pitch_variation = np.std(pitch_contour)
                avg_energy = np.mean(energy_profile)
                energy_variation = np.std(energy_profile)
                
                # Happy: high pitch variation, moderate to high energy
                if pitch_variation > 30 and avg_energy > 0.1:
                    emotions['happy'] = min(1.0, (pitch_variation / 50) * (avg_energy / 0.2))
                
                # Sad: low energy, low pitch variation
                if avg_energy < 0.05 and pitch_variation < 20:
                    emotions['sad'] = min(1.0, (1 - avg_energy/0.1) * (1 - pitch_variation/30))
                
                # Angry: high energy, high pitch
                if avg_energy > 0.15 and avg_pitch > 180:
                    emotions['angry'] = min(1.0, (avg_energy / 0.3) * (avg_pitch / 250))
                
                # Excited: high energy, high pitch variation
                if avg_energy > 0.12 and pitch_variation > 40:
                    emotions['excited'] = min(1.0, (avg_energy / 0.2) * (pitch_variation / 60))
            
            # Normalize so they sum to 1
            total = sum(emotions.values())
            if total > 0:
                emotions = {k: v/total for k, v in emotions.items()}
            else:
                emotions['neutral'] = 1.0
            
            return emotions
            
        except Exception as e:
            logger.error(f"Error determining emotional baseline: {e}")
            return {'neutral': 1.0, 'happy': 0.0, 'sad': 0.0, 'angry': 0.0, 'excited': 0.0}

    async def _extract_accent_markers(self, audio: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """Extract accent markers from voice sample."""
        if len(audio) == 0:
            return {'general_american': 1.0}
        
        try:
            formants = await self._extract_formants(audio, sample_rate)
            prosodic_features = await self._extract_prosodic_features(audio, sample_rate)
            
            # Simplified accent detection based on formant patterns
            accents = {
                'general_american': 0.5,
                'british': 0.0,
                'fantasy_noble': 0.0,
                'fantasy_common': 0.0,
                'draconic_influenced': 0.0,
                'elvish_influenced': 0.0
            }
            
            f1, f2, f3 = formants[0], formants[1], formants[2]
            
            # British indicators (simplified)
            if f2 < 1600 and prosodic_features['rhythm_regularity'] > 0.6:
                accents['british'] = 0.3
            
            # Fantasy noble (clear, precise articulation)
            if prosodic_features['stress_variation'] < 0.4 and f2 > 1800:
                accents['fantasy_noble'] = 0.4
            
            # Fantasy common (relaxed articulation)
            if prosodic_features['rhythm_regularity'] < 0.4:
                accents['fantasy_common'] = 0.3
            
            # Draconic influenced (low formants, rough quality)
            if f1 < 600 and f2 < 1200:
                accents['draconic_influenced'] = 0.2
            
            # Elvish influenced (high, clear formants)
            if f1 < 400 and f2 > 2000 and f3 > 2800:
                accents['elvish_influenced'] = 0.3
            
            # Normalize
            total = sum(accents.values())
            if total > 0:
                accents = {k: v/total for k, v in accents.items()}
            
            return accents
            
        except Exception as e:
            logger.error(f"Error extracting accent markers: {e}")
            return {'general_american': 1.0}

    async def generate_transformation(self, source_voice_id: str, target_voice_id: str) -> VoiceTransformation:
        """Generate voice transformation from source to target."""
        if source_voice_id not in self.voice_prints or target_voice_id not in self.voice_prints:
            raise ValueError("Voice prints not found")
        
        source_print = self.voice_prints[source_voice_id]
        target_print = self.voice_prints[target_voice_id]
        
        # Calculate transformation parameters
        pitch_shift_ratio = target_print.fundamental_freq / source_print.fundamental_freq
        
        # Formant shifts
        formant_shifts = []
        for i in range(min(len(source_print.formant_frequencies), len(target_print.formant_frequencies))):
            shift = target_print.formant_frequencies[i] / source_print.formant_frequencies[i]
            formant_shifts.append(shift)
        
        # Energy adjustment
        source_energy = np.mean(source_print.energy_profile)
        target_energy = np.mean(target_print.energy_profile)
        energy_adjustment = target_energy / max(source_energy, 1e-10)
        
        # Quality modifications
        quality_modifications = {}
        for quality in target_print.voice_quality_markers:
            if quality in source_print.voice_quality_markers:
                quality_modifications[quality] = (
                    target_print.voice_quality_markers[quality] - 
                    source_print.voice_quality_markers[quality]
                )
        
        # Create transformation matrix (simplified)
        transformation_matrix = np.eye(256)  # Identity matrix for spectral envelope transformation
        
        # Calculate confidence based on similarity
        confidence_score = await self._calculate_transformation_confidence(source_print, target_print)
        
        transformation = VoiceTransformation(
            source_voice_id=source_voice_id,
            target_voice_id=target_voice_id,
            transformation_matrix=transformation_matrix,
            pitch_shift_ratio=pitch_shift_ratio,
            formant_shifts=formant_shifts,
            energy_adjustment=energy_adjustment,
            quality_modifications=quality_modifications,
            confidence_score=confidence_score
        )
        
        # Cache the transformation
        self.transformations[(source_voice_id, target_voice_id)] = transformation
        
        return transformation

    async def _calculate_transformation_confidence(self, source: VoicePrint, target: VoicePrint) -> float:
        """Calculate confidence score for voice transformation."""
        try:
            # Compare key features
            pitch_similarity = 1.0 - abs(target.fundamental_freq - source.fundamental_freq) / max(target.fundamental_freq, source.fundamental_freq)
            
            # Formant similarity
            formant_similarity = 0.0
            for i in range(min(len(source.formant_frequencies), len(target.formant_frequencies))):
                f_sim = 1.0 - abs(target.formant_frequencies[i] - source.formant_frequencies[i]) / max(target.formant_frequencies[i], source.formant_frequencies[i])
                formant_similarity += f_sim
            formant_similarity /= max(1, min(len(source.formant_frequencies), len(target.formant_frequencies)))
            
            # Voice quality similarity
            quality_similarity = 0.0
            quality_count = 0
            for quality in source.voice_quality_markers:
                if quality in target.voice_quality_markers:
                    q_sim = 1.0 - abs(target.voice_quality_markers[quality] - source.voice_quality_markers[quality])
                    quality_similarity += q_sim
                    quality_count += 1
            
            if quality_count > 0:
                quality_similarity /= quality_count
            else:
                quality_similarity = 0.5
            
            # Overall confidence
            confidence = (pitch_similarity * 0.3 + formant_similarity * 0.4 + quality_similarity * 0.3)
            return max(0.1, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating transformation confidence: {e}")
            return 0.5

    async def start_real_time_transformation(self, session_id: str, dm_voice_id: str, 
                                           target_character: str) -> RealTimeVoiceConfig:
        """Start real-time voice transformation for a session."""
        target_voice_id = None
        for voice_id, voice_print in self.voice_prints.items():
            if voice_print.character_name == target_character:
                target_voice_id = voice_id
                break
        
        if not target_voice_id:
            raise ValueError(f"No voice print found for character: {target_character}")
        
        # Generate or retrieve transformation
        if (dm_voice_id, target_voice_id) in self.transformations:
            transformation = self.transformations[(dm_voice_id, target_voice_id)]
        else:
            transformation = await self.generate_transformation(dm_voice_id, target_voice_id)
        
        # Create real-time config
        config = RealTimeVoiceConfig(
            target_character=target_character,
            transformation=transformation,
            emotional_modifiers={'neutral': 1.0},
            age_adjustment=0.0,
            gender_shift=0.0,
            accent_preservation=1.0,
            quality_enhancement=True
        )
        
        self.active_transformations[session_id] = config
        
        # Start real-time processing
        await self.real_time_processor.start_transformation(session_id, config)
        
        return config

    async def apply_emotional_modification(self, session_id: str, emotion: str, intensity: float):
        """Apply emotional modification to active transformation."""
        if session_id not in self.active_transformations:
            return
        
        config = self.active_transformations[session_id]
        config.emotional_modifiers[emotion] = intensity
        
        # Update real-time processor
        await self.real_time_processor.update_emotional_state(session_id, emotion, intensity)

    async def apply_age_gender_transformation(self, session_id: str, age_shift: float, gender_shift: float):
        """Apply age and gender transformations."""
        if session_id not in self.active_transformations:
            return
        
        config = self.active_transformations[session_id]
        config.age_adjustment = age_shift
        config.gender_shift = gender_shift
        
        await self.real_time_processor.update_age_gender(session_id, age_shift, gender_shift)

    async def process_voice_command(self, session_id: str, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Process voice input for commands."""
        try:
            # Transcribe audio
            from .voice_processor import VoiceProcessor
            voice_processor = VoiceProcessor()
            transcription = await voice_processor.transcribe_audio(audio_data)
            
            if not transcription or transcription == "[Inaudible speech]":
                return None
            
            # Check against command patterns
            for command_name, command in self.voice_commands.items():
                pattern = command.parameters.get('pattern')
                if pattern:
                    import re
                    match = re.search(pattern, transcription, re.IGNORECASE)
                    if match:
                        # Process command
                        result = await self._execute_voice_command(
                            session_id, command_name, command, match, transcription
                        )
                        return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing voice command: {e}")
            return None

    async def _execute_voice_command(self, session_id: str, command_name: str, 
                                   command: VoiceCommand, match, transcription: str) -> Dict[str, Any]:
        """Execute a recognized voice command."""
        if command.command_type == 'dice_roll':
            # Extract dice parameters
            num_dice = int(match.group(1))
            die_sides = int(match.group(2))
            modifier = int(match.group(3)) if match.group(3) else 0
            
            # Roll dice
            import random
            rolls = [random.randint(1, die_sides) for _ in range(num_dice)]
            total = sum(rolls) + modifier
            
            return {
                'command_type': 'dice_roll',
                'transcription': transcription,
                'parameters': {
                    'num_dice': num_dice,
                    'die_sides': die_sides,
                    'modifier': modifier,
                    'rolls': rolls,
                    'total': total
                },
                'response': f"Rolling {num_dice}d{die_sides}{'+' + str(modifier) if modifier else ''}: {rolls} = {total}"
            }
        
        elif command.command_type == 'combat_action':
            target = match.group(1) if match.group(1) else 'unknown'
            
            return {
                'command_type': 'combat_action',
                'transcription': transcription,
                'parameters': {
                    'action': 'attack',
                    'target': target
                },
                'response': f"Attacking {target}!"
            }
        
        elif command.command_type == 'character_switch':
            character = match.group(1)
            
            # Switch to character voice if available
            result = await self._switch_character_voice(session_id, character)
            
            return {
                'command_type': 'character_switch',
                'transcription': transcription,
                'parameters': {
                    'character': character,
                    'switch_successful': result
                },
                'response': f"Switching to {character}" if result else f"No voice found for {character}"
            }
        
        elif command.command_type == 'dm_action':
            encounter_type = match.group(1)
            
            return {
                'command_type': 'dm_action',
                'transcription': transcription,
                'parameters': {
                    'action': 'create_encounter',
                    'encounter_type': encounter_type
                },
                'response': f"Creating {encounter_type} encounter..."
            }
        
        else:
            return {
                'command_type': command.command_type,
                'transcription': transcription,
                'parameters': {},
                'response': f"Executed {command_name}"
            }

    async def _switch_character_voice(self, session_id: str, character_name: str) -> bool:
        """Switch active voice transformation to different character."""
        # Find character voice print
        target_voice_id = None
        for voice_id, voice_print in self.voice_prints.items():
            if voice_print.character_name.lower() == character_name.lower():
                target_voice_id = voice_id
                break
        
        if not target_voice_id:
            return False
        
        # Get current config
        if session_id not in self.active_transformations:
            return False
        
        current_config = self.active_transformations[session_id]
        dm_voice_id = current_config.transformation.source_voice_id
        
        try:
            # Create new transformation
            new_transformation = await self.generate_transformation(dm_voice_id, target_voice_id)
            
            # Update config
            current_config.target_character = character_name
            current_config.transformation = new_transformation
            
            # Update real-time processor
            await self.real_time_processor.update_transformation(session_id, new_transformation)
            
            return True
            
        except Exception as e:
            logger.error(f"Error switching character voice: {e}")
            return False

    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voice prints."""
        voices = []
        for voice_id, voice_print in self.voice_prints.items():
            voices.append({
                'voice_id': voice_id,
                'character_name': voice_print.character_name,
                'fundamental_freq': voice_print.fundamental_freq,
                'voice_quality': voice_print.voice_quality_markers,
                'emotional_baseline': voice_print.emotional_baseline,
                'accent_type': max(voice_print.accent_markers.items(), key=lambda x: x[1])[0],
                'created_at': voice_print.created_at.isoformat()
            })
        
        return voices

    def stop_real_time_transformation(self, session_id: str):
        """Stop real-time voice transformation for a session."""
        if session_id in self.active_transformations:
            del self.active_transformations[session_id]
        
        asyncio.create_task(self.real_time_processor.stop_transformation(session_id))

class RealTimeVoiceProcessor:
    """Handle real-time voice processing and transformation."""
    
    def __init__(self):
        self.active_sessions = {}  # session_id -> processing_config
        self.audio_buffers = {}    # session_id -> audio buffer
    
    async def start_transformation(self, session_id: str, config: RealTimeVoiceConfig):
        """Start real-time transformation for a session."""
        self.active_sessions[session_id] = {
            'config': config,
            'active': True,
            'buffer_size': 1024,
            'processing_delay': 0.05  # 50ms delay
        }
        
        self.audio_buffers[session_id] = []
        logger.info(f"Started real-time voice transformation for session {session_id}")
    
    async def process_audio_chunk(self, session_id: str, audio_chunk: bytes) -> bytes:
        """Process a chunk of audio in real-time."""
        if session_id not in self.active_sessions:
            return audio_chunk  # Pass through unprocessed
        
        try:
            # Convert audio chunk to numpy array
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Apply transformation
            config = self.active_sessions[session_id]['config']
            transformed_audio = await self._apply_real_time_transformation(audio_array, config)
            
            # Convert back to bytes
            transformed_chunk = (transformed_audio * 32767).astype(np.int16).tobytes()
            
            return transformed_chunk
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            return audio_chunk  # Return original on error
    
    async def _apply_real_time_transformation(self, audio: np.ndarray, config: RealTimeVoiceConfig) -> np.ndarray:
        """Apply real-time voice transformation to audio."""
        if len(audio) == 0:
            return audio
        
        try:
            # Apply pitch shift
            pitch_shifted = await self._apply_pitch_shift(audio, config.transformation.pitch_shift_ratio)
            
            # Apply formant shifts (simplified)
            formant_shifted = await self._apply_formant_shifts(pitch_shifted, config.transformation.formant_shifts)
            
            # Apply energy adjustment
            energy_adjusted = formant_shifted * config.transformation.energy_adjustment
            
            # Apply emotional modifications
            emotion_modified = await self._apply_emotional_modifiers(energy_adjusted, config.emotional_modifiers)
            
            # Apply age/gender adjustments
            age_gender_modified = await self._apply_age_gender_effects(emotion_modified, config.age_adjustment, config.gender_shift)
            
            # Ensure output is in valid range
            transformed = np.clip(age_gender_modified, -1.0, 1.0)
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error in real-time transformation: {e}")
            return audio
    
    async def _apply_pitch_shift(self, audio: np.ndarray, shift_ratio: float) -> np.ndarray:
        """Apply pitch shifting to audio."""
        if abs(shift_ratio - 1.0) < 0.01:  # No significant shift needed
            return audio
        
        try:
            # Simple time-domain pitch shifting (phase vocoder would be better)
            if shift_ratio > 1.0:
                # Higher pitch - compress time then stretch
                compressed_length = int(len(audio) / shift_ratio)
                indices = np.linspace(0, len(audio)-1, compressed_length)
                compressed = np.interp(indices, range(len(audio)), audio)
                return compressed
            else:
                # Lower pitch - stretch time then compress
                stretched_length = int(len(audio) / shift_ratio)
                indices = np.linspace(0, len(audio)-1, stretched_length)
                stretched = np.interp(indices, range(len(audio)), audio)
                # Compress back to original length
                final_indices = np.linspace(0, len(stretched)-1, len(audio))
                return np.interp(final_indices, range(len(stretched)), stretched)
        
        except Exception as e:
            logger.error(f"Error in pitch shift: {e}")
            return audio
    
    async def _apply_formant_shifts(self, audio: np.ndarray, formant_shifts: List[float]) -> np.ndarray:
        """Apply formant frequency shifts (simplified)."""
        if not formant_shifts or all(abs(s - 1.0) < 0.01 for s in formant_shifts):
            return audio
        
        try:
            # Simple spectral shifting approximation
            fft = np.fft.fft(audio)
            
            # Apply frequency domain scaling (very simplified)
            if len(formant_shifts) > 0:
                avg_shift = np.mean(formant_shifts)
                # Shift the spectrum slightly
                shifted_fft = np.zeros_like(fft, dtype=complex)
                for i, val in enumerate(fft):
                    new_index = int(i * avg_shift)
                    if 0 <= new_index < len(shifted_fft):
                        shifted_fft[new_index] = val
                
                return np.real(np.fft.ifft(shifted_fft))
            
            return audio
            
        except Exception as e:
            logger.error(f"Error in formant shift: {e}")
            return audio
    
    async def _apply_emotional_modifiers(self, audio: np.ndarray, emotional_modifiers: Dict[str, float]) -> np.ndarray:
        """Apply emotional modifications to audio."""
        try:
            modified_audio = audio.copy()
            
            for emotion, intensity in emotional_modifiers.items():
                if intensity > 0.1:  # Only apply if significant
                    if emotion == 'angry':
                        # Increase energy and add slight distortion
                        modified_audio *= (1.0 + intensity * 0.3)
                        # Add slight harmonic distortion
                        modified_audio = np.tanh(modified_audio * (1 + intensity * 0.5))
                    
                    elif emotion == 'sad':
                        # Reduce energy and add tremolo
                        modified_audio *= (1.0 - intensity * 0.2)
                        # Add slight tremolo effect
                        tremolo = 1.0 + intensity * 0.1 * np.sin(2 * np.pi * 5 * np.linspace(0, len(audio)/16000, len(audio)))
                        modified_audio *= tremolo[:len(modified_audio)]
                    
                    elif emotion == 'happy':
                        # Slight energy increase and brightness
                        modified_audio *= (1.0 + intensity * 0.15)
                    
                    elif emotion == 'excited':
                        # Increase dynamics
                        modified_audio *= (1.0 + intensity * 0.25)
            
            return np.clip(modified_audio, -1.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error applying emotional modifiers: {e}")
            return audio
    
    async def _apply_age_gender_effects(self, audio: np.ndarray, age_adjustment: float, gender_shift: float) -> np.ndarray:
        """Apply age and gender transformation effects."""
        try:
            modified_audio = audio
            
            # Age effects
            if abs(age_adjustment) > 0.1:
                if age_adjustment > 0:  # Older voice
                    # Add slight tremor and reduce high frequencies
                    tremor = 1.0 + age_adjustment * 0.05 * np.sin(2 * np.pi * 8 * np.linspace(0, len(audio)/16000, len(audio)))
                    modified_audio *= tremor[:len(modified_audio)]
                else:  # Younger voice
                    # Increase brightness slightly
                    modified_audio *= (1.0 + abs(age_adjustment) * 0.1)
            
            # Gender effects (simplified)
            if abs(gender_shift) > 0.1:
                # This would typically involve formant shifting
                # For now, just apply a slight pitch adjustment
                pitch_adjustment = 1.0 + gender_shift * 0.2
                if pitch_adjustment != 1.0:
                    modified_audio = await self._apply_pitch_shift(modified_audio, pitch_adjustment)
            
            return np.clip(modified_audio, -1.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error applying age/gender effects: {e}")
            return audio
    
    async def update_transformation(self, session_id: str, new_transformation: VoiceTransformation):
        """Update the transformation for an active session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['config'].transformation = new_transformation
    
    async def update_emotional_state(self, session_id: str, emotion: str, intensity: float):
        """Update emotional state for active transformation."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['config'].emotional_modifiers[emotion] = intensity
    
    async def update_age_gender(self, session_id: str, age_shift: float, gender_shift: float):
        """Update age and gender adjustments."""
        if session_id in self.active_sessions:
            config = self.active_sessions[session_id]['config']
            config.age_adjustment = age_shift
            config.gender_shift = gender_shift
    
    async def stop_transformation(self, session_id: str):
        """Stop transformation for a session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.audio_buffers:
            del self.audio_buffers[session_id]
        
        logger.info(f"Stopped real-time voice transformation for session {session_id}")