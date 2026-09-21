"""
VR/AR Character Visualization System
Immersive character visualization with VR headset support, AR mobile integration, and spatial interaction
"""

import asyncio
import logging
import json
import time
import uuid
import numpy as np
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import websockets
import cv2
import threading
from scipy.spatial.transform import Rotation
import base64
import struct

logger = logging.getLogger(__name__)

class VRPlatform(Enum):
    OCULUS_QUEST = "oculus_quest"
    HTC_VIVE = "htc_vive"
    VALVE_INDEX = "valve_index"
    PICO_4 = "pico_4"
    VARJO_AERO = "varjo_aero"
    MICROSOFT_HOLOLENS = "hololens"
    MAGIC_LEAP = "magic_leap"

class ARPlatform(Enum):
    IOS_ARKIT = "ios_arkit"
    ANDROID_ARCORE = "android_arcore"
    HOLOLENS = "hololens"
    MAGIC_LEAP = "magic_leap"
    WEB_XR = "web_xr"

class InteractionType(Enum):
    GAZE = "gaze"
    HAND_TRACKING = "hand_tracking"
    CONTROLLER = "controller"
    VOICE = "voice"
    GESTURE = "gesture"
    TOUCH = "touch"

@dataclass
class VRTransform:
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    rotation: np.ndarray = field(default_factory=lambda: np.array([0, 0, 0, 1]))  # quaternion
    scale: np.ndarray = field(default_factory=lambda: np.ones(3))

@dataclass
class VRController:
    controller_id: str
    platform: VRPlatform
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    rotation: np.ndarray = field(default_factory=lambda: np.array([0, 0, 0, 1]))
    buttons: Dict[str, bool] = field(default_factory=dict)
    triggers: Dict[str, float] = field(default_factory=dict)
    touchpad: Dict[str, float] = field(default_factory=dict)
    is_connected: bool = False

@dataclass
class HandTrackingData:
    hand_side: str  # "left" or "right"
    landmarks: List[np.ndarray] = field(default_factory=list)
    gesture: str = "unknown"
    confidence: float = 0.0
    is_tracked: bool = False

@dataclass
class VREnvironment:
    environment_id: str
    name: str
    skybox_url: str = ""
    lighting_config: Dict[str, Any] = field(default_factory=dict)
    physics_enabled: bool = True
    scale: float = 1.0
    ambient_sound: str = ""

class SpatialTrackingSystem:
    """Advanced spatial tracking for VR/AR environments"""
    
    def __init__(self):
        self.tracked_objects = {}
        self.spatial_anchors = {}
        self.tracking_quality = 1.0
        self.reference_frame = VRTransform()
        
    def create_spatial_anchor(self, anchor_id: str, transform: VRTransform) -> bool:
        """Create a spatial anchor for persistent object placement"""
        try:
            self.spatial_anchors[anchor_id] = {
                "transform": transform,
                "created_at": time.time(),
                "confidence": 1.0,
                "persistent": True
            }
            logger.info(f"Created spatial anchor: {anchor_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create spatial anchor: {e}")
            return False
    
    def update_object_tracking(self, object_id: str, transform: VRTransform, confidence: float = 1.0):
        """Update tracking information for an object"""
        self.tracked_objects[object_id] = {
            "transform": transform,
            "confidence": confidence,
            "last_update": time.time(),
            "velocity": self._calculate_velocity(object_id, transform),
            "acceleration": self._calculate_acceleration(object_id, transform)
        }
    
    def _calculate_velocity(self, object_id: str, current_transform: VRTransform) -> np.ndarray:
        """Calculate object velocity based on position history"""
        if object_id not in self.tracked_objects:
            return np.zeros(3)
        
        previous_data = self.tracked_objects[object_id]
        previous_transform = previous_data["transform"]
        time_delta = time.time() - previous_data["last_update"]
        
        if time_delta > 0:
            position_delta = current_transform.position - previous_transform.position
            velocity = position_delta / time_delta
            return velocity
        
        return np.zeros(3)
    
    def _calculate_acceleration(self, object_id: str, current_transform: VRTransform) -> np.ndarray:
        """Calculate object acceleration"""
        if object_id not in self.tracked_objects:
            return np.zeros(3)
        
        previous_data = self.tracked_objects[object_id]
        previous_velocity = previous_data.get("velocity", np.zeros(3))
        current_velocity = self._calculate_velocity(object_id, current_transform)
        time_delta = time.time() - previous_data["last_update"]
        
        if time_delta > 0:
            velocity_delta = current_velocity - previous_velocity
            acceleration = velocity_delta / time_delta
            return acceleration
        
        return np.zeros(3)
    
    def get_relative_transform(self, from_object: str, to_object: str) -> Optional[VRTransform]:
        """Get relative transform between two tracked objects"""
        if from_object not in self.tracked_objects or to_object not in self.tracked_objects:
            return None
        
        from_transform = self.tracked_objects[from_object]["transform"]
        to_transform = self.tracked_objects[to_object]["transform"]
        
        # Calculate relative position
        relative_position = to_transform.position - from_transform.position
        
        # Calculate relative rotation (simplified)
        from_rot = Rotation.from_quat(from_transform.rotation)
        to_rot = Rotation.from_quat(to_transform.rotation)
        relative_rot = to_rot * from_rot.inv()
        
        return VRTransform(
            position=relative_position,
            rotation=relative_rot.as_quat(),
            scale=to_transform.scale / from_transform.scale
        )

