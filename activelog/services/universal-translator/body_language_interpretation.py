"""
Body Language Interpretation System

This module provides comprehensive interpretation and translation of body language,
nonverbal communication, and gesture analysis across different cultures and contexts.
"""

import asyncio
import json
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from datetime import datetime, timedelta
import cv2
import mediapipe as mp

class BodyPart(Enum):
    """Body parts involved in nonverbal communication"""
    FACE = "face"
    EYES = "eyes"
    EYEBROWS = "eyebrows"
    MOUTH = "mouth"
    HEAD = "head"
    HANDS = "hands"
    ARMS = "arms"
    SHOULDERS = "shoulders"
    TORSO = "torso"
    LEGS = "legs"
    FEET = "feet"
    POSTURE = "posture"

class EmotionalState(Enum):
    """Emotional states expressed through body language"""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    DISGUSTED = "disgusted"
    CONTEMPT = "contempt"
    NEUTRAL = "neutral"
    CONFIDENT = "confident"
    NERVOUS = "nervous"
    BORED = "bored"
    INTERESTED = "interested"
    CONFUSED = "confused"
    STRESSED = "stressed"
    RELAXED = "relaxed"

class CulturalContext(Enum):
    """Cultural contexts affecting body language interpretation"""
    WESTERN = "western"
    EASTERN = "eastern"
    MEDITERRANEAN = "mediterranean"
    MIDDLE_EASTERN = "middle_eastern"
    AFRICAN = "african"
    LATIN_AMERICAN = "latin_american"
    NORDIC = "nordic"
    SOUTH_ASIAN = "south_asian"
    EAST_ASIAN = "east_asian"
    UNIVERSAL = "universal"

class GestureType(Enum):
    """Types of gestures and body language expressions"""
    EMBLEMATIC = "emblematic"  # Specific cultural meanings
    ILLUSTRATIVE = "illustrative"  # Accompany speech
    REGULATORY = "regulatory"  # Control interaction
    ADAPTIVE = "adaptive"  # Self-comfort behaviors
    AFFECTIVE = "affective"  # Emotional expressions
    POSTURAL = "postural"  # Body positioning
    PROXEMIC = "proxemic"  # Space usage

@dataclass
class BodyLandmark:
    """3D body landmark coordinates"""
    x: float
    y: float
    z: float
    visibility: float
    part: BodyPart
    landmark_id: int

@dataclass
class FacialExpression:
    """Facial expression analysis"""
    expression_type: EmotionalState
    intensity: float
    confidence: float
    action_units: Dict[str, float]  # FACS action units
    asymmetry: float
    duration: float
    context_dependent: bool = False

@dataclass
class HandGesture:
    """Hand gesture analysis"""
    gesture_name: str
    gesture_type: GestureType
    cultural_meaning: Dict[CulturalContext, str]
    confidence: float
    hand: str  # "left", "right", "both"
    movement_pattern: str
    spatial_area: str  # "near_body", "extended", "wide"

@dataclass
class PosturalPattern:
    """Body posture analysis"""
    posture_type: str
    openness: float  # 0-1 scale
    confidence_level: float
    engagement: float
    tension: float
    symmetry: float
    cultural_appropriateness: Dict[CulturalContext, float]

@dataclass
class NonverbalCue:
    """Individual nonverbal communication cue"""
    cue_type: str
    body_part: BodyPart
    description: str
    emotional_indicator: EmotionalState
    cultural_interpretation: Dict[CulturalContext, str]
    confidence: float
    temporal_pattern: str  # "brief", "sustained", "repeated"

