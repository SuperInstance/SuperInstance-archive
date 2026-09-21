"""
Marine Environment Noise Filtering System
Advanced noise cancellation for wind, engine, and marine environment
"""

import logging
import numpy as np
from typing import Optional, Dict, Any
import threading
import time

logger = logging.getLogger(__name__)

class MarineNoiseFilter:
    """
    Professional marine environment noise filtering
    Handles wind, engine, and sea noise cancellation
    """
    
    def __init__(self):
        self.sample_rate = 16000
        self.noise_profile = None
        self.adaptive_filter_enabled = True
        
        # Marine-specific noise characteristics
        self.wind_frequency_range = (100, 1000)  # Hz
        self.engine_frequency_range = (50, 500)   # Hz
        self.sea_noise_range = (20, 200)         # Hz
        
        # Noise reduction parameters
        self.noise_reduction_strength = 0.7
        self.voice_enhancement = True
        
        # Audio level monitoring
        self.current_noise_level = 0.0
        self.ambient_noise_baseline = 0.0
        self.noise_history = []
        
        logger.info("Marine Noise Filter initialized")
    
    def filter_audio(self, audio_data: bytes) -> bytes:
        """Apply marine environment noise filtering"""
        try:
            if not audio_data:
                return audio_data
            
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Apply noise reduction
            filtered_audio = self._apply_noise_reduction(audio_array)
            
            # Apply voice enhancement
            if self.voice_enhancement:
                filtered_audio = self._enhance_voice_frequencies(filtered_audio)
            
            # Convert back to bytes
            return filtered_audio.astype(np.int16).tobytes()
            
        except Exception as e:
            logger.error(f"Audio filtering error: {e}")
            return audio_data  # Return original on error
    
    def _apply_noise_reduction(self, audio_array: np.ndarray) -> np.ndarray:
        """Apply noise reduction algorithms"""
        try:
            # Spectral subtraction for wind noise
            filtered = self._spectral_subtraction(audio_array, self.wind_frequency_range)
            
            # Engine noise filtering using notch filters
            filtered = self._engine_noise_filter(filtered)
            
            # Sea noise reduction
            filtered = self._sea_noise_filter(filtered)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Noise reduction error: {e}")
            return audio_array
    
    def _spectral_subtraction(self, audio: np.ndarray, freq_range: tuple) -> np.ndarray:
        """Apply spectral subtraction for wind noise"""
        try:
            # Simplified spectral subtraction
            # In production, would use FFT-based processing
            
            # Apply high-pass filter to reduce low-frequency wind noise
            if len(audio) > 100:
                # Simple high-pass filter approximation
                filtered = np.copy(audio)
                for i in range(10, len(filtered)):
                    filtered[i] = filtered[i] - 0.3 * filtered[i-10]
                
                return filtered
            
            return audio
            
        except Exception as e:
            logger.error(f"Spectral subtraction error: {e}")
            return audio
    
    def _engine_noise_filter(self, audio: np.ndarray) -> np.ndarray:
        """Filter engine noise using adaptive filtering"""
        try:
            # Simplified engine noise filtering
            # In production, would use adaptive notch filters at engine RPM frequencies
            
            # Apply band-stop filter for typical engine frequencies
            if len(audio) > 50:
                filtered = np.copy(audio)
                
                # Simple moving average to reduce periodic engine noise
                window_size = min(20, len(filtered) // 10)
                for i in range(window_size, len(filtered) - window_size):
                    avg = np.mean(filtered[i-window_size:i+window_size])
                    if abs(filtered[i] - avg) < 0.5 * np.std(filtered[i-window_size:i+window_size]):
                        filtered[i] = filtered[i] * 0.7 + avg * 0.3
                
                return filtered
            
            return audio
            
        except Exception as e:
            logger.error(f"Engine noise filter error: {e}")
            return audio
    
    def _sea_noise_filter(self, audio: np.ndarray) -> np.ndarray:
        """Filter sea and wave noise"""
        try:
            # Simple low-frequency noise reduction for sea noise
            if len(audio) > 20:
                filtered = np.copy(audio)
                
                # Reduce low-frequency components
                for i in range(5, len(filtered)):
                    filtered[i] = filtered[i] - 0.2 * filtered[i-5]
                
                return filtered
            
            return audio
            
        except Exception as e:
            logger.error(f"Sea noise filter error: {e}")
            return audio
    
    def _enhance_voice_frequencies(self, audio: np.ndarray) -> np.ndarray:
        """Enhance voice frequencies (300-3400 Hz)"""
        try:
            # Simplified voice enhancement
            # Boost mid-frequencies where speech occurs
            
            if len(audio) > 10:
                enhanced = np.copy(audio)
                
                # Simple emphasis filter for voice frequencies
                for i in range(2, len(enhanced) - 2):
                    # Enhance local variations (voice characteristics)
                    local_variation = abs(enhanced[i] - (enhanced[i-1] + enhanced[i+1]) / 2)
                    if local_variation > np.std(enhanced) * 0.1:
                        enhanced[i] = enhanced[i] * 1.2  # Boost voice-like signals
                
                return enhanced
            
            return audio
            
        except Exception as e:
            logger.error(f"Voice enhancement error: {e}")
            return audio
    
    def analyze_audio_levels(self, audio_data: bytes):
        """Analyze current audio levels for adaptive filtering"""
        try:
            if not audio_data:
                return
            
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calculate RMS level
            rms_level = np.sqrt(np.mean(audio_array.astype(float) ** 2))
            self.current_noise_level = rms_level
            
            # Update noise history
            self.noise_history.append(rms_level)
            if len(self.noise_history) > 100:  # Keep last 100 samples
                self.noise_history.pop(0)
            
            # Update ambient baseline
            if len(self.noise_history) > 10:
                self.ambient_noise_baseline = np.percentile(self.noise_history, 20)  # 20th percentile
            
        except Exception as e:
            logger.error(f"Audio level analysis error: {e}")
    
    def set_noise_reduction_strength(self, strength: float):
        """Set noise reduction strength (0.0 to 1.0)"""
        self.noise_reduction_strength = max(0.0, min(1.0, strength))
        logger.info(f"Noise reduction strength set to {self.noise_reduction_strength}")
    
    def enable_adaptive_filtering(self, enabled: bool):
        """Enable/disable adaptive filtering"""
        self.adaptive_filter_enabled = enabled
        logger.info(f"Adaptive filtering {'enabled' if enabled else 'disabled'}")
    
    def calibrate_noise_profile(self, duration: int = 5):
        """Calibrate noise profile from ambient environment"""
        try:
            logger.info(f"Calibrating noise profile for {duration} seconds...")
            
            # In production, would record ambient noise for the specified duration
            # and create a noise profile for better filtering
            
            time.sleep(duration)
            
            if self.noise_history:
                self.ambient_noise_baseline = np.mean(self.noise_history)
                logger.info(f"Noise profile calibrated. Baseline: {self.ambient_noise_baseline:.2f}")
            else:
                logger.warning("No audio data available for calibration")
                
        except Exception as e:
            logger.error(f"Noise calibration error: {e}")
    
    def get_noise_levels(self) -> Dict[str, float]:
        """Get current noise level information"""
        return {
            'current_level': self.current_noise_level,
            'baseline_level': self.ambient_noise_baseline,
            'noise_reduction_strength': self.noise_reduction_strength,
            'samples_analyzed': len(self.noise_history)
        }
    
    def set_marine_environment(self, environment: str):
        """Adjust filtering for specific marine environment"""
        environments = {
            'harbor': {
                'wind_strength': 0.3,
                'engine_strength': 0.8,
                'sea_strength': 0.2
            },
            'coastal': {
                'wind_strength': 0.5,
                'engine_strength': 0.6,
                'sea_strength': 0.4
            },
            'open_ocean': {
                'wind_strength': 0.8,
                'engine_strength': 0.4,
                'sea_strength': 0.7
            },
            'heavy_weather': {
                'wind_strength': 0.9,
                'engine_strength': 0.5,
                'sea_strength': 0.9
            }
        }
        
        if environment in environments:
            config = environments[environment]
            # Adjust filtering parameters based on environment
            self.noise_reduction_strength = max(config.values())
            logger.info(f"Noise filtering configured for {environment} environment")
        else:
            logger.warning(f"Unknown environment: {environment}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get noise filter status"""
        return {
            'adaptive_filtering': self.adaptive_filter_enabled,
            'noise_reduction_strength': self.noise_reduction_strength,
            'voice_enhancement': self.voice_enhancement,
            'current_noise_level': self.current_noise_level,
            'ambient_baseline': self.ambient_noise_baseline,
            'sample_rate': self.sample_rate,
            'samples_processed': len(self.noise_history)
        }