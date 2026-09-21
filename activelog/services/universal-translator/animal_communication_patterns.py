"""
Animal Communication Patterns System

This module provides comprehensive analysis and interpretation of animal communication
patterns, including vocalizations, body language, chemical signals, and interspecies
communication translation.
"""

import asyncio
import json
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from enum import Enum
from datetime import datetime, timedelta
import librosa
import scipy.signal
from scipy import stats

class AnimalSpecies(Enum):
    """Supported animal species for communication analysis"""
    DOLPHINS = "dolphins"
    WHALES = "whales"
    ELEPHANTS = "elephants"
    PRIMATES = "primates"
    BIRDS = "birds"
    WOLVES = "wolves"
    DOGS = "dogs"
    CATS = "cats"
    BEES = "bees"
    ANTS = "ants"
    CUTTLEFISH = "cuttlefish"
    OCTOPUS = "octopus"
    HORSES = "horses"
    CATTLE = "cattle"
    SHEEP = "sheep"
    PIGS = "pigs"
    CHICKENS = "chickens"
    FROGS = "frogs"
    CRICKETS = "crickets"
    BATS = "bats"

class CommunicationModality(Enum):
    """Types of animal communication modalities"""
    ACOUSTIC = "acoustic"  # Sounds and vocalizations
    VISUAL = "visual"  # Body language, coloration, displays
    CHEMICAL = "chemical"  # Pheromones, scent marking
    TACTILE = "tactile"  # Touch, vibrations
    ELECTRICAL = "electrical"  # Electrical fields (sharks, electric fish)
    MAGNETIC = "magnetic"  # Magnetic field detection
    BIORHYTHMIC = "biorhythmic"  # Temporal patterns, circadian signals

class MessageType(Enum):
    """Types of messages animals communicate"""
    ALARM_CALL = "alarm_call"
    MATING_CALL = "mating_call"
    TERRITORIAL_CLAIM = "territorial_claim"
    FOOD_LOCATION = "food_location"
    SOCIAL_BONDING = "social_bonding"
    DOMINANCE_DISPLAY = "dominance_display"
    SUBMISSION = "submission"
    PLAY_INVITATION = "play_invitation"
    DISTRESS_CALL = "distress_call"
    NAVIGATION_SIGNAL = "navigation_signal"
    GROUP_COORDINATION = "group_coordination"
    WARNING = "warning"
    GREETING = "greeting"
    REQUEST = "request"
    COMFORT = "comfort"

class CommunicationContext(Enum):
    """Environmental and social contexts for communication"""
    FEEDING = "feeding"
    BREEDING = "breeding"
    PARENTING = "parenting"
    PREDATOR_PRESENCE = "predator_presence"
    TERRITORIAL_DISPUTE = "territorial_dispute"
    MIGRATION = "migration"
    PLAY_BEHAVIOR = "play_behavior"
    GROOMING = "grooming"
    RESTING = "resting"
    EXPLORATION = "exploration"
    DANGER = "danger"
    SOCIAL_INTERACTION = "social_interaction"

@dataclass
class AcousticSignal:
    """Represents an acoustic communication signal"""
    frequency_range: Tuple[float, float]  # Hz
    duration: float  # seconds
    amplitude: float
    modulation_type: str  # "FM", "AM", "constant", "complex"
    harmonics: List[float]
    peak_frequency: float
    bandwidth: float
    signal_type: str  # "whistle", "click", "growl", "chirp", etc.
    temporal_pattern: str  # "single", "repeated", "burst", "trill"

@dataclass
class VisualSignal:
    """Represents a visual communication signal"""
    signal_type: str  # "posture", "color_change", "movement", "display"
    body_parts_involved: List[str]
    intensity: float
    duration: float
    spatial_pattern: str  # "localized", "whole_body", "directional"
    color_changes: Optional[Dict[str, str]] = None
    movement_pattern: Optional[str] = None

@dataclass
class ChemicalSignal:
    """Represents a chemical communication signal"""
    signal_type: str  # "pheromone", "scent_mark", "secretion"
    chemical_compounds: List[str]
    concentration: float
    persistence: float  # how long signal lasts
    volatility: str  # "high", "medium", "low"
    detection_method: str  # "airborne", "contact", "taste"
    molecular_weight: Optional[float] = None

@dataclass
class CommunicationEvent:
    """Represents a complete communication event"""
    species: AnimalSpecies
    timestamp: float
    modality: CommunicationModality
    message_type: MessageType
    context: CommunicationContext
    signal_data: Union[AcousticSignal, VisualSignal, ChemicalSignal]
    sender_id: Optional[str] = None
    receiver_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    environmental_factors: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SpeciesProfile:
    """Profile of communication capabilities for a species"""
    species: AnimalSpecies
    primary_modalities: List[CommunicationModality]
    frequency_range: Optional[Tuple[float, float]] = None
    typical_messages: List[MessageType] = field(default_factory=list)
    social_structure: str = "unknown"
    communication_complexity: str = "low"  # low, medium, high, very_high
    learning_capacity: str = "limited"  # limited, moderate, high, exceptional
    interspecies_communication: bool = False
    unique_features: List[str] = field(default_factory=list)

