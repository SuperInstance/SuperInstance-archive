"""
Custom Wake Word Detection System
Advanced wake word detection with personalized training and multi-language support
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from dataclasses import dataclass
import threading
import time
import json
from scipy import signal
from scipy.signal import correlate
from scipy.fft import fft, ifft

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WakeWordSensitivity(Enum):
    """Wake word detection sensitivity levels"""
    VERY_LOW = 0.2
    LOW = 0.4
    NORMAL = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


class WakeWordStatus(Enum):
    """Wake word detection status"""
    INACTIVE = "inactive"
    LISTENING = "listening"
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    TRAINING = "training"


@dataclass
class WakeWordTemplate:
    """Wake word template for pattern matching"""
    word: str
    language: str
    user_id: str
    features: np.ndarray
    mfcc_features: np.ndarray
    spectral_features: np.ndarray
    duration_ms: int
    confidence_threshold: float
    created_at: datetime
    training_samples: List[np.ndarray]
    success_rate: float


@dataclass
class DetectionResult:
    """Wake word detection result"""
    detected: bool
    wake_word: str
    confidence: float
    timestamp: datetime
    audio_segment: np.ndarray
    detection_latency_ms: float
    false_positive_probability: float


@dataclass
class WakeWordConfig:
    """Wake word configuration"""
    wake_words: List[str]
    sensitivity: WakeWordSensitivity
    confirmation_required: bool
    multi_word_support: bool
    background_suppression: bool
    adaptive_threshold: bool
    user_specific: bool
    language_specific: bool


class AudioFeatureExtractor:
    """Extract audio features for wake word detection"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.frame_size = 512
        self.hop_size = 256
        self.mel_filters = 26
        self.mfcc_coeffs = 13
        
        # Pre-compute mel filter bank
        self.mel_filter_bank = self._create_mel_filter_bank()
        
        logger.info("AudioFeatureExtractor initialized")
    
    def _create_mel_filter_bank(self) -> np.ndarray:
        """Create mel-scale filter bank"""
        try:
            # Mel scale parameters
            low_freq_mel = 0
            high_freq_mel = 2595 * np.log10(1 + (self.sample_rate / 2) / 700)
            
            # Create mel points
            mel_points = np.linspace(low_freq_mel, high_freq_mel, self.mel_filters + 2)
            hz_points = 700 * (10**(mel_points / 2595) - 1)
            
            # Convert to FFT bins
            bin_points = np.floor((self.frame_size + 1) * hz_points / self.sample_rate)
            
            # Create filter bank
            fbank = np.zeros((self.mel_filters, int(np.floor(self.frame_size / 2 + 1))))
            
            for m in range(1, self.mel_filters + 1):
                f_m_minus = int(bin_points[m - 1])
                f_m = int(bin_points[m])
                f_m_plus = int(bin_points[m + 1])
                
                for k in range(f_m_minus, f_m):
                    fbank[m - 1, k] = (k - bin_points[m - 1]) / (bin_points[m] - bin_points[m - 1])
                for k in range(f_m, f_m_plus):
                    fbank[m - 1, k] = (bin_points[m + 1] - k) / (bin_points[m + 1] - bin_points[m])
            
            return fbank
            
        except Exception as e:
            logger.error(f"Error creating mel filter bank: {e}")
            return np.eye(self.mel_filters)
    
    def extract_mfcc(self, audio_segment: np.ndarray) -> np.ndarray:
        """Extract MFCC features from audio segment"""
        try:
            # Pre-emphasis
            pre_emphasized = np.append(audio_segment[0], audio_segment[1:] - 0.97 * audio_segment[:-1])
            
            # Frame the signal
            frames = self._frame_signal(pre_emphasized)
            
            # Apply window function
            windowed_frames = frames * np.hamming(self.frame_size)
            
            # FFT
            mag_frames = np.absolute(np.fft.rfft(windowed_frames, self.frame_size))
            
            # Power spectrum
            pow_frames = ((1.0 / self.frame_size) * mag_frames ** 2)
            
            # Apply mel filter bank
            filter_banks = np.dot(pow_frames, self.mel_filter_bank.T)
            filter_banks = np.where(filter_banks == 0, np.finfo(float).eps, filter_banks)
            filter_banks = np.log(filter_banks)
            
            # DCT for MFCC
            mfcc = self._dct(filter_banks)[:, :self.mfcc_coeffs]
            
            return mfcc
            
        except Exception as e:
            logger.error(f"Error extracting MFCC: {e}")
            return np.zeros((1, self.mfcc_coeffs))
    
    def _frame_signal(self, signal: np.ndarray) -> np.ndarray:
        """Frame the signal into overlapping windows"""
        signal_length = len(signal)
        frame_length = self.frame_size
        frame_step = self.hop_size
        
        if signal_length <= frame_length:
            num_frames = 1
        else:
            num_frames = 1 + int(np.ceil((1.0 * signal_length - frame_length) / frame_step))
        
        pad_signal_length = num_frames * frame_step + frame_length
        z = np.zeros((pad_signal_length - signal_length))
        pad_signal = np.append(signal, z)
        
        indices = np.tile(np.arange(0, frame_length), (num_frames, 1)) + \
                 np.tile(np.arange(0, num_frames * frame_step, frame_step), (frame_length, 1)).T
        
        return pad_signal[indices.astype(np.int32, copy=False)]
    
    def _dct(self, filter_banks: np.ndarray) -> np.ndarray:
        """Discrete Cosine Transform"""
        num_frames, num_filters = filter_banks.shape
        dct_matrix = np.zeros((num_filters, num_filters))
        
        for i in range(num_filters):
            for j in range(num_filters):
                dct_matrix[i, j] = np.cos(np.pi * i * (2 * j + 1) / (2 * num_filters))
        
        return np.dot(filter_banks, dct_matrix)
    
    def extract_spectral_features(self, audio_segment: np.ndarray) -> np.ndarray:
        """Extract spectral features"""
        try:
            # Compute spectrum
            spectrum = np.abs(fft(audio_segment))[:len(audio_segment)//2]
            
            # Spectral centroid
            freqs = np.arange(len(spectrum)) * self.sample_rate / (2 * len(spectrum))
            centroid = np.sum(freqs * spectrum) / np.sum(spectrum) if np.sum(spectrum) > 0 else 0
            
            # Spectral bandwidth
            bandwidth = np.sqrt(np.sum(((freqs - centroid) ** 2) * spectrum) / np.sum(spectrum)) if np.sum(spectrum) > 0 else 0
            
            # Spectral rolloff
            cumulative_spectrum = np.cumsum(spectrum)
            rolloff_idx = np.where(cumulative_spectrum >= 0.85 * cumulative_spectrum[-1])[0]
            rolloff = freqs[rolloff_idx[0]] if len(rolloff_idx) > 0 else 0
            
            # Zero crossing rate
            zcr = np.sum(np.diff(np.sign(audio_segment)) != 0) / len(audio_segment)
            
            # Energy
            energy = np.sum(audio_segment ** 2)
            
            return np.array([centroid, bandwidth, rolloff, zcr, energy])
            
        except Exception as e:
            logger.error(f"Error extracting spectral features: {e}")
            return np.zeros(5)
    
    def extract_combined_features(self, audio_segment: np.ndarray) -> Dict[str, np.ndarray]:
        """Extract all feature types"""
        return {
            "mfcc": self.extract_mfcc(audio_segment),
            "spectral": self.extract_spectral_features(audio_segment),
            "raw": audio_segment
        }


class WakeWordMatcher:
    """Pattern matching for wake word detection"""
    
    def __init__(self):
        self.templates: Dict[str, List[WakeWordTemplate]] = {}
        self.feature_extractor = AudioFeatureExtractor()
        
        # Matching parameters
        self.dtw_enabled = True
        self.template_matching_enabled = True
        self.neural_matching_enabled = False  # Placeholder for neural network
        
        logger.info("WakeWordMatcher initialized")
    
    def add_template(self, template: WakeWordTemplate):
        """Add a wake word template"""
        if template.word not in self.templates:
            self.templates[template.word] = []
        
        self.templates[template.word].append(template)
        logger.info(f"Added template for wake word: {template.word}")
    
    def calculate_dtw_distance(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """Calculate Dynamic Time Warping distance"""
        try:
            n, m = len(features1), len(features2)
            
            # Create cost matrix
            cost_matrix = np.inf * np.ones((n, m))
            cost_matrix[0, 0] = np.linalg.norm(features1[0] - features2[0])
            
            # Fill cost matrix
            for i in range(1, n):
                cost_matrix[i, 0] = cost_matrix[i-1, 0] + np.linalg.norm(features1[i] - features2[0])
            
            for j in range(1, m):
                cost_matrix[0, j] = cost_matrix[0, j-1] + np.linalg.norm(features1[0] - features2[j])
            
            for i in range(1, n):
                for j in range(1, m):
                    cost = np.linalg.norm(features1[i] - features2[j])
                    cost_matrix[i, j] = cost + min(
                        cost_matrix[i-1, j],      # insertion
                        cost_matrix[i, j-1],      # deletion
                        cost_matrix[i-1, j-1]     # match
                    )
            
            return cost_matrix[n-1, m-1] / max(n, m)
            
        except Exception as e:
            logger.error(f"Error calculating DTW distance: {e}")
            return float('inf')
    
    def calculate_template_similarity(self, features: Dict[str, np.ndarray], 
                                    template: WakeWordTemplate) -> float:
        """Calculate similarity to template"""
        try:
            # MFCC similarity using DTW
            if "mfcc" in features and len(template.mfcc_features) > 0:
                mfcc_distance = self.calculate_dtw_distance(features["mfcc"], template.mfcc_features)
                mfcc_similarity = np.exp(-mfcc_distance / 10)  # Convert distance to similarity
            else:
                mfcc_similarity = 0.0
            
            # Spectral feature similarity
            if "spectral" in features and len(template.spectral_features) > 0:
                spectral_distance = np.linalg.norm(features["spectral"] - template.spectral_features)
                spectral_similarity = np.exp(-spectral_distance / 100)
            else:
                spectral_similarity = 0.0
            
            # Combined similarity
            combined_similarity = 0.7 * mfcc_similarity + 0.3 * spectral_similarity
            
            return combined_similarity
            
        except Exception as e:
            logger.error(f"Error calculating template similarity: {e}")
            return 0.0
    
    def match_wake_word(self, audio_segment: np.ndarray) -> Tuple[str, float]:
        """Match audio segment against wake word templates"""
        try:
            # Extract features
            features = self.feature_extractor.extract_combined_features(audio_segment)
            
            best_match = ""
            best_confidence = 0.0
            
            # Test against all templates
            for wake_word, templates in self.templates.items():
                for template in templates:
                    similarity = self.calculate_template_similarity(features, template)
                    
                    if similarity > best_confidence:
                        best_confidence = similarity
                        best_match = wake_word
            
            return best_match, best_confidence
            
        except Exception as e:
            logger.error(f"Error matching wake word: {e}")
            return "", 0.0
    
    def update_template_performance(self, wake_word: str, user_id: str, 
                                  success: bool, confidence: float):
        """Update template performance statistics"""
        if wake_word in self.templates:
            for template in self.templates[wake_word]:
                if template.user_id == user_id:
                    # Update success rate with exponential smoothing
                    alpha = 0.1
                    template.success_rate = (1 - alpha) * template.success_rate + alpha * (1.0 if success else 0.0)
                    
                    # Adjust confidence threshold based on performance
                    if template.success_rate < 0.7 and confidence > 0.8:
                        template.confidence_threshold = min(template.confidence_threshold + 0.05, 0.9)
                    elif template.success_rate > 0.9 and confidence < 0.5:
                        template.confidence_threshold = max(template.confidence_threshold - 0.05, 0.3)


class CustomWakeWordDetector:
    """Main wake word detection system"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.matcher = WakeWordMatcher()
        
        # Detection parameters
        self.window_size_ms = 2000  # 2 second sliding window
        self.step_size_ms = 250     # 250ms step
        self.window_samples = int(self.sample_rate * self.window_size_ms / 1000)
        self.step_samples = int(self.sample_rate * self.step_size_ms / 1000)
        
        # Audio buffer
        self.audio_buffer = np.array([])
        self.buffer_max_size = self.sample_rate * 10  # 10 seconds max
        
        # Detection state
        self.status = WakeWordStatus.INACTIVE
        self.last_detection = None
        self.detection_callbacks: List[Callable] = []
        
        # Performance tracking
        self.detections_count = 0
        self.false_positives_count = 0
        self.true_positives_count = 0
        
        # Default wake words
        self.active_wake_words = ["activelog", "marine assistant", "voice command", "emergency"]
        self.wake_word_configs = {}
        
        logger.info("CustomWakeWordDetector initialized")
    
    def add_wake_word(self, wake_word: str, config: WakeWordConfig):
        """Add a custom wake word"""
        self.wake_word_configs[wake_word] = config
        if wake_word not in self.active_wake_words:
            self.active_wake_words.append(wake_word)
        
        logger.info(f"Added wake word: {wake_word}")
    
    def remove_wake_word(self, wake_word: str):
        """Remove a wake word"""
        if wake_word in self.active_wake_words:
            self.active_wake_words.remove(wake_word)
        if wake_word in self.wake_word_configs:
            del self.wake_word_configs[wake_word]
        
        logger.info(f"Removed wake word: {wake_word}")
    
    def train_wake_word(self, wake_word: str, training_samples: List[np.ndarray], 
                       user_id: str = "default", language: str = "en"):
        """Train a wake word with audio samples"""
        try:
            logger.info(f"Training wake word '{wake_word}' with {len(training_samples)} samples")
            
            # Extract features from training samples
            all_mfcc = []
            all_spectral = []
            
            for sample in training_samples:
                features = self.matcher.feature_extractor.extract_combined_features(sample)
                if "mfcc" in features:
                    all_mfcc.extend(features["mfcc"])
                if "spectral" in features:
                    all_spectral.append(features["spectral"])
            
            # Calculate average features
            avg_mfcc = np.mean(all_mfcc, axis=0) if all_mfcc else np.array([])
            avg_spectral = np.mean(all_spectral, axis=0) if all_spectral else np.array([])
            
            # Calculate duration
            avg_duration = int(np.mean([len(sample) for sample in training_samples]) / self.sample_rate * 1000)
            
            # Create template
            template = WakeWordTemplate(
                word=wake_word,
                language=language,
                user_id=user_id,
                features=np.concatenate([avg_mfcc.flatten(), avg_spectral]) if len(avg_mfcc) > 0 and len(avg_spectral) > 0 else np.array([]),
                mfcc_features=np.array(all_mfcc) if all_mfcc else np.array([]),
                spectral_features=avg_spectral,
                duration_ms=avg_duration,
                confidence_threshold=0.6,
                created_at=datetime.now(timezone.utc),
                training_samples=training_samples,
                success_rate=1.0
            )
            
            # Add to matcher
            self.matcher.add_template(template)
            
            logger.info(f"Successfully trained wake word: {wake_word}")
            return True
            
        except Exception as e:
            logger.error(f"Error training wake word: {e}")
            return False
    
    def add_audio_data(self, audio_data: np.ndarray):
        """Add audio data to processing buffer"""
        self.audio_buffer = np.append(self.audio_buffer, audio_data)
        
        # Trim buffer if too large
        if len(self.audio_buffer) > self.buffer_max_size:
            self.audio_buffer = self.audio_buffer[-self.buffer_max_size:]
    
    def process_audio_window(self) -> Optional[DetectionResult]:
        """Process current audio window for wake word detection"""
        if len(self.audio_buffer) < self.window_samples:
            return None
        
        try:
            start_time = time.time()
            
            # Extract current window
            window = self.audio_buffer[-self.window_samples:]
            
            # Match against wake words
            matched_word, confidence = self.matcher.match_wake_word(window)
            
            detection_latency = (time.time() - start_time) * 1000
            
            # Check if detection threshold is met
            detected = False
            if matched_word and confidence > 0.5:  # Base threshold
                # Get specific threshold for this wake word
                config = self.wake_word_configs.get(matched_word)
                if config:
                    threshold = config.sensitivity.value
                else:
                    threshold = 0.6  # Default threshold
                
                if confidence >= threshold:
                    detected = True
            
            # Create detection result
            result = DetectionResult(
                detected=detected,
                wake_word=matched_word,
                confidence=confidence,
                timestamp=datetime.now(timezone.utc),
                audio_segment=window,
                detection_latency_ms=detection_latency,
                false_positive_probability=self._calculate_false_positive_probability(confidence)
            )
            
            # Update statistics
            if detected:
                self.detections_count += 1
                self.last_detection = result
                self.status = WakeWordStatus.DETECTED
                
                # Notify callbacks
                for callback in self.detection_callbacks:
                    try:
                        callback(result)
                    except Exception as e:
                        logger.error(f"Error in detection callback: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing audio window: {e}")
            return None
    
    def _calculate_false_positive_probability(self, confidence: float) -> float:
        """Calculate probability of false positive"""
        # Simple heuristic based on confidence
        if confidence < 0.3:
            return 0.9
        elif confidence < 0.5:
            return 0.7
        elif confidence < 0.7:
            return 0.3
        elif confidence < 0.9:
            return 0.1
        else:
            return 0.05
    
    def start_detection(self):
        """Start wake word detection"""
        self.status = WakeWordStatus.LISTENING
        logger.info("Wake word detection started")
    
    def stop_detection(self):
        """Stop wake word detection"""
        self.status = WakeWordStatus.INACTIVE
        logger.info("Wake word detection stopped")
    
    def add_detection_callback(self, callback: Callable[[DetectionResult], None]):
        """Add callback for wake word detections"""
        self.detection_callbacks.append(callback)
    
    def remove_detection_callback(self, callback: Callable[[DetectionResult], None]):
        """Remove detection callback"""
        if callback in self.detection_callbacks:
            self.detection_callbacks.remove(callback)
    
    def confirm_detection(self, wake_word: str, user_id: str = "default", correct: bool = True):
        """Confirm whether a detection was correct"""
        if self.last_detection:
            confidence = self.last_detection.confidence
            self.matcher.update_template_performance(wake_word, user_id, correct, confidence)
            
            if correct:
                self.true_positives_count += 1
            else:
                self.false_positives_count += 1
            
            logger.info(f"Detection confirmed: {wake_word} - {'correct' if correct else 'incorrect'}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get detection performance statistics"""
        total_detections = self.true_positives_count + self.false_positives_count
        
        return {
            "total_detections": self.detections_count,
            "true_positives": self.true_positives_count,
            "false_positives": self.false_positives_count,
            "accuracy": self.true_positives_count / total_detections if total_detections > 0 else 0,
            "false_positive_rate": self.false_positives_count / total_detections if total_detections > 0 else 0,
            "active_wake_words": self.active_wake_words,
            "status": self.status.value,
            "templates_count": sum(len(templates) for templates in self.matcher.templates.values())
        }
    
    def export_wake_word_data(self, wake_word: str) -> Dict[str, Any]:
        """Export wake word training data"""
        if wake_word in self.matcher.templates:
            templates = self.matcher.templates[wake_word]
            exported_data = []
            
            for template in templates:
                exported_data.append({
                    "word": template.word,
                    "language": template.language,
                    "user_id": template.user_id,
                    "duration_ms": template.duration_ms,
                    "confidence_threshold": template.confidence_threshold,
                    "success_rate": template.success_rate,
                    "created_at": template.created_at.isoformat(),
                    "training_samples_count": len(template.training_samples)
                })
            
            return {
                "wake_word": wake_word,
                "templates": exported_data,
                "total_templates": len(templates)
            }
        
        return {"wake_word": wake_word, "templates": [], "total_templates": 0}
    
    def import_wake_word_data(self, wake_word_data: Dict[str, Any]) -> bool:
        """Import wake word training data"""
        try:
            wake_word = wake_word_data["wake_word"]
            
            for template_data in wake_word_data["templates"]:
                # Create template from imported data
                template = WakeWordTemplate(
                    word=template_data["word"],
                    language=template_data["language"],
                    user_id=template_data["user_id"],
                    features=np.array([]),  # Would need to re-extract
                    mfcc_features=np.array([]),  # Would need to re-extract
                    spectral_features=np.array([]),  # Would need to re-extract
                    duration_ms=template_data["duration_ms"],
                    confidence_threshold=template_data["confidence_threshold"],
                    created_at=datetime.fromisoformat(template_data["created_at"]),
                    training_samples=[],  # Would need original samples
                    success_rate=template_data["success_rate"]
                )
                
                self.matcher.add_template(template)
            
            logger.info(f"Imported {len(wake_word_data['templates'])} templates for '{wake_word}'")
            return True
            
        except Exception as e:
            logger.error(f"Error importing wake word data: {e}")
            return False
    
    def create_personalized_wake_word(self, user_id: str, base_word: str, 
                                    variations: List[str]) -> str:
        """Create personalized wake word with variations"""
        personalized_word = f"{base_word}_{user_id}"
        
        # Create training samples from variations
        training_samples = []
        
        # In a real implementation, would convert text variations to audio
        # For now, create placeholder samples
        for variation in variations:
            # Placeholder: create synthetic audio data
            duration_samples = int(self.sample_rate * 1.5)  # 1.5 seconds
            synthetic_sample = np.random.randn(duration_samples) * 0.1
            training_samples.append(synthetic_sample)
        
        # Train the personalized wake word
        success = self.train_wake_word(personalized_word, training_samples, user_id)
        
        if success:
            self.add_wake_word(personalized_word, WakeWordConfig(
                wake_words=[personalized_word],
                sensitivity=WakeWordSensitivity.NORMAL,
                confirmation_required=False,
                multi_word_support=True,
                background_suppression=True,
                adaptive_threshold=True,
                user_specific=True,
                language_specific=True
            ))
        
        return personalized_word if success else ""