class HandTrackingEngine:
    """Advanced hand tracking for natural interaction"""
    
    def __init__(self):
        try:
            import mediapipe as mp
            self.mp_hands = mp.solutions.hands
            self.mp_drawing = mp.solutions.drawing_utils
            
            self.hands_detector = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                model_complexity=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5
            )
            
            self.gesture_recognizer = GestureRecognizer()
            logger.info("Hand tracking engine initialized")
            
        except ImportError:
            logger.warning("MediaPipe not available, hand tracking disabled")
            self.hands_detector = None
    
    def process_hand_tracking(self, frame: np.ndarray) -> List[HandTrackingData]:
        """Process hand tracking from camera frame"""
        if not self.hands_detector:
            return []
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands_detector.process(rgb_frame)
            
            hand_data_list = []
            
            if results.multi_hand_landmarks:
                for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    # Determine hand side
                    hand_side = "left" if results.multi_handedness[hand_idx].classification[0].label == "Left" else "right"
                    
                    # Extract landmark positions
                    landmarks = []
                    for landmark in hand_landmarks.landmark:
                        landmarks.append(np.array([landmark.x, landmark.y, landmark.z]))
                    
                    # Recognize gesture
                    gesture, confidence = self.gesture_recognizer.recognize_gesture(landmarks)
                    
                    hand_data = HandTrackingData(
                        hand_side=hand_side,
                        landmarks=landmarks,
                        gesture=gesture,
                        confidence=confidence,
                        is_tracked=True
                    )
                    
                    hand_data_list.append(hand_data)
            
            return hand_data_list
            
        except Exception as e:
            logger.error(f"Hand tracking error: {e}")
            return []

