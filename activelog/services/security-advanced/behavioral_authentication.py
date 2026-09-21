"""
Behavioral Authentication System
Continuous authentication based on user behavior patterns and biometric characteristics
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any, Callable, Union, Tuple
from enum import Enum
import hashlib
import secrets
import asyncio
from datetime import datetime, timedelta
import json
import numpy as np
from abc import ABC, abstractmethod
import math
import statistics

class BehavioralMetric(Enum):
    TYPING_DYNAMICS = "typing_dynamics"
    MOUSE_MOVEMENT = "mouse_movement"
    TOUCH_PATTERNS = "touch_patterns"
    GAIT_ANALYSIS = "gait_analysis"
    VOICE_PATTERNS = "voice_patterns"
    APP_USAGE_PATTERNS = "app_usage_patterns"
    LOCATION_PATTERNS = "location_patterns"
    DEVICE_INTERACTION = "device_interaction"

class AuthenticationDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    CHALLENGE = "challenge"
    MONITOR = "monitor"

class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ModelStatus(Enum):
    TRAINING = "training"
    ACTIVE = "active"
    UPDATING = "updating"
    EXPIRED = "expired"

@dataclass
class TypingDynamics:
    """Keystroke dynamics and timing patterns"""
    dwell_times: List[float]  # Time key is pressed
    flight_times: List[float]  # Time between key presses
    typing_rhythm: float
    pressure_variations: List[float]
    common_digraphs: Dict[str, float]  # Two-character combinations timing

@dataclass
class MouseMovement:
    """Mouse movement patterns and characteristics"""
    velocity_profile: List[float]
    acceleration_patterns: List[float]
    click_patterns: List[Dict[str, Any]]
    scroll_behavior: Dict[str, float]
    tremor_frequency: float
    movement_efficiency: float

@dataclass
class TouchPatterns:
    """Touch screen interaction patterns"""
    touch_pressure: List[float]
    touch_area: List[float]
    swipe_velocities: List[float]
    tap_timing: List[float]
    gesture_patterns: Dict[str, List[float]]
    hand_orientation: str

@dataclass
class VoiceCharacteristics:
    """Voice biometric patterns"""
    fundamental_frequency: float
    formant_frequencies: List[float]
    spectral_features: List[float]
    prosodic_features: Dict[str, float]
    voice_quality_metrics: Dict[str, float]

@dataclass
class BehavioralProfile:
    """Complete behavioral profile for a user"""
    user_id: str
    typing_dynamics: Optional[TypingDynamics]
    mouse_movement: Optional[MouseMovement]
    touch_patterns: Optional[TouchPatterns]
    voice_characteristics: Optional[VoiceCharacteristics]
    app_usage: Dict[str, float]
    location_patterns: Dict[str, Any]
    device_preferences: Dict[str, Any]
    temporal_patterns: Dict[str, List[float]]
    created_at: datetime
    last_updated: datetime
    sample_count: int

@dataclass
class BehavioralSample:
    """Individual behavioral measurement sample"""
    sample_id: str
    user_id: str
    metric_type: BehavioralMetric
    timestamp: datetime
    raw_data: Dict[str, Any]
    processed_features: List[float]
    context: Dict[str, Any]  # Environment, device, task type, etc.

@dataclass
class AuthenticationAttempt:
    """Record of authentication attempt with behavioral analysis"""
    attempt_id: str
    user_id: str
    timestamp: datetime
    behavioral_samples: List[BehavioralSample]
    confidence_scores: Dict[BehavioralMetric, float]
    overall_confidence: float
    decision: AuthenticationDecision
    threat_level: ThreatLevel
    additional_context: Dict[str, Any]

@dataclass
class AnomalyDetection:
    """Detected behavioral anomaly"""
    anomaly_id: str
    user_id: str
    detected_at: datetime
    metric_type: BehavioralMetric
    anomaly_score: float
    deviation_details: Dict[str, Any]
    possible_causes: List[str]
    risk_assessment: ThreatLevel

class BehavioralAnalyzer(ABC):
    """Abstract base for behavioral pattern analysis"""
    
    @abstractmethod
    async def extract_features(self, raw_data: Dict[str, Any]) -> List[float]:
        """Extract features from raw behavioral data"""
        pass
    
    @abstractmethod
    async def calculate_similarity(self, features1: List[float], features2: List[float]) -> float:
        """Calculate similarity between feature vectors"""
        pass
    
    @abstractmethod
    async def detect_anomaly(self, current_features: List[float], baseline_profile: Any) -> float:
        """Detect anomalies in behavioral patterns"""
        pass

class TypingDynamicsAnalyzer(BehavioralAnalyzer):
    """Analyzer for keystroke dynamics"""
    
    async def extract_features(self, raw_data: Dict[str, Any]) -> List[float]:
        """Extract typing dynamics features"""
        keystrokes = raw_data.get("keystrokes", [])
        
        if len(keystrokes) < 2:
            return [0.0] * 10  # Default feature vector
        
        # Calculate dwell times (key press duration)
        dwell_times = []
        flight_times = []
        
        for i, keystroke in enumerate(keystrokes):
            if "press_time" in keystroke and "release_time" in keystroke:
                dwell_time = keystroke["release_time"] - keystroke["press_time"]
                dwell_times.append(dwell_time)
            
            if i > 0:
                flight_time = keystroke["press_time"] - keystrokes[i-1]["release_time"]
                flight_times.append(flight_time)
        
        features = []
        
        # Statistical features of dwell times
        if dwell_times:
            features.extend([
                statistics.mean(dwell_times),
                statistics.stdev(dwell_times) if len(dwell_times) > 1 else 0,
                min(dwell_times),
                max(dwell_times)
            ])
        else:
            features.extend([0, 0, 0, 0])
        
        # Statistical features of flight times
        if flight_times:
            features.extend([
                statistics.mean(flight_times),
                statistics.stdev(flight_times) if len(flight_times) > 1 else 0,
                min(flight_times),
                max(flight_times)
            ])
        else:
            features.extend([0, 0, 0, 0])
        
        # Typing rhythm (overall cadence)
        if len(keystrokes) > 1:
            total_time = keystrokes[-1]["press_time"] - keystrokes[0]["press_time"]
            typing_rhythm = len(keystrokes) / total_time if total_time > 0 else 0
            features.append(typing_rhythm)
        else:
            features.append(0)
        
        # Pressure variations (if available)
        pressures = [k.get("pressure", 0) for k in keystrokes if "pressure" in k]
        if pressures:
            features.append(statistics.mean(pressures))
        else:
            features.append(0)
        
        return features
    
    async def calculate_similarity(self, features1: List[float], features2: List[float]) -> float:
        """Calculate cosine similarity between feature vectors"""
        if len(features1) != len(features2):
            return 0.0
        
        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(features1, features2))
        magnitude1 = math.sqrt(sum(a * a for a in features1))
        magnitude2 = math.sqrt(sum(b * b for b in features2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def detect_anomaly(self, current_features: List[float], baseline_profile: TypingDynamics) -> float:
        """Detect typing anomalies using statistical deviation"""
        if not baseline_profile.dwell_times:
            return 1.0  # High anomaly if no baseline
        
        # Compare current features with baseline statistics
        baseline_features = [
            statistics.mean(baseline_profile.dwell_times),
            statistics.stdev(baseline_profile.dwell_times) if len(baseline_profile.dwell_times) > 1 else 0,
            statistics.mean(baseline_profile.flight_times) if baseline_profile.flight_times else 0,
            baseline_profile.typing_rhythm
        ]
        
        # Calculate z-scores for deviation
        deviations = []
        for i, (current, baseline) in enumerate(zip(current_features[:4], baseline_features)):
            if baseline > 0:
                deviation = abs(current - baseline) / baseline
                deviations.append(deviation)
        
        # Return average deviation as anomaly score
        return statistics.mean(deviations) if deviations else 1.0

class MouseMovementAnalyzer(BehavioralAnalyzer):
    """Analyzer for mouse movement patterns"""
    
    async def extract_features(self, raw_data: Dict[str, Any]) -> List[float]:
        """Extract mouse movement features"""
        movements = raw_data.get("movements", [])
        clicks = raw_data.get("clicks", [])
        
        if len(movements) < 2:
            return [0.0] * 8  # Default feature vector
        
        # Calculate velocities and accelerations
        velocities = []
        accelerations = []
        
        for i in range(1, len(movements)):
            prev_pos = movements[i-1]
            curr_pos = movements[i]
            
            # Calculate velocity
            dx = curr_pos["x"] - prev_pos["x"]
            dy = curr_pos["y"] - prev_pos["y"]
            dt = curr_pos["timestamp"] - prev_pos["timestamp"]
            
            if dt > 0:
                velocity = math.sqrt(dx*dx + dy*dy) / dt
                velocities.append(velocity)
                
                if i > 1 and len(velocities) > 1:
                    acceleration = (velocities[-1] - velocities[-2]) / dt
                    accelerations.append(acceleration)
        
        features = []
        
        # Velocity statistics
        if velocities:
            features.extend([
                statistics.mean(velocities),
                statistics.stdev(velocities) if len(velocities) > 1 else 0,
                max(velocities),
                min(velocities)
            ])
        else:
            features.extend([0, 0, 0, 0])
        
        # Acceleration statistics
        if accelerations:
            features.extend([
                statistics.mean(accelerations),
                statistics.stdev(accelerations) if len(accelerations) > 1 else 0
            ])
        else:
            features.extend([0, 0])
        
        # Click pattern features
        if clicks:
            click_intervals = []
            for i in range(1, len(clicks)):
                interval = clicks[i]["timestamp"] - clicks[i-1]["timestamp"]
                click_intervals.append(interval)
            
            if click_intervals:
                features.append(statistics.mean(click_intervals))
            else:
                features.append(0)
        else:
            features.append(0)
        
        # Movement efficiency (direct path vs actual path)
        if len(movements) > 1:
            start_pos = movements[0]
            end_pos = movements[-1]
            direct_distance = math.sqrt(
                (end_pos["x"] - start_pos["x"])**2 + 
                (end_pos["y"] - start_pos["y"])**2
            )
            
            actual_distance = sum(
                math.sqrt((movements[i]["x"] - movements[i-1]["x"])**2 + 
                         (movements[i]["y"] - movements[i-1]["y"])**2)
                for i in range(1, len(movements))
            )
            
            efficiency = direct_distance / actual_distance if actual_distance > 0 else 0
            features.append(efficiency)
        else:
            features.append(0)
        
        return features
    
    async def calculate_similarity(self, features1: List[float], features2: List[float]) -> float:
        """Calculate similarity using Euclidean distance"""
        if len(features1) != len(features2):
            return 0.0
        
        # Normalized Euclidean distance
        distance = math.sqrt(sum((a - b)**2 for a, b in zip(features1, features2)))
        max_distance = math.sqrt(len(features1))  # Maximum possible distance
        
        return 1.0 - (distance / max_distance) if max_distance > 0 else 0.0
    
    async def detect_anomaly(self, current_features: List[float], baseline_profile: MouseMovement) -> float:
        """Detect mouse movement anomalies"""
        if not baseline_profile.velocity_profile:
            return 1.0
        
        # Compare velocity patterns
        baseline_velocity = statistics.mean(baseline_profile.velocity_profile)
        current_velocity = current_features[0] if current_features else 0
        
        velocity_deviation = abs(current_velocity - baseline_velocity) / baseline_velocity if baseline_velocity > 0 else 1.0
        
        # Compare movement efficiency
        baseline_efficiency = baseline_profile.movement_efficiency
        current_efficiency = current_features[-1] if current_features else 0
        
        efficiency_deviation = abs(current_efficiency - baseline_efficiency) / baseline_efficiency if baseline_efficiency > 0 else 1.0
        
        # Return combined anomaly score
        return (velocity_deviation + efficiency_deviation) / 2

class BehavioralAuthenticationSystem:
    """Main behavioral authentication system"""
    
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self.user_profiles: Dict[str, BehavioralProfile] = {}
        self.analyzers: Dict[BehavioralMetric, BehavioralAnalyzer] = {
            BehavioralMetric.TYPING_DYNAMICS: TypingDynamicsAnalyzer(),
            BehavioralMetric.MOUSE_MOVEMENT: MouseMovementAnalyzer()
        }
        self.authentication_history: List[AuthenticationAttempt] = []
        self.anomaly_detections: List[AnomalyDetection] = []
    
    async def create_user_profile(self, user_id: str) -> BehavioralProfile:
        """Create initial behavioral profile for user"""
        profile = BehavioralProfile(
            user_id=user_id,
            typing_dynamics=None,
            mouse_movement=None,
            touch_patterns=None,
            voice_characteristics=None,
            app_usage={},
            location_patterns={},
            device_preferences={},
            temporal_patterns={},
            created_at=datetime.now(),
            last_updated=datetime.now(),
            sample_count=0
        )
        
        self.user_profiles[user_id] = profile
        return profile
    
    async def collect_behavioral_sample(
        self,
        user_id: str,
        metric_type: BehavioralMetric,
        raw_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> BehavioralSample:
        """Collect and process behavioral sample"""
        if metric_type not in self.analyzers:
            raise ValueError(f"Unsupported metric type: {metric_type}")
        
        analyzer = self.analyzers[metric_type]
        processed_features = await analyzer.extract_features(raw_data)
        
        sample = BehavioralSample(
            sample_id=f"sample_{secrets.token_hex(8)}",
            user_id=user_id,
            metric_type=metric_type,
            timestamp=datetime.now(),
            raw_data=raw_data,
            processed_features=processed_features,
            context=context or {}
        )
        
        # Update user profile with new sample
        await self._update_user_profile(sample)
        
        return sample
    
    async def _update_user_profile(self, sample: BehavioralSample):
        """Update user profile with new behavioral sample"""
        if sample.user_id not in self.user_profiles:
            await self.create_user_profile(sample.user_id)
        
        profile = self.user_profiles[sample.user_id]
        profile.sample_count += 1
        profile.last_updated = datetime.now()
        
        # Update specific behavioral patterns based on metric type
        if sample.metric_type == BehavioralMetric.TYPING_DYNAMICS:
            await self._update_typing_dynamics(profile, sample)
        elif sample.metric_type == BehavioralMetric.MOUSE_MOVEMENT:
            await self._update_mouse_movement(profile, sample)
    
    async def _update_typing_dynamics(self, profile: BehavioralProfile, sample: BehavioralSample):
        """Update typing dynamics in profile"""
        keystrokes = sample.raw_data.get("keystrokes", [])
        
        if not keystrokes:
            return
        
        dwell_times = []
        flight_times = []
        pressures = []
        
        for i, keystroke in enumerate(keystrokes):
            if "press_time" in keystroke and "release_time" in keystroke:
                dwell_time = keystroke["release_time"] - keystroke["press_time"]
                dwell_times.append(dwell_time)
                
                if "pressure" in keystroke:
                    pressures.append(keystroke["pressure"])
            
            if i > 0:
                flight_time = keystroke["press_time"] - keystrokes[i-1]["release_time"]
                flight_times.append(flight_time)
        
        # Calculate typing rhythm
        if len(keystrokes) > 1:
            total_time = keystrokes[-1]["press_time"] - keystrokes[0]["press_time"]
            typing_rhythm = len(keystrokes) / total_time if total_time > 0 else 0
        else:
            typing_rhythm = 0
        
        # Update or create typing dynamics
        if profile.typing_dynamics is None:
            profile.typing_dynamics = TypingDynamics(
                dwell_times=dwell_times,
                flight_times=flight_times,
                typing_rhythm=typing_rhythm,
                pressure_variations=pressures,
                common_digraphs={}
            )
        else:
            # Exponential moving average update
            alpha = 0.1  # Learning rate
            profile.typing_dynamics.dwell_times = self._update_list_ema(
                profile.typing_dynamics.dwell_times, dwell_times, alpha
            )
            profile.typing_dynamics.flight_times = self._update_list_ema(
                profile.typing_dynamics.flight_times, flight_times, alpha
            )
            profile.typing_dynamics.typing_rhythm = (
                alpha * typing_rhythm + (1 - alpha) * profile.typing_dynamics.typing_rhythm
            )
    
    async def _update_mouse_movement(self, profile: BehavioralProfile, sample: BehavioralSample):
        """Update mouse movement patterns in profile"""
        analyzer = self.analyzers[BehavioralMetric.MOUSE_MOVEMENT]
        features = await analyzer.extract_features(sample.raw_data)
        
        if profile.mouse_movement is None:
            profile.mouse_movement = MouseMovement(
                velocity_profile=features[:4] if len(features) >= 4 else [0, 0, 0, 0],
                acceleration_patterns=features[4:6] if len(features) >= 6 else [0, 0],
                click_patterns=[],
                scroll_behavior={},
                tremor_frequency=0.0,
                movement_efficiency=features[-1] if features else 0
            )
        else:
            # Update with exponential moving average
            alpha = 0.1
            for i in range(min(4, len(features))):
                if i < len(profile.mouse_movement.velocity_profile):
                    profile.mouse_movement.velocity_profile[i] = (
                        alpha * features[i] + (1 - alpha) * profile.mouse_movement.velocity_profile[i]
                    )
    
    def _update_list_ema(self, old_list: List[float], new_list: List[float], alpha: float) -> List[float]:
        """Update list using exponential moving average"""
        if not old_list:
            return new_list[:10]  # Limit to 10 most recent values
        
        # Take average of new values and update with EMA
        if new_list:
            new_avg = statistics.mean(new_list)
            old_avg = statistics.mean(old_list)
            updated_avg = alpha * new_avg + (1 - alpha) * old_avg
            
            # Return updated list with new average
            return [updated_avg] * min(len(old_list), 10)
        
        return old_list
    
    async def authenticate_user(
        self,
        user_id: str,
        behavioral_samples: List[BehavioralSample]
    ) -> AuthenticationAttempt:
        """Perform behavioral authentication"""
        if user_id not in self.user_profiles:
            # New user - create profile but require traditional authentication
            await self.create_user_profile(user_id)
            
            attempt = AuthenticationAttempt(
                attempt_id=f"auth_{secrets.token_hex(8)}",
                user_id=user_id,
                timestamp=datetime.now(),
                behavioral_samples=behavioral_samples,
                confidence_scores={},
                overall_confidence=0.0,
                decision=AuthenticationDecision.CHALLENGE,
                threat_level=ThreatLevel.MEDIUM,
                additional_context={"reason": "new_user_no_profile"}
            )
            
            self.authentication_history.append(attempt)
            return attempt
        
        profile = self.user_profiles[user_id]
        confidence_scores = {}
        
        # Analyze each behavioral sample
        for sample in behavioral_samples:
            if sample.metric_type in self.analyzers:
                analyzer = self.analyzers[sample.metric_type]
                
                # Calculate confidence based on similarity to profile
                if sample.metric_type == BehavioralMetric.TYPING_DYNAMICS and profile.typing_dynamics:
                    anomaly_score = await analyzer.detect_anomaly(sample.processed_features, profile.typing_dynamics)
                    confidence = 1.0 - anomaly_score
                elif sample.metric_type == BehavioralMetric.MOUSE_MOVEMENT and profile.mouse_movement:
                    anomaly_score = await analyzer.detect_anomaly(sample.processed_features, profile.mouse_movement)
                    confidence = 1.0 - anomaly_score
                else:
                    confidence = 0.5  # Neutral confidence if no baseline
                
                confidence_scores[sample.metric_type] = max(0.0, min(1.0, confidence))
        
        # Calculate overall confidence
        overall_confidence = statistics.mean(confidence_scores.values()) if confidence_scores else 0.0
        
        # Make authentication decision
        if overall_confidence >= self.confidence_threshold:
            decision = AuthenticationDecision.ALLOW
            threat_level = ThreatLevel.LOW
        elif overall_confidence >= self.confidence_threshold * 0.7:
            decision = AuthenticationDecision.CHALLENGE
            threat_level = ThreatLevel.MEDIUM
        else:
            decision = AuthenticationDecision.DENY
            threat_level = ThreatLevel.HIGH
        
        # Check for anomalies
        await self._check_for_anomalies(user_id, behavioral_samples, confidence_scores)
        
        attempt = AuthenticationAttempt(
            attempt_id=f"auth_{secrets.token_hex(8)}",
            user_id=user_id,
            timestamp=datetime.now(),
            behavioral_samples=behavioral_samples,
            confidence_scores=confidence_scores,
            overall_confidence=overall_confidence,
            decision=decision,
            threat_level=threat_level,
            additional_context={"profile_age_days": (datetime.now() - profile.created_at).days}
        )
        
        self.authentication_history.append(attempt)
        return attempt
    
    async def _check_for_anomalies(
        self,
        user_id: str,
        samples: List[BehavioralSample],
        confidence_scores: Dict[BehavioralMetric, float]
    ):
        """Check for behavioral anomalies and log them"""
        for sample in samples:
            confidence = confidence_scores.get(sample.metric_type, 0.5)
            
            if confidence < 0.3:  # Low confidence indicates potential anomaly
                anomaly_score = 1.0 - confidence
                
                anomaly = AnomalyDetection(
                    anomaly_id=f"anomaly_{secrets.token_hex(8)}",
                    user_id=user_id,
                    detected_at=datetime.now(),
                    metric_type=sample.metric_type,
                    anomaly_score=anomaly_score,
                    deviation_details={"confidence": confidence, "sample_id": sample.sample_id},
                    possible_causes=self._analyze_possible_causes(sample, confidence),
                    risk_assessment=self._assess_risk_level(anomaly_score)
                )
                
                self.anomaly_detections.append(anomaly)
    
    def _analyze_possible_causes(self, sample: BehavioralSample, confidence: float) -> List[str]:
        """Analyze possible causes for behavioral anomalies"""
        causes = []
        
        if confidence < 0.1:
            causes.append("potential_imposter")
        elif confidence < 0.3:
            causes.extend(["stress", "fatigue", "injury"])
        
        # Context-based analysis
        context = sample.context
        if context.get("device_type") != "usual_device":
            causes.append("different_device")
        
        if context.get("time_of_day") not in ["morning", "afternoon"]:
            causes.append("unusual_time")
        
        return causes
    
    def _assess_risk_level(self, anomaly_score: float) -> ThreatLevel:
        """Assess risk level based on anomaly score"""
        if anomaly_score >= 0.9:
            return ThreatLevel.CRITICAL
        elif anomaly_score >= 0.7:
            return ThreatLevel.HIGH
        elif anomaly_score >= 0.4:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW
    
    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get behavioral statistics for user"""
        if user_id not in self.user_profiles:
            return {}
        
        profile = self.user_profiles[user_id]
        user_attempts = [a for a in self.authentication_history if a.user_id == user_id]
        user_anomalies = [a for a in self.anomaly_detections if a.user_id == user_id]
        
        # Calculate success rate
        successful_attempts = len([a for a in user_attempts if a.decision == AuthenticationDecision.ALLOW])
        success_rate = successful_attempts / len(user_attempts) if user_attempts else 0
        
        # Average confidence
        avg_confidence = statistics.mean([a.overall_confidence for a in user_attempts]) if user_attempts else 0
        
        return {
            "profile_age_days": (datetime.now() - profile.created_at).days,
            "total_samples": profile.sample_count,
            "authentication_attempts": len(user_attempts),
            "success_rate": success_rate,
            "average_confidence": avg_confidence,
            "anomaly_count": len(user_anomalies),
            "last_authentication": user_attempts[-1].timestamp.isoformat() if user_attempts else None,
            "behavioral_metrics": {
                "typing_dynamics": profile.typing_dynamics is not None,
                "mouse_movement": profile.mouse_movement is not None,
                "touch_patterns": profile.touch_patterns is not None,
                "voice_characteristics": profile.voice_characteristics is not None
            }
        }

