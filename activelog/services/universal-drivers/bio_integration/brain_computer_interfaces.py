import numpy as np
import asyncio
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime
from scipy import signal
from scipy.fft import fft, fftfreq

class BCIDeviceType(Enum):
    EEG_HEADSET = "eeg_headset"
    INVASIVE_ARRAY = "invasive_array"
    ECOG_GRID = "ecog_grid"
    SINGLE_UNIT = "single_unit"
    LOCAL_FIELD_POTENTIAL = "lfp"
    FMRI_REALTIME = "fmri_realtime"
    FNIRS = "fnirs"
    HYBRID_BCI = "hybrid_bci"

class SignalType(Enum):
    RAW_EEG = "raw_eeg"
    FILTERED_EEG = "filtered_eeg"
    EVENT_RELATED_POTENTIAL = "erp"
    STEADY_STATE_VISUAL_EVOKED = "ssvep"
    MOTOR_IMAGERY = "motor_imagery"
    P300_SPELLER = "p300_speller"
    ATTENTION_LEVEL = "attention"
    MEDITATION_LEVEL = "meditation"
    EMOTION_STATE = "emotion"
    FATIGUE_LEVEL = "fatigue"

@dataclass
class BCIConfiguration:
    device_type: BCIDeviceType
    sampling_rate: int
    channel_count: int
    electrode_positions: List[str]
    signal_types: List[SignalType]
    preprocessing_pipeline: Dict[str, Any]
    feature_extraction: Dict[str, Any]
    classification_model: Optional[str] = None
    real_time_processing: bool = True

@dataclass
class BrainSignal:
    timestamp: datetime
    channel_data: np.ndarray
    signal_quality: List[float]
    artifacts: Dict[str, bool]
    processed_features: Dict[str, float]
    classification_result: Optional[Dict[str, Any]] = None