@dataclass
class TranslationResult:
    """Result of animal communication translation"""
    source_species: AnimalSpecies
    target_format: str  # "human_language", "other_species", "symbolic"
    original_signals: List[CommunicationEvent]
    translated_message: str
    confidence: float
    processing_time: float
    interpretation_notes: List[str]
    behavioral_context: str
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class SpeciesDatabase:
    """Database of animal communication profiles and patterns"""
    
    def __init__(self):
        self.species_profiles = self._initialize_species_profiles()
        self.communication_patterns = self._initialize_communication_patterns()
        
    def _initialize_species_profiles(self) -> Dict[AnimalSpecies, SpeciesProfile]:
        """Initialize species communication profiles"""
        profiles = {
            AnimalSpecies.DOLPHINS: SpeciesProfile(
                species=AnimalSpecies.DOLPHINS,
                primary_modalities=[CommunicationModality.ACOUSTIC, CommunicationModality.VISUAL],
                frequency_range=(1000, 150000),  # 1kHz to 150kHz
                typical_messages=[MessageType.NAVIGATION_SIGNAL, MessageType.SOCIAL_BONDING, 
                                MessageType.GROUP_COORDINATION, MessageType.PLAY_INVITATION],
                social_structure="complex_social_groups",
                communication_complexity="very_high",
                learning_capacity="exceptional",
                interspecies_communication=True,
                unique_features=["echolocation", "signature_whistles", "mimicry", "dialects"]
            ),
            
            AnimalSpecies.WHALES: SpeciesProfile(
                species=AnimalSpecies.WHALES,
                primary_modalities=[CommunicationModality.ACOUSTIC],
                frequency_range=(10, 8000),  # 10Hz to 8kHz, some species lower
                typical_messages=[MessageType.MATING_CALL, MessageType.NAVIGATION_SIGNAL,
                                MessageType.GROUP_COORDINATION, MessageType.TERRITORIAL_CLAIM],
                social_structure="pods_and_migrations",
                communication_complexity="very_high",
                learning_capacity="high",
                interspecies_communication=False,
                unique_features=["long_distance_calls", "song_structures", "cultural_transmission"]
            ),
            
            AnimalSpecies.ELEPHANTS: SpeciesProfile(
                species=AnimalSpecies.ELEPHANTS,
                primary_modalities=[CommunicationModality.ACOUSTIC, CommunicationModality.VISUAL, 
                                  CommunicationModality.TACTILE, CommunicationModality.CHEMICAL],
                frequency_range=(5, 2000),  # Including infrasound
                typical_messages=[MessageType.ALARM_CALL, MessageType.GROUP_COORDINATION,
                                MessageType.SOCIAL_BONDING, MessageType.DOMINANCE_DISPLAY],
                social_structure="matriarchal_herds",
                communication_complexity="high",
                learning_capacity="high",
                interspecies_communication=False,
                unique_features=["infrasonic_calls", "trunk_gestures", "temporal_glands", "mourning_behavior"]
            ),
            
            AnimalSpecies.PRIMATES: SpeciesProfile(
                species=AnimalSpecies.PRIMATES,
                primary_modalities=[CommunicationModality.VISUAL, CommunicationModality.ACOUSTIC,
                                  CommunicationModality.TACTILE],
                frequency_range=(100, 8000),
                typical_messages=[MessageType.ALARM_CALL, MessageType.DOMINANCE_DISPLAY,
                                MessageType.SOCIAL_BONDING, MessageType.PLAY_INVITATION],
                social_structure="complex_hierarchical",
                communication_complexity="high",
                learning_capacity="exceptional",
                interspecies_communication=True,
                unique_features=["facial_expressions", "gestural_communication", "tool_use_signaling", "culture_transmission"]
            ),
            
            AnimalSpecies.BEES: SpeciesProfile(
                species=AnimalSpecies.BEES,
                primary_modalities=[CommunicationModality.VISUAL, CommunicationModality.CHEMICAL,
                                  CommunicationModality.TACTILE],
                frequency_range=None,
                typical_messages=[MessageType.FOOD_LOCATION, MessageType.NAVIGATION_SIGNAL,
                                MessageType.ALARM_CALL, MessageType.GROUP_COORDINATION],
                social_structure="eusocial_colony",
                communication_complexity="high",
                learning_capacity="moderate",
                interspecies_communication=False,
                unique_features=["waggle_dance", "pheromone_trails", "polarized_light_navigation", "geometric_communication"]
            ),
            
            AnimalSpecies.BIRDS: SpeciesProfile(
                species=AnimalSpecies.BIRDS,
                primary_modalities=[CommunicationModality.ACOUSTIC, CommunicationModality.VISUAL],
                frequency_range=(100, 20000),
                typical_messages=[MessageType.MATING_CALL, MessageType.TERRITORIAL_CLAIM,
                                MessageType.ALARM_CALL, MessageType.SOCIAL_BONDING],
                social_structure="varies_by_species",
                communication_complexity="high",
                learning_capacity="high",
                interspecies_communication=True,
                unique_features=["song_learning", "syntax_like_structures", "mimicry", "regional_dialects"]
            ),
            
            AnimalSpecies.DOGS: SpeciesProfile(
                species=AnimalSpecies.DOGS,
                primary_modalities=[CommunicationModality.VISUAL, CommunicationModality.ACOUSTIC,
                                  CommunicationModality.CHEMICAL],
                frequency_range=(67, 45000),
                typical_messages=[MessageType.GREETING, MessageType.PLAY_INVITATION,
                                MessageType.WARNING, MessageType.SUBMISSION],
                social_structure="pack_hierarchy",
                communication_complexity="medium",
                learning_capacity="high",
                interspecies_communication=True,
                unique_features=["human_gesture_reading", "referential_barking", "emotional_contagion"]
            ),
            
            AnimalSpecies.CATS: SpeciesProfile(
                species=AnimalSpecies.CATS,
                primary_modalities=[CommunicationModality.VISUAL, CommunicationModality.ACOUSTIC,
                                  CommunicationModality.CHEMICAL, CommunicationModality.TACTILE],
                frequency_range=(50, 64000),
                typical_messages=[MessageType.GREETING, MessageType.REQUEST,
                                MessageType.TERRITORIAL_CLAIM, MessageType.COMFORT],
                social_structure="semi_social",
                communication_complexity="medium",
                learning_capacity="moderate",
                interspecies_communication=True,
                unique_features=["purring", "scent_marking", "slow_blinking", "human_directed_vocalizations"]
            )
        }
        
        return profiles
    
    def _initialize_communication_patterns(self) -> Dict[AnimalSpecies, Dict[str, Any]]:
        """Initialize known communication patterns for species"""
        patterns = {
            AnimalSpecies.DOLPHINS: {
                "signature_whistle": {
                    "type": "individual_identification",
                    "frequency_range": (7000, 15000),
                    "duration": (0.5, 2.0),
                    "context": "social_interaction"
                },
                "echolocation_clicks": {
                    "type": "navigation_and_hunting",
                    "frequency_range": (40000, 130000),
                    "duration": (0.001, 0.1),
                    "context": "exploration"
                },
                "burst_pulse": {
                    "type": "aggressive_or_excited",
                    "frequency_range": (1000, 40000),
                    "duration": (0.1, 1.0),
                    "context": "social_interaction"
                }
            },
            
            AnimalSpecies.ELEPHANTS: {
                "infrasonic_rumble": {
                    "type": "long_distance_coordination",
                    "frequency_range": (5, 35),
                    "duration": (0.5, 10.0),
                    "context": "group_coordination"
                },
                "trumpet": {
                    "type": "alarm_or_excitement",
                    "frequency_range": (300, 3000),
                    "duration": (0.5, 3.0),
                    "context": "danger"
                },
                "trunk_slap": {
                    "type": "warning_display",
                    "modality": "visual_acoustic",
                    "context": "territorial_dispute"
                }
            },
            
            AnimalSpecies.BEES: {
                "waggle_dance": {
                    "type": "food_location_communication",
                    "modality": "visual_tactile",
                    "parameters": ["distance", "direction", "quality"],
                    "context": "feeding"
                },
                "queen_piping": {
                    "type": "queen_status_signal",
                    "frequency_range": (400, 600),
                    "context": "breeding"
                },
                "alarm_pheromone": {
                    "type": "danger_warning",
                    "modality": "chemical",
                    "compounds": ["isoamyl_acetate"],
                    "context": "danger"
                }
            },
            
            AnimalSpecies.BIRDS: {
                "dawn_chorus": {
                    "type": "territorial_and_mate_attraction",
                    "frequency_range": (1000, 8000),
                    "temporal_pattern": "early_morning",
                    "context": "breeding"
                },
                "mobbing_call": {
                    "type": "predator_harassment",
                    "frequency_range": (2000, 8000),
                    "duration": (0.1, 0.5),
                    "context": "predator_presence"
                },
                "contact_call": {
                    "type": "group_cohesion",
                    "frequency_range": (500, 4000),
                    "context": "migration"
                }
            }
        }
        
        return patterns