def create_behavioral_authentication_system(confidence_threshold: float = 0.7) -> BehavioralAuthenticationSystem:
    """Factory function to create behavioral authentication system"""
    return BehavioralAuthenticationSystem(confidence_threshold)

# Example usage
async def example_usage():
    """Example of using behavioral authentication"""
    
    # Create authentication system
    auth_system = create_behavioral_authentication_system(confidence_threshold=0.75)
    
    # Create user profile
    user_id = "user_123"
    profile = await auth_system.create_user_profile(user_id)
    print(f"Created profile for user: {user_id}")
    
    # Simulate typing dynamics sample
    typing_sample = await auth_system.collect_behavioral_sample(
        user_id=user_id,
        metric_type=BehavioralMetric.TYPING_DYNAMICS,
        raw_data={
            "keystrokes": [
                {"key": "h", "press_time": 1000, "release_time": 1050, "pressure": 0.5},
                {"key": "e", "press_time": 1080, "release_time": 1120, "pressure": 0.6},
                {"key": "l", "press_time": 1150, "release_time": 1190, "pressure": 0.4},
                {"key": "l", "press_time": 1200, "release_time": 1240, "pressure": 0.5},
                {"key": "o", "press_time": 1270, "release_time": 1310, "pressure": 0.7}
            ]
        },
        context={"device_type": "usual_device", "time_of_day": "morning"}
    )
    
    # Simulate mouse movement sample
    mouse_sample = await auth_system.collect_behavioral_sample(
        user_id=user_id,
        metric_type=BehavioralMetric.MOUSE_MOVEMENT,
        raw_data={
            "movements": [
                {"x": 100, "y": 100, "timestamp": 2000},
                {"x": 150, "y": 120, "timestamp": 2050},
                {"x": 200, "y": 150, "timestamp": 2100},
                {"x": 250, "y": 180, "timestamp": 2150}
            ],
            "clicks": [
                {"x": 250, "y": 180, "timestamp": 2200, "button": "left"}
            ]
        },
        context={"device_type": "usual_device"}
    )
    
    print(f"Collected typing sample: {typing_sample.sample_id}")
    print(f"Collected mouse sample: {mouse_sample.sample_id}")
    
    # Simulate additional training samples
    for i in range(5):
        await auth_system.collect_behavioral_sample(
            user_id=user_id,
            metric_type=BehavioralMetric.TYPING_DYNAMICS,
            raw_data={
                "keystrokes": [
                    {"key": f"k{j}", "press_time": 3000 + j*100, "release_time": 3040 + j*100, "pressure": 0.5 + j*0.1}
                    for j in range(5)
                ]
            },
            context={"device_type": "usual_device"}
        )
    
    print(f"Profile updated with {auth_system.user_profiles[user_id].sample_count} samples")
    
    # Perform authentication
    auth_samples = [
        await auth_system.collect_behavioral_sample(
            user_id=user_id,
            metric_type=BehavioralMetric.TYPING_DYNAMICS,
            raw_data={
                "keystrokes": [
                    {"key": "t", "press_time": 4000, "release_time": 4045, "pressure": 0.5},
                    {"key": "e", "press_time": 4070, "release_time": 4115, "pressure": 0.6},
                    {"key": "s", "press_time": 4140, "release_time": 4180, "pressure": 0.4},
                    {"key": "t", "press_time": 4200, "release_time": 4240, "pressure": 0.5}
                ]
            },
            context={"device_type": "usual_device"}
        )
    ]
    
    auth_attempt = await auth_system.authenticate_user(user_id, auth_samples)
    
    print(f"\nAuthentication Result:")
    print(f"  Attempt ID: {auth_attempt.attempt_id}")
    print(f"  Decision: {auth_attempt.decision.value}")
    print(f"  Overall Confidence: {auth_attempt.overall_confidence:.3f}")
    print(f"  Threat Level: {auth_attempt.threat_level.value}")
    print(f"  Confidence Scores:")
    for metric, score in auth_attempt.confidence_scores.items():
        print(f"    {metric.value}: {score:.3f}")
    
    # Get user statistics
    stats = await auth_system.get_user_statistics(user_id)
    print(f"\nUser Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    asyncio.run(example_usage())