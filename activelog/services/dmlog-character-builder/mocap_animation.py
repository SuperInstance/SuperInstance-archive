"""
Professional Motion Capture Animation System
Advanced character animation with industry-standard mocap processing
"""

import numpy as np
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import cv2
import mediapipe as mp
from scipy.spatial.transform import Rotation
from scipy import interpolate
from sklearn.decomposition import PCA
import threading
import time
import websockets
import pickle
import base64

logger = logging.getLogger(__name__)

class AnimationType(Enum):
    IDLE = "idle"
    COMBAT = "combat"
    SPELLCASTING = "spellcasting"
    DIALOGUE = "dialogue"
    MOVEMENT = "movement"
    EMOTE = "emote"
    CUSTOM = "custom"

@dataclass
class BoneTransform:
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    rotation: np.ndarray = field(default_factory=lambda: np.array([0, 0, 0, 1]))
    scale: np.ndarray = field(default_factory=lambda: np.ones(3))

@dataclass
class AnimationFrame:
    timestamp: float
    bone_transforms: Dict[str, BoneTransform]
    facial_expressions: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AnimationClip:
    name: str
    animation_type: AnimationType
    frames: List[AnimationFrame]
    duration: float
    loop: bool = False
    blend_weight: float = 1.0
    priority: int = 0

class SkeletonRig:
    """Professional character skeleton with industry-standard bone hierarchy"""
    
    def __init__(self):
        self.bones = self._create_humanoid_skeleton()
        self.bone_hierarchy = self._build_hierarchy()
        self.bind_pose = self._create_bind_pose()
        
    def _create_humanoid_skeleton(self) -> Dict[str, Dict[str, Any]]:
        return {
            # Core skeleton
            "root": {"parent": None, "position": [0, 0, 0]},
            "hips": {"parent": "root", "position": [0, 1.0, 0]},
            "spine1": {"parent": "hips", "position": [0, 1.1, 0]},
            "spine2": {"parent": "spine1", "position": [0, 1.2, 0]},
            "spine3": {"parent": "spine2", "position": [0, 1.3, 0]},
            "neck": {"parent": "spine3", "position": [0, 1.5, 0]},
            "head": {"parent": "neck", "position": [0, 1.6, 0]},
            
            # Left arm
            "left_shoulder": {"parent": "spine3", "position": [-0.2, 1.4, 0]},
            "left_upper_arm": {"parent": "left_shoulder", "position": [-0.3, 1.4, 0]},
            "left_forearm": {"parent": "left_upper_arm", "position": [-0.6, 1.4, 0]},
            "left_hand": {"parent": "left_forearm", "position": [-0.9, 1.4, 0]},
            
            # Right arm
            "right_shoulder": {"parent": "spine3", "position": [0.2, 1.4, 0]},
            "right_upper_arm": {"parent": "right_shoulder", "position": [0.3, 1.4, 0]},
            "right_forearm": {"parent": "right_upper_arm", "position": [0.6, 1.4, 0]},
            "right_hand": {"parent": "right_forearm", "position": [0.9, 1.4, 0]},
            
            # Left leg
            "left_upper_leg": {"parent": "hips", "position": [-0.1, 1.0, 0]},
            "left_lower_leg": {"parent": "left_upper_leg", "position": [-0.1, 0.5, 0]},
            "left_foot": {"parent": "left_lower_leg", "position": [-0.1, 0.0, 0]},
            
            # Right leg
            "right_upper_leg": {"parent": "hips", "position": [0.1, 1.0, 0]},
            "right_lower_leg": {"parent": "right_upper_leg", "position": [0.1, 0.5, 0]},
            "right_foot": {"parent": "right_lower_leg", "position": [0.1, 0.0, 0]},
            
            # Facial bones
            "jaw": {"parent": "head", "position": [0, 1.55, 0.05]},
            "left_eye": {"parent": "head", "position": [-0.03, 1.62, 0.08]},
            "right_eye": {"parent": "head", "position": [0.03, 1.62, 0.08]},
        }
    
    def _build_hierarchy(self) -> Dict[str, List[str]]:
        hierarchy = {}
        for bone_name, bone_data in self.bones.items():
            parent = bone_data["parent"]
            if parent:
                if parent not in hierarchy:
                    hierarchy[parent] = []
                hierarchy[parent].append(bone_name)
        return hierarchy
    
    def _create_bind_pose(self) -> Dict[str, BoneTransform]:
        bind_pose = {}
        for bone_name, bone_data in self.bones.items():
            bind_pose[bone_name] = BoneTransform(
                position=np.array(bone_data["position"]),
                rotation=np.array([0, 0, 0, 1]),
                scale=np.ones(3)
            )
        return bind_pose