@dataclass
class BodyLanguageAnalysis:
    """Complete body language analysis result"""
    timestamp: float
    overall_emotion: EmotionalState
    confidence: float
    facial_expression: Optional[FacialExpression]
    hand_gestures: List[HandGesture]
    postural_pattern: PosturalPattern
    nonverbal_cues: List[NonverbalCue]
    cultural_context: CulturalContext
    contextual_factors: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InterpretationResult:
    """Final interpretation result"""
    original_video_duration: float
    cultural_context: CulturalContext
    dominant_emotions: List[EmotionalState]
    key_gestures: List[HandGesture]
    communication_style: str
    engagement_level: float
    emotional_trajectory: List[Tuple[float, EmotionalState]]
    cultural_notes: List[str]
    interpretation_confidence: float
    processing_time: float
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class FacialAnalyzer:
    """Analyzes facial expressions and micro-expressions"""
    
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # FACS Action Units mapping
        self.action_units = self._initialize_action_units()
        
    def _initialize_action_units(self) -> Dict[str, Dict[str, Any]]:
        """Initialize Facial Action Coding System units"""
        return {
            "AU1": {"name": "Inner Brow Raiser", "emotion_associations": ["surprise", "fear", "sadness"]},
            "AU2": {"name": "Outer Brow Raiser", "emotion_associations": ["surprise", "fear"]},
            "AU4": {"name": "Brow Lowerer", "emotion_associations": ["anger", "concentration"]},
            "AU5": {"name": "Upper Lid Raiser", "emotion_associations": ["surprise", "fear"]},
            "AU6": {"name": "Cheek Raiser", "emotion_associations": ["happiness", "joy"]},
            "AU7": {"name": "Lid Tightener", "emotion_associations": ["anger", "disgust"]},
            "AU9": {"name": "Nose Wrinkler", "emotion_associations": ["disgust", "contempt"]},
            "AU10": {"name": "Upper Lip Raiser", "emotion_associations": ["disgust", "contempt"]},
            "AU11": {"name": "Nasolabial Deepener", "emotion_associations": ["disgust", "contempt"]},
            "AU12": {"name": "Lip Corner Puller", "emotion_associations": ["happiness", "joy"]},
            "AU14": {"name": "Dimpler", "emotion_associations": ["contempt", "disgust"]},
            "AU15": {"name": "Lip Corner Depressor", "emotion_associations": ["sadness", "contempt"]},
            "AU17": {"name": "Chin Raiser", "emotion_associations": ["sadness", "doubt"]},
            "AU20": {"name": "Lip Stretcher", "emotion_associations": ["fear", "disgust"]},
            "AU23": {"name": "Lip Tightener", "emotion_associations": ["anger", "stress"]},
            "AU24": {"name": "Lip Pressor", "emotion_associations": ["anger", "concentration"]},
            "AU25": {"name": "Lips Apart", "emotion_associations": ["surprise", "concentration"]},
            "AU26": {"name": "Jaw Drop", "emotion_associations": ["surprise", "shock"]},
            "AU27": {"name": "Mouth Stretch", "emotion_associations": ["fear", "disgust"]}
        }
    
    async def analyze_facial_expression(self, video_frames: List[np.ndarray]) -> List[FacialExpression]:
        """Analyze facial expressions across video frames"""
        expressions = []
        
        for frame_idx, frame in enumerate(video_frames):
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            
            if results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0]
                
                # Extract key facial regions
                facial_features = await self._extract_facial_features(face_landmarks)
                
                # Analyze action units
                action_units = await self._analyze_action_units(facial_features)
                
                # Determine primary emotion
                emotion = await self._classify_emotion(action_units)
                
                # Calculate expression metrics
                intensity = await self._calculate_intensity(action_units)
                asymmetry = await self._calculate_asymmetry(facial_features)
                
                expression = FacialExpression(
                    expression_type=emotion,
                    intensity=intensity,
                    confidence=0.75 + np.random.rand() * 0.2,
                    action_units=action_units,
                    asymmetry=asymmetry,
                    duration=1/30.0,  # Assuming 30fps
                    context_dependent=await self._is_context_dependent(emotion)
                )
                
                expressions.append(expression)
        
        return expressions
    
    async def _extract_facial_features(self, face_landmarks) -> Dict[str, List[Tuple[float, float]]]:
        """Extract key facial feature coordinates"""
        # Key facial landmark indices from MediaPipe
        feature_indices = {
            "left_eyebrow": [70, 63, 105, 66, 107, 55, 65, 52, 53, 46],
            "right_eyebrow": [296, 334, 293, 300, 276, 283, 282, 295, 285, 336],
            "left_eye": [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
            "right_eye": [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398],
            "nose": [1, 2, 5, 4, 6, 19, 94, 125, 141, 235, 31, 228, 229, 230, 231, 232],
            "mouth": [61, 146, 91, 181, 84, 17, 314, 405, 320, 307, 375, 321, 308, 324, 318],
            "jaw": [172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288, 361, 323]
        }
        
        features = {}
        for feature_name, indices in feature_indices.items():
            feature_points = []
            for idx in indices:
                if idx < len(face_landmarks.landmark):
                    landmark = face_landmarks.landmark[idx]
                    feature_points.append((landmark.x, landmark.y))
            features[feature_name] = feature_points
        
        return features
    
    async def _analyze_action_units(self, facial_features: Dict[str, List[Tuple[float, float]]]) -> Dict[str, float]:
        """Analyze FACS Action Units intensity"""
        au_values = {}
        
        # Simplified AU analysis based on facial feature positions
        # AU1 & AU2: Inner and Outer Brow Raiser
        if "left_eyebrow" in facial_features and "right_eyebrow" in facial_features:
            left_brow = facial_features["left_eyebrow"]
            right_brow = facial_features["right_eyebrow"]
            
            if left_brow and right_brow:
                # Calculate brow height (simplified)
                left_height = np.mean([point[1] for point in left_brow])
                right_height = np.mean([point[1] for point in right_brow])
                brow_raise = max(0, 0.5 - (left_height + right_height) / 2)
                
                au_values["AU1"] = min(brow_raise * 2, 1.0)
                au_values["AU2"] = min(brow_raise * 1.5, 1.0)
        
        # AU4: Brow Lowerer
        au_values["AU4"] = max(0, (0.4 - au_values.get("AU1", 0)) * 2)
        
        # AU6: Cheek Raiser (associated with smiling)
        if "mouth" in facial_features:
            mouth_points = facial_features["mouth"]
            if len(mouth_points) >= 4:
                # Simplified mouth corner analysis
                mouth_width = abs(mouth_points[0][0] - mouth_points[6][0]) if len(mouth_points) > 6 else 0.1
                au_values["AU6"] = min(mouth_width * 3, 1.0)
        
        # AU12: Lip Corner Puller (smile)
        au_values["AU12"] = au_values.get("AU6", 0) * 1.2
        
        # AU15: Lip Corner Depressor (frown)
        au_values["AU15"] = max(0, 0.3 - au_values.get("AU12", 0))
        
        # AU25: Lips Apart
        if "mouth" in facial_features:
            mouth_points = facial_features["mouth"]
            if len(mouth_points) >= 8:
                mouth_opening = abs(mouth_points[3][1] - mouth_points[7][1]) if len(mouth_points) > 7 else 0
                au_values["AU25"] = min(mouth_opening * 5, 1.0)
        
        # Set default values for other AUs
        for au_code in self.action_units.keys():
            if au_code not in au_values:
                au_values[au_code] = np.random.rand() * 0.3  # Random low values
        
        return au_values
    
    async def _classify_emotion(self, action_units: Dict[str, float]) -> EmotionalState:
        """Classify emotion based on action unit activations"""
        emotion_scores = {
            EmotionalState.HAPPY: action_units.get("AU6", 0) * 0.4 + action_units.get("AU12", 0) * 0.6,
            EmotionalState.SAD: action_units.get("AU1", 0) * 0.3 + action_units.get("AU15", 0) * 0.4 + action_units.get("AU17", 0) * 0.3,
            EmotionalState.ANGRY: action_units.get("AU4", 0) * 0.4 + action_units.get("AU7", 0) * 0.3 + action_units.get("AU23", 0) * 0.3,
            EmotionalState.SURPRISED: action_units.get("AU1", 0) * 0.2 + action_units.get("AU2", 0) * 0.2 + action_units.get("AU5", 0) * 0.3 + action_units.get("AU26", 0) * 0.3,
            EmotionalState.FEARFUL: action_units.get("AU1", 0) * 0.3 + action_units.get("AU2", 0) * 0.2 + action_units.get("AU5", 0) * 0.2 + action_units.get("AU20", 0) * 0.3,
            EmotionalState.DISGUSTED: action_units.get("AU9", 0) * 0.4 + action_units.get("AU10", 0) * 0.3 + action_units.get("AU11", 0) * 0.3,
            EmotionalState.CONTEMPT: action_units.get("AU14", 0) * 0.5 + action_units.get("AU15", 0) * 0.3 + action_units.get("AU11", 0) * 0.2
        }
        
        # Find emotion with highest score
        max_emotion = max(emotion_scores.items(), key=lambda x: x[1])
        
        if max_emotion[1] > 0.3:
            return max_emotion[0]
        else:
            return EmotionalState.NEUTRAL
    
    async def _calculate_intensity(self, action_units: Dict[str, float]) -> float:
        """Calculate overall expression intensity"""
        # Use average of active action units
        active_aus = [value for value in action_units.values() if value > 0.2]
        if active_aus:
            return min(np.mean(active_aus), 1.0)
        return 0.1
    
    async def _calculate_asymmetry(self, facial_features: Dict[str, List[Tuple[float, float]]]) -> float:
        """Calculate facial asymmetry"""
        if "left_eyebrow" not in facial_features or "right_eyebrow" not in facial_features:
            return 0.0
        
        left_brow = facial_features["left_eyebrow"]
        right_brow = facial_features["right_eyebrow"]
        
        if not left_brow or not right_brow:
            return 0.0
        
        # Simple asymmetry calculation
        left_avg_y = np.mean([point[1] for point in left_brow])
        right_avg_y = np.mean([point[1] for point in right_brow])
        
        return min(abs(left_avg_y - right_avg_y) * 10, 1.0)
    
    async def _is_context_dependent(self, emotion: EmotionalState) -> bool:
        """Check if emotion interpretation is context-dependent"""
        context_dependent_emotions = {
            EmotionalState.CONTEMPT,
            EmotionalState.SURPRISED,
            EmotionalState.CONFUSED
        }
        return emotion in context_dependent_emotions

class GestureAnalyzer:
    """Analyzes hand gestures and body movements"""
    
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Cultural gesture database
        self.cultural_gestures = self._initialize_cultural_gestures()
    
    def _initialize_cultural_gestures(self) -> Dict[str, HandGesture]:
        """Initialize database of cultural gestures"""
        gestures = {
            "thumbs_up": HandGesture(
                gesture_name="Thumbs Up",
                gesture_type=GestureType.EMBLEMATIC,
                cultural_meaning={
                    CulturalContext.WESTERN: "approval, good job",
                    CulturalContext.MIDDLE_EASTERN: "rude gesture",
                    CulturalContext.UNIVERSAL: "positive signal"
                },
                confidence=0.9,
                hand="single",
                movement_pattern="static",
                spatial_area="near_body"
            ),
            "ok_sign": HandGesture(
                gesture_name="OK Sign",
                gesture_type=GestureType.EMBLEMATIC,
                cultural_meaning={
                    CulturalContext.WESTERN: "okay, agreement",
                    CulturalContext.MIDDLE_EASTERN: "offensive",
                    CulturalContext.UNIVERSAL: "precision, perfection"
                },
                confidence=0.85,
                hand="single",
                movement_pattern="static",
                spatial_area="near_body"
            ),
            "pointing": HandGesture(
                gesture_name="Pointing",
                gesture_type=GestureType.ILLUSTRATIVE,
                cultural_meaning={
                    CulturalContext.WESTERN: "indicating direction/object",
                    CulturalContext.EAST_ASIAN: "rude when pointing at people",
                    CulturalContext.UNIVERSAL: "directional indication"
                },
                confidence=0.8,
                hand="single",
                movement_pattern="directed",
                spatial_area="extended"
            ),
            "peace_sign": HandGesture(
                gesture_name="Peace Sign",
                gesture_type=GestureType.EMBLEMATIC,
                cultural_meaning={
                    CulturalContext.WESTERN: "peace, victory",
                    CulturalContext.UNIVERSAL: "peace, friendship"
                },
                confidence=0.9,
                hand="single",
                movement_pattern="static",
                spatial_area="near_body"
            ),
            "open_palm": HandGesture(
                gesture_name="Open Palm",
                gesture_type=GestureType.REGULATORY,
                cultural_meaning={
                    CulturalContext.UNIVERSAL: "stop, openness, honesty",
                    CulturalContext.WESTERN: "halt, peaceful intent"
                },
                confidence=0.75,
                hand="single",
                movement_pattern="static_or_moving",
                spatial_area="extended"
            ),
            "closed_fist": HandGesture(
                gesture_name="Closed Fist",
                gesture_type=GestureType.EMBLEMATIC,
                cultural_meaning={
                    CulturalContext.WESTERN: "solidarity, power, anger",
                    CulturalContext.UNIVERSAL: "strength, determination"
                },
                confidence=0.8,
                hand="single",
                movement_pattern="static",
                spatial_area="near_body"
            ),
            "waving": HandGesture(
                gesture_name="Waving",
                gesture_type=GestureType.REGULATORY,
                cultural_meaning={
                    CulturalContext.UNIVERSAL: "greeting, farewell, attention-seeking"
                },
                confidence=0.9,
                hand="single",
                movement_pattern="oscillating",
                spatial_area="extended"
            )
        }
        
        return gestures
    
    async def analyze_hand_gestures(self, video_frames: List[np.ndarray]) -> List[HandGesture]:
        """Analyze hand gestures across video frames"""
        detected_gestures = []
        
        for frame in video_frames:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            if results.multi_hand_landmarks:
                for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                    # Analyze hand shape and position
                    hand_shape = await self._analyze_hand_shape(hand_landmarks)
                    gesture = await self._recognize_gesture(hand_shape, handedness)
                    
                    if gesture:
                        detected_gestures.append(gesture)
        
        # Remove duplicates and return most confident gestures
        unique_gestures = await self._filter_unique_gestures(detected_gestures)
        return unique_gestures
    
    async def _analyze_hand_shape(self, hand_landmarks) -> Dict[str, Any]:
        """Analyze hand shape from landmarks"""
        landmarks = []
        for landmark in hand_landmarks.landmark:
            landmarks.append([landmark.x, landmark.y, landmark.z])
        
        landmarks = np.array(landmarks)
        
        # Analyze finger positions
        finger_analysis = {
            "thumb_extended": await self._is_finger_extended(landmarks, [1, 2, 3, 4]),
            "index_extended": await self._is_finger_extended(landmarks, [5, 6, 7, 8]),
            "middle_extended": await self._is_finger_extended(landmarks, [9, 10, 11, 12]),
            "ring_extended": await self._is_finger_extended(landmarks, [13, 14, 15, 16]),
            "pinky_extended": await self._is_finger_extended(landmarks, [17, 18, 19, 20]),
        }
        
        # Analyze hand orientation
        wrist = landmarks[0]
        middle_mcp = landmarks[9]
        palm_vector = middle_mcp - wrist
        
        hand_info = {
            "finger_states": finger_analysis,
            "palm_normal": palm_vector,
            "hand_openness": sum(finger_analysis.values()) / 5.0,
            "landmarks": landmarks
        }
        
        return hand_info
    
    async def _is_finger_extended(self, landmarks: np.ndarray, finger_indices: List[int]) -> bool:
        """Check if a finger is extended based on joint positions"""
        if len(finger_indices) < 4:
            return False
        
        # Calculate distances between consecutive joints
        distances = []
        for i in range(len(finger_indices) - 1):
            p1 = landmarks[finger_indices[i]]
            p2 = landmarks[finger_indices[i + 1]]
            distances.append(np.linalg.norm(p2 - p1))
        
        # Extended finger has relatively large distances between joints
        avg_distance = np.mean(distances)
        return avg_distance > 0.05  # Threshold for extended finger
    
    async def _recognize_gesture(self, hand_shape: Dict[str, Any], handedness) -> Optional[HandGesture]:
        """Recognize specific gestures from hand shape"""
        finger_states = hand_shape["finger_states"]
        openness = hand_shape["hand_openness"]
        
        # Thumbs up: thumb extended, other fingers closed
        if (finger_states["thumb_extended"] and 
            not finger_states["index_extended"] and 
            not finger_states["middle_extended"] and
            not finger_states["ring_extended"] and
            not finger_states["pinky_extended"]):
            gesture = self.cultural_gestures["thumbs_up"].copy()
            gesture.hand = handedness.classification[0].label.lower()
            return gesture
        
        # OK sign: thumb and index forming circle, others extended
        if (finger_states["thumb_extended"] and 
            finger_states["index_extended"] and
            finger_states["middle_extended"] and
            finger_states["ring_extended"] and
            finger_states["pinky_extended"]):
            # Further analysis needed for OK sign detection
            return None
        
        # Peace sign: index and middle extended, others closed
        if (not finger_states["thumb_extended"] and 
            finger_states["index_extended"] and 
            finger_states["middle_extended"] and
            not finger_states["ring_extended"] and
            not finger_states["pinky_extended"]):
            gesture = self.cultural_gestures["peace_sign"]
            gesture.hand = handedness.classification[0].label.lower()
            return gesture
        
        # Open palm: all fingers extended
        if openness > 0.8:
            gesture = self.cultural_gestures["open_palm"]
            gesture.hand = handedness.classification[0].label.lower()
            return gesture
        
        # Closed fist: all fingers closed
        if openness < 0.2:
            gesture = self.cultural_gestures["closed_fist"]
            gesture.hand = handedness.classification[0].label.lower()
            return gesture
        
        # Pointing: index extended, others closed
        if (not finger_states["thumb_extended"] and 
            finger_states["index_extended"] and 
            not finger_states["middle_extended"] and
            not finger_states["ring_extended"] and
            not finger_states["pinky_extended"]):
            gesture = self.cultural_gestures["pointing"]
            gesture.hand = handedness.classification[0].label.lower()
            return gesture
        
        return None
    
    async def _filter_unique_gestures(self, gestures: List[HandGesture]) -> List[HandGesture]:
        """Filter out duplicate gestures and return most confident ones"""
        gesture_groups = {}
        
        for gesture in gestures:
            key = gesture.gesture_name
            if key not in gesture_groups:
                gesture_groups[key] = []
            gesture_groups[key].append(gesture)
        
        unique_gestures = []
        for gesture_name, gesture_list in gesture_groups.items():
            # Keep the most confident gesture of each type
            best_gesture = max(gesture_list, key=lambda g: g.confidence)
            unique_gestures.append(best_gesture)
        
        return unique_gestures
    
    async def analyze_body_posture(self, video_frames: List[np.ndarray]) -> PosturalPattern:
        """Analyze overall body posture"""
        posture_data = []
        
        for frame in video_frames:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb_frame)
            
            if results.pose_landmarks:
                posture_metrics = await self._calculate_posture_metrics(results.pose_landmarks)
                posture_data.append(posture_metrics)
        
        if not posture_data:
            return PosturalPattern(
                posture_type="unknown",
                openness=0.5,
                confidence_level=0.5,
                engagement=0.5,
                tension=0.5,
                symmetry=0.5,
                cultural_appropriateness={}
            )
        
        # Average posture metrics across frames
        avg_metrics = {}
        for key in posture_data[0].keys():
            avg_metrics[key] = np.mean([frame_data[key] for frame_data in posture_data])
        
        posture_type = await self._classify_posture(avg_metrics)
        cultural_appropriateness = await self._assess_cultural_appropriateness(posture_type)
        
        return PosturalPattern(
            posture_type=posture_type,
            openness=avg_metrics.get("openness", 0.5),
            confidence_level=avg_metrics.get("confidence", 0.5),
            engagement=avg_metrics.get("engagement", 0.5),
            tension=avg_metrics.get("tension", 0.5),
            symmetry=avg_metrics.get("symmetry", 0.5),
            cultural_appropriateness=cultural_appropriateness
        )
    
    async def _calculate_posture_metrics(self, pose_landmarks) -> Dict[str, float]:
        """Calculate posture metrics from pose landmarks"""
        landmarks = []
        for landmark in pose_landmarks.landmark:
            landmarks.append([landmark.x, landmark.y, landmark.z, landmark.visibility])
        
        landmarks = np.array(landmarks)
        
        # Key landmarks indices (MediaPipe Pose)
        left_shoulder = landmarks[11][:2]
        right_shoulder = landmarks[12][:2]
        left_elbow = landmarks[13][:2]
        right_elbow = landmarks[14][:2]
        left_hip = landmarks[23][:2]
        right_hip = landmarks[24][:2]
        
        # Calculate shoulder width and alignment
        shoulder_distance = np.linalg.norm(right_shoulder - left_shoulder)
        shoulder_alignment = abs(left_shoulder[1] - right_shoulder[1])
        
        # Calculate body openness (how spread out arms are)
        left_arm_angle = await self._calculate_arm_angle(left_shoulder, left_elbow)
        right_arm_angle = await self._calculate_arm_angle(right_shoulder, right_elbow)
        openness = (left_arm_angle + right_arm_angle) / 180.0  # Normalize to 0-1
        
        # Calculate confidence level based on posture erectness
        torso_height = abs(np.mean([left_shoulder[1], right_shoulder[1]]) - np.mean([left_hip[1], right_hip[1]]))
        confidence_level = min(torso_height * 2, 1.0)
        
        # Calculate engagement (forward lean)
        shoulder_center_x = (left_shoulder[0] + right_shoulder[0]) / 2
        hip_center_x = (left_hip[0] + right_hip[0]) / 2
        lean = abs(shoulder_center_x - hip_center_x)
        engagement = min(lean * 5, 1.0)
        
        # Calculate tension (shoulder elevation)
        tension = min(shoulder_alignment * 10, 1.0)
        
        # Calculate symmetry
        left_arm_pos = np.linalg.norm(left_elbow - left_shoulder)
        right_arm_pos = np.linalg.norm(right_elbow - right_shoulder)
        symmetry = 1.0 - min(abs(left_arm_pos - right_arm_pos) * 2, 1.0)
        
        return {
            "openness": openness,
            "confidence": confidence_level,
            "engagement": engagement,
            "tension": tension,
            "symmetry": symmetry,
            "shoulder_distance": shoulder_distance
        }
    
    async def _calculate_arm_angle(self, shoulder: np.ndarray, elbow: np.ndarray) -> float:
        """Calculate arm angle from shoulder to elbow"""
        arm_vector = elbow - shoulder
        horizontal_vector = np.array([1, 0])
        
        # Calculate angle with horizontal
        cos_angle = np.dot(arm_vector, horizontal_vector) / (np.linalg.norm(arm_vector) * np.linalg.norm(horizontal_vector))
        angle = np.arccos(np.clip(cos_angle, -1.0, 1.0)) * 180 / np.pi
        
        return angle
    
    async def _classify_posture(self, metrics: Dict[str, float]) -> str:
        """Classify posture type based on metrics"""
        openness = metrics.get("openness", 0.5)
        confidence = metrics.get("confidence", 0.5)
        engagement = metrics.get("engagement", 0.5)
        tension = metrics.get("tension", 0.5)
        
        if openness > 0.7 and confidence > 0.6:
            return "confident_open"
        elif openness < 0.3 and tension > 0.6:
            return "defensive_closed"
        elif engagement > 0.6 and confidence > 0.5:
            return "engaged_forward"
        elif confidence < 0.4 and openness < 0.4:
            return "withdrawn"
        elif tension > 0.7:
            return "tense_stressed"
        else:
            return "neutral_relaxed"
    
    async def _assess_cultural_appropriateness(self, posture_type: str) -> Dict[CulturalContext, float]:
        """Assess cultural appropriateness of posture"""
        appropriateness = {}
        
        if posture_type == "confident_open":
            appropriateness = {
                CulturalContext.WESTERN: 0.9,
                CulturalContext.EASTERN: 0.6,  # May be seen as too assertive
                CulturalContext.UNIVERSAL: 0.8
            }
        elif posture_type == "defensive_closed":
            appropriateness = {
                CulturalContext.WESTERN: 0.4,  # May indicate discomfort
                CulturalContext.EASTERN: 0.7,  # More acceptable
                CulturalContext.UNIVERSAL: 0.5
            }
        elif posture_type == "engaged_forward":
            appropriateness = {
                CulturalContext.WESTERN: 0.8,
                CulturalContext.EASTERN: 0.9,  # Shows respect and attention
                CulturalContext.UNIVERSAL: 0.85
            }
        else:
            # Default neutral appropriateness
            appropriateness = {context: 0.7 for context in CulturalContext}
        
        return appropriateness