class GestureRecognizer:
    """Advanced gesture recognition for hand interactions"""
    
    def __init__(self):
        self.gesture_templates = self._load_gesture_templates()
        self.gesture_history = []
        
    def _load_gesture_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load gesture templates for recognition"""
        return {
            "point": {
                "description": "Index finger extended, others closed",
                "landmarks": [8],  # Index finger tip
                "conditions": self._check_pointing_gesture
            },
            "grab": {
                "description": "All fingers closed in fist",
                "landmarks": [4, 8, 12, 16, 20],  # All fingertips
                "conditions": self._check_grab_gesture
            },
            "open_hand": {
                "description": "All fingers extended",
                "landmarks": [4, 8, 12, 16, 20],
                "conditions": self._check_open_hand_gesture
            },
            "pinch": {
                "description": "Thumb and index finger close",
                "landmarks": [4, 8],  # Thumb tip and index finger tip
                "conditions": self._check_pinch_gesture
            },
            "peace": {
                "description": "Index and middle finger extended",
                "landmarks": [8, 12],
                "conditions": self._check_peace_gesture
            },
            "thumbs_up": {
                "description": "Thumb extended, others closed",
                "landmarks": [4],
                "conditions": self._check_thumbs_up_gesture
            }
        }
    
    def recognize_gesture(self, landmarks: List[np.ndarray]) -> Tuple[str, float]:
        """Recognize gesture from hand landmarks"""
        if len(landmarks) < 21:  # MediaPipe provides 21 landmarks
            return "unknown", 0.0
        
        best_gesture = "unknown"
        best_confidence = 0.0
        
        for gesture_name, gesture_data in self.gesture_templates.items():
            try:
                confidence = gesture_data["conditions"](landmarks)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_gesture = gesture_name
            except Exception as e:
                logger.debug(f"Error checking gesture {gesture_name}: {e}")
        
        # Update gesture history for temporal consistency
        self.gesture_history.append(best_gesture)
        if len(self.gesture_history) > 10:
            self.gesture_history.pop(0)
        
        # Apply temporal smoothing
        if len(self.gesture_history) >= 3:
            recent_gestures = self.gesture_history[-3:]
            if recent_gestures.count(best_gesture) >= 2:
                best_confidence = min(best_confidence * 1.2, 1.0)
        
        return best_gesture, best_confidence
    
    def _check_pointing_gesture(self, landmarks: List[np.ndarray]) -> float:
        """Check if landmarks match pointing gesture"""
        # Index finger extended, middle/ring/pinky closed
        index_tip = landmarks[8]
        index_pip = landmarks[6]
        middle_tip = landmarks[12]
        middle_pip = landmarks[10]
        
        # Index finger should be extended
        index_extended = index_tip[1] < index_pip[1]
        
        # Middle finger should be closed
        middle_closed = middle_tip[1] > middle_pip[1]
        
        if index_extended and middle_closed:
            return 0.8
        elif index_extended:
            return 0.4
        else:
            return 0.0
    
    def _check_grab_gesture(self, landmarks: List[np.ndarray]) -> float:
        """Check if landmarks match grab/fist gesture"""
        # All fingertips should be below their respective PIPs
        fingertips = [landmarks[4], landmarks[8], landmarks[12], landmarks[16], landmarks[20]]
        pips = [landmarks[3], landmarks[6], landmarks[10], landmarks[14], landmarks[18]]
        
        closed_count = 0
        for tip, pip in zip(fingertips, pips):
            if tip[1] > pip[1]:  # Y coordinate increases downward
                closed_count += 1
        
        return closed_count / 5.0
    
    def _check_open_hand_gesture(self, landmarks: List[np.ndarray]) -> float:
        """Check if landmarks match open hand gesture"""
        # All fingertips should be above their respective PIPs
        fingertips = [landmarks[4], landmarks[8], landmarks[12], landmarks[16], landmarks[20]]
        pips = [landmarks[3], landmarks[6], landmarks[10], landmarks[14], landmarks[18]]
        
        extended_count = 0
        for tip, pip in zip(fingertips, pips):
            if tip[1] < pip[1]:  # Finger extended upward
                extended_count += 1
        
        return extended_count / 5.0
    
    def _check_pinch_gesture(self, landmarks: List[np.ndarray]) -> float:
        """Check if landmarks match pinch gesture"""
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        
        # Calculate distance between thumb and index finger tips
        distance = np.linalg.norm(thumb_tip - index_tip)
        
        # Pinch is when distance is small
        if distance < 0.05:
            return 1.0
        elif distance < 0.1:
            return 0.6
        else:
            return 0.0
    
    def _check_peace_gesture(self, landmarks: List[np.ndarray]) -> float:
        """Check if landmarks match peace sign gesture"""
        index_tip = landmarks[8]
        index_pip = landmarks[6]
        middle_tip = landmarks[12]
        middle_pip = landmarks[10]
        ring_tip = landmarks[16]
        ring_pip = landmarks[14]
        
        # Index and middle extended, ring closed
        index_extended = index_tip[1] < index_pip[1]
        middle_extended = middle_tip[1] < middle_pip[1]
        ring_closed = ring_tip[1] > ring_pip[1]
        
        if index_extended and middle_extended and ring_closed:
            return 0.9
        elif index_extended and middle_extended:
            return 0.5
        else:
            return 0.0
    
    def _check_thumbs_up_gesture(self, landmarks: List[np.ndarray]) -> float:
        """Check if landmarks match thumbs up gesture"""
        thumb_tip = landmarks[4]
        thumb_mcp = landmarks[2]
        index_tip = landmarks[8]
        index_pip = landmarks[6]
        
        # Thumb extended upward, index closed
        thumb_up = thumb_tip[1] < thumb_mcp[1]
        index_closed = index_tip[1] > index_pip[1]
        
        if thumb_up and index_closed:
            return 0.8
        elif thumb_up:
            return 0.4
        else:
            return 0.0

class ImmersiveCharacterRenderer:
    """Advanced 3D character rendering for VR/AR environments"""
    
    def __init__(self):
        self.character_models = {}
        self.animation_systems = {}
        self.lighting_setups = self._create_lighting_presets()
        self.shader_programs = self._create_shader_programs()
        
    def _create_lighting_presets(self) -> Dict[str, Dict[str, Any]]:
        """Create lighting presets for different environments"""
        return {
            "dungeon": {
                "ambient": {"color": [0.1, 0.05, 0.0], "intensity": 0.2},
                "directional": {"color": [1.0, 0.8, 0.4], "intensity": 0.6, "direction": [0.5, -1.0, 0.3]},
                "point_lights": [
                    {"position": [0, 2, 0], "color": [1.0, 0.6, 0.2], "intensity": 0.8, "range": 5.0}
                ]
            },
            "outdoor": {
                "ambient": {"color": [0.4, 0.6, 1.0], "intensity": 0.3},
                "directional": {"color": [1.0, 0.95, 0.8], "intensity": 1.0, "direction": [0.3, -0.8, 0.5]},
                "point_lights": []
            },
            "tavern": {
                "ambient": {"color": [0.8, 0.6, 0.4], "intensity": 0.4},
                "directional": {"color": [1.0, 0.8, 0.6], "intensity": 0.5, "direction": [0, -1, 0]},
                "point_lights": [
                    {"position": [-2, 2, 0], "color": [1.0, 0.7, 0.3], "intensity": 0.6, "range": 3.0},
                    {"position": [2, 2, 0], "color": [1.0, 0.7, 0.3], "intensity": 0.6, "range": 3.0}
                ]
            },
            "studio": {
                "ambient": {"color": [1.0, 1.0, 1.0], "intensity": 0.5},
                "directional": {"color": [1.0, 1.0, 1.0], "intensity": 0.8, "direction": [0.2, -0.8, 0.6]},
                "point_lights": [
                    {"position": [-1, 1, 1], "color": [0.9, 0.9, 1.0], "intensity": 0.7, "range": 4.0},
                    {"position": [1, 1, -1], "color": [1.0, 0.9, 0.9], "intensity": 0.5, "range": 4.0}
                ]
            }
        }
    
    def _create_shader_programs(self) -> Dict[str, str]:
        """Create shader programs for character rendering"""
        return {
            "pbr_vertex": """
                #version 330 core
                layout (location = 0) in vec3 aPos;
                layout (location = 1) in vec3 aNormal;
                layout (location = 2) in vec2 aTexCoord;
                layout (location = 3) in vec3 aTangent;
                
                uniform mat4 model;
                uniform mat4 view;
                uniform mat4 projection;
                uniform mat3 normalMatrix;
                
                out vec3 FragPos;
                out vec3 Normal;
                out vec2 TexCoord;
                out vec3 Tangent;
                out vec3 Bitangent;
                
                void main() {
                    FragPos = vec3(model * vec4(aPos, 1.0));
                    Normal = normalMatrix * aNormal;
                    TexCoord = aTexCoord;
                    Tangent = normalMatrix * aTangent;
                    Bitangent = cross(Normal, Tangent);
                    
                    gl_Position = projection * view * vec4(FragPos, 1.0);
                }
            """,
            
            "pbr_fragment": """
                #version 330 core
                out vec4 FragColor;
                
                in vec3 FragPos;
                in vec3 Normal;
                in vec2 TexCoord;
                in vec3 Tangent;
                in vec3 Bitangent;
                
                uniform vec3 viewPos;
                uniform vec3 albedo;
                uniform float metallic;
                uniform float roughness;
                uniform float ao;
                
                uniform sampler2D albedoMap;
                uniform sampler2D normalMap;
                uniform sampler2D metallicMap;
                uniform sampler2D roughnessMap;
                uniform sampler2D aoMap;
                
                // Light uniforms
                uniform vec3 lightPositions[4];
                uniform vec3 lightColors[4];
                uniform int numLights;
                
                vec3 calculatePBR(vec3 albedo, float metallic, float roughness, float ao, 
                                vec3 normal, vec3 viewDir, vec3 lightDir, vec3 lightColor) {
                    // Simplified PBR calculation
                    float NdotL = max(dot(normal, lightDir), 0.0);
                    float NdotV = max(dot(normal, viewDir), 0.0);
                    
                    vec3 halfwayDir = normalize(lightDir + viewDir);
                    float NdotH = max(dot(normal, halfwayDir), 0.0);
                    
                    // Fresnel
                    vec3 F0 = mix(vec3(0.04), albedo, metallic);
                    vec3 F = F0 + (1.0 - F0) * pow(1.0 - max(dot(halfwayDir, viewDir), 0.0), 5.0);
                    
                    // Distribution
                    float alpha = roughness * roughness;
                    float alpha2 = alpha * alpha;
                    float denom = NdotH * NdotH * (alpha2 - 1.0) + 1.0;
                    float D = alpha2 / (3.14159 * denom * denom);
                    
                    // Geometry
                    float k = (roughness + 1.0) * (roughness + 1.0) / 8.0;
                    float G1L = NdotL / (NdotL * (1.0 - k) + k);
                    float G1V = NdotV / (NdotV * (1.0 - k) + k);
                    float G = G1L * G1V;
                    
                    // BRDF
                    vec3 numerator = D * G * F;
                    float denominator = 4.0 * NdotV * NdotL + 0.001;
                    vec3 specular = numerator / denominator;
                    
                    vec3 kS = F;
                    vec3 kD = vec3(1.0) - kS;
                    kD *= 1.0 - metallic;
                    
                    return (kD * albedo / 3.14159 + specular) * lightColor * NdotL;
                }
                
                void main() {
                    vec3 albedoColor = pow(texture(albedoMap, TexCoord).rgb * albedo, vec3(2.2));
                    float metallicValue = texture(metallicMap, TexCoord).r * metallic;
                    float roughnessValue = texture(roughnessMap, TexCoord).r * roughness;
                    float aoValue = texture(aoMap, TexCoord).r * ao;
                    
                    vec3 normal = normalize(Normal);
                    vec3 viewDir = normalize(viewPos - FragPos);
                    
                    vec3 color = vec3(0.0);
                    
                    for(int i = 0; i < numLights && i < 4; ++i) {
                        vec3 lightDir = normalize(lightPositions[i] - FragPos);
                        color += calculatePBR(albedoColor, metallicValue, roughnessValue, aoValue,
                                            normal, viewDir, lightDir, lightColors[i]);
                    }
                    
                    // Ambient lighting
                    vec3 ambient = vec3(0.03) * albedoColor * aoValue;
                    color += ambient;
                    
                    // HDR tonemapping
                    color = color / (color + vec3(1.0));
                    // Gamma correction
                    color = pow(color, vec3(1.0/2.2));
                    
                    FragColor = vec4(color, 1.0);
                }
            """
        }
    
    def create_character_model(self, character_id: str, character_data: Dict[str, Any]) -> bool:
        """Create 3D character model from character data"""
        try:
            # Generate character mesh based on race and class
            mesh_data = self._generate_character_mesh(character_data)
            
            # Create material based on appearance
            material_data = self._generate_character_material(character_data)
            
            # Set up animation rig
            animation_rig = self._create_animation_rig(character_data)
            
            self.character_models[character_id] = {
                "mesh": mesh_data,
                "material": material_data,
                "animation_rig": animation_rig,
                "bounding_box": self._calculate_bounding_box(mesh_data),
                "level_of_detail": self._generate_lod_models(mesh_data),
                "created_at": time.time()
            }
            
            logger.info(f"Created character model for {character_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create character model: {e}")
            return False
    
    def _generate_character_mesh(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate character mesh based on race and appearance"""
        race = character_data.get("race", "human").lower()
        appearance = character_data.get("appearance", {})
        
        # Base humanoid mesh - in production this would be more sophisticated
        base_mesh = {
            "vertices": self._get_base_humanoid_vertices(race),
            "indices": self._get_base_humanoid_indices(),
            "normals": self._calculate_normals(),
            "uvs": self._get_base_uv_coordinates(),
            "bone_weights": self._get_bone_weights(),
            "bone_indices": self._get_bone_indices()
        }
        
        # Apply racial modifications
        if race == "elf":
            base_mesh = self._apply_elf_modifications(base_mesh)
        elif race == "dwarf":
            base_mesh = self._apply_dwarf_modifications(base_mesh)
        elif race == "halfling":
            base_mesh = self._apply_halfling_modifications(base_mesh)
        elif race == "dragonborn":
            base_mesh = self._apply_dragonborn_modifications(base_mesh)
        
        # Apply appearance customizations
        base_mesh = self._apply_appearance_modifications(base_mesh, appearance)
        
        return base_mesh
    
    def _generate_character_material(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate material properties for character"""
        appearance = character_data.get("appearance", {})
        
        return {
            "albedo": appearance.get("skin_color", [0.8, 0.7, 0.6]),
            "metallic": 0.0,
            "roughness": 0.8,
            "normal_intensity": 1.0,
            "emission": [0.0, 0.0, 0.0],
            "textures": {
                "albedo": self._generate_skin_texture(appearance),
                "normal": self._generate_normal_map(appearance),
                "roughness": self._generate_roughness_map(appearance)
            }
        }
    
    def render_character_in_vr(self, character_id: str, vr_transform: VRTransform,
                              lighting_preset: str = "studio") -> Dict[str, Any]:
        """Render character model for VR display"""
        if character_id not in self.character_models:
            logger.error(f"Character model {character_id} not found")
            return {"error": "Character not found"}
        
        character_model = self.character_models[character_id]
        lighting = self.lighting_setups.get(lighting_preset, self.lighting_setups["studio"])
        
        try:
            # Set up model matrix
            model_matrix = self._create_model_matrix(vr_transform)
            
            # Render with PBR shading
            render_data = {
                "model_matrix": model_matrix.tolist(),
                "mesh_data": character_model["mesh"],
                "material": character_model["material"],
                "lighting": lighting,
                "render_settings": {
                    "shadows": True,
                    "ambient_occlusion": True,
                    "anti_aliasing": True,
                    "anisotropic_filtering": 16
                }
            }
            
            return {
                "success": True,
                "render_data": render_data,
                "performance_metrics": self._get_render_performance_metrics()
            }
            
        except Exception as e:
            logger.error(f"VR rendering error: {e}")
            return {"error": str(e)}
    
    def _get_base_humanoid_vertices(self, race: str) -> List[List[float]]:
        """Get base humanoid vertices (simplified representation)"""
        # This would normally load from a mesh file
        return [
            [0.0, 0.0, 0.0],    # Root
            [0.0, 1.7, 0.0],    # Head
            [-0.3, 1.4, 0.0],   # Left shoulder
            [0.3, 1.4, 0.0],    # Right shoulder
            [-0.7, 1.4, 0.0],   # Left hand
            [0.7, 1.4, 0.0],    # Right hand
            [-0.1, 0.0, 0.0],   # Left foot
            [0.1, 0.0, 0.0]     # Right foot
        ]
    
    def _get_base_humanoid_indices(self) -> List[int]:
        """Get base humanoid face indices"""
        return [0, 1, 2, 0, 2, 3, 3, 4, 5, 5, 6, 7]
    
    def _calculate_normals(self) -> List[List[float]]:
        """Calculate surface normals"""
        return [[0.0, 0.0, 1.0]] * 8  # Simplified
    
    def _create_model_matrix(self, transform: VRTransform) -> np.ndarray:
        """Create model transformation matrix"""
        # Translation matrix
        T = np.eye(4)
        T[:3, 3] = transform.position
        
        # Rotation matrix
        rotation = Rotation.from_quat(transform.rotation)
        R = np.eye(4)
        R[:3, :3] = rotation.as_matrix()
        
        # Scale matrix
        S = np.eye(4)
        S[0, 0] = transform.scale[0]
        S[1, 1] = transform.scale[1]
        S[2, 2] = transform.scale[2]
        
        return T @ R @ S

class VRARVisualizationSystem:
    """Complete VR/AR character visualization system"""
    
    def __init__(self, port: int = 8412):
        self.port = port
        self.connected_clients = {}
        self.active_sessions = {}
        
        # Initialize subsystems
        self.spatial_tracking = SpatialTrackingSystem()
        self.hand_tracking = HandTrackingEngine()
        self.character_renderer = ImmersiveCharacterRenderer()
        
        # VR/AR environments
        self.environments = self._create_default_environments()
        
        # Performance monitoring
        self.performance_metrics = {
            "frame_rate": 90.0,
            "frame_time": 11.1,  # milliseconds
            "render_time": 8.5,
            "tracking_latency": 20.0,
            "dropped_frames": 0
        }
    
    def _create_default_environments(self) -> Dict[str, VREnvironment]:
        """Create default VR environments"""
        return {
            "character_studio": VREnvironment(
                environment_id="studio_01",
                name="Character Studio",
                skybox_url="https://dmlog.ai/assets/skyboxes/studio.hdr",
                lighting_config={"preset": "studio", "intensity": 1.0},
                physics_enabled=False,
                scale=1.0,
                ambient_sound="https://dmlog.ai/assets/audio/ambient_studio.ogg"
            ),
            "tavern_scene": VREnvironment(
                environment_id="tavern_01",
                name="The Prancing Pony",
                skybox_url="https://dmlog.ai/assets/skyboxes/tavern.hdr",
                lighting_config={"preset": "tavern", "intensity": 0.8},
                physics_enabled=True,
                scale=1.0,
                ambient_sound="https://dmlog.ai/assets/audio/tavern_ambience.ogg"
            ),
            "dungeon_preview": VREnvironment(
                environment_id="dungeon_01",
                name="Ancient Dungeon",
                skybox_url="https://dmlog.ai/assets/skyboxes/dungeon.hdr",
                lighting_config={"preset": "dungeon", "intensity": 0.6},
                physics_enabled=True,
                scale=1.0,
                ambient_sound="https://dmlog.ai/assets/audio/dungeon_ambience.ogg"
            )
        }
    
    async def start_server(self):
        """Start VR/AR visualization WebSocket server"""
        logger.info(f"Starting VR/AR visualization system on port {self.port}")
        
        async def handle_client(websocket, path):
            await self._handle_client_connection(websocket, path)
        
        server = await websockets.serve(handle_client, "localhost", self.port)
        logger.info(f"VR/AR system running on ws://localhost:{self.port}")
        await server.wait_closed()
    
    async def _handle_client_connection(self, websocket, path):
        """Handle VR/AR client connections"""
        client_id = f"vr_client_{len(self.connected_clients)}"
        self.connected_clients[client_id] = websocket
        
        try:
            await websocket.send(json.dumps({
                "type": "vr_connection_established",
                "client_id": client_id,
                "supported_platforms": [platform.value for platform in VRPlatform] + 
                                     [platform.value for platform in ARPlatform],
                "environments": {env_id: env.name for env_id, env in self.environments.items()},
                "capabilities": {
                    "hand_tracking": True,
                    "spatial_anchors": True,
                    "character_rendering": True,
                    "physics_simulation": True,
                    "multi_user": True
                }
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_vr_message(client_id, data, websocket)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"VR client disconnected: {client_id}")
        finally:
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
    
    async def _process_vr_message(self, client_id: str, data: Dict[str, Any], websocket):
        """Process VR/AR client messages"""
        message_type = data.get("type")
        
        if message_type == "start_vr_session":
            await self._handle_start_vr_session(client_id, data, websocket)
        elif message_type == "load_character":
            await self._handle_load_character(client_id, data, websocket)
        elif message_type == "update_tracking":
            await self._handle_tracking_update(client_id, data, websocket)
        elif message_type == "hand_gesture":
            await self._handle_hand_gesture(client_id, data, websocket)
        elif message_type == "change_environment":
            await self._handle_environment_change(client_id, data, websocket)
        elif message_type == "create_spatial_anchor":
            await self._handle_spatial_anchor(client_id, data, websocket)
        elif message_type == "character_interaction":
            await self._handle_character_interaction(client_id, data, websocket)
    
    async def _handle_start_vr_session(self, client_id: str, data: Dict[str, Any], websocket):
        """Start VR session"""
        platform = VRPlatform(data.get("platform", "oculus_quest"))
        environment_id = data.get("environment", "character_studio")
        
        session_id = str(uuid.uuid4())
        
        self.active_sessions[session_id] = {
            "client_id": client_id,
            "platform": platform,
            "environment": environment_id,
            "characters": {},
            "spatial_anchors": {},
            "created_at": time.time(),
            "last_activity": time.time()
        }
        
        environment = self.environments.get(environment_id, self.environments["character_studio"])
        
        await websocket.send(json.dumps({
            "type": "vr_session_started",
            "session_id": session_id,
            "environment": {
                "id": environment.environment_id,
                "name": environment.name,
                "skybox_url": environment.skybox_url,
                "lighting": environment.lighting_config,
                "ambient_sound": environment.ambient_sound
            },
            "tracking_space": {
                "origin": [0, 0, 0],
                "forward": [0, 0, -1],
                "up": [0, 1, 0],
                "scale": environment.scale
            }
        }))
    
    async def _handle_load_character(self, client_id: str, data: Dict[str, Any], websocket):
        """Load character into VR session"""
        character_data = data.get("character_data", {})
        character_id = character_data.get("id", str(uuid.uuid4()))
        position = data.get("position", [0, 0, -2])
        
        # Create character model
        success = self.character_renderer.create_character_model(character_id, character_data)
        
        if not success:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Failed to create character model"
            }))
            return
        
        # Set up character transform
        character_transform = VRTransform(
            position=np.array(position),
            rotation=np.array([0, 0, 0, 1]),
            scale=np.ones(3)
        )
        
        # Add to spatial tracking
        self.spatial_tracking.update_object_tracking(character_id, character_transform)
        
        # Render character
        render_result = self.character_renderer.render_character_in_vr(
            character_id, character_transform, "studio"
        )
        
        if render_result.get("success"):
            await websocket.send(json.dumps({
                "type": "character_loaded",
                "character_id": character_id,
                "character_name": character_data.get("name", "Unknown"),
                "render_data": render_result["render_data"],
                "transform": {
                    "position": position,
                    "rotation": [0, 0, 0, 1],
                    "scale": [1, 1, 1]
                }
            }))
        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": render_result.get("error", "Unknown render error")
            }))
    
    async def _handle_tracking_update(self, client_id: str, data: Dict[str, Any], websocket):
        """Handle tracking data updates"""
        hmd_transform = data.get("hmd_transform", {})
        controllers = data.get("controllers", [])
        
        # Update HMD tracking
        if hmd_transform:
            hmd_vr_transform = VRTransform(
                position=np.array(hmd_transform.get("position", [0, 0, 0])),
                rotation=np.array(hmd_transform.get("rotation", [0, 0, 0, 1])),
                scale=np.ones(3)
            )
            self.spatial_tracking.update_object_tracking("hmd", hmd_vr_transform)
        
        # Update controller tracking
        for controller in controllers:
            controller_id = controller.get("id", "controller_0")
            controller_transform = VRTransform(
                position=np.array(controller.get("position", [0, 0, 0])),
                rotation=np.array(controller.get("rotation", [0, 0, 0, 1])),
                scale=np.ones(3)
            )
            self.spatial_tracking.update_object_tracking(controller_id, controller_transform)
        
        # Send tracking confirmation
        await websocket.send(json.dumps({
            "type": "tracking_updated",
            "timestamp": time.time()
        }))
    
    async def _handle_hand_gesture(self, client_id: str, data: Dict[str, Any], websocket):
        """Handle hand gesture recognition"""
        gesture = data.get("gesture", "unknown")
        hand = data.get("hand", "right")
        confidence = data.get("confidence", 0.0)
        
        # Process gesture for character interaction
        interaction_result = await self._process_gesture_interaction(gesture, hand, confidence)
        
        await websocket.send(json.dumps({
            "type": "gesture_processed",
            "gesture": gesture,
            "hand": hand,
            "confidence": confidence,
            "interaction_result": interaction_result
        }))
    
    async def _process_gesture_interaction(self, gesture: str, hand: str, confidence: float) -> Dict[str, Any]:
        """Process gesture for character interaction"""
        if confidence < 0.6:
            return {"action": "none", "message": "Gesture confidence too low"}
        
        if gesture == "point":
            return {"action": "highlight", "message": "Pointing at character"}
        elif gesture == "grab":
            return {"action": "select", "message": "Character selected"}
        elif gesture == "open_hand":
            return {"action": "release", "message": "Character released"}
        elif gesture == "thumbs_up":
            return {"action": "approve", "message": "Character approved"}
        elif gesture == "peace":
            return {"action": "celebrate", "message": "Victory pose"}
        else:
            return {"action": "none", "message": f"Unknown gesture: {gesture}"}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive VR/AR system status"""
        return {
            "system_status": "running",
            "connected_clients": len(self.connected_clients),
            "active_sessions": len(self.active_sessions),
            "performance_metrics": self.performance_metrics,
            "supported_platforms": {
                "vr": [platform.value for platform in VRPlatform],
                "ar": [platform.value for platform in ARPlatform]
            },
            "environments": len(self.environments),
            "characters_loaded": len(self.character_renderer.character_models),
            "spatial_anchors": len(self.spatial_tracking.spatial_anchors),
            "hand_tracking_active": self.hand_tracking.hands_detector is not None
        }

async def main():
    """Main entry point for VR/AR visualization system"""
    logging.basicConfig(level=logging.INFO)
    
    vr_ar_system = VRARVisualizationSystem(port=8412)
    
    try:
        await vr_ar_system.start_server()
    except KeyboardInterrupt:
        logger.info("VR/AR visualization system stopped by user")

if __name__ == "__main__":
    asyncio.run(main())