class RealtimeMocapProcessor:
    """Real-time motion capture processing using MediaPipe"""
    
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands
        self.mp_face = mp.solutions.face_mesh
        
        self.pose_detector = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            smooth_landmarks=True,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        self.hands_detector = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        self.face_detector = self.mp_face.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        self.calibration_data = None
        self.skeleton = SkeletonRig()
        
    def calibrate_user(self, calibration_frames: List[np.ndarray]) -> Dict[str, Any]:
        """Calibrate the system for a specific user's proportions"""
        logger.info("Starting user calibration...")
        
        # Process calibration frames to establish user proportions
        bone_lengths = {}
        joint_offsets = {}
        
        for frame in calibration_frames:
            pose_results = self.pose_detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if pose_results.pose_landmarks:
                landmarks = pose_results.pose_landmarks.landmark
                
                # Calculate bone lengths from landmarks
                shoulder_width = self._calculate_distance(landmarks[11], landmarks[12])
                arm_length = self._calculate_distance(landmarks[11], landmarks[13]) + \
                           self._calculate_distance(landmarks[13], landmarks[15])
                leg_length = self._calculate_distance(landmarks[23], landmarks[25]) + \
                           self._calculate_distance(landmarks[25], landmarks[27])
                
                bone_lengths["shoulder_width"] = shoulder_width
                bone_lengths["arm_length"] = arm_length
                bone_lengths["leg_length"] = leg_length
        
        # Average the measurements
        self.calibration_data = {
            "bone_lengths": {k: np.mean(v) if isinstance(v, list) else v 
                           for k, v in bone_lengths.items()},
            "joint_offsets": joint_offsets,
            "timestamp": time.time()
        }
        
        logger.info("User calibration completed")
        return self.calibration_data
    
    def process_frame(self, frame: np.ndarray, timestamp: float) -> AnimationFrame:
        """Process a single frame to extract animation data"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process pose
        pose_results = self.pose_detector.process(rgb_frame)
        hand_results = self.hands_detector.process(rgb_frame)
        face_results = self.face_detector.process(rgb_frame)
        
        bone_transforms = {}
        facial_expressions = {}
        
        if pose_results.pose_landmarks:
            bone_transforms.update(self._extract_pose_transforms(pose_results.pose_landmarks))
        
        if hand_results.multi_hand_landmarks:
            bone_transforms.update(self._extract_hand_transforms(hand_results))
        
        if face_results.multi_face_landmarks:
            facial_expressions = self._extract_facial_expressions(face_results.multi_face_landmarks[0])
        
        return AnimationFrame(
            timestamp=timestamp,
            bone_transforms=bone_transforms,
            facial_expressions=facial_expressions,
            metadata={"frame_quality": self._assess_frame_quality(pose_results)}
        )
    
    def _calculate_distance(self, point1, point2) -> float:
        return np.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2 + (point1.z - point2.z)**2)
    
    def _extract_pose_transforms(self, pose_landmarks) -> Dict[str, BoneTransform]:
        landmarks = pose_landmarks.landmark
        transforms = {}
        
        # Map MediaPipe landmarks to our skeleton
        landmark_mapping = {
            "hips": (landmarks[23], landmarks[24]),  # Hip center
            "spine1": landmarks[0],  # Nose as spine reference
            "left_shoulder": landmarks[11],
            "right_shoulder": landmarks[12],
            "left_upper_arm": landmarks[13],
            "right_upper_arm": landmarks[14],
            "left_forearm": landmarks[15],
            "right_forearm": landmarks[16],
            "left_hand": landmarks[19],
            "right_hand": landmarks[20],
            "left_upper_leg": landmarks[23],
            "right_upper_leg": landmarks[24],
            "left_lower_leg": landmarks[25],
            "right_lower_leg": landmarks[26],
            "left_foot": landmarks[31],
            "right_foot": landmarks[32],
        }
        
        for bone_name, landmark_data in landmark_mapping.items():
            if isinstance(landmark_data, tuple):
                # Average position for paired landmarks
                pos = np.array([(landmark_data[0].x + landmark_data[1].x) / 2,
                               (landmark_data[0].y + landmark_data[1].y) / 2,
                               (landmark_data[0].z + landmark_data[1].z) / 2])
            else:
                pos = np.array([landmark_data.x, landmark_data.y, landmark_data.z])
            
            # Calculate rotation based on bone direction
            rotation = self._calculate_bone_rotation(bone_name, pos, landmarks)
            
            transforms[bone_name] = BoneTransform(
                position=pos,
                rotation=rotation,
                scale=np.ones(3)
            )
        
        return transforms
    
    def _calculate_bone_rotation(self, bone_name: str, position: np.ndarray, landmarks) -> np.ndarray:
        """Calculate bone rotation based on joint positions"""
        # Simplified rotation calculation - would be more sophisticated in production
        if "arm" in bone_name.lower():
            # Arm rotation based on shoulder-elbow-wrist alignment
            if "left" in bone_name:
                shoulder = np.array([landmarks[11].x, landmarks[11].y, landmarks[11].z])
                elbow = np.array([landmarks[13].x, landmarks[13].y, landmarks[13].z])
                wrist = np.array([landmarks[15].x, landmarks[15].y, landmarks[15].z])
            else:
                shoulder = np.array([landmarks[12].x, landmarks[12].y, landmarks[12].z])
                elbow = np.array([landmarks[14].x, landmarks[14].y, landmarks[14].z])
                wrist = np.array([landmarks[16].x, landmarks[16].y, landmarks[16].z])
            
            # Calculate rotation from bone direction
            bone_direction = elbow - shoulder
            bone_direction = bone_direction / np.linalg.norm(bone_direction)
            
            # Convert to quaternion (simplified)
            angle = np.arccos(np.dot(bone_direction, np.array([1, 0, 0])))
            axis = np.cross(np.array([1, 0, 0]), bone_direction)
            if np.linalg.norm(axis) > 0:
                axis = axis / np.linalg.norm(axis)
                rotation = Rotation.from_rotvec(angle * axis).as_quat()
            else:
                rotation = np.array([0, 0, 0, 1])
        
        else:
            # Default identity rotation
            rotation = np.array([0, 0, 0, 1])
        
        return rotation
    
    def _extract_hand_transforms(self, hand_results) -> Dict[str, BoneTransform]:
        """Extract hand bone transforms from MediaPipe hand tracking"""
        transforms = {}
        
        for hand_idx, hand_landmarks in enumerate(hand_results.multi_hand_landmarks):
            hand_side = "left" if hand_results.multi_handedness[hand_idx].classification[0].label == "Left" else "right"
            
            # Extract key hand points
            landmarks = hand_landmarks.landmark
            wrist = landmarks[0]
            index_tip = landmarks[8]
            thumb_tip = landmarks[4]
            
            # Create hand transform
            transforms[f"{hand_side}_hand"] = BoneTransform(
                position=np.array([wrist.x, wrist.y, wrist.z]),
                rotation=self._calculate_hand_rotation(landmarks),
                scale=np.ones(3)
            )
        
        return transforms
    
    def _calculate_hand_rotation(self, landmarks) -> np.ndarray:
        """Calculate hand rotation from landmark positions"""
        wrist = np.array([landmarks[0].x, landmarks[0].y, landmarks[0].z])
        middle_finger = np.array([landmarks[9].x, landmarks[9].y, landmarks[9].z])
        
        hand_direction = middle_finger - wrist
        hand_direction = hand_direction / np.linalg.norm(hand_direction)
        
        # Convert to quaternion
        angle = np.arccos(np.dot(hand_direction, np.array([0, 1, 0])))
        axis = np.cross(np.array([0, 1, 0]), hand_direction)
        if np.linalg.norm(axis) > 0:
            axis = axis / np.linalg.norm(axis)
            rotation = Rotation.from_rotvec(angle * axis).as_quat()
        else:
            rotation = np.array([0, 0, 0, 1])
        
        return rotation
    
    def _extract_facial_expressions(self, face_landmarks) -> Dict[str, float]:
        """Extract facial expression parameters"""
        landmarks = face_landmarks.landmark
        
        expressions = {}
        
        # Eye blink detection
        left_eye_ratio = self._calculate_eye_aspect_ratio(landmarks, [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246])
        right_eye_ratio = self._calculate_eye_aspect_ratio(landmarks, [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398])
        
        expressions["left_eye_blink"] = max(0, 1 - left_eye_ratio * 3)
        expressions["right_eye_blink"] = max(0, 1 - right_eye_ratio * 3)
        
        # Mouth expressions
        mouth_ratio = self._calculate_mouth_aspect_ratio(landmarks)
        expressions["mouth_open"] = max(0, mouth_ratio - 0.02) * 20
        
        # Eyebrow raise
        eyebrow_height = (landmarks[70].y + landmarks[63].y + landmarks[105].y + landmarks[66].y + landmarks[107].y) / 5
        expressions["eyebrow_raise"] = max(0, 0.48 - eyebrow_height) * 50
        
        return expressions
    
    def _calculate_eye_aspect_ratio(self, landmarks, indices: List[int]) -> float:
        """Calculate eye aspect ratio for blink detection"""
        if len(indices) < 6:
            return 0.3
        
        # Vertical eye landmarks
        A = self._calculate_distance(landmarks[indices[1]], landmarks[indices[5]])
        B = self._calculate_distance(landmarks[indices[2]], landmarks[indices[4]])
        
        # Horizontal eye landmark
        C = self._calculate_distance(landmarks[indices[0]], landmarks[indices[3]])
        
        ear = (A + B) / (2.0 * C)
        return ear
    
    def _calculate_mouth_aspect_ratio(self, landmarks) -> float:
        """Calculate mouth aspect ratio for mouth open detection"""
        # Mouth landmarks
        A = self._calculate_distance(landmarks[13], landmarks[14])  # Top-bottom
        B = self._calculate_distance(landmarks[78], landmarks[308])  # Left-right
        
        return A / B if B > 0 else 0
    
    def _assess_frame_quality(self, pose_results) -> float:
        """Assess the quality of motion capture data in the frame"""
        if not pose_results.pose_landmarks:
            return 0.0
        
        # Check landmark visibility
        visible_landmarks = sum(1 for landmark in pose_results.pose_landmarks.landmark 
                               if landmark.visibility > 0.7)
        total_landmarks = len(pose_results.pose_landmarks.landmark)
        
        quality_score = visible_landmarks / total_landmarks
        return quality_score

class AnimationBlender:
    """Professional animation blending system"""
    
    def __init__(self):
        self.active_clips = {}
        self.blend_tree = {}
        
    def add_animation_clip(self, clip: AnimationClip, blend_weight: float = 1.0):
        """Add an animation clip to the blending system"""
        self.active_clips[clip.name] = {
            "clip": clip,
            "weight": blend_weight,
            "time": 0.0,
            "active": True
        }
    
    def blend_animations(self, timestamp: float) -> Dict[str, BoneTransform]:
        """Blend multiple animation clips based on weights and priorities"""
        if not self.active_clips:
            return {}
        
        # Sort clips by priority
        sorted_clips = sorted(self.active_clips.items(), 
                            key=lambda x: x[1]["clip"].priority, reverse=True)
        
        final_transforms = {}
        total_weight = 0.0
        
        for clip_name, clip_data in sorted_clips:
            if not clip_data["active"]:
                continue
                
            clip = clip_data["clip"]
            weight = clip_data["weight"]
            clip_time = clip_data["time"]
            
            # Get transforms for current time
            transforms = self._sample_animation_at_time(clip, clip_time)
            
            # Blend transforms
            for bone_name, transform in transforms.items():
                if bone_name not in final_transforms:
                    final_transforms[bone_name] = BoneTransform()
                
                # Weighted blending
                self._blend_transform(final_transforms[bone_name], transform, weight)
            
            total_weight += weight
            
            # Update clip time
            clip_data["time"] += 1/60.0  # Assuming 60 FPS
            if clip_data["time"] > clip.duration:
                if clip.loop:
                    clip_data["time"] = 0.0
                else:
                    clip_data["active"] = False
        
        # Normalize weights
        if total_weight > 0:
            for transform in final_transforms.values():
                transform.position /= total_weight
                # Normalize quaternion
                transform.rotation /= np.linalg.norm(transform.rotation)
        
        return final_transforms
    
    def _sample_animation_at_time(self, clip: AnimationClip, time: float) -> Dict[str, BoneTransform]:
        """Sample animation clip at specific time with interpolation"""
        if not clip.frames:
            return {}
        
        # Find surrounding frames
        frame_before = None
        frame_after = None
        
        for frame in clip.frames:
            if frame.timestamp <= time:
                frame_before = frame
            if frame.timestamp >= time and frame_after is None:
                frame_after = frame
                break
        
        if frame_before is None:
            return clip.frames[0].bone_transforms
        if frame_after is None:
            return clip.frames[-1].bone_transforms
        if frame_before == frame_after:
            return frame_before.bone_transforms
        
        # Interpolate between frames
        t = (time - frame_before.timestamp) / (frame_after.timestamp - frame_before.timestamp)
        interpolated_transforms = {}
        
        all_bones = set(frame_before.bone_transforms.keys()) | set(frame_after.bone_transforms.keys())
        
        for bone_name in all_bones:
            transform_before = frame_before.bone_transforms.get(bone_name, BoneTransform())
            transform_after = frame_after.bone_transforms.get(bone_name, BoneTransform())
            
            # Interpolate position
            pos = transform_before.position * (1 - t) + transform_after.position * t
            
            # Slerp rotation (quaternion)
            rot_before = Rotation.from_quat(transform_before.rotation)
            rot_after = Rotation.from_quat(transform_after.rotation)
            rot = Rotation.slerp(rot_before, rot_after, t)
            
            # Interpolate scale
            scale = transform_before.scale * (1 - t) + transform_after.scale * t
            
            interpolated_transforms[bone_name] = BoneTransform(
                position=pos,
                rotation=rot.as_quat(),
                scale=scale
            )
        
        return interpolated_transforms
    
    def _blend_transform(self, target: BoneTransform, source: BoneTransform, weight: float):
        """Blend source transform into target transform with weight"""
        target.position += source.position * weight
        
        # Quaternion blending (simplified)
        target_rot = Rotation.from_quat(target.rotation)
        source_rot = Rotation.from_quat(source.rotation)
        blended_rot = Rotation.slerp(target_rot, source_rot, weight)
        target.rotation = blended_rot.as_quat()
        
        target.scale += source.scale * weight

class ProfessionalMocapSystem:
    """Complete professional motion capture animation system"""
    
    def __init__(self, port: int = 8410):
        self.port = port
        self.processor = RealtimeMocapProcessor()
        self.blender = AnimationBlender()
        self.skeleton = SkeletonRig()
        self.animation_library = {}
        self.recording_session = None
        self.connected_clients = {}
        self.is_recording = False
        
    async def start_server(self):
        """Start the motion capture WebSocket server"""
        logger.info(f"Starting professional mocap system on port {self.port}")
        
        async def handle_client(websocket, path):
            await self._handle_client_connection(websocket, path)
        
        server = await websockets.serve(handle_client, "localhost", self.port)
        logger.info(f"Professional mocap system running on ws://localhost:{self.port}")
        await server.wait_closed()
    
    async def _handle_client_connection(self, websocket, path):
        """Handle client connections and messages"""
        client_id = f"mocap_client_{len(self.connected_clients)}"
        self.connected_clients[client_id] = websocket
        
        try:
            await websocket.send(json.dumps({
                "type": "connection_established",
                "client_id": client_id,
                "capabilities": {
                    "realtime_mocap": True,
                    "animation_blending": True,
                    "facial_capture": True,
                    "hand_tracking": True,
                    "animation_library": True
                }
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_client_message(client_id, data, websocket)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Mocap client disconnected: {client_id}")
        finally:
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
    
    async def _process_client_message(self, client_id: str, data: Dict[str, Any], websocket):
        """Process messages from mocap clients"""
        message_type = data.get("type")
        
        if message_type == "start_calibration":
            await self._handle_calibration_start(client_id, data, websocket)
        elif message_type == "calibration_frame":
            await self._handle_calibration_frame(client_id, data, websocket)
        elif message_type == "start_recording":
            await self._handle_recording_start(client_id, data, websocket)
        elif message_type == "mocap_frame":
            await self._handle_mocap_frame(client_id, data, websocket)
        elif message_type == "stop_recording":
            await self._handle_recording_stop(client_id, data, websocket)
        elif message_type == "get_animation_library":
            await self._send_animation_library(websocket)
        elif message_type == "play_animation":
            await self._handle_play_animation(client_id, data, websocket)
        elif message_type == "blend_animations":
            await self._handle_blend_animations(client_id, data, websocket)
    
    async def _handle_calibration_start(self, client_id: str, data: Dict[str, Any], websocket):
        """Handle calibration start request"""
        await websocket.send(json.dumps({
            "type": "calibration_ready",
            "instructions": "Please stand in T-pose facing the camera for 5 seconds"
        }))
    
    async def _handle_calibration_frame(self, client_id: str, data: Dict[str, Any], websocket):
        """Handle calibration frame data"""
        # Decode frame data
        frame_data = base64.b64decode(data["frame"])
        frame = pickle.loads(frame_data)
        
        # Process calibration frame
        # In production, would accumulate frames and process at end
        calibration_result = self.processor.calibrate_user([frame])
        
        await websocket.send(json.dumps({
            "type": "calibration_complete",
            "calibration_data": {
                "bone_lengths": calibration_result["bone_lengths"],
                "timestamp": calibration_result["timestamp"]
            }
        }))
    
    async def _handle_recording_start(self, client_id: str, data: Dict[str, Any], websocket):
        """Handle animation recording start"""
        animation_name = data.get("animation_name", f"recording_{int(time.time())}")
        animation_type = AnimationType(data.get("animation_type", "custom"))
        
        self.recording_session = {
            "name": animation_name,
            "type": animation_type,
            "frames": [],
            "start_time": time.time(),
            "client_id": client_id
        }
        self.is_recording = True
        
        await websocket.send(json.dumps({
            "type": "recording_started",
            "animation_name": animation_name,
            "animation_type": animation_type.value
        }))
    
    async def _handle_mocap_frame(self, client_id: str, data: Dict[str, Any], websocket):
        """Handle motion capture frame data"""
        timestamp = data.get("timestamp", time.time())
        
        # Decode frame data
        frame_data = base64.b64decode(data["frame"])
        frame = pickle.loads(frame_data)
        
        # Process frame
        animation_frame = self.processor.process_frame(frame, timestamp)
        
        if self.is_recording and self.recording_session:
            self.recording_session["frames"].append(animation_frame)
        
        # Send processed animation data to all connected clients
        animation_data = {
            "type": "animation_frame",
            "timestamp": timestamp,
            "bone_transforms": {
                bone_name: {
                    "position": transform.position.tolist(),
                    "rotation": transform.rotation.tolist(),
                    "scale": transform.scale.tolist()
                }
                for bone_name, transform in animation_frame.bone_transforms.items()
            },
            "facial_expressions": animation_frame.facial_expressions,
            "frame_quality": animation_frame.metadata.get("frame_quality", 0.0)
        }
        
        # Broadcast to all clients
        for ws in self.connected_clients.values():
            try:
                await ws.send(json.dumps(animation_data))
            except:
                pass
    
    async def _handle_recording_stop(self, client_id: str, data: Dict[str, Any], websocket):
        """Handle animation recording stop"""
        if not self.recording_session or not self.is_recording:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "No active recording session"
            }))
            return
        
        # Create animation clip
        duration = time.time() - self.recording_session["start_time"]
        animation_clip = AnimationClip(
            name=self.recording_session["name"],
            animation_type=self.recording_session["type"],
            frames=self.recording_session["frames"],
            duration=duration,
            loop=data.get("loop", False)
        )
        
        # Save to library
        self.animation_library[animation_clip.name] = animation_clip
        self.is_recording = False
        self.recording_session = None
        
        await websocket.send(json.dumps({
            "type": "recording_complete",
            "animation_name": animation_clip.name,
            "duration": duration,
            "frame_count": len(animation_clip.frames)
        }))
    
    async def _send_animation_library(self, websocket):
        """Send animation library to client"""
        library_data = {
            "type": "animation_library",
            "animations": {
                name: {
                    "name": clip.name,
                    "type": clip.animation_type.value,
                    "duration": clip.duration,
                    "frame_count": len(clip.frames),
                    "loop": clip.loop
                }
                for name, clip in self.animation_library.items()
            }
        }
        
        await websocket.send(json.dumps(library_data))
    
    async def _handle_play_animation(self, client_id: str, data: Dict[str, Any], websocket):
        """Handle animation playback request"""
        animation_name = data.get("animation_name")
        blend_weight = data.get("blend_weight", 1.0)
        
        if animation_name in self.animation_library:
            clip = self.animation_library[animation_name]
            clip.blend_weight = blend_weight
            self.blender.add_animation_clip(clip, blend_weight)
            
            await websocket.send(json.dumps({
                "type": "animation_started",
                "animation_name": animation_name,
                "blend_weight": blend_weight
            }))
        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Animation '{animation_name}' not found in library"
            }))
    
    async def _handle_blend_animations(self, client_id: str, data: Dict[str, Any], websocket):
        """Handle animation blending request"""
        animations = data.get("animations", [])
        
        for anim_data in animations:
            name = anim_data.get("name")
            weight = anim_data.get("weight", 1.0)
            
            if name in self.animation_library:
                clip = self.animation_library[name]
                clip.blend_weight = weight
                self.blender.add_animation_clip(clip, weight)
        
        await websocket.send(json.dumps({
            "type": "blending_started",
            "animation_count": len(animations)
        }))

async def main():
    """Main entry point for the professional mocap system"""
    logging.basicConfig(level=logging.INFO)
    
    mocap_system = ProfessionalMocapSystem(port=8410)
    
    try:
        await mocap_system.start_server()
    except KeyboardInterrupt:
        logger.info("Professional mocap system stopped by user")

if __name__ == "__main__":
    asyncio.run(main())