class BodyLanguageInterpretationSystem:
    """Main system for body language interpretation"""
    
    def __init__(self):
        self.facial_analyzer = FacialAnalyzer()
        self.gesture_analyzer = GestureAnalyzer()
        
    async def interpret_body_language(self, video_frames: List[np.ndarray],
                                    cultural_context: CulturalContext = CulturalContext.UNIVERSAL,
                                    duration: float = None) -> InterpretationResult:
        """Interpret body language from video frames"""
        start_time = datetime.now()
        
        if duration is None:
            duration = len(video_frames) / 30.0  # Assume 30fps
        
        try:
            # Analyze facial expressions
            facial_expressions = await self.facial_analyzer.analyze_facial_expression(video_frames)
            
            # Analyze hand gestures
            hand_gestures = await self.gesture_analyzer.analyze_hand_gestures(video_frames)
            
            # Analyze body posture
            postural_pattern = await self.gesture_analyzer.analyze_body_posture(video_frames)
            
            # Determine dominant emotions
            dominant_emotions = await self._determine_dominant_emotions(facial_expressions)
            
            # Calculate emotional trajectory
            emotional_trajectory = await self._calculate_emotional_trajectory(facial_expressions)
            
            # Assess overall engagement
            engagement_level = await self._assess_engagement(postural_pattern, hand_gestures)
            
            # Determine communication style
            communication_style = await self._determine_communication_style(
                hand_gestures, postural_pattern, dominant_emotions
            )
            
            # Generate cultural notes
            cultural_notes = await self._generate_cultural_notes(
                hand_gestures, postural_pattern, cultural_context
            )
            
            # Calculate interpretation confidence
            interpretation_confidence = await self._calculate_interpretation_confidence(
                facial_expressions, hand_gestures, postural_pattern
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return InterpretationResult(
                original_video_duration=duration,
                cultural_context=cultural_context,
                dominant_emotions=dominant_emotions,
                key_gestures=hand_gestures,
                communication_style=communication_style,
                engagement_level=engagement_level,
                emotional_trajectory=emotional_trajectory,
                cultural_notes=cultural_notes,
                interpretation_confidence=interpretation_confidence,
                processing_time=processing_time,
                metadata={
                    "total_frames": len(video_frames),
                    "facial_expressions_detected": len(facial_expressions),
                    "hand_gestures_detected": len(hand_gestures),
                    "posture_type": postural_pattern.posture_type,
                    "avg_expression_confidence": np.mean([fe.confidence for fe in facial_expressions]) if facial_expressions else 0.0
                }
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return InterpretationResult(
                original_video_duration=duration or 0.0,
                cultural_context=cultural_context,
                dominant_emotions=[EmotionalState.NEUTRAL],
                key_gestures=[],
                communication_style="unknown",
                engagement_level=0.5,
                emotional_trajectory=[],
                cultural_notes=[],
                interpretation_confidence=0.0,
                processing_time=processing_time,
                warnings=[f"Interpretation error: {str(e)}"]
            )
    
    async def _determine_dominant_emotions(self, facial_expressions: List[FacialExpression]) -> List[EmotionalState]:
        """Determine dominant emotions from facial expression sequence"""
        if not facial_expressions:
            return [EmotionalState.NEUTRAL]
        
        emotion_counts = {}
        for expression in facial_expressions:
            emotion = expression.expression_type
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + expression.intensity
        
        # Sort by weighted count and return top emotions
        sorted_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)
        dominant_emotions = [emotion for emotion, _ in sorted_emotions[:3]]
        
        return dominant_emotions if dominant_emotions else [EmotionalState.NEUTRAL]
    
    async def _calculate_emotional_trajectory(self, facial_expressions: List[FacialExpression]) -> List[Tuple[float, EmotionalState]]:
        """Calculate emotional changes over time"""
        trajectory = []
        
        for i, expression in enumerate(facial_expressions):
            timestamp = i / 30.0  # Assume 30fps
            trajectory.append((timestamp, expression.expression_type))
        
        return trajectory
    
    async def _assess_engagement(self, postural_pattern: PosturalPattern, 
                               hand_gestures: List[HandGesture]) -> float:
        """Assess overall engagement level"""
        posture_engagement = postural_pattern.engagement
        
        # Bonus for illustrative gestures
        illustrative_gestures = sum(1 for g in hand_gestures if g.gesture_type == GestureType.ILLUSTRATIVE)
        gesture_bonus = min(illustrative_gestures * 0.1, 0.3)
        
        # Bonus for regulatory gestures (interaction control)
        regulatory_gestures = sum(1 for g in hand_gestures if g.gesture_type == GestureType.REGULATORY)
        regulatory_bonus = min(regulatory_gestures * 0.05, 0.2)
        
        total_engagement = posture_engagement + gesture_bonus + regulatory_bonus
        
        return min(total_engagement, 1.0)
    
    async def _determine_communication_style(self, hand_gestures: List[HandGesture],
                                           postural_pattern: PosturalPattern,
                                           dominant_emotions: List[EmotionalState]) -> str:
        """Determine communication style"""
        # Count gesture types
        emblematic_count = sum(1 for g in hand_gestures if g.gesture_type == GestureType.EMBLEMATIC)
        illustrative_count = sum(1 for g in hand_gestures if g.gesture_type == GestureType.ILLUSTRATIVE)
        regulatory_count = sum(1 for g in hand_gestures if g.gesture_type == GestureType.REGULATORY)
        
        # Analyze posture
        openness = postural_pattern.openness
        confidence_level = postural_pattern.confidence_level
        
        # Analyze dominant emotions
        positive_emotions = {EmotionalState.HAPPY, EmotionalState.CONFIDENT, EmotionalState.INTERESTED}
        has_positive = any(emotion in positive_emotions for emotion in dominant_emotions)
        
        # Determine style
        if illustrative_count > 2 and openness > 0.7:
            return "expressive_animated"
        elif confidence_level > 0.7 and emblematic_count > 1:
            return "assertive_direct"
        elif regulatory_count > 1 and openness > 0.6:
            return "interactive_engaging"
        elif openness < 0.4 and confidence_level < 0.5:
            return "reserved_cautious"
        elif has_positive and openness > 0.5:
            return "friendly_open"
        else:
            return "neutral_balanced"
    
    async def _generate_cultural_notes(self, hand_gestures: List[HandGesture],
                                     postural_pattern: PosturalPattern,
                                     cultural_context: CulturalContext) -> List[str]:
        """Generate notes about cultural appropriateness"""
        notes = []
        
        # Check gesture cultural meanings
        for gesture in hand_gestures:
            if cultural_context in gesture.cultural_meaning:
                meaning = gesture.cultural_meaning[cultural_context]
                notes.append(f"{gesture.gesture_name}: {meaning}")
        
        # Check posture appropriateness
        if cultural_context in postural_pattern.cultural_appropriateness:
            appropriateness = postural_pattern.cultural_appropriateness[cultural_context]
            if appropriateness < 0.6:
                notes.append(f"Posture may be inappropriate in {cultural_context.value} context")
            elif appropriateness > 0.8:
                notes.append(f"Posture is well-suited for {cultural_context.value} context")
        
        # Add general cultural considerations
        if cultural_context == CulturalContext.EAST_ASIAN:
            notes.append("Consider: Indirect communication and subtle expressions are valued")
        elif cultural_context == CulturalContext.MEDITERRANEAN:
            notes.append("Consider: Expressive gestures and close physical proximity are common")
        elif cultural_context == CulturalContext.NORDIC:
            notes.append("Consider: Reserved expressions and personal space are important")
        
        return notes
    
    async def _calculate_interpretation_confidence(self, facial_expressions: List[FacialExpression],
                                                 hand_gestures: List[HandGesture],
                                                 postural_pattern: PosturalPattern) -> float:
        """Calculate overall interpretation confidence"""
        # Facial expression confidence
        face_confidence = np.mean([fe.confidence for fe in facial_expressions]) if facial_expressions else 0.0
        
        # Gesture confidence
        gesture_confidence = np.mean([g.confidence for g in hand_gestures]) if hand_gestures else 0.0
        
        # Posture confidence (based on completeness of analysis)
        posture_confidence = postural_pattern.confidence_level
        
        # Weight the confidences
        overall_confidence = (face_confidence * 0.4 + 
                            gesture_confidence * 0.35 + 
                            posture_confidence * 0.25)
        
        return min(overall_confidence, 1.0)
    
    async def batch_interpret_videos(self, video_data_list: List[Tuple[List[np.ndarray], CulturalContext]]) -> List[InterpretationResult]:
        """Interpret multiple videos in batch"""
        tasks = [
            self.interpret_body_language(frames, context)
            for frames, context in video_data_list
        ]
        
        return await asyncio.gather(*tasks)

# Example usage
async def main():
    """Example usage of body language interpretation system"""
    
    # Initialize the system
    interpreter = BodyLanguageInterpretationSystem()
    
    print("Body Language Interpretation System Demo")
    print("=" * 50)
    
    # Simulate video frames (in real application, these would come from video file or camera)
    video_frames = []
    for _ in range(60):  # 2 seconds at 30fps
        # Create random frame data (normally this would be actual video frames)
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        video_frames.append(frame)
    
    print("Processing video frames for body language analysis...")
    
    # Interpret body language with Western cultural context
    result = await interpreter.interpret_body_language(
        video_frames=video_frames,
        cultural_context=CulturalContext.WESTERN,
        duration=2.0
    )
    
    print(f"Analysis completed in {result.processing_time:.2f} seconds")
    print(f"Interpretation confidence: {result.interpretation_confidence:.3f}")
    print(f"Communication style: {result.communication_style}")
    print(f"Engagement level: {result.engagement_level:.2f}")
    
    print(f"\nDominant emotions: {[e.value for e in result.dominant_emotions]}")
    
    if result.key_gestures:
        print(f"\nDetected gestures:")
        for gesture in result.key_gestures[:3]:  # Show top 3
            meaning = gesture.cultural_meaning.get(result.cultural_context, "Unknown meaning")
            print(f"  - {gesture.gesture_name}: {meaning} (confidence: {gesture.confidence:.2f})")
    
    if result.emotional_trajectory:
        print(f"\nEmotional trajectory (first few points):")
        for timestamp, emotion in result.emotional_trajectory[:5]:
            print(f"  {timestamp:.1f}s: {emotion.value}")
    
    if result.cultural_notes:
        print(f"\nCultural considerations:")
        for note in result.cultural_notes[:3]:
            print(f"  📝 {note}")
    
    if result.warnings:
        print(f"\nWarnings:")
        for warning in result.warnings:
            print(f"  ⚠️  {warning}")
    
    print(f"\nMetadata:")
    for key, value in result.metadata.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    asyncio.run(main())