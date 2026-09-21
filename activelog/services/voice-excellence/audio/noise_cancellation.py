"""
Advanced Noise Cancellation System
Specialized for marine and industrial environments with adaptive filtering
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator
from enum import Enum
from dataclasses import dataclass
import threading
import time
from scipy import signal
from scipy.signal import butter, filtfilt, wiener
from scipy.fft import fft, ifft, fftfreq

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnvironmentType(Enum):
    """Types of noise environments"""
    MARINE_ENGINE_ROOM = "marine_engine_room"
    MARINE_BRIDGE = "marine_bridge"
    MARINE_DECK = "marine_deck"
    INDUSTRIAL_FACTORY = "industrial_factory"
    INDUSTRIAL_CONSTRUCTION = "industrial_construction"
    INDUSTRIAL_WORKSHOP = "industrial_workshop"
    OFFICE_QUIET = "office_quiet"
    VEHICLE_CABIN = "vehicle_cabin"
    OUTDOOR_WINDY = "outdoor_windy"
    GENERAL_NOISY = "general_noisy"


class NoiseType(Enum):
    """Specific types of noise patterns"""
    ENGINE_CONSTANT = "engine_constant"
    ENGINE_VARIABLE = "engine_variable"
    MACHINERY_CYCLIC = "machinery_cyclic"
    HYDRAULIC_PUMPS = "hydraulic_pumps"
    VENTILATION_FANS = "ventilation_fans"
    WAVE_SPLASH = "wave_splash"
    WIND_NOISE = "wind_noise"
    ELECTRICAL_HUM = "electrical_hum"
    HUMAN_CHATTER = "human_chatter"
    METAL_CLANGING = "metal_clanging"


@dataclass
class NoiseProfile:
    """Noise profile for specific environment"""
    environment_type: EnvironmentType
    dominant_frequencies: List[float]
    noise_floor_db: float
    peak_frequencies: List[float]
    spectral_shape: np.ndarray
    adaptation_rate: float
    filter_coefficients: Dict[str, np.ndarray]


@dataclass
class AudioFrame:
    """Single frame of audio data"""
    data: np.ndarray
    sample_rate: int
    timestamp: datetime
    channels: int
    frame_id: int


class AdaptiveNoiseFilter:
    """Adaptive noise filtering using multiple algorithms"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.frame_size = 512  # samples
        self.hop_size = 256    # samples
        
        # Filter parameters
        self.adaptation_rate = 0.01
        self.noise_floor_threshold = -40  # dB
        self.voice_activity_threshold = 0.05
        
        # Noise tracking
        self.noise_spectrum = np.zeros(self.frame_size // 2 + 1)
        self.noise_power = np.zeros(self.frame_size // 2 + 1)
        self.voice_activity_history = []
        
        # Multi-band processing
        self.num_bands = 8
        self.band_filters = self._create_band_filters()
        
        logger.info(f"AdaptiveNoiseFilter initialized with {sample_rate}Hz sampling")
    
    def _create_band_filters(self) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Create multi-band filters for frequency-specific processing"""
        filters = []
        nyquist = self.sample_rate / 2
        
        # Define frequency bands (logarithmic distribution)
        frequencies = np.logspace(np.log10(80), np.log10(nyquist), self.num_bands + 1)
        
        for i in range(self.num_bands):
            low = frequencies[i]
            high = frequencies[i + 1]
            
            if high >= nyquist:
                high = nyquist - 1
            
            # Bandpass filter
            b, a = butter(4, [low, high], btype='band', fs=self.sample_rate)
            filters.append((b, a))
        
        return filters
    
    def detect_voice_activity(self, audio_frame: np.ndarray) -> bool:
        """Detect voice activity in audio frame"""
        try:
            # Calculate energy
            energy = np.sum(audio_frame ** 2)
            
            # Calculate spectral centroid
            spectrum = np.abs(fft(audio_frame))
            freqs = fftfreq(len(audio_frame), 1/self.sample_rate)
            centroid = np.sum(freqs[:len(freqs)//2] * spectrum[:len(spectrum)//2]) / np.sum(spectrum[:len(spectrum)//2])
            
            # Calculate zero crossing rate
            zcr = np.sum(np.diff(np.sign(audio_frame)) != 0) / len(audio_frame)
            
            # Voice activity decision
            voice_activity = (energy > self.voice_activity_threshold and 
                            200 <= centroid <= 3000 and  # Human voice frequency range
                            zcr > 0.05)
            
            # Keep history for better decision making
            self.voice_activity_history.append(voice_activity)
            if len(self.voice_activity_history) > 10:
                self.voice_activity_history.pop(0)
            
            # Use majority voting
            return sum(self.voice_activity_history) > len(self.voice_activity_history) // 2
            
        except Exception as e:
            logger.error(f"Error in voice activity detection: {e}")
            return False
    
    def update_noise_profile(self, audio_frame: np.ndarray, voice_active: bool):
        """Update noise profile during non-voice segments"""
        try:
            if not voice_active:
                # Calculate spectrum
                spectrum = fft(audio_frame)
                power_spectrum = np.abs(spectrum[:len(spectrum)//2 + 1]) ** 2
                
                # Adaptive noise floor estimation
                if np.sum(self.noise_power) == 0:
                    # Initialize
                    self.noise_power = power_spectrum
                    self.noise_spectrum = spectrum[:len(spectrum)//2 + 1]
                else:
                    # Exponential smoothing
                    alpha = self.adaptation_rate
                    self.noise_power = (1 - alpha) * self.noise_power + alpha * power_spectrum
                    self.noise_spectrum = (1 - alpha) * self.noise_spectrum + alpha * spectrum[:len(spectrum)//2 + 1]
        
        except Exception as e:
            logger.error(f"Error updating noise profile: {e}")
    
    def spectral_subtraction(self, audio_frame: np.ndarray) -> np.ndarray:
        """Apply spectral subtraction for noise reduction"""
        try:
            # FFT of input
            spectrum = fft(audio_frame)
            magnitude = np.abs(spectrum)
            phase = np.angle(spectrum)
            
            # Noise estimation
            noise_magnitude = np.abs(self.noise_spectrum)
            
            # Extend noise spectrum to match signal length
            if len(noise_magnitude) < len(magnitude):
                # Repeat noise spectrum
                repeats = len(magnitude) // len(noise_magnitude) + 1
                extended_noise = np.tile(noise_magnitude, repeats)[:len(magnitude)]
            else:
                extended_noise = noise_magnitude[:len(magnitude)]
            
            # Spectral subtraction with over-subtraction factor
            alpha = 2.0  # Over-subtraction factor
            beta = 0.01  # Spectral floor factor
            
            enhanced_magnitude = magnitude - alpha * extended_noise
            
            # Apply spectral floor
            spectral_floor = beta * magnitude
            enhanced_magnitude = np.maximum(enhanced_magnitude, spectral_floor)
            
            # Reconstruct signal
            enhanced_spectrum = enhanced_magnitude * np.exp(1j * phase)
            enhanced_signal = np.real(ifft(enhanced_spectrum))
            
            return enhanced_signal
            
        except Exception as e:
            logger.error(f"Error in spectral subtraction: {e}")
            return audio_frame
    
    def wiener_filtering(self, audio_frame: np.ndarray) -> np.ndarray:
        """Apply Wiener filtering for noise reduction"""
        try:
            if np.sum(self.noise_power) == 0:
                return audio_frame
            
            # Calculate signal power spectrum
            signal_spectrum = fft(audio_frame)
            signal_power = np.abs(signal_spectrum) ** 2
            
            # Extend noise power to match signal length
            if len(self.noise_power) < len(signal_power):
                repeats = len(signal_power) // len(self.noise_power) + 1
                extended_noise_power = np.tile(self.noise_power, repeats)[:len(signal_power)]
            else:
                extended_noise_power = self.noise_power[:len(signal_power)]
            
            # Wiener filter
            snr = signal_power / (extended_noise_power + 1e-10)
            wiener_gain = snr / (snr + 1)
            
            # Apply gain
            enhanced_spectrum = signal_spectrum * wiener_gain
            enhanced_signal = np.real(ifft(enhanced_spectrum))
            
            return enhanced_signal
            
        except Exception as e:
            logger.error(f"Error in Wiener filtering: {e}")
            return audio_frame
    
    def multi_band_processing(self, audio_frame: np.ndarray) -> np.ndarray:
        """Apply different processing to different frequency bands"""
        try:
            enhanced_frame = np.zeros_like(audio_frame)
            
            for i, (b, a) in enumerate(self.band_filters):
                # Extract band
                band_signal = filtfilt(b, a, audio_frame)
                
                # Apply band-specific processing
                if i < 2:  # Low frequency bands (engines, machinery)
                    # Stronger noise reduction
                    processed_band = self.spectral_subtraction(band_signal) * 0.3
                elif i < 5:  # Mid frequency bands (human voice)
                    # Preserve voice, moderate noise reduction
                    processed_band = self.wiener_filtering(band_signal) * 0.8
                else:  # High frequency bands
                    # Light processing to preserve voice clarity
                    processed_band = band_signal * 0.9
                
                enhanced_frame += processed_band
            
            return enhanced_frame
            
        except Exception as e:
            logger.error(f"Error in multi-band processing: {e}")
            return audio_frame


class MarineIndustrialNoiseCanceller:
    """Specialized noise cancellation for marine and industrial environments"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.adaptive_filter = AdaptiveNoiseFilter(sample_rate)
        
        # Environment-specific noise profiles
        self.noise_profiles = self._create_noise_profiles()
        self.current_environment = EnvironmentType.GENERAL_NOISY
        
        # Processing parameters
        self.processing_enabled = True
        self.aggressiveness = 0.7  # 0.0 to 1.0
        
        # Performance monitoring
        self.frames_processed = 0
        self.processing_time_avg = 0.0
        
        logger.info("MarineIndustrialNoiseCanceller initialized")
    
    def _create_noise_profiles(self) -> Dict[EnvironmentType, NoiseProfile]:
        """Create predefined noise profiles for different environments"""
        profiles = {}
        
        # Marine Engine Room
        profiles[EnvironmentType.MARINE_ENGINE_ROOM] = NoiseProfile(
            environment_type=EnvironmentType.MARINE_ENGINE_ROOM,
            dominant_frequencies=[50, 100, 150, 200, 300, 500, 800],  # Engine harmonics
            noise_floor_db=-20,
            peak_frequencies=[125, 250, 500, 1000],
            spectral_shape=np.array([1.0, 0.8, 0.6, 0.4, 0.3, 0.2, 0.1]),
            adaptation_rate=0.005,  # Slow adaptation for constant noise
            filter_coefficients={}
        )
        
        # Marine Bridge
        profiles[EnvironmentType.MARINE_BRIDGE] = NoiseProfile(
            environment_type=EnvironmentType.MARINE_BRIDGE,
            dominant_frequencies=[60, 120, 240, 400, 600],  # HVAC and electronics
            noise_floor_db=-35,
            peak_frequencies=[60, 120, 400],
            spectral_shape=np.array([0.6, 0.5, 0.4, 0.3, 0.2, 0.1]),
            adaptation_rate=0.01,
            filter_coefficients={}
        )
        
        # Marine Deck
        profiles[EnvironmentType.MARINE_DECK] = NoiseProfile(
            environment_type=EnvironmentType.MARINE_DECK,
            dominant_frequencies=[100, 200, 400, 800, 1600],  # Wind and wave noise
            noise_floor_db=-30,
            peak_frequencies=[200, 400, 800],
            spectral_shape=np.array([0.8, 0.7, 0.5, 0.3, 0.2, 0.1]),
            adaptation_rate=0.02,  # Faster adaptation for variable conditions
            filter_coefficients={}
        )
        
        # Industrial Factory
        profiles[EnvironmentType.INDUSTRIAL_FACTORY] = NoiseProfile(
            environment_type=EnvironmentType.INDUSTRIAL_FACTORY,
            dominant_frequencies=[50, 100, 200, 400, 800, 1200],  # Machinery
            noise_floor_db=-25,
            peak_frequencies=[100, 200, 400, 800],
            spectral_shape=np.array([1.0, 0.9, 0.7, 0.5, 0.3, 0.2, 0.1]),
            adaptation_rate=0.008,
            filter_coefficients={}
        )
        
        # Industrial Construction
        profiles[EnvironmentType.INDUSTRIAL_CONSTRUCTION] = NoiseProfile(
            environment_type=EnvironmentType.INDUSTRIAL_CONSTRUCTION,
            dominant_frequencies=[80, 160, 320, 640, 1280],  # Impact noise
            noise_floor_db=-20,
            peak_frequencies=[160, 320, 640],
            spectral_shape=np.array([1.0, 0.8, 0.6, 0.4, 0.2, 0.1]),
            adaptation_rate=0.03,  # Fast adaptation for transient noise
            filter_coefficients={}
        )
        
        return profiles
    
    def set_environment(self, environment: EnvironmentType):
        """Set the current noise environment"""
        self.current_environment = environment
        
        # Update adaptive filter parameters
        if environment in self.noise_profiles:
            profile = self.noise_profiles[environment]
            self.adaptive_filter.adaptation_rate = profile.adaptation_rate
            
            logger.info(f"Environment set to {environment.value}")
    
    def auto_detect_environment(self, audio_frames: List[np.ndarray]) -> EnvironmentType:
        """Automatically detect the noise environment"""
        try:
            if not audio_frames:
                return EnvironmentType.GENERAL_NOISY
            
            # Combine frames for analysis
            combined_audio = np.concatenate(audio_frames)
            
            # Calculate spectrum
            spectrum = np.abs(fft(combined_audio))
            freqs = fftfreq(len(combined_audio), 1/self.sample_rate)
            
            # Find dominant frequencies
            spectrum_half = spectrum[:len(spectrum)//2]
            freqs_half = freqs[:len(freqs)//2]
            
            # Find peaks
            peaks, _ = signal.find_peaks(spectrum_half, height=np.max(spectrum_half) * 0.1)
            dominant_freqs = freqs_half[peaks]
            
            # Calculate noise characteristics
            noise_level = np.mean(spectrum_half)
            peak_concentration = len(peaks) / len(spectrum_half)
            
            # Environment classification logic
            if len(dominant_freqs) > 0:
                max_freq = np.max(dominant_freqs)
                low_freq_power = np.sum(spectrum_half[freqs_half < 300])
                total_power = np.sum(spectrum_half)
                low_freq_ratio = low_freq_power / total_power
                
                if low_freq_ratio > 0.7 and noise_level > 1000:
                    if peak_concentration > 0.01:
                        return EnvironmentType.MARINE_ENGINE_ROOM
                    else:
                        return EnvironmentType.INDUSTRIAL_FACTORY
                elif 0.4 < low_freq_ratio < 0.7:
                    if max_freq < 1000:
                        return EnvironmentType.MARINE_BRIDGE
                    else:
                        return EnvironmentType.MARINE_DECK
                elif low_freq_ratio < 0.4:
                    return EnvironmentType.INDUSTRIAL_CONSTRUCTION
            
            return EnvironmentType.GENERAL_NOISY
            
        except Exception as e:
            logger.error(f"Error in environment detection: {e}")
            return EnvironmentType.GENERAL_NOISY
    
    def process_frame(self, audio_frame: np.ndarray) -> np.ndarray:
        """Process a single audio frame"""
        start_time = time.time()
        
        try:
            if not self.processing_enabled:
                return audio_frame
            
            # Voice activity detection
            voice_active = self.adaptive_filter.detect_voice_activity(audio_frame)
            
            # Update noise profile during silence
            self.adaptive_filter.update_noise_profile(audio_frame, voice_active)
            
            # Apply noise reduction based on environment
            if self.current_environment in [EnvironmentType.MARINE_ENGINE_ROOM, EnvironmentType.INDUSTRIAL_FACTORY]:
                # Heavy machinery - aggressive processing
                enhanced_frame = self.adaptive_filter.multi_band_processing(audio_frame)
            elif self.current_environment in [EnvironmentType.MARINE_DECK, EnvironmentType.INDUSTRIAL_CONSTRUCTION]:
                # Variable noise - spectral subtraction
                enhanced_frame = self.adaptive_filter.spectral_subtraction(audio_frame)
            else:
                # Moderate noise - Wiener filtering
                enhanced_frame = self.adaptive_filter.wiener_filtering(audio_frame)
            
            # Apply aggressiveness factor
            enhanced_frame = (enhanced_frame * self.aggressiveness + 
                            audio_frame * (1 - self.aggressiveness))
            
            # Update performance metrics
            processing_time = time.time() - start_time
            self.processing_time_avg = (0.9 * self.processing_time_avg + 0.1 * processing_time)
            self.frames_processed += 1
            
            return enhanced_frame
            
        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")
            return audio_frame
    
    async def process_stream(self, audio_stream) -> AsyncGenerator:
        """Process continuous audio stream"""
        try:
            frame_buffer = []
            
            async for frame in audio_stream:
                # Process frame
                enhanced_frame = self.process_frame(frame.data)
                
                # Create enhanced audio frame
                enhanced_audio_frame = AudioFrame(
                    data=enhanced_frame,
                    sample_rate=frame.sample_rate,
                    timestamp=frame.timestamp,
                    channels=frame.channels,
                    frame_id=frame.frame_id
                )
                
                # Buffer for environment detection
                frame_buffer.append(frame.data)
                if len(frame_buffer) > 50:  # Keep 50 frames for analysis
                    frame_buffer.pop(0)
                
                # Periodic environment detection
                if self.frames_processed % 100 == 0:
                    detected_env = self.auto_detect_environment(frame_buffer)
                    if detected_env != self.current_environment:
                        logger.info(f"Environment changed: {self.current_environment.value} -> {detected_env.value}")
                        self.set_environment(detected_env)
                
                yield enhanced_audio_frame
                
        except Exception as e:
            logger.error(f"Error in stream processing: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get noise cancellation performance statistics"""
        return {
            "frames_processed": self.frames_processed,
            "avg_processing_time_ms": self.processing_time_avg * 1000,
            "current_environment": self.current_environment.value,
            "processing_enabled": self.processing_enabled,
            "aggressiveness": self.aggressiveness,
            "sample_rate": self.sample_rate
        }
    
    def set_aggressiveness(self, level: float):
        """Set noise cancellation aggressiveness (0.0 to 1.0)"""
        self.aggressiveness = max(0.0, min(1.0, level))
        logger.info(f"Noise cancellation aggressiveness set to {self.aggressiveness}")
    
    def enable_processing(self, enabled: bool):
        """Enable or disable noise cancellation"""
        self.processing_enabled = enabled
        logger.info(f"Noise cancellation {'enabled' if enabled else 'disabled'}")
    
    def calibrate_for_environment(self, audio_samples: List[np.ndarray], duration_seconds: int = 10):
        """Calibrate noise cancellation for current environment"""
        try:
            logger.info(f"Starting noise calibration for {duration_seconds} seconds...")
            
            # Analyze provided samples
            if audio_samples:
                detected_env = self.auto_detect_environment(audio_samples)
                self.set_environment(detected_env)
                
                # Update noise profile with actual samples
                for sample in audio_samples:
                    self.adaptive_filter.update_noise_profile(sample, False)  # Assume no voice during calibration
            
            logger.info("Noise calibration completed")
            
        except Exception as e:
            logger.error(f"Error during calibration: {e}")


class RealTimeAudioProcessor:
    """Real-time audio processing with noise cancellation"""
    
    def __init__(self, sample_rate: int = 16000, frame_size: int = 512):
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.noise_canceller = MarineIndustrialNoiseCanceller(sample_rate)
        
        # Audio buffer
        self.audio_buffer = np.array([])
        self.frame_counter = 0
        
        # Processing thread
        self.processing_active = False
        self.processing_thread = None
        
        logger.info("RealTimeAudioProcessor initialized")
    
    def add_audio_data(self, audio_data: np.ndarray):
        """Add new audio data to processing buffer"""
        self.audio_buffer = np.append(self.audio_buffer, audio_data)
    
    def get_next_frame(self) -> Optional[AudioFrame]:
        """Get next audio frame for processing"""
        if len(self.audio_buffer) >= self.frame_size:
            # Extract frame
            frame_data = self.audio_buffer[:self.frame_size]
            self.audio_buffer = self.audio_buffer[self.frame_size:]
            
            # Create audio frame
            audio_frame = AudioFrame(
                data=frame_data,
                sample_rate=self.sample_rate,
                timestamp=datetime.now(timezone.utc),
                channels=1,
                frame_id=self.frame_counter
            )
            
            self.frame_counter += 1
            return audio_frame
        
        return None
    
    def process_frame_sync(self, audio_frame: AudioFrame) -> AudioFrame:
        """Synchronously process a single frame"""
        enhanced_data = self.noise_canceller.process_frame(audio_frame.data)
        
        return AudioFrame(
            data=enhanced_data,
            sample_rate=audio_frame.sample_rate,
            timestamp=audio_frame.timestamp,
            channels=audio_frame.channels,
            frame_id=audio_frame.frame_id
        )
    
    def start_processing(self):
        """Start real-time processing"""
        self.processing_active = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.start()
        logger.info("Real-time processing started")
    
    def stop_processing(self):
        """Stop real-time processing"""
        self.processing_active = False
        if self.processing_thread:
            self.processing_thread.join()
        logger.info("Real-time processing stopped")
    
    def _processing_loop(self):
        """Main processing loop"""
        while self.processing_active:
            frame = self.get_next_frame()
            if frame:
                enhanced_frame = self.process_frame_sync(frame)
                # Enhanced frame would be output to audio system
            else:
                time.sleep(0.001)  # Short sleep to prevent busy waiting