class BrainComputerInterface:
    def __init__(self, config: BCIConfiguration):
        self.config = config
        self.is_recording = False
        self.signal_buffer = []
        self.max_buffer_size = config.sampling_rate * 30  # 30 seconds
        self.callbacks = {}
        self.current_signal = None
        self.background_thread = None
        
        # Initialize signal processing components
        self.filters = self._initialize_filters()
        self.feature_extractors = self._initialize_feature_extractors()
        self.artifact_detectors = self._initialize_artifact_detectors()
        
    def _initialize_filters(self) -> Dict[str, Any]:
        """Initialize digital filters for signal processing"""
        fs = self.config.sampling_rate
        
        filters = {}
        
        # Bandpass filter for EEG (0.5-50 Hz)
        nyq = fs / 2
        low_cut = 0.5 / nyq
        high_cut = 50.0 / nyq
        filters['bandpass'] = signal.butter(4, [low_cut, high_cut], btype='band')
        
        # Notch filter for 50/60 Hz power line noise
        filters['notch_50'] = signal.iirnotch(50, 30, fs)
        filters['notch_60'] = signal.iirnotch(60, 30, fs)
        
        # Alpha band filter (8-13 Hz)
        alpha_low = 8.0 / nyq
        alpha_high = 13.0 / nyq
        filters['alpha'] = signal.butter(4, [alpha_low, alpha_high], btype='band')
        
        # Beta band filter (13-30 Hz)
        beta_low = 13.0 / nyq
        beta_high = 30.0 / nyq
        filters['beta'] = signal.butter(4, [beta_low, beta_high], btype='band')
        
        # Theta band filter (4-8 Hz)
        theta_low = 4.0 / nyq
        theta_high = 8.0 / nyq
        filters['theta'] = signal.butter(4, [theta_low, theta_high], btype='band')
        
        # Gamma band filter (30-100 Hz)
        gamma_low = 30.0 / nyq
        gamma_high = min(100.0 / nyq, 0.95)  # Ensure below Nyquist
        filters['gamma'] = signal.butter(4, [gamma_low, gamma_high], btype='band')
        
        return filters
    
    def _initialize_feature_extractors(self) -> Dict[str, Callable]:
        """Initialize feature extraction methods"""
        extractors = {}
        
        def power_spectral_density(data):
            freqs, psd = signal.welch(data, fs=self.config.sampling_rate, nperseg=256)
            return {'freqs': freqs, 'psd': psd}
        
        def band_power(data, band_name):
            if band_name in self.filters:
                filtered = signal.filtfilt(*self.filters[band_name], data)
                return np.mean(filtered ** 2)
            return 0.0
        
        def hjorth_parameters(data):
            # Hjorth Activity, Mobility, and Complexity
            diff1 = np.diff(data)
            diff2 = np.diff(diff1)
            
            activity = np.var(data)
            mobility = np.sqrt(np.var(diff1) / np.var(data))
            complexity = np.sqrt(np.var(diff2) / np.var(diff1)) / mobility
            
            return {'activity': activity, 'mobility': mobility, 'complexity': complexity}
        
        def common_spatial_patterns(data_matrix):
            # Simplified CSP for motor imagery
            # In practice, this would use trained CSP filters
            if data_matrix.shape[0] < 2:
                return data_matrix
            
            cov_matrix = np.cov(data_matrix)
            eigenvals, eigenvecs = np.linalg.eig(cov_matrix)
            
            # Sort by eigenvalues
            idx = np.argsort(eigenvals)[::-1]
            eigenvecs = eigenvecs[:, idx]
            
            # Use first and last components
            spatial_filter = np.vstack([eigenvecs[:, :2], eigenvecs[:, -2:]])
            return np.dot(spatial_filter, data_matrix)
        
        extractors['psd'] = power_spectral_density
        extractors['band_power'] = band_power
        extractors['hjorth'] = hjorth_parameters
        extractors['csp'] = common_spatial_patterns
        
        return extractors
    
    def _initialize_artifact_detectors(self) -> Dict[str, Callable]:
        """Initialize artifact detection methods"""
        detectors = {}
        
        def eye_blink_detection(data, threshold=100):
            # Simple threshold-based eye blink detection
            return np.any(np.abs(data) > threshold)
        
        def muscle_artifact_detection(data, high_freq_threshold=30):
            # Detect high-frequency muscle artifacts
            freqs, psd = signal.welch(data, fs=self.config.sampling_rate)
            high_freq_power = np.sum(psd[freqs > high_freq_threshold])
            total_power = np.sum(psd)
            return (high_freq_power / total_power) > 0.3
        
        def electrode_drift_detection(data, window_size=1000):
            # Detect slow electrode drift
            if len(data) < window_size:
                return False
            windowed_means = [np.mean(data[i:i+window_size]) 
                             for i in range(0, len(data)-window_size, window_size)]
            return np.std(windowed_means) > np.std(data) * 0.1
        
        detectors['eye_blink'] = eye_blink_detection
        detectors['muscle'] = muscle_artifact_detection
        detectors['drift'] = electrode_drift_detection
        
        return detectors
    
    async def start_recording(self):
        """Start real-time signal acquisition"""
        if self.is_recording:
            return
        
        self.is_recording = True
        self.background_thread = threading.Thread(target=self._recording_loop)
        self.background_thread.daemon = True
        self.background_thread.start()
    
    async def stop_recording(self):
        """Stop signal acquisition"""
        self.is_recording = False
        if self.background_thread:
            self.background_thread.join()
    
    def _recording_loop(self):
        """Main recording loop running in background thread"""
        while self.is_recording:
            # Simulate signal acquisition
            signal_data = self._simulate_brain_signals()
            
            # Process signal
            processed_signal = self._process_signal(signal_data)
            
            # Store in buffer
            self.signal_buffer.append(processed_signal)
            if len(self.signal_buffer) > self.max_buffer_size:
                self.signal_buffer.pop(0)
            
            self.current_signal = processed_signal
            
            # Trigger callbacks
            self._trigger_callbacks(processed_signal)
            
            # Wait for next sample
            time.sleep(1.0 / self.config.sampling_rate)
    
    def _simulate_brain_signals(self) -> np.ndarray:
        """Simulate realistic brain signals for testing"""
        duration = 1.0 / self.config.sampling_rate  # Single sample duration
        t = np.linspace(0, duration, int(self.config.sampling_rate * duration), endpoint=False)
        
        signals = np.zeros((self.config.channel_count, len(t)))
        
        for ch in range(self.config.channel_count):
            # Base EEG signal with multiple frequency components
            signal_data = (
                # Alpha rhythm (8-13 Hz)
                10 * np.sin(2 * np.pi * 10 * t + np.random.random() * 2 * np.pi) +
                # Beta activity (15-25 Hz)
                5 * np.sin(2 * np.pi * 20 * t + np.random.random() * 2 * np.pi) +
                # Theta waves (4-8 Hz)
                8 * np.sin(2 * np.pi * 6 * t + np.random.random() * 2 * np.pi) +
                # Random noise
                np.random.normal(0, 2, len(t))
            )
            
            # Add occasional artifacts
            if np.random.random() < 0.01:  # 1% chance of eye blink
                signal_data += 50 * np.exp(-((t - 0.5) ** 2) / 0.01)
            
            if np.random.random() < 0.005:  # 0.5% chance of muscle artifact
                signal_data += 20 * np.random.normal(0, 1, len(t))
            
            signals[ch] = signal_data
        
        return signals
    
    def _process_signal(self, raw_data: np.ndarray) -> BrainSignal:
        """Process raw signal data"""
        timestamp = datetime.now()
        
        # Apply preprocessing pipeline
        processed_data = raw_data.copy()
        
        # Apply filters
        if 'bandpass' in self.config.preprocessing_pipeline:
            for ch in range(processed_data.shape[0]):
                processed_data[ch] = signal.filtfilt(*self.filters['bandpass'], processed_data[ch])
        
        if 'notch_filter' in self.config.preprocessing_pipeline:
            for ch in range(processed_data.shape[0]):
                processed_data[ch] = signal.filtfilt(*self.filters['notch_50'], processed_data[ch])
        
        # Calculate signal quality
        signal_quality = []
        for ch in range(processed_data.shape[0]):
            # Simple SNR-based quality metric
            signal_power = np.var(processed_data[ch])
            noise_estimate = np.var(np.diff(processed_data[ch]))  # High-frequency noise
            snr = signal_power / (noise_estimate + 1e-10)
            signal_quality.append(min(snr / 10.0, 1.0))  # Normalize to 0-1
        
        # Detect artifacts
        artifacts = {}
        for ch in range(processed_data.shape[0]):
            artifacts[f'ch_{ch}_eye_blink'] = self.artifact_detectors['eye_blink'](processed_data[ch])
            artifacts[f'ch_{ch}_muscle'] = self.artifact_detectors['muscle'](processed_data[ch])
            artifacts[f'ch_{ch}_drift'] = self.artifact_detectors['drift'](processed_data[ch])
        
        # Extract features
        features = {}
        for ch in range(processed_data.shape[0]):
            ch_name = f'ch_{ch}'
            
            # Band power features
            for band in ['alpha', 'beta', 'theta', 'gamma']:
                if band in self.filters:
                    features[f'{ch_name}_{band}_power'] = self.feature_extractors['band_power'](processed_data[ch], band)
            
            # Hjorth parameters
            hjorth = self.feature_extractors['hjorth'](processed_data[ch])
            for param, value in hjorth.items():
                features[f'{ch_name}_hjorth_{param}'] = value
        
        # Overall brain state estimation
        alpha_power = np.mean([features.get(f'ch_{ch}_alpha_power', 0) for ch in range(processed_data.shape[0])])
        beta_power = np.mean([features.get(f'ch_{ch}_beta_power', 0) for ch in range(processed_data.shape[0])])
        theta_power = np.mean([features.get(f'ch_{ch}_theta_power', 0) for ch in range(processed_data.shape[0])])
        
        # Attention and meditation estimation (simplified)
        features['attention_level'] = min(beta_power / (alpha_power + theta_power + 1e-10), 1.0)
        features['meditation_level'] = min(alpha_power / (beta_power + theta_power + 1e-10), 1.0)
        features['fatigue_level'] = min(theta_power / (alpha_power + beta_power + 1e-10), 1.0)
        
        return BrainSignal(
            timestamp=timestamp,
            channel_data=processed_data,
            signal_quality=signal_quality,
            artifacts=artifacts,
            processed_features=features
        )
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for specific events"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    def _trigger_callbacks(self, signal: BrainSignal):
        """Trigger registered callbacks"""
        # General signal callback
        if 'signal_update' in self.callbacks:
            for callback in self.callbacks['signal_update']:
                try:
                    callback(signal)
                except Exception as e:
                    print(f"Callback error: {e}")
        
        # Attention level change callback
        attention = signal.processed_features.get('attention_level', 0)
        if 'attention_change' in self.callbacks and attention > 0.7:
            for callback in self.callbacks['attention_change']:
                try:
                    callback(attention)
                except Exception as e:
                    print(f"Attention callback error: {e}")
        
        # Artifact detection callback
        if any(signal.artifacts.values()) and 'artifact_detected' in self.callbacks:
            for callback in self.callbacks['artifact_detected']:
                try:
                    callback(signal.artifacts)
                except Exception as e:
                    print(f"Artifact callback error: {e}")
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current BCI state"""
        if not self.current_signal:
            return {'status': 'no_signal'}
        
        return {
            'status': 'active' if self.is_recording else 'stopped',
            'timestamp': self.current_signal.timestamp.isoformat(),
            'signal_quality': {
                'average': np.mean(self.current_signal.signal_quality),
                'per_channel': self.current_signal.signal_quality
            },
            'features': {
                k: float(v) if isinstance(v, (int, float, np.number)) else v 
                for k, v in self.current_signal.processed_features.items()
            },
            'artifacts_detected': sum(self.current_signal.artifacts.values()),
            'buffer_size': len(self.signal_buffer)
        }
    
    def classify_mental_state(self) -> Dict[str, Any]:
        """Classify current mental state"""
        if not self.current_signal:
            return {'state': 'unknown', 'confidence': 0.0}
        
        features = self.current_signal.processed_features
        
        # Simple rule-based classification
        attention = features.get('attention_level', 0)
        meditation = features.get('meditation_level', 0)
        fatigue = features.get('fatigue_level', 0)
        
        states = {
            'focused': attention,
            'relaxed': meditation,
            'tired': fatigue,
            'neutral': 1 - max(attention, meditation, fatigue)
        }
        
        dominant_state = max(states, key=states.get)
        confidence = states[dominant_state]
        
        return {
            'state': dominant_state,
            'confidence': confidence,
            'all_states': states,
            'timestamp': self.current_signal.timestamp.isoformat()
        }
    
    def export_session_data(self, filename: str, format: str = 'json'):
        """Export recorded session data"""
        if format == 'json':
            session_data = {
                'config': asdict(self.config),
                'signal_count': len(self.signal_buffer),
                'session_duration': len(self.signal_buffer) / self.config.sampling_rate,
                'average_signal_quality': np.mean([np.mean(s.signal_quality) for s in self.signal_buffer]),
                'artifact_count': sum([sum(s.artifacts.values()) for s in self.signal_buffer]),
                'timestamp': datetime.now().isoformat()
            }
            
            with open(filename, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
    
    def inject_stimulus(self, stimulus_type: str, parameters: Dict[str, Any]):
        """Inject simulated stimulus for testing"""
        # This would interface with actual stimulus presentation systems
        stimulus_info = {
            'type': stimulus_type,
            'parameters': parameters,
            'timestamp': datetime.now().isoformat()
        }
        
        if 'stimulus_presented' in self.callbacks:
            for callback in self.callbacks['stimulus_presented']:
                try:
                    callback(stimulus_info)
                except Exception as e:
                    print(f"Stimulus callback error: {e}")

class EEGHeadsetSimulator(BrainComputerInterface):
    """Specialized simulator for consumer EEG headsets"""
    
    def __init__(self, model: str = "generic"):
        # Common EEG headset configurations
        configs = {
            "emotiv_epoc": BCIConfiguration(
                device_type=BCIDeviceType.EEG_HEADSET,
                sampling_rate=128,
                channel_count=14,
                electrode_positions=['AF3', 'F7', 'F3', 'FC5', 'T7', 'P7', 'O1', 'O2', 'P8', 'T8', 'FC6', 'F4', 'F8', 'AF4'],
                signal_types=[SignalType.RAW_EEG, SignalType.ATTENTION_LEVEL, SignalType.MEDITATION_LEVEL],
                preprocessing_pipeline={'bandpass': True, 'notch_filter': True},
                feature_extraction={'band_power': True, 'hjorth': True}
            ),
            "muse_headband": BCIConfiguration(
                device_type=BCIDeviceType.EEG_HEADSET,
                sampling_rate=256,
                channel_count=4,
                electrode_positions=['TP9', 'AF7', 'AF8', 'TP10'],
                signal_types=[SignalType.RAW_EEG, SignalType.MEDITATION_LEVEL],
                preprocessing_pipeline={'bandpass': True, 'notch_filter': True},
                feature_extraction={'band_power': True}
            ),
            "openBCI": BCIConfiguration(
                device_type=BCIDeviceType.EEG_HEADSET,
                sampling_rate=250,
                channel_count=8,
                electrode_positions=['Fp1', 'Fp2', 'C3', 'C4', 'P7', 'P8', 'O1', 'O2'],
                signal_types=[SignalType.RAW_EEG, SignalType.MOTOR_IMAGERY],
                preprocessing_pipeline={'bandpass': True, 'notch_filter': True},
                feature_extraction={'band_power': True, 'hjorth': True, 'csp': True}
            )
        }
        
        config = configs.get(model, configs["generic"] if "generic" in configs else configs["openBCI"])
        super().__init__(config)
        self.model = model

if __name__ == "__main__":
    print("Brain-Computer Interface Simulation")
    print("=" * 50)
    
    # Create BCI simulator
    bci = EEGHeadsetSimulator("openBCI")
    
    # Register callbacks
    def on_attention_change(attention_level):
        print(f"High attention detected: {attention_level:.2f}")
    
    def on_artifact(artifacts):
        detected = [k for k, v in artifacts.items() if v]
        if detected:
            print(f"Artifacts detected: {detected}")
    
    bci.register_callback('attention_change', on_attention_change)
    bci.register_callback('artifact_detected', on_artifact)
    
    async def demo():
        print(f"Starting {bci.model} simulation...")
        await bci.start_recording()
        
        try:
            for i in range(10):
                await asyncio.sleep(1)
                state = bci.get_current_state()
                mental_state = bci.classify_mental_state()
                
                print(f"Time: {i+1}s")
                print(f"  Signal quality: {state['signal_quality']['average']:.2f}")
                print(f"  Mental state: {mental_state['state']} ({mental_state['confidence']:.2f})")
                print(f"  Features: Attention={state['features'].get('attention_level', 0):.2f}, "
                      f"Meditation={state['features'].get('meditation_level', 0):.2f}")
                print()
            
        finally:
            await bci.stop_recording()
            print("Simulation completed")
    
    asyncio.run(demo())