class AcousticAnalyzer:
    """Analyzes acoustic animal communication signals"""
    
    def __init__(self):
        self.species_db = SpeciesDatabase()
        
    async def analyze_acoustic_signal(self, audio_data: np.ndarray, sample_rate: int,
                                    species: AnimalSpecies) -> List[AcousticSignal]:
        """Analyze audio data for animal communication signals"""
        signals = []
        
        # Preprocessing
        filtered_audio = await self._preprocess_audio(audio_data, sample_rate, species)
        
        # Detect signal segments
        signal_segments = await self._detect_signal_segments(filtered_audio, sample_rate)
        
        # Analyze each segment
        for segment_start, segment_end in signal_segments:
            segment_audio = filtered_audio[segment_start:segment_end]
            
            # Extract acoustic features
            signal = await self._extract_acoustic_features(segment_audio, sample_rate, species)
            
            if signal:
                signals.append(signal)
        
        return signals
    
    async def _preprocess_audio(self, audio_data: np.ndarray, sample_rate: int, 
                               species: AnimalSpecies) -> np.ndarray:
        """Preprocess audio based on species characteristics"""
        species_profile = self.species_db.species_profiles.get(species)
        
        if species_profile and species_profile.frequency_range:
            # Apply species-specific frequency filtering
            low_freq, high_freq = species_profile.frequency_range
            
            # Design bandpass filter
            nyquist = sample_rate / 2
            low_norm = max(low_freq / nyquist, 0.01)
            high_norm = min(high_freq / nyquist, 0.99)
            
            if low_norm < high_norm:
                sos = scipy.signal.butter(4, [low_norm, high_norm], btype='band', output='sos')
                filtered_audio = scipy.signal.sosfilt(sos, audio_data)
            else:
                filtered_audio = audio_data
        else:
            filtered_audio = audio_data
        
        # Normalize amplitude
        if np.max(np.abs(filtered_audio)) > 0:
            filtered_audio = filtered_audio / np.max(np.abs(filtered_audio))
        
        return filtered_audio
    
    async def _detect_signal_segments(self, audio_data: np.ndarray, 
                                    sample_rate: int) -> List[Tuple[int, int]]:
        """Detect segments containing communication signals"""
        # Calculate short-time energy
        frame_length = int(0.025 * sample_rate)  # 25ms frames
        hop_length = frame_length // 2
        
        energy = []
        for i in range(0, len(audio_data) - frame_length, hop_length):
            frame = audio_data[i:i + frame_length]
            energy.append(np.sum(frame ** 2))
        
        energy = np.array(energy)
        
        # Adaptive threshold based on energy distribution
        threshold = np.mean(energy) + 1.5 * np.std(energy)
        
        # Find segments above threshold
        above_threshold = energy > threshold
        segments = []
        
        in_segment = False
        start_idx = 0
        
        for i, is_above in enumerate(above_threshold):
            if is_above and not in_segment:
                start_idx = i * hop_length
                in_segment = True
            elif not is_above and in_segment:
                end_idx = i * hop_length
                if end_idx - start_idx > sample_rate * 0.1:  # Minimum 100ms
                    segments.append((start_idx, end_idx))
                in_segment = False
        
        # Handle case where signal continues to end
        if in_segment:
            segments.append((start_idx, len(audio_data)))
        
        return segments
    
    async def _extract_acoustic_features(self, segment_audio: np.ndarray, 
                                       sample_rate: int, species: AnimalSpecies) -> Optional[AcousticSignal]:
        """Extract acoustic features from audio segment"""
        if len(segment_audio) == 0:
            return None
        
        # Calculate spectrogram
        stft = librosa.stft(segment_audio, hop_length=512)
        magnitude = np.abs(stft)
        
        # Frequency analysis
        freqs = librosa.fft_frequencies(sr=sample_rate)
        
        # Find dominant frequencies
        mean_magnitude = np.mean(magnitude, axis=1)
        peak_idx = np.argmax(mean_magnitude)
        peak_frequency = freqs[peak_idx]
        
        # Calculate frequency range (where magnitude > 10% of peak)
        threshold = 0.1 * np.max(mean_magnitude)
        significant_freqs = freqs[mean_magnitude > threshold]
        
        if len(significant_freqs) > 0:
            freq_min = np.min(significant_freqs)
            freq_max = np.max(significant_freqs)
        else:
            freq_min = freq_max = peak_frequency
        
        # Calculate bandwidth
        bandwidth = freq_max - freq_min
        
        # Calculate harmonics
        harmonics = await self._detect_harmonics(mean_magnitude, freqs, peak_frequency)
        
        # Determine signal type based on spectral characteristics
        signal_type = await self._classify_signal_type(magnitude, freqs, species)
        
        # Analyze temporal patterns
        temporal_pattern = await self._analyze_temporal_pattern(segment_audio, sample_rate)
        
        # Determine modulation type
        modulation_type = await self._analyze_modulation(magnitude)
        
        return AcousticSignal(
            frequency_range=(freq_min, freq_max),
            duration=len(segment_audio) / sample_rate,
            amplitude=np.max(np.abs(segment_audio)),
            modulation_type=modulation_type,
            harmonics=harmonics,
            peak_frequency=peak_frequency,
            bandwidth=bandwidth,
            signal_type=signal_type,
            temporal_pattern=temporal_pattern
        )
    
    async def _detect_harmonics(self, magnitude: np.ndarray, freqs: np.ndarray, 
                               fundamental: float) -> List[float]:
        """Detect harmonic frequencies"""
        harmonics = []
        
        # Look for harmonics up to the 6th harmonic
        for harmonic_num in range(2, 7):
            target_freq = fundamental * harmonic_num
            
            # Find closest frequency bin
            freq_idx = np.argmin(np.abs(freqs - target_freq))
            
            if freq_idx < len(magnitude):
                # Check if there's a peak at this frequency
                local_max = scipy.signal.find_peaks(magnitude, height=0.1 * np.max(magnitude))[0]
                
                if any(abs(freqs[peak_idx] - target_freq) < 50 for peak_idx in local_max):
                    harmonics.append(target_freq)
        
        return harmonics
    
    async def _classify_signal_type(self, magnitude: np.ndarray, freqs: np.ndarray,
                                   species: AnimalSpecies) -> str:
        """Classify the type of acoustic signal"""
        # Calculate spectral characteristics
        spectral_centroid = np.mean(np.sum(magnitude * freqs[:, np.newaxis], axis=0) / np.sum(magnitude, axis=0))
        spectral_bandwidth = np.sqrt(np.mean(np.sum(magnitude * (freqs[:, np.newaxis] - spectral_centroid)**2, axis=0) / np.sum(magnitude, axis=0)))
        
        # Species-specific classification
        if species == AnimalSpecies.DOLPHINS:
            if spectral_centroid > 50000:
                return "echolocation_click"
            elif spectral_bandwidth < 2000:
                return "whistle"
            else:
                return "burst_pulse"
        elif species == AnimalSpecies.BIRDS:
            if spectral_bandwidth > 3000:
                return "complex_song"
            elif spectral_centroid > 4000:
                return "trill"
            else:
                return "note"
        elif species == AnimalSpecies.ELEPHANTS:
            if spectral_centroid < 100:
                return "rumble"
            else:
                return "trumpet"
        else:
            # Generic classification
            if spectral_bandwidth < 500:
                return "tonal"
            elif spectral_centroid > 10000:
                return "high_frequency"
            else:
                return "broadband"
    
    async def _analyze_temporal_pattern(self, audio: np.ndarray, sample_rate: int) -> str:
        """Analyze temporal patterns in the signal"""
        # Calculate envelope
        envelope = np.abs(scipy.signal.hilbert(audio))
        
        # Smooth envelope
        smooth_envelope = scipy.signal.savgol_filter(envelope, window_length=min(101, len(envelope)//2*2+1), polyorder=3)
        
        # Find peaks in envelope
        peaks, _ = scipy.signal.find_peaks(smooth_envelope, height=0.3 * np.max(smooth_envelope))
        
        if len(peaks) <= 1:
            return "single"
        elif len(peaks) < 5:
            return "repeated"
        else:
            # Check if peaks are regularly spaced (trill-like)
            if len(peaks) > 2:
                intervals = np.diff(peaks)
                cv = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 1
                if cv < 0.3:  # Low coefficient of variation indicates regularity
                    return "trill"
            return "burst"
    
    async def _analyze_modulation(self, magnitude: np.ndarray) -> str:
        """Analyze frequency modulation patterns"""
        if magnitude.shape[1] < 3:
            return "constant"
        
        # Track frequency over time
        freq_track = []
        for time_idx in range(magnitude.shape[1]):
            peak_freq_idx = np.argmax(magnitude[:, time_idx])
            freq_track.append(peak_freq_idx)
        
        freq_track = np.array(freq_track)
        
        # Analyze frequency changes
        freq_changes = np.diff(freq_track)
        
        if np.std(freq_changes) < 2:
            return "constant"
        elif np.max(freq_changes) - np.min(freq_changes) > 10:
            return "FM"  # Frequency modulated
        else:
            return "complex"

class CommunicationInterpreter:
    """Interprets animal communication signals into meaningful messages"""
    
    def __init__(self):
        self.species_db = SpeciesDatabase()
        self.acoustic_analyzer = AcousticAnalyzer()
        
    async def interpret_communication_event(self, communication_event: CommunicationEvent) -> str:
        """Interpret a single communication event"""
        species = communication_event.species
        modality = communication_event.modality
        context = communication_event.context
        signal_data = communication_event.signal_data
        
        # Get species communication patterns
        patterns = self.species_db.communication_patterns.get(species, {})
        
        if modality == CommunicationModality.ACOUSTIC and isinstance(signal_data, AcousticSignal):
            interpretation = await self._interpret_acoustic_signal(signal_data, species, context, patterns)
        elif modality == CommunicationModality.VISUAL and isinstance(signal_data, VisualSignal):
            interpretation = await self._interpret_visual_signal(signal_data, species, context)
        elif modality == CommunicationModality.CHEMICAL and isinstance(signal_data, ChemicalSignal):
            interpretation = await self._interpret_chemical_signal(signal_data, species, context)
        else:
            interpretation = f"Unknown {modality.value} signal from {species.value}"
        
        return interpretation
    
    async def _interpret_acoustic_signal(self, signal: AcousticSignal, species: AnimalSpecies,
                                       context: CommunicationContext, patterns: Dict[str, Any]) -> str:
        """Interpret acoustic signals"""
        interpretations = []
        
        # Match against known patterns
        for pattern_name, pattern_info in patterns.items():
            if await self._matches_acoustic_pattern(signal, pattern_info):
                if "type" in pattern_info:
                    interpretations.append(f"{pattern_info['type']} ({pattern_name})")
                else:
                    interpretations.append(pattern_name)
        
        # Context-based interpretation
        if context == CommunicationContext.DANGER:
            if signal.peak_frequency > 2000 and signal.duration < 1.0:
                interpretations.append("alarm call - high urgency")
            elif signal.temporal_pattern == "repeated":
                interpretations.append("warning signal")
        elif context == CommunicationContext.FEEDING:
            if species == AnimalSpecies.DOLPHINS and signal.signal_type == "whistle":
                interpretations.append("food sharing signal")
        elif context == CommunicationContext.SOCIAL_INTERACTION:
            if signal.temporal_pattern == "trill":
                interpretations.append("friendly social contact")
        
        # Species-specific interpretations
        if species == AnimalSpecies.DOLPHINS:
            if signal.signal_type == "whistle" and 7000 <= signal.peak_frequency <= 15000:
                interpretations.append("signature whistle - individual identification")
            elif signal.signal_type == "echolocation_click":
                interpretations.append("echolocation for navigation or hunting")
        elif species == AnimalSpecies.ELEPHANTS:
            if signal.peak_frequency < 35:
                interpretations.append("long-distance infrasonic communication")
            elif signal.signal_type == "trumpet":
                interpretations.append("excitement or alarm display")
        elif species == AnimalSpecies.BIRDS:
            if context == CommunicationContext.BREEDING and signal.duration > 2.0:
                interpretations.append("territorial song or mate attraction")
        
        # Default interpretation if no specific matches
        if not interpretations:
            freq_desc = "low" if signal.peak_frequency < 1000 else "medium" if signal.peak_frequency < 5000 else "high"
            duration_desc = "short" if signal.duration < 0.5 else "medium" if signal.duration < 2.0 else "long"
            interpretations.append(f"{freq_desc}-frequency {duration_desc} vocalization")
        
        return "; ".join(interpretations)
    
    async def _matches_acoustic_pattern(self, signal: AcousticSignal, pattern: Dict[str, Any]) -> bool:
        """Check if signal matches a known acoustic pattern"""
        if "frequency_range" in pattern:
            pattern_min, pattern_max = pattern["frequency_range"]
            signal_min, signal_max = signal.frequency_range
            
            # Check for overlap
            if not (signal_max >= pattern_min and signal_min <= pattern_max):
                return False
        
        if "duration" in pattern:
            if isinstance(pattern["duration"], tuple):
                duration_min, duration_max = pattern["duration"]
                if not (duration_min <= signal.duration <= duration_max):
                    return False
            else:
                expected_duration = pattern["duration"]
                if abs(signal.duration - expected_duration) > 0.5:
                    return False
        
        return True
    
    async def _interpret_visual_signal(self, signal: VisualSignal, species: AnimalSpecies,
                                     context: CommunicationContext) -> str:
        """Interpret visual signals"""
        interpretations = []
        
        if signal.signal_type == "posture":
            if "head" in signal.body_parts_involved:
                if signal.intensity > 0.7:
                    interpretations.append("dominant posture display")
                else:
                    interpretations.append("submissive posture")
        elif signal.signal_type == "color_change":
            if species == AnimalSpecies.CUTTLEFISH:
                interpretations.append("camouflage or communication display")
        elif signal.signal_type == "movement":
            if signal.movement_pattern == "rhythmic" and species == AnimalSpecies.BEES:
                interpretations.append("waggle dance - location information")
        
        if not interpretations:
            interpretations.append(f"{signal.signal_type} display")
        
        return "; ".join(interpretations)
    
    async def _interpret_chemical_signal(self, signal: ChemicalSignal, species: AnimalSpecies,
                                       context: CommunicationContext) -> str:
        """Interpret chemical signals"""
        interpretations = []
        
        if signal.signal_type == "pheromone":
            if context == CommunicationContext.BREEDING:
                interpretations.append("mating pheromone")
            elif context == CommunicationContext.DANGER:
                interpretations.append("alarm pheromone")
            else:
                interpretations.append("social pheromone")
        elif signal.signal_type == "scent_mark":
            interpretations.append("territorial marking")
        
        if not interpretations:
            interpretations.append(f"{signal.signal_type} chemical communication")
        
        return "; ".join(interpretations)

class AnimalCommunicationTranslationSystem:
    """Main system for analyzing and translating animal communication"""
    
    def __init__(self):
        self.species_db = SpeciesDatabase()
        self.acoustic_analyzer = AcousticAnalyzer()
        self.interpreter = CommunicationInterpreter()
        
    async def translate_animal_communication(self, audio_data: Optional[np.ndarray] = None,
                                           video_data: Optional[np.ndarray] = None,
                                           chemical_data: Optional[Dict[str, float]] = None,
                                           species: AnimalSpecies = AnimalSpecies.DOGS,
                                           context: CommunicationContext = CommunicationContext.SOCIAL_INTERACTION,
                                           sample_rate: int = 44100) -> TranslationResult:
        """Translate animal communication to human-understandable format"""
        start_time = datetime.now()
        
        communication_events = []
        
        try:
            # Analyze acoustic signals
            if audio_data is not None:
                acoustic_signals = await self.acoustic_analyzer.analyze_acoustic_signal(
                    audio_data, sample_rate, species
                )
                
                for signal in acoustic_signals:
                    event = CommunicationEvent(
                        species=species,
                        timestamp=0.0,  # Would be calculated from actual timing
                        modality=CommunicationModality.ACOUSTIC,
                        message_type=await self._infer_message_type(signal, context),
                        context=context,
                        signal_data=signal,
                        confidence=0.8
                    )
                    communication_events.append(event)
            
            # Analyze visual signals (placeholder - would need computer vision)
            if video_data is not None:
                # This would involve computer vision analysis
                pass
            
            # Analyze chemical signals
            if chemical_data is not None:
                # This would involve chemical analysis
                pass
            
            # Interpret all events
            interpretations = []
            for event in communication_events:
                interpretation = await self.interpreter.interpret_communication_event(event)
                interpretations.append(interpretation)
            
            # Generate human-readable translation
            translated_message = await self._generate_human_translation(
                communication_events, interpretations, species, context
            )
            
            # Calculate confidence
            confidence = await self._calculate_translation_confidence(communication_events)
            
            # Generate interpretation notes
            interpretation_notes = await self._generate_interpretation_notes(
                species, communication_events, context
            )
            
            # Determine behavioral context
            behavioral_context = await self._determine_behavioral_context(
                communication_events, context
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return TranslationResult(
                source_species=species,
                target_format="human_language",
                original_signals=communication_events,
                translated_message=translated_message,
                confidence=confidence,
                processing_time=processing_time,
                interpretation_notes=interpretation_notes,
                behavioral_context=behavioral_context,
                metadata={
                    "total_signals": len(communication_events),
                    "acoustic_signals": len([e for e in communication_events if e.modality == CommunicationModality.ACOUSTIC]),
                    "context": context.value,
                    "species_profile": self.species_db.species_profiles.get(species, "unknown")
                }
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return TranslationResult(
                source_species=species,
                target_format="human_language",
                original_signals=[],
                translated_message=f"Translation error: {str(e)}",
                confidence=0.0,
                processing_time=processing_time,
                interpretation_notes=[f"Error: {str(e)}"],
                behavioral_context="unknown",
                warnings=["Translation failed due to analysis error"]
            )
    
    async def _infer_message_type(self, signal: AcousticSignal, context: CommunicationContext) -> MessageType:
        """Infer message type from signal characteristics and context"""
        if context == CommunicationContext.DANGER:
            if signal.peak_frequency > 2000 and signal.duration < 1.0:
                return MessageType.ALARM_CALL
            else:
                return MessageType.WARNING
        elif context == CommunicationContext.BREEDING:
            return MessageType.MATING_CALL
        elif context == CommunicationContext.TERRITORIAL_DISPUTE:
            return MessageType.TERRITORIAL_CLAIM
        elif context == CommunicationContext.FEEDING:
            return MessageType.FOOD_LOCATION
        elif context == CommunicationContext.PLAY_BEHAVIOR:
            return MessageType.PLAY_INVITATION
        elif context == CommunicationContext.SOCIAL_INTERACTION:
            if signal.temporal_pattern == "trill":
                return MessageType.GREETING
            else:
                return MessageType.SOCIAL_BONDING
        else:
            return MessageType.SOCIAL_BONDING  # Default
    
    async def _generate_human_translation(self, events: List[CommunicationEvent],
                                        interpretations: List[str], species: AnimalSpecies,
                                        context: CommunicationContext) -> str:
        """Generate human-readable translation"""
        if not events:
            return f"No clear communication signals detected from {species.value}"
        
        species_name = species.value.replace("_", " ").title()
        context_desc = context.value.replace("_", " ")
        
        if len(events) == 1:
            return f"{species_name} communication: {interpretations[0]} (context: {context_desc})"
        else:
            main_interpretation = interpretations[0] if interpretations else "vocalization"
            additional_info = f" with {len(events)-1} additional signals" if len(events) > 1 else ""
            
            return f"{species_name} communication sequence: {main_interpretation}{additional_info} (context: {context_desc})"
    
    async def _calculate_translation_confidence(self, events: List[CommunicationEvent]) -> float:
        """Calculate overall translation confidence"""
        if not events:
            return 0.0
        
        confidences = [event.confidence for event in events if event.confidence > 0]
        
        if not confidences:
            return 0.3  # Low default confidence
        
        avg_confidence = np.mean(confidences)
        
        # Adjust based on number of signals (more signals = more confidence)
        signal_bonus = min(len(events) * 0.05, 0.2)
        
        return min(avg_confidence + signal_bonus, 1.0)
    
    async def _generate_interpretation_notes(self, species: AnimalSpecies,
                                           events: List[CommunicationEvent],
                                           context: CommunicationContext) -> List[str]:
        """Generate notes about the interpretation process"""
        notes = []
        
        species_profile = self.species_db.species_profiles.get(species)
        if species_profile:
            notes.append(f"Species communication complexity: {species_profile.communication_complexity}")
            notes.append(f"Primary modalities: {[m.value for m in species_profile.primary_modalities]}")
            if species_profile.unique_features:
                notes.append(f"Unique features: {', '.join(species_profile.unique_features[:3])}")
        
        # Analyze signal characteristics
        acoustic_events = [e for e in events if e.modality == CommunicationModality.ACOUSTIC]
        if acoustic_events:
            frequencies = []
            durations = []
            for event in acoustic_events:
                if isinstance(event.signal_data, AcousticSignal):
                    frequencies.append(event.signal_data.peak_frequency)
                    durations.append(event.signal_data.duration)
            
            if frequencies:
                notes.append(f"Frequency range: {min(frequencies):.0f}-{max(frequencies):.0f} Hz")
            if durations:
                notes.append(f"Signal durations: {min(durations):.2f}-{max(durations):.2f} seconds")
        
        # Context information
        notes.append(f"Behavioral context: {context.value.replace('_', ' ')}")
        
        return notes
    
    async def _determine_behavioral_context(self, events: List[CommunicationEvent],
                                          context: CommunicationContext) -> str:
        """Determine behavioral context description"""
        context_descriptions = {
            CommunicationContext.FEEDING: "Food-related behavior",
            CommunicationContext.BREEDING: "Mating or reproductive behavior",
            CommunicationContext.PARENTING: "Parent-offspring interaction",
            CommunicationContext.PREDATOR_PRESENCE: "Anti-predator response",
            CommunicationContext.TERRITORIAL_DISPUTE: "Territorial defense or competition",
            CommunicationContext.MIGRATION: "Group movement or navigation",
            CommunicationContext.PLAY_BEHAVIOR: "Playful or exploratory behavior",
            CommunicationContext.GROOMING: "Social bonding and maintenance",
            CommunicationContext.RESTING: "Resting or low-activity state",
            CommunicationContext.EXPLORATION: "Environmental exploration",
            CommunicationContext.DANGER: "Danger response or alarm",
            CommunicationContext.SOCIAL_INTERACTION: "General social communication"
        }
        
        base_description = context_descriptions.get(context, "Unknown behavioral context")
        
        # Add signal-specific information
        if events:
            signal_count = len(events)
            modalities = set(event.modality for event in events)
            modality_desc = ", ".join(m.value for m in modalities)
            
            return f"{base_description} ({signal_count} signals via {modality_desc})"
        
        return base_description

# Example usage
async def main():
    """Example usage of animal communication translation system"""
    
    # Initialize the system
    translator = AnimalCommunicationTranslationSystem()
    
    print("Animal Communication Patterns System Demo")
    print("=" * 50)
    
    # Simulate dolphin audio data
    print("Example 1: Dolphin Communication Analysis")
    sample_rate = 96000  # High sample rate for dolphin sounds
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Simulate dolphin signature whistle (frequency modulated)
    frequency = 10000 + 2000 * np.sin(2 * np.pi * 3 * t)  # FM whistle
    dolphin_audio = np.sin(2 * np.pi * frequency * t) * np.exp(-t/1.0)
    
    # Add some noise
    dolphin_audio += 0.1 * np.random.normal(0, 1, len(dolphin_audio))
    
    result1 = await translator.translate_animal_communication(
        audio_data=dolphin_audio,
        species=AnimalSpecies.DOLPHINS,
        context=CommunicationContext.SOCIAL_INTERACTION,
        sample_rate=sample_rate
    )
    
    print(f"Translation: {result1.translated_message}")
    print(f"Confidence: {result1.confidence:.3f}")
    print(f"Processing time: {result1.processing_time:.2f}s")
    print(f"Behavioral context: {result1.behavioral_context}")
    
    # Example 2: Bird song analysis
    print("\n" + "=" * 30)
    print("Example 2: Bird Song Analysis")
    
    # Simulate bird song (rapid frequency changes)
    bird_sample_rate = 44100
    bird_duration = 1.5
    t_bird = np.linspace(0, bird_duration, int(bird_sample_rate * bird_duration))
    
    # Create a complex bird song pattern
    note1 = np.sin(2 * np.pi * 2000 * t_bird[:len(t_bird)//3])
    note2 = np.sin(2 * np.pi * 4000 * t_bird[len(t_bird)//3:2*len(t_bird)//3])
    note3 = np.sin(2 * np.pi * 1500 * t_bird[2*len(t_bird)//3:])
    bird_audio = np.concatenate([note1, note2, note3])
    
    result2 = await translator.translate_animal_communication(
        audio_data=bird_audio,
        species=AnimalSpecies.BIRDS,
        context=CommunicationContext.BREEDING,
        sample_rate=bird_sample_rate
    )
    
    print(f"Translation: {result2.translated_message}")
    print(f"Confidence: {result2.confidence:.3f}")
    
    # Example 3: Dog communication
    print("\n" + "=" * 30)
    print("Example 3: Dog Communication Analysis")
    
    # Simulate dog bark (short, repetitive)
    dog_sample_rate = 22050
    dog_duration = 0.8
    t_dog = np.linspace(0, dog_duration, int(dog_sample_rate * dog_duration))
    
    # Create bark pattern
    bark_freq = 800
    dog_audio = np.sin(2 * np.pi * bark_freq * t_dog) * (t_dog < 0.3)
    dog_audio += 0.7 * np.sin(2 * np.pi * bark_freq * (t_dog - 0.4)) * ((t_dog >= 0.4) & (t_dog < 0.7))
    
    result3 = await translator.translate_animal_communication(
        audio_data=dog_audio,
        species=AnimalSpecies.DOGS,
        context=CommunicationContext.SOCIAL_INTERACTION,
        sample_rate=dog_sample_rate
    )
    
    print(f"Translation: {result3.translated_message}")
    print(f"Confidence: {result3.confidence:.3f}")
    
    # Show detailed analysis for one result
    print(f"\nDetailed Analysis (Dolphins):")
    if result1.interpretation_notes:
        print("Interpretation notes:")
        for note in result1.interpretation_notes:
            print(f"  📝 {note}")
    
    if result1.original_signals:
        print(f"\nDetected signals: {len(result1.original_signals)}")
        for i, signal in enumerate(result1.original_signals[:2]):
            if isinstance(signal.signal_data, AcousticSignal):
                acoustic = signal.signal_data
                print(f"  Signal {i+1}: {acoustic.signal_type}, "
                      f"{acoustic.peak_frequency:.0f}Hz, "
                      f"{acoustic.duration:.2f}s")
    
    print(f"\nSystem metadata:")
    for key, value in result1.metadata.items():
        if key != "species_profile":
            print(f"  {key}: {value}")

if __name__ == "__main__":
    asyncio.run(main())